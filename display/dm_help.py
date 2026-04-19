#!/usr/bin/env python3
"""
dm_help.py — On-demand DM hint generator.

Called by Flask /help-request endpoint as a subprocess.
Reads recent display log + campaign state.md + current session-log.md entry,
calls the Claude API, sends result to the display via send.py --tutor.

Context hierarchy (most → least current):
  1. text_log.json   — real-time scene (last N display blocks)
  2. session-log.md  — current session events and open threads (authoritative for in-session state)
  3. state.md        — campaign-level persistent context (targeted sections only; may lag)

Lock lifecycle:
  Flask creates .help-lock (O_EXCL) before spawning this process.
  This script removes .help-lock in its finally block.
  Multiple browser clicks → Flask returns 409 on all but the first.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

BASE      = pathlib.Path("~/.claude/skills/dnd").expanduser()
LOCK_FILE = BASE / "display" / ".help-lock"
LOG_FILE  = BASE / "display" / "text_log.json"
SEND_PY   = BASE / "display" / "send.py"

# Sections to extract from state.md.
# Deliberately excludes "## Open Threads & Rumours" and "## Recent Events"
# because those go stale during a session — session-log.md is more current.
STATE_SECTIONS = [
    "## Current Situation",
    "## Active Quests",
    "## World State",
    "## Session Flags",
]
STATE_SECTION_LINE_LIMIT = 20  # per section — keeps prompt tight


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def get_recent_display(n: int = 10) -> str:
    """Return the last n display blocks as labelled text, skipping previous tutor blocks."""
    if not LOG_FILE.exists():
        return ""
    try:
        data = json.loads(LOG_FILE.read_text())
    except Exception:
        return ""
    recent = data[-n:] if len(data) >= n else data
    parts = []
    for item in recent:
        if not isinstance(item, dict) or "text" not in item:
            continue
        if item.get("tutor"):
            continue  # don't feed prior hints back as scene context
        text = item["text"].strip()
        if item.get("player"):
            parts.append(f"[PLAYER ACTION] {text}")
        elif item.get("npc"):
            parts.append(f"[NPC: {item.get('npc', '')}] {text}")
        elif item.get("dice"):
            parts.append(f"[DICE] {text}")
        else:
            parts.append(f"[DM] {text}")
    return "\n\n".join(parts)


def get_campaign_state(campaign: str) -> str:
    """
    Extract targeted sections from state.md.
    Skips Open Threads and Recent Events — those go stale mid-session.
    session-log.md is the authoritative source for in-session state.
    """
    state_path = pathlib.Path(
        f"~/.claude/dnd/campaigns/{campaign}/state.md"
    ).expanduser()
    if not state_path.exists():
        return ""
    text = state_path.read_text()
    parts = []
    for header in STATE_SECTIONS:
        match = re.search(
            rf"(^{re.escape(header)}.*?)(?=^## |\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            lines = match.group(1).strip().splitlines()[:STATE_SECTION_LINE_LIMIT]
            parts.append("\n".join(lines))
    return "\n\n".join(parts)


def get_session_context(campaign: str) -> str:
    """
    Extract the most recent session entry from session-log.md.
    This is the authoritative source for what has actually happened in the
    current session — more current than state.md during an active session.
    Falls back to the archive if the main log is empty or has no sessions.
    """
    log_path = pathlib.Path(
        f"~/.claude/dnd/campaigns/{campaign}/session-log.md"
    ).expanduser()
    if not log_path.exists():
        return ""
    text = log_path.read_text()

    # Find all session headers — "## Session N" or "## Session N — ..."
    matches = list(re.finditer(r"^## Session \d+", text, re.MULTILINE))
    if not matches:
        return ""

    # Take the last (most recent) session
    last_start = matches[-1].start()
    session_text = text[last_start:]

    # Hard limit: 100 lines is enough for Key Events + Open Threads
    lines = session_text.splitlines()[:100]
    return "\n".join(lines)


def call_claude(display: str, state: str, session: str) -> str:
    """Call claude -p (non-interactive print mode) — uses Claude Code's own auth."""
    system = (
        "You are a D&D 5e Dungeon Master generating a brief in-character DM hint. "
        "You are given three sources of context in decreasing order of freshness: "
        "(1) RECENT SCENE — the last few display blocks, most current; "
        "(2) CURRENT SESSION — key events and open threads logged this session, authoritative "
        "for what has actually happened; "
        "(3) CAMPAIGN STATE — persistent campaign context, may lag behind current session events. "
        "If sources conflict, trust RECENT SCENE first, then CURRENT SESSION, then CAMPAIGN STATE. "
        "Based on this context, identify the single most useful thing the player may not have "
        "considered right now: a skill check worth attempting and what it would reveal; "
        "2-3 visible options at this decision point noting which close doors permanently; "
        "if there is an irreversible risk begin with: ⚠ WARNING:; "
        "or an unused class feature or reaction relevant to this exact moment. "
        "Rules: 2-4 sentences maximum. Write from inside the fiction — no rule names, "
        "no meta-language. Never reveal information the character could not know. "
        "If there is genuinely nothing useful to add, respond with exactly: SKIP"
    )

    prompt_parts = []
    if state:
        prompt_parts.append(f"CAMPAIGN STATE:\n{state}")
    if session:
        prompt_parts.append(f"CURRENT SESSION (authoritative — trust over campaign state):\n{session}")
    if display:
        prompt_parts.append(f"RECENT SCENE (most current — trust over all other sources):\n{display}")
    prompt_parts.append("Generate a DM hint for the player's current situation.")

    prompt = "\n\n".join(prompt_parts)

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", "claude-sonnet-4-6",
            "--system-prompt", system,
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        return "SKIP"

    return result.stdout.strip()


def send_tutor(text: str) -> None:
    subprocess.run(
        [sys.executable, str(SEND_PY), "--tutor"],
        input=text,
        text=True,
        capture_output=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and send an on-demand DM hint.")
    parser.add_argument("--campaign", required=True, help="Campaign directory name")
    args = parser.parse_args()

    try:
        display = get_recent_display(10)
        state   = get_campaign_state(args.campaign)
        session = get_session_context(args.campaign)

        if not display and not state and not session:
            return

        hint = call_claude(display, state, session)
        if hint.strip().upper() == "SKIP":
            return

        send_tutor(hint)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
