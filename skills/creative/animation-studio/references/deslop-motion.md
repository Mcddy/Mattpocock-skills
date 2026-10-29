# Deslop for animation: stock motion, stock acting, stock copy

Stock prose fails at a predictable point: a ready-made phrase stands where an observation
should be. Animation fails the same way. A ready-made move (everything fades up, a thumbs-up,
a slow push-in, sparkles, a whoosh) stands where a specific thought, cause or action should
be. The fix is the same as in writing: find what is true and particular about *this*
character, product, brand or story, decide what it means for the viewer, and animate that.

This is a quality gate, not a style ban and not authorship detection. A fade, a bounce, a
gradient or a push-in stays when it does a job you can name. Swapping one stock look for
another (everything hand-drawn-wobbly, everything glitchy) is also a failure.

## 1. Gather the material before moving anything
- The one thing the piece must leave with the viewer (one sentence). If you can't write
  it, the brief is short of substance; ask one precise question or use what exists.
- Supplied facts: names, product behaviour, numbers, brand colours and type, the user's own
  words. What their logo/artwork actually contains (`SVGArt.summary()`).
- The character's want, obstacle and what they have to hand (props, body, setting).
- Never fill a gap with invented proof: no made-up stats, client logos, testimonials,
  "trusted by" rows, award badges or UI data presented as real. Label samples as samples.

## 2. Tells and what replaces them
| Stock tell | Replace with |
|---|---|
| Every element fades/slides up from below with the same ease and delay | Choreography by meaning: the hero leads, others follow its path or react to it; distance and duration by mass and importance |
| Everything animates at once on load | One entrance at a time in reading or causal order; 2-6 frame offsets that vary; the main element first |
| Overshoot/bounce on everything (`out_back` everywhere) | Overshoot only where something has mass or spring; UI motion eases out in 150-250 ms |
| Typewriter text; letters flying in from random directions; the same per-letter stagger on every line | Type moves by meaning: the word that matters gets the move; tracking, weight, masks and reveals tied to the motif or a sound |
| Floating blurred orbs, glows, lens flares, sparkles or particles for "magic" | Light from a motivated source; FX only at a contact, impact or reveal (`fx.dust_puff` on a landing) |
| Purple-to-blue gradients, gradient text, glassy cards, everything centred | The brand palette (or one chosen for the story) with one accent that has one job; value structure; composition with a focal point |
| A slow push-in or drift on every shot | Camera moves for a reason (reveal, focus on a thought, tension) or locks off |
| Looping spin, orbit or float that fills time | A hold that is a choice (moving hold with a purpose) or a cut |
| Whoosh on every transition, riser + boom on every reveal, generic upbeat pluck | Sound from the action (CueSheet), one signature sound, score that follows the beats, silence before the turn |
| Captions narrating feelings ("Simplify your life") | Show the thing doing its job; copy names the specific instance |
| "Problem, logo, tagline" or a three-icon grid for every explainer | Structure from the content: one transformation, a comparison, a sequence, a single case |

## 3. Stock acting (character work)
| Stock tell | Replace with |
|---|---|
| Thumbs-up, jump for joy with both arms, generic wave, shrug, facepalm, hand-on-chin "thinking" | What *this* character would do with what is in front of them, from their want and situation (the cookie thief hugs the jar; the courier taps the parcel twice) |
| Emotion as an instant face swap | A visible thought: realise, decide, act. Eyes and brows lead the mouth by 2-4 frames (`face.ExpressionTrack`); hold each thought 8-16 frames |
| Twinning: both arms, brows or eyes doing the same thing at once | Asymmetry and offsets (the expression presets add some; offset hands by 2-4 frames) |
| Floaty, evenly-eased motion | Contrast: fast after slow, holds, accents, anticipation before effort, a settle after |
| Effort without weight (pushing upright, lifting with no squash) | Lean 15-25 degrees, plant the feet, slow first push, strain on the face (`effort` preset) |
| A default rig used unchanged for every job | Restyle per job: proportions, palette, props and one distinctive feature with a story reason; silhouette test |

## 4. The tests (run them on beat stills and the contact sheet)
- **Transplant:** could this shot, sting or move drop unchanged into an unrelated brand or
  story? Then it's stock; rebuild it from the material.
- **Swap:** could another character perform this acting unchanged? Could two options in an
  explainer trade visuals and stay true? Find the missing particular.
- **Strip:** turn off glows, particles, gradients, camera drift and music. Does the beat
  still read? If not, decoration was doing the story's job.
- **Source:** every number, name, logo, quote and claim on screen traces to supplied
  material, or is labelled as a sample.
- **Sound off, text off:** does the story still read?
- **Overcorrection:** did the pass remove a fade, bounce or gradient that was doing a job,
  or flatten the brand's own style? Put it back.

## 5. On-screen copy, scripts, captions and delivery notes
- Lead with the thing (the product, the result, the action). Cut warm-ups and recaps.
- Name the instance: the measured change, the named feature, the real place.
- A word that asserts quality ("seamless", "powerful", "effortless") needs the visible
  consequence that makes it true, or it goes. Hype verbs (Elevate, Unleash, Supercharge,
  Revolutionize, Unlock) go.
- Keep distinctions ("may" stays "may"; two prices stay two prices) and the client's voice.
- Same name for the same thing everywhere (title card, caption, end card, file name).
- Follow the client's spelling and punctuation conventions (e.g. no em dashes if they
  don't use them; rewrite the relationship with a full stop, comma or colon).
- Delivery notes: what was made, what was inspected, what was measured, what is untested.
  No boilerplate, no AI badges unless the client chose disclosure.

## 6. Tooling
`python3 scripts/qa/slop_lint.py --text copy.txt --code scene.py --video out.mp4` flags
candidates: hype words and stock phrases in copy, one-ease-everywhere and overshoot-on-
everything in scene code, typewriter reveals, default fonts, purple-blue palettes, and
moments where most of the frame starts moving in the same two frames. Every flag is a
question to answer ("is this doing a job?"), not a verdict.
