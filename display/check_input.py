#!/usr/bin/env python3
"""
check_input.py — Non-blocking check for queued player input.

Prints any pending player input from the display panel to stdout, then clears
the queue. If the queue is empty, prints nothing and exits 0.

Called by the DM at the start of each turn when the display companion is running:
  python3 ~/.claude/skills/dnd/display/check_input.py

Output format (when non-empty):
  [CharName]: action text
  [CharName2]: action text

One line per character. Same format as autorun-wait.sh output.
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

QUEUE_FILE = os.path.expanduser("~/.claude/skills/dnd/display/.input_queue")

try:
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, encoding="utf-8") as f:
            content = f.read().strip()
        os.remove(QUEUE_FILE)
        if content:
            print(content)
except Exception:
    pass
