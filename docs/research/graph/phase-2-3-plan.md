# Campaign-Graph — Phase 2 / Phase 3 Plan

**Status:** Phase 1 (Haiku-backed) validated and shipped to the live skill as a sandbox feature; not yet promoted to canonical. Phase 2 (deterministic) is designed and ready to implement against the saturated verb-table seed. Phase 3 (hybrid) is sketched but deferred.

This document captures the design decisions, friction findings from Phase 1 live use, and the migration path forward.

---

## What Phase 1 proved

1. **The continuity-gap class is real and consequential.** A DM voicing an NPC will, over a long session, refer to a known character as a fresh contact. The relationship facts are all in `npcs-full.md` — but after context compaction, that file is no longer fully in scope.
2. **Compacted Continuity Archive bullets aren't sufficient** for relationship-genealogy questions. The "X introduced Y to Z" detail rarely survives summarization.
3. **Haiku extraction recovers the gap-fix edges** with auditable source anchors. Clean SVO sentences ("X sent Y to Z") are recovered ~100% of the time. Precision ≈ 85%; ~15% of proposals have quality issues (abstract targets, role-assignment errors, occasional mis-direction).
4. **The source-anchor field is the audit lineage that justifies the format.** Every extracted edge has `{file, session, anchor}`. A reviewer can grep the anchor, verify the claim, accept or reject. Hallucinated edges are catchable by anchor-not-found.

For the supporting A/B replay study, see `ab-experiment-findings.md` in this directory.

---

## Phase 1 friction callouts (six concrete improvement axes)

| # | Issue | Fix shape |
|---|-------|-----------|
| 1 | **Role assignment** — "X sent Y to Z" sometimes emitted as `X→referred→Z` (wrong) instead of `X→referred→Y, note: to Z` | Pattern post-processor for `X V Y to Z` constructions; deterministic in Phase 2 |
| 2 | **Entity resolution** — abstract targets ("the Island", "the protection network", "their mother") emitted as standalone nodes without canonical resolution | Fuzzy match against existing node list + `npcs.md`/`world.md` indices; strict "skip non-resolvable" mode for low-confidence outputs |
| 3 | **Apply UX** — `--pick N1,N2,...` requires reading proposals once, deciding, then re-running with the pick list | Add `--review` interactive mode: step proposal-by-proposal with y/n/edit/skip prompts |
| 4 | **Confidence scoring** — no per-proposal score; reviewer has to judge each from scratch | High/medium/low based on: anchor-found-in-source, both entities resolved, verb in known-good set, sentence structure clean. Default-apply on high, default-skip on low |
| 5 | **Source-anchor verification** — currently informational only; not validated at apply time | At `extract-apply` time, grep the source file for the anchor phrase. Anchor not found → reject as likely hallucination |
| 6 | **Bidirectional inference** — Haiku sometimes picks the less-narrative direction (`X allied_with Y` when canon says `Y committed_to X`) | Ranked-direction heuristic in deterministic mode; Haiku post-processor for Phase 1 |

Friction #5 is the cheapest and highest-impact; address first if Phase 1 stays in production for any length of time.

---

## Phase 2 — Deterministic extraction

**Why now:** open-tabletop-gm (the LLM-agnostic fork of this skill) needs an extraction path that doesn't require Haiku. Pattern-based extraction is faster, cheaper, reproducible, and portable.

**Why not before now:** the verb table needs to be designed against real corpus. As of this release the seed has 1,014 verb-bearing observations across 7 live campaigns + 4 published adventures + 280 Reddit narrative posts; ~50 inclusion verbs, ~10 borderline. Saturated — diminishing returns observed in pass 2.

### Architecture

```
campaign_graph.py extract --deterministic
```

**1. Entity recognizer**
- Build at extract time from canonical sources: `npcs.md` (name column), `world.md` (settlement details, factions), `state.md → ## Live State Flags`
- Word-boundary regex from alternation of all known names
- Optional alias table per campaign (manual, in `npcs.md` frontmatter)
- Pronoun resolution: skip for v1; flag pronoun-heavy sentences for human review

**2. Verb table** — versioned YAML at `data/graph/verb_table_seed.yaml`. Schema:

```yaml
- verb_forms: [sent, sends, sending, send]
  edge_type: referred_to
  lifetime: event              # event | state | dispositional
  symmetric: false
  confidence: high
  category_object_ok: false    # accept categorical objects ("a ghost") as targets?
  patterns:
    - template: "X sent Y to Z"
      emits:
        - {from: X, to: Y, type: referred_to, note: "to Z"}
        - {from: Y, to: Z, type: met}
    - template: "X sent Y"
      emits: [{from: X, to: Y, type: dispatched}]
```

The seed at `data/graph/verb_table_seed.yaml` (v0.5) has the inclusion + borderline + exclusion lists already populated. New schema fields versus v0.4:
- **`lifetime`** — distinguishes event-verbs (immutable: `killed`, `attacked`) from state-verbs (can end: `serves`, `imprisoned`) from dispositional-verbs (drift over time: `wary_of`, `fears`).
- **`category_object_ok`** — for state-verbs whose object is frequently a category rather than a unique entity (`possessed_by a ghost`, `worships the gods`, `cursed_by an old witch`). Without this flag, the extractor's concrete-rate filter rejects these patterns even though they're valid edges to category-nodes.

**3. Sentence scanner**
- Sentence-tokenize each session-log entry (regex on `. `, `! `, `? ` + paragraph breaks)
- For each sentence: find all entity matches + all verb matches
- Score: `≥2 entities + 1 known verb` → candidate; below that → ignore (skip pronoun-heavy and ambient sentences)
- Apply pattern templates from verb table; emit edge proposals
- `source.anchor = sentence` (full, verbatim) — auditable

**4. Confidence scoring (built-in, not retrofit)**
- HIGH: anchor matches verb table pattern exactly + both entities resolve to existing nodes
- MEDIUM: verb matches pattern but one entity doesn't resolve (auto-create candidate)
- LOW: ambiguous role assignment, or sentence has multiple entities and could parse multiple ways

**5. Apply UX**
- `--review` interactive mode (Phase 1 friction #3)
- Default behavior: `--auto-high` applies HIGH-confidence proposals automatically; MEDIUM go to review queue; LOW are dropped unless `--include-low`

### Estimated recall vs Phase 1 Haiku

| Class | Pattern-match recall |
|-------|---------------------|
| Clean SVO ("X V Y") | ~95% |
| SVO with prep object ("X V Y to Z") | ~85% (with templates) |
| Pronoun-mediated | ~10% (skipped, flagged) |
| Implicit / figurative | ~30% (only what's in the idiom table) |
| Cross-sentence | 0% (skipped) |
| **Overall** | **~50% recall, ~95% precision** |

The trade is real — ~half the volume of Phase 1 — but the *high-impact* class (introductions, meetings, named relationships) is preserved at near-100%, and precision is much higher. For a deterministic, LLM-agnostic, free tool, that's the right trade.

**Implementation cost:** ~half-day, ~250 LOC + the existing YAML verb table.

---

## Phase 3 — Hybrid (pattern-first, LLM-fallback)

For users who *do* have LLM budget and want the recall:

```
campaign_graph.py extract --hybrid
```

1. Run Phase 2 deterministic extractor first
2. Identify sentences that contain entities but produced no edge (likely complex grammar / pronouns)
3. Send only those sentences to Haiku for second-pass extraction
4. Merge results, dedupe

**Cost benefit:** for a typical campaign, deterministic catches ~50% of edges at $0 cost. The remaining 50% go through Haiku at maybe 1/4 the input volume of pure Phase 1. Net: half the cost for full recall.

Defer until Phase 2 has soaked across multiple campaigns and the recall gap is measurable in real DM use.

---

## Schema additions for Phase 2

These three fields are required for Phase 2 to be a meaningful upgrade over Phase 1:

### 1. `closed` field on state edges

State edges represent ongoing claims that can end. When they end, write the closing anchor; don't delete the edge.

```yaml
- source: {file: session-log.md, session: s10, anchor: "Pol delivers the report..."}
  edge_type: serves
  lifetime: state
  closed: {session: s21, anchor: "flipped on silence"}
```

The default `scene-context` query filters to `closed == null` for current-state queries. Replays and `subgraph` queries show full history. Event edges (lifetime: event) ignore `closed` entirely — they're permanent.

### 2. `lifetime` column in the verb table

Three values:
- **`event`** — immutable past occurrence (`killed`, `attacked`, `told`, `gave`). Permanent in the graph.
- **`state`** — current ongoing relationship (`serves`, `imprisoned`, `member_of`). Can be ended via `closed`.
- **`dispositional`** — current emotional/political stance that drifts over time (`wary_of`, `fears`, `committed_to`). Can be reaffirmed (later assertion in the same direction strengthens) or contradicted (assertion in opposite direction supersedes).

The extractor uses `lifetime` to decide whether to emit a `closed`-eligible state, a permanent event, or a dispositional edge subject to drift detection.

### 3. `category_object_ok` flag in verb table

For state-verbs whose object is often categorical (`possessed_by a ghost`, `worships the gods`, `cursed_by an old witch`), the extractor should emit an edge to a category-node — a node with `category_node: true` that displays as "a ghost (unnamed)" in `scene-context`.

Without this flag, the concrete-rate filter rejects these patterns despite their narrative value.

---

## Retcon handling (deferred to Phase 2.5)

When canon explicitly contradicts an earlier edge, two options:
- **Soft retcon** — close the old edge, add a new one. The closed edge stays in the audit trail.
- **Hard retcon** — mark the old edge as wrong (e.g. it was extracted from a since-corrected session-log). New `superseded_by` field links to the corrected edge.

In practice, ~3% of state edges over a long campaign get superseded. Most retcons are soft (a relationship changed) rather than hard (the original extraction was wrong). Soft retcons need only `closed`; hard retcons need `superseded_by`.

Recommendation: ship Phase 2 with `closed` only. Add `superseded_by` in Phase 2.5 when the first real hard retcon shows up.

---

## Open design questions

- **Deceased / offscreen entities** — should the graph track relationships to characters who are dead or off-screen? Argument for: they influence ongoing narrative ("the water knew who was aboard"). Argument against: they'll never appear in `--present` queries. **Recommendation:** allow `npc` nodes with `tags: [deceased, offscreen]`; participate in `subgraph` queries but not `scene-context`.
- **Abstract groupings** ("the protection network", "the hunters") — under-specified factions deliberately left unnamed in canon. **Recommendation:** create as faction nodes with placeholder ID (`faction_protection_network_v1`) and `tags: [unnamed_in_canon]`; surface in graph but never reveal the placeholder name to players until canon names them.
- **Source-anchor verification at apply time** — already proposed (friction #5). High priority for any Phase 1 → Phase 2 transition.

---

## Promotion gate

`/dnd graph` stays in the sandbox in this release. Promotion to canonical requires:

1. Phase 2 deterministic extractor merged + tested across ≥3 live campaigns.
2. `closed` + `lifetime` schema land in `campaign_graph.py`.
3. `--review` interactive mode shipped (friction #3).
4. Source-anchor verification at apply time (friction #5).
5. `scene-context` query confirmed working with category-nodes (`category_object_ok`).

When those land, `campaign_graph.py` ships in the canonical skill and the docs under `docs/research/graph/` move to the user-facing docs. Until then, the graph remains opt-in and clearly marked as experimental.
