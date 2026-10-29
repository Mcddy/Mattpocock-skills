# Purposeful motion contract

For each shipped transition, record briefly in existing implementation notes:

| Field | Decision |
| --- | --- |
| Trigger | Which user action or real state change starts it? |
| Relationship | What continuity, feedback or hierarchy does it explain? |
| Treatment | Which properties, duration and easing serve that relationship? |
| Interruption | What happens on repeated action, reversal, navigation, resize or dismissal? |
| Final state | What remains correct when animation finishes or never runs? |
| Alternative | What nonmoving feedback remains under reduced motion? |
| Measurement | Which demanding interaction and environment will be profiled? |

Functional motion helps users track change: a selected preview, expanding detail, a changed basket total or a dialog's layer. Keep repeated interactions quick and interruptible. Expressive motion can introduce an object or mark an important completion when the brief benefits. An ambient effect needs a stronger reason because it consumes ongoing attention and resources. Do not confuse the absence of motion with the absence of polish.

Choose durations by distance, frequency and context. Roughly 120–220 ms micro-feedback and 200–400 ms layer transitions are starting heuristics, not standards or fixed requirements. Test the feel at real speed. Avoid repeating large entrance animations on routine actions. Timing, easing and spatial continuity should form a coherent small vocabulary.

## Implementation and resilience

Prefer transform/opacity for suitable movement. Avoid animating layout dimensions casually; if necessary, test rendering work. Do not permanently promote every element with will-change. A small CSS/WAAPI implementation often suffices; do not import a library for one transition.

Keep the DOM's state authoritative. Cancel or reverse current animations before replacing them; do not allow old completion callbacks to restore stale content. A counter should show the current value even while emphasis animates. Dialog content/focus should not wait for animation. Closing during opening must end closed with focus returned. Do not move a user's focused control unexpectedly.

Respect `prefers-reduced-motion` and changes to that preference. Replace large spatial motion, parallax and unnecessary loops with immediate updates or quiet nonmoving feedback. Content remains available if CSS/JS animation fails. Never gate reading or operation behind staggered reveal, scroll progress, cursor tricks or decorative loading.

## Evidence

Exercise repeated inputs and cancellation under normal and reduced motion. Inspect focus, final state, viewport resize and responsive rearrangement. Profile the demanding transition with existing tooling and record environment, duration, dropped/long-frame evidence where supported, layout/paint observations and remaining gaps. Source properties alone do not establish smoothness. Do not label requestAnimationFrame intervals as GPU frame delivery or a local trace as field INP.

Primary references: [web.dev animation performance](https://web.dev/articles/animations-guide), [IBM animation](https://www.ibm.com/design/language/animation/overview/), [W3C interaction motion](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html). The last is AAA; reduced motion is also an independent requirement here.
