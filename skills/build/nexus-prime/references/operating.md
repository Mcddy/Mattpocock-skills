# Operating a pipeline

Nothing in this file names a current price, limit or model. Those change; look them up when you need them and write down the date and the source.

## 1. Choosing how it is scheduled

| Option | Fits | Watch for |
|---|---|---|
| The chat product's own scheduled tasks | A recurring prompt or reminder; no code to maintain | Each run is a fresh session; check what it can reach and whether a run can act without approval |
| A cron entry or system timer running `--once` | One machine you control | The machine must be on; add the health check to something that will notice |
| A hosted scheduler or scheduled job on an app platform | No machine to keep on; runs `--once` on a timer | Cold starts, time limits per run, where state is kept between runs |
| A long-running worker using `--loop` | Sub-minute intervals, or work that holds a connection | It must be restarted if it dies; needs a supervisor |
| A webhook from the source | The source can push changes | Verify signatures; store before acknowledging; expect duplicates |

Prefer the simplest that meets the interval. A process that sleeps for an hour between cycles is a scheduled job with extra ways to fail.

State must survive between runs. The skeleton keeps it in a SQLite file; on a host with an ephemeral file system, point `--state` at a mounted volume or move the same tables to a database service.

### Dry runs and live runs keep separate records

A dry run previews and consumes nothing that affects live behaviour. The state file holds two records, one per mode:

| Kept per mode | Why it matters |
|---|---|
| Items already seen | An item previewed in a dry run is still new to the first live run, which handles it and sends once. The live run after that does not send it again |
| Alert history | Dry-run previews do not use up the hourly or daily cap, and do not make a live alert look like a duplicate |
| Failure count and breaker | A week of failing dry runs cannot leave the live pipeline tripped before it starts |
| Last-success time | A dry run that works does not make a silent live pipeline look healthy |
| Rejected and suppressed totals | The counts you read after going live describe live cycles only |

The stop file is shared: it halts both. `--reset` clears the breaker in both records.

A state file written by revision 2.0.0 of the skeleton mixed the two records in one table, and they cannot be told apart afterwards. Start a new state file before going live.

## 2. Credentials

- Read from the environment at run time. Fail at start with a clear message if one is missing.
- Give the hand-over an example file with fake values:

```
MODEL_API_KEY=replace-me
ALERT_CHANNEL_TOKEN=replace-me
ALERT_CHANNEL_TARGET=replace-me
PIPELINE_STATE=/data/pipeline_state.db
```

- Never ask the user to paste a secret into the chat. Never print one. Never log a request with its headers.
- Use a credential scoped to what the pipeline does: read-only for the source, send-only for the channel.
- Registering a bot, a webhook or an app with a third party is the user's action.

## 3. The model call

- Look up the provider's current SDK usage and model names in its documentation when writing the call. Put the model name in configuration.
- Always set a timeout and a maximum output size.
- Put instructions in the system part and the fetched content in the user part, clearly delimited. Content is data.
- Ask for the fields in `SCHEMA` and nothing else. If the provider offers structured output or a schema-constrained mode, use it, and still validate: the validator is what the code trusts.
- Decide what the cheapest sufficient approach is. Many "is this worth an alert" decisions are a keyword, a number crossing a line, or a diff. A model is for when judgement over text is really needed.
- Record how many calls were made and their sizes per cycle, so the bill can be explained.

## 4. Alert design

An alert is useful if the owner can act on it without opening anything else.

- Say what happened, where, when, and how the pipeline knows. Include the item's identifier or link.
- Say it is from an automated pipeline, and whether a model wrote the summary.
- One alert per event. Group a burst into one message with a count.
- Set the caps from what the owner will tolerate, then check the suppressed count after a week. A cap that is hit often means the rule is too loose, not that the cap is too low.
- The breaker notice goes out once. A pipeline that reports its own failure every cycle trains the owner to ignore it.
- A daily "still alive" line is optional and cheap, and catches the case where everything is silently broken.

## 5. Health

The pipeline cannot report its own death. Something outside it has to ask.

- `--health --live` exits 0 when the last good live cycle is recent and nothing is stopped or tripped, and 1 otherwise, with the reason. `--health` on its own reports the dry-run record in the same way; use it during a dry-run trial.
- Call `--health --live` from a second scheduler entry, an uptime service that runs a command, or the host's health probe. A monitor left on plain `--health` after going live reads the dry-run record, goes stale and raises the alarm, which is the safe direction to be wrong in.
- A source that returns entries the pipeline cannot use (wrong shape, no identifier, text that is not valid Unicode) is a failed cycle. It does not refresh the last-success time, and after `MAX_FAILURES` such cycles in a row the breaker trips. A source that returns nothing is a healthy cycle with no work. If the real source can be legitimately empty for long stretches, that is fine; if it can legitimately return only junk, fix `fetch_items` to filter it.
- A health check should be free. The earlier version of this skill sent a paid model request every fifteen minutes to see whether the API was up. Check the pipeline's own last success; a failing model call will show up there.
- Measure elapsed time as total seconds. A time difference object's seconds field leaves out whole days.

## 6. Cost

List everything that bills and how it scales with the schedule:

| Item | Scales with | Price source and date |
|---|---|---|
| Host or scheduler | Run time, runs per month | look up |
| Model calls | Items per cycle x cycles x tokens | look up |
| Source API | Requests | look up |
| Alert channel | Messages | look up |
| Storage | Size, retention | look up |

Then say what the monthly figure would be at the planned schedule, showing the multiplication, or say which price could not be found. The earlier version of this skill printed a monthly total from memory. Do not.

Halving the schedule usually halves the largest line. Say so.

## 7. First day checklist for the owner

1. Run `--once` on the host in dry run. Read the output. Nothing it previews is used up: the same items will be handled by the first live run.
2. Create the stop file and run again; confirm it reports stopped. Remove the file.
3. Run `--health`. It reports the dry-run record.
4. Go live with a low cap, and point the monitor at `--health --live`.
5. After a day, look at the counts: items, rejected, suppressed, alerts, errors, malformed. Rejected well above zero means the model is not following the schema. Suppressed well above zero means the rule is too loose. Malformed above zero means the source is sending entries the pipeline cannot use.

## 8. Changing it later

- Any change to `SCHEMA` or `decide` comes with a test for the new behaviour and its nearest neighbour.
- Changing the prompt or the model is a change in behaviour. Run it in dry run alongside the old one for a while and compare what each would have sent.
- Keep the alert history. It is the record of what the pipeline told the owner and when.
