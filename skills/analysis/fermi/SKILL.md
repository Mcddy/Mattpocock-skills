---
name: fermi
description: "Estimates a quantity that cannot be looked up by breaking it into factors with ranges, simulating the result, and showing which input matters most. Use for roughly how many, estimate the market size, ballpark, order of magnitude, back of the envelope, what would this cost a year. Not for forecasting whether an event will happen (oracle), scoring past predictions (calibrate), analysing data that already exists (data-intelligence) or anything that can simply be looked up."
metadata:
  revision: "1.1.0"
---

# Fermi: a range with its reasons

"How big is this market", "how many users could this handle", "what would this cost a year". The usual answers are a refusal or one invented number. This skill gives a third: break the quantity into factors, give each a range with a reason, propagate the ranges by simulation, and say which input is worth finding out.

A skill is instructions plus a script. It adds no knowledge of the world. Every range comes from the user, from a source read in the session, or from the model's stated reasoning, and is tagged as such.

## Use when

- A quantity is wanted that nobody has measured: a market size, a demand, a cost, a capacity, a count.
- The words are "roughly", "ballpark", "order of magnitude", "back of the envelope", "what would this cost a year".
- A single-figure estimate already exists and someone asks how solid it is.
- Two ways of estimating the same thing disagree and the gap needs explaining.

## Not this skill

| The job | Use |
|---|---|
| Will an event happen, and how likely | oracle |
| Log a prediction and score it later | calibrate |
| Analyse data that already exists | data-intelligence |
| Find and record sources for the inputs | deep-research-orchestrator |
| A simulation to explore with adjustable controls | simforge |
| Compare a few options on weighted criteria | decision-board |
| Counts and proportions from survey responses | response-analyst |
| A workbook model with formulas | spreadsheet-intelligence |
| Anything that can be looked up | No skill. Look it up and cite it |
| Plain arithmetic on known figures | No skill. Do the sum |

## Inputs

- **The quantity**, with whatever the user knows about unit, period and scope. Missing parts are chosen, stated and carried on with.
- **Anything the user already knows**: their own records, a pilot, a price list. These beat any outside figure.
- **The decision it feeds**, if there is one, and any threshold (a budget, a break-even). The threshold becomes an anchor.
- Nothing else is needed to start. Build a first version without asking; ask only when two readings of the question differ by more than the uncertainty.

## Tools: discover first

- A shell with Python 3.8 or later, for `scripts/fermi.py`. Standard library only, no installs. Without a shell: show a manual scenario calculation with assumptions. Products of marginal percentiles are not guaranteed bounds or joint percentiles. Only genuine bounded inputs and a monotone positive product permit endpoint bounds; formulas with subtraction, division or signed inputs need separate range analysis. Label the result manual, with no simulation or sensitivity table.
- Search and page reading, for step 2. Without them every outside figure is from memory: tag it ASSESSMENT, give it a range, and say nothing was looked up.
- oracle, calibrate and deep-research-orchestrator are named as next steps only if they are actually present.

## Procedure

The method in full, with the distribution table and the percentile conversion, is `references/method.md`.

1. **State the quantity** with unit, time frame and scope, so that it could in principle be checked.
2. **Look up what can be looked up.** If the whole answer can be looked up, give it with its source and stop. Otherwise each input becomes a FACT (source and date), an ASSESSMENT (reason for its range) or a GAP (could have been looked up and was not).
3. **Decompose two ways** where possible: top-down from a total, bottom-up from a unit. Three to six factors each.
4. **Give each uncertain input a range and a shape.** The range is the one the estimator would be surprised to fall outside. For lognormal and normal inputs, low and high are the 5th and 95th percentiles; for uniform and triangular they are hard bounds. Declare shares as `"kind": "probability"`. Start from `assets/model-template.json`.
5. **Run** `python scripts/fermi.py MODEL.json`. If it refuses the model, fix what it names: a missing `why` or `source`, low not below high, a name in the formula that is not an input.
6. **Read the sensitivity table.** Name the one or two inputs that drive the spread and how each could be pinned down.
7. **Check.** Anchors (a total it cannot exceed; a budget as a threshold). `python scripts/fermi.py --compare A.json B.json` for two decompositions. One implied value divided back into something recognisable. If two ranges do not overlap, or touch only at their edges with each median outside the other range (the script says which), find out why before reporting anything.
8. **Report** the median and the 90 percent range with the assumptions, in the order under Output. Wording to use and avoid: `references/write-up.md`.
9. **If the script was changed**, run `python scripts/test_fermi.py` and `python scripts/test_fermi.py --planted` before trusting it.

The formula in a model is read by a small parser inside the script: numbers, input names, `+ - * / **`, parentheses, `min` and `max`. Nothing a user types is ever run as code. If a formula needs more than that, restructure it; do not reach for another evaluator.

## Failure branches

- **No shell.** Bracket by hand as above and say so. Do not describe a simulation that was not run.
- **It can be looked up.** Look it up. An estimate of a published figure is worse than the figure.
- **Nothing can be looked up and no search tool.** Proceed with every input as an ASSESSMENT, and say that no figure was checked.
- **One number is demanded.** Give the median with its range in the same sentence. For a threshold decision, give the count of runs past the threshold.
- **The range is too wide to decide anything.** Say so, and name the input that would narrow it most. That is the result.
- **The two decompositions do not overlap, or overlap only at their edges.** Do not average them. Report both, the gap, and the input most likely to explain it. Say which one the plan should rest on and why, as an ASSESSMENT.
- **The model is refused.** Report the errors as printed. Do not loosen the model to get a run (for example by turning an unsupported guess into a fixed "fact").
- **The request is small.** "Is it nearer a hundred or a million" with obvious factors gets two lines of arithmetic and a range, with no model file.
- **A neighbour's job.** A yes or no about the future is oracle. Existing data is data-intelligence.
- **Money and investment.** The estimate is arithmetic on stated ranges. It is not advice, and the decision is the user's.
- **This skill's own ways of going wrong:** a remembered statistic typed in as a FACT; ranges drawn too narrow; the mean of a skewed result quoted as the estimate; digits added back that the script rounded away; inputs that move together treated as independent without saying so; a factor left out that neither decomposition contains; hours spent narrowing an input the sensitivity table shows does not matter.

## Output

The first line names the method: "Fermi estimate: factors with ranges, simulated."

Then, in about a page:

1. **Answer.** Median and 90 percent range with unit, time frame and scope, and what to do with it.
2. **What was looked up and what was assumed.** A table: input, tag (FACT, ASSESSMENT or GAP), value or range, basis.
3. **Two decompositions**, when built: each result, the overlap, what the difference says.
4. **What drives it.** The top inputs from the sensitivity table and how to pin them down.
5. **Checks.** Anchors with counts of runs beyond them; an implied value.
6. **What would change it.**
7. **To reproduce.** Model files, runs, seed.

A passing ballpark gets items 1, 2 and 4 in a few lines.

## Rules that always hold

- The estimate is a range with a median, never a single figure presented as known.
- Every uncertain input has a stated reason for its range; every fixed input has a source read in this session.
- Nothing a user supplies is evaluated as code. The formula goes through the parser or it does not run.
- No more precision is printed or written than the script gives: two significant figures at most.
- The mean of a skewed result is never given without the median beside it.
- Low and high mean the 5th and 95th percentiles for lognormal and normal inputs, and that is said wherever the ranges are shown.
- If two decompositions disagree, the disagreement is reported, not averaged away.
- Every estimate names its dominant uncertainty: the one input that drives the spread most, from the sensitivity table.
- A figure is a FACT only if its source was opened in this session; the address and the date it was read are written beside it. Anything else is an assumption with a range.
- A range too wide to use is reported as such, with the input to pin down.
- Inputs treated as independent are said to be so when it matters.

## What has and has not been tested

Everything below was run by the session that wrote this skill or by a second session that reviewed and repaired it on 2026-10-09, on Python 3.13. Both are author-side. Nobody independent has run any of it. The numbers are from the review's reruns.

- `scripts/test_fermi.py`: 26 tests, all passing. They check the normal and lognormal percentile conversions against hand-worked values, a product of two lognormals against the exact analytic result (median and 5th and 95th percentiles within four standard errors at 200,000 runs), fixed-only models against exact arithmetic, 17 precedence cases and 41 refused formulas in the parser, 4,000 random strings that must either evaluate or be refused cleanly, seed reproducibility, 31 refusals each paired with its valid neighbour, 13 code-like formulas refused at the command line, anchor counts, clipping of probability inputs, Spearman's coefficient and the comparison arithmetic.
- `--planted`: four broken copies of the script, each caught by its named test. Two treat a lognormal's low and high as its minimum and maximum (one by a three-sd conversion, one by clamping draws); one hands the formula to Python, which then accepts `__import__`; one calls two ranges compatible when they touch only at their edges.
- Changed in review: `--compare` now says when two ranges overlap only at their edges, with each median outside the other range, in place of calling them compatible.
- The review's own checks, not shipped: 49 checks (an unknown option, a missing value, a byte-order mark, an empty file, NaN, infinity, wrongly typed values, 30 refusals and valid neighbours, and an independent simulation with a different generator and seed that agreed with the printed 5th, 50th and 95th percentiles within 6 per cent). All passed, and two altered copies of the script each failed.
- Two worked examples: a top-down and a bottom-up model of one quantity, and a fully synthetic yearly cost model, each with an estimate written by the authoring session. The first uses one real official figure. In review its source page was opened and the figure confirmed on 2026-10-09; an earlier version had derived a count by subtraction that the source did not support, and it was replaced by the published one. A third pair of models, on invented inputs, was run in review and is not shipped.

Not tested: any model following this skill other than the session that wrote it; any real host's preview. Also not tested: any Python version other than 3.13 (the sampler uses only `random.random()`, which Python documents as stable across versions, but that was not run); whether estimates made with this skill turn out close to the truth, which only checking them against later counts can show; models with dependent inputs, which the script cannot represent.

## Acceptance cases

The full set travels with the source for review.

1. "Roughly how many households pay for regular lawn mowing?" Expect: a stated quantity with unit, period and scope; at least one input looked up and cited with a date, the rest tagged ASSESSMENT or GAP with reasons; two decompositions and their overlap; a median with a 90 percent range to two significant figures; the input worth finding out named.
2. "What would this metered service cost us a year?" with pilot notes and a budget. Expect: the range, the count of runs over budget, the mean shown only beside the median, and a recommendation to measure the dominant input.
3. "I need one number for the slide." Expect: the median given with its range in the same sentence, and no figure with more than two significant digits.
4. Negative control: "Will the council approve the application by March?" Expect: oracle leads. Second negative control: "What is the population of the country?" Expect: looked up and cited, with no model built.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
