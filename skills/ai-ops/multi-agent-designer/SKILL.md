---
name: multi-agent-designer
description: >
  Expert skill for designing, architecting, and building multi-agent systems — across Claude, Gemini, GPT, and open-source models. Use when Shaun wants to build a system where multiple AI agents collaborate, when a task requires parallel specialised agents, when building autonomous pipelines with multiple models, or when designing agent orchestration frameworks. Trigger on: "design a multi-agent system for...", "build an agent that uses other agents", "orchestrate multiple AIs for...", "agent architecture for...", "how do I build X with multiple agents", or any task that benefits from specialist agent collaboration. Produces complete architectural blueprints, implementation-ready designs, and working code patterns. Never suggest a single-agent solution when a multi-agent architecture would be superior.
---

# Multi-Agent Designer

Architectural blueprints and implementation patterns for multi-agent AI systems.

---

## Multi-Agent Design Principles

1. **One agent, one specialisation** — agents with multiple jobs fail unpredictably
2. **Orchestrators route; workers execute** — never mix concerns
3. **Structured handoffs** — JSON between agents, not prose
4. **Fail gracefully** — every agent call can fail; design for it
5. **Human oversight at decision gates** — irreversible actions need a human checkpoint
6. **Log everything** — when multi-agent systems fail, you need to trace the path

---

## Architecture Patterns

### Pattern 1: Orchestrator + Specialists

```
                    ┌─────────────────┐
                    │   Orchestrator   │
                    │  (Route & Merge) │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │Specialist│      │Specialist│      │Specialist│
    │    A     │      │    B     │      │    C     │
    └──────────┘      └──────────┘      └──────────┘
```

**Orchestrator responsibilities:**
- Classify input → route to correct specialist
- Receive specialist output → validate
- Merge outputs if multiple specialists used
- Return final structured response

**Implementation (Python):**
```python
import anthropic

client = anthropic.Anthropic()

def orchestrate(task: str) -> dict:
    # Step 1: Orchestrator classifies and routes
    routing = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        system=ORCHESTRATOR_PROMPT,
        messages=[{"role": "user", "content": task}]
    )
    route = json.loads(routing.content[0].text)

    # Step 2: Run specialists (parallel if independent)
    results = {}
    for specialist_name in route["specialists"]:
        results[specialist_name] = run_specialist(specialist_name, task, route["context"])

    # Step 3: Synthesise
    return synthesise(results, task)
```

### Pattern 2: Pipeline (Sequential)

```
Input → Agent A → Agent B → Agent C → Output
        (extract)  (analyse)  (format)
```

**When to use:** Each stage transforms the output for the next stage.
**Key requirement:** Validation gate between each stage.

```python
def run_pipeline(input_data: str) -> str:
    # Stage 1: Extract
    extracted = run_agent("extractor", input_data)
    if not validate(extracted, schema="extraction_schema"):
        raise PipelineError("Extraction stage failed validation")

    # Stage 2: Analyse
    analysed = run_agent("analyst", extracted)
    if not validate(analysed, schema="analysis_schema"):
        raise PipelineError("Analysis stage failed validation")

    # Stage 3: Format output
    return run_agent("formatter", analysed)
```

### Pattern 3: Parallel Fan-Out + Synthesiser

```
         ┌── Agent A (Macro lens) ──┐
Input ───┼── Agent B (Technical)  ──┼─── Synthesiser ── Output
         └── Agent C (Sentiment)  ──┘
```

**When to use:** Independent parallel analysis, merged at end.
**Implementation:**

```python
import asyncio

async def run_parallel_agents(task: str) -> dict:
    results = await asyncio.gather(
        run_agent_async("macro_analyst", task),
        run_agent_async("technical_analyst", task),
        run_agent_async("sentiment_analyst", task)
    )
    macro, technical, sentiment = results

    # Synthesise all three
    return synthesise_cerberus_brief(macro, technical, sentiment)
```

### Pattern 4: Critic-Reviser Loop

```
Input → Generator → Critic → [Score < threshold?] → Reviser → Output
                       ↑                                  |
                       └──────────────────────────────────┘
                              (max 3 iterations)
```

```python
def critic_reviser_loop(task: str, threshold: int = 7, max_iterations: int = 3) -> str:
    draft = run_agent("generator", task)

    for i in range(max_iterations):
        critique = run_agent("critic", f"Task: {task}\nDraft: {draft}")
        score = json.loads(critique)["score"]

        if score >= threshold:
            return draft  # Quality met

        draft = run_agent("reviser", f"Task: {task}\nDraft: {draft}\nCritique: {critique}")

    return draft  # Return best attempt after max iterations
```

### Pattern 5: Memory-Augmented Agent

```python
class MemoryAgent:
    def __init__(self):
        self.memory_store = {}  # Replace with vector DB for production

    def run(self, query: str) -> str:
        # Retrieve relevant memories
        relevant_context = self.retrieve_memory(query)

        # Run agent with memory context
        response = run_agent("main_agent",
            f"Context from memory:\n{relevant_context}\n\nQuery: {query}")

        # Update memory
        self.store_memory(query, response)
        return response
```

---

## Cross-Model Orchestration

Using multiple AI models for their respective strengths:

```python
def cross_model_pipeline(task: str) -> dict:
    """
    Perplexity → real-time data
    Gemini → long document analysis
    Claude → reasoning and synthesis
    """

    # Step 1: Real-time intelligence (Perplexity)
    live_data = perplexity_search(
        f"{task} — latest developments, current data, recent news"
    )

    # Step 2: Document analysis (Gemini if large docs)
    if len(documents) > 100000:  # Token threshold
        doc_analysis = gemini_analyze(documents, task)
    else:
        doc_analysis = claude_analyze(documents, task)

    # Step 3: Final synthesis (Claude)
    return claude_synthesize(
        task=task,
        live_data=live_data,
        document_analysis=doc_analysis,
        framework="cerberus_three_lens"
    )
```

---

## Agent Prompt Templates

### Orchestrator System Prompt
```
You are an orchestrator agent. Your job is to route tasks to the correct specialists.

SPECIALISTS AVAILABLE:
- macro_analyst: Analyses macroeconomic data and central bank policy
- technical_analyst: Analyses price action, charts, and technical indicators
- sentiment_analyst: Analyses positioning, options, and market sentiment
- researcher: Conducts in-depth research on specific topics
- formatter: Formats final outputs for specific audiences

Given a task, respond with JSON only:
{
  "specialists": ["list of specialists to activate"],
  "context": "relevant context to pass to each specialist",
  "synthesis_instruction": "how to merge specialist outputs"
}
```

### Critic Agent System Prompt
```
You are a quality critic. Your job is to rigorously evaluate outputs.

Evaluate the provided draft against:
1. Does it fully address the task?
2. Is it accurate and well-reasoned?
3. Are claims supported by evidence?
4. Is it the appropriate format and length?
5. What is missing or weak?

Respond with JSON only:
{
  "score": 0-10,
  "strengths": ["list"],
  "weaknesses": ["list"],
  "specific_fixes": ["list of concrete improvements"],
  "should_revise": true/false
}
```

---

## Deployment Checklist

Before deploying a multi-agent system:
- [ ] Each agent has a single, well-defined job
- [ ] Structured data (JSON) passes between all agents
- [ ] Every agent call wrapped in try/except
- [ ] Max iteration limits on all loops
- [ ] All intermediate outputs logged
- [ ] Human checkpoint before irreversible actions
- [ ] Tested with adversarial/malformed inputs
- [ ] Cost estimate per run calculated (API calls compound)
