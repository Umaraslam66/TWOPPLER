# pilot2 comparison: Gemini vs Qwen

Generated 2026-07-24 14:30 UTC

## Runs discovered

| variant | model | dir | records | status |
|---|---|---|---|---|
| v0 | gemini | pilot2_v0_k48_20260724-142949 | 1000 | complete |
| v0 | qwen | - | - | PENDING |
| v1 | gemini | pilot2_v1_k48_20260724-162018 | ? | in flight (no summary) |
| v1 | qwen | - | - | PENDING |
| v2 | gemini | - | - | PENDING |
| v2 | qwen | - | - | PENDING |

## Metrics (lift = twin better)

| variant | model | MAE lift [95% CI] | p(t) | p(Wilcoxon) | within-1 lift [CI] | exact lift | parse fails | exclusions |
|---|---|---|---|---|---|---|---|---|
| v0 | gemini | +0.072 [-0.005, +0.149] | 0.0663 | 0.173 | -0.006 [-0.044, +0.032] | +0.042 [+0.001, +0.083] | 0 | 0 |
| v0 | qwen | PENDING | - | - | - | - | - | - |
| v1 | gemini | PENDING | - | - | - | - | - | - |
| v1 | qwen | PENDING | - | - | - | - | - | - |
| v2 | gemini | PENDING | - | - | - | - | - | - |
| v2 | qwen | PENDING | - | - | - | - | - | - |

## v0 detail

### gemini — predicted vs true histogram

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 30 | 58 | 44 | 100 | 78 | 172 | 18 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 6 | 95 | 43 | 56 | 118 | 181 | 1 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### qwen: PENDING

### v0 per-item MAE lift (gemini | qwen)

| item | gemini MAE lift | qwen MAE lift |
|---|---|---|
| TIPI1 | +0.180 | - |
| TIPI10 | +0.340 | - |
| TIPI2 | +0.200 | - |
| TIPI3 | +0.140 | - |
| TIPI4 | +0.000 | - |
| TIPI5 | -0.080 | - |
| TIPI6 | -0.060 | - |
| TIPI7 | +0.080 | - |
| TIPI8 | +0.060 | - |
| TIPI9 | -0.140 | - |

## v1 detail

### gemini: PENDING

### qwen: PENDING

_No runs available for this variant yet._

## v2 detail

### gemini: PENDING

### qwen: PENDING

_No runs available for this variant yet._
