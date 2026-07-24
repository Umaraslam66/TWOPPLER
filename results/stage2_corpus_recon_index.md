# Stage 2 corpus recon — MediaSum guest index

Generated: 2026-07-24 19:14 CEST  
Script: `experiments/mediasum_index.py`  
Cost: $0 (no paid/LLM API; Wikipedia free API only).

## Source and checksum

- Source: https://drive.google.com/file/d/1ZAKZM1cGhEw2A4_n4bGGMYyF8iPjLZni/view (linked from github.com/zcgzcgzcg1/MediaSum)
- Compressed zip: `data/mediasum/mediasum.zip` — 1468019848 bytes
  - zip sha256: `9a72373725938d217bb97762258cc13bc76abd51ce2a9ddff5fdabd2ebcb82bb`
  - compression: **deflate64 (method 9)** — stdlib zipfile / unzip / ditto / bsdtar all fail; extracted with the `inflate64` wheel via `data/mediasum/extract_deflate64.py`.
- Extracted JSON: `data/mediasum/news_dialogue.json` — 4452348907 bytes
- Records parsed: **463596** (expected ~463.6k). Utterances: 13919244. Records with a util/speaker length mismatch or bad shape: 0.
- ID prefixes: CNN=414176, NPR=49420

## Parsing / normalization rules actually used

- Speaker excluded as **staff** if the whole uppercased label matches `\b(HOST|ANCHOR|CORRESPONDENT|BYLINE|REPORTER|COMMENTATOR)\b`.
- Excluded as **anonymous** if it matches `\b(UNIDENTIFIED|UNKNOWN|...)\b` or reduces to only generic tokens (MALE, WOMAN, AUDIENCE, CALLER, ANNOUNCER, PANEL, ...).
- Name = label with `(...)`/`[...]` removed, then text before the first comma / ` - ` / ` : ` separator.
- Leading honorifics stripped and recorded (DR, MR, MS, SEN, REP, GOV, PRESIDENT, PROF, GEN, REV, and multi-word ones like VICE PRESIDENT, PRIME MINISTER, ATTORNEY GENERAL).
- Normalized = per-word title-case, whitespace collapsed. Raw->normalized mapping kept (652859 distinct raw guest labels).
- **Staff catch-all:** any normalized name in > 100 distinct transcripts reclassified as staff. This removed **2800** names.
  - Top removed (name, #transcripts): Donald Trump (35945); Blitzer (29881); Trump (27626); Barack Obama (22239); Berman (20717); Romans (19094); Costello (18054); Cooper (16963); Whitfield (16838); King (16716); Baldwin (15836); Cuomo (15132); Lemon (14578); Camerota (14433); George W. Bush (14260)

## Staff-filter / population counts

- Distinct guests after all filters: **354184**
- Catch-all removed: 2800 high-frequency names

## Interviews-per-guest histogram

| interviews | guests |
|---|---|
| 1 | 227597 |
| 2 | 52369 |
| 3 | 22477 |
| 4 | 12161 |
| 5+ | 39580 |

## THE KEY NUMBER

Guests with **>= 3 distinct transcripts AND >= 2000 total guest words**: **10869**

## Supplementary cuts

- >= 3 transcripts each individually substantive (>= 300 guest words AND >= 5 turns): **6735**
- >= 4 distinct transcripts: **51741**
- >= 5 distinct transcripts: **39580**
- Of the 10869 key candidates: first-to-last span >= 180 days: **9039**
- Of the 10869 key candidates: >= 3 transcripts with a usable/parseable date: **9146**
- Of the 10869 key candidates: suspiciously generic name (common first + common last): **224**

## Wikipedia long-tail split (key candidates only)

- Checked: 2000 of 10869 candidates (cap 2000; 8869 unchecked).
- **LONG-TAIL (no exact-title Wikipedia page): 265**
- Has a Wikipedia page: 1735

## Top-100 candidates by total guest words

| # | name | interviews | guest words | span days | programs | wiki | generic? |
|---|---|---|---|---|---|---|---|
| 1 | Chopra | 88 | 60357 | 5840 | 28 | page |  |
| 2 | Richard Harris | 85 | 56064 | 5226 | 10 | page | Y |
| 3 | Lankford | 92 | 55775 | 3961 | 17 | page |  |
| 4 | Gallego | 98 | 54446 | 2151 | 17 | page |  |
| 5 | Steyer | 77 | 53934 | 1770 | 22 | page |  |
| 6 | Julie Rovner | 96 | 53544 | 4796 | 7 | page |  |
| 7 | George Curry | 95 | 53112 | 3292 | 6 | page |  |
| 8 | Michael Meyers | 79 | 52833 | 896 | 2 | page |  |
| 9 | Orman | 61 | 51410 | 4146 | 21 | page |  |
| 10 | Mary Frances Berry | 73 | 51367 | 7177 | 9 | page |  |
| 11 | Inslee | 91 | 51186 | 7215 | 23 | page |  |
| 12 | Boies | 78 | 50905 | 7270 | 23 | page |  |
| 13 | Ventura | 67 | 49810 | 5892 | 33 | page |  |
| 14 | Jackson Lee | 96 | 49301 | 7205 | 26 | page |  |
| 15 | Al-Jubeir | 98 | 49278 | 6557 | 36 | long-tail |  |
| 16 | Nina Totenberg | 95 | 49264 | 5555 | 11 | page |  |
| 17 | Dole | 100 | 48268 | 6529 | 37 | page |  |
| 18 | Pixley | 71 | 48219 | 392 | 4 | page |  |
| 19 | Yoho | 65 | 46940 | 2260 | 11 | page |  |
| 20 | Schuch | 45 | 46538 | 31 | 5 | page |  |
| 21 | Moulton | 80 | 46422 | 6849 | 22 | page |  |
| 22 | Barrasso | 89 | 46386 | 4012 | 17 | page |  |
| 23 | Kyl | 97 | 45934 | 6145 | 32 | page |  |
| 24 | Kildee | 90 | 45893 | 1872 | 14 | page |  |
| 25 | Smiley | 61 | 45063 | 7223 | 18 | page |  |
| 26 | Schieffer | 80 | 44481 | 6596 | 22 | page |  |
| 27 | Dreier | 82 | 44433 | 7022 | 29 | page |  |
| 28 | Castor | 89 | 43824 | 4664 | 23 | page |  |
| 29 | Pagliarulo | 64 | 43473 | 386 | 6 | page |  |
| 30 | Parmar | 81 | 43169 | 1357 | 2 | page |  |
| 31 | Jayapal | 89 | 43159 | 1238 | 19 | page |  |
| 32 | O'Donoghue | 88 | 41237 | 4183 | 8 | page |  |
| 33 | Finighan | 65 | 41232 | 1111 | 11 | long-tail |  |
| 34 | Klain | 79 | 41177 | 7292 | 30 | page |  |
| 35 | Sununu | 100 | 40947 | 7093 | 27 | page |  |
| 36 | Gaetz | 93 | 40827 | 1252 | 17 | page |  |
| 37 | Velez Mitchell | 58 | 40784 | 66 | 5 | long-tail |  |
| 38 | Oren | 94 | 40775 | 2399 | 24 | page |  |
| 39 | Hughley | 50 | 40466 | 4586 | 18 | page |  |
| 40 | Bayh | 94 | 40303 | 7065 | 36 | page |  |
| 41 | Coulter | 99 | 40081 | 6299 | 33 | page |  |
| 42 | Metzl | 94 | 39866 | 3599 | 16 | page |  |
| 43 | Williamson | 96 | 39810 | 6655 | 32 | page |  |
| 44 | Bennet | 83 | 39759 | 7140 | 24 | page |  |
| 45 | Sheindlin | 21 | 39576 | 4797 | 9 | page |  |
| 46 | Mike Shuster | 81 | 38983 | 2320 | 7 | page |  |
| 47 | David Wessel | 80 | 38888 | 5252 | 4 | page |  |
| 48 | Somers | 46 | 38392 | 3257 | 22 | page |  |
| 49 | Gilmore | 90 | 38316 | 7254 | 45 | page |  |
| 50 | Weil | 31 | 38117 | 7283 | 16 | page |  |
| 51 | Costas | 90 | 38093 | 6510 | 31 | page |  |
| 52 | Oswald | 86 | 38065 | 7276 | 24 | page |  |
| 53 | Bottoms | 83 | 37922 | 838 | 15 | page |  |
| 54 | C. Cuomo | 59 | 37887 | 2402 | 6 | long-tail |  |
| 55 | Laura Washington | 57 | 37825 | 5290 | 4 | long-tail |  |
| 56 | David Folkenflik | 68 | 37585 | 3835 | 8 | page |  |
| 57 | Dewine | 85 | 37566 | 5094 | 22 | long-tail |  |
| 58 | Frank Langfitt | 78 | 37444 | 4878 | 7 | long-tail |  |
| 59 | Osterholm | 85 | 37241 | 6948 | 21 | page |  |
| 60 | Dickinson | 70 | 37157 | 7175 | 33 | page |  |
| 61 | Kerrey | 77 | 37098 | 7253 | 37 | long-tail |  |
| 62 | Farrow | 70 | 37079 | 4844 | 23 | page |  |
| 63 | Pawlenty | 87 | 36669 | 5989 | 28 | page |  |
| 64 | Curran | 79 | 36659 | 7165 | 24 | page |  |
| 65 | J. King | 75 | 36649 | 4377 | 20 | long-tail |  |
| 66 | Besser | 100 | 36350 | 2200 | 16 | page |  |
| 67 | Barkley | 96 | 36067 | 6510 | 33 | page |  |
| 68 | Tom Bowman | 84 | 36028 | 4760 | 9 | page |  |
| 69 | Gaffney | 77 | 35994 | 5170 | 31 | page |  |
| 70 | Dina Temple-Raston | 40 | 35765 | 1268 | 6 | page |  |
| 71 | Ofeibea Quist-Arcton | 72 | 35733 | 3005 | 7 | page |  |
| 72 | Card | 80 | 35588 | 5938 | 36 | page |  |
| 73 | Lofgren | 74 | 35487 | 3543 | 19 | page |  |
| 74 | Meehan | 100 | 35459 | 6894 | 36 | page |  |
| 75 | Ros-Lehtinen | 67 | 35171 | 6374 | 25 | page |  |
| 76 | Eric Westervelt | 86 | 35132 | 2262 | 6 | long-tail |  |
| 77 | Devine | 94 | 35044 | 5690 | 39 | page |  |
| 78 | Mccartney | 65 | 34779 | 6929 | 27 | page |  |
| 79 | Norquist | 78 | 34774 | 6408 | 30 | page |  |
| 80 | Seacrest | 70 | 34635 | 5252 | 8 | page |  |
| 81 | Brian Naylor | 98 | 34632 | 2017 | 6 | page |  |
| 82 | Rudin | 65 | 34595 | 3675 | 16 | page |  |
| 83 | Ruddy | 62 | 34478 | 6550 | 19 | page |  |
| 84 | Brokaw | 51 | 34454 | 7239 | 25 | page |  |
| 85 | Wexler | 88 | 34419 | 7265 | 30 | page |  |
| 86 | Reno | 80 | 34280 | 6153 | 29 | page |  |
| 87 | Walter Fields | 50 | 34273 | 716 | 3 | page |  |
| 88 | Holbrooke | 68 | 34157 | 6460 | 33 | page |  |
| 89 | Faulkner | 90 | 34029 | 6757 | 22 | page |  |
| 90 | Nat Irvin | 43 | 34019 | 689 | 1 | long-tail |  |
| 91 | Dahlia Lithwick | 64 | 33982 | 6182 | 10 | page |  |
| 92 | Flora Lichtman | 76 | 33573 | 1155 | 1 | long-tail |  |
| 93 | Stefan Fatsis | 63 | 33374 | 3451 | 2 | page |  |
| 94 | Monaco | 93 | 33363 | 5753 | 18 | page |  |
| 95 | Oz | 88 | 33275 | 7116 | 30 | page |  |
| 96 | Gifford | 73 | 33257 | 6877 | 22 | page |  |
| 97 | Crow | 70 | 33174 | 6755 | 25 | page |  |
| 98 | Imus | 64 | 33125 | 4417 | 13 | page |  |
| 99 | Harf | 73 | 33091 | 643 | 8 | page |  |
| 100 | Nye | 73 | 32884 | 5556 | 31 | page |  |

## Caveats and data-quality landmines

- **Name collisions:** a normalized name can conflate two different people (e.g. two 'John Roberts'). Not resolved. `n_programs`, sample titles, and the generic-name flag are in the CSVs for human review. 224 key candidates have a common first+last name.
- **Date quality:** span/chronological-split feasibility depends on parseable dates; see the per-candidate `n_dates` column. Candidates with < 3 usable dates cannot get a clean 3-way chronological split.
- **Wiki-flag confounds:** an exact-name match to an *unrelated* person's page yields a false 'has-page'; genuinely notable people can lack a page. The flag is a rough triage signal, not ground truth.
- **Staff-marker over-exclusion:** the role regex runs on the whole label, so a guest introduced as e.g. '(former war correspondent)' is dropped. This under-counts guests (safe direction for feasibility).
- **Honorific stripping** can merge/rarely mis-split identities; the set is broad but not exhaustive.
- **Title-casing** is per-word; 'McDonald' becomes 'Mcdonald', so a few names look odd but remain internally consistent for grouping.
- **Bare-surname labels dominate the candidate list.** 61.3% of the 10,869 key candidates are single-token surname labels (Chopra, Lankford, Dole, Kyl, ...). CNN in particular labels dialogue lines by last name only. A bare surname conflates every guest who shares it (e.g. 'Dole' = Bob + Elizabeth Dole; 'Chopra' spans 88 transcripts / 28 programs / 16 years and is certainly several different Chopras). **Treat single-token candidates as unreliable identities.** The 4,211 multi-token candidates are the more trustworthy pool.
- **Staff leakage via bare names (verified).** NPR/CNN journalists appear under several labels: `NAME, BYLINE` / `NAME, HOST` (correctly dropped) **but also** bare `NAME` and `NAME reporting` (kept as guests). Confirmed for Totenberg, Rovner, Langfitt, Folkenflik, Naylor. The 100-transcript catch-all only removes the very highest-volume ones; regular correspondents/contributors below that threshold leak into the candidate pool, and in fact dominate the top-100-by-words list (Totenberg, Julie Rovner, David Wessel, Mike Shuster, Brian Naylor, Dina Temple-Raston, Ofeibea Quist-Arcton, Flora Lichtman, Stefan Fatsis, David Folkenflik, ...). These are media professionals, not interview subjects.
- **'reporting' suffix splits identities.** `NINA TOTENBERG reporting` normalizes to 'Nina Totenberg Reporting', a separate row from 'Nina Totenberg'. The trailing `reporting` is not stripped in the main index (it is stripped in the recheck below).

## ADDENDUM — unbiased mid-tail Wikipedia long-tail re-check

The long-tail split above (13.3% = 265/2000) is biased two ways: it checked only the **top 2,000 candidates by word count** (the famous end), and it queried the per-word title-cased *normalized* name — which for the 61% single-token rows is a bare surname that always misses. Both inflate the "has-page" rate and understate the true long-tail share. Re-check script: `experiments/wiki_recheck.py`.

**Sampling (frozen, seed=43):** 500 guests drawn uniformly from the pool `passes_key_filter AND normalized name has >= 2 tokens AND not in the top 500 by total guest words within that >=2-token pool`. Pool sizes: 4,211 two-token candidates -> drop famous top-500 -> 3,711 realistic -> sample 500. Every sampled guest was found in the corpus (500/500).

**Query form:** each guest's **most frequent raw transcript label**, with honorifics + role/affiliation suffix + `reporting` stripped, casing handled as below. Wikipedia API, batches of 50, `redirects=1`, `>=1.1s` sleep, UA `DOPPLER-research-recon/0.1`.

**Casing decision (transparent deviation, with evidence).** MediaSum name labels are ~60% ALL-CAPS. Wikipedia's title API is case-sensitive after character 1, so a literal all-caps query misses every page — verified: `BOB DOLE` -> missing, `MIKE DEWINE` -> missing, `FRANK LANGFITT` -> missing, `BOB KERREY` -> missing. The same names title-cased resolve via Wikipedia redirects: `Bob Dole` -> page, `Mike Dewine` -> `Mike DeWine`, `Ronald Mcdonald` -> `Ronald McDonald`, `Bob Kerrey` -> page. So the raw label is **title-cased only when it is all-caps**; genuinely mixed-case labels (e.g. `Mike DeWine`) are preserved as-is. This departs from a literal "use raw casing" reading because raw casing here is destructive, and the internal-capital worry it was meant to fix is absorbed by Wikipedia redirects. The real false-long-tail driver was the surname-only labels, removed by the >=2-token filter.

**Result:** long-tail (no Wikipedia page) = **128 / 500 = 25.6%**, 95% CI (Wilson) **[22.0%, 29.6%]**. About a quarter of the mid-tail recurring-guest pool has no en.wikipedia page. Example long-tail guests (exactly the Stage-2 target profile — experts, strategists, attorneys, relatives of newsmakers): Ab Stoddard, Adam Swickle (criminal defense attorney), Adolfo Franco (GOP strategist), Aisha Moodie-Mills, Ali Rezaian (brother of Jason Rezaian), Amy Myers Jaffe (Rice University), Andrew Stettner, Bashar Ja'Afari (Syrian UN ambassador). Has-page controls resolved correctly (Al Baker, Alice Rivlin, Alex Padilla, Allen West). Per-guest detail in `data/mediasum_index/wiki_recheck.csv`.

**Residual confound:** a handful of internal-capital surnames with no redirect still misflag (e.g. `Bill Mcinturff` for Bill McInturff). This is rare and only nudges the long-tail rate slightly upward. The has-page/unrelated-page confound from the main check still applies (a page existing at a name does not prove it is *this* person).

**Read-through for Stage 2:** even after discarding all single-token candidates and assuming heavy staff/pundit leakage, the >=2-token candidate pool is 4,211, ~25% of it is genuine long-tail, and the target is >= 30 subjects. Feasibility is not the constraint; identity disambiguation and staff removal are the real curation work.

