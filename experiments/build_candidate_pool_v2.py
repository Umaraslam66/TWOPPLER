"""Rebuild the Stage 2 candidate pool after Phase B curation (v2).

Successor to build_candidate_pool.py. Same pool definition, but every input
that Phase A got wrong has been repaired first:

  - dates      : tolerant parser (curate_scan_v2.py). Phase A dropped 41.8% of
                 all transcripts because it required a zero-padded month/day.
  - identity   : conservative label-variant merging (curate_pool_v2.py), so a
                 subject split across "C. Reeve" / "Christopher Reeve" counts
                 once, with the evidence recorded.
  - recurrence : near-duplicate detection, so a single interview re-aired on
                 three shows counts as ONE interview.
  - long tail  : Wikipedia checked for every candidate with the raw-label
                 method (wiki_recheck_v2.py), not just a 133-guest subset.

Outputs
  results/stage2_candidate_pool_v2.csv  — every canonical candidate + flags
  results/stage2_shortlist.csv          — ~120 rows for human review,
                                          biased long-tail, full provenance

Run: uv run python experiments/build_candidate_pool_v2.py
"""
import csv
import os
import sys
from collections import Counter, defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402
from curate_pool_v2 import initial_form, particle_only  # noqa: E402

ROOT = M.ROOT
OUT_DIR = M.OUT_DIR
CANON_STATS = os.path.join(OUT_DIR, "canonical_stats_v2.csv")
CANON_MAP = os.path.join(OUT_DIR, "canonical_map_v2.csv")
REJECTED = os.path.join(OUT_DIR, "canonical_rejected_v2.csv")
STAFF_V2 = os.path.join(OUT_DIR, "staff_crossref_v2.csv")
STAFF_SUMMARY = os.path.join(OUT_DIR, "staff_summary_v2.csv")
WIKI_V2 = os.path.join(OUT_DIR, "wiki_recheck_v2.csv")
WIKI_FUZZY = os.path.join(OUT_DIR, "wiki_fuzzy_v2.csv")
DEDUP_MAP = os.path.join(OUT_DIR, "dedup_map_v2.csv")
POOL_V1 = os.path.join(ROOT, "results/stage2_candidate_pool.csv")

OUT_POOL = os.path.join(ROOT, "results/stage2_candidate_pool_v2.csv")
OUT_SHORT = os.path.join(ROOT, "results/stage2_shortlist.csv")

SHORTLIST_N = 120
SHORTLIST_LONGTAIL = 90   # 3:1 long-tail bias, per PREREGISTRATION_AMENDMENT_1 A5
MIN_SUBST_DEDUP = 3
MIN_SPAN_DAYS = 180
MIN_DATES = 3


def main():
    stats = pd.read_csv(CANON_STATS)
    cmap = pd.read_csv(CANON_MAP)
    staff = pd.read_csv(STAFF_V2)
    ssum = pd.read_csv(STAFF_SUMMARY)
    wiki = pd.read_csv(WIKI_V2)
    dedup = pd.read_csv(DEDUP_MAP)
    idx = pd.read_csv(M.INDEX_CSV)

    # ---- top-500 celebrity/staff head cutoff, re-applied to MERGED totals ----
    top500_cut = idx.nlargest(500, "total_guest_words")["total_guest_words"].min()

    # ---- staff evidence: flagged if ANY variant of the subject is flagged ----
    staff_yes = set(staff.loc[staff["staff_evidence"] == "yes", "normalized_name"])
    var_by_canon = cmap.groupby("canonical_name")["variant_name"].apply(list).to_dict()
    rule_by_canon = (cmap[cmap["merge_rule"].isin(
        ["initial_vs_full", "middle_initial", "punctuation_variant",
         "reporting_suffix", "transitive"])]
        .groupby("canonical_name")["merge_rule"].apply(lambda s: ";".join(sorted(set(s))))
        .to_dict())
    _ev = cmap[cmap["merge_evidence"].notna() & (cmap["merge_evidence"] != "")]
    evid_by_canon = (_ev.groupby("canonical_name")["merge_evidence"]
                     .apply(lambda s: " | ".join(sorted(set(map(str, s)))[:3]))
                     .to_dict())
    cid_by_canon = cmap.drop_duplicates("canonical_name").set_index(
        "canonical_name")["canonical_id"].to_dict()

    # ---- names whose initial label matched more than one full name ----
    rej = pd.read_csv(REJECTED)
    ambiguous = set(
        pd.concat([
            rej.loc[rej["reason"].str.startswith("ambiguous"), "name_a"],
            rej.loc[rej["reason"].str.startswith("ambiguous"), "name_b"],
        ]))
    ambiguous = {a for a in ambiguous if initial_form(str(a))}

    s = stats.copy()
    s["canonical_id"] = s["canonical_name"].map(cid_by_canon)
    s["staff_evidence"] = s.apply(
        lambda r: "yes" if any(v in staff_yes for v in str(r["variants"]).split(";"))
        else "no", axis=1)
    marker_of = dict(zip(staff["normalized_name"], staff["marker"].fillna("")))
    s["staff_marker"] = s.apply(
        lambda r: ";".join(sorted({
            marker_of.get(v, "")
            for v in str(r["variants"]).split(";") if v in staff_yes})), axis=1)
    # second staff filter: what the transcript summaries call the person
    sum_verdict = dict(zip(ssum["canonical_name"], ssum["summary_staff"]))
    sum_example = dict(zip(ssum["canonical_name"], ssum["example_summary"].fillna("")))
    s["summary_staff"] = s["canonical_name"].map(sum_verdict).fillna("no")
    s["summary_evidence"] = s["canonical_name"].map(sum_example).fillna("")

    s["initial_label"] = s["canonical_name"].map(initial_form)
    # a ":" anywhere in the group means the speaker label was mis-parsed, even
    # if the canonical form we picked happens to look clean ("Question Trump")
    def _artifact(r):
        for v in str(r["variants"]).split(";"):
            if ":" in v:
                return True
        n = r["canonical_name"]
        return ":" in n or n.endswith(" Reporting")
    s["label_artifact"] = s.apply(_artifact, axis=1)
    s["ambiguous_identity"] = s["canonical_name"].isin(ambiguous)
    s["particle_surname"] = s["canonical_name"].map(particle_only)
    s["generic_name_flag"] = s["canonical_name"].map(M.generic_name_flag)
    s["n_tokens"] = s["canonical_name"].str.split().str.len()
    s["over_top500_head"] = s["total_guest_words"] > top500_cut
    s["merge_rules"] = s["canonical_name"].map(rule_by_canon).fillna("")
    s["merge_evidence"] = s["canonical_name"].map(evid_by_canon).fillna("")

    # ---- wiki status (raw-label method for all; v1 kept as a cross-check) ----
    wmap = wiki.set_index("normalized_name")
    def wiki_status(name):
        if name not in wmap.index:
            return "unchecked"
        pe = wmap.at[name, "page_exists"]
        if pe == "no":
            return "long-tail"
        if pe == "yes":
            return "has-page"
        return "unchecked"
    s["wiki_status"] = s["canonical_name"].map(wiki_status)

    # exact-title misses that are really spelling variants of a real article
    # ("Karen Deyoung" -> "Karen DeYoung"). Only titles the search pass could
    # not match stay long-tail, which is the pre-registered bias target.
    s["closest_wikipedia_title"] = ""
    s["wiki_similarity"] = ""
    if os.path.exists(WIKI_FUZZY):
        fz = pd.read_csv(WIKI_FUZZY)
        fstat = dict(zip(fz["canonical_name"], fz["fuzzy_status"]))
        ftitle = dict(zip(fz["canonical_name"], fz["closest_wikipedia_title"]))
        fsim = dict(zip(fz["canonical_name"], fz["similarity"]))
        s["closest_wikipedia_title"] = s["canonical_name"].map(ftitle).fillna("")
        s["wiki_similarity"] = s["canonical_name"].map(fsim).fillna("")
        s["wiki_status"] = [
            ("has-page-fuzzy" if fstat.get(n) == "has-page-fuzzy" else st)
            for n, st in zip(s["canonical_name"], s["wiki_status"])]
    else:
        print("WARNING: no wiki_fuzzy_v2.csv — long-tail counts are the "
              "exact-title numbers and are inflated ~12% (see report).")

    s["clean"] = (
        (s["staff_evidence"] == "no") & (s["summary_staff"] != "staff")
        & ~s["initial_label"] & ~s["label_artifact"] & ~s["ambiguous_identity"]
        & (s["n_tokens"] >= 2) & ~s["over_top500_head"]
    )
    s["chronological"] = (s["span_days_dedup"] >= MIN_SPAN_DAYS) & \
                         (s["n_dates_dedup"] >= MIN_DATES)
    s["recurring_dedup"] = s["subst_dedup"] >= MIN_SUBST_DEDUP
    s["qualifies"] = s["clean"] & s["chronological"] & s["recurring_dedup"]
    s["long_tail"] = s["wiki_status"] == "long-tail"

    # ---- per-subject transcript provenance ----
    dedup["prov"] = (dedup["transcript_id"] + "|" + dedup["date"].fillna("")
                     + "|" + dedup["program"].fillna("") + "|cl"
                     + dedup["dup_cluster"].astype(str)
                     + dedup["substantive"].map({1: "|S", 0: "|-"}))
    prov = dedup.sort_values(["canonical_name", "date"]).groupby(
        "canonical_name")["prov"].apply(lambda x: ";".join(x)).to_dict()
    _g = dedup.groupby("canonical_name")
    collapsed = (_g.size() - _g["dup_cluster"].nunique()).to_dict()
    sdmp = dedup.groupby("canonical_name")["same_day_multi_program"].sum().to_dict()
    s["transcripts"] = s["canonical_name"].map(prov).fillna("")
    s["appearances_collapsed"] = s["canonical_name"].map(collapsed).fillna(0).astype(int)
    s["same_day_multi_program"] = s["canonical_name"].map(sdmp).fillna(0).astype(int)

    # ---- note ----
    def note(r):
        bits = []
        if r["staff_evidence"] == "yes":
            bits.append(f"FLAG staff label evidence ({r['staff_marker']})")
        if r["summary_staff"] == "staff":
            bits.append("FLAG summaries describe them as network staff")
        if r["summary_staff"] == "review":
            bits.append("CHECK summaries use a role word (outside journalist "
                        "or recurring pundit?)")
        if r["ambiguous_identity"]:
            bits.append("FLAG initial label matches >1 full name")
        if r["initial_label"]:
            bits.append("FLAG initial-only label, no full-name evidence found")
        if r["label_artifact"]:
            bits.append("FLAG parsing artifact in label")
        if r["over_top500_head"]:
            bits.append("FLAG celebrity/staff head after merge")
        if r["particle_surname"]:
            bits.append("CHECK particle+surname label (effectively a surname)")
        if r["generic_name_flag"]:
            bits.append("CHECK common first+last name, collision risk")
        if r["n_variants"] > 1:
            bits.append(f"merged {int(r['n_variants'])} label variants "
                        f"({r['merge_rules']})")
        if r["appearances_collapsed"] > 0:
            bits.append(f"{int(r['appearances_collapsed'])} re-airings collapsed")
        if r["subst_dedup"] >= 8 and r["n_programs"] <= 2:
            bits.append(f"CHECK {int(r['subst_dedup'])} interviews across only "
                        f"{int(r['n_programs'])} program(s) — recurring panelist "
                        "rather than interview subject?")
        if r["npr_share"] < 0.34:
            bits.append("CNN-dominated (thinner turns, more re-airing)")
        if not bits:
            bits.append("clean: no staff evidence, full name, no duplicate inflation")
        return "; ".join(bits)
    s["note"] = s.apply(note, axis=1)

    cols = ["canonical_id", "canonical_name", "clean", "qualifies", "wiki_status",
            "subst_dedup", "subst_appearances_raw", "n_appearances",
            "n_dedup_clusters", "appearances_collapsed", "same_day_multi_program",
            "span_days_dedup", "n_dates_dedup", "first_date", "last_date",
            "total_guest_words", "n_programs", "npr_share", "n_variants",
            "variants", "merge_rules", "merge_evidence", "staff_evidence",
            "staff_marker", "summary_staff", "summary_evidence",
            "closest_wikipedia_title", "wiki_similarity",
            "n_affiliations", "affiliations", "initial_label", "label_artifact",
            "ambiguous_identity", "particle_surname", "generic_name_flag",
            "over_top500_head", "top_raw_label", "note", "transcripts"]
    s.sort_values(["qualifies", "long_tail", "subst_dedup", "total_guest_words"],
                  ascending=[False, False, False, False])[cols].to_csv(
                      OUT_POOL, index=False)

    # ---------------- shortlist: biased long-tail ----------------
    q = s[s["qualifies"]].copy()
    q["risk"] = (q["particle_surname"].astype(int)
                 + q["generic_name_flag"].astype(int)
                 + (q["summary_staff"] == "review").astype(int)
                 + ((q["subst_dedup"] >= 8) & (q["n_programs"] <= 2)).astype(int)
                 + (q["npr_share"] < 0.34).astype(int))
    q = q.sort_values(["risk", "subst_dedup", "span_days_dedup",
                       "total_guest_words"],
                      ascending=[True, False, False, False])
    lt = q[q["long_tail"]].head(SHORTLIST_LONGTAIL)
    rest = q[~q["long_tail"]].head(SHORTLIST_N - len(lt))
    short = pd.concat([lt, rest]).head(SHORTLIST_N)
    short_cols = ["canonical_id", "canonical_name", "wiki_status", "subst_dedup",
                  "n_appearances", "appearances_collapsed", "span_days_dedup",
                  "n_dates_dedup", "first_date", "last_date", "npr_share",
                  "n_programs", "total_guest_words", "n_variants", "merge_rules",
                  "merge_evidence", "top_raw_label", "n_affiliations",
                  "affiliations", "summary_staff", "note", "transcripts"]
    short[short_cols].to_csv(OUT_SHORT, index=False)

    # ---------------- report numbers ----------------
    v1 = pd.read_csv(POOL_V1)
    print("=" * 70)
    print(f"top-500 head cutoff (guest words): {top500_cut}")
    print(f"v1 pool rows: {len(v1)}  ->  v2 canonical subjects: {len(s)}")
    print(f"v1 clean: {int(v1['clean'].sum())}  ->  v2 clean: {int(s['clean'].sum())}")
    print(f"v2 clean & >= {MIN_SUBST_DEDUP} DEDUPED substantive: "
          f"{int((s['clean'] & s['recurring_dedup']).sum())}")
    print(f"v2 clean & chronological (>= {MIN_SPAN_DAYS}d span, >= {MIN_DATES} "
          f"dedup dates, FIXED dates): {int((s['clean'] & s['chronological']).sum())}")
    print(f"v2 QUALIFYING (clean + deduped recurrence + chronology): "
          f"{int(s['qualifies'].sum())}")
    print(f"   of those long-tail: {int((s['qualifies'] & s['long_tail']).sum())}")
    print(f"   of those has-page : "
          f"{int((s['qualifies'] & (s['wiki_status']=='has-page')).sum())}")
    print(f"   of those has-page-fuzzy (spelling-variant article found): "
          f"{int((s['qualifies'] & (s['wiki_status']=='has-page-fuzzy')).sum())}")
    print(f"   of those unchecked: "
          f"{int((s['qualifies'] & (s['wiki_status']=='unchecked')).sum())}")
    print(f"shortlist rows: {len(short)} "
          f"(long-tail {int(short['long_tail'].sum())})")
    print(f"wrote {OUT_POOL}")
    print(f"wrote {OUT_SHORT}")
    return s, short


if __name__ == "__main__":
    main()
