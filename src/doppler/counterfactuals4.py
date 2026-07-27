"""Round 4 additions to the B10 instrument — SPEC v1.10 (D6-v4).

Round 3 shipped B10's generated same-question counterfactuals and the
zero-information arm still solved 15 of 15 (mean margin +0.69). The gate's own
completions named three mechanisms, and round 4 attacks each one. Nothing here
changes round 3: ``counterfactuals.py`` and its ``TEMPLATE_SHA256`` are frozen,
this module carries its own ``TEMPLATE_SHA256_V4``, and round 3's artifacts stay
verifiable against the digest they were built with.

What round 3 measured, and what each round-4 change is aimed at:

1. **Speaker plausibility** (report 2.1, the +0.96 item). The model said options
   A-C "read more like an op-ed or a political speech than a natural response
   from an academic guest" and picked the one that "reflects the typical
   speaking style of a social science professor". The generator writes
   confident advocacy; real interviewees hedge. B10.4's paraphrase cannot fix
   it because the paraphrase must preserve every claim and the confidence is IN
   the claims. -> ``gen_prompt_v4`` conditions on the subject's OWN real
   answers as style exemplars and demands hedged, qualified speech.

2. **World truth** (report 2.2). B10.5 requires each distractor to CONFLICT
   with the true position, so when the true position is simply correct about
   the world, every conflicting alternative is wrong about it and a
   well-informed scorer wins on general knowledge without modelling anyone.
   -> an explicit instruction plus ``plausibility_prompt``, a separate check
   call that rejects factually-false and fringe alternatives.

3. **Conversational deixis** (report 2.3, the tightest item). The paraphrased
   true answer kept the host's first name from the transcript and the model
   cited it. -> ``apply_deixis_rule`` strips host names and second-person
   address from ALL FOUR options, or uniformly retains them, and records which
   per item.

Plus a supply decision: round 3's biggest margins sat on factual-explanation
questions, so ``classify_question`` splits the candidates and round 4 builds
the subjective-leaning subset first.

The generator is still never a scored model, and the B10.3 declared overlap
with the A3 robustness scorer is unchanged and still reported.
"""

from __future__ import annotations

import hashlib
import re

from doppler import counterfactuals as CF
from doppler import stage2_render as R

#: Style exemplars shown to the generator per item. Enough to establish a
#: register, few enough to leave the budget to the answers themselves.
N_STYLE_EXEMPLARS = 3

#: A stripped option this much shorter than the original means the deixis rule
#: ate the answer rather than its packaging; the whole SET is then retained
#: unstripped, because uniformity across the four options is the actual
#: requirement.
MIN_RETAIN_RATIO = 0.70


# ---------------------------------------------------------------------------
# Round-4 prompt templates. Frozen text + their own digest.
# ---------------------------------------------------------------------------

GEN_TEMPLATE_V4 = """\
You are helping build a multiple-choice comprehension test.

Below is a question a journalist asked a guest on American broadcast news, and \
the guest's ACTUAL answer. Write {n} ALTERNATIVE answers to the SAME question.

First, study how this guest actually talks. These are real answers the SAME \
guest gave in other interviews. Copy the REGISTER -- the hedging, the \
qualifications, the sentence rhythm -- but never the content.

{exemplars}

RULES, all mandatory:
1. Every alternative must directly answer the question that was asked.
2. Every alternative must take a position that GENUINELY CONFLICTS with the \
actual answer. Someone who believes an alternative would disagree with the \
actual answer on substance. Do not restate, soften, or partially agree with it.
3. The {n} alternatives must also differ from each other, not be {n} wordings \
of one position.
4. REGISTER, the most important rule. Write like the guest above actually \
writes: measured, hedged, qualified expert speech. Use hedges ("it depends", \
"the evidence is mixed", "I think", "to some extent", "we don't really know \
yet"), acknowledge complexity, and allow that the other side has a point. \
Do NOT write op-ed advocacy, campaign rhetoric, or a confident thesis \
statement. A real expert being interviewed almost never says a thing is \
"a total disaster" or "completely delusional"; they say it is "worrying" or \
"probably a mistake".
5. PLAUSIBILITY. Every alternative must be a position a reasonable, \
well-informed expert could ACTUALLY HAVE HELD at the time, given what was \
known then. Do not write anything factually false, invented, or fringe. A \
reader who knows the subject well must find every option defensible -- if \
three options are wrong about the world and one is right, the test measures \
general knowledge instead of this person's view.
6. Do NOT copy distinctive phrases or specific content from the actual answer \
or from the style examples.
7. Length: about {words} words each (between {lo} and {hi} words).
8. SPECIFICITY: the actual answer refers to about {ents} specific named things \
(people, places, organisations, numbers). Use a similar number in each \
alternative -- roughly {lo_e} to {hi_e}.
9. ERA: the interview took place on {date}. Nothing you write may mention or \
imply any event after that date. Naming people, places and organisations that \
already existed on that date is expected and wanted; avoid naming explicit \
calendar dates.
10. Never name the guest, and never refer to the guest in the third person.
11. Never address the interviewer. Do not use the interviewer's name, do not \
say "you" to them, and do not open with a vocative such as "Well, Robert," or \
"You know,".

QUESTION
{question}

ACTUAL ANSWER
{answer}

Output format -- exactly {n} blocks, nothing before, between, or after them \
except the markers:
{markers}
"""

PLAUSIBILITY_TEMPLATE = """\
A journalist asked the question below on American broadcast news on {date}. A \
proposed answer follows.

Judge ONLY whether the proposed answer is a position a reasonable, \
well-informed expert could actually have held on that date, given what was \
known at the time. Do not judge whether you agree with it, whether it is the \
majority view, or how well it is written. A minority view held by serious \
people is PLAUSIBLE.

- PLAUSIBLE: a defensible expert position on that date.
- FALSE: it asserts something that was already known to be untrue on that \
date, or invents events, people, or figures.
- FRINGE: not factually false, but a position essentially no serious expert \
held -- a conspiracy theory or a crank reading.

Reply with exactly one line:
VERDICT: PLAUSIBLE
or
VERDICT: FALSE
or
VERDICT: FRINGE
then a second line:
WHY: <one sentence>

QUESTION
{question}

PROPOSED ANSWER
{answer}
"""

#: Round 4 reuses round 3's paraphrase, position and contradiction templates
#: unchanged -- they are not what failed -- so the v4 digest covers only what
#: is new. Both digests are recorded in every round-4 artifact.
TEMPLATE_TEXT_V4 = "\n".join([GEN_TEMPLATE_V4, PLAUSIBILITY_TEMPLATE])
TEMPLATE_SHA256_V4 = hashlib.sha256(
    TEMPLATE_TEXT_V4.encode("utf-8")).hexdigest()

#: The unchanged round-3 templates this round still uses, recorded beside it.
TEMPLATE_SHA256_V3_REUSED = CF.TEMPLATE_SHA256


def format_exemplars(answers) -> str:
    """The style-exemplar block. Empty input is an explicit absence, not a gap.

    ``None`` entries are dropped rather than rendered. ``str(None)`` is the
    literal "None", which would have put ``STYLE EXAMPLE 1: None`` into the
    prompt for a guest whose exemplar lookup came back short.
    """
    rows = [" ".join(str(a).split()) for a in (answers or ())
            if a is not None and str(a).strip()]
    if not rows:
        return ("(No style examples were available for this guest, so match the "
                "register of the ACTUAL ANSWER below instead.)")
    return "\n\n".join(f"STYLE EXAMPLE {i} (same guest, different interview, "
                       f"content irrelevant):\n{t}"
                       for i, t in enumerate(rows, 1))


def gen_prompt_v4(question: str, answer: str, date: str, exemplars, *,
                  n: int = CF.N_GENERATED, tolerance: float = 0.15) -> str:
    """D6-v4.1 — conflicting answers in the guest's own hedging register.

    ``answer`` is the PARAPHRASED true answer, as in round 3: it is what the
    option set actually shows, and generating against the verbatim answer
    produced options outside the length ladder before any check ran.

    ``exemplars`` are real answers by the SAME guest from OTHER interviews.
    They are style conditioning only -- the caller must still guard the
    generated text against copying them, because a model shown three real
    answers can reach for their content as well as their rhythm.
    """
    words = R.word_count(answer)
    ents = CF.entity_tokens(answer)
    return GEN_TEMPLATE_V4.format(
        n=n, words=words, lo=int(words * (1 - tolerance)),
        hi=int(words * (1 + tolerance)), date=date,
        ents=ents, lo_e=max(0, ents - 2), hi_e=ents + 2,
        question=" ".join(question.split()),
        answer=" ".join(answer.split()),
        exemplars=format_exemplars(exemplars),
        markers=CF._markers(n))


def plausibility_prompt(question: str, answer: str, date: str) -> str:
    """D6-v4.3 — could a well-informed expert actually have held this?"""
    return PLAUSIBILITY_TEMPLATE.format(
        date=date, question=" ".join(question.split()),
        answer=" ".join(answer.split()))


PLAUSIBILITY_VERDICTS = ("PLAUSIBLE", "FALSE", "FRINGE")


def parse_plausibility(completion: str):
    """``(verdict, why)``; ``(None, ...)`` if unparseable. Never a guess."""
    return CF.parse_verdict(completion, PLAUSIBILITY_VERDICTS)


# ---------------------------------------------------------------------------
# D6-v4.2 Deixis stripping
# ---------------------------------------------------------------------------
#
# Round 3's tightest item was solved on "referring to him as 'Robert'". The
# paraphrase preserves the transcript's conversational packaging, and only the
# real answer has any, because only the real answer was spoken to a person.

#: Openers that address the interviewer rather than answer the question.
_ADDRESS_OPENERS = (
    "you know", "look", "well look", "as you said", "as you say",
    "as you know", "as you point out", "as you pointed out",
    "you're right", "you are right", "that's right", "sure",
    "well", "right", "yeah", "oh",
)

_SECOND_PERSON = re.compile(
    r"\b(?:as you (?:said|say|know|note|noted|point out|pointed out)|"
    r"you(?:'re| are) right|you know)\b[,\s]*", re.IGNORECASE)


def host_name_forms(labels) -> list[str]:
    """Name forms to strip, longest first, from raw host speaker labels.

    A MediaSum host label looks like ``ROBERT SIEGEL, HOST``. Both the full
    name and each name token are stripped, because the transcript says "Robert"
    where the label says "ROBERT SIEGEL".

    The FULL-name form keeps every alphabetic token; only the standalone-token
    forms drop short ones. Building the full name from the surviving tokens
    only turned "AL SHARPTON, HOST" into just ``["SHARPTON"]``, so
    "Al Sharpton is wrong" stripped to "Al is wrong" -- the tell half-removed,
    which is worse than not stripping at all because it also mangles the text.
    Short tokens are still excluded as STANDALONE forms, since stripping every
    "al" or "jo" out of an option would do real damage.
    """
    forms: set[str] = set()
    for label in labels or ():
        name = str(label).split(",")[0].strip()
        if not name:
            continue
        tokens = [t for t in re.split(r"\s+", name)
                  if t.replace(".", "").isalpha()]
        if not tokens:
            continue
        forms.add(" ".join(tokens))
        forms.update(t for t in tokens if len(t) > 2)
    return sorted(forms, key=len, reverse=True)


def strip_deixis(text: str, host_forms) -> tuple[str, list[str]]:
    """Remove interviewer address from one option. Returns ``(text, removed)``.

    Deliberately narrow. It removes vocatives, the interviewer's name, and a
    fixed list of address openers -- not every "you", because a guest saying
    "you can't fix this with policing" is talking about the world, not to the
    host, and mangling that would damage the option's meaning far more than the
    tell it removes.
    """
    removed: list[str] = []
    out = " ".join((text or "").split())

    for form in host_forms or ():
        pattern = re.compile(
            r"(?:^|(?<=[\s,;:]))" + re.escape(form) + r"\b[\s,]*",
            re.IGNORECASE)
        if pattern.search(out):
            removed.append(form)
            out = pattern.sub(" ", out)

    def _drop_opener(s: str) -> str:
        for opener in sorted(_ADDRESS_OPENERS, key=len, reverse=True):
            m = re.match(r"^\s*" + re.escape(opener) + r"\b[\s,]*", s,
                         re.IGNORECASE)
            if m:
                removed.append(opener)
                return s[m.end():]
        return s

    prev = None
    while prev != out:            # "Well, you know, Robert, ..." nests
        prev = out
        out = _drop_opener(out)

    hit = _SECOND_PERSON.search(out)
    if hit:
        removed.append(hit.group(0).strip())
        out = _SECOND_PERSON.sub(" ", out)

    out = _tidy_punctuation(out)
    if out:
        out = out[0].upper() + out[1:]
    return out, removed


def _tidy_punctuation(text: str) -> str:
    """Repair the punctuation a mid-sentence removal leaves behind.

    Load-bearing, not cosmetic. Removing a vocative that is not at the front
    strands its commas: "I think it's fine, Robert." became "I think it's fine,
    ." and "The situation, as you said, is worrying." became "The situation, is
    worrying." Those strings go straight into an option the scorer reads, so a
    stray " , ." in one option and not the others is a NEW formatting tell --
    exactly the kind of asymmetry D6-v4.2 exists to remove. The retain-ratio
    guard cannot catch it either, because the word count barely moves.
    """
    out = " ".join((text or "").split())
    out = re.sub(r"\s+([,;:.!?])", r"\1", out)     # " ," -> ","
    out = re.sub(r",\s*([.!?])", r"\1", out)       # ", ." -> "."
    out = re.sub(r"([,;:])\s*\1+", r"\1", out)     # ",," -> ","
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip().lstrip(",;: ").strip()


def apply_deixis_rule(texts, host_forms,
                      min_retain_ratio: float = MIN_RETAIN_RATIO):
    """D6-v4.2 — strip every option, or retain every option. Never a mixture.

    Uniformity IS the rule. Stripping only the options that happen to contain a
    vocative would leave exactly the asymmetry the strip exists to remove, so if
    any option would lose more than ``1 - min_retain_ratio`` of its words the
    whole SET is retained unstripped and the item records why.

    Returns ``(texts, record)`` where ``record["mode"]`` is ``"stripped"`` or
    ``"retained"`` and is written into the item artifact.
    """
    originals = [" ".join((t or "").split()) for t in texts]
    stripped, removals = [], []
    for text in originals:
        out, removed = strip_deixis(text, host_forms)
        stripped.append(out)
        removals.append(removed)

    too_short = [
        i for i, (a, b) in enumerate(zip(originals, stripped))
        if not b or (R.word_count(a)
                     and R.word_count(b) / R.word_count(a) < min_retain_ratio)
    ]
    if too_short:
        return list(originals), {
            "mode": "retained",
            "reason": "stripping would have removed more than "
                      f"{int((1 - min_retain_ratio) * 100)}% of option(s) "
                      f"{too_short}; the set is retained unstripped so all four "
                      "options carry the same packaging",
            "min_retain_ratio": min_retain_ratio,
            "forced_by_option_index": too_short,
            # What the strip WOULD have taken, kept so a reader auditing the
            # decision can see the evidence for it instead of re-running
            # strip_deixis by hand.
            "would_have_removed_per_option": removals,
            "would_have_produced": stripped,
            "removed_per_option": [[] for _ in originals],
            "n_options_changed": 0,
        }
    return stripped, {
        "mode": "stripped",
        "reason": "interviewer address removed from every option",
        "min_retain_ratio": min_retain_ratio,
        "removed_per_option": removals,
        "n_options_changed": sum(1 for r in removals if r),
    }


# ---------------------------------------------------------------------------
# D6-v4.4 Item-type classification
# ---------------------------------------------------------------------------
#
# Deterministic and documented rather than a model call: 15 questions do not
# justify an unauditable judgement, and a rule can be disagreed with line by
# line. Every matched cue is recorded so a reader can overrule a specific call
# instead of the whole split.

#: Asking the guest for their own view.
SUBJECTIVE_CUES = (
    "do you think", "did you think", "you think", "in your view",
    "in your opinion", "your perspective", "from your perspective",
    "your sense", "your read", "in your mind", "any doubt in your mind",
    "what do you make of", "how do you feel", "do you feel",
    "would you say", "is it fair to say", "do you expect", "do you believe",
    "for you", "how worried", "are you worried", "your take",
    "do you agree", "surprised", "stuck out", "strike you", "struck you",
)

#: Evaluative or forecasting frames that call for a judgement even when the
#: guest's own view is not named. Generic question forms, not topic words.
EVALUATIVE_CUES = (
    "to what extent", "how much of", "is there an opportunity",
    "is there enough", "is there still enough", "lost most", "the most",
    "the biggest", "the worst", "the best", "how likely", "any doubt",
    "seriously want", "turn out to be", "what happens next",
)

#: Modals that mark a prediction or an evaluation rather than a fact.
SUBJECTIVE_MODALS = ("could", "would", "might", "may", "should", "ought")

#: Asking what is or was the case, or what the evidence shows.
FACTUAL_CUES = (
    "do we know", "what happened", "what is the", "what are the",
    "how does", "how did", "how many", "what percentage",
    "explain", "walk us through", "what exactly", "tell us what",
    "why did", "why does", "why is", "what caused", "the evidence",
    "research show", "studies show", "data show", "statistics",
    "comes first", "happens first",
)


def _distinct_cues(cues, text: str) -> list[str]:
    """Matched cues with nested duplicates dropped.

    "do you think" also contains "you think", so a single phrase scored twice
    and the subjective/factual comparison is a raw count. Only the longest
    match at a given position is a distinct signal.
    """
    hits = [c for c in cues if c in text]
    return [c for c in hits
            if not any(c != other and c in other for other in hits)]


def classify_question(question: str) -> dict:
    """``subjective`` / ``factual_explanation`` / ``unclear`` for one question.

    Round 3's widest margins sat on factual-explanation questions, where B10.5
    forces every conflicting alternative to be wrong about the world (report
    2.2), so round 4 builds the subjective-leaning subset first.

    **This rule reports ``unclear`` when no cue fires, and does not pretend a
    no-evidence question is factual.** An earlier version broke 0-0 ties toward
    ``factual_explanation`` and mislabelled nine of round 3's fifteen questions
    -- "Is there an opportunity to change course in Syria?" is an assessment,
    not a fact, and scoring it zero on both sides is the rule admitting it has
    nothing to say. A tie with evidence on BOTH sides still resolves to
    ``factual_explanation``, because claiming an item is subjective is what
    buys it a place in the build.

    The cue lists were written while looking at the round-3 dev questions, so
    the rule is tuned on the set it scores. That is acceptable on dev subjects
    and stated rather than hidden -- and it is why the driver pairs this rule
    with a recorded hand classification and reports every disagreement.
    """
    text = " ".join((question or "").split()).lower()
    subj = _distinct_cues(SUBJECTIVE_CUES, text)
    evalu = _distinct_cues(EVALUATIVE_CUES, text)
    fact = _distinct_cues(FACTUAL_CUES, text)
    modals = [m for m in SUBJECTIVE_MODALS if re.search(rf"\b{m}\b", text)]

    score_s = len(subj) + len(evalu) + (1 if modals else 0)
    score_f = len(fact)
    if score_s == 0 and score_f == 0:
        kind = "unclear"
    elif score_s > score_f:
        kind = "subjective"
    else:
        kind = "factual_explanation"
    return {
        "kind": kind,
        "subjective_cues": subj,
        "evaluative_cues": evalu,
        "subjective_modals": modals,
        "factual_cues": fact,
        "score_subjective": score_s,
        "score_factual": score_f,
        "tie_broken_to_factual": score_s == score_f and score_s > 0,
        "no_cue_fired": score_s == 0 and score_f == 0,
    }


def copies_any(text: str, others, threshold: float = CF.COPY_JACCARD) -> bool:
    """Did a generated option copy a style exemplar (or any other text)?"""
    return any(CF.copies_true(text, o, threshold) for o in others if o)


def quotes_any(text: str, others, n: int = CF.LEAK_SHINGLE_WORDS):
    """Shared n-gram between a generated option and any exemplar, or None.

    The style exemplars are real speech by the subject. Showing them to the
    generator is safe -- the generator is never scored -- but an option that
    reproduces a run from one of them puts real transcript text into a
    "generated" slot, which is the failure D6-v3.7's grounding-quote guard
    exists to prevent, arriving by a new route.
    """
    for other in others or ():
        if not other:
            continue
        hit = R.find_answer_leak(other, text, n=n)
        if hit is not None:
            return hit
    return None


__all__ = [
    "N_STYLE_EXEMPLARS", "MIN_RETAIN_RATIO",
    "GEN_TEMPLATE_V4", "PLAUSIBILITY_TEMPLATE",
    "TEMPLATE_TEXT_V4", "TEMPLATE_SHA256_V4", "TEMPLATE_SHA256_V3_REUSED",
    "format_exemplars", "gen_prompt_v4", "plausibility_prompt",
    "PLAUSIBILITY_VERDICTS", "parse_plausibility",
    "host_name_forms", "strip_deixis", "apply_deixis_rule",
    "SUBJECTIVE_CUES", "EVALUATIVE_CUES", "SUBJECTIVE_MODALS", "FACTUAL_CUES",
    "classify_question",
    "copies_any", "quotes_any",
]
