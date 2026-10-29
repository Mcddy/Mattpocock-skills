# chronology examples

Made by the session that wrote the skill, by following its procedure. Nobody else has run them. Paths below are relative to the skill folder.

## standard-adoption-timeline

Thirty events about the EU accessibility standard EN 301 549 and the two directives it supports, 2014 to 2026.

**Where the facts come from.** Nothing here is invented. Each row is either a fact recorded in the research ledger this example was seeded from (the EU accessibility standards ledger from the deep-research-orchestrator skill, dated 8 October 2026) or was read from the named source with a page fetch on 9 October 2026. `sources.csv` says, source by source, what was actually read, and where a fetch returned only part of a page. Rows that rest on a secondary account, or on a date the source gives only loosely, are marked REPORTED. No instruction-like text was found in any fetched page.

| File | What it is |
|---|---|
| `events.csv`, `sources.csv` | The timeline: 30 events (29 dated, 1 undated), 13 sources |
| `check-output.txt`, `check-output.json` | `chronology_check.py` on the two files: 0 errors, 5 conflict pairs, 3 gaps over 365 days. Exit 0 |
| `sequence-output.txt` | The same run with six `--before` assertions: 3 hold, 1 violated, 2 cannot be decided. Exit 1, because one assertion is contradicted by the dates. That is the finding, not a fault in the data |
| `build-output.txt` | Output of `build_timeline.py` |
| `timeline.html` | The built viewer. Open it in a browser or a chat preview |
| `journey-steps.txt` | 55 steps for interface-architect's `delivery_check.py`: filter, open an event, follow a conflict, show gaps, export, change the display |
| `reading.md` | The written reading |

What the example shows:

- **Month, year and approximate precision from real sources.** "EN 301 549 V3.2.1 (2021-03)" on the standard's cover is recorded as `2021-03`. "First published in 2014" is `2014`. "Last summer", in a note dated 18 September 2026, is `approx` on `2025-07`.
- **Three precision-compatible pairs** (E15 and E16, E24 and E25, E27 and E28).
- **One real date disagreement** (E18 and E19): 12 against 18 August 2021, the second from a Commission page that contradicts its own table.
- **One announcement-against-occurrence pair** (E07 and E08).
- **An undecidable sequence that looks obvious** (E13 and E14): adoption on 10 March 2021 against publication in "March 2021".

Because the real material has a real disagreement, no synthetic conflict example was added.

Regenerate:

```
python scripts/chronology_check.py examples/standard-adoption-timeline/events.csv examples/standard-adoption-timeline/sources.csv --gap-days 365 --today 2026-10-09
python scripts/chronology_check.py examples/standard-adoption-timeline/events.csv examples/standard-adoption-timeline/sources.csv --gap-days 365 --today 2026-10-09 --before E05 E06 --before E13 E14 --before E14 E17 --before E20 E21 --before E22 E26 --before E28 E24
python scripts/build_timeline.py examples/standard-adoption-timeline/events.csv examples/standard-adoption-timeline/sources.csv --out examples/standard-adoption-timeline/timeline.html --title "EN 301 549 and EU accessibility law: adoption timeline" --gap-days 365
```

The build is deterministic: the same inputs give the same bytes.

Check the built page in a tab and in a sandboxed frame, if interface-architect's scripts are to hand:

```
python delivery_check.py examples/standard-adoption-timeline/timeline.html --steps examples/standard-adoption-timeline/journey-steps.txt --width 390 --height 844
```

The steps open the filters with a click, which is right at a phone width where they start closed. At 960 pixels and wider the filters start open, so run the steps at 390.
