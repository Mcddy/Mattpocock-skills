---
name: animation-studio
description: Build and review character animation, logo motion, UI transitions, loops and motion graphics using a brief, timed beats, style frames and inspected exports. Includes CSS/Lottie, 2-D tools, optional Blender and checks for media, timing and capability limits. Route by film, UI, logo or loop mode; distinguish measured checks from visual judgement and unavailable rendering.
metadata:
  revision: '3.1.0'
---

# Animation Studio

Build motion around its purpose: a readable state change, a recognisable mark,
a continuous loop or an acted story. Lock timing before polish, inspect the
composition and final export, and separate measurements from visual judgement.

The bundle ships a toolkit in `scripts/`: **animkit** (2-D animation:
easing, keyed channels, springs, walk with locked feet, IK, a character rig with a
face that acts, expressions, eye darts, lip sync, light, camera, particle FX, SVG and
raster artwork, kinetic type, render loop with alpha, sound design + mastering, and
exporters for GIF, WebM/ProRes alpha, APNG, Lottie and CSS; Skia backend or a
numpy+PIL fallback), a **Blender kit** (materials, light rigs, eased keys, spring
bakes, framing checks, turntables, GLB export, asset reports), and **QA tools**
(`reel_critic`, `filmstrip`, `sync_check`, `slop_lint`, in-scene review helpers).

## Step 0: environment and toolkit (always, before planning)

1. **Find the toolkit** beside this file (`scripts/`) within the task's allowed
   paths. Availability in Claude, ChatGPT or Codex depends on the active execution
   surface; a listed skill does not prove its files or tools can run. Inspect relevant
   scripts before execution. If unavailable, give a source handoff and mark script
   execution, rendering and runtime validation not run. Do not scan the whole host,
   change settings or substitute a source check for a render.
2. **Run `python scripts/env_check.py --json`** when execution is available. It is
   offline by default. `--probe-network` is a separately authorised direct endpoint
   probe, never proof that installation is possible. Use observed dependencies and
   the actual backend. `scripts/tests/selftest.py [--render]` is a broader optional
   suite: inspect its writes, subprocesses and cleanup before running it in an allowed
   location. A capability inventory is not a rendered test.

3. **Adapt the route to what's there:**
   - The soft 2-D route requires numpy, PIL and a successful canvas backend import.
     Missing network is not the deciding condition. Use installed fonts when the
     helper succeeds; an unknown font count is not zero fonts.
   - No Blender: propose an available T1/T2 route only if it meets the brief, or
     hand off Blender source with rendering unverified. Do not silently replace
     a required 3-D deliverable.

   - Short tool-call limits: render in chunks (`--frames a:b`) and join with
     `animkit.timeline.concat`. Leave `workers` unset: `render()` sizes the pool to free memory and,
     if a worker is still killed (out of memory), halves the pool and carries on from the same frame.
     Forcing `os.cpu_count()` got workers killed in a test run.
   - Cache what doesn't move: render a static set once (`Canvas(...).rgba_array()`) and draw it each
     frame with `cv.image(plate, ...)` (through the camera transform if the camera moves), instead of
     redrawing it for every motion-blur sample. A test run's soft render went from stalling to steady.
   - Respect the host: on a user's own machine, ask before installing anything.

## Honest fidelity tiers (say which one you're delivering)

| Tier | What it is | Achievable here |
|---|---|---|
| T1 Motion design | type, UI, infographics, logo stings, explainers | Depends on verified tools and the inspected output |
| T2 Stylised 2-D character | procedural rigs + keyed acting, painterly light, sound where required | Requires verified backend/dependencies and inspected output; rig simplicity limits acting depth |
| T3 Stylised 3-D | Blender (Cycles CPU / EEVEE), product shots, props, simple rigs | Where Blender exists; render time is the limit |
| T4 Feature film | sculpted deformation rigs, hand-keyed performance by animators, cloth/hair sim, film-res path tracing | No. Apply the *process and principles*; never label output "Pixar quality" |

If a brief asks for "Pixar level", clarify the intended style, craft and outcome.
State the achievable tier and any gap; do not redefine a binding quality target as
process compliance. Matching a reference requires inspected output comparisons,
not use of the same production vocabulary. State the tier in the delivery note.

## Choose the mode before applying craft rules

Record `film`, `ui`, `logo` or `loop` in the brief, plus required or silent audio,
intentional still intervals, target player, ratios, crops and thumbnail. Film includes
character shorts, narrative spots and reels. Asset jobs use the closest relevant
mode and mark irrelevant story/audio checks not applicable. Do not infer a film
narrative, camera move, soundtrack or 24 fps requirement for a utility interface.

Film uses thought, staging and continuity; UI uses immediate content, state clarity,
interruptibility, keyboard access and a usable reduced-motion state; logos use mark
recognition and a deliberate lock-up; loops need an inspected seam. Stillness,
silence and constant speed can be correct. The applicable brief governs the older
film-oriented reference examples below; they are not universal restrictions.

## Craft checks (apply only where the mode and brief require them)

1. **A clear beat.** Film: want, obstacle, turn and payoff. UI: input, transition and
   stable state. Logo: reveal and readable lock-up. Loop: a continuous cycle.
2. **Deliberate holds.** Review frozen or near-still film spans as candidates, not
   automatic defects. A readable lock-up, quiet beat or stable UI can remain still.

3. **Characters act through their bodies.** The hand does the work; eyes lead the
   head; anticipation before effort. Props never move on their own. Effort shows:
   lean 15-25 degrees into a push or pull, feet planted behind, a slow first shove (inertia).
4. **Feet stick.** Contact/down/passing/up, weight, bob, counter-swing; `foot_slide_report() == 0`.
5. **Spacing, not tweening.** Eases, arcs, overshoot and settle; constant speed only
   for things meant to feel mechanical.
6. **Light is motivated and lands on things.** Albedo x light for characters, additive
   practicals, falloff, reflections. No grey "glow" discs.
7. **Sound follows the brief.** Where sound is required, place contacts from the
   CueSheet and test offsets. Silence is valid when declared; do not add audio to UI by default.
8. **Score fits the form.** Narrative scoring may change with beats; utility feedback
   and loops do not need film dynamics. Loudness/LRA heuristics are review evidence.
9. **Legible typography.** Choose installed, licensed type for the purpose; never squash glyphs.
10. **Frame cadence is a choice.** Specify fps and motion blur for the intended surface.

11. **Framing is checked, and acting is staged to read.** Hero subjects stay inside the
    safe area unless leaving is the point; other aspects are recomposed, not centre-cropped.
    Thought beats (failure, idea, realisation, payoff) play at medium or closer, through
    a push-in, a reframe or a cut. One locked wide for an acting piece over ~8 s needs a
    stated reason.
12. **Reels follow reel rules.** Best first, about 60-90 s (Pixar's careers FAQ: reels of
    "approximately one to three minutes"), name and contact on first and last cards, breakdown.
13. **No stock (deslop).** Every move, gesture, effect and line of copy comes from this
    character, product, brand or story. A ready-made move (everything fades up, a
    thumbs-up, sparkles, a whoosh, "Unleash") standing where a specific thought should be
    fails the transplant, swap, strip and source tests in `references/deslop-motion.md`.
    No invented proof on screen. A fade or a bounce stays when it does a job you can name.

## The director's loop (how the work actually gets good)

The full sequence below is the film lane. Map it explicitly before work: UI uses
state-transition frames, keyboard/recovery/reduced-motion and target-player checks;
film story, character rigs, subject-size ratios and camera gates are not applicable
unless the brief actually includes them. Logo work uses reveal, recognition and
read-hold frames; loop work uses cycle and seam frames. Mark irrelevant pipeline
gates not applicable with a reason. Preserve timing, hierarchy, continuity, export
inspection and repair/reinspection in every lane.

Quality comes from looking, not from writing code. Run this loop; don't advance a
step until its check passes. Every claim you make about the picture must come from
frames you looked at; every claim about sound from a measurement.

1. **Brief + beats.** Fill `templates/brief.md` and `templates/beat_sheet.md`. Write the
   one sentence or state change the piece must communicate, and for character work the
   *thought* behind every beat ("too high", "the crate!", "mine"). Encode beats as one
   dict of frame numbers (`B = dict(...)`) that drives every channel, expression, the
   camera and the CueSheet, so re-timing is one edit.
2. **Style frame first.** Render ONE full-resolution still of the key moment before
   animating anything. Look at it and answer: Where does the eye land? Is the subject
   big enough to act (roughly 20-35% of frame height for action, 35-50% for thought
   beats such as an idea or a reaction)? Do values group
   (check it in greyscale)? Is every bright thing motivated by a source? Are fonts real?
3. **Block.** `review.beat_stills(draw, B, out)` renders one still per beat into a
   labelled grid. Check silhouettes, staging, screen direction, state continuity
   (everything that should still be there is still there after each change).
4. **Spline + preview.** Render the whole shot cheaply (`mb_samples=1`). Then build
   **character-tracked filmstrips** of every beat (`qa/filmstrip.py` on the preview,
   or `review.subject_strip` from the scene), every 2-3 frames. Look for: skating feet,
   pops, limbs crossing the face, props moving without a hand, hands stopping short
   (`review.reach_report`), dead holds, straight-line paths, simultaneous starts.
   Write a fix list; fix; re-render the affected frames; look again.
5. **Camera check.** `review.framing_report()` (2-D) or `scene_kit.frame_report()` /
   `fit_rig_scale()` (3-D) across the whole move. Decide explicitly what may leave frame.
6. **Light + sound pass where applicable.** Light per `references/lighting-and-colour.md`. Build sound
   from cues; inspect the spectrogram (no hiss blocks, nothing missing); run
   `qa/sync_check.py` (median offset < 1 frame); master and re-measure the final file.
7. **Final render** using the brief's frame rate and blur policy, with workers sized
   to observed memory when available. Do not call a CPU-only fallback memory-sized.
8. **QA.** Run `qa/reel_critic.py VIDEO --out DIR --mode MODE --sound auto|required|silent`
   with an actual sound-policy value. Declare permitted still ranges with
   `--allow-still START:END`. Fix applicable hard defects; resolve review flags by
   inspection against the brief, recording kept findings and reasons. Film
   stillness/staging/score heuristics do not automatically fail UI, logo or loop work.
   Loop mode leaves seam checking partial until a separate seam test is recorded.
   Then inspect the contact sheet, final filmstrips and visual rubric
   (`references/qa-rubric.md`), a scan of `references/failure-gallery.md`, and the
   deslop pass: `qa/slop_lint.py --text <copy> --code <scene.py> --video <final>` plus
   the transplant, swap, strip and source tests by eye (`references/deslop-motion.md`).
9. **Deliver** with an honest note (see Reporting).

Self-review questions before showing anything: What would a supervisor circle
first? Does each moving or still state serve its purpose? Who performs the key action? Where is the eye in each
beat? What lights each bright thing? Does required contact audio align? Does the
story read with the sound off? Is anything cropped, tangent, or covering a face?

## Pipeline gates

| # | Stage | Artefact | Gate |
|---|---|---|---|
| 1 | Brief | brief.md | audience, platform, length, aspect, tier, deliverables known |
| 2 | Purpose | logline or state/mark/loop beat sheet | mode-specific action and final state clear |
| 3 | Animatic | beat stills / stepped preview + scratch sound | runtime and beat frames locked |
| 4 | Design | style frame, colour script, character/prop design | style-frame questions answered |
| 5 | Build | rigs (drawing functions / Blender objects), assets | rig hits every boarded pose; reach checked |
| 6 | Layout | camera per shot, depth layers | framing report clean; one idea per shot |
| 7 | Blocking | stepped poses | poses read as stills |
| 8 | Spline + polish | eased channels, overlap, secondary | filmstrips clean |
| 9 | Light / FX / comp | light passes, atmosphere, grade | eye lands on the story point |
| 10 | Sound, if required | Foley from cues, ambience, score, master | complete applicable sync coverage; loudness on target |
| 11 | QA + delivery | reel_critic, rubric, masters + variants | hard defects fixed; visual findings resolved; gaps explicit |

Details and checklists: `references/pipeline.md`.

## Tool routing

| Need | Use |
|---|---|
| Environment + route | `scripts/env_check.py`, `scripts/tests/selftest.py [--render]` |
| 2-D character, motion design, explainers, type | `animkit` (`canvas` picks skia or soft) - `scripts/examples/doorstep.py` is the reference shot |
| A character, fast | `animkit.rigs`: `BlobRig(RigStyle(...))` + `Performer(channels, walks)` - restyle it rather than inventing a rig per job (`examples/hello_sting.py`) |
| Facial acting, dialogue | `RigStyle(face_rig=True)`; `face.ExpressionTrack([(f, "frustrated"), (f2, "idea", "snap"), ...])` (eyes and brows lead the mouth), `face.eye_darts`, `lipsync.from_audio(wav)`; craft in `references/acting-and-story.md` (`examples/eureka.py`) |
| The client's logo or artwork | `animkit.svg.SVGArt(path)` (+ `summary()`), per-part transforms, stroke `draw_on`, shape masks with `vector.mask_to` (never `blend="dst_in"`), raster parts with `cv.image`; Lottie with `layer_from_vpaths(mask=...)` and `null_layer` parents (`examples/logo_reveal.py`) |
| Contacts, impacts, weather | `animkit.fx`: `dust_puff`, `sparks`, `confetti`, `snow`, `steam`, `Burst`/`Emitter` (pure functions of time) |
| Formats: GIF, alpha, loops, captions | `timeline.render_rgba` + `animkit.deliver`: `gif`, `webm_alpha`, `prores4444`, `apng`, `loop_report`, `write_srt`/`write_vtt`, `draw_caption`, `safe_zone` |
| Web / app motion | `animkit.web`: `css_animation`, `Lottie`, `lottie_from_svg`; rules in `references/ui-motion.md` |
| Paths, draw-on, motion along a path | `animkit.vector.VPath` (`trim`, `point_at`, `transform`), `draw_fill`, `draw_stroke` |
| Data viz numbers | `typeanim.draw_number` (tabular digits for count-ups); `references/styles.md` data visualisation |
| Stock check (deslop) | `qa/slop_lint.py` + `references/deslop-motion.md` |
| Kinetic type | `animkit.typeanim`: `KineticText` + `stagger_in`, `tracking_to`, `pop_on_beats` (sync letters to cues) |
| Explainer transformations | `animkit.shapes.morph(a, b, t)` with circle/rect/star/wave builders |
| 3-D props, products, environments | `scripts/blender/scene_kit.py` - `scripts/examples/asset_radio.py` (framing gate + sound from animation) |
| Pixel art / sprites | animkit at low res, integer upscale, locked palette (`references/styles.md`) |
| Sound design, score, mix, master | `animkit.audio` + ffmpeg loudnorm |
| Review while building | `animkit.review`: beat_stills, subject_strip, framing_report, reach_report |
| Review a video | `qa/filmstrip.py` (frame strips), `qa/reel_critic.py` (measured QA), `qa/sync_check.py` (sound vs cues) |
| Fonts | `animkit.fonts.fetch(family, weight)` online; `best_available(role)` offline |

Performance: bound every blurred layer (`cv.layer(bounds=...)`). Historical producer
timings, not rerun for 3.1.0: a 1080p, 19 s shot with 3-sample blur took about 4 min
on a 2-CPU Skia sandbox; soft was about 2x slower. These are not host promises.

## Minimal shot (historical teaching pattern, not a validated 3.1.0 output)

```python
from animkit.canvas import Canvas
from animkit.curves import Channel, K
from animkit.principles import impact_squash
from animkit.timeline import render, CueSheet

B = dict(drop=0, hit=14, rest=40)
y = Channel([K(B["drop"], 200, "in_quad"), K(B["hit"], 820, "out_quad"), K(B["hit"] + 12, 640, "in_quad"),
             K(B["hit"] + 24, 820, "settle"), K(B["rest"], 820)])
cues = CueSheet(24).add(B["hit"], "impact").add(B["hit"] + 24, "impact", soft=True)

def draw(cv: Canvas, f: float):
    cv.clear("#14181F")
    sx, sy = impact_squash(f - B["hit"]) if f < B["hit"] + 24 else impact_squash(f - B["hit"] - 24, 0.12)
    cv.shadow(960, 866, 60 * (0.5 + y(f) / 1640), 10)        # shrinks as the ball rises
    with cv.at(960, y(f) + 44, 0, sx, sy):                    # pivot at the contact point
        cv.circle(0, -44, 44, "#E8A33D")

render(draw, 48, "ball.mp4", mb_samples=3)
```

Historical teaching examples under `scripts/examples/`, retained unchanged and not rerendered for 3.1.0: `examples/eureka.py` (the flagship: a 17 s pantomime built to the
feature process - thought per beat, face rig with expressions leading the mouth, eye
darts, strain vibration (`curves.Tremor`), hands pinned to props, a push and a jump,
cuts to a medium for the idea and for the payoff, sound from the action; `--review DIR`
prints framing and reach gaps), `examples/logo_reveal.py` (a client SVG animated from
the mark's own idea, masks via `vector.mask_to`, one set of Channels driving MP4,
transparent WebM, GIF and a masked Lottie), `examples/doorstep.py` (acting beats, walk,
IK, light, wet ground, rain, score + Foley), `examples/hello_sting.py` (reusable rig +
kinetic type synced to footsteps), `examples/asset_radio.py` (3-D asset, GLB, asset
sheet, product beat), `examples/bouncing_ball.py` (arcs, squash, decaying bounces).

## Asset creation mode

Deliver assets another artist (or a later session) can use without asking questions.
Details: `references/assets.md`.
- **Characters**: turnaround (front, 3/4, side, back), height chart, expression sheet
  (6-12), hand poses, colour callouts (hex), construction notes, rig controls.
- **3-D assets**: real scale in metres, named parts and meshes, pivots where they rotate,
  bevels, UVs, PBR materials, GLB, `asset_report()`, 4-view sheet, seamless turntable.
- **Sprites**: integer-scaled, palette-locked, frame counts per action, sheet + JSON.
- **Backgrounds**: depth-layered for parallax, value room for characters, colour keys.

## Critique mode

1. Measure: `qa/reel_critic.py VIDEO --out DIR --mode MODE --sound POLICY [--reel]` and `qa/slop_lint.py --video VIDEO`.
2. Look: contact sheet, then `qa/filmstrip.py` strips of the key beats; full-res stills
   for type, lighting and edges.
3. Judge against `references/qa-rubric.md` and `references/failure-gallery.md`.
4. Write findings as evidence -> consequence -> fix, ranked by impact, with
   timestamps; separate measured facts from judgement; credit what works
   (`templates/critique.md`). If you can, prove the main fix by rebuilding one beat
   and measuring before vs after.

## Reporting the result

Write the note the way `references/deslop-motion.md` section 5 says: lead with what was
made, name specifics, no hype. State: tier; canvas backend (skia/soft) or Blender version; runtime, resolution, fps;
what was rendered, which frames were inspected, what was measured (loudness, sync
offsets, foot slide, framing); **every reel_critic flag with what you did about it**
(fixed, or kept and why; a low bitrate on flat graphics encoded at CRF 16 is expected,
say so); what was not verified (e.g. no listening test on
speakers, not checked on a phone); known limits of the rig or style. Flag fiction,
placeholders and sample content. Keep an asset-origin ledger: supplied, original,
generated, synthetic, sample or licensed, with source/licence and any substitutions.
Carry that origin in sidecars and handoffs; disclose it where a user would otherwise
assume live or measured content. Never call a prototype finished.

## Result receipts and validation limits

`env_check`, `sync_check` and `reel_critic` share five states and one `RECEIPT` JSON
line on stderr: `completed` (exit 0), `partial` (3), `not-applicable` (0), `failed`
(2), `runner-error` (1). Known hard failures survive later errors. Coverage, observations,
errors and `quality_verdict.outcome` explain the scope. `env_check --json` and
`sync_check --json` output one JSON object; `reel_critic` retains its legacy report
fields and writes final status/output outcomes to `report.json`. These contracts do
not retrofit the unchanged `filmstrip`, `slop_lint` or selftest scripts; inspect their
actual output and do not relabel an unrun analysis as completed.

Partial cue coverage cannot pass the whole sync check. Mode-aware review candidates
are not hard defects. A completed media scan still needs visual inspection, listening
where required, final ratio/crop/thumbnail checks and actual player testing.

3.1.0 validation is source and controlled offline function/stub testing. Actual media
decoding, fresh animation renders, browser computed styles and preference-switch tests
were not run in this upgrade. The browser lane was unavailable; use the generated CSS
and test receipts as source evidence only. No equal-conditions blind output comparison
has established better finished animations yet. Do not claim one.

## Reference map

- `references/failure-gallery.md` - every defect class seen, how to detect it, the fix
- `references/deslop-motion.md` - stock motion, acting and copy; transplant/swap/strip/source tests
- `references/ui-motion.md` - interface motion timing, reduced motion, Lottie and CSS delivery
- `references/pipeline.md` - stage checklists, folder layout, time budgets
- `references/principles.md` - the 12 principles as code + timing tables
- `references/acting-and-story.md` - beats, visible thought, staging, short-form story
- `references/cinematography.md` - shot sizes, camera motivation, continuity, editing, reframes
- `references/lighting-and-colour.md` - colour script, values, motivated light, 2-D lighting
- `references/sound.md` - spotting, Foley, ambience, score structure, mix, loudness targets
- `references/styles.md` - 2-D character, 3-D, motion/type, explainer, product, pixel, game
- `references/assets.md` - model sheets, turnarounds, 3-D asset spec, sprite sheets
- `references/delivery.md` - codecs, bitrates, aspect ratios, reel package, accessibility
- `references/qa-rubric.md` - measured checks, visual review and honest labels
- `references/blender.md` - headless Blender recipes, API pitfalls, render budgeting
