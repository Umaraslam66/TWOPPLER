# Project DOPPLER — Pre-Registration Amendment 3

Status: **ADOPTED 2026-07-27.** Approved by the owner on 2026-07-27
with two owner edits incorporated at adoption: the UNCLEAR handling
rule in C2.3 and the C6 bar-lock parameter list, and the judge-family
robustness sentence in C3. Committed on adoption. Drafted 2026-07-27,
immediately after round 4's pre-committed kill rule fired. **No confirmatory Stage 2 data exists at drafting** — the only
Stage 2 runs are the four dev-subject instrument pilots cited in C1.
Where this amendment conflicts with PREREGISTRATION.md, Amendment 1, or
Amendment 2, this amendment governs. Everything not amended stays
frozen. This draft is the pre-written fallback sketch
(`results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md`, commit `71ae352`)
promoted to amendment form, per the owner's pre-commitment — designed
before the kill result was known, not after.

## C1. Why: the forced-choice instrument is dead, by pre-committed rule

Amendment 2 B10 registered forced choice over generated same-question
counterfactuals, with a build-time zero-information gate as final
arbiter. Four dev-pilot rounds then showed that **no tested construction
of four-way forced choice on this corpus is hard for a person-blind
scorer**:

| round | distractor construction | zero-info accuracy | dominant tell |
|---|---|---|---|
| 1 | other people's answers, similarity-ranked | 17/17 | topical coherence |
| 2 | same subject's other answers | 10/10 | responsiveness to the shown question |
| 3 | generated counterfactuals | 15/15 | register (advocacy vs hedging), world-truth, deixis |
| 4 | + hedge/register conditioning, deixis stripping, plausible-position rule, subjective-only items | 8/8 | register inverted: real voice (idiom, entity deployment) vs bland generated prose |

Round 4 ran under a pre-committed kill rule (owner, 2026-07-27,
recorded before launch): zero-info accuracy ≥ 0.9 → forced choice is
dead on this corpus, no round 5 on any axis. It measured 1.00 under
both parser readings (`results/stage2_pilot3/PILOT_REPORT_4.md`). A
frontier-LLM rater line (out-of-family from all scored and generator
models), filed as a frozen pre-gate prediction, identified the real
option 10/10 on the same tells — the leak is instrument-level, not
scorer-specific. The fixes did move confidence (mean margin +0.69 →
+0.56) without moving accuracy; an instrument that only gets harder to
solve *confidently* is not getting harder to solve.

**Declared finding (claimable, scoped):** verbatim-answer forced choice
over public-interview corpora is dominated by person-blind signal —
topic, responsiveness, register, world knowledge — across every
distractor source tested, because a real person's answer differs from
any constructed alternative in ways that do not require knowing the
person. Scope: this corpus (broadcast interviews, largely expert
subjects) and these constructions; stated in all write-ups with the
four pilot reports as the record.

## C2. The replacement instrument: open-ended generation, dual-channel scoring

1. **Task.** The twin answers the held-out interview question freely in
   text. No options. Same five arms (twin redacted/named, zero-info
   redacted/named, imposter), same grounding budgets, chronological
   splits, contamination meter, and identity controls as before.
   Generation length capped and format-instructed identically across
   arms.
2. **Channel 1 — embedding similarity** between the generated answer
   and the person's real answer. Fixed, named, locally-run embedding
   model (never an API model, never a scored model); version pinned at
   bar-lock.
3. **Channel 2 — stance/entailment judge.** A judge model classifies
   whether the generated answer takes the same position as the real
   answer (SAME / DIFFERENT / UNCLEAR) under a frozen rubric whose text
   and sha256 are pinned at bar-lock. The judge is generator-side
   family and **never a scored model**; it must be a different model
   version than the A3 robustness scorer, or the overlap is declared
   beside every robustness number it touches (the B10.3 clause,
   carried forward). The UNCLEAR label carries a pre-specified
   handling rule, frozen at bar-lock. Proposed for the bar-lock
   addendum: UNCLEAR items are excluded from the stance-match rate's
   denominator, and every arm's UNCLEAR rate is always reported
   beside its stance-match rate; a material difference in UNCLEAR
   rates between arms is flagged, not silently absorbed.
4. **No claim rests on one channel alone.** A headline requires
   direction agreement across both channels; disagreement between
   channels is itself reported.

## C3. Metrics and reporting

- **Primary metric: own-twin minus imposter-twin**, per Amendment 1 A1,
  computed identically in both channels. The contrast is relative by
  design: judge and embedding biases (verbosity, topic priors,
  generosity) apply to both arms and cancel in the difference.
- Zero-information lift is computed and reported alongside, as always.
- Both scored models per A3 (Gemma-4-31B-it primary,
  gemini-3.5-flash-lite robustness) are evaluated identically; headline
  claims require both, as registered. Because the stance judge shares a
  model family with the robustness scorer, robustness-arm absolute
  scores are explicitly secondary: only the own-minus-imposter contrast
  carries robustness weight (extending the B10.3 declaration).
- B8 applies: individual-level lift beside a population-level
  distribution metric (TVD over stance categories), divergences
  flagged.
- Effect sizes with confidence intervals, never bare means. Raw
  per-arm scores always printed beside every difference (the
  watch-which-arm-moves rule).

## C4. Validation gate before any confirmatory registration

On dev subjects only, before bars freeze:

1. The instrument must separate own-twin from imposter-twin in the
   pre-registered direction on the primary model.
2. The owner spot-checks **≥ 50 judge labels** (sampled across subjects
   and balanced across SAME/DIFFERENT), same pattern as the B2.2 trust
   gate; the trust bar for the judge is set in the bar-lock addendum.
3. If the instrument cannot separate own from imposter on dev subjects,
   **Stage 2 pauses for a design review** — the failure is reported,
   and no larger instrument is reached for without a new amendment.

## C5. Hypotheses under the new instrument

H1, H2, H6, and H7 are unchanged as hypotheses and transfer with their
existing branch rules (A5, B3, B7): confirmatory bars remain
direction + significance (paired over subjects, p < .05, primary
model; robustness per A3). **Magnitude ("interesting") bars registered
in accuracy points do not transfer to continuous similarity scales and
are re-set in the bar-lock addendum after dev measurement** — until
then, no magnitude claim is made. H7's outcome variable becomes
open-ended fidelity; its design (B7), crossover statistic, and Δ bins
are otherwise unchanged.

## C6. What is superseded and what stands

- **Superseded:** B10's forced-choice option construction, the
  build-time zero-info gate (an option-set concept), the A4 distractor
  controls (no distractors exist), and the forced-choice distribution
  parser and its widening question — all recorded as applying to a
  dead instrument. Their pilot evidence remains part of the record.
- **Stands unchanged:** A1 imposter arms; A2 (ceiling descriptive); A3
  two-model rule; A5/B3/B7 subject-count branches; B1 scope; B2/B3 H6
  design and classifier trust gate (still outstanding); B7 H7 design;
  B8 dual-level rule; B9 positioning; B10.8's detectability deviation
  record (human line waived 2026-07-27, LLM-rater substitution) as
  documented history; all cost-logging, dual-decoding-spirit, and
  provenance rules. Dev subjects stay dev forever.
- The existing bar-lock addendum draft
  (`PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`) is revised to
  Amendment-3 terms before any freeze: its instrument-parameter
  section is replaced by C2's parameters (embedding model + version,
  judge model + version, rubric + hash, generation caps, judge trust
  bar, the UNCLEAR handling rule, magnitude bars); its ten measured queue decisions are
  unaffected except item 8 (era window — moot without option sets) and
  item 7 (parser widening — moot; superseded with the instrument).

## C7. Cost and freeze path

A dev pilot of the open-ended instrument (5 arms × dev items,
generation + judging) precedes bar-lock; its costs are logged per arm
as everywhere. All C2/C4/C5 parameters freeze in the revised bar-lock
addendum after the owner reviews that pilot. Confirmatory subjects are
untouched until the addendum is committed. On adoption this amendment
is committed and the OSF snapshot is updated to include it (upload
remains on the owner).
