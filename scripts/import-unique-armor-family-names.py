#!/usr/bin/env python3
"""Use a unique exact-stat armor-family match to resolve row-level ambiguity."""
from __future__ import annotations

import collections
import json
import re
import sqlite3
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

SLOTS = {"Head": 0, "Body": 1, "Arms": 2, "Waist": 3, "Legs": 4}
GENDER = {0: 1, 1: 2, 2: 0}
PARTS = ("head", "body", "arms", "waist", "legs")

def name_is_chinese(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))

def armor_signature(row: sqlite3.Row) -> tuple:
    signature = (
        row["defense"], row["rarity"], row["num_slots"], row["fire_res"],
        row["water_res"], row["ice_res"], row["thunder_res"], row["dragon_res"],
        SLOTS[row["slot"]], GENDER[row["gender"]], GENDER[row["hunter_type"]],
    )
    # Community data has the correct max-defense figures for blademaster rows.
    # Its gunner pages use the blademaster figure, so omit that one field there.
    return signature + ((row["max_defense"],) if row["hunter_type"] == 0 else ())

def source_signature(row: sqlite3.Row) -> tuple:
    signature = tuple(row[key] for key in (
        "defence", "rare", "slotNum", "fire", "water", "ice", "flash",
        "dragon", "part", "sex", "type",
    ))
    return signature + ((row["maxDefence"],) if row["type"] == 1 else ())

source_groups: dict[tuple[str, int], list[sqlite3.Row]] = collections.defaultdict(list)
for row in CN.execute("SELECT * FROM Equip"):
    source_groups[(row["url"], row["type"])].append(row)
source_counters = {
    key: collections.Counter(source_signature(row) for row in rows)
    for key, rows in source_groups.items()
}

added = 0
for family in DB.execute("SELECT * FROM armor_families ORDER BY _id"):
    members = []
    for part in PARTS:
        item_id = family[f"{part}_id"]
        if not item_id:
            continue
        row = DB.execute(
            "SELECT i._id, i.name, i.rarity, a.* FROM armor a JOIN items i USING(_id) WHERE i._id=?",
            (item_id,),
        ).fetchone()
        if row:
            members.append((part, row))
    missing = [(part, row) for part, row in members if not name_is_chinese(known.get(str(row["_id"]), ""))]
    if not missing:
        continue
    required = collections.Counter(armor_signature(row) for _, row in members)
    group_matches = [
        key for key, available in source_counters.items()
        if not (required - available)
    ]
    if len(group_matches) != 1:
        continue
    key = group_matches[0]
    url, source_type = key
    group_rows = source_groups[key]
    proposed = []
    for part, row in missing:
        expected_part = SLOTS[row["slot"]]
        candidates = [
            source_row for source_row in group_rows
            if source_row["part"] == expected_part
            and source_signature(source_row) == armor_signature(row)
            and name_is_chinese(source_row["name"])
        ]
        names = {candidate["name"] for candidate in candidates}
        if len(names) != 1:
            proposed = []
            break
        proposed.append((row, next(iter(names))))
    if not proposed or len(proposed) != len(missing):
        continue
    for row, name in proposed:
        item_id = str(row["_id"])
        linked["items_by_id"][item_id] = name
        known[item_id] = name
        sources.setdefault("items", {})[item_id] = [{
            "name": name,
            "source": f"jestar719/mhgu:{url}",
            "method": "unique complete armor-family match by all available pieces' exact rarity, defense, slots, resistances, parts, gender, and hunter-type signatures",
            "english": row["name"],
        }]
        added += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + "\n")
source_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
print(f"Imported {added} armor names from uniquely matched armor families.")
