# Physical Dice Server (optional)

A small local web server that gives every player at the table a 3D dice tray on
their phone. When the DM (Claude) rolls for a player character, the dice are
pushed to that player's phone, where they shake or tap to cast — and the result
is returned to the campaign.

It's fully optional: the [`scripts/dice.py`](../scripts/dice.py) command checks
for the server at startup and falls back to local Python `random` if it isn't
running, so installing this changes nothing about the skill's default behavior.

---

## How it feels

1. The DM (Claude Code) is sitting on the table with the skill loaded.
2. Each player opens `http://<dm-mac-ip>:7777/?player=<their-pc-name>` on their
   phone once at the start of the session and taps "tap to consecrate."
3. When the DM resolves an action — *"Make a Perception check"* — Claude runs
   `dice.py d20+4 --player piper --label "Perception"`.
4. Piper's phone vibrates a 3D d20 onto a candle-lit table. Piper shakes the
   phone. The die tumbles, settles, and Piper sees the result.
5. The result returns to Claude, which narrates the outcome.

NPC / monster / hidden DM rolls are kept off the players' phones (omit
`--player`); they auto-roll server-side and only Claude sees them.

---

## Requirements

- macOS or Linux host (the DM's machine running Claude Code)
- Python 3.9+ with Flask: `pip3 install flask`
- All phones on the same Wi-Fi as the host (LAN-only by design)
- A reasonably modern phone browser — the dice scene uses WebGL via Three.js
  loaded from `unpkg.com`. Tested on iOS 16+ Safari and Chrome.

---

## Install

### Quickest: run it in the foreground

```bash
python3 dice-server/server.py
```

You'll see something like:

```
🎲 dice server
   local:   http://localhost:7777
   network: http://192.168.1.42:7777/?player=<your-name>   ← players
            http://192.168.1.42:7777/                       ← DM tab
```

Players open the `?player=...` URL on their phones. Done.

### Recommended on macOS: launchd auto-start

```bash
./dice-server/install-launchd.sh
```

This installs `~/Library/LaunchAgents/com.dnd-skill.dice-server.plist`, starts
the server, and keeps it running across logins / crashes. Re-run the script to
upgrade or after moving the skill directory. To remove:

```bash
launchctl unload ~/Library/LaunchAgents/com.dnd-skill.dice-server.plist
rm ~/Library/LaunchAgents/com.dnd-skill.dice-server.plist
```

### Linux

The server is a plain Flask app. Run it under systemd, screen, tmux, or in a
terminal — whatever you prefer. Bind address is `0.0.0.0:7777` by default;
change with `DND_DICE_PORT=8081`.

---

## How players join

Each player opens this URL on their phone, substituting their own PC name:

```
http://<dm-mac-ip>:7777/?player=piper
```

Lowercase, no spaces (use hyphens). The name must match what the DM passes via
`--player` in `dice.py`. Convention is to use the PC's short name.

The phone should be kept open and on the active tab during play. The page
holds a screen wake-lock so it won't sleep mid-session.

If a player closes the tab, rolls addressed to them will instead auto-roll
server-side — the game never deadlocks waiting for a missing phone.

---

## Skill integration

The opt-in is already wired into `scripts/dice.py`:

```bash
# DM-resolved roll (NPC attacks, monster saves, etc.)
python3 scripts/dice.py d20+5 --label "Goblin attack"

# Player roll — routes to that player's phone
python3 scripts/dice.py d20+4 --label "Perception" --player piper

# Force-skip the physical roller for this one call
python3 scripts/dice.py d20+5 --auto

# Force-skip globally for a session
DND_DICE_PHYSICAL=0 python3 scripts/dice.py d20+5
```

If the server isn't running, the script silently falls back to local random
— exactly the original `dice.py` behavior. So a campaign can be played on a
machine without the server installed and nothing breaks.

When the server *was* used but no phone was on the target channel, the output
gets an `[auto]` tag so you know the result came from the server rather than
a physical cast:

```
Roll: 17 + 5 = 22 [auto]
```

---

## What it looks like

The phone scene is a single `<canvas>` rendered with [Three.js](https://threejs.org/):
real polyhedron geometry (`IcosahedronGeometry` for d20,
`DodecahedronGeometry` for d12, etc.), PBR brass material lit by a warm key
light and a cool blue rim, dice numbered with engraved bronze decals drawn to
canvas textures (Cormorant Garamond typography), hand-rolled physics
(gravity, bounce, settle-to-target-face), and synthesized audio (clatter,
thud per bounce, chime on a natural 20). It tone-maps in ACES with a subtle
film-grain overlay for the antique-print mood.

No external CDN dependencies other than Three.js itself and Google Fonts —
no `node_modules`, no build step, no compilation.

---

## Protocol (for the curious)

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /` | — | The dice page. Add `?player=NAME` to subscribe a channel. |
| `GET /events` | SSE | Server-Sent Events stream of rolls for this player's channel (default: `_dm`). |
| `POST /roll` | JSON | `{"spec":"1d20+5","label":"...","player":"piper","physical":true}` |
| `GET /spec/<id>` | — | Returns the spec for an in-flight roll (page uses this on load). |
| `POST /submit/<id>` | JSON | `{"total":17,"rolls":[12],"kept":[12],"modifier":5,"spec":"1d20+5"}` |
| `GET /result/<id>` | — | Poll for a roll's result (used by `dice.py`). |
| `GET /health` | — | `{"ok":true,"subscribers":{"piper":1}}` |

The notation supported by the server matches `dice.py`:
`NdM[kh|kl N][+|-K]` (e.g. `4d6kh3`, `2d20kh1+5`).

---

## Privacy & security

- LAN-only: binds `0.0.0.0:7777`. There's no auth — anyone on the same Wi-Fi
  can connect, see rolls, and trigger fake rolls. This is intentional for a
  trusted home/table setting.
- Do not expose the port to the internet without adding auth.
- No telemetry, no analytics, no outbound network calls beyond Three.js +
  Google Fonts on the player's phone (both load over HTTPS direct from CDNs).

---

## Why this exists

The default `dice.py` rolls deterministically in Python. That's fine, but it
removes the moment a die actually lands — the tiny rite that makes D&D feel
like a ritual rather than a chat. This bolts that moment back on without
changing how the skill works for anyone who doesn't want it.
