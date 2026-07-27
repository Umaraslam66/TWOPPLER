"""Fresh parameter-5 tranche for the judge trust bar (owner-directed 2026-07-28).

Builds a NEW blind 18-row sheet drawn ONLY from judged generations NOT used
in the 51-row A/B/C spot-check sample, balanced per the same recipe
(SAME/DIFFERENT primary balance, shortfall filled with UNCLEAR and said so;
spread across arms, both scored models, all subjects), WITH the frozen
rubric text printed at the top — the owner labels rubric-in-hand.

The pre-committed bar (set BEFORE this tranche is scored, no bar-shopping):
raw agreement >= 0.80 AND Cohen's kappa >= 0.60 between the judge and the
rubric-briefed auditor line on this tranche.

Twin rule (D6-v4.9): within any single sheet a question appears at most
once, so 18 rows split into sub-sheets D and E of 9; no item contributes
more than 2 rows overall. Deterministic from SEED; rerun reproduces the
sheets byte-identically.
"""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "results" / "stage2_openended"
SEED = 611  # distinct from 47 (dev draw), 49, 61 (H6), 79 (fuzzy), 610 (A/B/C)
N_ROWS = 18
TARGET = {"SAME": 9, "DIFFERENT": 9}
MODEL_OF_DIR = {"flashlite": "gemini-3.5-flash-lite", "gemma": "Gemma-4-31B-it"}
ARM_NAMES = ["twin_redacted", "twin_named", "zeroinfo_redacted",
             "zeroinfo_named", "imposter_redacted"]

BAR_TEXT = ("Pre-committed 2026-07-28, before this tranche was scored: the judge "
            "passes parameter 5 iff raw agreement >= 0.80 AND Cohen's kappa >= 0.60 "
            "against the rubric-briefed auditor line on this tranche.")


def load_jsonl(path):
    return [json.loads(line) for line in open(path)]


def main():
    used = {(e["item_id"], e["arm"], e["model"])
            for e in json.load(open(BASE / "judge_spotcheck_key.json"))["entries"]}
    items = {r["item_id"]: r for r in load_jsonl(BASE / "items_oe1.jsonl")}
    gen_text = {}
    for d in ("flashlite", "gemma"):
        for arm in ARM_NAMES:
            for r in load_jsonl(BASE / "gen" / d / f"completions_{arm}.jsonl"):
                gen_text[(r["item_id"], r["arm"], MODEL_OF_DIR[d])] = r["text"]

    pool = []
    for fname in ("judgements_v2.jsonl", "judgements_gemma.jsonl"):
        for r in load_jsonl(BASE / "judge" / fname):
            model = MODEL_OF_DIR[r["scored_model_dir"]]
            trip = (r["item_id"], r["arm"], model)
            if trip in used:
                continue
            pool.append({"item_id": r["item_id"], "arm": r["arm"], "model": model,
                         "canonical_id": r["canonical_id"], "label": r["label"],
                         "why": r["why"], "text": gen_text[trip]})
    assert len(pool) == 170 - len(used), (len(pool), len(used))

    rng = random.Random(SEED)
    by_label = {}
    for row in pool:
        by_label.setdefault(row["label"], []).append(row)
    for rows in by_label.values():
        rows.sort(key=lambda r: (r["item_id"], r["arm"], r["model"]))
        rng.shuffle(rows)

    picked, arm_ct, model_ct, subj_ct, item_ct = [], Counter(), Counter(), Counter(), Counter()

    def cost(r):
        return (item_ct[r["item_id"]] >= 2, arm_ct[r["arm"]], model_ct[r["model"]],
                subj_ct[r["canonical_id"]])

    shortfall = {}
    # scarcest label first, so plentiful labels don't eat its item slots
    for label, want in sorted(TARGET.items(),
                              key=lambda kv: len(by_label.get(kv[0], []))):
        got = 0
        cands = list(by_label.get(label, []))
        while got < want and cands:
            cands.sort(key=cost)
            r = cands.pop(0)
            if item_ct[r["item_id"]] >= 2:
                break  # only capped candidates remain
            picked.append(r); got += 1
            arm_ct[r["arm"]] += 1; model_ct[r["model"]] += 1
            subj_ct[r["canonical_id"]] += 1; item_ct[r["item_id"]] += 1
        if got < want:
            shortfall[label] = want - got
    fill = list(by_label.get("UNCLEAR", []))
    while len(picked) < N_ROWS and fill:
        fill.sort(key=cost)
        r = fill.pop(0)
        if item_ct[r["item_id"]] >= 2:
            continue
        picked.append(r)
        arm_ct[r["arm"]] += 1; model_ct[r["model"]] += 1
        subj_ct[r["canonical_id"]] += 1; item_ct[r["item_id"]] += 1
    assert len(picked) == N_ROWS

    # Bipartition: no question twice within a sub-sheet.
    sheets = {"D": [], "E": []}
    for r in sorted(picked, key=lambda r: item_ct[r["item_id"]], reverse=True):
        tgt = "D" if (r["item_id"] not in [x["item_id"] for x in sheets["D"]]
                      and len(sheets["D"]) < 9) else "E"
        assert r["item_id"] not in [x["item_id"] for x in sheets[tgt]]
        sheets[tgt].append(r)
    for name in sheets:
        rng.shuffle(sheets[name])

    rubric = (BASE / "rubric_r1.txt").read_text()
    rubric_sha = hashlib.sha256(rubric.encode()).hexdigest()
    key_entries = []
    for name, rows in sheets.items():
        out = [f"# OE-1 judge trust tranche — sheet {name} of 2 (parameter 5, fresh)\n"]
        out.append("PILOT -- open-ended instrument validation on dev subjects; "
                   "no research conclusions.\n")
        out.append("Label each row SAME / DIFFERENT / UNCLEAR **with the rubric "
                   "below in hand** — apply it as written, boundary rules included. "
                   "Do not open `fresh_tranche_key.json` until every row on both "
                   "sheets is labeled. No row here appeared in sheets A/B/C.\n")
        out.append(f"## The frozen rubric (sha256 `{rubric_sha}`)\n\n```\n{rubric}\n```\n")
        for i, r in enumerate(rows, 1):
            entry = f"{name}{i}"
            item = items[r["item_id"]]
            out.append(f"## {entry}\n")
            out.append(f"**QUESTION.** {item['question']}\n")
            out.append(f"**REAL ANSWER.** {item['real_answer_verbatim']}\n")
            out.append(f"**CANDIDATE ANSWER.** {r['text']}\n")
            out.append("`SAME / DIFFERENT / UNCLEAR:` ______\n\n---\n")
            key_entries.append({"entry": entry, "sheet": name, "position": i,
                                "item_id": r["item_id"], "canonical_id": r["canonical_id"],
                                "arm": r["arm"], "model": r["model"],
                                "judge_label": r["label"], "judge_why": r["why"]})
        text = "\n".join(out)
        for leak in ARM_NAMES + ["Gemma-4-31B", "flash-lite", "flashlite",
                                 "judge_label", "scored_model"]:
            assert leak not in text, f"leak {leak!r} in sheet {name}"
        (BASE / f"fresh_tranche_sheet_{name}.md").write_text(text)

    key = {"purpose": "Parameter-5 fresh tranche (owner-directed 2026-07-28). "
                      "Do not open until both sheets are labeled.",
           "bar_pre_committed": BAR_TEXT, "seed": SEED, "n_rows": N_ROWS,
           "recipe": "same as A/B/C: SAME/DIFFERENT primary balance, UNCLEAR fills "
                     "shortfall (documented); spread across arms, models, subjects; "
                     "twin rule per sub-sheet; drawn only from combos unused in A/B/C",
           "achieved_balance": dict(Counter(e["judge_label"] for e in key_entries)),
           "shortfall": shortfall,
           "arms": dict(Counter(e["arm"] for e in key_entries)),
           "models": dict(Counter(e["model"] for e in key_entries)),
           "subjects": dict(Counter(e["canonical_id"] for e in key_entries)),
           "subjects_note": "C01677 absent: a single-item subject whose fresh-pool "
                            "rows lost out to the two-rows-per-item cap under strict "
                            "9/9 label balance. Documented, not hidden.",
           "rubric_sha256": rubric_sha, "entries": key_entries}
    json.dump(key, open(BASE / "fresh_tranche_key.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in key.items() if k != "entries"}, indent=1))


if __name__ == "__main__":
    main()
