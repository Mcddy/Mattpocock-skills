# Routing check: dispatch

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of every skill in the registry (via `skills.build_registry()` plus the full descriptions of the closest siblings) and the likely winner recorded.

## Should trigger dispatch

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Give me a Cerberus brief on gold for the London session." | dispatch | |
| 2 | "I keep planning the newsletter but never publish it. Help me execute." | dispatch | |
| 3 | "What should I focus on today? Uni, the trading journal and Cerberus all want time." | dispatch | Borderline with heirloom-plan-capacity-week, which needs a fixed hour budget |
| 4 | "My notes system isn't working, things are spread over three apps." | dispatch | |
| 5 | "Run three lenses on AUD/USD ahead of the RBA decision." | dispatch | |
| 6 | "I check the same prices by hand every morning. Should I automate it?" | dispatch | Borderline with nexus-prime; the ask is whether, not build |

## Should not trigger dispatch

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Log the decision we just made and write context for next session." | mnemosyne | mnemosyne |
| 8 | "I have 12 usable hours this week, fit uni assignments, Cerberus and job applications in." | heirloom-plan-capacity-week | heirloom-plan-capacity-week |
| 9 | "Build and deploy an always-on alert that pings me when gold breaks a level." | nexus-prime | nexus-prime |
| 10 | "Do due diligence on this crypto exchange before I deposit." | oracle | oracle |

Result: 10 of 10 judged correct, with 3 and 6 borderline. Re-run against a live router before relying on them.
