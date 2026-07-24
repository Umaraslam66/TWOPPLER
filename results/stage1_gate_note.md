# Stage 1 sanity gate — pre-launch note

Date: 2026-07-24. Written and committed BEFORE any gate call is made.
Approved by the project owner; launch awaits their explicit go.

## Arms

**Primary (the pre-registered gate):**
- Model: gemini-3.5-flash-lite (Google AI Studio API, temperature 0).
- Twin constructor: **variant v2** — profile (demographics + all 48 interest
  ratings as integers) then the held-out TIPI item answered as a probability
  distribution over 1–7; expected value scores MAE, argmax scores the
  accuracy secondaries.
- Baseline: identical pipeline, demographics only.
- Persons: the frozen GATE set — 500 persons, positions 21–520 of the
  seed-42 draw of 520 from the cleaned RIASEC data. Verified 2026-07-24:
  zero overlap with any person used in pilot 1 (n=20) or pilot 2 (n=50)
  across all 13 existing run directories.
- 10 TIPI items per person, one call per (person, item, arm) = 10,000 calls.
- Config: k=48, seed=42, max_output_tokens=120, v2 parser, exclusion rule
  for parse failures (drops the pair from both arms; counted).

**Variant selection rationale (fixed here, before gate data):** v1 had the
best pilot2 point estimate on Gemini (+0.148 vs v2's +0.091), but v2 was
chosen for (i) cross-model robustness — v2 is the only variant positive on
two models (Gemini p=.0001, Gemma-4 p=.007) — and (ii) mechanism: v1
amplifies the scale-anchoring failure on open models
(results/finding_scale_anchoring.md); its edge over v2 within Gemini has
overlapping CIs at n=50.

**Secondary (robustness, NOT the gate):**
- Gemma-4-31B-it on Leonardo (vLLM 0.25.1, TP=4, bf16, temperature 0),
  byte-identical prompts via the batchfile backend, same 500 persons, same
  items, same v2 scoring.

## Bar (frozen, from PREREGISTRATION.md)

The gate passes iff the PRIMARY arm shows twin lift over the
demographics-only baseline that is **positive and significant** (MAE lift
> 0; paired t-test p < .05 across the 500 persons; Wilcoxon reported
alongside). The primary metric is MAE lift per stage1_metric_note.md;
within-1 and exact-match are reported as secondaries, never alone.

## Pre-commitment on the secondary arm

- If the secondary (Gemma-4 + v2) shows positive AND significant MAE lift
  (same test, p < .05) at n=500: Gemma-4-31B-it + v2 becomes the primary
  simulation model for all later stages (speed + cost), with Gemini demoted
  to robustness checks.
- If not: Gemini stays primary and the open-model failure to use
  individuating information is a documented Stage 1 finding.
- The gate pass/fail verdict itself depends ONLY on the primary arm.

## Cost estimate

- Primary: 10,000 Gemini calls ≈ 5.4M input + ~0.5M output tokens ≈ **$3**
  at $0.30/$2.50 per M; ~15–30 min at the 1,000 RPM client guard.
- Secondary: one Leonardo debug-queue job, 10,000 prompts through one
  engine init ≈ **0.3–0.5 node-hours** of the remaining ~1,018.

## Provenance

Every number in the gate report will link to: this note, the run dirs
(records.jsonl with full prompts and raw responses), summary.json, and
cost_log.jsonl lines. Analysis code is frozen at the commit containing this
note; any post-hoc analysis will be labeled exploratory.
