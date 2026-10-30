# Lint debt

Generated 2026-10-30 from `scripts/skill_lint.py` plus three house checks. Report only; nothing was fixed.

The linter's own "no 'Use when'" warning is literal and over-counts: many descriptions say "Use for", "Use first" or "Trigger on". The trigger column below uses a looser match. User-invoked skills deliberately have no trigger phrasing (see `.agents/invocation.md`), so they are excluded from that count.

| Bucket | Skills | Over 500 lines | Over 5,000 tokens | Model-invoked without trigger phrasing | Contain em dashes |
| --- | --- | --- | --- | --- | --- |
| ai-ops | 19 | 1 | 1 | 1 | 2 |
| analysis | 16 | 0 | 0 | 0 | 0 |
| build | 12 | 0 | 2 | 0 | 1 |
| creative | 16 | 0 | 1 | 2 | 1 |
| engineering | 34 | 0 | 0 | 0 | 0 |
| incubating | 9 | 0 | 0 | 0 | 0 |
| productivity | 7 | 0 | 0 | 0 | 0 |
| research | 19 | 0 | 0 | 0 | 0 |

## Worst offenders

### Longest bodies (estimated tokens)

- `build/forge`: 276 lines, about 10,121 tokens
- `ai-ops/skill-creator`: 502 lines, about 8,944 tokens
- `creative/animation-studio`: 453 lines, about 7,786 tokens
- `build/web-to-store`: 283 lines, about 5,368 tokens
- `research/research-agency`: 277 lines, about 4,999 tokens
- `creative/algorithmic-art`: 400 lines, about 4,832 tokens
- `build/percept`: 201 lines, about 4,821 tokens
- `build/showpiece`: 103 lines, about 4,684 tokens
- `build/elicitor`: 136 lines, about 4,243 tokens
- `build/preceptor`: 130 lines, about 4,046 tokens

### Model-invoked, no trigger phrasing

- `ai-ops/schedule`
- `creative/animation-studio`
- `creative/sample-picker`

### Em dashes remaining (not yet rewritten)

- `ai-ops/skill-creator`: 45
- `ai-ops/schedule`: 3
- `build/mcp-builder`: 1
- `creative/canvas-design`: 1

## Suggested order

1. Bodies over 5,000 tokens: split into `references/` per `.agents/rewrite-standard.md` (forge, skill-creator and animation-studio first).
2. Model-invoked skills with no trigger phrasing: add a "Use when" clause, then routing-test it.
3. Em dashes: clear them during any rewrite, not as a blind character swap.
