# Bar-lock measurements (owner decision D-C)

Every number here is a **proposal**. Nothing in this file freezes anything. The
six sections match the six queued items in `results/stage2_pilot/PILOT_REPORT.md`
sections 8.3, 8.6, 8.2, 8.7, 8.1 and the new H7 question.

Everything was measured on CPU, on dev subjects and pool metadata only. No
Gemini calls, no GPU, no confirmatory subjects touched. Raw numbers are in
`results/stage2_pilot2/barlock/*.json`; the scripts are
`experiments/barlock_*.py`.

Total compute: **50 seconds of measurement** plus **19 seconds** for one
streaming pass over the 4.45 GB corpus. Cost in USD: 0.

---

## 1. The fuzzy host threshold (report 8.3)

**Short version: 0.60 is too low, and the bigger problem is not the threshold.**

### What was measured

I replayed D3.2's `program_host_match` over all 28,837 transcripts in the cached
corpus scan and recorded the raw difflib ratio of every *fuzzy-arm* candidate —
every label the literal and normalised arms did **not** already catch.

The fuzzy arm at ratio >= 0.55 fires on only **151 distinct
(descriptor, programme) pairs** in the whole corpus. That is small enough to
label every one of them by hand, so this is a **census, not a sample**. Each
pair was labelled once and the label applies to all its turns.

Three labels:

| label | meaning |
|---|---|
| `anchor` | this speaker presents **this** programme — D3.2's stated target |
| `staff` | house staff of the show (correspondent, analyst, producer): on the host side of the split, but not the interviewer |
| `false` | a guest, a relative of the host, an outside-network person, or parse noise |

### Where the true and false cases separate

| ratio band | label rows | anchor | staff | false | precision (anchor only) | precision (anchor+staff) |
|---|---|---|---|---|---|---|
| 0.55–0.60 | 301 | 13 | 142 | 146 | 0.043 | 0.515 |
| 0.60–0.65 | 65 | 12 | 4 | 49 | 0.185 | 0.246 |
| 0.65–0.70 | 53 | 24 | 7 | 22 | 0.453 | 0.585 |
| 0.70–1.01 | 79 | 49 | 15 | 15 | 0.620 | 0.810 |

There is no clean separation. The distributions overlap heavily below 0.70.

### Precision at each candidate threshold

`changed` = the fires that actually change something, i.e. the labels
`classify_speaker()` does not already call staff. Those are the only turns the
threshold decision moves.

| threshold | rows | anchor | staff | false | strict | lenient | changed rows | changed anchor | changed strict |
|---|---|---|---|---|---|---|---|---|---|
| >= 0.55 | 498 | 98 | 168 | 232 | 0.197 | 0.534 | 302 | 18 | 0.060 |
| **>= 0.60 (current)** | 197 | 85 | 26 | 86 | **0.431** | 0.564 | 120 | 17 | **0.142** |
| >= 0.65 | 132 | 73 | 22 | 37 | 0.553 | 0.720 | 68 | 14 | 0.206 |
| >= 0.70 | 79 | 49 | 15 | 15 | 0.620 | 0.810 | 26 | 1 | 0.038 |

**The current threshold is wrong in a specific way.** At 0.60, 86 of 197 fires
are plain false positives, and of the 120 fires that actually convert a turn
from guest to host, only 17 (14%) are the anchor. The rest are people the rule
should never have touched.

### What the false positives look like

They are not random. Two shapes account for most of them:

```
FALSE  descriptor "NEW YORK"                vs programme "NEW DAY"          (14 rows)
       — REP. PETE KING, GOV. ANDREW CUOMO, REP. TOM REED: politicians
         labelled by their state, on a show whose name rhymes with it.

FALSE  descriptor "LARRY KING'S SON"        vs programme "CNN LARRY KING LIVE" (8 rows)
       — plus WIFE, DAUGHTER, BROTHER, FRIEND: the host's family, who are
         guests on a birthday special.

FALSE  descriptor "POLITICO"                vs programme "INSIDE POLITICS"  (11 rows)
FALSE  descriptor "THE BROOKINGS INSTITUTION" vs "THE SITUATION ROOM"       (5 rows)
FALSE  descriptor "FOX NEWS HOST"           vs programme "CNN NEWSROOM"     (19 rows)
```

And the true ones:

```
ANCHOR descriptor "CNN HOST, AMANPOUR"      vs "CNN'S AMANPOUR"      0.870 (16 rows)
ANCHOR descriptor "DIPLOMATIC LICENSE"      vs "CNN International Diplomatic Linense"
                                                                    0.680 (13 rows)
ANCHOR descriptor "CNN ANCHOR, SATURDAY MORNING" vs "CNN SATURDAY MORNING NEWS"
                                                                    0.727 (14 rows)
```

The full 151-pair label list with my verdict on each is in
`barlock/fuzzy_host_labels.json`; a 42-case stratified sample with two lines of
transcript context each is in `barlock/fuzzy_host_sample.json`. Both are laid
out for spot-checking.

### The case the rule was written for

C00292's `DIPLOMATIC LICENSE` typo sits at **0.68** — 13 label rows, all true
anchors. **A threshold of 0.70 destroys the only case v1.5 exists for.** That is
the hard ceiling on raising the bar.

### A cheap guard that does the work the threshold cannot

Both dominant false shapes are trivially excludable and neither can ever touch a
typo:

1. reject a descriptor containing a relationship marker
   (`'S`, ` OF `, WIFE, SON, DAUGHTER, BROTHER, SISTER, MOTHER, FATHER, FRIEND,
   WIDOW);
2. require the normalised descriptor and programme to share at least one word of
   4 or more letters.

Priced on the same census:

| rule | rows | anchor | false | strict | lenient | anchors lost |
|---|---|---|---|---|---|---|
| >= 0.60, no guard (current) | 197 | 85 | 86 | 0.431 | 0.564 | — |
| >= 0.60 + guard | 119 | 83 | 20 | 0.698 | 0.832 | 2 |
| **>= 0.65 + guard** | 91 | 72 | **4** | **0.791** | **0.956** | **1** |
| >= 0.70 + guard | 57 | 48 | 1 | 0.842 | 0.983 | 1 |

`0.65 + guard` cuts false fires from 86 to 4 and loses exactly one true anchor
(`"PIECE OF ME") VELEZ-MITCHELL` on `JANE VELEZ-MITCHELL`, a malformed label).
The Diplomatic License case passes the guard (`DIPLOMATIC` is shared, no
relationship marker) and clears 0.65.

**Proposed value/decision for bar-lock: raise D3.2's fuzzy threshold to 0.65
AND add the two-part guard above.** If the owner wants a threshold-only change,
0.65 alone (strict 0.553, 37 false rows) is still strictly better than 0.60, and
0.70 must be rejected because it loses the Diplomatic License case.

---

## 2. NER upgrade (report 8.6)

**Short version: real NER installs fine and fixes all three limitations. The
cheap fix gets two of the three for free.**

### Is offline NER possible?

Yes. `uv pip install spacy` (3.8.14) plus
`uv run python -m spacy download en_core_web_sm` (3.8.0, a 12.2 MiB wheel)
both resolved without trouble. `click` had to be installed alongside — spaCy's
CLI needs it and the resolver did not pull it. After install the model runs with
no network at all and survives `uv run`.

Neither package is in `pyproject.toml`; adding them is the owner's call, not
mine.

### The NER variant

D5's NUMBER rule is kept byte-for-byte. Only the name side changes: a
whitespace token is a name token when it overlaps a spaCy entity whose label is
PERSON, NORP, FAC, ORG, GPE, LOC, PRODUCT, EVENT, WORK_OF_ART, LAW or LANGUAGE.
Numeric spaCy labels are excluded so the comparison isolates the name rule.

### How much moves

| corpus | rows | bucket changes under NER | bucket changes under the cheap fix |
|---|---|---|---|
| distractor bank | 652 | **54 (8.3%)** | 4 (0.6%) |
| dev subjects' turns | 2,071 | **195 (9.4%)** | 2 (0.1%) |

Bucket confusion on the bank (D5 -> NER):

```
Z->Z 187   Z->L   4
L->Z  20   L->L 285   L->H   6
           H->L  24   H->H 126
```

Mean density barely moves (0.0514 -> 0.0491 on the bank). The direction is
mostly D5 over-counting: 44 rows fall to a lower bucket, 10 rise.

**Entity-stripped option texts change a lot.** 44 of the 72 committed distractor
option texts (61%), touching all 17 items, come out different under NER. On the
bank, 344 of 652 answers (53%) strip differently. So this is not a cosmetic
change — the A4.2 stripped variant is materially different under NER.

### The three named limitations

| limitation | occurrences found | NER fixes | cheap fix fixes |
|---|---|---|---|
| 1. spelled-out titles glue the next word | 36 glue sites (43 texts, 47 occurrences) | **33 of 36** | **32 of 36** |
| 2. `St.` splits a place name | 2 sites in the bank+turns | **2 of 2** | **2 of 2** |
| 3. sentence-initial lone proper noun survives | **177 sites in 160 texts** | **all — this is what NER is for** | **0 — impossible** |

Limitation 3 is by far the biggest, and it is the one the cheap fix cannot
touch. Real leaks it catches, in the stripped variant that exists to remove
exactly these:

```
"Republicans look out and see a..."   NORP   (survives D5 stripping)
"NAFTA isn't broken. It's done..."    ORG
"Germany is the biggest, the most..." GPE
"Romney's always had a low-grade..."  PERSON
"ISIS has really tapped into what..." ORG
"Spain has been in the crosshairs..." GPE
```

Corpus-wide rates, measured on an independent 98-transcript slice
(8,596 utterances) fetched for the other items:
`St.` in 0.07% of utterances, spelled-out-title glue in 0.99%.

**Proposed value/decision for bar-lock: adopt spaCy `en_core_web_sm` for D5's
name side, keeping D5's NUMBER rule unchanged.** It is the only option that
closes limitation 3, which is the one that leaks real names into the
adversarial-stripped condition 177 times over this small slice. The cost is one
new dependency plus a rebuild of the bank and every option set (nothing has been
scored against the current buckets that matters, same as the v1.4 rebuild).
If the owner refuses the dependency, the curated 26-entry abbreviation subset
(the 25 real abbreviations in HONORIFIC plus `ST`) is the fallback: it fixes
limitations 1 and 2 at 32/36 and 2/2, moves only 4 bank rows between buckets,
and leaves limitation 3 open on the record.

---

## 3. The nickname rule (report 8.2)

**Short version: the resource exists, is tiny, and covers 10x what the hand
table does. It is not a superset — use the union.**

### The resource

`nicknames` 1.0.1 on PyPI, Apache-2.0, data from
`github.com/carltonnorthern/nicknames`. One CSV, **74 KB, 2,691 hand-curated
English name/nickname pairs**. Small enough to check into the repo as a data
file. Two lookup directions matter and the pilot only ever used one:

* forward (`nicknames_of`) — the pool name is formal, the transcript says the
  short form ("Matthew" -> "Matt"). This is what NICKNAME_SUPPLEMENT does.
* reverse (`canonicals_of`) — the pool name is already short, the transcript
  says the formal one ("Ron" -> "Ronald").

### Coverage

Share of first names that get at least one alternate form:

| population | rows | hand table | resource |
|---|---|---|---|
| the pilot's 12 (6 dev + 6 donors) | 12 | 9 (75%) | 9 (75%) |
| the 200-subject bank donor sample | 167 | 13 (**7.8%**) | 118 (**70.7%**) |
| **eligible pool** | 578 | 38 (**6.6%**) | 404 (**69.9%**) |
| full pool | 1,153 | 55 (4.8%) | 765 (66.8%) |

The hand table looks fine on the 12 people it was written for and covers 6.6% of
the pool it would have to serve. That is the scaling problem, quantified.

### The resource is not a superset

| person | first name | hand table | resource | resource misses |
|---|---|---|---|---|
| C00792 Frederic Hof | frederic | fred, freddie, freddy | *(nothing)* | **all three** |
| C02013 / C02006 Robert | robert | bob, bobby, rob, robbie | bill, billy, bob, bobby, dob, dobbin, hob, hobkin, rob, robby, rupert | robbie |
| C01677 Matthew Kroenig | matthew | matt, matty | matt, mattie, matty, thias, thys | — |
| C02040 Ron Christie | ron | ronnie | aaron, aron, cameron, ronald, ronnie, ronny, veronica | — |
| C01316 Joshua Landis | joshua | josh | joe, jos, josh | — |
| C00690 Doris Meissner | doris | *(none)* | dora | — |

"Frederic" (French spelling) is simply absent from the CSV, and "Robbie" is
missing from Robert's entry. **A hand table plus the resource, not the resource
alone.**

### New leaks and over-redaction on the pilot-1 prompts

Scanned: all 68 committed redacted prompts (twin_redacted and imposter_redacted,
both option variants), plus the underlying committed turn files for all 12
people.

| rule | new leaks (prompts) | collateral (prompts) | new leaks (turn files) | collateral (turn files) |
|---|---|---|---|---|
| hand table (current) | 0 | 0 | 0 | 0 |
| resource, forward only | **0** | 3 | 0 | 1 |
| resource, both directions | **0** | 3 | 0 | 1 |
| hand ∪ resource | **0** | 3 | 0 | 1 |

**No new leaks.** The hand table happened to be complete for these 12 people, so
the resource catches nothing extra here — it is the *scale* argument that
carries, not this slice.

The 3 collateral hits are all one word, "bill", pulled in because the resource
lists "bill" as a nickname of Robert:

```
"...we saw the flap that Bill Cosby caused by, some people say..."     C02013
"...over the last few months about this bill. And so, by and large..." C02013 (x2)
```

That is the same class of cost the pilot already accepted for "bob" and "rob".

### Over-redaction at scale

Using the macOS `web2` word list as a generous proxy for "is this also an
ordinary English word":

| population | subjects gaining a form | extra name forms | forms that are ordinary words | subjects with such a form |
|---|---|---|---|---|
| eligible 578 | 404 | 1,661 | 1,169 (70%) | 369 |
| full 1,153 | 763 | 3,190 | 2,247 (70%) | 694 |

Commonest offenders on the eligible pool: `billy` (20 subjects), `mick`/`micky`/
`miguel`/`day`/`dave` (17 each), `rob` (15), `bill` (15). `web2` is a generous
list (it contains "dave" and "jock"), so 70% is an **upper bound** on the risk,
not a measurement of real over-redaction. The reverse direction is where most of
the junk comes from ("Ron" -> Cameron, Veronica, Aaron).

**Proposed value/decision for bar-lock: adopt `nicknames` (checked in as one
74 KB CSV with its Apache-2.0 notice) UNION the existing NICKNAME_SUPPLEMENT,
forward direction only, with the hand table retained as the documented override
for names the CSV misses.** Forward-only avoids the Cameron/Veronica class of
junk while keeping every form the pilot already relied on; the union is required
because the CSV does not contain "Frederic". Reverse lookup should be a separate,
later decision with its own measurement — I did not find a case in the pilot
where it was needed.

---

## 4. The Q-A eligibility floor (report 8.7)

**Short version: a floor of 3 items keeps about 70% of the pool. Roughly 405 of
578 candidates survive. Stage 2's >= 80 branch is safe by a wide margin.**

### (a) The 6 dev subjects

| subject | test programme | items | passes floor of 3 |
|---|---|---|---|
| C00792 Frederic Hof | All Things Considered | 5 | yes |
| C02013 Robert Sampson | Talk of the Nation | 4 | yes |
| C02124 Samer Shehata | Weekend Edition Saturday | 4 | yes |
| C02006 Robert Harris | Morning Edition | 3 | yes |
| C01677 Matthew Kroenig | Talk of the Nation | 1 | **no** |
| C00292 Bassir Pour | DIPLOMATIC LICENSE | 1 | **no** |

4 of 6 pass. Note the committed `qa_items.jsonl` for C00292 holds **1** item,
not 0 — the report's "0" predates the D3.1-r2 / D3.2 re-extraction, and SPEC
v1.4 already records that the burn does not flip on that drift.

### (b) The full eligible pool, sampled

60 candidates drawn with `random.Random(73)` from the 578 eligible rows with the
6 dev subjects removed, sorted by `canonical_id`. Each was split by D2, its test
transcript's turns extracted by D3/D3.1-r2/D3.2 and its items by D4 — the same
code the pilot ran. All 60 extracted cleanly (no split failures, no missing
records).

Item-count distribution:

```
items  0  1  2  3  4  5  6  7  12
subj   9  3  6 14 16  5  3  3   1
```

| floor | pass | rate | Wilson 95% | projected of 578 | projected 95% |
|---|---|---|---|---|---|
| >= 1 | 51/60 | 0.850 | 0.739 – 0.919 | 491 | 427 – 531 |
| >= 2 | 48/60 | 0.800 | 0.682 – 0.882 | 462 | 394 – 510 |
| **>= 3** | **42/60** | **0.700** | **0.575 – 0.801** | **405** | **332 – 463** |
| >= 4 | 28/60 | 0.467 | 0.346 – 0.591 | 270 | 200 – 342 |
| >= 5 | 12/60 | 0.200 | 0.118 – 0.318 | 116 | 68 – 184 |
| >= 6 | 7/60 | 0.117 | 0.058 – 0.222 | 67 | 33 – 128 |

**Even the bottom of the interval at a floor of 3 is 332 candidates.** The
>= 80-subject confirmatory branch is not at risk from this floor. A floor of 5
would be, and a floor of 6 clearly is.

Why items get dropped, aggregated over the 60: `not_interrogative` 190,
`question_too_short` 42, `answer_too_short` 32, `intro_host_turn` 18. Same
shape as the pilot — the cue filter is the binding constraint, not answer
length.

### The "prefer one-on-one programmes" clause

Measured, not asserted. Proxy: a test transcript with no `other`-role turns at
all is a two-person interview; anything with `other` turns is a panel,
roundtable or reported package.

| shape | n | mean items | pass floor of 3 | pass rate |
|---|---|---|---|---|
| one-on-one | 35 | 3.51 | 31 | **0.886** |
| multi-speaker | 25 | 2.96 | 11 | **0.440** |

The preference is real and large: a one-on-one test interview is twice as likely
to clear the floor. It is also almost free — 58% of the sampled pool is already
one-on-one.

**Proposed value/decision for bar-lock: floor of >= 3 D4-eligible items,
applied at draw time, with a one-on-one test interview as a preference (not a
hard requirement).** Expected yield 405 of 578 (95% CI 332–463), which supports
the >= 80 branch with three-fold headroom. Filtering to one-on-one *only* would
raise the pass rate to 0.886 but shrink the base to ~58% of the pool
(~296 surviving candidates) — still above 80, so the owner can take the harder
rule if item quality matters more than pool size.

---

## 5. Affiliation redaction scope (report 8.1)

**Short version: 32 distinct identity facts survive across 5 subjects.
Removing the host's description of the guest kills two thirds of them for zero
collateral. Removing all organisations costs far more than it buys.**

### What is there

Detector: spaCy ORG/FAC spans, a 62-word role list, and quoted work titles next
to an authorship cue. A mention is "attached to GUEST" when it sits in the same
sentence as the GUEST placeholder AND is closer to GUEST than to any other
PERSON entity (a roundtable host introduces three people in one breath), or when
the host is addressing the guest in the second person.

| arm | prompts | mentions total | attached to GUEST | third party | topic | **distinct identity facts** |
|---|---|---|---|---|---|---|
| twin_redacted | 17 | 294 | 90 | 10 | 194 | **32** |
| zeroinfo_redacted | 17 | 4 | 2 | 0 | 2 | **2** |
| zeroinfo_named | 17 | 4 | 2 | 0 | 2 | **2** |

The 90 attached mentions in the twin arm collapse to **32 distinct facts in 18
distinct sentences**, because 17 prompts share a small pool of grounding
excerpts.

Per subject (distinct facts): C01677 Kroenig 10, C02013 Sampson 9, C02006
Harris 5, C02124 Shehata 5, C00792 Hof 3.

The full 32-row table with sentences is in
`barlock/affiliation_scope.json -> distinct_identity_facts`. The clear ones:

```
ORG   State Department                  GUEST, as a former State Department official, can you...
ORG   the Atlantic Council              GUEST, who's now with the Atlantic Council.
ORG   the Council on Foreign Relations  GUEST is a senior national security fellow at the Council...
ORG   Georgetown University             I'm joined now by GUEST, professor of Middle East politics at...
ORG   the Department of Sociology       GUEST is chairman of the Department of Sociology and professor...
ORG   Harvard                           ...and professor of the social sciences at Harvard.
TITLE Imperium                          GUEST is the author of "Imperium", a novel of ancient Rome.
ROLE  novelist                          Best-selling British novelist GUEST told us he will do so...
```

**My own detector's precision, hand-checked on those 32:** 25 are genuine
identity facts, 7 are not — `the Roman Senate`, `Tahrir Square`,
`the Supreme Constitutional Court`, `the Security Council`, `the president's
remarks from Chicago` are the interview topic, and `the Brooking Institution` /
`co-founder` belong to a third person in a roundtable intro. So read 32 as
"about 25 real leaks, plus 7 the detector over-called".

**The zero-information arms are not clean either**, confirming report 8.1:

```
zeroinfo_redacted  C02013:NPR-9480:70   "You're a professor of social sciences."
zeroinfo_redacted  C02013:NPR-9480:45   "So you heard the president's remarks from Chicago on Friday."
```

The first is a real occupation leak in the arm whose entire job is to carry no
information. 1 of 17 items (6%). The second is my detector over-calling.

### Three scopes priced

* **S0 — none / meter-only.** Today's rule.
* **S1 — host-intro clauses.** In HOST lines only, replace the appositive or
  predicate that describes GUEST when it carries a role word:
  `GUEST, <clause>,` / `GUEST is <clause>.` / `GUEST, as a <clause>,`.
* **S2 — all ORG/FAC spans in HOST lines.**
* **S3 — S1 plus every ORG/FAC anywhere (host and guest) plus quoted titles.**

| scope | mentions removed | prompts changed | attached mentions left | collateral: topical ORGs removed |
|---|---|---|---|---|
| S0 | 0 | 0 / 51 | 94 | 0 |
| **S1** | **23** | 17 / 51 | **38** | **0** |
| S2 | 132 | 21 / 51 | 46 | 84 |
| S3 | 251 | 21 / 51 | 16 | 203 |

Before / after, one example per scope:

```
S1  before  HOST: GUEST, as a former State Department official, can you reflect on any of this?
    after   HOST: GUEST, [DESCRIPTION REMOVED], can you reflect on any of this?

S2  before  HOST: GUEST, as a former State Department official, can you reflect on any of this?
    after   HOST: GUEST, as a former [ORG] official, can you reflect on any of this?
            (leaves "former ... official" — the role survives, only the name of
             the institution goes)

S3  before  GUEST: I suspect that people may have been nervous about the comings and
            goings of the U.N. special envoy Lakhdar Brahimi, who replaced Kofi Annan...
    after   GUEST: I suspect that people may have been nervous about the comings and
            goings of the [ORG] special envoy Lakhdar Brahimi, who replaced Kofi Annan...
            (pure collateral: the U.N. is the topic, not the guest's employer)
```

**S1 is the only scope with zero collateral.** It removes 23 mentions and cuts
attached mentions from 94 to 38 — the remainder are mostly my detector's
false calls plus role words inside guest turns. S2 removes 132 mentions but 84
of them are the interview's own subject matter, and it *still* leaves the role
description standing ("former ... official"), which is the more identifying half.
S3 is worse on both counts: 203 of 251 removals are collateral.

**Proposed value/decision for bar-lock: adopt S1 (host-intro clause redaction),
plus a question-level scrub of second-person role descriptions in the
zero-information arms.** S1 is cheap, zero-collateral, and hits the highest-value
leaks (the host's own one-line résumé of the guest). Do not adopt S2 or S3: they
remove the interview's topic, which is the one thing the twin arms need. The
contamination meter stays load-bearing either way, because S1 does not make the
arm identity-blind — it makes it résumé-blind.

---

## 6. H7 staleness feasibility (new hypothesis)

**Short version: H7 is comfortably confirmatory-eligible. 262 of 578 candidates
meet the draft rule.**

Pure CSV work off `results/stage2_candidate_pool_v2.csv`. Bins: `<6m`, `6-12m`,
`1-2y`, `2-3y`, `>3y`. A subject's "gap" for a grounding cutoff at cluster *k*
is (test cluster date − cluster *k* date); the number of distinct bins those
gaps fall into is how many staleness levels that chronology can support.

### (a) Per dev subject

| subject | dated clusters | first | test | span | bins it can fill | H7 eligible |
|---|---|---|---|---|---|---|
| C00792 Frederic Hof | 3 | 2013-01-08 | 2016-12-14 | 3.9 y | 1 (`>3y`) | no |
| C00292 Bassir Pour | 13 | 2000-03-04 | 2004-12-31 | 4.8 y | 3 (`6-12m`, `2-3y`, `>3y`) | **yes** |
| C02013 Robert Sampson | 3 | 2005-12-23 | 2013-02-19 | 7.2 y | 2 (`2-3y`, `>3y`) | no |
| C02124 Samer Shehata | 9 | 2011-01-29 | 2014-02-01 | 3.0 y | **4** (`6-12m`, `1-2y`, `2-3y`, `>3y`) | **yes** |
| C01677 Matthew Kroenig | 3 | 2012-03-06 | 2013-04-29 | 1.1 y | 2 (`6-12m`, `1-2y`) | no |
| C02006 Robert Harris | 3 | 2006-11-22 | 2017-06-09 | 10.6 y | 2 (`6-12m`, `>3y`) | no |

C02124 is the shape H7 wants — 8 usable cutoffs spread from 210 days to 1,099
days:

```
cutoff 2013-07-06   210 d   6-12m
cutoff 2012-11-24   434 d   1-2y
cutoff 2012-06-14   597 d   1-2y
cutoff 2011-11-25   799 d   2-3y
cutoff 2011-10-13   842 d   2-3y
cutoff 2011-02-12  1085 d   2-3y
cutoff 2011-02-01  1096 d   >3y
cutoff 2011-01-29  1099 d   >3y
```

Note that a long *span* is not what matters — C02006 has 10.6 years and can only
fill 2 bins, because it has 3 clusters. **Cluster count is the binding
constraint, not span.**

### (b) The full eligible pool (578 rows)

Draft H7 rule: **>= 4 dated interview clusters spanning >= 2 years.**

**262 of 578 candidates qualify (45.3%).** That is well past the >= 80 threshold,
so **H7 can be confirmatory.**

Candidates able to fill each bin (any eligible candidate / H7-eligible only):

| bin | any candidate | H7-eligible candidate |
|---|---|---|
| `<6m` | 168 | 72 |
| `6-12m` | 200 | 88 |
| `1-2y` | 250 | 120 |
| `2-3y` | 189 | 136 |
| `>3y` | 364 | 215 |

Candidates that can fill at least *k* distinct bins:

| k | any | H7-eligible |
|---|---|---|
| 1 | 578 | 262 |
| 2 | 425 | 214 |
| 3 | 134 | 121 |
| 4 | 33 | 33 |
| 5 | 1 | 1 |

**The within-subject design is the tight one.** Only 33 candidates can fill 4
bins and 121 can fill 3. A between-subject design (each subject contributes at
one staleness level) has 262 subjects and 72–215 per bin, all comfortably above
80 except possibly the `<6m` cell at 72.

Sensitivity of the headline to the rule:

| rule | candidates |
|---|---|
| >= 3 clusters, >= 1 y | 532 |
| >= 3 clusters, >= 2 y | 438 |
| >= 4 clusters, >= 1 y | 304 |
| **>= 4 clusters, >= 2 y (draft)** | **262** |
| >= 4 clusters, >= 3 y | 215 |
| >= 5 clusters, >= 2 y | 173 |
| >= 6 clusters, >= 2 y | 115 |

Nothing in this range drops below 80, so the rule can be tightened for quality
without losing confirmatory status.

**Proposed value/decision for bar-lock: H7 is CONFIRMATORY-eligible. Keep the
draft rule (>= 4 dated clusters spanning >= 2 years, 262 candidates) and run H7
as a BETWEEN-subject design across 4 bins (`6-12m`, `1-2y`, `2-3y`, `>3y`),
dropping the `<6m` bin.** The within-subject version, which is the stronger
design, is only available for 121 candidates at 3 bins and 33 at 4 bins — that
is exploratory scale, not confirmatory. `<6m` should be dropped because only 72
H7-eligible candidates can fill it and it is the cell most likely to overlap the
test event.

---

## What I could not measure, and why

* **Item 1 — I labelled the census myself.** The 151 pair verdicts in
  `barlock/fuzzy_host_labels.json` are my best judgment from the descriptor, the
  programme, the transcript's other speaker labels and (for 42 of them) two
  lines of what the speaker actually said. Some are genuinely ambiguous: I
  treated CNN staff analysts and correspondents as `staff` rather than `anchor`,
  which is why the two precision columns differ so much in the 0.55–0.60 band.
  Different judgments there would move the lenient column, not the strict one.
* **Item 3 — no new leaks were found because the pilot slice is small.** 68
  prompts and 12 people is not enough to find a leak the hand table missed. The
  scaling case rests entirely on the coverage numbers (6.6% vs 69.9% of the
  eligible pool), which are exact, not on a leak count.
* **Item 3 — over-redaction at scale is an upper bound, not a measurement.** I
  used the `web2` word list as a proxy for "ordinary English word". Measuring the
  real collateral would need the corpus text for all 578 subjects, which is a
  second full corpus pass.
* **Item 4 — 60 of 578 is a sample, not a census.** The Wilson interval at the
  floor of 3 is 0.575–0.801, so the projected count is 332–463 rather than a
  point. A full census would need one streaming pass with ~578 transcripts;
  cheap (the 98-transcript pass took 19 s) but I stayed with the brief's ~60.
* **Item 5 — my leak detector has about 78% precision on its own output.** I
  hand-checked all 32 distinct facts and 7 are over-calls. The scope numbers
  (23 / 132 / 251 removed) inherit that noise proportionally.
* **Item 6 — dates come from the pool CSV only.** I did not re-verify any date
  against the raw corpus, and 2 records in the corpus scan carry an implausible
  year (recorded in the scan cache's `date_qual`).
