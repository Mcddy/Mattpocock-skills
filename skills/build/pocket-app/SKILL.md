---
name: pocket-app
description: "Build single-file personal tools with versioned local state, migrations, autosave, undo and atomic import/export, while stating where data lives. Use for saved logs, trackers and tools reopened later. Not for shared data, automatic sync or servers (forge), visual repair (anti-vibecoded-ui), questionnaires (elicitor) or courses (preceptor)."
metadata:
  revision: "1.1.0"
---

# Pocket app: a single-file tool that keeps its data

A small tool delivered as one HTML file has no server, and in a chat preview it may have no storage either. This skill supplies the part that is easy to get wrong: a state library (`assets/pocket-state.js`) that versions the data, saves it wherever saving is possible, says in words where that is, and refuses any import that would damage what is already there. The skill is instructions and tested files. It gives the page no storage the host does not offer, and no way to reach another device.

## Use when

- The user wants a small tool for one person (a log, tracker, list, calculator with saved cases) and expects the entries to be there next time.
- An existing single-file tool loses work on reload, or broke when its fields changed.
- A page needs export, import or backup of what the user has entered.

## Not this skill

| The job | Use |
|---|---|
| Data shared between people, accounts, or anything that needs a server | forge |
| A questionnaire, survey or quiz | elicitor |
| A course that tracks mastery | preceptor |
| A model with adjustable parameters | simforge |
| A research ledger to work through | casefile |
| Focused visual audit or repair of an existing page | anti-vibecoded-ui |
| Ambitious new/open-direction showcase | showpiece |
| Numbered interface-code rules or a command-line interface | interface-architect |
| A page that shows something and keeps nothing | No skill: build the page plainly, without the library |

## Inputs

- What the tool records: the things, their fields, and the one action done most often.
- Roughly how much data: tens, hundreds or thousands of items.
- Where it will be opened: a chat preview, a saved file in a browser, a phone.
- If an earlier version exists: one export or saved copy in the old shape.

Build a first version from the request without asking. Ask only if it is unclear whether more than one person must see the same data, because that decides whether this skill applies at all.

## Tools: discover first

- **A shell with Python 3**, for `scripts/pocket_embed.py`. Without one, paste the two library files into the page whole and unchanged, and say the paste was done by hand and not compared.
- **Python Playwright with Chromium**, for `scripts/test_demo.py`. Without it the script prints `NOT RUN` and exits 3, with a structured `runner-error` receipt, not a pass or partial browser run. Then walk the hand checks in `references/state-contract.md` section 7 if a browser is available to the user, and say plainly that no browser test was run.
- **Node**, for `assets/test_pocket_state.js`. Run it only when `assets/pocket-state.js` or `assets/pocket-ui.js` has been changed, or when the library's behaviour is in doubt in a new environment. An unchanged library does not need it for each tool. Without Node, do not change the library.
- **Host storage.** If the host gives pages a storage object (`window.storage` with asynchronous `get` and `set`), the library uses it first. Nothing needs configuring. Do not promise it: the page reports what it found.
- **interface-architect's check scripts** (contrast, target size, dead controls), if that skill is installed. Name them as a next step only if they are present.

## Procedure

1. **Decide whether one file is the right container.** It is when there is one user, nothing shared, no secrets, and data that stays small (see `references/state-contract.md` section 6). If any of those fails, say so and hand over to forge. If there is nothing to keep, build the page without the library.
2. **Write the data shape first**, as literal JSON for the empty state. Choose a stable app id and a content id, and start at schema 1. Say the shape in the reply.
3. **Write `validate(data)` before any markup.** It returns a list of sentences a person can act on, and an empty list when the data is sound. Types are checked strictly and nothing is coerced. `references/state-contract.md` section 2 lists what to check.
4. **Start from `assets/pocket-demo.html`**, a working checklist. Change it in the order its opening comment gives: identity and empty shape, validator, migrations, the changes (each one a `store.update` with a label), then the markup and `render`. Compose around the record, comparison or next action the task needs. Give deciding information useful prominence and keep actions reachable; a table, form, list or quiet reading surface need not acquire an oversized hero or illustration. Preserve accepted brand and native controls, recompose at narrow widths, and check keyboard order, focus, long content and recovery.
5. **Leave the keeping to the library.** `PocketUI.note` shows where the data lives. `PocketUI.undoButtons` gives undo and redo. `PocketUI.panel` gives export (download and text box together), import (paste or file), and Start again with confirmation in the page. Do not write a second version of any of these.
6. **When the shape changes later**, raise the schema by one and add one numbered migration step, following `references/state-contract.md` section 3. Never edit a step that has shipped. Import a saved copy in the old shape and confirm it arrives intact.
7. **Keep display choices in their own store** (theme, row spacing, text size), as the starter page does, so that Start again does not reset them and a data import does not carry them.
8. **Check it.**
   - `python scripts/pocket_embed.py PAGE.html` shows the pasted library is the released file, and notes any form element, dialog call or outside address.
   - `python scripts/test_demo.py PAGE.html --change "fill:#field=Text" --change "click:#add" --proof "#list=Text"` requests twelve contract tests in a tab and nine in a sandboxed frame (or the explicit `--only` subset), recording which actually ran. Infrastructure errors are distinct from failed assertions. Add `--panel STEP` if the export panel sits behind a tab or button.
   - Look at the page at a phone width and a desktop width, with real content in it, before calling it done.
9. **Hand over the file and say where the data lives**, in the page's own words, and what that means for this user (see Output).

For a substantial screen, record task, content object, device/delivery, first meaningful action and accepted direction before decoration. Reference examples inform hierarchy, density and feedback, not a universal style. A static capture proves only its visible state. Preserve ordinary keyboard access and honest state copy. Synthetic/candidate/measured/validated labels follow evidence; provider mock/sample origin must remain in metadata or a sidecar, handoff and the decision surface where it could be mistaken for live data.

See `references/state-contract.md` section 8 for script status/exit compatibility and semantic receipts. `pocket_embed.py` checks released-library bindings; it does not prove save/reload behaviour. `test_demo.py` checks named state observations on its tested surface; a stub or local frame does not verify a real host. `--planted --only` is rejected rather than silently changing scope.

## Failure branches

- **No shell, no browser, or no Node.** Follow the fallbacks above. Each one ends with saying what was done by hand and what was not run.
- **The request is too small.** A page with nothing to keep, or a question about how browser storage works, gets a plain answer or a plain page. Do not add a schema and an export panel to a tip calculator.
- **The data is shared, large or sensitive.** More than one person, more than one device at once, several megabytes, or secrets: this is forge's job. Say why in one sentence.
- **The user asks for sync between devices.** A single file cannot do it. The working route is export on one device and import on the other; the import replaces what is there and can be undone. Automatic sync needs a server.
- **The host offers its own storage.** Prefer it, through the library's chain. Do not write host-specific storage calls into the page.
- **The preview keeps nothing.** That is normal in a sandboxed frame. The page says `Not saved: this page cannot store data here. Export to keep your work`. Repeat that in the reply and give the two routes: export before closing, or save the file and open it in a browser.
- **An import is refused.** Give the reason the page gave (`references/state-contract.md` section 4). Do not advise editing the file to force it through, and do not loosen the validator to accept it.
- **An old saved copy no longer loads after a change.** The schema was not raised, or a step is missing. Fix it with a migration; do not ask the user to re-enter data.
- **The request is a questionnaire, a course, a simulation or an interface review.** Hand over to the skill in the table above.
- **This skill's own ways of going wrong:** editing the pasted library inside a page (the embed check then fails; change the file in `assets/` and re-run its tests instead); a validator that repairs data silently; reusing an app id for a different tool; claiming the data is safe when the page said it is not saved.

## Output

The first line names the method: "Single-file tool on the pocket-app state library." Then:

- The file, and what it records.
- The data shape and its schema number. If the shape changed, the migration that was added.
- Where the data lives, as the page states it, and what that means: which browser, which device, and that the exported file is the copy that lasts.
- A checks table: each check, whether it was run, and the result or `NOT RUN`.
- What it does not do: no sync, no sharing, no recovery if the browser's data is cleared and no export was taken.

## Rules that always hold

- A failed import, a refused update and a failed migration change nothing.
- The schema starts at 1 and rises by one per change of shape, each with its own step.
- The page says where the data lives, and the reply never claims more than the page does.
- Export is a download and a text box together. Destructive actions are confirmed in the page and can be undone.
- No form element, no `alert`, `confirm` or `prompt`, no outside requests, text set with `textContent`.
- The pasted library is the released file, unchanged.
- Nothing is called tested unless it was run in this session. A sandboxed frame on this machine is a stand-in for a chat preview, never the preview itself.

## Historical author-reported checks

The following totals describe the original authoring session, not newly run checks for revision 1.1.0. Current script/stub receipts and installation readback are separate. Historical reports:

- `node assets/test_pocket_state.js`: 38 of 38 tests passed, including 28 refused imports that each left the same object, the same bytes, the same history and no storage write. With `--planted`, 5 of 5 broken copies were caught by their named tests (a failed import that partly applies, migration steps out of order, a storage exception that escapes, a second tab that silently overwrites, a released file that differs from its recorded hash).
- Large state under Node on one machine: 5,000 items (571,235 bytes) exported and imported intact. Across five runs: one update 18 to 228 ms, export 17 to 108 ms, import with validation 12 to 134 ms, undo under 1 ms. The spread is load on a shared machine; read these as an order of magnitude.
- `scripts/test_demo.py` on the starter page at 390 by 844 and 1280 by 800: 21 of 21 at each size (12 tests in a tab, 9 in a `sandbox="allow-scripts"` frame, where storage was refused and the page said so). The same on a reading log built by this procedure: 21 of 21 at each size. With `--planted`, 5 of 5 broken copies were caught (a note that always claims the data is saved, an empty export box, a refused import that still applies, a panel that overflows a narrow window, an unhandled storage error).
- `scripts/pocket_embed.py`: identical copies pass; a copy with one word changed and a block with no end marker each exit 1; an unreadable page, an unknown option, a missing value and `--out` naming the input each exit 2.
- With interface-architect's scripts, on the starter page and the reading log: a 55-step journey passed in a tab and in the frame at both sizes; contrast in all four themes with an error showing, none of 24 and 28 measured text elements below AA and a lowest ratio of 6.29; target sizes at 390 wide, all 12 and 15 targets 24 by 24 or larger, and no control under 44 by 44 on the empty reading log; no dead controls among 7 and 6 tried. Screenshots at 390 and 1280 wide were looked at.

Not tested: any model following this skill other than the session that wrote it; any real host's preview; a real host storage object (the tests use a fake with the same shape); any browser other than the Chromium that Playwright launches; a screen reader; real quota limits on a phone.

## Acceptance cases

The historical teaching examples and negative controls travel with this package for inspection. Their presence is not new runtime validation; the examples README labels their status.

1. "Make me a tool to log the books I read, and it has to remember them." Expect: the shape and schema 1 stated, a validator, the unchanged library, export as download and text together, undo for removal, a sentence about where the data lives, and a checks table with real results or `NOT RUN`.
2. An export in an old shape, with "add shelves and dates without losing my books". Expect: schema raised by one, one numbered step that invents no values, and the old file imported with the count reported.
3. "Can it sync between my phone and laptop?" Expect: no, said at once; export and import as the working route; a server-backed build named as a different job.
4. Negative control: "an inventory app my three staff can all update". Expect: forge leads, and no single-file tool is built as if it met the request.
