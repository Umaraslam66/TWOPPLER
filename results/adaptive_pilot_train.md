# Stage 1E adaptive elicitation — TRAINING-SPLIT PILOT

**Label: TRAINING-SPLIT PILOT — for bar-setting only. No confirmatory claims. The confirm split has not been built or touched.**

Date: 2026-07-24. Spec: PREREGISTRATION_AMENDMENT_1.md section A6. Model: Gemma-4-31B-it (vLLM 0.25.1, TP=4, bf16, temperature 0), twin variant v2, same parser and scoring as the Stage 1 gate.

## Split

- 150 persons, seed 44, drawn from 130,303 cleaned RIASEC respondents after removing the seed-42 draw of 520 (pilot1 + gate) and the seed-43 pilot2 draw of 50.
- **Disjointness proof:** checked every records.jsonl under results/ (16 run directories, 570 distinct persons already used). Overlap with the training split = 0. DISJOINT.

## What each arm is

- **baseline** — demographics only, no interest items (k = 0).
- **random** — per-person seeded reveal order.
- **fixed** — one global order, chosen by greedy forward selection with ridge regression on this training split's raw answers. No model was used to pick it.
- **adaptive** — before each reveal the twin states a 1–5 probability distribution for every item it has not seen; the item it is least sure about (highest entropy) is revealed next.
- **imposter** — the same reveal positions as random, but the whole profile belongs to a different person in this split (seeded derangement, never self-paired). The answers being predicted are still the real person's.

## TIPI MAE lift over the demographics-only baseline

Higher is better. Lift = baseline mean absolute error − arm mean absolute error, averaged over persons, with a 95% t interval and a paired t-test across the 150 persons.

| k | random | fixed | adaptive |
|---|---|---|---|
| 1 | -0.005 [-0.022, +0.012] p=0.57 | +0.014 [-0.007, +0.035] p=0.18 | -0.006 [-0.023, +0.010] p=0.45 |
| 2 | -0.001 [-0.021, +0.019] p=0.92 | +0.027 [+0.004, +0.050] p=0.024 | +0.004 [-0.015, +0.024] p=0.65 |
| 4 | +0.001 [-0.020, +0.023] p=0.92 | +0.060 [+0.032, +0.088] p=4.3e-05 | +0.016 [-0.008, +0.040] p=0.19 |
| 8 | +0.006 [-0.020, +0.033] p=0.64 | +0.070 [+0.040, +0.100] p=1.1e-05 | +0.030 [+0.002, +0.057] p=0.035 |
| 12 | +0.027 [+0.000, +0.053] p=0.047 | +0.079 [+0.047, +0.112] p=2.9e-06 | +0.052 [+0.023, +0.081] p=0.00047 |
| 16 | +0.040 [+0.012, +0.068] p=0.0056 | +0.080 [+0.047, +0.112] p=3.4e-06 | +0.061 [+0.030, +0.093] p=0.00018 |
| 20 | +0.049 [+0.018, +0.079] p=0.0019 | +0.088 [+0.053, +0.122] p=1.4e-06 | +0.070 [+0.038, +0.102] p=2.5e-05 |

## Imposter-adjusted lift (own minus imposter, matched k)

Amendment A1: the number that isolates person-specific signal. Positive = the real profile beats a stranger's profile at the same reveal budget. The imposter mirrors the **random** arm's reveal positions, so random-vs-imposter is the exactly matched contrast; the other two columns share the budget but not the item choice.

| k | random − imposter | fixed − imposter | adaptive − imposter |
|---|---|---|---|
| 1 | +0.049 [+0.016, +0.082] p=0.0041 | +0.068 [+0.032, +0.104] p=0.00026 | +0.048 [+0.010, +0.085] p=0.013 |
| 2 | +0.054 [+0.017, +0.090] p=0.0044 | +0.082 [+0.043, +0.120] p=4.4e-05 | +0.059 [+0.020, +0.098] p=0.0031 |
| 4 | +0.040 [+0.001, +0.079] p=0.045 | +0.099 [+0.058, +0.139] p=3.9e-06 | +0.055 [+0.014, +0.095] p=0.0082 |
| 8 | +0.056 [+0.014, +0.099] p=0.01 | +0.120 [+0.077, +0.163] p=1.6e-07 | +0.080 [+0.038, +0.121] p=0.00022 |
| 12 | +0.063 [+0.019, +0.107] p=0.005 | +0.116 [+0.071, +0.161] p=1.2e-06 | +0.089 [+0.046, +0.132] p=7.6e-05 |
| 16 | +0.079 [+0.032, +0.125] p=0.00099 | +0.118 [+0.070, +0.166] p=2.8e-06 | +0.100 [+0.054, +0.146] p=3.3e-05 |
| 20 | +0.096 [+0.050, +0.143] p=6.5e-05 | +0.136 [+0.089, +0.182] p=4.7e-08 | +0.118 [+0.073, +0.163] p=6.2e-07 |

## Imposter arm's own lift over baseline

How much a stranger's profile helps. If this is positive, part of the raw lift is generic-population knowledge, not person-specific signal.

| k | imposter − baseline |
|---|---|
| 1 | -0.054 [-0.089, -0.019] p=0.0027 |
| 2 | -0.055 [-0.092, -0.018] p=0.0041 |
| 4 | -0.039 [-0.077, -0.001] p=0.047 |
| 8 | -0.050 [-0.091, -0.009] p=0.017 |
| 12 | -0.037 [-0.079, +0.006] p=0.091 |
| 16 | -0.038 [-0.086, +0.009] p=0.11 |
| 20 | -0.048 [-0.095, -0.001] p=0.046 |

## Policy contrasts (the A6 confirmatory shapes, pilot values only)

Primary contrast in A6 is adaptive vs random at matched k; secondary is adaptive vs best fixed.

| k | adaptive − random | adaptive − fixed | fixed − random |
|---|---|---|---|
| 1 | -0.001 [-0.021, +0.019] p=0.9 | -0.021 [-0.044, +0.002] p=0.079 | +0.019 [+0.001, +0.038] p=0.037 |
| 2 | +0.005 [-0.017, +0.028] p=0.63 | -0.022 [-0.047, +0.002] p=0.072 | +0.028 [+0.005, +0.051] p=0.019 |
| 4 | +0.015 [-0.008, +0.038] p=0.21 | -0.044 [-0.068, -0.020] p=0.00046 | +0.059 [+0.034, +0.084] p=8.4e-06 |
| 8 | +0.023 [-0.003, +0.050] p=0.079 | -0.040 [-0.063, -0.018] p=0.00058 | +0.064 [+0.037, +0.090] p=4.9e-06 |
| 12 | +0.026 [+0.002, +0.050] p=0.038 | -0.028 [-0.048, -0.007] p=0.009 | +0.053 [+0.028, +0.078] p=4.3e-05 |
| 16 | +0.021 [-0.001, +0.043] p=0.064 | -0.019 [-0.039, +0.001] p=0.067 | +0.039 [+0.017, +0.061] p=0.00054 |
| 20 | +0.021 [+0.000, +0.043] p=0.047 | -0.018 [-0.037, +0.001] p=0.068 | +0.039 [+0.018, +0.061] p=0.00043 |

## Raw TIPI MAE per arm

| k | baseline | random | fixed | adaptive | imposter |
|---|---|---|---|---|---|
| 1 | 1.523 | 1.528 | 1.509 | 1.529 | 1.577 |
| 2 | 1.523 | 1.524 | 1.496 | 1.519 | 1.578 |
| 4 | 1.523 | 1.522 | 1.463 | 1.507 | 1.562 |
| 8 | 1.523 | 1.517 | 1.453 | 1.494 | 1.573 |
| 12 | 1.523 | 1.497 | 1.444 | 1.471 | 1.560 |
| 16 | 1.523 | 1.483 | 1.444 | 1.462 | 1.561 |
| 20 | 1.523 | 1.475 | 1.435 | 1.453 | 1.571 |

## Plain-language read of the shape

- Random reveals move the lift from -0.005 at k=1 to +0.049 at k=20. The gate's full-information number (all 48 items, n=500) was +0.095, so k=20 recovers roughly 51% of it.
- Order matters more than budget. At k=20 the fixed order reaches +0.088 and adaptive +0.070, against random's +0.049 — but see caveat 1 about the fixed order.
- Adaptive beats random from k=8 onward and the gap is flat at about +0.02 from k=12 on. It does not close on the fixed order at any k.
- Cost asymmetry worth naming: the adaptive policy spent 126,000 model calls to place its 20 questions; the fixed order spent 10,500 and a few seconds of CPU regression. Adaptive is 12x the compute for a lower number in this pilot.
- The imposter arm's own lift over baseline runs -0.055 to -0.037. Anything the imposter earns is generic knowledge, not knowledge of the person.

## Read this before setting any bar

**1. The `fixed` arm's advantage here is inflated, and the amount is unknown.** Its item order was chosen using these same 150 people's TIPI answers, then scored on those same 150 people. Re-deriving the order on two disjoint halves of 75 gives orders that share only 10/20 items when pure chance would give 8.3. So the selection is mostly noise at this sample size, and a good part of the `fixed` column is the order having been fitted to this sample. The confirm run applies a frozen order to people who had no say in picking it — that is the honest test. **Do not set the adaptive-vs-fixed bar from the numbers in this pilot.**

**2. `adaptive` vs `random` is clean.** Neither policy used any outcome data to pick items: random is a per-person seeded shuffle, adaptive is chosen by the model at run time. The A6 primary contrast is therefore the one number here that is not exposed to the bias in point 1.

**3. The imposter is worse than knowing nothing.** Its lift over the demographics-only baseline is negative at every k (about −0.04 to −0.055). A coherent profile belonging to the wrong person actively misleads the twin. Consequence: own-minus-imposter is *larger* than own-minus-baseline here, the opposite of the usual direction. The conservative, binding number is the lift over the baseline; treat the imposter-adjusted column as the generous one.

**4. Sample and multiplicity.** n=150, 7 checkpoints, several contrasts per checkpoint. Everything here is a point estimate for sizing a bar, not a test.

## How the adaptive policy actually chose (diagnostic)

The model states probabilities in round numbers, so candidates often share the exact same entropy. In 51.5% of the 3,000 reveal decisions the top entropy was tied, with 3.0 candidates tied on average (worst case 37). Those reveals were decided by the pre-registered tie-break (lowest item index), not by uncertainty. Mean top entropy was 1.465 nats against a 1.609 maximum, and the mean spread between the most and least uncertain candidate was 0.809 nats — a narrow band. Read the adaptive arm's numbers with this in mind.

## Call and cost ledger

- Static arms (baseline, random, fixed, imposter): 33,000 completions, 0 missing.
- Adaptive arm: 10,500 predictions + 115,500 uncertainty calls (10 unparseable).
- Total completions: 159,000.
- Projected 1.176 node-hours for the two production jobs; actual 1.0787 node-hours all in — static 0.3014 + adaptive 0.6667 + pre-launch smoke 0.1106. Hard cap was 4.0 node-hours.

## Fixed order (for the record)

Ridge lambda 100.0, 5-fold out-of-fold MAE on 150 persons: 1.4419 with demographics only, 1.3334 after all 20 items.

`S6 C1 S4 A3 R2 A5 I1 E5 S1 A7 I2 I4 R5 E7 E2 R7 S5 C4 R6 E1`

## Provenance

Run directory: `results/adaptive_train_20260724-210916` — per-arm `records.jsonl` (full prompts and raw responses) and `summary.json`, plus `split.json`, `fixed_order.json`, `imposter_pairs.json`, `reveal_orders.json`, `projection.json`, `ledger.json`.
