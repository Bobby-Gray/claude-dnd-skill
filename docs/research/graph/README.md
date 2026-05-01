# Campaign-Graph Research

This directory holds the design + research artifacts behind the campaign relationship graph that ships in v1.7.0. The graph is a typed-edge structural overlay alongside the canonical markdown campaign files (`npcs.md`, `state.md`, `session-log*.md`, `world.md`); every edge carries a verbatim source-anchor pointing back to the line in canon that asserts it.

**Status:** shipped in v1.7.0. The Phase 1 Haiku-backed implementation is live in [`scripts/campaign_graph.py`](../../../scripts/campaign_graph.py); the `/dnd graph` command suite is documented in `SKILL-commands.md`. Phase 2 (deterministic extractor) is designed and ready to implement.

## What problem this is solving

After enough sessions, the DM voice will sometimes treat a known character as a fresh contact — *"go see the chandler, tell him I sent you"* — when the player and that character were introduced sessions ago. The relationship facts were always in the canon (`npcs-full.md`), but after context compaction those files fall out of scope, and the compacted Continuity Archive bullet doesn't preserve relationship-genealogy details.

The graph is the structural overlay that surfaces those facts cheaply during long sessions, after the full files have been compacted away.

## Documents

- **[ab-experiment-findings.md](ab-experiment-findings.md)** — controlled A/B replay study (60 generations, 3 prompt-shape variations) measuring whether the graph reduces continuity errors. Headline: well-prompted Sonnet doesn't reproduce the gap on a fresh prompt. The graph's primary value is **mid-session context preservation** when `npcs-full.md` is no longer in scope. Secondary value: 9/10 vs 6/10 redirect compliance with the graph's `flagged_offlimits` edge type.
- **[verb-gap-categories.md](verb-gap-categories.md)** — 17-category taxonomy audit of NPC-relationship verbs against the seed table. Identifies high-priority gaps + 8 verb additions promoted in v0.5 of the seed table.
- **[phase-2-3-plan.md](phase-2-3-plan.md)** — design plan for the deterministic verb-table extractor (Phase 2) + hybrid path (Phase 3). Six friction axes from Phase 1 live-trial. Schema additions (`closed`, `lifetime`, `category_object_ok`) specified.
- **[discussion-post-draft.md](discussion-post-draft.md)** — community write-up for GitHub Discussions; references issue #7 and acknowledges prior continuity-fix methodologies.

## Tooling

- **[`scripts/campaign_graph.py`](../../../scripts/campaign_graph.py)** — the shipped extractor + query engine. Subcommands: `init`, `add-node`, `add-edge`, `close-edge`, `list`, `show`, `subgraph`, `scene-context`, `extract`, `extract-apply`. Auto-pulled at `/dnd load` (scene-context) and swept at `/dnd save` (relationship-shift extraction).
- **[`data/graph/verb_table_seed.yaml`](../../../data/graph/verb_table_seed.yaml)** v0.5 — saturated verb seed: 1,014 verb-bearing observations across 7 live campaigns + 4 published adventures + 280 Reddit narrative posts. ~50 inclusion, ~10 borderline, ~20 exclusion, ~35 candidates. Schema additions: `lifetime`, `category_object_ok`. Used by the deterministic Phase 2 extractor (designed; not yet built).
- **[`scripts/graph/experiment_replay.py`](../../../scripts/graph/experiment_replay.py)** — reference A/B replay harness. Configure for your own gap-prone moment.
- **[`scripts/graph/external_corpus_collect.py`](../../../scripts/graph/external_corpus_collect.py)** — Reddit JSON-API scraper (no auth, rate-limited, anonymized). `--query` flag for phrase-anchored search.
- **[`scripts/graph/external_corpus_extract.py`](../../../scripts/graph/external_corpus_extract.py)** — batched Haiku verb-frequency extractor.

## What's next

Phase 2 is the deterministic verb-table extractor — pattern-matching on the v0.5 seed instead of an LLM pass. The plan is fully spec'd in [phase-2-3-plan.md](phase-2-3-plan.md). It needs three schema additions (`closed` field on state edges, `lifetime` column on verbs, `category_object_ok` flag) before it lands. Phase 2 reaches feature-parity with Phase 1 on the high-impact relationship classes (introductions, meetings, named relationships) at zero LLM cost, and is also what the LLM-agnostic [open-tabletop-gm](https://github.com/Bobby-Gray/open-tabletop-gm) fork will pick up when it merges.

Phase 3 is the hybrid path: Phase 2 deterministic first, Haiku fallback only on sentences that didn't match a pattern. Defer until Phase 2 has soaked across multiple campaigns.
