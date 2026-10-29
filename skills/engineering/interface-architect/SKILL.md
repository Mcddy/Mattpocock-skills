---
name: interface-architect
description: "Check interface code against 200 numbered GUI, CLI and TUI rules and explain the standard, finding or convention behind a rule. Use for specific-rule reviews and terminal interfaces. Not for whole-GUI audits or repairs (anti-vibecoded-ui), ambitious pages or open-direction redesigns (showpiece), app back ends (forge), or store packaging (web-to-store)."
metadata:
  revision: "3.1.0"
  revised-from: "Preserved 3.0.1 local/web sources; exact Forge 3.3.2 check scripts"
---

# Interface architect: the rule reference

A numbered rule set for interface code, with the reason behind each rule kept separately so a rule can be defended, relaxed or dropped on evidence. Graphical rules are 1 to 100. Terminal and command-line rules are 101 to 200.

- `references/protocol.md`: the rules, the scope gate, theme and preference handling, host notes and the checklist.
- `references/research-grounding.md`: which rules rest on a standard (WCAG), which on a research finding, which on convention, and what is not established.
- `references/review.md`: how to review a built interface, and what counts as evidence.
- `references/results.md`: the five bundled checks, native result meanings, receipt schema and limits.
- `scripts/contrast_check.py` and `scripts/dead_controls.py`: measured text contrast and observable control/keyboard-effect candidates; neither certifies accessibility or a complete workflow.
- `scripts/ui_candidates.py`: lists patterns worth a look in the source, including things a sandboxed frame blocks. It finds candidates. It does not judge a design.
- `scripts/target_size.py`: applies the WCAG 2.2 target-size geometry (24 by 24, or a centred 24 pixel circle clear of neighbours) to a list of boxes or to a page.
- `scripts/delivery_check.py`: runs a page and a list of steps in a browser tab and again inside a sandboxed frame, and reports what works in one and not the other.

## Use when

- Building or reviewing a command-line tool or terminal interface.
- Checking a graphical interface against specific rules ("does this table follow the density rules", "is this target size right").
- Someone asks why a rule exists, or wants to override one and needs to know what they are giving up.
- No dedicated GUI design workflow is available in this session and a graphical interface needs building or reviewing. Then this skill's procedure covers it.

## Not this skill

| The job | Use |
|---|---|
| Audit, repair or polish a whole GUI | anti-vibecoded-ui, when available. It leads; look rules up here when it needs one. |
| Build an ambitious page, portfolio or open-direction showcase redesign | showpiece, when available; this skill supplies specific rules. |
| Build the working software behind an interface: API, storage, a running app | forge. It owns implementation; this skill supplies the rules it checks against. |
| An animated course or a simulation | percept, simforge |
| Packaging a web app for app stores | web-to-store |
| A quick throwaway snippet the user asked to keep minimal | no skill. Honour the request. |
| A script with no interface | no skill |

These are declared routing contracts, not evidence that a host loaded a skill. Name an unavailable method and continue authorised work with the tools available; do not claim activation. Confirmed task, access, delivery and accepted brand take precedence over a style default. State a consequential conflict before recommending a rule override, with its source or reason.

## Inputs

- What is being built or reviewed, and for whom.
- Target: graphical, terminal or both.
- The user's stated preferences for theme, density and tone, if any. These override the rule defaults.
- For a review: the source, and a way to see it rendered if one exists.

Ask only if the target is truly unclear and guessing wrong would waste the build. Otherwise state the assumption and continue.

## Tools: discover first

Check what this session has before choosing a method:

- Whether the runtime has a build step, which libraries load and whether browser storage works. Read the host's instructions or test it. Do not carry an assumption over from another product.
- A way to render and look at the result: a browser tool, a screenshot tool, a preview the user can see, or a terminal to run a TUI in.
- Python, for `scripts/ui_candidates.py`.

If there is no way to render, the review is a source review and must be reported as one.

## Procedure

1. **Scope.** Confirm the request calls for interface code (protocol Section 0). If the user asked for quick and disposable, stop here and do that.
2. **Target and runtime.** Graphical, terminal or both. Then find out what the runtime supports (Host Notes in the protocol). This decides how tokens are defined (Rule 94) and whether terminal rules apply literally or as in-browser equivalents (Faux-Terminal Note).
3. **Preferences.** Apply the user's stated theme, density and tone (protocol Section 0.1). With none stated: light by default, dark following the device, tokens throughout, and a working theme choice where the interface will be used more than once.
4. **Load only the sections you need.** The protocol is in ten-rule sections by concern: colour, type, layout, controls, copy, tables, states, motion, accessibility, code, then the terminal equivalents. A form needs sections 4, 5, 7 and 9. Do not try to hold 200 rules for one button.
5. **Build**, applying the rules as you go.
6. **Review the result**, following `references/review.md`:
   - Run `python scripts/ui_candidates.py <path> --fail-on-defect --receipt <new-file>` if Python is available. Confirm each DEFECT against the actual source and named standard before fixing it. A CANDIDATE is a prompt to inspect, not a design verdict. Read the native status and coverage using `references/results.md`; a zero exit without `--fail-on-defect` means the scan ran, not that no defects were found.
   - Render the interface if you can, and look at each candidate there. Keep it, with a reason, or change it.
   - Work through the checklist at the end of the protocol.
7. **Check it where it is delivered.** A page that works in a browser tab can fail inside the frame a host shows it in (protocol Section 0.2). Exercise the main path, such as enter, save, change and restore, in the delivered preview if you can reach it. Otherwise run `python scripts/delivery_check.py <page> --steps <file>` and say a stand-in was used. What the page may rely on depends on the surface:
   - A chat host's sandboxed preview, or a surface you could not confirm: the strict set. No `form` element, no native dialog or popup, and storage and downloads optional with a fallback.
   - A confirmed normal web origin or a native shell: forms, storage and downloads are fine, and a real `form` with a submit button and its keyboard behaviour is preferred. For an authorised browser test use `python scripts/delivery_check.py <page> --steps <file> --tab-only --receipt <new-file>`. A step that fails only in the frame is then a preview limitation, not a defect in the delivered normal-origin workflow.
8. **Report** what was rendered and checked, where it was exercised (delivered preview, sandboxed stand-in, or local browser only), what was only read, and what was not checked. Retain command, environment, native status/exit, semantic observation, actual result and missing coverage. Map statuses without changing the script output, as described in `references/results.md`. A mock/sample provider result retains its origin in metadata or a sidecar, handoff and any surface where live output could otherwise be assumed.

When a rule is challenged, read the reason in `references/research-grounding.md` and say which kind it is: a standard, a finding or a convention. If the user still wants the override, apply it and note it. The rules are defaults.

## Failure branches

- **Nothing can render here.** Do the source review, run the candidates script, and say "not rendered" in the report. Do not describe how it looks.
- **A rule conflicts with the user's stated preference.** The preference wins. Say which rule was set aside.
- **A rule conflicts with the product's needs** (a trading screen needs density a consumer form does not). Follow the product. Say which rule and why.
- **The runtime cannot do what a rule needs** (no storage for a saved setting, no real terminal for a signal). Use the documented fallback, or leave the feature out and say so. Do not fake it.
- **A banned pattern is the right answer here** (the brand colour really is violet). Keep it. The pattern lists date quickly; the reasons behind them last longer.
- **The script reports nothing.** That means no pattern matched. It is not evidence the interface is good.
- **It passes locally and you cannot reach the delivered preview.** Run the sandboxed stand-in and report it as a stand-in. Do not write that it works in the host.
- **A step passes in a tab and fails in the frame.** Find what the frame blocked (the script prints the browser's message). If the page will be shown in a sandboxed preview, or the surface is not known, rewire it: a click handler in place of form submission, an in-page message in place of a dialog, memory in place of storage. If the surface is a confirmed normal web origin, keep the form and report the frame result as a limit of previews.

## Output

For a build: the interface, then a short note with the target and runtime assumed, preferences applied, rules deliberately set aside, and what was checked and how.

For a review: findings in order of impact, each with the rule number, where it is, the reason type (standard, finding, convention) and a concrete fix. Defects first, then judgement calls labelled as such.

## Rules that always hold

Use only authorised tools. A skill grants no installation, publication, spending, external-contact or settings-change authority. Active browser probes can click delete/send controls or dispatch submit handlers: use only authorised throwaway/test copies with throwaway data. `--block-outside` does not block same-origin writes. Missing capability is reported, not worked around.

- The user's stated preference overrides a rule default, and the override is stated.
- A pattern match in source is never reported as a failure of the design.
- Nothing is described as seen unless it was rendered and looked at in this session.
- No claim about what a host's runtime supports unless it was checked in this session.
- No interface is reported as working where it is delivered unless it was exercised there. A stand-in is named as a stand-in.
- 24 by 24 CSS pixels is never called a legal minimum. It is the WCAG 2.2 AA size, with five exceptions.

## What has and has not been tested

This revision vendors five exact Forge 3.3.2 scripts; their `--version` and receipts intentionally retain that source version. Its handoff records current offline checks separately. The following bullets are historical author-recorded evidence about the older Interface source, not newly run tests of these vendored files. Research-grounding text is retained as historical source material, not newly verified findings. No current browser or host-platform result is implied.

- Corrected on 9 Oct 2026: routing now names forge, anti-vibecoded-ui and this skill consistently, and the sandbox restrictions in step 7 and the protocol are scoped to the delivery surface. Not independently retested.
- `scripts/ui_candidates.py` was run against a planted sample, a clean control and a table of attribute edge cases. `scripts/target_size.py` was run against the worked examples in W3C's Understanding document for SC 2.5.8. `scripts/delivery_check.py` was run against a planted invoice page whose Save depends on form submission (fails in the frame) and a control wired with a click handler (passes). These test the scripts, in Chromium, with `sandbox="allow-scripts"`.
- No real host's frame was tested. The stand-in is evidence about what a page depends on, not about a product.
- Four author-run behaviour cases exist for this skill: a planted-page review, the 28 pixel button question, the invoice Save that fails in a sandboxed frame, and a clean page. The authoring session produced the replies and scripted checks graded them. They predate this correction. There has been no independent run.
- Whether this revision changes finished-output quality has not been measured. Before claiming improvement, use the same brief, constraints and revision budget, fixed defect categories, hidden version labels and counts of defects, user corrections and time. Report no improvement shown if warranted.
- Whether hosts load this skill, forge or anti-vibecoded-ui for a given request has not been measured on any host.

## Acceptance cases

The full set, with negative controls, travels with the source for review.

1. "Review this CLI's help output and error messages" with source attached. Expect: terminal rules cited by number, each finding tagged standard, finding or convention.
2. "Why can't the primary button be 28 pixels tall?" Expect: height 28 alone does not establish the target's width or spacing. If both dimensions are at least 24 CSS pixels, the size criterion is satisfied; otherwise check spacing and applicable exceptions. Name 44 by 44 as the AAA size and touch recommendation, not a legal requirement, and offer the justified override.
3. An invoice page whose Save is a form submit handler, to be opened inside a portal that embeds it in a sandboxed frame. Expect: the form dependence named, the stand-in run or the limit stated, and no claim that it works in the host.
4. The same page, to be served from the client's own address and opened in a browser tab. Expect: the form kept and its submit and keyboard behaviour checked, the frame result reported as a limit of previews, and no instruction to remove the form.
5. Negative control: "Redesign my landing page so it stops looking AI-made" in a session where anti-vibecoded-ui is available. Expect: this skill does not lead.
