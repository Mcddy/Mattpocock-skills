# Positive design playbook

Use these as design assessments, not universal research findings. Fit the brief and existing product. Design the useful surface before decorating it.

## Choose composition from the job

| Product job | Starting composition | Distinctiveness serving the job | Wrong default |
|---|---|---|---|
| Review or approve records | Queue/table, filters near data, detail pane and clear status | Column hierarchy, relevant metadata, decision context and feedback | Hero and KPI cards hiding the queue |
| Create or edit media | Canvas/preview, stage-based tools, timeline or layers | Real work in the centre, precise controls and recognisable media behaviour | Tiny preview surrounded by an ornamental dashboard |
| View or customise a vehicle | Vehicle imagery, coherent angle/state comparison, options and saved versions | Material details, stance, lighting continuity and honest before/after | Generic showroom hero and fake 3D controls |
| Learn or practise | Current task, progress in context, worked example and practice feedback | Course notation, readable explanation and useful recovery | Gamified statistics instead of the next learning action |
| Search a collection | Query/filters, identifying results and item detail | Useful metadata and domain-appropriate thumbnails | Decorative cards with vague titles and hidden filters |
| Plan work | Dated tasks, ownership, dependencies and relevant detail | Density fitted to the horizon, editable state and meaningful groups | Totals unrelated to the next decision |
| Sell a service/product | Concrete promise, demonstration/evidence, understandable offer and next step | Actual expertise, media, credible details and editorial rhythm | Template filler and invented social proof |
| Operate a native utility | Platform-appropriate window, current status, primary control and recovery | Honest device state, direct settings and predictable system behaviour | Web landing page inside a desktop window |
| Experience a game/expressive brand | World, content and play affordances fitted to the audience | Art direction, character, atmosphere and purposeful motion | Muted enterprise UI imposed to avoid all flagged styles |

Choose density by information needed for a decision. Do not equate quality with minimalism or novelty with unfamiliar controls.

## Write a short design contract

Capture decisions in existing notes or the response; do not create a documentation pile for a minor fix:

1. Task and observable success.
2. Main content object.
3. Composition and why it exposes that object and action.
4. Two or three specific character qualities tied to audience/material.
5. Semantic palette, type roles, spacing, density, shape and motion.
6. Difficult states to prove: empty, failure, long content and responsive layout.

Reject adjectives such as premium, futuristic or modern without a visible implementation consequence. Explain what changes on screen.

## Establish tokens with roles

Reuse good tokens. If missing, define the smallest useful set rather than a complete design-system product:

- **Colour:** surfaces, primary/secondary text, separators, action, focus and semantic status. Keep muted text readable and status understandable without colour alone.
- **Typography:** page/section titles, body, labels, metadata and data. Choose sizes and line lengths from real content. Verify availability/fallbacks. Use tabular numerals for aligned quantities where helpful.
- **Spacing:** control internals, within-group gaps, between-group separation and page gutters. Make hierarchy consistent. A four-pixel base is an option, not a requirement.
- **Shape/elevation:** express grouping and stacking. Do not give every object the same rounded rectangle and shadow.
- **Responsive behaviour:** decide when content wraps, collapses, scrolls or rearranges; preserve reading order and action access.
- **Interaction:** distinguish hover, focus, pressed, selected, disabled and busy. Give keyboard focus its own visible treatment.

Prefer existing/local fonts and assets. Do not change a framework or add large animation dependencies to solve styling. Verify installed versions/APIs when implementation depends on them.

## Make content carry identity

Use domain detail the app actually knows. An invoice queue can expose supplier, reference, amount, due date and approval state. A restoration viewer can expose vehicle, stage and changed parts. Never invent these to fake readiness.

| Generic copy | Useful replacement, only when truthful |
|---|---|
| Unlock your potential | Start today's database practice |
| Seamlessly manage your workflow | Review the six invoices awaiting approval |
| AI-powered insights | Compare the two restoration previews |
| Something went wrong | The preview could not load. Retry or choose another photo. |
| Get started | Add a vehicle / Import invoices / Create a scene, according to the action |
| Your command centre | A literal title such as Invoice approvals or Scene editor |

These are examples, not strings to paste into unrelated products. Label fixtures in demos. Remove unverified quantitative claims rather than substituting plausible numbers.

## Preserve familiarity and build character

Keep standard navigation, labels, selection behaviour and obvious actions. Differentiate composition, media, hierarchy and tone. Reuse coherent familiar icons; remove decorative saturation. Do not invent an icon for a familiar action to prove originality.

For native products, inspect applicable platform guidance and actual widgets. Do not impose CSS units/browser tests on native controls. Preserve window focus, display scaling, assistive-technology semantics and conventional shortcuts.

## Proof before expansion

Choose the screen exposing the hardest trade-off: dense records with long names, bright images under overlays or an editor at phone width. Include the main action and a difficult state. Inspect the rendering and behaviour. Revise if the result stays interchangeable with an unrelated template.

Judge whether the result exposes the object and action more clearly and fits the product character. Do not treat aesthetic preference as evidence of faster task completion, conversion or retention; those need audience testing.
