# Dev skill routing: before and after

This is a judged simulation, not a live measurement. I read each prompt as a router that sees only the skill descriptions (the full frontmatter `description:`; the `REGISTRY.md` view truncates to about 160 characters, which hides the "Use when" and "Not for" clauses) and recorded the skill it would pick. Treat the scores as a sanity check on the wording, not as a hit rate. Scope: `research`, `diagnosing-bugs`, `perf-lab`, `program-verifier`, `tdd`, plus their near neighbours.

Changes tested: `research` now says it is the lightweight single-question lookup and points to deep-research-orchestrator and research-agency; `diagnosing-bugs`, `perf-lab` and `program-verifier` gained "Not for" pointers and natural trigger phrases; `tdd` gained a pointer to `diagnosing-bugs` because the baseline showed it taking an unknown-cause bug.

| # | Prompt | Expected | Before | After |
| --- | --- | --- | --- | --- |
| 1 | "Look into how Stripe retries webhooks and write it up in docs/" | research | research | research |
| 2 | "What do the Node 22 fetch docs say about keepalive? Drop notes in the repo" | research | research | research |
| 3 | "Research this properly: is logical replication safe for zero-downtime Postgres upgrades? I want a source ledger" | deep-research-orchestrator | research (miss) | deep-research-orchestrator |
| 4 | "Deep dive: what does the evidence say about remote work and productivity?" | deep-research-orchestrator | deep-research-orchestrator | deep-research-orchestrator |
| 5 | "Design and run a preregistered study to test whether this caching speedup is real" | research-agency | research-agency | research-agency |
| 6 | "Debug this: the login endpoint throws a 500" | diagnosing-bugs | diagnosing-bugs | diagnosing-bugs |
| 7 | "It's slow, the dashboard takes 8 seconds to load" | diagnosing-bugs | diagnosing-bugs | diagnosing-bugs |
| 8 | "Benchmark the old and new group-by with paired runs and tell me the speedup" | perf-lab | perf-lab | perf-lab |
| 9 | "Profile allocations and call counts in the parser and check how it scales with input size" | perf-lab | perf-lab | perf-lab |
| 10 | "Fix this bug test-first: the date parser returns the wrong month" | tdd | tdd | tdd |
| 11 | "Build the discount feature with red-green-refactor" | tdd | tdd | tdd |
| 12 | "This test fails intermittently and I have no idea why" | diagnosing-bugs | diagnosing-bugs | diagnosing-bugs |
| 13 | "Check my slugify against a reference implementation with property-based tests" | program-verifier | program-verifier | program-verifier |
| 14 | "Is this function correct?" (a small pure parser, no diff supplied) | program-verifier | code-review (miss) | program-verifier |
| 15 | "Fuzz our email validator, it accepts bad addresses, and shrink the failures" | program-verifier | program-verifier | program-verifier |
| 16 | "The export crashes on empty input. Find the cause and fix it with a regression test" | diagnosing-bugs | tdd (miss) | diagnosing-bugs |
| 17 | "Review my PR before I merge" | code-review (none of the five) | code-review | code-review |
| 18 | "Prototype two layouts for the settings page so I can see which feels right" | prototype (none of the five) | prototype | prototype |
| 19 | "Build me an invoice tracking app end to end" | forge (none of the five) | forge | forge |
| 20 | "Grill me on this migration plan" | grilling (none of the five) | grilling | grilling |

Score before: 17 of 20. Score after: 20 of 20.

Caveats: prompts 7, 10 and 16 sit on a real boundary ("slow" can be perf-lab once the user wants measurements; a bug with a known cause can go to tdd). The expected answers follow `overlaps.md` sections 3 and 8. Re-run with a live router before treating the after score as earned.
