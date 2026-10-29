---
name: "fact-check"
description: "Verifies supplied drafts claim by claim against observed sources, optionally using a blind checker or requested cross-model second opinion. Returns a sourced FACT / ASSESSMENT / GAP ledger, retains material source conflicts and corrects supported errors. Use when asked to fact-check or verify a draft before sending. Research from scratch and dataset calculation checks are separate workflows."
---

# fact-check

Checks a finished text one claim at a time. The checker answers neutral questions from sources without seeing the draft, because a reviewer who has read the draft tends to agree with it.

## Use when

- The user asks to fact-check, verify or double-check a draft, answer or report.
- The user asks whether pasted text is true, or wants a check before something is sent.
- The user wants a second opinion from another model, judged blind.

## Not this skill

| The request | Goes to |
|---|---|
| Research a topic from scratch | deep-research-orchestrator |
| Check the calculations or query logic in an analysis | replicate-lab, or a data-validation skill if installed |
| Weigh competing explanations of a live situation | intelligence-analyst |
| Judge whether one study's design supports its conclusion | paper-audit |
| Referee a whole study or paper | referee-panel |
| Critique a design or a screen | anti-vibecoded-ui |
| Remove AI tells from prose | deslop |

## Inputs

The exact text to check. Freeze it: no silent edits while checking.

## Tools

Check what this session has: web search and fetch, file reading, a way to start a separate agent or fresh context, access to another model family. The procedure names a fallback for each one that is missing.

## Procedure

1. **Extract claims.** Split the text into atomic, checkable claims and number them. Type each: quantity, quote or attribution, date or event, cause, present-tense status, definition. List opinions and predictions separately as not checkable.
2. **Write one question per claim** that does not leak the draft's answer. "What was the unemployment rate in March?" and never "Was it 4.1%?"
3. **Answer blind.** Give only the numbered questions and the source tools to a separate agent or fresh context. If the session cannot start one, answer every question from sources before reading the draft again, and label the run `single-context` in the output.
4. **Source rule.** Every answer carries a source seen in this session (a URL, a file, a tool result) or it is a GAP. Present-tense claims (prices, roles, versions, law, availability) must be looked up. Without a lookup tool they are GAP, never FACT from recall.
5. **Adjudicate disagreements.** Resolve material conflicts using source quality, dates, definitions and direct primary evidence. Independent passes can expose errors but a majority vote does not establish truth. Retain material conflicts in the ledger even after resolution: identify both sources, their disagreement and the reason one carries more weight. Record unresolved conflicts as GAP or a qualified ASSESSMENT.
6. **Compare** each answer with its claim: SUPPORTED, CONTRADICTED, UNSUPPORTED or NOT CHECKABLE.
7. **Cross-model mode,** when the user asks for a second opinion. Compile a sealed brief: the questions, the evidence gathered and a scoring rubric, with no draft answers and no model names. Carry it to a different model family with whatever tool the session has, or hand it to the user to paste. When answers return, strip the labels, shuffle the order, score each against the rubric, and send every disagreement back through step 3. A second opinion from the same model family is not a cross-model check: say so.
8. **Correct.** Produce the corrected draft, changing only what the ledger supports.

## Output

1. A ledger table: number, claim, verdict, tag (FACT with source, ASSESSMENT with confidence, or GAP), source, note.
2. Counts: supported, contradicted, unsupported, not checkable.
3. The corrected draft with each change marked.
4. Not checked: what could not be verified and why. State whether the run was blind or `single-context`.

## Rules that always hold

- Nothing is tagged FACT without a source seen in this session.
- A contradiction is reported plainly, never softened.
- The corrected draft changes facts only. Style is out of scope.
- Different models often share the same errors, so agreement between models is weaker evidence than a primary source.

## QA provenance

Acceptance cases and inert adversarial fixtures are retained in the canonical source library, separate from this runtime package. Script checks do not establish live skill routing or model quality. Routing table revised on 22 October 2026 to name installed skills instead of generic or plugin-only targets; not yet routing-tested.