# Person-blind signal dominates forced-choice evaluation of interview-grounded twins

**Methods paper — DRAFT for owner review, 2026-07-28.**

Every number below links to the report or script that produced it. Nothing here
is a new analysis; this is assembly of a record that is already committed.

---

## 1. The point, up front

We tried to measure how well a language-model "twin" of a real person predicts
what that person says in a later interview. The measurement instrument was
forced choice: show the twin a real question from a held-out interview, show it
the person's real answer hidden among three wrong ones, and see if it picks the
right one.

**It does not measure the twin.** We built four versions of that instrument,
each fixing the previous version's flaw, and in all four a *person-blind*
baseline — a prompt with no name, no excerpts, no date, no information about the
person at all — solved essentially every item.

| round | where the wrong options came from | person-blind accuracy | what gave it away |
|---|---|---|---|
| 1 | other people's answers to other questions | **17 / 17** | topical coherence |
| 2 | the same subject's answers to other questions | **10 / 10** | responsiveness to the question shown |
| 3 | generated answers to the *same* question | **15 / 15** | register, world-truth, deixis |
| 4 | round 3 + four targeted fixes, subjective items only | **8 / 8** | register *inverted*, entity deployment, stance-vs-premise fit |

Chance is 0.25 in every row. Sources, in order:
[round 1](../stage2_pilot/PILOT_REPORT.md) ·
[round 2](../stage2_pilot2/PILOT_REPORT_2.md) ·
[round 3](../stage2_pilot3/PILOT_REPORT_3.md) ·
[round 4](../stage2_pilot4/PILOT_REPORT_4.md).

Round 4 ran under a kill rule the owner committed to in writing before the round
launched. It fired. There was no round 5.

The claim we make from this is narrow and we hold it to that width: **on this
corpus, with these four constructions, forced choice over a person's verbatim
answers is dominated by signal that requires no knowledge of the person.** We do
not claim forced choice is dead as an evaluation format everywhere.

The paper also reports what replaced it — open-ended generation scored on two
independent channels — together with the full validation trail of that
replacement, including the parts that failed.

---

## 2. What the task is, and what the field does

A **twin** here is a language model whose prompt contains records of one
specific real person, instructed to answer as that person
([PREREGISTRATION.md §2](../../PREREGISTRATION.md)). **Fidelity** is agreement
with the person's real answers on material the twin never saw. **Lift** is
fidelity minus the fidelity of a zero-information baseline — the same model, the
same items, no grounding, identity redacted. Lift is the only headline metric in
this project; a raw fidelity number is never reported without its baseline.

The design target is Park et al. (2024), "Generative Agent Simulations of 1,000
People", commercialised by Simile: an agent grounded in a two-hour interview
reproduces a person's survey answers at roughly 0.85 of that person's own
two-week test-retest consistency. That work uses surveys. We wanted the same
question asked on natural speech, so we used public interviews, where the
held-out data already exists — ground a twin on a person's earlier interviews,
test it on real questions from a later one.

The pre-registered instrument was forced choice
([PREREGISTRATION.md §3, Stage 2](../../PREREGISTRATION.md)): extract
question–answer pairs from the held-out interview, hide the real answer among
three or four distractors drawn from other guests' answers to similar questions,
randomise position, and score whether the twin picks it. It was chosen because it
is cheap, automatic, and has an obvious chance rate. Amendment 1 added distractor
controls — matching, an entity-stripped re-score, an adversarial filter. That is
the instrument the four rounds below tested to destruction.

---

## 3. Corpus and subjects

MediaSum: 463,596 NPR and CNN interview transcripts (CNN 414k, NPR 49k), 2000 to
2020 — [corpus recon](../stage2_corpus_recon.md), with parsing rules and
checksums in [the index](../stage2_corpus_recon_index.md) and a 20-guest hand
audit in [the quality note](../stage2_corpus_recon_quality.md). Curation yields
**578 clean candidate subjects** with at least three deduplicated substantive
interviews and at least 180 days of span, of which **137 are confirmed
long-tail** — no Wikipedia article under any spelling
([curation report](../stage2_curation_report.md)).

All four rounds ran on **development subjects only**: six subjects drawn by a
seeded rule (seed 47, 578-row pool), three with a Wikipedia page and two
long-tail, plus one added after a burn event
([round 1 §1](../stage2_pilot/PILOT_REPORT.md)). One of the six yields no usable
question–answer pairs and is excluded from every prediction set. Dev subjects are
excluded from every confirmatory analysis permanently
([Amendment 2 B4.1](../../PREREGISTRATION_AMENDMENT_2.md)). No confirmatory
subject was touched by any round reported here.

Item counts are small by design — 17, 10, 15 and 8. Enough to see a ceiling, not
enough to size an effect, and every round report says so in its own header.

---

## 4. What the instrument claims to measure

From round 3 onward the options are generated, not harvested, so the claim being
scored changes and the change is binding on every write-up
([Amendment 2 B10.2](../../PREREGISTRATION_AMENDMENT_2.md)):

> The claim scored is that the twin **identifies the person's actual position
> among plausible alternative positions on the same question** — not that it
> picks a verbatim transcript answer.

That reframing matters for reading rounds 3 and 4. A twin that reproduces a
person's stance but not their words should score well. The problem the rounds
document is not that the instrument is too strict about wording; it is that the
real answer is identifiable as *real* without any reference to who said it.

---

## 5. The four rounds

### 5.1 Round 1 — distractors from other people

Three wrong options per item, drawn from other guests' answers to unrelated
questions, similarity-ranked. 17 items over five subjects.

Both arms, side by side ([round 1 §5](../stage2_pilot/PILOT_REPORT.md), driver
[`experiments/stage2_pilot.py`](../../experiments/stage2_pilot.py)):

| arm | items scored | accuracy | probability mass on the true option |
|---|---|---|---|
| twin, identity redacted | 17 | 1.000 | 0.972 |
| twin, named | 17 | 1.000 | 0.985 |
| **zero-information, redacted** | 17 | **1.000** | 0.983 |
| zero-information, named | 17 | 1.000 | 0.991 |
| imposter twin (another person's transcripts) | 17 | 0.941 | 0.885 |

Twin minus zero-information is **0.0000** in accuracy, by construction: both
arms sit on the ceiling. Twin minus imposter is **+0.0500** accuracy and
**+0.0853** probability mass, which is the only structure anywhere in the table
and is not evidence about fidelity either, because the imposter arm is simply
the one arm not pinned at 1.00.

Amendment 1's adversarial filter — drop every item the zero-information arm got
right — removed **all 17 items**. The empty table is the filter working
correctly and saying the instrument is unusable.

The mechanism is visible in the scorer's own words: *"Option B directly
addresses the host's question about American responsibility."* It is matching
topic. The median distractor's question-similarity to the real question was
cosine 0.050, and one item of eighteen had any distractor above 0.10.

**What round 1 established:** the pipeline runs end to end — draw, chronological
split, question–answer extraction, distractors, imposter donors, five-arm
rendering, both leakage guards, cluster execution, ingest, scoring. **What it
established about twins:** nothing.

### 5.2 Round 2 — distractors from the same person

One change: every wrong option is a real answer **the same subject** gave in one
of their other interviews. Speaker is now controlled by construction.

The zero-information arm still solved every item
([round 2 §1](../stage2_pilot2/PILOT_REPORT_2.md)):

    candidate items built                     10
    zero-information accuracy, frozen parser 1.00  (8 of 8 parsed)
    zero-information accuracy, honest reading 1.00  (10 of 10, 2 recovered)
    mean probability mass on the true option  0.94
    smallest margin over the best rival      +0.80
    items rejected by the build-time gate        8 (10 on the honest reading)
    items surviving into a final item set        0

No twin, imposter or contamination number exists for round 2. The prediction
phase was never run — the stop condition was "five or more of ten rejected", and
eight were. The final item set would have been empty regardless.

The diagnostic decomposition is the part that mattered. Three conditions, same
ten items, direction only, not effect size
([round 2 §3](../stage2_pilot2/PILOT_REPORT_2.md), implementation
`src/doppler/diagnostics_v2.py`):

| condition | question shown? | options | accuracy | mean p(true) | mean margin |
|---|---|---|---|---|---|
| standard zero-information | yes | standard | **1.00** | 0.94 | +0.91 |
| entity-stripped (names, numbers, dates removed) | yes | stripped | **1.00** | 0.87 | +0.82 |
| question-blind (host question removed) | **no** | standard | **0.10** | 0.24 | −0.12 |

Read it as: **named entities carry none of the solve; the whole thing rides on
the true answer being the only option that is responsive to the question
shown.** Strip every name, number and date and accuracy does not move. Remove
the question and accuracy falls below the 0.25 chance line, with the margin
going negative and the model hedging.

That is intrinsic to the shape "forced choice among verbatim real answers".
Distractors are, by definition, answers to other questions. No further
distractor-sourcing rule repairs it, and this evidence is what forced the
instrument change registered as
[Amendment 2 B10](../../PREREGISTRATION_AMENDMENT_2.md).

Two secondary constraints surfaced here and both stayed true afterwards. First,
the anti-leak rule starves the item pool: 32 of 100 harvested answers were
excluded because the twin's own grounding block could quote them. Second, a
similarity floor cannot rescue the design at this scale — a floor of 0.10 admits
**zero** items from these pools, 0.05 admits three.

### 5.3 Round 3 — generated counterfactuals to the same question

Every option is now a *written* answer to the same question, taking a position
that genuinely conflicts with the subject's real one. Every option, the real one
included, passes one identical neutralising paraphrase, so corpus style cannot
mark the true option. Distractors are checked for genuine conflict. The
generator (gemini-3.5-flash-lite) never scores anything.

Responsiveness is gone by construction. The ceiling did not move
([round 3 §1](../stage2_pilot3/PILOT_REPORT_3.md)):

    items built                                15   (of 17 eligible)
    zero-information accuracy, frozen parser  1.00   (3 of 3 parsed)
    zero-information accuracy, honest reading 1.00   (15 of 15, 12 recovered)
    mean probability mass on the true option   0.77
    mean margin over the best rival           +0.69   (range +0.30 .. +0.96)
    items surviving into a final item set         0

Again no prediction phase, so no twin or imposter numbers exist for round 3.

Three replacement tells, each quoted from the scorer's own reasoning:

- **Register.** *"Options A, B, and C are written in a highly argumentative,
  polemical style… Option D, however, reflects the typical speaking style of a
  social science professor in a televised interview."* Asked for a genuinely
  conflicting position, the generator writes a confident thesis. Real
  interviewees qualify, digress, and say "it's mixed". The paraphrase cannot fix
  this, because it must preserve every substantive claim and the confidence
  lives *in* the claims.
- **World-truth.** *"Option C reflects the actual political reality of that
  moment… Options A, B, and D suggest a competitive race, which does not align
  with the historical consensus."* If the person's real position is simply
  correct about the world, then every genuinely conflicting alternative is wrong
  about the world, and a well-informed scorer picks the true one on general
  knowledge without modelling anyone. This is structural, not a bug in one item.
- **Deixis.** The tightest item in the set (+0.30) was solved partly on the
  paraphrased true answer retaining the host's first name — a leak of
  conversational packaging that only the real answer has, because only the real
  answer was spoken to a person.

Two hypotheses about *other* tells were frozen before the gate completions were
read, and are reported whichever way they landed. The **polar-question**
hypothesis — that on a yes/no question all three distractors must land on the
same side, making the true answer the lone dissenter — was **rejected**: polar
items 7/7 solved at mean margin +0.633, non-polar 8/8 at +0.740, so the polar
items were solved with *smaller* margins than the others, the opposite of the
prediction. The **naming-register** hypothesis was **not supported as a
systematic property**: the capitalised-entity-overlap proxy was positive on only
4 of 15 items — but the proxy was case-sensitive and missed the case that
prompted the flag, so the honest reading is that register marks the true option
through conversational deixis, not through entity naming.

### 5.4 Round 4 — every fix at once, under a pre-committed kill rule

Round 4 attacked four of the six tells a frontier-model rater had named on round
3's material, under the design frozen in
[SPEC v1.10, D6-v4](../stage2_pilot4/SPEC_v1.10.md):

- generation few-shot conditioned on **the subject's own real answers**, to stop
  the generator writing advocacy;
- **deixis stripped** from all four options or from none, never from some;
- an explicit **plausibility check** on every surviving distractor
  (PLAUSIBLE / FALSE / FRINGE, only PLAUSIBLE accepted), to blunt world-truth;
- **subjective items only**, since round 3's widest margins sat on factual
  questions.

Result, under both parser readings
([round 4 §1](../stage2_pilot4/PILOT_REPORT_4.md)):

| reading | prompts | parsed | zero-information accuracy | mean p(true) | mean margin |
|---|---|---|---|---|---|
| frozen parser (the contract) | 8 | 2 | **1.00** | 0.750 | +0.630 |
| widened reading (reported beside, never instead) | 8 | 8 | **1.00** | 0.694 | +0.558 |

Readings disagreeing on any item: **0**. Items surviving into a final set: **0**.
No twin, imposter or contamination number exists for round 4.

**The fixes worked and it did not matter.** Mean probability mass fell from 0.776
to 0.694 and the mean margin from +0.690 to +0.558. Every item was still solved.
An instrument that only gets harder to solve *confidently* is not getting harder
to solve.

Stated so it is not over-read: round 4 is **not** apples-to-apples with round 3.
Round 4 is eight subjective items; round 3 was fifteen mixed ones, and round 3's
widest item (+0.96, the world-truth case) is excluded from round 4 by design. The
*direction* — 1.00 either way — is comparable. The *size* of the margin drop is
partly a change of item mix.

**The register fix inverted the tell instead of removing it.** Conditioned on the
subject's own speech, the generator stopped writing op-eds and started writing
briefing documents. The real answer says the U.S. failure to act gave Russia,
Assad and Iran "an absolute free ride"; the generated alternatives reach for "the
intelligence community in Langley and the Pentagon", "recent UN Security Council
resolutions", "the Joint Chiefs of Staff". The scorer picked the real one on
*"the biting irony"*. Entity counts were matched within ±2 and six of eight items
sat at the tightest matching rung — matching on a count is not matching on how
entities are *deployed*.

---

## 6. The tell taxonomy

Six mechanisms, none of which requires knowing the person. Each row names the
round that exposed it and what the next round's fix did to it.

| tell | what it is | exposed by | fix attempted | outcome |
|---|---|---|---|---|
| **Topical coherence** | the real answer is the only option about this subject matter | [round 1](../stage2_pilot/PILOT_REPORT.md) | draw distractors from the same person | removed as the dominant tell; topic still separated where a career spans many subjects ([round 2 §2.1](../stage2_pilot2/PILOT_REPORT_2.md)) |
| **Responsiveness** | the real answer is the only option that answers *this* question | [round 2](../stage2_pilot2/PILOT_REPORT_2.md) — question-blind accuracy 0.10 vs 1.00 | generate all options as answers to the same question | **removed** by construction |
| **Register — advocacy vs hedging** | generated positions sound like op-eds; real interviewees hedge | [round 3 §2.1](../stage2_pilot3/PILOT_REPORT_3.md) | few-shot on the subject's own answers | **inverted** — options became bland institutional prose and the real answer was still the one that sounded like a person ([round 4 §2](../stage2_pilot4/PILOT_REPORT_4.md)) |
| **World-truth** | when the real position is correct about the world, every conflicting option is wrong about it | [round 3 §2.2](../stage2_pilot3/PILOT_REPORT_3.md) | plausibility check + subjective-only items | 2 rejections fired (1 FALSE, 1 FRINGE); not decisive in round 4, but the item most exposed to it was excluded by design, so the tell is untested rather than beaten |
| **Deixis** | the real answer carries the host's name and conversational address, because it was spoken to a person | [round 3 §2.3](../stage2_pilot3/PILOT_REPORT_3.md) | strip host names and address from all four options or none | **removed** — stripped on 8 of 8 items, no round-4 trace cites it |
| **Real-voice idiom and entity deployment** | a person with a view uses idiom and names the actors they are actually talking about; generated text name-drops institutions | [round 4 §2](../stage2_pilot4/PILOT_REPORT_4.md) | none — this is what the register fix produced | **unfixed** |

A seventh, **stance-vs-premise fit**, sits across rounds 3 and 4: a leading
question invites a stance, and the rule requiring every distractor to conflict
with the real position puts all three distractors on the side the host did not
invite. Restricting to subjective items makes this worse, not better — leading
questions are more common there.

An eighth, **twin-pair stance inference** (reasoning across two versions of the
same question inside one rating sheet), was named by the rater and closed by a
standing rule: no rater and no scorer ever sees both twins of a duplicated
question, asserted at export rather than assumed
([SPEC v1.10 D6-v4.9](../stage2_pilot4/SPEC_v1.10.md); verified in
`results/stage2_pilot4/twin_check.json`).

The taxonomy has a shape. Rounds 1 and 2 fail because a real answer is
recognisable as *the answer to this question*. Rounds 3 and 4 fail because a real
answer is recognisable as *something a real person actually said*. Removing one
mechanism reveals the next.

---

## 7. The kill rule, and how it was applied

The rule was recorded by the owner on 2026-07-27, **before round 4 launched and
before any round-4 data existed**
([SPEC v1.10 D6-v4.6](../stage2_pilot4/SPEC_v1.10.md), quoted verbatim in
[round 4 §0](../stage2_pilot4/PILOT_REPORT_4.md)):

> **KILL RULE, pre-committed before any round-4 data existed:** if round 4's
> zero-information argmax accuracy is **≥ 0.90**, four-way forced choice is
> **DEAD** on this corpus and there is **no round 5 on any axis**. Rounds 1, 2
> and 3 solved 17/17, 10/10 and 15/15 by three different mechanisms; a fourth
> instrument that also fails is evidence about the format, not about the next
> patch.

Round 4 measured 1.00 under both parser readings. The rule was read on the frozen
number, as written. Phase 2 was not submitted. There is no round 5.

Two supporting facts belong here rather than in a footnote.

**A gate-loosening option was on the table and was not taken.** A margin-relaxed
gate — reject an item only when the person-blind arm solves it by more than some
margin — was specified in advance and explicitly *not adopted for round 4*, on
the grounds that a kill rule means nothing if the bar can move in the round that
tests it. It was made available at bar-lock only if round 4 landed in the grey
zone (clearly below 0.90 and clearly above 0.25). It did not: accuracy was 1.00
and the *smallest* margin in the set was +0.40, wider than round 3's tightest
item. The precondition never arose.

**The fallback was written before the result was known.** The open-ended
replacement design was committed as
`results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md` (commit `71ae352`) while
round 4 was still being built, and was promoted to
[Amendment 3](../../PREREGISTRATION_AMENDMENT_3.md) unchanged in substance after
the rule fired.

---

## 8. The declared finding, and exactly how wide it is

Registered wording, from
[Amendment 3 C1](../../PREREGISTRATION_AMENDMENT_3.md):

> **Declared finding (claimable, scoped):** verbatim-answer forced choice over
> public-interview corpora is dominated by person-blind signal — topic,
> responsiveness, register, world knowledge — across every distractor source
> tested, because a real person's answer differs from any constructed
> alternative in ways that do not require knowing the person. Scope: this corpus
> (broadcast interviews, largely expert subjects) and these constructions;
> stated in all write-ups with the four pilot reports as the record.

Three things sharpen it.

**The leak is in the instrument, not in one scorer.** A frontier model from a
different family than both the generator and the scorer read round 3's option
sets with no information about the speaker and identified the real option **10
times out of 10** against a 0.25 chance rate, with 9 of 10 correct rejections on
controls where no real answer was present, 19/20 overall
([rater line](../stage2_pilot4/DETECTABILITY_RATER_LINE.md), scored and committed
at `ddb3ac6` **before** round 4's gate was submitted, so it is a genuine
prediction). It named six tells; round 4 attacked four; two were fixed, two
inverted or survived, two were untested. A twin scored against such option sets
would earn credit for detecting text provenance, not for modelling anyone.

**Confidence moved, accuracy did not.** Mean margin fell +0.69 → +0.56 across
rounds 3 and 4 while accuracy stayed at 1.00.

**What the finding is not.** It is not "forced choice is a bad format". It is not
a claim about other corpora, other subject populations, or constructions we did
not test. Four rounds is enough to stop paying for a fifth on this corpus; it is
not enough to generalise beyond it.

---

## 9. The replacement, and its validation trail

### 9.1 Design

[Amendment 3 C2](../../PREREGISTRATION_AMENDMENT_3.md) replaces the option set
with free text. The twin answers the held-out question in its own words. No
options exist, so there is no option set to leak.

Scoring runs on two channels that fail differently:

- **Channel 1 — embedding similarity** between the generated answer and the
  person's real answer. A fixed, locally-run model, never an API model and never
  a scored model: `sentence-transformers/all-mpnet-base-v2`, revision
  `e8c3b32edf5434bc2275fc9bab85f82640a19130`, pinned in
  [Addendum A, instrument parameter 1](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md).
- **Channel 2 — a stance judge.** A separate model labels whether the generated
  answer takes the same position as the real one: SAME / DIFFERENT / UNCLEAR,
  under a rubric frozen by hash. Pinned as `gemini-3.5-flash`, temperature 0.0,
  `thinking_budget=0`, `max_output_tokens=512`, rubric r2 sha256
  `ad050d1a…102464` ([Addendum A parameters 2–3](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md)).

Two rules bind the reporting. The primary metric is **own twin minus imposter
twin**, computed identically in both channels, because judge and embedding
biases — verbosity, topic priors, generosity — apply to both arms and cancel in
the difference. And **no headline rests on one channel alone**: a claim requires
direction agreement across both, and disagreement between channels is itself the
reported result.

### 9.2 The dev pilot and its gate — PASS, directional

The C4 validation gate required the instrument to separate own twin from imposter
twin on the primary model, on dev subjects, before any bar could freeze. The
readings were written before the numbers existed
([PILOT_SPEC §7](../stage2_openended/PILOT_SPEC.md)).

17 items, five dev subjects, five arms, both scored models
([OE-1 report](../stage2_openended/OE1_PILOT_REPORT.md), driver
[`experiments/stage2_oe1.py`](../../experiments/stage2_oe1.py)):

| channel | model | own | imposter | own − imposter (95% CI) | subjects own > imposter | paired items |
|---|---|---|---|---|---|---|
| 1 embedding | Gemma-4-31B-it (primary) | 0.6497 | 0.5473 | **+0.1024** (0.0444, 0.1770) | 5 / 5 | 17 |
| 2 stance | Gemma-4-31B-it (primary) | 0.8125 | 0.7273 | **+0.1818** (0.0000, 0.3333) | 2 / 3 | 11 |
| 1 embedding | gemini-3.5-flash-lite (robustness) | 0.6368 | 0.5708 | **+0.0660** (0.0473, 0.1119) | 5 / 5 | 17 |
| 2 stance | gemini-3.5-flash-lite (robustness) | 0.7500 | 0.7143 | **+0.1429** (0.0000, 0.2308) | 2 / 4 | 14 |

One arithmetic caveat, since the columns invite it: on channel 2 the own and
imposter means are computed over each arm's own judged items, while the
difference is paired on the items where **both** sides got a non-UNCLEAR label.
The difference is therefore not the subtraction of the two printed means. Channel
1 has no such gap (0.6497 − 0.5473 = 0.1024).

**Verdict: PASS**, applied mechanically against the pre-written reading — own
beats imposter on the primary model in both channels, and the channels agree.

Three qualifications were published with the verdict, not after it.

1. **Directional, not powered.** 17 items over five subject clusters, one of
   which contributes a single item. Channel 2's confidence interval touches zero.
2. **The UNCLEAR asymmetry is real and it thins the data.** The judge returned
   UNCLEAR on 6 of 17 imposter answers (0.353) against 1 of 17 for the twin
   (0.059) on the primary model — the imposter dodges the question in its donor's
   register. That is itself an own-versus-imposter difference, but it drops the
   stance denominator to 11 items, and a confirmatory design must expect it. The
   robustness model shows the same pattern, smaller (0.177 vs 0.059).
3. **Channel 1's separation is partly topical.** Cosine between the twin's own
   grounding text and the real answer correlates r ≈ **0.74** with the own-arm
   score on the pinned encoder. The design anticipated this — which is why no
   claim rests on channel 1 alone, and why the stance channel, which topic
   overlap cannot satisfy by itself, has to agree. The diagnostic itself is
   partial: the grounding block is ~2,000 words and the encoder truncates it, so
   the number describes the head of the grounding, not all of it. Two figures for
   that window sit on the project's record and both are right about different
   things — OE-1's caveat quotes the 512-token limit of the candidate encoders
   generally, while the later H7 diagnostics quote **384 tokens**, which is the
   pinned `all-mpnet-base-v2`'s configured sequence length and so is the operative
   truncation here ([`h7_diagnostics.md` §2](../stage2_confirm/h7_diagnostics.md)).
   The smaller number makes the caveat stronger, not weaker.

### 9.3 A judge defect, found and pinned

The first judge pass was broken and the record says so
([OE-1 §9](../stage2_openended/OE1_PILOT_REPORT.md)).

Running `gemini-3.5-flash` at 256 output tokens with no thinking setting, 82 of
85 replies came back with the explanation line cut mid-phrase. A two-budget probe
found the cause: the model charges hidden thinking against the output budget and
did not finish thinking at either budget — 243 of 256 tokens, then 980 of 1024,
both ending in truncation.

The damaging part is not the truncation. **The label itself moved between the two
budgets at temperature 0** (DIFFERENT → UNCLEAR). The v1 labels were a function
of the budget, not only of the rubric.

Fix, taken before any re-run: thinking explicitly disabled (`thinking_budget=0`),
budget 512, everything else unchanged. A determinism probe ran first — three
items, two runs, 3/3 identical labels, explanations intact — and only then did
the batches run. v1 and v2 agree on 72 of 85 labels (84.7%) on the same
generations; v1 is retained as the defect record and used for nothing else. Both
settings are now pinned parameters.

### 9.4 The judge trust bar — FAIL, one iteration, PASS

This is the part of the validation trail that failed, and it gets the same space
as the parts that passed. Full record:
[AUDIT_LINES_2026-07-28.md](../stage2_openended/AUDIT_LINES_2026-07-28.md).

**The first audit was inconclusive and diagnosed as our fault.** 51 rows across
three sheets. Human labels on sheet A (17 rows, owner time constraint, recorded
as deviation D1), an out-of-family LLM co-auditor on all 51. The two lines agreed
17/17 on sheet A. Against the judge: human 0.7647 raw / κ 0.556; co-auditor
0.7843 / κ 0.596. But the auditors had been briefed with a *paraphrase* of the
task rather than the frozen rubric text — an audit-protocol defect recorded as
the owner's, not the judge's. The owner adjudicated the four rows where the judge
disagreed with a concordant auditor line: **net 2–2**, two judge-correct, two
auditors-correct.

**The bar was then set, in writing, before its measurement existed:** the judge
passes if and only if **raw agreement ≥ 0.80 AND Cohen's κ ≥ 0.60** against a
rubric-briefed auditor line on a fresh blind tranche. The rationale is on the
record — the 0.76–0.78 above is a lower bound because the auditors were
rubric-naive.

**First measurement: FAIL.** Fresh 18-row tranche (sheets D/E, seed 611, drawn
only from generations unused in the first audit, key sealed). Scored by
[`experiments/oe1_param5_score.py`](../../experiments/oe1_param5_score.py):
**raw 0.7778 (14/18), κ 0.5789.** Both legs miss. The verdict was applied
mechanically.

The four disagreements were each a failure mode the earlier adjudication had
already ruled on: the judge scoring a second-order conflict instead of the
question's first-order ask (twice), reading refusal-of-premise as opposition, and
matching on a side claim in a pick-one question. Three of the four were the judge
over-calling DIFFERENT.

**One pre-committed iteration, then re-measure on the same bar.** Rubric r2 makes
three targeted edits, one per diagnosed failure mode, plus a reply-format line
where the judge must name the central issue it scored (and a one-line parser
widening to accept it). The owner approved the diff as drafted; all three edits
increase strictness. A regression rule was set before the run: **if r2 breaks
more than 2 of the 14 previously-correct rows, stop — it is overfitted.**

**Result** ([`experiments/oe1_r2_score.py`](../../experiments/oe1_r2_score.py)):

| step | tranche | outcome |
|---|---|---|
| regression | D/E, 18 rows | **0** previously-correct rows broken (rule: >2 → stop). 1 of 4 disagreements fixed. Agreement 0.7778 → 0.8333. |
| trust bar | F/G, 18 fresh rows, seed 613 | **raw 0.8889 (16/18), κ 0.7978 — PASS** against the unchanged bar |

Both remaining F/G disagreements are SAME-versus-UNCLEAR confusions. There is no
SAME-versus-DIFFERENT flip anywhere on the tranche.

**The bar never moved.** It was fixed before the first measurement, missed, and
met on the second attempt at the same numbers.

Three honesty notes stay attached to the PASS rather than being cleared by it:

- **Three known hard rows are still wrong.** Under r2, the judge's new
  central-issue line shows it *naming* the adjudicated central issue on all three
  residual D/E rows and still holding its call. The residual gap is the judge
  model's application, not the rubric text.
- **The dev supply is nearly exhausted.** The unused pool held only 4
  judge-DIFFERENT rows, so the F/G tranche is 9 SAME / 4 DIFFERENT / 5 UNCLEAR by
  the old labels rather than balanced. Another label-balanced tranche requires
  fresh dev generations, not another draw.
- **Both auditor lines on the fresh tranches are LLM lines** (deviation D4,
  owner-directed), out-of-family from the generator, both scored models and the
  judge, with the frozen rubric read in full and the key never opened. They are
  reported as their own line and never pooled with a human line.

### 9.5 What the replacement has and has not shown

It has cleared a dev-scale validation gate on 17 items, and its judge has cleared
a pre-committed trust bar after one documented iteration. That is all it had to
do to unfreeze the bars.

It has **not** established anything about twin fidelity in this paper. The
confirmatory run of the replacement instrument is a separate result with its own
reports — [H1 and H7](../stage2_confirm/STAGE2_CONFIRM_REPORT.md) and
[H6](../stage2_confirm/H6_REPORT.md) — written up in
[the main results paper](PAPER2_MAIN.md); they are named here only so a reader does
not assume the instrument went untested at scale. In brief, so the handoff is
honest about outcomes as well as existence: the instrument separated own twin from
imposter twin at confirmatory scale on 88 subjects in both channels and on both
models, while H7 ended with the two channels disagreeing and H6 with too few
eligible subjects to license any claim. The details, the misses and the magnitude
bars belong to that paper, not this one.

---

## 10. Positioning: what this adds, and what it does not

Adaptive and uncertainty-guided questioning is an active research area with
published results. No document in this project may claim otherwise
([Amendment 2 B9.a](../../PREREGISTRATION_AMENDMENT_2.md), binding). The record
we cite instead:

- **BED-LLM** (Choudhury et al., ICLR 2026) — Bayesian experimental design for
  adaptive LLM questioning: pick the next question by expected information gain
  about the thing you are trying to learn. Our Stage 1E entropy rule corresponds
  to their weak baseline.
- **Wang et al. (ICML 2025)** — adaptive elicitation in natural language,
  evaluated on OpinionQA among other tasks.
- **Su et al. (May 2026 preprint)** — adaptive interviewing for persona
  simulation; small effect, small scale (follow-up-grounded predictions 45.5%
  against 39.3% for core-only). The flag is planted and is cited.

Full references in §14.

This project claims two contributions, and this paper adds a third:

1. **A population-optimised static-script baseline** that adaptive-questioning
   work generally omits. Stage 1E showed it beating adaptive selection at a tenth
   of the compute ([Stage 1E findings](../stage1e_findings.md)).
2. **Elicitation budgets priced in human time** — respondent seconds rather than
   item counts ([time-cost note](../stage1e_timecost_note.md)).
3. **This paper's scoped negative result about forced-choice instruments**, with
   the tell taxonomy and the four-round record behind it.

The project's identity follows from that list: DOPPLER is measurement and
validation science for person-models — what makes a twin faithful, where it
fails, how fast it goes stale — not a competing interviewer.

One scope statement carries over and is worth repeating because it is easy to
overstate. Stage 1E's null for adaptive selection was measured on a closed pool
of 48 fixed items with single-rating answers and no conversation. It licenses no
claim about follow-up generation in open conversation, and it may not be cited as
evidence that adaptive interviewing does not work
([Amendment 2 B1](../../PREREGISTRATION_AMENDMENT_2.md)).

---

## 11. Limitations

**One corpus.** Everything here is MediaSum: American broadcast news interviews,
2000–2020, guests who are largely subject-matter experts speaking in a
professional register. The tells we found are plausibly corpus-specific. A
corpus of ordinary people speaking casually might behave differently, and we did
not test one.

**Public personas, not private people.** Stage 2's honest object is what a person
says in a public interview given their previous ones. That sentence belongs in
every write-up of this project and it belongs here.

**The human detectability line was waived.** Amendment 2 B10.8 required the owner
to attempt to spot the real answer among generated ones on 20 unmarked items. The
owner declined on 2026-07-27 and substituted an out-of-family LLM rater. **No
human hit rate exists and none is fabricated.** This is a documented deviation,
recorded in [round 4 §3.1](../stage2_pilot4/PILOT_REPORT_4.md) and in
[Addendum A precondition 4](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md). The
LLM line answers a related but different question — whether a capable model can
spot the real answer — which predicts scorer behaviour more directly but is not
the check the amendment asked for.

**Model-family relationships, declared** (Amendment 2 B10.3, carried into
[Amendment 3 C3](../../PREREGISTRATION_AMENDMENT_3.md)). The option generator in
rounds 3 and 4 was `gemini-3.5-flash-lite`, which is also the registered
robustness scorer — an owner cost decision, declared at the time. It was inert in
those rounds, since only Gemma scored anything there, but it would be live at
confirmatory scale. Under the open-ended instrument the stance judge
(`gemini-3.5-flash`) is a different version from the robustness scorer
(`gemini-3.5-flash-lite`) but shares its family. The consequence is registered:
**robustness-arm absolute scores are explicitly secondary; only the
own-minus-imposter contrast carries robustness weight.**

**Dev scale throughout.** 17, 10, 15 and 8 items on five or six development
subjects. These are directions and ceilings, not effect sizes. The ceiling
finding survives the small numbers because a ceiling at 1.00 with margins from
+0.40 to +1.00 is not a marginal call — but nothing else in these rounds should
be read quantitatively.

**A measurement artifact we chose not to patch mid-flight.** The scoring model
sometimes prints its probability distribution twice, which the frozen parser
rejects as malformed. The rate climbed with option length: 2 of 170 in round 1,
2 of 10 in round 2, 12 of 15 in round 3, **6 of 8 in round 4**. Every affected
reply was recoverable and every recovered reply agreed with the frozen reading,
so no conclusion here turns on it — but in round 4 the contract number rested on
two of eight replies, and a run where the two readings disagreed would be a
serious problem. Widening the parser was treated as a bar-lock decision, not an
implementer's; the instrument died before it was taken.

**One unaudited data-quality risk.** Round 2's answer pool was widened to include
non-substantive transcripts (mostly older CNN panel shows) to keep the item yield
above zero. That is exactly the material where MediaSum is most likely to
misattribute speech to the wrong speaker, which would silently break the one
property the same-subject design exists to guarantee. It was flagged and not
audited ([round 2 §4](../stage2_pilot2/PILOT_REPORT_2.md)).

**"Pre-registered" is currently weaker than it sounds.** The governance documents
are frozen in git with per-document commit and sha256 provenance, and an OSF
snapshot covering all six is prepared — but **the external upload is still
outstanding**. Until it happens, "pre-registered" means "committed to version
control before the data was touched".

---

## 12. Cost

The whole programme reported in this paper, from
[`results/cost_log.jsonl`](../cost_log.jsonl), one line per run:

| item | compute (node-hours) | API spend | calls the spend covers | all ledger calls |
|---|---|---|---|---|
| Round 1 | 0.3544 | $0.00 | 639 scored cluster calls | 661 |
| Round 2 | 0.2633 | $0.00 | 30 scored cluster calls | 30 |
| Round 3 | 0.1156 | $0.0999 | 239 priced API calls | 305 |
| Round 4 | 0.1064 | $0.0447 | 137 priced API calls | 145 |
| Open-ended dev pilot (OE-1) | 0.1053 | $0.3177 | 340 priced API calls | 425 |
| Judge r2 round (re-judge + re-score) | — | $0.0459 | 36 priced API calls | 36 |
| **total** | **0.945** | **$0.508** | | **1,602** |

**The two call columns differ on purpose, and here is exactly how.** The fourth
column counts only the calls the dollar figure beside it pays for, which is why
every dollar figure matches the ledger to the cent. The fifth column is the raw
sum of `n_calls` for that run prefix in
[`results/cost_log.jsonl`](../cost_log.jsonl). Four rows differ:

- **Round 1** — 639 is prediction (170) plus classifier (469). The ledger's 661
  adds a **22-call smoke slice** that produced no scientific output. Note the
  asymmetry in that row: the smoke slice carries 0.2280 of the 0.3544
  node-hours, so the compute column *does* include it while the scored-call
  column does not.
- **Round 3** — 239 is the priced flash-lite work (build 175, budget probe 15,
  controls 49). The ledger's 305 adds the **51-call abandoned Pro generator
  line** (superseded, unpriced) and the **15 cluster gate calls** (no API cost).
- **Round 4** — 137 is the priced flash-lite build. The ledger's 145 adds the
  **8 cluster gate calls** (no API cost).
- **OE-1** — 340 is the four priced API runs (flash-lite generation, and three
  judge passes at 85 calls each). The ledger's 425 adds the **85 cluster
  generation calls** for the primary model, which are billed in node-hours, not
  dollars.

Round 2 and the r2 round have no such gap; their two columns agree.

Three notes the ledger insists on. GPU time is billed from the scheduler's own
accounting, never from the in-process wall clock — a node is billed whole from
allocation, so a failed attempt costs what a successful one of the same length
costs (round 2 wasted 0.0558 node-hours to a node fault, and it is billed). One
abandoned generator line carries a **null** cost because the price table has no
entry for that model: **a missing price, not a zero cost.** Real money was spent
on it, and that is why 51 of round 3's calls sit outside the priced column
rather than inside it at zero. And the totals row is a sum of measured lines,
not a budget: 0.3544 + 0.2633 + 0.1156 + 0.1064 + 0.1053 node-hours, and
$0.09988 + $0.044708 + $0.317696 + $0.045888 across the priced runs.

Killing an instrument after four rounds cost under a node-hour and under a
dollar. The expensive resource in this project is owner review time.

---

## 13. Where every number comes from

| what | document | regenerated by |
|---|---|---|
| Round 1 — other-people distractors | [`stage2_pilot/PILOT_REPORT.md`](../stage2_pilot/PILOT_REPORT.md) | [`experiments/stage2_pilot.py`](../../experiments/stage2_pilot.py) |
| Round 2 — same-subject distractors, decomposition | [`stage2_pilot2/PILOT_REPORT_2.md`](../stage2_pilot2/PILOT_REPORT_2.md) | [`experiments/stage2_pilot2.py`](../../experiments/stage2_pilot2.py) |
| Round 3 — generated counterfactuals | [`stage2_pilot3/PILOT_REPORT_3.md`](../stage2_pilot3/PILOT_REPORT_3.md) | [`experiments/stage2_pilot3.py`](../../experiments/stage2_pilot3.py) |
| Round 4 — fixes + kill rule | [`stage2_pilot4/PILOT_REPORT_4.md`](../stage2_pilot4/PILOT_REPORT_4.md) | [`experiments/stage2_pilot4.py`](../../experiments/stage2_pilot4.py) |
| Round 4 design contract | [`stage2_pilot4/SPEC_v1.10.md`](../stage2_pilot4/SPEC_v1.10.md) | frozen snapshot |
| Frontier-rater detectability line (pre-gate) | [`stage2_pilot4/DETECTABILITY_RATER_LINE.md`](../stage2_pilot4/DETECTABILITY_RATER_LINE.md) | — |
| Open-ended dev pilot (OE-1) | [`stage2_openended/OE1_PILOT_REPORT.md`](../stage2_openended/OE1_PILOT_REPORT.md) | [`experiments/stage2_oe1.py`](../../experiments/stage2_oe1.py) |
| Judge audit, trust bar, FAIL → PASS | [`stage2_openended/AUDIT_LINES_2026-07-28.md`](../stage2_openended/AUDIT_LINES_2026-07-28.md) | [`oe1_param5_score.py`](../../experiments/oe1_param5_score.py), [`oe1_r2_judge.py`](../../experiments/oe1_r2_judge.py), [`oe1_r2_score.py`](../../experiments/oe1_r2_score.py) |
| Judge rubric r2 (pinned) | [`stage2_openended/rubric_r2_draft.txt`](../stage2_openended/rubric_r2_draft.txt) | frozen, sha256 `ad050d1a…102464` |
| Corpus recon and curation | [`stage2_corpus_recon.md`](../stage2_corpus_recon.md), [`stage2_curation_report.md`](../stage2_curation_report.md) | [`experiments/mediasum_index.py`](../../experiments/mediasum_index.py) |
| The contract: stages, hypotheses, bars | [`PREREGISTRATION.md`](../../PREREGISTRATION.md) | frozen |
| Instrument revision (B10), positioning (B9) | [`PREREGISTRATION_AMENDMENT_2.md`](../../PREREGISTRATION_AMENDMENT_2.md) | frozen |
| Kill record (C1), replacement (C2), validation gate (C4) | [`PREREGISTRATION_AMENDMENT_3.md`](../../PREREGISTRATION_AMENDMENT_3.md) | frozen |
| Frozen instrument parameters and judge trust bar | [`PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md) | frozen |
| Cost ledger | [`cost_log.jsonl`](../cost_log.jsonl) | every run driver |

---

## 14. References

The three works named in
[Amendment 2 B9.a](../../PREREGISTRATION_AMENDMENT_2.md), resolved to full
citations. Each was confirmed against the arXiv listing page for the identifier
given; the amendment names them only by short description.

- Choudhury, D., Williamson, S., Goliński, A., Miao, N., Bickford Smith, F.,
  Kirchhof, M., Zhang, Y., & Rainforth, T. (2026). *BED-LLM: Intelligent
  Information Gathering with LLMs and Bayesian Experimental Design.*
  International Conference on Learning Representations (ICLR) 2026.
  arXiv:2508.21184. https://arxiv.org/abs/2508.21184
- Wang, J., Zollo, T., Zemel, R., & Namkoong, H. (2025). *Adaptive Elicitation of
  Latent Information Using Natural Language.* International Conference on Machine
  Learning (ICML) 2025. arXiv:2504.04204. https://arxiv.org/abs/2504.04204 —
  evaluated on the Twenty Questions game, adaptive student assessment, and
  dynamic opinion polling on **OpinionQA** (Santurkar et al., 2023), which is the
  evaluation B9 refers to.
- Su, R., Liu, Y., & Hu, J. (2026). *Adaptive Interviewing for Persona Simulation
  in LLMs: Evidence-Grounded Reasoning Improves Decision Alignment.* Preprint,
  submitted 28 May 2026. arXiv:2605.29458. https://arxiv.org/abs/2605.29458 —
  not peer-reviewed at time of writing.

Two further works are cited in the text and are not part of B9's list:

- Park, J. S., Zou, C. Q., Shaw, A., Hill, B. M., Cai, C., Morris, M. R.,
  Willer, R., Liang, P., & Bernstein, M. S. (2024). *Generative Agent
  Simulations of 1,000 People.* arXiv:2411.10109.
  https://arxiv.org/abs/2411.10109 — the design target named in
  [PREREGISTRATION.md §1](../../PREREGISTRATION.md), commercialised by Simile.
  Verified against the arXiv listing 2026-07-28.
- Santurkar, S., Durmus, E., Ladhak, F., Lee, C., Liang, P., & Hashimoto, T.
  (2023). *Whose Opinions Do Language Models Reflect?* ICML 2023.
  arXiv:2303.17548. https://arxiv.org/abs/2303.17548 — the origin of OpinionQA,
  already on the project's record in
  [`results/lit_check.md`](../lit_check.md).

---

*Draft. Not submitted, not published. All pilot numbers are development-subject
measurements; no confirmatory subject was touched by any round reported here.*
