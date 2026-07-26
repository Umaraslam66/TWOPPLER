"""Bar-lock item 3: replace the hand-maintained nickname table with a resource.

Report 8.2 says the pilot's NICKNAME_SUPPLEMENT (11 first names, hand-written)
does not scale to 1,153 subjects and that the real answer is a name-
normalisation resource. This measures one concrete resource against the hand
table:

    nicknames 1.0.1 (PyPI), Apache-2.0, data from
    github.com/carltonnorthern/nicknames — one 74 KB CSV, 2,691 name/nickname
    pairs, hand-curated English hypocorisms. Small enough to check into the
    repo as a data file; no network at run time.

Measured:
  (a) coverage of the hand table vs the resource, on the 6 dev subjects, their
      6 imposter donors, the 200-subject bank donor sample, and the whole
      578-row eligible pool;
  (b) NEW leaks: nickname or formal-name forms that survive in the committed
      pilot-1 redacted prompts and that the resource would have caught;
  (c) over-redaction: how many extra tokens the resource would scrub out of
      those same prompts, listed so the owner can judge each one.

CPU only, no network, no model calls.

Usage: uv run python experiments/barlock_nicknames.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler.stage2_data import HONORIFIC, eligible_subjects, load_pool  # noqa: E402
from doppler.stage2_render import expand_variants  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"
PILOT = ROOT / "results" / "stage2_pilot"

sys.path.insert(0, str(ROOT / "experiments"))
import stage2_pilot as P  # noqa: E402  (for NICKNAME_SUPPLEMENT / first_name_of)

REDACTED_ARMS = ("twin_redacted", "imposter_redacted")


def namer():
    from nicknames import NickNamer
    return NickNamer()


def first_name(full: str) -> str | None:
    got = P.first_name_of(full)
    return got[0] if got else None


def hand_forms(first: str) -> set[str]:
    return {n.lower() for n in P.NICKNAME_SUPPLEMENT.get(first, ())}


def resource_forms(nn, first: str) -> set[str]:
    """Every alternate first-name form: nicknames of it, and formal names of it.

    Both directions matter. The pool's canonical name can be the formal one
    ("Matthew" when the transcript says "Matt") or the short one ("Bob" when
    the transcript says "Robert"), and the pilot's table only ever handled the
    first case.
    """
    out = {n.lower() for n in nn.nicknames_of(first)}
    out |= {n.lower() for n in nn.canonicals_of(first)}
    out.discard(first.lower())
    return out


def person_rows() -> list[dict]:
    """The 12 people whose names the pilot prompts actually redact."""
    pool = {r["canonical_id"]: r for r in load_pool()}
    dev = json.loads((PILOT / "dev_subjects.json").read_text())["subjects"]
    pairs = json.loads((PILOT / "imposter_pairs.json").read_text())["pairs"]
    ids = [s["canonical_id"] for s in dev]
    rows = []
    for cid in ids:
        rows.append({"canonical_id": cid, "role": "dev",
                     "canonical_name": pool[cid]["canonical_name"],
                     "variants": pool[cid]["variants"]})
    for cid in sorted(set(pairs.values())):
        rows.append({"canonical_id": cid, "role": "donor",
                     "canonical_name": pool[cid]["canonical_name"],
                     "variants": pool[cid]["variants"]})
    return rows


def coverage(nn) -> dict:
    pool = load_pool()
    elig = eligible_subjects(pool)
    people = person_rows()

    per_person = []
    for r in people:
        f = first_name(r["canonical_name"])
        hand = hand_forms(f) if f else set()
        res = resource_forms(nn, f) if f else set()
        per_person.append({
            "canonical_id": r["canonical_id"], "role": r["role"],
            "canonical_name": r["canonical_name"],
            "first_name": f,
            "hand_table": sorted(hand),
            "resource": sorted(res),
            "resource_only": sorted(res - hand),
            "hand_only": sorted(hand - res),
        })

    def share(rows):
        f = [first_name(r["canonical_name"]) for r in rows]
        f = [x for x in f if x]
        hand = sum(1 for x in f if x in P.NICKNAME_SUPPLEMENT)
        res = sum(1 for x in f if resource_forms(nn, x))
        return {"n_with_first_name": len(f), "n_rows": len(rows),
                "hand_table_hits": hand, "resource_hits": res,
                "hand_share": round(hand / len(f), 4) if f else 0.0,
                "resource_share": round(res / len(f), 4) if f else 0.0}

    bank = [json.loads(l) for l in
            (PILOT / "distractor_bank.jsonl").read_text().splitlines() if l.strip()]
    bank_ids = sorted({r["source_canonical_id"] for r in bank})
    by_id = {r["canonical_id"]: r for r in pool}

    return {
        "per_person": per_person,
        "pilot_12": share(people),
        "bank_donors": share([by_id[c] for c in bank_ids if c in by_id]),
        "eligible_pool_578": share(elig),
        "full_pool_1153": share(pool),
    }


#: A word that is BOTH a hypocorism and an ordinary English word is the whole
#: over-redaction cost of this rule ("Bill", "Bob", "Rob", "Art", "Dick").
#: /usr/share/dict/words is the macOS/BSD web2 list, present on the dev box; if
#: it is absent the scale-risk block is reported as unavailable rather than
#: guessed.
WORDS_PATH = Path("/usr/share/dict/words")


def english_words() -> set[str] | None:
    if not WORDS_PATH.exists():
        return None
    return {w.strip().lower() for w in WORDS_PATH.read_text(errors="ignore").splitlines()
            if len(w.strip()) >= 3}


def scale_risk(nn) -> dict:
    """How much over-redaction the resource buys across the whole pool."""
    words = english_words()
    pool = load_pool()
    elig = eligible_subjects(pool)
    out = {}
    for label, rows in (("eligible_578", elig), ("full_1153", pool)):
        n_sub_any, n_forms, n_word_forms, n_sub_word = 0, 0, 0, 0
        worst: dict[str, int] = {}
        for r in rows:
            f = first_name(r["canonical_name"])
            if not f:
                continue
            forms = {x for x in forms_for(nn, f, "hand_union_both") if len(x) >= 3}
            if forms:
                n_sub_any += 1
            n_forms += len(forms)
            if words is None:
                continue
            wf = {x for x in forms if x in words}
            n_word_forms += len(wf)
            if wf:
                n_sub_word += 1
            for x in wf:
                worst[x] = worst.get(x, 0) + 1
        out[label] = {
            "n_rows": len(rows),
            "subjects_gaining_at_least_one_form": n_sub_any,
            "total_extra_name_forms": n_forms,
            "forms_that_are_ordinary_english_words": (
                None if words is None else n_word_forms),
            "subjects_with_an_ordinary_word_form": (
                None if words is None else n_sub_word),
            "commonest_ordinary_word_forms": (
                None if words is None else
                dict(sorted(worst.items(), key=lambda kv: -kv[1])[:15])),
        }
    out["word_list"] = (str(WORDS_PATH) if words is not None else "unavailable")
    return out


def prompt_index() -> list[dict]:
    """Every committed redacted prompt with the person it is about."""
    out = []
    exports = PILOT / "exports"
    for arm in REDACTED_ARMS:
        for variant in ("standard", "stripped"):
            mp = exports / f"meta_pred_{arm}_{variant}.jsonl"
            pp = exports / f"prompts_pred_{arm}_{variant}.jsonl"
            if not (mp.exists() and pp.exists()):
                continue
            metas = [json.loads(l) for l in mp.read_text().splitlines() if l.strip()]
            prompts = {json.loads(l)["idx"]: json.loads(l)["prompt"]
                       for l in pp.read_text().splitlines() if l.strip()}
            for m in metas:
                out.append({"arm": arm, "variant": variant,
                            "item_id": m["item_id"],
                            "canonical_id": m["canonical_id"],
                            "donor_id": m.get("donor_id"),
                            "prompt": prompts[m["idx"]]})
    return out


def word_hits(text: str, token: str) -> list[str]:
    """Case-insensitive whole-word hits of ``token`` with a little context."""
    pat = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
    out = []
    for m in pat.finditer(text):
        a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
        out.append(text[a:b].replace("\n", " "))
    return out


#: The four rules compared. "fwd" = nicknames_of (the pool name is the formal
#: one, the transcript may use the short one). "rev" = canonicals_of (the pool
#: name is already the short one and the transcript may use the formal one).
VARIANTS = ("hand", "resource_fwd", "resource_both", "hand_union_both")


def forms_for(nn, first: str, variant: str) -> set[str]:
    hand = hand_forms(first)
    fwd = {n.lower() for n in nn.nicknames_of(first)} - {first.lower()}
    rev = {n.lower() for n in nn.canonicals_of(first)} - {first.lower()}
    if variant == "hand":
        return hand
    if variant == "resource_fwd":
        return fwd
    if variant == "resource_both":
        return fwd | rev
    return hand | fwd | rev


def scan_text(text: str, forms, surname: str) -> tuple[list, list]:
    """(leaks, collateral) hits of ``forms`` in ``text``.

    A hit sitting next to the person's surname or next to the GUEST
    placeholder is a leak the rule would catch; any other hit is a word the
    rule would scrub for no reason.
    """
    leaks, coll = [], []
    for form in sorted(forms):
        if len(form) < 3:
            continue                       # "Al", "Ed" — indistinguishable noise
        if form.upper() in HONORIFIC:
            continue
        for ctx in word_hits(text, form):
            near = re.search(
                rf"\b{re.escape(form)}\b[^\w]+(guest|{re.escape(surname)})|"
                rf"(guest|{re.escape(surname)})[^\w]+\b{re.escape(form)}\b",
                ctx, re.IGNORECASE)
            (leaks if near else coll).append({"form": form, "context": ctx})
    return leaks, coll


def turn_texts(cid: str) -> str:
    """All committed turn text for one dev subject or donor."""
    chunks = []
    for base in ("subjects", "donors"):
        d = PILOT / base / cid
        for name in ("grounding_turns.jsonl", "test_turns.jsonl"):
            p = d / name
            if p.exists():
                for line in p.read_text().splitlines():
                    if line.strip():
                        chunks.append(json.loads(line).get("text") or "")
    return "\n".join(chunks)


def variant_table(nn) -> dict:
    """Leaks and collateral per rule variant, on prompts and on raw turn text."""
    pool = {r["canonical_id"]: r for r in load_pool()}
    prompts = prompt_index()
    people = person_rows()

    def already(cid):
        row = pool[cid]
        v = P.name_variants({"canonical_name": row["canonical_name"],
                             "variants": row["variants"]})
        return {t.lower() for t in expand_variants(v)}

    out = {}
    for variant in VARIANTS:
        n_leak = n_coll = 0
        leak_ex, coll_ex = [], []
        seen = set()
        # (i) the committed rendered prompts
        for p in prompts:
            cid = (p["donor_id"] if p["arm"] == "imposter_redacted"
                   else p["canonical_id"])
            row = pool.get(cid)
            if row is None:
                continue
            f = first_name(row["canonical_name"])
            if not f:
                continue
            forms = forms_for(nn, f, variant) - already(cid)
            surname = row["canonical_name"].split()[-1].lower()
            lk, cl = scan_text(p["prompt"], forms, surname)
            for h in lk:
                key = ("p", cid, h["form"], h["context"])
                if key in seen:
                    continue
                seen.add(key)
                n_leak += 1
                if len(leak_ex) < 5:
                    leak_ex.append({"where": f"{p['arm']}/{p['item_id']}",
                                    "person": cid, **h})
            for h in cl:
                key = ("p", cid, h["form"], h["context"])
                if key in seen:
                    continue
                seen.add(key)
                n_coll += 1
                if len(coll_ex) < 5:
                    coll_ex.append({"where": f"{p['arm']}/{p['item_id']}",
                                    "person": cid, **h})
        # (ii) the raw turn text behind them (prompts are budget-trimmed, so
        #      this is the stronger test of what the rule would catch)
        t_leak = t_coll = 0
        t_leak_ex = []
        for r in people:
            cid = r["canonical_id"]
            f = first_name(r["canonical_name"])
            if not f:
                continue
            forms = forms_for(nn, f, variant) - already(cid)
            surname = r["canonical_name"].split()[-1].lower()
            lk, cl = scan_text(turn_texts(cid), forms, surname)
            t_leak += len(lk)
            t_coll += len(cl)
            for h in lk[:2]:
                if len(t_leak_ex) < 6:
                    t_leak_ex.append({"person": cid, **h})
        out[variant] = {
            "prompts_new_leaks": n_leak,
            "prompts_collateral": n_coll,
            "turns_new_leaks": t_leak,
            "turns_collateral": t_coll,
            "prompt_leak_examples": leak_ex,
            "prompt_collateral_examples": coll_ex,
            "turn_leak_examples": t_leak_ex,
        }
    return out


def leaks_and_overredaction(nn) -> dict:
    pool = {r["canonical_id"]: r for r in load_pool()}
    prompts = prompt_index()
    people = {r["canonical_id"]: r for r in person_rows()}

    # Tokens already scrubbed by the pilot (so a hit on one of these is
    # impossible, and finding one would mean the pilot guard failed).
    def pilot_tokens(cid: str) -> set[str]:
        row = pool[cid]
        variants = P.name_variants({"canonical_name": row["canonical_name"],
                                    "variants": row["variants"]})
        return {t.lower() for t in expand_variants(variants)}

    leaks, over = [], []
    seen_leak, seen_over = set(), set()
    for p in prompts:
        # In an imposter prompt the excerpts are the DONOR's, so the person
        # whose name could leak there is the donor.
        cid = p["donor_id"] if p["arm"] == "imposter_redacted" else p["canonical_id"]
        if cid not in people:
            continue
        row = pool[cid]
        f = first_name(row["canonical_name"])
        if not f:
            continue
        already = pilot_tokens(cid)
        new_forms = sorted(resource_forms(nn, f) - already)
        for form in new_forms:
            if len(form) < 3:
                continue                     # "Al", "Ed" — too short to judge
            if form.upper() in HONORIFIC:
                continue
            for ctx in word_hits(p["prompt"], form):
                rec = {"arm": p["arm"], "variant": p["variant"],
                       "item_id": p["item_id"], "person": cid,
                       "person_name": row["canonical_name"],
                       "first_name": f, "form": form, "context": ctx}
                key = (cid, form, ctx)
                # A hit next to the surname (or next to GUEST) is a real leak;
                # anything else is an unrelated word and would be collateral.
                surname = row["canonical_name"].split()[-1].lower()
                near = re.search(rf"\b{re.escape(form)}\b[^\w]+(guest|{re.escape(surname)})",
                                 ctx, re.IGNORECASE)
                if near:
                    if key not in seen_leak:
                        seen_leak.add(key)
                        leaks.append(rec)
                else:
                    if key not in seen_over:
                        seen_over.add(key)
                        over.append(rec)
    return {"n_prompts_scanned": len(prompts),
            "new_leaks": leaks,
            "collateral_candidates": over}


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    nn = namer()
    cov = coverage(nn)
    scan = leaks_and_overredaction(nn)

    per_form: dict[str, int] = {}
    for r in scan["collateral_candidates"]:
        per_form[r["form"]] = per_form.get(r["form"], 0) + 1

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "resource": {
            "package": "nicknames==1.0.1 (PyPI)",
            "data": "names.csv, 2,691 pairs, 74 KB",
            "source": "https://github.com/carltonnorthern/nicknames",
            "licence": "Apache-2.0",
            "shippable": "yes — one CSV, checkable into data/ or src/doppler/",
            "directions_used": "nicknames_of(first) AND canonicals_of(first)",
        },
        "hand_table": {"n_first_names": len(P.NICKNAME_SUPPLEMENT),
                       "entries": {k: list(v) for k, v in
                                   P.NICKNAME_SUPPLEMENT.items()}},
        "coverage": cov,
        "variant_comparison": variant_table(nn),
        "scale_risk": scale_risk(nn),
        "prompt_scan": {
            "n_prompts_scanned": scan["n_prompts_scanned"],
            "n_new_leaks": len(scan["new_leaks"]),
            "n_collateral_candidates": len(scan["collateral_candidates"]),
            "collateral_by_form": dict(sorted(per_form.items(),
                                              key=lambda kv: -kv[1])),
            "new_leaks": scan["new_leaks"],
            "collateral_candidates": scan["collateral_candidates"][:40],
        },
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "nickname_resource.json").write_text(json.dumps(payload, indent=1))
    slim = json.loads(json.dumps(payload))
    slim["coverage"]["per_person"] = "(see file)"
    slim["prompt_scan"]["collateral_candidates"] = "(see file)"
    print(json.dumps(slim, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
