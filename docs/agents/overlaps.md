# Skill overlaps

Recommendation only. No skill was edited. Built from `REGISTRY.md` descriptions; a `SKILL.md` was opened only where two descriptions genuinely compete. Overlaps already listed in `docs/agents/rewrite-decisions.md` (nexus, ai-power-user, meta-prompt-engineer; dispatch and heirloom-plan-capacity-week; vector and cipher; generative-content, media-compiler and showpiece; interactive-generator, pocket-app and forge; learning-visualiser, percept and atlas) are not repeated here: see rewrite-decisions.md.

Ordered by how likely a router is to pick wrongly, worst first.

## 1. handoff, rebrief, mnemosyne, claude-handoff

Shared situation: the conversation is long and the user wants to continue elsewhere.

| Skill | Trigger that should pick it |
| --- | --- |
| rebrief | "Start fresh", "give me something to paste into a new chat", the thread is long or going in circles. Auto-invoked. |
| handoff | User types `/handoff` to brief another agent in a coding workflow. User-only, so a router never picks it. Description has no "Use when". |
| mnemosyne | Files that persist across sessions: debrief, decision log, belief register. "Write a handoff for next time" also fits here. |
| claude-handoff (incubating) | Spawn a background agent that starts work immediately. Not installed by default. |

Risk: the phrase "hand this off" appears in rebrief and "write a handoff" in mnemosyne, while the skill actually named handoff cannot be auto-picked.
Recommendation: sharpen description. Add a "Use when ... Not for" clause to handoff naming rebrief (paste-into-new-chat) and mnemosyne (persisting files). Keep all four separate.

## 2. grill-me, grilling, grill-with-docs, elicitor, to-questionnaire

Shared situation: "ask me questions".

| Skill | Trigger that should pick it |
| --- | --- |
| grilling | Auto-invoked stress test of a plan or idea in chat. The real body; grill-me is a 7-line stub that calls it. |
| grill-me | `/grill-me`. User-only wrapper over grilling. |
| grill-with-docs | `/grill-with-docs`. Same interview, plus ADRs and a glossary written as it goes. |
| elicitor | The user wants a questionnaire, quiz or form built as a page ("quiz me on these notes", "interview me" when a page is wanted). |
| to-questionnaire | A decision the user cannot answer, turned into questions for someone else. |

Risk: "interview me" and "quiz me" are in elicitor's description but also read as grilling. grill-me and grilling duplicate each other by design.
Recommendation: sharpen description. Add a one-line "Not for" to grilling pointing at elicitor (page to fill in) and grill-with-docs (docs wanted). Keep grill-me as the thin user-invoked alias; do not merge.

## 3. research (engineering), deep-research-orchestrator, research-agency, sitrep, oracle, intelligence-analyst

Shared situation: "research X".

| Skill | Trigger that should pick it |
| --- | --- |
| research | Quick primary-source lookup written to a Markdown file in a repo, often delegated to a background agent. |
| deep-research-orchestrator | "Research this properly", "deep dive", "what does the evidence say": a campaign ending in a source ledger and brief. |
| research-agency | "Design and run a study", "test whether a finding is real": a gated, preregistered project. |
| sitrep | "Keep an eye on", "what's changed": recurring watch. |
| oracle | Forward-looking: forecasts, scenarios, due diligence, "help me decide". |
| intelligence-analyst | "What is really going on": competing explanations of contradictory evidence. |

Risk: `research` has the shortest, most generic description and wins by default on any "investigate" prompt; it does not say it is the lightweight repo-side option. The three campaign skills overlap on scale only.
Recommendation: sharpen description. Add to `research` "Not for multi-source campaigns (deep-research-orchestrator) or full studies (research-agency)". Keep separate.

## 4. orchestrator, taskforce, mandate, longhaul, chief-of-staff

Shared situation: a big task that needs more than one step or worker.

| Skill | Trigger that should pick it |
| --- | --- |
| orchestrator | "Handle this end to end" using whatever skills are present; sequences skills, not workers. |
| taskforce | A large divisible job split across several workers with path ownership, or resuming an interrupted run. |
| mandate | Owning an outcome against explicit authority and criteria; recovering a watered-down delivery. |
| longhaul | One agent, unattended or overnight coding run with a milestone plan. |
| chief-of-staff (incubating) | Long goal in one session coordinating subagents. |

Risk: "run the whole thing" and "end to end" appear in orchestrator, mandate and forge. taskforce and mandate descriptions point at each other but say little about the user's words.
Recommendation: sharpen description. Give taskforce and mandate concrete user phrases (for example "split this across agents" versus "own this outcome"). Keep separate. Candidate merge of chief-of-staff into taskforce when chief-of-staff leaves incubating.

## 5. skill-creator, skill-audit, rosetta

Shared situation: working on skills.

| Skill | Trigger that should pick it |
| --- | --- |
| skill-creator | Write, edit, test or tune one skill's description. |
| skill-audit | The whole library: overlaps, dedupe, "many skills never fire", candidates from recent sessions. |
| rosetta | Move a skill between Claude, ChatGPT and Codex. |

Descriptions already cross-reference (skill-audit names skill-creator). Only skill-creator lacks a "Not for" line, and its "optimize a skill's description" overlaps skill-audit's trigger tests.
Recommendation: keep separate. Optionally add "Not for the whole library (skill-audit) or porting (rosetta)" to skill-creator.

## 6. code-review, referee-panel, fact-check, paper-audit, program-verifier

Shared situation: "review this".

code-review reviews code diffs; referee-panel reviews finished research; fact-check checks a draft's claims against sources; paper-audit reads one study; program-verifier tests code correctness with an oracle. The words "review" and "check" are the only shared ground, and each description names its domain.
Recommendation: keep separate. Low risk; code-review could add "Not for research or papers (referee-panel)".

## 7. implement, implement-spec, to-spec, to-tickets, wayfinder

Shared situation: turning a plan into shipped work.

implement and implement-spec are both user-only and differ only in scope (a ticket or spec versus an entire spec on one integration branch). to-spec and to-tickets produce the inputs; wayfinder is for work bigger than one session. User-only skills are not auto-routed, so mis-picking comes from the user typing the wrong name; ask-shaun covers the flow.
Recommendation: keep separate. Candidate merge of implement into implement-spec only if Shaun finds he uses one ticket path and one spec path interchangeably.

## 8. diagnosing-bugs, perf-lab, tdd, program-verifier

Shared situation: code is broken or slow.

diagnosing-bugs is the entry for "debug this" and "slow"; perf-lab is for measured benchmark experiments; tdd is test-first building and bug fixes; program-verifier is oracle-based correctness testing. "Fix a bug test-first" fits tdd and diagnosing-bugs; "slow" fits diagnosing-bugs and perf-lab.
Recommendation: sharpen description. Add "measured benchmarks (perf-lab)" to diagnosing-bugs and a "Use when" trigger phrase to perf-lab. Keep separate.

## 9. fact-check, paper-audit, evidence-synthesis, intelligence-analyst

Shared situation: judging evidence quality.

Descriptions already carry reciprocal "Not for" clauses (draft versus one study versus many studies versus competing explanations). No change needed.
Recommendation: keep separate.
