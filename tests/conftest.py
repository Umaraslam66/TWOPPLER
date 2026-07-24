"""Shared synthetic fixtures: a fake codebook + person record.

These are fully synthetic so the prompt/gym/scoring tests run with no data
files and no API access. Item texts are deliberately distinctive tokens so a
leak of any TIPI/interest text into the wrong place is unambiguous.
"""

from __future__ import annotations

from collections import OrderedDict

import pytest

from doppler.data import RIASEC_ITEMS, TIPI_ITEMS, Codebook


@pytest.fixture
def fake_codebook() -> Codebook:
    return Codebook(
        riasec_items={code: f"INTERESTTEXT_{code}_activity" for code in RIASEC_ITEMS},
        tipi_items={code: f"TIPITEXT_{code}_trait" for code in TIPI_ITEMS},
        demographic_decoders={
            "gender": {1: "Male", 2: "Female", 3: "Other"},
            "education": {1: "High school", 3: "University degree"},
        },
        scales={
            "riasec": {"min": 1, "max": 5,
                       "anchors": {1: "Dislike", 3: "Neutral", 5: "Enjoy"}},
            "tipi": {"min": 1, "max": 7,
                     "anchors": {i: f"ANCHOR{i}" for i in range(1, 8)}},
        },
    )


def _make_record(person_id: int, demographics: dict) -> dict:
    interests = OrderedDict(
        (code, {"text": f"INTERESTTEXT_{code}_activity", "answer": (i % 5) + 1})
        for i, code in enumerate(RIASEC_ITEMS)
    )
    tipi = OrderedDict(
        (code, {"text": f"TIPITEXT_{code}_trait", "answer": (i % 7) + 1})
        for i, code in enumerate(TIPI_ITEMS)
    )
    return {
        "person_id": person_id,
        "demographics": demographics,
        "interests": interests,
        "tipi": tipi,
    }


@pytest.fixture
def full_demographics() -> dict:
    return {
        "gender": "Male",
        "education": "University degree",
        "urban": "Urban (town, city)",
        "engnat": "Yes",
        "religion": "Atheist",
        "orientation": "Heterosexual",
        "race": "Other",
        "voted": "No",
        "married": "Never married",
        "hand": "Right",
        "age": 33,
        "familysize": 2,
        "country": "US",
        "major": "physics",
    }


@pytest.fixture
def synthetic_record(full_demographics) -> dict:
    return _make_record(777, full_demographics)


@pytest.fixture
def record_factory():
    return _make_record
