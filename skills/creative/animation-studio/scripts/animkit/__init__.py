"""animkit - principle-driven procedural animation toolkit (animation-studio skill).

Modules
  easing      easing family, CSS cubic-bezier, springs, steps, intent presets
  curves      Channel/Key pose-to-pose curves, holds, moving holds, on-twos, ArcPath, Tremor (effort vibration)
  principles  squash/stretch, anticipation, springs, overlap chains, blink, breathe, 2-bone IK
  walk        side-view walk with locked foot plants and contact events
  canvas      one drawing API, two backends: Skia (fast) or numpy+PIL "soft" (offline sandboxes)
  finish      motion-blur accumulate, vignette, grain
  camera      2-D camera: parallax, eased moves, handheld drift, impact shake
  rigs        BlobRig + Performer: a reusable, restylable character that already follows the rules
  face        expression library, ExpressionTrack (brows and eyes lead the mouth), eye_darts
  lipsync     mouth channels from a voice track (open / round / width, on twos, one frame early)
  vector      VPath: beziers, transforms, trim (draw-on), point_at, mask_to, circle_vp
  svg         SVGArt: load a client's SVG logo/artwork as animatable parts
  fx          particle bursts and emitters: dust, sparks, confetti, snow, steam (pure in f)
  typeanim    kinetic typography: per-letter stagger, tracking, pops synced to cues
  shapes      circle/rect/star/wave builders, arc-length resample, morph(a, b, t)
  review      beat stills, tracked strips, framing and reach reports (check before rendering)
  timeline    Beats, CueSheet (sound sync), render loop -> ffmpeg (parallel), render_rgba, mux, chunk concat
  deliver     GIF (size budget), alpha WebM, ProRes 4444, APNG, loop check, captions, safe zones
  web         CSS keyframes (cubic-bezier / linear() springs, reduced motion), Lottie (masks, null parents)
  audio       SFX library, textured ambience, score helpers, mixer, EBU R128 mastering
  fonts       real typefaces: npm @fontsource online, best installed face offline
"""
__version__ = "3.0.4"
