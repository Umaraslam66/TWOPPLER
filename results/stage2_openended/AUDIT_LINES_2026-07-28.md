# Audit lines — judge spot-check, fuzzy-host, H6 (2026-07-28)

The owner's recorded audit lines and their scoring. Four deviations,
all documented, none silent:

- **D1** — the human judge tranche is **sheet A only** (17 of 51 rows),
  owner time constraint. The full 51 rows carry the LLM co-auditor line.
- **D2** — the fuzzy-host 20-row spot-check is **fully substituted** by
  the out-of-family LLM co-auditor (no human line exists for it).
- **D3** — the H6 classifier audit runs as an LLM co-audit (Opus 5,
  blind to the key) with a **disagreement-triggered human tranche**:
  if co-auditor-vs-classifier agreement clears the B2.2 bar (≥ 85% raw,
  κ ≥ 0.6) the part-1 gate is satisfied with D3 recorded; below the
  bar, everything stops and a 30-row human tranche stratified on the
  disagreements is built for the owner.
- **D4** — the parameter-5 auditor line on the fresh D/E tranche is a
  **rubric-briefed out-of-family LLM line** (Claude; the frozen rubric
  sha `85c7c990…bff64d1` read in full, key never opened),
  owner-directed, substituted for the owner's own rubric-in-hand labels
  that §2 anticipated. Same pattern as D1–D3.

The co-auditor for lines 2 and 3 of the judge sheets and for the fuzzy
sheet is Claude (out-of-family from the generator, both scored models,
and the judge). Keys were never opened by any auditor; the owner
labeled sheet A before any key was read.

## 1. The lines, verbatim

**Human (owner), sheet A:**
A1 DIFFERENT · A2 SAME · A3 DIFFERENT · A4 SAME · A5 SAME · A6 DIFFERENT
· A7 SAME · A8 SAME · A9 DIFFERENT · A10 DIFFERENT · A11 DIFFERENT ·
A12 DIFFERENT · A13 SAME · A14 DIFFERENT · A15 SAME · A16 SAME · A17 SAME

**LLM co-auditor, all 51 rows:** sheet A identical to the human line
(concordance **17/17** — the two lines are reported separately, never
pooled, and the concordance is stated).
B1 SAME · B2 UNCLEAR · B3 DIFFERENT · B4 SAME · B5 SAME · B6 SAME ·
B7 DIFFERENT · B8 SAME · B9 DIFFERENT · B10 DIFFERENT · B11 SAME ·
B12 DIFFERENT · B13 SAME · B14 SAME · B15 SAME · B16 SAME · B17 SAME
C1 DIFFERENT · C2 SAME · C3 DIFFERENT · C4 DIFFERENT · C5 DIFFERENT ·
C6 SAME · C7 DIFFERENT · C8 DIFFERENT · C9 SAME · C10 SAME · C11 SAME ·
C12 SAME · C13 DIFFERENT · C14 SAME · C15 SAME · C16 SAME · C17 SAME

Low-confidence flags, recorded verbatim: **B2, B5, B15, C7, C9, C12,
C14**. Outcome: 5 of the 7 flagged rows are judge disagreements (B2,
B15, C7, C9, C12); B5 and C14 agree. The co-auditor's stated
uncertainty tracks the actual hard rows.

## 2. Scoring against the judge (key: `judge_spotcheck_key.json`)

| line | raw agreement | Cohen's κ | n |
|---|---|---|---|
| human vs judge (sheet A) | 0.7647 | 0.556 | 17 |
| LLM co-auditor vs judge (all) | 0.7843 | 0.596 | 51 |
| — sheet A | 0.7647 | 0.556 | 17 |
| — sheet B | 0.7647 | 0.575 | 17 |
| — sheet C | 0.8235 | 0.660 | 17 |
| pooled auditor labels vs judge | 0.7794 | 0.586 | 68 |

All 11 LLM-line disagreements: A3, A5, A6, A7, B2, B6, B13, B15, C7,
C9, C12.

**The owner's >3 rule TRIGGERED.** The judge disagrees with the
concordant human+LLM sheet-A line on **4 rows**: A3, A5, A6, A7
(auditors→judge: DIFFERENT→SAME, SAME→DIFFERENT, DIFFERENT→UNCLEAR,
SAME→DIFFERENT). Per the owner's rule those rows went to the owner
verbatim before any trust bar was proposed.

### Adjudication (owner, 2026-07-28 — rows were unblind, so they are
### adjudicated, not re-scored)

- **A6 → judge correct** (rubric rule 5: the candidate answers a
  different question and never commits on the central one). This row
  also exposed an **audit-protocol defect, recorded as the owner's and
  not the judge's**: the auditors were briefed with a paraphrase of the
  task, not the frozen rubric text.
- **A7 → judge correct** under rule 3: the real answer is
  hedged-but-committed to "inaction aggravated"; the candidate rejects
  that.
- **A3 → auditors correct**: the judge keyed on surface framing; the
  real answer's central claim is the dependency reversal (the US needs
  Egypt more).
- **A5 → auditors correct**: both texts land "no one will reverse
  Brexit"; optimism-vs-doom is secondary.
- **Net: 2–2.**

### Parameter-5 trust bar — set 2026-07-28, PRE-COMMITTED before its
### measurement exists

The judge passes iff **raw ≥ 0.80 AND κ ≥ 0.60** against a
**rubric-briefed** auditor line on a fresh blind tranche. Rationale on
record: the 51-row audit used rubric-naive auditors, so its 0.76–0.78
is a lower bound, and two of the four adjudicated disagreements were
auditor error. The bar was committed before the fresh tranche was
scored — no bar-shopping. Fresh tranche:
`fresh_tranche_sheet_{D,E}.md`, 18 rows (9 SAME / 9 DIFFERENT by judge
label), seed 611, drawn only from generations unused in A/B/C, arms
3–4 each, both models 9/9, the frozen rubric printed at the top; key
sealed in `fresh_tranche_key.json`. C01677 is absent (single-item
subject, rows lost to the two-per-item cap under strict label
balance — documented in the key). On a fail: rubric/judge iteration on
dev subjects, re-tranche, same pre-committed bar.

### Parameter-5 verdict (2026-07-28, fresh tranche D/E) — FAIL; the
### pre-committed iteration is opened

The rubric-briefed auditor line arrived under **deviation D4** (see
header). Recorded verbatim:
D1 SAME · D2 SAME · D3 SAME · D4 DIFFERENT · D5 DIFFERENT · D6 SAME ·
D7 SAME · D8 DIFFERENT · D9 DIFFERENT
E1 SAME · E2 DIFFERENT · E3 SAME · E4 SAME · E5 SAME · E6 SAME ·
E7 UNCLEAR · E8 DIFFERENT · E9 DIFFERENT
Low-confidence flags, recorded verbatim: **D6, D9, E2, E6**.

**Score vs the judge line** (key: `fresh_tranche_key.json`; scorer:
`experiments/oe1_param5_score.py`): **raw 0.7778 (14/18), Cohen's κ
0.5789.** The pre-committed bar is raw ≥ 0.80 AND κ ≥ 0.60 — both legs
miss. **Verdict, applied mechanically: FAIL.** The pre-committed
on-fail path runs: one rubric/judge iteration on dev subjects,
re-tranche, same bar. No bar movement.

The four disagreements, diagnosed — each is a failure mode the A-sheet
adjudication already ruled on:

- **D6 + E6** (auditor SAME, judge DIFFERENT; both auditor-flagged
  low-confidence; two candidates for the same Brexit item). Both
  answers land "nobody will stop Brexit"; they conflict only on whether
  backing away toward a softer form is feasible. The judge scored the
  second-order feasibility conflict instead of the first-order landing
  — the **A5 error** (adjudicated auditors-correct) repeated, twice.
- **E7** (auditor UNCLEAR, judge DIFFERENT). The candidate refuses the
  question's framing ("my focus isn't on celebrating or despairing
  over a specific outcome") and never commits on the asked issue.
  Rubric rule 5 says UNCLEAR; the judge read refusal-of-framing as
  opposition. It applied rule 5 correctly on A6 — the application is
  inconsistent, not absent.
- **E9** (auditor DIFFERENT, judge SAME). A pick-one question ("who
  lost most"). The REAL answer picks the U.S.; the candidate picks
  "the international community as a whole" (Turkey among the listed
  actors) and merely also notes U.S. credibility loss. The judge
  matched on that side claim — the **A3 "keyed on surface framing"
  error** again.

Direction note: 3 of 4 disagreements are the judge over-calling
DIFFERENT. The auditor self-flagged 2 of the 4 disagreements (D6, E6)
plus two rows that agreed (D9, E2). The judge line carries no UNCLEAR
on this tranche by construction (9/9 draw); the auditor produced one.

**The iteration, executed 2026-07-28 per the pre-committed path:**

- **Rubric r2 draft** — `rubric_r2_draft.txt`, sha256
  `ad050d1a75b038fc63ee162fe74862fd8f99c895e2b39b3af56f24bdea102464`,
  status PROPOSED. Three targeted edits, one per failure mode: rule 1
  gains a first-order-ask clause for multi-part questions (D6/E6 —
  codifies the A5 adjudication); rule 5 gains a
  rejecting-the-premise-is-not-opposition clause (E7); new rule 8 for
  pick-one questions (E9 — codifies A3). The reply format gains a
  CENTRAL line (the judge names the central issue it scored) — this
  requires a one-line parser widening (accept CENTRAL before LABEL)
  and re-pins the judge config at bar-lock; the rest of the pinned
  config (temp 0.0, `thinking_budget=0`, 512 tokens) is unchanged.
- **Re-tranche** — `fresh_tranche_r2_sheet_{F,G}.md`, 18 rows, seed
  613, generator `experiments/oe1_r2_tranche.py` (byte-identical rerun
  verified), drawn only from combos unused in A/B/C AND D/E, key
  sealed in `fresh_tranche_r2_key.json`. **Supply caveat, said
  loudly:** the unused pool holds only 4 judge-DIFFERENT rows, so the
  recipe's shortfall rule fired — balance by r1 labels is 9 SAME / 4
  DIFFERENT / 5 UNCLEAR. The dev pool is nearly out of judge-DIFFERENT
  generations: if this iteration also fails, a further label-balanced
  re-tranche requires new dev generations, not another draw.
- **Key caveat** — the key's balance labels are r1-judge labels (the
  only judge line in existence at build time). The r2 judge is re-run
  on exactly these 18 rows after the owner approves the r2 diff and
  before the auditor line is scored; pass/fail = r2-judge vs the
  rubric-briefed auditor line, same bar.

**STOPPED at the pre-committed stop.** Awaiting the owner: (1) approve
or amend the r1→r2 diff; (2) the r2 judge run on the 18 rows (needs
the Gemini key — no `.env` is present in the repo); (3) rubric-briefed
labels on sheets F/G.

### r2 adoption and the second round (2026-07-28, later the same night)

**The r1→r2 diff is APPROVED as drafted** (owner review on record:
edits confined to the three adjudicated failure modes, all
strictness-increasing; CENTRAL line + parser widening with a
regression test). r2 is the proposed judge rubric pending parameter 5.
The rubric file is byte-unchanged by adoption, so the pinned sha
`ad050d1a…102464` and the sha printed on sheets F/G stay valid; the
approval lives here and in `audit_scores.json`, not in the file.

Two ambiguities resolved conservatively, logged:
- `.env` provides `MODEL_NAME=gemini-3.5-flash-lite` — that is the
  robustness scored model, not the judge. The judge stays the pinned
  `gemini-3.5-flash` (addendum parameter 2); `MODEL_NAME` is ignored
  for judging.
- The F/G auditor line arrived before the r2 judge run. The judge is
  blind by construction (stateless API calls that see only redacted
  QUESTION/REAL/CANDIDATE, never a label), so the ordering cannot leak
  the auditor line into the judge; noted rather than hidden.

Runner: `experiments/oe1_r2_judge.py` (pinned config verbatim from
`stage2_oe1.py`: gemini-3.5-flash, temp 0.0, `thinking_budget=0`, 512
tokens, same redaction path, one candidate per stateless call; parser
self-test runs before any API call; committed before the run so the
tooling predates the result). Regression branch rule, owner-set: if r2
breaks more than 2 of the 14 previously-correct D/E rows, STOP —
overfitted.

## 3. Fuzzy-host sheet — LLM co-auditor line (D2)

Line (rows 1–20): staff · false · false · anchor · anchor · anchor ·
staff · false · staff · anchor · anchor · false · false · false ·
false · anchor · staff · staff · false · anchor.
Recorded notes: row 10 — video-clip parse noise, but the speaker is
the programme's own host; row 1 — recurring panelist scored staff.

**Concordance with the census key: 20/20. Nothing is overturned.**
Addendum precondition 1 is satisfied via D2.

The frozen 0.65+guards rule applied to this sheet fires on 6 rows
(1, 4, 5, 6, 7, 8); on this line its strict precision (anchor only) is
**3/6 = 0.500**, lenient (anchor+staff) **5/6 = 0.833**. Caveat stated
plainly: the sheet was stratified to oversample hard cells (band ×
verdict, many cells of population 1), so on-sheet precision is NOT an
estimate of census precision — the committed census-wide measurement
(precision 0.79, false fires 86 → 4, one true anchor lost) remains the
operative number, and what this line establishes is that the labels it
rests on survive an independent blind audit.

## 4. H6 co-audit (D3)

Co-auditor: Opus 5 subagent, blind (read only the sheet and the frozen
rubric, sha256 `053b96cb…8a24da` — matches the recorded RUBRIC_V1 hash;
the key, the classifier records, and the sampler were off-limits).

Result over all 120 rows: **raw agreement 0.8667 (104/120), Cohen's κ
0.7333 — CLEARS the B2.2 bar (≥ 0.85, κ ≥ 0.6). Part-1 gate satisfied
with D3 recorded; the escalation rule does not trigger, no human
tranche is built.**

Detail: disagreement rows 8, 9, 11, 15, 17, 18, 20, 30, 37, 42, 44,
51, 60, 61, 92, 101. Direction is lopsided — 15 of 16 are co-auditor
NEW-TOPIC vs classifier FOLLOW-UP — and 11 of 16 fall inside the
co-auditor's 35 self-flagged low-confidence rows. Plain reading: the
classifier's FOLLOW-UP boundary is somewhat looser than a strict
rubric application; within-bar, but the part-2 confirmatory tranche
should look at exactly this boundary.

## 5. Machine-readable

`audit_scores.json` — all lines, all pairwise scores, fire lists, and
the H6 tally.
