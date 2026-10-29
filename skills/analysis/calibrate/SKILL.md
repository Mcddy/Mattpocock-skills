---
name: calibrate
description: "Tracks predictions and scores them: records a falsifiable prediction with a probability and a resolution date, resolves it later, and computes Brier score and calibration by confidence band from the ledger file. Use when the user wants to log a forecast, resolve one, or see how well calibrated they or the model have been. Not for making the forecast (oracle, intelligence-analyst), logging decisions and beliefs (mnemosyne), verifying claims (fact-check) or benchmarking prompts (prompt-bench)."
metadata:
  revision: "2.0.1"
  revised-from: "calibrate as exported 8 Oct 2026"
---

# Calibrate: a prediction ledger and its score

Calibration means that things you call 70% likely happen about 70% of the time. The only way to find out is to write predictions down before the outcome is known, resolve them honestly, and count. This skill keeps that ledger and does the counting with a script, so the score is arithmetic and not an impression.

- `assets/ledger-template.csv`: the ledger format.
- `scripts/brier.py`: validates the ledger and prints the Brier score, calibration by band and overdue predictions. When it rejects any row it scores the valid rows only and marks the result partial.

The ledger is a file the user keeps. The skill reads it when it is supplied. Nothing runs between sessions, and nothing is tracked unless it is in the file.

## Use when

- "Log this prediction", "track this forecast", "put 70% on that and check it in March".
- "Resolve P-014", "that one came true".
- "How calibrated am I", "score my predictions", "am I overconfident".
- A forecast was just made in the conversation and the user wants it recorded.

## Not this skill

| The job | Use |
|---|---|
| Produce the forecast or the analysis behind it | oracle, intelligence-analyst |
| Record decisions and working beliefs | mnemosyne |
| Check whether a claim is true now | fact-check |
| Compare prompt versions on a test set | prompt-bench |
| Weigh options for a choice | decision-board |

## Inputs

- To log: the claim, a probability, and when it will be known.
- To resolve: the id and what happened.
- To score: the ledger file, supplied in this session.

## Tools: discover first

- A way to read and write the ledger where the user keeps it. Without write access, output the new or changed row for the user to paste.
- Python, for `scripts/brier.py`. Without it, compute by hand only for a handful of rows, show the working, and say the script was not run.
- Search, only if the user asks you to look up an outcome. Report the source and let the user confirm the resolution.

## Procedure

### A. Log a prediction

1. Rewrite the claim until it can only come out true or false, with a date. "Sales will improve" becomes "March revenue is above February revenue, by the monthly report dated on or before 10 April".
2. Write the resolution rule into the statement: what source decides it, and what counts.
3. Record the probability the forecaster gives. If they give a phrase, ask for a number once; if they decline, do not log it. Do not supply the number for them unless the prediction is the model's own.
4. Set `made_by` to who is making the claim: the user, the model, or both.
5. Add the row. Show it. Write it to the file only if asked and a write tool exists.

One row per claim. A claim with "and" in it is two rows.

### B. Resolve

1. Find the row by id.
2. Apply the resolution rule as written when the prediction was made. Outcome is 1 or 0.
3. If the rule cannot be applied (the source never published, the question became meaningless), mark it `void` and note why. Void rows are not scored. Do not void a row because the outcome is uncomfortable.
4. "Partly right" is not an outcome. If it keeps coming up, the claims are being written too loosely; tighten step A.
5. Never change the probability or the statement after the fact.

### C. Score

Run:

```
python scripts/brier.py ledger.csv
python scripts/brier.py ledger.csv --by made_by
python scripts/brier.py ledger.csv --by domain
```

Report what it printed:

- Rejected rows, with reasons. When any row is rejected the script scores the valid resolved rows only, prints a `PARTIAL RESULT` line and sets `"partial": true` in `--json`. Report the figure in those terms ("partial: scored 6 of 8 resolved rows; 4 rows rejected and listed"), never as the ledger's score, and say the rows must be fixed and rescored for a final figure. Do not repair a row by guessing what was meant.
- The Brier score, next to the score that always quoting the ledger's own base rate would have earned. Beating that reference is the first bar.
- Calibration by band. A band is called overconfident or underconfident only when it has at least 10 resolved predictions. Below that the script says "too few to call", and so do you.
- Overdue predictions.

### D. Read the pattern (only with enough data)

With at least 20 resolved predictions overall and 10 in the band in question:

- Name the band or group where forecast and outcome differ most, with the counts.
- Suggest one adjustment, stated as a number ("when you say 90%, say 80% until the next 20 resolve").
- Say when to look again.

With less data, say there is not enough to read a pattern, and stop. Do not fill the space with general advice about bias.

## Failure branches

- **No ledger supplied.** If the user asked to log a prediction, offer the template and log that row with procedure A. If the request was only to score, say there is nothing to score yet and offer the template. Log nothing the user did not ask to log.
- **Fewer than 20 resolved.** Give the score with the small-sample flag. No pattern reading.
- **Rows rejected.** List them with reasons, report the script's figure as partial with its "N of M resolved rows" count, and say what to fix. Read no pattern from a partial result: procedure D waits for the corrected ledger to be scored.
- **The claim cannot be made falsifiable.** Say so and do not log it.
- **The outcome is disputed.** Record the dispute in the row's note, leave it pending, and ask who decides.
- **All predictions are near 50%.** The score will look fine and say little. Point that out.

## Output

- Log: the row as added.
- Resolve: the row as changed.
- Score: the script's output, then at most three lines of reading it, then what is due next. A partial result is labelled partial in the first line of the reply.

## Rules that always hold

- A probability or statement is never edited after the prediction is logged.
- No pattern is claimed from fewer than 10 predictions in a band or 20 overall.
- The score reported is the script's. If the script did not run, that is stated.
- A figure computed while rows were rejected is a partial diagnostic. It is given with its counts and is never called the ledger's score.
- The ledger holds predictions. It does not hold observations about the forecaster.
- Nothing is written to the file, to notes or to memory unless the user asked for that write.

## What has and has not been tested

Corrected on 9 Oct 2026: a score computed while rows are rejected is now reported as partial by the script and the procedure, and a score-only request with no ledger no longer logs a row. Not independently retested.

`scripts/brier.py` was run on a sample ledger, an all-pending ledger, a ledger with a missing column and a missing file, and its arithmetic was checked against an independent calculation. On 9 Oct 2026 it was also run on the sample ledger (four rows rejected: partial, 6 of 8 resolved rows scored, Brier 0.2088) and on the same ledger with those rows repaired (not partial, 9 resolved rows, Brier 0.2142, matching a hand calculation). That tests the script.

Four author-run behaviour cases exist for this skill. The authoring session produced the replies and scripted checks graded them; they predate this correction, so the sample-ledger case shows the earlier wording. There has been no independent run and no measurement of whether any host loads this skill. Whether using it makes anyone better calibrated has not been measured and cannot be from a handful of rows.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. "Log it: I think the migration will go fine." Expect: the claim rewritten as true-or-false with a date and a source, one request for a number, no row without one.
2. A ledger with six valid resolved rows and four malformed rows. Expect: the reply opens by calling the result partial ("scored 6 of 8 resolved rows; 4 rows rejected and listed"), gives Brier 0.2088 only as that partial figure with the small-sample flag, lists the four rows with reasons, says they must be fixed and rescored for a final figure, and claims no bias pattern.
3. The same ledger with the four rows repaired. Expect: Brier 0.2142 over nine resolved rows, reported as the ledger's score with the small-sample flag and no partial label.
4. "Score my predictions", with no ledger supplied. Expect: "nothing to score yet", the template offered, and no row logged.
5. Negative control: "What are the odds the central bank cuts rates next month?" Expect: this skill does not produce the forecast. It offers to log one once made.
