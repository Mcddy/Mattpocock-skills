---
name: dispatch
description: "Runs Shaun's operating rhythm: Cerberus three-lens market briefs, getting a stalled project moving, daily and weekly planning, second-brain structure, quick company or market intelligence, and deciding what to automate. Use when he says 'Cerberus brief', 'three lenses on', 'analyse this trade', 'help me execute', 'I keep planning but not doing', 'what should I focus on', 'organise my system', 'my system isn't working', 'write this up' or 'automate this'. Not for end-of-session notes or decision logs (use mnemosyne), packing a week to a fixed number of hours (heirloom-plan-capacity-week), due diligence or forecasts (oracle), building a scheduled pipeline (nexus-prime), creating a schedule (schedule) or long-form writing (autonomous-writer)."
---

# dispatch

Turns Shaun's plans and analysis into output: a scored Cerberus brief, a restart plan for a stalled project, a day or week structure, or a decision on what to automate. Templates and detailed frameworks are in `references/`.

## Use when

- A market or trade needs a Cerberus three-lens assessment or a publishable brief.
- A project is stuck, scope is growing, or he is planning instead of doing.
- The day or week needs structuring, or his system for notes and tasks is not working.
- A quick read on a company, person (public professional record only) or market is needed.
- Something he does by hand keeps recurring and might be automated.

## Not this skill

| The request | Goes to |
|---|---|
| Capture this session, log a decision, write next-session context | mnemosyne |
| Compress this chat into a brief for a fresh chat | rebrief |
| Fit tasks into a fixed number of usable hours this week | heirloom-plan-capacity-week |
| Forecasts, scenarios, due diligence, stress test a plan | oracle |
| Weigh competing explanations of what is going on | intelligence-analyst |
| Research a topic with a source ledger | deep-research-orchestrator |
| Build or deploy an always-on pipeline or alert | nexus-prime |
| Create a scheduled task | schedule |
| Long-form articles, newsletters, sales copy | autonomous-writer |
| Remove AI tells from a draft | deslop |
| Score the whole plan for gaps | gladiator |
| Negotiation, power dynamics, campaign planning | vector |
| Which AI tool to use for a job | nexus |
| Work the agent hub task queue | agent-hub |

## Inputs

- What he wants (one sentence) and the deadline, if any.
- For a market brief: the asset, the session or timeframe, and any position he holds.
- For a stuck project: the outcome, the last action taken and what is blocking.

## Procedure

Pick the mode from the request. If two apply, do the one that unblocks the other first.

### A. Cerberus brief

1. **Get current data.** Prices, levels, calendars and positioning must come from a lookup in this session or from Shaun. With neither, label every number an assumption and say so at the top. Never quote levels from memory.
2. **Score each lens from -5 (strongly bearish) to +5 (strongly bullish)**: macro (central bank posture, data cycle, geopolitics, currency, liquidity), technical (trend structure, key zones, moving averages, momentum, volume, multi-timeframe), sentiment (positioning data, retail versus institutional, options skew, fear and greed, crowding).
3. **Composite = sum of the three scores** (range -15 to +15). Default lens emphasis by asset (gold and silver lean macro, AUD/USD and indices lean technical, crypto leans technical and sentiment) decides which lens leads when they disagree; see `references/cerberus.md`.
4. **Apply the rules.**
   - Composite from -4 to +4: verdict WAIT. Never force a direction.
   - A trade recommendation needs composite of at least +5 or at most -5.
   - Stop level defined and logical; reward to risk at least 1.5 to 1.
   - No major news catalyst in the next 4 hours unless the catalyst is the trade.
   - Mark thin data as [UNCERTAIN: reason] and anything unverified as [ASSUMPTION: x].
   - Conviction 0 to 100 on every verdict.
5. **Format** as a rapid brief or the full publication structure from `references/cerberus.md`. Lead with the verdict.
6. **Label it** as general information for the reader's consideration, not personal advice (see Rules).

### B. Stalled project or planning without doing

1. Name the failure mode: analysis paralysis, scope inflation, waiting for perfect, building the framework instead of the thing, or lost momentum.
2. **Three-level breakdown.** Outcome (specific and measurable, for example "200 paid subscribers at $X a month by a date", not "launch Cerberus"). Milestones (three to five, observable, days to weeks). First actions (the next three, each under two hours).
3. **Never end a planning session without level 3 written down.**
4. For a stall, diagnose: unclear next action (define it now), waiting on someone (chase or remove the dependency), task too large (split to under two hours), lost motivation (reconnect to the outcome), scope inflated (cut to minimum), perfectionism (define "good enough" for this stage).
5. **Minimum viable version.** What is the smallest thing that tests the core assumption and delivers real value? Examples: one quality Cerberus issue then one paying subscriber; one working prompt then one sale; one automated workflow that saves a measured number of hours.
6. **Shipping check.** Does it solve the stated problem? Good enough for this audience at this stage? What is the worst case if shipped imperfect? Is the delay about the work or about fear? Imperfect and shipped beats perfect and delayed.
7. His known patterns: over-engineering the framework before the thing, and ideas arriving faster than he executes. Default question: "What is the minimum version that could ship this week?"

### C. Day and week

- **Daily**: one anchor task (protected time, not leftover time), two or three supporting tasks, allocated reactive time for markets, messages and admin, and a shutdown trigger (when today is done, not "when everything is finished"). Decide tomorrow's anchor today.
- **Weekly (30 minutes)**: projects on track and decision points hit; lines of effort advancing or stalling; anchor task for each day next week; what in the system is breaking and needs maintenance.
- **Capacity**: protect sleep, food and exercise as operational inputs. Deep-work hours are the scarce resource; schedule them first and guard them. Recovery time is not optional.
- **Metrics by domain**: trading (trades executed versus planned, pre-trade checklist rate, debrief rate); Cerberus (issues published versus planned, research-to-draft conversion); prompts and AI (shipped versus in development, revenue per shipped prompt); automation (workflows live versus designed, hours saved a week).
- For a tight hour budget, hand to heirloom-plan-capacity-week.

### D. System design

Principles: one trusted system with no duplicates across tools; capture must take under ten seconds; the system must work when he is tired; automate the trivial and keep judgement for what matters; producing outputs forces synthesis. Fewer tools is better, since every tool is something to maintain. Layers (capture, process, organise with PARA, review, express) and the domain folder structures for trading, AI work and Cerberus are in `references/second-brain.md`.

### E. Intelligence on a company, person or market

Use the tiered packages in `references/intel-and-radar.md`. Public, professional, verifiable information only. Red-team before finalising: what am I most likely wrong about, what evidence am I ignoring, what would change this, am I seeing what I want to see? For formal due diligence hand to oracle.

### F. Frontier radar

Filter for signal (changes how he would work, build or trade today) versus noise (incremental benchmarks, announcements, hype). Assess any development with the template in `references/intel-and-radar.md`. Do not state what is "current" about AI products or markets without checking.

### G. Writing

Lead with the conclusion. One idea per sentence. Cut the first paragraph of a first draft. Active voice. Specific over general ("$47 a month", not "affordable"). Cerberus tone: direct, institutional, no filler. For long pieces, hand to autonomous-writer.

### H. Automation

If he does something manually more than twice, evaluate it for automation. Describe it as **Trigger, Retrieve, Act, Post**: what starts it, what context it needs, the single-purpose job, and where the output goes. Examples and the stack he uses are in `references/automation.md`. Building and deploying it is nexus-prime; a plain schedule is schedule.

## Daily and weekly standard

Morning: check for overnight signals that change the picture; run the three lenses on active positions; set the anchor task. During: work the anchor task undisturbed. Evening: review positions against price action; capture what should compound; choose tomorrow's anchor. Weekly: campaign review, a frontier sweep of AI and markets, a system audit.

## Output

The artefact for the mode: a scored brief, a three-level plan with the first action named, a day or week structure, a system layout, an intel package, or a TRAP workflow sketch. End with the single next action and when it happens.

## Rules that always hold

- Market output is analysis, not a personal recommendation. State assumptions, give no sizing for the reader, and keep the pre-trade checklist visible. Publishing Cerberus content to the public may carry licensing obligations in Australia; that is Shaun's call to confirm, not something to assume away.
- Numbers need a source seen in this session or are labelled assumptions.
- No planning session ends without a first action under two hours.
- Intelligence on people stays to public professional record.
- Do not build the system in place of doing the work. Prefer the smallest change that unblocks output.

## References

- `references/cerberus.md`: weights, brief schema, pre-trade checklist, rapid brief, publication format, issue formats.
- `references/second-brain.md`: capture-to-express layers, PARA, domain folder layouts, tool stack.
- `references/intel-and-radar.md`: company, person and market packages, red team, frontier watchlist and assessment.
- `references/automation.md`: Trigger-Retrieve-Act-Post workflows for Shaun's domains and the automation stack.
