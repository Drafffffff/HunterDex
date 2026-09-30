#!/usr/bin/env python3
"""Import weapon names whose exact stat signature has one Chinese source name."""
from __future__ import annotations

import collections
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/data-sources"
RES = ROOT / "Sources/HunterDex/Resources"
DB = sqlite3.connect(RES / "mhgu.db")
DB.row_factory = sqlite3.Row
CN = sqlite3.connect(CACHE / "jestar-mhgu.db")
linked_path = RES / "linked-localization.json"
source_path = ROOT / "LINKED-LOCALIZATION-SOURCES.json"
linked = json.loads(linked_path.read_text())
sources = json.loads(source_path.read_text())
legacy = json.loads((RES / "localization.json").read_text())
known = {**legacy.get("items_by_id", {}), **linked.get("items_by_id", {})}

TYPES = (
    "Great Sword", "Long Sword", "Sword and Shield", "Dual Blades", "Hammer",
    "Hunting Horn", "Lance", "Gunlance", "Switch Axe", "Charge Blade",
    "Insect Glaive", "Bow", "Light Bowgun", "Heavy Bowgun",
)
SOURCE_TYPES = {
    "Great Sword": "大剑", "Long Sword": "太刀", "Sword and Shield": "片手剑",
    "Dual Blades": "双剑", "Hammer": "大锤", "Hunting Horn": "狩猎笛",
    "Lance": "长枪", "Gunlance": "铳枪", "Switch Axe": "斩击斧",
    "Charge Blade": "盾斧", "Insect Glaive": "操虫棍", "Bow": "弓",
    "Light Bowgun": "轻弩", "Heavy Bowgun": "重弩",
}
ELEMENTS = {
    "Fire": "火", "Water": "水", "Thunder": "雷", "Ice": "冰", "Dragon": "龙",
    "Poison": "毒", "Paralysis": "麻痹", "Sleep": "睡眠",
    "Blastblight": "爆破", "Blast": "爆破",
}

def normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()

def chinese_name(text: str) -> str | None:
    text = normalized(text)
    text = re.sub(r"\[(?:生产G?|生产|购入|購入|XX|生産G?|终|最終)\]", "", text).strip()
    # Keep the Chinese middle-dot separator while rejecting Japanese kana.
    if re.search(r"[\u3040-\u309f\u30a0-\u30fa\u30fc-\u30ff]", text):
        return None
    return text if re.search(r"[\u3400-\u9fff]", text) else None

def database_signature(row: sqlite3.Row) -> tuple:
    sharp = tuple(map(int, (row["sharpness"] or "").split()[0].split("."))) if row["sharpness"] else ()
    elements = tuple(sorted(
        (ELEMENTS.get(row[key], row[key]), row[value])
        for key, value in (("element", "element_attack"), ("element_2", "element_2_attack"))
        if row[key]
    ))
    return row["attack"], row["num_slots"], str(row["affinity"]), elements, sharp, row["defense"] or 0

def source_groups(paths: list[Path], kind: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for path in paths:
        if not path.exists():
            continue
        soup = BeautifulSoup(path.read_text(), "html.parser")
        # Base and G-rank pages use #sorter, while the final-upgrade index
        # uses #sorter0. Both tables contain the same row-stat columns.
        table = soup.select_one("table[id^=sorter]")
        if not table:
            continue
        for tr in table.select(":scope > tbody > tr"):
            cells = tr.find_all("td", recursive=False)
            if len(cells) < 5:
                continue
            first = cells[0]
            button = first.select_one(".panel_btn")
            ids = re.findall(r"a_cl(\d+)", " ".join(tr.get("class", [])))
            group = ids[0] if ids else (re.search(r"id(\d+)", button.get("id", "")).group(1) if button else None)
            if not group:
                continue
            ranged = kind in ("Light Bowgun", "Heavy Bowgun")
            bow = kind == "Bow"
            final_layout = len(cells) >= 6 and path.stem.startswith("27")
            if final_layout:
                # Final-upgrade index columns include an expected-value column
                # absent from the per-rank pages.
                stat = cells[2] if ranged else cells[3]
                attack_text = cells[2].get_text(" ", strip=True) if ranged else cells[2].get_text(strip=True)
                attack_match = re.search(r"(?:攻击[：:]?\s*)?(\d+)", attack_text)
                if not attack_match:
                    continue
                attack = int(attack_match.group(1))
            else:
                stat = cells[1] if ranged else cells[2]
                attack = int(cells[1].select_one(".b").get_text()) if ranged else int(cells[1].get_text(strip=True))
            stat_text = normalized(stat.get_text(" ", strip=True))
            affinity = re.search(r"会心\s*([\d+\-]+)\s*%", stat_text)
            affinity_value = str(int(affinity.group(1))) if affinity else "0"
            defense = re.search(r"防[御禦]?\s*[+:]?\s*(\d+)", stat_text)
            defense_value = int(defense.group(1)) if defense else 0
            elements = []
            for element in stat.select("[class*=type_]"):
                match = re.search(r"(火|水|雷|冰|氷|龙|龍|毒|麻痹|麻痺|睡眠|爆破)\s*(\d+)", normalized(element.get_text()))
                if match:
                    name = {"氷": "冰", "龍": "龙", "麻痺": "麻痹"}.get(match.group(1), match.group(1))
                    elements.append((name, int(match.group(2))))
            sharp_cell = cells[4] if final_layout and not (ranged or bow) else (cells[3] if not (ranged or bow) else None)
            sharp = tuple(len(tr.select_one(f".kr{index}").get_text()) for index in range(7)) if sharp_cell and tr.select_one(".kr0") else ()
            slot_text = (cells[2] if ranged else cells[5] if not bow else cells[6]).get_text() if final_layout else (cells[1].get_text() if ranged else cells[-1].get_text())
            slots = slot_text.count("◯") + slot_text.count("○")
            for element in first.select(".hasei,.panel_btn,.c_g,.c_r,.c_p"):
                element.decompose()
            name = normalized("".join(first.stripped_strings))
            groups[group].append({
                "name": name,
                "signature": (attack, slots, affinity_value, tuple(sorted(elements)), sharp, defense_value),
                "page": path.name,
                "group": group,
            })
    return groups

added = 0
for index, kind in enumerate(TYPES):
    paths = [CACHE / "jestar/data" / f"{1900 + index}.html"]
    if index not in (9, 10):
        paths.append(CACHE / "jestar/data" / f"{2882 + index}.html")
    final_page = CN.execute(
        "SELECT child.url FROM IndexBean parent JOIN IndexBean child ON child.parent=parent.id "
        "WHERE parent.type=1 AND parent.name=? AND child.name IN ('最终', '最終') "
        "AND child.url IS NOT NULL LIMIT 1",
        (SOURCE_TYPES[kind],),
    ).fetchone()
    if final_page:
        paths.append(CACHE / "jestar" / final_page[0])
    wiki = source_groups(paths, kind)
    source_names: dict[tuple, set[str]] = collections.defaultdict(set)
    source_groups_by_signature: dict[tuple, set[str]] = collections.defaultdict(set)
    native: dict[tuple, list[sqlite3.Row]] = collections.defaultdict(list)
    for group, rows in wiki.items():
        for row in rows:
            source_names[row["signature"]].add(row["name"])
            source_groups_by_signature[row["signature"]].add(group)
    for row in DB.execute(
        "SELECT i._id, i.name, w.* FROM weapons w JOIN items i USING(_id) WHERE wtype=? ORDER BY w._id",
        (kind,),
    ):
        native[database_signature(row)].append(row)
    for signature, rows in native.items():
        if len(rows) != 1:
            continue
        row = rows[0]
        item_id = str(row["_id"])
        if re.search(r"[\u3400-\u9fff]", known.get(item_id, "")):
            continue
        candidates = {chinese_name(name) for name in source_names.get(signature, ())}
        candidates.discard(None)
        if len(candidates) != 1:
            continue
        level_match = re.search(r"(\d+)$", row["name"])
        if not level_match:
            continue
        level = int(level_match.group(1))
        name = next(iter(candidates))
        if name.endswith(str(level)):
            name = name[:-len(str(level))].rstrip()
        translation = f"{name} Lv.{level}"
        linked["items_by_id"][item_id] = translation
        known[item_id] = translation
        source_group = sorted(source_groups_by_signature[signature])[0]
        sources.setdefault("items", {})[item_id] = [{
            "name": translation,
            "source": f"jestar719/mhgu:ida/{source_group}.html",
            "method": "unique exact attack, slots, affinity, elements, sharpness, and defense signature in both databases",
            "english": row["name"],
        }]
        added += 1

    # Exact signatures can repeat across otherwise distinct weapons. Match
    # the complete Chinese upgrade row to the native parent-child chain so a
    # repeated single-row signature is never resolved by itself.
    native_by_id = {
        str(row["_id"]): row
        for rows in native.values()
        for row in rows
    }
    children: dict[str, list[str]] = collections.defaultdict(list)
    for item_id, row in native_by_id.items():
        if row["parent_id"]:
            children[str(row["parent_id"])].append(item_id)

    chain_proposals: dict[str, list[dict]] = collections.defaultdict(list)
    for source_group, source_rows_in_chain in wiki.items():
        if not source_rows_in_chain:
            continue
        paths = [
            [str(row["_id"])]
            for row in native.get(source_rows_in_chain[0]["signature"], [])
        ]
        for source_row in source_rows_in_chain[1:]:
            next_paths = []
            for path in paths:
                for child_id in children.get(path[-1], []):
                    if database_signature(native_by_id[child_id]) == source_row["signature"]:
                        next_paths.append(path + [child_id])
            paths = next_paths
            if not paths:
                break
        unique_paths = {tuple(path) for path in paths}
        if len(unique_paths) != 1:
            continue
        path = next(iter(unique_paths))
        for source_row, item_id in zip(source_rows_in_chain, path):
            if re.search(r"[\u3400-\u9fff]", known.get(item_id, "")):
                continue
            level_match = re.search(r"(\d+)$", native_by_id[item_id]["name"])
            source_name = chinese_name(source_row["name"])
            if not level_match or not source_name:
                continue
            level = int(level_match.group(1))
            if source_name.endswith(str(level)):
                source_name = source_name[:-len(str(level))].rstrip()
            chain_proposals[item_id].append({
                "name": f"{source_name} Lv.{level}",
                "group": source_group,
                "english": native_by_id[item_id]["name"],
            })

    for item_id, proposals in chain_proposals.items():
        translations = {proposal["name"] for proposal in proposals}
        if len(translations) != 1:
            continue
        translation = next(iter(translations))
        linked["items_by_id"][item_id] = translation
        known[item_id] = translation
        evidence = proposals[0]
        sources.setdefault("items", {})[item_id] = [{
            "name": translation,
            "source": f"jestar719/mhgu:ida/{evidence['group']}.html",
            "method": "unique full upgrade-chain match by ordered attack, slots, affinity, elements, sharpness, and defense signatures",
            "english": evidence["english"],
        }]
        added += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + "\n")
source_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
print(f"Imported {added} uniquely matched weapon names.")
