---
name: heirloom-rank-product-experiments
description: "Rank product experiments by the decision each result could change, evidence quality, cost, reversibility and reusable capability. Use when several software ideas compete for scarce engineering time; measured delivery profitability and longer-horizon option allocation are separate decisions."
---

# Rank tests, not attractive product names

Obtain candidate ideas, evidence already collected, current decision, weekly time/cash limits, reusable assets and any nonnegotiable learning goals. Separate a product concept from an experiment. If a candidate has no falsifiable uncertainty, rewrite it as a question with an observable result before ranking. User interest is a legitimate motivation but not demand evidence.

For each candidate identify the load-bearing assumption, current evidence, cheapest discriminating test, result thresholds, next action and dependencies. Use a decision table: if result A, do X; if result B, do Y. If both outcomes lead to building the same thing, the proposed test has little immediate decision value. Avoid speculative numerical expected values unless probabilities and payoffs have defensible inputs; ordinal judgements with rationale are often more honest.

Estimate effort as setup, execution and interpretation, including data access and integration work. Price cash separately from time. Record estimates with ranges and confidence rather than fake precision. An experiment requiring a paid service should include a no-spend rehearsal or stop before the purchase unless separately authorised. Include switching cost and recovery if the experiment fails.

Assess evidence discrimination, downside, time to result and reusable capability. Reuse needs a concrete asset such as a parser contract, simulator fixture or measured router, not the phrase builds skills. Prefer tests that expose a decisive failure cheaply. A broad build may be justified for intrinsic learning, but label that objective rather than describing it as validated commercial opportunity.

If evidence and effort are uncertain, select a short measurement spike or eliminate dominated candidates. If a candidate already has sufficient evidence for the next authorised step, do not repeat research merely to create a ranking exercise. Respect the weekly capacity actually supplied (a 10 to 20 hour week is only an illustration) by choosing one primary experiment and at most one small fallback; parallel ideas are not free capacity.

Deliver `experiment_rankings.csv` and `next_experiment.md`. Columns include assumption, existing evidence, test, decision branches, time/cash range, access gap, reuse asset, rationale, rank and stop rule. The selected brief includes inputs, first runnable proof, positive and negative controls, acceptance and the smallest useful output. Keep commercial promise distinct from engineering value.

Acceptance compares two candidates where the flashier one cannot change a decision but a smaller test can. A negative control with missing access must not be ranked as immediately executable. Passing yields an explicit prioritisation under stated preferences; it does not predict revenue or ensure product success.

Worked situation: a local routing replay costs one evening and can reveal whether a cheaper model is adequate. A marketplace application needs weeks and unknown customers. The replay may rank first because it changes a current engineering choice and leaves a reusable benchmark.
