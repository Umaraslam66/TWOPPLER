# Stage 2 pilot report — round 3 (generated same-question counterfactuals)

# PILOT -- pipeline validation on dev subjects; no research conclusions.

**PILOT -- pipeline validation on dev subjects; no research conclusions.** Every number below is a pipeline-validation number on the same five Q-A development subjects as rounds 1 and 2. Nothing here answers a pre-registered bar, nothing here is confirmatory, and no result in it should be quoted as a finding about twins. Contract: SPEC.md v1.9 (D6-v3), binding design PREREGISTRATION_AMENDMENT_2.md **B10**. Scoring model leonardo-gemma4-31b-it, temperature 0.0, tp 4, max-model-len 8192. Generator gemini-3.5-flash-lite. 15 model calls, 239 API calls, $0.0999 API, 0.1156 node-hours.

**What is scored (B10.2, binding reframing).** The claim scored is that the twin identifies the person's actual **POSITION** among plausible alternative positions on the same question — **not** that it picks a verbatim transcript answer.

Round 1 is `results/stage2_pilot/PILOT_REPORT.md`. Round 2 is `results/stage2_pilot2/PILOT_REPORT_2.md`. Round 3 changed the option sets from harvested real answers to **written** counterfactuals.

---

## 1. The headline: the third instrument did not fix the ceiling either

Rounds 1 and 2 both put the zero-information arm at 100%. Round 2's decomposition located the mechanism: the true answer was the only option *responsive* to the question shown. B10 fixed responsiveness by construction — every option is now an answer to the same question, written to take a conflicting position.

**It did not work. The zero-information arm still solves every item.**

    D4-eligible test items                    17
    candidate items built                     15   (2 dropped, section 5)
    gate prompts                              15
    replies the frozen parser accepted         3
    PRE-gate zero-info argmax accuracy      1.00   (3 of 3 parsed)
                                            1.00   (15 of 15 incl. 12 recovered)
    mean probability mass on the true option 0.77
    mean margin over the best rival         +0.69
    per-item margin, range           +0.30 .. +0.96
    items the gate rejected                   15   (on the honest reading)
    items that would survive into a final set  0

`pre_gate_zeroinfo_argmax_accuracy` is **the instrument-difficulty number** (B10.7/D6-v3.9). Post-gate zero-info accuracy is ~0 by construction and is not evidence of anything.

**Phase 2 was not run.** The orchestrator's stop condition was "8 or more of 15 argmax-solved"; 15 were. No twin, imposter or contamination number exists for round 3, and none should be quoted. The final item set would have been empty in any case.

**This is a third distractor result, not a twin result.**

---

## 2. What the model is actually using, in its own words

Round 2's tell was responsiveness. That tell is gone — and three new ones replaced it. The completions are explicit.

### 2.1 The generated options do not sound like a person of that type (the big one)

`C02013:NPR-9480:70`, margin **+0.96**, the largest in the set:

> "Options A, B, and C are written in a highly argumentative, polemical style that reads more like an op-ed or a political speech than a natural response from an academic guest on a broadcast news program. They are dismissive and lean heavily into specific political ideologies (e.g., the Giuliani administration, 'tough on crime' rhetoric).
>
> **Option D, however, reflects the typical speaking style of a social science professor in a televised interview**: it is nuanced, acknowledges that evidence is 'mixed', references specific academic studies (the Perry Preschool Project), and provides a multifaceted explanation..."

This is B10.4 failing at its own job. Style neutralization was supposed to make corpus-verbatim style un-markable by passing every option through one identical paraphrase. It does remove *verbal tics*. It does not remove the difference between **a real expert hedging** and **a language model writing advocacy prose**. Asked for a position that "genuinely conflicts", the generator writes a confident thesis; real interviewees qualify, digress, and say "it's mixed".

The paraphrase cannot fix this because the paraphrase is instructed to preserve every substantive claim. The confidence is *in* the claims.

### 2.2 World knowledge, not person knowledge

`C02124:NPR-12184:4`, margin **+0.80**:

> "The context of this interview refers to the period leading up to the 2014 Egyptian presidential election... the prevailing political analysis was that his victory was virtually inevitable... **Option C reflects the actual political reality of that moment**... Options A, B, and D suggest a competitive race or a high likelihood of defeat, which does not align with the historical consensus."

B10.5 requires each distractor to *conflict* with the true position. When the true position is simply **correct about the world**, every conflicting alternative is **wrong about the world**, and a well-informed scorer picks the true one on general knowledge. It never has to model the person at all. This is structural: it applies to every factual question the instrument will ever contain.

### 2.3 Conversational deixis survives the paraphrase

`C00792:NPR-19884:15`, margin **+0.30** — the tightest item in the set:

> "Option C follows the typical rhetorical style of a guest addressing a host (**referring to him as 'Robert'**) and provides a broad strategic assessment common in these interviews."

The paraphrased true answer kept the host's first name from the real transcript. One distractor happened to open "Robert," too, which is why this item is the tightest of the fifteen rather than a walkover — but the cue is a leak of transcript context into an option, and the offline guards do not test for it (they test years, subject-name variants, grounding shingles and copy-of-true).

### 2.4 Framing nuance still separates, even with responsiveness controlled

`C02006:NPR-14829:29`, margin **+0.50**:

> "The host's question asks if the election result could be 'good, better, [or] less bad,' which **invites a nuanced or cautiously optimistic perspective**... Option B and D are purely negative and dismissive. Option C provides a reasoned argument... directly answering the host's specific framing."

All four options answer the question. Only one answers it at the *register the question invited*. B10 controlled responsiveness at the level of topic, not at the level of stance-toward-the-asker.

---

## 3. Polar-question tell (PRE-REGISTERED — and REJECTED)

Frozen in `tell_classification.json` **before** the gate completions were read (slurm 50387477 was still running).

**Hypothesis.** B10.5 forces every distractor to CONFLICT with the true position. On a two-sided question (yes/no, or A-or-B), all three distractors must land on the opposite side, leaving the true option the lone dissenter — so "pick the odd one out" would solve the item without modelling anyone. 7 of 15 items were hand-classified polar on question form, with the reason recorded per item.

| group | n | solved | mean p(true) | mean margin | min margin |
|---|---|---|---|---|---|
| polar | 7 | **7/7** | 0.736 | **+0.633** | +0.45 |
| non-polar | 8 | **8/8** | 0.811 | **+0.740** | +0.30 |

**The hypothesis is rejected.** Both groups are solved completely, and the polar items are solved with *lower* margins than the wh-questions, which is the opposite of the predicted direction. No trace in the set reasons by elimination or odd-one-out. Whatever is carrying the solve, it is not the polarity structure.

Recorded so it is not re-litigated: the contradiction-rule refinement (require position diversity among the three distractors on polar questions) remains a reasonable **bar-lock design item**, but this pilot supplies no evidence that it would help, and it is not a re-run.

## 4. Naming-register tell (PRE-REGISTERED — partly confirmed, in a different form)

**Hypothesis.** The true option names things the way the question named them while distractors reach for alternatives — a question listing "the U.S., Turkey, Saudi Arabia, Qatar" answered truly with "the United States" against distractors saying "Ankara", "Doha", "Riyadh".

**Measured proxy** (capitalised-entity overlap with the question, true minus mean distractor): positive on only **4 of 15** items. As a systematic property of the option sets, the tell is **not** present.

**But the proxy missed the case that prompted the flag.** It is case-sensitive, so "the U.S." in the question does not match "the United States" in the option — exactly the pair in `C00792:NPR-19884:15`. And the trace that *does* cite naming style cites something the proxy never looked at: the host's first name (section 2.3). So the honest reading is: **register does mark the true option, but through conversational deixis and speaker-plausibility, not through entity naming.** The pre-registered measure was aimed at the wrong surface.

Bar-lock design item, unchanged: instruct the generator to match the true answer's naming register relative to the question. Add to it: strip second-person address and host names from every option, or preserve them in all four.

---

## 5. Build yield and guard statistics

Generator **gemini-3.5-flash-lite**, temperature 0.7 generation / 0.0 paraphrase and checks, template digest `adb6fd3b42a5c67c...`. Budgets sized on measurement, not inherited (section 9).

| subject | test items | **built** | dropped | gate-solved |
|---|---|---|---|---|
| C00792 Frederic Hof | 5 | **5** | 0 | 5 |
| C02013 Robert Sampson | 4 | **4** | 0 | 4 |
| C02124 Samer Shehata | 4 | **2** | 2 | 2 |
| C02006 Robert Harris | 3 | **3** | 0 | 3 |
| C01677 Matthew Kroenig | 1 | **1** | 0 | 1 |
| **total** | **17** | **15** | **2** | **15** |

C00292 stays `burned_for_qa` and is excluded from every set, as in rounds 1 and 2.

**Guard chain, all 17 attempted items:**

    position preservation SAME            17 / 17   (0 retries)
    truncated paraphrases                  0
    era violations                         0
    surviving subject-name variants        0
    grounding-quote hits (10-word shingle) 0
    copy-of-true (Jaccard >= 0.8)          0
    contradiction rejections               9        (all AGREE)
    ladder rungs                           rung 0: 9, rung 1: 1, rung 2: 5
    ladder_exceeded                        0

**The two drops are the contradiction check working, not failing.** Both are C02124 (`:2`, `:8`), and in both, 3 of 4 generated options came back AGREE. On "why is the field marshal popular" and "why did the uprising fail", the generator writes *complementary explanations* rather than conflicting positions, and B10.5 correctly refuses them. Per D6-v3.6 an unfillable item is not built.

---

## 6. Five items verbatim, with their gate margins

Full option sets. `p(true)` and `margin` are the zero-information arm's, recovered where the frozen parser rejected the reply (section 7).

### 6.1 `C00792:NPR-19884:15` — rung 0, true = C, p(true) 0.50, margin **+0.30** (tightest)

> **Q.** Which international backer has lost most here - the U.S., Turkey, Saudi Arabia, Qatar? I mean who's the outside player who's lost (unintelligible)?
> **A.** Robert, regarding foreign backers in Syria, Ankara has taken the heaviest hit, especially since President Erdogan failed to remove Assad from power in Damascus.
> **B.** Looking across all foreign participants in Syria, Doha took the hardest blow, with Emir Tamim losing all leverage over the main rebel factions in Idlib.
> **C.** *(true)* Robert, regarding external actors involved in the Syrian crisis, the biggest loser is the United States, and the loss of credibility and reputation has been enormous.
> **D.** Among outside powers meddling in Syria, Riyadh suffered the greatest defeat, watching King Salman's proxy militias crumble completely across the northern provinces last month.

### 6.2 `C02006:NPR-14829:29` — rung 0, true = C, p(true) 0.65, margin **+0.50**

> **Q.** Oh. So maybe from your perspective, this could actually turn out to be - this election result could turn out to be good, better, less bad?
> **A.** I wish I could share that optimism, but I am worried about what comes next. We needed a clear mandate to tackle the NHS crisis and housing, and instead, we got gridlock. Nobody won, and the public is going to pay the price for this indecision over the coming months. We are looking at months of political instability, backroom deals, and a failure to address the daily struggles working families face across the nation right now.
> **B.** I see this as a total disaster from every imaginable angle. We had a chance for steady, predictable governance, and the voters threw it away for no good reason. Now businesses are pausing investments, and foreign partners are completely baffled by our choices. There is nothing good or less bad about a hung parliament. It paralyses our leadership precisely when we need decisive action on the international stage to protect our core national interests.
> **C.** *(true)* It is possible, because certain realities are now going to start to affect us. We have lived in a kind of twilight period, a phony war that has gone on for a year with not much happening. But in 10 days, the negotiations begin in earnest, and at that point, I think a lot of people are going to start wondering whether we are on the right path, and this election result would legitimize a different approach.
> **D.** Not at all, I think it is a catastrophe for the country, we are heading straight into a wall with zero preparation, look at what happened with the currency markets this morning, that is just the tip of the iceberg, instead of stability we have invited pure chaos into the system, and anybody who thinks this outcome brings any sort of positive change is completely delusional about the economic cliff we are now standing on together.

### 6.3 `C02124:NPR-12184:4` — rung 2, true = C, p(true) 0.85, margin **+0.80**

> **Q.** Samer, any doubt in your mind that General Sisi could win the election?
> **A.** I think there is serious doubt about whether he would actually win at the ballot box. While the state media in Cairo tries to project an aura of inevitability, ordinary citizens in places like Tahrir Square are growing deeply fatigued by military rule. When you look at the strong grassroots organizing coming out of the Muslim Brotherhood and other civilian factions, a general stepping into the presidency faces a fierce contest, and victory is far from guaranteed for him.
> **B.** People have good reason to doubt his chances in the election because powerful opposition networks in Alexandria and Giza still remember the harsher days of the Supreme Council of the Armed Forces, and prominent political figures are already organizing a united front to challenge any uniformed candidate so that if he runs, he will face a formidable campaign that could easily defeat him when voters cast their ballots this spring.
> **C.** *(true)* There is no doubt whatsoever. In fact, many of the other potential candidates have already said that if Abdel Fattah el-Sisi declares his candidacy, they are going to withdraw. The real question is what this means for Egyptian democracy. I think the answer is that it does not bode well to have a military general as president in a country that has had military strongmen ruling for 60 years, and I think that is the great tragedy of all of this.
> **D.** I have serious doubts about assuming he is unbeatable because the country faces a severe economic crisis and the Tamarod movement and youth groups are holding any future leader to an incredibly high standard. If Field Marshal el-Sisi runs, he will have to answer for persistent shortages and security failures that frustrate voters daily, and a charismatic civilian alternative could easily galvanize enough public anger to pull off an upset against the military establishment.

### 6.4 `C01677:NPR-8791:77` — rung 2, true = C, p(true) 0.60, margin **+0.45**

> **Q.** With a much shorter timeline?
> **A.** No, the timeline isn't shifting because Tehran is ignoring international pressure entirely and continuing without pause. The International Atomic Energy Agency inspectors just reported that Natanz and Fordow are operating at full capacity. Supreme Leader Ayatollah Ali Khamenei has made it clear that domestic energy independence comes before any diplomatic overtures from Washington. We are looking at a much compressed schedule regardless of what their diplomatic delegation says in Geneva.
> **B.** The schedule is accelerating dramatically because the regime in Tehran has crossed every red line we established regarding weaponization. Prime Minister Benjamin Netanyahu briefed our committee last week about new intelligence showing covert underground workshops near Isfahan. They are aggressively bypassing international monitors and producing medium-enriched material faster than Western intelligence agencies anticipated. Tehran's supreme council has authorized full acceleration, meaning the breakout window is shrinking before our eyes.
> **C.** *(true)* It depends on a shorter timeline, presumably, because the Iranians are doing some things to suggest that they might be willing to slow that timeline. They have threatened to deploy more advanced centrifuges, but they haven't done that yet. They are not enriching above 20 percent yet, and they are converting some of their 20 percent to fuel plates, so it all depends on Iranian behavior and how fast they push the nuclear program.
> **D.** The window is expanding significantly because economic sanctions led by the European Union and the White House are finally biting hard inside Iran. President Hassan Rouhani and his negotiating team understand that continuing down this path will collapse their entire banking sector. Tehran simply cannot afford the domestic unrest that would follow an oil embargo managed by OPEC. Because of this severe financial crunch, they have quietly decided to freeze their advanced enrichment activities for the foreseeable future.

### 6.5 `C02013:NPR-9480:70` — rung 2, true = D, p(true) 0.97, margin **+0.96** (widest)

> **Q.** Well, let me bring that back to you, Robert Sampson, then. You're a professor of social sciences. This is something you've studied. And we're trying to talk about programs that actually work. So do we know that early education works to prevent future violence? Does community involvement? Does something like the caller who's walking around their neighborhood, does that work?
> **A.** I disagree that early childhood schooling or localized citizen patrols have a proven track record of stopping violence, because when researchers study children in programs meant to build non-cognitive skills, the reduction in future arrests disappears once you control for neighborhood demographics and family income. It is unrealistic to believe that teaching a four-year-old conflict resolution or having a resident walk down the street with a clipboard will prevent a teenager from committing a violent crime a decade later. The root causes of violent crime are tied to local drug markets, gang structures, and the breakdown of family units, which are not affected by preschool curricula or neighborhood watch groups. To make urban centers safer, we need to use the strategies from the Giuliani administration in New York City, which focused on order maintenance, rigorous prosecution, and dismantling illicit networks. Spending public funds on early education interventions for crime reduction is an inefficient use of taxpayer dollars that does not improve public safety.
> **B.** Based on the data accumulated over the past few decades, the notion that early schooling or neighborhood patrols reduce crime is not supported by empirical research. When you examine large-scale initiatives like Head Start or municipal safety patrols, the statistical findings consistently demonstrate zero long-term impact on crime rates or violent behavior later in life. We need to be realistic about what social programs can achieve. Pouring millions of dollars into preschool education or neighborhood watch groups in cities like Chicago or Detroit makes people feel proactive, but it does nothing to alter the fundamental economic drivers of criminality. Instead of spending resources on pedagogical schemes or amateur patrols, we should focus almost entirely on expanding police manpower on the streets and increasing prison sentences for repeat offenders through tougher state statutes. Programs that target early childhood or rely on community volunteers do not move the needle on homicides or aggravated assaults. The hard truth is that deterrence and incapacitation are the only proven methods to lower crime, and every other supposed solution is just a distraction from what actually works in law enforcement.
> **C.** Neither early childhood education nor neighborhood patrolling has any proven efficacy in preventing violent crime, and pretending otherwise misleads the public. When you look at longitudinal studies evaluating programs from the Chicago Child-Parent Centers to various municipal block-watch initiatives, the outcomes are overwhelmingly flat regarding future criminal behavior. We must acknowledge that violence stems from immediate environmental stressors and individual choices made in adolescence and adulthood, not from deficits in preschool learning or a lack of neighbors keeping watch out their windows. Investing heavily in early education as an anti-crime strategy is a misplaced priority, because those classrooms are designed for cognitive development, not as crime prevention laboratories. Similarly, untrained citizens walking their streets cannot replace professional law enforcement agencies like the local police department or county sheriff. What actually reduces violence is robust economic opportunity, job creation, and targeted enforcement by trained officers using traditional detective work, not social work experiments. When mayors and federal officials promote these community-based models, they are ignoring decades of criminological data that show prevention efforts at that age and level are largely ineffective.
> **D.** *(true)* Those are good questions to address in a couple of ways. First, kids' expectations and attitudes are crucially important, because if you don't expect to live to age twenty-five or have a job as an adult, an insult today takes on greater significance, which is why much of the violence is rooted in insults and revenge as classic motives, and that remains a problem even with strict gun laws, so we do need a multifaceted approach. On two fronts, the evidence on early intervention is mixed but shows encouraging signs, and there is evidence that early childhood educational intervention, such as the Perry Preschool Project, shows mixed effects on test scores but improves non-cognitive and behavioral outcomes so kids do better in later life, suggesting that more holistic approaches care about a child's development in the broadest sense rather than just test scores, which is encouraging evidence and why I pointed to the second prong of President Obama's approach. On the third point regarding community-level interventions, the evidence is also mixed, but I would note that evidence on policing is zeroing in on the idea that certain policies, particularly hotspot policing that targets particular areas using better data like predictive analytics, are promising and can be done without necessarily locking up more people.

Read 6.5 beside section 2.1. Three confident policy theses and one hedging academic. The hedging one is real.

---

## 7. Parse notes under the frozen parser

**12 of 15 gate replies were parse failures.** Not one was a refusal. Every one is the doubled-distribution artifact already on record as SPEC D6-v2.10: the model prints the same distribution twice, once as four lines and once as one line, so the stated mass is ~2.0 and D8's renormalise window `[0.8, 1.2]` discards it.

    replies received                      15
    accepted by the frozen parser          3
    parse failures                        12
    recoverable via relaxed_reread        12   (100%)
    recovered replies that are argmax-CORRECT 12   (100%)

**The frozen parser was not changed**, and the gate decision used its verdict. `relaxed_reread` output is recorded as `parse_failure_diagnostic` in `gate_results.json`, explicitly labelled DIAGNOSTIC.

The rate is the story. Round 1 hit this on 2 of 170 prediction prompts; round 2 on 2 of 10 gate prompts; round 3 on **12 of 15**. The artifact scales with how much the model writes before answering, and round 3's options are long, argumentative and require more discussion — so it reasons more, and doubles its answer more. Both readings agree here (3/3 and 15/15 are both 1.00), so nothing in this report turns on it. That will not stay true in a run where the two readings disagree.

**Widening the parser is a BAR-LOCK decision, not the implementer's** — it changes N in every arm of every table.

---

## 8. B10.3 generator separation — DECLARED OVERLAP

**The generator `gemini-3.5-flash-lite` is also the Amendment 1 A3 robustness scorer.** Owner cost directive of 2026-07-27 selected the cheapest model. B10.3 provides for exactly this ("if operational constraints ever force the same version, that overlap is reported beside every robustness number it touches"). Declared here and in `build_summary.json`, `config.json` and the gate export manifest:

- **(a) Inert in this pilot.** Round-3 scoring is Gemma-4-31B-it only. No Gemini model scores anything anywhere in round 3, so no model reads its own writing at any point.
- **(b) Live at the confirmatory stage.** Either the generator changes to a different model at bar-lock, or every A3 robustness number computed on this instrument carries the overlap flag beside it. **Bar-lock decision for the owner.**
- **(c) Mitigating symmetry.** B10.4 sends all four options — including the paraphrased true answer — through one byte-identical paraphrase call on this same model. No option is stylistically closer to the generator than any other, so a self-preference effect would have to distinguish text the model wrote from text it only rewrote, not model style from corpus style.

**Generator history** (both switches on owner cost directives, recorded because B10.3 requires the exact version per run):

1. `gemini-3.1-pro-preview` → abandoned on the owner's cost directive after 5 items. Artifacts kept untouched as an audit trail under `genlog_pro_abandoned/` and `items_pro_abandoned/`; they enter no set. All 17 items were regenerated so the sets have one generator and one version string.
2. `gemini-3.5-flash` → superseded before any call was made.
3. `gemini-3.5-flash-lite` → in use.

---

## 9. Token budgets were measured for this generator, not inherited

Pro charges hidden thinking against `max_output_tokens`, so its 16384/16384/8192 were mostly thinking headroom. `doppler.gemini` sends flash-lite no thinking config, and the probe measured `thoughts_token_count == 0` on **all 15 calls** — the budget is visible output and nothing else.

Worst case, `C02013:NPR-9480:70` (318-word answer):

| step | worst measured | truncation floor | frozen budget |
|---|---|---|---|
| generate (4 blocks) | 1,555 tokens, finish STOP, 4/4 blocks | 1,024 → MAX_TOKENS, 4th block 10 words | **8,192** |
| paraphrase | 253 tokens | not truncated even at 512 | **2,048** |
| position / contradiction check | 43 tokens | not truncated even at 128 | **1,024** |

Zero truncated paraphrases in the whole build, which is the budget sizing being confirmed in production rather than assumed.

---

## 10. Detectability sheet (B10.8) — awaiting the owner

`DETECTABILITY_SHEET.md` (20 unmarked entries, zero answer markings) and `DETECTABILITY_KEY.md` are committed. Seed 53; 10 real entries (paraphrased true among three generated distractors) and 10 controls (four generated options, no real answer, correct response `none`).

**Owner hit rate: _____ / 10 real, _____ false positives / 10 controls.** *(to be filled in after the owner completes the sheet; chance on a real entry is 0.25 if a letter is always named)*

Five questions appear twice, once as a real entry and once as a control — unavoidable at 15 built items, since B10.8 asks for 20 entries. Those five control entries were given **entirely fresh option sets** by a second generation pass (49 calls, $0.0150): fresh counterfactuals against the same paraphrased true answer, same guards, same paraphrase step, same contradiction check, then checked against the real entry's own options. Measured overlap: **zero shared option texts across all five pairs.** The pair therefore shares the question and nothing else, there is no option to eliminate on, and all 10 real entries count.

The first draft of the sheet did not do this — it built those controls from the real item's own three distractors plus its spare, leaving three of four options identical and the real answer recoverable by elimination. Recorded because the fix should be auditable.

Given section 2.1, the owner's hit rate is the number most worth having: if a human can also spot the real answer by register, the instrument's problem is not specific to Gemma.

---

## 11. Cost

**GPU (billed from `sacct`, never from the in-process wall clock).**

| job | slurm | state | elapsed | nodes | node-hours |
|---|---|---|---|---|---|
| `stage2_pilot3_gate` | 50387477 | COMPLETED | 00:06:56 | 1 | **0.1156** |
| `stage2_pilot3_pred` | — | **not submitted** (stop condition) | — | — | 0 |
| **total** | | | | | **0.1156** |

Against the orchestrator's 1.2 node-hour cap for round 3: **0.1156 used, 1.0844 unspent.** One attempt, no node faults, no resubmission. The in-process wall clock said 0.0725 — 37% low, because it misses queue-side and engine-teardown time. `sacct` is the truth.

**API.**

| run | model | calls | tokens in | tokens out | cost |
|---|---|---|---|---|---|
| `stage2_pilot3/budget_probe` | gemini-3.5-flash-lite | 15 | 10,940 | 5,702 | $0.0175 |
| `stage2_pilot3/build` | gemini-3.5-flash-lite | 175 | 58,613 | 19,909 | $0.0674 |
| `stage2_pilot3/build_controls` | gemini-3.5-flash-lite | 49 | 13,391 | 4,388 | $0.0150 |
| **flash-lite total** | | **239** | **82,944** | **29,999** | **$0.0999** |
| `stage2_pilot3/build_pro_abandoned` | gemini-3.1-pro-preview | 51 | 13,331 | 3,852 | **null** |
| `stage2_pilot3/gate` | leonardo-gemma4-31b-it | 15 | 8,918 | 3,289 | $0.00 |

Two things about the abandoned Pro line. `cost_usd` is **null because `MODEL_PRICES` has no entry for that model — a missing price, not a zero cost.** Real money was spent. And its 3,852 output tokens are *visible* tokens only: Pro is a thinking model whose hidden thinking is billed but is not reported in `candidates_token_count`, so true billable output was higher by an unrecorded amount. The line is marked `superseded: true` so it is never added to the round-3 build total.

0 retries and 0 rate-limit events across all 239 flash-lite calls.

---

## 12. What this leaves

Three instruments, three ceilings:

| round | where the wrong options came from | zero-info accuracy | mechanism found |
|---|---|---|---|
| 1 | other people's answers | 17/17 | topical coherence |
| 2 | the same subject's other answers | 10/10 | responsiveness to the question |
| 3 | **written counterfactuals to the same question** | **15/15** | speaker plausibility + world knowledge |

Rounds 1 and 2 failed because a real answer is recognisable as *the answer to this question*. Round 3 removes that and fails because a real answer is recognisable as *something a real person of this type would actually say* — and, when the question is factual, as *the option that is true*.

The pattern across three rounds is that four-way forced choice keeps leaking a signal that has nothing to do with knowing the person. Whether a fourth distractor design can close this, or whether the Stage 2 measurement should stop being forced choice, is the orchestrator's and the owner's call, not the implementer's. What this pilot can say concretely:

- **2.1 is the biggest lever and is not a sourcing problem.** The generator writes advocacy; interviewees hedge. Any fix has to change what the generator is asked to produce, not where options come from.
- **2.2 may not be fixable inside forced choice at all.** If the true position is correct about the world, every genuinely conflicting alternative is wrong about the world.
- **2.3 is cheap to fix** — strip host names and second-person address from every option, or keep them in all four.
- **The parse artifact needs a decision before any run whose two readings disagree.**

No confirmatory subject was touched. Rounds 1 and 2 artifacts were not modified.
