# Picker data: every field, by kind

Detail for `SKILL.md`. The data is one strict JSON object. `scripts/validate_picker.py` enforces everything marked "required" here, and `scripts/build_picker.py` puts the object into `assets/picker.html`.

## 1. The object

```json
{"id": "notes-theme", "version": 1,
 "title": "Theme for the notes tool",
 "question": "Which colour theme should the note-taking tool open in?",
 "kind": "theme",
 "recommended": {"id": "warm-paper", "reason": "it is the warm light theme that was asked for, and every text pair measures above 4.5."},
 "options": [{"id": "warm-paper", "name": "Warm paper", "note": "Cream page, brown-black ink and a rust accent; the warmest of the five.", "tokens": {}, "sample": {}}],
 "controls": [{"id": "density", "label": "Density", "type": "choice", "options": ["compact", "comfortable", "roomy"], "default": "comfortable"}],
 "context": {}}
```

| Field | Rule |
|---|---|
| `id` | Required. Lower-case words joined by hyphens. It names the picker in the result, so keep it stable |
| `version` | Whole number, 1 or more. Raise it when the options change, so an old result is not applied to new options |
| `title`, `question` | Required. The question says what is being chosen |
| `kind` | Required: `theme`, `type`, `layout`, `copy`, `component` or `custom` |
| `recommended` | `{"id", "reason"}`. Leaving it out is an advisory: the person should be reacting to a commitment |
| `options` | Required, 2 to 8. More than 6 is an advisory |
| `options[].id` | Required, unique, hyphenated. Name it for what it is (`warm-paper`), not for its position (`a`, `option-2`) |
| `options[].name` | Required, unique |
| `options[].note` | Required: one line, 140 characters or fewer, saying what is different about this option. Two options with the same note are refused |
| `controls` | Optional. Only the control ids listed for the kind in section 3 |
| `context` | Required: the real content the options are drawn on. Placeholder text is refused anywhere in it |

Two options whose `tokens` and `sample` are identical are refused: they would look the same.

## 2. What each kind draws, and what it needs

### theme

A working specimen drawn with each option's colours: heading, status line, body paragraph, link, a labelled input with its error, a table with its rows, the primary button at rest, on hover, with keyboard focus and disabled, and a secondary button.

- `options[].tokens`, all required as hex: `bg`, `surface`, `text`, `muted`, `line`, `accent`, `on-accent`, `danger`, `ok`. Optional: `accent-strong` (button hover), `focus`, `field` (input background).
- `context`: `title`, `body`, `primary` (button label) required. `field` `{label, value, error}` required. `columns` (a list of labels) and `rows` (lists, one value per column) required. Optional: `status`, `link`, `secondary`.
- Measured: every text pair's contrast, computed in the page from the colours the browser used. Pairs under 4.5 are named on the card. The validator computes the same pairs from the tokens and refuses an option whose body text (on the page, on a surface, or in the input) is under 4.5.
- Ratios are rounded to two places before they are compared with 4.5, the same as the shared contrast checker, so a pair at 4.496 reads as 4.50 and passes.

### type

The user's text set in each option's stack, size, weight, measure and leading.

- `options[].sample`: `stack` required (a CSS font stack; end it with a generic family). Optional numbers: `size` 8 to 96, `weight` 100 to 900, `leading` 0.9 to 3, `measure` 20 to 120 (in ch), `heading_stack`, `heading_size`, `heading_weight`.
- `context`: `text` required, a real paragraph of 40 characters or more, or a list of paragraphs. Optional `heading`.
- Measured: the font actually in use on this device, any named font that is not installed here, characters per line, text size in px.
- Use system and commonly installed stacks only. The page makes no requests, so a web font cannot be loaded. A stack that names an uninstalled font is shown in the fallback and the page says so.

### layout

The same rows arranged per option, drawn at a phone width (360) and a wide width (960) side by side, scaled to fit the card.

- `options[].sample.layout` required: `table`, `cards` or `list`.
- `context`: `columns` required, two or more `{key, label}` with optional `role` of `title`, `value` or `status` (a status column may carry `alert`, a list of values to mark). `rows` required, two or more objects with a value for every key. Optional `title`.
- Measured, per width: height in px, how many phone screens tall, and whether it scrolls sideways.

### copy

Text variants in the component they will appear in.

- `options[].sample`: `heading` required; `sub` and `action` optional.
- `context.component`: `header` (needs `brand`; optional `nav`, `action`, `secondary`, `footnote`) or `notice` (optional `action`, `secondary`). Optional `tokens` to draw it in the product's own colours.
- Measured: length of each slot in characters and words, and how many lines the heading takes at this width.

### component

One component across its states: a button (rest, hover, keyboard focus, pressed, busy, disabled) or a field (empty, filled, keyboard focus, error, disabled).

- `options[].sample`: optional `variant` (`solid`, `outline`, `soft`), `radius` 0 to 40, `border` 0 to 6, `weight`, `pad_y` 0 to 40, `pad_x` 0 to 60. Optional `tokens` per option.
- `context`: `component` required (`button` or `field`), `label` required. A button may give `busy_label`. A field needs `value` and `error`, and may give `placeholder`. Optional `tokens`.
- Measured: size at rest (with a note when it is under the 44 px touch height) and text contrast at rest.

### custom

For anything the built-in kinds do not draw. Each option needs a renderer function, supplied to `scripts/build_picker.py` with `--renderers FILE.js`:

```js
const RENDERERS = {
  "plain-count": function (root, ctx) {
    // ctx: {option, context, controls, el}. Draw into root with ctx.el(tag, {text: ...}, children).
    root.appendChild(ctx.el('p', {text: ctx.context.task + ': ' + ctx.context.done + ' of ' + ctx.context.total}));
    return [{label: 'lines of text', value: 1}];      // optional measured facts
  }
};
```

A renderer is run again whenever a tweak changes, with the new values in `ctx.controls`. It must be plain ASCII, set text as text (never markup built from strings), and make no requests: the builder refuses `fetch`, `XMLHttpRequest`, `WebSocket`, `import` and any URL with a scheme. Any control id is allowed for this kind, because the renderer decides what it means.

## 3. Controls each built-in kind responds to

A control the renderer ignores would change nothing, so the validator refuses it.

| Kind | Control id | Type | Values |
|---|---|---|---|
| theme | `density` | choice | from `compact`, `comfortable`, `roomy` |
| theme | `text-size` | range, unit `px` | for example 14 to 20 |
| theme | `radius` | range, unit `px` | corner radius |
| type | `scale` | range, no unit | percent of each option's own size |
| type | `measure` | range, unit `ch` | line length |
| layout | `density` | choice | as above |
| layout | `text-size` | range, unit `px` | |
| layout | `stripes` | toggle | shade alternate rows |
| copy | `align` | choice | `left`, `centre` |
| copy | `heading-size` | range, unit `px` | |
| copy | `action` | toggle | show the buttons |
| copy | `density` | choice | as above |
| component | `density` | choice | as above |
| component | `text-size` | range, unit `px` | |

A choice is `{"id", "label", "type": "choice", "options": [...], "default"}` where each option is a string or `{"value", "label"}`. A range is `{"id", "label", "type": "range", "min", "max", "step", "unit", "default"}` with real numbers (text and `true` are refused) and a default on the step grid. A toggle has a `default` of `true` or `false`.

Tweaks apply to every option at once, so the comparison stays fair.

## 4. The result that comes back

The Result view offers the same session in two forms. Either can be pasted back, and `scripts/parse_choice.py` turns both into the same object.

Short text:

```
=== sample-picker choice v1 ===
picker: notes-theme@1
kind: theme
status: final
chosen: sage-desk
chosen-name: "Sage desk"
control: density = "compact"
control: text-size = 16
shortlist: warm-paper, sage-desk
rejected: slate-night
note: sage-desk = "Like the colour, not the weight of the buttons."
fact: "heading, body text contrast" = 13.1
saved: 2026-10-09T02:03:04Z
=== end ===
```

JSON, which is also the saved session:

```json
{"app": "sample-picker", "schema": 1, "content_id": "notes-theme@1", "saved_at": "2026-10-09T02:03:04Z",
 "data": {"kind": "theme", "status": "final", "chosen": "sage-desk", "chosen_name": "Sage desk",
          "controls": {"density": "compact", "text-size": 16}, "shortlist": ["warm-paper", "sage-desk"],
          "rejected": ["slate-night"], "notes": {"sage-desk": "..."}, "facts": [{"label": "...", "value": 13.1}]}}
```

- `status` is `final` when an option is chosen, otherwise `in progress` with `chosen: (none)`.
- `facts` are measured in the person's browser, on the chosen option drawn alone at the width the detail view gives it, with the final tweaks. They belong to that device and width: characters per line on a phone are not characters per line on a desktop. `parse_choice.py` does not re-measure them.
- Check a result against the picker it came from with `--picker`. A result for another picker or another version, an option id the picker lacks, or a tweak value the control does not allow is an error.

## 5. The page itself

- Views: Options (one card per option), Compare (two or three shortlisted options on the same content; on a narrow screen one at a time, switched by large tabs above the bar), a detail view per option (tweaks, Choose this, a note, the measured facts), Result, and Page (the page's own theme, text size and card layout, loading a saved session, clearing with undo).
- The session (shortlist, ruled out, choice, tweaks, notes) is saved after each change: host storage if the page finds one, then the browser's own storage, then memory. The page says which. In a sandboxed frame nothing is stored and the page says so; the Result view is then the only way to keep the work.
- Loading a saved session checks it first. A file from another tool, a newer schema, malformed JSON and an empty paste are refused with the session left as it was. A session from another picker asks before loading.
- `picker.html#solo=OPTION-ID` shows one option's sample alone, with no page chrome, for screenshots and for measuring with an outside tool.
