---
name: response-analyst
description: "Analyses collected survey, questionnaire, quiz and interview responses: counts over named denominators with intervals, non-response, cross-tabs, coded free-text themes with quotations, and item analysis for quizzes. Use for analyse these survey responses, what did people say, summarise the feedback, which quiz questions were bad, code these comments. Not for building the questionnaire (elicitor), datasets that are not responses (data-intelligence) or checking someone else's report (fact-check)."
metadata:
  revision: "1.0.0"
---

# Response analyst: what the responses support, and no more

Responses come back from a survey, a feedback form, a quiz or a round of interviews. This skill turns them into findings a reader can check: every proportion as a count over a named denominator, non-response in view, uncertainty shown as an interval, free text coded openly, and quiz items read one at a time.

A skill is instructions plus a script. It adds no memory and no judgement of its own. The script counts; the reading is done by the model and belongs in the report as assessment.

## Use when

- Responses are in hand and someone asks what they say: "analyse these survey responses", "summarise the feedback", "what did people say".
- A quiz has been sat and someone asks which questions misbehaved.
- Comments or interview notes need coding into themes with quotations.
- Two groups of respondents need comparing and the groups are small.

## Not this skill

| The job | Use |
|---|---|
| Write or build the questionnaire, survey or quiz | elicitor |
| A dataset that is not responses: sales, logs, measurements | data-intelligence |
| A workbook or spreadsheet model | spreadsheet-intelligence |
| Choose which people or records to ask | No skill. Answer plainly: a random draw, with the method and the seed stated |
| Estimate a quantity nobody measured | fermi |
| Decide which explanation best fits what the responses show | intelligence-analyst |
| Check the claims in a report someone else wrote | fact-check |
| One percentage from two numbers, or three comments to read | No skill. Answer plainly, with the count beside the percentage |

Interviews done as product or design research are still this skill.

## Inputs

- **The responses.** A CSV with one row per respondent, in either of two layouts. The plain layout has a `respondent` column, one column per question id, and optional `<id>__note` columns for a free-text note on a question; several choices in one cell are separated by `;`. The file that the elicitor skill's `collect_responses.py` writes is also read as it is: `source` is taken as the respondent column, `<id>.note` columns as notes, `(skipped)` and `(not shown)` as what they say, ` | ` as the separator between choices, and the `tally:` columns are left out and named. Pasted tables and transcripts are first written to the plain layout.
- **The instrument**, if it exists: wording, type and options of each question, the keyed answer for quiz items, and routing. Fill in `assets/instrument-template.json`. Without it the script infers types and says what it guessed.
- **How respondents were reached**, how many were asked, and who is missing. If the user has not said, do not stop: run the analysis, print NOT STATED as the first gap, and ask for it in one line.
- **The decision the findings feed**, if there is one. It decides which comparisons are worth running.

## Tools: discover first

- A shell with Python 3.8 or later, for `scripts/analyse_responses.py`. Standard library only, no installs. Without a shell: tally by hand, show each tally as count of denominator, compute intervals from the formula in `references/methods.md` with the arithmetic shown, and say it was done by hand.
- File reading, for the CSV. If the data arrives as an image or a screenshot, transcribe it, show the transcription, and say counts depend on it.
- elicitor, if present, is where the instrument came from. Name it only if it is actually available.

## Procedure

1. **Size the request.** A single percentage, or a handful of comments that fit in the reply, gets a plain answer with counts. Do not run the whole procedure on it.
2. **Say who answered** before anything else: how they were reached, how many of how many, who is missing. A convenience sample describes those who answered.
3. **Get the data into shape.** One row per respondent. Write the instrument from the questionnaire using `assets/instrument-template.json`: options in their real order, the key for quiz items, `shown_if` for routed questions.
4. **Run** `python scripts/analyse_responses.py RESPONSES.csv --instrument INSTRUMENT.json`. If it refuses the file (ragged rows, repeated respondent values, answers that are not options, an instrument that does not match), report the errors as printed and fix the cause with the user. Never repair a row by guessing.
5. **Read non-response first.** For each question: shown, answered, skipped, not shown. Skipped and routed past are different things and are reported separately.
6. **Closed questions.** Report the full distribution. For "agree or strongly agree" style figures use `--combine "Q=A|B"`, which gives one count with its interval. For scales, report every point; a mean needs `--scale-means` and its printed sentence about treating the scale as numbers.
7. **Comparisons.** `--cross Q1 Q2` for the table; `--compare "Q=OPTION" --by GROUPQ` for a difference with an interval. Decide which comparisons matter before looking, run those, and report all that were run. Say plainly when groups cannot be separated: "3 of 4 against 5 of 9: the intervals overlap almost entirely".
8. **Free text.** `--coding-sheet OUT.csv`, read every passage, write a codebook from `assets/codebook-template.csv`, code the sheet, then `--themes CODED.csv --codebook CODEBOOK.csv`. Pick two or three quotations per theme with respondent ids, find the case that does not fit, and run the privacy check. The full method is in `references/reporting.md`.
9. **Quiz data.** Read the item analysis: difficulty, discrimination with the group sizes, option counts by group, and the CANDIDATE lines. Each candidate is read against the question itself; the reading is the finding. If a key is wrong, correct the instrument and run again, because every total changes. Add `--point-biserial` when a second index is wanted. Reading guide: `references/methods.md`.
10. **Write the findings** in the order under Output, tagging load-bearing claims FACT, ASSESSMENT or GAP. Wording to use and avoid: `references/reporting.md`.
11. **If the script was changed**, run `python scripts/test_analyse_responses.py` and `python scripts/test_analyse_responses.py --planted` before trusting it.

Useful options: `--skip-questions` for a second run that only adds a comparison or themes, `--level 90` for a different interval, `--json` for machine-readable output, `--keep-ids` only when the user asks for respondent values as given.

## Failure branches

- **No shell.** Count by hand and say so. Keep the same denominators and show the interval arithmetic, or leave intervals out and say that they were left out.
- **No instrument.** Run without it and report what the script inferred. Say that skipped cannot be told from not shown (unless the file is in the collector's layout, which marks both), that options nobody chose are invisible, and that a quiz cannot be scored. Offer to build the instrument from the questionnaire.
- **A collector file whose choices are written as JSON lists** (the collector's `--multi json`). The script refuses those cells and names them. Ask for the file to be collected again with the default, or split the cells by hand and say so.
- **The file is refused.** Quote the errors. Do not hand-edit data to get a run.
- **Reach not stated.** Report it as the first gap and limit every claim to "the N who answered".
- **Very few respondents.** Report anyway: counts, denominators, intervals, every comment. What changes is how far it can be generalised, and the interval width shows that. Do not quote a minimum sample size; there is no universal one.
- **"Is it significant?"** Give the difference and its interval. If a test is still wanted, name it and give its inputs. Do not run many comparisons and report the one that separates.
- **A score, a type or a diagnosis is asked for** from an informal questionnaire. Give the tallies as counts and say what they are. Do not label a person or a group.
- **Asked who said what.** Respondent values stay replaced by ids unless respondents were told their answers are attributable and the user asks for them. Do not work out who a respondent is.
- **Too small for the skill, or a neighbour's job.** Answer plainly, or name the neighbour from the table above.
- **This skill's own ways of going wrong:** a percentage with no count; "of respondents" used for a routed question; a mean of an agreement scale called a score; mentions counted as people; a theme built on one comment; a D from groups of two read as a verdict; a candidate flag reported as a fault without reading the item; several comparisons run and one reported.

## Output

The first line names the method: "Response analysis: counts over named denominators, with intervals." (for a quiz: "Response analysis: quiz item analysis, with counts and group sizes.").

Then, in about a page:

1. **Answer.** Two to four findings the responses support and one recommendation, each finding with its count and denominator.
2. **Who answered.** Reach, response count over invited, who is missing.
3. **Closed questions.** Full distributions with skips.
4. **Comparisons.** Both groups' counts, the difference, its interval.
5. **What people wrote.** Themes labelled as the analyst's coding, the codebook or where it is, respondents per theme over the denominator, quotations with ids, the case that does not fit, and the privacy check.
6. **Quiz items**, when keyed: how groups were formed and their sizes, the item table, each candidate and how it was read.
7. **What these responses cannot show.**
8. **Next.**

## Rules that always hold

- Every percentage has its count and a named denominator beside it.
- Non-response is reported for each question. Skipped and not shown are never merged, and skipped respondents are never dropped from a denominator without saying so.
- Who answered comes first. A convenience sample describes those who answered.
- Small samples still get findings. No universal minimum number of respondents is ever stated.
- Proportions carry an interval computed by the script; comparisons carry both groups' counts and an interval for the difference. "Significant" is never used without the test and its inputs.
- Scales are reported as full distributions. A mean of scale points is labelled as treating them as numbers.
- Themes are the analyst's coding, counted by respondent, shown with the codebook, quotations and a case that does not fit.
- Tallies from informal questionnaires are counts. They are never diagnoses, types or validated scores.
- Quiz item flags are candidates for a person to read, printed with group sizes.
- Respondent names are replaced by ids, and quotations are checked for identifying detail before they are shown.

## What has and has not been tested

Everything below was run by the session that wrote this skill or by a second session that reviewed and repaired it on 2026-10-09, on Python 3.13. Both are author-side. Nobody independent has run any of it. The numbers are from the review's reruns.

- `scripts/test_analyse_responses.py`: 32 tests, all passing. They check the Wilson interval, the difference interval, discrimination, point-biserial, cross-tab and theme counts against values worked by hand in the test comments, and cover ragged rows, unknown option values, repeated respondent values, non-UTF-8 and UTF-16 files, and ten kinds of instrument mismatch.
- `--planted`: seven broken copies of the script, each caught by its named test. They are: skipped respondents dropped from denominators, themes counted by mention, a Wald half-width in place of Wilson, discrimination with its sign reversed, the difference interval built from the wrong limits, the collector's "(not shown)" mark counted as a skip, and its "(skipped)" mark counted as an answer.
- The elicitor collector's own output. As first written, the script refused it: the layout had been taken from a description that did not match the collector (it writes `source`, `<id>.note`, `(skipped)`, `(not shown)` and ` | `). In review the collector was run on nine invented reply files and on its own one-reply fixture, the script was changed to read both files as they are, and both files are kept inside the test suite with counts worked by hand. Not run: the collector's `--multi json` output, which the script refuses, and a file with more than nine rows from it.
- The review's own bad-input checks, not shipped: 27 checks (an unknown option, a missing option value, a byte-order mark, an empty file, NaN and infinity in a number column, wrongly typed instrument values, and that no output line carries a percentage without its count). All passed, and three altered copies of the script each failed at least one.
- Three worked runs on synthetic data (23 survey respondents with coded free text; 31 quiz respondents with a planted miskey and a dead option, both raised as candidates; 6 respondents), with findings written by the authoring session. Regenerated in review: byte for byte the same, apart from one new key in the JSON output. A fourth run in review, on the nine collector replies, with a coded sheet, a codebook and written findings, is not shipped.
- The difference interval reproduces 0.0524 to 0.3339 for 56 of 70 against 48 of 80, the figures given for Newcombe's method 10. That table was not fetched for this skill, so this is corroboration only. A 3,000-row synthetic file ran in under a second.

Not tested: any model following this skill other than the session that wrote it; any real host's preview. Also not tested: files larger than that 3,000-row file; consistency of theme coding between two coders; any real survey.

## Acceptance cases

The full set travels with the source for review.

1. A 23-row feedback file with an instrument and "summarise the feedback". Expect: who answered first, with 23 of 38 invited; every percentage beside a count and a named denominator; the routed question reported as shown to 9; themes labelled as the analyst's coding with respondent counts, ids and a case that does not fit; no mean score for a scale.
2. A 31-row quiz file with a key and "which questions were bad". Expect: group definition and sizes stated; the miskeyed item reported as a candidate and then read against its wording; the unchosen option named; no item called bad on a flag alone.
3. Six respondents and "is that enough to tell anything". Expect: counts and wide intervals reported, a 2 against 4 comparison described as unable to separate the groups, every comment quoted, no minimum sample size stated.
4. Negative control: "write me a ten-question feedback survey". Expect: elicitor leads. Second negative control: "12 of 40 said yes, what per cent is that". Expect: "30% (12 of 40)" in one line, with no procedure.
