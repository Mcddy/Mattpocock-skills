# Step 7: verify, then the craft test

Read before step 7. Check statuses and receipts are defined in results.md.

| Check | Command | A pass means |
|---|---|---|
| API answers, refusals, persistence | `api_check.py BASE STEPS.json --start "..."` | The listed requests got the listed answers, against a server this run started |
| The flow in the page | `delivery_check.py PAGE --steps FILE` (add `--tab-only` on a confirmed normal origin); again with `--reduced-motion`, and with `--block-outside` | Every step passes in a tab, and in the sandboxed frame when that surface applies; still passes with reduced motion and with every non-local request blocked |
| Render, layout and access | `render_gate.py PAGE OUTDIR --prep-js "..."` per state and per in-app theme | No sideways scroll at 320, 390, 768 and 1280; zoom allowed; no serious axe issues; keyboard reach and visible focus; reduced motion respected; screenshots saved |
| Controls do something, by mouse and keyboard | `dead_controls.py PAGE --keyboard` (throwaway data only) | Every activated control had an observable change; each MOUSE ONLY, CLICK ONLY and UNRESOLVED item is a candidate that was read and then fixed or explained. An observable change is not proof the promised action worked: the flow steps prove that |
| Contrast per theme | `contrast_check.py PAGE --set "html@data-dir=NAME"` | Text meets WCAG 1.4.3 in that state, errors showing |
| Pointer targets | `target_size.py --page PAGE --width 390 --json` | 24 by 24 at least; 44 by 44 on primary and touch actions |
| Source candidates | `ui_candidates.py FILES` | Nothing; it lists things to look at |
| The design pack is still true | `design_page.py docs/design.md docs/design.html` after updating the pack to match the code | Exit 0; every diagram, route and table matches what was built |
| Tier deliverable | Demo: the packed file under `delivery_check.py --block-outside`; Release: `release/launcher.py --self-test` | The demo works offline; the launcher starts and stops the server |

Every check ends with a RECEIPT line; report its status verbatim (`references/results.md`). A Demo runs the checks in the Demo fast path. Break the UI steps once on purpose as well as the API ones: a suite that never failed has not been shown to work. `render_gate.py` loads the page several times, so a `--prep-js` that writes data must be repeatable, or reseed between runs. If you can reach the real delivery surface, exercise the flow there; a local frame is a stand-in. A failing check is reported as failing and never loosened to pass.

Then use the page at 390 px and 1280 px, in every theme, with realistic data, look at the screenshots of populated, empty and error states, and answer. Any "no" means not done. Give the reason for each answer.

**Can the job be done?**
1. Can a new user complete the main action without being told how?
2. Does every visible control do something? (Read `dead_controls.py`'s list.)
3. Is every number, list and chart produced from real data, with its source or range clear?
4. After each action, can the user tell what happened, including failure, and do the tally, row and summary agree?
5. Do the awkward cases hold: the longest value, zero items, many items, a refused action, a lost connection, a denied permission?
6. Are the facts a practitioner checks first present, correct and findable within ten seconds, beside the action they affect?

**Is it this job's page?**
7. Cold read: at thumbnail size, write one line saying what it is. Does it match the five-second line? Renamed, would it suit an unrelated product just as well?
8. Median: describe the typical generated version of this app in three lines. For the five most prominent decisions, is the reason drawn from this task, or would it fit any product?
9. With gradients, shadows, blur and rounding removed, does the hierarchy hold? Does anything move at rest?
10. Does the main object get the most space and the main action the easiest reach, at both widths?
11. Does the string sheet pass: literal, specific, the user's spelling, promises matching behaviour?
12. Does each customisation work fully, in every state and theme, and reset?

**Is it at the bar?**
13. Mismatch review (`references/visual.md` section 10): put the first-viewport captures (390 and 1280) and the exercised states beside the analog from step 4b and list the concrete mismatches in hierarchy, first action, density, disclosure and feedback. Is each one fixed, or stated as a departure with its reason?
14. Does it look current, judged at 390 px (`references/frontend.md` section 11)? Where boxes, rules or outlines do work that grouping, scale or imagery should; navigation or options wrap into a wall of boxes; the subject's own picture (the map, the diagram, the object) is missing where only words explain it; or a large region shows nothing with no designed state, it reads as dated. Boundaries, density and empty states that have a job stay.

A failure on 7, 8 or 13 is fixed by changing the composition or the layout move, never by recolouring, swapping a font or adding effects. Classify findings: a **measured defect** is fixed without debate; a **design assessment** is fixed with the reasoning and confidence stated; a **preference** (the user's theme, banned marks, palette) is applied without being presented as fact. Never score how "AI-made" a page looks.
