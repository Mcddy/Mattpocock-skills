---
name: synthesis
description: "Finds where separate domains bearing on one situation interact: maps the domains in play, the points where one changes the answer in another, and the insight that only appears at the join. Use when a problem crosses fields (technical, financial, legal, human, operational) and single-domain answers conflict or miss something, or when the user asks for a multi-perspective or panel view. Not for one-question depth (apex-intelligence), scoring a plan (gladiator) or wide idea generation (wild-ideas)."
metadata:
  revision: "2.0.1"
  revised-from: "synthesis as exported 8 Oct 2026"
---

# Synthesis: what the domains do to each other

Most situations get answered one domain at a time: the technical answer, then the commercial answer, then the legal one. This skill looks at the joins. It asks where a fact in one domain changes the right answer in another, and reports only the interactions that change something.

## Use when

- A situation has parts in different fields and the user wants them considered together.
- Two sound single-domain answers point in different directions.
- "What does this look like from all angles", "what am I not seeing across these", "give me a panel view".

Use it on request. Do not append cross-domain commentary to answers that did not ask for it.

## Not this skill

| The job | Use |
|---|---|
| Depth on one question | apex-intelligence |
| Score a plan and prioritise gaps | gladiator |
| Many varied ideas | wild-ideas |
| Choose between options | decision-board |
| Run several skills in sequence | orchestrator |

## Inputs

- The situation, and what the user is trying to decide or do.
- Any domain material they supplied (a contract clause, a cost table, an architecture).

## Tools: discover first

- Search or supplied documents, for domain facts about the present. Unchecked domain claims are labelled.
- Domain skills present in the session. Use one for depth in its domain if it is available; otherwise reason directly and say the depth is limited.

## Procedure

### 1. List the domains in play

Name each domain that bears on the situation and rate it: central, relevant or peripheral. Choose from what the situation contains, for example technical, financial, legal and regulatory, people and organisation, operations, market and customers, security, time. Drop the peripheral ones. Three or four domains is typical. Seven is a sign of padding.

### 2. State each domain's own answer

One or two lines per domain: what this domain alone would say to do, and the fact it rests on. Mark each fact as supplied, checked or assumed.

### 3. Find the interactions

For each pair of central or relevant domains, ask: does something in A change what B should do? Keep a pair only if the answer is yes. Write each kept interaction as a statement with a direction:

> Because [fact in A], [conclusion in B] changes from [X] to [Y].

"A and B are both relevant" is not an interaction. Parallel observations are cut.

### 4. Name the main one

Pick the single interaction that most changes what the user should do. Say what a single-domain view would have recommended, and what the joined view recommends instead.

### 5. Integrate

One recommendation that takes the interactions into account, with the trade-off it accepts. If the domains truly conflict and nothing resolves it, say which domain's constraint is binding and why.

### Optional tools, on request

- **Inversion:** what would make this fail in each domain, and which failure spreads to the others.
- **Time:** whether the interaction changes at a week, a year and several years.
- **Scale:** whether it holds at one tenth and ten times the current size.
- **Opposition:** how a competitor or critic would exploit the weakest join.

### Panel view, on request only

When the user asks for a panel, write three to five named viewpoints (for example: the numbers, the sceptic, the specialist in the central domain, the person who has to run it, the contrarian). Each gives its position, its strongest objection to the others, and what would change its mind. Then say where they agree, where they do not, and your own call.

Label it for what it is: one model writing several viewpoints. It is a way to organise objections. It is not independent review, and agreement among the viewpoints is not evidence. If independent review matters, say so and suggest a separate checker or a different model.

## Failure branches

- **Only one domain matters.** Say so and answer in that domain. Do not manufacture joins.
- **No interaction changes anything.** Report that the domains are independent here. That is a finding.
- **A domain needs expertise you lack** (a jurisdiction's law, a clinical question). State the limit, give the general shape, and say who would know. For legal and financial points, give information for the user's decision, not a directive.
- **The key fact in a domain is unchecked.** Show how the main interaction changes if it is false.

## Output

1. Domains in play, with ratings.
2. Each domain's own answer, briefly.
3. The interactions that change something, as directed statements.
4. The main interaction and how it changes the recommendation.
5. The integrated recommendation and its trade-off.
6. Unchecked facts and what remains unresolved.

## Rules that always hold

- An interaction is reported only if it changes a conclusion.
- Cross-domain commentary is not added to answers that did not ask for it.
- A panel is always labelled as one model's structured viewpoints.
- Domain facts about the present are checked or labelled.

## What has and has not been tested

Corrected on 9 Oct 2026: this section said nothing had been run against a model. It now states what was run and by whom, and the pointer to review files was removed. Not independently retested.

Three author-run behaviour cases exist for this skill: overseas hosting against a data-location clause, a panel view, and a single-topic explanation with the skill loaded. The authoring session produced the replies and scripted checks graded them. They predate this correction. There has been no independent run and no measurement of whether any host loads this skill.

This skill and apex-intelligence overlapped in their earlier versions (both had a cross-domain step). The boundary drawn here, one question in depth versus the joins between domains, is a proposal and has not been tested for routing on any host.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. A small software business wants to store customer documents with an overseas host to cut cost; the cost table and a contract clause on data location are supplied. Expect: an interaction stated with direction (the clause changes the cost answer), the single-domain recommendation contrasted with the joined one.
2. "Give me a panel view on whether to open-source our SDK." Expect: named viewpoints with objections to each other, the one-model label, and a call.
3. Negative control: "Explain how TLS certificate chains work." Expect: this skill is not used.
