# Extracting events and reading the result

## Extracting

Work through one source at a time. For each dated statement:

1. **Name the event.** One thing that happened, in a few words. "Notice published", not "the closure".
2. **Find what exactly the source dates.** The decision, the signing, the announcement, the publication, the entry into force, the thing taking place, or the report about it. These are different events. A press report dated the 6th about a notice issued on the 4th supports "reported on the 6th", and supports "issued on the 4th" only if it says so.
3. **Copy the precision, not more.** Check the source's own wording: "in early March" is `approx` on `2024-03`, not a day.
4. **Record the locator:** page, paragraph, article, table row, or a quoted phrase a reader can search for.
5. **Check whether the event is already in the file from another source.** Same date and precision: add this source to the row. Different date or precision: a second row, linked both ways.

### Traps

| Trap | What to do |
|---|---|
| A date format that could be read two ways (03/04/2024) | Find a date in the same source that can only be read one way, and say in `detail` how the format was settled. If none exists, record both readings as an open conflict or mark `approx` on the month |
| A version label that carries a month ("V3.2.1 (2021-03)") | That is month precision. A file stamp on a server is a different fact with a different meaning |
| "Last summer", "three weeks later", "the following quarter" | Resolve only from a dated anchor. Mark `approx`. Put the wording and the anchor in `detail` |
| A source that corrects itself, or says two things | Two rows from the same source, as a conflict. A source can disagree with itself |
| A date that appears only in passing in another row's detail | Give it its own row if it falls where a gap would otherwise be reported |
| A scheduled future date | Record it, tag it, and run the checker with `--today` so it is flagged as not yet happened |

## Reading

Run the checker first, then read the listing under these headings. Each observation is an ASSESSMENT: say how sure, and on what.

**Sequences that matter.** List the claims in the narrative that depend on order and turn each into a `--before` assertion. A cause must precede its effect; a response must follow what it responds to; a party cannot have known something before it existed. Report HOLDS with the two dates, VIOLATED as a contradiction of the narrative, and UNDECIDED as exactly that, with the precision that would be needed to settle it.

**Gaps.** Look for long stretches with nothing recorded where events would be expected. A gap can mean nothing happened, that it happened out of public view, or that the sources read do not cover it. Say which sources would show which. Do not report a gap that a known but unrecorded date would fill: record that date.

**Clusters.** Several events close together often share a trigger. Name the cluster and the candidate trigger; leave the causal claim to an analysis that tests it.

**Conflicts.** For each open conflict: both dates, both sources, the tier of each, and what would settle it. Do not settle it by tier alone. A primary record of the wrong event is still the wrong event.

**What the precision hides.** If an important ordering rests on a month or a year, say so, and say which source might give the day.

## Writing the reading

Lead with the answer to the question the timeline was built for. Then, briefly:

1. What the order shows, with event ids and dates.
2. What the narrative asserts that the dates contradict.
3. What cannot be decided at the recorded precision.
4. Gaps, with the threshold used.
5. Open date conflicts.
6. Undated items, and what was not established.

Keep it to a screen. The detail is in the files.

### A short sample

SYNTHETIC, to show shape.

> **Chronology, dates as precise as their sources.** 19 events from 6 sources, 2023 to 2025. 2 date conflicts open, 1 undated.
>
> - **The closure followed the survey** (ASSESSMENT, high confidence). The survey report reached the council on 14 Feb 2024 (B03, minutes); the closure notice is dated 4 Mar 2024 (B04, register).
> - **Whether the ferry started before the bridge closed cannot be decided.** The ferry is dated only as about 8 Apr 2024, from a forum post counting three weeks from the closure (B08). The post is the only source, and it is unverified.
> - **One gap over 90 days:** at least 241 days after 3 Oct 2024 with nothing recorded. The council minutes for that period were not read.
> - **Open conflicts.** The bridge reopened on 9 Sep 2024 by the authority's notice (B12, primary) and on 16 Sep 2024 by the freight digest (B13, aggregator). The digest is weekly; 16 Sep may be its issue date. The subsidy payment is dated 17 Jun 2025 by the forum (B15) and 1 Jul 2025 by the minutes (B16), not yet classified.
> - **Undated:** the noise complaint (B17).

## Small timelines

Under about eight events, answer in the reply with a table: date as written, event, status, source and locator. Apply the same precision rules. List conflicts under the table. Skip the viewer.

## The viewer

`scripts/build_timeline.py` writes one HTML file with the data inside it. It makes no outside requests and works in a sandboxed chat preview. Things to tell the user:

- The page is a view of the CSV. To change an event, change the CSV and build again.
- Filters, search and the gaps toggle change what is shown; the export follows the view.
- Gaps shown under a filter are gaps in that filtered view, and the page says so.
- Display settings (theme, spacing, text size, date style, scrolling) are kept by the host, the browser, or for the visit only. The page says which.
- Links to sources open in a new tab where the host allows it. The address is also shown as text.
