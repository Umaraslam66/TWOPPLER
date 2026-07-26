# H7 date-sanity pass

The H7 feasibility numbers in `BARLOCK_MEASUREMENTS.md` section 6 were computed
from the pool CSV's dates without ever checking them. This is that check.

**Headline: 90 of 90 transcript dates match the raw MediaSum record on the
calendar day. Zero discrepancies. The H7 bin assignment is unaffected.**

Raw numbers: `h7_date_sanity.json`. Script: `experiments/barlock_spotcheck.py dates`.
CPU only, no model calls; one streaming pass over the corpus shared with the
spot-check sheet.

---

## Sample

30 subjects drawn with `random.Random(81)` from the **262 H7-eligible
candidates** (>= 4 dated substantive clusters spanning >= 2 years), sorted by
`canonical_id`. Then up to 3 of each subject's substantive transcripts drawn
from the same generator. **90 transcripts checked, 0 records missing from the
corpus.**

## (a) CSV date vs the MediaSum record's own `date` field

| result | count | rate |
|---|---|---|
| **same calendar day** | **90 / 90** | **1.000** |
| different calendar day | 0 / 90 | 0.000 |
| byte-identical date string | 81 / 90 | 0.900 |
| same day, different zero-padding | 9 / 90 | 0.100 |
| **largest date error observed** | **0 days** | — |

The only difference anywhere is string formatting. MediaSum writes some dates
unpadded and the pool build normalised them — the corpus scan already recorded
this, with 193,925 of 463,596 records needing the padding fix
(`date_qual: ok_padding_fixed`). All nine cases here are that:

```
CNN-227885   csv 2014-04-04   mediasum 2014-4-4    same day
CNN-110494   csv 2006-09-20   mediasum 2006-9-20   same day
CNN-95071    csv 2005-06-03   mediasum 2005-6-3    same day
CNN-104099   csv 2006-03-21   mediasum 2006-3-21   same day
CNN-116258   csv 2007-04-21   mediasum 2007-4-21   same day
CNN-40888    csv 2001-10-02   mediasum 2001-10-2   same day
CNN-223496   csv 2014-01-22   mediasum 2014-1-22   same day
CNN-67697    csv 2003-03-08   mediasum 2003-3-8    same day
CNN-16729    csv 2000-09-28   mediasum 2000-9-28   same day
```

A naive string comparison reports these as a 10% mismatch rate. They are not
mismatches. The programme name also agreed on all 90.

## (b) Date evidence inside the transcript text

**This corpus almost never states its own broadcast date.** Openings read
"today's Washington Post", "a week or so ago", "this morning" — relative
references, not absolute ones. Measured over the same 90:

| signal | count of 90 |
|---|---|
| a full date or month+day matching the record | 1 |
| the record's own year mentioned anywhere | 8 |
| a relative self-reference (today / tonight / yesterday / this week) | 70 |
| **an anachronism (newest year mentioned > record year + 1)** | **4** |

So corroboration is weak *by nature* and its absence proves nothing. The signal
that does work is falsification: a broadcast cannot discuss a year later than
the year it aired. I hand-read all four flagged cases and **all four are
forward-looking references, not date errors**:

```
CNN-314270  recorded 2017-06-12, mentions 2022
   "...The country secured the 2022 World Cup, it has 13 percent of the
    natural gas reserves..."

NPR-16943   recorded 2017-07-24, mentions 2021
   "...the most important part of scoring is really not did you get the number
    right for 2021 - when that year shows up almost certainly it'll be wrong."

NPR-12649   recorded 2012-03-29, mentions 2015
   "...none of this could be adjudicated until somebody had to pay the tax,
    which doesn't happen until 2015, so we could punt this down the road two
    years."

NPR-8282    recorded 2013-06-20, mentions 2015
   "...the end of the Civil War in this country... It'll happen in 2015, Neal.
    We don't - we have two years just to get ready for it."
```

Note that three of the four state the offset out loud ("two years", "until
2015"), which is consistent with the recorded date rather than against it.
**Zero internal contradictions found.**

## Three example rows

| subject | transcript | CSV date | MediaSum date | same day | internal evidence |
|---|---|---|---|---|---|
| C00060 Ahmed Rashid | NPR-44940 | 2010-05-05 | 2010-05-05 | yes | relative self-reference ("today's Washington Post"); no absolute date |
| C00075 Al Baker | CNN-227885 | 2014-04-04 | 2014-4-4 | yes (padding only) | relative self-reference; no absolute date; mentions "the 2022 World Cup" — a forward reference, not an error |
| C01837 Nikky Finney | NPR-8282 | 2013-06-20 | 2013-06-20 | yes | flagged for mentioning 2015, read and cleared: "It'll happen in 2015, Neal... we have two years" |

## Does anything move an H7 bin?

**No.** The bin edges are 183 / 366 / 731 / 1096 days. The largest observed date
error is **0 days**, so nothing shifts and nothing can cross an edge. **0 of the
578 eligible candidates could change bin.**

For scale, here is what an error that was *not* observed would have cost —
subjects with at least one grounding-to-test gap close enough to an edge that
the error could push it across:

| hypothetical date error | subjects at risk (of 578) |
|---|---|
| **0 days (observed)** | **0** |
| 1 day | 18 |
| 3 days | 48 |
| 7 days | 73 |
| 30 days | 203 |

The design is not robust to a sloppy date field — a month of slop would put a
third of the pool at risk — which is exactly why this check was worth running.
It came back clean.

**The H7 bin assignment in `BARLOCK_MEASUREMENTS.md` section 6 survives
unchanged: 262 of 578 candidates eligible, and the per-bin counts
(`<6m` 72, `6-12m` 88, `1-2y` 120, `2-3y` 136, `>3y` 215) stand.**

## Limits of this check

* 30 subjects and 90 transcripts, not a census. At 90/90 the Wilson 95%
  interval on the calendar-day match rate is **0.959–1.000**, so the true rate
  is above 95.9%.
* This verifies the CSV against MediaSum. It does **not** verify MediaSum
  against the broadcaster — if MediaSum itself mis-dated a show, both sides
  agree and this check cannot see it. The internal-evidence pass is the only
  guard against that, and it found nothing, but it is weak because the corpus
  does not self-date.
* The corpus scan recorded **2 records corpus-wide with an implausible year**
  (`date_qual: implausible_year`). None of them landed in this sample, and they
  are 2 of 463,596.
