# Forecasting and scenarios

The techniques here (outside view before inside view, splitting into sub-questions, small frequent updates, keeping score) are the standard ones from the forecasting literature, chiefly Kahneman and Tversky on the planning fallacy and Tetlock's forecasting tournaments. They are stated from general knowledge and were not re-opened against the sources in this pass.

## 1. Make it resolvable

A forecast is a claim that a named observation will or will not be made by a named date.

| Vague | Resolvable |
|---|---|
| "Will the launch go well?" | "Will the product have 200 paying accounts on 31 March 2027, by the billing system's count?" |
| "Is the supplier reliable?" | "Will the next three orders each arrive within the quoted lead time?" |
| "Will rates fall?" | "Will the central bank's published cash rate on 1 July 2027 be lower than today's?" |

Write the date, the observation and where it will be read. If the user's question cannot be made resolvable, say what it was changed to.

## 2. Outside view, then inside view

1. **Reference class**: what is this a case of? Find the broadest class with data, then narrow while data remains. Several plausible classes give a range, which is informative in itself.
2. **Base rate**: how often does the outcome occur in that class? Give the count and the source.
3. **Adjust** for what is specific to this case. Say which way and roughly how far, and why this case differs from the class. Most adjustments should be modest; a strong story is not strong evidence.
4. No reference class at all? Say so. Confidence is then low whatever the reasoning, and the range is wide.

## 3. Sub-questions

Break a hard forecast into parts that can each be estimated or looked up, then combine. State how the parts combine (all must happen, any one suffices) because that changes the arithmetic. A chain of five steps each "likely" is not itself likely.

## 4. Scenarios

Scenarios differ in **what drives them**, not only in how good the outcome is. "Base, better, worse" along one line is one scenario with error bars.

For each scenario:

| Field | Content |
|---|---|
| Driver | The cause that makes this the path |
| Description | What the world looks like |
| Likelihood | A figure or scale word **with its own basis**, or "no basis" |
| Indicator | An early, observable sign it is unfolding |
| Falsifier | What would rule it out |
| Consequence | What it means for the decision |

Also include: the scenario in which the question's framing is wrong, and, where the stakes warrant, a low-likelihood outcome with severe consequence, described by its mechanism and not given a made-up percentage.

### On percentages

The earlier version of this skill printed a template with "Base case (~55%), Upside (~25%), Downside (~20%)" and a check that they sum to about 100. Filling in a template is not estimating. Rules now:

- A percentage needs a basis you can point to: a count from a reference class, a figure implied by a market price, the output of a model whose inputs are stated.
- One basis supports one likelihood. Three scenarios cannot share "most likely under normal conditions".
- With no such basis, use a word from the scale, or say there is no basis.
- Percentages for an exhaustive, mutually exclusive set add to 100. If they are not exhaustive, name the remainder.
- Words must be jointly possible. Two exclusive outcomes cannot both be "likely".

`scripts/scenario_check.py` enforces these.

## 5. The scale

From the US Intelligence Community's analytic standards (ICD 203), read from the published directive in October 2026:

| Term | Range |
|---|---|
| almost no chance | 1 to 5% |
| very unlikely | 5 to 20% |
| unlikely | 20 to 45% |
| roughly even chance | 45 to 55% |
| likely | 55 to 80% |
| very likely | 80 to 95% |
| almost certain | 95 to 99% |

Likelihood is about the event. Confidence is about the evidence behind the judgement. The directive says not to combine the two in one sentence. Write: "It is likely the part ships on time. Confidence is moderate: the base rate comes from ten orders."

## 6. Updating and scoring

- Set the review trigger when the forecast is made: a date, or an indicator firing.
- When evidence arrives, move in proportion to how much more expected it is under one scenario than another. Evidence that every scenario predicted should move nothing.
- Record the forecast, its likelihood and its resolution date at the time it is made, and score it when it resolves. calibrate does this if it is available. Without a record, there is no way to learn whether "likely" from this process means what the scale says.

## 7. Money and markets

For a position or an investment thesis, the product is: the thesis as a resolvable claim, the scenarios with their drivers and indicators, what would invalidate the thesis, and the risks to it. Price levels are quoted only when they come from the user's own plan or from data looked up in the session, with the source and time. This skill does not generate entry, stop or target prices, and what to do with the position is the user's decision. It is analysis, not financial advice.

## 8. Forecast record

```
QUESTION (resolvable):
RESOLVES ON / HOW:
REFERENCE CLASS and BASE RATE (with source):
ADJUSTMENTS and why:
SCENARIOS: driver / likelihood and basis / indicator / falsifier
FORECAST: one sentence with a likelihood
CONFIDENCE: level and reason, as its own sentence
REVIEW TRIGGER:
MADE ON:
```
