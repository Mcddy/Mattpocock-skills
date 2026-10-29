# Pattern skeletons

Skeletons, not finished code. `MODEL` and the helper functions (`run_agent`, `validate`, `synthesise`) are placeholders to define in the target stack. Look up a current model ID in the vendor's documentation; do not copy one from here.

## 1. Orchestrator and specialists

```
Orchestrator (route and merge) -> Specialist A | Specialist B | Specialist C
```

The orchestrator classifies the input and routes it, validates each specialist's output, merges if several ran, and returns one structured response.

```python
import json
import anthropic

client = anthropic.Anthropic()

def orchestrate(task: str) -> dict:
    routing = client.messages.create(
        model=MODEL, max_tokens=500,
        system=ORCHESTRATOR_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    route = json.loads(routing.content[0].text)   # validate against a schema in real use
    results = {name: run_specialist(name, task, route["context"])
               for name in route["specialists"]}   # parallelise if independent
    return synthesise(results, task)
```

## 2. Sequential pipeline

```
Input -> Agent A (extract) -> Agent B (analyse) -> Agent C (format) -> Output
```

```python
def run_pipeline(input_data: str) -> str:
    extracted = run_agent("extractor", input_data)
    if not validate(extracted, schema="extraction_schema"):
        raise PipelineError("Extraction stage failed validation")
    analysed = run_agent("analyst", extracted)
    if not validate(analysed, schema="analysis_schema"):
        raise PipelineError("Analysis stage failed validation")
    return run_agent("formatter", analysed)
```

## 3. Parallel fan-out and synthesiser

```
Input -> Agent A (macro) | Agent B (technical) | Agent C (sentiment) -> Synthesiser -> Output
```

```python
import asyncio

async def run_parallel_agents(task: str) -> dict:
    macro, technical, sentiment = await asyncio.gather(
        run_agent_async("macro_analyst", task),
        run_agent_async("technical_analyst", task),
        run_agent_async("sentiment_analyst", task),
    )
    return synthesise_cerberus_brief(macro, technical, sentiment)
```

Use `return_exceptions=True` or per-agent timeouts so one failed lens does not lose the other two.

## 4. Critic and reviser loop

```
Input -> Generator -> Critic -> score below threshold? -> Reviser -> back to Critic (max 3)
```

```python
def critic_reviser_loop(task: str, threshold: int = 7, max_iterations: int = 3) -> str:
    draft = run_agent("generator", task)
    for _ in range(max_iterations):
        critique = run_agent("critic", f"Task: {task}\nDraft: {draft}")
        if json.loads(critique)["score"] >= threshold:
            return draft
        draft = run_agent("reviser", f"Task: {task}\nDraft: {draft}\nCritique: {critique}")
    return draft   # best attempt after the cap; flag that the threshold was not met
```

## 5. Memory-augmented agent

```python
class MemoryAgent:
    def __init__(self):
        self.memory_store = {}   # vector database for production; date every entry

    def run(self, query: str) -> str:
        context = self.retrieve_memory(query)
        response = run_agent("main_agent", f"Context from memory:\n{context}\n\nQuery: {query}")
        self.store_memory(query, response)
        return response
```

## Cross-model pipeline sketch

Use each model for its strength: live data from a search-grounded tool, long documents to a long-context model, reasoning and synthesis to the strongest reasoning model.

```python
def cross_model_pipeline(task: str, documents: list) -> dict:
    live_data = search_tool(f"{task}: latest developments, current data, recent news")
    if total_tokens(documents) > LONG_CONTEXT_THRESHOLD:
        doc_analysis = long_context_model_analyse(documents, task)
    else:
        doc_analysis = reasoning_model_analyse(documents, task)
    return reasoning_model_synthesise(task=task, live_data=live_data,
                                      document_analysis=doc_analysis,
                                      framework="cerberus_three_lens")
```
