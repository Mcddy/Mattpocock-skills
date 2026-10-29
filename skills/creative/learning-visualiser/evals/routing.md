# Routing check: learning-visualiser

Judged simulation, not a live routing measurement. Prompts were read against registry descriptions and the closest siblings' full descriptions.

## Should trigger learning-visualiser

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Visualise how TCP congestion control works with a window slider." | learning-visualiser | Borderline with simforge |
| 2 | "Make me an interactive explainer for public-key encryption." | learning-visualiser | |
| 3 | "Teach me how gradient descent works visually." | learning-visualiser | |
| 4 | "Show me how a packet moves through NAT, step by step." | learning-visualiser | |
| 5 | "Interactive explainer for how DNS caching works." | learning-visualiser | |
| 6 | "Make a learning tool for how subnetting splits an address." | learning-visualiser | Borderline with interactive-generator |

## Should not trigger learning-visualiser

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Build an animated course on the whole CCNA syllabus." | percept | percept |
| 8 | "Make a study app with quizzes and spaced review for security fundamentals." | preceptor | preceptor |
| 9 | "Check this chart I made for teaching for misleading scales." | heirloom-audit-learning-visualisation | heirloom-audit-learning-visualisation |
| 10 | "Map how all the concepts in OSI relate to each other." | atlas | atlas |

Result: 10 of 10 judged correct, with 2 borderline. Re-run against a live router before relying on it.
