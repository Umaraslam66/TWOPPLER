# Fuzzy host rule — owner spot-check sheet

20 of the 151 (descriptor, programme) pairs the D3.2 fuzzy arm fires on
at ratio >= 0.55. Drawn with `random.Random(79)`, stratified across the
four ratio bands and across the three verdicts, then printed in ratio
order. **My verdicts are not in this file** — they are in
`fuzzy_host_spotcheck_key.md`.

For each row, decide what the speaker is **on this programme**:

* `anchor` — they present this show (what D3.2 exists to find)
* `staff` — house staff of the show: correspondent, analyst, producer
  (host side of the host/guest split, but not the interviewer)
* `false` — a guest, a relative of the host, someone from another
  network, or parse noise

`ratio` is difflib's similarity between the normalised descriptor and the
normalised programme. The current threshold is 0.60; the proposal is 0.65
plus a guard. `rows` is how many label rows in the whole corpus carry this
exact pair, so a wrong call on a high-`rows` line costs more.

---

### 1. ratio 0.9167 — CNN-93766 (1 label row corpus-wide)

* **descriptor**: `CAPITOL GANG`
* **programme**: `CNN CAPITAL GANG`
* full speaker label: `E.J. DIONNE, CAPITOL GANG`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after SHIELDS] Why, no. And in fact, I think Democrats would like DeLay to hang around at least through the 2006 election. I think his problem is that Republicans are beginning to slip away. "The Wall Street Journal" editorial page is hardly a left- wing sheet, and Congressm

**Your verdict (anchor / staff / false): ______________**

---

### 2. ratio 0.7143 — CNN-166540 (1 label row corpus-wide)

* **descriptor**: `PRIEST`
* **programme**: `CNN PRESENTS`
* full speaker label: `FATHER WILLIAM FULCO, PRIEST`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after ANDERSON (voice-over)] These are incredibly passionate men.

**Your verdict (anchor / staff / false): ______________**

---

### 3. ratio 0.7059 — CNN-25421 (1 label row corpus-wide)

* **descriptor**: `"USA TODAY"`
* **programme**: `Saturday`
* full speaker label: `DAVID FIELD, "USA TODAY"`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after BRIAN NELSON, CNN ANCHOR] Thank you.

**Your verdict (anchor / staff / false): ______________**

---

### 4. ratio 0.7059 — CNN-94409 (2 label rows corpus-wide)

* **descriptor**: `HOST "INSIDE POLITICS"`
* **programme**: `JUDY WOODRUFF'S INSIDE POLITICS`
* full speaker label: `JUDY WOODRUFF, HOST "INSIDE POLITICS"`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after ANNOUNCER] Thank you for joining us. Republicans who were hoping to stop Hillary Clinton's political career dead in its tracks may be looking to find ammunition in a California courtroom. That is where jury selection is beginning today in the trial of Senator Clinton's f

**Your verdict (anchor / staff / false): ______________**

---

### 5. ratio 0.7027 — CNN-48649 (3 label rows corpus-wide)

* **descriptor**: `NEWSNIGHT ANCHOR`
* **programme**: `CNN NEWSNIGHT AARON BROWN`
* full speaker label: `WOLF BLITZER, NEWSNIGHT ANCHOR`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after (opens the transcript)] I'm Wolf Blitzer. I'm in for Aaron Brown. Congress got stood up today and a group of spurned legislators did not take it well at all. We're talking about Enron and it's former Chairman Ken Lay, who decided yesterday that he wouldn't appear before a Senate Comm

**Your verdict (anchor / staff / false): ______________**

---

### 6. ratio 0.6957 — CNN-312942 (1 label row corpus-wide)

* **descriptor**: `CNN AMANPOUR HOST`
* **programme**: `CNN'S AMANPOUR`
* full speaker label: `CHRISTIANE AMANPOUR, CNN AMANPOUR HOST`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after (opens the transcript)] Tonight, our special one-hour edition live from Manchester, as thousands continue to bring flowers here to remember the lives that were lost in the terror attack that killed 22 people, including children. And as we come on air; new details about the investigat

**Your verdict (anchor / staff / false): ______________**

---

### 7. ratio 0.6923 — CNN-52391 (7 label rows corpus-wide)

* **descriptor**: `CNN STUDENT BUREAU`
* **programme**: `CNN STUDENT NEWS`
* full speaker label: `SIR BLACK, CNN STUDENT BUREAU (voice-over)`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after WALCOTT] Failure is not an option is a bold and inspiring statement that accurately reflects the attitude of NASA's Mission Control. Former director of Flight Operations Gene Kranz defines what this means.

**Your verdict (anchor / staff / false): ______________**

---

### 8. ratio 0.6667 — CNN-356090 (2 label rows corpus-wide)

* **descriptor**: `SPECIAL PROSECUTOR`
* **programme**: `CNN SPECIAL REPORTS`
* full speaker label: `ROBERT FISK, SPECIAL PROSECUTOR`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after ZAKARIA (voice-over)] As quickly and as thoroughly as possible.

**Your verdict (anchor / staff / false): ______________**

---

### 9. ratio 0.6316 — CNN-348399 (1 label row corpus-wide)

* **descriptor**: `CNN CRIME AND JUSTICE EDITORIAL PRODUCER`
* **programme**: `CRIME AND JUSTICE WITH ASHLEIGH BANFIELD`
* full speaker label: `TALIA TIRELLA, CNN CRIME AND JUSTICE EDITORIAL PRODUCER (via telephone)`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after BANFIELD] Yes, that`s right, Ashleigh. So as Jenna said, you know, this alleged mistress, whoever he was having an affair with, Chris Watts, you know, we`re not sure at this point who this person is. But the name is floating around out there, so I was able to track down

**Your verdict (anchor / staff / false): ______________**

---

### 10. ratio 0.6286 — CNN-151719 (2 label rows corpus-wide)

* **descriptor**: `" 1997) LARRY KING, HOST`
* **programme**: `CNN LARRY KING LIVE`
* full speaker label: `BEGIN VIDEO CLIP OF "MAD CITY," 1997) LARRY KING, HOST`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after KING] Good evening. Welcome to LARRY KING LIVE. How are the kids, Sam?

**Your verdict (anchor / staff / false): ______________**

---

### 11. ratio 0.6269 — CNN-317198 (1 label row corpus-wide)

* **descriptor**: `PRIMETIME JUSTICE SHOW HOST`
* **programme**: `PRIMETIME JUSTICE WITH ASHLEIGH BANFIELD`
* full speaker label: `ASHLEIGH BANFIELD, PRIMETIME JUSTICE SHOW HOST`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after SIMPSON] You heard it. In just a few short months, O.J. Simpson will once again be walking as a free machine in America after spending nearly nine years at the Lovelock Prison in Nevada. The Nevada Parole Board voted unanimously, four of them, to set O.J. Simpson loose

**Your verdict (anchor / staff / false): ______________**

---

### 12. ratio 0.6061 — CNN-94672 (1 label row corpus-wide)

* **descriptor**: `AIR AMERICA RADIO`
* **programme**: `AMERICAN MORNING`
* full speaker label: `RACHEL MADDOW, AIR AMERICA RADIO`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after O'BRIEN] Well, you know, the -- no officers have been prosecuted for Abu Ghraib and there's the Downing Street memo that says the war on Iraq was -- had nothing do with weapons, so the Bush administration has decided that its strategy for approaching the Muslim public 

**Your verdict (anchor / staff / false): ______________**

---

### 13. ratio 0.6000 — CNN-257253 (1 label row corpus-wide)

* **descriptor**: `NEWS CORP`
* **programme**: `NEWS STREAM`
* full speaker label: `RUPERT MURDOCH, NEWS CORP`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after STELTER] I would just like to say one sentence. This is the most humble day of my life.

**Your verdict (anchor / staff / false): ______________**

---

### 14. ratio 0.5938 — CNN-24029 (1 label row corpus-wide)

* **descriptor**: `AUSTIN BUREAU CHIEF, "THE DALLAS MORNING NEWS"`
* **programme**: `Saturday Morning News`
* full speaker label: `WAYNE SLATER, AUSTIN BUREAU CHIEF, "THE DALLAS MORNING NEWS"`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after KAGAN] Good morning.

**Your verdict (anchor / staff / false): ______________**

---

### 15. ratio 0.5882 — CNN-212726 (18 label rows corpus-wide)

* **descriptor**: `NEW JERSEY`
* **programme**: `NEW DAY`
* full speaker label: `GOV. CHRIS CHRISTIE, (R) NEW JERSEY`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after UNIDENTIFIED MALE] These are complicated issues. I know you think it's simple.

**Your verdict (anchor / staff / false): ______________**

---

### 16. ratio 0.5789 — CNN-295220 (1 label row corpus-wide)

* **descriptor**: `CNN THE LEAD HOST`
* **programme**: `THE LEAD WITH JAKE TAPPER`
* full speaker label: `JAKE TAPPER, CNN THE LEAD HOST`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after JOHNSON] Oh, Governor Johnson. Welcome back to THE LEAD. The libertarian presidential candidate doing more to harm the cause of marijuana legalization than every Cheech & Chong movie combined. This latest gaffe demonstrating what many believe is a stunning lack of basi

**Your verdict (anchor / staff / false): ______________**

---

### 17. ratio 0.5758 — CNN-351310 (3 label rows corpus-wide)

* **descriptor**: `CRIME AND JUSTICE PRODUCER`
* **programme**: `CRIME AND JUSTICE WITH ASHLEIGH BANFIELD`
* full speaker label: `KYLE PELTZ, CRIME AND JUSTICE PRODUCER`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after ASHLEIGH BANFIELD, HLN, HOST] Right. We know Shanann`s family as we reported was in Colorado last week moving items removing items from the house. Now we know they were also at the courthouse apparently dealing with the fact that Shanann did not have a will.

> [after ASHLEIGH BANFIELD, HOST, HLN CRIME AND JUSTICE] Right. We know Shanann`s family as we recorded was in Colorado last week, moving items from the house. Now we know they were also at the court house apparently dealing with the fact that Shanann did not have a will.

**Your verdict (anchor / staff / false): ______________**

---

### 18. ratio 0.5641 — CNN-95703 (1 label row corpus-wide)

* **descriptor**: `CNN SENIOR POLITICAL ANALYST`
* **programme**: `INSIDE POLITICS`
* full speaker label: `BILL SCHNEIDER, CNN SENIOR POLITICAL ANALYST (voice-over)`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after HENRY] Here's the problem President Bush is facing in Iraq. When the major fighting ended in April 2003, the president's approval rating on Iraq was 76 percent. Since then, things have generally gone downhill. The insurgency, increasing violence, mounting casualties.

**Your verdict (anchor / staff / false): ______________**

---

### 19. ratio 0.5556 — CNN-104531 (1 label row corpus-wide)

* **descriptor**: `FREELANCE JOURNALIST`
* **programme**: `CNN RELIABLE SOURCES`
* full speaker label: `JILL CARROLL, FREELANCE JOURNALIST`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after (opens the transcript)] I was happy to be free.

**Your verdict (anchor / staff / false): ______________**

---

### 20. ratio 0.5556 — CNN-212218 (1 label row corpus-wide)

* **descriptor**: `CNN NEWS ANCHOR`
* **programme**: `NEW DAY`
* full speaker label: `MICHAELA PEREIRA, CNN NEWS ANCHOR`
* transcript title: (none)

What this speaker actually says (their longest turns, with who spoke immediately before):

> [after CUOMO] We're watching this rain that's in the forecast and it means more flooding will continue for the Midwest and South Eastern U.S. Flash flood warnings have been issued in at least a dozen states. The floods have been deadly. On Thursday, a woman was killed when 

**Your verdict (anchor / staff / false): ______________**

---

## Answer grid

| # | ratio | transcript | descriptor | programme | your verdict |
|---|---|---|---|---|---|
| 1 | 0.9167 | CNN-93766 | `CAPITOL GANG` | `CNN CAPITAL GANG` |  |
| 2 | 0.7143 | CNN-166540 | `PRIEST` | `CNN PRESENTS` |  |
| 3 | 0.7059 | CNN-25421 | `"USA TODAY"` | `Saturday` |  |
| 4 | 0.7059 | CNN-94409 | `HOST "INSIDE POLITICS"` | `JUDY WOODRUFF'S INSIDE POLITICS` |  |
| 5 | 0.7027 | CNN-48649 | `NEWSNIGHT ANCHOR` | `CNN NEWSNIGHT AARON BROWN` |  |
| 6 | 0.6957 | CNN-312942 | `CNN AMANPOUR HOST` | `CNN'S AMANPOUR` |  |
| 7 | 0.6923 | CNN-52391 | `CNN STUDENT BUREAU` | `CNN STUDENT NEWS` |  |
| 8 | 0.6667 | CNN-356090 | `SPECIAL PROSECUTOR` | `CNN SPECIAL REPORTS` |  |
| 9 | 0.6316 | CNN-348399 | `CNN CRIME AND JUSTICE EDITORIAL PRODUCER` | `CRIME AND JUSTICE WITH ASHLEIGH BANFIELD` |  |
| 10 | 0.6286 | CNN-151719 | `" 1997) LARRY KING, HOST` | `CNN LARRY KING LIVE` |  |
| 11 | 0.6269 | CNN-317198 | `PRIMETIME JUSTICE SHOW HOST` | `PRIMETIME JUSTICE WITH ASHLEIGH BANFIELD` |  |
| 12 | 0.6061 | CNN-94672 | `AIR AMERICA RADIO` | `AMERICAN MORNING` |  |
| 13 | 0.6000 | CNN-257253 | `NEWS CORP` | `NEWS STREAM` |  |
| 14 | 0.5938 | CNN-24029 | `AUSTIN BUREAU CHIEF, "THE DALLAS MORNING NEWS"` | `Saturday Morning News` |  |
| 15 | 0.5882 | CNN-212726 | `NEW JERSEY` | `NEW DAY` |  |
| 16 | 0.5789 | CNN-295220 | `CNN THE LEAD HOST` | `THE LEAD WITH JAKE TAPPER` |  |
| 17 | 0.5758 | CNN-351310 | `CRIME AND JUSTICE PRODUCER` | `CRIME AND JUSTICE WITH ASHLEIGH BANFIELD` |  |
| 18 | 0.5641 | CNN-95703 | `CNN SENIOR POLITICAL ANALYST` | `INSIDE POLITICS` |  |
| 19 | 0.5556 | CNN-104531 | `FREELANCE JOURNALIST` | `CNN RELIABLE SOURCES` |  |
| 20 | 0.5556 | CNN-212218 | `CNN NEWS ANCHOR` | `NEW DAY` |  |
