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
