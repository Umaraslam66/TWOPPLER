# Stage 2 eval harness — design contract (v1, session 2026-07-26)

Owner-approved build order: (a) Q-A extraction + A4 distractor controls,
(b) same-domain imposter, (c) contamination meter, (d) 5-subject pilot, STOP.
No confirmatory runs. Classifier + pilot <= 3 node-hours. No Gemini calls at all
in the pilot. This SPEC is the single source of design decisions; deviations
require the orchestrator's sign-off, not the implementer's.

## Repo context (binding)

- Repo: /Users/umaraslam/Projects/DOPPLER. Python via `uv run`. Tests: `uv run pytest tests/test_<module>.py`.
- Patterns to copy: leakage guards (src/doppler/gym.py:90-120), frozen pure-stdlib
  prompt renderers with sha256 (src/doppler/adaptive_render.py), batch export/ingest
  (src/doppler/backends.py BatchFileBackend, write_prompts_jsonl/read_completions join on idx),
  cost ledger (src/doppler/costlog.py -> results/cost_log.jsonl),
  sbatch generation (experiments/confirm_run.py:290-360).
- Git: commit ONLY your own new files. The working tree has pre-existing dirty files
  (.claude/CLAUDE.md, experiments/overnight.py, src/doppler/adaptive.py,
  src/doppler/eig_render.py, results/*/config.json, and untracked dirs) — NEVER
  `git add -A`, never touch those. Small single-purpose commits, message style like
  `git log --oneline -5`, end body with: Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
- data/ is gitignored and stays that way. results/stage2_pilot/ artifacts ARE committed.
- PREREGISTRATION.md + PREREGISTRATION_AMENDMENT_1.md are the contract. PREREGISTRATION_AMENDMENT_2.md
  is an UNCOMMITTED DRAFT — do not commit it, do not rely on its numbers being final.

## Data sources

- Candidate pool: results/stage2_candidate_pool_v2.csv (1,153 rows). Subject ID = `canonical_id`
  (e.g. C00344). Columns used: canonical_name, clean, qualifies, wiki_status ('long-tail' vs other),
  ambiguous_identity, variants, transcripts (";"-joined items `TID|date|program|cluster_id|S`,
  trailing flag S=substantive).
- Raw transcripts: data/mediasum/news_dialogue.json (4.45 GB single JSON array; keys id, program,
  date, title, summary, utt[list], speaker[list]). Stream with experiments/mediasum_index.py:185
  stream_records() — never load whole file. data/mediasum_index/_scan_cache_v2.pkl may already hold
  what you need; check it before streaming.
- Speaker role classifier: experiments/mediasum_index.py:127 classify_speaker().

## Module layout (one implementer per task, files are disjoint)

- T1 src/doppler/stage2_data.py + experiments/stage2_draw_dev.py
- T2 src/doppler/qa_extract.py + src/doppler/distractors.py
- T3 src/doppler/imposter2.py
- T4 src/doppler/stage2_render.py
- T5 src/doppler/followup_render.py
- T6 experiments/stage2_pilot.py
- tests/test_<module>.py per module, deterministic, no network, synthetic fixtures.

## Frozen design decisions

### D1. Dev subjects (T1)
- Eligible: qualifies == True, clean == True, ambiguous_identity falsy.
- Draw: random.Random(47).shuffle over eligible canonical_ids sorted lexicographically;
  take the FIRST 3 with wiki article (wiki_status != 'long-tail') and FIRST 2 long-tail
  in shuffled order. Record seed, rule, and the full shuffled order position of each pick.
- If a drawn subject is later found broken (identity collision etc.), it stays burned
  (still a dev subject forever); the replacement is the next same-stratum id in the
  shuffled order. Record any such event.
- Output: results/stage2_pilot/dev_subjects.json
  {seed: 47, rule: "<one-paragraph description>", drawn_at: "<ISO date>",
   subjects: [{canonical_id, canonical_name, wiki_status, shuffle_pos}]}

### D2. Chronological split (T1)
- Use only substantive transcripts (flag S) from the `transcripts` column, grouped by cluster_id
  (a cluster = one real interview event; re-airings share a cluster). Cluster date = earliest
  date in cluster; cluster representative transcript = the one with most guest words
  (tie: lexicographically smallest transcript_id).
- test = the cluster with the LATEST date. grounding = all clusters with date STRICTLY earlier.
  Any other cluster sharing the test date is EXCLUDED entirely (same-event leak guard).
  Tie for latest date resolved by representative transcript_id lexicographic order (largest last).
- Output per subject: results/stage2_pilot/subjects/<canonical_id>/split.json
  {canonical_id, rule, grounding: [{cluster_id, transcript_id, date, program, title}],
   test: {cluster_id, transcript_id, date, program, title}, excluded_same_date: [...]}

### D3. Turn extraction (T1)
- For each split transcript, emit turns: {transcript_id, turn_idx, role, speaker_label, text}.
  role = "guest" if the speaker label matches the subject (canonical_name or any of `variants`,
  case-insensitive, honorific-tolerant); "host" if classify_speaker() says staff/host/anchor;
  else "other".
- Files: subjects/<cid>/grounding_turns.jsonl and test_turns.jsonl.
- D3.1-r2 (v1.2, supersedes D3.1 after review): within-transcript surname resolution.
  (a) Label cleaning BEFORE shape analysis: strip parenthetical/bracketed stage directions
  ("(voice-over)", "(via phone)", "(through translator)" and the like — they are neither
  role descriptors nor names); drop non-honorific tokens ending in "." from the name part
  ("UNMOVIC." in "UNMOVIC. ROTH" is corpus noise, not a first name; MR./MS./DR. survive).
  (b) Registration requires a name part of >= 2 tokens OR an explicit role word from a
  fixed list (ANCHOR/HOST/CORRESPONDENT/REPORTER/BYLINE/...); punctuation shape alone
  ("(", ",", dash) never registers.
  (c) Resolution: a bare surname resolves iff exactly one registered MULTI-token name has
  that last token. A registered single-token key equal to the last token of a registered
  multi-token key is the SAME person (merge), not an ambiguity.
  (d) Guest matching is token-subsequence containment, not exact key equality: a label
  matches the subject when the canonical/variant name-key tokens appear as a contiguous
  subsequence of the label's name-key tokens or vice versa, with >= 2 tokens in common
  ("afsane bassir pour" matches "bassir pour").
- D2 guard hardening (v1.2): the same-date exclusion tests EVERY member transcript date of
  a grounding cluster against the test date (a cluster is excluded from grounding if ANY
  member is dated on/after the test cluster's date), not just the cluster min date.

### D4. Q-A extraction from the test interview (T2)
- A Q-A item: host turn (the question) immediately followed by >= 1 guest turn.
  question_text = host turn text; answer_text = concatenation of consecutive guest turns
  until the next non-guest turn.
- Filters: question >= 5 words; answer 30..400 words (v1.1: floor lowered from 40 after
  observed pilot yield) (if > 400, truncate at the sentence
  boundary nearest 300 words and set flag "truncated"); question must contain "?" OR start
  with an interrogative/imperative cue (what/why/how/when/where/who/tell/describe/do/did/
  is/are/was/were/can/could/would/will, case-insensitive first word).
- Drop the first host turn of the transcript if the guest has not spoken yet (intro).
- Near-duplicate questions within a transcript (>= 0.8 Jaccard over word sets) keep first only.
- Cap: first 20 surviving items in turn order. item_id = "<canonical_id>:<transcript_id>:<q_turn_idx>".
- Output: subjects/<cid>/qa_items.jsonl
  {item_id, canonical_id, transcript_id, q_turn_idx, question, answer, answer_words, flags: []}

### D5. Entity heuristic (T2; shared helper in distractors.py, used by T4 too)
- Pilot-grade documented heuristic (upgrade to real NER is a bar-lock decision, NOT yours):
  entity tokens = (a) maximal spans of capitalized tokens ([A-Z][\w'’.-]*) where the span is
  not solely sentence-initial, (b) numbers with >= 2 digits, (c) $/%-amounts.
- entity_density = entity tokens / total tokens (whitespace tokens).
- Density buckets: Z: 0..0.02, L: 0.02..0.08, H: > 0.08.
- strip_entities(text): replace each capitalized span with "[NAME]", each number with "[NUMBER]".
- All counts in words (whitespace tokens); word counts are the pilot's token proxy, documented.

### D6. Distractor bank + selection (T2)
- Bank: seeded sample of 200 OTHER qualifying clean subjects (random.Random(48) over sorted
  eligible ids, excluding the 5 dev subjects), extract Q-A items (rules D4) from each donor's
  LATEST cluster representative transcript only. Bank rows carry {question, answer, answer_words,
  entity_density, bucket, source_canonical_id, source_transcript_id}. Persist bank to
  results/stage2_pilot/distractor_bank.jsonl (committed; ~2k rows expected).
- Per item: candidates = bank rows with different source subject, answer_words within +-20% of
  the true answer, same density bucket. Rank by question similarity: sklearn TfidfVectorizer
  (word 1-2 grams, lowercase) fit on bank questions + the query; cosine. Take top 3.
- Relaxation ladder if < 3 candidates: widen length to +-30%, then allow adjacent bucket,
  then widen to +-50%. Record which rung was used per item in flags. Never relax "different subject".
- Position shuffle: random.Random(int(sha256(item_id)[:8], 16)) shuffles the 4 options.
- Output: subjects/<cid>/distractors.jsonl
  {item_id, options: [{text, kind: "true"|"distractor", source_canonical_id, source_transcript_id,
   answer_words, entity_density}], correct_index, relax_rung, options_stripped: [same order,
   entity-stripped texts]}

### D7. Same-domain imposter (T3, Amendment A1)
- Representation: per subject, concatenated guest-role text from GROUNDING clusters only.
- Donor pool: the same 200-subject bank sample (their grounding-side text), plus the other
  4 dev subjects are NOT eligible donors (keeps dev arms independent).
- donor(X) = argmax TF-IDF cosine similarity to X among eligible donors with >= 2500 words of
  grounding text; exclude donors whose name fuzzy-matches X (token overlap or difflib
  ratio >= 0.7 on any name variant). Deterministic; ties by lexicographic canonical_id.
- Record results/stage2_pilot/imposter_pairs.json: {method, pairs: {cid: donor_cid},
  similarity, runner_up_top5: {cid: [[donor, sim] x5]}}.

### D8. Prompt shapes (T4; pure stdlib, sha256-recorded, adaptive_render.py conventions)
All prediction prompts elicit a DISTRIBUTION over options (Stage 1E dual-decoding lesson:
score argmax accuracy AND probability-mass-on-correct):
final line format the model must produce: "A: <p> B: <p> C: <p> D: <p>" summing to ~1.
Parser: tolerant of separators, renormalizes if sum in [0.8, 1.2], else parse failure.

Arms (5):
1. twin_redacted (PRIMARY): grounding excerpts with ALL subject name variants replaced by
   "GUEST" (case-insensitive replacement, longest variant first). Preamble: reads past
   interview excerpts with one person ("GUEST"), then must answer as GUEST would in a LATER
   interview. Segments rendered as "[Interview, <date>, <program>]\nHOST: ...\nGUEST: ..."
   in chronological order. Then the question + 4 options (A-D) + distribution instruction.
2. twin_named (exploratory): identical + one line "GUEST is <canonical_name>." before excerpts.
3. zeroinfo_redacted: NO excerpts, NO program, NO date. "A person was interviewed on American
   broadcast news. Predict which answer they gave." + question + options + instruction.
4. zeroinfo_named: same as 3 + "The person is <canonical_name>."
5. imposter_redacted: byte-identical template to arm 1 but excerpts come from the DONOR's
   grounding (donor name variants also replaced by "GUEST"). The prompt never reveals either name.
- Contamination meter (Task 2c) = per-subject accuracy(zeroinfo_named) - accuracy(zeroinfo_redacted).
- Grounding budget B_pilot = 2000 words per prompt. Segment selection for the pilot twin arms:
  most-recent-first greedy fill of whole HOST+GUEST exchange segments until budget, then render
  chronologically. (H2's selection-policy arms come later; NOT in this pilot.)
- LEAKAGE GUARDS (hard asserts, gym.py style): (a) no 10-word shingle of the true answer may
  appear in the grounding block; (b) test-interview text must never enter grounding; (c) in
  redacted arms, no name variant of the subject (or donor) may survive in the rendered prompt.
  Guard (c) may pass only after replacement; assert on final rendered string.
- Renderer exposes sha256() of each rendered prompt, and render functions are pure
  (dict in -> string out), stdlib only, so the file can be rsynced to the node unchanged.

### D9. Follow-up classifier rubric (T5; pure stdlib renderer + parser)
- classify only host turns that FOLLOW at least one guest turn in the same transcript;
  the transcript's first host turn is NEW-TOPIC by definition (no model call, label emitted
  with source="rule").
- Prompt inputs: prev host turn (last 60 words), the guest's intervening answer (last 120 words),
  target host turn (first 120 words). Output contract:
  "LABEL: FOLLOW-UP" or "LABEL: NEW-TOPIC" then "WHY: <one sentence>".
- Rubric (DRAFT status until bar-lock; string constant RUBRIC_V1 + RUBRIC_SHA256):
  FOLLOW-UP = the turn references, quotes, probes, or challenges the content of the guest's
  preceding answer (incl. minimal continuers like "Go on", "Meaning what?").
  NEW-TOPIC = introduces material not derived from the preceding answer (prepared/agenda
  question, topic switch, segment transition), INCLUDING acknowledgment-then-pivot
  ("Fascinating. Now let's talk about X") and returns to the interviewer's own earlier
  agenda that ignore the intervening answer.
  Include exactly 4 SYNTHETIC few-shot examples (2 per label, hand-written, no corpus text).
- Parser: regex for the LABEL line; anything else = parse failure (caller may retry twice).

### D10. Pilot driver (T6) — separate brief will follow; do not build it yet.

## Review + reporting contract (every task)
- Write your full report to the report file path given in your dispatch prompt.
- Return only: STATUS (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED), commit hashes,
  one-line test summary, concerns.
- Acceptance floor: tests pass (`uv run pytest tests/ -q` green for YOUR files and the
  pre-existing suite untouched), no network in tests, deterministic outputs given seeds.

## v1.2 amendment — D7-r2 (orchestrator-approved after pilot evidence)
The D7 TfidfVectorizer drops terms with document frequency > 0.9 across the matching corpus
(raw-count vectors were dominated by register-carrying conversational filler, collapsing
topically-unrelated subjects onto a single donor). Donor multiplicity (one donor serving
several subjects) remains allowed but is REPORTED; any hard cap is a bar-lock decision.
The matched donors also get donors/<cid>/{split.json, grounding_turns.jsonl} artifacts
(needed to render D8 HOST/GUEST segments).

## v1.3 amendment — D3.2 program-name host rule (orchestrator-approved after T1 re-review)
After D3.1-r2 resolution, a speaker label (resolved or direct) whose descriptor part —
the text after the name, cleaned of stage directions — case-insensitively equals or
contains the record's own `program` value is classified "host" (it is the show's anchor;
CNN labels anchors "NAME, PROGRAM NAME" with no role word). Applies before the "other"
fallback; never overrides a guest match. Labels with no full-name form anywhere in the
transcript remain unresolvable ("other") — accepted.
Also: excluded_same_date entries carry a `reason` field ("shares_test_date" vs
"member_on_or_after_test").

## v1.4 amendment — D5-r2 entity heuristic fixes (orchestrator-approved after T2 evidence)
(a) The pronoun family I / I'm / I've / I'd / I'll (case-exact "I" forms) is never an
entity token. (b) Capitalized spans break at sentence boundaries (. ! ? followed by space)
— "Absolutely. He" is not a span. Everything else in D5 stands. Bucket boundaries unchanged.
Consequence: bank + distractor artifacts rebuilt; nothing had been scored against the old
buckets. C00292 stays burned_for_qa despite its post-D3.1-r2 yield of 1 (the burn decision
is recorded and does not flip on yield drift).

## v1.5 amendment — D3.2 fuzzy extension (orchestrator-ruled after typo evidence)
MediaSum program values contain typos ("Diplomatic Linense"), so D3.2 becomes:
literal-or-containment OR fuzzy(normalised descriptor, normalised program) >= 0.60
(normalise = strip parentheticals, leading network word, punctuation, casefold; difflib
ratio). Every fuzzy conversion records its ratio + matched program string (auditable).
Threshold 0.60 is PROVISIONAL pending bar-lock review (measured separation: true anchor
0.680 vs best non-anchor 0.379; corpus-wide fire rate 3.42% of cached transcripts).
Safeguards unchanged: never overrides guest match; no-full-name turns stay "other".

## v1.6 amendment — D5-r3 abbreviation-dot guard (orchestrator-approved)
A trailing "." does not end a sentence for D5-r2(b) span-breaking when the dotted stem is
in the HONORIFIC set, contains an internal dot ("U.S."), or is a single initial. Protects
the A4.2 entity-stripped variant ("Mr. Morsi" must strip "Morsi", not strand it
sentence-initial). Folded into the same rebuild as D5-r2.

## v1.7 amendment — D4 cue clarification + D6-r2 distinct donors (post T2 review)
D4 cue rule, clarified: strip leading parenthetical stage directions ("(LAUGHTER)"), then
apply the cue test to the LITERAL first word — no skipping of numeric or other tokens
("1-800-... is our number" is not a question; "(LAUGHTER) What..." is).
D6-r2: an item's 3 distractors must come from 3 DISTINCT donors; if the matched candidate
set cannot supply 3 distinct donors, fall through the existing relaxation ladder before
permitting a duplicate at the final rung (record it in flags).
Known A4.2 limitation on record (bar-lock NER item): a single-token proper noun opening a
sentence survives entity-stripping under D5's sentence-initial rule.

## v1.8 amendment — D6-v2 same-subject distractors (owner decision D-B, pilot round 2)

Supersedes D6 and D6-r2 for the round-2 build ONLY. Round 1's artifacts under
results/stage2_pilot/ are frozen and untouched; round 2 writes to
results/stage2_pilot2/ and reads round 1 read-only. Implemented in
src/doppler/distractors_v2.py + experiments/stage2_pilot2.py.

Why: the round-1 zero-information arm scored 17/17 (pilot report 8.0). Wrong
options were other people's answers to unrelated questions, so topical coherence
alone won every item. Under D6-v2 speaker and general subject matter are
controlled by construction and only the specific answer differs.

### D6-v2.1 Pool (same-subject only, no cross-person fallback)
- Source: EVERY transcript the subject appears in EXCEPT (a) the test cluster and
  (b) any cluster D2 excluded for sharing the test date. Substantive AND
  non-substantive transcripts both qualify — the S flag is a rule about which
  interviews may ground or test a subject (D2), not about whose voice it is, and
  a non-substantive transcript is never rendered so it cannot leak. (In this
  pilot the b-set is empty for all 5 subjects.)
- D4 extraction is run per transcript, unchanged. A pool row carries
  {question, answer, answer_words, entity_density, bucket, source_canonical_id,
  source_transcript_id, source_q_turn_idx, source_cluster_id, source_date,
  source_program, source_substantive, flags}.
- Pool-level near-duplicate dedup: word-set Jaccard >= 0.8 (D4's
  NEAR_DUP_JACCARD) against an already-kept row drops the later one, ordered by
  (source_transcript_id, source_q_turn_idx). This replaces D6-r2's
  "3 distinct donors", which is meaningless once every option is one person; it
  targets the real failure mode, a re-aired interview supplying one answer
  three times. Fired 0 times in this pilot.

### D6-v2.2 Anti-leak against the twin's own context (mandatory, counted)
- A candidate whose answer shares ANY 10-word shingle with the SUBJECT'S
  RENDERED grounding block is excluded. The test is the frozen D8 guard-(a)
  function stage2_render.find_answer_leak (casefolded, punctuation-insensitive
  shingles), so the admission rule and the leak guard are literally the same
  code. Answers under 10 words fall back to whole-string containment.
- Run TWICE — raw answer vs raw rendered grounding, and redacted answer vs
  redacted rendered grounding — because redaction rewrites names on one side
  only. Either hit excludes. The excluded row records the shingle and the side.
- The rendered block is the twin arms' 2,000-word D8 block, so the rule is
  effectively "was this exchange shown to the twin?". Exclusions are counted per
  subject and written to subjects/<cid>/pool_excluded.jsonl.
- Rationale: without it the twin arm could string-match a distractor out of its
  own context and score for a reason unrelated to modelling a person.

### D6-v2.3 Ambiguity guard (implementer-added, FLAGGED FOR SIGN-OFF)
A candidate whose answer has word-set Jaccard >= 0.8 against the item's TRUE
answer is excluded and counted (`pool_excluded_duplicate_of_true`). Two correct
options is not a forced choice. Same threshold/machinery as D4's near-duplicate
question rule. NOT in the owner's brief; added because same-subject distractors
make duplicate-correct a live risk for the first time. Fired 0 times here.

### D6-v2.4 A4 controls and the ladder (unchanged from D6)
Length within +-20% of the true answer, matching entity-density bucket (D5
buckets, unchanged), then D6's relaxation ladder
[(0.20,False),(0.30,False),(0.30,True),(0.50,True)]. The rung used is recorded
per item in `relax_rung` and in flags. Never relaxed: "same subject".

### D6-v2.5 No fallback; unfillable items are not built
If a rung cannot supply 3 candidates from the subject's own pool, the item is
NOT built. There is no cross-person fallback of any kind. Unbuilt items are
written to subjects/<cid>/unfillable.jsonl with the pool size, the true answer's
words/bucket and the best rung's candidate count, and counted per subject.

### D6-v2.6 Question similarity: recorded, not yet enforced
- Per candidate: TF-IDF cosine between its SOURCE question and the item's
  question. TfidfVectorizer(word 1-2 grams, lowercase) fitted ONCE on a fixed
  corpus — every dev subject's pool questions plus every test question — instead
  of D6's per-query refit on the bank. Reason: a v2 pool holds tens of documents,
  not thousands, and IDF from ten documents is noise; one yardstick also makes
  the floor sweep comparable across subjects. The corpus size, vocab size and
  sha256 are recorded in build_summary.json.
- Selection ranks candidates by this cosine descending, ties by
  (source_transcript_id, source_q_turn_idx), and takes the top 3.
- The BUILD applies floor = 0.00. Every distractor's similarity is written to
  disk, and build_summary.json carries a yield-vs-floor sweep over
  {0.00, 0.02, 0.05, 0.10, 0.15, 0.20}. **Freezing an admission floor is a
  bar-lock decision for the owner, not the implementer's.**

### D6-v2.7 Build-time zero-information gate (two phases)
- Phase 1 exports ONE prompt per candidate item: the `zeroinfo_redacted`
  standard-variant prompt, rendered by the unmodified D8 renderer.
- Gate rule, applied after the run: an item the zero-information arm
  argmax-solves NEVER enters the final set. An item whose gate reply does not
  parse is also held out. Rejections are counted in gate_results.json and
  finalize_summary.json.
- **Reporting rule (binding).** Gate and scoring use the same model at
  temperature 0, so POST-gate zero-info accuracy is ~0 BY CONSTRUCTION and is
  not evidence of anything. The instrument-difficulty number is PRE-GATE
  zero-info accuracy on the candidate set, recorded as
  `pre_gate_zeroinfo_argmax_accuracy`. Both artifacts are kept; the candidate
  set is never overwritten by the final set.
- Phase 2 exports the ten prediction sets (5 arms x 2 option variants) over the
  survivors only.

### D6-v2.8 Position shuffle, invariants, provenance
- Shuffle seed unchanged: random.Random(int(sha256(item_id)[:8],16)).
- Asserted at build AND re-asserted at verify: every option's
  source_canonical_id is the subject; no distractor comes from the test
  transcript; no (transcript_id, q_turn_idx) is used twice in one item;
  correct_index is read off after the shuffle from the option marked "true";
  the true option's text is byte-identical to round 1's qa_items answer.
- build_summary.json records the sha256 of every round-1 artifact consumed
  (dev_subjects, imposter_pairs, and each subject's split / qa_items /
  grounding_turns), so both rounds can be proven to share a draw and a split.

### D6-v2.9 DIAGNOSTIC variants (orchestrator-authorised, post-gate)

NOT arms. Never a fidelity number, never a bar, never in a lift table. They
exist only to decompose the phase-1 gate result (zero-information arm solved
10/10 candidate items, margins +0.80..+1.00). Implemented in
src/doppler/diagnostics_v2.py; **the frozen D8 templates in stage2_render.py are
not touched** and the D8 answer-format instruction and option renderer are
reused verbatim so the same frozen parser reads both.

- **DIAGNOSTIC A — entity-stripped gate (`gate_stripped`).** The frozen
  `zeroinfo_redacted` template, standard renderer, called with A4.2's
  entity-stripped option texts. No new template at all. Measures how much of
  the solve rides on named entities and numbers — which matters because D2
  makes the test interview the latest by construction, so every distractor is
  systematically older (measured mean gap 5.0 years on this set) and dated
  entities mark the true answer.
- **DIAGNOSTIC B — question-blind gate (`gate_qblind`).** Zero-information,
  standard option texts, HOST QUESTION REMOVED. Measures how much rides on the
  true answer being *responsive* to the question shown, versus cues intrinsic to
  the options. Two new constants, both minimal deviations, both frozen by their
  own digest `QB_TEMPLATE_SHA256` (separate from D8's `TEMPLATE_SHA256`):
  - `QB_PREAMBLE` = D8's `ZEROINFO_PREAMBLE` **first sentence verbatim**. D8's
    second sentence ("The person is called GUEST in the question below.") is
    dropped because there is no question below.
  - `QB_CHOICE_LINE` = D8's `CHOICE_LINE` with who="the person" plus the clause
    "in this interview", required because with the question removed "these
    replies" has no referent.
  - Guards: `assert_question_blind` refuses a prompt containing a `HOST:` line,
    an excerpt block, or any 6-word run of the item's own question; the standard
    D8 redaction assert still runs.
- Both run in ONE sbatch job (one engine init). Baseline for both is the
  phase-1 gate on the same items.
- Reporting: a diagnostic number is reported beside its baseline and labelled
  DIAGNOSTIC, never alone.

### D6-v2.10 Doubled-distribution parse artifact (measurement issue, on record)
D8's parser renormalises only when the stated mass lands in [0.8, 1.2]. Gemma-4
sometimes prints the SAME distribution twice — once as four lines, once as one —
so the stated mass is ~2.0 and a clearly-answered item is recorded as a parse
failure. Measured: 2 of 10 round-2 gate prompts, and **2 of 170 round-1
prediction prompts** (`pred_imposter_redacted_stripped` idx 0,
`pred_twin_named_stripped` idx 4) — the same artifact in both rounds, and in
every case the recovered answer was argmax-CORRECT.
The frozen parser is NOT changed here. `relaxed_reread` re-reads the last
distribution line and its output is recorded as an explicitly-labelled
DIAGNOSTIC (`parse_failure_diagnostic`), so a report can state both the frozen
verdict and what the reply actually said. Whether to widen the parser (e.g.
"take the last distribution line") is a BAR-LOCK decision, not the
implementer's — it changes N in every arm of every table.

## v1.9 amendment — B10 generated same-question counterfactuals (pilot 3)

Binding design is **PREREGISTRATION_AMENDMENT_2.md B10** (commit 9949c9d);
where this section and B10 differ, B10 wins. Supersedes D6 and D6-v2 as the
distractor rule. Rounds 1 and 2 stay frozen; round 3 writes only to
results/stage2_pilot3/ and reads rounds 1-2 read-only.
Implemented in src/doppler/counterfactuals.py + experiments/stage2_pilot3.py.

### D6-v3.1 Item supply
The FULL D4-eligible test-interview item set (17 items over 5 Q-A dev
subjects). Round 2's 10-item ceiling came from same-subject pool scarcity;
distractors are now written, not harvested, so supply is not the constraint.
C00292 stays burned_for_qa and is excluded from every prediction set.

### D6-v3.2 Generator and separation (B10.3)

**Generator: `gemini-3.5-flash-lite`** (owner directive 2026-07-27, final —
the cheapest model). Exact string recorded in every artifact.

#### D6-v3.2a Generator history — two switches, both owner cost directives

B10.3 requires the exact generator version per run, so a mid-round switch is
precisely what must not be silent. Both are recorded in
`stage2_pilot3.GENERATOR_HISTORY` and in `build_summary.json`.

1. **`gemini-3.1-pro-preview` → `gemini-3.5-flash`** — owner cost directive.
   Five items had already been built on Pro when the redirect came. They are
   kept **untouched as an audit trail** under
   `results/stage2_pilot3/genlog_pro_abandoned/` and `items_pro_abandoned/`,
   and **none of them enters a final set**: a set must have ONE generator and
   one version string, so all 17 items were regenerated from scratch on the
   final generator. The Pro spend is billed as its own superseded cost-ledger
   line.
2. **`gemini-3.5-flash` → `gemini-3.5-flash-lite`** — owner directive
   2026-07-27, final. Cheapest available. No call was ever made on
   `gemini-3.5-flash`.

#### D6-v3.2b Declared overlap with the A3 robustness scorer (B10.3)

The generator now **IS** the Amendment 1 A3 robustness scorer. B10.3 provides
for this in terms ("if operational constraints ever force the same version,
that overlap is reported beside every robustness number it touches"); the
constraint here is the owner's cost directive. The overlap is **declared, not
engineered away**, and the declaration string
(`stage2_pilot3.B10_3_OVERLAP_DECLARATION`) is carried in `build_summary.json`,
`config.json`, the gate export manifest, and the pilot report. It states three
things:

- **(a) Inert in this pilot.** Round-3 scoring is Gemma-4-31B-it only. No
  Gemini model scores anything, anywhere in round 3, so no model reads its own
  writing at any point.
- **(b) Live at the confirmatory stage.** Either the generator is changed to a
  different model at bar-lock, or every A3 robustness number computed on this
  instrument carries the overlap flag beside it. **A bar-lock decision for the
  owner, not the implementer's.**
- **(c) Mitigating symmetry.** D6-v3.5 sends all four options — *including the
  paraphrased true answer* — through one byte-identical paraphrase call on this
  same model. No option is stylistically closer to the generator than any
  other, so a self-preference effect would have to distinguish text the model
  wrote from text it only rewrote, not model style from corpus style.

What B10.3 still enforces as a **hard build-time failure** is the invariant
that survives the switch: the generator is never a model this pilot SCORES
(`stage2_pilot3.SCORED_MODELS`). The old check — refuse to run if the generator
equals the robustness scorer — is replaced by that one, because it would now
refuse the owner's chosen generator.

#### D6-v3.2c Temperatures and measured token budgets

Temperatures unchanged: generation 0.7 (diversity), paraphrase and both checks
0.0.

**Budgets were re-measured for this generator; Pro's do not transfer.** Pro
charges hidden thinking against `max_output_tokens`, so its 16,384/16,384/8,192
were mostly thinking headroom. `doppler.gemini` sends flash-lite **no thinking
config at all**, and the 2026-07-27 probe measured `thoughts_token_count == 0`
on all 15 calls — the budget is visible output and nothing else.

Measured on the worst-case item `C02013:NPR-9480:70` (318-word answer):

| step | worst measured visible tokens | truncation floor | frozen budget |
|---|---|---|---|
| generate (4 blocks) | 1,555 (finish STOP, 4/4 blocks) | 1,024 → `MAX_TOKENS`, 4th block 10 words | **8,192** |
| paraphrase | 253 | not truncated even at 512 | **2,048** |
| position / contradiction check | 43 | not truncated even at 128 | **1,024** |

A generous budget costs nothing — billing is on tokens produced, not on the
budget — so each is set well above its worst measurement. The
`looks_truncated` refusal (D6-v3.5) remains the runtime backstop.

### D6-v3.3 Pipeline order (differs from B10's listing order, deliberately)
The true answer is paraphrased FIRST and the counterfactuals are generated
AGAINST THE PARAPHRASE, because the paraphrase is what the option set shows.
Generating against the verbatim answer produced 49-53 word options for a
42-word true option in trial — outside the length ladder before any check ran.
Order: paraphrase-true -> position-check -> generate -> offline guards ->
paraphrase-generated -> offline guards -> contradiction-check -> ladder ->
seeded shuffle.

### D6-v3.4 Generation constraints (B10.1, B10.6)
Per item, 4 counterfactuals are requested (3 used; the 4th is the spare that
replaces a rejection and, unused, supplies the B10.8 control items without a
second call). The prompt binds: same question; position that genuinely
conflicts; the 4 differ from each other; spoken first-person register; no
copying of distinctive phrases; length within +-15% of the paraphrased true
answer; **specificity target** (+-2 of the true answer's D5 entity-token
count); era bound at the test date; never name the guest.
The specificity clause exists because trial produced a bucket-H true answer
against three bucket-Z alternatives — the tell "pick the option with the
names", which A4.1 exists to forbid.

### D6-v3.5 Style neutralization (B10.4)
Every option INCLUDING the true answer passes ONE paraphrase step, each in its
OWN call with a BYTE-IDENTICAL template. The paraphraser therefore cannot know
which text is real and cannot treat it differently — that is what makes the
neutralization one-factor rather than aspirational.
Position preservation is checked on the paraphrased true answer (SAME/CHANGED).
One re-paraphrase is allowed; a second failure DROPS the item, logged.
A paraphrase that does not end in sentence-final punctuation is treated as
TRUNCATED and refused before the position check, so a budget failure is never
misreported as a changed position.

### D6-v3.6 Contradiction check (B10.5)
Each candidate distractor is classified against the paraphrased true answer as
CONFLICT / AGREE / UNRELATED. Only CONFLICT is accepted. AGREE is a paraphrase
of the true position; UNRELATED does not answer the question and would
reintroduce round 2's responsiveness tell. Rejection counts are logged by
reason. An unparseable verdict is a rejection, never a guess.

### D6-v3.7 Deterministic guards (offline, auditable)
Run on the raw generated text AND again on its paraphrase, because a paraphrase
can reintroduce a violation:
- **era**: any 4-digit year later than the test interview's year. Deliberately
  blunt and deterministic; it cannot catch an unnamed later event, which is why
  the generator is ALSO instructed on the era and the limit is recorded.
- **name leak**: any surviving subject name variant (nickname supplement
  applies, as in rounds 1-2).
- **grounding quote**: any shared 10-word shingle with the subject's rendered
  grounding block (the frozen D8 guard-(a) test), checked raw and redacted.
- **copy-of-true**: word-set Jaccard >= 0.8 against the true answer.

### D6-v3.8 Matching ladder (B10.6)
The tightest D6 rung the whole option set satisfies is recorded per item; the
ladder is unchanged from the pilots so the number means the same thing across
rounds. A set that misses even the loosest rung is flagged `ladder_exceeded`
rather than silently accepted.

### D6-v3.9 Gate and reporting (B10.7)
Unchanged from D6-v2.7: the build-time zero-information gate is the final
arbiter; PRE-gate accuracy on the candidate set is the instrument-difficulty
number and post-gate is ~0 by construction. On gated sets the informative
baselines are the imposter arm and chance.

### D6-v3.10 Auditability
API generation is NOT seed-reproducible. results/stage2_pilot3/genlog/ holds
every generator prompt and every raw completion, one file per item, and is
committed. The four prompt templates are frozen by a single digest
(`counterfactuals.TEMPLATE_SHA256`) recorded in every artifact.

### D6-v3.11 Detectability sheet (B10.8)
20 unmarked entries, seeded shuffle (seed 53): 10 REAL (paraphrased true among
3 generated distractors) and 10 CONTROL (4 generated, no real answer present —
the correct response is `none`). Controls reuse an item's unused spare, so they
cost no extra generation. Real/control item overlap is recorded in the KEY, not
hidden. The SHEET carries no answer markings anywhere; the KEY is a separate
file. Both are committed.

### D6-v3.12 Binding reframing (B10.2)
Every artifact and every write-up carries: *the claim scored is that the twin
identifies the person's actual POSITION among plausible alternative positions
on the same question — NOT that it picks a verbatim transcript answer.*

## v1.10 amendment — D6-v4 round 4 (owner-approved 2026-07-27)

Round 3 shipped B10's generated same-question counterfactuals and the
zero-information arm still solved **15 of 15**, mean margin +0.69
(`results/stage2_pilot3/PILOT_REPORT_3.md`). Its gate completions named the
mechanisms, and round 4 attacks each one. Round 3 is FROZEN: round 4 writes
only to `results/stage2_pilot4/` and reads rounds 1–3 read-only.
Implemented in `src/doppler/counterfactuals4.py`, `src/doppler/dual_parse.py`
and `experiments/stage2_pilot4.py`.

`counterfactuals.py` and its `TEMPLATE_SHA256` are untouched, so round 3's
artifacts stay verifiable against the digest they were built with. Round 4
carries its own `TEMPLATE_SHA256_V4` and records the reused v3 digest beside it.

### D6-v4.1 Register conditioning (attacks report 2.1, speaker plausibility)
The gate said options A–C "read more like an op-ed or a political speech than a
natural response from an academic guest" and picked the one that "reflects the
typical speaking style of a social science professor". The generator writes
confident advocacy; interviewees hedge. B10.4's paraphrase cannot fix it,
because the paraphrase must preserve every claim and the confidence is IN the
claims.

Generation is now few-shot conditioned on the subject's OWN real answers.
Exemplar source order: round 2's `answer_pool.jsonl` first (other interviews,
already filtered against the twin's rendered grounding by D6-v2.2, so nothing
in it is text the twin arm also sees), topped up from the subject's other
answers in the SAME test interview when a subject has too few. Both sources
recorded per item; shortfalls recorded in `build_summary.json`.
**New guards:** a generated option that copies (Jaccard ≥ 0.8) or quotes
(10-word shingle) any exemplar is rejected — a model handed three real answers
can reach for their content as well as their rhythm, which would put real
transcript speech into a slot the item calls generated.

### D6-v4.2 Deixis rule (attacks report 2.3)
Round 3's tightest item (+0.30) was solved on "referring to him as 'Robert'".
The paraphrase preserves the transcript's conversational packaging, and only
the real answer has any, because only the real answer was spoken to a person.

Host names and interviewer address are stripped from **ALL FOUR options** or
from **NONE**. Uniformity is the rule: stripping only the options that happen
to carry a vocative leaves exactly the asymmetry the strip removes. If any one
option would lose more than 30% of its words (`MIN_RETAIN_RATIO = 0.70`) the
whole SET is retained unstripped. The mode (`stripped` / `retained`), the
reason, and the removed fragments per option are recorded per item and flagged
`deixis_<mode>`.

Deliberately narrow: it removes vocatives, the interviewer's name and a fixed
list of address openers — **not every "you"**. A guest saying "you can't fix
this with policing" is talking about the world, not to the host, and mangling
that would damage the option's meaning far more than the tell it removes.

**The ladder rung is recomputed AFTER stripping.** A rung measured on pre-strip
text describes an option set that no longer exists.

### D6-v4.3 Plausibility check (attacks report 2.2, the world-truth tell)
B10.5 requires each distractor to CONFLICT with the true position. When the
true position is simply **correct about the world**, every conflicting
alternative is **wrong about the world**, and a well-informed scorer picks the
true one on general knowledge without modelling the person at all.

Two changes. The generation prompt carries an explicit plausibility rule, and
each surviving candidate gets a separate check call classifying it
PLAUSIBLE / FALSE / FRINGE against the test date. **Only PLAUSIBLE is
accepted**; an unparseable verdict is a rejection, never a guess. Rejections
are logged by reason. The check runs only on options that already passed the
contradiction check — an AGREE option is dead already and paying for a
plausibility call on it is waste.

Residual limitation on record: this replaces one model judgement with another.
The check cannot certify truth, only that the generator-side model finds the
position defensible. It is auditable through the genlog like every other call.

### D6-v4.4 Item-type split (supply decision)
Round 3's widest margins sat on factual-explanation questions. Candidates are
split **subjective** vs **factual_explanation**, and round 4 builds the
subjective-leaning subset first; factual items are built only if supply demands
and are labelled SECONDARY in every table.

Method is a documented cue rule (`classify_question`) **cross-checked against a
recorded hand call with a per-item reason**; the BUILD uses the hand call and
every disagreement is reported. The rule returns `unclear` when no cue fires
and does **not** pretend a no-evidence question is factual — an earlier version
broke 0-0 ties toward factual and mislabelled 9 of 15. The rule's cue lists
were written while looking at these dev questions, so the rule is tuned on the
set it scores; that is acceptable on dev subjects and is stated, which is
precisely why it is a cross-check rather than independent evidence.

Measured split on round 3's 15 built items: **10 subjective, 5
factual-explanation**; rule and hand agree on 11 of 15, and all 4 disagreements
are cases where the rule had no evidence or one weak modal cue.

### D6-v4.5 Two parsers, one contract
Round 3 lost 12 of 15 gate replies to the doubled-distribution artifact, all
12 recoverable and all 12 argmax-correct. The rate is climbing with option
length (2/170 → 2/10 → 12/15) and round 4's options are longer still.

**The frozen parser is NOT changed.** `stage2_render.parse_distribution`
remains the contract, its verdict is what a gate decision uses, and every
round-4 table reports its N. A WIDENED reading runs beside it: take the LAST
well-formed distribution in the reply and read it **with the frozen parser**.
Not a second parser with its own semantics — the same code applied to a
window, so widening cannot rescue a genuinely malformed distribution. Both
numbers are reported with their own N, because they are computed on different
denominators and a rate quoted without its N hides that.

Validated against round 3's gate: the widened reading reproduces the 15/15,
mean p 0.776, mean margin 0.690 that the independent `relaxed_reread`
diagnostic produced, and recovers exactly the same 12 replies.

### D6-v4.6 KILL RULE (pre-committed, verbatim in the report)
> If round 4's zero-information argmax accuracy is **≥ 0.90**, four-way forced
> choice is **DEAD** on this corpus and there is **no round 5 on any axis**.

Rounds 1, 2 and 3 solved 17/17, 10/10 and 15/15 by three different mechanisms;
a fourth instrument that also fails is evidence about the format, not about the
next patch. The fallback landing zone is already written and committed:
`results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md` (commit 71ae352). The rule
is read on the FROZEN number; if the two readings straddle the threshold, that
is itself the finding and the owner decides.

### D6-v4.7 Gate margin relaxation — CONSIDERED, NOT ADOPTED
A margin-relaxed gate (reject only when the zero-information arm solves by more
than some margin) would keep items the current gate discards, and round 3's
tightest item sat at +0.30. **Not adopted for round 4**, for one reason: round
4 tests a pre-committed kill rule, and a kill rule means nothing if the bar
moves in the same round it is tested. Loosening the gate and then reporting
that fewer items were rejected would be unfalsifiable.

Available at BAR-LOCK, and only if round 4 lands in the gray zone —
zero-information accuracy clearly below 0.90 but clearly above the 0.25 chance
line. The owner decides.

### D6-v4.8 Unchanged from round 3
Generator `gemini-3.5-flash-lite` with the B10.3 declared overlap (D6-v3.2b)
carried forward verbatim; temperatures 0.7 / 0.0; measured token budgets
8192 / 2048 / 1024; the paraphrase-first pipeline order; the position check;
the era / name-leak / grounding-quote / copy-of-true guards; the D6 ladder; the
item-id shuffle seed; the strict argmax gate; and B10.2's binding reframing.

### D6-v4.9 STANDING EVAL RULE — no cross-visible twins
Added 2026-07-27 after the frontier rater named **twin-pair stance inference**
as one of six tells on round 3's detectability sheet.

> **No rater and no scorer may ever see both twins of a duplicated question.**
> Within any single prompt file or rating sheet, a question appears AT MOST
> ONCE.

Round 3's sheet showed five questions twice, once as a real entry and once as a
control. The option sets shared nothing after the second generation pass, so
elimination was impossible — but a reader could still reason across the two
stance sets, and the rater says they did. Round 4 asserts the rule at export
(`assert_no_cross_visible_twins`) over every exported prompt set and writes
`twin_check.json`; a repeat raises rather than warns, because a duplicated
question inside a scored file is a reason not to run the file.

Measured on the rater line: the clean non-twinned real entries scored the SAME
as the twinned ones (1.00 vs 1.00), so twin inference was not what carried that
result. The rule closes a real leak that happened not to be load-bearing.

### D6-v4.10 B10.8 human line — WAIVED, open deviation
The owner declined to complete the detectability sheet on 2026-07-27 and
substituted an out-of-family LLM rater (Claude; not the generator
`gemini-3.5-flash-lite`, not the scorer `Gemma-4-31B-it`).

**No human hit rate exists. B10.8's human check is UNMET and is recorded as an
open deviation, not as satisfied by the LLM line.** The LLM line answers a
related but different question — whether a capable model can spot the real
answer — which is the more direct predictor of scorer behaviour but is not the
check the amendment asks for. If the instrument goes confirmatory, either the
human line runs or B10.8 is formally amended. Owner decision at bar-lock.

Result of the substituted line, frozen pre-gate in
`results/stage2_pilot4/DETECTABILITY_RATER_LINE.md`: **10/10 on the real
entries** against a 0.25 chance rate, 9/10 correct rejections on controls,
19/20 overall. Six named tells: hedging/register, stance-vs-premise fit,
world-truth/academic content, entity density, twin-pair stance inference, and a
vocative-name leak. Round 4 attacks four of the six; entity density was
*already* controlled by A4.1 and still read as a tell, which is itself a
finding about matching on a count rather than on deployment.
