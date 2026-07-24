# pilot2 comparison: Gemini vs Qwen

Generated 2026-07-24 14:52 UTC

## Runs discovered

| variant | model | dir | records | status |
|---|---|---|---|---|
| v0 | gemini | pilot2_v0_k48_20260724-142949 | 1000 | complete |
| v0 | qwen | pilot2_v0_k48_20260724-165228_leonardo-batch | 1000 | complete |
| v1 | gemini | pilot2_v1_k48_20260724-162018 | ? | in flight (no summary) |
| v1 | qwen | pilot2_v1_k48_20260724-165231_leonardo-batch | 1000 | complete |
| v2 | gemini | - | - | PENDING |
| v2 | qwen | pilot2_v2_k48_20260724-165234_leonardo-batch | 1000 | complete |

## Metrics (lift = twin better)

| variant | model | MAE lift [95% CI] | p(t) | p(Wilcoxon) | within-1 lift [CI] | exact lift | parse fails | exclusions |
|---|---|---|---|---|---|---|---|---|
| v0 | gemini | +0.072 [-0.005, +0.149] | 0.0663 | 0.173 | -0.006 [-0.044, +0.032] | +0.042 [+0.001, +0.083] | 0 | 0 |
| v0 | qwen | -0.088 [-0.205, +0.029] | 0.136 | 0.199 | -0.030 [-0.077, +0.017] | +0.048 [+0.002, +0.094] | 0 | 0 |
| v1 | gemini | PENDING | - | - | - | - | - | - |
| v1 | qwen | -0.118 [-0.237, +0.001] | 0.0519 | 0.0865 | -0.030 [-0.079, +0.019] | +0.016 [-0.020, +0.052] | 0 | 0 |
| v2 | gemini | PENDING | - | - | - | - | - | - |
| v2 | qwen | +0.003 [-0.049, +0.055] | 0.899 | 0.904 | -0.008 [-0.044, +0.028] | +0.020 [-0.011, +0.051] | 0 | 0 |

## v0 detail

### gemini — predicted vs true histogram

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 30 | 58 | 44 | 100 | 78 | 172 | 18 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 6 | 95 | 43 | 56 | 118 | 181 | 1 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### qwen — predicted vs true histogram

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 42 | 99 | 105 | 76 | 44 | 110 | 24 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 0 | 57 | 84 | 140 | 71 | 148 | 0 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### v0 per-item MAE lift (gemini | qwen)

| item | gemini MAE lift | qwen MAE lift |
|---|---|---|
| TIPI1 | +0.180 | +0.220 |
| TIPI10 | +0.340 | +0.040 |
| TIPI2 | +0.200 | -0.160 |
| TIPI3 | +0.140 | +0.140 |
| TIPI4 | +0.000 | -0.220 |
| TIPI5 | -0.080 | -0.240 |
| TIPI6 | -0.060 | -0.520 |
| TIPI7 | +0.080 | +0.060 |
| TIPI8 | +0.060 | -0.220 |
| TIPI9 | -0.140 | +0.020 |

## v1 detail

### gemini: PENDING

### qwen — predicted vs true histogram

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 90 | 162 | 20 | 13 | 67 | 119 | 29 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 50 | 130 | 30 | 27 | 77 | 150 | 36 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### v1 per-item MAE lift (gemini | qwen)

| item | gemini MAE lift | qwen MAE lift |
|---|---|---|
| TIPI1 | - | +0.200 |
| TIPI10 | - | +0.020 |
| TIPI2 | - | -0.340 |
| TIPI3 | - | +0.240 |
| TIPI4 | - | -0.440 |
| TIPI5 | - | -0.240 |
| TIPI6 | - | -0.560 |
| TIPI7 | - | -0.060 |
| TIPI8 | - | -0.020 |
| TIPI9 | - | +0.020 |

## v2 detail

### gemini: PENDING

### qwen — predicted vs true histogram

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 43 | 0 | 125 | 135 | 67 | 118 | 12 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 6 | 1 | 156 | 102 | 37 | 178 | 20 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### v2 per-item MAE lift (gemini | qwen)

| item | gemini MAE lift | qwen MAE lift |
|---|---|---|
| TIPI1 | - | +0.206 |
| TIPI10 | - | +0.126 |
| TIPI2 | - | +0.019 |
| TIPI3 | - | +0.017 |
| TIPI4 | - | -0.194 |
| TIPI5 | - | -0.135 |
| TIPI6 | - | -0.001 |
| TIPI7 | - | +0.053 |
| TIPI8 | - | -0.035 |
| TIPI9 | - | -0.021 |
