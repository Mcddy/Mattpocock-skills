---
name: computational-design
description: Generate and validate unit-aware planar polygons or parametric organisers, export dimensioned SVG and extruded 2.5D OBJ geometry, and verify area, fit and mesh invariants. Use for constrained geometric design, not structural certification or full 3D boolean CAD.
---

# Computational Design

Turn supplied dimensions and constraints into editable parameters and actual geometry. Deliver SVG, OBJ and a dimensional receipt using `scripts/design.py`. Read [geometry contracts](references/geometry.md) first. Choose a simple-polygon extrusion or a modular organiser. These are geometric designs; material behaviour, fabrication tolerances and structural safety require separately justified checks.

Run `python scripts/design.py design.json --out-dir fresh-output`. The directory must not exist. Inputs accept mm, cm, m or inches; convert every dimension from the declared input unit, then work in millimetres. Do not mix units in unlabelled arrays. Retain the original parameters and input hash.

Validate before exporting: positive finite dimensions, wall/clearance constraints, simple nondegenerate polygon, triangulation consistency and closed component mesh topology. Show bounds, area, perimeter, height and component volume. Do not claim a unioned watertight assembly: organiser components are separately closed boxes touching along their boundaries. The OBJ retains component groups; coincident contact surfaces are intentional and must be resolved by a real geometry kernel before a single solid is required.

Compare a useful neighbouring variant that changes capacity, clearance or silhouette. For warm/customisable presentation, the generated SVG uses a cream background, clear dimensions and an explicit chosen accent; it carries useful geometry rather than a dashboard shell. Editable JSON is the reopen/import contract. Re-running a changed design regenerates geometry; no badge persists through unvalidated edits.

`assets/organiser.json` and `assets/polygon.json` are working examples. “Design a dimensioned 4-slot organiser” should trigger this skill. “Make an abstract animation” routes to Media Compiler; “prove this design is load safe” needs an engineering analysis beyond this core.

Authorship: Codex continuation. Producer checks are separate from independent acceptance.
