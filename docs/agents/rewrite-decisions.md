# Rewrite decisions for Shaun

Fifteen first-generation skills were rewritten to `.agents/rewrite-standard.md`. Old versions are in git history (`git show <commit>~1:<path>`). Each rewritten skill has `evals/routing.md`; those checks are judged simulations, not live routing measurements.

Below are the calls that are yours. Nothing has been merged or deleted.

## Behaviour changes to confirm or revert

1. **multi-agent-designer**: the "never suggest a single agent when multi-agent would be superior" bias is gone. Step 1 now asks whether multi-agent is warranted.
2. **dispatch**: the Cerberus composite is the plain sum of the three lenses; the weights table now only decides which lens leads when they disagree. Confirm that matches your intent.
3. **vector**: honesty line applied. Dropped the Flinch (staged reaction). "Higher authority" only when the approver is real. BATNA signalled only when real. Anchors need a true rationale. Foot-in-the-door and reciprocity reworded to transparent versions. Pattern of life limited to public, professional information. "Strategic patience" had a heading and no content; a short act-now versus wait rule was written for it. Review that rule.
4. **cipher**: "Deliberate false statement" and feigned ignorance replaced with honest equivalents. False indicators, managed leaks, feints and cover stories dropped. Recommendation: leave them out.
5. **interactive-generator**: the Tailwind-only rule is dropped for a host-neutral `.jsx` or `.html` fallback.

## Wording added for you to approve

- **Cerberus disclaimer** (autonomous-writer `references/voices.md`, also referenced by dispatch): "General analysis only, not personal financial advice. Assumptions are stated; do your own checks before acting." Publishing market analysis in Australia can carry licensing obligations; confirm your position with an adviser.
- **No invented evidence**: autonomous-writer, deck-builder, generative-content and commercial-prompt-packager now refuse invented stats, testimonials, customers or results and leave `[needs source]` placeholders.
- **commercial-prompt-packager**: licence wording flagged as not legal advice; sole-trader tax and GST obligations to be checked with an accountant. Prices are still USD. Do you want AUD and GST guidance?
- **Untrusted input**: meta-prompt-engineer, multi-agent-designer and ai-power-user treat retrieved or user-supplied text as data, not instructions.

## Facts that need a currency check

Marked "as of <date>, verify before use" in `references/`:

- nexus `references/platforms.md`: Gemini, AI Studio, Replit, Perplexity and NotebookLM details (March 2026).
- dispatch: tool stack (n8n, Railway, Render, Telegram, Substack) and watchlists.
- ai-power-user `references/autonomy.md`: autonomy stack table (March 2026).
- commercial-prompt-packager: price tiers and licence tables.

## Possible merges (recommendation only)

| Skills | Overlap | Suggestion |
| --- | --- | --- |
| nexus, ai-power-user, meta-prompt-engineer | AI stack coaching and prompting | Keep separate for now; routing tables split them cleanly |
| dispatch day/week planning, heirloom-plan-capacity-week | Weekly planning | Keep; capacity-week needs a fixed hour budget |
| vector power mapping, cipher network mapping | Mapping people and influence | Keep; vector is strategy, cipher is relationships |
| generative-content, media-compiler, showpiece | Visual output | Candidate merge of generative-content into showpiece |
| interactive-generator, pocket-app, forge | Single-file tools | Candidate merge of interactive-generator into pocket-app |
| learning-visualiser, percept, atlas | Teaching visuals | Keep; percept is a course, atlas is a map |
