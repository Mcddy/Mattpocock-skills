# The principles, as code and numbers

The twelve principles come from Frank Thomas and Ollie Johnston, *The Illusion of
Life: Disney Animation* (1981). Below, each is mapped to what it means on screen,
how animkit implements it, and the numbers that make it read. Frame counts assume
24 fps.

## 1. Squash and stretch
- Volume is preserved: `sx * sy == 1` (`principles.squash_stretch`, `impact_squash`).
- Stretch along the direction of travel at speed; squash on impact, then spring back.
- Amount is a style dial: 5-10% for grounded characters, 20-35% for cartoony; rigid
  props (radio, car body) get ~0 but their *suspension/secondary parts* can squash.
- Never squash text glyphs or logos by non-uniform scale; animate tracking, weight,
  position, or use a variable-font width axis.

## 2. Anticipation
- A small move opposite to the main action before it happens
  (`principles.anticipate`, ease `"anticipate"`).
- Size scales with effort: a glance 2-3 frames, a reach 4-6, a jump 6-10, a throw 8-12.
- Anticipate thought too: eyes move (or a blink) before the head; the head before the body.

## 3. Staging
- One idea per moment. The viewer's eye should land where the story is: brightest
  value, highest contrast, sharpest edge, most saturated colour, isolated silhouette.
- Silhouette test: fill the character black; the action must still read.
- Don't stage key actions behind other objects or with limbs crossing the face.

## 4. Straight ahead and pose to pose
- Pose to pose for acting and anything timed to story beats (`curves.Channel`).
- Straight ahead for chaotic / physical things: fire, water, cloth, hair, debris
  (simulate: `Spring`, `simulate_positional`, particle loops).
- Blocking review: `Channel.stepped(f)` shows only key poses.

## 5. Follow-through and overlapping action
- Parts don't stop together. Loose parts (hood tip, ears, tail, antenna, bag, coat
  hem, hair) keep going and settle after the body stops: `lag_chain`, `simulate_positional`.
- Offset timing: torso leads, head 1-2 frames later, arms 2-4 later, appendages 3-6 later.
- Settle with one or two decreasing overshoots, then a moving hold.

## 6. Slow in and slow out
- Spacing bunches near key poses. Default `slow_in_out`; heavy things `heavy`; fast
  starts `snap`; light floaty things `float`.
- Check the spacing numerically: `curves.timing_chart(0, 1, n, ease)`.
- Constant velocity is a choice reserved for machines, conveyors, scrolling credits.

## 7. Arcs
- Organic motion travels on arcs: heads during turns, hands in reaches and waves,
  the hip during walks (vertical bob), thrown objects (parabola). Use `ArcPath`.
- Straight-line interpolation between two poses of a limb is the most common
  "computer animation" tell after constant speed.

## 8. Secondary action
- Supports the main action without competing: a satchel swinging on a walk, a
  hand adjusting a strap while waiting, breathing, blinks.
- If it pulls focus from the primary action, cut it or reduce it.

## 9. Timing
- Number of frames = weight, mood and intent. Reference table:

| Action | Frames @24 | Notes |
|---|---|---|
| Blink | 4-7 | close 2, hold 0-1, open 3 (`principles.blink`) |
| Eye dart / glance | 2-4 | eyes lead the head by 2-4 frames |
| Head turn | 6-12 | arc through a slight dip; anticipate with a blink |
| Take (surprise) | antic 4-6, hit 2-3, hold 8-16, settle 6-10 | squash then stretch |
| Walk step (brisk) | 8-10 | 2 steps per cycle; 12 = normal, 16 = stroll |
| Run step | 4-6 | include flight phase (both feet off ground) |
| Jump | antic 6-10, air depends on height, land 3 + settle 8-12 | |
| Reach for object | 8-14 | anticipate, lead with the eyes |
| Thought beat before acting | 6-18 | the "decision" is visible |
| Moving hold | 12-48+ | keep 1-2% drift, breathing, blinks |
| Text on screen | ~ 0.3 s per word + 1 s | minimum readable hold |

## 10. Exaggeration
- Push poses beyond reality so they read at speed and at small screen sizes.
  Then pull back on anything that looks like a mistake rather than a choice.

## 11. Solid drawing
- Consistent volumes across turns and squash (turnarounds, construction shapes).
- In 2-D rigs: keep line weights consistent across scale changes (`sw` / scale).

## 12. Appeal
- Clear readable shapes, varied proportions (big/small, straight/curve),
  expressive eyes, an asymmetry or two. A character the audience wants to watch,
  hero or villain.

## Walks (animkit.walk)
- Contact -> Down (lowest, weight lands) -> Passing -> Up (highest) per step.
- Planted foot locked in world space; `foot_slide_report()` must return 0.
- Hip speed trapezoid; strides shrink into the stop; closing step brings feet together.
- Arms counter-swing; amplitude scales with speed. Lean forward with speed.
- Chain walks with `start_feet=previous.final_feet()` to avoid foot pops.

## Acting-specific mechanics
- Eyes lead: gaze channel keys 2-4 frames before head/body keys.
- Weight shift during holds: hip drifts toward the supporting foot.
- Breathing: `breathe()` ~0.25-0.35 Hz, 1-2% scale.
- Contact with props: the hand must arrive at the prop before the prop moves.
  The prop then inherits the hand's spacing (no prop floating on its own).

## Failure -> fix table

| Symptom | Cause | Fix |
|---|---|---|
| Character "skates" | body translation not tied to planted feet | `Walk`, foot locking, contact frames |
| Robotic movement | linear spacing, all parts moving together | eases, offsets, overlap chains |
| Floaty | too few frames on impacts, no squash, slow out of contact | faster into contact, squash, shorter settle |
| Dead hold | identical frames | moving hold: breathing, drift, blink |
| Twinned limbs | both arms/legs mirror each other | offset timing, vary poses |
| Object moves by itself | prop animated independently | animate the hand, parent prop to it |
| Mushy acting | no clear key poses | block stepped, strengthen silhouettes |
| Pops | missing in-betweens or rig flips | more keys at the flip, motion blur, check `bend_dir` changes |
