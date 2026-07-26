# DOPPLER pre-registration — OSF timestamp snapshot, v2

Prepared 2026-07-26 for external timestamping. **Frozen copy. Do not edit.**

This supersedes `results/osf_preregistration_snapshot.md`, which covered only the
original pre-registration and Amendment 1 and is itself kept verbatim forever. v2
carries all four governance documents in adoption order, exactly as committed.

Each document below is preceded by a provenance header giving the commit it was
adopted in and the sha256 of the file at that commit. Nothing was added, removed,
or reworded inside any document.

**The OSF upload itself has not happened.** Until it does, "pre-registered" means
"committed to git before the data was touched".

| # | document | adopted in commit | sha256 |
|---|---|---|---|
| 1 | `PREREGISTRATION.md` | `6aff273` | `cf63d90b301859b60d174738bfdffc1d2ba8aa32e28394973f836ae9dd2df046` |
| 2 | `PREREGISTRATION_AMENDMENT_1.md` | `6aff273` | `b0e284d40cb36a1a4335a6b0c1716a9b512a9bb4e7949fb473c634965d6b44cc` |
| 3 | `PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md` | `3b8dd57` | `5ccd445b753bcc4c32481e3c0ca5d09386b91d481ce2ab139ed244fa156b4172` |
| 4 | `PREREGISTRATION_AMENDMENT_2.md` | `9949c9d` | `f0f52730b5be8363045b99a48fefffeff4f905f881db3f6b96ce03a76217fd4d` |

Later documents override earlier ones where they conflict.

---

<!-- SNAPSHOT DOCUMENT 1 OF 4 -->

**Provenance — document 1 of 4:** `PREREGISTRATION.md`, adopted in commit `6aff273`, sha256 `cf63d90b301859b60d174738bfdffc1d2ba8aa32e28394973f836ae9dd2df046`. Verbatim below.

# Project DOPPLER — Pre-Registration

**Digital twins Of People from Public and Live Elicited Records**
(Also a pun: the Doppler effect infers an object's motion from shifted signals it emits — we infer a person's behavior from the interview signals they emit. And it echoes "doppelgänger.")

Status: pre-registered before any experiment is run. Analysis code may be built and debugged on Stage 1 data, but all bars below are frozen before Stage 2/3 data is scored.

---

## 1. Context and motivation

Recent work (Park et al. 2024, "Generative Agent Simulations of 1,000 People"; commercialized by Simile) showed that an LLM agent grounded in a 2-hour interview with a real person can reproduce that person's survey answers at ~0.85 normalized accuracy, where normalization is against the person's own 2-week test-retest consistency (~0.80 raw). Open questions this project attacks:

1. **Interview value:** Which information about a person buys the most predictive fidelity per minute of their time? Does *adaptive* elicitation (choosing what to ask next based on current uncertainty) beat fixed scripts at matched budgets?
2. **Twin architecture:** Given the same transcript, which agent construction yields the highest fidelity (raw transcript in context vs. distilled persona vs. adaptive context selection vs. small fine-tuned model)?
3. **Calibration:** Can a twin report trustworthy confidence in its own predictions?

Constraint honesty: solo researcher, no budget for paid participants, no proprietary interview data. All designs below are executable at ~zero cost.

## 2. Core definitions

- **Twin:** an LLM-based agent whose context or weights are grounded in records of one specific real person, prompted to answer as that person.
- **Fidelity:** agreement between the twin's answers and the real person's actual answers on items the twin was never grounded on.
- **Lift:** fidelity of the grounded twin minus fidelity of the zero-information baseline (same model, same items, no grounding, identity redacted). **Lift is the primary metric everywhere.** Raw fidelity alone is never reported without its baseline.
- **Ceiling:** the person's own self-consistency (same/similar question answered at two different times). Fidelity is also reported normalized by ceiling where ceiling is measurable.

## 3. Stages

### Stage 1 — Gym (survey replay; development only, no confirmatory claims)

- **Data:** OpenPsychometrics raw datasets (public mirror, no registration): primary RIASEC (~146k respondents; 48 interest items + TIPI personality + vocabulary + rich demographics incl. free-text major), secondary Cattell 16PF, HEXACO, MACH (MACH includes per-item response times in ms, used to build realistic time-cost functions). GSS cross-sectional download for heterogeneous-topic replay.
- **Setup:** each respondent row is treated as a replayable person. The system "interviews" by revealing that person's recorded answers one item at a time; after k items it predicts held-out items.
- **Purpose:** debug the full pipeline (elicitation policy, twin construction, scoring, calibration) and tune all hyperparameters. Cross-domain prediction only (e.g., seed on interests + demographics → predict personality items); within-scale prediction is disallowed as an outcome because item redundancy makes it trivial.
- **Pre-specified sanity gate (go/no-go):** grounded twin lift over the demographics-only baseline must be positive and significant on RIASEC cross-domain prediction (n ≥ 500 held-out persons). If not, the twin constructor is broken; fix before proceeding.

### Stage 2 — Recurring-guest corpus (main confirmatory study)

- **Idea:** people who give many public interviews have natural held-out data. Ground a twin on a person's earlier interviews; test it on real questions from a *later* interview it never saw.
- **Data sources (no signup):** MediaSum (~463k NPR/CNN interview transcripts, GitHub); podcast transcripts via yt-dlp auto-captions and openly published transcripts (e.g., shows that post full transcripts). Curation target: ≥ 30 subjects with ≥ 3 substantive interviews each, biased toward **long-tail subjects** (no or minimal Wikipedia presence) rather than celebrities.
- **Splits:** strictly chronological. Grounding = earliest interviews; test = latest interview. A fully airtight subset uses test interviews dated after the simulation model's training cutoff.
- **Contamination controls (mandatory):**
  - Zero-information baseline per subject: identity redacted, no transcripts. Primary metric is lift.
  - **Contamination meter:** per subject, (named baseline) − (name-redacted baseline). Reported per subject and as a corpus figure; subjects with a large meter are analyzed separately.
- **Eval mechanics:** from each held-out interview, extract Q–A pairs. Convert to forced-choice: the real answer's content hidden among 3–4 distractor answers (drawn from other guests' answers to similar questions), position-randomized. Twin picks (or generates, then an embedding match selects nearest option). Secondary: open-ended generation scored by rubric, exploratory only.
  - **Ceiling harvest:** where a subject answered the same/similar question in two different grounding interviews, cross-interview self-consistency is computed and used as that subject's ceiling.
- **Adaptive component (offline form):** *adaptive context selection.* Under a fixed context-token budget B, compare (a) random transcript segments, (b) recency-selected, (c) model-selected segments chosen to reduce its own uncertainty about the test domain. Same budget, same model, only selection differs.
- **Pre-registered hypotheses and bars:**
  - **H1 (grounding works):** mean lift > 0 across subjects, p < .05 (paired test over subjects). Interesting bar: mean normalized fidelity ≥ 0.70 of ceiling on the low-contamination subject subset.
  - **H2 (selection matters):** model-selected context beats random-segment context at matched budget by ≥ 5 points fidelity. Null result (≤ 5 points) is reported as a finding: transcript content is fungible.
  - **H3 (fame confound, descriptive):** lift shrinks as the contamination meter grows.
- **What this stage measures, honestly:** the *public persona* — prediction of what a person will say in their next public interview given their previous ones. Stated as such in all write-ups.

### Stage 3 — Live gamified study (adaptive elicitation on real people)

- **Format:** small web app: "Chat with an AI for 15 minutes; it builds your twin; watch the twin try to guess your answers to 20 questions; see your twin's score." Recruitment: public posting in online communities; volunteers, no payment. Consent checkbox + plain-language data-use notice; no PII beyond a pseudonymous ID and optional email for the retest.
- **Design:** participants randomized to interviewer arm:
  - **Arm A — fixed script** (Simile-style condensed protocol).
  - **Arm B — adaptive interviewer:** after each answer, the system asks the question whose predicted answer distribution (sampled from the current twin) has the highest uncertainty, subject to conversational coherence. This is the project's core novelty claim and is never dropped.
  - Matched interview duration across arms.
- **Outcomes:** immediate held-out question fidelity (20 items spanning attitudes, preferences, behavior self-reports); **2-week retest** of the same items by email for the self-consistency ceiling; calibration (below).
- **Pre-registered hypotheses and bars:**
  - **H4 (adaptive beats scripted):** Arm B twins achieve higher normalized fidelity than Arm A at matched time. Interesting bar: +5 points or a 30% interview-time reduction at matched fidelity. Given expected small n (target n ≥ 30, realistically 20–60 volunteers), this is reported as a **pilot estimate with confidence intervals**, not a definitive test; the direction and effect size are the deliverable.
  - **H5 (calibration):** twin confidence (self-consistency sampling: k = 10 samples, agreement rate = confidence) is calibrated: ECE ≤ 0.10 on pooled predictions across Stages 2–3. Reliability diagrams reported regardless.

## 4. Models and infrastructure (design choices, fixed)

- **Simulation model (the twin/interviewer engine):** gemini-3.5-flash-lite via API, or an open-source small model (~7–8B) served on Leonardo HPC. **Never Anthropic Haiku/Sonnet-class models for human simulation** (cost). MoE architectures are known not to work on the Leonardo setup; use dense models.
- **Fine-tune ablation arm (Stage 2 extension, optional):** LoRA fine-tune of a dense 7–8B open model on a subject's grounding transcripts vs. the same base model with transcripts in context. Same eval, same budget accounting.
- **Compute:** Leonardo EuroHPC (project 548 allocation). Long training runs use 4 GPUs of a node with distributed training (whole node is billed regardless; 1-GPU runs on a full node are forbidden waste).
- **No from-scratch pretraining, ever.** Contamination is handled by experimental design (lift, redaction, time splits), not by model surgery.

## 5. Analysis and reporting rules

- All bars above are frozen now. Any post-hoc analysis is labeled exploratory.
- Nulls are published with the same prominence as positives. Every hypothesis has a pre-written "what a null means" interpretation (H2 null → transcript fungibility; H4 null → scripted interviews suffice at short durations).
- Per-claim provenance: every reported number links to the script and data snapshot that produced it.
- Compute and API cost are logged and reported (cost-per-twin is itself a result).

## 6. Known limitations (declared up front)

- Stage 2 measures public personas, not private individuals.
- Stage 3 is a volunteer convenience sample; results are pilot-grade.
- Auto-captions (yt-dlp) are noisy; transcript quality is quantified (WER spot-check on a sample) and reported.
- Forced-choice fidelity is a proxy for open-ended behavioral fidelity.

## 7. Deliverables

1. Open-source pipeline (replay gym, corpus builder, twin constructor, adaptive interviewer, eval harness).
2. The headline figures: fidelity-vs-budget curves (Stage 1–2), lift-vs-contamination plot, Arm A vs. Arm B comparison, reliability diagrams.
3. A short paper/technical report per stage; Stage 2 is the primary publication target.
4. The live demo app (Stage 3) doubling as a portfolio artifact.

---

<!-- SNAPSHOT DOCUMENT 2 OF 4 -->

**Provenance — document 2 of 4:** `PREREGISTRATION_AMENDMENT_1.md`, adopted in commit `6aff273`, sha256 `b0e284d40cb36a1a4335a6b0c1716a9b512a9bb4e7949fb473c634965d6b44cc`. Verbatim below.

# Project DOPPLER — Pre-Registration Amendment 1

Adopted: 2026-07-24. Status at adoption: Stage 1 complete (gate PASS, commit
`ce54d9b`; Gemma-4-31B-it + v2 promoted to primary simulation model per the
pre-committed rule). Stage 2 Phase A corpus recon complete (commit `e9d019e`).
**No Stage 2 twin construction or evaluation data exists at adoption.**
Prompted by an external review of the design. Where this amendment conflicts
with PREREGISTRATION.md, this amendment governs. Everything not amended
stays frozen as originally registered.

## A1. Imposter baseline (mandatory, all stages)

Every fidelity report gains a third arm beside the grounded twin and the
zero-information baseline: an **imposter twin** — the identical pipeline and
context budget, but grounded entirely on a different person's data drawn from
the same domain (identity-redacted, deterministic seeded matching).

- Stage 2 primary lift = own-twin fidelity − imposter-twin fidelity.
  Zero-information lift is still computed and reported alongside.
- **H1 bar (updated):** H1 passes iff BOTH mean zero-info lift > 0 AND mean
  imposter lift > 0, each p < .05 (paired test over subjects).
- Gym analog (Stage 1E below): the imposter profile is another respondent's
  demographics + revealed items in full; the prediction targets stay the
  test person's.
- Why: zero-info lift can be earned by generic-population knowledge; imposter
  lift isolates person-specific signal.

## A2. Ceiling demoted to descriptive

Corpus-harvested cross-interview self-consistency ("ceiling harvest") is
descriptive only. The "mean normalized fidelity >= 0.70 of ceiling"
interesting-bar in H1 is withdrawn as a confirmatory bar; ceiling-normalized
numbers are reported as exploratory. Stage 2 confirmatory bars operate on raw
lift and imposter lift only.

## A3. Two-model replication for Stage 2 headlines

Any Stage 2 headline claim must replicate in direction and significance on
both Gemma-4-31B-it + v2 (primary) and gemini-3.5-flash-lite + v2
(robustness). A result holding on one model only is reported as
model-specific, never as a headline.

## A4. Distractor controls (Stage 2 forced-choice)

1. Distractors are matched to the true answer on length (within ±20% of token
   count) and named-entity density.
2. An **entity-stripped scoring variant** (all named entities masked in every
   option) is reported alongside the standard variant.
3. **Adversarial filter:** items the zero-information baseline answers
   correctly are flagged; all results are reported both filtered (flagged
   items removed) and unfiltered.

## A5. Curation target and the H2 power branch

- Stage 2 curation target is raised from >= 30 to **>= 80 subjects** (still
  biased long-tail). Phase A recon (results/stage2_corpus_recon.md) shows the
  pool supports this.
- **Branch, declared pre-data and decided solely by delivered subject count:**
  - If curation delivers >= 80 subjects: H2 is confirmatory with its original
    bar (model-selected context beats random segments by >= 5 points at
    matched budget).
  - If curation delivers 30–79: H2 is exploratory (effect size + CI, no
    hypothesis-test claim); H1 remains confirmatory.

## A6. New confirmatory experiment, inserted before any Stage 2 twin data: Stage 1E — adaptive elicitation, offline

Setting: the RIASEC replay gym. Demographics are given up front; the 48
interest items are revealed one at a time, true recorded answer per reveal.
After k reveals the v2 twin predicts all 10 held-out TIPI items
(cross-domain, as in the gate). Primary metric: TIPI MAE lift vs the
demographics-only baseline, as a function of k; imposter arm per A1.

- Policies:
  1. **Random order** (per-person seeded).
  2. **Best fixed order** — one global item order chosen by greedy forward
     selection maximizing statistical predictability of TIPI from the
     revealed set on training-split ground truth (regression-based; no LLM in
     the selection). Design note: an LLM-based greedy selection was rejected
     on cost; the statistical order is the stronger, cheaper "best fixed
     script" benchmark.
  3. **Adaptive greedy** — next reveal = the remaining item whose answer the
     current twin is most uncertain about (highest entropy of the v2 stated
     probability distribution for that item, ties broken by item index).
- Budget checkpoints: k ∈ {1, 2, 4, 8, 12, 16, 20}. (Owner's directive
  specified a maximum budget of 20; this grid is the adopted reading. If the
  owner corrects the intended budget set at pilot review, the correction is
  recorded in the bar-lock addendum below and applies to the confirm run.)
- Splits: tuning and the fixed-order selection use a training split, disjoint
  from pilot1 (n=20), pilot2 (n=50), and the gate set (n=500). The
  confirmatory run uses a frozen confirm split of >= 1,000 persons, disjoint
  from all of the above, untouched until bars are locked.
- Primary confirmatory contrast: adaptive (iii) vs random (i) at matched k.
  Secondary: adaptive (iii) vs best fixed (ii).
- **Bar-lock addendum:** numeric bars for these contrasts are frozen in a
  dated addendum to this amendment after the training-split pilot is reviewed
  by the owner and before any confirm-split call is made. The confirm split
  is not touched before that addendum is committed.
- Replication: after the TIPI confirm run, the same protocol is replicated on
  the 16PF dataset (163-item pool); its seed pool, target domain, and split
  sizes are locked in the same bar-lock addendum before any 16PF confirm run.

## A7. Known-answer probe (declared diagnostic, not confirmatory)

One diagnostic run on the gate persons (n=500): seed the twin on
demographics + 5 TIPI items, predict the other 5, counterbalanced (folds
{TIPI1–5} and {TIPI6–10}, so every predicted item has its same-trait pair in
the seed; both directions run). Purpose: bound the constructor — if
within-scale seeded lift is also small, the +0.085 gate lift reflects a weak
constructor; if large, a hard task. Within-scale prediction remains
disallowed as an outcome claim (original registration); this probe is
reported as a diagnostic beside the gate number, with no bar.

## A8. Reporting

All original reporting rules stand (nulls published, per-claim provenance,
cost logging). This amendment and PREREGISTRATION.md are committed together;
an OSF snapshot of both is prepared for external timestamping.

---

<!-- SNAPSHOT DOCUMENT 3 OF 4 -->

**Provenance — document 3 of 4:** `PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md`, adopted in commit `3b8dd57`, sha256 `5ccd445b753bcc4c32481e3c0ca5d09386b91d481ce2ab139ed244fa156b4172`. Verbatim below.

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

---

<!-- SNAPSHOT DOCUMENT 4 OF 4 -->

**Provenance — document 4 of 4:** `PREREGISTRATION_AMENDMENT_2.md`, adopted in commit `9949c9d`, sha256 `f0f52730b5be8363045b99a48fefffeff4f905f881db3f6b96ce03a76217fd4d`. Verbatim below.

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

