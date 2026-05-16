"""Drop-in roll() for the claude-dnd-skill.

Usage:
    from roll_client import roll
    result = roll("1d20+5", label="Attack roll")          # physical (phone)
    result = roll("1d8",    label="Goblin HP", physical=False)  # auto

The server will also auto-roll if `physical=True` but no clients are
connected, so player rolls won't deadlock if the phone tab is closed.
"""
import os, time, urllib.request, json

PORT = int(os.environ.get("DND_DICE_PORT", "7777"))
BASE = f"http://localhost:{PORT}"


def _post(path: str, data: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return json.loads(r.read())


def roll(spec: str, label: str = "", *, physical: bool = True,
         player: str | None = None, timeout: float = 180.0) -> dict:
    """Request a roll; block until result.

    spec     -- dice notation, e.g. "1d20+5", "4d6kh3", "2d20kh1"
    label    -- shown in the browser HUD
    physical -- True (default) routes to a phone; False auto-rolls server-side
    player   -- name of the player whose phone should receive the roll.
                None routes to the DM channel.
    timeout  -- seconds to wait for a physical roll
    """
    payload = {"spec": spec, "label": label, "physical": physical}
    if player:
        payload["player"] = player
    r = _post("/roll", payload)
    if r.get("auto"):
        return r["result"]

    rid = r["id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = _get(f"/result/{rid}")
        if res.get("result") is not None:
            return res["result"]
        time.sleep(0.4)
    raise TimeoutError(f"no roll within {timeout}s for {spec}")


if __name__ == "__main__":
    import sys
    spec = sys.argv[1] if len(sys.argv) > 1 else "1d20+5"
    label = sys.argv[2] if len(sys.argv) > 2 else "test roll"
    physical = "--auto" not in sys.argv
    print(f"rolling {spec} ({'physical' if physical else 'auto'})...")
    print(json.dumps(roll(spec, label, physical=physical), indent=2))
