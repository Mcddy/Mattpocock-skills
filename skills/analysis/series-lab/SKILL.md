---
name: series-lab
description: Backtest univariate time series with availability-aware rolling origins, naive/seasonal/drift baselines, prequential residual intervals and leakage checks. Use for bounded temporal forecasts, delayed observations and honest error comparisons, not causal explanations or forecasts from unseen future labels.
---

Define the value/unit, regular time grid, forecast origin, horizon and actual observation release time. Distinguish zero, missing and not-yet-available values. Retain original timestamps and timezone. The fact that a value appears in an historical file does not mean it was knowable at an earlier origin.

Read [method](references/method.md) and [schema](references/schema.md). Inspect `scripts/series.py`, then run `python scripts/series.py INPUT.json --out NEW_RESULT.json`. The standard-library core forecasts naive, seasonal-naive and drift baselines at explicit rolling origins, refuses look-ahead training candidates, flags auxiliary values released after their origin and scores only labels available by the evaluation cutoff. Features flagged for leakage are never incorporated into these univariate models.

The [seasonal example](examples/seasonal.json) keeps real zeros, a delayed observation and withheld future targets. It reports metrics with actual denominators. No MAPE is used. MASE is suppressed when its first-origin seasonal-difference denominator is absent or tiny. Intervals use only completed same-horizon prior residuals; limited evidence means an unestimated interval, not a fabricated confidence band. Warm visualisations must label observed, released-late, missing and forecast points distinctly.

Select a final method using completed backtest labels available at the final deployment origin; freeze that choice before future targets arrive. Return the final unscored forecasts separately from retrospective backtest metrics. Retrospective median-shift candidates are exploratory prompts, not validated changepoints or intervention effects. Do not describe the baselines as a comprehensive forecasting platform.

Deliver input hash, explicit origins/horizons, each baseline's forecasts, availability violations, actual error/coverage counts and method limits. If an explorer helps, use a legible warm time plot with origin/horizon selection and text-size/theme controls. Changes to the evaluation cutoff must update score counts; missing points cannot become zeros to draw a smoother line. Export the underlying numeric series, not just a screenshot. Preserve exact numbers and avoid generic AI prose or unsupported performance claims.

Discovery: rolling forecasts, time-based model comparison or revision/release leakage activates this skill. General tabular classification belongs to Model Lab; causal intervention attribution belongs to Causal Lab. A static line chart does not require fitting forecasts.

Authorship: Codex after Shaun authorised finishing without Claude. `tests/test_series.py` uses synthetic finite oracles; no population coverage or real-world predictive performance is established.
