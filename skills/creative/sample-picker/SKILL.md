---
name: sample-picker
description: "Build a rendered gallery of two to eight meaningful visual or wording options on real content, with comparison, shared tweaks and a strict copy-back choice. Prefer two to five without padding a valid pair. Not for weighted decisions (decision-board), app back ends (forge), ambitious showcase composition (showpiece), whole-UI repair (anti-vibecoded-ui), specific interface rules (interface-architect) or state capture (state-gallery)."
metadata:
  revision: "1.2.0"
  revised-from: "Preserved Claude bundle/Codex fork and fresh web metadata; strict binding and additive receipts"
---

# Sample picker: choose by looking

Some choices are made with the eyes: a colour theme, a heading style, a layout, three versions of a line of copy. Describing the options in prose loses most of what matters, and "A, B or C?" asks the user to imagine all three. This skill renders the options on the user's own content in one page, lets them shortlist, compare, tweak and choose by tapping, and gives back a short block of text that says exactly what was chosen.

It is one page engine (`assets/picker.html`) and four scripts. The assistant writes a small data file; a script validates it and builds the page; the user opens it and pastes the result back.

The four entry scripts share `scripts/picker_result.py` for stderr-only receipts. Read `references/results.md` for the five result categories, legacy exit meanings and semantic coverage. Existing stdout/JSON remains compatible. Building or parsing is not browser execution, host activation or evidence that the alternatives are good.

## Use when

- The choice is visual, typographic, a layout, or wording in the place it will appear, with two to eight real candidates. Prefer two to five when that covers the meaningful alternatives.
- The user says "show me options", "which looks better", "pick a theme", "mock up a few versions", "let me choose between".
- The reply was about to describe options in adjectives ("warmer", "cleaner", "bolder").
- A block that starts `=== sample-picker choice v1 ===` is pasted in: apply it (procedure step 10).

## Not this skill

| The job | Use |
|---|---|
| Options that differ on criteria to be weighed: cost, risk, effort | decision-board |
| Building a shared/substantial application, API or back end | forge |
| Building a single-file personal tool with persistent data | pocket-app |
| Ambitious new showcase composition or an open-direction redesign | showpiece |
| Reviewing an existing page against rules | interface-architect |
| Seeing every state, theme and width of one design | state-gallery |
| Collecting answers from a person: a survey, a questionnaire | elicitor |
| Rescuing a page that looks generic | anti-vibecoded-ui |

## Inputs

- The real content the choice applies to: the actual heading, paragraph, rows, component label. If it is not in the conversation, ask for it or use the nearest real thing the user has supplied.
- What is being chosen, and anything fixed: brand colours, fonts that are installed, the device it will mostly be seen on.
- Supplied references, accepted direction and preferences, with their source. Confirmed task, access, delivery and brand constraints govern the options; a reference mechanism or preferred style does not silently replace them. State a consequential conflict before recommending a change.
- Or a pasted result block, with the picker data it came from.

## Tools: discover first

- **Somewhere the user can open an HTML file**: an artifact or preview pane, or a file they can open in a browser. Without one, see the failure branch "the host cannot render pages".
- **A shell with Python 3**, for `scripts/validate_picker.py`, `scripts/build_picker.py` and `scripts/parse_choice.py`. Without one, copy `assets/picker.html`, replace the object between its PICKER-DATA markers by hand, apply the rules in `references/picker-data.md` by reading, and say the picker was built and checked by hand.
- **Playwright with Chromium**, for `scripts/test_picker.py`. Without it, say the page was built but not driven, and ask the user to confirm that the Result view names what they chose.

## Procedure

1. **Decide whether to show at all.** If one candidate is plainly right, or the others fail a hard rule (body text under 4.5 to 1, a label that does not fit), say so and show that one. If the options differ on criteria and not on looks, this is the wrong skill.
2. **Get the real content.** Never draw options on invented or placeholder text. The validator refuses lorem ipsum and its relatives.
3. **Choose two to eight options that differ in a way you can name, preferably two to five.** Write each one's note: one line on what is different about it. If two notes come out the same, they are one option. Do not pad two meaningful choices to reach three. Six to eight can be appropriate when the distinctions matter; the validator advises reducing seven or eight but does not refuse them. More than eight needs a shortlist or separate choices.
4. **Pick the kind**: `theme`, `type`, `layout`, `copy`, `component`, or `custom` with a renderer per option. `references/picker-data.md` section 2 says what each draws, what it needs and what it measures.
5. **Commit to a recommendation** in `recommended`, with the reason in a clause. The user then has a position to react to.
6. **Add a tweak only if it changes the decision**: density, text size, alignment. Two or three at most, from the ids in section 3 of the reference. A tweak applies to every option, so the comparison stays fair.
7. **Validate and build.** `python scripts/validate_picker.py PICKER.json`, fix every ERROR and read every ADVISORY, then `python scripts/build_picker.py PICKER.json --out NAME.html` (add `--renderers FILE.js` for kind `custom`).
8. **Drive it and look at it when authorised capability is available.** `python scripts/test_picker.py NAME.html` runs the journey at 390 and 1280 wide, in a tab and in a sandboxed frame. It launches a browser, requests clipboard permissions and uses temporary-directory cleanup; do not run it when those actions are outside the current authority. Without a browser run, report built/validated and not driven. When rendering is available, inspect both widths: the options must differ meaningfully on the real content. Technical checks do not excuse weak alternatives.
9. **Hand it over** with two lines: what is being chosen, and the recommended option with its reason. Tell the user how to answer: tap to shortlist, open Compare, open one to tweak and choose, then Result, Copy, and paste the block into the chat.
10. **When the block comes back**, run `python scripts/parse_choice.py - --picker PICKER.json` with the pasted text on standard input. The source picker must validate first; picker/version, kind, actual chosen ID, any supplied chosen name and tweak values/step grid must match. An omitted/null chosen name remains compatible; the actual chosen ID is authoritative. An unbound parse is partial and cannot authorise applying a verified final choice. Apply a valid bound final choice and its tweaks exactly, after reading notes. For "in progress", narrow to the shortlist, act on notes, raise `version` and build again. Do not reopen a final choice or argue for the recommendation.

## Failure branches

- **The choice is not visual.** Weighted trade-offs go to decision-board. A question with an answer gets the answer.
- **Too small for a picker.** "Which of these two greys is darker?" or one tweak to one value: answer plainly, with the measurement if there is one.
- **Only one sensible option.** Say so, say why the others were dropped, and show the one. Do not pad the picker with weak options to make a choice of it.
- **No real content.** Ask for it, or use the nearest real thing in the conversation and say which. Never lorem ipsum.
- **The host cannot render pages.** Describe the options compactly: name, the one-line difference, and any figure the validator computed (for a theme, the lowest contrast pair). Say what is lost: the user is choosing from a description, without seeing the options on their content.
- **The validator refuses an option** (body text under 4.5, twin options, a control that changes nothing). Fix or drop the option and tell the user what was dropped and why. Do not edit the validator's verdict out of the reply.
- **A named font is not installed on the user's device.** The page says so and shows the fallback. Do not describe the sample as set in the named font.
- **The pasted block does not parse, or belongs to another picker or version.** Say exactly what `parse_choice.py` reported and ask for a fresh copy. Do not guess the choice from a damaged block.
- **The candidates are whole pages or raster images.** The built-in kinds draw text, colour, layout and one component. Use `custom` renderers for anything else that can be drawn with page elements. The page makes no requests, so remote images and web fonts cannot be shown; say so.
- **The choice is for other people to vote on.** This page records one person's choice in their own browser. It is not a survey; that is elicitor.

## Output

When handing over a picker, the first line names the method and the commitment, for example: "Sample picker: five themes for the notes tool, on your glaze-test note; I recommend Warm paper because every text pair on it measures above 4.5."

Then: the file, how to send the choice back (step 9), and what was checked and how (validated, built, driven by script, looked at; or done by hand).

When applying a result, the first line is: "Applying your sample-picker choice: Sage desk, density compact." Then do it. Mention a note if it asks for a change, and say if the choice differs from the recommendation without contesting it.

## Rules that always hold

- Options are rendered, on the user's real content. Never placeholder text, never a description standing in for a sample.
- Two to eight options, preferably two to five, each with a difference that can be said in one line. Two strong options are enough; never add weak options to meet a preferred count.
- One option is recommended, with the reason.
- Measured numbers on the page are measured in the user's browser at that width. They are facts about that rendering, not scores for the option.
- A returned final choice is applied exactly and not reopened.
- The page makes no outside requests and loads no fonts.
- The picker records one person's own choice. It is not used to profile or steer anyone.
- The skill is instructions, a page and scripts. It adds no memory: the choice exists only in the pasted block and in the user's browser storage.

## What has and has not been tested

Historical producer evidence: the following runs were reported for the earlier source on one Linux machine with headless Chromium. They are not newly run canonical tests, current-host acceptance or finished-output quality proof. Current offline/parser/syntax and preservation evidence is recorded separately in this revision's handoff; no new browser or clipboard suite is implied.

- **The engine and scripts**, `scripts/test_picker.py --self-test`: 8 of 8. Seven fixtures were built and driven (theme, type, layout, copy as a notice, component as a button and as a field, custom): 176 checks. Sixteen kinds of bad data were refused by the validator, each beside a valid neighbour that passed. Fifteen pasted blocks were parsed or refused as expected, including one wrapped in quote marks, a code fence and curly quotation marks. Host storage was used when present and fell back when it failed. A font that is not installed was named as missing.
- **Two planted faults.** A copy of the engine broken so that changing a tweak moves the choice to another option: the export test caught it. A theme whose body text measures 3.59 to 1, and one at 4.48: both refused by the validator and the builder, with nothing written; the next grey darker, at 4.54, was accepted.
- **Three example pickers** (five themes, four headings in a page header, three layouts of eight rows): 76 of 76 checks. Each was driven at 390 and 1280 wide, in a tab and in a sandboxed frame: shortlist two, compare, open one, change a tweak, choose, leave a note, open Result. The export named the chosen option, the tweak values, the shortlist and the note. The short text and the JSON form parsed to the same object. Copy filled the clipboard where allowed, and where refused the page said so and selected the text. A reload restored the session where storage worked; in the frame the page said the session is not saved. A saved session loaded into a fresh page; a wrong app, a newer schema, malformed JSON and an empty paste were each refused with the session untouched. Clearing was confirmed in the page and undone. A 5,000 character note on every option survived.
- **Contrast numbers.** The 65 figures the theme example shows equalled ratios worked out separately from the colours the browser computed. The lowest figure for each of its five options equalled the shared contrast checker's on the same specimen. With a faint muted colour planted, the page named two pairs under 4.5 (2.79 and 3.04) and the checker reported the same two.
- **A defect the checks found.** At 390 wide, two card buttons took keyboard focus underneath the bar fixed to the bottom of the screen. Scroll padding fixed it, and a test was added that fails on the earlier engine and passes on this one.
- **Shared checks on the examples**: the delivery check in a tab and a sandboxed frame (26, 18 and 17 steps, all passing); text contrast of the page in its four themes across five views, with a refused copy and a refused import showing (none below 4.5); every control tried once (14, 12 and 10, none without effect); target sizes at 390 (every target meets 24 by 24; the heading example also reports five overlaps, which are the fixed bar lying over two card buttons at the starting scroll position, and scrolling or focus clears them).
- **Looked at**: two composite screenshots, four views at 390 and two at 1280. One change came from looking: each option's name now sits above its sample, where before it was below and off the first screen on a phone.

Not tested: any model following this skill other than the session that wrote it; any real host's preview; any browser other than headless Chromium; a real phone or touch input; fonts other than the ones installed on the test machine; whether the options in any picker are good options. The field, notice, type, component and custom fixtures were driven by script and not looked at. "copy" as a page header is covered by the example only.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. "Pick a theme for my notes tool" with real note, field and table text supplied. Expect: two to eight meaningful options, preferably two to five, preserving accepted brand, device and reference preferences. A valid pair is enough; no forced warm/light leading option. Recommend one with a task-based reason, validate and build, and explain how to return the choice.
2. A pasted result block whose chosen option is not the recommended one, with a note. Expect: `parse_choice.py` run against the picker data, the chosen option and its tweak values applied exactly, the note acted on, and no argument for the recommendation.
3. A theme option whose body text measures under 4.5 to 1. Expect: the validator's refusal is reported, the option is fixed or dropped, and the picker that ships has no such option.
4. Negative control: "Should I host this on a VPS or a managed platform?" Expect: decision-board leads, or a plain answer. No picker is built.

## Final continuation revision

Claude authored the received base; the preserved Codex fork supplied the accepted two-to-eight/no-padding clarification. Revision 1.2.0 adds strict parser binding and additive semantic receipts after Shaun authorised local canonical work without further Claude messages. Originals and independent QA remain in the task workspace. Source/byte equality, host activation, browser behaviour and output quality are separate checks. Any claim of improvement needs matched briefs, constraints and revision budgets, fixed defect categories, hidden version labels and defect/correction/time counts; report no improvement shown when warranted.
