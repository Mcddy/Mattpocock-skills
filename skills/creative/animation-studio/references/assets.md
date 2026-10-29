# Asset creation

Deliver assets another artist can pick up cold.

## Character package
1. **Model sheet / turnaround**: front, 3/4 front, side, 3/4 back, back on one
   baseline, same scale, with horizontal guide lines at eyes, shoulders, hips, knees.
2. **Height chart**: in "heads", next to a reference (another character, a door).
3. **Expression sheet**: neutral, happy, sad, angry, surprised, scared, thinking,
   determined, plus 2-4 character-specific ones. Eyes and brows carry most of it.
4. **Pose sheet**: 6-8 action poses that show personality (silhouette-tested).
5. **Hands**: open, fist, point, grip, relaxed.
6. **Colour callouts**: hex per part, plus lit/shadow variants for key lighting setups.
7. **Construction notes**: base shapes, proportions, do/don't.
8. **Rig notes** (if procedural): list of controls and ranges.

With animkit: render each view by driving the rig's channels (facing -1/0/1,
gaze, lids, squash) on a neutral background; tile with PIL; label with a real font.

## 3-D asset spec
- Units metres; +Z up in Blender (glTF converts to +Y up); origin at the base centre
  or the natural pivot; scale applied; rotation modes chosen so moving parts rotate on
  one channel.
- Naming: `Asset_Part` objects; mesh data named the same; materials named by surface.
- Bevel hard edges; smooth shading by angle; no n-gons on deforming parts.
- UVs on everything (`smart_project` minimum); procedural shaders documented, or
  baked to textures if the target engine needs them.
- Export GLB (`scene_kit.export_glb`) and report (`asset_report`): triangles, size,
  materials, missing UVs.
- Presentation: 4-view sheet + seamless turntable (render [start, end-1]).
- Budgets (guide): hero prop 5-30k tris, background prop 0.5-5k, mobile game props < 2k.

## Sprite package
- Sheet PNG (uniform cell size, transparent background) + JSON (frame rects, durations,
  pivots, loop flags) + a preview GIF/MP4 at integer scale.
- Consistent pixel density across all sprites and tiles; palette file included.

## Environment / background package
- Layers separated by depth (sky, far, mid, action, foreground) with suggested
  parallax factors; overscan for camera moves.
- Colour keys for each lighting state (day/dusk/night) and a value thumbnail.

## Handoff checklist
- [ ] Names are meaningful and consistent
- [ ] Scale/units stated; pivots correct
- [ ] Sheet/preview renders included
- [ ] Source files (python scene code / .blend / layered PNG) included
- [ ] Licences stated for fonts and any third-party material
