#!/usr/bin/env python3
"""Dev-only measurements behind the H6/B3 parameter proposal.

Amendment 2 B3 leaves four H6 numbers to bar-lock: the grounding token
budget(s) B, the segment/chain definitions, the rich/poor cut, and the
flagged-turn threshold. Addendum A adopted 2026-07-28 with that slot
deliberately open. This script measures what the DEV data can support so the
proposal in ``results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md`` rests on
numbers rather than taste.

Touches dev subjects only. Confirmatory subjects are untouched: every input
path below is under ``results/stage2_pilot/`` (the 6 dev subjects) or
``results/stage2_openended/`` (the dev audit sheet and its key).

Pure standard library. No network, no model calls, no GPU. Deterministic:
enumeration only, no sampling. SEED is declared and asserted unused so the
determinism claim is checkable rather than asserted.

Run:  uv run python experiments/h6_b3_measure.py
Out:  stdout only (this script writes no files).
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from doppler.followup_render import (  # noqa: E402
    CASE_HEADER,
    FOLLOW_UP,
    NEW_TOPIC,
    OUTPUT_INSTRUCTION,
    RUBRIC_SHA256,
)

#: Declared for the record. Nothing here samples, so nothing consumes it.
SEED = 63

PILOT = REPO / "results/stage2_pilot"
OE = REPO / "results/stage2_openended"

RECORDS = PILOT / "records/classify.jsonl"
PROMPTS = PILOT / "exports/prompts_classify.jsonl"
RULE_LABELS = PILOT / "exports/labels_rule.jsonl"
DEV_SUBJECTS = PILOT / "dev_subjects.json"

AUDIT_KEY = OE / "h6_audit_key.json"
AUDIT_SCORES = OE / "audit_scores.json"

#: Closed function-word list for the overlap measure below. Frozen here so the
#: measurement is reproducible from this file alone; deliberately small, since
#: the point is to strip grammar, not topic.
STOPWORDS = frozenset("""
a about all am an and any are as at be been being but by can could did do does
doing don for from get got had has have he her here hers him his how i if in
into is it its just know like me my no not now of on one or our out own really
right said say says she so some such than that the their them then there these
they thing things think this those to too us very want was we well were what
when where which who whom why will with would you your yours yeah yes ok okay
mr mrs ms dr going get lot going way going back going bit going sort kind
""".split())


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def words(text: str) -> int:
    """Words = whitespace tokens. Same proxy as stage2_render.word_count (D5)."""
    return len((text or "").split())


def content_words(text: str) -> set[str]:
    """Lowercased alphabetic tokens, stopwords and 1-2 letter tokens dropped."""
    out = set()
    for raw in (text or "").lower().split():
        tok = "".join(ch for ch in raw if ch.isalpha() or ch == "'").strip("'")
        if len(tok) > 2 and tok not in STOPWORDS:
            out.add(tok)
    return out


def case_fields(prompt: str) -> dict:
    """PREV / GUEST / TARGET, sliced out of the rendered classifier prompt.

    Taken from the prompt rather than re-derived, so the measurement sees
    byte-for-byte what the classifier saw (same 60/120/120-word truncations).
    """
    start = prompt.index(CASE_HEADER) + len(CASE_HEADER)
    end = prompt.index(OUTPUT_INSTRUCTION)
    block = prompt[start:end].strip()
    fields = {"PREV": "", "GUEST": "", "TARGET": ""}
    current = None
    for line in block.splitlines():
        hit = None
        for name in fields:
            if line.startswith(name + ":"):
                hit = name
                break
        if hit:
            current = hit
            fields[hit] = line[len(hit) + 1:].strip()
        elif current:
            fields[current] += " " + line.strip()
    return fields


# ---------------------------------------------------------------------------
# Segment assembly
# ---------------------------------------------------------------------------


def segments_for(cid: str) -> list[dict]:
    """One dict per host turn in a subject's grounding transcripts.

    A SEGMENT is one host turn plus the guest reply it drew (B2.3), which is
    also the unit ``stage2_render._exchange_items`` already selects on. The
    reply is the run of consecutive guest turns immediately after the host
    turn; a host or other-speaker turn closes it. A host turn with no reply
    behind it gets an empty reply and 0 guest words -- kept, because it is
    still a labelled turn and still costs its own words.
    """
    turns = read_jsonl(PILOT / f"subjects/{cid}/grounding_turns.jsonl")
    by_transcript: dict[str, list[dict]] = defaultdict(list)
    for t in turns:
        by_transcript[t["transcript_id"]].append(t)

    out = []
    for tid, rows in by_transcript.items():
        rows.sort(key=lambda r: r["turn_idx"])
        for i, row in enumerate(rows):
            if row.get("role") != "host":
                continue
            host_text = (row.get("text") or "").strip()
            if not host_text:
                continue
            reply = []
            for nxt in rows[i + 1:]:
                if nxt.get("role") != "guest":
                    break
                txt = (nxt.get("text") or "").strip()
                if txt:
                    reply.append(txt)
            guest_text = " ".join(reply)
            out.append({
                "canonical_id": cid,
                "transcript_id": tid,
                "turn_idx": row["turn_idx"],
                "host_words": words(host_text),
                "guest_words": words(guest_text),
                "words": words(host_text) + words(guest_text),
            })
    out.sort(key=lambda s: (s["transcript_id"], s["turn_idx"]))
    return out


def attach_labels(segs: list[dict], labels: dict, drops: set) -> None:
    for s in segs:
        key = (s["canonical_id"], s["transcript_id"], s["turn_idx"])
        s["label"] = labels.get(key)
        s["dropped"] = key in drops


# ---------------------------------------------------------------------------
# Chains
# ---------------------------------------------------------------------------


def chains_for(segs: list[dict]) -> list[dict]:
    """Chains under the proposed definition.

    A CHAIN is one NEW-TOPIC root segment plus the maximal run of FOLLOW-UP
    segments that immediately follows it in the same transcript. Chain DEPTH
    is the number of FOLLOW-UP segments (root excluded), so depth >= 1 by
    construction -- a NEW-TOPIC turn with no FOLLOW-UP behind it is not a
    chain, it is a lone new-topic segment.

    An unlabelled (dropped) turn BREAKS a run: the code cannot tell whether it
    continued the chain, and guessing would launder a drop into evidence.
    A FOLLOW-UP run with no NEW-TOPIC root in front of it (transcript opens
    mid-chain, or the root was dropped) is a ROOTLESS chain and is counted
    separately.
    """
    out = []
    by_transcript: dict[str, list[dict]] = defaultdict(list)
    for s in segs:
        by_transcript[s["transcript_id"]].append(s)

    for tid, rows in by_transcript.items():
        rows.sort(key=lambda r: r["turn_idx"])
        i = 0
        while i < len(rows):
            if rows[i].get("label") != FOLLOW_UP or rows[i]["dropped"]:
                i += 1
                continue
            j = i
            while (j < len(rows) and rows[j].get("label") == FOLLOW_UP
                   and not rows[j]["dropped"]):
                j += 1
            run = rows[i:j]
            root = None
            if i > 0 and rows[i - 1].get("label") == NEW_TOPIC and not rows[i - 1]["dropped"]:
                root = rows[i - 1]
            out.append({
                "transcript_id": tid,
                "root_turn_idx": root["turn_idx"] if root else None,
                "rootless": root is None,
                "depth": len(run),
                "members": ([root] if root else []) + run,
                "words": sum(m["words"] for m in ([root] if root else []) + run),
                "followup_words": sum(m["words"] for m in run),
            })
            i = j
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    dev = json.load(DEV_SUBJECTS.open())
    dev_ids = [s["canonical_id"] for s in dev["subjects"]]

    records = read_jsonl(RECORDS)
    rule_rows = read_jsonl(RULE_LABELS)
    prompts = {r["idx"]: r["prompt"] for r in read_jsonl(PROMPTS)}

    labels: dict = {}
    drops: set = set()
    by_rec: dict = {}
    for r in records:
        key = (r["canonical_id"], r["transcript_id"], r["turn_idx"])
        if r.get("parse_failure") or r.get("missing_completion"):
            drops.add(key)
            continue
        labels[key] = r["label"]
        by_rec[r.get("idx")] = r
    for r in rule_rows:
        labels.setdefault(
            (r["canonical_id"], r["transcript_id"], r["turn_idx"]), r["label"]
        )

    print("=" * 74)
    print("H6 / B3 dev measurement -- 6 dev subjects, CPU only, $0")
    print(f"rubric sha256 {RUBRIC_SHA256}")
    print(f"seed {SEED} (declared; nothing here samples)")
    print("=" * 74)

    print("\n--- 0. classifier record census -------------------------------")
    src = Counter(r.get("source") for r in records)
    lab = Counter(r.get("label") for r in records if not r.get("parse_failure"))
    print(f"records {len(records)}  by source {dict(src)}")
    print(f"labels  {dict(lab)}")
    print(f"drops (parse failure / missing completion): {len(drops)}")

    # -------------------------------------------------------------------
    per_subject = {}
    all_chains = {}
    for cid in dev_ids:
        segs = segments_for(cid)
        attach_labels(segs, labels, drops)
        chains = chains_for(segs)
        per_subject[cid] = segs
        all_chains[cid] = chains

    print("\n--- 1. segment supply per dev subject (words = host + guest) ---")
    print(f"{'subject':9} {'segs':>5} {'lab':>4} {'drop':>4} {'FU':>4} {'NT':>4} "
          f"{'allwords':>9} {'FUwords':>8} {'NTwords':>8}")
    for cid in dev_ids:
        segs = per_subject[cid]
        lab_segs = [s for s in segs if s["label"] and not s["dropped"]]
        fu = [s for s in lab_segs if s["label"] == FOLLOW_UP]
        nt = [s for s in lab_segs if s["label"] == NEW_TOPIC]
        print(f"{cid:9} {len(segs):5} {len(lab_segs):4} "
              f"{sum(1 for s in segs if s['dropped']):4} {len(fu):4} {len(nt):4} "
              f"{sum(s['words'] for s in segs):9} {sum(s['words'] for s in fu):8} "
              f"{sum(s['words'] for s in nt):8}")

    print("\n--- 2. chains ---------------------------------------------------")
    print(f"{'subject':9} {'chains':>6} {'rootless':>8} {'depth1':>6} {'depth2':>6} "
          f"{'depth3+':>7} {'maxdepth':>8} {'chainwords':>10}")
    depth_all = []
    for cid in dev_ids:
        ch = all_chains[cid]
        d = [c["depth"] for c in ch]
        depth_all += d
        print(f"{cid:9} {len(ch):6} {sum(1 for c in ch if c['rootless']):8} "
              f"{sum(1 for x in d if x == 1):6} {sum(1 for x in d if x == 2):6} "
              f"{sum(1 for x in d if x >= 3):7} {max(d) if d else 0:8} "
              f"{sum(c['words'] for c in ch):10}")
    print(f"pooled depth distribution: {dict(sorted(Counter(depth_all).items()))}")
    print(f"pooled chains {len(depth_all)}  "
          f"median depth {statistics.median(depth_all) if depth_all else 0}")

    print("\n--- 3. arm supply and the feasible budget B --------------------")
    print("rich  = segments inside a chain of depth >= D (root + follow-ups)")
    print("poor  = NEW-TOPIC segments that are NOT a chain root (lone new topics)")
    print("arms are disjoint by construction: a root belongs to rich, never poor")
    for dmin in (1, 2):
        print(f"\n  D_min = {dmin}")
        print(f"  {'subject':9} {'richW':>7} {'poorW':>7} {'feasibleB':>10} "
              f"{'richSegs':>8} {'poorSegs':>8}")
        feas = []
        for cid in dev_ids:
            ch = [c for c in all_chains[cid] if c["depth"] >= dmin]
            rich_ids = {(m["transcript_id"], m["turn_idx"]) for c in ch
                        for m in c["members"]}
            rich_w = sum(m["words"] for c in ch for m in c["members"])
            roots = {(c["transcript_id"], c["root_turn_idx"])
                     for c in all_chains[cid] if not c["rootless"]}
            poor = [s for s in per_subject[cid]
                    if s["label"] == NEW_TOPIC and not s["dropped"]
                    and (s["transcript_id"], s["turn_idx"]) not in roots
                    and (s["transcript_id"], s["turn_idx"]) not in rich_ids]
            poor_w = sum(s["words"] for s in poor)
            b = min(rich_w, poor_w)
            feas.append(b)
            print(f"  {cid:9} {rich_w:7} {poor_w:7} {b:10} "
                  f"{len(rich_ids):8} {len(poor):8}")
        print(f"  feasible B across 6 dev subjects: "
              f"min {min(feas)}  median {statistics.median(feas)}  max {max(feas)}")
        for level in (300, 400, 500, 600, 800, 1000, 1500, 2000):
            n = sum(1 for b in feas if b >= level)
            print(f"    B = {level:5} words -> {n}/6 dev subjects eligible")

    print("\n--- 3b. can each arm actually be FILLED to within +/-5% of B? ---")
    print("rich fill : whole chains, deepest first (date desc, transcript,")
    print("            root idx as tie-breaks), skip-not-stop; then a")
    print("            segment-level top-up from unused chain members,")
    print("            newest first. poor fill: lone NEW-TOPIC segments,")
    print("            newest first, skip-not-stop. Segments are never split.")

    dates = {}
    for cid in dev_ids:
        sp = json.load((PILOT / f"subjects/{cid}/split.json").open())
        for c in sp["grounding"]:
            dates[(cid, c["transcript_id"])] = c["date"]

    def fill(items, budget):
        """Greedy skip-not-stop over (sort_key, words) items. Returns words used."""
        used = 0
        for _k, w in items:
            if used + w <= budget:
                used += w
        return used

    def rich_used(cid, dmin, budget):
        ch = sorted(
            (c for c in all_chains[cid] if c["depth"] >= dmin),
            key=lambda c: (-c["depth"], _negdate(dates.get((cid, c["transcript_id"]), "")),
                           c["transcript_id"], c["root_turn_idx"] or -1),
        )
        used = 0
        leftover = []
        for c in ch:
            if used + c["words"] <= budget:
                used += c["words"]
            else:
                leftover += c["members"]
        leftover.sort(key=lambda m: (_negdate(dates.get((cid, m["transcript_id"]), "")),
                                     m["transcript_id"], -m["turn_idx"]))
        for m in leftover:
            if used + m["words"] <= budget:
                used += m["words"]
        return used

    def _negdate(d):
        # descending date via a reversible key on the ISO string
        return tuple(-ord(ch) for ch in (d or ""))

    def poor_used(cid, budget):
        roots = {(c["transcript_id"], c["root_turn_idx"])
                 for c in all_chains[cid] if not c["rootless"]}
        inchain = {(m["transcript_id"], m["turn_idx"])
                   for c in all_chains[cid] for m in c["members"]}
        poor = [s for s in per_subject[cid]
                if s["label"] == NEW_TOPIC and not s["dropped"]
                and (s["transcript_id"], s["turn_idx"]) not in roots
                and (s["transcript_id"], s["turn_idx"]) not in inchain]
        poor.sort(key=lambda s: (_negdate(dates.get((cid, s["transcript_id"]), "")),
                                 s["transcript_id"], -s["turn_idx"]))
        return fill([(None, s["words"]) for s in poor], budget)

    for dmin in (1, 2):
        print(f"\n  D_min = {dmin}   (cell = rich%/poor% of B; PASS needs both >= 95%)")
        header = "  " + f"{'subject':9}" + "".join(
            f"{('B=' + str(b)):>14}" for b in (400, 600, 800, 1000, 1200, 1500))
        print(header)
        pass_count = Counter()
        for cid in dev_ids:
            cells = []
            for b in (400, 600, 800, 1000, 1200, 1500):
                r = rich_used(cid, dmin, b) / b
                p = poor_used(cid, b) / b
                ok = r >= 0.95 and p >= 0.95
                pass_count[b] += 1 if ok else 0
                cells.append(f"{r:.2f}/{p:.2f}{'*' if ok else ' '}".rjust(14))
            print(f"  {cid:9}" + "".join(cells))
        print("  " + "eligible".ljust(9) + "".join(
            f"{str(pass_count[b]) + '/6':>14}" for b in (400, 600, 800, 1000, 1200, 1500)))

    print("\n  poor-arm supply if chain ROOTS were allowed into the poor arm")
    print("  (rejected in the proposal -- it would put drilled content in both")
    print("   arms -- but the cost of rejecting it is reported):")
    for cid in dev_ids:
        roots = [(c["transcript_id"], c["root_turn_idx"])
                 for c in all_chains[cid] if not c["rootless"]]
        rw = sum(s["words"] for s in per_subject[cid]
                 if (s["transcript_id"], s["turn_idx"]) in set(roots))
        base = poor_used(cid, 10 ** 9)
        print(f"    {cid:9} lone-NT words {base:6}  + root words {rw:6} "
              f"= {base + rw:6}")

    print("\n--- 4. follow-up density per grounding cluster ------------------")
    print("density = FOLLOW-UP segments / labelled segments in the cluster")
    rows = []
    for cid in dev_ids:
        by_t: dict[str, list[dict]] = defaultdict(list)
        for s in per_subject[cid]:
            if s["label"] and not s["dropped"]:
                by_t[s["transcript_id"]].append(s)
        for tid, segs in sorted(by_t.items()):
            fu = sum(1 for s in segs if s["label"] == FOLLOW_UP)
            rows.append((cid, tid, len(segs), fu, fu / len(segs)))
    rows.sort(key=lambda r: r[4])
    for cid, tid, n, fu, d in rows:
        print(f"  {cid} {tid:12} n={n:3} FU={fu:3} density={d:.3f}")
    dens = [r[4] for r in rows]
    print(f"  clusters {len(dens)}  median {statistics.median(dens):.3f}  "
          f"mean {statistics.mean(dens):.3f}")
    print("  histogram (0.05-wide bins):")
    hist = Counter(min(int(d / 0.05), 19) for d in dens)
    for b in range(20):
        if hist[b]:
            print(f"    [{b*0.05:.2f},{(b+1)*0.05:.2f}) {'#' * hist[b]} {hist[b]}")
    for cut in (0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        print(f"    cut {cut:.2f}: rich {sum(1 for d in dens if d >= cut)}  "
              f"poor {sum(1 for d in dens if d < cut)}")

    # -------------------------------------------------------------------
    print("\n--- 5. flagged turns: the FOLLOW-UP boundary -------------------")
    key = json.load(AUDIT_KEY.open())
    scores = json.load(AUDIT_SCORES.open())["h6_coaudit"]
    co = {int(k): v for k, v in scores["labels"].items()}
    lowconf = set(scores["low_confidence_rows"])
    disagree = set(scores["disagreement_rows"])

    audit = []
    for row in key["key"]:
        n = row["row"]
        rec = by_rec.get(row["record_idx"])
        if rec is None:
            continue
        f = case_fields(prompts[row["record_idx"]])
        tw = content_words(f["TARGET"])
        gw = content_words(f["GUEST"])
        overlap = len(tw & gw) / len(tw) if tw else 0.0
        audit.append({
            "row": n,
            "classifier": row["classifier_label"],
            "coauditor": co.get(n),
            "agree": co.get(n) == row["classifier_label"],
            "lowconf": n in lowconf,
            "overlap": overlap,
            "n_shared": len(tw & gw),
            "target_words": words(f["TARGET"]),
        })

    assert {a["row"] for a in audit if not a["agree"]} == disagree, \
        "reconstructed disagreements do not match the recorded set"
    print(f"  reconstructed {len(audit)} audit rows; disagreements match "
          f"the recorded set {sorted(disagree)}")

    fu_rows = [a for a in audit if a["classifier"] == FOLLOW_UP]
    fu_ok = [a for a in fu_rows if a["agree"]]
    fu_bad = [a for a in fu_rows if not a["agree"]]
    print(f"\n  classifier FOLLOW-UP rows on the sheet: {len(fu_rows)}  "
          f"upheld {len(fu_ok)}  overturned by the co-auditor {len(fu_bad)}")

    def desc(name, rows_, field):
        v = sorted(r[field] for r in rows_)
        if not v:
            print(f"    {name:34} (none)")
            return
        print(f"    {name:34} n={len(v):3} min={v[0]:.3f} "
              f"p25={v[len(v)//4]:.3f} med={statistics.median(v):.3f} "
              f"p75={v[3*len(v)//4]:.3f} max={v[-1]:.3f}")

    print("  shared-content-word overlap (TARGET vs GUEST), FOLLOW-UP rows:")
    desc("upheld FOLLOW-UP", fu_ok, "overlap")
    desc("overturned FOLLOW-UP", fu_bad, "overlap")
    print("  absolute count of shared content words:")
    desc("upheld FOLLOW-UP", fu_ok, "n_shared")
    desc("overturned FOLLOW-UP", fu_bad, "n_shared")

    print("\n  candidate flag rules on the 120-row sheet "
          "(fires on classifier FOLLOW-UP only):")
    for thresh in (0, 1, 2, 3):
        fired = [a for a in fu_rows if a["n_shared"] <= thresh]
        caught = [a for a in fired if not a["agree"]]
        print(f"    shared content words <= {thresh}: fires on "
              f"{len(fired):3}/{len(fu_rows)} FOLLOW-UP rows, catches "
              f"{len(caught)}/{len(fu_bad)} overturned "
              f"({len(caught)/len(fu_bad) if fu_bad else 0:.0%} recall, "
              f"{len(caught)/len(fired) if fired else 0:.0%} precision)")
    for thresh in (0.05, 0.10, 0.15, 0.20):
        fired = [a for a in fu_rows if a["overlap"] <= thresh]
        caught = [a for a in fired if not a["agree"]]
        print(f"    overlap fraction <= {thresh:.2f}: fires on "
              f"{len(fired):3}/{len(fu_rows)} FOLLOW-UP rows, catches "
              f"{len(caught)}/{len(fu_bad)} overturned "
              f"({len(caught)/len(fu_bad) if fu_bad else 0:.0%} recall, "
              f"{len(caught)/len(fired) if fired else 0:.0%} precision)")

    print("\n  co-auditor self-flagged low-confidence rows as a comparator:")
    lc = [a for a in audit if a["lowconf"]]
    print(f"    {len(lc)}/120 rows flagged, catching "
          f"{sum(1 for a in lc if not a['agree'])}/{len(disagree)} disagreements")

    nt_rows = [a for a in audit if a["classifier"] == NEW_TOPIC]
    print("\n  the asymmetry, as an error rate per label:")
    print(f"    classifier FOLLOW-UP rows: {len(fu_rows)}, overturned "
          f"{len(fu_bad)} -> {len(fu_bad)/len(fu_rows):.1%}")
    print(f"    classifier NEW-TOPIC rows: {len(nt_rows)}, overturned "
          f"{sum(1 for a in nt_rows if not a['agree'])} -> "
          f"{sum(1 for a in nt_rows if not a['agree'])/len(nt_rows):.1%}")

    # ---- 5b: does the boundary error sit in shallow chains? -------------
    print("\n--- 5b. where the overturned FOLLOW-UPs sit in the chain --------")
    pos_of = {}
    for cid in dev_ids:
        for c in all_chains[cid]:
            run = [m for m in c["members"]
                   if m.get("label") == FOLLOW_UP and not m["dropped"]]
            for k, m in enumerate(run, start=1):
                pos_of[(cid, m["transcript_id"], m["turn_idx"])] = (c["depth"], k)

    key_by_row = {r["row"]: r for r in key["key"]}
    tab = defaultdict(lambda: [0, 0])   # depth -> [upheld, overturned]
    postab = defaultdict(lambda: [0, 0])  # position -> [upheld, overturned]
    for a in fu_rows:
        k = key_by_row[a["row"]]
        pk = (k["canonical_id"], k["transcript_id"], k["turn_idx"])
        if pk not in pos_of:
            continue
        depth, pos = pos_of[pk]
        dbin = depth if depth <= 2 else 3
        pbin = pos if pos <= 2 else 3
        tab[dbin][0 if a["agree"] else 1] += 1
        postab[pbin][0 if a["agree"] else 1] += 1
    print("  by chain depth (3 = depth 3+):")
    for d in sorted(tab):
        up, bad = tab[d]
        print(f"    depth {d}: upheld {up:3}  overturned {bad:3}  "
              f"error {bad/(up+bad):.1%}")
    print("  by position of the FOLLOW-UP within its chain (3 = 3rd or later):")
    for p in sorted(postab):
        up, bad = postab[p]
        print(f"    pos {p}: upheld {up:3}  overturned {bad:3}  "
              f"error {bad/(up+bad):.1%}")

    # ---- 5c: rich-supply sensitivity to the co-auditor's labels ---------
    print("\n--- 5c. rich-arm supply if the co-auditor's labels are used ----")
    print("  (co-auditor labels substituted on the 120 audited turns only;")
    print("   every other turn keeps its classifier label)")
    strict_labels = dict(labels)
    for row in key["key"]:
        n = row["row"]
        if n in co:
            strict_labels[(row["canonical_id"], row["transcript_id"],
                           row["turn_idx"])] = co[n]
    print(f"  {'subject':9} {'richW(D1)':>10} {'strict':>8} {'delta':>8} "
          f"{'richW(D2)':>10} {'strict':>8} {'delta':>8}")
    for cid in dev_ids:
        segs2 = segments_for(cid)
        attach_labels(segs2, strict_labels, drops)
        ch2 = chains_for(segs2)
        out = []
        for dmin in (1, 2):
            base = sum(m["words"] for c in all_chains[cid]
                       if c["depth"] >= dmin for m in c["members"])
            strict = sum(m["words"] for c in ch2
                         if c["depth"] >= dmin for m in c["members"])
            out.append((base, strict))
        (b1, s1), (b2, s2) = out
        print(f"  {cid:9} {b1:10} {s1:8} {s1-b1:8} {b2:10} {s2:8} {s2-b2:8}")

    # ---- corpus-wide fire rate of the proposed rule --------------------
    print("\n--- 6. corpus-wide flag rate at the proposed rule ---------------")
    print("rule: a FOLLOW-UP turn is FLAGGED when it shares <= 1 content word")
    print("      with the guest answer it claims to follow up on")
    print(f"{'subject':9} {'FUsegs':>7} {'flagged':>8} {'rate':>7} "
          f"{'dropped':>8} {'droprate':>9}")
    subj_rates = []
    for cid in dev_ids:
        fu_recs = [r for r in records
                   if r["canonical_id"] == cid and r.get("source") == "model"
                   and not r.get("parse_failure") and not r.get("missing_completion")
                   and r["label"] == FOLLOW_UP]
        flagged = 0
        for r in fu_recs:
            f = case_fields(prompts[r["idx"]])
            if len(content_words(f["TARGET"]) & content_words(f["GUEST"])) <= 1:
                flagged += 1
        n_model = sum(1 for r in records if r["canonical_id"] == cid
                      and r.get("source") == "model")
        n_drop = sum(1 for r in records if r["canonical_id"] == cid
                     and (r.get("parse_failure") or r.get("missing_completion")))
        rate = flagged / len(fu_recs) if fu_recs else 0.0
        subj_rates.append(rate)
        print(f"{cid:9} {len(fu_recs):7} {flagged:8} {rate:7.3f} "
              f"{n_drop:8} {n_drop / n_model if n_model else 0:9.3f}")
    print(f"pooled flag rate min {min(subj_rates):.3f}  "
          f"median {statistics.median(subj_rates):.3f}  max {max(subj_rates):.3f}")

    print("\ncost: CPU only, no API calls, no GPU. $0.00.")


if __name__ == "__main__":
    main()
