# B10.8 detectability — the rater line

# PILOT -- pipeline validation on dev subjects; no research conclusions.

**LABEL: PRE-GATE PREDICTION.** Written, scored and committed **before** the
round-4 generation batch and gate job were submitted, so it cannot be drawn
around the gate outcome. Same freeze discipline as
`results/stage2_pilot3/tell_classification.json`.

Sheet: `results/stage2_pilot3/DETECTABILITY_SHEET.md` (20 unmarked entries,
seed 53). Key: `results/stage2_pilot3/DETECTABILITY_KEY.md`. Machine-readable
scoring: `detectability_rater_line.json`.

---

## 1. The human line is WAIVED — a documented deviation, not a satisfied check

**B10.8 requires a HUMAN detectability check. It was not performed.** The owner
declined to complete the sheet on 2026-07-27 and substituted an out-of-family
LLM rater.

**No human hit rate exists for this instrument, and none is fabricated here.**
B10.8's human check is recorded as an **open deviation**. The LLM line below
does not satisfy it: it answers a related but different question — whether a
capable *model* can spot the real answer — which is the more direct predictor
of what a scorer will do, but is not the check the amendment asks for.

If the instrument ever goes confirmatory, either the human line is run or
B10.8 is formally amended. That is an owner decision at bar-lock.

## 2. The rater

**Claude**, a frontier LLM, **out-of-family from both** the generator
(`gemini-3.5-flash-lite`) and the scorer (`Gemma-4-31B-it`). No model in the
scoring or generation path rated its own writing.

Picks, verbatim:

    1:A  2:none  3:B  4:none  5:C  6:none  7:D  8:C  9:D  10:C
    11:C 12:B    13:B 14:none 15:none 16:none 17:none 18:none 19:C 20:none

**Scoring rule.** A named letter on a REAL entry is a hit only if it is the key
letter. `none` on a real entry is a **miss** (non-identification). `none` on a
CONTROL is a **correct rejection**; any named letter on a control is a **false
positive**. Chance on a real entry, for a rater that always names a letter, is
**0.25**.

## 3. Result

    real entries                  10
    correctly identified          10        hit rate 1.00   (chance 0.25)
    said "none" on a real entry    0
    control entries               10
    correct rejections             9        0.90
    false positives                1        0.10
    overall correct            19/20        0.95

**The rater identified the real answer in every single real entry.** The one
error is a false positive on entry 7, a control — it named a letter where no
real answer was present.

Because the rater never said `none` on a real entry, the two readings the
scoring rule distinguishes (none-as-miss on real, none-as-correct-rejection on
controls) give the same number: **10/10 either way**.

### Twin contamination does not explain it

Five questions appear twice on the sheet, once as a real entry and once as a
control. Those controls were given entirely fresh option sets — **zero shared
option texts** — so nothing is recoverable by elimination. But the rater
reported using *twin-pair stance inference*: seeing the same question twice and
reasoning across the two option sets. The non-twinned entries are therefore the
clean subset.

| subset | real entries | hit rate |
|---|---|---|
| twinned (#1, 3, 5, 8, 10) | 5 | **1.00** |
| **clean, non-twinned (#9, 11, 12, 13, 19)** | 5 | **1.00** |

**Identical.** Twin-pair inference is a real leak and is being closed
(section 5), but it is not what carried this result. The realness signal is
available from a single option set.

## 4. The tells the rater named, verbatim

1. **hedging/register**
2. **stance-vs-premise fit**
3. **world-truth/academic content**
4. **entity density**
5. **twin-pair stance inference**
6. **vocative-name leak in item 10**

Four of the six are exactly what round 4 was built to attack, which is why this
line is worth having *before* the gate rather than after:

| tell | round-4 change | SPEC |
|---|---|---|
| hedging/register | few-shot conditioning on the subject's own answers | D6-v4.1 |
| world-truth/academic content | plausibility check, FALSE/FRINGE rejected | D6-v4.3 |
| vocative-name leak | deixis stripping across all four options | D6-v4.2 |
| stance-vs-premise fit | subjective-only item set | D6-v4.4 |
| entity density | **already controlled** by A4.1's ±2 entity target and the D6 ladder — and it still reads as a tell, which is itself a finding | D6-v3.4 |
| twin-pair stance inference | new standing eval rule, no rater or scorer ever sees both twins | D6-v4.9 |

## 5. What this predicts, recorded before the gate ran

Every tell the rater names is available to **any** capable scorer reading the
same four options with **no information about the person**. A frontier model
identifying the real answer 10 times out of 10 is direct evidence that the
option sets carry a realness signal independent of who was speaking.

**Prediction: the round-4 zero-information arm scores far above the 0.25 chance
line.** Round 4 attacks four of the six named tells; whether that is enough is
precisely what the gate measures. If it is not, the pre-committed kill rule
(≥ 0.90) fires and forced choice is done on this corpus.

Two caveats on record before the comparison is made:

- **Entity density was already controlled and still reads as a tell.** A4.1
  matches it within ±2 tokens and the D6 ladder enforces the bucket. If a rater
  can still use it, matching on a count is not matching on how the entities are
  deployed.
- **The rater saw round 3's options.** Round 4 rebuilds them. This line is a
  prediction about round 4, not a measurement of it.
