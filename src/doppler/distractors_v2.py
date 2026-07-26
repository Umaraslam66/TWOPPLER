"""SPEC v1.8 D6-v2 — same-subject distractors for the Stage 2 pilot round 2.

Why this module exists. Pilot round 1 built every wrong option out of some OTHER
person's answer to some other question (SPEC D6). The zero-information arm then
solved 17 items out of 17: a model that knew nothing at all about the person
could win by picking the one option that was about the right topic. The forced
choice measured topical coherence, not a twin (pilot report finding 8.0).

The fix, decided by the owner (decision D-B): **every distractor is a real answer
the SAME subject gave in one of their OTHER interviews.** Speaker, register and
general subject matter are then controlled by construction, and the only thing
left to tell the four options apart is which answer this person gave to THIS
question — which is exactly what Stage 2 wants to measure.

Four rules, in the order they bite:

1. **Pool** (:func:`harvest_answer_pool`) — D4 Q-A extraction over every
   transcript of the subject EXCEPT the test cluster and any cluster D2 already
   excluded for sharing the test date. Substantive and non-substantive
   transcripts both count: a non-substantive transcript is one where the guest
   said relatively little, not one that belongs to somebody else, and it is
   never rendered into a prompt so it cannot leak.
2. **Anti-leak** (:func:`anti_leak_split`) — a candidate whose answer text
   overlaps the subject's RENDERED grounding block is dropped. Without this the
   twin arm could string-match a distractor against its own context and score
   for a reason that has nothing to do with modelling a person. The test is the
   frozen D8 guard (a): any shared 10-word shingle.
3. **Ambiguity** (:func:`too_close_to_true`) — a candidate that near-duplicates
   the true answer is dropped, because two correct options is not a forced
   choice. Same threshold and same word-set machinery D4 already uses to drop
   near-duplicate questions.
4. **A4 controls + ranking** (:func:`select_same_subject`) — length within
   +-20%, matching entity-density bucket, the same relaxation ladder as D6, then
   rank by TF-IDF question similarity and take the top 3. If three cannot be
   found the item is NOT built; there is no cross-person fallback.

Every distractor carries its question similarity so the owner can pick an
admission floor from the recorded numbers (:func:`similarity_floor_sweep`). This
module applies whatever floor it is given and defaults to 0.0 — freezing a
threshold is a bar-lock decision, not an implementation choice.

sklearn is imported lazily inside :class:`QuestionSimilarity`, so the pool and
filter helpers stay importable on a node with no sklearn.
"""

from __future__ import annotations

import hashlib

from doppler import stage2_render as R
from doppler.distractors import (
    ADJACENT_BUCKETS, RELAX_LADDER, density_bucket, entity_density,
    shuffle_seed, strip_entities,
)
from doppler.qa_extract import NEAR_DUP_JACCARD, extract_qa, jaccard, word_set

#: Number of distractors per item. Four options, one of them true.
N_DISTRACTORS = 3

#: Shingle length for the anti-leak test. The frozen D8 guard-(a) value; named
#: here so the rule can be quoted in a report without importing the renderer.
LEAK_SHINGLE_WORDS = R.SHINGLE_WORDS

#: Word-set Jaccard at or above which two answers are "the same answer".
#: D4's NEAR_DUP_JACCARD (0.8), reused rather than reinvented.
DUP_ANSWER_JACCARD = NEAR_DUP_JACCARD

#: Floors the sweep reports on. The BUILD runs at 0.0; which of these becomes
#: the admission rule is frozen by the owner at bar-lock.
SWEEP_FLOORS = (0.00, 0.02, 0.05, 0.10, 0.15, 0.20)

#: The pool rule, as one sentence, so artifacts can carry it verbatim.
POOL_RULE = (
    "Every transcript the subject appears in EXCEPT the test cluster and any "
    "cluster D2 excluded for sharing the test date; substantive and "
    "non-substantive alike. D4 Q-A extraction is run per transcript, so a "
    "pool row is one real answer the subject gave to one real question."
)

ANTI_LEAK_RULE = (
    f"A candidate is excluded when its answer shares any "
    f"{LEAK_SHINGLE_WORDS}-word shingle with the subject's rendered grounding "
    "block (the frozen D8 guard-(a) test, stage2_render.find_answer_leak). The "
    "test runs twice, raw-against-raw and redacted-against-redacted, and either "
    "hit excludes."
)

DUP_RULE = (
    f"A candidate whose answer has word-set Jaccard >= {DUP_ANSWER_JACCARD} "
    "against the item's true answer is excluded (two correct options is not a "
    "forced choice). The same threshold drops near-duplicate answers WITHIN the "
    "pool, keeping the first in (transcript_id, q_turn_idx) order, so a "
    "re-aired interview cannot supply the same answer three times."
)


# ---------------------------------------------------------------------------
# 1. The pool
# ---------------------------------------------------------------------------

def pool_row(item: dict, *, substantive: bool, cluster_id: str = "",
             date: str = "", program: str = "") -> dict:
    """One D4 item from a non-test interview -> one answer-pool row."""
    density = entity_density(item["answer"])
    return {
        "question": item["question"],
        "answer": item["answer"],
        "answer_words": item["answer_words"],
        "entity_density": density,
        "bucket": density_bucket(density),
        "source_canonical_id": item["canonical_id"],
        "source_transcript_id": item["transcript_id"],
        "source_q_turn_idx": item["q_turn_idx"],
        "source_cluster_id": cluster_id,
        "source_date": date,
        "source_program": program,
        "source_substantive": bool(substantive),
        "flags": list(item.get("flags", [])),
    }


def pool_sources(subject_row: dict, exclude_cluster_ids) -> list[dict]:
    """The subject's transcript entries that may feed the answer pool.

    Sorted by (transcript_id) so the harvest order — and therefore every
    tie-break downstream — is fixed by the data, not by dict iteration.
    """
    blocked = set(exclude_cluster_ids)
    rows = [t for t in subject_row["transcripts"]
            if t["cluster_id"] not in blocked]
    return sorted(rows, key=lambda t: t["transcript_id"])


def harvest_answer_pool(subject_row: dict, records: dict,
                        exclude_cluster_ids, *, extract_turns_fn=None,
                        on_transcript=None) -> list[dict]:
    """SPEC v1.8 D6-v2 rule 1. The subject's own answers from other interviews.

    ``records`` maps transcript_id -> raw MediaSum record; the caller fetches
    them (one streaming pass) so this stays testable without the 4.45 GB corpus.
    ``extract_turns_fn(record, subject_row)`` defaults to D3's extractor and is
    injectable for the same reason.

    ``on_transcript(transcript_id, substantive, n_items, note)`` is an optional
    progress hook. A transcript that yields nothing is reported, not hidden: a
    silent zero is how a broken speaker match looks.
    """
    if extract_turns_fn is None:
        from doppler.stage2_data import extract_turns as extract_turns_fn
    cid = subject_row["canonical_id"]
    out: list[dict] = []
    for entry in pool_sources(subject_row, exclude_cluster_ids):
        tid = entry["transcript_id"]
        record = records.get(tid)
        if record is None:
            if on_transcript:
                on_transcript(tid, entry["substantive"], 0, "record not fetched")
            continue
        turns = extract_turns_fn(record, subject_row)
        items = extract_qa(turns, cid, tid)
        for item in items:
            out.append(pool_row(item, substantive=entry["substantive"],
                                cluster_id=entry["cluster_id"],
                                date=entry.get("date", ""),
                                program=entry.get("program", "")))
        if on_transcript:
            on_transcript(tid, entry["substantive"], len(items), None)
    return out


def dedupe_pool(pool: list[dict],
                threshold: float = DUP_ANSWER_JACCARD) -> tuple[list[dict], list[dict]]:
    """Drop pool answers that near-duplicate an already-kept one.

    A cluster of re-aired transcripts carries the same interview more than
    once, and three copies of one answer would be three "different" wrong
    options that are really one. Order is (transcript_id, q_turn_idx), so which
    copy survives is deterministic. Returns (kept, dropped).
    """
    kept: list[dict] = []
    kept_sets: list[set[str]] = []
    dropped: list[dict] = []
    for row in sorted(pool, key=lambda r: (r["source_transcript_id"],
                                           r["source_q_turn_idx"])):
        wset = word_set(row["answer"])
        hit = next((k for k, s in enumerate(kept_sets)
                    if jaccard(wset, s) >= threshold), None)
        if hit is not None:
            dropped.append({**row, "duplicate_of": kept[hit]["source_transcript_id"]
                            + ":" + str(kept[hit]["source_q_turn_idx"])})
            continue
        kept.append(row)
        kept_sets.append(wset)
    return kept, dropped


# ---------------------------------------------------------------------------
# 2. Anti-leak against the rendered grounding
# ---------------------------------------------------------------------------

def leak_against(pool_answer: str, blocks) -> str | None:
    """The first shared shingle between an answer and any rendered block."""
    for block in blocks:
        if not block:
            continue
        hit = R.find_answer_leak(block, pool_answer)
        if hit is not None:
            return hit
    return None


def anti_leak_split(pool: list[dict], grounding_raw: str,
                    grounding_redacted: str,
                    variants) -> tuple[list[dict], list[dict]]:
    """SPEC v1.8 D6-v2 rule 2. Split the pool into (usable, leaking).

    Checked twice on purpose. Redaction rewrites names to ``GUEST`` in the
    rendered prompt but not in the raw transcript text, so a shingle that
    contains a name matches only when both sides have had the same treatment.
    Running raw-against-raw AND redacted-against-redacted catches both cases and
    costs nothing anybody will notice.
    """
    keep: list[dict] = []
    excluded: list[dict] = []
    for row in pool:
        raw_hit = leak_against(row["answer"], [grounding_raw])
        red_hit = leak_against(R.redact(row["answer"], variants),
                               [grounding_redacted])
        if raw_hit or red_hit:
            excluded.append({**row, "leak_shingle": raw_hit or red_hit,
                             "leak_side": "raw" if raw_hit else "redacted"})
            continue
        keep.append(row)
    return keep, excluded


def too_close_to_true(candidate_answer: str, true_answer: str,
                      threshold: float = DUP_ANSWER_JACCARD) -> bool:
    """SPEC v1.8 D6-v2 rule 3: is this candidate a second correct answer?"""
    return jaccard(word_set(candidate_answer), word_set(true_answer)) >= threshold


# ---------------------------------------------------------------------------
# 3. Question similarity
# ---------------------------------------------------------------------------

class QuestionSimilarity:
    """TF-IDF cosine between questions, over ONE fixed corpus.

    D6 fitted a vectorizer per query on "the bank's questions plus the query".
    The v2 pools are one to two orders of magnitude smaller (a subject has tens
    of past answers, not thousands), and an IDF estimated on ten documents is
    noise. So the corpus is fixed once — every dev subject's pool questions plus
    every test question — and every similarity in the run is measured on the
    same yardstick. That is also what makes the floor sweep comparable across
    subjects.

    The corpus digest is exposed so an artifact can prove which yardstick it
    used.
    """

    def __init__(self, corpus_questions):
        self.corpus = sorted({q for q in corpus_questions if q and q.strip()})
        if not self.corpus:
            raise ValueError("QuestionSimilarity needs a non-empty corpus")
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                    lowercase=True)
        self._vec.fit(self.corpus)

    @property
    def corpus_sha256(self) -> str:
        return hashlib.sha256(
            "\n".join(self.corpus).encode("utf-8")).hexdigest()

    @property
    def vocab_size(self) -> int:
        return len(self._vec.vocabulary_)

    def cosines(self, query: str, questions) -> list[float]:
        """Cosine of ``query`` against each of ``questions``, same order.

        TF-IDF rows are L2-normalised, so the dot product IS the cosine.
        """
        questions = list(questions)
        if not questions:
            return []
        left = self._vec.transform([query])
        right = self._vec.transform(questions)
        sims = (right @ left.T).toarray().ravel()
        return [float(s) for s in sims]


# ---------------------------------------------------------------------------
# 4. Selection
# ---------------------------------------------------------------------------

def _eligible(pool: list[dict], true_words: int, true_bucket: str,
              tol: float, adjacent: bool) -> list[int]:
    lo, hi = true_words * (1.0 - tol), true_words * (1.0 + tol)
    allowed = ADJACENT_BUCKETS[true_bucket] if adjacent else {true_bucket}
    return [i for i, r in enumerate(pool)
            if lo <= r["answer_words"] <= hi and r["bucket"] in allowed]


def _rank(indices, pool: list[dict], sims: list[float]) -> list[tuple[float, int]]:
    """(similarity, pool index) best first, ties broken by source position."""
    scored = [(sims[i], i) for i in indices]
    scored.sort(key=lambda s: (-s[0], pool[s[1]]["source_transcript_id"],
                               pool[s[1]]["source_q_turn_idx"]))
    return scored


def select_same_subject(item: dict, pool: list[dict], sims: list[float], *,
                        n: int = N_DISTRACTORS, floor: float = 0.0) -> dict:
    """SPEC v1.8 D6-v2. One test item + the subject's own pool -> its options.

    ``sims[i]`` is the question similarity of ``pool[i]``'s source question to
    this item's question; the caller computes them once per item with
    :class:`QuestionSimilarity`.

    Returns a record with ``built``. When ``built`` is False the item is NOT
    part of the set — there is no cross-person fallback, by design — and
    ``reason`` plus ``best_rung_candidates`` say how close it came.

    The relaxation ladder is D6's, unchanged, and the rung actually used is
    recorded per item. What D6-r2's "3 distinct donors" rule protected against
    is gone by construction (every distractor is the same person), so its
    replacement is the pool-level near-duplicate dedup: three distinct pool
    rows are three distinct answers.
    """
    true_words = item["answer_words"]
    true_density = entity_density(item["answer"])
    true_bucket = density_bucket(true_density)

    usable = []
    n_dup_true = 0
    n_below_floor = 0
    for i, row in enumerate(pool):
        if too_close_to_true(row["answer"], item["answer"]):
            n_dup_true += 1
            continue
        if sims[i] < floor:
            n_below_floor += 1
            continue
        usable.append(i)

    chosen: list[tuple[float, int]] = []
    rung = None
    best_seen = 0
    for k, (tol, adjacent) in enumerate(RELAX_LADDER):
        matched = _eligible([pool[i] for i in usable], true_words, true_bucket,
                            tol, adjacent)
        indices = [usable[m] for m in matched]
        best_seen = max(best_seen, len(indices))
        if len(indices) >= n:
            chosen = _rank(indices, pool, sims)[:n]
            rung = k
            break

    base = {
        "item_id": item["item_id"],
        "canonical_id": item["canonical_id"],
        "true_answer_words": true_words,
        "true_entity_density": true_density,
        "true_bucket": true_bucket,
        "pool_size": len(pool),
        "pool_excluded_duplicate_of_true": n_dup_true,
        "pool_excluded_below_floor": n_below_floor,
        "similarity_floor": floor,
    }
    if rung is None:
        return {**base, "built": False,
                "reason": "fewer than 3 same-subject candidates at the final "
                          "relaxation rung; no cross-person fallback exists",
                "best_rung_candidates": best_seen}

    options = [{
        "text": item["answer"],
        "kind": "true",
        "source_canonical_id": item["canonical_id"],
        "source_transcript_id": item["transcript_id"],
        "source_q_turn_idx": item["q_turn_idx"],
        "answer_words": true_words,
        "entity_density": true_density,
        "question_similarity": None,     # it IS the question; keys stay uniform
        "source_question": item["question"],
        "source_substantive": True,
    }]
    for sim, idx in chosen:
        row = pool[idx]
        options.append({
            "text": row["answer"],
            "kind": "distractor",
            "source_canonical_id": row["source_canonical_id"],
            "source_transcript_id": row["source_transcript_id"],
            "source_q_turn_idx": row["source_q_turn_idx"],
            "answer_words": row["answer_words"],
            "entity_density": row["entity_density"],
            "question_similarity": round(sim, 6),
            "source_question": row["question"],
            "source_substantive": row["source_substantive"],
        })

    import random
    random.Random(shuffle_seed(item["item_id"])).shuffle(options)
    correct = [i for i, o in enumerate(options) if o["kind"] == "true"]
    if len(correct) != 1:
        raise AssertionError(f"{item['item_id']}: {len(correct)} true options")

    # --- invariants, asserted rather than trusted ---------------------------
    for opt in options:
        if opt["source_canonical_id"] != item["canonical_id"]:
            raise AssertionError(
                f"{item['item_id']}: option from {opt['source_canonical_id']}, "
                "but every v2 option must come from the subject themself")
    for opt in options:
        if opt["kind"] == "distractor" \
                and opt["source_transcript_id"] == item["transcript_id"]:
            raise AssertionError(
                f"{item['item_id']}: distractor drawn from the test transcript")
    keys = [(o["source_transcript_id"], o["source_q_turn_idx"]) for o in options]
    if len(keys) != len(set(keys)):
        raise AssertionError(f"{item['item_id']}: an option is used twice")

    return {
        **base,
        "built": True,
        "options": options,
        "correct_index": correct[0],
        "relax_rung": rung,
        "flags": [f"relax_rung_{rung}"],
        "options_stripped": [strip_entities(o["text"]) for o in options],
        "distractor_similarities": [o["question_similarity"] for o in options
                                    if o["kind"] == "distractor"],
    }


def similarity_floor_sweep(items_by_subject: dict, pools: dict,
                           sims_by_item: dict,
                           floors=SWEEP_FLOORS) -> dict:
    """Item yield at each candidate admission floor. Reports; decides nothing.

    ``items_by_subject[cid]`` is the subject's test items, ``pools[cid]`` their
    answer pool, and ``sims_by_item[item_id]`` the per-pool-row similarity list
    for that item. Returns {"floors": [...], "per_subject": {...},
    "total": {...}} keyed by the floor rendered as a 2-decimal string.
    """
    out_subject: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {}
    for floor in floors:
        key = f"{floor:.2f}"
        total = 0
        for cid in sorted(items_by_subject):
            built = 0
            for item in items_by_subject[cid]:
                res = select_same_subject(item, pools[cid],
                                          sims_by_item[item["item_id"]],
                                          floor=floor)
                built += 1 if res["built"] else 0
            out_subject.setdefault(cid, {})[key] = built
            total += built
        totals[key] = total
    return {"floors": [f"{f:.2f}" for f in floors],
            "per_subject": out_subject, "total": totals}


__all__ = [
    "N_DISTRACTORS", "LEAK_SHINGLE_WORDS", "DUP_ANSWER_JACCARD", "SWEEP_FLOORS",
    "POOL_RULE", "ANTI_LEAK_RULE", "DUP_RULE",
    "pool_row", "pool_sources", "harvest_answer_pool", "dedupe_pool",
    "leak_against", "anti_leak_split", "too_close_to_true",
    "QuestionSimilarity", "select_same_subject", "similarity_floor_sweep",
]
