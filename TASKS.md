# Tasks for Codex

Work queue for the Shaun skills repo. Read `AGENTS.md` first (it is `CLAUDE.md`). Do the tasks in order, one commit per task, and run `python scripts/skills.py sync` before each commit. Stop and report rather than guess when a task says to.

## Rules

- No em dashes in repo-level prose. Imported skill bodies keep their original text.
- Never delete a skill. Propose removals in `TASKS.md` under "Proposals" and wait.
- Never invent a host's config format. Read that host's current documentation in this session, cite the page and date in `hosts/<host>/NOTES.md`, and write the file only if the format is confirmed. Otherwise list the gap.
- Do not change a skill's `description` unless the task says so. A changed description needs a routing test.
- Do not push to `main`. Work on a branch and open a PR only when asked.
- Report each task as done, partly done or blocked, with the command output that shows it.

## 0. Bootstrap (Shaun runs this, not Codex)

Fresh private repo with no inherited history. The old history carries 96 commits authored by the upstream project; a fresh history does not. The `LICENSE` notice stays, because MIT requires it on copies of those skills.

```bash
git clone --depth 1 --branch shaun-skills https://github.com/Mcddy/Mattpocock-skills.git shaun-skills
cd shaun-skills
rm -rf .git
git init -b main
git add -A
git commit -m "Initial commit"
gh repo create shaun-skills --private --source . --push
```

PowerShell: replace `rm -rf .git` with `Remove-Item -Recurse -Force .git`.

After it is pushed, delete the old repo or archive it.

## 1. Rename the slug

`mcddy/shaun-skills` is hard-coded in `README.md` and `CLAUDE.md`. Replace it with the real `owner/repo` of the new repo. Also update the clone URL in `README.md`. Check: `grep -rn "mcddy" .` shows only the real slug, and `grep -rniE "mattpocock|aihero" .` shows nothing.

## 2. Windows check

Shaun's desktop and laptop run Windows. In CI, add a `windows-latest` job to `.github/workflows/check.yml` that runs `python scripts/skills.py check` and `python scripts/skills.py install --copy` with `HOME` and `USERPROFILE` pointed at a temp folder. Fix whatever breaks. Known risks: `Path.home()` on Windows, symlink fallback in `link_or_copy`, long paths in `canvas-design` and `forge`.

## 3. Codex metadata for imported skills

Matt-derived skills have `agents/openai.yaml` (`interface.display_name`, `interface.short_description`). The 96 imported skills do not. Confirm the current Codex format from OpenAI's Codex skills documentation, then add a `generate-openai-yaml` subcommand to `scripts/skills.py` that writes the file from each skill's frontmatter. Do not set `policy.allow_implicit_invocation` unless the skill has `disable-model-invocation: true`. Skip skills that already have the file. Record the documentation page in `hosts/codex/NOTES.md`.

## 4. ChatGPT

1. Read OpenAI's current documentation for ChatGPT skills and for the API skills endpoint. Write `hosts/chatgpt/NOTES.md` with what is confirmed: where skills are uploaded, accepted layout, size limits, and what the app ignores.
2. Check `python scripts/skills.py package` output against those limits. List any skill over a limit.
3. Shaun will put an export of the skills installed in ChatGPT in `incoming/chatgpt/<skill>/`. When that folder exists, run `import --source incoming/chatgpt --dry-run`, show the plan, and wait before the real import. Name clashes with existing skills are a stop-and-ask.

## 5. Codex plugin manifest

Only if OpenAI's Codex documentation confirms a plugin manifest that can point at `skills/`. Write it from `scripts/skills.py manifests` so it stays generated. Otherwise write the gap into `hosts/codex/NOTES.md` and skip.

## 6. Overlap report

Write `docs/agents/overlaps.md`: pairs or groups of skills that cover the same situation, with the trigger that should pick each. Start from these and find more by reading `REGISTRY.md`:

- `handoff` and `rebrief`
- `skill-creator` and `skill-audit` and `rosetta`
- `research` (engineering) and `deep-research-orchestrator` and `research-agency`
- `code-review` (engineering) and `referee-panel`
- `grill-me`, `grill-with-docs` and `elicitor`
- `orchestrator`, `taskforce` and `mandate`

Recommendation only. Do not edit the skills.

## 7. Lint debt

`python scripts/skill_lint.py --root skills/<bucket>` reports 79 descriptions without a "Use when" clause and several bodies over 500 lines. Report counts per bucket in `docs/agents/lint-debt.md` with the worst offenders. Fix nothing in this task.

## 8. Host-specific content

`skills/ai-ops/agent-hub` is bound to a Windows path on Shaun's desktop. Move the path-specific material to `skills/ai-ops/agent-hub/hosts/windows/NOTES.md` and make `SKILL.md` refer to a configurable workspace folder. This changes the description, so write 5 routing test prompts (3 should trigger, 2 should not) in `skills/ai-ops/agent-hub/evals/routing.md` and say which would trigger it.

## Proposals

(Codex appends here. Shaun decides.)
