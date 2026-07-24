# Stage 2 corpus recon — feasibility verdict (Phase A)

Date: 2026-07-24. Scope: MediaSum only, per the Phase A brief. Cost: $0 API
(Wikipedia free API only), ~2.5 h CPU on the local machine, no GPU, no LLM calls.

## Verdict

**MediaSum alone supports Stage 2.** The pre-registered target (>= 30 subjects
with >= 3 substantive interviews each, biased toward long-tail people) is met
with a comfortable margin, but only after automated cleaning — the raw
"guests with 3+ interviews" number is inflated ~17x by staff journalists,
bare-surname labels, and celebrity head.

One design flag needs the owner's attention (see "Airtight subset" below).

## The funnel (each number verified, provenance at bottom)

| step | count |
|---|---|
| MediaSum transcripts (CNN 414,176 / NPR 49,420) | 463,596 |
| distinct non-staff guest names | 354,184 |
| >= 3 transcripts and >= 2,000 words of own speech (raw key number) | 10,869 |
| >= 3 individually substantive interviews (>= 300 words, >= 5 turns each) | 6,735 |
| ... and full (multi-token) name | 1,237 |
| ... and not in the top-500-by-words celebrity/staff head | 1,162 |
| ... and no staff evidence anywhere in the corpus, no label artifact (**clean pool**) | **634** |
| ... and usable chronology (>= 3 dated interviews spanning >= 180 days) | **579** |

Long-tail (no Wikipedia page, the pre-registered bias target): of 133 clean
candidates checked so far, **26 are long-tail (19.5%)**; 23 of those also have
usable chronology. Extrapolating the rate to the 501 clean-but-unchecked
candidates gives an expected **~120 clean long-tail candidates** total.
Even after the quality audit's residual discount (collisions, re-aired
duplicates, thin interviews: roughly a further 25% loss), that leaves
~90 long-tail plus ~350 non-long-tail usable subjects. Target is 30.

## What the hand audit showed (20 guests, 121 transcripts read)

Full detail: `stage2_corpus_recon_quality.md`. Rates on the structurally
qualifying pool BEFORE the staff cross-reference fix:

- Speaker attribution: 70% clean, 20% minor issues, 10% broken.
- Substance: 80% substantive; but only ~55% substantive AND genuine AND non-duplicated.
- Staff leakage: 30% were network journalists appearing without a role tag.
  This was the biggest contaminant and is now fixed mechanically: any name that
  ever appears anywhere in the corpus with HOST/ANCHOR/BYLINE/REPORTER/etc.
  is excluded (398 of 1,162 removed; all six audit-derived sanity checks pass).
- Name collisions: ~10% (e.g. one "Rick Nelson" = a counterterrorism expert
  plus a restaurant critic). Not yet fixed; needs per-subject human review.
- Re-airing duplication (CNN especially): same interview broadcast on several
  shows inflates interview counts. Needs near-duplicate detection in Phase B.

## Facts that shape the Stage 2 design

- **NPR is the workhorse.** CNN is 93% of transcripts but its guest turns are
  mostly too thin; the substantive recurring-guest pool is NPR-dominated
  (283 of the 634 clean candidates are majority-NPR). NPR dates are 100%
  parseable; half of CNN rows have missing or placeholder dates (a mix of a
  fixable non-zero-padded format and a "2000-1-1" default).
- **Corpus ends October 2020.**

## Airtight subset — decision needed (not blocking)

PREREGISTRATION.md Stage 2 names "a fully airtight subset" using test
interviews dated after the simulation model's training cutoff. The corpus
ends 2020-10; Gemma-4's training data ends well after that. So the airtight
subset **cannot come from MediaSum**. Recommendation: run the main
confirmatory study (H1-H3) on MediaSum as planned — lift, redaction, and the
contamination meter are the pre-registered controls and they don't depend on
the cutoff — and add a small post-cutoff supplement (e.g. podcast transcripts
via yt-dlp) later, only for the airtight subset. Per the Phase A rule, no
such download happens until the owner approves a concrete plan.

## What Phase B (curation) must build

1. Wikipedia check for the 501 clean-but-unchecked candidates (~10 API batches).
2. Near-duplicate interview detection (re-airings), then recount interviews.
3. CNN date fix (non-padded formats; treat 2000-1-1 as missing).
4. Label-variant merging within a subject (honorifics, initials, "Reporting").
5. Human review of the resulting shortlist for identity coherence (collisions)
   and genuine-guest status, targeting >= 30 subjects biased long-tail.

## Provenance

- Index + Wikipedia checks: `experiments/mediasum_index.py`,
  `experiments/wiki_recheck.py` -> `stage2_corpus_recon_index.md`,
  `data/mediasum_index/guest_index.csv`, `guest_interviews.csv`, `wiki_recheck.csv`.
- Hand audit: `experiments/mediasum_extract.py` ->
  `stage2_corpus_recon_quality.md`, transcript dumps in
  `data/mediasum_index/quality_sample/`.
- Staff cross-reference: `experiments/staff_crossref.py` ->
  `data/mediasum_index/staff_crossref.csv`.
- Candidate table: `experiments/build_candidate_pool.py` ->
  `stage2_candidate_pool.csv` (1,162 rows, flags: clean / staff_evidence /
  initial_label / label_artifact / wiki_status; clean candidates sorted first).
- Raw corpus: `experiments/extract_deflate64.py`; zip sha256 `9a723737...cb82bb`,
  json sha256 `b0b79d3f...72aeef3`, 463,596 records verified.

## Corrections (2026-07-24, from Phase B curation — results/stage2_curation_report.md)

Two claims above are wrong and are corrected here rather than silently edited:

1. **CNN dates are not missing.** "Half of CNN rows have missing or
   placeholder dates" was an artifact of the Phase A index parser requiring
   zero-padded months/days; it silently discarded 41.8% of the corpus's
   dates. A tolerant parser recovers 100.0% of dates. "2000-1-1" is genuine
   New Year's Day 2000 coverage (55 records, confirmed via CNN URL paths),
   not a placeholder.
2. **The staff cross-reference was not the final fix.** Staff who are
   always bare-labelled (no role marker anywhere) pass any label filter;
   a summary-text filter now catches them (all 6 audit-identified staff
   excluded, at the cost of an over-exclusion reserve needing review).
