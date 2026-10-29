# Research Grounding

The rules in `protocol.md` are prescriptive. This file is the evidence behind the load-bearing ones: what's a documented standard, what's a robust HCI finding, and what's still just informed convention. Read this when the user asks *why* a rule exists, when a rule needs defending against pushback, or when deciding how hard to enforce a rule that conflicts with a specific request.

Tags used in this file:

- FACT: read from the named source in the revision dated beside it. Primary unless a lower tier is named.
- REPORTED: stated by a secondary source that was read. The source tier is named. Not checked against a primary text.
- INHERITED: carried over from an earlier version of this file. The cited source was not re-opened. Treat any number in an INHERITED line as unverified and do not quote it as fact.
- ASSESSMENT: reasoned inference. It can be wrong.
- GAP: not established.

Being able to rebuild this file from its earlier version proves the edits are the ones listed. It says nothing about whether an inherited claim is true.

---

## 1. "AI slop" is a named, documented phenomenon, not a personal taste complaint

INHERITED: Multiple independent 2025-2026 sources describe a converging, self-reinforcing pattern in AI-generated interfaces: purple/indigo gradients, Inter-family fonts, symmetrical three-card layouts, and generic hero sections, and note the pattern is worsening rather than fading as models improve, because striking outputs get folded back into training data and become the new median. [Phogat, Medium, Aug 2026; 925Studios, "AI Slop Fonts and Gradients," Jun 2026]

ASSESSMENT: The mechanism described (output → attention → training data → next generation's default) explains why banning specific surface patterns (Rules 1, 21, 41, 47 in `protocol.md`) has a shelf life: the *specific* purple gradient or hero stack named today will be replaced by a new median pattern in roughly a year. The durable move is the underlying discipline (intentional constraint, semantic color, specific copy), not memorizing this year's list of banned patterns. Revisit the "banned surface patterns" annually.

INHERITED: A 2026 practitioner guide on AI-generated interfaces identifies "everything visible at all times" (no progressive disclosure: showing every panel, table, and form simultaneously because the model can't anticipate which the user needs *right now*) as a distinct slop signature, separate from the visual/color issues. [Mania Design / hey.com, "Spot the Slop," Jul 2026]

ASSESSMENT: This directly supports `protocol.md` Section 3 (varied container weighting, inline expansions over full-page modals) and Section 6 (density toggles, virtualization): the fix isn't just visual restraint, it's information architecture that reveals detail on demand rather than dumping it all upfront.

GAP: There's no controlled study (that a web search surfaced) quantifying *how much* these patterns actually hurt task completion or conversion versus simply reading as generic. The critique is well-documented as an aesthetic/trust signal from practitioners and one empirical UX study (below), not yet as a hard usability metric.

FACT (arXiv abstract page, read 8 Oct 2026): A 2026 study, "Usable but Conventional: An Empirical Study on the UX of AI-Generated Interface Prototypes" (Romero, Wiese, Balancieiri, Leal, Guerino), had 92 participants rate AI-generated and human-made prototypes without knowing which was which, using the UEQ-S questionnaire. AI prototypes rated positively on practical qualities such as usability and efficiency, and neutral or negative on originality and innovation. [arXiv:2605.15124]

ASSESSMENT: This supports a narrow claim. In one survey, people rated generated prototypes well on perceived practical quality and poorly on perceived originality. The study measured perceptions of prototypes with a short questionnaire. It did not measure task success on working software, and it does not show that generated interfaces are free of usability failures. Measured defects in generated interfaces, such as controls pushed off a phone screen or labels rendered too small to read, are easy to find when someone looks. Treat sameness as a common weakness of generated interfaces, and treat usability as something to test, not assume.

---

## 2. Nielsen's 10 usability heuristics (1994, updated 2020): still the baseline

FACT: Jakob Nielsen's ten usability heuristics, visibility of system status, match between system and the real world, user control and freedom, consistency and standards, error prevention, recognition rather than recall, flexibility and efficiency of use, aesthetic and minimalist design, help users recognize/diagnose/recover from errors, and help and documentation, were developed with Rolf Molich in 1990 and refined by Nielsen in 1994 from a factor analysis of 249 usability problems. The article was updated in 2020 with more explanation, and states that the ten have "remained relevant and unchanged since 1994". [nngroup.com/articles/ten-usability-heuristics, read 8 Oct 2026]

ASSESSMENT: Most of `protocol.md`'s GUI rules map directly onto specific heuristics, which is worth knowing when a rule needs justifying to a stakeholder who wants the "why," not just the "what":
- Visibility of system status → Section 8 (streaming/motion feedback), Section 7 rules 63-66 (loading states)
- User control and freedom → Rule 79-80 (undo buffers), Rule 167-168 (TUI destructive-action confirmation)
- Recognition rather than recall → Rule 50 (contextual placeholders), Rule 181-184 (TUI persistent help footer)
- Aesthetic and minimalist design → Section 3 (layout discipline), Rule 29 (bounded stacking)
- Help users recognize, diagnose, recover from errors → Rule 45-46 (diagnostic error copy), Rule 187-188 (TUI error boxes)
- Flexibility and efficiency of use → Rule 38 (command palettes), Rule 132/140 (dual navigation, spatial jumps)

---

## 3. WCAG 2.2: the actual current numbers

FACT: WCAG defines contrast requirements by success criterion: 1.4.3 (AA) requires 4.5:1 for normal text and 3:1 for large text (≥18pt, or ≥14pt bold); 1.4.6 (AAA) raises this to 7:1 normal / 4.5:1 large; 1.4.11 (AA) requires 3:1 for non-text UI components and graphical objects (borders, icons, focus indicators). [W3C, WCAG 2.2, read 8 Oct 2026]

ASSESSMENT: `protocol.md` Rule 6 states AAA (7:1) as the enforced floor for "critical data, body text, and interactive controls." That's a stricter bar than the AA level (4.5:1) most products target: worth knowing so it can be relaxed deliberately for marketing surfaces where full AAA is impractical, rather than applied uniformly by default. AAA is realistically achievable for documentation, data tables, and long-form text; it's a much harder constraint on marketing hero sections with large branded type, where AA is the more common real-world target.

FACT (W3C, WCAG 2.2 Understanding SC 2.5.8, read 8 Oct 2026): Target Size (Minimum) is Level AA. The size of the target for pointer inputs is at least 24 by 24 CSS pixels, with five exceptions: Spacing, Equivalent, Inline, User Agent Control and Essential. A target meets the size when a 24 by 24 CSS pixel square, aligned to the axes, fits completely inside it.

FACT (same source): the Spacing exception is a geometry test, not a gap width. Undersized targets pass when "a 24 CSS pixel diameter circle is centered on the bounding box of each" and "the circles do not intersect another target or the circle for another undersized target". W3C's worked examples: 20 by 20 targets with a 4 pixel space between them pass; 20 by 20 targets with no space fail; a 16 by 16 target abutting a large target fails, and passes with a 4 pixel gap; two rows of 16 pixel high buttons with a 1 pixel gap fail. Touching circles pass; overlapping ones fail.

FACT (same source): the other four exceptions are an equivalent control on the same page that meets the size, a target in a sentence or constrained by the line height of non-target text, a target whose size is set by the browser and not modified by the author, and a presentation that is essential or legally required. Where targets overlap, the overlapping area is left out of the size unless they perform the same action.

FACT (W3C, Understanding SC 2.5.5, read 8 Oct 2026): Target Size (Enhanced) is Level AAA and asks for 44 by 44 CSS pixels, with four exceptions (equivalent, inline, user agent control, essential).

INHERITED: 44 by 44 matches Apple's Human Interface Guidelines (44 by 44 points) and is close to Google Material Design's 48 by 48 dp recommendation. [testparty.ai; wcag22aa.org; AllAccessible, Dec 2025]

ASSESSMENT: 24 by 24 is not an absolute minimum, legal or otherwise. It is the size at which no exception is needed. An undersized target is fine when its circle is clear or another exception applies, and a 24 by 24 target can still be a poor target on a touch screen. Use 44 by 44 as the working size for primary and touch actions, and use the circle test (`scripts/target_size.py`) for dense controls. The four non-geometric exceptions need a person to decide.

FACT (EUR-Lex, Commission Implementing Decision (EU) 2021/1339 of 11 August 2021, read 8 Oct 2026): EN 301 549 V3.2.1 (2021-03) is the harmonised standard under Directive (EU) 2016/2102, the Web Accessibility Directive, which covers the websites and mobile applications of public sector bodies. It applies from 12 February 2022. The decision does not mention Directive (EU) 2019/882.

REPORTED (secondary sources, not checked against the Official Journal or the ETSI text): the European Accessibility Act is a different instrument, Directive (EU) 2019/882, covering listed private-sector products and services, applicable from 28 June 2025. As of August 2026 no harmonised standard had been cited in the Official Journal in support of it, so no version of EN 301 549 gave a presumption of conformity under the Act, and conformity is assessed against the Directive's own Annex I [Legalithm, 14 Aug 2026; tier: legal-technology blog]. EN 301 549 V3.2.1 references WCAG 2.1 Level AA, which has no SC 2.5.8. EN 301 549 V4.1.1, written under standardisation request M/587 and incorporating WCAG 2.2 Levels A and AA, was published on 2 September 2026; its legal effect under the Act waits on citation in the Official Journal [Davis Wright Tremaine, Sept 2026; tier: law firm client note. BrowserStack, 1 Oct 2026; tier: vendor article]. The August source says V4.1.1 was not yet published and the September source gives its publication date; the dates are consistent.

CORRECTION: the version of this file before October 2026 said SC 2.5.8 was "legally required under the EU's European Accessibility Act since June 2025". An interim correction then described EN 301 549 V3.2.1 as the standard giving presumption of conformity without saying under which directive. Both were wrong in the way set out above: V3.2.1 is harmonised under the Web Accessibility Directive, not the Act, and it does not contain 2.5.8.

ASSESSMENT: do not describe SC 2.5.8, or any pixel size, as a legal requirement in the EU. Describe it as the WCAG 2.2 Level AA criterion, likely to matter legally once V4.1.1 is cited. GAP: the Official Journal index for Directive 2019/882 and the ETSI standard were not read. This is not legal advice.

---

## 4. Fitts's Law: the physical basis for target-size and placement rules

INHERITED: Paul Fitts (1954) established that the time to acquire a target rises with the distance to it and falls with its size (in his formulation, movement time is about a + b log2(2D/W)). The direction of the effect is textbook. An earlier version of this file also gave millisecond timings for large and small touch targets and a "2 to 3 times" penalty, citing two design-advice sites. No primary study was located for those figures and they have been removed. [lawsofux.com; uxuiprinciples.com]

ASSESSMENT: This is the mechanism behind `protocol.md` Rule 33-36 (deliberate corner radius and sizing, not stadium buttons for the sake of it) and Rule 40 (bringing actions to the point of selection rather than requiring travel to a fixed toolbar). Padding makes the target itself larger, which is what Fitts's Law rewards. The spacing exception in SC 2.5.8 is a different thing: it leaves the target small and keeps neighbours out of a 24 pixel circle, which reduces mis-taps but does not make the target quicker to hit.

---

## 5. What's convention, not research

Several rules in `protocol.md` are professional convention rather than something with a citable study behind them: worth being honest about this distinction rather than presenting every rule with equal evidentiary weight:

ASSESSMENT: The 45-75 character line-length guideline (Rule 16) traces to typographic tradition (Bringhurst's *Elements of Typographic Style* and decades of print/editorial practice) rather than a specific HCI study; it's near-universal advice in typography references but treat it as strong convention, not an RCT finding.

ASSESSMENT: The 100-150ms / 200ms motion durations (Rule 74) and the 3-5% lightness-shift threshold for surface separation (Rule 4) are design-system convention (matching what Material Design, Apple HIG, and most enterprise design systems converge on) rather than figures traceable to a single controlling study. Apply them as sound defaults, not as inviolable physics.

GAP: Hick's Law (decision time increases with the number and complexity of choices) is real and well-established in the cognitive psychology literature, and it's the implicit justification for `protocol.md`'s density/progressive-disclosure rules (Section 3, Section 6): but no specific paper or figure was pulled for this file. Treat the *direction* of the effect as solid, the specific thresholds in the protocol (e.g., "4 clicks vs 2-click segmented row") as informed convention, not a cited number.

---

## What remains unresolved

- No controlled study quantifies the business impact (conversion, task success, trust) of "AI slop" patterns specifically: the case for avoiding them rests on practitioner consensus and one usability study showing AI output is usable-but-generic, not on a measured harm.
- What any particular chat product's page frame allows (build step, storage, forms, popups) is not recorded here. Check the host in the session, and exercise the page where it is delivered (see `review.md`).
- The line-length, motion-duration, and lightness-shift numbers are convention, not citation-backed thresholds: don't defend them as if they were.
- Citation status: re-read in October 2026 against primary sources: the arXiv study, the NN/g heuristics page, the WCAG 2.2 contrast criteria, SC 2.5.8 and SC 2.5.5, and the EUR-Lex decision. Read at secondary tier: the three articles on the European Accessibility Act. Every line tagged INHERITED was not re-opened.
- Whether SC 2.5.8 is cited in any standard with legal effect in the EU will change. Check before stating it either way.
