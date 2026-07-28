# H6 / B3 parameters — DRAFT PROPOSAL (2026-07-28)

**Status: PROPOSAL. Nothing here is frozen. Nothing here changes any adopted
document.** Every number carries **[PROPOSED]**.

This fills the one slot Addendum A deliberately left open on record: the H6
parameters from Amendment 2 B3 — token budget(s) B, segment and chain
definitions, rich/poor thresholds, and the flagged-turn threshold.

Two gates stand between this draft and any confirmatory H6 number, and they
are independent of each other:

1. **This appendix needs its own owner approval before any confirmatory H6
   scoring.** Addendum A's freeze did not cover it. Approving Addendum A did
   not approve this.
2. **Addendum A precondition 5 part 2 still gates H6 scoring separately.**
   After the classifier first runs on confirmatory subjects, a fresh blind
   audit tranche of **≥ 60 labels from ≥ 10 confirmatory subjects** goes to
   the owner, at the same trust bar (raw ≥ 0.85, κ ≥ 0.60). If it fails, H6
   scoring halts pending rubric revision. Approving this appendix does not
   satisfy that, and passing that does not approve this.

Measured on the **6 dev subjects only**. No confirmatory subject was read,
listed, or counted. Cost: **CPU only, no API calls, no GPU — $0.00.**

---

## The proposal, in one table

| # | Parameter | Proposed value | Dev evidence behind it |
|---|---|---|---|
| 1 | Primary token budget **B** | **1,000 words [PROPOSED]** | 4 of 6 dev subjects fill both arms to within ±5%; rich fill ≥ 0.96 of B for all 6 |
| 1b | Secondary budget (dose check) | **400 words [PROPOSED]** | same 4 subjects fill it; 2.5× dose gap; below 400 the fill gets worse, not better |
| 2 | Segment | **one host turn + the guest run immediately after it; never split [PROPOSED]** | matches the unit `stage2_render` already selects on; 740 segments over 26 dev clusters |
| 2b | Chain | **one NEW-TOPIC root + the maximal run of FOLLOW-UP segments right after it, same transcript [PROPOSED]** | 91 chains in dev; depth 1–6 |
| 2c | Chain depth floor **D_min** | **2 [PROPOSED]** | depth-1 chains rest on one FOLLOW-UP call, wrong 41.2% of the time on the audit sheet vs 15–20% deeper |
| 3 | Rich arm content | **segments in chains of depth ≥ 2 (root + its follow-ups) [PROPOSED]** | 40 of 91 dev chains qualify; supply 995–4,111 words per subject |
| 3b | Poor arm content | **NEW-TOPIC segments that are neither a chain root nor inside any chain [PROPOSED]** | disjoint from rich by construction; supply 263–12,085 words |
| 3c | Cluster rich/poor label (descriptive only) | **follow-up density ≥ 0.25 = rich [PROPOSED]** | dev median 0.268; the cut sits in the histogram's thin bin (1 cluster in [0.20, 0.25)) |
| 4 | Flagged turn — unlabelable | **subject analyzed separately above a 5% drop rate [PROPOSED]** | dev drop rate is **0 of 469**; not calibrated from data, said plainly |
| 4b | Flagged subject — boundary risk | **analyzed separately when > 60% of rich-arm words come from depth-2 chains [PROPOSED]** | dev range 0.000–0.589; fires on 0 of 6, sits just above the observed max |
| 4c | Corpus-level boundary tripwire | **part-2 FOLLOW-UP overturn rate > 20% → pre-committed D_min = 3 sensitivity arm, both reported [PROPOSED]** | dev overturn rate 25.0% on FOLLOW-UP vs 1.7% on NEW-TOPIC |

---

## What the dev data is

Six dev subjects. 26 grounding interview clusters. **740 host turns
classified**: 469 by the model, 271 NEW-TOPIC by the rule (a host turn with no
guest answer behind it). 173 FOLLOW-UP, 567 NEW-TOPIC. **Zero parse failures,
zero missing completions.**

Supply is very uneven. C00292 carries 330 segments and 17,674 words; C02006
carries 20 segments and 2,046 words. That spread drives most of what follows.

---

## 1. Token budget B

**Proposed: B = 1,000 words primary [PROPOSED], plus a 400-word secondary dose
check [PROPOSED]. Words = whitespace tokens, host speech plus guest speech,
the same proxy the rest of Stage 2 uses.**

The thing that decides B is not how many words exist. It is whether the greedy
fill can *land* on B within Amendment 2's ±5% budget-matching tolerance, given
that segments are never split. A subject with 1,010 rich words in three chunky
pieces cannot hit a 400-word budget.

So I simulated the fill, arm by arm, at each budget. Cell = fraction of B the
rich arm reached / fraction the poor arm reached. A subject is eligible when
both reach ≥ 0.95.

**D_min = 2 (the proposed setting):**

| subject | B=400 | B=600 | B=800 | B=1000 | B=1200 | B=1500 |
|---|---|---|---|---|---|---|
| C00792 | 0.98/1.00 ✓ | 0.98/0.99 ✓ | 0.96/0.99 ✓ | 0.99/1.00 ✓ | 0.83/1.00 | 0.66/1.00 |
| C00292 | 1.00/1.00 ✓ | 1.00/1.00 ✓ | 1.00/1.00 ✓ | 1.00/1.00 ✓ | 1.00/1.00 ✓ | 1.00/1.00 ✓ |
| C02013 | 0.84/0.99 | 0.93/0.81 | 0.94/0.99 | 0.96/0.89 | 0.84/0.99 | 0.67/0.79 |
| C02124 | 0.99/1.00 ✓ | 1.00/1.00 ✓ | 0.99/1.00 ✓ | 0.99/1.00 ✓ | 1.00/1.00 ✓ | 1.00/1.00 ✓ |
| C01677 | 1.00/1.00 ✓ | 1.00/0.99 ✓ | 0.99/1.00 ✓ | 0.96/0.99 ✓ | 0.86/1.00 | 0.97/1.00 ✓ |
| C02006 | 0.99/0.66 | 0.98/0.44 | 0.94/0.33 | 0.99/0.26 | 0.98/0.22 | 0.99/0.18 |
| **eligible** | **4/6** | **4/6** | **4/6** | **4/6** | **2/6** | **3/6** |

Why 1,000: it is the largest budget that keeps 4 of 6 dev subjects, and at
1,000 the **rich** arm fills to ≥ 0.96 for every one of the six. Both failures
at 1,000 are poor-arm supply, not rich-arm supply. Above 1,000 the rich arm
starts falling apart (2/6 at 1,200), so 1,000 is the edge of what dev supports.

Why 400 as the second level: the same four subjects fill it, and it is a 2.5×
dose gap — enough to see whether any H6 effect is budget-dependent. It is also
the floor. Going lower makes fills *worse*, not better, because a single long
exchange overshoots a small budget entirely and gets skipped.

Two subjects fail at every level, for different reasons, and both are exactly
the mechanical exclusion B4.2 anticipates (excluded counts reported, subjects
stay in H1/H2):

- **C02006** — the poor arm starves. Only 7 lone-NEW-TOPIC segments, 263
  words. This is a subject the host mostly drilled.
- **C02013** — granularity. 1,010 rich words, but in pieces too coarse to land
  within ±5% at most budgets.

**Honest note on the pilot's own budget.** H1's grounding budget is 2,000
words. H6's B is half that or less, because each H6 arm draws one content type
only. The two are not comparable and no write-up should compare them.

---

## 2. Segment and chain definitions

**Segment [PROPOSED].** One host turn plus the run of consecutive guest turns
immediately after it, joined with spaces. A host turn or any other speaker
closes the run. A host turn with no guest reply keeps an empty reply and costs
only its own words. **Segments are never split** — they are the atom of both
arms. This is the same unit `stage2_render._exchange_items` already selects on
for H1, so H6 inherits a tested selector rather than inventing one.

**Chain [PROPOSED].** A chain is **one NEW-TOPIC root segment plus the maximal
run of FOLLOW-UP segments that immediately follows it in the same transcript.**

- **A chain starts** at a NEW-TOPIC host turn that is immediately followed by
  at least one FOLLOW-UP host turn.
- **A chain ends** at the last FOLLOW-UP turn before any of: the next
  NEW-TOPIC turn, an unlabelled turn, or the end of the transcript.
- **Depth** = the number of FOLLOW-UP segments, root excluded. Depth is ≥ 1 by
  construction. A NEW-TOPIC turn with nothing following it is not a
  zero-depth chain — it is a lone new-topic segment, and it belongs to the
  poor arm.
- **An unlabelled turn breaks the run.** The code cannot tell whether it
  continued the chain, and guessing would launder a dropped turn into
  evidence.
- **Rootless chains** (a FOLLOW-UP run with no NEW-TOPIC root in front of it —
  a transcript that opens mid-chain, or a root that was dropped) are
  **excluded from the rich arm [PROPOSED]**. Zero occurred in dev, so this
  rule costs nothing here and exists so the confirmatory run has an answer.

Dev chains, at D_min = 1 (i.e. all of them): **91 chains.** Depth
distribution: **51 at depth 1, 22 at depth 2, 7 at depth 3, 3 at depth 4, 3 at
depth 5, 5 at depth 6.** Median depth 1. Zero rootless.

**Chain depth floor D_min = 2 [PROPOSED].** Only chains of depth ≥ 2 feed the
rich arm — 40 of the 91. The reason is the co-audit finding, and it is in
section 4.

---

## 3. Rich and poor

**Rich arm [PROPOSED]:** every segment inside a chain of depth ≥ 2 — the root
plus its follow-ups. This follows B2.3's own wording ("consecutive FOLLOW-UP
segments form a chain **with their root turn**").

**Poor arm [PROPOSED]:** NEW-TOPIC segments that are **neither a chain root nor
inside any chain** — call them lone new-topic segments.

The two arms are **disjoint by construction**. Chain roots go to rich and never
to poor. That matters: a root is a NEW-TOPIC turn the host chose to drill, so
letting it into the poor arm would put drilled content on both sides and blunt
the contrast H6 exists to measure.

Supply at D_min = 2:

| subject | rich words | poor words | rich segments | poor segments |
|---|---|---|---|---|
| C00792 | 995 | 2,598 | 19 | 39 |
| C00292 | 2,803 | 12,085 | 61 | 225 |
| C02013 | 1,010 | 1,189 | 12 | 14 |
| C02124 | 4,111 | 5,663 | 36 | 111 |
| C01677 | 1,696 | 4,639 | 21 | 80 |
| C02006 | 1,783 | 263 | 13 | 7 |

**Cost of excluding roots from the poor arm, reported rather than hidden:**
roots are 731 / 3,169 / 331 / 2,535 / 418 / 433 words per subject. Letting them
into poor would have rescued C02006's starved poor arm (263 → 696 words). The
proposal still rejects it, because a rescued arm that shares content with the
rich arm is not a control.

**Selection rule inside each arm [PROPOSED], deterministic, no LLM anywhere:**

- **Rich:** whole chains, deepest first; ties broken by interview date
  descending, then transcript id, then root turn index. If a whole chain does
  not fit the remaining budget, **skip it and continue** rather than stopping —
  the same skip-not-stop discipline `render_grounding` already uses, so one
  long chain cannot throw away the rest of the budget. After the whole-chain
  pass, top up from unused chain members, newest first.
- **Poor:** lone new-topic segments, newest first, skip-not-stop.
- Both arms then render **chronologically**, per B2.3. Selection order and
  render order are different things, exactly as in H1.

**Cluster-level rich/poor label [PROPOSED] — descriptive only, no arm depends
on it.** Follow-up density = FOLLOW-UP segments ÷ labelled segments in the
cluster. **Cut at 0.25.** Dev: 26 clusters, median 0.268, mean 0.252.

Histogram, 0.05-wide bins:

```
[0.05,0.10)  #                1
[0.10,0.15)  ######           6
[0.15,0.20)  ####             4
[0.20,0.25)  #                1   <- the cut sits here, in the thin bin
[0.25,0.30)  #####            5
[0.30,0.35)  #####            5
[0.35,0.40)                   0
[0.40,0.45)  ###              3
[0.60,0.65)  #                1
```

The distribution is bimodal-ish with a gap. The 0.20–0.25 bin holds one
cluster, and it is the sparsest bin anywhere in the middle of the range, so
0.25 is where a cut does least violence. It splits dev 14 rich / 12 poor.
Nearby cuts: 0.20 → 15/11, 0.30 → 10/16, 0.35 → 4/22.

This label exists for the declared confound in B2 ("follow-up chains occur
where the host chose to drill"), so the write-up can report per-arm results by
cluster type. **It never selects content.**

---

## 4. Flagged-turn threshold — and the co-audit's boundary finding

The co-audit (Addendum A precondition 5 part 1, deviation D3) cleared the bar
at raw 0.8667 / κ 0.7333, and recorded that **15 of the 16 disagreements ran
one way** — co-auditor NEW-TOPIC where the classifier said FOLLOW-UP. The
addendum says the part-2 tranche should look at exactly this boundary. This
section is the proposal's answer.

### 4.0 What the asymmetry is worth, as a number

I rebuilt the 120 audit rows from the sealed key and the recorded co-auditor
line and re-derived the disagreement set (it reproduces exactly: rows 8, 9, 11,
15, 17, 18, 20, 30, 37, 42, 44, 51, 60, 61, 92, 101). Split by label:

| classifier said | rows | overturned by the co-auditor | rate |
|---|---|---|---|
| FOLLOW-UP | 60 | 15 | **25.0%** |
| NEW-TOPIC | 60 | 1 | **1.7%** |

That is the finding in one line: **the classifier's NEW-TOPIC label is close to
solid; its FOLLOW-UP label is about one in four loose.** Only the rich arm is
exposed. The poor arm is built from the label that holds.

### 4.1 A per-turn lexical flag was tried and is REJECTED

The obvious rule — flag a FOLLOW-UP turn that shares no words with the answer
it claims to follow up on — does not work, and I am recording that so nobody
proposes it again.

Shared content words between the host turn and the guest answer, over the 60
classifier-FOLLOW-UP audit rows:

- upheld (n=45): median 1, p75 2, max 10
- overturned (n=15): median 0, p75 2, max 3

The distributions sit on top of each other. Every threshold I tried fires on
half the arm and is right a quarter of the time:

| rule | fires on | catches | recall | precision |
|---|---|---|---|---|
| ≤ 0 shared content words | 30/60 | 9/15 | 60% | 30% |
| ≤ 1 shared content words | 37/60 | 11/15 | 73% | 30% |
| ≤ 2 shared content words | 52/60 | 13/15 | 87% | 25% |
| overlap fraction ≤ 0.10 | 41/60 | 10/15 | 67% | 24% |

Run corpus-wide, the ≤ 1 rule flags **47%–100%** of every dev subject's
FOLLOW-UP turns (median 67%). A flag that fires on two thirds of the arm is not
a flag. **Rejected [PROPOSED].**

### 4.2 The structural answer: D_min = 2

Where the overturned FOLLOW-UPs actually sit is informative:

| chain depth | upheld | overturned | error |
|---|---|---|---|
| 1 | 10 | 7 | **41.2%** |
| 2 | 11 | 2 | 15.4% |
| 3+ | 24 | 6 | 20.0% |

A **depth-1 chain rests on exactly one FOLLOW-UP judgement**, and that
judgement is wrong about 41% of the time. A depth-2 chain needs two consecutive
FOLLOW-UP calls to both be wrong. Requiring depth ≥ 2 is therefore the honest
mitigation: it is structural, it needs no new heuristic, and it throws out the
51 chains built on a single fragile call while keeping 40.

Same story by position within the chain: the **first** follow-up after a root
is overturned 34.5% of the time (10/29); the second, 7.1% (1/14); third or
later, 23.5% (4/17). Small cells — say so — but the first-position result is
the same effect seen from another angle.

**Sensitivity check.** I re-derived every subject's rich supply substituting
the co-auditor's labels on the 120 audited turns (all other turns keep the
classifier's label). At D_min = 1 the rich arm moves by up to −32.5%
(C02013: 1,497 → 1,010). At D_min = 2 it is steadier — unchanged for 3 of 6
subjects, worst case −19.2% (C02124). D_min = 2 is the more stable setting on
both the median and the worst case.

### 4.3 The threshold itself, in three parts

**(a) Unlabelable turns — B4.3 as literally written. [PROPOSED: 5%]**
A subject whose model-classified grounding turns are unparseable after 2
retries at a rate above **5%** is analyzed separately.

**This value is not calibrated from dev data, and I will not pretend it is.**
The dev drop rate is **0 of 469 model calls — exactly zero, for all six
subjects.** There is no distribution to cut. 5% is a placeholder chosen to be
loose enough never to fire on a healthy subject and tight enough to catch a
broken one. If the owner prefers a different number, dev evidence cannot
argue.

**(b) Boundary-risk flag, per subject. [PROPOSED: 60%]**
A subject is analyzed separately when **more than 60% of its rich-arm words
come from depth-2 chains** — the shallowest depth admitted, and therefore the
least verified.

Dev depth-2 share: 0.075 / 0.520 / 0.327 / 0.589 / 0.000 / 0.578. Range
0.000–0.589, median 0.423. The rule fires on **0 of 6** dev subjects and sits
just above the observed maximum. Stated plainly: this is a **tripwire for
confirmatory subjects worse than anything dev showed**, not a dev-calibrated
cut. C02124 at 0.589 is close enough to the line that the owner may reasonably
want it higher.

**(c) Corpus-level tripwire on the part-2 tranche. [PROPOSED: 20% / 35%]**
The per-subject rate cannot be measured from part 2 — ≥ 60 labels over ≥ 10
subjects is about 6 rows each, far too thin. So the boundary check belongs at
corpus level:

- Part-2 FOLLOW-UP overturn rate **> 20%** → H6's rich arm is additionally
  built at **D_min = 3** as a pre-committed sensitivity arm, and both results
  are reported side by side. Direction must survive both for any headline.
- **> 35%** → H6 scoring halts pending rubric revision. (Addendum A part 2
  already halts on a trust-bar failure; this is the narrower, label-specific
  version of the same stop.)

Dev's own FOLLOW-UP overturn rate is 25.0%, which is above the 20% line. That
is deliberate: on dev evidence the D_min = 3 sensitivity arm is **already
likely to be required**, and pre-committing to it now costs nothing and
prevents choosing it after seeing results.

---

## What this draft does not settle

- **It cannot measure confirmatory supply.** Every budget and eligibility
  number here is from 6 dev subjects. The B4.2 eligibility rule is mechanical
  and will produce its own confirmatory counts; if those come in low, the
  B3 subject-count branch (≥ 80 confirmatory / 30–79 exploratory / < 30
  descriptive) decides what H6 can claim, not this appendix.
- **The rich arm is not pure follow-up content, by B2.3's own definition.**
  Chain roots are NEW-TOPIC turns, and they are **17%–45% of rich-arm words**
  (median 23%). Any write-up must say the rich arm is "follow-up chains
  including their root question", not "follow-up material".
- **One co-auditor, one round, 120 dev rows.** The 25% / 1.7% asymmetry rests
  on a single blind LLM line under deviation D3. It is the best evidence that
  exists, and it is thin.

---

## Reproduce

`uv run python experiments/h6_b3_measure.py`

Standard library only, no network, no model calls, deterministic (enumeration,
no sampling; SEED = 63 is declared and unused). Inputs are dev-only:
`results/stage2_pilot/records/classify.jsonl`,
`results/stage2_pilot/exports/{prompts_classify,meta_classify,labels_rule}.jsonl`,
`results/stage2_pilot/subjects/*/{grounding_turns.jsonl,split.json}`,
`results/stage2_pilot/dev_subjects.json`,
`results/stage2_openended/h6_audit_key.json`,
`results/stage2_openended/audit_scores.json`.

Classifier rubric in force for every label counted here:
sha256 `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`
(RUBRIC_V1, `src/doppler/followup_render.py`).

**Cost of every measurement in this document: CPU only, no API calls, no GPU
node. $0.00.**
