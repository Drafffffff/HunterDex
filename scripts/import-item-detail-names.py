#!/usr/bin/env python3
"""Match Chinese item pages to MHGU records by unique quest-reward fingerprints."""
import collections
import json
import re
import sqlite3
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'Sources/HunterDex/Resources'
CACHE = ROOT / '.cache/data-sources/jestar'
db = sqlite3.connect(RES / 'mhgu.db')
db.row_factory = sqlite3.Row
out = json.loads((RES / 'linked-localization.json').read_text())
evidence = json.loads((ROOT / 'LINKED-LOCALIZATION-SOURCES.json').read_text())

# The linked-quest importer has already matched Chinese title pages to database
# quests using hub, rank, stars, location, objective, and targets.
source_quests = collections.defaultdict(set)
for quest_id, record in evidence.get('quests', {}).items():
    source_ids = set(record.get('source_quest_ids', []))
    if record.get('source_quest_id'):
        source_ids.add(record['source_quest_id'])
    for source_id in source_ids:
        source_quests[source_id].add(int(quest_id))
source_quests = {source_id: ids for source_id, ids in source_quests.items() if len(ids) == 1}

source_items = collections.defaultdict(set)
source_origins = collections.defaultdict(set)
for path in (CACHE / 'ida').glob('*.html'):
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    table = soup.select_one('table.t2')
    if table is None:
        continue
    rows = table.select('tr')
    if len(rows) < 2:
        continue
    heading = rows[0].find('th')
    name_cell = rows[0].find('td')
    if heading is None or heading.get_text(strip=True) != '名称' or name_cell is None:
        continue
    name_el = name_cell.select_one('.b')
    name = name_el.get_text(' ', strip=True) if name_el else ''
    if not re.search(r'[\u3400-\u9fff]', name) or re.search(r'[\u3040-\u30ff]', name):
        continue
    values = {}
    cells = rows[1].find_all(['th', 'td'], recursive=False)
    for index in range(0, len(cells) - 1, 2):
        label = cells[index].get_text(' ', strip=True)
        value = cells[index + 1].get_text(' ', strip=True)
        if label.startswith('稀有度'):
            m = re.search(r'\d+', value)
            if m: values['rarity'] = int(m.group())
        elif label == '所持':
            m = re.search(r'\d+', value)
            if m: values['carry'] = int(m.group())
    if 'rarity' not in values or 'carry' not in values:
        continue

    reward_rows = []
    for row in soup.select('table.t1 tr'):
        label = row.select_one('td.get_item1')
        cell = row.select_one('td.get_item2')
        if label is None or cell is None or '任务报酬' not in label.get_text(' ', strip=True):
            continue
        line = []
        lines = []
        for node in list(cell.contents):
            if getattr(node, 'name', None) == 'br':
                lines.append(line)
                line = []
            else:
                line.append(node)
        if line: lines.append(line)
        for nodes in lines:
            anchor = next((node for node in nodes if getattr(node, 'name', None) == 'a' and '/ida/' in node.get('href', '')), None)
            if anchor is None: continue
            source_id = re.search(r'/ida/(\d+)\.html', anchor.get('href', ''))
            if source_id is None: continue
            db_ids = source_quests.get(source_id.group(1), set())
            if len(db_ids) != 1: continue
            text = ''.join(node.get_text(' ', strip=True) if hasattr(node, 'get_text') else str(node) for node in nodes)
            quantity = re.search(r'(\d+)\s*个', text)
            percentage = re.search(r'(\d+)\s*%', text)
            if percentage is None: continue
            slot = 'Sub' if '副任务' in text else 'Main'
            reward_rows.append((next(iter(db_ids)), slot, int(quantity.group(1)) if quantity else 1, int(percentage.group(1))))
    if len(reward_rows) < 1:
        continue
    signature = (values['rarity'], values['carry'], tuple(sorted(reward_rows)))
    source_items[signature].add(name)
    source_origins[signature].add(path.stem)

database_items = collections.defaultdict(list)
mapped_quest_ids = {value for ids in source_quests.values() for value in ids}
reward_by_item = collections.defaultdict(list)
if mapped_quest_ids:
    placeholders = ','.join('?' for _ in mapped_quest_ids)
    for reward in db.execute(f"SELECT item_id,quest_id,reward_slot,stack_size,percentage FROM quest_rewards WHERE quest_id IN ({placeholders})", tuple(mapped_quest_ids)):
        reward_by_item[reward['item_id']].append((reward['quest_id'], 'Sub' if reward['reward_slot'] == 'Sub' else 'Main', reward['stack_size'], reward['percentage']))
for row in db.execute("SELECT _id,name,rarity,carry_capacity FROM items WHERE type='' "):
    rewards = reward_by_item.get(row['_id'], [])
    if len(rewards) >= 1:
        signature = (row['rarity'], row['carry_capacity'], tuple(sorted(rewards)))
        database_items[signature].append(row)

proposals = collections.defaultdict(list)
for signature, names in source_items.items():
    rows = database_items.get(signature, [])
    if len(names) == 1 and len(rows) == 1:
        proposal = next(iter(names))
        proposals[str(rows[0]['_id'])].append(proposal)

added = 0
for item_id, names in proposals.items():
    if len(set(names)) != 1:
        continue
    name = names[0]
    existing = out.get('items_by_id', {}).get(item_id)
    if existing and existing != name:
        continue
    if existing == name:
        continue
    out.setdefault('items_by_id', {})[item_id] = name
    evidence.setdefault('items', {}).setdefault(item_id, []).append({
        'name': name,
        'method': 'unique rarity/carry capacity and mapped quest-reward distribution',
        'english': db.execute('SELECT name FROM items WHERE _id=?', (int(item_id),)).fetchone()['name'],
        'source': ['jestar719/mhgu:app/src/main/assets/mhxx/ida/' + source_id + '.html'
                   for source_id in sorted(source_origins[signature])]
    })
    added += 1

(RES / 'linked-localization.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'LINKED-LOCALIZATION-SOURCES.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
print(f'Item detail mappings: {added} (quest pages mapped: {len(source_quests)})')
