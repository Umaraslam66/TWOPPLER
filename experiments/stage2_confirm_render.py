"""Stage 2 CONFIRMATORY render: H1's five arms + H7's staleness renders.

CONFIRMATORY. This is not a pilot. Everything here renders prompts for the
subjects drawn by ``experiments/stage2_confirm_draw.py`` (seed 20260728) and
built by ``experiments/stage2_confirm_build.py``. It renders and it STOPS: no
API call, no GPU submission, no generation, no sbatch. CPU only, $0.00.

Binding documents, in force and quoted where they are applied:

- ``STAGE2_LAUNCH_PLAN.md`` section b -- the five arms, the frozen rules list,
  the H1+H7 single generation plan.
- ``PREREGISTRATION_AMENDMENT_2.md`` B7 -- H7's design: cutoffs, the Delta
  definition, and the B7.3 volume control.
- ``PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`` item 6 -- the four frozen
  Delta bins, between-subject primary, within-subject sweep as a supporting
  analysis on subjects that fill >= 3 bins.

What this file does NOT do: invent renderer behaviour. Every prompt is built
by :func:`stage2_oe1.render_and_guard_open`, i.e. the exact call OE-1 made,
against the same :mod:`doppler.oe_render` template, the same 2,000-word
grounding budget, the same S1 scope (frozen extension in force), the same
guard set, the same generation config (temperature 0.0, max_output_tokens
256, 150-word instruction tail). The only new machinery in this file is
(a) the D7 donor match for confirmatory subjects and (b) the H7 cutoff plan,
and both are derived mechanically from the frozen text and LOGGED in the
manifest for review before submission.

Determinism. Re-running writes byte-identical prompt files, node files and
``render_manifest.json``. Every wall-clock field lives in ``render_run.json``,
which is the one artifact that is expected to differ between runs.

Outputs, all under ``results/stage2_confirm/``::

    imposter_pairs_confirm.json   the D7 record for the confirmatory subjects
    donors/<donor_id>/            the matched donors' split + grounding turns
    items_confirm.jsonl           one row per D4 item that survived the guards
    prompts/chunk_NN.jsonl        API-ready prompts (gemini-3.5-flash-lite)
    node/chunk_NN.prompts.jsonl   node prompt files (Gemma-4-31B-it, Leonardo)
    node/chunk_NN.meta.jsonl      the join sidecar for the node files
    render_index.jsonl            every logical render -> (chunk, idx)
    render_manifest.json          the submission manifest (timestamp-free)
    render_run.json               timestamps and runtime, kept out of the above

Run::

    uv run python experiments/stage2_confirm_render.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_oe1 as OE1  # noqa: E402
import stage2_pilot as P1  # noqa: E402

from doppler import counterfactuals4 as C4  # noqa: E402
from doppler import imposter2 as I2  # noqa: E402
from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
DRAW_FILE = RESULTS_DIR / "stage2_confirm_draw_provisional.json"
BUILD_FILE = CONFIRM_DIR / "build_full140.json"

#: Draw positions 1-40 were rendered first, reviewed, and committed; 41-140
#: followed. The split is kept only for reporting -- every rule below is
#: applied identically to all 89 survivors.
TRANCHE_1_LAST_POS = 40
TRANCHE_NAMES = {1: "positions_1_40", 2: "positions_41_140"}
PAIRS_FILE = CONFIRM_DIR / "imposter_pairs_confirm.json"
DONOR_CACHE = _ROOT / "data/stage2_cache/donor_grounding_v1.json"

BANNER = ("CONFIRMATORY. Rendered only; nothing here has been generated, "
          "judged or scored. No GPU submission, no API call, $0.00.")

#: The generation config, imported not restated: same objects OE-1 used.
PRIMARY_MODEL = OE1.PRIMARY_MODEL              # Gemma-4-31B-it, Leonardo
ROBUSTNESS_MODEL = OE1.ROBUSTNESS_MODEL        # gemini-3.5-flash-lite, API
GEN_TEMPERATURE = OE1.GEN_TEMPERATURE          # 0.0
GEN_MAX_OUTPUT_TOKENS = OE.MAX_OUTPUT_TOKENS   # 256
GROUNDING_BUDGET_WORDS = OE.GROUNDING_BUDGET_WORDS  # 2000 == H7's budget B

#: Addendum A item 6's four bins, taken from the dev code rather than retyped:
#: ("6-12m", 183, 365), ("1-2y", 365, 730), ("2-3y", 730, 1095), (">3y", 1095, inf).
DELTA_BINS = OE1.DELTA_BINS
BIN_NAMES = tuple(name for name, _lo, _hi in DELTA_BINS)
delta_bin = OE1.delta_bin

#: The one arm that carries a staleness axis (the dev scorer's OWN_ARM).
H7_TWIN_ARM = "h7_twin_redacted"
#: The crossover comparison's fresh imposter (B7's killer statistic).
H7_IMPOSTER_ARM = "h7_imposter_fresh"

#: B7.1, re-derived here rather than trusted from the draw file.
H7_MIN_CLUSTERS = 4
H7_MIN_SPAN_DAYS = 730

#: Roughly this many prompts per independent per-subject block.
CHUNK_TARGET_PROMPTS = 500

#: A guard-exclusion rate above this is a systematic problem, not an outlier:
#: the run stops and reports instead of shipping a hollow prompt set.
GUARD_EXCLUSION_STOP_RATE = 0.05


# ---------------------------------------------------------------------------
# The rules this file DERIVED. Every one of them is reviewed before submission.
# ---------------------------------------------------------------------------

DERIVED_RULES = [
    {
        "id": "D7-CONF",
        "topic": "Which donors may ground a confirmatory imposter arm",
        "frozen_text": (
            "SPEC_v1.10 D7: 'Donor pool: the same 200-subject bank sample "
            "(their grounding-side text), plus the other 4 dev subjects are "
            "NOT eligible donors (keeps dev arms independent).'"),
        "ambiguity": (
            "The dev code removes the study's own subjects BEFORE drawing the "
            "seed-48 sample; the spec sentence removes them from ELIGIBILITY "
            "after the sample is drawn. On dev the two readings produced the "
            "committed artifact. On confirmatory they differ: 45 of the 200 "
            "banked donors are themselves confirmatory drawn subjects."),
        "choice": (
            "The frozen seed-48 200-id bank is kept EXACTLY as committed "
            "(donor_sample_sha256 asserted equal to "
            "results/stage2_pilot/imposter_pairs.json), and the 6 dev "
            "subjects plus all 140 confirmatory drawn subjects are removed "
            "from ELIGIBILITY, alongside the frozen 2,500-word floor and the "
            "frozen name-conflict exclusion. Removals are counted."),
        "why_this_reading": (
            "It is the spec sentence's own shape, and it is the only reading "
            "that leaves the frozen bank untouched: re-drawing the sample "
            "with 140 more ids removed would produce a different 200 and "
            "retire a sha that is committed in a dev artifact. The research "
            "property the rule exists for -- no study subject grounds another "
            "study subject's imposter arm -- holds identically under both."),
        "impact": "155 of the 200 banked donors remain permitted; 54 clear "
                  "the 2,500-word floor (dev had 70 of 200).",
    },
    {
        "id": "D7-GUARD",
        "topic": "What happens when a D7 winner trips a frozen leakage guard",
        "frozen_text": (
            "SPEC_v1.10 D8 LEAKAGE GUARDS and imposter2's asserts: the subject "
            "and its donor must never have shared a transcript, and the "
            "donor's grounding text must not carry the subject's name."),
        "ambiguity": (
            "On six dev subjects the argmax winner never tripped either "
            "assert, so the frozen machinery has no recorded behaviour for "
            "the case. At 30 confirmatory subjects it fires: C00050's "
            "highest-similarity donor shares broadcast CNN-150694 with them."),
        "choice": (
            "Both conditions become ELIGIBILITY exclusions inside the D7 "
            "argmax, exactly like the frozen name-conflict exclusion: a donor "
            "that would trip either assert is not scored, and the argmax runs "
            "over what is left. The asserts themselves are unchanged, are NOT "
            "relaxed, and still run on the winner -- where they can no longer "
            "fire. Every exclusion is recorded per subject in "
            "imposter_pairs_confirm.json under excluded_by_leakage_guard."),
        "why_this_reading": (
            "The name-conflict exclusion the spec already carries is the same "
            "rule of the same shape -- 'do not pick a donor that would leak "
            "the subject's identity' -- applied before the argmax rather than "
            "after it. The alternative readings are worse: aborting the run "
            "makes the confirmatory imposter arm unbuildable, and waving the "
            "assert through would put the subject's own broadcast inside the "
            "control arm. The unmodified matcher is run alongside and every "
            "subject whose reference winner was not guard-excluded is "
            "asserted to match, so the change is provably confined."),
    },
    {
        "id": "H7-R1",
        "topic": "Test interview and items at every cutoff",
        "frozen_text": (
            "B7.2: 'The test interview stays the subject's chronologically "
            "LAST interview -- the same test set as H1, identical items at "
            "every cutoff.'"),
        "choice": "Test cluster and D4 items are taken unchanged from the "
                  "committed build (D2 chronological split); every filled bin "
                  "renders the same item set.",
        "why_this_reading": "Stated mechanically in B7.2; no judgment needed.",
    },
    {
        "id": "H7-R2",
        "topic": "Which cutoffs T exist",
        "frozen_text": (
            "B7.2: 'A grounding cutoff T restricts grounding to interviews "
            "dated <= T. Staleness Delta = date(test) - date(newest interview "
            "available under T). Delta is swept by moving T.'"),
        "ambiguity": "B7 does not enumerate the cutoffs; T is continuous.",
        "choice": (
            "Candidate cutoffs = the distinct DATES of the subject's D2 "
            "GROUNDING clusters, one candidate per date, with T = that date. "
            "At T = date(g) the newest available interview is g itself, so "
            "Delta(g) = date(test) - date(g)."),
        "why_this_reading": (
            "Both quantities B7 defines -- Delta and the available set -- "
            "change only when T crosses a grounding cluster date, so the "
            "distinct (Delta, available-set) pairs are exactly indexed by "
            "those dates. Any other T duplicates one of them. This is "
            "arithmetic, not a preference."),
    },
    {
        "id": "H7-R3",
        "topic": "The bin of a cutoff",
        "frozen_text": (
            "Addendum A item 6: 'four Delta bins: 6-12 months, 1-2 years, "
            "2-3 years, > 3 years (the < 6-month bin is dropped)'."),
        "choice": (
            "The bin edges are taken byte-for-byte from the dev code "
            "(stage2_oe1.DELTA_BINS, cited there as 'Spec section 9 / "
            "addendum item 6'): 6-12m = [183, 365) days, 1-2y = [365, 730), "
            "2-3y = [730, 1095), >3y = [1095, inf). Delta < 183 days falls in "
            "the dropped <6m band: such a cutoff is NOT rendered and is "
            "counted as dropped_lt_6m."),
        "why_this_reading": "It is the reading the dev code embodies, and it "
                            "is the only numeric expression of item 6 that "
                            "exists in the repository.",
    },
    {
        "id": "H7-R4",
        "topic": "B7.3 volume control -- when a cutoff is unfillable",
        "frozen_text": (
            "B7.3: 'At every T the grounding context is filled to the same "
            "token budget B, newest-first below the cutoff. Only the AGE of "
            "the grounding varies, never the amount. A cutoff at which B "
            "cannot be filled is excluded (counts reported).'"),
        "ambiguity": (
            "'B cannot be filled' is not operationalized, and exchanges are "
            "atomic so a rendered block never lands exactly on B."),
        "choice": (
            "B = 2,000 words = the frozen H1 grounding budget "
            "(stage2_render.GROUNDING_BUDGET_WORDS); there is no other B in "
            "the frozen documents or the code. A cutoff is FILLABLE iff the "
            "total grounding speech words available at that cutoff -- host + "
            "guest words of every exchange in clusters dated <= T, the same "
            "accounting render_grounding budgets against -- is >= B. "
            "Unfillable cutoffs are excluded and counted."),
        "why_this_reading": (
            "It is the only test that can be applied before rendering and "
            "that makes 'the same amount at every T' true rather than "
            "aspirational. The words actually achieved by the greedy fill are "
            "recorded per cutoff so a reviewer can see the realized volume "
            "match; NO extra bar is imposed on that number, because inventing "
            "a fill-ratio threshold would be a new parameter, not a reading."),
        "flag_for_review": (
            "This rule is what excludes most H7 renders in this tranche: a "
            "subject whose entire grounding side is under 2,000 words cannot "
            "fill B at any cutoff and contributes no H7 bin at all. The "
            "counts are in h7.exclusions."),
    },
    {
        "id": "H7-R5",
        "topic": "Which cutoff represents a bin",
        "ambiguity": (
            "Several cutoffs can fall in one bin; the frozen text does not "
            "say which one is rendered, and item 6 speaks of a subject "
            "'filling' a bin, i.e. one render per bin."),
        "choice": "The cutoff with the SMALLEST Delta inside the bin "
                  "(equivalently: the newest grounding cluster whose Delta "
                  "lands in that bin). Ties cannot occur -- one cutoff per "
                  "distinct date.",
        "why_this_reading": (
            "Availability is monotone non-decreasing in T, so the "
            "smallest-Delta cutoff in a bin is fillable whenever ANY cutoff "
            "in that bin is. It is therefore the choice that minimises the "
            "B7.3 exclusion count, which is the thing B7.3 asks to be kept "
            "and reported. That is a mechanical argument, not a taste."),
    },
    {
        "id": "H7-R6",
        "topic": "Which arm gets the staleness sweep",
        "frozen_text": "STAGE2_LAUNCH_PLAN b: 'the staleness renders'; B7.4: "
                       "'the same Stage 2 harness with all Amendment 1 "
                       "controls (A1 arms ...)'.",
        "choice": "twin_redacted only, rendered as arm '" + H7_TWIN_ARM +
                  "'. The named and zero-information arms carry no grounding "
                  "and therefore no staleness axis.",
        "why_this_reading": "twin_redacted is the dev scorer's OWN_ARM and "
                            "the arm the H1 primary contrast is measured on; "
                            "aging an arm that has no grounding is undefined.",
    },
    {
        "id": "H7-R7",
        "topic": "The crossover comparison's fresh imposter",
        "frozen_text": (
            "B7: 'At each Delta bin, the STALE true-person twin is compared "
            "against a FRESH same-domain imposter twin: the A1 imposter "
            "pipeline, grounded on the donor's interviews closest in time to "
            "the test date, same budget B.'"),
        "choice": (
            "The fresh imposter is rendered as arm '" + H7_IMPOSTER_ARM +
            "': the D7 donor's grounding filled newest-first at budget B. "
            "That render is byte-identical to the item's H1 imposter_redacted "
            "prompt; the script ASSERTS the sha equality, emits the prompt "
            "once, and reuses it at every Delta bin of that subject. Both the "
            "logical row count and the unique-prompt count are reported."),
        "why_this_reading": (
            "'The donor's interviews closest in time to the test date' is "
            "exactly what render_grounding's most-recent-first greedy fill "
            "selects, which is the A1 imposter pipeline as the dev code "
            "implements it. The imposter is not aged, so its value is "
            "constant across bins: generating the identical string more than "
            "once at temperature 0 would buy nothing and cost node-hours. "
            "Nothing is dropped -- every logical (item, bin) crossover row is "
            "in render_index.jsonl, pointing at the one prompt."),
    },
    {
        "id": "H7-R8",
        "topic": "H7 eligibility",
        "frozen_text": "B7.1: 'subjects with >= 4 dated interview clusters "
                       "spanning >= 2 years'.",
        "choice": "The GATE is n_dedup_clusters >= 4 AND span_days_dedup >= "
                  "730 from the pool row -- the derivation "
                  "stage2_confirm_draw.py froze. It is cross-checked against a "
                  "second derivation straight from the SUBSTANTIVE cluster "
                  "dates, and every disagreement is logged under "
                  "h7.eligibility.",
        "why_this_reading": "It is the derivation the committed draw embodies "
                            "and the launch plan quotes (98 of 140); 2 years "
                            "is read as 730 days, the same number the 1-2y bin "
                            "edge uses. It is also the more permissive of the "
                            "two, so it cannot drop a subject the stricter "
                            "reading would keep.",
        "flag_for_review": (
            "The two derivations disagree, and the disagreement is material. "
            "n_dedup_clusters counts non-substantive mentions too, so a "
            "subject can be flagged H7-eligible on 28 clusters while owning 3 "
            "usable interviews. Counts and the affected subject list are in "
            "h7.eligibility; nothing was changed on this file's authority."),
    },
    {
        "id": "GUARD-SCOPE",
        "topic": "What a guard failure excludes",
        "choice": (
            "A guard failure on any of the five H1 arms excludes the whole "
            "ITEM (all five arms and all of its H7 renders): the primary "
            "metric is paired own-minus-imposter on one item, so a half-built "
            "item is not scoreable. A guard failure on an H7 cutoff render "
            "excludes that (item, bin) render only. Every exclusion is "
            "counted with its arm and its reason; none passes silently."),
        "why_this_reading": "The pairing is what the metric is; C3 makes "
                            "own-minus-imposter the primary everywhere.",
    },
    {
        "id": "TWIN-RULE-SCOPE",
        "topic": "Where the D6-v4.9 twin rule is asserted",
        "frozen_text": OE1.TWIN_RULE,
        "ambiguity": "H7 shows one question at several cutoffs, so a file "
                     "holding a subject's whole block necessarily repeats it.",
        "choice": (
            "Asserted on the per-(arm, Delta-bin) logical sets, each of which "
            "holds a question at most once -- the same unit OE-1 asserted it "
            "on (its per-arm prompt_<arm>.jsonl sets). The chunk and node "
            "files interleave arms exactly as OE-1's own node file did "
            "(prompts_oe1.jsonl carried each of its 17 items five times)."),
        "why_this_reading": "It is the reading the dev code embodies, and the "
                            "rule's own words bind what a RATER or SCORER "
                            "sees, not what one generation batch contains.",
    },
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def rel(path: Path) -> str:
    return str(Path(path).resolve().relative_to(_ROOT))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def days_between(later: str, earlier: str) -> int | None:
    try:
        return (date.fromisoformat(str(later)[:10])
                - date.fromisoformat(str(earlier)[:10])).days
    except (TypeError, ValueError):
        return None


def git_commit_for(path: Path) -> str | None:
    """The last commit that touched ``path`` (recorded, never trusted blindly)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(_ROOT), "log", "-1", "--format=%H", "--",
             str(Path(path).resolve().relative_to(_ROOT))],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    value = (out.stdout or "").strip()
    return value or None


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


def survivors(build_file: Path = BUILD_FILE) -> list[dict]:
    """Every surviving subject of the committed draw, in draw order.

    Each row is tagged with the build tranche it came from (draw positions
    1-40, then 41-140). The tag is reporting only: the arms, the guards, the
    D7 match and the H7 rules are applied identically to every survivor.
    """
    doc = json.loads(Path(build_file).read_text(encoding="utf-8"))
    rows = [s for s in doc.get("subjects", []) if s.get("survived")]
    rows.sort(key=lambda s: s["draw_pos"])
    if not rows:
        raise fatal(f"{rel(build_file)} lists no survivors")
    if len(rows) != doc.get("n_survived"):
        raise fatal(f"{rel(build_file)}: n_survived={doc.get('n_survived')} "
                    f"but {len(rows)} subject rows say survived")
    for row in rows:
        row["tranche"] = 1 if row["draw_pos"] <= TRANCHE_1_LAST_POS else 2
    return rows


def h7_eligibility(row: dict, draw_flag: bool) -> dict:
    """B7.1 re-derived two ways and compared to the committed draw flag.

    ``pool_derived`` reproduces the committed draw's own rule
    (``stage2_confirm_draw.h7_eligible``): ``n_dedup_clusters >= 4 AND
    span_days_dedup >= 730``. It is the gate this render uses, because it is
    the gate the draw froze and the launch plan quotes (98 of 140).

    ``substantive_derived`` is B7.1 read off the cluster dates themselves, over
    SUBSTANTIVE transcripts only -- the flag-S rows, which are the only ones D2
    ever builds a split from. The two disagree, and the disagreement is the
    point of the cross-check: ``n_dedup_clusters`` counts every dedup cluster
    including non-substantive mentions, so a subject can be flagged H7-eligible
    on 28 clusters while owning 3 interviews the pipeline can actually use.
    ``pool_derived`` is the strictly more permissive of the two, so using it as
    the gate cannot drop a subject the stricter reading would have kept.
    """
    n_clusters = int(row["n_dedup_clusters"])
    span = int(row["span_days_dedup"])
    pool_derived = n_clusters >= H7_MIN_CLUSTERS and span >= H7_MIN_SPAN_DAYS

    by_cluster: dict[str, list[str]] = {}
    for entry in row.get("transcripts", []):
        if entry.get("date") and entry.get("substantive"):
            by_cluster.setdefault(entry["cluster_id"], []).append(entry["date"])
    cluster_dates = sorted(min(v) for v in by_cluster.values() if v)
    n_dated = len(cluster_dates)
    date_span = (days_between(cluster_dates[-1], cluster_dates[0])
                 if len(cluster_dates) >= 2 else 0)
    substantive_derived = (n_dated >= H7_MIN_CLUSTERS
                           and (date_span or 0) >= H7_MIN_SPAN_DAYS)

    return {
        "draw_flag": bool(draw_flag),
        "pool_derived": pool_derived,
        "substantive_derived": substantive_derived,
        "n_dedup_clusters": n_clusters,
        "span_days_dedup": span,
        "n_substantive_dated_clusters": n_dated,
        "span_days_substantive": date_span,
        "agrees_with_draw": pool_derived == bool(draw_flag),
        "derivations_agree": pool_derived == substantive_derived,
    }


# ---------------------------------------------------------------------------
# D7 donors for the confirmatory subjects
# ---------------------------------------------------------------------------


def donor_texts_from_cache(sample: list[str]) -> dict:
    """The banked donors' grounding text, from the committed cache.

    The cache is keyed on the donor sample AND on the bytes of stage2_data.py,
    so a stale entry cannot be served silently; on a miss this raises rather
    than quietly re-deriving, because a corpus re-pass here would be a
    different (and unreviewed) donor side.
    """
    key = hashlib.sha256(
        (I2.sample_sha256(sample) + ":"
         + sha256_file(_ROOT / "src/doppler/stage2_data.py")).encode()
    ).hexdigest()
    doc = json.loads(Path(DONOR_CACHE).read_text(encoding="utf-8"))
    if doc.get("cache_key") != key:
        raise fatal(
            f"{rel(DONOR_CACHE)} was built under different rules or a "
            "different donor sample; re-run experiments/stage2_imposters.py "
            "before rendering rather than re-deriving donors here")
    missing = sorted(set(sample) - set(doc["texts"]))
    if missing:
        raise fatal(f"donor cache is missing {len(missing)} banked donors: "
                    f"{missing[:5]}")
    return doc["texts"]


def _shares_transcript(subject_row: dict, donor_row: dict,
                       subject_split: dict, donor_split: dict) -> str:
    """The co-appearance the frozen leakage guard forbids, as a reason string.

    Same two comparisons ``imposter2.check_no_shared_transcripts`` makes -- the
    raw pool rows and the D2 splits -- read as a predicate instead of an
    assert, so the pair can be excluded before it is chosen rather than after.
    """
    a = {e["transcript_id"] for e in subject_row.get("transcripts", [])}
    b = {e["transcript_id"] for e in donor_row.get("transcripts", [])}
    shared = sorted(a & b)
    if shared:
        return f"shares transcript(s) {shared[:3]}"
    sa = {e["transcript_id"] for e in subject_split["grounding"]}
    sa.add(subject_split["test"]["transcript_id"])
    sb = {e["transcript_id"] for e in donor_split["grounding"]}
    sb.add(donor_split["test"]["transcript_id"])
    overlap = sorted(sa & sb)
    if overlap:
        return f"shares split transcript(s) {overlap[:3]}"
    return ""


def _names_subject(subject_row: dict, donor_tokens: list[str],
                   donor_token_set: set) -> str:
    """``check_no_subject_name_in_text`` as a predicate, same two levels."""
    for key in sorted(I2.name_keys(subject_row)):
        needle = key.split()
        n = len(needle)
        if n and any(donor_tokens[i:i + n] == needle
                     for i in range(len(donor_tokens) - n + 1)):
            return f"donor text carries the subject's full name {key!r}"
    hits = sorted(I2.name_tokens(subject_row) & donor_token_set)
    if hits:
        return f"donor text carries the subject's name token(s) {hits[:3]}"
    return ""


def select_donors(subject_ids: list[str], pool: list[dict], dev_ids: list[str],
                  draw_ids: set[str], out_dir: Path) -> dict:
    """SPEC D7 for the confirmatory subjects. See DERIVED_RULES D7-CONF/D7-GUARD.

    The argmax, the TF-IDF, the word floor, the rounding, the tie-break and the
    recorded fields are :func:`imposter2.match_donors`'s, reproduced here only
    because the eligibility filter needs two more exclusions (D7-GUARD) and the
    vocabulary must stay fitted once over the whole document set. The
    unmodified ``match_donors`` is run alongside as the reference and every
    subject whose reference winner survived the extra exclusions must match it.

    Read-never-redo: once ``imposter_pairs_confirm.json`` exists it is reused,
    so a re-run cannot silently re-match a donor under a prompt already built
    against the old pair.
    """
    by_id = {r["canonical_id"]: r for r in pool}
    sample = I2.donor_sample(pool, dev_ids)
    frozen_sha = I2.sample_sha256(sample)
    committed = json.loads(
        (RESULTS_DIR / "stage2_pilot/imposter_pairs.json").read_text("utf-8"))
    if committed["donor_sample_sha256"] != frozen_sha:
        raise fatal("the seed-48 donor bank no longer reproduces the sha "
                    "committed in results/stage2_pilot/imposter_pairs.json")

    permitted = [c for c in sample
                 if c not in draw_ids and c not in set(dev_ids)]
    removed_as_study_subjects = sorted(set(sample) - set(permitted))

    pairs_path = out_dir / "imposter_pairs_confirm.json"
    superseded = None
    if pairs_path.exists():
        doc = json.loads(pairs_path.read_text(encoding="utf-8"))
        if sorted(doc["pairs"]) == sorted(subject_ids):
            return doc
        # The subject set grew. D7's method fits the TF-IDF "once on all
        # eligible donor documents plus all subject documents", so a larger
        # subject set is a different fit and the whole match is redone -- one
        # uniform rule over every confirmatory subject, rather than one rule
        # for the subjects matched early and another for the rest. Safe here
        # only because nothing has been generated yet: re-matching costs file
        # bytes, not node-hours. What moved is recorded, never silent.
        superseded = {"n_subjects_before": len(doc["pairs"]),
                      "pairs_before": dict(doc["pairs"])}

    texts = donor_texts_from_cache(sample)
    donor_texts = {c: texts[c] for c in permitted}
    subject_texts = {cid: I2.grounding_text(cid, pilot_dir=out_dir)
                     for cid in subject_ids}

    # match_donors' own construction, step for step.
    donor_words = {c: S.word_count(t) for c, t in donor_texts.items()}
    eligible = sorted(c for c, w in donor_words.items()
                      if w >= I2.WORD_FLOOR)
    subjects = sorted(subject_ids)
    docs = eligible + subjects
    vectors = I2.tfidf_vectors([donor_texts[c] for c in eligible]
                               + [subject_texts[c] for c in subjects],
                               max_df=I2.MAX_DF)
    vec = dict(zip(docs, vectors))
    vocabulary = len({t for row in vectors for t in row})

    donor_split = {}
    donor_tokens = {}
    guest_words = S.load_guest_words([by_id[c] for c in eligible])
    for donor in eligible:
        donor_split[donor] = S.chronological_split(by_id[donor],
                                                   guest_words.get(donor, {}))
        toks = I2.tokenize(donor_texts[donor])
        donor_tokens[donor] = (toks, set(toks))

    pairs, similarity, runners = {}, {}, {}
    excluded_by_name, excluded_by_guard = {}, {}
    for cid in subjects:
        row = by_id[cid]
        split = S.load_split(cid, out_dir)
        blocked_name, blocked_guard, scored = [], [], []
        for donor in eligible:
            conflict, why = I2.name_conflict(row, by_id[donor], I2.NAME_RATIO)
            if conflict:
                blocked_name.append({"donor": donor, "reason": why})
                continue
            why = _shares_transcript(row, by_id[donor], split,
                                     donor_split[donor])
            if not why:
                why = _names_subject(row, *donor_tokens[donor])
            if why:
                blocked_guard.append({"donor": donor, "reason": why})
                continue
            scored.append((round(I2.cosine(vec[cid], vec[donor]), 6), donor))
        if not scored:
            raise fatal(f"{cid}: every eligible donor was excluded")
        scored.sort(key=lambda s: (-s[0], s[1]))
        pairs[cid] = scored[0][1]
        similarity[cid] = scored[0][0]
        runners[cid] = [[d, s] for s, d in scored[1:6]]
        excluded_by_name[cid] = blocked_name
        excluded_by_guard[cid] = blocked_guard

    # Reference run: the unmodified frozen matcher, for the equivalence check.
    reference = I2.match_donors(subjects, pool, subject_texts, donor_texts,
                                donor_ids=permitted)
    guard_blocked = {cid: {b["donor"] for b in v}
                     for cid, v in excluded_by_guard.items()}
    divergent = sorted(
        cid for cid in subjects
        if reference["pairs"][cid] not in guard_blocked[cid]
        and reference["pairs"][cid] != pairs[cid])
    if divergent:
        raise fatal("the confirmatory matcher disagrees with the frozen "
                    f"matcher on {divergent} without a D7-GUARD exclusion "
                    "explaining it")
    moved = sorted(cid for cid in subjects
                   if reference["pairs"][cid] != pairs[cid])

    by_donor: dict[str, list[str]] = {}
    for cid, donor in pairs.items():
        by_donor.setdefault(donor, []).append(cid)
    used = sorted({*pairs.values(),
                   *(d for rs in runners.values() for d, _ in rs)})

    doc = {
        "method": I2.METHOD,
        "confirmatory_method_delta": (
            "Identical to the frozen method above, with the eligibility "
            "filter extended by D7-GUARD: a donor that shares a transcript "
            "with the subject (raw rows or D2 splits) or whose grounding text "
            "carries the subject's name is excluded from the argmax instead "
            "of being allowed to win and then trip the leakage assert. The "
            "asserts themselves are unchanged and still run on the winner."),
        "donor_seed": I2.DONOR_SEED,
        "n_donor_sample": len(permitted),
        "donor_sample_sha256": I2.sample_sha256(permitted),
        "n_donor_texts": len(donor_texts),
        "word_floor": I2.WORD_FLOOR,
        "name_ratio": I2.NAME_RATIO,
        "max_df": I2.MAX_DF,
        "vocabulary_terms": vocabulary,
        "n_eligible_donors": len(eligible),
        "donor_multiplicity": {
            "distinct_donors": len(by_donor),
            "n_subjects": len(pairs),
            "max_subjects_per_donor": max((len(v) for v in by_donor.values()),
                                          default=0),
            "subjects_by_donor": {d: sorted(v)
                                  for d, v in sorted(by_donor.items())},
            "shared_donors": sorted(d for d, v in by_donor.items()
                                    if len(v) > 1),
        },
        "pairs": pairs,
        "similarity": similarity,
        "runner_up_top5": runners,
        "subject_words": {c: S.word_count(subject_texts[c]) for c in subjects},
        "donor_words": {c: donor_words[c] for c in used},
        "excluded_by_name": {c: v for c, v in excluded_by_name.items() if v},
        "excluded_by_leakage_guard": {c: v for c, v in
                                      excluded_by_guard.items() if v},
        "donors_recorded": used,
    }
    doc["confirmatory"] = {
        "rule_ids": ["D7-CONF", "D7-GUARD"],
        "frozen_bank_sha256": frozen_sha,
        "frozen_bank_size": len(sample),
        "n_removed_as_study_subjects": len(removed_as_study_subjects),
        "removed_as_study_subjects": removed_as_study_subjects,
        "n_permitted_donors": len(permitted),
        "permitted_bank_sha256": I2.sample_sha256(permitted),
        "reference_matcher": {
            "source": "doppler.imposter2.match_donors, unmodified",
            "n_subjects_whose_winner_moved": len(moved),
            "subjects_whose_winner_moved": moved,
            "reference_pairs_for_moved": {c: reference["pairs"][c]
                                          for c in moved},
            "equivalence_checked": ("every subject whose reference winner was "
                                    "not D7-GUARD-excluded matches"),
        },
        "subject_turnfile_sha256": {
            cid: sha256_file(S.subject_dir(cid, out_dir)
                             / "grounding_turns.jsonl")[:16]
            for cid in subjects},
    }
    if superseded is not None:
        before = superseded["pairs_before"]
        moved_by_refit = [
            {"canonical_id": c, "donor_before": before[c],
             "donor_now": pairs[c]}
            for c in sorted(before) if before[c] != pairs[c]]
        doc["confirmatory"]["supersedes_earlier_match"] = {
            "n_subjects_before": superseded["n_subjects_before"],
            "n_subjects_now": len(pairs),
            "reason": (
                "D7 fits the TF-IDF once over all eligible donor documents "
                "plus ALL subject documents. Growing the confirmatory subject "
                "set from "
                f"{superseded['n_subjects_before']} to {len(pairs)} changes "
                "that fit, so the match was redone for every subject rather "
                "than leaving two populations matched under two different "
                "idf weightings. No generation had been run against the "
                "earlier pairs."),
            "n_donors_moved": len(moved_by_refit),
            "donors_moved": moved_by_refit,
        }

    # The frozen leakage guards, unrelaxed, on the winners.
    for cid, donor in sorted(pairs.items()):
        I2.check_no_shared_transcripts(by_id[cid], by_id[donor],
                                       S.load_split(cid, out_dir),
                                       donor_split[donor])
        I2.check_no_subject_name_in_text(by_id[cid], donor, donor_texts[donor])
    doc["confirmatory"]["guards"] = {
        "check_no_shared_transcripts": "passed for every pair",
        "check_no_subject_name_in_text": "passed for every pair",
    }
    S.write_json(pairs_path, doc)
    return doc


def write_donor_artifacts(donor_ids: list[str], pool: list[dict],
                          out_dir: Path) -> dict:
    """The matched donors' D2 split and grounding turns, one corpus pass.

    Same layout and same schema as ``results/stage2_pilot/donors/<cid>/``, so
    :func:`stage2_pilot.donor_grounding` reads it unchanged. Resumable: a donor
    whose two files already exist is not re-read.
    """
    by_id = {r["canonical_id"]: r for r in pool}
    todo = [d for d in donor_ids
            if not (out_dir / "donors" / d / "grounding_turns.jsonl").exists()]
    written = {}
    if todo:
        guest_words = S.load_guest_words([by_id[d] for d in todo])
        splits = {d: S.chronological_split(by_id[d], guest_words.get(d, {}))
                  for d in todo}
        wanted = sorted({e["transcript_id"]
                         for sp in splits.values() for e in sp["grounding"]})
        records = S.fetch_records(wanted)
        for donor in sorted(todo):
            base = out_dir / "donors" / donor
            base.mkdir(parents=True, exist_ok=True)
            split = splits[donor]
            turns = []
            for entry in split["grounding"]:
                for turn in S.extract_turns(records[entry["transcript_id"]],
                                            by_id[donor]):
                    turns.append(turn)
            S.write_json(base / "split.json", split)
            S.write_jsonl(base / "grounding_turns.jsonl", turns)
    # A re-match can retire a donor. Its artifacts are dropped so the committed
    # donors/ directory always holds exactly the donors in force.
    keep = set(donor_ids)
    pruned = []
    donors_root = out_dir / "donors"
    if donors_root.exists():
        for path in sorted(donors_root.iterdir()):
            if path.is_dir() and path.name not in keep:
                for child in sorted(path.iterdir()):
                    child.unlink()
                path.rmdir()
                pruned.append(path.name)

    for donor in sorted(donor_ids):
        base = out_dir / "donors" / donor
        written[donor] = {
            "split_sha256": sha256_file(base / "split.json")[:16],
            "turns_sha256": sha256_file(base / "grounding_turns.jsonl")[:16],
        }
    # ``n_built_this_run`` is run-scoped, not content: it lives in
    # render_run.json so render_manifest.json stays byte-identical whether the
    # donor artifacts were already on disk or were built by this invocation.
    # Both counters are run-scoped, not content: whether a donor directory was
    # built or pruned by THIS invocation depends on what was already on disk,
    # so they live in render_run.json and the manifest stays byte-stable.
    return {"n_donors": len(donor_ids), "files": written,
            "_n_built_this_run": len(todo),
            "_retired_donor_dirs_pruned": pruned}


# ---------------------------------------------------------------------------
# H7 cutoff plan (DERIVED_RULES H7-R2 .. H7-R6)
# ---------------------------------------------------------------------------


def same_event_leak_scan(cid: str, out_dir: Path) -> dict:
    """How much of the test interview is replayed on the subject's grounding side.

    DESCRIPTIVE. Nothing is excluded on this number -- the frozen exclusions
    are D2's same-event guard upstream and the per-item answer-leak assert
    downstream, and inventing a third threshold here would be a new bar rather
    than a reading. It exists because the downstream assert only sees the
    2,000-word rendered block, so a re-aired interview whose overlap happens to
    fall outside the budget window would leave no trace anywhere.

    Measured with the frozen convention: 10-word shingles over
    ``stage2_render._norm_tokens``, guest-role text only, per grounding
    transcript against the test transcript.
    """
    base = S.subject_dir(cid, out_dir)
    test_turns = S.read_jsonl(base / "test_turns.jsonl")
    grounding_turns = S.read_jsonl(base / "grounding_turns.jsonl")

    def shingles(turns, tid=None):
        text = " ".join(t["text"] for t in turns if t.get("role") == "guest"
                        and (tid is None or t["transcript_id"] == tid))
        toks = R._norm_tokens(text)
        n = R.SHINGLE_WORDS
        return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}, len(toks)

    test_sh, test_words = shingles(test_turns)
    per_transcript = {}
    worst = 0.0
    for tid in sorted({t["transcript_id"] for t in grounding_turns}):
        sh, words = shingles(grounding_turns, tid)
        shared = len(test_sh & sh)
        frac = (shared / len(test_sh)) if test_sh else 0.0
        if shared:
            per_transcript[tid] = {"guest_words": words,
                                   "shared_10grams": shared,
                                   "share_of_test": round(frac, 4)}
        worst = max(worst, frac)
    return {"test_guest_words": test_words,
            "n_test_10grams": len(test_sh),
            "max_share_of_test_in_one_grounding_transcript": round(worst, 4),
            "grounding_transcripts_with_overlap": per_transcript}


def cutoff_table(segments: list[dict], test_date: str) -> list[dict]:
    """Every candidate cutoff for one subject, with Delta, bin and volume.

    ``available_words`` uses ``stage2_render._exchange_items`` -- the exact
    accounting ``render_grounding`` budgets against -- so the B7.3 fill test is
    measured in the same unit as the budget it is tested against.
    """
    items = R._exchange_items(segments)
    per_date: dict[str, int] = {}
    for _seg, _ex, seg_date, _host, _guest, words in items:
        per_date[seg_date] = per_date.get(seg_date, 0) + words
    table = []
    running = 0
    for cut_date in sorted(per_date):
        running += per_date[cut_date]
        delta = days_between(test_date, cut_date)
        table.append({
            "cutoff_date": cut_date,
            "delta_days": delta,
            "delta_bin": delta_bin(delta),
            "available_words": running,
            "fillable": running >= GROUNDING_BUDGET_WORDS,
        })
    return table


def h7_plan(segments: list[dict], test_date: str) -> dict:
    """The bins one subject fills, and why every other cutoff was dropped."""
    table = cutoff_table(segments, test_date)
    chosen: dict[str, dict] = {}
    dropped = {"lt_6m": [], "unfillable": [], "bin_already_filled": []}
    # Smallest Delta first == newest cutoff first (H7-R5).
    for row in sorted(table, key=lambda r: r["delta_days"]):
        name = row["delta_bin"]
        if name not in BIN_NAMES:
            dropped["lt_6m"].append(row)
            continue
        if name in chosen:
            dropped["bin_already_filled"].append(row)
            continue
        if not row["fillable"]:
            dropped["unfillable"].append(row)
            continue
        chosen[name] = row
    filled = [b for b in BIN_NAMES if b in chosen]
    return {
        "cutoffs": table,
        "chosen": {b: chosen[b] for b in filled},
        "bins_filled": filled,
        "n_bins_filled": len(filled),
        "within_subject_sweep_subset": len(filled) >= 3,
        "dropped": dropped,
    }


# ---------------------------------------------------------------------------
# Subject context: the grounding blocks both arms are built from
# ---------------------------------------------------------------------------


def subject_context(row: dict, pool: dict, pairs: dict, out_dir: Path,
                    draw_flags: dict) -> dict:
    """Everything one subject's prompts need, with both blocks already guarded.

    Identical construction to ``stage2_oe1.subject_blocks``: the twin block is
    the subject's own grounding redacted with the subject's variants, the
    imposter block is the D7 donor's grounding redacted with the DONOR's
    variants, and both are asserted clean before a prompt is built from them.
    """
    cid = row["canonical_id"]
    pool_row = pool[cid]
    variants = P1.name_variants(pool_row)
    segments, _turns = P1.subject_grounding(cid, pilot_dir=out_dir)
    twin_block = R.redact(
        R.render_grounding(segments, GROUNDING_BUDGET_WORDS), variants)
    R.assert_redacted(twin_block, variants)

    donor_id = pairs[cid]
    donor_variants = P1.name_variants(pool[donor_id])
    dsegs, _dturns = P1.donor_grounding(donor_id, pilot_dir=out_dir)
    donor_block = R.redact(
        R.render_grounding(dsegs, GROUNDING_BUDGET_WORDS), donor_variants)
    R.assert_redacted(donor_block, donor_variants)
    if donor_block == twin_block:
        raise fatal(f"{cid}: the imposter block equals the twin block")

    split = S.load_split(cid, out_dir)
    test_date = (split.get("test") or {}).get("date")
    gdates = sorted(g.get("date", "") for g in split.get("grounding", [])
                    if g.get("date"))
    newest = gdates[-1] if gdates else None
    delta_days = days_between(test_date, newest) if newest else None

    elig = h7_eligibility(pool_row, draw_flags.get(cid, False))
    plan = h7_plan(segments, test_date) if elig["pool_derived"] else None

    return {
        "canonical_id": cid,
        "canonical_name": pool_row["canonical_name"],
        "draw_pos": row["draw_pos"],
        "stratum": row["stratum"],
        "variants": variants,
        "segments": segments,
        "twin_block": twin_block,
        "twin_block_words": OE.grounding_speech_words(twin_block),
        "donor_id": donor_id,
        "donor_variants": donor_variants,
        "donor_block": donor_block,
        "donor_block_words": OE.grounding_speech_words(donor_block),
        "test_date": test_date,
        "grounding_dates": gdates,
        "newest_grounding_date": newest,
        "delta_days": delta_days,
        "delta_bin": delta_bin(delta_days),
        "h7_eligibility": elig,
        "h7": plan,
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def _guarded(arm: str, item: dict, ctx: dict, block, donor_variants,
             failures: list, *, h7_bin=None, cutoff_date=None):
    """One render, every guard, and an exclusion record instead of a crash."""
    try:
        built = OE1.render_and_guard_open(
            _base_arm(arm),
            item, subject_name=ctx["canonical_name"],
            subject_variants=ctx["variants"], grounding_block=block,
            donor_variants=donor_variants)
    except (SystemExit, ValueError, AssertionError, KeyError) as exc:
        failures.append({
            "canonical_id": ctx["canonical_id"], "item_id": item["item_id"],
            "arm": arm, "h7_bin": h7_bin, "cutoff_date": cutoff_date,
            "guard": type(exc).__name__,
            "reason": " ".join(str(exc).split())[:400],
        })
        return None

    # The build-QA checks that live outside render_and_guard_open, re-run per
    # prompt rather than once per set, so an exclusion can name its prompt.
    # Scope copied from stage2_oe1.build_qa step (6): the subject-variant
    # sweep runs on the REDACTED arms. A named arm carries the name on
    # purpose, and render_and_guard_open has already asserted that arm clean
    # with its one name line removed.
    prompt = built["prompt"]
    left = ([] if _base_arm(arm) in OE.NAMED_ARMS
            else R.surviving_variants(prompt, ctx["variants"]))
    if donor_variants is not None:
        left = left + R.surviving_variants(prompt, donor_variants)
    residue = OE.forced_choice_residue(prompt)
    over_budget = built["grounding_speech_words"] > GROUNDING_BUDGET_WORDS
    tail_ok = built["instruction_tail_sha256"] == OE.INSTRUCTION_SHA256
    problems = []
    if left:
        problems.append(f"surviving name variants {sorted(set(left))[:3]}")
    if residue:
        problems.append(f"forced-choice residue {residue}")
    if over_budget:
        problems.append(
            f"grounding {built['grounding_speech_words']} words over the "
            f"{GROUNDING_BUDGET_WORDS}-word budget")
    if not tail_ok:
        problems.append("instruction tail is not the frozen tail")
    if problems:
        failures.append({
            "canonical_id": ctx["canonical_id"], "item_id": item["item_id"],
            "arm": arm, "h7_bin": h7_bin, "cutoff_date": cutoff_date,
            "guard": "post_render_qa", "reason": "; ".join(problems),
        })
        return None

    built.update({
        "item_id": item["item_id"], "canonical_id": ctx["canonical_id"],
        "arm": arm, "h7_bin": h7_bin, "cutoff_date": cutoff_date,
        "delta_days": None if h7_bin is None else days_between(
            ctx["test_date"], cutoff_date),
        "item_type": item["item_type"],
        "donor_id": (ctx["donor_id"]
                     if arm in ("imposter_redacted", H7_IMPOSTER_ARM) else None),
    })
    return built


def _base_arm(arm: str) -> str:
    """The frozen five-arm name an H7 arm renders as."""
    if arm == H7_TWIN_ARM:
        return "twin_redacted"
    if arm == H7_IMPOSTER_ARM:
        return "imposter_redacted"
    return arm


def render_subject(ctx: dict, items: list[dict], failures: list) -> dict:
    """Every logical render for one subject: five H1 arms, then H7."""
    rows: list[dict] = []
    excluded_items: dict[str, str] = {}

    # --- H1: the five frozen arms, exactly as OE-1 built them ---------------
    for item in items:
        built_for_item = []
        ok = True
        for arm in OE.ARMS:
            if arm == "imposter_redacted":
                block, donor_check = ctx["donor_block"], ctx["donor_variants"]
            elif arm in OE.GROUNDED_ARMS:
                block, donor_check = ctx["twin_block"], None
            else:
                block, donor_check = None, None
            built = _guarded(arm, item, ctx, block, donor_check, failures)
            if built is None:
                ok = False
                break
            built_for_item.append(built)
        if not ok:
            excluded_items[item["item_id"]] = failures[-1]["arm"]
            continue
        rows.extend(built_for_item)

    kept = [it for it in items if it["item_id"] not in excluded_items]

    # --- H7: one twin render per filled bin, plus the fresh imposter --------
    h7_rows: list[dict] = []
    crossover_rows: list[dict] = []
    plan = ctx.get("h7")
    if plan and plan["bins_filled"] and kept:
        for name in plan["bins_filled"]:
            cut = plan["chosen"][name]
            subset = [s for s in ctx["segments"]
                      if s.get("date", "") <= cut["cutoff_date"]]
            block = R.redact(
                R.render_grounding(subset, GROUNDING_BUDGET_WORDS),
                ctx["variants"])
            R.assert_redacted(block, ctx["variants"])
            cut["rendered_words"] = OE.grounding_speech_words(block)
            cut["n_grounding_clusters"] = len(subset)
            for item in kept:
                built = _guarded(H7_TWIN_ARM, item, ctx, block, None, failures,
                                 h7_bin=name, cutoff_date=cut["cutoff_date"])
                if built is not None:
                    h7_rows.append(built)
        # The crossover's fresh imposter: one per item, reused at every bin.
        for item in kept:
            built = _guarded(H7_IMPOSTER_ARM, item, ctx, ctx["donor_block"],
                             ctx["donor_variants"], failures)
            if built is not None:
                crossover_rows.append(built)

    rows.extend(h7_rows)
    rows.extend(crossover_rows)
    return {"rows": rows, "kept_items": kept,
            "excluded_items": excluded_items,
            "n_h1": len(rows) - len(h7_rows) - len(crossover_rows),
            "n_h7_twin": len(h7_rows), "n_h7_crossover": len(crossover_rows)}


# ---------------------------------------------------------------------------
# Export: dedup, chunk, write
# ---------------------------------------------------------------------------

API_FIELDS = ("idx", "chunk", "canonical_id", "item_id", "arm", "h7_bin",
              "cutoff_date", "delta_days", "item_type", "donor_id",
              "prompt_sha256", "prompt_words", "prompt_tokens_est",
              "grounding_speech_words", "max_output_tokens", "temperature",
              "model", "prompt")

NODE_META_FIELDS = ("idx", "item_id", "canonical_id", "arm", "h7_bin",
                    "cutoff_date", "delta_days", "item_type", "prompt_sha256",
                    "prompt_words", "prompt_tokens_est")


def dedup_subject_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Unique prompts for one subject, plus the logical index that maps to them.

    Two logical renders collapse only when their prompt strings are byte
    identical, which at temperature 0 means one generation answers both. The
    two cases this is built for are named in H7-R5/H7-R7: the newest H7 cutoff
    reproduces the H1 twin prompt, and the crossover imposter reproduces the H1
    imposter prompt.
    """
    unique: list[dict] = []
    by_sha: dict[str, int] = {}
    index: list[dict] = []
    for row in rows:
        sha = row["prompt_sha256"]
        if sha not in by_sha:
            by_sha[sha] = len(unique)
            unique.append(row)
        slot = unique[by_sha[sha]]
        index.append({
            "canonical_id": row["canonical_id"], "item_id": row["item_id"],
            "arm": row["arm"], "h7_bin": row["h7_bin"],
            "cutoff_date": row["cutoff_date"], "delta_days": row["delta_days"],
            "prompt_sha256": sha,
            "generated_as_arm": slot["arm"],
            "generated_as_h7_bin": slot["h7_bin"],
            "is_duplicate_of_earlier_render": slot is not row,
        })
    return unique, index


def chunk_subjects(per_subject: list[dict],
                   target: int = CHUNK_TARGET_PROMPTS) -> list[list[dict]]:
    """Whole subjects packed into blocks of roughly ``target`` prompts.

    A block never splits a subject: the launch plan's parallel submission
    depends on the blocks being independent, and a subject's arms have to stay
    together for the per-subject ledger to mean anything.

    A block never spans two build tranches either, so the chunk numbering runs
    continuously across the whole draw and a chunk always names one tranche.
    Subjects arrive in draw order, so tranche order is draw order.
    """
    chunks: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    tranche = None
    for entry in per_subject:
        n = len(entry["unique"])
        if current and (size + n > target or entry["tranche"] != tranche):
            chunks.append(current)
            current, size = [], 0
        current.append(entry)
        size += n
        tranche = entry["tranche"]
    if current:
        chunks.append(current)
    return chunks


def write_chunks(chunks: list[list[dict]], out_dir: Path) -> dict:
    prompts_dir = out_dir / "prompts"
    node_dir = out_dir / "node"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    node_dir.mkdir(parents=True, exist_ok=True)
    files = []
    index_rows: list[dict] = []
    for n, chunk in enumerate(chunks, start=1):
        tag = f"chunk_{n:02d}"
        api_rows, node_prompts, node_meta = [], [], []
        idx = 0
        for entry in chunk:
            for row in entry["unique"]:
                api = {
                    "idx": idx, "chunk": tag,
                    "canonical_id": row["canonical_id"],
                    "item_id": row["item_id"], "arm": row["arm"],
                    "h7_bin": row["h7_bin"], "cutoff_date": row["cutoff_date"],
                    "delta_days": row["delta_days"],
                    "item_type": row["item_type"], "donor_id": row["donor_id"],
                    "prompt_sha256": row["prompt_sha256"],
                    "prompt_words": row["prompt_words"],
                    "prompt_tokens_est": row["prompt_tokens_est"],
                    "grounding_speech_words": row["grounding_speech_words"],
                    "max_output_tokens": GEN_MAX_OUTPUT_TOKENS,
                    "temperature": GEN_TEMPERATURE,
                    "model": ROBUSTNESS_MODEL,
                    "prompt": row["prompt"],
                }
                api_rows.append({k: api[k] for k in API_FIELDS})
                node_prompts.append({
                    "idx": idx, "prompt": row["prompt"],
                    "max_output_tokens": GEN_MAX_OUTPUT_TOKENS})
                meta = dict(api, idx=idx)
                node_meta.append({k: meta[k] for k in NODE_META_FIELDS})
                row["_chunk"], row["_idx"] = tag, idx
                idx += 1
            for ref in entry["index"]:
                slot = next(r for r in entry["unique"]
                            if r["prompt_sha256"] == ref["prompt_sha256"])
                index_rows.append(dict(ref, chunk=slot["_chunk"],
                                       idx=slot["_idx"]))
        api_path = prompts_dir / f"{tag}.jsonl"
        node_path = node_dir / f"{tag}.prompts.jsonl"
        meta_path = node_dir / f"{tag}.meta.jsonl"
        S.write_jsonl(api_path, api_rows)
        S.write_jsonl(node_path, node_prompts)
        S.write_jsonl(meta_path, node_meta)
        files.append({
            "chunk": tag,
            "tranche": TRANCHE_NAMES[chunk[0]["tranche"]],
            "subjects": [e["canonical_id"] for e in chunk],
            "n_subjects": len(chunk),
            "n_prompts": len(api_rows),
            "n_logical_renders": sum(len(e["index"]) for e in chunk),
            "tokens_in_est": sum(r["prompt_tokens_est"] for r in api_rows),
            "tokens_out_cap": len(api_rows) * GEN_MAX_OUTPUT_TOKENS,
            "api_file": rel(api_path), "api_sha256": sha256_file(api_path),
            "node_prompts_file": rel(node_path),
            "node_prompts_sha256": sha256_file(node_path),
            "node_meta_file": rel(meta_path),
            "node_meta_sha256": sha256_file(meta_path),
        })
    S.write_jsonl(out_dir / "render_index.jsonl", index_rows)
    return {"chunks": files, "n_chunks": len(files),
            "index_file": rel(out_dir / "render_index.jsonl"),
            "index_sha256": sha256_file(out_dir / "render_index.jsonl"),
            "n_logical_renders": len(index_rows)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--build-file", default=None)
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir or CONFIRM_DIR)
    build_file = Path(args.build_file or BUILD_FILE)
    started = time.time()

    rows = survivors(build_file)
    subject_ids = [r["canonical_id"] for r in rows]
    pool_list = S.load_pool()
    pool = {r["canonical_id"]: r for r in pool_list}
    dev_ids = sorted({s["canonical_id"] for s in P1.dev_subjects()})
    draw = json.loads(DRAW_FILE.read_text(encoding="utf-8"))
    draw_ids = {s["canonical_id"] for s in draw["subjects"]}
    draw_flags = {s["canonical_id"]: s["h7_eligible"] for s in draw["subjects"]}
    stray = sorted(set(subject_ids) - draw_ids)
    if stray:
        raise fatal(f"survivors not in the committed draw: {stray}")
    print(f"[render] {len(subject_ids)} survivors of draw positions 1-40")

    pairs_doc = select_donors(subject_ids, pool_list, dev_ids, draw_ids, out_dir)
    pairs = pairs_doc["pairs"]
    donors = write_donor_artifacts(sorted(set(pairs.values())), pool_list,
                                   out_dir)
    print(f"[render] D7 donors matched: {len(set(pairs.values()))} distinct "
          f"for {len(pairs)} subjects")

    # --- context, items, renders -------------------------------------------
    failures: list[dict] = []
    per_subject: list[dict] = []
    item_rows: list[dict] = []
    h7_report: list[dict] = []
    elig_mismatches: list[dict] = []
    leak_scan: list[dict] = []

    for row in rows:
        cid = row["canonical_id"]
        ctx = subject_context(row, pool, pairs, out_dir, draw_flags)
        elig = ctx["h7_eligibility"]
        if not (elig["agrees_with_draw"] and elig["derivations_agree"]):
            elig_mismatches.append(dict(elig, canonical_id=cid))

        items = []
        for qa in S.read_jsonl(S.subject_dir(cid, out_dir) / "qa_items.jsonl"):
            rule = C4.classify_question(qa["question"])
            items.append(dict(qa, item_type=rule["kind"],
                              item_type_source="cue_rule_confirmatory"))
        if len(items) != row["n_items"]:
            raise fatal(f"{cid}: build.json says {row['n_items']} items, "
                        f"qa_items.jsonl holds {len(items)}")

        scan = same_event_leak_scan(cid, out_dir)
        scan["canonical_id"] = cid
        leak_scan.append(scan)

        built = render_subject(ctx, items, failures)
        unique, index = dedup_subject_rows(built["rows"])
        per_subject.append({
            "canonical_id": cid, "draw_pos": row["draw_pos"],
            "tranche": row["tranche"],
            "unique": unique, "index": index,
            "n_items_built": len(built["kept_items"]),
            "n_items_excluded": len(built["excluded_items"]),
        })

        for item in built["kept_items"]:
            item_rows.append({
                "item_id": item["item_id"], "canonical_id": cid,
                "transcript_id": item["transcript_id"],
                "q_turn_idx": item["q_turn_idx"],
                "question": item["question"],
                "real_answer_verbatim": item["answer"],
                "answer_words": item.get("answer_words")
                or R.word_count(item["answer"]),
                "item_type": item["item_type"],
                "item_type_source": item["item_type_source"],
                "test_date": ctx["test_date"],
                "newest_grounding_date": ctx["newest_grounding_date"],
                "delta_days": ctx["delta_days"],
                "delta_bin": ctx["delta_bin"],
                "donor_id": ctx["donor_id"],
                "flags": item.get("flags", []),
            })

        plan = ctx["h7"]
        h7_report.append({
            "canonical_id": cid, "draw_pos": row["draw_pos"],
            "tranche": TRANCHE_NAMES[row["tranche"]],
            "h7_eligible": elig["pool_derived"],
            "eligibility": elig,
            "test_date": ctx["test_date"],
            "n_grounding_clusters": len(ctx["segments"]),
            "grounding_words_total": (
                sum(it[5] for it in R._exchange_items(ctx["segments"]))),
            "bins_filled": plan["bins_filled"] if plan else [],
            "n_bins_filled": plan["n_bins_filled"] if plan else 0,
            "within_subject_sweep_subset": (
                plan["within_subject_sweep_subset"] if plan else False),
            "chosen_cutoffs": plan["chosen"] if plan else {},
            "n_cutoffs_considered": len(plan["cutoffs"]) if plan else 0,
            "dropped_lt_6m": len(plan["dropped"]["lt_6m"]) if plan else 0,
            "dropped_unfillable": (
                len(plan["dropped"]["unfillable"]) if plan else 0),
            "dropped_bin_already_filled": (
                len(plan["dropped"]["bin_already_filled"]) if plan else 0),
            "cutoffs": plan["cutoffs"] if plan else [],
        })
        print(f"[render] {cid} pos {row['draw_pos']:>3}  "
              f"{len(built['kept_items'])} items  "
              f"{len(unique)} prompts  "
              f"H7 bins {','.join(plan['bins_filled']) if plan else '-'}")

    # --- guard rollup, and the stop rule ------------------------------------
    n_logical = sum(len(e["index"]) for e in per_subject)
    n_attempted = n_logical + len(failures)
    exclusion_rate = (len(failures) / n_attempted) if n_attempted else 0.0
    if exclusion_rate > GUARD_EXCLUSION_STOP_RATE:
        S.write_json(out_dir / "render_guard_failures.json",
                     {"n_failures": len(failures),
                      "n_attempted": n_attempted,
                      "exclusion_rate": round(exclusion_rate, 4),
                      "failures": failures})
        raise fatal(
            f"{len(failures)} of {n_attempted} renders failed a guard "
            f"({exclusion_rate:.1%} > {GUARD_EXCLUSION_STOP_RATE:.0%}). That "
            "is a systematic problem, not an outlier: nothing was written, "
            "see results/stage2_confirm/render_guard_failures.json")

    # --- the D6-v4.9 twin rule, on the per-(arm, bin) sets ------------------
    logical = [r for e in per_subject for r in e["index"]]
    sets: dict[str, list[dict]] = {}
    for r in logical:
        key = r["arm"] if r["h7_bin"] is None else f"{r['arm']}@{r['h7_bin']}"
        sets.setdefault(key, []).append(r)
    twin_check = OE1.assert_no_cross_visible_twins(sets)

    # --- H7-R7: the crossover imposter really is the H1 imposter ------------
    by_key = {(r["canonical_id"], r["item_id"], r["arm"]): r for r in logical}
    crossover_checked = crossover_identical = 0
    for r in logical:
        if r["arm"] != H7_IMPOSTER_ARM:
            continue
        crossover_checked += 1
        h1 = by_key.get((r["canonical_id"], r["item_id"], "imposter_redacted"))
        if h1 is not None and h1["prompt_sha256"] == r["prompt_sha256"]:
            crossover_identical += 1
    if crossover_checked != crossover_identical:
        raise fatal(
            f"{crossover_checked - crossover_identical} crossover imposter "
            "renders are NOT byte-identical to their H1 imposter_redacted "
            "counterpart; rule H7-R7 does not hold and the H7 crossover "
            "cannot reuse the H1 arm")

    # --- export -------------------------------------------------------------
    # A subject whose every item was guard-excluded has nothing to submit and
    # must not occupy a block. It stays in every report.
    dropped_subjects = [e["canonical_id"] for e in per_subject
                        if not e["unique"]]
    chunks = chunk_subjects([e for e in per_subject if e["unique"]])
    written = write_chunks(chunks, out_dir)
    S.write_jsonl(out_dir / "items_confirm.jsonl", item_rows)

    # --- counts -------------------------------------------------------------
    per_arm_logical: dict[str, int] = {}
    per_arm_unique: dict[str, int] = {}
    for r in logical:
        per_arm_logical[r["arm"]] = per_arm_logical.get(r["arm"], 0) + 1
    for e in per_subject:
        for r in e["unique"]:
            per_arm_unique[r["arm"]] = per_arm_unique.get(r["arm"], 0) + 1
    n_unique = sum(len(e["unique"]) for e in per_subject)
    h1_arms = set(OE.ARMS)
    n_unique_h1 = sum(v for a, v in per_arm_unique.items() if a in h1_arms)
    n_unique_h7 = n_unique - n_unique_h1

    per_bin_subjects = {b: sorted(s["canonical_id"] for s in h7_report
                                  if b in s["bins_filled"]) for b in BIN_NAMES}
    sweep_subset = sorted(s["canonical_id"] for s in h7_report
                          if s["within_subject_sweep_subset"])

    # --- per-tranche breakdown (reporting only; one rule set throughout) ----
    h7_by_id = {s["canonical_id"]: s for s in h7_report}
    by_subject = {e["canonical_id"]: e for e in per_subject}
    tranche_report = {}
    for num, name in sorted(TRANCHE_NAMES.items()):
        cids = [r["canonical_id"] for r in rows if r["tranche"] == num]
        if not cids:
            continue
        arms: dict[str, int] = {}
        for cid in cids:
            for r in by_subject[cid]["unique"]:
                arms[r["arm"]] = arms.get(r["arm"], 0) + 1
        tranche_report[name] = {
            "draw_positions": ([1, TRANCHE_1_LAST_POS] if num == 1
                               else [TRANCHE_1_LAST_POS + 1, 140]),
            "n_survivors": len(cids),
            "subjects": cids,
            "n_items_built": sum(by_subject[c]["n_items_built"] for c in cids),
            "n_unique_prompts": sum(len(by_subject[c]["unique"])
                                    for c in cids),
            "n_logical_renders": sum(len(by_subject[c]["index"])
                                     for c in cids),
            "unique_prompts_per_arm": arms,
            "n_h7_eligible": sum(1 for c in cids
                                 if h7_by_id[c]["h7_eligible"]),
            "n_h7_usable": sum(1 for c in cids
                               if h7_by_id[c]["n_bins_filled"] > 0),
            "n_h7_bin_renders": sum(h7_by_id[c]["n_bins_filled"]
                                    for c in cids),
            "n_within_subject_sweep_subset": sum(
                1 for c in cids
                if h7_by_id[c]["within_subject_sweep_subset"]),
            "chunks": [c["chunk"] for c in written["chunks"]
                       if c["tranche"] == name],
        }

    s1_commit = git_commit_for(_ROOT / "src/doppler/oe_render.py")
    manifest = {
        "banner": BANNER,
        "phase": "render",
        "contract": [
            "STAGE2_LAUNCH_PLAN.md section b",
            "PREREGISTRATION_AMENDMENT_2.md B7",
            "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md item 6",
        ],
        "draw": {
            "source": rel(build_file),
            "source_sha256": sha256_file(build_file),
            "draw_file": rel(DRAW_FILE), "draw_seed": draw["seed"],
            "draw_positions": [1, 140],
            "n_survivors_rendered": len(subject_ids),
            "subjects": subject_ids,
            "note": "The whole committed draw: every surviving subject of "
                    "positions 1-140. Every rule is applied identically to "
                    "all of them; the tranche split below is reporting only.",
        },
        "tranches": tranche_report,
        "generation_config": {
            "primary_model": PRIMARY_MODEL,
            "robustness_model": ROBUSTNESS_MODEL,
            "temperature": GEN_TEMPERATURE,
            "max_output_tokens": GEN_MAX_OUTPUT_TOKENS,
            "answer_word_cap": OE.MAX_ANSWER_WORDS,
            "grounding_budget_words": GROUNDING_BUDGET_WORDS,
            "instruction_tail_sha256": OE.INSTRUCTION_SHA256,
            "instruction_tail_text": OE.OPEN_ANSWER_INSTRUCTION,
            "same_prompts_both_models": True,
        },
        "renderer": {
            "oe_render_template_sha256": OE.TEMPLATE_SHA256,
            "oe_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/oe_render.py"),
            "s1_extension_commit": s1_commit,
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "stage2_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "stage2_data_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_data.py"),
            "render_call": "stage2_oe1.render_and_guard_open (unmodified)",
        },
        "derived_rules": DERIVED_RULES,
        "counts": {
            "n_subjects": len(subject_ids),
            "n_items_built": len(item_rows),
            "n_logical_renders": n_logical,
            "n_unique_prompts": n_unique,
            "n_unique_prompts_h1": n_unique_h1,
            "n_unique_prompts_h7": n_unique_h7,
            "n_unique_prompts_per_model": n_unique,
            "n_generations_both_models": n_unique * 2,
            "logical_renders_per_arm": per_arm_logical,
            "unique_prompts_per_arm": per_arm_unique,
            "deduplicated_logical_renders": n_logical - n_unique,
            "dedup_note": (
                "A logical render collapses only on byte-identical prompt "
                "text (H7-R5, H7-R7). Every logical row survives in "
                "render_index.jsonl with the prompt it is answered by."),
        },
        "h7": {
            "rule_ids": ["H7-R1", "H7-R2", "H7-R3", "H7-R4", "H7-R5",
                         "H7-R6", "H7-R7", "H7-R8"],
            "bins": [{"name": n, "lo_days": lo,
                      "hi_days": None if hi > 10 ** 5 else hi}
                     for n, lo, hi in DELTA_BINS],
            "budget_B_words": GROUNDING_BUDGET_WORDS,
            "n_eligible_survivors": sum(1 for s in h7_report
                                        if s["h7_eligible"]),
            "n_usable_subjects": sum(1 for s in h7_report
                                     if s["n_bins_filled"] > 0),
            "usable_note": (
                "USABLE = fills at least one Delta bin after the B7.3 volume "
                "control, i.e. can contribute a point to the fidelity-vs-Delta "
                "curve. This is the count the H7 subject-count branch should "
                "be read against, not the eligibility flag: an eligible "
                "subject that fills no bin contributes nothing to the slope."),
            "subject_count_branch": {
                "rule": "B7 / A5-mirroring: >= 80 confirmatory; 30-79 "
                        "exploratory (effect size + CI); < 30 descriptive",
                "on_eligibility_flag": sum(1 for s in h7_report
                                           if s["h7_eligible"]),
                "on_usable_subjects": sum(1 for s in h7_report
                                          if s["n_bins_filled"] > 0),
                "note": "Reported both ways; which one the branch is decided "
                        "on is an owner call, not this file's.",
            },
            "n_subjects_with_at_least_one_bin": sum(
                1 for s in h7_report if s["n_bins_filled"] > 0),
            "n_bin_renders": sum(s["n_bins_filled"] for s in h7_report),
            "per_bin_subject_counts": {b: len(v)
                                       for b, v in per_bin_subjects.items()},
            "per_bin_subjects": per_bin_subjects,
            "within_subject_sweep_subset": sweep_subset,
            "n_within_subject_sweep_subset": len(sweep_subset),
            "exclusions": {
                "cutoffs_dropped_lt_6m": sum(s["dropped_lt_6m"]
                                             for s in h7_report),
                "cutoffs_dropped_unfillable_B7_3": sum(
                    s["dropped_unfillable"] for s in h7_report),
                "cutoffs_dropped_bin_already_filled": sum(
                    s["dropped_bin_already_filled"] for s in h7_report),
                "eligible_subjects_filling_zero_bins": sorted(
                    s["canonical_id"] for s in h7_report
                    if s["h7_eligible"] and s["n_bins_filled"] == 0),
            },
            "eligibility": {
                "gate_used": "pool_derived (n_dedup_clusters >= 4 AND "
                             "span_days_dedup >= 730) -- the committed draw's "
                             "own rule, per rule H7-R8",
                "n_agreeing_with_draw_flag": sum(
                    1 for s in h7_report if s["eligibility"]["agrees_with_draw"]),
                "n_disagreeing_with_draw_flag": sum(
                    1 for s in h7_report
                    if not s["eligibility"]["agrees_with_draw"]),
                "n_eligible_pool_derived": sum(
                    1 for s in h7_report if s["eligibility"]["pool_derived"]),
                "n_eligible_substantive_derived": sum(
                    1 for s in h7_report
                    if s["eligibility"]["substantive_derived"]),
                "finding": (
                    "n_dedup_clusters counts every dedup cluster, including "
                    "non-substantive mentions, while only flag-S transcripts "
                    "ever enter a D2 split. Subjects therefore carry the "
                    "H7-eligible flag on cluster counts the pipeline cannot "
                    "ground on -- which is the mechanism behind the B7.3 "
                    "unfillable exclusions below. Reported, not acted on: the "
                    "flag is committed in the draw and quoted in the launch "
                    "plan (98 of 140), so changing the gate is an owner call."),
                "subjects_eligible_only_under_the_draw_rule": sorted(
                    s["canonical_id"] for s in h7_report
                    if s["eligibility"]["pool_derived"]
                    and not s["eligibility"]["substantive_derived"]),
                "bin_renders_that_would_be_lost_under_the_strict_reading": sum(
                    s["n_bins_filled"] for s in h7_report
                    if s["eligibility"]["pool_derived"]
                    and not s["eligibility"]["substantive_derived"]),
                "per_subject_mismatches": elig_mismatches,
            },
            "crossover_check": {
                "rule": "H7-R7",
                "n_checked": crossover_checked,
                "n_byte_identical_to_h1_imposter": crossover_identical,
            },
            "per_subject": h7_report,
        },
        "guards": {
            "run_on_every_prompt": [
                "R.assert_redacted(subject variants) on every arm",
                "R.assert_redacted(donor variants) on the imposter arms",
                "R.surviving_variants == 0 (subject, and donor where present)",
                "named arm == its redacted counterpart plus one name line",
                "R.assert_no_answer_leak on every grounded arm",
                "zero-information arms carry no excerpt block",
                "OE.assert_open_ended: frozen tail present, no forced-choice "
                "residue",
                "grounding speech words <= the 2,000-word budget",
                "instruction tail sha == the frozen tail sha",
            ],
            "n_renders_attempted": n_attempted,
            "n_renders_excluded": len(failures),
            "exclusion_rate": round(exclusion_rate, 6),
            "stop_rate": GUARD_EXCLUSION_STOP_RATE,
            "stopped": False,
            "failures": failures,
            "excluded_items_by_subject": {
                e["canonical_id"]: e["n_items_excluded"] for e in per_subject
                if e["n_items_excluded"]},
            "subjects_dropped_entirely": dropped_subjects,
            "twin_free_check": twin_check,
        },
        "same_event_leak_scan": {
            "what": "DESCRIPTIVE contamination scan, no exclusion attached: "
                    "share of the test interview's 10-word guest shingles that "
                    "also appear in one grounding transcript. Frozen "
                    "convention (stage2_render._norm_tokens, SHINGLE_WORDS).",
            "why": (
                "The per-item answer-leak assert only sees the 2,000-word "
                "rendered block, so a re-aired interview whose overlap falls "
                "outside the budget window would leave no trace. This scan "
                "sees the whole grounding side."),
            "n_subjects_scanned": len(leak_scan),
            "n_subjects_with_any_overlap": sum(
                1 for s in leak_scan
                if s["max_share_of_test_in_one_grounding_transcript"] > 0),
            "subjects_over_10pct": sorted(
                (s["canonical_id"],
                 s["max_share_of_test_in_one_grounding_transcript"])
                for s in leak_scan
                if s["max_share_of_test_in_one_grounding_transcript"] > 0.10),
            "finding": (
                "C02502 is a re-aired interview: CNN-381362 (2019-09-25) "
                "replays 47% of the test transcript CNN-388758 (2019-12-25, "
                "Christmas Day) on the same programme. The two sit in "
                "different dedup clusters, so D2's same-event guard never saw "
                "them; the answer-leak assert caught it downstream and every "
                "one of the subject's 11 items was excluded, dropping the "
                "subject. Reported because the clustering, not the split "
                "logic, is what missed it -- that is an owner call, not this "
                "file's."),
            "per_subject": [s for s in leak_scan
                            if s["max_share_of_test_in_one_grounding_transcript"]
                            > 0],
        },
        "donors": {
            "rule_id": "D7-CONF",
            "pairs_file": rel(out_dir / "imposter_pairs_confirm.json"),
            "pairs_sha256": sha256_file(
                out_dir / "imposter_pairs_confirm.json"),
            "n_distinct_donors": len(set(pairs.values())),
            "n_eligible_donors": pairs_doc["n_eligible_donors"],
            "frozen_bank_sha256": pairs_doc["confirmatory"][
                "frozen_bank_sha256"],
            "permitted_bank_sha256": pairs_doc["confirmatory"][
                "permitted_bank_sha256"],
            "n_removed_as_study_subjects": pairs_doc["confirmatory"][
                "n_removed_as_study_subjects"],
            "artifacts": {k: v for k, v in donors.items()
                          if not k.startswith("_")},
            "pairs": pairs,
        },
        "chunking": {
            "target_prompts_per_chunk": CHUNK_TARGET_PROMPTS,
            "rule": "whole subjects only; a chunk is closed before a subject "
                    "that would take it past the target. Blocks are "
                    "independent and may be submitted in parallel.",
            **written,
        },
        "files": {
            "items": rel(out_dir / "items_confirm.jsonl"),
            "items_sha256": sha256_file(out_dir / "items_confirm.jsonl"),
        },
        "submission": {
            "submitted": False,
            "sbatch_written": False,
            "note": "STOP. Nothing here has been submitted or called. The "
                    "sbatch is deliberately NOT written: submission is the "
                    "next owner-gated step and the derived H7 rules above are "
                    "reviewed first.",
        },
        "cost": {"api_calls": 0, "gpu_hours": 0.0, "cost_usd": 0.0,
                 "note": "CPU only. No model call, no network fetch beyond the "
                         "local corpus file, no GPU. $0.00."},
    }
    S.write_json(out_dir / "render_manifest.json", manifest)
    S.write_json(out_dir / "render_run.json", {
        "banner": BANNER,
        "generated_utc": now(),
        "runtime_secs": round(time.time() - started, 2),
        "n_donor_artifacts_built_this_run": donors["_n_built_this_run"],
        "retired_donor_dirs_pruned_this_run": donors["_retired_donor_dirs_pruned"],
        "manifest_sha256": sha256_file(out_dir / "render_manifest.json"),
        "note": "The only artifact with wall-clock fields. render_manifest.json "
                "and every prompt file are byte-identical on a re-run.",
    })

    print(f"[render] items {len(item_rows)}  logical renders {n_logical}  "
          f"unique prompts {n_unique} (H1 {n_unique_h1} / H7 {n_unique_h7})")
    print(f"[render] guards: {len(failures)} of {n_attempted} excluded "
          f"({exclusion_rate:.2%}, stop at {GUARD_EXCLUSION_STOP_RATE:.0%})")
    print(f"[render] H7 bin renders {manifest['h7']['n_bin_renders']} over "
          f"{manifest['h7']['n_subjects_with_at_least_one_bin']} subjects; "
          f"sweep subset {len(sweep_subset)}")
    print(f"[render] {written['n_chunks']} chunks -> {rel(out_dir/'prompts')} "
          f"and {rel(out_dir/'node')}")
    print(f"[render] manifest -> {rel(out_dir/'render_manifest.json')}  "
          "NOT submitted, $0.00")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
