---
name: causal-lab
description: Identify intervention effects from an explicit causal DAG, validate adjustment sets and estimate discrete-stratum effects with overlap and cluster uncertainty checks. Use for causal observational analyses and experiment design, not prediction or a causal claim inferred from correlation alone.
---

Use the question's actual intervention, population, outcome horizon and estimand. Ask for a missing causal assumption only when it changes identification. Retain the raw data. A graph is a scientific assumption, not something proved by drawing arrows.

Read [the method contract](references/method.md) before estimating. The executable core validates the declared DAG by d-separation in its backdoor graph and standardises binary-treatment outcome differences over observed discrete strata. It rejects treatment descendants, latent adjustment variables and unsupported target strata. Its `causal_estimate` stays null when the graph fails identification or overlap fails. Descriptive comparisons remain available.

Read [the schema](references/schema.md) to prepare explicit JSON from the supplied data. Run `python scripts/causal.py INPUT.json --out NEW_RESULT.json` after inspecting the script. Existing outputs are not overwritten. A runnable [synthetic example](examples/adjusted.json) demonstrates a confounded contrast and a valid adjustment set. No network or installation is required.

For continuous confounders, time-varying treatment, instrumental variables, difference-in-differences or mediation, choose a justified task-specific implementation with available tooling. State that the bundled estimator did not run those methods. Never bin a continuous confounder silently to make this core accept it. Cluster bootstrap is exploratory and requires supplied cluster identity; it does not turn six participants into a reliable population interval.

Deliver the actual estimand, identification status, source/assumption provenance, supported subgroup contrasts, reproducible input and numeric output. Unsupported causal conclusions are replaced with a descriptive result and the experiment or measurement that would resolve the key ambiguity. Do not pad this with a catalogue of methods. Keep exact quotations and data values intact; use plain language and preserve uncertainty.

If an explorer materially helps, expose the DAG assumptions, chosen controls, support counts and estimand separately from estimates. Prefer a warm readable document with a theme and text-size choice. Recomputing a control set must rerun identification; a cosmetic toggle cannot retain a causal-valid badge.

Discovery controls: use for "did the intervention help, controlling for baseline risk?" or "is this adjustment set valid?". A forecasting request belongs to Model Lab or Series Lab; a study credibility review belongs to Paper Audit. A randomised trial can use this core only when its explicit graph and target-population support meet the contract.

Authorship: Codex, under Shaun's instruction to finish without Claude. Producer regressions in `tests/test_causal.py` are finite checks, not independent acceptance or causal validation.
