"""Tests for the RIASEC loader (src/doppler/data.py).

These run against the real downloaded dataset in ``data/riasec``. If that data
is absent (e.g. a fresh checkout without the gitignored data), the tests skip
rather than fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doppler.data import (
    CATEGORICAL_DEMOGRAPHICS,
    RAW_DEMOGRAPHICS,
    RIASEC_ITEMS,
    TIPI_ITEMS,
    clean_riasec,
    load_codebook,
    load_riasec,
    person_record,
    sample_eval_persons,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "riasec" / "data.csv").exists(),
    reason="RIASEC data.csv not present (data/ is gitignored)",
)


# --- shared fixtures ------------------------------------------------------


@pytest.fixture(scope="module")
def raw_df():
    return load_riasec(DATA_DIR)


@pytest.fixture(scope="module")
def codebook():
    return load_codebook(DATA_DIR)


@pytest.fixture(scope="module")
def clean_df(raw_df):
    return clean_riasec(raw_df)


# --- (a) loader returns the expected column set ---------------------------


def test_loader_column_set(raw_df):
    cols = set(raw_df.columns)
    assert "person_id" in cols
    for col in RIASEC_ITEMS + TIPI_ITEMS:
        assert col in cols, f"missing item column {col}"
    for col in CATEGORICAL_DEMOGRAPHICS + RAW_DEMOGRAPHICS:
        assert col in cols, f"missing demographic column {col}"
    # The trailing-tab artifact column must have been dropped.
    assert not any(str(c).startswith("Unnamed") for c in raw_df.columns)


def test_person_id_is_zero_based_row_index(raw_df):
    assert raw_df["person_id"].tolist() == list(range(len(raw_df)))


# --- (b) cleaned data has no out-of-range values --------------------------


def test_clean_has_no_out_of_range(clean_df):
    assert len(clean_df) > 0
    for col in RIASEC_ITEMS:
        assert clean_df[col].between(1, 5).all(), f"{col} out of 1-5 after cleaning"
    for col in TIPI_ITEMS:
        assert clean_df[col].between(1, 7).all(), f"{col} out of 1-7 after cleaning"
    assert clean_df["age"].between(14, 90).all()
    country = clean_df["country"].astype("string")
    assert country.notna().all()
    assert (country != "NONE").all()
    assert (country.str.strip() != "").all()


def test_clean_is_subset_and_smaller(raw_df, clean_df):
    assert len(clean_df) <= len(raw_df)
    assert set(clean_df["person_id"]).issubset(set(raw_df["person_id"]))


# --- (c) codebook has exactly 48 RIASEC + 10 TIPI, none empty -------------


def test_codebook_item_counts(codebook):
    assert len(codebook.riasec_items) == 48
    assert len(codebook.tipi_items) == 10
    assert set(codebook.riasec_items) == set(RIASEC_ITEMS)
    assert set(codebook.tipi_items) == set(TIPI_ITEMS)


def test_codebook_texts_nonempty(codebook):
    for code, text in codebook.riasec_items.items():
        assert text.strip(), f"empty text for {code}"
    for code, text in codebook.tipi_items.items():
        assert text.strip(), f"empty text for {code}"


def test_codebook_scales_and_decoders(codebook):
    assert codebook.scales["riasec"]["anchors"][1]  # e.g. "Dislike"
    assert codebook.scales["riasec"]["anchors"][5]  # e.g. "Enjoy"
    assert len(codebook.scales["tipi"]["anchors"]) == 7
    # every categorical demographic has a decoder with at least 2 codes
    for var in CATEGORICAL_DEMOGRAPHICS:
        assert var in codebook.demographic_decoders, f"no decoder for {var}"
        assert len(codebook.demographic_decoders[var]) >= 2


# --- (d) person_record structure ------------------------------------------


def test_person_record_structure(clean_df, codebook):
    row = clean_df.iloc[0]
    rec = person_record(row, codebook)

    assert set(rec) == {"person_id", "demographics", "interests", "tipi"}
    assert isinstance(rec["person_id"], int)

    # interests: 48 items, ordered, each with text + int answer in range
    assert list(rec["interests"]) == RIASEC_ITEMS
    for code, entry in rec["interests"].items():
        assert set(entry) == {"text", "answer"}
        assert entry["text"].strip()
        assert isinstance(entry["answer"], int)
        assert 1 <= entry["answer"] <= 5

    # tipi: 10 items, ordered, each with text + int answer in range
    assert list(rec["tipi"]) == TIPI_ITEMS
    for code, entry in rec["tipi"].items():
        assert set(entry) == {"text", "answer"}
        assert entry["text"].strip()
        assert isinstance(entry["answer"], int)
        assert 1 <= entry["answer"] <= 7

    # demographics: decoded categoricals are strings (or None), plus raw fields
    demo = rec["demographics"]
    for var in CATEGORICAL_DEMOGRAPHICS:
        assert var in demo
        assert demo[var] is None or isinstance(demo[var], str)
    assert demo["age"] is None or isinstance(demo["age"], int)
    assert "country" in demo
    assert "major" in demo  # raw free text or None


def test_person_record_decodes_against_codebook(clean_df, codebook):
    row = clean_df.iloc[0]
    rec = person_record(row, codebook)
    demo = rec["demographics"]
    for var in CATEGORICAL_DEMOGRAPHICS:
        if demo[var] is not None:
            assert demo[var] in codebook.demographic_decoders[var].values()


# --- (e) sample_eval_persons is deterministic -----------------------------


def test_sample_deterministic(clean_df):
    a = sample_eval_persons(clean_df, 100, seed=42)
    b = sample_eval_persons(clean_df, 100, seed=42)
    assert a == b
    assert len(a) == 100
    assert len(set(a)) == 100  # distinct
    assert set(a).issubset(set(clean_df["person_id"]))


def test_sample_different_seed_differs(clean_df):
    a = sample_eval_persons(clean_df, 100, seed=42)
    c = sample_eval_persons(clean_df, 100, seed=43)
    assert a != c


def test_sample_too_many_raises(clean_df):
    with pytest.raises(ValueError):
        sample_eval_persons(clean_df, len(clean_df) + 1, seed=0)
