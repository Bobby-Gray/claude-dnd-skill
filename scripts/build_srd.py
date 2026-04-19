#!/usr/bin/env python3
"""
build_srd.py — build the bundled dnd5e_srd.json from two upstream sources

Sources:
  • 5e-bits/5e-database  (MIT + OGL)    — spells, equipment, magic items, conditions, monsters
  • foundryvtt/dnd5e     (MIT + CC-BY-4.0) — class features, racial traits (2024 SRD)

Output: ~/.claude/skills/dnd/data/dnd5e_srd.json

Usage:
    python3 build_srd.py             # build/rebuild the dataset
    python3 build_srd.py --status    # show current dataset metadata
    python3 build_srd.py --no-fvtt   # skip FoundryVTT features (faster, spells/items only)
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("PyYAML required for FoundryVTT data. Install: pip3 install pyyaml")
    print("Run with --no-fvtt to skip class features and build spells/items only.")
    yaml = None  # type: ignore

DATA_DIR  = os.path.expanduser("~/.claude/skills/dnd/data")
OUT_FILE  = os.path.join(DATA_DIR, "dnd5e_srd.json")

RAW_5EBITS   = "https://raw.githubusercontent.com/5e-bits/5e-database/main/src/2014"
RAW_FVTT     = "https://raw.githubusercontent.com/foundryvtt/dnd5e/master"
FVTT_TREE    = "https://api.github.com/repos/foundryvtt/dnd5e/git/trees/master?recursive=1"
BITS_COMMITS = "https://api.github.com/repos/5e-bits/5e-database/commits/main?per_page=1"
FVTT_COMMITS = "https://api.github.com/repos/foundryvtt/dnd5e/commits/master?per_page=1"

BITS_FILES = {
    "spells":      "5e-SRD-Spells.json",
    "equipment":   "5e-SRD-Equipment.json",
    "magic_items": "5e-SRD-Magic-Items.json",
    "conditions":  "5e-SRD-Conditions.json",
    "monsters":    "5e-SRD-Monsters.json",
}


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _fetch(url: str, as_json: bool = False):
    """Fetch URL, return parsed JSON or raw text. Returns None on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "dnd-skill-build/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        return json.loads(data) if as_json else data.decode("utf-8")
    except Exception as e:
        print(f"    ✗ {url}: {e}", file=sys.stderr)
        return None


def _fetch_json(url: str):
    return _fetch(url, as_json=True)


# ─── Text normalisation ───────────────────────────────────────────────────────

def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _strip_html(html: str) -> str:
    """Convert FoundryVTT HTML description to clean plain text."""
    if not html:
        return ""
    # @UUID[...]{label} → label
    html = re.sub(r"@UUID\[[^\]]*\]\{([^}]+)\}", r"\1", html)
    # [[lookup @scale.class.feature]] — resolved before _strip_html via _resolve_scale_tokens;
    # this fallback catches any that slip through (e.g. no scale_tables loaded)
    html = re.sub(r"\[\[lookup\s+@scale\.[^\]]+\]\]", "(scales with level)", html)
    # [[/r ...]] inline roll expressions → strip entirely
    html = re.sub(r"\[\[/r\s+[^\]]+\]\]", "", html)
    # Any remaining [[ ... ]] FoundryVTT tokens → strip
    html = re.sub(r"\[\[[^\]]*\]\]", "", html)
    # @Damage[...]{label} → label
    html = re.sub(r"@Damage\[[^\]]*\]\{([^}]+)\}", r"\1", html)
    # @Check[...]{label} → label
    html = re.sub(r"@Check\[[^\]]*\]\{([^}]+)\}", r"\1", html)
    # Any remaining @Token[...]{label} → label
    html = re.sub(r"@\w+\[[^\]]*\]\{([^}]+)\}", r"\1", html)
    # Any remaining bare @Token[...] → strip
    html = re.sub(r"@\w+\[[^\]]*\]", "", html)
    # &amp;Reference[Dash] → Dash
    html = re.sub(r"&amp;Reference\[([^\]]+)\]", r"\1", html)
    # &Reference[Dash] → Dash (in case already decoded)
    html = re.sub(r"&Reference\[([^\]]+)\]", r"\1", html)
    # List items
    html = re.sub(r"<li[^>]*>", "• ", html)
    html = re.sub(r"</li>", "\n", html)
    # Paragraphs/divs as line breaks
    html = re.sub(r"</p>|</div>|<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Table cells (crude: separate with spaces)
    html = re.sub(r"<td[^>]*>|<th[^>]*>", "  ", html, flags=re.IGNORECASE)
    html = re.sub(r"</tr>", "\n", html, flags=re.IGNORECASE)
    # Strip all remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # HTML entities
    html = html.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    html = html.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"')
    # Collapse whitespace
    lines = [ln.strip() for ln in html.splitlines()]
    text  = "\n".join(ln for ln in lines if ln)
    text  = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Strip FoundryVTT-specific "Foundry Note" sections (everything from that header onward)
    text = re.sub(r"\n?Foundry Note\b.*", "", text, flags=re.DOTALL).strip()
    return text


def _fmt_scale_table(table: dict) -> str:
    """Format {level_str: value_str} into a compact range string.
    e.g. {"1":"1d6","3":"2d6",...} → "1d6 (lvl 1–2), 2d6 (lvl 3–4), ..., 10d6 (lvl 19–20)"
    """
    levels = sorted(table.keys(), key=lambda x: int(x))
    parts  = []
    for i, lvl in enumerate(levels):
        val     = table[lvl]
        lvl_int = int(lvl)
        if i + 1 < len(levels):
            end = int(levels[i + 1]) - 1
            parts.append(f"{val} (lvl {lvl_int}–{end})" if end > lvl_int else f"{val} (lvl {lvl_int})")
        else:
            parts.append(f"{val} (lvl {lvl_int}–20)" if lvl_int < 20 else f"{val} (lvl 20)")
    return ", ".join(parts)


def _resolve_scale_tokens(html: str, scale_tables: dict) -> str:
    """Replace [[lookup @scale.class.identifier]] with formatted progression strings.
    Called before _strip_html so that the real data is embedded in the description.
    If a table is not found, substitutes '(scales with level)' as fallback.
    """
    if "[[" not in html:
        return html

    def _replacer(m):
        inner = re.search(r'@scale\.(\w+)\.([^\]\s]+)', m.group(0))
        if not inner:
            return "(scales with level)"
        cls_name   = inner.group(1)
        identifier = inner.group(2)
        table = (scale_tables.get(cls_name) or {}).get(identifier)
        return _fmt_scale_table(table) if table else "(scales with level)"

    return re.sub(r'\[\[lookup\s+@scale\.[^\]]+\]\]', _replacer, html)


def _join_desc(desc) -> str:
    """Normalise 5e-bits desc field (list or string) to a single string."""
    if isinstance(desc, list):
        return "\n\n".join(str(d) for d in desc)
    return str(desc) if desc else ""


# ─── 5e-bits normalisers ──────────────────────────────────────────────────────

def _norm_spell(r: dict) -> dict:
    school = r.get("school", {})
    return {
        "name":         r.get("name", ""),
        "index":        r.get("index", _slugify(r.get("name", ""))),
        "description":  _join_desc(r.get("desc", [])),
        "higher_level": _join_desc(r.get("higher_level", [])),
        "level":        r.get("level", 0),
        "school":       school.get("name", school) if isinstance(school, dict) else str(school),
        "casting_time": r.get("casting_time", ""),
        "range":        r.get("range", ""),
        "components":   r.get("components", []),
        "material":     r.get("material", ""),
        "duration":     r.get("duration", ""),
        "concentration":r.get("concentration", False),
        "ritual":       r.get("ritual", False),
        "classes":      [c.get("name", c) if isinstance(c, dict) else str(c)
                         for c in r.get("classes", [])],
    }


def _norm_equipment(r: dict) -> dict:
    cat  = r.get("equipment_category", {})
    cost = r.get("cost", {})
    dmg  = r.get("damage", {})
    dmg2 = r.get("two_handed_damage", {})
    rng  = r.get("range", {})
    trng = r.get("throw_range", {})
    ac   = r.get("armor_class", {})
    props = [p.get("name", p) if isinstance(p, dict) else str(p)
             for p in r.get("properties", [])]
    return {
        "name":          r.get("name", ""),
        "index":         r.get("index", _slugify(r.get("name", ""))),
        "description":   _join_desc(r.get("desc", [])),
        "category":      cat.get("name", "") if isinstance(cat, dict) else str(cat),
        "cost":          f"{cost.get('quantity','?')} {cost.get('unit','?')}"
                         if isinstance(cost, dict) else "",
        "weight":        r.get("weight"),
        "damage":        f"{dmg.get('damage_dice','')} {dmg.get('damage_type',{}).get('name','')}"
                         .strip() if dmg else "",
        "damage_2h":     f"{dmg2.get('damage_dice','')} {dmg2.get('damage_type',{}).get('name','')}"
                         .strip() if dmg2 else "",
        "ac":            f"AC {ac.get('base','')} + DEX" if ac else "",
        "properties":    props,
        "range":         f"{rng.get('normal','?')}/{rng.get('long','?')} ft"
                         if rng and rng.get("normal") else "",
        "throw_range":   f"{trng.get('normal','?')}/{trng.get('long','?')} ft" if trng else "",
        "stealth_disadv":r.get("stealth_disadvantage", False),
        "str_minimum":   r.get("str_minimum"),
    }


def _norm_magic_item(r: dict) -> dict:
    rar = r.get("rarity", {})
    cat = r.get("equipment_category", {})
    return {
        "name":        r.get("name", ""),
        "index":       r.get("index", _slugify(r.get("name", ""))),
        "description": _join_desc(r.get("desc", [])),
        "rarity":      rar.get("name", rar) if isinstance(rar, dict) else str(rar),
        "category":    cat.get("name", "") if isinstance(cat, dict) else str(cat),
        "attunement":  "attunement" in _join_desc(r.get("desc", [])).lower(),
    }


def _norm_condition(r: dict) -> dict:
    return {
        "name":        r.get("name", ""),
        "index":       r.get("index", _slugify(r.get("name", ""))),
        "description": _join_desc(r.get("desc", [])),
    }


def _norm_monster(r: dict) -> dict:
    ac_list = r.get("armor_class", [])
    ac_val  = (ac_list[0].get("value") if isinstance(ac_list, list) and ac_list
               and isinstance(ac_list[0], dict) else
               ac_list[0] if isinstance(ac_list, list) and ac_list else
               ac_list if isinstance(ac_list, (int, float)) else "?")
    speed   = r.get("speed", {})
    speed_s = ", ".join(f"{k} {v}" for k, v in speed.items() if v) if isinstance(speed, dict) else ""
    # Flatten special abilities + actions into description
    parts = []
    for sa in r.get("special_abilities", []):
        parts.append(f"{sa.get('name','')}: {sa.get('desc','')}")
    for a in r.get("actions", []):
        parts.append(f"Action — {a.get('name','')}: {a.get('desc','')}")
    for a in r.get("legendary_actions", []):
        parts.append(f"Legendary — {a.get('name','')}: {a.get('desc','')}")
    return {
        "name":  r.get("name", ""),
        "index": r.get("index", _slugify(r.get("name", ""))),
        "description": "\n\n".join(parts),
        "cr":    r.get("challenge_rating", "?"),
        "xp":    r.get("xp", "?"),
        "size":  r.get("size", ""),
        "type":  r.get("type", ""),
        "hp":    r.get("hit_points", "?"),
        "hp_dice": r.get("hit_dice", ""),
        "ac":    ac_val,
        "speed": speed_s,
        "str":   r.get("strength", 10),
        "dex":   r.get("dexterity", 10),
        "con":   r.get("constitution", 10),
        "int":   r.get("intelligence", 10),
        "wis":   r.get("wisdom", 10),
        "cha":   r.get("charisma", 10),
        "alignment": r.get("alignment", ""),
        "languages": r.get("languages", ""),
    }


# ─── FoundryVTT normaliser ────────────────────────────────────────────────────

def _parse_scale_tables(class_doc: dict) -> dict:
    """Extract ScaleValue advancements from a class YAML document.
    Returns {identifier: {level_str: value_str}}
    Indexed by both config.identifier and _slugify(title) so either lookup hits.
    """
    tables = {}
    system = class_doc.get("system", {}) if "system" in class_doc else class_doc
    for adv in system.get("advancement", []):
        if adv.get("type") != "ScaleValue":
            continue
        title  = adv.get("title", "").strip()
        config = adv.get("configuration", {}) or {}
        scale  = config.get("scale", {})
        vtype  = config.get("type", "dice")
        ident  = (config.get("identifier") or "").strip() or _slugify(title)
        if not scale or not title:
            continue

        table = {}
        for lvl, val in scale.items():
            if not isinstance(val, dict):
                continue
            if vtype == "dice":
                n, f = val.get("number", 0), val.get("faces", 0)
                if n and f:
                    table[str(lvl)] = f"{n}d{f}"
            elif vtype == "number":
                v = val.get("value")
                if v is not None:
                    table[str(lvl)] = f"+{v}" if isinstance(v, (int, float)) and v > 0 else str(v)
            else:
                v = val.get("value") or val.get("number")
                if v is not None:
                    table[str(lvl)] = str(v)

        if not table:
            continue
        tables[ident] = table
        slug = _slugify(title)
        if slug != ident:
            tables[slug] = table

    return tables


def _norm_feature(doc: dict, path: str, scale_tables=None):
    name = doc.get("name", "").strip()
    if not name:
        return None
    system    = doc.get("system", {})
    desc_html = system.get("description", {}).get("value", "") if isinstance(system.get("description"), dict) else ""
    prereq    = system.get("prerequisites", {}) or {}
    feat_type = system.get("type", {}).get("value", "class") if isinstance(system.get("type"), dict) else "class"

    # Derive class from path: packs/_source/classes24/<class>/class-features/...
    # or races: packs/_source/races/<race>/<variant>-features/...
    parts      = path.replace("\\", "/").split("/")
    class_name = None
    if "classes24" in parts:
        idx        = parts.index("classes24")
        class_name = parts[idx + 1] if idx + 1 < len(parts) else None
    elif "races" in parts:
        feat_type = "race"

    # Resolve [[lookup @scale.class.identifier]] tokens before HTML stripping
    desc_html = _resolve_scale_tokens(desc_html, scale_tables or {})

    return {
        "name":        name,
        "index":       _slugify(name),
        "description": _strip_html(desc_html),
        "class":       class_name,
        "level_req":   prereq.get("level"),
        "type":        feat_type,
    }


# ─── Fetch 5e-bits datasets ───────────────────────────────────────────────────

def _load_bits_records(filename: str) -> list:
    raw = json.loads(_fetch(f"{RAW_5EBITS}/{filename}") or "null")
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("results", list(raw.values())[0] if raw else [])
    return []


def _build_5ebits() -> dict:
    categories = {}
    for key, filename in BITS_FILES.items():
        print(f"  5e-bits  {key} …", end="", flush=True)
        records = _load_bits_records(filename)
        NORM = {
            "spells":      _norm_spell,
            "equipment":   _norm_equipment,
            "magic_items": _norm_magic_item,
            "conditions":  _norm_condition,
            "monsters":    _norm_monster,
        }
        normed = [NORM[key](r) for r in records if isinstance(r, dict)]
        normed = [r for r in normed if r.get("name")]
        categories[key] = normed
        print(f" {len(normed)} records")
    return categories


# ─── Fetch FoundryVTT features ────────────────────────────────────────────────

def _build_fvtt():
    if yaml is None:
        print("  foundryvtt  skipped (PyYAML not installed)")
        return [], ""

    print("  foundryvtt  fetching repo tree …", end="", flush=True)
    data = _fetch_json(FVTT_TREE)
    if not data:
        print(" failed")
        return [], ""
    tree = data.get("tree", [])
    sha  = data.get("sha", "")

    # Partition tree into feature YAMLs and class-level YAMLs (scale tables)
    feature_paths  = []
    class_yml_paths = []
    for t in tree:
        p = t["path"]
        if not p.endswith(".yml") or os.path.basename(p).startswith("_"):
            continue
        if p.startswith("packs/_source/classes24/"):
            depth = p.count("/")
            if "/class-features/" in p:
                # e.g. packs/_source/classes24/rogue/class-features/SneakAttack.yml (5 slashes)
                feature_paths.append(p)
            elif depth == 4:
                # e.g. packs/_source/classes24/rogue/Rogue.yml — class document itself (4 slashes)
                class_yml_paths.append(p)
        elif p.startswith("packs/_source/races/") and re.search(r"/-?\w+-features/", p):
            feature_paths.append(p)

    print(f" {len(feature_paths)} feature files, {len(class_yml_paths)} class files")

    # Fetch class YAMLs and extract scale tables
    # scale_tables: {class_name: {identifier: {level_str: value_str}}}
    scale_tables = {}
    for path in class_yml_paths:
        raw = _fetch(f"{RAW_FVTT}/{path}")
        if not raw:
            continue
        try:
            doc = yaml.safe_load(raw)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        parts = path.replace("\\", "/").split("/")
        if "classes24" not in parts:
            continue
        idx        = parts.index("classes24")
        class_name = parts[idx + 1] if idx + 1 < len(parts) else None
        if not class_name:
            continue
        tables = _parse_scale_tables(doc)
        if tables:
            scale_tables[class_name] = tables

    if scale_tables:
        resolved = sum(len(v) for v in scale_tables.values())
        print(f"  foundryvtt  {len(scale_tables)} classes, {resolved} scale tables loaded")

    # Fetch and normalise feature files
    features = []
    failed   = 0
    for i, path in enumerate(feature_paths, 1):
        raw = _fetch(f"{RAW_FVTT}/{path}")
        if raw is None:
            failed += 1
            continue
        try:
            doc = yaml.safe_load(raw)
        except Exception:
            failed += 1
            continue
        if not isinstance(doc, dict):
            continue
        feat = _norm_feature(doc, path, scale_tables)
        if feat and feat["description"]:
            features.append(feat)
        if i % 50 == 0:
            time.sleep(0.5)
            print(f"    … {i}/{len(feature_paths)}")

    print(f"  foundryvtt  {len(features)} features  ({failed} failed/empty)")
    return features, sha


# ─── Latest commit SHAs (for sync_srd.py) ────────────────────────────────────

def _latest_sha(url: str) -> str:
    data = _fetch_json(url)
    if data and isinstance(data, list) and data:
        return data[0].get("sha", "")
    return ""


# ─── Main ─────────────────────────────────────────────────────────────────────

def cmd_status() -> None:
    if not os.path.exists(OUT_FILE):
        print(f"Dataset not built. Run build_srd.py to create it.")
        return
    with open(OUT_FILE) as f:
        data = json.load(f)
    meta   = data.get("_meta", {})
    counts = meta.get("record_counts", {})
    sources = meta.get("sources", {})
    print(f"Dataset:    {OUT_FILE}")
    print(f"Built at:   {meta.get('built_at','?')}")
    print()
    for cat, n in counts.items():
        print(f"  {cat:<12}  {n} records")
    print()
    for src, info in sources.items():
        print(f"  {src}:  {info.get('fetched_at','?')}  sha={info.get('sha','?')[:12]}…")


def cmd_build(skip_fvtt: bool = False) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("── 5e-bits/5e-database ─────────────────────────────────────────")
    bits_sha = _latest_sha(BITS_COMMITS)
    categories = _build_5ebits()

    print()
    print("── foundryvtt/dnd5e ────────────────────────────────────────────")
    fvtt_sha = _latest_sha(FVTT_COMMITS)
    if skip_fvtt:
        print("  skipped (--no-fvtt)")
        features = []
    else:
        features, _ = _build_fvtt()
    categories["features"] = features

    counts = {k: len(v) for k, v in categories.items()}
    total  = sum(counts.values())

    dataset = {
        "_meta": {
            "built_at":      now,
            "total_records": total,
            "record_counts": counts,
            "sources": {
                "5e-bits": {
                    "repo":       "5e-bits/5e-database",
                    "branch":     "main",
                    "sha":        bits_sha,
                    "fetched_at": now,
                },
                "foundryvtt": {
                    "repo":       "foundryvtt/dnd5e",
                    "branch":     "master",
                    "sha":        fvtt_sha,
                    "fetched_at": now,
                },
            },
        },
        **categories,
    }

    with open(OUT_FILE, "w") as f:
        json.dump(dataset, f, separators=(",", ":"))  # compact

    size_kb = os.path.getsize(OUT_FILE) // 1024
    print()
    print(f"── Complete ────────────────────────────────────────────────────")
    print(f"  {total} records  →  {OUT_FILE}  ({size_kb} KB)")
    for cat, n in counts.items():
        print(f"    {cat:<12}  {n}")


def main() -> None:
    args = sys.argv[1:]
    if "--status" in args:
        cmd_status()
    else:
        cmd_build(skip_fvtt="--no-fvtt" in args)


if __name__ == "__main__":
    main()
