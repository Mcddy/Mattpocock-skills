## 7. Verify

**Rendered checks.** If you can render, inspect desktop and narrow widths (320 CSS pixels where reflow applies) and exercise the journey, including failure and recovery. For exports, inspect the intended ratio, platform crop and thumbnail. At each target width, check:

- **Wraps:** a short heading, label or status that strands one word while its container has room usually has an arbitrary width cap. Fix the cap or balance the wrap. Never cut a needed qualifier, and let text wrap where meaning or the platform requires it.
- **Grouping:** a lead-in and what it introduces share one group, with no divider or wider gap between them.
- **Fact map:** list each fact a user acts on, where it appears and at what size. Any repeat needs its own context; a headline answer restated by a timeline at another scale is duplication.
- **Roles:** no user input can be read as data.

Use existing tooling and authorised surfaces. Don't install a test stack unasked, and honour tool approvals and errors. If you can't render, finish the source work and name the visual checks that remain. Screenshots don't establish keyboard or screen-reader behaviour, and selected checks aren't conformance.

### Optional scanner result contract

`scripts/ui_review.py scan PROJECT` is lexical triage of supported web sources; `contrast FOREGROUND BACKGROUND` evaluates one supplied opaque hex pair for its selected role. Existing stdout JSON fields remain, with `status`, `exit`, `status_reason` and semantic `coverage` added. Every check writes one stderr `RECEIPT`; help writes none.

| Native status | Exit | Meaning |
|---|---:|---|
| completed | 0 | Full declared source scope scanned, or the requested colour pair meets its selected threshold. Source candidates remain advisory. |
| failed | 1 | The requested opaque colour pair does not meet its selected threshold. This is no whole-interface verdict. |
| partial | 3 | Applicable sources were unreadable, oversized or otherwise unchecked, or the returned candidate list was truncated. |
| runner_error | 4 | Missing/invalid input, refused link/reparse root, or another tool error prevented the check. |
| not_applicable | 5 | No supported in-scope regular web source inputs were available; reason and exclusions are recorded. |

Dependencies/build directories, unsupported formats and child symlinks/reparse points are declared scope exclusions and do not alone make a scoped scan partial. Such links are never followed; a link/reparse scan root is refused. Unreadable applicable directories remain coverage gaps. Review the skipped/exclusion records rather than hiding them. Native underscore spellings map to the report's runner-error/not-applicable categories explicitly.

Preserve command, role/scope, actual result and receipt. Missing capability is not a pass; zero candidates is neither design approval nor accessibility certification. Hashes prove custody, while a semantic check establishes whether the intended action/output was actually reached. The scanner never exercises keyboard, hidden states or product workflows.

**Taste.** After the technical checks:

1. View the render cold, at thumbnail and full size, and write one line saying what it is. If it misses the intended task, repair the framing. In a substantial open-direction brief, interchangeable framing is a reason to revisit the idea. Useful operational conventions and accepted brands do not need novelty to pass.
2. Rerun the median and reason tests on the five most prominent decisions.
3. Replace the most predictable decision where the subject offers a better reason.
4. Remove what nobody would miss.

These are agent lenses, not independent review.

**Outcomes.** Whether a design improves understanding shows in correct answers, consequential errors, recovery, time and transfer to a changed task, each reported separately. Speed, low effort, confidence or gaze patterns alone don't certify understanding, and published effects don't predict this product's results.

**Revise.** Fix the highest-impact problem first.

- If a substantial open-direction brief remains correct but interchangeable after repairs, revisit the organising idea. Preserve accepted directions and useful functional conventions; novelty alone does not justify redesign.
- If the owner still finds it below the bar once named defects are fixed, build a candidate from a different idea with the same content, and compare the two at the same sizes.
- In a defect-only or export check of accepted work, fix the defects and leave the direction alone.



## Example (illustrative)

A trip planner answers "leave after 7:30".

- **Before:** the headline reads "7:42". A timeline below repeats 7:42 at a small size. "7:30" sits in the departure column, styled like a service. A footnote mentions a 7:36 from Stop C.
- **After:** "Leaving after 7:30" is an editable input above the results. The 7:36 from Stop C and the 7:42 from Stop A are option rows at body size, each with its walk and arrival time, so the trade-off sits where the choice is made. The timeline either compares the two arrivals or goes.
- **Avoided:** a second scale for one answer, input disguised as data, and a live option demoted to history.

