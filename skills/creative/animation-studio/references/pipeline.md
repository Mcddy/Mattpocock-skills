# Pipeline in detail

Feature studios run story -> editorial (story reels) -> art -> modelling/rigging ->
layout -> animation -> FX/simulation -> lighting -> compositing -> sound -> final.
The discipline that matters most at any scale: **timing is locked in a reel before
expensive work, and every stage gets notes before the next one starts.**

## Job folder

```
job/
  brief.md            filled templates/brief.md
  story/              logline, beat_sheet.md, script, thumbnails/
  animatic/           animatic.mp4, beats.json (frame numbers), scratch.wav
  design/             character sheets, colour script, style frames
  build/              scene/rig code (python), Blender files, assets/
  renders/            preview/ (mb=1), final/ (master), stills/
  sound/              cues.json, stems/, mix.wav, master.wav
  qa/                 reel_critic output, filmstrips, notes.md
  deliver/            masters, variants, breakdown, captions
```

## 0. Environment (gate: route chosen)
`python3 scripts/env_check.py` then `scripts/tests/selftest.py`. Note the canvas backend,
Blender availability, network, CPUs and fonts; choose the route (SKILL.md Step 0).

## 1. Brief (gate: nothing ambiguous that would change the build)
Audience; platform(s) and aspect(s); runtime; tier (SKILL.md table); style refs or
brand; deliverables (master, cut-downs, stills, GIF, assets); sound (VO? music?
licensing); deadline; what "done" means. If ambiguous and expensive, ask once.

## 2. Story (gate: want / obstacle / turn / payoff in one line each)
- Logline: "When [character] tries to [want], [obstacle], until [turn]."
- Beat sheet with seconds and frames. Beats are visible actions, not feelings.
- Product spot: the product's job is the "turn" (it solves, reveals, delights).
- Explainer: each beat is one idea transformed into the next.

## 3. Thumbnails, boards, animatic (gate: runtime and beat frames locked)
- Thumbnail every beat at stamp size: if it doesn't read tiny, it won't read big.
- Animatic: stills (or blocking renders) on the timeline at beat times with scratch
  sound. In animkit this is `Channel.stepped` + `render(..., mb_samples=1)`.
- Re-time here. After this gate, timing changes are expensive.

## 4. Design (gate: silhouettes read; greyscale value plan works)
- Characters: shape language (circles = friendly, squares = stable, triangles =
  dynamic/danger), 3-4 main colours, eyes sized to act at delivery size.
- Colour script: a strip of thumbnails showing colour/value per beat; the emotional
  turn usually lands with a colour/light change.
- Style frame: one finished frame per look before animating.

## 5. Build (gate: rig hits every boarded pose)
- 2-D: a drawing function per character with channels for every control the boards
  need (facing, squash, lean, gaze, lids, mouth, hands). Parts drawn in a fixed order
  with near/far swap on facing.
- 3-D: real scale, named parts, pivots where they rotate, rotation modes that make
  the main axis a single channel, materials named.

## 6. Layout (gate: one idea per shot, continuity holds)
- Camera per shot: framing, lens/zoom, depth layers (parallax depths), move plan.
- Check screen direction and eyelines across cuts (`cinematography.md`).

## 7. Blocking (gate: stepped poses tell the story)
- Key poses and breakdowns only. Review stills at each beat and a stepped playblast.

## 8. Spline and polish (gate: arcs, spacing, overlap, holds alive, feet locked)
- Convert to eases, add overlap and secondary, eye darts and blinks, contact detail.
- Review with character-tracked filmstrips every 2-3 frames around each beat.

## 9. Lighting / FX / comp (gate: the eye goes to the story point in every shot)
- Light passes in order: ambient grade, key, practicals (additive), rim/kick,
  atmosphere, reflections, particles, grade/vignette/grain.

## 10. Sound (gate: every contact covered; loudness on target; LRA healthy)
- Spotting from the CueSheet; ambience bed; Foley; score sections at beat times;
  mix with ducking; master (`sound.md`).

## 11. QA + delivery (gate: no HIGH flags; rubric passed; outputs verified)
- `reel_critic.py`, contact sheet, filmstrips, listen at two volumes, check
  each deliverable opens and plays (duration, fps, audio present).

## Time budgets in a sandbox (2 CPU cores, guide only)
| Work | Typical cost |
|---|---|
| 2-D 1080p frame, moderate scene | 0.3-0.8 s per sample |
| 2-D 20 s shot, 3-sample motion blur, 2 workers | ~4 min (measured, doorstep.py) |
| Cycles 960x540, 24 spp + denoise, product shot | ~8-25 s per frame |
| reel_critic on a 4 min 60 fps video | ~1.5 min |
Render previews at mb=1; keep finals for after the animation is approved.
