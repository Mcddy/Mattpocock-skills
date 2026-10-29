---
name: tabletop
description: "Runs a turn-based tabletop exercise in the conversation: a scenario with injects, decisions each turn, outcomes from rules set in advance, and an after-action review against the user's own plan. Use for run a tabletop, walk me through an incident, drill me on this scenario, test my response plan, simulate a crisis turn by turn, wargame this decision. Not for a numeric simulation (simforge), a written stress test of a plan (oracle), a course (preceptor), or a quick what-if (answered directly)."
metadata:
  revision: "1.1.0"
---

# Tabletop: a turn-based exercise with rules written before play

A plan for an incident or a hard decision is untested until the day it is needed. A tabletop exercise tests it sooner: a scenario unfolds turn by turn, the user decides with incomplete and sometimes wrong information, consequences follow from rules that were written down before play began, and the review afterwards is measured against the user's own plan.

Three things make it an exercise and not a story:

- **Outcomes follow rules written before play.** The facilitator does not invent an outcome to be dramatic or kind. Where the rules are silent it says so, makes a judgement call, and gives the reason.
- **Hidden facts stay hidden** until something the player does discovers them.
- **The review has no score.** An exercise is a way of finding things out, not an exam.

The skill adds no memory and no background process. The whole state of an exercise is a compact block reprinted each turn; the state is reprinted in the conversation; if file logging is available, a local session log also persists at the disclosed path.

## Use when

- The user wants to practise or test a response: an outage, data loss, an account compromise, a supplier failing.
- A decision under uncertainty is worth walking through move by move: a launch, a negotiation, a budget cut.
- A study drill: working a networking or security fault step by step, with the facts withheld until tested for.
- The user has a runbook or plan and wants to know where it is silent or wrong.

## Not this skill

| The job | Use |
|---|---|
| A simulation with numbers and adjustable parameters | simforge |
| A written stress test of a plan, or a risk register | oracle |
| A course with lessons and mastery checks | preceptor |
| A quiz or questionnaire | elicitor |
| What could be abused in a system, and the test for each defence | threat-model |
| Explaining an incident that already happened | intelligence-analyst |
| A quick "what would you do if X" | no skill: answer directly |

## Inputs

Four things, asked for in one message, each with a default so the user can answer "go":

- **Type**: incident response, decision under uncertainty, or study drill.
- **The system or plan under test**, and the plan's steps if one exists. Use the user's words; do not improve the plan while copying it.
- **Objectives**: two to four things the exercise should reveal.
- **How long**: turns, and real minutes. Default 8 to 10 turns, about half an hour.

If the user wants to start at once, use a shipped scenario and say which.

## Tools: discover first

- **A shell with Python 3**, for `scripts/scenario_check.py` and `scripts/session_log.py`. Without one, check the scenario by hand against the error list in the first script's docstring, build the review's tables by hand from the log, and say both were done by hand.
- **A file system**, to append log lines to a file as play goes on. Without one, print each log line in the conversation, prefixed `log>`, and collect them at the end.
- **File reading**, for the user's runbook. Without it, ask them to paste the steps.
- Nothing else. No search is needed, and nothing is sent anywhere.

## Procedure

1. **Is it an exercise at all?** A quick what-if gets a direct answer. A request that belongs to a neighbour is handed over. See the failure branches.
2. **Agree the four inputs**, or take the defaults.
3. **Get a scenario file, before play.** Choose one from `assets/scenarios/` or write one from `assets/scenario-template.json`:
   - `assets/scenarios/outage-small-saas.json`: a database disk fills and the only person who knows the backups is away.
   - `assets/scenarios/account-compromise.json`: a mail account sends odd messages and a supplier's bank details change; one indicator is misleading.
   - `assets/scenarios/subnet-fault-drill.json`: a study drill in which one VLAN cannot reach a server because of a wrong prefix length. Its address facts are checked by `assets/scenarios/verify_subnet_drill.py`; run that after any edit.
   A scenario holds the setting, what the player knows, what is hidden, the injects (each with what the player is told, what is really true, and the objective it probes), the actions, the resources, and the adjudication rules. For the user's own system, put their plan's steps in `plan`.
4. **Check it.** `python scripts/scenario_check.py scenario.json`. Fix every ERROR; read every ADVISORY. Do not start play on a scenario with errors.
5. **Brief the player**: who they are, what they know, what they have, how turns work, and the active logging mode and local log path, or that the log exists only in the conversation. Not the hidden facts, the rules or which injects mislead.
6. **Run the turns**, following `references/facilitation.md`, in the fixed format of `references/turn-format.md`: apply clock rules, deliver injects, print the turn block (state block, what is new, a short menu, free input), wait, adjudicate by the rules, print the answer, write the log line. One turn block per reply. Commands `status`, `log`, `help`, `hint`, `pause` and `end` always work, and a hint is recorded.
7. **Log every line as it happens**, including clock rules and judgement calls. If the user supplied a plan, mark each decision as following, skipping or contradicting a step, or as one the plan is silent on.
8. **When play ends**, run `python scripts/session_log.py scenario.json play-log.jsonl`. It validates the log against the scenario and prints the tables. If it reports errors, they are the facilitator's: say so, correct what can be corrected, and put the rest in the review.
9. **Write the after-action review** from the tables, in the six parts given under Output.
10. **Stop there.** Offer a second run only if the plan has changed or the user asks.

## Failure branches

- **A quick what-if** ("what would you do if the database died?"). Answer it directly in a few sentences. Offer an exercise in one line if the question deserves one; do not start one.
- **No plan to measure against.** Run it anyway, with `plan` empty. Say at the start and in the review that decisions could not be logged against a plan, and make the first of the three changes "write one".
- **The scenario fails the check.** Fix it before play. A hidden fact nothing can discover either gets an action that finds it or moves to `unknowable`.
- **The request is a numeric model** (simforge), **a paper review of a plan** (oracle), **a course** (preceptor) or **a security model of a system** (threat-model). Hand it over.
- **The exercise would rehearse harming someone, targets a real named person, or casts a real person or organisation as the adversary.** Decline that framing. Offer the same exercise on the user's own system or a fictional organisation, with generic roles. `subject` in the scenario file is `own_system`, `own_plan` or `fictional`, never a real third party.
- **No shell.** Check and tabulate by hand, and say so. Do not report that a script passed.
- **The conversation is interrupted or runs long.** `pause` prints the state block and the log. To resume, the user pastes those and the scenario; recompute the state from the log before the next turn. If only the state block survives, play can continue, and the review covers only what the log holds: say so.
- **The player wants a score.** Give the counts with their denominators, and say in one sentence why they are not added up.
- **Real time runs out.** End and review what was played. Do not skip injects to finish, and do not add any.
- **The skill's own ways of going wrong.** Revealing a hidden fact in a menu, a hint or an aside; softening or sharpening an outcome; passing off a judgement call as a rule; inventing an inject mid-play; playing the player's move for them; printing several turns at once; reconstructing the log afterwards; turning the review into a grade or a comment on the person. Each is a facilitation error. If one happens, say so at the time and record it in the review.

## Output

The first line of the first reply names the method: **"Tabletop exercise: turn-based, outcomes from rules written before play, a review with no score."**

During play, every reply is terminal-style blocks in the fixed turn format, with at most a sentence of prose around them.

The after-action review has six parts, in this order:

1. **What happened**: the decision timeline with scenario times, and the time taken to each key action.
2. **What went well**, each item tied to an inject and an objective.
3. **What was missed or late**, each tied to an inject and an objective, with what was really true.
4. **Where the plan was silent or wrong.**
5. **Three concrete changes to the plan**, each with an owner placeholder and how to test it.
6. **What the exercise could not test**: injects not reached, what is unknowable, every judgement call, hints used.

Tag load-bearing claims FACT (in the log), ASSESSMENT (inference about the plan) or GAP. No score out of anything. Counts carry their denominators.

## Rules that always hold

- The scenario, with its rules and its hidden facts, is written and checked before the first turn.
- Outcomes come from the rules. Where they are silent, the reply says "judgement call" and why.
- A hidden fact is stated once, when an action, a rule outcome or an inject reveals it, and never before.
- An inject's "really true" entry is never read out during play.
- The player makes every move. The facilitator never plays for them and never prints two turns at once.
- The log is written as play goes on and is never tidied afterwards.
- The review has no score, describes decisions and not the person, and proposes exactly three changes.
- Scenarios are about the user's own systems and plans, or fictional organisations, with generic roles. No real individual is a target or an adversary.
- The player is told whether the log is conversation-only or written to a named local file.

## What has and has not been tested

Everything below is an author-side check: run by the session that built the skill on 9 Oct 2026, then rerun and extended the same day by a second session that repaired what it found. Nobody outside that authoring side has tested the skill.

- `scripts/test_scenario_check.py`: 35 tests, all passing, one or more per checker rule with its valid neighbour. The planted scenario with an undiscoverable hidden fact is caught by `test_planted_undiscoverable_hidden_fact`.
- `scripts/test_session_log.py`: 35 tests, all passing: the tables against a hand-built log with answers worked by hand, and each validation refusal. The planted log that reveals a hidden fact with no discovering action is caught, as a facilitation error, by `test_planted_hidden_fact_revealed_with_no_discovering_action`.
- `scripts/test_verify_subnet_drill.py`: 9 tests, all passing.
- Ten scratch copies of the scripts, each with one rule removed or one calculation broken (four in the scenario checker, four in the log validator, two in the subnet verifier): every one failed at least one test, including the test named for its rule.
- By hand, 29 runs of `scenario_check.py`, 23 of `session_log.py` and 11 of the subnet verifier on good, bad and edge inputs (unknown option, byte-order mark, empty file, invalid UTF-8, NaN, text or true where a number is read, a clock written `2140`, each spec rule with its valid neighbour). Exit codes were as documented and none produced a traceback.
- The three shipped scenarios and the template pass `scenario_check.py` with 0 errors and 0 advisory notes. The subnet drill's 20 address claims hold under Python's `ipaddress`. A generated run in which the player waits every turn validates for each of the three scenarios (23, 18 and 18 log lines), and one hand-written run of the account-compromise and subnet scenarios (22 and 16 log lines) validates with 0 errors.
- One complete author-run exercise of the outage scenario: 8 turns of 10, 26 log lines, 0 validation errors, one hint, one judgement call, four hidden facts found by action. Its transcript passes a script that checks five things (state blocks equal to the log's, no hidden fact before its discovery, no gated action in a menu too early, rule text read out word for word, inputs equal to the log's); four planted faulty transcripts each fail it.
- The second session wrote and played a scenario the skill does not ship (a go or hold decision, 6 turns, 21 log lines). The checker passed it first time. The log validator caught one real slip by the facilitator: a resource not logged as spent on an attempt the rules refused. That led to one new advisory in the checker, for an outcome marked `done: false` on an action that has a cost, with its test.

Not tested: any model following this skill other than the sessions that wrote and reran it; any real host's preview; a real person playing, which is the only test of whether the format holds attention and the review is useful; the account-compromise and subnet scenarios played as a conversation (their logs were written and validated, but no transcript exists); resuming from a pasted state block; a session long enough to lose its early turns from context.

## Acceptance cases

The full set, with negative controls and input files, travels with the source for review.

1. "Run a tabletop on our outage runbook, about half an hour." Expect: the method line; a checked scenario named before play; a briefing without hidden facts; one turn block in the fixed format ending at the prompt, and nothing played on the user's behalf.
2. Mid-exercise, the player does something the action list does not cover. Expect: an answer labelled as a judgement call with its reason, a log line carrying `"rule": "judgement call"`, and no hidden fact revealed by it without saying so.
3. A finished log is supplied with its scenario. Expect: `session_log.py` run or the tables built by hand and said to be; a six-part review; exactly three changes with owner placeholders and tests; no score.
4. Negative control: "What would you do if our payment provider went down for a day?" Expect: a direct answer in a few sentences, no scenario file, no turn block.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
