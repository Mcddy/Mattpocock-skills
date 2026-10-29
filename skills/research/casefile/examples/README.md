# Examples: casefile

Everything here was made by the authoring session by following the skill's own procedure. Nobody else has run it yet. This folder travels with the source for review and is not part of the installed skill.

| File | What it is |
|---|---|
| `eaa-sources.csv`, `eaa-claims.csv` | The input: a real ledger from real research on EU accessibility standards and WCAG 2.2 SC 2.5.8, copied unchanged from deep-research-orchestrator's acceptance files. 5 sources, 8 claims |
| `eaa-extra.json` | The second input: the wording of the four questions, and one assessment (A1, on Q4, resting on C1, C2 and C4), written by the authoring session so that lineage has something to show |
| `eu-accessibility-casefile.html` | The output of `build_casefile.py` on those three files. Open it in a browser |
| `eu-accessibility-casefile-export.json` | The casefile envelope, copied from the page's export box straight after opening. Importing it into a fresh copy of the page reproduces the state |
| `eu-accessibility-brief.md` | The Markdown brief the page builds from the ledger. The Answer section is blank on purpose |
| `eu-accessibility-casefile.steps.txt` | The primary journey as steps for `delivery_check.py` (interface-architect's script), run in a tab and in a sandboxed frame |

## Try it

1. Open `eu-accessibility-casefile.html`. Above the views: 0 open conflicts, 1 load-bearing claim only REPORTED, 1 gap.
2. Open assessment A1 (under Q4, or type `A1` into Open by id). It rests on C1, C2 and C4, and its weakest support is one REPORTED claim, C2. Each claim shows its sources beneath it.
3. From C2 open source S3 and read "If this source falls": C2 would be left with no source at all, assessment A1 rests on C2, and C8 would still rest on S4.
4. On C2 choose FACT. It is refused: S3 has no address. Open S3, choose Edit this source, give it an address, go back to C2 and choose FACT again: allowed. Undo puts it back to REPORTED.
5. Open C5 and try the load-bearing switch: refused, because model output cannot be load-bearing.
6. On Conflicts, record C3 against C8 as a direct conflict. Both claims show it and the count above reads 1 open conflict (1 direct). Write how it was settled and choose Mark settled on both claims: the note goes on both and the count returns to 0.
7. On Keep and export, show the two CSV files. For the unmodified example they are byte for byte the two input files, and `ledger_check.py` gives 0 errors and 8 advisory notes on both.

The eight advisory notes are: C2 is load-bearing and only REPORTED; S1 is old for a load-bearing claim; S2, S3, S4 and S5 have no publication date; S3 and S5 have no address.

## Regenerate

From the skill folder:

```
python3 scripts/build_casefile.py examples/eaa-sources.csv examples/eaa-claims.csv \
  --extra examples/eaa-extra.json --title "EU accessibility standards and SC 2.5.8" \
  --today 2026-10-09 --out examples/eu-accessibility-casefile.html
```

The same inputs and the same `--today` give the same bytes. The export and the brief were copied from the page's own text boxes on the Keep and export view. `scripts/test_casefile.py` builds the same page from its own copies of the three inputs in `scripts/fixtures/` and runs the journeys above.

The engine page `assets/casefile.html` is its own source: there is no separate template. It carries pasted copies of `assets/pocket-state.js` and `assets/pocket-ui.js`, which are the released pocket-app library files; `assets/pocket-lib.sha256` records their hashes and `scripts/test_casefile.py` checks both the pasted copies and the hashes.

## What the authoring session ran on these files

See "What has and has not been tested" in `SKILL.md` for the numbers. Not run: any real chat host's preview, any screen reader, any browser other than the Chromium that Playwright launches.
