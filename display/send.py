#!/usr/bin/env python3
"""
send.py — send text to the DnD DM display server.

Usage:
    # DM narration (default)
    python3 send.py << 'DNDEND'
    The tavern reeks of old ale and burnt tallow.
    DNDEND

    # Player action — prepends character name on display
    python3 send.py --player Flerb << 'DNDEND'
    Flerb draws her greatsword and steps forward.
    DNDEND

    # Dice result — pipe from dice.py for open rolls
    python3 ~/.claude/skills/dnd/scripts/dice.py d20+4 | python3 send.py --dice

    # NPC dialogue — amber border, italic, amber name header
    python3 send.py --npc "Vesna" << 'DNDEND'
    "I've been waiting for you."
    DNDEND

    # Tutor/learning mode hint — collapsible parchment block on display
    python3 send.py --tutor << 'DNDEND'
    You could try a Perception check (WIS) to scan the room before acting.
    DNDEND

    # Player action intent — subdued label echoing what the player declared
    python3 send.py --action "Bob" << 'DNDEND'
    Attempts to shimmy across the rope to the ship under cover of darkness.
    DNDEND

    # Short inline string
    echo "Short message" | python3 send.py

    # State changes bundled with narration (Option B)
    python3 send.py --stat-hp "Mira:12:17" --stat-slot-use "Aldric:1" << 'DNDEND'
    The goblin's blade finds a gap in her armor for 5 damage...
    DNDEND

    # Supported stat flags (can repeat for multiple players):
    #   --stat-hp         "NAME:CURRENT:MAX"
    #   --stat-temp-hp    "NAME:N"
    #   --stat-slot-use   "NAME:LEVEL"       (expend one slot)
    #   --stat-slot-restore "NAME:LEVEL"     (restore one slot)
    #   --stat-condition-add    "NAME:CONDITION"
    #   --stat-condition-remove "NAME:CONDITION"
    #   --stat-concentrate "NAME:SPELL"       (empty SPELL = clear)
    #   --stat-inventory-add    "NAME:ITEM"
    #   --stat-inventory-remove "NAME:ITEM"
    #
    # Timed effect flags:
    #   --effect-start "NAME:SPELL:DURATION"   DURATION: 10r/60m/8h/indef  optional :conc
    #   --effect-end   "NAME:SPELL"            narrative end (broken/dispelled)
"""

import sys
import json
import argparse
import os
import ssl
import time
import urllib.request

_DISPLAY_DIR = os.path.dirname(os.path.abspath(__file__))
_SCHEME_FILE = os.path.join(_DISPLAY_DIR, ".scheme")
_SCHEME = open(_SCHEME_FILE).read().strip() if os.path.exists(_SCHEME_FILE) else "http"
FLASK_URL   = f"{_SCHEME}://localhost:5001/chunk"
STATS_URL   = f"{_SCHEME}://localhost:5001/stats"
TOKEN_FILE  = os.path.expanduser("~/.claude/skills/dnd/display/.token")
TIMEOUT     = 8.0
RETRIES     = 1                # one retry on timeout/connection error
CHUNK_LIMIT = 3500             # paragraph-split text bodies above this many chars

# SSL context — only used when running HTTPS (self-signed cert)
if _SCHEME == "https":
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE
else:
    _SSL_CTX = None


def _read_token() -> str:
    try:
        return open(TOKEN_FILE).read().strip()
    except FileNotFoundError:
        return ""


def _post(url: str, data: bytes, token: str) -> bool:
    """POST data with retries. Logs failures to stderr (visible in Bash output).

    Returns True on success, False after all retries exhausted. Display being
    offline is the only "expected" failure mode; everything else is logged so
    transient timeouts / dropped sends do not silently lose narration.
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-DND-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    attempts = RETRIES + 1
    last_err: "Exception | None" = None
    for i in range(attempts):
        try:
            urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX)
            return True
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            # Connection refused = display not running. First-attempt fail-fast.
            inner = getattr(e, "reason", e)
            if isinstance(inner, ConnectionRefusedError) or "Connection refused" in str(inner):
                return False
            last_err = e
            if i < attempts - 1:
                time.sleep(0.5 * (i + 1))
        except Exception as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(0.5 * (i + 1))
    print(f"send.py: POST {url} failed after {attempts} attempts: {last_err}",
          file=sys.stderr)
    return False


def _split_paragraphs(text: str, limit: int = CHUNK_LIMIT) -> list:
    """Split a long text body into chunks no larger than `limit` chars.

    Splits on paragraph boundaries (`\\n\\n`) when possible. Each chunk
    preserves the original whitespace. If a single paragraph exceeds the
    limit, it is hard-split on character boundary as a last resort.
    """
    if len(text) <= limit:
        return [text]
    paragraphs = text.split("\n\n")
    chunks: list = []
    cur = ""
    for p in paragraphs:
        candidate = (cur + "\n\n" + p) if cur else p
        if len(candidate) <= limit:
            cur = candidate
            continue
        # Flush whatever we have, start a new chunk with this paragraph
        if cur:
            chunks.append(cur)
            cur = ""
        # If this single paragraph is itself too big, hard-split it
        if len(p) > limit:
            for i in range(0, len(p), limit):
                chunks.append(p[i:i + limit])
        else:
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


def _build_stats_payload(args) -> "dict | None":
    """Build a push_stats-compatible payload from --stat-* flags."""
    players: "dict[str, dict]" = {}

    def _p(name: str) -> dict:
        return players.setdefault(name, {"name": name})

    for spec in (args.stat_hp or []):
        parts = spec.split(":")
        if len(parts) >= 3:
            name, cur, mx = parts[0], parts[1], parts[2]
            try:
                _p(name)["hp"] = {"current": int(cur), "max": int(mx)}
            except ValueError:
                pass

    for spec in (args.stat_temp_hp or []):
        idx = spec.rfind(":")
        if idx > 0:
            name, n = spec[:idx], spec[idx + 1:]
            try:
                _p(name).setdefault("hp", {})["temp"] = int(n)
            except ValueError:
                pass

    for spec in (args.stat_slot_use or []):
        idx = spec.rfind(":")
        if idx > 0:
            name, lvl = spec[:idx], spec[idx + 1:]
            try:
                _p(name)["_slot_use"] = int(lvl)
            except ValueError:
                pass

    for spec in (args.stat_slot_restore or []):
        idx = spec.rfind(":")
        if idx > 0:
            name, lvl = spec[:idx], spec[idx + 1:]
            try:
                _p(name)["_slot_restore"] = int(lvl)
            except ValueError:
                pass

    for spec in (args.stat_condition_add or []):
        idx = spec.find(":")
        if idx > 0:
            name, cond = spec[:idx], spec[idx + 1:]
            if cond.strip():
                _p(name)["_conditions_add"] = cond.strip()

    for spec in (args.stat_condition_remove or []):
        idx = spec.find(":")
        if idx > 0:
            name, cond = spec[:idx], spec[idx + 1:]
            if cond.strip():
                _p(name)["_conditions_remove"] = cond.strip()

    for spec in (args.stat_concentrate or []):
        idx = spec.find(":")
        if idx >= 0:
            name, spell = spec[:idx], spec[idx + 1:]
            _p(name)["concentration"] = spell.strip() or None

    for spec in (args.stat_inventory_add or []):
        idx = spec.find(":")
        if idx > 0:
            name, item = spec[:idx], spec[idx + 1:]
            if item.strip():
                _p(name)["_inventory_add"] = item.strip()

    for spec in (args.stat_inventory_remove or []):
        idx = spec.find(":")
        if idx > 0:
            name, item = spec[:idx], spec[idx + 1:]
            if item.strip():
                _p(name)["_inventory_remove"] = item.strip()

    for spec in (args.effect_start or []):
        # Format: NAME:SPELL:DURATION[:conc]
        # DURATION: 10r (rounds), 60m (minutes), 8h (hours), indef (indefinite)
        parts = spec.split(":", 3)
        if len(parts) < 3:
            continue
        name     = parts[0].strip()
        spell    = parts[1].strip()
        dur_str  = parts[2].strip().lower()
        is_conc  = len(parts) == 4 and parts[3].strip().lower() == "conc"
        if not name or not spell:
            continue
        effect: dict = {"name": spell, "concentration": is_conc}
        if dur_str.endswith("r"):
            try:
                effect["duration_type"]      = "rounds"
                effect["duration_remaining"] = int(dur_str[:-1])
            except ValueError:
                continue
        elif dur_str.endswith("m"):
            try:
                effect["duration_type"]    = "minutes"
                effect["duration_seconds"] = int(dur_str[:-1]) * 60
                effect["started_at"]       = time.time()
            except ValueError:
                continue
        elif dur_str.endswith("h"):
            try:
                effect["duration_type"]    = "hours"
                effect["duration_seconds"] = int(dur_str[:-1]) * 3600
                effect["started_at"]       = time.time()
            except ValueError:
                continue
        else:
            effect["duration_type"] = "indefinite"
        _p(name)["_effect_start"] = effect

    for spec in (args.effect_end or []):
        idx = spec.find(":")
        if idx > 0:
            name, spell = spec[:idx], spec[idx + 1:]
            if spell.strip():
                _p(name)["_effect_end"] = spell.strip()

    if not players:
        return None
    return {"players": list(players.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Send text to the DnD display server.")
    parser.add_argument(
        "--player", metavar="NAME",
        help="Send as a player action, prepending the character name on display",
    )
    parser.add_argument(
        "--npc", metavar="NAME",
        help="Send as NPC dialogue with amber styling and character name header",
    )
    parser.add_argument(
        "--dice", action="store_true",
        help="Send as a dice result (inline gold styling)",
    )
    parser.add_argument(
        "--tutor", action="store_true",
        help="Send as a tutor/learning hint (collapsible parchment block)",
    )
    parser.add_argument(
        "--action", metavar="NAME",
        help="Send as a player action intent — subdued label echoing what the player declared",
    )

    # ── Inspiration / XP award flags ─────────────────────────────────────────
    parser.add_argument("--inspiration-award", metavar="NAME",
        help="Award Inspiration: fires a styled gold block in the feed + sidebar badge")
    parser.add_argument("--inspiration-reason", metavar="TEXT",
        help="Optional reason to render below the name in the inspiration block "
             "(matches how --xp-award reason is rendered). Requires --inspiration-award.")
    parser.add_argument("--inspiration-spend", metavar="NAME",
        help="Spend/clear Inspiration: removes sidebar badge")
    parser.add_argument("--xp-award", metavar="JSON",
        help='XP award block: \'{"names":["Aldric","Mira"],"xp":250,"reason":"Encounter resolved","total":"3250/6500"}\'')

    # ── Stat-change flags (Option B — bundled with narration) ─────────────────
    parser.add_argument("--stat-hp", action="append", metavar="NAME:CUR:MAX",
        help="Set HP: NAME:CURRENT:MAX (can repeat for multiple players)")
    parser.add_argument("--stat-temp-hp", action="append", metavar="NAME:N",
        help="Set temp HP: NAME:N")
    parser.add_argument("--stat-slot-use", action="append", metavar="NAME:LEVEL",
        help="Expend one spell slot: NAME:LEVEL")
    parser.add_argument("--stat-slot-restore", action="append", metavar="NAME:LEVEL",
        help="Restore one spell slot: NAME:LEVEL")
    parser.add_argument("--stat-condition-add", action="append", metavar="NAME:COND",
        help="Add condition: NAME:CONDITION (can repeat)")
    parser.add_argument("--stat-condition-remove", action="append", metavar="NAME:COND",
        help="Remove condition: NAME:CONDITION (can repeat)")
    parser.add_argument("--stat-concentrate", action="append", metavar="NAME:SPELL",
        help="Set concentration: NAME:SPELL (empty SPELL = clear)")
    parser.add_argument("--stat-inventory-add", action="append", metavar="NAME:ITEM",
        help="Add inventory item: NAME:ITEM")
    parser.add_argument("--stat-inventory-remove", action="append", metavar="NAME:ITEM",
        help="Remove inventory item: NAME:ITEM")
    parser.add_argument("--effect-start", action="append", metavar="NAME:SPELL:DURATION",
        help="Start a timed effect: NAME:SPELL:DURATION (10r/60m/8h/indef) optionally :conc")
    parser.add_argument("--effect-end", action="append", metavar="NAME:SPELL",
        help="End a timed effect: NAME:SPELL (narrative end — broken, dispelled, player drops)")

    args = parser.parse_args()

    # Only read stdin when a content flag (or no flag at all = plain narration)
    # is set. Body-less flags (inspiration / xp-award / stat-only) have no text
    # body and must not touch stdin — when chained in a multi-command Bash
    # block, the parent shell's stdin pipe stays open until the whole bash
    # exits, so a body-less stdin.read() would block for the entire bash
    # duration and silently drop every subsequent send in the chain.
    _has_content_flag = bool(args.player or args.npc or args.dice or args.tutor or args.action)
    _has_bodyless_flag = bool(
        args.inspiration_award or args.inspiration_spend or args.xp_award
        or _build_stats_payload(args)
    )
    text = sys.stdin.read() if (_has_content_flag or not _has_bodyless_flag) else ""
    token = _read_token()

    # ── Inspiration award/spend (bypass normal text flow) ─────────────────────
    if args.inspiration_award:
        name = args.inspiration_award.strip()
        body: dict = {"inspiration_award": name, "text": name}
        if args.inspiration_reason:
            body["reason"] = args.inspiration_reason.strip()
        _post(FLASK_URL, json.dumps(body).encode(), token)
        _post(STATS_URL, json.dumps({"players": [{"name": name, "inspiration": True}]}).encode(), token)
        return

    if args.inspiration_spend:
        name = args.inspiration_spend.strip()
        _post(STATS_URL, json.dumps({"players": [{"name": name, "inspiration": False}]}).encode(), token)
        return

    # ── XP award block ────────────────────────────────────────────────────────
    if args.xp_award:
        try:
            xp_data = json.loads(args.xp_award)
        except json.JSONDecodeError as e:
            print(f"Invalid xp-award JSON: {e}", file=sys.stderr)
            sys.exit(1)
        # Build a human-readable summary if not provided
        if "summary" not in xp_data:
            names = ", ".join(xp_data.get("names", []))
            amt   = xp_data.get("xp", 0)
            rsn   = xp_data.get("reason", "")
            xp_data["summary"] = f"{names} — {amt} XP" + (f" ({rsn})" if rsn else "")
        _post(FLASK_URL, json.dumps({"xp_award": xp_data, "text": xp_data["summary"]}).encode(), token)
        return

    # ── Text send ─────────────────────────────────────────────────────────────
    if text.strip():
        chunks = _split_paragraphs(text)
        for chunk in chunks:
            payload: dict = {"text": chunk}
            if args.action:
                payload["action"] = args.action
            elif args.player:
                payload["player"] = args.player
            elif args.npc:
                payload["npc"] = args.npc
            elif args.dice:
                payload["dice"] = True
            elif args.tutor:
                payload["tutor"] = True

            _post(FLASK_URL, json.dumps(payload).encode("utf-8"), token)

    # ── Stat send (bundled) ───────────────────────────────────────────────────
    stats_payload = _build_stats_payload(args)
    if stats_payload:
        _post(STATS_URL, json.dumps(stats_payload).encode("utf-8"), token)


if __name__ == "__main__":
    main()
