# Visual kit

Tokens, components, fonts and illustrations for forge's seventeen visual directions (sixteen expressive ones on the default board, plus Ink Paper for dense tools). Read `../../references/visual.md` first; this file says what is here and how to use it.

## Files

| File | What it is |
|---|---|
| `kit.css` | Token sets for `warm-pop`, `lime-night`, `lilac-soft`, `fresh-green` and `ink-paper`; the shared components (`.screen`, `.display`, `.eyebrow`, `.btn`, `.chip`, `.tag`, `.topbar`, `.week`/`.day`, `.hero`, `.meter`, `.card`, `.next`, `.stats`/`.stat`, `.section-h`, `.sched`/`.slot`, `.nav`/`.fab`, booking and profile pieces, desktop `.desk`/`.rail`/`.timeline`); and the composition layer that changes their shape per direction |
| `kit2.css` | Token sets for `coral-editorial`, `sky-illustrated`, `mono-flood` and `candy-pastel`, with the missing shared tokens filled in at the end, plus each direction's own gallery components (prefixed `ce-`, `sk-`, `mf-`, `cp-`) |
| `kit3.css` | Token sets and composition layers for `cherry-noir`, `aqua-mint`, `rose-studio`, `terracotta-arch`, `arcade-pixel`, `navy-gold`, `photo-bold` and `plum-peach`. Load after `kit2.css` |
| `kit-dir.js` | A few lines that let the live board switch the page's direction: reads `?dir=name` on load and accepts `postMessage({forgeDir: name})` from the parent frame only. Required in any page shown on `board-live.html` |
| `fonts.css`, `fonts/` | `@font-face` rules with relative paths to the woff2 files (latin subset, open licences, each family's licence beside it) |
| `illustrations.js` | The clay core, exported as `CLAY` (`ctx`, `tone`, `mix`, `ramp`, `bun`, `blob`, `tufts`, `bumps`), and the dog pack: `clayDog(key, {bg, size})`, `scene(name, {palette, dog})` |
| `illustrations-plants.js` | A second subject pack on the same core: `plantArt(kind, {style, bg, label})` for eight plants in pots and `plantScene(name, {style})` for empty, watered and wilting, each flat or clay. Load after `illustrations.js`. The model for drawing a new subject |
| `example/today.html` | One responsive screen (phone and desktop) built only on the shared components and tokens. `direction_board.py` re-skins it into all directions |
| `example/build_board.py`, `gallery.js`, `gallery2.js` | The full gallery for the first eight directions: three phone screens and a desktop view each (the newer eight appear on the board and the live switcher, not in the gallery). `python build_board.py --shots` from that folder writes `out/board.html` and `out/shots/` |

## Using it in a build

1. Copy `fonts.css`, `fonts/`, `kit.css`, `kit2.css`, `kit3.css` and `kit-dir.js` into the app (all three CSS files while you run the options board, since the board switches between all directions), and put `<script src="kit-dir.js"></script>` in the page head. For a single file or a sandboxed preview, inline the CSS and embed only the faces of the chosen direction with `scripts/embed_fonts.py "Family:600,700" ...`.
2. Set `data-dir="<direction>"` on `<html>` and `class="screen"` on `<body>`.
3. Build the app's own components on the token contract and role classes (`visual.md` section 2): `.hero-value` for the operative number, `.slot` as the generic row with `.is-now` (one current item), `.is-alert` and `.is-done`, and the generic pieces (`.field`, `.input`, `.field-error`, `.choices`, `.chip[aria-pressed]`, `.state`, `.banner`, `.skeleton`). New components use the shape tokens (`--r-card`, `--r-row`, `--r-control`, `--r-field`, `--outline`), so Mono Flood's square corners and Candy Pastel's outlines reach them too. `../reference-app-plants/` is a whole app built this way.
4. Render the board on your populated main screen: `python scripts/direction_board.py PAGE OUTDIR --title "App" --recommend a,b,c --notes notes.json`. It writes `board-live.html` (the page live in phone and desktop frames, one chip per direction; for a page that is a file, packed in so it opens offline as one file) and, with Playwright, `board.png` and `board.html`; `--live-only` makes the live board with Python alone. After the pick, you may drop the unused token blocks and fonts.
5. Write the identity note at the top of your stylesheet.

Two habits for real data: a value that can run long (money, big counts) takes `.is-long` on `.hero-value` or `.stat b`, which fits it to its box in every direction; and an app that opens empty should load labelled sample data on `?sample=1`, so `direction_board.py --query sample=1` shows it populated.

Never hard-code a colour in a component: the board lists every element that kept the same colour in every direction, and the dark directions will break.

## Adding or changing a direction

- A direction is one `[data-dir="name"]` block defining every token in the contract, plus composition rules that touch only shared components (`[data-dir="name"] .stat { ... }`). New directions go in `kit3.css` (or a later file loaded after it).
- A display face whose figures are old-style or oddly wide (Playfair Display, Syne) should not set numbers: give `.stat b`, `.slot .price`, `.sched .t`, `.day b` and `.hero-value` the body face, as Navy Gold and Cherry Noir do.
- Check `--sig-ink` on `--sig`, `--ink-2` on `--bg` and `--surface`, and `--nav-ink` on `--nav` at 4.5:1 or better.
- Add its name to `NAMES` (and `DEFAULT` if it belongs in the standard board) in `scripts/direction_board.py`, and an illustration style to `DOG_STYLE` in `example/gallery.js`, and its faces to `fonts.css` and `fonts/` (`embed_fonts.py --list-dir` can fetch them from @fontsource).

## Limits

- The shots are emulated viewports in headless Chromium, not devices.
- Photography is not included: the hosts used to make the kit block outside image sites, so photo slots in examples are shown as token tiles. `visual.md` section 7 covers photo treatment.
- The packs cover dogs and plants; other subjects need their own pack on the `CLAY` core, or generated images where the host offers image generation.
