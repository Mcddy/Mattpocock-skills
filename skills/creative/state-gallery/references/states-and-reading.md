# Choosing states, reaching them, and reading the sheet

Detail for `SKILL.md`. The states file format itself is in the docstring of `scripts/state_gallery.py`; run the script with no arguments to print it.

## 1. Which states to capture

Walk this list for each view of the page. It is the state list from the forge skill's front-end method (its `references/frontend.md`, section 3), with two additions at the end. For each line, either write a state or write down why the page cannot be in it.

| State | What a person should see | Usual way to reach it |
|---|---|---|
| Loading | Something in the shape of what will arrive | `route_delay` on the data request |
| Empty (nothing exists yet) | A sentence saying so, and the first action | A second copy of the app with an empty data file, named in the state's `page` |
| No results | What was searched for, and a way back to everything | `fill:` the search with a term that matches nothing |
| Error on load | What failed, that nothing changed, a retry | `route_fail` on the data request |
| Error on an action | The reason beside the field, typed values kept | `fill:` bad values, `click:` the action |
| Refused by a rule | The server's reason in words | Steps that break a rule the server owns |
| Busy | The pressed control marked as waiting | `route_delay` on the write, limited with `"method": "POST"`, then `click:` |
| Success | A brief confirmation where the user is looking | Only if the write can be undone or the data file is thrown away afterwards |
| Destructive confirm | The question in place, naming the thing | `click:` the remove control and stop before confirming |
| Long content | The longest realistic name, code and number, all inside their boxes | Seed two such items and filter to them |
| Largest realistic set | The page with as many rows as it will really hold | Seed them; expect a count |

Give every state a `shows` line: one plain sentence saying what a person should see. It prints beside the row on the sheet, and it is what the frame is judged against. A state without one can only be judged against a guess.

End each state's steps with an `expect:` that proves the state was reached. Without it, a frame of the wrong state looks like a pass. A frame whose step fails is drawn as a labelled empty frame with the reason. It contributes to missing coverage, not a measured page defect. The historical combined summary counter still includes it for compatibility; the new receipt separates both counts.

## 2. Making a state reachable

In order of preference:

1. **Steps alone.** Type, click and filter through the page's own controls.
2. **Request interception.** `route_fail` shows an error state while the server is healthy. `route_delay` holds a request until the frame has been taken, which is the only reliable way to photograph a loading or busy state. Both leave the page's own document alone. An entry is a glob, or `{"url": GLOB, "method": "POST"}` to catch a write and let the reads through.
3. **A second instance.** Empty and first-run states need a copy of the app with nothing in it. Start it on another port with an empty data file and give that state its own `page`.
4. **Seed data.** Long content and large sets need rows that exist. Put them in before the run, through the app's own API.
5. **A hook in the app.** Only when none of the above works: a state that depends on time, on a permission, or on a third party. Say that the state could not be reached without changing the app, and propose the smallest hook: one query parameter or one demo-data control, removed or disabled outside development.

Steps must leave stored data as they found it. Every frame of a state is a fresh load of the same page, so a step that saves something changes what the next theme and width see. Use a throwaway data file, stop destructive flows at the confirm, and compare the data before and after the run.

A page that is one static screen with no data does not need any of this. Two or three screenshots in the reply are enough.

## 3. What is measured, and what the words on the sheet mean

Each frame's caption starts with a verdict in words, never colour alone.

| Caption | Meaning |
|---|---|
| No measured problem | Every count below is zero and every step passed. This is a measurement, not a judgement |
| Not reached | The requested state or usable capture is unavailable; the label gives the stage and reason. A state never reached has no measurements. A later screenshot or encoding failure can retain `measured_facts` and `measured_problems`, without proving an image was captured |
| Overflows sideways by N px | The document is wider than the viewport. The widest offending elements are listed when the frame is opened |
| N text elements cut off | Text inside a box that hides or clips its overflow and is smaller than the text |
| N text elements below contrast | Below 4.5 to 1, or 3 to 1 for large text (WCAG 1.4.3 AA), measured as rendered in that theme |
| N targets under 24 by 24 | Pointer targets that fail the 24 by 24 size with no spacing exception (WCAG 2.5.8 geometry) |
| N console errors | Errors the page wrote, and uncaught exceptions |
| N failed requests, N server errors | Requests that failed or were answered 500 and above, or any error for a page, script, style sheet, image or font |

Reported but not counted as a problem: a data request answered 400 to 499 (that is a server refusing bad input, which a refusal state is meant to cause), targets under 44 by 44, text over an image or gradient that could not be measured, and the requests this tool aborted or held on purpose.

Limits of the measurements: hover is never captured; focus is captured only where a step left it; an emulated width is not a device; contrast is measured for text only, not for borders, icons or focus rings.

## 4. Reading the sheet

Open `gallery.html`, or read the pictures in `sheets/` (one per state and width, every theme side by side with its captions). For a single frame at full size, read it from `frames/`.

Read row by row, not frame by frame. For each state, write one line:

1. Does the frame show what the `shows` line says? A blank area where a message should be is the commonest failure, and no measurement sees it.
2. Is the state told apart from its neighbours by something other than colour?
3. Does it hold in every theme? Look for a theme where a stripe, a border or a muted line disappears.
4. Does it hold at the phone width? Look for a control pushed off the first screen, a label that wraps into the next, a table that became a strip.
5. After the action, can the user tell what happened?

Then apply the craft rejection test from the forge skill's front-end method to the whole sheet. A sheet with no measured problem can still fail it: a page that would suit any product after a noun swap passes every count here.

Write findings in three groups, because they are handled differently: measured defects (fix), design assessments (fix, with the reasoning and how sure), and preferences (apply the user's stated preference; do not call it a finding of fact).

## 5. Comparing two runs

`python scripts/state_gallery.py --compare OLD_gallery.json NEW_gallery.json` lists frames whose measured facts changed, and frames added or removed. Use it after a fix, or for a redesign captured with the same states file.

It compares facts only. Two frames with identical facts can look different, and a redesign usually does. For before and after, build both galleries and look at the two sheets for the same state together.

Read the phase and status in the receipt. A completed comparison means the stored facts were compared, not that either gallery is complete or better. No common frame keys is not-applicable. Added and removed frames are still listed. Input validation, capture coverage and a design assessment are separate claims.

## 6. File size

Every frame is embedded in `gallery.html`, and the script prints the size. In the build session, eighty frames of one app came to about 2.4 MB with the wide frames embedded 1024 px wide, and to 884 kB with `--image-scale 0.7 --max-image-width 720 --quality 30`. The embedded pictures get softer; the pictures in `frames/` stay at full size, and an opened frame says what percent of the captured size it is showing. To cut the count, capture fewer themes before fewer states: a missing theme hides less than a missing state.
