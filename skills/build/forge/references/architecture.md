# Architecture sized to the problem

Architecture is the set of decisions that are expensive to change later. The aim is to make those few decisions well and leave the rest cheap. Size is not the measure. A system with ten services is fine when ten things need to fail, scale or deploy separately, and wrong when one person uses it on one machine.

## 1. What kind of build is this

Decide from the brief, mainly from "what it keeps" and "where it is delivered".

| Kind | Tell | Usual shape | The trap |
|---|---|---|---|
| Script or command-line tool | Run by one person, on demand | One file, arguments, exit codes, no server | Wrapping it in a web app nobody asked for |
| Single-page tool | Works on data the user has in front of them; nothing shared | One HTML file, state in the page | Claiming it "saves" when the delivery frame has no storage |
| Full-stack app | Data must outlive the page or be shared | A page, an API, a database | A page with typed-in data described as full-stack |
| Service or API | Other programs call it | An API with a contract and checks, no page | No error contract; clients guess |
| Pipeline or always-on job | Runs on a schedule or reacts to events | See nexus-prime | A loop with no kill switch or health signal |

Where it is delivered constrains all of these:

| Delivered as | Can run a server | Can keep data | Notes |
|---|---|---|---|
| A page in a chat preview | No | Only if the host offers storage; browser storage may throw | Sandboxed frame; see `frontend.md` section 8 (the delivery container) |
| Files to run on the user's machine | Yes | Yes, in a local file or database | Give exact run commands; ports and paths are theirs |
| A static host | No | No shared data | Needs a separate back end for anything shared |
| A deployed app host | Yes | Yes, with a managed or attached database | Deployment needs the user's go-ahead and credentials |

## 2. Start as one deployable

Unless the user chose otherwise, begin with a single program that serves the page and the API and talks to one database. This is not a prototype shape to be thrown away. Many systems stay this way for their whole life, and it is the easiest shape to test, deploy and reason about.

Keep the inside tidy so a later split is cheap:

- The rules live in functions that do not know about HTTP.
- The HTTP layer translates requests into calls and results into answers, and nothing else.
- Storage access sits behind a small set of functions.

The reference app is small enough to keep these in one file. The separation is still visible: `validate_item` knows nothing of HTTP, and the handler methods do translation only.

## 3. The component ledger

Before building, and again whenever something is added, list each component and justify it by a flow that exists now.

| Component | Flow in scope that needs it | What breaks without it | Verdict |
|---|---|---|---|
| SQLite file | Counts must survive a restart | Data is lost when the process stops | In |
| HTTP API | The page must read and change counts | No way to reach the data | In |
| Idempotency keys on create | A lost answer followed by a retry must not create twice | Duplicate items after a timeout | In |
| User accounts | None: one user on one machine | Nothing | Cut. Add when a second person needs their own view or the address is public |
| Queue and worker | None: every operation finishes in milliseconds | Nothing | Cut. Add when an operation takes longer than a request should wait |
| Cache | None: reads are a single indexed query | Nothing | Cut. Add when a measured read is too slow |
| Container | None: runs with one command on a stock runtime | Nothing | Cut. Add when it is deployed somewhere that takes containers, or setup differs between machines |

Rules for the ledger:

- "We might need it" is not a flow. Cut it and write the trigger.
- "Requested" is a valid reason. The user's choice stands. The slice must then actually pass through the component, so it is real and tested, not decoration.
- Every "in" line implies a check. If nothing would fail when the component is removed, the ledger is wrong or the check is missing.

## 4. When to split or add

Add structure in response to a named pressure, and say which one.

| Pressure you can point to | Response |
|---|---|
| An operation takes longer than a user should wait, or must survive a crash midway | A job table or queue and a worker |
| One part needs a different runtime, or must scale or deploy on its own | A separate service with its own contract |
| The same expensive read is measured as slow | An index first, then a cache with a stated staleness |
| Several consumers must react to one event independently | An event log or bus |
| More than one person, or a public address | Authentication and per-user authorisation |
| Writes from several processes | A database server in place of a single file |
| Text search beyond simple matching | The database's full-text feature, with the column and index it needs both defined |

## 5. Things that look like engineering and are not

Each of these makes a system look serious while adding cost and no behaviour. Remove them unless the ledger can justify them.

- A queue or event bus with one producer and one consumer in the same process.
- Several services that are always deployed together and share one database.
- A container orchestrator for a single process.
- An authentication scaffold when there are no users, or roles nobody is assigned.
- A "settings" or "admin" area whose controls do nothing.
- A dashboard of totals and trends with no data source behind it.
- Abstract layers (repositories, factories, adapters) with one implementation and no test that swaps it.
- Soft deletes, audit columns and flexible JSON columns on every table by default, with no reader for any of them.
- Retry, circuit-breaker and rate-limit wrappers around calls that are local or never fail that way.
- Configuration for environments that do not exist.

The test is the same each time: name the flow, or delete it.

## 6. Choosing the pieces

These are starting points to reason from, not a ranking. Check current versions, limits and prices at the time of use.

**Storage**

| Need | Reasonable choice | Why, and the limit |
|---|---|---|
| One process, one machine, modest data | SQLite | No server to run; real transactions and constraints. One writer at a time; awkward across several app servers |
| Several processes or machines, or growth expected | PostgreSQL or another database server | Concurrent writers, richer types and indexing. Something to run, back up and secure |
| Files or large blobs | Object storage, with metadata in the database | Databases are poor file stores |
| Ephemeral, fast, loss is acceptable | An in-memory store | Not a system of record |
| Similarity search over embeddings | A vector index, often an extension of the main database | Only when the feature exists |

Whatever is chosen: constraints live in the schema, changes to the schema are scripted and repeatable, and there is a stated way to back up and restore.

**Back end**: the language the user or the codebase already uses, with a mainstream web framework, or the standard library when the surface is small. The reference app uses only the standard library so that it runs anywhere and every line is visible. That is a choice for an example, not advice against frameworks.

**Front end**: one HTML file with no build step suits a small tool and anything delivered into a preview frame. A component framework earns its place when there are many views sharing state. Either way, the page is built against the real API.

## 7. Build order

The order is `SKILL.md` steps 1 to 9: brief and slice, contract, ledger, back end with its checks, the page designed against the real API, verification, the craft test by looking, then widening. Operations arrive as flows require them, and performance work only on something measured as slow.

Placing "security hardening" after deployment ships an unvalidated system first. Input validation, parameterised queries and secret handling are properties of the first line of code. What does come later is the work that depends on exposure: authentication when there are users, rate limits when the address is public.

## 8. Non-functional questions, asked when relevant

Ask these of the flows in scope, and write the answer or "not needed yet, because":

- How does the owner find out it is broken? (A health address is a start; someone or something has to look at it.)
- What is lost if the machine dies, and how is it restored? Has a restore been tried?
- What happens when an outside service is slow or down?
- Where do secrets live, and who can read them?
- What does it cost to run for a month at expected use? Look up current prices; do not estimate from recall.
- Could someone else, or the owner in six months, change it safely? What would they read first?
