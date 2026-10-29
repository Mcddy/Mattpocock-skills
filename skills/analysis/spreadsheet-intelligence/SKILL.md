---
name: spreadsheet-intelligence
description: "Builds working Excel files (.xlsx) that calculate, not just store: financial models, trackers, calculators, dashboards, budgets, trading journals, KPI and P&L sheets, with formulas, validation, conditional formatting, charts and protected cells. Also repairs or extends a broken or messy spreadsheet. Use when he says 'build me a spreadsheet for', 'create an Excel file that', 'make a tracker', 'financial model', 'budget spreadsheet', 'trading journal in Excel', 'make a calculator', 'dashboard in Excel', or uploads a spreadsheet to fix. Not for analysing the data inside a file (use data-intelligence), forecasting (series-lab), charts for a report (folio), or a web dashboard (showpiece)."
---

# spreadsheet-intelligence

Produces an .xlsx that is a tool: inputs in marked cells, logic in formulas, outputs on a summary sheet. Formula, validation and layout details are in `references/`.

## Use when

- A tracker, model, calculator, budget, journal or dashboard is wanted as a spreadsheet file.
- An existing workbook is broken, hard-coded or needs new logic.

## Not this skill

| The request | Goes to |
|---|---|
| Analyse, clean or find patterns in a dataset | data-intelligence |
| Forecast a time series | series-lab |
| Fit a predictive model | model-lab |
| Write up findings as a report | folio |
| Interactive web dashboard | showpiece |

## Inputs

1. Purpose: track, calculate, model, compare or visualise.
2. Inputs: manual entry, imported data, links between sheets.
3. Outputs wanted: totals, charts, flags, summaries.
4. Scale and use: rows, sheets, users, daily or one-off.
5. Who edits it: formulas, or only the highlighted cells.
6. Existing data or workbook to load, if any.
7. Where it will be opened (Excel, Sheets, LibreOffice), because dynamic array functions are not universal.

## Procedure

1. **Design the layout before building.** Simple tracker: frozen header, table, summary. Complex file: separate Dashboard, Inputs, Calculations, Data and Lookup sheets. Financial model: Assumptions, then Calculations, then Outputs. Write the sheet list and the main formulas in a few lines.
2. **Pick the functional elements the file needs** from `references/elements.md`: formulas, validation, conditional formatting, charts, named ranges, protection. Include only what serves the purpose.
3. **Build the file.** If the host has an xlsx file skill, use it for file mechanics. Otherwise use openpyxl, with frozen headers, tables for data ranges, proper number formats and the colour convention in `references/elements.md`.
4. **Test it.** Reopen the file and recalculate if a spreadsheet engine is available (LibreOffice headless works); check no cell shows #REF!, #DIV/0!, #N/A or #NAME?. Enter two or three known cases and compare results with hand calculation. If recalculation is not possible, say the file was not recalculated and that openpyxl does not compute values.
5. **Repair mode.** For a broken workbook, copy it first and never overwrite the original. List the faults found (broken references, hard-coded values where a formula belongs, inconsistent formulas down a column, mixed types, volatile or circular logic) before fixing them, then fix and record each change on a Notes sheet.
6. **Deliver** with a short guide: what to enter, what calculates, how to read the outputs, and any manual steps or limits.

## Output

- The .xlsx at a stated path.
- A short how-to (entry cells, automatic cells, reading the results).
- A change list when an existing workbook was repaired.

## Rules that always hold

- Every file contains logic, not just layout. A table with a file extension is not the deliverable.
- No hard-coded numbers inside formulas; use input cells or named ranges.
- Input cells are marked, formula cells are locked, errors are handled cleanly.
- For trading journals and P&L sheets, state the formula assumptions (fees, currency, position sizing basis) on the sheet. They are record-keeping tools, not advice.
- Do not overwrite the user's original file.

## References

- `references/elements.md`: formulas, validation, conditional formatting, charts, named ranges, protection, number formats, colour convention, final checklist.
