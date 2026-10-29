# Routing check: interactive-generator

Judged simulation, not a live routing measurement. Prompts were read against registry descriptions and the closest siblings' full descriptions.

## Should trigger interactive-generator

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Build me a quick GST calculator for my sole trader invoices." | interactive-generator | |
| 2 | "I need a tool that converts subnet masks to CIDR and shows host counts." | interactive-generator | |
| 3 | "Quick app to time my study blocks with a Pomodoro counter." | interactive-generator | |
| 4 | "Make an interactive kanban board for this week's tasks." | interactive-generator | Borderline with pocket-app if saving implied |
| 5 | "Create a calculator for position size from risk percent and stop distance." | interactive-generator | |
| 6 | "Generate a small utility that formats pasted CSV into a markdown table." | interactive-generator | |

## Should not trigger interactive-generator

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "A trade journal I can reopen next week with my entries saved and exportable." | pocket-app | pocket-app |
| 8 | "Compare these three laptops across price, weight and battery with sensitivity." | decision-board | decision-board |
| 9 | "Simulate predator and prey populations with sliders." | simforge | simforge |
| 10 | "Build a quiz to test my networking knowledge." | elicitor | elicitor |

Result: 10 of 10 judged correct, with 1 borderline. Re-run against a live router before relying on it.
