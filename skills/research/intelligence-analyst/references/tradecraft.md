# Tradecraft reference

## 1. Analysis of Competing Hypotheses

Source: Richards J. Heuer Jr., *Psychology of Intelligence Analysis*, Center for the Study of Intelligence, 1999, chapter 8. The step list and the four quoted lines below were checked against a copy of the chapter in October 2026.

The eight steps:

1. Identify the possible hypotheses, ideally with people who see the problem differently.
2. List the significant evidence and arguments for and against each.
3. Prepare a matrix with hypotheses across the top and evidence down the side. Analyse the diagnosticity of the evidence.
4. Refine the matrix. Reconsider the hypotheses and delete evidence and arguments that have no diagnostic value.
5. Draw tentative conclusions about the relative likelihood of each hypothesis. Proceed by trying to disprove hypotheses rather than prove them.
6. Analyse how sensitive the conclusion is to a few critical items of evidence.
7. Report conclusions. Discuss the relative likelihood of all the hypotheses, not just the most likely one.
8. Identify milestones for future observation that may indicate events are taking a different course than expected.

Four lines from the chapter that this skill is built on:

- "Evidence is diagnostic when it influences your judgment on the relative likelihood of the various hypotheses".
- "The most probable hypothesis is usually the one with the least evidence against it".
- "The matrix should not dictate the conclusion to you."
- "Analyze how sensitive your conclusion is to a few critical items of evidence."

### What the earlier version of this skill got wrong

It reduced the method to: count the inconsistent cells in each column, call the column with the most the least likely, and report the leader with a confidence percentage. Three errors:

| Error | Why it matters |
|---|---|
| The count was treated as a likelihood | Items are not independent and not equally important. Five weak items against a hypothesis do not outweigh one sound disproof of its rival |
| Diagnosticity and sensitivity were skipped | Those two steps are where the method earns its keep. Without them the matrix is a tally of how many items the analyst thought of |
| A percentage was attached | Nothing in a matrix of judgements yields a percentage. The number made a judgement look measured |

### Rating scale

| Mark | Meaning | Ask |
|---|---|---|
| CC | Very consistent | If the hypothesis were true, I would strongly expect this |
| C | Consistent | I would expect this |
| N | Neutral or not applicable | It neither helps nor hurts |
| I | Inconsistent | I would not expect this |
| II | Very inconsistent | This is hard to explain if the hypothesis is true |
| ? | Not yet assessed | Makes the whole row incomplete; see below |

Rate across each row. If you cannot say how an item bears on a hypothesis, that is N or ?, not C.

### Incomplete rows

A row with `?` in any cell is incomplete. The script treats it as not yet part of the matrix:

- it adds to no tally, not even under the hypotheses it does rate;
- it is not used in the sensitivity test;
- it plays no part in judging which hypotheses are separated;
- it is listed as not assessed, with the advice to rate it before relying on the ranking;
- the output says how many rows of how many were complete.

The reason: the method compares hypotheses on the same evidence. A row rated II under one hypothesis and `?` under another would count against the first and say nothing about the second, and the gap would read as a difference between them. The earlier revision of the script did exactly that, and could name a stable sole leader from a single half-rated row while also saying the hypotheses were not separated.

If no complete row is diagnostic, there is nothing to order. The script's verdict is then "no basis": no leader, no stability result, no separation judgement. Report that, and say which ratings are missing. N is a judgement that an item does not bear on a hypothesis; `?` is the absence of a judgement. Do not turn `?` into N to make the row count.

### Credibility of an item

High, medium or low, from these questions: Could the source know this first-hand? Has it been reliable before? Is it corroborated by a source that could know independently? Does the source gain from being believed? Is the item a record or a recollection? Could it have been arranged to be seen?

### Reading the script's output

| Output | Meaning | What to do |
|---|---|---|
| NOT DIAGNOSTIC | Same rating under every hypothesis | Set it aside. Do not let its vividness count |
| WEAK | Differs in strength only (CC against C) | Treat as slight |
| Least contradicted | Fewest or lightest items against | A place to start the argument, not its end |
| The ordering at the top holds | One hypothesis leads under every weighting tried and with any one diagnostic item removed | Report it as least contradicted, with what is against the others. It is still not a probability |
| No single leader | The same two or more hypotheses are level at the top throughout | Report them as level. Say what would separate them |
| NOT stable | The leader changes with weighting or with one item removed | Report the dependence. Do not name a leader without it |
| NO BASIS | No complete row tells the hypotheses apart | There is no ordering. Say so, and say what needs rating or gathering |
| N of M row(s) complete | How much of the matrix the result rests on | Quote it with the result whenever N is less than M |
| NOT ASSESSED | The row has a `?` and was left out entirely | Rate it before relying on the ranking |
| SENSITIVE | Removing this item changes the leader | Scrutinise this item hardest: source, date, alternative readings |
| NOT SEPARATED | Two hypotheses rated alike on all diagnostic items | You need evidence that would differ between them. Say what it would be |
| UNTESTED | Nothing rated against it | Find what would be impossible if it were true, and look |

## 2. Key assumptions check

| Assumption | Stated or unstated | Status | If it fails |
|---|---|---|---|
| ... | ... | supported / unsupported / unknown | what the judgement becomes |

Prompts for finding unstated ones: What am I taking as fixed that could have changed? What am I assuming about what the other party knows, wants or can do? What am I assuming about my data being complete? What would have to be true for the opposite conclusion to hold?

Pick the assumption that is both least supported and most consequential. State it in the product.

## 3. Likelihood and confidence

One scale, used consistently. This is the scale in the US Intelligence Community's analytic standards (ICD 203), read from the published directive in October 2026:

| Term | Range |
|---|---|
| almost no chance | 1 to 5% |
| very unlikely | 5 to 20% |
| unlikely | 20 to 45% |
| roughly even chance | 45 to 55% |
| likely | 55 to 80% |
| very likely | 80 to 95% |
| almost certain | 95 to 99% |

The earlier version of this skill used a different table with different break points and labelled it a standard. It also said never to write "it is possible that" and always to assign a probability term. The better rule:

- "Possible", "may" and "could" on their own tell the reader nothing, so do not leave them as the whole judgement.
- Where there is a basis, use a term from the scale and give the basis.
- Where there is no basis, say so: "The evidence does not support an estimate of how likely this is. X would." Forcing a term onto an unsupported guess is false precision.
- Confidence (high, moderate, low) describes the evidence: quantity, quality, independence, consistency. The directive says a confidence level and a degree of likelihood must not be combined in the same sentence. Write two sentences.
- A range from the scale may be quoted with its term. A single figure is given only when computed from stated inputs, with the working shown.

## 4. Indicators

For each live hypothesis:

| Indicator | Would raise or lower | Where it would be seen | By when | Seen? |
|---|---|---|---|---|

Good indicators are observable, specific, and differ between hypotheses. "Further deterioration" is not an indicator. "The supplier issues a recall notice for batch 14 within thirty days" is. Include at least one indicator whose appearance would count against the leading hypothesis.

State the review trigger: a date, or an indicator firing.

## 5. Bias questions

Ask the ones that could change the answer and write a line for each:

| Question | Guards against |
|---|---|
| What would someone who disagrees say I have wrong? | Building a case |
| Which item did I meet first, and what if I had met it last? | Anchoring |
| Am I assuming they think like me, or want what I would want? | Mirror imaging |
| Is the striking item also the informative one? | Vividness |
| What would I expect to see that I have not looked for? | Availability |
| Which answer would I prefer, and have I been easier on it? | Wishful thinking |
| What is the base rate for this kind of thing? | Neglect of prior frequency |

If asking a question changes nothing, do not report it. If it changes something, say what.

## 6. Product formats

**Short**

```
JUDGEMENT:      one sentence
LIKELIHOOD:     scale term, or "no basis for an estimate"
CONFIDENCE:     level and reason, as its own sentence
RESTS ON:       the items and the assumption doing the work
ALTERNATIVES:   what remains live; what rules out the rest
WATCH:          the indicator that would change this
```

**Long**

```
QUESTION and as-of date
KEY JUDGEMENTS        numbered; each stands alone; likelihood and confidence in separate sentences
WHAT IS ESTABLISHED   facts with sources
ANALYSIS              hypotheses; what was set aside as not diagnostic; what counts against each;
                      the sensitivity result
ASSUMPTIONS           the table; the one that matters most
ALTERNATIVES          each remaining hypothesis and what would make it the leader
INDICATORS            the table; the review trigger
NOT KNOWN             gaps, and what would fill them
```

Write key judgements so that a reader who reads nothing else is not misled about how sure you are.
