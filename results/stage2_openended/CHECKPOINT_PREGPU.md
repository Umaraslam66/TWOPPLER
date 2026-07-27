# OE-1 stop-before-GPU checkpoint — owner review

2026-07-27. **PILOT — pipeline validation on dev subjects; no research
conclusions.** Contract: `PILOT_SPEC.md` (Amendment 3, commit `7548bc3`).
Everything below ran on CPU and the flash-lite API only. **Nothing has
been submitted to Leonardo.** The Gemma job is written and waiting:
`stage2_oe1_gen.sbatch`, 85 prompts, 1 node, projected **0.0716
node-hours** against the 0.25 cap.

## The ask

Approve the Leonardo submission. After it: judge and embeddings on the
Gemma generations (same v2 judge config, ~$0.086), then
`OE1_PILOT_REPORT.md` with the C4 gate verdict, then STOP. Declining or
amending anything below is cheap now and expensive later.

## What you can review

- `prompt_samples.md` — one full rendered prompt per arm, same item.
- `build_summary.json` — all QA checks green (tail byte-identical across
  85 prompts, twin-free pass, grounding ≤ 2000 words, zero-info arms
  carry nothing, 0 surviving name variants).
- `gen/`, `judge/`, `embed/` — every completion, label, and cosine.

## What the flash-lite side showed (robustness arm — secondary per C3)

1. **Generation is clean.** 0 truncations at the 256-token cap, 0
   refusals, 0 meta-commentary. The zero-info arms are fluent on-topic
   answers — the leftover "Predict which answer they gave" preamble
   wording is inert on flash-lite. One era violation (a zeroinfo_named
   generation mentions 2019, post-test) is flagged and carried to the
   report. Untested on Gemma until the GPU phase.
2. **The pilot caught a real judge defect, now fixed and recorded.**
   gemini-3.5-flash spends hidden thinking against the output budget: 82
   of 85 WHY justifications truncated, and a probe flipped a label
   (DIFFERENT→UNCLEAR) between 256 and 1024 token budgets at temperature
   0 — the v1 labels were configuration-confounded and are kept only as
   a defect record (`judge/judgements.jsonl`, `thinking_budget_probe.json`).
   Fix: `thinking_budget=0`, 512 output tokens. Result: deterministic
   (3/3 repeat probe), 0 parse failures, 100% intact WHY lines, 13/85
   labels moved off v1. **These settings become pinned judge parameters
   in the bar-lock addendum.**
3. **Channel 1 (embeddings) separates own from imposter on all four
   candidates** — mpnet +0.066 (11/17 items), bge +0.044 (13/17), e5
   +0.013 (13/17), MiniLM +0.085 (11/17) — **but the declared
   topic-overlap risk is real:** similarity between the own arm's
   grounding text and the real answer correlates r = 0.58–0.75 with the
   own-arm score on every candidate. A chunk of channel 1's separation
   is topical, exactly as PILOT_SPEC §8.1 warned. Channel 2 is the
   load-bearing channel.
4. **Channel 2 (stance) does not separate on the robustness side:**
   twin_redacted 0.750 vs imposter 0.714 stance-match; zeroinfo_named is
   the highest arm at 0.875 (the name buys flash-lite real information —
   the contamination meter will say how much). Per-arm UNCLEAR rates
   differ (imposter 0.177 vs twin 0.059) — the C2.3 flag fires; the
   imposter tends to dodge the question in its donor's register, which
   the TVD view will capture. **So on flash-lite the two channels
   disagree — the C4 gate rides on the primary model, which is exactly
   what the GPU phase decides.** No gate language until then.
5. **S1 observation:** it removes appositive descriptors but misses
   free-standing intro sentences ("He was the former U.S. Department of
   State special advisor… now with the Atlantic Council" survives in
   redacted arms). Within its measured ~23-of-25 scope, symmetric
   between own and imposter, contamination meter is the declared
   backstop. Carried to the report.

## Costs

| item | spent | cap |
|---|---|---|
| API (gen $0.074 + judge v1 $0.078 + judge v2 $0.086) | **$0.238** | $0.40 |
| reserved for Gemma-side judge | ~$0.086 | (within the same cap) |
| GPU | **0** | 0.25 nh |
| GPU projection for the one job | 0.0716 nh | |

Projected session total if approved: ≈ $0.33 API, ≈ 0.07–0.10 nh.

## Decisions taken and disclosed (not silent)

- Judge endpoint price: AI Studio $0.75/$4.50 per Mtok (the endpoint the
  code bills against); OpenRouter/Vertex $1.50/$9.00 documented beside it.
- S1 applied to all five arms, not only redacted ones, to keep
  twin_named vs twin_redacted a one-factor contrast. Rounds 1–4 applied
  no S1 in render, so OE-1 prompts are not byte-comparable to round 4
  on this dimension.
- Zero-info preamble residue left as-is (spec froze the arm preambles);
  evidence above says it is harmless on flash-lite; the report checks
  Gemma's zero-info generations for the same.
- Item types are 10 subjective / 7 factual (two items had no hand
  classification and fell to the rule classifier; sources recorded).

## Ruling needed from you (not blocking the GPU go)

**H6 audit sheet:** built, blind, 120 rows, 60/60 balanced — but the
classifier has only ever run on the 6 dev subjects, because
confirmatory subjects are untouchable until the addendum freezes, and
this trust gate is itself a freeze precondition. B2.2's ≥10-subject ask
and the untouched discipline cannot both be satisfied. Either accept 6
subjects / 120 rows as clearing B2.2 (documented deviation) or amend
B2.2's subject count. The sheet works under either ruling.

---

## Resolution (owner, 2026-07-27)

1. **GPU GO granted**: submit `stage2_oe1_gen.sbatch`, then the
   Gemma-side judge + embeddings, then `OE1_PILOT_REPORT.md` with the
   C4 verdict applied mechanically. STOP at the report.
2. **B2.2 ruled as a two-part trust gate, documented deviation** — part
   1: the 6-subject / 120-row sheet is accepted for the freeze
   precondition (untouchability wins over the ≥10-subject count); part
   2 (new, binding): after the freeze, a second blind tranche of ≥ 60
   labels from ≥ 10 confirmatory subjects before any confirmatory H6
   scoring, same trust bar; failure halts H6 scoring pending rubric
   revision. Written into the addendum precondition list same day.
3. **S1's free-standing-intro miss acknowledged** — including that it
   identifies the imposter DONOR in at least one dev case (the
   blog-naming line). Symmetric across arms, contamination meter is the
   backstop, and "free-standing intro sentence handling" is added to
   the addendum's bar-lock open-questions list rather than dropped.
