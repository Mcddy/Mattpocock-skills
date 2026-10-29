# Examples: response-analyst

Three worked runs. All data is SYNTHETIC: invented for these examples, describing no real people.

Every `analysis*.txt`, `themes.txt` and `follow-up-by-mode.txt` file is the real, unedited output of `scripts/analyse_responses.py` on the inputs beside it. Every `findings.md` was written by the authoring session, following the skill's procedure, from those outputs. A second session regenerated every output on 2026-10-09 after changing the script to read the elicitor collector's files: the text outputs came out byte for byte the same, and the JSON output gained one key (`layout`). Nobody outside those two sessions has checked them. The theme codes in the workshop example were assigned by the authoring session reading each passage once.

## workshop-feedback

23 respondents to a 12-question feedback form: single choice, scales, a multiple-choice question, a number, two free-text questions, two note columns, some skipped answers, and one question (q7) shown only to online attendees.

| File | What it is |
|---|---|
| `responses.csv`, `instrument.json` | Inputs |
| `analysis.txt` | Overview, every question, two combined counts, the mode by pace cross-tab, and the pace comparison |
| `follow-up-by-mode.txt` | A second run for one more comparison, with the question block left out |
| `coding-sheet.csv` | Free text as exported by `--coding-sheet` |
| `codebook.csv`, `coded-sheet.csv` | The codebook and the sheet with codes added. Two passages from R20 were edited to remove a role and an email address |
| `themes.txt` | Theme counts by respondent |
| `findings.md` | The written findings, about one page |

To regenerate, from this folder:

```
python ../../scripts/analyse_responses.py responses.csv --instrument instrument.json --combine "q3=Useful|Very useful" --combine "q4=A bit fast|Much too fast" --cross q1 q4 --compare "q4=A bit fast|Much too fast" --by q1 --coding-sheet coding-sheet.csv --overwrite > analysis.txt
python ../../scripts/analyse_responses.py responses.csv --instrument instrument.json --skip-questions --compare q9=Yes --by q1 > follow-up-by-mode.txt
python ../../scripts/analyse_responses.py responses.csv --instrument instrument.json --skip-questions --themes coded-sheet.csv --codebook codebook.csv > themes.txt
```

## quiz-item-analysis

31 respondents to a 12-item quiz. Two faults were planted on purpose: item k7 is keyed C although B is correct, and option D of item k10 is implausible. `make_synthetic_quiz.py` is the generator (`python make_synthetic_quiz.py . 1` rewrites `responses.csv` and `instrument.json` with seed 1, the first seed tried).

| File | What it is |
|---|---|
| `responses.csv`, `instrument.json` | Inputs, with the miskey in place |
| `analysis.txt` | Output. k7 carries the "possible miskey" candidate and k10 the "option nobody chose" candidate |
| `instrument-k7-key-corrected.json`, `analysis-after-key-fix.txt` | The same responses rescored with k7 keyed B |
| `findings.md` | The written findings |

```
python ../../scripts/analyse_responses.py responses.csv --instrument instrument.json --point-biserial > analysis.txt
python ../../scripts/analyse_responses.py responses.csv --instrument instrument-k7-key-corrected.json --point-biserial > analysis-after-key-fix.txt
```

## tiny-sample

6 respondents. Shows descriptive findings with wide intervals, a comparison of 2 people against 4 that cannot separate the groups, every comment quoted, and no generalising.

| File | What it is |
|---|---|
| `responses.csv`, `instrument.json` | Inputs |
| `analysis.txt`, `analysis.json` | Text and `--json` output of the same run |
| `findings.md` | The written findings |

```
python ../../scripts/analyse_responses.py responses.csv --instrument instrument.json --combine "t2=Agree|Strongly agree" --cross t1 t3 --compare t3=Yes --by t1 > analysis.txt
```
