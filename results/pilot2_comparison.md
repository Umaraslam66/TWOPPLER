# pilot2 comparison across models

Generated 2026-07-24 15:02 UTC

## Runs discovered

| model | variant | dir | records | status |
|---|---|---|---|---|
| gemini | v0 | pilot2_v0_k48_20260724-142949 | 1000 | complete |
| gemini | v1 | pilot2_v1_k48_20260724-162018 | ? | in flight (no summary) |
| gemini | v2 | - | - | PENDING |
| leonardo-qwen3.6-27b | v0 | pilot2_v0_k48_20260724-165228_leonardo-batch | 1000 | complete |
| leonardo-qwen3.6-27b | v1 | pilot2_v1_k48_20260724-165231_leonardo-batch | 1000 | complete |
| leonardo-qwen3.6-27b | v2 | pilot2_v2_k48_20260724-165234_leonardo-batch | 1000 | complete |

## Metrics (lift = twin better)

| model | variant | MAE lift [95% CI] | p(t) | p(Wilcoxon) | within-1 lift [CI] | exact lift | parse fails | exclusions |
|---|---|---|---|---|---|---|---|---|
| gemini | v0 | +0.072 [-0.005, +0.149] | 0.0663 | 0.173 | -0.006 [-0.044, +0.032] | +0.042 [+0.001, +0.083] | 0 | 0 |
| gemini | v1 | PENDING | - | - | - | - | - | - |
| gemini | v2 | PENDING | - | - | - | - | - | - |
| leonardo-qwen3.6-27b | v0 | -0.088 [-0.205, +0.029] | 0.136 | 0.199 | -0.030 [-0.077, +0.017] | +0.048 [+0.002, +0.094] | 0 | 0 |
| leonardo-qwen3.6-27b | v1 | -0.118 [-0.237, +0.001] | 0.0519 | 0.0865 | -0.030 [-0.079, +0.019] | +0.016 [-0.020, +0.052] | 0 | 0 |
| leonardo-qwen3.6-27b | v2 | +0.003 [-0.049, +0.055] | 0.899 | 0.904 | -0.008 [-0.044, +0.028] | +0.020 [-0.011, +0.051] | 0 | 0 |

## Predicted-vs-true histograms

### gemini v0

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 30 | 58 | 44 | 100 | 78 | 172 | 18 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 6 | 95 | 43 | 56 | 118 | 181 | 1 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### leonardo-qwen3.6-27b v0

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 42 | 99 | 105 | 76 | 44 | 110 | 24 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 0 | 57 | 84 | 140 | 71 | 148 | 0 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### leonardo-qwen3.6-27b v1

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 90 | 162 | 20 | 13 | 67 | 119 | 29 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 50 | 130 | 30 | 27 | 77 | 150 | 36 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

### leonardo-qwen3.6-27b v2

| arm/series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| twin predicted | 43 | 0 | 125 | 135 | 67 | 118 | 12 |
| twin true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |
| baseline predicted | 6 | 1 | 156 | 102 | 37 | 178 | 20 |
| baseline true | 57 | 51 | 53 | 55 | 109 | 101 | 74 |

## Per-item MAE lift (wide)

| item | gemini v0 | leonardo-qwen3.6-27b v0 | leonardo-qwen3.6-27b v1 | leonardo-qwen3.6-27b v2 |
|---|---|---|---|---|
| TIPI1 | +0.180 | +0.220 | +0.200 | +0.206 |
| TIPI2 | +0.200 | -0.160 | -0.340 | +0.019 |
| TIPI3 | +0.140 | +0.140 | +0.240 | +0.017 |
| TIPI4 | +0.000 | -0.220 | -0.440 | -0.194 |
| TIPI5 | -0.080 | -0.240 | -0.240 | -0.135 |
| TIPI6 | -0.060 | -0.520 | -0.560 | -0.001 |
| TIPI7 | +0.080 | +0.060 | -0.060 | +0.053 |
| TIPI8 | +0.060 | -0.220 | -0.020 | -0.035 |
| TIPI9 | -0.140 | +0.020 | +0.020 | -0.021 |
| TIPI10 | +0.340 | +0.040 | +0.020 | +0.126 |
