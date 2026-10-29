# AI and software benchmark claims: the questions in detail

A benchmark result is a measurement of one configuration on one set of items. Read it the way a trial is read: what was run, on what, how many times, compared with what, and scored how. Each question below names the `reporting` item that `scripts/extraction_check.py` expects for a benchmark or a vendor report.

## 1. What exactly was run (`what_was_run`)

- The exact model or software version, with a date. "The latest version" is not a version.
- Whether the system under test is the bare model or the model with tools, retrieval, a scaffold or several attempts per item.
- Whether the comparison systems were run by the author or quoted from someone else's report under different conditions. Quoted numbers are a different experiment.

If versions are missing, record it as not reported. The result cannot be repeated without them.

## 2. On what data (`test_set_origin`)

- Who wrote the items, and from what source.
- How many items. Run `python scripts/effect.py proportion --events K --total N` for each system: the interval is what that many items allow. With 50 items one item is 2 percentage points; with 500, 0.2.
- Whether the items were chosen before the systems were run. A subset picked after scoring ("the hardest questions") is selected on the outcome and will tend to show a gap.
- Whether the set is public, so that others can run it.

## 3. With what prompts and settings (`prompts_and_settings`)

- The full prompt for each system, including any worked examples.
- Temperature and other sampling settings, token limits, tool access, time limits.
- Whether every system received the same prompt. If one system had a prompt developed for it and the others a generic one, the comparison measures the prompt as much as the model.

## 4. How many runs, and how much they vary (`number_of_runs`, `run_to_run_variation`)

- Systems that sample give different answers on different runs. One run cannot show how large that spread is.
- Ask for the number of runs and the spread across them (range, standard deviation, or every run's score).
- If there is one run and no spread, say so. The item-count interval from `effect.py` covers which items happened to be in the set. It does not cover run-to-run variation, which comes on top.

## 5. Could the test set have been seen in training (`contamination_check`)

- When were the items published, relative to the model's training cut-off?
- Do the items come from the same source as training or fine-tuning data?
- Was any check made: exact-match search, a held-out set written afterwards, performance on freshly written items?

No check reported is a GAP. It is not proof of contamination and not proof of its absence.

## 6. Were the comparison systems tuned as carefully (`baseline_tuning`)

- How much effort went into the prompt and settings for the system being promoted, and how much for the others?
- Were the baselines run in the configuration their own makers recommend?
- A fair comparison gives each system the same budget of tuning, or reports each at its best published configuration.

## 7. Does the metric reflect the task (`metric_definition`)

- What counts as correct, and who or what decides. An automatic exact match, a rubric, a human marker, another model.
- If people marked the answers: could they see which system produced each one, and how often did markers disagree?
- If a model marked the answers: was it one of the systems under test, or from the same maker?
- Whether the score tracks what a user needs. Accuracy on short questions with one right answer says little about long documents, cost, speed or failure on unusual inputs.

## Recomputing a benchmark comparison

1. For each system: `effect.py proportion --events CORRECT --total ITEMS`.
2. For the comparison the claim rests on: `effect.py two-by-two --a-events ... --b-events ...`. State the difference in points and in items.
3. Say that the interval is unpaired. All systems answered the same items, so with per-item results the comparison should be paired, counting the items one system got right and the other got wrong. `effect.py` does not do the paired analysis. If per-item results are not published, that is a GAP, and the unpaired interval is what can be said.
4. If a relative figure is quoted ("36 percent fewer errors"), run `two-by-two` on the errors as well and show that it is the same handful of items.
5. To show what a larger set would allow, rerun `two-by-two` with the same percentages at a larger item count and label the result as an illustration. It is not a power calculation.

## What a careful benchmark report contains

Versions and dates; the full prompts; settings; item count and source; number of runs with the spread; a contamination check; how baselines were configured; the scoring rule and who applied it; per-item results. A report with all of these can still be wrong, but it can be checked. A report with none of them is a claim with an unknown method.
