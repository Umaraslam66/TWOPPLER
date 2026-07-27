# Stage 2 pilot report — round 4 (hedged, plausible, deixis-free counterfactuals)

# PILOT -- pipeline validation on dev subjects; no research conclusions.

**PILOT -- pipeline validation on dev subjects; no research conclusions.** Every number below is a pipeline-validation number on the same development subjects as rounds 1–3. Nothing here answers a pre-registered bar, nothing here is confirmatory, and no result in it should be quoted as a finding about twins. Contract: SPEC.md v1.10 (D6-v4), binding design PREREGISTRATION_AMENDMENT_2.md **B10** as amended by the owner-approved round-4 design of 2026-07-27. Scoring model leonardo-gemma4-31b-it, temperature 0.0, tp 4, max-model-len 8192. Generator gemini-3.5-flash-lite. 8 model calls, 137 API calls, $0.0447 API, 0.1064 node-hours.

**What is scored (B10.2, binding reframing).** The claim scored is that the twin identifies the person's actual **POSITION** among plausible alternative positions on the same question — **not** that it picks a verbatim transcript answer.

---

## 0. The kill rule, verbatim, and the fact that it fired

> **KILL RULE, pre-committed before any round-4 data existed:** if round 4's zero-information argmax accuracy is **≥ 0.90**, four-way forced choice is **DEAD** on this corpus and there is **no round 5 on any axis**. Rounds 1, 2 and 3 solved 17/17, 10/10 and 15/15 by three different mechanisms; a fourth instrument that also fails is evidence about the format, not about the next patch. The fallback landing zone is already written and committed: `results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md` (commit 71ae352).

**Round 4's zero-information argmax accuracy is 1.00 under both parser readings. THE KILL RULE FIRES.**

Phase 2 was not submitted. There are no twin, imposter or contamination numbers for round 4 and none should be quoted. `FALLBACK_OPENENDED_SKETCH.md` now becomes the amendment draft for the owner to review.

---

## 1. Result

    D4-eligible subjective items attempted     10
    candidate items built                       8   (2 dropped, section 5)
    gate prompts                                8

    FROZEN parser (the contract)
      replies parsed                            2 / 8
      argmax accuracy                        1.00   (2 of 2)
      mean p(true) 0.750   mean margin +0.630   range +0.40 .. +0.86

    WIDENED reading (reported beside, never in place of)
      replies parsed                            8 / 8   (6 recovered)
      argmax accuracy                        1.00   (8 of 8)
      mean p(true) 0.694   mean margin +0.558   range +0.40 .. +0.86

    items the gate rejected                     8   (every one)
    items surviving into a final set            0
    readings disagreeing on argmax              0

Both readings agree at 1.00. The kill rule is read on the frozen number, and the widened number does not rescue it.

### Per item, widened reading

| item | frozen parsed | p(true) | margin |
|---|---|---|---|
| C00792:NPR-19884:10 | yes | 0.90 | **+0.86** |
| C02006:NPR-14829:19 | recovered | 0.85 | +0.80 |
| C02006:NPR-14829:26 | recovered | 0.80 | +0.70 |
| C00792:NPR-19884:13 | recovered | 0.60 | +0.45 |
| C00792:NPR-19884:15 | recovered | 0.60 | +0.45 |
| C00792:NPR-19884:6 | recovered | 0.60 | +0.40 |
| C02124:NPR-12184:6 | recovered | 0.60 | +0.40 |
| C02006:NPR-14829:29 | yes | 0.60 | +0.40 |

**The four changes did move the needle — and it did not matter.** Mean p(true) fell from 0.776 (round 3) to 0.694, mean margin from +0.690 to +0.558, and the widest margin from +0.96 to +0.86. Every item still solved. A margin that narrows while accuracy stays at 1.00 is the instrument getting harder to solve *confidently*, not harder to solve.

### Cross-round caveat — this is NOT apples-to-apples

Round 4 is built on the **subjective-only** subset (8 items from 10 attempted). Round 3 was a mixed set of 15. In particular **`C02013:NPR-9480:70`, round 3's +0.96 world-truth item, is excluded by design** (D6-v4.4 classifies it factual-explanation). So round 4's numbers are not a like-for-like improvement measurement against round 3's, and the drop in mean margin is partly a change of item mix. Both facts point the same way — accuracy 1.00 either way — but the *size* of the improvement must not be read off a table comparing 15 mixed items with 8 subjective ones.

---

## 2. What the model used this time — the register fix inverted the tell

Round 3's mechanism was that generated options read like op-ed advocacy while the real answer hedged. Round 4 conditioned generation on the subject's own answers and demanded hedged, qualified speech. **It worked, and produced the opposite tell.**

`C00792:NPR-19884:10`, margin **+0.86**, the widest in the set:

> "Option A reflects the specific rhetorical style and political arguments common in critiques of early Trump-era campaign rhetoric... **Options B, C, and D are written in a more generic, academic, or policy-heavy style** that lacks the specific 'campaign' context and the **biting irony ('a gift that keeps on giving')** typical of these broadcast interviews."

`C00792:NPR-19884:6`, margin **+0.40**:

> "Option B reflects a common nuanced geopolitical argument... **This specific phrasing — mentioning the 'free ride' for Russia, the Assad regime, and Iran** — is highly representative of the rhetoric used by analysts discussing the Syrian conflict."

Read the option sets and it is plain. The true answer says the failure to act "has given the Russians, the Assad regime, and Iran the sense that they have **an absolute free ride** to do anything they want to civilians". The three generated alternatives say things like "the intelligence community in **Langley** and the **Pentagon** experts tracking the Levant", "**Congress** and the **State Department**... recent **UN Security Council** resolutions", "the **Department of Defense** and the **Joint Chiefs of Staff**".

**The register axis has a sweet spot the generator cannot hit.** Pushed toward advocacy it is too confident; pushed toward hedging it becomes bland institutional name-dropping. Either way the real answer is the one that sounds like a person with a view, and the generated ones sound like a briefing document. B10.4's paraphrase is supposed to strip "catchphrases" — it did not strip "a gift that keeps on giving" or "an absolute free ride", because the paraphrase must preserve every substantive claim and these idioms *carry* the claim.

### Entity density: matched on count, still a tell

A4.1 matches entity tokens within ±2 and the D6 ladder enforces the bucket; 6 of 8 items sat at rung 0, the tightest. And the tell survives anyway, because **the generated options spend their entity budget on institutions while the real answer spends it on the actors it is actually talking about**. Matching on a count is not matching on how entities are deployed. This is exactly what the frontier rater flagged pre-gate, and it is now confirmed by the scorer's own reasoning.

### Stance-vs-premise fit survived the subjective-only filter

`C02006:NPR-14829:29`, margin +0.40:

> "The host's question... is **a leading question inviting a 'yes'** or a qualified positive perspective. Option C is the only response that directly answers 'It is possible'... Options A, B, and D are primarily pessimistic or dismissive, which does not align as naturally with the host's specific prompt."

This is the polar structure flagged in round 3 §3 and named by the rater as *stance-vs-premise fit*. B10.5 requires every distractor to conflict with the true position, so on a leading question all three land on the side the host did not invite. Restricting to subjective items does not help; leading questions are *more* common there, not less.

---

## 3. The detectability line, laid beside the gate outcome

`DETECTABILITY_RATER_LINE.md` was scored and **committed before this gate was submitted** (commit ddb3ac6), so it is a genuine prediction.

### 3.1 The human line is WAIVED — an open deviation, not a satisfied check

**B10.8 requires a HUMAN detectability check. It was not performed.** The owner declined on 2026-07-27 and substituted an out-of-family LLM rater. **No human hit rate exists and none is fabricated here.** B10.8's human check is recorded as an **open deviation**; if the instrument ever goes confirmatory, either the human line runs or B10.8 is formally amended. Owner decision at bar-lock.

### 3.2 The LLM rater line (PRE-GATE PREDICTION)

Rater: **Claude**, out-of-family from both the generator (`gemini-3.5-flash-lite`) and the scorer (`Gemma-4-31B-it`).

    real entries                  10
    correctly identified          10        hit rate 1.00   (chance 0.25)
    said "none" on a real entry    0
    controls                      10
    correct rejections             9        0.90
    false positives                1        0.10
    overall correct            19/20        0.95

Both scoring readings give the same number: the rater never said `none` on a real entry, so none-as-miss and none-as-correct-rejection agree at 10/10.

Twin contamination does not explain it. Five questions appear twice on the round-3 sheet and the rater reported using twin-pair stance inference, but the clean non-twinned real entries scored **1.00 — identical** to the twinned ones (both 5/5).

### 3.3 Prediction vs outcome

| | rater, on round 3's options (pre-gate) | Gemma, on round 4's rebuilt options |
|---|---|---|
| identifies the real answer | **10/10** | **8/8** |
| chance | 0.25 | 0.25 |

**The prediction was right.** A frontier model said the realness signal was there; the round-4 rebuild did not remove it. Of the six tells the rater named, round 4 attacked four:

| tell | round-4 change | outcome |
|---|---|---|
| hedging/register | few-shot on the subject's own answers | **inverted, not removed** (§2) |
| world-truth/academic content | plausibility check, FALSE/FRINGE rejected | 2 rejections fired; tell not decisive here, but the item most exposed to it was excluded by design |
| vocative-name leak | deixis stripping across all four options | **removed** — 8/8 items stripped, no host name in any option, no trace cites it |
| stance-vs-premise fit | subjective-only item set | **survived** (§2) |
| entity density | already controlled by A4.1 | **survived** — count matched, deployment not (§2) |
| twin-pair stance inference | new standing rule D6-v4.9 | **closed**, and verified (§6) |

Two of six fixed. Two inverted or survived. Two untested here.

---

## 4. Both-parser tables

The frozen parser is the contract. The widened reading takes the LAST well-formed distribution and reads it **with the same frozen parser**, so it cannot rescue a genuinely malformed one; it is reported beside the contract number, never in place of it.

| cell | reading | N prompts | N parsed | parse failures | argmax accuracy | mean p(true) | mean margin |
|---|---|---|---|---|---|---|---|
| gate `zeroinfo_redacted` / standard | **frozen** | 8 | **2** | 6 | **1.00** | 0.750 | +0.630 |
| gate `zeroinfo_redacted` / standard | widened | 8 | **8** | 0 | **1.00** | 0.694 | +0.558 |

Recovered by widening: **6**. Readings disagreeing on argmax: **0** (structurally impossible by construction — the widened reading returns the frozen result unchanged when the frozen parser succeeds — and retained as a tripwire).

**The parse-failure rate is now the dominant measurement risk.** Round 1: 2 of 170. Round 2: 2 of 10. Round 3: 12 of 15. Round 4: **6 of 8 (75%)**. Every failure in rounds 3 and 4 is the same doubled-distribution artifact, every one recoverable, every one argmax-correct. It has not yet changed a conclusion because both readings have always agreed. On a run where they disagree, the contract number would rest on a quarter of the data. Widening the frozen parser remains a **bar-lock decision**; this report does not take it.

No prediction cells exist — phase 2 was not run.

## 5. Build yield and guard statistics

| subject | attempted | **built** | dropped | gate-solved |
|---|---|---|---|---|
| C00792 Frederic Hof | 4 | **4** | 0 | 4 |
| C02006 Robert Harris | 3 | **3** | 0 | 3 |
| C02124 Samer Shehata | 2 | **1** | 1 | 1 |
| C02013 Robert Sampson | 1 | **0** | 1 | 0 |
| **total** | **10** | **8** | **2** | **8** |

Only the subjective subset was built (D6-v4.4); the 5 factual-explanation items were not attempted.

    position preservation SAME              10 / 10   (0 retries)
    truncated paraphrases                    0
    era violations                           0
    surviving subject-name variants          0
    grounding-quote hits                     0
    copies/quotes of a style exemplar        0
    contradiction rejections                 7        (6 AGREE, 1 UNRELATED)
    PLAUSIBILITY rejections                  2        (1 FALSE, 1 FRINGE)
    deixis mode                              stripped on 8 of 8
    style-exemplar shortfalls                none
    ladder rungs                             rung 0: 6, rung 2: 2
    ladder_exceeded                          0

**The plausibility check fired**, rejecting one factually-false and one fringe alternative — the D6-v4.3 guard doing its job. Both drops (`C02013:NPR-9480:45`, `C02124:NPR-12184:4`) are "only 2 distractors survived the checks": the combined contradiction-plus-plausibility bar is tighter than round 3's, which is the intended cost.

API: 137 calls over 10 items (13.7/item, up from round 3's 10.3 — the plausibility call is the difference). Steps: 10 generate, 50 paraphrase, 10 position, 37 contradiction, 30 plausibility. 0 retries, 0 rate-limit events.

## 6. D6-v4.9 twin verification

New standing rule, added after the rater named twin-pair stance inference:

> No rater and no scorer may ever see both twins of a duplicated question. Within any single prompt file or rating sheet, a question appears AT MOST ONCE.

**Verified, not assumed.** `assert_no_cross_visible_twins` runs at export over every exported prompt set and raises rather than warns. Result in `twin_check.json`: the gate set holds **8 rows and 8 distinct item_ids** — no question appears twice. No prediction sets were exported.

## 7. B10.7 margin relaxation — CONSIDERED, NOT ADOPTED

> A margin-relaxed gate — rejecting an item only when the zero-information arm solves it by more than some margin, rather than on argmax alone — would keep items the current gate discards, and round 3's tightest item sat at +0.30. It is **NOT adopted** here for one reason: round 4 is the round that tests a pre-committed kill rule, and a kill rule means nothing if the bar moves in the same round it is tested. Loosening the gate and then reporting that fewer items were rejected would be unfalsifiable. Available at **BAR-LOCK**, and only if round 4 lands in the gray zone — zero-information accuracy clearly below 0.90 but clearly above the 0.25 chance line. The owner decides.

**Round 4 did not land in the gray zone.** Accuracy is 1.00 under both readings and the *smallest* margin in the set is +0.40 — larger than round 3's tightest item. The precondition for reconsidering the margin rule is not met, so it stays unadopted and is not an open question.

## 8. Cost

**GPU, billed from `sacct`.**

| job | slurm | state | elapsed | nodes | node-hours |
|---|---|---|---|---|---|
| `stage2_pilot4_gate` | 50422185 | COMPLETED | 00:06:23 | 1 | **0.1064** |
| `stage2_pilot4_pred` | — | **not submitted** (kill rule) | — | — | 0 |
| **round-4 total** | | | | | **0.1064** |

One attempt, no node fault, no resubmission. Against the ~0.14 estimate and the 1.0844 remaining cap: **0.1064 used, 0.9780 left**.

**API.**

| run | model | calls | tokens in | tokens out | cost |
|---|---|---|---|---|---|
| `stage2_pilot4/build` | gemini-3.5-flash-lite | 137 | 49,694 | 11,920 | **$0.0447** |
| `stage2_pilot4/gate` | leonardo-gemma4-31b-it | 8 | 3,889 | 1,417 | $0.00 |

Under the $0.09 cap. **Programme total across all four rounds: 0.1064 + 0.1156 (r4+r3 GPU, plus rounds 1–2 recorded in their own reports), $0.1446 flash-lite API for rounds 3–4, and one superseded `gemini-3.1-pro-preview` line whose `cost_usd` is null because `MODEL_PRICES` has no entry for it — a missing price, not a zero cost.**

## 9. Where this leaves Stage 2

Four instruments, four ceilings:

| round | wrong options came from | zero-info accuracy | mechanism |
|---|---|---|---|
| 1 | other people's answers | 17/17 | topical coherence |
| 2 | the same subject's other answers | 10/10 | responsiveness to the question |
| 3 | written counterfactuals | 15/15 | speaker plausibility + world knowledge |
| 4 | **hedged, plausibility-checked, deixis-free counterfactuals, subjective items only** | **8/8** | **inverted register + entity deployment + stance-vs-premise fit** |

Each round removed the previous mechanism and revealed another. Round 4 is the informative one because it removed a mechanism and the *replacement was the inverse of what it removed*: make the alternatives less like advocacy and they become bland; the real answer is identifiable either way, because it was written by a person with a view and the alternatives were not.

A frontier model reading only the four options, with no information about the speaker, identified the real answer 10 times out of 10. That is the finding. It says the option sets carry a realness signal that has nothing to do with knowing the person — and a twin scored against them would earn credit for detecting text provenance, not for modelling anyone.

**The kill rule fires. There is no round 5.** `results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md` becomes the amendment draft for the owner.

Two things a successor should not have to rediscover:

- **The parse artifact is at 75% and rising with option length.** Decide the parser question before any run whose two readings could disagree.
- **B10.8's human line is still unmet.** Everything above about detectability rests on an LLM rater, which predicts scorer behaviour well but is not the check the amendment asks for.

No confirmatory subject was touched. Rounds 1–3 artifacts were not modified; round 3's node-side completions were verified unchanged after round 4 ran.
