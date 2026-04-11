# DnD DM Display — Cinematic Spectator Screen

Renders your DM session as a cinematic full-screen display on a browser tab,
which you Chromecast to your TV. You continue typing in the terminal as normal.

```
Terminal (you type here)
    ↓ stdout captured by wrapper.py
 Flask on localhost:5001
    ↓ SSE stream
 Browser tab → Chromecast → TV
 (or any LAN device: phone, tablet)
```

---

## Setup

### 1. Install dependencies

```bash
cd ~/.claude/skills/dnd/display
pip3 install -r requirements.txt
```

### 2. Start the Flask server

```bash
# Localhost only (default)
python3 ~/.claude/skills/dnd/display/app.py

# LAN mode — serve to phones, tablets, other devices on your network
python3 ~/.claude/skills/dnd/display/app.py --lan
```

In LAN mode a token is generated and stored at `.token`. The `send.py` and `push_stats.py`
scripts read this file automatically.

### 3. Open the browser tab

```
http://localhost:5001
# or from another device:
http://<your-machine-ip>:5001
```

Chromecast this tab to your TV via Chrome → three-dot menu → Cast → Cast tab.

### 4. Start your Claude session via the wrapper

```bash
python3 ~/.claude/skills/dnd/display/wrapper.py
python3 ~/.claude/skills/dnd/display/wrapper.py --resume
```

---

## How it works

| Component | Role |
|---|---|
| `wrapper.py` | Spawns `claude` in a PTY, tees its stdout to the Flask server |
| `app.py` | Receives text, strips ANSI/TUI chrome, detects scene from keywords, pushes via SSE |
| `audio.py` | Scans narration for SFX triggers; serves synthesized WAV files to browsers |
| `index.html` | Typewriter rendering, sky canvas, particle system, CSS gradient crossfades |

### Scene detection

The Flask server scans each text chunk for keywords and derives a scene:

| Scene | Keywords (sample) | Particles |
|---|---|---|
| Tavern / Inn | tavern, inn, hearth, ale, candle | Embers |
| Mine | mine, seam, shaft, ore | Dust |
| Forest | forest, wood, tree, hollow wood | Leaves |
| Dungeon | dungeon, corridor, torch | Dust |
| Temple | temple, shrine, altar, lantern | Smoke |
| Crypt | crypt, tomb, bones, undead | Smoke |
| Night | night, midnight, moon, star | Stars |
| Arcane | arcane, spell, rune, sigil | Sparks |
| Mountain | mountain, snow, blizzard | Snow |
| Ocean / Docks | ocean, sea, ship, wave, dock | Ripples |
| Desert | desert, sand, dune | Sand |
| City / Town | city, street, market | Rain |
| Cave | cave, grotto, stalactite | Mist |
| Swamp | swamp, bog, marsh | Mist |

Background gradient and particle type transition smoothly over ~2.5 seconds when the scene changes.

### Dynamic sky canvas

A canvas layer above the scene background renders a live sky driven by `world_time` data:

- **Time of day** — sun arcs from dawn through midday to dusk; crescent moon + twinkling stars at night; orange horizon at twilight
- **Weather** — calm (sparse clouds) → overcast → rainy → stormy (near-black); all affect cloud density, color, and opacity
- **Clouds** — 5 cloud objects drifting left, each rendered as 8 overlapping circles; wrap to opposite edge

Push world_time updates via `push_stats.py`:

```bash
python3 push_stats.py --world-time \
  '{"date":"19 Ashveil 1312 AR","day_name":"Moonday","time":"morning","season":"Long Hollow","weather":"calm"}'
```

Valid `time`: `dawn`, `morning`, `midday`, `afternoon`, `evening`, `dusk`, `night`  
Valid `weather`: `calm`, `clear`, `overcast`, `rainy`, `stormy`

### Sound effects

`audio.py` scans narration text server-side via compiled regex patterns. On a match it broadcasts `{"sfx": name}` to all connected browsers via SSE. The browser fetches the WAV file from `/audio/sfx/<name>` (synthesized on demand, cached after first request) and plays it via Web Audio API.

**12 effect types:** impact · sword · arrow · shout · thud · magic · coins · door · low_hum · fire · breath

Requires `numpy`. If numpy is not installed the module degrades silently — WAV endpoints return 404 and the Sound Effects toggle in the browser has no effect.

The Sound Effects toggle in the top-right corner of the display enables/disables SFX. The first click also satisfies the browser's autoplay policy for Web Audio.

### Text rendering

- DM output streams in as chunks from the Claude CLI
- ANSI escape codes and TUI chrome (borders, cost bars) are stripped server-side
- Characters render one at a time at ~18ms/char (typewriter effect)
- Gaps of >1.8 seconds between chunks start a new text block
- All previous responses remain visible and scroll naturally

---

## Troubleshooting

**Nothing appears on screen**
- Confirm Flask is running: `curl http://localhost:5001/ping` should return `ok`
- Confirm wrapper is running (not bare `claude`)
- Check the browser console for SSE connection errors

**Text looks garbled / shows control characters**
- The ANSI stripper may need tuning for your Claude CLI version
- Open an issue at the project repo with a sample of the raw output

**Scene never changes**
- Scene detection requires keywords in the DM narration
- The buffer window is 20 chunks — it may take a few paragraphs to trigger

**Sound effects not playing**
- Click the Sound Effects toggle once to enable; this also unlocks the Web Audio context
- Confirm numpy is installed: `python3 -c "import numpy; print(numpy.__version__)"`
- Check browser console for fetch errors to `/audio/sfx/<name>`

**Particles are slow / choppy**
- Reduce particle count in `index.html` → `PARTICLE_COUNT` object
- Mist and ripples use canvas ellipses; leaves use `save()/restore()` — reduce these first

**LAN mode — browsers on other devices can't connect**
- Confirm the server started with `--lan` (look for `LAN mode (0.0.0.0:5001)` in output)
- Check your machine's firewall allows port 5001 inbound

---

## Quick reference

```bash
DISPLAY=~/.claude/skills/dnd/display

# Terminal 1 — Flask server
python3 $DISPLAY/app.py
# or for LAN access:
python3 $DISPLAY/app.py --lan

# Browser — open and Chromecast BEFORE starting your session
open http://localhost:5001

# Terminal 2 — Claude session via wrapper
python3 $DISPLAY/wrapper.py
python3 $DISPLAY/wrapper.py --resume   # resume existing session
```
