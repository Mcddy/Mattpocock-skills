# Routing check: meta-prompt-engineer

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry and the likely winner recorded.

## Should trigger meta-prompt-engineer

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Help me write a system prompt for a bot that triages my client emails." | meta-prompt-engineer | |
| 2 | "My prompt keeps returning waffle instead of three bullet points. Here it is, fix it." | meta-prompt-engineer | |
| 3 | "Engineer a prompt that turns a central bank statement into a Cerberus macro read." | meta-prompt-engineer | |
| 4 | "I'm building a research assistant agent and need its underlying prompt designed." | meta-prompt-engineer | Borderline with multi-agent-designer; one agent, so this skill |
| 5 | "Refine this prompt: 'Summarise this document well.'" | meta-prompt-engineer | |
| 6 | "Make a meta prompt that generates prompts for my trade journal reviews." | meta-prompt-engineer | |

## Should not trigger meta-prompt-engineer

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Turn this into a Perplexity query for the last 12 months of RBA commentary." | nexus | nexus |
| 8 | "Run these four prompt variants against my 20 test emails and tell me which wins." | prompt-bench | prompt-bench |
| 9 | "Design a planner, researcher and reviewer agent team with handoff schemas." | multi-agent-designer | multi-agent-designer |
| 10 | "Write the Gumroad listing and licence for this prompt." | commercial-prompt-packager | commercial-prompt-packager |

Result: 10 of 10 judged correct, with 4 borderline. Re-run against a live router before relying on it.
