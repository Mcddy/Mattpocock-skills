# The COURSE data block, field by field

A course is one JSON object. `scripts/build_course.py` writes it into `assets/engine.html` between these two markers and changes nothing else:

```
/* === COURSE DATA: BEGIN (to make a course, write only this object, as strict JSON) === */
const COURSE = { ... };
/* === COURSE DATA: END === */
```

Strict JSON: double quotes, no comments, no trailing commas, `true` and `false` unquoted. Write the course as a `.json` file, validate it, then build. `assets/sample-course-ipv4.json` is a complete five-module course to match for standard; read one of its modules before writing your own.

Text fields accept two inline marks: `` `code` `` and `**strong**`. Everything else is shown as plain text. Keep the JSON plain ASCII where you can.

## Course

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id: lower-case letters, digits, hyphens. Saved progress is keyed to it. Never change it for the same course. |
| `version` | yes | Whole number from 1. Raise it whenever module, objective, card or item ids are added, removed or change meaning. |
| `title` | yes | Shown as the page heading. |
| `subtitle` | no | One or two sentences under "Course map". |
| `size` | yes | `"primer"`, `"course"`, `"full"`, or `"demo"` for the engine's own sample. |
| `size_reason` | yes | One line: why this size. Shown on the map. |
| `for` | no | Who it was written for. Shown under the title. |
| `gate_threshold` | no | Pass mark in whole percent, 50 to 100. Default 80. |
| `check_after_days` | no | Days without evidence after which an objective is listed as due for a check. Default 30. |
| `modules` | yes | List of modules, in an order a learner could follow. |

## Module

| Field | Required when ready | Meaning |
|---|---|---|
| `id` | always | Stable id, unique in the course. |
| `title` | always | |
| `status` | always | `"ready"` or `"planned"`. A planned module has only `id`, `title`, `status` and `prereqs`. |
| `prereqs` | always | Ids of the modules that must be mastered first. `[]` for a starting module. |
| `summary` | yes | One or two sentences. |
| `objectives` | yes | `[{"id", "text", "bloom"}]`. `bloom` is one of remember, understand, apply, analyse, evaluate, create. |
| `terms` | no | `[{"term", "definition"}]`. |
| `theory` | yes | `[{"objective", "heading", "blocks"}]`. Every objective needs at least one section. |
| `visuals` | advised | List of visuals (below). |
| `worked` | yes | List of worked examples (below). |
| `quiz` | yes | Practice items (below). `objective` may name an objective of this module or of any module it depends on. |
| `gate` | yes | `{"items": [...]}`. Each item's `objective` must be one of this module's. Every objective needs at least one item; give it two or more. |
| `cheatsheet` | yes | A list of blocks. |
| `cards` | yes | `[{"id", "objective", "front", "back"}]`. |
| `challenge` | no | Applied challenge (below). |

Every id (module, objective, visual, worked example, item, card) must be unique across the whole course. Prefix ids with the module id.

## Blocks

Theory sections, cheat sheets and challenge briefs are lists of blocks.

| `type` | Fields | Shown as |
|---|---|---|
| `p` | `text` | Paragraph |
| `list` | `items` | Bulleted list |
| `steps` | `items` | Numbered list |
| `note` | `label`, `text` | A labelled note. Use labels such as Definition, Assumption, Rule, Check, Common error, Scope. |
| `code` | `text` | Fixed-width block; line breaks and spacing are kept |
| `table` | `head`, `rows` | Table. Every row has as many cells as `head`. Keep to four columns or fewer for a phone. |

Optional on any block: `source` (text shown as "Source: ..."), and `check` or `checks` (below).

## Items (practice and gate)

```json
{"id": "m1-g1", "objective": "m1-o1", "stem": "One clear question?",
 "options": [
  {"text": "A wrong answer someone would give", "correct": false, "why": "Why it is wrong, naming the misconception."},
  {"text": "The right answer", "correct": true, "why": "Why it is right."},
  {"text": "Another real mistake", "correct": false, "why": "Why it is wrong."}]}
```

Three or more options, exactly one with `"correct": true`, and a `why` on every option. Options are shown in the order written; on a gate retake the engine shuffles them. Rules for writing them are in `references/item-writing.md`.

## Worked examples

```json
{"id": "m1-w1", "objective": "m1-o2", "title": "Short title",
 "full": {"problem": "...", "steps": [{"text": "What is done.", "result": "what comes out"}]},
 "partial": {"problem": "...", "steps": [
   {"text": "A step that is shown.", "result": "..."},
   {"text": "A step the learner completes.", "blank": {"label": "Label of the input", "answer": "42", "accept": ["42.0"], "hint": "A pointer to the method."}}]},
 "independent": {"problem": "...",
   "answers": [{"label": "Label of the input", "answer": "42", "accept": []}],
   "solution": [{"text": "...", "result": "..."}]}}
```

All three levels are required. The partial level needs at least one blank. A step has either a `result` or a `blank`, never both. `result` is plain text. Typed answers match `answer` or any entry of `accept` after spaces and case are removed.

## Applied challenge

```json
"challenge": {"title": "...", "objective": "m5-o3",
  "brief": [ blocks ],
  "tasks": [{"label": "What to enter", "answer": "...", "accept": []}],
  "solution": [{"text": "...", "result": "..."}]}
```

Shown at the end of Practice. The solution is hidden until asked for.

## Visuals

Common fields: `type`, `id`, `title`, `objective` (one of this module's), `caption` (what to notice), and optional `prompts` (things to try, each asking for a prediction).

Formulas are written in a small arithmetic language and are never run as code. Allowed: numbers, the variables the visual declares, `+ - * / ^`, brackets, and the functions `floor ceil round abs sqrt log2 min max mod band`. `^` is a power and binds tighter than a leading minus, so `-2^2` is -4. `band(a, b)` is bitwise AND of two whole numbers. A formula that divides by zero or leaves the real numbers shows "no value". Formats: `int` (rounded), `fixed1`, `fixed2`, `bin8` (eight binary digits), `bin`.

### steps

A procedure revealed one step at a time. Give `steps` (each with a `caption`) and either `rows` or `nodes`.

```json
{"type": "steps", "id": "m1-v1", "title": "...", "objective": "m1-o1", "caption": "...",
 "col_labels": ["128", "64", "32"],
 "rows": [{"label": "Row name", "cells": ["1", "0", "1"], "show_at": 1, "cells_at": [1, 2, 3]}],
 "steps": [{"caption": "What happens first.", "highlight": [[0, 0]]}, {"caption": "..."}, {"caption": "..."}]}
```

`show_at` is the step at which the whole row appears (default 1). `cells_at` gives the step at which each cell is filled in. `highlight` is a list of `[row, cell]` pairs, counted from 0. For a flow of boxes use `"nodes": [{"label": "...", "detail": "...", "show_at": 1}]` in place of `rows`; without `show_at`, node k appears at step k.

### slider

One or two controls driving computed outputs.

```json
{"type": "slider", "id": "m2-v1", "title": "...", "objective": "m2-o1", "caption": "...",
 "params": [{"name": "p", "label": "Prefix length", "min": 8, "max": 30, "step": 1, "value": 26, "unit": ""}],
 "outputs": [
   {"label": "Host bits", "formula": "32 - p", "format": "int"},
   {"label": "Share", "formula": "p / 32 * 100", "format": "fixed1", "unit": "%", "bar_max": "100"},
   {"label": "Joined value", "parts": ["p", "32 - p"], "join": " and ", "format": "int"}],
 "strip": {"cells": 32, "group": 8, "label": "What the strip shows",
   "regions": [{"label": "network bits", "symbol": "N", "upto": "p"}, {"label": "host bits", "symbol": "H", "upto": "32"}]}}
```

`bar_max` draws a bar of the output against that value. `parts` joins several formulas into one readout. `strip` draws up to 64 cells split into one to three regions; each region ends at the cell number its `upto` formula gives.

### compare

Two states and a control to show the first, the second or both. A fact with the same label and a different value in the two states is marked "differs".

```json
{"type": "compare", "id": "m5-v1", "title": "...", "objective": "m5-o1", "caption": "...",
 "states": [
   {"name": "Before", "summary": "...", "segments": [{"label": "whole", "size": 256}], "facts": [{"label": "Subnets", "value": "1"}]},
   {"name": "After", "summary": "...", "segments": [{"label": "first", "size": 64}, {"label": "second", "size": 64}], "facts": [{"label": "Subnets", "value": "4"}]}]}
```

Exactly two states. Each needs `facts`, `segments` or both. Segments are drawn in proportion to `size`.

### number-line

A marker on a line, optionally cut into segments, with readouts.

```json
{"type": "number-line", "id": "m3-v1", "title": "...", "objective": "m3-o1", "caption": "...",
 "min": 0, "max": 256,
 "point": {"name": "x", "label": "Fourth octet", "value": 77, "step": 1, "max": 255},
 "choice": {"name": "b", "label": "Prefix length", "value": 64, "options": [{"label": "/26", "value": 64}, {"label": "/27", "value": 32}]},
 "segment_size": "b",
 "readouts": [{"label": "Start of the block", "formula": "floor(x / b) * b", "format": "int"}]}
```

`choice` is optional and adds a second variable chosen by buttons. `segment_size` is optional; with it, the segment holding the marker is banded.

### table-builder

The learner fills the computed columns and the engine checks each cell against its formula.

```json
{"type": "table-builder", "id": "m4-v1", "title": "...", "objective": "m4-o1", "caption": "...",
 "columns": [
   {"key": "p", "label": "Prefix length", "given": true},
   {"key": "u", "label": "Usable hosts", "formula": "2^(32 - p) - 2", "format": "int"}],
 "rows": [{"p": 24}, {"p": 26}]}
```

At least one given column and one computed column. Formulas use the keys of given columns. Five columns is the most that fits a phone.

### custom

For what the built-in types cannot show. The visual names a renderer and passes it data:

```json
{"type": "custom", "id": "m1-v2", "renderer": "bit-toggles", "title": "...", "objective": "m1-o2", "caption": "...", "data": {"start": "01001101"}}
```

The renderer goes in a separate plain-ASCII file holding one object literal, passed to `build_course.py --renderers FILE.js`. It replaces the value between the CUSTOM RENDERERS markers:

```js
{
  "bit-toggles": function (host, data, api) {
    // host: an empty element to fill. data: the visual's "data".
    // api.el(tag, attributes, children) builds elements (text is set as text; "on" takes handlers);
    // api.evalFormula(text, variables) and api.formatValue(number, format) are the engine's own;
    // api.say(text) announces a change to assistive technology.
  }
}
```

Rules for a renderer: build elements with `api.el`, never from markup strings; use native buttons and inputs with labels; no network, no storage, no timers that run for ever; use the page's colour tokens (`var(--ink)`, `var(--accent-soft)`, `var(--mark)`), never fixed colours. `assets/sample-renderers-ipv4.js` is a working one. If the renderer is missing or throws, the visual shows a message and the rest of the module still works.

## Check fields (optional, for subjects whose answers can be computed)

Any item, step, blank, answer, task, card, block, compare fact or segment, slider output, number-line readout or table column may carry `"check": {"op": "name", "args": [...]}` or a list under `"checks"`. The engine ignores them. They exist so a verifier script, written for the course's subject, can recompute each answer with a trusted library and compare. In formulas checked across a control's range, an argument written `"$p"` stands for the variable `p`. A check on a step is compared with its `result`; add `"in": "text"` to compare with the step's text. `assets/sample-course-ipv4.json` carries a check on every numeric answer. `assets/verifier-template.py` is the verifier to start from: copy it, add one function per operation your checks name, and run it on the course. `validate_course.py` reports how many answers containing digits carry no check.

## A small complete course

The smallest course the validator accepts: one module with every required part. It is deliberately tiny; a real module has six or more practice items and eight or more cards.

```json
{
 "id": "clock-demo", "version": 1, "title": "The 24-hour clock", "size": "demo",
 "size_reason": "One module, to show the shape of the data.",
 "modules": [{
  "id": "clock", "title": "From 24-hour to 12-hour time", "status": "ready", "prereqs": [],
  "summary": "Converting a 24-hour time to a 12-hour time with am or pm.",
  "objectives": [{"id": "clock-o1", "text": "Convert a 24-hour time to 12-hour time with am or pm.", "bloom": "apply"}],
  "terms": [{"term": "24-hour time", "definition": "Hours counted from 00 at midnight to 23."}],
  "theory": [{"objective": "clock-o1", "heading": "Subtract 12 after noon", "blocks": [
   {"type": "p", "text": "Hours 01 to 11 are the same in both systems and are **am**. Hour 12 is 12 pm. For hours 13 to 23 subtract 12 and write **pm**."},
   {"type": "note", "label": "Special case", "text": "Hour 00 is 12 am: midnight starts the day."}]}],
  "visuals": [{"type": "slider", "id": "clock-v1", "title": "Turn the hour", "objective": "clock-o1",
   "caption": "The 12-hour number repeats; only am and pm tell the two halves of the day apart.",
   "params": [{"name": "h", "label": "Hour on the 24-hour clock", "min": 0, "max": 23, "step": 1, "value": 15}],
   "outputs": [{"label": "Hour on the 12-hour clock", "formula": "mod(h + 11, 12) + 1", "format": "int"}]}],
  "worked": [{"id": "clock-w1", "objective": "clock-o1", "title": "An afternoon time",
   "full": {"problem": "Write 15:20 in 12-hour time.", "steps": [
    {"text": "15 is above 12, so subtract 12.", "result": "3"},
    {"text": "Keep the minutes and write pm.", "result": "3:20 pm"}]},
   "partial": {"problem": "Write 21:05 in 12-hour time.", "steps": [
    {"text": "21 is above 12, so subtract 12.", "blank": {"label": "Hour", "answer": "9", "accept": [], "hint": "21 minus 12."}},
    {"text": "Keep the minutes and write pm.", "result": "9:05 pm"}]},
   "independent": {"problem": "Write 18:45 in 12-hour time.",
    "answers": [{"label": "12-hour time", "answer": "6:45 pm", "accept": ["6:45pm", "6.45 pm"]}],
    "solution": [{"text": "18 minus 12 is 6. Keep the minutes and write pm.", "result": "6:45 pm"}]}}],
  "quiz": [{"id": "clock-q1", "objective": "clock-o1", "stem": "What is 13:00 in 12-hour time?", "options": [
   {"text": "1 pm", "correct": true, "why": "13 minus 12 is 1, and the hour is after noon."},
   {"text": "3 pm", "correct": false, "why": "The second digit was read as the hour. Subtract 12 from 13."},
   {"text": "1 am", "correct": false, "why": "The hour is right, but 13:00 is after noon, so it is pm."}]}],
  "gate": {"items": [
   {"id": "clock-g1", "objective": "clock-o1", "stem": "What is 15:00 in 12-hour time?", "options": [
    {"text": "5 pm", "correct": false, "why": "The second digit was read as the hour. 15 minus 12 is 3."},
    {"text": "3 pm", "correct": true, "why": "15 minus 12 is 3, and the hour is after noon."},
    {"text": "3 am", "correct": false, "why": "The hour is right, but 15:00 is after noon, so it is pm."}]},
   {"id": "clock-g2", "objective": "clock-o1", "stem": "What is 00:30 in 12-hour time?", "options": [
    {"text": "12:30 pm", "correct": false, "why": "12:30 pm is half past noon. Hour 00 is midnight."},
    {"text": "0:30 am", "correct": false, "why": "The 12-hour clock has no hour 0. Midnight is written 12."},
    {"text": "12:30 am", "correct": true, "why": "Hour 00 is 12 am, and the minutes are kept."}]}]},
  "cheatsheet": [{"type": "list", "items": ["00 is 12 am.", "01 to 11: same hour, am.", "12 is 12 pm.", "13 to 23: subtract 12, pm."]}],
  "cards": [
   {"id": "clock-c1", "objective": "clock-o1", "front": "17:00 in 12-hour time", "back": "5 pm"},
   {"id": "clock-c2", "objective": "clock-o1", "front": "00:00 in 12-hour time", "back": "12 am"}]
 }]
}
```

`assets/engine.html` ships with a larger, three-module demo course in its data block that uses every block type and every built-in visual type. Run `python scripts/build_course.py --extract assets/engine.html demo.json` to read it as a file.

## Changing a course that people have progress in

- Keep every id that still means the same thing.
- Give a new id to anything that now means something else, and raise `version`.
- Run `python scripts/validate_course.py --compare OLD NEW` before shipping.
- When a learner opens the new file where the old one was used, or imports an old backup, the page matches progress by module, objective and card id, lists anything unmatched, and keeps the older record so it can be copied out.
