# sitrep examples

Made by the session that wrote the skill, by following its procedure. Nobody else has run them. Paths below are relative to the skill folder.

## What is real and what is not

- **Real:** every statement in `open-standard-watch/watch-baseline.json`. Each was either recorded in the research ledger this watch was seeded from (the EU accessibility standards ledger from the deep-research-orchestrator skill, dated 8 October 2026) or read from the named source with a page fetch on 9 October 2026. The source notes say which, and say where a fetch returned only part of a page.
- **SYNTHETIC:** every later run. No source was read on 16 October 2026. The second-run files invent changes to show each category of the comparison, and each invented statement, note and source begins with the word SYNTHETIC. Do not cite them.

## open-standard-watch

| File | What it is |
|---|---|
| `watch-baseline.json` | The watch after its first run: four requirements, five indicators, nine sources, ten state items |
| `baseline-check-output.txt` | Output of `watch_check.py` on the baseline |
| `watch-run2-candidate-SYNTHETIC.json` | The candidate for a second run: one new item (F11), one changed (F9), one withdrawn (F1), one indicator newly seen (I5), one source unreachable (S3) |
| `diff-output.txt`, `diff-output.json` | Output of `sitrep_diff.py` on the two files, as text and as JSON |
| `sitrep-skeleton.md` | Output of `sitrep_diff.py --markdown`: the skeleton the writer completes |
| `sitrep.md` | The sitrep as written from the skeleton: 14 lines of text, 31 lines when wrapped at 110 columns with blank lines counted |

Regenerate the outputs:

```
python scripts/watch_check.py examples/open-standard-watch/watch-baseline.json
python scripts/sitrep_diff.py examples/open-standard-watch/watch-baseline.json examples/open-standard-watch/watch-run2-candidate-SYNTHETIC.json
python scripts/sitrep_diff.py examples/open-standard-watch/watch-baseline.json examples/open-standard-watch/watch-run2-candidate-SYNTHETIC.json --markdown
python scripts/sitrep_diff.py examples/open-standard-watch/watch-baseline.json examples/open-standard-watch/watch-run2-candidate-SYNTHETIC.json --json
```

Things to notice. F1 is withdrawn and the sitrep says in the same breath what that does not mean. F6 rests on the unreachable source and keeps its old date; it is reported as not checked, not as unchanged. The advisory about R1 having both a removed and a new item is the script declining to guess whether F11 is F1 reworded.

## no-change

| File | What it is |
|---|---|
| `watch-before.json` | The same baseline |
| `watch-after-SYNTHETIC.json` | A second run in which every source due was reached and nothing differs |
| `diff-output.txt` | Output of `sitrep_diff.py`: one line |
| `sitrep.md` | The whole sitrep: one line |

```
python scripts/sitrep_diff.py examples/no-change/watch-before.json examples/no-change/watch-after-SYNTHETIC.json
```
