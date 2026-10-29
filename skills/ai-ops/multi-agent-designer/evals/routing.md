# Routing check: multi-agent-designer

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry and the likely winner recorded.

## Should trigger multi-agent-designer

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Design a multi-agent system that runs macro, technical and sentiment lenses and merges them." | multi-agent-designer | |
| 2 | "Design a team of agents that triage my inbox and draft replies, with handoff schemas." | multi-agent-designer | |
| 3 | "How do I orchestrate Perplexity, Gemini and Claude in one pipeline in Python?" | multi-agent-designer | Borderline with nexus; code and orchestration favour this skill |
| 4 | "Agent architecture for a research assistant with a critic that reviews drafts." | multi-agent-designer | |
| 5 | "Build an agent that calls other agents for planning, coding and review." | multi-agent-designer | |
| 6 | "What is the right orchestration pattern for 5 specialist agents and one human approval step?" | multi-agent-designer | |

## Should not trigger multi-agent-designer

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Which tool should I use, Perplexity or NotebookLM, for this competitor scan?" | nexus | nexus |
| 8 | "How good is my current agent setup and what limits it?" | ai-power-user | ai-power-user |
| 9 | "Write the system prompt for my summariser agent." | meta-prompt-engineer | meta-prompt-engineer |
| 10 | "Build a scheduled pipeline with a dry run and kill switch that posts my daily brief." | nexus-prime | nexus-prime |

Result: 10 of 10 judged correct, with 3 borderline. Re-run against a live router before relying on it.
