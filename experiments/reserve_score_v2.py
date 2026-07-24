"""Score the staff-filter reserve from extracted corpus evidence.

Reads _reserve_evidence_v2.json (from reserve_evidence_v2.py) and
writes:
  results/staff_reserve_dossiers.csv   one row per reserve subject
  results/staff_reserve_spotcheck.md   20-subject human spot-check sheet

Conservative by construction: any strong staff signal blocks RE-ADMIT.
CPU only, no network, no LLM.

Run: uv run python experiments/reserve_score_v2.py
"""
import csv
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "data/mediasum_index/_reserve_evidence_v2.json")
OUT_CSV = os.path.join(ROOT, "results/staff_reserve_dossiers.csv")
OUT_MD = os.path.join(ROOT, "results/staff_reserve_spotcheck.md")

sys.path.insert(0, os.path.join(ROOT, "experiments"))

# ---------------------------------------------------------------- vocabularies
NET = r"(?:NPR|CNN)"
ROLE_WORDS = (r"correspondent|reporter|host|anchor|analyst|commentator|"
              r"contributor|producer|editor|humorist|critic|columnist|byline")
ROLE = rf"(?:{ROLE_WORDS})"

OUTLETS = [
    r"New York Times", r"N\.?Y\.? Times", r"Washington Post", r"Los Angeles Times",
    r"L\.?A\.? Times", r"Wall Street Journal", r"USA Today", r"Chicago Tribune",
    r"Boston Globe", r"Miami Herald", r"Dallas Morning News", r"Houston Chronicle",
    r"Philadelphia Inquirer", r"Baltimore Sun", r"Star Tribune", r"Seattle Times",
    r"Denver Post", r"San Francisco Chronicle", r"Detroit Free Press", r"Newsday",
    r"New York Post", r"Financial Times", r"The Guardian", r"The Economist",
    r"Time Magazine", r'"TIME"', r"'TIME'", r"Newsweek", r"The Atlantic",
    r"New Yorker", r"Harper's", r"Rolling Stone", r"Vanity Fair", r"Esquire",
    r"Wired", r"Forbes", r"Fortune", r"Bloomberg", r"Reuters",
    r"Associated Press", r"Politico", r"The Hill", r"Roll Call", r"McClatchy",
    r"ProPublica", r"Slate", r"Salon", r"Vox", r"BuzzFeed", r"Huffington Post",
    r"HuffPost", r"Daily Beast", r"National Review", r"The Nation",
    r"Mother Jones", r"Foreign Policy", r"Foreign Affairs",
    r"Sports Illustrated", r"ESPN", r"Yahoo", r"Axios", r"Al Jazeera", r"BBC",
    r"Sky News", r"ABC News", r"CBS News", r"NBC News", r"Fox News", r"MSNBC",
    r"PBS", r"Univision", r"Telemundo", r"Bloomberg News", r"Christian Science Monitor",
    r"Village Voice", r"Texas Tribune", r"Marketplace", r"Al-?Monitor",
    r"Wired Magazine", r"Variety", r"Billboard", r"Hollywood Reporter",
    r"Entertainment Weekly", r"People Magazine", r"US News", r"U\.S\. News",
    r"Bleacher Report", r"The Athletic", r"Deadspin", r"Grantland",
]
OUTLET_RE = re.compile(r"\b(?:" + "|".join(OUTLETS) + r")\b", re.I)

ORG_WORDS = (r"universit(?:y|ies)|college|institute|institution|"
             r"center|centre|foundation|school|academy|society|association|"
             r"council|museum|hospital|laborator|department|ministry|agency|"
             r"bureau chief|company|corporation|magazine|newspaper|journal|"
             r"tribune|herald|gazette|chronicle|observer|quarterly|"
             r"think tank|law firm")
ORG_RE = re.compile(rf"\b(?:{ORG_WORDS})\b", re.I)

TITLE_WORDS = (r"professor|author|co-?author|director|president|founder|"
               r"co-?founder|senior fellow|fellow|chairman|chairwoman|chair|"
               r"dean|curator|economist|historian|scientist|researcher|"
               r"attorney|lawyer|physician|surgeon|psychologist|psychiatrist|"
               r"ambassador|senator|congressman|congresswoman|representative|"
               r"governor|mayor|secretary|general counsel|chief executive|"
               r"C\.?E\.?O\.?|executive director|vice president|spokesman|"
               r"spokeswoman|coach|novelist|playwright|filmmaker|musician|"
               r"artist|activist|astronaut|engineer|analyst at|analyst with|"
               r"staff writer|columnist for|writer for|reporter for|"
               r"reporter at|correspondent for|correspondent at")
TITLE_RE = re.compile(rf"\b(?:{TITLE_WORDS})\b", re.I)

# public-radio member stations / network-adjacent producers: the hand audit
# treated a Capital Public Radio reporter (Emily Green) as staff, so these are
# never auto-re-admitted
PUBRADIO_RE = re.compile(
    r"\b(?:public radio|public media|member station|youth radio|"
    r"american public media|minnesota public radio|marketplace|"
    r"public radio international|PRI|APM|"
    r"W(?:NYC|BUR|AMU|BEZ|FCR|MFE|GBH|HYY|NPR|UNC|FAE|ESA|USF|LRN|DET|BFO|"
    r"YPR|VTF|KSU|UWM|CAI|SHU|BAA|UOL|MOT|BHM|JCT)|"
    r"K(?:QED|PCC|UOW|JZZ|PBS|ERA|UT|WMU|ALW|CRW|BIA|UNM|UNC|OSU|PLU|UOW))\b",
    re.I)
OTHER_NETWORK_RE = re.compile(
    r"\b(?:ABC News|CBS News|NBC News|Fox News|MSNBC|PBS|BBC|ESPN|"
    r"Al Jazeera|Sky News|Univision|Telemundo|HBO|Bloomberg TV)\b", re.I)

STAFF_ROLE_MARKER = re.compile(
    r"\b(HOST|ANCHOR|CORRESPONDENT|BYLINE|REPORTER|COMMENTATOR)\b", re.I)
REPORTING_RE = re.compile(r"\breporting\b", re.I)
NET_RE = re.compile(r"\b(NPR|CNN)\b")

PAREN_RE = re.compile(r"\(([^)]*)\)|\[([^\]]*)\]")


# ------------------------------------------------------------ label classifier
def classify_label(raw):
    """-> (side, weight, reason) or None.  side in {'staff','guest'}."""
    up = raw.upper()
    # affiliation text = everything after the first comma + parenthetical text
    aff = ""
    if "," in raw:
        aff += " " + raw.split(",", 1)[1]
    for m in PAREN_RE.finditer(raw):
        aff += " " + (m.group(1) or m.group(2) or "")
    aff = aff.strip()
    aff_up = aff.upper()

    has_net = bool(NET_RE.search(up))
    rm = STAFF_ROLE_MARKER.search(up)
    role = rm.group(1).upper() if rm else None
    aff_no_role = STAFF_ROLE_MARKER.sub(" ", aff_up)
    aff_no_role = re.sub(r"[^A-Z0-9']+", " ", aff_no_role).strip()
    has_outlet = bool(OUTLET_RE.search(aff) or ORG_RE.search(aff)
                      or TITLE_RE.search(aff))

    if has_net:
        return ("staff", 3, f"network-owned speaker label ({role or 'NPR/CNN'})")
    if role and (has_outlet or len(aff_no_role.split()) >= 2):
        if role in ("HOST", "ANCHOR"):
            return ("guest", 2, f"{role.lower()} of an outside programme/outlet")
        return ("guest", 3, f"outside-outlet {role.lower()} label")
    if role:
        if role in ("HOST", "ANCHOR", "BYLINE"):
            return ("staff", 3, f"bare '{role}' label (network convention)")
        if role == "COMMENTATOR":
            return ("staff", 1, "bare 'COMMENTATOR' label")
        return ("staff", 2, f"bare '{role}' label, no affiliation")
    if REPORTING_RE.search(raw):
        return ("staff", 2, "'reporting' sign-off label")
    if aff_no_role and (has_outlet or len(aff_no_role.split()) >= 1):
        w = 3 if has_outlet else 2
        return ("guest", w, "speaker label carries an outside affiliation/title")
    return None


# ------------------------------------------------------------ quote classifier
def build_quote_patterns(name_alt):
    n = name_alt
    staff_strong = [
        ("network_possessive", re.compile(rf"\b{NET}'s\s+(?:\w+\s+){{0,2}}(?:{n})\b")),
        ("byline_signoff", re.compile(rf"\b(?:{n})\s*,\s*{NET}\s+News\b", re.I)),
        ("name_comma_network", re.compile(rf"\b(?:{n})\s*,\s*{NET}\b")),
        ("network_role_name", re.compile(
            rf"\b{NET}\s+(?:\w+\s+){{0,3}}{ROLE}\s+(?:{n})\b", re.I)),
        ("our_role_name", re.compile(
            rf"\bour\s+(?:\w+\s+){{0,2}}{ROLE}[,]?\s+(?:{n})\b", re.I)),
        ("name_of_network", re.compile(
            rf"\b(?:{n})\s*,?\s+(?:of|from|with|at)\s+{NET}\b")),
    ]
    staff_med = [
        ("name_reports", re.compile(
            rf"\b(?:{n})\s+(?:reports|reported|reporting|has\s+(?:this|the|more|our))\b",
            re.I)),
        ("name_report_noun", re.compile(rf"\b(?:{n})'s\s+report\b", re.I)),
        ("as_name_reports", re.compile(rf"\bas\s+(?:{n})\s+report", re.I)),
    ]
    staff_weak = [
        ("bare_role_name", re.compile(rf"\b{ROLE}\s+(?:{n})\b", re.I)),
    ]
    guest_strong = [
        ("outlet_near_name", re.compile(
            rf"(?:\b(?:{n})\b[^.]{{0,90}}?(?:" + "|".join(OUTLETS) + r")\b"
            rf"|\b(?:" + "|".join(OUTLETS) + rf")\b[^.]{{0,90}}?\b(?:{n})\b)", re.I)),
        ("author_of", re.compile(
            rf"(?:\bauthor(?:ed)?\s+of\b[^.]{{0,90}}?\b(?:{n})\b"
            rf"|\b(?:{n})\b[^.]{{0,90}}?\bauthor(?:ed)?\s+of\b"
            rf"|\b(?:{n})'s\s+(?:new\s+|latest\s+)?book\b"
            rf"|\b(?:{n})\b[^.]{{0,60}}?\bwrote\s+(?:the\s+|a\s+)?book\b)", re.I)),
        ("title_near_name", re.compile(
            rf"(?:\b(?:{n})\b[^.]{{0,70}}?\b(?:{TITLE_WORDS})\b"
            rf"|\b(?:{TITLE_WORDS})\b[^.]{{0,70}}?\b(?:{n})\b)", re.I)),
        ("org_near_name", re.compile(
            rf"(?:\b(?:{n})\b[^.]{{0,70}}?\b(?:{ORG_WORDS})\b"
            rf"|\b(?:{ORG_WORDS})\b[^.]{{0,70}}?\b(?:{n})\b)", re.I)),
    ]
    guest_med = [
        ("joins_us", re.compile(
            rf"(?:\b(?:{n})\s+(?:joins|joined|is\s+here|was\s+here|is\s+with\s+us)\b"
            rf"|\bjoin(?:s|ed)?\s+(?:us|me)\b[^.]{{0,60}}?\b(?:{n})\b)", re.I)),
        ("host_talks_to", re.compile(
            rf"\b(?:talks?|talked|speaks?|spoke|sat\s+down|sits\s+down|"
            rf"called|asked|interviewed|welcomes?|welcomed)\s+"
            rf"(?:to|with|down\s+with)?\s*(?:[^,.]{{0,40}}\s+)?\b(?:{n})\b", re.I)),
        ("name_tells_us", re.compile(
            rf"\b(?:{n})\s+(?:tells|told|explains|explained|discusses|"
            rf"describes|argues|says\s+that)\b", re.I)),
        ("thanks_for_joining", re.compile(
            rf"\b(?:{n})\b[^.]{{0,50}}?\b(?:thanks?\s+for\s+(?:joining|being|"
            rf"talking|coming)|thank\s+you\s+for\s+(?:joining|being))\b", re.I)),
    ]
    name_rx = re.compile(rf"\b(?:{n})\b", re.I)
    return staff_strong, staff_med, staff_weak, guest_strong, guest_med, name_rx


OTHER_NET = re.compile(r"\b(?:fox|msnbc|abc|cbs|nbc|pbs|hbo|bbc|espn|"
                       r"comedy central|daily show|bloomberg|al jazeera)\b", re.I)
INTERVIEW_VERB = re.compile(
    r"\s*(?:talks?|talked|speaks?|spoke|sits?\s+down|sat\s+down|interviews?|"
    r"interviewed|asks?)\s+(?:to|with|down\s+with)\s+(.{0,80})", re.I | re.S)


def interview_direction(text, name_rx):
    """MediaSum summaries write both 'HOST talks with GUEST' and 'GUEST talks
    with HOST'. Decide which side the subject is on, or None."""
    for m in name_rx.finditer(text):
        pre = text[max(0, m.start() - 45):m.start()]
        post = text[m.end():m.end() + 100]
        if re.search(r"\b(?:guest\s+)?host,?\s*$", pre, re.I) and \
                not OUTLET_RE.search(pre) and not OTHER_NET.search(pre):
            return "staff"
        m2 = INTERVIEW_VERB.match(post)
        if m2:
            obj = m2.group(1)
            if re.search(rf"{NET}'s|\bhost\b|\banchor\b|"
                         rf"\bweekend edition\b|\bmorning edition\b", obj, re.I):
                return "guest"     # the other side is the network person
            return "staff"         # the subject is doing the interviewing
    return None


def classify_quote(text, pats):
    (staff_strong, staff_med, staff_weak, guest_strong, guest_med,
     name_rx) = pats
    for k, rx in staff_strong:
        if rx.search(text):
            return ("staff", 3, k)
    direction = interview_direction(text, name_rx)
    if direction == "staff":
        return ("staff", 3, "acts as the interviewer/host in this summary")
    for k, rx in guest_strong:
        if rx.search(text):
            return ("guest", 3, k)
    if direction == "guest":
        return ("guest", 2, "interviewed by the network host")
    for k, rx in staff_med:
        if rx.search(text):
            return ("staff", 2, k)
    for k, rx in guest_med:
        if rx.search(text):
            return ("guest", 2, k)
    for k, rx in staff_weak:
        if rx.search(text):
            return ("staff", 1, k)
    return (None, 0, "")


# ------------------------------------------------------------------- scoring
def score_subject(name, v, name_alt):
    pats = build_quote_patterns(name_alt)
    guest, staff, excl = [], [], []

    for lb, info in v["labels"].items():
        c = classify_label(lb)
        tids = ";".join(info["tids"][:3])
        trig = None
        up = lb.upper()
        if STAFF_ROLE_MARKER.search(up):
            trig = STAFF_ROLE_MARKER.search(up).group(1)
        elif REPORTING_RE.search(lb):
            trig = "REPORTING"
        elif "," in lb and NET_RE.search(lb.split(",", 1)[1].upper()):
            trig = NET_RE.search(lb.split(",", 1)[1].upper()).group(1)
        if trig:
            excl.append({"quote": lb, "n": info["n"], "tids": tids,
                         "marker": trig})
        if c is None:
            continue
        side, w, reason = c
        item = {"kind": "label", "quote": lb, "w": w, "reason": reason,
                "n": info["n"], "tids": tids}
        (guest if side == "guest" else staff).append(item)

    for tid, q in v["summary_quotes"]:
        side, w, k = classify_quote(q, pats)
        if side is None:
            continue
        item = {"kind": "summary", "quote": q, "w": w, "reason": k, "n": 1,
                "tids": tid}
        (guest if side == "guest" else staff).append(item)

    for tid, who, q in v["utt_quotes"]:
        side, w, k = classify_quote(q, pats)
        # a sign-off inside the subject's OWN turn is decisive
        if side == "staff" and w >= 3:
            k = k + " (self sign-off)" if name.lower() in who.lower() else k
        if side is None:
            continue
        item = {"kind": f"utterance[{who}]", "quote": q, "w": w, "reason": k,
                "n": 1, "tids": tid}
        (guest if side == "guest" else staff).append(item)

    # de-duplicate near-identical quotes
    def dedup(items):
        seen, out = set(), []
        for it in sorted(items, key=lambda x: (-x["w"], -x["n"])):
            key = re.sub(r"[^a-z0-9]+", "", it["quote"].lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    guest, staff = dedup(guest), dedup(staff)
    excl = sorted(excl, key=lambda x: -x["n"])

    gs = sum(1 for i in guest if i["w"] == 3)
    gm = sum(1 for i in guest if i["w"] == 2)
    ss = sum(1 for i in staff if i["w"] == 3)
    sm = sum(1 for i in staff if i["w"] == 2)
    sw = sum(1 for i in staff if i["w"] == 1)
    G = 3 * min(gs, 4) + 2 * min(gm, 4)
    S = 3 * min(ss, 4) + 2 * min(sm, 4) + 1 * min(sw, 4)

    # network-adjacent affiliations seen anywhere in this subject's evidence
    # only the subject's own speaker labels — summary text mentions other
    # people's outlets and is far too noisy for an affiliation flag
    all_text = " | ".join([i["quote"] for i in guest + staff
                           if i["kind"] == "label"]
                          + [e["quote"] for e in excl])
    pubradio = bool(PUBRADIO_RE.search(all_text))
    othernet = bool(OTHER_NETWORK_RE.search(all_text))

    if ss == 0 and gs >= 2 and G >= 2 * S and (sm + sw) <= 3 and not pubradio:
        rec = "RE-ADMIT"
    elif ss >= 2 and ss >= gs:
        rec = "KEEP-EXCLUDED"
    elif ss >= 1 and gs == 0:
        rec = "KEEP-EXCLUDED"
    elif ss == 0 and sm >= 2 and gs == 0:
        rec = "KEEP-EXCLUDED"
    else:
        rec = "AMBIGUOUS"

    flags = []
    if pubradio:
        flags.append("public-radio/member-station affiliation somewhere in "
                     "the evidence — treat as network-adjacent")
    if othernet:
        flags.append("staff of another broadcaster (ABC/CBS/NBC/Fox/BBC/ESPN "
                     "etc.) — outside NPR-CNN, but still a media professional")
    return {"guest": guest, "staff": staff, "exclusion": excl,
            "gs": gs, "gm": gm, "ss": ss, "sm": sm, "sw": sw,
            "G": G, "S": S, "rec": rec, "flags": flags,
            "pubradio": pubradio, "othernet": othernet}


def main():
    d = json.load(open(EV))
    S = d["subjects"]
    import pandas as pd
    cmap = pd.read_csv(os.path.join(ROOT,
                                    "data/mediasum_index/canonical_map_v2.csv"))
    var_by_canon = defaultdict(set)
    for vn, cn in zip(cmap["variant_name"], cmap["canonical_name"]):
        var_by_canon[cn].add(str(vn))

    results = {}
    for name, v in S.items():
        forms = sorted({f for f in var_by_canon[name] | {name}
                        if len(f.split()) >= 2}, key=len, reverse=True)
        alt = "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in forms)
        results[name] = score_subject(name, v, alt)

    # --------------------------------------------------------------- CSV
    rows = []
    for name, v in S.items():
        if not v["in_reserve"]:
            continue
        r = results[name]
        tg = r["guest"][0] if r["guest"] else None
        ts = r["staff"][0] if r["staff"] else None
        rows.append({
            "canonical_name": name,
            "long_tail": int(v["long_tail"]),
            "wiki_status": v["wiki_status"],
            "recommendation": r["rec"],
            "n_guest_quotes": len(r["guest"]),
            "n_staff_quotes": len(r["staff"]),
            "guest_strong": r["gs"], "guest_medium": r["gm"],
            "staff_strong": r["ss"], "staff_medium": r["sm"],
            "staff_weak": r["sw"],
            "guest_score": r["G"], "staff_score": r["S"],
            "flag_public_radio": int(r["pubradio"]),
            "flag_other_network": int(r["othernet"]),
            "exclusion_trigger_label": r["exclusion"][0]["quote"] if r["exclusion"] else "",
            "exclusion_marker": v["staff_marker"],
            "summary_filter_verdict": v["summary_staff"],
            "top_guest_quote": (tg["quote"] if tg else ""),
            "top_guest_source": (f"{tg['kind']}:{tg['tids']}" if tg else ""),
            "top_staff_quote": (ts["quote"] if ts else ""),
            "top_staff_source": (f"{ts['kind']}:{ts['tids']}" if ts else ""),
            "subst_dedup": v["subst_dedup"],
            "n_dates_dedup": v["n_dates_dedup"],
            "span_days_dedup": v["span_days_dedup"],
            "npr_share": round(v["npr_share"], 2),
            "n_programs": v["n_programs"],
            "first_date": v["first_date"], "last_date": v["last_date"],
            "transcript_ids": ";".join(v["own_tids"][:25]),
        })
    order = {"RE-ADMIT": 0, "AMBIGUOUS": 1, "KEEP-EXCLUDED": 2}
    rows.sort(key=lambda r: (order[r["recommendation"]], -r["long_tail"],
                             -r["guest_score"]))
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT_CSV} ({len(rows)} rows)")

    # ------------------------------------------------------------- spot check
    ANCHORS = ["Brian Bennett", "Dexter Filkins", "Alex Kellogg", "Brian Unger"]
    reserve = [n for n, v in S.items() if v["in_reserve"] and n not in ANCHORS]
    lt = sorted([n for n in reserve if S[n]["long_tail"]])
    nlt = sorted([n for n in reserve if not S[n]["long_tail"]])
    rng = random.Random(42)
    pick = sorted(rng.sample(lt, 10)) + sorted(rng.sample(nlt, 10))

    cnt = Counter(r["recommendation"] for r in rows)
    cnt_lt = Counter(r["recommendation"] for r in rows if r["long_tail"])

    def block(name, out):
        v, r = S[name], results[name]
        out.append(f"### {name}")
        out.append("")
        out.append(f"- long-tail: **{'yes' if v['long_tail'] else 'no'}** "
                   f"({v['wiki_status']}) | interviews (dedup): "
                   f"{v['subst_dedup']} on {v['n_dates_dedup']} dates | span "
                   f"{v['span_days_dedup']}d ({v['first_date']} to "
                   f"{v['last_date']}) | NPR share {v['npr_share']:.2f} | "
                   f"{v['n_programs']} programmes")
        out.append(f"- auto-recommendation: **{r['rec']}** — guest evidence: "
                   f"{r['gs']} strong, {r['gm']} medium (capped score "
                   f"{r['G']}); staff evidence: {r['ss']} strong, {r['sm']} "
                   f"medium, {r['sw']} weak (capped score {r['S']})")
        out.append(f"- label filter fired on marker: `{v['staff_marker']}`; "
                   f"summary filter said: `{v['summary_staff']}`")
        for fl in r["flags"]:
            out.append(f"- **caution:** {fl}")
        out.append("")
        out.append("**Exclusion evidence — the labels that triggered the filter**")
        out.append("")
        if r["exclusion"]:
            for e in r["exclusion"][:6]:
                out.append(f"- `{e['quote']}`  (x{e['n']}, marker "
                           f"{e['marker']}; e.g. {e['tids']})")
        else:
            out.append("- (none found in this pass — see staff_crossref_v2.csv)")
        if v["summary_staff"] == "review" and v["summary_evidence"]:
            out.append(f"- summary-filter tier-2 example: "
                       f"\"{v['summary_evidence'][:300]}\"")
        out.append("")
        out.append("**Guest-role evidence**")
        out.append("")
        if r["guest"]:
            for g in r["guest"][:10]:
                out.append(f"- [{g['w']}] ({g['reason']}, {g['kind']}, "
                           f"{g['tids']}) \"{g['quote'][:400]}\"")
        else:
            out.append("- none found")
        out.append("")
        out.append("**Staff-role evidence**")
        out.append("")
        if r["staff"]:
            for st in r["staff"][:10]:
                out.append(f"- [{st['w']}] ({st['reason']}, {st['kind']}, "
                           f"{st['tids']}) \"{st['quote'][:400]}\"")
        else:
            out.append("- none found")
        out.append("")
        out.append("**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   "
                   "[ ] UNSURE")
        out.append("")
        out.append("---")
        out.append("")

    o = []
    o.append("# Staff-filter reserve — spot-check sheet")
    o.append("")
    o.append("What this is: the 292 subjects the Phase A staff filter dropped "
             "purely because a **speaker label** somewhere in the corpus "
             "carried a role word (HOST / ANCHOR / CORRESPONDENT / BYLINE / "
             "REPORTER / COMMENTATOR / a 'reporting' sign-off), with **no** "
             "tier-1 summary evidence that they are NPR or CNN staff. For each "
             "one I pulled every piece of role evidence out of the corpus and "
             "made an automatic recommendation. Nothing is re-admitted "
             "automatically: this sheet is the 20-subject human check that has "
             "to happen first.")
    o.append("")
    o.append("Sources: raw speaker labels across all 463,596 transcripts, "
             "transcript summaries, and host/self utterances that name the "
             "subject. Built by `experiments/reserve_evidence_v2.py` (one "
             "12-second pass over the 4.4 GB corpus) and "
             "`experiments/reserve_score_v2.py`. The per-subject table is "
             "`results/staff_reserve_dossiers.csv`. CPU only, no network, no "
             "LLM, $0.")
    o.append("")
    o.append("## Counts")
    o.append("")
    n_lt_total = sum(r["long_tail"] for r in rows)
    o.append(f"| recommendation | all {len(rows)} | long-tail ({n_lt_total}) |")
    o.append("|---|---|---|")
    for k in ("RE-ADMIT", "AMBIGUOUS", "KEEP-EXCLUDED"):
        o.append(f"| {k} | {cnt.get(k,0)} | {cnt_lt.get(k,0)} |")
    o.append("")
    ra_names = [r["canonical_name"] for r in rows
                if r["recommendation"] == "RE-ADMIT"]
    n_label_backed = sum(1 for x in ra_names
                         if any(i["kind"] == "label" and i["w"] == 3
                                for i in results[x]["guest"]))
    n_pub = sum(r["flag_public_radio"] for r in rows)
    n_other = sum(r["flag_other_network"] for r in rows)
    o.append("One number differs from the curation report: it says 84 of the "
             "292 are long-tail. Recomputing from "
             "`stage2_candidate_pool_v2.csv` gives **76** long-tail, plus 6 "
             "\"has-page-fuzzy\" (an article exists under a different "
             "spelling) and 210 with an article. 76 is the post-fuzzy figure "
             "and is what this sheet uses.")
    o.append("")
    o.append("## How much to trust the automatic recommendation")
    o.append("")
    o.append(TRUST.format(n_ra=len(ra_names), n_label_backed=n_label_backed,
                          n_pub=n_pub, n_other=n_other))
    o.append("")
    o.append("## Anchors (audit-verified, shown separately)")
    o.append("")
    o.append("Brian Bennett and Dexter Filkins were judged genuine guests by "
             "the 20-guest hand audit and should come out RE-ADMIT. Alex "
             "Kellogg and Brian Unger were judged staff and should come out "
             "KEEP-EXCLUDED. Kellogg and Unger are *not* in the reserve — the "
             "summary filter already catches them — they are here only as "
             "controls.")
    o.append("")
    for a in ANCHORS:
        block(a, o)
    o.append("## The 20 spot-check subjects")
    o.append("")
    o.append("Random sample, seed 42, stratified 10 long-tail / 10 with a "
             "Wikipedia page. Read the exclusion evidence first, then the two "
             "evidence blocks, then tick a box.")
    o.append("")
    for name in pick:
        block(name, o)

    with open(OUT_MD, "w") as f:
        f.write("\n".join(o))
    print(f"wrote {OUT_MD}")

    print("\ncounts all:", dict(cnt))
    print("counts long-tail:", dict(cnt_lt))
    for a in ["Brian Bennett", "Dexter Filkins", "Alex Kellogg", "Brian Unger"]:
        r = results[a]
        print(f"ANCHOR {a:16s} -> {r['rec']:14s} G={r['G']} "
              f"(gs{r['gs']}/gm{r['gm']})  S={r['S']} "
              f"(ss{r['ss']}/sm{r['sm']}/sw{r['sw']})")
    return rows, results, S


TRUST = """My honest read: **the recommendation is good enough to sort the
queue, not good enough to re-admit anyone on its own.**

Where it is strong. Most of the decisive evidence is a speaker label the
transcript itself carries, quoted verbatim — `GREG JAFFE, MILITARY REPORTER,
"THE WASHINGTON POST"`. When a label names an outside outlet, there is nothing
to interpret. {n_label_backed} of the {n_ra} RE-ADMIT subjects have at least
one such label. The four audit anchors all come out the way the audit says they
should, and six more people the audit or the curation report independently
called NPR staff
(Emily Green, Cheryl Corley, Allison Aubrey, Alex Cohen, Celeste Headlee,
Michel Martin) land in KEEP-EXCLUDED without being told to.

Where it is weak, in the order I would worry about it:

1. **Proximity, not grammar.** For summaries and host turns I look for role
   words near the name. In "guest host X talks with Y, author of Z" the word
   "author" belongs to Y. I patched the common form of this (the sheet now
   works out which side of "talks with" the subject is on), but the general
   problem is not solved, and it inflates guest evidence on any subject who
   shares a summary with several other people.
2. **Bare role labels carry no information.** `X, CORRESPONDENT` with nothing
   after it could be an NPR correspondent or a magazine's. Those subjects are
   mostly in AMBIGUOUS, which is where they belong, but it is why AMBIGUOUS is
   the largest bucket.
3. **Member stations look like outside outlets and are not.** A reporter for
   WFCR or Capital Public Radio reads as "outside affiliation" but files for
   NPR — the hand audit judged exactly such a person (Emily Green) to be staff.
   {n_pub} subjects trip this flag and none of them is auto-RE-ADMIT, but the
   station list is hand-made and certainly incomplete.
4. **Identity collisions are untouched.** The evidence is gathered per *name*,
   so two people who share a name share a dossier. `David Jackson` shows both
   "USA Today White House correspondent" and "Director, Voice of America";
   `Brian Bennett` shows "TIME magazine" and "passenger on Delta flight 1156".
   Re-admitting a name does not mean the transcripts behind it are one person.
5. **Other broadcasters.** {n_other} subjects carry an ABC / CBS / NBC / Fox /
   BBC / ESPN affiliation in their own speaker labels. They are outside NPR and
   CNN, so the filter's rationale does not apply to them, but whether a
   correspondent from a *different* network counts as an "interview subject" is
   the owner's call, not mine. They are flagged, not decided.

What I would expect if you audit the RE-ADMIT bucket by hand: a high hit rate
(the label evidence is explicit), with the errors concentrated in items 3-5
rather than in genuine NPR staff slipping through."""

if __name__ == "__main__":
    main()
