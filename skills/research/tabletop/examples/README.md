# Examples

One worked example, made by the session that wrote this skill. It has not been played or reviewed by anyone else.

## outage-run

A complete exercise of the outage scenario: 8 turns played of 10, ended by the player.

| File | What it is |
|---|---|
| `scenario.json` | The scenario as played: a copy of the shipped `outage-small-saas.json` |
| `play-log.jsonl` | The play log, 26 lines: one `start` line per turn, one line per thing the player did, one clock rule |
| `transcript.md` | The whole conversation in the fixed turn format: briefing, eight turn blocks, every answer block |
| `session-log-output.txt` | What `session_log.py` printed for the log: 0 validation errors, and the after-action tables |
| `after-action-review.md` | The six-part review written from those tables. No score |
| `check_transcript.py` | A review aid for this example only. It checks five things a program can check about the transcript against the scenario and the log |

### How it was made, exactly

One session wrote both sides. That is the honest limit of this example: nobody was surprised by anything.

1. The scenario was written and passed `scenario_check.py` before any play.
2. The player was written as a persona decided in advance: an engineer who trusts the runbook and a green dashboard tile more than they should, works alone, and asks for one hint. The moves were chosen for that persona, turn by turn, and include real mistakes: a turn spent phoning someone known to be in the air; the support lead left unanswered for four turns; the misleading backup tile taken at its word and a wrong statement made to customers; a turn spent clearing 0.4 GB when the cause was already known.
3. Each move was adjudicated from the scenario's rules and written to the log. `session_log.py` then checked every line against the scenario. Nothing in the log was changed after a consequence turned out badly for the player.
4. The transcript's answer blocks quote the rule text from the scenario. Its state blocks are the output of `session_log.py --state` for the log up to that point, which is what the turn format requires of a facilitator with a shell.
5. The review was written from `session-log-output.txt`.

The transcript shows the things the specification asks for: the fixed turn format (every turn); an information request that uses the turn (turn 5, reading the backup log; also turns 2 and 6); a hint (turn 4); a judgement call labelled as one (turn 3); hidden facts discovered by action (H1 on turn 2, H3 on turn 4, H2 on turn 5, H4 on turn 6).

### Regenerate and check

From the skill folder:

```bash
python scripts/scenario_check.py examples/outage-run/scenario.json
python scripts/session_log.py examples/outage-run/scenario.json examples/outage-run/play-log.jsonl
python examples/outage-run/check_transcript.py examples/outage-run/transcript.md \
  examples/outage-run/scenario.json examples/outage-run/play-log.jsonl --scripts scripts
```

The second command reproduces `session-log-output.txt`. The third prints `RESULT: PASS` with 10 state blocks, 4 hidden facts, 8 rule citations and 17 player inputs compared.

### What was shown to fail

- Four copies of the transcript with one planted fault each (an action offered before the fact it depends on was found; a rule's outcome softened; a hidden fact leaked in an aside; a state line edited by hand) each failed `check_transcript.py`.
- A copy of the log in which a hidden fact is revealed on a line whose action does not discover it fails `session_log.py` with a facilitation error.

### What this example does not show

Whether a real person finds the format usable on a phone, whether the injects land as intended on someone who has not read the scenario, or whether the review changes anything. Only play by someone else can show those.
