# Writing the questions

The page is fixed. The questions are the work. This file holds the item-writing rules for both kinds of instrument: questions that gather (intake and survey modes) and items that test (quiz mode). Each rule has a bad example and a better one.

Basis for this file. ASSESSMENT, moderate confidence: these are standard conventions of survey design and test-item writing as the author knows them; no source was fetched while writing it, so none is cited. GAP: the limit of about 60 questions is a working figure carried over from the earlier version of this skill, not a measured threshold. Treat every rule as a default to argue with, not a law.

`scripts/validate_instrument.py` points at some of these as advisories (two things in one question, leading openers, absolutes, overlapping ranges, bunched or over-long quiz options, length). It cannot judge wording. An advisory is a prompt to reread the item; a clean run does not mean the questions are good.

## Before writing any question

1. **Say what each answer will be used for.** If no decision or next step depends on an answer, cut the question. A questionnaire is paid for in the respondent's attention.
2. **Do not ask what can be looked up or is already known.** Put known facts in the intro and ask whether they are still right.
3. **Give every question a permanent id that names what it asks** (`deadline`, `user-count`), never its position (`q7`). Revisions add ids; they never renumber or reuse one. Old exports stay readable only if ids keep their meaning.

## Questions that gather

### 1. Concrete and recent beats abstract and general

- Bad: "How is your focus lately?"
- Better: "On how many of the last five working days did you get two unbroken hours?" (number, 0 to 5)

People answer the abstract version with their self-image. They answer the concrete one from memory.

### 2. One thing per question

- Bad: "Is the tool fast and easy to use?"
- Better: two questions, "How fast does the tool feel?" and "How easy was it to find what you needed?"

If the two halves can have different answers, a single answer is unreadable. The validator flags " and " and " or " in single-answer questions as candidates. Many are fine ("Laptop or desktop" as one device class); decide each.

### 3. No push towards an answer

- Bad: "Don't you agree the new layout is clearer?"
- Bad, more quietly: "How much has the new layout improved things?"
- Better: "Compared with the old layout, the new one is" with options from "Much harder to read" to "Much easier to read"

The second bad example presumes an improvement. Ask in a way that lets the unwelcome answer be given as easily as the welcome one.

### 4. The whole range of answers, including the unflattering end

- Bad: "How often do you back up your work?" with "Daily", "Weekly", "Monthly"
- Better: add "A few times a year", "Never" and "I do not know"

On anything a person could feel judged for (money, habits, mistakes, conflict), people choose the nearest acceptable option. If the honest answer is not on the list, the data is wrong and nothing shows it.

### 5. Options that do not overlap and leave no gap

- Bad: "1-5", "5-10", "10+" (where does 5 go, and 10?)
- Better: "1 to 5", "6 to 10", "More than 10"
- Also bad: a list of causes with no "Something else" and no "Not sure"

A single-answer list must have exactly one right place for every respondent. Add "None of these" to a tick-all list so that an empty answer and "none apply" can be told apart.

### 6. No absolutes in statements to rate

- Bad: "I always test my changes before sharing them." (agree or disagree)
- Better: "Of the last ten changes I shared, I tested" with "All ten", "Most", "About half", "Few", "None"

Most people read "always" and "never" as direction, not literally, so agreement cannot be interpreted. Ask for the frequency directly.

### 7. Scales with every point labelled, in one direction

- Bad: a 1 to 5 scale with only "bad" and "good" at the ends, and the next question reversed
- Better: five labelled points, low to high, the same way round throughout

Use four points when the respondent should lean one way; use five when "neither" is a real position. For a number scale, label both ends in words, since "7" means nothing by itself.

### 8. State the time frame and the unit

- Bad: "How much do you spend on software?"
- Better: "Roughly how much do you spend on software subscriptions in a month?" with the currency as the unit

### 9. Plain words the respondent uses

- Bad: "Rate the discoverability of the information architecture."
- Better: "How easy was it to find the page you were looking for?"

If a term must be used, define it in the help line.

### 10. No negatives stacked on negatives

- Bad: "Do you disagree that the session should not be shortened?"
- Better: "Should the session be shorter, the same length or longer?"

### 11. Behaviour that was seen, not character

This applies to role-relevant observation forms (an interview scorecard against stated job criteria, notes from a usability session), filled in by the observer about what happened, with the person aware that they are being assessed.

- Bad: "Is the candidate confident?"
- Better: "When the candidate did not know an answer, what did they do?" with "Said so and reasoned aloud", "Said so and stopped", "Guessed without saying it was a guess", "Changed the subject", "Did not come up"

Record what was done and said. Do not rate personality, and do not build a form about a person who does not know it exists.

### 12. Free text where choices cannot reach, and a note box everywhere else

Typing on a phone is slow, so a questionnaire that is mostly free text gets short answers or none. Use choices for what can be listed, keep one or two free-text questions per section for what cannot, and leave the note box on for every choice question. The note is where the reason, the exception and the "it depends" go, and it is often the most useful part of the export.

### 13. Order and length

Easy and factual first; anything sensitive after the respondent has warmed up; group questions into sections of one topic. Use `show_if` so that nobody is asked a question their earlier answer has made pointless. Mark a question `required` only when the export is useless without it. Say on the first screen how long it takes. Past about 60 questions, cut or split into two sittings.

## Items that test (quiz mode)

### 1. One item, one idea, and a stem that can be answered with the options covered

- Bad: "Subnetting:" followed by four unrelated statements
- Better: "A host has the address 192.168.10.77/26. What is the network address of its subnet?"

A reader who knows the material should be able to produce the answer before looking at the options.

### 2. Exactly one defensible answer, and it has been checked

- Bad: "Which mask is best for a small office?" (best by what measure?)
- Better: "A subnet must hold 50 hosts. Which is the longest prefix that fits them?"

Compute the key where the subject allows it (arithmetic, addresses, dates, code output). Where it cannot be computed, check it against the supplied material and say which was done. An answer key that was typed from memory is a draft.

### 3. Every wrong option is a specific mistake

- Bad distractors for "How many usable hosts in a /27?": "7", "1,000", "banana"
- Better: "32" (forgot to remove the network and broadcast addresses), "62" (used /26), "14" (used /28)

A distractor nobody would choose teaches nothing and makes the item easier than it looks. Each one should be what a particular misunderstanding produces, and its explanation should name that misunderstanding.

### 4. Options alike in form and length

- Bad: three options of two words and a correct one of twenty
- Better: all four the same kind of thing, about the same length

Length, grammar that only fits one option, and repeated words from the stem all give the answer away. The validator flags an option much longer than the rest.

### 5. No "all of the above", no "none of the above"

They test how the list is read more than what is known. If several options are right, make it a select-all item and say that it is marked all or nothing.

### 6. Put options in a natural order and let the key fall where it falls

Numbers ascending, addresses ascending, dates in order. Then look at where the correct answers landed. If more than half sit in one position, reorder a few items; the validator counts this for single-answer items.

### 7. Explain every option

- Bad: "Incorrect."
- Better: "62 is the usable count for a /26, which has 6 host bits."

The explanation of a wrong option says what it is the answer to, or which step went wrong. The explanation of the right one shows the working. Feedback is where a quiz teaches; the engine refuses a quiz with any option left unexplained.

### 8. No negatives in the stem unless the negative is the point

- Bad: "Which of these is not an invalid host address?"
- Better: "Which of these can be assigned to a host?"

### 9. Items do not answer each other

Read the quiz as one piece. If the stem of item 7 states the fact that item 3 asks for, change one of them.

### 10. Say what the score is

A score is the number of these items answered correctly on this attempt. It is not a grade, a level or a measure of ability, and the page never calls it one. Skipped items are reported apart from wrong ones.

## Tallies

A tally counts answers: how many of ten habits were ticked, how many statements were rated 4 or above. Name it as a count ("Habits that apply"), never as a trait, a type, a diagnosis or a percentile. The page prints each tally with its denominator and adds the same sentence under every set: "These totals are counts of your answers. They are not a validated measure of anything."
