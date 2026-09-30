#!/usr/bin/env python3
"""Resolve ambiguous Chinese quest panels using their detailed objective text."""
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'Sources/HunterDex/Resources'
CACHE = ROOT / '.cache/data-sources/jestar/ida'
db = sqlite3.connect(RES / 'mhgu.db')
db.row_factory = sqlite3.Row
out = json.loads((RES / 'linked-localization.json').read_text())
base = json.loads((RES / 'zh.json').read_text())
local = json.loads((RES / 'localization.json').read_text())
evidence = json.loads((ROOT / 'LINKED-LOCALIZATION-SOURCES.json').read_text())

def normalize(text):
    return re.sub(r'[^\w\u3400-\u9fff]', '', unicodedata.normalize('NFKC', text).replace('姫', '姬')).lower()

def detail_goals(source_id):
    path = CACHE / f'{source_id}.html'
    if not path.exists(): return None
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    result = {}
    for row in soup.select('tr'):
        cells = row.find_all(['th', 'td'], recursive=False)
        for index in range(0, len(cells) - 1, 2):
            key = cells[index].get_text(' ', strip=True)
            if key in ('主任务', '副任务'):
                result[key] = cells[index + 1].get_text(' ', strip=True)
    return result or None

terms = set()
for group in ('monsters', 'items', 'quests'):
    terms.update(value for value in base.get(group, {}).values() if isinstance(value, str))
terms.update(value for value in local.get('monsters', {}).values() if isinstance(value, str))
terms.update(value for value in local.get('items_by_id', {}).values() if isinstance(value, str))
terms.update(value for value in out.get('items_by_id', {}).values() if isinstance(value, str))
terms = {normalize(value): value for value in terms if len(normalize(value)) >= 2}

mapped = out.setdefault('quests_by_id', {})
quest_sources = evidence.setdefault('quests', {})
added = 0
conflicts = 0
for source_id, records in evidence.get('quest_candidates', {}).items():
    unique_records = {(record['name'], tuple(record['candidates']), record['source']) for record in records}
    if len(unique_records) != 1:
        continue
    source_name, candidate_ids, source_page = next(iter(unique_records))
    if not re.search(r'[\u3400-\u9fff]', source_name) or re.search(r'[\u3040-\u30ff]', source_name):
        continue
    source_goals = detail_goals(source_id)
    if not source_goals:
        continue
    source_normalized = {key: normalize(value) for key, value in source_goals.items()}
    matches = []
    for candidate_id in candidate_ids:
        quest = db.execute('SELECT _id,name,goal,sub_goal FROM quests WHERE _id=?', (candidate_id,)).fetchone()
        if quest is None: continue
        translated = out.get('goals', {})
        goal = translated.get(quest['goal'], base.get('goals', {}).get(quest['goal'], ''))
        sub_goal = translated.get(quest['sub_goal'], base.get('goals', {}).get(quest['sub_goal'], '')) if quest['sub_goal'] else ''
        exact_title = base.get('quests', {}).get(quest['name']) == source_name
        goal_matches = []
        for key, candidate_goal in (('主任务', goal), ('副任务', sub_goal)):
            if key not in source_normalized or not candidate_goal: continue
            normalized_goal = normalize(candidate_goal)
            if normalized_goal and normalized_goal in source_normalized[key]:
                goal_matches.append(True)
                continue
            entities = [token for token, value in terms.items() if token in normalized_goal and len(token) >= 2]
            if entities and all(token in source_normalized[key] for token in entities):
                goal_digits = sorted(re.findall(r'\d+', normalized_goal))
                source_digits = sorted(re.findall(r'\d+', source_normalized[key]))
                if not goal_digits or not source_digits or goal_digits == source_digits:
                    goal_matches.append(True)
        if exact_title or goal_matches:
            matches.append(quest)
    if len(matches) != 1:
        if len(matches) > 1: conflicts += 1
        continue
    quest = matches[0]
    quest_id = str(quest['_id'])
    existing = mapped.get(quest_id, base.get('quests', {}).get(quest['name']))
    if existing and existing != source_name:
        continue
    mapped[quest_id] = source_name
    quest_sources[quest_id] = {
        'english': quest['name'],
        'source': f'jestar719/mhgu:app/src/main/assets/mhxx/ida/{source_id}.html',
        'source_quest_id': source_id,
        'method': 'unique hub/rank/stars/location/targets plus exact translated objective text'
    }
    added += 1

(RES / 'linked-localization.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'LINKED-LOCALIZATION-SOURCES.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
print(f'Quest titles resolved from detailed objectives: {added}; multiple candidate matches: {conflicts}')
