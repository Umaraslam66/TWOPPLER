# S1 redaction-scope extension — collateral re-measure on dev prompts

Date: 2026-07-28. Dev subjects only. CPU only, no API, no GPU, cost $0.00.

Governing text: `PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`, instrument
parameter 8. Frozen scope it extends: decision 5 (scope **S1** — the host's
descriptive clause about GUEST).

## Verdict

**FROZEN.** Collateral damage on dev prompts is **zero**, which is the
pre-committed condition. The extension is now the S1 that any confirmatory
render uses.

- newly-removed spans: **3** (all in one prompt)
- classified identity-leak: **3**
- classified collateral: **0**
- prompts changed: **1 of 85**; the other 84 are byte-identical

One of the two known dev leaks is fixed and one is not. The unfixed one is a
**declared miss**, not collateral — see "Known case 2" below. The contamination
meter stays the backstop for it, exactly as parameter 8 says.

## What changed

Two patterns in `src/doppler/oe_render.py`, nothing else. The role-word list
and the appositive pattern that were priced in
`results/stage2_pilot2/BARLOCK_MEASUREMENTS.md` are **byte-identical** to
`experiments/barlock_affiliation.py` still; the extension sits beside them, and
a test pins that.

**(a) Read through an abbreviation's full stop.** S1's clause ran "up to the
next full stop". The dot inside "U.S." counted as a full stop, so the clause
ended after the letter U and the role word behind it was never seen. The clause
patterns now run over a copy of the line in which an abbreviation's dots are
hidden ("U.S.", "D.C.", "Dr.", "Sen." and similar). A dot followed by a space
and a capital letter is left alone — that is a real sentence break and the
clause must still stop there.

**(b) Follow a "GUEST, who ..." clause past its commas.** S1 stopped at the
first comma, which cut a relative clause in half and left the rest of the
résumé standing (", now at the Brookings Institution"). The clause now grows
one comma-segment at a time and stops at the first segment that is no longer
describing the guest — no role word and no proper noun — or that turns to
address them. That stop rule is what keeps the host's own question out of the
removal, and it is tested directly
(`test_s1_who_clause_never_swallows_the_hosts_own_question`).

Both stay inside S1's declared intent: the host's descriptive clause about
GUEST. Nothing outside a `HOST:` / `GUEST:` speech line is touched, as before.

## How it was measured

The OE-1 build was re-run offline into a scratch directory, three times over
the same inputs: S1 off, S1 as frozen, S1 extended
(`experiments/stage2_oe1.py build`, all 17 items × 5 arms = 85 prompts).

The baseline re-run reproduced the committed OE-1 prompt files
(`results/stage2_openended/prompts/*.jsonl`) **byte for byte**, all seven files,
so the before/after diff below is a diff of the extension and of nothing else.

The committed OE-1 prompt files were not overwritten. They are the record of
what OE-1 actually ran.

## Every newly-removed span

All three are in one prompt: arm `imposter_redacted`, subject `C01677`, item
`C01677:NPR-8791:77`. All three sit in the **donor's** intro lines — the arm
whose whole job is to withhold identity.

**Span 1 — identity-leak.** Host intro clause naming the donor's two posts.

- before: `HOST: GUEST, who served two tours as U.S. ambassador to Israel, now at the Brookings Institution, thanks so much.`
- after: `HOST: GUEST, [DESCRIPTION REMOVED], thanks so much.`
- removed: `who served two tours as U.S. ambassador to Israel, now at the Brookings Institution`
- the host's sign-off "thanks so much" survives — the clause stopped where it should.

**Span 2 — identity-leak.** The same donor's fuller résumé.

- before: `HOST: We're going to check in now on U.S.-Israeli relations and other matters with GUEST, who used to be U.S. ambassador there, as well as assistant secretary of state for the region and who now directs foreign policy programs at the Brookings Institution. Welcome to the program, GUEST.`
- after: `HOST: We're going to check in now on U.S.-Israeli relations and other matters with GUEST, [DESCRIPTION REMOVED]. Welcome to the program, GUEST.`
- removed: `who used to be U.S. ambassador there, as well as assistant secretary of state for the region and who now directs foreign policy programs at the Brookings Institution`
- the interview's topic ("U.S.-Israeli relations and other matters") survives untouched.

**Span 3 — identity-leak.** A free-standing host-intro sentence about the donor.

- before: `HOST: Until just a few weeks ago GUEST was running Secretary of State John Kerry's faltering effort to get Israelis and Palestinians on a path toward peace. GUEST is a former U.S. ambassador to Israel and a former assistant secretary of state. He is now back at the Brookings Institution in Washington and he joins us today as Israelis and Palestinians are once again fighting. GUEST, Thanks for joining us.`
- after: `HOST: Until just a few weeks ago GUEST was running Secretary of State John Kerry's faltering effort to get Israelis and Palestinians on a path toward peace. GUEST is [DESCRIPTION REMOVED]. He is now back at the Brookings Institution in Washington and he joins us today as Israelis and Palestinians are once again fighting. GUEST, Thanks for joining us.`
- removed: `a former U.S. ambassador to Israel and a former assistant secretary of state`
- only that one sentence changed; the neighbouring sentences are untouched.

**Collateral count: 0.** No interview topic content, no question text and no
non-identity prose is inside any of the three removals.

Counts, for the record: S1 placeholders across all five arms 56 → 59; across
the three redacted arms 33 → 36; prompts carrying at least one placeholder in
the redacted arms 22 → 23.

## The two known cases

**Known case 1 — the "U.S."-truncation résumé. FIXED.** This is the case
parameter 8 recorded. Three lines carried it; all three are spans 1–3 above.
Counting prompts that still contain the text: `who served two tours` 1 → 0,
`who used to be U.S. ambassador` 1 → 0, `GUEST is a former U.S. ambassador`
1 → 0.

**Known case 2 — the donor blog-naming line. NOT FIXED. The miss stays
declared.** Unchanged in all 5 prompts that carry it:

- `HOST: And also with us from member station KUOG in Norman, Oklahoma, GUEST, [DESCRIPTION REMOVED]. He also runs the blog Syria Comment. GUEST, nice to talk to you again.`
- `HOST: All right, GUEST, [DESCRIPTION REMOVED]. He runs the blog Syria Comment, and he joined us from member station KGOU in Norman, Oklahoma. Thank you so much.`

Why the two authorised patterns cannot reach it, plainly:

1. It is not an appositive and it is not abbreviation-truncated. It is a
   separate sentence with a pronoun subject ("He also runs the blog ..."), so
   neither pattern (a) nor pattern (b) has anything to match on.
2. It carries no role word. S1 decides a clause is descriptive by finding a
   role word in it, and "runs the blog Syria Comment" has none.

Catching it would need a third pattern shape (a pronoun-subject sentence whose
subject is GUEST by reference) **and** a widened trigger set beyond
`ROLE_WORDS` (a publication cue). That is two structural changes the addendum
does not authorise — parameter 8 authorises (a) and (b) — and widening
`ROLE_WORDS` would change the frozen core that the S1 pricing measurement rests
on and would raise collateral risk on every pattern at once. So it was not
done. This is flagged for the owner as a decision, not patched quietly.

## Redaction assertions and tests

All re-run on the re-rendered dev prompts, all pass.

- `experiments/stage2_oe1.py build` completed on all 85 prompts. That runs
  `R.assert_redacted` on every prompt (and twice on the imposter arm, subject
  and donor), `R.surviving_variants` over the redacted arms, the named-arm
  one-line-difference check, `R.assert_no_answer_leak`, the D6-v4.9 twin-free
  check, the zero-info no-excerpt check and the open-ended shape guard.
- Surviving name variants in the redacted arms: **0** before, **0** after.
- Grounded prompts over the 2,000-word grounding budget: **0** before, **0**
  after.
- Full test suite: **1139 passed** (was 1132; the 7 new ones are the extension's).

## Residual leaks still standing (declared, not fixed)

Beyond the blog-naming line, S1 still leaves these on dev prompts. All were
already declared before this extension; none is new.

- `GUEST, who's now with the Atlantic Council.` (twin arms, C00792) — an
  affiliation with no role word, so the role-word gate does not fire.
- Pronoun-subject follow-on sentences generally: `He is now back at the
  Brookings Institution in Washington ...` (imposter, C01677), `He is coauthor
  of the forthcoming book called "Bending History" ...` (imposter, C01677).
  Note `coauthor` is not in `ROLE_WORDS`; `co-author` is.
- Co-panellist résumés in twin prompts, which are a co-occurrence fingerprint
  on the subject rather than a description of GUEST — outside S1's declared
  intent by construction.

One measurement note worth keeping: the spaCy-based leak detector in
`experiments/barlock_affiliation.py` reports the same GUEST-attached mention
count before and after (108). That is not evidence the removals did nothing —
it is the same bug in the detector. It splits sentences on `.` too, so on span
1 it read "GUEST, who served two tours as U.S." and "ambassador to Israel, now
at the Brookings Institution, ..." as two sentences, put GUEST in the first and
"the Brookings Institution" in the second, and therefore classed the leak as
"topic" and never counted it. Independent corroboration that the abbreviation
dot was the bug. The span-level diff above is the operative measurement.

## Scope of the change

- `src/doppler/oe_render.py` — the two patterns. sha256
  `49707ebe052d77e73b0b5046567ab9289cf09e0b7a4a27209a84bbaa39a65398`.
- `tests/test_oe_render.py` — 7 new tests.
- `experiments/barlock_affiliation.py` — **not touched.** It is the script that
  priced S1; changing it would rewrite the record of that measurement.
- `results/stage2_openended/prompts/*.jsonl` — **not touched.** They are what
  OE-1 ran.

The one prompt that would change on a re-render, for the record:
`imposter_redacted` / `C01677:NPR-8791:77`, sha256
`02572...773a44` → `bb0bc...e6457b`, 2,130 → 2,081 words.
