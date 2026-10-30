# Routing check: agent-hub

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry and the likely winner recorded.

## Should trigger agent-hub

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Triage my inbox." | agent-hub | Could also read as email; the description's "my inbox" phrase and the workspace context carry it |
| 2 | "Add a task to the queue to check S2's disk space, and tell me which agent should do it." | agent-hub | |
| 3 | "Point Codex at the agent hub and see what's in my task queue." | agent-hub | |

## Should not trigger agent-hub

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 4 | "Run my market research brief every weekday at 7am." | schedule | schedule |
| 5 | "Design a team of planner, coder and reviewer agents with handoff schemas." | multi-agent-designer | multi-agent-designer |

Result: 5 of 5 judged correct (3 should-trigger, 2 should-not), with prompt 1 borderline. The task specified 5 prompts; the standard's 6+4 set was not used. Re-run against a live router before relying on this.
