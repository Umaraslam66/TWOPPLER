# Stage 2 confirmatory launch plan

Status: **AWAITING THE OWNER'S EXPLICIT GO. Nothing below runs until it
is given.** Prepared 2026-07-28, the same day the bar-lock addendum was
adopted (commit `bcd1d51`) after parameter 5 passed its pre-committed
gate on the second tranche. Every bar quoted below is quoted verbatim
from a frozen document; everything marked [PLAN] is an operational
choice inside those bars, not a new rule. No confirmatory subject's
transcript is opened, rendered, or scored before the GO.

The one deliberately open governance slot: the H6/B3 parameters
(addendum, open on record). H6 is decoupled — its parameter spec is
being drafted separately and gates confirmatory **H6 scoring only**,
never this launch. Its part-2 audit tranche (≥ 60 labels, ≥ 10
confirmatory subjects, same trust bar) additionally gates H6 scoring
after the classifier first runs on confirmatory subjects.

## a. Subject draw

Provisional draw executed from committed pool metadata only:
`results/stage2_confirm_draw_provisional.json`, generator
`experiments/stage2_confirm_draw.py`, **seed 20260728**, byte-identical
on rerun (verified).

- **Eligibility rule** (same rule and file as the committed dev draw):
  `qualifies AND clean AND NOT ambiguous_identity` in
  `results/stage2_candidate_pool_v2.csv` → **578** (matches the dev
  draw's recorded `n_eligible`).
- **Dev subjects excluded by ID**, all six, C00292 included —
  intersection with the draw printed: **empty**.
- **Staff reserve (292) excluded by construction** — not in the
  clean/qualifying pool; additionally asserted: zero drawn rows carry
  staff evidence. Re-admission still gates on the owner's 20-dossier
  spot-check, which this plan does not touch.
- **Composition**: long-tail-biased **3:1** (the committed 90:30
  expression of the owner's mix decision) → drawn 105 long-tail / 35
  article, interleaved LT,LT,LT,A in draw order.
- **Priority** (addendum item 10, frozen): ≥ 4 dated dedup clusters
  drawn first — the pool is deep enough that **all 140 drawn subjects
  have ≥ 4 clusters**.
- **Draw depth 140** against the item-4 build-time floor (frozen: a
  subject enters only if the test cluster yields **≥ 3 D4-eligible Q–A
  items**, one-on-one programmes preferred): measured survival 70%
  (95% CI 57.5–80.1) → ~98 expected survivors, so the **≥ 80 branch
  (A5/B3) holds** with margin. Subjects are built in draw order until
  either the depth is exhausted or 110 survivors exist [PLAN: small
  overshoot so late failures don't drop us under 80].
- **H7-eligible subset** (B7, frozen: ≥ 4 dated clusters spanning
  ≥ 2 years): **98 of 140** flagged in the draw file.

## b. Arms, batching, scoring

- **Five arms** per item, exactly as OE-1: `twin_redacted`,
  `twin_named`, `zeroinfo_redacted`, `zeroinfo_named`,
  `imposter_redacted`. **Both models per A3**: Gemma-4-31B-it primary
  (Leonardo, 4-GPU distributed batch jobs, whole-node billing),
  gemini-3.5-flash-lite robustness (API).
- **Item extraction under all frozen rules**: D4 cue filter;
  chronological splits; S1 redaction scope; spaCy 3.8.14 NER (item 2);
  nickname union (item 3); near-duplicate guard (item 9);
  no-post-dated-generation rule (item 8); twin-free verification of
  every scoring sheet (precondition 4's standing rule); contamination
  meter on every arm.
- **Sequenced before any confirmatory render** (addendum item 8's
  approved-as-proposed extension): extend S1 with the
  abbreviation-safe clause pattern and the `GUEST, who …` appositive
  shape, **re-measure collateral on dev prompts, freeze only if
  collateral stays zero** — else the miss stays declared and the
  contamination meter is the backstop.
- **H1 + H7 batched into one generation plan.** Per surviving subject:
  the H1 fresh-grounding render, plus — for H7-eligible subjects —
  the staleness renders. H7 per B7 (frozen): between-subject over the
  four Δ bins **6–12 months / 1–2 years / 2–3 years / > 3 years**
  (addendum item 6); test interview = the chronologically last
  cluster, identical items at every cutoff; **volume control B7.3**:
  every cutoff filled to the same token budget newest-first,
  unfillable cutoffs excluded and counted; the crossover comparison
  grounds a **fresh same-domain imposter at the matched budget**. The
  within-subject sweep runs as the pre-registered **supporting
  analysis** on the subset that fills ≥ 3 bins, never substituted for
  the between-subject result.
- **Scoring per the adopted addendum**: channel 1 = pinned
  `all-mpnet-base-v2` (revision `e8c3b32e…`, local CPU); channel 2 =
  `gemini-3.5-flash`, temp 0.0, `thinking_budget=0`, 512 tokens,
  rubric **r2** (sha `ad050d1a…102464`), CENTRAL/LABEL/WHY format,
  widened parser; UNCLEAR rule as adopted (excluded from denominator,
  per-arm rates always shown, ≥ 0.10 gap flagged); one candidate per
  stateless call; judge never sees two twins of a duplicated question.

## c. Cost, caps, chunking

Anchors are measured, not guessed: OE-1 produced 85 Gemma generations
in 0.105 node-hours; the r2 judge pass priced at ~$0.0012/call; OE-1's
whole API session (85 flash-lite gens + 170 judge calls + probes) cost
$0.326.

| quantity | estimate | basis |
|---|---|---|
| items | ~390 (300–500) | ~98 survivors × ~4 items (floor ≥ 3, dev mean 3.4) |
| H1 generations | ~1,950/model | 5 arms × items |
| H7 generations | ~900/model | ~70 H7 survivors × 2 extra arms × ~4 items, + ~30-subject within-subject sweep × 3 cutoffs |
| total generations | **~2,900/model** (2,400–3,600) | above |
| Gemma GPU | **~3.6 nh**, worst +20% ≈ 4.3 | 0.105 nh / 85 gens, measured |
| judge calls | ~5,800 | 2,900 × 2 models |
| API total | **~$9–10**, worst +20% ≈ $12 | judge ~$7 + flash-lite gens ~$2 |
| wall-clock | ~2–3 days | GPU queue + chunked API days |

**Proposed caps [PLAN, your sign-off]: 8 node-hours GPU, $15 API.**
Either cap reached → everything stops mid-chunk and reports; no
overage without a new owner decision. Leonardo balance ~1,008 nh,
expiry 2026-09-17 — compute is not the constraint; the caps are
discipline, not scarcity.

**Chunking, all resumable:** generations in per-subject-block jobs of
~500 (~0.6 nh each), each with a manifest and completed-work ledger so
a re-submit skips finished blocks; judge and embedding passes chunked
per 500 with the same ledger; `sacct` billed after every chunk
including failed attempts; cost log appended per chunk, never at the
end.

## d. Risk table — top 5, detection and response pre-written

| # | failure mode | detection (automatic, per chunk) | pre-written response |
|---|---|---|---|
| 1 | parse-failure spike (gen or judge) | parse-failure counter vs OE-1 baseline (0/85 judge, 0 gen); any chunk > 2% halts the queue | inspect 10 raw outputs; if format drift → fix parser additively (never the rubric), re-run chunk; if model-side → stop, owner decision |
| 2 | judge drift (API model changed under the pinned name) | 10-row canary from the D/E tranche re-judged at the start of every judging day; any label flip vs the recorded r2 line halts judging | freeze judging; record version headers; owner decides re-pin vs pause — no silent continuation |
| 3 | UNCLEAR-rate asymmetry blowup | per-arm UNCLEAR rates per chunk; adopted flag fires at ≥ 0.10 gap; escalation trigger at imposter UNCLEAR > 0.50 | report beside stance rates as adopted; at escalation trigger, pause stance-channel claims for owner review — channel 1 continues; nothing is absorbed silently |
| 4 | item-yield collapse (survival below the CI floor 57.5%) | running survivor count vs draw position after every 20 subjects built | extend the draw in the same seeded order (the file goes to depth 140; deeper tranches use the same generator, same seed, positions 141+); if < 80 at pool exhaustion → the A5 subject-count branch rules apply, no silent shrink |
| 5 | sacct billing surprise (node-hours ≠ plan) | `sacct` ElapsedRaw after every chunk, failed attempts included, vs the per-chunk budget line | stop GPU submissions at the cap; owner notified with the ledger; also fires on the known failure of watchers missing job completion — billing comes from sacct, never from the watcher |

Also on record, below top-5: the long-tail stratum holds only ~134
after dev exclusion, so a long-tail-skewed attrition can erode the 3:1
mix — if the stratum exhausts, the achieved ratio is reported, never
silently rebalanced. And flash-lite arm-level contamination (measured
positive on dev) is expected and is why C3 makes robustness absolute
scores secondary.

## e. Report skeleton (the confirmatory report will follow this shape)

1. **Provenance block** — every number's generator script, commit,
   seed, and cost-log lines; the six governance documents by sha
   (OSF snapshot v4).
2. **H1 verdict** — bar quoted verbatim: *"H1 (grounding works): mean
   lift > 0 across subjects, p < .05 (paired test over subjects)."*
   with C5's transfer (registered contrast per the adopted addendum:
   own-twin − zero-info) and the adopted magnitude bar quoted
   verbatim: *"a registered contrast is 'interesting' only if it
   reaches ≥ +0.05 cosine (channel 1, pinned model) or ≥ +0.09
   stance-match points (channel 2)"* — both channels, both models,
   raw per-arm scores beside every difference, direction agreement
   required for any headline.
3. **H7 verdict** — bar quoted verbatim: *"Confirmatory bar: fidelity
   declines with Δ — per-subject slope of fidelity against Δ, mean
   slope < 0 across subjects, paired within subject where the
   chronology allows, p < .05, on the primary model. Direction-robust
   on the robustness model per A3."* Plus the pre-declared crossover
   statistic and both pre-written readings at equal prominence
   (decay-with-crossover / flat-decay-in-range).
4. **Own-minus-imposter primary** (C3) everywhere; zero-info lift
   beside it; robustness-model absolute scores explicitly secondary
   with the judge-family overlap declared.
5. **B8 dual-level tables** — individual-level lift beside
   population-level TVD over stance categories, divergences flagged.
6. **Instrument health** — per-arm UNCLEAR rates, parse/truncation
   rates, contamination meter per arm and per subject, era-violation
   counts, judge canary log.
7. **Costs** — node-hours from sacct and API dollars from the cost
   log, against the caps above.
8. **Deviations** — D1–D4 restated, plus anything new, each with its
   date and owner decision.

## The gate

**This plan does not run itself.** The GO must name: the caps in §c
(or amended numbers), and confirmation that the S1-extension
re-measure (§b) may proceed on dev prompts immediately. On GO:
S1 re-measure → build in draw order → generation chunks → scoring →
report. First stop after GO: the S1 collateral re-measure result if it
is nonzero.
