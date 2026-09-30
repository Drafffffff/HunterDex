#!/usr/bin/env python3
"""Add explicit project-reviewed translations for transparent armor name patterns."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "Sources/HunterDex/Resources"
DB = sqlite3.connect(RES / "mhgu.db")
DB.row_factory = sqlite3.Row
linked_path = RES / "linked-localization.json"
source_path = ROOT / "LINKED-LOCALIZATION-SOURCES.json"
linked = json.loads(linked_path.read_text())
sources = json.loads(source_path.read_text())
legacy = json.loads((RES / "localization.json").read_text())

# These two set names and their part names translate directly without relying
# on a stat-only join to unrelated armor. Rank suffixes remain the game's
# standard S/X/U/Z notation.
SERIES = {
    "Guardian": "守护者",
    "Gammoth": "巨兽",
}
PARTS = {
    "Helm": "头盔", "Mask": "面具", "Suit": "铠甲", "Vest": "轻甲",
    "Braces": "腕甲", "Guards": "手甲", "Vambraces": "腕甲",
    "Coil": "腰甲", "Coat": "护腰", "Boots": "重靴", "Pants": "护腿",
    "Cap": "帽", "Mail": "铠甲", "Faulds": "腰甲",
    "Greaves": "护腿", "Leggings": "胫甲",
}
EXPLICIT_NAMES = {
    "Takami Feather": "高见羽饰",
    "Hayabusa Feather": "隼刃羽饰",
    "Kakuju Feather": "鹤羽饰",
    "Sword Saint Earring": "剑圣耳环",
    "Barrage Earring": "增弹耳环",
    "Flame Earring": "斩炎耳环",
    "Shock Earring": "雷电耳环",
    "Ice Earring": "巨冰耳环",
    "Water Earring": "水狐耳环",
    "Comet Earring": "龙彗耳环",
    "Blooming Bherna": "贝尔纳绽花装",
    "Verdant Kokoto": "科科特翠绿装",
    "Snowy Pokke": "波凯雪景装",
    "Thermal Yukumo": "结云暖衣",
    "Biker Jacket": "机车夹克",
    "Biker Leather": "机车皮衣",
    "Rider Jacket": "骑手夹克",
    "Rider Leather": "骑手皮衣",
    "Trapper's Greaves": "捕猎者护腿",
    "Trapper's Boots": "捕猎者靴",
    "Black Leather Chaps": "黑皮短裤",
    "Black Leather Pants": "黑皮长裤",
}
EARRING_SOURCE = "https://mhwiki.axibug.com/mhxx-wiki/data/2307.html"
PATTERN = re.compile(r"(.+?) (Helm|Mask|Suit|Vest|Braces|Guards|Vambraces|Coil|Coat|Boots|Pants|Cap|Mail|Faulds|Greaves|Leggings)(?: ([SUXZ]))?")

translated = 0
known = {**legacy.get("items_by_id", {}), **linked.get("items_by_id", {})}
for row in DB.execute(
    "SELECT _id, name FROM items WHERE _id IN (SELECT _id FROM armor) ORDER BY _id"
):
    item_id = str(row["_id"])
    if re.search(r"[\u3400-\u9fff]", known.get(item_id, "")):
        continue
    if row["name"] in EXPLICIT_NAMES:
        name = EXPLICIT_NAMES[row["name"]]
        linked["items_by_id"][item_id] = name
        known[item_id] = name
        is_earring = row["name"].endswith("Earring")
        sources.setdefault("items", {})[item_id] = [{
            "name": name,
            "source": EARRING_SOURCE if is_earring else "project-reviewed direct translation",
            "method": "project-reviewed Chinese name from MHXX reference" if is_earring else "project-reviewed direct translation of the English special-armor name",
            "english": row["name"],
        }]
        translated += 1
        continue
    match = PATTERN.fullmatch(row["name"])
    if not match or match.group(1) not in SERIES:
        continue
    name = SERIES[match.group(1)] + PARTS[match.group(2)]
    if match.group(3):
        name += match.group(3)
    linked["items_by_id"][item_id] = name
    known[item_id] = name
    sources.setdefault("items", {})[item_id] = [{
        "name": name,
        "method": "project-reviewed translation of the explicit English armor-set and armor-part names",
        "english": row["name"],
    }]
    translated += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + "\n")
source_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
print(f"Imported {translated} project-reviewed armor names.")
