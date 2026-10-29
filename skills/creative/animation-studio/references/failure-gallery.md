# Failure gallery: symptom, how to detect it, fix

Every entry below was seen for real while building this skill: in the AI-generated
reel it was built to beat, in this skill's own drafts before review caught it, or in
test runs of the skill in another assistant (marked *test run*). Detection says how to
find it *without* relying on luck.

## Story and staging
| Symptom | Detect | Fix |
|---|---|---|
| Captions tell the story ("A good morning has a soundtrack") while the picture shows a static object | Watch with text hidden: does a beat still read? | Rebuild around want / obstacle / turn; let text confirm, not carry |
| Every section has the same layout (title, centred object, tagline) | Contact sheet: identical compositions in a row | Vary shot size and staging by beat; one idea per shot |
| Subject too small to act (character ~10% of frame height in an acting beat) | `review.on_screen(...)["height_frac"]`; beat stills | Wide to establish, push to medium for acting (the doorstep camera goes 1.0 -> 1.6 zoom) |
| Flat value structure (whole frame one mid tone) | Greyscale a still; histogram | 3-5 value groups; darkest/brightest at the focal point |
| Limbs or props cross the face during key beats | Character-tracked filmstrip | Attach shoulders at the silhouette edge; draw straps under the face; restage |
| *Test run:* 10 s character shot (paper bag chasing a leaf) in one locked wide with the character ~6% of frame height; 50% near-still kept "to give the story room to read" | `reel_critic` staging flag (v3.0.2: main moving subject's height per second) + near-still | Wide only to establish; medium for the tries and the give-up, close for the payoff; cut or push |
| *Test run:* a 12 s acting piece in one locked wide; the idea and the triumph play small, 7 s near-still | `reel_critic` near-still share; beat stills at thought beats | Wide to establish, push or cut to a medium for the failed reach and the idea, closer for the payoff |

## Acting and mechanics
| Symptom | Detect | Fix |
|---|---|---|
| Prop moves by itself (letter floats into the slot, arms at sides) | Filmstrip of the contact beat | Animate the hand; prop inherits the hand's spacing; prop appears only after the hand fetches it |
| Hand stops short of the prop | `review.reach_report()` (IK clamps silently) | Move the character/prop or lengthen the reach (lean, step in) |
| Prop pops into existence | Filmstrip around the fetch | Visible fetch: hand to bag, bag flap opens, prop shows, prop leaves |
| Feet skate; two-pose leg toggle | `Walk.foot_slide_report()`; filmstrip | `animkit.walk.Walk` (contact/down/passing/up, locked plants) |
| Dead holds / frozen frames | `reel_critic` frozen seconds; motion plot | Moving holds (breathing, blinks, drift) or cut; end clips on the settle, not after it |
| Metronomic constant-speed motion | `reel_critic` motion CV < 0.1 | Eases, accents, speed changes, events |
| *Test run:* pushing a heavy crate while standing upright | Filmstrip of the push: body axis stays vertical | Lean 15-25 degrees into it, feet planted behind, slow first shove, squash on each push |
| *Test run:* a foot floats free of the body during a climb | Filmstrip of the climb | Keep limbs connected at full stretch (IK with a visible leg), or restage the climb |
| Fake depth: character shrinks in place to "walk away" | Watch the ground contact: feet don't follow a ground plane | Move along the ground plane with perspective, exit frame, or cut |
| Body pitches 60-140 degrees for a few frames as a brisk walk starts or stops (acceleration lean not normalised) | Frame-by-frame strip through every walk start and stop; selftest bounds walk tilt | Fixed in walk.py (lean into acceleration capped at about 0.2 rad); always strip starts and stops, not just beats |
| *Test run:* leaning into a push, the near arm covers the mouth (shoulder did not rotate with the lean, so the face swung down over it) | Filmstrip of the push, character-tracked | Fixed in rigs.py (shoulders rotate with lean); still strip every effort beat |
| *Test run:* reaching up, the near arm crosses the eyes (character in near-profile right under the target) | Beat still of the reach | Stand back so the arm angles away from the face, and play the strain 3/4 to camera |
| *Test run:* a strain held as a dead pose (arms up, body frozen for half a second) | Filmstrip of the strain: identical frames | Effort vibrates: `curves.Tremor(channel, start, end, amp=1-2 px)` alternates sides every frame; add a breath catch on the release |
| *Test run:* the hero prop held against a busy background (biscuit in front of the full jar) | Beat still at the hold; squint | Turn or move the hand so the prop reads against a clean, contrasting area; make its key feature (the bite) face camera |
| *Test run:* the payoff (bite, savour) played in the same medium-wide as the climb | Beat stills of the payoff; near-still at the end | Cut on the action (mid-turn) to a medium; the character turns to us with the prize |
| Hop goes down instead of up (sign convention mismatch: values keyed as +down, code applied +up) | Strip through the jump; selftest checks body_dy sign | One convention everywhere: body_dy is +down; negative lifts and tucks the feet |
| A beat timed past the shot end (keys re-sort, so later actions bleed into earlier frames) | `Channel` now warns on out-of-order keys; beat stills | Lengthen the shot or re-time; never key past N |
| Continuity break when state changes (door vanished when the light came on) | Beat stills before/after every state change; diff them | State audit: list environment elements and assert each is present in every beat |

## Stock (deslop) - see deslop-motion.md
| Symptom | Detect | Fix |
|---|---|---|
| Stock gesture (thumbs-up, jump for joy, generic wave) where a specific action should be | Swap test: could any character do this unchanged? | An action from this character's want, props and situation |
| Emotion snaps from one face to another with no thought in between | Filmstrip across the change | `ExpressionTrack`: brows and eyes lead, a held realisation, blink on the change of thought |
| Everything enters at once / with one ease and one delay | `slop_lint --video` onset check; `--code` ease counts | Stagger by meaning; vary ease and distance by mass and importance |
| Sparkles, glows, gradients doing the story's job | Strip test: turn effects off, does the beat read? | Motivated light; FX only at contacts and reveals |
| Hype copy on screen ("Unleash", "seamless") | `slop_lint --text` | Name the instance; show the consequence |

## Light and colour
| Symptom | Detect | Fix |
|---|---|---|
| "Light" is an opaque grey disc that greys the wall and covers a window | Look: does the area get brighter and warmer, or just greyer? | Additive `light()`/`cone()` with falloff; never paint light with opaque fills |
| Character unlit inside a light beam | Compare character colours inside vs outside the beam | Albedo x light (`lit()` in doorstep.py) + src_atop key/rim |
| Character pasted on (full saturation in a night scene) | Character is the most saturated thing in a dark frame before the turn | Multiply albedo by the scene's ambient |
| Over-lit after a light change (character glows, loses form) | Beat still after the change; form shading still visible? | Smaller warm term; keep shadow side; key from one side |
| Procedural texture at the wrong scale (wood as stripes, grille dots huge) | Render one still at final framing before animating | Scale textures to object size; check on the hero angle |

## Camera and framing
| Symptom | Detect | Fix |
|---|---|---|
| Push-in crops the hero object | `scene_kit.frame_report()` / `review.framing_report()` | `fit_rig_scale()` or re-key the move; decide what may leave frame |
| Foreground object blocks the subject mid-shot | Contact sheet | Use occluders as wipes between shots, not during the action |
| Vertical versions are centre crops that cut the product | Look at each aspect's first/last frame | Recompose per aspect (subject whole, layout rebuilt) |
| Black frames from a 3-D camera | Mean luminance of frame 1 | Stale `matrix_world` after parenting: `view_layer.update()` first (fixed in scene_kit.parent) |

## Sound
| Symptom | Detect | Fix |
|---|---|---|
| One music loop under everything | `reel_critic` loop detection | Sections that change with the picture; silence before reveals |
| Flat mix (LRA ~1 LU) | `reel_critic` / `audio.loudness()` | Dynamics: quiet beats, swells, hits |
| White-noise "rain", "road", "train" | `reel_critic` flat-noise check; spectrogram | Textured ambience: shaped bed + discrete events + space |
| No sound on contacts | Count cues vs sounds | Every contact in the CueSheet gets a sound; `qa/sync_check.py` |
| A single SFX dominates as broadband hiss (paper, static) | Spectrogram: wide bright blocks | Lower level, low-pass, shorter envelope |
| True peak above target after encoding | Measure the final MP4, not the WAV | Master to -1.5 dBTP for AAC/MP3 deliveries |
| A silent clip that should have sound (the first 3-D example) | Spectrogram is empty | Sound from the animation: cues from channels, not guessed timings |

## Type and delivery
| Symptom | Detect | Fix |
|---|---|---|
| Default sandbox fonts | Glyph shapes (Arial/Helvetica-metric + Courier) | `fonts.fetch()` online; `fonts.best_available(role)` offline |
| "Stretch" by squashing glyphs | Stroke weights change with the stretch | Tracking, variable width axis, per-letter motion |
| Tiny metadata labels | Text height < ~3.5% of frame height | Remove or enlarge; information or nothing |
| *Test run:* title sting locks at 2.6 s of 6 s, then 3 s barely move | `reel_critic` near-still >= 45% (MEDIUM) | Reveal at 55-70% of runtime; 1.5-2.5 s moving hold; short out (`styles.md`) |
| *Test run:* logo reveal played at final lock-up size (a third of frame height): 86% near-still, then waved through as "a deliberately quiet reveal" | `reel_critic` near-still; contact sheet | Hero scale for the mark's moment, pull back to the lock-up as the name arrives (`styles.md`); "quiet" or "design choice" is not a reason |
| *Test run:* a stray accent (copper dash) shrinks during the hold with no link to the motif | Contact sheet across the hold | Anchor every element to the motif or the type, or remove it |
| *Test run:* opening second is a thin, dim outline on an empty frame | First 0.5 s of the contact sheet at phone size | Something legible by ~0.5 s; strokes >= 3 px at 1080 |
| 60 fps tween look on character work | `reel_critic` look flag | 24 fps (on 1s/2s), motion blur |
| Low-bitrate master | `reel_critic` bitrate flag (busy content) | CRF 14-18 master; let the platform compress |
| Contour bands in vignettes and soft gradients (moving grain was smoothed away by the encoder) | `reel_critic` gradient banding flag (share of soft-gradient area in flat steps) | Static dither in post (`finish.dither(img, 1.5)`): 0% flat steps at ~2 Mbps. Switching to `-tune grain` also works but cost 45 Mbps on the rainy doorstep (106 MB for 19 s) |
| *Test run:* transparent WebM held 63 of 120 frames (a render chunk failed; ffmpeg stops silently at the first missing PNG) | `deliver.count_frames(out)` vs the sequence; v3 `webm_alpha`/`prores4444`/`apng` refuse gaps and report `frames` | Re-render the missing chunk; never hand over an export whose frame count wasn't checked |
| *Test run:* outlined shapes rendered as empty outlines (`cv.circle(x, y, r, fill, stroke=..)` kept only the stroke on both backends) | Style frame: shapes hollow | Fixed in v3.0.3: fill then stroke. Still look at the first style frame before animating |
| *Test run:* shape mask leaks (sun visible outside the ring it should be clipped to) | Stills where the masked part crosses the mask edge | `blend="dst_in"` only touches pixels under the drawn mask (its bounds on the soft backend); use `vector.mask_to(cv, shape, bounds)` inside `cv.layer` |
| *Test run:* logo part keeps drifting during the end hold, so the final frame is off-model | Compare the last frame with the static artwork | Move the whole lock-up in the hold (scale 1-2%, light), never one part of the mark |
| 4-minute reel, static opening, no contact | `reel_critic --reel` | 60-90 s, best first, contact on first/last cards, breakdown |

## Environment and process
| Symptom | Detect | Fix |
|---|---|---|
| Toolkit files not visible (ChatGPT Chat mode lists only built-in skills) | `find / -name reel_critic.py` finds nothing | Use ChatGPT Work mode, or ask the user to attach `animation-studio.zip` and unzip it |
| `pip install` fails (no network) | `env_check.py` network: False | Soft canvas backend (automatic), installed fonts, hand Blender scripts to the user |
| Long render calls killed by the host | Tool call times out | Render chunks with `--frames a:b`, join with `timeline.concat` |
| *Test run:* parallel render stalled after 3 s (two workers killed out of memory; the pool waited forever) | Progress log stops advancing; fewer frames than expected | v3.0.4: `render()` sizes workers to memory (`timeline.auto_workers`, conservative on the soft backend) and, when a worker is killed anyway, halves the pool and continues from the same frame (a v3.0.2 re-test lost 10 minutes stepping 9 -> 4 -> 2 -> 1 by hand) |
| Full-frame blurred layers make renders 50x slower | Per-pass timing | Always pass `bounds=` to blurred layers |
| Declaring "done" from code alone | No stills or strips were looked at | Director's loop in SKILL.md: every claim about the picture comes from looking at frames |
| *Test run:* QA flags waved through (near-still and bitrate reported by the tool, absent from the delivery note) | Compare `report.json` flags with the note | Fix HIGH and MEDIUM; one line per LOW saying why it stays |
| Review tool tracks the wrong object (colour tracker jumped to a lit window) | Strip shows the wrong subject | `filmstrip.py` searches near the last position; pass `--seed x,y` |
