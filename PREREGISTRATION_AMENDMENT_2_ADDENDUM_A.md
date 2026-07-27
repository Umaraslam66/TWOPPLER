# Addendum A to Amendment 2 — Stage 2 bar lock

Status: **DRAFT — NOT ADOPTED, NOT COMMITTED.** This addendum freezes the
numeric and procedural parameters that Amendment 2 (adopted 2026-07-26,
commit `9949c9d`) left to bar-lock. The owner approved the ten decision
items below IN DIRECTION on 2026-07-26, with the measured values as
drafted; the addendum FREEZES only when every precondition in the list at
the bottom has cleared and the owner adopts it. Values marked **[TO FILL]**
await the open-ended dev pilot or a pending owner check. Confirmatory
subjects remain untouched by all Stage 2 machinery until this addendum is
committed.

**Revised 2026-07-27 to Amendment-3 terms.** Amendment 3 was adopted that
day (commit `7548bc3`): the forced-choice instrument is dead by
pre-committed rule, and open-ended generation with dual-channel scoring
replaces it. Amendment 3 C6 requires this draft to be revised before any
freeze, so decision item 7 is marked superseded, item 8's era window is
marked moot, the instrument-parameter section is rewritten around the new
instrument, and the precondition list is re-cast. The revision changes
nothing about this draft's standing: it is still a **DRAFT**, it is **NOT
ADOPTED**, and committing this revision to git does **not** commit it as a
freeze. The freeze still requires every precondition below to clear and the
owner to adopt it.

Evidence base: `results/stage2_pilot2/BARLOCK_MEASUREMENTS.md` (measured
on dev subjects and pool metadata only), `results/stage2_pilot/
PILOT_REPORT.md`, `results/stage2_pilot2/PILOT_REPORT_2.md`.

## The ten frozen decisions

### 1. Fuzzy host-attribution threshold (was provisional 0.60)

Threshold **0.65**, plus two admission guards: (a) reject relationship
descriptors (e.g. a descriptor naming the host's relative rather than a
presenter role); (b) require the descriptor and the programme string to
share at least one word of 4+ letters. Measured on the full 151-pair
census: false fires drop 86 → 4, anchor precision rises to 0.79, one true
anchor lost. 0.70 is rejected on record: it misses the Diplomatic License
anchor (0.68) the rule exists for. Precondition: the owner's independent
labelling of the 20-row spot-check sheet must not overturn the census
labels.

### 2. Entity handling: real NER

spaCy 3.8.14 + `en_core_web_sm` replaces the D5 heuristic for entity
density and entity stripping; D5's number rule is retained. Measured
impact: 54/652 bank rows and 195/2,071 dev turns change density bucket;
44/72 stripped option texts change; all three documented D5 limitations
fixed, including 177 sentence-initial proper nouns that previously
survived A4.2 stripping. The spaCy model version is pinned in the
environment and named in every report.

### 3. Nickname handling at scale

The `nicknames` CSV (carltonnorthern/nicknames, Apache-2.0, checked into
the repo) UNION the existing hand-maintained NICKNAME_SUPPLEMENT, forward
direction only (formal → hypocorism). Reverse lookup is rejected (adds
junk: Ron → Cameron). Measured: resource alone covers 69.9% of pool first
names vs the hand table's 6.6%, but is not a superset (misses "Frederic"),
so the union is required. Applied to every subject AND every donor.

### 4. Test-interview eligibility floor (draw-time rule)

A subject enters the confirmatory draw only if their test-interview
cluster yields **≥ 3** D4-eligible Q–A items; one-on-one interview
programmes are preferred in the draw order before panels/roundtables.
Measured on a seeded 60-candidate sample: 70% survival (95% CI 57.5–80.1),
projecting ~405 of 578 candidates — the ≥ 80 branch keeps three-fold
headroom. One-on-ones pass at 88.6% vs 44.0% for panels.

### 5. Affiliation redaction scope

Scope **S1**: the host's descriptive clause about GUEST (intro
affiliations, role descriptions, attributable book/article titles in host
intro lines) is redacted in the redacted arms. Measured: removes 23 of
~25 genuine identity leaks on dev prompts with zero collateral damage.
Broader scopes are rejected on record (S2: 84 of 132 removals are the
interview's own topic; S3: 203 of 251 collateral). The contamination
meter remains the backstop for what redaction cannot remove.

### 6. H7 staleness design parameters

Confirmatory H7 is **between-subject** over four Δ bins: **6–12 months,
1–2 years, 2–3 years, > 3 years** (the < 6-month bin is dropped; supply
72 candidates but too near-fresh to carry the contrast). Measured
eligibility: 262 of 578 candidates meet the B7 rule (≥ 4 dated clusters
spanning ≥ 2 years) — the ≥ 80 confirmatory branch holds with 3× headroom.
Per-bin candidate counts: 88 / 120 / 136 / 215. The **within-subject
sweep is pre-registered as a supporting analysis** on the subset that can
fill ≥ 3 bins (121 candidates; 33 can fill 4) — reported beside the
between-subject result, never substituted for it. Precondition: the
30-subject date-sanity pass must show CSV dates are reliable at bin
granularity.

### 7. Parser widening (the doubled-distribution artifact) — SUPERSEDED

**SUPERSEDED 2026-07-27 by Amendment 3 C6.** The forced-choice completion
parser died with the instrument it parsed. The open-ended instrument asks
for free text, not a probability distribution over options, so there is no
doubled-distribution form to widen for and no both-N transition table to
print. This is no longer a live decision. The original text is kept below,
word for word, as the record of what was decided and why.

> **Original text (superseded, kept for the record):**
>
> The completion parser is widened to accept the doubled-distribution
> completion form (the model prints its distribution twice; the frozen
> parser discards it as mass ≈ 2.0): the widened parser recovers the final
> well-formed distribution line. Evidence: all four affected completions
> across pilots 1–2 were argmax-correct and were being silently dropped
> from N. Rule for the transition, owner-directed: the first report scored
> under the widened parser prints **both-N tables once** (frozen-parser N
> beside widened-parser N for every cell) to show nothing else moved;
> thereafter the widened parser is the parser.

### 8. Option-set chronology: post-dated text forbidden, era window

Any REAL text used in an option set (the true answer aside) must come
from material dated **before the test interview cluster** — post-test
text is forbidden in option sets. For GENERATED options (Amendment 2
B10), no generated text may reference events after the test interview's
date (B10.6). Era window — the maximum age gap tolerated inside one
option set before an item is flagged era-inconsistent: **MOOT as of
2026-07-27 (Amendment 3 C6).** There are no option sets under the
open-ended instrument, so there is no set to measure an age gap across.
The original **[TO FILL after dev pilot 3 measurement]** is withdrawn, not
deferred.

**The no-post-dated-text rule for GENERATED material carries forward.**
Under the open-ended instrument it reads: **no generated answer may
reference events after the test interview's date.** It binds every arm's
generated answers, exactly as B10.6 bound generated options.

### 9. Near-duplicate option guard

Any option pair within an item (real or generated) with answer word-set
Jaccard ≥ **0.8** invalidates the option set: the offending distractor is
rejected and regenerated/replaced, or the item is dropped. Adopted from
pilot 2's D6-v2.3 (fired 0 times there; the risk becomes real with
generated distractors and paraphrased true answers). Rejections logged.

### 10. Draw-time cluster-count criterion

Interview **cluster count, not time span, is the binding supply
constraint** (pilot evidence: a 10.6-year subject with 3 clusters fills
only 2 H7 bins; 4 of 6 dev subjects hold ≤ 3 clusters). Confirmatory
draws record cluster count at draw time, and subjects below **[TO FILL —
proposed ≥ 4 dated clusters, confirmed after the open-ended dev pilot's
yield]** are deprioritized in the draw order (H7 eligibility per B7 is
unchanged and stricter).

## Instrument parameters deferred to the open-ended dev pilot (per Amendment 3 C6/C7)

Each value below is frozen here when filled, before any confirmatory
scoring.

1. **Embedding model and its pinned version (channel 1) [TO FILL].** Run
   locally, never an API model, never a scored model (C2.2).
2. **Judge model and its version (channel 2) [TO FILL].** Generator-side
   family, never a scored model, and a different model version than the A3
   robustness scorer — or the overlap is declared beside every robustness
   number it touches (C2.3).
3. **Judge rubric text and its sha256 [TO FILL].**
4. **Generation cap and the format-instruction text [TO FILL]** —
   identical across all five arms (C2.1).
5. **Judge trust bar [TO FILL]** — set after the owner's ≥ 50-label
   spot-check per C4.2.
6. **UNCLEAR handling rule [TO FILL].** Proposed in C2.3: UNCLEAR items are
   excluded from the stance-match rate's denominator; every arm's UNCLEAR
   rate is always reported beside its stance-match rate; a material
   difference in UNCLEAR rates between arms is flagged, not silently
   absorbed.
7. **Magnitude ("interesting") bars for H1, H2, H6 and H7 on the new
   continuous scales [TO FILL]** — the accuracy-point bars do not transfer
   to similarity scores, and no magnitude claim is made until these are set
   (C5).
8. **Free-standing intro sentence handling [TO FILL]** — added by owner
   direction 2026-07-27. S1's frozen scope removes appositive
   descriptors but not free-standing host-intro sentences; in OE-1 dev
   prompts this left identifying role descriptions for the subject and,
   in at least one case, for the imposter DONOR (a blog-naming line).
   The miss is symmetric across own and imposter arms and the
   contamination meter is the backstop, but whether a
   free-standing-intro rule is added, and its exact scope, is decided
   here on OE-1 evidence — not silently dropped.

H6 parameters likewise per B3: token budget(s) B, segment/chain
definitions, rich/poor thresholds, flagged-turn threshold **[TO FILL]**.

## Preconditions before this addendum can freeze

1. Owner's independent 20-row fuzzy-host spot-check (sheet:
   `results/stage2_pilot2/barlock/fuzzy_host_spotcheck_sheet.md`) —
   labels must not overturn the census.
2. H7 date-sanity pass over 30 sampled subjects
   (`results/stage2_pilot2/barlock/h7_date_sanity.md`) — **CLEARED
   2026-07-26: 90/90 transcripts agree with the raw MediaSum record on
   the calendar day (max error 0 days); zero internal contradictions; 0
   of 578 candidates could change Δ bin.** Declared residual limit: this
   verifies pool-vs-MediaSum, not MediaSum-vs-broadcaster; the
   internal-evidence pass that could catch the latter found nothing but
   is weak by nature (broadcast transcripts rarely state their own
   date).
3. Owner review of the open-ended dev pilot report (per Amendment 3 C7).
4. Detectability check (B10.8) — **NO LONGER A LIVE FREEZE CONDITION.**
   The record stands as documented history per Amendment 3 C6: the HUMAN
   line was **WAIVED by owner decision 2026-07-27 — a documented deviation
   from B10.8** (reason: owner declined; no human hit rate exists and none
   may be fabricated); substituted was a frontier-LLM rater line (Claude,
   out-of-family from every scored and generator model), filed as a
   pre-gate prediction before round 4's gate ran, with its hit rate and
   stated tells recorded in PILOT_REPORT_4. It stops being a freeze
   condition because the option-set instrument it was checking is dead.
   What carries forward is the standing eval rule adopted the same day:
   **no rater or scorer may ever see both twins of a duplicated
   question** — twin-pair stance inference was demonstrated by the rater.
   That rule applies to all future rating and scoring sheets, the
   open-ended judge and the owner's spot-checks included; item sets are
   verified twin-free before any scoring.
5. H6 classifier trust gate (B2.2) — **owner ruling 2026-07-27, a
   documented deviation, in two parts.**
   **Part 1 (freeze precondition):** the owner's blind audit of the
   120-row, 6-subject sheet
   (`results/stage2_openended/h6_audit_sheet.md`). B2.2's ≥ 10-subject
   count is unsatisfiable while confirmatory subjects stay untouched by
   all Stage 2 machinery — the untouchability rule wins — so 6 subjects
   / 120 rows is accepted as satisfying B2.2's intent for the freeze.
   The labeling itself remains outstanding.
   **Part 2 (binding, added 2026-07-27):** after this addendum freezes
   and the classifier first runs on confirmatory subjects, a second
   blind audit tranche of ≥ 60 labels drawn from ≥ 10 confirmatory
   subjects is built for the owner BEFORE any confirmatory H6 scoring —
   same blind format, the same trust bar carried over. If part 2 fails
   the bar, H6 scoring halts pending rubric revision. Dev-only evidence
   gates the freeze; confirmatory-subject evidence gates the science.
6. Owner's ≥ 50-label judge spot-check (Amendment 3 C4.2), sampled across
   subjects and balanced across SAME/DIFFERENT. It can only run once the
   open-ended dev pilot has produced judge labels, so it is sequenced
   after precondition 3, not beside it.
