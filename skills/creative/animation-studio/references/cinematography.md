# Camera, staging and editing

## Shot sizes and what they're for
| Size | Use |
|---|---|
| Extreme wide / establishing | place, scale, mood; hold long enough to read (2-4 s) |
| Wide | full body action, choreography, walks, staging relationships |
| Medium | gesture + face; most acting with props |
| Close-up | emotion, decisions, reactions |
| Insert | the prop / product detail that matters (a slot, a knob, a dial) |

Move in as the story focuses (wide for the approach, medium for the action, close for
the decision). Test it on the beat stills: at every thought beat (a failure, an idea,
a realisation, the payoff) is the face at medium or closer? If the whole piece is one
locked wide, the acting is too small to read and `reel_critic` will report most of it
as near-still. The reference shot does this with one camera: wide -> push to medium on
arrival -> slow push on the payoff -> hold as the character exits.

## Camera motivation
- Move the camera only for a reason: follow action, reveal, emphasise, connect.
- Ease every move (slow in/out); lag slightly behind the subject when following.
- Handheld drift (`Camera.handheld`, 1-3 px) keeps static 2-D frames alive; impact
  shake (`Camera.shake`) only for real impacts.
- Parallax: depth 0.3-0.5 far background, 0.7 mid, 1.0 action, 1.2-1.4 foreground
  (blurred: it reads as shallow depth of field).
- 3-D: longer lenses (50-85 mm) for characters/products, wide (18-28 mm) for space
  and comedy distortion; shallow DOF to direct the eye, focus pulls on story changes.

## Composition
- Value grouping: the subject sits on the area of highest contrast.
- Rule of thirds / golden section as defaults; centre framing for symmetry and confrontation.
- Leading lines (kerbs, rooflines, light cones) point at the subject.
- Headroom and lead room: give space in the direction of look and travel.
- Don't put tangents (edges touching edges) near the focal point.

## Continuity
- 180-degree rule: keep the camera on one side of the action line between cuts.
- Screen direction: a journey keeps its direction (left-to-right = going, by convention).
- Eyelines match across cuts.
- Match props, lighting state and time of day across cuts.

## Editing
- Cut on action (mid-movement), or on a look (cut to what they see).
- Average shot length for short-form spots 1.5-4 s; acting pieces can hold 6-20 s if
  the staging evolves.
- Sound can lead picture (J-cut) or trail it (L-cut) to smooth transitions.
- Montages need rhythm (cut on music beats) and a shape (build, peak, release).

## Reframing for other aspects (9:16, 1:1, 4:5)
- Re-stage, don't centre-crop. Keep the subject whole, rebuild the layout (title
  position, subject scale) per aspect, re-time if the subject leaves frame sooner.
- Keep text and faces out of platform UI zones (top ~14%, bottom ~20-35% on vertical
  feeds; check the current platform guide before shipping).
- With procedural scenes, render natively at the new aspect with a per-aspect camera.
