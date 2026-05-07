"""
name_registry.py — persistent cache of every character name ever used
across all campaigns under this account.

Storage: <DND_CAMPAIGN_ROOT>/.name_registry.json (defaults to
~/.claude/dnd/.name_registry.json).

Purpose:
    1. Detect duplicate-name proposals at /dnd new, /dnd character new,
       /dnd npc <new> time (consumed by Piece 2 — uniqueness check).
    2. Power the random-name path of /dnd npc rename (Piece 3) — never
       pick a name already in the registry.
    3. Auditable footprint of who's been used where.

Schema per entry (keyed by slug):
    {
        "name": "Aldric Voss",
        "slug": "aldric_voss",
        "type": "npc" | "pc",
        "first_campaign": "campaign-name",
        "first_session": 1,
        "first_used": "YYYY-MM-DD",
        "currently_active_in": ["campaign-1", "campaign-2"],
        "retired_from": [
            {"campaign": "campaign-name", "replaced_by": "new_slug",
             "date": "YYYY-MM-DD"}
        ]
    }

CLI:
    python3 name_registry.py rebuild           # scan all campaigns
    python3 name_registry.py list [--campaign C] [--type npc|pc]
    python3 name_registry.py lookup <name>     # case-insensitive
    python3 name_registry.py add --name N --type T --campaign C --session N
    python3 name_registry.py retire --name N --campaign C [--replaced-by NEW]
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys

from paths import campaigns_dir, characters_dir, _root


def _registry_path() -> pathlib.Path:
    return _root() / ".name_registry.json"


def _today() -> str:
    return datetime.date.today().isoformat()


def slug(name: str) -> str:
    """Lowercase, snake_case slug. Drop punctuation; collapse whitespace.

    Strips parenthetical content first so 'Vedra Ceth (V.C.)' and
    'Vedra Ceth' produce the same slug. Strips trailing/leading whitespace.
    """
    s = name.strip().lower()
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)  # drop parenthetical asides
    s = re.sub(r"[^\w\s]", "", s)            # drop remaining punctuation
    s = re.sub(r"\s+", "_", s).strip("_")    # collapse whitespace to _
    return s


def _load() -> dict:
    p = _registry_path()
    if not p.exists():
        return {"version": 1, "updated": _today(), "entries": {}}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        sys.stderr.write(f"name_registry: {p} is corrupt; starting fresh\n")
        return {"version": 1, "updated": _today(), "entries": {}}


def _save(data: dict) -> None:
    data["updated"] = _today()
    p = _registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Scanners ──────────────────────────────────────────────────────────────

_NPCS_TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|", re.MULTILINE)
_NPCS_FULL_HEADER = re.compile(r"^### \s*([^\n]+?)\s*$", re.MULTILINE)
_NPC_HEADER = re.compile(r"^## \s*([^\n]+?)\s*$", re.MULTILINE)
_CHARACTER_H1 = re.compile(r"^#\s+([^\n]+?)\s*$", re.MULTILINE)
_SESSION_COUNT = re.compile(r"\*\*Session count:\*\*\s*(\d+)")
_LAST_SESSION = re.compile(r"\*\*Last session:\*\*\s*(\d{4}-\d{2}-\d{2})")
_CREATED = re.compile(r"\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})")


def _campaign_session_count(camp_dir: pathlib.Path) -> int:
    state = camp_dir / "state.md"
    if not state.exists():
        return 0
    m = _SESSION_COUNT.search(state.read_text(errors="replace"))
    return int(m.group(1)) if m else 0


def _scan_campaign_npcs(camp_dir: pathlib.Path) -> list[str]:
    """Read npcs.md table column 1 + npcs-full.md ### headers; return names."""
    names: list[str] = []
    npcs = camp_dir / "npcs.md"
    if npcs.exists():
        for row in _NPCS_TABLE_ROW.finditer(npcs.read_text(errors="replace")):
            cell = row.group(1).strip()
            # Skip header rows ("Name") and divider rows ("---")
            if not cell or cell.lower() in {"name"} or set(cell) <= {"-", " ", ":"}:
                continue
            names.append(cell)
    full = camp_dir / "npcs-full.md"
    if full.exists():
        for h in _NPCS_FULL_HEADER.finditer(full.read_text(errors="replace")):
            names.append(h.group(1).strip())
        for h in _NPC_HEADER.finditer(full.read_text(errors="replace")):
            names.append(h.group(1).strip())
    return names


def _scan_campaign_pcs(camp_dir: pathlib.Path) -> list[str]:
    """Read characters/*.md H1 line; return PC names."""
    pcs: list[str] = []
    char_dir = camp_dir / "characters"
    if not char_dir.exists():
        return pcs
    for f in sorted(char_dir.glob("*.md")):
        text = f.read_text(errors="replace")
        m = _CHARACTER_H1.search(text)
        if m:
            pcs.append(m.group(1).strip())
    return pcs


def _scan_campaign_graph(camp_dir: pathlib.Path) -> list[tuple[str, str]]:
    """Read graph.json node names + types — returns [(name, type), ...]."""
    g = camp_dir / "graph.json"
    if not g.exists():
        return []
    try:
        data = json.loads(g.read_text())
    except json.JSONDecodeError:
        return []
    out = []
    for node in data.get("nodes", []):
        name = node.get("name") or node.get("label")
        ntype = node.get("type", "npc")
        # Only collect npc/pc nodes — places/factions/threads aren't characters
        if name and ntype in {"npc", "pc"}:
            out.append((name, ntype))
    return out


# ── Operations ────────────────────────────────────────────────────────────

def _ensure_entry(entries: dict, name: str, ntype: str,
                  campaign: str, session: int) -> dict:
    s = slug(name)
    if s in entries:
        e = entries[s]
        # Update active list
        if campaign not in e.get("currently_active_in", []):
            e.setdefault("currently_active_in", []).append(campaign)
        return e
    entries[s] = {
        "name": name,
        "slug": s,
        "type": ntype,
        "first_campaign": campaign,
        "first_session": session,
        "first_used": _today(),
        "currently_active_in": [campaign],
        "retired_from": [],
    }
    return entries[s]


def rebuild() -> dict:
    """Walk every campaign and populate the registry from scratch.

    Existing retire-from history is preserved on a best-effort basis if
    the slug matches; otherwise rebuild starts fresh (use --keep-history
    to preserve all retire records — see CLI flag).
    """
    data = _load()
    old_entries = data.get("entries", {})
    new_entries: dict = {}

    cd = campaigns_dir()
    if not cd.exists():
        return {"campaigns": 0, "entries": 0}

    campaign_count = 0
    for camp in sorted(cd.iterdir()):
        if not camp.is_dir() or camp.name.startswith("."):
            continue
        if ".backup-" in camp.name:
            continue
        campaign_count += 1
        sess = _campaign_session_count(camp)

        for name in _scan_campaign_npcs(camp):
            _ensure_entry(new_entries, name, "npc", camp.name, sess)
        for name in _scan_campaign_pcs(camp):
            _ensure_entry(new_entries, name, "pc", camp.name, sess)
        for name, ntype in _scan_campaign_graph(camp):
            _ensure_entry(new_entries, name, ntype, camp.name, sess)

    # Preserve retire-from history from old registry where slug matches
    for s, old_e in old_entries.items():
        if s in new_entries and old_e.get("retired_from"):
            new_entries[s]["retired_from"] = old_e["retired_from"]

    data["entries"] = new_entries
    _save(data)
    return {"campaigns": campaign_count, "entries": len(new_entries)}


def add(name: str, ntype: str, campaign: str, session: int) -> dict:
    data = _load()
    entry = _ensure_entry(data["entries"], name, ntype, campaign, session)
    _save(data)
    return entry


def retire(name: str, campaign: str, replaced_by: str | None = None) -> dict | None:
    data = _load()
    s = slug(name)
    if s not in data["entries"]:
        return None
    e = data["entries"][s]
    e["currently_active_in"] = [c for c in e.get("currently_active_in", []) if c != campaign]
    e.setdefault("retired_from", []).append({
        "campaign": campaign,
        "replaced_by": slug(replaced_by) if replaced_by else None,
        "date": _today(),
    })
    _save(data)
    return e


def lookup(name: str) -> dict | None:
    data = _load()
    return data["entries"].get(slug(name))


def list_entries(campaign: str | None = None,
                 ntype: str | None = None) -> list[dict]:
    data = _load()
    out = []
    for e in data["entries"].values():
        if campaign and campaign not in e.get("currently_active_in", []):
            continue
        if ntype and e.get("type") != ntype:
            continue
        out.append(e)
    return sorted(out, key=lambda x: x["name"].lower())


def all_taken_slugs() -> set[str]:
    """Used by random-name path to exclude every name ever seen."""
    data = _load()
    return set(data["entries"].keys())


# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("rebuild", help="scan all campaigns, populate registry")

    pl = sub.add_parser("list", help="list registry entries")
    pl.add_argument("--campaign", help="filter to this campaign's active set")
    pl.add_argument("--type", choices=["npc", "pc"], help="filter by type")

    pk = sub.add_parser("lookup", help="case-insensitive lookup by name")
    pk.add_argument("name")

    pa = sub.add_parser("add", help="record a new name")
    pa.add_argument("--name", required=True)
    pa.add_argument("--type", choices=["npc", "pc"], default="npc")
    pa.add_argument("--campaign", required=True)
    pa.add_argument("--session", type=int, default=1)

    pr = sub.add_parser("retire", help="mark a name as retired in a campaign")
    pr.add_argument("--name", required=True)
    pr.add_argument("--campaign", required=True)
    pr.add_argument("--replaced-by", help="slug of replacement entry")

    args = p.parse_args()

    if args.cmd == "rebuild":
        result = rebuild()
        print(f"name_registry: scanned {result['campaigns']} campaigns; "
              f"{result['entries']} unique names recorded")
        print(f"  registry: {_registry_path()}")
        return 0

    if args.cmd == "list":
        entries = list_entries(campaign=args.campaign, ntype=args.type)
        for e in entries:
            active = ",".join(e.get("currently_active_in", [])) or "(retired everywhere)"
            print(f"  {e['type']:3s}  {e['name']:30s}  first: {e['first_campaign']} S{e['first_session']}  active: {active}")
        print(f"\n  total: {len(entries)} entries")
        return 0

    if args.cmd == "lookup":
        e = lookup(args.name)
        if not e:
            print(f"  no entry for '{args.name}'")
            return 1
        print(json.dumps(e, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "add":
        e = add(args.name, args.type, args.campaign, args.session)
        print(json.dumps(e, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "retire":
        e = retire(args.name, args.campaign, args.replaced_by)
        if not e:
            print(f"  no entry for '{args.name}'")
            return 1
        print(json.dumps(e, indent=2, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
