# The two files

`events.csv` holds one event per row. `sources.csv` is in the research ledger's sources format, so a ledger's file can be used as it is. Both are UTF-8 CSV with a header row. `scripts/chronology_check.py` validates them; `scripts/build_timeline.py` refuses to build from files that fail. Templates with one example row for each case are `assets/events-template.csv` and `assets/sources-template.csv`.

## events.csv

| Column | Holds | Rule |
|---|---|---|
| `event_id` | A short id | Starts with a letter; letters, digits, hyphen, underscore. Unique |
| `date` | The date as the source gives it | See below. Blank only for `undated` |
| `date_precision` | `day`, `month`, `year`, `approx` or `undated` | Must match how the date is written |
| `end_date` | Optional end of something that lasted | A date in any of the three forms; not before the start |
| `time` | Optional clock time | `HH:MM` then a zone: `UTC`, `Z`, an offset like `+02:00`, or `local`. Only on a `day` date |
| `title` | What happened, in a few words | Not empty. Two rows for one event share a title |
| `detail` | Anything a reader needs | For an ASSESSMENT or an `approx` date, the basis |
| `actors` | Organisations and public roles | List separated by semicolons |
| `source_id` | One or more ids from `sources.csv` | List separated by semicolons. Several only when they agree on the date and its precision |
| `locator` | Where in the source the date is given | Required for a FACT |
| `status` | `FACT`, `REPORTED` or `ASSESSMENT` | See below |
| `conflicts_with` | Ids of rows that date the same event differently | `E07` or `E07:class`; list separated by semicolons |
| `tags` | Free labels for filtering | List separated by semicolons |

### How a date is written

One representation, enforced: the text of the date carries its precision.

| Precision | Written | Shown as | Possible range used for comparisons |
|---|---|---|---|
| `day` | `2024-03-19` | 19 Mar 2024 | That day |
| `month` | `2024-03` | Mar 2024 | 1 to 31 March 2024 |
| `year` | `2024` | 2024 | 1 January to 31 December 2024 |
| `approx` | any of the three | about 19 Mar 2024, about Mar 2024, about 2024 | A day widened by 15 days each side (`--approx-days`); a month by one month each side; a year by one year each side |
| `undated` | blank | Undated | None. Never placed, never compared |

A `month` row written `2024-03-01` is an error, as is a `year` row written `2024-01`. The convention of writing the first of the month and remembering that it means the month is exactly how a day gets invented, so it is not offered.

The widths for `approx` are a convention for deciding what the checker will call decided. They are not a claim about the source. If the source supports a narrower or wider window, say so in `detail` and set `--approx-days`.

Dates are real calendar dates. `20240319`, `19/03/2024`, `2024-3-19` and `2024-02-30` are refused.

### Status

| Status | Means | Needs |
|---|---|---|
| `FACT` | An opened source of secondary tier or better gives this date | A locator, and at least one cited source with tier `primary`, `peer_reviewed` or `secondary` and read level `full` or `section` |
| `REPORTED` | A source says so; not confirmed against a better one, or the source is weak or was not opened | A source |
| `ASSESSMENT` | The writer's inference | A source, or the basis in `detail` |

### Conflicts

When two sources date one event differently, record two rows and put each row's id in the other's `conflicts_with`. The checker refuses a conflict recorded on one row only. Classes:

| Class | Means | The checker |
|---|---|---|
| `precision` | One date sits inside the other: "March 2024" and "18 March 2024" | Refuses it if the two ranges do not overlap |
| `timezone` | One moment written as two local dates | Refuses it if both rows record a time with an offset and the instants differ, or if the dates are more than a day apart. Otherwise says it cannot confirm |
| `announcement` | One source dates the decision, signing or announcement; the other dates the publication, entry into force or occurrence | Does not judge. Say in `detail` which is which, and that this is your reading |
| `disagreement` | The sources give incompatible dates and nothing read explains it | Notes it if the dates are in fact compatible |
| none | Not yet classified | Says what the dates allow |

Disagreements and unclassified pairs are the open conflicts. They are listed in the reading and coloured as open in the viewer.

If both the decision and the publication matter, they are also two separate events with their own titles. The conflict rows record that a source put the wrong label on one of the dates.

## sources.csv

`source_id, title, publisher, address, tier, published, accessed, read_level, family, notes`

- `tier`: `primary` (the original record), `peer_reviewed`, `secondary` (a named publisher's account), `aggregator` (collected or rewritten material), `unverified` (origin cannot be established).
- `read_level`: `full` or `section` mean the source was opened and read; those count for a FACT. `abstract`, `snippet` and `not_opened` do not. Any other value draws an advisory and is treated as not opened.
- `published` and `accessed`: blank or `YYYY-MM-DD`. An opened source needs an access date.
- `address` may be blank; the checker notes it, because a reader cannot follow it.

## What the checker reports

Errors (exit 1): any rule above; ids that do not resolve; a `--before` assertion the dates contradict.

Advisories: unclassified or doubtful conflicts; rows with the same title and different dates that are not marked as conflicting; events resting only on sources below secondary tier; sources with no address or never cited; events dated after `--today`; pairs whose recorded instants run against their written order; `--before` assertions that cannot be decided.

### Order

Events are listed by the earliest day the written date could be. On a tie the less precise date comes first, then an untimed event before a timed one, then clock time as written, then file order. An approximate date is listed at the date written.

The listing has to put an imprecise date somewhere. Where it lands is not a finding. "Mar 2021" is listed before "10 Mar 2021" and the checker will still answer UNDECIDED if asked which came first.

### Sequence checks

`--before A B` asserts that A preceded B, by start dates.

| Verdict | When |
|---|---|
| HOLDS | The latest A could be is before the earliest B could be. If both are day-precision dates one calendar day apart with no zone on both, a note says it holds only if both dates are in one zone |
| VIOLATED | The latest B could be is before the earliest A could be |
| UNDECIDED | The ranges overlap, an event is undated, or both fall on one day without a time and zone on both |

Where both rows record a time with an offset, instants are compared and the written dates are ignored.

### Gaps

A gap is a stretch in which no listed event can fall: from the latest day any earlier event could be (its end date included) to the earliest day any later one could be. A year-precision event therefore closes every gap inside its year, because it could have happened on any day of it. Gaps longer than `--gap-days` are listed as "at least" their certain length.

## What the scripts cannot tell

Whether a source says what a row claims, whether two rows describe one event, whether a gap matters, and why anything happened.
