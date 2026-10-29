# Functional elements

## Formulas
- Aggregation: SUM, AVERAGE, COUNT and their IF variants.
- Logic: IF, IFS, SWITCH.
- Lookups: XLOOKUP or INDEX-MATCH in preference to VLOOKUP.
- Dates: DATE, YEAR, MONTH, EDATE.
- Errors: IFERROR around anything that can return #N/A or #DIV/0!.
- Dynamic arrays (FILTER, SORT, UNIQUE) only if the file will be opened in a current Excel; otherwise use classic formulas.

## Data validation
- Drop-down lists for controlled fields, sourced from the Lookup sheet.
- Number and date ranges.
- Input messages and error alerts.

## Conditional formatting
- Red, amber, green for KPIs (also add a text flag so colour is not the only signal).
- Data bars for comparison.
- Highlight rules for over budget, overdue and flagged rows.

## Charts
- Line for trend, bar for comparison, scatter for correlation, pie only for few-part composition.
- Title each chart with its conclusion or subject, label axes, place on the dashboard or beside the data.
- Charts must reference the ranges so they update when data changes.

## Named ranges
Use for key inputs and assumptions, so formulas read `=Revenue-COGS` rather than `=B12-B23`.

## Protection
Lock formula cells, leave input cells editable, protect sheets with a note on how to unprotect (blank password unless he asks for one).

## Layout and formats
- Auto-sized columns, frozen header rows, data ranges as Tables.
- Number formats: `#,##0.00` currency, `0.0%` percentages, ISO or locale dates (Australian dd/mm/yyyy by default).
- Colour: light blue `#DDEEFF` input cells, white calculated cells, light grey `#F5F5F5` headers and labels. Professional, not garish.

## Final checklist
- [ ] Input cells identifiable by colour or label
- [ ] Formula cells locked
- [ ] No hard-coded values inside formulas
- [ ] Error-prone formulas wrapped in IFERROR
- [ ] Headers frozen
- [ ] File opens without errors and values were recalculated or the limit stated
- [ ] Charts update when data changes
