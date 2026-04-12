#!/usr/bin/env python3
"""
lookup.py — query local 5e SRD data files during play

Searches the locally cached JSON datasets for monsters, spells, magic items,
conditions, and equipment. Returns a concise DM-readable summary.

Usage:
    python3 lookup.py monster "goblin"
    python3 lookup.py spell "fireball"
    python3 lookup.py item "longsword"          # searches equipment + magic items
    python3 lookup.py condition "poisoned"
    python3 lookup.py equipment "explorer's pack"

Flags:
    --json      dump full raw JSON for the match (for scripting)
    --all       show all fuzzy matches, not just the best one
"""

import json
import os
import sys
from typing import Optional

DATA_DIR = os.path.expanduser("~/.claude/skills/dnd/data")

FILE_MAP = {
    "monster":   "5e-SRD-Monsters.json",
    "monsters":  "5e-SRD-Monsters.json",
    "spell":     "5e-SRD-Spells.json",
    "spells":    "5e-SRD-Spells.json",
    "magic_item": "5e-SRD-Magic-Items.json",
    "magic":     "5e-SRD-Magic-Items.json",
    "condition": "5e-SRD-Conditions.json",
    "conditions":"5e-SRD-Conditions.json",
    "equipment": "5e-SRD-Equipment.json",
    "gear":      "5e-SRD-Equipment.json",
    # "item" searches both equipment and magic items (see special handling)
    "item":      None,
    "items":     None,
}


# ─── Loaders ─────────────────────────────────────────────────────────────────

_cache: dict[str, list] = {}

def _load(filename: str) -> list:
    if filename in _cache:
        return _cache[filename]
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    # The 5e-bits format is either a top-level array or {"results": [...]}
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("results", list(data.values())[0] if data else [])
    else:
        records = []
    _cache[filename] = records
    return records


# ─── Matching ────────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    return s.lower().replace("-", " ").replace("_", " ").strip()


def _score(query: str, record: dict) -> int:
    """Simple match score: 3=exact, 2=starts-with, 1=contains, 0=no match."""
    name = _normalize(record.get("name", ""))
    idx  = _normalize(record.get("index", ""))
    q    = _normalize(query)
    if name == q or idx == q:
        return 3
    if name.startswith(q) or idx.startswith(q):
        return 2
    if q in name or q in idx:
        return 1
    return 0


def _find(query: str, records: list, top_n: int = 1) -> list[dict]:
    scored = [(r, _score(query, r)) for r in records]
    scored = [(r, s) for r, s in scored if s > 0]
    scored.sort(key=lambda x: (-x[1], x[0].get("name", "")))
    return [r for r, _ in scored[:top_n]]


# ─── Formatters ──────────────────────────────────────────────────────────────

def _fmt_monster(m: dict) -> str:
    lines = []
    cr    = m.get("challenge_rating", "?")
    xp    = m.get("xp", "?")
    lines.append(f"## {m.get('name', '?')}  [CR {cr} | {xp} XP]")
    lines.append(
        f"{m.get('size','?')} {m.get('type','?')}  ·  "
        f"Align: {m.get('alignment','?')}"
    )
    lines.append("")

    # AC
    ac_list = m.get("armor_class", [])
    if isinstance(ac_list, list) and ac_list:
        ac_entry = ac_list[0]
        ac_val   = ac_entry.get("value", "?") if isinstance(ac_entry, dict) else ac_entry
        ac_type  = ac_entry.get("type", "") if isinstance(ac_entry, dict) else ""
        lines.append(f"AC {ac_val}" + (f" ({ac_type})" if ac_type else ""))
    elif isinstance(ac_list, (int, float)):
        lines.append(f"AC {ac_list}")

    lines.append(
        f"HP {m.get('hit_points','?')} ({m.get('hit_dice','?')})"
    )

    speed = m.get("speed", {})
    if isinstance(speed, dict):
        speed_parts = [f"{k} {v}" for k, v in speed.items() if v]
        lines.append("Speed: " + ", ".join(speed_parts))
    lines.append("")

    # Ability scores
    stats = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    abbr  = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    row1  = " | ".join(f"{a:3}" for a in abbr)
    row2  = " | ".join(
        f"{m.get(s,0):3}" + f"({(m.get(s,10)-10)//2:+d})" for s, _ in zip(stats, abbr)
    )
    lines.append(row1)
    lines.append(row2)
    lines.append("")

    # Proficiencies (saving throws + skills)
    profs = m.get("proficiencies", [])
    saves  = [p for p in profs if "saving" in p.get("proficiency", {}).get("name","").lower()]
    skills = [p for p in profs if "skill" in p.get("proficiency", {}).get("name","").lower()]
    if saves:
        sv = ", ".join(
            f"{p['proficiency']['name'].replace('Saving Throw: ','')}: +{p['value']}"
            for p in saves
        )
        lines.append(f"Saves: {sv}")
    if skills:
        sk = ", ".join(
            f"{p['proficiency']['name'].replace('Skill: ','')}: +{p['value']}"
            for p in skills
        )
        lines.append(f"Skills: {sk}")

    # Immunities / resistances
    di = m.get("damage_immunities", [])
    dr = m.get("damage_resistances", [])
    dv = m.get("damage_vulnerabilities", [])
    ci = [c.get("name","") for c in m.get("condition_immunities", [])]
    if di: lines.append(f"Immune: {', '.join(di)}")
    if dr: lines.append(f"Resist: {', '.join(dr)}")
    if dv: lines.append(f"Vulnerable: {', '.join(dv)}")
    if ci: lines.append(f"Condition immune: {', '.join(ci)}")

    # Senses / Languages
    senses = m.get("senses", {})
    if senses:
        s = ", ".join(f"{k} {v}" for k, v in senses.items() if v)
        lines.append(f"Senses: {s}")
    langs = m.get("languages", "")
    if langs: lines.append(f"Languages: {langs}")
    lines.append("")

    # Special abilities
    specials = m.get("special_abilities", [])
    if specials:
        lines.append("**Special Abilities**")
        for sa in specials:
            desc = (sa.get("desc","") or "").split(".")[0] + "."
            lines.append(f"  {sa.get('name','')}. {desc}")
        lines.append("")

    # Actions
    actions = m.get("actions", [])
    if actions:
        lines.append("**Actions**")
        for a in actions:
            name = a.get("name","")
            desc = (a.get("desc","") or "").strip()
            lines.append(f"  {name}. {desc}")
        lines.append("")

    # Legendary actions
    leg = m.get("legendary_actions", [])
    if leg:
        lines.append("**Legendary Actions**")
        for a in leg:
            lines.append(f"  {a.get('name','')}. {(a.get('desc','') or '').strip()}")

    return "\n".join(lines)


def _fmt_spell(s: dict) -> str:
    lines = []
    lvl    = s.get("level", 0)
    school = s.get("school", {})
    school_name = school.get("name","?") if isinstance(school, dict) else school
    level_str = "Cantrip" if lvl == 0 else f"Level {lvl}"
    lines.append(f"## {s.get('name','?')}  [{level_str} {school_name}]")
    lines.append("")

    comp = s.get("components", [])
    mat  = s.get("material","")
    comp_str = ", ".join(comp)
    if "M" in comp and mat:
        comp_str += f" ({mat})"

    lines.append(f"Casting time : {s.get('casting_time','?')}")
    lines.append(f"Range        : {s.get('range','?')}")
    lines.append(f"Components   : {comp_str}")
    lines.append(f"Duration     : {s.get('duration','?')}")
    conc = s.get("concentration", False)
    if conc:
        lines[-1] += "  *(concentration)*"
    lines.append(f"Ritual       : {'Yes' if s.get('ritual') else 'No'}")
    lines.append("")

    classes = s.get("classes", [])
    if classes:
        cnames = [c.get("name","") if isinstance(c,dict) else c for c in classes]
        lines.append(f"Classes: {', '.join(cnames)}")
        lines.append("")

    desc = s.get("desc", [])
    if isinstance(desc, list):
        lines.extend(desc)
    else:
        lines.append(str(desc))

    higher = s.get("higher_level", [])
    if higher:
        lines.append("")
        lines.append("**At Higher Levels:**")
        if isinstance(higher, list):
            lines.extend(higher)
        else:
            lines.append(str(higher))

    return "\n".join(lines)


def _fmt_condition(c: dict) -> str:
    lines = [f"## {c.get('name','?')}"]
    lines.append("")
    desc = c.get("desc", [])
    if isinstance(desc, list):
        for d in desc:
            lines.append(f"  • {d}")
    else:
        lines.append(str(desc))
    return "\n".join(lines)


def _fmt_equipment(e: dict) -> str:
    lines = []
    cat = e.get("equipment_category", {})
    cat_name = cat.get("name","") if isinstance(cat, dict) else str(cat)
    lines.append(f"## {e.get('name','?')}  [{cat_name}]")
    lines.append("")

    cost = e.get("cost", {})
    if isinstance(cost, dict):
        lines.append(f"Cost   : {cost.get('quantity','?')} {cost.get('unit','?')}")
    weight = e.get("weight")
    if weight is not None:
        lines.append(f"Weight : {weight} lb")

    # Weapon stats
    dmg = e.get("damage", {})
    if dmg:
        dice = dmg.get("damage_dice","")
        dtype = dmg.get("damage_type",{})
        dtype_name = dtype.get("name","") if isinstance(dtype, dict) else str(dtype)
        lines.append(f"Damage : {dice} {dtype_name}")
    two_h = e.get("two_handed_damage", {})
    if two_h:
        lines.append(f"2H dmg : {two_h.get('damage_dice','')} {two_h.get('damage_type',{}).get('name','')}")

    bonus = e.get("attack_bonus")
    if bonus is not None:
        lines.append(f"Atk bonus: +{bonus}")

    # Armour
    ac = e.get("armor_class", {})
    if ac:
        base = ac.get("base","")
        dex  = ac.get("dex_bonus", False)
        max_b= ac.get("max_bonus")
        ac_str = f"AC {base}"
        if dex:
            ac_str += " + DEX"
            if max_b is not None:
                ac_str += f" (max +{max_b})"
        lines.append(ac_str)
    stealth = e.get("stealth_disadvantage")
    if stealth:
        lines.append("Stealth: disadvantage")
    str_min = e.get("str_minimum")
    if str_min:
        lines.append(f"Str minimum: {str_min}")

    # Properties
    props = e.get("properties", [])
    if props:
        pnames = [p.get("name","") if isinstance(p,dict) else str(p) for p in props]
        lines.append(f"Properties: {', '.join(pnames)}")

    # Range
    rng = e.get("range", {})
    throw_rng = e.get("throw_range", {})
    if rng and (rng.get("normal") or rng.get("long")):
        lines.append(f"Range : {rng.get('normal','?')}/{rng.get('long','?')} ft")
    if throw_rng:
        lines.append(f"Throw : {throw_rng.get('normal','?')}/{throw_rng.get('long','?')} ft")

    # Gear contents
    contents = e.get("contents", [])
    if contents:
        lines.append("")
        lines.append("Contents:")
        for item in contents:
            qty = item.get("quantity","")
            iname = item.get("item",{}).get("name","?") if isinstance(item.get("item"),dict) else ""
            lines.append(f"  × {qty} {iname}")

    # Description (for misc items)
    desc = e.get("desc", [])
    if desc:
        lines.append("")
        if isinstance(desc, list):
            lines.extend(desc)
        else:
            lines.append(str(desc))

    return "\n".join(lines)


def _fmt_magic_item(m: dict) -> str:
    lines = []
    rarity = m.get("rarity", {})
    rarity_name = rarity.get("name","?") if isinstance(rarity, dict) else str(rarity)
    cat = m.get("equipment_category", {})
    cat_name = cat.get("name","") if isinstance(cat, dict) else str(cat)
    lines.append(f"## {m.get('name','?')}  [{rarity_name} {cat_name}]")
    lines.append("")
    desc = m.get("desc", [])
    if isinstance(desc, list):
        lines.extend(desc)
    else:
        lines.append(str(desc))
    return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────────────────────

FORMATTERS = {
    "5e-SRD-Monsters.json":    _fmt_monster,
    "5e-SRD-Spells.json":      _fmt_spell,
    "5e-SRD-Conditions.json":  _fmt_condition,
    "5e-SRD-Equipment.json":   _fmt_equipment,
    "5e-SRD-Magic-Items.json": _fmt_magic_item,
}


def _search_file(filename: str, query: str, top_n: int) -> list[tuple[dict, str]]:
    """Returns list of (record, filename) tuples."""
    records = _load(filename)
    if not records:
        return []
    matches = _find(query, records, top_n)
    return [(m, filename) for m in matches]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    dump_json = "--json" in flags
    show_all  = "--all"  in flags
    top_n     = 10 if show_all else 1

    if len(args) < 2:
        print(__doc__)
        sys.exit(0)

    category = args[0].lower()
    query    = " ".join(args[1:])

    # Special case: "item" searches both equipment and magic items
    if category in ("item", "items"):
        results = (
            _search_file("5e-SRD-Equipment.json",   query, top_n) +
            _search_file("5e-SRD-Magic-Items.json", query, top_n)
        )
        results.sort(key=lambda x: -_score(query, x[0]))
        results = results[:top_n]
    else:
        filename = FILE_MAP.get(category)
        if not filename:
            print(f"Unknown category '{category}'. Use: monster, spell, item, condition, equipment")
            sys.exit(1)
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(
                f"Data file not found: {path}\n"
                f"Run `python3 ~/.claude/skills/dnd/scripts/data_pull.py` first."
            )
            sys.exit(1)
        results = _search_file(filename, query, top_n)

    if not results:
        print(f"No match for '{query}' in {category}.")
        sys.exit(0)

    for record, filename in results:
        if dump_json:
            print(json.dumps(record, indent=2))
        else:
            fmt = FORMATTERS.get(filename, lambda r: json.dumps(r, indent=2))
            print(fmt(record))
            print()


if __name__ == "__main__":
    main()
