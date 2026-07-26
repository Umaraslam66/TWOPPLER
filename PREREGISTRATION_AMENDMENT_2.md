# Project DOPPLER — Pre-Registration Amendment 2

Status: **ADOPTED 2026-07-26 on explicit owner approval; committed at
adoption.** Drafted 2026-07-26; extended the same day with B7–B9 on owner
direction, and with B10 on the owner's instrument decision after the two
dev pilots. **No confirmatory Stage 2 twin construction or evaluation data
exists at adoption** — the only Stage 2 runs are the two dev-subject
pilots cited in B10, which touch no confirmatory subject. Stage 1 and
Stage 1E are closed (`results/stage1e_findings.md`, commit `a4b9f1b`).
Where this amendment conflicts with PREREGISTRATION.md or Amendment 1,
this amendment governs. Everything not amended stays frozen.

On 2026-07-26 the owner approved every value drafted as [PROPOSED] — the
classifier trust bar, the H6 budget-matching tolerance, the H6 interesting
bar, the dev-subject composition — and the H6 subject-count branch, all
exactly as drafted. They are marked **[APPROVED 2026-07-26]** below and
freeze when this amendment is adopted.

## B1. Scope statement imported from Stage 1E

Stage 1E's confirmed results — adaptive item selection indistinguishable
from random ordering (C1 null), and a population-derived fixed order beating
both at a tenth of the compute (C2) — were measured in one specific setting:
a **closed question pool** (48 fixed items) with **low-bandwidth answers**
(a single 1–7 rating per reveal), no conversation.

Their scope is exactly that setting. They license **no claim about follow-up
generation in open conversation** — where the question space is unbounded,
answers run to hundreds of words, and the interviewer's core move is to
reference and probe what the person just said. None of those features exist
in survey replay.

Corollary, binding on all write-ups: Stage 1E may not be cited as evidence
that "adaptive interviewing doesn't work." The defensible sentence is:
"adaptive selection over a fixed Likert item pool did not beat a
population-derived static order at budgets up to 20 items on one corpus."
Whether adaptivity has value in open conversation is untested and remains
this project's open question (H6 below is the first Stage 2 probe; Stage 3
H4 is the live test).

## B2. New pre-registered hypothesis H6 — follow-up value

**H6:** Within a subject's grounding transcripts, segments arising from
**follow-up chains** (host turns that reference the content of the guest's
previous answer) carry more twin fidelity per grounding token than
**scripted question-hop** (new-topic) segments, at matched token budget.

Motivation: Stage 1E showed that *choosing which fixed question to ask next*
adds nothing over a good static order. H6 asks a different question — whether
the *content produced by follow-up probing* is worth more per token than
content produced by topic-hopping. Depth versus breadth, measured on the
grounding side.

### Design

1. **Turn classification.** Every host turn in a subject's grounding
   transcripts is classified **FOLLOW-UP** or **NEW-TOPIC** by
   Gemma-4-31B-it under a **frozen rubric prompt**. FOLLOW-UP: the turn
   references or probes the content of the guest's preceding answer (asks
   to expand, questions a specific thing said, challenges it). NEW-TOPIC:
   the turn introduces material not derived from the preceding answer
   (prepared question, topic switch, segment transition). The rubric defines
   the boundary cases and forces a single label per turn. The final rubric
   text and its hash are frozen in the bar-lock addendum (B3).
2. **Classifier trust gate.** Before any confirmatory H6 arm is built, the
   owner spot-checks **≥ 100 classifications**, sampled across ≥ 10 subjects
   and balanced across the two labels. Trust bar **[APPROVED 2026-07-26]**: ≥ 85% raw
   agreement AND Cohen's kappa ≥ 0.6. Below bar → rubric is revised on dev
   subjects only and a fresh sample is re-checked; every iteration is
   documented. The classifier is not trusted, and no confirmatory H6 arm is
   built, until the gate passes.
3. **Segments and arms.** A segment is one host turn plus the guest's reply.
   Consecutive FOLLOW-UP segments form a chain with their root turn.
   Per subject, two grounding contexts are built at the **same token budget
   B**: **follow-up-rich** (segments drawn from follow-up chains, highest
   chain-density first) and **follow-up-poor** (NEW-TOPIC segments only).
   Selection is a **deterministic seeded rule — no LLM chooses segments in
   either arm.** Both arms draw from the same eligible grounding interviews
   and present segments in chronological order. Budget matching: both arms
   filled to within ±5% of B **[APPROVED 2026-07-26]**.
4. **Outcome.** Held-out forced-choice fidelity on the chronologically last
   interview, scored by the Stage 2 harness with all Amendment 1 controls
   (A4 distractor matching, entity-stripped variant, adversarial filter).
5. **Models.** Per A3: primary Gemma-4-31B-it + v2; robustness
   gemini-3.5-flash-lite + v2.

### Pre-written readings (equal prominence)

- **H6 positive:** depth-per-token beats breadth — follow-up material is
  where interviewer value concentrates. This is the evidence that adaptive
  follow-up is where interviewer value lives, and it motivates Stage 3's
  adaptive interviewer.
- **H6 null:** segment type does not matter at these budgets — breadth
  suffices, and grounding value is carried by the volume of the subject's
  own speech rather than by how it was elicited. This is a publishable
  finding with the same prominence.

### Declared confound (stated in every write-up)

Follow-up chains occur where the host *chose* to drill, so drilled topics
may be more informative regardless of the follow-up structure. H6 therefore
tests the value of follow-up **content**, not the causal effect of asking
follow-ups. Likewise H6 is a grounding-side result: a positive H6 says where
value sits in existing transcripts; it does not establish that a live
adaptive interviewer beats a script (that is Stage 3 H4). Position- or
topic-matched re-analyses may be reported, labelled exploratory.

## B3. H6 bars and analysis rules

- Unit of analysis: subject. Test: paired over subjects, follow-up-rich
  minus follow-up-poor forced-choice accuracy, identical test items in both
  arms.
- **Confirmatory bar:** mean paired difference > 0, p < .05, on the primary
  model. **Interesting bar [APPROVED 2026-07-26]:** ≥ +5 points accuracy
  (mirrors H2's magnitude bar).
- **Binding robustness checks** (Stage 1E lesson: a robustness check must be
  able to change the claim). A headline H6 claim requires direction
  preserved under ALL of: (a) the robustness model (A3), (b) the
  adversarial-filtered scoring variant (A4.3), (c) the entity-stripped
  variant (A4.2). Any flip → the result is reported as variant-specific or
  model-specific, never as a headline.
- Both arms' raw accuracies are always printed beside the difference (watch
  which arm moves).
- Subject-count branch, mirroring A5 and decided solely by the count of
  H6-eligible confirmatory subjects: **≥ 80** → H6 confirmatory as above;
  **30–79** → exploratory (effect size + CI, no hypothesis-test claim);
  **< 30** → descriptive only.
- **Bar-lock addendum.** The numeric parameters — token budget(s) B, segment
  and chain definitions in final form, rich/poor selection thresholds,
  classifier rubric text + hash, trust-gate results, the flagged-turn
  threshold in B4.3 — are frozen in a dated addendum after the 5-subject
  pilot is reviewed by the owner and **before any confirmatory H6 scoring**.
  Confirmatory subjects are untouched by H6 machinery until that addendum is
  committed. (Same pattern as Amendment 1's A6 bar-lock.)
- Cost per arm (node-hours and API $) is logged and reported.

## B4. Exclusions

1. **Dev subjects.** Five pilot subjects are drawn by a deterministic seeded
   draw from the qualifying candidate pool (staff-filter reserve excluded),
   used for all pipeline development and rubric tuning, and **excluded from
   every confirmatory analysis of every Stage 2 hypothesis, permanently.**
   IDs, seed, and draw rule are recorded in `results/stage2_pilot/`.
   Composition **[APPROVED 2026-07-26]**: 3 with-Wikipedia + 2 long-tail, so
   the contamination meter is exercised on both kinds while sparing the tight
   long-tail supply.
2. **H6 eligibility.** A subject enters H6 only if both arms can be filled
   to budget B from their grounding transcripts (enough follow-up-rich AND
   enough follow-up-poor material). This is a mechanical rule applied before
   any fidelity scoring; excluded counts are reported. Subjects failing it
   remain in H1/H2.
3. **Classifier failures.** Host turns the classifier fails to label after
   2 retries are dropped from segment selection in both arms; per-subject
   drop rates are reported; subjects above a flagged-turn threshold
   (numeric value set at bar-lock) are analyzed separately.
4. **Reserve subjects.** Standing constraint restated: nothing that depends
   on staff-filter-reserve subjects proceeds until the owner's 20-subject
   spot-check clears them.

## B5. Relationship between H2 and H6

Separate contrasts, separate write-ups, **no shared headline**:

- **H2** holds content composition free and varies the *selection policy*
  (model-selected vs random segments) at matched budget.
- **H6** holds the selection policy fixed (deterministic rule, no LLM) and
  varies *content type* (follow-up-rich vs follow-up-poor) at matched
  budget.
- By construction they stay orthogonal: H6 arms never use model-selected
  segments; H2 arms never condition on the follow-up classifier.
- A positive H2 is not evidence for H6 and vice versa. If both are positive
  they are reported as two findings; no pooled or combined claim is made;
  any interaction analysis is exploratory.

## B6. Reporting

All original and Amendment 1 reporting rules stand (nulls at equal
prominence, per-claim provenance, cost logging, A1 imposter arms for all
fidelity reports — the H6 contrast itself is own-twin vs own-twin, so the
imposter arm attaches to the H1 reporting layer, not per H6 arm). On
adoption this amendment is committed alongside PREREGISTRATION.md and
Amendment 1, and an updated OSF snapshot including all three is prepared for
external timestamping (the OSF upload itself remains on the owner and is
pending).

## B7. New pre-registered hypothesis H7 — twin staleness (co-headline with H1)

Motivation. One open validation question for interview-grounded person-models
is unclaimed in the field: how fast does a twin decay as its grounding ages?
Answering it normally needs years of repeated panel waves, and commercial
builders have no incentive to publish decay curves. Our corpus carries years
of interview time-depth per subject for free. H7 is a new AXIS on machinery
that already exists — chronological splits, the A1 imposter arm, the
contamination meter — not a new pipeline.

**H7: a twin's fidelity declines as the staleness Δ between its grounding
material and the test interview grows.**

### Design

1. **Eligibility (mechanical, applied before any scoring):** subjects with
   ≥ 4 dated interview clusters spanning ≥ 2 years. Excluded counts reported.
2. **The sweep.** The test interview stays the subject's chronologically LAST
   interview — the same test set as H1, identical items at every cutoff. A
   grounding cutoff T restricts grounding to interviews dated ≤ T. Staleness
   Δ = date(test) − date(newest interview available under T). Δ is swept by
   moving T; within-subject where the chronology supports several cutoffs,
   so the same subject is compared to themself on identical items.
3. **Volume control.** At every T the grounding context is filled to the
   same token budget B, newest-first below the cutoff. Only the AGE of the
   grounding varies, never the amount. A cutoff at which B cannot be filled
   is excluded (counts reported).
4. **Outcome.** Forced-choice fidelity from the same Stage 2 harness with
   all Amendment 1 controls (A1 arms, A4 distractor controls) and the B8
   dual-level reporting rule. Models per A3: primary Gemma-4-31B-it + v2,
   robustness gemini-3.5-flash-lite + v2.
5. **Deliverable:** the fidelity-versus-Δ decay curve, per subject and
   pooled.

### Pre-declared killer statistic — the crossover point

At each Δ bin, the STALE true-person twin is compared against a FRESH
same-domain imposter twin: the A1 imposter pipeline, grounded on the donor's
interviews closest in time to the test date, same budget B. The **crossover
point** is the smallest Δ at which the fresh imposter twin matches or beats
the stale own twin — "a stranger's fresh twin beats your Δ-year-old twin."
It is pre-declared here as H7's headline statistic if it occurs inside the
observed Δ range.

### Pre-written readings (equal prominence)

- **Measurable decay, crossover in range:** person-models have a shelf
  life; the curve and the crossover Δ are the headline.
- **Flat decay across our Δ range:** public personas are stable at these
  horizons — grounding age does not matter within the years this corpus
  covers. Equally reportable, same prominence.

### Bars and rules

- **Confirmatory bar:** fidelity declines with Δ — per-subject slope of
  fidelity against Δ, mean slope < 0 across subjects, paired within subject
  where the chronology allows, p < .05, on the primary model.
  Direction-robust on the robustness model per A3.
- Exact Δ bins, the binning rule, and eligibility counts are frozen in the
  bar-lock addendum after dev-subject measurement and before any
  confirmatory H7 scoring (same pattern as B3).
- Subject-count branch, mirroring A5/B3 and decided solely by the
  H7-eligible confirmatory subject count: ≥ 80 → confirmatory as above;
  30–79 → exploratory (effect size + CI); < 30 → descriptive only.
- **Declared confounds, stated in every write-up:** (a) staleness bundles
  person-change and world-change — topics move on even when the person does
  not; H7 measures operational staleness (how useful old grounding is), not
  its mechanism. (b) At matched token budget, older-cutoff grounding can
  differ in venue and interview count; venue composition per bin is
  reported descriptively.
- H7 is co-headline with H1. Costs logged per arm as everywhere.

## B8. Standing reporting rule — individual-level AND population-level, side by side

From this amendment on, every fidelity report in this project shows BOTH of
these, side by side, in the same table:

1. **Individual-level lift** — the project's primary metric (own-twin minus
   baseline and minus imposter, per A1).
2. **A population-level distribution-match metric** — total variation
   distance (TVD) or equivalent between predicted and true answer/option
   distributions, per subject and pooled. The metric family is frozen now;
   the exact forced-choice operationalization is frozen at bar-lock.
3. **Divergences explicitly flagged** — wherever the two levels disagree
   (good population match with poor individual lift, or the reverse), the
   disagreement is called out in the report body, not in a footnote.

Motivation, on the record: the field's headline numbers are
individual-level while deployed operating thresholds are population-level,
and the two can diverge completely — a system can match a population's
answer distribution while being wrong about every individual, and vice
versa. Documenting where they diverge on our data is a standing deliverable
of every fidelity report. No confirmatory bar attaches to the population
metric; it is a mandatory descriptive companion.

## B9. Positioning, scope, and one withdrawal

### B9.a Prior work and the two claimed contributions

Binding kill-rule on all write-ups: no DOPPLER document may claim that
adaptive or uncertainty-guided questioning is untested. Any "nobody has
tested this" phrasing is removed project-wide. The record cited instead:

- **BED-LLM (ICLR 2026)** — Bayesian experimental design for adaptive LLM
  questioning. Our Stage 1E entropy rule corresponds to their weak
  baseline. The honest defense on our task: Stage 1E's EXP3 tested
  target-aware expected-information-gain selection and found no significant
  headroom over self-uncertainty (largest edge +0.019, p = .12, n = 100;
  `results/overnight_stage1e.md`), and the confirm run showed neither
  beats a population-derived static order at these budgets.
- **Wang et al. (ICML 2025)** — adaptive elicitation on OpinionQA.
- **A May 2026 preprint** on adaptive interviewing for persona simulation —
  small effect, small scale; the flag is planted and is cited.

The two contributions this project claims, stated as such in every
write-up: **(1) the population-optimized static-script baseline** that
prior adaptive-questioning work omits — Stage 1E showed it beating adaptive
selection at a tenth of the compute; **(2) elicitation budgets priced in
human time** (respondent seconds), which no prior work prices. Project
identity follows: DOPPLER is measurement and validation science for
person-models — what makes a twin faithful, where it fails, how fast it
goes stale — not a competing interviewer.

### B9.b Stage 3 demoted; H4-live withdrawn (documented deviation)

The Stage 3 live app is demoted from research stage to **optional demo
carrying no hypothesis**. **H4 is withdrawn as a registered claim.** This
is a documented deviation from the original registration, with reasons on
the record: (1) commercial products now ship live interview-to-twin at
scale, so the novelty claim is gone; (2) Stage 1E already answered the
closed-pool version of the question — a properly powered null for adaptive
selection, with a static script ahead at lower cost. Consequence for H5
(calibration), which was registered as pooled across Stages 2–3: **H5 is
re-scoped to Stage 2 predictions.** If the demo is ever built and run, its
data is exploratory and carries no registered claim.

### B9.c H2 / H6 / H7 stay separate

Three separate contrasts, separate write-ups, no shared or pooled headline
(extends B5): H2 varies the selection policy at matched budget; H6 varies
the content type at matched budget; H7 varies the grounding age at matched
budget. A positive result in one is not evidence for another. Any
interaction analysis among them is exploratory.

## B10. Stage 2 eval instrument, revised on pilot evidence — generated same-question counterfactuals

**Amended by pilot evidence, before any confirmatory data.** Two
dev-subject pilots showed that forced choice over verbatim real answers is
invalid on this corpus, in a way no distractor sourcing can repair:

- Pilot 1 (`results/stage2_pilot/PILOT_REPORT.md`, finding 8.0):
  distractors drawn from other people's interviews — the zero-information
  baseline solved all 17 items on topical coherence alone.
- Pilot 2 (`results/stage2_pilot2/PILOT_REPORT_2.md`): distractors drawn
  from the same subject's other interviews — the zero-information baseline
  solved all 10 items. The diagnostic decomposition located the mechanism:
  entity-stripping changed nothing (10/10), removing the question collapsed
  accuracy to 1/10. The solve rides entirely on the true answer being the
  only option *responsive* to the question shown. Responsiveness is
  intrinsic to verbatim real answers: distractors are, by definition,
  answers to other questions.

Both pilots used dev subjects only; no confirmatory subject or data was
involved. The original instrument (PREREGISTRATION.md §3 Stage 2 eval
mechanics, as tightened by Amendment 1 A4) is therefore revised as follows.

### The revised instrument

1. **Generated same-question counterfactuals.** For each held-out Q–A
   pair, the distractors are GENERATED answers to the SAME question,
   expressing positions that genuinely conflict with the subject's actual
   answer. Every option is responsive to the question by construction, so
   responsiveness ceases to be a tell.
2. **What is scored (binding reframing, stated in every write-up):** the
   claim scored is that the twin **identifies the person's actual POSITION
   among plausible alternative positions** on the same question — not that
   it picks a verbatim transcript answer.
3. **Generator separation (binding).** The generator model is never any
   scored model. Generation, paraphrase, and contradiction checks run on
   the Gemini side; Gemma never scores its own writing. The exact
   generator version is documented per run. Residual declared limitation:
   the robustness scoring model (A3) is Gemini-family; the generator must
   be a different model version than the robustness scorer, and if
   operational constraints ever force the same version, that overlap is
   reported beside every robustness number it touches.
4. **Style neutralization.** Every option INCLUDING the true answer passes
   one neutral paraphrase/normalization step by the generator-side model,
   so corpus-verbatim style cannot mark the true option. The paraphrased
   true answer is checked for position preservation; failures are logged
   and the item is rebuilt or dropped.
5. **Contradiction check.** Each distractor is checked to genuinely
   CONFLICT with the true answer's position — a distractor that
   paraphrases the true position is rejected. Rejection counts logged.
6. **Option-set matching.** Entity density, length, and era consistency
   are matched within the option set. Generated text must not reference
   events after the test interview's date. Relaxation-ladder rungs
   recorded per item, as in the pilots.
7. **Build-time zero-information gate (final arbiter).** An item the
   zero-information arm argmax-solves at build time never enters the set.
   Pre-gate zero-info accuracy on the candidate set is the reported
   instrument-difficulty number; post-gate zero-info accuracy is ~0 by
   construction and is labelled as such. On gated sets the informative
   baselines are the imposter arm and chance. This gate subsumes A4.3's
   score-time adversarial filter; both pre-gate and post-gate numbers are
   always reported. A4.1 matching and the A4.2 entity-stripped variant are
   retained.
8. **Human detectability check (binding, at the dev-pilot stop-point).**
   The owner receives 20 unmarked items — 10 real items (paraphrased true
   answer among generated distractors) and 10 controls (all options
   generated, no real answer present) — and attempts to identify the real
   option in each. The hit rate is reported in the pilot report. If the
   owner beats chance materially, the design iterates before any
   confirmatory registration.
9. **Freeze path.** All numeric and procedural parameters — generator
   version, paraphrase procedure text and hash, contradiction-check rule,
   era window, matching tolerances, gate rule — are frozen in the bar-lock
   addendum after the owner reviews dev pilot 3. Confirmatory subjects are
   untouched by the new instrument until that addendum is committed.

H1, H2, H6, and H7 are unchanged as hypotheses; they are scored on the
revised instrument. The contamination meter and all A1/A3 requirements
apply unchanged.
