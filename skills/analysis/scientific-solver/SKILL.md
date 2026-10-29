---
name: scientific-solver
description: Solve declared numerical dynamics with adaptive error control and analytic checks, or profile parameters of supplied decay observations under a stated noise model. Use for numerical accuracy, calibration and identifiability work; do not imply arbitrary PDE or stiff-system support.
---

# Scientific Solver

Use the executable kernels to produce trajectories and an error/convergence record, or likelihood profiles that expose ambiguity. Simforge may consume these trajectories; an animation alone does not establish numerical accuracy.

Read [methods and schemas](references/methods.md). State equations, units, initial conditions, observation noise and supported regime before running. `scripts/solve.py` accepts decay, logistic, harmonic oscillator and linear relaxation. RK4 step doubling handles the first three; a stable adaptive implicit Euler kernel handles scalar linear relaxation, including large relaxation rates. It does not support general stiff systems, DAEs or PDEs. Report unsupported regimes without pretending an explicit solver became stiff capable.

Run `python scripts/solve.py input.json --out output.json` into a fresh path. Inspect accepted/rejected steps, budget termination, analytic comparison and a tighter-tolerance rerun. Local-error control is not a bound on the global error. Failed integration retains its partial trajectory and says FAILED; never relabel it complete because the plot looks plausible. Units are explicit labels, with coefficients consistent with those labels; the solver does not infer dimensional consistency.

For inverse work, `operation: profile` fits a decay rate, or a product of two rates, using a declared known Gaussian observation sigma. This is a finite-grid likelihood calculation. Report grid resolution, boundary minima, flat profiles and the structurally identifiable parameter combination. A product fit cannot identify its two factors separately. Confidence regions are approximate likelihood-ratio regions under the supplied independent Gaussian noise contract, not uncertainty about whether that contract is true.

Use the worked decay and product examples in `assets/`. Deliver numeric JSON and a labelled scientific plot or concise trajectory/profile table. If an interactive view is requested, expose actual tolerance, parameter and observation changes and mark stale results until recomputed. Avoid ornamental “intelligence” scores.

Should trigger: “Why does my ODE result change when I tighten tolerance?” or “Can these observations distinguish two parameters?” Near miss: a purely combinatorial schedule goes to Discrete Lab. Authorship: Codex continuation; producer evidence requires independent acceptance.
