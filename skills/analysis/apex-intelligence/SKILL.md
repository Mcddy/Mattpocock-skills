---
name: apex-intelligence
description: "Deep reasoning pass on one hard question: restate the real question, work it through a few named lenses, stress-test the leading answer, and give calibrated confidence with what would change it. Use when the user asks to think hard about, stress-test or get to the bottom of a single question. Not for sourcing and verifying facts (fact-check, deep-research-orchestrator), scoring a whole plan (gladiator), finding cross-domain links (synthesis) or choosing between options (decision-board)."
metadata:
  revision: "2.0.1"
  revised-from: "apex-intelligence as exported 8 Oct 2026"
---

# Apex intelligence: a structured pass on one question

A fixed sequence for a question that deserves more than a first answer: find the question behind the question, apply a small number of lenses and actually use them, attack the leading answer, then say how sure you are and why.

It is a procedure. It does not make the model more capable than it is, and it does not replace looking things up. Where the answer turns on a fact about the present, check the fact.

## Use when

- "Think hard about this", "stress-test this conclusion", "what am I not seeing in this question", "steelman the other side".
- A single judgement call where a wrong answer is costly and the first answer came too easily.

Use it when asked, or when the user's standing preferences call for depth on this kind of question. Do not switch it on by default for ordinary questions: the extra structure costs time and reading.

## Not this skill

| The job | Use |
|---|---|
| Find and verify facts | fact-check, deep-research-orchestrator |
| Score a plan across domains | gladiator |
| Find where separate domains interact | synthesis |
| Choose between listed options with weights | decision-board |
| Generate many varied ideas | wild-ideas |
| Track whether predictions came true | calibrate |

## Inputs

- The question.
- What the user already believes, if they said.
- What hangs on it: the decision it feeds and the cost of being wrong.

If the stakes are not stated, infer them and say so.

## Tools: discover first

- Web search or supplied sources, for any premise about the present. If neither exists, list the premises you could not check.
- Code execution, for arithmetic and estimates. Run the numbers; do not eyeball them.

## Procedure

### 1. Reframe

Write four lines:

- Asked: what was literally asked.
- Needed: the question whose answer would actually settle the matter.
- Unasked: the adjacent question the user would want raised.
- Stakes: what depends on the answer.

Then answer the "needed" question, and say in one line that you narrowed or shifted it. If the reframe changes what the user asked for, keep theirs as the main line and offer yours as the addition.

### 2. Choose two to four lenses and use them

Pick the lenses that could change the answer. Apply each to the specifics. A lens that is named but produces no new statement about this question is cut.

| Lens | Fits | What it should produce |
|---|---|---|
| First principles | Inherited assumptions may be wrong | The premises listed, with the weakest marked |
| Second-order effects | A choice with consequences over time | What happens after the obvious result |
| Inversion | Risk and failure | The conditions under which this fails |
| Base rates and updating | Predictions | The reference class, its base rate, and how the evidence moves it |
| Incentives and other players | Others can respond | What each party does next, given what they want |
| Feedback loops | Systems that reinforce or damp | The loop, and where a small push matters |
| Time horizons | Plans | The answer at a week, a year and a decade, if they differ |
| Steelman | Before settling | The strongest case for the answer you reject |
| Asymmetry | Uneven payoffs | Where downside is capped and upside is not, or the reverse |
| Estimation | Unknown quantities | Components, a range for each, the combined range, a sanity check |

### 3. State the leading answer

One or two sentences. Commit to it.

### 4. Stress-test it

- The three most likely ways it is wrong, ranked likely, possible or remote. Give a percentage only when you have a base rate or data to derive it from, and show the derivation. Otherwise use the words.
- For each: how bad it would be, and what you would see first if it were happening.
- The premise that, if false, reverses the answer.
- If the test breaks the answer, change the answer. Do not report a conclusion you have just undermined.

### 5. Calibrate

Say two things, in separate sentences, once, at the end of the pass.

**Likelihood** is about the world: how probable it is that the leading answer is right, or that the event it predicts happens.

| Phrase | Meaning |
|---|---|
| Near certain | Would be surprised to be wrong |
| Likely | More probable than not, with a named way it could fail |
| Toss-up | Neither side is favoured |
| Unlikely | Possible, with a named reason it could happen |
| Cannot say | There is no basis for a likelihood; say what is missing |

**Confidence** is about the evidence behind that judgement: high, moderate or low, with the reason. How much of it was checked or computed, how much is inference, and whether the sources are independent.

Example: "It is likely the rewrite will not pay back within a year. Confidence is low: there is no measurement of where the time goes." A judgement can be likely on thin evidence or a toss-up on good evidence, which is why the two are not merged.

Add what specific evidence would move the likelihood, and what would raise the confidence. These are the meanings oracle and intelligence-analyst use. When handing a judgement to either, restate the likelihood in that skill's scale. Formal labels are for this closing judgement, not for every sentence.

### 6. Leverage

Close with only the items that have real content:

- The insight: the one thing from this pass the user probably did not have.
- The move: the action with the best expected effect.
- The warning: the main thing to avoid.
- The next question.

If there is no asymmetric bet or no warning, leave that line out.

## Failure branches

- **The question cannot be settled by evidence** (values, taste, the unknowable future). Say so first. Give the positions a careful person could hold and the assumption each one rests on. Do not present a verdict as a finding.
- **A premise cannot be checked.** Carry it as an assumption, labelled, and show how the answer changes if it is false.
- **The lenses disagree.** Report the disagreement and which lens you weight more, and why.
- **The question is simple.** Answer it in a few lines and say the full pass was not needed.

## Output

Lead with the answer, how likely it is, and the confidence in the evidence. Then the reasoning in the order above, as short as the question allows. End with what remains unresolved. Make it plain which statements were computed or looked up, which are inference, and which rest on something unknown. Formal tags are for claims the decision turns on, not for every sentence.

## Rules that always hold

- No number is invented. A probability appears only with its derivation.
- Likelihood (how probable) and confidence (how good the evidence is) are stated separately and never merged into one word or number.
- Anything about the present is looked up or labelled unchecked.
- If the stress test changes the answer, the answer delivered is the changed one.
- The pass does not run unprompted on routine questions.

## What has and has not been tested

Corrected on 9 Oct 2026: step 5 now separates likelihood (how probable) from confidence (how good the evidence is), matching oracle and intelligence-analyst. Not independently retested.

Three author-run behaviour cases exist for this skill: a price rise with numbers supplied, a Rust rewrite with none, and a trivial question with the skill loaded. The authoring session produced the replies and scripted checks graded them. They predate this correction, so they show the earlier single confidence line. There has been no independent run and no measurement of whether any host loads this skill.

There is published evidence that asking a model to critique its own answer without new information does not reliably improve it, so step 4 is strongest when it brings in a fact that was looked up or computed, and weakest when it only re-reads the first answer.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. "Think hard: is it worth rewriting our working Python service in Rust for speed?" with no numbers given. Expect: a reframe, the lenses applied to this case, no invented percentages, the missing measurements listed, and a closing likelihood with a separate confidence sentence.
2. "Stress-test my conclusion that our churn is caused by pricing." Expect: three failure modes ranked in words, the premise that reverses it, and what data would settle it.
3. Negative control: "What's the capital of Australia?" Expect: a direct answer and no procedure.
