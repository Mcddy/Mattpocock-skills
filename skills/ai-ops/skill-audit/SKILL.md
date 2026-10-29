---
name: skill-audit
description: Audits the skill library itself and finds new skill candidates. Use when the user asks to audit, clean up, dedupe, consolidate or stocktake their skills or plugins; asks which skills overlap or collide; says many skills never fire; wants trigger tests across the library; or asks what repeated work from recent sessions should become a skill, subagent, hook or scheduled task. Not for writing or tuning one skill (use skill-creator).
---

# skill-audit

Looks at a skill library as a whole: what is duplicated, what competes for the same request, what the model can no longer see, and what repeated work deserves a skill of its own. It reports. It never edits, deletes or installs.

## Use when

- The user wants their skills or plugins audited, deduplicated, consolidated or counted.
- The user says skills are not firing, or asks which ones overlap.
- The user wants trigger tests across the library, not for one skill.
- The user asks what they keep doing by hand that should become a skill, subagent, hook or scheduled task.

## Not this skill

| The request | Goes to |
|---|---|
| Write, edit or tune one skill, or improve one description | skill-creator |
| Is this downloaded skill safe to install | airlock |
| Make this skill run on another product | rosetta |
| What is in my task queue, what should I work on | answer directly or the task skill |

## Inputs

- One or more folders that contain skill directories. If none is given, find them: list the directories the host exposes, read the session's own skill listing, and ask the user only if nothing turns up. Do not assume a path.
- Optional: the skill listing as this session sees it (names, and which entries carry a description).

## Tools

Check what this session has before planning: file listing and reading, a shell with Python 3, a search over past conversations, the ability to start a separate agent. `scripts/inventory.py` needs only Python 3. With no shell, do steps 1 to 3 by reading the files and say that body hashes were not computed.

## Procedure

1. **Inventory.** Run `python scripts/inventory.py <root> [<root> ...] --json inventory.json`. It records each skill's name, path, description length, body length, a hash of the body, frontmatter keys and quoted trigger phrases.
2. **Duplicates and forks.** The same body hash under two paths is a true duplicate: one copy per surface is enough. The same name with different hashes is a fork: diff the two and report which is newer and what differs. Never pick a winner silently.
3. **Collisions.** Review each phrase the script lists as claimed by two or more skills, and each description with catch-all wording. A collision is a finding, not a verdict. Two skills can share a phrase and still do different jobs. Recommend a merge only when the procedures and outputs are the same; otherwise recommend narrowing one description and say which words to cut.
4. **Listing gaps.** Compare the inventory with the listing this session can see. Record every skill whose description is missing from the listing, because missing descriptions can impair routing; name-only availability does not prove that activation is impossible. If the host documents a diagnostic for listing size, run that and quote its output instead of estimating.
5. **Name test (optional, costs model calls).** For the skills that matter most, follow `references/routing-test.md`: realistic messages, descriptions removed, blind routing. Report the hit rate per name.
6. **Candidates.** If a conversation search tool exists, look through recent sessions for multi-step procedures that ran two or more times. For each, choose the container: a skill for reusable instructions, a script or hook for a rule that must hold every time, a scheduled task for work tied to a time, a separate agent for work that needs its own context. With no search tool, ask the user for the three chores they repeat most.
7. **Report.**

## Output

Five tables, then one change list.

- Duplicates, Forks, Collisions, Listing gaps, Candidates.
- Change list: one action per row (keep, narrow description, merge into X, retire, rename, build new), the evidence for it, and a status word: `inspected` (read from files), `proposed` (a recommendation) or `tested` (a routing test backs it).

## Rules that always hold

- Report only. The user or the repo's maintainer applies changes.
- Description overlap alone never justifies a merge.
- Keep what was read from files separate from what is inferred.
- A single routing run is noisy. Do not rank two names that differ by a message or two.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
