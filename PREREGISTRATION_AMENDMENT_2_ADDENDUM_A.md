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

**Filled 2026-07-28.** The instrument-parameter slots are filled from
OE-1 measurements, the audit lines are scored, deviations D1–D3 are
recorded inline, the four flagged judge rows are owner-adjudicated (net
2–2), and the judge trust bar is **set and pre-committed** (parameter
5). The owner approved the [PROPOSED] values in items 6, 7, 8 and 10 on
2026-07-28. **Parameter 5's first measurement landed later the same
day: FAIL** (raw 0.7778 / κ 0.5789 vs the pre-committed ≥ 0.80 / ≥
0.60, under deviation D4) — the pre-committed on-fail path is running:
one rubric/judge iteration (r2 PROPOSED), a re-tranche (sheets F/G),
same bar, no bar movement. Parameter 5 and the H6/B3 parameters remain
open. Status is unchanged: **DRAFT, NOT ADOPTED** — nothing freezes
until the owner's final freeze review after the parameter-5 verdict.

Evidence base: `results/stage2_pilot2/BARLOCK_MEASUREMENTS.md` (measured
on dev subjects and pool metadata only), `results/stage2_pilot/
PILOT_REPORT.md`, `results/stage2_pilot2/PILOT_REPORT_2.md`,
`results/stage2_openended/OE1_PILOT_REPORT.md`, and
`results/stage2_openended/AUDIT_LINES_2026-07-28.md`.

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
labels. **Satisfied 2026-07-28 via deviation D2** (LLM co-auditor
substituted for the human line, owner-directed): the blind co-audit
matched the census key **20/20**, overturning nothing
(`results/stage2_openended/AUDIT_LINES_2026-07-28.md` §3). The
census-wide numbers above remain the operative measurement.

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
draws record cluster count at draw time, and subjects below **≥ 4 dated
clusters** are deprioritized in the draw order (H7 eligibility per B7 is
unchanged and stricter). Filled 2026-07-28 at the proposed value: OE-1's
yield produced no contrary evidence (all 17 D4 items built and scored;
the dev subjects holding ≤ 3 clusters filled at most 2 H7 Δ bins), and
the operative supply measurement is the H7 pool census (262 of 578
candidates at ≥ 4 dated clusters — 3× headroom on the ≥ 80 branch).

## Instrument parameters deferred to the open-ended dev pilot (per Amendment 3 C6/C7)

Each value below is frozen here when filled, before any confirmatory
scoring. Filled 2026-07-28 from OE-1 measurements
(`results/stage2_openended/OE1_PILOT_REPORT.md`); values marked
**[PROPOSED]** await the owner's approval of this text, and nothing
freezes until the owner adopts the addendum.

1. **Embedding model (channel 1): `sentence-transformers/all-mpnet-base-v2`,
   HF revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`**, run locally
   on CPU, cosine between the generated answer and the real verbatim
   answer. Selected by the pre-stated rule (cleanest own-minus-imposter
   on the primary model among eligible candidates: mpnet +0.1024 >
   bge-large +0.0582 > e5-large +0.0242; MiniLM excluded by spec as
   sanity-only). Never an API model, never a scored model (C2.2).
2. **Judge (channel 2): `gemini-3.5-flash`, temperature 0.0,
   `thinking_budget=0`, `max_output_tokens=512`**, AI Studio endpoint,
   one candidate per stateless call, blind to arm/model/subject.
   The thinking-off setting is load-bearing: with hidden thinking
   enabled, labels were budget-dependent at temperature 0 (the OE-1
   judge-v1 defect record). Different model version than the A3
   robustness scorer (`gemini-3.5-flash-lite`); the family overlap is
   declared per Amendment 3 C3.
3. **Judge rubric: `results/stage2_openended/rubric_r1.txt`, sha256
   `85c7c990af522c2c1e41c116617f406a473496b4c5875f293d687ef62bff64d1`.**
4. **Generation cap and format instruction: 150 words,
   `max_output_tokens=256`, temperature 0.0, identical tail across all
   five arms (C2.1), tail sha256
   `d8758204009e71b482d36fb7133641f3077b7414df87e5a055f3949cb2ef3d3b`.**
   Measured: 0 truncations at the cap on either scored model; 82/85 and
   85/85 within the word cap.
5. **Judge trust bar — SET 2026-07-28, pre-committed before its
   measurement exists:** the judge passes iff **raw agreement ≥ 0.80
   AND Cohen's κ ≥ 0.60** against a **rubric-briefed** auditor line on
   a fresh blind tranche. Rationale on record: the first C4.2 audit ran
   under deviation D1 (human tranche = sheet A only, 17 of 51 rows; LLM
   co-auditor on all 51; concordance 17/17 on A) with **rubric-naive**
   auditors — briefed with a paraphrase, not the frozen rubric text, an
   audit-protocol defect recorded as the owner's, not the judge's — so
   its measured 0.76–0.78 raw / κ 0.56–0.60 is a lower bound. The
   judge's four sheet-A disagreements with the concordant auditor line
   were adjudicated by the owner 2026-07-28, unblind, therefore
   adjudicated rather than re-scored: **A6 judge correct** (rubric rule
   5; the auditor-protocol defect case), **A7 judge correct** (rule 3,
   hedged-but-committed), **A3 auditors correct** (judge keyed on
   surface framing; the real answer's central claim is the dependency
   reversal), **A5 auditors correct** (both texts land "no one will
   reverse Brexit"; optimism-vs-doom is secondary). Net 2–2.
   **Measured 2026-07-28 on the fresh 18-row tranche
   (`fresh_tranche_sheet_{D,E}.md`, seed 611): FAIL.** The
   rubric-briefed auditor line (an out-of-family LLM line under
   deviation D4, owner-directed) scored **raw 0.7778 / κ 0.5789**
   against the judge — both legs miss the pre-committed bar. The
   verdict was applied mechanically and the pre-committed on-fail path
   executed the same day, bar unchanged: rubric r2 **[PROPOSED]**
   (`results/stage2_openended/rubric_r2_draft.txt`, sha256
   `ad050d1a75b038fc63ee162fe74862fd8f99c895e2b39b3af56f24bdea102464`;
   three targeted edits matching the three diagnosed judge failure
   modes, each anchored to an owner adjudication: multi-part
   first-order-ask (A5/D6/E6), premise-rejection-is-UNCLEAR (E7),
   pick-one questions (A3/E9); reply format gains a CENTRAL line and
   the judge config is re-pinned on adoption) and a re-tranche
   (`fresh_tranche_r2_sheet_{F,G}.md`, seed 613, combos unused in
   A/B/C AND D/E, key sealed; the unused pool held only 4
   judge-DIFFERENT rows, so balance by r1 labels is 9/4/5 with the
   shortfall documented). **Parameter 5 stays OPEN** pending: owner
   approval of the r1→r2 diff, the r2 judge run on the 18 F/G rows,
   and the rubric-briefed auditor labels — scored against the same
   bar. Full record: `results/stage2_openended/AUDIT_LINES_2026-07-28.md`.
6. **UNCLEAR handling rule — adopted as proposed in C2.3:** UNCLEAR items
   are excluded from the stance-match rate's denominator; every arm's
   UNCLEAR rate is always reported beside its stance-match rate; a
   between-arm UNCLEAR-rate difference **≥ 0.10 absolute [PROPOSED]** is
   flagged as material. (OE-1 measured the flag firing: imposter 0.353
   vs twin 0.059 on the primary model.)
7. **Magnitude ("interesting") bars [PROPOSED], one unit per channel,
   derived as half of OE-1's dev own-minus-imposter effect:** a
   registered contrast is "interesting" only if it reaches **≥ +0.05
   cosine (channel 1, pinned model)** or **≥ +0.09 stance-match points
   (channel 2)** — with direction agreement across both channels
   required for any headline, as always. Applied to each hypothesis's
   registered contrast (H1: own-twin − zero-info; H2: between-arm;
   H7: freshest − stalest Δ bin, beside the unchanged crossover
   statistic). Rationale on record: every pilot effect in this project
   has shrunk at scale, so the dev effect halved is a deliberately
   modest bar; no magnitude claim is made below it.
8. **Free-standing intro sentence handling [PROPOSED]** — added by owner
   direction 2026-07-27. S1's frozen scope removes appositive
   descriptors but not free-standing host-intro sentences; in OE-1 dev
   prompts this left identifying role descriptions for the subject and,
   in at least one case, for the imposter DONOR (a blog-naming line; a
   second case: a full donor résumé surviving because the "U.S."
   abbreviation's period truncates S1's clause pattern). Proposed
   resolution: extend S1 with (a) an abbreviation-safe clause pattern
   and (b) the `GUEST, who …` appositive shape — both inside S1's
   declared intent (the host's descriptive clause about GUEST) — then
   re-measure collateral damage on dev prompts before any confirmatory
   render; the extension freezes only if collateral stays at zero, else
   the miss stays declared with the contamination meter as backstop.

H6 parameters likewise per B3: token budget(s) B, segment/chain
definitions, rich/poor thresholds, flagged-turn threshold **[TO FILL —
stays open on record]**. OE-1 measured none of these; they require their
own dev measurement and MUST be filled before any confirmatory H6
scoring. This is the one slot this revision deliberately does not fill,
and it is said here rather than hidden.

## Deviations D1–D4 (owner-directed 2026-07-28, all documented)

- **D1** — the C4.2 human judge tranche is sheet A only (17 of 51 rows,
  owner time constraint); the full 51 rows carry an out-of-family LLM
  co-auditor line. The two lines are reported separately, never pooled;
  their sheet-A concordance (17/17) is stated wherever either is cited.
- **D2** — the fuzzy-host 20-row spot-check is fully substituted by the
  out-of-family LLM co-auditor; no human line exists for it.
- **D3** — the H6 trust audit runs as a blind LLM co-audit (Opus 5)
  with a disagreement-triggered human tranche: agreement at or above
  the B2.2 bar (raw ≥ 85%, κ ≥ 0.6) satisfies the part-1 gate with D3
  recorded; below the bar, everything stops and a 30-row human tranche
  stratified on the disagreements goes to the owner.
- **D4** — the parameter-5 auditor line on the fresh D/E tranche is a
  rubric-briefed out-of-family LLM line (Claude; frozen rubric read in
  full, key never opened), owner-directed, in place of the owner's own
  rubric-in-hand labels this addendum anticipated. Reported as its own
  line, never pooled with a human line.

Full lines, scores, and flags: `results/stage2_openended/AUDIT_LINES_2026-07-28.md`.

## Preconditions before this addendum can freeze

1. Owner's independent 20-row fuzzy-host spot-check (sheet:
   `results/stage2_pilot2/barlock/fuzzy_host_spotcheck_sheet.md`) —
   labels must not overturn the census. **SATISFIED 2026-07-28 via D2:**
   the blind LLM co-audit matched the census key 20/20; nothing
   overturned.
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
   **CLEARED 2026-07-28** — the owner reviewed OE1_PILOT_REPORT and
   issued the audit directives and deviations D1–D3 on its basis.
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
   **Part 1 SATISFIED 2026-07-28 via deviation D3** (owner-directed):
   the audit ran as a blind LLM co-audit (Opus 5; read only the sheet
   and the frozen rubric, sha256
   `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`;
   the key and classifier records were off-limits). Result over all
   120 rows: **raw agreement 0.8667, Cohen's κ 0.7333** — clears the
   B2.2 bar (≥ 0.85, κ ≥ 0.6), so the pre-stated escalation rule does
   NOT trigger and no human tranche is built. Recorded beside the
   verdict, not buried: 15 of the 16 disagreements run one way
   (co-auditor NEW-TOPIC where the classifier said FOLLOW-UP), and 11
   of 16 sit in the co-auditor's 35 self-flagged low-confidence rows —
   the classifier's FOLLOW-UP boundary reads looser than a strict
   rubric application, a note the part-2 tranche should revisit.
   **Part 2 (binding, added 2026-07-27):** after this addendum freezes
   and the classifier first runs on confirmatory subjects, a second
   blind audit tranche of ≥ 60 labels drawn from ≥ 10 confirmatory
   subjects is built for the owner BEFORE any confirmatory H6 scoring —
   same blind format, the same trust bar carried over. If part 2 fails
   the bar, H6 scoring halts pending rubric revision. Dev-only evidence
   gates the freeze; confirmatory-subject evidence gates the science.
6. Owner's ≥ 50-label judge spot-check (Amendment 3 C4.2), sampled across
   subjects and balanced across SAME/DIFFERENT. **RAN 2026-07-28 under
   D1** (human: sheet A, 17 rows; LLM co-auditor: all 51; concordance
   17/17 on A). Scores in `AUDIT_LINES_2026-07-28.md` §2. The four
   flagged rows were **adjudicated by the owner 2026-07-28** (net 2–2;
   see instrument parameter 5) and the trust bar is now **set and
   pre-committed**. The fresh D/E tranche was scored 2026-07-28 under
   deviation D4: **FAIL** (raw 0.7778 / κ 0.5789), and the
   pre-committed iteration opened — rubric r2 proposed, re-tranche F/G
   built, same bar. **OPEN REMAINDER:** the r1→r2 diff decision, the
   r2 judge run on sheets F/G, the rubric-briefed labels on F/G, and
   the resulting parameter-5 pass/fail verdict. This precondition
   closes when that verdict lands.
