# DOPPLER pre-registration — OSF timestamp snapshot

Prepared 2026-07-24 for external timestamping. Contents: the original
pre-registration (frozen before any experiment) followed by Amendment 1
(adopted 2026-07-24, before any Stage 2 twin data).
Git provenance: original+amendment committed as 6aff273; Stage 1 gate ce54d9b; Phase A recon e9d019e.

---

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
