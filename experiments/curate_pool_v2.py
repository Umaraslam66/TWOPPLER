"""Phase B curation — the three mechanical fixes, on top of curate_scan_v2.py.

Reads the cached scan (data/mediasum_index/_scan_cache_v2.pkl) and produces:

  1. data/mediasum_index/guest_interviews_v2.csv
        every (guest, transcript) row with a TOLERANTLY parsed date and a
        date_quality flag. The Phase A parser demanded zero-padded month/day
        and threw away 41.8% of the corpus.
  2. data/mediasum_index/canonical_map_v2.csv
        conservative label-variant merges, each with the rule that fired and
        the transcript evidence behind it.
  3. data/mediasum_index/dedup_map_v2.csv
        near-duplicate clusters of a subject's appearances (re-airings,
        same-interview-on-three-shows, posthumous re-broadcasts). One cluster
        counts as ONE interview.
  4. data/mediasum_index/canonical_stats_v2.csv
        per-canonical-subject deduped counts, fixed-date span, npr share.

CPU only, no network, no LLM. Run: uv run python experiments/curate_pool_v2.py
"""
import csv
import os
import pickle
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402

ROOT = M.ROOT
OUT_DIR = M.OUT_DIR
CACHE_PKL = os.path.join(OUT_DIR, "_scan_cache_v2.pkl")
DATES_CSV = os.path.join(OUT_DIR, "transcript_dates_v2.csv")
POOL_CSV = os.path.join(ROOT, "results/stage2_candidate_pool.csv")

INTERVIEWS_V2 = os.path.join(OUT_DIR, "guest_interviews_v2.csv")
CANON_MAP = os.path.join(OUT_DIR, "canonical_map_v2.csv")
DEDUP_MAP = os.path.join(OUT_DIR, "dedup_map_v2.csv")
CANON_STATS = os.path.join(OUT_DIR, "canonical_stats_v2.csv")
STAFF_V2 = os.path.join(OUT_DIR, "staff_crossref_v2.csv")
SUMMARY_JSON = os.path.join(OUT_DIR, "_curation_summary_v2.json")

# near-duplicate thresholds (frozen here, reported in the curation report)
JACCARD_DUP = 0.60          # same text, minor transcription differences
CONTAIN_DUP = 0.80          # one airing is a subset of the other (re-broadcast)
MIN_SHINGLES_FOR_CONTAIN = 50
MIN_SHINGLES_FOR_JACCARD = 20

# An initial-form label ("C. Reeve") is merged into a full name only when the
# full name is present in at least this share of the initial form's own
# transcripts. Without it, one shared transcript was enough to fold "J. Edwards"
# (27 transcripts, mostly the senator) into "Justin Edwards" (1 transcript).
MIN_INITIAL_COVERAGE = 0.75

SUBST_MIN_WORDS = M.SUBST_MIN_WORDS   # 300
SUBST_MIN_TURNS = M.SUBST_MIN_TURNS   # 5

PARTICLES = {"DE", "DEL", "DELLA", "DI", "DA", "DOS", "VAN", "VON", "LA", "LE",
             "EL", "AL", "BIN", "IBN", "TER", "TEN", "DU", "ST", "SAN", "MAC"}


# ---------------------------------------------------------------------------
class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

    def groups(self):
        g = defaultdict(list)
        for x in self.p:
            g[self.find(x)].append(x)
        return g


def _is_initial(tok):
    """A one-letter name fragment, whatever punctuation clings to it.

    Covers 'C.', 'C', and the transcription noise MediaSum leaves behind
    ('A+.' in 'A+. Harris').
    """
    letters = re.sub(r"[^A-Za-z]", "", tok)
    return len(letters) <= 1 and len(letters) >= 1


def initial_form(name):
    t = name.split()
    return bool(t) and _is_initial(t[0])


def particle_only(name):
    t = name.split()
    return len(t) == 2 and t[0].upper().rstrip(".") in PARTICLES


_AFF_PAREN = re.compile(r"\(([^)]*)\)")


def affiliations_of(raw_counter):
    """Distinct affiliation/role strings a subject's raw labels carry.

    'RICK NELSON, SENIOR FELLOW, CENTER FOR STRATEGIC AND INTERNATIONAL
    STUDIES' and 'Mr. RICK NELSON (Director, Homeland Security ...)' both
    yield one. Two unrelated affiliations under one name is the signature of
    an identity collision, so this is provenance for the human reviewer.
    """
    out = Counter()
    for lab, n in raw_counter.items():
        parts = [m.group(1) for m in _AFF_PAREN.finditer(lab)]
        base = _AFF_PAREN.sub(" ", lab)
        if "," in base:
            parts.append(base.split(",", 1)[1])
        for p in parts:
            p = re.sub(r"[^A-Za-z0-9& ]", " ", p)
            p = re.sub(r"\s+", " ", p).strip().upper()
            if len(p) >= 3:
                out[p] += n
    return out


def _digit_key(name):
    """Letters AND digits, uppercased. Digits carry identity in MediaSum
    labels ('Bush 41' vs 'Bush 43', 'Juror B-29' vs 'Juror B-37')."""
    return re.sub(r"[^A-Za-z0-9]", "", name).upper()


# ---------------------------------------------------------------------------
def step1_dates(tid_date):
    """Rewrite guest_interviews.csv with tolerant dates. Returns before/after."""
    before_dated = 0
    after = Counter()
    n = 0
    t0 = time.time()
    with open(M.INTERVIEWS_CSV) as fin, open(INTERVIEWS_V2, "w", newline="") as fout:
        r = csv.DictReader(fin)
        w = csv.writer(fout)
        w.writerow(["normalized_name", "transcript_id", "date", "date_quality",
                    "date_v1", "program", "title", "guest_words", "guest_turns",
                    "total_turns_in_transcript"])
        for row in r:
            n += 1
            if row["date"]:
                before_dated += 1
            iso, q, _prog = tid_date.get(row["transcript_id"], ("", "missing", ""))
            after[q] += 1
            w.writerow([row["normalized_name"], row["transcript_id"], iso, q,
                        row["date"], row["program"], row["title"],
                        row["guest_words"], row["guest_turns"],
                        row["total_turns_in_transcript"]])
    print(f"[dates] {INTERVIEWS_V2}: {n} rows in {time.time()-t0:.0f}s")
    print(f"[dates] rows with a date BEFORE={before_dated} "
          f"({before_dated/n:.1%})  AFTER={sum(v for k,v in after.items() if k.startswith('ok'))} "
          f"({sum(v for k,v in after.items() if k.startswith('ok'))/n:.1%})")
    print(f"[dates] quality breakdown: {dict(after)}")
    return {"rows": n, "before_dated": before_dated, "after": dict(after)}


# ---------------------------------------------------------------------------
def step2_merges(cache, pool_names, index_words):
    """Decide which variant proposals become real merges."""
    pairs = cache["pairs"]
    tid_names = cache["tid_names"]

    # co-occurrence: for each unordered name pair, the transcripts sharing both
    cooc = defaultdict(list)
    for tid, names in tid_names.items():
        ns = sorted(names)
        if len(ns) < 2:
            continue
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                cooc[(ns[i], ns[j])].append(tid)

    # a name whose initial-form co-occurs with >1 distinct full name is a
    # genuinely ambiguous label; refuse to merge it at all.
    initial_partners = defaultdict(set)
    for a, b, rule in pairs:
        if rule != "initial_vs_full":
            continue
        ev = cooc.get((min(a, b), max(a, b)), [])
        if not ev:
            continue
        ini, full = (a, b) if initial_form(a) else (b, a)
        initial_partners[ini].add(full)
    ambiguous = {k for k, v in initial_partners.items() if len(v) > 1}

    name_tids = defaultdict(set)
    for tid, names in tid_names.items():
        for nm in names:
            name_tids[nm].add(tid)

    accepted, rejected = [], []
    for a, b, rule in pairs:
        key = (min(a, b), max(a, b))
        ev = cooc.get(key, [])
        if rule == "punctuation_variant":
            # digits are part of the identity: "Bush 41" != "Bush 43",
            # "Juror B-29" != "Juror B-37"
            if _digit_key(a) != _digit_key(b):
                rejected.append((a, b, rule, "digits differ (distinct identities)"))
            else:
                accepted.append((a, b, rule,
                                 "identical letters+digits ignoring punctuation"))
        elif rule == "reporting_suffix":
            accepted.append((a, b, rule, "'X Reporting' sign-off artifact"))
        elif rule in ("initial_vs_full", "middle_initial"):
            ini = a if initial_form(a) else (b if initial_form(b) else None)
            full = b if ini == a else a
            if rule == "initial_vs_full" and ini in ambiguous:
                rejected.append((a, b, rule, "ambiguous: initial matches >1 full name"))
            elif not ev:
                rejected.append((a, b, rule, "no shared transcript"))
            else:
                cov = len(set(ev)) / max(1, len(name_tids.get(ini, ())))
                if cov < MIN_INITIAL_COVERAGE:
                    rejected.append((a, b, rule,
                                     f"low coverage {cov:.2f} of the initial "
                                     f"label's {len(name_tids.get(ini, ()))} transcripts"))
                else:
                    accepted.append((a, b, rule,
                                     f"co-labelled in {len(set(ev))}/"
                                     f"{len(name_tids.get(ini, ()))} of the initial "
                                     f"label's transcripts (cov {cov:.2f}): "
                                     + ";".join(sorted(ev)[:5])))
        else:
            rejected.append((a, b, rule, "no rule"))

    uf = UF()
    for n in cache["universe"]:
        uf.find(n)
    for a, b, _r, _e in accepted:
        uf.union(a, b)

    groups = uf.groups()
    # canonical name per group: prefer a full (non-initial, non-artifact) name,
    # then the one with most guest words, then alphabetical.
    canon_of = {}
    group_members = {}
    for root, members in groups.items():
        def score(nm):
            return (0 if (not initial_form(nm) and not nm.endswith(" Reporting")
                          and ":" not in nm) else 1,
                    -index_words.get(nm, 0), nm)
        best = sorted(members, key=score)[0]
        for m in members:
            canon_of[m] = best
        group_members[best] = sorted(members)

    merged_groups = {c: ms for c, ms in group_members.items() if len(ms) > 1}
    rule_hits = Counter(r for _a, _b, r, _e in accepted)
    print(f"[merge] proposals={len(pairs)} accepted={len(accepted)} "
          f"rejected={len(rejected)}")
    print(f"[merge] accepted by rule: {dict(rule_hits)}")
    rej_bucket = Counter(
        ("low coverage" if e.startswith("low coverage") else e.split(":")[0])
        for _a, _b, _r, e in rejected)
    print(f"[merge] rejected by reason: {dict(rej_bucket)}")
    print(f"[merge] multi-name canonical groups: {len(merged_groups)}; "
          f"names absorbed: {sum(len(v)-1 for v in merged_groups.values())}")
    print(f"[merge] ambiguous initial labels refused: {len(ambiguous)}")

    pool_set = set(pool_names)
    touched = {c for c, ms in merged_groups.items() if any(m in pool_set for m in ms)}
    print(f"[merge] canonical groups touching the 1,162 pool: {len(touched)}")

    with open(CANON_MAP, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant_name", "canonical_id", "canonical_name",
                    "in_original_pool", "merge_rule", "merge_evidence",
                    "group_size"])
        ev_by_pair = {(min(a, b), max(a, b)): (r, e) for a, b, r, e in accepted}
        cid = {}
        for i, c in enumerate(sorted(group_members), 1):
            cid[c] = f"C{i:05d}"
        for c in sorted(group_members):
            ms = group_members[c]
            for m in ms:
                if m == c:
                    rule, evid = ("canonical", "")
                else:
                    rule, evid = ev_by_pair.get((min(c, m), max(c, m)),
                                                ("transitive", "merged via group"))
                w.writerow([m, cid[c], c, int(m in pool_set), rule, evid, len(ms)])
    print(f"[merge] wrote {CANON_MAP}")

    with open(os.path.join(OUT_DIR, "canonical_rejected_v2.csv"), "w",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["name_a", "name_b", "rule", "reason"])
        for a, b, r, e in rejected:
            w.writerow([a, b, r, e])

    return canon_of, group_members, cid, ambiguous, rule_hits, len(accepted), len(rejected)


# ---------------------------------------------------------------------------
def step_staff(cache, pool_names):
    """Staff evidence for every name in the merge universe (not just the pool).

    Also re-derives the Phase A pool numbers as a sanity check: the scan uses
    the same rules as staff_crossref.py, so the pool flag count must match.
    """
    staff_ev = cache["staff_ev"]
    with open(STAFF_V2, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["normalized_name", "staff_evidence", "marker",
                    "example_raw_label"])
        for n in sorted(cache["universe"]):
            ev = staff_ev.get(n)
            w.writerow([n, "yes" if ev else "no",
                        ev[1] if ev else "", ev[2] if ev else ""])
    pool_flagged = sum(1 for n in pool_names if n in staff_ev)
    old = 0
    old_path = os.path.join(OUT_DIR, "staff_crossref.csv")
    if os.path.exists(old_path):
        with open(old_path) as f:
            old = sum(1 for r in csv.DictReader(f) if r["staff_evidence"] == "yes")
    print(f"[staff] universe names flagged: {len(staff_ev)}/{len(cache['universe'])}; "
          f"of the 1,162 pool: {pool_flagged} (Phase A said {old})")
    return pool_flagged, old


# ---------------------------------------------------------------------------
def jaccard_contain(a, b):
    if len(a) == 0 or len(b) == 0:
        return 0.0, 0.0
    inter = np.intersect1d(a, b, assume_unique=True).size
    union = len(a) + len(b) - inter
    return inter / union, inter / min(len(a), len(b))


def step3_dedup(cache, canon_of, tid_date, pool_canon):
    """Cluster near-duplicate appearances within each canonical subject."""
    shingles = cache["shingles"]
    stats = cache["stats"]

    # merge variant rows onto the canonical subject, per transcript
    per_canon = defaultdict(dict)   # canon -> tid -> [shingle_arr, words, turns]
    for (name, tid), sh in shingles.items():
        c = canon_of.get(name, name)
        if c not in pool_canon:
            continue
        w, t = stats[(name, tid)]
        slot = per_canon[c].get(tid)
        if slot is None:
            per_canon[c][tid] = [sh, w, t]
        else:
            slot[0] = np.union1d(slot[0], sh)
            slot[1] += w
            slot[2] += t

    rows = []
    n_pairs = 0
    dup_clusters_total = 0
    dup_members_removed = 0
    same_day_multi_prog = 0
    same_day_and_dup = 0
    t0 = time.time()
    out = {}
    for c, tmap in per_canon.items():
        tids = sorted(tmap)
        uf = UF()
        for t in tids:
            uf.find(t)
        for i in range(len(tids)):
            ai = tmap[tids[i]][0]
            for j in range(i + 1, len(tids)):
                bj = tmap[tids[j]][0]
                n_pairs += 1
                mn = min(len(ai), len(bj))
                if mn < MIN_SHINGLES_FOR_JACCARD:
                    if mn > 0 and len(ai) == len(bj) and np.array_equal(ai, bj):
                        uf.union(tids[i], tids[j])
                    continue
                jac, con = jaccard_contain(ai, bj)
                if jac >= JACCARD_DUP or (con >= CONTAIN_DUP
                                          and mn >= MIN_SHINGLES_FOR_CONTAIN):
                    uf.union(tids[i], tids[j])
        clusters = uf.groups()
        # same-day / multi-program flag
        by_date = defaultdict(list)
        for t in tids:
            iso, _q, prog = tid_date.get(t, ("", "missing", ""))
            by_date[iso].append((t, prog))
        sd_flag = {}
        for iso, lst in by_date.items():
            if iso and len(lst) > 1 and len({p for _t, p in lst}) > 1:
                same_day_multi_prog += 1
                for t, _p in lst:
                    sd_flag[t] = True
        cl_id = {}
        for k, (root, members) in enumerate(sorted(clusters.items()), 1):
            for t in members:
                cl_id[t] = k
            if len(members) > 1:
                dup_clusters_total += 1
                dup_members_removed += len(members) - 1
                if any(sd_flag.get(t) for t in members):
                    same_day_and_dup += 1
        for t in tids:
            sh, w, tu = tmap[t]
            iso, q, prog = tid_date.get(t, ("", "missing", ""))
            rows.append([c, t, cl_id[t],
                         sum(1 for x in tids if cl_id[x] == cl_id[t]),
                         iso, q, prog, w, tu, len(sh),
                         int(bool(sd_flag.get(t))),
                         int(w >= SUBST_MIN_WORDS and tu >= SUBST_MIN_TURNS)])
        out[c] = (tmap, cl_id)
    print(f"[dedup] compared {n_pairs} within-subject transcript pairs in "
          f"{time.time()-t0:.0f}s")
    print(f"[dedup] duplicate clusters (size>1): {dup_clusters_total}; "
          f"appearances collapsed away: {dup_members_removed}")
    print(f"[dedup] same-day multi-program date groups: {same_day_multi_prog} "
          f"(of which also text-duplicates: {same_day_and_dup})")

    with open(DEDUP_MAP, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical_name", "transcript_id", "dup_cluster", "cluster_size",
                    "date", "date_quality", "program", "guest_words", "guest_turns",
                    "n_shingles", "same_day_multi_program", "substantive"])
        w.writerows(rows)
    print(f"[dedup] wrote {DEDUP_MAP} ({len(rows)} rows)")
    return out, {"pairs": n_pairs, "dup_clusters": dup_clusters_total,
                 "collapsed": dup_members_removed,
                 "same_day_multi_prog": same_day_multi_prog,
                 "same_day_and_dup": same_day_and_dup}


# ---------------------------------------------------------------------------
def step4_stats(dedup_out, tid_date, cache, canon_of, group_members):
    """Per-canonical deduped counts + fixed-date chronology."""
    import datetime
    raw_counts = cache["raw_counts"]
    rows = []
    for c, (tmap, cl_id) in dedup_out.items():
        tids = sorted(tmap)
        # cluster -> members
        cl = defaultdict(list)
        for t in tids:
            cl[cl_id[t]].append(t)
        n_app = len(tids)
        n_clusters = len(cl)
        subst_raw = sum(1 for t in tids
                        if tmap[t][1] >= SUBST_MIN_WORDS and tmap[t][2] >= SUBST_MIN_TURNS)
        subst_clusters = []
        for k, members in cl.items():
            if any(tmap[t][1] >= SUBST_MIN_WORDS and tmap[t][2] >= SUBST_MIN_TURNS
                   for t in members):
                # representative = earliest dated member (original airing)
                dated = [tid_date.get(t, ("", "", ""))[0] for t in members]
                dated = [d for d in dated if d]
                subst_clusters.append((min(dated) if dated else "", members))
        subst_dedup = len(subst_clusters)
        dts = sorted(d for d, _m in subst_clusters if d)
        n_dates = len(set(dts))
        if len(dts) >= 2:
            a = datetime.date.fromisoformat(dts[0])
            b = datetime.date.fromisoformat(dts[-1])
            span = (b - a).days
        else:
            span = 0
        npr = sum(1 for t in tids if t.startswith("NPR")) / max(1, len(tids))
        words = sum(tmap[t][1] for t in tids)
        progs = {tid_date.get(t, ("", "", ""))[2] for t in tids}
        variants = group_members.get(c, [c])
        rawc = Counter()
        for v in variants:
            rawc.update(raw_counts.get(v, {}))
        # Label used for the Wikipedia query. Prefer a label that spells the
        # name out: the most FREQUENT label of a merged subject is often the
        # initial form ("C. REEVE"), which no encyclopaedia has an article for
        # and which would mark Christopher Reeve as long-tail.
        def _lab_rank(kv):
            lab, n = kv
            nm = M.classify_speaker(lab)[1] or ""
            return (1 if (not nm or initial_form(nm)) else 0, -n, -len(lab))
        top_raw = min(rawc.items(), key=_lab_rank)[0] if rawc else ""
        aff = affiliations_of(rawc)
        rows.append({
            "canonical_name": c,
            "n_variants": len(variants),
            "variants": ";".join(variants),
            "n_appearances": n_app,
            "n_dedup_clusters": n_clusters,
            "subst_appearances_raw": subst_raw,
            "subst_dedup": subst_dedup,
            "n_dates_dedup": n_dates,
            "span_days_dedup": span,
            "first_date": dts[0] if dts else "",
            "last_date": dts[-1] if dts else "",
            "total_guest_words": words,
            "n_programs": len([p for p in progs if p]),
            "npr_share": round(npr, 4),
            "top_raw_label": top_raw,
            "n_affiliations": len(aff),
            "affiliations": " / ".join(a for a, _ in aff.most_common(4)),
            "transcript_ids": ";".join(tids),
        })
    rows.sort(key=lambda r: -r["total_guest_words"])
    with open(CANON_STATS, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[stats] wrote {CANON_STATS} ({len(rows)} canonical subjects)")
    return rows


# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    with open(CACHE_PKL, "rb") as f:
        cache = pickle.load(f)
    print(f"cache loaded: {len(cache['shingles'])} (name,tid) shingle sets, "
          f"scan took {cache['scan_secs']:.0f}s")

    tid_date = {}
    with open(DATES_CSV) as f:
        for row in csv.DictReader(f):
            tid_date[row["transcript_id"]] = (row["date"], row["date_quality"],
                                              row["program"])
    print(f"transcript dates: {len(tid_date)}")

    pool_names = []
    with open(POOL_CSV) as f:
        for row in csv.DictReader(f):
            pool_names.append(row["normalized_name"])

    index_words = {}
    with open(M.INDEX_CSV) as f:
        for row in csv.DictReader(f):
            index_words[row["normalized_name"]] = int(row["total_guest_words"])

    d1 = step1_dates(tid_date)
    staff_flagged, staff_old = step_staff(cache, pool_names)
    canon_of, group_members, cid, ambiguous, rule_hits, n_acc, n_rej = \
        step2_merges(cache, pool_names, index_words)

    pool_canon = {canon_of.get(n, n) for n in pool_names}
    print(f"[merge] 1,162 pool names -> {len(pool_canon)} canonical subjects")

    # Chronology must not use a date the parser distrusts. Two CNN records are
    # dated 3007-2-12 (their URL says 2007-02-12); those are dropped here.
    tid_chrono = {t: (iso if q.startswith("ok") else "", q, prog)
                  for t, (iso, q, prog) in tid_date.items()}

    dedup_out, d3 = step3_dedup(cache, canon_of, tid_chrono, pool_canon)
    rows = step4_stats(dedup_out, tid_chrono, cache, canon_of, group_members)

    import json
    with open(SUMMARY_JSON, "w") as f:
        json.dump({
            "dates": d1,
            "merge": {"proposals": len(cache["pairs"]), "accepted": n_acc,
                      "rejected": n_rej, "by_rule": dict(rule_hits),
                      "ambiguous_initials": len(ambiguous),
                      "pool_names": len(pool_names),
                      "pool_canonical_subjects": len(pool_canon)},
            "dedup": d3,
            "scan": {"records": cache["n_records"],
                     "distinct_labels": cache["n_distinct_labels"],
                     "date_qual": cache["date_qual"],
                     "scan_secs": cache["scan_secs"]},
        }, f, indent=2)
    print(f"wrote {SUMMARY_JSON}")
    print(f"TOTAL {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
