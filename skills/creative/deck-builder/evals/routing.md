# Routing check: deck-builder

Judged simulation, not a live routing measurement. Each prompt was read against the descriptions of the registry skills and the likely winner recorded.

## Should trigger deck-builder

| # | Prompt | Judged winner | Note |
|---|---|---|---|
| 1 | "Build me a 12 slide investor deck for Cerberus Intelligence." | deck-builder | |
| 2 | "Make slides for my networking assignment presentation on OSPF." | deck-builder | |
| 3 | "Turn this report into a briefing deck for my manager." | deck-builder | Borderline with folio, but the deliverable is slides |
| 4 | "I need a PowerPoint on zero trust for a workshop." | deck-builder | |
| 5 | "Create a pitch deck for my prompt packs." | deck-builder | |
| 6 | "Design a training deck on phishing awareness, 15 slides." | deck-builder | |

## Should not trigger deck-builder

| # | Prompt | Should go to | Judged winner |
|---|---|---|---|
| 7 | "Make an interactive scroll presentation as a web page." | showpiece | showpiece |
| 8 | "Design a poster for the cyber society night." | canvas-design | canvas-design |
| 9 | "These slide bullets read like filler, tighten the wording." | deslop | deslop |
| 10 | "Write the newsletter on gold this week." | autonomous-writer | autonomous-writer |

Result: 10 of 10 judged correct, with 3 borderline. Re-run against a live router before relying on them.
