# Percept animation catalogue

The engine ships with **16 universal renderers**. Each animates across the lesson's
`steps` (one beat per step). Pick the renderer whose *shape* matches the idea, not the
subject. A cycle is a cycle whether it's the Krebs cycle or a feedback loop.

**Golden rule of sync:** the number of `steps` = the number of animation beats. Beat *i*
reveals visual chunk *i* **and** lights explanation line *i*. Keep visual pieces and
`steps` roughly equal in count. Renderers tolerate mismatch (they reveal proportionally),
but 1:1 is cleanest.

Every `anim` object takes an optional `accent` and `caption` (short string under the figure).
`accent`, and any `color` field below, is a tone name (`blue teal purple green amber red pink`),
which follows the reader's theme, or a six-digit hex, which stays the same in every theme.
Prefer tone names. Three-digit hex is not supported. Below, only the renderer-specific params are listed.

Renderer labels, item titles/details, captions, separators and units are plain text and are escaped by the engine. Colour values are restricted to palette tones or six-digit hex; malformed values fall back to the active blue tone. Diagram coordinates/anchor values are escaped for attribute boundaries; escaping does not validate geometry, so supply numeric coordinates and the normal SVG anchor names. `diagram.base` and bespoke renderer functions are explicit authored SVG/code, not plain fields or automatic source imports; inspect them before use. Lesson beat HTML remains authored markup under the separate `steps.t` contract.

---

## Choosing a renderer: by the shape of the idea

| The idea is…                                   | Use          |
|------------------------------------------------|--------------|
| A definition, or a list of parts/components    | `reveal`     |
| Two things that get confused (A vs B)          | `compare`    |
| An ordered process / pipeline                  | `flow`       |
| A repeating loop with no start                 | `cycle`      |
| Events across time / history / a sequence      | `timeline`   |
| A taxonomy, tree, pyramid, dependency graph    | `hierarchy`  |
| A scale, range, threshold, spectrum, fences    | `numberline` |
| A ranking or comparison of magnitudes          | `bars`       |
| A relationship between two variables / a trend | `plot`       |
| An operation: one state becomes another        | `transform`  |
| A matrix, truth table, Punnett square, grid    | `grid`       |
| A labelled figure (anatomy, circuit, geometry) | `diagram`    |
| A headline number or two                       | `bignum`     |
| Set relationships / logical overlap            | `venn`       |
| A layered system (OSI, strata, tech stack)     | `stack`      |
| A proportion, probability, or filling value    | `gauge`      |

If none fit, hand-author a scene function following the contract in
"Extending with a bespoke renderer" below.

---

## Renderer reference

### `reveal`: sequential idea boxes
Params: `items:[ 'text' | {t:'title', d:'detail'} ]`
Reveals each numbered box in turn. The workhorse for definitions and component lists.

### `compare`: A vs B table
Params: `a:'ColA label'`, `b:'ColB label'`, `rows:[[rowLabel, aValue, bValue], ...]`
Header stays; rows reveal one per beat. Best for the distinctions exams love.

### `flow`: process stages, left → right
Params: `stages:[ 'name' | {t:'name', d:'detail'} ]`, `loop:true?`
Arrows appear between stages; the current stage is outlined. `loop:true` adds a "feeds back" note.

### `cycle`: circular stages
Params: `stages:[ 'name' | {t} ]`, `caption?`
Lays stages around a ring. For water cycle, feedback loops, iterative lifecycles.

### `timeline`: events on a time axis
Params: `events:[ 'label' | {t:'label', d:'when'} ]`
Alternating above/below labels. For history, chronology, ordered milestones. Keep labels short;
four or five events is the practical limit on a phone.

### `hierarchy`: layered tree / dependency graph
Params: `nodes:['A','B',...]`, `edges:[[fromIdx,toIdx], ...]`
Auto-computes levels from edges (longest-path). Reveals in `nodes` order. For taxonomies,
skill trees, DIKW, org charts. Keep to ≤ ~10 nodes for legibility.

### `numberline`: scale with markers, regions, fences
Params: `marks:[{at:0..1, label, color?, dash?, outlier?}]`, `regions:[{from,to,color}]`
`at` is a 0-1 position. `dash:true` = fence line; `outlier:true` adds a red dot.
Keep marks at least 0.15 apart and labels short (about 8 characters), or neighbouring labels
collide. `render_check.py` reports colliding labels.
For quartiles/IQR, thresholds, spectra, statistical fences.

### `bars`: bar chart
Params: `data:[['label', value], ...]`, `highlightTop:N?`
Bars grow per beat. `highlightTop:2` tints the two biggest teal. Bars keep gaps
(categorical). For rankings and magnitude comparisons.

### `plot`: scatter / line with trendline
Params: `points:[[x,y], ...]` (x,y in 0..1), `trend:[y0,y1]?`, `trendLabel?`, `xlabel?`
Points appear, then an optional dashed trendline at the end. For correlations, functions,
trends. (Remember to note correlation ≠ causation in a callout when relevant.)

### `transform`: before → after
Params: `before:'state'`, `after:'state'`, `beforeLabel?`, `afterLabel?`, `op:'what happened'`
Shows one state, an arrow, then the transformed state. For operations, reactions, edits,
encodings, mappings.

### `grid`: matrix of cells
Params: `cells:[[..row..], ...]`, `cols:['C0',...]?`, `rowLabels:['r0',...]?`
Cells reveal in reading order. For truth tables, matrices, Punnett squares, confusion
matrices, any 2-D table concept.

### `diagram`: labelled figure with callouts
Params: `base:'<svg inner>'?`, `parts:[{x,y, lx,ly, label, anchor?}]`
`x,y` = point on the figure; `lx,ly` = where the label sits (leader line drawn between).
Supply a custom `base` SVG (viewBox 0 0 460 240) for the figure, or omit for a default box.
For anatomy, circuits, architecture, geometry: anything with named parts.

### `bignum`: headline number(s)
Params: `nums:[{v:'284k', label:'rows', color?}]`, `sep:'×'?`
Reveals big stats one at a time. For key figures, magnitudes, ratios.

### `venn`: 2 or 3 sets
Params: `sets:[{label:'A'},{label:'B'}(,{label:'C'})]`, `overlap:'text in middle'?`
Circles fade in per beat. For set logic, shared/exclusive properties.

### `stack`: layers building bottom-up
Params: `layers:[ 'name' | {t:'name', d:'tag', color?} ]`
Stacks from the bottom. For OSI layers, tech stacks, geological strata, Maslow.

### `gauge`: value fills a semicircle
Params: `value:0..1`, `unit:'%'?`, `label?`
Needle/arc fills toward the value across beats. For probabilities, proportions, scores.

---

## Extending with a bespoke renderer

When an idea needs a picture none of the 16 can draw, define it in the course data block as
`CUSTOM_RENDERERS`. The engine adds these to its renderer table at start-up, so the engine
code below the data block stays untouched. Contract:

```js
const CUSTOM_RENDERERS = {
  myScene: {
    build: (a) => `<div id="ms"></div>`,             // called once on lesson open
    update: (root, a, step, total) => {              // called on every beat, and on a theme change
      // a = the lesson.anim object; step 0..total
      root.querySelector('#ms').innerHTML = svgWrap(/* SVG string for this step */, 460, 220);
    }
  }
};
```

Helpers available inside renderers: `svgWrap(inner,w,h)`, `cap(text)`, `esc(text)`,
`clamp(n,a,b)`, `mapCount(n,step,total)` (how many of `n` items to reveal at this beat),
`revealN(root,n)` (reveal first `n` `[data-i]` elements), and the colour object `C`.

Keep bespoke scenes to SVG and inline styles, with no external libraries. Take every colour
from `C` (`C.blue`, `C.teal`, `C.dim`, `C.bd` and so on) or from the CSS variables
(`var(--tx)`, `var(--raised)`), so the scene follows the theme. Do not write colour literals.
`update` runs again when the reader changes theme, so it must redraw from its arguments and
keep no state of its own. Reference the scene with `anim:{r:'myScene', ...}`.

---

## Micro-lesson discipline (applies to every renderer)

- **One idea per lesson.** If a lesson needs two renderers, it's two lessons.
- **2-4 steps.** Fewer than 2 isn't an animation; more than 4 is a lecture.
- **The example box is optional.** Use it for the code/formula/statement the animation is
  about. Set `lang:'code'` for syntax highlighting, else `lang:'text'`.
- **Callouts are seasoning, not the meal.** Pick the one or two that fit: `why`
  (why it matters), `trap` (the common mistake), `insight` (a deeper connection).
  Never use all three.
