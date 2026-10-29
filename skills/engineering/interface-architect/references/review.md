# Reviewing a built interface

The earlier version of this skill told the model to run its checklist "silently" and present the result. A check nobody can see cannot be told apart from a check that was skipped. This file replaces that step.

## Three kinds of finding

| Kind | What it is | How it is decided | Can it fail a build? |
|---|---|---|---|
| Defect | The source or the measured render breaks a named standard | By reading or measuring | Yes |
| Candidate | A pattern that is often a sign of default output | By looking at the render | Only after someone looks and agrees |
| Judgement | Hierarchy, density, tone and fit against the agreed task, brand and quality criteria | Evidence-based assessment by an identified reviewer; state the basis and uncertainty | May hold delivery when agreed criteria are missed. A preference is not a universal defect |

Keep the three apart in every report.

## Defects: things that can be measured

Measure these when the tools exist. Report the number, not an impression.

- Text contrast against the background actually painted behind it. 4.5 to 1 for normal text, 3 to 1 for large text (24px and up, or 18.66px and up when bold) [WCAG 1.4.3].
- Zoom not blocked by the viewport tag [WCAG 1.4.4].
- Every image has an alt attribute, and the page has a language set [WCAG 1.1.1, 3.1.1].
- Every control can be reached and operated from the keyboard, with a visible focus indicator [WCAG 2.1.1, 2.4.7].
- Pointer targets against WCAG 2.2 SC 2.5.8: a target meets the size when a 24 by 24 CSS pixel square fits inside it. An undersized target passes when a 24 pixel circle centred on its bounding box is clear of every other target and of every other undersized target's circle (touching is allowed, overlapping is not). Four more exceptions need a person: an equivalent control that meets the size, a target inline in a sentence, a browser-default control left unstyled, and an essential presentation. `scripts/target_size.py` does the geometry and lists the targets where an exception has to be checked. Aim for 44 by 44 on primary and touch actions.
- No horizontal overflow at the narrowest width the product supports, and no control pushed off screen.
- Motion respects the reduced-motion setting.
- Any setting the interface offers (theme, density, type size, motion) changes what it says it changes, survives a reload where storage exists, works without storage and resets.

## Candidates: things to look at

Run `python scripts/ui_candidates.py <path>`. For each candidate, look at the render and decide:

- Is it there because the product needs it, or because it is the default?
- Would removing it lose anything a user would notice?

Then either change it or keep it and write one line saying why. A report that lists candidates without a decision on each is unfinished.

The script reads text. It cannot see layout, rhythm, hierarchy or whether a page looks like every other page. Zero candidates does not mean the design is good.

## Final delivery: where the interface is actually used

A local browser tab is the most permissive place a page will ever run. Hosts embed generated pages in a sandboxed frame, and what the sandbox leaves out fails silently. The table applies when the page will be shown in such a preview or the surface is not known. On a confirmed normal web origin or native shell, forms, storage and downloads are supported: keep them, check their submit and keyboard behaviour, and do not report their use as a finding.

| The page does this | Blocked when the frame lacks | What the user sees | Use this |
|---|---|---|---|
| Native form submission or navigation | `allow-forms` | Native submission is blocked before its submit event; programmatic event dispatch or direct JavaScript handlers can still run | Assess the actual flow and avoid reliance on blocked native submission; use a supported handler where needed |
| `alert`, `confirm`, `prompt`, `print` | `allow-modals` | Nothing happens | In-page messages and dialogs |
| `localStorage`, `sessionStorage`, IndexedDB, cookies | `allow-same-origin` | An exception, often swallowed, and lost state | try and catch, state in memory, correct with nothing stored |
| `window.open`, `target="_blank"` | `allow-popups` | Nothing opens | Show the content in the page |
| A file download | `allow-downloads` | No file | Show the content in the page as well |
| Navigating the outer page | `allow-top-navigation` | Nothing happens | Links the user can copy |

The native form distinction follows the [WHATWG form-submission algorithm](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#form-submission-algorithm). Do not infer that native user submission fires a submit event in the sandbox from a scripted event-dispatch probe, or that blocked native submission prevents all application JavaScript effects.

How to check, in order of strength:

1. **In the delivered preview.** Exercise the main path there: enter values, save, change them, save again, restore, reload. This is the only real proof.
2. **In a sandboxed stand-in.** `python scripts/delivery_check.py page.html --steps steps.txt` runs the same steps in a tab and in a frame with `sandbox="allow-scripts"`, and names any step that passes in one and fails in the other. A pass shows the page does not depend on the blocked features. It does not show the page works in a given product, which may add its own policies.
3. **By reading.** `ui_candidates.py` lists the "delivery" patterns. Reading finds dependence; it cannot prove its absence.

The report says which of the three was done. "Tested in Chromium" without saying whether it was framed is not enough.

Write the steps so they prove state, not just clicks: after Save, check that the saved value shows; after Restore, check the fields went back. Use at least two different values so a stale display cannot pass.

## When nothing can be rendered

Say so in the first line of the report: "Source review only: not rendered." Then:

- Report defects that are visible in source.
- List candidates as candidates, undecided.
- Do not describe appearance, spacing or feel.

## What a report contains

1. What was reviewed, and how: rendered at which sizes and themes, or source only. Where it was exercised: delivered preview, sandboxed stand-in, or local browser only.
2. Defects, with location, the standard and the fix.
3. Candidates, each with the decision and reason.
4. Design assessments with evidence, agreed criteria, reviewer and uncertainty; preferences identified separately.
5. What was not checked.

## Rendered checks with a browser tool

If a scriptable browser is available, these are worth automating because they are cheap and objective: computed contrast for every visible text node, bounding boxes of controls against the viewport, page scroll width against viewport width, tab order reaching every control, and each setting's effect on a computed style. Include one negative control (for example a deliberately low-contrast label) to prove the audit can fail. An audit that has never failed has not been shown to work.

## Vendored checks in revision 3.1.0

Read [the Interface result guide](results.md) before interpreting the five bundled Forge 3.3.2 checks. Native exit 3 now means partial coverage; runner failures use 4. The dead-controls JSON field `controls_tried` was replaced by `activated`, with explicit per-row outcomes. No other packaged script parses it. A page-extracted inline target may be marked as an observed sentence or uncertain; review that heuristic and any claimed exemption rather than treating geometry as certification. Use `--tab-only` for a confirmed normal-origin delivery and preserve real forms and keyboard submit. A pattern/observable effect is evidence to inspect, not proof that the promised user outcome occurred.
