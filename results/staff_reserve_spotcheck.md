# Staff-filter reserve — spot-check sheet

What this is: the 292 subjects the Phase A staff filter dropped purely because a **speaker label** somewhere in the corpus carried a role word (HOST / ANCHOR / CORRESPONDENT / BYLINE / REPORTER / COMMENTATOR / a 'reporting' sign-off), with **no** tier-1 summary evidence that they are NPR or CNN staff. For each one I pulled every piece of role evidence out of the corpus and made an automatic recommendation. Nothing is re-admitted automatically: this sheet is the 20-subject human check that has to happen first.

Sources: raw speaker labels across all 463,596 transcripts, transcript summaries, and host/self utterances that name the subject. Built by `experiments/reserve_evidence_v2.py` (one 12-second pass over the 4.4 GB corpus) and `experiments/reserve_score_v2.py`. The per-subject table is `results/staff_reserve_dossiers.csv`. CPU only, no network, no LLM, $0.

## Counts

| recommendation | all 292 | long-tail (76) |
|---|---|---|
| RE-ADMIT | 106 | 22 |
| AMBIGUOUS | 110 | 22 |
| KEEP-EXCLUDED | 76 | 32 |

One number differs from the curation report: it says 84 of the 292 are long-tail. Recomputing from `stage2_candidate_pool_v2.csv` gives **76** long-tail, plus 6 "has-page-fuzzy" (an article exists under a different spelling) and 210 with an article. 76 is the post-fuzzy figure and is what this sheet uses.

## How much to trust the automatic recommendation

My honest read: **the recommendation is good enough to sort the
queue, not good enough to re-admit anyone on its own.**

Where it is strong. Most of the decisive evidence is a speaker label the
transcript itself carries, quoted verbatim — `GREG JAFFE, MILITARY REPORTER,
"THE WASHINGTON POST"`. When a label names an outside outlet, there is nothing
to interpret. 103 of the 106 RE-ADMIT subjects have at least
one such label. The four audit anchors all come out the way the audit says they
should, and six more people the audit or the curation report independently
called NPR staff
(Emily Green, Cheryl Corley, Allison Aubrey, Alex Cohen, Celeste Headlee,
Michel Martin) land in KEEP-EXCLUDED without being told to.

Where it is weak, in the order I would worry about it:

1. **Proximity, not grammar.** For summaries and host turns I look for role
   words near the name. In "guest host X talks with Y, author of Z" the word
   "author" belongs to Y. I patched the common form of this (the sheet now
   works out which side of "talks with" the subject is on), but the general
   problem is not solved, and it inflates guest evidence on any subject who
   shares a summary with several other people.
2. **Bare role labels carry no information.** `X, CORRESPONDENT` with nothing
   after it could be an NPR correspondent or a magazine's. Those subjects are
   mostly in AMBIGUOUS, which is where they belong, but it is why AMBIGUOUS is
   the largest bucket.
3. **Member stations look like outside outlets and are not.** A reporter for
   WFCR or Capital Public Radio reads as "outside affiliation" but files for
   NPR — the hand audit judged exactly such a person (Emily Green) to be staff.
   18 subjects trip this flag and none of them is auto-RE-ADMIT, but the
   station list is hand-made and certainly incomplete.
4. **Identity collisions are untouched.** The evidence is gathered per *name*,
   so two people who share a name share a dossier. `David Jackson` shows both
   "USA Today White House correspondent" and "Director, Voice of America";
   `Brian Bennett` shows "TIME magazine" and "passenger on Delta flight 1156".
   Re-admitting a name does not mean the transcripts behind it are one person.
5. **Other broadcasters.** 13 subjects carry an ABC / CBS / NBC / Fox /
   BBC / ESPN affiliation in their own speaker labels. They are outside NPR and
   CNN, so the filter's rationale does not apply to them, but whether a
   correspondent from a *different* network counts as an "interview subject" is
   the owner's call, not mine. They are flagged, not decided.

What I would expect if you audit the RE-ADMIT bucket by hand: a high hit rate
(the label evidence is explicit), with the errors concentrated in items 3-5
rather than in genuine NPR staff slipping through.

## Anchors (audit-verified, shown separately)

Brian Bennett and Dexter Filkins were judged genuine guests by the 20-guest hand audit and should come out RE-ADMIT. Alex Kellogg and Brian Unger were judged staff and should come out KEEP-EXCLUDED. Kellogg and Unger are *not* in the reserve — the summary filter already catches them — they are here only as controls.

### Brian Bennett

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 597d (2014-04-18 to 2015-12-06) | NPR share 0.18 | 13 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 36 strong, 2 medium (capped score 16); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `CORRESPONDENT`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `BRIAN BENNETT, NATIONAL CORRESPONDENT, "TIME"`  (x1, marker CORRESPONDENT; e.g. CNN-111915)
- `BRIAN BENNETT, NAT'L SECURITY CORRESPONDENT, L.A. TIMES`  (x1, marker CORRESPONDENT; e.g. CNN-166757)
- `BRIAN BENNETT, SENIOR WHITE HOUSE CORRESPONDENT, "TIME"`  (x1, marker CORRESPONDENT; e.g. CNN-367788)
- `BRIAN BENNETT, SENIOR WHITE HOUSE CORRESPONDENT, "TIME" MAGAZINE`  (x1, marker CORRESPONDENT; e.g. CNN-384495)

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-74387;CNN-79262;CNN-80238) "BRIAN BENNETT, "TIME" MAGAZINE"
- [3] (speaker label carries an outside affiliation/title, label, CNN-83691) "BRIAN BENNETT, BAGHDAD BUREAU CHIEF, "TIME" MAGAZINE"
- [3] (speaker label carries an outside affiliation/title, label, CNN-84106) "BRIAN BENNETT, "TIME" MAGAZINE, BAGHDAD BUREAU CHIEF"
- [3] (speaker label carries an outside affiliation/title, label, CNN-103182) "BRIAN BENNETT, BAGHDAD BUREAU CHIEF, "TIME""
- [3] (outside-outlet correspondent label, label, CNN-111915) "BRIAN BENNETT, NATIONAL CORRESPONDENT, "TIME""
- [3] (outside-outlet correspondent label, label, CNN-166757) "BRIAN BENNETT, NAT'L SECURITY CORRESPONDENT, L.A. TIMES"
- [3] (outside-outlet correspondent label, label, CNN-367788) "BRIAN BENNETT, SENIOR WHITE HOUSE CORRESPONDENT, "TIME""
- [3] (outside-outlet correspondent label, label, CNN-384495) "BRIAN BENNETT, SENIOR WHITE HOUSE CORRESPONDENT, "TIME" MAGAZINE"
- [3] (outlet_near_name, summary, NPR-23407) "NPR's Lynn Neary speaks with Brian Bennett, who wrote a profile of Malik for the Los Angeles Times."
- [3] (outlet_near_name, summary, NPR-26856) "Using a Freedom of Information Act request, Brian Bennett of the Los Angeles Times recently obtained data on deportations."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Dexter Filkins

- long-tail: **no** (has-page) | interviews (dedup): 7 on 7 dates | span 3436d (2005-08-15 to 2015-01-11) | NPR share 0.35 | 12 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 63 strong, 2 medium (capped score 16); staff evidence: 0 strong, 1 medium, 2 weak (capped score 4)
- label filter fired on marker: `CORRESPONDENT`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `Mr. DEXTER FILKINS (Foreign Correspondent, The New York Times)`  (x1, marker CORRESPONDENT; e.g. NPR-3522)
- `Mr. DEXTER FILKINS (Reporter, New York Times)`  (x1, marker REPORTER; e.g. NPR-14742)
- `Mr. DEXTER FILKINS (Reporter, The New York Times; Author, "The Forever War")`  (x1, marker REPORTER; e.g. NPR-34441)
- `DEXTER FILKINS reporting`  (x1, marker REPORTING; e.g. NPR-49004)
- `Mr. DEXTER FILKINS (Foreign Correspondent, New York Times, Author, "The Forever War")`  (x1, marker CORRESPONDENT; e.g. NPR-49361)
- summary-filter tier-2 example: "Afghan President Hamid Karzai hopes to launch peace negotiations with insurgents and lay the groundwork for an end to the war. New York Times foreign correspondent Dexter Filkins has learned that top-level Taliban leader"

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-213439;CNN-370789;CNN-387585) "DEXTER FILKINS, STAFF WRITER, THE NEW YORKER"
- [3] (speaker label carries an outside affiliation/title, label, CNN-68287;CNN-68945;CNN-101840) "DEXTER FILKINS, "THE NEW YORK TIMES""
- [3] (speaker label carries an outside affiliation/title, label, NPR-15871;NPR-16043) "Mr. DEXTER FILKINS (The New York Times)"
- [3] (speaker label carries an outside affiliation/title, label, CNN-262222;CNN-387585) "DEXTER FILKINS, "THE NEW YORKER""
- [3] (outside-outlet correspondent label, label, NPR-3522) "Mr. DEXTER FILKINS (Foreign Correspondent, The New York Times)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-3858) "Mr. DEXTER FILKINS (New York Times)"
- [3] (outside-outlet reporter label, label, NPR-14742) "Mr. DEXTER FILKINS (Reporter, New York Times)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-29610) "Mr. DEXTER FILKINS (Writer, The New Yorker Magazine)"
- [3] (outside-outlet reporter label, label, NPR-34441) "Mr. DEXTER FILKINS (Reporter, The New York Times; Author, "The Forever War")"
- [3] (outside-outlet correspondent label, label, NPR-49361) "Mr. DEXTER FILKINS (Foreign Correspondent, New York Times, Author, "The Forever War")"

**Staff-role evidence**

- [2] ('reporting' sign-off label, label, NPR-49004) "DEXTER FILKINS reporting"
- [1] (bare_role_name, summary, NPR-12667) "But reporter Dexter Filkins paints a complicated picture of Erdogan under threats of coup and paranoia."
- [1] (bare_role_name, utterance[STEVE INSKEEP, host], NPR-34441) "The reporter Dexter Filkins remembers a day when he stood on a dam over the Euphrates River in Iraq."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Alex Kellogg

- long-tail: **yes** (long-tail) | interviews (dedup): 4 on 4 dates | span 182d (2011-02-20 to 2011-08-21) | NPR share 1.00 | 3 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 0 medium (capped score 0); staff evidence: 12 strong, 0 medium, 0 weak (capped score 12)
- label filter fired on marker: `nan`; summary filter said: `staff`

**Exclusion evidence — the labels that triggered the filter**

- (none found in this pass — see staff_crossref_v2.csv)

**Guest-role evidence**

- none found

**Staff-role evidence**

- [3] (network_possessive, summary, NPR-48731) "A group of teens who will attend talk to NPR's Alex Kellogg about what the monument means to them."
- [3] (network_possessive, utterance[LIANE HANSEN, host], NPR-13480) "NPR's Alex Kellogg was there."
- [3] (byline_signoff (self sign-off), utterance[ALEX KELLOGG], NPR-13480) "Alex Kellogg, NPR News, Montgomery, Alabama."
- [3] (network_possessive, utterance[MARY LOUISE KELLY, host], NPR-29129) "As NPR's Alex Kellogg reports, the closings could start as early as next year and they'll affect rural areas the most."
- [3] (byline_signoff (self sign-off), utterance[ALEX KELLOGG], NPR-29129) "Alex Kellogg, NPR News, Washington."
- [3] (network_possessive, utterance[STEVE INSKEEP, Host], NPR-29290) "In Baltimore, more than half of homes sold this year have been bought with cash, as NPR's Alex Kellogg reports."
- [3] (byline_signoff (self sign-off), utterance[ALEX KELLOGG], NPR-29290) "Alex Kellogg, NPR News."
- [3] (network_possessive, utterance[LINDA WERTHEIMER, host], NPR-29581) "NPR's Alex Kellogg reports."
- [3] (network_possessive, utterance[LINDA WERTHEIMER, host], NPR-29797) "And as NPR's Alex Kellogg reports, that will change the politics and identity of many communities."
- [3] (network_possessive, utterance[ROBERT SIEGEL, host], NPR-32526) "As NPR's Alex Kellogg explains, state lawmakers say they're taking action now because Washington is not."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Brian Unger

- long-tail: **no** (has-page) | interviews (dedup): 15 on 15 dates | span 735d (2007-03-12 to 2009-03-16) | NPR share 1.00 | 1 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 1 strong, 0 medium (capped score 3); staff evidence: 9 strong, 2 medium, 6 weak (capped score 20)
- label filter fired on marker: `nan`; summary filter said: `staff`

**Exclusion evidence — the labels that triggered the filter**

- (none found in this pass — see staff_crossref_v2.csv)

**Guest-role evidence**

- [3] (title_near_name, utterance[ANNABELLE GURWITCH], NPR-17203) "So clearly, I need a name that properly frames the kind of commentaries that I'm offering to you, so I asked my fellow commentators, Brian Unger and Sandra Tsing Loh, for their input, and I brought in an expert, Chris Arnold, who makes movie trailers and has named, or renamed, hundreds of movies and asked him to give me some fe..."

**Staff-role evidence**

- [3] (our_role_name, summary, NPR-89) "And our humorist Brian Unger is following suit as he examines the path of personal evolution."
- [3] (our_role_name, summary, NPR-8635) "Our humorist Brian Unger attended the awards ceremony, and despite some questionable behavior, he managed to avoid getting throw out."
- [3] (our_role_name, utterance[ALEX CHADWICK, host], NPR-89) "Our humorist, Brian Unger, says you might be evolving."
- [3] (our_role_name, utterance[MADELEINE BRAND, host], NPR-7123) "And now, our humorist Brian Unger imagines the very human presidential candidates as stars of a very steamy primetime drama."
- [3] (our_role_name, utterance[MADELEINE BRAND, host], NPR-8254) "And now with his final Unger report for this program, here is our humorist, Brian Unger."
- [3] (our_role_name, utterance[MADELEINE BRAND, host], NPR-8382) "Our humorist Brian Unger has his own tweet to share in today's Unger Report."
- [3] (our_role_name, utterance[MADELEINE BRAND, host], NPR-9103) "Our humorist Brian Unger offers his two cents in today's Unger Report."
- [3] (our_role_name, utterance[MADELEINE BRAND, host], NPR-9103) "Getting down to humor every Monday, that's our slightly confused correspondent Brian Unger."
- [3] (our_role_name, utterance[MADELEINE BRAND, host], NPR-9254) "Our humorist Brian Unger offers these precautions to the White House's newest residents in today's Unger Report."
- [2] (name_reports, utterance[MADELEINE BRAND, host], NPR-22) "In today's Unger Report, Brian Unger has this advice for Barack Obama on how to handle the Bill factor."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

## The 20 spot-check subjects

Random sample, seed 42, stratified 10 long-tail / 10 with a Wikipedia page. Read the exclusion evidence first, then the two evidence blocks, then tick a box.

### Alice Furlaud

- long-tail: **yes** (long-tail) | interviews (dedup): 3 on 3 dates | span 473d (2007-09-09 to 2008-12-25) | NPR share 1.00 | 3 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 1 medium (capped score 2); staff evidence: 0 strong, 3 medium, 7 weak (capped score 10)
- label filter fired on marker: `REPORTER`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `Ms. ALICE FURLAUD (Reporter)`  (x1, marker REPORTER; e.g. NPR-39905)
- `Ms. ALICE FURLAUD (Commentator)`  (x1, marker COMMENTATOR; e.g. NPR-42484)
- `ALICE FURLAUD reporting`  (x1, marker REPORTING; e.g. NPR-42567)

**Guest-role evidence**

- [2] (speaker label carries an outside affiliation/title, label, NPR-9645) "Ms. ALICE FURLAUD (Writer)"

**Staff-role evidence**

- [2] (bare 'REPORTER' label, no affiliation, label, NPR-39905) "Ms. ALICE FURLAUD (Reporter)"
- [2] ('reporting' sign-off label, label, NPR-42567) "ALICE FURLAUD reporting"
- [2] (name_reports, utterance[JOHN YDSTIE, host], NPR-42567) "Reporter Alice Furlaud has the story."
- [1] (bare 'COMMENTATOR' label, label, NPR-42484) "Ms. ALICE FURLAUD (Commentator)"
- [1] (bare_role_name, summary, NPR-39905) "Reporter Alice Furlaud was visiting France that month and had a different perspective on the scene."
- [1] (bare_role_name, summary, NPR-41136) "Commentator Alice Furlaud remarks on a land dispute on Cape Cod between a developer and neighbors who want to preserve a landscape made famous by artist Edward Hopper."
- [1] (bare_role_name, utterance[SCOTT SIMON, host], NPR-16466) "Reporter Alice Furlaud is getting on in years."
- [1] (bare_role_name, utterance[GUY RAZ, host], NPR-39905) "Today, the recollections of reporter Alice Furlaud."
- [1] (bare_role_name, utterance[JACKI LYDEN, host], NPR-41136) "Commentator Alice Furlaud has spent part of every year in Truro since 1933."
- [1] (bare_role_name, utterance[DEBBIE ELLIOTT, host], NPR-42484) "Commentator Alice Furlaud developed a deep connection with the writer."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Allison Samuels

- long-tail: **yes** (long-tail) | interviews (dedup): 4 on 4 dates | span 329d (2007-05-04 to 2008-03-28) | NPR share 0.25 | 8 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 67 strong, 1 medium (capped score 14); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `CORRESPONDENT`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `Ms. ALLISON SAMUELS (National Correspondent, Newsweek)`  (x5, marker CORRESPONDENT; e.g. NPR-37;NPR-309;NPR-13149)
- `Ms. ALLISON SAMUELS (Entertainment Reporter, Newsweek)`  (x2, marker REPORTER; e.g. NPR-2158;NPR-2213)
- `Ms. ALLISON SAMUELS (Correspondent, Newsweek)`  (x1, marker CORRESPONDENT; e.g. NPR-31)
- `Mr. ALLISON SAMUELS (Reporter, Newsweek)`  (x1, marker REPORTER; e.g. NPR-739)
- `Ms. ALLISON SAMUELS (Entertainment Reporter, Newsweek Magazine)`  (x1, marker REPORTER; e.g. NPR-1551)
- `Ms. ALLISON SAMUELS (Reporter, Newsweek)`  (x1, marker REPORTER; e.g. NPR-1630)
- summary-filter tier-2 example: "Farai Chideya talks with Newsweek national correspondent Allison Samuels about the latest Hollywood news. Today, we discuss The L.A. Times' retraction of a story on Tupac Shakur, Spike Lee's ongoing struggle to fund his "

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-124630;CNN-129419;CNN-132690) "ALLISON SAMUELS, "NEWSWEEK""
- [3] (outside-outlet correspondent label, label, NPR-37;NPR-309;NPR-13149) "Ms. ALLISON SAMUELS (National Correspondent, Newsweek)"
- [3] (outside-outlet reporter label, label, NPR-2158;NPR-2213) "Ms. ALLISON SAMUELS (Entertainment Reporter, Newsweek)"
- [3] (speaker label carries an outside affiliation/title, label, CNN-181025;CNN-192137) "ALLISON SAMUELS, SENIOR WRITER, "NEWSWEEK""
- [3] (outside-outlet correspondent label, label, NPR-31) "Ms. ALLISON SAMUELS (Correspondent, Newsweek)"
- [3] (outside-outlet reporter label, label, NPR-739) "Mr. ALLISON SAMUELS (Reporter, Newsweek)"
- [3] (outside-outlet reporter label, label, NPR-1551) "Ms. ALLISON SAMUELS (Entertainment Reporter, Newsweek Magazine)"
- [3] (outside-outlet reporter label, label, NPR-1630) "Ms. ALLISON SAMUELS (Reporter, Newsweek)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-1657) "Ms. ALLISON SAMUELS (Entertainment Writer, Newsweek)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-1771) "Ms. ALLISON SAMUELS (Writer, Newsweek)"

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Brad Linder

- long-tail: **yes** (long-tail) | interviews (dedup): 3 on 3 dates | span 882d (2006-07-09 to 2008-12-07) | NPR share 1.00 | 2 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 1 medium (capped score 2); staff evidence: 0 strong, 4 medium, 0 weak (capped score 8)
- label filter fired on marker: `REPORTING`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `BRAD LINDER reporting`  (x1, marker REPORTING; e.g. NPR-40616)

**Guest-role evidence**

- [2] (name_tells_us, utterance[RENEE MONTAGNE, Host], NPR-34937) "Brad Linder explains."

**Staff-role evidence**

- [2] ('reporting' sign-off label, label, NPR-40616) "BRAD LINDER reporting"
- [2] (name_reports, summary, NPR-40616) "From member station WHYY in Philadelphia, Brad Linder reports."
- [2] (name_reports, utterance[RENEE MONTAGNE, host], NPR-34562) "Brad Linder reports."
- [2] (name_reports, utterance[DEBBIE ELLIOTT, Host], NPR-42167) "From member station WHYY in Philadelphia, Brad Linder reports the thefts have been costly and in some cases dangerous."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Cory Turner

- long-tail: **yes** (long-tail) | interviews (dedup): 3 on 3 dates | span 279d (2006-09-15 to 2007-06-21) | NPR share 1.00 | 2 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 1 strong, 2 medium (capped score 7); staff evidence: 20 strong, 0 medium, 6 weak (capped score 16)
- label filter fired on marker: `BYLINE`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `CORY TURNER, BYLINE`  (x13, marker BYLINE; e.g. NPR-8506;NPR-8757;NPR-8944)
- `CORY TURNER, HOST`  (x4, marker HOST; e.g. NPR-20529;NPR-20531;NPR-20532)
- summary-filter tier-2 example: "News & Notes editor Cory Turner serves up this week's staff song pick: Patsy Cline's \"Leaving On Your Mind.\" This is Turner's last week with the show."

**Guest-role evidence**

- [3] (org_near_name, utterance[STEVE INSKEEP, HOST], NPR-8757) "I have to ask, Cory Turner, because, of course, there are divided opinions about college..."
- [2] (host_talks_to, summary, NPR-26620) "NPR's Eric Westervelt talks with education reporter Cory Turner about other misconceptions about the Common Core standards."
- [2] (host_talks_to, utterance[STEVE INSKEEP, HOST], NPR-22468) "So we're going to talk about all this with Cory Turner of the NPR Ed Team, who's in our studios."

**Staff-role evidence**

- [3] (bare 'BYLINE' label (network convention), label, NPR-8506;NPR-8757;NPR-8944) "CORY TURNER, BYLINE"
- [3] (bare 'HOST' label (network convention), label, NPR-20529;NPR-20531;NPR-20532) "CORY TURNER, HOST"
- [3] (network_possessive, utterance[FARAI CHIDEYA, host], NPR-3428) "NPR's Cory Turner has the story."
- [3] (byline_signoff (self sign-off), utterance[CORY TURNER], NPR-3428) "Cory Turner, NPR News."
- [3] (network_possessive, utterance[TONY COX, host], NPR-3916) "NPR's Cory Turner visited one such school in Los Angeles to find out how it's taken some of the city's lowest achieving kids and turned them into the best and brightest."
- [3] (byline_signoff, utterance[Ms. ASHLEY GOMEZ (Student, KIPP Academy of Opportunity)], NPR-3916) "Cory Turner, NPR News, Los Angeles."
- [3] (network_possessive, utterance[AUDIE CORNISH, HOST], NPR-8506) "As NPR's Cory Turner reports, there's little doubt that Public Service Loan Forgiveness hasn't helped many people - 99% of borrowers have been rejected."
- [3] (network_possessive, utterance[STEVE INSKEEP, HOST], NPR-8757) "NPR's Cory Turner is breaking this story."
- [3] (network_possessive, utterance[STEVE INSKEEP, HOST], NPR-8757) "That's NPR's Cory Turner."
- [3] (network_possessive, utterance[ARI SHAPIRO, HOST], NPR-8944) "NPR's Cory Turner is here in the studio."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Curt Nickisch

- long-tail: **yes** (long-tail) | interviews (dedup): 4 on 4 dates | span 702d (2006-11-30 to 2008-11-01) | NPR share 1.00 | 5 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 4 strong, 0 medium (capped score 12); staff evidence: 9 strong, 9 medium, 0 weak (capped score 20)
- label filter fired on marker: `BYLINE`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `CURT NICKISCH, BYLINE`  (x8, marker BYLINE; e.g. NPR-8977;NPR-23811;NPR-23889)
- `CURT NICKISCH reporting`  (x2, marker REPORTING; e.g. NPR-15856;NPR-40649)
- summary-filter tier-2 example: "Floods have killed at least 25 people in central and southern Europe over the past week. In Bavaria, German soldiers evacuated residents as river embankments collapsed, sending flood waters surging through several Alpine"

**Guest-role evidence**

- [3] (title_near_name, utterance[CELESTE HEADLEE, HOST], NPR-8977) "We're going to stick with Curt Nickisch, a reporter at member station WBUR in Boston."
- [3] (title_near_name, utterance[CELESTE HEADLEE, HOST], NPR-8977) "We're joined by Curt Nickisch, a reporter for our member station WBUR in Boston."
- [3] (title_near_name, utterance[CELESTE HEADLEE, HOST], NPR-8977) "With us on the line is Don Borelli, who is chief operating officer at The Soufan Group, former FBI counterterrorism official, and also Curt Nickisch, who is a reporter at member station WBUR."
- [3] (title_near_name, utterance[CELESTE HEADLEE, HOST], NPR-8977) "Also, I want to say thank you to Curt Nickisch, reporter at member station, WBUR in Boston."

**Staff-role evidence**

- [3] (bare 'BYLINE' label (network convention), label, NPR-8977;NPR-23811;NPR-23889) "CURT NICKISCH, BYLINE"
- [3] (network_possessive, utterance[LIANE HANSEN, host], NPR-16364) "NPR's Curt Nickisch joins us from the studios of WBUR in Boston."
- [3] (network_possessive, utterance[LIANE HANSEN, host], NPR-16364) "NPR's Curt Nickisch."
- [3] (network_possessive, utterance[DAVID GREENE, HOST], NPR-26118) "We want to turn to NPR's Curt Nickisch right now."
- [3] (network_possessive, utterance[STEVE INSKEEP, HOST], NPR-26118) "That's NPR's Curt Nickisch."
- [3] (network_possessive, utterance[STEVE INSKEEP, Host], NPR-34723) "NPR's Curt Nickisch has more."
- [3] (byline_signoff (self sign-off), utterance[CURT NICKISCH], NPR-34723) "Curt Nickisch, NPR News."
- [3] (network_possessive, utterance[RENEE MONTAGNE, host], NPR-34829) "Here's NPR's Curt Nickisch."
- [3] (byline_signoff (self sign-off), utterance[CURT NICKISCH], NPR-34829) "Curt Nickisch, NPR News, Boston."
- [2] ('reporting' sign-off label, label, NPR-15856;NPR-40649) "CURT NICKISCH reporting"

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Devlin Barrett

- long-tail: **yes** (long-tail) | interviews (dedup): 3 on 3 dates | span 1641d (2015-01-31 to 2019-07-30) | NPR share 0.30 | 7 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 22 strong, 0 medium (capped score 12); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `REPORTER`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `DEVLIN BARRETT, NATIONAL SECURITY REPORTER, "WASHINGTON POST"`  (x1, marker REPORTER; e.g. CNN-308580)
- `DEVLIN BARRETT, NATIONAL SECURITY REPORTER, "THE WASHINGTON POST"`  (x1, marker REPORTER; e.g. CNN-308744)
- `DEVLIN BARRETT, NATIONAL SECURITY REPORTER, THE WASHINGTON POST`  (x1, marker REPORTER; e.g. CNN-312941)
- `DEVLIN BARRETT, REPORTER, THE WASHINGTON POST (via telephone)`  (x1, marker REPORTER; e.g. CNN-331076)

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-308607;CNN-312938;CNN-315279) "DEVLIN BARRETT, THE WASHINGTON POST"
- [3] (speaker label carries an outside affiliation/title, label, CNN-243267) "DEVLIN BARRETT, WALL STREET JOURNAL"
- [3] (speaker label carries an outside affiliation/title, label, CNN-243316) "DEVLIN BARRETT, "THE WALL STREET JOURNAL""
- [3] (outside-outlet reporter label, label, CNN-308580) "DEVLIN BARRETT, NATIONAL SECURITY REPORTER, "WASHINGTON POST""
- [3] (outside-outlet reporter label, label, CNN-308744) "DEVLIN BARRETT, NATIONAL SECURITY REPORTER, "THE WASHINGTON POST""
- [3] (outside-outlet reporter label, label, CNN-331076) "DEVLIN BARRETT, REPORTER, THE WASHINGTON POST (via telephone)"
- [3] (outlet_near_name, summary, NPR-14823) "Devlin Barrett of The Washington Post talks about the widening Russia investigation, reported to include Trump."
- [3] (outlet_near_name, summary, NPR-25199) "NPR's Arun Rath speaks with Wall Street Journal reporter Devlin Barrett."
- [3] (outlet_near_name, utterance[STEVE INSKEEP, HOST], NPR-9569) "Washington Post reporter Devlin Barrett has been following the story."
- [3] (outlet_near_name, utterance[STEVE INSKEEP, HOST], NPR-9569) "That's Devlin Barrett of The Washington Post."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### James Fredrick

- long-tail: **yes** (long-tail) | interviews (dedup): 4 on 4 dates | span 431d (2017-09-20 to 2018-11-25) | NPR share 1.00 | 3 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 1 medium (capped score 2); staff evidence: 1 strong, 3 medium, 20 weak (capped score 13)
- label filter fired on marker: `BYLINE`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `JAMES FREDRICK, BYLINE`  (x14, marker BYLINE; e.g. NPR-1666;NPR-1842;NPR-1936)

**Guest-role evidence**

- [2] (host_talks_to, summary, NPR-8025) "NPR's Lulu Garcia-Navarro speaks with journalist James Fredrick and "John," who fled from Honduras to the United States with his daughter."

**Staff-role evidence**

- [3] (bare 'BYLINE' label (network convention), label, NPR-1666;NPR-1842;NPR-1936) "JAMES FREDRICK, BYLINE"
- [2] (name_reports, utterance[AUDIE CORNISH, HOST], NPR-1842) "That's James Fredrick reporting from Tijuana, Mexico."
- [2] (name_reports, utterance[AUDIE CORNISH, HOST], NPR-5778) "But these families are undeterred, as James Fredrick reports from the Mexican state of Chiapas."
- [2] (name_reports, utterance[NOEL KING, HOST], NPR-9880) "James Fredrick has the story from Mexico City."
- [1] (bare_role_name, utterance[DAVID GREENE, HOST], NPR-1666) "And let's hear more about what that scene was like from reporter James Fredrick, who joins us this morning."
- [1] (bare_role_name, utterance[DAVID GREENE, HOST], NPR-1666) "Reporter James Fredrick in Tijuana this morning."
- [1] (bare_role_name, utterance[MICHEL MARTIN, HOST], NPR-1841) "Reporter James Fredrick is in Tijuana on the Mexican side of that port of entry, and he's with us now."
- [1] (bare_role_name, utterance[MICHEL MARTIN, HOST], NPR-1841) "That's reporter James Fredrick in Tijuana."
- [1] (bare_role_name, utterance[AUDIE CORNISH, HOST], NPR-1842) "First we go to reporter James Fredrick in Tijuana."
- [1] (bare_role_name, utterance[DAVID GREENE, HOST], NPR-1943) "And we want to turn now to reporter James Fredrick, who is on the ground and has been following them."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Jeff Lunden

- long-tail: **yes** (long-tail) | interviews (dedup): 3 on 3 dates | span 1223d (2007-10-10 to 2011-02-14) | NPR share 1.00 | 1 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 2 medium (capped score 4); staff evidence: 1 strong, 10 medium, 1 weak (capped score 12)
- label filter fired on marker: `BYLINE`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `JEFF LUNDEN, BYLINE`  (x10, marker BYLINE; e.g. NPR-8500;NPR-9626;NPR-12014)

**Guest-role evidence**

- [2] (joins_us, utterance[AUDIE CORNISH, HOST], NPR-17934) "Jeff Lunden is with us at our New York bureau."
- [2] (name_tells_us, utterance[AUDIE CORNISH, HOST], NPR-30451) "Jeff Lunden tells us more."

**Staff-role evidence**

- [3] (bare 'BYLINE' label (network convention), label, NPR-8500;NPR-9626;NPR-12014) "JEFF LUNDEN, BYLINE"
- [2] (name_reports, utterance[ARI SHAPIRO, HOST], NPR-8500) "Reporter Jeff Lunden has this remembrance."
- [2] (name_reports, utterance[RACHEL MARTIN, HOST], NPR-9626) "Jeff Lunden reports."
- [2] (name_reports, utterance[SCOTT SIMON, HOST], NPR-12014) "Our Jeff Lunden reports."
- [2] (name_reports, utterance[AUDIE CORNISH, HOST], NPR-17934) "Jeff Lunden reporting to us from New York."
- [2] (name_reports, utterance[DAVID GREENE, HOST], NPR-19305) "Jeff Lunden reports on Broadway's big night."
- [2] (name_reports, utterance[MICHEL MARTIN, HOST], NPR-21197) "Jeff Lunden has this report."
- [2] (name_reports, utterance[DAVID GREENE, HOST], NPR-23838) "Jeff Lunden has this appreciation of a singular talent."
- [2] (name_reports, utterance[LINDA WERTHEIMER, host], NPR-36208) "The stagehands strike on Broadway has shut down more than two dozen theaters, but it's actually helping some smaller shows in New York, as Jeff Lunden reports."
- [2] (name_reports, utterance[STEVE INSKEEP, host], NPR-36298) "Jeff Lunden has more."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Joe Wertz

- long-tail: **yes** (long-tail) | interviews (dedup): 3 on 3 dates | span 828d (2014-05-29 to 2016-09-03) | NPR share 1.00 | 2 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 2 medium (capped score 4); staff evidence: 1 strong, 1 medium, 1 weak (capped score 6)
- label filter fired on marker: `BYLINE`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `JOE WERTZ, BYLINE`  (x7, marker BYLINE; e.g. NPR-16251;NPR-17572;NPR-19932)
- summary-filter tier-2 example: "An earthquake with a magnitude of 5.6 hit Oklahoma on Saturday morning. StateImpact Oklahoma reporter Joe Wertz talks about earthquakes and their connections to oil and gas production."

**Guest-role evidence**

- [2] (host_talks_to, utterance[MICHEL MARTIN, HOST], NPR-20925) "To find out more, we called Joe Wertz."
- [2] (name_tells_us, utterance[MELISSA BLOCK, HOST], NPR-27225) "As StateImpact's Joe Wertz tells us, that poor wheat harvest could have national consequences."

**Staff-role evidence**

- [3] (bare 'BYLINE' label (network convention), label, NPR-16251;NPR-17572;NPR-19932) "JOE WERTZ, BYLINE"
- [2] (name_reports, summary, NPR-27225) "StateImpact Oklahoma's Joe Wertz reports that some are calling this the worst drought since the '50s — or even since the Dust Bowl."
- [1] (bare_role_name, summary, NPR-20925) "StateImpact Oklahoma reporter Joe Wertz talks about earthquakes and their connections to oil and gas production."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Nancy Mullane

- long-tail: **yes** (long-tail) | interviews (dedup): 10 on 10 dates | span 989d (2006-02-19 to 2008-11-04) | NPR share 1.00 | 5 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 0 strong, 0 medium (capped score 0); staff evidence: 0 strong, 8 medium, 5 weak (capped score 12)
- label filter fired on marker: `REPORTING`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `NANCY MULLANE reporting`  (x1, marker REPORTING; e.g. NPR-4442)
- summary-filter tier-2 example: "A few years ago, homes had a short life on the \"for sale\" market because of eager buyers. Now more homeowners are foreclosure because of high interest rates on home loans. The problem is hitting the black community har"

**Guest-role evidence**

- none found

**Staff-role evidence**

- [2] ('reporting' sign-off label, label, NPR-4442) "NANCY MULLANE reporting"
- [2] (name_reports, summary, NPR-5360) "Nancy Mullane reports."
- [2] (name_reports, utterance[TONY COX, host], NPR-3418) "From San Francisco, reporter Nancy Mullane has the story."
- [2] (name_reports, utterance[FARAI CHIDEYA, host], NPR-5360) "From Oakland, California, Nancy Mullane reports."
- [2] (name_report_noun, utterance[LIANE HANSEN, host], NPR-17563) "In Oakland, California, Nancy Mullane's report begins in a child's bedroom that's doubling as a classroom."
- [2] (name_reports, utterance[LIANE HANSEN, Host], NPR-19045) "From San Francisco Nancy Mullane reports on efforts by linguists and tribal members who are struggling to resurrect one language."
- [2] (name_reports, utterance[RENEE MONTAGNE, Host], NPR-38161) "Nancy Mullane reports from San Francisco."
- [2] (name_reports, utterance[MELISSA BLOCK, host], NPR-41592) "From San Franscisco, Nancy Mullane reports."
- [1] (bare_role_name, summary, NPR-2309) "Reporter Nancy Mullane of member station KALW shows how the problem is impacting black neighborhoods in San Francisco."
- [1] (bare_role_name, utterance[FARAI CHIDEYA, host], NPR-1652) "Reporter Nancy Mullane was there and has this story."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Alan Schwarz

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 1821d (2006-09-13 to 2011-09-08) | NPR share 0.67 | 4 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 28 strong, 2 medium (capped score 16); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `CORRESPONDENT`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `Mr. ALAN SCHWARZ (Correspondent, The New York Times)`  (x1, marker CORRESPONDENT; e.g. NPR-4543)
- `Mr. ALAN SCHWARZ (Reporter, New York Times)`  (x1, marker REPORTER; e.g. NPR-44621)
- `ALAN SCHWARZ, SENIOR REPORTER, "BASEBALL AMERICA"`  (x1, marker REPORTER; e.g. CNN-18774)
- summary-filter tier-2 example: "The Atlanta Braves' 14 straight division title streak officially has come to an end. Author and columnist Alan Schwarz talks about the record-holding team and their recent elimination from the National League East race."

**Guest-role evidence**

- [3] (outside-outlet correspondent label, label, NPR-4543) "Mr. ALAN SCHWARZ (Correspondent, The New York Times)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-5832) "Mr. ALAN SCHWARZ (Author, The Numbers Game: Baseball's Lifelong Fascination with Statistics; Senior Writer, Baseball America)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-16885) "Mr. ALAN SCHWARZ (Sports Writer, Baseball America, New York Times)"
- [3] (outside-outlet reporter label, label, NPR-44621) "Mr. ALAN SCHWARZ (Reporter, New York Times)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-47330) "Mr. ALAN SCHWARZ (Author, The Numbers Game: Baseball's Lifelong Fascination with Statistics)"
- [3] (outside-outlet reporter label, label, CNN-18774) "ALAN SCHWARZ, SENIOR REPORTER, "BASEBALL AMERICA""
- [3] (speaker label carries an outside affiliation/title, label, CNN-218427) "ALAN SCHWARZ, NEW YORK TIMES"
- [3] (speaker label carries an outside affiliation/title, label, CNN-218449) "ALAN SCHWARZ, "NEW YORK TIMES" (via telephone)"
- [3] (outlet_near_name, summary, NPR-1392) "Alan Schwarz, national correspondent, The New York Times Buzz Bissinger, sports columnist, The Daily Beast"
- [3] (outlet_near_name, summary, NPR-4543) "Alan Schwarz of The New York Times and Boston University's Dr."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Alex Cohen

- long-tail: **no** (has-page) | interviews (dedup): 25 on 25 dates | span 917d (2006-09-08 to 2009-03-13) | NPR share 0.97 | 3 programmes
- auto-recommendation: **KEEP-EXCLUDED** — guest evidence: 8 strong, 4 medium (capped score 20); staff evidence: 17 strong, 4 medium, 0 weak (capped score 20)
- label filter fired on marker: `HOST`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `ALEX COHEN, host`  (x340, marker HOST; e.g. NPR-8;NPR-11;NPR-12)
- `ALEX COHEN, Host`  (x11, marker HOST; e.g. NPR-8492;NPR-8494;NPR-8614)
- `ALEX COHEN reporting`  (x9, marker REPORTING; e.g. NPR-15983;NPR-16184;NPR-17186)

**Guest-role evidence**

- [3] (org_near_name, summary, NPR-2122) "Jeff Martin, Kaposi's sarcoma expert and professor at the University of California San Francisco School of Medicine, talks to Alex Cohen about what this means."
- [3] (outlet_near_name, summary, NPR-2287) "Marketplace's Amy Scott talks with Alex Cohen about how Ticketmaster is fighting back."
- [3] (org_near_name, summary, NPR-2288) "Alex Cohen then talks to Danielle Pletka of the American Enterprise Institute, who says there's no such thing as an Iran strategy."
- [3] (outlet_near_name, summary, NPR-2290) "Alex Cohen clicks along with Slate blogger Chris Beam, who has been tracking what people are most curious about when they look up the 2008 presidential candidates."
- [3] (outlet_near_name, summary, NPR-2939) "Sam Eaton of Marketplace talks with Alex Cohen."
- [3] (outlet_near_name, summary, NPR-8985) "Patty Stonesifer, former CEO of the Bill and Melinda Gates Foundation and a Slate advice columnist, talks with Alex Cohen about how she handles panhandling."
- [3] (outlet_near_name, summary, NPR-17482) "Alex Cohen of member station KQED reports on a controversial roadside billboard in the Los Angeles metro area advertising a local Spanish-language television station."
- [3] (outlet_near_name, summary, NPR-44404) "Sam Eaton of Marketplace talks with Alex Cohen about the merger."
- [2] (speaker label carries an outside affiliation/title, label, CNN-124216) "ALEX COHEN, SMALL BUSINESS OWNER"
- [2] (host_talks_to, summary, NPR-12) "Our personal finance contributor talks with Alex Cohen about ways to help teens find a job."

**Staff-role evidence**

- [3] (bare 'HOST' label (network convention), label, NPR-8;NPR-11;NPR-12) "ALEX COHEN, host"
- [3] (acts as the interviewer/host in this summary, summary, NPR-462) "The Gratitude Campaign urges people to show their appreciation with a sign similar to the American Sign Language gesture for "Thank You." Alex Cohen talks with Scott Truitt who started the campaign."
- [3] (acts as the interviewer/host in this summary, summary, NPR-2285) "NPR's Senior Washington Editor Ron Elving joins host Alex Cohen for a look ahead to Tuesday's Republican presidential candidates' debate."
- [3] (network_possessive, summary, NPR-7755) "First, NPR's Alex Cohen talks to David Rennie of The Economist magazine, Rami Khouri, editor of The Daily Star in Beirut and Mark Magnier, Beijing correspondent for The Los Angeles Times."
- [3] (acts as the interviewer/host in this summary, summary, NPR-8379) "Host Alex Cohen talks with NPR Senior Washington Editor Ron Elving about this week in politics."
- [3] (acts as the interviewer/host in this summary, summary, NPR-8491) "NPR News Analyst Juan Williams talks with host Alex Cohen about the Republican strategy."
- [3] (acts as the interviewer/host in this summary, summary, NPR-8499) "In another installment of Dispatches from the Downturn, host Alex Cohen talks with Mike Frankovich, owner of NoHo Scooters in North Hollywood, Calif., about how his business is coping during the recession."
- [3] (acts as the interviewer/host in this summary, summary, NPR-9090) "Host Alex Cohen takes a look at the proceedings."
- [3] (acts as the interviewer/host in this summary, summary, NPR-9091) "Host Alex Cohen talks to Dow Jones reporter Brett Philbin about what the loss means for the state."
- [3] (acts as the interviewer/host in this summary, summary, NPR-9092) "Host Alex Cohen talks with NPR's Mike Pesca for a preview of Super Bowl XLIII."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Aryn Baker

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 1500d (2014-05-16 to 2018-06-24) | NPR share 0.75 | 3 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 12 strong, 0 medium (capped score 12); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `CORRESPONDENT`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `ARYN BAKER, CORRESPONDENT, TIME MAGAZINE`  (x1, marker CORRESPONDENT; e.g. CNN-267653)

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-206948) "ARYN BAKER, TIME MIDDLE EAST BUREAU CHIEF"
- [3] (outside-outlet correspondent label, label, CNN-267653) "ARYN BAKER, CORRESPONDENT, TIME MAGAZINE"
- [3] (outlet_near_name, summary, NPR-16112) "Steve Inskeep talks to Aryn Baker of Time magazine about a Liberian nursing assistant, who cared for Ebola patients, but who died earlier this month after childbirth because no one would help her."
- [3] (outlet_near_name, summary, NPR-46207) "NPR's Michel Martin speaks with Time magazine's Aryn Baker who's been out on a ride with some of the first women drivers."
- [3] (outlet_near_name, utterance[STEVE INSKEEP, HOST], NPR-7393) "Time magazine's Aryn Baker is among them and she joins us now from the capital city of Damascus."
- [3] (outlet_near_name, utterance[STEVE INSKEEP, HOST], NPR-7393) "Aryn Baker of Time magazine, thanks very much."
- [3] (outlet_near_name, utterance[STEVE INSKEEP, HOST], NPR-16112) "And we're going to talk about this with Aryn Baker of Time magazine who's on the line."
- [3] (outlet_near_name, utterance[STEVE INSKEEP, HOST], NPR-16112) "Aryn Baker of Time magazine, thank you very much."
- [3] (outlet_near_name, utterance[MICHEL MARTIN, HOST], NPR-46207) "That's Aryn Baker of Time magazine."
- [3] (org_near_name, utterance[BLITZER], CNN-206948) "Joining us now is Aryn Baker, the Middle East bureau chief of "TIME" magazine, our sister publication."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### David Gardner

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 553d (2006-06-01 to 2007-12-06) | NPR share 0.50 | 4 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 11 strong, 10 medium (capped score 20); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `HOST`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `DAVID GARDNER, HOST "MOTLEY FOOL"`  (x1, marker HOST; e.g. CNN-74667)

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, NPR-14947) "Mr. DAVID GARDNER (Co-Founder, The Motley Fool)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-18195) "Mr. DAVID GARDNER (Co-Founder, Motley Fool)"
- [3] (speaker label carries an outside affiliation/title, label, CNN-48668) "DAVID GARDNER, AUTHOR, "THE LAST OF THE HITLERS""
- [3] (title_near_name, summary, NPR-14947) "In his final visit before the end of 2007, David Gardner, co-founder of the Motley Fool, offers suggestions for ways to tune up your portfolio before 2008 arrives."
- [3] (outlet_near_name, summary, NPR-16497) "In our monthly visit with the Motley Fool, co-founder David Gardner talks about the recent plunge on Wall Street and checks in on the Talk of the Nation fantasy portfolio."
- [3] (title_near_name, summary, NPR-18195) "David Gardner, co-founder of the Motley Fool, answers questions on how to make wise investment decisions."
- [3] (title_near_name, utterance[NEAL CONAN, host], NPR-14947) "David Gardner is co-founder of the Motley Fool."
- [3] (title_near_name, utterance[NEAL CONAN, host], NPR-14947) "David Gardner is the co-founder of the Motley Fool."
- [3] (title_near_name, utterance[NEAL CONAN, host], NPR-16497) "David Gardner, co-founder of the Motley Fool from Fool headquarters in Alexandria, Virginia."
- [3] (title_near_name, utterance[NEAL CONAN, Host], NPR-18195) "David Gardner is co-founder of the Motley Fool, a multimedia company devoted to helping people sort through their investment decisions."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### David Walker

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 3214d (2008-08-09 to 2017-05-28) | NPR share 0.08 | 20 programmes
- auto-recommendation: **AMBIGUOUS** — guest evidence: 22 strong, 24 medium (capped score 20); staff evidence: 2 strong, 0 medium, 0 weak (capped score 6)
- label filter fired on marker: `ANCHOR`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `DAVID WALKER, CNN ANCHOR`  (x9, marker ANCHOR; e.g. CNN-1279;CNN-9218;CNN-95004)
- `DAVID WALKER, FORMER CNN ANCHOR`  (x3, marker ANCHOR; e.g. CNN-95015;CNN-95020;CNN-354952)

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-161195;CNN-161225;CNN-162330) "DAVID WALKER, CEO, COMEBACK AMERICA INITIATIVE"
- [3] (speaker label carries an outside affiliation/title, label, CNN-145591;CNN-152566) "DAVID WALKER, CEO, PETER G. PETERSON FOUNDATION"
- [3] (speaker label carries an outside affiliation/title, label, CNN-158229;CNN-158256) "DAVID WALKER, FOUNDER & CEO, THE COME BACK AMERICA INITIATIVE"
- [3] (speaker label carries an outside affiliation/title, label, CNN-176258;CNN-176288) "DAVID WALKER, FOUNDER & CEO, COMEBACK AMERICA INITIATIVE"
- [3] (speaker label carries an outside affiliation/title, label, NPR-35211) "Mr. DAVID WALKER (President/CEO, Peter G. Peterson Foundation; Former Comptroller General)"
- [3] (speaker label carries an outside affiliation/title, label, CNN-120305) "DR. DAVID WALKER, FORENSIC PSYCHIATRIST"
- [3] (speaker label carries an outside affiliation/title, label, CNN-131087) "DAVID WALKER, PRESIDENT/CEO, PETER G. PETERSON FOUNDATION"
- [3] (speaker label carries an outside affiliation/title, label, CNN-145497) "DAVID WALKER, AUTHOR, WALKER REPORT"
- [3] (speaker label carries an outside affiliation/title, label, CNN-148267) "DAVID WALKER, PRESIDENT AND CEO, PETER G. PETERSON FOUNDATION"
- [3] (speaker label carries an outside affiliation/title, label, CNN-217769) "DAVID WALKER, CHAIRMAN, BARCLAY'S BANK"

**Staff-role evidence**

- [3] (network-owned speaker label (ANCHOR), label, CNN-1279;CNN-9218;CNN-95004) "DAVID WALKER, CNN ANCHOR"
- [3] (network-owned speaker label (ANCHOR), label, CNN-95015;CNN-95020;CNN-354952) "DAVID WALKER, FORMER CNN ANCHOR"

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Elisabeth Rosenthal

- long-tail: **no** (has-page) | interviews (dedup): 4 on 4 dates | span 2602d (2011-12-06 to 2019-01-20) | NPR share 0.57 | 5 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 11 strong, 2 medium (capped score 16); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `REPORTER`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `Ms. ELISABETH ROSENTHAL (Environment Reporter, New York Times)`  (x1, marker REPORTER; e.g. NPR-34635)

**Guest-role evidence**

- [3] (outside-outlet reporter label, label, NPR-34635) "Ms. ELISABETH ROSENTHAL (Environment Reporter, New York Times)"
- [3] (outlet_near_name, summary, NPR-626) "Ian Lee, professor, Sprott School of Business, Carleton University Elisabeth Rosenthal, reporter and blogger, New York Times Bill Snodgrass, pharmacist in North Platte, Nebraska"
- [3] (outlet_near_name, summary, NPR-34635) "NPR's Robert Siegel talks with Elisabeth Rosenthal, environment reporter for the New York Times, who is in Budapest."
- [3] (outlet_near_name, utterance[NEAL CONAN, HOST], NPR-626) "Our guests, New York Times' Elisabeth Rosenthal, she wrote a recent piece headlined "The Junking of the Postal Service;" also Ian Lee, a professor at the Sprott School of Business at Carleton University in Ottawa."
- [3] (outlet_near_name, utterance[NEAL CONAN, HOST], NPR-626) "Elisabeth Rosenthal is a reporter and blogger for The New York Times."
- [3] (org_near_name, utterance[NEAL CONAN, HOST], NPR-626) "Elisabeth Rosenthal, I think quasigovernmental agency is probably more accurate."
- [3] (author_of, utterance[LULU GARCIA-NAVARRO, HOST], NPR-7952) "Elisabeth Rosenthal is the author of "An American Sickness: How Healthcare Became A Big Business And How You Can Take It Back (ph)." Thank you so much."
- [3] (author_of, utterance[SCOTT SIMON, HOST], NPR-11265) "Elisabeth Rosenthal, editor-in-chief of Kaiser Health News and author of "An American Sickness: How Health Care Became Big Business And How You Can Take It Back." Thanks so much for being with us."
- [3] (outlet_near_name, utterance[ROBERT SIEGEL, host], NPR-34635) "Environmental reporter Elisabeth Rosenthal of the New York Times is in Budapest."
- [3] (outlet_near_name, utterance[ROBERT SIEGEL, host], NPR-34635) "That's environmental reporter Elisabeth Rosenthal of the New York Times, speaking to us from Budapest in Hungary."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Kim Masters

- long-tail: **no** (has-page) | interviews (dedup): 32 on 32 dates | span 4826d (2006-01-26 to 2019-04-14) | NPR share 0.92 | 9 programmes
- auto-recommendation: **AMBIGUOUS** — guest evidence: 26 strong, 3 medium (capped score 18); staff evidence: 21 strong, 1 medium, 3 weak (capped score 17)
- label filter fired on marker: `BYLINE`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `KIM MASTERS reporting`  (x11, marker REPORTING; e.g. NPR-16067;NPR-19040;NPR-19412)
- `KIM MASTERS, EDITOR-AT-LARGE, THE HOLLYWOOD REPORTER`  (x3, marker REPORTER; e.g. CNN-249684;CNN-323465;CNN-323671)
- `KIM MASTERS, BYLINE`  (x2, marker BYLINE; e.g. NPR-27974;NPR-47286)
- `KIM MASTERS, HOLLYWOOD REPORTER`  (x2, marker REPORTER; e.g. CNN-204299;CNN-204304)
- `KIM MASTERS, EDITOR AT LARGE, "THE HOLLYWOOD REPORTER"`  (x2, marker REPORTER; e.g. CNN-245488;CNN-245884)
- `KIM MASTERS, SENIOR CORRESPONDENT, INSIDE.COM`  (x1, marker CORRESPONDENT; e.g. CNN-25881)
- summary-filter tier-2 example: "News that NBC plans to make a mini-series about Hillary Clinton and CNN will commission a documentary about her, sparked controversy this week. The Republican National Committee and a liberal media watchdog group have de"

**Guest-role evidence**

- [3] (outside-outlet reporter label, label, CNN-249684;CNN-323465;CNN-323671) "KIM MASTERS, EDITOR-AT-LARGE, THE HOLLYWOOD REPORTER"
- [3] (outside-outlet reporter label, label, CNN-204299;CNN-204304) "KIM MASTERS, HOLLYWOOD REPORTER"
- [3] (speaker label carries an outside affiliation/title, label, CNN-12267) "KIM MASTERS, AUTHOR, "THE KEYS TO THE KINGDOM""
- [3] (outside-outlet correspondent label, label, CNN-25881) "KIM MASTERS, SENIOR CORRESPONDENT, INSIDE.COM"
- [3] (speaker label carries an outside affiliation/title, label, CNN-27472) "KIM MASTERS, "VANITY FAIR""
- [3] (speaker label carries an outside affiliation/title, label, CNN-54326) "KIM MASTERS, ESQUIRE MAGAZINE"
- [3] (speaker label carries an outside affiliation/title, label, CNN-96856) "KIM MASTERS, "RADAR" MAGAZINE"
- [3] (outside-outlet reporter label, label, CNN-204239) "KIM MASTERS, EDITOR AT LARGE, "HOLLYWOOD REPORTER""
- [3] (outside-outlet reporter label, label, CNN-323402) "KIM MASTERS, EDITOR-IN-LARGE, "THE HOLLYWOOD REPORTER""
- [3] (outlet_near_name, summary, NPR-278) "Just in time for Oscar weekend, NPR's Michel Martin speaks with Kim Masters, editor-at-large of The Hollywood Reporter, about the culture in Hollywood post-Harvey Weinstein."

**Staff-role evidence**

- [3] (bare 'BYLINE' label (network convention), label, NPR-27974;NPR-47286) "KIM MASTERS, BYLINE"
- [3] (network_possessive, utterance[ALEX CHADWICK, host], NPR-5032) "NPR's Kim Masters."
- [3] (network_possessive, utterance[MICHELE NORRIS, Host], NPR-5857) "NPR's Kim Masters is there."
- [3] (network_possessive, utterance[MICHELE NORRIS, Host], NPR-5857) "That was NPR's Kim Masters, reporting from the Upfronts."
- [3] (network_possessive, utterance[MADELEINE BRAND, host], NPR-16067) "NPR's Kim Masters has been looking into the star's relationship with Scientology for an article that appears in the upcoming issue of Radar magazine."
- [3] (network_possessive, utterance[SCOTT SIMON, host], NPR-18785) "NPR's Kim Masters reports."
- [3] (byline_signoff (self sign-off), utterance[KIM MASTERS], NPR-18785) "Kim Masters, NPR News, Los Angeles."
- [3] (network_possessive, utterance[LIANE HANSEN, host], NPR-19040) "NPR's Kim Masters explains."
- [3] (network_possessive, utterance[SCOTT SIMON, host], NPR-19412) "NPR's Kim Masters covers the movie industry; joins us from NPR West."
- [3] (network_possessive, utterance[SCOTT SIMON, host], NPR-19412) "NPR's Kim Masters at NPR West."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Marc Ambinder

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 3111d (2008-08-14 to 2017-02-19) | NPR share 0.43 | 6 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 16 strong, 4 medium (capped score 20); staff evidence: 0 strong, 0 medium, 0 weak (capped score 0)
- label filter fired on marker: `REPORTER`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `Mr. MARC AMBINDER (Reporter, National Journal)`  (x1, marker REPORTER; e.g. NPR-3397)

**Guest-role evidence**

- [3] (outside-outlet reporter label, label, NPR-3397) "Mr. MARC AMBINDER (Reporter, National Journal)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-39206) "Mr. MARC AMBINDER (The Atlantic)"
- [3] (speaker label carries an outside affiliation/title, label, NPR-45044) "Mr. MARC AMBINDER (Politics Editor, The Atlantic)"
- [3] (speaker label carries an outside affiliation/title, label, CNN-117081) "MARC AMBINDER, NATIONAL REVIEW "HOTLINE""
- [3] (speaker label carries an outside affiliation/title, label, CNN-203498) "MARC AMBINDER, CO-AUTHOR, "DEEP STATE""
- [3] (outlet_near_name, summary, NPR-39206) "Marc Ambinder, reporter and blogger for the Atlantic, offers his insight."
- [3] (outlet_near_name, summary, NPR-45044) "Marc Ambinder of The Atlantic talks about his own fight against obesity."
- [3] (outlet_near_name, utterance[ROBERT SIEGEL, host], NPR-39206) "Marc Ambinder of the Atlantic has been following this story and joins us now."
- [3] (outlet_near_name, utterance[ROBERT SIEGEL, host], NPR-39206) "Marc Ambinder of the Atlantic, thank you very much."
- [3] (outlet_near_name, utterance[NEAL CONAN, host], NPR-45044) "In the May issue of The Atlantic, Marc Ambinder looked closely at this plan and at the many unsuccessful initiatives that preceded it, and he brings personal experience to this story."

**Staff-role evidence**

- none found

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Michael Isikoff

- long-tail: **no** (has-page) | interviews (dedup): 6 on 6 dates | span 4531d (2005-10-26 to 2018-03-23) | NPR share 0.10 | 32 programmes
- auto-recommendation: **AMBIGUOUS** — guest evidence: 80 strong, 6 medium (capped score 20); staff evidence: 1 strong, 0 medium, 0 weak (capped score 3)
- label filter fired on marker: `REPORTER`; summary filter said: `review`

**Exclusion evidence — the labels that triggered the filter**

- `MICHAEL ISIKOFF, CHIEF INVESTIGATIVE CORRESPONDENT, YAHOO NEWS`  (x38, marker CORRESPONDENT; e.g. CNN-313455;CNN-313610;CNN-314227)
- `MICHAEL ISIKOFF, CHIEF INVESTIGATIVE CORRESPONDENT, YAHOO! NEWS`  (x22, marker CORRESPONDENT; e.g. CNN-308014;CNN-308172;CNN-312095)
- `MICHAEL ISIKOFF, CHIEF INVESTIGATION CORRESPONDENT, YAHOO NEWS`  (x7, marker CORRESPONDENT; e.g. CNN-321112;CNN-323768;CNN-330185)
- `MICHAEL ISIKOFF, INVESTIGATIVE REPORTER, "NEWSWEEK"`  (x6, marker REPORTER; e.g. CNN-45423;CNN-86297;CNN-121507)
- `MICHAEL ISIKOFF, INVESTIGATIVE CORRESPONDENT, "NEWSWEEK"`  (x4, marker CORRESPONDENT; e.g. CNN-86934;CNN-99162;CNN-114289)
- `MICHAEL ISIKOFF, "NEWSWEEK" REPORTER`  (x3, marker REPORTER; e.g. CNN-94557;CNN-94567;CNN-94570)
- summary-filter tier-2 example: "NPR's Robert Siegel speaks with investigative reporter Michael Isikoff of Yahoo News about what it takes to start an independent investigation outside of the FBI."

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-2529;CNN-22728;CNN-32999) "MICHAEL ISIKOFF, "NEWSWEEK""
- [3] (outside-outlet correspondent label, label, CNN-313455;CNN-313610;CNN-314227) "MICHAEL ISIKOFF, CHIEF INVESTIGATIVE CORRESPONDENT, YAHOO NEWS"
- [3] (outside-outlet correspondent label, label, CNN-321112;CNN-323768;CNN-330185) "MICHAEL ISIKOFF, CHIEF INVESTIGATION CORRESPONDENT, YAHOO NEWS"
- [3] (speaker label carries an outside affiliation/title, label, CNN-38986;CNN-40921;CNN-45919) "MICHAEL ISIKOFF, "NEWSWEEK" MAGAZINE"
- [3] (outside-outlet reporter label, label, CNN-45423;CNN-86297;CNN-121507) "MICHAEL ISIKOFF, INVESTIGATIVE REPORTER, "NEWSWEEK""
- [3] (outside-outlet correspondent label, label, CNN-86934;CNN-99162;CNN-114289) "MICHAEL ISIKOFF, INVESTIGATIVE CORRESPONDENT, "NEWSWEEK""
- [3] (outside-outlet reporter label, label, CNN-94557;CNN-94567;CNN-94570) "MICHAEL ISIKOFF, "NEWSWEEK" REPORTER"
- [3] (speaker label carries an outside affiliation/title, label, CNN-335255;CNN-356007;CNN-356522) "MICHAEL ISIKOFF, AUTHOR, "RUSSIAN ROULETTE""
- [3] (outside-outlet correspondent label, label, CNN-6453;CNN-58502) "MICHAEL ISIKOFF, INVESTIGATIVE CORRESPONDENT, "NEWSWEEK" MAGAZINE"
- [3] (outside-outlet correspondent label, label, CNN-86509;CNN-98079) "MICHAEL ISIKOFF, "NEWSWEEK" INVESTIGATIVE CORRESPONDENT"

**Staff-role evidence**

- [3] (acts as the interviewer/host in this summary, utterance[ROBERT SIEGEL, HOST], NPR-19350) "Yahoo News chief investigative correspondent Michael Isikoff sat down with Bashar al-Assad, the first in-depth interview the Syrian president has given to an American reporter since President Trump's inauguration."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

### Ronald Kessler

- long-tail: **no** (has-page) | interviews (dedup): 3 on 3 dates | span 3412d (2005-06-01 to 2014-10-04) | NPR share 0.06 | 28 programmes
- auto-recommendation: **RE-ADMIT** — guest evidence: 68 strong, 4 medium (capped score 20); staff evidence: 0 strong, 1 medium, 1 weak (capped score 3)
- label filter fired on marker: `CORRESPONDENT`; summary filter said: `no`

**Exclusion evidence — the labels that triggered the filter**

- `RONALD KESSLER, INVESTIGATIVE REPORTER`  (x3, marker REPORTER; e.g. CNN-186614;CNN-239421;CNN-243253)
- `Mr. RONALD KESSLER (Chief Washington Correspondent, Newsmax.com)`  (x1, marker CORRESPONDENT; e.g. NPR-40614)
- `RONALD KESSLER, INVESTIGATIVE REPORTER, AUTHOR, "THE FIRST FAMILY DETAIL"`  (x1, marker REPORTER; e.g. CNN-239920)

**Guest-role evidence**

- [3] (speaker label carries an outside affiliation/title, label, CNN-30234;CNN-54988;CNN-83759) "RONALD KESSLER, AUTHOR"
- [3] (speaker label carries an outside affiliation/title, label, CNN-85142;CNN-85155;CNN-85172) "RONALD KESSLER, AUTHOR, "INSIDE THE CIA""
- [3] (speaker label carries an outside affiliation/title, label, CNN-121350;CNN-122406;CNN-123178) "RONALD KESSLER, AUTHOR, "THE TERRORIST WATCH""
- [3] (speaker label carries an outside affiliation/title, label, CNN-186675;CNN-251244;CNN-251286) "RONALD KESSLER, AUTHOR, "IN THE PRESIDENT'S SECRET SERVICE""
- [3] (speaker label carries an outside affiliation/title, label, CNN-239933;CNN-243202;CNN-263054) "RONALD KESSLER, AUTHOR, "THE FIRST FAMILY DETAIL""
- [3] (speaker label carries an outside affiliation/title, label, CNN-184374;CNN-184380;CNN-184383) "RONALD KESSLER, JOURNALIST/AUTHOR (via telephone)"
- [3] (speaker label carries an outside affiliation/title, label, CNN-184378;CNN-184389;CNN-184393) "RONALD KESSLER, JOURNALIST/AUTHOR"
- [3] (speaker label carries an outside affiliation/title, label, CNN-62254;CNN-65191) "RONALD KESSLER, AUTHOR, "THE BUREAU""
- [3] (speaker label carries an outside affiliation/title, label, CNN-77766;CNN-77886) "RONALD KESSLER, AUTHOR, "THE CIA AT WAR""
- [3] (speaker label carries an outside affiliation/title, label, CNN-195509;CNN-195522) "RONALD KESSLER, AUTHOR, (voice-over)"

**Staff-role evidence**

- [2] (bare 'REPORTER' label, no affiliation, label, CNN-186614;CNN-239421;CNN-243253) "RONALD KESSLER, INVESTIGATIVE REPORTER"
- [1] (bare_role_name, utterance[FREDRICKA WHITFIELD, CNN ANCHOR], CNN-184374) ""The Post" was tipped off to the allegations by former "Post" reporter Ronald Kessler."

**Human verdict:**  [ ] RE-ADMIT   [ ] KEEP-EXCLUDED   [ ] UNSURE

---

## CLOSED AS MOOT — 2026-07-28

**Owner ruling, stop point iii** ([`results/stage2_confirm/RULINGS_STOPPOINT3_20260728.md`](stage2_confirm/RULINGS_STOPPOINT3_20260728.md),
decision 5). **This sheet is closed as moot for this project version. The
20-subject human spot-check is not owed.**

Three reasons:

- **It gates one thing only: re-admission of the 292-subject reserve.** Nothing
  else in the project depends on it. No number, no bar and no verdict anywhere
  in Stage 2 waits on it.
- **The corpus is final for this version.** The confirmatory draw is made and
  the run is complete. Re-admitting anyone now would change the drawn cohort
  after the draw, which is exactly what the frozen draw procedure exists to
  prevent — the same reasoning that deferred the two name-resolution defects in
  [`RULINGS_20260728.md`](stage2_confirm/RULINGS_20260728.md).
- **Nothing is discarded.** The **106 auto-re-admit candidates**, the 110
  ambiguous and the 76 keep-excluded stay recorded here and in
  [`staff_reserve_dossiers.csv`](staff_reserve_dossiers.csv), available as an
  input to **any future corpus revision**.

**Closed as moot is not "skipped" and is not a deviation.** There is no decision
left for this sheet to gate in this version, so there is no obligation left
unmet. If the corpus is ever rebuilt, this sheet is where that work starts, and
the human check would be owed again at that point.
