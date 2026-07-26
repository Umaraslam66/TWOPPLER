# Detectability sheet — KEY (Amendment 2 B10.8)

Seed 53. 10 real entries, 10 controls.

A **real** entry has one paraphrased true answer among three generated distractors. A **control** entry is four generated answers with no real answer present; the correct response to a control is `none`.

Chance on a real entry, if the owner always names a letter, is 0.25. The control entries measure the false-positive rate: naming any letter on a control is a false positive.

## READ THIS BEFORE SCORING — the overlapping entries leak

5 items appear TWICE, once as a real entry and once as a control: #1/#20 (`C00792:NPR-19884:10`), #3/#4 (`C00792:NPR-19884:6`), #5/#17 (`C00792:NPR-19884:13`), #8/#15 (`C02006:NPR-14829:19`), #10/#16 (`C00792:NPR-19884:15`).

The overlap is forced by supply, not chosen: B10.8 asks for 10 real and 10 control entries and only 15 items were built, so 20 disjoint entries do not exist.

**Why it matters.** A control reuses the same item's three distractors plus its unused spare, so an overlapping pair shows the SAME question with THREE of the four options identical. The option that appears in the real entry and not in its control twin IS the real answer. Anyone who compares the two entries can score those items **by elimination**, without judging realism at all.

**Therefore:** the uncontaminated hit rate is the one computed over the 5 real entries with no control twin — #9, #11, #12, #13, #19 — and that is the number to quote. Report the all-10 rate beside it, flagged. Whether to rebuild the sheet with disjoint items (fewer entries, or a second generation pass for control-only option sets) is a design decision for the owner, not the implementer's.

| # | kind | item_id | real answer |
|---|---|---|---|
| 1 | real | `C00792:NPR-19884:10` | **A** |
| 2 | control | `C00792:NPR-19884:2` | **none** |
| 3 | real | `C00792:NPR-19884:6` | **B** |
| 4 | control | `C00792:NPR-19884:6` | **none** |
| 5 | real | `C00792:NPR-19884:13` | **C** |
| 6 | control | `C02124:NPR-12184:4` | **none** |
| 7 | control | `C02006:NPR-14829:29` | **none** |
| 8 | real | `C02006:NPR-14829:19` | **C** |
| 9 | real | `C02013:NPR-9480:70` | **D** |
| 10 | real | `C00792:NPR-19884:15` | **C** |
| 11 | real | `C01677:NPR-8791:77` | **C** |
| 12 | real | `C02013:NPR-9480:82` | **B** |
| 13 | real | `C02013:NPR-9480:49` | **B** |
| 14 | control | `C02006:NPR-14829:26` | **none** |
| 15 | control | `C02006:NPR-14829:19` | **none** |
| 16 | control | `C00792:NPR-19884:15` | **none** |
| 17 | control | `C00792:NPR-19884:13` | **none** |
| 18 | control | `C02013:NPR-9480:45` | **none** |
| 19 | real | `C02124:NPR-12184:6` | **C** |
| 20 | control | `C00792:NPR-19884:10` | **none** |
