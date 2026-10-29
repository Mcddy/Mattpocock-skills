---
name: model-lab
description: Fit and export numeric tabular regression or binary classifiers with train-only preprocessing, group/time boundaries, development baseline comparisons and a sealed single-audit holdout lifecycle. Use for reproducible predictive models and inference contracts, not causal effects, LLM evaluation or unrestricted AutoML.
---

Define what is predicted, at what moment, for which entity and decision. Review candidate features against the actual prediction-time evidence; target availability declarations do not detect semantic leakage. Exclude identifiers and target-bearing/post-outcome information before fitting. Respect Shaun's runtime/resource budget and existing data boundaries.

Read [method/lifecycle](references/method.md) and [schema](references/schema.md). The bundled standard-library engine offers a constant baseline, ridge regression and regularised binary logistic regression. Medians, scaling and coefficients fit on training data only. Penalty choice uses development loss. Group/time boundaries and immutable test-byte commitment are explicit. Binary probability calibration and advanced text/LLM models are not supplied.

Inspect `scripts/model.py`; use `seal-test TEST.json SEAL.json` before fit, then `fit CONTRACT.json TRAIN.json DEV.json SEAL.json MODEL.json`. Run `predict MODEL.json ROWS.json PREDICTIONS.json` for inference and `audit-test MODEL.json TEST.json SEAL.json LEDGER.json` once for final audit. All outputs are new files. Audit creates a persistent exclusive lock beside the seal before parsing labels; a failed audit remains recorded by that lock and requires an explicitly documented new experiment to rerun. This guards this workflow, not users opening the data elsewhere.

The [example data](examples/) forms an executable chronological group split. Compare the actual development baseline and selected model, preserve raw split IDs/time bounds and report convergence diagnostics. No paid services or installation are required. If the numerical core is inadequate, use a reviewed available adapter and state which paths ran. Do not train an ambitious neural model because the skill is named Model Lab.

Export the saved preprocessing, exact feature order, inference contract, model checksum, split/data commitments, actual losses and error slices. Test reloaded predictions and malformed input. Thresholds are fixed at 0.5 in this binary core; task-specific costs or threshold selection must be frozen on development data before test opening. Test outcomes cannot be relabelled as development evidence to tune a better score.

If an error explorer helps, let the user inspect concrete failed rows, feature values and group/time slices in a readable warm table. Show which dataset selected a parameter and which dataset audited it. Theme/text-size preferences are cosmetic; selection changes invalidate the old audit. Avoid decorative architecture or unsupported performance claims. Preserve exact values and use concise natural prose.

Discovery: a fitted numeric predictor or exported classifier activates this skill. Forecast horizons require Series Lab; an intervention question requires Causal Lab. A paper review or generic AI advice does not need this engine.

Authorship: Codex after Shaun authorised finishing without Claude. `tests/test_model.py` exercises synthetic finite cases; independent host routing/model behaviour is separate.
