# Routing check: spreadsheet-intelligence

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of the registry skills and the likely winner recorded.

## Should trigger spreadsheet-intelligence

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Build me a trading journal in Excel with win rate and expectancy." | spreadsheet-intelligence | |
| 2 | "Make a budget spreadsheet for my sole trader income and GST." | spreadsheet-intelligence | |
| 3 | "Create an Excel calculator for subnet sizing." | spreadsheet-intelligence | |
| 4 | "This workbook has #REF! errors everywhere, fix it." | spreadsheet-intelligence | |
| 5 | "I need a KPI dashboard in Excel for Cerberus subscribers." | spreadsheet-intelligence | |
| 6 | "Make a tracker for my uni assignments with due dates and flags." | spreadsheet-intelligence | |

## Should not trigger spreadsheet-intelligence

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Here is a CSV of sales, find patterns and tell me what drives churn." | data-intelligence | data-intelligence |
| 8 | "Forecast next quarter's subscribers from this monthly series." | series-lab | series-lab |
| 9 | "Build an interactive web dashboard of my trades." | showpiece | showpiece |
| 10 | "Turn these results into a cited report." | folio | folio |

Result: 10 of 10 judged correct. Re-run against a live router before relying on them.
