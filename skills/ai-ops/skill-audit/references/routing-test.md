# Name and description routing test

Measures whether a skill would be chosen for a message, using a model as the router. It is a simulation: it does not prove the skill fires in a live session.

## Build the set

1. Per skill, write at least 5 messages that should reach it and 3 near-misses that share its vocabulary but belong elsewhere. Write them the way the user types. Never put a skill name in a message.
2. Have a different author (a separate agent, another model, or the user) add 3 harder messages per skill, phrased without the skill's own keywords.
3. Shuffle. Keep the expected answers in a file the router never sees.
4. Hold back about 40% of the messages. Use only the rest when revising names or descriptions, then report the held-back score.

## Run it

- **Descriptions visible.** The router sees the full library listing and picks one skill or `none` per message.
- **Name only.** Remove the descriptions of the skills under test and run again. This is the case that matters when a large library pushes descriptions out of the listing.
- Run each arm at least twice, in a context that has not seen the answers.

## Score and read

- A should-trigger message passes when the right skill is picked. A near-miss passes when the skill under test is not picked.
- 100% means the test is too easy. Write harder messages before trusting it.
- On 7 messages, a gap of 4 or less between two single runs is noise.
- Report the model used as router, the number of runs, and the date.
