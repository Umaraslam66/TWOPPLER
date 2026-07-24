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
