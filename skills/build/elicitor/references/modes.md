# The engine: data block, modes, exports and state

`assets/engine.html` is one page with one editable part. Everything a questionnaire is, lives in its data block. This file is the contract for that block and for what the page does with it.

## 1. The data block

In the engine, between two marker lines:

```
/* ====== BEGIN INSTRUMENT DATA: ... ====== */
const INSTRUMENT = { ... };
/* ====== END INSTRUMENT DATA: ... ====== */
```

The object is strict JSON: double quotes, no trailing commas, no comments. `scripts/build_instrument.py` writes it from a `.json` file and refuses an instrument with errors. Editing it by hand is the fallback. Nothing outside the block is changed, ever; `scripts/validate_instrument.py PAGE --engine assets/engine.html` proves that for a built page.

| Field | Needed | Meaning |
|---|---|---|
| `id` | yes | Permanent name of the questionnaire, `[a-z0-9_-]+`. Saved answers and exports are tied to it |
| `version` | yes | Whole number from 1. Raise it whenever questions change |
| `mode` | yes | `intake`, `survey` or `quiz` |
| `title` | yes | One line |
| `purpose` | no | One line shown on the first screen and written into the export |
| `intro` | no | A paragraph or two for the first screen |
| `minutes` | no | The author's estimate, shown as "The author estimates about N minutes". Leave it out if it has not been tried |
| `layout` | no | `one` (default: one question a screen) or `sections` (a section a screen). The reader can switch in the page. Ignored in quiz mode |
| `notes` | no | `on` or `off`: the default for the note box. On in intake and survey, off in quiz |
| `feedback` | quiz | `immediate` (default) or `at_end`. The reader can switch on the first screen until the first answer |
| `disclosure` | survey | `who`, `purpose`, `handling` (all required), `contact` (optional) |
| `sections` | no | `[{"id": "...", "title": "...", "intro": "..."}]`. Questions name a section by id |
| `questions` | yes | The list, in the order asked |
| `tallies` | no | Named counts over tagged questions. Not in quiz mode |

### Questions

Every question has `id` (permanent, `[a-z0-9_-]+`, named for what it asks, never a bare position), `type`, and `text` (one line). Optional on any question: `section`, `help` (one line under the question), `required` (default false; a required question has no Skip), `note` (the "Anything to add?" box; default on for single, multi, likert, scale and rank, off for text and number), `note_label`, `tags` (names used by tallies), `show_if`.

| Type | Fields | Answer in the export |
|---|---|---|
| `single` | `options`: 2 to 8 | The option text |
| `multi` | `options`: 2 to 8 | A list of option texts, in the order the options are listed |
| `rank` | `options`: 2 to 8 | A numbered list. Moved with Up and Down buttons; an untouched order is not an answer until "Use this order" is pressed |
| `text` | `long`: true for a multi-line box | Quoted lines, with line breaks kept |
| `likert` | `labels`: 4 or 5, one for each point, low to high | `4 of 5, Agree` |
| `scale` | `min`, `max`, `step` (whole numbers), `min_label`, `max_label` | A whole number. Up to 11 points are buttons; more is a slider with plus and minus |
| `number` | `min`, `max`, `unit`, `integer` | A number, with the unit after it |

Options are plain text, except in quiz mode, where each is `{"text": "...", "correct": true, "explain": "..."}`. An answer is stored and exported as the option's text, so reordering options is safe and rewording one makes old answers to it unreadable.

### show_if

`"show_if": {"q": "earlier-id", TEST}` with exactly one test:

| Test | Works on | Shown when |
|---|---|---|
| `"equals": value` | single (an option text), likert, scale, number, text | the earlier answer is exactly that value |
| `"includes": "option text"` | multi | that option is among those ticked |
| `"answered": true` (or `false`) | any | the earlier question has (or has not) an answer |

The question read must come earlier in the list. A hidden question is passed over, is not on the review screen, and is absent from the export (a response block marks it `HIDDEN`). If the question it depends on is itself hidden, it stays hidden. Its answer is kept in the page and comes back if it is shown again.

## 2. The three modes

### intake: the paste-back loop

No right answers. The respondent is the user, or an observer recording what they saw. The last screen shows the full markdown export; the user pastes it into the chat.

First screen: title, purpose, length, where answers are kept, how it works. Then questions with Back, Skip and Next; a review screen where any answer can be changed; Finish.

Role-relevant observation forms are intake mode filled in by the observer: an interview scorecard against stated job criteria, notes from a usability session. They record what was done and said, by someone who knows they are being assessed. See "Rules that always hold" in SKILL.md for what is refused.

### survey: for other people to fill in knowingly

The first screen is a disclosure, built from the data block and required:

| Shown as | From | Write it as |
|---|---|---|
| Who is asking | `disclosure.who` | The role or name the respondent knows the asker by |
| What it is for | `disclosure.purpose` | The decision the answers will feed |
| What happens to your answers | `disclosure.handling` | Who reads them, where they are kept, whether names are attached, when they are deleted. It must be true |
| Questions about this | `disclosure.contact` | Optional |

The page adds a line of its own: it sends nothing; at the end it shows the answers as a block of text and the respondent decides whether to send it. The Start button reads "I have read this. Start". An instrument in survey mode with any of the three fields missing does not open, and the validator refuses it.

The last screen shows a compact response block. The respondent copies it and sends it to the asker by whatever channel the asker named. Collecting several:

1. Save each reply as a text file, one respondent per file (the surrounding message can stay; only the block is read).
2. Run `python scripts/collect_responses.py replies/*.txt --out responses.csv`.
3. One row per respondent, one column per question id, a `.note` column after any question with a note. A block from another instrument or version is refused and named, and nothing is written.

The block carries no name. Rows are named after their files. If answers must be anonymous, the asker removes the file names before sharing the CSV; if they must be attributable, the asker keeps them. Say which in `handling`.

### quiz: a scored check on supplied material

Every item is `single` or `multi`. Every option has an explanation. `single` has exactly one correct option; `multi` has one or more.

Scoring contract, printed on the first screen and under the score, in these words:

> One mark per item. An item is correct only when the answer matches exactly; a select-all item needs every correct option and no others. Skipped items earn no mark and are reported separately, so the result gives correct out of attempted and correct out of all items.

- Attempted: items with an answer. Skipped: items passed with Skip. Not answered: items never reached. Total: items shown.
- The score screen shows "N correct of M attempted", then N of the total, the skipped count marked "not counted as wrong", and the not-answered count.
- Missed items (answered and wrong) are listed with the explanation of every option, the chosen and the correct ones labelled in words. Skipped and unanswered items are listed separately with the same explanations.
- `immediate`: the main button reads "Check answer"; the item locks and shows its explanations; then "Next". `at_end`: nothing is marked until Finish, and answers can be changed until then.
- There is no partial credit, no weighting, no pass mark, no grade and no percentage.

A score is a count of these items answered correctly on one attempt. The page never presents it as a measure of ability.

## 3. Tallies (intake and survey)

```
"tallies": [{"id": "habits", "label": "Habits that apply", "tag": "habit", "when": {"equals": "Yes"}}]
```

A tally counts the shown questions carrying `tag` whose answer passes `when`: `equals`, `includes`, `at_least`, `at_most`, or `answered` (the default when `when` is left out). The page prints the label, the count and its denominator ("6 of 10"), adds how many were answered when that is fewer than the denominator, and always prints beneath:

> These totals are counts of your answers. They are not a validated measure of anything.

No tally is turned into a percentage, a band, a named type, a diagnosis or a percentile, in the page or in the reply that uses the export.

## 4. Export formats

### Markdown export (intake, and quiz with results)

Real output of the demo instrument that ships in the engine:

```text
# Demo: choosing a place for a shared lunch

Instrument: demo-shared-lunch, version 1, intake mode
Finished: 2026-10-08T16:38:23Z
Purpose: A short sample that shows every question type. Replace this data block with your own.
Questions shown: 9. Answered: 8. Skipped: 1. No answer: 0. Hidden by earlier answers: 0.

## Section: Who is coming

### [group-size] How many people will be at the table?
Type: number, people
Answer: 6 people

### [day] Which day suits most of the group?
Type: single
Answer: Saturday
Note:
> Only after 1 pm.

### [needs] Which of these does someone in the group need?
Type: multi
Answer:
- Vegetarian dishes
- Step-free access

### [needs-detail] What should the venue be told about the step-free access needed?
Type: text
Answer:
> One wheelchair user.
> Is there a ramp at the side door?

## Section: Food and place

### [walk] How far is the group willing to walk from the meeting point?
Type: scale, 0 to 10 (0: Next door only; 10: A long walk is fine)
Answer: 4

### [noise] A lively, noisy room would be fine for this lunch.
Type: likert, 5 points (1: Strongly disagree; 5: Strongly agree)
Answer: 2 of 5, Disagree

### [sharing] Ordering dishes to share would be fine for this lunch.
Type: likert, 4 points (1: Strongly disagree; 4: Strongly agree)
Answer: 4 of 4, Strongly agree

### [priorities] Put these in order, most important first.
Type: rank
Answer:
1. Travel time
2. Price
3. Range of dishes
4. Being able to book

### [ideas] Name one place you would be happy with.
Type: text
Answer: (skipped)

## Tallies

- [relaxed-agreed] Statements about a relaxed lunch rated 3 or above: 1 of 2 (answered: 2)
These totals are counts of your answers. They are not a validated measure of anything.

End of export: 9 questions.
```

Rules of the format, which `scripts/parse_export.py` relies on:

- Every shown question has a block: the heading with its id in square brackets and its text, a `Type:` line, an `Answer`, and a `Note:` when one was written.
- `Answer: (skipped)` means Skip was pressed. `Answer: (no answer)` means the question was never answered or skipped (possible when Finish is reached through the review screen).
- Typed text and notes are quoted line by line with `> `, so a line break or a blank line inside an answer survives. Trailing spaces on a line and blank lines at either end are dropped; nothing else is changed.
- The header counts and the last line let a reader detect a paste that was cut short.
- Nothing a person types can be taken for structure. Typed text and notes sit on quoted lines, option texts are single lines, and a response block keeps each value inside one JSON string. So an answer that contains `### [id]`, `Answer:`, `End of export:` or the first line of a response block is read back as the text it is, by `scripts/parse_export.py` and by the page's own import.

In quiz mode each block also has `Result:` (correct, incorrect, skipped, no answer) and, unless correct, `Correct answer:`; the export ends with a Score section. An excerpt from the real output of a six-item test quiz (two of its blocks, then its end):

```text
### [even-numbers] Which of these numbers are even?
Type: multi
Answer:
- 21
- 49
Result: incorrect
Correct answer:
- 14
- 36

### [multiples-of-three] Which of these are multiples of 3?
Type: multi
Answer: (skipped)
Result: skipped
Correct answer:
- 12
- 27
- 33

## Score

Correct: 4
Attempted: 5
Total: 6
Skipped: 1
No answer: 0
Rule: One mark per item. An item is correct only when the answer matches exactly; a select-all item needs every correct option and no others. Skipped items earn no mark and are reported separately, so the result gives correct out of attempted and correct out of all items.

End of export: 6 questions.
```

### Response block (survey)

Real output of a six-question test survey, filled in by the test driver (hence the odd notes):

```text
=== elicitor response ===
instrument: fixture-survey
version: 1
finished: 2026-10-08T16:25:54Z
useful = 1
useful.note = "Note on useful: \"quoted\", 100% & <tag>?\nSecond line of the note."
pace = "About right"
pace-where = HIDDEN
kept = ["The group exercise","The questions at the end"]
kept.note = "Note on kept: \"quoted\", 100% & <tag>?\nSecond line of the note."
recommend = SKIPPED
one-change = "Text for one-change: 50% sure & <not> certain.\n\n  An indented second paragraph.\nThird line."
tally:rated-high = [0,2]
=== end elicitor response: 6 questions, 2 notes ===
```

One line per question id, every question listed. A value is JSON (text in double quotes with `\n` for a line break, a number, or a list of option texts) or one of `SKIPPED`, `HIDDEN` (not shown because of an earlier answer) and `NONE` (shown, never answered). The closing line states how many questions and notes the block holds, so a block that lost a line is refused. There is no question text in the block: the asker has the instrument.

## 5. State: saving, resume codes, import

| Behaviour | What the page does |
|---|---|
| Where answers are kept | Tried in order: a host storage object (`window.storage` with async `get` and `set`), `localStorage`, memory. Every access is inside a try |
| What it says | "Saved by the app that is showing this page." or "Saved in this browser." or, as a banner on every screen, "Not saved: this page cannot store data here. Get a resume code to keep your work." |
| Autosave | After each change, a moment later, without blocking. A reload returns to the same question |
| Resume code | "Save and display", then "Get a resume code": the saved state as one line of JSON in a text box, with Copy and Download. Pasted into the same questionnaire on any device, it restores every answer, note and the place reached |
| Import | "Continue from a code or export" takes pasted text or a chosen file: a resume code, a finished markdown export, or a response block. It is checked before anything changes |
| Refused, with answers untouched | Empty text; text that is not complete JSON; a code from another app; a schema newer than the page reads, or not a whole number; a code or export for another questionnaire; answers that do not fit the questions; a cut-off export |
| Asked first | A code or export from another version of the same questionnaire: the page says which versions, how many answers match and which cannot be loaded, and waits. Keeping the current answers is the default |
| Answers saved under another version | When the page opens and finds answers saved in this browser under another version of the same questionnaire, it starts fresh, says so, and puts the old saved code in the import box. "Load it" then asks first, as above. The old saved code is replaced once a question is answered or skipped |
| Undo | After a load, a reset, or a Skip that removed an answer, the status line offers Undo |
| Start again | Confirmed in the page. It states how many answers, skip marks and notes will be cleared, and offers a resume code first |

The envelope, with most answers left out:

```json
{"app": "elicitor", "schema": 1, "content_id": "demo-shared-lunch@1", "saved_at": "2026-10-08T16:38:23Z",
 "data": {"stage": "q", "cur": "walk", "feedback": "immediate", "agreed": false, "finished_at": null,
          "answers": {"group-size": {"v": 6}, "day": {"v": "Saturday", "note": "Only after 1 pm."}, "ideas": {"skipped": true}}}}
```

`content_id` is the instrument id and version. Schema 1 is the first, so there is nothing to migrate from yet; a later schema adds an explicit step to the engine's `MIGRATE` table.

Loading a finished export puts the answers back and opens the review screen (a finished quiz opens at its result), so answers can be changed later and exported again.

## 6. Display choices

"Save and display" also holds: theme (Paper, the warm light default; Slate; Dusk; Ink), text size (Standard, Large, Larger), spacing (Comfortable, Compact), movement (On, Off; off by default when the device asks for reduced motion), and questions (one at a time, or a section at a time; not in quiz mode). Each applies at once, shows as selected, is kept when storage works, and "Reset display" returns all of them to their defaults. Without storage the page says the choices last for the visit.

## 7. What the page does not do

It makes no network request, loads nothing from outside the file, sends answers nowhere, and keeps no record beyond the storage named above. It has no accounts and no timer. It cannot stop a respondent reading the data block of a quiz, so a quiz is for practice, not for examination.
