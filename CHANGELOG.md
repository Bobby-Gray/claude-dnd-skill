# Changelog

All notable changes to the D&D 5e DM skill are documented here. The skill follows [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` where MAJOR breaks an existing campaign or workflow, MINOR adds significant new capability, and PATCH fixes bugs without changing behavior.

The current installed version is recorded in the `VERSION` file at the repo root. Run `/dnd update --check` to compare your local copy against `origin/main`.

Versions before **1.6.0** are reconstructed retroactively from git history; the dates reflect the commit each version is anchored on. Going forward, every release lands in the same commit as a `VERSION` bump and a CHANGELOG entry.

---

## [Unreleased]

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
