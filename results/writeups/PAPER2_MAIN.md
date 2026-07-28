# DOPPLER Stage 2 — can a twin built from someone's old interviews predict what they say in the next one?

**Main results paper. Draft for owner review.**

Every number below links to the report that produced it. The confirmatory numbers come
from one place only: [`results/stage2_confirm/STAGE2_CONFIRM_REPORT.md`](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)
(machine-readable copy: [`report_numbers.json`](../stage2_confirm/report_numbers.json)).
The frozen contract is [`PREREGISTRATION.md`](../../PREREGISTRATION.md) plus
[Amendment 1](../../PREREGISTRATION_AMENDMENT_1.md),
[Addendum A to 1](../../PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md),
[Amendment 2](../../PREREGISTRATION_AMENDMENT_2.md),
[Addendum A to 2](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md), and
[Amendment 3](../../PREREGISTRATION_AMENDMENT_3.md).

---

## 1. The headline

**A twin grounded in a person's earlier public interviews predicts that person's answers in
a later, unseen interview better than an identically built twin grounded in a *different*
person's interviews.** That is the imposter-controlled result, it is confirmatory, it holds
on 88 subjects, and it holds on both scoring channels and both scored models.

Primary contrast — own twin minus imposter twin, the metric
[Amendment 3 C3](../../PREREGISTRATION_AMENDMENT_3.md) makes primary — on the primary model
(Gemma-4-31B-it), with both arms' raw means printed beside the difference as the
watch-which-arm-moves rule requires
([confirm report §4](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)):

| channel | own twin | imposter twin | difference | 95% CI | p | subjects |
|---|---|---|---|---|---|---|
| 1 embedding cosine | 0.5821 | 0.5070 | **+0.0751** | [+0.0570, +0.0932] | < 0.0001 | 88 |
| 2 stance match | 0.6914 | 0.5703 | **+0.1211** | [+0.0580, +0.1843] | 0.0003 | 85 |

Second registered leg — own twin minus the zero-information baseline (same model, same
items, no grounding, identity redacted), same model, same run
([confirm report §2](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)):

| channel | own twin | zero-info baseline | difference | 95% CI | p | subjects |
|---|---|---|---|---|---|---|
| 1 embedding cosine | 0.5821 | 0.5443 | **+0.0378** | [+0.0211, +0.0545] | < 0.0001 | 88 |
| 2 stance match | 0.6943 | 0.5788 | **+0.1155** | [+0.0543, +0.1767] | 0.0003 | 88 |

**H1 verdict: PASS.** The frozen bar
([Amendment 1 A1](../../PREREGISTRATION_AMENDMENT_1.md)) is "H1 passes iff BOTH mean
zero-info lift > 0 AND mean imposter lift > 0, each p < .05 (paired test over subjects)."
Both legs clear p < .05 in the pre-registered direction on the primary model in both
channels; the channels agree in direction; the robustness model holds direction
([confirm report §2](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). 88 subjects is above the
frozen ≥ 80 threshold, so H1 ran as a confirmatory test and not as an exploratory one.

### 1.1 The magnitude bar was NOT met on the contrast the frozen text names

This sits here, at the top, at the same size as the pass.

The frozen magnitude bar
([Addendum A to Amendment 2, instrument parameter 7](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md))
reads: *"a registered contrast is 'interesting' only if it reaches ≥ +0.05 cosine (channel 1,
pinned model) or ≥ +0.09 stance-match points (channel 2)"*, and the same frozen text names
**own-twin − zero-info** as H1's registered contrast.

**On the primary model in channel 1, that contrast reads +0.0378 cosine
[+0.0211, +0.0545] against the frozen ≥ +0.05 — NOT MET**
([confirm report §2](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). H1's significance legs
passed; H1's magnitude bar on its own named contrast did not, on the primary model in
channel 1. Those two sentences travel together everywhere this result is quoted.

The own-twin − imposter contrast reads **+0.0751 cosine [+0.0570, +0.0932]** against the
same ≥ +0.05 unit — **MET** — and is labelled here for what it is: the **C3 primary
contrast**, not the contrast the frozen magnitude text names for H1. Applying the frozen
unit to it is a labelled extension, not the registered comparison.

Where the same bar *was* met, for completeness and at lower prominence, because it does not
rescue the line above: own − zero-info reads +0.0578 cosine on the robustness model
(channel 1, MET) and +0.1155 stance points on the primary model (channel 2, against
≥ +0.09, MET) ([confirm report §2](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). The miss
is specific and it is the one the frozen text points at.

**Erratum note, 2026-07-28 — a post-freeze governance ambiguity, recorded rather than
resolved quietly.** Two frozen texts point at different contrasts.
[Amendment 3 C3](../../PREREGISTRATION_AMENDMENT_3.md) makes **own − imposter** the primary
contrast; the Addendum-A magnitude text, written for the same instrument, names
**own − zero-info** as H1's registered contrast. Neither was written to override the other,
and the conflict only became visible once the two numbers landed on opposite sides of the
same bar. **Owner ruling, 2026-07-28: the headline is own-vs-imposter, and the
own − zero-info magnitude miss stays top-placed at equal size.** The ambiguity is resolved
by **reporting both contrasts fully — never by choosing between them**: no back-selection of
whichever contrast clears the bar, and no quiet retirement of the one that does not. Both
travel together everywhere this result is quoted, including here.

### 1.2 Which arm moved

Read the tables above by watching the arms, not the differences. On channel 1, the primary
model's own twin sits at 0.5821 and the imposter at 0.5070, while the zero-information
baseline sits at 0.5443 — **higher than the imposter**
([confirm report §2](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). Knowing nothing beats
knowing about the wrong person. Stage 1E saw the same *shape* on survey data
([`stage1e_findings.md`](../stage1e_findings.md) section c) — but the two imposters are
different constructs (a random different respondent there, a same-domain donor here) and the
frozen text forbids conflating them
([Addendum A to Amendment 1](../../PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md)), so this is a
rhyme and not a replication. What it does explain is why the imposter arm — not the
zero-information arm — carries the claim.

Effect sizes, paired over subjects, primary model
([`report_numbers.json`](../stage2_confirm/report_numbers.json), `h1`): own − imposter
Cohen's dz = 0.88 (channel 1) and 0.41 (channel 2); own − zero-info dz = 0.48 (channel 1)
and 0.40 (channel 2).

---

## 2. What is actually being scored, and what it is not

**Stage 2 measures the public persona, not the private individual.**

That sentence is the honest object of this study. It appears here in the introduction and
again, verbatim, in the limitations. It was registered up front
([`PREREGISTRATION.md`](../../PREREGISTRATION.md) §3 and §6) and nothing in the results
softens it.

The scored claim was also reframed once, on pilot evidence, before any confirmatory data
existed. Four dev pilots showed that forced choice over this corpus is solvable without
knowing the person at all — a person-blind scorer got 17/17, 10/10, 15/15, then 8/8 across
four different distractor constructions, and a pre-committed kill rule fired
([Amendment 3 C1](../../PREREGISTRATION_AMENDMENT_3.md), record in
[`PILOT_REPORT_4.md`](../stage2_pilot4/PILOT_REPORT_4.md)). The replacement instrument is
open-ended generation, and the claim it scores is stated in the frozen text
([Amendment 2 B10.2](../../PREREGISTRATION_AMENDMENT_2.md)):

> the twin **identifies the person's actual POSITION among plausible alternative
> positions** on the same question — not that it picks a verbatim transcript answer.

So: the twin writes a free-text answer to a question the real person was actually asked in
an interview the twin never saw. Two instruments score it independently. Channel 1 is
cosine similarity between the twin's answer and the person's real answer, using a pinned
local embedding model (`all-mpnet-base-v2`, revision `e8c3b32e…`, pin asserted at run
time). Channel 2 is a stance judge (`gemini-3.5-flash`, temperature 0, thinking off,
rubric sha256 `ad050d1a…`) labelling SAME / DIFFERENT / UNCLEAR against the real answer
([confirm report §1](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). No claim rests on one
channel alone ([Amendment 3 C2.4](../../PREREGISTRATION_AMENDMENT_3.md)).

**Design in one paragraph.** Subjects are recurring interview guests from MediaSum
(463,596 NPR and CNN transcripts, 2000–2020), curated to 578 clean candidates with ≥ 3
deduplicated substantive interviews and ≥ 180 days of span, of which 137 are confirmed
long-tail ([`stage2_curation_report.md`](../stage2_curation_report.md)). Splits are strictly
chronological: grounding is earlier interviews, the test is the chronologically last one.
Five arms per item — twin redacted, twin named, zero-info redacted, zero-info named,
imposter redacted — at an identical 2,000-word grounding budget and an identical 150-word
answer cap ([confirm report §1](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). The
confirmatory draw was 140 seeded subjects; 89 survived the ≥ 3-item floor; one was dropped
by a guard (§8.5 below), leaving **88 scored subjects and 355 items**
([`report_numbers.json`](../stage2_confirm/report_numbers.json), `cohort`).

---

## 3. H7 — does a twin go stale? EXPLORATORY, and the channels disagree

**Everything in this section is exploratory and carries no confirmatory claim.** 68 subjects
carry the H7 eligibility flag; **36** of them fill at least one staleness bin after the
frozen volume control and can contribute a point to the curve. Both counts sit inside the
frozen 30–79 exploratory band, so the label does not depend on which count you read the
branch against ([confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).

H7 asks whether a twin's fidelity falls as the gap Δ between its grounding material and the
test interview grows, holding the grounding *volume* fixed and varying only its *age*
([Amendment 2 B7](../../PREREGISTRATION_AMENDMENT_2.md)). The pre-declared killer statistic
is the **crossover point**: the smallest Δ at which a *fresh* stranger's twin matches or
beats the subject's *stale* own twin.

### 3.1 The four cells

| model | channel | mean slope / year | p | pooled crossover | subjects crossing |
|---|---|---|---|---|---|
| Gemma-4-31B-it (primary) | 1 embedding | +0.00146 | 0.8650 | none in range | 13/36 |
| Gemma-4-31B-it (primary) | 2 stance | **+0.06502** | **0.0182** | **6-12m (earliest bin)** | 21/36 |
| gemini-3.5-flash-lite (robustness) | 1 embedding | −0.00804 | 0.4371 | none in range | 11/36 |
| gemini-3.5-flash-lite (robustness) | 2 stance | −0.00219 | 0.9601 | none in range | 22/36 |

Source: [confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md). Slopes are
per-subject slopes of fidelity against Δ, averaged over the 17–18 subjects who fill ≥ 2
bins; 18–19 subjects fill exactly one bin and contribute no slope. Slope CIs: primary
channel 1 [−0.01571, +0.01863]; primary channel 2 [+0.01278, +0.11761]; robustness
channel 1 [−0.02922, +0.01315]; robustness channel 2 [−0.09095, +0.08656].

### 3.2 Channel 1: no crossover, stated plainly

**In channel 1, on both models, the stale own twin stays ahead of the fresh imposter in
every filled Δ bin.** No pooled crossover occurs anywhere inside the observed range —
which stretches past three years, to a mean Δ of 1,788 days in the oldest bin
([confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)):

| Δ bin | subjects | items | mean Δ (days) | stale own twin | fresh imposter | own − fresh imposter |
|---|---|---|---|---|---|---|
| 6-12m | 15 | 59 | 261.5 | 0.5647 | 0.4830 | +0.0817 |
| 1-2y | 19 | 76 | 534.2 | 0.5520 | 0.5048 | +0.0472 |
| 2-3y | 9 | 38 | 906.9 | 0.6066 | 0.5850 | +0.0216 |
| >3y | 18 | 74 | 1788.2 | 0.5436 | 0.4823 | +0.0612 |

(Primary model, channel 1. The robustness model's channel-1 table has the same shape and
the same verdict: +0.0760 / +0.0558 / +0.0448 / +0.0688 across the four bins,
[confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md).)

Per subject, 13 of 36 cross at some bin on the primary model and 11 of 36 on the robustness
model — so individual crossovers exist; the pooled curve does not cross.

### 3.3 Channel 2 on the primary model: an anomaly, reported as measured

The stance channel on the primary model produces a **significantly POSITIVE slope**
(+0.06502 stance points per year, p = 0.0182, 95% CI [+0.01278, +0.11761]) — twins scoring
*better* with older grounding — together with a **pooled crossover at the earliest bin**
(6-12m) ([confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).

Two things about that, stated flatly:

1. **It is outside both pre-written readings.** The frozen text pre-wrote exactly two
   readings — "measurable decay, crossover in range" and "flat decay across our Δ range"
   ([Amendment 2 B7](../../PREREGISTRATION_AMENDMENT_2.md)). A significantly positive slope
   is neither. It is reported as measured, with no reading attached.
2. **A crossover at the earliest bin under a non-negative slope is not the declared decay
   pattern.** The declared pattern is a stranger's fresh twin overtaking *as Δ grows*. This
   is a stranger's fresh twin ahead at the *shortest* gap and behind afterwards. Calling it
   decay would be wrong.

### 3.4 The disagreement is itself the finding

The frozen rule ([Amendment 3 C2.4](../../PREREGISTRATION_AMENDMENT_3.md)): *"No claim rests
on one channel alone. A headline requires direction agreement across both channels;
disagreement between channels is itself reported."*

Applied mechanically to the primary model: **channel 1 points at the flat reading; channel 2
points at neither pre-written reading.** They do not agree. **H7 therefore gets no headline
reading at all**, and the disagreement, with both channels' numbers beside it, is what this
section reports ([confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).

The magnitude bar for H7 is also missed everywhere it was applied. Freshest − stalest bin,
paired over the 3–4 subjects who fill both: +0.0077 (p = 0.8595) and +0.0280 (p = 0.2440) on
channel 1 against ≥ +0.05; −0.1111 (p = 0.7418) and −0.3958 (p = 0.0864) on channel 2
against ≥ +0.09 — **NOT MET** in all four cells
([confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). The interval on the
channel-2 primary figure runs [−1.3760, +1.1538]; that is a number with no information in
it, and it is printed rather than dropped.

**Caveats printed where the numbers are.** Channel-2 per-bin stance denominators are thin
(31–65 items per bin, spread over 9–19 subjects) and are thinned further by the
imposter-arm UNCLEAR asymmetry in §8.3 — the imposter arm's answers are judged UNCLEAR far
more often than any other arm's, so the imposter's stance-match rate is computed on a
smaller and differently-selected denominator. Channel-2 H7 numbers carry wider uncertainty
than their channel-1 counterparts
([confirm report §3](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).

**Declared confounds, restated as the frozen text requires:** staleness bundles person-change
and world-change — topics move on even when the person does not — so H7 measures operational
staleness, not its mechanism; and at matched token budget, older-cutoff grounding can differ
in venue and interview count ([Amendment 2 B7](../../PREREGISTRATION_AMENDMENT_2.md)).

### 3.5 What the diagnostics narrowed, and what they did not

A separate exploratory note takes the channel disagreement apart four ways
([`h7_diagnostics.md`](../stage2_confirm/h7_diagnostics.md), CPU only, $0.00). Three things
from it belong beside the numbers above, all exploratory. **First, the precision loss sits
exactly where the anomaly lives:** on the primary model the *stale own twin's* own UNCLEAR
rate spikes to **0.3051 in the 6-12m bin against 0.1543 across the other three pooled** — that
is the bin carrying the channel-2 crossover and the start of its positive slope, and it is the
bin whose twin denominator is thinned hardest. On the robustness model, which has no positive
slope and no crossover, the same comparison is 0.2034 vs 0.1809, barely a spike. **Second, the
pooled channel-2 crossover rests on a mismatched-subject-set comparison.** The report driver
prints a bin difference only when both arms cover the same subjects (a `len(tw) == len(im)`
guard); on channel 2 the imposter arm loses whole subjects when all their imposter items come
back UNCLEAR, which is why the 6-12m and >3y rows print `n/a` in the difference column. The
crossover statistic does **not** apply that guard — it compares the two arm means whatever
subject sets produced them. So the crossover sits one column away from a difference the same
driver declines to print. That is a visible fact about the frozen statistic, reported as such;
no rule is changed and none is proposed. **Third, two candidate explanations were weakened and
neither accounts for the sign:** a Δ-correlated era covariate exists between subjects (lexical
Jaccard r = +0.2725, p = 0.0336) but vanishes within them (per-subject slope −0.000107/year,
p = 0.8491) and does not track the stance slope (r = +0.0237, p = 0.9281, n = 17); and the
slope stays positive under all three UNCLEAR handling rules (+0.06502 frozen, +0.04785 counted
as non-match, +0.07013 counted as half). Net: **the disagreement is narrowed, not resolved**,
and nothing in the note changes the conclusion above — the channels disagree, so H7 gets no
headline reading.

---

## 4. H6 — is follow-up-derived grounding worth more per token? DESCRIPTIVE, and unresolved

**Headline: DESCRIPTIVE ONLY — neither pre-written reading is applied; H6 is UNRESOLVED at
confirmatory scale on this corpus** ([H6 report §8](../stage2_confirm/H6_REPORT.md)).

H6 asks whether grounding drawn from **follow-up chains including their root** buys more twin
fidelity per token than grounding drawn from new-topic segments, at matched budget
([Amendment 2 B2](../../PREREGISTRATION_AMENDMENT_2.md)). **That wording is binding** (owner
ruling 1, 2026-07-28): the arm is never called "follow-up material", because its roots are
NEW-TOPIC turns and they make up 0.2425 of the rich arm's words at the median
([H6 report §1–2](../stage2_confirm/H6_REPORT.md)).

### 4.1 The branch collapsed, and that is the operative finding

| budget B | eligible | excluded | rich arm short | poor arm short | both short | items | branch |
|---|---|---|---|---|---|---|---|
| 1,000 (primary) | **24** | 64 | 19 | 21 | 24 | 98 | **DESCRIPTIVE** |
| 400 (dose check) | 41 | 47 | 24 | 11 | 12 | 173 | EXPLORATORY |

Source: [H6 report §2](../stage2_confirm/H6_REPORT.md). A subject enters H6 only if **both**
arms can be filled to budget B from its own grounding transcripts. At the primary budget only
**24 of 88** subjects clear that — the frozen branch puts 24 in the `< 30` band, so **no
hypothesis-test claim may be made at all** and every number below is descriptive.

**The shortfall is the finding.** Development supply implied roughly two thirds of the pool
would be eligible (4 of 6 subjects); the confirmatory corpus delivered 27%. What this run
establishes is that **the registered H6 design does not reach confirmatory power on
MediaSum-derived grounding transcripts at the frozen budget** — that, not any effect estimate,
is what carries forward ([H6 report §8](../stage2_confirm/H6_REPORT.md)). One subject (C02474)
produced zero host turns across both its grounding transcripts and fails mechanically; it is
counted, not patched.

### 4.2 The four registered-contrast numbers

Rich minus poor at matched budget, both arms' raw means beside every difference:

| model | channel | rich arm | poor arm | difference | 95% CI | paired t p | n |
|---|---|---|---|---|---|---|---|
| Gemma-4-31B-it (primary) | 1 embedding | 0.5767 | 0.5550 | **+0.0217** | [−0.0099, +0.0565] | 0.2169 | 24 |
| Gemma-4-31B-it (primary) | 2 stance | 0.6913 | 0.6623 | **+0.0290** | [−0.0797, +0.1486] | 0.6418 | 23 |
| gemini-3.5-flash-lite (robustness) | 1 embedding | 0.5755 | 0.5616 | **+0.0140** | [−0.0239, +0.0619] | 0.5348 | 24 |
| gemini-3.5-flash-lite (robustness) | 2 stance | 0.8091 | 0.6311 | **+0.1780** | [+0.0288, +0.3500] | 0.0442 | 22 |

Source: [H6 report §3](../stage2_confirm/H6_REPORT.md). All four are positive at the primary
budget and the channels agree in direction; three of four confidence intervals cross zero.
Neither magnitude unit is reached (+0.0217 against ≥ +0.05 cosine; +0.0290 against ≥ +0.09
stance points) ([H6 report §8b](../stage2_confirm/H6_REPORT.md)).

### 4.3 The sign reverses at the smaller budget

At the B = 400 dose check the primary model's sign **flips negative on both channels**:
−0.0230 cosine [−0.0388, −0.0055], p = 0.0101, n = 41 (rich 0.5331 vs poor 0.5562), and
−0.0483 stance points [−0.1283, +0.0254], p = 0.2341, n = 40 (rich 0.6657 vs poor 0.7140)
([H6 report §3](../stage2_confirm/H6_REPORT.md)). The sign reverses between budgets in 2 of 4
model × channel cells. **A contrast whose direction depends on the budget is not a stable
effect**, and the dose check is what exposed it.

**The root-excluded sensitivity arm agrees with the registered contrast at both budgets** —
positive at B = 1,000 (+0.0173 cosine [−0.0266, +0.0692], p = 0.4994, n = 16; +0.0222 stance,
p = 0.7443, n = 15) and negative at B = 400 (−0.0243 cosine, p = 0.0858, n = 29; −0.0667
stance, p = 0.2499, n = 28) ([H6 report §4](../stage2_confirm/H6_REPORT.md)). It was added
unconditionally by owner ruling 1 before any confirmatory number existed, runs on the primary
model only to conserve API budget, and for 3 subjects at B = 400 it is byte-identical to the
rich arm, so for those it is not an independent check. So the budget-dependence is not an
artifact of counting the NEW-TOPIC roots inside the rich arm — it survives removing them.

### 4.4 Why neither pre-written reading applies

Both readings were pre-written at equal prominence: the positive one ("depth-per-token beats
breadth") and the null one ("segment type does not matter at these budgets"). **Neither is
applied**, because both are hypothesis-level claims and the branch returns DESCRIPTIVE
([H6 report §8e](../stage2_confirm/H6_REPORT.md)).

The null reading in particular has to be earned, not defaulted to — it asserts a *publishable
absence* of an effect, which takes a powered null, and this run is not one. **A
non-significant positive point estimate on 24 subjects is an absence of evidence, not evidence
of absence.** The dose check cuts against a null from the other side too: a settled null does
not reverse sign when the budget halves.

### 4.5 The part-2 trust gate, and the tripwire that did not fire

The classifier had to clear a second blind audit on **confirmatory** subjects before any H6
arm was scored. **PASS: raw agreement 0.8833 against the ≥ 0.85 bar, Cohen's κ 0.7667 against
the ≥ 0.60 bar, over 120 rows from 60 confirmatory subjects**
([H6 report §7](../stage2_confirm/H6_REPORT.md); scorer output
[`h6_part2_score_output.txt`](../stage2_openended/h6_part2_score_output.txt)). The verdict was
applied by a script committed before any co-audit label existed.

Three things stay attached to that PASS rather than being cleared by it:

- **Deviation, D3 pattern, owner-directed.** The auditor line is a blind Opus 5 co-audit
  substituted for the owner's own labels. It is reported as its own line and never pooled
  with a human line — **no human line exists for it**.
- **The 120-row sizing ruling.** The frozen text sets a floor of ≥ 60 rows, not a ceiling. The
  owner raised the tranche from 60 to 120 **while still blind**, before any co-audit label
  existed, so the enlargement adds power without adding bias
  ([build note](../stage2_openended/h6_part2_build_note.md)).
- **The tripwire did not fire.** A part-2 FOLLOW-UP overturn rate above 20% would have forced
  an extra rich arm at chain depth 3; the measured rate is **18.33%**, below the line, so that
  arm was not built. Development's own rate was 25%, above the line — the appendix expected
  the arm to fire and the confirmatory measurement came in under it.

A depth-3 arm was nonetheless built later, **ordered by the owner as exploratory diagnostic
colour after the registered numbers were rendered — it is not the pre-committed sensitivity
arm, whose tripwire never fired**, and it changes no verdict: its direction matches the
registered contrast in all four cells including the B = 400 sign reversal, and eligibility
halves again from 24 subjects to 12 at the primary budget
([H6 report §11](../stage2_confirm/H6_REPORT.md)). That is the same supply dependency §4.1
reports, seen from a third angle: the depth requirement bites the rich arm, not the poor one,
and it gets worse as the requirement rises.

### 4.6 The declared confound

Stated in every write-up, as the frozen text requires
([Amendment 2 B2](../../PREREGISTRATION_AMENDMENT_2.md)): **follow-up chains occur where the
host chose to drill**, so drilled topics may be more informative regardless of the follow-up
structure. H6 tests the value of follow-up *content*, not the causal effect of asking
follow-ups. It is also a grounding-side result: it says where value sits in transcripts that
already exist, and establishes nothing about whether a live adaptive interviewer beats a
script. That confound is structural and is not corrected for.

---

## 5. Registered hypotheses without a verdict — one withdrawn, one untested under cap

Two hypotheses are on the frozen record and neither returns a pass or a fail. They are in
**different states** and the difference matters: H2 is withdrawn, H5 was run as a substituted
analysis whose registered estimator could not be computed inside the cap. Both dispositions
were decided by owner ruling on 2026-07-28
([rulings record](../stage2_confirm/RULINGS_STOPPOINT3_20260728.md)). **This is also a
different status from H6 in §4:** H6 ran end to end and came back unresolved because too few
subjects were eligible to license a claim.

**H2 (selection matters) — WITHDRAWN, documented deviation.** Model-selected context beats
random-segment context at matched budget
([`PREREGISTRATION.md`](../../PREREGISTRATION.md) §3, confirmatory at ≥ 80 subjects under the
[Amendment 1 A5](../../PREREGISTRATION_AMENDMENT_1.md) branch). It is withdrawn for three
stated reasons:

- **It was never run.** No confirmatory selection-policy arms were ever generated, so H2 has
  no data at all — not a null, not a weak effect, nothing.
- **It was superseded by the instrument change.** H2's bar was written in forced-choice
  accuracy points, and forced choice was killed outright by pre-committed kill rule
  ([Amendment 3 C1](../../PREREGISTRATION_AMENDMENT_3.md)). The bar did not transfer.
- **Stage 1E already answered the selection-policy question at lower cost.** Adaptive item
  selection did not beat random ordering there, and that was a *powered* null rather than a
  shortfall (§7, [`stage1e_findings.md`](../stage1e_findings.md)).

The withdrawal follows the precedent set when **H4 was withdrawn** under
[Amendment 2 B9.b](../../PREREGISTRATION_AMENDMENT_2.md): dated, documented, labelled a
deviation, and never left silent. Leaving a registered hypothesis unmentioned was not one of
the available options.

**H5 (calibration) — the registered estimator is UNTESTED under the cap; a substituted
analysis is reported in its place.** Full record:
[`H5_CALIBRATION.md`](../stage2_confirm/H5_CALIBRATION.md); artifacts and figures under
[`stage2_confirm/h5/`](../stage2_confirm/h5/), machine copy
[`h5_numbers.json`](../stage2_confirm/h5/h5_numbers.json).

> H5 registered a specific estimator: k = 10 self-consistency samples per prediction,
> agreement rate as the confidence, ECE ≤ 0.10, re-scoped from Stages 2–3 to Stage 2
> predictions alone by [Amendment 2 B9.b](../../PREREGISTRATION_AMENDMENT_2.md). **That
> estimator was not computed and no verdict on it is claimed.** Every confirmatory generation
> was produced at temperature 0.0, which is greedy decoding: ten samples return ten identical
> strings, so the registered confidence is a *constant* 1.0 on these records and its ECE
> measures the pinning, not the twin. Running it properly means re-generating above
> temperature 0 — a fresh run that can recycle nothing, costing **1.12 node-hours and $4.51**
> on the primary model alone (**$12.13** with the two-model structure Stage 2 uses
> everywhere), against an owner cap of 0.2 node-hours and $0.50. Both caps break on the
> cheapest honest version. In its place, and at $0.00 on CPU, a graded signal already
> attached to every generation — the channel-1 embedding cosine — was mapped monotonically to
> a confidence and calibrated against channel-2 stance correctness, cross-fit over a 44/44
> subject split so no item is scored by a map that saw its own subject. **The substituted
> estimator is a different quantity and is reported as its own line, never pooled with or
> presented as the registered one.** Held out on the primary model it reads ECE 0.0861
> (equal-width) and 0.0939 (equal-mass) — numerically under 0.10, and **this is not "H5
> passed"**: both 95% CIs cross 0.10, the secondary isotonic map lands *above* it (0.1162),
> and a predictor that always states the base rate scores ECE **exactly 0.0000** while
> knowing nothing. Read the discrimination column instead. The primary model's **AUC is
> 0.518**, a coin flip, and the mapped confidence's held-out Brier score (0.2059) is *worse*
> than that constant base-rate predictor's (0.1974). The one consistency-style signal
> measurable on these records — whether the twin says the same thing when the subject's name
> is hidden, the closest available analogue to the registered agreement rate and the only one
> a deployed twin could actually compute — has an **AUC of 0.427**, below chance, and its
> fitted map slopes *positive on one half of the subject pool and negative on the other*
> (+1.375 / −1.514). Stated plainly and labelled exploratory: **the confidence signals
> available on this record do not rank the twin's correct answers above its incorrect ones.**
> That is not evidence against registered H5, because it is not the registered estimator —
> but it is the closest available evidence about the mechanism H5 assumed, and it points the
> wrong way. Reliability diagrams are reported regardless, as the registration requires, and
> labelled as substituted on the figures themselves.

**For the record: registered H5 is neither passed nor failed.** It is untested under the cap,
with the substituted descriptive analysis reported in its place. What is still owed, if the
registered estimator is ever wanted, is the fresh generation run priced above — a cap
decision, not an analysis decision.

## 6. B8 — individual level beside population level

The standing rule ([Amendment 2 B8](../../PREREGISTRATION_AMENDMENT_2.md)) requires every
fidelity report to print individual-level lift beside a population-level distribution
metric, and to call out divergences in the body.

| contrast | individual lift (ch.1) | 95% CI | individual lift (ch.2) | population TVD (pooled) | population TVD (per-subject mean) |
|---|---|---|---|---|---|
| own − imposter | +0.0751 | [+0.0570, +0.0932] | +0.1211 | 0.1972 | 0.3298 |
| own named − imposter | +0.0778 | [+0.0597, +0.0958] | +0.1407 | 0.2282 | 0.3448 |
| own − zero-info | +0.0378 | [+0.0211, +0.0545] | +0.1155 | 0.1380 | 0.2774 |
| own named − zero-info named | +0.0270 | [+0.0104, +0.0437] | +0.0971 | 0.0986 | 0.2677 |

Source: [confirm report §5](../stage2_confirm/STAGE2_CONFIRM_REPORT.md). TVD is over the
stance categories {SAME, DIFFERENT, UNCLEAR}, taken between each contrast's own two arms —
the real answer carries no stance label of its own, so there is no reference distribution to
compare an arm against, and that choice is declared in the report rather than inherited.
Channel 1 is a continuous cosine with no categories, so the registered population metric does
not apply to it; its individual lift is printed here so both levels sit in one table, as the
rule requires. No confirmatory bar attaches to the population column.

**Divergences: none.** The individual and population levels agree on every registered
contrast — the contrasts with the largest individual lift also have the largest
between-arm distribution distance
([confirm report §5](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). Saying so explicitly is
part of the rule; a divergence would have been reported the same way.

---

## 7. Stage 1 and Stage 1E — elicitation groundwork, not a headline

Stage 1 is development only. Stage 1E is confirmatory within its own frozen bars, but those
bars are about elicitation policy on a survey corpus, not about twin fidelity. Neither
carries a Stage 2 claim. They are here because they are why Stage 2 was built the way it
was.

**The sanity gate passed.** Cross-domain prediction on RIASEC → TIPI, n = 500 held-out
persons: MAE lift over the demographics-only baseline **+0.0850 [0.0689, 0.1012]**, paired
t p = 6.87e-23, 0 parse failures on the primary arm
([`stage1_gate_report.md`](../stage1_gate_report.md)). The secondary arm (Gemma-4-31B-it +
v2) read **+0.0954 [0.0750, 0.1159]**, p = 1.25e-18, which triggered the pre-committed
promotion making Gemma the primary simulation model for every later stage.

**Adaptive item selection did not beat random ordering, and it was not a power failure.**
Confirm run, n = 1,000 persons, disjoint from everything used before. Adaptive minus random
at k = 12: **+0.0043 [−0.0055, +0.0140], p = 0.391** under the pre-registered primary
decoding, with raw MAEs of 1.4370 (adaptive) against 1.4412 (random)
([`stage1e_findings.md`](../stage1e_findings.md), full tables in
[`stage1e_confirm_report.md`](../stage1e_confirm_report.md)). The frozen bar carried its own
power note: the pilot-sized effect would have had > 95% power at this n. The effect shrank
to a fifth of its pilot size because the adaptive configuration had been picked best-of-four
on the same 150 people it was then measured on.

**BINDING SCOPE.** [Amendment 2 B1](../../PREREGISTRATION_AMENDMENT_2.md) forbids citing
Stage 1E as evidence that "adaptive interviewing doesn't work." The defensible sentence,
used verbatim wherever this result is quoted:

> **"adaptive selection over a fixed Likert item pool did not beat a population-derived
> static order at budgets up to 20 items on one corpus."**

Whether adaptivity has value in open conversation is untested and remains this project's
open question.

**A static order derived on disjoint people beat both, at a twelfth of the model calls.**
The fixed order was derived by greedy ridge regression on 2,000 *disjoint* persons, no model
involved; it read +0.074 on the derivation-adjacent split
([`overnight_stage1e.md`](../overnight_stage1e.md)) and **+0.068** on the confirm split — it
replicated ([`stage1e_findings.md`](../stage1e_findings.md)). At k = 20 the fixed order beats
adaptive under **both** decodings: adaptive − fixed = **−0.0187 [−0.0264, −0.0109],
p = 2.53e-06** (expected-value decoding) and **−0.0159 [−0.0290, −0.0028], p = 0.0174**
(argmax), with raw MAEs of 1.4269 vs 1.4082 and 1.4316 vs 1.4157. Cost side, pre-registered
as mandatory beside either reading: adaptive spent **12× the interview-time model calls and
9.2× the node-hours** (840,000 calls / 3.928 node-hours against 70,000 / 0.426).

**Budgets priced in human seconds.** k = 20 is about **92 seconds** of a respondent's
attention (plausible range 83–132 s); k = 12 is about 58 s; the whole 48-item instrument is
about 233 s ([`stage1e_timecost_note.md`](../stage1e_timecost_note.md)). Re-pricing the
x-axis changes no verdict and says so up front — every arm asks the same number of items, so
a shared rescaling cannot reorder them. What it adds is the one real asymmetry: **the
adaptive policy makes the respondent wait while it picks the next question**, somewhere
between +3% and +840% of interview wall clock depending entirely on serving engineering, and
a static script never pays that cost at all.

**Negative transfer replicated and is the most decoding-robust result in the project.** A
coherent profile belonging to the *wrong person* scores below knowing nothing at all — at
every budget, under both decodings. At k = 20: **−0.0627, p = 3.3e-13** (EV) and **−0.1486,
p = 8.8e-32** (argmax), with raw MAEs of 1.5389 / 1.5861 for the imposter against 1.4762 /
1.4375 for the baseline ([`stage1e_findings.md`](../stage1e_findings.md)). It is the only
headline effect in Stage 1E that grows under the robustness decoding. Scope limit: this
imposter is a random different respondent and measures generic-profile harm; Stage 2's
same-domain imposter is a different construct and the two must not be conflated.

**Why every contrast in this project carries both arms' raw scores.** The re-scoring note
([`rescore_ev_vs_argmax.md`](../rescore_ev_vs_argmax.md)) showed that collapsing a stated
probability distribution by its expected value damages hedging arms — and baselines hedge.
That inflated lift in four of six runs checked. The rule adopted in consequence, binding
ever since: watch which arm moves, and print both.

---

## 8. Supporting apparatus

### 8.1 The contamination meter is LIVE on both models

Per subject, (named zero-info baseline) − (name-redacted zero-info baseline). This is the
instrument that detects the model already knowing the person
([`PREREGISTRATION.md`](../../PREREGISTRATION.md) §3):

| model | named baseline | redacted baseline | meter (per-subject mean) | 95% CI | p | pooled item-level |
|---|---|---|---|---|---|---|
| Gemma-4-31B-it | 0.5577 | 0.5443 | **+0.0134** | [+0.0004, +0.0264] | 0.0437 | +0.0165 |
| gemini-3.5-flash-lite | 0.5965 | 0.5463 | **+0.0503** | [+0.0352, +0.0653] | < 0.0001 | +0.0510 |

Source: [confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md). Both fire. The
robustness model's meter is roughly four times the primary model's, and it is the arm whose
absolute scores are already declared secondary. The frozen text requires subjects with a large meter to be
analysed separately; the confirm report **identifies** them — cutoffs ≥ 0.0856 (Gemma, 9
subjects) and ≥ 0.1263 (flash-lite, 9 subjects), listed by ID
([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)) — but does not yet print a
separate lift recomputed on that subset. **That analysis now exists** — added at closeout as a
large-meter-versus-rest subsection of
[confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md), descriptive, no bar attached.
Its result runs *against* the naive fame story: on channel 1 the top-decile group's lift is
**larger** than the rest's, not smaller (own − imposter +0.0977 vs +0.0726 on the primary
model, +0.1127 vs +0.0729 on the robustness model, 9 subjects against 79), which is the same
direction as H3's flat-to-positive correlation in §8.2 and is read the same way — with the
caveat that the group is 9 people, the split is post hoc, and the two groups are different
subjects, so the gap is a difference of group means and not a test. The dev pilot measured the
meter at +0.016 and +0.048, so the confirmatory run reproduced the dev magnitude rather than
surprising us.

### 8.2 H3 (descriptive) — and the coupling that makes half of it unusable

H3 is registered as descriptive: *"lift shrinks as the contamination meter grows"*
([`PREREGISTRATION.md`](../../PREREGISTRATION.md) §3). **Only the own − imposter row can
test it.** The meter is (zero-info named − zero-info redacted) and the zero-information lift
is (own − zero-info redacted): they share the `zeroinfo_redacted` term with the same sign, so
a subject whose redacted baseline happens to be low gets a large meter *and* a large lift for
that reason alone ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).

| model | lift | usable for H3 | n | Pearson r | p | Spearman ρ | p |
|---|---|---|---|---|---|---|---|
| Gemma-4-31B-it | own − imposter | yes | 88 | +0.0563 | 0.6024 | +0.0610 | 0.5726 |
| Gemma-4-31B-it | own − zero-info | **NO — shares a term** | 88 | +0.4541 | < 0.0001 | +0.4101 | < 0.0001 |
| gemini-3.5-flash-lite | own − imposter | yes | 88 | +0.2710 | 0.0107 | +0.1923 | 0.0727 |
| gemini-3.5-flash-lite | own − zero-info | **NO — shares a term** | 88 | +0.7393 | < 0.0001 | +0.6692 | < 0.0001 |

On the confound-free row, lift does **not** shrink as the meter grows — the correlation is
non-negative on both models, weakly and non-significantly so on the primary. The large,
highly significant correlations in the unusable rows are exactly what the shared term
predicts, and anyone quoting them as support for H3 would be quoting an artifact. No
estimator was frozen for H3; the choice of Pearson and Spearman is declared in the report,
not inherited.

### 8.3 Imposter-arm UNCLEAR asymmetry — flagged on both models

The frozen UNCLEAR rule excludes UNCLEAR items from the stance-match denominator, requires
every arm's UNCLEAR rate beside its match rate, and flags a between-arm gap ≥ 0.10 as
material ([Addendum A to Amendment 2, parameter 6](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md)).
**It fired on every arm pair involving the imposter, on both models.** On the primary model
the imposter arm's UNCLEAR rate is 0.2958 against 0.1465 for the own twin (gap 0.1493) and
0.0901 for the zero-info arms (gap 0.2056); on the robustness model, 0.2535 against 0.1183
and 0.0817 ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). Consequence,
stated rather than absorbed: the imposter arm's stance-match rate is computed on ~250–265
items where the other arms use ~303–326, and those denominators are not a random subset —
they are the items where the judge could read a position at all.

### 8.4 Donor concentration

**25 distinct donors ground 89 subjects' imposter arms, and the busiest donor grounds 11**
(54 donors cleared the frozen 2,500-word floor)
([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). The imposter arm is
therefore not 89 independent strangers: a donor whose speech happens to sit close to several
subjects moves several rows at once, so own − imposter carries correlated noise across the
subjects sharing a donor. This is declared beside every own − imposter number rather than
corrected for; the 2,500-word floor that causes the concentration is frozen and was not
relaxed.

### 8.5 Guards, the dropped subject, and the rest of the instrument health record

- **Guard exclusion rate 12 of 2,176 renders = 0.0055**, against a stop rate of 0.05 that
  was never reached ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).
- **C02502 was dropped entirely.** Its test transcript (CNN-388758, 2019-12-25) is a
  **re-airing** of CNN-381362 (2019-09-25) on the same programme, replaying 47% of the test
  guest text. The two sit in different dedup clusters, so the same-event guard never saw
  them; the downstream answer-leak assert caught it and excluded all 11 of the subject's
  items. The clustering, not the split logic, is what missed it — flagged for the owner, not
  fixed in the report ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).
- **Era-violation sensitivity: negligible.** 3 flagged generations across 2 items, all on
  the robustness model. Recomputing the primary contrast with those items removed moves it
  by +0.00059 (primary model) and −0.00052 (robustness model)
  ([confirm report §4](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).
- **Truncation, word cap, parse.** 0 truncations and 0 parse failures on both models; 0–4
  over-cap answers per arm on the primary model, 8–18 on the robustness model
  ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).
- **Judge canary.** A 10-row canary ran at the start of every judging session — 0 label flips
  across 2 runs on H1, **before any confirmatory judge call was made**
  ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)), and 0 flips across a
  further 3 runs on H6 ([H6 report §6](../stage2_confirm/H6_REPORT.md)). The halt-on-flip rule
  never fired.
- **Two name-resolution failures** (C02240, C02521) yielded zero guest turns in their test
  transcripts because the canonical name did not resolve to a speaker. Both failed the build
  and never reached generation; recorded so the attrition is visible rather than absorbed
  into the survival rate ([confirm report §6](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)).
- **One declared redaction miss stands.** The S1 affiliation-redaction extension froze with
  zero collateral damage on dev prompts, and one known dev leak — a donor-identifying blog
  line — remains unfixed and declared, with the contamination meter as its backstop
  ([`s1_extension_remeasure.md`](../stage2_confirm/s1_extension_remeasure.md)).

---

## 9. Costs, reported as results

Caps signed off at GO were 8 node-hours GPU and $15 API for the H1 run. It spent **0.6028
node-hours and $6.552869** — neither cap breached, headroom 7.3972 node-hours and $8.447131
([confirm report §7](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). That figure was a running
total at report render because the stance judge was still spending;
**the ledger ([`cost_log.jsonl`](../cost_log.jsonl)) carries the final figure, and it landed
on the same number.**

| run | calls | API $ | node-hours |
|---|---|---|---|
| H1 generation, robustness model (flash-lite) | 1,911 | $1.676161 | 0 |
| H1 generation, primary model (Gemma on Leonardo) | 1,911 | $0 | 0.6028 |
| H1 stance judging | 3,822 | $4.851384 | 0 |
| H1 judge canary | 20 | $0.025324 | 0 |
| H6 follow-up classifier (Gemma on Leonardo) | 5,287 | $0 | 0.1581 |
| H6 generation, robustness model | 542 | $0.351849 | 0 |
| H6 generation, primary model (Gemma on Leonardo) | 729 | $0 | 0.2531 |
| H6 stance judging | 1,271 | $1.617427 | 0 |
| H6 judge canary | 30 | $0.038122 | 0 |
| **Stage 2 confirmatory, all of it** | | **$8.560267** | **1.0140** |

H6 added **$2.007398 API and 0.4112 node-hours** this phase, against its own caps of $6.00 and
3.0 node-hours — neither breached, and both projections ($2.07 and ≤ 0.4 node-hours) were
computed and checked before the first call ([H6 report §10](../stage2_confirm/H6_REPORT.md)).

GPU billing comes from `sacct`, not a watcher: 7 job attempts, **2 of them cancelled or
failed and still billed**, counted at their billed elapsed time. That is the honest number
and it is the one reported.

**Project totals across every run ever logged**
([`cost_log.jsonl`](../cost_log.jsonl), 101 entries): **$12.34 API** and **13.75 Leonardo
node-hours**. Five rows carry a null cost field — unpriced models, not zero — and are
excluded from the API sum rather than counted as $0. The single largest compute line in the
project is not Stage 2 at all: it is Stage 1E's confirm run at 5.27 node-hours, of which the
adaptive arm alone took 3.928 for a null effect
([`stage1e_findings.md`](../stage1e_findings.md)). Compute was never the binding constraint
on this project; owner review time was.

---

## 10. Limitations, written the way a hostile reviewer would write them

**Public personas only.** Stage 2 measures the public persona, not the private individual.
Every subject is someone performing in a broadcast interview, with a publicist's framing, a
house style, and an audience. Nothing here licenses a claim about what these people are
like, believe, or would say in private. This was declared before any data
([`PREREGISTRATION.md`](../../PREREGISTRATION.md) §3, §6) and it is the ceiling on the whole
result.

**One corpus, and a narrow one.** Every confirmatory number rests on MediaSum — NPR and CNN
broadcast interviews, 2000–2020, mostly expert guests being asked to explain something
([`stage2_curation_report.md`](../stage2_curation_report.md)). Corpus generality is untested.
The project has form here: Stage 1E's pre-registered second-corpus replication was
**cancelled** on the evidence of its own data recon, so Stage 1E's findings also rest on one
corpus ([`16pf_closure_note.md`](../16pf_closure_note.md)). Two independent single-corpus
results are not a generalization.

**Judge family overlap.** The stance judge is `gemini-3.5-flash`; the robustness scorer is
`gemini-3.5-flash-lite`. Different versions, same family. This is declared under
[Amendment 3 C3](../../PREREGISTRATION_AMENDMENT_3.md), and the consequence is applied rather
than noted: robustness-arm **absolute** scores are explicitly secondary, and only the
own − imposter contrast carries robustness weight. A reviewer who discounts every
robustness-model absolute number in this paper is doing what the frozen text already does.

**H7 is exploratory and thin.** 36 usable subjects, of whom only 17–18 fill enough bins to
contribute a slope, and 3–4 fill both ends of the freshest−stalest contrast. Per-bin stance
denominators run 31–65 items. One of the four cells reports a confidence interval of
[−1.3760, +1.1538]. Nothing in §3 should be read as a decay curve, in either direction.

**The imposter arm is flagged twice.** Its UNCLEAR rate is materially higher than every other
arm's on both models (§8.3), and its donors are concentrated — 25 donors for 89 arms, busiest
donor 11 (§8.4). Since own − imposter is the primary metric, both flags land directly on the
headline. Neither was corrected for; both were declared.

**"Pre-registered" means two different things in this paper, and the split matters.** The OSF
registration is live — 2026-07-28, https://osf.io/qz28m (§12) — but it was made **after** the
H1/H7 confirmatory run had already produced its numbers. For **H1 and H7**, the registration
is therefore **retrospective**: the only before-data guarantee is "committed to git before
the data was touched", evidenced by the per-document commits and sha256es in
[`osf_preregistration_snapshot_v4.md`](../osf_preregistration_snapshot_v4.md), which is a
weaker guarantee than an external timestamp made in advance. For the **H6
confirmatory-subject scoring, the H5 substituted analysis and the D_min = 3 arm**, the
registration predates the work and is prospective. A reviewer should apply the weaker reading
to the headline and the stronger one only to the closeout analyses.

**No comparability with the accuracy numbers this project set out beside.** The original
motivation cited Park et al.'s ~0.85 normalized accuracy on survey replay. **Forced-choice
fidelity was abandoned** by a pre-committed kill rule after four dev pilots
([Amendment 3 C1](../../PREREGISTRATION_AMENDMENT_3.md)), so this project has **no
forced-choice accuracy number for Stage 2 and cannot be compared with theirs**. Stating what
is and is not comparable:

- **Not comparable:** any accuracy figure, any normalized-to-ceiling figure, anything on a
  0–1 correctness scale. The ceiling-normalization bar was also withdrawn as confirmatory
  ([Amendment 1 A2](../../PREREGISTRATION_AMENDMENT_1.md)).
- **Comparable in kind, not in units:** the *shape* of the claim — grounded twin beats
  ungrounded baseline on held-out items — and the direction and sign of that effect.
- **Comparable and, we think, ours:** the imposter-controlled contrast (grounded on the wrong
  person, same pipeline, same budget), which separates "knows about people" from "knows about
  this person"; and elicitation budgets priced in respondent seconds.

**The instrument is younger than the hypotheses.** The open-ended instrument was adopted on
2026-07-27 and the confirmatory run launched on 2026-07-28. Its trust evidence is one dev
pilot plus an audit that **failed on its first tranche** (raw 0.7778 / κ 0.5789) and passed
only after one pre-committed rubric iteration (raw 0.8889 / κ 0.7978 on a fresh tranche,
bar never moved) ([Addendum A to Amendment 2, parameter 5](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md)).
That is a real audit trail, and it is also a young instrument.

**Human labour was substituted by LLM auditors five times.** Deviations D1–D4 record four of
them: the judge audit's human tranche was 17 of 51 rows; the fuzzy-host spot-check was fully
substituted; the H6 classifier's part-1 trust audit ran as a blind LLM co-audit; the
parameter-5 auditor line was a rubric-briefed LLM
([confirm report §8](../stage2_confirm/STAGE2_CONFIRM_REPORT.md)). The fifth is the H6
**part-2** gate in §4.5 — the one audit that ran on confirmatory subjects rather than dev
ones — which carried the same D3-pattern substitution
([H6 report §9](../stage2_confirm/H6_REPORT.md)). Each is documented, none is pooled with a
human line, and **no human label exists anywhere in the H6 trust chain**. A reviewer is
entitled to weight all of it lower than owner labels.

**The instrument has a measured run-to-run noise floor, and it is not zero.** The exploratory
depth-3 arm accidentally re-generated **72 prompts that hash identically to the registered
run's** — same model, same weights, temperature 0.0, seed 0, two separate Leonardo jobs. Only
**15 of 72 came back byte-identical**. Channel-1 cosine differs on 57 of 72, with a **median
absolute gap of 0.0138** and a maximum of 0.123, and **4 of 72 channel-2 stance labels
flipped** ([H6 report §11](../stage2_confirm/H6_REPORT.md)). The cause is not a bug in either
run: greedy decoding is deterministic in arithmetic but not across batch compositions —
vLLM's batched matrix multiplies reduce in an order that depends on what else is in the
batch, and one flipped token early in a 150-word answer changes everything after it. The
registered job batched 542 prompts, this one 182. **This noise was present in every number in
this paper before it was measurable**, and its magnitude is the same order as several of the
thin-cell differences reported above — H7's per-bin numbers and H6's small-*n* contrasts in
particular. It is one more reason those carry wide uncertainty and read as descriptive rather
than decisive. It does **not** put the headline in doubt: item-level noise averages down into
a subject mean and again across 88 subjects, and H1's subject-pooled own − imposter contrast
(**+0.0751**, CI half-width ≈ 0.018) sits well above this floor.

**H6 did not reach the power its own design assumed.** Only 24 of 88 subjects could fill both
arms at the frozen budget, against a development supply that implied roughly two thirds. H6 is
therefore descriptive, unresolved, and — because its sign reverses when the budget halves —
not even a stable direction to carry forward (§4). A reviewer should read the H6 section as a
report on a design that did not fit the corpus, not as a weak effect.

**Nulls and misses, listed together so they are not scattered:** the H1 magnitude bar missed
on its own named contrast, primary model, channel 1 (§1.1); H7 produced no headline reading
in any cell (§3); H7's magnitude bar missed in all four cells (§3.4); H6 collapsed to
DESCRIPTIVE on eligibility and neither pre-written reading could be applied (§4); H6's
magnitude bar missed on both channels (§4.2) and its sign reversed at the dose-check budget
(§4.3); H2 was withdrawn without ever being run and H5's registered estimator is untested
under the cap (§5); **H5's substituted analysis found no usable discrimination at all — the
available confidence signals do not rank the twin's correct answers above its incorrect ones
(primary-model AUC 0.518 on the oracle signal, and 0.427 — below chance — on the only signal
a deployed twin could compute)** (§5); H3's confound-free row shows no shrinkage of
lift with contamination (§8.2); Stage 1E's primary adaptive bar C1 failed (§7); the
forced-choice instrument was killed outright after four rounds (§2); the 16PF replication was
cancelled (above). None of these is a footnote in this paper and none of them should become
one downstream.

---

## 11. Ethics and scope

All material is **public broadcast interview transcript** — words these people chose to say
on NPR and CNN, already published, already archived. No private data, no participants, no
consent burden, and nothing was collected from anyone for this study.

The subject pool is **deliberately biased toward the long tail** rather than celebrities: of
578 qualifying candidates, 137 are confirmed long-tail with no Wikipedia article under any
spelling we could find ([`stage2_curation_report.md`](../stage2_curation_report.md)). The
reason is scientific — famous subjects are contaminated, and the contamination meter (§8.1)
exists to measure exactly that — but it has an ethical consequence worth naming: this study
models people who are *less* able to notice or object. The mitigation is that nothing
individuating is published. **Subjects appear in the repository only as pseudonymous IDs**
(C00203, C02502, and so on); no subject name appears in any results file or in this paper,
including in the top-decile contamination lists and the dropped-subject record.

The corpus ends in October 2020, so the fully airtight post-training-cutoff subset described
in the original registration is not available from MediaSum; contamination is handled by
design — lift over baselines, name redaction, the meter, the imposter arm — rather than by
claiming a clean cutoff we do not have.

---

## 12. Where every number in this paper comes from

| what | source |
|---|---|
| Every confirmatory Stage 2 number | [`stage2_confirm/STAGE2_CONFIRM_REPORT.md`](../stage2_confirm/STAGE2_CONFIRM_REPORT.md), machine copy [`report_numbers.json`](../stage2_confirm/report_numbers.json) |
| Report generator | `experiments/stage2_confirm_report.py`, seed 20260728, bootstrap B = 10,000, sign-flip B = 20,000, CPU only, $0.00 |
| H7 exploratory diagnostics | [`stage2_confirm/h7_diagnostics.md`](../stage2_confirm/h7_diagnostics.md), from `experiments/h7_diagnostics.py` |
| Every H6 number | [`stage2_confirm/H6_REPORT.md`](../stage2_confirm/H6_REPORT.md), machine copy [`h6_numbers.json`](../stage2_confirm/h6_numbers.json), from `experiments/h6_report.py` |
| H6 part-2 trust gate and tranche sizing | [`stage2_openended/h6_part2_score_output.txt`](../stage2_openended/h6_part2_score_output.txt), [`h6_part2_build_note.md`](../stage2_openended/h6_part2_build_note.md) |
| Stage 1 gate | [`stage1_gate_report.md`](../stage1_gate_report.md) |
| Stage 1E verdicts and tables | [`stage1e_findings.md`](../stage1e_findings.md), [`stage1e_confirm_report.md`](../stage1e_confirm_report.md) |
| Stage 1E training-split batch | [`overnight_stage1e.md`](../overnight_stage1e.md) |
| Budgets in respondent seconds | [`stage1e_timecost_note.md`](../stage1e_timecost_note.md) |
| The decoding caveat | [`rescore_ev_vs_argmax.md`](../rescore_ev_vs_argmax.md) |
| Corpus and curation | [`stage2_curation_report.md`](../stage2_curation_report.md) |
| The four dead forced-choice pilots | [`stage2_pilot/PILOT_REPORT.md`](../stage2_pilot/PILOT_REPORT.md), [`stage2_pilot2/PILOT_REPORT_2.md`](../stage2_pilot2/PILOT_REPORT_2.md), [`stage2_pilot3/PILOT_REPORT_3.md`](../stage2_pilot3/PILOT_REPORT_3.md), [`stage2_pilot4/PILOT_REPORT_4.md`](../stage2_pilot4/PILOT_REPORT_4.md) |
| Open-ended dev pilot (instrument gate) | [`stage2_openended/OE1_PILOT_REPORT.md`](../stage2_openended/OE1_PILOT_REPORT.md) |
| Redaction-scope extension | [`stage2_confirm/s1_extension_remeasure.md`](../stage2_confirm/s1_extension_remeasure.md) |
| Cost ledger | [`cost_log.jsonl`](../cost_log.jsonl) |
| Frozen contract | [`PREREGISTRATION.md`](../../PREREGISTRATION.md) + [A1](../../PREREGISTRATION_AMENDMENT_1.md), [A1-Add-A](../../PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md), [A2](../../PREREGISTRATION_AMENDMENT_2.md), [A2-Add-A](../../PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md), [A3](../../PREREGISTRATION_AMENDMENT_3.md) |
| Governance snapshot for timestamping | [`osf_preregistration_snapshot_v4.md`](../osf_preregistration_snapshot_v4.md) |
| H5 substituted calibration analysis | [`stage2_confirm/H5_CALIBRATION.md`](../stage2_confirm/H5_CALIBRATION.md), artifacts under [`stage2_confirm/h5/`](../stage2_confirm/h5/), from `experiments/h5_calibration.py` |
| Exploratory D_min = 3 arm | [`stage2_confirm/H6_REPORT.md` §11](../stage2_confirm/H6_REPORT.md), from `experiments/h6_d3_arms.py` |
| Owner rulings, stop point iii | [`stage2_confirm/RULINGS_STOPPOINT3_20260728.md`](../stage2_confirm/RULINGS_STOPPOINT3_20260728.md) |
| Errata against the frozen documents | [`PREREGISTRATION_ERRATA.md`](../../PREREGISTRATION_ERRATA.md) |

**Pre-registration deposit.** Registered **2026-07-28** at https://osf.io/qz28m, on the
associated project https://osf.io/74bq3. The registration carries the name **TWOPPLER**;
**DOPPLER** is the internal codename used throughout the pre-registration, the results record
and the `src/doppler` package. They are the same project.

**What the deposit covers, stated from the repository record.** The registration **postdates**
Stage 1, Stage 1E and the Stage 2 H1/H7 confirmatory run — for those it is **retrospective**,
and the before-data evidence remains snapshot v4's per-document git commits and sha256es. It
**predates** the H6 confirmatory-subject scoring, the H5 substituted analysis and the
D_min = 3 arm — for those it is **prospective**. The consequence for reading the headline is
spelled out in §10.

*[registration summary, verbatim: pending — the registration is inside OSF's approval window
and not yet publicly readable; to be pasted by the owner]*

Repository commit at report render: `4f3d6b067355bc5cc10d28ff538291c12aa77694` (working tree
dirty at render time; recorded rather than hidden). Governance documents are pinned by
sha256 in [confirm report §1](../stage2_confirm/STAGE2_CONFIRM_REPORT.md).
