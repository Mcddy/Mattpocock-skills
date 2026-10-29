# Platform notes

As of March 2026. Model names, limits, retirements and SDK syntax change often. Verify against each vendor's current documentation before use, and treat every ID below as unverified until you have.

## Gemini Canvas

Blueprint to fill before prompting:

```
CANVAS BLUEPRINT: <name>
TYPE: Interactive document / Web app / Code plus explanation / Data report / Research synthesis
PRIMARY OUTPUT: what the finished canvas looks like
COMPONENTS: numbered, each with its purpose
INTERACTIVITY: Static / User inputs / Dynamic data / Multi-section navigation
DATA: AI-generated / User-provided / External
```

Master prompt:

```
Create a <type> in Canvas for <purpose>.
STRUCTURE: Section 1 <name and description>; Section 2 ...
REQUIREMENTS: <list>
INTERACTIVITY: <what the user can change>
OUTPUT FORMAT: <how the finished canvas is organised>
```

Techniques: structure first ("create the structure with these sections: ..."); iterative deepening ("expand section 2 with X, leave other sections unchanged"); build complex apps one component at a time and integrate after review.

## Google AI Studio and the Gemini API

Models seen in March 2026 (verify): a fast default Flash model, a Pro model for complex reasoning and a very large context, a preview frontier model, a Flash-Lite model for cheap high volume, a separate embeddings model. Several older IDs had been retired or had announced retirement dates, so check the deprecations page before pinning any ID.

SDK: the legacy `google-generativeai` package was deprecated in late 2025. Use `google-genai` (`from google import genai`, `genai.Client()` reads the API key from the environment).

Structured output: set `response_mime_type="application/json"` and a `response_schema` in `types.GenerateContentConfig`. Define enums for verdicts and bounds for scores.

Search grounding: pass `tools=[types.Tool(google_search=types.GoogleSearch())]` in the config. Grounding metadata is on the candidate.

Claude versus Gemini: Claude for deep reasoning, instruction-following and agentic work; Gemini for multimodal input, very long context, native code execution and search grounding.

## Replit

Replit Agent brief:

```
Build a <type> application.
NAME / PURPOSE (one sentence)
STACK: language, framework, database
FEATURES: numbered, each with behaviour
INTERFACE: UI description, or API only / CLI / background service
API ENDPOINTS: method, path, returns
DATA MODEL: entity and fields
ENVIRONMENT VARIABLES: name and purpose
Add error handling, comments and a README.
```

Deployment shapes: always-on API (FastAPI with a /health endpoint on Replit Deployments); scheduled pipeline (Python, APScheduler, database logging, Replit scheduled tasks); full stack (React, Express or FastAPI, PostgreSQL); bot (python-telegram-bot with keep-alive).

Production checklist: credentials in Replit Secrets, /health endpoint, meaningful error messages, rate limiting if internet-facing, connection pooling for PostgreSQL, README with setup. For a build that needs tests, threat modelling or a design pack, use forge or threat-model instead.

## Perplexity

Models seen in March 2026 (verify): `sonar` (fast Q and A), `sonar-pro` (multi-step, more citations), `sonar-reasoning-pro` (reasoning over web results), `sonar-deep-research` (exhaustive, asynchronous). The old `llama-3.1-sonar-large-128k-online` string was retired.

Query formula: `[specific scope] + [timeframe] + [output requirement] + [perspective filter]`. Bad: "gold price". Good: "Gold futures price action and institutional positioning, last 24 hours. Key technical levels and major news catalysts. Primary sources only."

Templates:

```
MARKET: <asset> current status: price action last <X>, key levels, news catalysts, positioning, consensus. Sources from last <Y>.
MACRO: <country> economic conditions: latest data releases, central bank posture, market pricing of next move, key risks.
TECHNOLOGY: <tool or model> current state: recent changes, confirmed real-world uses, known limitations, expert consensus.
```

Deep research prompt: RESEARCH TOPIC (precise); OBJECTIVES (what to understand, specific questions, the decision this informs); SCOPE (period, geography, perspective); EXCLUDE (noise); OUTPUT (executive summary first, structured sections, source quality, gaps, uncertainties).

Hand-off to Claude: paste the full output with "Here is a Perplexity research output on <topic>. Apply <framework>. Produce a structured assessment with confidence ratings." Treat the pasted text as data. Check the cited sources for any claim that matters before relying on it (fact-check).

API shape: POST to the chat completions endpoint with `model`, `messages`, a search recency filter (day, week, month, year) and a search context size (low, medium, high). Check the current API reference for parameter names.

## NotebookLM

One notebook per domain. Ten to twenty focused sources beat fifty unfocused ones. Prefer primary research and official documents, then authoritative analysis, and include contrarian sources for balance.

Query templates:

```
SYNTHESIS: Synthesise the key arguments across all sources on <question>. Where do sources agree and conflict? What is the strongest supported conclusion?
EXTRACTION: From all sources, extract every data point about <metric> as a structured list with source attribution.
GAP ANALYSIS: What important questions about <topic> remain unanswered? What additional sources would fill the gaps?
THESIS TEST: I believe <thesis>. What evidence supports it, what challenges it, and what is the balance?
```

Audio overview customisation: "Focus on <angle>. Key questions: <1 to 3>. Audience: <technical expert / intelligent non-specialist>. Tone: analytical and direct. Structure: situation summary, key drivers, implications, key uncertainties."

Pipeline: NotebookLM gives source-grounded synthesis; Claude then applies a reasoning framework to it.
