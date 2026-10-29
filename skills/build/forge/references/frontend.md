# Front end: composition, identity, words, proof

A page is finished when a person can do the job with it, in the place it is delivered, and the page is recognisably about that job, at the visual bar in `visual.md`, in words that are true. Sections 1 to 5 (composition, identity, motion, states, words), section 11 (does it look current) and `visual.md` are read before any markup is written. Section 10 is the test for rejecting a result that is not there. Where this file and `SKILL.md` differ, `SKILL.md` wins.

This skill owns implementation. A showcase or marketing site goes to showpiece, a quick clean-up of an existing front end to anti-vibecoded-ui, long prose to deslop, and specific interface rules or terminal interfaces to interface-architect, when those skills are available. Several methods here are adapted from them: the three-source composition and judging lenses from showpiece, the copy rules from deslop, the noun swap and decoration removal from anti-vibecoded-ui.

## 1. Composition from the task

Before any styling, write down:

- **The main object.** What the user looks at and acts on: an invoice, a count sheet, a support queue, a roster. Not "a dashboard".
- **The main action, and how often.** Done fifty times a session: one press, a large target, no confirmation unless it destroys something. Done monthly: it can sit behind a button and end on a designed receipt.
- **The hardest judgement** from the brief, and the facts that settle it.
- **Real content at its worst.** The longest name, zero items, the busiest case, a missing optional field. Placeholder text hides every layout problem that matters. Design for the median real record, test with the worst, and don't design around content the user's data won't have (product photos, avatars, logos).

For an open brief, write three candidate compositions, one from each source. For each: one sentence, what changes at 390 px, and what it gives up. Variants with the same structure count as one.

- **The object:** the thing itself becomes the structure.
- **The decision:** the hardest judgement is visible and operable where the user acts.
- **The context:** the device, place and pace of use shape it.

| Tool | Object | Decision | Context |
|---|---|---|---|
| Invoice app | The editor is the invoice at A4 proportion: what you type is what the client receives | Amount due and days overdue lead; computed GST and totals look different from typed values and recalculate as you type | End of month: a batch view of drafts, each naming the one fact that blocks sending (no ABN, no email) |
| Stock count (the reference app) | The count sheet: a name, a large tabular number, two 44 px buttons | The low mark in words ("Low: at or below 5") beside the stripe | A phone in one hand in a storeroom: step sizes 1, 5 and 10, so a box is one press |
| Support queue | The queue in arrival order with the oldest waiting time largest | What breaches next, and who owns it, beside the claim action | A shared screen: one keystroke to claim, the next item focused after each action |

Choose the candidate that grows out of the real data, eases the hard judgement, fails the noun swap and works at 390 px. Write the five-second line: what a stranger would say on seeing it ("this is where the storeroom count is kept").

Page architecture follows the question: numbered steps for a process with a real order, a table for comparing, list and detail for browsing records, a scale drawing for anything in time or space.

Patterns that recur:

- **Time-based views** (rosters, schedules, timelines): draw time to scale so durations and gaps are visible; free time is actionable where it appears; mark now; mute the past; show the zone when it can differ from the viewer's. The drawing is for reading and the controls are separate: a short item may be drawn shorter than 44 px, but its hit area is not. Tall items use their space for what the user checks next (contact, notes), not padding.
- **Chrome budget:** on the main view at 1280 by 800, the main object starts in the top quarter. One way to navigate per axis: previous and next, or a strip, or a date field, not all three. A summary line earns its height or goes.
- **Repeated rows** carry one primary action. Secondary actions (edit, move, archive) sit behind selecting the row or in one menu. If they reveal on hover, they also show on `:focus-within` and are always visible on coarse pointers.
- **List and detail:** the list and the selection stay put while the detail changes, so the user keeps their place.
- **Choosing from a known set** (a time, a size, a plan): show the available choices as buttons or a short grid when there are few enough to see at once; a long native select hides the answer to "what is free?"
- **Where the main action goes at 390 px:** within one step of the top, never below a long list.

Small signature moments in a tool are earned, not added: a saved row settles into place instead of a toast; "Sent 23 Oct" appears on the invoice itself; a changed row tints briefly. Each is recognisable because it could only belong to this tool. A tool's signature is judged in use, not from a screen recording.

## 2. Identity: direction, signature, governing rule

The board supplies **directions** (`visual.md` section 3), while the structure contract governs the production layout. Keep the board unchanged. Apply the chosen colour, type and shape vocabulary in a way that serves the task and accepted brand; its preview composition is not compulsory. Consider:

- **Colour roles.** Use colour consistently for emphasis, actions and states, with text or shape carrying meaning too. An operational screen need not flood one object with colour.
- **Composition.** Use a move from `visual.md` section 5 only when it clarifies the task; the work surface itself can provide the identity.
- **The governing rule** from the subject: a timeline drawn to scale, an invoice at A4 proportion, counts set larger than their names. A rule earns its place by making a relationship clearer to the user.
- **Imagery, if useful.** A coherent illustration or photographic approach (`visual.md` sections 6 and 7); omit it when it adds no useful meaning.

A user's house theme or existing brand wins over every direction: its colours and faces fill the token names, its name or version goes in the identity note, and composition follows its task and content. The house default is light. A dark direction is chosen for the case or by the user; a dark theme offered inside an app is a complete token set measured on its own (body text aiming at 7:1) with `color-scheme: dark`, and a document the app produces (an invoice, a letter) stays paper-coloured in it because it is the object. Following the system's dark setting is the user's call, not a default.

Every token value lives in a direction block; components read tokens only. Spacing stays on one 4 or 8 px scale. Radius follows the direction through the shape tokens (Mono Flood 6 px, Arcade Pixel 4 px, Ink Paper 10 to 16 px, the rest 22 to 40 px), one value per kind of element.

Record the identity in a short note at the top of the stylesheet: direction (or house theme and version), signature colour and its job, faces and numerals, the bold move, the governing rule and why. If notes from the user's earlier apps are available, choose a different direction or pairing. If the user wants real randomness between apps, seed it and record the seed.

**Identity without web fonts.** Embedding the kit's faces (`embed_fonts.py`) works in most deliveries, sandboxed previews included. Where even that is ruled out, the levers that remain: scale contrast between the key value and its labels; weight; a system stack chosen for the words (`Charter, "Iowan Old Style", Georgia, serif` or `ui-rounded, "SF Pro Rounded", system-ui` for headings, `ui-monospace` or tabular numerals for values); the signature colour; and one motif drawn from real data, such as a time ruler, a ticket edge or a count gauge. A motif that carries no data is decoration.

**Type.** Sizes in rem so the browser's zoom and the page's text-size control both work. Operational text 16 to 18 px with 1.4 to 1.6 leading and a 55 to 75 character measure. Labels and metadata no smaller than 12 px, tracked slightly when set in capitals, and still at 4.5:1. The key value in each row (a count, an amount, a time) is the display voice: larger, in tabular numerals. Avoid Inter for everything, Space Grotesk with Instrument Serif, and serif italic accent words; pick faces for the actual words.

**Fonts and libraries follow the delivery surface:**

| Delivery | Fonts | Libraries |
|---|---|---|
| Sandboxed preview, host policy unknown | The kit's faces embedded as base64 with `embed_fonts.py` (about 25 to 40 KB per weight); system stacks only if embedding is ruled out | Inline or none |
| A host that publishes an allow-list (check it at the time) | From the list, pinned, with `font-display: swap`, a metric-matched fallback (`size-adjust`, `ascent-override`) and only the weights used | An exact pinned version from a listed source, with a ledger line naming the flow that needs it |
| Your own origin, or deployed | Self-hosted, subset `woff2` | Bundled or self-hosted |

In every tier the page works fully when every outside request fails: content visible, nothing jumping when a font arrives, motion falling back to CSS or none.

**Checks:** contrast measured in every theme with error states showing, including `--sig-ink` on `--sig`; raw colour values appear only inside token blocks (search for hex, `rgb(`, `hsl(` and `oklch(` outside them); `direction_board.py` reports no direction that left the page unchanged.

## 3. Motion, budgeted by frequency

How often an action is done sets its motion. Each motion has a trigger, the relationship it explains, a duration, behaviour when interrupted, an end state and a reduced-motion version that keeps the feedback.

| Kind | Budget |
|---|---|
| Press feedback | Under 100 ms: colour, border or inset. No bounce, no ripple |
| A change in place (row added, panel opened) | 120 to 200 ms, ease-out `cubic-bezier(0.25, 1, 0.5, 1)`; exits about two thirds of entrances |
| What changed | A background tint fading over at most 600 ms, never blocking input |
| End of a rare flow | Up to 300 ms for the result to settle, then the designed end state |
| Page load | At most one entrance, for the hero object, up to 600 ms ease-out; a loading state shaped like the data swaps in without movement; no staggered lists |
| At rest | Nothing moves except progress for work actually in progress |
| Scroll | Native: no smooth-scroll library, no snapping, no scroll-triggered reveals |

Tokens: `--dur-instant: 80ms; --dur-quick: 160ms; --dur-settle: 280ms; --ease-out: cubic-bezier(0.25, 1, 0.5, 1);`. Animate only transform and opacity. Every transition can be interrupted. The default follows `prefers-reduced-motion`; an in-app control may offer Match system, Reduced and Full, and motion increases only when the user picks Full. Reduced means no movement, not no feedback: the change is instant, the tint and the announcement remain. Anything that moves by itself for more than five seconds gets a pause control. A drag with inertia or a scrubbed timeline comes in through the ledger with a flow behind it.

## 4. Every state the data can be in

For each view, decide what the user sees when:

| State | The page must |
|---|---|
| Loading | Show what is coming, in the shape of what will arrive, and not jump when it does |
| Empty (nothing exists yet) | Say so, and offer the first action |
| No results (a filter or search matched nothing) | Say what was searched, and offer a way back to everything |
| Error on load | Say what failed, that nothing was changed, and offer a retry |
| Error on an action | Show the reason beside the thing it concerns, keep what the user typed, move focus to the first problem |
| Refused by a rule | Show the server's reason in words a person can act on |
| Busy | Mark the control as waiting without removing focus (`aria-disabled`); ignore a second press |
| Unconfirmed (no answer to a write) | Say the outcome is unknown and re-read the real state; never assume success or silently retry an unsafe write |
| Stale (changed elsewhere) | Say so, show the current version, and don't overwrite it |
| Partial (some items in a batch failed) | Say which, keep the ones that worked, offer the failed ones again |
| Interrupted (leaving with unsaved edits) | Keep the draft, or ask in the page |
| Dismissed (a panel or confirm closed) | Return focus to the control that opened it |
| Permission denied or unsupported (camera, location, storage) | Say what is unavailable and offer the manual path |
| Outside request failed (font, library, service) | Keep working; name what is missing only if it changes what the user can do |
| Success | Confirm briefly where the user is looking, and announce it for assistive technology |
| Destructive confirm | Ask in place, name the thing and the consequence, make the safe choice the default focus |

Wire the states to the real server answers: error text is the server's `message`, field errors its `fields`. After every action the tally, the row and any summary agree; check each with a step.

## 5. Words on the page

Interface copy is part of the build. Its failure is predictable: a stock phrase where an observation should be. "Your workspace is ready" is stock; "No invoices yet. Add the first or import a CSV" is the observation.

Write the strings before the layout: the empty state, each error `message` (at contract time), the main action's label and its success line.

- **Lead with the thing.** Headings name the object ("Invoices, October"), not the product or a greeting. Statuses name the instance ("3 overdue, $4,180"), not "Some items need attention".
- **Each string has one job.** Labels name. Actions are a verb and object that predict the result ("Send invoice", "Add 5"); never "Submit" or "OK" alone. Errors say what happened and what to do, with the domain fact that helps. Copy that narrates the interface ("Use the options below to get started") signals a structure problem: fix the structure.
- **One home per decision fact.** A fact that changes the next action (a due date, a cost, what is free) sits beside that action, at body size or larger, once.
- **Keep roles distinct.** Typed input, computed values and suggestions look and read differently. Model output is labelled as a draft or suggestion until accepted.
- **One name per thing** across the choice, the confirmation, the receipt, the email and the undo.
- **Show or cut evaluation.** "Powerful", "seamless", "smart" need the consequence that makes them true, or they go.
- **Simplify without merging.** Subtotal, GST and amount due stay three lines; "requested" and "booked" stay two states.
- **Match promises to behaviour.** "Saved", "Synced", "Undo" and "Works offline" are requirements with checks. A "Saved" toast after a write that only reached memory is a measured defect.
- **Limits once, where they matter.** A stubbed integration says so on the screen it affects, not in a footer and not beside every control.
- **Words no stronger than the evidence.** A label, KPI name, badge or summary takes its wording from what the data is: sample, synthetic, candidate, measured or validated. Over a synthetic corpus, a deterministic score is "candidate signal", never "confirmed need". A FACT or verbatim tag proves a quote matches its text, not that the claim in it is true. When the README says "not validated", the screen must not say "confirmed".
- **Origin where it would be mistaken.** Mock, sample or cached results carry their origin on the screen where a user would otherwise read them as live, and in the response or a sidecar for the next program. Once, where it matters, not on every row.
- **The user's conventions.** Their spelling, their date and time format, their currency, through `Intl` in their locale. Where the user wrote their own forms ("8:00", "60 min", "$70"), those win over what `Intl` produces. Local events are shown in their own zone, named when the viewer's zone differs. When a punctuation mark is ruled out, rewrite the sentence rather than substitute a lookalike.
- **Keep build vocabulary out** of the product (slice, ledger, stub, fixture, exercised), and no process or AI badges. Show user data and protected text (codes, identifiers, legal notices) exactly as given.

Then make a **string sheet**: drive the page through loading, empty, no results, error, refused and success, collect the visible text after each (`page.inner_text("body")`), and read it top to bottom as one text. Fix any string that fails the **transplant** test (it would sit unchanged in an unrelated app), the **swap** test (two option descriptions could trade places), or the **source** test (a specific with nothing behind it). Watch for one idea said three times as eyebrow, headline and subtitle, and for curt fragments that lost the reason.

## 6. Customisation that works

Offer a control only if it changes something useful, and then make all of it work.

- Colour through the semantic tokens in section 2, one complete set per theme, each measured for contrast.
- Useful controls beyond colour: density, text size, reduced motion, a step size or unit that fits the task.
- Every choice applies immediately, shows as selected and has an obvious reset.
- Remember choices only if storage works, inside a try. If it doesn't, the choice still applies for the visit and the page says so.
- Motion follows the system's reduced-motion setting until the user chooses in the app. Colour starts light (section 2); a dark theme is the user's choice in the app.

## 7. Accessibility that can be checked

- Native elements for controls. A `div` with a click handler is not a button. A sortable column is `<th aria-sort="..."><button>Name</button></th>`; an expandable row has a disclosure `<button aria-expanded>` in it. Do not add `tabindex` to rows and cells to make them reachable: put a real control inside. A composite widget (radio group, tabs, listbox, menu, toolbar) keeps one Tab stop and moves between items with arrow keys (roving tabindex or `aria-activedescendant`); `tabindex="-1"` on its items is correct. `dead_controls.py` reports elements that act on click with no Tab stop and no composite path (MOUSE ONLY), items whose arrow-key path it could not show (UNRESOLVED) and, with `--keyboard`, controls with no observable change on their role's activation keys (CLICK ONLY): all candidates to read. Exercise the keys on the delivered page, and check focus and the changed state afterwards (`references/results.md`).
- Every input has a visible label tied to it. Errors are tied to their field.
- Everything works by keyboard, focus is always visible, and focus stays where the user is working after a redraw.
- Text contrast meets WCAG 1.4.3 in every theme. State is never shown by colour alone.
- Primary and touch targets 44 by 44 CSS pixels; 24 by 24 (WCAG 2.5.8) is the floor, not the goal.
- Status changes are announced through a live region.
- Zoom is never disabled. Motion respects the reduced-motion preference.
- Nothing overflows sideways and no text is cut off at 320, 390, 768 and 1280 wide with real content.

A clean run of these checks is not an accessibility audit and says nothing about screen-reader use, which needs a person.

## 8. The delivery container

What a page may rely on depends on where it is delivered, so settle that first.

| Delivery surface | Apply |
|---|---|
| A chat host's sandboxed preview, or not known | The strict set below: no `form` element, no native dialogs, storage and downloads optional with a fallback, no outside requests the page depends on |
| A confirmed normal web origin (a deployed address, a local server opened in a tab) or a native shell | Forms, storage and downloads are fine. Prefer a real `form` with a submit button. Still catch a storage error and a refused download |
| Both | The strict set, with the form's behaviour kept by hand: a labelled group, and Enter in a field calling the same function as the button |

For the strict set, assume `sandbox="allow-scripts"` with nothing else unless you know the host's settings:

| In that frame | Consequence | Do this |
|---|---|---|
| Form submission is blocked | A Save wired to submit does nothing, silently | No `form`; `type="button"` controls; Enter in a field calls the same function |
| The origin is opaque ("null") | Requests to the page's own server are cross-origin; cookies are not sent | Only for an API meant to be called this way, holding throwaway data or authorising by header token. Never loosen a real API's access control for a preview (`backend.md` section 9) |
| Storage throws | `localStorage` raises an error | Wrap in try; work without it; say when choices won't persist |
| `alert`, `confirm`, `prompt` are blocked | Nothing appears; `confirm` returns false | Confirm in the page |
| New windows and downloads may be blocked | The link does nothing | Offer the content in the page as well |
| Outside requests may be blocked | Fonts, scripts and images from other sites fail | Inline what the page needs; system fonts (section 2) |

`scripts/delivery_check.py` runs your steps in a tab and in such a frame. On a confirmed normal origin, pass `--tab-only`. It is a stand-in: the only proof for a given product is using the page in that product's preview, and the report says which was done. An emulated phone width is "a 390 pixel viewport", not "an iPhone".

Put text on the page as text: build elements and set their text content; never assemble markup from user or server strings.

## 9. Signs of a generic shell

None is a defect alone. Several together, with section 10 failing, is a shell assembled from a template of "an app" rather than from the task.

- A greeting or product name where the working surface should be; a badge above the headline; one idea repeated as eyebrow, headline and subtitle.
- Summary cards with large numbers that have no source, range or link; percent changes with no baseline; a chart whose data is typed into the markup.
- A sidebar of sections that don't exist; buttons with no handler; links to "#".
- An "insights" or "assistant" panel of sentences that would fit any product.
- Decoration doing hierarchy's work: purple-to-blue gradients, gradient text, glass cards, blurred orbs, glows, a shadow on everything, a different radius on every element, decorative coloured-border cards. (Big radii and a flat saturated block are part of several directions; they are a sign only when they carry no structure.)
- Kit defaults left untouched: Inter everywhere, three icon boxes in a row, bento grids for everything, sparkle icons on actions, an icon on every element.
- Motion with no relationship: fade-in on scroll, everything animating on load, hover tilts, typewriter text.
- One state only: populated and happy.
- A theme switch that changes two colours, or settings that don't persist or reset.

A planted example of such a shell travels with the source for review. It passes the source scan, contrast and target-size checks, and every one of its eight controls does nothing.

## 10. The craft rejection test

`SKILL.md` step 7 lists the fourteen questions. Apply them to the rendered page at 390 and 1280 px, in every theme, after using it with realistic data, and give the reason for each answer.

How to apply the harder ones:

- **Cold read (7):** look at a thumbnail before rereading the brief and write one line saying what it is. Compare with the five-second line. Then rename the product and a few nouns: if the screen still suits an unrelated product, the task-specific composition is missing.
- **Median (8):** describe the typical generated version of this app in three lines (it usually has a header, summary cards, a table and a modal form). List where this page departs and why. A reason that would fit any product ("clean", "modern") marks a default. Could a reviewer name the kit it came from?
- **Decoration removal (9):** mentally remove gradients, shadows, blur and rounding. If the hierarchy collapses, the structure is missing and the decoration was covering for it.
- **Current look (14):** section 11.
- **Mismatch review (13):** the first-viewport captures and exercised states beside the step 4b analog, as `visual.md` section 10 says. A mismatch is fixed by changing the composition (what leads, where the first action sits, how much shows at once), never by recolouring or adding effects.
- **Proof of an action:** a toast or any change on the page is not proof that the labelled action happened. Check the data after a reload or restart.

Classify every finding:

| Kind | Example | Handling |
|---|---|---|
| Measured defect | A dead control, text below contrast, overflow, lost focus, totals that disagree | Fix. Not negotiable |
| Design assessment | Weak hierarchy, a composition that fails the noun swap, action noise on rows | Fix, stating the reasoning and confidence |
| Preference | The user's house theme, banned marks, palette | Apply the user's preference; don't present it as a finding of fact |

Each finding names what was observed, its consequence and a fix that can be checked. A failure on questions 7, 8 or 13 is fixed by changing the composition (the object's form, the decision made visible, the layout move), never by recolouring or swapping a font. The scanners cannot answer any of the fourteen questions, and a page with zero scanner findings that fails one is rejected. Never produce a score for how "AI-made" a page looks.

## 11. Does it look current

Users reject screens as "dated" or "2010" for a few repeatable reasons. Two screens the user rejected show them: a weather research tool whose first phone screen was a heading band, five navigation buttons wrapping onto three rows, a paragraph, a native select and a large blank region where its map should be; and a crate puzzle with a real identity (crates, a clamp) set in a flat, dense composition of boxes inside boxes, outlined buttons and small type. Neither failed a scanner.

This is a judgement made at 390 px on the real screen, not a recipe. Look for:

- **Lines doing grouping's work.** Borders, rules and outlines around everything, where spacing, alignment, scale or a filled surface would group it. A boundary with a job (a table's rows, a form field, a selected item, a game board's cells) stays.
- **A wall of boxed options.** Navigation or choices that wrap into rows of equal bordered boxes. Five sections on a phone want a segmented control, a scrolling tab row, a menu or one primary path with the rest one step away; the choice depends on how often each is used.
- **Words where the subject has a picture.** A weather tool without the sky, a map tool without the map, a science page explaining a model only in prose. Show the subject's own visual explanation (a map, a diagram drawn from real data, the object itself) where it carries the idea, labelled for what it is: illustrative or measured.
- **A large region with nothing in it.** A frame waiting for data with no loading state, no error and no explanation looks broken. Purposeful empty states (an empty list that offers the first action, a calm cleared queue) stay; they are designed, not blank.
- **Flat hierarchy.** Every element at a similar size and weight, so nothing leads. The thing acted on should be clearly the largest or strongest; supporting facts stay small and legible, not tiny.
- **Cramped controls.** Primary actions under 44 px, controls packed edge to edge, labels in small caps or monospace that strain at phone size.

Density, rules and boundaries are not faults in themselves: a dense professional tool (Ink Paper) can look current. The fix is never a cosmetic skin: a new palette or effects over a workflow that does not work is worse than the plain version. Fix composition first: what leads, how things group, what the subject's picture is, and what each region shows in every state.

## 12. Checks

| Question | Check |
|---|---|
| Does the flow work in a tab (and in a sandboxed frame where that applies)? | `delivery_check.py PAGE --steps FILE [--tab-only]` |
| With reduced motion, and with outside requests blocked? | The same steps with `--reduced-motion`, then with `--block-outside` |
| Does focus stay put? | `expect-focus:` steps after `press:` steps |
| Layout, access and screenshots per state | `render_gate.py PAGE OUTDIR --prep-js "..."`, once per state and once per in-app theme |
| Do controls do anything, by mouse and keyboard? | `dead_controls.py PAGE --keyboard` |
| Contrast, per theme and with errors showing | `contrast_check.py PAGE --set "html@data-theme=X" --click ...` |
| Target sizes | `target_size.py --page PAGE --width 390 --json` |
| Source-level candidates | `ui_candidates.py FILES` (its rule numbers refer to interface-architect's protocol) |
| Copy | The string sheet from section 5, read as one text |
| Direction options | `direction_board.py PAGE OUTDIR --title "..."` on the populated main screen, before the other screens are built |
| Composition | Screenshots of populated, empty and error states at 390 and 1280 in each theme, looked at |

Each check ends with a RECEIPT line (`results.md`); report its status verbatim. If a script is missing, or is an older copy that rejects a flag used here, that check is a runner_error: report the mismatch and hold it. Hand-made substitutes (your own screenshots and measurements) may be added as separate evidence, labelled as such, never as the script's result.

Run everything on realistic content. A suite that passes on the author's tidy sample says little: when a course engine was first given a real twelve-lesson course, twenty-two of fifty-one captions were cut off on a phone, and none of the earlier checks had noticed.
