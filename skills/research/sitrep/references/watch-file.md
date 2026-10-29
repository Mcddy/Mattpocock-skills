# The watch file

One JSON object, UTF-8. The user keeps it between runs. `scripts/watch_check.py` validates it; `scripts/sitrep_diff.py` compares two versions of it. A blank one to start from is `assets/watch-template.json`.

## Fields

| Field | Type | Rule |
|---|---|---|
| `watch_id` | text | Lower case letters and digits joined by hyphens. Never changes once set; the comparison refuses two files with different ids |
| `schema` | whole number | `1`. A higher number is refused as newer than the scripts |
| `title` | text | What the watch is called in the first line of each sitrep |
| `purpose` | text | The decision or interest it serves, one sentence |
| `requirements` | list | Two to five is the working range |
| `indicators` | list | At least one for each requirement |
| `sources` | list | What is read each run |
| `state` | list | What was true at the last run |
| `withdrawn` | list, optional | Items removed from `state`, kept so their ids are never reused |
| `runs` | list | One entry per run, oldest first |

Every id is unique across the whole file. The usual letters are R for requirements, I for indicators, S for sources and F for state items, with a number that only ever goes up.

### A requirement

`{"id": "R1", "question": "...", "priority": "high|medium|low"}`

A question whose answer could change. Priority decides what the sitrep leads with.

### An indicator

`{"id": "I1", "requirement": "R1", "watch_for": "...", "where": "...", "would_mean": "...", "status": "not seen|seen|contradicted", "seen_on": null, "evidence": []}`

- `watch_for` is an event or a threshold that a source could show: "the register lists the rule with a number", "the fee schedule shows a fee above 100". A trend with no threshold ("increased activity") draws an advisory.
- `where` is the kind of source it would appear in, or the source id.
- `would_mean` is what the user should conclude or do if it is seen.
- `status` moves to `seen` or `contradicted` only with `seen_on` set and at least one evidence entry: `{"source_id": "S1", "note": "what the source shows"}`. `contradicted` means a source shows the opposite of what was watched for, with the evidence recorded the same way.

### A source

`{"id": "S1", "title": "...", "address": "...", "tier": "...", "check": "each run|monthly", "last_checked": "YYYY-MM-DD", "last_result": "reached|unreachable|not checked", "note": "..."}`

| Tier | Means |
|---|---|
| `primary` | The original record: the law, the register entry, the standards body's own text, the dataset, the organisation's own statement about itself |
| `peer_reviewed` | A reviewed paper or equivalent |
| `secondary` | A named publisher's account of primary material: a news report, a law firm note, an official explainer |
| `aggregator` | Collected or rewritten material: digests, vendor blogs, listings |
| `unverified` | Origin or authorship cannot be established: forum posts, anonymous accounts |

`last_checked` and `last_result` are optional in a file written by hand, but the comparison counts a source as reached this run only if `last_result` is `reached` and `last_checked` is the date of the newest run. `note` is free text: what was actually read, or how the attempt failed.

### A state item

`{"id": "F1", "requirement": "R1", "statement": "...", "status": "FACT|REPORTED|ASSESSMENT|GAP", "source_ids": ["S1"], "editorial_reason": "Optional: why an unchecked wording correction preserves meaning",
  "as_of": "YYYY-MM-DD"}`

| Status | Means | Needs |
|---|---|---|
| `FACT` | A source of secondary tier or better was read and says this | At least one such source attached |
| `REPORTED` | A source says this and it has not been confirmed against a better one | A source |
| `ASSESSMENT` | The writer's inference from other items | A confidence in the statement; sources optional |
| `GAP` | Not established. Says what was not read or could not be found | Nothing |

One assertion per item. `as_of` is the date a source was last read and found to say this. It is not the date of the run: an item whose source was not reached keeps its old date, and the comparison refuses an item dated today with no source reached today.

### A withdrawn entry

`{"id": "F4", "statement": "...", "withdrawn_on": "YYYY-MM-DD", "reason": "..."}`

Add one when an item leaves `state`. The reason says what the source does now: silent, page gone, or revised. Withdrawn means no source reached this run still says it. It does not mean the statement is false. If a source now says the opposite, that is a changed item: keep the id and rewrite the statement.

An item may be removed while none of its sources was reached only if it is listed here with a reason. The comparison then reports it as dropped by decision, not as withdrawn.

### A run

`{"date": "YYYY-MM-DD", "summary": "...", "changes": 0}`

`changes` is the count the comparison prints: new, changed, withdrawn and dropped items plus indicator status changes. Earlier entries are left as they were.

## Dates

Real calendar dates written `YYYY-MM-DD`. `20261009`, `9/10/2026` and `2026-02-30` are refused.

## What the scripts cannot tell

Whether a statement is true, whether a source says what an item claims, and whether a source marked reached was read. They check the form of one file and the difference between two.
