# 16PF replication — cancelled

**Decision: the 16PF replication of Stage 1E is cancelled. Addendum B will not
be written. Owner decision, 2026-07-26.**

This is a **documented deviation from PREREGISTRATION_AMENDMENT_1 section A6**,
which said the Stage 1E protocol would be replicated on 16PF after the TIPI
confirm run. The deviation is recorded here in the open, with its reasons and
its cost. It is deferred-then-cancelled, not silent: Addendum A section D
already flagged the deferral and required a data recon first, precisely so this
call could be made on evidence instead of blind. The recon is
`results/16pf_recon.md`; every number below comes from it.

## Why it is cancelled

**1. There is no genuine cross-domain split inside the file.**

Stage 1E's whole design is cross-domain: seed the twin on interest items,
predict a *different* instrument (TIPI personality). 16PF cannot reproduce that
shape. It is one domain measured 163 ways — no interests block, no vocabulary
block, no second instrument, and no respondent id, so it cannot be linked to
another dataset either. Every available option is personality-to-personality.

That collides with the original registration, which disallows within-scale
prediction as an outcome "because item redundancy makes it trivial"
(PREREGISTRATION.md section 3). A replication that has to break the parent
study's own exclusion rule is not a replication.

**2. The cleanest available target is leakier than the design it would
replicate.**

Measured against the registered RIASEC→TIPI boundary (max item-level
correlation 0.343, mean-per-target-item best correlation 0.175). All figures are
absolute correlations:

| option | max item corr. vs seed pool | mean-of-best corr. | target items with a seed item ≥ .40 |
|---|---|---|---|
| RIASEC→TIPI (the registered design) | 0.343 | **0.175** | — |
| 16PF, cleanest target (O Perfectionism) | 0.361 | **0.254** | 0 of 10 |
| 16PF, worst target (G Social Boldness) | 0.604 | 0.521 | 10 of 10 |

The best case is about equal on its single worst item pair but 45% leakier on
average. The worst case is not a cross-domain task at all — every one of its ten
target items has a seed item at 0.40 or above.

**3. The item pool is more redundant, not less.**

Mean absolute correlation between items inside a factor is 0.321. Between the
16 factor *scores* it is 0.235 — the factors are nearly as correlated with each
other as items are within a factor. 11 of the 120 factor pairs sit at 0.50 or
above, the strongest being Emotional Stability ~ Apprehension at −0.750. At item
level, 104 of 13,203 pairs are at 0.50 or above and 21 of those cross factor
boundaries, so "seed on the other 15 factors" leaks by construction rather than
by accident.

**4. Supporting reasons, none of them decisive alone.**

- The demographics-only baseline is not comparable: 16PF carries 3 demographic
  fields against RIASEC's 14 including free-text major. A weaker baseline
  mechanically inflates lift, so a 16PF lift number could not have been set
  beside a Stage 1E one anyway.
- No per-item response times (one whole-test `elapsed` only), so the
  time-cost work still has to come from MACH.
- No measurable self-consistency ceiling, and none of the bot-screening fields
  RIASEC provides.
- The shipped 2014 codebook is incomplete (item P10 has no entry; the recon
  recovered it by elimination and left it labelled inferred), and the live 16PF
  instrument today lists 164 items with *different* anchors. Any wording would
  have had to come from the shipped codebook — the exact hazard Addendum A
  section D was written to avoid.

Usable-respondent supply was never the problem: 49,159 rows, 34,641 usable
(70.5%) under RIASEC-style cleaning, 163 items on one 1–5 agreement scale. The
file is fine. It is the wrong shape for this question.

## What this costs, stated plainly

Stage 1E's findings now rest on **one corpus**. Corpus-generality is untested,
and nothing in Stage 1E should be read as established beyond RIASEC. That is a
real weakening of the evidence base and is declared as a limitation in
`results/stage1e_findings.md`.

What is *not* affected: the Stage 1E confirm run itself. Its bars were frozen in
Addendum A, its verdicts were computed against those bars, and no part of them
depended on the replication. The confirm run stands as run.

## Status

- Amendment A6's replication requirement is **withdrawn**, by this note.
- Addendum B is **not written and will not be**. No 16PF seed pool, target
  domain, or split was ever locked, and no 16PF split was ever drawn.
- No 16PF model run was ever made. Total cost of the 16PF line of work: **$0**
  and 0 node-hours (the recon was CPU-only).
- Raw data stays at `data/16pf/` (gitignored, with PROVENANCE.txt) in case a
  later question genuinely fits it. The recon and its script
  (`experiments/recon_16pf.py`) remain committed as the record of the decision.
