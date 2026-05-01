# Evaluating the Campaign Graph: A/B Replay Findings

**Status:** Phase 1 evaluation complete. Sandbox feature, not yet promoted to canonical skill.

## Background

The campaign-graph experiment is a sandbox feature that builds a typed-edge relationship graph alongside the markdown campaign files (`npcs.md`, `world.md`, `state.md`, `session-log*.md`). Each edge carries a `source` field with file + session + verbatim anchor — making every graph claim auditable against the canonical narrative.

The motivating hypothesis: **a structural graph alongside the markdown corpus reduces continuity errors** — situations where the DM voice contradicts an established relationship by treating known characters as fresh contacts.

This document reports on a controlled A/B replay study designed to measure that hypothesis directly.

---

## Method

A campaign session was frozen mid-turn at the moment a player asked a substantive question that required the DM to compose a multi-part NPC response involving three other characters — one to redirect away from, one to direct toward, and one to send the player to check on as an errand. The errand character is the relevant variable: in canon, that character is *already known to the player* (introduced them to the NPC in question several sessions earlier).

Two prompt conditions were tested:

| Condition | Context provided to the model |
|---|---|
| **baseline** | `state.md`, `npcs.md`, the focal NPC's full entry from `npcs-full.md`, current session narrative truncated at the player's input |
| **with-graph** | All of baseline + `scene-context` query output from the graph (39 active edges including the relevant introduction-chain edge with verbatim source anchor) |

A single Sonnet model was used for all generations. Three rounds of 10 baseline + 10 with-graph (60 generations total) were run under different prompt-shape variations to control for prompt-level effects.

Each output was scored on:
- **Gap-mode language** — fresh-introduction phrasing applied to the already-known character ("tell him I sent you" / "use my name" / "introduce yourself")
- **Explicit acknowledgment** — language that surfaces the existing relationship ("you know him", "go back to him", "the debt's clear", "we have a working relationship")
- **Other compliance** — does the response correctly redirect, mention all expected characters, etc.

---

## Results

### Headline: gap-mode language never reproduced

**Across all 60 generations in 3 rounds × 2 conditions, the original gap-mode language appeared 0 times.**

The well-prompted model — given the focal NPC's full entry from `npcs-full.md` (which contains a *Knows / Owes / Fears* relationship list explicitly naming the introducer character) — does not produce fresh-introduction framing for an already-known character.

### Round 2 — sanitized, no errand prompt

When the prompt did not explicitly direct the NPC to give the errand:

| Metric | Baseline | With-graph |
|---|---|---|
| Errand character mentioned at all | 1/10 | 0/10 |
| Other-character redirects correct | 9/10 | 9/10 |

The model rarely brings up the third character on its own. The gap occurred in production *because the DM volunteered the errand* — without that prompt, the model has no reason to surface the character.

### Round 3 — sanitized + explicit errand prompt (closest to original failure conditions)

When the prompt explicitly required the NPC to give the errand:

| Metric | Baseline | With-graph |
|---|---|---|
| Gap-mode language | 0/10 | 0/10 |
| Explicit acknowledgment language | 1/10 | 2/10 |
| Errand character handled correctly | 10/10 | 10/10 |
| Other-character redirect compliance | 6/10 | 9/10 |
| Avg word count | 278 | 301 |

**Notable signal-strength gap:** the with-graph condition correctly redirected away from the dangerous-to-meet character in 9/10 runs vs 6/10 in baseline (4 baseline runs failed to mention the redirect at all, despite the prompt requirement). The graph's `flagged_offlimits` edge appears to be a sharper instruction than equivalent prose framing.

### Variance characterization

The 60 outputs cluster into three response patterns:

1. **Neutral simple-naming** (~70%) — character-name + location + state, without explicit acknowledgment but also without fresh-introduction framing
2. **Implicit acknowledgment** (~20%) — phrasing that presupposes the player already knows the character ("you know where it is", "that's not him")
3. **Explicit relationship surfacing** (~10%, biased toward with-graph) — naming the specific edge ("we have a working relationship", "the debt's clear", "since the Chart")

Within-condition variance is significant — the same setup produces different framings each run. The graph context biases the model toward pattern 3 about 1.5–2× more often than baseline.

---

## Sample outputs (Round 3)

### Baseline — neutral simple-naming
> "[errand-NPC]. His chandlery, [the docks-quarter]. He hasn't been to his usual card game in two weeks. Hasn't sent word."

### Baseline — implicit acknowledgment
> "Stop by [errand-NPC]'s shop. [the docks-quarter]. **You know where it is.** He's been quiet. Two weeks, no word."

### With-graph — implicit acknowledgment
> "He's been quiet. Two weeks. **He doesn't go quiet.** I'm not asking you to press him. Just walk in. Buy something."

### With-graph — explicit relationship surfacing (rare, only seen in with-graph)
> "[errand-NPC]. His chandlery, in [the docks-quarter]. He's been quiet for two weeks." The gap before the next sentence is a fraction longer than usual. "**We have a working relationship. He should have surfaced by now.**" She doesn't explain what *surfaced* means. She doesn't explain what *working relationship* means. **Anyone who knew them would fill in both.**

The last example is the clearest demonstration of graph-context impact: the model explicitly frames the character as known to both speakers, with the meta-narration hinting at shared history.

---

## Interpretation

The hypothesis-as-stated — *"the graph prevents continuity gaps"* — is unfalsifiable in this experiment because the original gap doesn't reproduce when `npcs-full.md` is in fresh-prompt context. The relationship facts encoded in the graph are also encoded in the *Knows / Owes / Fears* sections of `npcs-full.md`, and the model picks them up from there.

What the experiment actually measured:

| Question | Answer |
|---|---|
| Does the model reproduce the original gap-mode framing on a fresh prompt? | **No** — 0/60 runs |
| Does the graph add explicit relationship-surfacing language? | **Yes, marginally** — ~10% of runs vs ~5% baseline |
| Does the graph improve compliance with structural directives (redirects, off-limits flagging)? | **Yes** — 9/10 vs 6/10 in the strongest signal |

The implication is that the graph's primary value is **not** first-turn correctness on fresh prompts — it's **mid-session context preservation**. When prompts are fresh and `npcs-full.md` is in context, relationship facts come from there. The original production gap occurred mid-session, after context compaction had likely stripped `npcs-full.md`. In that scenario the much-smaller graph subgraph (a few hundred tokens vs many thousands for `npcs-full.md`) is the cheaper representation of the same facts.

---

## Implications for the graph design

1. **`scene-context` as a load-time inject is the right architecture.** Confirmed by the redirect-compliance signal — the graph's structural edges (`flagged_offlimits`, `referred_to_sorn`) come through more reliably than the equivalent prose.
2. **Source-anchor field is load-bearing for trust.** Every extracted edge points back to a verbatim phrase in canonical files. This makes the graph auditable; bad extractions are catchable by anchor-not-found. (See the parallel verb-table research that produced an 85% precision floor on Haiku-extracted edges — and confirmed ~0% true hallucination rate when paraphrase tolerance was applied.)
3. **The graph is most valuable in long-context sessions** where `npcs-full.md` is no longer fully in scope. Fresh prompts already have the structural facts; compacted prompts don't.
4. **Variance within conditions is significant.** Same setup produces materially different framings each run. The graph nudges distribution toward more-explicit relationship surfacing but does not eliminate variance — and shouldn't, since narrative-DM voice should remain varied.

---

## Replication

The experiment harness is reproducible:

```bash
python3 experiment_replay.py --n 10 --parallel 4                  # round 1
python3 experiment_replay.py --n 10 --parallel 4 --sanitize       # round 2
python3 experiment_replay.py --n 10 --parallel 4 --sanitize \
                            --out-suffix=-prompted                  # round 3 (prompt also modified)
```

Each round writes one `.txt` per generation to `/tmp/replay-outputs/<condition>/run_NN.txt` and a JSON summary to `/tmp/replay-summary.json` with per-run scoring.

---

## What was *not* tested (open questions for future evaluation)

1. **Long-context drift** — does the graph prevent gaps when context has been compacted past the point where `npcs-full.md` is fully retained? This is the actual production failure-mode but requires multi-turn session simulation.
2. **Gap on novel relationship types not in the verb-table seed** — the graph here had a directly-relevant edge type. What about relationships the extractor missed?
3. **Graph staleness** — what happens when canon retcons an established relationship and the graph carries the prior fact?
4. **Cross-campaign portability** — does the verb table generalize across campaign settings, or does it drift toward whatever vocabulary the test campaign uses?
