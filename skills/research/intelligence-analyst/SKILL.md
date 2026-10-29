---
name: intelligence-analyst
description: "Weighs competing explanations of evidence that is incomplete or contradictory and returns a calibrated judgement: a full set of hypotheses, a consistency matrix worked for diagnosticity and sensitivity, a key-assumptions check, likelihood in words kept apart from confidence, and indicators to watch. Use for what is really going on, why did this happen, assess this situation. Not for gathering sources (deep-research-orchestrator), forecasts or decisions (oracle) or checking a draft (fact-check)."
metadata:
  revision: "2.0.1"
  revised-from: "intelligence-analyst as exported 8 Oct 2026"
---

# Intelligence analyst: competing hypotheses, worked honestly

Takes a situation and the evidence about it and returns a judgement about what is going on: which explanations survive, which do not, how sure, on what the judgement depends, and what to watch. It is analysis of evidence already in hand. Gathering more is a different job.

The core method is Analysis of Competing Hypotheses, from Richards Heuer's *Psychology of Intelligence Analysis* (1999), chapter 8. `references/tradecraft.md` has the method in full, the likelihood scale, the product formats and the bias questions. `scripts/ach.py` works the matrix.

## Use when

- "What is really going on with X?", "why did this happen?", "which explanation fits?"
- The evidence is partial, some of it conflicts, and more than one story fits.
- A judgement is wanted with its confidence and its tripwires, not a summary.

## Not this skill

| The job | Use |
|---|---|
| Find and record sources | deep-research-orchestrator |
| Say what will happen, or build scenarios | oracle |
| Choose between options | oracle or decision-board |
| Verify the claims in a draft | fact-check |
| Assess a plan across domains | gladiator |
| Hard reasoning on a question with one right answer | apex-intelligence |

## Inputs

- The question, as a judgement to be made, and the time it refers to.
- The evidence: documents, data, observations, reports. For each item, where it came from.
- What the user already believes, if they say. It becomes one hypothesis among the others.

If the evidence is thin, say what is missing and do the analysis on what there is. If nothing has been gathered at all, this is a research job first.

## Tools: discover first

- A shell with Python 3 for `scripts/ach.py`. Without one, work the matrix in a table and say the tallies were done by hand.
- Search or file reading, only to check a specific item's source or date. Wider gathering belongs to deep-research-orchestrator.

## Procedure

### 1. Frame the judgement

State the question so that it has an answer: what, about whom or what, as of when. Sort what you have into three piles and keep them apart throughout: what is established (with its source), what is inferred, and what is unknown.

### 2. Lay out every hypothesis

List all the explanations a reasonable person could hold, not the two that come to mind. Always consider:

- the dull one (nothing unusual; noise; seasonality);
- the measurement one (the data or the report is wrong);
- the one the user favours, and the one they would dislike;
- "something not on this list", kept as a standing row.

Make them distinct enough that evidence could tell them apart. Two hypotheses that predict the same observations are one hypothesis for now.

### 3. List the evidence and arguments

One item per row. Include assumptions and logical arguments, and include **absences**: things that should have been seen if a hypothesis were true and were not. For each item note its source and how far it can be trusted: how could the source know, has it been right before, is it corroborated by an independent source, could it be mistaken or planted.

### 4. Build the matrix across, not down

Take one item at a time and ask, for each hypothesis in turn: if this hypothesis were true, how expected is this item? Rate CC, C, N, I or II. Working across a row forces the comparison. Working down a column builds a case for one hypothesis.

Save the matrix as CSV (`assets/matrix-example.csv` shows the layout) and run:

```
python scripts/ach.py matrix.csv
```

Use `?` only for a cell not yet rated. A row with `?` in any cell is incomplete, and the script leaves the whole row out: out of every tally, out of the sensitivity test and out of the judgement on which hypotheses are separated. It lists the row as not assessed and says how many rows of how many were complete. Rate the row before relying on the ranking. A rating under some hypotheses and silence under others is not a comparison.

The script gives one verdict and writes its summary from it: the ordering holds with one leader, the top is level between named hypotheses, the ordering is not stable, or there is **no basis**, which means no complete row tells the hypotheses apart and so there is no leader and no ordering to report.

### 5. Look at diagnosticity first

An item that fits every hypothesis equally tells you nothing about which is true, however vivid it is. The script marks these. Set them aside and notice how few items are doing the work. Those few are where to spend scrutiny.

### 6. Try to refute, then test sensitivity

Judge hypotheses by the evidence **against** them. The one left standing is usually the one with the least against it, not the one with the most for it; a mass of consistent evidence proves little if it is also consistent with the rivals.

The count of inconsistencies is a way to order the discussion. It is not a probability, and no percentage follows from it. Items are not independent or equally weighty, and one solid disproof outweighs several weak points.

Then ask what the result depends on. The script reports whether the top of the ordering changes when any one item is removed or when weak items are discounted. For each item the result hinges on, ask: what if it is wrong, misread, out of date or deliberately misleading? If the leading hypothesis rests on one low-credibility item, say exactly that.

A hypothesis with nothing against it has not been confirmed. It has not been tested. Say what evidence would test it.

### 7. Check the key assumptions

List what must be true for the leading judgement to hold, including things nobody stated. Mark each as supported, unsupported or unknown. Name the one that is both shakiest and most consequential, and say what the judgement becomes if it fails.

### 8. State the judgement

- Give the standing of **every** hypothesis, not only the leader: which are effectively ruled out and by what, which remain live.
- Use likelihood words from one fixed scale (in `references/tradecraft.md`) and only where there is a basis for one. If there is no basis for a likelihood, say the evidence does not support an estimate and say what would.
- State confidence separately, in its own sentence, and tie it to the evidence: how much, how good, how independent, how consistent.
- Give a number only if it was computed from stated inputs.

### 9. Set indicators

For each hypothesis still live, list observable things that would raise it and things that would lower it. Make them specific enough that someone could check: what, where, by when. Prefer indicators that would differ between hypotheses. State what should trigger a fresh look.

### 10. Ask the bias questions that could change the answer

Not a list of labels to tick. Three questions, answered in a line each: What would someone who disagrees say I have got wrong? Which item did I see first, and am I still leaning on it? Am I assuming the other party reasons the way I would?

## Failure branches

- **Only one hypothesis seems possible.** Then say what observation would be impossible if it were true, and check for it. If you cannot name one, the claim is not yet a hypothesis.
- **All the evidence comes from one source or one family.** Say so at the top. The analysis is then about what that source implies, and confidence is low whatever the matrix shows.
- **The user asks for a percentage.** Give the likelihood word and its range from the scale, and say plainly that a specific figure would be invented. If they supply base rates or data, compute and show the working.
- **Rows are still unrated, or the verdict is no basis.** Report the verdict together with the count of complete rows ("7 of 8 rows complete") and name the unrated rows. Do not present a leader as settled while a row that bears on it is unrated. On no basis, say there is no ordering yet and which ratings would give one. Do not rank from the cells that happen to be filled in.
- **The ordering is not stable.** Report it as unstable. Give the two or three live hypotheses and what would separate them. Do not pick one to seem decisive.
- **No time for the full method.** Do steps 2, 6 and 9 in short form: the alternatives, the strongest evidence against the favourite, one indicator. Say it was the short form.
- **The subject is a person.** Analyse their public role, statements and actions as they bear on the question. Do not build a psychological profile, infer private characteristics, or treat a guess about motive as a finding.
- **Evidence may be planted or self-serving.** Add "this item is deception or error" as a consideration in step 3, and test in step 6 what happens without it.

## Output

Short form, for a quick read:

```
JUDGEMENT:      one sentence
LIKELIHOOD:     a word from the scale, or "no basis for an estimate"
CONFIDENCE:     high, moderate or low, and the reason, in its own sentence
RESTS ON:       the one or two items and the assumption doing the work
ALTERNATIVES:   what remains live, and what rules out the rest
WATCH:          the indicator that would change this
```

Long form adds: the hypotheses, the matrix or its summary, the items set aside, the sensitivity result, the assumptions table, the indicators, and what is unknown. Facts, inferences and gaps stay visibly separate throughout.

## Rules that always hold

- No percentage is derived from a count of consistent or inconsistent items.
- Likelihood and confidence are never combined in one sentence or one number.
- Every hypothesis considered is reported, with what happened to it.
- An untested hypothesis is called untested.
- Facts carry their source. Inferences are marked as inferences.
- Nothing about a person's private life, health, beliefs or character is inferred.
- The matrix arranges the analyst's judgement. It does not make it.

## What has and has not been tested

**Correction in revision 2.0.1.** An independent reviewer showed that a row rated `?` under one hypothesis and II under another was listed as not assessed yet still counted against the second hypothesis, and that the output could name a stable sole leader while also saying the hypotheses were not separated. `ach.py` now leaves a row with any `?` out of every tally, the sensitivity test and the separation judgement, says how many rows were complete, and writes its summary from one verdict: the ordering holds, the top is level, not stable, or no basis. The correction was author-tested on 9 Oct 2026: the reviewer's one-row matrix (now no basis, nothing counted), a matrix in which every row has a `?`, the same row fully rated (it counts), an eight-row matrix with one cell unrated compared with the matrix with that row deleted (identical results, "7 of 8 rows complete"), 400 random matrices checked for a report that states two verdicts (none), and a copy of the script with the old behaviour put back, which the same check fails. It has not been independently retested.

Run in this package's build session: `ach.py` on a stable synthetic matrix (one leader under every weighting, one non-diagnostic item flagged, the leader flagged as untested because nothing is rated against it) and on a fragile one (the leader differs between the unweighted and weighted tallies, and four items each change the result when removed), plus malformed inputs. The script's JSON output contains no percentage sign. The method's eight steps and four quoted principles were checked against a copy of Heuer's chapter in October 2026.

Not tested: any model following this skill other than the session that wrote it; whether ratings a model assigns are good ones, which no script can check; the default weights, which are arbitrary and exist only so the script can show whether the ordering survives changing them.

## Acceptance cases

Four of the cases in words. The full set, with negative controls and input files, travels with the source for review.

1. "Sign-ups fell 40 percent last week. What's going on?" with the eight items in `assets/matrix-example.csv`. Expect: four or more hypotheses including a measurement one; the item about the team's worry set aside as not diagnostic; the pricing-page hypothesis reported as least contradicted **and untested**; no percentage; one indicator that would separate it from the rest.
2. A three-hypothesis, five-item matrix in which the leader by count differs from the leader by weight and rests on a low-credibility forum post. Expect: reported as unstable, with the dependence on that post named; no single leader asserted.
3. "Just give me the probability it was the supplier." Expect: a likelihood word with its range or "no basis", and a refusal to invent a figure, in one or two sentences.
4. Negative control: "Find me sources on lithium supply." Expect: deep-research-orchestrator leads.
