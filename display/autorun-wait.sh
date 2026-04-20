#!/usr/bin/env bash
# autorun-wait.sh — blocking wait for the next player input in autorun/taxi mode.
#
# Uses a session-ID file (.autorun-session) instead of PID tracking so it works
# correctly when run as a Claude Code background task (process isolation makes PID
# kill unreliable). Writing a new session ID to the file causes any previous wait
# loop to exit gracefully without kill signals.
#
# Broadcasts the countdown to the display, polls for .input_queue, calls
# /queue/consumed on success (clears the display indicator), and prints the
# queue content to stdout. Prints nothing on timeout (9 min).
#
# Usage (from SKILL.md autorun bash block):
#   AUTORUN=$(bash ~/.claude/skills/dnd/display/autorun-wait.sh)

DISPLAY_DIR="$(cd "$(dirname "$0")" && pwd)"
PUSH="${DISPLAY_DIR}/push_stats.py"
QFILE="${HOME}/.claude/skills/dnd/display/.input_queue"
SESSION_FILE="${DISPLAY_DIR}/.autorun-session"

# ── Invalidate any previous wait loop by writing a new session ID ─────────────
MY_SESSION="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
echo "$MY_SESSION" > "$SESSION_FILE"

# Clean up session file on exit (only if it's still ours)
trap '[[ "$(cat "$SESSION_FILE" 2>/dev/null)" == "$MY_SESSION" ]] && rm -f "$SESSION_FILE"' EXIT

# Read autorun_interval from active campaign's state.md (default 60s)
INTERVAL=$(python3 -c "
import re, os
try:
    camp = open(os.path.expanduser('~/.claude/skills/dnd/display/.campaign')).read().strip()
    txt = open(os.path.expanduser(f'~/.claude/dnd/campaigns/{camp}/state.md')).read()
    m = re.search(r'autorun_interval:\s*(\d+)', txt)
    print(int(m.group(1)) if m else 60)
except Exception: print(60)
" 2>/dev/null || echo 60)

python3 "$PUSH" --autorun-waiting true --autorun-cycle "$INTERVAL"

# ── Poll loop — exits when queue file appears, session changes, or 9 min pass ──
AUTORUN=$(python3 - "$MY_SESSION" "$QFILE" "$SESSION_FILE" << 'PYEOF'
import sys, os, time

my_session, qfile, session_file = sys.argv[1], sys.argv[2], sys.argv[3]
max_count = 1800   # 0.3s * 1800 = 9 minutes

for _ in range(max_count):
    # Queue file appeared — consume and return content
    if os.path.exists(qfile):
        try:
            content = open(qfile).read()
            os.unlink(qfile)
            print(content, end='')
        except Exception:
            pass
        break

    # Session ID changed — a newer autorun-wait.sh started; exit silently
    try:
        if open(session_file).read().strip() != my_session:
            break
    except Exception:
        break

    time.sleep(0.3)
PYEOF
)

python3 "$PUSH" --autorun-waiting false

# Clear the display queue indicator on success
if [ -n "$AUTORUN" ]; then
  python3 -c "
import ssl, urllib.request, os
try:
    ddir = '$DISPLAY_DIR'
    scheme_file = os.path.join(ddir, '.scheme')
    scheme = open(scheme_file).read().strip() if os.path.exists(scheme_file) else 'http'
    token = open(os.path.expanduser('~/.claude/skills/dnd/display/.token')).read().strip()
    ctx = None
    if scheme == 'https':
        ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req = urllib.request.Request(f'{scheme}://localhost:5001/queue/consumed', data=b'', method='POST', headers={'X-DND-Token': token})
    urllib.request.urlopen(req, timeout=1, context=ctx)
except: pass
" 2>/dev/null
fi

printf '%s' "$AUTORUN"
