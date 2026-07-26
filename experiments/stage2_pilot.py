"""Stage 2 pilot driver -- end to end on the six dev subjects (SPEC D10).

PILOT. Pipeline validation only. Nothing here answers a pre-registered bar and
nothing here is confirmatory; every artifact and table it writes is labelled
"PILOT -- pipeline validation on dev subjects; no research conclusions."

What it does, in one paragraph. It reads the five frozen upstream artifacts
(T1's dev subjects / splits / turns, T2's Q-A items and distractor option sets,
T3's imposter donors, T4's five-arm prompt renderer, T5's follow-up classifier),
renders every prompt the pilot needs, proves the leakage guards on each one,
exports them as BatchFileBackend prompt files with sha256s, runs them in one
Leonardo job, joins the completions back, and writes results/stage2_pilot/
PILOT_REPORT.md.

Hard constraints, asserted in code rather than remembered:

* **Zero API calls.** Nothing in this file talks to Gemini or any hosted model.
* **Dev subjects only.** Every ``canonical_id`` that reaches a prompt is checked
  against results/stage2_pilot/dev_subjects.json.
* **C00292 is burned for Q-A** (SPEC D1 / T1 round 2). It has a full option set
  on disk -- T2 built its artifacts either way -- so the exclusion is enforced
  here, by filtering on the ``burned_for_qa`` annotation, and asserted at
  export and again at verify. It IS included in the classifier prompts.
* **Budget.** ``plan`` projects node-hours before anything is submitted; the
  driver refuses to bootstrap sbatch files if its own projection exceeds
  :data:`PROJECTION_ABORT_NODE_HOURS`.

Redaction (binding, orchestrator adjudication). Every rendered field is
scrubbed, not just the excerpts: the question and all four option texts are
redacted with the SUBJECT's variants, twin grounding likewise, and imposter
grounding with the DONOR's variants. Six of the eighteen Q-A questions name
their subject out loud (T2 concern 3), so this is load-bearing rather than
theoretical. After rendering, both D8 guards run on the full string and the
export refuses to write anything if a single one trips.

Subcommands
-----------
``plan``       build every prompt in memory, prove the guards, project
               node-hours. Writes nothing.
``export``     the same build, written to results/stage2_pilot/exports/ with a
               sha256 export manifest.
``verify``     re-run every guard against the prompts ON DISK, without
               re-rendering them, and re-check the manifest digests.
``bootstrap``  run config + the two sbatch files (smoke, full) + the manifest.
``record``     write a slurm job id / status / anomaly into the manifest.
``ingest``     join returned completions by idx, score, write records,
               analysis.json and the per-job cost-log lines.
``report``     results/stage2_pilot/PILOT_REPORT.md from analysis.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler import followup_render as F  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

RESULTS_DIR = _ROOT / "results"
PILOT_DIR = RESULTS_DIR / "stage2_pilot"
EXPORT_DIR = PILOT_DIR / "exports"
RECORDS_DIR = PILOT_DIR / "records"
DONORS_DIR = PILOT_DIR / "donors"
MANIFEST = PILOT_DIR / "manifest.json"
EXPORT_MANIFEST = EXPORT_DIR / "export_manifest.json"
ANALYSIS = PILOT_DIR / "analysis.json"
REPORT = PILOT_DIR / "PILOT_REPORT.md"
IMPOSTER_PAIRS = PILOT_DIR / "imposter_pairs.json"

#: The banner that has to appear on anything this driver writes.
PILOT_BANNER = ("PILOT -- pipeline validation on dev subjects; "
                "no research conclusions.")

# ---------------------------------------------------------------------------
# Node / job configuration
# ---------------------------------------------------------------------------

REMOTE = "leonardo"
NODE_ROOT = "/leonardo_work/AIFAC_P02_548/DOPPLER"
NODE_RUN = f"{NODE_ROOT}/runs/stage2_pilot"
NODE_JOBS = f"{NODE_ROOT}/jobs"
ACCOUNT = "AIFAC_P02_548"
MODEL = f"{NODE_ROOT}/models/Gemma-4-31B-it"
MODEL_LABEL = "leonardo-gemma4-31b-it"
SPLIT_LABEL = "stage2_pilot"

TP = 4
TEMPERATURE = 0.0
GPU_MEM_UTIL = 0.92

#: Context window for the pilot job.
#:
#: Stage 1E ran at 2048, which is far too small here: a twin prompt carries a
#: 2,000-word grounding block (SPEC D8's B_pilot) plus up to a 1,135-word option
#: block (C02013's long Z-bucket items), so the longest prompt is ~3,300
#: whitespace words. The T6 brief named 4096; measurement says 4096 is not
#: enough either -- see :func:`context_check`, which recomputes the arithmetic at
#: export time from the real prompts and refuses to write if the longest one
#: would not fit. 8192 is the smallest power of two with headroom at the
#: measured worst-case token/word ratio.
MAX_MODEL_LEN = 8192

#: Words -> tokens. Measured on 1,501 Stage 1E prompts against this exact model
#: (Gemma-4-31B-it): mean 1.905, p95 1.952, max 2.041 tokens per whitespace
#: word. The mean drives the projection, the max drives the context check.
TOKENS_PER_WORD = 1.9
TOKENS_PER_WORD_MAX = 2.05

#: Combined (prompt + completion) token throughput, measured on the Stage 1E
#: confirm static job: (21,547,730 in + 2,695,006 out) / 1153.59 s = 21,015
#: tokens/s on one 4xA100 node. Stage 2's prompts are ~10x longer, which shifts
#: the job from decode-bound to prefill-bound, so the projection de-rates it.
MEASURED_TOKENS_PER_SECOND = 21000.0
LONG_PROMPT_DERATE = 3.0
ENGINE_INIT_SECONDS = 225.0

#: Stop and ask rather than submit, if our own projection lands above this.
PROJECTION_ABORT_NODE_HOURS = 1.5
#: The hard ceiling the brief sets for the whole pilot.
BUDGET_NODE_HOURS = 3.0

#: Output-token cap for a PREDICTION prompt, overriding the renderer's
#: ``stage2_render.MAX_OUTPUT_TOKENS`` (120).
#:
#: Measured, not guessed. The first smoke slice (slurm 50356680) came back with
#: **20 of 20 prediction completions truncated at exactly 120 tokens**, none of
#: them reaching the final "A: <p> B: <p> C: <p> D: <p>" line, so all 20 scored
#: as parse failures. The two classifier cases parsed fine at 27 and 33 tokens.
#: D8's instruction says to END the reply with the distribution line, and this
#: model complies by characterising the speaker and walking the four options
#: first -- about 300 tokens before it gets to the answer.
#:
#: 512 gives that roughly 200 tokens of headroom. This changes NO prompt text:
#: every prompt string and its sha256 are byte-identical, only the
#: ``max_output_tokens`` field of the exported line moves. The renderer stays
#: frozen; T4's constant is its default, not a contract on the job.
PREDICTION_MAX_OUTPUT_TOKENS = 512

SMOKE_WALLTIME = "00:20:00"
FULL_WALLTIME = "01:00:00"
SMOKE_QOS = "boost_qos_dbg"

#: Two prompts from each of the ten prediction sets plus two classifier cases.
SMOKE_PER_SET = 2
SMOKE_CLASSIFY = 2

# ---------------------------------------------------------------------------
# Design constants
# ---------------------------------------------------------------------------

ARMS = R.ARMS                       # the five D8 arms, in SPEC order
VARIANTS = ("standard", "stripped")  # A4.2's entity-stripped option re-score
GROUNDING_BUDGET_WORDS = R.GROUNDING_BUDGET_WORDS   # 2000, SPEC D8

#: The subject the draw retired for Q-A. Named here so the exclusion is
#: greppable; the driver still reads the annotation rather than this constant.
BURNED_FOR_QA = "C00292"

#: Seed for the report's 20-case classifier sample. Report presentation only --
#: nothing scored depends on it.
SAMPLE_SEED = 49

# ---------------------------------------------------------------------------
# Nickname supplement (orchestrator ruling, 2026-07-26)
# ---------------------------------------------------------------------------
#
# The pool's ``variants`` column carries formal names. T4's redactor expands a
# variant to its bare name tokens, so "Matthew Kroenig" reaches "Matthew" and
# "Kroenig" but not "Matt" -- and the pilot's own excerpts say "Matt". The guard
# cannot see that, because it uses the same matcher as the scrubber.
#
# This table is the RULE, not a hand-fix for one subject: it is applied to every
# dev subject and every donor, and it holds standard English hypocorisms only,
# for first names that actually occur in the pilot. A supplement produces a
# whole substituted NAME ("Matt Kroenig"), never a bare token, so T4's frozen
# expansion semantics do the rest and nothing here reimplements matching.
#
# It buys deterministic over-redaction, exactly as T4 documented for the base
# expansion: "Rob" and "Bob" are ordinary English words in some contexts and the
# matcher is case-insensitive, so a stray one is scrubbed. Measured cost is in
# the pilot report. Nickname handling at corpus scale is a BAR-LOCK item: a
# hand-maintained table does not scale to 1,153 subjects and the real answer is
# a name-normalisation resource, not a longer dict.
NICKNAME_SUPPLEMENT = {
    "frederic": ("Fred", "Freddie", "Freddy"),
    "frederick": ("Fred", "Freddie", "Freddy"),
    "joshua": ("Josh",),
    "martin": ("Marty",),
    "matthew": ("Matt", "Matty"),
    "robert": ("Bob", "Bobby", "Rob", "Robbie"),
    "ron": ("Ronnie",),
    "ronald": ("Ron", "Ronnie"),
    "stephen": ("Steve", "Stevie"),
    "steven": ("Steve", "Stevie"),
    "walter": ("Walt", "Wally"),
}

#: First names present in this pilot that have NO standard English hypocorism.
#: Listed so the table's coverage is auditable rather than accidental: a name
#: missing from both structures is a name nobody checked.
NICKNAME_NONE = ("bassir", "doris", "samer")


#: Section 8 of the pilot report. These are the findings the whole Stage 2 build
#: accumulated -- across T1..T5's task reports and this driver -- that the
#: orchestrator ruled must travel with the pilot numbers rather than sit in five
#: separate reports. Sourced, numbered, and written for bar-lock review.
FINDINGS = """
Every item here is a PILOT observation or an inherited design limitation. None
of it is a research conclusion, and none of it clears or fails a bar.

### 8.0 THE HEADLINE: the item set is at ceiling, so this pilot measures nothing about twins

**The zero-information baseline scored 100% argmax accuracy on all 17 items.**

A prompt with no excerpts, no programme, no date and no name -- a model that
knows literally nothing about the person -- picked the right answer every single
time, under both option variants. The twin arms also scored 1.00, so:

* **twin - zeroinfo lift is exactly 0.00 in argmax**, because both arms are
  pinned at the ceiling and there is no room above the floor;
* **A4.3's adversarial filter removes ALL 17 items** (its rule is "drop the items
  the zero-information arm got argmax-correct"), leaving **N = 0** in every
  filtered cell. Those tables in section 5 are empty, and that is the filter
  working exactly as designed -- it is telling us the instrument is unusable;
* the only structure left anywhere is in probability mass and in the imposter
  arm, which is the one arm that is NOT at ceiling (0.94 argmax, 0.88 mass).

**This is not a twin result, it is a distractor result.** The forced choice is
solvable by topical coherence alone: the true answer is the guest's real reply to
*this* question, and all three distractors are answers to unrelated questions
from other people's interviews. The model's own reasoning in the completions says
so in as many words -- "Option B directly addresses the host's question about
American responsibility" -- it is matching topic, not modelling a person.

T2 predicted this precisely (finding 8.5): median distractor question-similarity
cosine 0.050, one item of eighteen with a distractor above 0.10. The prediction
was "a model that knows nothing about the person can score above chance". The
measured answer is worse than above chance: it is perfect.

**What this pilot therefore did and did not establish.** It DID establish that
the pipeline works end to end -- draw, split, extraction, distractors, imposter
matching, five-arm rendering, both leakage guards, export, node execution,
ingest, scoring. Every one of those ran clean on real data. It established
NOTHING about twin fidelity, and no number in section 5 should be read as
evidence about one.

**The fix is not in these rules.** It is a materially harder option set. The
levers, in the order I would try them:

1. **Distractors from the SAME subject's other interviews.** Then topic and
   speaker are both controlled and only the specific answer differs. This is the
   single biggest change and it is a D6 amendment.
2. **A much bigger, stratified bank** so the same-bucket, same-length pool has
   enough rows for question similarity to bite (finding 8.5).
3. **A similarity floor as a hard admission rule** -- reject an item whose best
   distractor cannot clear a stated cosine, rather than accepting whatever the
   ladder returns.
4. **Report the zero-information ceiling as a gate**: if the floor arm solves an
   item, that item carries no information about anybody, and it should never
   have entered the set. That is A4.3 applied at BUILD time instead of at score
   time.

All four are bar-lock decisions and none of them is mine.

### 8.1 The redacted arms are name-blind, not identity-blind

SPEC D8 redacts *name variants*. It does not touch affiliations, and the twin
excerpts are full of them. Real lines from the exported `twin_redacted` set:

    "GUEST is chairman of the Department of Sociology a..."          C02013
    "I'm joined now by GUEST, professor of Middle East politics
     at Georgetown U..."                                             C02124
    "GUEST is the author of "Imperium", a novel of anci..."          C02006
    "GUEST, as a former State Department official, can..."           C00792
    "And GUEST, Stanton nuclear security fellow at the Coun..."      C01677

Any model with world knowledge recovers the person from those lines. So
`twin_redacted` is a name-scrubbed arm, not a de-identified one, and the honest
reading of a twin number is "the excerpts help", NOT "the excerpts help without
identity".

This is inherent to D8 as frozen and was accepted as such. It is also exactly
why two controls in the design are load-bearing rather than decorative:

* the **zero-information arms** are the floor every twin number is reported
  against -- the project's standing rule, and on this pilot not a formality;
* the **contamination meter** (`zeroinfo_named - zeroinfo_redacted`, section 6)
  measures what the model already knows about the named person with no excerpts
  at all, which bounds how much of a twin score could be identity rather than
  evidence.

Bar-lock question: does a confirmatory Stage 2 need affiliation redaction, or
does it accept name-only redaction and lean on the meter? Not a pilot decision.

### 8.2 Nickname handling (new rule this pilot, bar-lock item at scale)

The pool's `variants` column carries formal names, so T4's expansion reached
"Matthew"/"Kroenig" but not the "Matt" the excerpts say -- and the guard could
not see it, because the guard and the scrubber share a matcher. A documented
`NICKNAME_SUPPLEMENT` table (standard English hypocorisms only, applied to every
dev subject AND every donor, emitting whole substituted names so T4's frozen
expansion does the matching) now closes it. It caught two leaks:

    C01677  "It's fair to say, Matt GUEST, ..."           twin arms, 1 item
    C01316  "... the blog Syria Comment. Josh, nice ..."  imposter arm, 5 items

The second is the interesting one: Joshua Landis is C00792's *donor*, so his
first name was surviving in the imposter excerpts and had not been spotted.
Zero collateral over-redaction in this corpus slice.

**Bar-lock item:** a hand-maintained table does not scale to 1,153 subjects. The
real answer is a name-normalisation resource, and it is the same decision as the
NER item in 8.6.

### 8.3 D3.2's fuzzy host rule: the 0.60 threshold is PROVISIONAL (T1 round 4)

MediaSum misspells a programme name ("CNN International Diplomatic Linense"),
so D3.2 had to accept a fuzzy descriptor/programme match. The adopted threshold
is **0.60** and it is explicitly provisional pending bar-lock. The evidence it
was set from:

* **Separation**: the true anchor descriptor scores **0.680** against that
  programme string; the best non-anchor descriptor in the same transcripts
  scores **0.379**. A margin of 0.30 -- and a 0.70 threshold would have missed
  the true anchor, which is why the bar is this low.
* **Corpus-wide fire rate** of the adopted predicate: **3.86%** of transcripts
  (1,112 of 28,804), 1,787 turns; the fuzzy arm alone accounts for 202 of them.

It has not been validated against a labelled sample. Review before any
confirmatory-scale use. Its effect here was large and local: C00292's grounding
host turns went 74 -> 330 and its host->guest pairs 18 -> 87, all through one
descriptor at ratio 0.68, with the guest side unchanged.

### 8.4 The imposter donors: register, not topic (T3, and what fixed it)

D7's first implementation measured **how similarly two people talk on air**, not
what they talk about. Plain TF-IDF with raw counts over ~74 documents let
conversational filler dominate the vectors: a British novelist and a US
political strategist scored 0.75, and one generic donor was in the top three for
all six subjects. The v1.2 amendment (drop terms with document frequency > 0.9)
fixed it: six subjects now have six distinct donors, similarities fell to a
meaningful 0.11-0.48, and a novelist gets a novelist.

Three residuals travel with the imposter arm:

* **C00292's donor is a near-miss the rule got wrong.** A UN correspondent was
  matched to a US partisan strategist (Ron Christie, 0.2196), **0.0091** ahead of
  a UN ambassador (Al Hussein, 0.2105) who is the obviously better same-domain
  donor. Not overridden by hand -- the rule is the rule. Cheapest of the six to
  be wrong about, since C00292 is burned for Q-A and its imposter arm never runs.
* **Two margins are near a thousandth of a point**: C02006 -> Walter Mosley by
  **0.0011** and C02013 -> Doris Meissner by **0.0016**. Both winners are the
  more sensible candidate, but neither pair is robust; any further change to turn
  extraction could flip them. That is a consequence of thin grounding text
  (1,397 and 1,714 guest words), not of the matching rule.
* **The control is stronger where the topic has its own vocabulary.** Syria, Arab
  politics and nuclear diplomacy give 0.12-0.13 margins and unambiguous topical
  agreement. "Urban sociology" and "literary fiction" do not exist as distinct
  vocabularies in a corpus of broadcast talk, and those pairs are weaker.

One asymmetry this driver measured: C02013's donor grounding renders at 2,050
words against C02013's own 1,817, so on that subject the imposter arm carries
slightly MORE excerpt text than the twin arm.

### 8.5 The distractors' topic control is weak, and the zero-info arms are how we know

A4 wants three controls on a wrong option: similar length, similar entity
density, similar topic. **Length and density held on every item** -- all 18
matched at relaxation rung 0, the pre-registered control, and the ladder has
never fired. **Topic did not.**

    distractor bank                                652 rows from 167 donors
                                                   (SPEC expected ~2k)
    distractor question-similarity cosine, range   0.016 - 0.102
    median across the 54 distractors               0.050
    items whose best distractor cleared 0.10       1 of 18

A cosine of 0.05 on TF-IDF 1-2 grams means the "most similar" donor question is
about something else entirely: an Egyptian field marshal against Homo sapiens and
LGBT bishops; Kofi Annan against drone strikes.

**Consequence for reading every table in section 5:** the forced choice is easier
than A4 intends, and a model that knows nothing about the person can score above
chance by picking the topically plausible option. The instrument that catches
this is already in the design -- the zero-information arms and the A4.3
adversarial filter -- which is why no twin number in this report appears without
its baseline. The lever for a real topic control is a bigger, stratified bank
(more donors, donors on one-on-one interview programmes), not a change to the
extraction rules.

### 8.6 D5's entity heuristic: three known limitations, all deferred to the NER decision

D5 is a documented pilot-grade heuristic and upgrading it to real NER is a
bar-lock decision. Three limits are pinned by labelled tests so they cannot
change silently:

1. **Spelled-out titles.** D5-r3's abbreviation clause matches all 83 entries of
   the HONORIFIC set, including 58 spelled out in full, so "became president. And
   of course" reads as an abbreviation and glues the next word into a span.
   Measured: 15 of 652 bank rows (2%), 19 occurrences; **4 rows and 0 items would
   change bucket if fixed**, so no option set depends on it.
2. **"St." is not covered.** Not in HONORIFIC, no internal dot, not an initial, so
   "St. Petersburg" still splits and "Petersburg" survives into the stripped text.
3. **A single-token proper noun opening a sentence survives entity-stripping**
   (SPEC v1.7 records this). D5's sentence-initial rule cannot tell it from an
   ordinary capitalised word.

All three degrade the A4.2 entity-stripped option variant only -- they leave a
name in text that variant exists to scrub, which makes the stripped condition a
slightly weaker adversarial re-score than intended. None of them touches the
standard variant. The proposed fix for 1 and 2 is one curated abbreviation
subset instead of all of HONORIFIC; 3 needs NER.

### 8.7 Test-interview Q-A eligibility: a floor proposal

The pilot's binding constraint is not answer length and never was: **23 of the 46
candidate host->guest pairs were dropped for not being questions** (no question
mark, no interrogative or imperative first word), and 0 answers were dropped for
being under 30 words. D4's cue filter is doing the work, and it is doing it
correctly -- those turns are statements and hand-offs.

What actually decides whether a subject can be measured is the shape of its test
interview. Proposal for bar-lock, to be applied at DRAW time rather than
discovered afterwards:

* require the test-interview cluster to yield **>= 3** D4-eligible items, and
* prefer one-on-one interview programmes over roundtables and multi-guest panels.

Evidence from the six: C00292 (a roundtable) yields 0 usable items because every
host turn before one of its guest turns is a statement; C01677 (a three-guest
panel) yields 1, because most host questions are answered by somebody else;
C02124 (a two-person NPR interview, strictly alternating) yields 4 of 6 possible
and is the shape the design wants. A floor of 3 would have rejected two of six
subjects at draw time, at the cost of drawing deeper into the shuffled order.

### 8.8 Items per subject vs H1 power

    C00792  5      C02013  4      C02124  4
    C02006  3      C01677  1      C00292  0 (burned)
    total  17 scoreable items across 5 subjects

Against D4's cap of 20 items PER SUBJECT. The consequences are structural, not
fixable by tuning:

* Any subject-paired contrast has **5 pairs**, and one of those pairs rests on a
  single item, so its per-subject "mean" is one observation.
* This report therefore prints **N per cell** everywhere and runs **no
  significance test at all**. That is deliberate. A p-value on 17 items would
  invite exactly the reading the pilot cannot support.
* For H1 at confirmatory scale the lever is subject selection (8.7), not the
  extraction rules. The pilot's job was to prove the pipeline; it did.

### 8.9 The C00292 burn, and what it is still used for

C00292 (Bassir Pour) was drawn second in the frozen order and is the only subject
retired for Q-A. The story, in order:

1. It first produced **zero** host->guest pairs at all: its CNN transcripts name
   the anchor in full once ("RICHARD ROTH, CNN ANCHOR") and then say "ROTH" for
   the next 35 turns, which the speaker classifier read as a guest.
2. D3.1-r2 (within-transcript surname resolution) and then D3.2 (the programme-
   name anchor rule, 8.3) recovered the anchor: grounding host turns 1 -> 74 ->
   330, host->guest pairs 0 -> 18 -> 87.
3. Its Q-A yield **still did not move off 0**, and no labelling rule can move it:
   DIPLOMATIC LICENSE is a roundtable and every host turn before one of its guest
   turns is a statement, which D4's cue filter correctly rejects.
4. Owner decision: the cue filter stays; C00292 stays a dev subject **forever**
   (burned, never reused, never replaced-and-forgotten); a sixth subject
   (C02124) was added alongside it rather than substituted for it.
5. A later rules change gave it a yield of **1** item with a full option set on
   disk. **The burn does not flip on yield drift.** That one item and its four
   options exist in `subjects/C00292/` and are excluded here by filtering on the
   `burned_for_qa` annotation -- asserted at build, at export, and at verify.

It is a full participant everywhere else, and it is not a passenger: it
contributes **167 of the 469 classifier cases**, more than any other subject.

### 8.10 Classifier prompts are deliberately NOT redacted

SPEC D9 says nothing about redaction, and the follow-up classifier is a
measurement instrument over the corpus rather than an evaluation arm: it reads
three host/guest turns and emits FOLLOW-UP or NEW-TOPIC. Its output is a label on
an interview turn. It feeds descriptive statistics about interview structure --
never a prediction prompt, never an option set, never a score. So a name inside a
classifier prompt cannot leak into anything the twin arms are measured on, and
the prompts carry the transcript text as written ("Mr. Harris, thanks so much for
talking to us").

Recorded as a decision, not an oversight. Redacting them would cost nothing if a
later review prefers uniformity.

### 8.11 Grounding words vs the 2,000-word budget, per subject

T1's standing concern was that four of six subjects had less grounding text than
SPEC D8's `B_pilot` = 2,000 words, so selection would be a no-op. That was
measured on **guest** words. An exchange carries its host turn too, and on the
real segments every subject reaches or nearly reaches the budget:

    subject   segments  exchanges  words available  words rendered
    C00792       2         21          2,177           2,036
    C02013       2         17          2,081           1,817
    C02124       8         68          8,630           2,038
    C01677       2         14          2,425           1,836
    C02006       2         14          1,907           1,937
    C00292      12        177          8,539           (classifier only)

Donor blocks all render at 2,026-2,060 words, so the imposter arm is never
thinner than the twin arm.

Reading: **C02124 is the only subject where most-recent-first selection discards
a lot** (8,630 available against a 2,000 budget). C02013, C01677 and C02006 land
under budget because the skip-and-continue rule declined an oversized exchange,
not because the material ran out. So this pilot still says almost nothing about
selection *policy* -- H2's arms need subjects with several times the budget
available, which is a draw-time criterion, same family as 8.7.
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def rel(path: Path) -> str:
    """Repo-relative path for printing, absolute when it is outside the repo."""
    try:
        return str(Path(path).relative_to(_ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Subjects, donors, and the C00292 exclusion
# ---------------------------------------------------------------------------


def dev_subjects(pilot_dir=PILOT_DIR) -> list[dict]:
    """The committed draw. Never re-drawn, and never silently short."""
    doc = S.load_dev_subjects(pilot_dir)
    subjects = list(doc["subjects"])
    if len(subjects) != 6:
        raise fatal(f"expected 6 dev subjects, dev_subjects.json has "
                    f"{len(subjects)}")
    return subjects


def prediction_subjects(subjects: list[dict]) -> list[dict]:
    """The Q-A-capable dev subjects: everyone the draw did not burn for Q-A.

    SPEC D1 / T1 round 2 retired C00292 in place. T2 built its Q-A item and its
    full four-option set anyway (nothing in T2 filters on the annotation), so
    the exclusion has to happen HERE or a burned subject silently enters five
    prediction arms. The filter is on the annotation, not on the id.
    """
    keep = [s for s in subjects if not s.get("burned_for_qa")]
    burned = [s["canonical_id"] for s in subjects if s.get("burned_for_qa")]
    if not burned:
        raise fatal("no dev subject carries burned_for_qa; the draw that this "
                    "driver was written against retired C00292 in place, so "
                    "either dev_subjects.json changed or it is the wrong file")
    if len(keep) + len(burned) != len(subjects):
        raise fatal("burned_for_qa partition does not cover the draw")
    return keep


def classifier_subjects(subjects: list[dict]) -> list[dict]:
    """All six. The burned subject is a full participant in the classifier."""
    return list(subjects)


def pool_rows() -> dict:
    return {r["canonical_id"]: r for r in S.load_pool()}


def first_name_of(variant: str) -> tuple[str, int] | None:
    """``(casefolded first name, its token index)`` for a variant, or None.

    The first token that is neither an honorific nor a bare initial. Returns the
    index so the caller can substitute in place and keep the rest of the name.
    """
    tokens = variant.split()
    for idx, token in enumerate(tokens):
        bare = token.strip(".,;:'\"").casefold()
        if not bare or not bare.isalpha():
            continue                      # "R." -- an initial, not a first name
        if bare.upper() in S.HONORIFIC:
            continue                      # "Dr.", "Professor", ...
        if len(bare) < 2:
            continue
        return bare, idx
    return None


def nickname_forms(variants) -> list[str]:
    """Whole substituted names from :data:`NICKNAME_SUPPLEMENT`.

    "Matthew Kroenig" -> "Matt Kroenig", "Matty Kroenig". Never a bare token:
    T4's expansion reduces these to "Matt"/"Matty"/"Kroenig" itself, so the
    matching semantics stay entirely inside the frozen renderer.
    """
    out: list[str] = []
    for variant in variants:
        found = first_name_of(variant)
        if found is None:
            continue
        first, idx = found
        for nick in NICKNAME_SUPPLEMENT.get(first, ()):
            tokens = variant.split()
            tokens[idx] = nick
            out.append(" ".join(tokens))
    return out


def name_variants(row: dict) -> list[str]:
    """Every string the redactor must be able to reach for one person.

    The pool's ``variants`` column, plus ``canonical_name``, plus the nickname
    supplement. T4's ``redact`` expands each of these to its bare name tokens by
    default, which is what catches the surnames the transcripts actually use.
    """
    out = list(row.get("variants") or [])
    canonical = (row.get("canonical_name") or "").strip()
    if canonical and canonical not in out:
        out.append(canonical)
    out += nickname_forms(out)
    variants = sorted({v.strip() for v in out if v and v.strip()})
    if not variants:
        raise fatal(f"{row.get('canonical_id')} has no name variants at all; "
                    "redaction would be a no-op")
    return variants


def assert_label_coverage(cid: str, turns: list[dict], variants: list[str],
                          where: str) -> list[str]:
    """Every name form the corpus uses for this person must be reachable.

    The pool's ``variants`` column is usually just the full name, while a
    transcript's own speaker label sometimes carries a first name that is not in
    it (C00292 is labelled ``AFSANE BASSIR POUR`` against a pool variant of
    ``Bassir Pour``). T4's guard is exactly as strong as its scrubber, so a name
    form outside the variant list is a leak the guard cannot see. Returns the
    uncovered forms; the caller decides whether that is fatal.
    """
    uncovered: list[str] = []
    seen: set[str] = set()
    for turn in turns:
        if turn.get("role") != "guest":
            continue
        label = turn.get("speaker_label") or ""
        if label in seen:
            continue
        seen.add(label)
        tokens = S.label_tokens(label)
        for token in tokens:
            if len(token) < 2:
                continue
            if not R.surviving_variants(token, variants):
                uncovered.append(f"{cid} {where}: {label!r} -> {token!r}")
    return sorted(set(uncovered))


def imposter_pairs(path=IMPOSTER_PAIRS) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(doc["pairs"])


# ---------------------------------------------------------------------------
# Grounding segments (SPEC D8 shape, built from D3 turn files)
# ---------------------------------------------------------------------------


def build_exchanges(turns: list[dict]) -> list[dict]:
    """One transcript's turns -> T4's ``exchanges`` list.

    An exchange is a maximal run of consecutive guest turns, joined with single
    spaces, plus the host turn immediately before the run when the turn
    immediately before the run IS a host turn. When an "other" speaker
    intervened, the host side is empty and the exchange renders one line. A run
    whose joined guest text is empty is dropped -- an exchange with no guest
    speech is not evidence about the guest.

    ``turns`` is a SPEC D3 list for ONE transcript, in any order; it is sorted
    by ``turn_idx`` here so the caller cannot pass an accidental ordering.
    """
    ordered = sorted(turns, key=lambda t: t["turn_idx"])
    exchanges: list[dict] = []
    run: list[str] = []
    run_host = ""
    for pos, turn in enumerate(ordered):
        if turn.get("role") == "guest":
            if not run:
                prev = ordered[pos - 1] if pos else None
                run_host = (prev.get("text") or "").strip() \
                    if prev is not None and prev.get("role") == "host" else ""
            run.append((turn.get("text") or "").strip())
            continue
        if run:
            _flush_exchange(exchanges, run_host, run)
            run = []
    if run:
        _flush_exchange(exchanges, run_host, run)
    return exchanges


def _flush_exchange(exchanges: list[dict], host: str, run: list[str]) -> None:
    guest = " ".join(part for part in run if part).strip()
    if not guest:
        return
    exchanges.append({"host_text": host, "guest_text": guest})


def build_segments(turns: list[dict], split: dict) -> list[dict]:
    """T4's segment list for one person's grounding side.

    One segment per grounding transcript that yields at least one exchange,
    carrying the date and program the split recorded, ordered by (date,
    transcript_id) so the input order is deterministic. ``render_grounding``
    re-sorts by date itself; the tie-break it falls back on is input position,
    which is why the order is pinned here rather than left to dict iteration.
    """
    meta = {g["transcript_id"]: g for g in split.get("grounding", [])}
    test_tid = (split.get("test") or {}).get("transcript_id")
    by_tid: dict[str, list[dict]] = {}
    for turn in turns:
        by_tid.setdefault(turn["transcript_id"], []).append(turn)
    if test_tid and test_tid in by_tid:
        # D8 guard (b). T1 asserts this when it writes the split; asserting it
        # again here costs nothing and this is the file that would carry the
        # damage.
        raise fatal(f"test transcript {test_tid} appears in the grounding turn "
                    "file -- the test interview must never enter grounding")
    segments = []
    for tid in sorted(by_tid, key=lambda t: (meta.get(t, {}).get("date", ""), t)):
        exchanges = build_exchanges(by_tid[tid])
        if not exchanges:
            continue
        entry = meta.get(tid, {})
        segments.append({
            "transcript_id": tid,
            "date": entry.get("date", ""),
            "program": entry.get("program", ""),
            "title": entry.get("title", ""),
            "exchanges": exchanges,
        })
    if not segments:
        raise fatal("no grounding segments could be built")
    return segments


def subject_grounding(cid: str, pilot_dir=PILOT_DIR) -> tuple[list[dict], list[dict]]:
    turns = S.read_jsonl(S.subject_dir(cid, pilot_dir) / "grounding_turns.jsonl")
    split = S.load_split(cid, pilot_dir)
    return build_segments(turns, split), turns


def donor_grounding(donor_id: str, pilot_dir=PILOT_DIR) -> tuple[list[dict], list[dict]]:
    base = Path(pilot_dir) / "donors" / donor_id
    turns = S.read_jsonl(base / "grounding_turns.jsonl")
    split = json.loads((base / "split.json").read_text(encoding="utf-8"))
    return build_segments(turns, split), turns


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


def load_items(cid: str, pilot_dir=PILOT_DIR) -> list[dict]:
    """T2's Q-A items joined to their option sets, in file order."""
    base = S.subject_dir(cid, pilot_dir)
    qa = S.read_jsonl(base / "qa_items.jsonl")
    opts = {row["item_id"]: row for row in
            S.read_jsonl(base / "distractors.jsonl")}
    items = []
    for row in qa:
        options = opts.get(row["item_id"])
        if options is None:
            raise fatal(f"{row['item_id']} has no distractors.jsonl row")
        texts = [o["text"] for o in options["options"]]
        stripped = list(options["options_stripped"])
        if len(texts) != len(stripped):
            raise fatal(f"{row['item_id']}: option/stripped length mismatch")
        correct = int(options["correct_index"])
        if not 0 <= correct < len(texts):
            raise fatal(f"{row['item_id']}: correct_index out of range")
        if options["options"][correct]["kind"] != "true":
            raise fatal(f"{row['item_id']}: correct_index does not point at "
                        "the true option")
        items.append({
            "item_id": row["item_id"],
            "canonical_id": row["canonical_id"],
            "transcript_id": row["transcript_id"],
            "q_turn_idx": row["q_turn_idx"],
            "question": row["question"],
            "answer": row["answer"],
            "answer_words": row["answer_words"],
            "options": {"standard": texts, "stripped": stripped},
            "correct_index": correct,
            "relax_rung": options.get("relax_rung"),
            "flags": row.get("flags", []),
        })
    return items


# ---------------------------------------------------------------------------
# Rendering + guards
# ---------------------------------------------------------------------------


def _name_line(arm: str, name: str) -> str:
    if arm == "twin_named":
        return R.TWIN_NAME_LINE.format(name=name)
    if arm == "zeroinfo_named":
        return R.ZEROINFO_NAME_LINE.format(name=name)
    raise fatal(f"{arm} is not a named arm")


_REDACTED_TWIN = {"twin_named": "twin_redacted",
                  "zeroinfo_named": "zeroinfo_redacted"}


def render_and_guard(arm: str, variant: str, item: dict, *,
                     subject_name: str, subject_variants: list[str],
                     grounding_block: str | None,
                     donor_variants: list[str] | None = None) -> dict:
    """Render one prompt and prove both D8 guards on it. Raises on any trip.

    ``grounding_block`` is already rendered AND already redacted (with the
    donor's variants for the imposter arm, the subject's for the twin arms).
    The question and every option are redacted here, with the SUBJECT's
    variants, for every arm including the imposter one -- they come from the
    subject's test interview and the distractor bank either way.
    """
    question = R.redact(item["question"], subject_variants)
    options = [R.redact(text, subject_variants)
               for text in item["options"][variant]]
    grounded = arm in R.GROUNDED_ARMS
    named = arm in R.NAMED_ARMS

    rendered = R.render_prompt(
        arm, question, options,
        grounding_block=grounding_block if grounded else None,
        name=subject_name if named else None,
    )

    # --- guard (c): no name may survive in the rendered string ---------------
    # A named arm reveals the name on purpose, on exactly one line. Strip that
    # line and assert on the rest -- and check while we are there that removing
    # it reproduces the redacted arm byte for byte, which is T4's own
    # one-factor invariant and catches template drift for free.
    guarded = rendered
    if named:
        line = _name_line(arm, subject_name)
        marker = f"{line}\n\n"
        if marker not in rendered:
            raise fatal(f"{arm} {item['item_id']}: the name line is not where "
                        "the template says it is")
        guarded = rendered.replace(marker, "", 1)
        twin = R.render_prompt(
            _REDACTED_TWIN[arm], question, options,
            grounding_block=grounding_block if grounded else None,
        )
        if guarded != twin:
            raise fatal(f"{arm} {item['item_id']}: differs from its redacted "
                        "counterpart by more than the name line")
    R.assert_redacted(guarded, subject_variants)
    if donor_variants is not None:
        # The imposter arm has two identities and neither list covers the
        # other. Asserting only the donor's would let the subject's name
        # through the question, which is the leak that makes an imposter prompt
        # look like a twin (T4 section 9.2).
        R.assert_redacted(rendered, donor_variants)

    # --- guard (a): the true answer must not sit in the excerpts -------------
    if grounded:
        true_raw = item["answer"]
        true_shown = options[item["correct_index"]]
        R.assert_no_answer_leak(grounding_block, true_raw)
        R.assert_no_answer_leak(grounding_block, true_shown)

    # --- zero-information arms carry no excerpts, program or date ------------
    if not grounded:
        if R.EXCERPTS_HEADER in rendered or "[Interview," in rendered:
            raise fatal(f"{arm} {item['item_id']}: a zero-information prompt "
                        "carries an excerpt block")

    words = R.word_count(rendered)
    return {
        "prompt": rendered,
        "prompt_sha256": R.sha256(rendered),
        "prompt_words": words,
        "prompt_tokens_est": int(round(words * TOKENS_PER_WORD)),
        "max_output_tokens": PREDICTION_MAX_OUTPUT_TOKENS,
    }


# ---------------------------------------------------------------------------
# The build: everything in memory, guards proven, before a byte is written
# ---------------------------------------------------------------------------


def build_prediction(pilot_dir=PILOT_DIR) -> dict:
    """Every prediction prompt for every arm and both option variants."""
    subjects = dev_subjects(pilot_dir)
    dev_ids = {s["canonical_id"] for s in subjects}
    qa_subjects = prediction_subjects(subjects)
    pool = pool_rows()
    pairs = imposter_pairs(Path(pilot_dir) / "imposter_pairs.json")

    sets: dict[tuple[str, str], list[dict]] = {
        (arm, variant): [] for arm in ARMS for variant in VARIANTS}
    per_subject: dict[str, dict] = {}
    coverage_warnings: list[str] = []

    for subject in qa_subjects:
        cid = subject["canonical_id"]
        if cid not in dev_ids:
            raise fatal(f"{cid} is not in dev_subjects.json")
        if subject.get("burned_for_qa"):
            raise fatal(f"{cid} is burned_for_qa and must not reach a "
                        "prediction arm")
        row = pool[cid]
        variants = name_variants(row)
        name = row["canonical_name"]

        segments, turns = subject_grounding(cid, pilot_dir)
        coverage_warnings += assert_label_coverage(cid, turns, variants,
                                                   "grounding")
        twin_raw = R.render_grounding(segments, GROUNDING_BUDGET_WORDS)
        twin_block = R.redact(twin_raw, variants)
        R.assert_redacted(twin_block, variants)

        donor_id = pairs.get(cid)
        if donor_id is None:
            raise fatal(f"{cid} has no imposter donor in imposter_pairs.json")
        if donor_id in dev_ids:
            raise fatal(f"donor {donor_id} for {cid} is itself a dev subject")
        donor_row = pool[donor_id]
        donor_variants = name_variants(donor_row)
        donor_segments, donor_turns = donor_grounding(donor_id, pilot_dir)
        coverage_warnings += assert_label_coverage(
            donor_id, donor_turns, donor_variants, f"donor of {cid}")
        donor_raw = R.render_grounding(donor_segments, GROUNDING_BUDGET_WORDS)
        donor_block = R.redact(donor_raw, donor_variants)
        R.assert_redacted(donor_block, donor_variants)

        items = load_items(cid, pilot_dir)
        for item in items:
            if item["canonical_id"] != cid:
                raise fatal(f"{item['item_id']} claims subject "
                            f"{item['canonical_id']} in {cid}'s file")
            for arm in ARMS:
                if arm == "imposter_redacted":
                    block, donor_check = donor_block, donor_variants
                elif arm in R.GROUNDED_ARMS:
                    block, donor_check = twin_block, None
                else:
                    block, donor_check = None, None
                for variant in VARIANTS:
                    built = render_and_guard(
                        arm, variant, item,
                        subject_name=name, subject_variants=variants,
                        grounding_block=block, donor_variants=donor_check)
                    built.update({
                        "item_id": item["item_id"],
                        "canonical_id": cid,
                        "arm": arm,
                        "variant": variant,
                        "correct_index": item["correct_index"],
                        "n_options": len(item["options"][variant]),
                        "donor_id": donor_id if arm == "imposter_redacted"
                        else None,
                    })
                    sets[(arm, variant)].append(built)

        per_subject[cid] = {
            "canonical_id": cid,
            "canonical_name": name,
            "wiki_status": subject.get("wiki_status"),
            "n_items": len(items),
            "item_ids": [i["item_id"] for i in items],
            "donor_id": donor_id,
            "donor_name": donor_row["canonical_name"],
            "n_grounding_segments": len(segments),
            "n_grounding_exchanges": sum(len(s["exchanges"]) for s in segments),
            "grounding_words_available": sum(
                R.word_count(e["host_text"]) + R.word_count(e["guest_text"])
                for s in segments for e in s["exchanges"]),
            "grounding_words_rendered": R.word_count(twin_block),
            "donor_grounding_words_rendered": R.word_count(donor_block),
            "grounding_budget_words": GROUNDING_BUDGET_WORDS,
            "variants_used": variants,
            "donor_variants_used": donor_variants,
        }

    n = {key: len(rows) for key, rows in sets.items()}
    if len(set(n.values())) != 1:
        raise fatal(f"prompt sets are not the same size: {n}")
    return {
        "sets": sets,
        "per_subject": per_subject,
        "n_items": sum(v["n_items"] for v in per_subject.values()),
        "n_subjects": len(per_subject),
        "coverage_warnings": coverage_warnings,
        "excluded_burned_for_qa": sorted(
            s["canonical_id"] for s in subjects if s.get("burned_for_qa")),
    }


def build_classifier(pilot_dir=PILOT_DIR) -> dict:
    """Every follow-up classifier case, over all six subjects' grounding."""
    subjects = classifier_subjects(dev_subjects(pilot_dir))
    dev_ids = {s["canonical_id"] for s in subjects}
    cases: list[dict] = []
    rule_labels: list[dict] = []
    per_subject: dict[str, dict] = {}

    for subject in subjects:
        cid = subject["canonical_id"]
        if cid not in dev_ids:
            raise fatal(f"{cid} is not in dev_subjects.json")
        turns = S.read_jsonl(
            S.subject_dir(cid, pilot_dir) / "grounding_turns.jsonl")
        by_tid: dict[str, list[dict]] = {}
        for turn in turns:
            by_tid.setdefault(turn["transcript_id"], []).append(turn)
        n_model = n_rule = 0
        for tid in sorted(by_tid):
            ordered = sorted(by_tid[tid], key=lambda t: t["turn_idx"])
            for case in F.classifiable_turns(ordered):
                if case.get("source") == "rule":
                    rule_labels.append({
                        "canonical_id": cid, "transcript_id": tid,
                        "turn_idx": case["turn_idx"], "label": case["label"],
                        "source": "rule",
                    })
                    n_rule += 1
                    continue
                prompt = F.classify_prompt(
                    prev_host=case["prev_host"],
                    guest_answer=case["guest_answer"],
                    target_host=case["target_host"])
                cases.append({
                    "canonical_id": cid,
                    "transcript_id": tid,
                    "turn_idx": case["turn_idx"],
                    "target_host": case["target_host"][:240],
                    "prompt": prompt,
                    "prompt_sha256": F.sha256(prompt),
                    "prompt_words": R.word_count(prompt),
                    "prompt_tokens_est": int(round(
                        R.word_count(prompt) * TOKENS_PER_WORD)),
                    "max_output_tokens": F.MAX_OUTPUT_TOKENS,
                })
                n_model += 1
        per_subject[cid] = {
            "canonical_id": cid,
            "canonical_name": subject.get("canonical_name"),
            "n_transcripts": len(by_tid),
            "n_model_cases": n_model,
            "n_rule_labels": n_rule,
            "burned_for_qa": bool(subject.get("burned_for_qa")),
        }
    return {
        "cases": cases,
        "rule_labels": rule_labels,
        "per_subject": per_subject,
        "rubric_sha256": F.RUBRIC_SHA256,
    }


def build_all(pilot_dir=PILOT_DIR) -> dict:
    pred = build_prediction(pilot_dir)
    clf = build_classifier(pilot_dir)
    return {"prediction": pred, "classifier": clf}


def context_check(build: dict) -> dict:
    """Prove the longest prompt fits the configured context window.

    A prompt longer than ``--max-model-len`` is refused by vLLM at generation
    time, on the node, after the engine has been paid for. Cheaper to fail here.
    """
    rows = [r for rows in build["prediction"]["sets"].values() for r in rows]
    rows += build["classifier"]["cases"]
    worst = max(rows, key=lambda r: r["prompt_words"])
    need = int(round(worst["prompt_words"] * TOKENS_PER_WORD_MAX)) \
        + worst["max_output_tokens"]
    out = {
        "longest_prompt_words": worst["prompt_words"],
        "longest_prompt_sha256": worst["prompt_sha256"],
        "longest_prompt_item": worst.get("item_id") or worst.get("transcript_id"),
        "longest_prompt_arm": worst.get("arm", "classifier"),
        "tokens_per_word_max": TOKENS_PER_WORD_MAX,
        "worst_case_tokens_needed": need,
        "max_model_len": MAX_MODEL_LEN,
        "headroom_tokens": MAX_MODEL_LEN - need,
    }
    if need > MAX_MODEL_LEN:
        raise fatal(
            f"longest prompt is {worst['prompt_words']} words -> up to {need} "
            f"tokens with its {worst['max_output_tokens']}-token reply, which "
            f"does not fit MAX_MODEL_LEN={MAX_MODEL_LEN}")
    return out


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def projection(build: dict) -> dict:
    """Node-hours, from the real prompts and Stage 1E's measured throughput."""
    pred_rows = [r for rows in build["prediction"]["sets"].values() for r in rows]
    clf_rows = build["classifier"]["cases"]
    eff = MEASURED_TOKENS_PER_SECOND / LONG_PROMPT_DERATE

    def block(rows: list[dict]) -> dict:
        tin = sum(r["prompt_tokens_est"] for r in rows)
        tout = sum(r["max_output_tokens"] for r in rows)
        return {"n_calls": len(rows), "tokens_in_est": tin,
                "tokens_out_cap": tout, "seconds": (tin + tout) / eff}

    pred, clf = block(pred_rows), block(clf_rows)
    smoke_rows = smoke_slice(build)
    smoke = block(smoke_rows)

    full_seconds = pred["seconds"] + clf["seconds"] + ENGINE_INIT_SECONDS
    smoke_seconds = smoke["seconds"] + ENGINE_INIT_SECONDS
    jobs = {
        "stage2_pilot_smoke": {
            "n_calls": smoke["n_calls"],
            "generation_seconds": round(smoke["seconds"], 1),
            "engine_init_seconds": ENGINE_INIT_SECONDS,
            "projected_node_hours": round(smoke_seconds / 3600, 4),
            "walltime": SMOKE_WALLTIME, "qos": SMOKE_QOS,
        },
        "stage2_pilot_full": {
            "n_calls": pred["n_calls"] + clf["n_calls"],
            "generation_seconds": round(pred["seconds"] + clf["seconds"], 1),
            "engine_init_seconds": ENGINE_INIT_SECONDS,
            "projected_node_hours": round(full_seconds / 3600, 4),
            "walltime": FULL_WALLTIME, "qos": "boost_usr_prod (normal)",
        },
    }
    total = round(sum(j["projected_node_hours"] for j in jobs.values()), 4)
    walltime_bound = round(_walltime_hours(SMOKE_WALLTIME)
                           + _walltime_hours(FULL_WALLTIME), 4)
    return {
        "prediction": pred, "classifier": clf, "smoke": smoke,
        "effective_tokens_per_second": round(eff, 1),
        "measured_tokens_per_second": MEASURED_TOKENS_PER_SECOND,
        "long_prompt_derate": LONG_PROMPT_DERATE,
        "tokens_per_word": TOKENS_PER_WORD,
        "jobs": jobs,
        "total_projected_node_hours": total,
        "walltime_bounded_worst_case_node_hours": walltime_bound,
        "abort_above_node_hours": PROJECTION_ABORT_NODE_HOURS,
        "budget_node_hours": BUDGET_NODE_HOURS,
        "note": "Output tokens are counted at their per-prompt CAP (120 for a "
                "prediction prompt, 80 for a classifier case), so the "
                "generation term is an upper bound. Throughput is Stage 1E's "
                "measured 21,015 combined tokens/s on one 4xA100 node, "
                f"de-rated by {LONG_PROMPT_DERATE}x because Stage 2's prompts "
                "are roughly ten times longer and shift the job from "
                "decode-bound to prefill-bound.",
    }


def _walltime_hours(walltime: str) -> float:
    hh, mm, ss = (int(p) for p in walltime.split(":"))
    return hh + mm / 60 + ss / 3600


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def set_name(arm: str, variant: str) -> str:
    return f"pred_{arm}_{variant}"


def smoke_slice(build: dict) -> list[dict]:
    """~20 prompts spanning every prompt set, in a stable order."""
    rows: list[dict] = []
    for arm in ARMS:
        for variant in VARIANTS:
            src = build["prediction"]["sets"][(arm, variant)]
            for row in src[:SMOKE_PER_SET]:
                rows.append(dict(row, source_set=set_name(arm, variant)))
    for row in build["classifier"]["cases"][:SMOKE_CLASSIFY]:
        rows.append(dict(row, source_set="classify"))
    return rows


def _write_pair(prompts_path: Path, meta_path: Path, rows: list[dict],
                meta_fields: tuple[str, ...]) -> dict:
    """Write one prompts/sidecar pair. ``idx`` is the row's position in the file.

    Per-file 0-based idx, because ``batch_generate.py`` echoes ``idx`` back per
    output file and each prompt set is its own file. The sidecar carries
    everything needed to join a completion to its item; the prompt file carries
    only what the node needs.
    """
    prompts, metas = [], []
    for idx, row in enumerate(rows):
        prompts.append({"idx": idx, "prompt": row["prompt"],
                        "max_output_tokens": row["max_output_tokens"]})
        meta = {"idx": idx}
        for field in meta_fields:
            meta[field] = row.get(field)
        metas.append(meta)
    S.write_jsonl(prompts_path, prompts)
    S.write_jsonl(meta_path, metas)
    return {
        "prompts_file": prompts_path.name,
        "meta_file": meta_path.name,
        "n_prompts": len(rows),
        "prompts_sha256": sha256_file(prompts_path),
        "meta_sha256": sha256_file(meta_path),
        "total_prompt_words": sum(r["prompt_words"] for r in rows),
        "max_prompt_words": max((r["prompt_words"] for r in rows), default=0),
    }


PRED_META_FIELDS = ("item_id", "canonical_id", "arm", "variant",
                    "correct_index", "n_options", "donor_id",
                    "prompt_sha256", "prompt_words")
CLF_META_FIELDS = ("canonical_id", "transcript_id", "turn_idx",
                   "target_host", "prompt_sha256", "prompt_words")
SMOKE_META_FIELDS = ("source_set", "item_id", "canonical_id", "arm", "variant",
                     "transcript_id", "turn_idx", "prompt_sha256",
                     "prompt_words")


def cmd_export(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    manifest_path = export_dir / "export_manifest.json"
    if manifest_path.exists() and not args.force:
        raise fatal(f"{manifest_path} already exists; pass --force to rebuild")

    build = build_all(pilot_dir)
    ctx = context_check(build)
    proj = projection(build)
    pred, clf = build["prediction"], build["classifier"]

    print(f"[export] {PILOT_BANNER}")
    print(f"[export] {pred['n_subjects']} Q-A subjects, {pred['n_items']} items, "
          f"{len(ARMS)} arms x {len(VARIANTS)} option variants")
    print(f"[export] excluded from every prediction arm (burned_for_qa): "
          f"{', '.join(pred['excluded_burned_for_qa'])}")
    if pred["coverage_warnings"]:
        for line in pred["coverage_warnings"]:
            print(f"[warn] name form outside the variant list: {line}",
                  file=sys.stderr)

    files: dict[str, dict] = {}
    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            rows = pred["sets"][(arm, variant)]
            files[name] = _write_pair(export_dir / f"prompts_{name}.jsonl",
                                      export_dir / f"meta_{name}.jsonl",
                                      rows, PRED_META_FIELDS)
            print(f"[export] {name}: {len(rows)} prompts")

    files["classify"] = _write_pair(export_dir / "prompts_classify.jsonl",
                                    export_dir / "meta_classify.jsonl",
                                    clf["cases"], CLF_META_FIELDS)
    print(f"[export] classify: {len(clf['cases'])} model prompts")

    smoke_rows = smoke_slice(build)
    files["smoke"] = _write_pair(export_dir / "prompts_smoke.jsonl",
                                 export_dir / "meta_smoke.jsonl",
                                 smoke_rows, SMOKE_META_FIELDS)
    print(f"[export] smoke: {len(smoke_rows)} prompts spanning "
          f"{len(ARMS) * len(VARIANTS) + 1} sets")

    rule_path = export_dir / "labels_rule.jsonl"
    S.write_jsonl(rule_path, clf["rule_labels"])
    files["labels_rule"] = {
        "prompts_file": None, "meta_file": rule_path.name,
        "n_prompts": 0, "n_rows": len(clf["rule_labels"]),
        "meta_sha256": sha256_file(rule_path),
    }
    print(f"[export] labels_rule: {len(clf['rule_labels'])} rule-labelled turns "
          "(NEW-TOPIC by definition, no model call)")

    doc = {
        "pilot": PILOT_BANNER,
        "exported_utc": now(),
        "contract": "SPEC.md v1.7 (D1-D10)",
        "n_qa_subjects": pred["n_subjects"],
        "n_items": pred["n_items"],
        "arms": list(ARMS),
        "option_variants": list(VARIANTS),
        "prediction_prompts_total": sum(
            files[set_name(a, v)]["n_prompts"] for a in ARMS for v in VARIANTS),
        "classifier_prompts_total": files["classify"]["n_prompts"],
        "rule_labels_total": len(clf["rule_labels"]),
        "excluded_burned_for_qa": pred["excluded_burned_for_qa"],
        "coverage_warnings": pred["coverage_warnings"],
        "grounding_budget_words": GROUNDING_BUDGET_WORDS,
        "renderer": {
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "followup_rubric_sha256": F.RUBRIC_SHA256,
            "stage2_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "followup_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/followup_render.py"),
        },
        "per_subject": pred["per_subject"],
        "classifier_per_subject": clf["per_subject"],
        "context": ctx,
        "projection": proj,
        "files": files,
    }
    S.write_json(manifest_path, doc)
    print(f"[export] manifest -> {manifest_path}")
    print(f"[export] projected {proj['total_projected_node_hours']} node-hours "
          f"(abort above {PROJECTION_ABORT_NODE_HOURS})")
    return 0


# ---------------------------------------------------------------------------
# Verify: re-run every guard against what is ON DISK
# ---------------------------------------------------------------------------


def cmd_verify(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    manifest_path = export_dir / "export_manifest.json"
    if not manifest_path.exists():
        raise fatal(f"{manifest_path} not found; run export first")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))

    subjects = dev_subjects(pilot_dir)
    dev_ids = {s["canonical_id"] for s in subjects}
    burned = {s["canonical_id"] for s in subjects if s.get("burned_for_qa")}
    pool = pool_rows()
    variants_of = {cid: name_variants(pool[cid]) for cid in dev_ids}
    checks = {"files": 0, "prompts": 0, "guard_redacted": 0,
              "guard_answer_leak": 0, "zeroinfo_clean": 0}

    # --- file digests --------------------------------------------------------
    for name, info in doc["files"].items():
        if info.get("prompts_file"):
            path = export_dir / info["prompts_file"]
            got = sha256_file(path)
            if got != info["prompts_sha256"]:
                raise fatal(f"{path.name} sha256 {got} != manifest "
                            f"{info['prompts_sha256']}")
            checks["files"] += 1
        meta_path = export_dir / info["meta_file"]
        got = sha256_file(meta_path)
        if got != info["meta_sha256"]:
            raise fatal(f"{meta_path.name} sha256 {got} != manifest "
                        f"{info['meta_sha256']}")
        checks["files"] += 1

    # --- true answers, for guard (a) ----------------------------------------
    answers: dict[str, dict] = {}
    for cid in dev_ids:
        for item in load_items(cid, pilot_dir):
            answers[item["item_id"]] = item

    donor_variants_of = {}
    for cid, donor_id in imposter_pairs(pilot_dir / "imposter_pairs.json").items():
        donor_variants_of[cid] = name_variants(pool[donor_id])

    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            prompts = S.read_jsonl(export_dir / f"prompts_{name}.jsonl")
            metas = S.read_jsonl(export_dir / f"meta_{name}.jsonl")
            joined = join_by_idx(prompts, metas)
            if len(joined) != len(prompts) or len(prompts) != len(metas):
                raise fatal(f"{name}: prompts/meta do not join 1:1 on idx")
            if len(joined) != doc["n_items"]:
                raise fatal(f"{name}: {len(joined)} prompts, expected "
                            f"{doc['n_items']}")
            for row in joined:
                cid = row["canonical_id"]
                if cid not in dev_ids:
                    raise fatal(f"{name} idx {row['idx']}: {cid} is not a dev "
                                "subject")
                if cid in burned:
                    raise fatal(f"{name} idx {row['idx']}: {cid} is "
                                "burned_for_qa and must not be in a "
                                "prediction prompt set")
                if row["arm"] != arm or row["variant"] != variant:
                    raise fatal(f"{name} idx {row['idx']}: sidecar says "
                                f"{row['arm']}/{row['variant']}")
                text = row["prompt"]
                if R.sha256(text) != row["prompt_sha256"]:
                    raise fatal(f"{name} idx {row['idx']}: prompt digest moved")
                guarded = text
                if arm in R.NAMED_ARMS:
                    line = _name_line(arm, pool[cid]["canonical_name"])
                    marker = f"{line}\n\n"
                    if marker not in text:
                        raise fatal(f"{name} idx {row['idx']}: named arm has "
                                    "no name line")
                    guarded = text.replace(marker, "", 1)
                R.assert_redacted(guarded, variants_of[cid])
                checks["guard_redacted"] += 1
                if arm == "imposter_redacted":
                    R.assert_redacted(text, donor_variants_of[cid])
                    checks["guard_redacted"] += 1
                if arm in R.GROUNDED_ARMS:
                    block = excerpt_block(text)
                    R.assert_no_answer_leak(block, answers[row["item_id"]]["answer"])
                    checks["guard_answer_leak"] += 1
                else:
                    if R.EXCERPTS_HEADER in text or "[Interview," in text:
                        raise fatal(f"{name} idx {row['idx']}: zero-information "
                                    "prompt carries excerpts")
                    checks["zeroinfo_clean"] += 1
                checks["prompts"] += 1

    prompts = S.read_jsonl(export_dir / "prompts_classify.jsonl")
    metas = S.read_jsonl(export_dir / "meta_classify.jsonl")
    joined = join_by_idx(prompts, metas)
    if len(joined) != len(prompts) or len(prompts) != len(metas):
        raise fatal("classify: prompts/meta do not join 1:1 on idx")
    for row in joined:
        if row["canonical_id"] not in dev_ids:
            raise fatal(f"classify idx {row['idx']}: "
                        f"{row['canonical_id']} is not a dev subject")
        if F.sha256(row["prompt"]) != row["prompt_sha256"]:
            raise fatal(f"classify idx {row['idx']}: prompt digest moved")
        if not row["prompt"].startswith(F.RUBRIC_V1):
            raise fatal(f"classify idx {row['idx']}: prompt does not open on "
                        "the frozen rubric")
        checks["prompts"] += 1

    print(f"[verify] {PILOT_BANNER}")
    print(f"[verify] {checks['files']} file digests match the manifest")
    print(f"[verify] {checks['prompts']} prompts re-checked on disk")
    print(f"[verify] {checks['guard_redacted']} redaction assertions passed "
          f"({checks['guard_answer_leak']} answer-leak, "
          f"{checks['zeroinfo_clean']} zero-information cleanliness)")
    print(f"[verify] burned_for_qa {sorted(burned)} absent from all "
          f"{len(ARMS) * len(VARIANTS)} prediction sets")
    return 0


def join_by_idx(prompts: list[dict], metas: list[dict]) -> list[dict]:
    """Join a prompts file to its sidecar on ``idx``. Missing/extra idx is fatal."""
    by_idx = {}
    for row in metas:
        idx = int(row["idx"])
        if idx in by_idx:
            raise fatal(f"sidecar has duplicate idx {idx}")
        by_idx[idx] = row
    out = []
    for row in prompts:
        idx = int(row["idx"])
        meta = by_idx.pop(idx, None)
        if meta is None:
            raise fatal(f"prompt idx {idx} has no sidecar row")
        out.append({**meta, **row, "idx": idx})
    if by_idx:
        raise fatal(f"sidecar has {len(by_idx)} rows with no prompt: "
                    f"{sorted(by_idx)[:5]}")
    return out


def excerpt_block(rendered: str) -> str:
    """The PAST INTERVIEWS block of a rendered twin/imposter prompt."""
    start = rendered.find(R.EXCERPTS_HEADER)
    if start < 0:
        return ""
    start += len(R.EXCERPTS_HEADER)
    end = rendered.find(R.LATER_HEADER, start)
    return rendered[start:end if end >= 0 else None].strip()


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def cmd_plan(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    build = build_all(pilot_dir)
    ctx = context_check(build)
    proj = projection(build)
    pred, clf = build["prediction"], build["classifier"]

    print(f"=== Stage 2 pilot: projection ===   {PILOT_BANNER}")
    print(f"  dev subjects            6 ({pred['n_subjects']} Q-A capable; "
          f"burned_for_qa {', '.join(pred['excluded_burned_for_qa'])} excluded "
          "from every prediction arm)")
    print(f"  Q-A items               {pred['n_items']}")
    print(f"  prediction prompts      {pred['n_items']} items x {len(ARMS)} arms "
          f"x {len(VARIANTS)} variants = "
          f"{pred['n_items'] * len(ARMS) * len(VARIANTS)}")
    print(f"  classifier prompts      {len(clf['cases'])} model cases "
          f"(+ {len(clf['rule_labels'])} rule-labelled, no model call)")
    print(f"  longest prompt          {ctx['longest_prompt_words']} words "
          f"-> up to {ctx['worst_case_tokens_needed']} tokens; "
          f"max-model-len {ctx['max_model_len']} "
          f"(headroom {ctx['headroom_tokens']})")
    print(f"  throughput              {proj['measured_tokens_per_second']:.0f} "
          f"tok/s measured / {proj['long_prompt_derate']}x de-rate = "
          f"{proj['effective_tokens_per_second']:.0f} tok/s")
    print("  --- node-hours ---")
    for name, job in proj["jobs"].items():
        print(f"  {name:22s} {job['projected_node_hours']:7.4f}  "
              f"({job['n_calls']:,} calls, {job['walltime']} walltime)")
    print(f"  {'TOTAL':22s} {proj['total_projected_node_hours']:7.4f}  "
          f"(abort above {PROJECTION_ABORT_NODE_HOURS}; brief's cap "
          f"{BUDGET_NODE_HOURS})")
    print(f"  walltime-bounded worst case {proj['walltime_bounded_worst_case_node_hours']} "
          "node-hours if both jobs run to their limit")
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal(f"projection {proj['total_projected_node_hours']} exceeds "
                    f"{PROJECTION_ABORT_NODE_HOURS} node-hours -- STOP and "
                    "report BLOCKED rather than submitting")
    return 0


# ---------------------------------------------------------------------------
# sbatch + manifest
# ---------------------------------------------------------------------------


HEADER = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition=boost_usr_prod
#SBATCH --account={account}
{qos_line}#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time={walltime}
#SBATCH --output={node_root}/logs/%x-%j.out
#
# Stage 2 PILOT -- {title}
# {banner}
# Projected {hours:.4f} node-hours. One engine init; every prompt file runs
# through it in sequence. Re-submitting skips any file that already has output.
set -euo pipefail
D={node_root}
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "{out}"
echo "[{name}] node=$(hostname) start=$(date -u +%FT%TZ)"
"""

FOOTER = '\necho "[{name}] DONE $(date -u +%FT%TZ)"\n'


def _pairs_loop(names: list[str]) -> str:
    listed = " ".join(f'"{n}"' for n in names)
    return f"""
ARGS=()
for f in {listed}; do
  P="{NODE_RUN}/prompts_$f.jsonl"
  O="{NODE_RUN}/completions_$f.jsonl"
  if [[ -f "$O.summary.json" ]]; then
    echo "[skip] $f already complete"
  else
    ARGS+=(--prompts "$P" --out "$O")
  fi
done
if [[ ${{#ARGS[@]}} -eq 0 ]]; then
  echo "all prompt files complete; nothing to do."
  exit 0
fi
python jobs/batch_generate.py \\
    --model-dir "{MODEL}" --tp {TP} --max-model-len {MAX_MODEL_LEN} \\
    --gpu-mem-util {GPU_MEM_UTIL} --temperature {TEMPERATURE} \\
    "${{ARGS[@]}}"
"""


def full_set_names() -> list[str]:
    return [set_name(a, v) for a in ARMS for v in VARIANTS] + ["classify"]


def smoke_sbatch(hours: float) -> str:
    head = HEADER.format(
        job_name="dop-s2pilot-smoke", account=ACCOUNT,
        qos_line=f"#SBATCH --qos={SMOKE_QOS}\n",
        walltime=SMOKE_WALLTIME, node_root=NODE_ROOT,
        title="smoke slice spanning every prompt set (debug QOS)",
        banner=PILOT_BANNER, hours=hours, name="stage2_pilot_smoke",
        out=NODE_RUN)
    return head + _pairs_loop(["smoke"]) + FOOTER.format(
        name="stage2_pilot_smoke")


def full_sbatch(hours: float) -> str:
    head = HEADER.format(
        job_name="dop-s2pilot-full", account=ACCOUNT, qos_line="",
        walltime=FULL_WALLTIME, node_root=NODE_ROOT,
        title="all 10 prediction sets + the follow-up classifier",
        banner=PILOT_BANNER, hours=hours, name="stage2_pilot_full",
        out=NODE_RUN)
    return head + _pairs_loop(full_set_names()) + FOOTER.format(
        name="stage2_pilot_full")


def load_manifest(path=MANIFEST) -> dict:
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "created_utc": now(),
        "run": "Stage 2 pilot (SPEC D10)",
        "confirmatory": False,
        "pilot": PILOT_BANNER,
        "contract": "SPEC.md v1.7",
        "jobs": {}, "anomalies": [], "notes": [],
    }


def save_manifest(man: dict, path=MANIFEST) -> None:
    man["updated_utc"] = now()
    S.write_json(path, man)


def cmd_bootstrap(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    manifest_path = pilot_dir / "manifest.json"
    export_manifest = pilot_dir / "exports/export_manifest.json"
    if not export_manifest.exists():
        raise fatal(f"{export_manifest} not found; run export first")
    doc = json.loads(export_manifest.read_text(encoding="utf-8"))
    proj = doc["projection"]
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal(f"projection {proj['total_projected_node_hours']} exceeds "
                    f"{PROJECTION_ABORT_NODE_HOURS} node-hours; not writing "
                    "sbatch files")

    config = {
        "run": SPLIT_LABEL,
        "pilot": PILOT_BANNER,
        "confirmatory": False,
        "contract": "SPEC.md v1.7 (D1-D10)",
        "model": "Gemma-4-31B-it", "model_label": MODEL_LABEL,
        "temperature": TEMPERATURE, "tp": TP,
        "max_model_len": MAX_MODEL_LEN,
        "max_model_len_note":
            "Stage 1E ran at 2048 and the T6 brief named 4096. Neither fits: "
            f"the longest pilot prompt is {doc['context']['longest_prompt_words']} "
            "words (a 2,000-word grounding block plus C02013's 1,135-word "
            "option block), which needs up to "
            f"{doc['context']['worst_case_tokens_needed']} tokens at the "
            "measured worst-case 2.05 tokens/word. DEVIATION, flagged for "
            "sign-off.",
        "gpu_mem_util": GPU_MEM_UTIL,
        "arms": list(ARMS),
        "option_variants": list(VARIANTS),
        "grounding_budget_words": GROUNDING_BUDGET_WORDS,
        "n_qa_subjects": doc["n_qa_subjects"],
        "n_items": doc["n_items"],
        "excluded_burned_for_qa": doc["excluded_burned_for_qa"],
        "prediction_prompts_total": doc["prediction_prompts_total"],
        "classifier_prompts_total": doc["classifier_prompts_total"],
        "retry_policy":
            "jobs/batch_generate.py has no re-ask mechanism (checked on the "
            "node: it is one vLLM pass per prompt file, no parse hook), so a "
            "parse failure is RECORDED, not retried. SPEC D9's 'up to 2 "
            "re-asks' is unreachable in batch mode; the pilot measures the "
            "resulting parse-failure rate instead.",
        "renderer": doc["renderer"],
        "projection": proj,
        "generated_utc": now(),
    }
    S.write_json(pilot_dir / "config.json", config)

    jobs = {
        "stage2_pilot_smoke": {
            "kind": "smoke", "walltime": SMOKE_WALLTIME, "qos": SMOKE_QOS,
            "files": ["smoke"],
            "text": smoke_sbatch(
                proj["jobs"]["stage2_pilot_smoke"]["projected_node_hours"]),
        },
        "stage2_pilot_full": {
            "kind": "full", "walltime": FULL_WALLTIME, "qos": None,
            "files": full_set_names(),
            "text": full_sbatch(
                proj["jobs"]["stage2_pilot_full"]["projected_node_hours"]),
        },
    }
    man = load_manifest(manifest_path)
    for name, spec in jobs.items():
        path = pilot_dir / f"{name}.sbatch"
        path.write_text(spec.pop("text"), encoding="utf-8")
        entry = man["jobs"].get(name, {})
        entry.update({
            "kind": spec["kind"], "walltime": spec["walltime"],
            "qos": spec["qos"], "prompt_files": spec["files"],
            "sbatch_local": rel(path),
            "sbatch_node": f"{NODE_JOBS}/{name}.sbatch",
            "node_outdir": NODE_RUN,
            "projected_node_hours":
                proj["jobs"][name]["projected_node_hours"],
            "status": entry.get("status", "bootstrapped"),
            "slurm_job_ids": entry.get("slurm_job_ids", []),
            "actual_node_hours": entry.get("actual_node_hours"),
        })
        man["jobs"][name] = entry
        print(f"[bootstrap] {name}: sbatch -> {rel(path)}")
    save_manifest(man, manifest_path)
    print(f"[bootstrap] config -> {pilot_dir / 'config.json'}")
    return 0


def cmd_record(args) -> int:
    man = load_manifest()
    if args.anomaly:
        man["anomalies"].append({"utc": now(), "job": args.name,
                                 "note": args.anomaly})
        print(f"[record] anomaly logged for {args.name}")
    entry = man["jobs"].setdefault(args.name, {})
    if args.job_id:
        entry.setdefault("slurm_job_ids", []).append(args.job_id)
    if args.status:
        entry["status"] = args.status
    if args.node_hours is not None:
        entry["actual_node_hours"] = float(args.node_hours)
    if args.note:
        entry.setdefault("notes", []).append({"utc": now(), "note": args.note})
    save_manifest(man)
    print(f"[record] {args.name}: {entry.get('status')} "
          f"jobs={entry.get('slurm_job_ids')}")
    return 0


# ---------------------------------------------------------------------------
# The thin ssh/rsync/sacct layer (argv construction only; tests monkeypatch run)
# ---------------------------------------------------------------------------


def run(argv: list[str], check: bool = True) -> str:
    """Run a command and return stdout. The single seam tests replace."""
    proc = subprocess.run(argv, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise fatal(f"{' '.join(argv)} failed ({proc.returncode}): "
                    f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def ssh_argv(command: str) -> list[str]:
    return ["ssh", "-o", "BatchMode=yes", REMOTE, command]


def rsync_argv(local: Path, remote_path: str) -> list[str]:
    return ["rsync", "-az", str(local), f"{REMOTE}:{remote_path}"]


def ssh_ok() -> bool:
    return run(ssh_argv("echo ok"), check=False).strip().endswith("ok")


def sacct_argv(job_id: str) -> list[str]:
    return ["ssh", "-o", "BatchMode=yes", REMOTE,
            f"sacct -j {job_id} -X -P -n "
            "--format=JobID,State,Elapsed,AllocNodes,ExitCode"]


def parse_sacct(text: str) -> dict | None:
    """One ``sacct -X -P -n`` line -> ``{job_id, state, elapsed, nodes, hours}``."""
    for line in (text or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) < 5 or not parts[0]:
            continue
        elapsed = parts[2]
        days, _, rest = elapsed.rpartition("-")
        chunks = [int(c) for c in rest.split(":")]
        while len(chunks) < 3:
            chunks.insert(0, 0)
        secs = chunks[0] * 3600 + chunks[1] * 60 + chunks[2]
        if days:
            secs += int(days) * 86400
        nodes = int(parts[3] or 1)
        return {"job_id": parts[0], "state": parts[1], "elapsed": elapsed,
                "alloc_nodes": nodes,
                "node_hours": round(secs * nodes / 3600, 4)}
    return None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_record(meta: dict, completion: str | None) -> dict:
    """One prediction completion -> a scored record."""
    dist = R.parse_distribution(completion, n_options=int(meta["n_options"]))
    correct = int(meta["correct_index"])
    rec = {
        "item_id": meta["item_id"], "canonical_id": meta["canonical_id"],
        "arm": meta["arm"], "variant": meta["variant"],
        "correct_index": correct, "donor_id": meta.get("donor_id"),
        "raw_response": (completion or "")[:600],
        "parse_failure": dist is None,
        "distribution": dist,
        "argmax_index": None, "argmax_correct": None, "prob_mass_correct": None,
    }
    if dist is not None:
        best = max(range(len(dist)), key=lambda i: dist[i])
        rec["argmax_index"] = best
        rec["argmax_correct"] = bool(best == correct)
        rec["prob_mass_correct"] = float(dist[correct])
    return rec


def accuracy(records: list[dict]) -> dict:
    """Argmax accuracy and probability-mass-on-correct over PARSED records.

    Parse failures are excluded from both denominators and reported separately;
    ``n`` is the number of scored records, never the number attempted.
    """
    parsed = [r for r in records if not r["parse_failure"]]
    n = len(parsed)
    return {
        "n_attempted": len(records),
        "n": n,
        "n_parse_failures": len(records) - n,
        "argmax_accuracy": round(sum(1 for r in parsed if r["argmax_correct"])
                                 / n, 6) if n else None,
        "prob_mass_correct": round(sum(r["prob_mass_correct"] for r in parsed)
                                   / n, 6) if n else None,
    }


def adversarial_keep(records: list[dict], variant: str) -> set[str]:
    """Amendment A4.3's filter: drop items the zero-information arm got right.

    Returns the item_ids to KEEP. Computed within one option variant, because
    the entity-stripped re-score is a different forced choice and can flip which
    items the floor arm solves.
    """
    solved = {r["item_id"] for r in records
              if r["arm"] == "zeroinfo_redacted" and r["variant"] == variant
              and not r["parse_failure"] and r["argmax_correct"]}
    everything = {r["item_id"] for r in records if r["variant"] == variant}
    return everything - solved


def contamination_meter(records: list[dict]) -> dict:
    """Per subject: acc(zeroinfo_named) - acc(zeroinfo_redacted), both reads."""
    out: dict[str, dict] = {}
    subjects = sorted({r["canonical_id"] for r in records})
    for cid in subjects:
        entry: dict = {}
        for variant in VARIANTS:
            named = [r for r in records if r["canonical_id"] == cid
                     and r["arm"] == "zeroinfo_named" and r["variant"] == variant]
            plain = [r for r in records if r["canonical_id"] == cid
                     and r["arm"] == "zeroinfo_redacted"
                     and r["variant"] == variant]
            a, b = accuracy(named), accuracy(plain)
            entry[variant] = {
                "zeroinfo_named": a, "zeroinfo_redacted": b,
                "delta_argmax": _sub(a["argmax_accuracy"], b["argmax_accuracy"]),
                "delta_prob_mass": _sub(a["prob_mass_correct"],
                                        b["prob_mass_correct"]),
            }
        out[cid] = entry
    return out


def _sub(a, b):
    if a is None or b is None:
        return None
    return round(a - b, 6)


def paired_lift(records: list[dict], better: str, worse: str,
                variant: str, keep: set[str] | None = None) -> dict:
    """Subject-paired mean difference between two arms. NO significance test.

    With ~17 items over 5 subjects the pilot is not powered for one, and a
    p-value here would invite exactly the reading the pilot must not support.
    """
    per_subject = []
    subjects = sorted({r["canonical_id"] for r in records})
    for cid in subjects:
        def sel(arm: str) -> list[dict]:
            return [r for r in records
                    if r["canonical_id"] == cid and r["arm"] == arm
                    and r["variant"] == variant
                    and (keep is None or r["item_id"] in keep)]
        a, b = accuracy(sel(better)), accuracy(sel(worse))
        if a["n"] == 0 or b["n"] == 0:
            continue
        per_subject.append({
            "canonical_id": cid, "n_better": a["n"], "n_worse": b["n"],
            "argmax_delta": _sub(a["argmax_accuracy"], b["argmax_accuracy"]),
            "prob_mass_delta": _sub(a["prob_mass_correct"],
                                    b["prob_mass_correct"]),
        })
    def mean(field: str):
        vals = [p[field] for p in per_subject if p[field] is not None]
        return round(sum(vals) / len(vals), 6) if vals else None
    return {
        "better_arm": better, "worse_arm": worse, "variant": variant,
        "n_subjects": len(per_subject),
        "mean_argmax_delta": mean("argmax_delta"),
        "mean_prob_mass_delta": mean("prob_mass_delta"),
        "per_subject": per_subject,
        "note": "Subject-paired mean. No significance test: the pilot is not "
                "powered for one.",
    }


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


_WHY_RE = re.compile(r"^[ \t>#*_-]*why[ \t*_]*:[ \t*_`\"']*(.+?)[*_`\"]*[ \t]*$",
                     re.IGNORECASE | re.MULTILINE)


def parse_why(completion: str | None) -> str | None:
    """The rubric's second output line. Presentation only -- never scored."""
    if not completion:
        return None
    hits = _WHY_RE.findall(completion.replace("\r\n", "\n"))
    return hits[0].strip() if len(hits) == 1 else None


def _node_hours(summary: dict | None) -> float | None:
    if not summary:
        return None
    secs = (summary.get("engine_init_seconds", 0.0)
            + summary.get("generation_wall_seconds", 0.0))
    return round(secs / 3600, 4) if secs else None


def cmd_ingest(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    nodedir = Path(args.nodedir)
    records_dir = pilot_dir / "records"
    doc = json.loads((export_dir / "export_manifest.json").read_text(
        encoding="utf-8"))

    all_records: list[dict] = []
    summaries: list[dict] = []
    missing_total = 0
    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            metas = S.read_jsonl(export_dir / f"meta_{name}.jsonl")
            comp_path = nodedir / f"completions_{name}.jsonl"
            comps = {}
            if comp_path.exists():
                comps = {int(r["idx"]): r for r in S.read_jsonl(comp_path)}
                side = nodedir / f"completions_{name}.jsonl.summary.json"
                if side.exists():
                    summaries.append(json.loads(side.read_text()))
            else:
                print(f"[warn] no completions for {name}", file=sys.stderr)
            rows = []
            for meta in metas:
                comp = comps.get(int(meta["idx"]))
                if comp is None:
                    missing_total += 1
                rec = score_record(meta, comp.get("text") if comp else None)
                rec.update({
                    "idx": int(meta["idx"]),
                    "tokens_in": int((comp or {}).get("tokens_in", 0) or 0),
                    "tokens_out": int((comp or {}).get("tokens_out", 0) or 0),
                    "missing_completion": comp is None,
                })
                rows.append(rec)
            S.write_jsonl(records_dir / f"{name}.jsonl", rows)
            all_records += rows
            print(f"[ingest] {name}: {len(rows)} records, "
                  f"{sum(1 for r in rows if r['parse_failure'])} parse failures")

    # --- classifier ----------------------------------------------------------
    clf_metas = S.read_jsonl(export_dir / "meta_classify.jsonl")
    comp_path = nodedir / "completions_classify.jsonl"
    comps = {}
    if comp_path.exists():
        comps = {int(r["idx"]): r for r in S.read_jsonl(comp_path)}
        side = nodedir / "completions_classify.jsonl.summary.json"
        if side.exists():
            summaries.append(json.loads(side.read_text()))
    else:
        print("[warn] no completions for classify", file=sys.stderr)
    clf_rows = []
    for meta in clf_metas:
        comp = comps.get(int(meta["idx"]))
        text = comp.get("text") if comp else None
        label = F.parse_label(text)
        clf_rows.append({
            "idx": int(meta["idx"]),
            "canonical_id": meta["canonical_id"],
            "transcript_id": meta["transcript_id"],
            "turn_idx": meta["turn_idx"],
            "target_host": meta.get("target_host"),
            "label": label, "source": "model",
            "why": parse_why(text),
            "parse_failure": label is None,
            "raw_response": (text or "")[:600],
            "tokens_in": int((comp or {}).get("tokens_in", 0) or 0),
            "tokens_out": int((comp or {}).get("tokens_out", 0) or 0),
            "missing_completion": comp is None,
        })
    rule_rows = S.read_jsonl(export_dir / "labels_rule.jsonl")
    S.write_jsonl(records_dir / "classify.jsonl", clf_rows + rule_rows)
    print(f"[ingest] classify: {len(clf_rows)} model + {len(rule_rows)} rule "
          f"labels, {sum(1 for r in clf_rows if r['parse_failure'])} parse "
          "failures")

    # Billed node-hours come from sacct (elapsed x allocated nodes), recorded
    # into the manifest by `record --node-hours`. A Booster node is billed
    # whole, so sacct is the truth and batch_generate's own wall-clock is only
    # a cross-check -- it misses queue-side overhead and teardown.
    man = load_manifest(pilot_dir / "manifest.json")
    # Only the FULL job produced these records. The smoke slice spent real node
    # time too, but it gets its own ledger line below -- folding it in here as
    # well would bill it twice.
    full_billed = (man.get("jobs", {}).get("stage2_pilot_full", {})
                   .get("actual_node_hours"))
    measured = _sum_node_hours(summaries)
    node_hours = float(full_billed) if full_billed is not None else measured
    billed = full_billed is not None
    if billed and measured:
        print(f"[ingest] node-hours: {node_hours} billed (sacct) vs "
              f"{measured} in-process (batch_generate summaries)")
    analysis = analyse(all_records, clf_rows, rule_rows, doc, node_hours,
                       missing_total, summaries)
    analysis["node_hours_source"] = "sacct" if billed else "batch_generate"
    analysis["node_hours_in_process"] = measured
    analysis["jobs"] = {k: {kk: vv for kk, vv in v.items() if kk != "text"}
                        for k, v in man.get("jobs", {}).items()}
    S.write_json(pilot_dir / "analysis.json", analysis)
    print(f"[ingest] analysis -> {pilot_dir / 'analysis.json'}")

    if node_hours:
        _log_cost(all_records, clf_rows, node_hours)
    # The smoke slice spent real node time and produced no scientific output,
    # so it gets its own ledger line rather than being folded into the arms.
    smoke = man.get("jobs", {}).get("stage2_pilot_smoke", {})
    if smoke.get("actual_node_hours"):
        append_cost_log(build_cost_entry(
            run_id="stage2_pilot/smoke", model=MODEL_LABEL, split=SPLIT_LABEL,
            variant="stage2_smoke", n_persons=0,
            n_calls=SMOKE_PER_SET * len(ARMS) * len(VARIANTS) + SMOKE_CLASSIFY,
            n_retries=0, n_parse_failures=0, tokens_in=0, tokens_out=0,
            backend="leonardo-batch",
            node_hours=float(smoke["actual_node_hours"]),
        ), RESULTS_DIR / "cost_log.jsonl")
        print(f"[cost] smoke: {smoke['actual_node_hours']} node-hours "
              f"(jobs {smoke.get('slurm_job_ids')}), $0.00 API")
    else:
        print("[cost] no node summaries found; no cost-log line written "
              "(entries are only written when node time was actually spent)")
    return 0


def _sum_node_hours(summaries: list[dict]) -> float | None:
    if not summaries:
        return None
    init = max((s.get("engine_init_seconds", 0.0) for s in summaries),
               default=0.0)
    gen = sum(s.get("generation_wall_seconds", 0.0) for s in summaries)
    total = init + gen
    return round(total / 3600, 4) if total else None


def _log_cost(pred: list[dict], clf: list[dict], node_hours: float) -> None:
    total_out = sum(r["tokens_out"] for r in pred + clf) or 1
    for label, rows in (("prediction", pred), ("classifier", clf)):
        share = sum(r["tokens_out"] for r in rows) / total_out
        append_cost_log(build_cost_entry(
            run_id=f"stage2_pilot/{label}", model=MODEL_LABEL,
            split=SPLIT_LABEL, variant="stage2_d8" if label == "prediction"
            else "stage2_d9",
            n_persons=len({r["canonical_id"] for r in rows}),
            n_calls=len(rows), n_retries=0,
            n_parse_failures=sum(1 for r in rows if r["parse_failure"]),
            tokens_in=sum(r["tokens_in"] for r in rows),
            tokens_out=sum(r["tokens_out"] for r in rows),
            backend="leonardo-batch",
            node_hours=round(node_hours * share, 4),
        ), RESULTS_DIR / "cost_log.jsonl")
        print(f"[cost] {label}: {round(node_hours * share, 4)} node-hours, "
              f"{len(rows):,} calls, $0.00 API")


def analyse(pred: list[dict], clf: list[dict], rule: list[dict],
            export_doc: dict, node_hours: float | None, missing: int,
            summaries: list[dict]) -> dict:
    out: dict = {
        "pilot": PILOT_BANNER, "confirmatory": False,
        "generated_utc": now(),
        "n_items": export_doc["n_items"],
        "n_qa_subjects": export_doc["n_qa_subjects"],
        "excluded_burned_for_qa": export_doc["excluded_burned_for_qa"],
        "n_missing_completions": missing,
        "node_hours_total": node_hours,
        "node_summaries": summaries,
        "accuracy": {}, "lift": {}, "contamination_meter": {},
        "classifier": {}, "per_subject_cost": {}, "parse_failures": {},
    }
    for variant in VARIANTS:
        keep = adversarial_keep(pred, variant)
        out["accuracy"][variant] = {}
        for filt, items in (("unfiltered", None), ("adversarial_filtered", keep)):
            block = {}
            for arm in ARMS:
                rows = [r for r in pred if r["arm"] == arm
                        and r["variant"] == variant
                        and (items is None or r["item_id"] in items)]
                block[arm] = accuracy(rows)
            out["accuracy"][variant][filt] = block
        out["accuracy"][variant]["adversarial_filter"] = {
            "rule": "A4.3: drop items zeroinfo_redacted got argmax-correct",
            "n_items_kept": len(keep),
            "items_kept": sorted(keep),
        }
        out["lift"][variant] = {
            "unfiltered": [
                paired_lift(pred, "twin_redacted", "zeroinfo_redacted", variant),
                paired_lift(pred, "twin_redacted", "imposter_redacted", variant),
            ],
            "adversarial_filtered": [
                paired_lift(pred, "twin_redacted", "zeroinfo_redacted", variant,
                            keep),
                paired_lift(pred, "twin_redacted", "imposter_redacted", variant,
                            keep),
            ],
        }
    out["contamination_meter"] = contamination_meter(pred)

    # Parse-failure rate per prompt set, the number the no-retry policy makes
    # the pilot responsible for reporting.
    for arm in ARMS:
        for variant in VARIANTS:
            rows = [r for r in pred if r["arm"] == arm
                    and r["variant"] == variant]
            fails = sum(1 for r in rows if r["parse_failure"])
            out["parse_failures"][set_name(arm, variant)] = {
                "n_attempted": len(rows), "n_parse_failures": fails,
                "rate": round(fails / len(rows), 6) if rows else None}
    clf_fails = sum(1 for r in clf if r["parse_failure"])
    out["parse_failures"]["classify"] = {
        "n_attempted": len(clf), "n_parse_failures": clf_fails,
        "rate": round(clf_fails / len(clf), 6) if clf else None}

    by_subject: dict[str, dict] = {}
    for row in clf:
        entry = by_subject.setdefault(row["canonical_id"],
                                      {"FOLLOW-UP": 0, "NEW-TOPIC": 0,
                                       "parse_failures": 0, "rule": 0})
        if row["label"] is None:
            entry["parse_failures"] += 1
        else:
            entry[row["label"]] += 1
    for row in rule:
        entry = by_subject.setdefault(row["canonical_id"],
                                      {"FOLLOW-UP": 0, "NEW-TOPIC": 0,
                                       "parse_failures": 0, "rule": 0})
        entry["rule"] += 1
    n_clf = len(clf)
    out["classifier"] = {
        "rubric_sha256": export_doc["renderer"]["followup_rubric_sha256"],
        "n_model_cases": n_clf,
        "n_rule_labels": len(rule),
        "parse_failures": sum(1 for r in clf if r["parse_failure"]),
        "parse_failure_rate": round(
            sum(1 for r in clf if r["parse_failure"]) / n_clf, 6)
        if n_clf else None,
        "per_subject": by_subject,
        "sample": classifier_sample(clf),
    }

    total_out = sum(r["tokens_out"] for r in pred + clf) or 1
    for cid in sorted({r["canonical_id"] for r in pred + clf}):
        rows = [r for r in pred + clf if r["canonical_id"] == cid]
        share = sum(r["tokens_out"] for r in rows) / total_out
        out["per_subject_cost"][cid] = {
            "n_calls": len(rows),
            "tokens_in": sum(r["tokens_in"] for r in rows),
            "tokens_out": sum(r["tokens_out"] for r in rows),
            "node_seconds_share": round((node_hours or 0.0) * 3600 * share, 1),
            "cost_usd": 0.0,
        }
    out["total_cost"] = {
        "node_hours": node_hours, "cost_usd": 0.0,
        "n_calls": len(pred) + len(clf),
        "api_calls": 0,
    }
    return out


def classifier_sample(clf: list[dict], n_each: int = 10) -> list[dict]:
    """A seeded 10/10 sample spanning as many subjects as the data allows."""
    rng = random.Random(SAMPLE_SEED)
    picked: list[dict] = []
    for label in (F.FOLLOW_UP, F.NEW_TOPIC):
        pool = sorted([r for r in clf if r["label"] == label],
                      key=lambda r: (r["canonical_id"], r["transcript_id"],
                                     r["turn_idx"]))
        rng.shuffle(pool)
        # Spread across subjects first, then fill.
        seen: set[str] = set()
        chosen: list[dict] = []
        for row in pool:
            if row["canonical_id"] not in seen:
                seen.add(row["canonical_id"])
                chosen.append(row)
            if len(chosen) >= n_each:
                break
        for row in pool:
            if len(chosen) >= n_each:
                break
            if row not in chosen:
                chosen.append(row)
        picked += chosen
    return [{"canonical_id": r["canonical_id"],
             "transcript_id": r["transcript_id"], "turn_idx": r["turn_idx"],
             "label": r["label"], "why": r.get("why"),
             "target_host": r.get("target_host"),
             "raw_response": r["raw_response"][:300]}
            for r in picked]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join("" if c is None else str(c)
                                     for c in row) + " |")
    return "\n".join(out)


def _cell(text, limit: int) -> str:
    """One markdown table cell: whitespace collapsed, pipes escaped, clipped."""
    flat = " ".join((text or "").split())
    if len(flat) > limit:
        flat = flat[:limit].rstrip() + "…"
    return flat.replace("|", "\\|") or "—"


def _fmt(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def _first_lines(text: str, n: int) -> str:
    lines = text.split("\n")
    if len(lines) <= n:
        return text
    return "\n".join(lines[:n]) + f"\n\n[... truncated, {len(lines) - n} more lines ...]"


def _load_prompt(export_dir: Path, name: str, idx: int) -> str:
    for row in S.read_jsonl(export_dir / f"prompts_{name}.jsonl"):
        if int(row["idx"]) == idx:
            return row["prompt"]
    raise fatal(f"{name} has no idx {idx}")


def cmd_report(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    analysis = json.loads((pilot_dir / "analysis.json").read_text(
        encoding="utf-8"))
    export_doc = json.loads(
        (export_dir / "export_manifest.json").read_text(encoding="utf-8"))
    man = load_manifest(pilot_dir / "manifest.json")
    dev = S.load_dev_subjects(pilot_dir)

    P = []                                     # report parts
    P += [
        "# Stage 2 pilot report",
        "",
        f"# {PILOT_BANNER}",
        "",
        f"**{PILOT_BANNER}** Every number below is a pipeline-validation number "
        "on six development subjects. Stage 1 and this pilot are for development "
        "and tuning only; nothing here answers a pre-registered bar, nothing "
        "here is confirmatory, and no result in it should be quoted as a "
        "finding about twins.",
        "",
        f"Generated {analysis['generated_utc']}. Contract: SPEC.md v1.7 (D1-D10). "
        f"Model {MODEL_LABEL}, temperature {TEMPERATURE}, tp {TP}, "
        f"max-model-len {MAX_MODEL_LEN}. "
        f"{analysis['total_cost']['n_calls']} model calls, "
        f"{analysis['total_cost']['api_calls']} API calls, $0.00.",
        "",
    ]

    # ---- 1. dev subjects ---------------------------------------------------
    P += ["## 1. Dev subjects, how they were drawn, and the C00292 story", "",
          _table(["canonical_id", "name", "wiki_status", "shuffle_pos",
                  "burned_for_qa", "Q-A items", "imposter donor"],
                 [[s["canonical_id"], s["canonical_name"], s["wiki_status"],
                   s["shuffle_pos"], "**yes**" if s.get("burned_for_qa") else "",
                   export_doc["per_subject"].get(s["canonical_id"], {})
                   .get("n_items", "— (excluded)"),
                   export_doc["per_subject"].get(s["canonical_id"], {})
                   .get("donor_name", "— (unused)")]
                  for s in dev["subjects"]]),
          "",
          "**Draw provenance.** Seed "
          f"{dev['seed']}, drawn {dev['drawn_at']}, "
          f"{dev.get('n_eligible')} eligible pool rows. Rule as frozen in D1:",
          "", f"> {dev['rule']}", ""]
    for rep in dev.get("replacements", []):
        P += [f"**Burn / replacement event.** `{rep['burned_canonical_id']}`, "
              f"mode `{rep['mode']}`, stratum {rep['stratum']}, replaced by / "
              f"joined by `{rep['replaced_by']}`.", "",
              f"> {rep['reason']}", ""]
    P += ["The full burn story — why it produced no Q-A items, what D3.1-r2 and "
          "D3.2 recovered, and why the burn does not flip now that it yields one "
          "item — is finding 8.9. Operationally: **C00292 is excluded from all "
          f"{len(ARMS) * len(VARIANTS)} prediction prompt sets** by filtering on "
          "the `burned_for_qa` annotation (asserted at build, export and verify) "
          "and **is included in the classifier prompts**, where it contributes "
          "more cases than any other subject.", ""]

    # ---- 2. verbatim Q-A items --------------------------------------------
    P += ["## 2. Three Q-A items, verbatim, with their full option sets", "",
          "Straight from T2's committed artifacts. The correct option is marked; "
          "the model never sees the marking, and D6 shuffled the positions with "
          "a seed derived from the item id.", ""]
    show = ["C02124:NPR-12184:2", "C02013:NPR-9480:49", "C02006:NPR-14829:19"]
    items = {}
    for cid in [s["canonical_id"] for s in dev["subjects"]]:
        for item in load_items(cid, pilot_dir):
            items[item["item_id"]] = item
    for item_id in show:
        item = items.get(item_id)
        if item is None:
            continue
        P += [f"### `{item_id}`  ({item['answer_words']} words, "
              f"relaxation rung {item['relax_rung']})", "",
              "**QUESTION**", "", f"> {item['question']}", ""]
        for pos, text in enumerate(item["options"]["standard"]):
            label = OPTION_LABELS_LOCAL[pos]
            kind = "**TRUE ANSWER**" if pos == item["correct_index"] \
                else "distractor"
            P += [f"**{label}.** {kind}", "", f"> {text}", ""]
        P += ["**Entity-stripped variant of the true option (the A4.2 "
              "re-score):**", "",
              f"> {item['options']['stripped'][item['correct_index']]}", ""]

    # ---- 3. rendered prompts ----------------------------------------------
    P += ["## 3. The rendered prompts", "",
          "One `twin_redacted` prompt in full — the primary arm, and the owner "
          "deliverable — then the first 40 lines of one prompt from each other "
          "arm. All five are the SAME item, so the arms differ only by what "
          "D8 says they differ by.", ""]
    ref = "C02124:NPR-12184:2"
    ref_idx = None
    for row in S.read_jsonl(export_dir / "meta_pred_twin_redacted_standard.jsonl"):
        if row["item_id"] == ref:
            ref_idx = int(row["idx"])
    if ref_idx is not None:
        P += [f"### 3.1 `twin_redacted` (PRIMARY), item `{ref}`, standard "
              "options — complete and verbatim", "", "```",
              _load_prompt(export_dir, "pred_twin_redacted_standard", ref_idx),
              "```", ""]
        n = 1
        for arm in ARMS:
            if arm == "twin_redacted":
                continue
            n += 1
            name = set_name(arm, "standard")
            P += [f"### 3.{n} `{arm}`, same item — first 40 lines", "", "```",
                  _first_lines(_load_prompt(export_dir, name, ref_idx), 40),
                  "```", ""]

    # ---- 4. classifier ------------------------------------------------------
    clf = analysis["classifier"]
    P += ["## 4. The follow-up classifier", "",
          f"Rubric `RUBRIC_V1`, sha256 `{clf['rubric_sha256']}`, frozen and "
          "pinned by a test. **The classifier prompts are deliberately not "
          "redacted** — rationale in finding 8.10.", "",
          f"{clf['n_model_cases']} model cases and {clf['n_rule_labels']} "
          "rule-labelled turns (a host turn with no guest answer anywhere behind "
          "it is NEW-TOPIC by definition and costs no model call). "
          f"Parse-failure rate **{_fmt(clf['parse_failure_rate'], 4)}**.", "",
          "### 4.1 The rubric, verbatim", "", "```", F.RUBRIC_V1, "```", "",
          "### 4.2 Per-subject label counts", "",
          _table(["subject", "FOLLOW-UP", "NEW-TOPIC", "parse failures",
                  "rule labels (NEW-TOPIC)"],
                 [[cid, v["FOLLOW-UP"], v["NEW-TOPIC"], v["parse_failures"],
                   v["rule"]]
                  for cid, v in sorted(clf["per_subject"].items())]), ""]
    sample = clf.get("sample") or []
    if sample:
        P += [f"### 4.3 {len(sample)} sampled classifications "
              f"(seeded, seed {SAMPLE_SEED}; spread across subjects first)", "",
              _table(["subject", "transcript", "turn", "label",
                      "target turn (truncated)", "model's WHY"],
                     [[s["canonical_id"], s["transcript_id"], s["turn_idx"],
                       s["label"],
                       _cell(s.get("target_host"), 150),
                       _cell(s.get("why"), 160)]
                      for s in sample]),
              "",
              f"Subjects represented: "
              f"{len({s['canonical_id'] for s in sample})}.", ""]

    # ---- 5. accuracy --------------------------------------------------------
    zi = analysis["accuracy"]["standard"]["unfiltered"]["zeroinfo_redacted"]
    ceiling = (zi["argmax_accuracy"] is not None
               and zi["argmax_accuracy"] >= 0.999)
    P += ["## 5. Accuracy per arm", ""]
    if ceiling:
        P += ["> **STOP — read finding 8.0 before reading these tables.** The "
              "zero-information baseline scored "
              f"**{_fmt(zi['argmax_accuracy'])} argmax accuracy**: a prompt "
              "with no excerpts, no name, no programme and no date got every "
              "item right. The item set is at ceiling, so the twin arms have "
              "nowhere to go, twin−zeroinfo lift is 0.00 by construction, and "
              "A4.3's filter empties every filtered cell. **These numbers say "
              "nothing about twin fidelity — they say the distractors are too "
              "easy.**", ""]
    P += ["**Read every twin number against its zero-information baseline.** "
          "That is the project's standing rule and on this pilot it is the whole "
          "story, not a formality — see findings 8.0, 8.1 and 8.5. `N` counts "
          "records that PARSED; parse failures are excluded from both "
          "denominators and reported separately in 8.12.", ""]
    for variant in VARIANTS:
        label = ("standard options" if variant == "standard"
                 else "entity-stripped options (A4.2)")
        for filt in ("unfiltered", "adversarial_filtered"):
            block = analysis["accuracy"][variant][filt]
            filt_label = ("unfiltered" if filt == "unfiltered"
                          else "adversarial-filtered (A4.3)")
            P += [f"### {label}, {filt_label}", ""]
            if filt != "unfiltered":
                info = analysis["accuracy"][variant]["adversarial_filter"]
                P += [f"Filter: {info['rule']}. "
                      f"**{info['n_items_kept']} of {analysis['n_items']} items "
                      "survive.**", ""]
                if info["n_items_kept"] == 0:
                    P += ["The zero-information arm solved every item, so the "
                          "filter removes every item and there is nothing left "
                          "to score. The empty table below is the correct "
                          "output of a filter that is working; see finding "
                          "8.0.", ""]
            P += [_table(["arm", "N scored", "parse fails", "argmax accuracy",
                          "prob-mass on correct"],
                         [[("**" + arm + "**" if arm == "twin_redacted" else arm),
                           block[arm]["n"], block[arm]["n_parse_failures"],
                           _fmt(block[arm]["argmax_accuracy"]),
                           _fmt(block[arm]["prob_mass_correct"])]
                          for arm in ARMS]), ""]
        P += [f"#### Lift rows ({label})", "",
              "Subject-paired mean differences. **No significance test, "
              "deliberately** — with "
              f"{analysis['n_items']} items over {analysis['n_qa_subjects']} "
              "subjects (one of them contributing a single item) the pilot is "
              "not powered for one, and a p-value here would invite exactly the "
              "reading this pilot cannot support. See finding 8.8.", ""]
        for filt in ("unfiltered", "adversarial_filtered"):
            P += [f"*{filt.replace('_', ' ')}*", "",
                  _table(["contrast", "subjects paired", "mean argmax delta",
                          "mean prob-mass delta"],
                         [[f"{l['better_arm']} − {l['worse_arm']}",
                           l["n_subjects"], _fmt(l["mean_argmax_delta"]),
                           _fmt(l["mean_prob_mass_delta"])]
                          for l in analysis["lift"][variant][filt]]), ""]

    # ---- 6. contamination meter --------------------------------------------
    P += ["## 6. Contamination meter", "",
          "`accuracy(zeroinfo_named) − accuracy(zeroinfo_redacted)`, per "
          "subject. The two prompts differ by exactly one line (the name), so "
          "this is a one-factor measurement of what the model already knows "
          "about the named person with no excerpts at all. Given finding 8.1 it "
          "is the number that bounds how much of any twin score could be "
          "identity rather than evidence.", ""]
    for variant in VARIANTS:
        P += [f"### {variant} options", "",
              _table(["subject", "zeroinfo_named argmax",
                      "zeroinfo_redacted argmax", "**delta argmax**",
                      "delta prob-mass"],
                     [[cid,
                       _fmt(v[variant]["zeroinfo_named"]["argmax_accuracy"]),
                       _fmt(v[variant]["zeroinfo_redacted"]["argmax_accuracy"]),
                       "**" + _fmt(v[variant]["delta_argmax"]) + "**",
                       _fmt(v[variant]["delta_prob_mass"])]
                      for cid, v in
                      sorted(analysis["contamination_meter"].items())]), ""]

    # ---- 7. cost ------------------------------------------------------------
    P += ["## 7. Cost", "",
          _table(["subject", "model calls", "tokens in", "tokens out",
                  "node-seconds (share)", "$"],
                 [[cid, v["n_calls"], f"{v['tokens_in']:,}",
                   f"{v['tokens_out']:,}", v["node_seconds_share"], "0.00"]
                  for cid, v in
                  sorted(analysis["per_subject_cost"].items())]),
          "",
          f"**Total: {analysis['total_cost']['node_hours']} node-hours, "
          f"{analysis['total_cost']['n_calls']} model calls, "
          f"{analysis['total_cost']['api_calls']} API calls, $0.00.** "
          "Node-seconds are apportioned by each subject's share of output "
          "tokens in the shared job; the jobs shared one engine init.", ""]
    jobs_rows = [[name, e.get("slurm_job_ids"), e.get("status"),
                  e.get("projected_node_hours"), e.get("actual_node_hours")]
                 for name, e in sorted(man.get("jobs", {}).items())]
    P += [_table(["job", "slurm id", "status", "projected node-hours",
                  "actual node-hours (sacct)"], jobs_rows), ""]

    # ---- 8. findings --------------------------------------------------------
    P += ["## 8. Findings for bar-lock", FINDINGS.rstrip(), "",
          "### 8.12 Parse-failure rate per prompt set", "",
          "`jobs/batch_generate.py` has no re-ask path — it is one vLLM pass per "
          "prompt file with no parse hook — so SPEC D9's 'up to 2 re-asks' is "
          "unreachable in batch mode and a parse failure is RECORDED, not "
          "retried. There are no duplicate `idx` rows anywhere in the export. "
          "These are the rates that policy produced.", "",
          _table(["prompt set", "attempted", "parse failures", "rate"],
                 [[name, v["n_attempted"], v["n_parse_failures"],
                   _fmt(v["rate"], 4)]
                  for name, v in analysis["parse_failures"].items()]), ""]

    # ---- 9. provenance ------------------------------------------------------
    P += ["## 9. Provenance", "",
          _table(["what", "value"],
                 [["contract", "SPEC.md v1.7 (D1-D10)"],
                  ["D8 template sha256",
                   "`" + export_doc["renderer"]["stage2_render_template_sha256"]
                   + "`"],
                  ["D9 rubric sha256",
                   "`" + export_doc["renderer"]["followup_rubric_sha256"] + "`"],
                  ["stage2_render.py sha256",
                   "`" + export_doc["renderer"]["stage2_render_file_sha256"]
                   + "`"],
                  ["followup_render.py sha256",
                   "`" + export_doc["renderer"]["followup_render_file_sha256"]
                   + "`"],
                  ["model", MODEL_LABEL],
                  ["node config",
                   f"1 node, 4x A100, tp={TP}, max-model-len={MAX_MODEL_LEN}, "
                   f"gpu-mem-util={GPU_MEM_UTIL}, temperature={TEMPERATURE}, "
                   "one engine init per job"],
                  ["grounding budget",
                   f"{GROUNDING_BUDGET_WORDS} words (SPEC D8 B_pilot)"],
                  ["exported", export_doc["exported_utc"]],
                  ["driver commit", _git_head()]]),
          "", "### Export manifest digests", "",
          _table(["file", "prompts", "sha256"],
                 [[info.get("prompts_file") or info["meta_file"],
                   info.get("n_prompts", "—"),
                   "`" + (info.get("prompts_sha256") or info["meta_sha256"])
                   + "`"]
                  for _, info in sorted(export_doc["files"].items())]),
          "",
          "Every prompt in this run is reproducible from the committed "
          "`exports/` files; `uv run python experiments/stage2_pilot.py verify` "
          "re-checks all of the above against the prompts on disk.", ""]

    path = pilot_dir / "PILOT_REPORT.md"
    path.write_text("\n".join(P) + "\n", encoding="utf-8")
    print(f"[report] -> {path}")
    return 0


OPTION_LABELS_LOCAL = R.OPTION_LABELS


def _git_head() -> str:
    try:
        out = subprocess.run(["git", "-C", str(_ROOT), "rev-parse", "--short",
                              "HEAD"], capture_output=True, text=True)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"



# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot-dir", default=None,
                    help="override results/stage2_pilot (tests only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    p_exp = sub.add_parser("export")
    p_exp.add_argument("--force", action="store_true")
    p_exp.set_defaults(fn=cmd_export)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--name", required=True)
    p_rec.add_argument("--job-id", default=None)
    p_rec.add_argument("--status", default=None)
    p_rec.add_argument("--node-hours", type=float, default=None)
    p_rec.add_argument("--note", default=None)
    p_rec.add_argument("--anomaly", default=None)
    p_rec.set_defaults(fn=cmd_record)

    p_in = sub.add_parser("ingest")
    p_in.add_argument("--nodedir", required=True)
    p_in.set_defaults(fn=cmd_ingest)

    sub.add_parser("report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
