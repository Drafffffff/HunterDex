#!/usr/bin/env python3
"""Import armor names with a unique exact-stat match in the Chinese community DB."""
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
base = json.loads((RES / "zh.json").read_text())
known = {**base.get("items_by_id", {}), **legacy.get("items_by_id", {}), **linked.get("items_by_id", {})}

def clean_name(value: str) -> str | None:
    value = unicodedata.normalize("NFKC", value).strip()
    value = re.sub(r"\[(?:生产G?|生产|购入|購入|XX|生産G?|终|最終)\]", "", value).strip()
    # Exclude Japanese kana, but keep the middle-dot separator (・) that is
    # common in Chinese armor names such as 结云之笠・天.
    if re.search(r"[\u3040-\u309f\u30a0-\u30fa\u30fc-\u30ff]", value):
        return None
    return value if re.search(r"[\u3400-\u9fff]", value) else None

lookup: dict[tuple, list[sqlite3.Row]] = collections.defaultdict(list)
for row in CN.execute("SELECT * FROM Equip"):
    sig = tuple(row[k] for k in (
        "defence", "rare", "slotNum", "fire", "water", "ice", "flash",
        "dragon", "part",
    ))
    lookup[sig].append(row)

slot_index = {"Head": 0, "Body": 1, "Arms": 2, "Waist": 3, "Legs": 4}
source_gender = {0: 2, 1: 1, 2: 0}
source_type = {0: 1, 1: 2, 2: 0}
added = 0
for row in DB.execute("SELECT i._id, i.name, i.rarity, a.* FROM armor a JOIN items i USING(_id)"):
    item_id = str(row["_id"])
    if re.search(r"[\u3400-\u9fff]", known.get(item_id, "")):
        continue
    sig = tuple(row[k] for k in (
        "defense", "rarity", "num_slots", "fire_res", "water_res", "ice_res",
        "thunder_res", "dragon_res",
    )) + (slot_index[row["slot"]],)
    genders = {source_gender[row["gender"]]}
    types = {source_type[row["hunter_type"]]}
    if row["gender"] in (0, 1):
        genders.add(0)
    if row["hunter_type"] in (0, 1):
        types.add(0)
    candidates = [
        candidate for candidate in lookup.get(sig, [])
        if candidate["sex"] in genders and candidate["type"] in types
    ]
    # The Chinese source lists bowgun armor with its corresponding blademaster
    # max-defense value, while this database stores the lower gunner value.
    # Keep the max-defense check for blademaster rows; all other stats remain
    # exact for gunner rows and the resulting Chinese name must still be unique.
    if row["hunter_type"] == 0:
        candidates = [candidate for candidate in candidates if candidate["maxDefence"] == row["max_defense"]]
    names = {clean_name(candidate["name"]) for candidate in candidates}
    names.discard(None)
    if len(names) != 1:
        continue
    name = next(iter(names))
    source = next(candidate["url"] for candidate in candidates if clean_name(candidate["name"]) == name)
    linked["items_by_id"][item_id] = name
    sources.setdefault("items", {})[item_id] = [{
        "name": name,
        "source": f"jestar719/mhgu:{source}",
        "method": "unique exact defense, rarity, slots, resistances, and part match, with exact or explicitly unrestricted gender and hunter type; max-defense also matched for blademaster",
        "english": row["name"],
    }]
    known[item_id] = name
    added += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + "\n")
source_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
print(f"Imported {added} uniquely matched armor names.")
