# Detectability sheet — KEY (Amendment 2 B10.8)

Seed 53. 10 real entries, 10 controls.

A **real** entry has one paraphrased true answer among three generated distractors. A **control** entry is four generated answers with no real answer present; the correct response to a control is `none`.

Chance on a real entry, if the owner always names a letter, is 0.25. The control entries measure the false-positive rate: naming any letter on a control is a false positive.

## Note on the repeated questions

5 questions appear TWICE, once as a real entry and once as a control: #1/#20 (`C00792:NPR-19884:10`), #3/#4 (`C00792:NPR-19884:6`), #5/#17 (`C00792:NPR-19884:13`), #8/#15 (`C02006:NPR-14829:19`), #10/#16 (`C00792:NPR-19884:15`). This is unavoidable at 15 built items — B10.8 asks for 20 entries and 20 disjoint items do not exist.

**Those 5 control entries share the QUESTION and NOTHING ELSE.** Their four options come from a second generation pass: fresh counterfactuals against the same paraphrased true answer, through the same guards, the same paraphrase step and the same contradiction check, then checked against the real entry's own options so no text is reused. Comparing a pair therefore tells you nothing — there is no option present in one and absent from the other to eliminate on. All 10 real entries count.

For the record, the earlier draft of this sheet built a control from the real item's own three distractors plus its spare, which left three of four options identical across the pair and let the real answer fall out **by elimination**. That is fixed; this note stays so the fix is auditable.

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
