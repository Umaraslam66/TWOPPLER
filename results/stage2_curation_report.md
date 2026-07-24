# Stage 2 curation — Phase B mechanics (MediaSum)

Date: 2026-07-24. Scope: the five mechanical fixes Phase A asked for, plus a
sixth that Phase A missed. Cost: **$0** (Wikipedia free API only; no LLM, no
paid API, CPU only, no GPU). Runtime: **~55 min**, dominated by one 35-minute
pass over the 4.4 GB corpus and a 17-minute rate-limited Wikipedia search pass.

Target under PREREGISTRATION_AMENDMENT_1 A5: **>= 80 subjects, biased
long-tail**, each with >= 3 substantive interviews.

## Verdict

**Yes, with room to spare on supply, and a real but manageable squeeze if the
owner insists all 80 subjects be long-tail.**

- **578 candidates** now pass every mechanical filter (clean identity, >= 3
  *deduplicated* substantive interviews, >= 180-day span on *fixed* dates).
- Of those, **137 are confirmed long-tail** (no Wikipedia article under any
  spelling we could find), 424 have an article, 17 have one under a different
  spelling.
- Human review is the binding constraint, not supply — exactly as Phase A
  predicted. Scoring the final pool against the 20-guest hand audit gives a
  survival rate of **60-80%** on candidates that reach review.
- **A mixed pool of 80 is easy: 4-6x margin.** An **all-long-tail 80 is
  tight** — 137 candidates exist, which yields 82-110 after review. If the
  owner wants all 80 long-tail, plan to review essentially every one of the
  137, and treat the 5-point margin at the pessimistic end as real.

Full margin arithmetic in "Can we deliver >= 80?" below.

---

## Step 1 — Dates

**Phase A was wrong about this in two ways, and one of them is the headline
of this report.**

Claim in `stage2_corpus_recon.md`: "half of CNN rows have missing or
placeholder dates (a mix of a fixable non-zero-padded format and a `2000-1-1`
default)".

What is actually in the file, from a full census of all 463,596 date strings
(10,315 distinct):

| date form | records |
|---|---|
| zero-padded `YYYY-MM-DD` | 269,669 |
| non-padded `YYYY-M-D` | 193,927 |
| empty | **0** |
| otherwise unparseable | **0** |
| implausible year (`3007-2-12`) | 2 |

1. **There is no `2000-1-1` placeholder.** It occurs 55 times, which is
   unremarkable next to its January-2000 neighbours (45-79 records per day).
   Reading those records settles it: every one is genuine New Year's Day 2000
   coverage ("Millennium 2000", Y2K, the Pope's address), and the CNN URL
   independently encodes the date (`.../TRANSCRIPTS/0001/01/...` = YY MM/DD).
   **Nothing was treated as missing.**
2. **Nothing is missing at all.** 100% of transcripts carry a well-formed,
   valid calendar date. The Phase A parser required two-digit month and day,
   so it silently discarded the 41.8% of records using the non-padded form.

The two `3007-2-12` records are typos for 2007-02-12 (their URL says
`/0702/12/`). They are flagged `implausible_year` and excluded from any
chronology, rather than silently corrected.

**Before / after**, on the 831,952 (guest, transcript) rows of
`guest_interviews.csv`:

| | rows with a usable date |
|---|---|
| Phase A parser | 416,389 (50.0%) |
| tolerant parser | **831,947 (100.0%)** |

Output: `data/mediasum_index/guest_interviews_v2.csv` — same rows, plus a
repaired `date`, a `date_quality` flag (`ok` / `ok_padding_fixed` /
`implausible_year`), and the original value kept as `date_v1`.
Also `data/mediasum_index/transcript_dates_v2.csv` (all 463,596 transcripts).

**What it bought us, honestly: less than you would guess.** Among clean
candidates, 27 gained a usable chronology purely from the date fix — and all
27 are CNN-only subjects (mean NPR share 0.01), previously undateable. But
the candidate pool was already NPR-dominated, and NPR dates were always fine,
so the *share* of clean candidates with a usable chronology barely moved
(91.3% -> 88.5%, the small drop being deduplication, see step 2). The fix is
still necessary — it is what makes CNN subjects usable at all, and it removes
a silent 42% data loss — but it did not unlock the pool.

## Step 2 — Near-duplicate interviews

Method: for each subject, take only that person's own utterances in each
transcript, hash them into 5-word shingles, and compare every pair of their
appearances. Two appearances are the same interview if Jaccard >= 0.60 (same
text) or containment >= 0.80 with >= 50 shingles (one airing is a subset of
the other — the re-broadcast case). Clusters are transitive; **one cluster
counts as one interview**. Same-day multi-programme appearances are flagged
separately.

| | count |
|---|---|
| appearances compared (within-subject pairs) | 532,830 |
| appearance rows for the 1,153 subjects | 25,472 |
| duplicate clusters found (size > 1) | 1,487 |
| appearances collapsed away | 2,227 (8.7%) |
| same-day multi-programme date groups | 1,322 |
| ...of which also text-duplicates | 687 |
| substantive appearances, before -> after | 7,053 -> 6,914 (-2.0%) |
| subjects whose substantive count dropped | 91 |
| subjects dropped below the >= 3 bar by dedup | 35 (22 of them clean) |

**Duplication is real but much smaller than Phase A feared** at the level
that matters. 8.7% of all appearances are re-airings, but only 2.0% of
*substantive* ones — because the re-airings are overwhelmingly short
soundbites, not full interviews. Phase A's expectation of "roughly a further
25% loss" from collisions + duplicates + thin interviews does not show up in
the duplicate column.

Worked example, the audit's worst case — Pedro Castro (brother of the
Cleveland kidnapper), 35 appearances: twelve identical ~85-word soundbites
across five programmes collapse into one cluster; the Savidge interview
survives as a handful of substantive clusters, all on 2013-05-13. He fails
the pool anyway, correctly, because three same-day airings cannot produce
three distinct interview dates.

That is the general protection: the qualifying rule counts **distinct
interview dates among deduplicated substantive clusters (>= 3)**, so a
same-day multi-programme burst can never look like recurrence, whatever the
text similarity says.

Output: `data/mediasum_index/dedup_map_v2.csv` — one row per appearance with
its cluster id, cluster size, date, programme, word/turn counts and a
same-day-multi-programme flag.

## Step 3 — Label-variant merging

Five rules, each carrying its evidence into
`data/mediasum_index/canonical_map_v2.csv`. Proposals are generated by string
shape over all 354,184 indexed guest names; acceptance requires evidence.

| rule | proposed | accepted | evidence required |
|---|---|---|---|
| `initial_vs_full` (`C. Reeve` = `Christopher Reeve`) | 1,414 | 55 | both labels in the same transcript, covering >= 75% of the initial label's own transcripts |
| `reporting_suffix` (`Nina Totenberg Reporting`) | 166 | 166 | string rule — a sign-off artifact |
| `punctuation_variant` (`E.J. Dionne` = `Ej Dionne`) | 90 | 73 | identical letters **and digits** ignoring punctuation |
| `middle_initial` (`John F. Burns` = `John Burns`) | 32 | 0 | same as initial_vs_full; none cleared it |
| `honorific_residue` | 0 | 0 | — |
| **total** | **1,702** | **294** | |

Rejections: 726 no shared transcript, 623 ambiguous (the initial matches more
than one full name — 32 such labels refused outright), 42 low coverage, 17
digits differ.

Result: 275 multi-name groups, **291 names absorbed**, and the 1,162 Phase A
pool rows become **1,153 canonical subjects**.

Two guards were added after seeing the first run produce nonsense, and both
matter:

- **Digits carry identity.** Stripping all non-letters merged `Bush 41` with
  `Bush 43`, and jurors `B-29`/`B-37`/`B-51`/`B-76` into one person. Fixed;
  17 pairs rejected on this ground.
- **One shared transcript is not enough.** Co-occurrence alone folded
  `J. Edwards` (27 transcripts, mostly the senator) into `Justin Edwards`
  (1 transcript), and `A. Gore` (16) into `Amanda Gore` (2). Requiring the
  full name to appear in >= 75% of the initial label's transcripts cut
  accepted initial merges from 96 to 55 and removed every one of these.

Sanity check on the audit's hardest case: `C. Reeve` merges into
`Christopher Reeve` at coverage 8/8, while `D. Reeve` merges into **Dana
Reeve** at 10/11 — the two are correctly kept apart, which is exactly what
the hand audit said was broken.

## Step 4 — Wikipedia coverage

Phase A had raw-label Wikipedia results for only 133 of the 1,162 candidates;
501 clean candidates were unchecked and ~200 more carried the biased v1 flag
(which queried the title-cased *normalized* name and produced false
long-tails).

Rather than check only the 501, **all 1,153 canonical subjects were checked**
with the good method — the subject's most frequent spelled-out raw transcript
label, honorifics and roles stripped, original casing preserved, redirects on,
batches of 50, >= 1.1 s between batches. Two titles are queried per subject
(the raw label and the canonical name); the subject counts as having a page if
either hits.

| | count |
|---|---|
| canonical subjects checked | 1,153 (100%) |
| has an article (exact title) | 772 |
| no article (exact title) | 381 |
| overlap with the v1 re-check | 103, **0 disagreements** |
| the 501 Phase A clean-unchecked -> canonical | 500 subjects, now 100% checked |

One bug found and fixed here: the query label was originally the *most
frequent* raw label, which for a merged subject is often the initial form.
`Christopher Reeve` was queried as "C. Reeve" and came back long-tail. Query
selection now prefers a spelled-out label.

**Residual false long-tails, measured not assumed.** Exact-title matching
still misses articles whose title differs in spelling: `Karen Deyoung` ->
"Karen DeYoung", `Nicholas Lardy` -> "Nicholas R. Lardy", `Tim Brookes` ->
"Tim Brooks", `Andy Kohut` -> "Andrew Kohut". A 25-name sample of shortlist
long-tails found 3 such misses (12%). So every exact-title long-tail was put
through Wikipedia's *search* API and downgraded when the closest article title
is >= 0.88 similar.

| | count |
|---|---|
| exact-title long-tails put through search | 381 |
| downgraded — an article exists under another spelling | **28 (7.3%)** |
| confirmed long-tail | **353** |

Almost all 28 are one systematic artifact: our normalizer title-cases each
word, so internal capitals die and the exact title misses — `Bill Mckibben` /
"Bill McKibben", `Karen Deyoung` / "Karen DeYoung", `Megan Mcardle` /
"Megan McArdle", `Maya Macguineas` / "Maya MacGuineas", `Ll Cool J` /
"LL Cool J", all at similarity 1.00. Wikipedia's redirects did **not** absorb
these, contrary to the note in `wiki_recheck.py`.

The 7.3% measured here is below the 12% the 25-name sample suggested, and the
remainder is not zero: `Glen Loury` is still marked long-tail although the
article is "Glenn Loury" — search returned nothing close enough. Treat the
long-tail count as accurate to a few percent, biased slightly high.

Outputs: `data/mediasum_index/wiki_recheck_v2.csv` (union of the v1 re-check
and the v2 pass, with a `source` column) and
`data/mediasum_index/wiki_fuzzy_v2.csv`.

## Step 5 — A sixth fix Phase A did not ask for: bare-name staff

The hand audit's largest single failure mode was network correspondents
passing as guests (30% of the sample). Phase A treated this as solved: "any
name that ever appears anywhere in the corpus with HOST/ANCHOR/BYLINE/... is
excluded (398 of 1,162 removed; all six audit-derived sanity checks pass)".

It is not solved. Re-running that cross-reference reproduces exactly 398
flagged names — the pipeline agrees with Phase A — but two of the audit's own
six staff cases still came through as clean:

- **Alex Kellogg** — labelled `ALEX KELLOGG` in all 74 of its occurrences.
- **Brian Unger** — labelled `BRIAN UNGER` in all 162.

A label-based filter cannot see them, because there is no role marker
anywhere. The transcript **summary** does name them: "a group of teens ...
talk to *NPR's Alex Kellogg*", "*our humorist Brian Unger* examines ...".

A regex-only stream over all 463,596 summaries (9 seconds, no JSON parsing)
now supplies a second, independent staff signal, in two tiers so that outside
journalists interviewed as experts are not thrown away:

- **tier 1, exclude** — network-owned phrasing: `NPR's X`, `X, NPR News`,
  `NPR ... correspondent X`, `our humorist X`. **94 subjects.**
- **tier 2, flag for review only** — a bare role word next to the name with no
  network possessive. **166 subjects.**

Measured against the hand audit: tier 1 catches Kellogg, Dade, Sutherland and
Unger, with **zero false positives on the 11 subjects the audit judged
genuine**. Combined with the label filter, **all 6 known staff cases are now
excluded (was 4 of 6).** Tier 2 lands on Dexter Filkins, Gustavo Arellano and
Mary Kate Cary — precisely the three the audit itself called borderline
outside-journalist/recurring-pundit — which is why it flags rather than cuts.

Output: `data/mediasum_index/staff_summary_v2.csv`.

## Step 6 — The rebuilt pool

`experiments/build_candidate_pool_v2.py` reapplies the Phase A pool definition
to the repaired inputs. A subject is **clean** if it has no staff evidence
from either filter, is not an initial-only or artifact label, is not an
ambiguous initial, has >= 2 name tokens, and stays under the top-500
celebrity/staff head cutoff (19,032 guest words) *after* merging.

| step | Phase A | Phase B |
|---|---|---|
| pool rows / canonical subjects | 1,162 | 1,153 |
| clean | 634 | **653** |
| clean & >= 3 substantive | 634 (raw counts) | **631** (deduplicated) |
| clean & usable chronology | 579 (old dates) | **578** (fixed dates, deduplicated) |
| **qualifying** | 579 | **578** |
| ...long-tail among them | ~120 (extrapolated from 133 checks) | **137 (all 1,153 checked)** |

Long-tail rate on the clean pool: 168 of 653 = **25.7%**, against Phase A's
19.5% measured on 133 candidates. The rate held up; the extrapolated *count*
(~120) was close to the measured 137 among qualifying candidates.

The headline totals barely moved; what moved is *which* subjects are in them
and how much you can trust the row. 27 CNN subjects entered on repaired dates,
24 left when their recurrence turned out to be same-day re-airings, 94 staff
were removed by the summary filter, 55 fragmented identities were reunited,
and 500 previously unchecked candidates now have a real long-tail flag.

Outputs: `results/stage2_candidate_pool_v2.csv` (all 1,153, every flag and the
full transcript provenance) and `results/stage2_shortlist.csv`.

## The shortlist

`results/stage2_shortlist.csv` — **120 candidates for human review, 90
long-tail and 30 with an article** (a deliberate 3:1 long-tail bias, keeping
some margin if long-tail candidates fail review). Ordered by a residual-risk
score, then by interview count and span.

Every row carries the provenance a reviewer needs: canonical name and id,
every transcript id with its date, programme, duplicate-cluster id and
substantive/not marker; deduplicated substantive count; raw appearance count;
appearances collapsed; span and distinct dates; first/last date; NPR share;
programme count; merged variants with the rule and evidence; the raw label
used; all distinct affiliations seen in the labels; the summary-filter
verdict; and a one-line note.

The note is rule-generated and says why the row is clean or what to check —
`CHECK particle+surname label (effectively a surname)`, `CHECK common
first+last name, collision risk`, `CHECK N interviews across only M
program(s) — recurring panelist rather than interview subject?`, `CHECK
summaries use a role word (outside journalist or recurring pundit?)`,
`merged N label variants (rule)`, `N re-airings collapsed`, `CNN-dominated`.
Of the 578 qualifying, 448 carry no flag at all.

Shortlist profile: median 5 deduplicated substantive interviews, median span
1,338 days, mean NPR share 0.73 — NPR-dominated, as the recon recommended.

Top 20 rows:

| # | id | name | wiki | subst (dedup) | appearances | collapsed | span d | dates | first | last | NPR share | programmes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C00344 | Bob Meadows | long-tail | 33 | 36 | 0 | 691 | 33 | 2005-05-12 | 2007-04-03 | 0.97 | 3 |
| 2 | C00752 | Emira Woods | long-tail | 10 | 17 | 0 | 1138 | 10 | 2005-09-16 | 2008-10-28 | 0.65 | 4 |
| 3 | C02124 | Samer Shehata | long-tail | 9 | 28 | 4 | 1099 | 9 | 2011-01-29 | 2014-02-01 | 0.39 | 17 |
| 4 | C00203 | Anna Greenberg | long-tail | 8 | 25 | 3 | 2312 | 8 | 2007-02-26 | 2013-06-26 | 0.48 | 12 |
| 5 | C00854 | Gregory Johnsen | long-tail | 8 | 20 | 3 | 2052 | 8 | 2009-01-28 | 2014-09-11 | 0.45 | 9 |
| 6 | C01722 | Michael Dimock | long-tail | 7 | 11 | 0 | 512 | 7 | 2013-01-16 | 2014-06-12 | 1.00 | 3 |
| 7 | C00592 | David Gorn | long-tail | 7 | 7 | 0 | 307 | 7 | 2008-02-12 | 2008-12-15 | 1.00 | 3 |
| 8 | C01247 | John Ourand | long-tail | 6 | 6 | 0 | 2958 | 6 | 2009-03-21 | 2017-04-26 | 1.00 | 3 |
| 9 | C01933 | Ramez Maluf | long-tail | 6 | 7 | 0 | 1911 | 6 | 2005-06-09 | 2010-09-02 | 1.00 | 1 |
| 10 | C01538 | Loveday Morris | long-tail | 6 | 6 | 0 | 1313 | 6 | 2013-08-21 | 2017-03-26 | 1.00 | 2 |
| 11 | C00376 | Bridget Johnson | long-tail | 6 | 6 | 0 | 840 | 6 | 2015-10-17 | 2018-02-03 | 1.00 | 1 |
| 12 | C00836 | Glen Loury | long-tail | 6 | 6 | 0 | 435 | 6 | 2005-09-19 | 2006-11-28 | 1.00 | 1 |
| 13 | C01842 | Noam Levey | long-tail | 5 | 6 | 0 | 2746 | 5 | 2012-01-01 | 2019-07-09 | 1.00 | 3 |
| 14 | C01848 | Omer Taspinar | long-tail | 5 | 7 | 0 | 2660 | 5 | 2011-09-06 | 2018-12-18 | 0.71 | 4 |
| 15 | C02218 | Shuja Nawaz | long-tail | 5 | 8 | 0 | 1621 | 5 | 2010-07-09 | 2014-12-16 | 0.88 | 4 |
| 16 | C01752 | Michelle Faul | long-tail | 5 | 5 | 0 | 1404 | 5 | 2014-01-15 | 2017-11-19 | 1.00 | 2 |
| 17 | C00515 | Corey Ealons | long-tail | 5 | 5 | 0 | 1232 | 5 | 2015-10-17 | 2019-03-02 | 1.00 | 1 |
| 18 | C00522 | Courtney Nguyen | long-tail | 5 | 5 | 0 | 1181 | 5 | 2015-06-08 | 2018-09-01 | 1.00 | 2 |
| 19 | C01012 | Jamila Trindle | long-tail | 5 | 5 | 0 | 288 | 5 | 2008-05-19 | 2009-03-03 | 1.00 | 1 |
| 20 | C00563 | Danica Coto | long-tail | 5 | 6 | 0 | 237 | 5 | 2017-05-07 | 2017-12-30 | 1.00 | 2 |

Two of the audit's named model subjects (Michael Dimock, Ramez Maluf) surface
in the top 10 unprompted, which is a reasonable sign the ranking is picking up
the right thing. Row 1, Bob Meadows, is a People magazine staff writer on
News & Notes 33 times in two years — a genuine outside guest by our rules, but
the reviewer should decide whether a magazine writer doing a recurring
segment is an "interview subject".

## Can we deliver >= 80?

Supply is not the constraint. Human review is.

The only honest estimate of review survival comes from scoring this pipeline
against the 20-guest hand audit. Ten of the 20 audited guests reach the
qualifying set:

- **6 the audit judged genuine or conditionally genuine** and we kept: Don
  Pettit, George Miller, Suleika Jaouad, Suzanne DiMaggio, Michael Dimock,
  Ramez Maluf.
- **2 the audit judged borderline** (recurring panel pundits, a design
  judgement rather than a defect): Mary Kate Cary, Vin Weber.
- **2 the audit judged failures** and we still keep: Rick Nelson (the
  confirmed identity collision — two different men under one name) and
  Christopher Reeve (a re-airing-heavy dead celebrity who slips under the
  word-count head cutoff because fragmentation kept each label small).

So **60% survival if panel pundits are rejected, 80% if accepted** — on n=10,
which is a very thin base and should be treated as a range, not a rate.

| target | candidates to review | available | margin |
|---|---|---|---|
| 80 subjects, mixed | 100-134 | 578 qualifying | **4.3-5.8x — comfortable** |
| 80 subjects, all long-tail | 100-134 long-tail | 137 qualifying long-tail | **1.03-1.37x — tight** |

**Read that second row carefully.** 137 confirmed long-tail candidates times
60-80% survival is 82-110 subjects. The target is met in both cases, but at
the pessimistic end the surplus is two subjects. There is no long-tail depth
behind it: 137 is the whole supply at these thresholds, and the shortlist's 90
long-tail rows are 66% of it.

Three consequences the owner should decide on:

1. **The delivered shortlist of 120 (90 long-tail + 30 with an article) yields
   72-96 subjects.** At the pessimistic survival rate that is *below* 80.
   Reviewing ~135-140 rows makes 80 safe. `stage2_candidate_pool_v2.csv` is
   sorted so the next rows can simply be taken.
2. **If all 80 must be long-tail, budget for reviewing all 137** and accept
   that a bad run of collisions could land at 82.
3. **If it comes up short, there is a known reserve** — see caveat 3: 84
   long-tail candidates are blocked purely by a role word in a speaker label
   with no supporting summary evidence. Some are genuine NPR staff, some are
   wrongly-excluded outside journalists like Dexter Filkins. Per-name review
   would recover part of that, at the cost of the guarantee the label filter
   currently gives.

Under Amendment A5 this puts H2 in the confirmatory branch (>= 80 delivered),
with the caveat that the branch is decided by *delivered* subject count after
human review, not by this pool count.

## Honest caveats

1. **Identity collisions are not fixed and cannot be fixed mechanically.**
   Rick Nelson (counterterrorism expert + restaurant critic) still passes
   every filter. The shortlist gives the reviewer the affiliation list and
   full transcript-by-transcript provenance to catch these fast, but catching
   them is human work. The audit rate was ~10%.
2. **Bare-name staff leakage is reduced, not eliminated.** The summary filter
   only fires when a summary happens to describe the person. A correspondent
   who is never named in any summary and never carries a role label remains
   invisible. Two independent filters now have to both miss.
3. **The staff filters over-exclude real subjects.** The Phase A role regex
   matches the word "correspondent" anywhere in a label, so **Brian Bennett**
   (LA Times) and **Dexter Filkins** (New Yorker) — both named model subjects
   by the audit — are dropped as staff. 292 subjects are blocked by a label
   role word alone with no summary evidence, 84 of them long-tail. That is a
   reserve, but not a free one: it is a mix of genuine NPR staff whose
   summaries stayed silent (Cheryl Corley, Celeste Headlee, Alex Cohen) and
   wrongly-excluded outsiders (Joe Nocera, Kim Masters). It would need
   per-name review, and at 578 qualifying we do not need it.
4. **The long-tail flag is a triage signal, not ground truth.** Even after the
   fuzzy pass, an exact-name match to an unrelated person's article yields a
   false "has-page", and a genuinely obscure person can share a name with an
   article subject. The direction of the remaining error is unknown.
5. **Near-duplicate detection is tuned, not proven.** Thresholds (Jaccard
   0.60, containment 0.80) were set by inspection, not validated against
   labelled duplicates. Partial re-airings — different excerpts of one
   interview on different shows — are only partly caught; the requirement of
   >= 3 distinct interview *dates* is what actually protects the recurrence
   count.
6. **Merging is deliberately conservative and therefore incomplete.** 623
   ambiguous initial labels were refused outright. Some are genuine subjects
   we are under-counting. Refusing costs nothing here, because an unmerged
   initial-only label is excluded from the clean pool anyway.
7. **Particle surnames.** 38 qualifying candidates are labels like
   "De Mistura" or "Van Praagh" — a particle plus a surname, which passes the
   two-token test but is really a bare surname with a bare surname's collision
   risk. Flagged, not excluded.
8. **The corpus still ends October 2020**, so the airtight post-cutoff subset
   flagged in Phase A remains unavailable from MediaSum. Nothing here changes
   that.

## Provenance

| what | script | output |
|---|---|---|
| corpus pass: tolerant dates, shingles, staff evidence, co-occurrence | `experiments/curate_scan_v2.py` | `transcript_dates_v2.csv`, `_scan_cache_v2.pkl` |
| dates, merges, dedup, per-subject stats | `experiments/curate_pool_v2.py` | `guest_interviews_v2.csv`, `canonical_map_v2.csv`, `canonical_rejected_v2.csv`, `dedup_map_v2.csv`, `canonical_stats_v2.csv`, `staff_crossref_v2.csv` |
| summary-based staff filter | `experiments/staff_summary_v2.py` | `staff_summary_v2.csv` |
| Wikipedia exact-title check | `experiments/wiki_recheck_v2.py` | `wiki_recheck_v2.csv` |
| Wikipedia fuzzy verification | `experiments/wiki_fuzzy_v2.py` | `wiki_fuzzy_v2.csv` |
| rebuilt pool + shortlist | `experiments/build_candidate_pool_v2.py` | `results/stage2_candidate_pool_v2.csv`, `results/stage2_shortlist.csv` |

All `_v2` data files live in `data/mediasum_index/` (gitignored). No Phase A
CSV was overwritten. No commits were made.

Runtime: corpus scan 2,103 s; curation 8 s; summary staff filter 9 s;
Wikipedia exact 33 s; Wikipedia fuzzy ~420 s; pool rebuild 10 s.
Cost: $0.
