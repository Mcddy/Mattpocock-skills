---
name: chronology
description: "Builds a sourced timeline from documents and notes, with each date as precise as its source, date conflicts and gaps kept visible, and a single-file viewer. Use for build a timeline of, what happened when, chronology of, sequence of events, put these events in order. Not for explaining why events happened (intelligence-analyst), gathering the sources (deep-research-orchestrator), a concept map (atlas) or project scheduling."
metadata:
  revision: "1.0.0"
---

# Chronology: what happened when, as far as the sources say

Analysis of events rests on order and timing. Sources give dates at different precisions and sometimes disagree. This skill builds a timeline that keeps what each source said: one event per row, its date written exactly as precisely as the source gives it, its source and locator, and conflicts and gaps left visible. It delivers two CSV files, a checker's findings, a single-file viewer and a short reading.

The skill is instructions, three scripts and one page. It does not find sources and does not explain causes.

## Use when

- "Build a timeline of", "what happened when", "chronology of", "sequence of events", "put these events in order".
- A narrative makes claims about order ("the warning came before the decision") that should be checked against dated sources.
- Sources disagree about when something happened and the disagreement needs to be laid out.

## Not this skill

| The job | Use |
|---|---|
| Why the events happened; which explanation fits | intelligence-analyst |
| Finding and reading the sources | deep-research-orchestrator |
| Whether the claims in a draft are true | fact-check |
| What happens next | oracle |
| What changed since last week on a standing topic | sitrep |
| How ideas relate, with no dates | atlas |
| A project plan with tasks and deadlines | a planning tool; this skill records what happened |

## Inputs

- The material: documents, notes, pasted text, or a research ledger's sources file.
- What the timeline is for: the period, and any claims about order that matter.
- Nothing else is needed to start. Build the first version without a round of questions.

## Tools: discover first

- **File reading**, for the material.
- **A shell with Python 3**, for `scripts/chronology_check.py` and `scripts/build_timeline.py`. Without one, apply the rules in `references/event-format.md` by hand, deliver the events as a table in the reply with no viewer, and say it was done by hand.
- **Search and page reading**, only to confirm a specific date the user asks to have confirmed. Gathering sources is another skill's job.
- **A browser with Playwright**, only for someone changing the viewer: `scripts/test_timeline.py`. It is not needed to build a timeline.

## Procedure

1. **Set the scope.** Subject, period, and the order questions the timeline should answer. Public events, organisations and people in a public role only.
2. **Register each source** in `sources.csv`, starting from `assets/sources-template.csv`: tier, how much was read, when.
3. **Extract events one at a time**, each from one place in one source, into `events.csv` (start from `assets/events-template.csv`). Write the date exactly as precisely as the source does:

   | The source says | date | date_precision |
   |---|---|---|
   | 19 March 2024 | `2024-03-19` | `day` |
   | March 2024 | `2024-03` | `month` |
   | in 2024 | `2024` | `year` |
   | about three weeks after a dated event | the resolved date | `approx` |
   | no date | blank | `undated` |

   "March 2024" is never `2024-03-01`. Never fill in a day or a month.
4. **Separate what happened from when it was reported or announced.** If both matter, they are two events with two titles.
5. **The same event with two dates is two rows**, each listing the other in `conflicts_with`. Do not choose. Classify the pair: `precision` (one date sits inside the other), `timezone`, `announcement` (one source dates the decision or announcement, the other the occurrence) or `disagreement`.
6. **Set each status.** FACT needs a locator and an opened source of secondary tier or better. Otherwise REPORTED. A date the writer worked out is ASSESSMENT, with the basis in `detail`.
7. **Do not hide dated events in `detail`.** A date mentioned only in another row's detail is invisible to the gap check and can produce a gap that is not there.
8. **Run the checker**: `python scripts/chronology_check.py events.csv sources.csv --gap-days N`. Fix errors. Read advisories. Choose N to fit the tempo of the material and say what was chosen.
9. **Test the order claims**: add `--before A B` for each claim that A preceded B. HOLDS and VIOLATED are decided by the dates. UNDECIDED means the recorded precision cannot settle it; report it as that, not as a guess.
10. **Read the timeline** for what it shows: sequences that matter (a cause must precede its effect), gaps where events would be expected, clusters, and anything the narrative asserts that the order contradicts. These observations are ASSESSMENT. See `references/reading-a-timeline.md`.
11. **Deliver.** For a handful of events, a table in the reply is enough: no viewer. Otherwise run `python scripts/build_timeline.py events.csv sources.csv --out timeline.html --title "..." --gap-days N` and hand over the page, both CSV files and the reading, with open date conflicts listed.

## Failure branches

- **No shell.** Apply the rules by hand, deliver a table, say so. Do not describe a viewer that was not built.
- **Undated material.** Record it as `undated`. It is listed apart and never placed by guess.
- **Relative dates.** "Three weeks later" is resolved only if its anchor is dated, and the result is `approx`. If the anchor is undated, so is the event.
- **Time zones.** Record the time with the zone the source used, or `local` if it names none. The checker converts only to compare two instants, and says so; the viewer shows each time as recorded. Two rows a day apart with no zones recorded may be one moment.
- **Few events.** Under about eight, answer with a table. The viewer adds nothing.
- **A private individual is the subject.** Decline. Public events, organisations and public roles only. No timeline of a private person's movements, posts or contacts.
- **The request is for causes.** Build the order, then name intelligence-analyst for the explanation. Order is evidence about cause, not a finding of it.
- **The sources are missing.** Say what would be needed, or name deep-research-orchestrator. Do not date events from recall.
- **Ways this skill goes wrong:**
  - filling in a day so the row sorts neatly;
  - merging two sources' dates into one row with the likelier date;
  - reading sequence off the listing. The list has to put a month-precision event somewhere; that position is not a finding;
  - calling a gap "nothing happened". A gap is where nothing was recorded;
  - treating the viewer as the deliverable. The CSV is the record; the page is a view of it.

## Output

The first line names the method: "Chronology, dates as precise as their sources", then the count of events, sources and open conflicts.

Then: the reading (sequences that hold, claims the dates contradict, what cannot be decided at the recorded precision, gaps, clusters), each observation marked ASSESSMENT; the open date conflicts, each with both dates and both sources; undated items; what was not established. Then the files: `events.csv`, `sources.csv` and, unless the timeline is small, the built page.

The viewer shows precision in the date itself ("Mar 2024", "2021", "about 12 Jun 2023"), pairs conflicting events on both rows, shows source and locator on every event, filters by tag, actor, status and source tier, shows gaps as labelled breaks, searches, and exports the current view as markdown and CSV. It keeps no work of the reader's; only display settings are stored, and it says where.

## Rules that always hold

- A date is never made more precise than its source.
- Conflicting dates are two rows, never one chosen date.
- Undated events are never placed.
- The listing order is not a sequence claim. Only a date comparison is, and it says UNDECIDED when precision cannot settle it.
- Every event has a source and locator, or is marked ASSESSMENT with its basis.
- A FACT has a locator and an opened source of secondary tier or better.
- A gap is an absence of record, not a record of absence.
- No private individuals.

## What has and has not been tested

Everything below is an author-side check: run locally by the session that wrote the skill, then rerun on 9 October 2026 by a second session. Nobody outside that authoring side has tested the skill.

- `scripts/test_chronology.py`: 34 named tests of the checker and builder, all passing, each refusal beside its valid neighbour. With `--mutants`, 11 planted faults (among them: a month treated as its first day so that a false "A precedes B" is reported; a day accepted on a month-precision date; a one-sided conflict accepted) were each caught by the test named for it.
- `scripts/test_timeline.py`: 19 named tests of the viewer in headless Chromium, each run in a tab and in a frame with `sandbox="allow-scripts"`, all passing. With `--mutants`, 7 planted faults (among them: the conflict pairing dropped; a month shown as the first of the month; gaps measured from the first day of an imprecise date) were each caught.
- By hand, 44 runs of `chronology_check.py` and 15 of `build_timeline.py` on good, bad and edge inputs: an unknown option, a missing value, a byte-order mark, an empty file, invalid UTF-8, NUL bytes, `20240214`, 30 February, a month written as a day, a time with no zone, a one-sided conflict, a FACT on a weak or unopened source. Every refusal had its valid neighbour beside it, exit codes were as documented, none produced a traceback, and a refused build wrote no file.
- On a 30-event timeline whose dates were read from their sources on 9 October 2026 (the dates of fourteen of the events were read again from their sources by the second session, all matching): the interface-architect tools `delivery_check.py` (55 steps: filter, open an event, follow a conflict, show gaps, export, change display; all passed in the tab and in the frame at a 390 pixel viewport), `contrast_check.py` in all four themes with filters, gaps, an open event and the export panel showing (310 text elements each, none below AA, lowest ratio 6.09), `target_size.py` at 390 (46 of 46 meet 24 by 24), and `dead_controls.py` at 390 (45 of 45 controls had an effect). A separate measurement found no interactive element under 44 by 44 pixels at 360, 390 and 1280 wide, and no sideways overflow.
- On a second, 15-event synthetic timeline written by the second session: the checker, six `--before` claims (3 hold, 3 undecided), a built page, a 47-step journey of its own in the tab and the frame, and the field error, no-results and bad-data states measured for contrast in all four themes (lowest ratio 6.09). Screenshots at 390 and 1280 were looked at by both sessions; the first changed the layout because of them, the second found nothing to change.
- A 600-event synthetic timeline renders and filters at a 390 pixel viewport (one of the 19 viewer tests).

Not tested: any model following this skill other than the session that wrote it; any real host's preview. Also not tested: a physical phone; a screen reader; printing; timelines beyond 600 events; the clipboard succeeding (in the sandboxed frame it is refused and the fallback was exercised); the host storage object beyond a stub with asynchronous get and set; dates before year 1 or in other calendars, which the checker refuses. The research ledger's own checker was not read, so the read levels accepted here (`full` and `section` count as opened) were inferred from its sample files.

## Acceptance cases

The full set, with negative controls and input files, travels with the source for review.

1. A folder of notices and press reports with "build a timeline". Expect: one event per row with source and locator; a source that says "March 2024" recorded as month precision and shown as "Mar 2024"; two sources with different dates for one event kept as two rows marked on both; the checker run; a built page; a reading with open conflicts listed.
2. "The report says the warning came before the decision. Check that." with the warning dated to a month and the decision to a day in that month. Expect: UNDECIDED, with the reason that the month does not say which day; no claim either way.
3. Three dated events pasted in a message. Expect: a table in the reply, no viewer, and the same precision rules.
4. Negative control: "Why did the regulator change course?" Expect: intelligence-analyst leads; at most an offer to put the dated events in order first.
