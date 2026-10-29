# Routing check: vector

Judged simulation, not a live routing measurement. Each prompt was read against the registry descriptions (via `skills.build_registry()`) and the full descriptions of the closest siblings, and the likely winner recorded.

## Should trigger vector

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Plan the Cerberus launch as a campaign with phases and decision points." | vector | Borderline with dispatch |
| 2 | "Help me negotiate a higher day rate with this client." | vector | |
| 3 | "Who actually holds power in this company's hiring decision?" | vector | Borderline with cipher network mapping |
| 4 | "Should I move now on this contract or wait?" | vector | |
| 5 | "Is my plan for 25 hours a week of study plus work sustainable?" | vector | Borderline with heirloom-plan-capacity-week |
| 6 | "Prep me for a meeting with the MSP owner: what do they want, how do I open?" | vector | |

## Should not trigger vector

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "How do I build a long-term relationship with a mentor?" | cipher | cipher |
| 8 | "Why did the AUD fall yesterday? Weigh the explanations." | intelligence-analyst | intelligence-analyst |
| 9 | "Compare these three job offers on salary, learning and commute." | decision-board | decision-board |
| 10 | "Forecast the odds this startup survives two years." | oracle | oracle |

Result: 10 of 10 judged correct, with 3 borderline. Re-run against a live router before relying on it.
