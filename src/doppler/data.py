"""Loader and cleaner for the OpenPsychometrics RIASEC Stage-1 dataset.

The raw files (``data.csv`` and ``codebook.txt``) come from the mirror
``github.com/haghish/openpsychometrics`` (folder ``RIASEC_data12Dec2018``).
Despite the ``.csv`` extension the data file is TAB-separated.

Item texts, scale anchors, and demographic code -> label mappings are parsed
from the shipped ``codebook.txt`` at runtime -- nothing is hard-coded from memory.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Canonical column groups (order matters for person records)
# ---------------------------------------------------------------------------

#: The 48 RIASEC interest items, in canonical R->I->A->S->E->C, 1..8 order.
RIASEC_ITEMS: list[str] = [f"{letter}{i}" for letter in "RIASEC" for i in range(1, 9)]

#: The 10 Ten-Item-Personality-Inventory items.
TIPI_ITEMS: list[str] = [f"TIPI{i}" for i in range(1, 11)]

#: The 16 vocabulary check-list items.
VCL_ITEMS: list[str] = [f"VCL{i}" for i in range(1, 17)]

#: Categorical demographics that have a code -> label decoding in the codebook.
CATEGORICAL_DEMOGRAPHICS: list[str] = [
    "education",
    "urban",
    "gender",
    "engnat",
    "hand",
    "religion",
    "orientation",
    "race",
    "voted",
    "married",
]

#: Demographics kept as raw numeric / free-text values (no code decoding).
RAW_DEMOGRAPHICS: list[str] = ["age", "familysize", "country", "major"]

# Valid response ranges. 0 encodes "missing" in this dataset.
RIASEC_VALID = (1, 5)
TIPI_VALID = (1, 7)
AGE_VALID = (14, 90)


# ---------------------------------------------------------------------------
# Codebook
# ---------------------------------------------------------------------------


@dataclass
class Codebook:
    """Structured view of ``codebook.txt``.

    Attributes:
        riasec_items: item code -> exact statement text (48 entries).
        tipi_items: item code -> exact statement text (10 entries).
        demographic_decoders: variable name -> {integer code -> label}.
        scales: scale name ("riasec"/"tipi") -> {"min", "max", "anchors"}.
    """

    riasec_items: dict[str, str] = field(default_factory=dict)
    tipi_items: dict[str, str] = field(default_factory=dict)
    demographic_decoders: dict[str, dict[int, str]] = field(default_factory=dict)
    scales: dict[str, dict] = field(default_factory=dict)


def _resolve_files(data_dir: str | Path) -> tuple[Path, Path]:
    """Return (data.csv, codebook.txt) paths, tolerating ``data`` or ``data/riasec``."""
    base = Path(data_dir)
    candidates = [base, base / "riasec"]
    for cand in candidates:
        data_csv = cand / "data.csv"
        codebook = cand / "codebook.txt"
        if data_csv.exists():
            return data_csv, codebook
    raise FileNotFoundError(
        f"Could not find data.csv under {base} or {base / 'riasec'}. "
        "Expected the downloaded RIASEC dataset directory."
    )


def _parse_decode_pairs(text: str) -> dict[int, str]:
    """Parse ``1=Label, 2=Other label, ...`` where labels may contain commas.

    A label runs up to the next ``, <digits>=`` boundary or end of string, so
    parentheticals with internal commas (e.g. the race option) survive intact.
    """
    pairs: dict[int, str] = {}
    for match in re.finditer(r"(\d+)\s*=\s*(.+?)(?=,\s*\d+\s*=|$)", text):
        code = int(match.group(1))
        label = match.group(2).strip().rstrip(".").strip()
        pairs[code] = label
    return pairs


def load_codebook(data_dir: str | Path) -> Codebook:
    """Parse ``codebook.txt`` into a :class:`Codebook`."""
    _, codebook_path = _resolve_files(data_dir)
    raw = codebook_path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()

    cb = Codebook()

    # --- RIASEC item statements: "R1<TAB>Test the quality of parts before shipment"
    for line in lines:
        m = re.match(r"^([RIASEC][1-8])\s+(\S.*)$", line)
        if m:
            cb.riasec_items[m.group(1)] = m.group(2).strip()

    # --- TIPI item statements: "TIPI1<TAB>Extraverted, enthusiastic."
    for line in lines:
        m = re.match(r"^(TIPI\d+)\s+(\S.*)$", line)
        if m:
            cb.tipi_items[m.group(1)] = m.group(2).strip()

    # --- RIASEC response scale anchors (inline in the intro paragraph):
    #     "... with the labels 1=Dislike, 3=Neutral, 5=Enjoy."
    riasec_anchor_line = next(
        (ln for ln in lines if "1=Dislike" in ln or "1 = Dislike" in ln), ""
    )
    cb.scales["riasec"] = {
        "min": RIASEC_VALID[0],
        "max": RIASEC_VALID[1],
        "anchors": _parse_decode_pairs(riasec_anchor_line),
    }

    # --- TIPI response scale anchors: one "N = Label" per line (keys 1..7).
    tipi_anchors: dict[int, str] = {}
    for line in lines:
        m = re.match(r"^(\d+)\s*=\s*(\S.*)$", line)
        if m:
            code = int(m.group(1))
            if 1 <= code <= 7:
                tipi_anchors[code] = m.group(2).strip().rstrip(".").strip()
    cb.scales["tipi"] = {
        "min": TIPI_VALID[0],
        "max": TIPI_VALID[1],
        "anchors": tipi_anchors,
    }

    # --- Demographic decoders: "gender<TABS>"What is your gender?", 1=Male, 2=Female, 3=Other"
    for line in lines:
        m = re.match(r'^([A-Za-z_]\w*)\t+"[^"]*"(.*)$', line)
        if not m:
            continue
        varname = m.group(1)
        decodes = _parse_decode_pairs(m.group(2))
        if decodes:
            cb.demographic_decoders[varname] = decodes

    return cb


# ---------------------------------------------------------------------------
# Data loading / cleaning
# ---------------------------------------------------------------------------


def load_riasec(data_dir: str | Path) -> pd.DataFrame:
    """Load the raw RIASEC table, one row per respondent.

    Adds a stable ``person_id`` column equal to the 0-based row index in the raw
    file (respondent order, header excluded). Drops the empty trailing column
    that the file's trailing tab produces.
    """
    data_csv, _ = _resolve_files(data_dir)
    df = pd.read_csv(data_csv, sep="\t", low_memory=False)

    # Drop the artifact column(s) created by the header's trailing tab.
    junk = [c for c in df.columns if str(c).startswith("Unnamed")]
    if junk:
        df = df.drop(columns=junk)

    df = df.reset_index(drop=True)
    df.insert(0, "person_id", np.arange(len(df), dtype=np.int64))
    return df


def _valid_mask(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Boolean masks for each cleaning rule (all indexed like ``df``)."""
    lo_r, hi_r = RIASEC_VALID
    lo_t, hi_t = TIPI_VALID
    lo_a, hi_a = AGE_VALID

    riasec_ok = pd.Series(True, index=df.index)
    for col in RIASEC_ITEMS:
        riasec_ok &= df[col].between(lo_r, hi_r)

    tipi_ok = pd.Series(True, index=df.index)
    for col in TIPI_ITEMS:
        tipi_ok &= df[col].between(lo_t, hi_t)

    age_ok = df["age"].between(lo_a, hi_a)

    country = df["country"].astype("string")
    country_ok = country.notna() & (country.str.strip() != "") & (country != "NONE")

    return {
        "riasec": riasec_ok,
        "tipi": tipi_ok,
        "age": age_ok,
        "country": country_ok,
    }


def clean_riasec(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to valid respondents.

    Keeps rows where all 48 RIASEC items are in 1-5, all 10 TIPI items are in
    1-7, age is in [14, 90], and country is present (not blank / "NONE").
    """
    masks = _valid_mask(df)
    keep = masks["riasec"] & masks["tipi"] & masks["age"] & masks["country"]
    return df.loc[keep].reset_index(drop=True)


def cleaning_breakdown(df: pd.DataFrame) -> dict[str, int]:
    """Per-rule drop counts (for reporting). Rules evaluated independently."""
    masks = _valid_mask(df)
    keep = masks["riasec"] & masks["tipi"] & masks["age"] & masks["country"]
    return {
        "total": int(len(df)),
        "dropped_riasec_out_of_range": int((~masks["riasec"]).sum()),
        "dropped_tipi_out_of_range": int((~masks["tipi"]).sum()),
        "dropped_age_out_of_range": int((~masks["age"]).sum()),
        "dropped_country_missing": int((~masks["country"]).sum()),
        "kept": int(keep.sum()),
    }


# ---------------------------------------------------------------------------
# Per-person record
# ---------------------------------------------------------------------------


def _decode(codebook: Codebook, var: str, value) -> str | None:
    """Human-readable label for a categorical demographic code, else None."""
    if pd.isna(value):
        return None
    try:
        code = int(value)
    except (TypeError, ValueError):
        return None
    return codebook.demographic_decoders.get(var, {}).get(code)


def person_record(row: pd.Series, codebook: Codebook) -> dict:
    """Build the clean per-person dict consumed by downstream twin/eval code.

    Shape:
        {
          "person_id": int,
          "demographics": {gender, education, ... (decoded), age, familysize,
                           country (raw), major (raw free text or None)},
          "interests": {code: {"text": str, "answer": int}, ...}  (48, ordered),
          "tipi":      {code: {"text": str, "answer": int}, ...}  (10, ordered),
        }
    """
    demographics: dict[str, object] = {}
    for var in CATEGORICAL_DEMOGRAPHICS:
        demographics[var] = _decode(codebook, var, row[var])

    demographics["age"] = None if pd.isna(row["age"]) else int(row["age"])
    demographics["familysize"] = (
        None if pd.isna(row["familysize"]) else int(row["familysize"])
    )
    demographics["country"] = None if pd.isna(row["country"]) else str(row["country"])
    major = row["major"]
    demographics["major"] = None if pd.isna(major) else str(major)

    interests: "OrderedDict[str, dict]" = OrderedDict()
    for code in RIASEC_ITEMS:
        interests[code] = {
            "text": codebook.riasec_items.get(code, ""),
            "answer": int(row[code]),
        }

    tipi: "OrderedDict[str, dict]" = OrderedDict()
    for code in TIPI_ITEMS:
        tipi[code] = {
            "text": codebook.tipi_items.get(code, ""),
            "answer": int(row[code]),
        }

    return {
        "person_id": int(row["person_id"]),
        "demographics": demographics,
        "interests": interests,
        "tipi": tipi,
    }


# ---------------------------------------------------------------------------
# Deterministic sampling
# ---------------------------------------------------------------------------


def sample_eval_persons(df: pd.DataFrame, n: int, seed: int) -> list[int]:
    """Deterministically sample ``n`` distinct ``person_id`` values.

    Uses ``numpy.random.default_rng(seed)`` so repeated calls with the same
    ``df``, ``n``, and ``seed`` return the same list.
    """
    ids = df["person_id"].to_numpy()
    if n > len(ids):
        raise ValueError(
            f"Requested n={n} but only {len(ids)} persons are available."
        )
    rng = np.random.default_rng(seed)
    chosen = rng.choice(ids, size=n, replace=False)
    return [int(x) for x in chosen]
