"""Stage 2 data foundation: dev-subject draw, chronological split, turn extraction.

This is the file every later Stage 2 module reads from. It implements SPEC
sections D1 (dev-subject draw), D2 (chronological split) and D3 (turn
extraction), and nothing else — no prompts, no scoring, no model calls.

**Pure standard library on purpose.** Same reason as adaptive_render.py: the
file may be rsynced to a compute node next to a driver, and the split rules
must not be able to drift between the local and remote copies.

What lives here
---------------
- ``load_pool``          read results/stage2_candidate_pool_v2.csv into typed rows
- ``parse_transcripts``  parse the ``transcripts`` provenance column
- ``draw_dev_subjects``  D1: seeded stratified draw of the 5 dev subjects
- ``chronological_split``D2: latest interview = test, everything strictly
                         earlier = grounding, same-date siblings excluded
- ``extract_turns``      D3: guest/host/other role assignment per utterance
- ``fetch_records``      one streaming pass over the 4.45 GB corpus for a
                         named set of transcript ids
- ``load_guest_words``   per-(subject, transcript) guest word counts, read from
                         the existing v2 scan cache instead of re-scanning

Word counts are whitespace tokens throughout; that is the pilot's documented
token proxy (SPEC D5).
"""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (resolved from this file so the module works from any cwd)
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
POOL_CSV = ROOT / "results/stage2_candidate_pool_v2.csv"
RAW_JSON = ROOT / "data/mediasum/news_dialogue.json"
SCAN_CACHE = ROOT / "data/mediasum_index/_scan_cache_v2.pkl"
PILOT_DIR = ROOT / "results/stage2_pilot"

DEV_SEED = 47
N_WIKI = 3
N_LONGTAIL = 2

DRAW_RULE = (
    "Eligible = qualifies AND clean AND NOT ambiguous_identity in "
    "results/stage2_candidate_pool_v2.csv. Eligible canonical_ids are sorted "
    "lexicographically, then shuffled once with random.Random(47).shuffle. "
    "Walking that shuffled order, the first 3 ids whose wiki_status is not "
    "'long-tail' and the first 2 whose wiki_status is 'long-tail' are the dev "
    "subjects. A subject found broken later stays burned (it is a dev subject "
    "forever and is never reused); its replacement is the next id of the same "
    "stratum in the same shuffled order. A subject broken for one purpose only "
    "is instead retained in place, annotated burned_for_qa, and the next id of "
    "its stratum is ADDED alongside it, which is why the subject count can "
    "exceed 5. shuffle_pos is the 0-based position of each pick in that "
    "shuffled order."
)

SPLIT_RULE = (
    "Substantive transcripts only (flag S in the pool's transcripts column), "
    "grouped by cluster_id (one cluster = one real interview event; re-airings "
    "share a cluster). Cluster date = earliest transcript date in the cluster. "
    "Cluster representative = the transcript with the most guest words, ties "
    "broken by lexicographically smallest transcript_id. test = the cluster "
    "with the latest date; a tie for latest is broken by representative "
    "transcript_id lexicographic order, largest wins. grounding = every "
    "cluster ALL of whose member transcripts are dated strictly before the "
    "test date. Every other cluster is excluded entirely: one sharing the test "
    "date, and one whose cluster date is earlier but which has any member "
    "transcript aired on or after the test date (same-event leak guard, "
    "hardened v1.2 to test every member rather than the cluster minimum)."
)


# ---------------------------------------------------------------------------
# Speaker classification
#
# VENDORED from experiments/mediasum_index.py (classify_speaker, its regexes
# and its helpers, as of commit a4b9f1b). Copied rather than imported because
# experiments/ is not an importable package and src/ must not path-hack its way
# into it; tests/test_stage2_data.py imports the original by file path and
# asserts this copy still agrees with it on a label battery, so the two cannot
# drift silently.
# ---------------------------------------------------------------------------

STAFF_ROLE_RE = re.compile(
    r"\b(HOST|ANCHOR|CORRESPONDENT|BYLINE|REPORTER|COMMENTATOR)\b")

ANON_RE = re.compile(r"\b(UNIDENTIFIED|UNIDENTIFED|UNKNOWN|UNIDENTIFY\w*)\b")

HONORIFIC_MULTI = [
    "VICE PRESIDENT", "PRIME MINISTER", "ATTORNEY GENERAL",
    "SECRETARY OF STATE", "SECRETARY OF DEFENSE", "FORMER PRESIDENT",
    "FIRST LADY", "MAJORITY LEADER", "MINORITY LEADER", "CHIEF JUSTICE",
    "SUPREME COURT JUSTICE", "STAFF SERGEANT", "LIEUTENANT GENERAL",
    "LIEUTENANT COLONEL", "MASTER SERGEANT", "STATE SENATOR", "STATE REP",
]
HONORIFIC = {
    "DR", "MR", "MRS", "MS", "MISS", "MX", "SEN", "SENATOR", "REP",
    "REPRESENTATIVE", "CONGRESSMAN", "CONGRESSWOMAN", "GOV", "GOVERNOR",
    "PRES", "PRESIDENT", "PROF", "PROFESSOR", "GEN", "GENERAL", "COL",
    "COLONEL", "LT", "LIEUTENANT", "LIEUT", "SGT", "SERGEANT", "MAJ",
    "MAJOR", "CPL", "CORPORAL", "CAPT", "CAPTAIN", "ADM", "ADMIRAL", "CMDR",
    "COMMANDER", "REV", "REVEREND", "FR", "FATHER", "RABBI", "IMAM", "SHEIKH",
    "SHEIK", "JUDGE", "JUSTICE", "MAYOR", "AMBASSADOR", "AMB", "SECRETARY",
    "SEC", "DEAN", "SIR", "DAME", "LORD", "LADY", "PRINCE", "PRINCESS",
    "KING", "QUEEN", "POPE", "ARCHBISHOP", "BISHOP", "CARDINAL", "DETECTIVE",
    "DET", "OFFICER", "CHIEF", "SUPERINTENDENT", "COACH", "DOCTOR", "PASTOR",
    "BROTHER", "SISTER", "MOTHER", "AYATOLLAH", "COUNSELOR", "DELEGATE",
    "ASSEMBLYMAN", "ASSEMBLYWOMAN", "COUNCILMAN", "COUNCILWOMAN",
}

GENERIC_TOKENS = {
    "MALE", "FEMALE", "MAN", "WOMAN", "MEN", "WOMEN", "BOY", "GIRL", "CHILD",
    "CHILDREN", "KID", "KIDS", "CALLER", "CALLERS", "QUESTION", "QUESTIONER",
    "SPEAKER", "SPEAKERS", "GUEST", "GUESTS", "VOICE", "VOICES", "AUDIENCE",
    "CROWD", "GROUP", "ALL", "PANEL", "PANELIST", "PANELISTS", "MODERATOR",
    "TRANSLATOR", "INTERPRETER", "OPERATOR", "NARRATOR", "ANNOUNCER",
    "ADVERTISEMENT", "COMMERCIAL", "RECORDING", "PROTESTER", "PROTESTERS",
    "PROTESTORS", "MULTIPLE", "EVERYONE", "PARTICIPANT", "PARTICIPANTS",
    "SUBJECT", "PERSON", "PEOPLE", "STUDENT", "STUDENTS", "WITNESS",
    "JUROR", "JURORS", "MEMBER", "MEMBERS", "SINGER", "SINGERS", "CHORUS",
    "SPOKESMAN", "SPOKESWOMAN", "SPOKESPERSON", "VOICEOVER", "AUTOMATED",
    "SoundBite".upper(), "SOUNDBITE", "CLIP", "ACTOR", "ACTRESS", "OTHERS",
    "SEVERAL", "BOTH", "VARIOUS", "OFFSCREEN", "INAUDIBLE", "APPLAUSE",
}

_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_DASH_SPLIT_RE = re.compile(r"\s[-–—:]\s")
_ALPHA_RUN_RE = re.compile(r"[A-Za-z]+")


def _titlecase(s: str) -> str:
    return _ALPHA_RUN_RE.sub(
        lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(), s)


def classify_speaker(raw):
    """Return (kind, normalized_name_or_None, honorific_or_None).

    kind in {'guest', 'staff', 'anon'}.
    """
    if not raw:
        return ("anon", None, None)
    label = raw.strip()
    up = label.upper()
    if STAFF_ROLE_RE.search(up):
        return ("staff", None, None)
    if ANON_RE.search(up):
        return ("anon", None, None)

    # Drop parenthetical / bracketed affiliation, then the role/affiliation that
    # follows the first comma or a " - " / " : " separator.
    name = _PAREN_RE.sub(" ", label)
    name = name.split(",")[0]
    name = _DASH_SPLIT_RE.split(name)[0]
    name = name.strip().strip(".").strip()

    # Strip leading honorifics (record the first one seen).
    honorific = None
    changed = True
    while changed and name:
        changed = False
        nu = name.upper()
        for phrase in HONORIFIC_MULTI:
            if nu.startswith(phrase + " "):
                if honorific is None:
                    honorific = phrase
                name = name[len(phrase):].strip()
                changed = True
                break
        if changed:
            continue
        parts = name.split(None, 1)
        if not parts:
            break
        head = parts[0].rstrip(".").upper()
        if head in HONORIFIC and len(parts) > 1:
            if honorific is None:
                honorific = head
            name = parts[1].strip()
            changed = True

    name = re.sub(r"\s+", " ", name).strip(" .,-")
    tokens = _ALPHA_RUN_RE.findall(name.upper())
    if not tokens:
        return ("anon", None, None)
    if all(t in GENERIC_TOKENS for t in tokens):
        return ("anon", None, None)
    return ("guest", _titlecase(name), honorific)


# ---------------------------------------------------------------------------
# Pool loading
# ---------------------------------------------------------------------------

# One provenance item is TID|YYYY-MM-DD|PROGRAM|CLUSTER|FLAG. Program names are
# NOT safe to split on ";": 243 MediaSum programs include five that contain a
# semicolon ("Q&A; WITH JIM CLANCY", "CNN&Time;", ...). So items are rebuilt by
# accumulating ";"-fragments until the accumulated text matches a whole item.
_ITEM_RE = re.compile(
    r"(?P<transcript_id>[A-Za-z][A-Za-z0-9]*-\d+)"
    r"\|(?P<date>\d{4}-\d{2}-\d{2})"
    r"\|(?P<program>.*)"
    r"\|(?P<cluster_id>cl\d+)"
    r"\|(?P<flag>[S-])\Z",
    re.DOTALL,
)

_TRUE = {"true", "1", "yes", "t"}


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE


def parse_transcripts(cell: str) -> list[dict]:
    """Parse one `transcripts` cell into typed entries.

    Returns a list of {transcript_id, date, program, cluster_id, substantive}
    in the order they appear in the cell. Raises ValueError on anything that
    does not parse, so a malformed pool can never silently shrink a split.
    """
    if cell is None:
        return []
    items: list[dict] = []
    buf: str | None = None
    for frag in str(cell).split(";"):
        buf = frag if buf is None else buf + ";" + frag
        m = _ITEM_RE.fullmatch(buf)
        if m is None:
            continue
        g = m.groupdict()
        items.append({
            "transcript_id": g["transcript_id"],
            "date": g["date"],
            "program": g["program"],
            "cluster_id": g["cluster_id"],
            "substantive": g["flag"] == "S",
        })
        buf = None
    if buf is not None and buf.strip():
        raise ValueError(f"unparsable transcripts fragment: {buf[:120]!r}")
    return items


def load_pool(path=POOL_CSV) -> list[dict]:
    """Read the Stage 2 candidate pool into typed rows.

    Every CSV column is kept as-is except the five the Stage 2 code actually
    reasons about, which are typed: clean / qualifies / ambiguous_identity
    become bools, variants becomes a list[str], transcripts becomes a list of
    typed entries (see parse_transcripts).
    """
    path = Path(path)
    # A single transcripts cell runs to a few KB; the default csv field limit is
    # 128 KB, which is enough today, but raise it so a longer-lived subject
    # cannot break the loader later.
    limit = 10 ** 7
    try:
        if csv.field_size_limit() < limit:
            csv.field_size_limit(limit)
    except OverflowError:  # pragma: no cover - platform dependent
        pass

    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            row = dict(raw)
            row["clean"] = _as_bool(raw.get("clean"))
            row["qualifies"] = _as_bool(raw.get("qualifies"))
            row["ambiguous_identity"] = _as_bool(raw.get("ambiguous_identity"))
            row["variants"] = [v.strip() for v in
                               str(raw.get("variants") or "").split(";")
                               if v.strip()]
            row["transcripts"] = parse_transcripts(raw.get("transcripts") or "")
            rows.append(row)
    return rows


def eligible_subjects(pool: list[dict]) -> list[dict]:
    """SPEC D1 eligibility: qualifies AND clean AND NOT ambiguous_identity."""
    return [r for r in pool
            if r["qualifies"] and r["clean"] and not r["ambiguous_identity"]]


# ---------------------------------------------------------------------------
# D1 — dev subject draw
# ---------------------------------------------------------------------------

def shuffled_eligible_ids(pool: list[dict], seed: int = DEV_SEED) -> list[str]:
    """The frozen shuffled order every D1 decision is read off."""
    import random

    ids = sorted(r["canonical_id"] for r in eligible_subjects(pool))
    random.Random(seed).shuffle(ids)
    return ids


def draw_dev_subjects(pool: list[dict], seed: int = DEV_SEED,
                      burned=(), burned_for_qa=(),
                      drawn_at: str | None = None) -> dict:
    """SPEC D1. Return the dev_subjects.json document.

    Two ways a subject can be found broken after the fact, both of which leave
    it burned — it is a dev subject forever and can never be reused as a donor,
    a distractor source or anything else:

    `burned` — dropped from the study entirely. It is skipped here and the next
    id of the same stratum in the shuffled order takes its slot. The subject
    count does not change.

    `burned_for_qa` — retired for one purpose but still carried. It stays in
    `subjects`, annotated `burned_for_qa: true`, and that stratum's quota goes
    up by one so the next same-stratum id in the shuffled order is ADDED. The
    subject count grows by one per retirement. Accepts a sequence of ids or a
    {canonical_id: reason} mapping.

    Every event of either kind is recorded in `replacements`, with `mode`
    saying which mechanism fired and `replaced_by` naming the id that entered
    because of it.
    """
    from datetime import date

    burned_ids = list(dict.fromkeys(burned))
    burned_set = set(burned_ids)
    qa_reasons = dict(burned_for_qa) if isinstance(burned_for_qa, dict) else \
        {cid: None for cid in dict.fromkeys(burned_for_qa)}
    if burned_set & set(qa_reasons):
        raise ValueError("a subject cannot be both dropped and retained: "
                         f"{sorted(burned_set & set(qa_reasons))}")

    order = shuffled_eligible_ids(pool, seed)
    by_id = {r["canonical_id"]: r for r in eligible_subjects(pool)}

    def stratum_of(cid: str) -> str:
        if cid not in by_id:
            raise ValueError(f"{cid} is not an eligible subject")
        return "long-tail" if by_id[cid]["wiki_status"] == "long-tail" else "wiki"

    quota = {"long-tail": N_LONGTAIL, "wiki": N_WIKI}
    for cid in burned_ids:
        stratum_of(cid)              # validate: an unknown id is a typo, not a burn
    for cid in qa_reasons:
        quota[stratum_of(cid)] += 1

    picked: list[dict] = []
    replacements: list[dict] = []
    taken = {"long-tail": 0, "wiki": 0}
    for pos, cid in enumerate(order):
        row = by_id[cid]
        stratum = "long-tail" if row["wiki_status"] == "long-tail" else "wiki"
        if taken[stratum] >= quota[stratum]:
            continue
        if cid in burned_set:
            replacements.append({
                "burned_canonical_id": cid,
                "burned_shuffle_pos": pos,
                "stratum": stratum,
                "mode": "dropped",
                "reason": None,
            })
            continue
        entry = {
            "canonical_id": cid,
            "canonical_name": row["canonical_name"],
            "wiki_status": row["wiki_status"],
            "shuffle_pos": pos,
        }
        if cid in qa_reasons:
            entry["burned_for_qa"] = True
            replacements.append({
                "burned_canonical_id": cid,
                "burned_shuffle_pos": pos,
                "stratum": stratum,
                "mode": "retained_in_place",
                "reason": qa_reasons[cid],
            })
        picked.append(entry)
        taken[stratum] += 1
        if all(taken[s] >= quota[s] for s in quota):
            break

    if any(taken[s] != quota[s] for s in quota):
        raise ValueError(
            f"pool exhausted: drew {taken['wiki']}/{quota['wiki']} wiki and "
            f"{taken['long-tail']}/{quota['long-tail']} long-tail dev subjects")

    # A dropped subject pushes its stratum's picks one slot down the shuffled
    # order; a retained one raises the quota. Either way each event adds
    # exactly one entrant at the tail of that stratum's pick list, so events
    # and tail entrants pair up in shuffled order.
    replacements.sort(key=lambda r: r["burned_shuffle_pos"])
    for stratum, size in (("long-tail", N_LONGTAIL), ("wiki", N_WIKI)):
        in_stratum = [p["canonical_id"] for p in picked
                      if (p["wiki_status"] == "long-tail") == (stratum == "long-tail")]
        events = [r for r in replacements if r["stratum"] == stratum]
        n_dropped = sum(1 for r in events if r["mode"] == "dropped")
        tail = in_stratum[size - n_dropped:]
        for i, rep in enumerate(events):
            rep["replaced_by"] = tail[i] if i < len(tail) else None

    return {
        "seed": seed,
        "rule": DRAW_RULE,
        "drawn_at": drawn_at or date.today().isoformat(),
        "n_eligible": len(order),
        "subjects": picked,
        "burned": burned_ids,
        "burned_for_qa": sorted(qa_reasons),
        "replacements": replacements,
    }


# ---------------------------------------------------------------------------
# D2 — chronological split
# ---------------------------------------------------------------------------

def _cluster_representative(entries: list[dict], guest_words: dict) -> dict:
    """Most guest words wins; ties go to the smallest transcript_id."""
    return min(entries,
               key=lambda e: (-int(guest_words.get(e["transcript_id"], 0)),
                              e["transcript_id"]))


def chronological_split(subject_row: dict, guest_words: dict | None = None,
                        titles: dict | None = None) -> dict:
    """SPEC D2. Return the split.json document for one subject.

    guest_words maps transcript_id -> guest word count and decides which
    transcript represents a multi-transcript cluster (a re-aired interview).
    The signature keeps it optional so the rule is testable on its own; the
    driver fills it from the v2 scan cache. With no counts supplied every
    transcript scores 0 and the documented tie-break (smallest transcript_id)
    decides, which is deterministic but arbitrary — the driver never does that.

    titles maps transcript_id -> transcript title, purely for the emitted
    record; missing titles come out as "".
    """
    guest_words = guest_words or {}
    titles = titles or {}

    clusters: dict[str, list[dict]] = {}
    for e in subject_row["transcripts"]:
        if e["substantive"]:
            clusters.setdefault(e["cluster_id"], []).append(e)
    if not clusters:
        raise ValueError(f"{subject_row['canonical_id']}: no substantive "
                         "transcripts to split")

    def entry(cluster_id: str) -> dict:
        members = clusters[cluster_id]
        rep = _cluster_representative(members, guest_words)
        return {
            "cluster_id": cluster_id,
            "transcript_id": rep["transcript_id"],
            "date": min(e["date"] for e in members),   # cluster date
            "program": rep["program"],
            "title": titles.get(rep["transcript_id"], ""),
            "n_transcripts_in_cluster": len(members),
            "member_dates": sorted({e["date"] for e in members}),
            "guest_words": int(guest_words.get(rep["transcript_id"], 0)),
        }

    built = [entry(cid) for cid in sorted(clusters)]
    latest = max(e["date"] for e in built)
    at_latest = sorted((e for e in built if e["date"] == latest),
                       key=lambda e: e["transcript_id"])
    test = at_latest[-1]                       # tie: largest rep id wins
    excluded = at_latest[:-1]

    # D2 hardening (SPEC v1.2): a cluster whose date is earlier still leaks if
    # ANY of its member transcripts was aired on or after the test date. Test
    # every member, not just the cluster minimum.
    grounding, late_members = [], []
    for e in built:
        if e is test or e in excluded:
            continue
        if max(e["member_dates"]) >= test["date"]:
            late_members.append(e)
        else:
            grounding.append(e)
    grounding.sort(key=lambda e: (e["date"], e["transcript_id"]))
    excluded = sorted(excluded + late_members,
                      key=lambda e: (e["date"], e["transcript_id"]))

    if not grounding:
        raise ValueError(f"{subject_row['canonical_id']}: no grounding "
                         "clusters strictly before the test date")

    return {
        "canonical_id": subject_row["canonical_id"],
        "canonical_name": subject_row["canonical_name"],
        "rule": SPLIT_RULE,
        "grounding": grounding,
        "test": test,
        "excluded_same_date": excluded,
    }


# ---------------------------------------------------------------------------
# D3 — turn extraction
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

# The fixed list of explicit role words (SPEC D3.1-r2(b)). Same words the
# origin classifier calls staff, so "registers as a person" and "is staff"
# cannot disagree. Punctuation shape alone -- "(", ",", " - " -- never counts.
_ROLE_WORD_RE = STAFF_ROLE_RE


def _drop_noise_dot_tokens(name: str) -> str:
    """SPEC D3.1-r2(a): drop non-honorific tokens ending in ".".

    MediaSum's CNN transcripts fuse a trailing fragment of the previous line
    into the speaker label: "UNMOVIC. ROTH", "UN. GREENSTOCK", "AIDS. BASSIR
    POUR". Those leading tokens are corpus noise, not first names, and left in
    they invent a new person for every fragment.

    Honorifics survive ("MR.", "DR.", "AMB."), and so do single-letter
    initials ("R. Harris"), which are real name material. Only a multi-letter
    non-honorific token ending in "." is treated as noise.
    """
    kept = []
    for token in name.split():
        stem = token.rstrip(".").upper()
        if token.endswith(".") and len(stem) >= 2 and stem not in HONORIFIC:
            continue
        kept.append(token)
    return " ".join(kept)


def _strip_honorifics(name: str) -> str:
    changed = True
    while changed and name:
        changed = False
        nu = name.upper()
        for phrase in HONORIFIC_MULTI:
            if nu.startswith(phrase + " "):
                name = name[len(phrase):].strip()
                changed = True
                break
        if changed:
            continue
        parts = name.split(None, 1)
        if not parts:
            break
        if parts[0].rstrip(".").upper() in HONORIFIC and len(parts) > 1:
            name = parts[1].strip()
            changed = True
    return name


def _name_part(raw: str) -> str:
    """The cleaned name portion of a raw speaker label (SPEC D3.1-r2(a)).

    Mirrors the stripping classify_speaker does -- parenthetical/bracketed
    blocks, everything after the first comma or a " - " / " : " separator, then
    leading honorifics -- but WITHOUT its staff/anon short-circuits, because
    D3.1 has to read a surname out of "RICHARD ROTH, CNN ANCHOR", a label
    classify_speaker answers with no name at all. On top of that it drops the
    noise dot-tokens described above.

    Note that the parenthetical strip removes stage directions as a
    side-effect: "ROTH (voice-over)" and "ROTH (on camera)" both reduce to
    "ROTH", so they are the same speaker and not three different people.
    """
    if not raw:
        return ""
    name = _PAREN_RE.sub(" ", raw.strip())
    name = name.split(",")[0]
    name = _DASH_SPLIT_RE.split(name)[0]
    # The noise drop runs before any trailing-dot trimming, so that
    # "DIPLOMATIC LICENSE." loses the whole noise token rather than just its
    # dot and then passing as a two-token name.
    name = _drop_noise_dot_tokens(name.strip())
    name = _strip_honorifics(name.strip(" .,-"))
    return re.sub(r"\s+", " ", name).strip(" .,-")


def label_tokens(raw: str) -> list[str]:
    """The cleaned, comparable name tokens of a raw speaker label."""
    return [t for t in (_token_key(t) for t in _name_part(raw).split()) if t]


def _token_key(token: str) -> str:
    """Comparison key for a single name token."""
    return re.sub(r"\s+", " ", _PUNCT_RE.sub(" ", token or "")).strip().casefold()


def name_key(name: str) -> str:
    """Comparison key for a speaker name: honorific-free, punctuation-free,
    casefolded, corpus-noise-free."""
    return " ".join(label_tokens(name))


def subject_name_keys(subject_row: dict) -> set[str]:
    """Every accepted spelling of the subject, as comparison keys."""
    names = [subject_row["canonical_name"], *subject_row.get("variants", [])]
    return {k for k in (name_key(n) for n in names) if k}


def subject_token_lists(subject_row: dict) -> list[list[str]]:
    """Every accepted spelling of the subject, as token lists."""
    names = [subject_row["canonical_name"], *subject_row.get("variants", [])]
    out, seen = [], set()
    for n in names:
        toks = label_tokens(n)
        key = " ".join(toks)
        if toks and key not in seen:
            seen.add(key)
            out.append(toks)
    return out


def _contains_run(needle: list[str], haystack: list[str]) -> bool:
    """True when `needle` appears as a contiguous run inside `haystack`."""
    n = len(needle)
    if not n or n > len(haystack):
        return False
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def name_matches_subject(tokens: list[str], subject_tokens: list[list[str]]) -> bool:
    """SPEC D3.1-r2(d): token-subsequence containment, not key equality.

    A label matches the subject when the subject's tokens appear as a
    contiguous run inside the label's tokens or vice versa, sharing at least
    two tokens. That is what makes 'AFSANE BASSIR POUR, "LE MONDE"' the same
    person as the canonical "Bassir Pour": the corpus writes the full name on
    the introduction line and the short one everywhere else.

    Exact equality still matches, so a one-token canonical name (which can
    never reach the two-token floor) is not silently unmatchable.
    """
    if not tokens:
        return False
    for subject in subject_tokens:
        if tokens == subject:
            return True
        if len(subject) >= 2 and _contains_run(subject, tokens):
            return True
        if len(tokens) >= 2 and _contains_run(tokens, subject):
            return True
    return False


def surname_registry(speaker_labels) -> dict[str, str]:
    """SPEC D3.1-r2(b)+(c). {surname key: the full label it belongs to}.

    Registration (b): a label registers only if its cleaned name part has two
    or more tokens, or the label carries an explicit role word from the fixed
    list. Punctuation shape never registers, which is what keeps
    "ROTH (voice-over)" from inventing a second Roth. Anonymous and generic
    labels never register either.

    Merge (c): a registered single-token key equal to the last token of a
    registered multi-token name is the SAME person, not an ambiguity. Real
    ambiguity is two DIFFERENT multi-token names sharing a surname, and only
    that drops the surname from the registry.

    Representative: among the labels that registered one person, the first that
    carries a role word wins, else the first seen. Preferring the role-bearing
    spelling matters -- it is the only one that tells the classifier this
    person is staff.

    The registry is built per transcript and never shared between transcripts:
    a name introduced in one interview says nothing about a bare surname in
    another.
    """
    regs = []       # (surname, name_key, is_multi, has_role, raw)
    for raw in speaker_labels:
        if classify_speaker(raw)[0] == "anon":
            continue
        tokens = label_tokens(raw)
        if not tokens:
            continue
        has_role = bool(_ROLE_WORD_RE.search((raw or "").upper()))
        if len(tokens) >= 2:
            regs.append((tokens[-1], " ".join(tokens), True, has_role, raw))
        elif has_role:
            regs.append((tokens[0], tokens[0], False, True, raw))

    out: dict[str, str] = {}
    for surname in dict.fromkeys(r[0] for r in regs):
        mine = [r for r in regs if r[0] == surname]
        multi_names = list(dict.fromkeys(r[1] for r in mine if r[2]))
        if len(multi_names) > 1:
            continue                                    # genuine ambiguity
        # At most one multi-token name is left, so every registration under
        # this surname is the same person (the merge rule) and any of them may
        # represent it. Prefer one that carries a role word: it is the only
        # spelling that tells the classifier this person is staff.
        out[surname] = next((r[4] for r in mine if r[3]), mine[0][4])
    return out


def extract_turns(record: dict, subject_row: dict) -> list[dict]:
    """SPEC D3 + D3.1-r2. One dict per utterance: transcript_id, turn_idx,
    role, speaker_label, resolved_label, text.

    role is "guest" when the speaker label resolves to the subject (the
    canonical name or any variant, matched by token containment, case- and
    honorific-insensitive), "host" when classify_speaker calls the label staff
    (host/anchor/correspondent/reporter/commentator/byline), "other" otherwise
    -- anonymous voices, soundbites and third-party guests.

    D3.1-r2: transcripts introduce a speaker once in full ("RICHARD ROTH,
    DIPLOMATIC LICENSE") and then use a bare surname ("ROTH", "ROTH
    (voice-over)") for every later turn. Before roles are assigned, a
    bare-surname label is replaced by the full label registered for that
    surname in the SAME transcript. This applies to hosts and to the subject's
    own turns alike. `resolved_label` records the substitution and is None when
    the raw label was used as-is; `speaker_label` is always the raw corpus
    label.

    Two known limits, both inherited from the origin classifier and accepted
    for the pilot:
    - A label carrying a staff marker ("ROBERT HARRIS, host") is staff to
      classify_speaker, which returns no name, so it can never match the
      subject and is labelled "host". A same-named host is an identity
      collision, not the subject speaking.
    - A named correspondent appearing as a panellist ("ANTHONY SHADID,
      NEW YORK TIMES CORRESPONDENT") is also staff, so it reads as "host"
      even when it is really a third guest. This inflates host turns on
      panel shows and is documented rather than fixed.
    """
    subject_tokens = subject_token_lists(subject_row)
    tid = record.get("id")
    utts = record.get("utt") or []
    speakers = record.get("speaker") or []
    if len(utts) != len(speakers):
        raise ValueError(f"{tid}: {len(utts)} utterances but "
                         f"{len(speakers)} speaker labels")
    registry = surname_registry(speakers)

    turns = []
    for idx, (label, text) in enumerate(zip(speakers, utts)):
        effective, resolved = label, None
        tokens = label_tokens(label)
        has_role = bool(_ROLE_WORD_RE.search((label or "").upper()))
        if len(tokens) == 1 and not has_role:
            full = registry.get(tokens[0])
            if full is not None and full != label:
                effective, resolved = full, full
                tokens = label_tokens(full)
        kind, _, _ = classify_speaker(effective)
        if kind == "guest" and name_matches_subject(tokens, subject_tokens):
            role = "guest"
        elif kind == "staff":
            role = "host"
        else:
            role = "other"
        turns.append({
            "transcript_id": tid,
            "turn_idx": idx,
            "role": role,
            "speaker_label": label,
            "resolved_label": resolved,
            "text": text,
        })
    return turns


def word_count(text: str) -> int:
    """The pilot's token proxy: whitespace tokens (SPEC D5)."""
    return len((text or "").split())


# ---------------------------------------------------------------------------
# Corpus access
# ---------------------------------------------------------------------------

# news_dialogue.json is one 4.45 GB JSON array of flat records, serialized with
# a space after every ": ". Every record therefore begins with the byte string
# b'{"id": "' and — because a quote inside a JSON string is escaped as \" — that
# byte string cannot occur anywhere else. Verified on the real file: the marker
# occurs 463,596 times, exactly the record count the v2 scan recorded.
#
# So instead of json-decoding all 463k records (mediasum_index.stream_records,
# ~15 min) we scan for the marker in bytes and decode only the records asked
# for. Same single pass, same result, ~10 s. Every decoded record's id is
# asserted against the id read from the marker, and a missing id is an error.
_ID_MARKER = b'{"id": "'


def iter_wanted_raw(path, wanted: set[str], chunk_bytes: int = 32 * 1024 * 1024):
    """Yield (transcript_id, raw_json_bytes) for ids in `wanted`, one pass.

    A record runs from its own marker up to the next record's marker, so the
    scanner always holds at most one chunk plus one record in memory and stops
    reading as soon as the last wanted id has been emitted.
    """
    remaining = set(wanted)
    if not remaining:
        return
    mark_len = len(_ID_MARKER)
    buf = b""
    cur_id = None       # id of the record we are currently inside
    cur_at = 0          # index in buf where that record starts
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_bytes)
            if not chunk:
                break
            buf += chunk
            search_from = cur_at + mark_len if cur_id is not None else 0
            partial_at = None
            while True:
                i = buf.find(_ID_MARKER, search_from)
                if i == -1:
                    break
                j = buf.find(b'"', i + mark_len)
                if j == -1:
                    partial_at = i             # id straddles the chunk seam
                    break
                rid = buf[i + mark_len:j].decode("utf-8", "replace")
                if cur_id is not None and cur_id in remaining:
                    yield cur_id, buf[cur_at:i]
                    remaining.discard(cur_id)
                    if not remaining:
                        return
                cur_id, cur_at = rid, i
                search_from = i + mark_len
            # Drop everything the scanner can never need again.
            if cur_id is not None:
                keep_from = cur_at
            elif partial_at is not None:
                keep_from = partial_at
            else:
                keep_from = max(0, len(buf) - mark_len)
            if keep_from:
                buf = buf[keep_from:]
                if cur_id is not None:
                    cur_at = 0
    if cur_id is not None and cur_id in remaining:
        yield cur_id, buf[cur_at:]


def fetch_records(transcript_ids, path=RAW_JSON) -> dict[str, dict]:
    """Pull the named transcripts out of news_dialogue.json in ONE pass.

    Returns {transcript_id: record}. Raises KeyError if any id is missing, so a
    silently short split is impossible.

    The v2 scan cache (data/mediasum_index/_scan_cache_v2.pkl) was checked
    first and does NOT hold records or byte offsets — only per-transcript
    program/title/n_utts, speaker labels and word counts — so the corpus pass
    is unavoidable for utterance text.
    """
    wanted = set(transcript_ids)
    decoder = json.JSONDecoder()
    out: dict[str, dict] = {}
    for rid, raw in iter_wanted_raw(path, wanted):
        text = raw.decode("utf-8")
        record, _ = decoder.raw_decode(text)
        if record.get("id") != rid:
            raise ValueError(f"record boundary error: marker said {rid}, "
                             f"decoded {record.get('id')}")
        out[rid] = record
    missing = wanted - set(out)
    if missing:
        raise KeyError(f"transcripts not found in {path}: "
                       f"{sorted(missing)[:10]}")
    return out


def load_guest_words(subject_rows, cache_path=SCAN_CACHE) -> dict[str, dict[str, int]]:
    """{canonical_id: {transcript_id: guest words}} from the v2 scan cache.

    The cache's `stats` maps (normalized speaker name, transcript_id) ->
    [words, turns]; a subject's words for a transcript is the sum over its
    canonical_name and every variant. Used to pick the representative
    transcript of a re-aired cluster without re-reading the corpus.

    Names are de-duplicated first: the pool's `variants` column normally
    repeats the canonical_name, and summing the same key twice would double
    every count.
    """
    import pickle

    with open(cache_path, "rb") as fh:
        cache = pickle.load(fh)
    stats = cache["stats"]
    out: dict[str, dict[str, int]] = {}
    for row in subject_rows:
        names = list(dict.fromkeys(
            [row["canonical_name"], *row.get("variants", [])]))
        per_tid: dict[str, int] = {}
        for e in row["transcripts"]:
            tid = e["transcript_id"]
            per_tid[tid] = sum(int(stats.get((n, tid), (0, 0))[0]) for n in names)
        out[row["canonical_id"]] = per_tid
    return out


def load_titles(transcript_ids, cache_path=SCAN_CACHE) -> dict[str, str]:
    """{transcript_id: title} from the v2 scan cache (records are authoritative)."""
    import pickle

    with open(cache_path, "rb") as fh:
        cache = pickle.load(fh)
    info = cache["tid_info"]
    return {tid: (info[tid][1] if tid in info else "") for tid in transcript_ids}


# ---------------------------------------------------------------------------
# Pilot layout helpers
# ---------------------------------------------------------------------------

def subject_dir(canonical_id: str, pilot_dir=PILOT_DIR) -> Path:
    return Path(pilot_dir) / "subjects" / canonical_id


def write_jsonl(path, rows) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_json(path, doc) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def load_dev_subjects(pilot_dir=PILOT_DIR) -> dict:
    """Read the committed draw. Never re-draw it."""
    path = Path(pilot_dir) / "dev_subjects.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc["seed"] != DEV_SEED:
        raise SystemExit(f"[fatal] dev_subjects.json seed is {doc['seed']}, "
                         f"expected {DEV_SEED}")
    n = len(doc["subjects"])
    # One extra subject per retained-in-place retirement, and no other way to
    # end up with a count other than 5.
    expected = N_WIKI + N_LONGTAIL + sum(1 for s in doc["subjects"]
                                         if s.get("burned_for_qa"))
    if n != expected:
        raise SystemExit(f"[fatal] dev_subjects.json has {n} subjects, "
                         f"expected {expected}")
    return doc


def load_split(canonical_id: str, pilot_dir=PILOT_DIR) -> dict:
    path = subject_dir(canonical_id, pilot_dir) / "split.json"
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "ROOT", "POOL_CSV", "RAW_JSON", "SCAN_CACHE", "PILOT_DIR",
    "DEV_SEED", "DRAW_RULE", "SPLIT_RULE",
    "classify_speaker", "parse_transcripts", "load_pool", "eligible_subjects",
    "shuffled_eligible_ids", "draw_dev_subjects", "chronological_split",
    "name_key", "subject_name_keys", "subject_token_lists", "label_tokens",
    "name_matches_subject", "surname_registry", "extract_turns", "word_count",
    "fetch_records", "iter_wanted_raw", "load_guest_words", "load_titles",
    "subject_dir", "write_jsonl", "read_jsonl", "write_json",
    "load_dev_subjects", "load_split",
]
