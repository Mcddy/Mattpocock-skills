---
name: deck-builder
description: "Builds a real PowerPoint file (.pptx) with a narrative spine, one claim per slide and consistent layout, or converts a report or notes into a deck. Use when he says 'build me a deck on', 'create a presentation about', 'make slides for', 'pitch deck', 'investor deck', 'briefing deck', 'workshop slides', 'training materials', 'create a PowerPoint', or hands over a document to turn into slides. Not for slides as a web page (use showpiece), posters or static art (canvas-design), a written report (folio or autonomous-writer), or editing a deck's wording only (deslop)."
---

# deck-builder

Produces a .pptx file whose slides follow a story and each make one point, plus a one-line-per-slide summary. Narrative templates and the python-pptx recipe are in `references/`.

## Use when

- A slide deck, pitch, briefing or training pack is wanted as a file.
- A report, notes or an outline needs converting to slides.

## Not this skill

| The request | Goes to |
|---|---|
| An interactive or web-based presentation page | showpiece |
| A poster or single static visual | canvas-design |
| An evidence-led written report or poster with citations | folio |
| Write the narrative copy or speaker script as prose | autonomous-writer |
| Fix wording on existing slides without rebuilding | deslop |

## Inputs

1. Purpose: inform, persuade, sell, teach or brief.
2. Audience: investors, executives, clients, class, team, public.
3. Delivery: presented live, or read alone (read-alone decks need more text per slide).
4. Length: slide count; default 10 to 15.
5. Source material: notes, report or bullets. If none, ask for it or state that content is drafted from stated assumptions.
6. Tone and branding: colours, fonts, logo. Defaults in `references/build.md`.

Ask only for what is missing and changes the deck.

## Procedure

1. **Choose the narrative spine** from `references/narratives.md` (pitch, executive briefing, educational, investor) and write the slide list as one claim-headline per slide before building anything.
2. **Design each slide to the rules:** one idea per slide; the headline states a claim ("Market growing 40% a year with no dominant player", not "Market analysis"); at most 5 bullets of at most 7 words each, otherwise split the slide; one chart per slide with a conclusion as its title, labelled axes and a source; hierarchy of title, body, callout, footnote. Slide types to draw on: title, section divider, statement, three-up, data, quote, timeline, comparison.
3. **Build the file.** If the host has a pptx file skill, use it for file mechanics. Otherwise use python-pptx as set out in `references/build.md`. Use real layouts and placeholders, a consistent font stack, 16:9.
4. **Check the file.** Reopen it, confirm the slide count, that no placeholder or lorem text remains, and that no text overflows a box. Render to images if a renderer is available and look at them; if not, say the visual check was not done.
5. **Deliver** the file with a one-line-per-slide summary, a list of slides that need real images, client data or live charts, and an offer to revise structure, depth or design.

## Output

- The .pptx file at a stated path.
- Slide-by-slide summary, one line each.
- Open items: images, data and facts that are placeholders.

## Rules that always hold

- A deck is a file, not chat bullets, unless he asks for an outline only.
- Numbers on slides come from his material or a source seen in this session; otherwise mark them as placeholders on the slide and in the open items. Do not invent traction, market sizes, customers or testimonials.
- Each slide connects to the next; if the story breaks between two slides, fix the spine, not the wording.
- Data is attributed on the slide.

## References

- `references/narratives.md`: the four story structures.
- `references/build.md`: python-pptx settings, default palette, fallback checks.
