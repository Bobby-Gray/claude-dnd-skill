#!/usr/bin/env python3
"""Local dice server: bridges the D&D skill <-> per-player phone tabs.

Player-scoped lobby model: each phone opens /?player=NAME and joins that
player's channel. The DM script (dice.py) sends a roll with --player NAME
and the server pushes it only to that player's phone(s). LAN-only by default.

Channels
--------
- "<player_name>"  : a specific player's tab
- "_dm"            : the DM's own tab (no --player passed)
- physical=False or no subscribers on the target channel → server auto-rolls
  so play never deadlocks if a phone is closed.
"""
import uuid, os, socket, queue, json, time, re, random
from collections import defaultdict
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response

HERE = Path(__file__).parent
PORT = int(os.environ.get("DND_DICE_PORT", "7777"))
DM_CHANNEL = "_dm"

app = Flask(__name__)
rolls = {}                                    # id -> roll record
subscribers = defaultdict(list)               # channel -> list[queue.Queue]


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def broadcast(channel: str, event: dict):
    dead = []
    for q in subscribers.get(channel, []):
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        subscribers[channel].remove(q)


SPEC_RE = re.compile(r"^(\d*)d(\d+)(?:k([hl])(\d+))?([+-]\d+)?$", re.I)


def parse_spec(spec: str):
    m = SPEC_RE.match(spec.replace(" ", ""))
    if not m:
        raise ValueError(f"bad dice spec: {spec}")
    return {
        "count": int(m.group(1) or "1"),
        "sides": int(m.group(2)),
        "keep_dir": m.group(3).lower() if m.group(3) else None,
        "keep_n": int(m.group(4)) if m.group(4) else None,
        "mod": int(m.group(5) or "0"),
    }


def server_side_roll(spec: str) -> dict:
    p = parse_spec(spec)
    raw = [random.randint(1, p["sides"]) for _ in range(p["count"])]
    if p["keep_dir"]:
        s = sorted(raw, reverse=True)
        kept = s[: p["keep_n"]] if p["keep_dir"] == "h" else s[-p["keep_n"]:]
    else:
        kept = list(raw)
    return {
        "total": sum(kept) + p["mod"],
        "rolls": raw,
        "kept": kept,
        "modifier": p["mod"],
        "spec": spec,
    }


@app.post("/roll")
def new_roll():
    data = request.get_json(force=True)
    spec = data["spec"]
    label = data.get("label", "")
    physical = data.get("physical", True)
    player = data.get("player") or DM_CHANNEL

    channel_subs = len(subscribers.get(player, []))

    # Auto-roll fallback: explicit physical=False OR no one subscribed on the target channel
    if not physical or channel_subs == 0:
        reason = "physical=false" if not physical else f"no subscribers on '{player}'"
        result = server_side_roll(spec)
        result["auto"] = True
        result["auto_reason"] = reason
        rid = str(uuid.uuid4())
        rolls[rid] = {"spec": spec, "label": label, "player": player,
                      "result": result, "created": time.time()}
        return {"id": rid, "auto": True, "result": result}

    rid = str(uuid.uuid4())
    rolls[rid] = {"spec": spec, "label": label, "player": player,
                  "result": None, "created": time.time()}
    broadcast(player, {"type": "roll", "id": rid, "spec": spec, "label": label, "player": player})
    return {"id": rid, "subscribers": channel_subs, "channel": player, "auto": False}


@app.post("/submit/<rid>")
def submit(rid):
    if rid not in rolls:
        return {"error": "unknown id"}, 404
    rolls[rid]["result"] = request.get_json(force=True)
    return {"ok": True}


@app.get("/spec/<rid>")
def spec(rid):
    if rid not in rolls:
        return {"error": "unknown id"}, 404
    r = rolls[rid]
    return jsonify({"spec": r["spec"], "label": r["label"], "player": r.get("player")})


@app.get("/result/<rid>")
def result(rid):
    return jsonify(rolls.get(rid, {"result": None}))


@app.get("/events")
def events():
    channel = request.args.get("player") or DM_CHANNEL
    q = queue.Queue(maxsize=64)
    subscribers[channel].append(q)

    def gen():
        try:
            yield f"data: {json.dumps({'type': 'hello', 'channel': channel})}\n\n"
            # Replay any unfilled rolls for this channel
            for rid, r in list(rolls.items()):
                if (r["result"] is None
                        and r.get("player") == channel
                        and (time.time() - r["created"]) < 300):
                    yield ("data: " + json.dumps({
                        "type": "roll", "id": rid, "spec": r["spec"],
                        "label": r["label"], "player": r.get("player"),
                    }) + "\n\n")
            while True:
                try:
                    msg = q.get(timeout=20)
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            if q in subscribers.get(channel, []):
                subscribers[channel].remove(q)

    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.get("/")
def page():
    return send_file(HERE / "dice.html")


@app.get("/health")
def health():
    counts = {k: len(v) for k, v in subscribers.items() if len(v) > 0}
    return {"ok": True, "subscribers": counts}


if __name__ == "__main__":
    ip = get_lan_ip()
    print("🎲 dice server")
    print(f"   local:   http://localhost:{PORT}")
    print(f"   network: http://{ip}:{PORT}/?player=<your-name>   ← players")
    print(f"            http://{ip}:{PORT}/                       ← DM tab")
    app.run(port=PORT, host="0.0.0.0", threaded=True)
