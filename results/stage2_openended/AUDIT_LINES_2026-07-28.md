# Audit lines — judge spot-check, fuzzy-host, H6 (2026-07-28)

The owner's recorded audit lines and their scoring. Three deviations,
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
SAME→DIFFERENT). Per the owner's rule those rows go to the owner
verbatim BEFORE any trust bar is proposed, so the addendum's judge
trust bar slot is **[PENDING]**. For calibration: under the B2.2
pattern (raw ≥ 0.85, κ ≥ 0.6) the measured concordance would currently
FAIL on raw agreement for every line — the flagged rows are the
evidence on which the owner rules whether that reflects a judge
defect, auditor error, or rubric-boundary behaviour (A6 is a case
where rubric boundary rule 5 sides with the judge's UNCLEAR).

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
