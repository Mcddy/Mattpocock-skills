# Pipeline patterns

For designing a real multi-agent system, route to multi-agent-designer. For a deployed always-on pipeline, route to nexus-prime. This file is the short version used when nexus plans a cross-tool job.

## Shapes

| Shape | Flow | Main risk and fix |
|---|---|---|
| Sequential chain | input, extract, analyse, synthesise, output | Errors propagate; put a validation gate between stages |
| Parallel fan-out and fan-in | input, agents A B C in parallel, synthesiser | Good for the Cerberus three-lens analysis: run lenses in parallel, synthesise last |
| Critic and reviser | generator, critic, score above threshold?, reviser | Always cap iterations (3 to 5) |
| Router and specialist | classify intent, then specialist A, B or C | Misrouting; log the route chosen |
| Memory-augmented | retrieve memory, act with context, output and update memory | Stale memory; date every entry |

## Prompts

Orchestrator (JSON only): which specialists to activate, the context each needs, how to merge their outputs.

Critic (JSON only): score 0 to 10, strengths, weaknesses, specific fixes, whether to revise.

Pass JSON between agents, not prose, and validate it before the next step.

## Cross-tool campaign (research-heavy jobs)

| Tier | Tool | Job |
|---|---|---|
| 1 | Perplexity | Current state, recent developments, key data points with sources; deep-research mode for exhaustive reports |
| 2 | NotebookLM | Load the authoritative sources from tier 1; run synthesis queries; extract structured findings |
| 3 | Gemini or Claude | Gemini if the document set is very large; Claude for framework application and hypothesis testing |
| 4 | Claude | Final synthesis: framework, confidence ratings, structured output, recommended action |

Gates: tier 1, is the core question answered with primary evidence and are conflicts listed. Tier 2, does it add to tier 1 rather than repeat it, and are gaps named. Tier 3, is the framework applied correctly with confidence levels and a reachable conclusion.

Final synthesis prompt: sources listed; the five most important findings; contradictions between sources; apply `<framework>`; output executive summary, key findings with confidence, uncertainties, recommended action, what would change the conclusion; overall confidence HIGH, MEDIUM or LOW. For a full ledger-backed campaign use deep-research-orchestrator.

## Deployment checklist

- One agent, one job.
- JSON between agents.
- Every external call has error handling.
- Maximum iterations on every loop.
- Intermediate outputs logged.
- Human checkpoint before irreversible actions.
- Tested with malformed and adversarial input.

## Cost routing

Use a small, cheap model for bulk classification and extraction, and a stronger one for synthesis and judgement. Check current pricing before committing to a volume.
