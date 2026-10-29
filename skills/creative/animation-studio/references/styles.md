# Style-specific rules

## 2-D character (vector / cut-out, animkit)
- Rig = a drawing function with named controls; part order with near/far swap on facing.
- 2-D turns: slide facial features across the head (facing -1..1), narrow them near
  profile, swap near/far limbs at the midpoint and let motion blur cover the flip.
- Limbs as two-bone IK from silhouette-edge shoulders/hips; keep line widths constant.
- 24 fps; consider animating on 2s (`Channel.on(f, 2)`) for a hand-made cadence while
  camera moves stay on 1s.
- Organic shapes: `cv.blob(wobble=0.01-0.02)` beats perfect ellipses.

## 3-D stylised (Blender)
- Real scale (metres), bevels on every hard edge (light catches edges), roughness
  variation, no pure black or pure white albedo.
- Stylised character motion still needs arcs, overlap, and holds; bake animkit
  channels/springs into Blender keys (`animkit_channel_bake`, `spring_bake`).
- Cycles CPU + denoise for quality; keep samples low (16-32) and resolution honest.

## Motion design / kinetic type
- Typeface choice is half the design: fetch a real face (`animkit.fonts.fetch`).
- Animate tracking, baseline offset, weight (variable fonts), masks and opacity.
  Never squash/stretch glyphs non-uniformly.
- Stagger letters/words 1-3 frames; ease each; let the last element settle.
- Hold readable text ~0.3 s per word + 1 s; don't stack unrelated captions.
- One typographic system per piece (2 families max), consistent grid and margins.
- **Title / logo stings** (4-8 s): open on something legible within ~0.5 s (no
  near-empty frame), land the reveal at roughly 55-70% of runtime, then a reading hold
  of 1.5-2.5 s that is a *moving* hold (slow push or drift of 2-4%, a light sweep, the
  motif's secondary motion settling); a push so restrained that `reel_critic` still
  calls the hold near-still is not registering on screen. An intro that cuts to content ends on a short out
  (resolve, light-off, wipe) or on the settle, never on 3 s of nothing. Fine lines
  under ~3 px at 1080 shimmer and vanish on phones; draw motif strokes heavier.
- Every element has a job. An accent that moves without relation to the motif or
  the type (a stray dash that shrinks during the hold) reads as a glitch: anchor it
  or remove it.

## Logo and artwork animation (the client's own files)
- Load the real artwork: `SVGArt("logo.svg")`, read `summary()` (ids, groups, colours,
  warnings). Never redraw or "improve" a client logo; animate the parts it is made of.
- Build the reveal from the mark's own idea (what the shape depicts, how the name reads),
  not a stock template: stroke draw-on (`draw_on`), parts assembling along their own
  geometry, a fill arriving after its outline, a part that behaves like what it depicts.
- Each part moves about its own centre (`per_shape` dx, dy, rot, sx, sy, alpha); stagger by
  reading order or construction order; land on the exact static logo and hold it.
- Things that rise from behind something (a sun behind a hill, letters behind a baseline) need
  a mask, not a fade: `vector.mask_to(cv, shape, bounds)` inside `cv.layer(bounds=...)`; in
  Lottie, `layer_from_vpaths(..., mask=vpath)` keeps the mask still while the part moves.
- Scale: a lock-up sized for its final layout sits at a third of frame height or less, so a reveal
  played at that size reads as near-still (a test logo measured 86%). Play the mark's own moment
  at hero scale (the mark filling about two-thirds of the frame) and pull back to the lock-up as
  the name arrives; `examples/logo_reveal.py` drives that as one camera transform for MP4 and Lottie.
- The end hold moves the whole lock-up (scale 1-2%, a light sweep), never one part: the last
  frame must match the static logo exactly. Compare them.
- Drive every format from one set of Channels (see `examples/logo_reveal.py`) so the MP4, the
  alpha WebM, the GIF and the Lottie match; check the Lottie in a player (lottie-web) against
  the rendered frames before delivery.
- Outlined text only for exact wordmarks (SVGArt warns when <text> needs a font).
- Raster artwork (PNG layers): `cv.image(arr, x, y, w, h)` inside `cv.at(...)` for cut-out
  animation; keep each part on its own layer with a pivot at the joint.
- Deliver the variants it will be used in: MP4, transparent WebM/ProRes, GIF, Lottie.

## Data visualisation
- Animate the comparison the viewer should make: bars grow from a shared baseline in the
  order you want them read, lines draw on along x, numbers count with tabular figures and
  land on the exact value. Label units and the period; no invented data.
- One change at a time; hold the final state long enough to read (0.3 s per word + 1 s).

## Explainer
- One idea per scene. Transform the previous visual into the next (morph, zoom into a
  detail, a dot becomes a wave) instead of cutting between unrelated diagrams.
- Accuracy first: label axes, units, and what's schematic. Physical processes shown
  with the right mechanism (sound = longitudinal pressure waves: show compression and
  rarefaction bands mapping to the waveform's peaks and troughs).
- Narration or captions say the idea once; the visual proves it.

## Product film
- The product must do its job on screen: knobs turn, screens light, lids open, parts
  click, materials catch light. Interaction beats with anticipation and settle.
- Hero lighting: soft key, strong rim for silhouette, controlled reflections (cards).
- Macro inserts of details; slow camera with shallow DOF; end on the hero angle + mark.
- Show scale (a hand, a familiar object) at least once.

## Pixel art
- Draw on a small canvas (e.g. 320x180 or 480x270) and scale by an integer with
  nearest-neighbour (`Image.resize(..., Image.NEAREST)`); never non-integer scaling.
- Lock a palette (8-32 colours); no anti-aliasing or blur on sprites; no sub-pixel
  positions (round to the pixel grid each frame, or move on 2s).
- Frame counts: idle 2-6, walk 4-8, run 6-8; animate at 8-12 fps for sprites even if
  the video is 24/30/60.
- UI text in a pixel font at integer scale, or clearly separated from the game layer.
- Characters need walk cycles with readable contact frames, not gliding sprites.

## Game cinematic / trailer
- Honest to gameplay: label pre-rendered vs in-engine; don't show features that don't exist.
- Camera language of the game's genre; cut to music; end on title + platforms + date.
