---
name: casefile
description: "Turns a research ledger into a working evidence workbench in one file: sources, claims, conflicts and assessments with lineage both ways, live ledger rules, export and reopen. Use for an evidence workbench, work through these sources and claims, trace this claim to its sources, which claims conflict, build a casefile. Not for doing the research (deep-research-orchestrator), weighing hypotheses (intelligence-analyst), checking a draft (fact-check), a general data app (forge)."
metadata:
  revision: "1.1.0"
---

# Casefile: a ledger a person can work

A research ledger is two CSV files: the sources that were consulted and the claims drawn from them. A casefile is one HTML page with that ledger inside it, where a person follows a claim to its sources and back, keeps conflicts in view, changes what the evidence supports, records assessments that name the claims they rest on, and takes the whole thing away again as files. The page is `assets/casefile.html`; `scripts/build_casefile.py` checks a ledger and writes a copy with the ledger in it.

The skill is instructions and tested files. It does not gather evidence, judge it, or remember anything between sessions. The casefile checks bookkeeping; whether a source is right is still the reader's call.

## Use when

- A ledger of sources and claims exists, or is being built, and a person will work it over days or weeks.
- The user wants to see what rests on what: which sources carry a claim, which claims carry a judgement, and what is left if a source is withdrawn.
- Conflicting claims need to stay visible until someone settles them.
- Assessments need recording against the claims they depend on, with the lot exported and reopened later.

## Not this skill

| The job | Use |
|---|---|
| Finding and reading sources, building the ledger | deep-research-orchestrator |
| Weighing competing explanations of the evidence | intelligence-analyst |
| Forecasts, risks and decisions drawn from it | oracle |
| Checking a finished draft against its sources | fact-check |
| A general app over other kinds of data | forge |
| A small tool that keeps a list of something else | pocket-app |
| Events in date order with conflicting dates | chronology |
| A question about a handful of sources | No skill: answer from the ledger, with a table if it helps |

## Inputs

- The ledger: a sources CSV and a claims CSV in the column layout of deep-research-orchestrator's `ledger_check.py`. The columns and allowed values are in `references/working-a-casefile.md` section 1.
- Optional: the wording of the questions, and any assessments the user has already made, as a small JSON file (same reference, section 1).
- A title.
- Or an existing casefile export, when the job is to carry on with one.

## Tools: discover first

- **A shell with Python 3**, for `scripts/build_casefile.py`. Without one, hand over a copy of `assets/casefile.html` unchanged and have the user import the two CSV files on its Keep and export view, where the same rules are applied. Say the build was done by hand and the page did the checking.
- **Python Playwright with Chromium**, for `scripts/test_casefile.py`. Needed only when `assets/casefile.html` has been changed. Without it the script prints `NOT RUN` and exits 3; do not change the engine page.
- **deep-research-orchestrator**, if installed. Its `ledger_check.py` can be given to `scripts/test_rules_agree.py --ledger-check PATH` to compare the two rule sets live. Without it the comparison runs against that checker's recorded output.
- **A way to show the user an HTML file.** If the host only previews it in a sandboxed frame, the page will say it cannot save there. Carry that into the reply.

## Procedure

1. **Decide whether a casefile is warranted.** It is when there is a ledger and it will be worked over time. For a single question about a few sources, answer in the reply. With no ledger, see Failure branches.
2. **Check the ledger without building**: `python scripts/build_casefile.py SOURCES.csv CLAIMS.csv --check-only`. Errors are listed by item in the checker's words. Fixing them is the user's decision: propose each correction and why, and never change a status, tier or date just to make the build pass.
3. **Add questions and assessments only if they exist.** Put the user's wording of each question, and any judgement the user has actually made, into the extra JSON file. Likelihood and confidence are separate fields. Do not write an assessment on the user's behalf to fill the page.
4. **Build**: `python scripts/build_casefile.py SOURCES.csv CLAIMS.csv --out NAME.html --title "Title" [--extra EXTRA.json]`. Exit 1 means the ledger has errors and nothing was written. The inputs are never modified.
5. **Report what the ledger says needs attention**, taken from the build output and not from memory: open conflicts, load-bearing claims that are only REPORTED, gaps, sources with no address or no date.
6. **Hand over the one file** with three sentences on how to read it (the views, lineage, and If this source falls: `references/working-a-casefile.md` sections 2 and 3) and where the work is kept (section 6).
7. **When the user comes back with an export**, read the envelope for the current state; it holds everything. Judgements reached since (the user's own, or from intelligence-analyst or oracle) go in as assessments resting on named claims, added in the page. If the ledger itself was regenerated, have the user import the two new CSV files on the Keep and export view, which keeps the questions and assessments; a fresh build from CSV starts without them.
8. **If the engine page itself is changed**, run `python scripts/test_casefile.py` and `python scripts/test_rules_agree.py`, each also with `--planted`, before handing anything over.

## Failure branches

- **No ledger yet.** Say that a casefile is built from one. Either the evidence is gathered first (deep-research-orchestrator, if available), or the user starts from the empty page, a copy of `assets/casefile.html`, and fills it by hand. Never populate a page with invented sources or claims.
- **A handful of sources and one question.** A table in the reply is enough. Offer a casefile in one sentence if the work looks set to continue.
- **The ledger has errors.** Nothing is built. List the errors, give the two ways out for each claim that cannot be a FACT (use REPORTED, or open a better source), and wait for the user's choice.
- **The user wants a rule bypassed** ("just make it a FACT"). Decline, give the rule's reason, and say what would satisfy it.
- **The host preview cannot keep data.** The page says so. Repeat it: work there lasts until the page is closed, and the exported casefile is the durable copy. Saving the file and opening it in a browser gives storage that the page will name.
- **Work was lost in a preview.** It cannot be recovered and this skill holds no copy. Say so, and give the export habit.
- **No shell.** Use the hand route under Tools and say so.
- **The request is research, analysis, a forecast or a draft check.** Hand over to the skill in the table. A casefile can follow once a ledger exists.
- **The ledger is very large.** Tested to 300 sources and 1,000 claims. Beyond that, say it is untested, and expect the export text boxes to be slow first.
- **This skill's own ways of going wrong:** describing a clean check as "verified"; writing the answer section of the brief for the user; presenting weakest support as a score; rebuilding from the original CSV files over later work that exists only in an export.

## Output

The first line names the method: "Casefile built from the ledger." Then:

- The file, with the counts: sources, claims, questions, assessments.
- The check result: errors (none, or the build did not happen) and the advisory notes, listed.
- What needs attention, by id.
- How to read it, in three sentences, and where the work is kept, in the page's words.
- What it is not: it checks bookkeeping, and no source has been verified by building this.

## Rules that always hold

- A ledger with errors is never built, and a refused change in the page changes nothing.
- No source, claim, assessment, quotation or date is invented to fill a casefile.
- An assessment rests on named claims and states likelihood and confidence separately. Its support is described in words, never as a score.
- Conflicts stay recorded on both claims. An open one is not averaged away or dropped from the brief.
- The brief's answer is the user's to write.
- A clean check is described as a tidy ledger, not as verified evidence.
- The pasted state library is the released pocket-app library, unchanged; `scripts/test_casefile.py` compares it with the recorded hashes.
- Nothing is called tested unless it was run in this session. The sandboxed frame is a local stand-in, not a chat host.

## What has and has not been tested

Run by the authoring session, on the real EAA ledger (5 sources, 8 claims, four questions and one assessment added) unless stated:

- `scripts/test_casefile.py --ledger-check` at 390 by 844 and 1280 by 800, in a tab and in a `sandbox="allow-scripts"` frame: 61 of 61 tests passed (one check of the library copies, then 15 tests in each of the four combinations). That covers lineage both ways, If this source falls on S3, C2 refused as FACT then allowed once S3 has an address and undone, C5 refused as load-bearing, a direct conflict recorded on both claims and settled with the count rising and falling, casefile round trip, a reading-log export and malformed CSV refused with the data intact, reload in a tab, and the honest note with working export in the frame.
- Exported CSV files run through deep-research-orchestrator's `ledger_check.py`: byte-identical to the originals, 0 errors and 8 advisory notes on both.
- `--planted`: 5 of 5 broken copies were caught by their named tests (a refused status change that still applies, a bad CSV import that wipes the ledger, a CSV export without the conflict columns, a pasted library that differs by one word, a library file that differs from its recorded hash).
- `scripts/test_rules_agree.py`, recorded and live against `ledger_check.py`: identical errors and advisory notes on four ledgers (the EAA ledger; a bad sample, 13 errors; a SYNTHETIC ledger written to trip every rule, 32 errors; a SYNTHETIC ledger of valid neighbours, 0 errors). `--planted`: 3 of 3 rule changes caught.
- SYNTHETIC ledger of 300 sources and 1,000 claims, Chromium on one machine, seven timed passes over two full runs: open and draw 306 to 1,538 ms; first draw of the list 8 to 54 ms (it draws a first part and offers more); search 11 to 33 ms; filter by status 36 to 265 ms; open a claim's lineage 14 to 73 ms; a status change 46 to 333 ms; undo 20 to 78 ms; the two CSV files 45 to 134 ms; the brief 56 to 288 ms; the casefile export (403,166 bytes) 123 to 667 ms, and 1,100 ms in an eighth pass. That pass failed the 700 ms limit then applied to every step. The limit for the three steps that write the whole ledger into a text box is now 2,500 ms, because the time is the browser laying out 400,000 characters (190 to 570 ms measured for that alone). The spread is load on a shared machine.
- With interface-architect's scripts: a 70-step journey passed in a tab and in the frame at both sizes; contrast in all four themes with a refusal showing and with import errors showing, 130 and 54 text elements measured per theme, none below AA, lowest ratio 5.26; target sizes at 390 wide, all 31 targets 24 by 24 or larger and no control under 44 by 44 in the list or in an open claim; dead controls, 29 tried on the example and 14 on the empty page, none without effect. Screenshots at 390 and 1280 wide were looked at.

Not tested: any model following this skill other than the session that wrote it; any real host's preview; any browser other than the Chromium that Playwright launches; a screen reader; ledgers beyond 1,000 claims; several people working copies of one casefile and merging them, which the page does not do.

## Acceptance cases

The full set, with negative controls and input files, travels with the source for review.

1. A sound ledger with "build me a casefile". Expect: the build result with error and advisory counts, one HTML file, what needs attention named by id, nothing invented, and where the work is kept.
2. A ledger with errors. Expect: nothing built, the errors listed in the checker's words, corrections proposed and not applied.
3. "Just make C2 a FACT so the brief reads better." Expect: declined, with the rule's reason and what would satisfy it.
4. Negative control: "if this one article is wrong, what do I lose?" about a five-source ledger. Expect: a plain answer read from the ledger, no build.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
