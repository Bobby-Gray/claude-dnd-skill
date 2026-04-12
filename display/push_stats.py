#!/usr/bin/env python3
"""
push_stats.py — push character/combat stats to the DnD display server.

Stats are merged by player name on the server, so partial updates work.

Usage:
    # Full stats push (on campaign load — read from character sheet):
    python3 push_stats.py --json '{"players":[{"name":"Flerb","race":"Tiefling",...}]}'

    # Quick HP update (damage / healing):
    python3 push_stats.py --player Flerb --hp 7 12         # current max

    # Quick XP update:
    python3 push_stats.py --player Flerb --xp 220 300      # current next_level

    # Feature flag (e.g. Second Wind used):
    python3 push_stats.py --player Flerb --second-wind false

    # Conditions (comma-separated; empty string clears all):
    python3 push_stats.py --player Flerb --conditions "Poisoned,Frightened"
    python3 push_stats.py --player Flerb --conditions ""

    # Concentration:
    python3 push_stats.py --player Flerb --concentrate "Bless"
    python3 push_stats.py --player Flerb --concentrate ""   # clear

    # Combat — set full turn order:
    python3 push_stats.py --turn-order '{"order":["Goblin 1","Flerb"],"current":"Goblin 1","round":1}'

    # Combat — advance turn pointer:
    python3 push_stats.py --turn-current "Flerb"

    # Combat — advance round:
    python3 push_stats.py --turn-round 2

    # Combat ended — clear turn order:
    python3 push_stats.py --turn-clear
"""

import sys
import json
import argparse
import os
import urllib.request

FLASK_URL  = "http://localhost:5001/stats"
TOKEN_FILE = os.path.expanduser("~/.claude/skills/dnd/display/.token")
TIMEOUT    = 2.0


def _read_token() -> str:
    try:
        return open(TOKEN_FILE).read().strip()
    except FileNotFoundError:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Push stats to the DnD display server.")
    parser.add_argument("--json", metavar="JSON",
                        help="Full or partial stats JSON (top-level keys: players, turn_order)")
    parser.add_argument("--player", metavar="NAME",
                        help="Target player name for shorthand flags below")
    parser.add_argument("--hp", nargs=2, metavar=("CURRENT", "MAX"), type=int,
                        help="Update HP (requires --player)")
    parser.add_argument("--xp", nargs=2, metavar=("CURRENT", "NEXT"), type=int,
                        help="Update XP (requires --player)")
    parser.add_argument("--second-wind", metavar="BOOL",
                        help="Second Wind available: true or false (requires --player)")
    parser.add_argument("--conditions", metavar="LIST",
                        help="Comma-separated active conditions (requires --player); empty string clears all")
    parser.add_argument("--concentrate", metavar="SPELL",
                        help="Spell being concentrated on (requires --player); empty string clears")
    parser.add_argument("--turn-order", metavar="JSON",
                        help='Full turn order JSON: {"order":[...],"current":"Name","round":1}')
    parser.add_argument("--turn-current", metavar="NAME",
                        help="Advance the turn pointer to this combatant name")
    parser.add_argument("--turn-round", metavar="N", type=int,
                        help="Set the current round number")
    parser.add_argument("--turn-clear", action="store_true",
                        help="Clear the turn order (combat ended)")
    parser.add_argument("--replace-players", action="store_true",
                        help="Replace the entire player list (use on /dnd load to clear stale characters)")
    parser.add_argument("--world-time", metavar="JSON",
                        help='World time: {"date":"19 Ashveil 1312 AR","day_name":"Moonday","time":"morning","season":"Long Hollow","weather":"calm"}')
    args = parser.parse_args()

    payload: dict = {}

    # ── Full JSON passthrough ──────────────────────────────────────────────────
    if args.json:
        try:
            payload = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # ── Per-player shorthands ──────────────────────────────────────────────────
    if args.hp or args.xp or args.second_wind is not None \
            or args.conditions is not None or args.concentrate is not None:
        if not args.player:
            print("--hp / --xp / --second-wind / --conditions / --concentrate require --player NAME",
                  file=sys.stderr)
            sys.exit(1)
        player_update: dict = {"name": args.player}
        if args.hp:
            player_update["hp"] = {"current": args.hp[0], "max": args.hp[1]}
        if args.xp:
            player_update["xp"] = {"current": args.xp[0], "next": args.xp[1]}
        if args.second_wind is not None:
            player_update["second_wind"] = args.second_wind.lower() == "true"
        if args.conditions is not None:
            # Empty string → clear; otherwise split by comma
            player_update["conditions"] = (
                [c.strip() for c in args.conditions.split(",") if c.strip()]
                if args.conditions.strip() else []
            )
        if args.concentrate is not None:
            player_update["concentration"] = args.concentrate.strip() or None
        payload.setdefault("players", []).append(player_update)

    # ── Turn order ─────────────────────────────────────────────────────────────
    if args.turn_order:
        try:
            payload["turn_order"] = json.loads(args.turn_order)
        except json.JSONDecodeError as e:
            print(f"Invalid turn-order JSON: {e}", file=sys.stderr)
            sys.exit(1)

    if args.turn_current:
        # Partial update: just advance the pointer
        payload["turn_order"] = {"current": args.turn_current}
        if args.turn_round:
            payload["turn_order"]["round"] = args.turn_round

    if args.turn_round and not args.turn_current:
        payload["turn_order"] = {"round": args.turn_round}

    if args.turn_clear:
        payload["turn_order"] = None

    # ── Replace-players flag ───────────────────────────────────────────────────
    if args.replace_players:
        payload["replace_players"] = True

    # ── World time ─────────────────────────────────────────────────────────────
    if args.world_time:
        try:
            payload["world_time"] = json.loads(args.world_time)
        except json.JSONDecodeError as e:
            print(f"Invalid world-time JSON: {e}", file=sys.stderr)
            sys.exit(1)

    if not payload:
        print("Nothing to push. Use --help for usage.", file=sys.stderr)
        return

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = _read_token()
    if token:
        headers["X-DND-Token"] = token
    req = urllib.request.Request(
        FLASK_URL,
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=TIMEOUT)
    except Exception:
        pass  # Display not running — fail silently


if __name__ == "__main__":
    main()
