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

    # Short inline string
    echo "Short message" | python3 send.py
"""

import sys
import json
import argparse
import os
import urllib.request

FLASK_URL  = "http://localhost:5001/chunk"
TOKEN_FILE = os.path.expanduser("~/.claude/skills/dnd/display/.token")
TIMEOUT    = 2.0


def _read_token() -> str:
    try:
        return open(TOKEN_FILE).read().strip()
    except FileNotFoundError:
        return ""


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
    args = parser.parse_args()

    text = sys.stdin.read()
    if not text.strip():
        return

    payload: dict = {"text": text}
    if args.player:
        payload["player"] = args.player
    if args.npc:
        payload["npc"] = args.npc
    if args.dice:
        payload["dice"] = True
    if args.tutor:
        payload["tutor"] = True

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
