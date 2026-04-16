#!/usr/bin/env python3
"""
lookup.py — query the bundled dnd5e_srd.json dataset during play

Usage (CLI):
    python3 lookup.py spell "healing word"
    python3 lookup.py item "rapier"
    python3 lookup.py feature "cunning action"
    python3 lookup.py condition "poisoned"
    python3 lookup.py monster "goblin"
    python3 lookup.py <any> "name"       # search across all categories

Flags:
    --all   show all fuzzy matches, not just the best
    --json  dump full raw record as JSON

Programmatic import (used by app.py):
    from lookup import lookup, lookup_record
    text = lookup("healing word", category="spell")   # → formatted string | None
    rec  = lookup_record("rapier", category="item")   # → dict | None
"""

import json
import os
import re
import sys

DATA_FILE        = os.path.expanduser("~/.claude/skills/dnd/data/dnd5e_srd.json")
SUPPLEMENTAL_FILE = os.path.expanduser("~/.claude/skills/dnd/data/dnd5e_supplemental.json")

# Category aliases → canonical dataset key
CATEGORY_MAP = {
    "spell":       "spells",
    "spells":      "spells",
    "equipment":   "equipment",
    "gear":        "equipment",
    "magic_item":  "magic_items",
    "magic":       "magic_items",
    "magic_items": "magic_items",
    "item":        None,   # searches equipment + magic_items
    "items":       None,
    "condition":   "conditions",
    "conditions":  "conditions",
    "monster":     "monsters",
    "monsters":    "monsters",
    "feature":     "features",
    "features":    "features",
    "feat":        "features",
}

ALL_CATEGORIES = ["spells", "equipment", "magic_items", "conditions", "monsters", "features"]

# ─── Data loading / index ─────────────────────────────────────────────────────

_data: dict = {}          # raw dataset keyed by category (SRD + supplemental merged)
_index: dict = {}         # {category: {normalized_name: record}}
_loaded = False


def _load() -> None:
    global _data, _index, _loaded
    if _loaded:
        return

    _data = {}

    # Load primary SRD
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            raw = json.load(f)
        for k, v in raw.items():
            if k != "_meta":
                _data[k] = list(v)  # copy so we can safely extend

    # Merge supplemental (non-SRD content) — adds without overwriting SRD entries
    if os.path.exists(SUPPLEMENTAL_FILE):
        with open(SUPPLEMENTAL_FILE) as f:
            supp = json.load(f)
        for k, v in supp.items():
            if k == "_meta":
                continue
            existing_names = {_norm(r.get("name", "")) for r in _data.get(k, [])}
            for r in v:
                if _norm(r.get("name", "")) not in existing_names:
                    _data.setdefault(k, []).append(r)

    _index = {}
    for cat, records in _data.items():
        idx = {}
        for r in records:
            name = r.get("name", "")
            key  = _norm(name)
            idx[key] = r
            if r.get("index") and r["index"] != key:
                idx[r["index"]] = r
        _index[cat] = idx
    _loaded = True


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ─── Matching ─────────────────────────────────────────────────────────────────

def _score(query: str, record: dict) -> int:
    """3=exact, 2=starts-with, 1=contains, 0=no match."""
    q    = _norm(query)
    name = _norm(record.get("name", ""))
    idx  = record.get("index", "")
    if name == q or idx == q:
        return 3
    if name.startswith(q) or idx.startswith(q):
        return 2
    if q in name or q in idx:
        return 1
    return 0


def _find(query: str, records: list, top_n: int = 1):
    scored = [(r, _score(query, r)) for r in records]
    scored = [(r, s) for r, s in scored if s > 0]
    scored.sort(key=lambda x: (-x[1], x[0].get("name", "")))
    return [r for r, _ in scored[:top_n]]


def _get_records(cat_key):
    """Return all records for a category key. None → equipment + magic_items."""
    _load()
    if cat_key is None:
        return _data.get("equipment", []) + _data.get("magic_items", [])
    return _data.get(cat_key, [])


# ─── Formatters ───────────────────────────────────────────────────────────────

def _fmt_spell(r: dict) -> str:
    lvl    = r.get("level", 0)
    school = r.get("school", "")
    lvl_s  = "Cantrip" if lvl == 0 else f"Level {lvl}"
    lines  = [f"## {r.get('name','?')}  [{lvl_s} {school}]", ""]
    comp   = ", ".join(r.get("components", []))
    if "M" in r.get("components", []) and r.get("material"):
        comp += f" ({r['material']})"
    lines += [
        f"Casting time : {r.get('casting_time','')}",
        f"Range        : {r.get('range','')}",
        f"Components   : {comp}",
        f"Duration     : {r.get('duration','')}"
        + ("  *(concentration)*" if r.get("concentration") else ""),
        f"Ritual       : {'Yes' if r.get('ritual') else 'No'}",
    ]
    classes = r.get("classes", [])
    if classes:
        lines += ["", f"Classes: {', '.join(classes)}"]
    desc = r.get("description", "")
    if desc:
        lines += ["", desc]
    hl = r.get("higher_level", "")
    if hl:
        lines += ["", "**At Higher Levels:**", hl]
    return "\n".join(lines)


def _fmt_equipment(r: dict) -> str:
    lines = [f"## {r.get('name','?')}  [{r.get('category','')}]", ""]
    if r.get("cost"):
        lines.append(f"Cost       : {r['cost']}")
    if r.get("weight") is not None:
        lines.append(f"Weight     : {r['weight']} lb")
    if r.get("damage"):
        lines.append(f"Damage     : {r['damage']}")
    if r.get("damage_2h"):
        lines.append(f"2H Damage  : {r['damage_2h']}")
    if r.get("ac"):
        lines.append(f"Armour     : {r['ac']}")
    if r.get("properties"):
        lines.append(f"Properties : {', '.join(r['properties'])}")
    if r.get("range"):
        lines.append(f"Range      : {r['range']}")
    if r.get("throw_range"):
        lines.append(f"Throw      : {r['throw_range']}")
    if r.get("stealth_disadv"):
        lines.append("Stealth    : disadvantage")
    if r.get("str_minimum"):
        lines.append(f"Str min    : {r['str_minimum']}")
    desc = r.get("description", "")
    if desc:
        lines += ["", desc]
    return "\n".join(lines)


def _fmt_magic_item(r: dict) -> str:
    lines = [f"## {r.get('name','?')}  [{r.get('rarity','')} {r.get('category','')}]", ""]
    if r.get("attunement"):
        lines.append("Requires attunement.")
        lines.append("")
    lines.append(r.get("description", ""))
    return "\n".join(lines)


def _fmt_condition(r: dict) -> str:
    lines = [f"## {r.get('name','?')}", ""]
    for bullet in r.get("description", "").splitlines():
        lines.append(f"  • {bullet}" if bullet.strip() and not bullet.startswith("•") else bullet)
    return "\n".join(lines)


def _fmt_monster(r: dict) -> str:
    lines = [f"## {r.get('name','?')}  [CR {r.get('cr','?')} | {r.get('xp','?')} XP]",
             f"{r.get('size','')} {r.get('type','')}  ·  {r.get('alignment','')}",
             "", f"AC {r.get('ac','?')}  ·  HP {r.get('hp','?')} ({r.get('hp_dice','')})",
             f"Speed: {r.get('speed','')}", ""]
    abbr = ["STR","DEX","CON","INT","WIS","CHA"]
    keys = ["str","dex","con","int","wis","cha"]
    def _mod(v): return (v - 10) // 2
    row1 = " | ".join(f"{a:3}" for a in abbr)
    row2 = " | ".join(f"{r.get(k,10):3}({_mod(r.get(k,10)):+d})" for k in keys)
    lines += [row1, row2, ""]
    if r.get("languages"):
        lines.append(f"Languages: {r['languages']}")
    desc = r.get("description", "")
    if desc:
        lines += ["", desc]
    return "\n".join(lines)


def _fmt_feature(r: dict) -> str:
    cls_s   = r.get("class", "")
    lvl_s   = f"  (level {r['level_req']})" if r.get("level_req") else ""
    src_s   = f"{cls_s}{lvl_s}".strip() or r.get("type", "")
    lines   = [f"## {r.get('name','?')}  [{src_s}]", "", r.get("description", "")]
    return "\n".join(lines)


FORMATTERS = {
    "spells":      _fmt_spell,
    "equipment":   _fmt_equipment,
    "magic_items": _fmt_magic_item,
    "conditions":  _fmt_condition,
    "monsters":    _fmt_monster,
    "features":    _fmt_feature,
}


# ─── Wikidot fallback URL ─────────────────────────────────────────────────────

def wikidot_url(name: str, category: str = None, record: dict = None) -> str:
    """Return a wikidot.com URL for a name that wasn't found in the dataset.

    Uses the record's own wikidot_url field if present (supplemental entries),
    otherwise constructs a URL from the category and name slug.
    Falls back to a site search for unknown categories.
    """
    if record and record.get("wikidot_url"):
        return record["wikidot_url"]

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    # Map internal category keys back to wikidot path prefixes
    _PREFIXES = {
        "spells":     "spell",
        "spell":      "spell",
        "conditions": "condition",
        "condition":  "condition",
        "monsters":   "monster",
        "monster":    "monster",
        "equipment":  "equipment",
        "magic_items": "magic-items",
    }
    prefix = _PREFIXES.get(category or "")
    if prefix:
        return f"https://dnd5e.wikidot.com/{prefix}:{slug}"
    # For features and unknowns: direct slug URL (wikidot search is unavailable)
    return f"https://dnd5e.wikidot.com/{slug}"


# ─── Public API ───────────────────────────────────────────────────────────────

def lookup_record(query: str, category=None):
    """Return the best-matching record dict, or None."""
    _load()
    if not _data:
        return None
    cat_key = CATEGORY_MAP.get((category or "").lower()) if category else None
    records = _get_records(cat_key)
    results = _find(query, records, top_n=1)
    # If no category specified and nothing found, search all
    resolved_cat = cat_key
    if not results and not category:
        for ck in ALL_CATEGORIES:
            results = _find(query, _data.get(ck, []), top_n=1)
            if results:
                resolved_cat = ck
                break
    # item search — resolve sub-category and tag the record
    if results and cat_key is None and resolved_cat is None:
        rec = results[0]
        for ck in ["equipment", "magic_items"]:
            if rec in _data.get(ck, []):
                resolved_cat = ck
                break
    if results and resolved_cat:
        results[0]["_cat"] = resolved_cat
    return results[0] if results else None


def lookup(query: str, category=None):
    """Return a formatted string description for the best match, or None."""
    _load()
    if not _data:
        return None
    cat_key  = CATEGORY_MAP.get((category or "").lower()) if category else None
    records  = _get_records(cat_key)
    results  = _find(query, records, top_n=1)
    resolved_cat = cat_key

    if not results and not category:
        for ck in ALL_CATEGORIES:
            results = _find(query, _data.get(ck, []), top_n=1)
            if results:
                resolved_cat = ck
                break

    # item search (cat_key=None) — resolve which sub-category the result came from
    if results and cat_key is None and resolved_cat is None:
        rec = results[0]
        for ck in ["equipment", "magic_items"]:
            if rec in _data.get(ck, []):
                resolved_cat = ck
                break

    if not results:
        return None

    fmt = FORMATTERS.get(resolved_cat or "spells", lambda r: json.dumps(r, indent=2))
    return fmt(results[0])


def _apply_level(text: str, level: int) -> str:
    """Collapse any scale progression strings to the value for the given level.

    Matches patterns like:
        1d6 (lvl 1–2), 2d6 (lvl 3–4), ..., 10d6 (lvl 19–20)
        +2 (lvl 1–8), +3 (lvl 9–15), +4 (lvl 16–20)

    Replaces the entire comma-separated run with just the matching value.
    Entries where the end bound is implicit (last entry, no upper bound shown)
    are treated as extending to 20.
    """
    # One entry: "VALUE (lvl START)" or "VALUE (lvl START–END)"
    entry_pat = r'[+\w\d/]+\s+\(lvl\s+\d+(?:[–\-]\d+)?\)'
    # Two or more entries separated by ", "
    scale_pat = entry_pat + r'(?:,\s*' + entry_pat + r')+'

    def _pick(m):
        entries = re.findall(r'([+\w\d/]+)\s+\(lvl\s+(\d+)(?:[–\-](\d+))?\)', m.group(0))
        for i, (val, start_s, end_s) in enumerate(entries):
            start = int(start_s)
            # Last entry: if no explicit end, treat as lvl START–20
            end = int(end_s) if end_s else 20
            if start <= level <= end:
                return val
        return m.group(0)  # no match — leave as-is

    return re.sub(scale_pat, _pick, text)


def lookup_with_level(query: str, category=None, level=None):
    """lookup() variant that collapses scale progressions to the given character level."""
    text = lookup(query, category=category)
    if text and level:
        try:
            text = _apply_level(text, int(level))
        except (ValueError, TypeError):
            pass
    return text


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args     = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags    = [a for a in sys.argv[1:] if a.startswith("--")]
    dump_json = "--json" in flags
    show_all  = "--all"  in flags
    top_n     = 10 if show_all else 1

    if not os.path.exists(DATA_FILE):
        print(f"Dataset not found: {DATA_FILE}")
        print("Run: python3 ~/.claude/skills/dnd/scripts/build_srd.py")
        sys.exit(1)

    _load()

    if len(args) < 2:
        print(__doc__)
        sys.exit(0)

    category, query = args[0].lower(), " ".join(args[1:])
    cat_key  = CATEGORY_MAP.get(category)
    records  = _get_records(cat_key)

    if cat_key is None and category not in CATEGORY_MAP:
        # Treat as a query across all categories
        query    = " ".join(args)
        records  = []
        for ck in ALL_CATEGORIES:
            records.extend(_data.get(ck, []))
        cat_key = None

    results = _find(query, records, top_n=top_n)

    # For item searches, resolve which sub-category each result came from
    def _resolve_cat(record):
        if cat_key is not None:
            return cat_key
        for ck in ALL_CATEGORIES:
            if record in _data.get(ck, []):
                return ck
        return "spells"

    if not results:
        print(f"No match for '{query}' in {category}.")
        sys.exit(0)

    for r in results:
        if dump_json:
            print(json.dumps(r, indent=2))
        else:
            rcat = _resolve_cat(r)
            fmt  = FORMATTERS.get(rcat, lambda x: json.dumps(x, indent=2))
            print(fmt(r))
            print()


if __name__ == "__main__":
    main()
