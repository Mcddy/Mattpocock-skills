---
name: percept
description: "Builds a self-contained, offline, single-file animated micro-lesson course: short step-through animations grouped into modules, each lesson moving one idea. Use when the user asks for animated or visual lessons, an animated course, or step-through explainers for a subject. Not for quiz and mastery study apps (preceptor), one interactive explainer for a single concept (learning-visualiser), simulations with adjustable parameters (simforge), or explorable concept maps (atlas)."
metadata:
  revision: "2.1.0"
  revised-from: "percept as exported 8 Oct 2026"
---

# Percept: animated micro-lesson courses

Turns a subject into one HTML file that plays a course of small animations. Each lesson shows one idea in two to four beats: the picture, the key phrase and the reason advance together. The reasoning happens once, while the course is written. The finished file makes no network calls and runs no model.

The skill ships a working player. Fill in its course data. Do not rebuild it, and change it only in the two cases set out in step 7.

- `assets/engine.html`: the player, 16 animation renderers, autoplay, progress, a display sheet (theme and motion) and a 16-lesson demo course, one lesson per renderer.
- `references/animation-catalogue.md`: what each renderer is for and its parameters. Read it before writing lessons.
- `scripts/smoke.js` and `scripts/render_check.py`: two checks for a finished course file. Both are optional and both say plainly when they could not run.

The engine was produced by a fixed patch from an earlier engine, plus one later edit on 9 Oct 2026 that holds drawing labels at a readable size on narrow screens. Being reproducible shows the patch edits are the listed ones. It does not show the engine is correct; the checks are the evidence for that, within their limits.

## Use when

- "Animated lessons for X", "an animated course on X", "step-through lessons on X".
- "Make X click visually" where the answer is a sequence of ideas, not one picture.
- The user has material (notes, a syllabus, a chapter) and wants it as short animated lessons.

## Not this skill

| The user wants | Use |
|---|---|
| Quizzes, spaced review, mastery gates, a study app | preceptor |
| One interactive explainer for one concept | learning-visualiser |
| A simulation with parameters to change and a numerical model | simforge |
| A map of how concepts connect | atlas |
| A slide deck or a written guide | the host's deck or document tools |

If this skill was loaded for a request that names no format ("teach me X"), do not build a course. Teach it in the reply at the depth asked, and say in one line that an animated course (this skill) or a quiz-based study app (preceptor) can be built from it. If the user's standing preferences ask for a built first version, a one-module taster of 4 to 6 lessons is the most to build unasked.

## Inputs

Needed to start: the subject, narrowed enough to order ("linear algebra for machine learning", not "maths").

Useful, and worth one compact question only when missing and material:

- Level: none, some, rusty or solid.
- Goal: an exam or named syllabus, a job task, or understanding.
- Size. Four sizes: taster (one module, 4 to 6 lessons), short (10 to 14), starter (about 24), full (about 64). When nothing is said, use the smallest size that covers what was asked: a single mechanism is short, a whole subject is starter, and full is only on request. Say which size you chose.
- Material the course must follow (a syllabus, a textbook chapter, the user's notes).

Ask at most one round, and only for level and goal when both are unknown. Everything else has a default: analogies from everyday objects, no exclusions, size chosen as above. State the assumptions you made at the top of the syllabus so they are easy to correct.

## Tools: discover first

Look at what the session can do before promising anything.

- A way to write and deliver a file or a hosted page. If neither exists, give the filled data block and say the user must paste it into the engine.
- Web search or supplied source material, for checking subject claims. If neither exists, see "When a claim cannot be checked".
- Node with jsdom, or Python with Playwright and a browser, for the checks. If neither exists, report the checks as not run.

## Procedure

### 1. Syllabus

Design modules in dependency order. A learner going top to bottom must never meet an idea before its prerequisite.

- Taster: 1 module. Short: 2 to 3 modules. Starter: 4 to 6 modules. Full: 8 to 12 modules. The lesson count follows from the ideas the subject has. Do not pad to reach a number and do not cram to stay under one.
- Each module is one coherent sub-area: orientation, then mechanics, then the part people get wrong.
- One idea per lesson. A title with "and" in it is usually two lessons.
- Each module gets `{n, title, sub, icon, accent}`. Icon keys: `book eye filter broom group sort sigma target chart spark flow cycle clock tree layers scale link atom beaker globe`. For `accent` use a tone name: `blue teal purple green amber red pink`. Vary them across modules.

Show the syllabus as module titles with lesson counts, with your assumptions on the first line. Build the first module in the same turn so there is a working course to react to, then continue. Take one round of corrections. If the user is not there to answer, carry on with the stated assumptions.

### 2. Lessons

Each lesson is one object in `LESSONS`:

- `m`: module index, from 0.
- `tag`: a short label shown above the title.
- `title`: the idea as a claim ("Bars have gaps; histograms do not"), not a topic ("Charts").
- `sub`: one sentence saying what this is and why it is here. Shown before the first beat.
- `steps`: two to four beats, each `{k:'key phrase', t:'explanation'}`. `t` may use `<b>` and `<span class="hl">`. Beat i reveals visual chunk i and shows explanation i. Write the picture and the words together.
- Titles, tags, `sub`, callouts, example labels and animation labels/captions are plain text; literal angle brackets stay visible. `steps.t` is deliberately authored HTML, not an untrusted source-text slot. Escape quoted source text before putting it inside a beat; inspect authored markup as code. Custom renderer functions and `diagram.base` SVG retain their explicit authored-code contract and require inspection too.
- Lengths that fit a phone: title up to about 70 characters, `sub` up to about 170, each beat's text up to about 150, each key phrase up to about 14. Longer text is cut off on small screens, and `render_check.py` reports every place that happens.
- `anim`: `{r:'renderer', ...params}`. Choose the renderer by the shape of the idea, using the table in the catalogue: a process is `flow`, a distinction is `compare`, a loop is `cycle`.
- `example` (optional): lines of code, a formula or a statement the animation is about. `lang:'code'` highlights it, `lang:'text'` shows it plain, `exLabel` labels the box.
- Callouts (optional, at most two per lesson): `why` (why it matters), `trap` (the common mistake), `insight` (a deeper link).
- `caveat` (only when needed): one sentence saying what in this lesson is not verified and what would confirm it, or, where the supplied material conflicts on a point that matters, both versions and which one the lesson follows. The engine shows it to the learner: a "not verified" marker in the lesson header and on the lesson card, a callout in the notes, and a count on the home page. It does not count toward the two-callout limit.

Accuracy rules:

- A confident error in a teaching tool is worse than a gap. Check each factual claim you are not sure of against the supplied material or a source you can open.
- A claim you could not check stays in the lesson with a `caveat`. The learner reads the course, not this conversation, so the doubt has to be in the course.
- If the user named an authority (a syllabus, a textbook, a standard), use its definitions and wording, because that is what they will be tested on.
- Every lesson ships complete. No placeholder text, no "to be added".

### 3. Fill the engine

1. Copy `assets/engine.html`. The copy is the course file. Leave the shipped engine as it is.
2. At the top of its script is the course data block: `COURSE`, `MODULES`, `LESSONS`. It ends at the line containing `END COURSE DATA`. Replace the demo data with yours. Leave everything below that line alone unless step 7 applies.
3. `COURSE = { title, subtitle, totalTarget?, theme? }`.
4. If one idea needs a picture none of the 16 renderers can draw, add it as `CUSTOM_RENDERERS` in the data block, following the contract in the catalogue. Do not edit the renderer table itself.
5. Deliver one self-contained `.html` file.

If the full set of lessons will not fit in one response, build in passes: the complete file with the first modules, then the remaining modules added to the same file. Say how many lessons are in the file after each pass. The course is not finished until every lesson in the syllabus is in it.

### 4. Theme and display

The engine handles this. Reusing it as shipped is the default; do not restyle it unasked.

- The reader gets a Display sheet with four themes (Paper, Mist, Dusk, Midnight), an Auto setting that follows the device, a motion setting and a reset. The choice is saved on the device when storage is available and the page works without it.
- The starting theme is Auto: light, or dark when the device asks for dark. If the user has a stated theme preference, set `COURSE.theme` to match it. Their preference decides. This skill has no opinion of its own.
- Write colours as tone names so they follow the theme. A six-digit hex is allowed and stays fixed in every theme, so use one only when a colour carries meaning that must not change.
- In a bespoke renderer, take colours from the `C` object and the CSS variables. Do not write colour literals.

### 5. Check before delivering

Read the finished data once against this list:

- Lessons are in dependency order and each uses the renderer that matches its idea.
- Every lesson has two to four beats and at most two callouts.
- The number of lessons in the file equals the number in the syllabus, or you have said what is still to come.
- Only the data block differs from `assets/engine.html`, or every other difference is an engine change recorded under step 7.

Then run whichever check the session supports and report the result as it printed:

```
node scripts/smoke.js course.html            # needs Node and the jsdom package
python3 scripts/render_check.py course.html  # needs Python, Playwright and Chromium
```

`smoke.js` opens every lesson, steps every beat, runs autoplay to the end and fails on script errors, on a drawing that does not change between beats, and on `NaN` or `undefined` in the drawing. `render_check.py` does the same in a real browser in every theme at desktop and phone size. It also measures text contrast, controls pushed off screen, pointer target sizes, colliding labels, cut-off captions and the smallest text in each drawing, and runs the course inside a scripts-only sandboxed frame.

Fix what they report. If neither can run, say "checks not run: no Node with jsdom and no Playwright here" and deliver anyway. Do not write that the course was tested.

### 6. Check where it is delivered

A course that works in a browser tab can still fail inside the frame a host shows it in. The engine is built not to depend on forms, native dialogs, popups, downloads or storage, and the sandboxed-frame run checks that. That run is a local stand-in. If you can open the delivered preview, press play, change the theme and reload there. In the reply, say which of these was done: exercised in the delivered preview, exercised in the sandboxed stand-in, or opened in a local browser only.

### 7. Changing the engine: only when asked or when a defect requires it

Two cases permit an edit below the data block:

- **The user asks for it.** Restyling beyond the four themes (their colours, a typeface, larger text) or a repair to how something displays ("the labels are cut off", "that button sits under the notch").
- **A defect requires it.** A check or the delivered preview shows a fault that course data cannot fix.

Then:

1. Change the smallest thing that does the job: a token value, one rule, one function. Edit the course copy. `assets/engine.html` stays as shipped.
2. Record it in a comment at the top of the data block, on the line under `const COURSE`: `/* ENGINE CHANGED 2026-10-09: what was changed and why. Checks rerun: ... */`. Say the same in the reply.
3. Rerun the checks the change can affect. Any edit: `smoke.js`. Colours: the contrast figures in `render_check.py`. Layout or text size: its overflow, cut-off, target-size, colliding-label and smallest-text figures. Run the whole of `render_check.py` when unsure.
4. Describe the file as a modified engine. The shipped engine's results do not carry over: report which checks were rerun on the modified file and which were not. If none could run, say the modified engine is unchecked.

A change the user did not ask for and no defect requires is not made.

## Failure branches

- **The subject is too broad to order.** Narrow it yourself to the most likely reading, say so in one line, and build that.
- **A claim cannot be checked.** Leave the lesson in, set its `caveat`, and also list it under "Not verified" in your reply with what would confirm it. Do not soften the lesson text into vagueness to hide the doubt, and do not leave the doubt out of the course.
- **The supplied material contradicts itself or a source.** Follow the named authority. When the conflict is material (it changes what the learner would do or answer), set that lesson's `caveat` to one sentence giving both versions and which one the lesson follows, so the standalone file shows it. Report it in the reply as well. A slip that changes nothing a learner would do is corrected and mentioned in the reply only.
- **A check fails and you cannot fix it.** Deliver the file with the failing output quoted and the lesson numbers affected.
- **The user asks for a different look.** A theme choice is `COURSE.theme` or the Display sheet. Anything further is an engine change: make it under step 7.
- **The user asks for a display repair.** Reproduce it if a browser is available, fix it under step 7, and report the measurement before and after. If it cannot be reproduced here, make the narrow change, say it is unchecked, and say what to look at.

## Output

1. The syllabus, with assumptions on the first line.
2. The course file.
3. A short note: the size chosen and how many lessons are in the file, which check ran and what it printed, where the course was exercised (delivered preview, sandboxed stand-in, or local browser only), the lessons carrying a caveat, any engine change with the checks rerun on it, and what is still to come if the build is in passes.

## Rules that always hold

- The delivered file makes no network requests and contains no keys.
- The engine below the data block is unchanged from `assets/engine.html` unless the user asked for a change or a defect required one. A change is recorded at the top of the data block and in the reply, the affected checks are rerun, and the file is never presented as the tested engine.
- A check that did not run is reported as not run.
- A claim that was not verified is marked in the lesson that carries it, with `caveat`, and repeated in the reply. A material conflict in the supplied material is marked the same way.
- The course is not reported as working in a host unless it was opened there. A stand-in is named as a stand-in.

## Known limits

- Drawing labels on small screens. Measured with Playwright on 9 Oct 2026: before the label edit, seven of the sixteen demo drawings drew labels at 7.2 to 8.6 pixels at 390 by 844. With it, the smallest label is 9.4 pixels at 390 by 844 in the demo and in a real 12-lesson course, with no colliding labels. Growth is capped at 1.3 times, because an uncapped floor made four labels collide in that course at 360 by 640. So at 360 by 640 a short stage can still draw labels at about 7.4 pixels (5.7 before). Desktop is unchanged at 9.5 pixels and up. Larger labels than this need the renderers redrawn, which has not been done.
- `render_check.py` measures text inside SVG drawings against the page behind the drawing, not the shape under the text.
- The sandboxed-frame run uses `sandbox="allow-scripts"`. A real host adds its own policies and may use different tokens. No host's frame was tested.
- The checks prove the file runs. They say nothing about whether a lesson teaches well. That needs a person who knows the subject.

## What has and has not been tested

Corrected on 9 Oct 2026: a narrow engine change is permitted when asked for or required by a defect, with its record and reruns; a material conflict in supplied material goes into the lesson's visible caveat; drawing labels are held near 9.5 pixels on a 390 wide screen. Not independently retested.

Run on 9 Oct 2026 on the changed engine, on Linux with Node, jsdom, Playwright and Chromium: `smoke.js` passes (16 lessons, autoplay 16 of 16, no script errors); `render_check.py` passes in six theme states at two sizes, with the sandboxed-frame run, and reports the smallest drawing text as 9.4 pixels on the phone size (7.2 before). A 12-lesson course rebuilt on the changed engine passes both checks.

Three author-run behaviour cases exist for this skill: a 12-lesson build, a "teach me" request that names no format, and a quiz request with the skill loaded. The authoring session produced the replies and scripted checks graded them. They predate this correction, and the course built for them used the engine before the label edit. There has been no independent run and no measurement of whether any host loads this skill.

Not tested: any model following step 7 or writing a conflict caveat; any real host's preview.

## Acceptance cases

Synthetic prompts and what must be observable. The full set, with negative controls, travels with the source for review.

1. "Animated lessons on how DNS resolution works. I know basic networking and want to understand it properly." Expect: no interview, a syllabus whose first line states the size chosen, a delivered file, a reply stating which check ran and where the course was exercised.
2. "Turn these notes on TCP into bite-sized animated explainers." with notes attached. Expect: lesson wording follows the notes, a size that fits seven notes (short, not 24), and any claim the notes do not support carries a `caveat` in its lesson and is listed in the reply.
3. Notes whose two lines disagree on a fact a learner would be tested on, with a named standard to follow. Expect: the lesson follows the standard, its `caveat` gives both versions and which was followed, and the reply reports the same conflict.
4. "Build the course. On my phone the caption text under the drawing is too small to read, fix that in the file you give me." Expect: a narrow engine change in the course copy, recorded at the top of the data block and in the reply, the affected checks rerun or reported as not run, and the file described as a modified engine.
5. "Teach me how public key cryptography works." Expect: an explanation in the reply and a one-line offer. No 24-lesson build.
6. Negative control: "Quiz me on the OSI layers until I stop getting them wrong." Expect: this skill is not used.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
