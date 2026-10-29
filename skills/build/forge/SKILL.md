---
name: forge
description: "Use first to build a working app, tool, system or API end to end: a design pack with architecture diagrams and learning notes (stop 1), a hardened back end, the main screen in 16 rendered looks to pick from (stop 2), then the app at the right tier: one-file demo, developer repo or Windows EXE. Not for award-grade sites (showpiece), clean-ups of an existing UI (anti-vibecoded-ui), CLIs (interface-architect), serverless save-my-data tools (pocket-app) or store releases (web-to-store)."
metadata:
  revision: "3.4.0"
  revised-from: "Claude 3.4.0-rc1; Codex completed composition precedence with Shaun's approval"
---

# Forge: software that works, looks like its job and reads true

Forge takes "build me X" and returns a thing that runs, with evidence that it runs. The method is one rule applied all the way down: every part carries a flow a user can perform today, and that flow is exercised, including the ways it should fail.

Working is the floor. The bar is three things at once:

- **It works.** Rules hold under bad input, races and restarts, on a system designed before it was coded.
- **It belongs, and it looks the part.** Hierarchy, density, navigation and imagery serve this job, its real content, device and accepted brand. The direction board offers visual choices; it does not require a hero, illustration or decorative layout in every product. A useful operational screen can be quiet; an expressive screen still has to work.
- **It reads true.** Every visible string names a real thing or state, in the user's voice and locale.

## How a build runs

Forge runs on its own from the request to the finished app and stops twice, at the two decisions that are the user's to make.

| Stage | What happens | Stops for the user |
|---|---|---|
| 1. Brief and tier | The brief, the tier (Demo, Repo, Release) and an assumptions list | No |
| 2. First slice | One flow through every layer, hardest part on the path | No |
| 3. Design pack | Requirements, two or three architectures with one recommended, diagrams, decision records, contract, ledger, learning notes, rendered as a design page | **Stop A: architecture** (not for a Demo) |
| 4. Back end | Storage, rules, API and its checks, broken once on purpose | No |
| 5. Main screen and board | The populated main screen in 16 directions, three recommended | **Stop B: look** |
| 6. The rest of the app | Every screen and state in the chosen direction | No |
| 7. Verify | Scripts, then the craft test | No |
| 8. Package and report | The tier's deliverable, the report and what to learn from this build | No |

**Automation rules.**
- Ask nothing outside the two stops. When something is unclear, take the reasonable reading, write it in the assumptions list (in `docs/design.md` and the report) and carry on; the user can correct it at a stop.
- At a stop, send one short message and wait. If nobody can answer (a scheduled run, "just build it", "you pick"), take the recommendation, say so in one line, keep the options on file so the user can switch later, and continue. If the user asked to skip the stops, skip them the same way.
- Deploying, spending money, sending messages, publishing and deleting real data still need the user's go-ahead for that action, whatever the stops say.
- **Teach as you go.** Design notes and the report are written for someone learning software engineering, by default a first-year IT student: a "why this, not that" note on each big decision, new terms explained the first time they appear, and the mistakes beginners and AI tools usually make at each layer, with how this build avoided them. Push a little; never condescend. If the user says they are experienced, keep only the decisions and the mistakes.

**Demo fast path.** For a Demo, steps 1, 5, 6, 7 and 8 apply; steps 2 to 4 (slice acceptance, design pack, contract, back end) do not, and there is no Stop A.
- Requirements are the promises the page makes ("Saved in this browser only", "Undo"), each with a status.
- Checks: `delivery_check.py` on the packed file in a tab, again with `--reduced-motion` and with `--block-outside`; `render_gate.py` per state; `contrast_check.py`; `dead_controls.py` and `target_size.py` with `--prep-js` for a populated state; `ui_candidates.py`. Break the UI steps once on purpose (plant a rounding or state bug and watch a step fail).
- An app that opens empty loads labelled sample data on `?sample=1`, and the board gets `--query sample=1`, so the live board shows it populated.
- With no design page, the report carries the learning notes and a short glossary itself, plus what moving to Repo would add.

## Rules that always hold

- Nothing is described as working unless it ran in this session. Nothing is described as deployed unless it is.
- No placeholder handlers, controls that do nothing, or sample data presented as results. Never invent proof: clients, testimonials, metrics, logos, awards and "trusted by" rows stay empty or labelled as sample.
- The server owns the rules. Client-side checks are a courtesy.
- One error shape across the API. Messages shown to people say what happened and what to do, and never expose internals.
- Only safe operations are retried automatically. Timeouts are always set. An unknown outcome is shown as unknown.
- Secrets never appear in code, the page, logs, commits or examples. Example configuration uses obvious placeholders.
- Queries are parameterised. Text from users or the server goes on the page as text, never as markup.
- Money is stored in integer minor units with its currency. Time is stored by kind (see step 3). Dates, times, numbers and money are formatted with `Intl` in the user's locale, never by hand, except where the user wrote their own forms ("8:00", "60 min"), which win. `Intl` is the starting point, not the last word: en-AU writes "Sept" and "Mon, 2 Mar", so apply the user's forms; a native date input shows the browser's own format, so show the chosen date beside it in the user's form. A local event is shown in its own zone, with the zone named when the viewer's differs.
- The user's spelling and punctuation apply to the interface, server messages and docs. When a mark is ruled out, rewrite the sentence; a lookalike character is the same habit.
- Destructive commands, including in your own shell, are never chained with ordinary ones and are labelled with what they destroy.
- Version-specific facts (packages, model names, prices, platform limits) are looked up when used and dated.
- A clean scan is not a quality verdict. The craft test (step 7) is made by looking at the render.
- Words claim no more than the evidence. A label, KPI name, badge or summary drawn from data takes its wording from what the data is: sample, synthetic, candidate, measured or validated. A score over a synthetic corpus ranks candidates; it never "confirms" anything.
- Origin survives fallbacks. A path that can answer with mock, sample or cached data instead of the live source marks `origin` (live, sample or mock) in the response or a sidecar, in the handoff, and on screen wherever a user would otherwise take it for live. A file produced is not proof the provider worked.
- Each check ends with one RECEIPT line: **completed**, **failed**, **partial** (an applicable check did not run), **runner_error** (the tool could not run) or **usage_error** (`references/results.md`). Report it verbatim. Partial and runner_error are never a pass.
- Where a reference file or an older script copy disagrees with this file, this file wins. Scripts from forge 3.3.2 print their version with `--version`. A script that rejects a flag used here, or prints an older version, is a version mismatch: report that check as runner_error with the mismatch, hold it, and do not work around it by dropping the flag.

## References

Read a reference when the work reaches it, and always before the step that names it. This file carries the essentials of each, so a build never stalls on a reference.

| File | Holds |
|---|---|
| `references/tiers.md` | Demo, Repo and Release: how the tier is chosen, what each delivers, how each runs and reports |
| `references/reference-method.md` | Step 4b: choosing a shipped-product analog by work surface, what transfers and what never does, mechanisms per surface |
| `references/results.md` | The result contract every check script follows: statuses, exit codes per tool, receipts, how to report them |
| `references/design.md` | The design pack and Stop A: requirements, options, diagrams, decision records, the learning layer (why notes, glossary, mistakes), the stop message |
| `references/architecture.md` | Kinds of build, sizing, the component ledger, when to split |
| `references/backend.md` | Ownership of rules, contract, validation, errors, persistence, migrations, time and money, retries and idempotency, local-server exposure, model output as untrusted input, auth, secrets |
| `references/visual.md` | The visual bar, the token contract, the sixteen board directions plus Ink Paper and when each fits, the board and Stop B, bold layout moves, illustration, photography, expressive motion, tells and foundations, the Dribbble lens |
| `references/frontend.md` | Composition from the task, identity and fonts by delivery, motion, states, words on the page, the delivery container, the craft test, checks |
| `references/operations.md` | Containers, deployment, CI, health, backup, cost. Destructive commands are separated and labelled |
| `assets/design-template.md` | The design pack to fill in, with working Mermaid examples |
| `assets/visual-kit/` | Tokens and components for the sixteen board directions plus Ink Paper (`kit.css`, `kit2.css`, `kit3.css`), `kit-dir.js` for the live board, open-licence fonts, the clay illustration core with dog and plant packs, an example screen. Its README says what to copy |
| `assets/release/` | Release tier templates: the desktop launcher, the PyInstaller spec, `build_exe.bat`, pinned build requirements |
| `assets/reference-app-plants/` | "Plant round", the canonical reference build: every back-end rule with its checks, the visual kit on a new subject, its design pack (`docs/`), `run.bat` and a tested `release/` folder. Read it for patterns, not to restyle. One gap is kept on purpose for teaching and named on its README's first line |
| `assets/reference-app/` | "Stock count", a teaching example from an earlier version, not a reference: its README's first line says so and lists what not to copy |

## Not this skill

| The job | Use |
|---|---|
| A marketing, launch or portfolio site meant to look award-grade | showpiece, when available. Forge still builds any back end it needs (contact, booking, waitlist). Forge carries the working core of showpiece, anti-vibecoded-ui and deslop for app screens, so it does not need them present |
| A quick visual clean-up of an existing front end, no build behind it | anti-vibecoded-ui, when available |
| Long prose: landing copy, onboarding sequences, help docs | deslop, when available. Forge applies the interface-copy rules itself |
| Specific interface rules; a command-line or terminal interface | interface-architect |
| A scheduled or always-on pipeline or agent | nexus-prime |
| A lesson or explainer | percept |
| Choose between two stacks, no build | decision-board if present; otherwise answer directly |
| A spreadsheet, document or slide deck | the skill for that file type |
| A one-file tool that keeps the user's entries with no server ("make it save", a tracker in one page) | pocket-app, when available; forge's Demo tier uses its save library when it is present |
| Getting an existing web app into the App Store or Google Play | web-to-store. Forge builds the app first when there is none |
| A security review or threat model on its own | threat-model. Forge applies its back-end security rules itself |
| A contact sheet of an existing page in every state and width | state-gallery |
| Choosing between rendered options outside a build (a palette, a wording) | sample-picker |

## Inputs and tools

Inputs: what the thing is for, in the user's words; anything they fixed (stack, host, codebase, deadline, brand, house theme, tier); where it will be used. If the user chose the stack or architecture, build that and say at Stop A what it costs or risks, in one line. Otherwise the stack is chosen per project at Stop A: the simplest one that does the job, every piece justified in the ledger.

Check what this session has before promising anything: this skill's own files (`scripts/`, `assets/`: list one folder); a shell that can run a server and which runtimes; a browser you can drive (the scripts need Python `playwright` and Chromium); how the result is delivered (file, preview frame, local tab, deployed address); web search for anything version-specific.
- **No browser**: the board runs with `--live-only` (one self-contained file, needing only Python); `design_page.py` writes the page with diagram source and reports partial; render checks are reported as not run, with their commands.
- **No shell**: write the code and the check files, report every check as not run, and give the exact commands.
- **This skill's files cannot be reached** (only this text is loaded): say so first, naming what is missing. Build from the rules here; never write output as if a script ran or a board was rendered. The look stop keeps all sixteen directions: hand over the exact command that makes the board on the user's own machine (`python scripts/direction_board.py page.html board --live-only`, Python only), or continue the build where the package is reachable. Do not imitate the kit's directions from memory and call them the board.

## Procedure

### 1. Brief and tier

Six lines. Tag every fact: **confirmed** (the user said it: quote it), **inferred** (your reading: give the reason) or **preference** (a taste, not a constraint). An explicit statement stays confirmed; an inference is never promoted because it is convenient. These tags open the design pack's requirement ledger:

- **Who** uses it, on what device, how often.
- **The one job**, and **the hardest judgement** in it: what makes the decision hard, what an expert checks first, what goes wrong for newcomers. (Invoicing: what is overdue, and is the GST right? Stock: what is about to run out?)
- **What it keeps**, and for how long. This decides whether there is a back end.
- **Where it is delivered.** A chat preview cannot run a server. A static host cannot keep shared data. A phone cannot reach a server bound to another computer's 127.0.0.1.
- **Conventions**: locale, time zone, 12 or 24 hour, currency format, spelling. Take them from the user; state the ones you inferred.
- **Works means**: one sentence a stranger could check by using it.

Then the **tier** from the request (`references/tiers.md`): **Demo** (one HTML file to try an idea), **Repo** (the default: a project run the way developers run it, with `run.bat`, checks and git) or **Release** (a Windows app with an icon, built by `build_exe.bat`). When two readings fit, take the lower tier and say what moving up adds. Start the assumptions list.

### 2. Name the first slice

Write the full vision down separately and keep it. Then pick one flow that crosses every layer the finished thing will have **and keeps the hardest part on the path**. Rank the claims that could sink the approach (an integration, a latency, a race, working offline) and put the top one inside the slice. A stand-in for the uncertain part cannot prove that part.

With a back end, the slice is accepted only with all four of:

1. a write that succeeds and is shown back from storage, not from the page's memory;
2. a write the server refuses for a rule (a duplicate, a clash, a limit), with the refusal shown to the user;
3. input the server rejects as invalid, with the reason beside the field it concerns;
4. the data still there after the server restarts.

A list that renders sample data is not a slice, and neither is a form that stores to a variable. If an outside integration cannot be reached, build against its documented contract with saved fixtures, label the stub where a reader will see it, and report the live boundary as unresolved. A stub never counts toward a claim that the integration works.

### 3. Design pack, then Stop A

Before code, fill `docs/design.md` from `assets/design-template.md` (rules and examples in `references/design.md`):

- **The requirement ledger** first: every requirement with its tag from the brief (confirmed with the quote, inferred with the reason, preference) and its source. Priority comes from the brief and the user's job, never from what an option can deliver: a requirement the safest design cannot meet keeps its rank and shows as unmet.
- **Requirements and quality attributes**: what "good" means for this app (reliability, privacy, offline, speed, cost), each as something a check can observe, with an id. Every promise the interface will make ("Saved", "Undo", "Works offline", "Private") is a requirement too.
- **Options**: two or three genuinely different architectures (for example a local server with SQLite, a static page with browser storage, a hosted API with a managed database), each with plain-English trade-offs; one recommended, and what would change the pick. No artificial options.
- **Diagrams** in Mermaid, each with a one-line caption saying what to look at: system context and containers (flowcharts with C4 conventions), the data model (`erDiagram`), sequence diagrams for the main action and its failure path, where each part runs, and a `stateDiagram-v2` for anything with a lifecycle.
- **Ownership and the contract** (detail in `references/backend.md`): one owner per rule, almost always the server, with invariants in the schema; the operations, their success answers, errors and client-settable fields (server-owned fields are refused if sent); one error shape with a stable `code`, a `message` written as product copy ("Invoice 1042 was paid on 3 October. Record a credit note instead."), per-field reasons and a request id; time by kind (an instant in UTC with an offset, a local event as local date-time plus IANA zone, a date-only value as `YYYY-MM-DD`); money in integer cents with one rounding rule; which operations are safe to repeat (creates only with an idempotency key).
- **The component ledger**: for every component (framework, database, cache, queue, container, auth, motion or chart library, web font, each service), the flow in scope that needs it and what breaks without it. No line, no component: move it to "add when" with the trigger. A component the user requested reads "requested", and the slice must run through it.
- **Decision records** (short ADRs) and **the learning layer**: a "why this, not that" note per big decision, a glossary of every term on first use (API, schema, migration, idempotency, race condition, transaction), and two or three "mistakes to watch for" per layer.
- **Assumptions** and **open questions**, each with the default forge will take.

Render it: `scripts/design_page.py docs/design.md docs/design.html`, and fix it until it exits 0. Then **Stop A**: one message that opens with any conflict between a confirmed requirement and the recommended option (before the recommendation, never only in a diagram note), then the recommendation and its catch in three lines, each other option in one line, the proposed tier, the stack, the top assumptions, and the design page. Wait for approve, another option, or a change. A Demo skips Stop A: its design is a short note at the end of the report.

### 4. Build the back end

- Write the API checks with the API: refusals and invalid cases, not only the happy path. Pair each refusal with its valid neighbour (the largest allowed value next to the smallest refused). A validator that rejects everything passes every refusal check.
- Rules live in storage where it can enforce them (unique, not null, check, foreign keys switched on). Check-then-change is one atomic statement or one transaction; overlapping ranges are checked inside the same transaction as the insert.
- From the first table: a schema version and numbered migrations; a catch-all handler that answers 500 in the error shape with the request id; a request id on every answer; logs without user text; bounded lists; a version check on records that two sessions can edit (409 `stale_version`, whose body carries the current record, so a client retrying its own lost edit can see the change already landed and treat it as done).
- Test seams stay out of real use: a frozen clock (`--now`) and a fault route (`--faults`) are accepted only with their flags, print a warning at start, and the page shows a visible banner while the clock is frozen.
- A local app that holds real records ships a backup command (SQLite's backup API, to a folder the user chooses) and a restore that has been run once.
- A local server with no login binds to 127.0.0.1, checks the `Host` header against its own names, requires JSON on writes and sends no wildcard CORS, because any website the user visits can reach localhost.
- **Break it once on purpose**: plant a race, a coercion or a lost write, watch a check fail, restore it. A suite that has never failed has not been shown to work.
- Then build the page against the real API. No mock data, no typed-in numbers.

### 4b. Reference analog: structure from a shipped product of the same kind

Before markup, write the structure contract (`assets/design-template.md`): the task, its main object, the device (with its requirement tag) and the first meaningful action. Then choose one primary and at most two supporting references by work surface, platform, density and interaction, not colour or brand: the user's reference pack if they supplied one, otherwise the mechanisms in `references/reference-method.md`. Note each reference's exact state and evidence type (exercised, official demo, marketing still). Take the mechanisms that transfer: hierarchy, navigation, action placement, disclosure, density, feedback. Never copy logos, artwork, marketing frames or whole layouts. Depart where this product's data or workflow differs, and say why. Composition comes from the task and the analog; the look (picked on the board, assigned, or the user's brand) sets colour, type and shape only.

### 5. Main screen, the board, then Stop B

Read `references/visual.md` and `references/frontend.md` (composition, motion, states, words) before writing markup. Design is part of the build, done from the task, not a coat applied after.

**Composition**
- Name the main object (an invoice, a count sheet, a support queue: never "a dashboard"), the main action and how often it is done, and the real content at its worst (the longest name, zero items, the busiest day).
- Find the **operative answer**: the number, status or item the user acts on. Give it the prominence the decision needs, beside the relevant action. A triage queue can lead with comparable rows; a calculator can lead with linked inputs and output; a canvas can lead with the work itself. Do not turn every answer into an oversized coloured hero.
- For an open brief, write three candidate compositions: from **the object** (the thing itself becomes the structure), **the decision** (the hardest judgement made visible where you act) and **the context** (device, place and pace of use). One sentence each, what changes at 390 px, what it gives up. Choose the one that eases the hard judgement and fails the noun swap; write the five-second line a stranger would say.
- Keep the first meaningful task visible at the intended viewport. Recompose for wider screens when it improves the task; a split pane, table, canvas or single reading column are choices, not a mandatory left-hero/right-list template. Check long content and keyboard order after reflow.
- Repeated rows carry one primary action; secondary actions sit behind selection or one menu, visible on focus and on touch. A choice from a short known set (free times, sizes) is shown as buttons, not hidden in a long select.

**The main screen, then the board**
- **Production precedence:** confirmed requirements and accepted brand, then task/data/device and the structure contract, then transferable reference mechanisms, then stylistic options. The expressive grammar in `references/visual.md` is optional when it fits. Do not force flooded colour, large radii, display numerals, imagery or pill navigation onto a utility app. Keep the sixteen-direction board, definitions, order and assets exactly as supplied; adapt the production screen through app-specific overrides when a preview composition conflicts with the task, and record why.
- Build the main screen first, populated with realistic worst-case data, on the kit's token contract and role classes (`assets/visual-kit/`; `assets/reference-app-plants/` shows a whole app built this way), with `kit-dir.js` in the page head. Components read tokens only; raw colours live only in token blocks, except inside drawings, which may keep their subject's colours. The operative value is `.hero-value`; the one current row is `.slot.is-now`; rows needing attention are `.slot.is-alert`; a value that can run long (money, big counts) also takes `.is-long` so it fits its box.
- Rank the sixteen directions for this case with the fits-when and avoid-when columns, choose three to recommend, and write one line per direction on why it fits or does not (`notes.json`), honest about the cliché choice: when the obvious fit is the subject's cliché (green for plants, navy for finance), weigh the second fit and say which you passed over.
- Run `scripts/direction_board.py PAGE OUTDIR --title "..." --recommend a,b,c --notes notes.json`. It writes `board-live.html` (the real page in a phone frame and a desktop frame, a chip per direction, the recommended three first; for a page that is a file, packed in so it opens offline as one file) and, with a browser, `board.png`. Fix every element it reports as unchanged across directions (a hard-coded colour) before showing it. Without a browser, the board is written but not yet viewed: say that, and do not describe how the directions look.
- **Stop B**: send the board with the three recommendations and their reasons first. The user picks one or names a mix; apply a mix by overriding the named rules, never by averaging palettes. Nobody to answer: take the first recommendation, avoiding the direction named in the identity note of the user's previous app (top of its stylesheet) where you have it, say so in one line, and deliver the board so they can switch.
- A brand or house theme the user has fixed wins: map it onto the token names, retain task-appropriate composition, and skip Stop B unless they ask for options. A theme given only in words ("light and warm") is a preference that narrows the three recommendations, not a fixed brand; one with tokens or a style guide is fixed. Light is the house default; a dark direction is chosen for the case or by the user.
- Record the identity note at the top of the stylesheet: direction, signature colour and its job, faces, the bold move, the governing rule from the subject (a timeline drawn to scale, an invoice at A4 proportion, counts set larger than their names).

### 6. Build the rest of the app

**Imagery**
- One illustration style per app, depicting the subject's own things and states: clay 3D or flat SVG built from the subject (the kit's `CLAY` helpers in `illustrations.js`, with its dog and plant packs, show the method), or generated images where the host has image generation, from one fixed prompt vocabulary and labelled where they could be read as real.
- Real photography when the user has it: one ratio per role, cropped on the subject, text on a solid band or measured scrim, never over a busy photo. Without photos, a token tile with the illustration or initials, labelled as where the photo goes.
- Never invented people, customers, reviews or results, in pictures or words.

**Tells and foundations.** Strip the generic tells by composition, not palette: purple-to-blue gradients, gradient text, glass cards, glows and blurred orbs, Tailwind defaults as the design, cards around everything, coloured-border cards, hover lifts on every card, a badge above the headline, three icon boxes, bento grids by default, Inter for everything, sparkle icons, emoji headings, fade-in on scroll, everything animating on load, one idea said as eyebrow, headline and subtitle. A bright flat colour, a big radius or a character is not a tell when it has a job. Then fix the foundations in order: type, spacing, colour, hierarchy, layout, components, copy, states, motion, details (`references/visual.md` section 9).

**Fonts follow delivery.** The kit's faces as files on your own origin; embedded for a single file or a sandboxed preview (`scripts/single_file.py --keep-fonts`, or `scripts/embed_fonts.py`, both reading the kit's fonts with no network); system stacks only when neither is possible, with identity carried by scale, colour and composition. The page works fully when every outside request fails.

**Motion, budgeted by frequency.** Press feedback under 100 ms (a colour step or a 0.98 scale), no bounce. The hero object may enter once on first load, up to 600 ms, ease-out; lists never stagger in. In-place changes 120 to 200 ms. A changed row may tint for up to 600 ms; the end of a rare flow may settle for up to 300 ms, with the character's success scene if there is one. Nothing moves at rest; native scrolling; the floating nav never covers the last item. Reduced motion makes changes instant and keeps the feedback. A motion library needs a ledger line.

**Every state the data can be in**, designed in the same direction (empty and success are where the character earns its place): loading (shaped like what arrives), empty (offers the first action), no results, load error, field error (beside the field, input kept, focus moved), refused (the server's reason), busy (`aria-disabled`, focus kept, second press ignored), unconfirmed (re-read, never assume), stale, partial (say which items failed), success (where the user is looking, announced), destructive confirm (in place, safe choice focused), permission denied or unsupported (the manual path). After every action the tally, the row and any summary agree.

**Words on the page**
- Write the strings before the layout, in the user's own forms where they gave them.
- Headings name the object ("Invoices, October"), not the product or a greeting. Actions are a verb and object that predict the result ("Send invoice", "Add 5", never "Submit"). Statuses name the instance ("3 overdue, $4,180").
- Each fact that changes the next action has one home, beside that action, at body size or larger. Typed input, computed values and suggestions look and read differently. One name per thing across choice, confirmation and receipt.
- Cut evaluation words with no consequence ("seamless", "powerful"), copy that narrates the interface ("Use the options below"), and build vocabulary (slice, stub, fixture). Hedge once, where it is true. Never fill a gap with plausible invented detail; show the gap at the decision it affects.
- Make a **string sheet**: the visible text of every state, read top to bottom as one text. Fix what fails the transplant test (it would fit any app), the swap test (two descriptions could trade places), the source test (every specific traces to the user's material or data) and the delta test (an edit kept every commitment, limit and distinction).

### 7. Verify, then the craft test

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

### 8. Package by tier, then report

Package as the tier says (`references/tiers.md`):
- **Demo**: `scripts/single_file.py page.html demo.html --dir <direction> --keep-fonts "..."`, checked offline. "Double-click demo.html."
- **Repo**: the project layout, `run.bat` and `run.sh`, a checks runner, a pinned dependency file, `.gitignore`, a README in the set order, and git with small commits in the order the work happened. "Double-click run.bat."
- **Release**: everything in Repo plus `release/` from `assets/release/` (launcher, spec, icon from `scripts/make_icon.py`, `build_exe.bat`), with the launcher's `--self-test` run. The EXE is built on Windows by `build_exe.bat`; a session on another platform reports that build as not run, and says that an unsigned EXE meets a SmartScreen warning.

Then the report. Use these words exactly: **written**, **run locally**, **run in a sandboxed frame stand-in**, **run in the delivered surface**, **deployed**. Give each requirement one status: **exercised** (a check ran and showed it), **source-supported** (the code appears to do it; nothing ran) or **not run**. An emulated screen is a viewport size, never a device.

## Failure branches

- **The delivery place cannot run a server.** Say so first. Offer what is true: a Demo that keeps state in the page and says it will not persist; the host's own storage if this session has it; or the full app as files to run elsewhere. Never present typed-in data as a working back end.
- **There is an existing codebase or brand.** Read its structure, conventions and tokens first and follow them. Its tokens fill the kit's token names and win over every direction (skip Stop B unless the user asks for options); its existing architecture is the recommended option at Stop A unless it cannot meet a requirement. Don't introduce a second way of doing something it already does.
- **The user asks for more architecture than the scope needs.** Build it, mark each component "requested", route the slice through it, note the running cost in one line.
- **A model's output will trigger an action.** Treat it as untrusted input: parse, validate against a schema, bound it, act only on an allowed set, with a timeout and a spending ceiling (`references/backend.md`).
- **A check cannot run here.** Report its status (runner_error, or partial for the part that did not run) with the command. Do not describe the result you expect.
- **The page passes the scripts and fails the craft test.** It is not done. Say which question failed and fix the composition or the words.

## Output

1. The brief, six lines, inferences marked; the tier; the assumptions.
2. The design page and what was decided at Stop A.
3. The direction board, the pick (or the reason for an unattended choice) and the identity note.
4. The files, packaged for the tier, and how to run them in one line.
5. Verification: each check, the command, the result and its status word.
6. **What to learn from this build**: the three to five decisions that mattered most and why, the mistakes it avoided, and the terms worth knowing, linked to the design page's glossary.
7. What is not done, not checked, the known limits, and the next flows worth adding.

## Evidence

Version 3 came from a QA build made with version 2, a review of what deslop and showpiece could add, and a second build of the same app. Version 3.1 replaced the quiet default look with the visual kit, the directions and the options board after the user judged v3's output too plain against reference app designs, and a test build of a new app by an agent following 3.1 alone. Version 3.2 set the flow from the user's answers: automated with two stops, tiers from a one-file demo to a Windows EXE, a design pack with diagrams and learning notes, and sixteen directions with three recommended. Version 3.3 came from a review of finished outputs rather than skill text: requirement tags before architecture, words bounded by evidence, origin kept through fallbacks, keyboard checks, one result contract for the checks, a board that opens offline as one file, and a current-look check from the user's rejection of two dated screens. Small samples, not clean comparisons: the record and its limits are in `references/provenance.md` where that file is present.
