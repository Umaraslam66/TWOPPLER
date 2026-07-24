# Re-scoring the v2 runs: expected value vs argmax (EXPLORATORY)

> **EXPLORATORY. Not confirmatory, not an outcome claim.**
> Stage 1 development data, re-scored after the fact from records already on disk.
> Prompted by the literature check (`results/lit_check.md`), not pre-registered.
> No bar in PREREGISTRATION.md attaches to anything below. No new model calls were made;
> compute cost of this analysis is zero (CPU re-scoring of existing files).

Generated 2026-07-24 19:49 UTC

## 1. The question

The v2 elicitation asks the model for a probability over each of the 7 answers.
A distribution has to be turned into a number before it can be scored. There are two
obvious ways:

- **EV (expected value)**: the probability-weighted average, e.g. `1:0.1 ... 7:0.1` -> 4.0.
  A continuous number between 1 and 7. This is what every published DOPPLER v2 number uses.
- **argmax**: the single answer with the highest probability. An integer 1-7.

The closest prior work (Ahnert et al., arXiv 2510.11586) reports that asking for a point
answer beats asking for a distribution at the individual level. But they decode the
distribution by **argmax**. That is a different comparison from ours. The open question is
narrow and answerable from data already on disk: **on the same distributions, does EV
decoding beat argmax decoding, per person?**

Everything below re-parses the raw model responses with `src/doppler/scoring.parse_v2` and
scores the identical set of (person, item) pairs under both decodings. The pre-registered
exclusion rule is kept: a pair is dropped from both arms if either arm failed to parse.
Parsing is identical for the two decodings, so the two are scored on exactly the same
pairs and every comparison is fully paired.

Two labelling notes:

- MAE under EV uses the continuous EV. MAE under argmax uses the integer.
- Within-1 and exact-match need an integer. Under argmax that is the argmax. Under EV
  there is no natural integer, so the EV is rounded to the nearest scale point
  (half rounds up) and the column is labelled **rounded EV** everywhere. Rounded-EV
  accuracy is a derived convenience number, not a decoding anyone proposed.

## 2. Reproduction gate

Before any new number is trusted, the EV-decoded lift recomputed here has to reproduce
the already-published lift for each run, to within 0.0005. All runs pass.

| run | published lift | source | recomputed (EV) | difference | vs run's own summary.json | gate |
|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | +0.0910 | `results/pilot2_comparison.md` | +0.090706 | -0.000294 | +0.00e+00 | PASS |
| pilot2 v2 - gemma-4 | +0.0850 | `results/pilot2_comparison.md` | +0.085420 | +0.000420 | +0.00e+00 | PASS |
| pilot2 v2 - qwen | +0.0030 | `results/pilot2_comparison.md` | +0.003300 | +0.000300 | +6.94e-18 | PASS |
| gate v2 - PRIMARY | +0.0850 | `results/stage1_gate_report.md` | +0.085021 | +0.000021 | -1.39e-17 | PASS |
| gate v2 - SECONDARY | +0.0954 | `results/stage1_gate_report.md` | +0.095445 | +0.000045 | +0.00e+00 | PASS |
| probe known-answer v2 | +0.0453 | `results/probe_known_answer.md (diagnostic, no bar)` | +0.045296 | -0.000004 | -1.39e-17 | PASS |

The last column is a tighter check: the difference against the full-precision lift stored
in each run's own `summary.json` (the published table rounds to 3 or 4 decimals).

Parser audit - the fresh parse was compared record by record against the values stored in
each file. Any drift would show up here.

| run | records | stored parse failures | fresh parse failures | flag mismatches | EV mismatches | argmax mismatches |
|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | 1000 | 0 | 0 | 0 | 0 | 0 |
| pilot2 v2 - gemma-4 | 1000 | 0 | 0 | 0 | 0 | 0 |
| pilot2 v2 - qwen | 1000 | 0 | 0 | 0 | 0 | 0 |
| gate v2 - PRIMARY | 10000 | 0 | 0 | 0 | 0 | 0 |
| gate v2 - SECONDARY | 10000 | 5 | 5 | 0 | 0 | 0 |
| probe known-answer v2 | 10000 | 0 | 0 | 0 | 0 | 0 |

## 3. Per-run results

### pilot2 v2 - gemini

`results/pilot2_v2_k48_20260724-180024` - model gemini-3.5-flash-lite, pilot2 (n=50), persons scored 50, pairs scored 500, pairs excluded 0

**MAE, all four arm x decoding cells** (lower is better):

| arm | EV decoding | argmax decoding |
|---|---|---|
| twin | 1.4296 [1.3249, 1.5343] | 1.4060 [1.2841, 1.5279] |
| baseline | 1.5203 [1.4165, 1.6242] | 1.5080 [1.3866, 1.6294] |

**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift cannot be read without seeing which arm moved:

| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |
|---|---|---|---|---|---|---|
| EV | 1.4296 | 1.5203 | +0.0907 | [+0.0469, +0.1345] | 4.1638 | 0.0001263 |
| argmax | 1.4060 | 1.5080 | +0.1020 | [+0.0320, +0.1720] | 2.9297 | 0.005139 |

**Individual-level head-to-head, EV vs argmax on the same distributions.** gap = argmax MAE - EV MAE, per person, paired t across persons. Positive gap = EV decoding is better:

| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |
|---|---|---|---|---|---|---|---|---|---|
| twin | 1.4296 | 1.4060 | -0.0236 | [-0.0780, +0.0307] | -0.8739 | 0.3864 | 25 | 25 | 0 |
| baseline | 1.5203 | 1.5080 | -0.0123 | [-0.0610, +0.0363] | -0.5091 | 0.613 | 23 | 27 | 0 |

**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns are EV rounded to the nearest scale point (labelled, see section 1):

| metric | decoding | twin | baseline | lift | 95% CI | p |
|---|---|---|---|---|---|---|
| within-1 | argmax | 0.5880 | 0.5260 | +0.0620 | [+0.0257, +0.0983] | 0.001213 |
| within-1 | rounded EV | 0.5660 | 0.5040 | +0.0620 | [+0.0351, +0.0889] | 2.64e-05 |
| exact match | argmax | 0.2400 | 0.1940 | +0.0460 | [-0.0021, +0.0941] | 0.0605 |
| exact match | rounded EV | 0.1800 | 0.1680 | +0.0120 | [-0.0159, +0.0399] | 0.3919 |

### pilot2 v2 - gemma-4

`results/pilot2_v2_k48_20260724-173317_leonardo-batch` - model leonardo-gemma4-31b, pilot2 (n=50), persons scored 50, pairs scored 500, pairs excluded 0

**MAE, all four arm x decoding cells** (lower is better):

| arm | EV decoding | argmax decoding |
|---|---|---|
| twin | 1.3843 [1.2884, 1.4802] | 1.4020 [1.2884, 1.5156] |
| baseline | 1.4697 [1.3738, 1.5656] | 1.4360 [1.3218, 1.5502] |

**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift cannot be read without seeing which arm moved:

| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |
|---|---|---|---|---|---|---|
| EV | 1.3843 | 1.4697 | +0.0854 | [+0.0248, +0.1461] | 2.8312 | 0.006709 |
| argmax | 1.4020 | 1.4360 | +0.0340 | [-0.0582, +0.1262] | 0.7414 | 0.462 |

**Individual-level head-to-head, EV vs argmax on the same distributions.** gap = argmax MAE - EV MAE, per person, paired t across persons. Positive gap = EV decoding is better:

| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |
|---|---|---|---|---|---|---|---|---|---|
| twin | 1.3843 | 1.4020 | +0.0177 | [-0.0329, +0.0684] | 0.7039 | 0.4848 | 24 | 26 | 0 |
| baseline | 1.4697 | 1.4360 | -0.0337 | [-0.0887, +0.0214] | -1.2293 | 0.2248 | 21 | 29 | 0 |

**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns are EV rounded to the nearest scale point (labelled, see section 1):

| metric | decoding | twin | baseline | lift | 95% CI | p |
|---|---|---|---|---|---|---|
| within-1 | argmax | 0.6000 | 0.5820 | +0.0180 | [-0.0271, +0.0631] | 0.4264 |
| within-1 | rounded EV | 0.6080 | 0.5500 | +0.0580 | [+0.0203, +0.0957] | 0.003273 |
| exact match | argmax | 0.2460 | 0.1840 | +0.0620 | [+0.0199, +0.1041] | 0.004782 |
| exact match | rounded EV | 0.2000 | 0.1720 | +0.0280 | [-0.0110, +0.0670] | 0.155 |

### pilot2 v2 - qwen

`results/pilot2_v2_k48_20260724-165234_leonardo-batch` - model leonardo-qwen3.6-27b, pilot2 (n=50), persons scored 50, pairs scored 500, pairs excluded 0

**MAE, all four arm x decoding cells** (lower is better):

| arm | EV decoding | argmax decoding |
|---|---|---|
| twin | 1.4374 [1.3343, 1.5405] | 1.4160 [1.2944, 1.5376] |
| baseline | 1.4407 [1.3320, 1.5494] | 1.4320 [1.3100, 1.5540] |

**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift cannot be read without seeing which arm moved:

| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |
|---|---|---|---|---|---|---|
| EV | 1.4374 | 1.4407 | +0.0033 | [-0.0486, +0.0552] | 0.1278 | 0.8988 |
| argmax | 1.4160 | 1.4320 | +0.0160 | [-0.0542, +0.0862] | 0.4582 | 0.6488 |

**Individual-level head-to-head, EV vs argmax on the same distributions.** gap = argmax MAE - EV MAE, per person, paired t across persons. Positive gap = EV decoding is better:

| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |
|---|---|---|---|---|---|---|---|---|---|
| twin | 1.4374 | 1.4160 | -0.0214 | [-0.0648, +0.0220] | -0.9915 | 0.3263 | 21 | 29 | 0 |
| baseline | 1.4407 | 1.4320 | -0.0087 | [-0.0560, +0.0385] | -0.3708 | 0.7124 | 24 | 26 | 0 |

**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns are EV rounded to the nearest scale point (labelled, see section 1):

| metric | decoding | twin | baseline | lift | 95% CI | p |
|---|---|---|---|---|---|---|
| within-1 | argmax | 0.5720 | 0.5800 | -0.0080 | [-0.0442, +0.0282] | 0.6593 |
| within-1 | rounded EV | 0.5640 | 0.5580 | +0.0060 | [-0.0272, +0.0392] | 0.7179 |
| exact match | argmax | 0.2360 | 0.2160 | +0.0200 | [-0.0114, +0.0514] | 0.2073 |
| exact match | rounded EV | 0.1980 | 0.1900 | +0.0080 | [-0.0259, +0.0419] | 0.6373 |

### gate v2 - PRIMARY

`results/gate_v2_k48_20260724-181226` - model gemini-3.5-flash-lite, gate (n=500), persons scored 500, pairs scored 5000, pairs excluded 0

**MAE, all four arm x decoding cells** (lower is better):

| arm | EV decoding | argmax decoding |
|---|---|---|
| twin | 1.4885 [1.4539, 1.5230] | 1.4744 [1.4348, 1.5140] |
| baseline | 1.5735 [1.5378, 1.6092] | 1.5476 [1.5088, 1.5864] |

**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift cannot be read without seeing which arm moved:

| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |
|---|---|---|---|---|---|---|
| EV | 1.4885 | 1.5735 | +0.0850 | [+0.0689, +0.1012] | 10.3541 | 6.87e-23 |
| argmax | 1.4744 | 1.5476 | +0.0732 | [+0.0469, +0.0995] | 5.4700 | 7.13e-08 |

**Individual-level head-to-head, EV vs argmax on the same distributions.** gap = argmax MAE - EV MAE, per person, paired t across persons. Positive gap = EV decoding is better:

| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |
|---|---|---|---|---|---|---|---|---|---|
| twin | 1.4885 | 1.4744 | -0.0141 | [-0.0334, +0.0053] | -1.4303 | 0.1533 | 234 | 266 | 0 |
| baseline | 1.5735 | 1.5476 | -0.0259 | [-0.0428, -0.0089] | -3.0019 | 0.002817 | 237 | 261 | 2 |

**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns are EV rounded to the nearest scale point (labelled, see section 1):

| metric | decoding | twin | baseline | lift | 95% CI | p |
|---|---|---|---|---|---|---|
| within-1 | argmax | 0.5844 | 0.5370 | +0.0474 | [+0.0350, +0.0598] | 2.52e-13 |
| within-1 | rounded EV | 0.5356 | 0.4958 | +0.0398 | [+0.0288, +0.0508] | 4.83e-12 |
| exact match | argmax | 0.2168 | 0.1876 | +0.0292 | [+0.0162, +0.0422] | 1.20e-05 |
| exact match | rounded EV | 0.1620 | 0.1494 | +0.0126 | [+0.0032, +0.0220] | 0.008592 |

### gate v2 - SECONDARY

`results/gate_v2_k48_20260724-182324_leonardo-batch` - model leonardo-gemma4-31b, gate (n=500), persons scored 500, pairs scored 4995, pairs excluded 5

**MAE, all four arm x decoding cells** (lower is better):

| arm | EV decoding | argmax decoding |
|---|---|---|
| twin | 1.4339 [1.3979, 1.4700] | 1.4489 [1.4066, 1.4913] |
| baseline | 1.5294 [1.4949, 1.5638] | 1.4968 [1.4585, 1.5351] |

**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift cannot be read without seeing which arm moved:

| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |
|---|---|---|---|---|---|---|
| EV | 1.4339 | 1.5294 | +0.0954 | [+0.0750, +0.1159] | 9.1686 | 1.25e-18 |
| argmax | 1.4489 | 1.4968 | +0.0479 | [+0.0188, +0.0769] | 3.2373 | 0.001287 |

**Individual-level head-to-head, EV vs argmax on the same distributions.** gap = argmax MAE - EV MAE, per person, paired t across persons. Positive gap = EV decoding is better:

| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |
|---|---|---|---|---|---|---|---|---|---|
| twin | 1.4339 | 1.4489 | +0.0150 | [-0.0027, +0.0328] | 1.6607 | 0.09741 | 274 | 224 | 2 |
| baseline | 1.5294 | 1.4968 | -0.0326 | [-0.0494, -0.0158] | -3.8116 | 0.0001553 | 216 | 284 | 0 |

**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns are EV rounded to the nearest scale point (labelled, see section 1):

| metric | decoding | twin | baseline | lift | 95% CI | p |
|---|---|---|---|---|---|---|
| within-1 | argmax | 0.6066 | 0.5589 | +0.0477 | [+0.0336, +0.0617] | 7.24e-11 |
| within-1 | rounded EV | 0.5992 | 0.5268 | +0.0723 | [+0.0602, +0.0844] | 2.78e-28 |
| exact match | argmax | 0.2551 | 0.1899 | +0.0651 | [+0.0511, +0.0792] | 1.97e-18 |
| exact match | rounded EV | 0.2016 | 0.1627 | +0.0389 | [+0.0273, +0.0505] | 1.20e-10 |

### probe known-answer v2

`results/probe_knownanswer_v2_20260724-211148_leonardo-batch` - model leonardo-gemma4-31b, gate (n=500), persons scored 500, pairs scored 5000, pairs excluded 0

Baseline arm is the gate secondary's baseline records, reused byte-identical
(`results/probe_known_answer.md` section 9). The baseline rows below are therefore
the same records as the gate secondary row, scored over the probe's item set.

**MAE, all four arm x decoding cells** (lower is better):

| arm | EV decoding | argmax decoding |
|---|---|---|
| twin | 1.4842 [1.4271, 1.5412] | 1.5652 [1.4979, 1.6325] |
| baseline | 1.5295 [1.4950, 1.5639] | 1.4968 [1.4585, 1.5351] |

**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift cannot be read without seeing which arm moved:

| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |
|---|---|---|---|---|---|---|
| EV | 1.4842 | 1.5295 | +0.0453 | [-0.0077, +0.0983] | 1.6798 | 0.09362 |
| argmax | 1.5652 | 1.4968 | -0.0684 | [-0.1344, -0.0024] | -2.0369 | 0.04218 |

**Individual-level head-to-head, EV vs argmax on the same distributions.** gap = argmax MAE - EV MAE, per person, paired t across persons. Positive gap = EV decoding is better:

| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |
|---|---|---|---|---|---|---|---|---|---|
| twin | 1.4842 | 1.5652 | +0.0810 | [+0.0646, +0.0975] | 9.6893 | 1.86e-20 | 335 | 164 | 1 |
| baseline | 1.5295 | 1.4968 | -0.0327 | [-0.0494, -0.0159] | -3.8197 | 0.0001504 | 216 | 284 | 0 |

**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns are EV rounded to the nearest scale point (labelled, see section 1):

| metric | decoding | twin | baseline | lift | 95% CI | p |
|---|---|---|---|---|---|---|
| within-1 | argmax | 0.5866 | 0.5588 | +0.0278 | [+0.0040, +0.0516] | 0.02225 |
| within-1 | rounded EV | 0.6008 | 0.5268 | +0.0740 | [+0.0510, +0.0970] | 5.73e-10 |
| exact match | argmax | 0.2756 | 0.1900 | +0.0856 | [+0.0659, +0.1053] | 1.88e-16 |
| exact match | rounded EV | 0.2300 | 0.1628 | +0.0672 | [+0.0517, +0.0827] | 2.34e-16 |

## 4. Cross-run summary

Every lift with both arms' raw MAEs beside it, under both decodings.

| run | model | twin EV | base EV | lift EV | p (EV) | twin argmax | base argmax | lift argmax | p (argmax) |
|---|---|---|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | gemini-3.5-flash-lite | 1.4296 | 1.5203 | +0.0907 | 0.0001263 | 1.4060 | 1.5080 | +0.1020 | 0.005139 |
| pilot2 v2 - gemma-4 | leonardo-gemma4-31b | 1.3843 | 1.4697 | +0.0854 | 0.006709 | 1.4020 | 1.4360 | +0.0340 | 0.462 |
| pilot2 v2 - qwen | leonardo-qwen3.6-27b | 1.4374 | 1.4407 | +0.0033 | 0.8988 | 1.4160 | 1.4320 | +0.0160 | 0.6488 |
| gate v2 - PRIMARY | gemini-3.5-flash-lite | 1.4885 | 1.5735 | +0.0850 | 6.87e-23 | 1.4744 | 1.5476 | +0.0732 | 7.13e-08 |
| gate v2 - SECONDARY | leonardo-gemma4-31b | 1.4339 | 1.5294 | +0.0954 | 1.25e-18 | 1.4489 | 1.4968 | +0.0479 | 0.001287 |
| probe known-answer v2 | leonardo-gemma4-31b | 1.4842 | 1.5295 | +0.0453 | 0.09362 | 1.5652 | 1.4968 | -0.0684 | 0.04218 |

**Changing the decoding changes the lift.** Same responses, same people, same items -
only the rule for turning a distribution into a number differs:

| run | lift EV | lift argmax | change | what happens to the headline |
|---|---|---|---|---|
| pilot2 v2 - gemini | +0.0907 | +0.1020 | +0.0113 | stays significant, size x1.12 |
| pilot2 v2 - gemma-4 | +0.0854 | +0.0340 | -0.0514 | significant -> not significant |
| pilot2 v2 - qwen | +0.0033 | +0.0160 | +0.0127 | not significant either way |
| gate v2 - PRIMARY | +0.0850 | +0.0732 | -0.0118 | stays significant, size x0.86 |
| gate v2 - SECONDARY | +0.0954 | +0.0479 | -0.0476 | stays significant, size x0.50 |
| probe known-answer v2 | +0.0453 | -0.0684 | -0.1137 | **sign flips** |

**The EV-vs-argmax verdict, twin arm, one row per run:**

| run | twin EV MAE | twin argmax MAE | gap (argmax - EV) | 95% CI | t | p | who wins |
|---|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | 1.4296 | 1.4060 | -0.0236 | [-0.0780, +0.0307] | -0.8739 | 0.3864 | tie (n.s.) |
| pilot2 v2 - gemma-4 | 1.3843 | 1.4020 | +0.0177 | [-0.0329, +0.0684] | 0.7039 | 0.4848 | tie (n.s.) |
| pilot2 v2 - qwen | 1.4374 | 1.4160 | -0.0214 | [-0.0648, +0.0220] | -0.9915 | 0.3263 | tie (n.s.) |
| gate v2 - PRIMARY | 1.4885 | 1.4744 | -0.0141 | [-0.0334, +0.0053] | -1.4303 | 0.1533 | tie (n.s.) |
| gate v2 - SECONDARY | 1.4339 | 1.4489 | +0.0150 | [-0.0027, +0.0328] | 1.6607 | 0.09741 | tie (n.s.) |
| probe known-answer v2 | 1.4842 | 1.5652 | +0.0810 | [+0.0646, +0.0975] | 9.6893 | 1.86e-20 | EV |

Same table for the baseline arm, because the decoding choice hits both arms and a lift is
a difference of two arms:

| run | base EV MAE | base argmax MAE | gap (argmax - EV) | 95% CI | t | p | who wins |
|---|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | 1.5203 | 1.5080 | -0.0123 | [-0.0610, +0.0363] | -0.5091 | 0.613 | tie (n.s.) |
| pilot2 v2 - gemma-4 | 1.4697 | 1.4360 | -0.0337 | [-0.0887, +0.0214] | -1.2293 | 0.2248 | tie (n.s.) |
| pilot2 v2 - qwen | 1.4407 | 1.4320 | -0.0087 | [-0.0560, +0.0385] | -0.3708 | 0.7124 | tie (n.s.) |
| gate v2 - PRIMARY | 1.5735 | 1.5476 | -0.0259 | [-0.0428, -0.0089] | -3.0019 | 0.002817 | argmax |
| gate v2 - SECONDARY | 1.5294 | 1.4968 | -0.0326 | [-0.0494, -0.0158] | -3.8116 | 0.0001553 | argmax |
| probe known-answer v2 | 1.5295 | 1.4968 | -0.0327 | [-0.0494, -0.0159] | -3.8197 | 0.0001504 | argmax |

**Why the two decodings differ: spread.** EV always pulls a prediction toward the middle
of the distribution; argmax keeps whatever spread the modes have. Pooled over every scored
pair, against the spread of the real answers:

| run | sd(true) | sd(twin EV) | sd(twin argmax) | sd(base EV) | sd(base argmax) |
|---|---|---|---|---|---|
| pilot2 v2 - gemini | 1.9304 | 0.9788 | 1.4277 | 0.9144 | 1.3023 |
| pilot2 v2 - gemma-4 | 1.9304 | 1.2685 | 1.7068 | 0.8971 | 1.3396 |
| pilot2 v2 - qwen | 1.9304 | 1.1586 | 1.5130 | 1.0142 | 1.4068 |
| gate v2 - PRIMARY | 1.9771 | 1.0737 | 1.6045 | 0.9665 | 1.3935 |
| gate v2 - SECONDARY | 1.9770 | 1.3750 | 1.8648 | 0.9601 | 1.4229 |
| probe known-answer v2 | 1.9771 | 1.6230 | 2.1155 | 0.9598 | 1.4225 |

## 5. Is each lift twin-driven or baseline-driven?

A lift is `baseline MAE - twin MAE`. It can go up because the twin got better, or because
the baseline got worse. The second one is not a result worth having. The lit check flagged
that some DOPPLER lifts look like the second kind, so each v2 lift is decomposed against
its v0 (single-integer point elicitation) counterpart on the same people and items:

```
lift(v2) - lift(v0)  =  [twin MAE improvement from v0 to v2]
                      + [baseline MAE damage from v0 to v2]
```

Both numbers below are per person, paired, matched by person id. Positive twin gain = the
twin got better under v2. Positive baseline damage = the baseline got **worse** under v2.
The verdict rule, in order: if only one of the two channels is pushing the lift up, that
channel names the lift outright (a negative twin gain with positive baseline damage is
BASELINE-DRIVEN however small the share column looks). If both channels push the same way,
whichever supplies >= 60% of the change names it, and below 60% it is MIXED. The 60%
threshold is a reporting convention chosen here, not a pre-registered bar.
v2 numbers are EV-decoded, matching the published lift.

| run | v0 twin | v0 base | v0 lift | v2 twin | v2 base | v2 lift | change | twin gain | p | baseline damage | p | share twin / base | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | 1.3660 | 1.4380 | +0.0720 | 1.4296 | 1.5203 | +0.0907 | +0.0187 | -0.0636 | 0.1837 | +0.0823 | 0.04884 | 44% / 56% | BASELINE-DRIVEN |
| pilot2 v2 - gemma-4 | 1.4960 | 1.4400 | -0.0560 | 1.3843 | 1.4697 | +0.0854 | +0.1414 | +0.1117 | 0.02682 | +0.0297 | 0.3335 | 79% / 21% | TWIN-DRIVEN |
| pilot2 v2 - qwen | 1.5160 | 1.4280 | -0.0880 | 1.4374 | 1.4407 | +0.0033 | +0.0913 | +0.0786 | 0.1128 | +0.0127 | 0.6312 | 86% / 14% | TWIN-DRIVEN |
| gate v2 - PRIMARY | - | - | - | - | - | - | - | - | - | - | - | - | N/A (no v0 counterpart) |
| gate v2 - SECONDARY | - | - | - | - | - | - | - | - | - | - | - | - | N/A (no v0 counterpart) |
| probe known-answer v2 | - | - | - | - | - | - | - | - | - | - | - | - | N/A (no v0 counterpart) |

Runs marked N/A have no v0 counterpart: the gate was only ever run at v2 (the variant was
chosen from pilot2 before the gate), and the known-answer probe is a v2-only diagnostic
with a different prompt construction, so there is nothing to decompose against.

Read the verdict precisely: it names what drove the **change in lift from v0 to v2**, not
the whole of the v2 lift. A run can have had a real lift at v0 already.

### 5b. The sharper test: can the v2 twin beat the *best* baseline?

The decomposition above can be gamed by a reader who only looks at one variant. The blunt
version of the same question: each run has two zero-information baselines on the same
people - the v0 one and the v2 one. Take the v0 baseline and ask whether the **v2 twin**
beats it. If a twin cannot beat the other variant's baseline, its own variant's lift is
mostly a statement about a damaged comparison arm.

| run | v2 twin MAE | v2 baseline MAE | v0 baseline MAE | which baseline is stronger | v2 twin vs v0 baseline | 95% CI | p | vs its own v2 lift |
|---|---|---|---|---|---|---|---|---|
| pilot2 v2 - gemini | 1.4296 | 1.5203 | 1.4380 | v0 | +0.0084 | [-0.0780, +0.0948] | 0.8464 | +0.0907 |
| pilot2 v2 - gemma-4 | 1.3843 | 1.4697 | 1.4400 | v0 | +0.0557 | [-0.0133, +0.1248] | 0.1112 | +0.0854 |
| pilot2 v2 - qwen | 1.4374 | 1.4407 | 1.4280 | v0 | -0.0094 | [-0.0866, +0.0678] | 0.8074 | +0.0033 |
| gate v2 - PRIMARY | - | - | - | - | - | - | - | N/A (no v0 counterpart) |
| gate v2 - SECONDARY | - | - | - | - | - | - | - | N/A (no v0 counterpart) |
| probe known-answer v2 | - | - | - | - | - | - | - | N/A (no v0 counterpart) |

## 6. What this says, in plain language

### The headline answer

**Does EV decoding beat argmax decoding of the same distributions, at the individual
level, consistently? No.** On the twin arm, the two decodings are statistically
indistinguishable in 5 of the 6 runs, and the
numerical direction is not even consistent: EV is nominally ahead in 3 runs and
argmax in 3. Only one run shows a real gap, and it is the run with the most
over-confident twin (details below). This does **not** replicate as a general rule.

The gaps, twin arm, run by run (positive = EV better):

- **pilot2 v2 - gemini**: EV is 0.0236 MAE points worse than argmax, p = 0.3864 (not significant); EV wins for 25 of 50 people.
- **pilot2 v2 - gemma-4**: EV is 0.0177 MAE points better than argmax, p = 0.4848 (not significant); EV wins for 24 of 50 people.
- **pilot2 v2 - qwen**: EV is 0.0214 MAE points worse than argmax, p = 0.3263 (not significant); EV wins for 21 of 50 people.
- **gate v2 - PRIMARY**: EV is 0.0141 MAE points worse than argmax, p = 0.1533 (not significant); EV wins for 234 of 500 people.
- **gate v2 - SECONDARY**: EV is 0.0150 MAE points better than argmax, p = 0.09741 (not significant); EV wins for 274 of 500 people.
- **probe known-answer v2**: EV is 0.0810 MAE points better than argmax, p = 1.86e-20 (**significant**); EV wins for 335 of 500 people.

### The finding that does replicate: the baseline arm

Look at the baseline instead and the picture is clean and consistent. **Argmax beats EV on
the baseline arm in every run**, significantly in all three of the n=500 runs (the pilot2
runs point the same way at n=50 and cannot resolve it). This is the opposite of what the
EV-is-better story would predict, and it is the more reliable of the two results.

The spread table in section 4 says why. EV is an averaging operation - it always pulls a
prediction toward the middle of its own distribution. The baseline (demographics only) is
already badly under-dispersed: it hedges near the scale midpoint while real answers are
spread across the whole 1-7 range. Averaging a hedged distribution squeezes it further,
and against a widely spread truth that costs MAE. Argmax at least lands on a mode and
keeps some spread. So EV *damages the baseline*.

The spread numbers make this exact. Real answers have sd about 1.98. Every EV-decoded arm in
every run sits between 0.90 and 1.62 - under-dispersed, all of them. Argmax runs 1.30 to
2.12, closer to the truth. There is exactly one cell in the whole table where argmax
*over*-shoots the truth's spread: the known-answer probe's twin, at 2.1155 against a true
1.9771. That is the one and only run where EV beats argmax on the twin. The rule and the
exception are the same fact.

That probe run is also the one whose own report (`results/probe_known_answer.md` section 5b)
documents an over-committed twin: peak stated probability >= 0.5 on 27.4% of answers versus
0.9% for the baseline, and a fat error tail. Over-dispersed, so averaging helps it. Same
operation, opposite sign, depending on whether the arm was over- or under-confident.

**One rule covers both directions: EV compresses spread. That helps an over-confident
predictor and hurts a hedging one.** It is not a better decoding; it is a variance
shrinker, and whether shrinking helps depends on the arm.

### Why this matters for the published lifts

In four of the six runs EV hurts the hedging baseline more than it hurts the twin, so EV
decoding inflates the lift and switching to argmax shrinks it. The two exceptions are the
gemini runs at pilot2 scale and the qwen run, where the twin is hurt about as much as the
baseline and the lift moves the other way by a small amount. The runs that move most:

- **pilot2 v2 - gemini**: +0.0907 (p=0.0001263) under EV -> +0.1020 (p=0.005139) under argmax.
- **pilot2 v2 - gemma-4**: +0.0854 (p=0.006709) under EV -> +0.0340 (p=0.462) under argmax.
- **pilot2 v2 - qwen**: +0.0033 (p=0.8988) under EV -> +0.0160 (p=0.6488) under argmax.
- **gate v2 - PRIMARY**: +0.0850 (p=6.87e-23) under EV -> +0.0732 (p=7.13e-08) under argmax.
- **gate v2 - SECONDARY**: +0.0954 (p=1.25e-18) under EV -> +0.0479 (p=0.001287) under argmax.
- **probe known-answer v2**: +0.0453 (p=0.09362) under EV -> -0.0684 (p=0.04218) under argmax.

Two of those deserve to be said out loud:

- **The gate secondary lift halves.** +0.0954 under EV, +0.0479 under argmax. It stays
  significant, but half of the headline number is a decoding choice, not the twin.
- **The known-answer probe flips sign.** +0.0453 (n.s.) under EV becomes -0.0684 under
  argmax, and the negative version is significant at p=0.042. Under argmax the seeded twin
  is *worse* than a demographics-only guess. The probe's stated conclusion - that the
  constructor over-extrapolates and MAE does not reward it - survives this and is arguably
  strengthened, but the sign of its headline number is not decoding-independent and the
  report should say so.

### Does this contradict Ahnert et al.?

No, and it does not rescue our design either. Their claim is that point elicitation beats
distribution elicitation, decoded by argmax. What this re-scoring adds is that the decoding
is not a neutral implementation detail: on the same distributions it moves the lift by up
to a factor of two and in one case flips its sign. So a point-vs-distribution comparison
that decodes by argmax is measuring elicitation and decoding together - and so is ours,
which decodes by EV. Neither is the clean experiment.

The uncomfortable version: our published v2 lifts use the decoding that flatters them. EV
was chosen before any of this was known (it is the natural summary of a distribution and it
is what the pre-registration froze), so this is not a case of picking the winner after the
fact. But it now has a known direction of bias and every v2 lift should carry the argmax
number beside it.

### Twin-driven or baseline-driven?

- **pilot2 v2 - gemini**: **BASELINE-DRIVEN** - twin gain -0.0636 (p=0.1837), baseline damage +0.0823 (p=0.04884), of a +0.0187 change in lift from v0 to v2.
- **pilot2 v2 - gemma-4**: **TWIN-DRIVEN** - twin gain +0.1117 (p=0.02682), baseline damage +0.0297 (p=0.3335), of a +0.1414 change in lift from v0 to v2.
- **pilot2 v2 - qwen**: **TWIN-DRIVEN** - twin gain +0.0786 (p=0.1128), baseline damage +0.0127 (p=0.6312), of a +0.0913 change in lift from v0 to v2.
- **gate v2 - PRIMARY**: N/A - no v0 counterpart exists for this run.
- **gate v2 - SECONDARY**: N/A - no v0 counterpart exists for this run.
- **probe known-answer v2**: N/A - no v0 counterpart exists for this run.

The gemini case is the one the lit check was worried about, and it is confirmed: going from
v0 to v2 made the gemini **twin worse** (MAE 1.3660 -> 1.4296) and the **baseline worse
still** (1.4380 -> 1.5203, p=0.049). The lift went up only because the comparison arm fell
further. Section 5b makes the consequence concrete: the gemini v2 twin beats the *v0*
baseline by +0.0084 - essentially nothing - while advertising a +0.0907 lift against its
own damaged v2 baseline. The qwen run is the same shape at the other end: its v2 twin is
-0.0094 against the v0 baseline, i.e. worse than a zero-information guess made under the
other variant.

Gemma-4 is the exception and it supports the existing choice of it as the Stage 2 model. Its
twin genuinely improved from v0 to v2 (1.4960 -> 1.3843, p=0.027), its baseline barely moved
(+0.0297, p=0.33), and its v2 twin is the only one that is ahead of the v0 baseline by a
non-trivial margin (+0.0557). Be honest about that last number though: at n=50 it is not
significant (p=0.111). It is the right sign and the right size, not proof.

Caveat on qwen: its v2 lift is +0.0033, statistically zero. Classifying the *change* in a
lift that is itself zero says something about the v0 run (where the twin was worse than
baseline), not about a v2 result worth having.

## 7. Limits

- Stage 1 development data only. No bar attaches. Nothing here passes or fails a hypothesis.
- Post-hoc: the decodings were compared after the EV numbers were published, prompted by
  the literature check. It is a re-analysis of one design choice, not a new experiment.
- The two decodings share the raw responses, so they cannot be independent evidence. This
  is a question about scoring, not about model behaviour.
- Rounded-EV accuracy (within-1, exact) is a convenience column. No one proposed rounding
  the EV as a decoding; it exists so the accuracy metrics have an EV-side entry at all.
- The known-answer probe shares its baseline records with the gate secondary run, so those
  two rows are not independent on the baseline side. The three baseline-arm argmax wins in
  section 4 are therefore two independent facts, not three.
- The 60% threshold in section 5 is a reporting convention invented for this document. The
  raw twin-gain and baseline-damage numbers are printed beside every verdict so a reader can
  apply a different threshold.
- Section 5 decomposes the *change* in lift from v0 to v2. It is not a decomposition of the
  whole v2 lift, and it needs a v0 counterpart, which the gate and probe runs do not have.
- The pilot2 runs are n=50. Nothing there resolves an effect of the size being discussed;
  the n=500 runs carry the weight.
- EV was frozen as the decoding before any of this was known, so no result here was selected
  after the fact. But that also means the argmax numbers have never been through a
  pre-registered analysis, and they are exploratory in exactly the same way.

## 8. Provenance

- Script: `experiments/rescore_ev_argmax.py` (no network, no API calls, CPU only).
- Parser: `src/doppler/scoring.parse_v2`, unchanged, re-run over the stored `raw_response`.
- Statistics helpers: `src/doppler/scoring.mean_ci` and `.paired_tests`, unchanged.
- Inputs: the `records.jsonl` of each run listed in section 3, plus the v0 runs named in
  section 5. Read-only: no pre-existing file was modified, this document is the only output.
- Cost: zero (no model calls).

