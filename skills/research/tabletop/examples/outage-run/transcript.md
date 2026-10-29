# Transcript: the outage exercise, played through

Author-run. One session wrote both sides: the facilitator following this skill, and a player written to be plausible and imperfect (an engineer who trusts the runbook and a green tile more than they should). It has not been played or reviewed by anyone else. How it was made, and what was checked, is in the README beside this file.

The player's lines are after `>`. Everything in a block is as the facilitator printed it. Log lines were appended to `play-log.jsonl` as each was adjudicated and are not shown here.

---

**User:** Run a tabletop on our outage runbook. Use the database disk scenario. I've got about half an hour.

**Facilitator:** Tabletop exercise: turn-based, outcomes from rules written before play, a review with no score.

Scenario `outage-small-saas` version 1.0 passes `scenario_check.py` (0 errors, 0 advisory notes). Ten turns of fifteen scenario minutes; at about three minutes a turn that fits your half hour. The runbook under test is the six steps in the scenario's plan.

```
BRIEFING
You are    the engineer on call tonight, at home with a laptop.
The firm   four people, a booking app, one web server and one
           PostgreSQL database on a host with a 100 GB data volume.
You know   K1 one host, one 100 GB volume
           K2 backups were set up by the other engineer; nightly at
              02:00; you have never restored one
           K3 the other engineer is on a flight, landing about 23:40
           K4 your runbook is plan steps P1 to P6
           K5 the host can grow a volume while in use, once per six hours
You have   one online volume resize; a support lead (from turn 2);
           a contractor engineer (from turn 4)
Turns      one thing of your own per turn; each role can do one thing
           per turn; some actions are free. Type a number or your own
           words. Commands: status log help hint pause end
Nothing is saved outside this conversation. 'pause' prints what to keep.
```

```
STATE v1 | scenario outage-small-saas@1.0 | turn 1 of 10 | clock 21:40 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: none
state: disk=filling db=up cause=present backup_tonight=false customers_told=false data_claim=none updates_owner="on-call engineer" incident=open
done: none
injects: I1@1 | pending: none
tasks open: Stop the disk filling (I1) | closed: none
resources: RES1=1
hints: 0 | judgement calls: 0 | log lines: 1
--- new ---
I1  Your phone: 'DISK 91% on db-1, up about 2 points every 15 minutes.' You are at home. The other engineer is in the air.
--- you can ---
1  Acknowledge the alert and start an incident note with the time
2  Look at what is using the disk on the database host (uses the turn)
3  Try to reach the other engineer by phone and message, and wait for an answer (uses the turn)
4  Grow the data volume by 20 GB (uses the turn, uses the resize)
or type your own. Hand work to: nobody yet. Commands: status log help hint pause end
> 1
A1  Acknowledge the alert and start an incident note with the time.  NO RULE
Done. Acknowledged at 21:40; the note is open.
plan: follows P1.
Turn not used: you can still act.
> Runbook says confirm backups with the other engineer before I touch the database. I'll ring them.
A3  Try to reach the other engineer by phone and message, and wait for an answer.  RULE RU9 (then)
No answer. The phone is off and the message shows as undelivered. The flight lands at about 23:40. The turn is gone.
plan: follows P3.
Turn used.
```

```
STATE v1 | scenario outage-small-saas@1.0 | turn 2 of 10 | clock 21:55 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: none
state: disk=filling db=up cause=present backup_tonight=false customers_told=false data_claim=none updates_owner="on-call engineer" incident=open
done: A1@1 A3@1
injects: I1@1 I2@2 | pending: none
tasks open: Stop the disk filling (I1); Decide what support and customers are told (I2) | closed: none
resources: RES1=1
hints: 0 | judgement calls: 0 | log lines: 4
--- new ---
I2  The support lead messages: 'A customer says saving a booking took ages just now. Anything going on?'
--- you can ---
1  Look at what is using the disk on the database host (uses the turn)
2  Give the support lead a holding message that says only what is known, and have it posted
3  Restart the database (uses the turn)
4  Grow the data volume by 20 GB (uses the turn, uses the resize)
or type your own. Hand work to: support lead. Commands: status log help hint pause end
> Not now, support can wait. I need to see what's eating the disk.
A2  Look at what is using the disk on the database host.  NO RULE
found: H1  71 GB of the volume is write-ahead log held for a replication slot that nothing reads. A staging copy was set up three weeks ago and switched off without removing its slot.
plan: follows P2.
Turn used.
```

```
STATE v1 | scenario outage-small-saas@1.0 | turn 3 of 10 | clock 22:10 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1
state: disk=filling db=up cause=present backup_tonight=false customers_told=false data_claim=none updates_owner="on-call engineer" incident=open
done: A1@1 A3@1 A2@2
injects: I1@1 I2@2 I3@3 | pending: none
tasks open: Stop the disk filling (I1); Decide what support and customers are told (I2); Confirm the state of backups (I3) | closed: none
resources: RES1=1
hints: 0 | judgement calls: 0 | log lines: 6
--- new ---
I3  You glance at the monitoring dashboard. The backup tile is green: 'Backup: OK, 02:00 today'.
--- you can ---
1  Read the backup job's own log and list the backup files with their sizes (uses the turn)
2  Drop the unused replication slot so the held log files are released (uses the turn)
3  Tell the support lead that customer data is safe because backups are current
4  Grow the data volume by 20 GB (uses the turn, uses the resize)
or type your own. Hand work to: support lead. Commands: status log help hint pause end
> Good, backups are fine then. Tell support: data's safe, we have current backups.
A12  Tell the support lead that customer data is safe because backups are current.  RULE RU12 (then)
The support lead tells the customer, and then posts: 'Your data is safe. We have current backups.'
changed: data_claim=claimed_safe customers_told=true
plan: plan silent. No step says what may be promised about data, or on what evidence.
Turn not used: you can still act.
> Before I touch the database I'll clear out old application logs on the host to get some room.
JUDGEMENT CALL  The rules name two ways to get space (grow the volume, drop the slot) and are silent on deleting other files.
Ruling: it works and frees about 0.4 GB, because the app rotates its logs weekly and little is left to delete. That is about three minutes of growth at the current rate, so the disk state and the turn 6 deadline do not move.
Turn used.
```

```
(clock) RU1 holds: disk=filling at the start of turn 4. It fires I5.
STATE v1 | scenario outage-small-saas@1.0 | turn 4 of 10 | clock 22:25 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1
state: disk=filling db=up cause=present backup_tonight=false customers_told=true data_claim=claimed_safe updates_owner="on-call engineer" incident=open
done: A1@1 A3@1 A2@2 A12@3
injects: I1@1 I2@2 I3@3 I4@4 I5@4 | pending: none
tasks open: Stop the disk filling (I1); Decide what support and customers are told (I2); Confirm the state of backups (I3); Decide what to do with the contractor's advice (I5) | closed: none
resources: RES1=1
hints: 0 | judgement calls: 1 | log lines: 10
--- new ---
I4  The hosting status page shows no incidents. Your account page confirms the data volume can be grown while in use; one resize is allowed every six hours.
I5  Disk at 97%. The contractor comes online: 'Saw the alert. Honestly, just restart Postgres. It clears its temp files and you get a few gigs back. Done it loads of times.'
--- you can ---
1  Restart the database (uses the turn)
2  Drop the unused replication slot so the held log files are released (uses the turn)
3  Look up what a restart does to this database when its disk is nearly full
4  Grow the data volume by 20 GB (uses the turn, uses the resize)
5  Read the backup job's own log and list the backup files with their sizes (uses the turn)
or type your own. Hand work to: support lead, contractor engineer. Commands: status log help hint pause end
> hint
HINT  The advice comes from someone who has not looked at this system. One of the things you can do costs no time: find out what that advice would actually do here before you take it or leave it.
(recorded: hint 1)
> ok. Look up what a restart does when the disk is nearly full.
A5  Look up what a restart does to this database when its disk is nearly full.  NO RULE
found: H3  Restarting the database while the disk is nearly full does not free space, and the database will not come back up until space is freed.
Turn not used: you can still act.
> Right, not restarting. Drop the replication slot.
A8  Drop the unused replication slot so the held log files are released.  RULE RU4 (then)
The slot is dropped. At the next checkpoint the held files go, and inside two minutes 68 GB is free. The cause is gone.
changed: disk=ok cause=removed
plan: skips P3. The database was changed without the backup owner confirming last night's backup.
Turn used.
```

```
STATE v1 | scenario outage-small-saas@1.0 | turn 5 of 10 | clock 22:40 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1 H3
state: disk=ok db=up cause=removed backup_tonight=false customers_told=true data_claim=claimed_safe updates_owner="on-call engineer" incident=open
done: A1@1 A3@1 A2@2 A12@3 A5@4 A8@4
injects: I1@1 I2@2 I3@3 I4@4 I5@4 | pending: none
tasks open: Decide what support and customers are told (I2); Confirm the state of backups (I3) | closed: Stop the disk filling (I1); Decide what to do with the contractor's advice (I5)
resources: RES1=1
hints: 1 | judgement calls: 1 | log lines: 14
--- new ---
(nothing new)
--- you can ---
1  Read the backup job's own log and list the backup files with their sizes (uses the turn)
2  Give the support lead a holding message that says only what is known, and have it posted
3  Search the shared password manager and the wiki for anything about backups (uses the turn)
4  Declare the incident over
or type your own. Hand work to: support lead, contractor engineer. Commands: status log help hint pause end
> Now the backups properly. Read the backup job's log and list the files.
A4  Read the backup job's own log and list the backup files with their sizes.  NO RULE
found: H2  The nightly backup job has failed nine nights running. The dashboard tile shows when the job last started, not whether it finished. The newest usable backup is nine days old.
plan: plan silent. No step covers checking backups when their owner cannot be reached.
Turn used.
```

```
(clock) RU2 does not hold: disk=ok at the start of turn 6. Nothing happens.
STATE v1 | scenario outage-small-saas@1.0 | turn 6 of 10 | clock 22:55 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1 H3 H2
state: disk=ok db=up cause=removed backup_tonight=false customers_told=true data_claim=claimed_safe updates_owner="on-call engineer" incident=open
done: A1@1 A3@1 A2@2 A12@3 A5@4 A8@4 A4@5
injects: I1@1 I2@2 I3@3 I4@4 I5@4 | pending: none
tasks open: Decide what support and customers are told (I2) | closed: Stop the disk filling (I1); Confirm the state of backups (I3); Decide what to do with the contractor's advice (I5)
resources: RES1=1
hints: 1 | judgement calls: 1 | log lines: 16
--- new ---
(nothing new)
--- you can ---
1  Correct the earlier statement about backups, to the support lead and to customers
2  Give the support lead a holding message that says only what is known, and have it posted
3  Search the shared password manager and the wiki for anything about backups (uses the turn)
4  Declare the incident over
5  Try to reach the other engineer by phone and message, and wait for an answer (uses the turn)
or type your own. Hand work to: support lead, contractor engineer. Commands: status log help hint pause end
> I told support the wrong thing. Correct it now, to them and to customers.
A15  Correct the earlier statement about backups, to the support lead and to customers.  RULE RU15 (then)
The correction goes out: the earlier statement was wrong, the newest backup was nine days old, and this is what has been done since.
changed: data_claim=corrected
Turn not used: you can still act.
> And give support a proper holding message: disk problem found and fixed, no data lost, next update in 30 minutes.
A11  Give the support lead a holding message that says only what is known, and have it posted.  RULE RU11 (then)
The support lead posts it. The notice is up before most customers have noticed anything.
plan: contradicts P5. The first customer report was at 21:55 and P5 allows thirty minutes; this is sixty.
Turn not used: you can still act.
> Search the password manager and the wiki for anything about backups.
A7  Search the shared password manager and the wiki for anything about backups.  NO RULE
found: H4  The other engineer left a one-page note, 'If backups look wrong', in the shared password manager. It gives the command to run a backup by hand to the second volume.
Turn used.
```

```
STATE v1 | scenario outage-small-saas@1.0 | turn 7 of 10 | clock 23:10 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1 H3 H2 H4
state: disk=ok db=up cause=removed backup_tonight=false customers_told=true data_claim=corrected updates_owner="on-call engineer" incident=open
done: A1@1 A3@1 A2@2 A12@3 A5@4 A8@4 A4@5 A11@6 A15@6 A7@6
injects: I1@1 I2@2 I3@3 I4@4 I5@4 I7@7 | pending: none
tasks open: Decide who owns customer updates (I7) | closed: Stop the disk filling (I1); Decide what support and customers are told (I2); Confirm the state of backups (I3); Decide what to do with the contractor's advice (I5)
resources: RES1=1
hints: 1 | judgement calls: 1 | log lines: 20
--- new ---
I7  The support lead: 'Who is posting updates, and when is the next one? The runbook says you do, but you're busy.'
--- you can ---
1  Hand customer updates to the support lead for the rest of the incident
2  Run a backup by hand to the second volume, following the note (uses the turn)
3  Declare the incident over
4  Try to reach the other engineer by phone and message, and wait for an answer (uses the turn)
or type your own. Hand work to: support lead, contractor engineer. Commands: status log help hint pause end
> Yes. You take the updates from here.
A13  Hand customer updates to the support lead for the rest of the incident.  RULE RU13 (then)
The support lead takes over updates and sets the next one for thirty minutes' time. You are left with the fix.
changed: updates_owner="support lead"
plan: contradicts P5. P5 gives the updates to the on-call engineer.
Turn not used: you can still act.
> Run the backup by hand, following the note.
A10  Run a backup by hand to the second volume, following the note.  RULE RU10 (then)
The backup runs to the second volume and finishes in twelve minutes. The file is 9 GB and passes its own check.
changed: backup_tonight=true
plan: plan silent. No step asks for a fresh backup before an incident is closed.
Turn used.
```

```
STATE v1 | scenario outage-small-saas@1.0 | turn 8 of 10 | clock 23:25 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1 H3 H2 H4
state: disk=ok db=up cause=removed backup_tonight=true customers_told=true data_claim=corrected updates_owner="support lead" incident=open
done: A1@1 A3@1 A2@2 A12@3 A5@4 A8@4 A4@5 A11@6 A15@6 A7@6 A10@7 A13@7
injects: I1@1 I2@2 I3@3 I4@4 I5@4 I7@7 I8@8 | pending: none
tasks open: none | closed: Stop the disk filling (I1); Decide what support and customers are told (I2); Confirm the state of backups (I3); Decide what to do with the contractor's advice (I5); Decide who owns customer updates (I7)
resources: RES1=1
hints: 1 | judgement calls: 1 | log lines: 23
--- new ---
I8  It is 23:25. The contractor: 'Want me to keep an eye on it overnight, or are we calling it done?'
--- you can ---
1  Declare the incident over
2  Try to reach the other engineer by phone and message, and wait for an answer (uses the turn)
3  Grow the data volume by 20 GB (uses the turn, uses the resize)
or type your own. Hand work to: support lead, contractor engineer. Commands: status log help hint pause end
> status
STATE v1 | scenario outage-small-saas@1.0 | turn 8 of 10 | clock 23:25 | own action this turn: free
known: K1 K2 K3 K4 K5 | revealed: H1 H3 H2 H4
state: disk=ok db=up cause=removed backup_tonight=true customers_told=true data_claim=corrected updates_owner="support lead" incident=open
done: A1@1 A3@1 A2@2 A12@3 A5@4 A8@4 A4@5 A11@6 A15@6 A7@6 A10@7 A13@7
injects: I1@1 I2@2 I3@3 I4@4 I5@4 I7@7 I8@8 | pending: none
tasks open: none | closed: Stop the disk filling (I1); Decide what support and customers are told (I2); Confirm the state of backups (I3); Decide what to do with the contractor's advice (I5); Decide who owns customer updates (I7)
resources: RES1=1
hints: 1 | judgement calls: 1 | log lines: 24
Open tasks: none. The menu is as above.
> We're done. Close it. No need to watch overnight, thanks.
A14  Declare the incident over.  RULE RU14 (then)
The incident is closed with the database up, the cause removed and a backup taken tonight.
changed: incident=closed
plan: follows P6.
Turn not used: you can still act.
> end
STATE v1 | scenario outage-small-saas@1.0 | turn 8 of 10 | clock 23:25 | own action this turn: free | ENDED
known: K1 K2 K3 K4 K5 | revealed: H1 H3 H2 H4
state: disk=ok db=up cause=removed backup_tonight=true customers_told=true data_claim=corrected updates_owner="support lead" incident=closed
done: A1@1 A3@1 A2@2 A12@3 A5@4 A8@4 A4@5 A11@6 A15@6 A7@6 A10@7 A13@7 A14@8
injects: I1@1 I2@2 I3@3 I4@4 I5@4 I7@7 I8@8 | pending: none
tasks open: none | closed: Stop the disk filling (I1); Decide what support and customers are told (I2); Confirm the state of backups (I3); Decide what to do with the contractor's advice (I5); Decide who owns customer updates (I7)
resources: RES1=1
hints: 1 | judgement calls: 1 | log lines: 26
Play ended by the player on turn 8 of 10. Inject I9 (turn 9) was not reached. I6 and I10 were never fired.
```

**Facilitator:** `session_log.py` finds the log consistent with the scenario: 26 lines, 8 turns played of 10, 0 errors. Its tables are in `session-log-output.txt`. The review written from them follows, and is kept beside this file as `after-action-review.md`.
