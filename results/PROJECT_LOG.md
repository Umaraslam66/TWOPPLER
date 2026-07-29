# Project DOPPLER — project log

Last updated 2026-07-28, after the stop-point-iii rulings. Project complete for
this version; one paste job open (§12).

## 1. What this file is, and what it is not

This is a map. It says what happened, in what order, and where the real document
lives. It is **not** a contract and it is **not** the source of truth for any
number. Every figure below carries a link to the report it came from; if this log
and that report disagree, the report wins. If this log and
[`PREREGISTRATION.md`](../PREREGISTRATION.md) or its amendments disagree, the
pre-registration wins, always. Nothing here is ever cited as a result.

Read this first when you pick the project up cold. Then read the pre-registration.

## 2. The project in five sentences

DOPPLER tests whether a language-model "twin" of a specific person, built from
things that person has actually said, can predict that person's held-out answers
better than a model that knows nothing about them. The only metric that counts is
**lift over a zero-information baseline** — raw accuracy is never reported alone,
because a good-looking accuracy usually means the task was easy, not that the
twin knew anything. Stage 1 was development and tuning on survey data (RIASEC →
TIPI), and produced no claims beyond a sanity gate. Stage 1E asked whether
choosing interview questions adaptively beats a fixed order, and is now closed.
Stage 2 is the real study: real people, real interview transcripts, predicting
what a person says in their next public interview from their earlier ones.

Stage 2's honest object is **the public persona**, not the private individual.
That sentence belongs in every write-up.

## 3. The governance chain

Six frozen documents, in order. They are never edited, summarised in place, or
moved. Later documents override earlier ones where they conflict.

| document | what it added | status |
|---|---|---|
| [`PREREGISTRATION.md`](../PREREGISTRATION.md) | The original contract: stages, hypotheses H1–H5, bars, the lift-over-baseline rule. | frozen |
| [`PREREGISTRATION_AMENDMENT_1.md`](../PREREGISTRATION_AMENDMENT_1.md) | A1 same-domain imposter arm mandatory, A2 ceiling numbers descriptive only, A3 two-model replication for headlines, A4 distractor controls, A5 the ≥80-subject power branch, plus Stage 1E inserted before Stage 2. | frozen |
| [`PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md`](../PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md) | Stage 1E's bars, locked before the confirm split was drawn: C1, C2 with both readings pre-written, C3, binding dual decoding. | frozen |
| [`PREREGISTRATION_AMENDMENT_2.md`](../PREREGISTRATION_AMENDMENT_2.md) | **Adopted 2026-07-26**, commit `9949c9d`. B7 new hypothesis H7 (twin staleness, co-headline with H1, with a pre-declared crossover statistic); B8 individual-level lift and population-level TVD reported side by side everywhere; B9 positioning, Stage 3 demoted to optional demo and **H4 withdrawn** as a documented deviation; B10 the revised Stage 2 instrument (generated same-question counterfactuals), forced by the two pilots below. | frozen |
| [`PREREGISTRATION_AMENDMENT_3.md`](../PREREGISTRATION_AMENDMENT_3.md) | **Adopted 2026-07-27**, commit `7548bc3`. C1 declares forced choice dead by pre-committed kill rule (four dev-pilot rounds, zero-info solved every item; a claimable, scoped negative finding); C2 the replacement instrument — open-ended generation, scored by a pinned local embedding model and a rubric-locked stance judge, no claim on one channel alone; C3 own-minus-imposter primary, robustness absolute scores explicitly secondary; C4 a dev validation gate with a pause-for-design-review branch; C5 hypotheses transfer, magnitude bars re-set at bar-lock. | frozen |
| [`PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`](../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md) | **Adopted 2026-07-28**, commit `bcd1d51`. The bar lock: instrument parameters filled from the dev pilot, the judge pinned (gemini-3.5-flash + rubric r2 + widened parser), the magnitude units re-set for continuous scales (≥ +0.05 cosine, ≥ +0.09 stance points), and the two-part classifier trust gate. | frozen |

**Errata.** Frozen documents are never edited, so corrections go in one place:
[`PREREGISTRATION_ERRATA.md`](../PREREGISTRATION_ERRATA.md) at the repository
root. Two entries so far, both filed 2026-07-28: **E1**, Amendment 3 C1 cites
`results/stage2_pilot3/PILOT_REPORT_4.md` when the file is in
`results/stage2_pilot4/` (a path typo; the cited content is correct); **E2**,
B7's pre-declared pooled crossover statistic compares bin-level arm means
without the equal-subject-set guard the same driver applies before printing a
per-bin difference (the frozen definition was applied as written for this
project; the caveat is recorded for any future use).

**External timestamping.** [`results/osf_preregistration_snapshot.md`](osf_preregistration_snapshot.md)
is a frozen copy of the pre-registration plus Amendment 1, prepared for OSF.
[`results/osf_preregistration_snapshot_v4.md`](osf_preregistration_snapshot_v4.md)
is the current one, covering all six documents with per-document commit and
sha256 provenance; v3, v2 and the original are kept verbatim.

**Snapshot v4 is now REGISTERED: 2026-07-28 at https://osf.io/qz28m**, on the
associated project https://osf.io/74bq3. The registration carries the name
**TWOPPLER**; **DOPPLER** is the internal codename used in the pre-registration,
this log and the `src/doppler` package — same project. Note the two names when
searching for it.

**The "pre-registered" caveat is now split rather than blanket.** The
registration **postdates** Stage 1, Stage 1E and the Stage 2 H1/H7 confirmatory
run, so for those it is a **retrospective** external timestamp and the
before-data evidence stays the **per-document git commits and sha256es** in
snapshot v4. It **predates** the H6 confirmatory-subject scoring, the H5
substituted analysis and the D_min = 3 arm, so for those it is **prospective**.
The registration summary itself is not quotable yet — it is inside OSF's
approval window and not publicly readable, and it is never paraphrased as a
quote.

## 4. Stage 1 — development and tuning (24–25 July)

Development only. Nothing from Stage 1 is a claim except the gate verdict.

Pilot 2 ran 12 model×variant cells (Gemini / Qwen3.6-27B / Gemma-4-31B × v0–v3,
n=50) — [`results/pilot2_comparison.md`](pilot2_comparison.md). Two things came
out of it. First, a named finding: open models anchor on the numbers in the
prompt rather than reading the scale, which is why v3's word-based fix helped and
v1's reasoning made it worse — [`results/finding_scale_anchoring.md`](finding_scale_anchoring.md),
with the diagnosis in [`results/qwen_failure_note.md`](qwen_failure_note.md).
Second, a split verdict: under the model-selection rule frozen *before* the sweep
([`results/stage1_model_selection_note.md`](stage1_model_selection_note.md)) no
open model qualified, because Gemma's best variant (v2) was not Gemini's best
(v1). That went to the owner rather than being resolved by the agent.

The metric was fixed before the gate: MAE lift is primary, within-1 lift
secondary, exact match last — [`results/stage1_metric_note.md`](stage1_metric_note.md).
The gate's bar and its promotion pre-commitment were written and committed before
any gate call — [`results/stage1_gate_note.md`](stage1_gate_note.md).

**Gate result: PASS** — [`results/stage1_gate_report.md`](stage1_gate_report.md).
Primary arm (Gemini + v2, n=500): MAE lift **+0.0850** [0.0689, 0.1012],
paired t p=6.87e-23, 0 parse failures. Secondary (Gemma-4-31B-it + v2): **+0.0954**
[0.0750, 0.1159], p=1.25e-18, which triggered the pre-committed promotion:
**Gemma-4-31B-it + v2 is the primary simulation model for all later stages**;
Gemini is the robustness check.

## 5. The metric caveat that changed how everything is reported

[`results/rescore_ev_vs_argmax.md`](rescore_ev_vs_argmax.md) is the most reusable
document in the project. Scoring a probability distribution by its expected value
shrinks prediction variance. That helps confident arms and hurts hedging arms —
and baselines hedge. So EV decoding damaged the baseline in all six runs checked
and inflated lift in four of them. The gate survives under argmax, but the
secondary lift halves; the known-answer probe's lift
([`results/probe_known_answer.md`](probe_known_answer.md)) flips sign entirely.

Consequence, now binding: **every contrast is reported under both decodings, with
both arms' raw MAEs beside the lift.** A lift that only exists under one decoding
is a decoding artifact, not a finding. Prior-art grounding for this and the
anchoring finding: [`results/lit_check.md`](lit_check.md).

## 6. Stage 1E — adaptive elicitation (24–26 July), CLOSED

Question: if you can ask someone only k questions before predicting something
else about them, does picking the questions adaptively beat a fixed order?

The training-split pilot said yes, about +0.02 from k≈8
([`results/archive/adaptive_pilot_train.md`](archive/adaptive_pilot_train.md)).
The overnight batch of five experiments then showed most of that edge was an
accident of how ties were broken, and that a fixed order derived on a *disjoint*
2,000-person split scored +0.074 honestly
([`results/overnight_stage1e.md`](overnight_stage1e.md)). Bars were locked in
Addendum A before the confirm split was drawn.

Confirm run, n=1,000, disjoint from everything used before —
[`results/stage1e_findings.md`](stage1e_findings.md), full tables in
[`results/stage1e_confirm_report.md`](stage1e_confirm_report.md):

- **C1 FAILED.** Adaptive minus random at k=12: **+0.0043**, p=0.391. Not a power
  problem — the bar carried a power note giving >95% power for the pilot effect.
  The effect shrank to a fifth of its pilot size, and the reason is visible in the
  same run: the fixed order was derived on disjoint people and replicated
  (+0.074 → +0.068); the adaptive configuration was picked best-of-four on the
  same 150 people it was then measured on, and did not.
- **C2 → Reading B.** At k=20 the fixed order beats adaptive under both decodings
  (+0.0187 EV p=2.5e-06; +0.0159 argmax p=0.017), while adaptive spent 12× the
  model calls and 9.2× the node-hours. Plain reading: **a good static
  questionnaire suffices at these budgets.**
- **C3 PASSED**, with the decoding caveat attached: most of the EV own-minus-baseline
  lift is the hedging baseline being damaged. The robust contrast is own minus
  imposter (+0.108 EV, +0.153 argmax).
- **Negative transfer replicated.** A coherent wrong-person profile scores *below*
  knowing nothing, at every k, under both decodings. The most decoding-robust
  result in the project.

A later descriptive re-analysis priced the budget curves in respondent seconds
instead of items — [`results/stage1e_timecost_note.md`](stage1e_timecost_note.md).
It changes no verdict, and says so up front: k=20 is about 92 seconds of a
person's attention, and because every arm asks the same number of items, rescaling
the axis cannot reorder them. What it adds is that adaptive makes the respondent
*wait* while it picks the next question (somewhere between +3% and +840% of
interview wall clock, depending entirely on serving engineering) — a cost the
static order never pays. The static order still wins per second.

## 7. The 16PF replication that was cancelled

Amendment 1 A6 promised a replication of Stage 1E on a second corpus. Addendum A
required a data recon first, precisely so the call could be made on evidence. The
recon ([`results/16pf_recon.md`](16pf_recon.md)) found that 16PF has no genuine
cross-domain split — it is one domain measured 163 ways — so it cannot reproduce
Stage 1E's shape at all. The replication was **cancelled** and Addendum B was
never written: [`results/16pf_closure_note.md`](16pf_closure_note.md).

Cost of that decision, stated plainly: **Stage 1E's findings rest on one corpus.**
This is a documented deviation, not a silent one.

## 8. Stage 2 — the corpus (24–25 July)

Phase A recon: MediaSum alone supports Stage 2 —
[`results/stage2_corpus_recon.md`](stage2_corpus_recon.md), with the parsing
rules and checksums in [`results/stage2_corpus_recon_index.md`](stage2_corpus_recon_index.md)
and the 20-guest hand audit in [`results/stage2_corpus_recon_quality.md`](stage2_corpus_recon_quality.md).
463,596 transcripts (CNN 414k, NPR 49k), spanning 2000 to 2020.

Phase B curation: [`results/stage2_curation_report.md`](stage2_curation_report.md).
The funnel ends at **578 clean candidates** with ≥3 deduplicated substantive
interviews and ≥180 days of span, of which **137 are confirmed long-tail** (no
Wikipedia article under any spelling). The owner chose a **long-tail-biased mix**
rather than an all-long-tail pool, because all-long-tail is tight against the ≥80
target once human review attrition is applied.

Still open: a **292-subject reserve** dropped purely for a role word in a speaker
label, with no staff evidence — [`results/staff_reserve_spotcheck.md`](staff_reserve_spotcheck.md).
The owner's rule is re-admit only with quoted guest-role evidence, and a human
spot-check of 20 first. That spot-check has not happened.

## 9. Stage 2 — the four dev pilots (26–27 July), and what they killed

**Pilot 1** — [`results/stage2_pilot/PILOT_REPORT.md`](stage2_pilot/PILOT_REPORT.md),
design contract snapshot [`results/stage2_pilot/SPEC_v1.7.md`](stage2_pilot/SPEC_v1.7.md).
Six dev subjects. The harness ran end to end — draw, chronological split, Q–A
extraction, distractors, imposter donors, five-arm rendering, guards, Leonardo
run, ingest, scoring. And the result was a **ceiling**: the zero-information
baseline — no excerpts, no name, no date, nothing — solved **all 17** forced-choice
items. Twin-minus-zeroinfo lift was 0 by construction, and A4.3's adversarial
filter emptied every cell. The distractors were other people's answers to
unrelated questions, so topical coherence alone won every item. **Pipeline
validated; nothing about twin fidelity established.**

**Pilot 2** — [`results/stage2_pilot2/PILOT_REPORT_2.md`](stage2_pilot2/PILOT_REPORT_2.md).
One change: every distractor is now a real answer **the same subject** gave in one
of their other interviews. **It did not work. The zero-information arm still solved
every item** — 10 of 10, mean probability mass on the true option 0.94, smallest
margin +0.80. Eight of ten items were rejected by the build-time gate, so no final
item set existed and the prediction phase was never run.

The diagnostic decomposition is the part that matters, because it found the
mechanism (10 items, direction not effect size):

| condition | argmax accuracy |
|---|---|
| standard zero-information | **10/10** |
| entity-stripped (all names, numbers, dates removed) | **10/10** |
| question-blind (host question removed, options unchanged) | **1/10** |

Read it as: named entities carry **none** of the solve. The whole thing rides on
the true answer being the only option that is **responsive to the question shown**.
That is intrinsic to forced choice over verbatim real answers — distractors are by
definition answers to other questions — so no further distractor-sourcing fix can
repair it.

That evidence forced **Amendment 2 B10**: the instrument becomes **generated
same-question counterfactuals**. Every option is a generated answer to the same
question expressing a genuinely conflicting position, every option including the
true one is paraphrased so corpus style cannot mark it, the generator is never a
scored model, and a build-time zero-information gate is the final arbiter. The
claim being scored is reframed accordingly: the twin identifies **the person's
position among plausible alternatives**, not a verbatim transcript answer.

**Bar-lock measurements** for the queued decisions were taken on dev subjects and
CPU only — [`results/stage2_pilot2/BARLOCK_MEASUREMENTS.md`](stage2_pilot2/BARLOCK_MEASUREMENTS.md).
Every number in it is a **proposal**; nothing is frozen. Headline: the D3.2 fuzzy
host threshold of 0.60 is too low — at that setting only 17 of the 120 fires that
actually change a label are the anchor.

**Pilots 3 and 4 (27 July) killed the instrument itself.** Round 3 built the
B10 generated counterfactuals and the zero-information arm solved 15/15 — the
tell moved to register (generated advocacy vs real hedging), world-truth, and
deixis ([`results/stage2_pilot3/PILOT_REPORT_3.md`](stage2_pilot3/PILOT_REPORT_3.md)).
Round 4 fixed all of that under a pre-committed owner kill rule (zero-info
≥ 0.90 → dead, no round 5) and measured **1.00 under both parser readings**:
the register tell inverted instead of disappearing, and a frozen pre-gate
frontier-LLM rater line had predicted exactly that
([`results/stage2_pilot4/PILOT_REPORT_4.md`](stage2_pilot4/PILOT_REPORT_4.md),
design contract [`results/stage2_pilot4/SPEC_v1.10.md`](stage2_pilot4/SPEC_v1.10.md)).
Four rounds, four distractor constructions, four person-blind mechanisms — a
claimable negative methods finding, scoped to this corpus. That fired the
pre-written fallback into **Amendment 3** (adopted 2026-07-27): open-ended
generation, dual-channel scoring, own-minus-imposter primary.

## 10. The confirmatory run (2026-07-28) — H1 PASS

The owner's GO launched confirmatory Stage 2 the same day the bar lock froze.
Full record: [`results/stage2_confirm/STAGE2_CONFIRM_REPORT.md`](stage2_confirm/STAGE2_CONFIRM_REPORT.md)
(numbers in `report_numbers.json`, every stage's generator committed, all
verdicts applied mechanically against the frozen bars).

- **Build:** 140-subject seeded draw (disjointness proven), 89 survived the
  ≥ 3-item floor (63.6%, inside the pre-registered CI); C02502 dropped by the
  answer-leak guard (re-aired test interview) → **88 scored subjects**,
  confirmatory branch holds.
- **H1: PASS.** Both legs (own − imposter, own − zero-info) clear p < .05 in
  the pre-registered direction on the primary model in BOTH channels;
  robustness model agrees. Own − imposter +0.0751 cosine / +0.1211 stance
  (magnitude bars met); own − zero-info +0.0378 cosine (magnitude bar NOT
  met on channel 1) / +0.1155 stance (met).
- **H7: exploratory (36 usable subjects), NO headline.** Channel 1 flat
  (slope ≈ 0, no crossover in range); channel 2 on the primary model shows a
  significantly POSITIVE slope — outside both pre-written readings — and an
  earliest-bin crossover that is not the declared decay pattern; the
  channels disagree, C2.4 forbids a one-channel claim, and the disagreement
  is itself the reported finding.
- **Flags on the record:** imposter-arm UNCLEAR asymmetry fired on both
  models (gaps 0.12–0.21 ≥ the 0.10 threshold); contamination meter live
  (+0.0165 Gemma, +0.0510 flash-lite, matching dev); donor concentration
  (25 donors / 89 arms); two name-resolution defect classes recorded
  (C02240, C02521 — 6 of 140 affected, owner deviation candidates); the S1
  donor-blog line stays a declared miss.
- **Cost:** 0.603 node-hours of the 8 cap, $6.55 API of the $15 cap.

## 11. Closeout (2026-07-28, evening)

Three things closed the confirmatory stage: H6 run end to end, an exploratory
decomposition of the H7 channel disagreement, and the contamination analysis the
pre-registration mandated but nobody had actually run.

### H6 — descriptive, and unresolved

Full record: [`results/stage2_confirm/H6_REPORT.md`](stage2_confirm/H6_REPORT.md).

- **The classifier ran clean.** The frozen follow-up classifier went over the 89
  survivors' grounding transcripts: **7,322 host turns in scope, 0 parse
  failures, 0 turns dropped**, and the follow-up share landed where development's
  did. Build note:
  [`results/stage2_openended/h6_part2_build_note.md`](stage2_openended/h6_part2_build_note.md).
- **The part-2 trust gate PASSED** — raw agreement 0.8833 against the ≥ 0.85
  bar, Cohen's κ 0.7667 against the ≥ 0.60 bar, over 120 rows from 60
  confirmatory subjects. Scored by `experiments/h6_part2_score.py`, committed
  before any co-audit label existed.
- **Two deviations carried into that gate, both owner-directed and both on the
  record.** The auditor line is a blind Opus 5 co-audit standing in for the
  owner's own labels (the D3 pattern from part 1, reported as its own line,
  never pooled with a human one — no human line exists for it). And the tranche
  was ruled up from the pre-registered floor of 60 rows to 120 **while still
  blind**, which adds power without adding bias; the reason was that 30
  FOLLOW-UP rows measure a 20% tripwire in steps of 3.3 points.
- **The D_min = 3 tripwire did not fire.** The confirmatory FOLLOW-UP overturn
  rate came in at **18.33%** against the frozen > 20% line, so that
  pre-committed sensitivity arm was never built. Development's rate was 25%, so
  the arm had been expected to fire; it did not.
- **The branch collapsed to descriptive.** Only **24 of 88** subjects could fill
  both arms to the primary budget, and B3's frozen rule puts anything under 30
  in the descriptive band. No hypothesis test is available, so **neither
  pre-written reading is applied** — not the positive one, not the null. The
  null in particular has to be earned by a powered null, and this is not one: a
  non-significant positive point estimate over 24 people, with the sign
  reversing at the B = 400 dose check.
- **Verdict: H6 UNRESOLVED at confirmatory scale on this corpus.** The operative
  finding is the eligibility shortfall itself — dev supply implied roughly two
  thirds of subjects would be eligible, the confirmatory corpus delivered 27%.
  What this run establishes is that the registered H6 design does not reach
  confirmatory power on MediaSum-derived grounding transcripts at the frozen
  budget.

### H7 — exploratory diagnostics, no verdict change

[`results/stage2_confirm/h7_diagnostics.md`](stage2_confirm/h7_diagnostics.md).
Four angles on the channel disagreement. Nothing in it is a bar, a verdict or a
claim; the reported H7 numbers stay in the confirmatory report.

- The imposter-minus-twin UNCLEAR gap is roughly flat across Δ bins. What spikes
  in the 6-12m bin is the **twin's own** UNCLEAR rate — so the bin carrying
  channel 2's crossover is the bin whose denominator is thinned hardest.
- The era / topic-overlap covariate is measurable between subjects but flat
  within them, and it does not track the channel-2 stance slope. **Era drift is
  not what produces the slope.**
- The slope's sign survives all three UNCLEAR handling rules (frozen,
  count-as-non-match, count-as-half). It is not an artefact of that choice.
- Noted rather than acted on: the pooled crossover statistic compares two arm
  means without the same-subject guard the report driver applies one column to
  its left, so it can fire on a comparison the driver itself declines to print.
- Net: two candidate explanations weakened, one strengthened (channel 2's
  denominators are thin and unevenly thinned). The disagreement is narrowed, not
  resolved, and H7 still gets no headline.

### The large-meter analysis that was mandated and missing

The pre-registration says subjects with a large contamination meter are analysed
separately. The confirmatory report named them but never ran that analysis. It
now does, in a new subsection of
[`STAGE2_CONFIRM_REPORT.md`](stage2_confirm/STAGE2_CONFIRM_REPORT.md):
descriptive, a top-decile split of 9 subjects, no bar attached to any number.
The reading rule travels with the table — own minus zero-info shares a term with
the meter that defines the split and therefore says nothing about contamination;
own minus imposter shares no term and is the row to read. The same report's
header now carries the live OSF registration line instead of the old
outstanding-upload flag (see §3).

### Write-ups — both APPROVED

Both were consistency-passed against the reports and approved by the owner on
2026-07-28. Neither is a source of truth for anything; the reports are.

- [`results/writeups/PAPER1_METHODS.md`](writeups/PAPER1_METHODS.md) — the
  methods paper on the four-round forced-choice failure.
- [`results/writeups/PAPER2_MAIN.md`](writeups/PAPER2_MAIN.md) — the main
  results paper.

H1's headline is **own-vs-imposter**, the contrast Amendment 3 C3 makes primary,
which clears every bar. The **own − zero-info magnitude miss stays top-placed at
equal size**. The two frozen texts point at different contrasts; that is a
post-freeze governance ambiguity, and it is resolved by reporting both fully,
never by choosing.

### H2 withdrawn, H5 substituted (2026-07-28)

- **H2 (selection matters) is WITHDRAWN** as a documented deviation, the same
  route Amendment 2 B9.b used for H4. It was never run, its forced-choice bar
  did not survive the instrument change, and Stage 1E already answered the
  selection-policy question at lower cost with a powered null.
- **H5 (calibration): the registered estimator is UNTESTED under the cap**, with
  an owner-directed substituted analysis reported in its place —
  [`results/stage2_confirm/H5_CALIBRATION.md`](stage2_confirm/H5_CALIBRATION.md).
  The registered k = 10 agreement rate is a constant on temperature-0 records
  and re-running it properly costs 5.6× the node-hour cap and 9.0× the API cap;
  the substitution ran at $0.00 on CPU, found **AUC 0.518** on the primary model
  (0.427 on the only signal a deployed twin could compute), and **no pass/fail on
  registered H5 is claimed anywhere**.

### The exploratory D_min = 3 arm, and a reproducibility finding

- **Owner-ordered exploratory arm at chain depth 3**, run after the registered
  numbers were rendered; **H6's verdict is unchanged** and it is not the
  pre-committed sensitivity arm, whose tripwire never fired. Direction matches
  the registered contrast in all four cells including the B = 400 sign reversal,
  and eligibility halves again, 24 → 12 subjects at B = 1,000 —
  [`H6_REPORT.md` §11](stage2_confirm/H6_REPORT.md).
- **Measured run-to-run generation noise, found by accident in that arm.** 72
  prompts were generated twice at temperature 0 in two Leonardo jobs: only 15/72
  byte-identical, median channel-1 cosine gap **0.0138** (max 0.123), 4/72 stance
  labels flipped — vLLM batch-composition non-determinism, present in every
  number in the record before it became measurable
  ([`H6_REPORT.md` §11](stage2_confirm/H6_REPORT.md)).

### Owner rulings on the record

[`results/stage2_confirm/RULINGS_20260728.md`](stage2_confirm/RULINGS_20260728.md):
the two name-resolution defect classes (C02240, a single-token surname; C02521,
a compound surname spelled inconsistently) are **deferred**. No mid-project pool
amendment, no matcher change, no re-admission — both subjects failed before
generation, so nothing downstream has to move, and the attrition stays visible
in the survival rate instead of being absorbed into it. The pair is carried as
one documented-deviation candidate for a future corpus rebuild. No action this
cycle.

[`results/stage2_confirm/RULINGS_STOPPOINT3_20260728.md`](stage2_confirm/RULINGS_STOPPOINT3_20260728.md):
the **seven stop-point-iii rulings** — both papers approved with H1's headline
set to own-vs-imposter and the magnitude miss kept top-placed; H2 withdrawn and
H5 substituted under caps; the exploratory D_min = 3 arm ordered; the two
co-audit rulings confirmed (120-row tranche sizing, H6 magnitude inheritance via
B3's mirror clause) and two errata approved for filing; future-version inputs
recorded with no action and the staff reserve closed as moot; the OSF
registration recorded as live; and this final pass.

Corrections against the frozen documents live in
[`PREREGISTRATION_ERRATA.md`](../PREREGISTRATION_ERRATA.md) — see §3.

## 12. What is open right now

**Two items.**

1. **The OSF registration summary quote.** The registration is live at
   https://osf.io/qz28m (§3), but it sits inside OSF's approval window and is
   not yet publicly readable, so its summary cannot be quoted. Both papers carry
   a marked slot — *[registration summary, verbatim: pending …]* — for the owner
   to paste the exact text once it is public. **It is never paraphrased as a
   quote.**

2. **The Zenodo publish decision.** A draft deposition with all four PDFs and
   full metadata sits at https://zenodo.org/deposit/21677214 (§16), private
   until published. Owner reviews the draft, then either publishes from the
   web page or runs `python experiments/zenodo_upload.py --publish`.
   Publishing mints the DOI and is **irreversible**.

Closed since the last revision of this list, so nobody re-opens them: the
bar-lock addendum is adopted; the confirmatory launch plan got its GO and ran;
the judge trust bar, the fuzzy-host spot-check and both parts of the H6
classifier trust audit are all satisfied, each under a documented deviation
(D1–D4 and the D3 pattern) recorded in
[`results/stage2_openended/AUDIT_LINES_2026-07-28.md`](stage2_openended/AUDIT_LINES_2026-07-28.md).
The B10.8 human detectability line is closed history — waived 2026-07-27 as a
documented deviation with an LLM-rater line substituted, recorded in
[`PILOT_REPORT_4.md`](stage2_pilot4/PILOT_REPORT_4.md). **Closed at stop point
iii (2026-07-28):** the OSF upload itself, now registered; owner review of the
closeout deliverables, with both papers approved; H2, withdrawn as a documented
deviation; H5, run as a substituted analysis with the registered estimator
untested under cap; and the staff-reserve spot-check, closed as moot.

### For any future corpus version

Recorded, no action in this cycle. None of these changes a number in this
version; all three are inputs to a rebuild if one ever happens.

- **The two name-resolution defect classes** — C02240 (single-token surname) and
  C02521 (compound surname spelled inconsistently), carried as one
  documented-deviation candidate
  ([`RULINGS_20260728.md`](stage2_confirm/RULINGS_20260728.md)).
- **The rubric tensions** surfaced by the judge audit, which the trust bar
  cleared but did not dissolve.
- **The 106 auto-re-admit candidates** in the staff reserve, kept on file with
  the full dossiers ([`staff_reserve_spotcheck.md`](staff_reserve_spotcheck.md),
  [`staff_reserve_dossiers.csv`](staff_reserve_dossiers.csv)). The sheet is
  closed as moot for this version, not discarded.

## 13. Cost ledger to date

Source of truth: [`results/cost_log.jsonl`](cost_log.jsonl), one line per run.

| item | value |
|---|---|
| entries logged | 105 |
| API spend (Gemini) | **$12.60** (5 rows carry null cost — unpriced models, not zero) |
| Leonardo compute | **13.88 node-hours** |
| Leonardo balance remaining | ~1,007 node-hours (~1,008 checked 2026-07-27, ~1.14 spent since) |
| allocation expires | **2026-09-17** |

The closeout phase cost **0.41 node-hours and about $2.01 of API** — the H6
classifier pass, H6 generation on both models, the H6 judge and its canaries;
figures as reported in [`H6_REPORT.md`](stage2_confirm/H6_REPORT.md) section 10.
The exploratory D_min = 3 arm added **0.125 node-hours and $0.2568** on top of
that, under its own separate cap and deliberately kept out of section 10's
projection ([`H6_REPORT.md` §11](stage2_confirm/H6_REPORT.md)); combined H6
totals including it are **$2.264194 and 0.5362 node-hours**. The H7 diagnostics,
the H6 report, the large-meter analysis and the whole H5 substituted analysis
were CPU only and cost nothing.

Compute is still not the constraint. Owner review time is.

## 14. Where everything lives

| what | where | regenerated by |
|---|---|---|
| Stage 1 gate verdict | [`stage1_gate_report.md`](stage1_gate_report.md) | `experiments/gate_report.py` |
| Stage 1 gate bar (pre-committed) | [`stage1_gate_note.md`](stage1_gate_note.md) | — |
| Primary-metric decision | [`stage1_metric_note.md`](stage1_metric_note.md) | — |
| Model-selection rule (pre-committed) | [`stage1_model_selection_note.md`](stage1_model_selection_note.md) | — |
| Pilot 2 model×variant table | [`pilot2_comparison.md`](pilot2_comparison.md) | `experiments/compare_pilot2.py` |
| Anchoring finding / its diagnosis | [`finding_scale_anchoring.md`](finding_scale_anchoring.md), [`qwen_failure_note.md`](qwen_failure_note.md) | — |
| Decoding caveat | [`rescore_ev_vs_argmax.md`](rescore_ev_vs_argmax.md) | `experiments/rescore_ev_argmax.py` |
| Known-answer probe | [`probe_known_answer.md`](probe_known_answer.md) | `experiments/probe_report.py` |
| Prior-art check | [`lit_check.md`](lit_check.md) | — |
| Stage 1E write-up | [`stage1e_findings.md`](stage1e_findings.md) | — |
| Stage 1E full tables | [`stage1e_confirm_report.md`](stage1e_confirm_report.md) | `experiments/confirm_report.py` |
| Stage 1E overnight batch | [`overnight_stage1e.md`](overnight_stage1e.md) | `experiments/overnight.py` |
| Stage 1E budgets in seconds | [`stage1e_timecost_note.md`](stage1e_timecost_note.md) | — |
| 16PF recon and cancellation | [`16pf_recon.md`](16pf_recon.md), [`16pf_closure_note.md`](16pf_closure_note.md) | `experiments/recon_16pf.py` |
| Stage 2 corpus recon and curation | [`stage2_corpus_recon.md`](stage2_corpus_recon.md), [`stage2_curation_report.md`](stage2_curation_report.md) | `experiments/mediasum_index.py` |
| Staff reserve (open task) | [`staff_reserve_spotcheck.md`](staff_reserve_spotcheck.md) | `experiments/reserve_score_v2.py` |
| Stage 2 pilot 1 | [`stage2_pilot/PILOT_REPORT.md`](stage2_pilot/PILOT_REPORT.md) | `experiments/stage2_pilot.py` |
| Stage 2 pilot 1 design contract | [`stage2_pilot/SPEC_v1.7.md`](stage2_pilot/SPEC_v1.7.md) | frozen snapshot |
| Stage 2 pilot 2 | [`stage2_pilot2/PILOT_REPORT_2.md`](stage2_pilot2/PILOT_REPORT_2.md) | — |
| Stage 2 pilot 3 | [`stage2_pilot3/PILOT_REPORT_3.md`](stage2_pilot3/PILOT_REPORT_3.md) | — |
| Stage 2 pilot 4 (kill rule fired) | [`stage2_pilot4/PILOT_REPORT_4.md`](stage2_pilot4/PILOT_REPORT_4.md) | — |
| Stage 2 design contract v1.10 | [`stage2_pilot4/SPEC_v1.10.md`](stage2_pilot4/SPEC_v1.10.md) | frozen snapshot |
| Open-ended dev pilot spec | [`stage2_openended/PILOT_SPEC.md`](stage2_openended/PILOT_SPEC.md) | — |
| OE-1 pilot report (C4 gate PASS) | [`stage2_openended/OE1_PILOT_REPORT.md`](stage2_openended/OE1_PILOT_REPORT.md) | `experiments/stage2_oe1.py report` |
| OE-1 pre-GPU checkpoint + resolutions | [`stage2_openended/CHECKPOINT_PREGPU.md`](stage2_openended/CHECKPOINT_PREGPU.md) | — |
| Owner sheets: judge spot-check A/B/C, H6 audit | [`stage2_openended/`](stage2_openended/) | `experiments/h6_audit_sample.py`, `stage2_oe1.py spotcheck` |
| Bar-lock proposals | [`stage2_pilot2/BARLOCK_MEASUREMENTS.md`](stage2_pilot2/BARLOCK_MEASUREMENTS.md) | `experiments/barlock_*.py` |
| Audit lines and deviations D1–D4 | [`stage2_openended/AUDIT_LINES_2026-07-28.md`](stage2_openended/AUDIT_LINES_2026-07-28.md) | `experiments/oe1_r2_score.py` |
| Stage 2 confirmatory report (H1, H7, contamination) | [`stage2_confirm/STAGE2_CONFIRM_REPORT.md`](stage2_confirm/STAGE2_CONFIRM_REPORT.md) | `experiments/stage2_confirm_report.py` |
| H6 verdict report | [`stage2_confirm/H6_REPORT.md`](stage2_confirm/H6_REPORT.md) | `experiments/h6_report.py` |
| H6 classifier run and part-2 tranche | [`stage2_openended/h6_part2_build_note.md`](stage2_openended/h6_part2_build_note.md) | `experiments/h6_confirm_classify.py`, `h6_part2_tranche.py` |
| H6 part-2 trust gate scoring | [`stage2_openended/h6_part2_score_output.txt`](stage2_openended/h6_part2_score_output.txt) | `experiments/h6_part2_score.py` |
| H7 exploratory diagnostics | [`stage2_confirm/h7_diagnostics.md`](stage2_confirm/h7_diagnostics.md) | `experiments/h7_diagnostics.py` |
| H5 substituted calibration analysis | [`stage2_confirm/H5_CALIBRATION.md`](stage2_confirm/H5_CALIBRATION.md), artifacts in [`stage2_confirm/h5/`](stage2_confirm/h5/) | `experiments/h5_calibration.py` |
| Exploratory D_min = 3 arm and the reproducibility finding | [`stage2_confirm/H6_REPORT.md`](stage2_confirm/H6_REPORT.md) §11 | `experiments/h6_d3_arms.py` |
| Owner rulings, 2026-07-28 | [`stage2_confirm/RULINGS_20260728.md`](stage2_confirm/RULINGS_20260728.md) | — |
| Owner rulings, stop point iii | [`stage2_confirm/RULINGS_STOPPOINT3_20260728.md`](stage2_confirm/RULINGS_STOPPOINT3_20260728.md) | — |
| Errata against the frozen documents | [`PREREGISTRATION_ERRATA.md`](../PREREGISTRATION_ERRATA.md) | — |
| Write-ups (both approved) | [`writeups/PAPER1_METHODS.md`](writeups/PAPER1_METHODS.md), [`writeups/PAPER2_MAIN.md`](writeups/PAPER2_MAIN.md) | — |
| Why MoE fails on Leonardo | [`moe_failure_note.md`](moe_failure_note.md) | — |
| Superseded documents | [`results/archive/`](archive/) | — |
| Cost ledger | [`cost_log.jsonl`](cost_log.jsonl) | every run driver |

Working notes live in `memory/` (untracked, not part of the record).
`memory/stage1-closed.md` holds the closed Stage 1 and 1E notes;
`memory/stage2-*.md` are the live ones.

## 15. Seven things this project learned the hard way

1. **Derive on a disjoint split or do not believe the number.** Learned twice.
   Selecting a variant counts as tuning. The pilot's fixed order was inflated by
   +0.014; the adaptive configuration by roughly its entire effect.
2. **Dual decoding is binding, not advisory.** Report EV and argmax for every
   contrast, next to both arms' raw MAEs. It turned a would-be headline
   (+0.045, p=6e-13) into an honest +0.004.
3. **Watch which arm moves.** A lift can grow because the baseline got worse. You
   only see that if the raw MAEs sit beside the lift.
4. **Cost is a result.** Log both currencies from the start. A 9.2× GPU multiple
   for a null effect is itself a finding.
5. **The imposter arm earns its cost.** It is the contrast that separates "knows
   about people" from "knows about this person", and it was the only Stage 1E
   result robust to every analysis choice.
6. **Expect the pilot effect to shrink.** Three for three now, counting the two
   Stage 2 ceilings: nothing that looked good at pilot scale on this project has
   survived at full size unchanged. When a result looks surprisingly good, hunt
   for the leak before celebrating.
7. **Project the supply, not just the effect — and expect that to shrink too.**
   H6 made this the third instance of pilot-to-scale shrinkage, and the first
   where what shrank was how many subjects the design could even use: dev supply
   implied about two thirds eligible, the confirmatory corpus delivered 27%, and
   a hypothesis that was fully powered on paper landed in the descriptive band
   before a single score was computed. Six dev subjects cannot tell you what
   eighty-eight real ones will supply. Measure eligibility on a realistic draw
   before freezing the budget that defines it.

## 16. Publication pass (2026-07-29, afternoon)

The write-ups became publishable artifacts. Four things happened, all on main:

1. **Style and authorship.** Em dashes removed from the article and both papers
   (the only survivors are inside verbatim quotes of frozen registration text,
   which are never altered). Authors are now explicit in all documents and on
   the PDF title blocks: Umar Aslam and Claude (Fable 5, Anthropic), with the
   role split stated; "we" means the two of them. Draft banners replaced with
   dated front matter.
2. **Citation verification and integration.** Every external citation checked
   by live lookup; the full memo is
   [`lit_check_v2.md`](lit_check_v2.md) (68 new verified entries, zero
   fabricated works found among the existing ones). Corrections applied: Park
   et al. updated to its 2026 record (0.83 for the interview-grounded arm, their
   0.74 demographics-only baseline quoted beside it); MediaSum finally cited
   (Zhu 2021; Majumder 2020 for the NPR half); Cohen 1960 at the kappa bars;
   encoder and model provenance cited. New positioning citations integrated
   into both papers (Chandak 2025, Reinhart 2025, Aggazzotti 2024, Morocho
   2026, Jia 2026, Choi 2010, ethics anchors). Paper 2 gained a References
   section. No measured number, verdict or bar changed anywhere.
3. **A consolidated preprint.**
   [`writeups/PREPRINT.md`](writeups/PREPRINT.md) (19 rendered pages) combines
   the methods story and the results into the one publishable paper; every
   number machine-checked verbatim against the two companion papers; the
   magnitude-bar miss travels beside the H1 pass at equal prominence.
4. **Zenodo automation and draft.** `experiments/zenodo_upload.py` (draft-first,
   stdlib only, state in [`zenodo_deposition.json`](zenodo_deposition.json))
   created deposition 21677214 with all four PDFs and CC-BY 4.0 metadata.
   Nothing is public; the publish decision is §12 item 2.
