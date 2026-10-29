---
name: longhaul
description: "Sets up and governs a multi-hour autonomous coding run in Claude Code or Codex: spec, milestone plan with validation commands, runbook, status log and a failing-first feature list. Use when the user wants an agent to build something large unattended or overnight, asks how to keep a long run on track or resume it after context resets, or wants a harness for a long run. Not for designing the architecture (use forge or system-design), and not for completion checks on a single task (use done-gate)."
---

# longhaul

A harness for agent runs that last hours. State lives in files, not in the conversation, so every session, including one that starts after the context was compacted, can pick up exactly where the last one stopped.

## Use when

- The user wants an agent to build something large unattended or overnight.
- A long run keeps losing track after context resets.
- The user asks for a harness for a long run.

## Not this skill

| The request | Goes to |
|---|---|
| Design the architecture | forge or system-design |
| Design a multi-agent system | multi-agent-designer |
| An always-on monitor or pipeline | the infrastructure skill |
| Stop an agent claiming done on one task | done-gate |
| Carry a chat into a fresh chat | rebrief |

## Inputs

The repository, the goal, and the constraints (time, budget, what must not be touched).

## Tools

Check what this session has: version control, the project's run and test commands, a way to start a separate agent, the host's features for long work (stated goals or completion criteria, hooks, isolated working copies). Read the host's current documentation for those features in this session before relying on any of them.

## Procedure

1. **Preconditions.** The repository is under version control and has at least one check that runs. If not, create that first.
2. **Control files.** Copy the four templates from `assets/` into a `run/` folder and fill them in:
   - `SPEC.md`: what is being built, what is out of scope, constraints.
   - `PLAN.md`: milestones in order, each with the command that proves it.
   - `RUNBOOK.md`: how to start, the environment, the commands, how to recover.
   - `STATUS.md`: an append-only log: date, milestone, result, next step.
3. **Feature list.** Write `run/FEATURES.json` from `assets/FEATURES.template.json`: every feature with a check and `"passes": false`. Later sessions may change a feature to passing only after its check ran green in that session. Descriptions are never edited and features are never deleted.
4. **Roles.** One builder works through the list in order. Building in parallel makes agents take conflicting decisions; reading and reviewing can be parallel. An evaluator in a separate context tries to break each milestone using the real interface (tests, requests, a browser if one exists). If the session cannot start a separate agent, the builder runs the evaluator checklist itself and logs the milestone as `self-evaluated`.
5. **Session routine.** Every session starts the same way: read the tail of `STATUS.md`, run all checks, choose the next failing feature, state the plan in three lines, work, commit, append to `STATUS.md`.
6. **Stop conditions.** Everything passes; or a decision is needed that the spec does not settle (write the question to `STATUS.md` and stop); or the time or budget limit is reached.
7. **Enforcement.** Pair the run with done-gate so that "done" is decided by the checks.

## Output

The filled `run/` folder, the first `STATUS.md` entry, and the exact command or message that starts the run.

## Rules that always hold

- A feature is marked passing only by a check that ran.
- `STATUS.md` is appended to, never rewritten.
- A blocked run stops and says why. It does not guess past the spec.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
