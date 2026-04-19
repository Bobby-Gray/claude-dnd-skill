# Unofficial D&D Claude Dungeon Master
### *with Cinematic Display Companion — Couch Co-op Edition*

> Claude runs the game. You play. The TV shows the story. Your phone is your controller.

An unofficial D&D 5e Dungeon Master skill for [Claude Code](https://claude.ai/code) — persistent campaigns, full 5e mechanics, and an optional cinematic display companion that streams typewriter narration, dice rolls, and live character stats to any screen — TV via Chromecast, tablet, phone, or second monitor — while players submit their actions from a phone or tablet.

Built for groups who want a real DM experience without needing one at the table.

![Cinematic Display Demo](demo-v2.gif)

---

## What This Is

You run `/dnd load my-campaign` in Claude Code. Claude becomes your DM — rolling dice, voicing NPCs, tracking HP and XP, and running combat. If you have a TV or tablet nearby, the **cinematic display companion** puts the narration on screen in real time — typewriter effect, atmospheric backgrounds that shift with the scene, a dynamic sky canvas, and a live party stat sidebar. Open it on any device on your network and everyone at the table can follow along. Players submit their actions from their phones; Claude picks them up automatically and runs the next turn.

What separates this from a chatbot improvising a story is a set of [twelve applied behavioral standards](https://github.com/Bobby-Gray/claude-dnd-skill/blob/main/SKILL.md#what-makes-a-great-dm--applied-standards) enforced as hard constraints on every session. They cover the full range of what makes DM-ing genuinely difficult and the result is sessions that feel authored — where moments land, where the world has weight, and where your choices accumulate into a story that couldn't have happened to anyone else.

It also manages a deep web of campaign data without overloading the LLM — coherent and complete, without burning tokens on context that isn't needed yet:

- **DM instructions** — split across three files with staggered load timing; core rules always in the system prompt, script syntax and command procedures loaded once at session start
- **Campaign data** — NPC roster indexed at load, full entries pulled only when a character becomes relevant; quest hooks and worldbuilding text in cold storage until called for
- **Session history** — archived as continuity summaries, not raw transcripts; full campaign history available for reference without front-loading token weight

A campaign can run dozens of sessions deep — with coherent recall of past events, NPC attitudes, and long-tail consequences — without the context bloat that forces other implementations to summarize, forget, or reset.

It is not an official Wizards of the Coast product. It uses Claude as the DM engine. It takes the rules seriously and the storytelling even more seriously.

---

## Using a different LLM?

This skill is built specifically for Claude Code. If you want to run the same framework on a different model — local inference, OpenRouter, or any OpenAI-compatible endpoint — check out [open-tabletop-gm](https://github.com/Bobby-Gray/open-tabletop-gm), the model-agnostic version extracted from this repo. It trades some Claude-specific integration depth for broader model support and includes a probe tool for benchmarking narration quality across models.

If you're on Claude Code, you're in the right place.

---

## Features

- **Persistent campaigns** — state, NPCs, quests, and characters survive across sessions in plain markdown files
- **Portable characters** — bring your character into any campaign; level up, grow your stat tree, and carry your inventory and loot — or start fresh each time
- **Full D&D 5e mechanics** — initiative, attacks, saving throws, spell slots, XP, levelling up, short/long rests
- **Atmospheric DM** — dark fantasy tone, distinct NPC voices, hidden rolls, a world that reacts to choices
- **Cinematic display companion** — typewriter narration on your TV, scene-reactive backgrounds, dynamic sky canvas, live party sidebar; cast, mirror, or open on any screen on your network
- **Dynamic sky canvas** — sun arc, moon, twinkling stars, and cloud density rendered in real time from world time data; transitions with time of day and weather
- **Player input from the companion UI** — players submit actions from phone/tablet; Claude picks them up automatically in autorun mode
- **Autorun / taxi mode** — Claude drives the turn loop without DM input; a pie countdown shows the next auto-fire window
- **LAN party support** — serve the companion over your local network; every device in the room sees the same display
- **TLS / HTTPS** — self-signed cert generation included; required for full browser feature support over LAN
- **17 scene types** — auto-detected from narration keywords — tavern, dungeon, ocean, crypt, arcane, glacier, and more
- **Clickable character sheets** — tap any sidebar card to open a full character sheet modal (attacks, features, inventory); works on phones and tablets via LAN
- **SRD spell/feature lookup** — click any spell or feature name in a character sheet to view its full description; bundled 5e dataset with supplemental entries for non-SRD content (Xanathar's, Tasha's, subclass features); wikidot fallback link shown for anything not in the local data
- **DM Help button** — click the ◈ button on the display for an on-demand contextual hint or warning; generated from the current scene without per-turn token overhead
- **Tutor / learning mode** — enable per-session for automatic hint blocks after every scene, decision point, and roll; ideal for players new to D&D
- **Browser-side sound effects** — 12 SFX types synthesized on demand via numpy and played through Web Audio API; works on any device with the tab open, including phones over LAN
- **Couch co-op** — multiple characters, shared display, turn order visible to everyone in the room
- **Combat tracker** — auto-rolled initiative, `▶` turn pointer, HP bars, inline dice math sent to display
- **Helper scripts** — dice rolling, ability scores, combat, character stat derivation, conditions/tracker, calendar, SRD data sync, SRD lookup, supplemental data builder

---

## How It Works

```
Claude Code CLI  ──→  /dnd commands  ──→  campaign files (~/.claude/dnd/)
                                              state.md · world.md · npcs.md
                                              session-log.md · characters/

Display pipeline (autorun mode):
  Players (phone/tablet)  ──→  Companion UI  ──→  Flask SSE server (localhost:5001)
                                                          ↓
                                                   autorun-wait.sh
                                                          ↓
                                                   Claude processes turn
                                                          ↓
                                              send.py / push_stats.py  ──→  TV display
```

The Flask server receives narration text, player actions, dice results, and character stats via HTTP POST. It broadcasts everything in real time to connected browsers via Server-Sent Events. The browser renders narration as a typewriter effect over a scene-reactive gradient background with a live character sidebar. In autorun mode Claude polls for player submissions and processes each turn automatically.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed
- Python 3.10+
- `pip3 install flask flask-cors numpy cryptography` (display companion; numpy required for sound effects, cryptography for LAN TLS)

---

## Installation

```bash
# 1. Clone into your Claude skills directory
git clone https://github.com/Bobby-Gray/claude-dnd-skill ~/.claude/skills/dnd

# 2. Install display companion dependencies (optional)
pip3 install flask flask-cors numpy cryptography

# 3. That's it — no other setup required
```

> **Claude Code skills** live in `~/.claude/skills/`. Once cloned, the `/dnd` command is available in any Claude Code session.

---

## Quick Start

```
/dnd new my-campaign         # create a new campaign
/dnd character new           # create a character
/dnd load my-campaign        # start a session (asks about display companion)
```

Once loaded, type naturally — no `/dnd` prefix needed. The DM interprets everything as in-game action.

---

## Campaign Commands

| Command | Description |
|---------|-------------|
| `/dnd new <name>` | Create a new campaign — generates world seed, NPCs, starting location |
| `/dnd load <name>` | Load an existing campaign and enter DM mode |
| `/dnd save` | Write session events to log, update state and character files |
| `/dnd end` | Save session, append recap, stop display companion |
| `/dnd abandon` | Exit without saving — discards all unsaved changes from this session |
| `/dnd list` | List all campaigns with last session date and count |
| `/dnd recap` | In-character 3–5 sentence recap of the last session |
| `/dnd world` | Display world lore |
| `/dnd quests` | Show active quests and open threads |
| `/dnd autorun on [seconds]` | Enable autorun mode — Claude drives the turn loop automatically |
| `/dnd autorun off` | Return to manual mode |
| `/dnd tutor on` | Enable tutor / learning mode for this session |
| `/dnd tutor off` | Disable tutor / learning mode |
| `/dnd data sync` | Rebuild bundled SRD dataset from upstream sources (only needed for new upstream content) |
| `/dnd data status` | Show current dataset record counts and upstream SHA |

---

## Character Commands

| Command | Description |
|---------|-------------|
| `/dnd character new` | Create a character — guided point buy or rolled stats |
| `/dnd character sheet [name]` | Display a character sheet |
| `/dnd level up [name]` | Level up a character — applies class features, HP roll |

### Character Creation

The creation flow walks through:
1. Name, race, class, background
2. **Point buy** (validates against 27-point budget) or **rolled** (3 arrays of 4d6kh3 to choose from)
3. Racial bonuses applied automatically
4. Derived stats calculated via `character.py`
5. Starting equipment assigned by class + background
6. Sheet written to `characters/<name>.md`

---

## Combat System

```
/dnd combat start
```

1. Identifies all combatants, collects DEX mods, HP, AC
2. Auto-rolls initiative for **every combatant** including PCs — results sent to display
3. Tracks HP, conditions, turn order across rounds
4. Resolves NPC/monster attacks inline with full dice math:
   ```
   Goblin attacks: d20(14) + 4 = 18 vs AC 16 — hit! 1d6(3) + 2 = 5 piercing
   ```
5. Players roll their own attack/skill/save numbers — DM resolves everything else

### Combat Display

During combat the sidebar shows a live turn order with a `▶` pointer:

```
— COMBAT — Round 2
▶ Aldric
  Skeleton
  Mira
```

The pointer advances after each turn. HP bars update in real time when damage is taken. Combat ends with `--turn-clear`.

---

## NPC System

```
/dnd npc Osk             # portray an existing NPC or generate a new one
/dnd npc attitude Osk friendly   # shift attitude on the 5-step scale
```

Every NPC gets: role, stat block, demeanor, motivation, secret, and a speech quirk. Attitudes shift on a 5-step scale: `hostile → unfriendly → neutral → friendly → allied`. Changes are logged with reason and date in `npcs.md`.

---

## Resting

```
/dnd rest short    # 1 hour — spend Hit Dice, recharge some features
/dnd rest long     # 8 hours — full HP, half Hit Dice back, all spell slots
```

Long rests advance the in-world clock in `state.md`.

---

## Cinematic Display Companion

An optional local web server (`display/app.py`) that renders DM narration on any screen — TV, tablet, phone, or second monitor. Cast it, mirror it, or open it on any device on your local network.

### Setup

```bash
pip3 install flask flask-cors numpy cryptography
```

### Starting the Display

The display starts automatically when you answer **y** at the `/dnd load` prompt. Or start it manually:

```bash
# Local only (Mac/same machine)
bash ~/.claude/skills/dnd/display/start-display.sh

# LAN mode — accessible to phones/tablets on your network
bash ~/.claude/skills/dnd/display/start-display.sh --lan
```

Then open `https://localhost:5001` in your browser. The first time you'll see a certificate warning for the self-signed cert — click through it. For LAN devices use the IP URL printed at startup (e.g. `https://192.168.1.x:5001`).

### Viewing Options

Open the display URL in a browser, then choose how to show it:

| Option | How |
|--------|-----|
| **TV — Cast tab** | Chrome → three-dot menu → Cast → Cast tab; select your Chromecast or smart TV |
| **TV — Screen mirror** | macOS: Control Centre → Screen Mirroring → Apple TV / AirPlay receiver |
| **iPad / tablet** | Start with `--lan`, open `https://<your-ip>:5001` in Safari or Chrome; works in landscape |
| **Second monitor** | Open `https://localhost:5001` in a browser window and drag it to the second display |

### TLS / HTTPS Setup

LAN mode requires HTTPS (mobile browsers require it for SSE and clipboard features). A self-signed cert is generated automatically on first `--lan` start, or you can regenerate it manually:

```bash
python3 ~/.claude/skills/dnd/display/setup_tls.py
```

This creates `cert.pem` + `key.pem` in the display folder with SANs for `localhost` and your current LAN IP. Import `cert.pem` into your phone's trusted certs to eliminate the browser warning on mobile.

### Player Input from the Companion UI

![Player input panel — staging an action from a phone](screenshot-player-input.png)

Players open the companion in their phone browser. The **Party Input** panel at the bottom lets each player:

1. **Stage** an action — type it and hit Stage. It appears in the panel visible to everyone.
2. **Mark Ready** — confirms the action is final.
3. **Skip** — passes the turn without typing.

When all players (or a configured minimum) are ready, the combined input fires to Claude automatically.

The panel shows a **"Next Turn"** countdown pie clock that loops at the configured interval. When a submission is picked up, the "Queued" indicator clears and three pulsing dots appear in the main chat confirming Claude received it and is thinking.

### Autorun Mode

Autorun is the primary way to run sessions with the companion UI. Once enabled, Claude drives the turn loop without requiring the DM to press Enter between each turn.

```
/dnd autorun on          # enable — 60s default countdown
/dnd autorun on 45       # enable with 45-second countdown
/dnd autorun off         # return to manual mode
```

The countdown is configurable per-campaign by setting `autorun_interval: N` in `state.md → ## Session Flags`. To interrupt autorun from the Claude Code CLI, press **Ctrl+C** during the wait.

**N-player threshold** — by default autorun fires when all known players are ready. For multi-device groups you can require only N players:

```bash
python3 ~/.claude/skills/dnd/display/push_stats.py --autorun-threshold 2  # fire when 2 ready
python3 ~/.claude/skills/dnd/display/push_stats.py --autorun-threshold 0  # reset to player count
```

### DM Help & Tutor Mode

There are two ways to surface hints and warnings on the display — an on-demand button and a per-session automatic mode.

**DM Help button (◈)** — a **◈ DM Help** button sits in the bottom-right corner of the display at all times. Click it and within a few seconds a contextual hint or warning is generated from the current scene and pushed to the display — no CLI command needed, no per-turn token overhead. The button reads the last 8 display blocks and current campaign state, calls Claude in non-interactive mode, and sends the result as a hint block via the normal SSE pipeline. Shows "Thinking…" while in flight; resets automatically when the block arrives. Multiple simultaneous clicks only trigger one execution.

Hint blocks are **collapsed by default** — click or tap the header to expand. Warnings use an amber border:

- **DM Hint** (◈, collapsible) — skills worth attempting, visible options, what each path might cost
- **Warning** (⚠, amber border) — flags irreversible choices before the player commits

![Tutor mode intro hint](tutor-hint-intro.png)

Hints can surface contextual NPC and situation knowledge the DM would naturally flag:

![Tutor hint with NPC context](tutor-hint-npc.png)

Warnings use an amber border to distinguish high-stakes choices:

![Tutor warning block](tutor-warning.png)

**Tutor mode (per-session)** — for new players who want continuous guidance, enable automatic hint blocks after every scene, decision point, and roll — no button needed. Adds ~10–20% token overhead per turn. Use the DM Help button instead for on-demand hints without the ongoing cost.

```
/dnd tutor on    # enable for this session
/dnd tutor off   # disable
```

Tutor mode is session-scoped — does not persist to the next `/dnd load` unless set again.

The two are independent — the ◈ button is always available regardless of whether tutor mode is on.

---

### Scene Detection

The server scans narration text for keywords and crossfades the background gradient and particle type to match the current environment. Scenes change automatically as the story moves.

| Scene | Trigger Keywords | Particles |
|-------|-----------------|-----------|
| Tavern | inn, hearth, ale, tallow, barkeep | embers |
| Dungeon | corridor, torch, portcullis, dank | dust |
| Ocean / Docks | dock, harbour, wave, tide, ship | ripples |
| Forest | tree, canopy, moss, thicket, grove | leaves |
| Crypt | tomb, undead, skeleton, burial | smoke |
| Arcane | ritual, rune, sigil, incantation | sparks |
| Mountain | glacier, frost, blizzard, ridge | snow |
| Cave | stalactite, grotto, echo, drip | mist |
| Night | midnight, moon, constellation | stars |
| City / Town | market, cobble, district, crowd | rain |
| Swamp | swamp, bog, marsh, mire | mist |
| + 6 more | mine, castle, ruins, desert, fire, temple | — |

Scene transitions crossfade over ~2.5 seconds. The server maintains a 20-chunk rolling window for detection so scenes don't flicker on single keyword matches.

### Dynamic Sky Canvas

A canvas layer rendered above the scene background shows a live sky that reacts to `world_time` data pushed via `push_stats.py`:

- **Time of day** — sun arcs from dawn (lower-left) through midday (top-center) to dusk (lower-right); switches to crescent moon + twinkling stars at night; twilight shows an orange horizon
- **Weather** — calm: 2 light clouds; overcast: 5 heavy dark clouds, dimmed sun; rainy: dense cloud cover, muted palette; stormy: near-black sky; clear night: full star field
- **Clouds** — 5 cloud objects each built from 8 overlapping circles; drift slowly and wrap

Push world time data after loading a campaign and after any rest or time advance:

```bash
python3 ~/.claude/skills/dnd/display/push_stats.py --world-time \
  '{"date":"7 Deepmonth 1312 CR","day_name":"Starday","time":"morning","season":"Deep Winter","weather":"overcast"}'
```

Valid `time` values: `dawn`, `morning`, `midday`, `afternoon`, `evening`, `dusk`, `night`
Valid `weather` values: `calm`, `clear`, `overcast`, `rainy`, `stormy`

### Sound Effects

Narration text is scanned server-side for 12 SFX trigger categories. When a match is found, the browser fetches a synthesized WAV file and plays it via Web Audio API — no server audio output, works on any device with the tab open.

```
impact · sword · arrow · shout · thud · magic · coins · door · low_hum · fire · breath
```

SFX synthesis uses numpy — if numpy is not installed the feature degrades silently. Enable via the **Sound Effects** toggle in the top-right of the display.

| Narration text | SFX |
|----------------|-----|
| "...strikes the shield..." | impact |
| "...draws her blade..." | sword |
| "...looses an arrow..." | arrow |
| "...he roars across the dock..." | shout |
| "...collapses to the floor..." | thud |
| "...arcane energy crackles..." | magic |
| "...coins spill across the table..." | coins |
| "...the door creaks open..." | door |
| "...the altar hums with energy..." | low_hum |
| "...the torch flares..." | fire |
| "...a sharp exhale..." | breath |

The browser caches each WAV after first fetch. SFX trigger naturally alongside the typewriter animation since both are driven by the same narration chunks.

### Live Character Sidebar

![NPC dialogue block and character sidebar with faction panel](screenshot-npc-dialogue.png)

A fixed left sidebar shows live stats for all party members, updated automatically as play progresses.

```bash
# Push full stats on campaign load (clears stale characters from previous campaigns)
python3 ~/.claude/skills/dnd/display/push_stats.py --replace-players --json '{
  "players": [{
    "name": "Aldric", "race": "Human", "class": "Fighter", "level": 2,
    "hp": {"current": 14, "max": 18}, "xp": {"current": 220, "next": 300},
    "ac": 17, "initiative": "+1", "speed": 30,
    "hit_dice": {"remaining": 2, "max": 2, "die": "d10"},
    "ability_scores": {
      "str": {"score": 16, "mod": "+3"}, "dex": {"score": 12, "mod": "+1"},
      "con": {"score": 15, "mod": "+2"}, "int": {"score": 10, "mod": "+0"},
      "wis": {"score": 11, "mod": "+0"}, "cha": {"score": 13, "mod": "+1"}
    }
  }]
}'

# Partial updates during play
python3 ~/.claude/skills/dnd/display/push_stats.py --player Aldric --hp 10 18
python3 ~/.claude/skills/dnd/display/push_stats.py --player Aldric --xp 270 300
python3 ~/.claude/skills/dnd/display/push_stats.py --player Aldric --conditions-add "Poisoned"
python3 ~/.claude/skills/dnd/display/push_stats.py --player Aldric --slot-use 2

# Or bundle stat changes directly with a narration send (no separate push_stats.py call needed):
python3 ~/.claude/skills/dnd/display/send.py \
  --stat-hp "Aldric:10:18" \
  --stat-condition-add "Aldric:Poisoned" \
  --stat-slot-use "Aldric:1" << 'EOF'
The goblin's blade catches Aldric across the ribs...
EOF

# Combat turn order
python3 ~/.claude/skills/dnd/display/push_stats.py \
  --turn-order '{"order":["Aldric","Skeleton","Mira"],"current":"Aldric","round":1}'

# Advance turn pointer
python3 ~/.claude/skills/dnd/display/push_stats.py --turn-current "Skeleton"

# Combat ended
python3 ~/.claude/skills/dnd/display/push_stats.py --turn-clear

# World time clock
python3 ~/.claude/skills/dnd/display/push_stats.py --world-time \
  '{"date":"7 Deepmonth 1312 CR","day_name":"Starday","time":"morning","season":"Deep Winter","weather":"overcast"}'
```

![Character sidebar card](sidebar-card.png)

### Clickable Character Sheet

Click or tap any character card in the sidebar to open a full character sheet modal — attacks, features, and inventory at a glance. Works on desktop and on phones/tablets connected via LAN.

![Character sheet modal](character-sheet-modal.png)

Include the `sheet` field when pushing stats on `/dnd load` to populate the full sheet:

```bash
python3 ~/.claude/skills/dnd/display/push_stats.py --replace-players --json '{
  "players": [{
    "name": "Aldric",
    ...
    "sheet": {
      "attacks": [
        {"name": "Longsword", "bonus": "+5", "damage": "1d8+3", "type": "Slashing", "notes": "Versatile (1d10)"}
      ],
      "features": [
        {"name": "Second Wind", "text": "Bonus action: regain 1d10+level HP. Short/long rest recharge."}
      ],
      "inventory": ["Longsword", "Chain Mail", "Shield", "Explorer'\''s Pack", "15 gp"]
    }
  }]
}'
```

If `sheet` is omitted, the modal still opens but shows only the stats visible in the sidebar. Close with **Esc**, clicking outside the panel, or the ✕ button.

Clicking a spell or feature name inside the sheet opens a description modal sourced from the bundled SRD dataset. Scaling progressions (e.g. Sneak Attack damage) automatically collapse to the character's current level. If a spell or feature isn't in the core SRD dataset, a link to the relevant page on D&D 5e Wiki is shown instead. To extend the local dataset with non-SRD content from a character file:

```bash
python3 ~/.claude/skills/dnd/scripts/build_supplemental.py --character ~/.claude/dnd/campaigns/<name>/characters/<charname>.md
```

This fetches descriptions from dnd5e.wikidot.com for any missing entries and writes them to `data/dnd5e_supplemental.json`. Run it once after creating or importing a character. A pre-built supplemental covering Circle of Spores, Thief archetype features, and several Xanathar's spells ships with the skill.

The sidebar:
- Shows compact dual-column cards for parties of 2+ (full ability grid for solo play)
- HP bars shift green → yellow → red as HP drops
- XP bar fills toward next level
- Active conditions displayed per character
- Spell slot pips track remaining charges
- Fades in automatically on first stats push
- Persists across Flask restarts (`stats.json`)
- Cleared automatically on `/dnd new` (fresh campaign)

### Replay Buffer

The server buffers the last 60 text chunks to disk (`text_log.json`). Reconnecting browsers (Chromecast drop, tab refresh) replay the full session history automatically — no narration is lost.

---

## Scripts Reference

All scripts live in `~/.claude/skills/dnd/scripts/`.

### `dice.py` — All dice rolls

```bash
python3 scripts/dice.py d20+5
python3 scripts/dice.py 2d6+3
python3 scripts/dice.py d20 adv          # advantage
python3 scripts/dice.py d20+3 dis        # disadvantage + modifier
python3 scripts/dice.py 4d6kh3          # keep highest 3 (ability score roll)
python3 scripts/dice.py d20 --silent    # integer only (for hidden rolls)
```

Flags nat 20 (`CRITICAL HIT`) and nat 1 (`FUMBLE`) automatically.

### `ability-scores.py` — Character creation

```bash
python3 scripts/ability-scores.py roll                          # 3 arrays to choose from
python3 scripts/ability-scores.py pointbuy                     # print cost table
python3 scripts/ability-scores.py pointbuy --check STR=15 DEX=10 CON=15 INT=8 WIS=11 CHA=12
python3 scripts/ability-scores.py modifiers STR=15 DEX=10 CON=15 INT=8 WIS=11 CHA=12
```

### `combat.py` — Initiative and attack resolution

```bash
# Roll initiative for all combatants and print tracker
python3 scripts/combat.py init '[
  {"name":"Aldric","dex_mod":1,"hp":18,"ac":17,"type":"pc"},
  {"name":"Skeleton","dex_mod":2,"hp":13,"ac":13,"type":"npc"}
]'

# Reprint tracker from saved state
python3 scripts/combat.py tracker '<state_json>' <round_num>

# Resolve a single attack
python3 scripts/combat.py attack --atk 5 --ac 13 --dmg 1d8+3
```

`init` outputs a `STATE_JSON:` line — save this to `state.md` under `## Active Combat` for persistence between turns.

### `build_supplemental.py` — Extend the SRD dataset with non-SRD content

Run after creating or importing a character to fetch descriptions for spells and features not in the core SRD:

```bash
# Scan a character file and fetch anything missing
python3 scripts/build_supplemental.py --character ~/.claude/dnd/campaigns/<name>/characters/<charname>.md

# Scan all characters in a campaign at once
python3 scripts/build_supplemental.py --campaign <campaign-name>

# Add a specific entry by name
python3 scripts/build_supplemental.py --add "Toll the Dead" spell
python3 scripts/build_supplemental.py --add "Halo of Spores" feature

# See what's currently cached
python3 scripts/build_supplemental.py --list

# Preview what would be fetched without writing
python3 scripts/build_supplemental.py --campaign <name> --dry-run
```

Fetches from `dnd5e.wikidot.com` with a polite request delay. Uses Python stdlib only — no extra dependencies. Writes to `data/dnd5e_supplemental.json`, which `lookup.py` merges at load time.

---

### `character.py` — Stat derivation and levelling

```bash
# Full stat block from raw scores
python3 scripts/character.py calc --class fighter --level 2 \
    STR=16 DEX=12 CON=15 INT=10 WIS=11 CHA=13 \
    --proficient STR CON Athletics Intimidation Perception Survival

# Level-up
python3 scripts/character.py levelup --class fighter --from 2 --hp-roll 8 --con-mod 2

# XP tracking
python3 scripts/character.py xp --level 2 --gained 150
```

---

## File Layout

```
~/.claude/skills/dnd/
├── SKILL.md                  # Skill definition and DM instructions
├── SKILL-scripts.md          # Script and tool syntax reference
├── SKILL-commands.md         # /dnd command procedures
├── README.md                 # This file
├── data/
│   ├── dnd5e_srd.json        # Bundled 5e SRD dataset (1453 records — spells, features, equipment, monsters)
│   └── dnd5e_supplemental.json  # Non-SRD content (Xanathar's, subclass features, etc.)
├── scripts/
│   ├── dice.py
│   ├── ability-scores.py
│   ├── combat.py
│   ├── character.py
│   ├── tracker.py
│   ├── calendar.py
│   ├── lookup.py             # SRD + supplemental query API
│   ├── build_srd.py          # Fetches upstream 5e data and builds dnd5e_srd.json
│   ├── sync_srd.py           # Checks upstream SHAs; rebuilds only on new commits
│   └── build_supplemental.py # Fetches non-SRD entries from wikidot for a character or campaign
├── display/
│   ├── app.py                # Flask SSE server
│   ├── audio.py              # SFX synthesis and browser trigger (numpy)
│   ├── autorun-wait.sh       # Blocking wait script for autorun mode
│   ├── send.py               # Direct send for narration/dice/player actions
│   ├── push_stats.py         # Character and combat stat updates
│   ├── setup_tls.py          # Self-signed TLS cert generator for LAN mode
│   ├── start-display.sh      # One-command display startup
│   ├── dm_help.py            # On-demand DM hint generator (◈ button)
│   ├── check_input.py        # Legacy player input queue reader
│   ├── wrapper.py            # PTY wrapper (legacy — autorun preferred)
│   ├── requirements.txt
│   └── templates/
│       └── index.html        # Browser frontend
└── templates/
    ├── character-sheet.md
    ├── state.md
    ├── world.md
    ├── npcs.md
    └── session-log.md

~/.claude/dnd/campaigns/<name>/
├── state.md                  # Current location, party status, active quests
├── world.md                  # World lore and setting details
├── npcs.md                   # NPC index with stat blocks and attitudes
├── session-log.md            # Session history and recaps
└── characters/
    ├── Aldric.md
    └── Mira.md
```

---

## DM Philosophy

The skill is designed around a set of hard constraints, not aspirational notes:

- **Improvise over script** — the world is a sandbox; player choices always find a "yes, and..."
- **Consequences are real** — NPCs remember conversations; factions shift; failure is possible
- **Economy of description** — two sharp sensory details beat a paragraph of exposition
- **Every NPC is a person** — even minor characters get a verbal tic, a contradiction, a goal
- **Hidden rolls stay hidden** — Perception, Insight, and Stealth roll silently; only the outcome is narrated (but results always appear on the display)

---

## License

MIT
