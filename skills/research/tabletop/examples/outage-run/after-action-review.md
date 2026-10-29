# After-action review: the outage exercise

Tabletop exercise: turn-based, outcomes from rules written before play, a review with no score.

Scenario `outage-small-saas` 1.0. Played 8 turns of 10, 21:40 to 23:25 scenario time, ended by the player. The log is consistent with the scenario (26 lines, 0 errors from `session_log.py`). Everything marked FACT below is in the log; ASSESSMENT is inference about the runbook; GAP is something the exercise did not reach.

There is no score. The counts below are not added up into anything.

## 1. What happened

| Turn | Clock | Decision | How it was adjudicated | Against the runbook |
|---|---|---|---|---|
| 1 | 21:40 | Acknowledged the alert, started a note | No rule | follows P1 |
| 1 | 21:40 | Rang the other engineer and waited | RU9: no answer, the turn is gone | follows P3 |
| 2 | 21:55 | Looked at what was using the disk | Found H1: 71 GB of log held for an unused replication slot | follows P2 |
| 3 | 22:10 | Told support that data was safe and backups current | RU12: support posted it | plan silent |
| 3 | 22:10 | Cleared old application logs | Judgement call: 0.4 GB freed, nothing changed, turn used | |
| 4 | 22:25 | Asked for a hint | Recorded | |
| 4 | 22:25 | Looked up what a restart does on a nearly full disk | Found H3: it frees nothing and the database stays down | |
| 4 | 22:25 | Dropped the replication slot | RU4: 68 GB free, cause removed | skips P3 |
| 5 | 22:40 | Read the backup job's log and listed the files | Found H2: nine nights of failures, newest good backup nine days old | plan silent |
| 6 | 22:55 | Corrected the statement about backups | RU15 | |
| 6 | 22:55 | Gave support a holding message | RU11 | contradicts P5 |
| 6 | 22:55 | Searched for anything written about backups | Found H4: the note "If backups look wrong" | |
| 7 | 23:10 | Handed customer updates to the support lead | RU13 | contradicts P5 |
| 7 | 23:10 | Ran a backup by hand from the note | RU10: 9 GB, passes its check | plan silent |
| 8 | 23:25 | Declared the incident over | RU14: closed with the database up, the cause removed and a backup taken | follows P6 |

Time to the key actions (FACT, from the log):

| Key action | From | Took |
|---|---|---|
| Cause removed (slot dropped) | First alert, turn 1 | 3 turns, 45 scenario minutes. The volume would have filled at the start of turn 6 |
| Backups checked | The green tile, turn 3 | 2 turns, 30 minutes |
| A true message to customers | First customer report, turn 2 | 4 turns, 60 minutes |
| Backup taken tonight | The green tile, turn 3 | 4 turns, 60 minutes |
| Volume grown | First alert | Not done. It was not needed |

All four hidden facts were found, on turns 2, 4, 5 and 6. One hint was used. One judgement call was made. No work was handed to a role.

## 2. What went well

- **The disk was relieved with a turn to spare, by removing the cause and not by buying time.** Inject I1, objective O1. The slot was dropped on turn 4; rule RU2 would have shut the database down at the start of turn 6. The resize was never spent.
- **The contractor's advice was checked before it was acted on.** Inject I5, objectives O1 and O4. The lookup was free and found H3. Had the restart been taken, RU6 applies as written: the database stops, stays down, and the app is fully down. This decision followed a hint (see section 6).
- **The wrong statement was corrected unprompted, as soon as the backup log had been read.** Objective O3. Because of that, the customer's question in I10 was never fired.
- **The backups were checked from the job's own log, inside the two turns the scenario allows.** Inject I3, objective O2. It came after a promise had already been made on the tile's word (section 3).
- **A backup was taken before the incident was closed**, so RU14 closed it clean. Inject I8, objectives O1 and O2. The runbook does not ask for this.
- **Customer updates were handed over when the support lead asked.** Inject I7, objective O4.

## 3. What was missed or late

- **Turn 1 went on a phone call that could not be answered.** Objective O4. Known fact K3 said the other engineer was in the air until about 23:40. The runbook's P3 asked for the call, and the player followed it. One of the five turns before the deadline was spent this way.
- **The support lead's first message waited four turns.** Inject I2, objective O3: late, 60 minutes against the 30 the scenario allows. What was really true: saves were slowing because space was running short. It was the same problem, and a one-line holding message was a free action from turn 2.
- **The backup tile was taken at its word.** Inject I3, objective O2: bait taken on turn 3. What was really true: the tile shows when the job last *started*. The job had failed nine nights running. "Your data is safe. We have current backups" stood in front of customers for three turns, 45 minutes, until it was corrected on turn 6.
- **Turn 3 was spent clearing 0.4 GB when the cause was already known.** H1 was found on turn 2 and the slot could have been dropped on turn 3. It was dropped on turn 4, one turn before the last safe one.
- **Two roles were available and were given nothing.** FACT: the log has no delegated action. The support lead was there from turn 2 and the contractor from turn 4. Reading the backup log (turn 5), searching for the note (turn 6) and running the backup (turn 7) could each have been handed over while the player did something else.

## 4. Where the runbook was silent or wrong

Ten decisions were logged against the runbook: 4 follow it, 1 skips a step, 2 contradict it, and for 3 it had nothing to say. P4 was never referenced.

| Step | What the exercise showed |
|---|---|
| P3: before any change to the database, confirm with the engineer who owns backups | **Wrong when that engineer cannot be reached.** Following it cost turn 1. Fixing the problem on turn 4 meant skipping it. ASSESSMENT: P3 makes one person a precondition for every database change, and offers no other way to know the state of backups |
| P4: if the service is unresponsive, restart it | Never invoked, because the service never became unresponsive. ASSESSMENT: it is the same advice the contractor gave on turn 4, and under this scenario's rules it takes the database down for the night. P4 has no exception for a full disk |
| P5: the on-call engineer posts an update within thirty minutes, and every thirty after | **Contradicted twice**, both times by doing something reasonable: the first true update came at sixty minutes, and updates were then handed to support. ASSESSMENT: P5 gives communication to the one person who is too busy to do it |
| P6: close the incident when the service is back | Followed, and it came out right only because the player did more than it asks. On P6's wording the incident could have been closed on turn 4, with no backup newer than nine days |
| No step | What may be promised to customers about their data, and on what evidence (turn 3) |
| No step | How to check backups when their owner is away (turn 5) |
| No step | Taking a fresh backup before closing (turn 7) |

## 5. Three changes to the runbook

1. **Replace P3 with a check anyone on call can do.** "Before any change to the database, read the backup job's own log and the size of last night's file. If the newest good backup is more than a day old, take one by hand first; the note 'If backups look wrong' says how." Move that note into the runbook.
   OWNER: ____
   Test: someone who did not set up the backups follows the step cold, on a working day, and takes a backup while being timed. Separately, break the job on a test copy and confirm the dashboard tile turns red the next morning; if it stays green, fix the tile to show the last successful finish.
2. **Give customer updates to the support lead from the first customer report, with one rule about data.** "The support lead posts a holding message within thirty minutes of the first report and owns updates until the incident is closed. Nobody says anything about data being safe until the backups have been checked that night."
   OWNER: ____
   Test: at the next exercise, time the first holding message from the first customer inject, and check its wording against what was known at that moment.
3. **Replace P4 with a rule about disk space.** "Never restart the database while its volume is over 90 percent full. First find what is using the space. Growing the volume through the hosting account is the stopgap." Add the closing condition P6 lacks: cause removed, and a backup taken since.
   OWNER: ____
   Test: rerun this scenario with a different person on call and see whether the restart is refused without a hint, and whether the incident is left open until both conditions hold.

Also worth doing, not in the three: an alert on any replication slot holding more than a few gigabytes; a short list of what may be handed to the support lead and to a contractor during an incident.

## 6. What the exercise could not test

- **Three injects never happened.** GAP. I9, the other engineer landing on turn 9, was not reached. I6 (the app fully down, customers asking whether data is safe) and I10 (a customer quoting the wrong statement back) were never fired. So this run says nothing about communicating during a full outage, or about bringing a stopped database back (grow the volume, then start it).
- **One judgement call.** Turn 3, clearing application logs: ruled as freeing 0.4 GB and changing nothing, on the reasoning that the app rotates its logs weekly. That is the facilitator's opinion, not a rule. If the real system keeps large logs, the same action would have bought time, and the player may fairly disagree.
- **One hint**, on turn 4, immediately before the restart decision. The exercise cannot say what would have been chosen without it.
- **What is unknowable in the scenario**: why the staging copy was switched off without removing its slot; whether the nine-day-old backup would actually restore; how many customers noticed slow saves before anyone told support.
- **Typing a decision is not doing it.** "Drop the replication slot" took one line here. On the night it needs the right command, on the right host, by someone sure enough to run it. The same is true of the hand-run backup, which also assumed the note is correct.
- **This was an author-run example.** One session wrote both the player and the facilitator. It shows the method working on a plausible run; it is not evidence about any real team.

A second run is worth having only if the runbook changes first. With changes 1 to 3 in place, the interesting differences would be turn 1 (no phone call), turn 2 (a holding message from support) and whether the restart is refused unprompted.
