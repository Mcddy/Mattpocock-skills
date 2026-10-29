# ANTI-AI INTERFACE PROTOCOL (GUI & TUI DUAL SPECIFICATION)
# Version: 2.5 | Rule reference for interface code
# Modes: [GUI / Web / Desktop] | [TUI / Terminal / CLI] | [Unified System Foundations]
#
# Changelog:
# 2.0 -> 2.1: added Section 0 scope gate, fixed Tailwind-config rule for
#             sandboxed/no-build environments, added faux-terminal compatibility
#             notes to TUI signal/buffer rules, appended Model Compatibility Addendum.
# 2.1 -> 2.2: corrected Rule 35 touch-target sizing against WCAG 2.2 SC 2.5.8/2.5.5
#             and Apple HIG (see references/research-grounding.md for the citations).
#             This file is now a reference loaded by the interface-architect skill;
#             see SKILL.md for the workflow this plugs into.
# 2.2 -> 2.3: opening persona replaced by a purpose statement; Section 0.1 added (theme and
#             user preferences); host-specific runtime claims replaced by host-neutral notes;
#             checklist treats pattern matches as candidates for rendered review; long
#             dashes removed.
# 2.3 -> 2.4: Section 0.2 added (the delivery container); Rule 35 restated with all five
#             SC 2.5.8 exceptions and the circle geometry, and no longer described as a legal minimum;
#             Rule 36 no longer claims what Fitts's Law predicts will feel error-free.
#             Rules 1-34 and 37-200 are unchanged from 2.2 apart from dash removal.
# 2.4 -> 2.5: Section 0.2 and the Delivery checklist line scoped to the delivery surface: the strict
#             set applies to a sandboxed preview or an unknown surface, and forms, storage and
#             downloads are supported on a confirmed normal web origin or native shell.

This file is a rule reference for interface code. Generated interfaces drift toward the average of their training data: the same gradients, chat boxes, card grids and happy-path assumptions. Each rule here is a default with a reason. `research-grounding.md` says which rules rest on a standard, which on a research finding and which on convention.

BAN and ENFORCE mark the default direction of a rule. They are not absolute: the user's stated preference or a specific product need overrides a rule, and the override should be stated. Decide the target (GUI, TUI or both), then apply the matching part and Part III.

---

## SECTION 0: SCOPE & ACTIVATION

This protocol governs **generated interface code** (components, pages, dashboards, CLI/TUI apps). It does not govern:
- Conversational replies, explanations, or plain data output with no rendered interface.
- Single-purpose scripts with no UI surface (a data transform, a cron job, an API client).
- Explicit user requests to keep something minimal, quick-and-dirty, or throwaway: honour that instruction over the protocol.

When the request is ambiguous about whether it wants a real interface or a quick snippet, default to the protocol only once the deliverable crosses into something a human will look at and use more than once.

---

## SECTION 0.1: THEME AND THE USER'S PREFERENCES

The user's stated preferences decide theme, density and tone. This file does not.

- If the user has stated a theme preference, follow it. It overrides every colour default below.
- If nothing is stated: light by default, a dark set that follows the device setting, and the choice exposed where the interface will be used more than once.
- Define colour as tokens (Rule 94) so a theme is one set of values, not a rewrite.
- A customisation control (theme, density, type size, motion) must do what it says, keep its value where the host allows storage, work when storage is missing, and reset.
- Do not add a control that is only decoration. If a setting cannot be made to work in this runtime, leave it out and say so.

---

## SECTION 0.2: THE DELIVERY CONTAINER

An interface is finished where it is used, not where it was written. Chat hosts and many dashboards show a generated page inside a sandboxed frame. Things that work in a browser tab can be switched off there with no error on the page.

Scope. The restrictions below are the strict set. They apply when the page will be shown in a chat host's sandboxed preview, or when the delivery surface could not be confirmed. On a confirmed normal web origin or in a native shell, forms, storage and downloads are fine, and a real form with a submit button and its keyboard behaviour is preferred. Say which surface was assumed.

- Do not hang an action on form submission. Without `allow-forms` the browser drops the submission before the submit event fires. Put a click handler on a `type="button"` control.
- Do not rely on `alert`, `confirm`, `prompt` or `print`. Without `allow-modals` they do nothing. Use in-page messages and dialogs.
- Treat storage as optional. Without `allow-same-origin`, `localStorage` and the rest throw. Wrap every access, keep state in memory, and make the page correct when nothing was stored.
- Do not depend on a new window, a file download or navigating the outer page. Offer the content in the page as well.
- Keep a manual fallback for the clipboard.
- Exercise the main path (enter, save, change, restore) in the delivered preview. If that is not possible, exercise it in a scripts-only sandboxed frame (`scripts/delivery_check.py`) and say that a stand-in was used.
- A pass in a local browser is not a pass in the delivered frame. Report which one was done.

---

## CORE ARCHITECTURAL DIRECTIVES (UNIVERSAL)

1. **Target Modality Routing:**
   - For Web, Mobile, and Desktop Graphical Apps: Apply **Part I (GUI Rules 1-100)** + **Part III (Unified Foundations)**.
   - For Terminal, Console, and CLI Applications: Apply **Part II (TUI Rules 101-200)** + **Part III (Unified Foundations)**.
   - For Hybrid Tools (CLI with Web Dashboards / Electron / Tauri): Enforce strict separation of concerns across both environments.
   - For TUI aesthetics rendered inside a browser sandbox (no real terminal, no PTY): see the **Faux-Terminal Note** under Part II. Apply the same visual and interaction discipline; skip rules that require a real POSIX process.
2. **First-Class Engineering:** Interfaces must never be treated as superficial wrappers over raw prompts. All interactions require deterministic states, explicit error boundaries, edge-case hardening, and high-density information architecture.

---

# PART I: GRAPHICAL USER INTERFACES (GUI RULES 1-100)

### Section 1: Color, Lighting & Palette Architecture (Rules 1-10)
1. **BAN:** Indigo-to-violet/cyan gradients (`from-indigo-500 to-purple-600`) as the uninspired default accent.
2. **ENFORCE:** Maximum 3 base hues: Dominant base surface (60%), Structural neutral (30%), Sharp accent (10%).
3. **BAN:** Artificial glow effects (`shadow-[0_0_50px_rgba(...)]`) around cards and buttons.
4. **ENFORCE:** Background separation via subtle lightness shifts (3-5% contrast delta) before applying borders.
5. **BAN:** Low-contrast washed-out dark mode (pure `#000` text on `gray-900` or `slate-800` text on pitch black).
6. **ENFORCE:** WCAG AAA compliance (min 7:1) for critical/long-form text and data; treat AA (4.5:1) as the acceptable floor for marketing surfaces where AAA is impractical. Non-text UI components (borders, icons, focus indicators) need at least 3:1 (WCAG 1.4.11).
7. **BAN:** Saturated rainbow badge indicators for simple status updates.
8. **ENFORCE:** Intentional, domain-specific semantic colors (warning is warm amber/ochre; success is calm forest/emerald; not radioactive neon).
9. **BAN:** Translucent glassmorphism (`backdrop-blur-md bg-white/10`) layered over unreadable background surfaces.
10. **ENFORCE:** Solid high-legibility surfaces with 1px tactile borders tinted to the background's hue.

### Section 2: Typography & Text Hierarchy (Rules 11-20)
11. **BAN:** Defaulting blindly to Inter, Geist, Poppins, or Space Grotesk everywhere without typographic intent.
12. **ENFORCE:** Expressive pairing: Contrast a distinct display font (or robust grotesque/serif) with a hyper-readable body type.
13. **BAN:** Single italicized serif buzzwords inside sans-serif hero headlines.
14. **ENFORCE:** Strict mathematical type scale (1.250 major third or 1.333 perfect fourth); no arbitrary pixel font sizes.
15. **BAN:** Center-aligned multi-line body paragraphs (>2 lines).
16. **ENFORCE:** Left-aligned body text capped strictly between 45-75 characters per line (`ch` unit) for scan readability: this is editorial/typographic convention (Bringhurst), not a specific study, but it's near-universal practice.
17. **BAN:** Over-tight letter spacing (`tracking-tighter`) on small body copy or data tables.
18. **ENFORCE:** Tabular numbers (`font-variant-numeric: tabular-nums` / `font-mono`) on all quantitative figures and timestamps.
19. **BAN:** Low-contrast gray subtitles (`text-zinc-500` on dark) that fail readability checks.
20. **ENFORCE:** Explicit hierarchy via scale, weight, and visual grouping rather than 5 different shades of faded gray.

### Section 3: Layout, Grids & Composition (Rules 21-30)
21. **BAN:** The "AI Hero Stack": Centered pill badge + H1 + 2-line subtitle + 2 pill buttons.
22. **ENFORCE:** Asymmetrical balance: Left-aligned content anchors, split heroes with live interactive UI previews, or editorial offsets.
23. **BAN:** Uniform 3-column card grids with identical text lengths.
24. **ENFORCE:** Varied container weighting based on information hierarchy (e.g., 2/3 primary workspace + 1/3 contextual rail).
25. **BAN:** Encasing every UI element in an isolated 1px bordered box.
26. **ENFORCE:** Grouping by proximity, whitespace gutters, and shared background surfaces instead of endless nesting boxes.
27. **BAN:** Full-page centered modals for simple interactions or confirmations.
28. **ENFORCE:** Inline expansions, drawers/sheets, or localized popovers anchored to the triggering element.
29. **BAN:** Unbounded vertical stacking that turns dashboards into endless infinite scrolls, or showing every panel/table/form at once instead of the specific thing the user needs right now (progressive disclosure: see research-grounding.md, "AI slop" section).
30. **ENFORCE:** Fixed viewport ergonomics for productivity tools: pinned headers, split scroll panes, and visible sticky footers.

### Section 4: Controls, Inputs & Ergonomics (Rules 31-40)
31. **BAN:** The "Chatbox Crutch": Replacing structured UI with a generic open-ended LLM text prompt.
32. **ENFORCE:** Direct-manipulation controls: Segmented pickers, multi-select tags, sliders, dual-range knobs, and date steppers.
33. **BAN:** Over-rounded stadium/pill buttons (`rounded-full`) for utility, data, and form buttons.
34. **ENFORCE:** Intentional, restrained corner radius (4px-8px) that matches the container grid tokens.
35. **BAN:** Pointer targets under 24 by 24 CSS px that meet none of the five WCAG 2.2 SC 2.5.8 exceptions: spacing (a 24 px circle centred on the target is clear of other targets and of other undersized targets' circles), an equivalent control that meets the size, inline in a sentence, sized by the browser and not restyled, or essential. `scripts/target_size.py` applies the geometry. 24 by 24 is the AA criterion, not a legal threshold and not a design goal.
36. **ENFORCE:** 44×44 CSS px as the actual target for primary and touch-oriented actions (WCAG 2.5.5 AAA, Apple HIG, close to Material's 48dp). Larger targets are quicker to hit and easier to hit accurately (Fitts's Law). Pair with a visible `:focus-visible` ring.
37. **BAN:** Dropdowns requiring 4 clicks when a 2-click segmented button row achieves the same goal.
38. **ENFORCE:** Command palettes (`Cmd+K`) for power users, supplemented by keyboard accelerator hints (`?`, `/`, `J/K`).
39. **BAN:** Custom un-styled scrollbars that break native operating system scrolling momentum.
40. **ENFORCE:** Contextual action toolbars that appear on item selection rather than cluttering every row with duplicate action buttons: this also shortens the Fitts's Law travel distance from selection to action.

### Section 5: Microcopy, Labels & Product Tone (Rules 41-50)
41. **BAN:** LLM buzzword soup: *"Supercharge your seamless workflow with next-gen AI-powered insights."*
42. **ENFORCE:** Plain, declarative human language: State what the tool does in concrete terms (*"Track compute costs across AWS clusters"*).
43. **BAN:** Rigid symmetrical triplet copywriting (*"Fast. Reliable. Scalable."*).
44. **ENFORCE:** Feature statements with explicit metrics, user outcomes, and concrete workflows.
45. **BAN:** Generic apologetic error toasts: *"Oops! Something went wrong on our end. Please try again."*
46. **ENFORCE:** Diagnostic, actionable error copy: *"Database connection timed out on port 5432. [Retry] [View Logs]"*.
47. **BAN:** Sparkle icons (`✨`, `✦`) prepended to every standard CRUD feature, button, or search bar.
48. **ENFORCE:** Functional action labels: Use standard terminology ("Filter", "Export", "Search") without artificial intelligence gimmicks.
49. **BAN:** Generic default placeholders: *"Enter text here..."* or *"Type a message..."*.
50. **ENFORCE:** Contextual, illustrative placeholders: *"e.g., staging-v2-cluster or 192.168.1.1"*.

### Section 6: Data Tables & Information Density (Rules 51-60)
51. **BAN:** Low-density tables with massive padding that only show 4 rows on a 1080p screen.
52. **ENFORCE:** High-density information design: Compact rows, sticky column headers, and customizable density toggles (compact/comfortable).
53. **BAN:** Raw unformatted database outputs (`2026-09-07T15:30:00Z` or `104857600`).
54. **ENFORCE:** Humanized formats with full detail on hover (*"2 hours ago"* + Tooltip: *"Sep 7, 2026, 3:30 PM AEST"* | *"100 MB"*).
55. **BAN:** Un-truncated table strings that break column alignments or push actions off-screen.
56. **ENFORCE:** Strict cell truncation (`text-ellipsis overflow-hidden`) coupled with click-to-copy or hover tooltips for long hashes/IDs.
57. **BAN:** Pagination-only tables for small datasets (<200 rows).
58. **ENFORCE:** Virtualized scrolling with instant client-side substring filtering and column sorting.
59. **BAN:** Center-aligned quantitative or monetary data columns.
60. **ENFORCE:** Right-aligned numbers/currency (with aligned decimals) and left-aligned text strings.

### Section 7: State Handling & Edge Cases (Rules 61-70)
61. **BAN:** The Happy-Path Trap: Interfaces designed solely for 4-character mock names and perfect 16:9 images.
62. **ENFORCE:** Graceful handling of extreme data: 80-character names, missing avatars, broken image fallbacks, and zero-state data.
63. **BAN:** Blank white or black screens while API data or models are fetching.
64. **ENFORCE:** Proportional skeleton loaders that match the geometry of the incoming content (no layout shift upon arrival).
65. **BAN:** Full-screen blocking spinners for background or localized updates.
66. **ENFORCE:** Optimistic UI updates with micro-status indicators (e.g., inline checkmark or subtle progress bar) and rollback on error.
67. **BAN:** Unstyled default browser alerts (`alert()`, `confirm()`).
68. **ENFORCE:** Accessible, focus-trapped dialog primitives with destructive action warnings in high-contrast red.
69. **BAN:** Zero-item empty states that simply say *"No data available"*.
70. **ENFORCE:** Actionable empty states: Include a clear graphic/icon, explanation, and a direct CTA (*"No projects yet. [Create your first project ->]"*).

### Section 8: Motion, Streaming & Interaction (Rules 71-80)
71. **BAN:** Unbuffered token-by-token streaming that continuously vibrates or jumps parent container height.
72. **ENFORCE:** Container height stabilization, debounced layout recalculation, and smooth auto-scroll lock.
73. **BAN:** Bouncy, theatrical spring physics on enterprise/utility interface transitions.
74. **ENFORCE:** Crisp, professional micro-durations: 100ms-150ms ease-out for hovers/menus; 200ms ease-out for sheets/drawers. (Design-system convention, matches what most enterprise systems converge on, not a single controlling study.)
75. **BAN:** Auto-playing decorative background video loops or particle canvases that hijack GPU cycles.
76. **ENFORCE:** Static, highly optimized SVG motifs or clean CSS line patterns with `prefers-reduced-motion` overrides.
77. **BAN:** Hover effects that trigger unintended horizontal layout reflows or scrollbars.
78. **ENFORCE:** GPU-accelerated transforms (`transform: scale()`, `opacity`, `translate3d`) that do not trigger browser layout thrashing.
79. **BAN:** Immediate destructive deletion without an undo buffer.
80. **ENFORCE:** "Toast with Undo" pattern (5-second grace window) or two-step inline verification for critical destructive actions.

### Section 9: Accessibility & Keyboard Workflows (Rules 81-90)
81. **BAN:** Unnavigable mouse-only interfaces where `Tab` focus gets lost or invisible.
82. **ENFORCE:** Full keyboard navigability: Logical `tabIndex`, visible `:focus-visible` indicator, and `Esc` key handlers on all overlays.
83. **BAN:** Using non-semantic `div` and `span` tags for clickable interactive elements.
84. **ENFORCE:** Native `<button>`, `<a>`, `<input>`, `<dialog>`, and `<main>` tags with appropriate ARIA roles and labels.
85. **BAN:** Conveying status purely through color (e.g., red circle vs. green circle with no text or icon difference).
86. **ENFORCE:** Multi-modal status indicators: Shape + Icon + Explicit text label + Color.
87. **BAN:** Fixed non-responsive viewports that break on mobile screens or at 200% browser zoom.
88. **ENFORCE:** Fluid responsive layouts using CSS Grid and Flexbox with zero horizontal overflow on small screens.
89. **BAN:** Autocomplete attributes missing from form fields.
90. **ENFORCE:** Proper `autocomplete`, `type="email"`, `inputmode="numeric"`, and clear inline validation feedback.

### Section 10: Architectural Code Craft (Rules 91-100)
91. **BAN:** Giant 800-line monolithic frontend files mixing state, styles, database fetches, and JSX.
92. **ENFORCE:** Clean component boundaries: Separate UI presentation, custom hooks for business logic, and API utility layers.
93. **BAN:** Inline hard-coded hex codes (`#1e293b`) and arbitrary pixel offsets (`margin: 13px`) in component markup.
94. **ENFORCE:** Strict design token consumption. Where a real build step exists (Next.js, Vite, a configured project), use Tailwind config theme tokens. **Where there is no build step (a hosted single page, a single HTML file)** there is no Tailwind compiler to extend the theme, so define tokens as CSS custom properties on `:root` and consume those everywhere. Check which situation you are in before choosing the mechanism (Host Notes).
95. **BAN:** Fragile raw `fetch` calls lacking validation, timeouts, or abort controllers.
96. **ENFORCE:** Type-safe client validation using Zod/TypeScript schemas with explicit error parsing.
97. **BAN:** Spurious `useEffect` dependencies triggering continuous component re-renders or infinite API loops.
98. **ENFORCE:** Stable memoization (`useCallback`, `useMemo`), clean event-driven state transitions, and server-state caching (TanStack Query/SWR) where a real backend exists.
99. **BAN:** Duplicate logic and copy-pasted UI blocks scattered across pages.
100. **ENFORCE:** Reusable, atomic design primitives with composable props (e.g., `<Button variant="outline" size="sm" />`).

---

# PART II: TERMINAL USER INTERFACES & CLI (TUI RULES 101-200)

**Faux-Terminal Note:** When a TUI is being rendered inside a browser sandbox (an HTML or React imitation of a terminal, not a real PTY process), rules that assume a real OS process (SIGWINCH, raw mode, exit codes, POSIX signals) apply as *behavioural equivalents*: emulate the resize handling, the cleanup-on-unmount, the signal-shaped keybindings, in JS/CSS rather than a real syscall. Don't skip the discipline just because there's no real terminal underneath it.

### Section 11: ANSI, Palettes & Color Fallbacks (Rules 101-110)
101. **BAN:** Hard-coded 24-bit RGB TrueColor without runtime fallback detection.
102. **ENFORCE:** 3-tier color fallback architecture: TrueColor (24-bit) -> ANSI-256 -> Base 16-color ANSI -> Monochrome.
103. **BAN:** Pure un-tinted neon colors (`#FF00FF`, `#00FFFF`) as primary UI container borders.
104. **ENFORCE:** Semantic ANSI palettes using base terminal colors (`cyan`, `magenta`, `dim`, `bold`) tuned to inherit the user's terminal theme.
105. **BAN:** Blindly ignoring the standard `NO_COLOR` environment variable.
106. **ENFORCE:** Automatic respect for `NO_COLOR`, `CLICOLOR`, `CLICOLOR_FORCE`, and `--no-color` flags.
107. **BAN:** Inverting foreground/background on active rows using unreadable, glaring white blocks.
108. **ENFORCE:** Subtle cursor styling: Bold font, discrete gutter indicators (`> ` or `▌`), or subtle background luminosity shifts (5-10%).
109. **BAN:** Using color as the exclusive indicator of system state or severity.
110. **ENFORCE:** Multi-modal status markers: Glyph + Text Token + Color (e.g., `[✓] OK`, `[!] WARN`, `[✗] ERR`).

### Section 12: Unicode, Glyphs & Box-Drawing Sanity (Rules 111-120)
111. **BAN:** Raw, unsupported Nerd Font icons and esoteric emojis that render as broken missing-glyph boxes on default terminals.
112. **ENFORCE:** Standard Unicode box-drawing primitives (`─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼`) with pure ASCII fallback modes (`- | +`).
113. **BAN:** Double-line borders (`╔═╗`) nested inside double-line borders creating visual static.
114. **ENFORCE:** Single-line thin borders (`rounded` or `sharp`) for panels, and borderless split panes separated by whitespace gutters or single vertical bars (`│`).
115. **BAN:** Mixing rounded corners (`╭╮╰╯`) on outer frames with sharp corners (`┌┐└┘`) on inner sub-blocks.
116. **ENFORCE:** Global border token consistency throughout all layouts.
117. **BAN:** Assuming every character occupies exactly 1 column width (breaking Asian full-width CJK characters and complex emojis).
118. **ENFORCE:** Explicit character cell calculation via Unicode width libraries (`wcwidth` / `unicode-width`).
119. **BAN:** Decorative sparkle emojis (`✨`, `✦`, `🤖`) prepended to automated CLI outputs or menu headers.
120. **ENFORCE:** Pragmatic, utilitarian terminal typography and ASCII symbols (`*`, `->`, `::`).

### Section 13: Spatial Layout, Viewport & Resize Handling (Rules 121-130)
121. **BAN:** Panicking, crashing, or mangling the screen on `SIGWINCH` terminal resize events (or, in a faux-terminal, on browser window resize).
122. **ENFORCE:** Atomic re-calculation of dynamic layout constraints (percentages, minimum/maximum cell clamps) on every resize.
123. **BAN:** Crashing when the terminal window is shrunk below 80x24.
124. **ENFORCE:** Graceful responsive degradation: Progressive panel collapse, tab grouping, or a clean "Terminal too small (WxH < 60x15)" placeholder.
125. **BAN:** Hard-coding absolute coordinates (`x: 40, y: 12`) for screen layouts.
126. **ENFORCE:** Flexbox/Constraint-based layout engines (e.g., Ratatui `Layout::default().constraints(...)`, Textual CSS, or CSS Grid in a faux-terminal).
127. **BAN:** Full-screen TUI execution for single-line queries or quick inspections.
128. **ENFORCE:** Inline execution mode (render in stdout scrollback) for transient commands; Alternate Screen Buffer (`smcup`/`rmcup`) only for persistent interactive dashboards.
129. **BAN:** Deeply nested panels where inner scroll areas compete with outer window bounds.
130. **ENFORCE:** Master-detail split planes (e.g., Left 30% index, Right 70% content viewport) with fixed, predictable bounds.

### Section 14: Navigation, Focus & Vim/Emacs Bindings (Rules 131-140)
131. **BAN:** Mouse-only navigation or arrow-key-only binding patterns.
132. **ENFORCE:** Universal dual navigation: Vim keys (`h/j/k/l`, `g/G`, `Ctrl+u/d`) AND standard Arrow/PageUp/PageDown keys.
133. **BAN:** Invisible or ambiguous focused active states.
134. **ENFORCE:** High-contrast focus indication: Highlighted border color, active title pill, and dimmed/faded borders on inactive widgets.
135. **BAN:** Trapping the user with non-standard exit keys or no escape path.
136. **ENFORCE:** Universal `q` (in read/navigate mode), `Esc` (to back out of sub-views), and un-intercepted `Ctrl+C` handling.
137. **BAN:** Stealing standard OS terminal signals (`Ctrl+Z`, `Ctrl+\`) without explicit terminal multiplexer intent.
138. **ENFORCE:** Proper terminal raw mode lifecycle management; restore canonical mode on exit or suspension.
139. **BAN:** Linear `Tab` cycles that require 30 keystrokes to cross the screen.
140. **ENFORCE:** Spatial panel jumps (e.g., `1-9` keys, `Alt+1..4`, or `H/L` pane switches) + `Tab` / `Shift+Tab` for micro-cycling.

### Section 15: State Machines, Caching & Screen Buffers (Rules 141-150)
141. **BAN:** Unbuffered, line-by-line full screen repainting that causes visual strobe/flicker.
142. **ENFORCE:** Double buffering and differential frame rendering: Write to an off-screen buffer, calculate the diff, and emit only changed cells.
143. **BAN:** Running heavy computational or blocking I/O tasks directly inside the main UI event loop.
144. **ENFORCE:** Strict actor/event-loop separation: Dedicated background worker threads/channels communicating asynchronously with a lightweight UI renderer.
145. **BAN:** Uncapped frame-rate loops burning 100% CPU on an idle terminal.
146. **ENFORCE:** Event-driven redraws (render only on key press, timer tick, or channel receive) or capped 30-60 FPS render loops.
147. **BAN:** Losing cursor position or scroll offset when toggling between views.
148. **ENFORCE:** Persistent viewport state models: Preserve row selection indices and horizontal scroll offsets per panel.
149. **BAN:** Polling backend endpoints without backoff or jitter.
150. **ENFORCE:** Event-driven push sockets or debounced polling with backoff and visual sync markers.

### Section 16: Streams, Spinners, Logs & Progress UX (Rules 151-160)
151. **BAN:** Freezing the entire terminal during long background operations without progress feedback.
152. **ENFORCE:** Non-blocking animated braille/ASCII spinners (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) or deterministic progress bars.
153. **BAN:** Leaving obsolete completed spinners and ephemeral progress bars behind in shell history.
154. **ENFORCE:** Line clearing on resolution (`\r\033[K` or widget teardown) followed by an immutable summary log line.
155. **BAN:** Indeterminate progress bars when discrete item counts or byte metrics are available.
156. **ENFORCE:** The "X of Y" progress pattern: `[████████░░░░] 67% (42/60 files, 1.2 MB/s, ETA 4s)`.
157. **BAN:** Flooding stdout with unthrottled streaming logs that blow past user scan speed.
158. **ENFORCE:** Virtualized ring-buffer log viewports with auto-scroll lock (pause auto-scroll when user scrolls up, resume at bottom).
159. **BAN:** In-progress present-tense verbs left behind after completion (*"Fetching dependencies..."* staying forever).
160. **ENFORCE:** Mutating verbs from active to past tense on completion (*"Fetching dependencies..."* -> `✓ Dependencies installed (142ms)`).

### Section 17: Forms, Modals & Direct Manipulation (Rules 161-170)
161. **BAN:** Breaking raw terminal modes by calling native standard `input()` / `scanf()` inside an active TUI.
162. **ENFORCE:** Purpose-built TUI input components handling cursor coordinates, backspace, insertion, and text selections.
163. **BAN:** Unchecked text input overflow that breaks border boxes or wraps into adjacent UI columns.
164. **ENFORCE:** Horizontal internal scrolling within fixed input fields with overflow indicator markers (`…` / `$`).
165. **BAN:** Full-screen modal takeovers for simple binary confirmations.
166. **ENFORCE:** Centered floating overlay popups with a drop shadow or dimmed background frame.
167. **BAN:** Destructive actions executed immediately on a single keystroke (e.g., pressing `d` immediately dropping a table).
168. **ENFORCE:** Two-step confirmation dialogs (`[y/N]`), explicit type-to-confirm prompts, or a temporary timed undo buffer.
169. **BAN:** Forms without inline syntax or validation checks.
170. **ENFORCE:** Real-time inline field validation indicators with concise error messages rendered below the active input cell.

### Section 18: High-Density Tables, Tree Views & Lists (Rules 171-180)
171. **BAN:** Un-virtualized rendering of lists with 10,000+ items that lags the render cycle.
172. **ENFORCE:** Viewport virtualization: Render only the `N` visible rows fitting the terminal height.
173. **BAN:** Fixed column widths that wrap arbitrarily and destroy table grid alignment.
174. **ENFORCE:** Strict cell truncation (`…`) with dynamic column width distribution based on available terminal width.
175. **BAN:** Tables without built-in substring search or instant filtering.
176. **ENFORCE:** Universal `/` search hotkey that live-filters visible items and highlights matched substrings.
177. **BAN:** Multi-level tree views that expand without clear hierarchy indicators.
178. **ENFORCE:** Standard tree glyphs (`├─`, `└─`, `▼`, `▶`) with indent tracking and collapse/expand (`Space` / `Enter`).
179. **BAN:** Center-aligned numerical data in lists and tables.
180. **ENFORCE:** Right-aligned numbers and timestamps (tabular numeric format) paired with left-aligned string names.

### Section 19: Microcopy, Discoverability & Help (Rules 181-190)
181. **BAN:** Forcing users to read external man pages or web docs just to learn basic keybindings.
182. **ENFORCE:** Three-tier contextual help: (1) Persistent 1-line footer shortcuts, (2) `?` overlay popup for all keys, (3) `--help` manual.
183. **BAN:** Static, stale help footers that show irrelevant commands for the active screen context.
184. **ENFORCE:** Dynamic status bar key hints that update based on the currently focused panel or modal.
185. **BAN:** Verbose, essay-length system alerts in terminal dialogs.
186. **ENFORCE:** Concise, telegraphic, high-density copy (*"ERR: Port 8080 busy (PID 14209). [k] Kill [c] Cancel"*).
187. **BAN:** Raw, unhandled stack traces or JSON blobs dumped directly into the TUI frame.
188. **ENFORCE:** Human-formatted diagnostic error boxes with copy-to-clipboard or view-raw-log toggles.
189. **BAN:** Cryptic custom hotkeys that fight terminal standards (`Ctrl+W` closing the app instead of deleting a word).
190. **ENFORCE:** Standard POSIX / readline hotkeys (`Ctrl+A` start of line, `Ctrl+E` end, `Ctrl+U` clear, `Ctrl+W` delete word).

### Section 20: Terminal Hygiene, Signals & POSIX Protocols (Rules 191-200)
191. **BAN:** Leaving the user's terminal broken (invisible cursor, raw mode stuck, text garbled) after a panic or exit.
192. **ENFORCE:** Global panic hooks and cleanup destructors (`atexit`, `drop`) that restore cursor visibility, disable raw mode, and exit alternate screen. In a faux-terminal, the equivalent is a `useEffect` cleanup / component-unmount handler that tears down listeners and timers.
193. **BAN:** Breaking unix pipeline composability (`app | grep foo` failing because ANSI codes or TUI chrome were sent to stdout).
194. **ENFORCE:** Automatic TTY detection: Run interactive TUI if stdout is a TTY (`isatty()`); emit clean machine-readable plain text or JSON if piped. Not applicable in a faux-terminal; skip.
195. **BAN:** Swallowing exit codes (always exiting `0` even when fatal errors occur).
196. **ENFORCE:** Standard POSIX exit codes (`0` success, `1` generic error, `130` SIGINT/Ctrl+C).
197. **BAN:** Hijacking mouse scroll without bypassing capability.
198. **ENFORCE:** Mouse wheel support with `Shift+Drag` passthrough for native terminal text copying.
199. **BAN:** Ignoring user configuration files (`~/.config/app/config.toml` or environment variables).
200. **ENFORCE:** Full configuration hierarchy: CLI flags > Env vars > Config file > Built-in defaults. In a faux-terminal, the equivalent hierarchy is URL params > in-memory session state > component defaults, since there's no real filesystem or env.

---

# PART III: UNIFIED SYSTEM FOUNDATIONS & PRE-FLIGHT AUDIT

```
+-----------------------------------------------------------------------+
|                       INTERFACE RUNTIME PROTOCOL                      |
+-----------------------------------+-----------------------------------+
|             GUI PATH              |             TUI PATH              |
|   Semantic Tokens (CSS / TW)      |   ANSI Fallback / NO_COLOR        |
|   Direct-Manipulation Controls    |   Vim (hjkl) + POSIX Readline     |
|   Proportional Skeleton Loaders   |   Double-Buffered Diff Rendering  |
|   Zero Layout Shift on Stream     |   Atomic SIGWINCH View Resizing   |
|   WCAG AAA Accessible Contrast    |   Clean Exit / Panic Terminal Drop|
+-----------------------------------+-----------------------------------+
```

### Checklist: before building, and again on the rendered result

Subjective items are judged by looking at the rendered interface. A text match in the source is a prompt to look, not a verdict.

- [ ] **Scope:** does this request call for interface code (Section 0)?
- [ ] **Modality:** GUI, TUI or both, with the two kept separate?
- [ ] **Runtime:** what this host supports has been checked, not assumed (Host Notes, Rule 94, Faux-Terminal Note).
- [ ] **Theme:** the user's stated preference is applied; with none stated, light default, dark follows the device, tokens throughout (Section 0.1).
- [ ] **Pattern candidates:** each generic pattern found (default gradients, chat-box-first layout, sparkle icons, filler copy) has been looked at in the render and either removed or kept for a stated reason.
- [ ] **Edge cases:** long strings, empty, loading, error, offline and extreme inputs each have a designed state.
- [ ] **Keyboard:** the whole task can be done without a pointer (GUI: visible focus and sensible order; TUI: documented keys).
- [ ] **Hygiene:** tokens separate from markup, large lists virtualised, clean-up on exit or unmount; in a TUI, signals handled or their in-browser equivalents.
- [ ] **Delivery:** the main path was exercised in the delivered preview, or in a scripts-only sandboxed frame with that stated; where that surface is a sandboxed preview or not known, nothing depends on form submission, native dialogs, popups, downloads or storage (Section 0.2).
- [ ] **Evidence:** what was rendered and checked is stated; what was not checked is stated as not checked.

---

## HOST NOTES (no host is assumed)

This file names no product's runtime. Hosts change, and a rule that was true for one last year may be false now.

- Before choosing how to define tokens or keep state, find out what this runtime has: a build step or not, which libraries load, whether browser storage works. Read the host's own instructions or test it.
- If you cannot find out, write for the smallest common case: CSS custom properties for tokens, state in memory, storage wrapped in try and catch with the page correct when storage is empty or throws.
- Loosen only for a capability you have confirmed in this session.
- GAP: the limits of any particular chat product's page sandbox are not recorded here. Earlier versions of this file stated them as fact; those statements were removed because they could not be kept current.
