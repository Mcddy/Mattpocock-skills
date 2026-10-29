---
name: discrete-lab
description: Model discrete scheduling and allocation problems, search bounded exact solutions, and independently verify witnesses. Use for resource constraints, dependency schedules, feasibility and counterexamples, rather than forecasts or performance profiling.
---

# Discrete Lab

Turn the actual decision into variables, constraints, units and an objective before choosing an algorithm. Distinguish indivisible tasks from divisible flow, renewable from consumable resources, and half-open time intervals from inclusive dates. A nice diagram is not a feasible solution.

The shipped core solves non-preemptive integer-time, single renewable-resource scheduling with finish-to-start dependencies. Read [the contract](references/contract.md) for supported inputs, independent witness checks and limits. Do not pretend this core covers arbitrary integer programming. For richer models, write and inspect a task-specific adapter, or use an already available solver with its named semantics.

1. Validate the supplied model. Report a cycle with its edges, excessive demand with its task, or unsupported semantics explicitly. Do not silently delete constraints.
2. Run `scripts/solve.py model.json` within a declared search budget. Preserve the input and JSON result. The result distinguishes OPTIMAL, INFEASIBLE and UNRESOLVED, and includes bounds, explored assignments and a witness where available.
3. Independently run `scripts/verify.py model.json result.json`. Verification checks endpoints and dependency edges without calling the search algorithm. A verified witness establishes feasibility, not optimality. On small cases, run `scripts/oracle.py model.json` and compare its exhaustive Cartesian enumeration with the solver. Keep oracle caps visible.
4. For changed requirements or manual schedule edits, verify again and remove stale optimality claims. Explain the binding constraints and next useful relaxation in concrete terms.

Separate mathematical modelling choices, actual search outcomes and user decisions. Preserve integer values without floating conversion. Show a compact task table or purposeful timeline when useful; allow warm/light/dark display preferences without changing the model. Use specific constraint explanations instead of generic optimisation prose. Never claim general impossibility from a capped search.
