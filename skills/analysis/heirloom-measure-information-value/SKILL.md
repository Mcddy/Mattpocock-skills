---
name: heirloom-measure-information-value
description: "Estimate the decision value of obtaining one more observation and choose a bounded experiment. Use when uncertainty blocks an option choice; distinguish information value from a broad research plan or invented revenue forecasts."
---
# Measure Information Value

Require the decision options, uncertain states, consequences of each choice, current evidence and experiment candidates. Use supplied numerical beliefs/losses only when their basis is explicit. Otherwise work with ordinal regret and sensitivity ranges. Mark value estimates ASSESSMENT with confidence, not observed benefit.

## Connect information to action

1. Write the action chosen now and the assumption that could reverse it. Reject experiments whose plausible outcomes leave every consequential action unchanged, unless explicitly marked learning-only.
2. Define observable experiment results and how they update each uncertain state. Separate the likelihood of an observation from the belief about the underlying state. If those probabilities are unknown, use scenarios and break-even bounds instead of a fabricated Bayesian calculation.
3. When defensible inputs exist, compare current minimum expected loss with expected minimum loss after each possible observation. Subtract experiment time/cash/opportunity cost. Keep units and currencies consistent; verify changing prices only from current official sources when executing.
4. Test sensitivity across plausible belief/loss ranges. Prefer an experiment whose recommendation survives reasonable assumptions. A fragile ranking is a gap requiring cheaper evidence, not a precise optimum.
5. Give every card a measurement, time ceiling, cash ceiling, stop rule and pass/fail/inconclusive decision update. Default to a zero-spend local proof. Fit the first card and the total queue to the task's actual effort ceiling. A 60 to 120 minute first block is a default for when no ceiling is given; a smaller experiment is not stretched to fill it.
6. Branch by result: retain actual observations and revise the belief/decision; for inconclusive results permit at most a stated correction budget. Distinguish realised learning from the estimated pre-experiment value. A null result can be valuable when it kills an expensive path.

## Deliver

Write `information-value.md` and `experiment-card.json`. Include decision_id, options, current_action, uncertain_states, belief_basis, consequence_units, outcome_model, estimated_value_or_range, sensitivity, experiment_cost, stop_rule and result_to_action mapping. List attractive rejected experiments and why their information would not change the decision.

## Acceptance and worked situation

Require one observation that changes the chosen action and a negative control that merely confirms an irrelevant detail. Show an outcome that falsifies the preferred idea. If numerical inputs are absent, the output must remain qualitative and explicit about unknowns. Passing yields a defensible next experiment, not proof of profit or a statistically powered study.

Situation: a hardware purchase depends on whether ledger queries exceed a tolerable latency. A local workload timing can reverse the purchase decision. Researching cosmetic dashboard themes cannot. Run the bounded timing test first and retain actual measurements before modelling an upgrade's value.
