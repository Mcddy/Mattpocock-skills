# Writing practice and gate items

Short rules for the multiple-choice items in a course. They cover quiz items only; for surveys, questionnaires and standalone tests use elicitor and its own question-writing reference.

## The stem

- One question, answerable before the options are read. "What is the network address of 192.168.1.130/25?" passes. "Which of the following is true?" does not.
- Everything the learner needs is in the stem. No clue in the stem's grammar points at one option.
- State it positively. If a negative is needed ("which of these is **not** a valid address"), make the negative impossible to miss and use it rarely.
- Test the objective the item is mapped to, at that objective's level. An "apply" objective needs a case to work, not a definition to recognise.

## The options

- Three or four. A fourth option that nobody would choose adds reading and no information; three real ones are better.
- Exactly one is correct, and it is correct without argument.
- **Every distractor is a real mistake.** Take each from a specific misconception or slip: the value from the neighbouring rule, the right method on the wrong input, the step left out, the two quantities swapped. If you cannot say what a learner did to get it, it is not a distractor.
- No "all of the above" and no "none of the above". The validator refuses both.
- Similar length and form. The correct option must not be the longest, the most qualified or the only one with a reason attached. If options carry reasons, all of them do.
- No overlap: one option must not be a special case of another.
- No pattern in position. Spread the correct answer across positions; the validator notes clustering and runs of four.

## The explanation on every option

Every option has a `why`, shown when the learner chooses it.

- For the correct option: why it is right, in one or two sentences, showing the step that decides it.
- For each wrong option: **what was done to get it** and what to do instead. "That is the usable-host count; the question asks for addresses" teaches. "Incorrect" does not.
- State what the wrong value actually is when that helps: "That is 240" beside a wrong binary string lets the learner see the slip.
- Every number in an explanation is a claim. Verify it the same way as an answer.

## Practice against gate

- Practice items teach: the learner sees each option's explanation at once and may try every option. The first choice is recorded for the weakness map and nothing else.
- Gate items decide: no feedback until the whole gate is submitted, at least two items on every objective, and the correct option is not revealed after a failure because the same items return on the retake.
- Do not reuse a practice item in the gate. Use the same kind of case with different values.
- In later modules, include a few practice items mapped to objectives of earlier modules. Gate items are always the module's own.

## A check before shipping

Read each item with the stem covered. If the correct option can be picked from the options alone (by length, by a repeated word, by being the odd one out), rewrite it. Then run `python scripts/validate_course.py`: it enforces the structural rules above and reports the two give-aways it can measure, position and length.
