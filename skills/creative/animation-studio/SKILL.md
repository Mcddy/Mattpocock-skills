---
name: "animation-studio"
description: "Plan, build and QA short-form social video (Reels, TikTok, Shorts) and animation (character, logo, UI, loops) end to end, including hook psychology, original art, voiceover, sound, multi-agent production and posting kits."
metadata:
  revision: '3.1.0'
---

# Content Studio

Make finished video content, not drafts: a reel someone can post, a logo sting a
client can ship, a UI transition a developer can drop in. Lock purpose and timing
before polish, build every asset from scratch or from licence-clean sources, look at
real frames, measure the audio, and deliver with an honest note.

Two families of work share one pipeline:

| Lane | Typical asks | Section |
|---|---|---|
| `social` | "make a reel like this", hooks, faceless explainer/list/quiz reels, carousels-to-video, Shorts | Social lane (below) |
| `film` | character shorts, narrative spots, animated reels | Animation lanes |
| `logo` | logo stings, reveals, lock-ups | Animation lanes |
| `ui` | interface transitions, Lottie, CSS motion | Animation lanes |
| `loop` | seamless loops, GIFs, ambient pieces | Animation lanes |

Record the lane in the brief, plus required or silent audio, intentional still
intervals, target player, ratios, crops and thumbnail. A social reel can borrow
from film (acting, staging) and loop (seam) rules; mark the rest not applicable.

The bundle ships a toolkit in `scripts/`: **animkit** (2-D animation: easing, keyed
channels, springs, walk with locked feet, IK, a character rig with a face that acts,
expressions, eye darts, lip sync, light, camera, particle FX, SVG and raster artwork,
kinetic type, render loop with alpha, sound design + mastering, and exporters for
GIF, WebM/ProRes alpha, APNG, Lottie and CSS; Skia backend or a numpy+PIL fallback),
a **Blender kit** (materials, light rigs, eased keys, spring bakes, framing checks,
turntables, GLB export, asset reports), and **QA tools** (`reel_critic`, `filmstrip`,
`sync_check`, `slop_lint`, in-scene review helpers). The social lane adds a
browser-canvas reel engine and circular mixer as inline recipes (S7, S8).

## Step 0: environment, toolkit and network (always, before planning)

1. **Find the toolkit** beside this file (`scripts/`) within allowed paths. A listed
   skill does not prove its files can run. Inspect scripts before executing. If
   `scripts/` is missing, use the inline recipes in this file (they are enough to
   ship a social reel) and say the toolkit was unavailable.
2. **Probe what exists:** `python scripts/env_check.py --json` when present; otherwise
   `which ffmpeg ffprobe node python3`, `fc-list`, `pip list | grep -iE "numpy|scipy|pillow|playwright"`.
   Chromium + Playwright are often preinstalled: `require('playwright')`, `chromium.launch()`;
   never reinstall Playwright.
3. **Map the network once, cheaply, then stop.** Test the specific hosts you need
   (one `curl -s -o /dev/null -w '%{http_code}'` each). Observed in the cloud
   workspace (Oct 2026): PyPI, npm, GitHub and GitHub release assets and
   `raw.githubusercontent.com` reachable; Hugging Face, Wikimedia, Unsplash, Pexels,
   Pixabay, jsDelivr, unpkg blocked. Treat this as a hint, re-test each session. When
   a host is refused, do not route around it via mirrors or other machines; tell the
   user what is blocked and what it costs, and offer the allowlist change.
4. **Adapt the route:**
   - Soft 2-D route: numpy + PIL + a working canvas backend.
   - Browser route (preferred for board/table/type-driven social reels): HTML canvas
     in headless Chromium, frames captured with `toDataURL` (recipe below).
   - No Blender: offer a T1/T2 route only if it meets the brief; never silently
     replace a required 3-D deliverable.
   - Short tool-call limits: render in chunks (`--frames a:b`) and join with
     `animkit.timeline.concat`. Leave `workers` unset: `render()` sizes the pool to
     free memory and, if a worker is killed, halves the pool and carries on. Forcing
     `os.cpu_count()` got workers killed in a test run.
   - Cache what doesn't move: render a static set once (`Canvas(...).rgba_array()`)
     and draw it each frame with `cv.image(plate, ...)`, instead of redrawing it for
     every motion-blur sample.
   - `env_check.py --probe-network` is a separately authorised probe, never proof that
     installation is possible. `scripts/tests/selftest.py [--render]`: inspect its
     writes and cleanup first. A capability inventory is not a rendered test.
   - On a user's own machine, ask before installing anything.

## Honest fidelity tiers (say which one you're delivering)

| Tier | What it is | Achievable here |
|---|---|---|
| T1 Motion design | type, UI, infographics, logo stings, explainers, board/list reels | Depends on verified tools and inspected output |
| T2 Stylised 2-D character | procedural rigs, keyed acting, painterly light, code-drawn illustration | Needs verified backend; rig and drawing simplicity limit depth |
| T3 Stylised 3-D | Blender (Cycles CPU / EEVEE), products, props, simple rigs | Where Blender exists; render time is the limit |
| T4 Feature film / photoreal | sculpted rigs, hand-keyed performance, sims, film-res path tracing, real photography | No. Apply the process; never label output "Pixar quality" or "realistic" when it is illustrated |

If a brief asks for "Pixar level", clarify the intended style, craft and outcome;
state the achievable tier and any gap; do not redefine a binding quality target as
process compliance. Matching a reference requires inspected side-by-side frames,
not shared vocabulary. State the tier in the delivery note.

## Social lane (Reels, TikTok, Shorts)

### S1. Deconstruct the reference (when the user supplies one)
Copy the upload to the working dir, then:
```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact ref.mp4
ffmpeg -v error -i ref.mp4 -vf "fps=2,scale=200:-1,tile=7x4" -frames:v 1 sheet.jpg   # look at it
ffmpeg -v info -i ref.mp4 -af "volumedetect,silencedetect=n=-35dB:d=0.3" -f null -   # VO/music rhythm
```
Write down: format (table, list, quiz, story, POV), hook in the first second, time
to first payoff, number of reveals, loop point, what is withheld, text sizes, where
it breaks safe zones, sound role (VO, music, SFX). Screen recordings include
platform UI and swipes; discount those when timing.

### S2. Brief (fill before building)
Purpose (follows, comments, sends, sales), audience, platform(s), runtime, loop or
not, the one withheld thing that keeps people watching, the CTA, the voice (gender,
mood), reveal count, safe-zone envelope, deliverables (master, alt voice, posting
kit, source). The user's stated length wins: "longer" usually means 20-45 s. If the
music bed loops, make the runtime a multiple of the bed length (e.g. 32 s = 4 x 8 s
at 120 BPM) so the loop seam stays musical, and say why it is not exactly 30.

### S3. Attention and retention design (evidence-graded; never oversell the science)
Users often frame this as "trigger the amygdala". Build the effect, but keep the
claims honest: the robust levers are salience and curiosity, not a specific brain
region, and no study measures amygdala activity in a feed.

| Lever | What to build | Evidence |
|---|---|---|
| Motion onset + sound onset at 0 s | something large starts moving on frame 1 with a transient (sting, thump, hiss) | Strong (Abrams & Christ 2003 motion onset); moderate for audio-visual capture |
| Size / contrast / centre | hook subject fills a large share of frame 1, high contrast, centre-upper | Strong salience basics; the exact % is heuristic |
| Threat or looming cue | snake/spider/strike-at-camera, looming zoom | Moderate and contested: snake detection replicates vs flowers (Öhman 2001, LoBue & DeLoache 2008) but not vs other animals (Lipp 2004), and Zsido 2024 found snakes slower than rabbits. All photo stimuli; cartoon/emoji untested. Use it, but the looming motion carries more weight than the species |
| Payoff in under 1 s | first reveal by ~0.6-0.8 s | Moderate (curiosity + completion signals) |
| Information gap | visible "?" cells, withheld answers, list numbering | Strong (Loewenstein 1994; Kang et al. 2009) |
| Self-relevance | "Dreamt about a snake?" second-person questions, common experiences | Strong for memory (Symons & Johnson 1997); weak for watch time |
| Prediction error | a counter-intuitive reveal, tagged TWIST, every 2-3 reveals | Strong mechanism, weak feed evidence |
| Re-arousal | a pattern interrupt every ~8-12 s: punch-in, peek, second strike, colour shift | Practitioner lore; cheap to do |
| Pointing cue | pointer/finger/arrow that moves to the next item before it reveals | Moderate (arrow cueing) |
| Seamless loop | last frame leads into the first (wind-up into the opening strike) | Lore; TikTok weights completion (official) |
| Sends | CTA or caption written to be sent to a friend | Moderate: Mosseri says sends per reach matter most for non-follower reach |
| Zeigarnik "open loops" | do not claim people remember unfinished things better | Weak (2025 meta-analysis null); the resume tendency (Ovsiankina) is the defensible version |

Concrete rules: payoff < 1 s; first frame has the hook subject big and moving;
pointer never covers unrevealed content for long; one surprise early; re-arousal
every 8-12 s; CTA end card that matches the caption; do not put "amygdala" or
"hard-wired fear" in copy (invites correction comments).

### S4. Platform reality (re-verify each time; these change)
- Instagram ranking (Mosseri, Jan 2025): watch time, likes per reach, sends per reach.
- Originality: Instagram recommends only the original of identical content; new
  voiceover or material edits are not replaced. TikTok makes unoriginal re-uploads
  and "extremely short clips" ineligible for For You. So: copy formats, never footage
  or audio; build every asset; change rows/items; no watermarks; don't cross-post a
  TikTok-watermarked file.
- Safe-zone envelope for one 1080x1920 master: critical content inside
  **x 65-940, y 270-1440** (top ~270, bottom ~480, left 65, right rail 140). Published
  specs disagree; this is the conservative intersection.
- Loudness: master around -14 to -16 LUFS integrated, true peak <= -1 dBFS.

### S5. Content and copy
- Items people have actually experienced beat clever ones. Order: threat or high
  arousal first, then a twist by item 3, most-asked items held for later.
- Labels <= 10 chars; reveals 1-2 words, <= 14 chars per line, max 2 lines.
- Voice lines as "Question? Answer." so the reveal lands on the answer; keep each
  line <= ~2.6 s.
- Folklore, astrology, "facts" and tips: tag the frame honestly ("Traditional dream
  folklore") and never present entertainment as science. No invented stats, quotes,
  testimonials or proof on screen.
- Posting kit: 3 captions (one comment prompt, one built to be sent, one curiosity),
  a pinned comment, 5-8 hashtags (broad + niche), follow-up/part-2 plan, timeline table.

### S6. Assets (licence-clean, logged in an origin ledger)
- **Icons:** Microsoft Fluent 3D emoji via npm `@lobehub/fluent-emoji-3d` (MIT,
  256 px WebP, `assets/<codepoint>.webp`; default tone is the bare codepoint).
  Convert to PNG with PIL. `@fontsource/noto-color-emoji` rendered blank in headless
  Chromium; don't rely on colour-emoji fonts there.
- **Fonts:** `@fontsource/*` packages from npm (e.g. `source-serif-4`, `anton`), loaded
  by relative CSS path; `await document.fonts.load(...)` before the first frame.
- **Hero illustrations** (e.g. a menacing creature when photos are unreachable):
  draw them in code (SVG via Chromium) as layered PNGs on one registered canvas
  (body / head_closed / head_open / tongue or equivalent) plus `anchors.json`. Brief
  the drawing for the emotion (menace: front-on, open mouth, fangs, slit pupils,
  brows angled down, rim light, dark values that read on white), review at full size
  AND at the on-screen size, iterate at least 3 times. A cute emoji does not read as
  threat; users notice.
- **Photos:** only public-domain/CC0/licensed sources the user supplies or that are
  reachable; record source and licence. Never trace copyrighted images; no real people.
- **Voice:** Kokoro TTS (Apache-2.0): `pip install --break-system-packages kokoro-onnx soundfile`,
  model + voices from GitHub releases
  (`thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx`
  and `voices-v1.0.bin`). Strong voices: `am_michael` (male narrator), `af_heart`
  (female). Speed ~0.95, 80 Hz high-pass, trim with 30 ms pads, peak -3 dBFS, 48 kHz.
  Piper voices need Hugging Face (often blocked). eSpeak is robotic; don't ship it as
  "realistic". Render a male and a female set so the user can choose.
- **Music and SFX:** synthesise with numpy/scipy: sting (transient + sub thump with
  a 110-300 Hz layer for phone speakers + dissonant stab), hiss (4-9 kHz noise,
  fast attack, flutter), whoosh (band-pass sweep), tap, pitched pops in the bed's key,
  and an exactly-N-second seamless bed (verify: concatenate 3 copies, max sample jump at joins).

### S7. Build engine (board/list/quiz reels; recipe)
One HTML file with a `<canvas width=1080 height=1920>`, a pure `render(t)` and a
`window.CFG` timeline injected per render. Everything is a function of time so any
frame can be re-rendered alone.
- **Timeline JSON drives everything:** `beats [{row, t (pointer tap), pop (reveal)}]`,
  `strike2 {t, hold}`, `peeks [t]`, `endcard {t0}`, `clearAt`, `loop`, `vo [{file, t}]`.
  Build it from measured VO: find each line's question/answer pause (longest
  low-energy run between 15-85% of the file, 10 ms RMS frames, threshold peak-30 dB),
  pop the reveal at `start + pause_start + 0.05`, tap the pointer 0.12 s before the
  line starts, 0.5-0.75 s gaps between lines.
- **Pointer on a stick:** pivot off-screen (bottom right, e.g. 1010, 2450); angle =
  `atan2(dx, -dy)` to the target, length = distance; ease-in-out swing (~0.42 s) with
  a sine "lift" off the board and a small poke on arrival; retract it during strikes
  and the end card and let it rise in during the first 0.5 s (motion onset).
- **Hook creature:** interpolate between a cell pose and a big centre pose with
  geometric zoom (`size = cell * (big/cell)^u`); jaw open crossfades closed/open
  head layers; tongue scaleY from its anchor; screen shake on impact; radial dim
  behind it; clip to its cell when settled; reframe from a tight head crop in the
  cell to the full figure when big. Idle sway + periodic tongue flick so the threat
  never fully settles. Wind-up in the last 0.4 s leads into the opening strike.
- **Reveals:** spring scale (`1 - e^{-d t} cos(2 pi f t)`), a brief highlight flash,
  a different colour + "TWIST" tag for counter-intuitive items, active-row highlight,
  a camera punch-in (~3.5%) on each tap, grey "?" in unrevealed cells.
- **Capture:** launch Chromium with `--allow-file-access-from-files` (otherwise
  `toDataURL` throws "Tainted canvases"), `page.addInitScript(c => window.CFG = c, cfg)`,
  then per frame `evaluate(t => { render(t); return canvas.toDataURL('image/png') })`.
  ~13 fps capture at 1080x1920; 960 frames in about a minute.
- **Encode:** `ffmpeg -framerate 30 -i f%04d.png -i mix.wav -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart out.mp4`.

### S8. Mix (circular, sample-accurate)
Place every clip with `idx = (arange(len(x)) + round(t*SR)) % N` so anything that
crosses the end wraps to the start (a seamless loop). Tile the bed to N. Duck the bed
under the voice (smoothed VO envelope -> up to -7 dB) and harder during big moments.
Normalise the summed float mix to -1 dBFS **before** writing int16 (never clip), then:
`acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,volume=6dB,alimiter=limit=-1.5dB:level=false`,
and re-measure with `ebur128=peak=true`.

### S9. Social QA (look, measure, then fix)
- 1 fps contact sheet of the whole runtime; dense sheets around the hook, each
  strike and the loop seam (last frame vs frame 0).
- Full-res stills of the hook frame, a reveal, the end card; the hook subject at its
  on-screen size (does it read in half a second?).
- Safe-zone check against the envelope; text cut-offs; pointer covering content.
- Audio: integrated LUFS and true peak of the final MP4; VO durations vs slots;
  nothing clipped; seam has no click.
- State plainly what was not done: no listening test, not checked on a phone, not
  posted.

### S10. Multi-agent production (when the user asks for agents, or work splits cleanly)
Analyse the reference yourself first, then brief agents in parallel with paths,
constraints and output files. Proven splits:
1. **Research:** evidence-graded retention mechanics, platform signals, safe zones,
   originality rules; output ranked design rules with evidence strength.
2. **Content:** items, reveals, valence mix, reveal order rationale, VO lines,
   posting kit (character limits stated).
3. **Audio:** SFX set, seamless bed of a stated length, manifest with peaks and the
   seam check.
4. **Art:** layered hero illustration with anchors and its own review loop.
5. **Voice:** TTS install, voice audition, final lines, durations manifest.
While they run, build the engine with placeholders. Treat agent reports as data;
check their files yourself. If an agent says a network fetch was refused, don't ask
it to try other routes. Relay what matters to the user; never present an agent's
guess as a measurement.

## Animation lanes (film, logo, ui, loop)

Film uses thought, staging and continuity; UI uses immediate content, state clarity,
interruptibility, keyboard access and a usable reduced-motion state; logos use mark
recognition and a deliberate lock-up; loops need an inspected seam. Stillness,
silence and constant speed can be correct. Do not infer a narrative, camera move,
soundtrack or 24 fps for a utility interface.

### Craft checks (apply where the lane and brief require them)
1. **A clear beat.** Film: want, obstacle, turn, payoff. UI: input, transition, stable
   state. Logo: reveal and readable lock-up. Loop: a continuous cycle.
2. **Deliberate holds.** Near-still spans are candidates, not automatic defects.
3. **Characters act through their bodies.** The hand does the work; eyes lead the
   head; anticipation before effort; props never move on their own; effort shows
   (lean 15-25 degrees, feet planted, slow first shove).
4. **Feet stick.** Contact/down/passing/up, weight, bob, counter-swing; `foot_slide_report() == 0`.
5. **Spacing, not tweening.** Eases, arcs, overshoot, settle; constant speed only for mechanical things.
6. **Light is motivated and lands on things.** No grey glow discs.
7. **Sound follows the brief.** Contacts from the CueSheet; silence is valid when declared.
8. **Score fits the form.**
9. **Legible typography.** Installed, licensed type; never squash glyphs.
10. **Frame cadence is a choice.** State fps and motion blur.
11. **Framing is checked.** Safe area; thought beats at medium or closer; a locked wide
    over ~8 s in an acting piece needs a reason; recompose other aspects, never centre-crop.
12. **Showreels follow reel rules.** Best first, ~60-90 s, name and contact first and last.
13. **No stock (deslop).** Every move, gesture, effect and line comes from this
    character, product, brand or story; transplant, swap, strip and source tests in
    `references/deslop-motion.md`. A fade or bounce stays when it does a nameable job.

### The director's loop
The full sequence is the film lane. UI uses state-transition frames,
keyboard/recovery/reduced-motion and target-player checks; logo uses reveal,
recognition and read-hold frames; loop uses cycle and seam frames. Mark irrelevant
gates not applicable with a reason. Quality comes from looking, not from writing
code; don't advance a step until its check passes. Every claim about the picture
comes from frames you looked at; every claim about sound from a measurement.
1. **Brief + beats** (`templates/brief.md`, `templates/beat_sheet.md`): one sentence
   the piece must communicate; for characters, the thought behind each beat. Encode
   beats as one dict (`B = dict(...)`) or timeline JSON that drives every channel, so
   re-timing is one edit.
2. **Style frame first.** One full-res still of the key moment: where does the eye
   land; is the subject big enough (20-35% of frame height for action, 35-50% for
   thought); do values group in greyscale; is every bright thing motivated; are fonts real?
3. **Block:** `review.beat_stills(draw, B, out)`; silhouettes, staging, continuity.
4. **Spline + preview:** cheap full render, subject-tracked filmstrips every 2-3 frames;
   fix skating, pops, hands stopping short (`review.reach_report`), dead holds,
   straight paths, simultaneous starts.
5. **Camera check:** `review.framing_report()` or `scene_kit.frame_report()`.
6. **Light + sound pass** where applicable; spectrogram; `qa/sync_check.py` (median offset < 1 frame).
7. **Final render** at the brief's fps and blur policy.
8. **QA:** `qa/reel_critic.py VIDEO --out DIR --mode MODE --sound auto|required|silent`
   (`--allow-still START:END` for intended holds); contact sheet, filmstrips,
   `references/qa-rubric.md`, `references/failure-gallery.md`, and
   `qa/slop_lint.py --text <copy> --code <scene.py> --video <final>` plus the
   transplant, swap, strip and source tests by eye. Fix hard defects; resolve review
   flags by inspection, recording kept findings and reasons. Film heuristics do not
   automatically fail UI, logo or loop work; loop seam checks stay partial until a
   separate seam test is recorded.
9. **Deliver** with an honest note.

Self-review: what would a supervisor circle first? Does each moving or still state
serve its purpose? Who performs the key action? Where is the eye in each beat? What
lights each bright thing? Does required contact audio align? Does it read with the
sound off? Is anything cropped, tangent or covering a face?

### Pipeline gates
| # | Stage | Artefact | Gate |
|---|---|---|---|
| 1 | Brief | brief.md | audience, platform, length, aspect, tier, deliverables known |
| 2 | Purpose | logline or state/mark/loop beat sheet | lane-specific action and final state clear |
| 3 | Animatic | beat stills + scratch sound | runtime and beat frames locked |
| 4 | Design | style frame, colour script, designs | style-frame questions answered |
| 5 | Build | rigs, assets | rig hits every boarded pose; reach checked |
| 6 | Layout | camera per shot, depth layers | framing clean; one idea per shot |
| 7 | Blocking | stepped poses | poses read as stills |
| 8 | Spline + polish | eased channels, overlap | filmstrips clean |
| 9 | Light / FX / comp | passes, grade | eye lands on the story point |
| 10 | Sound | Foley, ambience, score, master | sync coverage; loudness on target |
| 11 | QA + delivery | reel_critic, rubric, masters + variants | hard defects fixed; gaps explicit |

Details: `references/pipeline.md`.

### Tool routing (bundled toolkit)
| Need | Use |
|---|---|
| Environment + route | `scripts/env_check.py`, `scripts/tests/selftest.py [--render]` |
| 2-D character, motion design, explainers, type | `animkit` (`canvas` picks skia or soft); `scripts/examples/doorstep.py` |
| A character, fast | `animkit.rigs`: `BlobRig(RigStyle(...))` + `Performer(channels, walks)` (`examples/hello_sting.py`) |
| Facial acting, dialogue | `RigStyle(face_rig=True)`, `face.ExpressionTrack`, `face.eye_darts`, `lipsync.from_audio(wav)` (`examples/eureka.py`) |
| Client logo or artwork | `animkit.svg.SVGArt(path)`, stroke `draw_on`, masks via `vector.mask_to` (never `blend="dst_in"`); Lottie `layer_from_vpaths(mask=...)` (`examples/logo_reveal.py`) |
| Contacts, impacts, weather | `animkit.fx`: `dust_puff`, `sparks`, `confetti`, `snow`, `steam`, `Burst`/`Emitter` |
| Formats: GIF, alpha, loops, captions | `timeline.render_rgba` + `animkit.deliver`: `gif`, `webm_alpha`, `prores4444`, `apng`, `loop_report`, `write_srt`/`write_vtt`, `draw_caption`, `safe_zone` |
| Web / app motion | `animkit.web`: `css_animation`, `Lottie`, `lottie_from_svg`; `references/ui-motion.md` |
| Paths, draw-on | `animkit.vector.VPath`, `draw_fill`, `draw_stroke` |
| Kinetic type, numbers | `animkit.typeanim`: `KineticText`, `stagger_in`, `pop_on_beats`, `draw_number` |
| Morphs | `animkit.shapes.morph(a, b, t)` |
| 3-D props, products | `scripts/blender/scene_kit.py` (`examples/asset_radio.py`) |
| Pixel art | animkit at low res, integer upscale, locked palette |
| Sound design, score, master | `animkit.audio` + ffmpeg |
| Review | `animkit.review`, `qa/filmstrip.py`, `qa/reel_critic.py`, `qa/sync_check.py`, `qa/slop_lint.py` |
| Fonts | `animkit.fonts.fetch(family, weight)` online; `best_available(role)` offline; npm `@fontsource/*` when PyPI/npm are the only open routes |
| Social board/list/quiz reels | browser canvas engine (S7) + circular mixer (S8) |

Performance: bound every blurred layer (`cv.layer(bounds=...)`). Historical: a
1080p 19 s shot with 3-sample blur took ~4 min on 2 CPUs (Skia); soft ~2x slower.

### Minimal shot (teaching pattern)
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
    cv.shadow(960, 866, 60 * (0.5 + y(f) / 1640), 10)
    with cv.at(960, y(f) + 44, 0, sx, sy):
        cv.circle(0, -44, 44, "#E8A33D")

render(draw, 48, "ball.mp4", mb_samples=3)
```
Examples under `scripts/examples/`: `eureka.py` (flagship pantomime), `logo_reveal.py`,
`doorstep.py`, `hello_sting.py`, `asset_radio.py`, `bouncing_ball.py`.

## Asset creation mode
Deliver assets someone else can use without asking (`references/assets.md`):
characters (turnaround, height chart, 6-12 expressions, hands, hex callouts, rig
controls); 3-D (metres, named parts, pivots, UVs, PBR, GLB, `asset_report()`,
turntable); sprites (integer scale, locked palette, sheet + JSON); backgrounds
(parallax layers, value room); layered illustrations (one registered canvas,
`anchors.json`, a full-size and an on-screen-size preview).

## Critique mode
1. Measure: `qa/reel_critic.py VIDEO --out DIR --mode MODE --sound POLICY [--reel]`,
   `qa/slop_lint.py --video VIDEO`; for social, also loudness, safe zones, time to
   first payoff, re-arousal spacing, loop seam.
2. Look: contact sheet, filmstrips of key beats, full-res stills.
3. Judge against `references/qa-rubric.md`, `references/failure-gallery.md` and S3.
4. Findings as evidence -> consequence -> fix, ranked, with timestamps; separate
   measured facts from judgement; credit what works (`templates/critique.md`). If
   you can, prove the main fix by rebuilding one beat and measuring before vs after.

## Honesty and safety rules (all lanes)
- Engineer attention, not deception: no fake proof, fabricated stats, invented
  testimonials, impersonation of real people or brands, or medical/financial claims
  presented as fact. Entertainment folklore is labelled as such.
- Copy formats freely; never copy footage, audio, characters, logos or artwork. When
  a reference uses a known character, make an original one.
- Don't put a user's AI workflow into client-facing copy unless AI is the subject.
- Never call a prototype finished; never call an illustration a photo.

## Reporting the result
Write the note the way `references/deslop-motion.md` section 5 says: lead with what
was made and what the user can do with it; name specifics; no hype.
State: tier; backend (skia/soft/browser canvas/Blender); runtime, resolution, fps;
what was rendered and which frames were inspected; what was measured (LUFS, peak,
sync, foot slide, framing, safe zone); every QA flag and what you did about it (a
low bitrate on flat graphics at CRF 16-18 is expected, say so); what
was not verified (no listening test, not on a phone, not posted); known limits (e.g.
"the mouth interior is the weakest part of the drawing"). Keep an asset-origin
ledger (supplied, original, generated, synthetic, sample, licensed + source/licence
and substitutions); carry it in sidecars and handoffs; flag fiction, placeholders
and sample content.
For social work also deliver: master MP4, alternate voice cut, posting kit
(captions, pinned comment, hashtags, timeline), and editable source (engine,
timeline JSON, mixer, art sources, audio stems).

## Result receipts and validation limits
`env_check`, `sync_check` and `reel_critic` share five states and a `RECEIPT` JSON
line on stderr: `completed` (0), `partial` (3), `not-applicable` (0), `failed` (2),
`runner-error` (1). Known hard failures survive later errors. `env_check --json` and
`sync_check --json` output one JSON object; `reel_critic` writes final outcomes to
`report.json`. `filmstrip`, `slop_lint` and selftest don't use receipts; inspect their
actual output and never relabel an unrun analysis as completed. Partial cue coverage cannot pass the whole sync check. Review
candidates are not hard defects. A completed scan still needs visual inspection,
listening where required, ratio/crop/thumbnail checks and player testing. The
reel_critic scanner has no loop-seam check; record the seam inspection separately.

Validation status for 4.0.0: the social lane (S1-S10) was exercised end to end on a
32 s board reel (reference deconstruction, five parallel agents, browser-canvas
engine, Kokoro VO, synthesised bed/SFX, code-drawn layered cobra, circular mix at
-14.4 LUFS / -0.9 dBFS, contact-sheet and seam inspection). No listening test or
on-phone check was recorded. The bundled animkit toolkit and its 3.1.0 limits are
unchanged (source and offline stub validated; not re-rendered; browser computed
styles and reduced-motion preference tests not run). No blind old/new output
comparison has been made; do not claim one.

## Reference map
- `references/failure-gallery.md` - defect classes, detection, fixes
- `references/deslop-motion.md` - stock motion/acting/copy tests
- `references/ui-motion.md` - interface timing, reduced motion, Lottie/CSS
- `references/pipeline.md` - stage checklists, folder layout, budgets
- `references/principles.md` - the 12 principles as code + timing tables
- `references/acting-and-story.md` - beats, visible thought, staging
- `references/cinematography.md` - shot sizes, camera motivation, continuity
- `references/lighting-and-colour.md` - colour script, values, motivated light
- `references/sound.md` - spotting, Foley, ambience, score, loudness
- `references/styles.md` - 2-D, 3-D, motion/type, explainer, product, pixel
- `references/assets.md` - model sheets, turnarounds, sprite sheets
- `references/delivery.md` - codecs, bitrates, aspect ratios, accessibility
- `references/qa-rubric.md` - measured checks, visual review, honest labels
- `references/blender.md` - headless Blender recipes and pitfalls
- This file, sections S1-S10 - social short-form lane (self-contained recipes)