# DnD DM Display — Cinematic Spectator Screen

Renders your DM session as a cinematic full-screen display on a browser tab.
View it on a TV, iPad, tablet, phone, or second monitor — any device on your network.
You continue typing in the terminal as normal.

```
Terminal (you type here — claude runs directly, no wrapper needed)
    ↓ send.py calls (narration, dice, NPC dialogue, stat changes)
 Flask on http://localhost:5001
    ↓ SSE stream
 Browser tab (any device on your network)
    TV — Cast tab or screen mirror
    iPad / tablet — open in Safari or Chrome via LAN
    Second monitor — open http://localhost:5001 in a local window
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
# Localhost only (default) — HTTP, auto-kills any previous instance
bash ~/.claude/skills/dnd/display/start-display.sh

# LAN mode — HTTP, accessible from phones, tablets, other devices on your network
bash ~/.claude/skills/dnd/display/start-display.sh --lan

# LAN mode with TLS — HTTPS, for public or untrusted networks
bash ~/.claude/skills/dnd/display/start-display.sh --lan --tls
```

**HTTP is the default.** No certificate warnings — guests and new devices connect instantly
with no setup required. This is the recommended mode for home and trusted networks.

**`--tls` is an explicit opt-in** for public or untrusted networks. When `--tls` is used:
- A self-signed certificate is auto-generated (10-year validity, LAN IP in SAN)
- A plain HTTP server starts on `:8080` so devices can download `cert.pem`
- Full per-platform install instructions are printed to the CLI (iOS, Android, Mac)

In LAN mode a token is generated and stored at `.token`. The `send.py` and `push_stats.py`
scripts read this file automatically.

### 3. Open the browser tab

```
http://localhost:5001
# or from another device (LAN mode):
http://<your-machine-ip>:5001
# with --tls:
https://<your-machine-ip>:5001
```

**To display on a TV or other device:**
- **Cast tab** — Chrome → three-dot menu → Cast → Cast tab → select your Chromecast or smart TV
- **Screen mirror** — macOS Control Centre → Screen Mirroring → Apple TV / AirPlay receiver
- **iPad / tablet** — start with `--lan`, open `http://<your-ip>:5001` in Safari or Chrome
- **Second monitor** — drag the browser window to the second display

### 4. Start your Claude session

Run `claude` directly in your terminal — no wrapper needed. The DM skill sends each narration
block, dice result, and stat update to the display via `send.py` calls automatically.

To load a campaign with the display already running:

```
/dnd load <campaign-name>
```

The skill will detect the running display and push party stats, world time, and factions
to the sidebar on load.

---

## How it works

| Component | Role |
|---|---|
| `app.py` | Flask server — receives `send.py` POSTs, strips ANSI/TUI chrome, detects scene from keywords, pushes via SSE |
| `send.py` | Single pipeline for all display updates — narration, dice, NPC dialogue, stat changes, timed effects |
| `push_stats.py` | Bulk stat pushes (party load, turn order, world time, factions) |
| `check_input.py` | Drains the player input queue (autorun mode) — called at turn start |
| `dm_help.py` | One-shot hint fired by the ◈ DM Help button on the display |
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

### Stat sidebar

The right sidebar tracks each party member in real time:

- **HP bar** — current / max, temp HP shown separately
- **XP bar** — progress to next level
- **AC** — armour class
- **Spell slots** — filled pips per level; drain on use, refill on restore
- **Conditions** — coloured pills (red = danger, amber = warn, blue = info, green = buff)
- **Concentration** — purple italic label when active
- **Timed effects** — green pills with live duration: `⧗ Web · 7 rnd` (rounds), `⧗ Disguise Self 1:45` (live countdown), `⧗ Hunter's Mark ∞` (indefinite)
- **Combat turn order** — initiative tracker with current actor highlighted
- **Factions** — party standings (Allied → Hostile)

Click any character's name to open the **full character sheet modal**: attacks, spells, features, inventory, with SRD lookup links on every spell and feature name.

### Timed effects

Effects are started and ended via `send.py` flags, bundled with narration:

```bash
# Start a round-based concentration spell
python3 send.py --effect-start "Aldric:Web:10r:conc" --stat-slot-use "Aldric:2" << 'DNDEND'
Aldric raises his hand and a thick curtain of webbing erupts across the corridor...
DNDEND

# Start a time-based effect (minutes — live countdown in sidebar)
python3 send.py --effect-start "Mira:Disguise Self:1h" << 'DNDEND'
Mira's features shift and blur, settling into an unfamiliar face.
DNDEND

# Narrative end (broken, dispelled, dropped)
python3 send.py --effect-end "Aldric:Web" << 'DNDEND'
The webs shred and fall as Aldric's concentration shatters under the blow.
DNDEND
```

**Duration formats:** `10r` (rounds, decremented server-side on turn advance), `60m` / `8h` (live browser countdown, auto-expires), `indef` (indefinite, cleared by `--effect-end` only).

Append `:conc` to mark as concentration — sets the concentration field and clears any previous concentration spell.

When a round-based effect expires naturally (reaches 0 on turn advance), the display shows an amber expiry block in the feed. Time-based effects expire when the browser countdown hits zero and call `POST /effects/expire` automatically.

**Headless fallback:** if the display is not running, use `tracker.py effect start/end/tick` — effects persist in `tracker.json` and expiry warnings print to terminal.

### Player input panel (autorun mode)

When autorun is enabled, a collapsible input panel appears at the bottom of the display. Players on any device can submit their action before their turn. A pie-clock countdown shows the remaining wait window. When the timer fires or enough players are ready, the queued action is picked up automatically by `check_input.py` at turn start.

Enable autorun:
```
/dnd autorun on
```

### DM Help button

The ◈ button in the top-right corner fires a one-shot hint from `dm_help.py` — a single `--tutor` block appears in the feed with a tactical suggestion for the current situation. This is separate from tutor mode (`/dnd tutor on`) which appends hints to every response.

### Sound effects

`audio.py` scans narration text server-side via compiled regex patterns. On a match it broadcasts `{"sfx": name}` to all connected browsers via SSE. The browser fetches the WAV file from `/audio/sfx/<name>` (synthesized on demand, cached after first request) and plays it via Web Audio API.

**12 effect types:** impact · sword · arrow · shout · thud · magic · coins · door · low_hum · fire · breath

Requires `numpy`. If numpy is not installed the module degrades silently — WAV endpoints return 404 and the Sound Effects toggle in the browser has no effect.

The Sound Effects toggle in the top-right corner of the display enables/disables SFX. The first click also satisfies the browser's autoplay policy for Web Audio.

### Text rendering

- DM output is sent chunk by chunk via `send.py` after each narration block
- ANSI escape codes and TUI chrome (borders, cost bars) are stripped server-side
- Characters render one at a time at ~18ms/char (typewriter effect)
- Gaps of >1.8 seconds between chunks start a new text block
- All previous responses remain visible and scroll naturally
- NPC dialogue renders with an amber border; dice results render in gold inline style; tutor hints render as collapsible parchment blocks

---

## Troubleshooting

**Nothing appears on screen**
- Confirm Flask is running: `curl -s http://localhost:5001/ping` should return `ok` (use `https://` if started with `--tls`)
- Confirm you're running the DM skill (`/dnd load`) rather than bare `claude`
- Check the browser console for SSE connection errors

**Browser shows certificate warning**
- Only expected when started with `--tls`. Click "Advanced → Proceed" once; the browser will remember it.
- In HTTP mode (default) there are no certificate warnings.

**Scene never changes**
- Scene detection requires keywords in the DM narration
- The buffer window is 20 chunks — it may take a few paragraphs to trigger

**Timed effect pills not appearing**
- Confirm `--effect-start` was sent in the `send.py` call that delivered the narration
- Check `stats.json` in the display directory — effects should appear under the player's `effects` array
- If the 2-minute Disguise Self pill isn't counting down, check that `started_at` is a Unix timestamp (not zero)

**Sound effects not playing**
- Click the Sound Effects toggle once to enable; this also unlocks the Web Audio context
- Confirm numpy is installed: `python3 -c "import numpy; print(numpy.__version__)"`
- Check browser console for fetch errors to `/audio/sfx/<name>`

**Particles are slow / choppy**
- Reduce particle count in `index.html` → `PARTICLE_COUNT` object
- Mist and ripples use canvas ellipses; leaves use `save()/restore()` — reduce these first

**LAN mode — browsers on other devices can't connect**
- Confirm the server started with `--lan` (look for `LAN mode (0.0.0.0:5001)` in output)
- Check your machine's firewall allows port 5001 inbound TCP

**TLS cert install — iOS**
- In Safari, open `http://<your-ip>:8080/cert.pem` → tap Allow to download
- Go to Settings → General → VPN & Device Management → install the downloaded profile
- Go to Settings → General → About → Certificate Trust Settings → enable full trust for the cert

---

## Quick reference

```bash
DISPLAY=~/.claude/skills/dnd/display

# Start the display (force-kills any previous instance)
bash $DISPLAY/start-display.sh
# or for LAN access (HTTP, no cert required):
bash $DISPLAY/start-display.sh --lan
# or for LAN with TLS (public/untrusted networks):
bash $DISPLAY/start-display.sh --lan --tls

# Open the display BEFORE starting your session
open http://localhost:5001   # same machine
# or: open http://<your-ip>:5001  (LAN device)
# with --tls: open https://<your-ip>:5001

# Start a session — no wrapper needed
claude   # then: /dnd load <campaign>

# Send narration manually
python3 $DISPLAY/send.py << 'DNDEND'
The door groans open onto darkness.
DNDEND

# Send with stat changes bundled
python3 $DISPLAY/send.py --stat-hp "Mira:8:17" --stat-condition-add "Mira:Poisoned" << 'DNDEND'
The dart catches Mira in the neck. She staggers.
DNDEND

# Start a timed effect
python3 $DISPLAY/send.py --effect-start "Mira:Bless:10r:conc" << 'DNDEND'
Mira's prayer takes hold — a faint golden shimmer surrounds the party.
DNDEND
```
