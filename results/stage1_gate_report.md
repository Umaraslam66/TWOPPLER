# Stage 1 gate report

Generated 2026-07-24 16:23 UTC

## 1. Primary verdict

- Run dir: `gate_v2_k48_20260724-181226`
- MAE lift: 0.0850 [0.0689, 0.1012]
- paired t: t=10.3541, p=6.87e-23
- Wilcoxon: W=32046.0000, p=3.07e-21
- within-1 lift: 0.0474 [0.0350, 0.0598]
- exact lift: 0.0292 [0.0162, 0.0422]
- persons scored: 500; parse failures: 0; exclusions: 0

Bar (verbatim, stage1_gate_note.md): The gate passes iff the PRIMARY arm shows twin lift over the demographics-only baseline that is positive and significant (MAE lift > 0; paired t-test p < .05 across the 500 persons; Wilcoxon reported alongside).

GATE: PASS  (rule: MAE lift > 0 AND paired-t p < 0.05)

## 2. Secondary verdict and promotion decision

- Run dir: `gate_v2_k48_20260724-182324_leonardo-batch`
- MAE lift: 0.0954 [0.0750, 0.1159]
- paired t: t=9.1686, p=1.25e-18
- Wilcoxon: W=36509.0000, p=6.5e-16
- within-1 lift: 0.0477 [0.0336, 0.0617]
- exact lift: 0.0651 [0.0511, 0.0792]
- persons scored: 500; parse failures: 5; exclusions: 5

Pre-commitment (verbatim, stage1_gate_note.md):

> - If the secondary (Gemma-4 + v2) shows positive AND significant MAE lift
>   (same test, p < .05) at n=500: Gemma-4-31B-it + v2 becomes the primary
>   simulation model for all later stages (speed + cost), with Gemini demoted
>   to robustness checks.
> - If not: Gemini stays primary and the open-model failure to use
>   individuating information is a documented Stage 1 finding.
> - The gate pass/fail verdict itself depends ONLY on the primary arm.

PROMOTED: Gemma-4+v2 primary for future stages  (rule: secondary MAE lift > 0 AND paired-t p < 0.05)

## 3. Per-item MAE (primary | secondary)

| item | pri twin MAE | pri base MAE | pri MAE lift | sec twin MAE | sec base MAE | sec MAE lift |
|---|---|---|---|---|---|---|
| TIPI1 | 1.6008 | 1.8665 | 0.2657 | 1.4828 | 1.7696 | 0.2868 |
| TIPI2 | 1.7926 | 1.7198 | -0.0728 | 1.8375 | 1.8566 | 0.0191 |
| TIPI3 | 1.1648 | 1.2455 | 0.0806 | 1.1399 | 1.2194 | 0.0795 |
| TIPI4 | 1.6200 | 1.6240 | 0.0041 | 1.6113 | 1.6071 | -0.0042 |
| TIPI5 | 1.2966 | 1.5497 | 0.2531 | 1.0781 | 1.2351 | 0.1570 |
| TIPI6 | 1.8545 | 1.8594 | 0.0049 | 1.7265 | 1.8058 | 0.0793 |
| TIPI7 | 1.0112 | 1.0922 | 0.0810 | 0.9825 | 1.1878 | 0.2053 |
| TIPI8 | 1.5270 | 1.5833 | 0.0563 | 1.6910 | 1.5712 | -0.1198 |
| TIPI9 | 1.5412 | 1.6684 | 0.1272 | 1.4413 | 1.5123 | 0.0710 |
| TIPI10 | 1.4759 | 1.5259 | 0.0500 | 1.3487 | 1.5274 | 0.1787 |

## 4. Predicted (argmax) vs true histograms

### primary twin

| series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 262 | 789 | 761 | 1069 | 949 | 971 | 199 |
| twin true | 560 | 518 | 482 | 512 | 962 | 1073 | 893 |

### primary baseline

| series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| baseline predicted | 248 | 552 | 862 | 1667 | 852 | 762 | 57 |
| baseline true | 560 | 518 | 482 | 512 | 962 | 1073 | 893 |

### secondary twin

| series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 800 | 227 | 538 | 821 | 869 | 1504 | 236 |
| twin true | 560 | 518 | 482 | 512 | 961 | 1072 | 890 |

### secondary baseline

| series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| baseline predicted | 271 | 518 | 760 | 1284 | 1268 | 886 | 8 |
| baseline true | 560 | 518 | 482 | 512 | 961 | 1072 | 890 |

## 5. Calibration diagnostic (EXPLORATORY)

_Exploratory; from the primary arm's v2 twin records. matplotlib is not a dependency, so this is an ASCII reliability table only (no PNG)._

- records: 5000; option-pairs: 35000
- ECE (weighted |conf - freq|): 0.0453
- mean stated prob of the true answer: 0.1884 vs uniform 1/7 = 0.1429

| bin | n | mean stated prob | empirical freq true |
|---|---|---|---|
| [0.0, 0.1) | 12795 | 0.0372 | 0.0781 |
| [0.1, 0.2) | 10445 | 0.1252 | 0.1504 |
| [0.2, 0.3) | 7397 | 0.2310 | 0.1820 |
| [0.3, 0.4) | 3805 | 0.3317 | 0.2255 |
| [0.4, 0.5) | 467 | 0.4103 | 0.3726 |
| [0.5, 0.6) | 53 | 0.5057 | 0.6226 |
| [0.6, 0.7) | 21 | 0.6071 | 0.5238 |
| [0.7, 0.8) | 8 | 0.7000 | 0.7500 |
| [0.8, 0.9) | 1 | 0.8000 | 1.0000 |
| [0.9, 1.0) | 8 | 0.9515 | 0.1250 |

## 6. Cost ledger

Gate-run cost lines:

| run_id | backend | n_calls | cost_usd | node_hours |
|---|---|---|---|---|
| gate_v2_k48_20260724-181226 | gemini | 10001 | 2.842664 | None |
| gate_v2_k48_20260724-182324_leonardo-batch | leonardo-batch | 0 | None | 0.16 |

Project totals to date (all cost_log lines):
- total Gemini calls: 12001
- total $ (sum cost_usd): 3.2710
- total node-hours: 0.7441
