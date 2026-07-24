# Stage 1E overnight batch (EXP1-EXP5) — TRAINING-SPLIT RESULTS

**Label: TRAINING/DERIVATION SPLIT ONLY — for bar-setting and go/no-go judgement. No confirmatory claims. The confirm split has not been built or touched.**

Date: 2026-07-25. Spec: PREREGISTRATION_AMENDMENT_1.md A6, extending results/adaptive_pilot_train.md. Model: Gemma-4-31B-it (vLLM, TP=4, temperature 0), twin variant v2, same parser and scoring as the Stage 1 gate.

Lift = demographics-only baseline MAE − arm MAE, averaged over persons, 95% t interval and paired t-test. Higher is better.

## What was run, and what was reused

| experiment | status | reused from the pilot |
|---|---|---|
| EXP1a | queued | nothing |
| EXP1b | ingested | nothing |
| EXP1c | running | nothing |
| EXP2 + EXP4 + EXP5 (shared static job) | ingested | results/adaptive_train_20260724-210916/baseline (k=0); results/adaptive_train_20260724-210916/random (k in 1,2,4,8,12,16,20); results/adaptive_train_20260724-210916/imposter (random imposter, k=12,20) |
| EXP3 | queued | EXP1a and EXP1b curves restricted to the first 100 persons of the train split |

## Headlines (computed from the ingested arms)

- **EXP2.** The order frozen on 2,000 disjoint people gives +0.074 at k=20 and peaks at +0.081 (k=36). It reaches 90% of that peak by **k=16**, and the whole stretch from k=16 to k=48 moves the number by +0.006 — past ~16 questions extra items buy almost nothing.
- **EXP2 selection bias.** The pilot's fixed order, picked on the same 150 people it was scored on, read +0.088 at k=20. The honest order reads +0.074. The gap, +0.014, is roughly what the selection bias was worth.
- **EXP4.** Random reveals climb from +0.049 at k=20 to +0.079 at k=48 (all 48 items, i.e. full information). The Stage 1 gate's all-48 number on 500 people was +0.095, so this lands in the right place. **k=20 already recovers 62% of the full-information lift** on a random order — the budget question is about the last third, not the first two.
- **Consistency check.** At k=48 both static arms reveal the same 48 items and differ only in the order of the lines. Their difference is +0.000 [-0.013, +0.014] p=0.97 — order stops mattering once everything is on the table, so the order effects at low k are real, not a rendering artifact.
- **EXP5.** A much more similar wrong person does **not** mislead differently. NN-imposter minus random-imposter is k=12: -0.003 [-0.054, +0.048] p=0.92; k=20: +0.006 [-0.049, +0.061] p=0.83. Both stay below the demographics-only baseline (NN is -0.039 at k=12), so a coherent profile belonging to the wrong person is harmful regardless of how well it matches. Reassuring for A1: the imposter baseline looks insensitive to how the donor is chosen.


## EXP1 — tie-break, scorer and elicitation grid

All three variants replace the pilot's lowest-item-index tie-break with a seeded random one. The pilot's tie-break was deciding 51.5% of reveals, and lowest-index is biased towards R-items.

### Residual tie rate

| variant | decisions | tied at top | mean tied | max tied |
|---|---|---|---|---|
| pilot (entropy, index tie-break) | 3,000 | 51.5% | 3.0 | 37 |
| EXP1a entropy + random | not ingested | | | |
| EXP1b EV-variance + random | 3,000 | 40.4% | 2.1 | 36 |
| EXP1c entropy + random + 0.05 grid | not ingested | | | |

### Lift over baseline, by variant

| k | pilot adaptive | EXP1a entropy+rand | EXP1b EV-var | EXP1c fine grid |
|---|---|---|---|---|
| 1 | -0.006 [-0.023, +0.010] p=0.45 | not ingested | -0.011 [-0.029, +0.006] p=0.19 | not ingested |
| 2 | +0.004 [-0.015, +0.024] p=0.65 | not ingested | -0.006 [-0.028, +0.016] p=0.6 | not ingested |
| 3 | n/a | not ingested | +0.019 [-0.007, +0.044] p=0.15 | not ingested |
| 4 | +0.016 [-0.008, +0.040] p=0.19 | not ingested | +0.024 [-0.002, +0.050] p=0.071 | not ingested |
| 5 | n/a | not ingested | +0.026 [-0.000, +0.052] p=0.052 | not ingested |
| 8 | +0.030 [+0.002, +0.057] p=0.035 | not ingested | +0.031 [+0.003, +0.059] p=0.032 | not ingested |
| 12 | +0.052 [+0.023, +0.081] p=0.00047 | not ingested | +0.047 [+0.018, +0.076] p=0.0017 | not ingested |
| 16 | +0.061 [+0.030, +0.093] p=0.00018 | not ingested | +0.065 [+0.034, +0.097] p=6.3e-05 | not ingested |
| 20 | +0.070 [+0.038, +0.102] p=2.5e-05 | not ingested | +0.070 [+0.038, +0.102] p=2.4e-05 | not ingested |

### Delta vs the pilot adaptive curve at matched k

Positive = the change helped.

| k | EXP1a − pilot | EXP1b − pilot | EXP1c − pilot |
|---|---|---|---|
| 1 | n/a | -0.005 [-0.021, +0.011] p=0.53 | n/a |
| 2 | n/a | -0.010 [-0.029, +0.009] p=0.28 | n/a |
| 4 | n/a | +0.008 [-0.013, +0.029] p=0.45 | n/a |
| 8 | n/a | +0.001 [-0.019, +0.021] p=0.92 | n/a |
| 12 | n/a | -0.005 [-0.026, +0.015] p=0.6 | n/a |
| 16 | n/a | +0.004 [-0.016, +0.024] p=0.69 | n/a |
| 20 | n/a | +0.000 [-0.016, +0.016] p=1 | n/a |

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
| 3 | +0.006 [-0.015, +0.028] p=0.57 | not ingested | n/a |
| 4 | +0.001 [-0.020, +0.023] p=0.92 | not ingested | n/a |
| 5 | +0.009 [-0.013, +0.032] p=0.41 | not ingested | n/a |
| 8 | +0.006 [-0.020, +0.033] p=0.64 | not ingested | n/a |
| 12 | +0.027 [+0.000, +0.053] p=0.047 | not ingested | n/a |
| 16 | +0.040 [+0.012, +0.068] p=0.0056 | not ingested | n/a |
| 20 | +0.049 [+0.018, +0.079] p=0.0019 | not ingested | n/a |
| 28 | +0.063 [+0.030, +0.096] p=0.0002 | not ingested | n/a |
| 36 | +0.067 [+0.035, +0.100] p=7.4e-05 | not ingested | n/a |
| 48 | +0.079 [+0.041, +0.116] p=5.3e-05 | not ingested | n/a |

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
| overnight_exp1a | 1.265 | — | 50191885 | queued |
| overnight_exp1b | 0.656 | 0.630 | 50191886 | ingested |
| overnight_exp1c | 0.656 | — | 50191887 | running |
| overnight_exp245 | 0.300 | 0.227 | 50191888 | ingested |
| overnight_exp3 | 1.881 | — | 50191936 | queued |
| **TOTAL** | **4.760** | **0.857** | | caps: 4.0/job, 12.0/batch |

## Provenance

Per-experiment run directories under `results/overnight_exp*/` — each with `config.json`, its `.sbatch`, per-arm `records.jsonl` (full prompts and raw responses) and `summary.json`. Job ids, node paths and the exact ingestion commands are in `results/overnight_manifest.json`.
