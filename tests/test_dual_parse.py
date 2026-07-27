"""Tests for the two-readings parser harness (dual_parse.py).

Deterministic, offline, no API. Round 3's gate lost 12 of 15 replies to one
measurement artifact: the model printed its distribution twice, once as four
lines and once as one, so the stated mass was ~2.0 and D8's renormalise window
[0.8, 1.2] discarded it. Every one of the 12 was recoverable and every one was
argmax-correct.

The properties being defended: the FROZEN parser is not changed and is still the
contract number; the widened reading is the same frozen parser applied to the
last well-formed distribution in the reply, so it can never rescue a reply that
never contained one; and every rate is reported beside the N it was computed on,
because the two readings run on different denominators.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doppler import dual_parse as DP  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

#: The round-3 artifact, reproduced: reasoning, the distribution as four lines,
#: then the same distribution again as the required single line.
DOUBLED_REPLY = (
    "Let me weigh the four options carefully before I commit to numbers.\n"
    "A: 0.1\n"
    "B: 0.2\n"
    "C: 0.6\n"
    "D: 0.1\n"
    "A: 0.1 B: 0.2 C: 0.6 D: 0.1\n"
)

#: One distribution, stated once, the way the prompt asks for it.
CLEAN_REPLY = "C reads most like the guest.\nA: 0.1 B: 0.2 C: 0.6 D: 0.1"

#: A reply that never states a distribution at all.
NO_ANSWER_REPLY = "I cannot say which of these the person gave."


def _meta(correct_index: int, item_id: str = "C1:T:3") -> dict:
    return {"item_id": item_id, "canonical_id": "c1", "arm": "zeroinfo_redacted",
            "variant": "v4", "correct_index": correct_index, "n_options": 4}


# ---------------------------------------------------------------------------
# The widened reading
# ---------------------------------------------------------------------------


def test_a_distribution_printed_twice_is_lost_by_the_frozen_parser():
    """The central fact of round 3: this reply answered the question, argmax and
    all, and the contract parser scored it as no answer because the labels
    repeat and the stated mass is ~2.0."""
    assert R.parse_distribution(DOUBLED_REPLY) is None


def test_a_distribution_printed_twice_is_recovered_by_the_widened_reading():
    """12 of 15 round-3 replies looked like this. Reporting the two numbers side
    by side is what lets the owner see what widening buys before deciding at
    bar-lock whether the contract should move."""
    assert DP.widened_parse(DOUBLED_REPLY) == [0.1, 0.2, 0.6, 0.1]


def test_the_widened_reading_takes_the_last_distribution_not_the_first():
    """A model that revises mid-reply means the last line, and the prompt asks
    for the answer to be the final line. Taking the first would score a draft."""
    revised = ("A: 0.6 B: 0.2 C: 0.1 D: 0.1\n"
               "On reflection C is the better read.\n"
               "A: 0.1 B: 0.2 C: 0.6 D: 0.1")
    assert DP.widened_parse(revised) == [0.1, 0.2, 0.6, 0.1]
    assert len(DP.distribution_windows(revised)) == 2


def test_a_single_clean_distribution_reads_identically_under_both_parsers():
    """The widened reading is only allowed to differ where the frozen one
    failed. If it moved a number on an ordinary reply it would not be a second
    reading of the same contract, it would be a second contract."""
    assert R.parse_distribution(CLEAN_REPLY) == DP.widened_parse(CLEAN_REPLY)
    assert DP.widened_parse(CLEAN_REPLY) == [0.1, 0.2, 0.6, 0.1]


def test_a_reply_with_no_distribution_fails_under_both_readings():
    """A reply that never answered must stay a parse failure. Widening is a
    recovery of lost measurements, not a way to manufacture them."""
    assert R.parse_distribution(NO_ANSWER_REPLY) is None
    assert DP.widened_parse(NO_ANSWER_REPLY) is None
    assert DP.distribution_windows(NO_ANSWER_REPLY) == []
    assert DP.widened_parse("") is None
    assert DP.widened_parse(None) is None


def test_widening_does_not_rescue_a_distribution_that_is_missing_a_label():
    """The widened reading reuses the frozen parser on a window; it does not
    loosen the parser's own rules. Three probabilities are not an answer over
    four options however many times they are printed."""
    reply = ("Only three seem worth mass.\n"
             "A: 0.3 B: 0.3 C: 0.4\n"
             "A: 0.3 B: 0.3 C: 0.4")
    assert R.parse_distribution(reply) is None
    assert DP.widened_parse(reply) is None


def test_widening_does_not_rescue_mixed_percent_and_decimal_scales():
    """"A: 70% B: 0.1" has no honest reading, and the frozen parser refuses it
    on purpose. Handing the same text to the same parser on a window must not
    change that answer."""
    mixed = "A: 70% B: 0.1 C: 0.1 D: 0.1"
    assert R.parse_distribution(mixed) is None
    assert DP.widened_parse(mixed) is None
    twice = "Here are my numbers.\n" + mixed + "\n" + mixed
    assert len(DP.distribution_windows(twice)) == 2
    assert DP.widened_parse(twice) is None


def test_no_widening_reason_is_given_when_the_frozen_parser_already_succeeded():
    """A reason on a row the contract already scored would suggest the two
    readings disagreed about it when they did not."""
    assert DP.widened_reason(CLEAN_REPLY) is None


def test_a_doubled_distribution_reports_the_doubling_as_the_reason():
    """The report has to name the mechanism it is asking to widen for, not just
    the count of rows it would move."""
    assert DP.widened_reason(DOUBLED_REPLY) == DP.DOUBLED
    assert "0.8, 1.2" in DP.DOUBLED


def test_a_stray_label_in_the_reasoning_reports_the_stray_as_the_reason():
    """The other way the frozen parser loses a real answer: a label-shaped token
    in the prose makes a label repeat. It is a different failure with a
    different fix, so the two are counted apart."""
    stray = ("As option B. 3 shows, the guest hedges everywhere.\n"
             "A: 0.1 B: 0.2 C: 0.6 D: 0.1")
    assert R.parse_distribution(stray) is None
    assert DP.widened_parse(stray) == [0.1, 0.2, 0.6, 0.1]
    assert DP.widened_reason(stray) == DP.STRAY


def test_a_reply_that_never_parsed_has_no_widening_reason():
    """Nothing was recovered, so there is nothing to explain."""
    assert DP.widened_reason(NO_ANSWER_REPLY) is None


def test_the_widened_reading_is_always_a_superset_of_the_frozen_one():
    """Widening may only ever ADD readings, never remove them.

    The window is anchored on the label A, so a reply stating its labels out of
    order loses everything before the A and no window parses. If that were the
    whole rule the widened N could come out SMALLER than the contract N, which
    makes the both-N table incoherent -- the widened column is supposed to say
    "the contract, plus what it discarded". The frozen reading is therefore
    tried first and returned unchanged when it succeeds.
    """
    reordered = "B: 0.2 A: 0.1 C: 0.6 D: 0.1"
    assert R.parse_distribution(reordered) == [0.1, 0.2, 0.6, 0.1]
    assert DP.widened_parse(reordered) == [0.1, 0.2, 0.6, 0.1]

    lowercase = "a: 0.1 b: 0.2 c: 0.6 d: 0.1"
    assert R.parse_distribution(lowercase) is not None
    assert DP.widened_parse(lowercase) == R.parse_distribution(lowercase)


def test_no_completion_parses_frozen_while_failing_widened():
    """The superset invariant, stated over a spread of shapes rather than one."""
    for text in ("A: 0.25 B: 0.25 C: 0.25 D: 0.25",
                 "B: 0.2 A: 0.1 C: 0.6 D: 0.1",
                 "a: 0.1 b: 0.2 c: 0.6 d: 0.1",
                 "A: 70% B: 10% C: 10% D: 10%",
                 "prose first. A: 0.4 B: 0.3 C: 0.2 D: 0.1",
                 "A: 0.1 B: 0.2 C: 0.6 D: 0.1\nA: 0.1 B: 0.2 C: 0.6 D: 0.1",
                 "no distribution at all"):
        if R.parse_distribution(text) is not None:
            assert DP.widened_parse(text) is not None, text


# ---------------------------------------------------------------------------
# Scoring one distribution
# ---------------------------------------------------------------------------


def test_a_confident_correct_answer_scores_its_mass_and_its_margin():
    """Margin over the best rival, not raw accuracy, is what the gate reads: a
    solved item at +0.6 and a solved item at +0.02 are different findings."""
    got = DP.score_distribution([0.7, 0.1, 0.1, 0.1], 0)
    assert got["parsed"] is True
    assert got["argmax_correct"] is True
    assert got["argmax_index"] == 0
    assert got["p_correct"] == 0.7
    assert got["margin"] == 0.6


def test_the_margin_is_measured_against_the_best_rival_not_the_average():
    """A model split between two options is nearly undecided even when its mass
    on the truth is high; averaging the rivals would hide that."""
    got = DP.score_distribution([0.4, 0.35, 0.15, 0.1], 0)
    assert got["argmax_correct"] is True
    assert got["margin"] == pytest.approx(0.05)


def test_the_margin_goes_negative_when_the_model_is_confidently_wrong():
    """A wrong answer has to cost something on the same scale a right one earns,
    or the mean margin over a set of items is not a summary of anything."""
    got = DP.score_distribution([0.7, 0.1, 0.1, 0.1], 1)
    assert got["argmax_correct"] is False
    assert got["argmax_index"] == 0
    assert got["p_correct"] == 0.1
    assert got["margin"] == -0.6


def test_an_unparsed_distribution_gets_a_record_of_the_same_shape():
    """A parse failure is a row in the table with nothing in it, not a missing
    row. Scoring code that has to test for absence starts inventing zeros."""
    got = DP.score_distribution(None, 0)
    assert got["parsed"] is False
    assert set(got) == {"parsed", "argmax_correct", "p_correct", "argmax_index",
                        "margin", "distribution"}
    assert all(got[k] is None for k in got if k != "parsed")


# ---------------------------------------------------------------------------
# One completion under both readings
# ---------------------------------------------------------------------------


def test_a_row_the_frozen_parser_lost_is_flagged_as_recovered_by_widening():
    """This flag IS the finding: it counts exactly the replies the contract
    scored as silence and the widened reading scored as an answer."""
    got = DP.dual_score(_meta(2), DOUBLED_REPLY)
    assert got["frozen"]["parsed"] is False
    assert got["widened"]["parsed"] is True
    assert got["widened"]["argmax_correct"] is True
    assert got["recovered_by_widening"] is True
    assert got["widened_reason"] == DP.DOUBLED


def test_a_row_both_readings_parse_is_not_flagged_as_recovered():
    """Otherwise the recovered count would be the parse rate, and the report
    would claim widening bought something on every ordinary reply."""
    got = DP.dual_score(_meta(2), CLEAN_REPLY)
    assert got["frozen"]["parsed"] and got["widened"]["parsed"]
    assert got["recovered_by_widening"] is False
    assert got["widened_reason"] is None


def test_a_row_neither_reading_parses_is_not_flagged_as_recovered():
    """A reply that never answered stays unanswered under both readings."""
    got = DP.dual_score(_meta(2), NO_ANSWER_REPLY)
    assert got["frozen"]["parsed"] is False and got["widened"]["parsed"] is False
    assert got["recovered_by_widening"] is False
    assert got["readings_disagree_on_argmax"] is False


def test_an_empty_completion_is_scored_as_a_failure_under_both_readings():
    """API calls come back empty. That is a parse failure, not a crash."""
    got = DP.dual_score(_meta(0), "")
    assert got["frozen"]["parsed"] is False and got["widened"]["parsed"] is False
    assert got["widened_reason"] is None
    assert got["raw_response"] == ""


def test_the_two_readings_never_disagree_on_argmax_when_both_parse():
    """By construction the widened window is a suffix of the completion, so when
    the frozen parser also succeeds both readings are reading the same labels
    and the same numbers. The flag exists to prove that, and a True here would
    mean widening had changed a scored answer rather than recovered a lost one."""
    for reply, correct in ((CLEAN_REPLY, 2), (CLEAN_REPLY, 0),
                           ("A: 0.25 B: 0.25 C: 0.25 D: 0.25", 3)):
        got = DP.dual_score(_meta(correct), reply)
        assert got["frozen"]["parsed"] and got["widened"]["parsed"]
        assert got["readings_disagree_on_argmax"] is False


def test_the_row_carries_the_identifiers_a_table_is_grouped_by():
    """The two tables are built from these records without re-reading anything,
    so a record that loses its arm or its item id cannot be grouped."""
    got = DP.dual_score(_meta(2, item_id="C9:T:1"), CLEAN_REPLY)
    assert got["item_id"] == "C9:T:1"
    assert got["arm"] == "zeroinfo_redacted"
    assert got["variant"] == "v4"
    assert got["correct_index"] == 2
    assert got["raw_response"].startswith("C reads most like the guest.")


# ---------------------------------------------------------------------------
# The tables
# ---------------------------------------------------------------------------


def _records() -> list:
    """Three rows: one solved, one wrong, one that never answered."""
    return [
        DP.dual_score(_meta(2, "solved"), CLEAN_REPLY),
        DP.dual_score(_meta(0, "wrong"), CLEAN_REPLY),
        DP.dual_score(_meta(2, "silent"), NO_ANSWER_REPLY),
    ]


def test_rates_are_computed_on_the_parsed_subset_and_report_that_n():
    """A rate quoted without its N hides the whole point of running two
    parsers: the frozen and widened numbers sit on different denominators."""
    table = DP.accuracy_table(_records(), "frozen")
    assert table["n_prompts"] == 3
    assert table["n_parsed"] == 2
    assert table["n_parse_failures"] == 1
    assert table["n_argmax_correct"] == 1
    assert table["argmax_accuracy"] == 0.5          # 1 of 2 parsed, not of 3
    assert table["mean_prob_mass_correct"] == pytest.approx(0.35)
    assert table["mean_margin"] == pytest.approx(-0.05)
    assert table["min_margin"] == pytest.approx(-0.5)
    assert table["max_margin"] == pytest.approx(0.4)


def test_the_widened_table_counts_the_rows_the_frozen_one_lost():
    """The two tables are the deliverable. They must move apart exactly on the
    recovered rows and nowhere else."""
    records = _records() + [DP.dual_score(_meta(2, "doubled"), DOUBLED_REPLY)]
    frozen = DP.accuracy_table(records, "frozen")
    widened = DP.accuracy_table(records, "widened")
    assert frozen["n_parsed"] == 2 and widened["n_parsed"] == 3
    assert frozen["n_argmax_correct"] == 1 and widened["n_argmax_correct"] == 2


def test_a_table_over_nothing_but_parse_failures_reports_none_rates():
    """Round 3 came within three replies of this. An accuracy of "0.0" on zero
    parsed replies would be a fabricated number; None says there is none."""
    table = DP.accuracy_table([DP.dual_score(_meta(0), NO_ANSWER_REPLY)],
                              "frozen")
    assert table["n_parsed"] == 0
    assert table["n_parse_failures"] == 1
    assert table["argmax_accuracy"] is None
    assert table["mean_prob_mass_correct"] is None
    assert table["mean_margin"] is None
    assert table["min_margin"] is None and table["max_margin"] is None


def test_an_empty_record_set_is_a_table_of_nothing_rather_than_a_crash():
    """An arm that produced no rows must still render a table, or the report
    silently drops it."""
    table = DP.accuracy_table([], "widened")
    assert table["n_prompts"] == 0 and table["n_parsed"] == 0
    assert table["argmax_accuracy"] is None


def test_asking_for_a_reading_that_does_not_exist_is_refused():
    """The reading name is what a report labels its column with. A typo must
    stop the run rather than quietly produce a table of the wrong parser."""
    with pytest.raises(ValueError):
        DP.accuracy_table(_records(), "loosened")
    with pytest.raises(ValueError):
        DP.accuracy_table(_records(), "Frozen")


def test_both_readings_carries_both_tables_the_recovered_count_and_the_note():
    """Round 3 had one number and a footnote. The block exists so a reader gets
    the contract number, the alternative, and the statement that the contract is
    still the contract, in one place and never one without the others."""
    records = _records() + [DP.dual_score(_meta(2, "doubled"), DOUBLED_REPLY)]
    block = DP.both_readings(records)
    assert block["frozen"]["reading"] == "frozen"
    assert block["widened"]["reading"] == "widened"
    assert block["n_recovered_by_widening"] == 1
    assert block["n_readings_disagree_on_argmax"] == 0
    assert "FROZEN parser is the contract number" in block["contract_note"]
    assert "bar-lock decision" in block["contract_note"]
