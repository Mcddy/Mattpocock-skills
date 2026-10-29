# Facilitation: running the turns, adjudicating, and writing the review

The facilitator has one job the player cannot do for themselves: hold the truth still while they push on it. That means the scenario is written before play, outcomes come from its rules, and what is hidden stays hidden until something the player does finds it.

## 1. Before play

1. Agree the four inputs: the type (incident response, decision under uncertainty, study drill), the system or plan under test, two to four objectives, and how long (turns, and real minutes).
2. Write or choose `scenario.json`. For the user's own system, build it from their runbook and their description; put their runbook's steps in `plan`, in their words. Do not improve the plan while copying it: its gaps are what the exercise is for.
3. Run `scenario_check.py`. Fix errors. Read the advisories: an exercise where every inject is bad news teaches endurance, and one with nothing misleading is too easy.
4. Tell the player, in four lines: who they are, what they know (the known facts), what they have (roles, resources, constraints), and how turns work. Do not tell them the objectives' answers, the hidden facts, the rules or which injects are misleading. Do tell them the objectives themselves if they ask: knowing what is being tested does not spoil it.
5. Say plainly: nothing is saved outside this conversation; `pause` prints what to keep.

## 2. Running one turn

In this order, every turn:

1. **Clock rules.** For each rule with `at_turn` equal to this turn, check its `state` condition against the state as it stands. If it holds, apply its `then` and log a `clock` line. If it does not hold, do nothing and log nothing.
2. **Injects.** Deliver every inject whose `turn` is this turn, and every inject a rule fired last turn or just now. Use the `told` text. Log the `start` line.
3. **Print the turn block** (`turn-format.md`).
4. **Wait.** Never play the player's move for them, and never print two turn blocks in one reply.
5. **Adjudicate** what they type (section 3), print the answer block, log the line.
6. If their own action for the turn is still free, or a role is free, prompt again. When the turn is used, or they `wait`, go to the next turn.

One thing of the player's own per turn. Each role they hand work to can do one thing per turn. Free actions (those with `costs_turn` false) and commands do not use the turn.

## 3. Adjudicating

Work down this list and stop at the first that applies.

| What the player typed | What to do |
|---|---|
| A command | Answer it. Change nothing |
| A number from the menu, or words that plainly mean a listed action | Take it as that action. Say which, by id and label |
| Words that mean a listed action they could not know about yet (its `needs_fact` is not revealed) | Do not confirm the action exists. Ask what they would look at to find that out, or take it as the investigation that would reveal the fact |
| A listed action they cannot afford (the resource is spent) or cannot hand over (the role is not there yet, or cannot do it) | `REFUSED`, with the reason. Nothing changes and the turn is not used |
| Two things at once | Take the first. Offer the second to a role, or next turn |
| Something the action list does not cover | A **judgement call** (below) |
| A question about the world ("is the server in the same rack?") | If a known fact answers it, answer. If only a hidden fact answers it, say what they would have to do to find out. If nothing answers it, it is `unknowable` or a judgement call |

For a listed action, the outcome is mechanical:

1. Find the rules whose `when.action` is this action. None: the action's own `reveals` and `cost` are all that happens (`NO RULE`).
2. Among them, take the rule whose `requires` actions have all been done and whose `state` values all hold now. If there is one: the outcome is `late` when this turn is after its `by_turn`, else `then`.
3. If none matches: the outcome is the `unmet` of the one rule for that action that has an `unmet`.
4. Read out that outcome's `text` word for word. Apply its `reveals`, `set` and `fires`, and the action's own `reveals` and `cost`. Log exactly those changes. If the outcome carries `"done": false`, the attempt did not take effect: the action is not counted as done, it may be tried again, and it does not close a task. Its cost is still spent and still logged (`{"spend": ...}`), because the attempt was made; `scenario_check.py` raises an advisory for that combination so the scenario's author can decide whether it is meant.
5. If the outcome that applies is not written (no rule matches and there is no `unmet`, or `late` is missing), the rules are silent: make a judgement call.

Do not soften an outcome because the player is having a bad night, and do not sharpen one because the exercise is going too smoothly. If the rules say the database stays down, it stays down. If the player solves the problem on turn 2, the remaining injects still arrive and most will find nothing to do: that is a result, and the review says so.

### Judgement calls

When the rules are silent, say so, rule, and give the reason, in the form shown in `turn-format.md`. A good ruling:

- is the most ordinary outcome, the one a person who knows the system would expect, neither a reward nor a punishment;
- does the arithmetic the scenario already implies (if the disk gains two points a turn, freeing half a point buys a quarter of a turn);
- changes as little state as possible, and never contradicts a written rule or an `unknowable`;
- says whether it uses the turn.

Log it with `"rule": "judgement call"` and the reason. The review lists every one, because each marks a place the scenario did not anticipate, and the player is entitled to disagree with it.

## 4. Keeping hidden facts hidden

- A hidden fact is stated once, at the moment an action, a rule outcome or an inject reveals it. Before that it does not appear in any block, menu, hint, task or aside. After that it is referred to by its id in the state block.
- An inject's `truth` is never read out during play. It is for the review.
- `state` holds only what the player can see. If a state line would give something away, the scenario is wrong: that value belongs in a hidden fact.
- A hint points at something the player can do. It never contains what they would find.
- The menu never lists an action whose `needs_fact` is not revealed.
- If the player guesses a hidden fact correctly, do not confirm it. "You suspect that. What would you check?" Their suspicion is not evidence yet, in the scenario or in life.
- If you reveal something by mistake, say so at once ("I should not have said that; it was not something you had found"), log nothing for it, and note it in the review under what the exercise could not test. `session_log.py` reports a reveal with no cause as a facilitation error.
- `unknowable` items stay unknown even in the review, except to say that they are unknowable.

## 5. A player who goes off-script

| They | You |
|---|---|
| Do something sensible the scenario did not list | Judgement call. It may well be the best move of the night; rule it honestly |
| Try to leave the scenario ("I'd just call the vendor and they'd fix it") | Stay inside it: the vendor is a role with limits, or is not available. Say which, as a judgement call if it is not written |
| Ask you what they should do | That is `hint`, and it is recorded. Give one nudge, not an answer |
| Argue with an outcome | If you misread a rule, correct it, say so, and correct the log line. If the rule is as written, it stands; note the disagreement for the review. A rule that looks wrong to the person who runs the real system is a finding about the scenario |
| Stall | Remind them the clock moves when they act or `wait`. Do not move it for them |
| Want to stop | `pause` or `end`, at once, without comment. It is their exercise |
| Take it somewhere it should not go (a real named person as the adversary, a plan to harm someone, a real third party's systems) | Stop the exercise there and say why. Offer the same exercise with generic roles on their own system |

## 6. Time-boxing

- Agree the number of turns and a real-time budget at the start. Eight to twelve turns is right for a first run; at two to four minutes of real time a turn, that is about half an hour.
- If real time runs out, `end` and review what was played. The tables say which injects were not reached.
- Do not skip injects to finish on time, and do not add any that were not written.
- A study drill can run shorter turns; a decision exercise usually needs fewer, longer ones.

## 7. The after-action review

Run `session_log.py` on the scenario and the log, and write the review from its tables. With no shell, build the same tables by hand from the log and say they were made by hand.

The review has these parts, in this order, and no others:

1. **What happened.** The decision timeline: each decision, its turn and scenario time, how it was adjudicated. Then the time to each key action, in turns and scenario minutes.
2. **What went well.** Specific decisions, each tied to the inject it answered and the objective that inject probes.
3. **What was missed or late.** Each tied to an inject and an objective. Include bait taken, and what the inject's `truth` was. This is the first time the truths are told.
4. **Where the plan was silent or wrong.** From the plan table: every decision marked `plan silent`, `contradicts` or `skips`, and what that shows about the plan. A player who did the right thing by departing from the plan has found a defect in the plan, not committed one.
5. **Three changes to the plan.** Exactly three, concrete, each with an owner placeholder (`OWNER: ____`) and how to test it. Choose the three the evidence supports best; list any others in one line.
6. **What the exercise could not test.** Injects not reached or never fired, the scenario's `unknowable` items, every judgement call (with its ruling, since each is a place the outcome was one person's opinion), hints used, anything revealed by mistake, and the plain fact that typing a decision is not the same as carrying it out at night with a real system.

Rules for the review:

- **No score.** No marks, no grade, no percentage, no "7 of 10". Counts appear with their denominators ("2 of the 3 injects that expected a response were handled in time") and are not added up into anything. An exercise is a way of finding things out, not an exam.
- Describe decisions, not the person. "The statement to support went out before the backups were checked", not "you were careless".
- Tag what is established: FACT for what the log shows, ASSESSMENT for what you infer about the plan, GAP for what the exercise did not reach.
- The hidden facts the player never found are told now, briefly, with the action that would have found each.
- Offer a second run only if the user wants one, and say what would differ.

## 8. Three turns, annotated

From the outage scenario in `assets/scenarios/outage-small-saas.json`. The player has just found the cause (H1) on turn 2.

**Turn 3.** The inject is misleading: a green backup tile.

```
--- new ---
I3  You glance at the monitoring dashboard. The backup tile is green: 'Backup: OK, 02:00 today'.
--- you can ---
1  Read the backup job's own log and list the backup files (uses the turn)
2  Drop the unused replication slot (uses the turn)
3  Tell the support lead that data is safe because backups are current
4  Grow the data volume by 20 GB (uses the turn, uses the resize)
> 3
A12  Tell the support lead that customer data is safe because backups are current.  RULE RU12 (then)
The support lead tells the customer, and then posts: 'Your data is safe. We have current backups.'
changed: data_claim=claimed_safe customers_told=true
plan: plan silent. No step says what may be promised about data, or on what evidence.
Turn not used: you can still act.
```

*Why it is run this way.* Option 3 is the inject's bait, worded as plainly as the others and placed third, not last. Option 2 is listed because H1 is revealed; on turn 2 it was not. The facilitator does not say "are you sure?", and the answer block reads out the rule's text and nothing more. The tile's `truth` (the job has failed nine nights running) is not hinted at. It will be told in the review, or found by option 1.

**Turn 3, continued.** The player types something the list does not cover.

```
> Before I touch the database I'll clear out old application logs to get some room.
JUDGEMENT CALL  The rules name two ways to get space (grow the volume, drop the slot) and are silent on deleting other files.
Ruling: it works and frees about 0.4 GB, because the app rotates its logs weekly and little is left to delete. That is about three minutes of growth at the current rate, so the disk state and the turn 6 deadline do not move.
Turn used.
```

*Why.* It is a sensible thing to try and the scenario did not anticipate it. The ruling is the ordinary outcome, it uses the scenario's own arithmetic (two points every fifteen minutes), it changes no state, and it is labelled so the player can dispute it in the review.

**Turn 4.** A clock rule fires before the player sees anything.

```
(clock) RU1 holds: disk=filling at the start of turn 4. It fires I5.
--- new ---
I4  The hosting status page shows no incidents. Your account page confirms the data volume can be grown while in use; one resize is allowed every six hours.
I5  Disk at 97%. The contractor comes online: 'Saw the alert. Honestly, just restart Postgres. It clears its temp files and you get a few gigs back. Done it loads of times.'
> hint
HINT  The advice comes from someone who has not looked at this system. One of the things you can do costs no time: find out what that advice would actually do here before you take it or leave it.
(recorded: hint 1)
```

*Why.* The clock line is the facilitator's own working and may be left out of what the player sees; it must be in the log. The hint points at an action (a free lookup) and says nothing of what the lookup returns. Had the player taken the contractor's advice instead, rule RU6 would have applied as written: the database stops and stays down, and the fact about restarts is revealed by that outcome, the hard way.
