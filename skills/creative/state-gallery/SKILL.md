---
name: state-gallery
description: "Captures a page in every declared state, theme and width onto one contact sheet, with measured facts beside each frame, so the whole interface can be judged at a glance. Use for show me every state, screenshot all the states, does it work in dark mode and on a phone, contact sheet, before and after of this redesign. Not for building the interface (forge), reviewing it against rules (interface-architect) or a design critique with no page to load (anti-vibecoded-ui)."
metadata:
  revision: "1.2.0"
---

# State gallery: every state, theme and width on one sheet

A generated interface is usually shown once: populated and happy. The defects are in the other states: loading, empty, no results, an error, a very long name, the dark theme, the phone width. This skill makes all of them visible together, so they can be judged in a minute.

It is one script and one page template. The script loads the page once per state, theme and width, runs the steps that reach the state, measures a few facts and takes the picture. The template lays the frames out as a contact sheet. The measurements are aids. The sheet exists so that someone looks, and the first one to look is the model, before the user sees it.

## Use when

- An interface is about to be called done. Capture it first.
- The user asks to see every state, or whether it works in the dark theme or on a phone.
- A redesign is being compared with what it replaces: the same states file, two galleries.
- A fix has gone in and the question is what else moved: capture again and compare the facts.

## Not this skill

| The job | Use |
|---|---|
| Build a shared product, back end or substantial application | forge |
| Build an ambitious polished showcase | showpiece |
| Review a page against numbered interface, accessibility and delivery rules | interface-architect |
| Make a focused repair to an existing interface, or critique a design with no page to load | anti-vibecoded-ui |
| Choose between a few rendered options for one design decision | sample-picker |
| Build a persistent single-person tool on any device | pocket-app |

## Inputs

- The page: an HTML file, or the address of an app running locally on throwaway data. Never a live system.
- The themes and how the page switches them (an attribute on the root element, or a control to click).
- The widths that matter. Default: 390 and 1280.
- The states. If the user has not listed them, derive them (procedure step 2).

## Tools: discover first

- **A shell with Python 3, the Playwright package and a Chromium it can launch.** `python scripts/state_gallery.py STATES.json --dry-run` validates only the input file; it does not discover or verify browser capability. A capture run reports `runner-error` and legacy exit 3 when the browser is missing. Without it, see the first failure branch: nothing is captured, and the reply says so.
- **A way to look at pictures.** The script writes PNG files for the model to read. Without that ability, build the sheet, say that nobody has looked at it yet, and hand the user the sheet with each state's `shows` line as the checklist.
- **The page's own server**, for an app with a back end. Start a copy on a spare port with an empty or seeded throwaway data file. Without a way to run it, capture only the states a static file can reach and list the rest as not captured.

## Procedure

1. **Decide whether a gallery is the right size of answer.** A single static screen needs two or three screenshots in the reply, not this. A page with data, actions or more than one theme needs the gallery.
2. **List the states.** Walk the table in `references/states-and-reading.md` section 1 for each view: loading, empty, no results, error on load, error on an action, refused by a rule, busy, success, destructive confirm, long content, the largest realistic set. For each, write a state or write why the page cannot be in it. Give every state a `shows` line: one sentence on what a person should see.
3. **Make each state reachable**, in this order of preference: steps through the page's own controls; `route_fail` and `route_delay` for error, loading and busy states; a second instance with an empty data file for empty states; seeded rows for long content. Section 2 of the reference has the detail. Record the stored data before the run.
4. **Write the states file** (format: run `python scripts/state_gallery.py` with no arguments). End each state's steps with an `expect:` that proves the state was reached. If the page has a theme control, switch themes with it (a theme's `steps`), so the control shows the right theme in every frame.
5. **Validate, then capture.** `python scripts/state_gallery.py STATES.json --dry-run`, then `python scripts/state_gallery.py STATES.json --out DIR`. It writes `gallery.html`, `gallery.json`, `frames/` and `sheets/`, and prints one line per frame that has a measured problem or was not reached.
6. **Deal with NOT REACHED first.** Read the stage and reason: a state may be unreachable, or its later screenshot or encoding may have failed. A state never reached has no measurements; a later capture failure can retain `measured_facts` and `measured_problems`. Keep those observations, but do not claim an image was captured or visually inspected. Fix the step or capture failure, or keep the labelled empty frame and report why. Never delete the state to make the sheet clean.
7. **Look at the sheet.** Read the pictures in `sheets/` (one per state and width, all themes together), phone width first, and any single frame at full size from `frames/`. For each state write one line: what the frame shows against its `shows` line, and what is wrong. Do this before showing the user anything. Section 4 of the reference lists what to look for.
8. **Check the stored data is unchanged** after the run. If it changed, a step saved something, later frames saw a different page, and the run must be repeated on fresh data.
9. **Classify what was found**: measured defects (fix), design assessments (fix, with the reasoning and how sure), preferences (apply the user's; not a finding of fact). Apply the craft rejection test from the forge skill's front-end method to the whole sheet.
10. **Report** in the form under Output, with the sheet. After fixes, capture again into a new folder and run `python scripts/state_gallery.py --compare OLD/gallery.json NEW/gallery.json`.
11. **If the sheet has to travel** and is too heavy, rerun with `--image-scale`, `--max-image-width` and `--quality` (reference section 6), and say that the embedded frames are reduced.

## Failure branches

- **No browser tool.** Do steps 1 to 4 anyway. Give the user the list of states, the `shows` line for each, and what to check by hand at 390 and 1280 in each theme. Say plainly that nothing was captured and nothing was measured.
- **A state cannot be reached without changing the app** (it depends on time, a permission or a third party). Say so, keep it on the list as not captured, and propose the smallest hook: one query parameter or one demo-data control.
- **A one-screen static page.** Two or three screenshots in the reply are enough. Say that a gallery would add nothing.
- **There is no page to load** (a description, a mock-up image, a plan). This skill cannot capture it. A critique belongs to anti-vibecoded-ui or interface-architect.
- **The request is to build or fix the interface.** Route shared or substantial applications to forge, persistent single-person tools on any device to pocket-app, focused interface repairs to anti-vibecoded-ui, ambitious showcases to showpiece, and numbered-rule audits to interface-architect. Offer the gallery once the relevant page exists.
- **The states file is refused** (exit 2). The message names the state and the reason. Fix the file; do not work around the check.
- **Every frame says "No measured problem".** That is a measurement, not a verdict. Step 7 still applies in full. A blank empty state, a weak hierarchy and a generic composition all measure clean.
- **Frames of one state differ between themes in content, not colour.** A step changed stored data. Use a throwaway data file and states that end where they began.
- **The only running copy holds real data.** Do not capture it: steps click and type. Ask for a throwaway copy, or make one.
- **The sheet is very large** (hundreds of frames). Capture fewer themes before fewer states, or split by view. `--max-frames` refuses a run above 240 frames unless raised on purpose.

## Output

The first line names the method and the size of the run, for example: "State gallery: 10 states x 4 themes x 2 widths, 80 frames; 0 with a measured problem, 0 not reached."

Then:

1. Where the sheet is, and its size.
2. A table, one row per state: what it should show, what the frame shows, the finding and its kind (measured defect, design assessment, preference, or none).
3. What to fix, most serious first.
4. What was not captured: hover, any unreachable state, a real device, and anything listed but not reached.
5. What was done by hand, if any tool was missing.

Say what kind of evidence each claim rests on: measured by the script, seen in a frame, or inferred. Never write "all states pass".

### Read the result receipt

Every operation emits a receipt with its phase and one status: `completed`, `partial`, `not-applicable`, `failed` or `runner-error`. `--dry-run` is phase `validation`, with zero captures. `--compare` is phase `compare`, for stored facts only; no common frames is `not-applicable`. Neither establishes visual quality.

For capture, a known measured defect is `failed`, even if another frame or sheet is missing. Missing requested captures or sheet exports without a known measured defect are `partial`. Missing browser/tools or invalid setup are `runner-error`. A late execution error retains any known measurements and all requested combinations, including those not attempted. `execution_status` and `runner_errors` keep that interruption separate from observed page defects.

Legacy process exits remain: 0 for a built gallery or valid validation/comparison, 1 with `--fail-on-problems`, 2 for invalid arguments/input/setup, and 3 when execution cannot finish. Exit 0 can therefore accompany `failed` or `partial`: read the receipt status. The flag changes the legacy exit policy, not the receipt category.

The final `gallery.json` contains the receipt and output inventory after the sheet attempt. If it cannot be written, the stderr receipt retains observations and says so. Preserve earlier output files; use a new output folder for each run. `summary.with_measured_problem` remains a legacy combined count including unreached frames; use `summary.measured_problem_frames` for measured defects only. `measured_facts` and `measured_problems` preserve observations made before a screenshot or encoding failure; they do not establish that a usable image was captured.

## Rules that always hold

- Every declared state is on the sheet. One that was not reached is a labelled empty frame, never left out.
- "No measured problem" is never reported as "works", "passes" or "looks right".
- The model looks at the sheet and writes one line per state before the user is shown it.
- Captures run against throwaway data only, and the data is checked afterwards.
- An emulated width is not a device, and the report does not call it one.
- `--compare` compares measured facts. Pixel comparison is out of scope, and the report says so when a redesign is compared.
- No score is produced for how a page looks.
- The capture script, gallery template and tests add no memory or background process.

## Historical producer tests (not rerun for 1.2.0)

Original producer history, retained from the earlier authoring session on one Linux machine with headless Chromium. These results were not rerun for revision 1.2.0. Everything below was labelled "run locally" or "run in a sandboxed frame stand-in" by that producer; nothing was run in a real host.

- **The script's own suite**, `scripts/test_state_gallery.py`: 16 of 16 named tests passed. On a planted page, overflow was flagged in the long state at 390 and nowhere else, low contrast in the six frames of the dim theme and nowhere else, and the blank empty state measured clean. An unreached state stayed on the sheet as a labelled empty frame. `--fail-on-problems` exited 1 on the planted page and 0 on a clean one. `--compare` named the two changed frames, four added and four removed, and no change between a gallery and itself. Twelve bad states files were refused with exit 2, each beside a valid neighbour that passed, along with bad bytes, a frame limit and unknown options. `route_fail` and `route_delay` showed an error and a loading state on a served page. An address nothing listens on exited 3 with NOT RUN.
- **Seven planted faults**, one at a time, in copies of the script and the template: overflow forced to zero, unreached frames dropped, aborted requests counted as failures, the contrast threshold lowered to 2, overflow left out of the comparison, the problems filter inverted, the image scale ignored. All seven runs failed, and each time the test named for that behaviour was among the failures.
- **A real app with a server**: 10 states x 4 themes x 2 widths = 80 frames in about four and a half minutes, 0 with a measured problem, 0 not reached, stored data identical before and after. The sheet was 883,867 bytes with reduced frames.
- **A page with three planted defects**: 20 frames. Overflow was flagged at 390 in the long-reference state only. Low contrast was flagged in the four dusk frames that draw muted text. All four frames of the blank empty state said "No measured problem". Four frames were not reached and were labelled.
- **The sheet page itself**, on both galleries: the shared delivery check in a tab and in a sandboxed frame (31 of 31 and 35 of 35 steps); text contrast in its four themes with problem labels, the opened viewer and both panels showing (none below 4.5, lowest 5.73); target sizes at 390 wide (23 of 23 and 83 of 83 meet 24 by 24); every control tried once (23 and 83, none without effect).
- **Looked at**: seven screenshots. The sheet at 1280 and at 390 and an opened frame, on a build with slightly larger frames than the shipped one; an opened wide frame of the shipped sheet (names, counts and messages readable at 56 percent, small monospaced codes soft); the planted sheet; all ten states of the app at 390 at full size; four of its states at 1280.

Not tested: any model following this skill other than the session that wrote it; any real host's preview; any browser other than headless Chromium; a real phone; a page behind a login; a gallery of more than 80 frames; hover states, which the tool does not capture. In the 80-frame example, 15 frames were looked at at full size and the rest only as thumbnails or not at all.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. "Show me every state of this page" with a small page that logs parcels. Expect: a states file covering at least empty, populated, a validation error and long content, each with a `shows` line; a gallery built; the sideways overflow at 390 and the low-contrast theme reported as measured defects in the frames where they occur; the blank empty state reported as something seen in the frame, not measured.
2. A states file with one mistyped step kind. Expect: the dry run is used, the refusal is quoted, the step is corrected, and the corrected file is run.
3. "I fixed the wrapping. What changed?" with two fact files. Expect: `--compare` is run, the two frames whose overflow changed are named, and the reply says that only measured facts were compared.
4. Negative control: "Build me a settings page with a dark mode." Expect: forge leads; the gallery is offered as the check once the page exists.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.

Revision 1.2.0 changes result reporting and preservation of observed evidence. Its new verification uses retained offline stubs for capture, encoding, missing tools, sheet export and late output failures, plus separate input/compare CLI fixtures. These are source/controlled-function tests. No real browser, rendered gallery or new device evidence was obtained for this revision; the historical browser results above are not rerun claims.
