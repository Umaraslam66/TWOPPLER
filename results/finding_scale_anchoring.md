# Finding: numeric scale anchoring in persona-conditioned prediction

Date: 2026-07-24. Status: Stage 1 finding (pilot2, n = 50 persons, exploratory
by design; selected effects to be confirmed at the gate). Provenance: pilot2
run dirs in results/ (Gemini `pilot2_v*_k48_20260724-14/16*`, Qwen and
Gemma-4 `*_leonardo-batch`), diagnosis in results/qwen_failure_note.md.

## The finding

When a persona profile contains ratings on one numeric scale (48 interest
items, 1–5) and the model must answer on a different numeric scale (TIPI
personality items, 1–7), open-weight models let the profile's raw numbers
leak into the answer scale. People's interest ratings average low (every
person's mean is <= 3.7/5), so the twin's 1–7 answers get dragged down, and
since 57% of true answers are >= 5, the twin does *worse* than a
demographics-only baseline that never sees a number.

## Evidence (v0 = interests as raw integers; MAE lift = baseline − twin, positive is good)

| Model | v0 lift | person-level corr(mean interest, twin prediction) | twin-minus-baseline mean shift |
|---|---|---|---|
| gemini-3.5-flash-lite | +0.072 | −0.09 | −0.01 |
| Qwen3.6-27B | −0.088 | **+0.53** | **−0.52** |
| Gemma-4-31B-it | −0.056 | **+0.28** | −0.04 |

- Qwen shows the full syndrome: strong correlation and a global downward
  shift (mean prediction 4.34 → 3.81 against a true mean of 4.41).
- Gemma-4 shows the correlation with a near-zero *net* shift — its anchoring
  is centered rather than a global drag, but still misallocates answers
  (negative lift).
- Gemini shows neither, and is the only model with positive v0 lift.
- Not an artifact: prompts are byte-identical across models, parse failures
  are zero everywhere, and both open models' baselines equal Gemini's
  (≈1.43 MAE), so the gap is entirely in the twin arm.
- Reasoning first (v1) amplifies the harm (Qwen −0.118, Gemma −0.062):
  verbalizing the low ratings strengthens the anchor.

## The fix and its effect (v3 = same prompt, ratings rendered as words)

Variant v3 renders each rating as a word ("Dislike" … "Enjoy") and removes
every digit from the interests block; everything else is byte-identical to
v0 (the demographics-only baseline prompt is literally unchanged).

| Model | v0 lift | v3 lift |
|---|---|---|
| Qwen3.6-27B | −0.088 | +0.002 |
| Gemma-4-31B-it | −0.056 | −0.016 |

Removing the numbers removes the harm in both models — a mechanism-confirmed
fix. It does not, by itself, produce positive lift: with words, both models
land at their baseline, meaning they no longer misuse the profile but still
fail to extract signal from it in point-prediction mode. (Gemma-4 does show
positive lift when asked for a probability distribution instead of a point
answer — v2, +0.085, p = .007 before any multiplicity correction — suggesting
the information is usable but not through a single forced integer.)

## Why this matters for anyone building persona agents

Persona and digital-twin systems routinely paste structured user data —
survey responses, star ratings, activity scores — into a prompt and then ask
the model for a rating, a score, or a prediction on some other scale. This
finding says the numeric context itself is not neutral: numbers in the
profile act as anchors on numbers in the output, in a direction and
magnitude that varies by model and can be large enough to make the grounded
agent *worse than an agent given no individual data at all* — while looking
perfectly well-behaved (fluent answers, valid format, plausible reasoning).
The failure is invisible without a zero-information baseline, which is why
lift-over-baseline, not raw accuracy, should be the default metric for
persona fidelity; and the cheap mitigation is to verbalize numeric ratings
(or otherwise separate the scales) before they enter the context.
