# Stage 2 corpus-quality recon — MediaSum transcript audit

What this is: a hand audit of 20 recurring MediaSum "guests", drawn by a
reproducible stratified sample, to check whether the structurally-qualifying
pool is actually usable for Stage 2. I read up to 3 transcripts per guest
(earliest / middle / latest) and judged them myself. No LLM, CPU only, $0.

Scripts: `experiments/mediasum_extract.py` (sampling + per-guest transcript
dumps). Dumps kept on disk at `data/mediasum_index/quality_sample/<slug>/` with
per-guest `_manifest.json` for spot-checks.

## Sampling rule as executed, and pool sizes after each filter

Pool = guests where (a) >= 3 transcripts each individually substantive (>= 300
guest words AND >= 5 guest turns, computed from `guest_interviews.csv`); (b)
normalized name has >= 2 whitespace tokens; (c) NOT in the top 500 by
`total_guest_words`. Then stratify by qualifying-transcript count: 10 with 3-5,
10 with 6-15. Random within strata, seed 42.

| step | count |
|---|---|
| distinct guests in `guest_index.csv` | 354,184 |
| distinct guests appearing in `guest_interviews.csv` (n>=2) | 126,587 |
| after (a) >= 3 substantive transcripts | 6,735 |
| after (b) name has >= 2 tokens | 1,237 |
| after (c) not in top-500 by total words | **1,162** (final pool) |
| of pool: stratum A, 3-5 qualifying | 833 |
| of pool: stratum B, 6-15 qualifying | 252 |
| of pool: > 15 qualifying (in neither stratum) | 77 |

Pool (1,162) is well above the 40-guest floor, so the audit proceeded.
Top-500 cutoff was at 19,032 guest words (everything sampled is below that).

## Per-guest verdicts (n=20, 3 transcripts read each)

Attribution: clean / minor / broken. Substance: substantive / thin / package
(soundbites) / monologue. Same-person across the read transcripts. Staff-leak:
genuine-guest / STAFF-or-contributor.

| # | guest | stratum | qual tx | read | attribution | substance | same-person | staff-leak | one-line note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Alex Kellogg | A 3-5 | 4 | 3 | minor | package | same | **STAFF** | NPR reporter; news packages, signs off "Alex Kellogg, NPR News" |
| 2 | Brian Bennett | A 3-5 | 3 | 3 | clean | substantive | same | genuine | LA Times immigration reporter interviewed as expert; clean one-on-ones |
| 3 | C. Reeve | A 3-5 | 5 | 3 | **broken** | substantive(montage) | same | genuine | Christopher Reeve; speech split across C.REEVE/REEVE/CHRISTOPHER REEVE, bare REEVE shared w/ wife Dana; 2006 tribute re-airs 2002 interview verbatim |
| 4 | Corey Dade | A 3-5 | 3 | 3 | clean | substantive | same | **STAFF** | "NPR national correspondent"; in-studio analysis of his own reporting |
| 5 | Don Pettit | A 3-5 | 3 | 3 | clean | substantive | same | genuine | NASA astronaut on Science Friday; coherent, clean — model subject |
| 6 | Emily Green | A 3-5 | 3 | 3 | minor | package/mixed | **unclear/collision** | **STAFF/contrib** | 2010 "Capitol Public Radio's Emily Green" (CA horse racing) vs 2018-19 Mexico freelance immigration reporter — likely 2 people or radical beat shift |
| 7 | George Miller | A 3-5 | 4 | 3 | clean | substantive | same (sampled) | genuine | Rep. George Miller (D-CA); read set coherent, but index honorifics carry "DR" → aggregate bucket likely conflates a second George Miller |
| 8 | Rick Nelson | A 3-5 | 3 | 3 | clean | substantive | **COLLISION** | genuine | CSIS counterterrorism expert (2010,2012) + Minneapolis Star Tribune restaurant critic (2016) merged into one name |
| 9 | Suleika Jaouad | A 3-5 | 3 | 3 | clean | substantive | same | genuine | NYT "Life, Interrupted" columnist / leukemia patient; coherent, clean — model subject |
| 10 | Suzanne DiMaggio | A 3-5 | 3 | 3 | minor | substantive | same | genuine | Think-tank NK-diplomacy expert (New America→Carnegie); 1 host question misattributed to her in NPR-756 |
| 11 | Allison Aubrey | B 6-15 | 9 | 3 | clean | package | same | **STAFF** | NPR health/food correspondent; reported packages w/ soundbites |
| 12 | Brian Unger | B 6-15 | 15 | 3 | clean | monologue | same | **CONTRIB** | "The Unger Report" — NPR's weekly humorist; solo satire, not interviews |
| 13 | Dexter Filkins | B 6-15 | 7 | 3 | clean | substantive | same | genuine | War correspondent (NYT→New Yorker), external; coherent, clean — model subject |
| 14 | Gustavo Arellano | B 6-15 | 6 | 3 | clean | substantive | same | genuine | "Ask a Mexican"/LA Times columnist; genuine but a recurring NPR-panel regular |
| 15 | JJ Sutherland | B 6-15 | 7 | 3 | minor | substantive | same | **STAFF** | NPR Baghdad correspondent (2006,2009) then games podcaster (2015) — same person, staff + topically incoherent |
| 16 | Mary Kate Cary | B 6-15 | 15 | 3 | clean | substantive | same | genuine | Ex-GHW Bush speechwriter / US News columnist; genuine but recurring NPR-panel regular |
| 17 | Michael Dimock | B 6-15 | 7 | 3 | clean | substantive | same | genuine | Pew Research Center director/VP; coherent polling expert — model subject |
| 18 | P. Castro | B 6-15 | 6 | 3 | **broken** | substantive(dup) | same | genuine | Pedro Castro (brother of Cleveland kidnapper); all 3 read = SAME Savidge interview re-aired same day on 3 CNN shows; label split P.CASTRO/PEDRO.../UNIDENTIFIED MALE |
| 19 | Ramez Maluf | B 6-15 | 6 | 3 | clean | substantive | same | genuine | Lebanese American University journalism professor; coherent Arab-media expert — model subject |
| 20 | Vin Weber | B 6-15 | 9 | 3 | clean | substantive | same | genuine | Ex-Rep/GOP strategist (Mercury Public Affairs); genuine but recurring NPR-panel regular |

## Overall rates (n=20)

- **Clean attribution:** 14/20 = **70%** clean; 4 minor (soundbite/host-turn folding), 2 broken → 90% clean-or-minor.
- **Substantive:** 16/20 = **80%** have real interview/analysis content in the sampled transcripts. But 3 are staff analysis, and 2 of the "substantive" ones (C. Reeve, P. Castro) are duplicated/montage content. Genuine-guest + substantive + non-duplicated deep interviews ≈ 11/20 = 55%.
- **Collision rate:** 1 confirmed (Rick Nelson) + 1 probable/unclear (Emily Green) among the read sample = **2/20 = 10%**; plus George Miller's aggregate bucket carries a collision flag (DR honorific) though the 3 read were coherent → up to 3/20 = 15% if counting aggregate risk.
- **Staff/contributor leakage:** 6/20 = **30%** (Kellogg, Dade, Aubrey, Sutherland = NPR correspondents; Green = public-radio/freelance reporter; Unger = NPR contributor). A further 3 (Weber, Cary, Arellano) are genuine outsiders but recurring NPR-panel pundits — borderline "regular contributor."

## Extrapolated survival and feasibility of 30 clean subjects

Survivors (genuine guest + coherent identity + substantive + non-duplicated + clean/minor attribution): Brian Bennett, Don Pettit, Suleika Jaouad, Suzanne DiMaggio, Dexter Filkins, Gustavo Arellano, Mary Kate Cary, Michael Dimock, Ramez Maluf, Vin Weber (10), plus George Miller conditionally (if the Congressman transcripts are isolated from the bucket) → **~10-11/20 ≈ 50-55%**. If you further exclude the recurring panel-pundits (Weber, Cary, Arellano) as not "deep interview subjects," the pure count is **~7-8/20 ≈ 35-40%**.

Failures (would not survive curation): 6 staff/contributor (Kellogg, Dade, Aubrey, Unger, Sutherland, Green), 1 confirmed collision (Rick Nelson), 2 broken/duplicated celebrity or news figures (C. Reeve, P. Castro).

**Is 30 clean subjects realistic from MediaSum alone? Yes, numerically — but it's a curation-labor problem, not a supply problem.** At ~50% survival on a 1,162-guest structurally-qualifying pool, there are on the order of ~500 candidate survivors (~400 even at the stricter deep-interview bar). Netting 30 clean subjects means human-vetting roughly 60-90 candidates (2-3x oversampling). The binding constraints are: (1) fix the staff filter — 30% leakage of bare-name NPR correspondents; (2) de-duplicate same-day CNN re-airings and posthumous re-broadcasts before counting transcripts; (3) resolve label fragmentation / abbreviated-initial labels; (4) fix CNN date parsing before attempting any chronological split. If a chronological (train-early / test-late) design is required, **strongly prefer NPR subjects** — CNN dates are ~54% unparseable (see below), so time-splits on CNN subjects are unreliable.

## 3 worst examples

1. **Rick Nelson** — one normalized name merges a CSIS national-security/counterterrorism expert ("Rick 'Ozzie' Nelson") with a Minneapolis Star Tribune restaurant critic reviewing deep-fried state-fair food. Confirmed identity collision; a twin built on this bucket would fuse two unrelated people.
2. **C. Reeve** — Christopher Reeve, but his speech is scattered across ≥4 raw labels (C. REEVE / bare REEVE / CHRISTOPHER REEVE / CHRISTOPHER REEVE, ACTOR); bare "REEVE" is shared with his wife Dana ("D. REEVE"); one of the 5 transcripts is actually an interview with Dana (his widow); and the 2006 tribute re-airs the 2002 interview nearly verbatim. Broken attribution + duplication + a celebrity that slipped the top-500 filter precisely because fragmentation kept any single label's word count low.
3. **P. Castro** — Pedro Castro (brother of Cleveland kidnapper Ariel Castro). All three "transcripts" I read are the SAME Martin Savidge exclusive, re-aired the same day (2013-05-13) on Around the World, Starting Point, and The Situation Room. His words are split across P. CASTRO / "PEDRO CASTRO, ARIEL CASTRO'S BROTHER" / UNIDENTIFIED MALE, with a "TV. SAVIDGE" parsing artifact. A one-off news figure whose "recurrence" is pure duplication.

## Ugly surprises (systematic)

- **Staff leakage ~30%, concentrated in bare-name NPR correspondents.** The role regex (`HOST|ANCHOR|CORRESPONDENT|...`) only fires when the label itself carries the marker; NPR labels these people plain ("ALLISON AUBREY", "COREY DADE", "ALEX KELLOGG", "JJ SUTHERLAND"), so they pass as guests. The >100-transcript catch-all misses them because each has <100. The summaries often literally identify them as NPR staff.
- **CNN date-parsing bug.** CNN dates are not zero-padded ("2013-5-13", "2006-3-12"); the index's `parse_date` requires two-digit month/day, so **415,563 of 775,807 CNN interview rows (53.6%) have no parseable date**, vs **0% for NPR**. This silently guts chronological-split feasibility for ~half of all CNN appearances (P. Castro n_dates=0; C. Reeve n_dates=1/5).
- **Same-day multi-show re-airings and re-broadcasts inflate transcript counts**, especially on CNN (P. Castro: one interview × 3 shows; C. Reeve: tribute re-airs old interview). Naive transcript counts overstate recurrence and any time-split leaks. Near-duplicate detection is required before counting.
- **Label fragmentation and abbreviated-initial labels.** Single guests split across multiple raw labels; CNN uses first-initial labels ("C. Reeve", "P. Castro") that both under-count words and invite collisions with other initials.
- **Soundbite/tape folding.** In reporter-narrated packages and produced segments, embedded taped clips get concatenated into the reporter's turn (Emily Green's coyote phone tape, Alex Kellogg's Van de Putte soundbite, JJ Sutherland's game audio), padding the "guest's" word count with words that aren't theirs.
- **Recurring-pundit ecosystem in stratum B.** Several higher-frequency genuine guests are the same rotating NPR panel commentators (Vin Weber, Mary Kate Cary, Gustavo Arellano co-occur on Barbershop / Political Junkie). Coherent and real, but semi-professional talking heads rather than deep interview subjects — and they cluster in the 6-15 stratum.
- **CNN vs NPR quality gap.** Even though CNN is ~93% of raw interview rows, the substantive+recurring pool is NPR-dominated, because CNN "guest" turns are mostly too thin (panel soundbites) to clear the 300-word/5-turn bar. NPR recurring guests skew toward real interview subjects with long responsive turns and specific labels ("Professor RAMEZ MALUF (Lebanese American University)"); the few CNN entries that qualify skew toward celebrities/news-event figures with fragmented labels, broken dates, and re-airings. NPR carries the staff-leak problem; CNN carries the fragmentation/duplication/date problem.
