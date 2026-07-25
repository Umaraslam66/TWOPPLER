# Stage 1E overnight batch (EXP1-EXP5) — TRAINING-SPLIT RESULTS

**Label: TRAINING/DERIVATION SPLIT ONLY — for bar-setting and go/no-go judgement. No confirmatory claims. The confirm split has not been built or touched.**

Date: 2026-07-25. Spec: PREREGISTRATION_AMENDMENT_1.md A6, extending results/adaptive_pilot_train.md. Model: Gemma-4-31B-it (vLLM, TP=4, temperature 0), twin variant v2, same parser and scoring as the Stage 1 gate.

Lift = demographics-only baseline MAE − arm MAE, averaged over persons, 95% t interval and paired t-test. Higher is better.

## What was run, and what was reused

| experiment | status | reused from the pilot |
|---|---|---|
| EXP1a | ingested | nothing |
| EXP1b | ingested | nothing |
| EXP1c | ingested | nothing |
| EXP2 + EXP4 + EXP5 (shared static job) | ingested | results/adaptive_train_20260724-210916/baseline (k=0); results/adaptive_train_20260724-210916/random (k in 1,2,4,8,12,16,20); results/adaptive_train_20260724-210916/imposter (random imposter, k=12,20) |
| EXP3 | ingested | EXP1a and EXP1b curves restricted to the first 100 persons of the train split |

## Headlines (computed from the ingested arms)

- **EXP2.** The order frozen on 2,000 disjoint people gives +0.074 at k=20 and peaks at +0.081 (k=36). It reaches 90% of that peak by **k=16**, and the whole stretch from k=16 to k=48 moves the number by +0.006 — past ~16 questions extra items buy almost nothing.
- **EXP2 selection bias.** The pilot's fixed order, picked on the same 150 people it was scored on, read +0.088 at k=20. The honest order reads +0.074. The gap, +0.014, is roughly what the selection bias was worth.
- **EXP4.** Random reveals climb from +0.049 at k=20 to +0.079 at k=48 (all 48 items, i.e. full information). The Stage 1 gate's all-48 number on 500 people was +0.095, so this lands in the right place. **k=20 already recovers 62% of the full-information lift** on a random order — the budget question is about the last third, not the first two.
- **Consistency check.** At k=48 both static arms reveal the same 48 items and differ only in the order of the lines. Their difference is +0.000 [-0.013, +0.014] p=0.97 — order stops mattering once everything is on the table, so the order effects at low k are real, not a rendering artifact.
- **EXP1 tie-break.** Holding the scorer at entropy and swapping the pilot's lowest-index tie-break for a seeded random one costs -0.018 [-0.033, -0.004] p=0.014 at k=20. The index rule was *helping* — it was worth about +0.018, and roughly half of entropy's decisions are exact ties, so it was deciding half the questions.
- **EXP1 scorer.** Holding the tie-break at random, variance of the stated distribution beats entropy by +0.018 [+0.002, +0.034] p=0.027 at k=20 — it recovers exactly what the index crutch was providing, and it ties far less often.
- **EXP1 vs the A6 primary contrast (adaptive − random at k=20).** pilot entropy+index +0.021 [+0.000, +0.043] p=0.047; entropy+random +0.003 [-0.018, +0.024] p=0.76; EV-variance+random +0.022 [+0.002, +0.041] p=0.029; entropy+random+0.05 grid +0.004 [-0.017, +0.025] p=0.72. The pilot's edge does not survive an unbiased tie-break with entropy, but it does with EV-variance. Read as: use a scorer that discriminates, and never lean on an index tie-break.
- **EXP5.** A much more similar wrong person does **not** mislead differently. NN-imposter minus random-imposter is k=12: -0.003 [-0.054, +0.048] p=0.92; k=20: +0.006 [-0.049, +0.061] p=0.83. Both stay below the demographics-only baseline (NN is -0.039 at k=12), so a coherent profile belonging to the wrong person is harmful regardless of how well it matches. Reassuring for A1: the imposter baseline looks insensitive to how the donor is chosen.


## EXP1 — tie-break, scorer and elicitation grid

All three variants replace the pilot's lowest-item-index tie-break with a seeded random one. The pilot's tie-break was deciding 51.5% of reveals, and lowest-index is biased towards R-items.

### Residual tie rate

| variant | decisions | tied at top | mean tied | max tied |
|---|---|---|---|---|
| pilot (entropy, index tie-break) | 3,000 | 51.5% | 3.0 | 37 |
| EXP1a entropy + random | 7,200 | 45.0% | 2.4 | 39 |
| EXP1b EV-variance + random | 3,000 | 40.4% | 2.1 | 36 |
| EXP1c entropy + random + 0.05 grid | 3,000 | 47.9% | 2.8 | 40 |

### Lift over baseline, by variant

| k | pilot adaptive | EXP1a entropy+rand | EXP1b EV-var | EXP1c fine grid |
|---|---|---|---|---|
| 1 | -0.006 [-0.023, +0.010] p=0.45 | -0.005 [-0.024, +0.014] p=0.62 | -0.011 [-0.029, +0.006] p=0.19 | -0.016 [-0.037, +0.004] p=0.12 |
| 2 | +0.004 [-0.015, +0.024] p=0.65 | -0.011 [-0.033, +0.011] p=0.31 | -0.006 [-0.028, +0.016] p=0.6 | -0.002 [-0.024, +0.021] p=0.89 |
| 3 | n/a | +0.006 [-0.017, +0.029] p=0.62 | +0.019 [-0.007, +0.044] p=0.15 | -0.000 [-0.023, +0.023] p=1 |
| 4 | +0.016 [-0.008, +0.040] p=0.19 | +0.017 [-0.008, +0.041] p=0.19 | +0.024 [-0.002, +0.050] p=0.071 | +0.008 [-0.016, +0.033] p=0.49 |
| 5 | n/a | +0.014 [-0.011, +0.039] p=0.28 | +0.026 [-0.000, +0.052] p=0.052 | +0.013 [-0.012, +0.038] p=0.31 |
| 8 | +0.030 [+0.002, +0.057] p=0.035 | +0.020 [-0.006, +0.046] p=0.13 | +0.031 [+0.003, +0.059] p=0.032 | +0.020 [-0.008, +0.047] p=0.16 |
| 12 | +0.052 [+0.023, +0.081] p=0.00047 | +0.036 [+0.008, +0.064] p=0.011 | +0.047 [+0.018, +0.076] p=0.0017 | +0.038 [+0.008, +0.068] p=0.012 |
| 16 | +0.061 [+0.030, +0.093] p=0.00018 | +0.048 [+0.019, +0.078] p=0.0013 | +0.065 [+0.034, +0.097] p=6.3e-05 | +0.060 [+0.030, +0.089] p=0.0001 |
| 20 | +0.070 [+0.038, +0.102] p=2.5e-05 | +0.052 [+0.021, +0.083] p=0.0013 | +0.070 [+0.038, +0.102] p=2.4e-05 | +0.052 [+0.020, +0.085] p=0.0016 |

### Delta vs the pilot adaptive curve at matched k

Positive = the change helped.

| k | EXP1a − pilot | EXP1b − pilot | EXP1c − pilot |
|---|---|---|---|
| 1 | +0.002 [-0.013, +0.016] p=0.83 | -0.005 [-0.021, +0.011] p=0.53 | -0.010 [-0.028, +0.008] p=0.28 |
| 2 | -0.016 [-0.033, +0.002] p=0.091 | -0.010 [-0.029, +0.009] p=0.28 | -0.006 [-0.026, +0.014] p=0.55 |
| 4 | +0.001 [-0.018, +0.019] p=0.95 | +0.008 [-0.013, +0.029] p=0.45 | -0.007 [-0.030, +0.015] p=0.51 |
| 8 | -0.010 [-0.030, +0.010] p=0.34 | +0.001 [-0.019, +0.021] p=0.92 | -0.010 [-0.031, +0.011] p=0.35 |
| 12 | -0.016 [-0.034, +0.003] p=0.091 | -0.005 [-0.026, +0.015] p=0.6 | -0.014 [-0.033, +0.004] p=0.13 |
| 16 | -0.013 [-0.030, +0.004] p=0.14 | +0.004 [-0.016, +0.024] p=0.69 | -0.002 [-0.019, +0.015] p=0.83 |
| 20 | -0.018 [-0.033, -0.004] p=0.014 | +0.000 [-0.016, +0.016] p=1 | -0.018 [-0.034, -0.001] p=0.033 |

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
| 1 | +0.011 [-0.009, +0.031] p=0.28 | +0.014 [-0.007, +0.035] p=0.18 |
| 2 | +0.038 [+0.010, +0.066] p=0.0089 | +0.027 [+0.004, +0.050] p=0.024 |
| 3 | +0.039 [+0.010, +0.068] p=0.0086 | — |
| 4 | +0.041 [+0.011, +0.071] p=0.0079 | +0.060 [+0.032, +0.088] p=4.3e-05 |
| 5 | +0.032 [+0.000, +0.064] p=0.047 | — |
| 8 | +0.041 [+0.008, +0.074] p=0.015 | +0.070 [+0.040, +0.100] p=1.1e-05 |
| 12 | +0.060 [+0.024, +0.095] p=0.001 | +0.079 [+0.047, +0.112] p=2.9e-06 |
| 16 | +0.075 [+0.038, +0.111] p=8.8e-05 | +0.080 [+0.047, +0.112] p=3.4e-06 |
| 20 | +0.074 [+0.036, +0.112] p=0.00018 | +0.088 [+0.053, +0.122] p=1.4e-06 |
| 28 | +0.075 [+0.038, +0.112] p=0.00011 | — |
| 36 | +0.081 [+0.043, +0.120] p=4.8e-05 | — |
| 48 | +0.079 [+0.041, +0.117] p=6.9e-05 | — |

## EXP3 — selection ladder: does target-aware selection beat self-uncertainty?

n=100 (first 100 of the train split). Ladder rung (a) is EXP1's self-uncertainty policy restricted to these people — not rerun. Rung (b) scores each shortlisted item by how much the 10 TIPI target distributions are expected to move.

Node-side parse check before committing the run: 200/200 multi-target completions parsed (100.0%), bar was 95% — PASSED.

| k | (a) self-uncertainty (EXP1a) | (b) expected info gain | (b) − (a) |
|---|---|---|---|
| 1 | -0.005 [-0.028, +0.019] p=0.68 | -0.001 [-0.029, +0.027] p=0.95 | +0.004 [-0.020, +0.028] p=0.75 |
| 2 | -0.011 [-0.039, +0.017] p=0.43 | +0.002 [-0.027, +0.032] p=0.87 | +0.014 [-0.013, +0.040] p=0.32 |
| 3 | +0.005 [-0.025, +0.035] p=0.73 | +0.019 [-0.009, +0.048] p=0.18 | +0.014 [-0.014, +0.043] p=0.33 |
| 4 | +0.019 [-0.011, +0.049] p=0.21 | +0.026 [-0.004, +0.056] p=0.091 | +0.007 [-0.019, +0.032] p=0.6 |
| 5 | +0.016 [-0.015, +0.047] p=0.3 | +0.020 [-0.012, +0.051] p=0.22 | +0.003 [-0.023, +0.030] p=0.8 |
| 8 | +0.017 [-0.015, +0.048] p=0.29 | +0.024 [-0.011, +0.058] p=0.18 | +0.007 [-0.018, +0.032] p=0.59 |
| 12 | +0.035 [+0.001, +0.069] p=0.043 | +0.047 [+0.012, +0.083] p=0.0098 | +0.013 [-0.011, +0.036] p=0.3 |
| 16 | +0.045 [+0.012, +0.079] p=0.0087 | +0.064 [+0.026, +0.102] p=0.0012 | +0.019 [-0.005, +0.042] p=0.12 |
| 20 | +0.049 [+0.013, +0.085] p=0.0087 | +0.066 [+0.026, +0.106] p=0.0016 | +0.017 [-0.003, +0.037] p=0.091 |

Rung (c), one-step lookahead, was **not run**: it multiplies rung (b)'s cost by the shortlist size again and does not fit inside EXP3's 3.0 node-hour cap alongside (b).

## EXP4 — budget curve: where does the edge peak, where does it saturate?

The random arm reuses the pilot's completions at k in {1, 2, 4, 8, 12, 16, 20} and buys only {3, 5, 28, 36, 48}. The adaptive side is EXP1a.

| k | random | adaptive (EXP1a) | adaptive − random |
|---|---|---|---|
| 1 | -0.005 [-0.022, +0.012] p=0.57 | -0.005 [-0.024, +0.014] p=0.62 | +0.000 [-0.020, +0.020] p=0.98 |
| 2 | -0.001 [-0.021, +0.019] p=0.92 | -0.011 [-0.033, +0.011] p=0.31 | -0.010 [-0.032, +0.012] p=0.37 |
| 3 | +0.006 [-0.015, +0.028] p=0.57 | +0.006 [-0.017, +0.029] p=0.62 | -0.000 [-0.021, +0.021] p=0.98 |
| 4 | +0.001 [-0.020, +0.023] p=0.92 | +0.017 [-0.008, +0.041] p=0.19 | +0.015 [-0.008, +0.039] p=0.19 |
| 5 | +0.009 [-0.013, +0.032] p=0.41 | +0.014 [-0.011, +0.039] p=0.28 | +0.004 [-0.020, +0.029] p=0.72 |
| 8 | +0.006 [-0.020, +0.033] p=0.64 | +0.020 [-0.006, +0.046] p=0.13 | +0.014 [-0.010, +0.037] p=0.25 |
| 12 | +0.027 [+0.000, +0.053] p=0.047 | +0.036 [+0.008, +0.064] p=0.011 | +0.010 [-0.012, +0.032] p=0.38 |
| 16 | +0.040 [+0.012, +0.068] p=0.0056 | +0.048 [+0.019, +0.078] p=0.0013 | +0.008 [-0.016, +0.032] p=0.5 |
| 20 | +0.049 [+0.018, +0.079] p=0.0019 | +0.052 [+0.021, +0.083] p=0.0013 | +0.003 [-0.018, +0.024] p=0.76 |
| 28 | +0.063 [+0.030, +0.096] p=0.0002 | +0.067 [+0.035, +0.098] p=5.5e-05 | +0.003 [-0.016, +0.023] p=0.74 |
| 36 | +0.067 [+0.035, +0.100] p=7.4e-05 | +0.074 [+0.038, +0.109] p=6.5e-05 | +0.006 [-0.011, +0.024] p=0.49 |
| 48 | +0.079 [+0.041, +0.116] p=5.3e-05 | +0.075 [+0.037, +0.113] p=0.00014 | -0.003 [-0.017, +0.011] p=0.66 |

Reference: the Stage 1 gate's all-48-item lift on 500 people was +0.095.

## EXP5 — imposter gradient: does a MORE similar wrong person mislead less, or more?

Nearest-neighbour donors are drawn inside train-150 by cosine similarity on the 48 interest ratings (mean 0.9339, min 0.8343), never self-paired. Reveal positions mirror the random arm, exactly like the pilot's random imposter.

The gradient is real: the random imposter's mean cosine is 0.8378, so the nearest neighbour is +0.0961 more similar. 76 distinct people serve as NN donors for the 150.

| k | own (random arm) | NN imposter | random imposter | own − NN | own − random imp | NN − random imp |
|---|---|---|---|---|---|---|
| 12 | +0.027 [+0.000, +0.053] p=0.047 | -0.039 [-0.086, +0.007] p=0.099 | -0.037 [-0.079, +0.006] p=0.091 | +0.066 [+0.024, +0.108] p=0.0024 | +0.063 [+0.019, +0.107] p=0.005 | -0.003 [-0.054, +0.048] p=0.92 |
| 20 | +0.049 [+0.018, +0.079] p=0.0019 | -0.042 [-0.094, +0.009] p=0.11 | -0.048 [-0.095, -0.001] p=0.046 | +0.091 [+0.046, +0.135] p=0.0001 | +0.096 [+0.050, +0.143] p=6.5e-05 | +0.006 [-0.049, +0.061] p=0.83 |

Read: the pilot found a random stranger's profile is *worse than knowing nothing* (lift −0.04 to −0.055 over baseline). If the nearest neighbour is less harmful, similarity buys back some generic signal; if it is more harmful, a plausible-but-wrong profile is the more dangerous failure — which is the case Stage 2's same-domain imposter has to survive.

## Cost ledger

| experiment | projected node-hours | actual | slurm job(s) | status |
|---|---|---|---|---|
| overnight_exp1a | 1.265 | 0.970 | 50191885 | ingested |
| overnight_exp1b | 0.656 | 0.630 | 50191886 | ingested |
| overnight_exp1c | 0.656 | 0.648 | 50191887 | ingested |
| overnight_exp245 | 0.300 | 0.227 | 50191888 | ingested |
| overnight_exp3 | 2.817 | 2.089 | 50191936, 50197711 | ingested |
| **TOTAL** | **5.695** | **4.565** | | caps: 4.0/job, 12.0/batch |

## Provenance

Per-experiment run directories under `results/overnight_exp*/` — each with `config.json`, its `.sbatch`, per-arm `records.jsonl` (full prompts and raw responses) and `summary.json`. Job ids, node paths and the exact ingestion commands are in `results/overnight_manifest.json`.
