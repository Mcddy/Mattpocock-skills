---
name: "simforge"
description: "Builds a self-contained interactive simulation of a system with moving parts (physics, orbits, ecology, epidemics, markets, algorithms, agent models): a calibrated numerical engine, live parameters, invariant readouts and named regime thresholds. Use when asked to simulate something, visualise its dynamics, or let the user tweak parameters and watch the result. Not for certifying numerical accuracy (scientific-solver) or a ballpark figure (fermi)."
---

# Simforge: interactive simulation engine

Builds living models. Someone should be able to grab a parameter, drag it, and watch the system respond the way the real system would. The payoff is honest, calibrated dynamics: dramatic because the physics is real, not because the maths was fudged. A fudged simulation that looks impressive is a failure; a stark one that is correct is a win.

## Use when

- The user says: simulate, build a visualiser for, model the dynamics of, interactive simulator, show me what happens when, let me tweak the parameters of.
- The request is an N-body, orbital, population, market, epidemic, cellular automaton or flow simulation, or any abstract system worth making tangible.
- A concept has behaviour worth exploring, so a live model beats a static explanation.

## Not this skill

| The job | Use |
|---|---|
| Certify numerical accuracy, convergence or parameter identifiability | scientific-solver |
| A rough number with ranges | fermi |
| Derive a scaling law or design a test | first-principles |
| Treat a simulation result as a research finding | research-agency |

## Posture

Ship a strong first version from the spec. Ask one or two questions only if the request is genuinely ambiguous (which regime, what to hold fixed). Otherwise build.

## Phase 1: spec (fast, often skippable)

Extract only what cannot be inferred: the system, the parameters worth exposing, the regime or scale of interest, and the one or two readouts that matter most. If the request already implies these, skip the interview and build.

## Phase 2: simulation doctrine

Correctness first, then interactivity, then polish.

- **Pick the right integrator and say why.** Forward Euler for cheap non-stiff toys; velocity Verlet for anything whose energy should be conserved (orbits, springs, N-body); RK4 when accuracy per step matters; semi-implicit for stiff stability. Never let a conservative system visibly bleed energy without labelling it as numerical drift.
- **Work in real units, then non-dimensionalise.** Scale variables so the interesting behaviour sits near order-one numbers, and show real units in the readouts even when the engine runs dimensionless. Name the technique to the user: non-dimensionalisation keeps the numerics stable and the sliders meaningful.
- **Check against invariants.** Conservation laws, fixed points, known limits and analytic special cases. If the model has a closed-form limit, show the simulation converging to it. Keep a live invariant readout (total energy, population, momentum) so drift is visible.
- **For accuracy-critical dynamics,** run the model through scientific-solver first when it is installed, and show its convergence record beside the simulation. Otherwise compare two step sizes and report the difference.
- **Expose the parameters that change qualitative behaviour,** not cosmetic ones. The sliders should let the user cross bifurcations, phase transitions and stability boundaries. Name those thresholds in the interface.
- **Two views minimum:** the system itself (animation, field or bodies) and a quantitative readout (time series, phase portrait, spectrum or distribution). Numbers are shown, never narrated.

## Phase 3: build

**One self-contained file**: a single-file interactive page or component, whichever the host renders. Real engine in JavaScript; a `requestAnimationFrame` loop with a fixed-timestep accumulator so physics does not depend on frame rate. Canvas or SVG for the system; a charting library or hand-drawn SVG for readouts. No backend, no API.

**Appearance.** Warm and light by default, with a readable dark option and a text-size control. The canvas may run full-bleed; controls sit in an opaque, high-contrast panel beside or below it, never glass over the canvas. Monospace for numeric output. Motion belongs to the simulated system only. Respect reduced-motion settings by starting paused.

**Controls.** Labelled sliders with live values and keyboard support; play, pause, step and reset; a speed multiplier; preset buttons for named regimes ("stable orbit", "chaotic", "critical"); a scrubbable timeline when the history is worth replaying.

**States.** A clear starting state with the first preset loaded. A visible error state when the integrator diverges (non-finite values or runaway invariants): pause, say which quantity blew up, and offer a smaller step or a reset.

**Interactivity floor.** Every parameter is live-editable while running; reset returns the exact initial state; presets jump to named regimes; readouts update every frame.

## Phase 4: quality bar

- Dynamics are calibrated, not eyeballed; invariants hold or drift is labelled.
- At least one analytic or limit check passes, and the result is shown.
- Fixed-timestep loop; behaviour is identical regardless of frame rate.
- Parameters cross real qualitative thresholds, and those are named.
- The visual and the quantitative readout are both present and live.
- Runs smoothly at reasonable N, degrades gracefully, never freezes.
- Exercise the controls, presets, reset and the divergence state before calling it done.

## Rules that always hold

- Build the real engine, never a decorative fake.
- A simulation shows what its model implies. It is not evidence about the world; a finding that matters goes through research-agency.
- Writing: plain language, Australian spelling, no long dashes.

## Output

The simulation, then one paragraph: which regime to try first, which slider does the interesting thing, and the one numerical technique used that transfers to the next simulation.

## What has and has not been tested

Revised by Claude on 22 October 2026: description shortened to fit every host, long dashes removed, the appearance brought into line with the house theme (no glass panels, warm light default with a dark option, reduced motion), a divergence error state added, and an accuracy route to scientific-solver. Not yet tested: routing after the description change, and a fresh build against the new quality bar.