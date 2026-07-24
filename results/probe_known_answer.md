# Known-answer probe (A7) — probe_knownanswer_v2_20260724-211148_leonardo-batch

> **DIAGNOSTIC ONLY — NOT A CONFIRMATORY RESULT AND NOT AN OUTCOME CLAIM.**
> Declared in advance as PREREGISTRATION_AMENDMENT_1.md section A7, which attaches **no bar** to it.
> Within-scale prediction stays disallowed as an outcome claim under the original registration.
> The only job of this run is to bound the constructor. Nothing here passes, fails, or revises a hypothesis.

Generated 2026-07-24 19:14 UTC

## 1. What was run

Verbatim from PREREGISTRATION_AMENDMENT_1.md, section A7:

> One diagnostic run on the gate persons (n=500): seed the twin on
> demographics + 5 TIPI items, predict the other 5, counterbalanced (folds
> {TIPI1-5} and {TIPI6-10}, so every predicted item has its same-trait pair in
> the seed; both directions run). Purpose: bound the constructor - if
> within-scale seeded lift is also small, the +0.085 gate lift reflects a weak
> constructor; if large, a hard task. Within-scale prediction remains
> disallowed as an outcome claim (original registration); this probe is
> reported as a diagnostic beside the gate number, with no bar.

Implementation:

- Persons: the frozen GATE set, n=500 (positions 21-520 of the seed-42 draw of 520). Verified identical to the gate run's person ids.
- Twin prompt: the gate's demographics rendering, then five of the person's own TIPI items shown as already-answered questions with their true 1-7 answers, then the v2 probability-distribution elicitation for one held-out TIPI item. **No interest items anywhere in the prompt.**
- Folds (both directions run for every person): `A2B` = seed TIPI1-5 -> predict TIPI6-10; `B2A` = seed TIPI6-10 -> predict TIPI1-5. TIPI's same-trait pairs are (1,6) (2,7) (3,8) (4,9) (5,10), so every predicted item has its own trait partner sitting in the seed.
- Each person contributes one prediction per item: 10 per person, 5000 twin completions in total.
- Model: Gemma-4-31B-it on Leonardo (vLLM 0.25.1, TP=4, bf16, temperature 0), same stack as the gate secondary arm. Same v2 parser, same MAE-by-expected-value scoring, same parse-failure exclusion rule.
- Baseline: **reused** from the gate run `gate_v2_k48_20260724-182324_leonardo-batch` (5000 demographics-only records). All 5,000 baseline prompts were byte-compared against the gate's and were identical, so regenerating them would have produced the same text at temperature 0.

## 2. Result: within-scale MAE lift, beside the gate's cross-domain lift

MAE lift = baseline MAE − twin MAE, per person, averaged over that person's items. Positive = the seeded twin is closer to the truth. Paired t and Wilcoxon are over the 500 persons.

| arm | twin MAE | baseline MAE | MAE lift | 95% CI | t | t p | Wilcoxon p | n |
|---|---|---|---|---|---|---|---|---|
| **PROBE within-scale** (this run) | 1.4842 | 1.5295 | +0.0453 | [-0.0077, +0.0983] | 1.6798 | 0.0936 | 0.0618 | 500 |
| Gate cross-domain, PRIMARY (gemini-3.5-flash-lite + v2) | — | — | +0.0850 | [+0.0689, +0.1012] | 10.3541 | 6.87e-23 | — | 500 |
| Gate cross-domain, SECONDARY (Gemma-4-31B-it + v2) | — | — | +0.0954 | [+0.0750, +0.1159] | 9.1686 | 1.25e-18 | — | 500 |

Probe vs gate secondary (the directly comparable pair — same model, same 500 persons, same 10 items, same baseline records): **+0.0453** within-scale vs **+0.0954** cross-domain, a ratio of 0.47x.

- persons scored: 500; parse failures: 0; excluded pairs: 0; missing completions: 0

## 3. By fold direction

Each direction is 5 predicted items per person over the same 500 persons, so the two rows are independent in items but paired in people.

| direction | twin MAE | baseline MAE | MAE lift | 95% CI | t | t p | Wilcoxon p | n |
|---|---|---|---|---|---|---|---|---|
| `A2B` (seed TIPI1-5 -> predict TIPI6-10) | 1.4788 | 1.5211 | +0.0423 | [-0.0177, +0.1022] | 1.3849 | 0.167 | 0.0986 | 500 |
| `B2A` (seed TIPI6-10 -> predict TIPI1-5) | 1.4895 | 1.5378 | +0.0483 | [-0.0052, +0.1018] | 1.7744 | 0.0766 | 0.0407 | 500 |

## 4. Per predicted item

`seeded by` names the same-trait partner that was in the seed for that prediction. Pooled over persons (not a per-person paired test).

| predicted item | seeded by | direction | n | twin MAE | baseline MAE | MAE lift |
|---|---|---|---|---|---|---|
| TIPI1 | TIPI6 | `B2A` | 500 | 1.7607 | 1.7696 | +0.0089 |
| TIPI2 | TIPI7 | `B2A` | 500 | 1.8235 | 1.8566 | +0.0330 |
| TIPI3 | TIPI8 | `B2A` | 500 | 1.1789 | 1.2194 | +0.0405 |
| TIPI4 | TIPI9 | `B2A` | 500 | 1.4807 | 1.6084 | +0.1278 |
| TIPI5 | TIPI10 | `B2A` | 500 | 1.2037 | 1.2351 | +0.0314 |
| TIPI6 | TIPI1 | `A2B` | 500 | 1.7448 | 1.8058 | +0.0610 |
| TIPI7 | TIPI2 | `A2B` | 500 | 1.4878 | 1.1878 | -0.3000 |
| TIPI8 | TIPI3 | `A2B` | 500 | 1.2495 | 1.5712 | +0.3217 |
| TIPI9 | TIPI4 | `A2B` | 500 | 1.5851 | 1.5134 | -0.0717 |
| TIPI10 | TIPI5 | `A2B` | 500 | 1.3270 | 1.5274 | +0.2004 |

## 5. Secondary metrics (never reported alone)

| metric | twin | baseline | lift | 95% CI | t p |
|---|---|---|---|---|---|
| within-1 (argmax) | 0.5866 | 0.5588 | +0.0278 | [+0.0040, +0.0516] | 0.0222 |
| exact match (argmax) | 0.2756 | 0.1900 | +0.0856 | [+0.0659, +0.1053] | 1.88e-16 |

## 5b. Why the lift is small — mechanism (EXPLORATORY, post-hoc)

_Not pre-registered. Computed after seeing the headline, to check the pipeline was working before the small lift is interpreted._

**The twin is not ignoring the seed.** Handing it five of the person's own answers moves the prediction in 98.3% of the 5000 (person, item) pairs, by 1.18 scale points on average.

| diagnostic | twin (seeded) | baseline (demographics only) | truth |
|---|---|---|---|
| Spearman rho with the seed answer on the trait partner | -0.931 | -0.482 | -0.558 |
| Spearman rho with the true answer | +0.591 | +0.487 | — |
| regression slope of prediction on truth | 0.482 | 0.231 | 1.000 |
| sd of the prediction | 1.623 | 0.960 | 1.977 |
| mean peak stated probability | 0.444 | 0.295 | — |
| share of answers with peak probability >= 0.5 | 27.4% | 0.9% | — |

Read the first row carefully. Real respondents' answers on a reverse-scored trait pair correlate -0.558. The seeded twin's predictions correlate -0.931 with the seed — it treats the reverse item as a near-deterministic mirror of the one it was shown, far tighter than real people are. It applies the scoring rule, not the person.

That over-commitment is exactly why the accuracy gains and the MAE gain disagree. Error mass, share of predictions off by more than:

| error > | twin | baseline |
|---|---|---|
| 1 scale point | 54.1% | 67.5% |
| 2 scale points | 27.8% | 31.1% |
| 3 scale points | 12.8% | 6.8% |
| 4 scale points | 4.4% | 0.9% |

The twin is right far more often (exact match 0.276 vs 0.190, lift +0.0856) and tracks the truth better in rank terms (rho 0.591 vs 0.487), but it is badly wrong more often too. MAE prices both, so the two roughly cancel and the headline lift lands near zero. The baseline earns its MAE by hedging near the scale midpoint; the twin earns its exact matches by committing, and pays for the commitments it gets wrong.

## 6. Leakage guards

Enforced at prompt-build time; any violation raises and stops the run (`experiments/probe_known_answer.py`, unit-tested in `tests/test_probe_known_answer.py`):

1. A predicted item is never in its own seed set, and no seed item carries the predicted item's text.
2. The predicted statement appears exactly once in the whole prompt (only in `YOUR TASK`), and its recorded answer is never attached to it.
3. No interest-item text and no interests block ever enters a probe prompt — the seed is TIPI + demographics only.
4. Fold construction is unit-tested: 5/5 disjoint split, the two directions together cover each of the 10 items exactly once, and every predicted item's same-trait partner is in the seed.
5. The baseline arm was byte-compared, all 5,000 prompts, against the gate run before its completions were reused.

## 7. How to read this (interpretation guide)

This probe asks one question: **when the twin is handed five of the person's own answers on the very same questionnaire — including, for every prediction, the item measuring the same trait — how much better than a demographics-only guess does it get?** That is close to the easiest individuating information the constructor could ever be given, so it acts as a ceiling on what this constructor can extract from person-specific data.

A **large** within-scale lift (several times the cross-domain lift) would say the constructor works fine — it uses individuating information well when that information is on-topic — and the small +0.085 / +0.095 gate lift is then mostly a statement about the task: predicting personality from vocational interests is genuinely hard, and there may not be much more signal in interests to extract. Under that reading, effort belongs on richer or better-matched evidence, not on the constructor.

A **small** within-scale lift (of the same order as the cross-domain lift, or smaller) would say the opposite: even handed the answer's own trait partner, the twin barely improves on MAE. That points at the constructor and the elicitation rather than the task, and it caps how much any Stage-2 result can be attributed to person-specific grounding. It would also mean the gate's small lift should not be read as evidence that vocational interests carry little personality signal — the pipeline may simply not be converting individuating facts into better-calibrated predictions.

**This run landed in the second case:** within-scale lift +0.0453 [-0.0077, +0.0983], paired t p=0.0936 — not significant, and **smaller** than the gate's cross-domain +0.0954 on the same model, the same 500 people, and the same baseline records (ratio 0.47x). The easiest possible individuating evidence does not buy more MAE than vocational interests did.

Section 5b says why, and it matters for what you conclude. The twin clearly **uses** the seed — predictions move, and rank agreement with the truth and exact-match accuracy both rise well above baseline. What it does not do is stay calibrated: it treats a reverse-scored item as a near-deterministic mirror of the item it was shown, commits hard, and eats a fat error tail when the person does not behave like the scoring key. So the honest reading of this probe is **not** "the constructor cannot use person-specific information"; it is "the constructor over-extrapolates from it, and MAE — the pre-registered primary metric — does not reward that." A calibration or hedging fix to the elicitation is the indicated next lever, ahead of hunting for richer evidence.

One consequence for Stage 2: expect this constructor's headline lift to stay small on MAE even when its inputs get much richer, and expect accuracy-style secondaries to look better than MAE. That is a property of the pipeline, established here, not a fact about any Stage-2 corpus. It carries no bar and revises no hypothesis.

One caveat that limits both readings: seeded and cross-domain runs share the same baseline, so the comparison is fair, but the probe's seed is five items in the same scale format the model is being asked to produce. Some of any lift can be format mimicry (copying the person's response style or scale-use) rather than trait inference. The per-item table is where that shows up — mimicry should help roughly evenly, trait inference should concentrate on the seeded trait partner.

## 8. Cost

| run_id | backend | node_hours | twin tokens in | twin tokens out |
|---|---|---|---|---|
| probe_knownanswer_v2_20260724-211148_leonardo-batch | leonardo-batch | 0.14 | 2170390 | 245000 |

Baseline arm cost: **zero** — 5000 completions reused from `gate_v2_k48_20260724-182324_leonardo-batch` rather than regenerated. Budget cap for this probe was 1 node-hour.

## 9. Provenance

- Run dir: `results/probe_knownanswer_v2_20260724-211148_leonardo-batch/` — `records.jsonl` (full prompts and raw responses, both arms), `summary.json`, example prompts.
- Twin completions: `results/leonardo_probe/completions_v2.jsonl`
- Baseline records: copied from `results/gate_v2_k48_20260724-182324_leonardo-batch/records.jsonl` (arm=baseline).
- Task builder: `experiments/probe_known_answer.py`; report builder: `experiments/probe_report.py`; tests: `tests/test_probe_known_answer.py`.
- Gate numbers quoted in section 2 are frozen from `results/stage1_gate_report.md`.
