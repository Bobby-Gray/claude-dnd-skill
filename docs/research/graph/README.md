# Campaign-Graph Research

This directory holds the design + research artifacts for an experimental feature: a typed-edge **relationship graph** that runs alongside the canonical markdown campaign files (`npcs.md`, `state.md`, `session-log*.md`, `world.md`).

**Status:** sandbox feature in the live skill. Not yet promoted to the canonical skill in this release. Documentation + tooling published here so the design can be reviewed before the implementation lands in v1.7+.

## What problem is this trying to solve?

After enough sessions, the DM voice will sometimes treat a known character as a fresh contact — *"go see the chandler, tell him I sent you"* — when the player and that character were introduced sessions ago. The relationship facts were always in the canon (`npcs-full.md`), but after context compaction those files fall out of scope, and the compacted Continuity Archive bullet doesn't preserve relationship-genealogy details.

The graph is a structural overlay: every relationship is a typed edge with a verbatim source-anchor pointing back to the line in canon that asserts it. The aim is to surface those facts cheaply during long sessions, after the full files have been compacted away.

## Documents

- **[ab-experiment-findings.md](ab-experiment-findings.md)** — controlled A/B replay study (60 generations, 3 prompt-shape variations) measuring whether the graph reduces continuity errors. Headline: well-prompted Sonnet doesn't reproduce the gap on a fresh prompt. The graph's primary value is **mid-session context preservation** when `npcs-full.md` is no longer in scope. Secondary value: 9/10 vs 6/10 redirect compliance with the graph's `flagged_offlimits` edge type.
- **[verb-gap-categories.md](verb-gap-categories.md)** — 17-category taxonomy audit of NPC-relationship verbs against the seed table. Identifies high-priority gaps + 8 verb additions promoted in v0.5 of the seed table.
- **[phase-2-3-plan.md](phase-2-3-plan.md)** — design plan for the deterministic verb-table extractor (Phase 2) + hybrid path (Phase 3). Six friction axes from Phase 1 live-trial. Schema additions (`closed`, `lifetime`, `category_object_ok`) specified.

## Tooling

- **[`../../../data/graph/verb_table_seed.yaml`](../../../data/graph/verb_table_seed.yaml)** v0.5 — saturated verb seed: 1,014 verb-bearing observations across 7 live campaigns + 4 published adventures + 280 Reddit narrative posts. ~50 inclusion, ~10 borderline, ~20 exclusion, ~35 candidates. Schema additions: `lifetime`, `category_object_ok`.
- **[`../../../scripts/graph/experiment_replay.py`](../../../scripts/graph/experiment_replay.py)** — reference A/B replay harness. Configure for your own gap-prone moment.
- **[`../../../scripts/graph/external_corpus_collect.py`](../../../scripts/graph/external_corpus_collect.py)** — Reddit JSON-API scraper (no auth, rate-limited, anonymized). `--query` flag for phrase-anchored search.
- **[`../../../scripts/graph/external_corpus_extract.py`](../../../scripts/graph/external_corpus_extract.py)** — batched Haiku verb-frequency extractor.

## Promotion gate

Before `/dnd graph` ships in the canonical skill, the implementation must:

1. Phase 2 deterministic extractor merged + tested across ≥3 live campaigns
2. `closed` field on state edges + `lifetime` column on verb table
3. `--review` interactive apply-mode (Phase 1 friction #3)
4. Source-anchor verification at apply time (Phase 1 friction #5)
5. `scene-context` query confirmed working with category-nodes (`category_object_ok`)

Until then: opt-in, sandbox, clearly marked experimental.
