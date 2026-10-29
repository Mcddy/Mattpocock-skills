# Visual: directions, the options board, illustration, photography, bold layouts

Read this before step 6. It sets the visual bar for anything forge builds with a screen, gives the kit that reaches it, and the procedure for choosing a look with the user. Where this file and `SKILL.md` differ, `SKILL.md` wins.

## 1. The bar

The target is a well-made working product of the same kind (`reference-method.md`), with real data, clear hierarchy and usable behaviour. Production layout follows the task, content, device and accepted brand before any direction. The sixteen-direction board and its assets remain unchanged. Its expressive grammar is an available vocabulary, not a universal quality gate:

- **One signature colour with a job.** A saturated hue floods the one object the screen is about (the dog on the table, today's balance, the class starting next), not every button. Everything else is ink, paper and one soft tint.
- **Big, soft, confident shapes.** Cards at 24 to 40 px radius, pills and capsules, generous padding, floating pill navigation on phones with one round primary action.
- **Huge numerals and names.** The value the user acts on is set at 40 to 64 px in the display face, against 11 to 13 px labels. A 10:1 size ratio between the hero value and its label is normal.
- **A character or a picture in the composition.** One consistent illustration style (clay 3D or flat) or real photography, cropped with intent, never decoration from a stock pack.
- **One bold layout move per screen.** A flooded hero block, a full-bleed band, a split hero with a character breaking the edge, a joined stats bar, a ruled editorial list. One, chosen by the direction, not five.
- **Real states in the same language.** Empty, loading, error and success screens are designed in the direction too, often with the character.

Judge the result by task fit, hierarchy, readability, interaction and honest content. Gradients, borders, glass, cards, restrained type and expressive imagery are neither proof of quality nor defects by themselves. Use imagery only when it explains a subject, supports a decision or belongs to the accepted brand. Operational tools need not use a character, hero, oversized value or floating navigation. Ink Paper is one quiet option; no single style is compulsory for all tools.

## 2. The token contract

Every component reads these tokens and nothing else for colour, type, shape and elevation. That is what lets one page render in any direction and what makes the options board possible. Raw colour values appear only inside a direction's token block. The one exception is drawings: an illustration may hold its subject's own colours (leaf greens, a dog's coat), with its backdrop from the tokens.

| Token | Job |
|---|---|
| `--bg` | The page |
| `--surface`, `--surface-2` | Raised cards; a softer grouped area |
| `--ink`, `--ink-2`, `--ink-3` | Text: main, secondary (4.5:1 or better), tertiary for large text and decoration only |
| `--line` | Hairlines and outlines |
| `--sig`, `--sig-ink` | The signature colour and the text that sits on it (check the pair at 4.5:1) |
| `--sig-soft`, `--sig-deep` | A tint for selected or current items; a deeper shade for shapes inside the signature block |
| `--pop`, `--pop-ink` | The second voice: the selected day, the strong button |
| `--ok`, `--warn`, `--warn-soft` | Meanings, always paired with a word |
| `--nav`, `--nav-ink` | The floating navigation |
| `--block`, `--block-ink` | A large colour field (profile header, a summary band) |
| `--backdrop`, `--label` | Presentation only: behind phone frames in shots |
| `--font-display`, `--display-weight`, `--display-track` | The display voice |
| `--font-body` | The working voice |
| `--shadow-1`, `--shadow-2` | Elevation for cards and for the hero object (a direction may use outlines or hard offsets instead) |
| `--scheme` | `light` or `dark`, copied to `color-scheme` |
| `--rail`, `--rail-ink` | Optional: a desktop side rail when it should differ from `--nav` |
| `--focus` | The focus ring, 3:1 against its neighbours (defaults to `--ink`) |
| `--r-hero`, `--r-card`, `--r-row`, `--r-day`, `--r-control`, `--r-field` | Radii for the hero block, cards, list rows, day cells, buttons and chips, inputs. Mono Flood sets them near square, Lilac Soft plumper |
| `--outline` | A ring every card and row adds to its shadow (Candy Pastel's ink outline; transparent elsewhere) |
| `--hero-value-size` | The size of the operative value in the hero (76 px by default, 92 to 100 px in the bold directions) |

**Role classes.** The kit's components carry roles, not grooming meanings, where it matters for any subject: `.hero-value` is the operative number or word; `.slot` is the generic list row (picture, name, facts, a value or `.actions` on the right); `.slot.is-now` is the one current item on the screen, which several directions flood with the signature colour, so use it once; `.slot.is-alert` marks rows that need attention (overdue, failing) with a warn stripe that never competes with the signature; `.slot.is-done` is past or finished; `.is-long` on `.hero-value` or `.stat b` fits a long value (money, big counts) to its box. Generic pieces for forms and states: `.field`, `.input` (with `aria-invalid`), `.field-hint`, `.field-error`, `.choices`/`.choice` (radio cards), `.chip[aria-pressed]`, `.state` (illustration, heading, text, action for empty, error and success), `.banner`, `.skeleton`. New components use the same tokens and radii, so every direction reaches them.

## 3. The directions

The kit (`assets/visual-kit/`) ships seventeen token sets with a composition layer each: the same components change shape and rhythm as well as colour. Sixteen are expressive and make up the default board; Ink Paper is the quiet one for dense tools. Fonts are open-licence and included. `kit.css` and `kit2.css` hold the first eight and Ink Paper, `kit3.css` the other eight; a page loads all three while the board is in use.

| Direction | Look | Faces | Fits when | Avoid when | Illustration |
|---|---|---|---|---|---|
| `warm-pop` | Cream page, orange signature, black pill nav, soft shadows | Bricolage Grotesque, Plus Jakarta Sans | Friendly services, bookings, food, pets, a sole trader's daily tool | The subject is grave (legal, medical results) | Clay |
| `lime-night` | Near-black page, neon lime, huge neon numerals, glowing current item | Sora, Manrope | Used at night or in low light, fitness, music, energy, anything with a live "now" | Long reading, older or low-vision users without a light theme | Clay |
| `lilac-soft` | Lilac page, violet signature, coral second voice, plump capsules | Outfit | Wellbeing, habits, learning, gentle planning | Money-critical tools that need sobriety | Clay |
| `fresh-green` | Warm paper, deep green, yellow nav, serif display, rows not cards | Fraunces, DM Sans | Garden, food, outdoors, local business, calm admin with character | Fast, high-energy tasks | Flat |
| `coral-editorial` | White page, coral flood, very large type, ruled lists and stats | Schibsted Grotesk | Content-led tools, reading lists, events, anything where names and titles lead | Dense numeric tables | Clay |
| `sky-illustrated` | Pale sky page, sunshine signature, clouds, larger characters | Rubik, Figtree | Family, kids' activities, travel, onboarding-heavy consumer apps | Professional dashboards | Clay, large |
| `mono-flood` | Paper and black, one flooding blue band, condensed capitals, square shapes, hard offset shadows | Anton, Archivo | Sport, tickets, logistics, bold brands, anything with a schedule and urgency | Soft or caring subjects | Flat |
| `candy-pastel` | Ink outlines with a drop, a different pastel per block, chunky type | Fredoka, Nunito | Playful consumer apps, games, collections, kids and teens (content permitting) | Formal, financial, clinical | Clay |
| `cherry-noir` | Warm near-black, cherry signature, cream ink, wide lowercase display, asymmetric corners, numbers on cherry rules | Syne, Onest | Nightlife, music, film, bars and restaurants at night, bold grown-up consumer apps | Children's products, calm wellbeing, long daytime reading | Clay |
| `aqua-mint` | Mint page, aqua signature with dark ink, bubbles in the hero, soft round shapes, white nav | Lexend | Health habits, hydration, cleaning and laundry services, friendly money tools | Luxury, nightlife, anything that needs gravity | Clay |
| `rose-studio` | Blush page, deep rose, high-contrast serif names, a hero framed like a mounted print | DM Serif Display, Albert Sans | Beauty and salons, fashion, florists, weddings, personal brands | Technical tools, sport, anything urgent | Clay |
| `terracotta-arch` | Clay-pink page, terracotta, olive second voice, arched hero with the subject centred, arched stat cards | Epilogue, Instrument Sans | Crafts and makers, cafés, plants and gardens, homewares, retreats | Fast data-heavy screens; long lists of identical rows | Clay |
| `arcade-pixel` | Navy-black, cyan and magenta, square corners, hard offset shadows, mono type, a segmented pixel meter | Rubik Mono One, JetBrains Mono | Games and streaks, hobby collections, developer tools, gaming communities | Older audiences, formal or caring subjects, long reading | Flat |
| `navy-gold` | Deep navy, gold signature, ivory ink, serif names, gold hairlines, a list not cards | Playfair Display, Hanken Grotesk | Premium services, finance and investments, memberships, legal, concierge | Playful or low-cost consumer apps | Clay |
| `photo-bold` | White page, ink chrome, the subject as a large picture tile with its facts on a solid band | Familjen Grotesk, Instrument Sans | Venues, products, property, travel, food: anything with good photos | No real photos coming; dense data screens | Photos, or clay on a picture tile until they exist |
| `plum-peach` | Peach page, deep plum, flat duotone, a hard colour split in the hero, a two-tone stats bar | Gabarito | Creators and social apps, events, bookings with personality, youth brands | Corporate or clinical subjects | Flat |
| `ink-paper` | Warm paper, ink, deep teal, hairline rows, small radii (not in the default board) | Schibsted Grotesk, Figtree | Dense professional tools: accounts, admin, data entry, long scanning | Consumer apps meant to delight | None or small flat icons |

A user's brand or house theme wins over all of these: map it onto the token names and retain the composition that serves the task and content. The house default is light; a dark direction is chosen when the case calls for it (night use, media, a live "now") or the user picks it, and an in-app light alternative is offered when people read for long.

## 4. Choose the direction with rendered options

A look is chosen faster and better from rendered options of the real screen than from adjectives. For a new interface with an open look:

1. **Build the main screen first, populated.** Real or realistic data at its worst case (the longest name, the busiest day), the main object, the main action. Components read the token contract only. Set `data-dir` on `<html>`.
2. **Choose your three.** Rank the sixteen for this case with the fits-when and avoid-when columns and pick three to recommend. Write one line per direction on why it fits or does not (`notes.json`), honest about the cliché choice.
3. **Render the board.** `python scripts/direction_board.py PAGE OUTDIR --title "App name" --recommend a,b,c --notes notes.json` writes `board-live.html` (the page itself running in a phone frame and a desktop frame, with a chip per direction, the recommended three first and badged, and a Pick button that copies "Direction: name"), and, where Playwright is available, `board.png` (a grid of phone and desktop captures) and `board.html`. The live board needs the kit's `kit-dir.js` in the page. For a page that is a file, the board packs the page and everything it links into `board-live.html`, so it opens offline as one file; with `--live-only` it is made with Python alone, no browser. A board made that way is written, not yet viewed, until someone opens it. Use `--prep-js` to reach a populated state for the captures, `--dirs` to change the set (add `ink-paper` for a dense tool). The script warns when a direction did not change the page and lists elements that kept the same background or text colour in every direction: each is a component with a hard-coded colour.
4. **Show it before building further.** Send `board.png` and `board-live.html`, with the three recommendations and their reasons first. The user picks one, or a mix ("lime-night, with lilac's capsule days"): apply a mix by overriding the named rules, never by averaging palettes.
5. **When nobody is there to ask** (a scheduled run, "you pick", a user who has gone), choose from the "fits when" column for this case, avoid the direction used for the user's previous app if its identity note is available, state the choice and the reason in one line, and still deliver the board so the user can switch. When the obvious fit is the subject's cliché (green for plants, navy for finance), look at the second fit: take it if it serves the main task as well, and say which you passed over and why.
6. **Record it** in the identity note at the top of the stylesheet: direction, signature colour and its job, faces, the bold move, the governing rule from the subject.

Skip the board when the user has fixed a brand, house theme or direction, for a small change to an existing interface, and for a tool with no screen. With no browser in the session, run the board with `--live-only`, deliver `board-live.html` (it stands alone), report the captures as not run, and give the three recommendations with why each fits from section 3. Do not describe how they render: nobody has looked yet. Where this skill's files cannot be reached at all, the board cannot be made in this session: give the user the command to make it on their own machine, keep all sixteen directions, and never imitate them from memory.

## 5. Bold layout moves

The board previews include composition moves. For production, use a move below only when it improves this screen's task, hierarchy or accepted identity. A coherent table, form, reading column or canvas does not need an added hero. Keep the board assets intact and scope any production overrides to the app:

- **Flooded hero object.** The one thing the screen is about in a large signature block at 32 to 40 px radius, with its value at display size, its progress and its one warning. Phone: full width under the title. Desktop: the left column, the working list beside it.
- **Split hero with a character.** The illustration breaks the block's edge or sits in a halo; the name and value hold the left.
- **Full-bleed band.** A colour band edge to edge with a hard rule above and below (Mono Flood). Strong for a live "now".
- **Huge numerals on rules.** Stats as display numbers on hairlines or a left rule, no card behind them (Lime Night, Coral Editorial).
- **Joined stats bar.** One tinted bar divided by thin rules instead of three floating cards (Fresh Green, Ink Paper).
- **Colour run.** Each block in a different pastel with ink outlines (Candy Pastel). Only when the blocks are siblings of equal weight.
- **Ruled editorial list.** Rows divided by rules, the time or index in the display face, the current row marked by a thick rule (Coral Editorial).
- **Arched hero.** The block's top is an arch and the subject sits centred under it, name below (Terracotta Arch). Suits one object at a time.
- **Picture tile.** The subject as a large picture with its facts on a solid band overlapping the bottom edge (Photo Bold). Only when the pictures are good, or clearly placeholders until they are.
- **Hard colour split.** The hero divided into two flat colours, the subject on the boundary (Plum Peach). Flat stops, never a blend.
- **Framed print.** An inset frame inside the hero block, as if mounted (Rose Studio).

At desktop width, choose a composition that improves the real task and preserves meaningful reading and keyboard order. A split pane helps some workflows; a full-width comparison table, canvas or bounded reading column helps others. Use proportional timelines only when intervals matter. Check the first useful action, long content and recovery at the actual mobile and desktop sizes.

## 6. Illustration

Illustration earns its place when it depicts the subject's own things (the dog, the plant, the parcel, the bike) or a state (empty, done, offline). It never depicts invented customers, staff or testimonials.

**Clay 3D in SVG** (no image generation needed). `assets/visual-kit/illustrations.js` exports the helpers as `CLAY` (`ctx()` for unique ids, gradients and the clay filter; `tone()`, `mix()` and `ramp()` for colour; `bun()`, `blob()`, `tufts()` and `bumps()` for soft forms) plus a dog pack; `illustrations-plants.js` is a second pack (plants in pots, three scenes) written on those helpers, and the model for a new subject:

- Volume from radial gradients: a light spot at the upper left (about 30 per cent, 25 per cent), the base colour, a darker rim. One gradient per material.
- A soft rim light with a blurred inner edge filter, and a flattened ellipse contact shadow under the form.
- Simple, round, toy-like forms: big head, small features, eyes as glossy dots with a white catch-light. Features are shapes, not outlines.
- Colours from the subject (coat colours, leaf greens), backdrop from the tokens (`--surface`, `--sig-soft`) so it sits in every direction.
- Unique gradient and filter ids per call (a counter), `viewBox` sizing, under about 12 KB each, `aria-hidden="true"` when the name is beside it, otherwise `role="img"` with a label.

**Flat:** the same forms with solid fills, one shade step for depth, no gradients or outlines. Used by Fresh Green and Mono Flood; the kit's `flatDog` in `example/gallery.js` shows it.

**Generated images**, where the host has image generation and the user wants it, kept consistent with a fixed prompt vocabulary:

```
A cute 3D clay [subject, with its real distinguishing features], toy-like proportions, soft rounded forms,
matte clay material with subtle surface texture, soft studio lighting from the upper left, gentle contact shadow,
plain [hex from --sig-soft] background, centred, square, no text, no props unless named: [props].
```

Generate the whole set in one style and one lighting, check each at final size and at thumbnail, crop to a consistent ratio, and label generated imagery wherever it could be read as real work, real places or real people.

## 7. Photography

Photos lead when the subject is visual and the user has the pictures: their products, their venue, their dogs, their work. Treatment:

- One ratio per role (4:5 for cards, 3:2 or 16:9 for a hero), cropped on the subject, at the card's radius.
- Text never sits on a busy photo. Put it on a solid band, a token-coloured panel, or a scrim strong enough to pass 4.5:1 measured.
- A set reads as one body of work: similar light and temperature; a light `--sig` wash (0 to 15 per cent) can unify mixed photos.
- `width`, `height` and `alt` on every image; lazy loading below the fold; `object-fit: cover` with a deliberate `object-position`.
- When photos are not available (sandboxed preview, no assets yet, outside image hosts blocked), use a token-coloured tile with the subject's illustration or initials, labelled as where the photo will go. Never stock people presented as the user's customers, and never a broken image icon.

## 8. Feel and motion for expressive screens

- Press feedback under 100 ms: a slight scale to 0.98 or a colour step. No bounce on interface elements.
- The hero object may make one entrance on first load (up to 600 ms, ease-out `cubic-bezier(0.16, 1, 0.3, 1)`); lists and cards do not stagger in.
- A change in place 120 to 200 ms; a changed row tints for up to 600 ms; the end of a rare flow (a booking made) settles for up to 300 ms, often with the character's success scene.
- Nothing moves at rest except real progress. Anything that moves by itself for more than five seconds gets a pause control.
- Direct manipulation: inputs update results in the same frame; nothing moves under the pointer; fixed chrome (the floating nav) never covers the last item, so the page has bottom padding at least the nav's height plus its offset.
- Designed focus: a ring shaped to the control in `--sig` or `--ink`, 3:1 against its neighbours, on every control.
- Reduced motion makes changes instant and keeps the feedback.

## 9. Tells to strip, and the foundations

Strip on sight unless the brand or task needs them: purple-to-blue gradients and gradient text; glass cards, glows and blurred orbs; Tailwind defaults left as the design; cards around everything and coloured-border cards; hover lifts on every card and `transition: all`; a badge above the headline and an eyebrow over every section; three icon boxes and bento grids by default; Inter, Geist, Poppins or Montserrat by default, and Space Grotesk with Instrument Serif; sparkle icons on buttons; emoji headings; invented stats, logos and deltas; dead links and leftovers; fade-in on scroll; everything centred. A bright flat colour, a big radius or an illustration is not a tell when it has a job.

Then fix the foundations, in this order, because each depends on the one before: type (two voices, a real scale, tabular numerals for values), spacing (one 4 or 8 px scale, proximity groups), colour (tokens, one signature job, semantic colours only for state), hierarchy (one dominant element and one primary action per view), layout (a grid, recomposed for the phone), components (one radius scale per direction, one elevation approach, 44 px touch targets, labelled inputs, visible focus), copy, states, motion, details (title, favicon, consistent formats, no layout shift when fonts load).

## 10. Capture and judge

- Capture the populated main screen, the empty state, an error and the success state at 390 by 844 (2x) and 1280 by 800 in the chosen direction. `render_gate.py` takes the screenshots and the measurements; `direction_board.py --dirs <chosen>` gives a quick pair.
- Look at each capture at full size and at about 400 px wide.
- **Mismatch review**, after the craft test passes: the first viewport (the top 844 px of the 390 capture, the top 800 px of the 1280 capture) and each exercised state beside the analog chosen in step 4b. List concrete mismatches in hierarchy, first action, content density, disclosure and feedback; fix each, or state it as a departure with the reason (this product's data or workflow differs).
- Then score the six craft dimensions honestly, 1 to 5 at each width: task hierarchy (the user's decision leads, with its deciding facts beside the action), first usable viewport, content type and density (tuned to the worst case), coherent identity (the look used with intent in every state), responsive composition (each width composed for its use), states and feedback (every state designed; feedback matches the real outcome). A 3 or lower on any of them is reworked before delivery. A purposeful blank canvas can score 5.

A mismatch is fixed by changing the composition, not by adding effects or recolouring. The review is agent review, not a human design review, and it never overrides a failed check from step 7.
