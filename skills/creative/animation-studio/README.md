# animation-studio 3.1.0 (skill bundle)

Animation workflows for film, UI, logo and loop work: method (`SKILL.md`,
`references/`), templates and toolkit (`scripts/`). Availability depends on the host.

## Package and availability
The package contains `animation-studio/SKILL.md`. Use only an authorised platform
installation flow, with a recoverable backup first. A visible skill does not prove
that bundled scripts, media tools or a browser are available. Follow the observed
host capabilities; do not change settings or install dependencies without authority.

## Verify in a new environment
```bash
python scripts/env_check.py --json           # offline capability inventory
python scripts/qa/reel_critic.py clip.mp4 --out qa --mode ui --sound silent
python scripts/qa/sync_check.py --cues cues.json --audio clip.wav --kinds step,land --json
```

Inspect scripts before executing. The broader historical selftest may render,
invoke tools and remove temporary files; it was not rerun for this revision.
`env_check --probe-network` is opt-in, only for an authorised direct TCP probe.

## 3.1.0 changes and evidence limits

- Reduced-motion CSS now emits a stable state. Existing normal keyframes and Lottie
  source remain unchanged; start/end or explicit channel overrides are supported.
- Capability reporting is offline by default and does not invent available render
  routes, fonts, proxy connectivity or memory sizing.
- Environment, sync and reel checks use `completed`, `partial`, `not-applicable`,
  `failed`, `runner-error` receipts. Existing successful helper return types and reel
  metric fields remain. Exit codes are respectively 0, 3, 0, 2, 1. No matching cues
  now means not-applicable/0; incomplete cue coverage is partial/3. Reel review flags
  alone still do not fail the process; an explicit hard sound-policy failure does.
- Film, UI, logo and loop applicability is explicit. The reel scanner does not
  implement a loop seam check and records that gap. Silent means no audio stream;
  a track containing silence is still a track and is reported separately.

Validation for this revision uses inspected source and controlled offline stubs.
Real media decoding, new animation renders, browser computed-state/preference tests
and a blind old/new output comparison were not run. No finished-output quality
improvement is claimed from source tests. Historical examples are labelled in
`scripts/examples/README.md`; their scripts and assets are preserved.

## What's inside
| Path | Purpose |
|---|---|
| `SKILL.md` | the procedure: tiers, non-negotiables, pipeline gates, routing, method |
| `references/` | failure gallery, deslop for motion and copy, principles as code + timing tables, acting/story (feature acting craft, face rig), camera, light, sound, styles (logo, data viz, stings), UI motion, assets, delivery, QA rubric, Blender |
| `templates/` | brief, beat sheet, shot list, reel breakdown, critique |
| `scripts/animkit/` | easing, keyed channels (+ effort tremor), springs/overlap, walk with locked feet, IK, canvas (Skia or numpy+PIL fallback) + light, camera, reusable character rig with face rig, expressions and lip sync, vector paths + SVG import, FX particles, kinetic type, shape morphs, render loop (opaque or transparent) + chunk concat, delivery formats (GIF, alpha WebM, ProRes 4444, APNG, captions, safe zones, loop check), web export (CSS keyframes, Lottie), audio + mastering, fonts |
| `scripts/blender/scene_kit.py` | headless Blender: materials, lights, eased keys, spring bakes, framing report + auto-fit, turntables, GLB, asset report |
| `scripts/qa/reel_critic.py` | measured QA for any video: frozen and near-still runs, main-subject size (staging), cuts, cadence, gradient banding, bitrate vs CRF, loudness/LRA, score loops, flat-noise ambience |
| `scripts/qa/slop_lint.py` | stock-motion and stock-copy check for notes, code and video (deslop) |
| `scripts/qa/filmstrip.py`, `qa/sync_check.py` | frame-by-frame review strips; sound-vs-cue timing check |
| `scripts/animkit/review.py` | beat stills, tracked strips from the scene, framing and reach reports |
| `scripts/env_check.py` | environment report and route (skia/soft, Blender, network, fonts, CPUs) |
| `scripts/examples/` | `eureka.py` (flagship character pantomime: face rig, expressions, eye darts, props, cuts), `logo_reveal.py` (client SVG -> MP4, alpha WebM, GIF, Lottie), `doorstep.py` (2-D character shot, `--review` pack), `hello_sting.py` (rig + kinetic type), `asset_radio.py` (3-D asset + product beat with sound), `bouncing_ball.py` |
