---
name: interactive-generator
description: "Builds a quick single-file interactive tool from a one-line description: a calculator, converter, tracker, planner board, wizard, form, small dashboard, simulator or puzzle, working with zero configuration. Use when the user says 'build me a quick [tool]', 'make an interactive [thing]', 'create a calculator for [purpose]', 'generate a [utility] app', 'I need a tool that [does X]' or 'quick app for [task]'. Not for tools that must save data between sessions (pocket-app), weighted option comparison (decision-board), physics or system simulations with calibrated engines (simforge), apps with a back end (forge), or courses and quizzes (preceptor, elicitor)."
---

# interactive-generator

Builds a small working tool in one pass, from a plain description, as a single file that runs without setup.

## Use when

- The user wants a one-off utility they can use immediately: a calculator, converter, checklist, tracker, planner, wizard, form or simple dashboard.
- The need is clear enough to build without a design phase.

## Not this skill

| The request | Goes to |
|---|---|
| Tool whose data must persist, with import/export and undo | pocket-app |
| Compare concrete options with weighted criteria and sensitivity | decision-board |
| Simulate a system with parameters and regimes | simforge |
| Needs a server, accounts, shared data or sync | forge |
| Repair or restyle an existing interface | anti-vibecoded-ui |
| Quiz, survey instrument or questionnaire | elicitor |
| Course or study app | preceptor |
| Teach one concept interactively | learning-visualiser |
| Ambitious showcase page | showpiece |

## Inputs

- What the tool must do, in the user's words.
- Who uses it and on what device, if stated. Default: Shaun, desktop and phone.
- Any real formulas, rates or rules involved. Do not guess a formula that has a correct form; look it up or ask.

## Procedure

1. **Parse the job.** State in one line what the tool does and the minimum interaction that does it. Ask a question only if a wrong guess would make the tool useless (for example an unknown formula or currency).
2. **Define the data model**: what state the tool holds, what the user inputs, what it shows.
3. **Pick the form** from the table.
4. **Build the layout**, then wire the logic (calculations, transformations, validation), then handle edge cases: empty, zero, negative, very large, invalid input.
5. **Polish**: sensible defaults so it works on first load, helpful empty states, visible focus and hover states, keyboard shortcuts where natural, responsive layout.
6. **Test the logic** with at least two worked examples where the answer is known, and state them. If the tool computes money, tax or units, show the formula used.
7. **Deliver** the file with one line on how to open it and what it does not do (for example, state is lost on reload).

| Tool type | Form | Typical stack |
|---|---|---|
| Calculator, converter | Single page | React and Tailwind, or plain HTML and JS |
| Dashboard, monitor | Data-rich layout | A chart library |
| Planning tool | Board or grid | Drag and drop |
| Decision aid | Step-through wizard | State machine |
| Tracker | List with state | Local component state |
| Simulator (simple) | Canvas | Canvas and a game loop |
| Form, survey | Multi-step | Validation |
| Game, puzzle | Interactive canvas | Game loop |

## Output

- One self-contained file: `.jsx` with a default export when the host renders React, otherwise one `.html` file with inline script and style. Props or options all have defaults.
- No network calls, accounts or external data unless the user asked.
- A short note: what it does, the worked examples tested, and its limits.

## Design standards

- Clean, dark-friendly theme with generous spacing; readable on a phone.
- The interface explains itself; labels and units are visible.
- State lives in memory only (no browser storage) unless the user asks for persistence, in which case hand the job to pocket-app.
- An error boundary or guarded input handling so bad input never produces a blank screen.
- Contrast and focus states meet basic accessibility (AA contrast, keyboard operable).

## Rules that always hold

- Never present a computed result without being sure of the formula; flag assumptions on screen (rates, rounding, tax year).
- Do not collect or send personal data. Nothing leaves the page.
- If the tool is faster to replace with a spreadsheet formula or an existing standard tool, say so briefly and still build it if asked.
