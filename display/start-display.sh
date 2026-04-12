#!/usr/bin/env bash
# start-display.sh — Launch the DnD cinematic display companion
# Starts app.py in the background if not already running, then opens the browser.
#
# Usage:
#   bash start-display.sh          # localhost only (default)
#   bash start-display.sh --lan    # bind on 0.0.0.0, accessible from LAN devices

DISPLAY_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DISPLAY_DIR/app.log"
PID_FILE="$DISPLAY_DIR/app.pid"

# ── LAN flag ──────────────────────────────────────────────────────────────────
LAN_FLAG=""
LAN_IP=""
if [[ "$1" == "--lan" ]]; then
    LAN_FLAG="--lan"
    # Try common interface names on macOS / Linux
    LAN_IP=$(ipconfig getifaddr en0 2>/dev/null \
          || ipconfig getifaddr en1 2>/dev/null \
          || hostname -I 2>/dev/null | awk '{print $1}')
fi

LOCAL_URL="http://localhost:5001"

# Check if already running
if curl -s "$LOCAL_URL/ping" > /dev/null 2>&1; then
    echo "Display already running at $LOCAL_URL"
    if [[ -n "$LAN_IP" ]]; then
        echo "LAN access: http://$LAN_IP:5001"
    fi
    open "$LOCAL_URL" 2>/dev/null || true
    exit 0
fi

# Start Flask server in background
nohup python3 "$DISPLAY_DIR/app.py" $LAN_FLAG > "$LOG" 2>&1 &
echo $! > "$PID_FILE"

# Wait up to 5 seconds for the server to become ready
for i in $(seq 1 10); do
    sleep 0.5
    if curl -s "$LOCAL_URL/ping" > /dev/null 2>&1; then
        echo "Display started — $LOCAL_URL"
        if [[ -n "$LAN_IP" ]]; then
            echo "LAN access:     http://$LAN_IP:5001"
            echo "Open the LAN URL on your TV/phone/tablet browser, then cast from there."
        fi
        open "$LOCAL_URL" 2>/dev/null || true
        exit 0
    fi
done

echo "Warning: display server may not have started. Check $LOG for details."
exit 1
