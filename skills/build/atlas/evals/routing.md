# Routing check: atlas

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of the registry skills and the likely winner recorded.

## Should trigger atlas

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Map out how BGP, OSPF and static routing relate and depend on each other." | atlas | |
| 2 | "Build me a mind map of the cyber security career landscape." | atlas | |
| 3 | "Diagram the dependencies between these Cerberus data feeds." | atlas | |
| 4 | "Here are my unit notes, turn them into a concept map." | atlas | |
| 5 | "Decision tree for choosing a firewall rule action." | atlas | Borderline with decision-board, but branching, not weighted criteria |
| 6 | "Show me the prerequisite tree for learning machine learning." | atlas | Borderline with learning-visualiser |

## Should not trigger atlas

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Simulate packet loss on a network and let me tweak the parameters." | simforge | simforge |
| 8 | "Compare three laptops by price, battery and weight with adjustable weights." | decision-board | decision-board |
| 9 | "Design a poster of the OSI model." | canvas-design | canvas-design |
| 10 | "Build me a portfolio site for my cyber projects." | showpiece | showpiece |

Result: 10 of 10 judged correct, with 5 and 6 borderline. Re-run against a live router before relying on them.
