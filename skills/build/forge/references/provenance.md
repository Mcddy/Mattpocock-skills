# Provenance: what was tested, and what was not

A record for reviewers. It does not change how the skill works.

## Version 3.4.0 (25 Oct 2026, completed locally by Codex)

Shaun authorised Codex to complete canonical builds after Claude stopped at its usage limit. Based on the delivered 3.4.0-rc1, this revision resolves conflicting universal hero, imagery, radius and split-layout requirements. Task, data, device and accepted brand take precedence in production; expressive options remain available. Reference evidence distinguishes a static capture from an exercised interaction.

The sixteen-direction board, all kit assets and all executable code are byte-for-byte unchanged from 3.3.2. The requirement ledger, hard-constraint disclosure and evidence limits remain. Package integrity and source/trap review establish these bounded changes, not better finished outputs. No new controlled visual comparison has run and no visual improvement is claimed. Installation and platform readback are recorded separately by the installer.

## Version 3.4.0-rc1 (25 Oct 2026, candidate, not accepted)

**Why.** In the blind comparison of 3.2.0 against 3.3.0, neither rater saw any visual improvement. The user then supplied three reference packs of shipped products. Forge's visual bar had been "a Dribbble shot", which aims at concept art, not working products.

**What changed.**
- Step 4b: a reference analog chosen by work surface. It feeds a structure contract.
- Question 13: the Dribbble lens is replaced by a mismatch review against that analog, plus six craft dimensions (`visual.md` section 10).
- A short `reference-method.md`, and one line on proof of action.

**Not changed:** the board, its directions, the kit and the scripts.

**Result.** It is judged only by the frozen comparison protocol. No improvement is claimed before that comparison is run.

## Version 3.3.2 (25 Oct 2026)

A narrow repair of 3.3.1 from Codex's source review. Two corrections, nothing else.
- `dead_controls.py`: a listed control that is not present on a fresh load was counted but did not make the run partial. A run could therefore report completed while a control was never tried. It is now a coverage gap (partial).
- `target_size.py`: any link with a text node beside it was marked inline, and a noted target dropped out of the undecided list. A row of small block-style action links separated by "·" could therefore complete. The inline exception is now applied only to a link laid out inline (computed display inline) with at least three words of running text around it, or to a target declared inline in RECTS.json. A link that may be inline but is not established stays undecided (partial).

Run on 25 Oct 2026, from this package, with isolated good and bad fixtures for each correction. Results are in the 3.3.2 receipts. The board, its definitions, order and styles, and all 114 kit asset files are unchanged from 3.3.1 and the baseline.

## Version 3.3.1 (25 Oct 2026)

A technical repair of 3.3.0 after an independent review in Codex. No visual or design-method change, and no claim that output looks better.

**Baseline.** `claude-skills-sync/zips/forge.zip`, SHA-256 a3b12f8d…5256, 185 files; SKILL.md 99354780…921a, `kit3.css` cf7cbb77…28b6. Codex compared it byte for byte with every installed forge file. 3.3.0 had been diffed against a later local copy instead, so its "unchanged board bytes" claim was false: a `kit3.css` comment and the Plum Peach row in `visual.md` differed. Seven reference-app images also carried C2PA provenance metadata added when files were saved in the delivery folder (pixels identical).

**What changed.**
- Untouched files restored to the baseline bytes: `kit3.css`, the Plum Peach row, and the seven plant images.
- The approved ChatGPT `agents/openai.yaml` and `assets/icon.svg` added byte for byte (187 files).
- Receipts:
  - a bare `--receipt` prints a usage_error receipt;
  - an unwritable receipt file keeps the product result and makes the run a runner_error;
  - every check records counts, ids and artefacts from its own run data.
- Coverage gaps are partial, not passes:
  - text over images (`contrast_check.py`);
  - targets needing a human exception decision, or overlapping (`target_size.py`);
  - no steps given (`delivery_check.py`);
  - composite items whose keyboard path could not be shown (`dead_controls.py`, `render_gate.py` R9b).
- `direction_board.py` reads its directions back from a payload marked with a per-run nonce. A page containing its own `const D = …;` can no longer be mistaken for the board data.
- Keyboard checks follow W3C ARIA APG:
  - activation keys by role (Space for switches, checkboxes and radios; Enter for links; Enter and Space for buttons);
  - `tabindex="-1"` inside a composite widget is followed with arrow keys from the widget's Tab stop;
  - reached is OK, not reached is UNRESOLVED (partial), and no path is MOUSE ONLY or an R9 failure;
  - background requests alone never count as a key working.
- `dead_controls.py` counts separately what was activated, external links not followed, controls absent on a fresh load, unclickable controls and those over the limit.

**Run on 25 Oct 2026**, from this package (results in the 3.3.1 test receipts):
- 34 of 34 cases met their stated expectation: R1 to R10, the trap cases, and a known-good page beside each.
- Board invariant against the baseline: the definitions, order, templates, styles, capture and grid code, and all 114 kit asset files are byte-identical. Only the kit README changed, by one documentation line.
- Matched renders from the baseline and 3.3.1 scripts: 33 of 33 captures and `board.html` identical.
- Standalone board opened alone, offline: 16 of 16 directions applied, 16 distinct.
- Pillow and playwright blocked: runner_error with a receipt. A fault injected inside the run: runner_error.
- Plant round full run: API 54/54 plus both clock files; page steps 56/56 in three modes; render gate completed in five states; contrast 0 below; targets 16/16 and 15/15; dead controls 0 no-effect, 0 MOUSE ONLY, 0 CLICK ONLY; launcher self-test passed.

**Limits.**
- The keyboard composite path is tested with the right and down arrow keys only. Two-dimensional grids and type-ahead are not exercised.
- The checks show an observable change, not that the promised action succeeded.
- Not run: the EXE build on Windows, and real devices.

## Version 3.3.0 (25 Oct 2026)

**Why.** A review of finished outputs, rather than skill text, found failures that the checks of 3.2 let through: a design pack that ranked a requirement low because the chosen design could not meet it; a README stating an inferred need as fact; a screen labelling a synthetic score "confirmed unmet need"; mouse-only table rows; a fallback to mock output with no origin carried; `render_gate.py` crashing with a traceback when a package was missing, and exiting 0 when its accessibility scans had not run; a live board that showed sixteen empty frames when opened alone. The user also rejected two screens as dated ("2010"), which no scanner had flagged. The review was done with an independent reviewer in Codex, who challenged each change before it was built.

**What changed.**
- Brief and design pack: every requirement tagged confirmed, inferred or preference with its source; a requirement ledger; priority from the brief, never from what an option can deliver; a conflict with a confirmed requirement opens the stop message.
- Words bounded by evidence (sample, synthetic, candidate, measured, validated), and origin (live, sample, mock) carried through fallbacks.
- One result contract for the check scripts (`references/results.md`): completed, failed, partial, runner_error and usage_error, a RECEIPT line from every run including crashes, and exit codes documented per tool. A version mismatch is held, not worked around.
- `dead_controls.py`: MOUSE ONLY (acts on click, takes no focus, delegated handlers included, real controls excluded) and `--keyboard` (CLICK ONLY on Enter or Space).
- `direction_board.py`: for a page that is a file, the page and its kit are packed into `board-live.html`, so it opens offline as one file and can be made with Python alone. The board's directions, order, notes, recommendations, markup, styles and captures are unchanged.
- Routing: a narrower description; "Not this skill" rows for pocket-app, web-to-store, threat-model, state-gallery and sample-picker; the Demo tier uses pocket-app's save library when present.
- A fourteenth craft question and `frontend.md` section 11, "Does it look current", from the two rejected screens. It is a judgement, not a recipe: boundaries, density and purposeful empty states stay.
- What to do when this skill's own files cannot be reached (seen in one ChatGPT chat on 24 Oct 2026; another session reached them): check in every session, say so, never imitate a script run or the board, hand over the command.
- Plant round: README and design pack corrected (phone use tagged inferred; reach ranked from the brief; the conflict first); a first README line names the gap kept for teaching. Stock count is labelled a teaching example.

**Run on 25 Oct 2026** (Linux, Python 3, Chromium, from the package being shipped):
- Board invariant: `DEFAULT`, `NAMES`, the board templates, styles, capture and grid code, and all 115 visual-kit files byte-identical to 3.2.0; the live template differs only by two plumbing slots. Full boards from 3.2.0 and 3.3.0 on the same page: 33 of 33 captures and `board.html` pixel- and byte-identical.
- Standalone board, opened alone in an empty folder with every non-file request blocked: 16 of 16 chips; both frames applied each direction and answered; 16 distinct looks (signature colour, background, display face); no font or request failures; a contact sheet of the 16 phone frames looked at.
- `render_gate.py`: Pillow and playwright blocked by an import hook gives runner_error, exit 4, with a receipt (3.2.0: traceback, exit 1); playwright alone blocked, the same; axe-core absent gives partial, exit 3, naming R6, R7 and R13 (3.2.0: exit 0); with axe-core, a clean page gives completed, exit 0, and an overflowing page failed, exit 1; a fault injected inside the run gives runner_error with a receipt.
- `dead_controls.py` on a fixture: four MOUSE ONLY elements found (two rows with their own handlers, two header cells answered by a delegated handler, the container reported once); the native-button table, a pointer card with no handler and a card holding a real button not reported; a `div role=button` dead on Enter and Space reported CLICK ONLY.
- Plant round, full run with the 3.3 scripts: API 54 of 54 and both clock files; page steps 56 of 56 in a tab, with reduced motion and with outside requests blocked; render gate completed in five states with axe-core; contrast 0 below in three runs; targets 16 of 16 and 15 of 15; dead controls 0 with no effect, 0 MOUSE ONLY, 0 CLICK ONLY; launcher self-test passed; design page 8 of 8 diagrams.

**Limits.** The requirement-ledger, evidence-wording, origin and current-look changes are instructions; their effect on what a model builds is measured only by a separate comparison (same briefs, fresh builders, outputs judged without version labels), reported outside this package, and is not claimed here. ChatGPT access to this skill's files varies by session: on 24 Oct 2026 a normal chat could not reach them, while a Work-mode chat started from the installed skill (with the skill selected) ran `direction_board.py --help`. Mode and selection both differed, so neither is known to be the cause, and `--help` says nothing about rendering. The skill therefore checks access in every session. The EXE build is still unrun on Windows.

## Version 3.2.0 (24 Oct 2026)

**Why.** The user answered eight questions on how forge should run:
- fully automated, stopping only for the architecture and the look;
- 16 directions, so the options vary more, with recommendations;
- learning notes pitched at a first-year IT student ("push me but not too crazy");
- the design kept as a rendered page plus repo docs;
- the stack chosen per project;
- three finish lines, from a one-file demo to a Windows EXE with an icon.

**How it was made.**
- An agent built the design pack and `design_page.py`, including the plant app's pack.
- A second agent, a fork of this session, built the eight new directions, `kit-dir.js`, `--recommend` and the live board.
- The tiers, the launcher and the icon tool, `single_file.py` and the SKILL.md rewrite were done here.
- A third agent then built a Demo (a bills splitter for three housemates) by following the packaged 3.2 alone, unattended, and wrote a QA.
- Its findings were fixed before release.

**What changed.**
- **Flow:** two stops, Stop A (architecture) and Stop B (look); assumptions are written down instead of asked; a stop with nobody to answer takes the recommendation.
- **Tiers** (`references/tiers.md`): Demo (one HTML file, packed by `scripts/single_file.py`), Repo (`run.bat`, checks runner, git) and Release (`assets/release/`: launcher, PyInstaller spec, `build_exe.bat`, icon from `scripts/make_icon.py`).
- **Design pack** (`references/design.md`, `assets/design-template.md`, `scripts/design_page.py` with Mermaid 11.17.2 bundled):
  - checkable requirements;
  - two or three options with one recommended;
  - C4-style, ERD, sequence, deployment and state diagrams;
  - decision records, why notes, a glossary and mistakes to watch for.
- **Directions:** eight new ones (Cherry Noir, Aqua Mint, Rose Studio, Terracotta Arch, Arcade Pixel, Navy Gold, Photo Bold, Plum Peach) in `kit3.css`, 13 more font families, a board of 16 with three recommended, and a live switcher that needs no browser to generate.
- **After the Demo test:**
  - a Demo fast path in SKILL.md;
  - `--prep-js` for `dead_controls.py` and `target_size.py`;
  - `--query` for the board;
  - wrapped notes on `board.png`;
  - `--help` in every script;
  - UTF-8 named for every file read and write (Windows safety);
  - `single_file.py --dir` drops other directions' CSS (270 to 214 KB on the example, rendered pixel-identical);
  - `.is-long` for money-length values;
  - Plum Peach's hero and stats no longer colour by position;
  - Warm Pop gets its own composition moves;
  - raw white moved into tokens;
  - the Intl and date-input caveats.

**Results.**

| Measure | Result |
|---|---|
| Demo test build (bills splitter), the builder's run | UI 74 of 74 in a tab and in a sandboxed frame; 18 of 18 persistence steps; offline and reduced motion pass; render gate 15 pass in 7 states; contrast lowest 5.93; targets 13 of 13; dead controls 13 of 13 on the populated copy; a planted rounding fault first passed, then a new step caught it |
| Release tier on Linux (plant app) | Launcher `--self-test` from source passes; a PyInstaller 6.22.3 build loaded the page with every kit file and font and no failed request; SIGTERM stopped the server; the instance lock was removed |
| Design page (plant app) | 8 of 8 diagrams rendered; a broken diagram names its line and exits 1; with no browser, exit 3 with the source shown |
| Contrast on the kit example, all 17 directions | Lowest 4.69 (Coral Editorial); none below 4.5 |

**Limits.**
- The Windows EXE has not been built in a forge session: PyInstaller does not cross-compile.
- Stops A and B were exercised only unattended. No person has answered a stop yet.
- Both test builds were made and judged by agents.
- The Demo tester called the instructions long (about 760 lines before a Demo starts). The fast path is the answer for now; a shorter split is possible later.

## Version 3.1.0 (23 Oct 2026)

**Why.** The user judged v3's output (warm paper, hairlines, quiet type) too plain. He supplied three boards of app designs from Dribbble as the target: a bold signature colour, big rounded cards, huge numerals, illustration and 3D characters, dark neon and pastel palettes, and photo-led layouts. He asked for forge to carry the anti-vibecoded-ui, deslop and showpiece functions itself, and for eight options to be shown on a phone and a desktop before building.

**How it was made.**

- Four directions (Warm Pop, Lime Night, Lilac Soft, Fresh Green) were built here. Two agents built the other four (Coral Editorial, Sky Illustrated, Mono Flood, Candy Pastel) and the clay illustrations.
- The kit, its composition layer and `direction_board.py` were built here, and the board was checked by eye on the grooming example.
- A third agent then built a different app (an indoor plant watering round) by following 3.1 alone, unattended, and wrote a QA of the skill.
- Its findings were fixed, its app was re-pointed at the shared kit as `assets/reference-app-plants/`, and every check was rerun.

**What changed.**

- **Visual bar and directions:** `references/visual.md`; the kit in `assets/visual-kit/`; eight expressive directions plus Ink Paper for dense tools. Each direction has a composition layer, so a page changes shape as well as colour.
- **The options board:** `direction_board.py` renders the populated main screen in every direction at 390 and 1280 px, with one line per direction (`--notes`). It warns about elements that keep a hard-coded colour in every direction.
- **Step 6 rewritten:**
  - the operative answer becomes the signature;
  - the board comes before the other screens;
  - an unattended choice rule, with a tie-break against the subject's cliché;
  - one illustration style or real photography;
  - the tells and foundations from anti-vibecoded-ui;
  - expressive motion limits from showpiece;
  - the transplant, swap, source and delta tests from deslop.
- **Craft test:** question 13, the Dribbble lens.
- **Kit after the test build:**
  - role classes: `.hero-value`, `.slot.is-now` (once per screen), `.slot.is-alert`;
  - shape, outline, focus and hero-size tokens;
  - generic form, choice, state, banner and skeleton pieces;
  - a `[hidden]` rule, and a week strip that takes any number of days;
  - the clay helpers exported as `CLAY`, with a plants pack beside the dog pack;
  - contrast fixes: the warn tags, text dimmed by opacity on signature colours, muted past and closed items, and `.tag-ok`.
- **Scripts:**
  - `contrast_check.py` reads any colour Chromium reports, so `color-mix()` no longer gives false failures;
  - `target_size.py` no longer joins a separate label to its control across other targets;
  - `render_gate.py` R12 ignores decoration that overflows on purpose and visually hidden text;
  - `embed_fonts.py` reads the kit's fonts first;
  - every script answers `--version` and `--help`.

**Results.**

| Measure | Result |
|---|---|
| Test build, the builder's own run | API 54 of 54, plus Brisbane day-boundary steps; UI 56 of 56 in a tab, with reduced motion and with outside requests blocked; render gate exit 0 in five states; dead controls 28 of 28; planted coercion and race both caught |
| The same app rerun from `assets/reference-app-plants/` on the revised kit | The same API and UI results; render gate exit 0 in five states; contrast 0 below in three states; targets 16 of 16 and 15 of 15 (4 false overlaps gone); dead controls 16 of 16 and 12 of 12 |
| Contrast on the kit example, all nine directions | Lowest measured ratio 4.69 to 5.86; none below 4.5 |
| Options board on the plants app, 8 directions | No unchanged-element warnings; overdue rows no longer flood with the signature colour |
| The builder's own craft answers | 12 yes, 1 partly (question 8: green for plants was the median choice, which led to the tie-break) |

**Limits.**

- One test build, by an agent, not a person.
- The Dribbble lens and the craft test are agent judgements, not a design review or a user test.
- The captures are emulated viewports in headless Chromium, not devices.
- No photography was tested, because outside image hosts were blocked.
- The skill files repeat some material (motion, tells, craft questions) across SKILL.md, visual.md and frontend.md. The test builder found them long.

## Version 3.0.0 (23 Oct 2026)

**How it was made.** An agent built a fixed test app by following version 2.0.1 alone: a booking tool for a one-person dog-grooming business, with a Python standard-library server, SQLite and one page. It then wrote a QA of the skill. A second agent mapped what deslop and showpiece could add and reviewed the back-end references for gaps. Version 3 was written from both reports. Then two more passes ran:

- the first agent reviewed v3 against its own QA and re-ran the changed scripts on its build;
- the second agent built the same app by following v3.

**What changed.**

- **Composition from three sources:** the object, the decision and the context. Includes a chrome budget and patterns for time-based views, repeated rows and short choice sets.
- **Identity in two layers:** a fixed house layer and a per-app layer. Includes an identity note, levers that work without web fonts, and font and library loading by delivery surface.
- **Motion budgeted by how often an action is used.**
- **More states:** stale, partial, interrupted, dismissed, permission denied and outside request failed, plus a rule that the tally, the row and the summary agree.
- **Interface copy rules adapted from deslop,** and a string sheet.
- **A twelve-question craft test** that merges showpiece's judging lenses. A failure is fixed by changing the composition, not the palette.
- **Back end:** three kinds of time and money in cents; local-server exposure (Host allow-list, JSON-only writes, no wildcard CORS); migrations with a tested SQLite pattern; a catch-all handler and request ids; version checks, reconciled with retries after a lost answer; server-owned fields; per-object authorisation; an outbox for notifications; budgets for model calls; uploads; test seams kept out of real use; and backups for local apps.
- **Scripts:**
  - `api_check.py`: refuses to run when something already answers on the port; fills saved values into headers and bodies; new operators `$not_contains`, `$absent`, `$gte` and `$lte`; pointer-style keys; `--version`.
  - `delivery_check.py`: `--tab-only`, `--reduced-motion`, `--block-outside`, a `select:` step, failure detail per side, detection of a page that refuses framing, `--version`.
  - New `render_gate.py`: overflow at four widths, zoom, axe if present, keyboard reach, visible focus by pixel comparison, reduced motion, a dark-scheme check that warns when the page ignores it, and screenshots.
- **Reference app:** a "What not to copy" table in its README; its code is otherwise unchanged.
- **Shared scripts:** `delivery_check.py` now differs from interface-architect's copy (the other four shared scripts are unchanged). Copy it across if interface-architect should gain `--tab-only`, `--reduced-motion`, `--block-outside` and `select:`.

**Results of the comparison.** Both builds are in the session that made v3, not in this package.

| Measure | Built with v2 | Built with v3 |
|---|---|---|
| Builder's own API steps | 99 of 99 | 120 of 120, plus 5 of 5 boundary steps |
| Builder's own UI steps | 123 of 123 in a tab | 125 of 125 in a tab, plus 24 extra scenarios (reduced motion, outside requests blocked, a Sydney viewer, a race, a stale edit, a lost answer, a load error) |
| The same 14 black-box probes, written by the author of v3 (foreign Host, `text/plain` write, CORS, malformed JSON, request id, JSON 404, 413, server-owned fields, coercion, closed day, the hours boundary pair, script text, a 20-way race) | 14 of 14 | 14 of 14 |
| Render gate, seeded day view (final version of the gate) | 15 pass, 1 warn: the page ignores the system dark setting, and its dark theme is chosen in the app | 15 of 15 |
| Edit and delete for customers and dogs | No | Yes, with version checks |
| Schema migrations | No (DDL on every request) | Yes |
| Composition | An agenda list with Move and Cancel on every row, a proportional strip and a long time select | The day drawn to scale with free time bookable in place, an "on the table now / next" band showing each dog's handling note, and free start times as buttons |
| Weakest points each builder named | Action noise, an anonymous look close to the reference app, a slow time picker; no edit or delete, no migrations, weak backups | A heavy header before the first appointment, an identity that is "tasteful but thin"; no backup, no breaks or closures |

**How far this can be trusted.**

- It is one task, and the same task the revision was made from.
- The v3 builder had earlier read deslop and showpiece and written the transfer notes, so it was not a clean arm.
- Some v3 guidance (time-based views, short choice sets as buttons, local-server exposure) addresses weaknesses found in the v2 build. That helps this task more than it shows the guidance generalises.
- The comparison of composition is the v3 author's judgement from screenshots, not an independent review.
- Both builds passed every technical probe. The evidence is that v3 changed what got built (composition, edit and delete flows, migrations), not that v2 builds were broken.
- Identity stayed the weakest dimension under both versions.
- No other model or host has followed v3. ChatGPT and Codex use is untested.

## Version 2.0.1 record (kept)

Corrected on 9 Oct 2026: GUI routing was named consistently; sandbox restrictions were scoped to the delivery surface; unknown outcomes, model-reply logging and the retry sketch were rewritten.

Run on 9 Oct 2026: the retry sketch in `backend.md` against a local stub server, 17 of 17 cases, with two planted faults that each failed cases.

Run in the version 2 build session (Linux, Python 3, Chromium):

- the reference app's API: 38 steps, including a 20-way concurrent decrement and a restart, with four broken variants each caught;
- the reference page: 73 steps in a tab and in a `sandbox="allow-scripts"` frame;
- contrast in four themes, and target sizes at 390 and 1280;
- a planted generic dashboard that passes the source, contrast and target scans, with eight of eight controls that do nothing.

Re-run on 23 Oct 2026 with the version 3 scripts: the reference app's 38 API steps pass, and its 73 page steps pass in a tab, with reduced motion, and with outside requests blocked.

## Acceptance cases

1. "Build me a tool to track what's in my workshop storeroom, I want it to remember between sessions." Expect:
   - a brief, a slice with its four parts, and a contract with an error shape;
   - a ledger, and the composition in one sentence;
   - API checks that include refusals and a restart, and a page built against them;
   - a verification table that separates what ran from what didn't.
2. A planted generic dashboard with clean scanner output. Expect it rejected under the craft test, citing dead controls, typed-in numbers and the median question.
3. "Build it with microservices and Kubernetes" for a one-user tool. Expect it built as asked, with each component marked "requested", one line on cost, and no lecture.
4. "This will run at our own address behind single sign-on. Build the intake screen." Expect a real form, no claim that forms are banned, and no widening of allowed origins for a preview.
5. "One of those Framer sites with 3D" for a clinic's booking tool. Expect forge to build the booking tool with no 3D in the working views, and to hand the marketing page to showpiece if it is available.
6. Negative control: "Is this button label clear?" Expect forge not to lead.
