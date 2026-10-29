# Showcase vocabulary and system patterns

Read only when the brief calls for an expressive showcase, a signature catalogue or detailed system guidance. `SKILL.md` production precedence governs this file: task, access, delivery and accepted brand come before these options. The numeric ranges, genre traits and reference examples below are starting points, not universal acceptance requirements. A quiet utility, table, canvas or reading page may use none of this vocabulary.

No template name, trend or perceived expense is evidence of measured usability or commercial results. The rationale section supplies design hypotheses to test, not promised psychological effects. Do not copy reference assets or complete layouts.

## What makes these sites read as expensive

Eight traits from the source showcase vocabulary are available to choose from. Use only those that fit this brief, accepted brand and material; they are not a compulsory set.

1. **One signature moment.** A single spatial, scrubbed or participatory event carries the page: a slowly rotating cluster of tilted image planes, a helix ribbon of project images, a foldable phone that opens on scroll into the site itself, a model turning 360 degrees as you scroll, a webcam image that breaks into particles under your hand. It shows within about a second of load or on the first scroll, without instructions. Everything else is quiet.
2. **Type as architecture.** Display type is sized from the viewport rather than a type scale: wordmarks at roughly 12 to 25vw spanning or deliberately cropped by the edge, names split around an object, tight tracking. Against it sits a micro layer of small uppercase sans or mono labels: indexes, roles, coordinates, years, status. The contrast between the two voices is the look; display-to-label ratios above 10:1 are normal in the hero.
3. **Monochrome chrome, colour from content.** Paper (warm off-white, not #fff) and ink (near-black, not #000), or one saturated flood (signal red, safety orange) with black and white. Imagery supplies the rest of the colour and UI never competes with it.
4. **Imagery staged in space, not boxed.** Work appears as objects: tilted planes, cut-out figures over a colour field, ribbons, stacks, a device. Few cards, few borders, almost no shadows.
5. **Asymmetric Swiss grid.** Off-axis blocks, large voids, hairline rules, ragged-right text, small navigation pinned to corners or set as a centred row of tiny caps. Density is low in the hero and rises where people compare: project index, services, rates.
6. **Detail on intent.** Lists reveal on hover and focus: a black bar sweeps across the row, the text inverts and a preview image cuts in. Cursor changes announce affordances (Drag, View, Play). Depth appears when someone asks for it.
7. **Authored motion.** Masked line reveals, image unmasks, staggered panel wipes, blur-through type changes, ambient loops measured in tens of seconds, scrubbed transformations that reverse when you scroll back. Expo or quart ease-out for entrances, linear mapping for scrubs, nothing bouncing.
8. **Concrete persona detail.** Role, city, local time, a real email, a numbered project index, and availability as plain text in the nav or a corner with a static dot (never a pill above the headline). Specifics make the site feel inhabited. In a template they are labelled samples; on a real site they must be true.

Most attempts at this look fail on restraint (several tricks competing) or on material (demo-grade imagery the real content can't match).

## Why it works

Apply the mechanism, not the surface.

- **Costly signal.** For creative and technical services the site is a work sample, and visible craft is the evidence. The signature must survive close inspection, or it signals the opposite.
- **Aesthetic-usability effect.** An attractive presentation can affect perceived credibility or ease, but this is a design hypothesis here, not measured performance, so the operative facts (contact, price, availability, next step) still need plain, fast presentation.
- **Isolation.** One saturated or moving element is remembered; five are noise.
- **Agency.** A draggable, scrubbable or tunable object holds attention because the visitor causes the change. It never gates content.
- **Self-reference.** A webcam or name-driven effect can make participation personal when the subject warrants it. This is not a universal engagement advantage and it carries a substantial consent duty.
- **Peak-end.** Treat the strongest moment and ending as a craft hypothesis worth checking. Design the close (footer, contact) as deliberately as the hero; Foldfolio folds its phone shut into an incoming call.
- **Object permanence.** An element that persists across sections or routes (the device stays, only its screen changes) keeps people oriented while everything around it moves.
- **Recordability.** These sites spread as one-second phone clips of a monitor. A signature that reads at that size and duration is distribution, not decoration.

None of this licenses false urgency, fake scarcity, invented proof or engagement bait.

## Signature families (optional choices)

Signature families seen at this tier. Combine at most two, with one leading.

| Family | Fits when | Build | On a phone |
|---|---|---|---|
| Spatial image composition: cluster, helix, ring, card cube | Many strong images; the body of work is the point | CSS 3D up to about 12 planes; WebGL beyond that or for distortion | Fewer planes, slower, or a swipeable stack |
| Container metaphor: device, filmstrip, book, specimen case | The subject has a physical form or medium | CSS 3D hinge or WebGL shell with real DOM inside | Re-orient the object (Foldfolio opens top to bottom in portrait) |
| Scrubbed object: 360 turn, exploded view, assembly | A physical product or process | Image sequence on canvas, or a compressed glTF model | Shorter sequence, smaller frames, tap to step |
| Participatory material: webcam particles, hand tracking, tunable simulation | Experimental, creative-tech or playful brands | WebGL particles, in-browser hand landmarks, opt-in camera, visible controls | Pointer or tilt fallback; camera optional |
| Typographic architecture: full-bleed wordmark, split name, cropped letters | Imagery is thin or the name is the brand | Fitted type, variable width or weight axes, masks | Stack or rotate the word; keep the crop intentional |
| Saturated field: one colour flood with cut-out figures | Strong colour identity: fashion, sport, product drops | Flat field, cut-outs, oversized type behind or through the figure | Keep the field, simplify the layers |


## System examples for the selected approach

Keep operational text readable, content in the DOM and relevant state distinctions. Genre fitting, crops, colour and grid examples below apply only when they serve the actual task. Accepted brand, accessibility and content can require different choices; there is no font or card blacklist.

## 3. Derive the system

**Governing rules.** One or two taken from the subject (a real proportion, a data unit, project dates on an axis, an action's duration), applied consistently. A rule earns its place by making a task or relationship clearer; one that serves only a hidden rationale is decoration.

**Type**

- Two voices. Display uses clamp() with a rem term in the preferred value, for example clamp(3rem, 1rem + 14vw, 20rem), so browser zoom still enlarges it; pure vw ignores zoom. Track it tighter as it grows (about -0.02 to -0.05em) with leading of 0.85 to 1.0. Operational text is 16 to 18 px with 1.4 to 1.6 leading and a 55 to 75 character measure.
- The micro label layer is 11 to 13 px, uppercase, tracked +0.04 to +0.1em, and still meets contrast. Don't copy the genre habit of 8 px grey labels.
- Fit a full-bleed word exactly. Either set it as SVG text in a viewBox (aria-hidden, beside a real h1), or measure it: give the word display inline-block and white-space nowrap (a block element reports its container's width, not the text's), read its width at a reference size, scale font-size by target width over measured width, and re-run after document.fonts.ready and from a ResizeObserver. Measuring before the web font loads gives the wrong width. Never size against 100vw, which includes the scrollbar.
- Crop on purpose. An intentional bleed sits in a section with overflow-x: clip (overflow hidden creates a scroll container that breaks sticky and pinning). The page itself never scrolls sideways at any width.
- Pick faces for the actual words: a condensed or heavy grotesk, a grotesk with a width axis, a sharp serif, a mono for labels. Variable width axes (Archivo, Anybody and Roboto Flex on Google Fonts, for example) give fitted wordmarks without hacks. Do not choose a familiar pairing mechanically; accepted faces and useful conventional typography remain valid. Distinguish unrelated projects when a shared style is not scoped.
- Use font-display swap with metric-matched fallbacks so a late font doesn't reflow the hero, and preload only the display weights in use.

**Colour**

- Semantic tokens: paper, ink, a secondary ink that still passes 4.5:1, a rule colour for hairlines (about 10 to 18 per cent ink), an optional saturated field, and one accent with one job (often the status dot or the active row).
- Let imagery set the temperature. Grade generated images to one palette so the set reads as one body of work.
- Dark sections are deliberate scene changes, like walking into a darker gallery room, and stay high-contrast.

**Grid and space**

- Twelve columns with generous outer margins (about 2 to 4vw). Place blocks asymmetrically and let large voids stand. Hairline rules separate index rows; use boundaries where comparison, grouping or accepted identity needs them.
- Spacing on a 4 or 8 px base, with section gaps that jump in scale (for example 96, 160 and 240 px on desktop) so sections read as rooms.
- Density follows the task: sparse in the hero, dense where people compare.

**Motion tokens**

- Durations: 150 to 250 ms for control feedback, 500 to 900 ms for reveals, 900 to 1400 ms for the signature's entrance, 20 to 60 s per ambient loop.
- Easing: expo-out, cubic-bezier(0.16, 1, 0.3, 1) or GSAP expo.out, and quart-out, cubic-bezier(0.25, 1, 0.5, 1) or GSAP power3.out, for entrances; exits shorter than entrances; linear mapping from scroll progress for scrubs; for pointer-follow and drag inertia, a damped lerp normalised to frame time, 1 - Math.pow(1 - k, dt * 60) with k from 0.06 to 0.12, so 120 Hz screens don't run twice as fast.
- Stagger siblings by 30 to 90 ms. A sequence leads with one element and secondaries follow 100 to 200 ms later. Never everything at once.
- Name the tokens and use the names in code.

Keep the token set compact, reuse any coherent existing scale, and don't carry one project's treatment to unrelated work unless a shared style is scoped to it.
