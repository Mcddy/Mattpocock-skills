# Write-up: how to report an estimate

The script prints numbers. This file is about the page built on them.

## 1. Order of an estimate page

1. **Method line.** First line of the reply: "Fermi estimate: factors with ranges, simulated."
2. **Answer.** The median and the 90 percent range, with unit, time frame and scope, in one sentence. Then what to do with it.
3. **What was looked up and what was assumed.** A table of inputs, each tagged FACT (the source, its address and the date it was read), ASSESSMENT (the reasoning for the range) or GAP.
4. **Two decompositions**, when both were built: each result, whether the ranges overlap, and what the difference says.
5. **What drives it.** The top one or two inputs from the sensitivity table, and how to pin each down.
6. **Checks.** Anchors and the count of runs beyond each; one implied value divided back into something recognisable.
7. **What would change it.** Assumptions that, if wrong, move the answer out of its range; anything left out; inputs that may move together.
8. **To reproduce.** Model file names, runs and seed.

About a page. A quick ballpark asked in passing gets items 1, 2, 3 and 5 in a few lines.

## 2. Say this, not that

| Not this | This | Why |
|---|---|---|
| "The market is 620,000 households" | "Median 620,000 households; 90 percent range 270,000 to 1.4 million, during 2026" | One figure presented as known hides a factor of five |
| "About 1.2 million" when asked for a single number | "Around 620,000, and it could be anywhere from 270,000 to 1.4 million" | The single figure travels; make the range travel with it |
| "Expected cost 17,000" | "Median 11,000; mean 17,000 because of the upper tail; 18% of runs exceed the 25,000 budget" | A skewed result has a mean well above its typical outcome |
| "618,412 households" | "620,000" | Two significant figures at most. The inputs do not support more |
| "This cannot be estimated" | "The range is 2,000 to 900,000, too wide to plan on. It narrows most if the share who would pay is measured" | A range too wide to use is a finding, with a next step |
| "Between 5% and 25% of households" with no reason | "5% to 25%: most mow their own; older and time-poor households pay. Surprised outside that" | Every range carries its reasoning |
| "The two methods roughly agree" | "Top-down 270,000 to 1.4 million; bottom-up 450,000 to 3.5 million; they overlap from 450,000 to 1.4 million and the bottom-up median is twice the top-down" | Agreement is a range of overlap, not an adjective |
| Averaging two decompositions that do not overlap | "The ranges do not overlap. The gap traces to the operator count; until that is looked up, neither figure should be used" | Disagreement is information |
| A remembered statistic typed in as a FACT | A range with "from memory, not checked in this session" | A FACT is something read from a source now |

## 3. When one number is demanded

Give the median with its range in the same sentence, every time. If the user says they understand and still needs one cell for a spreadsheet, give the median and name what it is: "Use 620,000 (the median). Put 270,000 and 1.4 million in the cells beside it as the low and high cases."

For a decision with a threshold, the more useful single number is often the count of runs past the threshold: "3,696 of 20,000 runs go over budget (18%)".

## 4. A short worked sample

SYNTHETIC. A quick ballpark for a new service in a town of 26,000 households (the household figure is invented for this sample).

> Fermi estimate: factors with ranges, simulated.
>
> **Answer.** About 230 paying customers in the first year; 90 percent range 59 to 790. Plan stock and hours for a couple of hundred, and be ready for it to be under a hundred.
>
> | Input | Tag | Value | Basis |
> |---|---|---|---|
> | Households | FACT (SYNTHETIC) | 26,000 | invented for this sample |
> | Share with the problem | ASSESSMENT | 2% to 15%, lognormal | between one in fifty and one in seven; surprised outside that |
> | Share reached in year one | ASSESSMENT | 5% to 30%, uniform | a new entrant with no list reaches few; only bounds are known |
>
> **What drives it.** The share with the problem (rank correlation +0.77; on its own it moves the result from about 90 to about 680). The reach matters less (+0.60). Twenty doorstep conversations would narrow the first far more than any work on the second.
>
> **Check.** No run exceeds the 26,000 households. The median is about 1 household in 110.
>
> **What would change it.** The two shares are treated as independent. If the people with the problem are also the easiest to reach, the true figure sits higher.
>
> 20,000 runs, seed 1.
