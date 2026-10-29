# Routing check: autonomous-writer

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of the registry skills and the likely winner recorded.

## Should trigger autonomous-writer

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Write this week's Cerberus newsletter on the RBA decision, I've got the three lens notes." | autonomous-writer | Borderline with dispatch, but the analysis exists and the ask is the write-up |
| 2 | "Draft sales copy for my prompt pack." | autonomous-writer | |
| 3 | "Write a proposal for a small business that wants a network security review." | autonomous-writer | |
| 4 | "Script for a 3 minute YouTube explainer on VLANs." | autonomous-writer | |
| 5 | "Write a LinkedIn post about finishing my first networking unit." | autonomous-writer | |
| 6 | "Write an executive summary of this report for my manager." | autonomous-writer | Borderline with folio if the report needs rebuilding |

## Should not trigger autonomous-writer

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "This draft reads like AI, fix it without changing the facts." | deslop | deslop |
| 8 | "Build me a 12 slide investor deck." | deck-builder | deck-builder |
| 9 | "Give me a Cerberus brief on gold, scored on the three lenses." | dispatch | dispatch |
| 10 | "Compile these results into a cited report that updates when the data changes." | folio | folio |

Result: 10 of 10 judged correct, with 1 and 6 borderline. Re-run against a live router before relying on them.
