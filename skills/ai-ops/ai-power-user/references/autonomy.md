# Autonomous workflow architecture

## Autonomy spectrum

Manual, assisted, semi-automatic, autonomous, self-improving. The jump to autonomous needs three things: reliable triggers, decision logic that does not need a human, and output routing that needs no review for routine cases.

## Four parts of every autonomous workflow (trigger, retrieve, act, post)

- **Trigger.** What starts it; never "when I remember". Options: schedule (cron, n8n), event (webhook, file drop, threshold breach, new data), cascade (another agent's output).
- **Retrieve.** The context the agent needs: live data (APIs, web, feeds), stored memory (past outputs, knowledge base, preferences), documents (uploads, databases).
- **Act.** The core job, single-purpose. If it has several stages, build a pipeline.
- **Post.** Defined upfront: save to a structured store, send a notification, feed the next stage, or flag for human review (exceptional cases only).

## Pipeline shapes

| Shape | Flow | Risk and fix | Use for |
|---|---|---|---|
| Sequential chain | input, extract, analyse, synthesise, output | Errors propagate; validation gate between stages | Each stage depends on the last |
| Parallel fan-out and fan-in | input, agents A B C in parallel, synthesiser | Merge conflicts; synthesise last, list disagreements | Multi-lens analysis (Cerberus macro, technical, sentiment) |
| Critic and reviser | generator, critic, pass or fail, reviser | Endless loops; cap at 3 to 5 | Research outputs, high-stakes analysis |
| Router and specialist | input, router (classify), specialist A, B or C | Misrouting; log the route | Query type decides the workflow |
| Memory-augmented | retrieve memory, act with context, output and update memory | Stale memory; date every entry | Work that should compound |

Memory implementation: a structured JSON file (simple), a vector store (scalable), Notion or Airtable (no-code).

## Design principles

1. Pass structured data (JSON) between agents, not prose.
2. Log every intermediate output; when it breaks you need to know where.
3. Design for failure: empty API result, malformed input.
4. Test with adversarial inputs before running unattended.
5. One agent, one job.

## Solo-operator stack

As of March 2026, verify before use. Product capabilities change; the ordering by effort is the useful part.

| Tool | Best for | Effort |
|---|---|---|
| n8n | Visual workflow automation, no-code pipelines | Lowest |
| Claude API with Python | Full control, custom logic | Medium |
| Claude Code | Agentic coding and file tasks | Medium |
| CrewAI | Role-based multi-agent collaboration | Medium |
| LangGraph | Complex stateful agent graphs | Highest |

For a full multi-agent design use multi-agent-designer; for a deployed scheduled pipeline use nexus-prime.
