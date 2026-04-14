# D&D Skill — Command Procedures

Full step-by-step procedures for all `/dnd` slash commands. Load this file at `/dnd load` or before executing any slash command.

---

## `/dnd new <campaign-name> [theme]`
1. Ask: *"Start the cinematic display companion? [y/n]"*
   - **Yes** → ask *"LAN mode? [y/n]"*
     - LAN → `bash ~/.claude/skills/dnd/display/start-display.sh --lan`, print both URLs, set `_display_running = true`
     - Local → `bash ~/.claude/skills/dnd/display/start-display.sh`, print URL, set `_display_running = true`
     - Then: `python3 ~/.claude/skills/dnd/display/push_stats.py --clear`
   - **No** → continue without display
2. `mkdir -p ~/.claude/dnd/campaigns/<name>/characters`
3. Copy and populate templates from `~/.claude/skills/dnd/templates/` — state.md, world.md, npcs.md, session-log.md
4. Ask: **party size** and **starting level**
5. **Tone/Genre Wizard** — present all four in one message:
   - Tone: `grimdark / dark fantasy / heroic / horror / political / swashbuckling / cosmic`
   - Magic level: `none / low / medium / high`
   - Setting type: `medieval / renaissance / ancient / nautical / underground`
   - Danger level: `lethal / gritty / standard / heroic`
   *(If `[theme]` supplied, pre-fill Tone and ask remaining three. Randomise any blank via dice.py and log `"d6=N → [result]"` in world.md.)*
6. **World Foundations** — geography/biome/climate, magic system, pantheon (2–3 active deities), calendar. Write to `## World Foundations` in world.md. Seed `state.md → ## World State → In-world date`.
7. **Three Truths** — one settlement, one nearby threat, one mystery (with clue trail). Write to respective sections in world.md.
8. **Threat Escalation Arc** — fill the five-stage table in world.md immediately after threat generation. Set current stage to 1. Write `Threat arc stage: 1 — Now` to `state.md → ## World State`.
9. **2 Factions** — archetype, all fields including current activity. Write to `## Factions` in world.md. Write one-line faction states to `state.md → ## World State`.
10. **3 NPCs with relationship web** — full entries (role, stats, demeanor, motivation, secret, speech quirk, faction, current goal, schedule, personality axes). Generate all three first, then fill Relationships (every NPC needs ≥2 links to others). Update index table.
11. **3–5 Quest Seeds** from threat, factions, mystery, NPC motivations. Write to `## Quest Seed Bank` in world.md.
12. Write state.md with session count 0, starting location.
13. Confirm creation, offer `/dnd character new`.

---

## `/dnd load <campaign-name>`
1. Ask: *"Start the cinematic display companion? [y/n]"*
   - Same display start/LAN flow as `/dnd new` step 1.
   - Clear previous transcript: `python3 ~/.claude/skills/dnd/display/push_stats.py --clear`
   - Register active campaign for DM Help: `echo "<campaign-name>" > ~/.claude/skills/dnd/display/.campaign`
   - Ask: *"Enable autorun mode for player input? [y/n]"*
     - **y** → write `autorun: true` to `state.md → ## Session Flags`; enter the autorun wait after the recap paragraph.
     - **n** → continue without autorun; DM drives turns manually.

2. Read SKILL-scripts.md (for script syntax this session)
3. Read state.md, world.md, npcs.md (index only — **do NOT read npcs-full.md or world-seeds.md at load**), and all characters/*.md
4. Push full party stats to display sidebar with `--replace-players` (clears stale characters from previous campaigns). For each character, include `--sheet <JSON>` built from the character file (attacks, spells, features, inventory). Also push `--world-time` with date/time/season/weather from state.md. Also push `--factions` from active faction states in `state.md → ## World State` (use `[]` if no factions are active).

   Sheet JSON structure — see `## push_stats.py → --sheet` in SKILL-scripts.md for full example. Keys: `attacks`, `spells` (omit for non-casters), `features`, `inventory`. Display shows "Full sheet not loaded" when all four are absent.

   Faction JSON structure (from `state.md → ## World State → Faction states`):
   ```json
   [{"name":"Pale Court","standing":"Allied"},{"name":"Watch","standing":"Neutral"}]
   ```
   Faction `standing` values: `Allied`, `Friendly`, `Neutral`, `Suspicious`, `Hostile`. Use `[]` to clear all factions. Push with:
   ```bash
   python3 ~/.claude/skills/dnd/display/push_stats.py --factions '[...]'
   ```
   The faction panel on the sidebar only appears when at least one faction is present — do not skip this push.
5. Deliver one in-character paragraph recapping current situation — where the party is, what's at stake, what was last happening.
6. Enter active DM mode — no `/dnd` prefix needed from this point.

---

## `/dnd save`
Write session events to session-log.md, update state.md (location, active quests, party HP/resources, recent events), update any characters/*.md that changed. Mirror each updated character to global roster (`~/.claude/dnd/characters/<name>.md`).

Then update `## Faction Moves` in state.md: for each active faction, answer *"what did they do while the party was occupied?"* One line per faction — even if nothing visible yet. Confirm what was written.

**Session log archival (run on every save after session count > 3):**
session-log.md keeps only the **2 most recent full session entries**. Older entries move to `session-log-archive.md` (append, never delete). Before archiving each entry, extract a 3–5 bullet continuity summary and write it to `## Continuity Archive` in state.md. Format:

```markdown
### Session N — [date] — [one-line location/event label]
- [Key fact that may resurface as a callback]
- [NPC revelation, exact wording of something important, decision that has consequences]
- [Roll outcome that changed the fiction]
- [Relationship shift, attitude change, item acquired with story significance]
```

The continuity summary is what stays hot in context. The full verbose log is in the archive, readable on `/dnd recap` or explicit request. When a past detail surfaces mid-scene, check `## Continuity Archive` first, then read session-log-archive.md if more depth is needed.

---

## `/dnd end`
1. Run `/dnd save`, then:
   a. Append **Session Recap** block to session-log.md with key events and open threads.
   b. Ask: *"Quick calibration — what worked this session, and what would you adjust next time?"* Write answers to `### DM Calibration`. If skipped, leave blank.
   c. Update `## World State` in state.md: check whether events advanced the threat arc stage, shifted faction states, or changed the in-world date. Update all three.
2. If `_display_running = true`, stop the display:
   ```bash
   kill $(cat ~/.claude/skills/dnd/display/app.pid 2>/dev/null) 2>/dev/null
   rm -f ~/.claude/skills/dnd/display/app.pid
   ```

---

## `/dnd abandon`

Exit the current session **without saving any state changes**. Use this when an error occurred and you want to discard everything since the last `/dnd save` (or since load, if the session was never saved).

1. Confirm: *"Abandon session? All unsaved state changes will be lost. Type 'yes' to confirm."* — do not proceed until confirmed.
2. Do **NOT** write to state.md, world.md, npcs.md, session-log.md, or any character files.
3. Clear the autorun flag in memory (`autorun: false`) so the wait loop does not restart.
4. If `_display_running = true`, stop the display:
   ```bash
   kill $(cat ~/.claude/skills/dnd/display/app.pid 2>/dev/null) 2>/dev/null
   rm -f ~/.claude/skills/dnd/display/app.pid
   ```
5. Confirm: *"Session abandoned. No files were written. Run `/dnd load <campaign>` to reload from the last saved state."*

---

## `/dnd data [pull|status]`
- `pull` → `python3 ~/.claude/skills/dnd/scripts/data_pull.py`
- `pull --force` → re-download all files
- `status` → `python3 ~/.claude/skills/dnd/scripts/data_pull.py --status`
- No argument → print status and quick-start instructions

Files stored in `~/.claude/skills/dnd/data/`. Safe to run at any time. Run once after initial skill setup, then when you want to update.

---

## `/dnd display [start|stop|status]`
- `start` → ask LAN mode [y/n]; run `bash ~/.claude/skills/dnd/display/start-display.sh [--lan]`; print URL(s)
- `stop` → `kill $(cat ~/.claude/skills/dnd/display/app.pid) 2>/dev/null && rm -f ~/.claude/skills/dnd/display/app.pid`
- `status` → `curl -s http://localhost:5001/ping` — reachable or unreachable
- No argument → print quick-start instructions

---

## `/dnd list`
Read `~/.claude/dnd/campaigns/*/state.md`, print summary table: campaign name | last session date | session count.

---

## `/dnd character new [campaign-name]`
1. Ask: name, race, class, background
2. Ask: *"In a sentence, what should the DM know about [Name]?"*
   - If answered: derive ONE pillar — **Bond**, **Flaw**, **Ideal**, or **Goal** (whichever fits best). Store both the raw sentence and derived pillar in `## Character Pillar`.
   - If skipped: leave `## Character Pillar` blank. Do not invent one. Do not re-prompt.
3. Ask: roll or point buy
   - Roll → `ability-scores.py roll`, present 3 arrays, player assigns
   - Point buy → `ability-scores.py pointbuy --check <scores>` to validate
4. Apply racial bonuses. Run `character.py calc` to derive all secondary stats.
5. Ask: Fighting Style (Fighter/Paladin/Ranger), spells (if caster)
6. Assign starting equipment per class + background
7. Write to `characters/<name>.md` using `templates/character-sheet.md`; set `## Campaign History → Origin campaign`
8. Add to `state.md` party line
9. Mirror to global roster: `cp characters/<name>.md ~/.claude/dnd/characters/<name>.md`

---

## `/dnd character sheet [name]`
Read `characters/<name>.md`, display cleanly. If name omitted and one character exists, show that one.

---

## `/dnd character import <name> [from:<campaign>]`
1. Find character sheet: `from:<campaign>` specified → that campaign's characters/; otherwise check global roster `~/.claude/dnd/characters/<name>.md`; if neither → search all campaigns, list matches, ask.
2. Show summary (level, XP, HP, key inventory) and ask: *"Import at current level [X], or level up before starting?"*
   - As-is → copy directly; Level up first → run `/dnd level up` on source sheet
3. Copy to current campaign's `characters/<name>.md`. Update: Campaign, Last Updated, Previous campaigns, Death Saves (reset).
4. Optionally ask about equipment adjustment for new setting.
5. Add to `state.md` party line. Update global roster.
6. Deliver one-paragraph in-character aside — how does it feel to step into a new world?

---

## `/dnd level up [name]`
1. **XP gate — check first:**

   | Level | XP required | Level | XP required |
   |-------|-------------|-------|-------------|
   | 2 | 300 | 11 | 85,000 |
   | 3 | 900 | 12 | 100,000 |
   | 4 | 2,700 | 13 | 120,000 |
   | 5 | 6,500 | 14 | 140,000 |
   | 6 | 14,000 | 15 | 165,000 |
   | 7 | 23,000 | 16 | 195,000 |
   | 8 | 34,000 | 17 | 225,000 |
   | 9 | 48,000 | 18 | 265,000 |
   | 10 | 64,000 | 19 | 305,000 |
   |    |         | 20 | 355,000 |

   Insufficient XP → report deficit and stop. Only continue on explicit DM override.
2. Read sheet. Run `character.py levelup`. Apply class features. Ask for HP roll or average. Update sheet + global roster. Narrate the growth.

---

## `/dnd npc [name]`
- Existing → read full entry from npcs-full.md (search by name), portray in character with voice/quirk
- New → generate full entry: role, CR-appropriate stats, demeanor, motivation, secret, speech quirk, faction (or "independent"), current goal, schedule, all four personality axes, ≥2 relationships to existing NPCs. Default attitude neutral. Append full entry to npcs-full.md; add one-line summary row to npcs.md index.

## `/dnd npc attitude <name> <shift>`
Find NPC in npcs.md, shift attitude one step (hostile → unfriendly → neutral → friendly → allied), log reason and date.

---

## `/dnd characters`
List all characters in global roster (`~/.claude/dnd/characters/`). Display: name, race/class/level, origin campaign, previous campaigns, last updated.

---

## `/dnd roll <notation>`
Run `scripts/dice.py <notation>`. Display output verbatim. Examples: `d20`, `2d6+3`, `d20 adv`, `4d6kh3`.

---

## `/dnd combat start`
1. Identify combatants; collect name, DEX mod, HP, AC, type (pc/npc) for each.
2. Run `combat.py init '<JSON>'` — auto-roll initiative for every combatant including PCs. Display tracker and per-combatant roll breakdown.
3. Send initiative to display:
   ```bash
   python3 ~/.claude/skills/dnd/display/send.py << 'DNDEND'
   ⚔️ Initiative — Round 1
   [Name]: d20(N) + DEX = total
   Turn order: [Name] → [Name] → ...
   DNDEND
   ```
4. Push turn order to stats sidebar:
   ```bash
   python3 ~/.claude/skills/dnd/display/push_stats.py --turn-order '{"order":[...],"current":"FirstName","round":1}'
   ```
5. Save STATE_JSON to `state.md` under `## Active Combat`.
6. Step through turns using the per-turn sequence (in SKILL.md Active DM Mode).
7. On combat end: update HP in character sheets, clear `## Active Combat`, `push_stats.py --turn-clear`, narrate aftermath, send XP summary, run `tracker.py -c <campaign> clear`.

**XP awards** go in the final display send:
```bash
python3 ~/.claude/skills/dnd/display/send.py << 'DNDEND'
[combat aftermath narration]

⭐ XP Awarded
- [Enemy] defeated: N XP
- [Objective] completed: N XP
- Total: N XP ÷ [players] = N XP each
- [Name]: N / 300 XP | [Name]: N / 300 XP
DNDEND
```

---

## `/dnd rest <short|long>`
**Short (1 hour):**
1. Ask how many Hit Dice the player spends. Roll `d[hit-die] + CON mod` per die via `dice.py`. Update HP, push `push_stats.py --player NAME --hp`.
2. Note class features that recharge (e.g. Second Wind → `push_stats.py --player NAME --second-wind true`).
3. Advance time: `calendar.py -c <campaign> rest short`
4. Clear encounter conditions: `tracker.py -c <campaign> clear` (concentration may persist — ask)

**Long (8 hours):**
1. Restore all HP, half max Hit Dice (round up), all spell slots, most class features. Update sheet.
2. Push: `push_stats.py --player NAME --hp <max> <max>` and `--second-wind true`.
3. Advance time: `calendar.py -c <campaign> rest long`
4. Clear all tracker state: `tracker.py -c <campaign> clear --all`
5. Update `state.md` in-world date to match calendar output.

---

## `/dnd recap`
Read session-log.md. Deliver 3–5 sentence in-character narrator recap of the most recent session entry.

## `/dnd world`
Read and display world.md.

## `/dnd quests`
Read `state.md` → display Active Quests and Open Threads sections.

---

## `/dnd tutor on` / `/dnd tutor off`
Toggle tutor/learning mode. Write `tutor_mode: true/false` to `state.md` under `## Session Flags`. Session-scoped — does not persist to next `/dnd load` unless explicitly set again. (Full tutor mode behavior is in SKILL.md.)

---

## `/dnd autorun on` / `/dnd autorun off`

Toggle autorun (taxi) mode — Claude drives the turn loop automatically when players submit via the display companion. No PTY wrapper required.

**On:**
1. Write `autorun: true` to `state.md → ## Session Flags`.
2. **Check Bash permissions** — read `~/.claude/settings.json`. If `permissions.allow` does not include `"Bash"` (or `"Bash(*)"` or similar), add it automatically:
   - Read the file, merge `"Bash"` into `permissions.allow`, write it back.
   - Tell the DM: *"Added Bash to permissions.allow in ~/.claude/settings.json — autorun won't prompt for each wait. Restart this session for it to take effect if it doesn't immediately."*
   - If it was already present, skip silently.
3. Confirm to the DM: *"Autorun enabled. Players submit via the display; I'll pick up each action automatically. Send me a message at any time to take control of a turn."*
4. If the user specified an interval (e.g. `/dnd autorun on 45`), write `autorun_interval: 45` to `state.md → ## Session Flags`. Default is 60 if omitted.
5. Immediately enter the autorun wait (see SKILL.md for the Bash block). If there's already something in `.input_queue`, pick it up as the current turn's player action.

The display shows a pie-clock countdown draining from full to empty over the interval. Green pulse = actively waiting. Configurable via `autorun_interval: N` in state.md (default 60 seconds).

**Off:**
1. Write `autorun: false` (or remove the line) to `state.md → ## Session Flags`.
2. Confirm: *"Autorun disabled. Back to manual mode — press Enter or tell me to submit when players are ready."*
3. Do NOT start the autorun wait after this response.

**Check on `/dnd load`:** If `autorun: true` is present in state.md, tell the DM autorun is active and begin the wait loop after the recap paragraph.

**When NOT to run the autorun wait (even if flag is set):**
- Mid-combat, resolving a specific combatant's turn
- Waiting on a player dice roll result
- The DM just sent a message (they're driving this turn)
- During `/dnd save`, `/dnd end`, or any command response
