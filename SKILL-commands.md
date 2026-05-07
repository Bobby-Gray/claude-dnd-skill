# D&D Skill — Command Procedures

Full step-by-step procedures for all `/dnd` slash commands. Load this file at `/dnd load` or before executing any slash command.

---

## `/dnd new <campaign-name> [theme]`
1. Ask a single compound question: *"Start display companion? LAN mode? Enable autorun player input? (e.g. y/y/n)"*
   - If display **yes**:
     - LAN **yes** → `bash ~/.claude/skills/dnd/display/start-display.sh --lan`, print both URLs, set `_display_running = true`
     - LAN **no** → `bash ~/.claude/skills/dnd/display/start-display.sh`, print URL, set `_display_running = true`
     - Then: `python3 ~/.claude/skills/dnd/display/push_stats.py --clear`
   - If display **no** → continue without display
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
12. **Dynamic Campaign Arc** — auto-generate the arc from all world data just created. Use Opus for this step. Ask: *"Generate a committed narrative arc? [y/n — recommended]"*

   **If yes:** Drawing from theme, threat arc stages, factions, Three Truths, NPC motivations, and quest seeds, derive:
   - **`theme`** — one sentence: what is this story ultimately about? Not the threat — its meaning.
   - **`resolution`** — the committed endpoint shape: if the party succeeds, what's the emotional truth? Keep specific events open; commit to the shape.
   - **Acts 1–3**, each with 2 beats. Each beat has:
     - `label` — a dramatic name
     - `what_changes` — before/after: what's fundamentally different once this lands? **CRITICAL: write this as a CONSEQUENCE, not an event.** A consequence is a state-of-the-world after the beat. An event is one specific thing that happens. Consequences survive when players pre-empt the obvious event delivery; events break and the beat goes stale. Example contrast for a 2b "All Is Lost" beat:
       - ❌ Event-shaped (fragile): *"Vedra's nomination succeeds and she takes the third seat."* If the party flips the clerk, this can't land — beat goes stale.
       - ✅ Consequence-shaped (robust): *"The party experiences a concrete cost from the Kept's escalation that they cannot reverse — a cover blown, an ally compromised, or a position they relied on no longer available."* This survives multiple delivery paths.
     - `world_pressure` — the specific faction or NPC move (naming actual entities from this world) that makes the beat feel inevitable. This MAY be event-shaped — but if the players pre-empt it, you're expected to revise per SKILL.md rule 8 (pre-emption is a revision trigger).
   - **`steering_notes`** — how to reach the first beat without forcing it

   Beat layout:
   - Act 1: **1a Inciting Incident** (the threat becomes personal for the party), **1b Complication** (the problem is bigger or stranger than it first appeared)
   - Act 2: **2a Midpoint Shift** (what the party *thought* they were doing changes), **2b All Is Lost** (a genuine setback — something fails, is lost, or collapses)
   - Act 3: **3a Final Confrontation** (the decisive moment the campaign turns on), **3b Resolution** (what's different about the world and the characters after)

   Write to `state.md → ## Campaign Arc` with `type: dynamic`. Deliver a one-paragraph arc summary to the DM.

   **If no:** Write `type: sandbox` to `## Campaign Arc`. The story remains open-ended with no arc tracking.

13. Write state.md with session count 0, starting location.
14. Confirm creation, offer `/dnd character new`.

---

## `/dnd load <campaign-name>`
1. Ask a single compound question: *"Start display companion? LAN mode? Enable autorun player input? (e.g. y/y/n)"*
   - Parse three answers from the response (y/n each, in order). Defaults: no display, no LAN, no autorun.
   - If display **yes**:
     - LAN **yes** → `bash ~/.claude/skills/dnd/display/start-display.sh --lan`, print both URLs, set `_display_running = true`
     - LAN **no** → `bash ~/.claude/skills/dnd/display/start-display.sh`, print URL, set `_display_running = true`
   - **Session tail replay:** before clearing the display, check if the campaign's `session_tail.json` exists. The campaign-side path is the authoritative one — `~/.claude/dnd/campaigns/<name>/session_tail.json`. **Do NOT read** the legacy/fallback at `~/.claude/skills/dnd/display/session_tail.json`; that file may exist from older sessions or other campaigns and will mislead the replay. If the campaign-side file does not exist, skip replay (display starts blank). If it does, read it. After `--clear` and full stats push (step 4 below), replay the tail by sending each entry via the appropriate `send.py` flag. Entry type → flag mapping:
     - `player` key present → `send.py --player <name>` with text via stdin
     - `npc` key present → `send.py --npc <name>` with text via stdin
     - `dice` key present → `send.py --dice` with text via stdin
     - `xp_award` key present → `send.py --xp-award '<json of the xp_award sub-dict>'`
     - `inspiration_award` key present → `send.py --inspiration-award '<name>'`
     - none of the above (plain DM narration) → `send.py` with text via stdin
     This restores the last scene to the display before the recap. The tail is written continuously by `dnd-display-app.py` — it always contains the last session's final exchanges regardless of how the session ended.
   - Clear previous transcript: `python3 ~/.claude/skills/dnd/display/push_stats.py --clear`

     ⚠ **`--clear` wipes both text log AND stats** (player card, world time, factions, quests). It must always be paired with the full `--replace-players ... --world-time ... --factions ... --quests ...` push from step 4 — otherwise the sidebar card and sheet tab render empty. Same rule applies any time you `--clear` mid-session (e.g. restoring scene state after a re-replay): always re-push the full character JSON + world-time + factions + quests in the same bash burst as the clear.
   - Register active campaign for DM Help: `python3 ~/.claude/skills/dnd/display/push_stats.py --set-campaign <campaign-name>`
   - If autorun **yes** → write `autorun: true` to `state.md → ## Session Flags`; enter the autorun wait after the recap paragraph.
   - If autorun **no** → continue without autorun; DM drives turns manually.

2. Read SKILL-scripts.md (for script syntax this session)
3. Read state.md, world.md, npcs.md (index only), and all characters/*.md
   - **state.md contains `## DM Style Notes`** — read and internalize before narrating anything. These are table-specific calibration patterns that override default DM instincts.
   - **world.md:** Load in full — World Foundations and active Adventure Nodes both inform narration and faction moves. Do NOT read `world-seeds.md` at load (generation artifact, not live reference).
   - **npcs.md:** Index row only at load. **Before writing substantive dialogue or decisions for any named NPC, read their full entry in `npcs-full.md`.** Do not wait for an explicit `/dnd npc [name]` call — do it proactively when a scene centers on that character. Index rows carry surface traits only; personality axes, relationships, and hidden goals are in the full entry.
   - **Do NOT read session-log.md at load** — recent events are already in `state.md → ## Recent Events`. Only read session-log.md if the player explicitly requests a recap, or if DM Calibration from the last 1-2 sessions is needed and not already internalized.
4. Push full party stats to display sidebar. **CRITICAL:** use `--json` with a complete player object — **never** the `--player` shorthand here. `--player` only updates existing fields; it cannot populate the card or sheet tabs. The display shows "Full sheet not loaded" when `sheet` is absent.

   ```bash
   python3 ~/.claude/skills/dnd/display/push_stats.py --replace-players --json '{
     "players": [
       {
         "name": "CharName",
         "race": "Race",
         "class": "Class (Background)",
         "level": N,
         "hp": {"current": N, "max": N, "temp": 0},
         "ac": N,
         "speed": 30,
         "hit_dice": {"max": N, "remaining": N, "die": "d8"},
         "xp": {"current": N, "next": N},
         "conditions": [],
         "concentration": null,
         "inspiration": 0,
         "spell_slots": {},
         "sheet": {
           "attacks": [{"name":"...","bonus":"+N","damage":"...","type":"...","notes":"..."}],
           "features": [{"name":"Feature 1","text":"Description of what it does."},{"name":"Feature 2","text":"Description."}],
           "inventory": ["Item 1", "Item 2"]
         }
       }
     ]
   }'
   ```

   For casters, add `"spells": {"cantrips":["..."],"level1":["..."]}` inside `sheet`. Omit for non-casters.

   **Inspiration:** read from `state.md → ## Current Situation → Party status`. Set `"inspiration": 1` (or `true`) if the character has it, `0` if not. Inspiration is NOT reset by a long rest — it persists until spent. Must be explicitly tracked in the party status line at `/dnd save` (e.g., `Kat: Inspiration ✓`) and loaded at `/dnd load`. Use `push_stats.py --player <name> --inspiration true/false` for mid-session updates.

   `--replace-players` clears stale characters from previous campaigns. Build the JSON from the character file — every field above is required for the card and sheet tabs to render correctly.

   Also push `--world-time`, `--factions`, and `--quests` in the **same** `push_stats.py` call as the player JSON to avoid race conditions where the display server receives a partial update. Combine all into one invocation:

   ```bash
   python3 ~/.claude/skills/dnd/display/push_stats.py --replace-players \
     --json '{...players...}' \
     --world-time '{...}' \
     --factions '[...]' \
     --quests '[...]'
   ```

   Faction JSON structure — **`standing` is required**:
   ```json
   [{"name":"Pale Court","standing":"Allied"},{"name":"The Kept","standing":"Hostile"}]
   ```
   `standing` values: `Allied`, `Friendly`, `Neutral`, `Suspicious`, `Hostile`. If the field is omitted, `dnd-display-app.py` defaults it to `"Neutral"` and logs a warning to stderr — but always include it explicitly. Map prose from `state.md` to exact values (e.g. "deep ally" → `"Allied"`, "active hostile" → `"Hostile"`). Use `[]` to clear.

   The faction panel only appears when at least one faction is present — do not skip this push.

   Quest JSON structure:
   ```json
   [{"name":"The Missing Shipment","status":"resolved"},{"name":"Keth the Collector","status":"threat"}]
   ```
   Quest `status` values: `active` (amber), `threat` (red), `resolved` (green), `failed` (muted). Use `[]` to clear all quests:
   ```bash
   python3 ~/.claude/skills/dnd/display/push_stats.py --quests '[...]'
   ```
   The quest panel only appears when at least one quest is present — do not skip this push.
5. **Pull scene-context from the campaign graph.** Always run, even if you suspect `graph.json` doesn't exist — the script exits cleanly with a notice when uninitialized.
   ```bash
   python3 ~/.claude/skills/dnd/scripts/campaign_graph.py scene-context \
     --campaign <campaign-name> \
     --place "<current-location-name-or-id>" \
     --present "<comma-separated-NPC-names-likely-present>" \
     --hops 2 \
     --at-session <current-session-N>
   ```
   Identify `<current-location>` from `state.md → ## World State → location` (or the most recent location in `## Recent Events`). Identify `<present>` from the NPCs likely on-scene per `state.md` / `session-log.md`. `<current-session-N>` is `state.md → ## Session Count`.

   Output is a focused subgraph (nodes by type + relationships block). **Internalize this subgraph before delivering the recap** — it is the authoritative source for who-relates-to-whom in the current scene. Do not re-read `npcs-full.md` for relationships you can answer from the subgraph.

   If output reads `# graph not initialized` — graph hasn't been seeded for this campaign yet. **Graph init is a hard requirement, not deferrable.** The continuity-archive compression rule (step 6 below + `/dnd save`) assumes graph.json is present and canonical for relational state; deferring init creates state-archive drift that compounds session-over-session. Run the init flow before delivering the recap:

   1. **Detect legacy.** A campaign is "legacy" if any of: `Session count > 1` in state.md header, OR `## Continuity Archive` has at least one `### Session N` entry, OR session-log.md is > 100 lines. A freshly-created campaign at `/dnd new` time fails all three signals — do NOT classify it as legacy.

   2. **Backup the campaign directory** (always — both fresh and legacy):
      ```bash
      cp -R ~/.claude/dnd/campaigns/<name> \
            ~/.claude/dnd/campaigns/<name>.backup-$(date +%Y%m%d-%H%M%S)
      ```
      Tell the DM the backup path explicitly so they can revert if needed.

   3. **Run `/dnd graph init <name>`** — propose seed nodes/edges from `npcs.md`, `world.md`, and `state.md` (Live State Flags + Active Quests + recent NPC dispositions). Show the DM a single approval block (counts by type + named entries) and ask for one go/no-go. After approval, batch-execute the `add-node` and `add-edge` calls. Use `--since N` matching when each node/edge first became canon (use `1` for foundational; the actual session number for newer NPCs/edges).

   4. **Validate** with a `scene-context` query at the current location to confirm the subgraph is reachable.

   5. **(Legacy only)** Offer the one-time Continuity Archive compression pass:

      > "This campaign is legacy ({session_count} sessions, {archive_count} archive entries). Now that `graph.json` is the canonical source for faction memberships, NPC dispositions, and typed-edge relationships, I can do a one-time pass to trim the existing `## Continuity Archive` entries of relational restatements that the graph now answers. Mechanical changes, plot beats, atmospheric/decision moments, and disclosed information stay in full. Estimated reduction: 5–30% of archive bytes (varies by how relational vs. content-heavy your existing entries are). Backup is already at `<backup-path>`. Proceed? [y/n]"

      - `y` → trim each archive entry surgically; keep the bullet structure; remove ONLY pure-relational restatements (e.g. "X is allied with Y", "Z saw the party's faces", "W is a member of faction F") that have a corresponding edge in the just-initialized graph. Preserve: XP/level/items/HP, plot beats ("Beat 2a sealed"), atmospheric moments, disclosed content, calibration material, off-screen world events. Add a one-line note at the top of `## Continuity Archive`: *"Compressed YYYY-MM-DD (graph init pass). Relational state is canonical in graph.json — entries below preserve mechanical changes, plot beats, disclosed content, atmospheric/decision moments, and calibration material."*
      - `n` → leave the archive untouched. The going-forward compression rule (per `/dnd save`) still applies to NEW entries from this session forward.

      For fresh (non-legacy) campaigns: skip the offer entirely — there's nothing to compress yet, and the going-forward rule covers all future entries.

   6. Re-run scene-context (now populated). Then proceed to step 6 (recap).

6. Deliver one in-character paragraph recapping current situation — where the party is, what's at stake, what was last happening.
7. Enter active DM mode — no `/dnd` prefix needed from this point.

---

## `/dnd import <filepath> [campaign-name]`

Import a pre-written campaign from a source file (PDF, MD, TXT, DOCX) and create a playable campaign from it.

**Supported file types:** `.pdf` `.md` `.txt` `.markdown` `.docx`

### Step 1 — Extract source text
```bash
python3 ~/.claude/skills/dnd/scripts/import_campaign.py "<filepath>" --info
```
Print file info. If word count is over 4000, chunk the source:
```bash
python3 ~/.claude/skills/dnd/scripts/import_campaign.py "<filepath>" --chunks  # total chunks
python3 ~/.claude/skills/dnd/scripts/import_campaign.py "<filepath>" --chunk 0  # first chunk
```
For short sources (under 4000 words), read in full:
```bash
python3 ~/.claude/skills/dnd/scripts/import_campaign.py "<filepath>"
```

### Step 2 — Analyse structure
Read the extracted text and identify:
- **Campaign title and system**
- **Structure type:** `linear` (scene chain A→B→C) | `hub-and-spoke` (central hub + spoke locations, player-driven order) | `faction-web` (multi-faction city/complex, overlapping arcs)
- **Acts and chapters** — numbered sections, chapter headings, or named scenes
- **Key beats** — required story events the DM must deliver (boss reveals, faction turns, mandatory encounters)
- **Locations** — distinct named places with descriptions
- **NPCs** — names, roles, motivations, relationships, stat blocks if present
- **Factions** — groups with agendas, relationships to party
- **Quest hooks and seeds** — explicit adventure hooks, side quests, optional encounters
- **Starting conditions** — where does the party begin, what level, what's the inciting event

For large sources, read all chunks before proceeding.

### Step 3 — Confirm campaign name
If `[campaign-name]` not supplied, suggest one from the title and ask to confirm.

### Step 4 — Display summary and confirm
Show a structured summary before writing any files:

```
Title:    <source title>
Type:     structured / <structure type>
Acts:     N  |  Chapters: N  |  Key beats: N
NPCs:     N named  |  Factions: N
Locations: N distinct

Campaign name: <name>
Campaign dir:  ~/.claude/dnd/campaigns/<name>/

Proceed? [y/n]
```

### Step 5 — Create campaign files
On confirmation:

1. `mkdir -p ~/.claude/dnd/campaigns/<name>/characters`
2. Copy templates from `~/.claude/skills/dnd/templates/`
3. Write **world.md**:
   - `## World Foundations` — setting, geography, tone, magic level, calendar if present
   - `## Three Truths` — one settlement, one threat, one mystery (drawn from source)
   - `## Threat Escalation Arc` — map source acts to the 5-stage table; set stage 1
   - `## Factions` — all factions with archetype, current activity, relationship to party
   - `## Quest Seed Bank` — all explicit hooks + 2–3 implied side threads
   - `## Adventure Nodes` — named locations with one-line descriptions

4. Write **npcs.md** index table (one row per NPC: name, role, location, one-line demeanor)

5. Write **npcs-full.md** — full entry for each named NPC:
   - Role, motivation, secret, speech quirk, faction affiliation
   - Relationships to other NPCs (min 2 per NPC)
   - Stat block summary if present in source

6. Write **state.md** from template:
   - Populate `## Current Situation` — starting location and party placeholder
   - Populate `## World State` — in-world date if given, factions, threat arc stage 1
   - Populate `## Campaign Arc` — full act/chapter structure with key beats, telegraph scenes, and steering notes (see format in template)
   - Leave `## Active Quests`, `## Session Flags`, `## DM Style Notes` as template defaults

7. Write **session-log.md** with Session 0 import record:
   ```
   ## Session 0 — Import — <date>
   Source: <filepath>
   Imported: <N> acts, <N> chapters, <N> NPCs, <N> locations
   ```

### Step 6 — Gap-fill wizard
After writing files, identify anything the source left ambiguous:
- If starting level not specified → ask
- If party size not specified → ask
- If calendar/in-world date absent → offer to generate or leave blank
- If tone not clear from source → offer Tone/Genre Wizard

### Step 7 — Confirm and offer next step
Print summary of files written. Offer:
```
Campaign "<name>" created from <source title>.
→ /dnd character new      — create your character
→ /dnd load <name>        — start playing immediately
```

---

## `/dnd save`
Write session events to session-log.md, update state.md (location, active quests, party HP/resources, recent events), update any characters/*.md that changed. Mirror each updated character to global roster (`~/.claude/dnd/characters/<name>.md`).

**Inspiration tracking:** On every save, record each PC's Inspiration state in `state.md → ## Current Situation → Party status`. Use explicit text: `Inspiration ✓` if held, omit or `No Inspiration` if not. Inspiration persists across sessions and is NOT cleared by long rests. Example: `Kat: HP 24/24. Inspiration ✓. Ben: HP 24/24.`

**Update `## Live State Flags` in state.md on every save.** This section is the compaction-resistant anchor — it holds facts that prose summaries flatten. After each session, review and update:
- **Cover:** each PC's active cover, its status (INTACT / BLOWN / PARTIAL), and the one-line reason. Remove covers that are no longer active.
- **Faction stances:** each faction with non-neutral standing toward the party. Format: `[Faction]: [Allied/Friendly/Neutral/Suspicious/Hostile] — [one-line reason]`. Remove factions that have returned to neutral.
- **NPC dispositions:** each NPC with changed or notable standing. Format: `[Name]: [disposition] — [one-line reason]`. Remove NPCs who have returned to baseline.

If nothing changed in a category this session, leave it as-is. If a fact was wrong in the previous save, correct it.

Then update `## Faction Moves` in state.md: for each active faction, answer *"what did they do while the party was occupied?"* One line per faction — even if nothing visible yet. Confirm what was written.

**Session tail archive:** `dnd-display-app.py` continuously writes `~/.claude/dnd/campaigns/<name>/session_tail.json` — campaign-specific path, atomic-write, skip-on-empty guarded (since 2026-05-01). At save time:

1. Verify the campaign-side file exists and is non-empty:
   ```bash
   bash ~/.claude/skills/dnd/display/verify_tail.sh <campaign-name>
   ```
   The script returns 0 if the tail is healthy (non-empty + valid JSON list), 1 if missing/empty/corrupt. If it returns 1, the tail is unsafe to rely on for next session's replay — **write a canonical replacement directly to the campaign path** with this session's 5–8 most important narrative beats as a JSON list of `{"text": "...", "_camp": "<name>"}` entries (no display call needed; the display may already be dead). Use the `tools/write_canonical_tail.py` helper.
2. Also write `~/.claude/dnd/campaigns/<name>/session-tail.md` (human-readable snapshot — companion to the JSON, used as fallback during /dnd load if JSON read fails).

**Session log archival (run on every save after session count > 3):**
session-log.md keeps only the **2 most recent full session entries**. Older entries move to `session-log-archive.md` (append, never delete). Before archiving each entry, extract a 3–5 bullet continuity summary and write it to `## Continuity Archive` in state.md. Format:

```markdown
### Session N — [date] — [one-line location/event label]
- [Key fact that may resurface as a callback]
- [NPC revelation, exact wording of something important, decision that has consequences]
- [Roll outcome that changed the fiction]
- [Item acquired with story significance, plot beat, atmospheric/decision moment]
```

**Going-forward Continuity Archive compression rule (from 2026-05-07; applies when `graph.json` exists for the campaign):** When `graph.json` is present, the Continuity Archive bullets must NOT restate relational state that the graph holds canonically. Specifically, **omit** bullets/clauses that say:
- "X is allied with Y" / "X is hostile to Y" / "X is friendly with Y" — already a typed edge with `--since N` and source-anchor
- "X is a member of faction F" / "X works for Y" / "X reports to Y" — already a `member_of` / `works_for` / `reports_on` edge
- "Z saw the party's faces" / "K is now in the Kept profile" — already a `hostile_to` / `surveils` edge with `--since`
- Faction memberships and NPC dispositions that haven't changed this session
- Restated NPC profiles (job title, age, location) that already live as node tags + summary

**Keep** in archive bullets:
- Mechanical changes (XP awarded, level-ups, items gained/spent, slots burned, HP deltas at session end)
- Plot beats (arc beat completions, "Beat 2a sealed", "Beat 2b LANDED")
- Atmospheric / decision moments that have no graph edge ("Mira ate the bread — first food in 800 years", "Kat squeezed her hand")
- Disclosed content (the WHAT was learned — "fragment / anchor / host", "three acceleration factors") even when the relational fact is in graph
- Off-screen world events / faction moves
- Calibration / DM Notes
- Cliffhangers and pause-points

Treat each bullet as one sentence with one job. If the only job is "restate a graph edge", drop it. If it carries content + edge, keep the content half. The graph is queried at `/dnd load` step 5; the archive is queried for chronological narrative + mechanical state — they should not overlap.

The continuity summary is what stays hot in context. The full verbose log is in the archive, readable on `/dnd recap` or explicit request. When a past detail surfaces mid-scene, check `## Continuity Archive` first, then `/dnd graph scene-context` for relational context, then read session-log-archive.md if more depth is needed.

**Campaign-graph relationship-shift sweep:** before completing the save, scan this session's narration for relationship shifts that weren't captured live via `/dnd graph add-edge` / `close-edge`. Look for moments matching these patterns:

- New alliance, betrayal, or rivalry between named NPCs / factions ("Velkyn now serves the Pale Court")
- An NPC moving into / out of a location ("Mira fled the Citadel for the Lowmarket")
- A faction taking control of (or losing) a place ("House Tarn lost the silver mine")
- A character learning a secret ("the party now knows Velkyn was the spy")
- A quest / thread ending or being blocked

For each candidate, draft an `add-edge` or `close-edge` call. Then **present the batch to the DM as a numbered list** and ask: *"Apply all? [y / pick / skip]"*

- `y` → run all proposed calls via `python3 ~/.claude/skills/dnd/scripts/campaign_graph.py ...`
- `pick` → DM names the numbers to apply (e.g. `1, 3, 5`); skip the rest
- `skip` → don't apply any

Always supply `--since <current-session-N>` from state.md. Never write proposed edges silently.

If `graph.json` doesn't exist yet for this campaign, skip the sweep entirely (no proposal block) — graph isn't seeded.

---

## `/dnd end`
1. Run `/dnd save`, then:
   a. Append **Session Recap** block to session-log.md with key events and open threads.
   b. Ask: *"Quick calibration — what worked this session, and what would you adjust next time?"* Write answers to `### DM Calibration`. If skipped, leave blank.
   c. Update `## World State` in state.md: check whether events advanced the threat arc stage, shifted faction states, or changed the in-world date. Update all three.
   d. If the calibration response reveals a new pattern (or confirms/contradicts an existing one), update `## DM Style Notes` in state.md. Add new bullets; refine existing ones if the pattern has sharpened. Do not log every session — only update when something genuinely new or changed is observed.
   e. **Arc check** (dynamic arcs only — skip for sandbox/structured): If `## Campaign Arc` has `type: dynamic`, do all of:

      i. Ask: *"Did any arc beats land this session? [beat id(s) like '1b 2a', or 'none']"*
      ii. If beats landed: run `/dnd arc advance <beat-id>` for each.
      iii. **Pre-emption check (critical — added 2026-05-01):** for each remaining outstanding beat whose `world_pressure` was visibly delivered this session (the world event named in the beat actually appeared in narration or Faction Moves), evaluate whether the beat's `what_changes` consequence ALSO landed. Three possible states:
        - **Landed cleanly** → mark beat complete (step ii).
        - **Did not land — pressure absorbed without consequence** → the beat is overdue and its current shape no longer fits. **Run `/dnd arc revise` immediately**; do not just update `steering_notes`. The beat's `what_changes` was event-shaped (something specific happens) when it should be consequence-shaped (something fundamentally different is true) — revise both `what_changes` and `world_pressure` to fit a path that DOES land. The committed shape bends; it does not break.
        - **Pressure not yet delivered** → leave beat alone; expected to deliver next session.
      iv. Update `steering_notes` for the next outstanding beat with the *consequence shape* expected, not the specific event.
   f. **Tail verification (added 2026-05-01):** before killing the display, verify the campaign-side `session_tail.json` is healthy:
      ```bash
      bash ~/.claude/skills/dnd/display/verify_tail.sh <campaign-name>
      ```
      Exit 0 = healthy. Exit 1 = missing/empty/corrupt → write a canonical replacement to `~/.claude/dnd/campaigns/<name>/session_tail.json` from session context (5–8 entries, each `{"text": "...", "_camp": "<name>"}`) BEFORE the display kill — once the display is dead, only the file matters. The display's own `_persist_tail` has skip-on-empty + atomic-write guards, but the backstop ensures a worst-case file state is impossible.
2. Stop the display (always — even if `_display_running` was unclear):
   ```bash
   kill $(cat ~/.claude/skills/dnd/display/app.pid 2>/dev/null) 2>/dev/null
   rm -f ~/.claude/skills/dnd/display/app.pid
   ```
3. **Post-kill tail re-verification:** run `verify_tail.sh` once more after the kill. If it now reports unhealthy (file got truncated by a final write race), restore from the canonical version written in step 1f.

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

## `/dnd data [sync|status]`
- `sync` → `python3 ~/.claude/skills/dnd/scripts/sync_srd.py` — checks upstream SHAs (5e-bits + FoundryVTT) and rebuilds `dnd5e_srd.json` only if either source has new commits
- `sync --force` → `python3 ~/.claude/skills/dnd/scripts/sync_srd.py --force` — rebuild regardless
- `sync --check` → check upstream without rebuilding
- `status` → `python3 ~/.claude/skills/dnd/scripts/build_srd.py --status` — show current dataset metadata

Dataset is bundled at `~/.claude/skills/dnd/data/dnd5e_srd.json` (1453 records: spells, equipment, magic items, conditions, monsters, class features). No download required at runtime. Run `sync` only when you want to pull new upstream content.

---

## `/dnd path [<new-path> | reset]`

View or configure where campaign and character data is stored. Wraps the
`DND_CAMPAIGN_ROOT` env var.

- No args → `python3 ~/.claude/skills/dnd/scripts/path_config.py` and show output.
- New path → `python3 ~/.claude/skills/dnd/scripts/path_config.py set <path>`. Confirm to user, then remind them the change only takes effect in new shells (or after they `source` their rc on macOS/Linux).
- `reset` → `python3 ~/.claude/skills/dnd/scripts/path_config.py reset`.

Persistence is via shell rc on macOS/Linux and via `setx` on Windows. Existing campaigns are not auto-migrated; `paths.find_campaign()` handles legacy fallback + copy-on-access.

---

## `/dnd update [--check]`

Pull the latest skill changes from `origin/main`.

- No args → `python3 ~/.claude/skills/dnd/scripts/update_skill.py` and stream output (script prompts before pulling).
- `--check` → `python3 ~/.claude/skills/dnd/scripts/update_skill.py --check` — report status without pulling.
- The script refuses to update if the working tree is dirty and uses `--ff-only` so it never silently merges divergent history.
- After a successful pull, remind the user to restart Claude Code so the new `SKILL.md` and `SKILL-commands.md` are reloaded.

---

## `/dnd display [start|stop|status]`
- `start` → ask LAN mode [y/n]; run `bash ~/.claude/skills/dnd/display/start-display.sh [--lan]`; print URL(s)
- `stop` → `kill $(cat ~/.claude/skills/dnd/display/app.pid) 2>/dev/null && rm -f ~/.claude/skills/dnd/display/app.pid`
- `status` → `curl -sk $(cat ~/.claude/skills/dnd/display/.scheme 2>/dev/null || echo http)://localhost:5001/ping` — reachable or unreachable
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
10. Run supplemental builder to fetch any non-SRD spells/features the character uses:
    ```bash
    python3 ~/.claude/skills/dnd/scripts/build_supplemental.py --character ~/.claude/dnd/campaigns/<name>/characters/<charname>.md
    ```
    This scans the character file for spells and features not in the SRD and fetches descriptions from dnd5e.wikidot.com into `dnd5e_supplemental.json`. Skips any entries already present. Safe to re-run.

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
6. Run supplemental builder for any non-SRD entries:
    ```bash
    python3 ~/.claude/skills/dnd/scripts/build_supplemental.py --character ~/.claude/dnd/campaigns/<name>/characters/<charname>.md
    ```
7. Deliver one-paragraph in-character aside — how does it feel to step into a new world?

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

## `/dnd arc [status|advance|revise|view]`

Manage the dynamic campaign arc. Active only when `state.md → ## Campaign Arc` has `type: dynamic` — no-op for sandbox and structured campaigns.

- **`/dnd arc`** or **`/dnd arc status`** — print current act, current beat label, `what_changes` for the current beat, and `steering_notes`. Quick reference, one screen.
- **`/dnd arc advance [beat-id]`** — mark the named beat complete (current beat if omitted). Remove from `outstanding_beats`. Advance `current_beat` to the next pending beat. If all beats in an act are complete, advance `current_act`. Update `steering_notes` to describe how to reach the newly current beat without forcing it.

  **When the final beat (3b) is marked complete — arc continuation:**
  `outstanding_beats` is now empty. Ask: *"The arc is complete. Continue the campaign with a new arc? [y/n]"*
  - **Yes** → run `/dnd arc new` (see below).
  - **No** → set `type: sandbox` and clear `outstanding_beats`. The campaign continues open-ended from the resolution state.

- **`/dnd arc new`** — generate a new arc for a campaign that has completed its previous arc. Use Opus for this step.

  The new arc must be **intentionally distinct** — not a continuation of the same conflict, but a new chapter that grows from the changed world. The resolution of arc N is the status quo of arc N+1.

  Procedure:
  1. Read the completed arc's `resolution` field — this is now the world's baseline.
  2. Read `## DM Notes`, `## World State`, `## Faction Moves`, and any `## Continuity Archive` entries to understand what the world looks like post-resolution.
  3. Derive the new arc from **the consequences** of what just resolved. Ask: *what problem did solving the last arc create? What power vacuum formed? What did the party's victory cost that now has to be reckoned with? What was ignored because the last arc demanded all attention?*
  4. Generate a new full arc (theme, resolution, acts 1–3, 6 beats) using the same format as the initial arc. The new theme must be meaningfully different from the previous one — same world, new lens.
  5. Archive the completed arc: move the current `acts` block, `theme`, and `resolution` into a new `## Arc History` section in state.md under `arc_N` (numbered), with a one-line summary of how it resolved.
  6. Write the new arc to `## Campaign Arc`, incrementing `arc_number`. Set `current_act: 1`, `current_beat: "1a"`, `outstanding_beats` to all 6 beat ids.
  7. Append to `revision_log`: `"<date>: Arc N complete. New arc N+1 generated. [one-line premise of the new arc]"`
  8. Deliver a one-paragraph summary of the new arc's premise and how it differs from the previous one.

- **`/dnd arc view`** — show full arc: theme, resolution, all acts and beats with completion status (current / complete / pending). If `## Arc History` exists, show a one-line summary of each completed arc above the current one.
- **`/dnd arc revise`** — open revision flow for when the story has taken a major unexpected turn OR when the auto-trigger from /dnd end's pre-emption check fires (most common case):
  1. Show all outstanding beats with their current `what_changes` and `world_pressure`.
  2. Ask: *"What's changed in the story that the arc doesn't reflect?"* — or, when auto-triggered by pre-emption, name the pre-empted beat directly: *"Beat 2b's pressure delivered but the consequence didn't land. Picking a revision path…"*
  3. **Apply one of three landing-path templates** (per SKILL.md rule 8) to the affected outstanding beat:
     - **Cost path** — `what_changes` becomes "the party paid a concrete cost for moving fast"; `world_pressure` becomes the specific cost (cover blown, ally compromised, position lost). Best when the party pre-empted cleanly.
     - **Secondary consequence path** — `what_changes` becomes "the world responded to being pre-empted in a way the party didn't anticipate"; `world_pressure` becomes the new escalation (the antagonist reads the disruption as a signal and does something WORSE). Best when the antagonist is intelligent and adaptive.
     - **Deferred path** — keep the original `what_changes` shape; rewrite `world_pressure` to a NEW pressure pointing at the same consequence, scheduled for the next 1–2 sessions. Best when the original consequence is still narratively essential and only the timing slipped.
  4. Rewrite `what_changes` (consequence-shaped per the rule in /dnd new step 12) and `world_pressure` (event-shaped is fine) for the affected beat. Do NOT modify completed beats.
  5. Append to `revision_log`: `"<date>: <beat-id> — <path: cost/secondary/deferred> — <what changed and why — one sentence>"`
  6. Update `steering_notes` to describe the next session's expected delivery.
  7. Confirm what was revised. Show before/after for `what_changes` and `world_pressure`.

---

## `/dnd graph <subcommand>` — campaign relationship graph

Local-only typed-edge relationship graph supplementing markdown. Stored at `~/.claude/dnd/campaigns/<name>/graph.json`. Supplements `npcs-full.md` / `session-log.md` — does not replace them. Edges are time-stamped (`since_session` / `until_session`), so historical state is recoverable.

**Auto-pulled at `/dnd load` step 5** (scene-context) and **swept at `/dnd save`** (relationship-shift extraction). The DM also uses `/dnd graph scene-context` on demand mid-session, especially before heavy social or political scenes.

For background reading on the design and the A/B replay study that motivated it, see `docs/research/graph/`.

All subcommands invoke `python3 ~/.claude/skills/dnd/scripts/campaign_graph.py <subcommand> --campaign <name> [args]`.

### `/dnd graph init [campaign-name]`
First-time bootstrap. Read existing `npcs.md` / `world.md` / `state.md` for the campaign. Propose a node list (NPCs as `npc_*`, factions as `faction_*`, key locations as `place_*`) and a starter edge list (faction membership from npcs.md tables, NPC location from "Lives in / Based at" fields, faction relationships from world.md). Display the proposed list to the DM and **ask for approval** before writing — do not silently extract. After approval, run `add-node` and `add-edge` for each. Use `--since` matching state.md's current session count.

For existing campaigns being initialized for the first time, the `/dnd load` flow offers to back the campaign directory up first; honour that flow rather than running init from a cold prompt.

### `/dnd graph add-node --type T --name N [--tags ...] [--summary ...]`
Add a single node. Type is open vocab; suggested: `npc`, `faction`, `place`, `item`, `thread`. Default id is `<type>_<name-slug>`.

### `/dnd graph add-edge --from <id> --to <id> --type T [--since N] [--note ...]`
Add a typed edge between two existing nodes. Edge type is open vocab; common: `loyal_to`, `opposes`, `allied_with`, `member_of`, `lives_in`, `controls`, `knows_about`, `friends_with`, `lover_of`, `owes`, `rules`, `related_by_blood`, `advances_thread`, `blocks_thread`. Always supply `--since` (the current session number from state.md) so historical replay works.

### `/dnd graph close-edge --id <edge-id> --at-session N`
Mark an edge as ended at session N (e.g. when an alliance breaks). Original edge is preserved with `until_session` set; it remains visible in historical queries but is excluded from "active at session ≥ N" results.

### `/dnd graph list [--type T] [--at-session N]`
Print a compact node table grouped by type. With `--at-session`, also reports active edge count at that session.

### `/dnd graph show --id <node-id>`
Print one node with all incoming and outgoing edges.

### `/dnd graph scene-context --place <id> [--present id1,id2] [--threads id1,id2] [--hops H] [--at-session N]`
**Primary query for in-session use.** Returns a focused subgraph from the current scene (place + present NPCs + active threads) bounded by hop count, optionally filtered to edges active at a given session. Output is grouped: nodes by type, then a relationships block. Default `--hops 2`. Use this when you need to recall who-relates-to-whom in the current scene without re-reading `npcs-full.md` or session-log archives.

### `/dnd graph subgraph --seed <id> [--seed <id>] [--hops H] [--at-session N]`
Lower-level traversal — same as `scene-context` but with arbitrary seed nodes. Use when the scene framing doesn't fit (e.g. tracing faction politics independent of any specific place).

### `/dnd graph extract [campaign-name] [--last-session-only]`
Run a Haiku pass over the campaign's session-log to propose new edges with verbatim source-anchors. Outputs a proposal JSON to `~/.claude/dnd/campaigns/<name>/graph-proposals-<date>.json` for human review. Does **not** write to graph.json — that's the apply step.

### `/dnd graph extract-apply --proposals <file> [--pick N1,N2,...]`
Apply previously-extracted proposals. Without `--pick`, prompts interactively. With `--pick`, applies only the listed proposal indices.

### Suggested DM workflow

1. **First session after install:** `/dnd load` will offer to initialize the graph (with a backup-first prompt). Accept; review the proposed seed; approve.
2. **During session:** when a relationship shifts in narration, run `/dnd graph add-edge` (or `close-edge`) with `--since` set to the current session number. Don't batch this — record at the moment of the narrative change so you don't forget.
3. **Before a heavy social/political scene:** run `/dnd graph scene-context --place <current-place> --present <key-NPCs>` to refresh which relationships matter right now.
4. **At `/dnd save`:** review the session log and add any edges you missed during play (the save flow runs an automatic sweep and presents proposals for approval).

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
