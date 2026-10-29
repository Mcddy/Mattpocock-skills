---
name: gladiator
description: "Scores a plan or situation that spans several domains on five axes (information, strategy, execution readiness, compounding, risk control), names the single highest-leverage gap and gives a sequenced fix. Use for assess this plan, where is this weakest, what am I missing, a whole-situation critique. Not for choosing between options (decision-board), chaining skills into a pipeline (orchestrator), deep reasoning on one question (apex-intelligence) or finding cross-domain links (synthesis)."
metadata:
  revision: "2.0.1"
  revised-from: "gladiator as exported 8 Oct 2026"
---

# Gladiator: five-axis assessment of a plan or situation

Takes a plan, system or situation the user describes and returns a scored assessment: where it is strong, where it is thin, the one gap whose fix moves the most, and the order to act in. It assesses the work in front of it. It does not assess the person.

`references/domain-checks.md` holds short checklists for research, planning, building, AI pipelines and negotiation preparation. Load the ones that apply.

## Use when

- "Assess this plan", "where is this weakest", "what am I missing here", for something that touches more than one domain (for example a product launch with technical, commercial and operational parts).
- The user shares an approach or system and asks for a critique with priorities, not a list of everything.

## Not this skill

| The job | Use |
|---|---|
| Pick between a small set of options | decision-board |
| Run a task across several skills | orchestrator |
| Think hard about one question | apex-intelligence |
| Find how separate domains interact | synthesis |
| Verify the facts in a document | fact-check |
| A single-domain review (code, a prompt, an interface) | the skill for that domain |

## Inputs

- The plan or situation, in the user's words or a document.
- The goal: what "worked" would look like, and by when.
- Constraints the user has stated (time, money, people, tools).

If the goal is missing, infer the most likely one, state it in the first line and continue. Ask only when two plausible goals would produce opposite advice.

## Tools: discover first

- Web search or supplied documents, if the assessment depends on facts about the present (prices, competitors, rules, availability). Without them, score information quality on what was supplied and say that nothing was checked.
- Other skills present in the session. Name one as a next step only if it is actually available.

## Procedure

### 1. State the situation

Two or three lines: what is being attempted, the goal, the deadline, the constraints. Mark anything you inferred.

### 2. Score five axes

Each axis gets a score from 0 to 10, the evidence for it, and the gap. All five read the same way: higher is better. Every score must cite something the user supplied or something you checked in this session.

Two different things can be missing, and they are handled differently:

- **The plan lacks something a plan of this kind should contain** (no named sources, no risk list, no first action). That is evidence about the plan. Score the axis low and cite the absence.
- **A fact about the world is unknown** (whether demand exists, whether a supplier is reliable, what a competitor will do). That cannot be scored. Write "unknown" and list it.

Unknown never reads as fine. An axis you could not score is reported as a gap. In particular, a plan that says nothing about risk gets a low risk-control score, and its actual exposure is stated as unknown, not as low.

| Axis | What a high score means | Evidence to look for |
|---|---|---|
| Information | The facts the plan rests on are current, from more than one source, and checked | Sources named, dates, what has been verified |
| Strategy | The end state is specific and observable, with phases, decision points and branches | A written goal, milestones, if-then branches |
| Execution readiness | There is a defined first action, and the plan can be sustained with the resources named | Next action, owner, time and money against what is available |
| Compounding | The work leaves something reusable behind: knowledge, tooling, relationships, reputation | What exists after this that did not before |
| Risk control | The main risks are named, each with a mitigation or an accepted cost, and the single point of failure is known | A risk list, mitigations, what happens if the key assumption fails |

Anchors: 0 to 3 is absent or assumed, 4 to 6 is partly there with clear holes, 7 to 8 is solid with minor gaps, 9 to 10 is evidenced and tested. Do not average the axes into one number. The profile matters more than a mean.

The earlier version of this skill scored "threat exposure" with 10 as the worst case, the opposite way to the other four. That invited misreading, so this version scores risk control.

### 3. Name the highest-leverage gap

One gap. Choose the one whose fix raises the most axes or unblocks the others. Say what it is, why it comes first, what fixing it would produce, and how the user would know it is fixed.

If two gaps are tied, say so and say what would break the tie.

### 4. Sequence the actions

Three steps at most:

1. First: what has to happen before anything else.
2. Then: what builds on it.
3. Last: what makes the improvement stick.

Each step names who acts and what done looks like. Anything that sends, publishes, spends or deletes is the user's to do or to approve. This skill recommends; it does not act.

### 5. Check against the cycle (longer or higher-stakes work only)

Walk the plan through six stages and mark each present, thin or missing: collection (what was gathered and from where), processing (what was checked, what is uncertain), assessment (scenarios and the failure case), decision (the choice and what would reverse it), execution (phases and resources), learning (what gets recorded for next time). Report only the stages that are thin or missing.

## Failure branches

- **Too little to score.** Score what you can, mark the rest "not scored" or "unknown" as above, and list the three facts that would let you finish.
- **The plan depends on a fact you cannot check.** Flag it as the key assumption under Information and say what would confirm it.
- **The situation is single-domain.** Say so and point to the right skill if it is available. Give a short assessment anyway.
- **The user wants a decision between options.** That is decision-board. Offer it, and give the five-axis profile of each option only if asked.
- **Everything scores high.** Say so plainly. Do not invent a gap to have something to prescribe.

## Output

1. Situation, in two or three lines, with inferences marked.
2. The five axes: score, evidence, gap.
3. The highest-leverage gap and why.
4. The sequence, three steps at most.
5. What was not checked and what remains unresolved.

Keep it to what fits on one screen unless the user asked for depth.

## Rules that always hold

- A score without cited evidence is not given.
- The assessment is of the plan, not of the user's habits, discipline or personality.
- No personal facts are assumed. Everything about the user's situation comes from this conversation.
- Recommendations that touch other people are limited to honest, ordinary practice: preparing, asking, listening, keeping commitments.

## What has and has not been tested

Corrected on 9 Oct 2026: this section said nothing had been run against a model. It now states what was run and by whom, and the pointer to review files was removed. Not independently retested.

Three author-run behaviour cases exist for this skill: a newsletter plan, a payroll switch where unknown exposure must not read as low, and an option choice with the skill loaded. The authoring session produced the replies and scripted checks graded them. They predate this correction. There has been no independent run and no measurement of whether any host loads this skill.

The axis anchors are a judgement aid, not a validated instrument: two runs on the same plan may differ by a point or two.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. A plan for a paid newsletter with a schedule but no named sources and no risk list. Expect: Information and Risk control scored 4 or lower with the missing items cited, actual exposure stated as unknown, one gap named, three steps or fewer.
2. A plan with no stated goal. Expect: the inferred goal on the first line, marked as inferred.
3. Negative control: "Should I use Postgres or SQLite for this?" Expect: this skill does not lead; decision-board does if present.
