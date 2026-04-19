#!/usr/bin/env bash
# start-display.sh — Launch the DnD cinematic display companion
#
# Usage:
#   bash start-display.sh              # localhost only, HTTP (default)
#   bash start-display.sh --lan        # LAN mode, HTTP  ← use this for home/trusted networks
#   bash start-display.sh --lan --tls  # LAN mode, HTTPS ← use this on public/untrusted networks
#
# HTTP is the default. Guests and new devices connect instantly with no setup.
# TLS adds encryption but requires a one-time certificate install on each device.

DISPLAY_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DISPLAY_DIR/app.log"
PID_FILE="$DISPLAY_DIR/app.pid"
CERT_SERVER_PID="$DISPLAY_DIR/.cert-server.pid"

# ── Parse flags ───────────────────────────────────────────────────────────────
LAN_FLAG=""
TLS_MODE=false

for arg in "$@"; do
  case "$arg" in
    --lan) LAN_FLAG="--lan" ;;
    --tls) TLS_MODE=true ;;
  esac
done

if $TLS_MODE && [[ -z "$LAN_FLAG" ]]; then
  echo "Error: --tls requires --lan (TLS is only meaningful for network access)"
  exit 1
fi

# ── Get LAN IP ────────────────────────────────────────────────────────────────
LAN_IP=""
if [[ -n "$LAN_FLAG" ]]; then
  LAN_IP=$(ipconfig getifaddr en0 2>/dev/null \
        || ipconfig getifaddr en1 2>/dev/null \
        || hostname -I 2>/dev/null | awk '{print $1}')
fi

# ── TLS: generate cert if missing, then start cert server ────────────────────
if $TLS_MODE; then
  if [[ ! -f "$DISPLAY_DIR/cert.pem" || ! -f "$DISPLAY_DIR/key.pem" ]]; then
    echo "Generating self-signed certificate..."
    openssl req -x509 -newkey rsa:2048 \
      -keyout "$DISPLAY_DIR/key.pem" \
      -out    "$DISPLAY_DIR/cert.pem" \
      -days 3650 -nodes \
      -subj "/CN=dnd-display" \
      -addext "subjectAltName=IP:${LAN_IP:-127.0.0.1},IP:127.0.0.1" 2>/dev/null \
    && echo "Certificate generated (valid 10 years)." \
    || { echo "Error: openssl not found. Install it or use HTTP mode (remove --tls)."; exit 1; }
  fi

  # Start cert server (plain HTTP on :8080 so devices can download the cert)
  if [[ -f "$CERT_SERVER_PID" ]]; then
    kill "$(cat "$CERT_SERVER_PID")" 2>/dev/null || true
    rm -f "$CERT_SERVER_PID"
  fi
  python3 -m http.server 8080 --directory "$DISPLAY_DIR" > /dev/null 2>&1 &
  echo $! > "$CERT_SERVER_PID"
else
  # HTTP mode: shut down any leftover cert server from a previous TLS session
  if [[ -f "$CERT_SERVER_PID" ]]; then
    kill "$(cat "$CERT_SERVER_PID")" 2>/dev/null || true
    rm -f "$CERT_SERVER_PID"
  fi
fi

SCHEME=$($TLS_MODE && echo "https" || echo "http")

# ── Force-kill previous display instance ─────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
  kill -9 "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
fi
pkill -9 -f "python3.*${DISPLAY_DIR}/app\.py" 2>/dev/null || true
sleep 0.3

# ── Start Flask ───────────────────────────────────────────────────────────────
APP_ARGS="$LAN_FLAG"
$TLS_MODE && APP_ARGS="$APP_ARGS --tls"

nohup python3 "$DISPLAY_DIR/app.py" $APP_ARGS > "$LOG" 2>&1 &
echo $! > "$PID_FILE"

LOCAL_URL="${SCHEME}://localhost:5001"

# Wait up to 5 s for the server to become ready
for i in $(seq 1 10); do
  sleep 0.5
  if curl -sk "$LOCAL_URL/ping" > /dev/null 2>&1; then
    echo ""
    echo "Display started — $LOCAL_URL"
    [[ -n "$LAN_IP" ]] && echo "LAN access:     ${SCHEME}://${LAN_IP}:5001"

    if $TLS_MODE; then
      echo ""
      echo "══════════════════════════════════════════════════════════════"
      echo "  TLS MODE — one-time certificate install required per device"
      echo "══════════════════════════════════════════════════════════════"
      echo ""
      echo "  A plain HTTP server is running on :8080 so devices can"
      echo "  download the cert without needing to trust it first."
      echo ""
      echo "  Step 1 — on each new device, open:"
      echo "           http://${LAN_IP}:8080/cert.pem"
      echo ""
      echo "  iOS (iPhone / iPad):"
      echo "    Safari will say 'Allow' to download → tap Allow"
      echo "    Settings → General → VPN & Device Management → install profile"
      echo "    Settings → General → About → Certificate Trust Settings → enable"
      echo ""
      echo "  Android:"
      echo "    Chrome downloads the file → open it → install as CA Certificate"
      echo ""
      echo "  Mac (other than this machine):"
      echo "    Open cert.pem → Keychain Access → mark as Always Trust"
      echo ""
      echo "  Step 2 — open  https://${LAN_IP}:5001  in the device browser."
      echo "  No further warnings after the cert is trusted."
      echo ""
      echo "  The cert server on :8080 runs until the display is stopped."
      echo ""
      echo "  NOTE: TLS is only needed on public or untrusted networks."
      echo "  For home/trusted LANs, plain HTTP (--lan, no --tls) is"
      echo "  simpler: guests connect instantly with no setup required."
      echo "══════════════════════════════════════════════════════════════"
    fi

    open "$LOCAL_URL" 2>/dev/null || true
    exit 0
  fi
done

echo "Warning: display server may not have started. Check $LOG for details."
exit 1
