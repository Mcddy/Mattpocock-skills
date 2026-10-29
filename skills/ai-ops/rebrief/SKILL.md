---
name: rebrief
description: Compresses the current long conversation into one self-contained brief for a fresh chat, with the model and effort to use next. Use when a thread has grown long or drifted, the user says start fresh, hand this off, give me something to paste into a new chat, continue this in another tool, or save tokens, or when the conversation is going in circles. Not for long-term memory across sessions (use mnemosyne).
---

# rebrief

A hard reset inside one task. Long conversations degrade: early wrong turns stick, and every turn re-reads the whole history. This skill writes one brief that lets a fresh session take the next step with nothing else.

## Use when

- The thread is long, has drifted, or is going in circles.
- The user wants to start fresh, hand off, or continue in another tool.
- The user wants to cut usage on a long thread.

## Not this skill

| The request | Goes to |
|---|---|
| Remember this across future sessions | the memory skill |
| What did we decide in an earlier conversation | conversation search or memory |
| Write a standup or status update | standup |
| Summarise a document | answer directly |

## Inputs

The current conversation, and where the brief is going (the same product or a different one).

## Procedure

1. **Read the whole thread.** Later messages override earlier ones.
2. **Fill the template** in `assets/brief-template.md`. Every section is required; write "none" where a section is empty.
   - Goal: one sentence.
   - State: what exists now and where it is.
   - Decisions: each with its reason.
   - Constraints and preferences that still apply.
   - Dead ends: what was tried and why it failed, so it is not tried again.
   - Open questions.
   - Next step: one concrete action.
   - Artefacts: files and links, and what to attach.
   - Terms: names coined in this thread.
3. **Check it.**
   - Every decision made in the thread is in the brief.
   - Nothing in the brief contradicts the latest state.
   - No phrase points back at the old thread ("as above", "earlier", "the second option").
   - Names, numbers and paths are copied exactly.
   - A fresh assistant could do the next step with only this text and the attachments.
4. **Different product.** If the brief is going to another product, remove references to tools and features that only exist here and describe the capability needed instead.
5. **Next model.** Recommend a tier for the next step: light for mechanical work, standard for most building, deep for hard reasoning. Name a specific model only after checking the current list.

## Output

One fenced block containing the brief, under about 400 words unless the state needs more. Then two lines outside the block: what to attach, and the tier to use.

## Rules that always hold

- Abandoned ideas go under Dead ends, never under State or Next step.
- No pleasantries, tone notes or history of who said what.
- If the thread holds an unresolved disagreement, it goes under Open questions with both positions.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
