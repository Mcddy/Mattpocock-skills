---
name: media-compiler
description: Compile a typed data-bound procedural scene graph into deterministic SVG and PNG frames with rational timing and a warm scrub preview. Use for programmed data stories, geometry-based animation and generative visual content, not another fixed storyboard or arbitrary code renderer.
---

# Media Compiler

Author editable scenes whose geometry expresses real data or a deliberate visual rule. `scripts/compile.py` implements typed groups, rectangles, circles, lines and SVG text, numeric data bindings, keyframe interpolation and bounded sine/cosine functions. This is a scene compiler, not a template slide deck. Read [the scene contract](references/scene.md) before authoring.

Run `python scripts/compile.py scene.json --out-dir fresh-output`. Inspect the specification and renderer first. No expressions, plugins, external images/fonts, remote URLs or arbitrary imported code are evaluated. Use actual data labels, units and source locators. Keep synthetic examples labelled synthetic. Map narrative semantics to data bindings; unsupported reference or malformed timing must fail rather than render a plausible blank.

Choose SVG for typography and accessible vector composition. The stdlib PNG rasteriser supports geometry only and explicitly refuses text nodes in PNG scenes. It does not claim typography, antialiasing or production video quality. Both bundled examples produce actual PNG and SVG geometry frames, with captions and numeric semantics in the manifest/preview. For MP4, hand the verified numbered PNG frames, exact FPS and manifest to an existing reviewed video engine. No automatic subprocess, dependency installation or video encoding occurs here.

Preview the real compiled frames in `preview.html`: keyboard-operable scrubber, warm/light and dark appearance, caption and frame index, selected SVG export, and preview-state JSON export/import with strict range checking. Editable scene JSON reopens through compilation. The preview cannot recompile a changed data/model input; re-run the compiler and compare dependency/frame hashes. No result badge persists after changing a specification.

Deliver scene JSON, actual frames, frame times, dependency hash, per-frame hashes and semantic fields. Check a known frame's data-bound dimensions, invalid bindings, exact frame count/timing and deterministic rerun. A source hash proves byte identity, not visual readability or correct storytelling. Inspect exported media at useful sizes before claiming presentation quality. Use concise subject-specific captions, intentional spacing and a restrained palette.

Should trigger: “Make a programmatic animation that binds the bars to this dataset” or “render a procedural orbital study.” A narration-to-video storyboard alone routes to the existing video workflow. Computational Design owns fabrication geometry constraints. Authorship: Codex continuation; independent acceptance is separate.
