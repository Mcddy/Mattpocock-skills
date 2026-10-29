# Depth, synthesis and control prompts

Pick one or two per job. Stacking all of them wastes tokens. Wording is a starting point; tune it. Use the host's native extended-reasoning setting where one exists.

## Reasoning depth

- **Extended reasoning.** "Before answering, reason through this exhaustively inside <thinking> tags. Consider <angles>. Challenge your own assumptions. Then give your final answer."
- **Adversarial self-review** (high-stakes outputs). "Now argue against your own answer. What are the strongest objections? Which assumptions could be wrong?"
- **Hypothesis and evidence** (research, intelligence). "Generate 3 competing hypotheses that explain <observation>. For each: what confirms it, what falsifies it, current probability estimate and why."
- **Metacognitive flags.** Tag assumptions [ASSUMPTION], doubts [UNCERTAIN: reason], and pattern-matching rather than reasoning [HEURISTIC].
- **Calibrated uncertainty** (always for research outputs). "For each claim rate confidence High, Medium or Low. Flag anything to verify before acting on it."
- **Iterative densification.** Pass 1 get the ideas; pass 2 cut everything that adds no new information; pass 3 tighten every remaining sentence. Ask for all three passes before it returns.
- **Priority order for conflicts.** For example: accuracy, then actionability over completeness, then brevity over comprehensiveness, then directness over diplomacy.

## Control layer

- **Output schema.** Fix the answer's shape so it is parseable:
  ```xml
  <analysis>
    <verdict>string</verdict>
    <confidence>0-100</confidence>
    <key_finding>string</key_finding>
    <evidence_quality>HIGH | MEDIUM | LOW</evidence_quality>
    <next_action>string</next_action>
  </analysis>
  ```
- **Role and counterrole.** "First respond as an optimistic analyst. Then respond as a sceptical risk officer critiquing the first. Synthesise both."
- **Delegation language.** "Work autonomously and decide where you can. Pause only if the action is (a) irreversible, (b) ambiguous on direction, or (c) outside scope. Proceed and document decisions inline."
- **Context window as working memory.** Load full documents, not summaries; keep a running analysis log within a session; feed prior-session summaries back as a header.

## Research and synthesis pipeline

| Tier | Job | Autonomy |
|---|---|---|
| 1 Ingestion | Sources (RSS, APIs, document drops, web monitoring): extract, clean, tag, store as structured entries | Fully autonomous |
| 2 Analysis | Per-document analysis against a fixed rubric: relevance score, key claims, evidence quality, links to existing knowledge; flag items for tier 3 | Autonomous with quality gates |
| 3 Synthesis | Cross-source patterns on a schedule or threshold; fan-out per source cluster, one synthesiser across all; output a structured brief | Triggered |
| 4 Human review | Only items over a relevance or urgency threshold surface; the rest are logged, not surfaced | Exceptional cases |

## Synthesis quality

- **Perspective stacking.** "Analyse across <lens 1>, <lens 2>, <lens 3>. Where do they agree? Conflict? What does the tension reveal?"
- **Socratic pre-brief** (underdefined questions). "Do not answer yet. Ask the 5 most important questions you would need answered to give the best possible response. Then answer them yourself."
- **Cross-model comparison.** Run the same synthesis prompt on two models. Where outputs diverge, treat it as real uncertainty and investigate before acting.
- **Knowledge-graph tagging.** Tag and connect every output, not just store it: domain, date, confidence, connected topics, source quality, and contradicts, supports or extends <existing finding>. This compounds into a personal intelligence layer.

## Self-improving pipelines

Log every run: input, output, quality score, failure points. Periodically ask: "Review these runs. What patterns explain failures? What would improve quality?" Use the answer to revise the pipeline prompt.
