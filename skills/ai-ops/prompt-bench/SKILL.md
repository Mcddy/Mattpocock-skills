---
name: prompt-bench
description: "Tunes and tests an existing prompt: turns its parameters into controls and runs variants against a test set to find the best performer. Use when the user wants to test, compare, benchmark or A/B prompts, asks which version of a prompt works better or why a prompt is inconsistent, wants sliders or a control panel for a prompt or agent config, or wants a prompt optimised against examples. Not for drafting a prompt from an idea (use meta-prompt-engineer)."
---

# prompt-bench

Measures prompts instead of arguing about them. The test set is written before anything is changed, variants are run on the model the prompt is meant for, and a winner is named only when it clears the noise.

## Use when

- The user has two or more versions of a prompt and wants to know which is better.
- A prompt gives uneven results and the user wants it tested.
- The user wants controls for a prompt's parameters.
- The user wants a prompt improved against examples.

## Not this skill

| The request | Goes to |
|---|---|
| Write a prompt from a rough idea | meta-prompt-engineer |
| Price or package a prompt for sale | commercial-prompt-packager |
| Simulate a system with adjustable parameters | simforge |
| Is this product A/B result statistically real | statistical-analysis |

## Inputs

The prompt or prompts, the model and host it is meant for, and what a good output looks like.

## Tools

Find out how this session can run the target model, in this order of preference: a model call from inside a rendered page, a non-interactive or scripted mode, separate agents, or the user pasting prompts by hand. Find out whether the host can render an interactive page. Record which route was used.

## Procedure

1. **Parameters.** List the real variables in the prompt (role, scope, depth, tone, output format, examples, order of constraints) and give each one control with a default.
2. **Test set first.** Write 10 to 20 cases with inputs and pass criteria that can be checked: exact match, contains, pattern, or a rubric with anchored scores. Include two or three hard or adversarial cases. Freeze the set before running anything. When optimising, hold back about 40% and never tune on it.
3. **Variants.** Change one thing at a time first: structure, formatting, examples, ordering. Formatting alone can move results a long way. Then combine the changes that helped.
4. **Run the grid.** Every variant on every case, at least three runs per cell if outputs vary. Record the model, its settings and the date. State the grid size (variants x cases x runs) in the output. If it is large for the user's plan, run a smaller grid first and say so.
5. **Score.** Check coded criteria with code. For rubric scores use a judge from a different model family where one is reachable, with labels removed and order shuffled, because a model tends to favour its own output.
6. **Decide on the held-back cases.** Report each variant's mean and spread. If the gap between the top two is inside the spread, report a tie.
7. **Deliver.**

## Output

- The bench: an interactive page with the controls and the results grid if the host can render one, otherwise a table.
- The winning prompt in one fenced block, or the statement that no variant won.
- The test set as a JSON file, so the result can be repeated.
- The model, settings, date, route used and number of calls.

## Rules that always hold

- No winner is declared inside the noise.
- The held-back cases are never used for tuning.
- A result holds for the model and date tested and is labelled that way.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
