# Stage 2 open-ended dev pilot — design spec (OE-1)

Status: **SPEC ONLY — NO RUNS AUTHORIZED.** Nothing in this file spends a
token or a node-hour until the owner says go. Binding design:
`PREREGISTRATION_AMENDMENT_3.md` (adopted 2026-07-27, commit `7548bc3`).
Contract lineage: `results/stage2_pilot4/SPEC_v1.10.md` — everything not
changed below carries over from it. Dev subjects only; confirmatory
subjects are untouched by everything here.

Two owner gates are built in: (1) go/no-go on this spec; (2) the standing
stop-before-GPU checkpoint — the build runs, then STOPS for owner review
of rendered prompts and costs before any Leonardo submission.

## 0. What this pilot is for

Amendment 3 C4: before any bars freeze, the open-ended instrument must
separate own-twin from imposter-twin on dev subjects, in the
pre-registered direction, on the primary model. This pilot runs that gate
and takes the measurements the bar-lock addendum needs (embedding model
choice, judge behaviour, caps, UNCLEAR rates, magnitude-bar calibration).
It makes no claims. If separation fails, Stage 2 pauses for a design
review (C4.3) — that branch is pre-written in section 7.

## 1. Task shape and arms

Same five arms as SPEC v1.10 D8, unchanged in name and construction:
`twin_redacted` (primary), `twin_named`, `zeroinfo_redacted`,
`zeroinfo_named`, `imposter_redacted`. Same grounding budget (2,000 words,
most-recent-first fill, rendered chronologically), same S1 affiliation
redaction, same D7 imposter donors, same renderers. The only change is the
prompt tail: instead of four options and a distribution line, the prompt
ends with the held-out question and the open-answer instruction below.

Both scored models per A3 generate for every arm: Gemma-4-31B-it
(primary, Leonardo) and gemini-3.5-flash-lite (robustness, API). Per
Amendment 3 C3, robustness-arm absolute scores are secondary; only its
own-minus-imposter contrast carries robustness weight.

## 2. Generation cap and format instruction (identical across all five arms)

Real answers in the dev item set: median 78 words, mean 120, max 318
(measured over the 17 D4 items). Cap: **150 words, `max_output_tokens`
256, temperature 0.0** for both scored models. The instruction text, one
draft, frozen at bar-lock per C2.1:

> Now answer the interviewer's next question as this person would,
> speaking in their voice, in the first person. Give one spoken reply of
> at most 150 words. No lists, no stage directions, no commentary about
> this task.

"This person" reads correctly under every arm's existing preamble (GUEST
in the twin/imposter arms, "a person" in the zero-info arms), so the tail
is byte-identical across arms. Truncated generations are still scored,
flagged, and the truncation rate is reported per arm — a truncation-rate
gap between arms is itself a red flag, since it biases channel 1.

## 3. Channel 1 — embedding similarity, candidate models

Constraint found in recon: the venv has no torch and no
sentence-transformers (uv-managed; sklearn/spacy/numpy present). Any
candidate requires a one-time CPU-only torch + sentence-transformers
install — a new dependency, named in the report. All scoring is local
CPU; at ~200 texts this is minutes. Never an API model, never a scored
model (C2.2).

Candidates, all pinned by HF revision hash at bar-lock:

| candidate | size | one-line rationale |
|---|---|---|
| `sentence-transformers/all-mpnet-base-v2` | 110M | the standard symmetric-similarity SBERT; most widely validated; smallest footprint that is still credible as the pinned channel — **proposed primary** |
| `BAAI/bge-large-en-v1.5` | 335M | consistently stronger English similarity benchmarks; still CPU-viable at our N; no prefix gymnastics for symmetric use |
| `intfloat/e5-large-v2` | 335M | diversity candidate from a different training recipe; requires "query:"/"passage:" prefixes — a footgun we pin down explicitly if chosen |
| `sentence-transformers/all-MiniLM-L6-v2` | 22M | sanity check only, weights already in the local HF cache; confirms scores are not model-specific; never the pinned channel |

Selection rule, stated before any run: score all four on the pilot;
pick the candidate with the cleanest own-minus-imposter separation on the
primary model; ties break toward the smaller, more standard model. Dev
subjects are for tuning, so this selection is legitimate — it is recorded
in the pilot report and the winner is pinned in the addendum. Score =
cosine similarity between the generated answer and the real verbatim
answer.

## 4. Channel 2 — stance judge

**Proposed judge: `gemini-3.5-flash`** — generator-side family as C2.3
requires, never a scored model, and a different model version than the
robustness scorer (`gemini-3.5-flash-lite`), satisfying C2.3's
different-version clause. The family overlap with the robustness scorer
is already declared in C3 (owner edit at adoption): robustness absolute
scores are secondary. `MODEL_PRICES` in `src/doppler/costlog.py` has no
entry for it — one must be added before the run so cost logging is real,
not null.

Call protocol: one candidate answer per call — the judge never sees two
candidates together, never sees arm or model labels, never sees a
subject name, and never sees both twins of a duplicated question
(D6-v4.9, carried forward). Call order randomized, temperature 0.

The rubric draft below is the hash-ready object: its final text's sha256
is pinned in the addendum at bar-lock. The pilot may revise wording; the
report prints the version used and its hash.

```
STANCE JUDGE RUBRIC (draft r1 — text and sha256 frozen at bar-lock)

You will see three texts: a QUESTION asked in a broadcast interview,
the REAL answer the interviewee gave, and a CANDIDATE answer.

Decide whether the CANDIDATE takes the same position as the REAL
answer on the central issue the QUESTION asks about.

SAME — the CANDIDATE commits to the same position as the REAL answer
on the central issue: the same direction of judgment (for/against,
likely/unlikely, better/worse), the same recommendation, or the same
central explanatory claim. Differences of wording, style, detail,
emphasis, or strength do not matter; a more extreme version of the
same direction is SAME; agreement on the central issue with
disagreement on a side issue is SAME.

DIFFERENT — the CANDIDATE commits to a position the REAL answer's
position rules out: the opposite direction, an incompatible
recommendation, or a central claim that contradicts the REAL
answer's. Judge positions, not topics: two answers on the same topic
can be DIFFERENT, and answers emphasizing different aspects are not
DIFFERENT unless their commitments actually conflict.

UNCLEAR — anything that prevents the call: the CANDIDATE takes no
discernible position (pure hedging, refusal, generic both-sides
summary, off-topic reply); the REAL answer itself takes no position;
or the QUESTION does not ask for one and the answers share no central
claim to compare.

Boundary rules:
1. Central issue only. Identify the one thing the QUESTION most
   directly asks about; score positions on that. Side claims never
   flip a label.
2. Direction, not degree. "Cautiously yes" and "emphatically yes" are
   SAME. "Cautiously yes" and "probably not" are DIFFERENT.
3. Hedged but committed is a position. If an answer hedges and then
   lands ("it's complicated, but on balance X"), its position is X.
4. Factual-explanation questions: the "position" is the central
   explanatory claim (the main cause, mechanism, or account offered).
   Same central claim = SAME; contradicting central claims =
   DIFFERENT; merely different details of compatible accounts =
   UNCLEAR.
5. Answering a different question: if the CANDIDATE addresses a
   different issue and never commits on the central one, it is
   UNCLEAR, not DIFFERENT.
6. Predictions and counterfactuals count as positions (will/won't,
   would/wouldn't).
7. Never reward style. Fluency, idiom, or sounding like a broadcast
   guest is evidence for nothing.

Reply in exactly this format:
LABEL: <SAME|DIFFERENT|UNCLEAR>
WHY: <one sentence quoting the decisive phrase of each answer>
```

UNCLEAR handling follows the C2.3 proposal: UNCLEAR excluded from the
stance-match denominator, per-arm UNCLEAR rates always printed beside the
rate, material between-arm differences flagged. The pilot measures those
rates; the rule freezes in the addendum.

## 5. Item construction under the new task shape

Supply is already on disk: **17 D4-eligible Q–A items over the 5 Q–A dev
subjects** (`results/stage2_pilot/subjects/*/qa_items.jsonl` — C00792: 5,
C01677: 1, C02006: 3, C02013: 4, C02124: 4). C00292 stays excluded
(burned for Q–A, classifier-only, on record). No option construction
exists, so nothing filters the 17: the forced-choice machinery — option
generation, paraphrase, the build-time zero-info gate, A4 distractor
controls, the near-dup option guard — is all not applicable (dead per
Amendment 3 C6).

Carried forward unchanged: D4 filters and truncation flags; S1 redaction
in redacted arms; era rule for generated content (no generated answer may
reference events after the test interview's date — revised addendum item
8); the twin-free export check (`assert_no_cross_visible_twins`) over
every prompt set and judging sheet; the contamination meter, now computed
on channel scores (zeroinfo_named minus zeroinfo_redacted, per channel);
imposter donor assignment per D7. The subjective/factual classification
(10 subjective, 5 factual-explanation, hand-final in
`results/stage2_pilot4/item_types.json`) is kept as a reported covariate —
the judge scores both types, with boundary rule 4 covering the factual
ones. C01677 contributes one item, so subject-level readings for it are
noise; said in the report, not discovered there.

## 6. Cost estimate, per arm, 5 Q–A dev subjects

Volumes: 17 items × 5 arms = 85 generations per scored model, 170 total;
170 judge calls (one per generated answer); ~200 embedding texts × 4
candidate models, local.

Assumptions, stated: twin-arm prompts ≈ 2.9k tokens (2,000-word grounding),
zero-info prompts ≈ 250 tokens, generations ≈ 200 tokens, judge calls ≈
850 tokens in / 40 out. Flash-lite prices $0.30/$2.50 per Mtoken
(`costlog.py`). The judge's price is not yet in `MODEL_PRICES`; the high
end below assumes up to 3× flash-lite until the real price is entered.

| arm | flash-lite generation | judge (both models' outputs) | embedding |
|---|---|---|---|
| twin_redacted | ~$0.023 | $0.012–0.037 | $0 (local CPU) |
| twin_named | ~$0.023 | $0.012–0.037 | $0 |
| imposter_redacted | ~$0.023 | $0.012–0.037 | $0 |
| zeroinfo_redacted | ~$0.010 | $0.012–0.037 | $0 |
| zeroinfo_named | ~$0.010 | $0.012–0.037 | $0 |
| **total API** | **~$0.09** | **$0.06–0.19** | $0 |

Gemma generation (all 85 prompts, one batched job, engine init ~225 s
dominating as in rounds 3–4): estimate **~0.15 node-hours**, from the
~0.11 nh the 8–15-prompt gate jobs cost. Proposed caps: **$0.40 API,
0.25 node-hours GPU** — overshoot stops the run and reports. Every run
logs to `cost_log.jsonl`.

## 7. The C4 validation-gate report, format fixed now

One report, `results/stage2_openended/PILOT_REPORT_OE1.md`, with both
readings pre-written before the run:

Core table, one row per channel × scored model:

| channel | model | own mean | imposter mean | own−imposter (95% CI) | zero-info mean | per-arm UNCLEAR rates |
|---|---|---|---|---|---|---|

- Differences are paired per item (same item, own vs imposter
  generation), bootstrap CI clustered by subject. With 17 items over 5
  subjects this gate is **directional, not powered** — stated in the
  report header. Beside the CI: the subject-level sign count (how many of
  5 subjects show own > imposter, per channel).
- B8 applies: beside the item-level lift, a population-level TVD over
  stance categories per arm, divergences flagged.
- Raw per-arm scores always beside every difference; embedding-candidate
  comparison table; truncation rates per arm; contamination meter per
  channel; full cost table.
- **PASS reading (pre-written):** own > imposter in the pre-registered
  direction on the primary model in BOTH channels → proceed to fill the
  bar-lock addendum's [TO FILL] slots and to the owner's ≥50-label judge
  spot-check (precondition 6).
- **PAUSE reading (pre-written):** direction absent on the primary model,
  or the two channels disagree on direction → **Stage 2 pauses for a
  design review** per C4.3. The report is published as the record, and no
  new instrument is reached for without a new amendment. No spin: a
  pause outcome is a finding about the instrument, reported with the same
  care as a pass.

Owner ≥50-label spot-check sampling (runs only after the pilot exists):
50 judge calls sampled across all 5 subjects and both scored models,
balanced 25 SAME / 25 DIFFERENT where supply allows (shortfall filled
with UNCLEAR and said so), presented blind to arm and model, twin-free
per the standing rule.

## 8. Declared risks — the skeptic's reading, filed in advance

1. **Channel 1 can reward topic overlap, not person knowledge.** The own
   twin's grounding shares the subject's recurring topics and vocabulary
   with the real answer; the imposter's grounding does not. Some of that
   is genuine person signal (speaker-specific framing), some is trivial
   topic recurrence. Diagnostic reported with the gate: similarity
   between the own arm's grounding text itself and the real answer, as a
   covariate — if grounding-to-answer similarity alone tracks the
   own-arm score, channel 1's separation is suspect. Channel 2 is the
   disambiguator, and no headline rests on one channel (C2.4).
2. **UNCLEAR flooding.** Factual-explanation items (5 of 17) may drive
   high UNCLEAR rates and shrink the judged denominator. Measured per
   arm and per item type; if the stance channel loses too much N, that
   is a design-review fact, not something to patch mid-run.
3. **Judge family overlap** with the robustness scorer: declared and
   already handled by C3 — robustness absolute scores secondary.
4. **Small-N gate.** 17 items, 5 subjects, 1 item for C01677. The gate
   is directional; magnitude bars are set only after these measurements
   (C5), so no magnitude number from this pilot becomes a claim.

## 9. H7 plugs in unchanged

H7's design does not move: between-subject over the four frozen Δ bins
(6–12 m, 1–2 y, 2–3 y, >3 y; addendum item 6), crossover statistic as
registered in B7, within-subject sweep as supporting analysis. The only
change, per C5: the outcome variable is now open-ended fidelity — the
same two channel scores — computed per Δ bin exactly as computed here,
with headline direction agreement required across both channels. The
eligibility supply is already measured (262/578 candidates; bins
88/120/136/215). This pilot does not run H7; it reports each item's
grounding-to-test Δ as a smoke check that the outcome variable computes
per bin with no new machinery.

## 10. What this pilot feeds into the bar-lock addendum

Direct map to the revised addendum's [TO FILL] slots: embedding model +
pinned revision (§3 winner) · judge model + version (§4) · rubric text +
sha256 (§4, final wording) · generation cap + instruction text (§2) ·
judge trust bar (after the owner's ≥50-label spot-check) · UNCLEAR rule
(§4, measured rates attached) · magnitude bars for H1/H2/H6/H7 on the
continuous scales (calibrated from §7's measurements). Freeze happens in
the addendum, after owner review of the pilot report — never in this
file.
