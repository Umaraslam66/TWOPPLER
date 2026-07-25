# 16PF data recon (CPU only, report only)

Authorized by PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section D. This is a
recon, not an experiment. No model was called, no split was drawn, no bar is
proposed, nothing was committed. Addendum B is the owner's to lock.

**How to reproduce every number below:** `uv run python experiments/recon_16pf.py`.
It prints all of it and writes `results/16pf_recon_numbers.json`. Each section
here names the JSON key it came from. Download provenance and hashes are in
`data/16pf/PROVENANCE.txt` (data/ is gitignored, as it should be).

---

## The short version

- **49,159 rows** in the file. **34,641 usable** (70.5%) under RIASEC-style
  cleaning. The single biggest cut is missing answers: 28% of rows have at
  least one unanswered item.
- **163 items**, all on the same **1-5 Likert agree scale**, 0 = not answered.
  The 163 figure quoted in Amendment A6 is correct.
- **No genuine cross-domain split exists inside this file.** 16PF is one
  domain — personality — measured 163 ways. There is no interests block, no
  vocabulary block, no second instrument. The only splits available are
  factor-vs-factor inside personality, and the honest ones are noticeably
  more correlated than the RIASEC→TIPI boundary the registered design uses.
- **Demographics are much thinner than RIASEC's**: 3 fields (age, gender,
  country) against RIASEC's 14. The demographics-only baseline is not
  comparable to Stage 1E's, and will be a weaker baseline.
- The shipped codebook is **missing one item** (P10) and names no factors.
  Both gaps are filled here by exact item-text matching against the IPIP's own
  key, then checked against the data.

---

## 1. Item scales

JSON: `raw_table`, `codebook`, `observed_item_values`.

| Fact | Value |
|---|---|
| Item columns in `data.csv` | 163 |
| Items documented in `codebook.html` | 162 (P10 missing) |
| Response scale | 1-5, integer |
| Missing code | 0 ("1-5;0 if missed", codebook's own words) |
| Values ever observed in item cells | 0, 1, 2, 3, 4, 5 — nothing else |

Anchors, verbatim from the codebook (the same sentence is repeated on all 162
documented items, so there is no per-item variation):

| Code | Label |
|---|---|
| 1 | strongly disagree |
| 2 | disagree |
| 3 | neither agree not disagree (sic — typo is theirs) |
| 4 | agree |
| 5 | strongly agree |

Wording of the prompt: each item is a first-person statement ("I know how to
comfort others") and the respondent rates agreement. Contrast with RIASEC,
where the 48 seed items are rated for *liking a task* on 1=Dislike / 3=Neutral
/ 5=Enjoy, and the 10 TIPI targets are 1-7 agreement. So 16PF has **one scale
throughout**, and it is a 5-point agreement scale.

Cell-level value counts across all 8,012,917 item cells: 0 appears 98,919
times (1.23%), then 1: 847,566 / 2: 1,833,239 / 3: 1,576,459 / 4: 2,565,547 /
5: 1,091,187. Note the response distribution is lumpy — 2 and 4 are far more
common than 3 — which matters for any baseline that hedges to the middle.

### Reverse-keyed items

The shipped codebook says **nothing** about keying. Recovered as follows, and
labelled clearly because it is a recovery, not a citation:

1. Parsed the IPIP's own 16PF key page (`data/16pf/ipip_16pf_key.html`, from
   https://ipip.ori.org/new16PFKey.htm, retrieved 2026-07-25). It lists 16
   scales, each with its "+ keyed" and "– keyed" statements.
2. Matched dataset item texts to IPIP statements by exact normalized string
   equality. **162 of 163 matched exactly.**
3. Checked the result against the data with no reference to either source: for
   every item, correlate the raw item against the sign-corrected mean of the
   *other* items in its factor. A + keyed item should come out positive, a –
   keyed item negative. **163 of 163 agree. Zero disagreements.**

Reverse-keyed counts per factor are in the table in section 2. Weakest items
on that check (smallest |r|, i.e. the ones carrying least of their own factor):
H4 (r = +0.050, "I don't like action movies"), E9 (−0.194), H10 (−0.201),
M5 (+0.234), E7 (−0.260). H4 is essentially unrelated to its own scale.

### The missing item, P10

`codebook.html` documents A1 through P9 and then jumps straight to the country
key. P10 has no entry. After matching the other 162 items, **exactly one IPIP
statement was left unmatched**: "Have a good word for everyone.", – keyed, in
the EMOTIONALITY scale — which is exactly the scale the P items belong to. One
undocumented item, one leftover statement, same scale, so they pin each other.

Two pieces of support, both from the data:
- P10 correlates negatively with the rest of factor P, as – keying predicts.
- Treating P10 as – keyed raises factor P's split-half reliability from 0.738
  to 0.822 and its alpha from 0.723 to 0.806. Treating it as + keyed depresses
  both.

**Still labelled inferred.** If Addendum B uses P10's text in a prompt, that
text comes from the IPIP page, not from the dataset's own codebook. The
cautious option is to drop P10 and work with 162 items.

---

## 2. Factor structure

JSON: `factors`.

The raw header groups items by a leading letter, A through P — sixteen groups.
These letters are **positional, not Cattell's canonical factor letters**
(Cattell's are A, B, C, E, F, G, H, I, L, M, N, O, Q1-Q4 — note there is no
D, J, K or P in that set). Do not assume the file's letter is the factor's
letter.

Every one of the 16 letter groups maps to exactly one IPIP scale — no group
splits across scales, no scale is split across groups. That is a clean result
and it means the letter prefix *is* the factor grouping.

| File letter | Items | n | Reverse-keyed | Cattell factor | IPIP scale name | IPIP alpha |
|---|---|---|---|---|---|---|
| A | A1-A10 | 10 | 3 | A Warmth | WARMTH | .80 |
| B | B1-B13 | 13 | 5 | B Reasoning | INTELLECT | .76 |
| C | C1-C10 | 10 | 5 | C Emotional Stability | EMOTIONAL STABILITY | .85 |
| D | D1-D10 | 10 | 4 | E Dominance | ASSERTIVENESS | .81 |
| E | E1-E10 | 10 | 4 | F Liveliness | GREGARIOUSNESS | .78 |
| F | F1-F10 | 10 | 5 | G Rule-Consciousness | DUTIFULNESS | .84 |
| G | G1-G10 | 10 | 5 | H Social Boldness | FRIENDLINESS | .80 |
| H | H1-H10 | 10 | 4 | I Sensitivity | SENSITIVITY | .73 |
| I | I1-I10 | 10 | 4 | L Vigilance | DISTRUST | .80 |
| J | J1-J10 | 10 | 3 | M Abstractedness | IMAGINATION | .80 |
| K | K1-K10 | 10 | 5 | N Privateness | RESERVE | .86 |
| L | L1-L10 | 10 | 3 | O Apprehension | ANXIETY | .80 |
| M | M1-M10 | 10 | 5 | Q1 Openness to Change | COMPLEXITY | .82 |
| N | N1-N10 | 10 | 3 | Q2 Self-Reliance | INTROVERSION | .73 |
| O | O1-O10 | 10 | 5 | Q3 Perfectionism | ORDERLINESS | .81 |
| P | P1-P10 | 10 | 3 | Q4 Tension | EMOTIONALITY | .76 |

(P's "3" includes the inferred P10.)

**Where this mapping comes from — stated plainly.** The grouping into 16 sets
of items comes from the dataset itself (the column names). The *factor names*
and the *keying* are **not in the shipped codebook** and had to be brought in
from the IPIP key page, then matched item-text to item-text. The match is
162/163 exact plus one by elimination, and the keying survives an independent
data check at 163/163. So: grouping = from the data; names and keying =
inferred, by a verifiable text match, not from memory.

**Global factors: absent.** The file contains no global/second-order factor
columns and no computed scale scores at all — just the 163 raw items plus 6
non-item fields. Any factor score has to be computed. (Cattell's five global
factors are a feature of the commercial instrument; this is the IPIP
equivalent and does not ship them.)

---

## 3. Usable respondent counts

JSON: `cleaning`.

Rules mirror `clean_riasec()` where the fields exist, plus the checks RIASEC
does not need. Applied in order, so each row shows what that step costs *after*
the ones above it.

| Step | Rule | Rows in | Lost | Rows out |
|---|---|---|---|---|
| start | — | — | — | **49,159** |
| 1 items in range | all 163 items in 1-5 (0 = missing) | 49,159 | **13,778** | 35,381 |
| 2 age in range | age in [14, 90] — same window as `clean_riasec` | 35,381 | 269 | 35,112 |
| 3 gender present | gender in 1-3 (0 = missed) | 35,112 | 159 | 34,953 |
| 4 country present | non-blank, not A1/A2/O1 (proxy, satellite, other) | 34,953 | 19 | 34,934 |
| 5 accuracy in range | self-reported accuracy in 1-100 | 34,934 | 11 | 34,923 |
| 6 not straight-lining | non-zero SD across answered items | 34,923 | 106 | 34,817 |
| 7 not a duplicate | first occurrence of a given 163-item vector | 34,817 | 6 | 34,811 |
| 8 elapsed plausible | total time in [163 s, 86,400 s] | 34,811 | 170 | **34,641** |

**Usable: 34,641 of 49,159 = 70.5%.**

Each rule alone (independent, so these overlap):

| Rule | Rows it would drop by itself |
|---|---|
| items in range | 13,778 |
| elapsed plausible | 589 |
| age in range | 382 (302 under 14, 80 over 90 — of which 64 are over 120) |
| not straight-lining | 318 |
| not a duplicate answer vector | 277 |
| gender present | 238 |
| country present | 36 |
| accuracy in range | 23 |

**The missing-answer rule dominates everything else, and it is worth a
decision.** Missing answers are concentrated, not spread: the median row has 0
missing, the 90th and 95th percentiles have 2, and the 99th has 83. So a
handful of rows abandoned the test partway. If the owner is willing to tolerate
a few gaps, the pool grows a lot:

| Missing items tolerated per row (all other rules applied) | Usable rows |
|---|---|
| 0 (strict, mirrors RIASEC) | 34,641 |
| ≤ 1 | 43,215 |
| ≤ 2 | 45,769 |
| ≤ 5 | 47,223 |
| ≤ 10 | 47,435 |
| unlimited | 47,799 |

Uncertain / owner's call: RIASEC's rule is all-or-nothing and 34,641 is already
far more than the ~1,000-2,000 person splits Stage 1E uses, so the strict rule
costs nothing operationally. Listed only so the choice is visible rather than
accidental.

Two things RIASEC has that this file does not, both relevant to bot screening:
- **No `uniqueNetworkLocation` field.** RIASEC flags whether a row is the only
  one from its network. 16PF has no such field, so there is no network-level
  duplicate or shared-classroom signal. The 277 duplicate answer vectors above
  are the only duplicate evidence available.
- **No `VCL` validity items.** RIASEC ships three fake vocabulary words as a
  built-in attention check. 16PF ships none. The only self-report quality
  signal is `accuracy`.

---

## 4. What demographics exist, and how they compare to RIASEC

JSON: `demographics`.

**16PF has 3 demographic fields. RIASEC has 14.**

| | 16PF | RIASEC |
|---|---|---|
| Shared | age, gender, country | age, gender, country |
| RIASEC only | — | education, engnat, familysize, hand, major, married, orientation, race, religion, urban, voted |
| Technical / non-demographic | source, accuracy, elapsed | source, uniqueNetworkLocation, introelapse, testelapse, surveyelapse |

Missing from 16PF and notable: `major` (RIASEC's free-text university major,
the richest single string in the RIASEC baseline prompt), plus education,
native-language, marital status, religion, race and urban/rural.

Distribution of the 3 fields on the 34,641 cleaned rows:

| Field | Summary |
|---|---|
| age | min 14, median 21, mean 25.2, max 90 |
| gender | 1 Male 13,650 / 2 Female 20,816 / 3 Other 175 |
| country | 149 distinct; US 17,114, GB 3,607, IN 1,998, CA 1,921, AU 1,819 |
| accuracy (self-report) | min 1, median 90, mean 88.7, max 100 |
| source (referrer) | 1-6, median 2 |
| elapsed | min 163 s, median 757 s, max 86,281 s |

RIASEC cleaned pool for comparison: **130,303** persons of 145,828
(`cleaning_breakdown`: 10,064 dropped for RIASEC items out of range, 2,080 for
TIPI, 2,386 for age, 1,858 for missing country).

**Consequence for the baseline, stated plainly.** Stage 1E's demographics-only
baseline sees 14 fields including free-text major. A 16PF demographics-only
baseline would see 3. That baseline will be weaker, which mechanically inflates
lift over it. The two stages' lift numbers are therefore **not directly
comparable**, and any 16PF replication claim has to say so. This is a design
consequence of the dataset, not something a bar can fix. Flagging it as
something Addendum B should address explicitly.

---

## 5. Seed pool and target domain — the options, neutrally

JSON: `options`, `item_leakage`, `structure`, `riasec_cross_domain_benchmark`.

### First, the structural answer

**There is no second domain in this file.** Every one of the 163 items is a
personality self-report on the same 5-point agreement scale. The only non-item
columns are age, gender, country, source, accuracy, elapsed. So the RIASEC
design's shape — *seed on interests, predict personality* — has no exact
counterpart here. Whatever is chosen will be **personality → personality**.

There is also **no respondent identifier** of any kind, so 16PF rows cannot be
linked to any other OpenPsychometrics file. Cross-dataset seeding (16PF items →
a different instrument's items on the same people) is impossible: zero shared
persons.

### The benchmark to judge options against

The registered RIASEC design's boundary is genuinely wide. Across the 48
interest items × 10 TIPI items:

| RIASEC → TIPI (130,303 persons) | |
|---|---|
| Largest abs(r) between any seed item and any target item | **0.343** (S5 "Help people with family-related problems" ~ TIPI7 "Sympathetic, warm") |
| Mean abs(r) across the boundary | 0.064 |
| Mean, per target item, of its best seed correlate | **0.175** |
| Target items with any seed item at abs(r) ≥ 0.40 | 0 of 10 |

### The options 16PF actually makes possible

Persons available is 34,641 for all of them (the cleaned pool; no split drawn).

| Option | Seed items | Target items | Variants | Persons |
|---|---|---|---|---|
| **A. Hold out one factor** | 153 (150 if B is the target) | 10 (13 if B) | 16 | 34,641 |
| **B. Hold out five factors** | 113 | 50 | many | 34,641 |
| **C. Hold out eight factors** | 83 | 80 | many | 34,641 |
| **D. Within-factor split** | 5 of a factor's 10 | the other 5 | 16 | 34,641 |
| **E. Cross-dataset** | 163 | — | — | **0** |

- **D is disallowed as an outcome** by PREREGISTRATION.md §3 ("within-scale
  prediction is disallowed as an outcome because item redundancy makes it
  trivial"). It is listed for completeness and because it is the exact analogue
  of the A7 known-answer probe, which *is* allowed as a labelled diagnostic.
- **E is impossible**, as above.

### How cross-domain each Option A choice actually is

For each candidate target factor, the strongest correlation between one of its
items and any item in the 153-item seed pool, and the mean over its items of
that best-correlate value (the direct analogue of the RIASEC 0.343 / 0.175
above). Sorted cleanest first.

| Target factor | Cattell name | Max item abs(r) vs seed | Mean per-item best abs(r) | Target items with a seed item ≥ .50 | ≥ .40 |
|---|---|---|---|---|---|
| O | Perfectionism | 0.361 | **0.254** | 0 | 0 |
| H | Sensitivity | 0.434 | 0.295 | 0 | 1 |
| B | Reasoning | 0.399 | 0.318 | 0 | 0 |
| M | Openness to Change | 0.434 | 0.320 | 0 | 1 |
| J | Abstractedness | 0.505 | 0.332 | 1 | 2 |
| D | Dominance | 0.417 | 0.338 | 0 | 2 |
| I | Vigilance | 0.560 | 0.346 | 1 | 1 |
| A | Warmth | 0.476 | 0.356 | 0 | 4 |
| N | Self-Reliance | 0.527 | 0.364 | 1 | 4 |
| F | Rule-Consciousness | 0.505 | 0.367 | 1 | 4 |
| K | Privateness | 0.549 | 0.388 | 1 | 5 |
| E | Liveliness | 0.604 | 0.418 | 3 | 6 |
| P | Tension | 0.612 | 0.421 | 4 | 5 |
| L | Apprehension | 0.552 | 0.441 | 2 | 7 |
| C | Emotional Stability | 0.612 | 0.452 | 3 | 7 |
| G | Social Boldness | 0.604 | **0.521** | 8 | 10 |

Read against the RIASEC benchmark (max 0.343, mean-of-best 0.175): **the
cleanest 16PF option is still leakier than the registered RIASEC design.**
Perfectionism as target comes closest (max 0.361 vs RIASEC's 0.343 — about
equal on the worst pair) but its mean-of-best is 0.254 against RIASEC's 0.175,
so on average every target item has a noticeably closer neighbour in the seed
pool. At the other end, Social Boldness as target is not a cross-domain task at
all: all 10 of its items have a seed item at |r| ≥ 0.40 and 8 have one at
≥ 0.50.

**No option is picked here.** The counts above are what the choice trades off.

### Factor-level correlations, for the same question at scale level

Mean |r| between items inside a factor: 0.321. Mean |r| between the 16 factor
scores: 0.235 — the factors are nearly as correlated with each other as items
are within a factor. 11 of the 120 factor pairs are at |r| ≥ 0.50:

| Pair | r |
|---|---|
| C Emotional Stability ~ L Apprehension | −0.750 |
| G Social Boldness ~ K Privateness | −0.637 |
| E Liveliness ~ G Social Boldness | +0.636 |
| G Social Boldness ~ N Self-Reliance | −0.564 |
| B Reasoning ~ M Openness to Change | +0.563 |
| C Emotional Stability ~ P Tension | −0.550 |
| I Vigilance ~ P Tension | +0.543 |
| D Dominance ~ G Social Boldness | +0.514 |
| E Liveliness ~ N Self-Reliance | −0.512 |
| A Warmth ~ G Social Boldness | +0.512 |
| F Rule-Consciousness ~ J Abstractedness | −0.504 |

The clusters are obvious and they are Big-Five-shaped: an extraversion cluster
(E, G, K, N, and A leaning in), a neuroticism cluster (C, L, P), an openness
pair (B, M). Any Option B or C choice that puts one member of a cluster in the
seed pool and another in the target is predicting a factor from its own
near-twin.

---

## 6. Things that would bite

JSON: `item_leakage`, `structure`, `timing`, `codebook`.

**1. Item redundancy — the big one.** Of 13,203 item pairs, 104 sit at
|r| ≥ 0.50, 28 at ≥ 0.60, and 5 at ≥ 0.70. The worst offenders are near
paraphrases:

| Pair | r | Same factor? | Texts |
|---|---|---|---|
| H1 ~ H3 | +0.829 | yes | "I like to read" / "I read a lot" |
| J9 ~ J10 | +0.767 | yes | "I seldom daydream" / "I seldom get lost in thought" |
| K6 ~ K7 | +0.748 | yes | privateness pair |
| F6 ~ F9 | +0.725 | yes | "I resist authority" / "I oppose authority" |
| P1 ~ P2 | +0.713 | yes | "I get irritated easily" / "I get angry easily" |

Most of that redundancy is inside factors, which the registration already
handles by forbidding within-scale outcomes. But **21 of the ≥ .50 pairs and 2
of the ≥ .60 pairs are cross-factor**, so a factor-vs-factor split does not
automatically escape it. Addendum B should either (a) pick a target factor from
the top of the section-5 table, or (b) name the specific seed items to exclude,
per target. Either way, the exclusion has to be explicit, because the default
"seed on the other 15 factors" leaks.

**2. The registration's own within-scale rule is easy to violate by accident
here.** In RIASEC, "seed on interests, predict TIPI" is unambiguously
cross-domain. In 16PF, every option is personality→personality, and whether it
counts as cross-domain is a judgement about how far apart two factors are —
which is exactly the kind of thing that should be frozen before data, not
argued after. The numbers in section 5 are offered to make that judgement
checkable.

**3. No ceiling is measurable, and no honest split-half either.** There is no
retest, no repeated item, no timestamp beyond one total duration. Self-
consistency cannot be computed. Within-factor split-half *can* be computed
(range 0.641 for E Liveliness to 0.918 for G Social Boldness; alphas 0.670 for
H Sensitivity to 0.904 for G) but that is a within-scale reliability number,
so it cannot serve as the ceiling for a cross-factor prediction. Per Amendment
A2 ceiling is descriptive anyway, so this is a limitation to declare, not a
blocker. Worth noting H Sensitivity is a weak scale (alpha 0.670, mean
within-factor |r| 0.179, and item H4 essentially unrelated to its own factor
at r = +0.050) — it looks like a grab-bag, not a coherent construct.

**4. Response times: one field, whole test only.** `elapsed` is the seconds
between test start and submit. There are **no per-item times**. RIASEC at least
splits its timing three ways (introelapse / testelapse / surveyelapse); 16PF
does not. The realistic time-cost function the registration wanted must still
come from MACH (which does have per-item ms), not from here. Median cleaned
`elapsed` is 757 s over 163 items — about 4.6 s per item — usable as a crude
average only. Raw outliers before cleaning: 449 rows under 163 s, 140 rows over
a day, and a raw maximum of 8,534,589 s (about 99 days) — someone left the tab
open.

**5. The codebook is incomplete and slightly wrong.**
- P10 is undocumented (section 1).
- The codebook calls the duration field `elapse`; the header says `elapsed`.
- The `accuracy` description is garbled: "indicate on a scale from 0000 the
  overall accuracy". Almost certainly 0-100 — 49,136 of 49,159 rows fall in
  1-100 and the median is 90 — but the stated range is unusable as written and
  the 0-100 read is **inferred from observed values**, not documented. Out-of-
  range junk includes 101, 200, 300, 420, 44665, 100000000, 2147483647.
- `age` has 64 rows over 120, up to 2147483647 — same int-overflow garbage
  RIASEC has.
- The codebook names no factors and gives no keying (section 2).

**6. The live test on the website is no longer the archived version.** Fetching
http://openpsychometrics.org/tests/16PF.php today (`curl -sSL
http://openpsychometrics.org/tests/16PF.php`) returns a page describing
**164 statements** with anchors "(1) disagree (2) slightly disagree (3) niether
agree nor disagree (4) slightly agree (5) agree". The 2014 archive has 163
items and anchors "strongly disagree … strongly agree". So the current live
test is a revised instrument. **All item wording and anchors for this study
must come from the shipped 2014 codebook, not from the website.** Getting this
wrong would repeat the cross-scale anchoring surprise that Addendum A section D
was written to avoid.

**7. The 163 figure in Amendment A6 checks out** — 163 item columns exist. But
A6 calls it a "163-item pool" for the seed side. Only 153 of those can ever be
seed items if one 10-item factor is the target (150 if the 13-item Reasoning
factor is the target). Small point, but the number in Addendum B should be the
seed-pool size, not the file's item count.

**8. Sample is thinner and younger than RIASEC.** 34,641 usable vs RIASEC's
130,303 — still ample for 1,000-person splits, so not a constraint, but worth
knowing if Addendum B wants several disjoint splits plus a derivation split.
Median age 21, 60% female, half US.

---

## Provenance

| Number in this report | Where it comes from |
|---|---|
| every count, correlation, and funnel row | `uv run python experiments/recon_16pf.py` → `results/16pf_recon_numbers.json` |
| file hashes, row/column counts, download URL | `data/16pf/PROVENANCE.txt` (written from the same script's section 1) |
| the live-test-page discrepancy (item 6 above) | `curl -sSL http://openpsychometrics.org/tests/16PF.php`, run 2026-07-25 |
| the archive filename `16PF.zip` | `curl -sSL http://openpsychometrics.org/_rawdata/` index page, run 2026-07-25 |

Cost: zero. No API calls, no GPU, no Leonardo. One 3.7 MB download; the
analysis runs on CPU in about 5 seconds.
