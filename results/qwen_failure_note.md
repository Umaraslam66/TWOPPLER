# Why Qwen's twin shows negative lift (pilot2 diagnosis)

Read-only analysis of existing pilot2 records. Gemini v0 twin: +0.072 MAE lift;
Qwen3.6-27B: -0.088 (v0), -0.118 (v1), +0.003 (v2).

**Headline:** both models have basically the *same* baseline (Qwen 1.428 vs Gemini 1.438
MAE); the whole gap is the twin arm. When Qwen reads the interest profile it shifts every
prediction *downward* ~0.5 points, and because real TIPI answers skew high, that adds error.
Gemini uses the same profile without the downward drag.

## Hypothesis verdicts

**(a) Chat-template / formatting shift — NOT SUPPORTED (except a v2 quirk).**
Gemini-v0 and Qwen-v0 prompts are byte-identical on all 1000 cells (1.0000 match).
Qwen parses cleanly (0 parse failures). So negative lift is not a prompt/parsing artifact.
BUT v2 is genuinely broken by templating: Qwen emits only **32 unique probability strings
/500 twin** (21/500 baseline) — it copies a handful of canned distributions. That collapses
individuating signal and is why v2 lift ≈ 0, not why v0/v1 go negative.

**(b) Profile ignored — NOT SUPPORTED (the opposite).**
Qwen twin diverges from its own baseline on **61.4%** of cells (Gemini 47%, pilot1 ~39%).
Cross-person spread of predictions jumps from sd 0.43 (baseline) to 1.05 (twin). Twin moves
track the *semantically right* interest block (extraversion↔social/enterprising r=+0.52;
openness↔investigative/artistic r=+0.68). Qwen reads and uses the profile — that is exactly
why it goes wrong.

**(c) Demographics baseline unusually strong on Qwen — NOT SUPPORTED.**
Qwen baseline MAE 1.428 ≈ Gemini 1.438 — not stronger. Its per-group predicted means barely
move (all age brackets 4.27–4.36; it predicts ~the grand mean for everyone), so it is not
exploiting demographic stereotypes better. It just *hedges to the center*: |pred − item mean|
= 0.57 for Qwen baseline vs 1.21 for its twin, and it never once predicts 1 or 7. MAE rewards
that hedge, so the twin has a high bar and then makes things worse.

**(d) Genuine (harmful) use of individuating info — SUPPORTED. This is the cause.**
Adding interests shifts Qwen's mean prediction from 4.34 → **3.81** (true 4.41): a systematic
−0.52 downward move (Gemini's move is −0.01). Signed error by true value: Qwen twin is *better*
at low-true items (true=1: +1.32 vs baseline +2.19) but *worse* at high-true items
(true=6: −1.38 vs −1.02). Since real answers skew high (57% are ≥5), the downward bias hurts on
the majority. Among divergent cells the twin **hurts 53% / helps 42%**. Damage concentrates on
high-scoring / reverse-worded items (reverse-item lift −0.216 vs non-reverse +0.040; TIPI6
"Reserved, quiet" worst at −0.52). It also over-reaches to the extremes (13% of twin preds are
1/7 vs 0% baseline; truth is extreme only 26%).

**Mechanism (most likely, ranked #1):** scale anchoring. Every person's mean interest rating is
≤3.73 on the 1–5 interest scale (people dislike most listed activities). Qwen lets those low raw
numbers pull the 1–7 TIPI answer down: corr(person mean interest, twin mean TIPI) = **+0.45** for
Qwen vs **−0.07** for Gemini. Gemini extracts per-trait signal without importing the low-scale
anchor; Qwen imports it and drops everything ~half a point.

## Position / long-context proxy
Can't test position directly (fixed item order). Proxy: no primacy bias. Twin extraversion
(TIPI1) correlates most with the Artistic (+0.60), Social (+0.49), Enterprising (+0.39) blocks —
middle-and-late, semantically relevant — and weakly with early R (+0.11) / I (+0.14) and last
C (+0.10). Qwen attends by content, not by position; late blocks are used, irrelevant early ones
ignored. A clean test needs permuted block order — OUT OF SCOPE (new runs).

## What would settle residual ambiguity (all need new runs → OUT OF SCOPE now)
- Anchoring proof: re-run with interests as words (Enjoy/Neutral/Dislike) or rescaled to 1–7; if
  the downward shift vanishes, anchoring is confirmed.
- v2 canned distributions: vary temperature / format to test sampling vs prompt cause.
- Position: permuted interest-block order.

## Five most decisive numbers
1. Baselines equal: Qwen 1.428 vs Gemini 1.438 MAE → the gap is the twin arm, not the baseline.
2. Twin mean drops 4.34 → 3.81 (true 4.41); systematic move −0.52 (Gemini −0.01).
3. Anchoring: corr(mean interest, twin TIPI) = +0.45 (Qwen) vs −0.07 (Gemini); all persons ≤3.73.
4. Directional harm: twin better at true=1 (+1.32 vs +2.19) but worse at true=6 (−1.38 vs −1.02);
   divergent cells hurt 53% / help 42%.
5. Profile is used, not ignored: divergence 61.4%; cross-person sd 0.43→1.05; v2 only 32/500
   unique distributions (separate templating artifact).
