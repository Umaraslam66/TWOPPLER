"""Bar-lock item 5: how much identity survives name redaction, and what to cut.

Report 8.1 says the redacted arms are name-blind, not identity-blind: D8 scrubs
name variants and leaves "professor of Middle East politics at Georgetown
University" standing. This enumerates what is actually there in the committed
pilot-1 prompts and prices three candidate redaction scopes.

Leak classes counted (all inside the rendered prompt text, never the options):
  ORG      an institution named by spaCy (ORG / FAC / NORP), attached to GUEST
  ROLE     a role or occupation word attached to GUEST ("professor", "author",
           "former State Department official")
  TITLE    a quoted work title next to an authorship cue ("the author of
           \"Imperium\"")

"Attached to GUEST" means the mention sits in the same sentence as the GUEST
placeholder. That is the whole distinction between an identity leak and the
topic of the interview: "GUEST, professor at Georgetown" identifies the person;
"the United Nations sent an envoy" does not.

Scopes priced:
  S0  none / meter-only          today's rule; nothing removed
  S1  host-intro clauses         drop the appositive or predicate that
                                 describes GUEST, in HOST lines only
  S2  all ORG spans in host lines  replace every ORG/FAC in a HOST line
  S3  S1 + every ORG/FAC anywhere + quoted titles

CPU only, no network, no model calls.

Usage: uv run python experiments/barlock_affiliation.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"
PILOT = ROOT / "results" / "stage2_pilot"

ARMS = ("twin_redacted", "zeroinfo_redacted", "zeroinfo_named")

ORG_LABELS = frozenset({"ORG", "FAC"})

ROLE_WORDS = (
    "professor", "prof", "author", "co-author", "chairman", "chairwoman",
    "chair", "director", "fellow", "correspondent", "analyst", "ambassador",
    "secretary", "official", "officer", "editor", "columnist", "founder",
    "dean", "scholar", "researcher", "adviser", "advisor", "reporter",
    "anchor", "expert", "specialist", "scientist", "historian", "novelist",
    "writer", "attorney", "lawyer", "senator", "congressman", "congresswoman",
    "governor", "minister", "president", "vice president", "commissioner",
    "spokesman", "spokeswoman", "economist", "psychologist", "sociologist",
    "physician", "surgeon", "curator", "producer", "publisher", "critic",
    "strategist", "diplomat", "veteran", "professor emeritus", "lecturer",
    "head of", "chief", "co-founder", "general counsel", "consultant",
)
_ROLE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in ROLE_WORDS) + r")\b",
                      re.IGNORECASE)
_TITLE_RE = re.compile(r"(author|wrote|writes|book|novel|memoir|article|essay)"
                       r"[^.\n]{0,40}?[\"“]([^\"”\n]{2,80})[\"”]", re.IGNORECASE)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def nlp():
    import spacy
    return spacy.load("en_core_web_sm", disable=["lemmatizer"])


def excerpt_lines(prompt: str) -> list[tuple[int, str, str]]:
    """(line_no, kind, text) for every HOST:/GUEST: line of a rendered prompt.

    kind is "host" or "guest". Everything else — preamble, option list, the
    instruction — is not excerpt text and is not scanned, except that the
    zero-information arms have exactly one HOST line (the question), which is
    scanned because report 8.1 found an occupation in one.
    """
    out = []
    for i, line in enumerate(prompt.splitlines()):
        if line.startswith("HOST: "):
            out.append((i, "host", line[6:]))
        elif line.startswith("GUEST: "):
            out.append((i, "guest", line[7:]))
    return out


#: A host addressing the guest in the second person is describing the guest,
#: even when the GUEST placeholder is in the previous sentence. This is how
#: report 8.1's zero-information leak reads: "..., GUEST, then. You're a
#: professor of social sciences."
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|you've|yourself)\b",
                               re.IGNORECASE)


def _attachment(sent: str, offset: int, mention_at: int, persons) -> str:
    """"guest", "third_party" or "topic" for one mention inside ``sent``.

    A sentence that names GUEST can still be describing somebody else — a
    roundtable host introduces three people in one breath. The mention belongs
    to whichever of GUEST / the nearest other PERSON entity is closer to it in
    characters; ties go to GUEST (conservative: counts as a leak).
    """
    g = [m.start() for m in re.finditer("GUEST", sent)]
    p = [a - offset for a, b in persons if offset <= a < offset + len(sent)]
    if not g:
        return "topic"
    dg = min(abs(mention_at - x) for x in g)
    if not p:
        return "guest"
    dp = min(abs(mention_at - x) for x in p)
    return "guest" if dg <= dp else "third_party"


def find_leaks(prompt: str, doc_cache) -> list[dict]:
    """Every identity mention in one rendered prompt, with its class."""
    leaks = []
    for line_no, kind, text in excerpt_lines(prompt):
        doc = doc_cache(text)
        ents = [(e.text, e.label_, e.start_char, e.end_char) for e in doc.ents]
        persons = [(a, b) for _, label, a, b in ents if label == "PERSON"]
        pos = 0
        for sent in _SENT_SPLIT.split(text):
            start = text.find(sent, pos)
            if start < 0:
                start = pos
            end = start + len(sent)
            pos = end
            second_person = (kind == "host"
                             and bool(_SECOND_PERSON_RE.search(sent)))
            for etext, label, a, b in ents:
                if label not in ORG_LABELS or not (start <= a < end):
                    continue
                att = _attachment(sent, start, a - start, persons)
                if att == "topic" and second_person:
                    att = "guest"
                leaks.append({"line": line_no, "kind": kind, "cls": "ORG",
                              "attachment": att,
                              "attached_to_guest": att == "guest",
                              "mention": etext, "sentence": sent[:220]})
            for m in _ROLE_RE.finditer(sent):
                att = _attachment(sent, start, m.start(), persons)
                if att == "topic" and second_person:
                    att = "guest"
                if att == "topic":
                    continue          # a role word about nobody is not a leak
                leaks.append({"line": line_no, "kind": kind, "cls": "ROLE",
                              "attachment": att,
                              "attached_to_guest": att == "guest",
                              "mention": m.group(0), "sentence": sent[:220]})
            for m in _TITLE_RE.finditer(sent):
                att = _attachment(sent, start, m.start(), persons)
                if att == "topic" and second_person:
                    att = "guest"
                leaks.append({"line": line_no, "kind": kind, "cls": "TITLE",
                              "attachment": att,
                              "attached_to_guest": att == "guest",
                              "mention": m.group(2), "sentence": sent[:220]})
    return leaks


# ---------------------------------------------------------------------------
# The scopes
# ---------------------------------------------------------------------------

def _blank_org(text: str, doc, only: str | None = None) -> tuple[str, int]:
    spans = [(e.start_char, e.end_char) for e in doc.ents
             if e.label_ in ORG_LABELS]
    if only is not None:
        spans = [(a, b) for a, b in spans if only in text[max(0, a - 200):b + 200]]
    out, last, n = [], 0, 0
    for a, b in sorted(spans):
        if a < last:
            continue
        out.append(text[last:a])
        out.append("[ORG]")
        last = b
        n += 1
    out.append(text[last:])
    return "".join(out), n


_APPOS_RE = re.compile(
    r"GUEST(?:'s)?,\s+([^,.;]{3,120})(?=[,.;])|"          # "GUEST, professor at X,"
    r"GUEST\s+is\s+([^.;]{3,160})(?=[.;])|"               # "GUEST is the author of X."
    r"GUEST,\s+(?:as\s+)?an?\s+([^,.;]{3,120})(?=[,.;])"  # "GUEST, as a former ..."
)


def apply_s1(text: str) -> tuple[str, int]:
    """Drop the clause that describes GUEST, when it carries a role word."""
    n = 0

    def repl(m):
        nonlocal n
        body = next(g for g in m.groups() if g)
        if not _ROLE_RE.search(body):
            return m.group(0)
        n += 1
        return m.group(0).replace(body, "[DESCRIPTION REMOVED]")

    return _APPOS_RE.sub(repl, text), n


def apply_scope(prompt: str, scope: str, doc_cache) -> tuple[str, int]:
    """Rewrite one prompt under a scope; return (text, mentions removed)."""
    if scope == "S0":
        return prompt, 0
    lines = prompt.splitlines()
    removed = 0
    for i, line in enumerate(lines):
        if line.startswith("HOST: "):
            kind, body = "host", line[6:]
        elif line.startswith("GUEST: "):
            kind, body = "guest", line[7:]
        else:
            continue
        new = body
        if scope in ("S1", "S3"):
            new, n = apply_s1(new)
            removed += n
        if scope == "S2" and kind == "host":
            new, n = _blank_org(new, doc_cache(new))
            removed += n
        if scope == "S3":
            new, n = _blank_org(new, doc_cache(new))
            removed += n
            new, n2 = _TITLE_RE.subn(lambda m: m.group(0).replace(
                m.group(2), "[TITLE REMOVED]"), new)
            removed += n2
        lines[i] = ("HOST: " if kind == "host" else "GUEST: ") + new
    return "\n".join(lines), removed


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    pipe = nlp()
    cache: dict[str, object] = {}

    def doc_cache(text: str):
        if text not in cache:
            cache[text] = pipe(text)
        return cache[text]

    prompts = []
    for arm in ARMS:
        mp = PILOT / "exports" / f"meta_pred_{arm}_standard.jsonl"
        pp = PILOT / "exports" / f"prompts_pred_{arm}_standard.jsonl"
        if not (mp.exists() and pp.exists()):
            continue
        metas = [json.loads(l) for l in mp.read_text().splitlines() if l.strip()]
        texts = {json.loads(l)["idx"]: json.loads(l)["prompt"]
                 for l in pp.read_text().splitlines() if l.strip()}
        for m in metas:
            prompts.append({"arm": arm, "item_id": m["item_id"],
                            "canonical_id": m["canonical_id"],
                            "prompt": texts[m["idx"]]})

    # --- inventory --------------------------------------------------------
    inventory = {}
    per_subject: dict[str, dict] = {}
    all_leaks = []
    for p in prompts:
        leaks = find_leaks(p["prompt"], doc_cache)
        for lk in leaks:
            lk["arm"] = p["arm"]
            lk["item_id"] = p["item_id"]
            lk["canonical_id"] = p["canonical_id"]
        all_leaks.extend(leaks)
    for arm in ARMS:
        rows = [l for l in all_leaks if l["arm"] == arm]
        att = [l for l in rows if l["attached_to_guest"]]
        inventory[arm] = {
            "n_prompts": sum(1 for p in prompts if p["arm"] == arm),
            "mentions_total": len(rows),
            "mentions_attached_to_guest": len(att),
            "by_class_attached": {
                c: sum(1 for l in att if l["cls"] == c) for c in ("ORG", "ROLE", "TITLE")},
            "by_class_all": {
                c: sum(1 for l in rows if l["cls"] == c) for c in ("ORG", "ROLE", "TITLE")},
            "by_attachment": {
                a: sum(1 for l in rows if l["attachment"] == a)
                for a in ("guest", "third_party", "topic")},
            "distinct_identity_facts": len({(l["canonical_id"], l["cls"],
                                             l["mention"], l["sentence"])
                                            for l in att}),
            "distinct_identity_sentences": len({(l["canonical_id"], l["sentence"])
                                                for l in att}),
            "distinct_lines_attached": len({(l["item_id"], l["line"]) for l in att}),
            "distinct_lines_any": len({(l["item_id"], l["line"]) for l in rows}),
        }
    for l in all_leaks:
        d = per_subject.setdefault(l["canonical_id"],
                                   {"ORG": 0, "ROLE": 0, "TITLE": 0,
                                    "attached": 0, "total": 0})
        d[l["cls"]] += 1
        d["total"] += 1
        d["attached"] += int(l["attached_to_guest"])

    # --- scopes -----------------------------------------------------------
    scopes = {}
    for scope in ("S0", "S1", "S2", "S3"):
        removed_total = 0
        changed_prompts = 0
        examples = []
        residual = 0
        for p in prompts:
            new, n = apply_scope(p["prompt"], scope, doc_cache)
            removed_total += n
            if new != p["prompt"]:
                changed_prompts += 1
                if len(examples) < 3 and scope != "S0":
                    before = [a for a, b in zip(p["prompt"].splitlines(),
                                                new.splitlines()) if a != b]
                    after = [b for a, b in zip(p["prompt"].splitlines(),
                                               new.splitlines()) if a != b]
                    examples.append({"arm": p["arm"], "item_id": p["item_id"],
                                     "before": before[0][:300],
                                     "after": after[0][:300]})
            residual += sum(1 for l in find_leaks(new, doc_cache)
                            if l["attached_to_guest"])
        # collateral = ORG mentions removed that were NOT attached to GUEST
        collateral = 0
        if scope in ("S2", "S3"):
            for p in prompts:
                for l in find_leaks(p["prompt"], doc_cache):
                    if l["cls"] != "ORG" or l["attached_to_guest"]:
                        continue
                    if scope == "S2" and l["kind"] != "host":
                        continue
                    collateral += 1
        scopes[scope] = {
            "mentions_removed": removed_total,
            "prompts_changed": changed_prompts,
            "of_prompts": len(prompts),
            "residual_attached_mentions": residual,
            "collateral_topical_org_mentions_removed": collateral,
            "examples": examples,
        }

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_prompts": len(prompts),
        "arms": list(ARMS),
        "detector": {
            "ORG": "spaCy en_core_web_sm ents with label ORG or FAC",
            "ROLE": f"{len(ROLE_WORDS)} role words, only in a sentence containing GUEST",
            "TITLE": "quoted string within 40 chars of an authorship cue",
            "attached_to_guest": "the mention's sentence contains the GUEST placeholder",
        },
        "inventory": inventory,
        "per_subject": per_subject,
        "scopes": scopes,
        "sample_attached_mentions": [
            {k: l[k] for k in ("arm", "canonical_id", "cls", "mention",
                               "attachment", "sentence")}
            for l in all_leaks if l["attached_to_guest"]][:40],
        "zeroinfo_attached_mentions": [
            {k: l[k] for k in ("arm", "canonical_id", "item_id", "cls",
                               "mention", "sentence")}
            for l in all_leaks
            if l["attached_to_guest"] and l["arm"].startswith("zeroinfo")],
        "distinct_identity_facts": sorted({
            (l["canonical_id"], l["cls"], l["mention"], l["sentence"][:150])
            for l in all_leaks if l["attached_to_guest"]}),
        "sample_third_party_mentions": [
            {k: l[k] for k in ("arm", "canonical_id", "cls", "mention", "sentence")}
            for l in all_leaks if l["attachment"] == "third_party"][:10],
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "affiliation_scope.json").write_text(json.dumps(payload, indent=1))
    print(json.dumps({k: v for k, v in payload.items()
                      if not k.startswith("sample_")}, indent=1)[:9000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
