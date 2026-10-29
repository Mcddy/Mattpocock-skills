# Shaun skills

Single source of truth for the agent skills used across Claude, Codex and ChatGPT. 132 skills in 8 buckets. `REGISTRY.md` is the index.

## Buckets

| Bucket | What is in it |
| --- | --- |
| `engineering` | Idea-to-ship flow (grill, spec, tickets, implement, TDD, review, retro), plus verification, performance, security and run-governance skills |
| `productivity` | Interviewing, handoff, teaching, writing for agents |
| `research` | Sourced research, claim checking, evidence review, tradecraft |
| `analysis` | Data, models, estimation, scoring, prediction tracking |
| `build` | Apps, tools, pipelines, MCP servers |
| `creative` | Decks, documents, generative art, interactive visuals |
| `ai-ops` | Prompts, skill authoring and porting, orchestration, memory, scheduling |
| `incubating` | Unfinished. Not installed by default |
| `inbox` | Created on first import of an unfiled skill. Not installed by default |

## Use it

Requires Python 3.9+. No other dependencies.

```bash
git clone https://github.com/mcddy/shaun-skills
cd shaun-skills
python scripts/skills.py install          # Claude Code (~/.claude/skills) and Codex (~/.agents/skills)
```

| Host | Route |
| --- | --- |
| Claude Code | `install` above, or as a plugin: `/plugin marketplace add mcddy/shaun-skills` then `/plugin install shaun-skills@shaun` |
| Codex | `install` above (reads `~/.agents/skills`) |
| Claude.ai, ChatGPT | `python scripts/skills.py package`, then upload `dist/<skill>.zip`. Each zip has one top-level folder, which is what the OpenAI skills API accepts. Check the ChatGPT app's upload screen for its current limits |

`install` symlinks, so `git pull` updates every skill in place. Use `--copy` where symlinks are unavailable (Windows without developer mode) and re-run after each pull.

## Keep it in sync

```bash
python scripts/skills.py import --source <folder of skill folders> [--dry-run]   # bring in skills built inside a host
python scripts/skills.py sync                                                     # registry + manifests + lint
git add -A && git commit
```

Rules for changing skills are in [CLAUDE.md](./CLAUDE.md) (also read as `AGENTS.md`).

## Licence

MIT, see [LICENSE](./LICENSE). Four skills carry their own Apache-2.0 `LICENSE.txt`: `algorithmic-art`, `canvas-design`, `mcp-builder`, `skill-creator`.
