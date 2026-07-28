# Owner rulings — stop point iii, 2026-07-28

Seven decisions, each with the consequence it carries. This file is the record
of what was decided; it is not a source of truth for any number. Where a
decision points at a report, the report wins.

The earlier rulings of the same date — the two name-resolution defect classes,
deferred — are in [`RULINGS_20260728.md`](RULINGS_20260728.md) and are unchanged
by anything here.

---

## 1. Both write-ups APPROVED. H1's headline is own-vs-imposter, and the magnitude miss stays at the top.

**Both papers are approved** —
[`results/writeups/PAPER1_METHODS.md`](../writeups/PAPER1_METHODS.md) and
[`results/writeups/PAPER2_MAIN.md`](../writeups/PAPER2_MAIN.md).

**The headline contrast for H1 is own twin minus imposter twin.** That is the
contrast [Amendment 3 C3](../../PREREGISTRATION_AMENDMENT_3.md) makes primary,
and it clears every bar it is held to: both significance legs, both channels,
both models, and the frozen magnitude unit (+0.0751 cosine against ≥ +0.05).

**The magnitude miss stays top-placed and at equal size.** The frozen magnitude
text names **own minus zero-information** as H1's registered contrast, and on
the primary model in channel 1 that contrast reads +0.0378 cosine against
≥ +0.05 — NOT MET. That sentence keeps its position at the top of Paper 2, in
its own subsection, at the same prominence as the pass. It is not moved down,
not folded into a limitations list, and not softened by the contrasts that did
meet the bar.

**The tension between those two sentences is a post-freeze governance
ambiguity, and it is recorded as one.** Amendment 3 C3 made own-vs-imposter the
primary contrast. The Addendum-A magnitude text, written for the same
instrument, names own-vs-zero-info as H1's registered contrast. Both are frozen,
neither was written to override the other, and the conflict only became visible
once the numbers landed on opposite sides of the bar.

**Resolution: report both contrasts fully, never choose between them.** No
back-selection of whichever contrast clears the bar, and no quiet retirement of
the one that does not. Every place the H1 result is quoted carries both the
pass and the miss. A dated note recording the ambiguity sits in Paper 2 §1.1.

## 2. H2 is WITHDRAWN. H5 ran as an owner-directed substituted analysis under caps.

**H2 (selection matters) is withdrawn as a documented deviation.** Three
reasons, on the record:

- It was **never run**. No confirmatory selection-policy arms were ever
  generated, so there is no data to be unresolved about.
- It was **superseded by the instrument change**. H2's bar was written for
  forced-choice accuracy; forced choice was killed by pre-committed kill rule
  ([Amendment 3 C1](../../PREREGISTRATION_AMENDMENT_3.md)), and the bar did not
  transfer.
- **Stage 1E already answered the selection-policy question at lower cost.**
  Adaptive item selection did not beat random ordering on the survey corpus, and
  that was a powered null, not a shortfall
  ([`stage1e_findings.md`](../stage1e_findings.md)).

The withdrawal follows the pattern Amendment 2 B9.b used to withdraw H4:
documented, dated, named as a deviation rather than left silent.

**H5 (calibration) was not withdrawn. It ran as a substituted analysis under an
owner-issued cap** of $0.50 API and 0.2 node-hours. The outcome is in
[`H5_CALIBRATION.md`](H5_CALIBRATION.md) and is stated plainly here:

- The **registered estimator is UNTESTED under the cap**. It could not be run —
  every confirmatory generation is at temperature 0.0, so the registered k = 10
  agreement rate is a constant, and running it properly needs a fresh generation
  run costing 5.6× the node-hour cap and 9.0× the API cap.
- **No pass/fail verdict on registered H5 is claimed anywhere.** The frozen
  ECE ≤ 0.10 bar is not applied.
- The **substituted analysis is reported as its own line**, exploratory
  throughout, never pooled with or presented as the registered estimator. It
  spent $0.00 and 0.00 node-hours.

## 3. The exploratory D_min = 3 arm was ordered and run. H6's verdict is unchanged.

**Ordered by the owner after the registered numbers were rendered**, as
exploratory diagnostic colour. It is **not** the pre-committed sensitivity arm:
that arm's tripwire (part-2 FOLLOW-UP overturn rate > 20%) did not fire — the
measured rate is 18.33%.

**H6's verdict does not move.** It stays **DESCRIPTIVE ONLY — neither
pre-written reading is applied; H6 UNRESOLVED at confirmatory scale on this
corpus**. No bar is applied to any number in the arm and nothing in it is
claimable. Record: [`H6_REPORT.md` §11](H6_REPORT.md).

What it added: direction matches the registered contrast in all four cells
including the B = 400 sign reversal, and eligibility halves again (24 → 12
subjects at B = 1,000). That is the supply dependency seen from a third angle.
It also produced an unplanned reproducibility finding, recorded in the same
section.

## 4. The orchestrator's two co-audit rulings are CONFIRMED. Two errata are APPROVED for filing.

**Confirmed, both:**

- **The 120-row tranche sizing.** The frozen text sets a floor of ≥ 60 rows, not
  a ceiling. The owner raised the H6 part-2 tranche from 60 to 120 **while still
  blind**, before any co-audit label existed, so the enlargement adds power
  without adding bias.
- **H6's magnitude inheritance via B3's mirror clause.** B3 sets H6's interesting
  bar as "≥ +5 points accuracy (mirrors H2's magnitude bar)". When the bar lock
  re-set the magnitude units for continuous scales (≥ +0.05 cosine, ≥ +0.09
  stance points), H6 inherits the re-set units through that same mirror clause.
  H6 is held to the continuous units, not to a dead accuracy figure.

**Two errata are approved for filing** in a new correction file at the repository
root, [`PREREGISTRATION_ERRATA.md`](../../PREREGISTRATION_ERRATA.md): a path typo
in Amendment 3 C1, and the missing equal-subject-set guard in B7's pre-declared
pooled crossover statistic. **Frozen documents are never edited** — the errata
file is the correction channel, and both entries record that the frozen
definitions were applied as written for this project.

## 5. Future-version inputs are recorded with no action. The staff reserve is CLOSED AS MOOT.

**Recorded, no action this cycle:** the two name-resolution defect classes
(C02240, C02521), the rubric tensions surfaced by the judge audit, and the 106
subjects the reserve sheet auto-recommends for re-admission. All three are
inputs to **any future corpus version** and none of them changes a number in
this one.

**The staff-reserve spot-check is CLOSED AS MOOT for this project version.**
Reasons:

- It gates **only** re-admission of the 292-subject reserve. Nothing else in the
  project depends on it.
- The **corpus is final for this version**. The confirmatory draw is made, the
  run is complete, and re-admitting anyone now would alter the drawn cohort
  after the draw — the exact thing the frozen draw procedure exists to prevent.
- The **106 auto-re-admit candidates stay recorded** in
  [`staff_reserve_spotcheck.md`](../staff_reserve_spotcheck.md) and
  [`staff_reserve_dossiers.csv`](../staff_reserve_dossiers.csv) for any future
  corpus revision. Nothing is deleted; the sheet is closed, not discarded.

Closed as moot means the human spot-check is **not owed** for this version. It
is not "skipped" and it is not a deviation: there is no decision left for it to
gate.

## 6. The OSF registration is LIVE.

**Registered 2026-07-28 at https://osf.io/qz28m**, on the associated project
https://osf.io/74bq3.

**Name mapping, stated once so it is never guessed at:** DOPPLER is the internal
codename used throughout the pre-registration, the results record and the
`src/doppler` package. **TWOPPLER** is the name the OSF registration carries.
They are the same project.

**What the registration is and is not evidence of.** It postdates Stage 1,
Stage 1E, and the Stage 2 H1/H7 confirmatory run — for those it is a
retrospective deposit, and the before-data evidence remains snapshot v4's
per-document git commits and sha256es. It predates the H6 confirmatory-subject
scoring, the H5 substituted analysis, and the D_min = 3 arm — for those it is
prospective.

**The registration summary is not quotable yet.** The registration is inside
OSF's approval window and is not publicly readable. It is never paraphrased as a
quote; a marked slot waits for the owner to paste the verbatim text once it is
public. Propagated to both papers, the confirmatory report header, the project
log and the README.

## 7. Final consistency pass, push, and memory to project-complete.

The documents above are filed, every relative link and shared number is
consistency-passed across both papers and the project log, the repository is
pushed to origin, and the project memory moves to its project-complete state.

The one residual open item after this pass is **pasting the registration summary
quote once OSF makes it public**. Everything else on the open list is either
closed or explicitly carried to a future corpus version.
