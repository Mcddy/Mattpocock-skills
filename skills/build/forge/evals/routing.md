# Routing check: forge

Judged simulation, not a live routing measurement. Method: build the registry (`python3 -c "import sys; sys.path.insert(0,'scripts'); import skills; print(skills.build_registry())"`), read every skill's one-line description, and record which skill a router would pick for each prompt. The forge one-liner is: "Use first to build a working app, tool, system or API end to end: a design pack with architecture diagrams and learning notes (stop 1), a hardened back end, ..." The description was not changed by the progressive-disclosure split.

## Should trigger forge

| # | Prompt | Picked | Why |
|---|---|---|---|
| 1 | "Build me an invoicing app for my plumbing business that shows what is overdue and works on my phone." | forge | End-to-end app with a back end and a device constraint. |
| 2 | "Make a stock-count tool with a database that I can run on my laptop with a double-click." | forge | Repo tier: server, storage, `run.bat`. |
| 3 | "I want a Windows EXE for tracking when my plants need water, with an icon, built properly." | forge | Release tier. |
| 4 | "Build a booking API with validation and tests, and show me architecture options before you write code." | forge | Hardened back end plus Stop A. |
| 5 | "Take my idea for a support-ticket queue from nothing to a working app. Give me a design doc and let me pick the look." | forge | Design pack plus the 16-look board. |
| 6 | "Build a one-file demo of a recipe scaler so I can try the idea, with a few looks to choose from." | forge | Demo tier with the board. Closest rival is interactive-generator; the "looks to choose from" and "demo of an idea" wording favours forge. |

## Near misses (should not trigger forge)

| # | Prompt | Winner | Why |
|---|---|---|---|
| 7 | "Build an award-winning portfolio site for my photography with scroll-driven animation." | showpiece | Award-grade site, no app behind it. |
| 8 | "This dashboard looks AI-generated. Clean up the UI and keep the flows working." | anti-vibecoded-ui | Clean-up of an existing front end, no build. |
| 9 | "Write a command-line tool for renaming files, with good --help and exit codes." | interface-architect | CLI rules. |
| 10 | "One HTML page where I track my reading list and it remembers my entries in the browser, no server." | pocket-app | Serverless save-my-data tool. |

## Result

10/10 by judged simulation (6 of 6 should-trigger, 4 of 4 near misses to the named sibling). Weakest case: prompt 6, which an interactive-generator or pocket-app route could also take. Re-run after any description change.
