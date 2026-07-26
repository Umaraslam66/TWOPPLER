"""Same-domain imposter donors (SPEC D7, Amendment A1).

The imposter arm asks the same question with the same template as the twin arm,
but grounds the model on a *different* person's past interviews. This module
picks that other person — deterministically, from the same 200-subject bank
sample the distractor bank draws from (SPEC D6), by TF-IDF cosine similarity of
grounding-side guest text.

What lives here
---------------
- ``donor_sample``      the shared seed-48 sample of 200 bank subjects
- ``grounding_text``    one subject's concatenated guest-role grounding text
- ``collect_donor_texts`` the same for a whole donor list, in one corpus pass
- ``name_conflict``     the name-similarity exclusion of SPEC D7
- ``tfidf_vectors`` / ``cosine``  the similarity itself
- ``match_donors``      the D7 argmax, returning the imposter_pairs.json doc

Two things are worth knowing before reading the code.

**The donor sample is derived, never read.** T2 (distractor bank) and T3
(this module) both need the same 200 ids and are built in parallel, so each
derives the sample independently from the pool with ``random.Random(48)`` and
the two must agree. ``donor_sample`` is that derivation and
``donor_sample_sha256`` in the output artifact is how the agreement is checked.
Note that ``Random.sample(ids, 200)`` and ``Random.shuffle(ids)[:200]`` return
almost disjoint sets for this pool — SPEC D6 says "seeded sample", D1 says
"shuffle" where it means shuffle, so this is ``sample``.

**Pure standard library on purpose**, same reason as stage2_data.py: the file
can be copied to a compute node next to a driver without dragging a scientific
stack behind it, and the matching rule must not be able to drift between
copies. The TF-IDF here reproduces ``sklearn.feature_extraction.text.
TfidfVectorizer`` defaults exactly — same token pattern ``(?u)\\b\\w\\w+\\b``,
same smoothed idf ``ln((1+n)/(1+df)) + 1``, same L2 row normalization — and
tests/test_imposter2.py asserts that parity against the real thing whenever
sklearn happens to be importable (it is not installed in this repo's env).
"""

from __future__ import annotations

import difflib
import hashlib
import math
import random
import re
from collections import Counter
from pathlib import Path

from doppler.stage2_data import (
    PILOT_DIR,
    RAW_JSON,
    SCAN_CACHE,
    chronological_split,
    eligible_subjects,
    extract_turns,
    iter_wanted_raw,
    load_guest_words,
    name_key,
    read_jsonl,
    subject_dir,
    word_count,
)

# ---------------------------------------------------------------------------
# Frozen constants (SPEC D6 sample, SPEC D7 matching)
# ---------------------------------------------------------------------------

DONOR_SEED = 48
N_DONORS = 200
#: A donor needs this many words of grounding-side guest text to be eligible.
WORD_FLOOR = 2500
#: difflib ratio at or above which two names count as the same person.
NAME_RATIO = 0.7

METHOD = (
    "SPEC D7. Each subject is represented by its concatenated guest-role text "
    "from GROUNDING clusters only (dev subjects: the committed "
    "grounding_turns.jsonl; donors: D2 applied to their pool row, guest turns "
    "of every grounding cluster's representative transcript). Donor pool = the "
    "seed-48 sample of 200 eligible subjects (qualifies AND clean AND NOT "
    "ambiguous_identity), drawn with random.Random(48).sample over the "
    "lexicographically sorted eligible ids with ALL dev-subject ids removed "
    "first; the same derivation the distractor bank uses. Eligible donors are "
    "those with >= 2500 words of grounding text and no name conflict with the "
    "subject (shared name token, or difflib ratio >= 0.7 between any pair of "
    "name variants, honorific-stripped and casefolded). Similarity = cosine "
    "between L2-normalised TF-IDF vectors, word unigrams, lowercase, token "
    "pattern (?u)\\b\\w\\w+\\b, smoothed idf ln((1+n)/(1+df))+1, fitted once on "
    "all eligible donor documents plus all subject documents. donor(X) = argmax "
    "similarity, rounded to 6 decimals, ties broken by lexicographic "
    "canonical_id. runner_up_top5 holds ranks 2-6 (the winner is in pairs)."
)

# Name particles and generational suffixes never count as a shared name token:
# "de", "van" and "Jr" are not evidence that two people are the same person.
PARTICLES = frozenset({
    "al", "bin", "ben", "bint", "da", "das", "de", "del", "della", "der",
    "des", "di", "do", "dos", "du", "el", "ibn", "la", "le", "los", "mac",
    "mc", "san", "santa", "st", "ter", "van", "von", "zu",
    "jr", "sr", "ii", "iii", "iv", "phd", "md", "esq",
})


# ---------------------------------------------------------------------------
# The shared donor sample (SPEC D6, used by D7)
# ---------------------------------------------------------------------------

def donor_sample(pool: list[dict], dev_ids, seed: int = DONOR_SEED,
                 n: int = N_DONORS) -> list[str]:
    """The 200-subject bank sample, in draw order.

    Eligible = SPEC D1 eligibility (qualifies AND clean AND NOT
    ambiguous_identity), which is the same predicate the dev draw uses. Ids are
    sorted lexicographically, EVERY dev-subject id is removed (dev subjects are
    never donors — that keeps the arms independent), and
    ``random.Random(seed).sample`` takes n of what is left.

    T2 derives this same list independently for the distractor bank. If the two
    ever disagree, the pilot's imposter arm and its distractors are drawn from
    different populations, so ``sample_sha256`` of this list is recorded in the
    output artifact for cross-checking.
    """
    dev = set(dev_ids)
    ids = sorted(r["canonical_id"] for r in eligible_subjects(pool)
                 if r["canonical_id"] not in dev)
    if len(ids) < n:
        raise ValueError(f"donor sample wants {n} ids, only {len(ids)} eligible "
                         "subjects remain after removing the dev subjects")
    return random.Random(seed).sample(ids, n)


def sample_sha256(ids) -> str:
    """Order-independent fingerprint of an id list, for cross-task checking."""
    return hashlib.sha256(",".join(sorted(ids)).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Grounding-side representation (SPEC D7 "concatenated guest-role text")
# ---------------------------------------------------------------------------

def guest_text(turns) -> str:
    """Guest-role turn texts of one transcript, in turn order, newline-joined."""
    return "\n".join(t["text"] for t in turns
                     if t.get("role") == "guest" and (t.get("text") or "").strip())


def grounding_text(cid: str, pool=None, records=None, split=None,
                   guest_words=None, pilot_dir=PILOT_DIR) -> str:
    """Concatenated guest-role text from one subject's GROUNDING clusters.

    Two sources, one meaning:

    - No ``records``: read the committed
      ``subjects/<cid>/grounding_turns.jsonl``. That is the dev-subject path,
      and it uses exactly the turns T1 wrote (D3 + D3.1 surname resolution).
    - With ``pool`` and ``records`` ({transcript_id: raw record}): derive it,
      which is the donor path. The donor's grounding side is SPEC D2 applied to
      its own pool row — every cluster except the latest-dated one, with any
      cluster sharing the test date excluded — and the guest turns come from
      ``extract_turns`` with the donor as the subject.

    ``guest_words`` ({transcript_id: guest words}) only matters for donors whose
    cluster has more than one transcript (a re-airing); it picks the cluster
    representative, per D2.
    """
    if records is None:
        path = subject_dir(cid, pilot_dir) / "grounding_turns.jsonl"
        return guest_text(read_jsonl(path))

    row = _row(pool, cid)
    if split is None:
        split = chronological_split(row, guest_words or {})
    parts = []
    for entry in split["grounding"]:
        record = records.get(entry["transcript_id"])
        if record is None:
            raise KeyError(f"{cid}: grounding transcript "
                           f"{entry['transcript_id']} was not fetched")
        parts.append(guest_text(extract_turns(record, row)))
    return "\n\n".join(p for p in parts if p)


def _row(pool, cid: str) -> dict:
    for r in pool:
        if r["canonical_id"] == cid:
            return r
    raise KeyError(f"{cid} is not in the pool")


def donor_splits(donor_ids, pool, guest_words=None, cache_path=SCAN_CACHE):
    """{cid: split} for the donors, plus {cid: reason} for the ones D2 rejects.

    A donor is rejected when its row has no cluster strictly earlier than its
    latest one — a one-interview subject has no grounding side at all and
    therefore cannot ground an imposter prompt.
    """
    by_id = {r["canonical_id"]: r for r in pool}
    rows = [by_id[cid] for cid in donor_ids]
    if guest_words is None:
        guest_words = load_guest_words(rows, cache_path)
    splits, skipped = {}, {}
    for cid in donor_ids:
        try:
            splits[cid] = chronological_split(by_id[cid], guest_words.get(cid, {}))
        except ValueError as exc:
            skipped[cid] = str(exc)
    return splits, skipped


def collect_donor_texts(donor_ids, pool, raw_path=RAW_JSON, guest_words=None,
                        cache_path=SCAN_CACHE, keep_turns=()):
    """Grounding text for every donor, in ONE streaming pass over the corpus.

    Returns ``(texts, meta)`` where texts is {cid: grounding text} and meta
    carries the bookkeeping: which donors D2 rejected, which transcripts were
    read, which records were malformed, and the per-donor turn lists for the
    ids named in ``keep_turns`` (used to write the matched donors' turn files
    without a second pass when the caller already knows who it wants).

    One transcript can belong to two donors — panels happen — so the wanted map
    is transcript_id -> [donor ids], and each record is decoded once and given
    to every donor that claims it.
    """
    import json

    splits, skipped = donor_splits(donor_ids, pool, guest_words, cache_path)
    by_id = {r["canonical_id"]: r for r in pool}
    keep = set(keep_turns)

    wanted: dict[str, list[str]] = {}
    for cid, split in splits.items():
        for entry in split["grounding"]:
            wanted.setdefault(entry["transcript_id"], []).append(cid)

    pieces: dict[str, dict[str, str]] = {cid: {} for cid in splits}
    turns_out: dict[str, dict[str, list]] = {cid: {} for cid in keep}
    malformed: dict[str, str] = {}
    decoder = json.JSONDecoder()
    seen = set()

    for tid, raw in iter_wanted_raw(raw_path, set(wanted)):
        record, _ = decoder.raw_decode(raw.decode("utf-8"))
        if record.get("id") != tid:
            raise ValueError(f"record boundary error: marker said {tid}, "
                             f"decoded {record.get('id')}")
        seen.add(tid)
        for cid in wanted[tid]:
            try:
                turns = extract_turns(record, by_id[cid])
            except ValueError as exc:          # utt/speaker length mismatch
                malformed[f"{cid}:{tid}"] = str(exc)
                continue
            pieces[cid][tid] = guest_text(turns)
            if cid in keep:
                turns_out[cid][tid] = turns

    missing = set(wanted) - seen
    texts = {}
    for cid, split in splits.items():
        ordered = [pieces[cid].get(e["transcript_id"], "")
                   for e in split["grounding"]]
        texts[cid] = "\n\n".join(p for p in ordered if p)

    meta = {
        "splits": splits,
        "skipped_no_grounding": skipped,
        "n_transcripts_wanted": len(wanted),
        "n_transcripts_read": len(seen),
        "missing_transcripts": sorted(missing),
        "malformed": malformed,
        "turns": turns_out,
    }
    return texts, meta


# ---------------------------------------------------------------------------
# Name-similarity exclusion (SPEC D7)
# ---------------------------------------------------------------------------

def name_strings(row: dict) -> list[str]:
    """canonical_name plus every variant, de-duplicated, order preserved."""
    names = [row.get("canonical_name") or "", *(row.get("variants") or [])]
    return list(dict.fromkeys(n for n in names if n and n.strip()))


def name_keys(row: dict) -> set[str]:
    """Every accepted spelling as a comparison key (honorific-free, casefolded)."""
    return {k for k in (name_key(n) for n in name_strings(row)) if k}


def name_tokens(row: dict) -> set[str]:
    """Comparable name tokens: >= 2 characters, particles and suffixes dropped."""
    out = set()
    for key in name_keys(row):
        for token in key.split():
            if len(token) >= 2 and token not in PARTICLES:
                out.add(token)
    return out


def name_conflict(row_a: dict, row_b: dict, ratio: float = NAME_RATIO):
    """Do these two rows plausibly name the same person? (SPEC D7 exclusion)

    Returns ``(bool, reason)``. Two triggers, either is enough:

    - a shared name token ("Robert Harris" vs "Nina Harris" — a surname
      collision is exactly the case that would leak the subject's identity into
      an imposter prompt), particles and generational suffixes excluded;
    - ``difflib.SequenceMatcher`` ratio >= 0.7 between any pair of full name
      variants, which catches spelling drift ("Frederic Hof" / "Frederick
      Hoff") that no token comparison would.
    """
    shared = name_tokens(row_a) & name_tokens(row_b)
    if shared:
        return True, "shared name token: " + ", ".join(sorted(shared))
    best, pair = 0.0, None
    for ka in sorted(name_keys(row_a)):
        for kb in sorted(name_keys(row_b)):
            r = difflib.SequenceMatcher(None, ka, kb).ratio()
            if r > best:
                best, pair = r, (ka, kb)
    if best >= ratio:
        return True, f"difflib ratio {best:.3f} between {pair[0]!r} and {pair[1]!r}"
    return False, ""


# ---------------------------------------------------------------------------
# TF-IDF and cosine (sklearn TfidfVectorizer defaults, reimplemented)
# ---------------------------------------------------------------------------

#: sklearn's default token pattern: runs of >= 2 word characters.
TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def tfidf_vectors(docs) -> list[dict[str, float]]:
    """L2-normalised TF-IDF rows, one sparse dict per document.

    Reproduces TfidfVectorizer(lowercase=True, ngram_range=(1,1),
    smooth_idf=True, sublinear_tf=False, norm='l2'):
    ``tfidf = count * (ln((1 + n_docs) / (1 + df)) + 1)``, then each row is
    divided by its L2 norm. Fitting and transforming are one step here — the
    caller passes every document it wants compared, so no term can be out of
    vocabulary.

    Unigrams, not the 1-2 grams SPEC D6 uses for ranking short questions: these
    documents run to tens of thousands of words each and a bigram vocabulary of
    that corpus costs hundreds of megabytes in Python dicts for no topical
    signal a unigram model does not already carry.
    """
    counts = [Counter(tokenize(d)) for d in docs]
    n = len(counts)
    df: Counter = Counter()
    for c in counts:
        df.update(c.keys())
    idf = {t: math.log((1.0 + n) / (1.0 + d)) + 1.0 for t, d in df.items()}

    rows = []
    for c in counts:
        vec = {t: f * idf[t] for t, f in c.items()}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {t: v / norm for t, v in vec.items()}
        rows.append(vec)
    return rows


def cosine(a: dict, b: dict) -> float:
    """Cosine of two L2-normalised sparse rows, summed in sorted term order."""
    if len(b) < len(a):
        a, b = b, a
    total = 0.0
    for term in sorted(a):
        other = b.get(term)
        if other is not None:
            total += a[term] * other
    return max(0.0, min(1.0, total))


# ---------------------------------------------------------------------------
# The match (SPEC D7)
# ---------------------------------------------------------------------------

def match_donors(dev_subjects, pool, subject_texts: dict, donor_texts: dict,
                 word_floor: int = WORD_FLOOR, name_ratio: float = NAME_RATIO,
                 top_k: int = 5, generated_at: str | None = None) -> dict:
    """SPEC D7. Return the results/stage2_pilot/imposter_pairs.json document.

    ``dev_subjects`` is dev_subjects.json's ``subjects`` list (only
    ``canonical_id`` is read). ``subject_texts`` and ``donor_texts`` are
    {canonical_id: grounding text}; the donor map is the seed-48 sample.

    Hard guard first: no dev subject may appear in ``donor_texts``. A dev
    subject grounding another dev subject's imposter arm would couple the two
    arms, which is the one thing D7's donor-pool rule exists to prevent.

    Every subject is matched even if it is annotated ``burned_for_qa`` — the
    annotation retires a subject from Q-A, not from the study, and a pair costs
    nothing if its arm never runs.
    """
    dev_ids = [s["canonical_id"] if isinstance(s, dict) else s
               for s in dev_subjects]
    leaked = sorted(set(dev_ids) & set(donor_texts))
    if leaked:
        raise ValueError(f"dev subjects in the donor pool: {leaked}")

    donor_words = {cid: word_count(t) for cid, t in donor_texts.items()}
    eligible = sorted(cid for cid, w in donor_words.items() if w >= word_floor)
    if not eligible:
        raise ValueError("no donor clears the "
                         f"{word_floor}-word grounding floor")

    subjects = sorted(dev_ids)
    docs = eligible + subjects
    vectors = tfidf_vectors([donor_texts[c] for c in eligible]
                            + [subject_texts[c] for c in subjects])
    vec = dict(zip(docs, vectors))

    pairs, similarity, runners, excluded = {}, {}, {}, {}
    for cid in subjects:
        row = _row(pool, cid)
        blocked = []
        scored = []
        for donor in eligible:
            conflict, why = name_conflict(row, _row(pool, donor), name_ratio)
            if conflict:
                blocked.append({"donor": donor, "reason": why})
                continue
            scored.append((round(cosine(vec[cid], vec[donor]), 6), donor))
        if not scored:
            raise ValueError(f"{cid}: every eligible donor was excluded by name")
        # Rank on the rounded similarity that gets written to the artifact, so
        # the recorded numbers always explain the recorded order. Ties go to
        # the lexicographically smaller canonical_id (SPEC D7).
        scored.sort(key=lambda s: (-s[0], s[1]))
        pairs[cid] = scored[0][1]
        similarity[cid] = scored[0][0]
        runners[cid] = [[d, s] for s, d in scored[1:1 + top_k]]
        excluded[cid] = blocked

    used = sorted({*pairs.values(),
                   *(d for rs in runners.values() for d, _ in rs)})
    return {
        "method": METHOD,
        "generated_at": generated_at,
        "donor_seed": DONOR_SEED,
        "n_donor_sample": len(donor_texts),
        "donor_sample_sha256": sample_sha256(donor_texts),
        "word_floor": word_floor,
        "name_ratio": name_ratio,
        "n_eligible_donors": len(eligible),
        "pairs": pairs,
        "similarity": similarity,
        "runner_up_top5": runners,
        "subject_words": {c: word_count(subject_texts[c]) for c in subjects},
        "donor_words": {c: donor_words[c] for c in used},
        "excluded_by_name": {c: v for c, v in excluded.items() if v},
        "donors_recorded": used,
    }


def donor_text_path(cid: str, pilot_dir=PILOT_DIR) -> Path:
    return Path(pilot_dir) / "donor_texts" / f"{cid}.txt"


def donor_dir(cid: str, pilot_dir=PILOT_DIR) -> Path:
    return Path(pilot_dir) / "donors" / cid


__all__ = [
    "DONOR_SEED", "N_DONORS", "WORD_FLOOR", "NAME_RATIO", "METHOD", "PARTICLES",
    "donor_sample", "sample_sha256", "guest_text", "grounding_text",
    "donor_splits", "collect_donor_texts",
    "name_strings", "name_keys", "name_tokens", "name_conflict",
    "tokenize", "tfidf_vectors", "cosine", "match_donors",
    "donor_text_path", "donor_dir",
]
