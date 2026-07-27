# OE-1 — open-ended dev pilot, measurement report

**PILOT -- open-ended instrument validation on dev subjects; no research conclusions.**

**Directional, not powered.** 17 items over 5 Q–A dev subjects, one of which (C01677) contributes a single item — subject-level readings for it are noise, and that is said here rather than discovered later. No magnitude number in this report is a claim: magnitude bars are set only after these measurements (Amendment 3 C5). Stage 1/dev-subject work is for development and tuning; nothing here answers a pre-registered bar.

- Contract: results/stage2_openended/PILOT_SPEC.md (Amendment 3), lineage results/stage2_pilot4/SPEC_v1.10.md
- Scored claim: The claim scored is that the twin, asked the person's held-out question cold, produces a free-text reply that lands closer to what the person actually said than an imposter twin's reply does -- on embedding similarity (channel 1) and on stance match (channel 2). No forced choice is involved and no option set exists.
- Generated 2026-07-27T16:00:11Z

## 1. Instrument and configuration

| item | value |
|---|---|
| primary scored model | `Gemma-4-31B-it` (vLLM TP=4, max_model_len 8192, seed 0) |
| robustness scored model | `gemini-3.5-flash-lite` (Google AI Studio) |
| generation settings, both | temperature 0.0, max_output_tokens 256, answer cap 150 words |
| instruction tail | byte-identical across all five arms, sha256 `d8758204009e71b482d36fb7133641f3077b7414df87e5a055f3949cb2ef3d3b` |
| judge | `gemini-3.5-flash`, temperature 0.0, **thinking_budget 0**, max_output_tokens 512 |
| rubric | r1 verbatim from PILOT_SPEC section 4, sha256 `85c7c990af522c2c1e41c116617f406a473496b4c5875f293d687ef62bff64d1` |
| judge call order | randomized, seed 20260727; one candidate per call; blind to arm and model; all three texts GUEST-redacted |
| grounding budget | 2000 words, most-recent-first fill, rendered chronologically |
| items | 17 over 5 subjects; 7 factual explanation, 10 subjective |

Embedding candidates, pinned by HF revision (local CPU, never an API model, never a scored model):

| candidate | revision |
|---|---|
| `sentence-transformers/all-mpnet-base-v2` | `e8c3b32edf5434bc2275fc9bab85f82640a19130` |
| `BAAI/bge-large-en-v1.5` | `d4aa6901d3a41ba39fb536a557fa166f842b0e09` |
| `intfloat/e5-large-v2` | `f169b11e22de13617baa190a028a32f3493550b6` |
| `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |

## 2. Generation behaviour, per arm, both models

| model | arm | n | words min/mean/max | >150w | truncation rate | empty | era violations | max tokens_out |
|---|---|---|---|---|---|---|---|---|
| Gemma-4-31B-it | twin_redacted | 17 | 126/134.47/141 | 0 | 0.0 | 0 | 0 | 171 |
| Gemma-4-31B-it | twin_named | 17 | 124/133.59/143 | 0 | 0.0 | 0 | 0 | 174 |
| Gemma-4-31B-it | zeroinfo_redacted | 17 | 71/109.65/130 | 0 | 0.0 | 0 | 0 | 165 |
| Gemma-4-31B-it | zeroinfo_named | 17 | 63/108.29/127 | 0 | 0.0 | 0 | 0 | 155 |
| Gemma-4-31B-it | imposter_redacted | 17 | 124/132.82/143 | 0 | 0.0 | 0 | 0 | 188 |
| gemini-3.5-flash-lite | twin_redacted | 17 | 90/127.06/152 | 1 | 0.0 | 0 | 0 | 177 |
| gemini-3.5-flash-lite | twin_named | 17 | 104/136.35/150 | 0 | 0.0 | 0 | 0 | 182 |
| gemini-3.5-flash-lite | zeroinfo_redacted | 17 | 103/125.53/160 | 1 | 0.0 | 0 | 0 | 182 |
| gemini-3.5-flash-lite | zeroinfo_named | 17 | 94/121.88/150 | 0 | 0.0 | 0 | 1 | 169 |
| gemini-3.5-flash-lite | imposter_redacted | 17 | 76/127.0/155 | 1 | 0.0 | 0 | 0 | 188 |

## 3. C4 core table — per channel × model

Channel 1 is reported on the pinned candidate `sentence-transformers/all-mpnet-base-v2` (selection in section 4). Channel 2 excludes UNCLEAR from the match denominator (C2.3); per-arm UNCLEAR rates are in section 5. Differences are paired per item, own vs imposter on the same item; the CI is a bootstrap over **subjects** (5 clusters), so it is coarse by construction.

| channel | model | own mean | imposter mean | own−imposter (95% CI) | subj own>imp | zeroinfo_red | zeroinfo_named | contamination |
|---|---|---|---|---|---|---|---|---|
| 1 embedding | Gemma-4-31B-it | 0.6497 | 0.5473 | 0.1024 (0.0444, 0.1770) | 5/5 | 0.5772 | 0.5625 | -0.0147 |
| 1 embedding | gemini-3.5-flash-lite | 0.6368 | 0.5708 | 0.0660 (0.0473, 0.1119) | 5/5 | 0.5817 | 0.6477 | 0.0660 |
| 2 stance | Gemma-4-31B-it | 0.8125 | 0.7273 | 0.1818 (0.0000, 0.3333) | 2/3 | 0.7333 | 0.6875 | -0.0458 |
| 2 stance | gemini-3.5-flash-lite | 0.7500 | 0.7143 | 0.1429 (0.0000, 0.2308) | 2/4 | 0.6667 | 0.8750 | 0.2083 |

Paired-item N per row:

- channel 1, Gemma-4-31B-it: 17 items over 5 subjects
- channel 2, Gemma-4-31B-it: 11 items over 3 subjects — an item enters only when BOTH its own and its imposter generation got a non-UNCLEAR label, which is why this N and the subject-cluster count are below channel 1's
- channel 1, gemini-3.5-flash-lite: 17 items over 5 subjects
- channel 2, gemini-3.5-flash-lite: 14 items over 4 subjects — an item enters only when BOTH its own and its imposter generation got a non-UNCLEAR label, which is why this N and the subject-cluster count are below channel 1's

## 4. Channel 1 — all four candidates, and the section-3 selection

Absolute cosine LEVEL is not comparable across these models (each has its own similarity scale), so the selection rule reads the own−imposter SEPARATION, exactly as the spec words it.

| candidate | model | own | imposter | own−imposter (95% CI) | subj own>imp | zeroinfo_red | contamination |
|---|---|---|---|---|---|---|---|
| `all-mpnet-base-v2` | Gemma-4-31B-it | 0.6497 | 0.5473 | 0.1024 (0.0444, 0.1770) | 5/5 | 0.5772 | -0.0147 |
| `all-mpnet-base-v2` | gemini-3.5-flash-lite | 0.6368 | 0.5708 | 0.0660 (0.0473, 0.1119) | 5/5 | 0.5817 | 0.0660 |
| `bge-large-en-v1.5` | Gemma-4-31B-it | 0.8161 | 0.7578 | 0.0582 (0.0528, 0.0660) | 5/5 | 0.7741 | -0.0008 |
| `bge-large-en-v1.5` | gemini-3.5-flash-lite | 0.8045 | 0.7607 | 0.0438 (0.0357, 0.0601) | 5/5 | 0.7710 | 0.0233 |
| `e5-large-v2` | Gemma-4-31B-it | 0.8167 | 0.7926 | 0.0242 (0.0170, 0.0345) | 5/5 | 0.8054 | 0.0001 |
| `e5-large-v2` | gemini-3.5-flash-lite | 0.8146 | 0.8014 | 0.0131 (0.0072, 0.0194) | 5/5 | 0.7995 | 0.0105 |
| `all-MiniLM-L6-v2` | Gemma-4-31B-it | 0.5793 | 0.4533 | 0.1260 (0.0834, 0.1937) | 5/5 | 0.5159 | -0.0292 |
| `all-MiniLM-L6-v2` | gemini-3.5-flash-lite | 0.5410 | 0.4564 | 0.0847 (0.0435, 0.1542) | 5/5 | 0.4954 | 0.0748 |

**Selection rule applied, on the primary model:**

> Score all four on the pilot; pick the candidate with the cleanest own-minus-imposter separation on the primary model; ties break toward the smaller, more standard model. Dev subjects are for tuning, so this selection is legitimate -- it is recorded in the pilot report and the winner is pinned in the addendum.

| rank | candidate | own−imposter on primary | eligible |
|---|---|---|---|
| 1 | `all-MiniLM-L6-v2` | 0.1260 | NO — sanity check only |
| 2 | `all-mpnet-base-v2` | 0.1024 | yes |
| 3 | `bge-large-en-v1.5` | 0.0582 | yes |
| 4 | `e5-large-v2` | 0.0242 | yes |

Excluded: PILOT_SPEC section 3 names all-MiniLM-L6-v2 a sanity check only -- 'never the pinned channel'.

**Candidate the rule selects: `sentence-transformers/all-mpnet-base-v2` (revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`).** Recorded here as the pilot measurement that feeds the addendum; the pin itself happens at bar-lock, after owner review.

### Section-8 diagnostic — does grounding-to-answer similarity alone explain the own-arm score?

Declared risk 1: the own twin's grounding shares the subject's recurring topics and vocabulary with the real answer, and some of that is trivial topic recurrence rather than person signal. The diagnostic is cosine(own-arm grounding text, real answer) per item, reported as a covariate.

| candidate | diagnostic mean | min | max | Pearson r vs own-arm score (primary model) |
|---|---|---|---|---|
| `all-mpnet-base-v2` | 0.4343 | 0.0688 | 0.6301 | 0.738 |
| `bge-large-en-v1.5` | 0.7084 | 0.5165 | 0.8092 | 0.777 |
| `e5-large-v2` | 0.7822 | 0.7362 | 0.8288 | 0.785 |
| `all-MiniLM-L6-v2` | 0.3735 | -0.0460 | 0.6490 | 0.745 |

Caveat on this diagnostic, stated rather than buried: the grounding block is ~2000 words and every candidate encoder has a 512-token window, so the grounding is truncated to its opening excerpts before encoding. The number describes the head of the grounding, not all of it.

## 5. Channel 2 — stance labels, UNCLEAR rates, and B8 divergence

| model | arm | SAME | DIFFERENT | UNCLEAR | match rate (UNCLEAR excluded) | denominator | UNCLEAR rate |
|---|---|---|---|---|---|---|---|
| Gemma-4-31B-it | twin_redacted | 13 | 3 | 1 | 0.8125 | 16 | 0.0588 |
| Gemma-4-31B-it | twin_named | 13 | 3 | 1 | 0.8125 | 16 | 0.0588 |
| Gemma-4-31B-it | zeroinfo_redacted | 11 | 4 | 2 | 0.7333 | 15 | 0.1176 |
| Gemma-4-31B-it | zeroinfo_named | 11 | 5 | 1 | 0.6875 | 16 | 0.0588 |
| Gemma-4-31B-it | imposter_redacted | 8 | 3 | 6 | 0.7273 | 11 | 0.3529 |
| gemini-3.5-flash-lite | twin_redacted | 12 | 4 | 1 | 0.7500 | 16 | 0.0588 |
| gemini-3.5-flash-lite | twin_named | 12 | 4 | 1 | 0.7500 | 16 | 0.0588 |
| gemini-3.5-flash-lite | zeroinfo_redacted | 10 | 5 | 2 | 0.6667 | 15 | 0.1176 |
| gemini-3.5-flash-lite | zeroinfo_named | 14 | 2 | 1 | 0.8750 | 16 | 0.0588 |
| gemini-3.5-flash-lite | imposter_redacted | 10 | 4 | 3 | 0.7143 | 14 | 0.1765 |

**Material between-arm UNCLEAR differences, flagged per C2.3.** Declared risk 2 was UNCLEAR flooding shrinking the judged denominator, and it is present. gemini-3.5-flash-lite: highest is `imposter_redacted` at 0.1765 against `twin_redacted`'s 0.0588 (gap 0.1177, denominator falls to 14 of 17); Gemma-4-31B-it: highest is `imposter_redacted` at 0.3529 against `twin_redacted`'s 0.0588 (gap 0.2941, denominator falls to 11 of 17). This is not cosmetic: an arm that loses more items to UNCLEAR is scored on a different, smaller subset than the arm it is compared with, and the paired contrast in section 3 drops any item where EITHER side is UNCLEAR. It is measured here and reported; the UNCLEAR rule freezes in the addendum, not mid-pilot. Note separately that `twin_named` and `twin_redacted` produce identical label counts on both models (TVD 0.0000) -- on stance, the name line changes nothing.

**B8 — population-level divergence over stance categories.** The real answer carries no stance label of its own, so there is no reference distribution to score an arm against; the divergence that exists to be measured is **between arms**. TVD below is each arm's SAME/DIFFERENT/UNCLEAR distribution against the own-twin arm's.

| model | arm | TVD vs twin_redacted |
|---|---|---|
| Gemma-4-31B-it | twin_named | 0.0000 |
| Gemma-4-31B-it | zeroinfo_redacted | 0.1176 |
| Gemma-4-31B-it | zeroinfo_named | 0.1176 |
| Gemma-4-31B-it | imposter_redacted | 0.2941 |
| gemini-3.5-flash-lite | twin_named | 0.0000 |
| gemini-3.5-flash-lite | zeroinfo_redacted | 0.1176 |
| gemini-3.5-flash-lite | zeroinfo_named | 0.1176 |
| gemini-3.5-flash-lite | imposter_redacted | 0.1176 |

## 6. Contamination meter

`zeroinfo_named − zeroinfo_redacted`, per channel and model — what the name alone buys a model with no excerpts.

| channel | model | zeroinfo_named | zeroinfo_redacted | meter |
|---|---|---|---|---|
| 1 embedding | Gemma-4-31B-it | 0.5625 | 0.5772 | -0.0147 |
| 1 embedding | gemini-3.5-flash-lite | 0.6477 | 0.5817 | 0.0660 |
| 2 stance | gemini-3.5-flash-lite | 0.8750 | 0.6667 | 0.2083 |
| 2 stance | Gemma-4-31B-it | 0.6875 | 0.7333 | -0.0458 |

## 7. Verbatim examples

Five different items, one per Q–A dev subject. Each shows the question, the real held-out answer, and what the own twin and the imposter twin said, with the judge's label for each.

### Example 1 — `C00792:NPR-19884:6` (C00792, subjective, donor `C01316`, Δ 1285 days / bin >3y)

**Question.** To what extent is what is unfolding in Syria right now an American responsibility for lack of things the U.S. didn't do?

**Real answer (60 words).** You know, this is not an American responsibility. I would say that the failure of the United States to take any steps at all - this has certainly aggravated the problem, and its given the Russians, the Assad regime and Iran the sense that they have a - have an absolutely free ride to do anything they want to civilians.

**own twin — Gemma-4-31B-it — judge: SAME** (141 words)

> I think it's important to be clear that the primary responsibility for the catastrophe in Syria lies with the Assad regime. The systematic crimes against humanity—the shelling of populated areas and the use of chemical weapons—are the choices of a regime determined to perpetuate family rule at any cost. However, there is always a debate within the administration about the timing and nature of the U.S. response. We have to acknowledge that a protracted delay carries risks; it can send a message to both our adversaries and our allies about the relationship between American rhetoric and American action. While the U.S. wants to avoid the mistakes of the past and ensure any case for intervention is irrefutable, the humanitarian crisis continues to mount. The question is whether our caution has inadvertently provided the regime more time to terrorize its own people.

*Judge WHY:* The REAL answer states that the U.S. failure to act "has certainly aggravated the problem" by giving adversaries a "free ride," while the CANDIDATE similarly notes that "our caution has inadvertently provided the regime more time to terrorize its own people."

**own twin — gemini-3.5-flash-lite — judge: DIFFERENT** (145 words)

> I think the United States bears a share of responsibility, not because we caused this tragedy—that responsibility rests entirely with the Assad regime—but because we allowed ourselves to believe that this conflict could be contained or that a purely diplomatic process without leverage could somehow succeed. By hesitating to meaningfully shift the military balance on the ground early on, we created a vacuum. That vacuum was readily filled by extremists, and it allowed a humanitarian catastrophe to metastasize into a regional destabilization crisis. When a superpower sets clear red lines and then struggles to enforce them, it doesn't just affect the calculations of adversaries like Iran; it profoundly shakes the confidence of our closest allies around the world who rely on American credibility. So yes, the cost of inaction has been immense, and we are living with the consequences of those missed opportunities every day.

*Judge WHY:* The REAL answer explicitly states "this is not an American responsibility," whereas the CANDIDATE answer directly contradicts this by stating "I think the United States bears a share of responsibility."

**imposter twin — Gemma-4-31B-it — judge: UNCLEAR** (138 words)

> Well, it's a complicated picture. On one hand, the Obama administration has been very clear that it does not want to get bogged down in another Middle Eastern war, and he's done everything he can to keep us out of a direct military commitment. But the problem is that the U.S. has tried to walk a very thin line—providing non-lethal aid while coordinating with allies like Saudi Arabia and Turkey who are providing the lethal weapons. This "containment" strategy is designed to prevent the violence from overflowing into Jordan or Lebanon, but as we've seen, it's a mess. By trying to avoid a full commitment while still wanting Assad gone, we've created a vacuum where the lines are foggy and the weapons often end up in the wrong hands, particularly with groups like al-Qaida. It's a desperate problem.

*Judge WHY:* The REAL answer takes a clear position that "this is not an American responsibility" but that U.S. inaction "has certainly aggravated the problem," whereas the CANDIDATE answer describes the situation as "a complicated picture" and a "desperate problem" without committing to a clear stance on whether or to what extent the situation is ultimately an American responsibility.

**imposter twin — gemini-3.5-flash-lite — judge: SAME** (150 words)

> Well, it's a very complicated question, but I think many people in the region and among the opposition feel that the United States set expectations it couldn't meet. When Washington drew red lines and suggested that regime change was inevitable, it encouraged certain actors to dig in and keep fighting, believing full well that American cavalry was just over the horizon. At the same time, America was deeply reluctant to get militarily involved in another quagmire in the Middle East, especially after Iraq and Afghanistan. So you had this half-in, half-out policy—providing non-lethal aid, coordinating quietly with regional allies like Saudi Arabia and Qatar who were funneling weapons, but refusing to directly intervene. That hesitation created a vacuum. It allowed extremists like al-Qaida elements to grow, and it left millions of Syrians vulnerable to a brutal regime response without providing the means to actually change the balance on the ground.

*Judge WHY:* The REAL answer states that "the failure of the United States to take any steps at all... has certainly aggravated the problem," which aligns with the CANDIDATE answer's claim that "That hesitation created a vacuum... and it left millions of Syrians vulnerable."

**zero-information — Gemma-4-31B-it — judge: DIFFERENT** (116 words)

> It is a significant responsibility. We have to be honest about the fact that the United States has a long history of intervention in the region that often prioritized short-term stability over long-term democratic health. When we talk about the vacuum that allowed extremists to rise, we have to look at the strategic failures and the inconsistent policies of the last two decades. Whether it was the hesitation to act decisively during the early stages of the uprising or the chaotic nature of our withdrawals, the U.S. played a role in shaping the environment where this tragedy could unfold. We cannot simply distance ourselves from the consequences of our own geopolitical footprint in the Middle East.

*Judge WHY:* The REAL answer explicitly states "this is not an American responsibility" (attributing the crisis to other actors while noting U.S. inaction merely aggravated it), whereas the CANDIDATE answer asserts "It is a significant responsibility" for the United States.

**zero-information — gemini-3.5-flash-lite — judge: DIFFERENT** (160 words)

> Look, I think we have to be very careful about assuming that every tragedy in the world is ours to fix or ours to have prevented. For years, we were told that any American intervention would be a quagmire, that we had no business being the world's policeman, and that local actors needed to take responsibility for their own region. When we did try to shape outcomes diplomatically or through limited support, we were criticized for doing too little, and when we used heavy force elsewhere, we were criticized for overreach. The situation in Syria is a tragedy born of a brutal regime and complex regional and sectarian conflicts that defy simple external solutions. To suggest that a different set of American policies would have cleanly resolved a civil war of this magnitude oversimplifies a profoundly difficult reality. Our primary responsibility moving forward must be humanitarian, ensuring aid reaches those who are suffering while protecting our core national security interests.

*Judge WHY:* The REAL answer states "this has certainly aggravated the problem" by giving adversaries "a free ride," whereas the CANDIDATE answer argues that "To suggest that a different set of American policies would have cleanly resolved a civil war of this magnitude oversimplifies a profoundly difficult reality."

### Example 2 — `C01677:NPR-8791:77` (C01677, factual_explanation, donor `C01650`, Δ 342 days / bin 6-12m)

**Question.** With a much shorter timeline?

**Real answer (73 words).** With a shorter timeline, presumably. I mean, the Iranians are doing some things to suggest that they might be willing to slow that timeline. They've threatened that they're going to deploy these more advanced centrifuges, but they haven't done that yet. They're not enriching above 20 percent yet. They're converting some of their 20 percent to fuel plates. So it all depends on Iranian behavior and how fast they push the nuclear program.

**own twin — Gemma-4-31B-it — judge: UNCLEAR** (132 words)

> That is exactly the problem. When the timeline shrinks, the risk of a miscalculation increases exponentially. As I've mentioned before, while Iran is generally pragmatic and not suicidal, a nuclear-armed Iran would be far more likely to risk a crisis with Israel or the United States. If the window for diplomacy closes and we're forced into a choice between containment and a military strike, we're dealing with very bad options. A strike might set the program back—similar to what happened in Syria in 2007—but it's a gamble. If we don't have a meaningful, intrusive agreement that curbs their enrichment and stockpiles, we're essentially just watching the clock run out. The danger is that the shorter the timeline, the more likely we are to move from a managed tension to an actual escalation.

*Judge WHY:* The REAL answer takes no definitive position on whether the timeline is actually shorter, stating "it all depends on Iranian behavior," while the CANDIDATE answer bypasses the question of the timeline's actual length to discuss the consequences of a shrinking timeline, noting "the shorter the timeline, the more likely we are to move from a managed tension to an actual escalation."

**own twin — gemini-3.5-flash-lite — judge: UNCLEAR** (90 words)

> That is precisely the danger. If we are looking at a compressed timeline for Iran to reach a breakout capability, the diplomatic window narrows significantly, and the pressure on policymakers to make a binary choice between containment and a military strike becomes much more acute. With a shorter timeline, even an interim agreement that buys a few months might not be enough to prevent them from crossing the threshold. That is why the urgency is so high right now, and why everyone is watching these negotiations with such profound anxiety.

*Judge WHY:* The REAL answer states that the timeline "depends on Iranian behavior and how fast they push the nuclear program," whereas the CANDIDATE answer does not take a position on whether the timeline is actually shorter, instead discussing the hypothetical consequences "if we are looking at a compressed timeline."

**imposter twin — Gemma-4-31B-it — judge: UNCLEAR** (127 words)

> That is the great risk. When you have a compressed timeline, you often find that the pressure to produce a result overrides the actual willingness of the parties to make the necessary concessions. We've seen this pattern before. If you rush a process when the domestic political costs for leaders like Netanyahu or Abbas are too high, you don't get a sustainable peace; you get a fragile agreement that collapses at the first sign of trouble, or worse, a failure that further empowers the hardliners on both sides. The reality is that diplomacy moves at the pace of the parties' readiness, not at the pace of a calendar. If the political will isn't there, a shorter timeline only increases the likelihood of a public and costly failure.

*Judge WHY:* The REAL answer discusses Iran's nuclear enrichment timeline ("it all depends on Iranian behavior and how fast they push the nuclear program"), whereas the CANDIDATE answer addresses a completely different topic regarding Israeli-Palestinian peace negotiations ("leaders like Netanyahu or Abbas").

**imposter twin — gemini-3.5-flash-lite — judge: UNCLEAR** (76 words)

> Well, exactly. When you look at the constraints under which both sides are operating, the window for meaningful diplomatic engagement is narrow, and if we don't seize the moment when the dust settles from this round of conflict, we'll simply find ourselves right back where we started. The parties themselves will eventually have to realize that the status quo is unsustainable, but until they reach that conclusion, any external effort is bound to face immense headwinds.

*Judge WHY:* The REAL answer takes a position on the timeline of Iran's nuclear program, stating "it all depends on Iranian behavior and how fast they push the nuclear program," whereas the CANDIDATE answer addresses a different issue, focusing on the "window for meaningful diplomatic engagement" in a conflict.

### Example 3 — `C02006:NPR-14829:29` (C02006, subjective, donor `C02510`, Δ 352 days / bin 6-12m)

**Question.** Oh. So maybe from your perspective, this could actually turn out to be - this election result could turn out to be good, better, less bad?

**Real answer (78 words).** It's possible. It's certainly possible because certain realities are now going to start to bite. We've lived in a kind of twilight period - a phony war that's gone on for a year with not much happening. But in 10 days, the negotiations begin in earnest. And at that point, I think a lot of people are going to start wondering whether we're on the right path. And this election result would legitimize a different approach, I think.

**own twin — Gemma-4-31B-it — judge: DIFFERENT** (139 words)

> I think it is very difficult to see how this could be viewed as a positive. When you see a society succumb to the rhetoric of demagogues, when you see the disparaging of expertise and a turning away from the complexities of the modern world in favor of simple, angry slogans, it is rarely a recipe for success. We are seeing a pattern, both here and across the Atlantic, where people feel abandoned by the system and react with an emotional spasm. But the problems of globalization, the insecurity of the working class—these things aren't solved by isolation or by tearing down the institutions we've built. If anything, I fear we are simply repeating the mistakes of the past, surrendering our stability for a promise that cannot be kept. I suspect we shall pay a heavy price for this.

*Judge WHY:* The REAL answer suggests the election result could "turn out to be good, better, less bad" because "this election result would legitimize a different approach," whereas the CANDIDATE answer states "it is very difficult to see how this could be viewed as a positive" and warns "we shall pay a heavy price for this."

**own twin — gemini-3.5-flash-lite — judge: DIFFERENT** (135 words)

> Well, I suppose one can always search for a silver lining, but I must confess I find it difficult to be optimistic about a leap into the unknown. When you have an electorate driven by an emotional spasm, fueled by anti-immigrant rhetoric and a deep, legitimate anger at the inequalities of globalization, cutting ties with your closest neighbors rarely solves the underlying malaise. It tends to make things worse. We have chosen to use a complex international institution as a convenient whipping boy, and my fear is that the economic and diplomatic price we will pay for this decision will be heavy indeed. History teaches us that nations at their zenith often start looking for ways to dismantle their own achievements, and I worry we have just taken a very significant step down that path.

*Judge WHY:* The REAL answer suggests "this election result would legitimize a different approach" that could turn out "better," whereas the CANDIDATE answer rejects this optimism, stating "my fear is that the economic and diplomatic price we will pay for this decision will be heavy indeed."

**imposter twin — Gemma-4-31B-it — judge: UNCLEAR** (133 words)

> Well, you know, it's a complicated thing. I think we have to look at it through the lens of our rights. As a black man in America, I've always believed that in order to truly be in America, you have to protect everybody's rights—even the people you hate, even the "bad guys." Because if we start deciding who gets to have a voice and who doesn't based on how much we dislike them, then the next thing I know, I won't be able to march either. So, whether a result is "good" or "bad" often depends on whether the fundamental rules of the game are still being followed. It's about who we are as a people and whether we can protect the rights of all, even when it's terribly uncomfortable to do so.

*Judge WHY:* The REAL answer commits to the position that the election result could turn out to be "good, better, less bad" because "this election result would legitimize a different approach," whereas the CANDIDATE answer addresses a completely different context regarding civil rights in America, stating "whether a result is 'good' or 'bad' often depends on whether the fundamental rules of the game are still being followed."

**imposter twin — gemini-3.5-flash-lite — judge: UNCLEAR** (128 words)

> Well, you know, things happen in politics and in life that force us to look at ourselves, to see who we really are as a people. Poor people, working people, folks who get pushed to the margins—we've always had to survive under hard conditions, and we do it by telling our stories, by keeping our eyes open, and by protecting whatever rights we've got left. When a shock comes along, it strips away the polite illusions. It makes you realize that nobody is going to hand you your freedom or your future on a silver platter. You have to figure out a way to answer the questions of the moment, to take care of your own, and to keep moving forward, no matter how steep the cliff looks.

*Judge WHY:* The REAL answer commits to the position that the election result could "turn out to be good, better, less bad" because it "would legitimize a different approach," whereas the CANDIDATE answer avoids the central question entirely, offering a generic reflection that "things happen in politics and in life that force us to look at ourselves."

### Example 4 — `C02013:NPR-9480:45` (C02013, subjective, donor `C00690`, Δ 993 days / bin 2-3y)

**Question.** So you heard the president's remarks from Chicago on Friday. What stuck out of that speech for you?

**Real answer (189 words).** Yeah, it seems to me that President Obama was really suggesting a blend of policies at three distinct levels. First, as you noted, a focus on law, particularly gun laws. Secondly, I heard him speak about the need to support children, especially early childhood intervention. A child that drops out is going to be an adolescent who has a greater risk of being involved in crime and violence and many other negative outcomes. And thirdly, focus on communities, really community-level supports. What we know, in Chicago but also in many other cities, is that violence, along with many other social ills such as low birth weight, infant mortality, early dropout from school, truancy and so forth, these tend to be concentrated in specific places. Violence, especially, is highly uneven. As Cheryl noted earlier, it's not the fact that violence is somehow going up everywhere. In fact, violence is, overall, declining. What we're seeing, however, is that certain communities almost get locked into a vicious cycle, where it's very difficult to get out, and the factors related to that, among others, are high concentration of poverty related to racial segregation.

**own twin — Gemma-4-31B-it — judge: SAME** (135 words)

> Well, I think it's important to look at the rhetoric through the lens of the actual data. Often, political speeches lean into these narratives of rising disorder or crisis because that's how the public perceives the world, even when the statistics tell us something entirely different. If the president is focusing on the "brokenness" of certain communities, I would argue we have to be careful not to oversimplify. We know that violence isn't random; it's concentrated in areas of deep poverty and segregation, particularly among young males. If the speech suggests simple solutions or focuses solely on policing, it misses the broader social conditions—the lack of role models and the legacy of the crack epidemic—that actually drive these trends. We need to move past the materialist fallacy and address the structural isolation of these neighborhoods.

*Judge WHY:* The REAL answer notes that "violence, along with many other social ills... tend to be concentrated in specific places" driven by "high concentration of poverty related to racial segregation," which matches the CANDIDATE's claim that "violence isn't random; it's concentrated in areas of deep poverty and segregation."

**own twin — gemini-3.5-flash-lite — judge: SAME** (152 words)

> Well, what stood out to me was the president's willingness to address the realities of violence in urban neighborhoods without falling into the usual partisan traps. When he talked about Chicago, he was pointing to something we see across the country: a very specific concentration of violence among young males in economically disadvantaged, segregated communities. We have to be able to talk about these structural issues, the lack of adult supervision, and the legacy of the crack epidemic and high violence rates from the late '80s and early '90s, without people immediately crying foul or accusing anyone of blaming the victims. At the same time, we have to recognize the broader national context—that crime overall has been on a historic downward trend for years, even if public perception lags behind. So it was a nuanced speech that tried to balance those complex social realities with a call for more effective, targeted solutions.

*Judge WHY:* The REAL answer highlights that "violence, overall, declining" is concentrated in "specific places" with "high concentration of poverty related to racial segregation," which matches the CANDIDATE's focus on "a historic downward trend" of crime overall alongside "a very specific concentration of violence" in "economically disadvantaged, segregated communities."

**imposter twin — Gemma-4-31B-it — judge: DIFFERENT** (133 words)

> What stuck out to me is the continued reliance on high-visibility rhetoric and the framing of the situation as a crisis. As I've mentioned before, this is largely a manufactured crisis. When you look at the actual numbers, we aren't seeing the surges that the administration describes; rather, we are seeing a shift in the nature of the flow—more families and humanitarian cases from Central America. The president continues to emphasize barriers and deterrence, but that is a partial response. If the goal is truly to secure the border and maintain fairness, the focus should be on investing in our infrastructure at ports of entry and our decision-making systems. We need more immigration judges and asylum officers to process these cases timely, rather than relying on excessive measures that simply cannot be sustained.

*Judge WHY:* The REAL answer focuses on President Obama's speech about urban violence and gun laws, noting "a blend of policies at three distinct levels" including gun laws, early childhood intervention, and community supports, whereas the CANDIDATE answer addresses border security and immigration, claiming the president's speech relied on "high-visibility rhetoric" to address what is "largely a manufactured crisis" regarding Central American migration.

**imposter twin — gemini-3.5-flash-lite — judge: DIFFERENT** (134 words)

> Well, what stuck out most was the continued focus on painting entire immigrant communities with a broad brush, particularly framing cities like Chicago through a lens of fear and lawlessness rather than recognizing the complexities of urban safety and immigration. It relies heavily on rhetoric that ignores how communities actually function and how local law enforcement works alongside federal authorities. We continue to see this pattern of using high-visibility speeches to generate a sense of crisis, rather than addressing the actual, practical mechanics of our immigration system. If we want real solutions, the focus needs to be on investing in our decision-making systems—like the immigration courts and asylum officers—to ensure we have a process that is both fair and orderly, rather than leaning into divisive narratives that don't reflect the reality on the ground.

*Judge WHY:* The REAL answer focuses on President Obama's speech suggesting "a blend of policies at three distinct levels" (gun laws, early childhood intervention, and community-level supports), whereas the CANDIDATE answer criticizes a "continued focus on painting entire immigrant communities with a broad brush" and addresses immigration system mechanics.

### Example 5 — `C02124:NPR-12184:4` (C02124, subjective, donor `C02277`, Δ 210 days / bin 6-12m)

**Question.** Samer, any doubt in your mind that General Sisi could win the election?

**Real answer (76 words).** No doubt whatsoever. In fact, many of the other potential candidates have already said if Abdel Fattah el-Sisi declares his candidacy they're going to withdraw. The real question is what does it mean for Egyptian democracy? And I think the answer is it doesn't bode well to have a military general as president in a country that has had military strongmen ruling for 60 years. And that's, I think, the great tragedy of all of this.

**own twin — Gemma-4-31B-it — judge: SAME** (137 words)

> Well, in terms of the raw numbers and the current political climate, it seems almost inevitable. General Sisi has managed to position himself as the savior of the state and the answer to the chaos of the Morsi years. However, we have to be careful about how we define "winning" an election. If the process lacks genuine competition, if political dissent is suppressed, and if the military continues to wield this immense, unchecked power behind the scenes, then the result is more about consolidation than it is about a democratic mandate. We've seen this pattern before in Egypt—where the appearance of a legal or electoral process is used to legitimize a holdover or a military figure. So, while he will likely win, the question is whether this represents a democratic choice or simply a return to authoritarianism.

*Judge WHY:* The REAL answer states there is "No doubt whatsoever" that Sisi could win, while the CANDIDATE answer similarly concludes "while he will likely win" and that "it seems almost inevitable."

**own twin — gemini-3.5-flash-lite — judge: SAME** (133 words)

> Well, there is very little doubt that he would win, given the immense popularity he currently enjoys among a large segment of the Egyptian population and the state apparatus behind him. After all the turmoil, fuel shortages, and economic anxiety, many Egyptians are looking for a strong hand to restore stability and order. The real question is not whether he can win, but what kind of political future Egypt is building under his leadership. When you have a context where opposition voices are marginalized, the media largely falls in line, and the military is once again positioned as the ultimate savior of the nation, the path to a genuine, pluralistic democracy becomes extremely narrow. So while his electoral victory might be virtually guaranteed, the long-term health of Egypt's political transition remains deeply uncertain.

*Judge WHY:* The REAL answer states there is "No doubt whatsoever" that Sisi could win, while the CANDIDATE answer similarly asserts "there is very little doubt that he would win".

**imposter twin — Gemma-4-31B-it — judge: SAME** (127 words)

> Well, if we are talking about the likelihood of him winning, there is very little doubt. But the real question is not whether he will win, but under what conditions that victory occurs. We have to look at the environment in which this election is taking place. When you have a security apparatus that has effectively sidelined the opposition and a climate of intimidation, the results are often a foregone conclusion. It is reminiscent of the patterns we see in other parts of the region where the outward form of a democratic process—the ballot box—is maintained, but the actual democratic substance has been hollowed out. Sisi has the backing of the state and the military, and in that kind of configuration, the outcome is rarely in doubt.

*Judge WHY:* The REAL answer states there is "No doubt whatsoever" that Sisi could win, while the CANDIDATE answer similarly asserts "there is very little doubt" and that "the outcome is rarely in doubt."

**imposter twin — gemini-3.5-flash-lite — judge: SAME** (128 words)

> None at all. When you have the backing of the military and the state apparatus, and when the opposition is fractured, weak, or suppressed, the outcome of an election is practically predetermined. General Sisi enjoys immense popularity among a significant portion of the population that is desperate for stability and order, much like what we've seen in other transitional or post-uprising contexts in the region. Combined with the absence of any credible, viable alternative, his victory at the ballot box is essentially a foregone conclusion. The real question isn't whether he will win, but how he will govern once he assumes the presidency and whether he can address the deep economic and social challenges facing the country without sliding entirely back into the authoritarian patterns of the past.

*Judge WHY:* The REAL answer states there is "No doubt whatsoever" that Sisi could win, while the CANDIDATE answer similarly asserts there is "None at all" and that his victory is "essentially a foregone conclusion."

## 8. Carries and anomalies

1. **Era violations.** Generated answers must not reference events after the test interview's date. Counts by model — Gemma-4-31B-it: 0; gemini-3.5-flash-lite: 1. The single flash-lite violation is `C02006:NPR-14829:26` (zeroinfo_named), which mentions "2019". It is flagged, kept in the tables, and named here rather than dropped.
2. **S1 leaves a free-standing intro clause standing, and in one imposter prompt that clause describes the DONOR.** S1 removes the clause attached to GUEST; it does not remove a third party's résumé in the same line, and its pattern misses `GUEST, who ...` when an abbreviation's full stop truncates the clause before the role word. Measured: 1 of 17 `imposter_redacted` prompts (subject C01677, donor C01650) still carries, verbatim, *"GUEST, who served two tours as U.S. ambassador to Israel, now at the Brookings Institution"* and *"GUEST, who used to be U.S. ambassador there, as well as assistant secretary of state for the region and who now directs foreign policy programs at the Brookings Institution"*. No NAME survives — the name guard passes — but that is a donor-identifying résumé sitting in the arm whose entire job is to withhold identity. Separately, twin prompts retain co-panellist résumés (*"Eugene Rivers, a Pentecostal minister, community activist and co-founder of the city's 10-point Coalition, and GUEST, [DESCRIPTION REMOVED]"*), which is a co-occurrence fingerprint on the subject. Both are scope questions for bar-lock, not things to patch mid-pilot.
3. **The zero-information preamble still reads "Predict which answer they gave."** — forced-choice wording carried over from v1.10, kept because PILOT_SPEC section 2 freezes every arm's preamble so the instruction tail stays byte-identical. Measured effect: none visible. All 34 zero-information generations on both models are fluent first-person spoken replies; none names an option, restates the task, or asks which answer to choose.
4. **S1 was not applied by rounds 1–4.** OE-1 applies it to all five arms (so a named arm still differs from its redacted counterpart by exactly one line). OE-1 prompts are therefore not byte-comparable to round 4's on this dimension.
5. **Two of the 17 items have no hand-final type.** `results/stage2_pilot4/item_types.json` covers the 15 items round 3 built; `C02124:NPR-12184:2` and `C02124:NPR-12184:8` fell to the documented cue rule and both landed factual_explanation, so the split reported here is 10 subjective / 7 factual, not the spec's 10 / 5.

## 9. The judge defect, and what was pinned because of it

The first judge pass (v1, `judge/judgements.jsonl`) ran `gemini-3.5-flash` at max_output_tokens 256 with no thinking setting. 82 of 85 replies came back with the `WHY:` line cut mid-phrase while `LABEL:` survived. A two-budget probe (`judge/thinking_budget_probe.json`) found the cause: the model charges hidden thinking against `max_output_tokens` and did not finish thinking at either budget — 243 of 256, then 980 of 1024 tokens went to thoughts, both ending `MAX_TOKENS`. **The label itself moved between the two budgets at temperature 0** (DIFFERENT → UNCLEAR), so the v1 labels were a function of the truncation, not only of the rubric.

Owner decision, taken before any re-run: thinking explicitly disabled (`thinking_budget=0`) and `max_output_tokens=512`, everything else unchanged — same model, temperature 0, rubric r1 verbatim, same blinding, same randomization seed. **Both settings are pinned judge parameters at bar-lock.**

A determinism probe ran first (`judge/determinism_probe_v2.json`): 3 items × 2 runs under the new config, 3/3 identical labels, WHY intact on all 6. Only then did the batches run.

| pass | file | thinking | max out | parse failures | WHY intact |
|---|---|---|---|---|---|
| v1 (defect record, retained) | `judge/judgements.jsonl` | default (on) | 256 | 2 / 85 | 3 / 85 |
| v2 (gemini-3.5-flash-lite) | `judge/judgements_v2.jsonl` | disabled | 512 | 0 / 85 | 85 / 85 |
| gemma (Gemma-4-31B-it) | `judge/judgements_gemma.jsonl` | disabled | 512 | 0 / 85 | 85 / 85 |

v1 and v2 agree on 72 of 85 labels (84.7%) on the same flash-lite generations. v1 is retained as the defect record and is used for nothing else.

## 10. Cost

| run | model | backend | calls | tokens in | tokens out | USD | node-hours |
|---|---|---|---|---|---|---|---|
| `stage2_oe1/gen_flashlite` | gemini-3.5-flash-lite | gemini | 85 | 141217 | 12751 | 0.074242 | — |
| `stage2_oe1/gen_gemma` | leonardo-gemma4-31b-it | leonardo-batch | 85 | 142237 | 12592 | — | 0.10528 |
| `stage2_oe1/judge` | gemini-3.5-flash | gemini | 85 | 89706 | 867 | 0.071182 | — |
| `stage2_oe1/judge_gemma` | gemini-3.5-flash | gemini | 85 | 82650 | 5434 | 0.086441 | — |
| `stage2_oe1/judge_v2` | gemini-3.5-flash | gemini | 85 | 82876 | 5261 | 0.085831 | — |
| **total** | | | | | | **$0.317696** | **0.10528** |

Per-arm breakdown lives in `cost_log.jsonl` under each run's `variant` field. The primary-model generation is billed per whole node (1 node-hour = 4 GPU-hours = 32 core-hours), from `sacct` ElapsedRaw.

## 11. The two pre-written C4 readings, quoted verbatim

From `results/stage2_openended/PILOT_SPEC.md` section 7, written before any of these numbers existed:

- **PASS reading (pre-written):** own > imposter in the pre-registered
  direction on the primary model in BOTH channels → proceed to fill the
  bar-lock addendum's [TO FILL] slots and to the owner's ≥50-label judge
  spot-check (precondition 6).

- **PAUSE reading (pre-written):** direction absent on the primary model,
  or the two channels disagree on direction → **Stage 2 pauses for a
  design review** per C4.3. The report is published as the record, and no
  new instrument is reached for without a new amendment. No spin: a
  pause outcome is a finding about the instrument, reported with the same
  care as a pass.

### The gate inputs, laid beside them

Primary model (`Gemma-4-31B-it`), pinned embedding candidate `sentence-transformers/all-mpnet-base-v2`:

| channel | own | imposter | own−imposter | 95% CI (subject-clustered) | subjects own>imp | paired N |
|---|---|---|---|---|---|---|
| 1 embedding | 0.6497 | 0.5473 | 0.1024 | (0.0444, 0.1770) | 5/5 | 17 |
| 2 stance | 0.8125 | 0.7273 | 0.1818 | (0.0000, 0.3333) | 2/3 | 11 |

Robustness model (`gemini-3.5-flash-lite`) — per Amendment 3 C3 its absolute scores are secondary and only its own-minus-imposter contrast carries robustness weight:

| channel | own−imposter | 95% CI | subjects own>imp | paired N |
|---|---|---|---|---|
| 1 embedding | 0.0660 | (0.0473, 0.1119) | 5/5 | 17 |
| 2 stance | 0.1429 | (0.0000, 0.2308) | 2/4 | 14 |

## C4 verdict — PASS, by the pre-written reading, applied mechanically

Applied 2026-07-27 by the orchestrator against the gate inputs above.

The PASS reading requires own > imposter in the pre-registered direction
on the primary model in BOTH channels. On `Gemma-4-31B-it`: channel 1
**+0.1024** (CI 0.0444–0.1770, 5/5 subjects), channel 2 **+0.1818**
(CI 0.0000–0.3333, 2/3 subjects). Both directions positive. The two
channels agree. **The gate passes.** The robustness model's contrasts
point the same way in both channels (+0.0660, +0.1429), which the gate
does not require but is worth a sentence.

What this does and does not establish, stated with the verdict rather
than buried:

1. **The gate is directional, not powered** (pre-declared in the spec
   header). Channel 2's CI lower bound touches zero and its paired N is
   11 items over 3 subject clusters — because the judge returned UNCLEAR
   on 6/17 imposter answers (0.353) versus 1/17 for the twin (0.059).
   That asymmetry is declared risk 2 arriving and the C2.3 flag firing;
   it is itself an own-vs-imposter difference (the imposter dodges the
   question in its donor's register), but it thins the stance
   denominator, and a confirmatory design must expect it.
2. **Channel 1's separation is partly topical.** The grounding-to-answer
   similarity diagnostic correlates r ≈ +0.74 with the own-arm score on
   the pinned candidate. The design anticipated this: no claim rests on
   channel 1 alone, and the stance channel — which topic overlap cannot
   satisfy by itself — agrees in direction.
3. **Nothing here is a research finding.** Dev subjects, 17 items, no
   frozen bars. The verdict's only pre-registered consequence is
   procedural: per PILOT_SPEC §7 and Amendment 3 C4/C7, Stage 2
   proceeds to filling the bar-lock addendum's [TO FILL] slots and to
   the owner's ≥50-label judge spot-check (addendum precondition 6,
   sheets A/B/C ready). The addendum freezes only after every
   precondition clears and the owner adopts it.

