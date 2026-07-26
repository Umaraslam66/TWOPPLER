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
    "stratum in the same shuffled order. shuffle_pos is the 0-based position "
    "of each pick in that shuffled order."
)

SPLIT_RULE = (
    "Substantive transcripts only (flag S in the pool's transcripts column), "
    "grouped by cluster_id (one cluster = one real interview event; re-airings "
    "share a cluster). Cluster date = earliest transcript date in the cluster. "
    "Cluster representative = the transcript with the most guest words, ties "
    "broken by lexicographically smallest transcript_id. test = the cluster "
    "with the latest date; a tie for latest is broken by representative "
    "transcript_id lexicographic order, largest wins. grounding = every "
    "cluster dated strictly earlier. Any other cluster sharing the test date "
    "is excluded entirely (same-event leak guard)."
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
                      burned=(), drawn_at: str | None = None) -> dict:
    """SPEC D1. Return the dev_subjects.json document.

    `burned` is the list of canonical_ids that were drawn by an earlier run and
    later found broken (identity collision etc.). They stay dev subjects
    forever — they are never re-usable elsewhere — but they are skipped here and
    replaced by the next id of the same stratum in the same shuffled order.
    Every such event is recorded in the returned document.
    """
    from datetime import date

    burned_ids = list(dict.fromkeys(burned))
    burned_set = set(burned_ids)
    order = shuffled_eligible_ids(pool, seed)
    by_id = {r["canonical_id"]: r for r in eligible_subjects(pool)}

    picked: list[dict] = []
    replacements: list[dict] = []
    n_wiki = n_lt = 0
    for pos, cid in enumerate(order):
        row = by_id[cid]
        long_tail = row["wiki_status"] == "long-tail"
        want = (long_tail and n_lt < N_LONGTAIL) or \
               (not long_tail and n_wiki < N_WIKI)
        if not want:
            continue
        if cid in burned_set:
            replacements.append({
                "burned_canonical_id": cid,
                "burned_shuffle_pos": pos,
                "stratum": "long-tail" if long_tail else "wiki",
            })
            continue
        picked.append({
            "canonical_id": cid,
            "canonical_name": row["canonical_name"],
            "wiki_status": row["wiki_status"],
            "shuffle_pos": pos,
        })
        if long_tail:
            n_lt += 1
        else:
            n_wiki += 1
        if n_wiki == N_WIKI and n_lt == N_LONGTAIL:
            break

    if n_wiki != N_WIKI or n_lt != N_LONGTAIL:
        raise ValueError(
            f"pool exhausted: drew {n_wiki}/{N_WIKI} wiki and "
            f"{n_lt}/{N_LONGTAIL} long-tail dev subjects")

    # Each burn pushes that stratum's picks one slot further down the shuffled
    # order, so the i-th burn's replacement is the i-th of the extra entrants
    # at the tail of that stratum's pick list.
    for stratum, size in (("long-tail", N_LONGTAIL), ("wiki", N_WIKI)):
        in_stratum = [p["canonical_id"] for p in picked
                      if (p["wiki_status"] == "long-tail") == (stratum == "long-tail")]
        burns = [r for r in replacements if r["stratum"] == stratum]
        for i, rep in enumerate(burns):
            k = size - len(burns) + i
            rep["replaced_by"] = in_stratum[k] if 0 <= k < len(in_stratum) else None

    return {
        "seed": seed,
        "rule": DRAW_RULE,
        "drawn_at": drawn_at or date.today().isoformat(),
        "n_eligible": len(order),
        "subjects": picked,
        "burned": burned_ids,
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
            "guest_words": int(guest_words.get(rep["transcript_id"], 0)),
        }

    built = [entry(cid) for cid in sorted(clusters)]
    latest = max(e["date"] for e in built)
    at_latest = sorted((e for e in built if e["date"] == latest),
                       key=lambda e: e["transcript_id"])
    test = at_latest[-1]                       # tie: largest rep id wins
    excluded = at_latest[:-1]
    grounding = sorted((e for e in built if e["date"] < latest),
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


def name_key(name: str) -> str:
    """Comparison key for speaker names: honorific-free, punctuation-free, casefolded."""
    if not name:
        return ""
    _, normalized, _ = classify_speaker(name)
    base = normalized if normalized else name
    base = _PUNCT_RE.sub(" ", base)
    return re.sub(r"\s+", " ", base).strip().casefold()


def subject_name_keys(subject_row: dict) -> set[str]:
    """Every accepted spelling of the subject, as comparison keys."""
    names = [subject_row["canonical_name"], *subject_row.get("variants", [])]
    return {k for k in (name_key(n) for n in names) if k}


def _token_key(token: str) -> str:
    """Comparison key for a single name token."""
    return re.sub(r"\s+", " ", _PUNCT_RE.sub(" ", token or "")).strip().casefold()


# A label "carries a role descriptor" when it appends an affiliation or a role
# to the name: a parenthetical/bracketed block, anything after the first comma,
# a " - "/" : " separator, or one of the staff role words.
_ROLE_SEP_RE = re.compile(r"[,(\[]")


def _name_part(raw: str) -> str:
    """The name portion of a raw speaker label.

    Mirrors the stripping classify_speaker does — parenthetical affiliation,
    everything after the first comma or a " - " / " : " separator, then leading
    honorifics — but WITHOUT its staff/anon short-circuits, because D3.1 has to
    read a surname out of "RICHARD ROTH, CNN ANCHOR", a label classify_speaker
    answers with no name at all.
    """
    if not raw:
        return ""
    name = _PAREN_RE.sub(" ", raw.strip())
    name = name.split(",")[0]
    name = _DASH_SPLIT_RE.split(name)[0]
    name = name.strip().strip(".").strip()
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
    return re.sub(r"\s+", " ", name).strip(" .,-")


def _label_shape(raw: str) -> tuple[list[str], bool]:
    """(name tokens, carries a role descriptor) for one raw speaker label."""
    tokens = _name_part(raw).split()
    up = (raw or "").upper()
    has_role = bool(STAFF_ROLE_RE.search(up)) or bool(_ROLE_SEP_RE.search(raw or "")) \
        or bool(_DASH_SPLIT_RE.search(raw or ""))
    return tokens, has_role


def surname_registry(speaker_labels) -> dict[str, str]:
    """SPEC D3.1. {surname key: the full label that surname belongs to}.

    A label is registered when it carries a role descriptor or a multi-token
    name — i.e. when it introduces a person properly. Anonymous and generic
    labels ("UNIDENTIFIED MAN", "MALE VOICE") are never registered.

    A surname is only usable if exactly one distinct person registered it;
    when two speakers share a surname it is dropped from the registry and the
    bare label stays unresolved. Where one person registered several spellings,
    the first one seen in the transcript is the representative.

    The registry is built per transcript and is never shared between
    transcripts — a name introduced in one interview says nothing about a bare
    surname in another.
    """
    by_surname: dict[str, dict[str, str]] = {}
    for raw in speaker_labels:
        if classify_speaker(raw)[0] == "anon":
            continue
        tokens, has_role = _label_shape(raw)
        if not tokens or (len(tokens) < 2 and not has_role):
            continue
        surname = _token_key(tokens[-1])
        if not surname:
            continue
        by_surname.setdefault(surname, {}).setdefault(
            name_key(" ".join(tokens)), raw)
    return {s: next(iter(v.values()))
            for s, v in by_surname.items() if len(v) == 1}


def extract_turns(record: dict, subject_row: dict) -> list[dict]:
    """SPEC D3 + D3.1. One dict per utterance: transcript_id, turn_idx, role,
    speaker_label, resolved_label, text.

    role is "guest" when the speaker label resolves to the subject
    (canonical_name or any variant, case-insensitive and honorific-tolerant),
    "host" when classify_speaker calls the label staff (host/anchor/
    correspondent/reporter/commentator/byline), "other" otherwise —
    anonymous voices, soundbites and third-party guests.

    D3.1: transcripts routinely introduce a speaker once in full
    ("RICHARD ROTH, CNN ANCHOR") and then use a bare surname ("ROTH") for
    every later turn. Before roles are assigned, a bare-surname label is
    replaced by the full label registered for that surname earlier in the SAME
    transcript, when exactly one person registered it. This applies to hosts
    and to the subject's own turns alike. `resolved_label` records the
    substitution and is None when the raw label was used as-is;
    `speaker_label` is always the raw label from the corpus.

    Note the one place this differs from a literal reading of D3: a label that
    carries a staff marker ("ROBERT HARRIS, host") is classified staff by
    classify_speaker, which returns no name, so it can never match the subject
    and is labelled "host". That is deliberate — a same-named host is an
    identity collision, not the subject speaking.
    """
    keys = subject_name_keys(subject_row)
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
        tokens, has_role = _label_shape(label)
        if len(tokens) == 1 and not has_role:
            full = registry.get(_token_key(tokens[0]))
            if full is not None and full != label:
                effective, resolved = full, full
        kind, normalized, _ = classify_speaker(effective)
        if normalized is not None and name_key(normalized) in keys:
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
    if n != N_WIKI + N_LONGTAIL:
        raise SystemExit(f"[fatal] dev_subjects.json has {n} subjects, "
                         f"expected {N_WIKI + N_LONGTAIL}")
    return doc


def load_split(canonical_id: str, pilot_dir=PILOT_DIR) -> dict:
    path = subject_dir(canonical_id, pilot_dir) / "split.json"
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "ROOT", "POOL_CSV", "RAW_JSON", "SCAN_CACHE", "PILOT_DIR",
    "DEV_SEED", "DRAW_RULE", "SPLIT_RULE",
    "classify_speaker", "parse_transcripts", "load_pool", "eligible_subjects",
    "shuffled_eligible_ids", "draw_dev_subjects", "chronological_split",
    "name_key", "subject_name_keys", "surname_registry", "extract_turns",
    "word_count",
    "fetch_records", "iter_wanted_raw", "load_guest_words", "load_titles",
    "subject_dir", "write_jsonl", "read_jsonl", "write_json",
    "load_dev_subjects", "load_split",
]
