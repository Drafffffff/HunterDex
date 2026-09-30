#!/usr/bin/env python3
"""Match item names by complete cross-location gathering profiles.

Requires a unique Chinese source item and a unique database item with the same
rarity, carry capacity, and complete quantity/probability profile across all
mapped gathering locations.
"""
import collections
import json
import re
import sqlite3
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'Sources/HunterDex/Resources'
CACHE = ROOT / '.cache/data-sources'
db = sqlite3.connect(RES / 'mhgu.db')
db.row_factory = sqlite3.Row
out = json.loads((RES / 'linked-localization.json').read_text())
evidence = json.loads((ROOT / 'LINKED-LOCALIZATION-SOURCES.json').read_text())
base = json.loads((RES / 'zh.json').read_text())
old = json.loads((RES / 'localization.json').read_text())

source_db = sqlite3.connect(CACHE / 'jestar-mhgu.db')
location_ids = {
    translated: row['_id']
    for row in db.execute('select _id,name from locations')
    if (translated := out.get('locations', {}).get(row['name']))
}
mapped_ids = set(location_ids.values())
observations_by_url = collections.defaultdict(set)

for location, url in source_db.execute(
    'select name,url from IndexBean where type=7 and url is not null'
):
    if location not in location_ids:
        continue
    path = CACHE / 'jestar' / url
    if not path.exists():
        continue
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    for table in soup.select('table'):
        heading = table.find_previous('h3')
        rank_heading = table.find_previous('h4')
        if heading is None or rank_heading is None:
            continue
        area = heading.get_text(strip=True).replace('区域', 'Area ')
        if area == 'Area 秘境':
            area = 'Secret'
        if not (area.startswith('Area ') or area == 'Secret'):
            continue
        rank = {'下位': 'LR', '上位': 'HR', 'G级': 'G'}.get(
            rank_heading.get_text(strip=True)
        )
        if rank is None:
            continue
        for tr in table.select('tr'):
            cells = tr.find_all('td', recursive=False)
            if len(cells) < 2:
                continue
            anchor = cells[-2].select_one('a[href*="ida/"]')
            if anchor is None:
                continue
            percentage = re.search(r'(\d+)%', cells[-1].get_text())
            quantity = re.search(r'[x×]\s*(\d+)', cells[-2].get_text())
            if percentage is None:
                continue
            observations_by_url[anchor['href']].add((
                location_ids[location], rank, area,
                int(quantity[1]) if quantity else 1,
                int(percentage[1]),
            ))

source_profiles = collections.defaultdict(list)
source_dir = CACHE / 'jestar'
for url, observations in observations_by_url.items():
    path = source_dir / url.replace('../', '')
    if not path.exists() or len(observations) < 2:
        continue
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    rows = soup.select('table.t2 tr')
    if len(rows) < 2:
        continue
    heading = rows[0].find('th')
    name_cell = rows[0].find('td')
    name_el = name_cell.select_one('.b') if name_cell else None
    name = name_el.get_text(' ', strip=True) if name_el else ''
    if heading is None or heading.get_text(strip=True) != '名称':
        continue
    if not re.search(r'[\u3400-\u9fff]', name) or re.search(r'[\u3040-\u30ff]', name):
        continue
    values = {}
    cells = rows[1].find_all(['th', 'td'], recursive=False)
    for index in range(0, len(cells) - 1, 2):
        label = cells[index].get_text(' ', strip=True)
        value = cells[index + 1].get_text(' ', strip=True)
        if label.startswith('稀有度'):
            match = re.search(r'\d+', value)
            if match:
                values['rarity'] = int(match[0])
        elif label == '所持':
            match = re.search(r'\d+', value)
            if match:
                values['carry'] = int(match[0])
    if set(values) != {'rarity', 'carry'}:
        continue
    signature = (values['rarity'], values['carry'], tuple(sorted(observations)))
    source_profiles[signature].append((url, name))

db_observations = collections.defaultdict(set)
for row in db.execute(
    'select item_id,location_id,rank,area,quantity,percentage from gathering'
):
    if row['location_id'] in mapped_ids:
        db_observations[row['item_id']].add((
            row['location_id'], row['rank'], row['area'],
            row['quantity'], row['percentage'],
        ))

db_profiles = collections.defaultdict(list)
for row in db.execute("select _id,name,rarity,carry_capacity from items where type='' "):
    observations = db_observations.get(row['_id'], set())
    if len(observations) < 2:
        continue
    signature = (row['rarity'], row['carry_capacity'], tuple(sorted(observations)))
    db_profiles[signature].append(row)

added = 0
for signature, source_items in source_profiles.items():
    records = db_profiles.get(signature, [])
    if len(source_items) != 1 or len(records) != 1:
        continue
    source_url, name = source_items[0]
    row = records[0]
    item_id = str(row['_id'])
    existing = out.get('items_by_id', {}).get(item_id)
    if existing and existing != name:
        continue
    if existing == name or row['name'] in base.get('items', {}) or row['name'] in old.get('items', {}):
        continue
    out.setdefault('items_by_id', {})[item_id] = name
    evidence.setdefault('items', {}).setdefault(item_id, []).append({
        'name': name,
        'method': 'unique rarity/carry capacity and complete cross-location gathering distribution',
        'english': row['name'],
        'source': 'jestar719/mhgu:app/src/main/assets/mhxx/' + source_url.replace('../', ''),
    })
    added += 1

(RES / 'linked-localization.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + '\n'
)
(ROOT / 'LINKED-LOCALIZATION-SOURCES.json').write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2) + '\n'
)
print(f'Global gathering mappings: {added}')
