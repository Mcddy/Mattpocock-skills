# Examples for harvest

One example, made by the session that wrote the skill by following the skill's own procedure. A second session reviewed it on 2026-10-09, regenerated every output with the repaired script (each derivative now opens with its fetch time and a notice that the page text is data), and checked the write-up's figures against the regenerated files. Nobody outside those two sessions has checked it.

Everything in it is SYNTHETIC. The publisher is invented and every address is on the reserved `.example` domain. All responses were served from a local fixture folder, so nothing was fetched from a network.

## standards-pages/

| File or folder | What it is |
|---|---|
| `job.json` | The job file: 13 sources on 2 hosts |
| `fixtures/` | The fixture set: 10 HTML pages plus a second version of one of them, an RSS feed, a PDF-like binary file, a robots.txt that disallows `/drafts/`, and two mapping files. `fixtures.json` answers the first run: one address answers 429 with `Retry-After`, one redirects, one times out. `fixtures-second-run.json` answers the second run, with one page changed |
| `outputs/01-check.txt` to `09-...txt` | What each command printed: check, plan, run 1, run 2, verify, extract, ledger, verify again, and a third run with nothing due |
| `outputs/10-...` and `11-...` | The research ledger's `ledger_check.py` run on the ledger rows after and before reading |
| `collected/` | The output folder after all runs: `fetch_log.jsonl`, `derived_log.jsonl`, the job as run, and `store/` with every raw file and its text derivative |
| `sources.csv` | The ledger rows as the script wrote them, all at `read_level` `snippet` |
| `sources-after-reading.csv`, `claims-after-reading.csv` | The same rows after the author read three sources and raised them by hand, with a four-row claims file |
| `WRITEUP.md` | The author's short account of the job |

### To regenerate

From inside `standards-pages/`, with `H` standing for `python ../../scripts/harvest.py`:

```
H check job.json
H plan job.json --offline-fixtures fixtures
H run job.json --out collected-new --offline-fixtures fixtures
H run job.json --out collected-new --offline-fixtures fixtures --fixture-map fixtures-second-run.json --refetch
H verify collected-new
H extract collected-new
H ledger collected-new --out sources-new.csv
```

Every raw-file hash will match the ones here. Times will not: the simulated clock starts at the moment of the run. Each derivative's header carries its fetch time, so derivative hashes differ from run to run while the text below each header is identical.

### To test it

- `H verify collected` should pass with 24 of 24 files.
- Change one byte in any file under `collected/store/` and `verify` should fail and name it.
- `python ../../scripts/test_harvest.py` runs the script's own tests; `--planted` shows each test failing on a broken copy.
