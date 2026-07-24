"""Build the Stage 2 candidate pool CSV from the MediaSum recon index.

Pool definition (mirrors the quality-audit sampling pool):
  - >= 3 individually substantive appearances (>= 300 guest words and >= 5 turns)
  - normalized name has >= 2 tokens (bare surnames are unreliable identities)
  - not in the top 500 guests by total guest words (celebrity/staff head)

Output: results/stage2_candidate_pool.csv, sorted long-tail-first.
Run: uv run python experiments/build_candidate_pool.py
"""

import pandas as pd

INDEX = "data/mediasum_index/guest_index.csv"
INTERVIEWS = "data/mediasum_index/guest_interviews.csv"
RECHECK = "data/mediasum_index/wiki_recheck.csv"
OUT = "results/stage2_candidate_pool.csv"

idx = pd.read_csv(INDEX)
top500 = set(idx.nlargest(500, "total_guest_words")["normalized_name"])

pool = idx[
    (idx["subst_appearances"] >= 3)
    & (idx["normalized_name"].str.split().str.len() >= 2)
    & (~idx["normalized_name"].isin(top500))
].copy()

iv = pd.read_csv(INTERVIEWS)
iv["is_npr"] = iv["transcript_id"].str.startswith("NPR")
npr = iv.groupby("normalized_name")["is_npr"].mean().rename("npr_share")
pool = pool.merge(npr, on="normalized_name", how="left")

recheck = pd.read_csv(RECHECK)[["normalized_name", "page_exists"]]
pool = pool.merge(recheck, on="normalized_name", how="left")

# staff cross-reference: name ever seen with a role marker anywhere in the corpus
staff = pd.read_csv("data/mediasum_index/staff_crossref.csv")
pool = pool.merge(
    staff[["normalized_name", "staff_evidence", "marker"]], on="normalized_name", how="left"
)
pool["staff_evidence"] = pool["staff_evidence"].fillna("no")

# label-quality flags: initial-style names ("A. Gore") fragment identity and skew famous;
# ":"-containing or "... Reporting" names are parsing artifacts
toks = pool["normalized_name"].str.split()
pool["initial_label"] = toks.apply(lambda t: any(len(w.rstrip(".")) < 2 for w in t))
pool["label_artifact"] = pool["normalized_name"].str.contains(":") | pool[
    "normalized_name"
].str.endswith(" Reporting")

# wiki_status: recheck (unbiased, better casing) wins over the original check
def wiki_status(row):
    if row["page_exists"] == "no":
        return "long-tail"
    if row["page_exists"] == "yes":
        return "has-page"
    if row["wiki_page_exists"] == 0:
        return "long-tail(v1)"
    if row["wiki_page_exists"] == 1:
        return "has-page(v1)"
    return "unchecked"

pool["wiki_status"] = pool.apply(wiki_status, axis=1)
pool["clean"] = (
    (pool["staff_evidence"] == "no") & ~pool["initial_label"] & ~pool["label_artifact"]
)
rank = {"long-tail": 0, "long-tail(v1)": 1, "unchecked": 2, "has-page(v1)": 3, "has-page": 4}
pool["_r"] = pool["wiki_status"].map(rank)
pool = pool.sort_values(
    ["clean", "_r", "total_guest_words"], ascending=[False, True, False]
).drop(columns="_r")

cols = [
    "normalized_name", "clean", "staff_evidence", "marker", "initial_label",
    "label_artifact", "n_transcripts", "subst_appearances", "total_guest_words",
    "first_date", "last_date", "span_days", "n_dates", "n_programs", "npr_share",
    "wiki_status", "generic_name_flag", "honorifics", "example_transcript_ids",
]
pool[cols].to_csv(OUT, index=False)

chrono = (pool["span_days"] >= 180) & (pool["n_dates"] >= 3)
clean = pool["clean"]
lt = pool["wiki_status"].str.startswith("long-tail")
checked = pool["wiki_status"] != "unchecked"
print(f"pool size: {len(pool)}")
print(f"clean (no staff evidence, full name, no artifact): {clean.sum()}")
print(f"clean + chronological (span>=180d, >=3 dates): {(clean & chrono).sum()}")
print(f"clean + wiki-checked: {(clean & checked).sum()}; of those long-tail: {(clean & lt).sum()}")
print(f"clean + unchecked: {(clean & ~checked).sum()}")
print(f"clean long-tail + chronological: {(clean & lt & chrono).sum()}")
print(f"clean + npr_share>=0.5: {(clean & (pool['npr_share'] >= 0.5)).sum()}")
