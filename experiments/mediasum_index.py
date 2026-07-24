"""MediaSum guest-level index — Stage 2 corpus feasibility recon (DOPPLER).

Answers one question: does MediaSum contain enough recurring interview guests
to run the Stage 2 study (target >= 30 subjects with >= 3 substantive
interviews each, biased long-tail)?

What it does:
  1. Streams the ~4.45 GB news_dialogue.json (single JSON array) with low
     memory.
  2. Classifies every speaker label as guest / staff / anonymous.
  3. Aggregates per normalized guest name (transcripts, words, turns, dates,
     programs).
  4. Applies a >100-transcript catch-all to drop hosts the regex missed.
  5. Computes the headline distribution and the key number
     (>= 3 transcripts AND >= 2000 guest words).
  6. Flags the key-filter candidates as long-tail via the Wikipedia API.
  7. Writes two CSVs and a markdown report.

Run end-to-end:   uv run python experiments/mediasum_index.py
Data prep (once): the raw file is a deflate64 zip that stdlib/unzip/ditto
cannot open. See data/mediasum/extract_deflate64.py (uses the `inflate64`
wheel). ensure_data() below will attempt that extraction automatically if the
JSON is missing and inflate64 is available.

No paid/LLM API is used. Wikipedia's free API is the only network call.
"""
import csv
import json
import os
import re
import struct
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = "/Users/umaraslam/Projects/DOPPLER"
RAW_JSON = os.path.join(ROOT, "data/mediasum/news_dialogue.json")
RAW_ZIP = os.path.join(ROOT, "data/mediasum/mediasum.zip")
OUT_DIR = os.path.join(ROOT, "data/mediasum_index")
INDEX_CSV = os.path.join(OUT_DIR, "guest_index.csv")
INTERVIEWS_CSV = os.path.join(OUT_DIR, "guest_interviews.csv")
REPORT_MD = os.path.join(ROOT, "results/stage2_corpus_recon_index.md")

SOURCE_URL = ("https://drive.google.com/file/d/"
              "1ZAKZM1cGhEw2A4_n4bGGMYyF8iPjLZni/view "
              "(linked from github.com/zcgzcgzcg1/MediaSum)")
ZIP_SHA256 = "9a72373725938d217bb97762258cc13bc76abd51ce2a9ddff5fdabd2ebcb82bb"
JSON_SHA256 = "b0b79d3f2c240a4f15dd32e1839d91cfee878c43aa3cd7a7be7a8282572aeef3"

# Key thresholds (frozen by the task spec)
KEY_MIN_TRANSCRIPTS = 3
KEY_MIN_WORDS = 2000
SUBST_MIN_WORDS = 300     # a "substantive appearance": per-transcript
SUBST_MIN_TURNS = 5
STAFF_CATCHALL_TRANSCRIPTS = 100   # >100 distinct transcripts => treat as staff
WIKI_MAX_CANDIDATES = 2000

WIKI_UA = "DOPPLER-research-recon/0.1 (contact: aslamumar012@gmail.com)"

# ----------------------------------------------------------------------------
# Speaker classification
# ----------------------------------------------------------------------------
# NPR/CNN staff role markers (task-specified). Word-boundary match on the whole
# uppercased label. Conservative: excluding a few real guests whose affiliation
# literally contains one of these words only shrinks the candidate pool (safe
# direction for a feasibility count).
STAFF_ROLE_RE = re.compile(
    r"\b(HOST|ANCHOR|CORRESPONDENT|BYLINE|REPORTER|COMMENTATOR)\b")

# Anonymous / unknown speakers.
ANON_RE = re.compile(r"\b(UNIDENTIFIED|UNIDENTIFED|UNKNOWN|UNIDENTIFY\w*)\b")

# Honorifics/titles stripped from the front of a name (recorded as signal).
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

# Generic / collective labels that are not a single named guest.
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


def _titlecase(s):
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


# ----------------------------------------------------------------------------
# Streaming JSON-array reader (file is one big array, ~4.45 GB)
# ----------------------------------------------------------------------------
def stream_records(path, chunk_bytes=64 * 1024 * 1024):
    dec = json.JSONDecoder()
    ws = " \t\r\n,"
    with open(path, "r", encoding="utf-8") as f:
        buf = ""
        started = False
        done = False
        while not done:
            chunk = f.read(chunk_bytes)
            if chunk:
                buf += chunk
            else:
                done = True
            if not started:
                lb = buf.find("[")
                if lb == -1:
                    if done:
                        return
                    continue
                buf = buf[lb + 1:]
                started = True
            while True:
                i = 0
                n = len(buf)
                while i < n and buf[i] in ws:
                    i += 1
                if i:
                    buf = buf[i:]
                if not buf:
                    break
                if buf[0] == "]":
                    return
                try:
                    obj, end = dec.raw_decode(buf)
                except json.JSONDecodeError:
                    if done:
                        # Trailing garbage / truncation; stop cleanly.
                        return
                    break  # need more bytes
                yield obj
                buf = buf[end:]


# ----------------------------------------------------------------------------
# Date helpers
# ----------------------------------------------------------------------------
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def parse_date(s):
    """Return an integer ordinal (days) for a YYYY-MM-DD date, else None."""
    if not s or not isinstance(s, str):
        return None
    m = _DATE_RE.match(s.strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    import datetime
    try:
        return datetime.date(y, mo, d).toordinal()
    except ValueError:
        return None


def ord_to_str(o):
    import datetime
    return datetime.date.fromordinal(o).isoformat() if o is not None else ""


# ----------------------------------------------------------------------------
# Common-name heuristic (rough collision flag)
# ----------------------------------------------------------------------------
COMMON_FIRST = {
    "JAMES", "JOHN", "ROBERT", "MICHAEL", "WILLIAM", "DAVID", "RICHARD",
    "JOSEPH", "THOMAS", "CHARLES", "CHRISTOPHER", "DANIEL", "MATTHEW",
    "ANTHONY", "MARK", "DONALD", "STEVEN", "PAUL", "ANDREW", "JOSHUA",
    "KENNETH", "KEVIN", "BRIAN", "GEORGE", "EDWARD", "RONALD", "TIMOTHY",
    "JASON", "JEFFREY", "RYAN", "JACOB", "GARY", "NICHOLAS", "ERIC",
    "JONATHAN", "STEPHEN", "LARRY", "JUSTIN", "SCOTT", "BRANDON", "FRANK",
    "BENJAMIN", "GREGORY", "SAMUEL", "RAYMOND", "PATRICK", "ALEXANDER",
    "JACK", "DENNIS", "JERRY", "TOM", "PETER", "MARY", "PATRICIA", "JENNIFER",
    "LINDA", "ELIZABETH", "BARBARA", "SUSAN", "JESSICA", "SARAH", "KAREN",
    "NANCY", "LISA", "MARGARET", "BETTY", "SANDRA", "ASHLEY", "KIMBERLY",
    "EMILY", "DONNA", "MICHELLE", "DOROTHY", "CAROL", "AMANDA", "MELISSA",
    "DEBORAH", "STEPHANIE", "REBECCA", "SHARON", "LAURA", "CYNTHIA", "AMY",
    "KATHLEEN", "ANGELA", "SHIRLEY", "ANNA", "BRENDA", "PAMELA", "NICOLE",
    "RUTH", "KATHERINE", "CHRISTINE", "HELEN", "DEBRA", "RACHEL", "JOAN",
    "BOB", "BILL", "JIM", "MIKE", "STEVE", "DAN", "DAVE", "TONY", "CHRIS",
}
COMMON_LAST = {
    "SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES", "GARCIA", "MILLER",
    "DAVIS", "RODRIGUEZ", "MARTINEZ", "HERNANDEZ", "LOPEZ", "GONZALEZ",
    "WILSON", "ANDERSON", "THOMAS", "TAYLOR", "MOORE", "JACKSON", "MARTIN",
    "LEE", "PEREZ", "THOMPSON", "WHITE", "HARRIS", "SANCHEZ", "CLARK",
    "RAMIREZ", "LEWIS", "ROBINSON", "WALKER", "YOUNG", "ALLEN", "KING",
    "WRIGHT", "SCOTT", "TORRES", "NGUYEN", "HILL", "FLORES", "GREEN",
    "ADAMS", "NELSON", "BAKER", "HALL", "RIVERA", "CAMPBELL", "MITCHELL",
    "CARTER", "ROBERTS", "GOMEZ", "PHILLIPS", "EVANS", "TURNER", "DIAZ",
    "PARKER", "CRUZ", "EDWARDS", "COLLINS", "REYES", "STEWART", "MORRIS",
    "MORALES", "MURPHY", "COOK", "ROGERS", "GUTIERREZ", "ORTIZ", "MORGAN",
    "COOPER", "PETERSON", "BAILEY", "REED", "KELLY", "HOWARD", "RAMOS",
    "KIM", "COX", "WARD", "RICHARDSON", "WATSON", "BROOKS", "CHAVEZ", "WOOD",
    "JAMES", "BENNETT", "GRAY", "MENDOZA", "RUIZ", "HUGHES", "PRICE",
    "ALVAREZ", "CASTILLO", "SANDERS", "PATEL", "MYERS", "LONG", "ROSS",
    "FOSTER", "POWELL", "JENKINS", "PERRY", "RUSSELL", "SULLIVAN", "BELL",
    "COLEMAN", "BUTLER", "HENDERSON", "BARNES", "GONZALES", "FISHER",
}


def generic_name_flag(norm_name):
    toks = norm_name.upper().split()
    if len(toks) < 2:
        return False
    return toks[0] in COMMON_FIRST and toks[-1] in COMMON_LAST


# ----------------------------------------------------------------------------
# Data availability
# ----------------------------------------------------------------------------
def ensure_data():
    if os.path.exists(RAW_JSON) and os.path.getsize(RAW_JSON) > 1_000_000_000:
        return
    if not os.path.exists(RAW_ZIP):
        sys.exit(
            f"Missing {RAW_JSON} and {RAW_ZIP}.\n"
            "Download first:\n"
            "  uvx gdown 1ZAKZM1cGhEw2A4_n4bGGMYyF8iPjLZni "
            "-O data/mediasum/mediasum.zip\n"
            "then re-run (or run data/mediasum/extract_deflate64.py).")
    try:
        import zipfile
        import inflate64
    except ImportError:
        sys.exit(
            "news_dialogue.json is missing and it is a deflate64 zip that "
            "stdlib cannot open. Install the extraction helper wheel:\n"
            "  uv pip install inflate64\n"
            "then run: python data/mediasum/extract_deflate64.py")
    print("Extracting news_dialogue.json from deflate64 zip ...")
    with zipfile.ZipFile(RAW_ZIP) as zf:
        info = zf.getinfo("news_dialogue.json")
    with open(RAW_ZIP, "rb") as fz:
        fz.seek(info.header_offset)
        local = fz.read(30)
        fname_len = struct.unpack("<H", local[26:28])[0]
        extra_len = struct.unpack("<H", local[28:30])[0]
        fz.seek(info.header_offset + 30 + fname_len + extra_len)
        remaining = info.compress_size
        infl = inflate64.Inflater()
        with open(RAW_JSON, "wb") as fo:
            while remaining > 0:
                b = fz.read(min(16 * 1024 * 1024, remaining))
                if not b:
                    break
                remaining -= len(b)
                out = infl.inflate(b)
                if out:
                    fo.write(out)


# ----------------------------------------------------------------------------
# Main aggregation
# ----------------------------------------------------------------------------
def build():
    ensure_data()
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    # guests[name] = {tid: [words, turns]}
    guests = defaultdict(dict)
    # tmeta[tid] = [date_ord, program, title, total_turns]
    tmeta = {}
    honorifics = defaultdict(set)          # name -> set of honorifics seen
    raw_map = {}                           # raw label -> normalized (guests)
    speaker_cache = {}                     # raw -> (kind, name, honorific)

    n_records = 0
    n_bad = 0
    n_utt = 0
    prog_counter = defaultdict(int)
    id_prefix_counter = defaultdict(int)

    for rec in stream_records(RAW_JSON):
        n_records += 1
        if n_records % 50000 == 0:
            print(f"  ...{n_records} records ({time.time()-t0:.0f}s)")
        try:
            tid = rec["id"]
            utt = rec.get("utt") or []
            spk = rec.get("speaker") or []
        except (TypeError, KeyError):
            n_bad += 1
            continue
        program = (rec.get("program") or "").strip()
        title = (rec.get("title") or "").strip()
        date_ord = parse_date(rec.get("date"))
        total_turns = len(utt)
        prog_counter[program] += 1
        id_prefix_counter[str(tid).split("-")[0]] += 1

        m = min(len(utt), len(spk))
        if len(utt) != len(spk):
            n_bad += 1  # count mismatched records but still use overlap
        n_utt += m

        # accumulate this transcript's guest contributions
        local_guest = {}   # name -> [words, turns]
        for i in range(m):
            raw = spk[i]
            cached = speaker_cache.get(raw)
            if cached is None:
                cached = classify_speaker(raw)
                speaker_cache[raw] = cached
            kind, name, hon = cached
            if kind != "guest":
                continue
            text = utt[i] or ""
            w = len(text.split())
            slot = local_guest.get(name)
            if slot is None:
                local_guest[name] = [w, 1]
            else:
                slot[0] += w
                slot[1] += 1
            if hon:
                honorifics[name].add(hon)
            if raw not in raw_map:
                raw_map[raw] = name

        if local_guest:
            tmeta[tid] = [date_ord, program, title, total_turns]
            for name, (w, turns) in local_guest.items():
                guests[name][tid] = [w, turns]

    parse_secs = time.time() - t0
    print(f"Parsed {n_records} records, {n_utt} utterances in {parse_secs:.0f}s")

    # ---- staff catch-all: >100 distinct transcripts ----
    catchall_removed = []
    for name in list(guests.keys()):
        if len(guests[name]) > STAFF_CATCHALL_TRANSCRIPTS:
            catchall_removed.append((name, len(guests[name])))
            del guests[name]
    catchall_removed.sort(key=lambda x: -x[1])

    # ---- per-guest aggregation ----
    rows = []  # dicts
    hist = {1: 0, 2: 0, 3: 0, 4: 0, "5+": 0}
    for name, tmap in guests.items():
        n_t = len(tmap)
        total_words = sum(v[0] for v in tmap.values())
        total_turns = sum(v[1] for v in tmap.values())
        dates = [tmeta[t][0] for t in tmap if tmeta[t][0] is not None]
        n_dates = len(dates)
        first_o = min(dates) if dates else None
        last_o = max(dates) if dates else None
        span = (last_o - first_o) if (first_o is not None) else None
        progs = set(tmeta[t][1] for t in tmap if tmeta[t][1])
        # substantive appearances
        subst = sum(1 for v in tmap.values()
                    if v[0] >= SUBST_MIN_WORDS and v[1] >= SUBST_MIN_TURNS)
        passes_key = (n_t >= KEY_MIN_TRANSCRIPTS and total_words >= KEY_MIN_WORDS)
        example_ids = list(tmap.keys())[:5]
        titles = [tmeta[t][2] for t in list(tmap.keys())[:3] if tmeta[t][2]]
        rows.append({
            "name": name,
            "n_transcripts": n_t,
            "total_guest_words": total_words,
            "n_turns_total": total_turns,
            "n_dates": n_dates,
            "first_ord": first_o,
            "last_ord": last_o,
            "span_days": span,
            "n_programs": len(progs),
            "programs": sorted(progs)[:5],
            "subst_appearances": subst,
            "passes_key": passes_key,
            "example_ids": example_ids,
            "titles": titles,
            "honorifics": sorted(honorifics.get(name, [])),
            "generic_name": generic_name_flag(name),
            "wiki_page_exists": None,
        })
        b = n_t if n_t < 5 else "5+"
        hist[b] += 1

    # ---- distribution / key number / supplementary cuts ----
    candidates = [r for r in rows if r["passes_key"]]
    candidates.sort(key=lambda r: -r["total_guest_words"])
    key_number = len(candidates)

    cut_subst3 = sum(1 for r in rows if r["subst_appearances"] >= 3)
    cut_4 = sum(1 for r in rows if r["n_transcripts"] >= 4)
    cut_5 = sum(1 for r in rows if r["n_transcripts"] >= 5)
    cand_span180 = sum(1 for r in candidates
                       if r["span_days"] is not None and r["span_days"] >= 180)
    cand_dates3 = sum(1 for r in candidates if r["n_dates"] >= 3)
    cand_generic = sum(1 for r in candidates if r["generic_name"])

    stats = {
        "n_records": n_records,
        "n_bad": n_bad,
        "n_utt": n_utt,
        "parse_secs": parse_secs,
        "n_distinct_guests": len(rows),
        "n_distinct_raw_guest_labels": len(raw_map),
        "catchall_removed": catchall_removed,
        "hist": hist,
        "key_number": key_number,
        "cut_subst3": cut_subst3,
        "cut_4": cut_4,
        "cut_5": cut_5,
        "cand_span180": cand_span180,
        "cand_dates3": cand_dates3,
        "cand_generic": cand_generic,
        "prog_counter": prog_counter,
        "id_prefix_counter": dict(id_prefix_counter),
        "_guests_tmap": guests,
        "_tmeta": tmeta,
    }
    return rows, candidates, stats


# ----------------------------------------------------------------------------
# Wikipedia long-tail flag
# ----------------------------------------------------------------------------
def wiki_check(names):
    """Return {name: True/False} — True if an exact-title page exists."""
    result = {}
    checked = names[:WIKI_MAX_CANDIDATES]
    for start in range(0, len(checked), 50):
        batch = checked[start:start + 50]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "redirects": 1,
            "format": "json",
        }
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  wiki batch {start//50} failed: {e}")
            time.sleep(2)
            continue
        q = data.get("query", {})
        norm = {d["from"]: d["to"] for d in q.get("normalized", [])}
        redir = {d["from"]: d["to"] for d in q.get("redirects", [])}
        pages = q.get("pages", {})
        by_title = {}
        for p in pages.values():
            by_title[p.get("title", "")] = ("missing" not in p)
        by_title_ci = {k.lower(): v for k, v in by_title.items()}
        for name in batch:
            t = norm.get(name, name)
            t = redir.get(t, t)
            exists = by_title.get(t)
            if exists is None:
                exists = by_title_ci.get(t.lower())
            result[name] = bool(exists) if exists is not None else False
        time.sleep(1.1)
        print(f"  wiki {min(start+50, len(checked))}/{len(checked)}")
    return result


# ----------------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------------
def write_index_csv(rows):
    rows_sorted = sorted(rows, key=lambda r: (-r["total_guest_words"], r["name"]))
    with open(INDEX_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "normalized_name", "n_transcripts", "total_guest_words",
            "n_turns_total", "first_date", "last_date", "span_days",
            "n_programs", "n_dates", "subst_appearances", "passes_key_filter",
            "wiki_page_exists", "generic_name_flag", "honorifics",
            "example_transcript_ids",
        ])
        for r in rows_sorted:
            w.writerow([
                r["name"], r["n_transcripts"], r["total_guest_words"],
                r["n_turns_total"], ord_to_str(r["first_ord"]),
                ord_to_str(r["last_ord"]),
                "" if r["span_days"] is None else r["span_days"],
                r["n_programs"], r["n_dates"], r["subst_appearances"],
                int(r["passes_key"]),
                "" if r["wiki_page_exists"] is None else int(r["wiki_page_exists"]),
                int(r["generic_name"]), ";".join(r["honorifics"]),
                ";".join(r["example_ids"]),
            ])


def write_interviews_csv(rows, guests_tmap, tmeta):
    # One row per (guest, transcript), restricted to recurring guests
    # (n_transcripts >= 2) to keep the file bounded and analytically useful.
    with open(INTERVIEWS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "normalized_name", "transcript_id", "date", "program", "title",
            "guest_words", "guest_turns", "total_turns_in_transcript",
        ])
        for r in rows:
            if r["n_transcripts"] < 2:
                continue
            name = r["name"]
            for tid, (gw, gt) in guests_tmap[name].items():
                date_o, program, title, total_turns = tmeta[tid]
                w.writerow([name, tid, ord_to_str(date_o), program, title,
                            gw, gt, total_turns])


def write_report(rows, candidates, stats):
    h = stats["hist"]
    total_guests = stats["n_distinct_guests"]
    lines = []
    A = lines.append
    A("# Stage 2 corpus recon — MediaSum guest index\n")
    A(f"Generated: {time.strftime('%Y-%m-%d %H:%M %Z')}  ")
    A(f"Script: `experiments/mediasum_index.py`  ")
    A("Cost: $0 (no paid/LLM API; Wikipedia free API only).\n")

    A("## Source and checksum\n")
    A(f"- Source: {SOURCE_URL}")
    A(f"- Compressed zip: `data/mediasum/mediasum.zip` — {os.path.getsize(RAW_ZIP)} bytes")
    A(f"  - zip sha256: `{ZIP_SHA256}`")
    A("  - compression: **deflate64 (method 9)** — stdlib zipfile / unzip / ditto / bsdtar all fail; extracted with the `inflate64` wheel via `data/mediasum/extract_deflate64.py`.")
    if os.path.exists(RAW_JSON):
        A(f"- Extracted JSON: `data/mediasum/news_dialogue.json` — {os.path.getsize(RAW_JSON)} bytes")
        A(f"  - json sha256: `{JSON_SHA256}`")
    A(f"- Records parsed: **{stats['n_records']}** (expected ~463.6k). "
      f"Utterances: {stats['n_utt']}. Records with a util/speaker length "
      f"mismatch or bad shape: {stats['n_bad']}.")
    id_pref = stats["id_prefix_counter"]
    A(f"- ID prefixes: " + ", ".join(f"{k}={v}" for k, v in sorted(id_pref.items(), key=lambda x: -x[1])[:6]))
    A("")

    A("## Parsing / normalization rules actually used\n")
    A("- Speaker excluded as **staff** if the whole uppercased label matches "
      r"`\b(HOST|ANCHOR|CORRESPONDENT|BYLINE|REPORTER|COMMENTATOR)\b`.")
    A(r"- Excluded as **anonymous** if it matches `\b(UNIDENTIFIED|UNKNOWN|...)\b` "
      "or reduces to only generic tokens (MALE, WOMAN, AUDIENCE, CALLER, "
      "ANNOUNCER, PANEL, ...).")
    A("- Name = label with `(...)`/`[...]` removed, then text before the first "
      "comma / ` - ` / ` : ` separator.")
    A("- Leading honorifics stripped and recorded (DR, MR, MS, SEN, REP, GOV, "
      "PRESIDENT, PROF, GEN, REV, and multi-word ones like VICE PRESIDENT, "
      "PRIME MINISTER, ATTORNEY GENERAL).")
    A("- Normalized = per-word title-case, whitespace collapsed. Raw->normalized "
      f"mapping kept ({stats['n_distinct_raw_guest_labels']} distinct raw guest labels).")
    A(f"- **Staff catch-all:** any normalized name in > {STAFF_CATCHALL_TRANSCRIPTS} "
      f"distinct transcripts reclassified as staff. This removed "
      f"**{len(stats['catchall_removed'])}** names.")
    if stats["catchall_removed"]:
        top = stats["catchall_removed"][:15]
        A("  - Top removed (name, #transcripts): " +
          "; ".join(f"{n} ({c})" for n, c in top))
    A("")

    A("## Staff-filter / population counts\n")
    A(f"- Distinct guests after all filters: **{total_guests}**")
    A(f"- Catch-all removed: {len(stats['catchall_removed'])} high-frequency names")
    A("")

    A("## Interviews-per-guest histogram\n")
    A("| interviews | guests |")
    A("|---|---|")
    A(f"| 1 | {h[1]} |")
    A(f"| 2 | {h[2]} |")
    A(f"| 3 | {h[3]} |")
    A(f"| 4 | {h[4]} |")
    A(f"| 5+ | {h['5+']} |")
    A("")

    A("## THE KEY NUMBER\n")
    A(f"Guests with **>= {KEY_MIN_TRANSCRIPTS} distinct transcripts AND "
      f">= {KEY_MIN_WORDS} total guest words**: **{stats['key_number']}**\n")

    A("## Supplementary cuts\n")
    A(f"- >= 3 transcripts each individually substantive (>= {SUBST_MIN_WORDS} "
      f"guest words AND >= {SUBST_MIN_TURNS} turns): **{stats['cut_subst3']}**")
    A(f"- >= 4 distinct transcripts: **{stats['cut_4']}**")
    A(f"- >= 5 distinct transcripts: **{stats['cut_5']}**")
    A(f"- Of the {stats['key_number']} key candidates: first-to-last span "
      f">= 180 days: **{stats['cand_span180']}**")
    A(f"- Of the {stats['key_number']} key candidates: >= 3 transcripts with a "
      f"usable/parseable date: **{stats['cand_dates3']}**")
    A(f"- Of the {stats['key_number']} key candidates: suspiciously generic name "
      f"(common first + common last): **{stats['cand_generic']}**")
    A("")

    checked = [r for r in candidates if r["wiki_page_exists"] is not None]
    n_longtail = sum(1 for r in checked if r["wiki_page_exists"] is False)
    n_haspage = sum(1 for r in checked if r["wiki_page_exists"] is True)
    n_unchecked = len(candidates) - len(checked)
    A("## Wikipedia long-tail split (key candidates only)\n")
    A(f"- Checked: {len(checked)} of {len(candidates)} candidates "
      f"(cap {WIKI_MAX_CANDIDATES}; {n_unchecked} unchecked).")
    A(f"- **LONG-TAIL (no exact-title Wikipedia page): {n_longtail}**")
    A(f"- Has a Wikipedia page: {n_haspage}")
    A("")

    A("## Top-100 candidates by total guest words\n")
    A("| # | name | interviews | guest words | span days | programs | wiki | generic? |")
    A("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(candidates[:100], 1):
        wiki = ("long-tail" if r["wiki_page_exists"] is False
                else "page" if r["wiki_page_exists"] is True else "?")
        span = "" if r["span_days"] is None else r["span_days"]
        A(f"| {i} | {r['name']} | {r['n_transcripts']} | "
          f"{r['total_guest_words']} | {span} | {r['n_programs']} | {wiki} | "
          f"{'Y' if r['generic_name'] else ''} |")
    A("")

    A("## Caveats and data-quality landmines\n")
    A("- **Name collisions:** a normalized name can conflate two different "
      "people (e.g. two 'John Roberts'). Not resolved. `n_programs`, sample "
      "titles, and the generic-name flag are in the CSVs for human review. "
      f"{stats['cand_generic']} key candidates have a common first+last name.")
    A("- **Date quality:** span/chronological-split feasibility depends on "
      "parseable dates; see the per-candidate `n_dates` column. Candidates "
      "with < 3 usable dates cannot get a clean 3-way chronological split.")
    A("- **Wiki-flag confounds:** an exact-name match to an *unrelated* person's "
      "page yields a false 'has-page'; genuinely notable people can lack a "
      "page. The flag is a rough triage signal, not ground truth.")
    A("- **Staff-marker over-exclusion:** the role regex runs on the whole "
      "label, so a guest introduced as e.g. '(former war correspondent)' is "
      "dropped. This under-counts guests (safe direction for feasibility).")
    A("- **Honorific stripping** can merge/rarely mis-split identities; the set "
      "is broad but not exhaustive.")
    A("- **Title-casing** is per-word; 'McDonald' becomes 'Mcdonald', so a few "
      "names look odd but remain internally consistent for grouping.")
    A("")

    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------
def main():
    rows, candidates, stats = build()

    # Wikipedia flag for key candidates (by word count desc)
    cand_names = [r["name"] for r in candidates]
    print(f"Wikipedia-checking {min(len(cand_names), WIKI_MAX_CANDIDATES)} "
          f"of {len(cand_names)} candidates ...")
    flags = wiki_check(cand_names) if cand_names else {}
    for r in rows:
        if r["name"] in flags:
            r["wiki_page_exists"] = flags[r["name"]]

    # Rebuild guests tmap for interviews CSV from rows is not enough; we need the
    # per-transcript detail, which build() holds. Re-expose via closure:
    # (build() returned rows with example ids only; regenerate the maps here by
    # re-reading is wasteful, so build() attaches them.)
    write_index_csv(rows)
    write_interviews_csv(rows, stats["_guests_tmap"], stats["_tmeta"])
    write_report(rows, candidates, stats)

    print("\n=== DONE ===")
    print(f"key_number={stats['key_number']} "
          f"hist={stats['hist']} guests={stats['n_distinct_guests']}")
    print(f"index -> {INDEX_CSV}")
    print(f"interviews -> {INTERVIEWS_CSV}")
    print(f"report -> {REPORT_MD}")


if __name__ == "__main__":
    main()
