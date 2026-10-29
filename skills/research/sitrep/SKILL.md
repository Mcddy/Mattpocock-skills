---
name: sitrep
description: "Keeps a standing watch on a topic and reports what changed since last time, from a watch file of requirements, indicators and last known state that the user keeps. Use for keep an eye on, what's changed with, weekly update on, situation report, monitor this topic for me, sitrep. Not for one-off research (deep-research-orchestrator), an unattended pipeline (nexus-prime), a scheduled chat task (schedule) or forecasting (oracle)."
metadata:
  revision: "1.1.0"
---

# Sitrep: a standing watch, run on request

A watch is a topic the user will ask about again. The useful answer next week is what changed, and that needs a record of what was true last week. The record is one small file, `watch.json`, which the user keeps and hands back. Each run reads the sources again, compares with the file, and reports changes first.

The skill is instructions and two scripts. It adds no memory and no background process: nothing is watched between runs, and nothing runs unless the user asks.

## Use when

- The user wants to keep an eye on something and will ask again: "what's changed with", "weekly update on", "monitor this for me".
- The user hands back a watch file and asks for a sitrep.
- An earlier one-off answer is turning into a recurring question.

## Not this skill

| The job | Use |
|---|---|
| A question answered once, ending in a source and claim ledger | deep-research-orchestrator |
| Code that runs unattended and alerts | nexus-prime |
| A chat task that fires on a timetable | schedule |
| What will happen next, with likelihoods | oracle |
| Which explanation fits what happened | intelligence-analyst |
| Checking the claims in a supplied draft | fact-check |
| Events put in order with their dates | chronology |

## Inputs

- First run: the topic, and the decision or interest it serves. That is enough to start; build the baseline without a round of questions.
- Later runs: the watch file from the last run, pasted or attached. Without it there is nothing to compare with.
- Optional: sources the user trusts, how often they expect to ask, and anything they already know.

## Tools: discover first

- **Search and page reading.** Needed to check sources. Without them, say so, and either ask the user to paste the current text of each source or mark every source `not checked` and every item carried forward. Never fill the gap from recall.
- **A shell with Python 3**, for `scripts/watch_check.py` and `scripts/sitrep_diff.py`. Without one, compare the two versions by hand, by id, in the order in `references/sitrep-format.md`, and say it was done by hand.
- **The watch file is the only store.** Do not put the watch into a memory tool in place of the file. If the host can save files, save the file there as well as showing it.
- **Scheduling tools**, only if the user asks for automatic runs. See Failure branches.

## Procedure

### First run (no watch file)

1. **Say this is a baseline.** No comparison is possible yet.
2. **Write the purpose** in one sentence: the decision or interest the watch serves. Requirements that do not bear on it are cut.
3. **Write two to five requirements**: questions whose answers could change, each with a priority. "What is happening with X" is a topic. "Has the regulator published the final rule" is a requirement.
4. **Write indicators** for each requirement: an event or threshold that could be observed, where it would be seen, and what it would mean. The test is whether two people reading the same source would agree it has happened. "Further deterioration" fails; "the register lists the rule with a number" passes.
5. **List the sources** to check each time, highest tier first, each marked `each run` or `monthly`. Prefer the original record to an account of it. Tier definitions are in `references/watch-file.md`.
6. **Check each source now** and record the state: one statement per item, its status (FACT, REPORTED, ASSESSMENT or GAP), its sources and the date it was read. What nobody has established is a GAP item, written down.
7. **Write the file** starting from `assets/watch-template.json`, then run `python scripts/watch_check.py watch.json`. Fix errors. Read advisories and act on the ones that are right.
8. **Report the baseline**: for each requirement, where it stands, what is not established, and which indicator would change the answer. Hand over the file in full.

### Later runs (the user supplies the watch file)

1. **Validate what was handed back**: `python scripts/watch_check.py watch.json`. If the last run was long ago, say so first.
2. **Copy it to a candidate** and add an entry to `runs` dated today.
3. **Try every source that is due.** For each, set `last_checked` to today and `last_result` to `reached` or `unreachable`. A source that now wants a login, blocks access or times out is `unreachable`. Do not work around it.
4. **Go through the state items one at a time.** For an item with a source that was reached:
   - the source says the same: set `as_of` to today;
   - the source says something different: rewrite the statement and keep the id;
   - the source no longer says it: remove the item and add it to `withdrawn` with the reason.
   An item none of whose sources was reached is left exactly as it was, old date included.
5. **Add what is new** as new items with new ids. An id is never reused.
6. **Update indicators.** One moves to `seen` or `contradicted` only with an evidence entry naming the source.
7. **Run** `python scripts/sitrep_diff.py OLD.json NEW.json`. Fix errors; they are the script refusing things like a recheck claimed on an unreachable source. Read advisories. Set `changes` in the new run entry to the count it gives.
8. **Write the sitrep** from `python scripts/sitrep_diff.py OLD.json NEW.json --markdown`, in the order it gives: high-priority changes, indicator changes, other changes, what could not be checked, one line of no change. Add one or two sentences on what the changes mean for the purpose, marked ASSESSMENT. Wording rules and a worked sample are in `references/sitrep-format.md`.
9. **If nothing changed, say so in one line and stop.**
10. **Hand back the updated watch file in full.**

## Failure branches

- **No search or fetch tools.** Say so. Ask for pasted source text, or mark everything not checked this run. A sitrep written from recall is not a sitrep.
- **No watch file on a later run.** Start a baseline and say no comparison is possible. Do not rebuild last week's state from the conversation and compare against that.
- **A source is blocked, gone or behind a login.** Record it as unreachable. The items resting on it keep their old date and are reported as not checked. Do not look for a way round the block.
- **The user wants it to run by itself.** That is nexus-prime for a pipeline, or the host's scheduled tasks through the schedule skill. If the host supports it, a scheduled task can run a sitrep; the watch file still has to live somewhere the task can read and write. Offer either only if it is installed.
- **The request is too small.** "What's the latest on X?" asked once wants a plain answer or one-off research. Do not create a watch file unless the user means to come back.
- **The subject is a private individual.** Decline. Watches are for organisations, markets, technologies, public bodies and people in a public role, limited to that role.
- **It belongs to a neighbour.** Forecasting what happens next is oracle; explaining why something happened is intelligence-analyst. A sitrep reports what changed and stops.
- **Ways this skill goes wrong:**
  - padding an unchanged week with a recap. The recap is the failure the skill exists to prevent;
  - leading with a full summary and burying the one change;
  - reporting a withdrawn item as false. A source going quiet is not a source saying the opposite;
  - reporting a not-checked item as unchanged;
  - matching a new item to an old one because the wording is close. Ids are the only key;
  - raising REPORTED to FACT because it has been in the file for a while;
  - averaging two sources that disagree. Record each as its own item and show both.

## Output

The first line names the method: "Sitrep, changes since last run" or "Sitrep baseline", then the watch title and the two run dates.

Then, for a later run, in this order and nothing else:

1. Changes that touch a high-priority requirement.
2. Indicators that changed status.
3. Everything else that changed.
4. What could not be checked.
5. One line of no change for the rest.
6. One or two sentences on what it means for the purpose, marked ASSESSMENT with a confidence.
7. The updated watch file in full.

Each change carries its item id, status, source id with tier, and date. A changed item shows the old and the new statement. The whole sitrep fits on one screen; if it does not, the watch has too many requirements.

## Rules that always hold

- Changes come first. An unchanged run is one line.
- A withdrawn item is never reported as false.
- A not-checked item is never reported as unchanged.
- Present-tense claims are looked up this run, never recalled.
- Items are matched by id only.
- A FACT has a source of secondary tier or better attached. An indicator is seen only with evidence.
- Conflicts between sources are shown, not averaged.
- The user keeps the file. The skill stores nothing.
- No watch on a private individual.

## What has and has not been tested

Everything below is an author-side check: run locally by the session that wrote the skill, then rerun and extended on 9 October 2026 by a second session that repaired what it found. Nobody outside that authoring side has tested the skill.

- `scripts/test_sitrep_diff.py`: 39 named tests against the two scripts, all passing; each refusal is run beside its valid neighbour.
- The same script with `--mutants` plants 10 faults in temporary copies, and each was caught by the test named for it: withdrawn items labelled false; items matched by similar text; an unchanged run padded; a removed item reported as withdrawn while its source was unreachable; the freshness window off by a day; a FACT allowed without a secondary source; dates accepted without hyphens; the priority order reversed; an unreachable source left out of the written report; the skeleton's first line no longer naming the method.
- Two of those ten survived the first 36 tests when the second session planted them (the reversed priority order, and the unreachable source missing from the text while present in the JSON). Three tests were added and now catch them. The author also reports one defect found by its own planted faults (the indicator word list read "signs of" as a concrete verb); the second session did not reproduce that one.
- By hand, 35 runs of `watch_check.py` and 24 of `sitrep_diff.py` on good, bad and edge inputs: an unknown option, a missing value, a byte-order mark, an empty file, invalid UTF-8, NUL bytes, NaN, text or true where a number is read, `20261009`, 30 February, duplicate and dangling ids, mismatched watch ids, a FACT on a weak source, an indicator seen without evidence. Every refusal had its valid neighbour beside it, exit codes were as documented, and none produced a traceback.
- `watch_check.py` on a ten-item baseline whose statements were read from their sources on 9 October 2026 (0 errors, 0 advisories), and `sitrep_diff.py` on that baseline against a synthetic second run (4 changes, in the documented order) and a synthetic unchanged run (one line). Seven of the baseline's ten statements (F1, F3, F5 to F9) were read again from their sources by the second session and matched.
- The later-run procedure once more on a second synthetic watch: 5 changes, one unreachable source, one withdrawn item, and two primary sources that disagree kept as two items.

Not tested: any model following this skill other than the session that wrote it; any real host's preview. Also not tested: a real second run on a later date (every later run in the review material is synthetic); the indicator wording check beyond the six phrases in its test; whether the one-screen limit holds for watches larger than ten items; a host with no Python.

## Acceptance cases

The full set, with negative controls and input files, travels with the source for review.

1. "Keep an eye on whether the new accessibility standard gets cited in EU law." Expect: a baseline labelled as one, two to five requirements with priorities, indicators that name an observable event, sources with tiers, a GAP item for what was not established, and the watch file in full.
2. A watch file is handed back with "sitrep please", and the sources have moved. Expect: the comparison run, high-priority changes first, old and new statement side by side for a changed item, a withdrawn item reported with the sentence that it is not a finding of falsity, the unreachable source listed with the item resting on it, and the updated file.
3. A watch file is handed back and nothing has changed. Expect: one line, then the file. No recap.
4. Negative control: "Set this up to check every morning and message me." Expect: nexus-prime or schedule is named as the fitting tool if installed, and no claim that the skill runs by itself.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
