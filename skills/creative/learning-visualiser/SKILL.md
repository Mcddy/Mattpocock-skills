---
name: learning-visualiser
description: "Builds one interactive visual explainer for a single concept or process so the learner builds the right mental model: an animated step-through, parametric playground, zoomable system diagram, timeline, side-by-side comparison, 3D model or expandable hierarchy. Use when the user says 'visualise how [concept] works', 'make me a learning tool for [topic]', 'interactive explainer for [subject]', 'teach me [thing] visually' or 'show me how [process] works'. Not for multi-lesson animated courses (percept), courses with quizzes and spaced review (preceptor), a standalone quiz (elicitor), numerical simulations with calibrated engines (simforge), explorable maps of a whole domain (atlas), or auditing an existing educational visual (heirloom-audit-learning-visualisation)."
---

# learning-visualiser

Builds a single-file interactive explainer for one concept, designed so that using it corrects the learner's intuition. Intended for Shaun's own study (networking, security, AI) and for explaining to others.

## Use when

- One concept, mechanism or process needs to be understood through interaction, not text.
- The learner can be reached with sliders, toggles, step buttons or click-to-reveal.

## Not this skill

| The request | Goes to |
|---|---|
| Multi-lesson animated course | percept |
| Full course with prerequisites, practice and spaced review | preceptor |
| Quiz or self-test only | elicitor |
| Simulation with calibrated numerical engine and regimes | simforge |
| Explorable map of a whole domain's connections | atlas |
| Check an existing educational visual for accuracy and accessibility | heirloom-audit-learning-visualisation |
| Static infographic or illustration | generative-content |
| Explain it in conversation, no build | teach |

## Inputs

- The concept, and the learner's current level (default: capable beginner who knows the neighbouring basics).
- The misconception or sticking point, if known. This is the most useful input.
- Source facts or equations if precision matters (protocol steps, formulas).

## Procedure

1. **Name the target understanding** in one sentence: after using this, the learner can say or predict what? Name the likely misconception it must fix.
2. **Verify the content.** Get the mechanism right before drawing it: check protocol fields, formulas and sequences against a reliable source or the supplied material. If unsure, say so on screen or ask. A beautiful wrong explainer is worse than none.
3. **Decompose** into three to five ideas that build on each other.
4. **Choose the format** from the table and decide what the learner controls (slider, toggle, step, click-to-reveal, drag).
5. **Design for progressive disclosure**: simple at first load, depth on demand. Every interaction produces a visible change, and the most important idea is visually dominant.
6. **Build** as one self-contained file with labels and short annotations that teach as the learner explores. Use colour to encode meaning only.
7. **Test the mental model**: walk through it as the learner. Predict-then-reveal prompts ("what happens if you double the window size?") are the strongest device when the concept allows.
8. **Deliver** with one line on how to use it and the one misconception it addresses.

| Concept type | Format | Technology |
|---|---|---|
| Process or flow | Animated step-through | React with an animation library, or SVG and CSS |
| Data relationships | Interactive graph | SVG or a graph library |
| Mathematical idea | Parametric playground | Canvas or a chart library |
| System or architecture | Zoomable diagram | SVG |
| Timeline or history | Scrollable timeline | Scroll events |
| Comparison | Side-by-side with controls | Grid layout |
| Physical or spatial | 3D model | Three.js |
| Hierarchy | Expandable tree | SVG or a tree layout |

## Output

- One self-contained file: `.jsx` with a default export if the host renders React, otherwise one `.html` file. No network calls.
- Responsive, dark by default with high contrast, keyboard operable where possible, smooth animation, a visible state for anything computed.
- A short note: the target understanding, what the controls do, and any simplification made (for example, timings not to scale).

## Quality bar

- A newcomer can state the core idea after one minute.
- Every control teaches something; remove controls that only decorate.
- Simplifications are labelled where the learner might take them literally.
- Interaction beats the best static diagram of the same topic; if it does not, say a diagram would do.

## Rules that always hold

- Accuracy over polish. Label illustrative values as illustrative.
- Do not imply causation the model does not support; keep modelled behaviour distinct from measured data.
- For a heavily quantitative or consequential topic, recommend running the audit skill before sharing.
