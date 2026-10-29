# Acting and story for short-form animation

## Story shape (any length)
- **Want**: what the character (or product, or idea) is trying to do.
- **Obstacle**: what stops it. Without one there is no scene, only a demo.
- **Turn**: the moment things change (a decision, a reveal, a reversal).
- **Payoff**: the consequence the audience feels, ideally shown not captioned.

Example (the reference shot `examples/doorstep.py`): a courier wants the last
delivery to land; the house is dark (obstacle); they give up and turn away; the
light clicks on (turn); someone waves, the courier hops (payoff).

Short forms:
- 5-10 s sting / logo: setup -> twist -> resolve on the mark.
- 15-30 s spot: problem shown -> product acts -> life after, product hero.
- 30-90 s explainer: question -> 3-5 transformations -> answer the viewer can repeat.
- Reel: not a story, but each excerpt should contain a complete beat.

## Writing beats that animate
- Write actions a camera can see: "looks up at the dark window" not "feels hopeless".
- Give each beat a frame count. If two beats share the same pose, merge or change one.
- Let the audience get ahead of the character once (dramatic irony) and behind once (surprise).
- Captions that explain the image ("A mark that holds") are a sign the image isn't doing its job.

## Making thought visible
1. **Eyes first.** Gaze changes 2-4 frames before the head, head before body.
2. **Think beat.** Before a decision: a still moment (moving hold), a blink, a small shift.
3. **Anticipate intention.** Weight shifts toward where the character is about to go.
4. **Reaction > action.** The take after an event sells it more than the event.
5. **Contrast.** Fast after slow, big after small; uniform energy reads as nothing.

## Staging an idea
- One idea per moment, readable in silhouette.
- Profile and 3/4 views read best for actions with the hands; front view for emotion.
- Keep the face and the hands clear of each other during key beats.
- Entrances and exits are beats too: enter with purpose, exit with a final note.

## Pantomime checklist (no dialogue)
- Can a viewer describe the story with the sound off? Then with the picture off?
- Is every prop handled by a hand (or an obvious force)?
- Does every important change have a cause on screen?

## Comedy timing
- Setup, beat (pause), payoff. The pause is usually 6-12 frames longer than feels safe.
- Hold the reaction; cut on the laugh, not after it.

## Studio process worth copying
- Story reels: boards cut to scratch audio and watched as a film, many times, before
  production. Rework the reel, not the render.
- Notes sessions: specific, about the film not the person, focused on what isn't
  working and why, leaving the fix to the author. Run the rubric in `qa-rubric.md`
  as your notes session.
- Colour script: plan the emotional arc in colour and light before lighting shots.

## Feature-animation acting craft (what Pixar and Disney animators actually do)
Process, scaled to this toolkit:
1. **Know the thought, not the move.** For every beat write what the character thinks
   ("it's too high", "the crate!", "mine"), then find the action that shows that thought.
   A move without a thought behind it is stock (`deslop-motion.md`).
2. **Thumbnail the key poses.** Render `review.beat_stills` for the story poses before any
   in-betweens. Each pose: a clear line of action (one curve through the body), a readable
   silhouette, weight over a foot, asymmetry (no twinning), the face and hands clear.
3. **Extremes, then breakdowns.** Key the extremes; the breakdown (favouring) decides the
   character's personality: favour the start for reluctance, the end for eagerness, add
   an arc through the breakdown rather than a straight line.
4. **The thinking moment.** Realise, decide, act. Eyes dart and brows move first
   (`face.ExpressionTrack` leads them by 2-4 frames), then the head, then the body. Hold
   the realisation 8-16 frames as a moving hold (breath, a micro eye dart), with a blink on
   the change of thought. The audience should watch the idea arrive.
5. **Specific over generic.** Choose actions that only this character, with these props,
   in this situation, would do. Use the environment (lean on the shelf, test the crate with a
   foot before trusting it). Avoid the stock gesture list in `deslop-motion.md`.
6. **Contrast and texture.** Vary timing: a quick dart, a slow realisation, a snap into
   action, a settle. Even energy reads as no energy.
7. **Faces for the beat, not the whole shot.** One expression per thought, transitions with
   overlap (brows before mouth), asymmetry, and return to a living neutral, not a frozen one.
8. **Dialogue.** Act the meaning, not the words: one or two accents per line (a head nod, a
   brow), mouth shapes from `lipsync.from_audio` (shapes lead the sound by one frame and hold
   at least two), closed mouth on M/B/P and between phrases, expression carried by the brows,
   eyes and mouth corners underneath. No head bobbing on every syllable.
9. **Appeal.** Clear shapes (round = friendly, square = solid, triangle = danger), a
   characterful proportion, readable eyes with catchlights, one distinctive feature with a
   story reason. Restyle `BlobRig` per job instead of using it unchanged.
10. **Look at it as a film.** Watch the cut at speed, then frame by frame; fix the biggest
    note first; repeat. Most of the quality comes from this loop, not from the first pass.

Face rig quick reference (`BlobRig(RigStyle(face_rig=True))`): presets in `face.EXPRESSIONS`
(neutral, curious, thinking, frustrated, effort, determined, idea, surprised, joy, content,
sad, worried, sly, sleepy); raw controls brow_l/brow_r (raise), brow_la/brow_ra (inner angle),
lid_top, lid_tilt, happy, eye_sq, pupil, mouth_open, mouth_curve, mouth_width, mouth_round,
mouth_skew. `face.eye_darts([(frame, (gx, gy)), ...])` for saccades with holds.

## Stock patterns to avoid
See `deslop-motion.md`: stock motion, stock acting, stock copy, the transplant / swap / strip /
source tests, and `qa/slop_lint.py`.
