---
name: forge
description: "Use first to build a working app, tool, system or API end to end: a design pack with architecture diagrams and learning notes (stop 1), a hardened back end, the main screen in 16 rendered looks to pick from (stop 2), then the app at the right tier: one-file demo, developer repo or Windows EXE. Not for award-grade sites (showpiece), clean-ups of an existing UI (anti-vibecoded-ui), CLIs (interface-architect), serverless save-my-data tools (pocket-app) or store releases (web-to-store)."
metadata:
  revision: "3.4.0"
  revised-from: "Claude 3.4.0-rc1; Codex completed composition precedence with Shaun's approval"
---

# Forge: software that works, looks like its job and reads true

Forge takes "build me X" and returns a thing that runs, with evidence that it runs. Every part carries a flow a user can perform today, and that flow is exercised, including the ways it should fail. The bar is three things at once:

- **It works.** Rules hold under bad input, races and restarts, on a system designed before it was coded.
- **It belongs, and it looks the part.** Hierarchy, density, navigation and imagery serve this job, its real content, device and accepted brand. The direction board offers visual choices; it does not require a hero, illustration or decorative layout in every product. A useful operational screen can be quiet; an expressive screen still has to work.
- **It reads true.** Every visible string names a real thing or state, in the user's voice and locale.

## Use when

Someone asks to build an app, tool, system or API and wants it working, verified and packaged: from a rough idea to a one-file demo, a developer repo or a Windows EXE.

## Not this skill

| The job | Use |
|---|---|
| Award-grade marketing, launch or portfolio site (forge still builds any back end it needs) | showpiece |
| Quick visual clean-up of an existing front end, no build | anti-vibecoded-ui |
| Long prose: landing copy, onboarding, help docs | deslop |
| Specific interface rules; a command-line or terminal interface | interface-architect |
| A scheduled or always-on pipeline or agent | nexus-prime |
| A lesson or explainer | percept |
| Choose between two stacks, no build | decision-board, else answer directly |
| A spreadsheet, document or slide deck | the skill for that file type |
| One-file tool that keeps entries with no server | pocket-app (forge's Demo tier uses its save library when present) |
| Getting an existing web app into the App Store or Google Play | web-to-store |
| A security review or threat model on its own | threat-model |
| A contact sheet of an existing page in every state and width | state-gallery |
| Choosing between rendered options outside a build | sample-picker |

Forge carries the working core of showpiece, anti-vibecoded-ui and deslop for app screens, so it does not need them present.

## Inputs

What the thing is for, in the user's words; anything fixed (stack, host, codebase, deadline, brand, house theme, tier); where it will be used. A stack the user chose is built, with its cost or risk said in one line at Stop A. Otherwise the simplest stack that does the job is chosen at Stop A, every piece justified in the ledger.

Check what the session has before promising anything: this skill's own files, a shell and its runtimes, a browser you can drive (Python `playwright` and Chromium), the delivery surface, web search. Read `references/environment.md` when any is missing; never write output as if a script ran or a board was rendered when it did not.

## Procedure

Forge runs from request to finished app and stops twice, at **Stop A** (architecture, not for a Demo) and **Stop B** (look). Read `references/stages.md` before starting.

- Ask nothing outside the stops. Take the reasonable reading, write it in the assumptions list (in `docs/design.md` and the report) and carry on.
- At a stop, send one short message and wait. If nobody can answer (a scheduled run, "just build it", "you pick"), take the recommendation, say so in one line, keep the options on file and continue.
- Deploying, spending, sending messages, publishing and deleting real data still need the user's go-ahead for that action.
- Teach as you go: a "why this, not that" note per big decision, terms explained on first use, the usual beginner and AI mistakes per layer. Default reader is a first-year IT student; if the user is experienced, keep only decisions and mistakes.

For a Demo only steps 1, 5, 6, 7 and 8 apply: read `references/demo-fast-path.md` first.

1. **Brief and tier.** Six lines (who, one job and its hardest judgement, what it keeps, where delivered, conventions, "works means"), each fact tagged confirmed, inferred or preference. Pick Demo, Repo (default) or Release; when two fit, take the lower. Read `references/step-1-2-brief-slice.md` and `references/tiers.md`.
2. **First slice.** One flow through every layer that keeps the hardest part on the path. With a back end it is accepted only with a persisted write, a refused write, a rejected input and survival of a restart. Same file.
3. **Design pack, then Stop A.** Fill `docs/design.md` from `assets/design-template.md`, render with `scripts/design_page.py`, then stop. Read `references/step-3-design-pack.md` and `references/design.md`.
4. **Back end.** API checks first (refusals paired with valid neighbours), rules in storage, migrations, error shape, test seams out of real use, then break it once on purpose. Read `references/step-4-back-end.md` and `references/backend.md`.
4b. **Reference analog.** Write the structure contract and pick one shipped product of the same kind by work surface. Read `references/step-4b-analog.md` and `references/reference-method.md`.
5. **Main screen, the board, then Stop B.** Build the main screen populated with worst-case data on the kit's tokens, run `scripts/direction_board.py`, recommend three of the sixteen directions. Read `references/step-5-main-screen.md`, `references/visual.md` and `references/frontend.md`.
6. **The rest of the app.** Every screen and state in the chosen direction: imagery, fonts by delivery, budgeted motion, every data state, the string sheet. Read `references/step-6-rest-of-app.md`.
7. **Verify, then the craft test.** Run the check scripts, break the UI steps once on purpose, then answer the 14 craft questions by looking at the render. Any "no" means not done. Read `references/step-7-verify.md` and `references/results.md`.
8. **Package by tier, then report.** Demo: `single_file.py`. Repo: layout, `run.bat`, checks, git. Release: Repo plus `release/` from `assets/release/`. Read `references/step-8-package-report.md`.

If the delivery place cannot run a server, a codebase or brand exists, extra architecture is requested, a model output triggers an action, or a check cannot run, read `references/failure-branches.md`. File and asset index: `references/file-index.md`. Background on how this version came about: `references/evidence.md`.

## Output

1. The brief, six lines, inferences marked; the tier; the assumptions.
2. The design page and what was decided at Stop A.
3. The direction board, the pick (or the reason for an unattended choice) and the identity note.
4. The files, packaged for the tier, and how to run them in one line.
5. Verification: each check, the command, the result and its status word.
6. **What to learn from this build**: the three to five decisions that mattered most and why, the mistakes avoided, and the terms worth knowing, linked to the design page's glossary.
7. What is not done, not checked, the known limits, and the next flows worth adding.

Report with these words exactly: **written**, **run locally**, **run in a sandboxed frame stand-in**, **run in the delivered surface**, **deployed**. Each requirement is **exercised**, **source-supported** or **not run**.

## Rules that always hold

Full wording in `references/rules-detail.md`; read it at the start of a build.

- Nothing is described as working unless it ran in this session, or as deployed unless it is.
- No placeholder handlers, dead controls or sample data presented as results. Never invent proof: clients, testimonials, metrics, logos, awards.
- The server owns the rules. One error shape across the API; messages say what happened and what to do, never internals.
- Only safe operations are retried automatically; timeouts always set; an unknown outcome is shown as unknown.
- Secrets never appear in code, page, logs, commits or examples. Queries are parameterised. User or server text goes on the page as text, never markup.
- Money in integer minor units with currency. Time stored by kind. Dates, times, numbers and money formatted with `Intl` in the user's locale, with the user's own forms winning (en-AU "Sept", "8:00").
- The user's spelling and punctuation apply to the interface, server messages and docs; when a mark is ruled out, rewrite the sentence.
- Destructive commands are never chained with ordinary ones and are labelled with what they destroy.
- Version-specific facts are looked up when used and dated.
- A clean scan is not a quality verdict: the craft test is made by looking at the render.
- Words claim no more than the evidence (sample, synthetic, candidate, measured, validated). Origin (live, sample, mock) survives fallbacks, in the response, the handoff and on screen.
- Each check ends with one RECEIPT line: completed, failed, partial, runner_error or usage_error. Report it verbatim; partial and runner_error are never a pass.
- Where a reference or an older script copy disagrees with this file, this file wins. A script that rejects a flag used here, or prints an older version than 3.3.2 (`--version`), is a version mismatch: report runner_error and do not drop the flag.
