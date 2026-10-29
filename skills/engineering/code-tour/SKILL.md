---
name: code-tour
description: Explains code the user did not write by tracing one execution path from start to finish, stating which behaviour was confirmed by execution and which was read statically. Use for a code walkthrough or understanding what an agent built before sign-off or merge. Read-only requests stay read-only. Bug reviews, debugging and structural maps are separate workflows.
---

# code-tour

Follows one request, command or job through the code in execution order, so the user can understand code they did not type. Mark each step as confirmed by execution or traced statically. State consequential uncertainty and propose an appropriate check without implying execution or writes are authorised.

## Use when

- An agent built something and the user wants to know what it does.
- The user asks how a request, command or job flows through a repository.
- The user wants a walkthrough before merging or accepting code.

## Not this skill

| The request | Goes to |
|---|---|
| Find bugs, risks, or what will break first | code-review |
| Map how services or modules connect | atlas |
| Write a README, runbook or API docs | documentation |
| An error or stack trace needs fixing | debug |

## Inputs

The repository or files, and one entry point: a route, a command, a job or a function. If the user names none, choose the entry point most of the code serves and say which one was chosen and why.

## Tools

Check what this session has: file reading and search, a shell, the project's own run and test commands, a way to render an interactive page. Find the project's commands by reading its manifest files; do not guess them.

## Procedure

1. **Find the entry.** Locate where the chosen request, command or job enters the code.
2. **Trace.** Follow the path hop by hop. Inspect relevant commands and scripts before execution. Run only when execution is within the user's scope and the inspected command's side effects are acceptable; a read-only request remains static. Otherwise read statically. Mark every hop `confirmed by run` or `read only`. A project-defined command does not itself establish safety or authorisation.
3. **Write each hop:** file and line, what comes in, what it does, what goes out, and side effects (database, network, files, queues). Quote only the lines that matter, at most ten per hop.
4. **Explain one mechanism.** Pick the part that is hardest to hold in the head (a state machine, a retry loop, a cache) and build a small interactive page for it if the host can render one. Otherwise draw a sequence diagram in text.
5. **Check important uncertainty.** Propose focused checks for consequential unconfirmed behaviour. Execute or add tests only within the authorised scope; a read-only walkthrough stays read-only. Do not add tests that merely mirror each line of the implementation. Report what remains unconfirmed.
6. **List unknowns:** anything reached through configuration, reflection or an external service that could not be followed.

## Output

Deliver a concise walkthrough with an end-to-end summary, a path table (hop, file:line, in, out, side effects, confirmed or read only), the important mechanisms and unknowns. Create `TOUR.md` only when writing an artefact is authorised; otherwise deliver it in the reply. Include test files and results only when tests were authorised, necessary and actually performed. Proposed checks remain clearly unexecuted.

## Rules that always hold

- Source files are read only. Any new tests require scope that permits writes.
- Never describe behaviour that was not traced. Say "not followed" instead.
- This is an explanation, not a review. Defects noticed on the way are listed in one closing section and handed to code-review.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
