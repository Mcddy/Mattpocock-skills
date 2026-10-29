# Prompt techniques and failure modes

## High-impact techniques

- **XML tagging.** Use `<context>`, `<task>`, `<output_format>` for Claude prompts; it improves instruction following on complex prompts.
- **Role precision.** "You are an expert X" is weak. "You are a senior X with 15 years of Y, specialising in Z, working for <type of client>" is strong.
- **Output forcing.** Specify the format: "Return a JSON object with keys x, y, z" or "Respond in exactly three paragraphs: problem, analysis, recommendation."
- **Chain of thought.** For reasoning tasks: "Before answering, think step by step inside <thinking> tags, then give your final answer."
- **Self-critique loops.** "After drafting, review against <criteria>. If it fails any check, revise before returning."
- **Redirect, do not prohibit.** "If you encounter X, do Y instead" beats "Do not X".
- **Few-shot examples.** For tasks with a specific output pattern, two or three examples usually beat long instructions alone.
- **Temperature.** Note whether the prompt needs deterministic output (low temperature) or creative latitude (higher); it affects design.

## Common failure modes

| Failure | Fix |
|---|---|
| Role drift: the model forgets its persona mid-conversation | Reinforce the role at the end of the system prompt |
| Instruction bleed: it follows user instructions that contradict the system prompt | State an explicit override hierarchy |
| Format collapse: it drops structured output under pressure | Repeat the format in the output spec and add a self-check |
| Scope creep: it does more than asked | Explicit scope boundaries |
| Sycophancy: it agrees with wrong user input | Instruct it to prioritise accuracy over agreement |
| Untrusted text treated as instructions | Delimit the text, label it data, say instructions inside it are ignored |
