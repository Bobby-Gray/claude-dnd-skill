# Graph Verb-Table — Gap Categories Audit (post-saturation review)

**Date:** 2026-04-30
**Predecessor:** `1777586883_graph_verb_research_review.md` (142-proposal Phase 1 review)
**Trigger:** Pass 2 Reddit corpus showed diminishing returns (462 extractions → ~13 promotion-worthy verbs). Before locking the verb table for Phase 2 implementation, audit whether entire **categories** of relationships are missing from the seed (not just individual verb forms).

---

## Method

Two-step process:

1. **Taxonomy build** — derived a 21-category taxonomy of NPC↔NPC and PC↔NPC relationships from a-priori reasoning + scan of established RPG-graph literature.
2. **Coverage map** — cross-referenced each category against `verb_table_seed.yaml` v0.4 inclusion + borderline lists.
3. **Targeted phrase queries** — for the highest-priority gaps, ran phrase-anchored Reddit search (new `--query` flag added to `external_corpus_collect.py`) against narrative subs (`r/dndstories`, `r/DnDBehindTheScreen`, `r/all`) to validate that the category surfaces in real corpus and to harvest verb-form variants.

---

## Coverage map

### ✅ Well-covered (≥3 inclusion verbs)

| Category | Seed verbs |
|---|---|
| Identity / knowledge | met, knows, recognized, witnessed, identified, encountered, has_history_with |
| Family (nuclear) | parent_of, sibling_of, married_to, family_of, carries_lineage_from |
| Authority / faction | serves, leads, commands, controls, governs, founded, member_of, allied_with, employs, works_for |
| Combat / violence (events) | killed, attacked, fight, hunts, hunted, assassinated, sabotaged, abducted, imprisoned, escaped_from, destroyed |
| Speech / communication | told, asked, said, suggested, accused, argued, confessed, shared, refused, interrupted, blocked |
| Movement / location | based_at, located_at, resides_at, arrived_at, stayed_at, visited, neighbors, sought, traveled_with, explored |
| Manipulation / deception | lured, convinced, impersonated, sabotaged, accused |
| Money / transaction | possesses, pays, employs, gave, offered |

### ⚠️ Thin or missing categories (priority-ordered)

| # | Category | Current coverage | Gap verbs | Priority |
|---|---|---|---|---|
| **A** | **Death-state / undeath / resurrection** | none | `raised_from_dead`, `ghost_of`, `undead_form_of`, `soul_bound_to`, `resurrected_by` | **HIGH** |
| **B** | **Magical possession / vessel** | collapsed under `transformed_by` | `possessed_by`, `host_of`, `vessel_for`, `body_of`, `inhabited_by` | **HIGH** (active in horror-leaning campaigns where bodies are taken over) |
| **C** | **Oath / promise / pledge** | `committed_to` only (one-shot) | `swore_oath_to`, `pledged_to`, `vowed_to`, `broken_vow_to`, `indebted_to` | **HIGH** |
| **D** | **Future-tense planned** | `prepares_for` only | `plans_to`, `intends_to`, `scheduled_to`, `will_meet`, `set_to` | **HIGH** |
| **E** | **Romantic-extended** | `kissed`, `flirted`, `married_to` | `in_love_with`, `fell_in_love_with`, `engaged_to`, `betrothed_to`, `lover_of`, `courted`, `divorced_from`, `cheating_on` | **MEDIUM-HIGH** |
| **F** | **Rivalry / enmity (state)** | event verbs only | `sworn_enemy_of`, `rival_of`, `nemesis_of`, `blood_feud_with` | **MEDIUM** |
| **G** | **Religious devotion** | none | `worships`, `devoted_to`, `cleric_of`, `prays_to`, `blessed_by`, `cursed_by_god` | **MEDIUM** |
| **H** | **Sponsorship / patronage** | none | `patron_of`, `backed_by`, `funded_by`, `sponsored_by` | **MEDIUM** |
| **I** | **Disposition trend (temporal)** | none | `warming_to`, `growing_distant_from`, `lost_trust_in`, `fell_out_with` | **LOW-MEDIUM** |
| **J** | **Reputation / rumor** | `accused`, `wary_of` | `rumored_to_be`, `wanted_for`, `suspected_of`, `framed_for` | **LOW** |
| **K** | **Espionage / intelligence (state)** | `watches`, `surveils` borderline | `spies_on`, `informant_of`, `infiltrated`, `mole_in` | **LOW-MEDIUM** |
| **L** | **Healing / medical** | none | `healed`, `treated`, `cured`, `poisoned`, `infected_by` | **LOW** |
| **M** | **Inheritance** | partial via `carries_lineage_from` | `heir_to`, `inherits_from`, `disinherited_by` | **LOW** |
| **N** | **Body-mark / scar** | none | `scarred_by`, `branded_by`, `marked_by` | **LOW** |
| **O** | **Service-rendered (one-time)** | partial via `helped`, `saved` | `rescued`, `escorted`, `ferried`, `fed`, `hosted` | **LOW** |
| **P** | **Pregnancy / parentage-pending** | none | `expecting_child_with`, `conceived_with` | **LOW** |
| **Q** | **Agreement / contract** | `committed_to`, `allied_with` partial | `signed_pact_with`, `contracted_with`, `broke_agreement_with` | **LOW** |

---

## Targeted-query results (categories A-F)

Five phrase-anchored Reddit searches against narrative subs. Total corpus: 102 posts × ~250+ words = ~30k words of D&D narrative, anchored on the gap categories. Verb-form frequency by category:

| Category | Top verb form | Count | Other variants |
|---|---|---|---|
| **B** Possession | `possessed by` | **27** | `inhabited by` (3), `controlled by` (2) |
| **E** Romance | `in love with` | **28** | `fell in love` (8), `wed` (11 in own corpus) |
| **C** Oath | `swore an oath` | **6** | `oath to` (1) |
| **F** Rivalry | `sworn enemy` | **4** | `sworn enemies` (3), `rival` (2) |
| **D** Future-tense | sparse | <5 each | `plans to`, `set to`, `going to find` — confirms hypothesis: **future-tense verbs do not surface in past-tense story corpora**. To harvest these, would need DM session-prep documents (not story posts) or transcripts. |

### Concrete-relationship grounding (sample sentences, anchor-quotable)

**B / possessed_by — 100% concrete in 5/5 sampled:**
> "Herb is **possessed by** some entity..."
> "the baby was **possessed by** the haunted spirits of the murdered villagers"
> "the fighter was **possessed by** a ghost and attacked us"
> "a bag of holding **possessed by** the wizard"
> "the father was **possessed by** the lawful god"

**E / in_love_with — 100% concrete in 5/5 sampled:**
> "deeply **in love with** each other"
> "fall **in love with** him, and convince Dashing..."
> "made all of us **fall in love with** him"
> "the half orc **falls madly in love with** elf girl"
> "Ron finds the mermaid and **fall instantly in love with** her"

**C / swore_oath_to — concrete in all 6 hits:**
> "**swore an oath** to..." (Paladin oath formulations dominant)

**F / sworn_enemy_of — concrete in 4/4 sampled:**
> "his **sworn enemies**" / "their **sworn enemy**" / "**sworn enemy** of the cult" / "his **sworn enemy** the order of..."

---

## Recommended verb-table additions (Phase 2 lock-in)

**Tier 1 — promote to inclusion immediately** (multi-source ≥10 hits + 100% concrete in samples):

```yaml
- verb_forms: [possessed by, possesses (when entity-target), inhabited by, inhabits, hosts]
  edge_type: possessed_by
  symmetric: false
  confidence: high
  notes: |
    Distinct from `possesses` (item ownership) — pattern requires animate-entity
    object. Frequently REVERSIBLE state. Often surfaces with "by some entity",
    "by a spirit", "by a ghost", "by a god". NOT to be conflated with `transformed_by`
    (which implies physical/permanent change).

- verb_forms: [in love with, loves, fell in love with, fall in love with, fallen for]
  edge_type: in_love_with
  symmetric: false  # asymmetric — unrequited love is common
  confidence: high
  notes: |
    Distinct from `married_to` and `flirted`. Captures romantic *state* not *event*.
    28+ hits across r/dndstories. Asymmetric is the default — most love declarations
    in narrative are one-sided until explicitly mutual.
```

**Tier 2 — promote to inclusion** (≥5 hits + concrete):

```yaml
- verb_forms: [swore an oath to, swore to, oath to, pledged to, vowed to]
  edge_type: swore_oath_to
  symmetric: false
  confidence: high
  notes: |
    Distinct from `committed_to` (one-shot commitment) and `allied_with` (faction).
    Implies a binding commitment with consequence on breach.
    Common Paladin/clergy/political-fealty register.

- verb_forms: [sworn enemy of, sworn enemies of, nemesis of, archnemesis of]
  edge_type: sworn_enemy_of
  symmetric: true  # mutual enmity is the default
  confidence: high
  notes: |
    State, not event — distinct from `attacked` / `fought` (which are events).
    Captures persistent hostile relationship that frames future encounters.
```

**Tier 3 — add as borderline** (single-source or low-volume but high-value):

```yaml
- verb_forms: [raised from the dead, resurrected, brought back, returned from death]
  edge_type: resurrected
  symmetric: false
  confidence: medium
  notes: |
    D&D-specific. The agent (cleric/druid/divine source) → patient direction.
    Often accompanied by mechanical context (Revivify/Raise Dead/True Resurrection).

- verb_forms: [worships, devoted to, prays to, cleric of, paladin of]
  edge_type: worships
  symmetric: false
  confidence: medium
  notes: |
    Religious-devotion state. Target may be deity/saint/icon. Worth distinguishing
    from `serves` (which implies institutional authority).

- verb_forms: [patron of, backed by, sponsored by, funded by, bankrolls]
  edge_type: sponsored_by
  symmetric: false  # X is patron of Y; reverse direction in extraction
  confidence: medium
  notes: |
    Asymmetric power relationship — patron has leverage, client has obligation.
    Important for political/factional graphs.

- verb_forms: [betrothed to, engaged to, fiancé of, fiancée of, promised to wed]
  edge_type: betrothed_to
  symmetric: true
  confidence: medium
  notes: |
    Pre-marriage state. Can be broken (broken_engagement). Distinct from
    `married_to` and `in_love_with`.
```

**Tier 4 — defer to Phase 2.5** (low corpus support, future research):

- Future-tense planned (`plans_to`, `intends_to`) — needs DM session-prep corpus, not story posts. Reddit narrative corpus is the wrong source.
- Disposition-trend verbs (`warming_to`, `growing_distant_from`) — extracted at extreme rarity; possibly LLM-fallback territory.
- Healing / medical verbs — under-represented in horror/violence-skewed corpora.
- Body-mark / scar verbs — important for "the character with the scar from the dragon" pattern but rare.
- Pregnancy / parentage-pending — 0 hits; rare in narrative posts; high-quality when present.

---

## Source-corpus hypothesis update

The Reddit corpus skews toward **past-tense narrative** ("here's what happened in our session") and **horror/conflict content** (rpghorrorstories is a major source). This systematically under-samples:

1. **Future-tense verbs** (planning language) — pre-session content
2. **Religious / devotional verbs** — pantheon / lore / worldbuilding content
3. **Disposition-trend verbs** — character-arc content over multiple sessions
4. **Healing / medical verbs** — "we healed everyone and rested" is mundane/skipped
5. **Romantic-state verbs** (vs. romantic-event verbs like "kissed") — players narrate events, not states

For the 5 categories where the gap is *real* (A, B, C, E, F), the targeted queries succeeded — the verb forms exist, the patterns are concrete, the sample sentences are anchorable. **These should be promoted in v0.5.**

For the 5 categories where the gap is *real but corpus-resistant* (D, G, I, L, P), Phase 2.5 should explore alternative corpus sources:
- **Published adventure books** (already in corpus via PDFs — re-scan for these specific patterns)
- **r/DnDLore**, **r/worldbuilding** (D&D flair)
- **Player handbooks / DMG / Xanathar's** for canonical phrasing
- DM session-prep documents (offline, individual-DM)

---

## Recommendations

1. **Lock v0.5 of the verb table** with Tier 1+2 promotions (4 new edge types: `possessed_by`, `in_love_with`, `swore_oath_to`, `sworn_enemy_of`).
2. **Add Tier 3 to borderline** with explicit `LLM-fallback ok` annotation (`resurrected`, `worships`, `sponsored_by`, `betrothed_to`).
3. **Defer Tier 4 to Phase 2.5** — document in plan but don't block Phase 2 implementation.
4. **Phase 2 extractor must handle:**
   - **Asymmetric vs. symmetric** at the verb level (current schema has this; ensure all new entries set it correctly).
   - **State vs. event distinction** — `sworn_enemy_of` is a state; `attacked` is an event. Both use `referred_to` source-anchor pattern but different graph semantics (states persist; events have timestamps).
   - **Reversible vs. permanent** — `possessed_by` can end (exorcism); `killed` cannot. May want a `reversible: true|false` field on edge_type definitions.

---

## Open follow-ups

1. **Source-anchor for state-verbs.** When `sworn_enemy_of` is extracted, the anchor is the verb-phrase ("his sworn enemies the cult"). But state-verbs may be REPEATEDLY ASSERTED across sessions — first assertion sets the edge, later ones confirm. Should there be an `assertions: [list of anchors]` field for states, or just keep first-assertion?
2. **Reversibility schema.** If `possessed_by` ends via exorcism, how does the graph encode the transition? Current model has `extract` and `extract-apply` only; need `extract-close` for state-end events.
3. **Future-tense category** is the most interesting because it's where graph value is HIGHEST (DM planning) but corpus value is LOWEST. This is a known limitation; consider whether Phase 2.5 should source from session-prep docs directly.

---

## Appendix — extractor-vs-grep mismatch (post-run finding)

Ran the Haiku-based `external_corpus_extract.py` over the 32-post first batch (5 gap-category corpora). Result: **only 1 of the 5 gap categories was surfaced by the extractor at all** (`possessed`, count 3, **0% concrete**) — despite manual phrase-grep finding 27+ "possessed by" occurrences, 28 "in love with", 6 "swore an oath", etc. across the same posts.

This is a real signal about the **extractor's concrete-rate filter**:

The current extractor judges an extraction "concrete" only when both entities are uniquely-named (e.g. "[NPC_A] → [NPC_B]"). For state-verbs in narrative posts, the **object is frequently a category rather than a named individual**:

- "the fighter was **possessed by a ghost**" — "a ghost" is categorical
- "the baby was **possessed by the haunted spirits of the murdered villagers**" — pluralized, no name
- "the half orc **falls madly in love with elf girl**" — pseudonymized PCs, no name
- "their **sworn enemy the order of the black lily**" — faction, possibly already a node but anchored by definite article

These are still **valid graph edges** for DM purposes — knowing that a character was possessed by *something*, even unnamed, is load-bearing context. But the current extractor rejects them as abstract.

**Implication:** the Phase 2 deterministic extractor should treat these differently from Phase 1 Haiku:

1. **Don't gate state-verbs on "concrete" subject AND object.** A state-verb whose object is a CATEGORY (with `the` or `a` article + noun) should emit an edge to a category-node (e.g. `possessed_by → a:spirit`).
2. **Add `category_node: true` flag** for nodes that aren't uniquely-named entities. These display differently in `scene-context` ("possessed by a spirit (unnamed)").
3. **Re-classify "abstract" rejections from Phase 1 corpus** — a portion of them were probably category-node edges that should have been emitted, not rejections.

This was discovered specifically because the gap-category scrapes targeted state-verbs with frequently-categorical objects. Past corpus passes (which ranked verbs by "concrete rate") systematically under-counted these patterns.

**Recommendation:** before locking the verb table v0.5, add a `category_object_ok: true` flag to:
- `possessed_by`
- `worships`  (object often a god/deity name, but treat as category-node)
- `cleric_of` (same)
- `cursed_by`  (object often "an old witch", "the gods", "a demon")
- `fears` (already in borderline; same applies)
- `flagged_offlimits` (target may be a faction, not a person)

Edges to category-nodes should be retained, not filtered.
