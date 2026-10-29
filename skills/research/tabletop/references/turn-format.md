# Turn format: the turn block, the state block, the commands and the log line

Everything the facilitator prints during play is one of four things: a turn block, an answer block, a command reply, or a log line. All of them go in a fenced text block so they read like a terminal, on a phone as well as a desktop. Keep prose outside the blocks to a sentence or none.

## 1. The turn block

Printed once at the start of every turn, after the turn's clock rules and injects have been applied and logged.

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
1  Read the backup job's own log and list the backup files (uses the turn)
2  Drop the unused replication slot (uses the turn)
3  Tell the support lead that data is safe because backups are current
4  Grow the data volume by 20 GB (uses the turn, uses the resize)
or type your own. Hand work to: support lead. Commands: status log help hint pause end
>
```

The parts, in this order, every turn:

| Part | Rule |
|---|---|
| The eight state lines | The **state block**. Exactly what `scripts/session_log.py --state` prints for the log so far. If the two differ, the log is right and the block is wrong: fix the block and say so |
| `--- new ---` | Each inject delivered this turn, by id, in the scenario's own words (its `told` text, never its `truth`). If nothing arrived: `(nothing new)` |
| `--- you can ---` | Three to five numbered actions from the scenario's list, then the line about free input. Mark actions that use the turn or a resource. List the roles that are available this turn |
| `>` | The prompt. Stop here and wait |

Rules for the menu:

- Offer only actions the player could know about. An action with `needs_fact` is not listed, and is not accepted, until those facts are revealed. Listing it would give the hidden fact away, and `session_log.py` reports that as a facilitation error.
- Always include at least one action that is tempting and poor (an inject's `bait`), in the same plain wording as the others. Do not signal which is which, by order or by tone.
- Do not list every action. The player may type any of the others in their own words.
- An action already done is listed again only if doing it twice makes sense.

## 2. The state block

The eight lines at the top of the turn block. It is all the state there is. Nothing persists outside the conversation, so:

- to **pause**, print the state block and the log lines so far, and say "paste these and the scenario file to carry on";
- to **resume**, the user pastes the scenario file, the log lines and the last state block. Recompute the block from the log (`session_log.py --state`, or by hand) and confirm it matches before the next turn. If only the state block was kept, play can continue from it, but the after-action tables can cover only what the log holds: say so.

| Line | Holds |
|---|---|
| `STATE v1 \| scenario ID@VERSION \| turn N of M \| clock HH:MM \| own action this turn: free or used` | Where play is. `\| ENDED` is added after `end` |
| `known: ... \| revealed: ...` | Known fact ids, then hidden fact ids in the order they were found. Ids only: the text of a hidden fact is given once, when it is found |
| `state: key=value ...` | The scenario's `state`, which holds only what the player can see |
| `done: A1@1 ...` | Each action taken, with the turn it was first taken |
| `injects: I1@1 ... \| pending: ...` | Injects delivered, with their turns; then injects a rule has fired that have not arrived yet |
| `tasks open: ... \| closed: ...` | One task per delivered inject that has a `task` line. Closed when one of the inject's expected actions has been done |
| `resources: RES1=1` | What is left |
| `hints: n \| judgement calls: n \| log lines: n` | Counts so far |

## 3. The answer block

Printed after each thing the player types.

```
> 2
A8  Drop the unused replication slot.  RULE RU4 (then)
The slot is dropped. At the next checkpoint the held files go, and inside two minutes 68 GB is free. The cause is gone.
changed: disk=ok cause=removed
plan: skips P3. The database was changed without the backup owner confirming last night's backup.
Turn used.
>
```

| Line | Rule |
|---|---|
| Echo | `>` and what the player typed |
| What it was taken as | The action id and label, then how it was adjudicated: `RULE RUn (then, late or unmet)`, `NO RULE` (the action's own effects are all that happens), `JUDGEMENT CALL`, or `REFUSED` |
| The outcome | The rule's own text, word for word. For an action with no rule, the text of any hidden fact it reveals |
| `found:` | Only when a hidden fact is revealed: its id and its text, once |
| `changed:` | State values and resources that changed. Leave the line out if nothing did |
| `plan:` | Only when the scenario has plan steps and the decision bears on one: `follows`, `skips` or `contradicts` and the step id, or `plan silent`, with half a sentence saying why |
| Last line | `Turn used.` or `Turn not used: you can still act.` |

A judgement call is always printed in this form, so it cannot be mistaken for a rule:

```
JUDGEMENT CALL  The rules name two ways to get space and are silent on deleting other files.
Ruling: it works and frees about 0.4 GB, because the app rotates its logs weekly. That is about three minutes of growth, so the deadline does not move.
Turn used.
```

When the player's own action for the turn is used and no role is left to hand work to, go straight to the next turn block. Otherwise print `>` and wait: the player may still hand work to a role or take a free action.

## 4. Commands

Always available, never use the turn, never change the scenario.

| Command | Reply |
|---|---|
| `status` | The state block, the open tasks in words, and the same menu again |
| `log` | The log so far, one short line per entry: turn, what was done, how it was adjudicated |
| `help` | The commands, what uses a turn, how to hand work to a role, how to type a free action |
| `hint` | One nudge towards something the player can do next. It never states a hidden fact or a `truth`, and it is logged with its text. The review reports how many were used |
| `pause` | The state block and every log line, with the sentence about resuming |
| `end` | Ends play and goes to the after-action review. Also printed automatically after the last turn |

## 5. The log line

One JSON object per line, written **as play goes on**, never reconstructed afterwards. With a file system, append each to a file and do not print it. Without one, print each in its own one-line block under the answer, prefixed `log>`.

Write, in this order within a turn:

1. a `clock` line for each clock rule that applies at the start of the turn;
2. one `start` line, carrying the ids of the injects delivered this turn (or none);
3. then one line per thing the player does.

```
{"turn": 4, "clock": "22:25", "class": "clock", "rule": "RU1", "outcome": "then", "changes": [{"fire": "I5"}]}
{"turn": 4, "clock": "22:25", "class": "start", "inject": ["I4", "I5"]}
{"turn": 4, "clock": "22:25", "class": "command", "input": "hint", "hint": true, "text": "the hint as given"}
{"turn": 4, "clock": "22:25", "class": "investigate", "input": "look up what a restart does", "action": "A5", "rule": null, "changes": [{"reveal": "H3"}]}
{"turn": 4, "clock": "22:25", "class": "act", "input": "drop the slot", "action": "A8", "rule": "RU4", "outcome": "then", "changes": [{"set": {"disk": "ok", "cause": "removed"}}], "plan": {"step": "P3", "relation": "skips"}}
```

| Field | Values |
|---|---|
| `turn`, `clock` | The turn number, and `start_clock` plus `minutes_per_turn` for each turn played |
| `class` | `start`, `clock`, `inject`, `investigate`, `act`, `decide`, `communicate` (the player's own action, matching the action's class), `delegate` (with `to`: a role id), `other` (free input the action list does not cover), `wait`, `command` |
| `inject` | An inject id, a list of ids, or absent |
| `input` | What the player typed |
| `action` | The action id it was taken as |
| `rule`, `outcome` | The rule id and `then`, `late` or `unmet`; or `"judgement call"` with a `reason`; or `null` for an action that has no rule |
| `refused` | The reason, when the action was not allowed. A refused action changes nothing |
| `costs_turn` | For class `other`: whether it used the turn |
| `changes` | A list of `{"reveal": "H2"}`, `{"set": {"key": value}}`, `{"spend": {"RES1": 1}}`, `{"fire": "I6"}`. Exactly what the rule, the inject and the action declare. `session_log.py` refuses a change with no cause and a consequence left out |
| `plan` | `{"step": "P3" or null, "relation": "follows", "skips", "contradicts" or "silent"}` |
| `hint`, `text` | On a hint: `true`, and the hint as given |

`python scripts/session_log.py SCENARIO.json LOG.jsonl` checks every line against the scenario and prints the after-action tables. Its docstring lists each refusal.
