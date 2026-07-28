# H6 part-2 audit tranche — build note (2026-07-28)

The frozen follow-up classifier has now run on the confirmatory subjects, and
the part-2 blind audit tranche that gates H6 scoring is built. Nothing here
scores H6. Nothing here was labelled by a human yet.

## What ran

The classifier from Amendment 2 B2.1 — **Gemma-4-31B-it under RUBRIC_V1**,
rubric sha256 `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`
— over the **grounding** transcripts of the **89 confirmatory survivors**.

The test interview was never opened. The build asserts, per subject, that the
test transcript does not appear in the grounding turns.

Same machinery as the development run, not a rewrite: same prompt builder, same
rule shortcut, same decode settings (temperature 0.0, seed 0, 4 GPUs, one
whole node).

## The counts

| | count |
|---|---|
| host turns in scope | **7,322** |
| labelled by rule (no model call) | **2,035** |
| labelled by the model | **5,287** |
| parse failures after retries | **0** |
| turns dropped from selection | **0** |
| subjects above the 5% drop threshold | **none** |

The rule shortcut is the frozen one: a host turn with no guest answer anywhere
behind it is NEW-TOPIC by definition, because there is nothing for it to follow
up on. Those turns cost no model call.

Labels: **2,033 FOLLOW-UP**, **3,254 NEW-TOPIC** from the model, plus the 2,035
rule NEW-TOPIC turns. So 28% of all host turns are follow-ups, or 38% counting
only the turns the model actually judged.

That sits almost exactly where development sat — 37% follow-ups among
model-judged dev turns against 38% here. The classifier is not behaving
differently on the confirmatory subjects than it did on the dev ones.

**Zero parse failures over 5,287 calls**, matching dev's zero over 469. No
retry pass was needed, so the 2-retry rule never fired.

## One subject has no host turns at all

**C02474 (Van Boxmeer)** produced **0 host turns** across its two grounding
transcripts, so it has no classifier labels of either kind. Its turns are 21
guest and 53 "other" — nobody in those transcripts resolved to the host role.

This is not a classifier failure and nothing was dropped. It is an upstream
speaker-role outcome, and it means C02474 has no follow-up-rich or
follow-poor material to draw from, so it will fail the B4.2 eligibility rule
mechanically when the arms are built. It stays in H1/H2. Recorded here so the
89-vs-88 gap in the per-subject table is not read later as a missing file.

Supply is very uneven across the other 88, the same way it was in dev: the
median subject offers 27 model-judged turns, the top one offers 720, and the
thinnest offers 1.

## The tranche

Written to `results/stage2_openended/h6_part2_sheet.md` (blind) and
`results/stage2_openended/h6_part2_key.json` (sealed key).

| | value |
|---|---|
| rows | **60** |
| FOLLOW-UP / NEW-TOPIC | **30 / 30** — exactly balanced, no shortfall |
| subjects | **30**, two rows each |
| seed | **62** |
| pool drawn from | 5,268 auditable labels over 88 subjects |

Requirements from Addendum A precondition 5 part 2 are ≥ 60 rows and ≥ 10
confirmatory subjects. Both clear with room, and the balance is exact, so
there is no shortfall to document — unlike the F/G tranche.

What the sheet shows a co-auditor is byte-for-byte what the classifier saw:
the same PREV / GUEST / TARGET block, sliced out of the rendered prompt, with
the same truncations and the same `...` marks. The sheet carries no labels, no
reasoning, no subject id and no transcript id, and the rows are shuffled. That
is checked, not assumed — the writer refuses to save a sheet containing either
label word or any drawn row's subject or transcript id.

Three constraints were enforced on the draw:

- **No dev subjects.** Asserted against `dev_subjects.json`; the confirmatory
  set is disjoint from the six dev subjects by construction anyway.
- **No row from the part-1 sheet.** Asserted row by row against
  `h6_audit_key.json`.
- **No turn appears twice.** No two drawn rows from one transcript sit within
  3 turn indices, so no turn is ever both a TARGET to judge and the PREV of
  another row. 19 model rows whose prompt was byte-identical to another row's
  were dropped from the pool for the same reason.

Draws are spread over a **seeded shuffle** of subjects rather than the
alphabetically first ones. Part 1 used all 6 of its subjects so the order never
mattered; here 88 subjects compete for 30 slots, and taking the first by id
would have made the tranche a function of the id ordering instead of a sample.

## Cost

**0.1581 node-hours**, billed from `sacct`, every attempt included.

| job | state | elapsed | node-hours |
|---|---|---|---|
| 50595332 | CANCELLED while pending | 00:00:00 | 0.0000 |
| 50595689 | CANCELLED while pending | 00:00:00 | 0.0000 |
| 50597655 | COMPLETED | 00:09:29 | 0.1581 |

The two cancelled jobs never started, so they cost nothing, but they are listed
rather than quietly dropped. They were cancelled and resubmitted to get the job
out of a queue it was not moving in: under the normal QOS it sat behind roughly
4,635 pending jobs with no estimated start, so the final submission went under
`boost_qos_dbg` (priority 80, 30-minute cap) — a six-minute inference run is
what that QOS is for.

Of the 9m29s, about 4m22s was engine startup and 1m52s was actual generation;
the rest is job setup and teardown. Projection before submitting was 112.4
seconds of generation against 112.27 measured.

Cost line appended to `results/cost_log.jsonl` under run id
`stage2_confirm/h6_classify`. No API call was made anywhere in this task, so
there is no dollar cost. The closeout GPU phase caps at 3 node-hours and H6
generation still has to fit inside it; **2.84 node-hours remain**.

## What has to happen next, and what must not

The tranche is built but **not yet audited**. Until a blind co-audit clears
**raw ≥ 0.85 and Cohen's κ ≥ 0.60**, no confirmatory H6 arm may be built and no
H6 number may be produced. Failing that bar halts H6 scoring pending rubric
revision.

Two things are already pre-committed and cannot be chosen after seeing the
result. If the part-2 FOLLOW-UP overturn rate comes in **above 20%**, the rich
arm must additionally be built at D_min = 3 as a sensitivity arm and both
reported side by side. **Above 35%**, H6 scoring halts. Development's own
FOLLOW-UP overturn rate was 25%, so the D_min = 3 arm is expected to fire.

One honest limitation on that tripwire: 30 FOLLOW-UP rows measure an overturn
rate in steps of 3.3 points, which is coarse for a threshold set at 20%. 60
rows is the pre-registered floor and supply is nowhere near exhausted — a
larger tranche is one command away (`--rows 120`) if a tighter read is wanted,
and it would have to be decided before the co-audit, not after.

## Reproduce

```
.venv/bin/python experiments/h6_confirm_classify.py build
.venv/bin/python experiments/h6_confirm_classify.py finalise
.venv/bin/python experiments/h6_part2_tranche.py
```

Both are deterministic. The classifier run itself needs the node
(`experiments/h6_classify_gen.sbatch`).
