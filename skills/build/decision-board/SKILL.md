---
name: decision-board
description: "Builds an interactive decision board that shows which assumption flips the answer: options, weighted criteria and a sensitivity sweep. Use when the user requests a decision matrix, an interactive comparison or a sensitivity analysis of concrete options, or when a consequential choice has multiple competing criteria that warrant a board. Not for open-ended strategy or forecasting."
---

# decision-board

Turns a choice between concrete options into something the user can move: scored cells, weights, and a sweep that shows the smallest change that would flip the winner. The point is to see how fragile a ranking is.

## Use when

- A consequential choice has two to six concrete options and competing criteria; simple comparisons get a direct answer.
- The user asks for a decision matrix or help deciding.
- The user asks what a choice depends on, or whether a ranking is robust.

## Not this skill

| The request | Goes to |
|---|---|
| Open-ended strategy, timing or negotiation | the strategy skill |
| Forecast an outcome | the forecasting skill |
| Track a prediction for later scoring | calibrate |
| Generate options in the first place | wild-ideas |
| Compare specs with no decision to make | answer directly |

## Inputs

The options, what matters to the user, and any figures they already have.

## Tools

Check what this session has: lookup tools for current facts, a shell with Python 3, a way to render an interactive page. `scripts/sensitivity.py` needs only Python 3.

## Procedure

1. **Options and criteria.** Take both from the user's words. Add at most two criteria they missed and mark those as added.
2. **Score each cell** on 0 to 10. Every cell records its source: a lookup made in this session, a figure the user stated, or `GUESS`. Present-tense facts such as prices, limits and availability are looked up, not recalled.
3. **Weights.** Use the user's if stated, otherwise equal weights, and say which.
4. **Compute.** Write the board as JSON in the format at the top of `scripts/sensitivity.py` and run `python scripts/sensitivity.py board.json --json`. Take the ranking, margins and flip points from the script. Do not do this arithmetic by hand.
5. **Read the sweep.** The script gives, for each criterion, the smallest weight change that changes the winner, and for each cell the value at which the winner changes. The guessed cells with the smallest flips are the assumptions to verify first.
6. **Build the board.** An interactive page if the host can render one: weights the user can drag, live ranking, flip points marked, guessed cells visibly different. Otherwise the score table plus the sweep as a list.
7. **State the decision.**

## Output

- The board.
- One sentence in the form "X wins unless A or B", with the numbers.
- The guessed cells ordered by how easily they flip the result.
- What evidence would change the decision, and the board JSON so it can be rerun.

## Rules that always hold

- A guess is never shown as a fact.
- A near tie is reported as a near tie.
- The weighted sum is a way to expose assumptions. It does not prove the top option is the right call, and the output says so.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
