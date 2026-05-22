# Changelog

All notable changes to the D&D 5e DM skill are documented here. The skill follows [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` where MAJOR breaks an existing campaign or workflow, MINOR adds significant new capability, and PATCH fixes bugs without changing behavior.

The current installed version is recorded in the `VERSION` file at the repo root. Run `/dnd update --check` to compare your local copy against `origin/main`.

Versions before **1.6.0** are reconstructed retroactively from git history; the dates reflect the commit each version is anchored on. Going forward, every release lands in the same commit as a `VERSION` bump and a CHANGELOG entry.

---

## [Unreleased]

## [1.9.0] — 2026-05-22 — Community release: i18n + optional physical dice server (hardened)

Two community contributions landed in this release, both opt-in / additive — existing campaigns are unaffected unless you choose to engage with the new features.

### CJK input + multi-language SFX triggers (#32 — @canxer314)

Thanks to **@canxer314** for genuinely thoughtful i18n work. The `display/audio.py` SFX trigger map is refactored from inline regex patterns into a per-language data structure so future contributors can drop in Japanese, Korean, or any other language pack with minimal friction. A Chinese (`zh`) pack ships with this release. `_PRINTABLE` and `_CHAR_NAME_RE` in `display/dnd-display-app.py` and `display/wrapper.py` are widened to accept CJK Unicode ranges (U+4E00–U+9FFF, U+3400–U+4DBF, U+3000–U+303F, U+FF00–U+FFEF) without weakening the existing shell-injection filter. Backward-compatible by default — `_SFX_LANGUAGES = ['en']` keeps English-only behavior unless explicitly switched.

非常感谢您的贡献!

### Optional physical 3D dice server (#30 — @ethan-piper)

Thanks to **@ethan-piper** for a beautifully atmospheric piece of work. The new `dice-server/` directory adds an opt-in local Flask server + Three.js phone client that turns each player's phone into a tactile 3D dice tray. When the DM rolls for a PC, dice push to that player's phone — they shake or tap to cast, and the result returns to the campaign. NPC/DM rolls auto-resolve server-side. Real polyhedron geometry, brass PBR material with ACES tone mapping, synthesized clatter / thud / chime audio, and a "consecrate" ritual to anchor a player's tab to the table. Existing `dice.py` behavior is preserved when the server isn't running.

### Hardening applied on top of #30

A security-review skill pass on the dice-server PR flagged a handful of items worth tightening before release. None of these are structural changes — the contributor's core design and code are preserved:

- **`dice-server/server.py` default-bind to `127.0.0.1`.** Previously bound `0.0.0.0` unconditionally. Now binds localhost by default; pass `--lan` (or use the bundled launchd plist which sets the flag) to expose to phones on the LAN. Protects against accidental LAN exposure when developing or running the server briefly without thinking about the network.
- **Subresource Integrity (SRI) on the unpkg Three.js import.** `dice-server/dice.html` now uses a `<script type="importmap">` with `integrity` field pinning the SHA-384 hash of `three.module.js@0.160.0`. If unpkg ever serves modified content for that exact version, the browser refuses to execute it. SRI omitted on the Google Fonts CSS link because Google serves UA-varying content (no single hash works); inline comment documents the choice.
- **TTL sweep on the in-memory `rolls` dict.** Entries older than 1 hour are pruned on each `/roll`, `/submit`, `/spec`, and `/result` request. Cheap O(n) sweep; prevents long-running servers from accumulating roll records forever.
- **`scripts/dice.py` opt-in inverted.** Default is now `DND_DICE_PHYSICAL=0` (no server probe, zero added latency for users who didn't install the optional server). Opt-in two ways: set `DND_DICE_PHYSICAL=1`, or have `~/.dnd-dice/` exist (the `install-launchd.sh` script creates this marker automatically). Users who explicitly install the dice server get the physical-roll routing without doing anything else; users who never installed it pay no cost.
- **`SKILL-commands.md` health-probe conditional.** The `/dnd new` step 15 and `/dnd load` step 1 dice-server-check sub-step now short-circuits when neither `~/.dnd-dice/` exists nor `DND_DICE_PHYSICAL=1` is set — no `curl` probe at all for users who haven't installed the optional server.

---

## [1.8.0] — 2026-05-08 — D&D 5e 2024 (SRD 5.2) ruleset support

The skill now supports both **2014 (SRD 5.1)** and **2024 (SRD 5.2)**, declared per campaign on the `state.md` header line. **2014 stays the default** — nothing about an existing campaign changes unless the DM opts in. Routing happens at every `/dnd load` via `paths.campaign_ruleset()`. A backwards-compat migrator handles legacy campaigns with a one-time prompt and a timestamped backup before any write.

### What changed

**Per-campaign ruleset field**

`state.md` header gains `**Ruleset:** 2014` or `**Ruleset:** 2024`. `/dnd new` step 2 prompts at creation time. `/dnd load` reads the field every session and routes lookups, combat, and the procedural docs for character creation and level-up to the matching code path.

- **`paths.campaign_ruleset(name)`** reads the header, returns the declared value or the default (`2014`) for legacy campaigns. Exposed on the CLI as `paths.py campaign-ruleset <campaign>`.
- **`paths.srd_path(ruleset)`** resolves to `data/dnd5e_srd.json` (2014) or `data/dnd5e_srd_2024.json` (2024). Exposed as `paths.py srd-path [2014|2024]`.

**2024 SRD dataset (`data/dnd5e_srd_2024.json`)**

1,424 records pulled from CC-BY-4.0 sources — `5e-bits/5e-database` (`src/2024/en/`) and `foundryvtt/dnd5e` (`packs/_source/spells24/`, `actors24/`, `classfeatures24/`). Build with `python3 scripts/build_srd.py --ruleset 2024` (one-time, ~3 minutes).

- 341 native 2024 spells, 376 native 2024 monsters, 8 weapon mastery properties, 9 species, 24 subspecies, 17 origin / general / fighting-style feats, the 4 SRD 2024 backgrounds, plus equipment, magic items, conditions, and class features.
- Every record carries `_source` (e.g. `foundryvtt-2024`) and `_license` (`CC-BY-4.0`) so any single entry traces back to its origin.
- Foundry token resolvers in `_strip_html` and the actor-item path: `[[expr]]{label}` rolled-display, `@UUID[id]{label}`, `&Reference[id]{label}`, activity-aware lookup tokens, malformed `&Reference[id}` (curly-closer typo from upstream). Output is whole-dataset artifact-clean — bad-substring scan across 10 categories returns zero hits over 1,424 records.

**Weapon mastery in `combat.py`**

The 8 properties — Vex, Topple, Sap, Cleave, Graze, Nick, Push, Slow — wired into `combat.py attack --mastery <property>`. A Fighter applying Sap on a hit gets the disadvantage tracked on the target's next attack without anyone remembering the rule. Standalone `combat.py mastery <prop>` and `combat.py masteries` subcommands surface the canonical mechanical effect for narration.

**Backwards-compat migrator (`scripts/migrate_ruleset.py`)**

Legacy campaigns auto-prompt for migration on the next `/dnd load`.

- **`--check`** is strictly non-mutating. Exit codes: `0` = already migrated, `1` = needs migration, `2` = missing campaign.
- **`--ruleset 2014|2024 --yes`** stamps the field after backing up `state.md` to `state.md.backup-pre-ruleset-<timestamp>`. Idempotent — re-running on a migrated campaign is a clean no-op.
- The default for legacy campaigns is **2014** (they *were* 2014; silently flipping mid-arc would change character math under the players' feet). Explicit migration to 2024 via `--ruleset 2024 --yes` is a separate manual exercise.

**`lookup.py` ruleset-aware routing**

Accepts `--campaign <name>` (auto-routes via `paths.campaign_ruleset`) or `--ruleset 2014|2024` (explicit override). With no flag, defaults to 2014; emits a one-line stderr hint when the 2024 dataset is also present.

**Display companion ruleset badge**

Sidebar `#ruleset-badge` in the world-clock cluster — subdued amber for 2014, gold-accented for 2024. Server reads `paths.campaign_ruleset` on `/stats --set-campaign`; `push_stats.py` exposes `--ruleset` as an explicit override.

**Procedural updates**

- `/dnd new` step 2: ruleset selection question; build dataset on the spot if 2024 is chosen and missing.
- `/dnd load` step 2: `migrate_ruleset.py --check`; one-time prompt for legacy campaigns; renumbered subsequent steps.
- `/dnd character new` and `/dnd level up`: ruleset-aware branching for subclass-at-3, ASI source (race in 2014, background in 2024), and origin feats.

### Mechanic differences applied at the table

| Mechanic | 2014 | 2024 |
|---|---|---|
| Subclass timing | varies by class (1 / 2 / 3) | level 3 across the board |
| ASI source | race | background |
| Origin feat | n/a | granted at level 1 by background |
| Weapon mastery | n/a | 8 properties |
| Exhaustion | 6-level table with varied effects | 1 stack = -2 to all d20 rolls (cumulative); death at level 6 |

Combat resolution, dice, initiative, AC/HP derivation, XP tables, cantrip damage scaling, and rest recovery are identical between editions.

### Known limits

- **No mid-arc auto-rebuild.** Switching an in-progress campaign mid-arc is allowed by the migrator but doesn't recompute character builds.
- **Non-SRD 2024 supplemental content.** Wikidot has no 2024 surface yet; `build_supplemental.py --ruleset 2024` writes a stub file with documented `_meta`. Lookups for non-SRD content in a 2024 campaign degrade to the 2014 entry.
- **No mid-session ruleset switching from the display.** The badge surfaces the campaign's ruleset; there's no UI to flip it from the couch.

### Credit

- [`5e-bits/5e-database`](https://github.com/5e-bits/5e-database) — base SRD surface for both 2014 and 2024.
- [`foundryvtt/dnd5e`](https://github.com/foundryvtt/dnd5e) — extended 2024 packs (`spells24/`, `actors24/`, `classfeatures24/`, etc.). All foundry content is CC-BY-4.0 with provenance preserved per record.

---

## [1.7.5] — 2026-05-01 — Display robustness: send.py + tail persistence + arc pre-emption

Three long-standing reliability bugs land hard fixes in this release. Each one had been tripping live sessions repeatedly; the fixes are structural rather than patch-shaped, with regression tests so they don't come back.

### What changed

**send.py — body-bundling restored, integrity checks added**

The bug: when `--stat-*` flags were combined with a heredoc body (the documented pattern for bundling state changes with narration), `send.py` would dispatch the stat update but silently drop the narration text. Root cause was in the stdin-read decision: `_build_stats_payload(args)` was being treated as a "body-less" signal, so reading stdin was skipped even when a heredoc was attached.

- **Stdin decision rewritten.** Three categories are now distinguished cleanly:
  - Content flags (`--player`/`--npc`/`--dice`/`--tutor`/`--action`) → body required, stdin always read.
  - Truly body-less flags (`--inspiration-*`, `--xp-award`, `--milestone-*`) → stdin never read; safe in chained Bash blocks.
  - Stat flags (`--stat-*`, `--effect-*`) → body OPTIONAL; stdin is read when piped (heredoc), skipped when an interactive TTY (avoids blocking).

- **Pre-flight integrity checks.** Before posting, every payload runs through `_validate_payload(...)`: chunk payloads must have text or an award; multiple content tags (e.g. `--player` + `--npc`) are rejected; stats payloads must carry a list. Validation failures abort with `sys.exit(2)` and a clear stderr line including the offending payload — no more silent drops.

- **HTTP-level receipt verification.** The `_post(...)` helper now logs every send to a per-process `_SEND_LOG` and inspects the response status. Non-2xx responses surface the body excerpt to stderr. Connection refused (display offline) is the only "expected" silent failure.

- **Post-flight self-check.** After all sends, the script tallies failures from `_SEND_LOG`. Display-offline yields one quiet stderr line; any other partial failure yields a `PARTIAL FAILURE` summary and `sys.exit(3)` so the caller can react.

- **Optional `--verify` round-trip.** When set, after sending the script GETs the new `/health` endpoint to confirm the server is processing requests. Mismatches surface clearly. Use during dev/debug.

**dnd-display-app.py — non-destructive tail persistence + atomic writes**

The bug: `session_tail.json` was being silently wiped to `[]` between sessions, so `/dnd load` had no last-scene replay to play back. Replay had only worked once or twice across many sessions.

Root cause traced to a filtering+persistence chain in the tail buffer code. `_load_tail()` cleared the buffer first then re-appended campaign-filtered entries; if every entry filtered out (or the file was empty), the buffer ended up zeroed. The next `_persist_tail()` then wrote `[]` over the file. With dual-path resolution (campaign-side vs legacy fallback), the failure was hard to pin down.

- **`_load_tail` is now non-destructive.** Builds a candidate buffer first, only swaps it in if at least one entry survived filtering. Empty file → buffer left alone. All-filtered → buffer left alone. Corrupt JSON → buffer left alone, error logged.

- **`_persist_tail` skips on empty.** Refuses to overwrite an existing non-empty file with an empty buffer. Logs a stderr warning when it does so. Breaks the "wipe → persist → file lost" chain at the persistence end too.

- **Atomic writes.** `_persist_tail` writes to `<path>.tmp` then `os.replace(...)` — readers (the next `/dnd load`) can never see a partial or zero-byte state.

- **Legacy fallback path removed.** The skill-side `~/.claude/skills/dnd/display/session_tail.json` fallback is gone. Tails only ever land in the campaign-specific path. If `CAMP_FILE` is missing/empty, persist holds the buffer in memory and skips disk — no more silent bleed across campaigns.

- **`/health` endpoint added.** Returns `alive`, `tail_buffer` count, `tail_file_size`, `text_log` count, `campaign`, `clients`. No auth required (no PII). Used by `send.py --verify` and external monitors.

**`/dnd end` tail backstop + `verify_tail.sh` + `write_canonical_tail.py`**

Even with the in-process guards above, `/dnd end` now belt-and-suspenders the tail:

- Before killing the display, `verify_tail.sh <campaign>` checks the on-disk tail is healthy (>50 bytes, parses as a non-empty JSON list, entries have recognizable shape). Exit 0 = healthy; exit 1 = unsafe to rely on.
- If unhealthy, the DM writes a canonical replacement directly to disk via `write_canonical_tail.py` from session context — bypasses the display entirely so the file is good even if the server died unexpectedly. Atomic write, campaign-stamped, capped at 30 entries.
- Re-verification post-kill catches any final-write race.

**Beat 2b structural fix — pre-emption is a revision trigger**

The bug (campaign-level): when players act faster than the world, the `world_pressure` event for an outstanding beat plays out fully without the beat's `what_changes` consequence landing. Beats were going stale and steering notes were being rewritten manually.

Root cause: dynamic-arc beats were being generated with `what_changes` written event-shaped (something specific happens) when it should be consequence-shaped (something fundamentally different is true).

- **SKILL.md rule 8 added (Pre-emption is a revision trigger).** When `world_pressure` delivers but the consequence doesn't land, this triggers `/dnd arc revise` automatically at `/dnd end`. Three landing-path templates: **cost path** (the party paid for moving fast), **secondary consequence path** (the world responds to being pre-empted in a way the party didn't anticipate), **deferred path** (rewrite `world_pressure` toward the same consequence on a longer horizon).
- **`/dnd new` step 12 strengthened.** Arc-generation prompt now explicitly demands `what_changes` be consequence-shaped, with worked event-vs-consequence example.
- **`/dnd end` arc-check rewritten.** Now performs an explicit pre-emption check on each outstanding beat and auto-triggers `/dnd arc revise` when needed. The DM doesn't have to spot it.
- **`/dnd arc revise` enhanced.** Surfaces the three landing-path templates as a structured choice; before/after diff for the affected beat is shown for review.

### Tests

- New `tests/test_display_robustness.py` (18 tests) covers:
  - Stdin-read decision across all flag combinations including the bundled-stat regression
  - Payload validation (text-or-award required, multiple-content-tags rejected, stats-as-list)
  - Tail load: empty file / filtered-out / matching / corrupt JSON / missing CAMP_FILE
  - Tail persist: skip-on-empty-over-content / atomic / no-camp-no-write
- All 80 tests in the suite pass.

## [1.7.4] — 2026-05-01 — Stack-based milestone counter (backport from open-tabletop-gm v0.9.0)

A counted milestone counter for the rewards that don't fit Inspiration's binary shape — Bardic Inspiration dice, homebrew Hero Coins, Fate Tokens, alternate-system reward tokens, anything that *accumulates*. The existing Inspiration code is unchanged; the binary gold badge in the sidebar still works as before. This release adds a parallel, stack-based reward UI alongside it.

### What's new

- **`/dnd graph`-style send.py flags**:
  - `send.py --milestone-award NAME [--reason "..."] [--label "Bardic Inspiration"]`
  - `send.py --milestone-spend NAME [--label "..."]`

  Default label is `"Milestone"`. Use the system-specific term in `--label`.

- **Sidebar counter** — each player card renders one row per active milestone label with a gold count pill (`HERO COIN  3`). Empty labels don't render; a label is removed from the underlying `milestones` dict on decrement-to-zero.

- **Server-side mutation ops** `_milestone_inc` and `_milestone_dec` — same pattern as `_conditions_add` / `_slot_use`. Increments respect optional per-label `milestone_caps` (set to `{"Bardic Inspiration": 1}` for an effectively-binary reward). Decrements floor-clamp at 0.

- **Feed block** with gold-glow styling — `.milestone-block` rendered when an award fires. Persists to text_log + session tail; replays on browser reconnect.

### Test suite (62 total, up from 55)

`tests/test_milestone_counter.py` — 7 new tests covering increment, decrement, label removal at zero, cap enforcement, multi-label coexistence, decrement-below-zero clamping, and isolation from the existing binary `inspiration` boolean.

### Compatibility

- Existing campaigns: no change.
- Existing `inspiration_award` flow: untouched. The binary badge and gold-glow inspiration block continue to work.
- New `milestones` dict on player records: created on first award. No migration.

### Why this and not just inspiration?

D&D 5e's core Inspiration is binary — you have it or you don't. But many tables track *additional* reward currencies: Bardic Inspiration die counts, homebrew Hero Coins for great roleplay, Fate Tokens for cinematic moments, table-favorite "DM Coins" you can cash in for a reroll. The binary `inspiration` field can't represent these. Now you can:

```
$ python3 display/send.py --milestone-award "Aldric" --label "Bardic Inspiration" \
    --reason "rallied the crew at the harbor"
```

Sidebar shows `BARDIC INSPIRATION  1`. Award twice more → `3`. Spend one → `2`. Spend remaining → row disappears.

---

## [1.7.3] — 2026-05-01

Future-tense planning verbs land in the seed. The recall gap from earlier today's research is closed — the deterministic extractor now picks up GM session-prep prose like *"Vedra plans to file the nomination Friday"* or *"Mira intends to confront Aldric at dawn"*, not just past-tense narrative.

### What's new

- **Six new borderline verb entries**: `plans_to`, `intends_to`, `scheduled_to`, `aims_to`, `expected_to`, `targets`. All `lifetime: dispositional` (intentions can change). All medium-confidence by default — the GM should review before applying because the patterns are looser than past-tense SVO.
- **`V` wildcard in pattern templates** — represents a variable verb phrase (1–4 lowercase tokens) between a fixed modal phrase and an entity. Lets one template like `"X plans to V Y"` match `"plans to file"`, `"plans to meet"`, `"plans to ambush before dawn"` against the same regex. Implemented with `(?-i:...)` so the wildcard never accidentally consumes a capitalized entity prefix.

### Test suite (now 55 tests)

- Seven new `FutureTenseVerbTests` — V-wildcard captures the full canonical entity, doesn't consume capitalized names, all six new patterns match expected sentences, end-to-end extraction picks up `plans_to` / `intends_to` / `targets` edges from a synthetic session-log.

### Demo verification

A session 7 added to the Havenfall demo:

```
$ /dnd graph extract --deterministic --last-session-only
Captain Renna Voss --[plans_to]--> Mira Solveig    (medium)
  "Captain Renna Voss plans to ambush Mira Solveig at the docks."
Mira Solveig --[intends_to]--> Issaly Wreth        (medium)
  "Mira intends to flip Issaly Wreth before the harvest."
Brother Halvard --[targets]--> Mayor Aldric Brandt  (medium)
  "Brother Halvard targets Mayor Aldric Brandt in his sermons."
```

All three captured with verbatim source-anchors.

### What stays deferred

- **Phase 3 hybrid mode** (deterministic-first, LLM-fallback). Still on the design board, still unbuilt.

---

## [1.7.2] — 2026-05-01

Phase 2.5 — the two graph-feature follow-ups that needed real implementation rather than just design notes. Both ship behind the same opt-in pattern as Phase 2: existing campaigns and `graph.json` files keep working unchanged.

### What's new

- **`/dnd graph supersede-edge`** — mark an edge as superseded (hard retcon). Use when canon explicitly contradicts a prior extraction — a session log was corrected, or a relationship was misread. The wrong edge stays in the graph for audit trail; `scene-context` filters it out, but `subgraph` and `show` queries can still surface it for historical review. Optional `--by <correct-edge-id>` links to the replacement; `--reason "..."` records why. Distinct from `close-edge`: closing ends a real relationship cleanly; superseding says the original was wrong.

  ```
  /dnd graph supersede-edge --campaign havenfall --id e1 --by e9 \
    --reason "S6 retcon: Halvard framed the mayor; Theodora's intel was wrong"
  ```

- **Category-node edges**. State-verbs flagged `category_object_ok: true` in the verb seed (currently `possessed_by`, `worships`, `cleric_of`, `cursed_by`, `fears`, `flagged_offlimits`) now extract proposals where the verb's object is a categorical noun phrase (`a ghost`, `the silver veil`, `some old spirit`) rather than a uniquely-named entity. `extract-apply` auto-creates a node with `category_node: true` and `type: category`; `scene-context` renders it with an `(unnamed)` marker so the GM remembers the player canonically doesn't have a name yet.

  Example proposal:
  ```
  wraith --[possessed_by]--> Brother Halvard  (low) [X is category]
  Issaly Wreth --[worships]--> silver veil    (medium) [Y is category]
  ```

  Categorical proposals start at lower confidence than entity-only matches — the captured noun ("ghost") is genuinely ambiguous in a way that named entities aren't.

### Schema additions

- **`superseded_by: <edge-id> | true`** — optional field on edges. Set by `supersede-edge`. `_edge_active_at()` excludes any edge with this field truthy.
- **`supersede_reason: "..."`** — optional companion field with the human explanation.
- **`closed_anchor`** (recap from v1.7.1) — verbatim phrase justifying a closure. Now also rendered in `scene-context` output when present.
- **Node `category_node: true`** — flag on auto-created category nodes. Display layer renders these with an "(unnamed)" suffix.

### Tests

Suite is now **48 tests in ~2s**:
- 12 verb-table sanity tests
- 25 deterministic-extractor tests
- 11 end-to-end CLI tests, including:
  - `supersede-edge` marks the edge AND filters it out of `scene-context` at later sessions
  - `supersede-edge` without `--by` (retcon with no replacement) records `superseded_by: true`
  - `extract --deterministic` on a possession scene (`"Aldric is possessed by a ghost"`) produces a categorical proposal
  - `extract-apply` auto-creates a `cat_*` node with `category_node: true`

### Bug fixes

- **Category target slot detection**: the deterministic extractor was picking the emit's `to` slot as the categorical target, but verbs like `possessed_by` emit `{from: Y, to: X}` — Y is the grammatical object, not the emit's `to`. The category slot is now resolved from the LAST `X/Y/Z` placeholder in the template (the verb's grammatical object in SVO), not from emit metadata.
- **Section-header pluralization**. `## categorys` → `## categories`. One more node type and we'd have noticed eventually; cosmetic but caught it in the demo.

### What stays deferred

- Future-tense planning verbs (`plans_to`, `intends_to`, `scheduled_to`) — still need the DM session-prep corpus pass.
- Hybrid Phase 3 mode (deterministic-first, Haiku-fallback on unmatched sentences).

---

## [1.7.1] — 2026-05-01

The Phase 2 deterministic extractor lands one day after the Phase 1 release. We had been planning to ship this as a separate v1.8 minor; on second look it's better framed as completing what v1.7.0 promised. The Haiku-backed `extract` is still there and unchanged — `--deterministic` is a new opt-in flag on the same subcommand.

This release also adds a test suite (45 tests across three files) so future changes to the graph extractor don't regress what was just shipped.

### What's new

- **`extract --deterministic`** — pattern-matches sentences against `data/graph/verb_table_seed.yaml` instead of calling Haiku. Output format is identical to the LLM extractor; `extract-apply` accepts proposals from either path. Zero LLM cost. Estimated recall ~50%, precision ~95% on clean SVO and SVO-with-prep relationships. The Haiku path stays the default until your campaigns have run with the deterministic extractor for a while.
- **`extract --last-session-only`** — narrow extraction to the most recent `## Session N` block of `session-log.md` (skip the archive). Useful for end-of-session sweeps.
- **`extract-apply --review`** — interactive proposal-by-proposal walkthrough with `y / n / q` prompts. Each prompt shows the verbatim source anchor and confidence. Mutually exclusive with `--pick`. Quitting (`q`) honours edges already accepted but stops processing further proposals.
- **`close-edge --anchor "..."`** — record the verbatim phrase that justifies the closure as a new `closed_anchor` field on the edge. The original since-anchor in `source.anchor` is preserved; closure history is now also auditable. Optional and backwards-compatible.

### Schema additions to the verb-table seed

- **`lifetime: event | state | dispositional`** annotated on every inclusion + borderline entry (119 entries). Distinguishes immutable past occurrences (`killed`, `told`) from ongoing relationships (`serves`, `married_to`) from drift-over-time stances (`fears`, `committed_to`). The deterministic extractor uses this to scope future state-end logic.
- **`category_object_ok: true`** flag on state-verbs whose object is often a category rather than a unique entity (`possessed_by a ghost`, `worships the gods`). Currently informational; consumed by Phase 2.5 work on category-node edges.

### Test suite

- **`tests/test_verb_table.py`** (12 tests) — sanity checks on the seed: YAML parses, every entry has `lifetime`, lifetime values valid, spot-checks against known event/state/dispositional verbs, `category_object_ok` only on state/dispositional.
- **`tests/test_deterministic_extract.py`** (25 tests) — entity recognizer (npcs.md / npcs-full.md / world.md), sentence splitter, pattern regex builder, alias index (first-word / surname / middle-subsequence aliases, stop-word rejection, ambiguity skipping, canonical precedence), session-number resolution, end-to-end on a synthetic campaign, dedup, `--last-session-only` behavior, empty-campaign handling.
- **`tests/test_campaign_graph.py`** (8 tests) — end-to-end against the actual CLI: `add-node` / `add-edge` / `close-edge` (with and without `--anchor`), `scene-context` filtering by `--at-session` (closed edges hidden), uninitialized-graph notice, `extract --deterministic` write, `extract-apply --pick` subset application.

Run from repo root: `python3 -m unittest discover tests -v`

### Bug fixes

- **`build_alias_index` now generates surname / middle-subsequence aliases** in addition to the first-word alias, so a session-log saying "Aldric Brandt" or just "Brandt" still resolves to the canonical "Mayor Aldric Brandt". The previous first-word-only behaviour caused the deterministic extractor to miss most of a real campaign's relationships.
- **Stop words never become aliases**. `### The Council` in `world.md` was previously generating a `"The"` alias that case-insensitively matched every "the" in any sentence, producing edges like `Drave Cors --[met]--> the`. Articles, prepositions, and conjunctions are now excluded from alias promotion.
- **Verb-table loader handles both repo layouts.** `data/graph/verb_table_seed.yaml` (public repo) and `data/verb_table_seed.yaml` (live skill) are both checked, so the deterministic extractor works in either location without manual configuration.

### What stays deferred

- **Phase 2.5 schema additions** — `closed: {session, anchor}` as an object (the lightweight `closed_anchor` field is shipped instead), category-node edges via `category_object_ok` consumption, hard-retcon `superseded_by` field. Documented in `docs/research/graph/phase-2-3-plan.md`.
- **Hybrid mode (Phase 3)** — pattern-first then Haiku-fallback on unmatched sentences. Defer until Phase 2 has soaked.
- **Future-tense planning verbs** — `plans_to`, `intends_to`, `scheduled_to`. Need a separate corpus pass on DM session-prep documents (Reddit narrative is past-tense).

---

## [1.7.0] — 2026-05-01

Earlier than expected. The v1.6.0 notes said *"the implementation lands in v1.7+"*, which framed the work as somewhere on the horizon. After looking at it again the morning after — the implementation has been running in our own live campaigns for weeks, the A/B study showed clear and bounded behaviour, and the risk profile of holding it back was higher than the risk of shipping it. So it ships now.

The campaign relationship graph is no longer a research preview. It is a feature.

### What's new

- **`scripts/campaign_graph.py`** — full extractor + query engine in the canonical skill. Subcommands: `init`, `add-node`, `add-edge`, `close-edge`, `list`, `show`, `subgraph`, `scene-context`, `extract`, `extract-apply`. Local-only, time-stamped (`since_session` / `until_session`), with verbatim source-anchors on every edge.
- **Auto-pull at `/dnd load`.** The scene-context query runs as part of the load flow, before the recap, so Claude has the active subgraph in scope before it speaks. If the graph isn't initialized yet, the load flow offers an auto-init with a backup-first prompt — see below.
- **Sweep at `/dnd save`.** The save flow scans the session for relationship shifts that weren't recorded live and presents them to the DM as a numbered list (`y / pick / skip`) before writing.
- **`/dnd graph` command suite** documented end-to-end in `SKILL-commands.md`. The README command table covers the most common subcommands.

### Backwards-compatible auto-init

Existing campaigns don't have a graph. The `/dnd load` flow now handles this gracefully:

> *"This campaign doesn't have a relationship graph yet. I can initialize one now — it improves long-session continuity recall when `npcs-full.md` falls out of context. As a safety precaution, I'll back up the campaign first to `~/.claude/dnd/campaigns/<name>.backup-YYYYMMDD-HHMMSS/`. Proceed? [y/n]"*

`y` runs a `cp -R` snapshot before anything touches the campaign, then proposes seed nodes and edges from the existing markdown for DM approval. `n` continues without the graph for that session and doesn't re-prompt. No silent extraction, no auto-write — the same review-then-apply discipline that's been in the sandbox since Phase 1.

### What stays in `docs/research/graph/`

- **`phase-2-3-plan.md`** — design for the deterministic verb-table extractor (Phase 2) and hybrid path (Phase 3). Phase 2 ships when the three schema additions (`closed`, `lifetime`, `category_object_ok`) and `--review` interactive apply land.
- **`ab-experiment-findings.md`**, **`verb-gap-categories.md`** — the research record. Useful background reading for anyone running into similar continuity-gap issues; not required to use the feature.
- **`discussion-post-draft.md`** — community write-up draft for GitHub Discussions.

### What's next

- Phase 2 deterministic extractor (zero LLM cost, ports cleanly to the LLM-agnostic [open-tabletop-gm](https://github.com/Bobby-Gray/open-tabletop-gm) fork).
- Schema additions: `closed` field on state edges, `lifetime` column on verbs, `category_object_ok` flag for state-verbs whose object is often categorical.
- A separate corpus pass on DM session-prep documents to capture future-tense planning verbs (`plans_to`, `intends_to`).

Thanks again to [@ethros19](https://github.com/ethros19) (Ethan Piper) for the issue #7 thread and the months of long-campaign feedback that made the case for shipping this rather than holding it.

---

## [1.6.0] — 2026-04-30

Today's update is a quiet but meaningful one, and it lands on a problem that's been with us — and the broader LLM-RPG community — since very early on. [@ethros19](https://github.com/ethros19) (Ethan Piper) first surfaced it in [issue #7](https://github.com/Bobby-Gray/claude-dnd-skill/issues/7) back in v1.4 days, and has been the most consistent voice keeping us honest about the long-context failure modes ever since. The shape of the problem: after enough sessions, the DM voice will sometimes treat a known character as a fresh contact — *"go see the chandler, tell him I sent you"* — when the player and that character were introduced sessions ago. The relationship facts are always in the canon. They've just fallen out of scope after compaction.

We've shipped a few different methodologies for this over the last several months. The compaction-drift fix in 1.4 (re-read the source, never trust the compacted impression). The Live State Flags block (cover, faction stances, dispositions in compact key-value form). The targeted-Read directives in `SKILL.md`. Each one held the line at the scale of the campaigns we were running at the time.

Campaigns kept getting longer. The continuity surface kept getting wider. This release is the next scale of that same arc — a structural relationship graph alongside the markdown files, with verbatim source-anchors on every edge, designed to surface relationship facts cheaply when the full files are no longer in context. We think it scales much higher than the previous tools, and the research below explains why.

This release publishes the research, the design, and the tooling. It does **not** flip the implementation on yet — that lands in v1.7+. For now, what's new is documentation, data, and the version-tracking infrastructure that's been overdue for a while.

Existing campaigns are unaffected. Nothing here changes how you play today.

### Versioning is now tracked

- New `VERSION` file at the repo root. New `CHANGELOG.md` (this file) with the full history reconstructed from past releases.
- `/dnd update --check` now shows local vs. remote version side by side, so it's obvious at a glance whether you've fallen behind.

If you've ever wondered which copy of the skill you have, that's resolved.

### Campaign-graph research preview

A typed-edge relationship graph that runs alongside `npcs.md`, `state.md`, and `session-log.md`. Every edge carries a verbatim source-anchor pointing back to the line in canon that asserts it — so every claim the graph makes is auditable.

You can read everything we've put together so far under `docs/research/graph/`:

- **A/B experiment findings.** A controlled replay study (60 generations across three prompt-shape variations) measuring whether the graph reduces continuity errors. The honest answer turned out to be more interesting than the original hypothesis.
- **Verb-table gap audit.** A 17-category taxonomy of NPC-relationship verbs and which ones the seed table is missing. Eight new edge types are promoted in this release, including `possessed_by`, `in_love_with`, `swore_oath_to`, and `sworn_enemy_of`.
- **Phase 2 / 3 plan.** The design for the deterministic extractor that ships next. Six friction findings from Phase 1 live-trial, three new schema fields specified.

The supporting tooling is here too:

- `data/graph/verb_table_seed.yaml` v0.5 — saturated seed of ~50 inclusion verbs from 1,014 observations across 7 live campaigns, 4 published adventures, and 280 Reddit narrative posts.
- `scripts/graph/experiment_replay.py` — the A/B harness, configurable for your own gap-prone moment.
- `scripts/graph/external_corpus_collect.py` + `external_corpus_extract.py` — the Reddit collector and Haiku verb-frequency extractor we used to build the seed.

If any of that is interesting to you, the docs are written to be read on their own.

### Bug fixes

- **Spell slots no longer 500 on long rest.** Display-side payloads using the legacy `{remaining, max}` slot schema were tripping a `KeyError` during slot restoration. The server now accepts both shapes silently. This affects you only if you've seen "spell slots not restoring" after a long rest; you don't need to do anything to apply the fix.

### What's next

- v1.7 will land the deterministic graph extractor and the `/dnd graph` commands in the live skill — opt-in per campaign, behind a clear "experimental" marker.
- The schema changes (`closed` field on state edges, `lifetime` column on verbs, `category_object_ok` flag) need to ship before promotion to canonical.
- A separate corpus pass on DM session-prep documents is on the list to capture future-tense planning verbs (`plans_to`, `intends_to`) — those don't show up in past-tense narrative posts, which is the gap we already know about.

Thanks for sticking with this through Phase 1. The research turned out richer than we expected, and the deterministic path is now clear.

---

## [1.5.0] — 2026-04-30

This was the last pre-versioning release. PR #14 closed out the long tail of display companion polish that had been accumulating, plus the two skill-management commands that needed to land before version tracking could ship.

### What's new

- **`/dnd update`** — pull skill changes from `origin/main`. Refuses on a dirty tree, fast-forward only, so it never silently merges divergent history.
- **`/dnd path`** — view or relocate campaign storage via `DND_CAMPAIGN_ROOT`. Useful if you keep your campaigns in iCloud, on a network drive, or anywhere other than the default location.
- **Inspiration awards now render the reason inside the block.** Previously the reason landed only in the sidebar badge and you had to look twice to see why someone got it.

### Bug fixes

- **`send.py` no longer hangs on chained-bash invocations.** Body-less flags (like `--inspiration-award` or `--xp-award`) were waiting on stdin that never came. Detection skips the read entirely now.
- **Display tail replay** correctly resumes on session reload.
- **Heredoc gotcha warning** added to the send-batching docs after one too many missed `${VAR}` expansions.

---

## [1.4.0] — 2026-04-20

A big one. Every campaign now has a committed three-act narrative shape generated at `/dnd new`, and the DM is aware of it during play.

The arc isn't a script. Each of its six beats is defined by what *changes* in the story when it lands, not by what specifically happens. That gives Claude flexibility on how each beat arrives while committing to the fact that it must arrive. We've been running this on live campaigns for over a week and it's the difference between "the session was fun" and "the session was fun *and* it moved the story forward."

### What's new

- **Dynamic arc system.** Auto-generated from the world's threat, factions, and Three Truths. Six beats: 1a/1b (setup), 2a/2b (confrontation), 3a/3b (resolution). The arc commits to a thematic resolution. The shape bends; it doesn't break.
- **`/dnd arc advance <beat>`** — mark a beat complete at session end. Updates `outstanding_beats` automatically.
- **`/dnd arc revise`** — when a player choice significantly redirects the story, the arc adjusts outstanding beats to fit the new direction without retconning what already happened.
- **`/dnd arc new`** — once all six beats land, generate a new arc from the consequences of the first. Same world, new story question.
- **Arc-aware DM steering.** Claude reads `## Campaign Arc` at every session load. World pressure for the next beat lands as a visible event before the beat itself. No beats delivered cold.

### Bug fixes

- **Compaction drift (#7).** When the conversation context compacts, Claude's impression of faction states and NPC dispositions becomes lossy. The DM rules now require re-reading the source — the smallest section that covers the claim — before any recap or status statement. A new `## Live State Flags` block in `state.md` makes that re-read cheap: cover, faction stances, and dispositions live there in compact key-value form.

---

## [1.3.0] — 2026-04-16

Two quality-of-life improvements that, in combination, made tracking spell durations and non-SRD content much less painful.

### What's new

- **Timed effect tracking.** `tracker.py` now tracks effect start/end with rounds/minutes/hours/indefinite durations. Auto-expiry warnings fire when a Bless wears off mid-combat or a Hex's hour is up. Concentration syncs automatically.
- **`send.py --stat-*` flags.** HP, spell slots, conditions, concentration, inventory, effect-start, effect-end — all bundle with the narration send in a single call. No more separate `push_stats.py` round-trip just to update one stat.
- **Supplemental SRD dataset.** `dnd5e_supplemental.json` covers non-SRD spells and features (Xanathar's, Tasha's, subclass features). `build_supplemental.py` fetches descriptions from dnd5e.wikidot.com for any character feature not in the bundled SRD.

---

## [1.2.0] — 2026-04-15

The bundled SRD release. Spell and feature lookup is now offline, instant, and clickable from the character sheet.

### What's new

- **Bundled `dnd5e_srd.json`** — 1,453 records: spells, equipment, magic items, conditions, monsters, class features. No download required at runtime.
- **`/dnd data sync`** — rebuilds the dataset from upstream sources (5e-bits + FoundryVTT) only when their SHAs change. Idempotent; safe to run anytime.
- **Clickable spell and feature lookups** in the character sheet modal — tap any name to view the full description. Wikidot fallback link for anything not in the local data.

---

## [1.1.0] — 2026-04-14

This is the release that changed how the table actually plays. Before this, players told the DM what they wanted to do and the DM typed it. After this, players use their phones.

It also paved the way for autorun, which made running a campaign with a partner who isn't quite a DM possible.

### What's new

- **Player input form on the companion UI.** Players submit actions from a phone or tablet on the local network. The action lands in `.input_queue` until the DM presses Enter (or autorun fires), so Claude's context stays under DM control.
- **Autorun mode** (`/dnd autorun on`). Claude drives the turn loop without DM input. Player submissions are sanitized, character-validated, and content-checked before they enter context. A pie countdown on the display shows the next auto-fire window.
- **LAN mode.** The companion serves over your local network. Every device in the room — TV, tablet, phones — sees the same display.
- **TLS / HTTPS.** Self-signed cert generation included. Required for full browser-feature support over LAN, particularly player input from devices other than localhost.

---

## [1.0.0] — 2026-04-13

The point at which the skill felt complete enough to call it a stable foundation. The releases before this were still actively reshaping fundamentals; from this point forward, additions are additions, not rewrites.

### What's new

- **Spell slots in the sidebar.** Pip-graph rendering by level. Live updates from `--stat-slot-use` / `--stat-slot-restore` so the table sees a slot consumed the moment it's cast.
- **Faction panel in the sidebar.** Auto-refreshed faction stances and descriptions.
- **Relationship rendering** in NPC entries — the *Knows / Owes / Fears* block surfaces visibly.
- **Haiku description lookup** for SRD entries. Formats results without round-tripping through Sonnet, so the lookup feels instant.
- **DM Help button (◈).** One-shot contextual hint at the press of a button. Distinct from tutor mode, which is ongoing.

---

## [0.9.0] — 2026-04-12

Quietly the most consequential release before 1.0. We split the system prompt and added targeted-search tooling — and the result was that context bloat stopped being the limiting factor on long campaigns. Everything that came after this depends on the architecture decisions made here.

### What's new

- **`SKILL.md` split** into three files: core rules (always loaded into the system prompt), `SKILL-scripts.md` (script syntax), and `SKILL-commands.md` (command procedures). The latter two load once at session start. Core stays small; reference material is on demand.
- **Context optimization architecture.** Campaign data is tiered: the NPC index is always loaded, full entries pull only when a character becomes relevant, quest hooks and worldbuilding stay in cold storage until called for.
- **`campaign_search.py`** — targeted keyword search across campaign files. Replaces full-file Reads for most recap and status questions, which means more sessions fit in context before compaction matters.
- **Per-viewer DM Hints toggle** on the display companion.
- **Narrative structure standards** + faction and node templates surfaced in `world.md` (Adventure Nodes as situations, not plots).

---

## [0.8.0] — 2026-04-11

A small release with two distinct beneficiaries: brand-new players and experienced players who like to look things up.

### What's new

- **Tutor mode** (`/dnd tutor on`) — automatic hint blocks after every scene, decision point, and roll. Optional, session-scoped, ideal for players new to D&D.
- **SRD data tools.** Initial `data_pull.py` and `lookup.py` for spell and feature reference.
- **Character sheet modal fixes.** Clickable cards open a full sheet (attacks, features, inventory) cleanly on phones and tablets over LAN.

---

## [0.7.0] — 2026-04-11

The companion's visual identity took shape in this release. If you've seen the demo GIF, this is the version it's recorded against.

### What's new

- **LAN mode** for the display companion. Serve over your local network; cast to a TV, mirror to a second monitor, or open on a tablet at the table.
- **Browser-side sound effects.** 12 SFX types synthesized via numpy and played through Web Audio API. Works on any device with the tab open, including phones over LAN.
- **Dynamic sky canvas.** Sun arc, moon, twinkling stars, cloud density — all rendered in real time from world time data. Transitions with time of day and weather.
- **17 scene types**, auto-detected from narration keywords (tavern, dungeon, ocean, crypt, arcane, glacier, and a dozen more). Each one has its own particle effect set.
- **Model routing policy** formalized: Script / Haiku / Sonnet / Opus tiers per task class.
- **Clickable character sheet modal** on sidebar player cards.

---

## [0.1.0] — 2026-04-09

The first commit. Persistent campaigns, full 5e mechanics, atmospheric DM tone, real dice via Python `random`, the twelve applied DM standards, world-generation wizard, and the character creation and import flow.

The shape of the skill was already there. Everything since has been about deepening it.

---

## Versioning policy

- **PATCH** (1.6.x) — bug fixes, doc updates, corpus additions. No behavior change.
- **MINOR** (1.x.0) — new commands, new scripts, new opt-in features. Existing workflows continue to work without modification.
- **MAJOR** (x.0.0) — breaking change to campaign data format, command rename/removal, or workflow that requires migration.

Tag releases with `git tag v<version>` and update both `VERSION` and `CHANGELOG.md` in the same commit. Tags follow `vX.Y.Z` format.
