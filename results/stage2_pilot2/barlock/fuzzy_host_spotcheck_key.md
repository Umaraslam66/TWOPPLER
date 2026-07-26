# Fuzzy host spot-check — my key

My verdicts for the 20 rows in `fuzzy_host_spotcheck_sheet.md`, in the
same order. Do not read this before filling in the sheet.

Draw: `random.Random(79)` over the 151-pair census in
`fuzzy_host_labels.tsv`, stratified by (ratio band, my verdict) with the
quota in `experiments/barlock_spotcheck.py`. Sheet order is by descending
ratio, so the stratification is not visible in the sheet.

| # | ratio | band | transcript | descriptor | programme | my verdict | rows | cell pop |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.9167 | 0.70-1.01 | CNN-93766 | `CAPITOL GANG` | `CNN CAPITAL GANG` | **staff** | 1 | 5 |
| 2 | 0.7143 | 0.70-1.01 | CNN-166540 | `PRIEST` | `CNN PRESENTS` | **false** | 1 | 7 |
| 3 | 0.7059 | 0.70-1.01 | CNN-25421 | `"USA TODAY"` | `Saturday` | **false** | 1 | 7 |
| 4 | 0.7059 | 0.70-1.01 | CNN-94409 | `HOST "INSIDE POLITICS"` | `JUDY WOODRUFF'S INSIDE POLITICS` | **anchor** | 2 | 14 |
| 5 | 0.7027 | 0.70-1.01 | CNN-48649 | `NEWSNIGHT ANCHOR` | `CNN NEWSNIGHT AARON BROWN` | **anchor** | 3 | 14 |
| 6 | 0.6957 | 0.65-0.70 | CNN-312942 | `CNN AMANPOUR HOST` | `CNN'S AMANPOUR` | **anchor** | 1 | 4 |
| 7 | 0.6923 | 0.65-0.70 | CNN-52391 | `CNN STUDENT BUREAU` | `CNN STUDENT NEWS` | **staff** | 7 | 1 |
| 8 | 0.6667 | 0.65-0.70 | CNN-356090 | `SPECIAL PROSECUTOR` | `CNN SPECIAL REPORTS` | **false** | 2 | 6 |
| 9 | 0.6316 | 0.60-0.65 | CNN-348399 | `CNN CRIME AND JUSTICE EDITORIAL PRODUCER` | `CRIME AND JUSTICE WITH ASHLEIGH BANFIELD` | **staff** | 1 | 2 |
| 10 | 0.6286 | 0.60-0.65 | CNN-151719 | `" 1997) LARRY KING, HOST` | `CNN LARRY KING LIVE` | **anchor** | 2 | 10 |
| 11 | 0.6269 | 0.60-0.65 | CNN-317198 | `PRIMETIME JUSTICE SHOW HOST` | `PRIMETIME JUSTICE WITH ASHLEIGH BANFIELD` | **anchor** | 1 | 10 |
| 12 | 0.6061 | 0.60-0.65 | CNN-94672 | `AIR AMERICA RADIO` | `AMERICAN MORNING` | **false** | 1 | 20 |
| 13 | 0.6000 | 0.60-0.65 | CNN-257253 | `NEWS CORP` | `NEWS STREAM` | **false** | 1 | 20 |
| 14 | 0.5938 | 0.55-0.60 | CNN-24029 | `AUSTIN BUREAU CHIEF, "THE DALLAS MORNING NEWS"` | `Saturday Morning News` | **false** | 1 | 62 |
| 15 | 0.5882 | 0.55-0.60 | CNN-212726 | `NEW JERSEY` | `NEW DAY` | **false** | 18 | 62 |
| 16 | 0.5789 | 0.55-0.60 | CNN-295220 | `CNN THE LEAD HOST` | `THE LEAD WITH JAKE TAPPER` | **anchor** | 1 | 9 |
| 17 | 0.5758 | 0.55-0.60 | CNN-351310 | `CRIME AND JUSTICE PRODUCER` | `CRIME AND JUSTICE WITH ASHLEIGH BANFIELD` | **staff** | 3 | 11 |
| 18 | 0.5641 | 0.55-0.60 | CNN-95703 | `CNN SENIOR POLITICAL ANALYST` | `INSIDE POLITICS` | **staff** | 1 | 11 |
| 19 | 0.5556 | 0.55-0.60 | CNN-104531 | `FREELANCE JOURNALIST` | `CNN RELIABLE SOURCES` | **false** | 1 | 62 |
| 20 | 0.5556 | 0.55-0.60 | CNN-212218 | `CNN NEWS ANCHOR` | `NEW DAY` | **anchor** | 1 | 9 |

Verdict mix in this sample: anchor 7, staff 5, false 8.

`rows` = label rows in the whole corpus carrying this exact pair.
`cell pop` = how many distinct pairs sit in this (band, verdict) cell,
so a cell of 1 means this row IS the cell.

Reading the result: disagreement on `anchor` vs `staff` moves only the
lenient precision column in BARLOCK_MEASUREMENTS.md section 1;
disagreement on either of those vs `false` moves the strict column and
the guard's numbers.
