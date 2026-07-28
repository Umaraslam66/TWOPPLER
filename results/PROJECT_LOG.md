# Project DOPPLER — project log

Last updated 2026-07-28.

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

Four frozen documents, in order. They are never edited, summarised in place, or
moved. Later documents override earlier ones where they conflict.

| document | what it added | status |
|---|---|---|
| [`PREREGISTRATION.md`](../PREREGISTRATION.md) | The original contract: stages, hypotheses H1–H5, bars, the lift-over-baseline rule. | frozen |
| [`PREREGISTRATION_AMENDMENT_1.md`](../PREREGISTRATION_AMENDMENT_1.md) | A1 same-domain imposter arm mandatory, A2 ceiling numbers descriptive only, A3 two-model replication for headlines, A4 distractor controls, A5 the ≥80-subject power branch, plus Stage 1E inserted before Stage 2. | frozen |
| [`PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md`](../PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md) | Stage 1E's bars, locked before the confirm split was drawn: C1, C2 with both readings pre-written, C3, binding dual decoding. | frozen |
| [`PREREGISTRATION_AMENDMENT_2.md`](../PREREGISTRATION_AMENDMENT_2.md) | **Adopted 2026-07-26**, commit `9949c9d`. B7 new hypothesis H7 (twin staleness, co-headline with H1, with a pre-declared crossover statistic); B8 individual-level lift and population-level TVD reported side by side everywhere; B9 positioning, Stage 3 demoted to optional demo and **H4 withdrawn** as a documented deviation; B10 the revised Stage 2 instrument (generated same-question counterfactuals), forced by the two pilots below. | frozen |
| [`PREREGISTRATION_AMENDMENT_3.md`](../PREREGISTRATION_AMENDMENT_3.md) | **Adopted 2026-07-27**, commit `7548bc3`. C1 declares forced choice dead by pre-committed kill rule (four dev-pilot rounds, zero-info solved every item; a claimable, scoped negative finding); C2 the replacement instrument — open-ended generation, scored by a pinned local embedding model and a rubric-locked stance judge, no claim on one channel alone; C3 own-minus-imposter primary, robustness absolute scores explicitly secondary; C4 a dev validation gate with a pause-for-design-review branch; C5 hypotheses transfer, magnitude bars re-set at bar-lock. | frozen |

**External timestamping.** [`results/osf_preregistration_snapshot.md`](osf_preregistration_snapshot.md)
is a frozen copy of the pre-registration plus Amendment 1, prepared for OSF.
[`results/osf_preregistration_snapshot_v3.md`](osf_preregistration_snapshot_v3.md)
is the current one, covering all five documents with per-document commit and
sha256 provenance; v2 and the original are kept verbatim. **The OSF upload
itself is still outstanding on the owner.** Until it happens, "pre-registered"
means "committed to git before the data was touched", which is weaker.

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

## 10. What is open right now

1. **The open-ended dev pilot RAN and its C4 gate PASSED** (2026-07-27,
   directional, not powered) —
   [`results/stage2_openended/OE1_PILOT_REPORT.md`](stage2_openended/OE1_PILOT_REPORT.md).
   Own beat imposter on the primary model in both channels (embedding
   +0.1024, stance +0.1818); the imposter-arm UNCLEAR asymmetry and the
   topic-overlap diagnostic are reported beside the verdict. The pilot
   also caught and fixed a judge defect (hidden thinking made labels
   budget-dependent; pinned to thinking-off, 512 tokens). Next: the
   owner's ≥50-label judge spot-check (sheets A/B/C ready), then the
   addendum's [TO FILL] slots.
2. **The bar-lock addendum is ADOPTED** ([`PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`](../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md),
   commit `bcd1d51`, 2026-07-28). The road there, all on the record in
   [`results/stage2_openended/AUDIT_LINES_2026-07-28.md`](stage2_openended/AUDIT_LINES_2026-07-28.md):
   slots filled from OE-1; audits under documented deviations D1–D4; the
   pre-committed judge trust bar (raw ≥ 0.80 AND κ ≥ 0.60) **FAILED on the
   first tranche** (0.7778 / 0.5789); the pre-committed iteration ran once —
   rubric r2 (three edits matching the three adjudicated judge failure
   modes), regression broke 0 of 14 previously-correct rows, and the fresh
   F/G tranche **PASSED** (0.8889 / 0.7978), verdicts mechanical, bar never
   moved. Judge pinned: gemini-3.5-flash + rubric r2 + widened parser.
   OSF snapshot v4 covers all six documents
   ([`results/osf_preregistration_snapshot_v4.md`](osf_preregistration_snapshot_v4.md));
   the upload remains on the owner. **A confirmatory launch plan now awaits
   the owner's explicit GO:** [`STAGE2_LAUNCH_PLAN.md`](../STAGE2_LAUNCH_PLAN.md)
   (provisional seeded draw of 140 with printed disjointness proof, H1+H7
   batched generation, caps, risk table, report skeleton). The H6/B3
   parameter spec is being drafted separately and gates H6 scoring only.
3. **Three owner human tasks gating the freeze:** the 20-row fuzzy-host
   spot-check (sheet ready at
   [`results/stage2_pilot2/barlock/fuzzy_host_spotcheck_sheet.md`](stage2_pilot2/barlock/fuzzy_host_spotcheck_sheet.md)),
   the H6 classifier ≥100-label trust audit (B2.2), and the ≥50 judge-label
   spot-check (Amendment 3 C4.2, only possible after the dev pilot runs).
4. **The staff-reserve spot-check** — 20 dossiers, human task, owner only
   ([`results/staff_reserve_spotcheck.md`](staff_reserve_spotcheck.md)); gates
   re-admission of the 292-subject reserve, not the freeze.
5. **The OSF timestamp** — snapshot v3 is ready and covers all five documents;
   the upload is still outstanding, still weakening the word "pre-registered".
6. **Magnitude bars and instrument parameters** — set in the addendum after the
   dev pilot, per Amendment 3 C5/C6; until then no magnitude claim exists. The
   B10.8 human detectability line is closed history: waived 2026-07-27 as a
   documented deviation, LLM-rater line substituted, recorded in
   [`PILOT_REPORT_4.md`](stage2_pilot4/PILOT_REPORT_4.md).

## 11. Cost ledger to date

Source of truth: [`results/cost_log.jsonl`](cost_log.jsonl), one line per run.

| item | value |
|---|---|
| entries logged | 68 |
| API spend (Gemini) | **$3.733** (5 rows carry null cost — unpriced models, not zero) |
| Leonardo compute | **12.74 node-hours** |
| Leonardo balance remaining | ~1,008 node-hours (as of 2026-07-27) |
| allocation expires | **2026-09-17** |

Compute is not the constraint. Owner review time is.

## 12. Where everything lives

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
| Why MoE fails on Leonardo | [`moe_failure_note.md`](moe_failure_note.md) | — |
| Superseded documents | [`results/archive/`](archive/) | — |
| Cost ledger | [`cost_log.jsonl`](cost_log.jsonl) | every run driver |

Working notes live in `memory/` (untracked, not part of the record).
`memory/stage1-closed.md` holds the closed Stage 1 and 1E notes;
`memory/stage2-*.md` are the live ones.

## 13. Six things this project learned the hard way

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
