# Stage 1E budget curves, priced in respondent time

**Descriptive re-analysis of closed Stage 1E data. The Stage 1E bars are settled
and unaffected by anything in this note. No new claims are made here, and none of
these numbers may be quoted as a Stage 1E result.**

## Verdict, up front

**Nothing changes. The static order still wins per second.**

There is no picture here that differs from `results/stage1e_findings.md`, and
nothing for the orchestrator to re-open. That is the expected outcome, and the
reason is structural rather than empirical: every arm asks the same number of
items at checkpoint k, so converting the x-axis from items to seconds multiplies
all four arms by the same factor. A shared rescaling cannot change which arm is
ahead at a matched budget. It moves the tick labels, not the curves.

The one asymmetry that *is* real — the adaptive interviewer makes the respondent
wait while it picks the next question, a static script never does — pushes the
same way the findings already point. Adding thinking time shifts the adaptive
curve to the right and leaves fixed where it is, so it can only widen fixed's
lead. It never narrows it.

What this note actually adds is two things:

1. **Budgets in human time.** Twenty items is about **1.5 minutes** of respondent
   time (central estimate 92 s; plausible range 83–132 s). Twelve items is about
   **1 minute** (58 s). The whole 48-item instrument is about **4 minutes**.
   Stage 1E's frozen grid therefore spans roughly six seconds to a minute and a
   half of a person's attention — a small ask, which is worth knowing when
   reading how modest the lifts are.
2. **A bounded estimate of adaptive's latency tax**, which is somewhere between
   +3% and +840% of interview wall clock depending entirely on how the model is
   served — a range too wide to be a result, but wide in a direction that never
   helps adaptive.

---

## 1. Where the time numbers come from

Stage 1E measured budgets in items. Items are not what a respondent spends;
seconds are. RIASEC's own per-item timings were not recorded (all 48 items sat on
one page), so the per-item cost model is transferred from **MACH-IV**, the
OpenPsychometrics dataset named in PREREGISTRATION.md section 3 for exactly this
purpose.

MACH-IV is a good donor for one specific reason: **its 20 items were presented
one at a time, in a randomised order, with the time on each item recorded in
milliseconds.** Stage 1E's protocol reveals items one at a time too. The
randomised order is a bonus — it means presentation position and item identity
are unconfounded, so position effects can be measured separately from item
effects.

- Source: `https://openpsychometrics.org/_rawdata/MACH_data.zip`, downloaded
  2026-07-26 to `data/mach/` (gitignored). Archive 7,481,589 bytes; contents
  `MACH_data/data.csv` (22,501,950 bytes) and `MACH_data/codebook.txt`.
- 73,489 respondent rows; 73,486 with all 20 presentation positions intact.
- 1,469,720 item responses, each with an answer (`QnA`), a presentation position
  (`QnI`), and an elapsed time in ms (`QnE`).

### The garbage problem, and the trim rule

The raw `QnE` column is exactly as dirty as expected:

| statistic | raw value |
|---|---|
| minimum | −3,574,216 ms (negative) |
| values ≤ 0 | 14 |
| values < 500 ms | 2,052 |
| median | 6,979 ms |
| mean | 14,466 ms (inflated by idles) |
| 99th percentile | 66,259 ms |
| values > 60 s | 17,306 |
| values > 10 min | 1,005 |
| maximum | 749,602,091 ms (8.7 days) |

The mean is meaningless — one respondent left the tab open for over a week.

**Adopted trim rule: keep 500 ms ≤ RT ≤ 60 s.** Below 500 ms a person has not
read the item; above 60 s they have left the screen. This keeps **98.68%** of
observations. Everything downstream uses **medians**, never means.

### Sensitivity to the trim rule: negligible

This is the key robustness check, and it comes out clean. Four alternative rules
against the primary one:

| trim rule | kept | median of the 20 item medians | pooled median | cumulative 20 items |
|---|---|---|---|---|
| none (all values) | 100.00% | 6.82 s | 6.98 s | 140.9 s |
| 300 ms – 120 s | 99.54% | 6.81 s | 6.96 s | 140.5 s |
| **500 ms – 60 s (primary)** | **98.68%** | **6.78 s** | **6.92 s** | **139.7 s** |
| 750 ms – 45 s | 97.79% | 6.76 s | 6.89 s | 139.0 s |
| 1 s – 30 s | 95.60% | 6.71 s | 6.80 s | 137.1 s |

The headline figure moves by **0.10 s (1.5%)** across rules that discard between
0% and 4.4% of the data. Medians are doing the work; the trim rule is almost
decorative. Anyone who prefers a different cutoff gets the same answer.

### Position effect: the first two items are slower

Because MACH randomised presentation order, the median RT at each position is a
clean estimate of warm-up cost:

| position | 1 | 2 | 3 | 4 | 8 | 12 | 16 | 20 |
|---|---|---|---|---|---|---|---|---|
| median RT (s) | 9.72 | 9.58 | 7.62 | 7.24 | 6.79 | 6.56 | 6.41 | 6.36 |

The first two items cost about 50% more than the steady-state rate, which settles
near 6.4 s. The cost model therefore sums **position medians**, not a flat
per-item rate — so short budgets are not under-priced.

### Item length drives response time, and this matters a lot

Across the 20 MACH items, median RT tracks item text length very strongly:

- Spearman correlation, characters vs median RT: **0.92**
- Pearson: 0.92; Spearman on word count: 0.91
- Least-squares fit: **RT ≈ 2.59 s + 0.0633 s per character**

**MACH items average 71 characters. RIASEC items average 32.5.** MACH items are
more than twice as long ("When you ask someone to do something for you, it is best
to give the real reasons for wanting it rather than giving reasons which carry
more weight" versus "Write a song"). Transferring MACH's raw 6.8 s/item to RIASEC
would therefore **overstate** RIASEC's elicitation cost substantially.

Applying the fit at RIASEC's mean length gives **4.65 s per item**, a scaling
factor of **×0.656** on the MACH position medians.

This is interpolation, not extrapolation, for most of the instrument: MACH items
span 22–148 characters, and 37 of RIASEC's 48 items fall inside that range. The
fit is accurate at the short end where it matters — MACH's shortest item ("Most
people are brave.", 22 chars) has an observed median of 3.94 s against a
predicted 3.99 s. The 11 RIASEC items shorter than 22 characters are a genuine
extrapolation and are the weakest part of this step.

### Independent cross-check from RIASEC itself

RIASEC did record `testelapse` — server-side seconds on the 48-item page. That
gives a second, fully independent route to the same quantity, on the *right*
instrument and the *right* population:

| | value |
|---|---|
| respondents (trimmed to 24 s – 40 min) | 143,518 of 145,828 (98.4%) |
| median time for all 48 items | 233 s |
| interquartile range | 175 s – 332 s |
| **implied per-item** | **4.85 s** (p25 3.65 s, p75 6.92 s) |

**4.85 s from RIASEC's own timer versus 4.65 s from the length-adjusted MACH
model — a 4% disagreement.** Two unrelated measurements landing that close is the
strongest evidence in this note that the transfer is sound.

They are not measuring quite the same thing, and the small gap has a plausible
direction: RIASEC's figure is a whole-page timer that includes reading the
instructions, scrolling and submitting, spread over 48 items, while MACH's is
per-item thinking time under one-at-a-time presentation. Those two overheads
roughly offset. Given the agreement, I use **the length-adjusted MACH model as
the central estimate** (it is position-aware, so it prices short budgets
correctly) and treat the unadjusted MACH figure as the upper end.

### Assumption stated plainly, with its limits

**The assumption:** a MACH-IV Likert item and a RIASEC Likert item cost a
respondent about the same number of seconds, once you adjust for how long the
item is to read.

**Why it is defensible:** both are single-sentence agreement/preference items on a
5-point scale, both collected by the same platform in overlapping years
(RIASEC 2015–2018, MACH 2017–2019) from the same kind of self-selected online
volunteer, and the independent RIASEC page timer agrees to within 4%.

**Where it could be wrong:**

- **Different instrument.** MACH asks about cynicism and manipulation; RIASEC asks
  whether you would enjoy a task. Introspecting about morality plausibly takes
  longer than "would I like to lay brick or tile" — which, if true, means these
  numbers are still an over-estimate.
- **Different population.** MACH's sample is the subset who agreed to a follow-up
  survey. Both are unpaid internet volunteers, not a panel or a probability sample.
- **Reading length.** Handled explicitly above, and it was the largest single
  correction (×0.656). It is also the step with the most model in it.
- **Survey replay is not an interview.** This is the findings report's own
  limitation and it applies here with full force. These seconds price *reading an
  item and clicking a number*. A live interviewer asking a question aloud, and a
  person answering in their own words, is a different and almost certainly slower
  activity. **Treat every second in this note as a floor for conversational
  elicitation, not an estimate of it.**

---

## 2. The budget curves in seconds

### Conversion table

Cumulative respondent time to answer k RIASEC-length items, one at a time:

| k | MACH direct (s) | **central estimate (s)** | RIASEC pro-rata (s) | p25 (s) | p75 (s) | central (min) |
|---|---|---|---|---|---|---|
| 1 | 9.7 | **6.4** | 4.9 | 4.2 | 10.2 | 0.11 |
| 2 | 19.3 | **12.6** | 9.7 | 9.6 | 19.4 | 0.21 |
| 4 | 34.2 | **22.4** | 19.4 | 18.4 | 34.0 | 0.37 |
| 8 | 61.8 | **40.5** | 38.8 | 35.1 | 60.3 | 0.67 |
| 12 | 88.4 | **57.9** | 58.2 | 51.3 | 85.2 | 0.97 |
| 16 | 114.2 | **74.9** | 77.7 | 67.1 | 108.9 | 1.25 |
| 20 | 139.7 | **91.6** | 97.1 | 82.6 | 132.0 | 1.53 |

Columns: *MACH direct* is the sum of MACH position medians, no length adjustment
(the conservative upper end). *Central estimate* applies the ×0.656 length
adjustment. *RIASEC pro-rata* is 4.85 s × k from RIASEC's own page timer.
*p25/p75* are the 25th and 75th percentile respondent's actual cumulative time
under the length adjustment — the honest between-person spread, not a confidence
interval on the median.

**Headline: k=20 ≈ 92 seconds, call it a minute and a half, plausibly 83–132 s.
k=12 ≈ 1 minute. All 48 items ≈ 233 s ≈ 4 minutes.**

### Re-expressed curves, expected-value decoding (pre-registered primary)

Lift over the demographics-only baseline. Values are unchanged from
`results/stage1e_findings.md` section (e); only the budget column is new.

| k | respondent time | random | fixed | adaptive | imposter |
|---|---|---|---|---|---|
| 1 | 6 s | +0.0005 | −0.0009 | −0.0113 | −0.0576 |
| 2 | 13 s | +0.0063 | +0.0212 | −0.0001 | −0.0563 |
| 4 | 22 s | +0.0185 | **+0.0374** | +0.0163 | −0.0545 |
| 8 | 40 s | +0.0122 | **+0.0373** | +0.0189 | −0.0693 |
| 12 | 58 s | +0.0349 | **+0.0463** | +0.0392 | −0.0623 |
| 16 | 75 s | +0.0398 | **+0.0585** | +0.0511 | −0.0586 |
| 20 | 92 s | +0.0451 | **+0.0680** | +0.0493 | −0.0627 |

### Re-expressed curves, argmax decoding (binding robustness check)

| k | respondent time | random | fixed | adaptive | imposter |
|---|---|---|---|---|---|
| 1 | 6 s | −0.0040 | −0.0160 | −0.0240 | −0.0858 |
| 2 | 13 s | +0.0011 | −0.0030 | −0.0160 | −0.1063 |
| 4 | 22 s | +0.0054 | +0.0159 | −0.0022 | −0.1113 |
| 8 | 40 s | −0.0276 | −0.0177 | −0.0204 | −0.1504 |
| 12 | 58 s | +0.0001 | −0.0035 | +0.0032 | −0.1391 |
| 16 | 75 s | +0.0111 | +0.0062 | +0.0176 | −0.1303 |
| 20 | 92 s | +0.0039 | **+0.0218** | +0.0059 | −0.1486 |

Figure: `results/stage1e_timecost_curves.png` (both decodings, four arms, time
x-axis with the item grid on the top axis).

### One descriptive reading the time axis makes easier to see

Lift per minute of respondent time, EV decoding. This is just lift divided by
time, so within any row the ranking is identical to the lift ranking — it adds
nothing about which arm wins. What it shows is the **rate of return** falling as
the budget grows:

| k | time (s) | random | fixed | adaptive |
|---|---|---|---|---|
| 2 | 13 | +0.030 | **+0.101** | −0.000 |
| 4 | 22 | +0.050 | **+0.100** | +0.044 |
| 8 | 40 | +0.018 | +0.055 | +0.028 |
| 12 | 58 | +0.036 | +0.048 | +0.041 |
| 16 | 75 | +0.032 | +0.047 | +0.041 |
| 20 | 92 | +0.030 | +0.045 | +0.032 |

The fixed order returns about **0.10 MAE lift per respondent-minute at k=2–4**
and about **0.045 at k=20** — roughly half the rate for the last minute as the
first. Total lift keeps climbing (the findings report's "nothing saturates by
k=20" stands), but the per-minute return more than halves. If respondent time is
the scarce resource rather than accuracy, the first twenty seconds are worth
about twice the last twenty. Descriptive only — no bar attaches, and this is a
ratio of two point estimates with no interval on it.

---

## 3. What the transform cannot change, stated explicitly

**Every arm answers exactly k items at checkpoint k.** Random, fixed, adaptive and
imposter all reveal one item per step; they differ only in *which* item. So the
respondent-seconds column above is identical for all four arms, and applying it
is a single monotonic rescaling of a shared x-axis.

**A shared monotonic rescaling of the x-axis cannot reorder arms at a matched
budget.** If fixed beat adaptive at k=20, fixed beats adaptive at 92 seconds, by
exactly the same margin, with exactly the same p-value. There is no arithmetic
here that could have produced a different answer, and it would have been a red
flag if it had.

So this section is not a result. It is the statement of why section 2 was never
at risk of overturning anything — recorded so nobody reads the seconds tables as
independent evidence.

---

## 4. The one real asymmetry: the respondent waits while adaptive thinks

This is the part of the picture that item counts genuinely hide.

A **static script has zero between-item latency.** Question k+1 is known before
the interview starts. The respondent answers, the next question appears.

An **adaptive interviewer must compute** which question to ask next, and the
respondent sits there while it does.

### What the Stage 1E ledger tells us

From `results/stage1e_findings.md` section (b): the adaptive arm made **840,000
interview-time model calls**, of which **770,000 were item-selection calls**, over
1,000 persons.

770,000 / 1,000 = **770 selection calls per person**. That is exactly
sum over j=0..19 of (48 − j) = 960 − 190 = 770. The match is exact, which
confirms the mechanism: **at every one of the 20 reveals, the policy scores every
remaining unrevealed item, one model call each** — 48 candidates before the first
question, 29 before the twentieth.

### Why the run's own timing cannot answer the latency question

The adaptive arm spent 3.928 node-hours on 840,000 calls. That is **59.4 calls per
node-second** on a 4-GPU node, or 14.9 calls per GPU-second — an implied 16.8 ms
per call if you divide it out.

**Do not divide it out. Batch-GPU throughput is not deployment latency.** That
figure comes from an offline batch job that packs many independent requests into
large batches to keep the GPUs saturated, with no live respondent waiting on any
of them. A single interactive request in a deployed interview gets none of that
amortisation: it pays full prefill and decode on its own. Stage 1E never measured
single-request latency, so **this note cannot supply one**. What follows is a
scenario table with assumed latencies, clearly labelled as such — not a
measurement.

### Bounded scenarios, per interview, at k=20

Against a respondent-answering time of 92 s:

| serving mode | assumed latency | added wall clock | interview grows by |
|---|---|---|---|
| all 770 candidate scores served one at a time | 50 ms/call | 38 s | +42% |
| all 770 candidate scores served one at a time | 200 ms/call | 154 s | +168% |
| all 770 candidate scores served one at a time | 1 s/call | 770 s (12.8 min) | +841% |
| one reveal's candidates batched into a single pass | 0.15 s/reveal | 3 s | +3% |
| one reveal's candidates batched into a single pass | 0.5 s/reveal | 10 s | +11% |
| one reveal's candidates batched into a single pass | 2 s/reveal | 40 s | +44% |

**The honest summary: somewhere between +3% and +840%, and the spread is almost
entirely an engineering choice, not a property of the policy.** If the
implementation batches all remaining candidates for one reveal into a single
forward pass, the tax is small — a few seconds across the interview. If it scores
candidates serially, the tax dominates: the respondent spends longer waiting than
answering. Stage 1E's offline batch harness does not tell us which a deployment
would do.

### Caveats on the whole section

- Every latency above is **assumed, not measured**. Nothing here is a Stage 1E
  number.
- It assumes a deployment keeps the same scoring policy (score all remaining
  candidates). A cheaper approximation — score a shortlist, cache, or use a
  non-model scorer — would cut the tax, and would also be a different policy from
  the one Stage 1E evaluated, so its accuracy would be unmeasured.
- Human tolerance for the delay is not modelled at all. A respondent who waits
  several seconds between questions may disengage, which would degrade answer
  quality in a way no number in Stage 1E captures.

### The matched-wall-clock reading, flagged as unscored

At a matched wall-clock budget the static script asks strictly *more* questions,
because it spends none of the clock thinking. At the steady-state rate of 4.17 s
per late-position item, the added time converts to roughly:

| adaptive's added wall clock | extra items fixed could ask in the same time |
|---|---|
| +3 s (best case, batched) | ~0.7 items |
| +10 s | ~2.4 items |
| +40 s | ~9.6 items |
| +154 s (serial, 200 ms) | ~37 items (more than the rest of the instrument) |

**This is directional only and is not scored.** Stage 1E's frozen grid stops at
k=20, so there is no measured lift for a fixed order at k=22 or k=30 on the
confirm split, and borrowing one from another split would be a split violation.
All that can be said is the direction: fixed's curve was still climbing at k=20
(+0.0463 → +0.0585 → +0.0680 across k=12, 16, 20), so extra items would be
expected to help it rather than hurt it. Expected, not measured.

---

## 5. What this changes

**Nothing in the Stage 1E verdicts.** C1 still fails, C2 still reads
fixed ≥ adaptive, C3 still passes with the decoding caveat intact. The bars are
frozen and this note does not touch them.

The findings report's cost story gains one sentence it did not have: the adaptive
arm's 9.2× GPU multiple was already recorded as a *provider-side* cost, and this
note points out that some unknown fraction of it lands on the **respondent** as
waiting time — a cost the item-count axis makes invisible, and one the static
order does not pay at all.

Restating the verdict so it cannot be missed: **the static order still wins per
second, and once thinking time is included it wins by more.**

---

## 6. Provenance

| item | where |
|---|---|
| **script reproducing every number and the figure** | **`experiments/timecost_note.py`** |
| lift values (unchanged) | `results/stage1e_confirm/analysis.json`, key `lift_over_baseline` |
| closed findings | `results/stage1e_findings.md` |
| frozen bars | `PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md` (commit `3b8dd57`) |
| adaptive call ledger (770,000 selection calls, 3.928 node-hours) | `results/stage1e_findings.md` section (b) |
| MACH-IV raw data | `https://openpsychometrics.org/_rawdata/MACH_data.zip` → `data/mach/` (gitignored), downloaded 2026-07-26 |
| MACH item texts, response-time coding | `data/mach/MACH_data/codebook.txt` |
| RIASEC `testelapse` cross-check | `data/riasec/data.csv`, column `testelapse` |
| RIASEC item texts | `data/riasec/codebook.txt` |
| figure | `results/stage1e_timecost_curves.png` |
| dataset named for this purpose in advance | `PREREGISTRATION.md` section 3 |

**Reproducing this note.** Every number above, and the figure, come from
`experiments/timecost_note.py`:

```
uv run --no-project python experiments/timecost_note.py --check
uv run --no-project --with matplotlib python experiments/timecost_note.py --figure
```

`--check` re-derives the headline figures and aborts if they no longer match the
ones written into this note, so the prose and the code cannot drift apart
silently. It also verifies all 68 item texts verbatim against
`data/mach/MACH_data/codebook.txt` and `data/riasec/codebook.txt`, and
spot-checks three lift values against the frozen artifact. No lift number is
typed into the script; all are read from `analysis.json`, whose arms and
checkpoints are validated against the frozen grid on load.

matplotlib is deliberately **not** added to `pyproject.toml` — it is needed only
for the figure, is imported lazily, and `--no-project --with matplotlib` supplies
it without touching the project environment. Every table reproduces without it.

The method, for anyone reading rather than running it:

1. Read `data/mach/MACH_data/data.csv` (tab-separated). For items n = 1…20, take
   `QnE` (elapsed ms) and `QnI` (presentation position).
2. Keep observations with 500 ≤ `QnE` ≤ 60000.
3. Median `QnE` grouped by presentation position → the 20 position medians.
4. Cumulative cost of k items = sum of position medians 1…k.
5. Multiply by 0.656 — the ratio of predicted RT at RIASEC's mean item length
   (32.5 chars) to MACH's (71.0 chars), under the fit RT = 2.594 + 0.0633 ×
   characters estimated on the 20 MACH item medians.
6. For the p25/p75 band, compute each respondent's own summed time over positions
   1…k (dropping respondents with any trimmed value in that span) and take
   quantiles across respondents.

## 7. Cost

**CPU only. $0.00. No API calls, no GPU, no Gemini, no Leonardo.**

| item | value |
|---|---|
| model calls | 0 |
| API spend | $0.00 (measured, not unknown) |
| GPU node-hours | 0 |
| compute | local CPU, ~3 minutes of Python over 1.47 M MACH response times and 145,828 RIASEC rows |
| network | one 7.5 MB download |

Logged to `results/cost_log.jsonl` as run `stage1e_timecost_note`.
