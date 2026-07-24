"""Pull role evidence from the MediaSum corpus for the staff-filter reserve.

One targeted pass over data/mediasum/news_dialogue.json:
  * every raw speaker label anywhere in the corpus that normalizes to a reserve
    subject's name -> exclusion evidence (role-marked) or guest evidence
    (affiliation-bearing), with transcript ids
  * for the subject's own transcripts (and any transcript where a matching
    label appears): the summary sentence(s) naming them, and the utterance
    sentence(s) naming them (host introductions, byline sign-offs)

CPU only, no network, no LLM.

Run: uv run python experiments/reserve_evidence_v2.py
"""
import json
import os
import pickle
import re
import sys
import time
from collections import Counter, defaultdict

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
import mediasum_index as M  # noqa: E402
import staff_crossref as SC  # noqa: E402

RAW_JSON = os.path.join(ROOT, "data/mediasum/news_dialogue.json")
POOL = os.path.join(ROOT, "results/stage2_candidate_pool_v2.csv")
CANON_MAP = os.path.join(ROOT, "data/mediasum_index/canonical_map_v2.csv")
DEDUP = os.path.join(ROOT, "data/mediasum_index/dedup_map_v2.csv")
CACHE = os.path.join(ROOT, "data/mediasum_index/_scan_cache_v2.pkl")
OUT = os.path.join(ROOT, "data/mediasum_index/_reserve_evidence_v2.json")

MAX_LABEL_TIDS = 6          # example transcript ids kept per distinct raw label
MAX_QUOTES_PER_KIND = 60    # cap per subject per evidence kind

REC_START = re.compile(r'\{"id": "([^"]+)", "program": "')


# ---------------------------------------------------------------- reserve set
def build_reserve():
    s = pd.read_csv(POOL)
    m = (s["staff_evidence"] == "yes") & (s["summary_staff"] != "staff")
    oth = ((~s["initial_label"]) & (~s["label_artifact"])
           & (~s["ambiguous_identity"]) & (~s["over_top500_head"])
           & (s["canonical_name"].str.split().str.len() >= 2))
    q = (m & oth & (s["subst_dedup"] >= 3) & (s["span_days_dedup"] >= 180)
         & (s["n_dates_dedup"] >= 3))
    reserve = s[q].copy()
    # anchors that the summary filter (not the label filter) excluded; carried
    # along as controls even though they are not in the reserve proper
    anchors = s[s["canonical_name"].isin(["Alex Kellogg", "Brian Unger"])].copy()
    anchors["in_reserve"] = False
    reserve["in_reserve"] = True
    both = pd.concat([reserve, anchors])
    return s, reserve, both


def sentence_around(text, a, b, pad=200):
    """Enclosing sentence(s) for text[a:b], clipped to +-pad chars."""
    lo = max(0, a - pad)
    hi = min(len(text), b + pad)
    seg = text[lo:hi]
    ra = a - lo
    rb = b - lo
    left = 0
    for mm in re.finditer(r'(?<=[.!?])\s+', seg[:ra]):
        left = mm.end()
    right = len(seg)
    mm = re.search(r'(?<=[.!?])\s+', seg[rb:])
    if mm:
        right = rb + mm.start() + 1
    out = seg[left:right].strip()
    if lo > 0 and left == 0:
        out = "..." + out
    if hi < len(text) and right == len(seg):
        out = out + "..."
    return re.sub(r"\s+", " ", out)


def main():
    t0 = time.time()
    pool, reserve, both = build_reserve()
    subjects = list(both["canonical_name"])
    print(f"reserve={len(reserve)} +anchors -> {len(subjects)} subjects")

    # variants -> canonical
    cmap = pd.read_csv(CANON_MAP)
    var_by_canon = defaultdict(set)
    for v, c in zip(cmap["variant_name"], cmap["canonical_name"]):
        var_by_canon[c].add(v)
    for c in subjects:
        var_by_canon[c].add(c)

    name2canon = {}
    for c in subjects:
        for v in var_by_canon[c]:
            if len(str(v).split()) >= 2:
                name2canon.setdefault(str(v), set()).add(c)

    # per-subject mention regex (full-name forms only)
    mention_re = {}
    for c in subjects:
        forms = sorted({v for v in var_by_canon[c] if len(str(v).split()) >= 2},
                       key=len, reverse=True)
        pat = "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in forms)
        mention_re[c] = re.compile(rf"\b(?:{pat})\b", re.I)

    # own transcripts
    ded = pd.read_csv(DEDUP)
    ded = ded[ded["canonical_name"].isin(set(subjects))]
    own = defaultdict(set)
    for c, t in zip(ded["canonical_name"], ded["transcript_id"]):
        own[c].add(t)
    tid_subject = defaultdict(set)
    for c, ts in own.items():
        for t in ts:
            tid_subject[t].add(c)
    print(f"own transcripts: {len(tid_subject)}")

    # ------------------------------------------------------------ corpus pass
    label_hits = defaultdict(Counter)          # canon -> Counter(raw label)
    label_tids = defaultdict(lambda: defaultdict(list))   # canon -> label -> tids
    summ_quotes = defaultdict(list)            # canon -> [(tid, sentence)]
    utt_quotes = defaultdict(list)             # canon -> [(tid, who, sentence)]
    tid_meta = {}
    norm_cache = {}
    n = 0
    n_full = 0
    buf = ""
    with open(RAW_JSON, encoding="utf-8") as f:
        pending = None   # (tid, start_offset_in_buf)
        while True:
            chunk = f.read(64 * 1024 * 1024)
            if not chunk:
                break
            buf += chunk
            starts = [(mm.start(), mm.group(1)) for mm in REC_START.finditer(buf)]
            for i in range(len(starts) - 1):
                a, tid = starts[i]
                b = starts[i + 1][0]
                rec_text = buf[a:b].rstrip().rstrip(",")
                n += 1
                process(rec_text, tid, name2canon, norm_cache, tid_subject,
                        mention_re, label_hits, label_tids, summ_quotes,
                        utt_quotes, tid_meta)
            if starts:
                buf = buf[starts[-1][0]:]
            else:
                buf = buf[-1_000_000:]
            print(f"  ...{n} recs ({time.time()-t0:.0f}s)", flush=True)
    # tail record
    rec_text = buf.rstrip()
    if rec_text.endswith("]"):
        rec_text = rec_text[:-1].rstrip().rstrip(",")
    mm = REC_START.match(rec_text)
    if mm:
        n += 1
        process(rec_text, mm.group(1), name2canon, norm_cache, tid_subject,
                mention_re, label_hits, label_tids, summ_quotes, utt_quotes,
                tid_meta)
    print(f"scanned {n} records in {time.time()-t0:.0f}s; "
          f"distinct labels normalized={len(norm_cache)}")

    out = {
        "subjects": {},
        "n_records": n,
        "scan_secs": time.time() - t0,
    }
    for _, row in both.iterrows():
        c = row["canonical_name"]
        out["subjects"][c] = {
            "in_reserve": bool(row["in_reserve"]),
            "wiki_status": row["wiki_status"],
            "long_tail": row["wiki_status"] == "long-tail",
            "subst_dedup": int(row["subst_dedup"]),
            "n_dates_dedup": int(row["n_dates_dedup"]),
            "span_days_dedup": int(row["span_days_dedup"]),
            "npr_share": float(row["npr_share"]),
            "n_programs": int(row["n_programs"]),
            "first_date": row["first_date"],
            "last_date": row["last_date"],
            "staff_marker": row["staff_marker"],
            "summary_staff": row["summary_staff"],
            "summary_evidence": row["summary_evidence"] if isinstance(
                row["summary_evidence"], str) else "",
            "affiliations": row["affiliations"] if isinstance(
                row["affiliations"], str) else "",
            "top_raw_label": row["top_raw_label"],
            "own_tids": sorted(own.get(c, []))[:40],
            "labels": {lb: {"n": cnt, "tids": label_tids[c][lb][:MAX_LABEL_TIDS]}
                       for lb, cnt in label_hits[c].most_common()},
            "summary_quotes": summ_quotes[c][:MAX_QUOTES_PER_KIND],
            "utt_quotes": utt_quotes[c][:MAX_QUOTES_PER_KIND],
        }
    with open(OUT, "w") as f:
        json.dump(out, f)
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")


def process(rec_text, tid, name2canon, norm_cache, tid_subject, mention_re,
            label_hits, label_tids, summ_quotes, utt_quotes, tid_meta):
    # --- cheap speaker-array slice (speaker is the last field) ---
    si = rec_text.rfind('"speaker": [')
    hit_subjects = set()
    if si >= 0:
        arr_txt = rec_text[si + len('"speaker": '):]
        e = arr_txt.rfind("]")
        arr_txt = arr_txt[:e + 1]
        try:
            labels = json.loads(arr_txt)
        except Exception:
            labels = []
        for raw in set(labels):
            nm = norm_cache.get(raw, 0)
            if nm == 0:
                try:
                    nm = SC.normalize_name(raw)
                except Exception:
                    nm = None
                norm_cache[raw] = nm
            if nm is None:
                continue
            cs = name2canon.get(nm)
            if not cs:
                continue
            for c in cs:
                hit_subjects.add(c)
                label_hits[c][raw] += 1
                if len(label_tids[c][raw]) < MAX_LABEL_TIDS:
                    label_tids[c][raw].append(tid)

    subs = set(tid_subject.get(tid, ())) | hit_subjects
    if not subs:
        return
    try:
        rec = json.loads(rec_text)
    except Exception:
        return
    summary = rec.get("summary") or ""
    utt = rec.get("utt") or []
    spk = rec.get("speaker") or []
    tid_meta[tid] = (rec.get("program", ""), rec.get("date", ""))
    for c in subs:
        rx = mention_re[c]
        for mm in rx.finditer(summary):
            if len(summ_quotes[c]) >= MAX_QUOTES_PER_KIND:
                break
            summ_quotes[c].append([tid, sentence_around(summary, mm.start(),
                                                        mm.end())])
        seen = set()
        for i in range(min(len(utt), len(spk))):
            text = utt[i] or ""
            if len(text) > 20000:
                text = text[:20000]
            mm = rx.search(text)
            if not mm:
                continue
            if len(utt_quotes[c]) >= MAX_QUOTES_PER_KIND:
                break
            who = spk[i]
            q = sentence_around(text, mm.start(), mm.end())
            key = (who, q[:90])
            if key in seen:
                continue
            seen.add(key)
            utt_quotes[c].append([tid, who, q])


if __name__ == "__main__":
    main()
