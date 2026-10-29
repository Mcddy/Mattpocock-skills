# Examples

Three real questionnaires, built and filled in by the authoring session by following the skill's own procedure, then rebuilt and filled in again by a second session of the same authoring team after it repaired the engine. Nobody independent of that team has run them. The answers are SYNTHETIC: invented cases, no real person or organisation.

| File | What it is |
|---|---|
| `project-intake.html` | Intake mode. 28 questions in 4 sections (24 shown until earlier answers open the other 4), every question type, for capturing requirements for a small software tool |
| `project-intake.export.md` | The export the page produced after being filled in through a browser with `answers/project-intake.json` |
| `workshop-feedback.html` | Survey mode. A disclosure screen, 13 questions (one conditional), one tally |
| `workshop-responses/respondent-1.txt`, `-2.txt`, `-3.txt` | The response block the page produced for each of three invented respondents (`answers/workshop-feedback.json`) |
| `workshop-responses.csv` | Those three blocks merged by `scripts/collect_responses.py` |
| `subnetting-quiz.html` | Quiz mode. 12 items on IPv4 subnetting, every option explained |
| `subnetting-quiz.export.md` | The result the page produced for an invented attempt (`answers/subnetting-quiz.json`): 6 correct of 10 attempted, 2 skipped |
| `verify_subnetting.py` | Recomputes every answer key of the quiz with Python's `ipaddress` module, and 39 figures quoted in 36 of the 48 explanations, each tied to the wording it was taken from so that a reworded explanation fails until it is checked again. The other 12 explanations were read, not computed |
| `instruments/*.json` | The inputs: the three instruments as written before building |
| `answers/*.json` | The inputs: the invented answers the browser typed and clicked |
| `steps/*.steps` | Step files for the shared `delivery_check.py`, covering each page's main journey in a tab and in a sandboxed frame |
| `make_examples.py` | Rebuilds everything above |

## To regenerate

```
python make_examples.py
```

It needs Python Playwright with Chromium (it prints NOT RUN and exits 3 without them). It builds the three pages with `scripts/build_instrument.py`, runs `verify_subnetting.py`, opens each page from disk at a 390 by 844 viewport, answers it by clicking and typing, writes the exports, reads each one back with `scripts/parse_export.py`, compares it field by field with the state the page reported, and merges the three responses. The time stamps in the exports are the time of the run, so the export files change each time.

## To check them without a browser

```
python verify_subnetting.py subnetting-quiz.html
python ../scripts/validate_instrument.py project-intake.html --engine ../assets/engine.html
python ../scripts/parse_export.py project-intake.export.md
python ../scripts/parse_export.py subnetting-quiz.export.md
python ../scripts/collect_responses.py workshop-responses/respondent-*.txt --json
```

## What these do not show

They were filled in by a script in headless Chromium, not by a person on a phone. The answers are plausible, not real. The wording advisories of the validator were read and acted on once each (one question in `project-intake` was reworded because its opening presumed an answer); that is the author's judgement, not a test.
