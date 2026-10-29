# Decisions and stress tests

## 1. How much process

| Stakes | Can it be undone? | Do |
|---|---|---|
| Low | Yes | Decide in a few lines: the facts, the choice, the first action. No ceremony |
| High | Yes | Options, a pre-mortem, a tripwire. Then act; you can correct |
| Low | No | Slow down slightly: what exactly cannot be undone, and is it really low stakes? |
| High | No | Everything in this file |

Most decisions are in the first two rows. Applying the full method to them is its own failure.

## 2. Options

List them, then add: doing nothing, doing it later, doing a smaller version first, and the option nobody has raised. For each, write the condition under which it would be the right choice. If two options have the same condition, they are not really different.

## 3. Ruin first

Before weighing anything, ask of each option: is there an outcome here I could not recover from? Loss of the business, of money that cannot be replaced, of something legal or physical. An option with a live path to ruin is set aside or restructured before expected value is considered. A favourable average is no use to someone who is out of the game.

## 4. Break-even, not invented odds

The earlier version of this skill asked for "probability of being right: [%]" and computed expected value from it. With no basis, that number is invented and the arithmetic decorates a guess.

Do this instead, when gain and loss can be put in the same unit. First say what the two figures are, because the same pair gives different answers.

**Net outcomes.** If it works you end up U ahead. If it does not you end up D behind.

```
break-even chance = D / (U + D)
```

A net gain of 12,000 against a net loss of 4,000: 4,000 / 16,000 = 25 percent.

**A cost paid either way.** You pay C whichever way it turns out. Success brings in G before the cost, or avoids a loss of G. Net gain is G - C and net loss is C.

```
break-even chance = C / G
```

Spend 4,000, paid either way, to avoid a 12,000 loss: 4,000 / 12,000 = one third. Reading that pair as net outcomes gives 25 percent and sets the bar too low.

"Spend X to save Y", "pay X for a chance at Y" and insurance-like choices are the second kind. "Win Y or lose X" is the first. State the reading in the reply. If the wording does not settle it, give both figures with what each assumes; do not pick one silently. `scripts/scenario_check.py` takes `"convention": "net"` with `upside` and `downside`, or `"convention": "gross"` with `cost` and `gross_gain`, and refuses a decision that does not say.

The option has positive expected value only if the chance of success is above the break-even figure. Now the question is concrete: is the real chance plausibly above it, and what is the evidence? Often that can be answered with a base rate or a reference class without ever stating a point estimate. If the real chance might sit either side of the figure, the decision is close, and the next step is whatever would move that estimate most cheaply.

Limits. The formula is for exactly two outcomes measured in one unit.

- **Three or more outcomes.** Do not run the two-outcome formula on each scenario. Figures made that way each ignore the other outcomes, cannot be compared, and do not add up to a decision. Do one of two things instead:
  1. Write the complete table: every outcome, its payoff in one unit, and its probability with its own basis, the probabilities adding to 100 percent. Expected value is the sum of payoff times probability. Show the working.
  2. If any probability has no basis, stay qualitative: set the outcomes side by side with their payoffs, say which outcome dominates the result and which cannot be survived, and say what evidence would let the table be completed. A table with one invented probability in it is an invented answer.

  The arithmetic of option 1, on made-up figures (SYNTHETIC, for the layout only):

  | Outcome | Payoff | Probability | Basis | Payoff x probability |
  |---|---|---|---|---|
  | Works fully | +8,000 | 30% | 3 of 10 comparable cases | +2,400 |
  | Works in part | +1,000 | 50% | 5 of the same 10 | +500 |
  | Fails | -4,000 | 20% | 2 of the same 10 | -800 |
  | Expected value | | 100% | | +2,100 |

- **Units that do not compare** (time against reputation). Do not force them into one number; set them side by side.
- **Ruin.** Expected value says nothing about a loss that cannot be survived. Section 3 comes first.

## 5. Weighted comparison, used carefully

Scoring options against weighted criteria is a way to make reasoning visible, not a way to compute the answer. If used: agree the criteria and weights before scoring, check whether the winner changes under reasonable changes to the weights, and when the table and your judgement disagree, find out why. One of them has noticed something the other has not.

## 6. Pre-mortem and its reverse

"It is a year from now. We chose this and it failed badly. What happened?" Write three failure stories, each with its mechanism, whether it could have been seen coming, and what would have prevented it.

Then: "It went better than we hoped. Why?" and ask whether the plan does enough to make that happen.

## 7. Second-order effects

What happens immediately. What happens because of that. Who responds, and how. What is no longer possible afterwards. Stop when the effects stop being specific.

## 8. Commit

```
RECOMMENDATION: one option, stated plainly
WHY:            the two or three reasons that carry it
REVERSED BY:    the assumption that, if wrong, changes the recommendation
TRIPWIRE:       the specific observation that should trigger a rethink
FIRST ACTION:   what to do next, by whom
NOT ESTABLISHED: what was not known when this was written
```

"It depends" is an answer only when followed by what it depends on and what to do in each case. If the evidence cannot separate two options, say so, and recommend the one that is cheaper to reverse.

Confidence is given in words with its reason. The earlier version asked for a 0 to 100 confidence figure; nothing in a decision process produces one.

## 9. Stress test

Standing permission to attack. Begin with the problem, not with praise.

1. **Restate the plan at its strongest.** If the author would not recognise it, you are attacking something else.
2. **Objections**, three to five, most serious first. For each: the mechanism by which it causes failure, and a rating.

| Rating | Means |
|---|---|
| Fatal | If true, the plan fails and nothing in the plan addresses it |
| Serious | Likely to cause failure or large loss unless fixed |
| Manageable | A real cost with a known remedy |
| Minor | Worth knowing; does not change the plan |

   For fatal and serious ones, give a specific fix or say that you cannot see one.
3. **Steelman the opposing view.** The best version, its evidence, why informed people hold it, and its single strongest point. If you cannot rebut that point, say so.
4. **Assumption audit.**

| Assumption | Stated? | Status | If false |
|---|---|---|---|
| ... | stated / unstated | supported / unsupported / unknown | consequence |

   Status is one of three words. The earlier version asked for "probability holds: Z%"; use the words unless there is data.
5. **Verdict**: robust, needs work, seriously flawed, or broken. Then the bottom line in two sentences.

If the plan survives, say so and say what you tried. An attack that finds nothing fatal is information.
