# Palettes and design principles

## Design principles

1. Contrast creates hierarchy: the most important element stands out.
2. White space is a feature; do not crowd the canvas.
3. Typography communicates before the words do; choose type on purpose.
4. Three to five colours, each with a job.
5. Animation serves meaning: movement points at what matters.

## Preset palettes (hex)

| Name | Colours |
|---|---|
| Midnight Command | #0f172a, #1e293b, #3b82f6, #60a5fa, #f8fafc |
| Ember | #0c0a09, #292524, #ef4444, #f97316, #fef3c7 |
| Arctic | #0f172a, #e2e8f0, #06b6d4, #22d3ee, #ffffff |
| Neon Ops | #000000, #111111, #00ff88, #00ccff, #ff00ff |
| Earth Intel | #1a1a2e, #16213e, #0f3460, #e94560, #f5f5f5 |

Check contrast of text on each background (WCAG AA: 4.5:1 for body text, 3:1 for large text). Neon Ops accents fail on light backgrounds; use them on dark only.

## Delivery notes

- `.mermaid` is acceptable for plain flow diagrams when the destination renders it.
- Keep the file self-contained: no external fonts or images unless the destination allows them; otherwise use a system font stack.
- For social use, export at the destination's aspect ratio and keep key content inside the safe area.
