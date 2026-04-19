#!/usr/bin/env bash
# autorun-wait.sh — blocking wait for the next player input in autorun/taxi mode.
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
WAIT_PID_FILE="${DISPLAY_DIR}/.autorun-wait.pid"

# ── Kill any previous autorun-wait instance ───────────────────────────────────
if [[ -f "$WAIT_PID_FILE" ]]; then
  OLD_PID=$(cat "$WAIT_PID_FILE")
  # Kill the whole process group so the inner poll loop dies too
  kill -- -"$OLD_PID" 2>/dev/null || kill "$OLD_PID" 2>/dev/null || true
  rm -f "$WAIT_PID_FILE"
  sleep 0.1
fi
echo $$ > "$WAIT_PID_FILE"

# Clean up PID file on exit
trap 'rm -f "$WAIT_PID_FILE"' EXIT

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

# Counter-loop (macOS has no GNU timeout)
AUTORUN=$(bash -c '
  QFILE=~/.claude/skills/dnd/display/.input_queue
  COUNT=0
  while ! [ -f "$QFILE" ] && [ "$COUNT" -lt 1800 ]; do sleep 0.3; COUNT=$((COUNT+1)); done
  [ -f "$QFILE" ] && cat "$QFILE" && rm -f "$QFILE"
' 2>/dev/null)

python3 "$PUSH" --autorun-waiting false

# Clear the display queue indicator
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
