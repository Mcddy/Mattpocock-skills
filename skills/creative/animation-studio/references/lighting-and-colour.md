# Lighting and colour

## Colour script first
A strip of small frames, one per beat, showing palette and value. Decide where the
emotional turn lands and make the light change there (the reference shot: cool, dim
night until the window light, the only warm source, clicks on).

## Value structure
- Plan in greyscale: 3-5 value groups. The focal point gets the strongest value
  contrast; backgrounds compress into a narrow value range.
- Night scenes: deep but not crushed blacks (keep detail above ~3% luminance),
  a few bright practicals, characters separated by rim/edge light.
- Check: convert a still to greyscale; if the subject disappears, fix values not hue.

## Motivated light
Every light has a source the audience can believe: sun, sky, window, lamp, screen,
fire. Light *falls off* with distance, *colours* what it hits, *casts* shadows and
*reflects* off wet or glossy surfaces.

## 2-D lighting techniques (animkit)
1. **Albedo x light (analytic shading)**: compute each character colour as
   `base * (ambient + practical_contributions)` (doorstep `lit()`), so characters sit
   in the scene's light instead of glowing at full saturation in the dark.
2. **Key/rim inside the character layer**: draw the character in `cv.layer()`, then
   gradients with `blend="src_atop"` so light lands only on the character's pixels.
3. **Practicals**: `cv.light()` (radial, additive, falloff) and `cv.cone()` (beam
   with distance fade and soft edges) in `blend="plus"`.
4. **Contact shadows**: `cv.shadow()` multiply ellipses that shrink and fade as the
   object lifts.
5. **Wet ground**: vertical additive smears below bright sources; mirrored, blurred,
   low-alpha character reflection; sharper reflections in puddles; ripple rings.
6. **Atmosphere**: haze gradients between depth layers; a light's beam visible in rain.
7. **Grade last**: vignette (subtle), fine grain to break gradient banding.

Avoid: opaque grey "glow" discs over scenery, flat trapezoid light beams with no
falloff, light that doesn't touch the character standing in it.

## 3-D lighting (Blender)
- Start with a three-point rig (`scene_kit.three_point`), then motivate: key from the
  story light, fill from the environment, rim for separation.
- Use a cyclorama for product work (no horizon line); area lights for soft speculars.
- AgX view transform (Blender 4+) handles bright practicals gracefully.
- Emission for practicals (dial backlights, screens) plus a real light if it must
  illuminate surroundings.

## Palette building
- Pick a dominant temperature per sequence, an accent that belongs to the story
  (the courier's yellow coat), and one "event" colour reserved for the turn.
- Saturation is a focus tool: keep it highest on the subject.
- For brands: map brand colours to roles (hero, accent, background) and check
  contrast; don't paint the whole frame in brand colours.
