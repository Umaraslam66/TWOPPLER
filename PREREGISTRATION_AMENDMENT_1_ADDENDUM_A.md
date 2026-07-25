# Addendum A to Amendment 1 — Stage 1E bar lock

**STATUS: ADOPTED 2026-07-25 with the two owner-required edits applied
(C2 information-source framing; C3 own-arm definition). In force as of this
commit. The confirm split may now be drawn; the confirm RUN launches only on
a separate explicit owner go (production queue).**

Basis: training-split pilot (n=150), overnight batch of 2026-07-24/25
(results/overnight_stage1e.md; five experiments, training/derivation data
only), and the decoding re-scoring (results/rescore_ev_vs_argmax.md). The
confirm split has never been drawn or touched.

## A. Frozen design of the Stage 1E confirm run

- **Split:** n=1,000 persons, seed 46, drawn from the cleaned RIASEC pool
  after excluding (i) all 720 previously used persons and (ii) the 2,000
  derivation-split ids in results/overnight_exp2/derivation_ids.json.
  The derivation ids are not visible to the automatic used-ids scan and MUST
  be excluded by explicitly loading that file; the draw script must print
  both exclusion counts.
- **Arms (5):**
  1. Baseline: demographics only.
  2. Random order: per-person seeded reveal order.
  3. Fixed order: the frozen derivation-split order (greedy ridge on n=2,000,
     seed 45; first 20 items: A3 E5 S5 A5 A2 C1 C2 S7 E7 A6 A7 I1 I8 S6 E1
     S2 I2 S4 R2 C4; full 48-item list in results/overnight_exp2/).
  4. Adaptive: EV-variance uncertainty scorer + seeded random tie-break
     (SHA-256 seeding scheme), exactly the EXP1b configuration — elicitation
     wording unchanged from the pilot (the 0.05-grid variant is NOT adopted;
     it was flat-to-worse for selection and untested in combination with the
     EV-variance scorer).
  5. Imposter: random-person donor profile mirroring the random arm's
     reveals, per Amendment A1. Declared scope note: this random-person
     imposter measures generic-profile harm; Stage 2's same-domain imposter
     is a different construct and its results must not be conflated with
     this one. (EXP5 finding on record: imposter harm is insensitive to
     donor similarity, p≈0.9.)
- **Elicitation/scoring:** v2 distribution elicitation, temperature 0;
  MAE with expected-value decoding as the primary number; checkpoints
  k ∈ {1, 2, 4, 8, 12, 16, 20}.
- **Estimated cost:** 11–14 node-hours (scaling the pilot's measured
  per-person cost by 1,000/150). Logged per arm.

## B. Confirmatory bars (frozen on approval)

- **C1 — PRIMARY (adaptive value):** adaptive − random MAE lift at k=12 > 0,
  paired t p < .05 across persons. Same contrast at k=20 is SECONDARY.
  Power note: the pilot-sized effect (~+0.02, p=.029 at n=150) has >95%
  power at n=1,000.
- **C2 — SECONDARY confirmatory (adaptive vs static script):** adaptive vs
  fixed at k=12 and k=20. Pre-written readings, equal prominence:
  - adaptive > fixed (p < .05): uncertainty-guided ordering adds value
    beyond any static script.
  - fixed >= adaptive: a well-chosen static questionnaire suffices at these
    budgets — this is the honest headline, not a failure to report.
  - Pre-registered cost framing: the adaptive arm spends ~5–12x the
    per-person LLM compute at interview time; the fixed order costs one
    offline derivation. Both currencies are always reported together.
  - Information-source framing (owner-required, verbatim): "This contrast
    compares a population-optimized static questionnaire (derived from
    2,000 persons' observed outcomes) against individually-adaptive
    selection that uses no outcome data. They consume different
    information: fixed-order encodes population history; adaptive
    personalizes per respondent. A fixed >= adaptive result therefore
    means historical outcome data suffices at these budgets — not that
    personalization is worthless in settings without such history (cold
    start, new domains)."
- **C3 — grounding (per Amendment A1):** at k=20, own − baseline > 0 AND
  own − imposter > 0, each paired p < .05. Own-arm definition
  (owner-required): own = the random-order arm (matching the imposter arm's
  mirrored reveal schedule). Both C3 contrasts use it; the adaptive and
  fixed arms are never substituted.
- **DECODING ROBUSTNESS (binding):** every confirmatory contrast must hold
  in direction under argmax decoding of the same distributions. All lifts
  are reported under both decodings, always beside both arms' raw MAEs.
  Rationale: EV decoding shrinks variance and can inflate lift by damaging
  the hedging baseline (results/rescore_ev_vs_argmax.md).
- **Multiplicity:** C1 at k=12 alone carries the adaptive headline. Every
  other number is labeled secondary or descriptive. Curve shapes
  (saturation points, budget-recovery fractions) are descriptive.

## C. Pre-declared null interpretations

- C1 null: item order does not matter at these budgets on this corpus;
  the elicitation-budget curve (EXP4 shape) is the deliverable.
- C3 own−imposter null or negative at confirm scale: the negative-transfer
  observation from the pilot did not replicate; report as such.

## D. 16PF replication — deferred to Addendum B (flagged deviation)

Amendment A6 said 16PF specifics would be locked "in the same addendum."
Locking them blind risks a repeat of the cross-scale anchoring surprise.
Deviation, submitted for approval here: a small CPU-only data recon of the
16PF dataset (item scales, factor structure, usable respondent counts)
precedes a separate Addendum B that locks the 16PF seed pool, target
domain, and splits before any 16PF run.

## E. Reporting-rule additions (all stages, binding)

1. Every reported lift appears beside both arms' raw MAEs, under both
   decodings (extends Amendment A8).
2. Citation correction to PREREGISTRATION.md §1: the Park et al. paper
   (arXiv 2411.10109) was retitled in June 2026 to "LLM Agents Grounded in
   Self-Reports Enable General-Purpose Simulation of Individuals" with a
   revised 83–86% headline; the frozen text's citation is updated by this
   note without editing the frozen document.
3. Multi-target parsers must store example raw completions beside parse
   rates (an all-or-nothing parser makes truncation indistinguishable from
   format failure — EXP3 attempt-1 lesson).
