---
name: elicitor
description: "Builds questionnaires, intake forms, surveys and scored quizzes as one self-contained page to fill in, often on a phone, and export back as clean text. Use for build me a quiz, quiz me on these notes, ask me questions, interview me, questionnaire, intake form, feedback form, survey. Not for a full course with lessons (preceptor), analysing many collected responses (response-analyst), or a handful of questions, which are asked in chat."
metadata:
  revision: "2.1.0"
  revised-from: "elicitor as exported 8 Oct 2026"
---

# Elicitor: a questionnaire in, clean text out

The loop this skill exists for: the assistant builds a questionnaire, the user fills it in (often on a phone, away from the chat), exports the answers as text, pastes them back, and the assistant works from structured answers instead of a long exchange.

The page is a fixed engine, `assets/engine.html`. A questionnaire is a data block inside it. Building one means writing that block and nothing else.

| Mode | For | Comes back as |
|---|---|---|
| `intake` | The user's own answers, or an observer's notes on what they saw | Markdown: every question with its answer and note |
| `survey` | Other people, who are told first who is asking and why | A compact response block from each person, merged to CSV |
| `quiz` | A scored check on supplied material | A score with every missed item explained, and a text copy |

A skill is instructions plus tools. This one adds no memory and sends nothing anywhere.

## Use when

Scope first. Fewer than about ten simple items, or anything that needs back-and-forth (the next question depends on the last answer), is asked in chat with no page. Offer the page when:

- There are many structured things to ask (about ten or more), and typing the answers into chat would be slow or lossy.
- It will be filled in on a phone, later, or by someone other than the user.
- The user asks for a quiz, a questionnaire, an intake form or a survey by name.

Also use it when:

- An export from one of these pages is pasted back and has to be read.
- An existing questionnaire needs revising without breaking its old exports.

## Not this skill

| The job | Use |
|---|---|
| Fewer than about ten simple questions, or anything that needs back-and-forth | Ask in chat, with no page |
| A course with lessons and mastery gates | preceptor |
| Animated micro-lessons | percept |
| Finding the themes in many collected responses | response-analyst |
| Comparing a few options against weighted criteria | decision-board |
| A small app that keeps records between visits | pocket-app |
| Reviewing or designing an interface | interface-architect |

## Inputs

- What the answers are for: the task they feed, in one line. This decides which questions earn a place.
- Who fills it in, and where (the user on a phone, eight workshop attendees, an interviewer).
- For a quiz: the material the items are drawn from.
- For a survey: who is asking, what it is for, and what happens to the answers. These are shown to every respondent and must be true, so they come from the user, not from a guess.
- When revising: the current questionnaire (the built page or its instrument file).
- When reading answers: the pasted export.

## Tools: discover first

- **A shell with Python 3.** With it, `scripts/build_instrument.py` checks the questions and writes the page, and `scripts/parse_export.py` reads what comes back. Without it: copy `assets/engine.html`, replace the object between its two marker lines by hand, apply the error rules listed at the top of `scripts/validate_instrument.py` by reading, and say the checks were done by hand.
- **A way to hand over a file** (a file output, or a rendered page the user can save). The built page is about 110 kB; it is not pasted into chat. With no way to deliver a file, say so and ask the questions in chat in sections.
- **Python Playwright with Chromium** is needed only to run `scripts/test_engine.py` after changing the engine itself. It is not needed to build a questionnaire.
- No network, no accounts and no other skill are needed.

## Procedure

1. **Decide whether this needs a page at all.** Under about ten simple items, or questions whose next step depends on the last answer: ask in chat. Many structured items, or an explicit request for a quiz, questionnaire, form or survey: build the page. A phone, or another person filling it in, tips a borderline case towards the page. If it is still unclear, ask the short version in chat and offer the page in one line.
2. **Pick the mode** from the table above and write the purpose in one sentence: what will be done with the answers.
3. **Draft the questions** using `references/question-writing.md`. Give every question a permanent id that names what it asks (`deadline`, never `q7`). Choose the narrowest type that fits; the types and fields are in `references/modes.md`. Leave the note box on for choice questions: the reason behind an answer usually arrives there. Use `show_if` so nobody is asked what an earlier answer made pointless. Mark `required` only where the export is useless without the answer.
4. **Long questionnaire: show the list first.** Above about 20 questions, post the draft in chat as id, type and text, grouped by section, and ask for a quick yes or edits. Shorter ones are built straight away.
5. **Build.** Write the instrument as a `.json` file and run `python scripts/build_instrument.py instrument.json --engine assets/engine.html --out NAME.html`. It refuses errors and prints advisories. Read each advisory and either fix the wording or keep it for a reason you can state.
6. **Quiz: check the key.** Every option needs an explanation that says what mistake leads to it. Compute each answer where the subject allows (write a short script and run it); otherwise check each one against the supplied material. Say which was done for which items.
7. **Survey: disclosure and collection.** Put the three disclosure statements in the data block in the user's own terms and show them to the user before calling the file ready. Explain collection in two lines: each reply is saved as a text file, then `python scripts/collect_responses.py replies/*.txt --out responses.csv`. Sending the survey to people is the user's act, not the skill's.
8. **Hand over** the page with three things: what it is, how to fill it in (Back, Skip, the note box, the review screen), and what to bring back (the text from the last screen; the complete text is always in a box there, for when copying is blocked). Mention the resume code if it may be filled in over more than one sitting.
9. **When an export comes back,** run `python scripts/parse_export.py EXPORT --json` and work from that. A skipped question is skipped, not a "no"; a hidden question was never asked. Quote notes as written. If the parser reports a cut-off or inconsistent export, ask for it again and do not work from the fragment.
10. **Revising.** Keep every existing id on the same question. Give new questions new ids, raise `version`, and run `python scripts/validate_instrument.py --compare OLD NEW`. An error there means an old export would be read against the wrong question.
11. **Changing the engine** is rarely needed. If it is done, run `python scripts/test_tools.py`, `python scripts/test_engine.py` and `python scripts/test_planted.py`, and report their results.

## Failure branches

- **No shell.** Build by hand as described under Tools, and say that nothing was run.
- **No way to deliver a file.** Ask in chat, a section at a time, and say why.
- **The request is small.** Fewer than about ten simple items, or anything that needs back-and-forth, is asked in chat. Three questions about which laptop to buy are three questions in chat. Do not build a page to look thorough. A few questions the user will answer on a phone are still asked in chat, with the page offered in one line. The exceptions are a page asked for by name, which is built, and questions for someone else to fill in, where the page is offered because chat cannot reach them.
- **It belongs to a neighbour.** A course goes to preceptor; a pile of collected responses goes to response-analyst. Say so in one line and stop, or hand over if that skill is present.
- **Survey disclosure is missing.** Ask for it in one message, or build with the three statements clearly marked as drafts for the user to correct. Never invent what happens to respondents' answers.
- **The build reports errors.** Fix the instrument; do not edit the engine to get around a refusal.
- **A quiz answer cannot be verified.** Say which items rest on the supplied material alone, or cut them.
- **The user wants a personality type, a diagnosis or a percentile from the answers.** Offer what can be given honestly: the answers, and counts with their denominators under the fixed caveat. Say that a validated instrument and someone qualified to read it are a different thing from this page.
- **The questionnaire is about a person who would not know.** Decline that use. Offer a version the person fills in themselves, or a role-relevant observation form used with their knowledge.
- **More than about 60 questions.** Cut, or split into two sittings; say that answers thin out with length.
- **The export does not parse.** It was probably cut when copied. Ask for the text from the box on the last screen, or for a resume code.
- **The page says "Not saved".** It is in a frame without storage. The resume code under "Save and display" carries progress across a reload or to another device.
- **An old export is loaded into a new version.** The page asks first and lists what cannot be loaded. If ids were renumbered, nothing can fix that afterwards, which is why step 10 exists.

## Output

The first line names the method and the mode, so the user can see the skill was used: "Elicitor, intake mode: 27 questions in 4 sections."

Then, for a build: the file; how to fill it in and what to paste back; which advisories were acted on and which were kept, with the reason; for a quiz, how each key was verified; what was run (the build and its checks) and what was not (the page was not opened in the user's own app or on their phone by the assistant).

For a returned export: "Elicitor export read: 26 answered, 1 skipped, 1 hidden", then the task the answers were for. Tallies are reported as counts with denominators and the sentence the page prints with them.

## Rules that always hold

- Only the data block is edited. The engine outside it stays byte for byte as shipped.
- Question ids are permanent. A revision never renumbers, reuses or removes one.
- Choice questions keep their note box unless the user asks for it to go.
- Back, Skip and a review screen are always there. Skipped is exported as skipped.
- The complete export is always in a text box on the last screen, whatever the clipboard does.
- A survey opens with who is asking, what for, and what happens to the answers, and the page sends nothing.
- A quiz explains every option and states its scoring rule before the first item. Skipped is not counted as wrong.
- Tallies are counts with denominators, printed with the fixed caveat. No named type, diagnosis, percentile, band or grade is ever produced from answers.
- Not carried over from the earlier version of this skill, and not built on request: scoring another person's personality from an observer's ratings; "detector" items written to catch a respondent out; any questionnaire about a person who does not know it is being filled in. Role-relevant observation of behaviour, with the person's knowledge, is ordinary intake mode.
- Nothing is written to any memory system by this skill. An export is input for the task at hand. Saving something is the user's instruction to give at the time.
- Nothing the skill builds sends, publishes or contacts anyone.

## What has and has not been tested

Run on one machine in headless Chromium 141 at 390 by 844 and 1280 by 800 viewports (a viewport is not a phone). These checks are author-side: the authoring session wrote and ran them, and a second session of the same authoring team reran every one, added tests and repaired what it found. Nobody independent of that team has run them. The figures are from the second session's last run.

- `scripts/test_tools.py`: 156 of 156 cases passed (validate 95, build 7, parse 30, collect 24). Each case is a planted bad input that a tool must refuse, or its nearest valid input that it must accept.
- `scripts/test_engine.py`: 32 of 32 test runs passed: 20 tests, 12 of them at both viewport sizes. At both sizes: the intake journey (answer, note, Back and change, Skip, review, edit from review, export); a refused clipboard, stubbed in a tab and unstubbed inside a `sandbox="allow-scripts"` frame, which is a stand-in for a host and not a host; reload and resume; storage that throws; refused imports (wrong questionnaire, wrong app, newer schema, cut-off text, empty paste) with answers untouched; quiz scoring with both feedback timings and the select-all boundary; `show_if`; a 120 question instrument (median 3.7 ms to draw a question at 390 wide and 3.3 ms at 1280, slowest 26.8 ms) and a 400 question state; the export round trip for every question type and for three built questionnaires; answers that imitate export structure, in five scripts; a revision that keeps ids, loaded from an old export and from answers saved under the old version; survey mode. At 390 only: tallies, section layout, display settings, overflow at 360, 390 and 1280 wide, undo and reset, data block faults, keyboard and focus, page rules.
- `scripts/test_planted.py`: 41 of 41 planted faults were caught by the test named for each, among them the note left out of the export, ids renumbered in a revision and a skipped quiz item scored as correct.
- Three example questionnaires that travel with the source (intake with 28 questions, survey with 13, quiz with 12) were built with `scripts/build_instrument.py`, filled in through the browser and exported. Each export was read back by `scripts/parse_export.py` and matched the page's own state field by field. The quiz's 12 answer keys were recomputed with Python's `ipaddress` module.
- A second, different journey on each example at 390 by 844 (answers out of order, edits from review, notes with quotes, angle brackets, pipes, line breaks and non-Latin scripts, then loading each export back and into a revised version): 199 checks passed, in a tab and, for the intake example, in the sandboxed frame.
- Shared interface checks on the three examples: the delivery check passed in a tab and in the sandboxed frame; text contrast was measured in all four themes on 11 screens, including a validation error, quiz feedback, the result, the not-saved banner and a refused import (lowest ratio 5.40, none below the threshold); no pointer target under 44 by 44 and no sideways scroll on 180 screens at 360, 390 and 1280 wide; 193 controls on 17 screens were each tried and none did nothing.
- In the sandboxed frame the page's "Copied" was confirmed as a real copy by reading the clipboard from the outer page, in this Chromium only.
- Found by the second session and repaired: a note containing the first line of a survey response block stopped the page loading its own export back, and the summary line of `scripts/parse_export.py` gave hidden questions as 0 (each now has a test and a planted fault or case); the built examples were older than the engine and were rebuilt; one timing check failed once on a busy machine because of a single slow draw, and now judges the median and the 95th percentile and reports the slowest.
- Screenshots at 390 and 1280 wide were looked at, in the light default and one dark theme.

Not tested: any model following this skill other than the session that wrote it; any real host's preview; a real phone, a touch screen or an on-screen keyboard; any browser other than that Chromium; a screen reader; a real respondent; the acceptance cases and activation prompts against any model or host; whether the wording advisories catch the problems they are named for beyond the planted cases.

## Acceptance cases

The full set, with inputs, travels with the source for review.

1. "I want a small tool built for tracking loans of shared equipment. Ask me what you need to know, I'll answer on my phone tonight." Expect: a page, not a chat interview; intake mode; ids that name their questions; note boxes on; the question list shown first if it is long; a built file with what to paste back; a first line naming the method.
2. A pasted intake export and "what are the must-haves and what is still open?" Expect: the export parsed, the must-have list quoted as written, the skipped question reported as skipped, nothing invented for it, nothing saved to memory.
3. "Build me a 10 question quiz on IPv4 subnetting from these notes." Expect: quiz mode, every option explained, every key computed and reported as computed, the scoring rule shown, no claim that the score measures ability.
4. Negative control: "Ask me three quick questions to work out which laptop I should buy." Expect: three questions in chat and no page.

## Final continuation revision

Claude authored the received base. Codex repaired and tested this revision after Shaun instructed it to finish without Claude. Independent QA receipts remain in the task workspace; producer history above describes earlier runs, not this revision's acceptance. Installed resource equality, live routing and model behaviour are separate checks.
