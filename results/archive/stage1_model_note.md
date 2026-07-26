# Stage 1 model designation note

Date: 2026-07-24 (written before any gate data was collected)

The Stage 1 sanity gate (n = 500 held-out persons, RIASEC cross-domain, per
PREREGISTRATION.md) will be run with **gemini-3.5-flash-lite** as the
simulation model. This matches the model used in pilot 1 and pilot 2 — the
runs that select the twin-constructor variant — so the gate tests exactly the
configuration the pilots tuned.

The **Qwen3.6-27B replication of pilot 2** (same 50 persons, same items, same
prompts, same arms, run on Leonardo) is a **robustness check**: it asks
whether the winning variant is model-specific. It is reported alongside the
Gemini results and is not the gate, has no bearing on the gate's pass/fail,
and its numbers are labeled exploratory.

Decision rule, fixed in advance: if the two models disagree on which variant
wins pilot 2, no variant is picked and no gate is run until the disagreement
is reviewed and resolved by the project owner.
