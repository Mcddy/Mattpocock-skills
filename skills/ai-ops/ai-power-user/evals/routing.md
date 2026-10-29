# Routing check: ai-power-user

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry and the likely winner recorded.

## Should trigger ai-power-user

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Here's how I run my weekly market research: I paste articles into Claude and ask for a summary. How do I push this further?" | ai-power-user | |
| 2 | "How do I make my morning brief run without me touching it?" | ai-power-user | Borderline with nexus-prime; the ask is how, not build the code |
| 3 | "What's the frontier approach to orchestrating several models on one research question?" | ai-power-user | Borderline with multi-agent-designer |
| 4 | "How do I get Claude to reason deeper on trade theses instead of the safe answer?" | ai-power-user | |
| 5 | "Rate my current agent setup and tell me what's holding it back." | ai-power-user | |
| 6 | "Design a pipeline for ingesting RBA releases and flagging only what matters." | ai-power-user | Borderline with nexus-prime |

## Should not trigger ai-power-user

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Which tool should I use for a competitor deep dive, Perplexity or NotebookLM?" | nexus | nexus |
| 8 | "Write a system prompt for a customer support bot." | meta-prompt-engineer | meta-prompt-engineer |
| 9 | "Design a team of planner, coder and reviewer agents with the handoff schemas and code." | multi-agent-designer | multi-agent-designer |
| 10 | "Price and package this prompt for Gumroad." | commercial-prompt-packager | commercial-prompt-packager |

Result: 10 of 10 judged correct, with 2, 3 and 6 borderline. Re-run against a live router before relying on those.
