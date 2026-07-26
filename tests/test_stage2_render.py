"""Tests for the Stage 2 forced-choice prompt renderer (SPEC D8).

All fixtures are synthetic. No network, no data files, nothing random.
"""

from __future__ import annotations

import hashlib

import pytest

from doppler import stage2_render as R


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEGMENTS = [
    {
        "date": "2011-03-02",
        "program": "MORNING EDITION",
        "exchanges": [
            {"host_text": "You left the ministry in 2009. Why then?",
             "guest_text": "Because the audit was buried."},
            {"host_text": "And nobody backed you?",
             "guest_text": "Two colleagues did, quietly."},
        ],
    },
    {
        "date": "2013-04-29",
        "program": "ALL THINGS CONSIDERED",
        "exchanges": [
            {"host_text": "What would you tell a young official?",
             "guest_text": "Keep your own copy of everything."},
        ],
    },
]

OPTIONS = ["First reply text.", "Second reply text.", "Third reply text.",
           "Fourth reply text."]
QUESTION = "So what did you learn from all of that?"


def _grounding(budget=2000):
    return R.render_grounding(SEGMENTS, budget_words=budget)


def _speech_words(block):
    """Words in HOST/GUEST lines only -- what the budget actually caps."""
    total = 0
    for line in block.splitlines():
        if line.startswith("HOST: ") or line.startswith("GUEST: "):
            total += len(line.split()) - 1
    return total


# ---------------------------------------------------------------------------
# Frozen templates
# ---------------------------------------------------------------------------


def test_template_digest_is_frozen():
    # Re-freeze deliberately if a template changes; never "fix" this literal
    # to make a red suite green.
    assert R.TEMPLATE_SHA256 == (
        "032f751fe3d113539d4e9ccdf5a4b69e6108931e916f06054ae6918c62120d9f"
    )
    assert R.TEMPLATE_SHA256 == R.sha256(R.TEMPLATE_TEXT)


def test_sha256_helper_matches_hashlib():
    assert R.sha256("hello") == hashlib.sha256(b"hello").hexdigest()


def test_arms_are_the_five_d8_arms_in_spec_order():
    assert R.ARMS == ("twin_redacted", "twin_named", "zeroinfo_redacted",
                      "zeroinfo_named", "imposter_redacted")
    assert R.GROUNDED_ARMS == {"twin_redacted", "twin_named",
                               "imposter_redacted"}
    assert R.NAMED_ARMS == {"twin_named", "zeroinfo_named"}


def test_spec_fixed_sentences_are_verbatim():
    assert R.ZEROINFO_PREAMBLE == (
        "A person was interviewed on American broadcast news. Predict which "
        "answer they gave."
    )
    assert R.TWIN_NAME_LINE.format(name="Jane Smith") == "GUEST is Jane Smith."
    assert (R.ZEROINFO_NAME_LINE.format(name="Jane Smith")
            == "The person is Jane Smith.")


def test_distribution_instruction_shows_the_uniform_example():
    assert R.distribution_instruction(4).endswith(
        "A: 0.25 B: 0.25 C: 0.25 D: 0.25")
    assert R.distribution_instruction(2).endswith("A: 0.50 B: 0.50")


def test_budget_and_shingle_constants_match_the_spec():
    assert R.GROUNDING_BUDGET_WORDS == 2000
    assert R.SHINGLE_WORDS == 10
    assert (R.MIN_MASS, R.MAX_MASS) == (0.8, 1.2)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def test_redact_replaces_every_case():
    out = R.redact("Smith spoke. SMITH agreed. smith left.", ["Smith"])
    assert out == "GUEST spoke. GUEST agreed. GUEST left."


def test_redact_takes_the_longest_variant_first():
    out = R.redact("Jane Smith spoke.", ["Smith", "Jane Smith"])
    assert out == "GUEST spoke."


def test_redact_handles_possessives():
    assert R.redact("Smith's view", ["Smith"]) == "GUEST's view"
    assert R.redact("Jane Smith's view", ["Jane Smith"]) == "GUEST's view"


def test_redact_is_word_boundary_safe():
    text = "The Smithsonian hired a blacksmith named Smithy."
    assert R.redact(text, ["Smith"]) == text


def test_redact_swallows_an_honorific_in_front():
    assert R.redact("Mr. Smith said", ["Smith"]) == "GUEST said"
    assert R.redact("Senator Smith said", ["Smith"]) == "GUEST said"
    assert R.redact("DR. SMITH said", ["Smith"]) == "GUEST said"


def test_redact_matches_a_variant_that_itself_carries_an_honorific():
    # Pool variant has the title, the transcript does not.
    assert R.redact("Jane Smith said", ["Dr. Jane Smith"]) == "GUEST said"
    assert R.redact("Dr. Jane Smith said", ["Dr. Jane Smith"]) == "GUEST said"


def test_redact_matches_across_a_line_break():
    assert R.redact("Jane\nSmith said", ["Jane Smith"]) == "GUEST said"


def test_redact_accepts_a_custom_placeholder():
    assert R.redact("Smith said", ["Smith"], placeholder="X") == "X said"


def test_redact_with_no_variants_is_the_identity():
    assert R.redact("Smith said", []) == "Smith said"
    assert R.redact("", ["Smith"]) == ""


def test_redact_never_rewrites_its_own_output():
    # A single pass: an existing GUEST in the text is left alone, and a
    # variant that contains another variant is not replaced twice.
    out = R.redact("GUEST met Jane Smith and Smith left.",
                   ["Jane Smith", "Smith"])
    assert out == "GUEST met GUEST and GUEST left."


def test_variant_forms_are_longest_first_and_deduplicated():
    forms = R.variant_forms(["Smith", "smith", "Jane Smith", "Dr. Jane Smith"])
    assert forms == ["Dr. Jane Smith", "Jane Smith", "Smith"]


def test_expand_variants_adds_single_name_tokens():
    assert R.expand_variants(["Frederic Hof"]) == ["Frederic Hof", "Frederic",
                                                   "Hof"]


def test_expand_variants_drops_initials_and_short_tokens():
    assert "R" not in R.expand_variants(["R. Harris"])
    assert "Harris" in R.expand_variants(["R. Harris"])


def test_expansion_is_what_catches_a_bare_surname():
    text = "Hof told us the deal was dead."
    assert R.redact(text, ["Frederic Hof"]) == text          # the hole
    assert R.redact(text, R.expand_variants(["Frederic Hof"])) == (
        "GUEST told us the deal was dead.")


# ---------------------------------------------------------------------------
# Grounding block
# ---------------------------------------------------------------------------


def test_grounding_renders_chronologically_whatever_the_input_order():
    forward = R.render_grounding(SEGMENTS)
    backward = R.render_grounding(list(reversed(SEGMENTS)))
    assert forward.index("2011-03-02") < forward.index("2013-04-29")
    assert backward.index("2011-03-02") < backward.index("2013-04-29")
    assert forward.splitlines()[0] == (
        "[Interview, 2011-03-02, MORNING EDITION]")


def test_grounding_shape_is_the_d8_shape():
    lines = _grounding().splitlines()
    assert lines[0] == "[Interview, 2011-03-02, MORNING EDITION]"
    assert lines[1].startswith("HOST: ")
    assert lines[2].startswith("GUEST: ")
    assert lines[3] == ""            # blank line between exchanges
    assert "[Interview, 2013-04-29, ALL THINGS CONSIDERED]" in lines
    # One header per segment that contributed an exchange, no more.
    assert sum(1 for line in lines if line.startswith("[Interview,")) == 2


def test_grounding_keeps_the_newest_when_the_budget_is_tight():
    # The 2013 exchange is 13 words; a 15-word budget can hold only it.
    block = R.render_grounding(SEGMENTS, budget_words=15)
    assert "2013-04-29" in block
    assert "2011-03-02" not in block
    assert _speech_words(block) <= 15


def test_grounding_fills_greedily_down_the_recency_order():
    block = R.render_grounding(SEGMENTS, budget_words=28)
    # Newest first: 2013 (13 words), then the later 2011 exchange (8), then
    # the earlier one (13) no longer fits.
    assert "And nobody backed you?" in block
    assert "You left the ministry" not in block
    assert _speech_words(block) <= 28


def test_grounding_skips_an_oversized_exchange_and_keeps_filling():
    segments = [
        {"date": "2010-01-01", "program": "P",
         "exchanges": [{"host_text": "Short question?",
                        "guest_text": "Short answer."}]},
        {"date": "2020-01-01", "program": "Q",
         "exchanges": [{"host_text": "Q " * 40, "guest_text": "A " * 40}]},
    ]
    block = R.render_grounding(segments, budget_words=10)
    assert "Short question?" in block
    assert "2020-01-01" not in block


def test_grounding_never_truncates_an_exchange():
    block = R.render_grounding(SEGMENTS, budget_words=15)
    assert "GUEST: Keep your own copy of everything." in block


def test_grounding_uses_unknown_for_missing_date_or_program():
    segments = [{"exchanges": [{"host_text": "Q?", "guest_text": "A."}]}]
    assert R.render_grounding(segments).splitlines()[0] == (
        "[Interview, unknown, unknown]")


def test_grounding_normalizes_whitespace_inside_a_turn():
    segments = [{"date": "2010-01-01", "program": "P",
                 "exchanges": [{"host_text": " Why\n  now? ",
                                "guest_text": "Because\tso."}]}]
    block = R.render_grounding(segments)
    assert block.splitlines()[1:] == ["HOST: Why now?", "GUEST: Because so."]


def test_grounding_renders_a_one_sided_exchange_as_one_line():
    segments = [{"date": "2010-01-01", "program": "P",
                 "exchanges": [{"host_text": "", "guest_text": "Alone."},
                               {"host_text": "Only asked.", "guest_text": ""}]}]
    block = R.render_grounding(segments)
    assert block.splitlines() == ["[Interview, 2010-01-01, P]",
                                  "GUEST: Alone.", "", "HOST: Only asked."]


def test_grounding_is_deterministic():
    assert R.render_grounding(SEGMENTS) == R.render_grounding(SEGMENTS)


def test_grounding_rejects_an_empty_input():
    with pytest.raises(ValueError, match="no non-empty exchanges"):
        R.render_grounding([])
    with pytest.raises(ValueError, match="no non-empty exchanges"):
        R.render_grounding([{"date": "2010-01-01", "program": "P",
                             "exchanges": [{"host_text": " ",
                                            "guest_text": ""}]}])


def test_grounding_rejects_a_budget_nothing_fits():
    with pytest.raises(ValueError, match="no exchange fits"):
        R.render_grounding(SEGMENTS, budget_words=3)


def test_grounding_rejects_a_nonpositive_budget():
    with pytest.raises(ValueError, match="must be positive"):
        R.render_grounding(SEGMENTS, budget_words=0)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def _render(arm, **kwargs):
    kwargs.setdefault("question", QUESTION)
    kwargs.setdefault("options", OPTIONS)
    if arm in R.GROUNDED_ARMS:
        kwargs.setdefault("grounding_block", _grounding())
    if arm in R.NAMED_ARMS:
        kwargs.setdefault("name", "Jane Smith")
    return R.render_prompt(arm, **kwargs)


def test_all_five_arms_render_deterministically():
    for arm in R.ARMS:
        first, second = _render(arm), _render(arm)
        assert first == second
        assert R.sha256(first) == R.sha256(second)
        assert first.strip()


def test_the_five_arms_are_five_distinct_prompts_except_twin_and_imposter():
    digests = {arm: R.sha256(_render(arm)) for arm in R.ARMS}
    assert digests["twin_redacted"] == digests["imposter_redacted"]
    assert len(set(digests.values())) == 4


def test_twin_and_imposter_templates_are_byte_identical():
    kwargs = dict(question=QUESTION, options=OPTIONS,
                  grounding_block=_grounding())
    assert (R.render_prompt("twin_redacted", **kwargs)
            == R.render_prompt("imposter_redacted", **kwargs))
    # And nothing in the text names the arm.
    text = R.render_prompt("imposter_redacted", **kwargs)
    for word in ("imposter", "donor", "twin", "arm"):
        assert word not in text.lower()


def test_named_arms_add_exactly_one_line():
    for redacted, named, line in (
        ("twin_redacted", "twin_named", "GUEST is Jane Smith."),
        ("zeroinfo_redacted", "zeroinfo_named", "The person is Jane Smith."),
    ):
        base = _render(redacted).splitlines()
        with_name = _render(named).splitlines()
        assert line in with_name
        # The name line plus its blank separator are the only additions.
        assert [ln for ln in with_name if ln != line] == (
            base[:1] + [""] + base[1:])


def test_zeroinfo_arms_carry_no_excerpt_program_or_date():
    for arm in ("zeroinfo_redacted", "zeroinfo_named"):
        text = _render(arm)
        assert text.startswith(R.ZEROINFO_PREAMBLE)
        assert "[Interview," not in text
        assert "MORNING EDITION" not in text
        assert "2011-03-02" not in text
        assert R.EXCERPTS_HEADER not in text
        assert R.LATER_HEADER not in text


def test_twin_arms_carry_the_excerpts_and_the_later_interview_header():
    text = _render("twin_redacted")
    assert text.startswith(R.TWIN_PREAMBLE)
    assert f"{R.EXCERPTS_HEADER}\n[Interview, 2011-03-02, MORNING EDITION]" in text
    assert f"{R.LATER_HEADER}\nHOST: {QUESTION}" in text


def test_options_are_labelled_in_order_and_the_prompt_ends_with_the_format():
    text = _render("twin_redacted")
    assert "Which of these replies did GUEST give?" in text
    for label, option in zip("ABCD", OPTIONS):
        assert f"{label}. {option}" in text
    assert text.endswith("A: 0.25 B: 0.25 C: 0.25 D: 0.25")
    assert "Which of these replies did the person give?" in _render(
        "zeroinfo_redacted")


def test_stripped_options_use_the_same_template():
    stripped = ["[NAME] said [NUMBER].", "Second.", "Third.", "Fourth."]
    plain = _render("twin_redacted")
    entity = _render("twin_redacted", options=stripped)
    # Byte-identical apart from the option texts: swap them in and the two
    # prompts are the same string. That is what "no separate template" means.
    swapped = plain
    for before, after in zip(OPTIONS, stripped):
        swapped = swapped.replace(before, after)
    assert swapped == entity
    assert "[NAME] said [NUMBER]." in entity


def test_three_options_renumber_the_instruction():
    text = _render("zeroinfo_redacted", options=OPTIONS[:3])
    assert "C. Third reply text." in text
    assert "D." not in text
    assert text.endswith("A: 0.33 B: 0.33 C: 0.33")


def test_prompt_rejects_an_unknown_arm():
    with pytest.raises(ValueError, match="arm must be one of"):
        R.render_prompt("twin", QUESTION, OPTIONS)


def test_twin_arm_requires_a_grounding_block():
    with pytest.raises(ValueError, match="needs a grounding block"):
        R.render_prompt("twin_redacted", QUESTION, OPTIONS)
    with pytest.raises(ValueError, match="needs a grounding block"):
        R.render_prompt("twin_redacted", QUESTION, OPTIONS,
                        grounding_block="   ")


def test_zeroinfo_arm_refuses_a_grounding_block():
    with pytest.raises(ValueError, match="zero-information arm"):
        R.render_prompt("zeroinfo_redacted", QUESTION, OPTIONS,
                        grounding_block=_grounding())
    # An empty string is not a leak, so it is tolerated.
    assert R.render_prompt("zeroinfo_redacted", QUESTION, OPTIONS,
                           grounding_block="") == _render("zeroinfo_redacted")


def test_redacted_arms_refuse_a_name():
    for arm in ("twin_redacted", "imposter_redacted"):
        with pytest.raises(ValueError, match="would leak the identity"):
            R.render_prompt(arm, QUESTION, OPTIONS,
                            grounding_block=_grounding(), name="Jane Smith")
    with pytest.raises(ValueError, match="would leak the identity"):
        R.render_prompt("zeroinfo_redacted", QUESTION, OPTIONS,
                        name="Jane Smith")


def test_named_arms_require_a_name():
    with pytest.raises(ValueError, match="needs the subject's name"):
        R.render_prompt("zeroinfo_named", QUESTION, OPTIONS)
    with pytest.raises(ValueError, match="needs the subject's name"):
        R.render_prompt("twin_named", QUESTION, OPTIONS,
                        grounding_block=_grounding(), name=" ")


def test_prompt_rejects_bad_questions_and_options():
    with pytest.raises(ValueError, match="question is empty"):
        R.render_prompt("zeroinfo_redacted", "  ", OPTIONS)
    with pytest.raises(ValueError, match="at least 2 options"):
        R.render_prompt("zeroinfo_redacted", QUESTION, ["only one"])
    with pytest.raises(ValueError, match="option B is empty"):
        R.render_prompt("zeroinfo_redacted", QUESTION, ["a", " ", "c", "d"])


# ---------------------------------------------------------------------------
# Distribution parsing
# ---------------------------------------------------------------------------


def test_parse_the_canonical_line():
    assert R.parse_distribution("A: 0.7, B: 0.1, C: 0.1, D: 0.1") == pytest.approx(
        [0.7, 0.1, 0.1, 0.1])


def test_parse_one_pair_per_line():
    assert R.parse_distribution("A: 0.7\nB: 0.1\nC: 0.1\nD: 0.1") == pytest.approx(
        [0.7, 0.1, 0.1, 0.1])


def test_parse_percent_signs():
    assert R.parse_distribution("A: 70% B: 10% C: 10% D: 10%") == pytest.approx(
        [0.7, 0.1, 0.1, 0.1])
    assert R.parse_distribution("A: 70 % B: 10 % C: 10 % D: 10 %") == pytest.approx(
        [0.7, 0.1, 0.1, 0.1])


def test_parse_tolerates_separator_variants():
    for text in ("A:0.7 B:0.1 C:0.1 D:0.1",
                 "A) 0.7 B) 0.1 C) 0.1 D) 0.1",
                 "A = 0.7, B = 0.1, C = 0.1, D = 0.1",
                 "A. 0.7 B. 0.1 C. 0.1 D. 0.1",
                 "A - 0.7 | B - 0.1 | C - 0.1 | D - 0.1",
                 "a: .7 b: .1 c: .1 d: .1"):
        assert R.parse_distribution(text) == pytest.approx([0.7, 0.1, 0.1, 0.1]), text


def test_parse_ignores_prose_and_takes_the_last_complete_group():
    text = ("Let me think. The excerpts point to B.\n"
            "A: 0.1 B: 0.6 C: 0.2 D: 0.1\n"
            "On reflection:\n"
            "A: 0.7 B: 0.1 C: 0.1 D: 0.1")
    assert R.parse_distribution(text) == pytest.approx([0.7, 0.1, 0.1, 0.1])


def test_parse_accepts_reordered_labels_within_a_group():
    assert R.parse_distribution("D: 0.1 B: 0.1 A: 0.7 C: 0.1") == pytest.approx(
        [0.7, 0.1, 0.1, 0.1])


def test_parse_ignores_labels_outside_the_option_range():
    assert R.parse_distribution(
        "A: 0.7 B: 0.1 C: 0.1 D: 0.1 E: 0.9") == pytest.approx(
        [0.7, 0.1, 0.1, 0.1])


def test_parse_renormalizes_and_always_sums_to_one():
    out = R.parse_distribution("A: 0.4 B: 0.3 C: 0.2 D: 0.2")
    assert sum(out) == pytest.approx(1.0)
    assert out == pytest.approx([0.4 / 1.1, 0.3 / 1.1, 0.2 / 1.1, 0.2 / 1.1])


def test_parse_window_edges():
    # 0.8 and 1.2 are inside the window; float slack must not decide it.
    assert R.parse_distribution("A: 0.5 B: 0.1 C: 0.1 D: 0.1") is not None  # 0.8
    assert R.parse_distribution("A: 0.2 B: 0.2 C: 0.2 D: 0.2") is not None  # 0.8
    assert R.parse_distribution("A: 0.9 B: 0.1 C: 0.1 D: 0.1") is not None  # 1.2
    assert R.parse_distribution("A: 0.49 B: 0.1 C: 0.1 D: 0.1") is None    # 0.79
    assert R.parse_distribution("A: 0.91 B: 0.1 C: 0.1 D: 0.1") is None    # 1.21


def test_parse_rejects_incomplete_and_malformed_answers():
    assert R.parse_distribution(None) is None
    assert R.parse_distribution("") is None
    assert R.parse_distribution("I cannot say.") is None
    assert R.parse_distribution("A: 0.7 B: 0.3") is None            # missing C, D
    assert R.parse_distribution("A: 0.7 A: 0.1 B: 0.1 C: 0.1") is None
    assert R.parse_distribution("A: -0.1 B: 0.5 C: 0.3 D: 0.3") is None
    assert R.parse_distribution("A: 70 B: 10 C: 10 D: 10") is None  # no scale
    assert R.parse_distribution("A B C D") is None


def test_parse_supports_other_option_counts():
    assert R.parse_distribution("A: 0.5 B: 0.5", n_options=2) == pytest.approx(
        [0.5, 0.5])
    with pytest.raises(ValueError, match="n_options must be between"):
        R.parse_distribution("A: 1.0", n_options=1)


def test_parse_output_is_in_label_order():
    assert R.parse_distribution("A: 0.1 B: 0.2 C: 0.3 D: 0.4") == pytest.approx(
        [0.1, 0.2, 0.3, 0.4])


# ---------------------------------------------------------------------------
# Leakage guards
# ---------------------------------------------------------------------------

ANSWER = ("we walked out of the meeting because the numbers had been changed "
          "twice and nobody in the room would say who had changed them")


def test_answer_guard_passes_on_clean_grounding():
    R.assert_no_answer_leak(_grounding(), ANSWER)
    assert R.find_answer_leak(_grounding(), ANSWER) is None


def test_answer_guard_trips_on_a_verbatim_quote():
    block = f"[Interview, 2011-03-02, P]\nGUEST: Look, {ANSWER}."
    with pytest.raises(ValueError, match="true answer leaked"):
        R.assert_no_answer_leak(block, ANSWER)


def test_answer_guard_is_exact_at_ten_words():
    words = ANSWER.split()
    nine = "Filler start. " + " ".join(words[:9]) + ". Filler end."
    ten = "Filler start. " + " ".join(words[:10]) + ". Filler end."
    assert R.find_answer_leak(nine, ANSWER) is None
    assert R.find_answer_leak(ten, ANSWER) == " ".join(words[:10])
    R.assert_no_answer_leak(nine, ANSWER)
    with pytest.raises(ValueError):
        R.assert_no_answer_leak(ten, ANSWER)


def test_answer_guard_ignores_case_and_edge_punctuation():
    words = ANSWER.split()
    block = '"' + " ".join(w.upper() for w in words[:10]) + '," he said.'
    assert R.find_answer_leak(block, ANSWER) is not None


def test_answer_guard_falls_back_to_containment_for_a_short_answer():
    short = "the audit was buried"
    assert R.find_answer_leak(_grounding(), short) == short
    assert R.find_answer_leak("nothing like it here", short) is None


def test_answer_guard_diagnostic_names_the_shingle():
    words = ANSWER.split()
    block = " ".join(words[:12])
    with pytest.raises(ValueError) as excinfo:
        R.assert_no_answer_leak(block, ANSWER)
    assert " ".join(words[:10]) in str(excinfo.value)


def test_answer_guard_handles_empty_inputs():
    assert R.find_answer_leak("", ANSWER) is None
    assert R.find_answer_leak(_grounding(), "") is None


def test_redaction_guard_passes_on_a_redacted_prompt():
    variants = ["Jane Smith", "Smith"]
    text = R.render_prompt(
        "twin_redacted",
        R.redact("Ms. Smith, what did you learn?", variants),
        [R.redact(o, variants) for o in OPTIONS],
        grounding_block=R.redact(_grounding(), variants),
    )
    R.assert_redacted(text, variants)
    assert R.surviving_variants(text, variants) == []


def test_redaction_guard_trips_on_a_name_left_in_the_question():
    variants = ["Jane Smith", "Smith"]
    text = R.render_prompt("twin_redacted", "Ms. Smith, what did you learn?",
                           OPTIONS, grounding_block=_grounding())
    with pytest.raises(ValueError, match="redaction failed"):
        R.assert_redacted(text, variants)


def test_redaction_guard_trips_on_a_name_left_in_an_option():
    variants = ["Jane Smith"]
    options = list(OPTIONS)
    options[2] = "As Jane Smith told the committee, the file was closed."
    text = R.render_prompt("zeroinfo_redacted", QUESTION, options)
    with pytest.raises(ValueError, match="redaction failed"):
        R.assert_redacted(text, variants)


def test_redaction_guard_trips_on_a_name_left_in_the_excerpts():
    variants = ["Jane Smith"]
    segments = [{"date": "2010-01-01", "program": "P",
                 "exchanges": [{"host_text": "Jane Smith, welcome.",
                                "guest_text": "Thanks for having me."}]}]
    text = R.render_prompt("twin_redacted", QUESTION, OPTIONS,
                           grounding_block=R.render_grounding(segments))
    with pytest.raises(ValueError, match="redaction failed"):
        R.assert_redacted(text, variants)


def test_redaction_guard_diagnostic_lists_the_survivors():
    with pytest.raises(ValueError) as excinfo:
        R.assert_redacted("Senator Smith and Smith's aide", ["Smith"])
    message = str(excinfo.value)
    assert "2 name variant(s)" in message
    assert "Senator Smith" in message


def test_redaction_guard_is_exactly_as_strong_as_the_scrubber():
    # Whatever redact removes, the guard finds; and it never trips on
    # something redact could not have removed.
    variants = ["Smith"]
    text = "The Smithsonian called Mr. Smith about Smith's testimony."
    with pytest.raises(ValueError):
        R.assert_redacted(text, variants)
    R.assert_redacted(R.redact(text, variants), variants)


def test_redaction_guard_expand_flag_catches_a_bare_surname():
    variants = ["Frederic Hof"]
    text = "HOST: Hof, is the deal dead?"
    R.assert_redacted(text, variants)                       # default: misses it
    with pytest.raises(ValueError, match="redaction failed"):
        R.assert_redacted(text, variants, expand=True)
    R.assert_redacted(R.redact(text, R.expand_variants(variants)), variants,
                      expand=True)


def test_named_arms_are_not_subject_to_the_redaction_guard():
    # Sanity: the guard would of course trip on a named arm. Documented so no
    # one wires it into the wrong arm.
    text = _render("twin_named")
    with pytest.raises(ValueError):
        R.assert_redacted(text, ["Jane Smith"])
