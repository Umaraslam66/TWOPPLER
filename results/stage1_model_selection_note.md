# Stage 1 model selection rule

Date: 2026-07-24 (written before the open-model sweep was run, and before
Gemini pilot2 v1/v2 finished)

An open-model sweep (pilot2 design, same 50 persons, same prompts) will be run
on up to three dense open-weight models on Leonardo. The selection rule is
fixed now, before any sweep result is seen:

1. To qualify as the gate's primary simulation model, a model must show
   **positive pilot2 MAE lift** (twin beats demographics-only baseline), and
   its **winning variant must match Gemini's pilot2 winner in direction**
   (same variant comes out on top, both positive).
2. If one or more open models qualify, the best-lift qualifier becomes the
   **primary model for the gate and all later stages** (it is faster and
   cheaper than any API model), and gemini-3.5-flash-lite is demoted to a
   robustness check reported alongside.
3. If no open model qualifies, **Gemini stays primary** and the open-model
   failure to use individuating information is written up as a documented
   finding of Stage 1, not hidden.

This supersedes the "designated model" line of stage1_model_note.md only
through rule 2; the stop-on-disagreement principle stays: any ambiguous or
split outcome goes to the project owner before a gate run.

Qwen3.6-27B's already-observed pilot2 result (negative/flat lift on all
variants) means it does not qualify under rule 1 unless the diagnosis note
finds and fixes a pipeline artifact.
