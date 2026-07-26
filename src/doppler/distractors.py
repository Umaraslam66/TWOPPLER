"""SPEC D5 (entity heuristic) + D6 (distractor bank and per-item selection).

The point of D6 is that a wrong option must not be *findable* by anything
except knowing the person. So each distractor is a real answer, given by a
real person, to a similar question, at a similar length, with a similar amount
of named-entity clutter. What is left to distinguish the true answer is the
content — which is what Stage 2 is trying to measure.

Three controls, all from Amendment A4:

- **length**: distractors sit within +-20% of the true answer's word count, so
  "pick the longest" is not a strategy;
- **entity density** (D5): distractors come from the same density bucket, so
  "pick the one stuffed with names and numbers" is not a strategy;
- **topic**: distractors answer the most similar donor questions in the bank,
  so "pick the one that is about the right subject at all" is not a strategy.

The entity-stripped variant of every option set is emitted alongside, for T6's
adversarial re-score (A4.3) — that check is NOT done here.

sklearn is imported lazily, inside the one function that ranks candidates, so
the D5 helpers stay importable on a compute node with no sklearn (the same
constraint stage2_render.py works under).
"""

from __future__ import annotations

import hashlib
import random
import re

from doppler.qa_extract import extract_qa
from doppler.stage2_data import (
    SCAN_CACHE, RAW_JSON, eligible_subjects, extract_turns, fetch_records,
    load_guest_words, _cluster_representative,
)

BANK_SEED = 48
N_DONORS = 200

# ---------------------------------------------------------------------------
# D5 — entity heuristic
#
# Pilot-grade and deliberately dumb: capitalisation, digits, $ and %. Real NER
# is a bar-lock decision, not an implementation choice. Every reading of the
# SPEC that had to be pinned down is named in the docstrings below.
#
# D5-r2 (SPEC v1.4, orchestrator-approved on T2's evidence) closes the two
# ways the first reading over-counted:
#
# (a) The pronoun "I" is a capitalised token, so mid-sentence it used to count
#     as an entity. On the first pilot bank (653 rows) I/I'm/I've were 625 of
#     the single-token entity spans against 65 for the next real entity
#     ("U.S"); 46% of rows affected and 14% in the wrong bucket. The density
#     was partly measuring how often the speaker says "I" -- a style signal,
#     not a name signal. The I family is now never an entity token.
#
# (b) Spans used to run across sentence boundaries, so "Absolutely. He" was a
#     two-token span and therefore an entity, and got stripped to "[NAME]".
#     39% of rows had at least one such span. Spans now break at a sentence
#     boundary, which leaves both halves as lone sentence-initial capitals and
#     so excludes both.
#
# Bucket boundaries are unchanged. Everything else in D5 stands.
# ---------------------------------------------------------------------------

#: SPEC D5 bucket edges. Z = almost no entities, L = some, H = dense.
BUCKET_LOW = 0.02
BUCKET_HIGH = 0.08

#: Which buckets may substitute for which, once the ladder allows it.
ADJACENT_BUCKETS = {"Z": {"Z", "L"}, "L": {"Z", "L", "H"}, "H": {"L", "H"}}

_CAP_RE = re.compile(r"[A-Z][\w'’.-]*")
_LEAD_PUNCT = "\"'“”‘’([{-–—*"
_TRAIL_PUNCT = ",.;:!?)]}\"'“”‘’-–—*"
_SENT_END_CHARS = ".!?"

#: SPEC D5-r2(a): the first-person pronoun family, never an entity token.
#: Case-exact -- "I" is the pronoun, "i" is not, and neither is "IM".
#: Both apostrophes are accepted because they are the same word however the
#: transcriber typed it (this corpus uses ASCII only; the D5 token class
#: already allows the typographic one).
I_FORMS = frozenset(
    ["I"] + [f"I{a}{s}" for a in ("'", "’") for s in ("m", "ve", "d", "ll")])


def _split_token(tok: str) -> tuple[str, str, str]:
    """(leading punctuation, core, trailing punctuation) for one token.

    Quotes and brackets around a word must not stop it being recognised as a
    name, and must not be swallowed when the word is replaced. ``"Egypt,`` is
    a leading ``"``, a core ``Egypt`` and a trailing ``,``.
    """
    i, j = 0, len(tok)
    while i < j and tok[i] in _LEAD_PUNCT:
        i += 1
    while j > i and tok[j - 1] in _TRAIL_PUNCT:
        j -= 1
    return tok[:i], tok[i:j], tok[j:]


def _is_capitalised(core: str) -> bool:
    """SPEC D5(a): the token matches ``[A-Z][\\w'’.-]*`` at its start."""
    return bool(core) and _CAP_RE.match(core) is not None


def _is_placeholder(lead: str, core: str, trail: str) -> bool:
    """``[NAME]`` / ``[NUMBER]`` are this module's own output, not entities.

    Without this, stripping twice would turn ``[NAME]`` into ``[[NAME]]`` —
    ``NAME`` is a capitalised token like any other. Making the operation
    idempotent means a caller that strips an already-stripped option set gets
    the same text back instead of quietly corrupting it.
    """
    return core in ("NAME", "NUMBER") and lead.endswith("[") \
        and trail.startswith("]")


def _is_number(core: str) -> bool:
    """SPEC D5(b) and (c).

    (b) a number with >= 2 digits — read as "the token carries at least two
    digit characters", so ``1,300``, ``2011`` and ``9/11`` all count and a
    bare ``5`` does not; (c) any ``$`` or ``%`` amount, which is why ``$5``
    and ``5%`` count on one digit.
    """
    digits = sum(ch.isdigit() for ch in core)
    if digits >= 2:
        return True
    return digits >= 1 and ("$" in core or "%" in core)


def is_abbreviation(core: str) -> bool:
    """SPEC D5-r3: would a "." after this token be an abbreviation dot?

    Three cases, exactly as v1.6 lists them: the dotted stem is a known
    honorific (``Mr``, ``Dr``, ``Gen`` — the same set stage2_data strips off
    speaker labels), the token already carries an internal dot (``U.S``,
    ``N.Y``), or it is a single initial (``R.``).

    Not covered, deliberately: ``St.``. "ST" is not in HONORIFIC, has no
    internal dot and is not a single initial, so ``St. Petersburg`` still
    splits. Adding it would mean extending HONORIFIC or inventing a fourth
    case, and neither is in v1.6. Reported, not patched.
    """
    from doppler.stage2_data import HONORIFIC

    stem = core.replace(".", "")
    if not stem:
        return False
    return stem.upper() in HONORIFIC or "." in core or len(stem) == 1


def _ends_sentence(core: str, trail: str) -> bool:
    """Does this token close a sentence? (SPEC D5-r2(b) as amended by D5-r3.)

    ``!`` and ``?`` are unambiguous. A ``.`` is not: it ends a sentence or it
    marks an abbreviation, and D5-r3 rules that an abbreviation wins.

    That ruling has a price, and it is the right way round. "in the U.S.
    Nobody noticed" now reads as one span and loses "Nobody" to ``[NAME]``,
    which costs a little density accuracy. The alternative left real surnames
    sitting in the entity-stripped variant ("Mr. Morsi" -> "[NAME]. Morsi"),
    which breaks a pre-registered control (A4.2). Density noise is cheaper
    than a leak.
    """
    tail = core[-1:] + trail
    if any(ch in "!?" for ch in tail):
        return True
    if "." not in tail:
        return False
    return not is_abbreviation(core)


def _analyse(text: str):
    """Tokenise once and mark up entities. Shared by density and stripping.

    Returns (tokens, spans, numbers) where ``tokens`` is the list of
    (lead, core, trail) triples, ``spans`` is the list of (start, stop) index
    pairs for the capitalised spans that COUNT, and ``numbers`` is the set of
    indices of number tokens.

    A capitalised span is a run of consecutive capitalised tokens that does not
    cross a sentence boundary (SPEC D5-r2(b)). It counts unless it is *solely
    sentence-initial* — that is, unless it is a single token sitting at the
    start of a sentence, where the capital says nothing but "new sentence". A
    multi-token span counts even at a sentence start, because the second
    capital is not explained by punctuation.

    The first-person pronoun family never counts as capitalised at all (SPEC
    D5-r2(a)), so it can neither be an entity nor hold a span together: in
    "met Rex I think", "Rex" and "think" are not one span.
    """
    raw = (text or "").split()
    tokens = [_split_token(t) for t in raw]
    placeholder = [_is_placeholder(*t) for t in tokens]
    caps = [_is_capitalised(core) and not placeholder[k]
            and core not in I_FORMS
            for k, (_, core, _) in enumerate(tokens)]

    sentence_start = [False] * len(tokens)
    if tokens:
        sentence_start[0] = True
    for i in range(1, len(tokens)):
        _, core, trail = tokens[i - 1]
        if _ends_sentence(core, trail):
            sentence_start[i] = True

    spans = []
    i = 0
    while i < len(tokens):
        if not caps[i]:
            i += 1
            continue
        j = i + 1
        # A new sentence ends the span, however the capitals run on.
        while j < len(tokens) and caps[j] and not sentence_start[j]:
            j += 1
        if not (j - i == 1 and sentence_start[i]):
            spans.append((i, j))
        i = j

    in_span = {k for a, b in spans for k in range(a, b)}
    numbers = {k for k, (_, core, _) in enumerate(tokens)
               if k not in in_span and not placeholder[k] and _is_number(core)}
    return tokens, spans, numbers


def entity_density(text: str) -> float:
    """SPEC D5: entity tokens / total whitespace tokens. 0.0 for empty text."""
    tokens, spans, numbers = _analyse(text)
    if not tokens:
        return 0.0
    n_entity = sum(b - a for a, b in spans) + len(numbers)
    return n_entity / len(tokens)


def density_bucket(density: float) -> str:
    """SPEC D5 buckets: Z 0..0.02, L 0.02..0.08, H > 0.08.

    Read with inclusive upper edges, which is the only reading consistent with
    H being strictly ``> 0.08``: Z is d <= 0.02, L is 0.02 < d <= 0.08.
    """
    if density <= BUCKET_LOW:
        return "Z"
    if density <= BUCKET_HIGH:
        return "L"
    return "H"


def bucket_of(text: str) -> str:
    return density_bucket(entity_density(text))


def strip_entities(text: str) -> str:
    """SPEC D5: capitalised spans -> ``[NAME]``, numbers -> ``[NUMBER]``.

    The same spans the density counts, so a sentence-initial ``The`` survives
    and a mid-sentence ``Egypt`` does not. Surrounding punctuation is kept
    (``Egypt,`` -> ``[NAME],``) so the text stays readable; whitespace is
    normalised to single spaces, which is harmless because this variant is a
    scoring aid, never a rendered prompt.
    """
    tokens, spans, numbers = _analyse(text)
    if not tokens:
        return ""
    span_start = {a: b for a, b in spans}
    out, i = [], 0
    while i < len(tokens):
        if i in span_start:
            stop = span_start[i]
            lead = tokens[i][0]
            trail = tokens[stop - 1][2]
            out.append(f"{lead}[NAME]{trail}")
            i = stop
            continue
        lead, core, trail = tokens[i]
        if i in numbers:
            out.append(f"{lead}[NUMBER]{trail}")
        else:
            out.append(lead + core + trail)
        i += 1
    return " ".join(out)


# ---------------------------------------------------------------------------
# D6 — the bank
# ---------------------------------------------------------------------------

def sample_donor_ids(pool: list[dict], dev_ids, seed: int = BANK_SEED,
                     n_donors: int = N_DONORS) -> list[str]:
    """SPEC D6: ``random.Random(48).sample`` over the sorted eligible ids.

    Dev subjects are excluded, all of them — including any retired for Q-A.
    A dev subject is burned forever and can never come back as a donor; that
    would make a distractor an answer the twin's own arm might have seen.
    Returns the ids in the order ``sample`` produced them; that order is
    reproducible and is what gets recorded.
    """
    dev = set(dev_ids)
    ids = sorted(r["canonical_id"] for r in eligible_subjects(pool)
                 if r["canonical_id"] not in dev)
    if len(ids) < n_donors:
        raise ValueError(f"only {len(ids)} eligible donors, need {n_donors}")
    return random.Random(seed).sample(ids, n_donors)


def latest_cluster(subject_row: dict, guest_words: dict | None = None) -> dict | None:
    """The donor's LATEST cluster representative transcript (SPEC D6 via D2).

    Same rules as D2's ``test`` pick — substantive transcripts only, grouped by
    cluster_id, cluster date = earliest member date, representative = most
    guest words with the smallest transcript_id breaking ties, latest cluster
    date wins with the largest representative id breaking ties.

    Deliberately NOT ``chronological_split``: that one also insists on at least
    one strictly-earlier grounding cluster, which is a rule about dev subjects,
    not about donors. A one-interview donor is a perfectly good distractor
    source. Returns None when the donor has no substantive transcript at all.
    """
    guest_words = guest_words or {}
    clusters: dict[str, list[dict]] = {}
    for e in subject_row["transcripts"]:
        if e["substantive"]:
            clusters.setdefault(e["cluster_id"], []).append(e)
    if not clusters:
        return None
    built = []
    for cid in sorted(clusters):
        members = clusters[cid]
        rep = _cluster_representative(members, guest_words)
        built.append({
            "cluster_id": cid,
            "transcript_id": rep["transcript_id"],
            "date": min(e["date"] for e in members),
            "program": rep["program"],
        })
    latest = max(e["date"] for e in built)
    at_latest = sorted((e for e in built if e["date"] == latest),
                       key=lambda e: e["transcript_id"])
    return at_latest[-1]


def bank_row(item: dict) -> dict:
    """One qa_extract item -> one bank row (SPEC D6 schema, exactly)."""
    density = entity_density(item["answer"])
    return {
        "question": item["question"],
        "answer": item["answer"],
        "answer_words": item["answer_words"],
        "entity_density": density,
        "bucket": density_bucket(density),
        "source_canonical_id": item["canonical_id"],
        "source_transcript_id": item["transcript_id"],
    }


def build_bank(pool: list[dict], dev_ids, seed: int = BANK_SEED,
               n_donors: int = N_DONORS, fetch_fn=None,
               guest_words=None, on_donor=None) -> list[dict]:
    """SPEC D6. Build the distractor bank from ``n_donors`` sampled subjects.

    ``fetch_fn(transcript_ids) -> {transcript_id: record}`` is injected so the
    tests can run without the 4.45 GB corpus; the driver passes
    ``stage2_data.fetch_records``, which does the whole thing in one streaming
    pass. ``guest_words`` maps canonical_id -> {transcript_id: words} and only
    decides which transcript represents a re-aired cluster; it is read from the
    v2 scan cache by the driver.

    ``on_donor(canonical_id, transcript_id, items, note)`` is an optional
    progress/diagnostic hook; ``items`` is the donor's extracted Q-A items, so
    the caller can count truncations and empty donors without re-extracting.

    Rows come out grouped by donor in sample order, items in turn order, which
    makes the file diffable and gives selection a stable tie-break.
    """
    fetch_fn = fetch_fn or (lambda ids: fetch_records(ids, RAW_JSON))
    by_id = {r["canonical_id"]: r for r in pool}
    donor_ids = sample_donor_ids(pool, dev_ids, seed=seed, n_donors=n_donors)

    if guest_words is None:
        guest_words = load_guest_words([by_id[c] for c in donor_ids], SCAN_CACHE)

    wanted: dict[str, str] = {}          # canonical_id -> transcript_id
    for cid in donor_ids:
        chosen = latest_cluster(by_id[cid], guest_words.get(cid, {}))
        if chosen is None:
            if on_donor:
                on_donor(cid, None, [], "no substantive transcript")
            continue
        wanted[cid] = chosen["transcript_id"]

    records = fetch_fn(sorted(set(wanted.values())))

    bank: list[dict] = []
    for cid in donor_ids:
        tid = wanted.get(cid)
        if tid is None:
            continue
        record = records.get(tid)
        if record is None:
            if on_donor:
                on_donor(cid, tid, [], "transcript not returned by fetch_fn")
            continue
        turns = extract_turns(record, by_id[cid])
        items = extract_qa(turns, cid, tid)
        bank.extend(bank_row(it) for it in items)
        if on_donor:
            on_donor(cid, tid, items, None)
    return bank


def bank_stats(bank: list[dict]) -> dict:
    """Descriptive stats for the report; no decisions are made from these."""
    from collections import Counter

    lens = sorted(r["answer_words"] for r in bank)
    dens = sorted(r["entity_density"] for r in bank)

    def pct(xs, p):
        if not xs:
            return 0.0
        return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]

    donors = Counter(r["source_canonical_id"] for r in bank)
    return {
        "n_rows": len(bank),
        "n_donor_subjects_with_items": len(donors),
        "buckets": dict(Counter(r["bucket"] for r in bank)),
        "answer_words": {
            "min": lens[0] if lens else 0, "p25": pct(lens, 0.25),
            "median": pct(lens, 0.5), "p75": pct(lens, 0.75),
            "max": lens[-1] if lens else 0,
            "mean": round(sum(lens) / len(lens), 1) if lens else 0.0,
        },
        "entity_density": {
            "min": round(dens[0], 4) if dens else 0.0,
            "median": round(pct(dens, 0.5), 4),
            "max": round(dens[-1], 4) if dens else 0.0,
        },
        "items_per_donor_max": max(donors.values()) if donors else 0,
    }


# ---------------------------------------------------------------------------
# D6 — per-item selection
# ---------------------------------------------------------------------------

#: SPEC D6 relaxation ladder: (length tolerance, adjacent buckets allowed).
#: Rung 0 is the pre-registered control; each later rung gives up exactly one
#: notch of it. "Different subject" is never on this ladder and never will be.
RELAX_LADDER = [
    (0.20, False),
    (0.30, False),
    (0.30, True),
    (0.50, True),
]


def _eligible(bank: list[dict], canonical_id: str, true_words: int,
              true_bucket: str, tol: float, adjacent: bool) -> list[tuple[int, dict]]:
    lo, hi = true_words * (1.0 - tol), true_words * (1.0 + tol)
    allowed = ADJACENT_BUCKETS[true_bucket] if adjacent else {true_bucket}
    return [(i, r) for i, r in enumerate(bank)
            if r["source_canonical_id"] != canonical_id
            and lo <= r["answer_words"] <= hi
            and r["bucket"] in allowed]


def rank_by_question_similarity(question: str,
                                candidates: list[tuple[int, dict]],
                                bank_questions: list[str]) -> list[tuple[float, int, dict]]:
    """SPEC D6 ranking. Return (cosine, bank_index, row) best first.

    TfidfVectorizer over word 1-2 grams, lowercased, fit on the bank's
    questions plus the query, exactly as D6 says. TF-IDF rows come out L2
    normalised, so the dot product IS the cosine.

    Ties are broken by source_canonical_id, then source_transcript_id, then
    bank position — never by dict or float ordering — so the same bank and the
    same query always give the same three distractors in the same order.
    """
    if not candidates:
        return []
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), lowercase=True)
    matrix = vec.fit_transform(list(bank_questions) + [question])
    query = matrix[-1]
    cand = vec.transform([r["question"] for _, r in candidates])
    sims = (cand @ query.T).toarray().ravel()

    scored = [(float(sims[k]), idx, row) for k, (idx, row) in enumerate(candidates)]
    scored.sort(key=lambda s: (-s[0], s[2]["source_canonical_id"],
                               s[2]["source_transcript_id"], s[1]))
    return scored


def shuffle_seed(item_id: str) -> int:
    """SPEC D6: ``int(sha256(item_id)[:8], 16)``. Per item, so it is stable."""
    return int(hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:8], 16)


def select_distractors(item: dict, bank: list[dict], n: int = 3) -> dict:
    """SPEC D6. One qa item + the bank -> its option set.

    Walks the relaxation ladder only as far as it has to: the first rung that
    yields at least ``n`` candidates is the one used, and the rung is recorded
    so the report can say how often the pre-registered control actually held.
    The true answer is inserted, the four options are shuffled by a seed
    derived from the item_id, and ``correct_index`` is read off *after* the
    shuffle from the one option marked ``true`` — never assumed.
    """
    true_words = item["answer_words"]
    true_density = entity_density(item["answer"])
    true_bucket = density_bucket(true_density)
    bank_questions = [r["question"] for r in bank]

    chosen: list[tuple[float, int, dict]] = []
    rung = len(RELAX_LADDER) - 1
    for k, (tol, adjacent) in enumerate(RELAX_LADDER):
        cands = _eligible(bank, item["canonical_id"], true_words, true_bucket,
                          tol, adjacent)
        if len(cands) >= n or k == len(RELAX_LADDER) - 1:
            ranked = rank_by_question_similarity(item["question"], cands,
                                                 bank_questions)
            chosen, rung = ranked[:n], k
            break

    flags = [f"relax_rung_{rung}"]
    if len(chosen) < n:
        flags.append("insufficient_candidates")

    options = [{
        "text": item["answer"],
        "kind": "true",
        "source_canonical_id": item["canonical_id"],
        "source_transcript_id": item["transcript_id"],
        "answer_words": true_words,
        "entity_density": true_density,
        "question_similarity": None,    # it IS the question; keys stay uniform
    }]
    for sim, _, row in chosen:
        options.append({
            "text": row["answer"],
            "kind": "distractor",
            "source_canonical_id": row["source_canonical_id"],
            "source_transcript_id": row["source_transcript_id"],
            "answer_words": row["answer_words"],
            "entity_density": row["entity_density"],
            "question_similarity": round(sim, 6),
        })

    random.Random(shuffle_seed(item["item_id"])).shuffle(options)
    correct = [i for i, o in enumerate(options) if o["kind"] == "true"]
    if len(correct) != 1:
        raise AssertionError(f"{item['item_id']}: {len(correct)} true options")
    # Never-same-subject invariant, asserted rather than trusted.
    for opt in options:
        if opt["kind"] == "distractor" and \
                opt["source_canonical_id"] == item["canonical_id"]:
            raise AssertionError(
                f"{item['item_id']}: distractor from the subject's own transcripts")

    return {
        "item_id": item["item_id"],
        "options": options,
        "correct_index": correct[0],
        "relax_rung": rung,
        "flags": flags,
        "options_stripped": [strip_entities(o["text"]) for o in options],
    }


__all__ = [
    "BANK_SEED", "N_DONORS", "BUCKET_LOW", "BUCKET_HIGH", "ADJACENT_BUCKETS",
    "RELAX_LADDER",
    "entity_density", "density_bucket", "bucket_of", "strip_entities",
    "sample_donor_ids", "latest_cluster", "bank_row", "build_bank",
    "bank_stats", "rank_by_question_similarity", "shuffle_seed",
    "select_distractors",
]
