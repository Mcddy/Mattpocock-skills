---
name: nexus
description: >
  NEXUS — the complete doctrine for commanding the full AI stack. Integrates Claude power use, multi-agent pipeline design, Gemini Canvas, Google AI Studio, Replit, Perplexity, NotebookLM, deep research orchestration, and cross-platform prompt engineering. Use whenever Shaun wants to maximise any AI tool, design multi-agent systems, build autonomous pipelines, engineer prompts, or operate at the frontier of AI capability. Trigger on: "how do I get Claude to...", "design an agent", "build this in Replit", "Gemini Canvas", "AI Studio prompt", "Perplexity query", "NotebookLM", "multi-agent pipeline", "prompt for [model]", "make this autonomous", or any task requiring maximum AI leverage. NEXUS is the command and control centre.
---

# NEXUS
## The Complete Doctrine for Commanding the Full AI Stack

Integrates: Claude Power User · Multi-Agent Designer · AI Power User · Gemini Canvas · Google AI Studio · Replit Builder · Perplexity Intelligence · NotebookLM Synthesiser · Deep Research Orchestrator · Prompt Stack Engineer · Meta Prompt Engineer · Commercial Prompt Packager

> ⚠️ **Model currency note**: This skill was last updated March 2026. Always verify current model IDs at platform docs before deploying to production.

---

## Operating Principle

**AI is not a tool to be used — it is a force to be commanded.**

The difference between a user and a sovereign: users accept what the AI gives them. Sovereigns engineer what the AI produces. This doctrine covers the full stack — from raw prompts to autonomous multi-agent systems — and applies frontier-level techniques to every interaction.

**Mode detection:**
| Task | Module |
|------|--------|
| Get Claude to reason deeper | → Claude Power Use |
| Build multi-agent system | → Multi-Agent Designer |
| Build in Gemini Canvas | → Gemini Canvas |
| Build with Gemini API / AI Studio | → Google AI Studio |
| Build and deploy in Replit | → Replit Builder |
| Real-time web intelligence | → Perplexity Intelligence |
| Synthesise document collections | → NotebookLM |
| Multi-tool research campaign | → Deep Research Orchestrator |
| Engineer a prompt for any model | → Prompt Stack Engineer |
| Build a prompt from scratch | → Meta Prompt Engineer |
| Package a prompt commercially | → Commercial Prompt Packager |

---

## MODULE 1: Claude Power Use

### Current Claude Models (March 2026)
| Model | API String | Use Case |
|-------|-----------|----------|
| Claude Opus 4.6 | `claude-opus-4-6` | Most complex tasks, deep reasoning, long-horizon agents |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Frontier intelligence at scale, coding, enterprise workflows |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Fast, cost-efficient, near-frontier performance |

> ⚠️ **Retired/avoid**: All 3.x models retired. claude-sonnet-3-5 (retired), claude-haiku-3-5 (retired Feb 2026).

### Coach Assessment (evaluate any AI workflow on 5 axes)
| Axis | Question | Upgrade if low |
|------|----------|----------------|
| Autonomy | Could this run without Shaun? | Add triggers, decision rules, fallback logic |
| Depth | Is Claude reasoning deeply or pattern-matching? | Add reasoning scaffolds |
| Pipeline maturity | One-shot when pipeline is better? | Redesign as staged |
| Resilience | What happens when inputs fail? | Validation gates, error handling |
| Compounding | Does this improve over time? | Memory, logging, feedback loops |

### Depth Techniques

**Extended Thinking:**
```
Before answering, reason through this exhaustively inside <thinking> tags.
Consider: [angles]. Challenge your own assumptions. Then give your final answer.
```

**Adversarial Self-Review:**
```
Now argue against your own answer. Strongest objections? Assumptions that could be wrong?
```

**Hypothesis-Evidence Mode:**
```
Generate 3 competing hypotheses that explain [observation].
For each: what confirms it, what falsifies it, probability estimate and why.
```

**Metacognitive Flags:**
```
Flag assumptions: [ASSUMPTION]
Flag uncertainty: [UNCERTAIN: reason]
Flag pattern-matching vs reasoning: [HEURISTIC]
```

**Iterative Densification:**
Pass 1: Ideas. Pass 2: Cut everything that doesn't add new information. Pass 3: Tighten every sentence to its most precise form. Instruct Claude to run all three before returning.

**Constitutional Hierarchy:**
```
When goals conflict, prioritise:
1. Accuracy above all
2. Actionability over completeness
3. Brevity over comprehensiveness
4. Directness over diplomacy
```

**Output Schemas (control layer):**
```xml
<analysis>
  <verdict>string</verdict>
  <confidence>0-100</confidence>
  <key_finding>string</key_finding>
  <evidence_quality>HIGH|MEDIUM|LOW</evidence_quality>
  <next_action>string</next_action>
</analysis>
```

**Agentic Delegation Language:**
```
Work autonomously. Make decisions where you can.
Only pause if: (a) irreversible, (b) ambiguous on direction, or (c) outside scope.
Proceed and document decisions inline.
```

---

## MODULE 2: Multi-Agent Designer

### Pipeline Patterns

**Sequential Chain:**
```
Input → Extract → Analyse → Synthesise → Output
Risk: error propagation → Fix: validation gate between stages
```

**Parallel Fan-Out / Fan-In:**
```
Input → [Agent A] [Agent B] [Agent C] → Synthesiser → Output
Best for: Cerberus three-lens (run all in parallel, synthesise last)
```

**Critic-Reviser Loop:**
```
Generator → Critic → [score ≥ threshold?] → Reviser → Output
Max iterations: 3-5 (always set a limit)
```

**Router + Specialist:**
```
Input → Router (classify intent) → [Specialist A / B / C] → Output
```

**Memory-Augmented:**
```
Input → Retrieve memory → Act with context → Output + Update memory
```

### Implementation (parallel async)
```python
import asyncio, anthropic
client = anthropic.Anthropic()

async def run_parallel_agents(task: str) -> dict:
    results = await asyncio.gather(
        run_agent_async("macro_analyst", task),
        run_agent_async("technical_analyst", task),
        run_agent_async("sentiment_analyst", task)
    )
    return synthesise_cerberus_brief(*results)
```

**API call pattern (current SDK):**
```python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",  # or claude-opus-4-6 for heaviest tasks
    max_tokens=4096,
    messages=[{"role": "user", "content": task}]
)
```

### Orchestrator System Prompt
```
You are an orchestrator. Given a task, respond JSON only:
{
  "specialists": ["list to activate"],
  "context": "relevant context for each",
  "synthesis_instruction": "how to merge outputs"
}
```

### Critic Agent System Prompt
```
Evaluate the draft. Respond JSON only:
{
  "score": 0-10,
  "strengths": [],
  "weaknesses": [],
  "specific_fixes": [],
  "should_revise": true/false
}
```

### Cross-Model Orchestration
```python
def cross_model_pipeline(task):
    live_data = perplexity_search(f"{task} — latest developments, current data")
    doc_analysis = gemini_analyze(documents, task) if len(documents) > 100000 else claude_analyze(documents, task)
    return claude_synthesize(task=task, live_data=live_data, doc_analysis=doc_analysis)
```

### Deployment Checklist
- [ ] One agent, one job
- [ ] JSON between agents, not prose
- [ ] Every call wrapped in try/except
- [ ] Max iteration limits on all loops
- [ ] All intermediate outputs logged
- [ ] Human checkpoint before irreversible actions
- [ ] Tested with adversarial/malformed inputs

---

## MODULE 3: Prompt Stack Engineer

### Model Prompt Profiles

**Claude (Anthropic) — use XML tags:**
```xml
<s>
You are [specific expert role].
<context>[Background]</context>
<primary_task>[What to do]</primary_task>
<output_format>[Exact specification]</output_format>
<constraints>[What NOT to do]</constraints>
Priority when goals conflict: 1. Accuracy 2. Actionability 3. Brevity 4. Directness
</s>
```

**Gemini (Google) — use Markdown headings:**
```
## Role
[Expert role]
## Context
[Background]
## Task
1. [Step 1]
2. [Step 2]
## Output Format
[Schema or specification]
## Constraints
- [Constraint 1]
```

**GPT-4o — concise, direct:**
```
You are a [role]. [One-sentence context].
Your job: [Task in 1-2 sentences]
Output format: [Specification]
Rules: [2-3 bullet rules]
```

**Perplexity — timeframe + source spec + structure:**
```
[Topic] — intelligence brief as of [timeframe]:
- [Specific question 1]
- [Specific question 2]
Include publication dates. Prioritise [source types].
Flag single-source claims.
```

### Cross-Platform Porting
- **Claude → Gemini**: Replace XML tags with ## headings / "Use Google Search to verify" / simplify hierarchy
- **Claude → GPT-4o**: Reduce verbosity / remove XML / consolidate constraints to bullets
- **GPT-4o → Claude**: Add XML structure / expand output spec / add reasoning scaffold

### Meta Prompt Engineering Loop
1. **Intake**: Plain language intent OR rough draft analysis
2. **Structural design**: System / task / chain / meta / hybrid?
3. **Draft**: Write with role precision, XML tagging, output forcing, CoT scaffold, self-critique
4. **Critique** (internal, before showing): Clarity audit / Coverage audit / Tone audit / Power audit
5. **Present**: Clean prompt + key decisions explained + failure modes flagged
6. **Iterate**: Never stop at one draft unless explicitly done

### Prompt Quality Rubric
| Criterion | Check |
|-----------|-------|
| Role specificity | Is the role precise and domain-specific? |
| Task clarity | Would two readers produce the same output? |
| Output spec | Is the format unambiguous? |
| Constraint coverage | Are edge cases handled? |
| Model optimisation | Using this model's specific strengths? |
| Failure handling | What happens with bad inputs? |
**Minimum: 4/5 on all axes before production.**

---

## MODULE 4: Gemini Canvas Architect

### Blueprint Template
```
CANVAS BLUEPRINT: [name]
TYPE: Interactive Document / Web App / Code + Explanation / Data Report / Research Synthesis
PRIMARY OUTPUT: [Final state of the canvas — what done looks like]
COMPONENTS: [1. component — purpose / 2. ...]
INTERACTIVITY: Static / User inputs / Dynamic data / Multi-section navigation
DATA: AI-generated / User-provided / External
MODEL: gemini-2.5-flash (speed/default) / gemini-2.5-pro (complex reasoning) / gemini-3.1-pro-preview (frontier)
```

### Master Canvas Prompt
```
Create a [type] in Canvas for [purpose].

STRUCTURE:
- Section 1: [name and description]
- Section 2: [name and description]

REQUIREMENTS:
- [requirement 1]

INTERACTIVITY:
- [what user can interact with]

OUTPUT FORMAT:
- [how the final canvas should be organised]
```

### Optimisation Techniques
- **Structure-first**: Establish skeleton before content — "First, create the structure with these sections: [list]"
- **Iterative deepening**: "Expand section 2 with [X]. Keep all other sections unchanged."
- **Component isolation**: Build complex apps component by component and integrate after review

---

## MODULE 5: Google AI Studio Engineer

### Current Gemini Models (March 2026)
| Use Case | Model ID | Notes |
|----------|----------|-------|
| Default / general | `gemini-2.5-flash` | Best price-performance, reasoning capable |
| Complex reasoning + coding | `gemini-2.5-pro` | Frontier reasoning, 1M context |
| Frontier agentic / coding | `gemini-3.1-pro-preview` | Latest generation, preview |
| High-volume / low-latency | `gemini-2.5-flash-lite` | Cheapest capable model |
| Real-time grounding | `gemini-2.5-flash` or `gemini-3.1-pro-preview` | Use with google_search tool |
| Embeddings | `text-embedding-005` | Note: text-embedding-004 retired Jan 2026 |

> ⚠️ **Retired/avoid**: gemini-1.5-pro, gemini-1.5-flash (both retired), gemini-2.0-flash (retiring June 2026 — migrate to gemini-2.5-flash-lite), gemini-3-pro-preview (shut down March 9 2026 — use gemini-3.1-pro-preview).

### SDK: Use google-genai (NOT google-generativeai)
The legacy `google-generativeai` library is deprecated as of Nov 2025. Always use `google-genai`:

```python
# Install: pip install google-genai
from google import genai
from google.genai import types

client = genai.Client()  # uses GEMINI_API_KEY env var automatically
```

### JSON Mode (structured output)
```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Analyse this trade setup: [details]",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["BUY","SELL","HOLD","WAIT"]},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "key_risk": {"type": "string"}
            },
            "required": ["verdict", "confidence", "key_risk"]
        }
    )
)
```

### Grounded Generation (current SDK syntax)
```python
from google import genai
from google.genai import types

client = genai.Client()

# Correct — uses new google-genai SDK
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="[your query]",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)
print(response.text)
# Access grounding: response.candidates[0].grounding_metadata.web_search_queries
```

### Claude vs Gemini Routing
| Use Claude | Use Gemini |
|-----------|-----------|
| Deep reasoning / instruction following | Multimodal (images/video/audio) |
| Complex agentic tasks | Long context (>200k tokens) |
| Prompt engineering precision | Native Python execution |
| | Real-time search grounding |

---

## MODULE 6: Replit Builder

### Replit Agent Prompt Template
```
Build a [type] application:

NAME: [name]
PURPOSE: [one sentence]

STACK:
- Language: [Python/JavaScript/TypeScript]
- Framework: [FastAPI/Flask/Express/Next.js]
- Database: [None/Replit DB/PostgreSQL]

FEATURES:
1. [specific feature with behaviour]
2. [feature]

INTERFACE: [UI description or: API only / CLI / background service]

API ENDPOINTS:
- GET /[endpoint] — [returns]
- POST /[endpoint] — [accepts and returns]

DATA MODEL:
- [entity]: [fields]

ENVIRONMENT VARIABLES:
- [VAR_NAME]: [purpose]

Make production-ready with error handling, well-commented, include README.
```

### Deployment Patterns
```
Always-on API: FastAPI + /health endpoint + Replit Deployments
Scheduled pipeline: Python + APScheduler + DB logging + Replit Scheduled Tasks
Full-stack: React + Express/FastAPI + PostgreSQL + Replit Deployments
Bot: python-telegram-bot + keep-alive + Replit Deployments
```

### Production Checklist
- [ ] All credentials in Replit Secrets
- [ ] /health endpoint
- [ ] Error handling with meaningful messages
- [ ] Rate limiting if internet-facing
- [ ] Database connection pooling (PostgreSQL)
- [ ] README with setup

---

## MODULE 7: Perplexity Intelligence

### Current Perplexity API Models (March 2026)
| Model | ID | Best For |
|-------|----|----------|
| Sonar | `sonar` | Fast Q&A, lightweight search, 128k context |
| Sonar Pro | `sonar-pro` | Deep multi-step queries, 200k context, 2x citations |
| Sonar Reasoning Pro | `sonar-reasoning-pro` | Chain-of-thought + web search, complex analysis |
| Sonar Deep Research | `sonar-deep-research` | Exhaustive reports, hundreds of sources, async jobs |

> ⚠️ **Retired/avoid**: `llama-3.1-sonar-large-128k-online` (old model string — use `sonar-pro` instead)

### Query Engineering Formula
```
[Specific scope] + [Timeframe] + [Output requirement] + [Perspective filter]

BAD: "gold price"
GOOD: "Gold futures price action and institutional positioning — last 24 hours.
       Key technical levels and major news catalysts. Primary sources only."
```

### Query Templates
```
MARKET: [Asset] — current status: price action last [X] / key levels / news catalysts / positioning / consensus. Sources from last [Y].

MACRO: [Country] economic conditions: latest data releases / central bank posture / market pricing of next move / key risks.

TECHNOLOGY: [Tool/model] current state: recent changes / real-world use cases confirmed / known limitations / expert consensus.
```

### Deep Research Prompt
```
RESEARCH TOPIC: [precise]
OBJECTIVES:
1. [What to understand]
2. [Specific questions]
3. [Decision this informs]
SCOPE: [Time period / geographic focus / perspective]
EXCLUDE: [Noise to filter]
OUTPUT: Executive summary first / structured sections / source quality / gaps / uncertainties
```

### Perplexity → Claude Pipeline
1. Run Deep Research on Perplexity (use `sonar-deep-research` for exhaustive reports, `sonar-reasoning-pro` for analytical depth)
2. Copy full output
3. Feed to Claude: "Here is a Perplexity Deep Research output on [topic]. Apply [three-lens/hypothesis-evidence/framework]. Produce structured assessment with confidence ratings."

### API Integration (current model strings)
```python
def perplexity_search(query: str, recency: str = "week", model: str = "sonar-pro") -> dict:
    return httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"},
        json={
            "model": model,  # sonar | sonar-pro | sonar-reasoning-pro | sonar-deep-research
            "messages": [{"role": "user", "content": query}],
            "return_citations": True,
            "web_search_options": {"search_context_size": "high"},  # low | medium | high
            "search_recency_filter": recency  # day | week | month | year
        }
    ).json()
```

---

## MODULE 8: NotebookLM Synthesiser

**One notebook = one intelligence domain. Focused > comprehensive.**

### Source Selection
- Tier 1: Primary research, official documents (highest)
- Tier 2: Authoritative analysis, institutional research
- Include contrarian views for balanced synthesis
- Target: 10-20 focused sources > 50 unfocused

### Query Templates
```
SYNTHESIS: "Synthesise key arguments across all sources on [question]. Where do sources agree/conflict? Strongest supported conclusion?"

EXTRACTION: "From all sources, extract every piece of data about [metric]. Structured list with source attribution."

GAP ANALYSIS: "What important questions about [topic] remain unanswered? What additional sources would fill critical gaps?"

THESIS TEST: "I believe [thesis]. What evidence supports this? What challenges it? What is the balance?"
```

### Audio Overview Optimisation
```
Customise prompt: "Focus on [specific angle]. Key questions: [1-3]. Target audience: [technical expert / intelligent non-specialist]. Tone: analytical and direct."

Intelligence Brief Format: "Structure as: Situation summary / Key drivers / Implications / Key uncertainties. Direct and analytical."
```

### NotebookLM → Claude Pipeline
NotebookLM produces source-grounded synthesis → Claude applies reasoning frameworks → combined output is more powerful than either alone.

---

## MODULE 9: Deep Research Orchestrator

### Multi-Tool Campaign Architecture
```
TIER 1 — PERPLEXITY (real-time, source-cited):
sonar-pro: current state / recent developments / key data points
sonar-deep-research: comprehensive reports requiring 100s of sources (async)
sonar-reasoning-pro: analytical depth with CoT over web results

TIER 2 — NOTEBOOKLM (document synthesis):
Load authoritative sources from Tier 1 / Run synthesis queries / Extract structured intelligence

TIER 3 — GEMINI or CLAUDE (long-context or reasoning):
Gemini 2.5-pro: if document set >200k tokens
Claude Opus 4.6: for framework application, deep hypothesis testing
Claude Sonnet 4.6: for structured synthesis at scale

TIER 4 — CLAUDE (final synthesis):
Apply frameworks / Confidence ratings / Structured output / Actionable recommendations
```

### Quality Gates
```
TIER 1 GATE: Core question answered with primary evidence? Key developments captured? Conflicts identified?
TIER 2 GATE: Adds to Tier 1 (not repeating)? Source quality adequate? Major gaps identified?
TIER 3 GATE: Framework applied correctly? Confidence levels assigned? Actionable conclusion reachable?
```

### Final Synthesis Prompt
```
Synthesising multi-source research campaign.

SOURCES: [Perplexity intelligence] [NotebookLM synthesis] [Additional data]

TASK:
1. Five most important findings across sources
2. Contradictions between sources
3. Apply [framework]
4. Structured output: Executive summary / Key findings (with confidence) / Uncertainties / Recommended action / What would change this

Rate overall confidence: HIGH / MEDIUM / LOW
```

---

## MODULE 10: Commercial Prompt Packager

### Pricing Framework
| Tier | Price Range | Includes |
|------|-------------|---------|
| Entry/Solo | $9-$29 | Prompt file + basic guide |
| Pro/Professional | $49-$149 | Prompt + docs + examples + setup |
| Enterprise/Full Kit | $197-$497 | Everything + customisation + commercial licence |
| Bespoke/Custom | $500-$2,500+ | White-glove adaptation |

**Always 3-tier minimum. Single-price leaves money on the table.**

### Sales Copy Structure
1. Headline (outcome, not mechanism — 8-12 words)
2. Subheadline (who it's for, what changes)
3. Problem/Pain (name the pain before finding this)
4. Solution (what it does at high level)
5. What's Included (specific per tier)
6. Who This Is For (3-5 specific buyer profiles)
7. CTA (direct: "Get the Pro Kit — $97")

### Licence Types
- Personal Use: Own projects only, no resale or client use
- Commercial Use: Client work and business, no resale of prompt
- Extended Commercial: Full commercial including products, no redistribution
- White-Label/OEM: Rebrand and resell — highest price

### Technical Documentation Template
```
# [Prompt Name] — Technical Docs
## Overview / Recommended Model / Deployment Context
## Required Inputs / Output Description / Configuration Options
## Usage Examples (2-3 input/output pairs)
## Known Limitations / Version
```

**Cerberus branding (when selected):** "A Cerberus Market Intelligence Asset" / "Engineered to institutional-grade specifications" / Three-lens framework reference as credibility signal.

---

## Stack Architecture (Shaun's AI Operating System)

```
DATA LAYER:        Perplexity (real-time) + NotebookLM (documents)
REASONING LAYER:   Claude Opus/Sonnet 4.6 (primary) + Gemini 2.5 Pro (long-context/multimodal)
BUILD LAYER:       Replit (deploy) + AI Studio (Gemini API via google-genai SDK)
CANVAS LAYER:      Gemini Canvas (interactive documents)
PIPELINE LAYER:    Multi-agent (Claude API) + async Python
PRODUCT LAYER:     Prompt library + Commercial packaging
```

**Cross-model routing rule (current as of March 2026):**
- Deep reasoning, complex agentic tasks, instruction-following precision → Claude Sonnet 4.6 / Opus 4.6
- Multimodal, 200k+ tokens, native Python execution, live search grounding → Gemini 2.5 Pro / Flash
- Real-time intelligence, current data → Perplexity (sonar-pro or sonar-reasoning-pro)
- Exhaustive multi-source research → Perplexity sonar-deep-research
- Document synthesis from loaded sources → NotebookLM
- Fast deploy and prototype → Replit
- Cost-optimised high-volume tasks → Claude Haiku 4.5 or Gemini 2.5 Flash-Lite
