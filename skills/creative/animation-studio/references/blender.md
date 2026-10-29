# Headless Blender

## Getting Blender
- `pip install bpy` installs Blender as a Python module. The wheel must match the
  interpreter (e.g. bpy 5.2 ships cp313 wheels; older 4.x wheels need Python 3.11).
  The wheel is ~400 MB.
- Or a Blender binary: `blender -b -P script.py -- args` (args after `--`).
- On a user's machine, ask before installing; prefer their existing Blender.

## Engines
- **Cycles CPU** works everywhere headless. Use adaptive sampling, 16-64 samples,
  OpenImageDenoise (`use_denoising=True`). Motion blur is physically correct.
- **EEVEE** needs a GPU context; on GPU-less servers it may fall back to software EGL
  (it worked here, ~5x slower than Cycles for a simple scene). Engine id differs by
  version: `BLENDER_EEVEE_NEXT` (4.2-4.x) vs `BLENDER_EEVEE` (5.x); `scene_kit.engine`
  picks whichever exists.
- **Workbench** for fast layout/animatic previews.

## API pitfalls (handled in scene_kit)
- Principled BSDF socket names changed in 4.0 (`Emission Color`, `Coat Weight`,
  `Transmission Weight`); set by trying names.
- Slotted actions (4.4+) and 5.x removed `action.fcurves`; use
  `scene_kit.fcurves_of()` which goes through channelbags.
- Relative output paths (`//`) need a saved .blend; use absolute paths headless.
- `rotation_mode`: pick the order so the moving part spins on one channel (knob on
  its own axis after a 90-degree X rotation -> `ZXY`, animate index 2).
- Name mesh data, not just objects; exporters use mesh names.

## Recipes (scene_kit)
```python
import scene_kit as K
K.reset(24, (1920, 1080), (1, 120)); K.engine("CYCLES", samples=32)
K.world((0.01, 0.01, 0.012)); K.cyclorama(); K.three_point((0, 0, 0.1), dist=0.8, key=80)
m = K.wood("Walnut"); body = K.box("Body", (0.3, 0.1, 0.17), (0, 0, 0.09), m, bevel=0.01)
cam = K.camera((0, -0.7, 0.15), (0, 0, 0.09), lens=70, dof_target=body, fstop=2.8)
K.key(body, "location", 1, interp="BEZIER"); ...
K.render_sequence("frames"); K.encode("frames", "shot.mp4")
K.export_glb("asset.glb"); print(K.asset_report())
```
- Eased keys: `K.key(obj, path, frame, interp="BEZIER", handles="AUTO_CLAMPED")`;
  holds: `interp="CONSTANT"`; machine motion: `"LINEAR"`.
- Character-style motion in 3-D: build an animkit `Channel` (same eases as 2-D) and
  bake it with `animkit_channel_bake`; secondary motion with `spring_bake`.
- Turntables: `turntable(root, start, end)` and render `[start, end-1]`.
- Framing gate before rendering any move: `frame_report(cam, hero_objects, frames)`
  gives each frame's normalised extent; `fit_rig_scale(rig, cam, hero, key_frame, frames)`
  backs a dolly off until the hero stays inside the safe margin (the radio example's
  push-in was cropping the body until this ran: end scale 0.74 -> 0.83).
- Sound for 3-D beats comes from the same animkit channels that drive the keys
  (see `build_audio` in `examples/asset_radio.py`: detent ticks from knob travel,
  static and whistle from needle position, station fades in on settle).
- No Blender in the sandbox (e.g. offline ChatGPT): write the scene script with
  scene_kit anyway and hand it over with the command line; or deliver 2.5-D in animkit.

## Render budgeting
Measure one frame first (`render_still`) and multiply. At 960x540 / 24 spp a small
product scene took ~8 s per frame (wide, little DOF) to ~23 s (close-up, shallow DOF,
bump-heavy materials) on 2 cores here. Halve resolution for previews;
use `resolution_percentage`.
