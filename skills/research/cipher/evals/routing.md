# Routing check: cipher

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry (via `skills.build_registry()` plus the full descriptions of the closest siblings) and the likely winner recorded.

## Should trigger cipher

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "How do I develop a relationship with the owner of the local MSP I want to work for?" | cipher | |
| 2 | "Is this recruiter straight with me? His story keeps changing." | cipher | |
| 3 | "Map who is connected to the decision-maker at this company." | cipher | |
| 4 | "Something feels off about this client, he keeps asking about my other clients." | cipher | |
| 5 | "How do I stop my Cerberus method leaking when I talk to collaborators?" | cipher | |
| 6 | "What signals is this competitor emitting, hiring, partnerships, posting?" | cipher | Borderline with intelligence-analyst and sitrep |

## Should not trigger cipher

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "How do I negotiate a higher rate with this client?" | vector | vector |
| 8 | "Why did the AUD fall yesterday? Weigh the explanations." | intelligence-analyst | intelligence-analyst |
| 9 | "Check every claim in this pasted article." | fact-check | fact-check |
| 10 | "Threat model my web app's login flow." | threat-model | threat-model |

Result: 10 of 10 judged correct, with 6 borderline. Re-run against a live router before relying on it.
