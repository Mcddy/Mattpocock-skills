# Rewrite standard for first-generation skills

Applies when an older "doctrine" style skill is rewritten. The goal is the same capability and the same triggers in a form an agent follows reliably: procedure over persona.

## Keep

- Every real capability, procedure step, decision rule, framework and table that changes what the agent does.
- Shaun-specific context (his projects, stack, named systems such as Cerberus). It is why the skill exists.
- The skill's `name` and folder. Never rename, merge or delete a skill.

## Drop

- Slogans, persona framing and motivational lines ("a force to be commanded", "sovereign", "dominance").
- Repetition: the same rule said in three places becomes one rule.
- Claims about specific model versions, prices or product features that will go stale. Keep the method; if a dated fact is genuinely needed, put it in `references/` with "as of <date>, verify before use".
- Em dashes and decorative emoji. Rewrite the sentence (comma, colon, full stop, parentheses), never a blind character swap.

## Shape

```
---
name: <unchanged>
description: "<what it does>. Use when <situations and phrases>. Not for <near misses> (use <sibling>)."
---

# <name>

One or two sentences: what it produces.

## Use when
## Not this skill        table: request -> sibling skill (siblings must exist in REGISTRY.md)
## Inputs
## Procedure             numbered steps an agent can execute
## Output
## Rules that always hold
```

Exemplars: `skills/ai-ops/rosetta/SKILL.md`, `skills/research/fact-check/SKILL.md`.

- Description: one quoted line, at most 1,024 characters, model-facing, keeps the old trigger phrases that still apply.
- Body: aim for under 250 lines. Long reference material (catalogues, templates, platform notes) moves to `references/<topic>.md`, linked from the body, one level deep.
- Host-neutral: name the capability ("search the web", "start a separate agent with a fresh context window"), not a product tool, and give a fallback when it is missing.
- Australian spelling.

## Routing check

Each rewritten skill gets `evals/routing.md`: 6 prompts that should trigger it and 4 near misses that should not (each naming the sibling that should win). Run the simulated check: read every skill's description (`python3 -c "import sys; sys.path.insert(0,'scripts'); import skills; print(skills.build_registry())"`) and record which skill a router would pick for each prompt. This is a judged simulation, not a live routing measurement; say so in the file.

## Done means

- `python3 scripts/skill_lint.py <skill-dir>` reports no errors.
- No em dashes in the skill folder.
- Nothing listed under Keep was lost: the report names anything removed and why.
