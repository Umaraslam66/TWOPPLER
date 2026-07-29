# DOPPLER — citation verification and discovery memo

Date: 2026-07-29. Scope: every external published work referenced in
`results/writeups/PAPER1_METHODS.md`, `results/writeups/PAPER2_MAIN.md`,
`results/writeups/ARTICLE.md` and `results/lit_check.md`, plus new citations a
publishable version of the two papers should carry.

Every entry below was confirmed by a live web lookup during this task — arXiv
abstract page, ACL Anthology page, PMLR/NeurIPS proceedings page, publisher DOI
page, or (for models) the official model card. Anything that could not be
confirmed is quarantined in the "unverified — do not use" list at the end of each
part.

---

## Read this first — the ten things that actually need action

1. **MediaSum is never cited.** It is the corpus for every number in both papers.
   Add Zhu et al. (2021) and, for the NPR half, Majumder et al. (2020). (§A1.6)
2. **The Park et al. citation is wrong in four ways** — stale title, two missing
   authors, the 0.85 figure should be 0.83 for the interview-grounded arm, and
   their own 74% demographics-only baseline should be quoted beside it. (§A1.4)
3. **Chandak et al. (2025), arXiv:2507.02856** ran Paper 1's whole arc first
   (MCQ is leaky → replace with open generation graded against a reference).
   Paper 1 must cite it and restate its own contribution against it. (§B2)
4. **Reinhart et al. (2025, PNAS)** is the published mechanism for Paper 1's
   register tell — and it says instruction tuning makes the human/LLM style gap
   *larger*, which is exactly why round 4's fix inverted the tell. (§B2)
5. **Morocho et al. (2026), arXiv:2602.18462** is the closest published statement
   of Paper 2's strangest result: persona conditioning can be worse than no
   conditioning, with a proper baseline, on 70K+ instances. (§B6)
6. **Aggazzotti et al. (2024, TACL)** already showed that apparent speaker signal
   in transcripts is largely topic, and vanishes as topic is controlled. It is the
   best prior art for both Paper 1's topical-coherence tell and Paper 2's
   channel-1 topicality caveat. (§B4)
7. **Choi et al. (2010)** found in 2010 that a good static short form is only
   marginally worse than computerized adaptive testing. Paper 1's Stage 1E
   contribution has to be positioned against that, not presented as new. (§B7)
8. **Paper 2 §11 (ethics) has no external anchor at all.** Eight verified sources
   are supplied, including the Stanford HAI governance brief that is the companion
   to the very paper DOPPLER takes as its design target. (§B8)
9. **Nine citation errors in lit_check.md**, two of them wrong first authors
   ("Kizawa" should be Takagi; "Wang, N." does not exist on that paper). (§A2)
10. **A negative finding to keep:** nobody has published on MediaSum's data-quality
    defects. Paper 2's re-airing discovery is original. (§B11)

---

# PART A — verification of citations already in the writeups

## A1. The three writeups

The three writeups cite **8 external works** plus **4 non-paper artifacts**
(a corpus, an embedding model, two model families). Below, each one, verified.

### A1.1 Choudhury et al., BED-LLM — **OK**

Cited in PAPER1 §10 and §14.

> Choudhury, D., Williamson, S., Goliński, A., Miao, N., Bickford Smith, F.,
> Kirchhof, M., Zhang, Y., & Rainforth, T. (2026). *BED-LLM: Intelligent
> Information Gathering with LLMs and Bayesian Experimental Design.* ICLR 2026.
> arXiv:2508.21184. https://arxiv.org/abs/2508.21184

Everything in the writeup's entry checks out: all eight authors in the right
order, exact title, and the arXiv page carries the comment "Published at the
International Conference on Learning Representations 2026".

**One precision note.** The preprint is a **2025** arXiv posting (v1 28 Aug 2025;
v2 18 Oct 2025; v3 20 Apr 2026) that was published at ICLR **2026**. Writing
"(2026)" is defensible as the venue year, but the entry should carry both so a
reader is not surprised by a 2508 identifier. DOI: 10.48550/arXiv.2508.21184.

### A1.2 Wang, Zollo, Zemel & Namkoong — **OK, and the OpinionQA claim is correct**

Cited in PAPER1 §10 and §14.

> Wang, J., Zollo, T., Zemel, R., & Namkoong, H. (2025). *Adaptive Elicitation of
> Latent Information Using Natural Language.* ICML 2025. arXiv:2504.04204.
> https://arxiv.org/abs/2504.04204

Verified: four authors, exact title, ICML 2025, v1 5 Apr 2025 / v2 9 Jul 2025.
The abstract names the three evaluation settings as "the 20 questions game,
dynamic opinion polling, and adaptive student assessment" — so PAPER1's gloss
("evaluated on the Twenty Questions game, adaptive student assessment, and
dynamic opinion polling on OpinionQA") is accurate. The polling task is built on
OpinionQA (1,498 multiple-choice political questions, 60 US demographic groups),
which confirms the cross-reference to Santurkar et al.

**Optional addition:** the ICML proceedings record is
https://dl.acm.org/doi/10.5555/3780338.3782961 (Proc. 42nd ICML), and there is an
OpenReview page (id `63c2erbMoc`) plus code at
https://github.com/namkoong-lab/adaptive-elicitation.

### A1.3 Su, Liu & Hu — **OK, exactly as cited**

Cited in PAPER1 §10 and §14.

> Su, R., Liu, Y., & Hu, J. (2026). *Adaptive Interviewing for Persona Simulation
> in LLMs: Evidence-Grounded Reasoning Improves Decision Alignment.* Preprint,
> arXiv:2605.29458. https://arxiv.org/abs/2605.29458

Verified: three authors, exact title, single version submitted 28 May 2026, no
venue comment — so PAPER1's "not peer-reviewed at time of writing" is correct.
The abstract states "follow-up-grounded predictions are more accurate than
core-only grounded ones (45.5% vs. 39.3%)", which is exactly the figure PAPER1
quotes. Nothing to fix.

### A1.4 Park et al. — **FOUR PROBLEMS. This is the one that needs fixing.**

Cited in PAPER1 §2 and §14, in PAPER2 §10, and alluded to in ARTICLE §1.
lit_check.md already flagged part of this on 2026-07-24 (its item 6 under "How
this should change the two notes"), and the writeups drafted on 2026-07-28 still
carry the old version.

The current record (v3, 28 June 2026):

> Park, J. S., Zou, C. Q., Kamphorst, J., Egan, N., Shaw, A., Hill, B. M.,
> Cai, C., Morris, M. R., Liang, P., Willer, R., & Bernstein, M. S. (2026).
> *LLM Agents Grounded in Self-Reports Enable General-Purpose Simulation of
> Individuals.* arXiv:2411.10109. https://arxiv.org/abs/2411.10109
> (v1 15 Nov 2024, as *Generative Agent Simulations of 1,000 People*;
> v2 22 Apr 2026; v3 28 Jun 2026.)

1. **Title is stale.** PAPER1 §2 and §14 use the v1 title. Keep the v1 title as a
   parenthetical ("originally circulated as…") if you want the reader to
   recognise it, but the citation head must be the current title.
2. **Author list is incomplete.** The writeup lists nine authors; the current
   version has eleven. **Jonne Kamphorst** (3rd) and **Niles Egan** (4th) are
   missing from the writeup and both sit ahead of Shaw in the running order.
3. **The 0.85 figure is stale and it is the wrong one for the arm being
   described.** PAPER1 §2 says "an agent grounded in a two-hour interview
   reproduces a person's survey answers at roughly 0.85 of that person's own
   two-week test-retest consistency". The current abstract gives **83%** for the
   interview-only agent, 82% survey-only, 86% combined, against **74%** for
   demographics-only. The interview-grounded arm — the one PAPER1 is describing —
   is **0.83**, not 0.85. PAPER2 §10 repeats "~0.85 normalized accuracy on survey
   replay" and inherits the same error.
4. **The demographics-only baseline is now in the abstract and should be
   quoted.** 74% is the published zero-information-ish comparator. Given that
   DOPPLER's whole thesis is "never report fidelity without its baseline", it is
   worth quoting Park et al.'s own baseline rather than only their headline.

**"Commercialised by Simile" — verified as a fact, but it is not a citation.**
Simile is a real Stanford-spinout company; Joon Sung Park is CEO and co-founder.
There is no paper to cite. If the claim stays in the text, cite the company or a
dated interview (e.g. Sequoia Capital podcast, "Simulating Humans at Scale:
Simile's Joon Sung Park", https://sequoiacap.com/podcast/simulating-humans-at-scale-similes-joon-sung-park/)
and label it as a company claim, not a peer-reviewed result — in particular the
widely-quoted "85% accuracy" attached to Simile's product is a *company* number
on *proprietary behavioural data*, not the 83% in the paper. Do not let the two
85%s merge.

### A1.5 Santurkar et al. — **OK, add the venue detail**

Cited in PAPER1 §14 (and already in lit_check.md).

> Santurkar, S., Durmus, E., Ladhak, F., Lee, C., Liang, P., & Hashimoto, T.
> (2023). *Whose Opinions Do Language Models Reflect?* Proc. 40th International
> Conference on Machine Learning (ICML), PMLR 202:29971–30004. arXiv:2303.17548.
> https://proceedings.mlr.press/v202/santurkar23a.html

Six authors and title are exactly as cited. Two small precision points:
**(a)** the writeup gives no volume/pages — PMLR 202:29971–30004 is available and
should be used for a published venue; **(b)** the paper's own abstract calls the
dataset **"OpinionsQA"** (with the s). "OpinionQA" is the near-universal
shorthand and is fine, but pick one spelling and use it in both papers.

### A1.6 MediaSum — **MISSING CITATION. This is the biggest gap in Part A.**

MediaSum is the corpus for every number in both papers and for the whole article,
and **neither paper cites it.** It is named 6+ times with its statistics quoted.
Required:

> Zhu, C., Liu, Y., Mei, J., & Zeng, M. (2021). *MediaSum: A Large-scale Media
> Interview Dataset for Dialogue Summarization.* Proc. 2021 Conference of the
> North American Chapter of the ACL: Human Language Technologies (NAACL-HLT),
> 5927–5934. arXiv:2103.06410. doi:10.18653/v1/2021.naacl-main.474.
> https://aclanthology.org/2021.naacl-main.474/

Three number checks against the source, since the papers quote statistics:

- **463,596 transcripts.** The paper says "**463.6K**" and never prints the exact
  integer. 463,596 rounds to 463.6K and matches the released file count, so the
  project's figure is right — but it comes from the released data, not from a
  sentence in the paper. Say so, or attribute the figure to the project's own
  `stage2_corpus_recon.md` rather than to Zhu et al.
- **"CNN 414k, NPR 49k."** Correct. The paper gives NPR 49.4K / CNN 414.2K
  (≈10.6% / 89.4%).
- **"2000 to 2020."** Correct for the **CNN** half, which the paper states was
  collected 2000–2020. The **NPR** half is inherited wholesale from the INTERVIEW
  corpus (below), which spans roughly **1999–2019**. So "2000 to 2020" is very
  slightly wrong on the NPR side. Either say "CNN 2000–2020, NPR 1999–2019" or
  attribute the range to the project's own recon of the data it actually used.

**Also required, and also missing** — the NPR half's source corpus:

> Majumder, B. P., Li, S., Ni, J., & McAuley, J. (2020). *Interview: Large-scale
> Modeling of Media Dialog with Discourse Patterns and Knowledge Grounding.*
> Proc. EMNLP 2020, 8129–8141. arXiv:2004.03090.
> doi:10.18653/v1/2020.emnlp-main.653.
> https://aclanthology.org/2020.emnlp-main.653/

105K NPR news-interview conversations with speaker-role annotation. Cite it
wherever MediaSum's provenance is described; MediaSum's NPR portion is this
dataset.

**A negative finding worth recording.** A dedicated search for published work
documenting quality defects in MediaSum or its CNN/NPR scrapes — duplicate or
re-aired transcripts, speaker misattribution in older CNN panel shows, boilerplate
— **found nothing**. PAPER2 §8.5's re-airing discovery (CNN-388758 replaying
CNN-381362) and PAPER1 §11's flagged misattribution risk appear to be original
observations about this corpus. Write them up as such rather than hunting for a
citation that does not exist.

### A1.7 `sentence-transformers/all-mpnet-base-v2` — **verified, and it settles the 384 question**

The Hugging Face model card states verbatim: "By default, input text longer than
**384 word pieces is truncated**." That independently corroborates PAPER1 §9.2's
ruling that 384 — not 512 — is the operative truncation for the pinned encoder.
The card also confirms the base model is `microsoft/mpnet-base`.

The model card is not a citable paper. For a publishable version, cite the two
underlying works:

> Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using
> Siamese BERT-Networks.* Proc. EMNLP-IJCNLP 2019. arXiv:1908.10084.
> https://arxiv.org/abs/1908.10084

> Song, K., Tan, X., Qin, T., Lu, J., & Liu, T.-Y. (2020). *MPNet: Masked and
> Permuted Pre-training for Language Understanding.* Advances in Neural
> Information Processing Systems 33 (NeurIPS 2020), 16857–16867.
> arXiv:2004.09297.
> https://proceedings.neurips.cc/paper/2020/hash/c3a690be93aa602ee2dc0ccab5b7b67e-Abstract.html

…plus the model card itself with the pinned revision `e8c3b32e…` as a footnote.

### A1.8 The scored models — **no citations given; two now exist**

Both papers name `Gemma-4-31B-it`, `gemini-3.5-flash` and
`gemini-3.5-flash-lite` throughout and cite none of them.

> Gemma Team, Google DeepMind (2026). *Gemma 4 Technical Report.*
> arXiv:2607.02770. https://arxiv.org/abs/2607.02770
> (v1 2 Jul 2026, v2 24 Jul 2026. Suite spans 2.3B–31B, dense and MoE,
> open weights, pre-trained and instruction-tuned variants — which covers
> `gemma-4-31B-it`.)

The report was posted **before** these drafts (2026-07-28), so it is citable now.
Note in passing: the project's CLAUDE.md rule "MoE models do not work on Leonardo
— dense only" is consistent with the 31B being the dense member of that suite.

For the Gemini models there is no paper; cite the official model cards:
- https://deepmind.google/models/model-cards/gemini-3-5-flash/
- https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/

Gemini 3.5 Flash shipped 19 May 2026 — worth one line, because it means the judge
model post-dates the corpus by ~5.5 years and pre-dates the run by ~10 weeks.

### A1.9 Statistics used but not cited

- **Cohen's κ** is a pre-registered pass/fail bar in PAPER1 §9.4 and PAPER2 §4.5
  and is never cited.
  > Cohen, J. (1960). *A coefficient of agreement for nominal scales.*
  > Educational and Psychological Measurement, 20(1), 37–46.
  > doi:10.1177/001316446002000104.
  > https://journals.sagepub.com/doi/10.1177/001316446002000104
- **vLLM** — PAPER2 §10 attributes the run-to-run noise floor to "vLLM's batched
  matrix multiplies" and cites nothing.
  > Kwon, W., Li, Z., Zhuang, S., Sheng, Y., Zheng, L., Yu, C. H., Gonzalez, J. E.,
  > Zhang, H., & Stoica, I. (2023). *Efficient Memory Management for Large
  > Language Model Serving with PagedAttention.* SOSP 2023. arXiv:2309.06180.
  > https://arxiv.org/abs/2309.06180

  The *mechanism* citation is new and is in Part B (Yuan et al., arXiv:2506.09501).

### A1.10 The OSF deposit — **not machine-verifiable at time of check**

https://osf.io/qz28m returns a JavaScript shell with no readable registration
metadata to an automated fetch, so title, date, contributors and public status
could not be confirmed externally. This is consistent with the papers' own
statement that the registration sits inside OSF's approval window. Not a
literature problem; recorded so nobody assumes it was checked.

## A2. lit_check.md — problems found

Roughly **75 distinct works** across Claim A and Claim B were re-checked. The
headline is good: **no fabricated papers, no wrong arXiv identifiers, no wrong
venues.** Nine entries need edits, all listed here. Everything not listed
verified clean.

### A2.1 Real errors — fix before any of these is cited

1. **Claim A entry 4 — wrong first author.** "Kizawa, S., et al. (2025)" is
   wrong. Kizawa is the **third** of five authors.
   Correct: **Takagi, H., Minegishi, G., Kizawa, S., Sukeda, I., & Yanaka, H.
   (2025). *Interpreting Multi-Attribute Confounding through Numerical Attributes
   in Large Language Models.* IJCNLP-AACL 2025 (Main). arXiv:2511.04053.**
   https://aclanthology.org/2025.ijcnlp-long.60/

2. **Claim A entry 13 — there is no author "Wang, N." on that paper at all.**
   Correct: **Chen, N., Liu, J., Dong, X., Liu, Q., Sakai, T., & Wu, X.-M.
   (2024). *AI Can Be Cognitively Biased: An Exploratory Study on Threshold
   Priming in LLM-Based Batch Relevance Assessment.* SIGIR-AP 2024, 54–63.
   arXiv:2409.16022.** The cited title also drops "An Exploratory Study on".

3. **Claim A entry 13's follow-up — title changed at camera-ready.** The WSDM
   2026 published version is "…via Personality **Simulation**", not "via
   Personality Infusing" (which is the arXiv preprint title). Full published
   entry: **Chen, N., Fang, H., Liu, J., Wei, W., Sakai, T., & Wu, X.-M. (2026).
   *Mitigating the Threshold Priming Effect in Large Language Model-Based
   Relevance Judgments via Personality Simulation.* Proc. 19th ACM WSDM.
   doi:10.1145/3773966.3779384. arXiv:2512.00390.**

4. **Claim B — "Cao, Y. T." has a spurious middle initial.** The author is
   **Yong Cao**. Correct: **Cao, Y., Liu, H., Arora, A., Augenstein, I.,
   Röttger, P., & Hershcovich, D. (2025). *Specializing Large Language Models to
   Simulate Survey Response Distributions for Global Populations.* NAACL 2025.
   arXiv:2502.07068.** https://aclanthology.org/2025.naacl-long.162/

5. **Claim B — Cruz & Hardt is missing its third author.** Correct:
   **Cruz, A. F., Hardt, M., & Mendler-Dünner, C. (2024). *Evaluating language
   models as risk scores.* NeurIPS 2024. arXiv:2407.14614.**

### A2.2 Imprecise — tighten before citing

6. **Claim A — the scale-distortion background entry names no authors.** It is
   **Frederick, S. W., & Mochon, D. (2012). *A scale distortion theory of
   anchoring.* Journal of Experimental Psychology: General.** PMID 21767047.
   Name them; the sentence "scale-distortion theory predicted cross-scale
   anchoring should fail" is an attributable claim about a specific paper.

7. **Claim A — Sun et al. (arXiv:2311.09730) now has a venue.** Published at
   **NAACL 2025 (Short Papers)**, https://aclanthology.org/2025.naacl-short.71/.
   Cite the venue, not just the 2023 preprint.

8. **Claim B — Kim & Lee (arXiv:2305.09620) is mis-titled and mis-dated.** The
   later arXiv revision retitles it *AI-Augmented Surveys: Leveraging Large
   Language Models for Opinion Prediction in Nationally Representative Surveys*.
   DBLP shows only a CoRR entry — **no peer-reviewed venue**, so the "2023/2024"
   dual dating implies a publication that does not exist. Cite it as a preprint.

9. **Claim B — three titles are truncated** (harmless but fix for a reference
   list): LeWiDi is *"LeWiDi-2025 **at NLPerspectives**: Third Edition…"*;
   Sorensen & Choi is *"Opt-ICL at LeWiDi-2025: **Maximizing In-Context Signal
   from Rater Examples via Meta-Learning**"*; Sun et al. is *"Random Silicon
   Sampling: **Simulating Human Sub-Population Opinion Using a Large Language
   Model Based on Group-Level Demographic Information**"*.

### A2.3 lit_check.md's own caveats, re-adjudicated

- **arXiv:2602.19403 — lit_check says "neither pass could verify". It is
  verifiable and it is real.** Full entry: **Han, J., Devkota, J., Waring, J.,
  Luken, A., Naughton, F., Vilardaga, R., Bricker, J., Latkin, C., Moran, M.,
  Chen, Y., & Thrul, J. (2026). *Personalized Prediction of Perceived Message
  Effectiveness Using Large Language Model Based Digital Twins.*
  arXiv:2602.19403.** Johns Hopkins; 301 young-adult smokers, 3,010 message
  ratings, digital twins beating zero/few-shot and supervised baselines by
  12–13 points. Only the elicitation *format* remains unconfirmed (needs the
  methods section). Update lit_check's note — it is currently mislabelled as a
  verification gap, and this paper is directly relevant to Paper 2 as an
  individual-level digital-twin prediction result with baselines.
- **SSRN 6366838 (Garcia 2026) — still not directly verifiable.** SSRN returns
  403 to automated fetch. Existence, title, author and the ~52% figure are
  corroborated across three independent search snippets, so it is very likely
  real, but the posting date is inconsistent: lit_check says 9 Mar 2026, every
  snippet found says **3 Mar 2026**. **Do not cite the date without a manual
  check.** Keep lit_check's own "verify before citing" flag in force.
- **Publications 14(3):43 ("How Does Prompt Anchoring Affect LLM Outputs?")** —
  lit_check's assessment is corroborated: this is *not* numeric anchoring; the
  four conditions are example-type framings across 1,068 abstracts. Its
  "do not cite as anchoring evidence" ruling stands.
- **Peng et al. (arXiv:2509.19088 / SSRN 5518418)** — author order differs
  between arXiv (Brucks 3rd, Merlau 4th) and SSRN (Merlau 3rd). Not an error;
  pick the arXiv order and stay consistent.

### A2.4 Everything else checked clean

Verified with no change needed, across both claims: Harris & Speekenbrink 2016;
Wilson et al. 1996; Valencia-Clavijo 2025; Li et al. 2506.22316 (DASFAA 2026);
Yang 2607.01240; Lou & Sun 2412.06593 + JCSS DOI; Nguyen 2024 (JBEF vol. 43);
Huang et al. 2505.15392 (ICLR 2026 HCAIR workshop); Owusu et al. 2606.12818;
Jones & Steinhardt 2022 (NeurIPS 2022); Echterhoff et al. 2024 (Findings EMNLP
2024, 12640–12653); Licht et al. 2509.03116 (EMNLP 2025 Main); Bottoni &
Aizpurua 2026 (Quality & Quantity 60:4595–4613); "Likert or Not" 2505.19334;
"Grading Scale Impact" 2601.03444; Levy & Geva 2410.11781 (NAACL 2025); Shao et
al. 2506.01734 (NeurIPS 2025); Yuchi et al. 2602.07812 (EACL 2026, oral);
Deng et al. 2509.05691 (the written-form-numbers claim was checked against the
full text, §5.2, and holds); Park et al. 2411.10109 (lit_check's retitle note is
itself accurate); Tjuatja et al. TACL 12:1011–1026; Dominguez-Olmedo et al.
NeurIPS 2024; Beck et al. EACL 2024; Rupprecht et al. 2507.07188; Toubia et al.
2505.17479 (+ Marketing Science 44(6):1446–1455); "Measuring Self-Rating Bias"
2602.13862 (sole author Eduardo Vera Pichardo); Ahnert et al. 2510.11586 (ACL
2026, https://aclanthology.org/2026.acl-long.1927/ resolves); Meister et al.
NAACL 2025; Wang/Zhang/Choi Findings EMNLP 2025; Gong et al. 2603.20229;
G-Eval EMNLP 2023; Zawistowski FEDCSIS 2024; Maier et al. 2510.08338; Anthis et
al. ICML 2025; Miranda & Balbi Entropy 27(9):923; Kinzinger & Hartmann
2606.04592; Ku et al. 2607.03091; Choi et al. 2606.28963; SimBench 2510.17516;
Verbalized Sampling 2510.01171; Kambhatla et al. 2507.00439; Bradshaw et al.
2411.03486; "Failure to Mix" 2511.14630; Lin et al. TMLR 2022; Tian et al. EMNLP
2023; Xiong et al. ICLR 2024; Hu & Levy EMNLP 2023; Ren et al. Findings EMNLP
2025; Lee et al. EMNLP 2023; Ignatev et al. 2509.09524; Orlikowski et al. ACL
2025 (2092–2111).

All five ACL Anthology links in the Claim B section resolve to the claimed paper.

---

# PART B — new citations a publishable version should carry

Every entry verified by a live lookup during this task. Ordered by area. The
"where it belongs" line names the paper and the section/claim.

## B1. Simulating specific real, named individuals (Paper 2 mostly)

**Shao, Y., Li, L., Dai, J., & Qiu, X. (2023).** *Character-LLM: A Trainable Agent
for Role-Playing.* EMNLP 2023. arXiv:2310.10158.
https://aclanthology.org/2023.emnlp-main.814/
Trains agents to act as specific named real/historical people (Beethoven,
Cleopatra, Caesar) by "Experience Upload" from their biographies, and evaluates
them with an **interview-based test playground**.
→ **Paper 2 §2 / Paper 1 §2.** The founding precedent for "simulate one named
real person from their own material", and it already uses interviews as the probe.
Cite where the twin is defined.

**Du, B., Guo, M., He, S., Ye, Z., Zhu, X., Su, W., Zhu, S., Zhou, Y., Zhang, Y.,
Ai, Q., & Liu, Y. (2025).** *TwinVoice: A Multi-dimensional Benchmark Towards
Digital Twins via LLM Persona Simulation.* arXiv:2510.25536.
https://arxiv.org/abs/2510.25536
Benchmarks persona simulation across social / interpersonal / narrative contexts
and six capabilities (opinion consistency, memory recall, reasoning, lexical
fidelity, tone, syntactic style); LLMs land "considerably below the human
baseline", worst on syntactic style and memory recall.
→ **Paper 2 §2, and Paper 1 §2.** The current state of the "digital twin
benchmark" art. Also useful in Paper 1: its own protocol pairs a discriminative
multiple-choice arm with a generative arm — the exact instrument pairing DOPPLER
had to choose between.

**Jia, M., Chen, Y., Sharma, D., & Diaz-Rodriguez, J. (2026).** *When Can Digital
Personas Reliably Approximate Human Survey Findings?* arXiv:2605.10659.
https://arxiv.org/abs/2605.10659
LISS panel: personas built from background variables + **pre-2023 survey history**
and tested against the same respondents' **held-out post-cutoff answers**. Across
four architectures and three LLMs, personas improve distributional alignment but
"remain limited for individual prediction and fail to recover multivariate
respondent structure"; they do best on low-variability questions and worst on
subjective/heterogeneous ones.
→ **Paper 2 §1 and §10.** The closest published design to DOPPLER's: same person,
earlier material, later held-out answers. It independently reproduces DOPPLER's
central asymmetry (aggregate looks fine, individual-level lift is small) and its
"worst on subjective items" finding rhymes with Paper 1's round-4 result.
**This is the single best "we are not alone" citation for Paper 2.**

**Li, C., Mo, L., Tang, X., Qu, Y., Wu, X., Zhao, S., Gan, Y., Fan, Y., Yu, Z.,
Jiang, X., Liang, P. P., Zhao, Y., Pastor, D., & Larson, K. (2025).** *HugAgent:
Benchmarking LLMs for Simulation of Individualized Human Reasoning.*
arXiv:2510.15144. https://arxiv.org/abs/2510.15144
Benchmarks whether a model can predict a *specific person's* responses **and the
reasoning behind them** in out-of-distribution scenarios given partial evidence
of their prior views; finds substantial adaptation gaps in SOTA models.
→ **Paper 2 §2 (task setup).** Structurally the same task as DOPPLER's, on a
different substrate. Cite when defining "predict what this person says next".

**Hu, W., Zhang, Y., Wei, X., Han, S., Tang, J., Wang, Y., & Chen, X. (2026).**
*CloneMem: Benchmarking Long-Term Memory for AI Clones.* ACL 2026.
arXiv:2601.07023. https://aclanthology.org/2026.acl-long.1549/
Tests whether an "AI Clone" grounded in a person's non-conversational digital
traces (diaries, posts, emails, 1–3 years) tracks their **evolving** experiences,
emotions and opinions over time; current memory mechanisms struggle.
→ **Paper 2 §3 (H7 staleness).** The nearest published framing of "does a
person-model go stale", from the memory side. Cite where H7 is motivated.

**Kang, B., Moon, S., Lee, S., Raj, N., Suh, J., Chan, S. W. T., & Canny, J.
(2025).** *Deep Binding of Language Model Virtual Personas: a Study on
Approximating Political Partisan Misperceptions.* arXiv:2504.11673.
https://arxiv.org/abs/2504.11673
Builds personas from synthetic life-narrative **interviews** (narrative-identity
theory) and shows this distinguishes an authentic in-group persona from an
outsider's stereotype of that group, improving distribution match by up to 87%.
→ **Paper 2 §2 (imposter design).** The theoretical case for why interview-shaped
grounding beats attribute lists, and a direct framing for the imposter twin as
"an outsider's stereotype of this kind of person".

**Kolluri, A., Wu, M., Park, J. S., & Bernstein, M. S. (2025).** *Finetuning LLMs
for Human Behavior Prediction in Social Science Experiments.* arXiv:2509.05830.
https://arxiv.org/abs/2509.05830
Finetunes on 2.9M individual-level responses (SocSci210; 400K+ participants); the
finetuned model is 26% more aligned with human response distributions than its
base and beats GPT-4o by 13%.
→ **Paper 2 §10.** Same lab lineage as Park et al.; the "what you would do
instead of prompting" comparison. Useful for the limitation "we ground by prompt,
not by finetuning".

**Zhou, S., Zhang, X., Gao, Y., Jiang, S., & Wang, Y. (2025).** *PersonaEval: Are
LLM Evaluators Human Enough to Judge Role-Play?* arXiv:2508.10014.
https://arxiv.org/abs/2508.10014
LLM judges asked to identify which persona produced an utterance reach ~69%
accuracy against 90.8% for humans — i.e. they fail the prerequisite for judging
role-play at all.
→ **Paper 1 §9.4 (judge trust bar).** Direct support for auditing the stance
judge rather than assuming it; and a second data point that LLM judges are
weakest exactly on person-attribution.

**Mannekote, A., Davies, A., Li, J. J., Boyer, K. E., Zhai, C., Dorr, B., &
Pinto, F. (2025).** *Do Role-Playing Agents Practice What They Preach?
Belief-Behavior Consistency in LLM-Based Simulations of Human Trust.*
arXiv:2507.02197. https://arxiv.org/abs/2507.02197
Finds "systematic inconsistencies between LLMs' stated (or imposed) beliefs and
the outcomes of their role-playing simulation, at both an individual- and
population-level."
→ **Paper 2 §5 (H5 calibration).** The closest published analogue to DOPPLER's
finding that a twin's stated confidence does not track whether it is right.

**Kim, S., Im, J., Choi, J., Lee, S., Shim, H., Hong, J., & Choi, Y. (2026).**
*PICon: A Multi-Turn Interrogation Framework for Evaluating Persona Agent
Consistency.* arXiv:2603.25620. https://arxiv.org/abs/2603.25620
Multi-turn interrogation over internal / external / retest consistency shows
"systems previously reported as highly consistent fail to meet the human
baseline" (63 real participants) once the probing gets harder.
→ **Paper 1 §1 and §6.** The general pattern DOPPLER instantiates: an easier
instrument reports high fidelity, a harder one does not. Good companion for the
four-round narrative.

**Han, J., Devkota, J., Waring, J., Luken, A., Naughton, F., Vilardaga, R.,
Bricker, J., Latkin, C., Moran, M., Chen, Y., & Thrul, J. (2026).**
*Personalized Prediction of Perceived Message Effectiveness Using Large Language
Model Based Digital Twins.* arXiv:2602.19403. https://arxiv.org/abs/2602.19403
301 young-adult smokers, 3,010 message ratings; digital twins beat zero-shot,
few-shot and supervised baselines by 12–13 points on individual-level prediction.
→ **Paper 2 §1.** A positive individual-level twin result *with* baselines, in a
different domain — the contrast case for DOPPLER's smaller lift. (This is the
entry lit_check.md wrongly recorded as unverifiable; see A2.3.)

## B2. Forced-choice / MCQ evaluation methodology (Paper 1)

**Chandak, N., Goel, S., Prabhu, A., Hardt, M., & Geiping, J. (2025).** *Answer
Matching Outperforms Multiple Choice for Language Model Evaluation.*
arXiv:2507.02856. https://arxiv.org/abs/2507.02856
Multiple-choice benchmark items "can often be answered without even seeing the
question"; replacing MCQ with free-form generation graded against a reference by
an LLM ("answer matching") reaches near-inter-annotator agreement with humans,
and model rankings change substantially.
→ **Paper 1, everywhere — §1, §8, §9.1.** This is the *same arc as Paper 1*:
diagnose forced choice as leaky, replace with open generation graded against a
reference. It must be cited, and Paper 1's contribution restated against it:
Chandak et al. show MCQ is solvable without the *question*; DOPPLER shows a
person-prediction MCQ is solvable without the *person*, which is a different and
narrower leak. **Highest-priority new citation for Paper 1.**

**Balepur, N., Ravichander, A., & Rudinger, R. (2024).** *Artifacts or Abduction:
How Do LLMs Answer Multiple-Choice Questions Without the Question?* ACL 2024.
arXiv:2402.12483. https://arxiv.org/abs/2402.12483
Choices-only prompts beat the majority baseline in 11 of 12 model–dataset pairs,
by up to 0.33 accuracy; memorization alone does not explain it, and models can
partly reconstruct the question from the options.
→ **Paper 1 §5.2 and §6.** The direct methodological ancestor of DOPPLER's
question-blind ablation (accuracy 1.00 → 0.10 when the question is removed).
Their ablation is the mirror image of DOPPLER's; cite them together.

**Kaushik, D., & Lipton, Z. C. (2018).** *How Much Reading Does Reading
Comprehension Require? A Critical Investigation of Popular Benchmarks.* EMNLP
2018. arXiv:1808.04926. https://arxiv.org/abs/1808.04926
Establishes question-only and passage-only baselines for bAbI, SQuAD, CBT, CNN
and Who-did-What; passage-only models exceed 50% on 14 of 20 bAbI tasks,
sometimes matching the full model.
→ **Paper 1 §2 and §6.** The seminal statement of "run the ablated baseline
before you trust the benchmark" — which is exactly the discipline DOPPLER's
person-blind arm enforces. Cite it as the precedent for the whole method.

**Gururangan, S., Swayamdipta, S., Levy, O., Schwartz, R., Bowman, S. R., &
Smith, N. A. (2018).** *Annotation Artifacts in Natural Language Inference Data.*
NAACL 2018. https://aclanthology.org/N18-2017/
Hypothesis-only classifiers reach ~67% on SNLI and ~53% on MultiNLI without the
premise, because annotators leave lexical giveaways correlated with the label.
→ **Paper 1 §6 (tell taxonomy).** The canonical "one side of the pair leaks the
label" result. DOPPLER's tells are the same species: the real answer is
identifiable without its counterpart.

**Le Bras, R., Swayamdipta, S., Bhagavatula, C., Zellers, R., Peters, M. E.,
Sabharwal, A., & Choi, Y. (2020).** *Adversarial Filters of Dataset Biases.* ICML
2020. arXiv:2002.04108. https://arxiv.org/abs/2002.04108
AFLite iteratively removes items solvable by weak shallow-feature models; SNLI
performance drops 92% → 62% while human performance and OOD generalization hold.
→ **Paper 1 §5.1 and §8.** Prior art for DOPPLER's Amendment-1 adversarial filter
(drop every item the person-blind arm solves). Cite it where the filter removes
all 17 round-1 items — the empty table is AFLite taken to its limit.

**Pezeshkpour, P., & Hruschka, E. (2023).** *Large Language Models Sensitivity to
The Order of Options in Multiple-Choice Questions.* arXiv:2308.11483.
https://arxiv.org/abs/2308.11483
Shuffling option order alone swings accuracy by roughly 13–75 points across
benchmarks, driven by uncertainty among top candidates plus positional bias.
→ **Paper 1 §2.** The justification for DOPPLER's "randomise position" step,
with a magnitude attached.

**Zheng, C., Zhou, H., Meng, F., Zhou, J., & Huang, M. (2024).** *Large Language
Models Are Not Robust Multiple Choice Selectors.* ICLR 2024 (Spotlight).
arXiv:2309.03882. https://arxiv.org/abs/2309.03882
Across 20 LLMs and 3 benchmarks, selection bias traces to token-level prior
probability on the option *IDs* (A/B/C/D) rather than content; proposes PriDe as a
label-free debiasing method.
→ **Paper 1 §2 and §6.** The mechanistic account of position bias, and the reason
DOPPLER can say its tells are content tells rather than ID priors.

**Liusie, A., Raina, V., & Gales, M. (2023).** *World Knowledge in Multiple Choice
Reading Comprehension.* FEVER Workshop @ EMNLP 2023. arXiv:2211.07040.
https://arxiv.org/abs/2211.07040
Information-theoretic metrics (expected number of options, contextual mutual
information) quantify how much of a benchmark is answerable from world knowledge
alone; items solvable by a context-free shortcut are also typically solvable by
humans without context.
→ **Paper 1 §5.3 (world-truth tell).** Gives DOPPLER's world-truth tell a
published name and a *quantitative* instrument. If Paper 1 wants one number for
"how leaky is this item set", this is the method to borrow.

**Alhazmi, E., Sheng, Q. Z., Zhang, W. E., Zaib, M., & Alhazmi, A. (2024).**
*Distractor Generation in Multiple-Choice Tasks: A Survey of Methods, Datasets,
and Evaluation.* EMNLP 2024. arXiv:2402.01512. https://arxiv.org/abs/2402.01512
Survey of distractor generation from classical to transformer methods, and of how
distractor plausibility and quality are evaluated.
→ **Paper 1 §2 and §5.** Situates rounds 1–4 inside an existing subfield with its
own plausibility criteria, instead of presenting distractor design as ad hoc.

**Reinhart, A., Markey, B., Laudenbach, M., Pantusen, K., Yurko, R., Weinberg, G.,
& Brown, D. W. (2025).** *Do LLMs write like humans? Variation in grammatical and
rhetorical styles.* Proceedings of the National Academy of Sciences, 122,
e2422455122. arXiv:2410.16107. https://arxiv.org/abs/2410.16107
Using Biber's lexical/grammatical/rhetorical feature set, finds systematic
differences between human and LLM text that **persist across model scale and are
larger for instruction-tuned models than base models**.
→ **Paper 1 §5.3, §5.4, §6 (register tell).** This is the published mechanism for
DOPPLER's central failure: LLM-written distractors are stylistically
distinguishable from human speech, and instruction tuning makes it *worse* — which
is precisely why round 4's few-shot fix inverted the tell instead of removing it.
**Second-highest-priority new citation for Paper 1.**

**Bitton, Y., Bitton, R., & Nisan, S. (2025).** *Detecting Stylistic Fingerprints
of Large Language Models.* arXiv:2503.01659. https://arxiv.org/abs/2503.01659
LLMs carry consistent stylistic fingerprints **even when prompted to write in a
different style**; a classifier ensemble separates model families and humans at
precision 0.9988, FPR 0.0004.
→ **Paper 1 §5.3.** Directly explains why round 3's "one identical neutralising
paraphrase" could not launder the true option: style survives restyling.

## B3. LLM-as-judge validity and audit practice (Paper 1, some Paper 2)

**Panickssery, A., Bowman, S. R., & Feng, S. (2024).** *LLM Evaluators Recognize
and Favor Their Own Generations.* NeurIPS 2024. arXiv:2404.13076.
https://proceedings.neurips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html
GPT-4 and Llama 2 distinguish their own output from other models' and from humans
at non-trivial accuracy, and self-recognition strength correlates linearly with
self-preference bias.
→ **Paper 1 §11 and Paper 2 §10 (judge family overlap).** The canonical citation
for why a judge sharing a family with a scored model is a validity threat. It
turns DOPPLER's declared caveat into a cited one.

**Wataoka, K., Takahashi, T., & Ri, R. (2024).** *Self-Preference Bias in
LLM-as-a-Judge.* NeurIPS 2024 Safe Generative AI Workshop. arXiv:2410.21819.
https://arxiv.org/abs/2410.21819
Quantifies self-preference and traces it to **perplexity** — judges favour text
they find more familiar, not literally their own text.
→ **Paper 1 §11.** Sharpens the family-overlap caveat: the risk is fluency
familiarity, which applies across a family, not just to self-authored text.

**Calderon, N., Reichart, R., & Dror, R. (2025).** *The Alternative Annotator Test
for LLM-as-a-Judge: How to Statistically Justify Replacing Human Annotators with
LLMs.* ACL 2025. arXiv:2501.10970. https://arxiv.org/abs/2501.10970
Proposes the "alt-test", a statistical procedure for deciding whether an LLM judge
may replace human annotators; evaluated over 10 datasets, 6 LLMs, 4 prompting
strategies, and notes there is currently no standard procedure.
→ **Paper 1 §9.4 and Paper 2 §10.** The field's answer to exactly the question
DOPPLER answered ad hoc with a pre-committed 0.80/κ 0.60 bar. Cite it, and say
explicitly that DOPPLER's LLM-auditor substitution (deviations D1–D4) is the
weaker version of what the alt-test formalises.

**Angelopoulos, A. N., Bates, S., Fannjiang, C., Jordan, M. I., & Zrnic, T.
(2023).** *Prediction-Powered Inference.* Science, 382(6671), 669–674.
arXiv:2301.09633. https://arxiv.org/abs/2301.09633
Valid confidence intervals and p-values when a small gold-labelled sample is
combined with a large machine-labelled sample; validity does not depend on the
model's accuracy.
→ **Paper 1 §9.4 / future work.** The principled alternative to a single pass/fail
κ gate: DOPPLER has a small audited tranche and a large judge-scored corpus,
which is exactly PPI's setting.

**Fisch, A., Maynez, J., Hofer, R. A., Dhingra, B., Globerson, A., & Cohen, W. W.
(2024).** *Stratified Prediction-Powered Inference for Hybrid Language Model
Evaluation.* NeurIPS 2024. arXiv:2406.04291. https://arxiv.org/abs/2406.04291
Extends PPI with stratification for LLM evaluation, giving tighter intervals when
autorater accuracy varies across subgroups.
→ **Paper 1 future work.** The LLM-evaluation-specific descendant; relevant
because DOPPLER's judge accuracy plainly varies by stance label (the
SAME/UNCLEAR confusions).

**Yuan, J., Li, Y., Ding, Y., Xie, S., Li, T., Zhao, Y., Wan, Z., Shi, Y., Hu, W.,
& Liu, Z. (2025).** *Understanding and Mitigating Numerical Sources of
Nondeterminism in LLM Inference.* arXiv:2506.09501.
https://arxiv.org/abs/2506.09501
Batch size, GPU count and GPU version cause real output variation under greedy
decoding; small early-token rounding differences cascade into divergent outputs,
with up to 9% accuracy variation; root cause is floating-point non-associativity.
→ **Paper 2 §10 (the noise floor).** The mechanism citation for "only 15 of 72
byte-identical greedy prompts reproduced". Pair it with the vLLM paper
(arXiv:2309.06180) for the serving system. **Turns DOPPLER's most surprising
methodological observation into a known, cited phenomenon.**

**Desai, J., Card, D., & Jacobs, A. Z. (2026).** *Validating LLMs in social
science: Epistemic threats and emerging norms.* arXiv:2607.07915.
https://arxiv.org/abs/2607.07915
Systematic review of validation practice in social-science work using LLMs for
measurement; validation is inconsistent and often absent.
→ **Paper 1 §9 and Paper 2 §10.** The field-level framing that makes DOPPLER's
audit trail a contribution rather than housekeeping.

**Kotte, A. (2026).** *Two Wrongs, No Right: Auditing Social-Desirability Bias in
LLM Annotators for Computational Social Science.* arXiv:2606.12426.
https://arxiv.org/abs/2606.12426
Three 7B annotator models show inconsistent, model-specific failures (opposition
prevalence underestimated by 24–40 points); aggregate agreement masks class-level
errors severe enough to reverse a conclusion.
→ **Paper 1 §9.4.** The published reason DOPPLER's bar has **two** legs (raw
agreement AND κ) rather than raw agreement alone, and the reason the UNCLEAR
asymmetry in §8.3 of Paper 2 matters.

**Yeadon, W., Hardy, T., Mackay, C., & Agra, D. (2026).** *LLM-as-a-judge validity
in physics assessment depends more on the task than the model.* arXiv:2603.14732.
https://arxiv.org/abs/2603.14732
Judge validity varies sharply by task structure rather than by which frontier
model judges: strong on structured items, poor and harsher-than-human on open
essays.
→ **Paper 1 §9.** The reason moving from forced choice to open-ended scoring
raises judge risk, which is the regime DOPPLER moved into.

## B4. Corpora (both papers, Methods)

Zhu et al. 2021 (MediaSum) and Majumder et al. 2020 (INTERVIEW) are in Part A
§A1.6 — they are *missing existing* citations, not new discoveries. Three
genuinely new ones:

**Aggazzotti, C., Andrews, N., & Smith, E. A. (2024).** *Can Authorship
Attribution Models Distinguish Speakers in Speech Transcripts?* Transactions of
the ACL (TACL). arXiv:2311.07564. https://arxiv.org/abs/2311.07564
Authorship models achieve "surprisingly good performance in certain settings" on
speech transcripts but "perform markedly worse as conversational topic is
increasingly controlled" — the apparent speaker signal is substantially topic.
→ **Paper 1 §5.1 and §6 (topical coherence) and Paper 2 §9.2/§3.5.** The single
best prior-art citation for DOPPLER's core diagnosis: what looks like
person-specific signal in transcripts is largely topic, and it only shows up when
you control topic. It also independently supports Paper 1's caveat that channel-1
cosine separation is partly topical (r ≈ 0.74). **Highest-priority new corpus-side
citation.**

**Spangher, A., Lu, T., Kalyan, S., Cho, H., Shi, W., & May, J. (2025).**
*NewsInterview: a Dataset and a Playground to Evaluate LLMs' Grounding Gap via
Informational Interviews.* ACL 2025. arXiv:2411.13779.
https://arxiv.org/abs/2411.13779
Curates 40,000 two-person NPR/CNN informational interviews and shows LLMs are
markedly worse than human interviewers at acknowledgement and follow-up pivoting.
→ **Paper 1 §10 (positioning) and Paper 2 §4 (H6).** Same corpus family, and it
is about the *interviewer* side — which is exactly the open question DOPPLER
declares (does adaptivity help in open conversation). Cite it where the project
disclaims being a competing interviewer, and where H6's follow-up-chain design is
motivated.

**Zhang, S. et al. (2018).** *Personalizing Dialogue Agents: I have a dog, do you
have pets too?* ACL 2018. arXiv:1801.07243. https://arxiv.org/abs/1801.07243
Introduces PersonaChat: crowdsourced dialogue where each speaker is conditioned on
a short profile of invented facts.
→ **Paper 1 §2 / Paper 2 §2.** The contrast case. Persona-grounded dialogue means
five made-up sentences; DOPPLER grounds on 2,000 words of a real person's actual
recorded speech. One sentence of related work, no more.

## B5. Contamination and memorization (Paper 2 §8.1, §11; Paper 1 §11)

**Carlini, N., Tramèr, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K.,
Roberts, A., Brown, T., Song, D., Erlingsson, Ú., Oprea, A., & Raffel, C. (2021).**
*Extracting Training Data from Large Language Models.* USENIX Security 2021.
arXiv:2012.07805. https://arxiv.org/abs/2012.07805
Extracts hundreds of verbatim training sequences, including personal information,
from GPT-2; larger models are more vulnerable, and extraction works even for
singly-occurring sequences.
→ **Paper 2 §11 (ethics) and §8.1.** The foundational reason a model may already
"know" a subject, and the reason the ethics section's "public words only" defence
needs the contamination meter beside it.

**Carlini, N., Ippolito, D., Jagielski, M., Lee, K., Tramèr, F., & Zhang, C.
(2023).** *Quantifying Memorization Across Neural Language Models.* ICLR 2023.
arXiv:2202.07646. https://arxiv.org/abs/2202.07646
Memorization grows log-linearly with model capacity, **duplication count**, and
context length; a 6B model memorizes at least 1% of its training set.
→ **Paper 2 §8.1.** The duplication mechanism behind DOPPLER's top-decile meter
result. It is also the reason that result is *not* paradoxical: more-duplicated
(more famous) subjects are exactly where memorization bites.

**Kandpal, N., Deng, H., Roberts, A., Wallace, E., & Raffel, C. (2023).** *Large
Language Models Struggle to Learn Long-Tail Knowledge.* ICML 2023.
arXiv:2211.08411. https://arxiv.org/abs/2211.08411
QA accuracy on a fact correlates strongly with the number of relevant pretraining
documents; closing the long-tail gap needs large additional scale.
→ **Paper 2 §2 (curation) and §8.1.** The published justification for
over-sampling long-tail subjects with no Wikipedia page.

**Mallen, A., Asai, A., Zhong, V., Das, R., Khashabi, D., & Hajishirzi, H.
(2023).** *When Not to Trust Language Models: Investigating Effectiveness of
Parametric and Non-Parametric Memories.* ACL 2023, 9802–9822. arXiv:2212.10511.
doi:10.18653/v1/2023.acl-long.546. https://aclanthology.org/2023.acl-long.546/
Introduces PopQA (14K long-tail entity questions); scaling "fails to appreciably
improve memorization of factual knowledge in the long tail".
→ **Paper 2 §2 and §8.1.** The companion "popularity predicts recall" citation.
Cite both; they are the standard pair.

**Shi, W., Ajith, A., Xia, M., Huang, Y., Liu, D., Blevins, T., Chen, D., &
Zettlemoyer, L. (2024).** *Detecting Pretraining Data from Large Language Models.*
ICLR 2024. arXiv:2310.16789. https://arxiv.org/abs/2310.16789
Min-K% Prob: a reference-free membership-inference method flagging unseen text via
outlier low-probability tokens, on a temporally-split benchmark (WIKIMIA).
→ **Paper 2 §8.1.** The off-the-shelf alternative to DOPPLER's home-made
contamination meter. Cite it and say why the meter was used instead (MediaSum is
entirely pre-cutoff, so there is no "unseen" side to the split).

**Oren, Y., Meister, N., Chatterji, N., Ladhak, F., & Hashimoto, T. B. (2024).**
*Proving Test Set Contamination in Black Box Language Models.* ICLR 2024.
arXiv:2310.17623. https://arxiv.org/abs/2310.17623
An exchangeability test: if a model prefers a benchmark's canonical ordering to
shuffled orderings, that proves contamination; works on 1.4B models and 1,000
examples.
→ **Paper 2 §8.1.** Second alternative method; cite in the same sentence.

**Deng, C., Zhao, Y., Heng, Y., Li, Y., Cao, J., Tang, X., & Cohan, A. (2024).**
*Unveiling the Spectrum of Data Contamination in Language Models: A Survey from
Detection to Remediation.* ACL 2024. arXiv:2406.14644.
https://arxiv.org/abs/2406.14644
Survey of contamination causes, detection and remediation.
→ **Paper 2 §8.1.** The one-citation framing for the contamination paragraph.

**Zhang, J. et al. (2026).** *Test of Time: Rethinking Temporal Signal of Benchmark
Contamination.* arXiv:2509.00072. https://arxiv.org/abs/2509.00072
Post-cutoff performance decay — usually read as proof of contamination-free
evaluation — is highly sensitive to how the questions are phrased; paraphrased
versus cloze-style questions built from the *same* documents give different
temporal signals.
→ **Paper 2 §11.** Direct support for DOPPLER's decision **not** to claim a clean
post-cutoff subset. The strategy the project declined to use is itself unreliable.
This upgrades a limitation into a defended design choice.

## B6. Baselines and generic-answer effects (Paper 2 §1.2, §10)

**Wu, Z., Peng, R., Ito, T., Onizuka, M., & Xiao, C. (2026).** *LLM-Based Social
Simulations Require a Boundary.* ICML 2026 (Position). arXiv:2506.19806.
https://arxiv.org/abs/2506.19806
Systematic review: LLM social simulations trend toward a homogeneous "average
persona"; fewer than half of reviewed papers assess behavioural variance, and
those that do find lower variance than real populations.
→ **Paper 2 §1.2.** The mechanism candidate for DOPPLER's strangest number — the
zero-information baseline beating the imposter twin. If everything collapses
toward an average persona, a *confident wrong* persona is a displacement from that
average, while no persona sits on it.

**Morocho, E. E. T., Cima, L., Fagni, T., Avvenuti, M., & Cresci, S. (2026).**
*Assessing the Reliability of Persona-Conditioned LLMs as Synthetic Survey
Respondents.* arXiv:2602.18462. https://arxiv.org/abs/2602.18462
70K+ respondent-item instances from the World Values Survey, two open-weight
models plus a random-guesser baseline: "persona prompting does not yield a clear
aggregate improvement in survey alignment and, in many cases, significantly
degrades performance", redistributing error and undermining subgroup fidelity.
→ **Paper 2 §1.2 and §10.** The closest published statement of "conditioning on
person-information can be worse than not conditioning", with a proper baseline.
**The single best citation for the zero-info-beats-imposter result.**

**Cheng, M., Piccardi, T., & Yang, D. (2023).** *CoMPosT: Characterizing and
Evaluating Caricature in LLM Simulations.* EMNLP 2023. arXiv:2310.11501.
https://arxiv.org/abs/2310.11501
Framework (Context, Model, Persona, Topic) scoring individuation and exaggeration;
GPT-4 simulations of political and marginalized-group personas are highly
susceptible to caricature.
→ **Paper 2 §10 and Paper 1 §5.3.** Caricature is the population-level version of
Paper 1's register tell: conditioned generation exaggerates rather than
individuates.

**de Arruda, H. F., Gracia Lázaro, C., Aleta, A., & Moreno, Y. (2026).**
*Collective cooperation without individual fidelity in LLM agents.*
arXiv:2606.30454. https://arxiv.org/abs/2606.30454
LLM agents reproduce the macro-level cooperation dynamics of a large networked
human experiment, but "collective outcomes can appear human-like even when the
underlying behavioral distributions and mechanisms are not".
→ **Paper 2 §6 (B8, individual vs population).** The cleanest published statement
of why DOPPLER's standing rule — print individual lift beside a population metric
— is necessary.

**Li, A., Chen, H., Namkoong, H., & Peng, T. (2025).** *LLM Generated Persona is a
Promise with a Catch.* arXiv:2503.16527. https://arxiv.org/abs/2503.16527
~1M LLM-generated synthetic personas used for election forecasting and population
surveys carry systematic biases producing substantial real-world prediction error.
→ **Paper 2 §1 and §10.** Supports treating persona-conditioning risk as
*directional bias*, not noise — which is why lift, not accuracy, is the metric.

**Yao, S. (2026).** *More Is Not More: What Matters for Diversity in LLM Opinions?*
arXiv:2607.20429. https://arxiv.org/abs/2607.20429
Factorial study over 100 questions × 7 models: initial persona conditioning
captures most of the diversity gain; additional demographic elaboration gives
inconsistent or negative returns.
→ **Paper 2 §4 (H6).** Independent evidence for the "more grounding does not
monotonically help" pattern H6 ran into.

**Qin, Y., Li, X., & Cheng, Z. (2026).** *Restoring Heterogeneity in LLM-based
Social Simulation: An Audience Segmentation Approach.* arXiv:2604.06663.
https://arxiv.org/abs/2604.06663
Standard LLM simulation masks subgroup differences; against US climate-opinion
data, "no single configuration dominates all dimensions" of distributional,
structural and predictive fidelity.
→ **Paper 2 §6.** Supports the homogenization story and the fact that fixes trade
off across levels.

**Ma, Y., Zhang, T., Ang, S., & Chen, Y. (2026).** *Not-quite-human tastes: the
stylized omnivorousness of LLM survey surrogates.* arXiv:2606.30085.
https://arxiv.org/abs/2606.30085
~277K synthetic respondents show systematic positive bias ("liking inflation"),
loss of real taste-structure relationality, and distorted demographic-taste
associations.
→ **Paper 2 §1.2.** A second, independent mechanism for "generic output is
systematically displaced, not neutral".

**Sun, S., Lee, E., Nan, D., Zhao, X., Lee, W., Jansen, B. J., & Kim, J. H.
(2024).** *Random Silicon Sampling: Simulating Human Sub-Population Opinion Using a
Large Language Model Based on Group-Level Demographic Information.*
arXiv:2402.18144. https://arxiv.org/abs/2402.18144
Group-level demographic conditioning approximates US polling at subgroup level but
effectiveness varies greatly by demographic and topic.
→ **Paper 2 §2.** Background for why a demographic-style baseline is not a
substitute for a true zero-information arm. (Already listed in lit_check.md's
Claim-B background; included here with its full title for the reference section.)

## B7. Expected information gain, adaptive selection, CAT (Paper 1 §10)

**Lindley, D. V. (1956).** *On a Measure of the Information Provided by an
Experiment.* The Annals of Mathematical Statistics, 27(4), 986–1005.
doi:10.1214/aoms/1177728069.
https://projecteuclid.org/journals/annals-of-mathematical-statistics/volume-27/issue-4/On-a-Measure-of-the-Information-Provided-by-an-Experiment/10.1214/aoms/1177728069.full
Introduces the entropy-reduction measure of what an experiment teaches you, and
applies it to experimental design.
→ **Paper 1 §10.** The origin of "expected information gain". PAPER1 §10
describes EIG without ever citing where it comes from. One line, and it makes the
BED-LLM paragraph properly grounded.

**Foster, A., Ivanova, D. R., Malik, I., & Rainforth, T. (2021).** *Deep Adaptive
Design: Amortizing Sequential Bayesian Experimental Design.* ICML 2021.
arXiv:2103.02438. https://arxiv.org/abs/2103.02438
Trains a design network upfront so adaptive designs are chosen in a single
forward pass at deployment rather than re-optimized each step.
→ **Paper 1 §10.** The modern BED line that BED-LLM descends from (Rainforth is
on both). Cite it so the positioning names the research programme, not just its
LLM instance.

**Handa, K., Gal, Y., Pavlick, E., Goodman, N., Andreas, J., Tamkin, A., &
Li, B. Z. (2024).** *Bayesian Preference Elicitation with Language Models.*
arXiv:2403.05534. https://arxiv.org/abs/2403.05534
OPEN combines Bayesian optimal experimental design with LLMs to choose maximally
informative natural-language questions for eliciting a person's preferences, and
outperforms prior elicitation methods in user studies.
→ **Paper 1 §10.** The exact category Stage 1E tested. Cite it alongside BED-LLM
and Wang et al.; three points make the "this is an active area with published
results" statement (Amendment 2 B9.a) properly evidenced rather than asserted.

**Hartmann, J., Harvey, J., Navott, J., Wang, E. Y., Melo, L. C., Cipcigan, F.,
Zhang, C., & Abate, A. (2026).** *Amortising Bayesian Experimental Design for
Sequential Information Gathering in LLMs.* FoGen workshop @ ICML 2026
(non-archival). arXiv:2607.03426. https://arxiv.org/abs/2607.03426
Fine-tunes an LLM to internalize EIG-driven questioning; more than doubles
20-Questions success over the 7B base and cuts inference cost >25× versus BED-LLM.
→ **Paper 1 §10.** The most recent state of the art, and it post-dates the
project's own work — useful to show the flag is planted against a moving field.
Note the non-archival workshop status when citing.

**Choi, S. W., Reise, S. P., Pilkonis, P. A., Hays, R. D., & Cella, D. (2010).**
*Efficiency of static and computer adaptive short forms compared to full-length
measures of depressive symptoms.* Quality of Life Research, 19(1), 125–136.
doi:10.1007/s11136-009-9560-5. https://pubmed.ncbi.nlm.nih.gov/19941077/
On the 28-item PROMIS depression bank, CAT "outperformed each static short form in
almost all criteria. However, short-form selection strategies performed only
marginally worse than CAT."
→ **Paper 1 §10, contribution 1.** This is the closest published precedent to
Stage 1E's headline. It is **sixteen years old** and it says the same thing:
a well-chosen static short form is nearly as good as adaptive testing. Paper 1
should cite it *and* say what is new — that in the LLM setting the static order
did not merely come close, it won, at a twelfth of the compute. **Highest-priority
new citation for Paper 1's positioning section.**

**Amtmann, D., Bamer, A. M., Kim, J., Bocell, F., Chung, H., Park, R., Salem, R.,
& Hafner, B. J. (2018).** *A comparison of computerized adaptive testing and
fixed-length short forms for the Prosthetic Limb Users Survey of Mobility
(PLUS-M).* Prosthetics and Orthotics International.
https://pubmed.ncbi.nlm.nih.gov/28866959/
CAT, a 7-item short form and a 12-item short form give highly correlated,
similarly efficient scores; CAT's time savings over the 7-item form are minimal.
→ **Paper 1 §10.** Second, independent psychometric replication in a different
domain. Two citations make it a pattern rather than one odd study.

**Olaru, G., & Danner, D. (2021).** *Developing Cross-Cultural Short Scales Using
Ant Colony Optimization.* Assessment, 28(1), 199–210.
doi:10.1177/1073191120918026. https://pubmed.ncbi.nlm.nih.gov/32418476/
Selects a 15-item cross-culturally invariant BFI-2 short form from 5,567
respondents in five countries by optimization on population data, beating a
traditionally-constructed short form on measurement invariance.
→ **Paper 1 §10, contribution 1.** This is the psychometrics literature's name
for what Stage 1E's fixed order *is*: a population-optimized static instrument
derived on disjoint people. Cite it so the "static-script baseline" contribution
is positioned as importing a known psychometric method into LLM elicitation,
rather than inventing one.

**Schroeders, U., Wilhelm, O., & Olaru, G. (2016).** *Meta-Heuristics in Short
Scale Construction: Ant Colony Optimization and Genetic Algorithm.* PLOS ONE,
11(11), e0167110. doi:10.1371/journal.pone.0167110.
https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0167110
Compares stepwise CFA, ant colony optimization and genetic algorithms for
shortening an 89-item test; stepwise selection produces reliable but poorly valid
scales, the metaheuristics do better.
→ **Paper 1 §10.** Methodologically relevant and mildly uncomfortable: the
project's fixed order came from **greedy** ridge regression, which is the stepwise
family this paper says trades validity for reliability. Worth one honest sentence.

**Oh, G., Lee, J., Park, J., Yu, Y., Bae, W., & Noh, J. (2026).** *Random Is Hard
to Beat: Active Selection in online DPO with Modern LLMs.* arXiv:2604.02766.
https://arxiv.org/abs/2604.02766
Uncertainty-based active preference learning yields negligible gains over random
sampling across harmlessness, helpfulness and instruction-following; "in the
regime of strong pre-trained priors, the computational overhead of active
selection is difficult to justify against the 'cheap diversity' provided by simple
random samples."
→ **Paper 1 §10.** An LLM-era, 2026 instance of Stage 1E's exact result and its
exact cost argument, in a different task family. It generalises the project's
finding without the project having to over-claim it.

**Montazeralghaem, A., Tennenholtz, G., Boutilier, C., & Meshi, O. (2025).**
*Asking Clarifying Questions for Preference Elicitation With Large Language
Models.* arXiv:2510.12015. https://arxiv.org/abs/2510.12015
Trains LLMs with a two-stage diffusion-inspired scheme to generate sequential
clarifying questions that reconstruct a user's preference profile.
→ **Paper 1 §10, optional.** A fourth adaptive-elicitation point if the section
needs breadth; it also has no population-optimized static baseline, which is the
gap the project's contribution 1 claims.

## B8. Ethics and governance of simulating real people (Paper 2 §11)

Paper 2 §11 is currently three paragraphs of the project's own reasoning with no
external anchor. All of the following are real published or official sources.

**Park, J. S., Zou, C. Q., Shaw, A., Hill, B. M., Cai, C. J., Morris, M. R.,
Willer, R., Liang, P., & Bernstein, M. S. (2025).** *Simulating Human Behavior
with AI Agents.* Stanford HAI Policy Brief.
https://hai.stanford.edu/policy/simulating-human-behavior-with-ai-agents
The governance companion to the 1,052-person study: frames privacy, over-reliance
and reputational-misuse risks, and recommends tiered access, audit logs and
**revocable consent** for agents built from real people's interview data.
→ **Paper 2 §11.** The nearest thing to a governance template for exactly Paper
2's method. It also sharpens the contrast the paper should draw: Park et al.'s
subjects were paid, consenting, opt-in participants with a revocation path;
DOPPLER's are non-consenting broadcast guests. Measure the project's safeguards
(pseudonymous IDs, nothing individuating published) against this list explicitly.
**Highest-priority new citation for Paper 2's ethics section.**

**Favela, L. H., & Amon, M. J. (2023).** *The Ethics of Human Digital Twins:
Counterfeit People, Personhood, and the Right to Privacy.* 2023 IEEE 3rd
International Conference on Digital Twins and Parallel Intelligence (DTPI),
16–22. IEEE Xplore document 10365409. https://ieeexplore.ieee.org/document/10365409/
Argues that high-fidelity human digital twins necessarily encroach on features
constituting personhood, so creating them without consent is simultaneously a
privacy violation and a human-rights violation.
→ **Paper 2 §11.** The strongest available statement of the ethical objection
Paper 2 must answer. Cite it and answer it — the project's answer (public words
only, pseudonymous IDs, nothing individuating published, deliberately no fidelity
sufficient for misuse) is a good one, but it should be stated *against* this.

**Hollanek, T., & Nowaczyk-Basińska, K. (2024).** *Griefbots, Deadbots, Postmortem
Avatars: on Responsible Applications of Generative AI in the Digital Afterlife
Industry.* Philosophy & Technology, 37(2), article 63.
doi:10.1007/s13347-024-00744-w.
https://link.springer.com/article/10.1007/s13347-024-00744-w
Maps ethical concerns in AI recreations of people from their data through a
data-donor / data-holder / interactant framework, and recommends consent from both
donor and interactant, transparency, and a dignified retirement procedure.
→ **Paper 2 §11.** The "data donor cannot object" framing maps directly onto the
project's own declared asymmetry ("this study models people who are *less* able to
notice or object"). This is the literature that already has vocabulary for that.

**Methuku, V., & Myakala, P. K. (2025).** *Digital Doppelgangers: Ethical and
Societal Implications of Pre-Mortem AI Clones.* arXiv:2502.21248.
https://arxiv.org/abs/2502.21248
Examines AI clones of **living** people, flagging identity fragmentation,
unauthorized cloning, data exploitation and regulatory gaps.
→ **Paper 2 §11.** More precisely on-target than the griefbot literature: DOPPLER's
subjects are alive. Use this rather than the deadbot work if only one goes in.

**Bonagiri, V. K., Sepulveda-Arias, J. N., Djiberou Mahamadou, A. J., &
Choudhury, M. (2026).** *Cognitive Digital Twins: Ethical Risks and Governance for
AI Systems That Model the Mind.* arXiv:2606.23094.
https://arxiv.org/abs/2606.23094
A five-part governance framework (authority, autonomy, access/control,
accountability, availability) calling for stronger consent, purpose limitation,
traceability and **model retirement**.
→ **Paper 2 §11.** A ready-made checklist to evaluate the project against.
"Purpose limitation" and "model retirement" are the two the project has not
addressed and could address in one sentence each.

**Karpus, J., & Strasser, A. (2025).** *Persons and their Digital Replicas.*
Philosophy & Technology, 38, article 25. doi:10.1007/s13347-025-00854-z.
https://link.springer.com/article/10.1007/s13347-025-00854-z
Uses Parfit on personal identity to ask when a digital replica built from
someone's digital trace could count as an extension of that person; notes that
experts could not reliably distinguish a machine-generated Daniel Dennett from the
real one.
→ **Paper 2 §11, optional.** Philosophical grounding for what "twin" means. The
Dennett anecdote is also a nice bridge to Paper 1's detectability line.

**Lauterwasser, S., & Nedzhvetskaya, N. (2023).** *Privacy in Public?: The Ethics
of Academic Research with Publicly Available Social Media Data.* Berkeley Journal
of Sociology. https://berkeleyjournal.org/2023/08/11/privacy-in-public/
Argues that data being technically public does not settle consent, because people
do not anticipate downstream aggregation and analysis; recommends seeking consent
when spotlighting individuals and not publishing inferred characteristics.
→ **Paper 2 §11.** Directly engages the project's central ethical premise ("all
material is public broadcast transcript"). Note that the project already follows
this paper's two main recommendations by not spotlighting or publishing inferred
attributes — say so, with the citation.

**Hutiri, W., Papakyriakopoulos, O., & Xiang, A. (2024).** *Not My Voice! A
Taxonomy of Ethical and Safety Harms of Speech Generators.* ACM FAccT 2024.
arXiv:2402.01708. https://arxiv.org/abs/2402.01708
A relational harms taxonomy distinguishing impersonation from identity theft,
identity hijack and right-of-publicity violation, grounded in real incidents.
→ **Paper 2 §11, optional.** Transferable vocabulary for the risk discussion even
though it is about voice rather than text.

**119th U.S. Congress (2025).** *S. 1367 — Nurture Originals, Foster Art, and Keep
Entertainment Safe Act of 2025 ("NO FAKES Act of 2025").* Introduced 9 April 2025
by Sen. Coons with Sens. Blackburn, Klobuchar and Tillis.
https://www.congress.gov/119/bills/s1367/BILLS-119s1367is.pdf
Would create a federal property right in a person's voice and visual likeness,
defining a "digital replica" as a computer-generated, readily identifiable stand-in
for an individual, and requiring consent for its creation and use.
→ **Paper 2 §11.** The concrete emerging legal baseline — **and the gap is the
point**: the Act reaches audiovisual and voice replicas, so a text-only
statistical twin built from transcripts sits outside its scope. Paper 2 naming
that gap is a genuine contribution to the ethics section and costs two sentences.

## B9. Three further verified entries found outside the assigned areas

**Xie, Q., Feng, Q., Zhang, T., Li, Q., Yang, L., Zhang, Y., Feng, R., He, L.,
Gao, S., & Zhang, Y. (2025).** *Human Simulacra: Benchmarking the Personification
of Large Language Models.* ICLR 2025. arXiv:2402.18180.
https://arxiv.org/abs/2402.18180
A personification framework plus a **psychology-guided evaluation from both self
and observer perspectives**, using cloze, single-choice and multiple-choice items
to test a simulated character's knowledge and consistency.
→ **Paper 1 §2 and §5.** The best example of the exact instrument family Paper 1
kills: multiple-choice evaluation of a human simulacrum. If Paper 1's negative
result is to bite on anyone, it is on protocols shaped like this one. Cite it as
the representative case, carefully — the scope limit ("we do not claim forced
choice is dead everywhere") must travel with it.

**Li, S. S., Paranjape, B., Oktar, K., Ma, Z., Zhou, G., Guan, L., Zhang, N.,
Park, S., Chen, L., Yang, D., Tsvetkov, Y., & Celikyilmaz, A. (2026).**
*HorizonBench: Long-Horizon Personalization with Evolving Preferences.*
arXiv:2604.17283. https://arxiv.org/abs/2604.17283
4,245 items from 360 simulated users with 6-month histories; across 25 frontier
models the best reaches 52.8% and most score at or below the 20% chance baseline;
when models err on evolved preferences, over a third of the time they return the
user's *originally stated* value.
→ **Paper 2 §3 (H7 staleness).** The closest published treatment of "a person
changes and the model does not notice", with a chance baseline reported — which
is the DOPPLER house style. Useful for framing why H7 was worth asking even though
it returned no headline.

**Zhang, Z., Rossi, R. A., Kveton, B., Shao, Y., Yang, D., Zamani, H.,
Dernoncourt, F., Barrow, J., Yu, T., Kim, S., Zhang, R., Gu, J., Derr, T.,
Chen, H., Wu, J., Chen, X., Wang, Z., Mitra, S., Lipka, N., Ahmed, N., & Wang, Y.
(2025).** *Personalization of Large Language Models: A Survey.* Transactions on
Machine Learning Research (TMLR). arXiv:2411.00027.
https://arxiv.org/abs/2411.00027
Taxonomy of personalization granularity, techniques, datasets, evaluation methods
and applications.
→ **Both papers, one line in related work.** The standard survey to point at so
neither paper has to enumerate the personalization literature.

## B10. Unverified — do not use

- **Garcia, J. (2026), SSRN 6366838** (already in lit_check.md). SSRN returns 403
  to automated fetch. Existence corroborated by search snippets only, and the
  posting date is inconsistent (lit_check says 9 Mar 2026, snippets say 3 Mar
  2026). Manual check required before citing, and do not cite the date.
- **Guo, Y., Lu, X., Ma, W., et al. (2026), "LGA: lightweight design and privacy
  analysis of generative agents in social simulations", International Journal of
  Information Security.** Every fetch attempt hit a Springer authentication wall
  or 403. Title and abstract known only from search snippets.
- **Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference".** A company
  blog post with no accompanying paper found. Use Yuan et al. (arXiv:2506.09501)
  instead — it is the peer-reviewable version of the same argument.
- **Senate Judiciary / coons.senate.gov press release and govtrack.us page for the
  NO FAKES Act** — both 403. The Act itself is verified from the official
  congress.gov bill text; cite that, not the secondary pages.
- Surfaced in search but not read directly, so not used: "MM-JudgeBias"
  (arXiv:2604.18164); "Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge";
  "Breaking the Mirror" (arXiv:2509.03647); "Mitigating Easy Option Bias in
  Multiple-Choice Question Answering" (arXiv:2508.13428); Min-K%++
  (arXiv:2404.02936); "LLM Dataset Inference" (arXiv:2406.06443); MPCHAT
  (arXiv:2305.17388); "Extracting and Inferring Personal Attributes from Dialogue"
  (arXiv:2109.12702); SLX Corpus of Classic Sociolinguistic Interviews
  (LDC2003T15).
- **Verified but deliberately dropped as tangential** (available if a section needs
  them): Liang, "Artificial Intelligence Clones" (arXiv:2501.16996 — a
  game-theoretic matching-market model, not empirical); KnowMe-Bench
  (arXiv:2601.04745 — redundant with CloneMem); GermanPartiesQA (arXiv:2407.18008,
  AIES 2025); "Whose Personae?" (arXiv:2512.00461, AIES 2025); "Illusions of the
  Gold Standard" (arXiv:2606.07936); "What Is Actually Being Annotated?"
  (arXiv:2604.16413).

## B11. A negative finding worth keeping

A dedicated search found **no published work documenting quality defects specific
to MediaSum or its CNN/NPR source scrapes** — no re-aired/duplicate transcript
leakage, no speaker misattribution in older CNN panel shows, no boilerplate study.
PAPER2 §8.5's C02502 re-airing (CNN-388758 replaying 47% of CNN-381362) and
PAPER1 §11's flagged misattribution risk therefore appear to be **original
observations about a widely-used corpus**. That is a small, real, publishable
contribution and it should be written as one rather than buried in a guards
subsection.

---

# READY-TO-PASTE REFERENCES

Author-year, plain format. Entries marked **[NEW]** are not currently in any
writeup. Entries marked **[FIX]** are already cited somewhere and are wrong as
cited — the form below is the corrected one.

## References — Paper 1 (methods: forced-choice evaluation)

Alhazmi, E., Sheng, Q. Z., Zhang, W. E., Zaib, M., & Alhazmi, A. (2024). Distractor generation in multiple-choice tasks: A survey of methods, datasets, and evaluation. In Proceedings of EMNLP 2024. arXiv:2402.01512. https://arxiv.org/abs/2402.01512 **[NEW]**

Amtmann, D., Bamer, A. M., Kim, J., Bocell, F., Chung, H., Park, R., Salem, R., & Hafner, B. J. (2018). A comparison of computerized adaptive testing and fixed-length short forms for the Prosthetic Limb Users Survey of Mobility (PLUS-M). Prosthetics and Orthotics International. https://pubmed.ncbi.nlm.nih.gov/28866959/ **[NEW]**

Angelopoulos, A. N., Bates, S., Fannjiang, C., Jordan, M. I., & Zrnic, T. (2023). Prediction-powered inference. Science, 382(6671), 669–674. arXiv:2301.09633. https://arxiv.org/abs/2301.09633 **[NEW]**

Balepur, N., Ravichander, A., & Rudinger, R. (2024). Artifacts or abduction: How do LLMs answer multiple-choice questions without the question? In Proceedings of ACL 2024. arXiv:2402.12483. https://arxiv.org/abs/2402.12483 **[NEW]**

Bitton, Y., Bitton, R., & Nisan, S. (2025). Detecting stylistic fingerprints of large language models. arXiv:2503.01659. https://arxiv.org/abs/2503.01659 **[NEW]**

Calderon, N., Reichart, R., & Dror, R. (2025). The alternative annotator test for LLM-as-a-judge: How to statistically justify replacing human annotators with LLMs. In Proceedings of ACL 2025. arXiv:2501.10970. https://arxiv.org/abs/2501.10970 **[NEW]**

Chandak, N., Goel, S., Prabhu, A., Hardt, M., & Geiping, J. (2025). Answer matching outperforms multiple choice for language model evaluation. arXiv:2507.02856. https://arxiv.org/abs/2507.02856 **[NEW]**

Choi, S. W., Reise, S. P., Pilkonis, P. A., Hays, R. D., & Cella, D. (2010). Efficiency of static and computer adaptive short forms compared to full-length measures of depressive symptoms. Quality of Life Research, 19(1), 125–136. doi:10.1007/s11136-009-9560-5 **[NEW]**

Choudhury, D., Williamson, S., Goliński, A., Miao, N., Bickford Smith, F., Kirchhof, M., Zhang, Y., & Rainforth, T. (2026). BED-LLM: Intelligent information gathering with LLMs and Bayesian experimental design. In Proceedings of ICLR 2026. arXiv:2508.21184 (posted 2025). https://arxiv.org/abs/2508.21184

Cohen, J. (1960). A coefficient of agreement for nominal scales. Educational and Psychological Measurement, 20(1), 37–46. doi:10.1177/001316446002000104 **[NEW]**

Desai, J., Card, D., & Jacobs, A. Z. (2026). Validating LLMs in social science: Epistemic threats and emerging norms. arXiv:2607.07915. https://arxiv.org/abs/2607.07915 **[NEW]**

Foster, A., Ivanova, D. R., Malik, I., & Rainforth, T. (2021). Deep adaptive design: Amortizing sequential Bayesian experimental design. In Proceedings of ICML 2021. arXiv:2103.02438. https://arxiv.org/abs/2103.02438 **[NEW]**

Gururangan, S., Swayamdipta, S., Levy, O., Schwartz, R., Bowman, S. R., & Smith, N. A. (2018). Annotation artifacts in natural language inference data. In Proceedings of NAACL-HLT 2018, 107–112. https://aclanthology.org/N18-2017/ **[NEW]**

Handa, K., Gal, Y., Pavlick, E., Goodman, N., Andreas, J., Tamkin, A., & Li, B. Z. (2024). Bayesian preference elicitation with language models. arXiv:2403.05534. https://arxiv.org/abs/2403.05534 **[NEW]**

Kaushik, D., & Lipton, Z. C. (2018). How much reading does reading comprehension require? A critical investigation of popular benchmarks. In Proceedings of EMNLP 2018. arXiv:1808.04926. https://arxiv.org/abs/1808.04926 **[NEW]**

Kotte, A. (2026). Two wrongs, no right: Auditing social-desirability bias in LLM annotators for computational social science. arXiv:2606.12426. https://arxiv.org/abs/2606.12426 **[NEW]**

Le Bras, R., Swayamdipta, S., Bhagavatula, C., Zellers, R., Peters, M. E., Sabharwal, A., & Choi, Y. (2020). Adversarial filters of dataset biases. In Proceedings of ICML 2020. arXiv:2002.04108. https://arxiv.org/abs/2002.04108 **[NEW]**

Lindley, D. V. (1956). On a measure of the information provided by an experiment. The Annals of Mathematical Statistics, 27(4), 986–1005. doi:10.1214/aoms/1177728069 **[NEW]**

Liusie, A., Raina, V., & Gales, M. (2023). World knowledge in multiple choice reading comprehension. In Proceedings of the Sixth FEVER Workshop (EMNLP 2023). arXiv:2211.07040. https://arxiv.org/abs/2211.07040 **[NEW]**

Oh, G., Lee, J., Park, J., Yu, Y., Bae, W., & Noh, J. (2026). Random is hard to beat: Active selection in online DPO with modern LLMs. arXiv:2604.02766. https://arxiv.org/abs/2604.02766 **[NEW]**

Olaru, G., & Danner, D. (2021). Developing cross-cultural short scales using ant colony optimization. Assessment, 28(1), 199–210. doi:10.1177/1073191120918026 **[NEW]**

Panickssery, A., Bowman, S. R., & Feng, S. (2024). LLM evaluators recognize and favor their own generations. In Advances in Neural Information Processing Systems 37 (NeurIPS 2024). arXiv:2404.13076. https://arxiv.org/abs/2404.13076 **[NEW]**

Pezeshkpour, P., & Hruschka, E. (2023). Large language models sensitivity to the order of options in multiple-choice questions. arXiv:2308.11483. https://arxiv.org/abs/2308.11483 **[NEW]**

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In Proceedings of EMNLP-IJCNLP 2019. arXiv:1908.10084. https://arxiv.org/abs/1908.10084 **[NEW]**

Reinhart, A., Markey, B., Laudenbach, M., Pantusen, K., Yurko, R., Weinberg, G., & Brown, D. W. (2025). Do LLMs write like humans? Variation in grammatical and rhetorical styles. Proceedings of the National Academy of Sciences, 122, e2422455122. arXiv:2410.16107. https://arxiv.org/abs/2410.16107 **[NEW]**

Schroeders, U., Wilhelm, O., & Olaru, G. (2016). Meta-heuristics in short scale construction: Ant colony optimization and genetic algorithm. PLOS ONE, 11(11), e0167110. doi:10.1371/journal.pone.0167110 **[NEW]**

Song, K., Tan, X., Qin, T., Lu, J., & Liu, T.-Y. (2020). MPNet: Masked and permuted pre-training for language understanding. In Advances in Neural Information Processing Systems 33 (NeurIPS 2020), 16857–16867. arXiv:2004.09297. https://arxiv.org/abs/2004.09297 **[NEW]**

Wang, J., Zollo, T., Zemel, R., & Namkoong, H. (2025). Adaptive elicitation of latent information using natural language. In Proceedings of ICML 2025. arXiv:2504.04204. https://arxiv.org/abs/2504.04204

Xie, Q., Feng, Q., Zhang, T., Li, Q., Yang, L., Zhang, Y., Feng, R., He, L., Gao, S., & Zhang, Y. (2025). Human Simulacra: Benchmarking the personification of large language models. In Proceedings of ICLR 2025. arXiv:2402.18180. https://arxiv.org/abs/2402.18180 **[NEW]**

Yeadon, W., Hardy, T., Mackay, C., & Agra, D. (2026). LLM-as-a-judge validity in physics assessment depends more on the task than the model. arXiv:2603.14732. https://arxiv.org/abs/2603.14732 **[NEW]**

Zheng, C., Zhou, H., Meng, F., Zhou, J., & Huang, M. (2024). Large language models are not robust multiple choice selectors. In Proceedings of ICLR 2024. arXiv:2309.03882. https://arxiv.org/abs/2309.03882 **[NEW]**

## References — Paper 2 (main results: twin fidelity and lift)

119th U.S. Congress. (2025). S. 1367 — Nurture Originals, Foster Art, and Keep Entertainment Safe Act of 2025 (NO FAKES Act of 2025). Introduced 9 April 2025. https://www.congress.gov/119/bills/s1367/BILLS-119s1367is.pdf **[NEW]**

Bonagiri, V. K., Sepulveda-Arias, J. N., Djiberou Mahamadou, A. J., & Choudhury, M. (2026). Cognitive digital twins: Ethical risks and governance for AI systems that model the mind. arXiv:2606.23094. https://arxiv.org/abs/2606.23094 **[NEW]**

Carlini, N., Ippolito, D., Jagielski, M., Lee, K., Tramèr, F., & Zhang, C. (2023). Quantifying memorization across neural language models. In Proceedings of ICLR 2023. arXiv:2202.07646. https://arxiv.org/abs/2202.07646 **[NEW]**

Carlini, N., Tramèr, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, Ú., Oprea, A., & Raffel, C. (2021). Extracting training data from large language models. In Proceedings of USENIX Security 2021. arXiv:2012.07805. https://arxiv.org/abs/2012.07805 **[NEW]**

Cheng, M., Piccardi, T., & Yang, D. (2023). CoMPosT: Characterizing and evaluating caricature in LLM simulations. In Proceedings of EMNLP 2023. arXiv:2310.11501. https://arxiv.org/abs/2310.11501 **[NEW]**

de Arruda, H. F., Gracia Lázaro, C., Aleta, A., & Moreno, Y. (2026). Collective cooperation without individual fidelity in LLM agents. arXiv:2606.30454. https://arxiv.org/abs/2606.30454 **[NEW]**

Deng, C., Zhao, Y., Heng, Y., Li, Y., Cao, J., Tang, X., & Cohan, A. (2024). Unveiling the spectrum of data contamination in language models: A survey from detection to remediation. In Proceedings of ACL 2024. arXiv:2406.14644. https://arxiv.org/abs/2406.14644 **[NEW]**

Du, B., Guo, M., He, S., Ye, Z., Zhu, X., Su, W., Zhu, S., Zhou, Y., Zhang, Y., Ai, Q., & Liu, Y. (2025). TwinVoice: A multi-dimensional benchmark towards digital twins via LLM persona simulation. arXiv:2510.25536. https://arxiv.org/abs/2510.25536 **[NEW]**

Favela, L. H., & Amon, M. J. (2023). The ethics of human digital twins: Counterfeit people, personhood, and the right to privacy. In 2023 IEEE 3rd International Conference on Digital Twins and Parallel Intelligence (DTPI), 16–22. https://ieeexplore.ieee.org/document/10365409/ **[NEW]**

Han, J., Devkota, J., Waring, J., Luken, A., Naughton, F., Vilardaga, R., Bricker, J., Latkin, C., Moran, M., Chen, Y., & Thrul, J. (2026). Personalized prediction of perceived message effectiveness using large language model based digital twins. arXiv:2602.19403. https://arxiv.org/abs/2602.19403 **[NEW]**

Hollanek, T., & Nowaczyk-Basińska, K. (2024). Griefbots, deadbots, postmortem avatars: On responsible applications of generative AI in the digital afterlife industry. Philosophy & Technology, 37(2), 63. doi:10.1007/s13347-024-00744-w **[NEW]**

Hu, W., Zhang, Y., Wei, X., Han, S., Tang, J., Wang, Y., & Chen, X. (2026). CloneMem: Benchmarking long-term memory for AI clones. In Proceedings of ACL 2026. arXiv:2601.07023. https://aclanthology.org/2026.acl-long.1549/ **[NEW]**

Jia, M., Chen, Y., Sharma, D., & Diaz-Rodriguez, J. (2026). When can digital personas reliably approximate human survey findings? arXiv:2605.10659. https://arxiv.org/abs/2605.10659 **[NEW]**

Kandpal, N., Deng, H., Roberts, A., Wallace, E., & Raffel, C. (2023). Large language models struggle to learn long-tail knowledge. In Proceedings of ICML 2023. arXiv:2211.08411. https://arxiv.org/abs/2211.08411 **[NEW]**

Kang, B., Moon, S., Lee, S., Raj, N., Suh, J., Chan, S. W. T., & Canny, J. (2025). Deep binding of language model virtual personas: A study on approximating political partisan misperceptions. arXiv:2504.11673. https://arxiv.org/abs/2504.11673 **[NEW]**

Kolluri, A., Wu, M., Park, J. S., & Bernstein, M. S. (2025). Finetuning LLMs for human behavior prediction in social science experiments. arXiv:2509.05830. https://arxiv.org/abs/2509.05830 **[NEW]**

Kwon, W., Li, Z., Zhuang, S., Sheng, Y., Zheng, L., Yu, C. H., Gonzalez, J. E., Zhang, H., & Stoica, I. (2023). Efficient memory management for large language model serving with PagedAttention. In Proceedings of SOSP 2023. arXiv:2309.06180. https://arxiv.org/abs/2309.06180 **[NEW]**

Lauterwasser, S., & Nedzhvetskaya, N. (2023). Privacy in public? The ethics of academic research with publicly available social media data. Berkeley Journal of Sociology. https://berkeleyjournal.org/2023/08/11/privacy-in-public/ **[NEW]**

Li, C., Mo, L., Tang, X., Qu, Y., Wu, X., Zhao, S., Gan, Y., Fan, Y., Yu, Z., Jiang, X., Liang, P. P., Zhao, Y., Pastor, D., & Larson, K. (2025). HugAgent: Benchmarking LLMs for simulation of individualized human reasoning. arXiv:2510.15144. https://arxiv.org/abs/2510.15144 **[NEW]**

Li, S. S., Paranjape, B., Oktar, K., Ma, Z., Zhou, G., Guan, L., Zhang, N., Park, S., Chen, L., Yang, D., Tsvetkov, Y., & Celikyilmaz, A. (2026). HorizonBench: Long-horizon personalization with evolving preferences. arXiv:2604.17283. https://arxiv.org/abs/2604.17283 **[NEW]**

Mallen, A., Asai, A., Zhong, V., Das, R., Khashabi, D., & Hajishirzi, H. (2023). When not to trust language models: Investigating effectiveness of parametric and non-parametric memories. In Proceedings of ACL 2023, 9802–9822. doi:10.18653/v1/2023.acl-long.546 **[NEW]**

Mannekote, A., Davies, A., Li, J. J., Boyer, K. E., Zhai, C., Dorr, B., & Pinto, F. (2025). Do role-playing agents practice what they preach? Belief-behavior consistency in LLM-based simulations of human trust. arXiv:2507.02197. https://arxiv.org/abs/2507.02197 **[NEW]**

Methuku, V., & Myakala, P. K. (2025). Digital doppelgangers: Ethical and societal implications of pre-mortem AI clones. arXiv:2502.21248. https://arxiv.org/abs/2502.21248 **[NEW]**

Morocho, E. E. T., Cima, L., Fagni, T., Avvenuti, M., & Cresci, S. (2026). Assessing the reliability of persona-conditioned LLMs as synthetic survey respondents. arXiv:2602.18462. https://arxiv.org/abs/2602.18462 **[NEW]**

Oren, Y., Meister, N., Chatterji, N., Ladhak, F., & Hashimoto, T. B. (2024). Proving test set contamination in black box language models. In Proceedings of ICLR 2024. arXiv:2310.17623. https://arxiv.org/abs/2310.17623 **[NEW]**

Park, J. S., Zou, C. Q., Shaw, A., Hill, B. M., Cai, C. J., Morris, M. R., Willer, R., Liang, P., & Bernstein, M. S. (2025). Simulating human behavior with AI agents. Stanford HAI Policy Brief. https://hai.stanford.edu/policy/simulating-human-behavior-with-ai-agents **[NEW]**

Shao, Y., Li, L., Dai, J., & Qiu, X. (2023). Character-LLM: A trainable agent for role-playing. In Proceedings of EMNLP 2023. arXiv:2310.10158. https://aclanthology.org/2023.emnlp-main.814/ **[NEW]**

Shi, W., Ajith, A., Xia, M., Huang, Y., Liu, D., Blevins, T., Chen, D., & Zettlemoyer, L. (2024). Detecting pretraining data from large language models. In Proceedings of ICLR 2024. arXiv:2310.16789. https://arxiv.org/abs/2310.16789 **[NEW]**

Spangher, A., Lu, T., Kalyan, S., Cho, H., Shi, W., & May, J. (2025). NewsInterview: A dataset and a playground to evaluate LLMs' grounding gap via informational interviews. In Proceedings of ACL 2025. arXiv:2411.13779. https://arxiv.org/abs/2411.13779 **[NEW]**

Wu, Z., Peng, R., Ito, T., Onizuka, M., & Xiao, C. (2026). LLM-based social simulations require a boundary. In Proceedings of ICML 2026 (Position Paper Track). arXiv:2506.19806. https://arxiv.org/abs/2506.19806 **[NEW]**

Yuan, J., Li, Y., Ding, Y., Xie, S., Li, T., Zhao, Y., Wan, Z., Shi, Y., Hu, W., & Liu, Z. (2025). Understanding and mitigating numerical sources of nondeterminism in LLM inference. arXiv:2506.09501. https://arxiv.org/abs/2506.09501 **[NEW]**

Zhang, J., et al. (2026). Test of time: Rethinking temporal signal of benchmark contamination. arXiv:2509.00072. https://arxiv.org/abs/2509.00072 **[NEW]**

## References — shared by both papers

Aggazzotti, C., Andrews, N., & Smith, E. A. (2024). Can authorship attribution models distinguish speakers in speech transcripts? Transactions of the Association for Computational Linguistics. arXiv:2311.07564. https://arxiv.org/abs/2311.07564 **[NEW]**

Gemma Team, Google DeepMind. (2026). Gemma 4 technical report. arXiv:2607.02770. https://arxiv.org/abs/2607.02770 **[NEW]**

Google DeepMind. (2026). Gemini 3.5 Flash model card. https://deepmind.google/models/model-cards/gemini-3-5-flash/ — and Gemini 3.5 Flash-Lite model card, https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/ **[NEW]**

Majumder, B. P., Li, S., Ni, J., & McAuley, J. (2020). Interview: Large-scale modeling of media dialog with discourse patterns and knowledge grounding. In Proceedings of EMNLP 2020, 8129–8141. doi:10.18653/v1/2020.emnlp-main.653. arXiv:2004.03090 **[NEW]**

Park, J. S., Zou, C. Q., Kamphorst, J., Egan, N., Shaw, A., Hill, B. M., Cai, C., Morris, M. R., Liang, P., Willer, R., & Bernstein, M. S. (2026). LLM agents grounded in self-reports enable general-purpose simulation of individuals. arXiv:2411.10109 (v1, 2024, circulated as "Generative agent simulations of 1,000 people"). https://arxiv.org/abs/2411.10109 **[FIX]**

Santurkar, S., Durmus, E., Ladhak, F., Lee, C., Liang, P., & Hashimoto, T. (2023). Whose opinions do language models reflect? In Proceedings of ICML 2023, PMLR 202:29971–30004. arXiv:2303.17548. https://proceedings.mlr.press/v202/santurkar23a.html **[FIX]**

Su, R., Liu, Y., & Hu, J. (2026). Adaptive interviewing for persona simulation in LLMs: Evidence-grounded reasoning improves decision alignment. arXiv:2605.29458 (preprint, not peer reviewed). https://arxiv.org/abs/2605.29458

Sun, S., Lee, E., Nan, D., Zhao, X., Lee, W., Jansen, B. J., & Kim, J. H. (2024). Random silicon sampling: Simulating human sub-population opinion using a large language model based on group-level demographic information. arXiv:2402.18144. https://arxiv.org/abs/2402.18144 **[NEW]**

Zhang, Z., Rossi, R. A., Kveton, B., Shao, Y., Yang, D., Zamani, H., Dernoncourt, F., Barrow, J., Yu, T., Kim, S., Zhang, R., Gu, J., Derr, T., Chen, H., Wu, J., Chen, X., Wang, Z., Mitra, S., Lipka, N., Ahmed, N., & Wang, Y. (2025). Personalization of large language models: A survey. Transactions on Machine Learning Research. arXiv:2411.00027. https://arxiv.org/abs/2411.00027 **[NEW]**

Zhu, C., Liu, Y., Mei, J., & Zeng, M. (2021). MediaSum: A large-scale media interview dataset for dialogue summarization. In Proceedings of NAACL-HLT 2021, 5927–5934. doi:10.18653/v1/2021.naacl-main.474. arXiv:2103.06410 **[NEW — currently uncited anywhere, and it is the corpus]**


