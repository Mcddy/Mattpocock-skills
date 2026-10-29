# Numerical and inverse contract

All inputs are JSON `schema: 1`. Maximum input 2 MiB. Numbers must be finite, never booleans. Output paths are exclusive. No imported expressions/code, network or dependency installs.

## Integrate

`operation: integrate`, `model`, `parameters`, `initial`, `t_span: [t0,t1]`, `time_unit`, `state_units`, `rtol`, `atol`, optional `initial_step`, `max_steps` (1..100000, default 20000). Positive span; 1 or 2 states, matching labels. rtol in [1e-12,0.1], atol positive. At most 100001 trajectory rows.

- `decay`: y'=-rate*y, rate >=0; analytic y0 exp(-rate*(t-t0)).
- `logistic`: y'=rate*y*(1-y/capacity), rate >=0, capacity >0, y0 >0; analytic solution.
- `oscillator`: x'=v, v'=-omega²*x, omega>0. Analytical x/v and conserved energy diagnostic; units for velocity must be chosen appropriately by the user.
- `relaxation`: y'=-rate*(y-target), rate>=0. Implicit Euler full step and two half steps. Stable for positive scalar rate, but first-order and potentially expensive for tight accuracy near transients. Analytic control supplies a global discrepancy observation.

For RK4, fine/coarse step difference /15 estimates the fine local error. For implicit Euler it is the raw difference. Accept when each component's error divided by `atol+rtol*max(abs(old),abs(fine))` is <=1. Adjust step by a bounded safety factor using orders 5 and 2 respectively. The returned state is the two-half-step state. This conservative choice retains stability; it is not Richardson-extrapolated. Each attempted step counts toward the budget. Non-finite states, no floating-point time progress and budget exhaustion return FAILED with reason and partial data. The input endpoint is reached exactly by shortening the final step. RK4 is explicit and not claimed stable for stiff dynamics.

Output includes method, inputs, complete/failed, attempts/accepted/rejected, trajectory, maximum *observed* analytic absolute error and relative oscillator energy drift where applicable. Refine tolerance independently; do not equate the local error estimate with analytic global accuracy.

## Profile

`operation: profile`, `model: decay|product-decay`, `amplitude`, `sigma` >0 (known independent Gaussian measurement SD in observation units), `time_unit`, `observation_unit`, `observations: [{t,y},...]` (2..10000), `a_grid: [lo,hi,count]` with nonnegative increasing bounds, count 3..501. Product model also needs `b_grid`; maximum grid-cell count times observations <=2,000,000. Negative observation times rejected.

Prediction = amplitude exp(-a*t), or amplitude exp(-a*b*t). Score is sum(((prediction-y)/sigma)^2); additive likelihood constants are irrelevant. The profile for a minimises score over the b grid. Approximate 95% one-parameter LR support uses score-minimum <=3.841459; report actual accepted grid values and interval hull. Disconnected support is retained as values, not asserted continuous. A minimum on the edge requires extending bounds before an interior estimate. Coarse finite grids can miss minima and make a structural ridge look uneven. Product-decay always reports `only a*b structurally identifiable`; do not assert uniqueness from a grid-selected pair. This is not arbitrary model calibration, estimated-noise profiling, correlated-noise likelihood or Bayesian posterior inference.
