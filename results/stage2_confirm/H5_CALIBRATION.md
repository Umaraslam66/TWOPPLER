# H5 (calibration) — substituted analysis on the Stage 2 confirmatory records

**Read this line first. No verdict on registered H5 is claimed anywhere in
this file.** The registered estimator could not be run inside the cap. What
was run instead is a different quantity. Every number below is **exploratory**
and is labelled as such at the point of use, not only here.

Branch taken: **SUBSTITUTION** (not withdrawal). The substituted analysis is
coherent on the existing records — 303 usable confidence/correctness pairs on
the primary model, 313 on the robustness model — so there was no reason to
withdraw.

Written 2026-07-28. Analysis script `experiments/h5_calibration.py`, committed
at `98fd2d0` **before any result was computed** (scorers-before-results rule).

---

## (a) What was registered

> **Registered text, quoted verbatim** (PREREGISTRATION.md section 3, Stage 3
> pre-registered hypotheses):
>
> “**H5 (calibration):** twin confidence (self-consistency sampling: k = 10
> samples, agreement rate = confidence) is calibrated: ECE ≤ 0.10 on pooled
> predictions across Stages 2–3. Reliability diagrams reported regardless.”

> **Re-scope, quoted verbatim** (PREREGISTRATION_AMENDMENT_2.md B9.b):
>
> “Consequence for H5 (calibration), which was registered as pooled across
> Stages 2–3: **H5 is re-scoped to Stage 2 predictions.**”

So the target is: k = 10 self-consistency samples per prediction, agreement
rate used as the confidence, ECE computed over Stage 2 predictions, reliability
diagrams reported either way.

---

## (b) Why the registered estimator was not run — the projection

### The structural problem: on this record the registered confidence is a constant

Every confirmatory generation was produced at **temperature 0.0**, pinned on
both generators and asserted at run time:

- Primary model — `experiments/stage2_confirm_gen.sbatch` passes
  `--temperature 0.0`; the ingest sidecars record `"temperature": 0.0`.
- Robustness model — `experiments/stage2_confirm_gen_flashlite.py` refuses to
  start if the client temperature is not 0.0 (`"client temperature is not
  0.0"`).

Temperature 0.0 is greedy decoding: the same prompt returns the same string
every time. Draw k = 10 samples from that configuration and you get ten
identical answers, so the agreement rate is exactly 1.0 for **every** item. The
registered confidence is not noisy or low-powered on these records — it is
constant, and a constant confidence of 1.0 against a 0.73 success rate is a
fixed ECE of about 0.27 that measures the pinning, not the twin.

The consequence that matters for cost: the registered estimator **cannot reuse
a single existing generation**. Running it means re-generating at a temperature
above zero. That is a fresh run, not a re-analysis, and it cannot be trimmed by
recycling confirmatory output.

### The cost of running it properly

Unit costs are the confirmatory run's own measured throughput (report section
7, and `results/stage2_confirm/gen/gemma/node_hours_accounting.json`) — not a
vendor quote:

| unit cost | value | measured on |
|---|---|---|
| node-hours per primary-model generation | 0.6028 / 1,911 = **0.00031544** | `stage2_confirm/gen_gemma` |
| dollars per stance-judge call | $4.851384 / 3,822 = **$0.00126933** | `stage2_confirm/judge_r2` |
| dollars per robustness-model generation | $1.676161 / 1,911 = **$0.00087711** | `stage2_confirm/gen_flashlite` |

Cohort: **355** `twin_redacted` items (the registered twin arm, Stage-2 scope),
88 subjects.

**Primary model only — the cheapest honest version** (no retries, no canary, no
robustness model, one judge call per sample):

| line | arithmetic | result | cap | over by |
|---|---|---|---|---|
| generations needed | 355 × 10 | **3,550** | — | — |
| GPU | 3,550 × 0.00031544 | **1.1198 node-hours** | 0.2 | **5.60×** |
| API (judging all samples) | 3,550 × $0.00126933 | **$4.5061** | $0.50 | **9.01×** |

**With the two-model structure every other Stage 2 result carries** (robustness
model generated and both models' samples judged):

| line | arithmetic | result | cap | over by |
|---|---|---|---|---|
| API | $4.5061 + 3,550 × $0.00087711 + $4.5061 | **$12.1260** | $0.50 | **24.25×** |
| GPU | unchanged | **1.1198 node-hours** | 0.2 | 5.60× |

Both caps break on the cheapest version. That is the recorded justification for
the substitution below.

> **Owner cap, as issued** (2026-07-28 ruling, stop point iii): H5 runs as a
> calibration analysis over the existing Stage 2 records under **$0.50 API and
> 0.2 node-hours**; if it cannot fit, H5 is withdrawn with the same
> documented-deviation pattern as H2.

---

## (c) The substitution — deviation note

Written in the style of deviations D1–D4
(PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md). **The number in the D-series is
the owner's to assign; this file does not claim one.**

**H5-SUB** (2026-07-28, owner-directed) — the registered k = 10
self-consistency confidence is **not** computed. In its place, a graded signal
already attached to every confirmatory generation is mapped monotonically to a
[0, 1] confidence and calibrated against channel-2 stance correctness, at $0 on
CPU. The substituted estimator is reported as its own line and is **never
pooled with, averaged into, or presented as** the registered one. No pass/fail
on registered H5 follows from it. The registered estimator's projected cost
(section b) is the reason on the record.

### What the substituted estimator is, exactly

**Outcome (correctness):** the channel-2 stance label. `SAME` → 1,
`DIFFERENT` → 0, `UNCLEAR` → **excluded**.

> **Frozen handling rule, quoted verbatim**
> (PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument parameter 6, adopting
> PREREGISTRATION_AMENDMENT_3.md C2.3):
>
> “UNCLEAR items are excluded from the stance-match rate's denominator; every
> arm's UNCLEAR rate is always reported beside its stance-match rate”

Exclusions are counted, never imputed — full table in section (d).

**Signal A (owner-directed primary):** the channel-1 embedding cosine between
the generated answer and the real answer, pinned mpnet
(`sentence-transformers/all-mpnet-base-v2` @ `e8c3b32…`).

> **Limitation, stated before any number that uses it.** The cosine needs the
> real answer to exist. It is therefore **not** a confidence a deployed twin
> could state, and calibrating it does not answer the deployment question H5
> was written to ask ("can a twin report trustworthy confidence in its own
> predictions?"). What it measures is cross-channel agreement: channel 1's
> graded score, mapped to a probability, against channel 2's binary verdict.

**Signal B (secondary, exploratory, non-oracle):** prompt-perturbation
agreement — the cosine between the twin's `twin_redacted` answer and its own
`twin_named` answer to the same item, both encoded by the same pinned model.
Two generations of one item that differ only in whether the subject's name was
shown. This is the closest thing on this record to the registered "agreement
rate over k samples" (k = 2 pseudo-samples, produced by a prompt perturbation
rather than by temperature), and unlike signal A it needs no access to the real
answer. It is still not the registered estimator. Computed on CPU with the
pinned instrument; cached at `results/stage2_confirm/h5/perturbation_cosines.jsonl`.

**The monotone map (declared here, inherited from nothing):**

- **Platt** — `p = sigmoid(a·x + b)`, fit by Newton on Platt's smoothed
  targets. Monotone increasing whenever `a > 0`; the fitted `a` is reported so
  a decreasing fit cannot hide. **PRIMARY MAP.**
- **Isotonic** — pool-adjacent-violators, non-parametric monotone. **SECONDARY.**

**Fitting hygiene — the headline never comes from a map that saw its own
evaluation rows.** The 88 subjects are split in two by a seeded shuffle
(**seed 20260728**; `sorted(subject_ids)` then `Random(seed).shuffle`, first
half = fold A, 44 / 44). The fold-A map is fit on fold A and applied to fold B,
and vice versa, so **every item is scored by a map that never saw its
subject**. That cross-fit number is the headline. The fit-on-everything number
is computed too and carries the label **NAIVE** wherever it appears. The split
is on subjects, never items — two items from one person are not independent.

**Binning.** No binning was ever frozen for H5. Both are reported and neither
is privileged: **equal-width** (10 fixed bins on [0, 1]) and **equal-mass** (10
bins of equal count). Said out loud rather than chosen quietly.

**Uncertainty.** Subject-clustered percentile bootstrap, B = 10,000, seed
20260728. Resampling is over subjects, not items.

**ECE is gameable — read AUC and Brier beside it.** A predictor that always
states the base rate has an ECE of **0.0000** on this data and knows nothing.
That reference number is computed and printed beside every headline, as is AUC
(does the signal separate right from wrong at all?) and the Brier score of the
constant-base-rate predictor (does the mapped confidence beat "just say the
base rate"?). A low ECE with an AUC near 0.5 is a well-calibrated way of
knowing nothing.

---

## (d) Results

**All numbers in this section are EXPLORATORY, under the substitution.** Scope:
Stage 2 confirmatory records, per B9.b.

### UNCLEAR exclusions, all arms, both models

| model | arm | judged rows | usable | UNCLEAR excluded | UNCLEAR rate |
|---|---|---|---|---|---|
| Gemma-4-31B-it | `twin_redacted` **(primary)** | 355 | **303** | **52** | 0.1465 |
| Gemma-4-31B-it | `twin_named` | 355 | 311 | 44 | 0.1239 |
| Gemma-4-31B-it | `zeroinfo_redacted` | 355 | 323 | 32 | 0.0901 |
| Gemma-4-31B-it | `zeroinfo_named` | 355 | 323 | 32 | 0.0901 |
| Gemma-4-31B-it | `imposter_redacted` | 355 | 250 | 105 | 0.2958 |
| Gemma-4-31B-it | `h7_twin_redacted` | 136 | 107 | 29 | 0.2132 |
| gemini-3.5-flash-lite | `twin_redacted` **(primary)** | 355 | **313** | **42** | 0.1183 |
| gemini-3.5-flash-lite | `twin_named` | 355 | 316 | 39 | 0.1099 |
| gemini-3.5-flash-lite | `zeroinfo_redacted` | 355 | 309 | 46 | 0.1296 |
| gemini-3.5-flash-lite | `zeroinfo_named` | 355 | 326 | 29 | 0.0817 |
| gemini-3.5-flash-lite | `imposter_redacted` | 355 | 265 | 90 | 0.2535 |
| gemini-3.5-flash-lite | `h7_twin_redacted` | 136 | 106 | 30 | 0.2206 |

No rows carried any label other than SAME / DIFFERENT / UNCLEAR, so nothing was
dropped for a reason other than the frozen rule.

### Headline — primary arm `twin_redacted`, signal A, Platt map

| model | fit | n | subjects | base rate | ECE (equal-width) | 95% CI | ECE (equal-mass) | 95% CI | AUC |
|---|---|---|---|---|---|---|---|---|---|
| Gemma-4-31B-it **(primary)** | **held out (cross-fit)** | 303 | 88 | 0.7294 | **0.0861** | [0.0475, 0.1452] | **0.0939** | [0.0713, 0.1558] | **0.518** |
| Gemma-4-31B-it | NAIVE (fit = eval) | 303 | 88 | 0.7294 | 0.0108 | — | 0.0572 | — | 0.577 |
| gemini-3.5-flash-lite (robustness) | **held out (cross-fit)** | 313 | 88 | 0.7796 | **0.0594** | [0.0415, 0.1142] | **0.0660** | [0.0604, 0.1431] | **0.643** |
| gemini-3.5-flash-lite | NAIVE (fit = eval) | 313 | 88 | 0.7796 | 0.0206 | — | 0.0651 | — | 0.656 |

**Read the AUC column before the ECE column.** On the primary model the AUC is
**0.518** — a coin flip. The mapped confidence barely separates the answers
that were judged right from the ones judged wrong. The robustness model does
better (0.643) but is still far from a usable ranking.

**Does the confidence beat "just say the base rate"?** No, on either model:

| model | held-out Brier | Brier of the constant base-rate predictor | ECE of the constant base-rate predictor |
|---|---|---|---|
| Gemma-4-31B-it | 0.2059 | **0.1974** | 0.0000 |
| gemini-3.5-flash-lite | 0.1738 | **0.1719** | 0.0000 |

Out of sample the mapped confidence is **slightly worse** than a constant
predictor that always states the base rate, on both models. And that constant
predictor has an ECE of exactly zero. This is the concrete demonstration of why
the ECE numbers above cannot be read as an achievement on their own.

### Held-out vs naive — the hygiene, shown on our own data

| model | map | held-out ECE (equal-width) | NAIVE ECE (equal-width) |
|---|---|---|---|
| Gemma-4-31B-it | Platt | 0.0861 | 0.0108 |
| Gemma-4-31B-it | isotonic | 0.0785 | **0.0000** |
| gemini-3.5-flash-lite | Platt | 0.0594 | 0.0206 |
| gemini-3.5-flash-lite | isotonic | 0.0649 | **0.0000** |

Isotonic regression fit on all the data returns each bin's own empirical
frequency, so its fit-on-everything ECE is **exactly 0.0000** — a perfect score
that means nothing at all. Anyone reporting the naive column would be reporting
their own curve-fitting back to themselves. Held out, the same map lands
between 0.065 and 0.079. (The bootstrap CI on a naive number is not quoted: the
bootstrap resamples evaluation rows without refitting, so it does not bracket a
statistic that is an artifact of the fit.)

### Secondary map — isotonic, primary arm, signal A

| model | fit | ECE (equal-width) | ECE (equal-mass) | AUC |
|---|---|---|---|---|
| Gemma-4-31B-it | held out (cross-fit) | 0.0785 | 0.1162 | 0.532 |
| gemini-3.5-flash-lite | held out (cross-fit) | 0.0649 | 0.0828 | 0.644 |

The two binning schemes disagree by enough to matter on the primary model
(0.0785 vs 0.1162 — one side of 0.10, then the other). That is exactly why both
are reported and why neither is called the number.

### Signal B — prompt-perturbation agreement (non-oracle, exploratory)

Primary arm `twin_redacted`, held out (cross-fit):

| model | map | ECE (equal-width) | ECE (equal-mass) | AUC | Platt slope, fold A / fold B |
|---|---|---|---|---|---|
| Gemma-4-31B-it | Platt | 0.0762 | 0.0922 | **0.427** | +1.375 / **−1.514** |
| Gemma-4-31B-it | isotonic | 0.1190 | 0.1074 | 0.435 | — |
| gemini-3.5-flash-lite | Platt | 0.0561 | 0.1046 | 0.589 | +6.629 / +1.427 |
| gemini-3.5-flash-lite | isotonic | 0.1097 | 0.0917 | 0.579 | — |

**This is the most interesting row in the file and it is a null.** On the
primary model the perturbation-agreement signal has an AUC **below 0.5**, and
the declared monotone map fit as monotone *decreasing* on one of the two folds
(slope −1.514) and *increasing* on the other (+1.375). The relationship between
"the twin says the same thing under a prompt perturbation" and "the twin is
right" is not stable across halves of the subject pool — it flips sign. On the
robustness model the slope is positive on both folds and the AUC reaches 0.589,
which is weakly informative but far from usable.

The figure makes it visible: in the Gemma panel the fit-on-everything map
collapses to a **single point** at the base rate (the pooled Platt slope is
effectively zero), and the held-out curve slopes *downward* — more agreement,
slightly lower observed accuracy.

The reading, stated plainly and labelled exploratory: **the one
consistency-style confidence signal measurable on these records does not
predict correctness for the primary model.** That is not the registered
estimator, so it is not evidence against registered H5 — but it is the closest
available evidence about the mechanism H5 assumed, and it points the wrong way.

### Secondary arms (signal A, Platt, held out)

Reported for completeness; the registered arm is `twin_redacted`.

| model | arm | n | base rate | ECE (equal-width) | ECE (equal-mass) | AUC |
|---|---|---|---|---|---|---|
| Gemma-4-31B-it | `twin_named` | 311 | 0.7460 | 0.0923 | 0.1151 | 0.518 |
| Gemma-4-31B-it | `zeroinfo_redacted` | 323 | 0.5944 | 0.0559 | 0.0601 | 0.675 |
| Gemma-4-31B-it | `zeroinfo_named` | 323 | 0.6471 | 0.0839 | 0.1062 | 0.565 |
| Gemma-4-31B-it | `imposter_redacted` | 250 | 0.6040 | 0.0653 | 0.0923 | 0.633 |
| Gemma-4-31B-it | `h7_twin_redacted` | 107 | 0.6916 | 0.0767 | 0.0900 | 0.608 |
| gemini-3.5-flash-lite | `twin_named` | 316 | 0.7911 | 0.0261 | 0.0558 | 0.565 |
| gemini-3.5-flash-lite | `zeroinfo_redacted` | 309 | 0.6343 | 0.0165 | 0.0639 | 0.631 |
| gemini-3.5-flash-lite | `zeroinfo_named` | 326 | 0.7301 | 0.0325 | 0.0870 | 0.613 |
| gemini-3.5-flash-lite | `imposter_redacted` | 265 | 0.6566 | 0.0432 | 0.0512 | 0.664 |
| gemini-3.5-flash-lite | `h7_twin_redacted` | 106 | 0.7642 | 0.0497 | 0.0827 | 0.588 |

Two things about the shape of this table.

First, a cross-check that passed: every base rate here equals the
corresponding stance-match rate in the confirmatory report's per-arm table
(section 6) to four decimals — 0.7294, 0.7796, 0.5944, and the rest. The two
files are reading the same records the same way.

Second, and this is a warning not a result: the **zero-information** arms
calibrate at least as well as the twin arms, and on the primary model
`zeroinfo_redacted` has the best AUC of any arm (0.675). A confidence signal
that ranks an ungrounded baseline's answers better than a grounded twin's is
not measuring twin confidence. Do not read the ECE column across arms as a
comparison, though — the arms have base rates from 0.594 to 0.791, and ECE is
not comparable across different base rates. The arm contrast belongs to H1 and
is reported there.

### Reliability diagrams

Reported regardless, as the registration requires — under the substituted
estimator, and labelled as such on the figure itself.

- `results/stage2_confirm/h5/reliability_signal_A_cosine_to_real.png` — both
  models, held-out cross-fit beside NAIVE, both binning schemes on each panel,
  marker size proportional to bin count.
- `results/stage2_confirm/h5/reliability_signal_B_perturbation_cosine.png` —
  same layout for the perturbation signal.
- Underlying bin tables: `results/stage2_confirm/h5/reliability_bins.csv`
  (every bin, every model/arm/signal/map/fit/scheme).
- Every summary number: `results/stage2_confirm/h5/calibration_summary.csv` and
  `results/stage2_confirm/h5/h5_numbers.json`.

What the diagrams show, in words: the mapped confidence is **compressed**. On
the primary model 67% of items land in two equal-width bins (0.70–0.83), and
the curve sits well above the diagonal at the low end — where the map says 0.45
the twin is actually right 78% of the time. The twin is not over-confident; the
signal simply has almost no spread that tracks correctness.

Primary model, held-out cross-fit, equal-width bins:

| bin | n | weight | mean confidence | observed rate | gap |
|---|---|---|---|---|---|
| 0.356–0.398 | 2 | 0.007 | 0.3767 | 0.5000 | +0.1233 |
| 0.410–0.490 | 9 | 0.030 | 0.4540 | 0.7778 | +0.3238 |
| 0.500–0.599 | 25 | 0.083 | 0.5497 | 0.7600 | +0.2103 |
| 0.600–0.699 | 64 | 0.211 | 0.6514 | 0.7500 | +0.0986 |
| 0.700–0.800 | 163 | 0.538 | 0.7596 | 0.6933 | −0.0663 |
| 0.800–0.827 | 40 | 0.132 | 0.8115 | 0.8250 | +0.0135 |

---

## (e) THE BAR

> **Frozen bar, quoted verbatim** (PREREGISTRATION.md section 3, H5):
>
> “**ECE ≤ 0.10** on pooled predictions across Stages 2–3.”
>
> Re-scoped to Stage 2 predictions by PREREGISTRATION_AMENDMENT_2.md B9.b.

**The bar is not applied. No pass/fail verdict on registered H5 is claimed.**

The reason, stated plainly:

1. The bar was registered for **one specific estimator** — k = 10
   self-consistency samples, agreement rate as the confidence.
2. That estimator was **not** computed. It is degenerate on records generated
   at temperature 0.0, and running it properly costs 5.6× the node-hour cap and
   9.0× the API cap (section b).
3. What was computed is a **different quantity**: an embedding cosine mapped
   through a fitted logistic, or a two-generation perturbation agreement. A bar
   frozen for one estimator does not transfer to another estimator just because
   both produce a number called ECE.

**Therefore, for the record: registered H5 is neither passed nor failed. It is
UNTESTED under the cap, with the substituted descriptive analysis reported in
its place.**

The arithmetic against 0.10, reported descriptively with the label attached
because the registration asks for the diagrams regardless:

- Primary model, primary arm, held out, Platt: ECE(equal-width) **0.0861**,
  ECE(equal-mass) **0.0939**. Both are numerically below 0.10. **This is not
  "H5 passed."** It is a substituted estimator, and both 95% CIs cross 0.10
  ([0.0475, 0.1452] and [0.0713, 0.1558]).
- The secondary isotonic map on the same rows gives ECE(equal-mass) **0.1162**
  — numerically above 0.10. The two declared maps land on opposite sides of the
  registered threshold. That alone would make any verdict a choice of map.
- A constant predictor that always states the base rate scores ECE **0.0000**
  on these same rows, with AUC 0.5 by construction. Any threshold on ECE alone
  is cleared by knowing nothing.
- The primary model's AUC is **0.518** and its held-out Brier (0.2059) is worse
  than the constant predictor's (0.1974).

Read together: even under the substitution, the honest descriptive summary is
that **the available confidence signals do not usefully rank the twin's
correct answers above its incorrect ones on the primary model.** Labelled
exploratory. It attaches to no registered bar.

### What is still owed on registered H5

If the owner ever wants the registered estimator, the requirement is a fresh
generation run at temperature > 0 (k = 10 per item), plus stance-judging the
samples: **1.12 node-hours and $4.51** on the primary model alone, **$12.13**
with the two-model structure. That is a cap decision, not an analysis decision.

---

## (f) Cost

| currency | spent | cap | breached |
|---|---|---|---|
| API dollars | **$0.00** | $0.50 | no |
| GPU node-hours | **0.00** | 0.2 | no |

No API call was made. No GPU job was submitted. Everything ran on local CPU:
the calibration arithmetic, the bootstrap, and the signal-B encoding with the
pinned mpnet model (already in the local cache, resolved and asserted against
the frozen revision by the confirmatory embed driver's own pin check).

Nothing was appended to `results/cost_log.jsonl` because there is nothing to
append.

---

## Provenance

| item | value |
|---|---|
| script | `experiments/h5_calibration.py` |
| script commit (pre-results) | `98fd2d04b6b498f8175906353d78e62f152655fb` |
| script sha256 | `0440346accd8e1ce…` |
| repo HEAD at analysis | `98fd2d04b6b498f8175906353d78e62f152655fb` |
| split seed | 20260728 (subjects, 44 / 44) |
| bootstrap | B = 10,000, seed 20260728, subject-clustered |
| bins | 10, equal-width and equal-mass, both reported |
| channel-1 instrument | `sentence-transformers/all-mpnet-base-v2` @ `e8c3b32edf5434bc2275fc9bab85f82640a19130`, pin asserted |
| channel-2 instrument | `gemini-3.5-flash`, rubric sha256 `ad050d1a75b038fc…`, temperature 0.0 |
| join key | `(model, prompt_sha256)`; 3,822 / 3,822 judge rows joined to a channel-1 cosine, zero unmatched |

Outputs, by sha256:

| file | sha256 |
|---|---|
| `results/stage2_confirm/h5/h5_numbers.json` | `2a4fc2dd7a2dd2b3…` |
| `results/stage2_confirm/h5/calibration_summary.csv` | `f4a7d4fbcd557b3c…` |
| `results/stage2_confirm/h5/reliability_bins.csv` | `45a8e4b5781f2ad2…` |
| `results/stage2_confirm/h5/perturbation_cosines.jsonl` | `8f94cf86b6d162cd…` |
| `results/stage2_confirm/h5/reliability_signal_A_cosine_to_real.png` | `c924767f9160a40f…` |
| `results/stage2_confirm/h5/reliability_signal_B_perturbation_cosine.png` | `c697d838626d8704…` |

Reproduce:

```
.venv/bin/python experiments/h5_calibration.py --compute-signal-b
uv run --no-project --with matplotlib --with numpy \
    python experiments/h5_calibration.py --figure
```
