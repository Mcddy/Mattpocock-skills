---
name: spreadsheet-intelligence
description: >
  Expert skill for building intelligent, functional Excel/spreadsheet files (.xlsx) — not just tables, but working tools with formulas, named ranges, conditional formatting, charts, and structured data models. Use whenever the user wants a spreadsheet that does something: financial models, trackers, calculators, dashboards, budget tools, trading journals, KPI trackers, P&L sheets, or any .xlsx that needs to be more than static data. Trigger on: "build me a spreadsheet for...", "create an Excel file that...", "make a tracker for...", "I need a financial model...", "build a budget spreadsheet...", "create a trading journal in Excel...", "make a calculator for...", "I need a dashboard in Excel...", or any request for a functional .xlsx deliverable. Also trigger when the user uploads a broken spreadsheet and wants it fixed or enhanced. Never produce a table in chat when an actual working spreadsheet file is the right deliverable.
---

# Spreadsheet Intelligence

Builds functional, intelligent Excel files — tools that calculate, track, visualise, and model, not just store data.

---

## Core Principle

A spreadsheet is not a table with a file extension. It is a **computational tool**. Every .xlsx this skill produces should contain logic, not just layout.

---

## Phase 1: Intake

Establish before building:

1. **Purpose** — What should this spreadsheet *do*? (Track, calculate, model, compare, visualise?)
2. **Data inputs** — What goes *in*? (Manual entry, imported data, formulas from other sheets?)
3. **Outputs required** — What should the user *see* or *get out*? (Totals, charts, summaries, flags?)
4. **Scale** — How many rows/sheets/users? Daily use or one-off?
5. **Skill level of the end user** — Will they edit formulas or just fill in highlighted cells?
6. **Any existing data** — Do they have data to load in, or starting from scratch?

---

## Phase 2: Architecture Design

### Sheet Structure Patterns

**Model-View-Data separation (recommended for complex files):**
```
Sheet 1: DASHBOARD     — Summary view, charts, KPIs (read-only cells)
Sheet 2: INPUTS        — User-entry cells only (clearly highlighted)
Sheet 3: CALCULATIONS  — All formula logic (can be hidden)
Sheet 4: DATA          — Raw data tables (structured as Excel Tables)
Sheet 5: LOOKUP        — Reference tables, drop-down sources
```

**Simple tracker (single-sheet):**
```
Header row (frozen)
Data rows (Table format)
Summary section (top or bottom)
```

**Financial model:**
```
Assumptions sheet → Calculations sheet → Outputs/Reports sheet
```

---

## Phase 3: Functional Elements to Include

Always consider which of these the file needs:

### Formulas
- SUM, AVERAGE, COUNT for aggregation
- IF, IFS, SWITCH for logic
- VLOOKUP / INDEX-MATCH / XLOOKUP for lookups
- DATE, YEAR, MONTH, EDATE for date logic
- IFERROR for clean error handling
- Dynamic arrays (FILTER, SORT, UNIQUE) for modern Excel

### Data Validation
- Drop-down lists for controlled input fields
- Number/date range restrictions
- Input messages and error alerts

### Conditional Formatting
- Traffic light (red/amber/green) for KPIs
- Data bars for visual comparison
- Highlight rules for over-budget, overdue, flagged rows

### Charts
- Select chart type based on data: Line (trend), Bar (comparison), Pie (composition — use sparingly), Scatter (correlation)
- Always title charts and label axes
- Place on dashboard sheet or adjacent to data

### Named Ranges
- Use for key inputs and assumption cells
- Makes formulas readable: `=Revenue - COGS` not `=B12 - B23`

### Protection
- Lock formula cells, leave input cells editable
- Add sheet protection with clear instructions

---

## Phase 4: File Generation

→ Read `/mnt/skills/public/xlsx/SKILL.md` before generating. Use openpyxl with proper:
- Column width auto-sizing
- Freeze panes on header rows
- Table formatting (ListObject) for data ranges
- Proper number formats (#,##0.00 for currency, 0.0% for percentages)
- Colour scheme: professional, not garish

**Input cell colour convention:**
- **Light blue (#DDEEFF)** — user input cells
- **White** — calculated cells (locked)
- **Light grey (#F5F5F5)** — headers and labels

---

## Phase 5: Delivery

1. Generate to `/mnt/user-data/outputs/filename.xlsx`
2. Use `present_files` to deliver
3. Explain: what to enter, what calculates automatically, and how to read the outputs
4. Note any limitations or manual steps required

---

## Quality Checklist

- [ ] All input cells are clearly identifiable (coloured or labelled)
- [ ] Formula cells are locked / protected
- [ ] No hardcoded values in formulas (use named ranges or input cells)
- [ ] IFERROR wraps any formula that could show #N/A or #DIV/0!
- [ ] Headers are frozen
- [ ] File opens without errors
- [ ] If charts exist, they update when data changes
