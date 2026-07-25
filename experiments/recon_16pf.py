"""CPU-only data recon of the OpenPsychometrics Cattell 16PF dataset.

Authorized by PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section D: a small
CPU-only recon (item scales, factor structure, usable respondent counts) that
precedes a separate Addendum B. This script runs NO experiment, draws NO split,
and calls NO model API. Pure pandas/numpy.

Conventions mirror src/doppler/data.py (the RIASEC loader):
  - the raw table is TAB-separated despite the .csv extension;
  - 0 encodes "missing" on the Likert items;
  - item texts, scale anchors, and demographic code -> label maps are parsed
    from the shipped codebook at runtime, never hard-coded from memory;
  - person_id is the 0-based row index in the raw file.

Two extra facts the shipped 16PF codebook does NOT carry (factor names and
reverse-keying) are recovered by exact item-text matching against the IPIP's
own 16PF scale key, saved beside the data as ipip_16pf_key.html. The match is
computed here, not asserted from memory; unmatched items are printed.

Writes results/16pf_recon_numbers.json (every number quoted in
results/16pf_recon.md comes from that file).

Run: uv run python experiments/recon_16pf.py
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

from doppler.data import (
    CATEGORICAL_DEMOGRAPHICS,
    RAW_DEMOGRAPHICS,
    cleaning_breakdown,
    load_riasec,
)

DATA_DIR = Path("data/16pf")
OUT = Path("results/16pf_recon_numbers.json")

#: The 16 letter-prefixed item groups as they appear in the raw header.
FACTOR_LETTERS = list("ABCDEFGHIJKLMNOP")

#: Valid response range on the Likert items. 0 encodes "missing".
ITEM_VALID = (1, 5)
#: Same age window the RIASEC cleaner uses, for comparability.
AGE_VALID = (14, 90)
#: Self-reported accuracy is a 0-100 percentage per the codebook.
ACCURACY_VALID = (1, 100)

report: dict = {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _html_to_lines(path: Path) -> list[str]:
    """Flatten an HTML file to non-empty text lines (block tags become breaks)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table)>", "\n", raw)
    raw = re.sub(r"(?i)</t[dh]>", "\t", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    return [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.split("\n") if ln.strip()]


# ---------------------------------------------------------------------------
# 1. Files and provenance
# ---------------------------------------------------------------------------


def section_files() -> None:
    files = {}
    for name in ("16PF.zip", "data.csv", "codebook.html", "ipip_16pf_key.html"):
        p = DATA_DIR / name
        files[name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    report["files"] = files
    print("== 1. files ==")
    for name, meta in files.items():
        print(f"  {name:22s} {meta['bytes']:>10d} bytes  sha256={meta['sha256']}")


# ---------------------------------------------------------------------------
# 2. Codebook parse (mirrors load_codebook's contract, HTML source)
# ---------------------------------------------------------------------------


def parse_codebook() -> dict:
    """Parse codebook.html: item code -> text, anchors, demographic decoders."""
    path = DATA_DIR / "codebook.html"
    raw = path.read_text(encoding="utf-8", errors="replace")

    # Item rows look like: <td>A1</td><td>INTEGER</td><td>"text" rated on ...
    item_rows = re.findall(
        r'(?is)<td[^>]*>\s*([A-P](?:1[0-3]|[1-9]))\s*</td>\s*<td[^>]*>\s*INTEGER\s*'
        r'</td>\s*<td[^>]*>\s*"(.*?)"\s*rated on',
        raw,
    )
    items: "OrderedDict[str, str]" = OrderedDict()
    for code, text in item_rows:
        items[code] = re.sub(r"\s+", " ", html.unescape(text)).strip()

    # Anchors are stated inline on every item row; take them from the first.
    anchor_src = re.search(
        r"(?is)rated on a five point scale \(([^)]*)\)\.(.*?)</td>", raw
    )
    anchors: dict[int, str] = {}
    anchor_note = ""
    if anchor_src:
        anchor_note = re.sub(r"\s+", " ", html.unescape(anchor_src.group(1))).strip()
        for m in re.finditer(
            r'(\d+)\s*was labeled as\s*"([^"]*)"', html.unescape(anchor_src.group(2))
        ):
            anchors[int(m.group(1))] = m.group(2).strip()

    # Demographic rows: <td>gender</td><td>INTEGER</td><td>description ...</td>
    demo_rows = re.findall(
        r"(?is)<td[^>]*>\s*(age|gender|accuracy|country|source|elapse[d]?)\s*</td>\s*"
        r"<td[^>]*>\s*(INTEGER|STRING)\s*</td>\s*<td[^>]*>(.*?)</td>",
        raw,
    )
    demographics: dict[str, dict] = {}
    for name, fmt, desc in demo_rows:
        flat = re.sub(r"<[^>]+>", " ", desc)
        flat = re.sub(r"\s+", " ", html.unescape(flat)).strip()
        codes = {
            int(m.group(1)): m.group(2).strip().rstrip(".").strip()
            for m in re.finditer(r"(\d+)\s*=\s*(?:from )?([^,\.]+)", flat)
        }
        demographics[name] = {
            "format": fmt,
            "description": flat[:400],
            "n_inline_codes": len(codes),
        }

    # country code -> label key, listed as CC,"Label" lines
    country_key = {
        m.group(1): m.group(2)
        for m in re.finditer(r'\b([A-Z][A-Z0-9])\s*,\s*"([^"]+)"', raw)
    }

    return {
        "items": items,
        "anchors": anchors,
        "anchor_range_note": anchor_note,
        "demographics": demographics,
        "n_country_codes": len(country_key),
    }


def section_codebook(cb: dict, data_items: list[str]) -> None:
    documented = set(cb["items"])
    present = set(data_items)
    report["codebook"] = {
        "n_items_documented": len(documented),
        "n_items_in_data": len(present),
        "in_data_not_in_codebook": sorted(present - documented),
        "in_codebook_not_in_data": sorted(documented - present),
        "anchors": {str(k): v for k, v in sorted(cb["anchors"].items())},
        "anchor_range_note": cb["anchor_range_note"],
        "demographic_fields_documented": sorted(cb["demographics"]),
        "n_country_codes": cb["n_country_codes"],
    }
    print("\n== 2. codebook ==")
    print(f"  items documented in codebook : {len(documented)}")
    print(f"  item columns in data.csv     : {len(present)}")
    print(f"  in data but NOT in codebook  : {sorted(present - documented)}")
    print(f"  in codebook but NOT in data  : {sorted(documented - present)}")
    print(f"  anchor range note            : {cb['anchor_range_note']!r}")
    for k, v in sorted(cb["anchors"].items()):
        print(f"    {k} = {v}")
    print(f"  demographic fields documented: {sorted(cb['demographics'])}")
    print(f"  country code -> label entries : {cb['n_country_codes']}")


# ---------------------------------------------------------------------------
# 3. Factor structure via exact item-text match against the IPIP key
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    """Normalize an item statement for matching across the two sources.

    The dataset codebook writes first person with an explicit subject
    ("I know how to comfort others"); the IPIP key drops it
    ("Know how to comfort others."). Everything else is identical.
    """
    t = html.unescape(text).lower().strip()
    # Quote marks differ between the two sources (the dataset codebook uses
    # 'no', the IPIP key uses "no."), so drop all of them, including the
    # possessive apostrophe, which is dropped consistently on both sides.
    t = re.sub(r"[\"'’“”]", "", t)
    t = re.sub(r"^i\s+", "", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_ipip_key() -> list[dict]:
    """Parse the IPIP 16PF key into 16 scales with +/- keyed item statements."""
    lines = _html_to_lines(DATA_DIR / "ipip_16pf_key.html")
    joined = "\n".join(lines)
    # Scale headers wrap across lines, e.g. "WARMTH (16PF\nFactor A: Warmth) [.80]"
    joined = re.sub(
        r"([A-Z][A-Z /-]{2,})\s*\((?:16PF\s*)?\n?Factor\s+([A-Z]Q?\d?|Q\d):\s*([^)]+?)\)"
        r"\s*(?:\[[^\]]*?([.\d]+)\s*\])?",
        lambda m: "\n@@SCALE@@\t{}\t{}\t{}\t{}".format(
            m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4) or ""
        ),
        joined,
    )
    scales: list[dict] = []
    cur: dict | None = None
    sign = None
    for ln in joined.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("@@SCALE@@"):
            _, label, letter, name, alpha = ln.split("\t")
            cur = {
                "ipip_label": label,
                "cattell_factor": letter,
                "cattell_name": name,
                "ipip_alpha": alpha,
                "plus": [],
                "minus": [],
            }
            scales.append(cur)
            sign = None
            continue
        if cur is None:
            continue
        if re.fullmatch(r"[+–−-]\s*keyed", ln):
            sign = "plus" if ln.startswith("+") else "minus"
            continue
        # Statements end in a period, sometimes inside a closing quote, e.g.
        # 'Feel guilty when I say "no."' and 'Want everything to be "just right."'
        if sign and re.search(r'\.["”]?$', ln):
            cur[sign].append(ln)
    return scales


def section_factors(cb: dict, data_items: list[str]) -> dict:
    scales = parse_ipip_key()
    # index normalized IPIP statement -> (scale idx, sign)
    ipip_index: dict[str, tuple[int, str]] = {}
    for i, sc in enumerate(scales):
        for sign in ("plus", "minus"):
            for stmt in sc[sign]:
                ipip_index[_norm(stmt)] = (i, sign)

    matched: dict[str, dict] = {}
    unmatched_data: list[str] = []
    for code in data_items:
        text = cb["items"].get(code)
        if text is None:
            unmatched_data.append(code)  # not documented at all
            continue
        hit = ipip_index.get(_norm(text))
        if hit is None:
            unmatched_data.append(code)
            continue
        i, sign = hit
        matched[code] = {
            "text": text,
            "scale_idx": i,
            "keyed": "+" if sign == "plus" else "-",
        }

    used = {(m["scale_idx"], _norm(m["text"])) for m in matched.values()}
    leftover_ipip = [
        {
            "scale_idx": i,
            "ipip_label": sc["ipip_label"],
            "keyed": "+" if sign == "plus" else "-",
            "statement": stmt,
        }
        for i, sc in enumerate(scales)
        for sign in ("plus", "minus")
        for stmt in sc[sign]
        if (i, _norm(stmt)) not in used
    ]

    # If exactly one data item and exactly one IPIP statement are left over,
    # they pin each other by elimination. Recorded as INFERRED, not documented.
    inferred: dict[str, dict] = {}
    if len(unmatched_data) == 1 and len(leftover_ipip) == 1:
        code = unmatched_data[0]
        left = leftover_ipip[0]
        inferred[code] = {
            "text": left["statement"].rstrip("."),
            "scale_idx": left["scale_idx"],
            "keyed": left["keyed"],
            "how": "elimination: the only undocumented data item and the only "
                   "unmatched IPIP statement, and both sit in the same scale",
        }
        matched[code] = {k: inferred[code][k]
                         for k in ("text", "scale_idx", "keyed")}

    # Letter-group -> IPIP scale agreement: does each raw letter map to exactly
    # one IPIP scale?
    letter_to_scales: dict[str, set[int]] = {ltr: set() for ltr in FACTOR_LETTERS}
    for code, m in matched.items():
        letter_to_scales[code[0]].add(m["scale_idx"])
    one_to_one = all(len(v) == 1 for v in letter_to_scales.values())

    letter_map = {}
    for ltr in FACTOR_LETTERS:
        idxs = sorted(letter_to_scales[ltr])
        sc = scales[idxs[0]] if len(idxs) == 1 else None
        codes = [c for c in data_items if c[0] == ltr]
        rev = sorted(c for c in codes if matched.get(c, {}).get("keyed") == "-")
        letter_map[ltr] = {
            "n_items": len(codes),
            "items": codes,
            "ipip_label": sc["ipip_label"] if sc else None,
            "cattell_factor": sc["cattell_factor"] if sc else None,
            "cattell_name": sc["cattell_name"] if sc else None,
            "ipip_alpha": sc["ipip_alpha"] if sc else None,
            "reverse_keyed": rev,
            "n_reverse_keyed": len(rev),
            "n_unmatched": len([c for c in codes if c not in matched]),
        }

    report["factors"] = {
        "n_scales_in_ipip_key": len(scales),
        "n_items_matched_exactly": len(matched) - len(inferred),
        "unmatched_data_items": unmatched_data,
        "leftover_ipip_statements": leftover_ipip,
        "inferred_by_elimination": inferred,
        "letter_to_ipip_scale_is_one_to_one": bool(one_to_one),
        "letters": letter_map,
    }

    print("\n== 3. factor structure (via exact item-text match to IPIP key) ==")
    print(f"  scales in IPIP key            : {len(scales)}")
    print(f"  data items matched exactly    : {len(matched) - len(inferred)} "
          f"/ {len(data_items)}")
    print(f"  data items NOT text-matched   : {unmatched_data}")
    print(f"  IPIP statements left unmatched: "
          f"{[(x['ipip_label'], x['keyed'], x['statement']) for x in leftover_ipip]}")
    for code, inf in inferred.items():
        print(f"  INFERRED {code}: {inf['text']!r} keyed {inf['keyed']} "
              f"({inf['how']})")
    print(f"  each raw letter -> one scale  : {one_to_one}")
    print(f"  {'ltr':4s}{'n':>4s}{'rev':>5s}  {'Cattell':10s} {'IPIP label':18s} alpha")
    for ltr, m in letter_map.items():
        print(f"  {ltr:4s}{m['n_items']:>4d}{m['n_reverse_keyed']:>5d}  "
              f"{str(m['cattell_factor']) + ' ' + str(m['cattell_name']):22s}"
              f"{str(m['ipip_label']):18s} {m['ipip_alpha']}")
    return letter_map


# ---------------------------------------------------------------------------
# 4. Observed response values
# ---------------------------------------------------------------------------


def section_values(df: pd.DataFrame, items: list[str]) -> None:
    m = df[items].to_numpy()
    vals, counts = np.unique(m, return_counts=True)
    report["observed_item_values"] = {
        "distinct_values": [int(v) for v in vals],
        "counts": {int(v): int(c) for v, c in zip(vals, counts)},
        "n_cells": int(m.size),
        "n_zero_cells": int((m == 0).sum()),
        "pct_zero_cells": round(100 * float((m == 0).mean()), 4),
    }
    print("\n== 4. observed item values ==")
    print(f"  distinct values across all {m.size} item cells: {[int(v) for v in vals]}")
    for v, c in zip(vals, counts):
        print(f"    {int(v)}: {int(c):>10d}  ({100 * c / m.size:.3f}%)")


# ---------------------------------------------------------------------------
# 5. Cleaning funnel (mirrors clean_riasec / cleaning_breakdown)
# ---------------------------------------------------------------------------


def build_masks(df: pd.DataFrame, items: list[str]) -> "OrderedDict[str, pd.Series]":
    lo, hi = ITEM_VALID
    lo_a, hi_a = AGE_VALID
    lo_c, hi_c = ACCURACY_VALID

    m = df[items]
    n_missing = (m == 0).sum(axis=1)
    items_ok = pd.Series(True, index=df.index)
    for col in items:
        items_ok &= df[col].between(lo, hi)

    age_ok = df["age"].between(lo_a, hi_a)
    gender_ok = df["gender"].between(1, 3)
    country = df["country"].astype("string")
    country_ok = (
        country.notna()
        & (country.str.strip() != "")
        & (country != "NONE")
        & (~country.isin(["A1", "A2", "O1"]))  # proxy / satellite / unknown
    )
    accuracy_ok = df["accuracy"].between(lo_c, hi_c)

    answered = m.where(m != 0)
    variance_ok = answered.std(axis=1, ddof=0).fillna(0) > 0
    dup_ok = ~df.duplicated(subset=items, keep="first")
    # Slower than one second per item, and under a day.
    elapsed_ok = df["elapsed"].between(len(items), 86_400)

    return OrderedDict(
        items_in_range=items_ok,
        age_in_range=age_ok,
        gender_present=gender_ok,
        country_present=country_ok,
        accuracy_in_range=accuracy_ok,
        not_straightlining=variance_ok,
        not_duplicate_answer_vector=dup_ok,
        elapsed_plausible=elapsed_ok,
    )


def section_cleaning(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    masks = build_masks(df, items)
    total = len(df)

    independent = {k: int((~v).sum()) for k, v in masks.items()}

    funnel = []
    keep = pd.Series(True, index=df.index)
    for name, mask in masks.items():
        before = int(keep.sum())
        keep = keep & mask
        after = int(keep.sum())
        funnel.append(
            {"step": name, "rows_in": before, "rows_lost": before - after,
             "rows_out": after}
        )

    # Also: how many rows would survive a looser rule that tolerates some
    # missing items (the RIASEC rule is all-or-nothing).
    n_missing = (df[items] == 0).sum(axis=1)
    base = pd.Series(True, index=df.index)
    for name, mask in masks.items():
        if name != "items_in_range":
            base &= mask
    tolerance = {
        str(t): int((base & (n_missing <= t)).sum()) for t in (0, 1, 2, 5, 10, 163)
    }

    report["cleaning"] = {
        "total_rows": total,
        "independent_drop_counts": independent,
        "sequential_funnel": funnel,
        "kept": funnel[-1]["rows_out"],
        "kept_pct": round(100 * funnel[-1]["rows_out"] / total, 2),
        "rows_with_any_missing_item": int((n_missing > 0).sum()),
        "missing_items_per_row_quantiles": {
            q: float(n_missing.quantile(q)) for q in (0.5, 0.75, 0.9, 0.95, 0.99)
        },
        "kept_under_missing_tolerance": tolerance,
        "rules": {
            "items_in_range": f"all {len(items)} items in {ITEM_VALID} (0 = missing)",
            "age_in_range": f"age in {AGE_VALID} (same window as clean_riasec)",
            "gender_present": "gender in 1-3 (0 = missed)",
            "country_present": "country non-blank, not NONE, not A1/A2/O1",
            "accuracy_in_range": f"self-reported accuracy in {ACCURACY_VALID}",
            "not_straightlining": "non-zero SD across answered items",
            "not_duplicate_answer_vector": "first occurrence of a 163-item vector",
            "elapsed_plausible": f"elapsed in [{len(items)}, 86400] seconds",
        },
    }

    print("\n== 5. cleaning funnel ==")
    print(f"  total rows: {total}")
    print(f"  {'step':32s}{'in':>8s}{'lost':>8s}{'out':>8s}")
    for row in funnel:
        print(f"  {row['step']:32s}{row['rows_in']:>8d}{row['rows_lost']:>8d}"
              f"{row['rows_out']:>8d}")
    print("  independent (each rule alone, drops):")
    for k, v in independent.items():
        print(f"    {k:32s}{v:>8d}")
    print(f"  rows with >=1 missing item: {int((n_missing > 0).sum())}")
    print("  kept if we tolerate up to N missing items (other rules applied):")
    for t, n in tolerance.items():
        print(f"    <= {t:>3s} missing: {n:>7d}")
    return masks


# ---------------------------------------------------------------------------
# 6. Demographics, and the RIASEC comparison
# ---------------------------------------------------------------------------


def section_demographics(df: pd.DataFrame, keep: pd.Series) -> None:
    clean = df.loc[keep]
    dem = {}
    for col in ("age", "gender", "country", "source", "accuracy", "elapsed"):
        s = clean[col]
        entry = {"n_nonnull": int(s.notna().sum())}
        if col == "country":
            entry["n_distinct"] = int(s.nunique())
            entry["top5"] = {k: int(v) for k, v in s.value_counts().head(5).items()}
        elif col == "gender":
            entry["value_counts"] = {int(k): int(v)
                                     for k, v in s.value_counts().sort_index().items()}
        else:
            entry.update({
                "min": float(s.min()), "median": float(s.median()),
                "mean": round(float(s.mean()), 2), "max": float(s.max()),
            })
        dem[col] = entry

    riasec = load_riasec("data/riasec")
    riasec_bd = cleaning_breakdown(riasec)
    riasec_dem = sorted(CATEGORICAL_DEMOGRAPHICS + RAW_DEMOGRAPHICS)
    pf_dem = ["age", "gender", "country"]
    pf_meta = ["source", "accuracy", "elapsed"]

    report["demographics"] = {
        "16pf_fields": pf_dem,
        "16pf_meta_fields": pf_meta,
        "16pf_clean_summary": dem,
        "riasec_fields": riasec_dem,
        "riasec_n_fields": len(riasec_dem),
        "shared_fields": sorted(set(pf_dem) & set(riasec_dem)),
        "riasec_only_fields": sorted(set(riasec_dem) - set(pf_dem)),
        "riasec_cleaning_breakdown": riasec_bd,
    }
    print("\n== 6. demographics ==")
    print(f"  16PF demographic fields : {pf_dem}")
    print(f"  16PF technical fields   : {pf_meta}")
    print(f"  RIASEC demographic flds ({len(riasec_dem)}): {riasec_dem}")
    print(f"  shared with RIASEC      : {sorted(set(pf_dem) & set(riasec_dem))}")
    print(f"  RIASEC-only             : {sorted(set(riasec_dem) - set(pf_dem))}")
    print(f"  RIASEC cleaning breakdown: {riasec_bd}")
    for col, entry in dem.items():
        print(f"  {col}: {entry}")


# ---------------------------------------------------------------------------
# 7 + 8. Redundancy inside factors, and correlations between factors
# ---------------------------------------------------------------------------


def section_structure(df: pd.DataFrame, keep: pd.Series, letter_map: dict) -> None:
    clean = df.loc[keep]
    letters = FACTOR_LETTERS

    # Sign-correct every item so higher = more of the factor, using the keying
    # recovered in section 3.
    signed = {}
    for ltr in letters:
        for code in letter_map[ltr]["items"]:
            v = clean[code].astype(float).to_numpy()
            if code in letter_map[ltr]["reverse_keyed"]:
                v = (ITEM_VALID[0] + ITEM_VALID[1]) - v
            signed[code] = v
    S = pd.DataFrame(signed, index=clean.index)

    # Empirical keying check: correlate each RAW item against the sign-corrected
    # mean of the OTHER items in its factor. A correctly keyed item correlates
    # positively when it is + keyed and negatively when it is - keyed. This
    # validates the IPIP-derived keying from the data alone, and independently
    # settles the one item inferred by elimination.
    keying_check = []
    disagreements = []
    for ltr in letters:
        cols = letter_map[ltr]["items"]
        rev = set(letter_map[ltr]["reverse_keyed"])
        for code in cols:
            others = [c for c in cols if c != code]
            rest = S[others].mean(axis=1)
            r = float(np.corrcoef(clean[code].astype(float).to_numpy(), rest)[0, 1])
            expected = "-" if code in rev else "+"
            observed = "+" if r > 0 else "-"
            row = {"item": code, "factor": ltr, "keyed_per_source": expected,
                   "r_raw_vs_rest": round(r, 4), "sign_observed": observed,
                   "agrees": expected == observed}
            keying_check.append(row)
            if not row["agrees"]:
                disagreements.append(row)
    report["keying_check"] = {
        "n_items_checked": len(keying_check),
        "n_agree": sum(1 for r in keying_check if r["agrees"]),
        "n_disagree": len(disagreements),
        "disagreements": disagreements,
        "min_abs_r": round(min(abs(r["r_raw_vs_rest"]) for r in keying_check), 4),
        "weakest_five": sorted(keying_check,
                               key=lambda d: abs(d["r_raw_vs_rest"]))[:5],
        "per_item": keying_check,
    }
    print("\n== 7a. empirical keying check (raw item vs sign-corrected rest) ==")
    print(f"  items checked: {len(keying_check)}; sign agrees with the IPIP key "
          f"for {report['keying_check']['n_agree']}; disagrees for "
          f"{len(disagreements)}")
    print(f"  weakest |r| items: "
          f"{[(d['item'], d['r_raw_vs_rest']) for d in report['keying_check']['weakest_five']]}")
    if disagreements:
        print(f"  DISAGREEMENTS: {disagreements}")

    within = {}
    for ltr in letters:
        cols = letter_map[ltr]["items"]
        C = S[cols].corr().to_numpy()
        iu = np.triu_indices(len(cols), k=1)
        r = C[iu]
        # Split-half (odd vs even items), Spearman-Brown corrected.
        odd = S[cols[0::2]].mean(axis=1)
        even = S[cols[1::2]].mean(axis=1)
        rhalf = float(np.corrcoef(odd, even)[0, 1])
        sb = 2 * rhalf / (1 + rhalf)
        # Cronbach alpha on the sign-corrected items.
        k = len(cols)
        item_var = S[cols].var(ddof=1).sum()
        tot_var = S[cols].sum(axis=1).var(ddof=1)
        alpha = (k / (k - 1)) * (1 - item_var / tot_var)
        within[ltr] = {
            "n_items": k,
            "mean_abs_r": round(float(np.abs(r).mean()), 4),
            "max_abs_r": round(float(np.abs(r).max()), 4),
            "max_pair": [cols[int(iu[0][int(np.abs(r).argmax())])],
                         cols[int(iu[1][int(np.abs(r).argmax())])]],
            "n_pairs_r_ge_0.60": int((np.abs(r) >= 0.60).sum()),
            "n_pairs_r_ge_0.70": int((np.abs(r) >= 0.70).sum()),
            "split_half_spearman_brown": round(float(sb), 4),
            "cronbach_alpha": round(float(alpha), 4),
        }

    scores = pd.DataFrame({ltr: S[letter_map[ltr]["items"]].mean(axis=1)
                           for ltr in letters})
    fc = scores.corr()
    iu = np.triu_indices(len(letters), k=1)
    off = fc.to_numpy()[iu]
    pairs = sorted(
        (
            {"a": letters[i], "b": letters[j], "r": round(float(fc.iat[i, j]), 4),
             "a_name": letter_map[letters[i]]["cattell_name"],
             "b_name": letter_map[letters[j]]["cattell_name"]}
            for i, j in zip(*iu)
        ),
        key=lambda d: -abs(d["r"]),
    )

    report["structure"] = {
        "within_factor": within,
        "within_factor_mean_abs_r_overall": round(float(
            np.mean([v["mean_abs_r"] for v in within.values()])), 4),
        "between_factor_mean_abs_r": round(float(np.abs(off).mean()), 4),
        "between_factor_max_abs_r": round(float(np.abs(off).max()), 4),
        "n_factor_pairs_abs_r_ge_0.50": int((np.abs(off) >= 0.50).sum()),
        "n_factor_pairs_abs_r_ge_0.40": int((np.abs(off) >= 0.40).sum()),
        "n_factor_pairs": int(len(off)),
        "top_factor_pairs": pairs[:12],
        "factor_correlation_matrix": {
            a: {b: round(float(fc.at[a, b]), 4) for b in letters} for a in letters
        },
    }
    print("\n== 7. within-factor redundancy (sign-corrected, cleaned rows) ==")
    print(f"  {'ltr':4s}{'n':>3s}{'meanR':>8s}{'maxR':>8s}{'>=.6':>6s}{'>=.7':>6s}"
          f"{'splithalf':>11s}{'alpha':>8s}  worst pair")
    for ltr, v in within.items():
        print(f"  {ltr:4s}{v['n_items']:>3d}{v['mean_abs_r']:>8.3f}"
              f"{v['max_abs_r']:>8.3f}{v['n_pairs_r_ge_0.60']:>6d}"
              f"{v['n_pairs_r_ge_0.70']:>6d}"
              f"{v['split_half_spearman_brown']:>11.3f}{v['cronbach_alpha']:>8.3f}"
              f"  {v['max_pair']}")
    # Item-level near-duplicate scan across the WHOLE 163-item pool. Matters
    # because a seed item that is near-identical to a target item leaks the
    # target regardless of which factor each sits in.
    all_items = [c for ltr in letters for c in letter_map[ltr]["items"]]
    C = S[all_items].corr()
    A = np.array(C.to_numpy(), dtype=float, copy=True)
    np.fill_diagonal(A, 0.0)
    iu = np.triu_indices(len(all_items), k=1)
    r_all = A[iu]
    same_factor = np.array(
        [all_items[i][0] == all_items[j][0] for i, j in zip(*iu)]
    )
    ranked = sorted(
        (
            {"a": all_items[i], "b": all_items[j], "r": round(float(A[i, j]), 4),
             "same_factor": all_items[i][0] == all_items[j][0]}
            for i, j in zip(*iu)
        ),
        key=lambda d: -abs(d["r"]),
    )
    # For the "hold out one factor" family: worst leak between a held-out item
    # and any seed item, per candidate target factor.
    per_target = {}
    for ltr in letters:
        tgt = letter_map[ltr]["items"]
        seed = [c for c in all_items if c[0] != ltr]
        sub = C.loc[tgt, seed].abs()
        worst = sub.to_numpy().max()
        wi, wj = np.unravel_index(sub.to_numpy().argmax(), sub.shape)
        per_target[ltr] = {
            "cattell_name": letter_map[ltr]["cattell_name"],
            "n_target_items": len(tgt),
            "n_seed_items": len(seed),
            "max_abs_r_target_vs_seed": round(float(worst), 4),
            "worst_pair": [tgt[int(wi)], seed[int(wj)]],
            "n_target_items_with_seed_r_ge_0.50": int((sub.max(axis=1) >= 0.50).sum()),
            "n_target_items_with_seed_r_ge_0.40": int((sub.max(axis=1) >= 0.40).sum()),
            "mean_max_abs_r_per_target_item": round(float(sub.max(axis=1).mean()), 4),
        }
    report["item_leakage"] = {
        "n_item_pairs": int(len(r_all)),
        "n_pairs_abs_r_ge_0.70": int((np.abs(r_all) >= 0.70).sum()),
        "n_pairs_abs_r_ge_0.60": int((np.abs(r_all) >= 0.60).sum()),
        "n_pairs_abs_r_ge_0.50": int((np.abs(r_all) >= 0.50).sum()),
        "n_cross_factor_pairs_abs_r_ge_0.50": int(
            (np.abs(r_all) >= 0.50)[~same_factor].sum()),
        "n_cross_factor_pairs_abs_r_ge_0.60": int(
            (np.abs(r_all) >= 0.60)[~same_factor].sum()),
        "top_20_pairs": ranked[:20],
        "per_candidate_target_factor": per_target,
    }
    print("\n== 8b. item-level near-duplicate scan (all 163 items) ==")
    il = report["item_leakage"]
    print(f"  item pairs: {il['n_item_pairs']}; |r|>=.50: "
          f"{il['n_pairs_abs_r_ge_0.50']}; |r|>=.60: {il['n_pairs_abs_r_ge_0.60']}; "
          f"|r|>=.70: {il['n_pairs_abs_r_ge_0.70']}")
    print(f"  of those, CROSS-factor: |r|>=.50: "
          f"{il['n_cross_factor_pairs_abs_r_ge_0.50']}; |r|>=.60: "
          f"{il['n_cross_factor_pairs_abs_r_ge_0.60']}")
    print("  top 10 item pairs:")
    for p in ranked[:10]:
        print(f"    {p['a']} ~ {p['b']}  r={p['r']:+.3f}  "
              f"{'same factor' if p['same_factor'] else 'CROSS factor'}")
    print("  if one factor is the target, worst target-vs-seed item leak:")
    print(f"    {'ltr':4s}{'name':22s}{'maxR':>7s}{'>=.5':>6s}{'>=.4':>6s}  worst pair")
    for ltr, v in sorted(per_target.items(),
                         key=lambda kv: kv[1]["max_abs_r_target_vs_seed"]):
        print(f"    {ltr:4s}{str(v['cattell_name']):22s}"
              f"{v['max_abs_r_target_vs_seed']:>7.3f}"
              f"{v['n_target_items_with_seed_r_ge_0.50']:>6d}"
              f"{v['n_target_items_with_seed_r_ge_0.40']:>6d}  {v['worst_pair']}")

    # Benchmark: Stage 1E's RIASEC design seeds on interest items and predicts
    # TIPI items. Item-level |r| across that boundary is what "genuinely
    # cross-domain" looks like in the design already registered. Absolute
    # values, so no keying is needed on either side.
    from doppler.data import RIASEC_ITEMS, TIPI_ITEMS, clean_riasec

    rd = clean_riasec(load_riasec("data/riasec"))
    RC = rd[RIASEC_ITEMS + TIPI_ITEMS].corr().loc[RIASEC_ITEMS, TIPI_ITEMS].abs()
    rmax = RC.to_numpy().max()
    ri, rj = np.unravel_index(RC.to_numpy().argmax(), RC.shape)
    report["riasec_cross_domain_benchmark"] = {
        "n_persons_clean": int(len(rd)),
        "n_seed_items": len(RIASEC_ITEMS),
        "n_target_items": len(TIPI_ITEMS),
        "max_abs_r_seed_vs_target": round(float(rmax), 4),
        "worst_pair": [RIASEC_ITEMS[int(ri)], TIPI_ITEMS[int(rj)]],
        "mean_abs_r": round(float(RC.to_numpy().mean()), 4),
        "mean_max_abs_r_per_target_item": round(float(RC.max(axis=0).mean()), 4),
        "n_target_items_with_seed_r_ge_0.40": int((RC.max(axis=0) >= 0.40).sum()),
        "n_target_items_with_seed_r_ge_0.30": int((RC.max(axis=0) >= 0.30).sum()),
    }
    b = report["riasec_cross_domain_benchmark"]
    print("\n== 8c. RIASEC interests -> TIPI benchmark (the registered design) ==")
    print(f"  cleaned persons: {b['n_persons_clean']}; "
          f"{b['n_seed_items']} seed items -> {b['n_target_items']} target items")
    print(f"  max |r| across the domain boundary: {b['max_abs_r_seed_vs_target']:.3f} "
          f"({b['worst_pair']}); mean |r| {b['mean_abs_r']:.3f}")
    print(f"  mean of per-target-item max |r|   : "
          f"{b['mean_max_abs_r_per_target_item']:.3f}")
    print(f"  target items with any seed item |r| >= .40: "
          f"{b['n_target_items_with_seed_r_ge_0.40']} of {b['n_target_items']}")

    print("\n== 8. between-factor correlations ==")
    print(f"  mean |r| within factors : "
          f"{report['structure']['within_factor_mean_abs_r_overall']:.3f}")
    print(f"  mean |r| between factors: "
          f"{report['structure']['between_factor_mean_abs_r']:.3f}")
    print(f"  factor pairs |r| >= .50 : "
          f"{report['structure']['n_factor_pairs_abs_r_ge_0.50']} of {len(off)}")
    for p in pairs[:12]:
        print(f"    {p['a']}({p['a_name']}) ~ {p['b']}({p['b_name']}): r={p['r']:+.3f}")


# ---------------------------------------------------------------------------
# 9. Seed-pool / target-domain option counts (neutral; no choice made)
# ---------------------------------------------------------------------------


def section_options(df: pd.DataFrame, keep: pd.Series, letter_map: dict) -> None:
    n_clean = int(keep.sum())
    n_items = sum(letter_map[l]["n_items"] for l in FACTOR_LETTERS)

    opts = []
    # A: hold out one factor, seed on the other 15.
    sizes = sorted({letter_map[l]["n_items"] for l in FACTOR_LETTERS})
    opts.append({
        "id": "A_one_factor_held_out",
        "seed_items": [n_items - s for s in sizes],
        "target_items": sizes,
        "n_variants": len(FACTOR_LETTERS),
        "persons_available": n_clean,
    })
    # B: hold out five factors (~1 per Big-Five-ish cluster), seed on 11.
    held5 = 5 * 10
    opts.append({
        "id": "B_five_factors_held_out",
        "seed_items": n_items - held5,
        "target_items": held5,
        "n_variants": None,
        "persons_available": n_clean,
    })
    # C: half the factors held out.
    opts.append({
        "id": "C_eight_factors_held_out",
        "seed_items": n_items - 80,
        "target_items": 80,
        "n_variants": None,
        "persons_available": n_clean,
    })
    # D: within-factor split (disallowed as an outcome by the registration).
    opts.append({
        "id": "D_within_factor_split_DISALLOWED",
        "seed_items": "5 of a factor's 10",
        "target_items": "the other 5",
        "n_variants": len(FACTOR_LETTERS),
        "persons_available": n_clean,
        "note": "within-scale prediction is disallowed as an outcome "
                "(PREREGISTRATION.md section 3)",
    })
    # E: cross-dataset (16PF seed -> a different OpenPsychometrics instrument).
    opts.append({
        "id": "E_cross_dataset",
        "seed_items": n_items,
        "target_items": "n/a — target lives in a different file",
        "n_variants": None,
        "persons_available": 0,
        "note": "16PF has no respondent id linkable to any other "
                "OpenPsychometrics file; no shared persons exist",
    })

    # Budget feasibility: how many persons remain per k if we want a 20-reveal
    # budget from a seed pool — purely an item-count check, no split drawn.
    report["options"] = {
        "n_items_total": n_items,
        "n_persons_clean": n_clean,
        "options": opts,
        "second_domain_present_in_file": False,
        "non_personality_columns": ["age", "gender", "country", "source",
                                    "accuracy", "elapsed"],
    }
    print("\n== 9. seed / target options (neutral, no choice made) ==")
    for o in opts:
        print(f"  {o['id']}: seed={o['seed_items']} target={o['target_items']} "
              f"variants={o['n_variants']} persons={o['persons_available']}"
              + (f"  [{o['note']}]" if o.get("note") else ""))


# ---------------------------------------------------------------------------
# 10. Timing fields
# ---------------------------------------------------------------------------


def section_timing(df: pd.DataFrame, keep: pd.Series, items: list[str]) -> None:
    clean = df.loc[keep]
    e = clean["elapsed"]
    report["timing"] = {
        "n_time_fields_16pf": 1,
        "time_fields_16pf": ["elapsed"],
        "per_item_times_available": False,
        "riasec_time_fields": ["introelapse", "testelapse", "surveyelapse"],
        "elapsed_seconds_clean": {
            "min": float(e.min()), "p25": float(e.quantile(0.25)),
            "median": float(e.median()), "p75": float(e.quantile(0.75)),
            "p99": float(e.quantile(0.99)), "max": float(e.max()),
        },
        "median_seconds_per_item": round(float(e.median()) / len(items), 2),
        "raw_elapsed_outliers": {
            "lt_163s": int((df["elapsed"] < len(items)).sum()),
            "gt_1day": int((df["elapsed"] > 86_400).sum()),
            "max_raw": int(df["elapsed"].max()),
        },
    }
    print("\n== 10. timing ==")
    print(f"  16PF time fields: ['elapsed'] (whole test); per-item times: none")
    print(f"  cleaned elapsed seconds: median {e.median():.0f}, "
          f"p25 {e.quantile(0.25):.0f}, p75 {e.quantile(0.75):.0f}, "
          f"p99 {e.quantile(0.99):.0f}, max {e.max():.0f}")
    print(f"  median seconds per item: "
          f"{report['timing']['median_seconds_per_item']}")


# ---------------------------------------------------------------------------


def main() -> None:
    section_files()

    df = pd.read_csv(DATA_DIR / "data.csv", sep="\t", low_memory=False)
    junk = [c for c in df.columns if str(c).startswith("Unnamed")]
    if junk:
        df = df.drop(columns=junk)
    df = df.reset_index(drop=True)
    df.insert(0, "person_id", np.arange(len(df), dtype=np.int64))

    items = [c for c in df.columns
             if c[0] in FACTOR_LETTERS and c[1:].isdigit()]
    report["raw_table"] = {
        "n_rows": int(len(df)),
        "n_columns_incl_person_id": int(df.shape[1]),
        "n_columns_in_file": int(df.shape[1] - 1),
        "n_item_columns": len(items),
        "dropped_unnamed_columns": junk,
        "non_item_columns": [c for c in df.columns
                             if c not in items and c != "person_id"],
        "delimiter": "tab",
    }
    print(f"\n  raw table: {len(df)} rows x {df.shape[1] - 1} file columns; "
          f"{len(items)} item columns; "
          f"non-item: {report['raw_table']['non_item_columns']}")

    cb = parse_codebook()
    section_codebook(cb, items)
    letter_map = section_factors(cb, items)
    section_values(df, items)
    masks = section_cleaning(df, items)
    keep = pd.Series(True, index=df.index)
    for m in masks.values():
        keep &= m
    section_demographics(df, keep)
    section_structure(df, keep, letter_map)
    section_options(df, keep, letter_map)
    section_timing(df, keep, items)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, default=str))
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
