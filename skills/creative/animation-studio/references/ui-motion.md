# UI, web and app motion

Interface motion has a different job from film animation: it explains a state change or a
spatial relationship, quickly, and gets out of the way. Design it in animkit (same Channels,
same eases, reviewable as filmstrips), then export with `animkit.web` (CSS or Lottie).

## What to animate
- A change of state (open/close, add/remove, success/error), where something came from or
  went to, a relationship (this card expands into that page), progress, feedback on input.
- Avoid decorative movement that delays reading or distracts from the task. Effects
  can stay when they serve the product's purpose; inspect them against the brief.
- Content and essential actions are available immediately, without waiting for entrances.

## Timing and easing (starting points; tune by looking)
| Change | Duration | Ease |
|---|---|---|
| Micro feedback (press, toggle, checkbox) | 80-150 ms | ease-out (`out_quad`) |
| Small component (menu, tooltip, chip) | 150-250 ms | ease-out to enter, ease-in to leave |
| Medium (dialog, sheet, card expand) | 250-400 ms | `snap`-like ease-out; slight overshoot only if the system's style has springs |
| Large / page transition | 300-500 ms | in-out (`slow_in_out`) for things moving across the screen |
| Exits | about 20-30% shorter than entrances | ease-in |
Stagger list items 20-40 ms, capped (the 8th item shouldn't wait 300 ms).

## Rules
- Animate `transform` and `opacity` (GPU-friendly); avoid animating layout properties.
- Honour `prefers-reduced-motion`: expose a usable stable state. `web.css_animation`
  emits `animation: none` plus values derived at the export end by default. Choose
  an explicit state for exits and loops; the end frame is not always the right UX.
- No essential action hidden behind hover; keyboard focus states visible and not animated away.
- Loading: skeletons that match the layout, or inline progress; spinners only for short waits.
- Motion follows one system: shared durations and eases as tokens, not per-component guesses.
- Respect the product's existing motion language and brand; don't impose a new one.

## Lottie deliverables (`web.Lottie`, `web.lottie_from_svg`)
- Vector shapes, solid fills/strokes, transforms, opacity and trim paths export; springs and
  holds are baked per frame. Text must be outlined in the source SVG; gradients become flat.
- Budget: keep layers and keyframes lean (icons < 50 KB, illustrations < 300 KB) and test in
  the target player (lottie-web, lottie-ios, lottie-android) before delivery.
- Verify by rendering frames in a real player when one is available (headless browser +
  lottie-web) and comparing against the animkit render at the same frames.

## QA for interface motion
- A UI animation ends on a still state by design. Use `reel_critic --mode ui` and the
  brief's sound policy. Film stillness, staging, long-shot, cadence and story-score
  heuristics are omitted with reasons; raw measurements remain available.
- What to check instead: the total duration against the timing table, that the final frame
  equals the static design (pixel-compare the last frame with a still render), reduced-motion
  output shows that final state with no movement, and the asset size budget.
- With no browser or player available, say so and name the runtime the client must test in.

## CSS deliverables (`web.css_animation`)
- One @keyframes per property (translate, rotate, scale, opacity) so overlapping timings
  survive; bezier eases export exactly, springs/bounces as `linear()` samples.
- Check in a browser: pause the animations and sample computed values at known times.
- API: `css_animation(name, tracks, ..., stable_reduced_state=None)`. `None` or
  `"end"` derives export-end values; `"start"` derives frame zero; a mapping overrides
  end values with finite scalar `x`, `y`, `rot`, `scale`, `sx`, `sy`, `opacity` values.
  Units stay px/radians/unitless. Do not supply `scale` and axes together in the same
  mapping. Derived paired-scale channels remain supported. Negative scale is valid;
  opacity must be in [0, 1]. Unknown or malformed values raise `ValueError`.
- Example: `stable_reduced_state={"opacity": 0}` for an intentionally hidden exit;
  `stable_reduced_state={"x": 0, "y": 0, "scale": 1, "opacity": 1}` for a loop's rest.
- The reduced block follows the class rule, but component CSS must not override it
  with a conflicting higher-priority declaration. In the actual delivered component,
  inspect initial/final state, reduced preference before load and preference switched
  during motion. Verify focus and actions still work. Source declarations and stubbed
  value comparisons are not browser-computed or rendered evidence.
