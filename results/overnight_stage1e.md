# Stage 1E overnight batch (EXP1-EXP5) — TRAINING-SPLIT RESULTS

**Label: TRAINING/DERIVATION SPLIT ONLY — for bar-setting and go/no-go judgement. No confirmatory claims. The confirm split has not been built or touched.**

Date: 2026-07-24. Spec: PREREGISTRATION_AMENDMENT_1.md A6, extending results/adaptive_pilot_train.md. Model: Gemma-4-31B-it (vLLM, TP=4, temperature 0), twin variant v2, same parser and scoring as the Stage 1 gate.

Lift = demographics-only baseline MAE − arm MAE, averaged over persons, 95% t interval and paired t-test. Higher is better.

## What was run, and what was reused

| experiment | status | reused from the pilot |
|---|---|---|
| EXP1a | submitted | nothing |
| EXP1b | submitted | nothing |
| EXP1c | submitted | nothing |
| EXP2 + EXP4 + EXP5 (shared static job) | submitted | results/adaptive_train_20260724-210916/baseline (k=0); results/adaptive_train_20260724-210916/random (k in 1,2,4,8,12,16,20); results/adaptive_train_20260724-210916/imposter (random imposter, k=12,20) |
| EXP3 | submitted | EXP1a and EXP1b curves restricted to the first 100 persons of the train split |

## EXP1 — tie-break, scorer and elicitation grid

All three variants replace the pilot's lowest-item-index tie-break with a seeded random one. The pilot's tie-break was deciding 51.5% of reveals, and lowest-index is biased towards R-items.

### Residual tie rate

| variant | decisions | tied at top | mean tied | max tied |
|---|---|---|---|---|
| pilot (entropy, index tie-break) | 3,000 | 51.5% | 3.0 | 37 |
| EXP1a entropy + random | not ingested | | | |
| EXP1b EV-variance + random | not ingested | | | |
| EXP1c entropy + random + 0.05 grid | not ingested | | | |

### Lift over baseline, by variant

| k | pilot adaptive | EXP1a entropy+rand | EXP1b EV-var | EXP1c fine grid |
|---|---|---|---|---|
| 1 | -0.006 [-0.023, +0.010] p=0.45 | not ingested | not ingested | not ingested |
| 2 | +0.004 [-0.015, +0.024] p=0.65 | not ingested | not ingested | not ingested |
| 3 | n/a | not ingested | not ingested | not ingested |
| 4 | +0.016 [-0.008, +0.040] p=0.19 | not ingested | not ingested | not ingested |
| 5 | n/a | not ingested | not ingested | not ingested |
| 8 | +0.030 [+0.002, +0.057] p=0.035 | not ingested | not ingested | not ingested |
| 12 | +0.052 [+0.023, +0.081] p=0.00047 | not ingested | not ingested | not ingested |
| 16 | +0.061 [+0.030, +0.093] p=0.00018 | not ingested | not ingested | not ingested |
| 20 | +0.070 [+0.038, +0.102] p=2.5e-05 | not ingested | not ingested | not ingested |

### Delta vs the pilot adaptive curve at matched k

Positive = the change helped.

| k | EXP1a − pilot | EXP1b − pilot | EXP1c − pilot |
|---|---|---|---|
| 1 | n/a | n/a | n/a |
| 2 | n/a | n/a | n/a |
| 4 | n/a | n/a | n/a |
| 8 | n/a | n/a | n/a |
| 12 | n/a | n/a | n/a |
| 16 | n/a | n/a | n/a |
| 20 | n/a | n/a | n/a |

## EXP2 — best fixed order, derived on a disjoint split

Derived on 2000 persons (seed 45), disjoint from all ? previously used people. Ridge greedy forward selection, no model involved.

Frozen order (first 20): `A3 E5 S5 A5 A2 C1 C2 S7 E7 A6 A7 I1 I8 S6 E1 S2 I2 S4 R2 C4`

Full 48: `A3 E5 S5 A5 A2 C1 C2 S7 E7 A6 A7 I1 I8 S6 E1 S2 I2 S4 R2 C4 R3 C6 E8 R4 C5 S8 S1 R7 A8 R1 E6 E2 A4 I7 I5 I3 R5 C7 E4 A1 E3 C3 C8 I4 S3 R6 R8 I6`

### Stability

| statistic | value | chance baseline |
|---|---|---|

### Frozen order applied to train-150

These 150 people had no say in picking this order, so this column is not inflated the way the pilot's `fixed` arm was.

| k | fixed_deriv lift | pilot fixed (selection-biased) |
|---|---|---|
| 1 | not ingested | +0.014 [-0.007, +0.035] p=0.18 |
| 2 | not ingested | +0.027 [+0.004, +0.050] p=0.024 |
| 3 | not ingested | — |
| 4 | not ingested | +0.060 [+0.032, +0.088] p=4.3e-05 |
| 5 | not ingested | — |
| 8 | not ingested | +0.070 [+0.040, +0.100] p=1.1e-05 |
| 12 | not ingested | +0.079 [+0.047, +0.112] p=2.9e-06 |
| 16 | not ingested | +0.080 [+0.047, +0.112] p=3.4e-06 |
| 20 | not ingested | +0.088 [+0.053, +0.122] p=1.4e-06 |
| 28 | not ingested | — |
| 36 | not ingested | — |
| 48 | not ingested | — |

## EXP3 — selection ladder: does target-aware selection beat self-uncertainty?

n=100 (first 100 of the train split). Ladder rung (a) is EXP1's self-uncertainty policy restricted to these people — not rerun. Rung (b) scores each shortlisted item by how much the 10 TIPI target distributions are expected to move.

| k | (a) self-uncertainty (EXP1a) | (b) expected info gain | (b) − (a) |
|---|---|---|---|
| 1 | not ingested | not ingested | n/a |
| 2 | not ingested | not ingested | n/a |
| 3 | not ingested | not ingested | n/a |
| 4 | not ingested | not ingested | n/a |
| 5 | not ingested | not ingested | n/a |
| 8 | not ingested | not ingested | n/a |
| 12 | not ingested | not ingested | n/a |
| 16 | not ingested | not ingested | n/a |
| 20 | not ingested | not ingested | n/a |

Rung (c), one-step lookahead, was **not run**: it multiplies rung (b)'s cost by the shortlist size again and does not fit inside EXP3's 3.0 node-hour cap alongside (b).

## EXP4 — budget curve: where does the edge peak, where does it saturate?

The random arm reuses the pilot's completions at k in {1, 2, 4, 8, 12, 16, 20} and buys only {3, 5, 28, 36, 48}. The adaptive side is EXP1a.

| k | random | adaptive (EXP1a) | adaptive − random |
|---|---|---|---|
| 1 | -0.005 [-0.022, +0.012] p=0.57 | not ingested | n/a |
| 2 | -0.001 [-0.021, +0.019] p=0.92 | not ingested | n/a |
| 3 | not ingested | not ingested | n/a |
| 4 | +0.001 [-0.020, +0.023] p=0.92 | not ingested | n/a |
| 5 | not ingested | not ingested | n/a |
| 8 | +0.006 [-0.020, +0.033] p=0.64 | not ingested | n/a |
| 12 | +0.027 [+0.000, +0.053] p=0.047 | not ingested | n/a |
| 16 | +0.040 [+0.012, +0.068] p=0.0056 | not ingested | n/a |
| 20 | +0.049 [+0.018, +0.079] p=0.0019 | not ingested | n/a |
| 28 | not ingested | not ingested | n/a |
| 36 | not ingested | not ingested | n/a |
| 48 | not ingested | not ingested | n/a |

Reference: the Stage 1 gate's all-48-item lift on 500 people was +0.095.

## EXP5 — imposter gradient: does a MORE similar wrong person mislead less, or more?

Nearest-neighbour donors are drawn inside train-150 by cosine similarity on the 48 interest ratings (mean 0.9339, min 0.8343), never self-paired. Reveal positions mirror the random arm, exactly like the pilot's random imposter.

The gradient is real: the random imposter's mean cosine is 0.8378, so the nearest neighbour is +0.0961 more similar. 76 distinct people serve as NN donors for the 150.

| k | own (random arm) | NN imposter | random imposter | own − NN | own − random imp | NN − random imp |
|---|---|---|---|---|---|---|
| 12 | +0.027 [+0.000, +0.053] p=0.047 | not ingested | -0.037 [-0.079, +0.006] p=0.091 | n/a | +0.063 [+0.019, +0.107] p=0.005 | n/a |
| 20 | +0.049 [+0.018, +0.079] p=0.0019 | not ingested | -0.048 [-0.095, -0.001] p=0.046 | n/a | +0.096 [+0.050, +0.143] p=6.5e-05 | n/a |

Read: the pilot found a random stranger's profile is *worse than knowing nothing* (lift −0.04 to −0.055 over baseline). If the nearest neighbour is less harmful, similarity buys back some generic signal; if it is more harmful, a plausible-but-wrong profile is the more dangerous failure — which is the case Stage 2's same-domain imposter has to survive.

## Cost ledger

| experiment | projected node-hours | actual | slurm job(s) | status |
|---|---|---|---|---|
| overnight_exp1a | 1.265 | — | 50191885 | submitted |
| overnight_exp1b | 0.656 | — | 50191886 | submitted |
| overnight_exp1c | 0.656 | — | 50191887 | submitted |
| overnight_exp245 | 0.300 | — | 50191888 | submitted |
| overnight_exp3 | 1.881 | — | 50191936 | submitted |
| **TOTAL** | **4.760** | **0.000** | | caps: 4.0/job, 12.0/batch |

## Provenance

Per-experiment run directories under `results/overnight_exp*/` — each with `config.json`, its `.sbatch`, per-arm `records.jsonl` (full prompts and raw responses) and `summary.json`. Job ids, node paths and the exact ingestion commands are in `results/overnight_manifest.json`.
