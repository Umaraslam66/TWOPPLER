# Stage 2 pilot report — round 2 (same-subject distractors)

# PILOT -- pipeline validation on dev subjects; no research conclusions.

**PILOT -- pipeline validation on dev subjects; no research conclusions.** Every number below is a pipeline-validation number on the same six development subjects as round 1. Nothing here answers a pre-registered bar, nothing here is confirmatory, and no result in it should be quoted as a finding about twins. Contract: SPEC.md v1.8 (D6-v2). Model leonardo-gemma4-31b-it, temperature 0.0, tp 4, max-model-len 8192. 30 model calls, 0 API calls, $0.00 API, 0.2633 node-hours.

Round 1 is `results/stage2_pilot/PILOT_REPORT.md`. Round 2 changed exactly one thing: where the wrong options come from.

---

## 1. The headline: the redesign did not fix the ceiling, and we now know why

Round 1 finding 8.0 was that the zero-information baseline solved 17 items of 17, because the three wrong options were other people's answers to unrelated questions and topical coherence alone won every item. Owner decision D-B rebuilt the option sets so **every distractor is a real answer the same subject gave in one of their other interviews**.

**It did not work. The zero-information arm still solves every item.**

    candidate items built                     10  (of 17 round-1 Q-A items)
    pre-gate zero-info argmax accuracy      1.00  (8 of 8 parsed)
                                            1.00  (10 of 10 including 2 recovered)
    mean probability mass on the true option 0.94
    per-item margin, range                 +0.80 .. +1.00
    items rejected by the build-time gate      8  (10 on the honest reading)
    items surviving into a final set           0

Not one close call. The smallest margin between the true option and its best rival was +0.80.

**On the "8 of 8" versus "10 of 10" reading.** Two of the ten gate replies were recorded as parse failures. Neither was a refusal: in both, the model printed its distribution twice — once as four lines, once as one line — so the stated mass is ~2.0 and D8's renormalise window `[0.8, 1.2]` discards it. Both recovered replies were argmax-**correct** (`B: 0.70` and `C: 0.80`). The frozen parser's verdict is what the gate decision used and the parser has not been changed; but the honest instrument-difficulty number is **10 of 10**. Section 7 documents the artifact, including that it also hit round 1.

**This is still a distractor result, not a twin result.** Phase 2 (the ten prediction sets over gate survivors) was **not run**: the orchestrator's stop condition was "≥5 of 10 rejected", and 8 were. The final item set would have been empty in any case. No twin, imposter or contamination numbers exist for round 2, and none should be quoted.

---

## 2. Two mechanisms, in the model's own words

The completions say plainly what the model is doing, and it is two different things.

### 2.1 Same subject is not the same topic (C02124, C02006)

The pool spans a subject's whole career. Samer Shehata's usable answers run 2001–2013; the test interview is 2014. So the distractors are the same person on entirely different subject matter, and topic still separates them. On `C02124:NPR-12184:2` (margin +1.00):

> "Option A discusses a recording/voice-over regarding the Arab League and Ayman Al-Zawahiri, which is unrelated to the popularity of a field marshal. Option B discusses television shows and popular culture in the Arab world, which is unrelated. Option C discusses Colin Powell, Condoleezza Rice, and Ariel Sharon... **Option D is the only logically consistent answer to the question asked.**"

Same on `C02006:NPR-14829:29` (margin +1.00), where Robert Harris's own pool supplied answers about criminal defence against a question on the Brexit election:

> "Option A discusses a client, a 'booty call', and collecting money (legal/criminal defense context)... **Option C is the only response that is contextually relevant to the host's question about an election.**"

D-B controlled the speaker. It did not control the topic, because these people are interviewed about many different things over a decade.

### 2.2 Responsiveness beats topic control (C00792) — the deeper problem

Frederic Hof's pool is tight: on `C00792:NPR-19884:10` **all four options are Hof on Syria and ISIS policy**. Topic is genuinely controlled. The model still took it at +0.80:

> "Option A directly addresses the 'opportunity' and mentions 'President-elect Trump', which fits the context of a transition period where a change in course would be discussed... **Option A is the most logically consistent response to a question about the *opportunity* to change course.**"

A real answer is *responsive* to the question it was asked. Placed among real answers to **other** questions, it is the only one that fits the question shown — identifiable without knowing anything about the person. This is intrinsic to the shape "forced choice among verbatim real answers", not to where the distractors are sourced. It is why no further distractor-sourcing redesign is likely to help.

---

## 3. Diagnostic decomposition (DIAGNOSTIC ONLY — not arms, not bars)

Two diagnostics, authorised after the gate, run in one job on the same 10 candidate items. Neither is a SPEC D8 arm; neither may appear in a fidelity table. SPEC v1.8 D6-v2.9. Implementation `src/doppler/diagnostics_v2.py`; the frozen D8 templates are untouched and the frozen parser reads all three conditions.

- **A — entity-stripped** (`gate_stripped`): the frozen `zeroinfo_redacted` template called with A4.2's entity-stripped option texts. No new template at all. Asks: how much rides on dated names and numbers?
- **B — question-blind** (`gate_qblind`): zero-information, standard option texts, **host question removed**. Asks: how much rides on the answer being responsive to the question shown?

`effective` counts recover the doubled-distribution replies (section 7); chance is 0.25.

| condition | question | options | eff. n | argmax accuracy | mean p(true) | mean margin |
|---|---|---|---|---|---|---|
| **baseline** (phase-1 gate) | shown | standard | 10 | **1.00** | 0.94 | +0.91 |
| **A** entity-stripped | shown | entity-stripped | 10 | **1.00** | 0.87 | +0.82 |
| **B** question-blind | **removed** | standard | 10 | **0.10** | 0.24 | −0.12 |

**Read this as: the entire solve is carried by responsiveness to the question. Named entities carry none of it.**

- Stripping every name, number and date changed argmax accuracy by **nothing** — 10 of 10 both ways, all ten still correct, mean margin only 0.09 lower. The chronological tell (section 8) is real but is *not* what the model is using.
- Removing the question collapses it from 1.00 to **0.10**, below the 0.25 chance line, with the mean margin going negative. Five of ten question-blind replies also hedge into the doubled-line artifact at p(true) 0.15–0.30, i.e. the model stops committing. Its reasoning turns to guessing the venue rather than the answer: *"Option D specifically mentions 'President Obama' and 'Iraq 2003', which are quintessential topics for American news analysis during the mid-2010s."* — and that guess is wrong 9 times in 10.

Round-2 item counts are 10; treat every figure here as a direction, not an effect size.

---

## 4. Per-subject item yield under same-subject distractors

Pool = D4 extraction over every transcript of the subject except the test cluster and any cluster D2 excluded for sharing the test date. C00292 stays `burned_for_qa` and is excluded from every prediction set, as in round 1.

| subject | source transcripts | pool harvested | anti-leak excluded | dup dropped | pool usable | test items | **built** | unfillable |
|---|---|---|---|---|---|---|---|---|
| C00792 Frederic Hof | 5 | 18 | 11 | 0 | 7 | 5 | **4** | 1 |
| C01677 Matthew Kroenig | 14 | 8 | 4 | 0 | 4 | 1 | **0** | 1 |
| C02006 Robert Harris | 9 | 11 | 6 | 0 | 5 | 3 | **2** | 1 |
| C02013 Robert Sampson | 2 | 3 | 2 | 0 | 1 | 4 | **0** | 4 |
| C02124 Samer Shehata | 27 | 60 | 9 | 0 | 51 | 4 | **4** | 0 |
| **total** | 57 | 100 | **32** | 0 | 68 | 17 | **10** | 7 |

**The anti-leak rule collides with the grounding budget, and that is what starves the set.** A subject's answer pool comes from their other interviews — and the twin arm's 2,000-word D8 grounding block is built from those same interviews. Any candidate quotable from the rendered grounding must be excluded, or the twin arm could string-match a distractor out of its own context. For four of five subjects the budget swallows nearly everything they ever said: 32 of 100 harvested answers were excluded this way. C02013 has 3 harvestable answers in total, 2 of which leak, leaving a pool of 1 and zero items. Only C02124, with roughly four times the budget available, is unaffected. This is the same draw-time problem as round-1 findings 8.7 and 8.11, arriving from a new direction: **cluster count and available material, not span, is the binding constraint.**

**Flag: the pool includes non-substantive transcripts, and that is load-bearing.** SPEC D2 restricts *grounding and test* to substantive transcripts (flag S). The round-2 pool rule is "any interview except the test-interview cluster", which admits non-substantive ones too — they are never rendered, so they cannot leak. Without this widening the yield is **4 items from 1 subject** instead of 10 from 3; C00792 and C02006 would both be at zero. **Risk on record:** the widened material is mostly old CNN panel transcripts, which is exactly where round-1 finding 8.14 (MediaSum misattributing speech to the wrong speaker) is most likely. A misattributed pool answer is not the subject's answer, which silently breaks the one property the same-subject design exists to guarantee. It was not audited here; auditing it needs speaker-level verification on the CNN panel subset.

---

## 5. Similarity-floor sweep

Every distractor's question-similarity is recorded so a floor can be frozen later. The build applied floor 0.00. Yardstick: one `TfidfVectorizer` (word 1–2 grams, lowercase) fitted once on all dev pool questions plus all test questions — 85 questions, 4,175 vocabulary terms, corpus sha256 `049fe5f2…d838b7`. One shared yardstick, so the rows are comparable across subjects.

| floor | C00792 | C01677 | C02006 | C02013 | C02124 | **TOTAL** |
|---|---|---|---|---|---|---|
| 0.00 | 4 | 0 | 2 | 0 | 4 | **10** |
| 0.02 | 4 | 0 | 0 | 0 | 4 | 8 |
| 0.05 | 1 | 0 | 0 | 0 | 2 | 3 |
| 0.10 | 0 | 0 | 0 | 0 | 0 | **0** |
| 0.15 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0.20 | 0 | 0 | 0 | 0 | 0 | 0 |

The 30 selected distractors span cosine 0.007–0.147, median 0.036. **A floor of 0.10 or above admits nothing at this subject scale.** Note that low cosine no longer means "unrelated topic" the way it did in round 1 — speaker and domain are now controlled by construction, so the number measures only how differently the two questions are worded.

---

## 6. Five items, verbatim, with their gate margins

Straight from the committed artifacts. The correct option is marked; the model never sees the marking, and the positions were shuffled with a seed derived from the item id.

### `C00792:NPR-19884:10`

Relaxation rung 2 · answer-pool size 7 · gate margin **+0.80**, p(true) 0.85 — REJECTED

**QUESTION**

> Is there an opportunity to change course in Syria because of that?

**A.** **TRUE ANSWER** — source `NPR-19884` turn 10, 89 words, density 0.135

> There is an opportunity. To the extent President-elect Trump has said anything at all about this issue - he said during the campaign that there was a real opportunity for the United States to support Russia and the Assad regime in their battle against ISIS. And I presume that the president-elect probably understands that there is no Russian-Assad regime battle against ISIS, that the tactics being used by Russia and Assad against civilian populations are in fact a wonderful recruiting tool, a gift that keeps on giving for ISIS.

**B.** distractor — source `CNN-267783` turn 25, 98 words, density 0.092, question-similarity 0.044

> The President of the United States has committed the country to a military course aimed at degrading and ultimately defeating ISIS. Even if he does not look at civilian protection in Syria through a humanitarian lens he should be looking at it through a warfighting lens because every barrel bomb, every starvation siege is a gift to ISIS. It's a recruiting gift. If you add, on top of that, the effect all of this is having on allies in the neighborhood and now in Western Europe, the case is clear. He needs to look at some real options.

**C.** distractor — source `CNN-267783` turn 10, 106 words, density 0.066, question-similarity 0.070

> I think there's going to be a debate sometime in November. I think what has probably concentrated the attention of the British more than anything else on this issue is this phenomenon of tens of thousands of people now voting with their feet, heading to Western Europe and the United Kingdom, if possible. These are people who have finally come to the conclusion that Syria is hopeless, that it's a place where it's very difficult to raise a family, hold a job, have any kind of respectable living. So I think this has piqued interest in this country, perhaps to an extent that it hasn't before.

**D.** distractor — source `CNN-267783` turn 23, 76 words, density 0.092, question-similarity 0.147

> Well, the president referred, however, to strengthening our alliances. He referred to the reputation of the United States. The United States is at the head of an alliance in which many of our allies are now being touched directly by this problem. So if the humanitarian imperative were not enough, certainly upholding and strengthening our alliances dictates that the United States take another look at steps that could be taken to at least mitigate this problem.


### `C00792:NPR-19884:6`

Relaxation rung 1 · answer-pool size 7 · frozen parser: PARSE FAILURE (doubled distribution). Recovered: argmax CORRECT, p(true) 0.70 — held out

**QUESTION**

> To what extent is what is unfolding in Syria right now an American responsibility for lack of things the U.S. didn't do?

**A.** distractor — source `CNN-267783` turn 39, 45 words, density 0.133, question-similarity 0.014

> I think Iran and Russia have seized the advantage here. I think it's perfectly understandable that President Obama's instincts would be to try to hold all of this at arm's length. The president, I believe, is strongly influenced by what went wrong in Iraq 2003.

**B.** **TRUE ANSWER** — source `NPR-19884` turn 6, 60 words, density 0.100

> You know, this is not an American responsibility. I would say that the failure of the United States to take any steps at all - this has certainly aggravated the problem, and its given the Russians, the Assad regime and Iran the sense that they have a - have an absolutely free ride to do anything they want to civilians.

**C.** distractor — source `CNN-267783` turn 30, 47 words, density 0.085, question-similarity 0.051

> Yes, I think we have to keep in mind that, at least on two occasions I know of, the United States has put boots on the ground inside Syria to engage ISIS targets. One in particular over a year ago was an attempt to rescue two journalists.

**D.** distractor — source `CNN-267783` turn 23, 76 words, density 0.092, question-similarity 0.061

> Well, the president referred, however, to strengthening our alliances. He referred to the reputation of the United States. The United States is at the head of an alliance in which many of our allies are now being touched directly by this problem. So if the humanitarian imperative were not enough, certainly upholding and strengthening our alliances dictates that the United States take another look at steps that could be taken to at least mitigate this problem.


### `C02124:NPR-12184:2`

Relaxation rung 2 · answer-pool size 51 · gate margin **+1.00**, p(true) 1.00 — REJECTED

**QUESTION**

> Why is a field marshal, according to various surveys, so popular in Egypt?

**A.** distractor — source `CNN-52565` turn 15, 71 words, density 0.085, question-similarity 0.022

> Well it's not clear, actually, who made the reference to the Arab League meeting. In the segments that I've heard, it wasn't Ayman Al-Zawahiri and so on. It might have been a superimposed voice, as it were over that picture. And then if that was the case, we don't know whether the actual filming, the taping of this segment, did take place close enough to the Arab League meeting or not.

**B.** distractor — source `CNN-43473` turn 29, 65 words, density 0.169, question-similarity 0.012

> Right. Well, there's a whole range of films and television cereals that are seen everywhere from Morocco to Indonesia. And it ranges from Dallas and Dynasty and things like "The Bold and the Beautiful," which I had never heard of before until seeing it in Egypt, to "Xena, Warrior Princess and friends." So much of the popular culture that's produced for locally is consumed overseas.

**C.** distractor — source `CNN-72659` turn 6, 88 words, density 0.159, question-similarity 0.033

> Well, I think Colin Powell's visit is certainly good, but I think you're right to point out that it's not enough. There will need to be exerted and continual pressure from the White House from Condoleeza Rice, as well as President Bush himself, a kind of sustained effort and concentration on a daily basis. And also, putting equal pressure on Ariel Sharon, as well as the pressure on the Palestinians, because we've seen quite a bit of pressure on the Palestinians, but not enough pressure on Ariel Sharon.

**D.** **TRUE ANSWER** — source `NPR-12184` turn 2, 69 words, density 0.072

> He's popular for a number of reasons. One, there were many people, of course, who were opposed to the Muslim Brotherhood and Mr. Morsi before he became president. And of course it was a disastrous year in office. And there are many people who, as a result of all of that, are longing for stability and security. And the idea of a military general running the show is reassuring.


### `C02124:NPR-12184:6`

Relaxation rung 0 · answer-pool size 51 · gate margin **+1.00**, p(true) 1.00 — REJECTED

**QUESTION**

> In the end, how much would any Egyptian government would be concerned with the American reaction to their rule?

**A.** distractor — source `CNN-86690` turn 26, 116 words, density 0.129, question-similarity 0.068

> Well, there's -- it's more than likely that some of them are certainly going to be on the ballots. But, again, right now as the interim government, the individuals there are really representing themselves, they're not representing their political parties, but in the January 2005 elections, if, for example, Mr. Iyad Allawi wants to run, he's going to run as a member of his organization, the Iraqi National Accord. And then we're going see other groups like the Dowia Party and the Extreme Council for Islamic Revolution in Iraq also have platforms and run for positions in the legislative body. So, we're going to see a lot more political parties and a lot more organized politics.

**B.** distractor — source `CNN-52091` turn 14, 100 words, density 0.220, question-similarity 0.073

> Right. That was another proposition that the Arab League passed. That is, they're going to send a mission to the United Nations to ask the United Nations Security Council under Chapter 7 of the U.N. charter to force Israel to comply with the U.N. Security Charter that was passed several days ago with the United States support, calling for an immediate withdrawal. And part of Chapter 7 allows the United Nations to use either economic sanctions or military force to get a country to comply, similar to what happened with Iraq. So that's another aspect of the Arab League communique.

**C.** **TRUE ANSWER** — source `NPR-12184` turn 6, 125 words, density 0.176

> Obviously, the military as an institution receives a great deal of aid from the United States, $1.3 billion a year, and of course being on the good standing with the United States provides all kinds of other benefits. If you're dealing with the IMF for a loan or whatever it might be. At the same time, in some ways the United States needs Egypt more than Egypt needs the United States, and that explains why the present administration has been relatively silent on the abuses that we've seen. They need Egypt because of the maintenance of the Camp David Peace Treaty, because of the importance of the Suez Canal, because of the unlimited overflight rights that Egypt grants the United States military and so on.

**D.** distractor — source `NPR-10775` turn 14, 142 words, density 0.099, question-similarity 0.054

> We haven't gotten that far yet, and, in fact, it seems like - that the Supreme Council of the Armed Forces, the military men running the show, are actually themselves, in the next few days, going to appoint a 100-person committee, which they believe will reflect the diversity and heterogeneity of Egypt. Because that was, of course, one of the problems with the two previous committees that the parliament chose. The parliament is dominated by Islamists. Secular, liberal and other forces accused them of stacking the committee in their favor and - to the detriment of liberals - Coptic Christians, women and so on. So I think the Supreme Council of the Armed Forces is likely to appoint a 100-person committee, which then again, of course, that also lacks some legitimacy - I think rightfully so - in the eyes of many.


### `C02006:NPR-14829:29`

Relaxation rung 3 · answer-pool size 5 · gate margin **+1.00**, p(true) 1.00 — REJECTED

**QUESTION**

> Oh. So maybe from your perspective, this could actually turn out to be - this election result could turn out to be good, better, less bad?

**A.** distractor — source `CNN-220639` turn 44, 62 words, density 0.032, question-similarity 0.015

> Well, Nancy, it`s a pleasure to be here. I`m happy to be on your show. I don`t know what my client was thinking at the time, but what I can tell you is this. I have information that leads me to believe he wasn`t there for a booty call, as you suggested, that he was there to collect some money from someone.

**B.** distractor — source `CNN-60867` turn 16, 96 words, density 0.000, question-similarity 0.021

> Well, you know, what she did is a horrible thing, obviously. But I think it's made even more horrible or blown really to a greater scale because of the fact that it was caught on tape and then shown throughout the country. In the scheme of things, what she did in this particular case, is less horrendous than many of the cases that I see. I see cases involving sex abuse and physical abuse where the parents are never prosecuted, it never even comes up as a question. There's never even a charge or an arrest.

**C.** **TRUE ANSWER** — source `NPR-14829` turn 29, 78 words, density 0.013

> It's possible. It's certainly possible because certain realities are now going to start to bite. We've lived in a kind of twilight period - a phony war that's gone on for a year with not much happening. But in 10 days, the negotiations begin in earnest. And at that point, I think a lot of people are going to start wondering whether we're on the right path. And this election result would legitimize a different approach, I think.

**D.** distractor — source `CNN-220639` turn 59, 41 words, density 0.000, question-similarity 0.089

> Nancy, I don`t know the specifics of that. Obviously, witness statements can be wrong. I think people are going off of the booking report from the police point of view. It`s one-sided. We`ll have our side to say in court but...


---

## 7. The doubled-distribution parse artifact (measurement issue, both rounds)

D8's parser renormalises only when the stated probability mass lands in `[0.8, 1.2]`. Gemma-4 sometimes prints the **same** distribution twice — once as four lines, once as one — so the stated mass is ~2.0 and a clearly-answered item is recorded as a parse failure.

Measured across both rounds:

| run | set | prompts | parse failures | recoverable | recovered argmax correct |
|---|---|---|---|---|---|
| round 2 | gate (standard) | 10 | 2 | 2 | **2** |
| round 2 | diagnostic A (stripped) | 10 | 0 | — | — |
| round 2 | diagnostic B (question-blind) | 10 | 5 | 5 | 0 |
| round 1 | all 10 prediction sets | 170 | 2 | 2 | **2** |

Round 1's two, checked against its stored raw completions, are the **identical artifact**:

| set | item | frozen verdict | recovered | correct? |
|---|---|---|---|---|
| `pred_imposter_redacted_stripped` idx 0 | C00792:NPR-19884:2 | `None` | [0.10, **0.85**, 0.02, 0.03] | yes |
| `pred_twin_named_stripped` idx 4 | C00792:NPR-19884:15 | `None` | [0.05, 0.05, **0.85**, 0.05] | yes |

So the artifact has been quietly deflating `N` in both rounds, and in all four prediction-side instances the discarded reply was argmax-correct. In diagnostic B it behaves differently and more informatively: all five failures are the model *hedging* (p(true) 0.15–0.30, none correct), so there the artifact co-occurs with genuine uncertainty rather than masking a confident answer.

**The parser has not been changed.** `relaxed_reread` re-reads only the last distribution line and its output is recorded as an explicitly-labelled `parse_failure_diagnostic`, never as a score. Widening the parser (for example, "take the last distribution line") changes `N` in every arm of every table in both rounds, so it is a **bar-lock decision**, not the implementer's. Recorded as SPEC v1.8 D6-v2.10.

---

## 8. Distractors that post-date the test interview (rule needed)

Two of C02006's 30 distractors come from `CNN-411756` (2020-09-24), which is **after** its test interview (2017-06-09). D2's chronological rule constrains grounding, not the answer pool, and the non-substantive widening (section 4) is what let post-test material in.

Measured across all 30 selected distractors: 28 predate the test, 2 post-date it; mean gap **5.0 years**, range −3.3 to +14.7 years. Because the test cluster is the latest **substantive** cluster by construction, the pool is systematically older, which is a real chronological tell — though diagnostic A shows the model is not currently using it.

Both readings, stated neutrally for bar-lock:

- **Permissive:** a post-test answer cannot leak the test answer, the twin's grounding is still strictly pre-test, and excluding it costs scarce items from an already-starved pool.
- **Strict:** the option set should contain nothing the subject had not yet said at test time; a forced choice partly composed of the subject's future is not the counterfactual the design describes, and it interacts with H7 (staleness), where the direction of time is the independent variable.

No rule was applied either way in this build; the 2 items are in the candidate set and are flagged here.

---

## 9. Bar-lock numbers

Measured separately on CPU, dev subjects and pool metadata only, zero GPU and zero API cost. Full tables and raw JSON are in **`results/stage2_pilot2/BARLOCK_MEASUREMENTS.md`** and `results/stage2_pilot2/barlock/*.json`; they are not duplicated here. Every value is a **proposal** — nothing is frozen.

| § | item (round-1 finding) | proposed value |
|---|---|---|
| 1 | Fuzzy host threshold (8.3) | Raise D3.2 from 0.60 to **0.65** *and* add the two-part guard; 0.70 rejected (loses the Diplomatic License case) |
| 2 | NER upgrade (8.6) | Adopt spaCy **`en_core_web_sm`** for D5's name side, D5's NUMBER rule unchanged; fallback is the curated 26-entry abbreviation subset |
| 3 | Nickname rule (8.2) | Adopt the **`nicknames` CSV ∪ existing `NICKNAME_SUPPLEMENT`**, forward direction only, hand table retained as documented override |
| 4 | Q-A eligibility floor (8.7) | Floor of **≥ 3 D4-eligible items** at draw time, one-on-one test interview a preference not a requirement; expected yield 405 of 578 (95% CI 332–463) |
| 5 | Affiliation redaction scope (8.1) | Adopt **S1** (host-intro clause redaction) plus a question-level scrub of second-person role descriptions in the zero-info arms; reject S2 and S3 |
| 6 | H7 staleness feasibility (new) | **H7 is confirmatory-eligible** — see section 10 |

The measurement file also records what could not be measured and why, including that the section-1 census was self-labelled and the section-5 leak detector runs at ~78% precision.

---

## 10. H7 staleness: dev feasibility

Per `BARLOCK_MEASUREMENTS.md` section 6. A subject's staleness "gap" for a grounding cutoff at cluster *k* is (test cluster date − cluster *k* date); bins are `<6m`, `6-12m`, `1-2y`, `2-3y`, `>3y`.

| subject | dated clusters | span | bins it can fill | H7 eligible |
|---|---|---|---|---|
| C00792 Frederic Hof | 3 | 3.9 y | 1 (`>3y`) | no |
| C00292 Bassir Pour | 13 | 4.8 y | 3 | **yes** |
| C02013 Robert Sampson | 3 | 7.2 y | 2 | no |
| C02124 Samer Shehata | 9 | 3.0 y | **4** | **yes** |
| C01677 Matthew Kroenig | 3 | 1.1 y | 2 | no |
| C02006 Robert Harris | 3 | 10.6 y | 2 | no |

**Only 2 of 6 dev subjects are H7-eligible, and the two that are, are the two with many clusters.** C02006 has a 10.6-year span and still fills only 2 bins on 3 clusters: **cluster count is the binding constraint, not span.** C02124 is the shape H7 wants — 8 usable cutoffs from 210 to 1,099 days.

At corpus scale the draft rule (≥ 4 dated clusters spanning ≥ 2 years) qualifies **262 of 578 candidates (45.3%)**, comfortably past the ≥ 80 threshold, so H7 can be confirmatory. The proposal is a **between-subject** design over 4 bins, dropping `<6m`; the stronger within-subject design reaches only 121 candidates at 3 bins and 33 at 4, which is exploratory scale.

Note the tension with section 4: H7 wants many clusters, and many clusters is also what the same-subject distractor pool needs. The two selection criteria point the same way.

---

## 11. Cost

Zero API calls by design. GPU cost billed from `sacct` (elapsed × allocated nodes), never from the in-process wall clock — a Booster node is billed whole from allocation, so a failed attempt costs what a successful one of the same length costs.

| job | slurm | node | state | elapsed | nodes | node-hours |
|---|---|---|---|---|---|---|
| `stage2_pilot2_gate` attempt 1 | 50378388 | lrdn3356 | **FAILED** | 00:03:21 | 1 | 0.0558 |
| `stage2_pilot2_gate` attempt 2 | 50378706 | lrdn2411 | COMPLETED | 00:06:14 | 1 | 0.1039 |
| `stage2_pilot2_diag` | 50379940 | lrdn2688 | COMPLETED | 00:06:13 | 1 | 0.1036 |
| **total** | | | | | | **0.2633** |
| `stage2_pilot2_pred` | — | — | **not submitted** (stop condition) | — | — | 0 |

Attempt 1 died at vLLM engine init: worker rank 2 raised `torch.AcceleratorError: CUDA error: CUDA-capable device(s) is/are busy or unavailable` (`cudaErrorDevicesUnavailable`). A node fault, not a configuration fault — the identical sbatch, model, `tp=4` and `max-model-len` ran clean in round 1 (slurm 50359261) and on the retry. Recorded as a manifest anomaly. **0.0558 node-hours were spent and wasted**, and are billed.

Ledger lines in `results/cost_log.jsonl`: `stage2_pilot2/gate` (0.1597 node-hours, 10 calls) and `stage2_pilot2/diagnostic` (0.1036, 20 calls). Both carry `cost_usd = 0.0` as a measured fact, not as "unknown". Against the 1.5 node-hour authorisation: **0.2633 spent, 1.2367 remaining.**

Round-2 job efficiency is dominated by engine init: 201–206 s of init against 6.0 s and 12.9 s of generation. Any further diagnostic on this item set should be batched into one job for the same reason.

---

## 12. Provenance

Round 2 reuses round 1's frozen upstream read-only and never writes into `results/stage2_pilot/` (asserted by a test). `build_summary.json` records the sha256 of every round-1 artifact consumed — the draw, the imposter pairing, and each subject's split, Q-A items and grounding turns — so both rounds can be proven to share a draw, a split and a set of test interviews.

    contract                         SPEC.md v1.8 (D6-v2)
    dev subjects                     6 (C00292 burned_for_qa, excluded from prediction)
    candidate items                  10
    final items                      0  (no items_final.jsonl exists)
    D8 template sha256               26def409...f652b1  (unchanged from round 1)
    question-blind template sha256   d275f7a7...bcba80  (diagnostic only, separate marker)
    tests                            876 passing, deterministic, no network

Artifacts: `build_summary.json`, `gate_results.json`, `diagnostic_results.json`, `subjects/<cid>/{answer_pool,pool_excluded,candidates,unfillable}.jsonl`, `exports/`, `node/`, `config.json`, `manifest.json`.

---

## 13. Decisions this pilot forces

The instrument decision is the owner's. Stated neutrally, with the evidence for and against each.

**1. Change the counterfactual: distract with answers to the *same* question.** Another person's answer to the same question, or a model-generated alternative answer. *For:* it is the only option that touches mechanism 2.2 — if every option answers the question shown, responsiveness stops being a tell. *Against:* another person's answer to the same question requires two people asked the same question, which the corpus rarely provides; a model-generated alternative makes the wrong options synthetic, which is a materially different claim and needs its own validity argument.

**2. Enforce a similarity floor.** *For:* it is the lever round-1 finding 8.0 named, and it is already implemented and recorded. *Against:* **the sweep in section 5 rules it out at this scale** — a floor of 0.10 admits **zero** items from these pools, and 0.05 admits 3. It cannot be adopted without a much larger per-subject pool, which is the same draw-time constraint as section 4.

**3. Change the task shape away from forced choice over verbatim answers.** *For:* mechanism 2.2 is intrinsic to that shape, so no sourcing rule escapes it. *Against:* it is the largest change, it costs the pre-registered A4 controls their meaning, and it needs a new validity story for whatever replaces it.

**4. Accept the instrument as-is and report the ceiling.** *For:* it is an honest, publishable negative result about forced-choice-over-real-answers as a fidelity instrument. *Against:* it answers nothing about H1.

Two subsidiary decisions are needed whichever way the instrument goes:

- **The parser** (section 7): widen it or leave it. Leaving it deflates `N` in both rounds; widening it changes every table.
- **Post-test-dated distractors** (section 8): permit or forbid.

And one standing constraint, from section 4 and section 10 together: **whatever the instrument becomes, the draw needs subjects with many interview clusters.** Both the same-subject pool and H7 are limited by cluster count, and four of six dev subjects have three clusters.

---

*End of round-2 pilot report. PILOT -- pipeline validation on dev subjects; no research conclusions.*
