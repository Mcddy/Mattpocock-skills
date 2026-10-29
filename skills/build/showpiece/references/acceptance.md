# Acceptance and evidence

Use Pass, Revise or Not exercised for each relevant gate. Do not average unresolved defects into a quality rating.

| Gate | Examine | Claim supported |
| --- | --- | --- |
| Art direction | Main object, reading order, fitting density, meaningful type/image decisions | Agent editorial assessment only |
| Task payoff | The difficult choice, visible deciding information and a successful path plus relevant recovery | Exercised mechanism; human usefulness remains separately measured |
| Responsive craft | Desktop, phone, 320 CSS-pixel reflow where applicable, long text, actual text enlargement | Observed layouts, not all-device coverage |
| Interaction | Primary journey plus difficult state/recovery; repeated actions, cancellation and accurate output | Exercised fixture behaviour |
| Access | Keyboard order, visible/unobscured focus, semantics/names, contrast, touch, reduced motion | Selected accessibility checks only |
| Motion | Purpose, continuity, timing, interruption and quiet fallback at real speed | Observed transition behaviour |
| Performance | Named browser/device/viewport, demanding trace, bytes/dependencies, actual measurements | Local measurements with method limits |
| Presentation | Accurate screenshot, thumbnail and opened view, useful crop, clear context | Local presentation assessment |
| Human acceptance | Owner/reviewer sees the concrete render and responds in their own words | Actual qualitative response, not market validation |

Check contrast against actual backgrounds and states: ordinary text 4.5:1, qualifying large text 3:1; required meaningful non-text visuals generally 3:1, with applicable exceptions. Targets at AA are 24 × 24 CSS pixels or exceptions; prefer larger touch controls when practical. At AA focus cannot be entirely obscured by author content. These selected checks do not establish full WCAG conformance.

Capture screenshots after final relevant changes. A screenshot does not test keyboard behaviour; source inspection does not prove rendered quality. Use actual zoom/text enlargement where possible; resized images are not zoom evidence. Test failure and recovery without real purchases, messages or publication.

Verify content bindings in the real runtime: selecting an item must update the visible media as well as labels, price and summary. Inspect computed visibility and the actual picture; an accessible name can change while the wrong artwork remains. A test double that treats SVG like HTML can miss this defect. Derive the expected visual independently of the implementation and retain a regression for the observed failure. Scanner/logic passes cannot overrule the render.

Lead a portfolio demonstration with a representative populated/active state when interaction carries its value. Keep purposeful first-use, empty and recovery states in the app and show them as useful secondary views. Match each capability claim to the actual visible/exercised state. Inspect every final export edge at intended aspect ratio, native crop and thumbnail: avoid bisected headings, controls and cards; distinguish intentional illustration bleed. Minimise wrappers and repeated headings so the primary work dominates. Data cases show a recognisable before/after transformation and separate exceptions, without calling unresolved records import-ready.

Apply gates by deliverable. Writing-only work needs meaning, voice, reading-context and factual checks; static exports need composition/crop/readability checks. Do not invent runtime or performance work where no interactive or performance-sensitive deliverable exists.

Local performance: record source weight, external requests, browser/runtime and one demanding interaction measurement supported by available tools. If a performance trace is unavailable, report the exact missing measure. Do not claim smoothness, 60 fps, passed Core Web Vitals or real-user performance from tiny files, transform usage or a single screenshot. [Core Web Vitals](https://web.dev/articles/vitals) distinguish loading, interaction and stability, and field results need field data.

Human review: show the candidate at its intended size and ask what task/work it communicates, where attention goes and what feels unresolved. Record the actual answer. An agent review is useful but distinct. If no human response is available, finish local delivery with human acceptance Not exercised, rather than silently approving it or stopping all work. If the owner rejects it, reassess the organising direction and rerender before repeating only affected checks.

Final receipt: give changed source/result links, important decisions tied to purpose, checks actually observed, material gaps and any external action still held. Keep the receipt outside the product flow.
