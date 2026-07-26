"""Stage 2 forced-choice prompts: the five evaluation arms (SPEC D8).

**Pure standard library on purpose.** Like ``adaptive_render.py``, this exact
file is rsynced to the compute node next to the pilot driver, so the node and
any local re-analysis build prompts from one shared implementation and cannot
drift apart. Do not add third-party imports here, and do not import from the
rest of the package (the node has no sklearn): the two things this file borrows
from elsewhere in the repo -- the honorific list and the whitespace-token word
count -- are inlined below with origin comments.

What this file is for: a Stage 2 item asks "this person was asked Q in a later
interview; which of these four replies did they give?". The same item is asked
five ways (D8):

===================  ==========================================================
``twin_redacted``    PRIMARY. Past-interview excerpts, every name variant of the
                     subject replaced by GUEST.
``twin_named``       Exploratory. Identical, plus one line naming the person.
``zeroinfo_redacted``No excerpts, no program, no date -- the floor every twin
                     number is reported against.
``zeroinfo_named``   Floor plus the name. ``zeroinfo_named - zeroinfo_redacted``
                     is the contamination meter.
``imposter_redacted``Byte-identical template to ``twin_redacted``, but the
                     excerpts are a *different* person's (the donor's).
===================  ==========================================================

Nothing here calls a model, touches disk, or reads a config: every function is
dict/str in -> str out, so a prompt is reproducible from its inputs alone and
:func:`sha256` of the rendered string is the record of what was asked.

Blocks of a rendered twin prompt, in order::

    {TWIN_PREAMBLE}

    GUEST is <canonical_name>.        <- twin_named only

    PAST INTERVIEWS
    [Interview, <date>, <program>]
    HOST: ...
    GUEST: ...

    A LATER INTERVIEW
    HOST: <question>

    Which of these replies did GUEST give?
    A. ...
    B. ...

    {DISTRIBUTION_INSTRUCTION}

and of a zero-information prompt::

    {ZEROINFO_PREAMBLE}

    The person is <canonical_name>.   <- zeroinfo_named only

    HOST: <question>

    Which of these replies did the person give?
    A. ...

    {DISTRIBUTION_INSTRUCTION}

Who redacts what (read this before wiring the driver)
-----------------------------------------------------
:func:`render_prompt` is a template, not a scrubber. It renders exactly the
strings it is handed. The caller must run :func:`redact` over **the grounding
excerpts, the question, and every option** before rendering a redacted arm --
the question comes from the test interview, where the host says the guest's
name out loud more often than not. D8 guard (c) is checked against the *final
rendered string*, so :func:`assert_redacted` catches the omission either way.

Redact and assert with the SAME variant list, or the guard is weaker than the
scrubber and cannot catch anything. The pool's ``variants`` column is mostly
just the full name ("Frederic Hof"), so a bare surname in the transcript body
survives ``redact(text, variants)``; :func:`expand_variants` adds the single
name tokens and is what the driver should pass to both functions. It is opt-in
because it over-redacts common-word surnames (dev subject C00292 is "Bassir
Pour", and every "pour" in the text becomes GUEST) -- a fluency cost paid to
close a contamination hole.
"""

from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# Frozen constants
# ---------------------------------------------------------------------------

#: What a redacted name becomes, and the speaker label of the subject's turns.
PLACEHOLDER = "GUEST"

#: The five D8 arms. Order is the SPEC's order and is what reports iterate.
ARMS = (
    "twin_redacted",
    "twin_named",
    "zeroinfo_redacted",
    "zeroinfo_named",
    "imposter_redacted",
)

#: Arms that carry an excerpt block. ``imposter_redacted`` is in here because
#: it *is* ``twin_redacted`` with someone else's excerpts -- there is no
#: separate imposter template and no marker in the text saying which is which.
GROUNDED_ARMS = frozenset({"twin_redacted", "twin_named", "imposter_redacted"})

#: Arms that reveal the person's name. Everything else must never see a name.
NAMED_ARMS = frozenset({"twin_named", "zeroinfo_named"})

#: D8: grounding budget for the pilot, in words (whitespace tokens -- the
#: pilot's documented token proxy, SPEC D5). Counts excerpt speech only; the
#: "[Interview, ...]" headers add ~5 words per segment on top.
GROUNDING_BUDGET_WORDS = 2000

#: D8 guard (a): a shared run of this many words between the true answer and
#: the grounding is a leak.
SHINGLE_WORDS = 10

#: D8 parser: a stated distribution is renormalized when its mass lands in
#: this window, and is a parse failure outside it. Bounds are inclusive; the
#: epsilon is float slack (0.2 * 4 sums to 0.8000000000000001).
MIN_MASS = 0.8
MAX_MASS = 1.2
MASS_EPS = 1e-9

#: Enough for a short reason plus the required final line.
MAX_OUTPUT_TOKENS = 120

#: Option labels. The pilot always renders 4 (SPEC D6).
OPTION_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

TWIN_PREAMBLE = (
    "Below are excerpts from past interviews with one person, called GUEST "
    "here. Read them, then answer as GUEST would in a later interview."
)

#: Fixed by D8, word for word.
ZEROINFO_PREAMBLE = (
    "A person was interviewed on American broadcast news. Predict which "
    "answer they gave."
)

#: The only line that separates ``twin_named`` from ``twin_redacted`` (D8).
TWIN_NAME_LINE = "GUEST is {name}."

#: The only line that separates ``zeroinfo_named`` from ``zeroinfo_redacted``.
ZEROINFO_NAME_LINE = "The person is {name}."

EXCERPTS_HEADER = "PAST INTERVIEWS"
LATER_HEADER = "A LATER INTERVIEW"
SEGMENT_HEADER = "[Interview, {date}, {program}]"
HOST_LABEL = "HOST"
CHOICE_LINE = "Which of these replies did {who} give?"

#: How the subject is referred to in the question block. The twin arms have
#: met GUEST in the excerpts; the zero-information arms have not.
SUBJECT_NOUN = {True: PLACEHOLDER, False: "the person"}

#: Rendered when a segment arrives without a date or a program name.
UNKNOWN_FIELD = "unknown"

_INSTRUCTION_HEAD = (
    "Give a probability for each option, summing to 1. End your reply with "
    "one line in exactly this format and nothing after it:"
)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Small text helpers
# ---------------------------------------------------------------------------


def word_count(text: str) -> int:
    """Words = whitespace tokens. Origin: stage2_data.word_count (SPEC D5)."""
    return len((text or "").split())


def _norm_ws(text: str) -> str:
    """Collapse every run of whitespace to one space; strip the ends.

    Keeps one turn on one line of the prompt, which is what makes the
    ``HOST:`` / ``GUEST:`` shape readable and the renderer insensitive to how
    the corpus happened to wrap its lines.
    """
    return " ".join((text or "").split())


def _labels(n_options: int) -> str:
    if not isinstance(n_options, int) or isinstance(n_options, bool):
        raise ValueError(f"n_options must be an int, got {n_options!r}")
    if not 2 <= n_options <= len(OPTION_LABELS):
        raise ValueError(
            f"n_options must be between 2 and {len(OPTION_LABELS)}, "
            f"got {n_options}"
        )
    return OPTION_LABELS[:n_options]


def distribution_instruction(n_options: int = 4) -> str:
    """The D8 answer-format instruction, with a worked example line.

    The example is the uniform distribution, so it leaks no preference for any
    option. At ``n_options=4`` it is ``A: 0.25 B: 0.25 C: 0.25 D: 0.25``; other
    counts round to 2 decimals and may not sum to exactly 1 in the example
    (the pilot only ever renders 4).
    """
    labels = _labels(n_options)
    share = f"{1.0 / n_options:.2f}"
    example = " ".join(f"{label}: {share}" for label in labels)
    return f"{_INSTRUCTION_HEAD}\n{example}"


#: Freeze marker: every frozen string in this module, concatenated. Pinned as a
#: literal in tests/test_stage2_render.py, so editing any template -- even by a
#: space -- fails the suite and has to be re-frozen on purpose.
TEMPLATE_TEXT = "\n".join([
    TWIN_PREAMBLE,
    ZEROINFO_PREAMBLE,
    TWIN_NAME_LINE,
    ZEROINFO_NAME_LINE,
    EXCERPTS_HEADER,
    LATER_HEADER,
    SEGMENT_HEADER,
    HOST_LABEL,
    PLACEHOLDER,
    CHOICE_LINE,
    SUBJECT_NOUN[False],
    distribution_instruction(4),
])
TEMPLATE_SHA256 = sha256(TEMPLATE_TEXT)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------
#
# Case-insensitive, longest variant first, word-boundary safe (D8). One
# alternation compiled per variant list, so replacement is a single pass and
# can never rewrite text it has already replaced.

#: Inlined subset of stage2_data.HONORIFIC (SPEC D3) -- the titles that show up
#: in front of a guest's name in broadcast transcripts. Copied rather than
#: imported to keep this file rsync-able on its own.
_HONORIFICS = (
    "mr", "mrs", "ms", "miss", "mx", "dr", "doctor", "prof", "professor",
    "sen", "senator", "rep", "representative", "congressman",
    "congresswoman", "gov", "governor", "pres", "president", "gen",
    "general", "col", "colonel", "lt", "lieutenant", "sgt", "sergeant",
    "capt", "captain", "adm", "admiral", "cmdr", "commander", "maj", "major",
    "rev", "reverend", "fr", "father", "rabbi", "imam", "sheikh", "sheik",
    "judge", "justice", "mayor", "amb", "ambassador", "secretary", "sec",
    "sir", "dame", "lord", "lady", "chief", "coach", "pastor",
)

#: An optional title in front of a matched name, so "Senator Smith" collapses
#: to one GUEST instead of leaving "Senator GUEST" behind.
_HONORIFIC_PREFIX = r"(?:(?:" + "|".join(_HONORIFICS) + r")\.?\s+)?"

#: A name token must not start or end inside a longer word. The apostrophe in
#: the lookbehind keeps "Brien" from matching inside "O'Brien"; the trailing
#: check deliberately allows an apostrophe, so a possessive redacts as
#: "GUEST's" rather than being missed.
_LEFT_EDGE = r"(?<![\w'’])"
_RIGHT_EDGE = r"(?![\w])"

#: Single name tokens shorter than this are not treated as name variants by
#: :func:`expand_variants` -- initials ("R.") and two-letter particles match
#: far too much ordinary text.
MIN_EXPANDED_TOKEN = 3

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _strip_honorifics(variant: str) -> str:
    """Drop leading titles: "Dr. Jane Smith" -> "Jane Smith"."""
    name = _norm_ws(variant)
    while True:
        parts = name.split(None, 1)
        if len(parts) < 2:
            return name
        if parts[0].rstrip(".").casefold() not in _HONORIFICS:
            return name
        name = parts[1]


def variant_forms(variants) -> list:
    """The variant strings to match, longest first, duplicates folded away.

    Each input variant contributes itself and its honorific-free form, so a
    pool variant of "Dr. Jane Smith" also matches a bare "Jane Smith" in the
    text. Ordering is ``(-length, casefolded)``: longest first is D8's rule,
    and the lexicographic tie-break makes the compiled pattern deterministic.
    """
    forms: dict = {}
    for variant in variants or ():
        for form in (_norm_ws(variant), _strip_honorifics(variant)):
            if form:
                forms.setdefault(form.casefold(), form)
    return sorted(forms.values(), key=lambda f: (-len(f), f.casefold()))


def expand_variants(variants, min_token: int = MIN_EXPANDED_TOKEN) -> list:
    """Variant forms plus every single name token in them (opt-in, see module
    docstring).

    "Frederic Hof" yields "Frederic" and "Hof" as well, which is what stops a
    bare surname in the transcript body from surviving redaction. Tokens
    shorter than ``min_token`` characters, and tokens containing digits, are
    left out. Over-redaction is the accepted cost: a surname that is also an
    ordinary word ("Pour") takes that word with it.
    """
    forms = list(variant_forms(variants))
    extra = []
    for form in forms:
        for token in _TOKEN_RE.findall(form):
            if len(token) >= min_token:
                extra.append(token)
    return variant_forms(forms + extra)


def _variant_regex(variants):
    """Compiled alternation over :func:`variant_forms`, or ``None`` if empty."""
    forms = variant_forms(variants)
    if not forms:
        return None
    alts = "|".join(
        r"\s+".join(re.escape(token) for token in form.split()) for form in forms
    )
    return re.compile(
        f"{_LEFT_EDGE}{_HONORIFIC_PREFIX}(?:{alts}){_RIGHT_EDGE}",
        re.IGNORECASE,
    )


def redact(text: str, variants, placeholder: str = PLACEHOLDER) -> str:
    """Replace every name variant in ``text`` with ``placeholder`` (D8 arm 1).

    Case-insensitive; longest variant first, so "Jane Smith" is never left as
    "GUEST Smith"; word-boundary safe, so "Smithsonian" is untouched while
    "Smith's" becomes "GUEST's". A title directly in front of a match is
    swallowed by it ("Senator Smith" -> "GUEST"), because a title plus a
    program name is itself an identifying detail.

    Matches the variants it is given and nothing else -- see
    :func:`expand_variants` for the bare-surname problem.
    """
    pattern = _variant_regex(variants)
    if pattern is None:
        return text or ""
    return pattern.sub(placeholder, text or "")


# ---------------------------------------------------------------------------
# Grounding block
# ---------------------------------------------------------------------------


def _exchange_items(segments) -> list:
    """Flatten segments to ``(seg_idx, ex_idx, date, host, guest, words)``."""
    items = []
    for seg_idx, segment in enumerate(segments or ()):
        date = str(segment.get("date") or "")
        for ex_idx, exchange in enumerate(segment.get("exchanges") or ()):
            host = _norm_ws(exchange.get("host_text"))
            guest = _norm_ws(exchange.get("guest_text"))
            if not host and not guest:
                continue
            items.append(
                (seg_idx, ex_idx, date, host, guest,
                 word_count(host) + word_count(guest))
            )
    return items


def render_grounding(segments, budget_words: int = GROUNDING_BUDGET_WORDS) -> str:
    """The excerpt block for a twin/imposter prompt (D8).

    ``segments`` is one dict per interview, in any order::

        {"date": "2013-04-29",           # ISO; sorts lexicographically
         "program": "ALL THINGS CONSIDERED",
         "exchanges": [{"host_text": "...", "guest_text": "..."}, ...]}

    An *exchange* is one host turn with the guest reply it drew, and it is the
    unit of selection: exchanges are never split. Selection is D8's
    most-recent-first greedy fill -- walk exchanges newest first (segment date
    descending, then later exchanges within a segment first) and take each one
    whose words still fit the remaining budget, skipping the ones that do not
    and continuing down the list. Skipping rather than stopping at the first
    over-large exchange is what keeps a single 900-word answer from throwing
    away the rest of the budget.

    The kept exchanges are then rendered chronologically, grouped under their
    interview headers, with a blank line between exchanges so a skipped one in
    the middle cannot read as an uninterrupted conversation.

    Budget counts speech only (host + guest words); headers are on top of it.
    Raises ``ValueError`` if nothing can be selected -- an empty excerpt block
    would silently turn the twin arm into the zero-information arm.
    """
    if budget_words <= 0:
        raise ValueError(f"budget_words must be positive, got {budget_words}")
    items = _exchange_items(segments)
    if not items:
        raise ValueError(
            "render_grounding got no non-empty exchanges; a twin prompt with "
            "no excerpts is the zero-information arm, not a twin"
        )

    # Most recent first: date desc, then segment index desc, then exchange
    # index desc. Reversing the whole key makes ties deterministic.
    newest_first = sorted(items, key=lambda it: (it[2], it[0], it[1]), reverse=True)
    kept = set()
    used = 0
    for seg_idx, ex_idx, _date, _host, _guest, words in newest_first:
        if used + words <= budget_words:
            kept.add((seg_idx, ex_idx))
            used += words
    if not kept:
        shortest = min(it[5] for it in items)
        raise ValueError(
            f"no exchange fits the {budget_words}-word grounding budget "
            f"(shortest exchange is {shortest} words)"
        )

    chronological = sorted(items, key=lambda it: (it[2], it[0], it[1]))
    blocks: list = []
    header_done: set = set()
    for seg_idx, ex_idx, date, host, guest, _words in chronological:
        if (seg_idx, ex_idx) not in kept:
            continue
        lines = []
        if seg_idx not in header_done:
            header_done.add(seg_idx)
            segment = segments[seg_idx]
            lines.append(SEGMENT_HEADER.format(
                date=date or UNKNOWN_FIELD,
                program=_norm_ws(segment.get("program")) or UNKNOWN_FIELD,
            ))
        if host:
            lines.append(f"{HOST_LABEL}: {host}")
        if guest:
            lines.append(f"{PLACEHOLDER}: {guest}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def render_options(options) -> str:
    """``A. <text>`` ... one option per line, in the order given.

    Order is meaningful: D6 already shuffled the options with a seed derived
    from the item id, and ``correct_index`` points into this exact list.
    """
    if not options or len(options) < 2:
        raise ValueError("a forced-choice item needs at least 2 options")
    labels = _labels(len(options))
    lines = []
    for label, option in zip(labels, options):
        text = _norm_ws(option)
        if not text:
            raise ValueError(f"option {label} is empty")
        lines.append(f"{label}. {text}")
    return "\n".join(lines)


def render_prompt(arm: str, question: str, options, grounding_block=None,
                  name=None) -> str:
    """One rendered prompt for one item under one of the five D8 arms.

    ``grounding_block`` is the output of :func:`render_grounding`, already
    redacted; it is required for the twin and imposter arms and rejected for
    the zero-information arms. ``name`` is the subject's canonical name; it is
    required for the two named arms and rejected for the redacted arms -- a
    name handed to a redacted arm is a leak, not a formatting preference.

    ``twin_redacted`` and ``imposter_redacted`` share one code path, so the
    same inputs give byte-identical strings: only the provenance of the
    excerpts differs, and the prompt never says whose they are.

    The entity-stripped scoring variant is this same call with the D6
    ``options_stripped`` texts; there is no separate template.
    """
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")
    grounded = arm in GROUNDED_ARMS
    named = arm in NAMED_ARMS

    question_text = _norm_ws(question)
    if not question_text:
        raise ValueError(f"{arm}: question is empty")
    if grounded and not _norm_ws(grounding_block or ""):
        raise ValueError(f"{arm} needs a grounding block")
    if not grounded and _norm_ws(grounding_block or ""):
        raise ValueError(
            f"{arm} is a zero-information arm and must carry no excerpts, "
            "no program, and no date (D8)"
        )
    if named and not _norm_ws(name or ""):
        raise ValueError(f"{arm} needs the subject's name")
    if not named and _norm_ws(name or ""):
        raise ValueError(
            f"{arm} is a redacted arm; passing a name would leak the identity "
            "the arm exists to withhold (D8)"
        )

    who = SUBJECT_NOUN[grounded]
    blocks = [TWIN_PREAMBLE if grounded else ZEROINFO_PREAMBLE]
    if named:
        line = TWIN_NAME_LINE if grounded else ZEROINFO_NAME_LINE
        blocks.append(line.format(name=_norm_ws(name)))
    if grounded:
        blocks.append(f"{EXCERPTS_HEADER}\n{grounding_block.strip()}")
        blocks.append(f"{LATER_HEADER}\n{HOST_LABEL}: {question_text}")
    else:
        blocks.append(f"{HOST_LABEL}: {question_text}")
    blocks.append(f"{CHOICE_LINE.format(who=who)}\n{render_options(options)}")
    blocks.append(distribution_instruction(len(options)))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Distribution parsing
# ---------------------------------------------------------------------------
#
# Tolerant about how the model dresses the line -- ":", ")", "=", "-", ".", a
# missing space, commas between pairs, one pair per line, percent signs, prose
# before it -- and strict about the arithmetic: the stated mass has to land in
# [0.8, 1.2] or the answer is not scored (D8).

_PAIR_RE = re.compile(
    r"(?<![\w])([A-Za-z])\s*[:=).\]\-]\s*(\d*\.?\d+)\s*(%?)"
)


def _pairs(text: str, labels: str) -> list:
    """All ``(label, value, is_percent)`` in reading order, valid labels only."""
    out = []
    for match in _PAIR_RE.finditer(text):
        label = match.group(1).upper()
        if label not in labels:
            continue
        try:
            value = float(match.group(2))
        except ValueError:  # pragma: no cover - regex guarantees a number
            continue
        out.append((label, value, match.group(3) == "%"))
    return out


def parse_distribution(completion, n_options: int = 4):
    """``"A: 0.7 B: 0.1 C: 0.1 D: 0.1"`` -> ``[0.7, 0.1, 0.1, 0.1]``.

    Returns a list of ``n_options`` probabilities in label order, renormalized
    to sum to 1, or ``None`` on parse failure (D8).

    What counts as an answer: pairs are read left to right and grouped; a label
    that repeats starts a new group, and the **last complete group** wins. A
    model that thinks out loud and then restates its distribution is therefore
    scored on the restatement, which is what the "final line" instruction asks
    for. Percentages are divided by 100 per value, so "A: 70%" is 0.7.

    Failure cases: a missing or duplicated label with no later complete group,
    a negative number (the minus sign breaks the pair, so the group never
    completes), and any stated mass outside [0.8, 1.2] -- including "70 10 10
    10" written without percent signs, which is silence about the scale rather
    than a distribution.
    """
    labels = _labels(n_options)
    if not completion:
        return None
    groups: list = []
    current: dict = {}
    for label, value, is_percent in _pairs(completion, labels):
        if label in current:
            current = {}
        current[label] = value / 100.0 if is_percent else value
        if len(current) == n_options:
            groups.append(current)
            current = {}
    if not groups:
        return None
    chosen = groups[-1]
    values = [chosen[label] for label in labels]
    total = sum(values)
    if total < MIN_MASS - MASS_EPS or total > MAX_MASS + MASS_EPS:
        return None
    return [value / total for value in values]


# ---------------------------------------------------------------------------
# Leakage guards (D8; gym.py style -- loud, with a diagnostic)
# ---------------------------------------------------------------------------
#
# Guard (a) is find_answer_leak/assert_no_answer_leak below. Guard (c) is
# assert_redacted. Guard (b) -- test-interview text never entering the
# grounding -- is structural and is asserted upstream, where the split is built
# (T1's stage2_draw_dev.py), because by the time a string reaches this file
# there is nothing left to check it against.

_STRIP = "\"'`.,;:!?()[]{}<>-–—…“”‘’"


def _norm_tokens(text: str) -> list:
    """Casefolded whitespace tokens with edge punctuation removed.

    Makes the shingle guard insensitive to quoting and sentence punctuation:
    "the vote, and" and "the vote and" share their words.
    """
    out = []
    for token in (text or "").split():
        stripped = token.casefold().strip(_STRIP)
        if stripped:
            out.append(stripped)
    return out


def find_answer_leak(grounding_block: str, true_answer: str,
                     n: int = SHINGLE_WORDS):
    """The first ``n``-word run the answer and the grounding share, or ``None``.

    Answers shorter than ``n`` words have no ``n``-gram, so they are checked
    for whole-string containment instead (D4 floors answers at 30 words, so
    this is a guard on the guard).
    """
    haystack = _norm_tokens(grounding_block)
    needle = _norm_tokens(true_answer)
    if not needle or not haystack:
        return None
    if len(needle) < n:
        joined_h = " ".join(haystack)
        joined_n = " ".join(needle)
        return joined_n if joined_n in joined_h else None
    shingles = {
        tuple(haystack[i:i + n]) for i in range(len(haystack) - n + 1)
    }
    for i in range(len(needle) - n + 1):
        shingle = tuple(needle[i:i + n])
        if shingle in shingles:
            return " ".join(shingle)
    return None


def assert_no_answer_leak(grounding_block: str, true_answer: str,
                          n: int = SHINGLE_WORDS) -> None:
    """D8 guard (a): the true answer must not be quoted in the grounding."""
    leak = find_answer_leak(grounding_block, true_answer, n)
    if leak is not None:
        raise ValueError(
            f"true answer leaked into the grounding block: the {n}-word run "
            f"{leak!r} appears in both"
        )


def surviving_variants(rendered: str, variants, expand: bool = False) -> list:
    """Name variants still present in a rendered prompt, in order of first hit.

    Same matcher as :func:`redact`, so the guard is exactly as strong as the
    scrubber and never trips on something ``redact`` could not have removed.
    """
    forms = expand_variants(variants) if expand else variants
    pattern = _variant_regex(forms)
    if pattern is None or not rendered:
        return []
    seen: dict = {}
    for match in pattern.finditer(rendered):
        seen.setdefault(match.group(0).casefold(), match.group(0))
    return list(seen.values())


def assert_redacted(rendered: str, variants, expand: bool = False) -> None:
    """D8 guard (c): no name variant may survive in the final rendered prompt.

    Assert on the *whole* rendered string, after replacement -- the question
    and the options come from the test interview and the distractor bank, and
    the guard exists precisely to catch the ones the caller forgot to scrub.

    ``expand=True`` also rejects bare single name tokens (see
    :func:`expand_variants`). Pass the same setting here that you passed to
    :func:`redact`, or the two disagree.
    """
    survivors = surviving_variants(rendered, variants, expand=expand)
    if survivors:
        shown = ", ".join(repr(s) for s in survivors[:3])
        raise ValueError(
            f"redaction failed: {len(survivors)} name variant(s) survive in "
            f"the rendered prompt ({shown})"
        )
