---
name: interactive-generator
description: >
  Generate interactive tools, apps, calculators, dashboards, and utilities on the fly from a single description.
  Use when the user asks to "build me a quick [tool]", "make an interactive [thing]",
  "create a calculator for [purpose]", "generate a [utility] app", "I need a tool that [does X]",
  "quick app for [task]", or any request for an instant functional interactive tool.
metadata:
  version: "0.1.0"
  author: "Shaun"
---

# Interactive Generator

Build functional interactive tools, apps, and utilities instantly from natural language descriptions. Every tool should feel polished enough to ship.

## Activation Protocol

1. Parse what the user needs — what problem does this tool solve?
2. Determine the minimum viable interaction model
3. Select the optimal format (see below)
4. Build it in one shot — working, polished, complete

## Format Selection

| Tool Type | Format | Stack |
|---|---|---|
| Calculator / converter | Single-page app | React + Tailwind |
| Dashboard / monitor | Data-rich layout | React + recharts |
| Planning tool | Interactive board/grid | React + drag-and-drop |
| Decision tool | Wizard / flow | React + state machine |
| Tracker | List with state | React + local state |
| Simulator | Canvas-based | React + HTML5 Canvas |
| Form / survey | Multi-step form | React + validation |
| Game / puzzle | Interactive canvas | React + game loop |

## Design Standards

1. **Professional by default** — dark theme, clean typography, generous spacing
2. **Instant usability** — zero learning curve, the UI explains itself
3. **Responsive** — works on desktop and mobile
4. **Delightful details** — subtle animations, hover states, transitions
5. **Data persistence in state** — use React useState/useReducer (no localStorage)

## Build Protocol

1. **Define the data model** — what state does this tool manage?
2. **Design the interaction** — what does the user input, see, and control?
3. **Build the layout** — component structure with Tailwind
4. **Wire the logic** — calculations, transformations, validations
5. **Polish the output** — animations, empty states, edge cases
6. **Deliver as single .jsx** — self-contained, importable, ready to use

## Output Standards

- Single .jsx file with default export
- All props have defaults (works with zero configuration)
- Tailwind utility classes only (no custom CSS)
- Error boundaries for graceful failures
- Helpful empty states (never a blank screen)
- Keyboard shortcuts where appropriate

## Quality Bar

- Does it solve the problem in under 3 clicks?
- Would you be embarrassed to show this to a designer? (Answer should be no)
- Does it handle edge cases gracefully?
- Is it faster than Googling for an existing tool?
