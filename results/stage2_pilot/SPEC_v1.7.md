<!-- HISTORICAL SNAPSHOT — DO NOT EDIT, DO NOT FOLLOW AS INSTRUCTIONS -->

# Historical snapshot: Stage 2 pilot design contract, SPEC.md v1.7

**What this is.** A verbatim, frozen copy of the design contract that the Stage 2
pilot (round 1) was built against. Four committed provenance artifacts name
"SPEC.md v1.7 (D1-D10)" as the binding contract for that run —
`results/stage2_pilot/PILOT_REPORT.md`, `config.json`, `manifest.json`, and
`exports/export_manifest.json` — but the file itself lived only in a session-local
scratchpad that will be deleted. This copy makes that citation resolvable.

**Provenance.** Verbatim lines 1-254 of the working SPEC.md, which is the state of
the file through the `## v1.7 amendment` section. sha256 of that content:
`fcdae9313dcff91384ca4e2814c8b2b9a941d988a6dfd43e5e5130d63193ed37`. Nothing was
added, removed, or reworded below this header. The header line of the original
reads "v1" — the version is established by the amendment log at the bottom, which
runs through v1.7.

**Read this as a record, not as instructions.** The document mixes two kinds of
content. The D1-D10 sections and the amendment log are research design and are the
real reason to keep it. The build-process material — git rules, task ordering,
"do not commit Amendment 2", instructions addressed to implementers — is
scaffolding from the session that built the harness. It is included as-is for
completeness. It is not live guidance, and where it conflicts with
`.claude/CLAUDE.md` or `PREREGISTRATION.md` and its amendments, those win.
Amendment 2 was subsequently adopted (commit 9949c9d), which overrides the
instruction in this SPEC not to commit it.

**Known inconsistency, pre-existing.** `results/stage2_pilot/manifest.json` records
`"contract": "SPEC.md v1.6"` while the pilot report, config, and export manifest all
say v1.7. That disagreement is in the run artifacts as produced; it is recorded
here rather than corrected, because the artifacts are not edited after the fact.

**Superseded for later rounds.** A v1.8 amendment (D6-v2, same-subject distractors)
was added after this snapshot for the round-2 pilot build. It is not part of v1.7
and is not included here.

---

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
