"""SPEC D4: forced-choice Q-A items pulled out of an interview transcript.

One item = a host turn that asks something, plus the answer the subject gave
right after it. That is the whole idea. Everything below is the bookkeeping
that makes it reproducible.

The same code runs twice in Stage 2, on purpose:

- on a dev subject's HELD-OUT latest interview, to make the questions the
  twin arms are scored on;
- on a distractor donor's latest interview, to fill the distractor bank
  (SPEC D6). Same rules both times, so a distractor answer is exactly the
  same kind of object as a true answer and cannot be told apart by shape.

**Pure standard library on purpose**, same reason as stage2_data.py: the file
may be copied to a compute node next to a driver and the extraction rules must
not be able to drift between the local and the remote copy.

Word counts are whitespace tokens throughout — the pilot's documented token
proxy (SPEC D5).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# D4 constants — frozen. Do not tune these to move the yield; the yield is a
# finding about the corpus, not a knob. (v1.1 amendment: the answer floor was
# lowered 40 -> 30 after the first pilot yield was observed. That was an
# owner decision, recorded in PREREGISTRATION_AMENDMENT_1 / SPEC D4.)
# ---------------------------------------------------------------------------

MIN_QUESTION_WORDS = 5
MIN_ANSWER_WORDS = 30
MAX_ANSWER_WORDS = 400
TRUNCATE_TARGET_WORDS = 300
NEAR_DUP_JACCARD = 0.8
MAX_ITEMS = 20

#: First-word cues that make a host turn count as a question even with no "?".
CUE_WORDS = frozenset("""
what why how when where who tell describe do did is are was were can could
would will
""".split())

_SENT_END_RE = re.compile(r"[.!?]+[\"'”’)\]]*\s+")
_PUNCT_STRIP_RE = re.compile(r"^\W+|\W+$", re.UNICODE)

#: A leading stage direction: "(LAUGHTER)", "[APPLAUSE]". Stripped before the
#: cue test (SPEC D4 as clarified by v1.7). Applied repeatedly, because turns
#: occasionally open with two of them.
_STAGE_DIR_RE = re.compile(r"^\s*(?:\([^)]*\)|\[[^\]]*\])\s*")


# ---------------------------------------------------------------------------
# Small text helpers (public: the tests pin them, and D6 reuses word_count)
# ---------------------------------------------------------------------------

def word_count(text: str) -> int:
    """Whitespace tokens. The pilot's token proxy (SPEC D5)."""
    return len((text or "").split())


def first_word(text: str) -> str:
    """SPEC D4 as clarified by v1.7: the LITERAL first word, lowercased.

    Leading parenthetical or bracketed stage directions are stripped first, so
    ``"(LAUGHTER) What did you make of that?"`` opens with ``what``. After
    that the *first whitespace token* is the first word — punctuation wrapped
    around it does not make it a different word (``"...is"`` is ``is``), but
    nothing is ever skipped over.

    That last part is the whole point of v1.7. The earlier reading searched for
    the first *alphabetic* run, which skipped straight past a leading number:
    "1-800-989-8255 is our number. What is interesting..." opened with ``is``,
    a cue word, and was admitted as a question. It is not one. Under v1.7 its
    first word is the phone number, no cue, so only a "?" can admit it.
    """
    text = text or ""
    while True:
        m = _STAGE_DIR_RE.match(text)
        if m is None:
            break
        text = text[m.end():]
    parts = text.split()
    if not parts:
        return ""
    return _PUNCT_STRIP_RE.sub("", parts[0]).casefold()


def has_interrogative_cue(question: str) -> bool:
    """SPEC D4: the first word is one of the interrogative/imperative cues."""
    return first_word(question) in CUE_WORDS


def is_question(question: str) -> bool:
    """SPEC D4: contains "?" OR opens with an interrogative/imperative cue."""
    return "?" in (question or "") or has_interrogative_cue(question)


def word_set(text: str) -> set[str]:
    """Word set for the near-duplicate test.

    Whitespace tokens, lowercased, with leading/trailing punctuation removed
    and empties dropped. Casing and punctuation are not what makes two host
    questions the same question, so they are normalised away; nothing else is.
    """
    out = set()
    for tok in (text or "").split():
        tok = _PUNCT_STRIP_RE.sub("", tok).casefold()
        if tok:
            out.add(tok)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    """|A n B| / |A u B|; two empty sets are identical (1.0)."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def truncate_answer(text: str,
                    max_words: int = MAX_ANSWER_WORDS,
                    target_words: int = TRUNCATE_TARGET_WORDS):
    """SPEC D4 long-answer rule. Return (text, was_truncated).

    Answers over ``max_words`` are cut at the sentence boundary nearest
    ``target_words``. Sentence boundaries are ``.``/``!``/``?`` runs followed by
    whitespace (closing quotes and brackets allowed in between).

    Three edge cases the SPEC does not spell out, resolved here and
    documented: a run-on answer with no interior sentence boundary at all; one
    whose nearest boundary is the very end of the text (so cutting there would
    cut nothing); and one whose nearest boundary is itself past ``max_words``,
    where honouring the boundary would leave the option longer than the bound
    the rule exists to impose. All three fall back to a hard cut at
    ``target_words`` whitespace tokens.

    The output is therefore never longer than ``max_words``. That is a hard
    guarantee, not a tendency: an option that dwarfs the other three is a
    length cue, which is exactly what the A4 length control forbids.
    """
    text = (text or "").strip()
    if word_count(text) <= max_words:
        return text, False

    # Candidate cut points: character offsets just past each sentence end.
    cuts = [m.end() for m in _SENT_END_RE.finditer(text)]
    best = None
    for cut in cuts:
        n = word_count(text[:cut])
        if best is None or abs(n - target_words) < abs(best[1] - target_words):
            best = (cut, n)
    if best is not None:
        head = text[:best[0]].strip()
        n_head = word_count(head)
        if head and n_head < word_count(text) and n_head <= max_words:
            return head, True

    return " ".join(text.split()[:target_words]), True


# ---------------------------------------------------------------------------
# D4 — pairing and filtering
# ---------------------------------------------------------------------------

def _ordered(turns: list[dict], transcript_id: str | None) -> list[dict]:
    """Turns in ``turn_idx`` order, checked for the things that would ruin D4.

    The cross-transcript guard runs whether or not a ``transcript_id`` was
    supplied. Mixing transcripts would let a grounding turn answer a test
    question — the single worst thing this module could do — so it is a loud
    failure on every path into the pairing logic, not only the named one.
    """
    rows = list(turns)
    for t in rows:
        if "turn_idx" not in t or "role" not in t:
            raise ValueError("turn records need turn_idx and role")
    seen = {t.get("transcript_id") for t in rows
            if t.get("transcript_id") is not None}
    if transcript_id is not None:
        stray = sorted(seen - {transcript_id})
        if stray:
            raise ValueError(
                f"turn from {stray[0]!r} passed to extract_qa for "
                f"{transcript_id!r}")
    elif len(seen) > 1:
        raise ValueError(f"turns from multiple transcripts: {sorted(seen)}")
    rows.sort(key=lambda t: t["turn_idx"])
    idxs = [t["turn_idx"] for t in rows]
    if len(set(idxs)) != len(idxs):
        raise ValueError("duplicate turn_idx in the turn list")
    return rows


def qa_candidates(turns: list[dict]) -> list[dict]:
    """Every host turn immediately followed by >= 1 guest turn (SPEC D4).

    The answer is the run of consecutive guest turns after it, joined with a
    single space, stopping at the first non-guest turn. No filters applied yet
    — ``extract_qa`` does that, and the split is what lets the driver report
    *why* items were dropped.
    """
    rows = _ordered(turns, None)
    out = []
    for i, turn in enumerate(rows):
        if turn["role"] != "host":
            continue
        if i + 1 >= len(rows) or rows[i + 1]["role"] != "guest":
            continue
        j = i + 1
        parts = []
        while j < len(rows) and rows[j]["role"] == "guest":
            piece = (rows[j].get("text") or "").strip()
            if piece:
                parts.append(piece)
            j += 1
        out.append({
            "q_turn_idx": turn["turn_idx"],
            "question": (turn.get("text") or "").strip(),
            "answer": " ".join(parts),
            "n_answer_turns": j - (i + 1),
        })
    return out


def extract_qa_verbose(turns: list[dict], canonical_id: str,
                       transcript_id: str) -> tuple[list[dict], list[dict]]:
    """SPEC D4 in full. Return (items, drops).

    ``drops`` is one record per rejected candidate with the reason, purely for
    the driver's summary and for tests; it is never written to disk as part of
    the item set.

    Filter order, exactly as SPEC D4 lists them:

    1. the transcript's first host turn is dropped if the guest has not spoken
       yet (that turn is the show's billboard, not a question);
    2. question >= 5 words;
    3. question contains "?" or opens with an interrogative/imperative cue;
    4. answer >= 30 words, and over 400 words it is truncated (flag
       ``truncated``) rather than dropped;
    5. a question near-duplicating an already-kept one (Jaccard >= 0.8 over
       word sets) is dropped, first occurrence kept;
    6. the first 20 survivors in turn order.
    """
    rows = _ordered(turns, transcript_id)
    host_idxs = [t["turn_idx"] for t in rows if t["role"] == "host"]
    first_host = host_idxs[0] if host_idxs else None
    guest_before_first_host = any(
        t["role"] == "guest" and first_host is not None
        and t["turn_idx"] < first_host for t in rows)

    items: list[dict] = []
    drops: list[dict] = []
    kept_sets: list[set[str]] = []

    for cand in qa_candidates(rows):
        q_idx = cand["q_turn_idx"]
        question, answer = cand["question"], cand["answer"]

        def drop(reason: str, **extra):
            drops.append({"q_turn_idx": q_idx, "reason": reason,
                          "question": question, **extra})

        if q_idx == first_host and not guest_before_first_host:
            drop("intro_host_turn")
            continue
        n_q = word_count(question)
        if n_q < MIN_QUESTION_WORDS:
            drop("question_too_short", question_words=n_q)
            continue
        if not is_question(question):
            drop("not_interrogative")
            continue

        n_a = word_count(answer)
        if n_a < MIN_ANSWER_WORDS:
            drop("answer_too_short", answer_words=n_a)
            continue
        answer, truncated = truncate_answer(answer)
        flags = ["truncated"] if truncated else []

        qset = word_set(question)
        dup = next((s for s in kept_sets if jaccard(qset, s) >= NEAR_DUP_JACCARD),
                   None)
        if dup is not None:
            drop("near_duplicate_question")
            continue

        if len(items) >= MAX_ITEMS:
            drop("over_item_cap")
            continue

        kept_sets.append(qset)
        items.append({
            "item_id": f"{canonical_id}:{transcript_id}:{q_idx}",
            "canonical_id": canonical_id,
            "transcript_id": transcript_id,
            "q_turn_idx": q_idx,
            "question": question,
            "answer": answer,
            "answer_words": word_count(answer),
            "flags": flags,
        })

    return items, drops


def extract_qa(turns: list[dict], canonical_id: str,
               transcript_id: str) -> list[dict]:
    """SPEC D4. The Q-A items of one transcript, in turn order (max 20).

    ``turns`` is the D3 turn list (dicts with turn_idx, role, text). Works on
    any turn list, which is what lets the distractor bank reuse it verbatim.
    """
    return extract_qa_verbose(turns, canonical_id, transcript_id)[0]


__all__ = [
    "MIN_QUESTION_WORDS", "MIN_ANSWER_WORDS", "MAX_ANSWER_WORDS",
    "TRUNCATE_TARGET_WORDS", "NEAR_DUP_JACCARD", "MAX_ITEMS", "CUE_WORDS",
    "word_count", "first_word", "has_interrogative_cue", "is_question",
    "word_set", "jaccard", "truncate_answer",
    "qa_candidates", "extract_qa", "extract_qa_verbose",
]
