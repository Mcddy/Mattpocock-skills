Harvest: a collection job with robots rules, a delay and caps; every fetch logged with its hash.

Author-run example on SYNTHETIC material. The Harbour Lighting Standards Board does not exist; `standards.example` is a reserved domain. Every response came from the `fixtures` folder with `--offline-fixtures`, so **nothing was fetched from any network and every wait was simulated**. The session that wrote the skill produced this by following its procedure.

## What was asked

Collect the Board's four published standards, its last two sets of minutes, its notices feed and its register file, 13 sources on 2 hosts, so that it can be shown later what each standard required on the day it was fetched.

## Before the run

- API, download and terms: not applicable to a fixture folder. On a real site this step comes first and its result is reported here.
- People: none. The pages are an organisation's own standards and minutes.
- `check`: PASS (`outputs/01-check.txt`).
- `plan` (`outputs/02-plan.txt`): 12 to fetch, 1 to skip. S8, the working draft, is skipped because the site's robots.txt says `Disallow: /drafts/`. 14 requests planned against a cap of 60. Least time 24 s.

## Run 1 (`outputs/03-run-1.txt`)

11 of 13 sources collected. 16 requests, 9,539 bytes.

| Source | Outcome | Why |
|---|---|---|
| S8 working draft | skipped | robots.txt disallows `/drafts/`. Not requested. |
| S11 archive index | error | timed out after 20 s. One attempt, not retried. |
| S9 old address | stored | redirected (301); the final address is recorded. |
| S10 consultations | stored | answered 429 with `Retry-After: 30`; waited 30 s, retried once. |
| the other 9 | stored | |

## Run 2, a repeat with `--refetch` (`outputs/04-run-2.txt`)

11 of 13 again: 1 changed, 10 unchanged. S8 and S11 as before.

**S4, HL-103 Inspection intervals, changed.** SHA-256 `12fa83f0b8639a2f...` in run 1, `35d3dabe34ee8d58...` in run 2. Both versions are in `collected/store/`. This is the point at which sitrep would take over, to report what the change means.

## After the runs

- `verify`: 13 files named in the log, 13 matching (`outputs/05-verify.txt`). After `extract`: 24 of 24 (`outputs/08-verify-after-extract.txt`).
- `extract`: 11 derivatives for 12 stored versions; the register file is kind `file` and is left alone (`outputs/06-extract.txt`).
- `ledger`: 11 rows in `sources.csv`, every one at `read_level` `snippet`. S8 and S11 are omitted and listed with the reason (`outputs/07-ledger.txt`).
- A third run with no flags made 2 requests: everything collected was younger than 7 days, so only S11 was tried again, and it timed out again (`outputs/09-run-3-nothing-due.txt`).

## Fetched is not read

The author then read the stored derivatives of S4 (both versions), S6 and S7, and by hand raised those three rows to `read_level` `full` in `sources-after-reading.csv`. What they say, read from the stored copies:

- FACT (S4, version fetched in run 2, section 2): each fixed light shall be inspected at least once every 6 months; edition 2, in force from 1 October 2026.
- FACT (S4, version fetched in run 1, section 2): edition 1 said every 12 months.
- FACT (S6 and S7, first item of each): the committee agreed the shorter interval at meeting 41 and approved edition 2 at meeting 42.
- GAP: whether the HL-105 draft touches inspection. It was not collected.

The research ledger's checker accepts those three FACT claims against `sources-after-reading.csv` and refuses the same claims against the unread `sources.csv` ("no source was opened"): `outputs/10-ledger-check-after-reading.txt` and `outputs/11-ledger-check-before-reading.txt`.

Not read: S1, S2, S3, S5, S9, S10, S12, S13. Nothing is claimed from them.

## What this example does not show

Any behaviour against a real site. Real network errors. How long a real run takes: the 56 s and 26 s of waiting above are simulated figures.
