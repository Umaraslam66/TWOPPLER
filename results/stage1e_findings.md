# Stage 1E findings — adaptive elicitation, offline

**What Stage 1E set out to answer:** when you can ask a person a limited number
of questions before predicting something else about them, does choosing the
questions adaptively — based on the model's own uncertainty — beat asking them in
a fixed or random order?

**Answer: no, not at these budgets on this corpus.** A question order derived
once from population data beat both adaptive selection and random ordering, at
about a tenth of the compute. Adaptive selection was indistinguishable from
random.

Status: confirmatory. Bars were frozen in
`PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md` (commit `3b8dd57`) before the
confirm split was touched. Full verdicts and every table:
`results/stage1e_confirm_report.md`. Analysis artifact:
`results/stage1e_confirm/analysis.json`.

## The setting in one paragraph

Each RIASEC respondent is replayed as a person to be interviewed. Demographics
are given up front; their 48 recorded interest answers are then revealed one at
a time, in an order the policy chooses. After k reveals the twin predicts all 10
held-out TIPI personality items — a different instrument, so this is
cross-domain prediction, not filling in a scale from itself. The metric is mean
absolute error against the person's real answers, and the primary reported
quantity is always **lift over a demographics-only baseline**, never raw
accuracy.

Confirm run: n=1,000 persons, seed 46, disjoint from all 720 previously used
persons and from the 2,000-person derivation split. Gemma-4-31B-it, twin variant
v2, temperature 0. Checkpoints k ∈ {1, 2, 4, 8, 12, 16, 20}. Five arms:
baseline, random order, fixed order, adaptive, imposter.

**Every number below is given under both decodings.** The twin states a
probability distribution over the 7 answers; that has to be turned into a number
before scoring. Expected value (EV) is the pre-registered primary; argmax is the
binding robustness check. Where they disagree, that disagreement is the finding.

One precision note: an MAE quoted inside a two-arm contrast is computed on the
paired subset (a person-item pair is dropped from both arms if either failed to
parse), so it can differ from that arm's standalone MAE in the fourth decimal.
With 3 parse failures in 1,060,000 calls the difference never exceeds 0.0001.

## (a) The confirmed null: adaptive selection does not beat random ordering

**C1, the primary pre-registered bar.** Adaptive minus random at k=12, required
to be above zero with p < .05:

| decoding | adaptive MAE | random MAE | lift | 95% CI | p |
|---|---|---|---|---|---|
| EV (primary) | 1.4370 | 1.4412 | +0.0043 | [−0.0055, +0.0140] | **0.391** |
| argmax | 1.4341 | 1.4372 | +0.0030 | [−0.0122, +0.0183] | 0.695 |

At k=20 (secondary): +0.0042 EV [−0.0042, +0.0126], p=0.328; +0.0020 argmax
[−0.0121, +0.0161], p=0.78.

**C1 FAILS.** The point estimate is positive under both decodings and both
confidence intervals comfortably contain zero.

**This is not a power failure, and that matters.** The bar carried its own power
note: the training-split effect (+0.02) would have had >95% power at n=1,000. We
had the power. The effect was not there. It shrank from +0.022 on the training
split to +0.004 here — a fifth of its size.

**Why it shrank is the interesting part.** The adaptive configuration used here
(EV-variance uncertainty scorer, seeded random tie-break) was chosen as the best
of four variants on the training split — and then measured on those same 150
people. That is a selection effect, and Stage 1E had already measured exactly
this hazard once: the pilot's fixed order, picked on the same 150 people it was
scored on, read +0.088, while the honest version read +0.074. The bias was worth
+0.014 there. Here it appears to have been worth roughly the entire effect.

The contrast within this run is clean, because the two arms differ in exactly
this respect:

| arm | how it was derived | training split | confirm split | replicated? |
|---|---|---|---|---|
| fixed order | greedy ridge on 2,000 **disjoint** persons | +0.074 | +0.0680 | yes |
| adaptive edge over random | best-of-four **on the same 150 persons** | +0.022 | +0.0043 | no |

Pre-declared null reading, quoted from Addendum A section C: *"C1 null: item
order does not matter at these budgets on this corpus; the elicitation-budget
curve (EXP4 shape) is the deliverable."*

## (b) A population-derived fixed order beats both, at a tenth of the compute

**C2.** Adaptive versus the fixed order, at both checkpoints:

| k | decoding | adaptive MAE | fixed MAE | adaptive − fixed | 95% CI | p |
|---|---|---|---|---|---|---|
| 12 | EV | 1.4370 | 1.4298 | −0.0071 | [−0.0168, +0.0025] | 0.147 |
| 12 | argmax | 1.4341 | 1.4407 | +0.0066 | [−0.0095, +0.0227] | 0.419 |
| 20 | EV | 1.4269 | 1.4082 | **−0.0187** | [−0.0264, −0.0109] | **2.53e-06** |
| 20 | argmax | 1.4316 | 1.4157 | **−0.0159** | [−0.0290, −0.0028] | **0.0174** |

At k=12 there is no detectable difference, and the two decodings disagree on
sign — the only such disagreement among the six frozen contrasts. At k=20 the
fixed order is ahead, significantly, under **both** decodings.

C2 was pre-registered with both readings written in advance and equal
prominence. The one that applies is the second:

> adaptive > fixed (p < .05): uncertainty-guided ordering adds value
> beyond any static script.
>
> **fixed >= adaptive: a well-chosen static questionnaire suffices at these
> budgets — this is the honest headline, not a failure to report.**

**The cost side, pre-registered as mandatory alongside either reading.**
Measured on this run:

| arm | interview-time model calls | node-hours | multiple |
|---|---|---|---|
| fixed | 70,000 | 0.426 | 1× |
| adaptive | 840,000 | 3.928 | **12× calls, 9.2× node-hours** |

770,000 of the adaptive arm's calls are item-selection calls — the cost of
deciding what to ask. The contract predicted ~5–12×; calls landed at the top of
that band, node-hours inside it. The fixed order's own cost is one offline
derivation: greedy ridge regression on 2,000 persons, no model involved, CPU
only. So adaptive spent roughly nine times the GPU time to land 0.019 MAE
*worse*.

**The pre-registered information-source framing, quoted in full because it is
required in full and because it is the correct caveat on this result:**

> "This contrast compares a population-optimized static questionnaire
> (derived from 2,000 persons' observed outcomes) against
> individually-adaptive selection that uses no outcome data. They consume
> different information: fixed-order encodes population history; adaptive
> personalizes per respondent. A fixed >= adaptive result therefore
> means historical outcome data suffices at these budgets — not that
> personalization is worthless in settings without such history (cold
> start, new domains)."

Read it as a statement about information, not about algorithms. The static order
is not smarter; it is carrying 2,000 people's outcomes that the adaptive policy
never sees. Where that history does not exist, this result says nothing.

## (c) Negative transfer is real and robust

**The strongest decoding-robust result of the run.** The imposter arm gets a
different person's demographics and revealed answers, at the same reveal
positions, and still has to predict the test person's TIPI items. It performs
*worse than knowing nothing at all*, at every budget, under both decodings:

| k | imposter lift over baseline, EV | argmax |
|---|---|---|
| 1 | −0.0576 | −0.0858 |
| 2 | −0.0563 | −0.1063 |
| 4 | −0.0545 | −0.1113 |
| 8 | −0.0693 | −0.1504 |
| 12 | −0.0623 | −0.1391 |
| 16 | −0.0586 | −0.1303 |
| 20 | −0.0627 | −0.1486 |

At k=20: −0.0627 EV (p=3.3e-13) and −0.1486 argmax (p=8.8e-32). Raw MAEs at
k=20: imposter 1.5389 EV / 1.5861 argmax, against a baseline of 1.4762 /
1.4375.

Two things make this the run's most solid finding. It is **larger** under the
robustness decoding rather than smaller — the only headline result of which that
is true. And it **replicated**: Addendum A section C pre-declared a null reading
for the case where the pilot's negative-transfer observation failed to hold at
confirm scale, and that reading does not apply.

The own-versus-imposter contrast (C3's second half) is correspondingly strong:
+0.1078 EV (p=9.3e-32), +0.1525 argmax (p=4.5e-32).

**What it means.** A coherent profile belonging to the wrong person is not
neutral noise — it actively misleads. The twin commits to a person and predicts
that person. An earlier experiment adds a sharper edge: making the wrong person
*more similar* to the right one did not reduce the harm (nearest-neighbour minus
random-stranger imposter, p≈0.83–0.92 on the training split). Plausibility does
not soften a wrong-person profile.

**Scope limit, stated because it is easy to over-read.** This imposter is a
random *different respondent* and measures generic-profile harm. Stage 2's
same-domain imposter is a different construct and its results must not be
conflated with this one.

## (d) The decoding caveat: grounding value at partial budgets is weak

**C3 passed.** At k=20, own (the random-order arm) minus baseline and own minus
imposter are both above zero with p < .05 under the primary EV metric, and both
hold in direction under argmax, which is all the binding rule requires.

**But the own-versus-baseline half is decoding-fragile, and the honest reading
has to say so:**

| contrast | EV | argmax |
|---|---|---|
| own − baseline lift at k=20 | **+0.0451** [+0.0330, +0.0572] p=6.3e-13 | **+0.0039** [−0.0148, +0.0226] p=0.682 |
| baseline arm raw MAE | 1.4762 | 1.4375 |
| own arm raw MAE at k=20 | 1.4311 | 1.4336 |

For completeness, the other half of C3 with its intervals: own − imposter
+0.1078 [+0.0903, +0.1252] p=9.3e-32 under EV, +0.1525 [+0.1280, +0.1770]
p=4.5e-32 under argmax.

Look at which arm moves. Switching to argmax improves the **baseline** arm by
0.0387, while the own arm moves 0.0025 in the wrong direction. Almost the entire
EV-measured gap between knowing twenty real answers and knowing nothing is the
baseline being damaged by expected-value decoding — not the twin being helped by
the reveals.

Addendum A predicted this failure mode in the rule that catches it:

> Rationale: EV decoding shrinks variance and can inflate lift by damaging
> the hedging baseline (`results/rescore_ev_vs_argmax.md`).

The mechanism: with no information the model hedges toward the middle of the
scale. Averaging a hedged distribution produces a number near 4, which is a poor
point prediction; taking its argmax produces a plausible integer. EV decoding
therefore penalises the uninformed arm more than the informed one, and the gap
between them is partly an artifact of that.

**So the claim Stage 1E can defend is narrow:** twenty interest answers produce
a measurable improvement under the pre-registered primary metric, and
essentially nothing under the robustness metric. **Absolute grounding value at
partial budgets is weak.** Anyone quoting the +0.045 must quote the +0.004
beside it.

**What this does not undermine.** Two things survive intact. The
own-versus-imposter contrast is unaffected and grows under argmax — person-
specific signal is real even where absolute lift is fragile. And this is not a
verdict on the metric in general: the Stage 1 gate, at the full 48-item budget,
read +0.0954 EV and +0.0479 argmax (p=0.0013) — halved, but significant and
robust. That comparison spans different splits and different budgets, so it is
exploratory rather than a confirm number, but it points at **twenty items being
too few** rather than at EV having been the only thing that ever worked.

## (e) The budget curves, as the pre-declared deliverable

Since C1 is null, its pre-declared reading makes the curve itself the product.
Lift over the demographics-only baseline, EV / argmax:

| k | random | fixed | adaptive | imposter |
|---|---|---|---|---|
| 1 | +0.0005 / −0.0040 | −0.0009 / −0.0160 | −0.0113 / −0.0240 | −0.0576 / −0.0858 |
| 2 | +0.0063 / +0.0011 | +0.0212 / −0.0030 | −0.0001 / −0.0160 | −0.0563 / −0.1063 |
| 4 | +0.0185 / +0.0054 | +0.0374 / +0.0159 | +0.0163 / −0.0022 | −0.0545 / −0.1113 |
| 8 | +0.0122 / −0.0276 | +0.0373 / −0.0177 | +0.0189 / −0.0204 | −0.0693 / −0.1504 |
| 12 | +0.0349 / +0.0001 | +0.0463 / −0.0035 | +0.0392 / +0.0032 | −0.0623 / −0.1391 |
| 16 | +0.0398 / +0.0111 | +0.0585 / +0.0062 | +0.0511 / +0.0176 | −0.0586 / −0.1303 |
| 20 | +0.0451 / +0.0039 | +0.0680 / +0.0218 | +0.0493 / +0.0059 | −0.0627 / −0.1486 |

Descriptive readings, no bar attaches to any of them:

- **Nothing saturates by k=20 under EV.** Every informed arm is still climbing
  at the last checkpoint. The training split suggested the fixed order flattens
  around k=16; on the confirm split it goes +0.0463 → +0.0585 → +0.0680 across
  k=12, 16, 20. Whatever saturation exists is past this grid.
- **Under argmax, almost nothing is reliably positive.** The single exception is
  the fixed order at k=20 (+0.0218, p=0.037). The fixed order is the only policy
  that buys a decoding-robust improvement at these budgets.
- **The first question can hurt.** Adaptive at k=1 is significantly *worse* than
  baseline under both decodings (−0.0113 EV p=0.003, −0.0240 argmax p=0.0002).
  Asking the model's most-uncertain question first is an actively bad opening
  move. One item of any kind is not enough to help, and a strange one distracts.
- **A non-monotonic dip at k=8** appears in every informed arm under argmax
  (random −0.0276, fixed −0.0177, adaptive −0.0204) and not under EV. Unexplained.
  Flagged rather than interpreted.
- **Budget-recovery fractions are not computable here.** The frozen grid stops at
  k=20, so this split has no all-48 full-information denominator. Borrowing the
  training-split or gate denominator would be a split violation. The
  training-split figure ("k=20 recovers 62% of full-information lift") is an
  EV-decoded training-split number and does not transfer.

## (f) Methods lessons

These are the transferable part, and they cost real compute to learn.

**1. Derive on a disjoint split or do not believe the number.** This is the
single clearest lesson, and Stage 1E learned it twice. Anything tuned and then
measured on the same people is inflated: the pilot's fixed order by +0.014,
the adaptive configuration by roughly its whole effect. The fixed order derived
on 2,000 disjoint persons replicated almost exactly (+0.074 → +0.068). Selecting
a variant is tuning, even when it feels like just picking the best of a few.

**2. Report both decodings, always.** Making dual decoding *binding* rather than
advisory is what turned a would-be headline ("grounding on 20 answers gives
+0.045 lift, p=6e-13") into an honest one. A pre-registered robustness check is
only worth having if it can change what you are allowed to claim. It did here.
The general form: when a metric requires collapsing a distribution to a point,
check whether your effect lives in the collapse rather than in the data.

**3. Watch which arm moves.** A lift is a difference, and a difference can grow
because the baseline got worse. Reporting both arms' raw MAEs beside every lift —
a rule adopted after the earlier decoding work — is what made the C3 caveat
visible at a glance instead of requiring a separate investigation.

**4. Cost is a result, not an overhead line.** Adaptive selection's 9.2× GPU
multiple is as much a finding as its null effect. A policy that needs an order of
magnitude more compute to match a static script has been evaluated, and the
answer is legible only if both currencies were logged from the start.

**5. Selection-bias autopsies are cheap and worth doing.** Re-deriving the fixed
order honestly on a disjoint split cost about 0.2 node-hours and produced a
calibrated estimate of what in-split selection was worth. Having that number in
hand made the C1 null immediately interpretable instead of mysterious.

**6. An imposter arm earns its cost.** The zero-information baseline can be
beaten by generic population knowledge. The imposter arm is what separates
"knows about people" from "knows about this person" — and on this run it is the
one contrast robust to every analysis choice.

## Limitations

- **One corpus.** The pre-registered 16PF replication was cancelled on the
  evidence of its own data recon (`results/16pf_closure_note.md`): 16PF has no
  genuine cross-domain split. Corpus-generality is therefore untested, and
  nothing here should be read as established beyond RIASEC.
- **One model.** Gemma-4-31B-it + v2 only. Amendment A3's two-model requirement
  applies to Stage 2 headlines, not to Stage 1E, so the decoding fragility in
  particular may be model-specific.
- **k ≤ 20.** The frozen grid does not reach the full 48 items, so this run
  cannot say where the curves saturate.
- **Survey replay is not an interview.** Revealing recorded answers one at a time
  is not conversation. Stage 1E constrains what to expect from adaptive
  elicitation; it does not settle it for a live interviewer, where question
  wording, rapport, and what a person volunteers all matter and none of them
  exist here.
- **Stage 1 remains development-only** by the original registration. Stage 1E is
  confirmatory within its own frozen bars, and those bars are about elicitation
  policy on this corpus — not about twin fidelity in general.

## Provenance

| item | where |
|---|---|
| frozen bars | `PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md` (commit `3b8dd57`) |
| full verdicts, all tables | `results/stage1e_confirm_report.md` |
| analysis artifact | `results/stage1e_confirm/analysis.json` |
| run driver | `experiments/confirm_run.py` (commit `713c43c`) |
| report generator | `experiments/confirm_report.py` |
| training-split predecessors | `results/overnight_stage1e.md`, `results/adaptive_pilot_train.md` |
| decoding groundwork | `results/rescore_ev_vs_argmax.md` |
| 16PF cancellation | `results/16pf_closure_note.md`, `results/16pf_recon.md` |

Total confirm-run cost: **5.27 node-hours**, 1,060,000 model calls, $0 in API
spend. Per-arm ledger in `results/cost_log.jsonl`.
