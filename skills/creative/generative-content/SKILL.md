---
name: generative-content
description: "Produces a single-file visual piece that explains or presents something: an SVG illustration, infographic, animated diagram, visual one-pager, comparison, flow diagram, or scroll-driven visual story, delivered as .svg, .html or .jsx. Use when the user asks to 'generate something visual', 'create an infographic about [topic]', 'make something cool', 'visual for [concept]', 'illustration of [idea]' or 'animated diagram of [process]'. Not for a full page or portfolio (showpiece), code-driven art with seeded randomness (algorithmic-art), a static poster or PDF (canvas-design), data-bound deterministic SVG/PNG frames (media-compiler), a clickable concept map (atlas), or a teaching tool for one concept (learning-visualiser)."
---

# generative-content

Produces one self-contained visual piece: it picks the format that fits the goal, builds it in one pass, and checks it against a short quality bar. Palettes and format notes are in `references/palettes-and-formats.md`.

## Use when

- Someone wants an infographic, illustration, animated diagram, visual one-pager, comparison or flow diagram from a topic or a set of facts.
- The request is open ("make something cool", "a visual for X") and the right form is not yet chosen.
- A short visual story with a scroll or step sequence is needed.

## Not this skill

| The request | Goes to |
|---|---|
| Ambitious full page, portfolio or showcase site | showpiece |
| Generative art from code, flow fields, particles, seeded variations | algorithmic-art |
| Static poster, print piece, .png or .pdf artwork | canvas-design |
| Programmed, data-bound, deterministic SVG or PNG frames | media-compiler |
| Motion design, logo animation, loops, UI transitions | animation-studio |
| Explorable map of a domain's connections | atlas |
| Interactive explainer that teaches one concept | learning-visualiser |
| Animated multi-lesson course | percept |
| Slide deck | deck-builder |
| Chart of real data for analysis | data-intelligence |

## Inputs

- The subject and the facts to show (supplied, or to be drawn from the conversation; ask if none and the content matters).
- The goal: inform, persuade, delight or explain.
- The destination (social post, document, web page, slide) and any brand colours.

## Procedure

1. **Settle the goal and the one message.** Write the single takeaway in a sentence. If it needs two, make two pieces or ask.
2. **Check the facts.** Use only numbers and claims the user supplied or that are verifiable; mark estimates as estimates. Do not invent statistics to fill a layout.
3. **Choose the format** from the table.
4. **Choose the style and palette**: minimal, bold, technical or organic. Use at most five colours, each with a purpose (see the reference for presets). Respect brand colours if given.
5. **Compose.** Decide hierarchy first (what pops, what recedes), then spacing, then type. Build each element, then assemble.
6. **Add motion only where it carries meaning** (drawing attention to the step or change that matters). Respect reduced-motion preferences.
7. **Check against the quality bar**, fix, and deliver.

| Goal | Format | Technology |
|---|---|---|
| Explain a concept | Animated diagram | SVG with CSS animation, or React |
| Present data | Infographic | HTML or React with an SVG chart library |
| Tell a story | Visual narrative | Scroll-driven HTML or React |
| Delight | Generative piece | p5.js or canvas (route heavy art to algorithmic-art) |
| Summarise | Visual one-pager | HTML or React with a grid |
| Compare options | Comparison | Grid layout |
| Show a process | Flow diagram | SVG paths |
| Brand mark or icon | Logo or icon | Hand-written SVG |

If the host cannot render React, deliver plain HTML with inline SVG and CSS.

## Output

- One self-contained file: `.svg` for static work, `.html` for animation or interaction, `.jsx` when the host renders React. Say which file and how to open it.
- Retina-safe (vector preferred), dark and light variants where useful, a print-friendly version for infographics, WCAG AA contrast, alt text or a title and description on SVG.
- One line stating the message the piece carries and any figure that is an estimate.

## Quality bar

- The core message reads in about five seconds.
- Every element earns its place; remove decoration that carries no meaning.
- Text is legible at the smallest intended size and does not rely on colour alone.
- Numbers shown match the numbers supplied.

## Rules that always hold

- No invented data presented as fact; label illustrative figures as illustrative.
- Do not imitate a living artist's or a brand's distinctive work, or use real logos without the owner's permission.
- Build in one pass and deliver; do not ask about style when the request gives enough to choose.
