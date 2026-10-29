---
name: wild-ideas
description: Generates unusually diverse ideas by recording the user's own candidates first and then sampling the unlikely end of the model's distribution. Use when the user asks for ideas, names, angles, concepts or options that are not the obvious ones, says the ideas are generic or all the same, wants to brainstorm widely, or asks for wildcards and left-field options. Not for analysing or deciding between existing options.
---

# wild-ideas

Ideation that works against the model's pull toward the average answer. The user's own ideas are captured first, the predictable answers are named and set aside, and candidates are drawn from the low-probability end.

## Use when

- The user wants names, angles, concepts or options and says to avoid the obvious.
- The user says earlier ideas were generic or all alike.
- The user wants a wide brainstorm or left-field options.

## Not this skill

| The request | Goes to |
|---|---|
| Choose between options already on the table | decision-board |
| Analyse a market, competitor or situation | the analysis skill |
| Deep reasoning on one question | the reasoning skill |
| Write copy or a finished piece | autonomous-writer |

## Inputs

The target (what the ideas are for), hard constraints, and anything already tried.

## Tools

Check what this session has: a way to ask the user a structured question, a way to render an interactive page, access to a second model family. Each has a fallback below.

## Procedure

1. **Frame.** State the target and constraints in two lines. List the five most predictable answers and ban them.
2. **User candidates.** Retain candidates already supplied. Invite more only when their absence materially blocks the brief; otherwise proceed without a question. Keep supplied and generated ideas distinguishable.
3. **Diversify mechanisms.** Generate candidates with three framings: flip a constraint, change the audience, borrow from an unrelated field. Explain the mechanism behind each. Do not invent sampling probabilities or claim access to a model probability distribution. Use as many candidates as the brief needs; a short naming request stays short.
4. **Second family.** If another model family is reachable by tool or by the user pasting a prompt, run step 3 there as well. If not, record `single family`.
5. **Cluster.** Group candidates that share a core mechanism and keep the strongest of each group.
6. **Tag, do not rank.** Mark each survivor feasible, stretch or moonshot. Do not drop an idea for being strange.
7. **Present.** An interactive gallery if the host can render one, otherwise a numbered list grouped by cluster. The user's own ideas appear in the set, labelled as theirs.
8. **Hand off.** When the user has finalists, deciding between them belongs to decision-board.

## Output

A set of distinct clusters sized to the request. For each idea: a name, one line, why it is not the obvious answer, and its feasibility tag. End with the banned predictable answers, so the user can see what was avoided.

## Rules that always hold

- The banned list is honoured: none of the five predictable answers reappears reworded.
- No ranking and no winner. Selection is the user's.
- This is a heuristic for diversity. It does not establish novelty, feasibility or commercial demand; check those separately when relevant.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
