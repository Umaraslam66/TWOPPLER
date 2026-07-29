# DOPPLER: interview-grounded digital twins under imposter-controlled, preregistered evaluation

**Preprint, 2026-07-29.**

*Umar Aslam and Claude (Fable 5, Anthropic). Claude ran the experiments, the analyses and the drafting under Umar's direction; "we" throughout means the two of us.*

Two companion technical papers (one on methods, one on results) and a plain-language article sit in the same deposit and the same repository; this preprint consolidates them. Every number here traces to a report committed in that repository, and the generators are named in section 11.

---

## Abstract

Can a language model grounded in a person's earlier public interviews predict what that person says in a later one? Answering honestly requires a baseline, not an accuracy score. We built the evaluation twice. The pre-registered instrument was forced choice, and it failed: across four successive constructions, a person-blind prompt with no name, no excerpts and no information about the subject solved 17/17, 10/10, 15/15 and 8/8 items against a chance rate of 0.25. A kill rule committed in writing before the fourth round fired on the frozen number, and there was no fifth round. The replacement is open-ended generation scored on two channels that fail differently, an embedding similarity and a stance judge, with a judge trust bar that failed on first measurement (raw 0.7778, Cohen's kappa 0.5789) and passed after one pre-committed rubric iteration (raw 0.8889, kappa 0.7978) against a bar that never moved. At confirmatory scale on 88 subjects and 355 items, a twin grounded in a person's own earlier interviews beat an identically built twin grounded in a different person's interviews: +0.0751 cosine [+0.0570, +0.0932] and +0.1211 stance points [+0.0580, +0.1843] on the primary model, own-arm means 0.5821 and 0.6914. H1's significance legs passed; H1's magnitude bar on the contrast its frozen text names, own twin minus zero-information baseline, read +0.0378 cosine against a frozen +0.05 and was NOT MET. The zero-information baseline (0.5443) outscored the imposter twin (0.5070). Exploratory analyses of staleness and grounding type returned no headline. The project cost $12.60 in API spend and 13.88 node-hours.

---

## 1. Introduction and related work

**The only honest headline metric for a person-model is lift over a baseline, and most of the work is in choosing the baseline.**

A **twin** here is a language model whose prompt contains records of one specific real person, instructed to answer as that person. **Fidelity** is agreement with the person's real answers on material the twin never saw. **Lift** is fidelity minus the fidelity of a zero-information baseline: same model, same items, no grounding, identity redacted. Lift is the only headline metric in this project, and a raw fidelity number is never reported without its baseline. The reason is arithmetic: if a twin scores 0.85 and a model that has never heard of the person scores 0.82, the twin is worth three points, not eighty-five. That rule was a design constraint from the first day, and it is what broke the pre-registered instrument.

**The design target** is Park et al. (2026): an agent grounded in a two-hour interview reproduces a person's survey answers at 0.83 of that person's own two-week test-retest consistency, against 0.74 for an agent given demographics only; the work has since been commercialised. Their paper models the discipline above by reporting that baseline beside its headline. We wanted the same question asked on natural speech, using public interviews, where the held-out data already exists: ground a twin on a person's earlier interviews, test it on real questions from a later one. Closest to our design is Jia et al. (2026), who build personas from a panel's pre-cutoff survey history and test them on held-out post-cutoff answers from the same respondents; they find personas improve distributional alignment while remaining limited for individual prediction. That is the asymmetry we report too.

**Why forced choice was chosen, and why it deserved more suspicion.** The pre-registered instrument extracts question-and-answer pairs from a held-out interview, hides the real answer among distractors, randomises position (option order alone swings multiple-choice accuracy substantially: Pezeshkpour & Hruschka, 2023), and scores whether the twin picks it. It is cheap, automatic, and has an obvious chance rate. What it ignored is the literature on benchmark leakage: items answerable without the passage or the question (Kaushik & Lipton, 2018), inference items whose hypothesis alone predicts the label (Gururangan et al., 2018), and multiple-choice items answerable from the options alone (Balepur et al., 2024). Chandak et al. (2025) ran the arc we ended up running: diagnose forced choice as leaky, replace it with free-form generation graded against a reference. Their leak and ours differ. They show a multiple-choice item is often solvable without the *question*; we show a person-prediction item is solvable without the *person*, which is narrower and, for this task, fatal. Our round-1 filter (drop every item the person-blind arm solves) is the one-shot version of AFLite (Le Bras et al., 2020).

**Two published results explain most of what we found.** Aggazzotti et al. (2024) show authorship models on speech transcripts perform well until conversational topic is controlled, at which point the apparent speaker signal largely disappears. Reinhart et al. (2025) show systematic grammatical and rhetorical differences between human and model-written text that persist across scale and are *larger* for instruction-tuned models. Together they predict both failure families we hit: harvested distractors leak topic, generated distractors leak style. Bitton et al. (2025) add that stylistic fingerprints survive being prompted into a different style, which is why a neutralising paraphrase could not launder the true option.

**Our strangest result is not unprecedented either.** Our zero-information baseline outscored our imposter twin. Morocho et al. (2026) report the closest published version: across 70K+ respondent-item instances with a proper baseline, persona prompting does not yield a clear aggregate improvement and in many cases significantly degrades performance. Wu et al. (2026) offer a mechanism: simulated populations collapse toward a homogeneous average persona, so a confident wrong persona is a displacement away from that average while no persona sits on it.

**Elicitation, and what this project does not claim.** Adaptive and uncertainty-guided questioning is an active research area with published results, and no document in this project may claim otherwise: BED-LLM applies Bayesian experimental design to adaptive LLM questioning, and our own entropy rule corresponds to their weak baseline (Choudhury et al., 2026); Wang et al. (2025) do adaptive elicitation in natural language; Su et al. (2026) do adaptive interviewing for persona simulation. Our contribution here is a **population-optimised static-script baseline** that this literature generally omits, and it is not new outside machine learning: Choi et al. (2010) found sixteen years ago that a well-chosen static short form performs only marginally worse than computerized adaptive testing, and psychometrics already has a method for what our fixed order is (Olaru & Danner, 2021). What is new is the direction and the price: here the static order did not come close, it won, at a twelfth of the model calls.

**Three contributions.** A scoped negative result about forced-choice instruments for person prediction, with a taxonomy of the mechanisms that defeat them. An imposter-controlled confirmatory measurement of interview-grounded twin fidelity, reported with both baselines and with the magnitude bar it missed. And a full validation trail for the replacement instrument, including the parts that failed.

---

## 2. Corpus and subjects

**Everything here rests on one corpus.** MediaSum is a large-scale media interview dataset (Zhu et al., 2021); its NPR half is inherited from the INTERVIEW corpus (Majumder et al., 2020). Our own recon of the released data counts **463,596 NPR and CNN interview transcripts (CNN 414k, NPR 49k), 2000 to 2020**, with parsing rules, checksums and a 20-guest hand audit committed alongside.

Curation yields **578 clean candidate subjects** with at least three deduplicated substantive interviews and at least 180 days of span, of which **137 are confirmed long-tail**: no Wikipedia article under any spelling we could find. That bias is deliberate. Famous subjects are the ones a large model may already know, and recall of a fact tracks how often it appeared in pretraining (Kandpal et al., 2023; Mallen et al., 2023).

**Splits are strictly chronological**: grounding is the earlier interviews, the test is the chronologically last one. **Five arms per item** (twin redacted, twin named, zero-information redacted, zero-information named, imposter redacted) at an identical 2,000-word grounding budget and an identical 150-word answer cap. The imposter arm is an identically built twin grounded in a *different* person's interviews, a same-domain donor, which is what separates "knows about people like this" from "knows about this person".

**Development and confirmatory subjects never mix.** All four forced-choice rounds and the open-ended dev pilot ran on **development subjects only**: six drawn by a seeded rule (seed 47, 578-row pool), three with a Wikipedia page and two long-tail, plus one added after a burn event; one of the six yields no usable question-and-answer pairs and is excluded from every prediction set. Dev subjects are excluded from every confirmatory analysis permanently, and no confirmatory subject was touched by any pilot round. **The confirmatory cohort** came from a draw of 140 seeded subjects: 89 survived the floor of at least three items, one was dropped by a guard (section 8), leaving **88 scored subjects and 355 items**.

**Models and budgets.** The primary simulation model is Gemma-4-31B-it (Gemma Team, 2026) on Leonardo EuroHPC; the registered robustness model is `gemini-3.5-flash-lite` and the stance judge is `gemini-3.5-flash` (Google DeepMind, 2026). Caps signed off at GO for the confirmatory phase were 8 node-hours of GPU and $15 of API spend.

---

## 3. A forced-choice instrument that measured the wrong thing

**We built four versions of the forced-choice instrument, each fixing the previous version's flaw, and in all four a person-blind baseline solved essentially every item.** The person-blind arm is a prompt with no name, no excerpts, no date, no information about the person at all. Chance is 0.25 in every row.

| round | where the wrong options came from | person-blind accuracy | what gave it away |
|---|---|---|---|
| 1 | other people's answers to other questions | **17 / 17** | topical coherence |
| 2 | the same subject's answers to other questions | **10 / 10** | responsiveness to the question shown |
| 3 | generated answers to the *same* question | **15 / 15** | register, world-truth, deixis |
| 4 | round 3 + four targeted fixes, subjective items only | **8 / 8** | register *inverted*, entity deployment, stance-vs-premise fit |

Item counts are small by design: 17, 10, 15 and 8. Enough to see a ceiling, not enough to size an effect.

### 3.1 What each round changed, and what survived it

**Round 1** drew three wrong options per item from other guests' answers to unrelated questions, over 17 items and five subjects. Every arm sat at 1.000 accuracy except the imposter twin at 0.941, so twin minus zero-information is **0.0000** by construction, and the only structure in the table (twin minus imposter, **+0.0500** accuracy) is not evidence about fidelity either, because the imposter is simply the one arm not pinned. The adversarial filter removed **all 17 items**; the empty table is the filter working correctly. The mechanism appears in the scorer's own words: *"Option B directly addresses the host's question about American responsibility."* It is matching topic. The median distractor's question-similarity to the real question was cosine 0.050.

**Round 2** made every wrong option a real answer the *same subject* gave in another interview, so speaker is controlled by construction. The zero-information arm still solved every item: 10 items built, accuracy 1.00 under both parser readings, mean probability mass 0.94, smallest margin over the best rival +0.80. The gate rejected 8 items and **0 survived into a final set**, so no twin or imposter number exists for round 2. The diagnostic decomposition is what mattered. Three conditions, same ten items, direction only:

| condition | question shown? | options | accuracy | mean p(true) | mean margin |
|---|---|---|---|---|---|
| standard zero-information | yes | standard | **1.00** | 0.94 | +0.91 |
| entity-stripped (names, numbers, dates removed) | yes | stripped | **1.00** | 0.87 | +0.82 |
| question-blind (host question removed) | **no** | standard | **0.10** | 0.24 | −0.12 |

**Named entities carry none of the solve; the whole thing rides on the true answer being the only option responsive to the question shown.** That is intrinsic to the shape "forced choice among verbatim real answers", because distractors are by definition answers to other questions. It is the mirror image of the question-free ablation in Balepur et al. (2024). Two secondary constraints surfaced and stayed true: the anti-leak rule starves the item pool (32 of 100 harvested answers excluded because the twin's own grounding block could quote them), and a similarity floor cannot rescue the design at this scale (a floor of 0.10 admits **zero** items, 0.05 admits three).

**Round 3** made every option a *written* answer to the same question taking a position that genuinely conflicts with the subject's real one, each passing one identical neutralising paraphrase so corpus style could not mark the true option. Responsiveness is gone by construction and the ceiling did not move: 15 items built of 17 eligible, accuracy 1.00, mean probability mass 0.77, mean margin +0.69 (range +0.30 to +0.96), **0 items surviving**. From round 3 onward the options are generated rather than harvested, so the claim being scored changes, and the change binds every write-up:

> The claim scored is that the twin **identifies the person's actual position
> among plausible alternative positions on the same question** — not that it
> picks a verbatim transcript answer.

A twin that reproduces a person's stance but not their words should therefore score well. The problem is not that the instrument is too strict about wording. It is that the real answer is identifiable as *real* without any reference to who said it.

**Round 4** attacked four of the six tells a frontier-model rater had named on round 3's material: generation few-shot conditioned on the subject's own real answers, deixis stripped from all four options or from none, an explicit plausibility check on every surviving distractor (PLAUSIBLE / FALSE / FRINGE, only PLAUSIBLE accepted), and subjective items only. Zero-information accuracy came back at **1.00 under both parser readings** (frozen parser: 8 prompts, 2 parsed, mean p(true) 0.750, mean margin +0.630; widened reading: 8 of 8, 0.694, +0.558), with **0** readings disagreeing on any item and **0** items surviving.

**The fixes worked and it did not matter.** Mean probability mass fell from 0.776 to 0.694 and the mean margin from +0.690 to +0.558, while every item was still solved. An instrument that only gets harder to solve *confidently* is not getting harder to solve. Stated so it is not over-read: round 4 is eight subjective items and round 3 was fifteen mixed ones, and round 3's widest item (+0.96, a world-truth case) is excluded from round 4 by design, so the *direction* is comparable and the *size* of the margin drop is partly a change of item mix.

**The register fix inverted the tell instead of removing it**, exactly as Reinhart et al. (2025) would predict. Conditioned on the subject's own speech, the generator stopped writing op-eds and started writing briefing documents. The real answer says the U.S. failure to act gave Russia, Assad and Iran "an absolute free ride"; the generated alternatives reach for "the intelligence community in Langley and the Pentagon", "recent UN Security Council resolutions", "the Joint Chiefs of Staff". The scorer picked the real one on *"the biting irony"*. Entity counts were matched within plus or minus 2: matching on a count is not matching on how entities are *deployed*.

### 3.2 The tell taxonomy

Six mechanisms, none of which requires knowing the person.

| tell | what it is | exposed by | fix attempted | outcome |
|---|---|---|---|---|
| **Topical coherence** | the real answer is the only option about this subject matter | round 1 | draw distractors from the same person | removed as the dominant tell; topic still separates where a career spans many subjects |
| **Responsiveness** | the real answer is the only option that answers *this* question | round 2: question-blind accuracy 0.10 vs 1.00 | generate all options as answers to the same question | **removed** by construction |
| **Register: advocacy vs hedging** | generated positions sound like op-eds; real interviewees hedge | round 3 | few-shot on the subject's own answers | **inverted**: options became bland institutional prose and the real answer still sounded like a person |
| **World-truth** | when the real position is correct about the world, every conflicting option is wrong about it | round 3 | plausibility check plus subjective-only items | 2 rejections fired (1 FALSE, 1 FRINGE); the item most exposed was excluded by design, so untested rather than beaten |
| **Deixis** | the real answer carries the host's name and conversational address, because it was spoken to a person | round 3 | strip host names and address from all four options or none | **removed**: stripped on 8 of 8 items, no round-4 trace cites it |
| **Real-voice idiom and entity deployment** | a person with a view names the actors they are talking about; generated text name-drops institutions | round 4 | none; this is what the register fix produced | **unfixed** |

A seventh, **stance-vs-premise fit**, sits across rounds 3 and 4: a leading question invites a stance, and the rule requiring every distractor to conflict with the real position puts all three distractors on the side the host did not invite. Restricting to subjective items makes this worse, not better. An eighth, **twin-pair stance inference**, was closed by a standing rule asserted at export: no rater and no scorer ever sees both twins of a duplicated question.

The taxonomy has a shape. Rounds 1 and 2 fail because a real answer is recognisable as *the answer to this question*. Rounds 3 and 4 fail because a real answer is recognisable as *something a real person actually said*. Removing one mechanism reveals the next.

### 3.3 The kill rule

The rule was recorded by the owner on 2026-07-27, **before round 4 launched and before any round-4 data existed**:

> **KILL RULE, pre-committed before any round-4 data existed:** if round 4's
> zero-information argmax accuracy is **≥ 0.90**, four-way forced choice is
> **DEAD** on this corpus and there is **no round 5 on any axis**. Rounds 1, 2
> and 3 solved 17/17, 10/10 and 15/15 by three different mechanisms; a fourth
> instrument that also fails is evidence about the format, not about the next
> patch.

Round 4 measured 1.00 under both parser readings. The rule was read on the frozen number, as written. Phase 2 was not submitted. There is no round 5.

Two supporting facts belong here rather than in a footnote. **A gate-loosening option was on the table and was not taken:** a margin-relaxed gate was specified in advance and explicitly not adopted for round 4, on the grounds that a kill rule means nothing if the bar can move in the round that tests it; it was available only if round 4 landed in the grey zone, and it did not, because accuracy was 1.00 and the *smallest* margin in the set was +0.40. **The fallback was written before the result was known:** the open-ended replacement was committed while round 4 was still being built and promoted to the frozen record unchanged in substance after the rule fired.

### 3.4 The declared finding, and exactly how wide it is

The claim is narrow and we hold it to that width: **on this corpus, with these four constructions, forced choice over a person's verbatim answers is dominated by signal that requires no knowledge of the person.** Scope: broadcast interviews with largely expert subjects, and these constructions. We do not claim forced choice is dead as an evaluation format everywhere.

Two things sharpen it. **The leak is in the instrument, not in one scorer.** A frontier model from a different family than both the generator and the scorer read round 3's option sets with no information about the speaker and identified the real option **10 times out of 10** against a 0.25 chance rate, with 9 of 10 correct rejections on controls where no real answer was present, **19/20 overall**. That line was scored and committed *before* round 4's gate was submitted, so it is a genuine prediction. It named six tells; round 4 attacked four; two were fixed, two inverted or survived, two were untested. A twin scored against such option sets would earn credit for detecting text provenance, not for modelling anyone. **What the finding is not:** it is not a claim about other corpora, other subject populations, or constructions we did not test. Four rounds is enough to stop paying for a fifth on this corpus; it is not enough to generalise beyond it.

---

## 4. The replacement instrument and its validation

**The replacement removes the option set entirely: the twin answers the held-out question in its own words, so there is no option set to leak.** This is the move Chandak et al. (2025) recommend for benchmarks generally, and it shifts risk onto the scorer rather than removing it.

### 4.1 Two channels that fail differently

- **Channel 1, embedding similarity:** cosine between the generated answer and the person's real answer, using a fixed, locally-run model, never an API model and never a scored model: `sentence-transformers/all-mpnet-base-v2`, revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`, pinned as an instrument parameter and asserted at run time (Reimers & Gurevych, 2019; Song et al., 2020).
- **Channel 2, a stance judge:** a separate model labels whether the generated answer takes the same position as the real one, SAME / DIFFERENT / UNCLEAR, under a rubric frozen by hash. Pinned as `gemini-3.5-flash`, temperature 0.0, `thinking_budget=0`, `max_output_tokens=512`, rubric r2 sha256 `ad050d1a…102464`.

Two rules bind the reporting. The primary metric is **own twin minus imposter twin**, computed identically in both channels, because judge and embedding biases (verbosity, topic priors, generosity) apply to both arms and cancel in the difference. And **no headline rests on one channel alone**: a claim requires direction agreement across both channels, and disagreement between channels is itself the reported result.

### 4.2 The dev pilot and its gate: PASS, directional

The validation gate required the instrument to separate own twin from imposter twin on the primary model, on dev subjects, before any bar could freeze. The readings were written before the numbers existed. 17 items, five dev subjects, five arms, both scored models:

| channel | model | own | imposter | own − imposter (95% CI) | subjects own > imposter | paired items |
|---|---|---|---|---|---|---|
| 1 embedding | Gemma-4-31B-it (primary) | 0.6497 | 0.5473 | **+0.1024** (0.0444, 0.1770) | 5 / 5 | 17 |
| 2 stance | Gemma-4-31B-it (primary) | 0.8125 | 0.7273 | **+0.1818** (0.0000, 0.3333) | 2 / 3 | 11 |
| 1 embedding | gemini-3.5-flash-lite (robustness) | 0.6368 | 0.5708 | **+0.0660** (0.0473, 0.1119) | 5 / 5 | 17 |
| 2 stance | gemini-3.5-flash-lite (robustness) | 0.7500 | 0.7143 | **+0.1429** (0.0000, 0.2308) | 2 / 4 | 14 |

One arithmetic caveat, since the columns invite it: on channel 2 the own and imposter means are computed over each arm's own judged items, while the difference is paired on the items where **both** sides got a non-UNCLEAR label, so it is not the subtraction of the two printed means. Channel 1 has no such gap.

**Verdict: PASS**, applied mechanically against the pre-written reading. Three qualifications were published with the verdict, not after it. **Directional, not powered:** 17 items over five subject clusters, one contributing a single item, and channel 2's interval touches zero. **The UNCLEAR asymmetry is real and it thins the data:** the judge returned UNCLEAR on 6 of 17 imposter answers (0.353) against 1 of 17 for the twin (0.059) on the primary model, which is itself an own-versus-imposter difference but drops the stance denominator to 11 items. **Channel 1's separation is partly topical:** cosine between the twin's own grounding text and the real answer correlates r ≈ **0.74** with the own-arm score, which is the effect Aggazzotti et al. (2024) document for speaker signal in transcripts, and is why no claim rests on channel 1 alone. That diagnostic is itself partial, because the grounding block is around 2,000 words and the pinned encoder truncates at its configured sequence length of **384 tokens**, which makes the caveat stronger rather than weaker.

### 4.3 A judge defect, found and pinned

The first judge pass was broken and the record says so. Running `gemini-3.5-flash` at 256 output tokens with no thinking setting, 82 of 85 replies came back with the explanation line cut mid-phrase. A two-budget probe found the cause: the model charges hidden thinking against the output budget and did not finish thinking at either budget, using 243 of 256 tokens and then 980 of 1024, both ending in truncation.

The damaging part is not the truncation. **The label itself moved between the two budgets at temperature 0** (DIFFERENT to UNCLEAR). The v1 labels were a function of the budget, not only of the rubric. Fix, taken before any re-run: thinking explicitly disabled, budget 512, everything else unchanged. A determinism probe ran first (three items, two runs, 3/3 identical labels, explanations intact) and only then did the batches run. v1 and v2 agree on 72 of 85 labels (84.7%) on the same generations; v1 is retained as the defect record and used for nothing else.

### 4.4 The judge trust bar: FAIL, one iteration, PASS

This is the part of the validation trail that failed, and it gets the same space as the parts that passed.

**The first audit was inconclusive and diagnosed as our fault.** 51 rows across three sheets, with human labels on sheet A (17 rows, owner time constraint, recorded as a deviation) and an out-of-family LLM co-auditor on all 51; the two lines agreed 17/17 on sheet A. Against the judge: human 0.7647 raw and Cohen's kappa 0.556 (Cohen, 1960); co-auditor 0.7843 and kappa 0.596. But the auditors had been briefed with a *paraphrase* of the task rather than the frozen rubric text, an audit-protocol defect recorded as the owner's, not the judge's. The owner adjudicated the four rows where the judge disagreed with a concordant auditor line: **net 2 to 2**.

**The bar was then set, in writing, before its measurement existed:** the judge passes if and only if **raw agreement ≥ 0.80 AND Cohen's kappa ≥ 0.60** against a rubric-briefed auditor line on a fresh blind tranche.

**First measurement: FAIL.** Fresh 18-row tranche (sheets D/E, seed 611, drawn only from generations unused in the first audit, key sealed): **raw 0.7778 (14/18), kappa 0.5789.** Both legs miss, and the verdict was applied mechanically. The four disagreements were each a failure mode the earlier adjudication had already ruled on, and three of the four were the judge over-calling DIFFERENT.

**One pre-committed iteration, then re-measure on the same bar.** Rubric r2 makes three targeted edits, one per diagnosed failure mode, plus a reply-format line requiring the judge to name the central issue it scored; all three edits increase strictness. A regression rule was set before the run: if r2 breaks more than 2 of the 14 previously-correct rows, stop, because it is overfitted. On the D/E regression tranche it broke **0** previously-correct rows and fixed 1 of the 4 disagreements, moving agreement from 0.7778 to 0.8333. On a fresh 18-row tranche (sheets F/G, seed 613) it read **raw 0.8889 (16/18), kappa 0.7978: a PASS** against the unchanged bar, with both remaining disagreements SAME-versus-UNCLEAR confusions and no SAME-versus-DIFFERENT flip anywhere. **The bar never moved.** It was fixed before the first measurement, missed, and met on the second attempt at the same numbers.

Three honesty notes stay attached to the PASS rather than being cleared by it.

- **Three known hard rows are still wrong.** Under r2 the judge's new central-issue line shows it *naming* the adjudicated central issue on all three residual D/E rows and still holding its call. The residual gap is the judge model's application, not the rubric text.
- **The dev supply is nearly exhausted.** The unused pool held only 4 judge-DIFFERENT rows, so the F/G tranche is 9 SAME / 4 DIFFERENT / 5 UNCLEAR by the old labels rather than balanced. Another label-balanced tranche requires fresh dev generations, not another draw.
- **Both auditor lines on the fresh tranches are LLM lines**, out-of-family from the generator, both scored models and the judge, with the frozen rubric read in full and the key never opened. They are reported as their own line and never pooled with a human line. This is the ad hoc, weaker version of what Calderon et al. (2025) formalise as a statistical test for replacing human annotators with LLMs, and we say so rather than claim equivalence.

---

## 5. Confirmatory result

**A twin grounded in a person's earlier public interviews predicts that person's answers in a later, unseen interview better than an identically built twin grounded in a different person's interviews.** That is the imposter-controlled result, it is confirmatory, it holds on 88 subjects, and it holds on both scoring channels and both scored models.

Primary contrast (own twin minus imposter twin) on the primary model, with both arms' raw means printed beside the difference as the watch-which-arm-moves rule requires:

| channel | own twin | imposter twin | difference | 95% CI | p | subjects |
|---|---|---|---|---|---|---|
| 1 embedding cosine | 0.5821 | 0.5070 | **+0.0751** | [+0.0570, +0.0932] | < 0.0001 | 88 |
| 2 stance match | 0.6914 | 0.5703 | **+0.1211** | [+0.0580, +0.1843] | 0.0003 | 85 |

Second registered leg: own twin minus the zero-information baseline (same model, same items, no grounding, identity redacted), same model, same run:

| channel | own twin | zero-info baseline | difference | 95% CI | p | subjects |
|---|---|---|---|---|---|---|
| 1 embedding cosine | 0.5821 | 0.5443 | **+0.0378** | [+0.0211, +0.0545] | < 0.0001 | 88 |
| 2 stance match | 0.6943 | 0.5788 | **+0.1155** | [+0.0543, +0.1767] | 0.0003 | 88 |

**H1 verdict: PASS.** The frozen bar is that H1 passes if and only if both mean zero-info lift > 0 AND mean imposter lift > 0, each p < .05 on a paired test over subjects. Both legs clear p < .05 in the pre-registered direction on the primary model in both channels; the channels agree in direction; the robustness model holds direction. 88 subjects is above the frozen threshold of 80, so H1 ran as a confirmatory test and not an exploratory one.

### 5.1 The magnitude bar was NOT met on the contrast the frozen text names

This sits here, at the same size as the pass.

The frozen magnitude bar reads: *"a registered contrast is 'interesting' only if it reaches ≥ +0.05 cosine (channel 1, pinned model) or ≥ +0.09 stance-match points (channel 2)"*, and the same frozen text names **own twin minus zero-info** as H1's registered contrast.

**On the primary model in channel 1, that contrast reads +0.0378 cosine [+0.0211, +0.0545] against the frozen ≥ +0.05: NOT MET.** H1's significance legs passed; H1's magnitude bar on its own named contrast did not, on the primary model in channel 1. Those two sentences travel together everywhere this result is quoted, including here.

The own-twin minus imposter contrast reads **+0.0751 cosine [+0.0570, +0.0932]** against the same ≥ +0.05 unit, **MET**, and is labelled for what it is: the primary contrast under the frozen text that makes own-versus-imposter primary, not the contrast the frozen magnitude text names for H1. Applying the frozen unit to it is a labelled extension, not the registered comparison. Where the same bar *was* met, for completeness and at lower prominence, because it does not rescue the line above: own minus zero-info reads +0.0578 cosine on the robustness model (channel 1, MET) and +0.1155 stance points on the primary model (channel 2, against ≥ +0.09, MET). The miss is specific and it is the one the frozen text points at.

**A post-freeze governance ambiguity, recorded rather than resolved quietly.** Two frozen texts point at different contrasts: one makes own minus imposter primary, and the magnitude text written for the same instrument names own minus zero-info as H1's registered contrast. Neither was written to override the other, and the conflict became visible only once the two numbers landed on opposite sides of the same bar. The owner's ruling on 2026-07-28 was that the headline is own-versus-imposter and the own minus zero-info magnitude miss stays top-placed at equal size. The ambiguity is resolved by **reporting both contrasts fully, never by choosing between them**: no back-selection of whichever contrast clears the bar, and no quiet retirement of the one that does not.

### 5.2 Which arm moved, and the zero-information anomaly

Read the tables by watching the arms, not the differences. On channel 1 the primary model's own twin sits at 0.5821 and the imposter at 0.5070, while the zero-information baseline sits at 0.5443, **higher than the imposter**. Knowing nothing beats knowing about the wrong person.

Stage 1E saw the same *shape* on survey data, where a coherent profile belonging to the wrong person scored below knowing nothing at all at every budget, but the two imposters are different constructs (a random different respondent there, a same-domain donor here) and the frozen text forbids conflating them, so this is a rhyme and not a replication. Morocho et al. (2026) report the closest published statement of the same direction with a proper baseline. What the anomaly explains inside this project is why the imposter arm, not the zero-information arm, carries the claim.

Effect sizes, paired over subjects, primary model: own minus imposter Cohen's dz = 0.88 (channel 1) and 0.41 (channel 2); own minus zero-info dz = 0.48 (channel 1) and 0.40 (channel 2).

### 5.3 Contamination, measured rather than assumed

The contamination meter is (named zero-info baseline) minus (name-redacted zero-info baseline) per subject: the instrument that detects the model already knowing the person. **It is live on both models**, reading **+0.0134** [+0.0004, +0.0264], p = 0.0437 on Gemma-4-31B-it and **+0.0503** [+0.0352, +0.0653], p < 0.0001 on `gemini-3.5-flash-lite`. The robustness model's meter is roughly four times the primary model's, and it is the arm whose absolute scores are already declared secondary. The dev pilot measured +0.016 and +0.048, so the confirmatory run reproduced the dev magnitude rather than surprising us.

A registered descriptive hypothesis says lift shrinks as the meter grows. It is testable on **only one row**, because the meter and the zero-information lift share the `zeroinfo_redacted` term with the same sign. On the confound-free own minus imposter row lift does **not** shrink: Pearson r = +0.0563 (p = 0.6024) on the primary model and +0.2710 (p = 0.0107) on the robustness model, both non-negative. The large correlations on the unusable rows are exactly what the shared term predicts, and quoting them as support would be quoting an artifact.

---

## 6. Exploratory and unresolved

Everything in this section is exploratory or descriptive and carries no confirmatory claim. The labels are in the sentences, not in footnotes.

### 6.1 H7, staleness: the channels disagree, so there is no headline

**H7 is exploratory.** It asks whether a twin's fidelity falls as the gap Δ between its grounding material and the test interview grows, holding grounding *volume* fixed and varying only its *age*. The pre-declared killer statistic is the **crossover point**: the smallest Δ at which a fresh stranger's twin matches or beats the subject's stale own twin. 68 subjects carry the eligibility flag and **36** fill at least one staleness bin after the frozen volume control; both counts sit inside the frozen exploratory band.

| model | channel | mean slope / year | p | pooled crossover | subjects crossing |
|---|---|---|---|---|---|
| Gemma-4-31B-it (primary) | 1 embedding | +0.00146 | 0.8650 | none in range | 13/36 |
| Gemma-4-31B-it (primary) | 2 stance | **+0.06502** | **0.0182** | **6-12m (earliest bin)** | 21/36 |
| gemini-3.5-flash-lite (robustness) | 1 embedding | −0.00804 | 0.4371 | none in range | 11/36 |
| gemini-3.5-flash-lite (robustness) | 2 stance | −0.00219 | 0.9601 | none in range | 22/36 |

**In channel 1, on both models, the stale own twin stays ahead of the fresh imposter in every filled Δ bin**, with no pooled crossover anywhere in a range stretching to a mean Δ of 1,788 days: on the primary model the own minus fresh-imposter gap reads +0.0817, +0.0472, +0.0216 and +0.0612 across the 6-12m, 1-2y, 2-3y and >3y bins.

**Channel 2 on the primary model produces an anomaly, reported as measured**: a significantly *positive* slope (+0.06502 stance points per year, p = 0.0182, 95% CI [+0.01278, +0.11761]), twins scoring better with older grounding, together with a pooled crossover at the earliest bin. It is outside both pre-written readings, which were "measurable decay, crossover in range" and "flat decay across our Δ range". A crossover at the earliest bin under a non-negative slope is also not the declared decay pattern, which is a stranger's fresh twin overtaking *as Δ grows*; this is a stranger's fresh twin ahead at the *shortest* gap and behind afterwards. Calling it decay would be wrong.

Applied mechanically to the frozen two-channel rule: **channel 1 points at the flat reading, channel 2 points at neither pre-written reading, they do not agree, and H7 therefore gets no headline reading at all.** The disagreement, with both channels' numbers beside it, is what this section reports. The magnitude bar is missed everywhere it was applied: freshest minus stalest bin, paired over the 3 to 4 subjects who fill both, reads +0.0077 (p = 0.8595) and +0.0280 (p = 0.2440) on channel 1 against ≥ +0.05, and −0.1111 (p = 0.7418) and −0.3958 (p = 0.0864) on channel 2 against ≥ +0.09: **NOT MET in all four cells**. The interval on the channel-2 primary figure runs [−1.3760, +1.1538], a number with no information in it, printed rather than dropped.

Exploratory diagnostics narrowed the disagreement without resolving it. **The precision loss sits exactly where the anomaly lives:** on the primary model the stale own twin's UNCLEAR rate spikes to **0.3051 in the 6-12m bin against 0.1543 across the other three pooled**, the bin carrying the crossover and the start of the positive slope; on the robustness model, which has neither, the same comparison is 0.2034 vs 0.1809. **The pooled crossover also rests on a mismatched-subject-set comparison:** the report driver prints a bin difference only when both arms cover the same subjects, and the crossover statistic does not apply that guard. That is a visible fact about the frozen statistic, reported as such; no rule is changed and none is proposed. Two candidate explanations were weakened and neither accounts for the sign, and the slope stays positive under all three UNCLEAR handling rules (+0.06502 frozen, +0.04785 counted as non-match, +0.07013 counted as half). Declared confounds: staleness bundles person-change and world-change, so H7 measures operational staleness and not its mechanism; and at matched token budget, older-cutoff grounding can differ in venue and interview count.

### 6.2 H6, grounding type: descriptive, and the sign flips with the budget

**H6 is DESCRIPTIVE ONLY. Neither pre-written reading is applied; H6 is unresolved at confirmatory scale on this corpus.** It asks whether grounding drawn from follow-up chains *including their root* buys more twin fidelity per token than grounding drawn from new-topic segments, at matched budget. That wording is binding: the arm is never called "follow-up material", because its roots are NEW-TOPIC turns and they make up 0.2425 of the rich arm's words at the median.

**The branch collapsed, and the shortfall is the operative finding.** A subject enters H6 only if both arms can be filled to budget B from its own grounding transcripts. At the primary budget of 1,000 words only **24 of 88** clear that (64 excluded, 98 items), which puts the branch below the threshold at which any hypothesis-test claim may be made; at the 400-word dose check, 41 clear it (173 items). Development supply implied roughly two thirds of the pool would be eligible (4 of 6 subjects); the confirmatory corpus delivered 27%. What this run establishes is that the registered H6 design does not reach confirmatory power on MediaSum-derived grounding transcripts at the frozen budget.

The four registered-contrast numbers, rich minus poor at matched budget, with both arms' raw means:

| model | channel | rich arm | poor arm | difference | 95% CI | paired t p | n |
|---|---|---|---|---|---|---|---|
| Gemma-4-31B-it (primary) | 1 embedding | 0.5767 | 0.5550 | **+0.0217** | [−0.0099, +0.0565] | 0.2169 | 24 |
| Gemma-4-31B-it (primary) | 2 stance | 0.6913 | 0.6623 | **+0.0290** | [−0.0797, +0.1486] | 0.6418 | 23 |
| gemini-3.5-flash-lite (robustness) | 1 embedding | 0.5755 | 0.5616 | **+0.0140** | [−0.0239, +0.0619] | 0.5348 | 24 |
| gemini-3.5-flash-lite (robustness) | 2 stance | 0.8091 | 0.6311 | **+0.1780** | [+0.0288, +0.3500] | 0.0442 | 22 |

All four are positive at the primary budget and the channels agree in direction; three of four intervals cross zero; neither magnitude unit is reached (+0.0217 against ≥ +0.05 cosine; +0.0290 against ≥ +0.09 stance points).

**The sign reverses at the smaller budget.** At B = 400 the primary model flips negative on both channels: −0.0230 cosine [−0.0388, −0.0055], p = 0.0101, n = 41 (rich 0.5331 vs poor 0.5562), and −0.0483 stance points [−0.1283, +0.0254], p = 0.2341, n = 40 (rich 0.6657 vs poor 0.7140). The sign reverses between budgets in 2 of 4 model-by-channel cells. **A contrast whose direction depends on the budget is not a stable effect**, and the dose check is what exposed it. A root-excluded sensitivity arm agrees with the registered contrast at both budgets, so the budget-dependence is not an artifact of counting the NEW-TOPIC roots inside the rich arm.

Neither pre-written reading is applied. The null reading has to be earned rather than defaulted to, because it asserts a publishable absence of an effect and this run is not powered for one. **A non-significant positive point estimate on 24 subjects is an absence of evidence, not evidence of absence**, and a settled null does not reverse sign when the budget halves.

The classifier that builds the arms cleared a second blind audit on **confirmatory** subjects before any H6 arm was scored: **raw agreement 0.8833 against the ≥ 0.85 bar and Cohen's kappa 0.7667 against the ≥ 0.60 bar, over 120 rows from 60 confirmatory subjects**, with the verdict applied by a script committed before any co-audit label existed. Two things stay attached to that PASS: the auditor line is a blind LLM co-audit substituted for the owner's own labels, so **no human line exists for it**; and a tripwire that would have forced an extra arm at chain depth 3 did **not** fire, because the measured overturn rate is 18.33% against a 20% line where development's own rate had been 25%.

The declared confound is structural and is not corrected for: **follow-up chains occur where the host chose to drill**, so drilled topics may be more informative regardless of follow-up structure. H6 tests the value of follow-up *content*, not the causal effect of asking follow-ups, and establishes nothing about whether a live adaptive interviewer beats a script.

### 6.3 Two registered hypotheses without a verdict

**H2 (selection matters): WITHDRAWN, documented deviation.** Three stated reasons. It was never run, so it has no data at all: not a null, not a weak effect, nothing. It was superseded by the instrument change, because its bar was written in forced-choice accuracy points and forced choice was killed outright. And Stage 1E had already answered the selection-policy question at lower cost with a *powered* null. The withdrawal follows the precedent set when an earlier hypothesis was withdrawn: dated, documented, labelled a deviation, never left silent.

**H5 (calibration): the registered estimator is UNTESTED under the cap; a substituted analysis is reported in its place.** H5 registered ten self-consistency samples per prediction with the agreement rate as the confidence and an ECE bar of ≤ 0.10. Every confirmatory generation was produced at temperature 0.0, which is greedy decoding, so ten samples return ten identical strings and the registered confidence is a constant 1.0 on these records. Running it properly means re-generating above temperature 0, a fresh run that can recycle nothing, costing **1.12 node-hours and $4.51** on the primary model alone (**$12.13** with the two-model structure used everywhere else) against an owner cap of 0.2 node-hours and $0.50. Both caps break on the cheapest honest version.

In its place, at $0.00 on CPU, the channel-1 embedding cosine was mapped monotonically to a confidence and calibrated against channel-2 stance correctness, cross-fit over a 44/44 subject split so no item is scored by a map that saw its own subject. **The substituted estimator is a different quantity and is reported as its own line, never pooled with or presented as the registered one.** Held out on the primary model it reads ECE 0.0861 (equal-width) and 0.0939 (equal-mass), numerically under 0.10, and **this is not "H5 passed"**: both 95% CIs cross 0.10, the secondary isotonic map lands above it (0.1162), and a predictor that always states the base rate scores ECE exactly 0.0000 while knowing nothing.

Read the discrimination column instead. The primary model's **AUC is 0.518**, a coin flip, and the mapped confidence's held-out Brier score (0.2059) is *worse* than the constant base-rate predictor's (0.1974). The one consistency-style signal measurable on these records, whether the twin says the same thing when the subject's name is hidden, which is the closest analogue to the registered agreement rate and the only one a deployed twin could compute, has an **AUC of 0.427**, below chance, and its fitted map slopes positive on one half of the subject pool and negative on the other (+1.375 and −1.514). Stated plainly and labelled exploratory: **the confidence signals available on this record do not rank the twin's correct answers above its incorrect ones.** That is not evidence against registered H5, because it is not the registered estimator, but it is the closest available evidence about the mechanism H5 assumed, and it points the wrong way.

### 6.4 Stage 1E: the elicitation groundwork behind the design

Stage 1E is confirmatory within its own frozen bars, but those bars are about elicitation policy on a survey corpus, not about twin fidelity. It carries no Stage 2 claim. It is here because it is why Stage 2 was built the way it was.

**Adaptive item selection did not beat random ordering, and it was not a power failure.** Confirm run, n = 1,000 persons, disjoint from everything used before. Adaptive minus random at k = 12: **+0.0043 [−0.0055, +0.0140], p = 0.391** under the pre-registered primary decoding, raw MAEs 1.4370 (adaptive) against 1.4412 (random). The frozen bar carried its own power note: the pilot-sized effect would have had over 95% power at this n. It shrank to a fifth of its pilot size because the adaptive configuration had been picked best-of-four on the same 150 people it was then measured on. The binding scope limit, used verbatim wherever this is quoted:

> **"adaptive selection over a fixed Likert item pool did not beat a population-derived
> static order at budgets up to 20 items on one corpus."**

Whether adaptivity has value in open conversation is untested and remains this project's open question.

**A static order derived on disjoint people beat both, at a twelfth of the model calls.** The fixed order came from greedy ridge regression on 2,000 disjoint persons with no model involved; it read +0.074 on the derivation-adjacent split and **+0.068** on the confirm split, so it replicated. At k = 20 it beats adaptive under both decodings: adaptive minus fixed = **−0.0187 [−0.0264, −0.0109], p = 2.53e-06** (expected-value decoding) and **−0.0159 [−0.0290, −0.0028], p = 0.0174** (argmax). Cost side, pre-registered as mandatory beside either reading: adaptive spent **12 times the interview-time model calls and 9.2 times the node-hours** (840,000 calls and 3.928 node-hours against 70,000 and 0.426).

**Budgets priced in human seconds.** k = 20 is about **92 seconds** of a respondent's attention (plausible range 83 to 132 s), k = 12 about 58 s, the whole 48-item instrument about 233 s. Re-pricing the x-axis changes no verdict, because every arm asks the same number of items and a shared rescaling cannot reorder them. What it adds is the one real asymmetry: **the adaptive policy makes the respondent wait while it picks the next question**, between +3% and +840% of interview wall clock depending entirely on serving engineering, and a static script never pays that cost.

**Negative transfer replicated and is the most decoding-robust result in the project.** A coherent profile belonging to the *wrong person* scores below knowing nothing at all, at every budget, under both decodings. At k = 20: **−0.0627, p = 3.3e-13** (expected value) and **−0.1486, p = 8.8e-32** (argmax), raw MAEs 1.5389 and 1.5861 for the imposter against 1.4762 and 1.4375 for the baseline. It is the only headline effect in Stage 1E that grows under the robustness decoding. Scope limit: this imposter is a random different respondent and measures generic-profile harm, while Stage 2's same-domain imposter is a different construct, and the two must not be conflated.

---

## 7. Nulls and misses in one place

Listed together so they are not scattered, and none should become a footnote downstream.

- The H1 magnitude bar missed on its own named contrast, primary model, channel 1 (section 5.1).
- H7 produced no headline reading in any cell, and H7's magnitude bar missed in all four cells (section 6.1).
- H6 collapsed to DESCRIPTIVE on eligibility, neither pre-written reading could be applied, its magnitude bar missed on both channels, and its sign reversed at the dose-check budget (section 6.2).
- H2 was withdrawn without ever being run, and H5's registered estimator is untested under the cap (section 6.3).
- H5's substituted analysis found no usable discrimination at all: the available confidence signals do not rank the twin's correct answers above its incorrect ones (primary-model AUC 0.518 on the oracle signal, and 0.427, below chance, on the only signal a deployed twin could compute) (section 6.3).
- The confound-free contamination row shows no shrinkage of lift as the meter grows (section 5.3).
- Stage 1E's primary adaptive bar failed (section 6.4).
- The forced-choice instrument was killed outright after four rounds (section 3).
- A pre-registered second-corpus replication for Stage 1E was cancelled on the evidence of its own data recon (section 8).

---

## 8. Limitations

**Public personas, not private people.** Stage 2 measures the public persona, not the private individual. Every subject is performing in a broadcast interview, with a publicist's framing, a house style, and an audience. Nothing here licenses a claim about what these people are like, believe, or would say in private. This was declared before any data existed and it is the ceiling on the whole result.

**One corpus, and a narrow one.** Every confirmatory number rests on MediaSum: NPR and CNN broadcast interviews, 2000 to 2020, mostly expert guests being asked to explain something. Corpus generality is untested, and the project has form here: Stage 1E's pre-registered second-corpus replication was **cancelled** on the evidence of its own data recon, so Stage 1E also rests on one corpus. Two independent single-corpus results are not a generalization. The tells in section 3 are plausibly corpus-specific too; a corpus of ordinary people speaking casually might behave differently, and we did not test one.

**Judge family overlap.** The stance judge is `gemini-3.5-flash` and the robustness scorer is `gemini-3.5-flash-lite`: different versions, same family. This is a declared validity threat with a published mechanism, since evaluators recognise and favour text from their own family (Panickssery et al., 2024). The consequence is applied rather than noted: robustness-arm **absolute** scores are explicitly secondary, and only the own minus imposter contrast carries robustness weight.

**Human labour was substituted by LLM auditors five times.** The judge audit's human tranche was 17 of 51 rows; a spot-check was fully substituted; the H6 classifier's part-1 trust audit ran as a blind LLM co-audit; the parameter-5 auditor line was a rubric-briefed LLM; and the H6 part-2 gate, the one audit on confirmatory subjects, carried the same substitution. Each is documented, none is pooled with a human line, and **no human label exists anywhere in the H6 trust chain**. A pre-registered human detectability line on the forced-choice material was also waived and an out-of-family LLM rater substituted: **no human hit rate exists and none is fabricated.** A reviewer is entitled to weight all of it lower than owner labels.

**H7 is exploratory and thin.** 36 usable subjects, of whom only 17 to 18 fill enough bins to contribute a slope and 3 to 4 fill both ends of the freshest-minus-stalest contrast. Nothing in section 6.1 should be read as a decay curve, in either direction.

**The imposter arm is flagged twice, and it carries the headline.** Its UNCLEAR rate is materially higher than every other arm's on both models: on the primary model 0.2958 against 0.1465 for the own twin and 0.0901 for the zero-info arms; on the robustness model 0.2535 against 0.1183 and 0.0817. Its stance-match rate is therefore computed on roughly 250 to 265 items where the other arms use roughly 303 to 326, and those denominators are not a random subset; they are the items where the judge could read a position at all. Its donors are also concentrated: **25 distinct donors ground 89 subjects' imposter arms and the busiest grounds 11**, so own minus imposter carries correlated noise across subjects sharing a donor. Neither was corrected for; both were declared.

**The instrument has a measured run-to-run noise floor, and it is not zero.** An exploratory arm accidentally re-generated **72 prompts that hash identically to the registered run's** (same model, same weights, temperature 0.0, seed 0, two separate jobs). Only **15 of 72 came back byte-identical**. Channel-1 cosine differs on 57 of 72, with a **median absolute gap of 0.0138** and a maximum of 0.123, and **4 of 72 channel-2 stance labels flipped**. The cause is not a bug in either run: greedy decoding is deterministic in arithmetic but not across batch compositions, because batched matrix multiplies reduce in an order that depends on what else is in the batch (Kwon et al., 2023; Yuan et al., 2025), and one flipped token early in a 150-word answer changes everything after it. The registered job batched 542 prompts and this one 182. **This noise was present in every number here before it was measurable**, and its magnitude is the same order as several thin-cell differences in section 6. It does **not** put the headline in doubt: item-level noise averages down into a subject mean and again across 88 subjects, and H1's own minus imposter contrast (+0.0751, CI half-width around 0.018) sits well above this floor.

**The corpus has a defect our guards caught only downstream.** Guard exclusion rate was 12 of 2,176 renders = 0.0055 against a stop rate of 0.05 that was never reached, with 0 truncations and 0 parse failures on both models. But **one subject, C02502, was dropped entirely**: its test transcript is a **re-airing** of an earlier transcript on the same programme, replaying 47% of the test guest text. The two sit in different dedup clusters, so the same-event guard never saw them; the downstream answer-leak assert caught it and all 11 of the subject's items were excluded. We could find no published work documenting quality defects in this corpus, so the re-airing, and the misattribution risk we flagged in older panel material, appear to be original observations about a widely-used dataset.

**No comparability with the accuracy numbers this project set out beside.** The original motivation cited a normalized accuracy on survey replay (Park et al., 2026). Forced-choice fidelity was abandoned by a pre-committed kill rule, so this project has **no forced-choice accuracy number for Stage 2 and cannot be compared with theirs**. What is comparable is the shape and direction of the claim, that a grounded twin beats an ungrounded baseline on held-out items, and not any figure on a 0-to-1 correctness scale.

**"Pre-registered" means two different things here.** The governance documents are frozen in git with per-document commit and sha256 provenance, and the OSF registration is live (2026-07-28), but it was made **after** the H1 and H7 confirmatory run had produced its numbers. For **H1, H7 and every forced-choice round in section 3** the registration is therefore **retrospective**, and the only before-data guarantee is "committed to version control before the data was touched", which is weaker than an external timestamp made in advance. For the **H6 confirmatory-subject scoring, the H5 substituted analysis and the exploratory depth arm** the registration predates the work and is **prospective**. A reviewer should apply the weaker reading to the headline and the stronger one only to the closeout analyses.

---

## 9. Ethics

**All material is public broadcast interview transcript**: words these people chose to say on NPR and CNN, already published and already archived. No private data, no participants, no consent burden, and nothing was collected from anyone for this study. That is a real defence and not a complete one. Public availability does not settle consent, because people do not anticipate downstream aggregation and analysis, and the standing recommendations are to avoid spotlighting individuals and to avoid publishing inferred characteristics (Lauterwasser & Nedzhvetskaya, 2023). We follow both.

**The subject pool is deliberately biased toward the long tail** rather than celebrities: of 578 qualifying candidates, 137 are confirmed long-tail with no Wikipedia article under any spelling we could find. The reason is scientific, because famous subjects are contaminated and the contamination meter exists to measure exactly that (Carlini et al., 2021). The ethical consequence is worth naming: this study models people who are *less* able to notice or object. That asymmetry between the person whose data is used and the party using it is the central problem in the digital-replica ethics literature (Methuku & Myakala, 2025), and the strongest form of the objection is that building a high-fidelity model of a person without consent is simultaneously a privacy and a personhood violation (Favela & Amon, 2023). Our answer is a mitigation and not a refutation: **subjects appear in the repository only as pseudonymous IDs** (C00203, C02502, and so on), no subject name appears in any results file or in this preprint, and nothing individuating is published.

**The contrast with the design target is worth stating.** The published governance companion to that work recommends tiered access, audit logs and revocable consent for agents built from real people's interview data (Park et al., 2025). Their subjects were paid, consenting, opt-in participants with a revocation path. Ours are non-consenting broadcast guests, and no revocation path exists because no individual twin is published or retained as a product.

**Contamination is handled by design rather than by a claim we cannot support.** The corpus ends in October 2020, so the airtight post-training-cutoff subset described in the original registration is not available. Instead of asserting a clean cutoff we handle contamination through lift over baselines, name redaction, the contamination meter and the imposter arm. Off-the-shelf membership-inference detectors exist (Shi et al., 2024) and were not used, because they need an unseen side to the split and this corpus does not have one.

---

## 10. Cost

**The whole project cost $12.60 in API spend and 13.88 Leonardo node-hours**, across 105 ledger entries. Five rows carry a null cost field (unpriced models, not zero) and are excluded from the API sum rather than counted as $0.

Killing the forced-choice instrument after four rounds cost under a node-hour and under a dollar: **0.945 node-hours and $0.508** across all four rounds, the open-ended dev pilot and the judge iteration. The confirmatory phase spent **1.139 node-hours and $8.817063** against caps of 8 node-hours and $15, with the H1 run itself at 0.6028 node-hours and $6.552869. GPU time is billed from the scheduler's own accounting rather than an in-process wall clock, so failed and cancelled jobs are billed and counted: 7 job attempts on the confirmatory phase, 2 of them cancelled or failed and still billed. The single largest compute line in the project is not Stage 2 at all: it is Stage 1E's confirm run at 5.27 node-hours, of which the adaptive arm alone took 3.928 for a null effect.

**Compute was never the binding constraint on this project; owner review time was.** That is also why the kill rule mattered: the expensive thing about a fifth forced-choice round would not have been the dollar.

---

## 11. Reproducibility

**Pre-registration deposit.** Registered **2026-07-28** at https://osf.io/qz28m, on the associated project https://osf.io/74bq3. The registration carries the name **TWOPPLER**; **DOPPLER** is the internal codename used throughout the pre-registration, the results record and the `src/doppler` package. They are the same project.

**What the deposit covers, stated from the repository record.** The registration **postdates** Stage 1, Stage 1E and the Stage 2 H1 and H7 confirmatory run, and for those it is **retrospective**, with the before-data evidence remaining the per-document git commits and sha256 hashes in `osf_preregistration_snapshot_v4.md`. It **predates** the H6 confirmatory-subject scoring, the H5 substituted analysis and the exploratory depth arm, and for those it is **prospective**.

**Report generators.** Every confirmatory number comes from one place, `results/stage2_confirm/STAGE2_CONFIRM_REPORT.md`, with a machine-readable copy at `report_numbers.json`, produced by `experiments/stage2_confirm_report.py` at seed 20260728, bootstrap B = 10,000, sign-flip B = 20,000, CPU only, $0.00. H6 numbers come from `H6_REPORT.md` via `experiments/h6_report.py`, the H7 diagnostics from `h7_diagnostics.md`, and the H5 substituted analysis from `H5_CALIBRATION.md` via `experiments/h5_calibration.py`. The four forced-choice rounds regenerate from `experiments/stage2_pilot.py` through `stage2_pilot4.py` and the open-ended dev pilot from `experiments/stage2_oe1.py`, with the judge audit scored by `oe1_param5_score.py`, `oe1_r2_judge.py` and `oe1_r2_score.py`. Costs come from `results/cost_log.jsonl`, one line per run.

**Frozen contract.** `PREREGISTRATION.md` plus Amendments 1, 2 and 3 and their addenda, all committed with per-document sha256 provenance, with deviations and corrections appended to `PREREGISTRATION_ERRATA.md` rather than edited in place. Owner rulings are dated in `results/stage2_confirm/RULINGS_STOPPOINT3_20260728.md`.

**Repository.** Source under `src/doppler/`, run drivers under `experiments/`, all reports under `results/`. The corpus is not redistributed; it is MediaSum (Zhu et al., 2021), obtained from its public release, and the curation producing our 578 candidates and 137 long-tail subjects regenerates from `experiments/mediasum_index.py`. The chronological map a cold reader should start from is `results/PROJECT_LOG.md`, which summarises and links but is never the source of truth for any number.

---

## References

Aggazzotti, C., Andrews, N., & Smith, E. A. (2024). Can authorship attribution models distinguish speakers in speech transcripts? Transactions of the Association for Computational Linguistics. arXiv:2311.07564. https://arxiv.org/abs/2311.07564

Balepur, N., Ravichander, A., & Rudinger, R. (2024). Artifacts or abduction: How do LLMs answer multiple-choice questions without the question? In Proceedings of ACL 2024. arXiv:2402.12483. https://arxiv.org/abs/2402.12483

Bitton, Y., Bitton, R., & Nisan, S. (2025). Detecting stylistic fingerprints of large language models. arXiv:2503.01659. https://arxiv.org/abs/2503.01659

Calderon, N., Reichart, R., & Dror, R. (2025). The alternative annotator test for LLM-as-a-judge: How to statistically justify replacing human annotators with LLMs. In Proceedings of ACL 2025. arXiv:2501.10970. https://arxiv.org/abs/2501.10970

Carlini, N., Tramèr, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, Ú., Oprea, A., & Raffel, C. (2021). Extracting training data from large language models. In Proceedings of USENIX Security 2021. arXiv:2012.07805. https://arxiv.org/abs/2012.07805

Chandak, N., Goel, S., Prabhu, A., Hardt, M., & Geiping, J. (2025). Answer matching outperforms multiple choice for language model evaluation. arXiv:2507.02856. https://arxiv.org/abs/2507.02856

Choi, S. W., Reise, S. P., Pilkonis, P. A., Hays, R. D., & Cella, D. (2010). Efficiency of static and computer adaptive short forms compared to full-length measures of depressive symptoms. Quality of Life Research, 19(1), 125–136. doi:10.1007/s11136-009-9560-5

Choudhury, D., Williamson, S., Goliński, A., Miao, N., Bickford Smith, F., Kirchhof, M., Zhang, Y., & Rainforth, T. (2026). BED-LLM: Intelligent information gathering with LLMs and Bayesian experimental design. In Proceedings of ICLR 2026. arXiv:2508.21184 (posted 2025). https://arxiv.org/abs/2508.21184

Cohen, J. (1960). A coefficient of agreement for nominal scales. Educational and Psychological Measurement, 20(1), 37–46. doi:10.1177/001316446002000104

Favela, L. H., & Amon, M. J. (2023). The ethics of human digital twins: Counterfeit people, personhood, and the right to privacy. In 2023 IEEE 3rd International Conference on Digital Twins and Parallel Intelligence (DTPI), 16–22. https://ieeexplore.ieee.org/document/10365409/

Gemma Team, Google DeepMind. (2026). Gemma 4 technical report. Preprint, arXiv:2607.02770, https://arxiv.org/abs/2607.02770

Google DeepMind. (2026). Gemini 3.5 Flash and Gemini 3.5 Flash-Lite model cards. Published under https://deepmind.google/models/model-cards/ (paths `gemini-3-5-flash` and `gemini-3-5-flash-lite`).

Gururangan, S., Swayamdipta, S., Levy, O., Schwartz, R., Bowman, S. R., & Smith, N. A. (2018). Annotation artifacts in natural language inference data. In Proceedings of NAACL-HLT 2018, 107–112. https://aclanthology.org/N18-2017/

Jia, M., Chen, Y., Sharma, D., & Diaz-Rodriguez, J. (2026). When can digital personas reliably approximate human survey findings? arXiv:2605.10659. https://arxiv.org/abs/2605.10659

Kandpal, N., Deng, H., Roberts, A., Wallace, E., & Raffel, C. (2023). Large language models struggle to learn long-tail knowledge. In Proceedings of ICML 2023. arXiv:2211.08411. https://arxiv.org/abs/2211.08411

Kaushik, D., & Lipton, Z. C. (2018). How much reading does reading comprehension require? A critical investigation of popular benchmarks. In Proceedings of EMNLP 2018. arXiv:1808.04926. https://arxiv.org/abs/1808.04926

Kwon, W., Li, Z., Zhuang, S., Sheng, Y., Zheng, L., Yu, C. H., Gonzalez, J. E., Zhang, H., & Stoica, I. (2023). Efficient memory management for large language model serving with PagedAttention. In Proceedings of SOSP 2023. arXiv:2309.06180. https://arxiv.org/abs/2309.06180

Lauterwasser, S., & Nedzhvetskaya, N. (2023). Privacy in public? The ethics of academic research with publicly available social media data. Berkeley Journal of Sociology, 11 August 2023. https://berkeleyjournal.org

Le Bras, R., Swayamdipta, S., Bhagavatula, C., Zellers, R., Peters, M. E., Sabharwal, A., & Choi, Y. (2020). Adversarial filters of dataset biases. In Proceedings of ICML 2020. arXiv:2002.04108. https://arxiv.org/abs/2002.04108

Majumder, B. P., Li, S., Ni, J., & McAuley, J. (2020). Interview: Large-scale modeling of media dialog with discourse patterns and knowledge grounding. In Proceedings of EMNLP 2020, 8129–8141. doi:10.18653/v1/2020.emnlp-main.653. arXiv:2004.03090

Mallen, A., Asai, A., Zhong, V., Das, R., Khashabi, D., & Hajishirzi, H. (2023). When not to trust language models: Investigating effectiveness of parametric and non-parametric memories. In Proceedings of ACL 2023, 9802–9822. doi:10.18653/v1/2023.acl-long.546

Methuku, V., & Myakala, P. K. (2025). Digital doppelgangers: Ethical and societal implications of pre-mortem AI clones. arXiv:2502.21248. https://arxiv.org/abs/2502.21248

Morocho, E. E. T., Cima, L., Fagni, T., Avvenuti, M., & Cresci, S. (2026). Assessing the reliability of persona-conditioned LLMs as synthetic survey respondents. arXiv:2602.18462. https://arxiv.org/abs/2602.18462

Olaru, G., & Danner, D. (2021). Developing cross-cultural short scales using ant colony optimization. Assessment, 28(1), 199–210. doi:10.1177/1073191120918026

Panickssery, A., Bowman, S. R., & Feng, S. (2024). LLM evaluators recognize and favor their own generations. In Advances in Neural Information Processing Systems 37 (NeurIPS 2024). arXiv:2404.13076. https://arxiv.org/abs/2404.13076

Park, J. S., Zou, C. Q., Kamphorst, J., Egan, N., Shaw, A., Hill, B. M., Cai, C., Morris, M. R., Liang, P., Willer, R., & Bernstein, M. S. (2026). LLM agents grounded in self-reports enable general-purpose simulation of individuals. arXiv:2411.10109 (v1, 2024, circulated as "Generative agent simulations of 1,000 people"). https://arxiv.org/abs/2411.10109

Park, J. S., Zou, C. Q., Shaw, A., Hill, B. M., Cai, C. J., Morris, M. R., Willer, R., Liang, P., & Bernstein, M. S. (2025). Simulating human behavior with AI agents. Stanford HAI Policy Brief. https://hai.stanford.edu/policy/simulating-human-behavior-with-ai-agents

Pezeshkpour, P., & Hruschka, E. (2023). Large language models sensitivity to the order of options in multiple-choice questions. arXiv:2308.11483. https://arxiv.org/abs/2308.11483

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In Proceedings of EMNLP-IJCNLP 2019. arXiv:1908.10084. https://arxiv.org/abs/1908.10084

Reinhart, A., Markey, B., Laudenbach, M., Pantusen, K., Yurko, R., Weinberg, G., & Brown, D. W. (2025). Do LLMs write like humans? Variation in grammatical and rhetorical styles. Proceedings of the National Academy of Sciences, 122, e2422455122. arXiv:2410.16107. https://arxiv.org/abs/2410.16107

Shi, W., Ajith, A., Xia, M., Huang, Y., Liu, D., Blevins, T., Chen, D., & Zettlemoyer, L. (2024). Detecting pretraining data from large language models. In Proceedings of ICLR 2024. arXiv:2310.16789. https://arxiv.org/abs/2310.16789

Song, K., Tan, X., Qin, T., Lu, J., & Liu, T.-Y. (2020). MPNet: Masked and permuted pre-training for language understanding. In Advances in Neural Information Processing Systems 33 (NeurIPS 2020), 16857–16867. arXiv:2004.09297. https://arxiv.org/abs/2004.09297

Su, R., Liu, Y., & Hu, J. (2026). Adaptive interviewing for persona simulation in LLMs: Evidence-grounded reasoning improves decision alignment. arXiv:2605.29458 (preprint, not peer reviewed). https://arxiv.org/abs/2605.29458

Wang, J., Zollo, T., Zemel, R., & Namkoong, H. (2025). Adaptive elicitation of latent information using natural language. In Proceedings of ICML 2025. arXiv:2504.04204. https://arxiv.org/abs/2504.04204

Wu, Z., Peng, R., Ito, T., Onizuka, M., & Xiao, C. (2026). LLM-based social simulations require a boundary. In Proceedings of ICML 2026 (Position Paper Track). arXiv:2506.19806. https://arxiv.org/abs/2506.19806

Yuan, J., Li, Y., Ding, Y., Xie, S., Li, T., Zhao, Y., Wan, Z., Shi, Y., Hu, W., & Liu, Z. (2025). Understanding and mitigating numerical sources of nondeterminism in LLM inference. arXiv:2506.09501. https://arxiv.org/abs/2506.09501

Zhu, C., Liu, Y., Mei, J., & Zeng, M. (2021). MediaSum: A large-scale media interview dataset for dialogue summarization. In Proceedings of NAACL-HLT 2021, 5927–5934. doi:10.18653/v1/2021.naacl-main.474. arXiv:2103.06410

---

*All pilot numbers in section 3 are development-subject measurements; no confirmatory subject was touched by any round reported there. Every confirmatory number in sections 5 and 6 comes from `results/stage2_confirm/STAGE2_CONFIRM_REPORT.md` and its machine-readable copy.*
