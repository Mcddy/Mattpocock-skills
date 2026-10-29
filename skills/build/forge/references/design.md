# The design pack and the architecture stop

Since forge 3.2 a build runs on its own except at two stops. The first is the **architecture stop**: before any code is written, the user sees the system design, the options it was chosen from and the proposed tier, and answers with approve, another option, or a change. This file says what forge writes for that stop (the **design pack**), how it writes it for someone learning, how the stop is run, and how the pack is rendered and kept true.

- Worked example: `assets/reference-app-plants/docs/design.md`, rendered as `design.html` beside it. It was written from the plant app's code after the build, so it also shows what a stop would have caught (the phone, open question 1).
- Template: `assets/design-template.md`. Copy it to `docs/design.md` in the project and fill every section.
- Renderer: `scripts/design_page.py docs/design.md docs/design.html` (section 9).
- Tiers (Demo, Repo, Release) are defined in `references/tiers.md`. This file only says where the proposed tier appears.

The reader assumed throughout is the person in the brief. When the user has said they are learning (the case this file was written for: a first-year Bachelor of IT student who asked to be pushed, not too hard, with advice and reasons), the learning layer in section 7 is part of the pack, not an extra.

## 1. What the stop decides, and when

The stop comes after `SKILL.md` steps 1 to 4 (the brief, the first slice, ownership and the contract in draft, the component ledger) and before step 5 (code).

It decides only what is expensive to change later:

- where the data lives, and who holds it;
- where the code runs, and who can reach it;
- which rules the database owns rather than the code;
- what is kept, for how long, and how it is backed up;
- the tier.

Anything cheap to change stays out: screen layout, names, colours (the direction board settles the look), library choices inside one part.

Budget: the stop message is read in under a minute, and sections 1 to 4 of the pack (the decision, what good means, the options, the system) in about ten. The rest (data, flows, decisions, mistakes, glossary) is reference the user reads at their own pace; it must never hold up the answer. Detail that belongs in code or checks goes there, not in the pack. Scale it to the build: a single-file tool with no back end gets requirements, two options, a context diagram, a lifecycle if it has one, and two or three decision records.

If the user fixed the stack or architecture, build that (`SKILL.md`, Inputs). The stop still happens, with one option, theirs, its consequences, the tier and the open questions. Do not invent rivals to a choice the user already made.

## 2. The pack, section by section

`docs/design.md`, in this order (the template has every heading):

| Section | Holds |
|---|---|
| Title and status | App name; status (proposed; accepted by the user on a date; accepted unattended on a date); proposed tier; links to `design.html` and the code |
| 1. The decision on one screen | The stop message exactly as sent (section 8), then the answer recorded |
| 2. What good means here | The brief in six lines, the quality attributes ranked, the requirements table |
| 3. Options | Each option, a side-by-side table, the pick, what would change the pick |
| 4. The system | Context and container diagrams, with a paragraph each |
| 5. Data | The entity-relationship diagram, the constraints table, migrations, what is kept and for how long |
| 6. The main action and how it fails | Sequence diagrams for the main action, its failure paths and any safe retry; the contract in brief |
| 7. Lifecycle | A state diagram, when something has states |
| 8. Where it runs | The deployment diagram, run, backup and restore commands, what it needs, who can reach it |
| 9. Decisions | Short decision records, each with its "why this, not that" |
| 10. Mistakes to watch for | Two or three per layer |
| 11. Glossary | Every term defined in the pack |
| 12. Open questions | What is undecided or not met, and what each answer would change |

Numbered sections make the stop message and the report easy to point into ("open question 1", "ADR-5").

## 3. Requirements and quality attributes

A **quality attribute** is a property of the whole system (reliability, privacy, speed) rather than a feature. It only helps a decision when it is ranked for this brief and written as something a stranger could check.

Derive them from the brief: "what it keeps" gives reliability and privacy; "where it is delivered" gives reach, offline and cost; "who, how often" gives speed and reach; "works means" and the hardest judgement give the requirement that must never fail.

| Attribute | Ask | Checkable form | Usual check |
|---|---|---|---|
| Reliability | What must never be wrong, doubled or lost? | "20 simultaneous ticks of one plant record one watering"; "still there after a restart"; "a backup restores" | `api_check.py` parallel and restart steps; one restore, run |
| Correct time and money | Whose clock and zone? Which rounding rule? | "13:59:59 UTC is the 23rd in Brisbane, 14:00:00 UTC the 24th"; "GST per invoice, half up" | `--now` steps either side of local midnight; a rounding table |
| Privacy | Who could see this, and should they? How long is it kept? | "no request leaves the computer"; "kept until the owner removes it" | `delivery_check.py --block-outside`; the retention note beside the schema |
| Exposure | Who can reach it at all? | "a foreign `Host` gets 403"; "another user's item answers 404" | API steps |
| Offline | Which offline: no internet, or no server? | "the flow completes with outside requests blocked" | `--block-outside`; for "works with the server off", a service worker and a check with the server stopped |
| Speed | What size is realistic, and what delay would be noticed? | "`GET /api/plants` under 100 ms with 200 plants, median of 50, on the build machine" | a timing loop, with the machine named |
| Cost | What does a month cost at expected use? | "nothing to pay"; "under $X a month, prices looked up on (date)" | the ledger, and prices looked up when written |
| Reach | Which devices, from where? | "opens on the owner's phone at home" | open it there, or mark it not met |
| Maintainability | Who changes it next, and what do they read first? | "one command reruns every check" | run that command |

Rules:

- **Rank them.** The top three drive the pick. Say which attributes do not matter for this brief, and why ("speed: 15 plants, any design is fast enough; still measured").
- **Rewrite vague words.** "Fast", "secure", "scalable", "robust", "user-friendly", "works offline" are not requirements until they say what a person would observe and how it is checked. A requirement nobody could observe is rewritten or dropped.
- **Every requirement row** has an id, the attribute, the observable sentence, the check that shows it, and a status. At the stop the status is "planned"; at the report it becomes exercised, source-supported or not run (`SKILL.md` step 10). Reuse the requirement ids from step 3 so the pack, the checks and the report agree.
- **Promises the interface will make** ("Saved", "Undo", "Works offline", "Private") are requirements too.
- **A requirement the recommended option cannot meet is shown, not dropped**: status "not met", with an open question and the option that would meet it. In the worked example the brief says phone and the local server answers only on 127.0.0.1; the pack says so in the requirements, the stop message, the deployment diagram and open question 1.
- **Every requirement is tagged** before options are written: **confirmed** (the user said it; quote it with its source), **inferred** (a reading; give the reason) or **preference** (a taste, not a constraint). The ledger in the template holds them. An explicit statement is never downgraded to inferred, and an inference is never promoted to confirmed because it suits the design. A brief that says "on my phone in the garden" confirms phone use; a brief that names no device leaves the device inferred.
- **Priority comes from the brief, not the design.** Rank requirements by the user's job, then choose the option. Never rank reach (or any requirement) low because the safest option cannot provide it: that reasons backwards from the implementation. Keep its rank and show it as unmet.
- **A conflict comes first at the stop.** When the recommended option cannot meet a confirmed requirement, the stop message opens with that conflict, before the recommendation.

## 4. Options

Show two or three options that differ in at least one decision from section 1. Each must be:

- **Genuine**: one a competent engineer would choose for some real brief. Write that brief as "fits when". No straw men, no "microservices" option put there to lose, no third option invented to fill a slot. If only two shapes make sense, show two.
- **Buildable here**, at the proposed tier, or marked with what blocks it (credentials, a deploy go-ahead, a paid account).
- **Comparable**: the same screens and rules in each, so only the architecture differs.

Common families, in plain words. Adapt the trade-offs to the brief; do not paste them.

| Family | Good at | Costs you | Fits when |
|---|---|---|---|
| One local server with SQLite | Rules enforced by the database; data stays on one machine; nothing to pay; one file to back up | The computer must be on and the server started; reachable only from that computer unless a login is added | One person or household, one computer, records worth keeping |
| A static page with browser storage (IndexedDB or localStorage) | Nothing to run; can live on a phone; works without a network | Data lives in one browser on one device; rules live in page code a second tab can race; clearing site data loses it; storage can be blocked in a chat preview | A personal tool where losing the data would be annoying, not costly |
| A hosted API with a managed database | Reachable from anywhere; several people and devices; the provider backs up | A login and per-person rules; a monthly bill; credentials and a deploy go-ahead; data with a third party; no internet, no app | More than one person or device, away from home |

Variants (a desktop or mobile app, a function per route on a serverless host, a hosted database with its own sign-in, a spreadsheet as the store) are shown when the brief points at them. They move the same three decisions: where the code runs, who holds the data, who can reach it.

Then:

- **Side by side**: one table, rows are the ranked attributes with their requirement ids, cells are words ("database constraint", "page code only; a second tab can race it"). No ticks, stars or scores: a number invents a precision nobody measured.
- **The pick**: one paragraph tied to the top-ranked attributes, naming what it gives up.
- **What would change the pick**: two to four concrete triggers, each naming the option it would switch to and the decision record it would replace ("the phone must open it at home: A on the home network with a login, replacing ADR-5").
- **Prices** are looked up when written and dated, or written as "look up current prices". Never estimated from memory.

## 5. Diagrams

All diagrams are Mermaid code blocks in `docs/design.md`, so GitHub shows them and the renderer can draw them. Tested with Mermaid 11.17.2 in headless Chromium on 23 Oct 2026:

- **Drew cleanly**: `flowchart` (subgraphs, stadium, cylinder, dashed borders through a colour-free `classDef`, dotted arrows), `erDiagram`, `sequenceDiagram` (`autonumber`, `actor`, `alt`/`else`, `opt`, `par`, notes, `--x` for a lost answer), `stateDiagram-v2` (notes, `<<choice>>`).
- **Avoided: `C4Context` and `C4Container`.** They parse and draw, but on a four-box test the arrow labels overlapped the boxes, the text came out small, the layout could not be steered and most of the canvas was empty; Mermaid lists C4 as experimental. Forge draws C4 views as flowcharts with C4 conventions instead.
- **Avoided: `architecture-beta`.** It drew a clean deployment picture with its built-in icons, but it is beta syntax that GitHub and editor previews may not support yet, and a flowchart says the same with labels on the arrows.

Which diagrams, and when:

| Diagram | Mermaid | Include when | Skip when |
|---|---|---|---|
| System context | `flowchart TB` | Always. For a tool with no outside systems it is short, and "nothing points outside" is itself the point | Never |
| Containers | `flowchart TB` | Two or more running parts: page and server, a worker, a database | A single file with no back end |
| Data model | `erDiagram` | There is a schema | Nothing is stored |
| Main action | `sequenceDiagram` | There is a back end | No back end: describe the flow in two lines instead |
| Failure path | `sequenceDiagram` with `alt`/`else` | There is a back end: a refusal by a rule, an unknown outcome, a fault | No back end |
| Safe retry | `sequenceDiagram` | A create can be retried after a lost answer | No creates |
| Lifecycle | `stateDiagram-v2` | Anything with a status, an undo, an approval, a booking or an order | Nothing changes state |
| Deployment | `flowchart TB` | Anything that runs: machine, process, port, files, backups, and who cannot reach it | Never, for a running app |

**C4 conventions, drawn as flowcharts.** The **C4 model** draws software at four zoom levels: context, containers, components, code. Forge uses the first two.

- Label each box `"<b>Name</b><br/>[Kind: technology]<br/>What it does, in one line"`.
- A person is a stadium `(["..."])`, a running part a box `["..."]`, a data store a cylinder `[("...")]`, the place it runs a `subgraph id["The owner's computer"]`.
- Outside the system: `classDef ext stroke-dasharray: 5 4` and `class backups ext`. Shape and dashes carry meaning, never colour.
- Label every arrow with what flows and how: `-->|"JSON over HTTP, 8 second timeout"|`. Dotted `-.->` for "cannot reach" or "planned".
- Top to bottom (`TB`) for anything longer than three boxes in a row; wide diagrams shrink until their text is small. About nine boxes at most; split a busier view.

**Every diagram:**

- is followed by a caption line in italics that starts "Look at": `*Look at: the page has one arrow, and it goes to the server.*` One sentence: the one thing to notice and why it matters. The renderer turns it into the figure caption and warns when it is missing.
- sets no colours (`fill`, `color`, `stroke` in `style` or `classDef`) and no `%%{init}%%` directive. The renderer draws each diagram twice, light and dark; colours in the source would stay the same in both. It warns when it sees them.
- matches the plan or the code. The ER diagram is written from the real `CREATE TABLE` statements once they exist, the sequence steps from the real routes and error codes.

**Sequence diagrams:** short messages (the renderer wraps long ones between the lifelines); `Note over S: ...` for checks a part makes on its own, rather than an arrow to itself; `autonumber`, so a caption can say "look at step 4"; one `alt` branch per way it can fail; `--x` for an answer that never arrives.

**ER diagrams:** types as declared; PK, FK and UK markers; rules ER cannot show (a `UNIQUE` across two columns, a `CHECK`) go in the attribute's quoted comment and in the constraints table beneath.

**State diagrams:** one per lifecycle. When arrows start crossing, move the exceptions into `note` blocks. Say whether the status is stored or worked out on each read.

Mermaid 11 mistakes that stop a diagram drawing (each was tried on 23 Oct 2026):

- a node named `end` in a flowchart (use `End` or `finish`);
- brackets or braces inside an unquoted label, on a box or an arrow: `a[Server (Python)]` and `-->|SQL (one transaction)|` fail; quote them: `a["Server (Python)"]`, `-->|"SQL (one transaction)"|`. A double quote inside a label is `#quot;`;
- a semicolon inside a sequence message (`A->>B: one; two`): Mermaid reads it as the end of the line;
- a space inside an ER attribute name or type (`TEXT plant name`); comments go in double quotes after the name.

`design_page.py` names the diagram, its heading and its line in `design.md`, with Mermaid's message, so a broken block is found in seconds.

## 6. Decision records

An **ADR** (architecture decision record) is a short note of one decision. Keep three to eight per pack, one per decision from section 1 plus any the user changed at the stop.

```
### ADR-3: "Once per plant per day" is a UNIQUE constraint
- Decision: what was decided, in one or two sentences.
- Context: the situation that forced a decision: the requirement, the risk, the constraint.
- Options: the ones really considered, the chosen one first.
- Consequences: what follows, good and bad, including what it makes harder later.
> Why this, not that. (section 7.1)
```

- Status lives in the pack's status line: proposed; accepted by the user on a date; accepted unattended on a date.
- Numbers never change. A replaced record stays, with "Replaced by ADR-9 on (date): (one line why)", so the reasons survive.
- The tier is recorded in the status line. It gets its own record only when the user changes it at the stop.
- Consequences include the bad ones. A record that lists only benefits is a sales pitch.

## 7. The learning layer

Written for a first-year student who wants to understand, not just receive: they make mistakes, want the reasons, and asked to be pushed a little. The voice is a patient senior engineer reviewing a junior's first design with them.

**Tone:**

- Explain the why before the what. Name the trade-off. Say what is not known.
- Push a little: at most one "Think about it" question or one "Try this" per decision, doable in ten minutes with what they have, never a test they must pass.
- Never condescend. Leave out "simply", "just", "obviously", "easy", "of course", "as you know", exclamation marks and praise. Treat mistakes as normal: say once, where it is true, that most people get this wrong the first time, and how to catch it.
- Plain words first, then the technical term, defined in brackets the first time it appears.
- Name what AI tools commonly get wrong, plainly, when it is relevant. The student works with them and needs to spot it.

| Instead of | Write |
|---|---|
| "Simply add a UNIQUE constraint." | "Put the rule in the database as a UNIQUE constraint, so no code path can skip it." |
| "Obviously the browser clock is wrong." | "The browser gives the date in UTC, which in Brisbane is still yesterday until 10 am, exactly when the watering happens." |
| "This is a race condition, which you should avoid." | "Between the check and the insert another request can make the same check, and both insert. That gap is a race condition." |
| "Great question!" | Answer the question. |

### 7.1 Why this, not that

One blockquote at the end of each decision record, three to five sentences:

1. the tempting alternative, stated fairly;
2. what goes wrong with it here, concretely, with a number from a check where there is one ("removing the constraint made 9 of the 54 API steps fail, the 20-tick race among them");
3. when the alternative would be the right call;
4. optionally, one "Think about it" or "Try this".

Only claim a "Try this" result that was run, or say what to expect is unverified. The worked example's ADR-3 exercise was run while the pack was written.

### 7.2 Glossary

Every technical term is defined the first time it appears in the pack, in bold, with a short plain definition in brackets or straight after it: "a **transaction** (a group of database changes that all happen or none do)". Section 11 collects every defined term in one table, alphabetically, with the same wording.

- The stop message avoids terms that need a definition; the first section of the pack defines the four or five that every later section uses (database, server, API, and the main technology).
- In tables, use plain words and point to where a term is defined, or define it in the cell the first time.
- Definitions are one line, concrete, and use this app where they can ("every watering belongs to a real plant").

Starting definitions, to reuse so packs agree:

| Term | Definition |
|---|---|
| ADR | Architecture decision record: a short note of one decision, its context, the options and the consequences, kept even after it is replaced |
| API | Application programming interface: the fixed set of requests one program can send another, and the answers it can get back |
| Authentication, authorisation | Authentication checks who you are; authorisation checks what you are allowed to do |
| Backup and restore | A copy of the data kept elsewhere, and the tested way to put it back |
| C4 model | A way of drawing software at four zoom levels: context, containers, components, code |
| Constraint | A rule written into the schema that the database enforces on every write, such as `UNIQUE`, `CHECK`, `NOT NULL` or a foreign key |
| Container diagram | The C4 model's second level: each separately running program or data store, what it is built with and how they talk. Not about Docker |
| CORS | Cross-origin resource sharing: headers by which a server tells the browser which other websites may read its answers |
| Cursor | A marker meaning "carry on after this row", used to page through a list without skipping or repeating rows |
| Database | A program that stores data and enforces rules about it |
| Deployment diagram | A picture of where each part runs: which machine, which process, which files |
| Derived value | A value that can be computed from data already stored, so it need not be stored itself |
| DNS rebinding | A hostile website pointing its own name at your computer's address, so the browser treats your local server as part of that site |
| Endpoint, route | One request the API accepts: a method and a path, such as `POST /api/plants` |
| Entity-relationship diagram | A picture of the tables, their columns and how rows in one table point to rows in another |
| Foreign key | A column that must hold the primary key of a row in another table |
| Host header | The part of a request that names the site it was meant for |
| HTTP | The request-and-answer protocol every browser speaks |
| HTTP status code | The number at the start of every answer: 2xx worked, 4xx the request was refused, 5xx the server failed |
| Idempotency | Doing an operation twice has the same effect as doing it once |
| Idempotency key | A random id sent with one intended change, so the server can recognise a repeat and replay its first answer |
| Index | A sorted lookup the database keeps so it can find rows without reading the whole table |
| Instant, local event, date-only | When something happened (UTC); an appointment in a place (local date-time plus a zone); a day with no time (`YYYY-MM-DD`) |
| JSON | A plain-text format for structured data: names, values, lists |
| localhost | The name a computer uses for itself; 127.0.0.1 is its address |
| Migration | A numbered, scripted change to the schema, applied once and in order, never edited afterwards |
| Primary key | The column that identifies one row of a table |
| Quality attribute | A property of the whole system, such as reliability, privacy or speed, rather than a feature |
| Race condition | Two operations overlapping in time, so the result depends on which finishes first |
| Request id | A random id on every request and answer, also written in the server log, so one failure can be traced |
| Requirement | A sentence a stranger could check by using the app |
| Schema | The description of the tables, their columns and the rules on them |
| Sequence diagram | A picture of who sends what to whom, in time order |
| Server | A program that waits for requests and answers them |
| SQL | The language for asking a database to read or change data |
| State diagram | A picture of the states something can be in and the events that move it between them |
| System context diagram | The widest view: the system as one box, its users and the systems it talks to |
| Test seam | A switch that exists only for checks, such as a frozen clock, refused unless its flag is given |
| Timeout | The longest a request may wait for an answer before it is treated as unanswered |
| Trade-off | What you give up to get something else |
| Transaction | A group of database changes that all happen or none do |
| Unknown outcome | A change whose answer never arrived, so it may or may not have happened |
| UTC | Coordinated Universal Time, the reference clock time zones are measured from |
| WAL | Write-ahead logging: SQLite writes new changes to a side file and folds them into the main file later |

### 7.3 Mistakes to watch for

Two or three per layer that this build has, each in three parts: the mistake, how this design avoids it, how the student would notice it in someone else's code or their own. Pick from the catalogue below and make each specific to the build, with its names and numbers. A generic warning teaches nothing.

| Layer | Mistakes beginners and AI tools commonly make |
|---|---|
| Design | Boxes for parts the code never has (a cache, a queue, an auth service); options set up to lose; a design that drifts from the code |
| Page | Working out "today" in the browser (`toISOString().slice(0, 10)` is the UTC date); treating "no answer" as "failed" and sending again; putting user text into the page as HTML; checks only in the page |
| API | Silent coercion (`"7"`, `true`, `3.5` accepted as a number); letting the client set fields the server owns; a different error shape per route; unbounded lists |
| Rules and storage | Check then write (a race); foreign keys left off in SQLite; changing the schema by hand or with `CREATE TABLE IF NOT EXISTS`; `INSERT OR IGNORE` that swallows a refusal the user needed to see |
| Time and money | Keeping only the moment or only the day; showing a date-only value through the viewer's time zone; assuming time-zone data exists; money in floating point; totals accepted from the client |
| Exposure and sign-in | Listening on `0.0.0.0` to reach a phone, with no login; `Access-Control-Allow-Origin: *` added to quiet an error; checking that someone is logged in but not that the item is theirs |
| Running it | Copying a live SQLite file as a backup; a backup never restored; secrets in code or logs; no way to tell it is broken |
| Outside services and model output | Retrying every call, including payments and messages; no timeout; acting on a model's reply without checking it against a schema |

## 8. The stop

### 8.1 The message

Short enough to read on a phone. Plain words; a term that needs a definition stays in the pack.

```
Architecture stop: {App}

Recommended: {letter}, {plain name}. {Why, in at most three lines, tied to the top-ranked
attributes. The one catch, stated plainly.}
Also possible:
  {letter}, {plain name}: {good at, costs you, one line}
  {letter}, {plain name}: {one line}
Tier: {Demo | Repo | Release}, because {one line}.
Design: docs/design.html (with diagrams), docs/design.md (source)

Reply "approve", a letter, or a change in your own words ("approve, but it must open on my phone").
```

- The recommended option's weakness is in the message. If an open question would change the pick, it is the catch.
- About 120 words. Put the same text, word for word, in section 1 of the pack.
- Deliver `design.html` where the user can open it (attached, linked, or shown by the host). With no browser to draw the diagrams, send `design.md` and say the diagrams were not drawn (section 9).

### 8.2 Reading the answer

| The user says | Forge does |
|---|---|
| "approve", "yes", "go", "looks good" | Records "accepted by the user on (date)" in the status line, then builds. No further question |
| A letter or an option's name | Rewrites the pack for that option: the pick, the records it replaces (kept, marked replaced), the diagrams that change, the requirement statuses. Re-renders, says in two lines what changed, then builds. Asks once more only if the switch changes the tier or breaks a stated requirement, naming which |
| A change in their words | Applies it if it fits the brief and records it as a decision. If it breaks a requirement or adds cost, credentials or exposure, states the consequence in two lines and asks once |
| A different tier | Records it and updates the tier line; `references/tiers.md` says what changes |
| A question | Answers it in plain words, then asks for the decision again. The stop stays open |
| Something unclear ("hmm, maybe B?") | Asks one short question that offers the choices |

Silence in a live session is not approval. The stop waits.

### 8.3 When nobody can answer

On a scheduled or unattended run, or when the user said "you pick": go ahead with the recommendation, write "accepted unattended on (date): nobody was available at the architecture stop" in the status line, and choose the tier by the rule in `references/tiers.md`. Put the stop message at the top of the report with one line: "Went ahead with A. To switch, reply B or C." List first any open question that would have changed the pick.

An unattended run never picks an option that needs spending, deploying, credentials or a new account (`SKILL.md`, rules that always hold). If the best option needs one, take the best one that does not, and say so in the report.

## 9. Where the pack lives, how it is drawn, and keeping it true

- **`docs/design.md`** is the source to edit. GitHub draws its Mermaid blocks; VS Code's built-in Markdown preview needs a Mermaid preview extension, and the source reads as text without one.
- **`docs/design.html`** is made by `python3 scripts/design_page.py docs/design.md docs/design.html --title "{App}: design"`. One file with no scripts: the diagrams are inline SVG in light and dark, the fonts are embedded, and a contents list comes from the headings. It reads offline, inside a sandboxed preview, and after being downloaded from a chat, and works at 390 px wide. Wide diagrams scale down to about seven tenths of their drawn size, then scroll sideways inside their own frame.
- **Exit codes.** 0: every diagram drawn. 1: a diagram has a syntax error, named with Mermaid's message; fix it before the stop, never show a stop with a broken diagram. 2: bad arguments. 3: NOT RUN (no Playwright, no Chromium, or no Mermaid); the page is written with each diagram's source instead. Say so in the stop message, and never describe the diagrams as drawn.
- **Look at the page** before the stop, in light and dark, at 390 and 1280 px. A diagram that has to scroll at 1280 px is redrawn top to bottom or split.
- **Keeping it true.** At the report (`SKILL.md` step 10), compare the pack with the code: the ER diagram with the `CREATE TABLE` statements, the contract table with the routes, the deployment diagram with the run command, and each requirement's status with what ran. Re-render. The report says "design pack matches the code as of (date)" or lists the differences. A diagram that no longer matches the code is a defect, like a failing check.
- **No shell** (a chat with no tools): write `docs/design.md`, mark the diagrams NOT RUN, and give the command.

## 10. Before sending the stop

- Every requirement is observable, has a check, and has a status; the vague words are gone.
- Two or three options, each with "fits when"; none invented to fill a slot; prices dated or marked "look up".
- The recommended option's catch is in the message, and every requirement it cannot meet is marked "not met".
- Every diagram drawn (exit 0), captioned, and matching the plan.
- Every term defined at first use and listed in the glossary; one "why this, not that" per decision; the mistakes name this build's parts.
- The user's spelling and punctuation, plain words, no em dashes.
- The page looked at, in light and dark, at 390 and 1280 px.
