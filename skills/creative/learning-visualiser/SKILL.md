---
name: learning-visualiser
description: >
  Create interactive learning visualisations that make complex concepts click instantly.
  Use when the user asks to "visualise how [concept] works", "make me a learning tool for [topic]",
  "interactive explainer for [subject]", "teach me [thing] visually", "show me how [process] works",
  or any request to turn knowledge into an interactive visual experience.
metadata:
  version: "0.1.0"
  author: "Shaun"
---

# Learning Visualiser

Create interactive, visually stunning learning tools that transform complex concepts into intuitive visual experiences. Every output should make the user say "now I get it."

## Activation Protocol

When triggered, immediately determine:

1. **What concept** needs to be visualised
2. **What type of learner** is the audience (visual, kinetic, analytical)
3. **What format** best serves the concept (see Format Selection below)

## Format Selection Matrix

Choose the highest-impact format for the concept:

| Concept Type | Best Format | Technology |
|---|---|---|
| Processes / flows | Animated step-through | React + Framer Motion |
| Data relationships | Interactive graph/network | React + D3.js |
| Mathematical concepts | Parametric playground | React + recharts/canvas |
| Systems / architecture | Zoomable diagram | React + SVG |
| Timelines / history | Scrollable timeline | React + scroll events |
| Comparisons | Side-by-side interactive | React + Tailwind |
| Physical/spatial | 3D interactive model | Three.js |
| Hierarchies | Expandable tree | React + D3.js |

## Design Principles

1. **Progressive disclosure** — start simple, let the user drill deeper
2. **Immediate feedback** — every interaction produces visible change
3. **Beautiful defaults** — looks stunning before the user touches anything
4. **Annotations matter** — label everything, explain everything on hover
5. **Colour with purpose** — use colour to encode meaning, not decoration

## Build Protocol

1. **Concept decomposition** — break the topic into 3-5 core ideas that build on each other
2. **Interaction design** — decide what the user controls (sliders, toggles, click-to-reveal, drag)
3. **Visual hierarchy** — most important concept is visually dominant
4. **Build as single-file React** — use Tailwind for styling, inline everything
5. **Add explanatory text** — short, punchy annotations that teach as you explore
6. **Test mental model** — does interacting with this build correct intuition?

## Output Standards

- Single .jsx file, self-contained with all dependencies imported
- Responsive design (works on any screen size)
- Dark mode by default with high-contrast colours
- Smooth animations (60fps, no jank)
- Loading states for any computed elements
- Keyboard accessible where possible

## Quality Bar

Before delivering, verify:
- Does a 12-year-old understand the core concept from this visualisation?
- Is it beautiful enough to screenshot and share?
- Does every interactive element teach something?
- Would this be better than the top Google result for learning this topic?
