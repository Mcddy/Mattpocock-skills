# Routing check: nexus

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry (via `skills.build_registry()` plus the full descriptions of the closest siblings) and the likely winner recorded.

## Should trigger nexus

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Should I do this competitor pricing research in Perplexity or just ask Claude?" | nexus | Tool choice across the stack |
| 2 | "Write me a Replit Agent brief for a small FastAPI app that logs my trades." | nexus | Borderline with forge; the ask is the brief for a named platform, not the build |
| 3 | "Set up a Perplexity then NotebookLM then Claude pipeline for tracking RBA decisions." | nexus | Borderline with deep-research-orchestrator; named tools and hand-offs favour nexus |
| 4 | "Turn this Claude XML prompt into something that works in Google AI Studio." | nexus | Platform-fit port |
| 5 | "Give me a Gemini Canvas blueprint for an interactive budget tracker." | nexus | |
| 6 | "Which should handle a 400-page PDF plus screenshots, Claude or Gemini?" | nexus | Routing between models |

## Should not trigger nexus

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "How good is my current AI workflow and what is the ceiling?" | ai-power-user | ai-power-user |
| 8 | "Write a system prompt for a customer support bot." | meta-prompt-engineer | meta-prompt-engineer |
| 9 | "Design a team of agents that triage my inbox and draft replies." | multi-agent-designer | multi-agent-designer |
| 10 | "Price and package this prompt for Gumroad." | commercial-prompt-packager | commercial-prompt-packager |

Result: 10 of 10 judged correct, with 2 and 3 borderline. Re-run against a live router before relying on 2 and 3.
