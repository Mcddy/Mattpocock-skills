---
name: autonomous-writer
description: "Writes finished long-form and professional copy for Shaun: articles, reports, Cerberus newsletter and Substack issues, sales copy, proposals, scripts, emails, LinkedIn posts, press releases, white papers, case studies and executive summaries. Use when he says 'write a', 'draft', 'write my newsletter', 'sales copy for', 'proposal for', 'write a report on', 'script for', 'LinkedIn post', 'Substack article', 'blog post', 'executive summary', or when a launch, offer or intelligence report needs accompanying copy. Not for editing or de-padding an existing draft (use deslop), evidence-led reports with citations and value bindings (folio), slide decks (deck-builder), UX microcopy, or the Cerberus analysis itself (dispatch)."
---

# autonomous-writer

Produces a finished piece of writing in the right voice for its reader: structured, specific and ready to publish or send. Format guides and voices are in `references/`.

## Use when

- The output is writing that will be published, sent or presented, beyond a conversational reply.
- A product, offer or Cerberus issue needs its copy written.
- A document is wanted at length: article, report, proposal, script, white paper, case study.

## Not this skill

| The request | Goes to |
|---|---|
| Tighten, de-pad or fix the voice of a draft that exists | deslop |
| Report built from results with citations, figures and update checks | folio |
| Slides or a pitch deck | deck-builder |
| Run the Cerberus three-lens analysis or score a trade | dispatch |
| Verify the factual claims in a piece | fact-check |

## Inputs

Establish these, inferring from context where possible and asking only the one question that most changes the draft:

1. Audience: who reads it, what they know, what they care about.
2. Goal: what they should think or do afterwards.
3. Voice: pick from `references/voices.md`; default is Shaun's business voice.
4. Format and length: see `references/formats.md` for the shape of each.
5. Constraints: platform, word limit, keywords, source material to use.

## Procedure

1. **Settle the inputs** above. If the source material is supplied, use it; do not substitute invented detail.
2. **Plan the structure before drafting.** Order is the argument: lead with the conclusion or the sharpest insight, then support it. Write the outline in one line per section.
3. **Draft in the format's shape** (`references/formats.md`). Prose rules: one idea per sentence, active voice, specific over general ("$47 a month", not "affordable"), short paragraphs with varied sentence length, no throat-clearing. Cut the first paragraph of a first draft and see if it still works.
4. **Run the four tests.** Skim (structure carries the message), cut (every paragraph and sentence is needed), reader (they know what to do or think at the end), voice (sounds like the intended voice, not generic AI output). Fix and repeat.
5. **Check claims.** Every number, name, quote and outcome comes from the supplied material or a source seen in this session. Where it does not, mark it `[needs source]` or `[placeholder]` rather than inventing it.
6. **Deliver.** Offer a headline or subject line, and one alternative angle or hook.

## Output

- Under about 500 words: inline in the reply.
- 500 to 2,000 words: a Markdown file, with the path given.
- Longer, or if he asks for it: a Markdown file, or a document file via the host's docx skill when available (fallback: Markdown).
- Always include the headline or subject line options and the alternative angle.

## Rules that always hold

- Write for the reader's needs, not the writer's comfort. Clarity beats impressiveness.
- No invented statistics, testimonials, case results or quotes. Use placeholders and say so.
- Cerberus pieces are analysis, not personal advice: state assumptions, give no position sizing for the reader, and keep the disclaimer line from `references/voices.md`. Publishing market commentary to the public may carry licensing obligations in Australia; that is Shaun's call to confirm.
- Australian spelling unless the audience is elsewhere.
- Ghost-written pieces for his name go out as his; flag anything that states a personal claim he has not confirmed.

## References

- `references/formats.md`: structure for each format (article, newsletter, sales copy, email, script, proposal).
- `references/voices.md`: Shaun's business voice, Cerberus voice, cold outreach, technical documentation.
