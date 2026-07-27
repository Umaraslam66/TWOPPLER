# Fallback design sketch — the open-ended track

**Status: design sketch, NOT an amendment, NOT adopted.** Pre-written on
owner direction (2026-07-27) so that if round 4's kill rule fires
(zero-information accuracy ≥ 0.9 → forced choice is dead on this corpus,
no round 5 on any axis), the amendment draft the owner reviews starts
from this page instead of being designed under disappointment. If the
kill rule does not fire, this file remains a record of the contingency
and binds nothing.

## The task

The twin answers the held-out interview question **freely, in text** — no
options, nothing to pick. Same five arms as always (twin redacted/named,
zero-info redacted/named, imposter), same grounding budgets, same
chronological splits, same contamination meter. Every arm generates; the
scoring compares each generated answer to what the person actually said.

## Scoring, two channels

1. **Embedding similarity** between the generated answer and the real
   answer. Fixed, named, local embedding model (no API, no scored model
   involved); version pinned at bar-lock.
2. **Stance/entailment check**: a judge model classifies whether the
   generated answer takes the same position as the real answer
   (same / different / unclear), on a frozen rubric with its hash
   recorded. The judge comes from the generator-side family and is
   **never a scored model**. Note the standing tension: the A3
   robustness scorer is gemini-3.5-flash-lite, so the judge must be a
   *different* Gemini version — or the overlap is declared beside every
   robustness number it touches (same clause as B10.3). Named at
   amendment time.

## The primary metric is relative, by design

**Own-twin minus imposter-twin** similarity / stance-match, per
Amendment 1 A1. Both arms are scored by the identical judge on the
identical items, so the judge's absolute biases (verbosity preference,
topic priors, generosity) cancel in the difference. Zero-info lift is
reported alongside, as always. Both scored models (Gemma primary,
flash-lite robustness) are evaluated identically; B8's dual-level rule
applies (individual lift beside population-level TVD over stance
categories).

## Known weaknesses, stated up front

- **Soft metric.** No more "picked the real answer" crispness; the
  deliverable becomes a difference in continuous scores, harder to
  narrate and easier to over-read. Effect sizes with CIs, never bare
  means.
- **Judge sensitivity.** Stance classification by an LLM inherits its
  blind spots; mitigated (not removed) by the relative contrast, the
  frozen rubric, and a dev-subject spot-check of judge labels by the
  owner before any bar freezes.
- **Embedding similarity rewards topical overlap, not position.** On its
  own it would score a fluent on-topic wrong-position answer highly;
  that is why the stance channel exists and why neither channel alone
  carries a claim.
- **Style and length confounds.** Generation length is capped and
  format-instructed identically across arms; residual style effects are
  symmetric across own and imposter arms by construction.
- **Ceiling harvest** (cross-interview self-consistency) becomes harder
  to compute on free text; it stays descriptive per A2.

## Validation gate before any bar

Before any confirmatory registration: on dev subjects, the instrument
must show own-twin > imposter-twin discrimination in the pre-registered
direction and the owner must spot-check ≥ 50 judge labels (same pattern
as the B2.2 trust gate). If the open-ended instrument cannot separate
own from imposter on dev subjects, Stage 2 pauses for a design review
rather than proceeding to a bigger hammer.

## What would be registered at amendment time

Judge model + version; embedding model + version; rubric text + hash;
generation caps; the H1/H6/H7 bars restated in similarity-difference
form; the kill-rule provenance (three forced-choice rounds, PILOT_REPORT
1–3) cited as the reason for the change. Costs logged per arm as
everywhere.
