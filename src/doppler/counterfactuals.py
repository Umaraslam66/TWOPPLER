"""SPEC v1.9 / Amendment 2 B10 — generated same-question counterfactuals.

Why the instrument changed. Two dev pilots showed forced choice over VERBATIM
real answers is invalid on this corpus. Pilot 1 (other people's answers) and
pilot 2 (the same subject's other answers) were both solved 100% by the
zero-information arm, and pilot 2's decomposition located the mechanism exactly:
entity-stripping changed nothing (10/10), removing the question collapsed
accuracy to 1/10. The true answer wins because it is the only option
*responsive* to the question shown — and a distractor drawn from any real
transcript is, by definition, an answer to a different question.

B10's fix: the distractors are GENERATED answers to the SAME question, taking
positions that genuinely conflict with the subject's actual position. Every
option is responsive by construction, so responsiveness stops being a tell.

**What is scored changes with it, and must be said in every write-up:** the
claim is that the twin identifies the person's actual POSITION among plausible
alternative positions on the same question — not that it picks a verbatim
transcript answer.

This module holds the parts that must be auditable and offline-testable: the
prompt builders, the strict output parsers, and every deterministic guard. The
API calls themselves live in the driver, which logs every prompt and every raw
completion to results/stage2_pilot3/genlog/ — API generation is not
seed-reproducible, so the log IS the provenance.

Generator separation (B10.3) is the driver's job to enforce and document; this
module never names a model.
"""

from __future__ import annotations

import hashlib
import re

from doppler import stage2_render as R
from doppler.distractors import (
    ADJACENT_BUCKETS, RELAX_LADDER, density_bucket, entity_density,
)
from doppler.qa_extract import jaccard, word_set

#: Counterfactuals asked of the generator per item. Three go into the item; the
#: fourth is the spare that replaces a rejected one, and — when it survives
#: unused — supplies the all-generated control items on the B10.8 detectability
#: sheet without a second generation call.
N_GENERATED = 4

#: Distractors per item.
N_DISTRACTORS = 3

#: A generated option that copies the true answer this closely is a paraphrase
#: of it, not a counterfactual. Same threshold and machinery as D4's
#: near-duplicate question rule and D6-v2's ambiguity guard.
COPY_JACCARD = 0.8

#: Shingle length for the grounding-overlap guard. The frozen D8 guard-(a) value.
LEAK_SHINGLE_WORDS = R.SHINGLE_WORDS

#: Years outside this range are not era references (phone numbers, counts).
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

_BLOCK_RE = re.compile(r"<<<(\d+)>>>")


# ---------------------------------------------------------------------------
# Prompt builders. Frozen text + a digest, so a silent edit is detectable.
# ---------------------------------------------------------------------------

GEN_TEMPLATE = """\
You are helping build a multiple-choice comprehension test.

Below is a question a journalist asked a guest on American broadcast news, and \
the guest's ACTUAL answer. Write {n} ALTERNATIVE answers to the SAME question.

RULES, all mandatory:
1. Every alternative must directly answer the question that was asked.
2. Every alternative must take a position that GENUINELY CONFLICTS with the \
actual answer. Someone who believes an alternative would disagree with the \
actual answer on substance. Do not restate, soften, or partially agree with it.
3. The {n} alternatives must also differ from each other, not be {n} wordings \
of one position.
4. Write in spoken interview register, first person, as a guest being \
interviewed out loud. Match the actual answer's register and rhythm.
5. Do NOT copy distinctive phrases or specific content from the actual answer.
6. Length: about {words} words each (between {lo} and {hi} words).
7. SPECIFICITY: the actual answer refers to about {ents} specific named things \
(people, places, organisations, numbers). Use a similar number in each \
alternative -- roughly {lo_e} to {hi_e}. An alternative that stays vague while \
the actual answer names names is not a usable alternative.
8. ERA: the interview took place on {date}. Nothing you write may mention or \
imply any event after that date. Naming people, places and organisations that \
already existed on that date is expected and wanted; avoid naming explicit \
calendar dates.
9. Never name the guest, and never refer to the guest in the third person.

QUESTION
{question}

ACTUAL ANSWER
{answer}

Output format — exactly {n} blocks, nothing before, between, or after them \
except the markers:
{markers}
"""

PARA_TEMPLATE = """\
Rewrite the interview answer below in neutral, plain spoken English.

RULES, all mandatory:
1. Preserve the position and every substantive claim EXACTLY. Do not add, \
remove, soften, or strengthen any claim.
2. Remove distinctive stylistic marks: verbal tics, filler, false starts, \
catchphrases, unusual punctuation, idiosyncratic rhythm.
3. Keep it first person and conversational, about the same length.
4. Do not add framing such as "the speaker says". Write it as the answer itself.

Reply with the rewritten answer only, on one line, and nothing else.

ANSWER
{text}
"""

POSITION_TEMPLATE = """\
Two versions of the same interview answer are below.

Does version B express the SAME position and the same substantive claims as \
version A? Ignore differences of wording, style, and rhythm entirely; judge \
only the position taken and the claims made.

Reply with exactly one line:
VERDICT: SAME
or
VERDICT: CHANGED
then a second line:
WHY: <one sentence>

VERSION A
{original}

VERSION B
{paraphrase}
"""

CONTRA_TEMPLATE = """\
A journalist asked the question below. Two possible answers follow.

Classify the relationship between the positions the two answers take:
- CONFLICT: someone who holds answer 1's position would disagree with answer 2 \
on substance.
- AGREE: they take the same position, or one is a restatement or a milder \
version of the other.
- UNRELATED: at least one of them does not actually answer the question asked.

Reply with exactly one line:
VERDICT: CONFLICT
or
VERDICT: AGREE
or
VERDICT: UNRELATED
then a second line:
WHY: <one sentence>

QUESTION
{question}

ANSWER 1
{a}

ANSWER 2
{b}
"""

TEMPLATE_TEXT = "\n".join(
    [GEN_TEMPLATE, PARA_TEMPLATE, POSITION_TEMPLATE, CONTRA_TEMPLATE])
TEMPLATE_SHA256 = hashlib.sha256(TEMPLATE_TEXT.encode("utf-8")).hexdigest()


def _markers(n: int) -> str:
    return "\n".join(f"<<<{i}>>>\n<answer {i}>" for i in range(1, n + 1))


def entity_tokens(text: str) -> int:
    """How many D5 entity tokens a text carries (names, numbers, amounts)."""
    return int(round(entity_density(text) * R.word_count(text)))


def gen_prompt(question: str, answer: str, date: str, *, n: int = N_GENERATED,
               tolerance: float = 0.15) -> str:
    """B10.1 — ask for ``n`` conflicting answers to the same question.

    ``answer`` must be the text the option set will actually SHOW as the true
    option, i.e. the PARAPHRASED answer, not the verbatim transcript one. The
    first trial built counterfactuals against the verbatim answer and they came
    out 49-53 words against a 42-word paraphrase, missing the length ladder
    entirely.

    The specificity clause exists for the other half of the same trial failure:
    the real answer sat in density bucket H (it names ISIS and Bashar al-Assad)
    while all three generated options sat in Z, which hands a scorer the tell
    "pick the option with the names" -- precisely what A4.1 matching forbids.
    """
    words = R.word_count(answer)
    ents = entity_tokens(answer)
    return GEN_TEMPLATE.format(
        n=n, words=words, lo=int(words * (1 - tolerance)),
        hi=int(words * (1 + tolerance)), date=date,
        ents=ents, lo_e=max(0, ents - 2), hi_e=ents + 2,
        question=" ".join(question.split()),
        answer=" ".join(answer.split()), markers=_markers(n))


def para_prompt(text: str) -> str:
    """B10.4 — one neutral normalisation step.

    The SAME template is used for the true answer and for every generated
    option, and each is sent in its own call, so the paraphraser cannot know
    which text is the real one and cannot treat it differently. That is what
    makes style neutralisation a one-factor operation rather than a hope.
    """
    return PARA_TEMPLATE.format(text=" ".join(text.split()))


def position_prompt(original: str, paraphrase: str) -> str:
    """B10.4 — did the paraphrase preserve the true answer's position?"""
    return POSITION_TEMPLATE.format(original=" ".join(original.split()),
                                    paraphrase=" ".join(paraphrase.split()))


def contra_prompt(question: str, true_text: str, distractor: str) -> str:
    """B10.5 — does this distractor genuinely conflict with the true position?"""
    return CONTRA_TEMPLATE.format(question=" ".join(question.split()),
                                  a=" ".join(true_text.split()),
                                  b=" ".join(distractor.split()))


# ---------------------------------------------------------------------------
# Parsers. Strict: an unparseable reply is a failure, never a guess.
# ---------------------------------------------------------------------------

def parse_generated(completion: str, n: int = N_GENERATED) -> list[str]:
    """Pull the ``<<<k>>>`` blocks out of a generation reply, in order.

    Returns the blocks actually found, which may be fewer than ``n``; the
    caller decides whether that is fatal. Blocks are returned whitespace-
    normalised because every downstream length and overlap measure is defined
    on whitespace tokens.
    """
    if not completion:
        return []
    marks = list(_BLOCK_RE.finditer(completion))
    out: list[tuple[int, str]] = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(completion)
        text = " ".join(completion[start:end].split())
        if text:
            out.append((int(m.group(1)), text))
    seen: dict[int, str] = {}
    for idx, text in out:
        seen.setdefault(idx, text)
    return [seen[k] for k in sorted(seen)][:n]


_VERDICT_RE = re.compile(r"^\s*[*_>\s]*VERDICT[*_\s]*:[*_\s]*([A-Z]+)",
                         re.IGNORECASE | re.MULTILINE)
_WHY_RE = re.compile(r"^\s*[*_>\s]*WHY[*_\s]*:[*_\s]*(.+?)\s*$",
                     re.IGNORECASE | re.MULTILINE)


def parse_verdict(completion: str, allowed) -> tuple[str | None, str | None]:
    """``(verdict, why)`` from a check reply; ``(None, ...)`` if unparseable."""
    if not completion:
        return None, None
    match = _VERDICT_RE.search(completion)
    why = _WHY_RE.search(completion)
    why_text = why.group(1).strip() if why else None
    if match is None:
        return None, why_text
    verdict = match.group(1).upper()
    return (verdict if verdict in set(allowed) else None), why_text


def parse_paraphrase(completion: str) -> str:
    """A paraphrase reply is its text; strip stray markers and quoting."""
    text = " ".join((completion or "").split())
    text = re.sub(r"^(?:ANSWER|REWRITTEN(?:\s+ANSWER)?)\s*:\s*", "", text,
                  flags=re.IGNORECASE)
    return text.strip().strip('"').strip()


# ---------------------------------------------------------------------------
# Deterministic guards. No model in the loop; these are the auditable ones.
# ---------------------------------------------------------------------------

def looks_truncated(text: str) -> bool:
    """Did a reply stop mid-sentence?

    The generator is a thinking model whose hidden reasoning is charged against
    max_output_tokens, so an under-sized budget does not error -- it returns a
    clean-looking prefix that simply stops. A 228-word answer paraphrased under
    a 4,096 budget came back 163 visible tokens long ending mid-word, and only
    the position check noticed. Cheaper and clearer to catch it here.
    """
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped[-1] not in ".!?\"')]"


def era_violations(text: str, test_date: str) -> list[str]:
    """B10.6 — years in the text later than the test interview's year.

    Deliberately blunt and deliberately deterministic: a model asked "does this
    mention anything after 2014" is another unauditable judgement, whereas a
    year literal is a fact. It cannot catch an unnamed later event ("after the
    invasion"), which is why the generator is ALSO instructed on the era and why
    the limitation is recorded rather than hidden.
    """
    try:
        year = int(str(test_date)[:4])
    except (TypeError, ValueError):
        return []
    return [m.group(0) for m in _YEAR_RE.finditer(text or "")
            if int(m.group(0)) > year]


def copies_true(text: str, true_answer: str,
                threshold: float = COPY_JACCARD) -> bool:
    """A generated option that is really the true answer wearing new words."""
    return jaccard(word_set(text), word_set(true_answer)) >= threshold


def quotes_grounding(text: str, grounding_blocks) -> str | None:
    """B10 leakage guard — the option must not quote the twin's own context.

    Same frozen shingle test the D8 answer-leak guard uses. A generated option
    that reproduces a run from the grounding excerpts would let the twin arm
    string-match, which is the failure D6-v2 was built to prevent and which
    generation could reintroduce.
    """
    for block in grounding_blocks:
        if not block:
            continue
        hit = R.find_answer_leak(block, text, n=LEAK_SHINGLE_WORDS)
        if hit is not None:
            return hit
    return None


def names_subject(text: str, variants) -> list[str]:
    """Surviving name variants in a generated option (should be none)."""
    return R.surviving_variants(text or "", variants)


def match_rung(true_answer: str, options) -> int | None:
    """B10.6 — the tightest D6 ladder rung the whole option set satisfies.

    Same ladder as the pilots so the number means the same thing across rounds.
    ``None`` means even the loosest rung is missed, which the caller logs and
    the report states rather than silently accepting.
    """
    true_words = R.word_count(true_answer)
    true_bucket = density_bucket(entity_density(true_answer))
    for rung, (tol, adjacent) in enumerate(RELAX_LADDER):
        lo, hi = true_words * (1 - tol), true_words * (1 + tol)
        allowed = ADJACENT_BUCKETS[true_bucket] if adjacent else {true_bucket}
        if all(lo <= R.word_count(o) <= hi
               and density_bucket(entity_density(o)) in allowed
               for o in options):
            return rung
    return None


def shuffle_seed(item_id: str) -> int:
    """SPEC D6's seed, unchanged, so option order stays item-stable."""
    return int(hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:8], 16)


__all__ = [
    "entity_tokens", "N_GENERATED", "N_DISTRACTORS", "COPY_JACCARD", "LEAK_SHINGLE_WORDS",
    "GEN_TEMPLATE", "PARA_TEMPLATE", "POSITION_TEMPLATE", "CONTRA_TEMPLATE",
    "TEMPLATE_TEXT", "TEMPLATE_SHA256",
    "gen_prompt", "para_prompt", "position_prompt", "contra_prompt",
    "parse_generated", "parse_verdict", "parse_paraphrase",
    "looks_truncated", "era_violations", "copies_true", "quotes_grounding", "names_subject",
    "match_rung", "shuffle_seed",
]
