#!/usr/bin/env python3
"""Resolve remaining armor names by reviewed series terms and unique source metadata."""
from __future__ import annotations

import collections
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "Sources/HunterDex/Resources"
DB = sqlite3.connect(RES / "mhgu.db")
DB.row_factory = sqlite3.Row
CN = sqlite3.connect(ROOT / ".cache/data-sources/jestar-mhgu.db")
CN.row_factory = sqlite3.Row
linked_path = RES / "linked-localization.json"
source_path = ROOT / "LINKED-LOCALIZATION-SOURCES.json"
linked = json.loads(linked_path.read_text())
sources = json.loads(source_path.read_text())
legacy = json.loads((RES / "localization.json").read_text())
known = {**legacy.get("items_by_id", {}), **linked.get("items_by_id", {})}

# Series terms are attested by the Chinese community equipment index. Matching
# still requires exact rarity and database armor slot. The community data
# explicitly marks unrestricted hunter types and genders with 0; those rows
# may match a restricted entry only when the final series-prefixed name is
# unique across all exact and unrestricted candidates.
SERIES = {
    "Mosgharl": "南瓜",
    "Guild Bard": "公会诗人",
    "Blue Guild": "工会守卫蓝",
    "Red Guild": "工会守卫红",
    "Gourmew": "美食喵",
    "Sailor": "水手",
    "Guild Knight": "工会骑士",
    "Scholar's": "学士",
    "Scholar's Blouse": "学士",
    "Maiden's": "女仆",
    "French Maid": "休闲",
    "Helper": "支援者",
    "Healer": "治疗者",
    "Dianthus": "抚子",
    "Campanile": "桔梗",
    "Hawk": "猎鹰",
    # The community database splits several Hawk-set names into joined words.
    "Hawkhat": "猎鹰",
    "Hawksuit": "猎鹰",
    "Hawkbraces": "猎鹰",
    "Hawkcap": "猎鹰",
    "Hawkjacket": "猎鹰",
    "Hawkboots": "猎鹰",
    "Hawkguards": "猎鹰",
    "Hawkfeet": "猎鹰",
    "Hawkcoil": "猎鹰",
    "Hawkcoat": "猎鹰",
    "G. Knight": "公会骑士",
    "Barmaid's": "酒保",
    "Barman's": "酒保",
    "Mariner": "水手",
    "Lecturer's": "求知",
}
SLOT = {"Head": 0, "Body": 1, "Arms": 2, "Waist": 3, "Legs": 4}
# MHGenDatabase encodes gender as female=0, male=1, unrestricted=2;
# the community index uses male=1, female=2, unrestricted=0.
SOURCE_GENDER = {0: 2, 1: 1, 2: 0}
SOURCE_TYPE = {0: 1, 1: 2, 2: 0}
# Community skill names use a few different Chinese labels from this project's
# source database. These explicit correspondences let matching skill point
# signatures distinguish same-rarity S/U or X/Z support sets.
SOURCE_SKILLS = {
    "广域": "Wide-Range",
    "回复量": "Rec Level",
    "重击": "Destroyer",
    "观察眼": "Perception",
    "千里眼": "Psychic",
    "食菇": "Mushroom",
    "野草知识": "Herbal Lore",
    "ＳＰ持续": "Prolong SP",
}

def norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()

source_rows: dict[tuple[int, int, int, int], list[sqlite3.Row]] = collections.defaultdict(list)
source_skills: dict[int, list[tuple[str, int]]] = collections.defaultdict(list)
for row in CN.execute("SELECT * FROM Equip"):
    source_rows[(row["rare"], row["part"], row["type"], row["sex"])].append(row)
for row in CN.execute("SELECT equipId, name, value FROM EquipSkill"):
    source_skills[row["equipId"]].append((row["name"], row["value"]))

added = 0
for row in DB.execute(
    "SELECT i._id, i.name, i.rarity, a.* FROM armor a JOIN items i USING(_id) ORDER BY i._id"
):
    item_id = str(row["_id"])
    if re.search(r"[\u3400-\u9fff]", known.get(item_id, "")):
        continue
    en = norm(row["name"])
    series = next((prefix for prefix in sorted(SERIES, key=len, reverse=True)
                   if en == prefix or en.startswith(prefix + " ")), None)
    if not series:
        continue
    # Use the database's authoritative armor slot instead of inferring it
    # from English part-name vocabulary. The localized candidate must still
    # be unique within exact rarity, slot, hunter type, and gender.
    part = SLOT[row["slot"]]
    source_types = {SOURCE_TYPE[row["hunter_type"]]}
    source_genders = {SOURCE_GENDER[row["gender"]]}
    if row["hunter_type"] in (0, 1):
        source_types.add(0)
    if row["gender"] in (0, 1):
        source_genders.add(0)
    candidates = [
        candidate
        for source_type in source_types
        for source_gender in source_genders
        for candidate in source_rows[(row["rarity"], part, source_type, source_gender)]
    ]
    candidates = [candidate for candidate in candidates if norm(candidate["name"]).startswith(SERIES[series])]
    names = {candidate["name"] for candidate in candidates}
    if len(names) != 1:
        native_skills = {
            (skill["name"], skill["point_value"])
            for skill in DB.execute(
                "SELECT st.name, its.point_value FROM item_to_skill_tree its "
                "JOIN skill_trees st ON st._id=its.skill_tree_id WHERE its.item_id=?",
                (row["_id"],),
            )
        }
        # Use skill-based disambiguation only when every candidate in this
        # reviewed series family has a fully mapped source signature.
        if not candidates or not native_skills or any(
            any(name not in SOURCE_SKILLS for name, _ in source_skills[candidate["id"]])
            for candidate in candidates
        ):
            continue
        matched = [
            candidate for candidate in candidates
            if {
                (SOURCE_SKILLS[name], value)
                for name, value in source_skills[candidate["id"]]
            } == native_skills
        ]
        matched_names = {candidate["name"] for candidate in matched}
        if len(matched_names) != 1:
            continue
        candidates = matched
        names = matched_names
    name = next(iter(names))
    evidence = next(candidate for candidate in candidates if candidate["name"] == name)
    linked["items_by_id"][item_id] = name
    known[item_id] = name
    sources.setdefault("items", {})[item_id] = [{
        "name": name,
        "source": f"jestar719/mhgu:{evidence['url']}",
        "method": "unique Chinese series-prefix / exact rarity / database armor slot; exact or explicitly unrestricted gender and hunter-type match",
        "english": row["name"],
    }]
    added += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + "\n")
source_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
print(f"Imported {added} uniquely matched armor names from reviewed series terms.")
