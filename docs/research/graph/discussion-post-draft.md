# What we learned from a few weeks of trying to fix continuity gaps

*Draft for a GitHub Discussion post. Copy into the repo Discussions when ready.*

---

## What we were trying to figure out

If you've run a campaign past a dozen sessions, you've probably seen the moment we set out to fix. The DM is voicing an NPC. The player asks a question. The reply lands fine — until you read it again the next morning and realize the NPC just told the player to "go see the chandler, tell him I sent you," when the chandler is the person who introduced the player to that NPC three sessions ago.

This isn't a new problem, and it isn't unique to this skill. The continuity question — how an LLM-driven DM keeps a coherent picture of who-knows-whom across long-running campaigns — has been a running thread across the LLM-RPG community for as long as the community has existed. Every implementation we've seen has hit some version of it, and every implementation has tried something different in response.

In this project, [@ethros19](https://github.com/ethros19) (Ethan Piper) first flagged it in [issue #7](https://github.com/Bobby-Gray/claude-dnd-skill/issues/7) back in v1.4 days, and has been the most consistent voice keeping us honest about long-context failure modes since — much of what's followed traces directly to that thread. We've shipped a few different methodologies since then:

- The **compaction-drift fix** — a hard rule in `SKILL.md` that the DM must re-read the source for any recap or status claim, never trust the compacted impression.
- The **Live State Flags block** in `state.md` — cover, faction stances, NPC dispositions in compact key-value form. Designed to be the *first* thing re-read; cheap to keep in scope.
- **Targeted Reads.** A modular set of "smallest section that covers the claim" directives — read only that NPC's entry in `npcs-full.md`, not the whole file; read `state.md → ## Continuity Archive` first, escalate to `session-log.md` only if needed.

Each one held the line at the scale of campaigns we were running at the time. They're all still in the skill; we haven't replaced any of them. They work.

Campaigns kept getting longer though. Twenty sessions deep into a single thread, you start hitting cases the previous tools weren't designed to catch — relationships established once, never restated, that everyone-in-canon would treat as common knowledge but the model can no longer see. The compacted facts are *summaries* of summaries by then. The relationship-genealogy detail isn't in any of them.

The hypothesis that started this thread was simple: **what if a structural relationship graph, alongside the markdown files, surfaced these facts cheaply enough to keep them in scope when the full entries are no longer available?**

A few weeks of work later, we have an answer. It's not exactly the answer we expected, and we think it scales meaningfully higher than the previous tools.

## What we built

A small typed-edge graph. Each edge is `{from, to, type, source: {file, session, anchor}}` where the anchor is a verbatim quote from the canon line that asserts the relationship. The Phase 1 extractor was a Haiku-backed pass over `session-log.md`; the apply step was human-in-the-loop with a `--pick` flag. The graph runs as a sandbox tool — opt-in per campaign, no impact on existing workflow.

We trialed it on a campaign that had produced the original gap. The graph recovered the three edges that would have prevented it, all with verbatim source anchors. Then we ran the actual experiment.

## What the experiment found

A controlled A/B replay against the moment the original gap occurred. The setup was frozen mid-turn at the player's input, then 60 Sonnet generations were run across three prompt-shape variations (10 baseline + 10 with-graph each round) to control for prompt-level effects.

The headline result was honestly surprising:

**Across 60 generations, in 3 rounds × 2 conditions, the original gap-mode language appeared zero times.**

The well-prompted Sonnet, given a fresh prompt with the full `npcs-full.md` entry in context, simply doesn't reproduce the gap. The relationship facts encoded in the graph are also encoded in the *Knows / Owes / Fears* sections of the NPC entry, and the model picks them up from there. The fresh-prompt model isn't the one that has the problem.

That meant the original failure-mode was a **mid-session context-loss artifact**, not a baseline model failure. By the time we (the DM) were deep in the session, the NPC's full entry had likely fallen out of context, and the graph subgraph — a few hundred tokens, vs. many thousand for `npcs-full.md` — would have been the cheaper representation of the same facts.

The hypothesis-as-stated was unfalsifiable in this experiment. But the experiment did measure something we weren't asking about:

**The graph improves compliance with structural directives at a clearly measurable rate.** With the prompt explicitly requiring the NPC to redirect the player away from a dangerous-to-meet character, the with-graph condition got the redirect right in 9/10 runs. Baseline got it right in 6/10 — four of the ten failed to mention the redirect at all, despite the prompt requirement. The graph's `flagged_offlimits` edge is a sharper instruction than equivalent prose framing.

The graph also nudges the model toward more **explicit relationship surfacing** ("we have a working relationship," "since we last spoke") about 1.5–2× more often than baseline. Same information, but the model frames it as already-shared history rather than neutral simple-naming. That's a quality lift even when both conditions are technically correct.

## What we changed our mind about

The graph is most valuable in long-context sessions, **not** first-turn correctness. When prompts are fresh and the NPC entry is in scope, the model is fine without the graph. When mid-session compaction strips the entry, the graph is the cheaper representation of the same facts. That repositions the whole feature: it's not a correctness fix, it's a **context-budget tool**.

The source-anchor field — the thing that makes the graph auditable — is more load-bearing than the relationships themselves. Every claim points back to a verbatim phrase. Bad extractions get caught by anchor-not-found. That's the architecture decision we're keepers of for the deterministic Phase 2 build.

## What we built besides the experiment

To prepare for Phase 2 (a deterministic verb-table extractor that doesn't need an LLM and ports to non-Claude tooling), we needed to know what verbs actually show up in real D&D narrative. That turned into a corpus-collection effort across:

- 7 live campaigns (the ones already running)
- 4 published adventures (extracted from PDFs)
- 280 Reddit narrative posts (r/DnDBehindTheScreen, r/dndstories, r/RolePlay, r/rpghorrorstories)

About **1,014 verb-bearing observations** across 14 sources. Saturated — pass 2 of the Reddit corpus added only ~13 promotion-worthy verbs to the ~45 from pass 1. We also ran a category-audit afterward to identify whole **classes** of relationships (death-state, magical possession, oath/promise, romantic-extended, future-tense planned) where the seed had gaps. Eight of those gaps got promoted to the v0.5 seed in this release.

## What ships next

`/dnd graph` lands in the canonical skill in v1.7 once the deterministic extractor and three schema fields (`closed`, `lifetime`, `category_object_ok`) are merged. Until then it stays sandbox-only — opt-in per campaign, behind a clear "experimental" marker.

If you're curious about any of this, the artifacts are under `docs/research/graph/`:

- **`ab-experiment-findings.md`** — the full experiment writeup with sample outputs and variance characterization
- **`verb-gap-categories.md`** — the gap-categories audit
- **`phase-2-3-plan.md`** — the design plan for the deterministic extractor

We'd be interested in hearing from anyone who's run into similar continuity-gap issues in their own campaigns, or who's tried other approaches to keeping relationship facts in scope across long sessions. The corpus is open, the methodology is reproducible, and Phase 2 is designed against findings, not assumptions.

A genuine thank you to [@ethros19](https://github.com/ethros19) (Ethan Piper) for raising the original issue and for the steady stream of long-campaign feedback since — the through-line from issue #7 to this release wouldn't exist without it. And thanks to everyone running campaigns deep enough to find the failure modes in the first place. Phase 2 is built on what those sessions actually broke.
