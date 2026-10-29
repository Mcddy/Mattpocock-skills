---
name: meta-prompt-engineer
description: >
  Expert-level prompt engineering skill for crafting production-ready system prompts and task prompts from scratch or from rough drafts. Use this skill whenever the user wants to build, improve, or deeply engineer a prompt — including when they describe what they want in plain language, paste a rough draft, say "help me write a prompt", "engineer a prompt for me", "make a system prompt for X", "refine this prompt", "my prompt isn't working", or any variation. Also trigger when the user is building an AI tool, agent, workflow, or assistant and needs the underlying prompt architecture designed. This skill runs a full agentic engineering loop: it interviews the user, stress-tests assumptions, identifies edge cases, writes a draft, self-critiques, and iterates until the prompt is excellent. Never skip the loop for complex prompts — quality over speed.
---

# Meta Prompt Engineer

A full-loop prompt engineering skill that produces production-grade prompts through intelligent iteration. Works from plain language descriptions OR rough drafts.

---

## Core Philosophy

Great prompts are not written — they are *engineered*. This means:
- Understanding the **true goal** behind the stated request
- Anticipating **failure modes** before they happen
- Making **implicit assumptions explicit**
- Stress-testing against **edge cases and adversarial inputs**
- Iterating until the output is genuinely excellent

---

## Phase 1: Intake & Intent Mapping

Before writing a single line of prompt, run a focused intake interview. Your goal is to extract:

1. **The task** — What should the AI do? Be specific about the action, not just the domain.
2. **The model** — Which AI will run this prompt? (Claude, GPT-4, Gemini, etc.) Defaults to Claude if unspecified.
3. **The user** — Who will be interacting with the finished prompt/tool? End user? The prompt engineer themselves?
4. **The context** — Where does this run? System prompt? Single-shot task? Multi-turn agent? API pipeline?
5. **The output format** — What should the AI return? Prose? Structured data? Code? A decision?
6. **Constraints** — What should it never do? What tone? What length? Any hard rules?
7. **Success criteria** — How will we know the prompt is working well?

**Intake style:**
- If the user gave plain language intent: ask targeted questions to fill gaps before writing.
- If the user pasted a draft: read it carefully first, identify what's working and what's missing, then ask only the questions the draft doesn't answer.
- Keep the interview tight — max 5-7 questions, grouped logically. Don't interrogate.

---

## Phase 2: Structural Design

Before drafting, decide on the prompt architecture:

### Prompt Type Selection
| Type | Use When |
|------|----------|
| **System prompt** | Persistent AI persona/role for an agent or assistant |
| **Task prompt** | Single-shot instruction for a specific job |
| **Chain prompt** | Part of a multi-step pipeline (needs handoff clarity) |
| **Meta prompt** | A prompt that generates other prompts |
| **Hybrid** | System prompt + dynamic task injection |

### Core Structural Components (include what's relevant)
- **Role/Persona** — Who is the AI being? Be specific and purposeful.
- **Context** — What does the AI need to know to do its job?
- **Task definition** — Exactly what it should do, step by step if needed.
- **Output specification** — Format, length, structure, tone.
- **Constraints** — Hard rules, edge case handling, what to refuse or flag.
- **Examples** — Few-shot examples where the task benefits from demonstration.
- **Reasoning scaffold** — Chain-of-thought instructions if needed for complex tasks.
- **Self-check instructions** — Tell the AI to verify its output before returning.

---

## Phase 3: Draft & Internal Critique

Write the first draft, then immediately run an internal critique pass before showing the user. Ask yourself:

**Clarity audit:**
- [ ] Is every instruction unambiguous?
- [ ] Could any instruction be interpreted two different ways?
- [ ] Are there implicit assumptions the AI might not share?

**Coverage audit:**
- [ ] Does it handle the core case well?
- [ ] Does it handle edge cases (empty input, ambiguous input, adversarial input)?
- [ ] Are failure modes addressed?

**Tone & format audit:**
- [ ] Does the tone match the intended use?
- [ ] Is the length appropriate — not too sparse, not padded?
- [ ] Is formatting used where it helps, not just for aesthetics?

**Power audit:**
- [ ] Is there anything that would make this prompt significantly better?
- [ ] Are there techniques not yet used that would help? (CoT, few-shot, self-critique loops, XML tags, structured output forcing, etc.)

Fix obvious issues before showing the user. Only surface critique points where you genuinely need their input.

---

## Phase 4: Present & Iterate

Present the draft with:
1. **The prompt itself** — clean, ready to copy
2. **Key decisions explained** — briefly note 2-3 architectural choices and why you made them
3. **What to watch for** — flag 1-2 potential failure modes the user should test
4. **Iteration prompt** — ask: *"What feels off, what's missing, or what would you change?"*

Then iterate. Don't stop at one draft unless the user explicitly says it's done. Each iteration should be a genuine improvement, not cosmetic changes.

---

## Phase 5: Final Delivery

When the prompt is locked, deliver:

```
## Final Prompt
[clean prompt, ready to use]

## Usage Notes
- Model: [recommended model]
- Context: [where/how to deploy]
- Known edge cases: [any remaining caveats]
- Suggested tests: [2-3 test inputs to verify performance]
```

---

## Prompt Engineering Reference

### High-Impact Techniques

**XML tagging** — Use `<context>`, `<task>`, `<output_format>` tags for Claude prompts. Significantly improves instruction following on complex prompts.

**Role precision** — "You are an expert X" is weak. "You are a senior X with 15 years of Y, specialising in Z, working for [type of client]" is strong.

**Output forcing** — Specify format explicitly. "Return a JSON object with keys: x, y, z." or "Respond in exactly three paragraphs: problem, analysis, recommendation."

**Chain-of-thought** — For reasoning tasks: "Before answering, think through this step by step inside <thinking> tags. Then provide your final answer."

**Self-critique loops** — "After drafting your response, review it against [criteria]. If it fails any check, revise before returning."

**Negative instructions** — "Do not X" is often weaker than "If you encounter X, do Y instead." Redirect rather than prohibit where possible.

**Few-shot examples** — For tasks with a specific output pattern, 2-3 examples dramatically outperform long instructions alone.

**Temperature guidance** — Note if the prompt needs deterministic output (temp 0) or creative latitude (temp 0.7+). Affects prompt design.

### Common Failure Modes to Prevent
- **Role drift** — AI forgets its persona mid-conversation → reinforce at end of system prompt
- **Instruction bleed** — AI follows user instructions that contradict system prompt → explicit override hierarchy
- **Format collapse** — AI drops structured output under pressure → reinforce format in output spec and add self-check
- **Scope creep** — AI does more than asked → explicit scope boundaries
- **Sycophancy** — AI agrees with wrong user input → instruct to prioritise accuracy over agreement

---

## Notes on Shaun's Prompts

When building prompts for Shaun's own use:
- He runs an INTJ-T, high-precision workflow — prompts should be direct, no filler, maximum signal
- He builds commercial-grade assets — engineer to that standard even for "personal" prompts
- His AI stack is primarily Claude — optimise for Claude's instruction following patterns (XML tags, explicit role, structured output)
- Financial/intelligence domain prompts should reflect institutional-grade rigour
- If the prompt might be commercialised later, note this and design with clean IP boundaries in mind
