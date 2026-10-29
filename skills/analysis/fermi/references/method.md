# Method: estimating what cannot be looked up

Eight steps. `scripts/fermi.py` does the arithmetic in steps 5 to 7; the rest is judgement, and belongs in the write-up as assessment.

## 1. State the quantity so it could be checked

A quantity, a unit, a time frame and a scope. "How big is the market" is not a quantity. "Households in the region paying for regular lawn mowing during 2026, where regular means six or more paid visits a year" is: somebody could, in principle, count it.

If the request is vague, pick the reading that serves the decision, state it, and carry on. Ask only when two readings differ by more than the uncertainty in either.

## 2. Look up what can be looked up

An estimate is for what is left after looking. Before giving anything a range, check whether an official count, a price list, a log or the user's own records answers it. Each input ends up as one of:

| Tag | Means | In the model |
|---|---|---|
| FACT | Looked up, with source and date | `"dist": "fixed"` with `source` and `as_of` |
| ASSESSMENT | A judgement, with the reasoning for its range | Any other distribution, with `why` |
| GAP | Could have been looked up and was not, or cannot be known | An ASSESSMENT whose `why` begins "GAP:", and a line in the write-up |

If the whole quantity can be looked up, look it up and stop. That is the plain answer.

Never type a remembered figure in as a FACT. If it was not read from a source in this session, it is an ASSESSMENT with a range.

## 3. Decompose two ways

Top-down starts from a total and takes shares of it (households, times the share with the problem, times the share who would pay). Bottom-up starts from a unit and multiplies up (operators, times customers each). Build both where possible. They rest on different inputs, so agreement means something and disagreement says which inputs to look at.

Keep each factor something a person could reason about on its own. Three to six factors is typical. More factors do not make an estimate better; they hide the two that matter.

Check units through the formula: households x share x share is households.

## 4. Give each uncertain input a range and a shape

The range is the one the estimator would be surprised to fall outside: about a 1 in 10 chance of being outside it, half below and half above. That makes low and high the 5th and 95th percentiles.

| Shape | Use when | How low and high are read |
|---|---|---|
| lognormal | A positive quantity where the uncertainty is a factor ("somewhere between 2 and 50"), or the range spans much more than a factor of 2 | 5th and 95th percentiles |
| normal | An additive quantity that is about as likely to be above as below, with a range narrow against its size | 5th and 95th percentiles |
| uniform | Only bounds are known and nothing favours any part of the range | Hard minimum and maximum |
| triangular | Bounds are known and one value is most likely | Hard minimum and maximum, with `mode` |
| choice | A few discrete cases (a price tier, a yes or no) | `values` with `weights` |
| fixed | A looked-up fact | `value` |

The conversion the script uses, and tests:

```
normal:     mean = (low + high) / 2            sd = (high - low) / (2 * 1.6448536)
lognormal:  ln X is normal with
            mean = (ln low + ln high) / 2      sd = (ln high - ln low) / (2 * 1.6448536)
            so the median is sqrt(low * high)
```

1.6448536 is the 95th percentile of the standard normal distribution. Worked: lognormal with low 2 and high 50 has median 10 and sd of ln X 0.9785; normal with low 10 and high 30 has mean 20 and sd 6.080.

Two things follow that surprise people. A lognormal's low and high are not its minimum and maximum: one draw in twenty falls below low and one in twenty above high. And its median is the geometric middle, sqrt(low x high), which sits well below the arithmetic midpoint when the range is wide (2 to 50: median 10, midpoint 26).

Declare `"kind": "probability"` for any share between 0 and 1. The script refuses bounds outside 0 to 1, clips the rare lognormal or normal draw that leaves the interval, and reports how many it clipped.

Ranges tend to be drawn too narrow. After writing one, ask what would have to be true for the value to fall outside it, and widen it if that is easy to imagine.

## 5. Propagate by simulation

`python scripts/fermi.py MODEL.json`. Each run draws every uncertain input and evaluates the formula; 20,000 runs by default, at least 1,000. Draws use only Python's `random.random()` through the inverse distribution function, so the same model and seed give the same output on any Python 3.8 or later.

Report the median and the 5th to 95th percentile range. Percentiles are linear interpolation between order statistics at position (n - 1) x p, the definition numbered 7 in Hyndman and Fan (1996), "Sample quantiles in statistical packages", The American Statistician 50(4), pages 361 to 365.

The script prints two significant figures, or one when the range is wider than a factor of one hundred. Do not add figures back in the write-up.

A product of lognormals is skewed, so its mean sits above its median. The script prints the mean with a warning beside it. Never present the mean as "the estimate" without the median next to it. Where the question is a budget for expected spend, the mean is the relevant figure; say that it is a mean.

A check that the propagation is right: the product of two independent lognormals is lognormal, with the means of the logs added and the variances of the logs added. The test `test_product_of_two_lognormals_matches_the_analytic_result` compares the simulated median and 5th and 95th percentiles with that exact result.

## 6. Sensitivity: which input matters

The script prints two measures for each uncertain input.

- **Rank correlation** with the result: Spearman's coefficient, computed as Pearson's correlation of average ranks. Near +1 or -1 means the result moves with this input almost regardless of the others. Near 0 means it barely matters.
- **One-at-a-time swing**: the result with this input at its own 5th and 95th percentile and every other input at its median, and the factor between them.

The input at the top is the one worth finding out. Narrowing an input near the bottom is wasted effort, however easy it is to look up. Say which one or two inputs to pin down and how (a count from a register, two weeks of logs, five phone calls).

## 7. Sanity checks

- **Anchors.** A total the result cannot exceed, or a comparable known quantity, goes in `anchors` with a `max` or `min`. The script prints how many runs fall beyond each. If the reported range reaches past a hard limit, the model is wrong somewhere: fix it before reporting. An anchor can also be a threshold (a budget); then the count of runs beyond it is how often this model crosses it.
- **Two decompositions.** `python scripts/fermi.py --compare A.json B.json` says whether the two 90 percent ranges overlap and by how much. If they do not overlap, do not average them and do not pick the nicer one. Find the input that explains the gap.
- **Implied values.** Divide the result back into something recognisable (per household, per day, per operator) and ask whether that is believable.

## 8. Report a range with its assumptions

The estimate is a range with a median, a unit, a time frame and a scope, followed by the assumptions it rests on. Never one figure presented as known. If the user needs one number, give the median and say in the same sentence what range it sits in.

If the range is too wide to decide anything, say so, and say which input would narrow it most. That is a result.

## What the simulation does not know

- **Dependence between inputs.** The script draws each input independently. If two inputs move together (bigger towns have both more households and more operators), the true range is wider than printed; if they offset each other, narrower. Where dependence is strong, restructure the model so the shared driver is one input.
- **What was left out.** A missing factor is invisible to every check here. The second decomposition is the main defence.
- **Whether a range is honest.** The script checks that every range has a reason. It cannot tell a good reason from a poor one.
