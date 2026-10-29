# Shaun skills

One repo, one copy of every skill. Claude, Codex and ChatGPT all read from here. Nothing is edited in an installed location.

## Layout

```
skills/<bucket>/<skill>/SKILL.md   the skill (plus references/, scripts/, assets/, agents/openai.yaml as needed)
REGISTRY.md                        generated index of every skill; read this to route
.claude-plugin/                    generated; lets Claude Code install the repo as a plugin
scripts/skills.py                  the only tool: check, registry, manifests, install, import, package, sync
scripts/skill_lint.py              the linter skills.py calls (Agent Skills spec)
.agents/                           conventions: invocation.md, adr/
docs/agents/                       per-repo config templates the engineering skills read
```

Buckets: `engineering`, `productivity`, `research`, `analysis`, `build`, `creative`, `ai-ops` are installed. `incubating` (unfinished) and `inbox` (imported, not yet filed) are skipped by `install` unless `--all`.

## Picking a skill

1. Read `REGISTRY.md`. Match on the one-line description and the invocation column.
2. Read the candidate's `SKILL.md` before relying on the summary.
3. For the engineering flows (idea to ship), use `skills/engineering/ask-shaun`.

## Changing things

- Edit the skill in `skills/`. Never edit the installed copy, the zip, or `.claude-plugin/`.
- Folder name equals `name:` in the frontmatter. Lowercase, digits and single hyphens.
- Run `python scripts/skills.py sync` before every commit. It regenerates `REGISTRY.md` and the manifests, then lints. CI runs `check`.
- Adding or renaming a user-reachable engineering skill: re-read `ask-shaun/SKILL.md` and update it so the router does not lie.
- Host-specific material stays out of the shared instructions: Codex goes in `agents/openai.yaml`, anything else in `hosts/<host>/NOTES.md` inside the skill. Do not invent a host's config format; if it cannot be confirmed from that host's documentation, list it as a task instead.
- Invocation: see `.agents/invocation.md`. User-invoked means `disable-model-invocation: true` plus `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
- Every skill that dispatches a subagent says to start it with a fresh context window. Some harnesses fork the parent by default, and a fork inherits the context the subagent was meant to escape.
- Repo-level prose (this file, README, docs, ADRs) uses no em dashes. Imported skill bodies keep their original text.

## Syncing hosts

- Claude Code and Codex on this machine: `python scripts/skills.py install` (symlinks; `--copy` on Windows without developer mode). Re-run after adding or renaming a skill.
- Claude Code as a plugin (no `version` on purpose, so every commit is an update; `claude plugin validate .` warns about it, ignore): `/plugin marketplace add mcddy/shaun-skills` then `/plugin install shaun-skills@shaun`.
- Claude.ai and ChatGPT upload: `python scripts/skills.py package` writes `dist/<skill>.zip`, one top-level folder each.
- Pulling in skills you built inside a host: `python scripts/skills.py import --source <folder of skill folders>`, then `sync`. Unknown names land in `skills/inbox/`; file them and add them to `BUCKETS` in `scripts/skills.py`.

## Not vendored

Proprietary or host-maintained skills (docx, pdf, pptx, xlsx, the browser and computer-use skills, and a few Anthropic examples) are listed at the bottom of `REGISTRY.md` and excluded by `EXCLUDE` in `scripts/skills.py`. The Anthropic-catalog plugins (engineering, design, data, finance and the rest) update themselves upstream and are not copied.

## Work queue

Open work for other agents is in `TASKS.md`.

## Agent skills

### Triage labels

Canonical names, unchanged. See `docs/agents/triage-labels.md`.
