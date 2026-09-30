#!/usr/bin/env python3
"""Translate Prowler appraisal materials from their explicit descriptions."""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'Sources/HunterDex/Resources'
db = sqlite3.connect(RES / 'mhgu.db')
linked_path = RES / 'linked-localization.json'
provenance_path = ROOT / 'LINKED-LOCALIZATION-SOURCES.json'
linked = json.loads(linked_path.read_text())
provenance = json.loads(provenance_path.read_text())
base = json.loads((RES / 'zh.json').read_text())
existing = json.loads((RES / 'localization.json').read_text())

# Reuse the project's reviewed names and add source-description aliases used by
# MHGenDatabase's appraisal-item template.
monsters = dict(base.get('monsters', {}))
monsters.update(existing.get('monsters', {}))
monsters.update(json.loads((ROOT / 'scripts/monster-names.json').read_text()))
monsters.update({
    'Redhelm': '红盔青熊兽', 'Snowbaron': '大雪主白兔兽',
    'Stonefist': '矛碎大名盾蟹', 'Dreadqueen': '紫毒姬雌火龙',
    'Drilltusk': '岩穿鬼蛙', 'Silverwind': '白疾风迅龙',
    'Crystalbeard': '宝缠爆锤龙', 'Deadeye': '独眼黑狼鸟',
    'Dreadking': '黑炎王雄火龙', 'Thunderlord': '金雷公雷狼龙',
    'Grimclaw': '荒钩爪轰龙', 'Hellblade': '烬灭刃斩龙',
    'Nightcloak': '胧隐夜鸟', 'Rustrazor': '铠裂将军镰蟹',
    'Boltreaver': '青电主电龙', 'Soulseer': '天眼泡狐龙',
    'Elderfrost': '银岭巨兽', 'Bloodbath': '鏖魔角龙',
    'D.Hermitaur': '大名盾蟹', 'S.Ceanataur': '将军镰蟹',
    'K.Daora': '钢龙', 'S.Magala': '天廻龙', 'G.Maccao': '大跳狗龙',
    'R.Brachydios': '猛爆碎龙', 'Chaotic Gore Magala': '混沌黑蚀龙',
    'G.Thunderbug': '大雷光虫', 'Ruin': '巨戟龙', 'Empress': '巨戟龙',
    'furious Rajang': '激昂金狮子', 'savage Deviljho': '怒食恐暴龙',
    'crimson Fatalis': '红黑龙', 'old Fatalis': '老黑龙',
})

pattern = re.compile(
    r'An unappraised (.+?) material obtained by a Prowler using '
    r'Pilfer or Plunderang\.'
)
translated = 0
unmapped = []
for item_id, english, description in db.execute(
    "SELECT _id,name,description FROM items WHERE type='' ORDER BY _id"
):
    match = pattern.fullmatch(description or '')
    if not match:
        continue
    entity = match.group(1)
    chinese_entity = monsters.get(entity)
    if not chinese_entity:
        unmapped.append((english, entity))
        continue
    key = str(item_id)
    current = linked.get('items_by_id', {}).get(key) or existing.get('items_by_id', {}).get(key)
    if current and re.search('[\u3400-\u9fff]', current):
        continue
    name = f'未鉴定的{chinese_entity}素材'
    linked.setdefault('items_by_id', {})[key] = name
    provenance.setdefault('items', {})[key] = [{
        'name': name,
        'english': english,
        'method': 'translated from exact database appraisal-item description; monster entity resolved through reviewed monster-name glossary',
    }]
    translated += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + '\n')
provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
print(f'Imported {translated} unappraised material names.')
if unmapped:
    print('Unmapped description entities:', unmapped)
