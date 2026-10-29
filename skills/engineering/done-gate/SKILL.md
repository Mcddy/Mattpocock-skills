---
name: done-gate
description: Installs hooks that block an agent from finishing until the checks named in the task pass. Use when the user says an agent keeps claiming it is done when it is not, tests are failing after it reports complete, or wants a stop gate, completion checks or enforced verification in Claude Code or Codex. Not for planning a long run (use longhaul) and not for checking the facts in a document (use fact-check).
---

# done-gate

A skill is advice the model can skip. A hook runs every time. This skill sets up a completion gate: a config that names the checks, a script that runs them, and the host hook that calls the script when the agent tries to finish.

## Use when

- An agent reports done while tests fail or the build is broken.
- The user wants completion checks, a stop gate or enforced verification on a coding agent.

## Not this skill

| The request | Goes to |
|---|---|
| Plan or run a multi-hour build | longhaul |
| Check the facts in a document | fact-check |
| Decide what tests a project needs | testing-strategy |
| Pre-release checklist | deploy-checklist |

## Inputs

The project folder and the task's own definition of done.

## Tools

Check what this session has: a shell with Python 3, file writing, and the host's hook mechanism. `scripts/gate.py` needs only Python 3. Hosts with no hook mechanism (plain chat) cannot enforce anything: see step 5.

## Procedure

1. **Name the checks.** Turn the definition of done into commands that exit 0 on success. Find real commands by reading the project's manifest files (package scripts, a Makefile, the Python project file, CI config). If a needed check has no command, write the smallest one that tests it. Do not invent a command you have not run once.
2. **Write the config** as `.done-gate.json` in the project root:
   ```json
   {"brief": "TASK.md", "max_blocks": 8,
    "checks": [{"name": "tests", "cmd": "<the project's test command>", "timeout_s": 900}]}
   ```
3. **Dry run.** `python scripts/gate.py --list`, then `python scripts/gate.py`. Exit 0 with status `passed` means done. A non-zero exit with status `blocked` means not done; failures print to stderr.
4. **Wire the hook.** Read the host's current hook documentation in this session and register `gate.py` on the event that fires when the agent tries to finish, using the exit code that host treats as blocking (`--block-code`, default 2). Register `python scripts/gate.py --brief` on the session-start or post-compaction event so the task brief returns after context is compacted. Do not copy hook config from memory: formats differ by host and version.
5. **No hooks available.** Say plainly that enforcement is advisory on this host. Add one line to the project instruction file: run the gate before reporting done and paste its status.
6. **Prove it.** Use an isolated disposable fixture with a planted failure, confirm failure status, then fix the fixture and confirm success. Do not deliberately break the user's working project. Hook registration is separate from installing this skill and requires the applicable authorisation.

## Output

The config file, the hook registration (file and location), and the two proof outputs from step 6.

## Rules that always hold

- A failing check is never removed, loosened or skipped to get a pass. If a check is wrong, stop and ask the user.
- After `max_blocks` failed attempts the gate reports `needs_attention` with a non-zero exit. Stop automatic repair and report the failing checks. Only `passed` with exit zero establishes success.
- The gate script never edits the config.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality.
