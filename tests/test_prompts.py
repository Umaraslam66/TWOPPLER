"""Prompt-construction tests: structure, missing-value omission, arm symmetry."""

from __future__ import annotations

from doppler.prompts import (
    build_profile,
    build_prompt,
    select_interest_items,
)


def test_twin_profile_has_interests_baseline_does_not(synthetic_record, fake_codebook):
    twin = build_profile(synthetic_record, fake_codebook, include_interests=True)
    base = build_profile(synthetic_record, fake_codebook, include_interests=False)
    assert "HOW I RATED MY INTEREST IN VARIOUS ACTIVITIES" in twin
    assert "HOW I RATED" not in base
    assert "(Scale: 1=Dislike, 3=Neutral, 5=Enjoy)" in twin
    # every interest text + rating present in twin
    for code, entry in synthetic_record["interests"].items():
        assert f"- {entry['text']}: {entry['answer']}" in twin
        assert entry["text"] not in base


def test_prompt_structure_and_scale_from_codebook(synthetic_record, fake_codebook):
    profile = build_profile(synthetic_record, fake_codebook, include_interests=True)
    prompt = build_prompt(profile, "TIPI1", fake_codebook)
    assert prompt.startswith("You are simulating a specific, real survey respondent.")
    assert "MY PROFILE" in prompt
    assert "YOUR TASK" in prompt
    # TIPI scale anchors come from the codebook, not hardcoded
    assert "1=ANCHOR1, 2=ANCHOR2, 3=ANCHOR3, 4=ANCHOR4, 5=ANCHOR5, 6=ANCHOR6, 7=ANCHOR7" in prompt
    assert 'I see myself as: TIPITEXT_TIPI1_trait' in prompt
    assert prompt.rstrip().endswith(
        "Respond with a single integer from 1 to 7 and nothing else."
    )


def test_missing_values_are_omitted_no_none_artifacts(record_factory, fake_codebook):
    demo = {
        "gender": None,         # missing -> fall back to age-only sentence
        "education": None,
        "urban": None,
        "engnat": None,
        "religion": None,
        "orientation": None,
        "race": None,
        "voted": None,
        "married": None,
        "hand": None,
        "age": 40,
        "familysize": None,
        "country": "US",
        "major": "",            # blank string -> treated as missing
    }
    rec = record_factory(5, demo)
    prompt = build_prompt(
        build_profile(rec, fake_codebook, include_interests=True), "TIPI3", fake_codebook
    )
    assert "None" not in prompt
    assert "nan" not in prompt
    assert "Religion:" not in prompt
    assert "College major" not in prompt
    assert "I am 40 years old." in prompt   # gender missing -> age-only fragment
    assert "My country: US." in prompt


def test_familysize_zero_is_kept(record_factory, fake_codebook, full_demographics):
    demo = dict(full_demographics)
    demo["familysize"] = 0
    rec = record_factory(9, demo)
    prompt = build_profile(rec, fake_codebook, include_interests=False)
    assert "Number of children my parents had, including me: 0." in prompt


def test_arms_differ_only_by_interests_block(synthetic_record, fake_codebook):
    twin_profile = build_profile(synthetic_record, fake_codebook, include_interests=True)
    base_profile = build_profile(synthetic_record, fake_codebook, include_interests=False)
    twin = build_prompt(twin_profile, "TIPI2", fake_codebook)
    base = build_prompt(base_profile, "TIPI2", fake_codebook)

    # The interests block is the ONLY thing that differs.
    block = twin_profile.split("\n\n", 1)[1]  # everything after the demographics block
    assert block.startswith("HOW I RATED")
    assert twin.replace("\n\n" + block, "") == base

    # Line-level: lines unique to twin are exactly the interest-block lines.
    twin_only = [ln for ln in twin.splitlines() if ln not in set(base.splitlines())]
    assert twin_only  # non-empty
    for ln in twin_only:
        assert ln.startswith("HOW I RATED") or ln.startswith("(Scale:") or ln.startswith("- ")


def test_select_interest_items_deterministic_and_ordered():
    a = select_interest_items(person_id=123, k=10, seed=42)
    b = select_interest_items(person_id=123, k=10, seed=42)
    assert a == b
    assert len(a) == 10
    # canonical order preserved (subset of RIASEC_ITEMS in original order)
    from doppler.data import RIASEC_ITEMS
    assert a == [c for c in RIASEC_ITEMS if c in set(a)]
    # different person -> (very likely) different subset
    c = select_interest_items(person_id=124, k=10, seed=42)
    assert a != c
    # k >= 48 returns all in canonical order
    assert select_interest_items(1, 48, 42) == list(RIASEC_ITEMS)
    assert select_interest_items(1, 99, 42) == list(RIASEC_ITEMS)
