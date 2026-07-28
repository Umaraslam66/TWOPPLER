"""Stage 2 OPEN-ENDED prompts (OE-1): the same five D8 arms, no options.

Binding design: ``results/stage2_openended/PILOT_SPEC.md`` (owner-approved
2026-07-27), whose contract lineage is ``results/stage2_pilot4/SPEC_v1.10.md``.
Everything the spec does not change carries over from the forced-choice
renderer, and this module carries none of it twice: the preambles, the name
lines, the excerpt headers, the 2,000-word most-recent-first grounding fill,
the name redactor and the leakage guards are all imported from
:mod:`doppler.stage2_render` and used unchanged.

**The only change is the prompt tail.** Forced choice ended with

    Which of these replies did GUEST give?
    A. ...  B. ...  C. ...  D. ...
    <distribution instruction>

Open-ended ends with the held-out question and one instruction, byte-identical
across all five arms (:data:`OPEN_ANSWER_INSTRUCTION`). No options, no
distribution line, nothing that names the arm.

Blocks of a rendered open-ended twin prompt, in order::

    {TWIN_PREAMBLE}

    GUEST is <canonical_name>.        <- twin_named only

    PAST INTERVIEWS
    [Interview, <date>, <program>]
    HOST: ...
    GUEST: ...

    A LATER INTERVIEW
    HOST: <question>

    {OPEN_ANSWER_INSTRUCTION}

and of an open-ended zero-information prompt::

    {ZEROINFO_PREAMBLE}

    The person is <canonical_name>.   <- zeroinfo_named only

    HOST: <question>

    {OPEN_ANSWER_INSTRUCTION}

Why the preambles are not touched
---------------------------------
The spec (section 2) fixes this: "'This person' reads correctly under every
arm's existing preamble (GUEST in the twin/imposter arms, 'a person' in the
zero-info arms), so the tail is byte-identical across arms." The zero-info
preamble still contains the forced-choice sentence "Predict which answer they
gave." — that is the frozen v1.10 string and changing it is a bar-lock
decision, not an implementation one. It is flagged in the build summary rather
than silently rewritten.

S1 affiliation redaction
------------------------
:func:`apply_s1_scope` is the S1 scope priced in
``results/stage2_pilot2/BARLOCK_MEASUREMENTS.md`` section 8.1 and named by the
open-ended spec ("same S1 affiliation redaction"): inside HOST/GUEST speech
lines, the appositive or predicate clause that *describes* GUEST is replaced by
``[DESCRIPTION REMOVED]`` when it carries a role word. It is applied to ALL
five arms, not only the three ``*_redacted`` ones, so that a named arm stays
byte-identical to its redacted counterpart apart from the single name line —
the one-factor invariant the contamination meter rests on. The build summary
reports the check on the redacted arms, as required.

Extended 2026-07-28 under Addendum A instrument parameter 8, in two places
only: the clause pattern now reads through an abbreviation's full stop
("U.S."), and a "GUEST, who ..." clause now runs past its internal commas for
as long as it is still describing the guest. Both stay inside S1's declared
intent and neither changes what S1 removed before. Measurement:
``results/stage2_confirm/s1_extension_remeasure.md``.

Nothing here calls a model, reads a config, or touches disk beyond what its
caller hands it: a prompt is reproducible from its inputs alone, and
``R.sha256`` of the rendered string is the record of what was asked.
"""

from __future__ import annotations

import re

from doppler import stage2_render as R

# ---------------------------------------------------------------------------
# The frozen tail
# ---------------------------------------------------------------------------

#: PILOT_SPEC.md section 2, verbatim, one draft, frozen at bar-lock per C2.1.
#: Byte-identical in all five arms. Never format it, never per-arm it.
OPEN_ANSWER_INSTRUCTION = (
    "Now answer the interviewer's next question as this person would, "
    "speaking in their voice, in the first person. Give one spoken reply of "
    "at most 150 words. No lists, no stage directions, no commentary about "
    "this task."
)

#: The cap the instruction states, and the generation budget that assumes it
#: (spec section 2). Both scored models use these; the driver writes them into
#: the sbatch/prompt files so the cap lives with the prompt.
MAX_ANSWER_WORDS = 150
MAX_OUTPUT_TOKENS = 256
TEMPERATURE = 0.0

# Re-exported so a caller never has to import both modules to render one arm.
ARMS = R.ARMS
GROUNDED_ARMS = R.GROUNDED_ARMS
NAMED_ARMS = R.NAMED_ARMS
PLACEHOLDER = R.PLACEHOLDER
GROUNDING_BUDGET_WORDS = R.GROUNDING_BUDGET_WORDS

#: Freeze marker for the open-ended template: every frozen string this module
#: renders, concatenated. Pinned as a literal in tests, so editing any of them
#: — even by a space — fails the suite and has to be re-frozen on purpose.
TEMPLATE_TEXT = "\n".join([
    R.TWIN_PREAMBLE,
    R.ZEROINFO_PREAMBLE,
    R.TWIN_NAME_LINE,
    R.ZEROINFO_NAME_LINE,
    R.EXCERPTS_HEADER,
    R.LATER_HEADER,
    R.SEGMENT_HEADER,
    R.HOST_LABEL,
    R.PLACEHOLDER,
    OPEN_ANSWER_INSTRUCTION,
])
TEMPLATE_SHA256 = R.sha256(TEMPLATE_TEXT)

#: The tail on its own. The build QA asserts this exact string is the last
#: block of all 85 prompts.
INSTRUCTION_SHA256 = R.sha256(OPEN_ANSWER_INSTRUCTION)


# ---------------------------------------------------------------------------
# S1 affiliation redaction
# ---------------------------------------------------------------------------
#
# Inlined copy of the S1 scope from experiments/barlock_affiliation.py (role
# word list, appositive pattern and the substitution), so the renderer stays
# importable from src/ without reaching into experiments/. ROLE_WORDS and
# _APPOS_RE stay byte-identical to the origin module — the tests pin them — and
# the extension below is added beside them, never on top of them.

S1_PLACEHOLDER = "[DESCRIPTION REMOVED]"

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
_APPOS_RE = re.compile(
    r"GUEST(?:'s)?,\s+([^,.;]{3,120})(?=[,.;])|"          # "GUEST, professor at X,"
    r"GUEST\s+is\s+([^.;]{3,160})(?=[.;])|"               # "GUEST is the author of X."
    r"GUEST,\s+(?:as\s+)?an?\s+([^,.;]{3,120})(?=[,.;])"  # "GUEST, as a former ..."
)

_HOST_PREFIX = f"{R.HOST_LABEL}: "
_GUEST_PREFIX = f"{R.PLACEHOLDER}: "

# --- S1 extension, Addendum A instrument parameter 8 (2026-07-28) -----------
#
# Two additions, both inside S1's declared intent: the host's descriptive
# clause about GUEST. Nothing else about S1 moves.
#
# (a) Abbreviation-safe clause. _APPOS_RE's clause runs "up to the next full
#     stop", so the full stop inside "U.S." ended the clause early and the role
#     word behind it was never seen — an imposter prompt kept "GUEST, who
#     served two tours as U.S. ambassador to Israel, now at the Brookings
#     Institution" whole. The clause patterns now run over a copy of the line
#     in which an abbreviation's full stops are masked, so they no longer read
#     as sentence ends. A full stop followed by a space and a capital is left
#     alone: that is a real sentence break and the clause must still stop
#     there.
#
# (b) The "GUEST, who ..." relative clause. _APPOS_RE stops at the first comma,
#     which cuts such a clause in half and leaves the rest of the résumé
#     standing (", now at the Brookings Institution"). The clause now grows
#     across commas one segment at a time and stops at the first segment that
#     no longer describes the guest — no role word and no proper noun — or that
#     turns to address them ("thanks so much", "what did you see?"). That stop
#     rule is what keeps the host's own question out of the removal.

#: Stand-in for a full stop that belongs to an abbreviation. Never occurs in
#: transcript text, so masking and unmasking are exactly reversible.
_ABBREV_DOT = "\x00"

#: An abbreviation whose full stop is not the end of the sentence: an
#: initialism ("U.S.", "D.C.") or a common title ("Dr.", "Sen."), followed by
#: more of the same sentence — a comma, a hyphen, a bracket, or a space and a
#: lower-case word.
_ABBREV_RE = re.compile(
    r"(?:\b(?:[A-Za-z]\.){2,}"
    r"|\b(?:Mr|Mrs|Ms|Dr|Prof|Sen|Rep|Gov|Gen|Amb|Lt|Col|Sgt|St|Jr|Sr"
    r"|Inc|Corp|Ltd|Univ)\.)"
    r"(?=[,;:)\-]|\s+[a-z])"
)

#: "GUEST, who ..." up to the end of its sentence. How much of that is kept is
#: :func:`_describing_prefix`'s decision, not the pattern's.
_WHO_RE = re.compile(r"GUEST,\s+(who\b[^.;?!]{3,300})(?=[.;?!])")

#: A proper noun: what marks a comma-segment as still naming an affiliation
#: ("now at the Brookings Institution") rather than closing the introduction.
#: Two lower-case letters are required so a bare "I" does not qualify.
_PROPER_RE = re.compile(r"\b[A-Z][a-z]{2,}")

#: The host turning from describing the guest to addressing them. Same reading
#: as ``barlock_affiliation._SECOND_PERSON_RE``.
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|you've|yourself)\b",
                               re.IGNORECASE)


def _mask_abbreviations(text: str) -> str:
    """Hide abbreviation full stops so a clause pattern reads through them."""
    return _ABBREV_RE.sub(
        lambda m: m.group(0).replace(".", _ABBREV_DOT), text)


def _describing_prefix(body: str) -> str:
    """How much of a ``who ...`` clause is still describing GUEST.

    Grows the clause one comma-segment at a time from the left and returns the
    prefix of ``body`` that stops before the first segment that carries no role
    word and no proper noun, or that addresses the guest in the second person.
    """
    breaks = list(re.finditer(r",\s+", body))
    ends = [m.start() for m in breaks] + [len(body)]
    starts = [0] + [m.end() for m in breaks]
    keep = ends[0]
    for start, end in zip(starts[1:], ends[1:]):
        segment = body[start:end]
        if _SECOND_PERSON_RE.search(segment):
            break
        if not (_ROLE_RE.search(segment) or _PROPER_RE.search(segment)):
            break
        keep = end
    return body[:keep]


def apply_s1(text: str) -> tuple[str, int]:
    """Drop the clause that describes GUEST, when it carries a role word.

    Returns ``(rewritten, n_clauses_removed)``. Origin:
    ``experiments/barlock_affiliation.apply_s1``, plus the two Addendum A
    parameter-8 extensions described above.
    """
    n = 0

    def repl_who(m):
        nonlocal n
        body = _describing_prefix(m.group(1))
        if not _ROLE_RE.search(body):
            return m.group(0)
        n += 1
        return m.group(0).replace(body, S1_PLACEHOLDER, 1)

    def repl(m):
        nonlocal n
        body = next(g for g in m.groups() if g)
        if not _ROLE_RE.search(body):
            return m.group(0)
        n += 1
        return m.group(0).replace(body, S1_PLACEHOLDER)

    masked = _mask_abbreviations(text or "")
    masked = _WHO_RE.sub(repl_who, masked)
    masked = _APPOS_RE.sub(repl, masked)
    return masked.replace(_ABBREV_DOT, "."), n


def apply_s1_scope(prompt: str) -> tuple[str, int]:
    """S1 over a rendered prompt: speech lines only, headers untouched.

    Only lines that start with ``HOST: `` or ``GUEST: `` are rewritten, which
    is what keeps S1 away from the preamble, the excerpt headers and the
    ``GUEST is <name>.`` line of a named arm. Origin:
    ``experiments/barlock_affiliation.apply_scope(..., "S1", ...)``.
    """
    lines = (prompt or "").splitlines()
    removed = 0
    for i, line in enumerate(lines):
        if line.startswith(_HOST_PREFIX):
            prefix, body = _HOST_PREFIX, line[len(_HOST_PREFIX):]
        elif line.startswith(_GUEST_PREFIX):
            prefix, body = _GUEST_PREFIX, line[len(_GUEST_PREFIX):]
        else:
            continue
        new, n = apply_s1(body)
        removed += n
        lines[i] = prefix + new
    return "\n".join(lines), removed


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_open_prompt(arm: str, question: str, grounding_block=None,
                       name=None, s1: bool = True) -> str:
    """One rendered OPEN-ENDED prompt for one item under one of the five arms.

    Same contract as :func:`doppler.stage2_render.render_prompt` minus the
    options: ``grounding_block`` is required for the twin and imposter arms and
    rejected for the zero-information arms; ``name`` is required for the two
    named arms and rejected for the redacted arms.

    ``twin_redacted`` and ``imposter_redacted`` share one code path, so the
    same inputs give byte-identical strings — only the provenance of the
    excerpts differs and the prompt never says whose they are.

    ``s1=False`` turns off the affiliation scrub. It exists so a test can show
    what S1 changed; the pilot always renders with ``s1=True``.
    """
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")
    grounded = arm in GROUNDED_ARMS
    named = arm in NAMED_ARMS

    question_text = R._norm_ws(question)
    if not question_text:
        raise ValueError(f"{arm}: question is empty")
    if grounded and not R._norm_ws(grounding_block or ""):
        raise ValueError(f"{arm} needs a grounding block")
    if not grounded and R._norm_ws(grounding_block or ""):
        raise ValueError(
            f"{arm} is a zero-information arm and must carry no excerpts, "
            "no program, and no date (D8)"
        )
    if named and not R._norm_ws(name or ""):
        raise ValueError(f"{arm} needs the subject's name")
    if not named and R._norm_ws(name or ""):
        raise ValueError(
            f"{arm} is a redacted arm; passing a name would leak the identity "
            "the arm exists to withhold (D8)"
        )

    blocks = [R.TWIN_PREAMBLE if grounded else R.ZEROINFO_PREAMBLE]
    if named:
        line = R.TWIN_NAME_LINE if grounded else R.ZEROINFO_NAME_LINE
        blocks.append(line.format(name=R._norm_ws(name)))
    if grounded:
        blocks.append(f"{R.EXCERPTS_HEADER}\n{grounding_block.strip()}")
        blocks.append(f"{R.LATER_HEADER}\n{R.HOST_LABEL}: {question_text}")
    else:
        blocks.append(f"{R.HOST_LABEL}: {question_text}")
    blocks.append(OPEN_ANSWER_INSTRUCTION)
    rendered = "\n\n".join(blocks)
    if s1:
        rendered, _ = apply_s1_scope(rendered)
    return rendered


# ---------------------------------------------------------------------------
# Build-QA helpers (used by the driver and by the tests)
# ---------------------------------------------------------------------------

#: Anything that would betray a leftover forced-choice tail: an option line, or
#: the distribution instruction's first words.
_OPTION_LINE_RE = re.compile(r"^[A-Z]\.\s+\S", re.MULTILINE)
_CHOICE_LINE_FRAGMENT = "Which of these replies did"
_DISTRIBUTION_FRAGMENT = "Give a probability for each option"


def has_instruction_tail(prompt: str) -> bool:
    """True when the prompt ends with exactly the frozen instruction block."""
    return (prompt or "").endswith("\n\n" + OPEN_ANSWER_INSTRUCTION)


def tail_of(prompt: str) -> str:
    """The last ``\\n\\n``-separated block of a prompt."""
    return (prompt or "").rsplit("\n\n", 1)[-1]


def forced_choice_residue(prompt: str) -> list[str]:
    """Every forced-choice artefact still present, for a loud QA failure."""
    found = []
    if _CHOICE_LINE_FRAGMENT in (prompt or ""):
        found.append("choice_line")
    if _DISTRIBUTION_FRAGMENT in (prompt or ""):
        found.append("distribution_instruction")
    # An option line is "A. text" at the start of a line. Excerpt lines always
    # start with "HOST: ", "GUEST: " or "[Interview," -- render_grounding puts
    # one turn on one line -- so scanning the WHOLE prompt cannot false-positive
    # on a transcript, while scanning only the tail would miss an option block
    # wedged in front of the instruction.
    if _OPTION_LINE_RE.search(prompt or ""):
        found.append("option_line")
    return found


def assert_open_ended(prompt: str) -> None:
    """The open-ended shape guard: frozen tail present, no forced-choice tail."""
    if not has_instruction_tail(prompt):
        raise ValueError(
            "open-ended prompt does not end with the frozen instruction "
            f"block; its tail is {tail_of(prompt)!r}")
    residue = forced_choice_residue(prompt)
    if residue:
        raise ValueError(
            f"open-ended prompt still carries forced-choice material: "
            f"{', '.join(residue)}")


def grounding_speech_words(grounding_block: str) -> int:
    """Words of speech in a rendered grounding block, headers excluded.

    Reproduces the accounting :func:`doppler.stage2_render.render_grounding`
    budgets against: ``[Interview, ...]`` header lines do not count, and the
    ``HOST:`` / ``GUEST:`` labels do not count, so this number is directly
    comparable to :data:`GROUNDING_BUDGET_WORDS`.
    """
    total = 0
    for line in (grounding_block or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[Interview,"):
            continue
        if stripped.startswith(_HOST_PREFIX) or stripped.startswith(_GUEST_PREFIX):
            stripped = stripped.split(":", 1)[1]
        total += R.word_count(stripped)
    return total


def excerpt_block_of(prompt: str) -> str:
    """The excerpt text of a grounded prompt, or ``""`` for a zero-info one."""
    marker = f"{R.EXCERPTS_HEADER}\n"
    if marker not in (prompt or ""):
        return ""
    after = prompt.split(marker, 1)[1]
    return after.split(f"\n\n{R.LATER_HEADER}\n", 1)[0]


def carries_excerpts(prompt: str) -> bool:
    """D8: a zero-information prompt must carry no excerpts, program or date."""
    return R.EXCERPTS_HEADER in (prompt or "") or "[Interview," in (prompt or "")
