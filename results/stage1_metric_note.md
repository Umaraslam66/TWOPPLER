# Stage 1 metric change — MAE lift becomes the primary metric

Date: 2026-07-24

## What changed

- **Primary metric is now MAE lift** = baseline mean-absolute-error minus twin
  mean-absolute-error, per person (positive = twin is closer to the truth).
  Reported with a 95% confidence interval, a paired t-test, and a Wilcoxon
  signed-rank test across persons — the same machinery as before.
- **Within-1 lift is the secondary metric** (twin minus baseline rate of
  landing within one point of the true answer).
- **Exact-match lift is still computed and reported, but demoted to last.**
- **New diagnostic: Spearman correlation** between a person's predictions and
  their true answers, per arm, averaged across persons. When a person's
  predictions are all identical the correlation is undefined; those are
  recorded as null and excluded from the average, and the count of nulls is
  reported.
- Two new descriptive additions to each run summary: a predicted-vs-true answer
  histogram per arm, and a per-item table (TIPI1–10) of twin MAE, baseline MAE,
  MAE lift, and within-1 lift.

## Why

Exact match on a 7-point scale is noise-dominated: getting the exact integer
right is mostly luck, so it throws away almost all of the ordinal signal. The
20-person pilot showed this plainly — twin exact accuracy 20.5% vs baseline
19.5% (lift +1.0 point, p = 0.68), and within-1 was flat at 59% for both arms.
A metric that only rewards the exact integer cannot see a twin that is
consistently *closer* without being exactly right.

MAE uses the full ordinal scale: a prediction of 5 when the truth is 6 is
counted as better than a prediction of 2, which exact match cannot express. So
MAE is far more sensitive to whether grounding actually moves predictions toward
the person, which is the thing Stage 1 is meant to detect and tune.

## Standing with the pre-registration

This is a Stage 1 **tuning decision**, made during development and **before any
gate data was collected or scored**. The pre-registration designates Stage 1 as
development-only, explicitly for debugging the pipeline and tuning
hyperparameters, with no confirmatory claims. Choosing the metric that best
detects lift on the development set is exactly that kind of tuning.

The frozen go/no-go bar itself is **unchanged**: grounded-twin lift over the
demographics-only baseline must be **positive and significant** on RIASEC
cross-domain prediction (n ≥ 500 held-out persons). That bar is now evaluated on
**MAE lift** instead of exact-match lift. Everything else about the gate —
cross-domain only, lift over the zero-information baseline as the quantity of
interest, n ≥ 500 — stays as pre-registered.
