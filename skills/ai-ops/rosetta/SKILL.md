---
name: rosetta
description: Ports a skill between Claude and ChatGPT or Codex and keeps one canonical source folder. Use when the user wants a Claude skill to run in ChatGPT or Codex (or the reverse), asks to make a skill portable or spec-compliant, wants a custom GPT migrated into a skill before retirement, or asks what will break when a skill moves runtimes.
---

# rosetta

Keeps one source folder per skill that every host can read, and reports exactly what will not carry across. The canonical folder follows the open Agent Skills spec. Anything a single host needs lives beside it, never inside the shared instructions.

## Use when

- A skill written for one assistant has to run on another.
- The user asks whether a SKILL.md is portable or spec-compliant.
- A custom GPT or similar single-host assistant has to become a skill.
- The user asks what breaks when a skill changes host.

## Not this skill

| The request | Goes to |
|---|---|
| Turn a web app into a mobile app | web-to-store |
| Package a prompt for sale | commercial-prompt-packager |
| Build a connector or MCP server | mcp-builder |
| Write a new skill from an idea | skill-creator |

## Inputs

- The source: a skill folder, or for a migration the exported instructions, knowledge files, list of actions and conversation starters.
- The target host or hosts.

## Tools

Check what this session has: file read and write, a shell with Python 3, web fetch for the target host's current documentation. `scripts/skill_lint.py` needs only Python 3.

## Procedure

1. **Lint the source.** Run `python scripts/skill_lint.py <skill-dir>`. It checks the name (lower case, digits, single hyphens, at most 64 characters, same as the folder), the description (present, at most 1,024 characters), body length, that every referenced file exists, reference depth, and frontmatter keys outside the spec.
2. **Classify each finding** as portable, host-specific or unknown. Frontmatter keys outside the spec are host-specific by definition.
3. **Neutralise the body.** Replace named tools with the capability they provide ("search the web", "start a separate agent", "render an interactive page") and add a fallback for hosts without it. Keep the description unchanged unless it names a host feature; a changed description must be routing-tested again.
4. **Move host-specific material** to `hosts/<host>/NOTES.md` inside the skill folder. Do not delete it.
5. **Check the target host's current rules.** Read its documentation in this session for where skills live, what manifest it wants and what it ignores. If you cannot confirm a format from the host's own documentation, do not write that file: list it as a task for the maintainer.
6. **Migrating a single-host assistant.** Instructions become the SKILL.md body, rewritten as a procedure. Knowledge files become `references/`. Conversation starters become trigger cases in `evals/`. Each custom action is listed as "needs a connector" with its endpoint and auth type. Confirm against the host's migration page what its own tool carries over before promising anything.
7. **Lint again**, then write the report.

## Output

- The canonical skill folder, linted clean.
- `PORTING.md` with three lists: carried across unchanged, changed (old and new wording), not portable (and what would replace it), plus the host documentation pages read and their dates.

## Rules that always hold

- Never invent a host's config or manifest format.
- Never install. Hand the folder to the user or the repo maintainer.
- One canonical folder. Host builds are outputs and are not edited by hand.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
