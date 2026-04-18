# D&D Skill — Scripts Reference

Full syntax for all Python helper scripts. Load this file once at `/dnd load`, then it stays in context for the session.

---

## Dice Script — `scripts/dice.py`
```bash
python3 ~/.claude/skills/dnd/scripts/dice.py d20+5
python3 ~/.claude/skills/dnd/scripts/dice.py 2d6+3
python3 ~/.claude/skills/dnd/scripts/dice.py 4d6kh3        # ability score roll
python3 ~/.claude/skills/dnd/scripts/dice.py d20 adv       # advantage
python3 ~/.claude/skills/dnd/scripts/dice.py d20+3 dis     # disadvantage + modifier
python3 ~/.claude/skills/dnd/scripts/dice.py d20 --silent  # returns integer only
```
Flags nat 20 (CRITICAL HIT) and nat 1 (FUMBLE) automatically.

---

## Ability Scores Script — `scripts/ability-scores.py`
```bash
python3 ~/.claude/skills/dnd/scripts/ability-scores.py roll
python3 ~/.claude/skills/dnd/scripts/ability-scores.py pointbuy
python3 ~/.claude/skills/dnd/scripts/ability-scores.py pointbuy --check STR=15 DEX=10 CON=15 INT=8 WIS=11 CHA=12
python3 ~/.claude/skills/dnd/scripts/ability-scores.py modifiers STR=15 DEX=10 CON=15 INT=8 WIS=11 CHA=12
```
Roll mode: generates 3 arrays (4d6kh3 × 6 each). Point buy mode: prints cost table; `--check` validates against the 27-point budget.

---

## XP Script — `scripts/xp.py`
Awards XP for combat and qualifying non-combat encounters. Reads character files from the campaign directory, updates XP, and pushes to the display sidebar. All tables (difficulty thresholds, CR→XP, monster multipliers, level advancement) are codified in the script — the DM only decides the difficulty tier or provides a monster list.

```bash
# Preview — no files modified:
python3 ~/.claude/skills/dnd/scripts/xp.py calc --level 3 --players 2 --difficulty hard --type combat
python3 ~/.claude/skills/dnd/scripts/xp.py calc --level 3 --players 2 --monsters "goblin:1/4:3,hobgoblin:1:1"

# Award after a combat encounter — difficulty-rated (use when full monster list is unavailable):
python3 ~/.claude/skills/dnd/scripts/xp.py award \
  --campaign <name> --characters "Aldric,Mira" --difficulty hard --type combat

# Award after a combat encounter — exact CR calculation (preferred for standard combats):
python3 ~/.claude/skills/dnd/scripts/xp.py award \
  --campaign <name> --characters "Aldric,Mira" \
  --monsters "goblin:1/4:3,hobgoblin:1:1" --note "Ambush in the alley"

# Award for a qualifying non-combat encounter:
python3 ~/.claude/skills/dnd/scripts/xp.py award \
  --campaign <name> --characters "Aldric,Mira" --difficulty medium --type noncombat \
  --note "guild informant interrogation"
```

**Difficulty tiers:** `easy` `medium` `hard` `deadly`
**Encounter types:** `combat` `noncombat` (both use the same difficulty threshold table)
**Monster CR formats:** `1/4`, `0.25`, `1/2`, `0.5`, `1/8`, `0.125`, or integer (`1`, `5`, `10`)
**Monster count:** omit for 1 (e.g. `"dragon:10"`); explicit for groups (e.g. `"goblin:1/4:3"`)
**Monster multiplier** (applied automatically): ×1 (1), ×1.5 (2), ×2 (3–6), ×2.5 (7–10), ×3 (11–14), ×4 (15+)

`award` updates the character file XP field, flags LEVEL UP PENDING if a threshold is crossed, and pushes XP to the display via `push_stats.py`. The `--note` label prints to terminal only — not stored.

---

## Combat Script — `scripts/combat.py`
```bash
# Roll initiative and print tracker
python3 ~/.claude/skills/dnd/scripts/combat.py init '<JSON>'
# JSON: [{"name":"Flerb","dex_mod":0,"hp":12,"ac":16,"type":"pc"}, ...]

# Reprint tracker from saved state
python3 ~/.claude/skills/dnd/scripts/combat.py tracker '<JSON>' <round_num>

# Resolve a single attack
python3 ~/.claude/skills/dnd/scripts/combat.py attack --atk 4 --ac 15 --dmg 2d6+2
```
`init` outputs `STATE_JSON:` line — store in `state.md` under `## Active Combat` between turns.

---

## Character Script — `scripts/character.py`
```bash
# Full stat block from raw scores
python3 ~/.claude/skills/dnd/scripts/character.py calc --class fighter --level 1 \
    STR=15 DEX=10 CON=15 INT=9 WIS=11 CHA=14 \
    --proficient STR CON Athletics Intimidation Perception Survival

# Level-up HP and bonus calculation
python3 ~/.claude/skills/dnd/scripts/character.py levelup --class fighter --from 1 --hp-roll 7 --con-mod 2

# XP tracking
python3 ~/.claude/skills/dnd/scripts/character.py xp --level 1 --gained 150
```

---

## Stats Display Script — `display/push_stats.py`
Pushes character and combat stats to the sidebar. Players merged by name; partial updates work.

```bash
# Full stats push (on /dnd load — use --replace-players to clear stale characters):
python3 ~/.claude/skills/dnd/display/push_stats.py --replace-players --json '{
  "players": [{
    "name": "Flerb", "race": "Tiefling", "class": "Fighter", "level": 1, "background": "Soldier",
    "hp": {"current": 12, "max": 12, "temp": 0},
    "xp": {"current": 220, "next": 300},
    "ac": 16, "initiative": "+0", "speed": 30,
    "hit_dice": {"remaining": 1, "max": 1, "die": "d10"},
    "second_wind": true,
    "ability_scores": {
      "str": {"score": 15, "mod": "+2"}, "dex": {"score": 10, "mod": "+0"},
      "con": {"score": 15, "mod": "+2"}, "int": {"score": 9, "mod": "-1"},
      "wis": {"score": 11, "mod": "+0"}, "cha": {"score": 14, "mod": "+2"}
    },
    "sheet": {
      "attacks": [
        {"name": "Longsword", "bonus": "+4", "damage": "1d8+2", "type": "Slashing", "notes": "Versatile (1d10)"},
        {"name": "Handaxe",   "bonus": "+4", "damage": "1d6+2", "type": "Slashing", "notes": "Thrown 20/60 ft"}
      ],
      "spells": null,
      "features": [
        {"name": "Second Wind",  "text": "Bonus action: regain 1d10+level HP. Recharges on short/long rest."},
        {"name": "Action Surge", "text": "Once per rest: take an additional action on your turn."}
      ],
      "inventory": ["Longsword", "Handaxe ×2", "Chain Mail", "Shield", "Explorer'\''s Pack", "15 gp"]
    }
  }]
}'

# sheet sub-keys: attacks, spells ({slots, save_dc, attack_bonus, cantrips, prepared} or null),
# features ([{name, text}]), inventory ([strings])
# sheet is optional — omit if you only need the stats sidebar without the full sheet modal

# Partial updates (use whenever values change mid-session):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --hp 7 12
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --xp 220 300
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --second-wind false

# Temp HP (Symbiotic Entity, Aid, etc.):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --temp-hp 8   # set
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --temp-hp 0   # clear

# Hit dice (short rest):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --hit-dice-use          # spend one
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --hit-dice-restore 2    # restore N

# Conditions — full replace:
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --conditions "Poisoned,Frightened"
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --conditions ""          # clear all

# Conditions — granular (preferred mid-session):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --conditions-add "Poisoned"
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --conditions-remove "Poisoned"

# Concentration:
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --concentrate "Bless"
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --concentrate ""        # clear

# Spell slots — full replace (on /dnd load):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb \
  --spell-slots '{"1":{"used":1,"max":4},"2":{"used":0,"max":2}}'

# Spell slots — granular (preferred mid-session):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --slot-use 1      # expend one 1st-level slot
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --slot-restore 2  # restore one 2nd-level slot

# Inventory — granular (preferred to full --sheet rewrite):
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --inventory-add "Iron key"
python3 ~/.claude/skills/dnd/display/push_stats.py --player Flerb --inventory-remove "Folded paper"

# Faction standings (party-wide — REQUIRED at /dnd load to show faction panel):
python3 ~/.claude/skills/dnd/display/push_stats.py \
  --factions '[{"name":"Pale Court","standing":"Allied"},{"name":"Watch","standing":"Neutral"}]'
python3 ~/.claude/skills/dnd/display/push_stats.py --factions '[]'   # clear all

# Combat turn order (on /dnd combat start):
python3 ~/.claude/skills/dnd/display/push_stats.py --turn-order \
  '{"order":["Goblin 1","Flerb","Goblin 2"],"current":"Goblin 1","round":1}'

# Advance turn pointer:
python3 ~/.claude/skills/dnd/display/push_stats.py --turn-current "Flerb"

# New round:
python3 ~/.claude/skills/dnd/display/push_stats.py --turn-current "Goblin 1" --turn-round 2

# Combat ended:
python3 ~/.claude/skills/dnd/display/push_stats.py --turn-clear

# World time clock:
python3 ~/.claude/skills/dnd/display/push_stats.py --world-time \
  '{"date":"19 Ashveil 1312 AR","day_name":"Moonday","time":"morning","season":"Long Hollow","weather":"calm"}'

# Clear display (use push_stats.py, NOT curl — raw curl lacks the auth token in LAN mode):
python3 ~/.claude/skills/dnd/display/push_stats.py --clear

# Autorun cycle countdown (shown in party input panel):
python3 ~/.claude/skills/dnd/display/push_stats.py --autorun-waiting true --autorun-cycle 60
python3 ~/.claude/skills/dnd/display/push_stats.py --autorun-waiting false   # hide after turn resolves

# N-player threshold — auto-fire when N players (not all) are ready:
python3 ~/.claude/skills/dnd/display/push_stats.py --autorun-threshold 2   # fire when 2 ready
python3 ~/.claude/skills/dnd/display/push_stats.py --autorun-threshold 0   # reset to player count
```

**Player input queue — `display/check_input.py`:**
```bash
# Called at the start of each turn BEFORE processing the player's message.
# Drains any actions queued from the display companion (e.g. iPad) and prints them.
# Output: "[Aldric]: I draw my rapier" — empty if nothing queued. Clears the display indicator.
python3 ~/.claude/skills/dnd/display/check_input.py
```

If `check_input.py` returns output, prepend it to the player's terminal input when forming the turn:
- Only queued input: treat as the full player action this turn
- Queued input + terminal input: merge as `[Character]: <queued>\n[Character]: <terminal>`
- Empty queue: proceed as normal (use only terminal input)

---

**When to push stats:**
- `/dnd load` → `--replace-players --json` (full stats) + `--spell-slots` + `--world-time` + `--factions`
- HP change → `--player NAME --hp <current> <max>`
- Temp HP gained/lost → `--player NAME --temp-hp N` (0 to clear)
- XP awarded → `--player NAME --xp <current> <next>`
- Second Wind used/recovered → `--player NAME --second-wind false/true`
- Hit die spent → `--player NAME --hit-dice-use`; restored → `--hit-dice-restore N`
- Spell slot used → `--player NAME --slot-use <level>`; restored → `--slot-restore <level>`
- Condition gained → `--player NAME --conditions-add "Name"`; removed → `--conditions-remove "Name"`
- Concentration started → `--player NAME --concentrate "Spell"`; ended → `--concentrate ""`
- Item picked up → `--player NAME --inventory-add "Item"`; dropped/used → `--inventory-remove "Item"`
- Timed effect starts → `--effect-start "NAME:SPELL:DURATION[:conc]"` bundled with narration send
- Timed effect ends → `--effect-end "NAME:SPELL"` bundled with narration send
- Faction standing changes → `--factions '[...]'` (full replace)
- Combat start → `--turn-order`; each turn → `--turn-current`; end → `--turn-clear`
- Level up → push updated full stats
- Long rest → restore HP, hit dice, spell slots, second wind; push `--world-time` with updated time
- Any rest or time advance → push `--world-time`

---

## Tracker Script — `scripts/tracker.py`
Tracks conditions, concentration, timed effects, and death saves. State persists at `~/.claude/dnd/campaigns/<name>/tracker.json`.

```bash
CAMP=my-campaign

# Timed effects — duration: 10r (rounds), 60m (minutes), 8h (hours), indef
# Append 'conc' to mark as concentration (auto-sets concentration field)
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP effect start "Aldric" "Web" 10r conc
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP effect start "Mira" "Disguise Self" 1h
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP effect start "Mira" "Hunter's Mark" indef
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP effect end   "Aldric" "Web"   # narrative end (broken/dispelled)
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP effect tick  "Aldric"         # call on actor's turn — decrements rounds, prints expiry

# Conditions
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP condition add "Mira" poisoned
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP condition remove "Mira" poisoned
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP condition clear "Mira"

# Concentration (auto-clears previous if switching spells)
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP concentrate "Aldric" "Bless"
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP concentrate "Aldric" break

# Death saves
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP saves "Mira" success
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP saves "Mira" failure
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP saves "Mira" stable
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP saves "Mira" reset

# Status / clear
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP status
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP status "Mira"
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP clear           # conditions + concentration + effects
python3 ~/.claude/skills/dnd/scripts/tracker.py -c $CAMP clear --all     # also clears death saves
```

**When to run:** condition applied/removed; caster begins/loses concentration (immediately, not end of turn); PC drops to 0 HP; each death save rolled; end of encounter → `clear`.

---

## Calendar Script — `scripts/calendar.py`
```bash
# One-time setup (run during /dnd new):
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP init \
    --date "15 Harvestmoon 1247" \
    --time "morning" \
    --months "Frostfall,Deepwinter,Thawmonth,Seedtime,Bloomtide,Highsun,Harvestmoon,Duskfall" \
    --month-length 30 \
    --day-names "Sunday,Moonday,Ironday,Windday,Earthday,Fireday,Starday"

# Time advancement
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP advance 8 hours
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP advance 2 days
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP rest short   # +1 hour
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP rest long    # +8 hours

# Query / manual set
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP now
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP set "22 Harvestmoon 1247" evening
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP time night
python3 ~/.claude/skills/dnd/scripts/calendar.py -c $CAMP events
```

**When to run:** after every rest; after significant travel or time skip; when manually updating `state.md` date — use `calendar.py set` to keep them in sync.

---

## Campaign Search — `scripts/campaign_search.py`
Keyword search across campaign files. Use this **before** loading full files into context when looking up a specific past event, NPC detail, or plot thread.

```bash
CAMP=my-campaign

# Search all default files (state, log, archive, world, npcs):
python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c $CAMP Lasswater

# Narrow to specific files:
python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c $CAMP "Vael letter" --files log,archive

# Multi-keyword AND search:
python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c $CAMP VARETH Kel

# More context lines around each match:
python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c $CAMP Harwick -C 6
```

File keys: `state`, `log`, `archive`, `world`, `seeds`, `npcs`, `npcsfull`
Default files searched: state, log, archive, world, npcs

**When to use:** Any time a player asks about a past event, NPC detail, location, or plot thread that may not be in active context. Run this first — only escalate to a full `Read` if the search returns insufficient context.

---

## Data Commands — `scripts/sync_srd.py`, `scripts/build_srd.py`, and `scripts/lookup.py`

Dataset is bundled at `~/.claude/skills/dnd/data/dnd5e_srd.json`. No runtime download required.

```bash
# Check / rebuild dataset (only needed when upstream sources update):
python3 ~/.claude/skills/dnd/scripts/sync_srd.py             # rebuild if 5e-bits or FoundryVTT has new commits
python3 ~/.claude/skills/dnd/scripts/sync_srd.py --check     # check upstream SHAs, don't rebuild
python3 ~/.claude/skills/dnd/scripts/sync_srd.py --force     # always rebuild
python3 ~/.claude/skills/dnd/scripts/build_srd.py --status   # show current dataset metadata

# Lookup during play (CLI):
python3 ~/.claude/skills/dnd/scripts/lookup.py spell "fireball"
python3 ~/.claude/skills/dnd/scripts/lookup.py item "cloak of protection"
python3 ~/.claude/skills/dnd/scripts/lookup.py feature "sneak attack"
python3 ~/.claude/skills/dnd/scripts/lookup.py condition "poisoned"
python3 ~/.claude/skills/dnd/scripts/lookup.py monster "goblin"
python3 ~/.claude/skills/dnd/scripts/lookup.py monster "dragon" --all   # all fuzzy matches

# Programmatic (used by display companion /srd-lookup endpoint):
from lookup import lookup, lookup_record, lookup_with_level
lookup("fireball", category="spell")                  # → formatted string
lookup_with_level("sneak attack", category="feature", level=3)  # → level-resolved string
```

**When to use:** combat (monster stat blocks before using them); spellcasting (range, components, duration, at-higher-levels); conditions (rule text before applying); loot and equipment; NPC generation (monster stat block as mechanical base). The display companion's character sheet modal handles lookups automatically during play — these CLI calls are for DM reference outside the UI.

---

## Display Companion Setup (one-time)

```bash
cd ~/.claude/skills/dnd/display
pip3 install -r requirements.txt
```

```
Terminal (run claude directly — no wrapper needed)
    ↓ send.py calls per narration block / dice roll / stat change
Flask on https://localhost:5001 (app.py — HTTPS, self-signed cert)
    ↓ Server-Sent Events
Browser tab → Chromecast → TV
```

**Start the display:**
```bash
bash ~/.claude/skills/dnd/display/start-display.sh          # localhost
bash ~/.claude/skills/dnd/display/start-display.sh --lan    # LAN mode (phones, tablets)
open https://localhost:5001                                  # open browser before /dnd load
```

`start-display.sh` always force-kills any previous instance before starting — no manual pre-kill needed.

**Load a campaign:**
```
/dnd load <campaign-name>   # skill auto-detects running display, pushes party stats
```

The DM skill sends each narration block, dice result, and stat update via `send.py` calls (see Active DM Mode in SKILL.md for full send sequence and stat flag reference).

Open the browser tab and Chromecast it *before* running `/dnd load` so the browser is connected when the opening narration streams in. The display buffers the last 60 chunks and replays them to reconnecting browsers.

**Scene detection:** server scans narration for keywords and shifts background gradient + particle type (17 scenes: tavern, dungeon, forest, crypt, arcane, ocean, etc.). Crossfades over ~2.5 s.

**Audio (Python-side):** `audio.py` auto-imported by `app.py`. Two toggles: Ambient (looping soundscape) and Effects (one-shot SFX). Both default off. Scene changes crossfade the ambient loop. All synthesis via numpy — no audio files needed.
