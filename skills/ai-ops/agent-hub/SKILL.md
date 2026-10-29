---
name: "agent-hub"
description: "Work Shaun's agent coordination workspace at C:\\Users\\Shaun\\Desktop\\07_🗺️_SYSTEM\\_AGENT_WORKSPACE. Use when he says triage my inbox, what's in my task queue, add a task, which agent should do this, or points an agent at the agent hub / workspace."
---

# Agent hub

Shaun's agent coordination workspace lives at:

`C:\Users\Shaun\Desktop\07_🗺️_SYSTEM\_AGENT_WORKSPACE`

It is the shared filesystem layer between the many AI systems he runs, none of which share memory.

## Always do this first

1. Read `AGENTS.md` at the root of that folder. It holds the capability table and routing rules.
2. Read `CONTEXT/MACHINES.md`. It holds the durable facts about S1, S2, his network, and a
   "Not established" list of open questions. Never re-investigate something on that list and then state
   a confident conclusion. Never ask him something the file already answers.

## Hard rule

Do not move, rename or delete anything in that workspace that you did not create. Other agents are
pointed at existing paths. Additive changes only.

## Triaging the inbox

When he asks you to triage, or process the inbox:

1. List `INBOX/`, ignoring `README.md`.
2. For each item, work out what the task actually is and what it structurally requires: a command on
   Windows/S1, a command on Linux/S2, file synthesis, a coding run, or web research.
3. Match that requirement against the capability table in `AGENTS.md` and pick the agent. The
   constraint that cannot be worked around wins. Cowork cannot execute on S1 or S2, so anything needing
   a real command on his machines is never a Cowork task no matter how well it understands the problem.
4. Write `TASKS/<short-kebab-name>.md` in the same shape as the existing task files:

```
# Title

Status: queued
Agent: <which one>
Needs: <the structural requirement>

## Why
Two or three lines. Why this matters, what is currently unknown.

## Steps
Numbered, concrete, referencing real file paths that exist.

## Output
Where the result should land, and what to update afterwards.
```

5. Delete the inbox item once it is a task. Two copies is how work gets repeated.
6. Tell him what you created, one line each. Do not narrate the triage.

If an inbox item is not a task, say so and ask what he wants done with it rather than inventing one.

## Task state

One word on the Status line: `queued`, `active`, `blocked`, `done`. Changing that word is the entire
protocol. There is no other state anywhere. If a task is blocked, add a `Blocked by:` line saying what
would unblock it.

## Routing a one-off question

If he just asks "which agent should do this", answer from the capability table in `AGENTS.md` and give
the reason in one line. Do not create a task file unless he asks for one.

## Logging

If you did real work on his machines or changed files, append a report to
`ChatGPT/Projects/codex-agent-registry/README.md`, using the template at the top of that file.
Append only, never edit an earlier entry. Never write secrets, use `[REDACTED: type]`. Write
`UNVERIFIED` rather than guessing.

## What this system does not do

Nothing polls. No agent watches the inbox and no task starts on its own. It only moves when he opens an
agent and points it here. Do not imply otherwise.

