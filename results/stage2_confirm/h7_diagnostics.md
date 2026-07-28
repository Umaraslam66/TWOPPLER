# H7 diagnostics — EXPLORATORY

**EXPLORATORY THROUGHOUT. Nothing in this note is a bar, a verdict or a claim. It proposes no change to any frozen rule and makes no recommendation. The reported H7 numbers stay where they are, in `results/stage2_confirm/STAGE2_CONFIRM_REPORT.md`.**

Why this note exists. On the primary model the two channels disagree about H7. Channel 1 (embedding cosine) is flat — mean slope +0.00146 per year, p = 0.8650, no pooled crossover anywhere in range. Channel 2 (stance match) has a significantly positive slope — +0.06502 per year, p = 0.0182 — and a pooled crossover at the EARLIEST bin, 6-12m. This note takes that disagreement apart four ways and reports what each angle does and does not account for.

Scope: 36 H7 subjects, 61 subject-by-bin cells, 247 stale-own-twin renders and 142 fresh-imposter renders.

**Cost: $0.00.** CPU only, no API call, no GPU, no network fetch. Every number is recomputed from artifacts already on disk by `experiments/h7_diagnostics.py`.

## 1. Where the UNCLEAR asymmetry sits — EXPLORATORY

The confirmatory report flagged a global UNCLEAR asymmetry: the imposter arm draws far more UNCLEAR labels than the twin arm (0.2958 vs 0.1465 on Gemma, 0.2535 vs 0.1183 on flash-lite, section 6 of that report). The question here is whether that asymmetry piles up in one Δ bin — and in particular whether it sits in the 6-12m bin, which is where channel 2 puts its pooled crossover and where the positive slope starts.

Counting rule, stated so the denominators can be checked: twin rows are counted once per rendered item. Fresh-imposter rows are counted once in every bin their subject filled — the same placement the crossover statistic uses, because the imposter is rendered once per item and reused at every cutoff (rule H7-R7). Rates are therefore comparable within a bin, and the imposter's totals across bins are not independent.

One more thing to hold while reading: the stance-match column here is POOLED OVER ITEMS. The per-bin table in the confirmatory report averages per subject first. The two differ by construction and neither is wrong; this section needs the item-level version because it is about denominators.

### Gemma-4-31B-it — PRIMARY

| Δ bin | arm | SAME | DIFFERENT | UNCLEAR | denominator (SAME+DIFFERENT) | UNCLEAR rate | stance match |
|---|---|---|---|---|---|---|---|
| 6-12m | stale own twin | 25 | 16 | 18 | 41 | 0.3051 | 0.6098 |
| 6-12m | fresh imposter | 16 | 18 | 25 | 34 | 0.4237 | 0.4706 |
| 1-2y | stale own twin | 45 | 20 | 11 | 65 | 0.1447 | 0.6923 |
| 1-2y | fresh imposter | 30 | 26 | 20 | 56 | 0.2632 | 0.5357 |
| 2-3y | stale own twin | 21 | 10 | 7 | 31 | 0.1842 | 0.6774 |
| 2-3y | fresh imposter | 19 | 10 | 9 | 29 | 0.2368 | 0.6552 |
| >3y | stale own twin | 49 | 14 | 11 | 63 | 0.1486 | 0.7778 |
| >3y | fresh imposter | 30 | 21 | 23 | 51 | 0.3108 | 0.5882 |

| Δ bin | imposter UNCLEAR − twin UNCLEAR |
|---|---|
| 6-12m | +0.1186 |
| 1-2y | +0.1184 |
| 2-3y | +0.0526 |
| >3y | +0.1622 |

| arm | UNCLEAR rate, freshest bin (6-12m) | UNCLEAR rate, all other bins pooled | freshest − rest |
|---|---|---|---|
| stale own twin | 0.3051 (n = 59) | 0.1543 (n = 188) | +0.1508 |
| fresh imposter | 0.4237 (n = 59) | 0.2766 (n = 188) | +0.1471 |

### gemini-3.5-flash-lite — ROBUSTNESS

| Δ bin | arm | SAME | DIFFERENT | UNCLEAR | denominator (SAME+DIFFERENT) | UNCLEAR rate | stance match |
|---|---|---|---|---|---|---|---|
| 6-12m | stale own twin | 33 | 14 | 12 | 47 | 0.2034 | 0.7021 |
| 6-12m | fresh imposter | 20 | 17 | 22 | 37 | 0.3729 | 0.5405 |
| 1-2y | stale own twin | 51 | 14 | 11 | 65 | 0.1447 | 0.7846 |
| 1-2y | fresh imposter | 42 | 20 | 14 | 62 | 0.1842 | 0.6774 |
| 2-3y | stale own twin | 24 | 7 | 7 | 31 | 0.1842 | 0.7742 |
| 2-3y | fresh imposter | 19 | 14 | 5 | 33 | 0.1316 | 0.5758 |
| >3y | stale own twin | 41 | 17 | 16 | 58 | 0.2162 | 0.7069 |
| >3y | fresh imposter | 36 | 19 | 19 | 55 | 0.2568 | 0.6545 |

| Δ bin | imposter UNCLEAR − twin UNCLEAR |
|---|---|
| 6-12m | +0.1695 |
| 1-2y | +0.0395 |
| 2-3y | -0.0526 |
| >3y | +0.0405 |

| arm | UNCLEAR rate, freshest bin (6-12m) | UNCLEAR rate, all other bins pooled | freshest − rest |
|---|---|---|---|
| stale own twin | 0.2034 (n = 59) | 0.1809 (n = 188) | +0.0225 |
| fresh imposter | 0.3729 (n = 59) | 0.2021 (n = 188) | +0.1708 |

Source: `experiments/h7_diagnostics.py`, reading `results/stage2_confirm/render_index.jsonl`, `results/stage2_confirm/items_confirm.jsonl` and `results/stage2_confirm/judge/judgements_*.jsonl`.

### Why some channel-2 bin rows print `n/a` for own − fresh imposter

The confirmatory report's channel-2 H7 bin tables show both arm means but print `n/a` in the difference column for 6-12m and >3y on both models. That is not a missing number, it is a deliberate suppression, and the mechanism is worth stating plainly.

`h7_block` in `experiments/stage2_confirm_report.py` computes the difference only when the two arms cover the SAME set of subjects in that bin (the `len(tw) == len(im)` guard). On channel 2 a subject keeps a twin value in a bin as long as one of its items got a SAME/DIFFERENT label, but loses its imposter value in that bin if ALL of that subject's imposter items came back UNCLEAR. The imposter arm draws the most UNCLEAR, so it is the arm that loses subjects — the sets stop matching, and the driver refuses to subtract means computed over different people. Channel 1 never hits this: every render carries a cosine, so no subject drops out.

**Gemma-4-31B-it** — subjects contributing a value in each bin:

| Δ bin | ch1 twin | ch1 imposter | ch1 difference printed | ch2 twin | ch2 imposter | ch2 difference printed |
|---|---|---|---|---|---|---|
| 6-12m | 15 | 15 | yes | 14 | 13 | NO |
| 1-2y | 19 | 19 | yes | 19 | 19 | yes |
| 2-3y | 9 | 9 | yes | 9 | 9 | yes |
| >3y | 18 | 18 | yes | 18 | 17 | NO |

**gemini-3.5-flash-lite** — subjects contributing a value in each bin:

| Δ bin | ch1 twin | ch1 imposter | ch1 difference printed | ch2 twin | ch2 imposter | ch2 difference printed |
|---|---|---|---|---|---|---|
| 6-12m | 15 | 15 | yes | 15 | 14 | NO |
| 1-2y | 19 | 19 | yes | 19 | 19 | yes |
| 2-3y | 9 | 9 | yes | 9 | 9 | yes |
| >3y | 18 | 18 | yes | 18 | 17 | NO |

Worth noticing, and reported rather than acted on: the pooled crossover statistic does NOT apply that guard. It compares the two arm means directly, whatever subject sets produced them. So the channel-2 crossover at 6-12m on the primary model rests on a comparison the same driver declines to print as a difference one column to its left. This note only makes that visible; it proposes no change to the crossover definition, which is frozen.

## 2. Era and topic overlap as a Δ-correlated covariate — EXPLORATORY

The question on record: staleness moves the grounding's ERA as well as its age. Older grounding talks about older topics. If the test interview happens to share more vocabulary and subject matter with some cutoffs than others, and that sharing correlates with Δ, then a stance slope could appear without anything person-level changing. This section measures the covariate and correlates it with Δ. It does not test causation and no causal language is used.

Method, reused from OE-1 (`experiments/stage2_oe1.py`, `cmd_embed`, spec section 8; reported in `results/stage2_openended/OE1_PILOT_REPORT.md`): the similarity between the grounding block and the real test answer, per item. Here the grounding block is the one actually rendered at each cutoff, so the measure varies with Δ. Two readings are given because the embedding one has a known limit:

- **Embedding cosine** — the pinned channel-1 instrument (`sentence-transformers/all-mpnet-base-v2`, revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`, CPU, loaded offline). Its input window is 384 tokens, and a grounding block is around 2,000 words, so this reads the head of the block, not all of it. Same limit OE-1 had.
- **Lexical Jaccard over content words** — truncation-free, reads the whole block, stdlib only. Included precisely because it does not have the window problem.

Coverage: 61 of 61 cells yielded exactly one grounding block, over 247 grounding-to-answer pairs.

**Covariate by Δ bin.** If era were driving the stance curve, this would move with the bins.

| Δ bin | cells | embedding cosine (mean) | lexical Jaccard (mean) |
|---|---|---|---|
| 6-12m | 15 | 0.3802 | 0.0279 |
| 1-2y | 19 | 0.3552 | 0.0312 |
| 2-3y | 9 | 0.3400 | 0.0317 |
| >3y | 18 | 0.3673 | 0.0353 |

**Correlation with Δ.** Across cells (each cell is one subject at one cutoff) and, separately, as a per-subject slope against Δ — the same shape as the H7 slope test, so the two are directly comparable. Read both: cells are not independent, because one subject can fill up to four of them, so an across-cell correlation can be driven entirely by which subjects happen to fill which bins. The per-subject slope has that composition effect removed.

| covariate | across cells n | Pearson r | p | Spearman ρ | p | per-subject slope/year (mean) | p | n subjects |
|---|---|---|---|---|---|---|---|---|
| embedding cosine | 61 | +0.0764 | 0.5583 | +0.0147 | 0.9105 | -0.019183 | 0.3034 | 18 |
| lexical Jaccard | 61 | +0.2725 | 0.0336 | +0.3105 | 0.0149 | -0.000107 | 0.8491 | 18 |

**Does the covariate track the stance slope?** Per-subject covariate slope against per-subject channel-2 stance slope, primary model. If the era covariate were producing the stance slope, these would move together.

| covariate | n subjects | Pearson r | p | Spearman ρ | p |
|---|---|---|---|---|---|
| embedding cosine | 17 | -0.0401 | 0.8786 | -0.2064 | 0.4268 |
| lexical Jaccard | 17 | +0.0237 | 0.9281 | -0.0467 | 0.8588 |

Source: `experiments/h7_diagnostics.py`, reading `results/stage2_confirm/node/chunk_*.prompts.jsonl` (grounding text), `results/stage2_confirm/items_confirm.jsonl` (real answers) and `results/stage2_confirm/report_numbers.json` (channel-2 slopes).

## 3. Stance slope under three UNCLEAR rules — EXPLORATORY

The channel-2 slope is computed after UNCLEAR items are dropped. That is the frozen rule and it stays the reported number everywhere else. This table asks only whether the slope's direction and size depend on that choice. The two variants are exploratory arithmetic, nothing more; neither is proposed as a replacement.

Self-check: the frozen-rule row is recomputed here from the raw judgements, independently of the report driver, and reproduces the confirmatory report's published slopes exactly (+0.06502 at p = 0.0182 on the primary model, -0.00219 at p = 0.9601 on the robustness model). If those two ever stop matching, one of the two scripts has drifted.

### Gemma-4-31B-it — PRIMARY, channel 2

| UNCLEAR handling | mean slope / year | p | subjects with a slope | slopes below zero | cells scored | items scored |
|---|---|---|---|---|---|---|
| **frozen rule (reported)** | +0.06502 | 0.0182 | 17 | 4 | 60 | 200 |
| exploratory: counted as non match | +0.04785 | 0.0389 | 18 | 3 | 61 | 247 |
| exploratory: counted as half | +0.07013 | 0.0167 | 18 | 4 | 61 | 247 |

### gemini-3.5-flash-lite — ROBUSTNESS, channel 2

| UNCLEAR handling | mean slope / year | p | subjects with a slope | slopes below zero | cells scored | items scored |
|---|---|---|---|---|---|---|
| **frozen rule (reported)** | -0.00219 | 0.9601 | 18 | 4 | 61 | 201 |
| exploratory: counted as non match | +0.01315 | 0.8168 | 18 | 3 | 61 | 247 |
| exploratory: counted as half | +0.00183 | 0.9675 | 18 | 5 | 61 | 247 |

Source: `experiments/h7_diagnostics.py`, reading `results/stage2_confirm/render_index.jsonl` and `results/stage2_confirm/judge/judgements_*.jsonl`.

## 4. Crossing vs non-crossing subjects — EXPLORATORY

Per subject, the crossover fires when the fresh imposter matches or beats the stale own twin in some bin. It fires for 13/36 subjects on channel 1 Gemma, 11/36 on channel 1 flash-lite, 21/36 on channel 2 Gemma and 22/36 on channel 2 flash-lite. This section asks whether the subjects it fires for differ from the ones it does not on three plain covariates: the contamination meter, how many items they carry, and how many bins they fill.

**Small-n honesty, stated before the numbers.** Every cell below splits 36 subjects into two groups; the smallest group is 11. No significance test is run and none should be read in. These are counts, means and medians, and the only thing to take from them is the direction of a difference and whether it is large enough to notice.

The contamination meter is the channel-1 meter for that model (zeroinfo_named − zeroinfo_redacted, per subject) in all four cells: the channel-2 meter has a median of exactly 0 per subject and cannot separate groups. Item counts and bins filled ARE channel-specific — channel 2 counts only items the judge labelled SAME or DIFFERENT.

### Gemma-4-31B-it — PRIMARY, channel 1 (embedding cosine)

| group | subjects | contamination meter (mean / median) | bins filled (mean) | total items (mean) | items per filled bin (mean) |
|---|---|---|---|---|---|
| crosses at some bin | 13 | +0.0307 / +0.0307 | 2.00 | 8.54 | 3.85 |
| never crosses | 23 | -0.0004 / -0.0105 | 1.52 | 5.91 | 4.00 |

Crossing minus non-crossing: meter +0.0310, bins filled +0.48, total items +2.63, items per filled bin -0.15. Groups are thin; read direction only.

### gemini-3.5-flash-lite — ROBUSTNESS, channel 1 (embedding cosine)

| group | subjects | contamination meter (mean / median) | bins filled (mean) | total items (mean) | items per filled bin (mean) |
|---|---|---|---|---|---|
| crosses at some bin | 11 | +0.0469 / +0.0325 | 1.91 | 7.45 | 3.73 |
| never crosses | 25 | +0.0626 / +0.0530 | 1.60 | 6.60 | 4.04 |

Crossing minus non-crossing: meter -0.0157, bins filled +0.31, total items +0.85, items per filled bin -0.31. Groups are thin; read direction only.

### Gemma-4-31B-it — PRIMARY, channel 2 (stance match)

| group | subjects | contamination meter (mean / median) | bins filled (mean) | total items (mean) | items per filled bin (mean) |
|---|---|---|---|---|---|
| crosses at some bin | 21 | -0.0013 / -0.0110 | 1.71 | 5.10 | 2.87 |
| never crosses | 15 | +0.0278 / +0.0204 | 1.60 | 6.20 | 3.74 |

Crossing minus non-crossing: meter -0.0290, bins filled +0.11, total items -1.10, items per filled bin -0.88.

### gemini-3.5-flash-lite — ROBUSTNESS, channel 2 (stance match)

| group | subjects | contamination meter (mean / median) | bins filled (mean) | total items (mean) | items per filled bin (mean) |
|---|---|---|---|---|---|
| crosses at some bin | 22 | +0.0439 / +0.0442 | 1.68 | 5.64 | 3.27 |
| never crosses | 14 | +0.0796 / +0.0462 | 1.71 | 5.50 | 3.36 |

Crossing minus non-crossing: meter -0.0357, bins filled -0.03, total items +0.14, items per filled bin -0.09. Groups are thin; read direction only.

Source: `experiments/h7_diagnostics.py`, reading `results/stage2_confirm/report_numbers.json` (crossover lists, contamination meters), `results/stage2_confirm/embed/cosines_*.jsonl` and `results/stage2_confirm/judge/judgements_*.jsonl` (item counts).

## What this decomposition explains, and what it does not

1. **The imposter-minus-twin UNCLEAR gap does NOT concentrate in the crossover bin — the twin's OWN UNCLEAR rate does.** On the primary model the gap is roughly flat across bins (+0.1186, +0.1184, +0.0526, +0.1622). What is not flat is the stale own twin's UNCLEAR rate: 0.3051 in the freshest bin against 0.1543 across the other three pooled. That freshest bin is exactly where channel 2 puts its pooled crossover and where its positive slope begins, and it is the bin whose twin denominator is thinned hardest. On flash-lite — the model with no positive slope and no crossover — the same comparison is 0.2034 vs 0.1809, barely a spike. Related: the channel-2 bins printing `n/a` for own − fresh imposter (6-12m, >3y) do so because the imposter arm loses whole subjects to UNCLEAR, while the crossover statistic compares the same two means without that guard.

2. **A Δ-correlated era covariate exists between subjects but vanishes within them, and it does not track the stance slope.** Grounding-to-answer overlap rises with Δ across cells (lexical Jaccard r = +0.2725, p = 0.0336; embedding cosine r = +0.0764, p = 0.5583), so the confound B7 declares is measurable. But cells are not independent — the same subject fills several — and within subjects the covariate is flat (mean slope -0.000107 per year, p = 0.8491, n = 18). Per subject it also does not correlate with the channel-2 stance slope (r = +0.0237, p = 0.9281, n = 17). On this evidence era drift is not what produces the anti-decay slope — though n is small and this is a correlation, not a test of mechanism.

3. **The stance slope's sign is not an artefact of the UNCLEAR rule.** Under the frozen rule the primary-model slope is +0.06502 per year (p = 0.0182); counting UNCLEAR as a non-match gives +0.04785 (p = 0.0389); counting it as 0.5 gives +0.07013 (p = 0.0167). All three are positive. The frozen rule stays the reported number; the variants only show the direction does not hinge on it.

4. **Crossing and non-crossing subjects are not cleanly separated by contamination, item count, or bins filled.** The differences are small, inconsistent in sign across the four model-by-channel cells, and the smallest group is 11 subjects. These cells are too thin to read as a finding; they are reported so nobody has to wonder whether the split was checked.

5. **Net: the disagreement is narrowed, not resolved.** Two candidate explanations are weakened here — era drift does not track the slope, and the UNCLEAR rule does not flip its sign. One is strengthened: the channel-2 denominators are thin and unevenly thinned, worst in the bin that carries the crossover, so channel 2's H7 numbers are noisier than channel 1's. Nothing here identifies what makes the stance slope positive, and nothing here changes the frozen conclusion in the confirmatory report: the channels disagree, so H7 gets no headline reading.
