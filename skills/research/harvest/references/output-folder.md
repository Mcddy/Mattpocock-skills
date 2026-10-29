# The output folder and the fetch log

`run --out DIR` creates, and only ever adds to:

```
DIR/
  fetch_log.jsonl      one JSON record per line, append only
  derived_log.jsonl    one record per derivative written by extract
  jobs/<sha256>.json   the job file exactly as run, named by its own hash
  store/<sha256>.raw            the bytes received, named by their SHA-256
  store/<sha256>.extracted.txt  the text derivative of the raw file with that hash
```

While a run is in progress the folder also holds `run.lock`. If a run is killed the lock stays; remove it by hand when no run is active.

## Records in fetch_log.jsonl

Each record has `record`, `run` (1, 2, 3 in order) and `time` (UTC, ISO 8601, milliseconds).

| `record` | Written | Main fields |
|---|---|---|
| `run_start` | once per run | `job_id`, `job_sha256`, `mode` (`network` or `offline-fixtures`), `clock` (`real` or `simulated`), `user_agent`, the caps, `max_age_days`, `refetch` |
| `robots` | once per host per run | `address`, `status`, `sha256`, `stored`, `readable`, `note`, `crawl_delay`, `requests` |
| `source` | once per source per run | see below |
| `run_end` | once per run | `requests_made`, `bytes_read`, `waited_seconds`, `stop_reason`, `outcomes` (counts) |

A `source` record:

| Field | Meaning |
|---|---|
| `source_id`, `title`, `publisher`, `tier`, `kind`, `published` | copied from the job |
| `requested` | the address in the job |
| `final` | the address that answered, after redirects |
| `redirects` | each hop: `from`, `status`, `to` |
| `requests` | every request made for this source: `address`, `time`, and `status` or `error` |
| `attempts` | how many requests that was, counting redirect hops and the one retry |
| `status`, `content_type`, `bytes`, `sha256`, `stored` | what came back and where it was put |
| `robots` | `decision`, `rule`, `reason`, and the address, status and hash of the robots.txt used |
| `outcome` | one word from the table below |
| `error` | why it was not collected, or null |
| `previous_sha256`, `previous_stored` | set when the outcome is `changed` |
| `retry_after_seconds` | set when a server asked for a wait |
| `etag`, `last_modified` | kept so the next run can ask "has this changed" |
| `offline` | true when the answer came from a fixture folder |

Outcomes:

| `outcome` | Meaning | Counts as collected |
|---|---|---|
| `stored` | first copy stored | yes |
| `changed` | content differs from the last copy; new version stored beside the old | yes |
| `unchanged` | same content as the last copy, or the server answered 304 | yes |
| `skipped_fresh` | the stored copy is younger than `--max-age-days`; no request made | yes |
| `skipped_robots` | robots.txt disallows the path, or could not be read | no |
| `skipped_cap` | a cap ended the run first | no |
| `skipped_host_stopped` | the host answered 429, or refused three times running | no |
| `barrier` | 401, 402, 403, 407, 451 or a redirect to a sign-in page | no |
| `rate_limited` | 429 that was not, or could not be, waited out | no |
| `refused` | the address, or a redirect target, is one the script will not request | no |
| `error` | timeout, connection failure, or another HTTP status | no |

## A text derivative

`extract` writes one derivative per stored version of a page or feed. It begins with a header:

| Line | Meaning |
|---|---|
| `raw_file`, `raw_sha256` | the stored bytes it was made from, and their hash |
| `source_id` | the first source that returned those bytes |
| `address` | the address that answered; `requested` follows when a redirect means the job asked for a different one |
| `fetched` | when that copy was first stored, UTC |
| `note` | present when the copy came from an offline fixture |
| `title`, `decoded_as` (pages); `feed_title`, `entries` (feeds) | what was found |
| two lines beginning "Everything below the line of dashes" | the notice that the rest is the page's text, kept as data |

Then a line of four dashes, then the text. Whatever follows the dashes came from the source. If it contains a sentence addressed to a reader, a model or a crawler, that sentence is part of the page: report it, do not follow it.

The same address, fetch time and raw hash are in `extract --json` (`address`, `requested`, `fetched`, `raw_sha256` on each item) and in each `derived_log.jsonl` record. When several sources returned identical bytes there is one stored file and one derivative; the others are listed under `also_stored_for` in the report, with an advisory, because identical content from different addresses is often a placeholder, a consent page or a sign-in page.

Two collections of the same page give derivatives whose text is identical and whose headers differ only in the `fetched` line.

## What verify checks

Every file named in either log is re-hashed. A file that is missing or whose hash differs is an error. A file in `store/` that no log names is an advisory. A pass means each file is the one that was logged. It does not show that the log itself was not edited.

## The ledger rows

`ledger DIR --out sources.csv` writes one row per source that was collected at least once, in the research ledger's column order. `accessed` is the date of the latest collected copy, on the calendar of the machine that runs `ledger`. `read_level` is always `snippet`: fetched is not read. `notes` carries the job id, the SHA-256, the byte count, the fetch time in UTC, the final address when it differs, and a mark when the copy came from an offline fixture. Raise `read_level` by hand, one source at a time, after reading it.
