# Example: IPv4 subnetting primer

A complete course made by following this skill's procedure once, on an invented learner. **Made by the sessions that wrote the skill, not by an independent run.** Nobody else has built a course with this skill yet.

| File | What it is |
|---|---|
| `ipv4-subnetting-primer.html` | The built course: one self-contained page. Open it in a browser. Five modules, a branching prerequisite graph (module 2 opens modules 3 and 4; module 5 needs both), 15 objectives, 31 practice items, 30 gate items, 6 worked examples at three levels, 10 interactive visuals covering all six visual types, 47 cards, one applied challenge |
| `ipv4-interview-and-map.md` | The interview and the course map as carried out for this course, with a SYNTHETIC learner |
| `verify_course_answers.py` | Recomputes the course's numeric answers with Python's `ipaddress` module |

The inputs are the course data and the custom renderer, which ship in the skill as `assets/sample-course-ipv4.json` and `assets/sample-renderers-ipv4.js` so that a model building a new course can read them. The page was built from those two files and `assets/engine.html` by `scripts/build_course.py`.

## Why this subject

Its answers can be computed. Every address, mask, count and binary value the learner is marked against can be recomputed by a trusted library, so the claim "the answers are right" rests on a run and not on proofreading. A subject whose answers cannot be computed needs sources in the course and a careful read instead; the skill says so.

## What was checked, and by what

From the skill folder, on 9 Oct 2026:

```
python scripts/validate_course.py examples/ipv4-subnetting-primer.html
  RESULT: PASS. 0 error(s), 0 advisory note(s).

python examples/verify_course_answers.py examples/ipv4-subnetting-primer.html
  RESULT: PASS. 532 value(s) recomputed, 0 error(s). Left for a person to read: 13 block(s) and 192 other statement(s) that contain digits.

python examples/verify_course_answers.py examples/ipv4-subnetting-primer.html --selftest
  RESULT: PASS. 23 of 23 checks passed.
```

What "recomputed" covers: the correct option of every numeric item (and that no other option states the same value), every blank, typed answer and challenge task, every numeric result in a worked step, every numeric card, every fact in a compare visual, every slider, number-line and table formula across every setting its control can take (5,441 settings), every step-by-step grid row, and 187 statements found by pattern in the prose (sums, powers of two, binary values, block sizes, host counts, and explanations that say what a wrong option is).

What it does not cover: 13 theory, cheat-sheet and brief blocks and 192 other statements that contain digits (99 option explanations, 63 worked-step texts and hints, 17 definitions, objectives and summaries, 13 captions and prompts). No check or pattern recomputes those. `--list` prints each one. The finishing session read all of them against hand arithmetic and found no error; that reading is not a script and has not been repeated by anyone else. Two blocks cite a source in the page (RFC 3021 and RFC 1878) and are not recomputed.

The self-test plants 22 faults one at a time (a wrong option marked correct, a wrong blank, a wrong card, a wrong formula, a false sum, a false explanation of a wrong option, a wrong remainder in a caption, a check removed, and so on) and confirms each is reported.

The page's behaviour (gates, fading, per-option feedback, the review schedule, backup and import, planned modules, themes) is tested by `scripts/test_engine.py`, which builds the same page from the same inputs.

## Regenerate

```
python scripts/build_course.py assets/engine.html assets/sample-course-ipv4.json examples/ipv4-subnetting-primer.html --renderers assets/sample-renderers-ipv4.js
python scripts/build_course.py --extract examples/ipv4-subnetting-primer.html course.json
```

The first command rebuilds the page byte for byte. The second writes the course data found in the page back out as JSON.

## Limits

- The page has been opened in a local Chromium tab and in a local `sandbox="allow-scripts"` frame. It has not been opened in any product's preview.
- The content was written from knowledge and then recomputed. Recomputing shows the numbers are right; it does not show the explanations teach well. No learner has used it.
- /31 and /32 prefixes and variable-length subnetting are outside the course, and the course says so.
