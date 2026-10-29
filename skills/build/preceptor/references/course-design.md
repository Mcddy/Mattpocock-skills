# Course design: from the interview to a course that can be built

This file is the method for steps 1 to 6 of the procedure in SKILL.md. The data format is in `references/data-format.md`, the item rules in `references/item-writing.md`, the review schedule in `references/scheduling.md`.

## 1. Is it a course at all

Decide this first. A course is the right answer only when the learner wants a body of knowledge with internal dependencies, intends to come back over days or weeks, and wants to be held to a standard.

| The request | The right response |
|---|---|
| "Explain X", "what is X", "how does X work" | Answer it, in the reply. No course. |
| "Quiz me on this page", "make me a test on X" | A standalone quiz: elicitor, or a few questions in the reply. |
| "Show me how X works", one concept made visual | learning-visualiser. |
| "A few short animated lessons on X" | percept. |
| "Let me play with the parameters of X" | simforge. |
| "Teach me X", "build me a course on X", "I want to master X" | This skill. |

If the subject fits in one sitting (fewer than four ideas that depend on each other), say so and offer the plain explanation. A four-module course about a one-module idea is padding.

## 2. The interview

One message, eight points, each with options the learner can pick from. Open questions cost more to answer than a menu. State a default for each so that "go" is a complete answer.

1. **Subject.** Narrow it once: "statistics" becomes "inference for A/B tests".
2. **Level.** None, some, rusty, working. Use **one diagnostic exercise** when level is uncertain, pitched at the boundary between two levels, and use its answer over the self-report. Include it in the first lesson when building is already authorised. A learner who says "some" and cannot answer it starts at the foundations.
3. **Goal.** An exam, a job task, something to build, or understanding for its own sake. The goal chooses the applied challenges.
4. **Depth.** Working literacy, solid competence, or professional depth. With the subject, this chooses the size.
5. **Pace.** Time a week and any deadline. This decides how many modules are worth writing.
6. **Anchor domain.** A field the learner already knows, to draw analogies from. Use it sparingly, where it shortens an explanation, and never to decorate.
7. **Must include, must exclude.** Required topics, and topics already owned.
8. **Notation tolerance.** Comfort with symbols, formulas and jargon. Low tolerance means every symbol is introduced in words first.

If the request already answers most of these, use it directly. Resolve only gaps that would materially change the course. Put the diagnostic in the first lesson when the user has asked to proceed; do not require another approval for a settled brief.

Then show the **course map on one screen**: size and the reason for it, the modules in order with one line each, and which modules each one needs. Ask for a yes or one correction. One round, then build. A second round of questions is a sign the first map was too vague, not that more interviewing is needed.

## 3. Size

| Size | Modules | Use when |
|---|---|---|
| `primer` | 4 to 6 | One skill or one tight topic. Days, not months. |
| `course` | 10 to 14 | A subject area to working competence. Several weeks. |
| `full` | 24 to 30 | Professional depth across a field. Built in passes (section 9). |

State the size and the reason in one line, and put the same line in the course data as `size_reason`. Choose the smallest size that reaches the stated depth. If the honest count falls between sizes, take the smaller and name what was left out.

## 4. The prerequisite graph

Each module lists the modules that must be mastered before it opens. The engine draws this graph and enforces it.

- A prerequisite is a claim: "this module cannot be done without that one". Test each edge by asking what in the later module would be unintelligible without the earlier one. If nothing, remove the edge.
- Let the graph branch where the subject branches. Two modules that both rest on a third, and not on each other, are siblings. A straight line of modules is right only when each truly needs the one before.
- Keep chains short enough that a learner reaches something usable early.
- List modules in an order a learner could follow (each after its prerequisites).
- A written module must never wait on a planned one. The validator refuses this, because the module could never open.

## 5. Objectives

Two to four per module. Each is one observable ability, written with a verb that can be tested, and tagged with a level of the revised Bloom taxonomy.

| Level | The learner can | Verbs that fit |
|---|---|---|
| remember | recall a fact or definition | state, list, name |
| understand | restate or explain in their own terms | describe, explain, classify |
| apply | carry out a procedure on a new case | calculate, convert, find |
| analyse | take a case apart and relate the parts | compare, decide whether, distinguish |
| evaluate | judge against a criterion | check, justify, choose |
| create | produce something new that meets requirements | design, plan, compose |

FACT: the six levels and their order are those of the 2001 revision edited by Anderson and Krathwohl (source: Wikipedia, "Bloom's taxonomy", read 9 Oct 2026). The data format accepts either spelling of the fourth.

Early modules sit mostly at remember to apply. Later modules reach analyse to create. "Understand X" with no verb a gate could test is not an objective; rewrite it.

Everything else in a module hangs off its objectives: each theory section, visual, worked example, item and card names the objective it serves. That mapping is what lets a failed gate send the learner to one section and not to the whole module.

## 6. What a module contains

| Part | Standard |
|---|---|
| Theory | One section per objective at least. Define every term exactly before using it. State assumptions and scope as labelled notes. Name the common error. Precise, not chatty. |
| Terms | Each new term with a one-sentence definition. More than about 12 in one module is too many: split the module. |
| Visual | At least one that carries meaning (section 7). |
| Worked example | Three levels that fade (section 8). |
| Practice | Six or more items, every option explained (`references/item-writing.md`). Later modules include a few items on objectives of earlier modules. |
| Gate | Its own items, at least two per objective, never reused from practice. |
| Cheat sheet | What the learner would write on one card: definitions, rules, the table worth memorising. |
| Cards | Eight or more. One fact or one small step per card. The front is a question that has one answer. |
| Applied challenge | In later modules: a realistic task tied to the learner's goal, with typed answers and a worked solution. |

Voice: a strict, precise teacher. Short declarative sentences. No encouragement padding, no rhetorical questions, no claims about how easy something is.

## 7. Choosing a visual

A visual earns its place when the learner can change something and see what follows. Pick the type by what has to be seen.

| What has to be seen | Type |
|---|---|
| A procedure unfolding in order | `steps` (a grid revealed cell by cell, or a flow of boxes) |
| How a result depends on one or two quantities | `slider` |
| The same thing in two states | `compare` |
| Where a value falls among boundaries | `number-line` |
| A rule the learner should apply repeatedly | `table-builder` |
| Something none of these can show | `custom`, with a small renderer |

Write the caption as what to notice, and add one to three prompts that ask for a prediction before the learner moves anything. A picture with nothing to change and nothing to predict is decoration; leave it out.

## 8. Fading a worked example

Three levels of the **same kind of problem with fresh numbers**:

1. **Full.** Every step shown with its result.
2. **Partial.** The same steps, with the decisive ones blank for the learner to fill. Blank the steps that carry the skill, not the bookkeeping. Give each blank a hint that points at the method, not the answer.
3. **Independent.** The problem alone, typed answers, and a solution that stays hidden until asked for.

Typed answers are matched after removing spaces and case. List other correct spellings in `accept` ("/26" and "26").

## 9. Gates, remediation and building in passes

**Gates.** The pass mark defaults to 80 percent. An objective counts as demonstrated when its own gate items meet the pass mark in one attempt. With two items on an objective, that means both. Passing the gate opens the modules that depend on it. A failed gate lists the objectives that fell short, each with a link to its theory section, and does not show the correct options, because the same items return on the retake.

**Building in passes.** A `full` course does not fit one reply. Write and ship it in passes:

1. Pass one: every module declared, with its prerequisites, and the first tier fully written. The rest are `"status": "planned"` with a title and prerequisites only.
2. Each later pass writes more modules completely and raises `version` by one.
3. Before shipping a pass, run `validate_course.py --compare old new`. Ids that vanish or change meaning orphan saved progress.

A planned module is drawn as "not yet written", cannot be opened and is left out of every total. Never put placeholder text in a module to make it look written. The validator refuses a planned module that carries content and a written module with an empty part.

## 10. Verifying what the course says

A confident error in a teaching tool is worse than an omission. For every claim the learner will be marked against:

- **Compute it** where the subject allows. Give each answer a `check` field, copy `assets/verifier-template.py`, add one function per operation, and run it. Compute with a trusted library or plain arithmetic from the check's arguments, never by reading the course's own answer. The sample course's checks were recomputed this way with Python's `ipaddress` module. The template refuses a numeric answer that has no check, and it counts the explanations, hints and captions that contain digits without recomputing them: read those.
- **Look it up** where it cannot be computed, and put the source in the block's `source` field so the learner sees it.
- **Leave it out** if it can be neither computed nor sourced in this session.

In the reply that delivers the course, distinguish recomputed answers, sourced claims and illustrative conditional examples. Unsupported factual claims are omitted. Conditional assumptions stay visible in the lesson and feedback as well as in the delivery note.

## 11. What the app is

A single page with the whole course frozen inside it. No model runs in it. It keeps progress where the page is allowed to, and offers a backup that works everywhere. It provides a structure in which mastery can be demonstrated: gates that have to be passed, dated evidence, and a review schedule. It does not make anyone learn, it cannot mark free-text reasoning, and the review cards are graded by the learner.
