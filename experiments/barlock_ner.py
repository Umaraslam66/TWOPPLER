"""Bar-lock item 2: real NER against the D5 capitalisation heuristic.

Report 8.6 lists three known D5 limitations and defers all of them to "the NER
decision". spaCy en_core_web_sm installs offline-clean into the uv environment,
so this script measures what actually changes if D5's capitalisation rule is
replaced by real named-entity recognition:

  * the 652-row distractor bank: density, bucket, and how many rows move;
  * the dev subjects' 2,071 turns: same;
  * every entity-stripped distractor option: does the text change;
  * each of the three named limitations: is it actually fixed, with counts;
  * the cheaper alternative (curated abbreviation subset) measured alongside,
    because it fixes limitations 1 and 2 without any new dependency.

The NER variant keeps D5's NUMBER rule byte-for-byte and replaces only the
name side, so every difference reported here is attributable to the name rule.

CPU only, no network at run time (the model is a local package), no model API
calls.

Usage: uv run python experiments/barlock_ner.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler import distractors as D  # noqa: E402
from doppler.stage2_data import HONORIFIC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"
PILOT = ROOT / "results" / "stage2_pilot"

#: spaCy entity labels treated as "a name" — the proper-noun classes D5's
#: capitalisation rule is trying to approximate. Numeric classes (DATE, TIME,
#: PERCENT, MONEY, QUANTITY, ORDINAL, CARDINAL) are deliberately excluded: D5's
#: own number rule still handles those, unchanged, so this comparison isolates
#: the name side.
NAME_LABELS = frozenset({"PERSON", "NORP", "FAC", "ORG", "GPE", "LOC",
                         "PRODUCT", "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE"})

#: The 25 genuine abbreviations inside HONORIFIC's 83 entries, plus "ST".
#: This is the report-8.6 "curated abbreviation subset" fix, measured here as
#: the cheap alternative to NER. The other 58 HONORIFIC entries are ordinary
#: English words ("PRESIDENT", "JUSTICE", "KING") that never carry an
#: abbreviation dot, and treating them as abbreviations is limitation 1.
CURATED_ABBREV = frozenset({
    "ADM", "AMB", "CAPT", "CMDR", "COL", "CPL", "DET", "DR", "FR", "GEN",
    "GOV", "LIEUT", "LT", "MAJ", "MR", "MRS", "MS", "MX", "PRES", "PROF",
    "REP", "REV", "SEC", "SEN", "SGT", "ST",
})

_NLP = None


def nlp():
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm", disable=["lemmatizer"])
    return _NLP


# ---------------------------------------------------------------------------
# The NER variant of D5
# ---------------------------------------------------------------------------

def _token_offsets(text: str) -> list[tuple[int, int]]:
    """(start, stop) char offsets of each whitespace token of ``text``."""
    out, i = [], 0
    for tok in text.split():
        i = text.index(tok, i)
        out.append((i, i + len(tok)))
        i += len(tok)
    return out


def ner_analyse(text: str, doc=None):
    """(tokens, name_runs, numbers) — the NER counterpart of D._analyse.

    A whitespace token is a name token when it overlaps a spaCy entity span
    whose label is in NAME_LABELS. Consecutive name tokens form a run, which is
    what gets replaced by a single "[NAME]". Numbers use D5's rule, applied
    only to tokens no entity claimed.
    """
    raw = (text or "").split()
    tokens = [D._split_token(t) for t in raw]
    if not tokens:
        return [], [], set()
    if doc is None:
        doc = nlp()(text)
    offsets = _token_offsets(text)
    ent_ranges = [(e.start_char, e.end_char) for e in doc.ents
                  if e.label_ in NAME_LABELS]
    is_name = []
    for a, b in offsets:
        is_name.append(any(a < eb and ea < b for ea, eb in ent_ranges))
    placeholder = [D._is_placeholder(*t) for t in tokens]
    for k, ph in enumerate(placeholder):
        if ph:
            is_name[k] = False

    runs, i = [], 0
    while i < len(tokens):
        if not is_name[i]:
            i += 1
            continue
        j = i + 1
        while j < len(tokens) and is_name[j]:
            j += 1
        runs.append((i, j))
        i = j
    in_run = {k for a, b in runs for k in range(a, b)}
    numbers = {k for k, (_, core, _) in enumerate(tokens)
               if k not in in_run and not placeholder[k] and D._is_number(core)}
    return tokens, runs, numbers


def ner_density(text: str, doc=None) -> float:
    tokens, runs, numbers = ner_analyse(text, doc)
    if not tokens:
        return 0.0
    return (sum(b - a for a, b in runs) + len(numbers)) / len(tokens)


def ner_strip(text: str, doc=None) -> str:
    tokens, runs, numbers = ner_analyse(text, doc)
    if not tokens:
        return ""
    start = {a: b for a, b in runs}
    out, i = [], 0
    while i < len(tokens):
        if i in start:
            stop = start[i]
            out.append(f"{tokens[i][0]}[NAME]{tokens[stop - 1][2]}")
            i = stop
            continue
        lead, core, trail = tokens[i]
        out.append(f"{lead}[NUMBER]{trail}" if i in numbers else lead + core + trail)
        i += 1
    return " ".join(out)


# ---------------------------------------------------------------------------
# The curated-abbreviation variant of D5 (the cheap alternative)
# ---------------------------------------------------------------------------

class CuratedAbbrev:
    """Context manager swapping HONORIFIC for CURATED_ABBREV inside D5.

    D.is_abbreviation imports HONORIFIC from stage2_data at call time, so
    patching the attribute there is enough and nothing in distractors.py is
    edited. Restores on exit.
    """

    def __enter__(self):
        import doppler.stage2_data as S
        self._old = S.HONORIFIC
        S.HONORIFIC = CURATED_ABBREV
        return self

    def __exit__(self, *exc):
        import doppler.stage2_data as S
        S.HONORIFIC = self._old
        return False


# ---------------------------------------------------------------------------
# Limitation probes
# ---------------------------------------------------------------------------

SPELLED_OUT = frozenset(h for h in HONORIFIC if h not in CURATED_ABBREV)


def spelled_out_glue(text: str) -> list[dict]:
    """Occurrences of limitation 1: a spelled-out title read as an abbreviation.

    A token whose core ends in "." and whose stem is a spelled-out HONORIFIC
    word — so D5-r3 calls it an abbreviation, the sentence does not break, and
    the next capitalised token is glued into the span.
    """
    raw = (text or "").split()
    tokens = [D._split_token(t) for t in raw]
    hits = []
    for k, (_, core, trail) in enumerate(tokens):
        tail = core[-1:] + trail
        if "." not in tail:
            continue
        stem = core.replace(".", "")
        if stem.upper() not in SPELLED_OUT:
            continue
        nxt = tokens[k + 1] if k + 1 < len(tokens) else None
        glued = bool(nxt and D._is_capitalised(nxt[1]) and nxt[1] not in D.I_FORMS)
        hits.append({"token": core, "next": (nxt[1] if nxt else None),
                     "glued": glued,
                     "context": " ".join(raw[max(0, k - 4):k + 4])})
    return hits


def st_hits(text: str) -> list[dict]:
    """Occurrences of limitation 2: "St." splitting a place or saint name."""
    raw = (text or "").split()
    tokens = [D._split_token(t) for t in raw]
    hits = []
    for k, (_, core, trail) in enumerate(tokens):
        # _split_token moves a final "." into `trail`, so the dot has to be
        # looked for in both halves ("St." -> core "St", trail ".").
        if core.rstrip(".").upper() != "ST" or "." not in (core + trail):
            continue
        nxt = tokens[k + 1] if k + 1 < len(tokens) else None
        hits.append({"next": (nxt[1] if nxt else None),
                     "context": " ".join(raw[max(0, k - 3):k + 3])})
    return hits


def sentence_initial_survivors(text: str, doc) -> list[dict]:
    """Occurrences of limitation 3: a lone sentence-initial proper noun kept.

    D5 excludes a single capitalised token at a sentence start, so a real name
    opening a sentence survives entity stripping. This counts the ones spaCy
    calls a named entity — i.e. the true leaks, not "The" and "But".
    """
    tokens, spans, _ = D._analyse(text)
    if not tokens:
        return []
    in_span = {k for a, b in spans for k in range(a, b)}
    raw = (text or "").split()
    offsets = _token_offsets(text)
    ents = [(e.start_char, e.end_char, e.text, e.label_) for e in doc.ents
            if e.label_ in NAME_LABELS]

    sentence_start = [False] * len(tokens)
    sentence_start[0] = True
    for i in range(1, len(tokens)):
        _, core, trail = tokens[i - 1]
        if D._ends_sentence(core, trail):
            sentence_start[i] = True

    hits = []
    for k, (_, core, _) in enumerate(tokens):
        if k in in_span or not sentence_start[k]:
            continue
        if not D._is_capitalised(core) or core in D.I_FORMS:
            continue
        a, b = offsets[k]
        hit = next(((t, lab) for ea, eb, t, lab in ents if ea < b and a < eb), None)
        if hit is None:
            continue
        hits.append({"token": core, "ner_label": hit[1],
                     "context": " ".join(raw[k:k + 6])})
    return hits


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def compare(texts: list[str], docs) -> dict:
    """Bucket/density comparison of D5, NER and the curated variant."""
    d5_b, ner_b, cur_b = [], [], []
    d5_d, ner_d = [], []
    with CuratedAbbrev():
        for t in texts:
            cur_b.append(D.bucket_of(t))
    for t, doc in zip(texts, docs):
        d5_d.append(D.entity_density(t))
        d5_b.append(D.density_bucket(d5_d[-1]))
        ner_d.append(ner_density(t, doc))
        ner_b.append(D.density_bucket(ner_d[-1]))

    conf: dict[str, int] = {}
    for a, b in zip(d5_b, ner_b):
        conf[f"{a}->{b}"] = conf.get(f"{a}->{b}", 0) + 1
    n = len(texts)
    return {
        "n": n,
        "bucket_changed_ner": sum(a != b for a, b in zip(d5_b, ner_b)),
        "bucket_changed_curated": sum(a != b for a, b in zip(d5_b, cur_b)),
        "confusion_d5_to_ner": dict(sorted(conf.items())),
        "mean_density_d5": round(sum(d5_d) / n, 4) if n else 0.0,
        "mean_density_ner": round(sum(ner_d) / n, 4) if n else 0.0,
        "d5_bucket_counts": {b: d5_b.count(b) for b in "ZLH"},
        "ner_bucket_counts": {b: ner_b.count(b) for b in "ZLH"},
        "_d5_b": d5_b, "_ner_b": ner_b, "_cur_b": cur_b,
    }


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    pipe = nlp()

    # --- 1. the distractor bank ------------------------------------------
    bank = [json.loads(l) for l in
            (PILOT / "distractor_bank.jsonl").read_text().splitlines() if l.strip()]
    bank_texts = [r["answer"] for r in bank]
    bank_docs = list(pipe.pipe(bank_texts, batch_size=32))
    bank_cmp = compare(bank_texts, bank_docs)
    bank_examples = [
        {"source": bank[i]["source_canonical_id"],
         "d5_bucket": bank_cmp["_d5_b"][i], "ner_bucket": bank_cmp["_ner_b"][i],
         "d5_density": round(D.entity_density(bank_texts[i]), 4),
         "ner_density": round(ner_density(bank_texts[i], bank_docs[i]), 4),
         "answer_head": bank_texts[i][:220]}
        for i in range(len(bank))
        if bank_cmp["_d5_b"][i] != bank_cmp["_ner_b"][i]][:12]

    # --- 2. the dev subjects' turns ---------------------------------------
    turn_texts, turn_meta = [], []
    for sub in sorted((PILOT / "subjects").iterdir()):
        for name in ("grounding_turns.jsonl", "test_turns.jsonl"):
            p = sub / name
            if not p.exists():
                continue
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if not (r.get("text") or "").strip():
                    continue
                turn_texts.append(r["text"])
                turn_meta.append({"cid": sub.name, "file": name,
                                  "role": r["role"], "turn_idx": r["turn_idx"]})
    turn_docs = list(pipe.pipe(turn_texts, batch_size=32))
    turn_cmp = compare(turn_texts, turn_docs)

    # --- 3. entity-stripped option texts ----------------------------------
    opt_rows, changed_opts, examples = 0, 0, []
    items_with_change = set()
    for sub in sorted((PILOT / "subjects").iterdir()):
        p = sub / "distractors.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            for k, opt in enumerate(it["options"]):
                text = opt["text"]
                d5 = it["options_stripped"][k]
                nr = ner_strip(text)
                opt_rows += 1
                if nr != d5:
                    changed_opts += 1
                    items_with_change.add(it["item_id"])
                    if len(examples) < 6:
                        examples.append({"item_id": it["item_id"], "option": k,
                                         "kind": opt["kind"],
                                         "d5_stripped": d5[:260],
                                         "ner_stripped": nr[:260]})
    # bank-side stripped comparison too (larger n)
    bank_strip_changed = sum(
        1 for t, doc in zip(bank_texts, bank_docs)
        if ner_strip(t, doc) != D.strip_entities(t))

    # --- 4. the three limitations ----------------------------------------
    lim1_rows, lim1_occ, lim1_glued, lim1_ex = 0, 0, 0, []
    lim2_rows, lim2_occ, lim2_ex = 0, 0, []
    lim3_occ, lim3_rows, lim3_ex = 0, 0, []
    all_texts = bank_texts + turn_texts
    all_docs = bank_docs + turn_docs
    for t, doc in zip(all_texts, all_docs):
        g = spelled_out_glue(t)
        if g:
            lim1_rows += 1
            lim1_occ += len(g)
            lim1_glued += sum(1 for h in g if h["glued"])
            for h in g:
                if h["glued"] and len(lim1_ex) < 6:
                    lim1_ex.append(h)
        s = st_hits(t)
        if s:
            lim2_rows += 1
            lim2_occ += len(s)
            lim2_ex.extend(s[:1] if len(lim2_ex) < 6 else [])
        v = sentence_initial_survivors(t, doc)
        if v:
            lim3_rows += 1
            lim3_occ += len(v)
            for h in v:
                if len(lim3_ex) < 8:
                    lim3_ex.append(h)

    # does NER actually fix 1 and 2? check the specific glue/split sites.
    lim1_fixed = lim2_fixed = 0
    lim1_seen = lim2_seen = 0
    for t, doc in zip(all_texts, all_docs):
        for h in spelled_out_glue(t):
            if not h["glued"]:
                continue
            lim1_seen += 1
            # fixed when NER does NOT call the glued follower a name
            nr = ner_strip(t, doc)
            if h["next"] and h["next"] in nr.split():
                lim1_fixed += 1
        for h in st_hits(t):
            lim2_seen += 1
            nr = ner_strip(t, doc)
            # fixed when the follower is inside a [NAME] rather than stranded
            if h["next"] and h["next"] not in nr.split():
                lim2_fixed += 1
    # curated-subset behaviour on the same sites
    with CuratedAbbrev():
        cur_lim1_fixed = 0
        for t in all_texts:
            for h in spelled_out_glue(t):
                if not h["glued"]:
                    continue
                if h["next"] and h["next"] in D.strip_entities(t).split():
                    cur_lim1_fixed += 1
        cur_lim2_fixed = 0
        for t in all_texts:
            for h in st_hits(t):
                if h["next"] and h["next"] not in D.strip_entities(t).split():
                    cur_lim2_fixed += 1

    # --- 5. corpus-wide rate of the two abbreviation limitations ---------
    # The bank and the dev turns are a thin slice; "St." never fires in them.
    # The 98 transcripts cached for the other bar-lock items are an independent,
    # much larger sample of raw corpus text, so measure the rate there too.
    wide = {"available": False}
    cached = ROOT / "data" / "stage2_cache" / "barlock_records.json"
    if cached.exists():
        recs = json.loads(cached.read_text())
        n_utt = n_st = n_glue = 0
        for rec in recs.values():
            for u in rec["utt"]:
                n_utt += 1
                if st_hits(u):
                    n_st += 1
                if any(h["glued"] for h in spelled_out_glue(u)):
                    n_glue += 1
        wide = {"available": True, "transcripts": len(recs), "utterances": n_utt,
                "utterances_with_st_period": n_st,
                "utterances_with_spelled_out_glue": n_glue,
                "st_rate": round(n_st / n_utt, 5) if n_utt else 0.0,
                "glue_rate": round(n_glue / n_utt, 5) if n_utt else 0.0,
                "source": "data/stage2_cache/barlock_records.json (98 transcripts)"}

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_wide_limitation_rates": wide,
        "ner": {"library": "spaCy 3.8.14", "model": "en_core_web_sm 3.8.0",
                "install": "uv pip install spacy; uv run python -m spacy "
                           "download en_core_web_sm (12.2 MiB wheel)",
                "name_labels": sorted(NAME_LABELS),
                "number_rule": "unchanged from D5 (>=2 digits, or $/% amount)"},
        "bank": {k: v for k, v in bank_cmp.items() if not k.startswith("_")},
        "bank_bucket_change_examples": bank_examples,
        "turns": {k: v for k, v in turn_cmp.items() if not k.startswith("_")},
        "stripped_options": {
            "option_rows": opt_rows,
            "options_text_changed": changed_opts,
            "items_touched": len(items_with_change),
            "bank_answers_strip_changed": bank_strip_changed,
            "bank_answers": len(bank_texts),
            "examples": examples,
        },
        "limitations": {
            "1_spelled_out_titles": {
                "texts_with_occurrence": lim1_rows, "occurrences": lim1_occ,
                "occurrences_that_glue_a_word": lim1_glued,
                "ner_fixes": lim1_fixed, "ner_sites_checked": lim1_seen,
                "curated_subset_fixes": cur_lim1_fixed,
                "examples": lim1_ex},
            "2_st_period": {
                "texts_with_occurrence": lim2_rows, "occurrences": lim2_occ,
                "ner_fixes": lim2_fixed, "ner_sites_checked": lim2_seen,
                "curated_subset_fixes": cur_lim2_fixed,
                "examples": lim2_ex},
            "3_sentence_initial_proper_noun": {
                "texts_with_occurrence": lim3_rows,
                "occurrences_ner_calls_a_name": lim3_occ,
                "curated_subset_fixes": 0,
                "note": "the curated fix cannot touch this one; only NER can",
                "examples": lim3_ex},
        },
        "corpus": {"bank_rows": len(bank_texts), "dev_turns": len(turn_texts)},
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "ner_upgrade.json").write_text(json.dumps(payload, indent=1))
    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("bank_bucket_change_examples",)}, indent=1)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
