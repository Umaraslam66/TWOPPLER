# Pre-registration errata

**What this file is.** The frozen governance documents — `PREREGISTRATION.md`
and its five amendments — are never edited. When a defect is found in one of
them, it is corrected here, dated, with the frozen text left exactly as it
stands. This file is the correction channel and the only one.

**What an erratum does and does not do.** It records a defect and its correct
reading. It does **not** retroactively change how the project ran: where a
frozen definition was applied as written, that is stated in the entry, so a
reader can tell a typo from a silent re-analysis.

Entries are dated and appended. Nothing here is ever removed.

---

## E1 — Amendment 3 C1 cites the wrong directory for `PILOT_REPORT_4.md`

**Filed 2026-07-28** (owner ruling, stop point iii, decision 4). Discovered
2026-07-28 during Paper 1 drafting.

**The frozen text.** `PREREGISTRATION_AMENDMENT_3.md`, section C1, cites the
round-4 kill-rule measurement as:

> `results/stage2_pilot3/PILOT_REPORT_4.md`

**The defect.** That path does not exist. The file lives at
`results/stage2_pilot4/PILOT_REPORT_4.md`. `results/stage2_pilot3/` holds
round 3's report (`PILOT_REPORT_3.md`) and its detectability sheets; round 4's
report has always been in `results/stage2_pilot4/` alongside its spec
(`SPEC_v1.10.md`) and its frontier-rater line
(`DETECTABILITY_RATER_LINE.md`).

**Correct reading.** `results/stage2_pilot4/PILOT_REPORT_4.md`.

**Scope: a path typo in a frozen document, nothing more.** The cited *content*
is correct and unchanged — round 4 measured zero-info accuracy 1.00 under both
parser readings, which is what triggered the pre-committed kill rule. No number,
no bar and no verdict depends on which directory string the amendment carries.
Write-ups link the real path.

---

## E2 — B7's pooled crossover statistic has no equal-subject-set guard

**Filed 2026-07-28** (owner ruling, stop point iii, decision 4). Discovered
2026-07-28 via [`results/stage2_confirm/h7_diagnostics.md`](results/stage2_confirm/h7_diagnostics.md)
(section 1 and finding 1).

**The frozen text.** `PREREGISTRATION_AMENDMENT_2.md`, B7, "Pre-declared killer
statistic — the crossover point":

> At each Δ bin, the STALE true-person twin is compared against a FRESH
> same-domain imposter twin … The **crossover point** is the smallest Δ at which
> the fresh imposter twin matches or beats the stale own twin.

**The defect.** That definition compares the two arms' **bin-level means**
directly, over whatever subject sets happen to have produced them. The same
report driver (`experiments/stage2_confirm_report.py`, `h7_block`) applies an
equal-subject-set guard before it will print a per-bin difference: it subtracts
only when both arms cover the same subjects in that bin, and prints `n/a`
otherwise. The crossover statistic bypasses that guard.

**Why the sets come apart.** On channel 2 a subject keeps a twin value in a bin
if any of its items got a SAME/DIFFERENT label, but loses its imposter value in
that bin if *all* of its imposter items came back UNCLEAR. The imposter arm
draws the most UNCLEAR of any arm, so it is the arm that loses subjects. The
practical consequence on this run: the channel-2 pooled crossover at the 6–12m
bin on the primary model rests on a comparison the same driver **declines to
print** as a difference one column to its left. Channel 1 never hits this —
every render carries a cosine, so no subject drops out.

**How it was handled in this project: the frozen definition was applied as
written.** The crossover was computed exactly as B7 defines it, unguarded, and
the mismatch is reported rather than repaired. No number was changed, no guard
was retrofitted, and the diagnostics note that surfaced it proposed no change to
the definition. H7 carries no headline reading in any case — the two channels
disagree and Amendment 3 C2.4 forbids a one-channel claim — so nothing in the
record turns on this statistic.

**Correct reading for any future use.** A pooled crossover comparison of two arm
means should carry the same equal-subject-set guard the per-bin difference
carries, or state explicitly that it does not. Any later use of B7's definition
inherits this caveat.
