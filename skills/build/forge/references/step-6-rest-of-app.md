# Step 6: build the rest of the app

Read before step 6.

**Imagery**
- One illustration style per app, depicting the subject's own things and states: clay 3D or flat SVG built from the subject (the kit's `CLAY` helpers in `illustrations.js`, with its dog and plant packs, show the method), or generated images where the host has image generation, from one fixed prompt vocabulary and labelled where they could be read as real.
- Real photography when the user has it: one ratio per role, cropped on the subject, text on a solid band or measured scrim, never over a busy photo. Without photos, a token tile with the illustration or initials, labelled as where the photo goes.
- Never invented people, customers, reviews or results, in pictures or words.

**Tells and foundations.** Strip the generic tells by composition, not palette: purple-to-blue gradients, gradient text, glass cards, glows and blurred orbs, Tailwind defaults as the design, cards around everything, coloured-border cards, hover lifts on every card, a badge above the headline, three icon boxes, bento grids by default, Inter for everything, sparkle icons, emoji headings, fade-in on scroll, everything animating on load, one idea said as eyebrow, headline and subtitle. A bright flat colour, a big radius or a character is not a tell when it has a job. Then fix the foundations in order: type, spacing, colour, hierarchy, layout, components, copy, states, motion, details (`references/visual.md` section 9).

**Fonts follow delivery.** The kit's faces as files on your own origin; embedded for a single file or a sandboxed preview (`scripts/single_file.py --keep-fonts`, or `scripts/embed_fonts.py`, both reading the kit's fonts with no network); system stacks only when neither is possible, with identity carried by scale, colour and composition. The page works fully when every outside request fails.

**Motion, budgeted by frequency.** Press feedback under 100 ms (a colour step or a 0.98 scale), no bounce. The hero object may enter once on first load, up to 600 ms, ease-out; lists never stagger in. In-place changes 120 to 200 ms. A changed row may tint for up to 600 ms; the end of a rare flow may settle for up to 300 ms, with the character's success scene if there is one. Nothing moves at rest; native scrolling; the floating nav never covers the last item. Reduced motion makes changes instant and keeps the feedback. A motion library needs a ledger line.

**Every state the data can be in**, designed in the same direction (empty and success are where the character earns its place): loading (shaped like what arrives), empty (offers the first action), no results, load error, field error (beside the field, input kept, focus moved), refused (the server's reason), busy (`aria-disabled`, focus kept, second press ignored), unconfirmed (re-read, never assume), stale, partial (say which items failed), success (where the user is looking, announced), destructive confirm (in place, safe choice focused), permission denied or unsupported (the manual path). After every action the tally, the row and any summary agree.

**Words on the page**
- Write the strings before the layout, in the user's own forms where they gave them.
- Headings name the object ("Invoices, October"), not the product or a greeting. Actions are a verb and object that predict the result ("Send invoice", "Add 5", never "Submit"). Statuses name the instance ("3 overdue, $4,180").
- Each fact that changes the next action has one home, beside that action, at body size or larger. Typed input, computed values and suggestions look and read differently. One name per thing across choice, confirmation and receipt.
- Cut evaluation words with no consequence ("seamless", "powerful"), copy that narrates the interface ("Use the options below"), and build vocabulary (slice, stub, fixture). Hedge once, where it is true. Never fill a gap with plausible invented detail; show the gap at the decision it affects.
- Make a **string sheet**: the visible text of every state, read top to bottom as one text. Fix what fails the transplant test (it would fit any app), the swap test (two descriptions could trade places), the source test (every specific traces to the user's material or data) and the delta test (an edit kept every commitment, limit and distinction).
