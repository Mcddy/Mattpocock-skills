# Claude depth techniques

Prompts to add when a Claude answer is shallow. Pick one or two; stacking all of them wastes tokens. Wording is a starting point, tune it.

## Five-axis workflow assessment

| Axis | Question | Upgrade if low |
|---|---|---|
| Autonomy | Could this run without Shaun? | Add triggers, decision rules, fallback logic |
| Depth | Is the model reasoning or pattern-matching? | Add reasoning scaffolds |
| Pipeline maturity | Is a one-shot doing the work of a staged pipeline? | Redesign as stages |
| Resilience | What happens when inputs fail? | Validation gates, error handling |
| Compounding | Does it improve over time? | Memory, logging, feedback loops |

For a full assessment of Shaun's current approach, route to ai-power-user.

## Prompts

- **Extended reasoning.** "Before answering, reason through this exhaustively. Consider <angles>. Challenge your own assumptions. Then give your final answer." Use the host's native reasoning setting where one exists.
- **Adversarial self-review.** "Now argue against your own answer. What are the strongest objections? Which assumptions could be wrong?"
- **Hypothesis and evidence.** "Generate three competing hypotheses for <observation>. For each: what confirms it, what falsifies it, and a probability estimate with reasons."
- **Metacognitive flags.** Ask for [ASSUMPTION], [UNCERTAIN: reason] and [HEURISTIC] tags where the model is assuming, unsure or pattern-matching.
- **Iterative densification.** Pass 1 ideas; pass 2 cut anything that adds no new information; pass 3 tighten every sentence. Ask for all three before it returns.
- **Priority order for conflicts.** For example: accuracy, then actionability, then brevity, then directness.
- **Output schema.** Fix the shape of the answer, for example verdict, confidence 0 to 100, key finding, evidence quality (HIGH, MEDIUM, LOW), next action, as XML or JSON.
- **Delegation language.** "Work autonomously and decide where you can. Pause only if the action is irreversible, the direction is ambiguous, or it is outside scope. Document decisions inline."

Model IDs and pricing are deliberately absent. Use the claude-api skill or the vendor's current model list.
