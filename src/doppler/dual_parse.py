"""Two parsers, side by side — SPEC v1.10 (D6-v4.5).

Round 3's gate lost 12 of 15 replies to one measurement artifact: the model
prints its distribution twice, once as four lines and once as one, so the
stated mass is ~2.0 and D8's renormalise window [0.8, 1.2] discards it. Every
one of the 12 was recoverable and every one was argmax-correct. The rate is
climbing with option length -- 2 of 170 in round 1, 2 of 10 in round 2, 12 of
15 in round 3 -- and round 4's options are longer still.

**The frozen parser is not changed.** ``stage2_render.parse_distribution``
remains the contract, its verdict is what a gate decision uses, and every
round-4 table reports its N. This module adds a WIDENED reading that runs
beside it on the same completion, so a report can state both numbers and the
owner can see what widening would cost or buy before deciding anything at
bar-lock. Round 3 could not do that -- it had one number and a footnote.

Widening rule, deliberately narrow: take the LAST well-formed distribution in
the reply and read it with the FROZEN parser. Not a second parser with its own
semantics -- the same code, applied to a window. The only thing that changes is
which part of the completion is offered to it. A reply that never contained a
well-formed distribution is still a parse failure under both readings.
"""

from __future__ import annotations

import re

from doppler import stage2_render as R

#: Start of a candidate distribution block: an "A:"-style pair opening a line,
#: or one appearing inline after prose. Deliberately anchored on the FIRST
#: label so a window always begins at a distribution rather than mid-way
#: through one.
_BLOCK_START = re.compile(r"(?:(?<=^)|(?<=[\s>*_`]))A\s*[:=).\]\-]\s*(?=\d|\.)",
                          re.MULTILINE | re.IGNORECASE)

#: Reasons a widened read differs from the frozen one. Worded as what was
#: OBSERVED, not as a claim about the model's intent: the two are told apart by
#: how many distribution blocks the reply contains, which is evidence, not a
#: diagnosis. Note the stray example uses label B deliberately -- a stray "A."
#: in the reasoning opens a new window and so reports as DOUBLED.
DOUBLED = ("more than one distribution block appears in the reply, so the "
           "stated mass falls outside the frozen renormalise window [0.8, 1.2]")
STRAY = ("only one distribution block appears, so a stray label-like token "
         "elsewhere in the reply (e.g. 'option B. 3 people') made a label "
         "repeat and the frozen parser refused it")


def distribution_windows(completion: str) -> list[str]:
    """Every suffix of ``completion`` that starts at a distribution block."""
    if not completion:
        return []
    return [completion[m.start():] for m in _BLOCK_START.finditer(completion)]


def widened_parse(completion, n_options: int = 4):
    """The LAST well-formed distribution in the reply, read by the frozen parser.

    Returns the same shape ``parse_distribution`` returns -- ``n_options``
    probabilities summing to 1, or ``None``. ``None`` means neither the whole
    reply nor any window in it parsed, so the reply genuinely did not answer.

    **The frozen reading is tried FIRST, so the widened set is always a
    superset of the frozen set.** Without that, a reply stating its labels out
    of order ("B: 0.2 A: 0.1 C: 0.6 D: 0.1") parsed frozen and failed widened,
    because the window is anchored on the first label -- which would make the
    widened N SMALLER than the contract N and the both-N table incoherent.
    Widening may only ever add readings, never remove them.
    """
    frozen = R.parse_distribution(completion, n_options)
    if frozen is not None:
        return frozen
    for window in reversed(distribution_windows(completion)):
        got = R.parse_distribution(window, n_options)
        if got is not None:
            return got
    return None


def widened_reason(completion, n_options: int = 4) -> str | None:
    """Why the widened read succeeded where the frozen one failed."""
    if R.parse_distribution(completion, n_options) is not None:
        return None
    if widened_parse(completion, n_options) is None:
        return None
    return DOUBLED if len(distribution_windows(completion)) > 1 else STRAY


def score_distribution(dist, correct_index: int, n_options: int = 4) -> dict:
    """Argmax, mass on the true option, and margin over the best rival."""
    unparsed = {"parsed": False, "argmax_correct": None, "p_correct": None,
                "argmax_index": None, "margin": None, "distribution": None}
    if dist is None:
        return unparsed
    n = min(n_options, len(dist))
    if not 0 <= correct_index < n:
        # A correct_index off the end is a corrupt meta row, not an answer.
        # Returning the unparsed shape keeps one bad row from killing an
        # ingest that would otherwise report every other row correctly.
        return {**unparsed, "error": f"correct_index {correct_index} outside "
                                     f"0..{n - 1}"}
    argmax = max(range(n), key=lambda i: dist[i])
    rival = max((dist[i] for i in range(n) if i != correct_index), default=0.0)
    return {
        "parsed": True,
        "argmax_correct": bool(argmax == correct_index),
        "p_correct": float(dist[correct_index]),
        "argmax_index": argmax,
        "margin": round(float(dist[correct_index]) - float(rival), 6),
        "distribution": [float(p) for p in dist[:n]],
    }


def dual_score(meta: dict, completion) -> dict:
    """One completion scored under BOTH readings, in one record.

    The record carries ``frozen`` and ``widened`` sub-records of identical
    shape, so a table can be built from either without re-reading anything, and
    ``recovered_by_widening`` flags exactly the rows where the two disagree
    about whether an answer exists at all.
    """
    n = int(meta.get("n_options") or 4)
    correct = int(meta["correct_index"])
    frozen = score_distribution(R.parse_distribution(completion, n)
                                if completion else None, correct, n)
    widened = score_distribution(widened_parse(completion, n)
                                 if completion else None, correct, n)
    return {
        "item_id": meta.get("item_id"),
        "canonical_id": meta.get("canonical_id"),
        "arm": meta.get("arm"), "variant": meta.get("variant"),
        "correct_index": correct,
        "frozen": frozen, "widened": widened,
        "recovered_by_widening": bool(not frozen["parsed"]
                                      and widened["parsed"]),
        "widened_reason": widened_reason(completion, n) if completion else None,
        # Structurally always False: when the frozen parser succeeds the
        # widened reading returns its result unchanged. Kept as a TRIPWIRE --
        # if it ever goes True the two readings have diverged in a way this
        # module says is impossible, and a report built on "the contract
        # number plus a wider one" would be wrong.
        "readings_disagree_on_argmax": bool(
            frozen["parsed"] and widened["parsed"]
            and frozen["argmax_correct"] != widened["argmax_correct"]),
        "raw_response": (completion or "")[:600],
    }


def accuracy_table(records, reading: str) -> dict:
    """Accuracy under ONE reading, with the N it was computed on.

    N is returned beside every rate because that is the whole point of running
    two parsers: the frozen and widened numbers are computed on different
    denominators, and a rate quoted without its N hides that.
    """
    if reading not in ("frozen", "widened"):
        raise ValueError(f"reading must be 'frozen' or 'widened', got {reading}")
    parsed = [r for r in records if r[reading]["parsed"]]
    solved = [r for r in parsed if r[reading]["argmax_correct"]]
    margins = [r[reading]["margin"] for r in parsed]
    masses = [r[reading]["p_correct"] for r in parsed]
    return {
        "reading": reading,
        "n_prompts": len(records),
        "n_parsed": len(parsed),
        "n_parse_failures": len(records) - len(parsed),
        "n_argmax_correct": len(solved),
        "argmax_accuracy": round(len(solved) / len(parsed), 4) if parsed else None,
        "mean_prob_mass_correct": (round(sum(masses) / len(masses), 4)
                                   if masses else None),
        "mean_margin": round(sum(margins) / len(margins), 4) if margins else None,
        "min_margin": round(min(margins), 4) if margins else None,
        "max_margin": round(max(margins), 4) if margins else None,
    }


def both_readings(records) -> dict:
    """The both-N block every round-4 table carries."""
    return {
        "frozen": accuracy_table(records, "frozen"),
        "widened": accuracy_table(records, "widened"),
        "n_recovered_by_widening": sum(1 for r in records
                                       if r["recovered_by_widening"]),
        "n_readings_disagree_on_argmax": sum(
            1 for r in records if r["readings_disagree_on_argmax"]),
        "contract_note":
            "The FROZEN parser is the contract number (SPEC D8). The widened "
            "reading takes the LAST well-formed distribution in the reply and "
            "reads it with the same frozen parser; it is reported beside the "
            "contract number, never in place of it. Widening the contract is a "
            "bar-lock decision.",
    }


__all__ = [
    "DOUBLED", "STRAY", "distribution_windows", "widened_parse",
    "widened_reason", "score_distribution", "dual_score", "accuracy_table",
    "both_readings",
]
