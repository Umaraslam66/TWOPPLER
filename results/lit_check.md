# Literature check: are the two Stage 1 observations already known?

Date: 2026-07-24. Scope: prior-art check on two Stage 1 (exploratory) observations
before either is written up as a finding.

- **Claim A** — numeric scale anchoring: numbers in a persona profile (1-5 interest
  ratings) drag the model's answers on a different scale (1-7 TIPI), badly enough that
  the grounded twin loses to a zero-information baseline; rendering the input ratings as
  words removes the harm. Source: `results/finding_scale_anchoring.md`.
- **Claim B** — distribution elicitation: asking for a probability distribution over the
  answer options and scoring its expected value produces positive lift where a single
  point answer does not. Source: `results/pilot2_comparison.md` (v2 vs v0).

Method: ~126 web searches across three passes (all queries listed at the end), abstracts
read for ~60 papers, full text for the closest few, plus checks against our own code and
run summaries. Judged against what our notes actually claim, not against a generous
reading of them.

**Bottom line up front.**
- Claim A: **partially known.** The effect (numbers in context anchoring numeric output,
  including across scales) is published — in humans since 1996 and decisively for
  cross-scale in 2016, and for LLMs since 2022. What is ours: the persona-simulation
  setting, the demonstration that it inverts lift over a zero-information baseline, and
  the digits→words mitigation, which appears untested anywhere.
- Claim B: **mostly known, and our framing has a metric problem.** "Mean of the elicited
  distribution beats the mode" is a 2025 headline result elsewhere; the individual-level
  point-vs-distribution comparison was run at 400x our scale in 2026 and came out the
  other way. Separately, checking our own runs showed that some of our lift is baseline
  degradation rather than twin improvement — see the table under Claim B.

---

# Claim A — numeric scale anchoring in persona-conditioned prediction

## Verdict: **partially known — and less novel than the note implies**

Two things must be said plainly before anything else:

- **Anchoring on numbers in the prompt is thoroughly published for LLMs** (2022-2026,
  behavioural and mechanistic). "We found that LLMs are anchored by numbers" is a
  rediscovery.
- **Cross-scale anchoring — an anchor in one unit/scale shifting a judgment in a
  different unit/scale — was demonstrated decisively in humans ten years ago.**
  Harris & Speekenbrink (2016) showed a wolf's weight in lbs shifts giraffe *height*
  estimates in feet, and that even random digit strings do it. Our note's framing
  ("numbers in the profile act as anchors on numbers in the output") is that paper's
  result, restated for a model. A reviewer will find it; we should cite it first
  ourselves rather than let them.

What survives that:

**Already known (do not claim):**
1. Numbers in context bias numeric outputs — humans since 1996 (Wilson et al.), across
   scales and dimensions since 2016 (Harris & Speekenbrink), LLMs since 2022 (Jones &
   Steinhardt).
2. LLMs cluster ratings on arbitrary scale points and mis-use rating scales.
3. Anchoring strength varies a lot by model, and prompt-level mitigations mostly fail.

**Apparently new (claim this — in this order):**
1. **It is a measurement artifact that corrupts persona-fidelity metrics.** The anchoring
   literature reports anchoring as a shift in an estimate. Nobody reports that anchoring
   makes a *grounded* persona agent score worse than *the same model given no individual
   data at all*. That is the operational consequence, and it is invisible without a
   zero-information baseline arm. The nearest published version of this argument is Yang
   (2026), for count-based F1 in error detection — not for persona simulation.
2. **A cheap mechanical fix that nobody has tested: re-render the input numbers as
   words.** The published LLM mitigation work is instruction-level (explicit debiasing,
   CoT, reflection) and reports it is unreliable. The nearest published fix in survey
   simulation (Semantic Similarity Rating; self-rating-bias work) de-numerifies the
   **output**, not the **context**. Agent search found no paper testing digit-vs-word
   rendering as a bias mitigation anywhere.
3. **The anchor is a task-relevant profile attribute, not an irrelevant or explicitly
   labelled reference number.** Every LLM anchoring paper found uses a random/irrelevant
   number or a number presented as a candidate answer or prior estimate. Legitimate
   structured user data acting as an anchor is a different and more insidious case,
   because there is no obvious reason to strip it.
4. **Secondary, worth one sentence:** our v1 result (reasoning-first *amplifies* the harm:
   Qwen -0.118, Gemma -0.062) contradicts Huang et al. (2505.15392), who report reasoning
   as their best mitigation. Also consistent with Ahnert et al. (ACL 2026), who find
   reasoning output does not consistently improve survey-response alignment.

**Do not claim:** "cross-scale anchoring exists". It does, and it was shown in humans in
2016. Claim the setting, the metric consequence, and the fix.

## Closest prior work, ranked by proximity

1. **Harris, A. J. L., & Speekenbrink, M. (2016).** "Semantic cross-scale numerical
   anchoring." *Judgment and Decision Making*, 11(6), 572-581.
   https://jbaron.org/journal/16/16609/jdm16609.html
   — **The paper that most threatens our framing.** Four experiments showing numerical
   anchors transfer *across scales and across dimensions* in humans: a wolf's weight in
   lbs shifts giraffe *height* estimates in feet; a 3-ton elephant anchor raises giraffe
   weight estimates in lbs; Exp. 3 uses pure random digit strings (0101-0129 vs
   4001-4029) and still moves a height judgment; Exp. 4 replicates in credit-card
   repayment (2% vs $38.74). It also refutes scale-distortion theory, which had predicted
   cross-scale anchoring should *fail*.
   **Overlap:** the entire "numbers on scale A bias answers on scale B" claim.
   **Non-overlap:** humans, not models; no persona conditioning; no Likert items; no
   digit-vs-word manipulation; no accuracy-vs-baseline consequence.
   **Action:** cite prominently and up front in any write-up.

2. **Wilson, T. D., Houston, C. E., Etling, K. M., & Brekke, N. (1996).** "A new look at
   anchoring effects: Basic anchoring and its antecedents." *Journal of Experimental
   Psychology: General*, 125(4), 387-402. https://pubmed.ncbi.nlm.nih.gov/8945789/
   — The older human precedent. *Basic* anchoring: numbers that are uninformative and
   never presented as a candidate answer still shift an unrelated numeric judgment.
   Proposes the **numeric priming** account (the anchor activates nearby numeric values
   by spreading activation) — the mechanism our v0/v3 contrast implicates.
   **Non-overlap:** humans; no persona simulation; no baseline-lift framing.

3. **Garcia, J. (2026).** "Algorithmic Anchoring: How Prompt-Embedded Reference Points Bias
   LLM Financial Estimates." SSRN working paper 6366838 (posted 9 Mar 2026).
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6366838
   — The closest **LLM** result on cross-metric propagation: a number embedded in the
   prompt as a "prior AI estimate" raised valuation sensitivity by ~52% and propagated
   *selectively to a different metric* (moved P/E ratios and buy/sell recommendations,
   left growth forecasts largely untouched).
   **Overlap:** anchor is a context field, and the effect lands on an output on a
   different numeric scale.
   **Non-overlap:** finance, not persona/survey; the anchor is task-relevant *and*
   explicitly labelled as an estimate; no Likert; no word-rendering test.
   **Caveat: SSRN blocked automated fetch (403). This entry rests on search snippets —
   verify before citing.**

4. **Kizawa, S., et al. (2025).** "Interpreting Multi-Attribute Confounding through
   Numerical Attributes in Large Language Models." IJCNLP-AACL 2025 (Main).
   arXiv:2511.04053. https://aclanthology.org/2025.ijcnlp-long.60.pdf
   — The closest mechanistic story: numerical attributes of an entity share latent
   subspaces, models encode and **systematically amplify** real-world correlations between
   them, and irrelevant numerical context induces consistent shifts in magnitude
   representations with downstream output effects.
   **Overlap:** "numbers about one attribute perturb answers about another" at the
   representation level.
   **Non-overlap:** their concrete vulnerability test injects *same-attribute* few-shot
   examples (city areas → city area), so it is same-scale contamination; no persona, no
   Likert, no digit-vs-word test.

5. **Valencia-Clavijo, F. (2025).** "Anchors in the Machine: Behavioral and Attributional
   Evidence of Anchoring Bias in LLMs." arXiv:2511.05766.
   https://arxiv.org/abs/2511.05766
   — Behavioural plus Shapley-attribution evidence that anchors shift whole output
   distributions; Anchoring Bias Sensitivity Score across six open models.
   **Non-overlap (checked in full text):** anchor and output are on the **identical
   0-100 scale** (roulette-wheel number → percentage estimate); attribution runs over
   template slots, none a persona field; explicitly no personas, no Likert, no
   word-number rendering.

6. **Li, Q., Dou, S., Shao, K., Chen, C., & Hu, H. (2025/2026).** "Evaluating Scoring Bias
   in LLM-as-a-Judge." arXiv:2506.22316; DASFAA 2026.
   https://arxiv.org/abs/2506.22316
   — Introduces **reference answer score bias**: a score shown in the scoring prompt
   biases the judge's own score. Reframes judging biases as originating in the *scoring
   prompt itself* rather than in the thing being judged — the same move we make.
   **Non-overlap:** the reference score is on the *same* scale and about the *same*
   object; judging, not simulating a person.

7. **Yang, D. (2026).** "Prompt Framing Distorts Count-Based Evaluation of LLM Error
   Detection: Evidence from Numeric Anchoring." arXiv:2607.01240 (preprint).
   https://arxiv.org/abs/2607.01240
   — Six models, five prompt conditions; a numeric anchor in the instruction shifts
   reported error counts, inflating count-based F1 to 0.96 under strict matching with no
   span-level gain.
   **Overlap:** this is the **closest published version of our strongest argument** — a
   numeric anchor in the prompt creating a *measurement artifact* that flatters a metric.
   Nobody has made that argument for persona-simulation fidelity. Cite it as the model
   for how to frame ours.
   **Non-overlap:** grammatical-error counts, not Likert; anchor and output both counts;
   no persona; no word rendering.

8. **Lou, J., & Sun, Y. (2024/2025).** "Anchoring Bias in Large Language Models: An
   Experimental Study." arXiv:2412.06593; *Journal of Computational Social Science*,
   doi:10.1007/s42001-025-00435-2. https://arxiv.org/abs/2412.06593
   — GPT-3.5/4/4o; anchoring consistently present; tests CoT, "thoughts of principles",
   reflection and ignore-the-anchor instructions; results strongly model-dependent.
   **Note:** a separate paper, **Nguyen, J. K. (2024), "Human bias in AI models? Anchoring
   effects and mitigation strategies in large language models," *Journal of Behavioral and
   Experimental Finance*** (https://www.sciencedirect.com/science/article/pii/S2214635024000868),
   reports GPT-3 matching a prepended anchor exactly 67% of the time. Both are same-scale,
   single-number anchors on estimation tasks. Do not conflate the two.

9. **Huang, Y., Bie, B., Na, Z., Ruan, W., Lei, S., Yue, Y., & He, X. (2025/2026).**
   "Understanding the Anchoring Effect of LLM with Synthetic Data: Existence, Mechanism,
   and Potential Mitigations." arXiv:2505.15392; ICLR 2026 HCAIR Workshop.
   https://arxiv.org/abs/2505.15392
   — Introduces SynAnchors; the only LLM paper found that adopts the human literature's
   **semantic priming vs numerical priming** distinction. Anchoring "exists commonly with
   shallow-layer acting", is not removed by conventional prompt strategies, and reasoning
   helps somewhat.
   **Non-overlap and direct contradiction:** their numerical anchors are same-scale, and
   reasoning is their *best* mitigation — while our v1 shows reasoning makes it worse
   (-0.118 Qwen, -0.062 Gemma). Cite precisely because it disagrees.

10. **Owusu, H. N., Wiegreffe, S., & Feldman, N. H. (2026).** "Localizing Anchoring
    Pathways in Language Models." arXiv:2606.12818. https://arxiv.org/abs/2606.12818
    — Edge-level circuit attribution of anchoring in 7-8B Qwen/Llama base and instruct
    models; low- and high-anchor circuits transfer within a model but not reliably
    base→instruct. Relevant to our per-model variation (Qwen drag vs Gemma centred vs
    Gemini none).
    **Non-overlap:** multiple choice with shared options, not free numeric or Likert
    output; no personas; no cross-scale manipulation.

11. **Jones, E., & Steinhardt, J. (2022).** "Capturing Failures of Large Language Models
    via Human Cognitive Biases." NeurIPS 2022. arXiv:2202.12299.
    https://arxiv.org/abs/2202.12299
    — The origin point for cognitive-bias-inspired LLM testing; Codex adjusts outputs
    toward anchors. Cite as framing, not as evidence — the domain is code and the
    "anchors" are prior code snippets, not numbers.

12. **Echterhoff, J., Liu, Y., Alessa, A., McAuley, J., & He, Z. (2024).** "Cognitive Bias
    in Decision-Making with LLMs." Findings of EMNLP 2024, 12640-12653. arXiv:2403.00811.
    https://aclanthology.org/2024.findings-emnlp.739/
    — BiasBuster; anchoring among several biases in college-admissions decisions.
    **Non-overlap:** the model is a decision-maker *about* a person, not a simulation *of*
    one; anchors are prior decision values on the decision's own scale.

13. **Wang, N., Sakai, T., et al. (2024).** "AI Can Be Cognitively Biased: Threshold Priming
    in LLM-Based Batch Relevance Assessment." SIGIR-AP 2024. arXiv:2409.16022.
    https://arxiv.org/abs/2409.16022
    — Earlier relevance scores bias later ones. Follow-up **"Mitigating the Threshold
    Priming Effect via Personality Infusing", WSDM 2026, arXiv:2512.00390**, is notable
    because there the *mitigation is a persona* — the exact inverse of our setup, where
    the persona is the source of the bias.

14. **Licht, H., et al. (2025).** "Measuring Scalar Constructs in Social Science with LLMs."
    EMNLP 2025. arXiv:2509.03116. https://aclanthology.org/2025.emnlp-main.1635/
    — Documents that LLM direct scalar responses **bunch around arbitrary values**.
    **Overlap:** the scale-use pathology our histograms show.
    **Non-overlap:** annotation of text; no numeric context anchor; no persona.

15. **Human survey-methodology support for the digits→words fix:**
    - Bottoni, G., & Aizpurua, E. (2026). "Between two minds: the influence of numerical
      labels on survey responses in a cross-national study." *Quality & Quantity*, 60,
      4595-4613. doi:10.1007/s11135-025-02436-9 — **numeric labels on an 11-point scale
      (0-10 vs -5…+5) change responses with the verbal endpoints held identical.** The
      human-side evidence that number *rendering* is not neutral. Strong support for our
      v3 intervention being principled rather than a hack.
    - Scale-distortion theory background: "A scale distortion theory of anchoring"
      (https://pubmed.ncbi.nlm.nih.gov/21767047/) — predicted cross-scale anchoring should
      fail; Harris & Speekenbrink (2016) refuted it.

16. **Scale-format work (background, cite only if needed):**
   - "Likert or Not: LLM Absolute Relevance Judgments on Fine-Grained Ordinal Scales."
     arXiv:2505.19334. https://arxiv.org/abs/2505.19334 — scale granularity changes
     judgments; fine-grained scales are not used as intended.
   - "Grading Scale Impact on LLM-as-a-Judge: Human-LLM Alignment Is Highest on 0-5
     Grading Scale." arXiv:2601.03444. https://arxiv.org/abs/2601.03444 — the *output*
     scale itself is a design variable with large effects.
   - Garcia, J. "Algorithmic Anchoring: How Prompt-Embedded Reference Points Bias LLM
     Financial Estimates." SSRN 6366838.
     https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6366838 — prompt-embedded
     numeric reference points bias estimates across Claude/GPT/Gemini.

17. **Number-representation background (for the digits→words fix):**
    - Levy, A., & Geva, M. (2025). "Language Models Encode Numbers Using Digit
      Representations in Base 10." NAACL 2025 (short). arXiv:2410.11781.
      https://arxiv.org/abs/2410.11781 — per-digit circular encoding, not value encoding;
      errors are close in *string* space, not value space. A plausible mechanistic reason
      why deleting the digits kills the anchor.
    - Shao, Lu & Yang (2025). "Benford's Curse: Tracing Digit Bias to Numerical
      Hallucination in LLMs." NeurIPS 2025. arXiv:2506.01734.
      https://arxiv.org/abs/2506.01734 — leading-digit bias inherited from pretraining
      corpus statistics; skews small, which is the right direction for our downward drag.
    - Yuchi, Du & Eisner (2026). "LLMs Know More About Numbers than They Can Say." EACL
      2026 (short). arXiv:2602.07812. https://arxiv.org/abs/2602.07812 — hidden states
      linearly encode log-magnitude better than the outputs express it.
    - **None of these tests digit-vs-word rendering as a bias mitigation.** The nearest is
      arXiv:2509.05691 (text-embedding numeracy), where written-form numbers give a *minor*
      accuracy advantage attributed to in-vocabulary tokenization.

18. **Persona / survey-simulation context (none of these report the effect):**
    - Park, J. S., et al. (2024, rev. 2026). "LLM Agents Grounded in Self-Reports Enable
      General-Purpose Simulation of Individuals." arXiv:2411.10109.
      https://arxiv.org/abs/2411.10109 — **note the retitle**: this is the paper we cite as
      "Generative Agent Simulations of 1,000 People" in PREREGISTRATION.md; v3 (June 2026)
      renamed it, and the headline is now 83-86% of test-retest, outperforming a
      demographics-only baseline. Our preregistration should be read alongside the new
      title; the numbers changed slightly.
    - Tjuatja, L., Chen, V., Wu, T., Talwalkar, A., & Neubig, G. (2024). "Do LLMs Exhibit
      Human-like Response Biases? A Case Study in Survey Design." TACL 12.
      https://aclanthology.org/2024.tacl-1.56/ — tests wording-based response biases;
      finds LLMs mostly do *not* reproduce human ones. Numeric anchoring is not among the
      perturbations tested. This is the paper our claim sits next to: a *new* response
      bias, one that is machine-specific rather than human-like.
    - Dominguez-Olmedo, R., Hardt, M., & Mendler-Dünner, C. (2024). "Questioning the Survey
      Responses of Large Language Models." NeurIPS 2024. arXiv:2306.07951.
      https://arxiv.org/abs/2306.07951 — survey-response artifacts (ordering, label
      choice) that are model artifacts, not human-like biases. Same genre as our claim.
    - Sun, H., Pei, J., Choi, M., & Jurgens, D. (2023). "Sociodemographic Prompting is Not
      Yet an Effective Approach for Simulating Subjective Judgments with LLMs."
      arXiv:2311.09730. https://arxiv.org/abs/2311.09730 — nine LLMs; sociodemographic
      prompting does not consistently help and sometimes *worsens* judgments for specific
      sub-populations. The nearest published statement of "grounding can be worse than
      nothing", but attributed to persona sensitivity, not to numeric anchoring.
      (Companion: Beck, T., et al., "Sensitivity, Performance, Robustness: Deconstructing
      the Effect of Sociodemographic Prompting", EACL 2024, arXiv:2309.07034.)
    - Rupprecht, J., Ahnert, G., & Strohmaier, M. (2025). "Prompt Perturbations Reveal
      Human-Like Biases in LLM Survey Responses." arXiv:2507.07188.
      https://arxiv.org/abs/2507.07188 — 167k simulated World Values Survey interviews,
      ten perturbations, consistent recency bias. Checked: **no** persona prompting, **no**
      numeric-vs-word rendering, **no** context-number manipulation — and they list persona
      prompting as an explicit limitation. That is our gap, stated by someone else.
    - Toubia, O., Gui, G., et al. (2025). "Twin-2K-500: A Dataset for Building Digital Twins
      of over 2,000 People Based on Their Answers to over 500 Questions." arXiv:2505.17479;
      *Marketing Science* database report, doi:10.1287/mksc.2025.0262.
      https://arxiv.org/abs/2505.17479 — the obvious dataset to replicate Claim A on: it is
      full of numeric prior answers pasted into persona prompts. They warn that "LLM answers
      may be overly influenced by the architecture of the prompt" and decile-transform
      answers for unbounded anchoring questions — a workaround for scale effects, not a
      study of them.
    - "Measuring Self-Rating Bias in LLM-Generated Survey Data." arXiv:2602.13862.
      https://arxiv.org/abs/2602.13862 — like SSR (2510.08338), argues LLMs give unrealistic
      distributions when asked *directly for numbers* and fixes it by eliciting text and
      mapping to Likert via verbal anchor statements. **Closest published thing to our
      mitigation — but it de-numerifies the output, not the context, and neither paper
      frames it as removing an anchoring effect.**

19. **Negative result worth recording (do not cite as anchoring evidence):**
    - "How Does Prompt Anchoring Affect Large Language Model Outputs?" *Publications*
      14(3):43, doi:10.3390/publications14030043 — despite the title this is **not numeric
      anchoring**. "Anchoring" there means anchoring on *example types* (no examples /
      keywords / detailed explanations) for keyword generation over 1,068 abstracts.
      (Fetch was 403-blocked; assessment from search snippets.)

## Suggested citation list for Claim A write-ups

Must-cite (or the novelty claim is indefensible): **Harris & Speekenbrink 2016**;
Wilson et al. 1996; Valencia-Clavijo 2025 (2511.05766); Huang et al. 2025 (2505.15392);
Lou & Sun 2024/2025 (2412.06593); Yang 2026 (2607.01240) as the framing model.
Should-cite: Jones & Steinhardt 2022; Kizawa et al. 2025 (2511.04053); Li et al. 2026
(2506.22316); Owusu et al. 2026 (2606.12818); Garcia 2026 (SSRN 6366838, verify first).
Scale use: Licht et al. 2025 (2509.03116); "Likert or Not" (2505.19334); Bottoni &
Aizpurua 2026 (Quality & Quantity).
Mechanism for the fix: 2410.11781; 2506.01734; 2602.07812.
Setting: Park et al. 2411.10109; Tjuatja et al. TACL 2024; Dominguez-Olmedo et al.
2306.07951; Sun et al. 2311.09730; Rupprecht et al. 2507.07188; Toubia et al. 2505.17479;
SSR 2510.08338 and 2602.13862 (output-side de-numerification).

---

# Claim B — distribution elicitation vs point answers

## Verdict: **mostly known as a mechanism; the individual-level head-to-head is published and reports the opposite ranking; and our own framing has a metric problem**

This is much the weaker of the two claims. Three separate literatures already say "don't
force a single integer, take the expected value of the distribution", one ICML 2025
position paper explicitly proposes distribution elicitation as the obvious next step for
social simulation, and one ACL 2026 paper runs our comparison at the individual level on
32M responses and concludes that *point* elicitation wins.

**Already known (do not claim):**
1. Taking the **mean of the elicited judgment distribution beats taking the mode**, stated
   as a headline result and verified in 92/120 settings. **Wang, Zhang & Choi, Findings of
   EMNLP 2025.** Same paper also finds CoT collapses the distribution's spread and often
   hurts — which pre-empts our v1 observation too.
2. LLMs asked for one integer bunch on a few values, destroying variance and correlation
   with humans; a probability-weighted score over the scale points fixes it. **G-Eval
   (EMNLP 2023)**, **Licht et al. (EMNLP 2025)**, **Zawistowski (2024)**.
3. Verbalized distributions beat token log-probs for instruction-tuned models.
   **Meister et al. (NAACL 2025)**, corroborated by **SimBench (2025/26)**.
4. Distribution elicitation beats point-and-aggregate for survey simulation at the
   population level, decisively. **Gong, Sanders & Schneier (2026)**; **Maier et al.
   (2025)**; **Verbalized Sampling (2025)**.
5. Distribution methods win at the *population* level and point methods win at the
   *individual* level. **Ahnert et al. (ACL 2026).**
6. Distribution elicitation for social simulation has already been *proposed in print* as
   an underdeveloped direction. **Anthis et al., ICML 2025 position paper:** "there has
   been less development of distribution elicitation than individual-based methods."

**What is left that is arguably ours:**
- The **conjunction**: individual target + elicited distribution + expected-value scoring
  on an ordinal scale + lift over a zero-information baseline. No paper found runs all
  four. Ahnert et al. come closest and collapse the distribution to **argmax** before
  scoring macro-F1 — they never score an expected value. Their categorical datasets
  (vote choice) make expected value meaningless; their one ordinal dataset (ATP 2021,
  5-point Likert) shows no significant difference either way.
- Distribution-over-Likert for **psychometric prediction of a specific person** appears
  genuinely open; the perspectivist annotation literature (LeWiDi-2025) predicts a *hard
  label per annotator* and never a distribution per annotator scored by expected value.

**The reviewer objection we must answer.** Switching from argmax accuracy to
expected-value MAE changes the loss function, and expected value is Bayes-optimal under
absolute error — so it can beat a mode almost mechanically on an ordinal scale. Our
defence is that lift is a *within-variant* difference: both arms are parsed and scored
identically inside a variant (confirmed in `src/doppler/scoring.py`, `parse_v2` — expected
value drives MAE for twin and baseline alike). But that defence is not sufficient on its
own, for the reason in the next section.

## Honesty check on our own numbers — two problems, one of them serious

**Problem 1: the claim is singular, not plural.** The brief says "open models' lift
positive where point-prediction fails". Qwen's v2 lift is **+0.003, p = .899 — null**, and
`results/qwen_failure_note.md` records why (under v2 Qwen emitted only 32 unique
probability strings across 500 twin cells; it copied canned distributions). On lift, the
claim rests on **Gemma-4-31B alone**, n = 50, uncorrected.

**Problem 2 (serious): some of our lift is baseline degradation, not twin improvement.**
Pulled from the run summaries (`results/pilot2_v*/summary.json`):

| model | variant | twin MAE | baseline MAE | lift |
|---|---|---|---|---|
| gemini | v0 | 1.3660 | 1.4380 | +0.072 |
| gemini | v1 | 1.4680 | 1.6160 | **+0.148** |
| gemini | v2 | 1.4296 | 1.5203 | +0.091 |
| gemini | v3 | **1.3340** | 1.4240 | +0.090 |
| gemma | v0 | 1.4960 | 1.4400 | -0.056 |
| gemma | v1 | 1.5760 | 1.5140 | -0.062 |
| gemma | v2 | **1.3843** | 1.4697 | **+0.085** |
| gemma | v3 | 1.4520 | 1.4360 | -0.016 |
| qwen | v0 | 1.5160 | 1.4280 | -0.088 |
| qwen | v1 | 1.7060 | 1.5880 | -0.118 |
| qwen | v2 | 1.4374 | 1.4407 | +0.003 |
| qwen | v3 | **1.4240** | 1.4260 | +0.002 |

Read the twin column, not the lift column:

- **Gemini's largest lift (v1, +0.148) comes from its *second-worst* twin (1.468).** The
  v1 baseline collapsed to 1.616 from 1.438. That lift is manufactured by damaging the
  baseline. Gemini's genuinely best twin is v3 (1.334). Any headline built on Gemini v1
  lift is measuring the wrong thing, and this is exactly the artifact Yang (2026) reports
  for count-based F1.
- **Gemini v2 also makes the twin worse in absolute terms** (1.4296 vs 1.366 at v0). So
  "distribution elicitation helps" is *false* for Gemini on absolute error; it only looks
  true through the lift lens.
- **Gemma v2 is the real result.** Twin MAE drops from 1.496 to 1.3843 — the best twin
  Gemma produces under any variant — while the baseline is flat-to-worse. Both the
  absolute and the relative number move the right way.
- **Qwen's twin also genuinely improves under v2** (1.516 → 1.4374) and under v3
  (1.516 → 1.4240). Its lift stays ~0 only because its baseline is strong.

**The better framing, which the data actually supports:** *distribution elicitation
improves the twin's absolute accuracy for both open models (Qwen 1.516 → 1.437, Gemma
1.496 → 1.384) and for neither of them under point elicitation; only for Gemma does the
gain outrun the baseline. For Gemini it makes the twin worse.* That is a defensible
sentence. "Distribution elicitation rescues open models' lift" is not.

**Recommendation: report twin MAE alongside every lift number, in every table.** Lift is
the right primary metric per the preregistration, but a variant that degrades the baseline
inflates lift for free, and we have a live example of it (Gemini v1). This costs nothing
and closes an obvious referee attack.

## Closest prior work, ranked by proximity

1. **Ahnert, G., Haensch, A.-C., Plank, B., & Strohmaier, M. (2026).** "Survey Response
   Generation: Generating Closed-Ended Survey Responses In-Silico with Large Language
   Models." ACL 2026. arXiv:2510.11586. https://aclanthology.org/2026.acl-long.1927/
   — **The paper to beat.** 8 elicitation methods x 4 surveys x 10 open-weight models,
   32M simulated responses. Methods include a **Verbalized Distribution Method** (JSON
   probability over every response option, per individual, following Meister et al.) and
   an **Open-Ended Distribution Method**, against **Restricted Choice** (single point
   answer in JSON with a constrained vocabulary) and token-probability methods. They
   evaluate **individual-level alignment** (macro-F1 vs that person's actual answer)
   *and* subpopulation-level, with a **stratified shuffle baseline** and a random-forest
   "achievable alignment" ceiling.
   **Overlap:** this is our comparison, at 400x the scale, with a baseline and a ceiling.
   Their headline: *Restricted Generation Methods perform best overall*; Verbalized
   Distribution is best at the **subpopulation** level (Table 6) but is beaten by
   Restricted Choice at the **individual** level (Table 3: e.g. GLES2017 .233 vs .242;
   Table 7 normalized: 1.443 vs 1.535). They also find **reasoning output does not
   consistently improve alignment** — same direction as our v1 result for open models.
   **Non-overlap:** they argmax the distribution for individual scoring; we take its
   expected value on an ordinal scale and score MAE. They use political-attitude surveys
   with a persona of demographics only; we predict cross-domain from 48 revealed items.
   Their baseline is a shuffled-human-responses baseline, not a same-model
   zero-information arm.

2. **Meister, N., Guestrin, C., & Hashimoto, T. (2025).** "Benchmarking Distributional
   Alignment of Large Language Models." NAACL 2025. arXiv:2411.05403.
   https://aclanthology.org/2025.naacl-long.2/
   — Isolates the *distribution expression method* as a variable: log-probabilities vs
   emitting a sequence of samples vs **verbalizing the distribution**. Verbalization is
   best, log-probs worst; verbalized distributions do not show the log-prob
   miscalibration.
   **Overlap:** establishes verbalized distributions as the right elicitation format —
   our v2 is their method.
   **Non-overlap:** entirely **group-level** (matching a demographic group's opinion
   distribution). No individual prediction, no lift over a no-information baseline.

3. **Wang, V., Zhang, M. J. Q., & Choi, E. (2025).** "Improving LLM-as-a-Judge Inference
   with the Judgment Distribution." Findings of EMNLP 2025. arXiv:2503.03064.
   https://arxiv.org/abs/2503.03064
   — **Our mechanism as someone else's headline.** "Taking the mean of the judgment
   distribution consistently outperforms taking the mode (i.e. greedy decoding) in all
   evaluation settings (pointwise, pairwise, listwise)" — mean beats mode in 92/120 cases
   on RewardBench and MT-Bench. Also reports that **CoT collapses the spread of the
   distribution and often hurts**, which independently predicts our v1 result.
   **Overlap:** mean-of-distribution vs mode, stated generally.
   **Non-overlap:** judging text quality against pooled human preference labels; no
   persona, no individual target, no zero-information baseline.

4. **Gong, E., Sanders, N. E., & Schneier, B. (2026).** "Characterizing the ability of LLMs
   to recapitulate Americans' distributional responses to public opinion polling questions
   across political issues." arXiv:2603.20229. https://arxiv.org/abs/2603.20229
   — The cleanest published **point-vs-distribution elicitation contrast** in survey
   simulation. "Single Individual" (roleplay one member, one option, repeat 20x and
   aggregate) vs "Direct Distribution" (one call, state the numerical distribution).
   Direct Distribution wins: lower mean difference in 72.7% of 1,680 question x demographic
   cells, better conformity in 77.3%; the point method systematically over-estimates
   homogeneity.
   **Overlap:** the elicitation contrast, and the "point elicitation under-disperses"
   diagnosis.
   **Non-overlap:** no individual-level analysis at all; no zero-information baseline.

5. **Peng, T., Gui, G., Merlau, D., et al. (2025/2026).** "Digital Twins as Funhouse
   Mirrors: Five Key Distortions." arXiv:2509.19088; SSRN 5518418.
   https://arxiv.org/abs/2509.19088
   — 19 pre-registered studies, 164 outcomes, twins conditioned on 500+ prior answers per
   person. Individual accuracy scored against a **uniform-random benchmark of 0.629**;
   twins are "only modestly more accurate than a homogeneous base LLM", mean r ≈ 0.20 with
   humans, and adding rich personal information does not move individual accuracy
   (p = 0.37). **94% of outcomes show under-dispersion.**
   **Overlap:** our best published support for "point elicitation barely beats
   zero-information", with a proper baseline, at far larger scale. The under-dispersion
   result is exactly the failure a distribution arm should fix — but they never run one.
   **Non-overlap:** point elicitation throughout; no distribution arm.

6. **Liu, Y., Iter, D., Xu, Y., Wang, S., Xu, R., & Zhu, C. (2023).** "G-Eval: NLG
   Evaluation using GPT-4 with Better Human Alignment." EMNLP 2023. arXiv:2303.16634.
   https://aclanthology.org/2023.emnlp-main.153/
   — The canonical statement of our mechanism, three years old: LLMs output integer
   scores, "one digit usually dominates the distribution ... which leads to low variance
   of the scores and low correlation with human judgments", so take the
   **probability-weighted sum over the scale points**.
   **Overlap:** the exact diagnosis and the exact fix (expected value over a distribution
   on a rating scale).
   **Non-overlap:** LLM-as-judge on summarization; uses token log-probs, not a verbalized
   distribution; no human-simulation, no per-person target.

7. **Licht, H., et al. (2025).** "Measuring Scalar Constructs in Social Science with LLMs."
   EMNLP 2025. arXiv:2509.03116. https://aclanthology.org/2025.emnlp-main.1635/
   — Head-to-head of four ways to get a scalar out of an LLM: direct pointwise scoring,
   pairwise-comparison aggregation, **token-probability-weighted pointwise scoring**, and
   finetuning. Direct scoring "bunches around arbitrary values"; pairwise beats it;
   **probability-weighted expected value beats both**.
   **Overlap:** the ranking we claim (distribution-expected-value > forced point), with a
   proper comparison, on ordinal scales.
   **Non-overlap:** the target is a property of a *text*, not a *person*'s answer; no
   persona conditioning; no baseline-lift metric.

8. **Zawistowski, K. (2024).** "Unused information in token probability distribution of
   generative LLM: improving LLM reading comprehension through calculation of expected
   values." FEDCSIS 2024. arXiv:2406.10267. https://arxiv.org/abs/2406.10267
   — Expected value over the next-token distribution instead of greedy decoding, on
   Likert-scale scoring (SummEval). Gains are dramatic for the weaker model
   (Mistral-7B 6-8% → 13-28%) and smaller for the stronger one (Mixtral 20-46% → 37-56%).
   **Overlap:** expected value beats argmax on a Likert task, **and the model-strength
   interaction we observe**.
   **Non-overlap:** token probabilities, not verbalized; judging, not person simulation.

9. **Maier, B. F., Aslak, U., Fiaschi, L., et al. (2025).** "LLMs Reproduce Human Purchase
   Intent via Semantic Similarity Elicitation of Likert Ratings." arXiv:2510.08338.
   https://arxiv.org/abs/2510.08338
   — Opens with our premise verbatim: LLMs "produce unrealistic response distributions
   when asked directly for numerical ratings". Their fix (SSR) elicits *text*, then maps
   it to a **probability distribution over the 1-5 scale per synthetic respondent** via
   embedding similarity to reference statements. Explicitly benchmarked **against the
   point method** (Direct Likert Rating): DLR collapses onto "3", KS similarity 0.26
   (GPT-4o) / 0.39 (Gemini) versus 0.88 / 0.80 for SSR; correlation attainment ~80% → 90%.
   9,300 human responses, 57 surveys.
   **Overlap:** avoid the forced integer, produce a distribution over Likert points, and
   the direct-numeric-elicitation failure is the motivation. Also an interesting cousin of
   our v3 fix — both replace numbers with words, ours on the input side, theirs on the
   output side.
   **Non-overlap:** the headline metric is distribution realism and test-retest
   reliability, not per-person accuracy against a zero-information baseline.

10. **Anthis, J. R., Liu, R., Richardson, S. M., et al. (2025).** "LLM Social Simulations
    Are a Promising Research Method." ICML 2025 (Position). arXiv:2504.02234.
    https://arxiv.org/abs/2504.02234
    — **Matters for framing.** Explicitly proposes our intervention as future work:
    "Instead of prompting the LLM to generate one human's data in each forward pass,
    researchers can prompt the LLM to generate a distribution of human data... there has
    been less development of distribution elicitation than individual-based methods."
    No experiments. Cite it as the open call our work answers — and note it frames
    distribution elicitation at the *population* level, so the individual-level twist is
    still ours.

11. **Individual-level, point elicitation only (the "point is weak" evidence — but note
    half of it cuts against us):**
    - Peng et al. 2509.19088 (above) — supports "point ≈ baseline".
    - Miranda, F., & Balbi, P. P. (2025). "Simulating Public Opinion: Comparing
      Distributional and Individual-Level Predictions from LLMs and Random Forests."
      *Entropy* 27(9), 923. doi:10.3390/e27090923.
      https://pmc.ncbi.nlm.nih.gov/articles/PMC12468613/ — scores individual (F1, Cramér's
      V) *and* distributional (JSD) with **uniform-random and constant/modal-class
      baselines**. **Cuts against us:** their point-elicited LLM clearly beats both
      baselines (climate change F1 0.59 vs 0.36 random / 0.41 constant).
    - Kinzinger, L., & Hartmann, J. (2026). "Synthetic Personalities: How Well Can LLMs
      Mimic Individual Respondents Using Socio-Economic Microdata?" arXiv:2606.04592.
      https://arxiv.org/abs/2606.04592 — 2.1M twin responses, 500 participants, 183
      held-out questions, **empty-persona ablation as the zero-information baseline**
      (flat 0.65-0.66). **Cuts against us:** point elicitation gains +4.2 to +10.8 pp over
      baseline as persona depth grows.
    - Ku, C.-T., et al. (2026). "Silicon Sampling via Cross-Survey Transfer."
      arXiv:2607.03091. https://arxiv.org/abs/2607.03091 — makes our individual-vs-aggregate
      argument in print: "most evaluations rely on distributional comparisons rather than
      individual-level prediction, which risks conflating pattern matching with coherent
      respondent-level prediction."
    - Choi, E. C., et al. (2026). "Beyond the Mean: Three-Axis Fidelity for Aligning
      LLM-Based Survey Simulators from Small Pilot Data." arXiv:2606.28963.
      https://arxiv.org/abs/2606.28963 — decomposes fidelity into structural / marginal /
      individual axes; 4-point Likert, point answers, explicitly does not evaluate
      calibration of a distribution over options.
    - Kim, J., & Lee, B. (2023/2024). "AI-Augmented Surveys: Leveraging LLMs and Surveys
      for Opinion Prediction." arXiv:2305.09620. https://arxiv.org/abs/2305.09620 —
      individual-level and genuinely probabilistic (AUC 0.87), but the probability comes
      from a **fine-tuned** model, not from elicitation; no point-vs-distribution contrast.

12. **Aggregate distributional-alignment line (context, not competition — all group-level):**
    - Santurkar, S., Durmus, E., Ladhak, F., Lee, C., Liang, P., & Hashimoto, T. (2023).
      "Whose Opinions Do Language Models Reflect?" ICML 2023. arXiv:2303.17548.
      https://arxiv.org/abs/2303.17548 — OpinionQA; the origin of the aggregate framing we
      are pushing against.
    - Hu, T., Baumann, J., Lupo, L., Collier, N., Hovy, D., & Röttger, P. (2025/2026).
      "SimBench: Benchmarking the Ability of LLMs to Simulate Human Behaviors."
      arXiv:2510.17516. https://arxiv.org/abs/2510.17516 — **the metric precedent to
      follow**: score = normalized lift of TVD over a uniform baseline. Also confirms
      verbalized distributions beat direct token probabilities for instruction-tuned
      models.
    - Zhang, J., Yu, S., Chong, D., et al. (2025). "Verbalized Sampling: How to Mitigate
      Mode Collapse and Unlock LLM Diversity." arXiv:2510.01171.
      https://arxiv.org/abs/2510.01171 — ask for k candidates *with probabilities*; the
      human-simulation experiment beats direct prompting on KS distance, but it is
      population distributional fit, not per-person accuracy.
    - Kambhatla, G., et al. (2025/2026). "Improving the Distributional Alignment of LLMs
      using Supervision." arXiv:2507.00439. https://arxiv.org/abs/2507.00439 — contains
      the line closest to our wording, "explicit probability modeling substantially
      outperforms the one-hot method", but "one-hot" means a subpopulation's modal
      response, so the comparison is subpopulation-level.
    - Sun, S., et al. (2024). "Random Silicon Sampling." arXiv:2402.18144.
    - Cao, Y. T., Liu, H., et al. (2025). "Specializing LLMs to Simulate Survey Response
      Distributions for Global Populations." NAACL 2025. arXiv:2502.07068.
    - Bradshaw, C., Miller, C., & Warnick, S. (2024). "LLM Generated Distribution-Based
      Prediction of US Electoral Results, Part I." arXiv:2411.03486.

13. **Yang, I. Y., & Zhang, D. Y. (2025).** "Failure to Mix: Large language models struggle
    to answer according to desired probability distributions." arXiv:2511.14630.
    https://arxiv.org/abs/2511.14630
    — Models asked to emit "1" 49% of the time emit "0" ~100% of the time. Two uses for
    us: it documents that *sampling* a point answer is degenerate (supporting our premise),
    and it is an argument **against** over-trusting verbalized probabilities. Also the
    published context for the Qwen v2 canned-distribution artifact in
    `results/qwen_failure_note.md` — that is documented model behaviour, not a harness bug.

14. **Calibration / verbalized confidence (mechanism-adjacent; these concern the model's
    uncertainty about *its own* correctness, not about another person's answer):**
    - Lin, S., Hilton, J., & Evans, O. (2022). "Teaching Models to Express Their
      Uncertainty in Words." TMLR. arXiv:2205.14334.
    - Tian, K., Mitchell, E., Zhou, A., et al. (2023). "Just Ask for Calibration." EMNLP
      2023. arXiv:2305.14975 — RLHF wrecks logprob calibration, **verbalized** confidence
      is better calibrated (~50% relative ECE reduction). Direct support for our choice to
      verbalize rather than read logits.
    - Xiong, M., et al. (2024). "Can LLMs Express Their Uncertainty?" ICLR 2024.
      arXiv:2306.13063.
    - Hu, J., & Levy, R. (2023). "Prompting is not a substitute for probability
      measurements in large language models." EMNLP 2023. arXiv:2305.13264 — **the
      counterweight**: direct probability read-out beats metalinguistic prompting. Points
      the opposite way from Tian et al. and SimBench; expect it as a referee question.
    - Cruz, A. F., & Hardt, M. (2024). "Evaluating language models as risk scores." NeurIPS
      2024. arXiv:2407.14614 — closest published thing to "elicit a probability about a
      specific person and score it properly"; verbalized chat-style risk queries improve
      calibration. Binary outcomes, prediction *about* people rather than simulation *of*
      them.
    - Ren, K., et al. (2025). "Predicting Language Models' Success at Zero-Shot
      Probabilistic Prediction." Findings of EMNLP 2025. arXiv:2509.15356.

15. **Annotator disagreement / soft labels — a real, adjacent gap:**
    - Leonardelli, E., et al. (2025). "LeWiDi-2025: Third Edition of the Learning with
      Disagreements Shared Task." NLPerspectives @ EMNLP 2025. arXiv:2510.08460.
      https://aclanthology.org/2025.nlperspectives-1.16/ — the cleanest split between
      soft-label (population) and perspectivist (individual annotator) paradigms.
      **Task B systems output hard labels per annotator**, scored with random and
      most-frequent baselines. **Nobody predicted a distribution per individual annotator
      and scored its expected value.** That is our gap, in a shared task with published
      baselines — an obvious second testbed.
    - Lee, N., An, N. M., & Thorne, J. (2023). "Can Large Language Models Capture
      Dissenting Human Voices?" EMNLP 2023. arXiv:2305.13788 — Monte Carlo (sample-and-
      aggregate) vs log-probability estimation of the *annotator pool's* distribution.
    - Sorensen, T., & Choi, Y. (2025). "Opt-ICL at LeWiDi-2025." arXiv:2510.07105 (Task B
      winner; point predictions per annotator).
    - Ignatev, D., et al. (2025). "DeMeVa at LeWiDi-2025: Modeling Perspectives with
      In-Context Learning and Label Distribution Learning." arXiv:2509.09524.
    - Orlikowski, M., Pei, J., Röttger, P., et al. (2025). "Beyond Demographics:
      Fine-tuning LLMs to Predict Individuals' Subjective Text Perceptions." ACL 2025.
      arXiv:2502.20897.

16. **One paper neither pass could verify — check by hand before claiming novelty:**
    arXiv:2602.19403, "Personalized Prediction of Perceived Message Effectiveness Using
    LLM-Based Digital Twins." Individual-level and Likert-based; the elicitation format
    could not be confirmed (PDF would not parse).

## Suggested citation list for Claim B write-ups

Must-cite (or the claim looks naive): **Ahnert et al. ACL 2026 (2510.11586)** — engage
head-on; **Wang, Zhang & Choi, Findings EMNLP 2025 (2503.03064)**; Meister et al. NAACL
2025 (2411.05403); G-Eval, Liu et al. EMNLP 2023 (2303.16634); Licht et al. EMNLP 2025
(2509.03116); **Anthis et al. ICML 2025 (2504.02234)** as the open call.
Should-cite: Gong et al. 2026 (2603.20229); Peng et al. 2025/26 (2509.19088); Maier et al.
2025 (2510.08338); Zawistowski 2024 (2406.10267); SimBench (2510.17516) for the
lift-over-uniform metric precedent; "Failure to Mix" (2511.14630).
Must-acknowledge as contrary evidence: Miranda & Balbi (*Entropy* 2025); Kinzinger &
Hartmann 2026 (2606.04592) — both report point elicitation beating a zero-information
baseline at the individual level.
Background: Santurkar et al. ICML 2023; Tian et al. 2023; Hu & Levy 2023 (the "why not
logprobs?" challenge); LeWiDi-2025 (2510.08460) as a second testbed.

---

# How this should change the two notes

1. **`finding_scale_anchoring.md` — retitle the contribution, and drop the "cross-scale"
   novelty.** The section "Why this matters for anyone building persona agents" currently
   presents "numbers in the profile act as anchors on numbers in the output" as the
   discovery. That is Harris & Speekenbrink (2016) for humans and the LLM anchoring line
   for models. Restate the contribution as: *anchoring on legitimate persona data is large
   enough to invert lift over a zero-information baseline, and the fix is to re-render the
   input numbers as words.* Add a short related-work paragraph citing Harris &
   Speekenbrink 2016 first, and note the disagreement with 2505.15392 on reasoning.
2. **The digits→words fix is the strongest part of Claim A — lead with it.** Two searches
   (mine and the breadth agent's 47) found no paper that debiases anchoring by re-rendering
   input numbers as words. The published LLM mitigation work is instruction-level and
   reports failure; the nearest survey-simulation fix (SSR, 2510.08338; 2602.13862)
   de-numerifies the *output*. Human survey methodology already shows numeric labels change
   responses (Bottoni & Aizpurua 2026), so the intervention is principled, not a hack.
   Say all of this explicitly.
3. **`pilot2_comparison.md` — add a twin-MAE column, and stop leading with Gemini v1.**
   The single most important thing this review turned up is in our own numbers, not in the
   literature: **Gemini's largest lift (v1, +0.148) comes from a twin that is worse in
   absolute terms than its v0 twin (1.468 vs 1.366); the lift exists because the v1
   baseline degraded to 1.616.** A variant that damages the baseline manufactures lift for
   free. Lift stays the primary metric per the preregistration, but every lift number
   should be reported next to its twin MAE and baseline MAE so this is visible. This is
   the same measurement artifact Yang (2026) documents for count-based F1.
4. **Any v2 claim — downgrade and re-scope.** Ahnert et al. (ACL 2026) already ran the
   individual-level point-vs-distribution comparison on 32M responses and found point
   elicitation better; Wang, Zhang & Choi (2025) already published "mean beats mode"; and
   Anthis et al. (ICML 2025) already proposed distribution elicitation for social
   simulation in print. What is left is the conjunction plus the ordinal expected-value
   scoring rule. On our own data: Gemma is the only model where v2 lift is positive and
   significant, though **both** open models' twins improve in absolute MAE under v2.
   Present v2 as a *design choice justified by the gate*, not as a finding.
5. **The cheap experiment that would make Claim B defensible** — score the *same* v2
   outputs two ways, argmax vs expected value, and report lift for each. That isolates
   precisely the thing Ahnert et al. did not test, on their own terms, at zero extra API
   cost. `src/doppler/scoring.py::parse_v2` already returns both `ev` and `argmax`, so
   this is a re-scoring pass over existing records, not a new run. Strongly recommend
   before any v2 claim leaves the repo.
6. **Update the Park et al. citation.** arXiv:2411.10109 was retitled in v3 (June 2026) to
   "LLM Agents Grounded in Self-Reports Enable General-Purpose Simulation of Individuals",
   and the headline is now 83-86% of test-retest consistency. PREREGISTRATION.md §1 cites
   the old title and the 0.85 figure.
7. **Two datasets worth noting for later stages.** Twin-2K-500 (2505.17479) has 500+ items
   per person and a test-retest ceiling, and ablates a dozen prompting variants but never
   distribution-vs-point — it is the obvious external replication for both claims.
   LeWiDi-2025 (2510.08460) supplies individual annotators with published random and
   most-frequent baselines, and nobody there predicted a per-annotator distribution.

---

# Search queries run (for reproducibility)

Run 2026-07-24 via WebSearch (US region) and WebFetch on arXiv/ACL Anthology.

**Claim A:**
1. anchoring bias in large language models numeric values in prompt
2. numeric anchoring LLM survey response simulation persona rating scale
3. LLM annotator rating scale bias Likert numbers in context
4. LLM recommender system predict user rating anchoring on ratings in prompt history bias
5. digits versus words numeric representation prompt LLM bias verbalize numbers mitigation
6. cross-scale contamination LLM output scale different from input scale rating bias
7. LLM as judge anchoring on reference score shown in prompt biases rating
8. assimilation effect numeric response scale prior ratings carryover questionnaire psychology
9. LLM copies numbers from context into its rating output leakage numeric context Likert answer
10. "anchoring" LLM persona profile attributes numeric bias survey simulation digital twin
11. Wilson 1996 basic anchoring effects incidental numbers unrelated estimates psychology
12. mitigate anchoring LLM by removing numbers from prompt replacing with verbal labels debiasing
13. LLM response scale mismatch 1-5 input scale 1-7 output scale conversion error prompt
14. LLM persona agent worse than demographic-only baseline individual prediction lift over baseline
15. Tjuatja do LLMs exhibit human-like response biases survey design
16. generative agent simulations of 1000 people interview predict survey responses normalized accuracy
17. Twin-2K-500 dataset digital twins 2000 people 500 questions LLM persona prediction

**Claim B:**
18. Benchmarking Distributional Alignment of Large Language Models verbalized distribution
19. "verbalized sampling" mode collapse LLM distribution diversity
20. LLM predict individual survey responses probability distribution over options expected value better than point prediction
21. "survey response generation" in-silico LLM closed-ended distribution elicitation methods comparison 2510.11586
22. Licht 2025 annotating scalar constructs with LLMs token probability-weighted scores pairwise comparison
23. G-Eval token probability weighted score integer scores low variance NLG evaluation Liu 2023
24. expected value of elicited distribution over Likert options mean absolute error simulate individual respondent LLM

Full text read: arXiv:2510.11586v2 (pp. 1-8). Abstracts/pages fetched: 2510.08338,
2506.22316, 2406.10267, 2411.10109, 2506.22316.

**Second-pass breadth search on Claim A** (delegated; 47 further queries, ~15 sources
fetched). Additional queries beyond those above:

cross-scale anchoring persona attributes numeric values contaminate LLM Likert output
different scale · verbal labels instead of numbers mitigate anchoring LLM prompt rating
words not digits · "Interpreting Multi-Attribute Confounding" numerical attributes ·
star ratings in prompt bias LLM personality questionnaire answers different scale
spillover · numbers in context leak into unrelated numeric answers LLM "different scale"
anchoring contamination · LLM judge score format words versus numeric labels changes score
distribution verbal rubric · persona demographic numbers age income bias LLM numeric survey
answers anchoring profile · threshold priming batch relevance assessment LLM prior scores
bias subsequent judgments · anchor number different unit transfers LLM estimate
"cross-domain" anchoring semantic priming numeric · "cross-scale" anchoring large language
models numeric anchor different scale target judgment · LLM simulated respondent prior
survey answers in prompt bias later Likert responses carryover numeric · "Between two
minds" numerical labels survey responses cross-national · LLM predicts user movie rating
history 1-5 stars in prompt biases output distribution anchoring recommendation · writing
numbers as words instead of numerals reduces anchoring bias language model number format
prompt · "silicon sampling" OR "LLM twin" persona numeric attributes anchoring bias survey
response scale mismatch · aclanthology anchoring effect persona conditioned language model
numeric context bias rating scale · magnitude of numbers in prompt influences unrelated
rating output LLM "number format" mitigation textual · "Prompt Perturbations Reveal
Human-Like Biases in LLM Survey Responses" · LLM annotation numeric scale in prompt biases
output "anchoring" reference rating shown few-shot examples scores · persona prompt
containing past ratings biases LLM questionnaire response distribution shift digital twin
fidelity artifact · "scale distortion" OR "numeric priming" theory applied to language
models anchoring different response scale units · "Prompt Framing Distorts Count-Based
Evaluation" numeric anchoring · "Localizing Anchoring Pathways in Language Models" ·
"Grading Scale Impact on LLM-as-a-Judge" · "Algorithmic Anchoring" Garcia SSRN
prompt-embedded reference points LLM financial estimates.

**Second-pass breadth search on Claim B** (delegated; 55 further queries, ~21 sources
fetched). Additional queries beyond those above:

LLM simulate individual survey respondent probability distribution over answer options
versus point prediction · individual-level prediction LLM silicon sampling accuracy
baseline lift modal response · expected value scoring Likert token probability LLM judge
weighted average rating soft score · LLM predict individual annotator label distribution
per-annotator soft labels · digital twin LLM predict individual person's survey answers
probability distribution beats baseline lift · "zero-information baseline" OR
"no-information baseline" LLM persona prediction individual survey answer lift over
baseline · asking LLM for percentage breakdown across answer options instead of single
answer improves individual prediction survey · LLM persona individual-level accuracy no
better than chance majority baseline survey prediction negative result · LeWiDi 2025 shared
task learning with disagreement perspectivist individual annotator prediction soft label ·
soft label per individual annotator LLM distribution better than hard label prediction
Wasserstein individual perspectivist · "expected value" OR "probability weighted"
elicitation improves prediction of individual respondent Likert rating LLM twin ·
verbalized sampling persona dialogue simulation individual human behavior prediction
accuracy improvement · LLM twin individual accuracy point estimate fails distribution
elicitation recovers signal preregistration · "LLM-as-an-expert" versus "LLM-as-a-subject"
distribution elicitation social simulation Anthis · predicting how a specific person
answers asking model for probabilities over options outperforms asking for the answer ·
LLM survey simulation compare argmax single answer versus full response distribution
individual accuracy ANES persona · "individual-level" LLM opinion prediction "probability
distribution" prompt elicits improves over "most likely answer" · predict individual's
questionnaire item responses LLM distribution over Likert options psychometric personality
expected score · Toubia Gui Peng digital twins LLM individual level accuracy elicitation
format probability distribution prompting strategies · Mega-Study digital twins funhouse
mirrors distortions LLM individual prediction elicitation methods · first-token probability
versus verbalized distribution individual respondent prediction accuracy comparison survey
LLM ablation · score LLM by probability assigned to the true answer of an individual
respondent log score Brier survey simulation · "Evaluating language models as risk scores"
Cruz individual-level probabilistic predictions calibration folktables · "Improving
LLM-as-a-Judge Inference with the Judgment Distribution".

**Own-data checks run during this review** (not literature): read
`src/doppler/scoring.py` to confirm v2 scores expected value for *both* arms; extracted
twin and baseline MAE from all twelve `results/pilot2_v*/summary.json` to test whether v2
lift reflects twin improvement or baseline degradation. It reflects both, depending on the
model — see the table above.

**Known search limits.** SSRN 6366838 and the MDPI *Publications* article returned 403 to
automated fetching; both entries rest on search snippets. Several 2026 arXiv items were
verified from abstract pages rather than full PDFs. "Nothing found" here is bounded by
keyword coverage — a paper framed as, say, "profile-field leakage" or "attribute magnitude
spillover" could exist in wording neither pass hit.
