---
name: atlas
description: "Builds a self-contained, explorable map of a domain or body of material as a single-file interactive page: concept map, mind map, system diagram, dependency or prerequisite graph, decision tree, skill or tech tree, process flow. Use when he says 'map out', 'how does X connect', 'concept map', 'mind map', 'knowledge map of', 'diagram the dependencies of', 'visualise the structure of', 'decision tree for', 'show me how these relate', 'the landscape of [field]', or when relationships between things are the content. Not for simulating dynamics with live parameters (use simforge), weighing options against criteria (decision-board), a static diagram or poster (canvas-design), a teaching visual for one idea (learning-visualiser) or a portfolio page (showpiece)."
---

# atlas

Turns a tangled domain or a pile of notes into a map he can pan, zoom, search and drill into, with the relationships correct and detail revealed on demand.

## Use when

- Understanding lives in the connections: what depends on what, what sits at the centre, where branches go.
- A topic or a body of notes needs a navigable structure instead of a linear list.

## Not this skill

| The request | Goes to |
|---|---|
| A system with moving parts and tweakable parameters | simforge |
| Compare options against weighted criteria | decision-board |
| A static poster or illustration | canvas-design |
| Teach one concept visually | learning-visualiser |
| A portfolio or showcase page | showpiece |

## Inputs

- The domain, or the material (notes, text, a document) to extract structure from.
- The relationship that matters: hierarchy, dependency, causal chain, decision branching, or free association. Choose it yourself from the material; do not ask him to name graph types.

## Procedure

1. **Specify fast.** Settle the domain or material and the relationship type. If given only a topic, build from expert knowledge and say so; if given material, extract the structure from that and map that.
2. **Choose the layout to fit the relationship:**
   - Hierarchy or prerequisites: directed tree or DAG, top-down or radial.
   - Interconnected concepts: force-directed graph (d3-force: nodes repel, edges pull, it settles into a readable shape).
   - Causal chains and processes: left-to-right flow.
   - Decisions: branching tree with labelled edges.
3. **Model the data first:** nodes (id, label, importance, short definition, detail) and typed edges (from, to, type). Every edge means something specific (depends-on, causes, part-of, leads-to) and points the right way. Label edge types wherever more than one exists. A wrong arrow is a wrong idea.
4. **Build one self-contained file** with all data baked in and no backend. Use d3 (force simulation, zoom and pan) rendered to SVG, in a single HTML page or a single-file React component, whichever the host can display. For a simple tree, hand-rolled SVG is enough. If a library is loaded from a CDN, pin an exact version; if the host blocks external scripts, use the hand-rolled SVG fallback.
5. **Make it navigable and layered:**
   - The overview shows the skeleton only (major nodes and the spine). Definitions, sub-nodes and notes appear on click or zoom.
   - Important nodes are visually dominant (size or colour by importance or connectivity).
   - Pan, zoom, click-to-focus, search or filter to jump to a node, and a way back to the full view.
   - Selecting a node highlights it and its neighbours and dims the rest; a detail panel opens.
6. **Style:** dark, minimal. Background `#0B1220`, panel `#121C2E`, accent violet `#8B5CF6` for edges and highlights, node fills tiered by importance, white text, clean sans-serif. Keep text contrast readable and do not rely on colour alone to carry meaning.
7. **Check before shipping.** Open it if a browser is available; confirm no console errors, that search, focus, zoom and reset work, that no label is clipped in the overview, and spot-check a sample of edges against the source. If it cannot be opened, say so.
8. **Deliver** the file and one paragraph: where to start on the map, how to drill in, and which layout technique was used and when to reach for it again.

## Output

The map as a single file, then the orientation paragraph. Where content came from his material, say what was left out of the overview.

## Rules that always hold

- The relationships are the content, so they must be correct. Where the domain is disputed or the direction of an edge is a judgement, mark it as such on the edge rather than presenting it as settled.
- Do not state facts about fast-moving fields (current tools, versions, market structure) as current without checking; label the map with its build date.
- Faithful to supplied material: do not add nodes he did not provide unless marked as added.
