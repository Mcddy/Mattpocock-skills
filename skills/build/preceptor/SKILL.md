---
name: preceptor
description: "Builds a self-contained educational app with prerequisite gates, worked examples, interactive visuals, assessed practice, spaced review and progress backup. Use for courses, curricula and study apps; use Elicitor for standalone quizzes or Percept for animated explanations."
metadata:
  revision: "2.1.0"
  revised-from: "preceptor as exported 8 Oct 2026"
---

# Preceptor: a mastery course in one file

Use the learner's brief, resolve only consequential gaps, design a prerequisite-gated course, write every module's content, and build it into one self-contained page. The page is `assets/engine.html` with one data block replaced; everything else in it is fixed and tested. No model runs in the page: the reasoning is spent once, at build time.

What the page gives is a structure in which mastery can be demonstrated: gates that must be passed, dated evidence, and a review schedule. It does not make anyone learn, and this skill never says it does.

| Size | Modules | Use when |
|---|---|---|
| `primer` | 4 to 6 | One skill or one tight topic |
| `course` | 10 to 14 | A subject area to working competence |
| `full` | 24 to 30 | Professional depth; built in passes, unwritten modules marked `planned` |

## Use when

- The user wants to learn a body of knowledge that has internal dependencies and will come back to it over days or weeks: "teach me", "build me a course on", "I want to learn", "study app for", "curriculum for", "help me master".
- A course built with this skill needs its next pass of modules, or a revision that must not orphan saved progress.
- **Not** when the request is small. "Explain X", "what is X" and "quiz me on this page" get a plain answer or a neighbouring skill. A small request does not get a course.

## Not this skill

| The job | Use |
|---|---|
| One explanation | answer in the reply |
| One concept made visual and interactive | learning-visualiser |
| A short set of animated micro-lessons | percept |
| A standalone quiz, test, survey or questionnaire | elicitor |
| A simulation with adjustable parameters | simforge |
| An explorable map of how ideas connect | atlas |
| A general app, tracker or tool | forge |
| Review or restyle of an interface | interface-architect |

## Inputs

- The subject, and any syllabus or notes the course must follow.
- The interview answers: subject, level (checked with one diagnostic question), goal, depth, pace, anchor domain for analogies, must-include and must-exclude, notation tolerance. Each has a default, so "go" is a complete answer.
- For a later pass or a revision: the existing course page or its JSON.

## Tools: discover first

- **A shell with Python 3.8 or later**, for `scripts/validate_course.py`, `scripts/build_course.py` and `scripts/sm2.py`. Without one: write the course object by hand between the two COURSE DATA markers in a copy of `assets/engine.html`, check it against `references/data-format.md` by reading, and say the course was assembled by hand and not validated by script.
- **File output or an artifact surface** to deliver the page. Without one: deliver the course JSON and the build command.
- **Search and page reading**, for subject claims that cannot be computed. Without them: omit unsupported claims. Conditional teaching examples must state their assumptions visibly in the lesson and feedback; never grade an unchecked factual claim as established.
- **A library that can compute the subject's answers** (for subnetting, Python's `ipaddress`). Without one: recompute by hand and say it was done by hand.
- **A browser tool**, to open the built page once. Without one: say the page was built and not opened.
- Node and Python Playwright are needed only for `scripts/test_logic.py` and `scripts/test_engine.py`, which matter only when the engine itself is changed. Without them those scripts print NOT RUN and exit 3.

Do not read `assets/engine.html` or the sample course in full; they are large. Read one module of the sample, and let the build script handle the engine.

## Procedure

1. **Decide whether it is a course.** Use the table in `references/course-design.md` section 1. If the subject fits one sitting, answer it plainly, or name the neighbour, and stop.
2. **Resolve only consequential gaps.** Use the brief directly when it specifies the learner, goal, scope and pace. Offer one diagnostic exercise when level is uncertain, or include it as the first lesson so building can proceed. For an open-ended request, ask a compact menu with defaults; do not force a questionnaire when the user says to proceed.
3. **Choose the size** and state it with its reason in one line. Take the smallest size that reaches the stated depth.
4. **Show the course map on one screen**: modules, prerequisites and the reason for the size. Proceed when the brief authorises the build. Ask for a correction only when a consequential scope choice remains unresolved.
5. **Write the course as one JSON file**, following `references/data-format.md`. Read one module of `assets/sample-course-ipv4.json` first, for the standard. Every written module has: two to four objectives with Bloom levels; theory for each objective; at least one visual the learner can change (`steps`, `slider`, `compare`, `number-line`, `table-builder`, or `custom` with a small renderer); a worked example at three levels (full, partial with blanks, independent with the solution hidden); six or more practice items and a gate with two or more items per objective, written to `references/item-writing.md`, every option explained; a cheat sheet; eight or more cards; and, in later modules, an applied challenge. Voice: a strict, precise teacher. Define terms exactly and state assumptions.
6. **For a `full` course, build in passes.** Declare every module with its prerequisites; write the first tier completely; give the rest `"status": "planned"` with a title and prerequisites only. Never write placeholder text.
7. **Verify what the course says** (`references/course-design.md` section 10). Compute every answer that can be computed: put a `check` beside it, copy `assets/verifier-template.py`, add the subject's operations, run it. Look up what cannot be computed and put the source in the block. Leave out what can be neither computed nor sourced.
8. **Validate**: `python scripts/validate_course.py course.json`. Fix every ERROR. Read every ADVISORY and either act on it or say why not.
9. **Build**: `python scripts/build_course.py assets/engine.html course.json out.html`, adding `--renderers file.js` if a `custom` visual is used. The script refuses to write a course that has errors.
10. **Open the page once** if a browser tool exists: the map shows locked modules, the first module opens, a visual responds.
11. **Deliver** the page, then a short orientation: where to start; that a module opens when the gates of the modules it rests on are passed (pass mark 80 percent unless changed); the four review buttons and what each records (Again = 1, Hard = 3, Good = 4, Easy = 5 on the SM-2 scale); that mastery and activity are counted separately; how to back up. Then the verification statement: which answers were recomputed or sourced, and which illustrative examples rely on explicit visible assumptions.
12. **Later passes and revisions.** `python scripts/build_course.py --extract page.html course.json`, edit, raise `version`, run `python scripts/validate_course.py --compare old.json new.json`, rebuild. Tell the learner to export a backup first. The new page maps old progress by module, objective and card id and lists anything unmatched.

The review schedule is fixed by the engine and stated in `references/scheduling.md`. `python scripts/sm2.py --trace "5,4,2,3,5"` prints the interval and E-Factor after each grade, for answering questions about it.

## Failure branches

- **The request is too small.** "Explain X" or "quiz me on this" is answered in the reply or handed to elicitor's quiz or to percept. Say in one line that a course would be padding.
- **It belongs to a neighbour.** Name the skill from the table and stop. Do not build a course around a quiz, a simulation or a single explainer.
- **No shell.** Assemble by hand as described under Tools, and say so. Do not claim the course was validated.
- **The user will not be interviewed.** Build on the brief and stated defaults. Include a short diagnostic in the course with a foundations path; do not hold the build for another reply.
- **The answers cannot be computed and no source can be read.** Omit the unsupported factual claim. An illustrative conditional example must show its assumptions in both teaching and feedback, and must not be presented as verified fact.
- **The course does not fit one reply.** Build in passes. Say which modules are written and which are planned.
- **The validator reports errors that cannot be fixed now.** Do not ship. `--allow-errors` exists for building test pages, not for delivery.
- **The subject's competence is not shown by multiple choice or typed answers** (writing, a physical skill, judgement under pressure). Say what the gates can and cannot show, build the knowledge part, and make the applied challenge a task the learner checks against a worked standard.
- **Medical, legal or safety subjects.** The course is a study aid. Source every rule in the page and say what a qualified authority must confirm.
- **The host page cannot store data.** The course says "Not saved" in its footer and still works. Tell the user to export a backup before closing it.
- **The user wants a tutor that answers questions inside the app.** Not available: no model runs in the page.
- **This skill's own ways of going wrong:** padding the module count to fit a size; a straight line of modules drawn as a graph; a visual that only decorates; distractors nobody would choose; the correct option always in one position or always the longest; activity points presented as competence; changing ids without raising the version; saying the app teaches to mastery.

## Output

The first line of each reply names the method and the stage, for example "Preceptor course build: interview" or "Preceptor course build: primer, 5 modules, delivered".

- Discovery reply when needed: only missing consequential choices, with defaults. A complete build brief proceeds directly; a diagnostic can be included in the first lesson.
- Map reply: size and reason, the module table, what was left out.
- Delivery: the single HTML page, the course JSON (and renderer file if any), the orientation, the verification statement, and for a `full` course the list of modules not yet written.

## Rules that always hold

- A module shown as content is completely written. A `planned` module is drawn as not yet written, cannot be opened and is left out of every total. No placeholder text, ever.
- The prerequisite graph is real: a module stays locked until the gate of every module it rests on is passed, and the map shows what unlocks what.
- A failed gate names the weak objective and links to that objective's material, not to the whole module.
- Every quiz and gate option has its own explanation. Exactly one option is correct.
- Mastery comes only from gate results; card recall keeps that evidence current. Activity (parts read, items tried, cards reviewed, days active) is counted and labelled separately and never raises mastery. A level is never presented as competence.
- Nothing decays silently. Evidence is shown with its date, and an objective with no evidence for `check_after_days` (default 30) is listed as due for a check.
- The review schedule is SM-2 as published: E-Factor starts at 2.5; I(1) = 1, I(2) = 6, then I(n) = I(n-1) * EF rounded up; EF changes by 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02) with a floor of 1.3; a grade below 3 restarts the card at 1 day and leaves the E-Factor unchanged; a card graded below 4 returns in the same session. Due dates are whole local calendar days; a clock moved backwards un-dues nothing.
- A refused import leaves existing progress exactly as it was. A backup from another course, a newer format or damaged text is refused with the reason.
- One file, no network requests, no live model.
- Subject claims are computed, sourced or left out, and the delivery note says which.
- This skill is instructions and tools. It adds no memory and no background process; the page does not remind anyone to study.

## What has and has not been tested

Run in the authoring sessions, 9 Oct 2026, locally (Python 3.13, Node 22, Chromium through Playwright):

- `scripts/sm2.py --selftest`: 11 of 11, including six hand-worked sequences (33 steps) and four planted wrong schedules, each caught. The algorithm text was re-read at its source that day.
- `scripts/test_logic.py`: 14 of 14. The page's JavaScript schedule equals `sm2.py` on 9,330 grade sequences of length 1 to 5 and 300 random sequences of length 40; dates, formulas, the gate rule and backup validation agree; five planted faults caught.
- `scripts/validate_course.py --selftest`: 49 of 49 planted faults and valid neighbours. A course file with a prerequisite cycle is refused by the validator and by the build script.
- `scripts/test_engine.py`: 28 of 28 runs (14 tests at 390 by 844 and 1280 by 800) on the sample IPv4 course, and again on the built page with `--page`: gates and remediation, fading, per-option feedback, the schedule against `sm2.py --trace`, reload and backup round trip, eleven refused imports with stored progress byte-identical, mastery against activity, due for a check at 30 days and not at 29, planned modules, four themes and three settings, a 28-module course with 280 card schedules, layout at 360, 390 and 1280 wide, a sandboxed frame, a host storage object, all six visual types.
- `scripts/test_engine.py --mutants`: 20 of 20 deliberately broken engines caught by the named test, among them a failed gate that still unlocks, a lapse that changes the E-Factor and a refused import that wipes progress.
- `assets/verifier-template.py --selftest`: 6 of 6, five planted faults caught.
- The sample course: 532 values recomputed with Python's `ipaddress`, 0 errors; 22 planted wrong values each caught. A further 205 blocks and statements containing digits were read by the session, not recomputed.
- On the built sample page, with the shared interface tools: an 82-step journey passed in a tab and in a `sandbox="allow-scripts"` frame at two widths; text contrast measured in all four themes with a wrong answer, a failed gate, a refused import and a review card showing, lowest ratio 4.85 to 1, and a planted low-contrast copy failed; all 14 pointer targets on the opening screen at 390 wide meet 24 by 24; none of the ten controls on the opening screen is dead. A scratch sweep of twelve screens at 390 wide found none of 250 controls under 44 by 44 pixels. Screenshots at 390 and 1280 wide were looked at.

Not tested: any model following this skill other than the session that wrote it; any real host's preview; a learner using a course; screen reader use; a `course` or `full` size course with real content (the 28-module test course is made-up filler); any subject other than IPv4 subnetting and the built-in percentages demo; whether courses built this way teach well.

## Acceptance cases

The full set travels with the source for review.

1. "Teach me IPv4 subnetting", with a brief that already states goal, pace and exclusions. Expect: the method named in the first line; one diagnostic question and no repeat of what the brief gave; a primer map with a branching prerequisite graph and a one-line reason for the size; a validated, built single page; a statement of which answers were recomputed.
2. A course file whose second and third modules each require the other, with "build it". Expect: the validator's cycle error naming both modules, no page delivered, a specific fix proposed.
3. Old and new versions of a course in which an objective id was renamed and the version not raised, with "is it safe to ship?". Expect: `--compare` run, the id named, the answer no, and both remedies offered.
4. Negative control: "Explain what a subnet mask is in two paragraphs." Expect: two paragraphs in the reply. No interview, no map, no app.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
