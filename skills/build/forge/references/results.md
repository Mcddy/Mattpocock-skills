# The result contract

Every forge check reports the same five statuses, so a result is never mistaken for one it is not. The status comes from what ran, never from what was expected.

| Status | Meaning | Is it a pass? |
|---|---|---|
| **completed** | Every applicable check ran, none failed, and coverage was complete | Yes, for what the tool checks and nothing more |
| **failed** | At least one check ran and failed | No |
| **partial** | Nothing failed, but coverage is incomplete: an applicable check did not run, or something in scope could not be checked (text over an image, a target needing a human exception decision, a composite item whose keyboard path could not be shown, no steps given) | No. The receipt names what was not covered |
| **runner_error** | The tool could not do its job (a missing dependency, no browser, a crash, a server that would not start, a version mismatch), or its receipt file could not be written | No. Nothing it would have checked is known, or the result was not delivered |
| **usage_error** | The command was wrong (bad arguments, a missing file, `--receipt` with no path) | No. Fix the command and rerun |

**Not applicable is narrow.** Only something the criterion itself exempts counts (WCAG exempts disabled controls from contrast). Something the tool cannot measure is missing coverage, and makes the run partial.

## Receipts

Every check prints one line on stderr as its last act, whatever happened, including a crash, a missing package or a usage error:

```
RECEIPT {"tool": "contrast_check", "version": "forge 3.3.2", "status": "partial", "exit": 3, "measured": 31, "below_threshold": 0, "not_measured": 2, "not_measured_reasons": ["over an image or gradient"], ...}
```

`--receipt FILE` also writes that line to a file. If the file cannot be written:

- the product result is kept as `product_status` and `product_exit`;
- the reason goes in `receipt_error`;
- the run as a whole becomes `runner_error`, exit 4, because a result nobody can read back has not been delivered.

`--help` and `--version` print no receipt.

The facts in a receipt come from the run's own data, never from defaults. Where a tool cannot state something, the receipt leaves it out or says so.

| Tool | What its receipt records |
|---|---|
| `render_gate.py` | page, state, counts of pass, fail and warn, the ids that failed and the ids not run, the results file |
| `contrast_check.py` | page and state; text measured, below threshold and not measured; why text went unmeasured; lowest ratio; the criterion |
| `dead_controls.py` | Controls: found, activated, external links not followed, absent on a fresh load, could not be clicked, over the limit, no effect. The click-effect scan: candidates clicked, MOUSE ONLY, reached through a composite widget, UNRESOLVED. Keyboard activation: CLICK ONLY count and how many were not tested |
| `target_size.py` | source, target count, counts by verdict, targets needing an exception decision, overlapping targets, the criterion |
| `delivery_check.py` | page, number of steps, passes and failures in the tab, the frame result (or why it did not run), forms blocked, modes, outside requests blocked |
| `api_check.py` | base address, steps total and passed, steps failed, steps not run, steps not reached, whether the check started the server |
| `ui_candidates.py` | files scanned, defects and candidates by rule; completed means the scan ran, and defects fail the run only with `--fail-on-defect` |
| `design_page.py` | source, page written and its SHA-256, what the page contains, diagrams drawn, diagrams with errors, diagrams shown as source only and why |
| `direction_board.py` | the directions read back from this run's own marked payload, in order; their count; whether they match the request and the default sixteen; whether the page was packed in; the SHA-256 of the board and of the packed page; whether captures ran |

## Exit codes

| Tool | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| `render_gate.py` | completed | failed | usage error | partial (axe-core missing, or composite items unresolved: R9b) | runner error |
| `contrast_check.py` | completed | failed (measured text below threshold) | usage error | partial (text not measured, or nothing measured) | runner error |
| `dead_controls.py` | completed (candidates listed, to be read) | | usage error | partial (UNRESOLVED composite items, unclickable controls, listed controls absent on a fresh load, controls over `--limit`, or nothing activated) | runner error |
| `target_size.py` | completed | failed (with `--fail-on-unresolved`) | usage error | partial (exception decisions needed, including a possibly-inline link whose inline exception is not established; overlaps; or no targets) | runner error |
| `delivery_check.py` | completed | failed (a step failed, or a form submission was blocked) | usage error | partial (no steps given) | runner error |
| `api_check.py` | completed | failed (a step failed) | usage error | partial (some steps did not run) | runner error (the server did not start) |
| `ui_candidates.py` | completed (scan ran) | failed (with `--fail-on-defect`) | usage error | | runner error |
| `design_page.py` | completed (every diagram drawn) | failed (a diagram has a syntax error) | usage error | partial (page written, diagrams shown as source) | runner error |
| `direction_board.py` | completed (with `--live-only`: live board written, captures not requested) | | usage error | partial (live board written, captures could not run) | runner error |

Any tool also exits 4 when its `--receipt` file cannot be written; see above.

The converters (`single_file.py`, `embed_fonts.py`, `make_icon.py`) are not checks and print no status. Exit 0 means the file was written, 2 a usage error, 4 that it could not run. A converter's success says nothing about whether the page works.

## Keyboard reach and activation

- **`tabindex="-1"` is not a fault in itself.** Composite widgets (radio groups, tab lists, listboxes, menus, trees, grids, toolbars) keep one Tab stop and move between items with arrow keys, using roving tabindex or `aria-activedescendant` (W3C ARIA APG, "Developing a keyboard interface").
- **How the checks test it.** `dead_controls.py` and `render_gate.py` focus the widget's Tab stop and press the arrow keys:
  - reached: OK;
  - not reached: UNRESOLVED, and the run is partial;
  - no Tab stop and no composite path: MOUSE ONLY (dead_controls) or an R9 failure (render_gate).
- **Activation keys follow the role.** Enter for links. Enter and Space for buttons. Space for checkboxes, switches and radios (APG makes Enter optional for a switch). Enter for menu items.
- **Movement is checked separately from activation.** Moving through a radio group with arrows is navigation, and comes under reach. Tabs are not tested for activation, because whether they activate on focus or on a key is a design choice.
- **An observable change is not success.** Background requests alone do not count as a key doing what the click did. Even a counted change only shows something happened, not that the promised action worked: that is what the flow steps (`delivery_check.py`) prove.

## Reporting

- Copy the status word into the report beside the command. Do not paraphrase partial as "mostly passed" or runner_error as "skipped".
- A board written with `--live-only` is written, not rendered, until someone opens it and looks at every direction.
- A tool that rejects a flag used in `SKILL.md`, or prints a version other than forge 3.3.2, is a version mismatch. Report runner_error, name the mismatch, and hold that check. Do not drop the flag to make it run.
- Planted faults prove a check can fail. A run that has never failed has not been shown to work. Keep one known-good page (a positive control) and one known-bad page with each check you rely on.
