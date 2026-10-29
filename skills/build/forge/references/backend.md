# Back end: ownership, contract, storage, retries, exposure

Worked example for everything here: `assets/reference-app/server.py` and its checks in `api-steps.json`.

## 1. Who owns each rule

Write down every rule the data must obey and give each exactly one owner.

| Rule (from the reference app) | Owner | Enforced where |
|---|---|---|
| An item code is unique | Server | `UNIQUE` in the schema; the server turns the violation into `409 duplicate_sku` |
| A count is a whole number and never below zero | Server | `CHECK (qty >= 0)` in the schema, and one atomic `UPDATE ... WHERE qty + ? >= 0` |
| A name is required, 80 characters at most | Server | `validate_item` |
| Which display theme is on | The page | The page; the server never hears of it |

Consequences:

- The page may repeat a check to save a round trip. It must show the server's answer when they differ, and it must work if its own check is removed.
- A rule enforced only in the page is not enforced. Anyone can call the API directly.
- A rule that spans a read and a write ("only if enough is left") is one statement or one transaction. Reading, deciding in code and then writing is a race. The reference checks include twenty simultaneous decrements of one from ten; exactly ten succeed. A variant that reads, checks and writes separately lets fifteen through.
- Overlapping ranges (bookings, rosters, reservations) are the same race in another shape. In SQLite, hold the overlap check and the insert in one `BEGIN IMMEDIATE` transaction, or store slot rows under `UNIQUE(resource, slot)`. In PostgreSQL use an exclusion constraint on resource and time range (check the extension and version in use). The check: 20 parallel bookings of one slot give one 201 and nineteen 409s, an overlap is refused, and the adjacent slot is accepted.
- Correctness comes from the statement or the transaction. A lock inside one process (the reference app's `LOCK`) does not cover a second process on the same file.
- Decide for each rule whether it is an input bound or an invariant. An invariant goes into a `CHECK` so that every write path obeys it: create, update, adjust, import and scripts. The reference app shows the gap: create caps a count at 1,000,000, but adjust can take it past that.

## 2. The contract

For each operation, write: method and path, request body, success status and body, and the errors it can return. Do this before the code and keep it beside the code.

Decisions to make once, for the whole API:

- **Naming**: plural nouns for collections, an id in the path for one item, verbs only for actions that are not plain create, read, update or delete (`/items/7/adjust`).
- **Identifiers**: opaque to clients. Do not let clients derive meaning from them.
- **Time** comes in three kinds, and each is stored as itself:
  - an *instant* (when something happened): UTC, ISO 8601, `2026-10-23T03:15:00Z`;
  - a *local event* (an appointment, a shift): a local date-time plus an IANA zone, `2026-11-14T09:00` in `Australia/Sydney`, so it stays at 9:00 when daylight-saving rules change;
  - a *date-only* value (a due date, a birthday): `YYYY-MM-DD`, no time, no zone.
  Business-local "today" is computed on the server in the business's zone, never from the browser's clock. Local events are displayed in their own zone, with the zone named when the viewer's zone differs; converting a 9:00 Brisbane appointment to the laptop's zone shows 10:00 to a Sydney viewer in summer, which is wrong for the person keeping the book. Queensland has no daylight saving while New South Wales, Victoria, Tasmania, the ACT and South Australia do, so a Brisbane business and a Sydney client are an hour apart only in summer. In UTC+10, `new Date().toISOString().slice(0, 10)` is yesterday's date before 10 am. Some platforms ship without time-zone data (Python on Windows has no `tzdata` unless installed): test that path, or use a fixed offset where the zone has no daylight saving.
- **Money**: integer minor units (cents) or a decimal type, never a float, with the currency stored beside it. One rounding rule for tax (per line or per invoice), written down and applied in one function. Totals are computed by the server from the lines and never accepted from the client. Tax facts (GST rounding, what a tax invoice must show) are looked up from the tax authority at the time and dated.
- **Lists**: always bounded. Return a page and a way to get the next one. Prefer a cursor (the last seen sort key) to an offset for large or changing sets.
- **Unknown fields**: refuse them. Silently ignoring a misspelt field hides bugs.
- **Versioning**: none until there is a second client you cannot update. Then add fields without removing; break only behind a new path.

## 3. Validation

- Validate at the edge, once, into a clean internal value. Code past that point does not re-check types.
- **No silent coercion.** `"7"` is not `7`, `true` is not `1`, `3.5` is not `3`. Refuse and say why. In Python, `bool` is a subclass of `int`: test for it explicitly.
- Bound everything: string lengths, number ranges, list sizes, total body size.
- Report every invalid field in one answer, keyed by field name, so the page can show each reason in place.
- Validation says the input is well-formed. Rules (uniqueness, permissions, limits against stored state) are checked after, against storage, and produce a conflict or a refusal, not a validation error.
- **Fields the client may set** are listed per operation. Server-owned fields (`id`, owner, role, totals, prices, `created_at`, a status change outside the allowed transitions) are refused with 422 naming the field, not silently ignored and never applied.
- **Normalise before uniqueness**: trim, lower-case an address used to sign in, NFC for names, one phone format. Put `UNIQUE` on the normalised key so "Ann@Example.com " and "ann@example.com" collide.
- **Field reasons read after their label.** The page shows "Email" then the reason, so the reason is a predicate: "is required", "needs an @ and a domain", "already belongs to another customer". The `message` is a whole sentence that ends in what to do.
- Use the framework's validation layer if there is one, at its current version. Its syntax changes between major versions, so check the version in use before writing validators from recall.

## 4. Error semantics

One shape, everywhere:

```json
{"error": {"code": "would_go_negative", "message": "Only 7 in stock. The count cannot go below zero.", "fields": {"delta": "too large"}}}
```

`code` is for programs and never changes. `message` is for people and can be shown as is: write it as product copy, with the domain fact that helps the next move ("Invoice 1042 was paid on 3 October. Record a credit note instead."). `fields` maps input names to reasons. `request_id` matches the `X-Request-Id` header and the server log line.

| Status | Use it for | Client may retry unchanged? |
|---|---|---|
| 400 | Body is not parseable, or not the expected kind of thing | No |
| 401 | Not authenticated | After authenticating |
| 403 | Authenticated, not allowed | No |
| 404 | No such route or item | No |
| 405 | Method not supported on this path | No |
| 409 | A rule against stored state: duplicate, clash, stale version, would break an invariant | No. The user must change something |
| 413 | Body too large | No |
| 422 | Well-formed, but fields are invalid, including a rule about the request alone (outside opening hours, a date in the past, a server-owned field sent) and a referenced id in the body that does not exist (reason on that field) | No |
| 429 | Too many requests | After the time in `Retry-After` |
| 500 | A fault in the server | Only if the operation is safe to repeat |
| 502, 503, 504 | Upstream or capacity trouble | Only if the operation is safe to repeat |

Rules:

- A 5xx answer says nothing was changed, or says what state things are in, whenever the server knows. "Something went wrong" with an unknown outcome is the worst case. Atomic writes remove half-applied states. They do not remove unknown outcomes: a transaction can commit and the answer still be lost on the way back, and the client cannot tell that from a failure. So keep three things: an idempotency key on every write that is not safe to repeat (section 6); an explicit "outcome unknown" state that the client shows and never treats as success or as failure; and a way to reconcile, by re-reading the item or looking the operation up by its key.
- Never return a stack trace, a query, a file path or a secret in an error.
- Log the detail on the server with a request id, and return that id.
- Unknown routes inside the API return the JSON error shape, not an HTML page.
- One outermost handler catches every unexpected exception and answers 500 in the error shape with the request id. It says "nothing was changed" only when the transaction rolled back. Without it, a standard-library server prints a traceback and drops the connection, and the client sees an unknown outcome.
- Accept an incoming `X-Request-Id` or make one, return it on every answer, and log the route template, status, duration and id. Never log a query string or body that carries user text.

## 5. Persistence

- Put constraints in the schema: `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys. Code has bugs; constraints hold anyway. Then translate each violation into the right API error.
- Parameterise every query. Never build SQL by joining strings with input. Escape wildcard characters when user text goes into a pattern match.
- One transaction per operation that must be all or nothing.
- Index what you filter and sort by, and each foreign key. Confirm with the database's query plan on realistic data before adding more.
- Schema changes are numbered migrations kept with the code, applied in order at start inside a transaction, recorded in a version marker, and never edited once applied. In SQLite the marker can be `PRAGMA user_version`:

```python
MIGRATIONS = [
    "CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 80))",
    "ALTER TABLE customer ADD COLUMN phone TEXT",
]

def migrate(db):                     # db = sqlite3.connect(path, isolation_level=None)
    have = db.execute("PRAGMA user_version").fetchone()[0]
    for number, sql in enumerate(MIGRATIONS[have:], start=have + 1):
        db.execute("BEGIN IMMEDIATE")    # the step and its version number commit together
        try:
            db.execute(sql)
            db.execute(f"PRAGMA user_version = {number}")
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
```

  Python's `sqlite3` does not open a transaction before DDL in its default mode, so `with db:` alone would not make a step atomic; explicit `BEGIN` does. Run on 23 Oct 2026 (Python 3, SQLite): a rerun changed nothing, and a failing step rolled back both its DDL and its version number.

  Run DDL once at start, not on every request. The check is an upgrade test: keep a database file made by the previous version, start the new server against it and run the API steps; run the migrations twice and see the version unchanged.
- SQLite specifics, all per connection: `PRAGMA foreign_keys = ON` (off by default, so `REFERENCES` is decoration until it is on), a `busy_timeout`, and WAL mode when more than one process writes. `STRICT` tables stop a text "7" landing in an integer column (check the SQLite version in use).
- A record two sessions can edit carries a `version` column. The update is `UPDATE ... SET ..., version = version + 1 WHERE id = ? AND version = ?`; zero rows changed answers 409 `stale_version` with the current record, and the page shows its Stale state. This meets the unknown-outcome rule in one place: an edit whose answer was lost, retried with the old version, gets `stale_version` for its own change. The client compares the current record with what it sent and treats a match as success; or edits carry an `Idempotency-Key` like creates, and the stored answer is replayed.
- Every person-shaped record has a delete or archive flow, and a delete removes the data everywhere a flow reads it (lists, search, exports, totals). Write the fields kept, the purpose and the retention beside the schema.
- A feature needs all its parts defined: an index on a column the table does not define fails as written. In PostgreSQL a full-text column can be generated from the text columns and then indexed:

```sql
ALTER TABLE notes ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED;
CREATE INDEX notes_search_idx ON notes USING gin (search_vector);
SELECT id, title FROM notes WHERE search_vector @@ plainto_tsquery('english', $1);
```

  This was not run in this package's session. Run it against the database version in use.
- Blanket conventions (soft deletes everywhere, a JSON column on every table, audit columns nobody reads) are cut unless a flow reads them. See the ledger in `architecture.md`.
- Prove persistence by restarting the server in a check, not by reading the code.
- Decide the backup and try one restore. An untested backup is a hope.

## 6. Retries and idempotency

Wrapping every outbound call in a blanket retry repeats non-idempotent writes (a payment, a message, an "add 5") and retries client errors that can never succeed.

What can be repeated safely:

| Operation | Safe to repeat? |
|---|---|
| GET, HEAD, OPTIONS | Yes |
| PUT of a full replacement, DELETE | Yes by HTTP semantics: the end state is the same. Check that the service you call honours this |
| POST that creates or triggers something | Only with an idempotency key the server honours |
| PATCH, or any "change by an amount" | No, unless designed for it (a key, or a version check) |

When to retry at all: a connection failure or timeout before any answer, and 502, 503, 504, and 429 after the stated wait. Never on other 4xx answers. And only a request that is safe to repeat by the table above, or that carries an idempotency key the server honours.

How. This is a sketch with stated limits, not a library:

```python
import datetime, email.utils, random, time

RETRY_STATUS = {429, 502, 503, 504}
REPEATABLE_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


def retry_after_seconds(value, now=None):
    """Seconds to wait, from a Retry-After header in either form: delta-seconds ("120") or an
    HTTP-date ("Fri, 09 Oct 2026 07:30:00 GMT"). None when the header is absent or unreadable."""
    value = (value or "").strip()
    if not value:
        return None
    if value.isascii() and value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return max(0.0, when.timestamp() - (time.time() if now is None else now))


def call_with_retry(send, *, method, idempotency_key=None, attempts=4, base=0.5, cap=8.0,
                    max_wait=30.0, sleep=time.sleep):
    """send() makes one request with its own timeout and returns (status, headers, body), with
    header names in lower case, or raises ConnectionError or TimeoutError.
    Returns (status, headers, body, outcome). outcome is one of:
      "answered"  a final answer arrived: a success, or an error that repeating will not fix
      "refused"   429 to a request that must not be repeated: nothing was done; the caller decides
      "unknown"   a request that must not be repeated got no answer, or 502, 503 or 504. It may
                  or may not have been applied. Reconcile; do not send it again
      "gave_up"   a repeatable request still failing after the last attempt, or told to wait
                  longer than max_wait"""
    repeatable = method.upper() in REPEATABLE_METHODS or bool(idempotency_key)
    for attempt in range(1, attempts + 1):
        try:
            status, headers, body = send()
        except (ConnectionError, TimeoutError):
            status, headers, body = None, {}, None
        if status is not None and status not in RETRY_STATUS:
            return status, headers, body, "answered"
        if not repeatable:
            return status, headers, body, ("refused" if status == 429 else "unknown")
        told = retry_after_seconds(headers.get("retry-after")) if status in (429, 503) else None
        if attempt == attempts or (told is not None and told > max_wait):
            return status, headers, body, "gave_up"
        if told is None:
            wait = random.uniform(0, min(cap, base * 2 ** (attempt - 1)))   # full jitter
        else:
            wait = told + random.uniform(0, base)                          # never sooner than told
        sleep(wait)
```

What it does: bounds the attempts; reads `Retry-After` on 429 and 503 in both forms and never returns sooner than told; stops, and does not sleep, when told to wait longer than `max_wait`; backs off with full jitter up to `cap` when no time is given; and repeats nothing unless the method is repeatable or a key was supplied.

Its limits: it sleeps in the calling thread; it keeps no budget across calls and has no circuit breaker; the HTTP-date form depends on the client's clock; it trusts that the service honours PUT, DELETE and the idempotency key as repeatable, which must be checked per service; it does not retry 500; `send` must attach the same key on every attempt.

Run on 9 Oct 2026 against a local stub server, on Python 3 standard library only: 17 of 17 cases passed, covering both header forms, the wait cap, the attempt bound, a keyed create applied once across a lost answer, and unkeyed writes sent once. Two planted faults (repeating unkeyed writes, ignoring the header) each failed cases. It has not been run against any real service.

- Always set a timeout. A call with no timeout can hang a worker forever.
- An unanswered non-idempotent call has an unknown outcome. Do not repeat it. Read the current state, or tell the user it is unconfirmed. The reference page does this for a count adjustment.

Making a create safe: the client sends an `Idempotency-Key` header, one key per intended create. The server stores the key with a hash of the request and the answer, inside the same transaction as the create. The same key with the same request returns the stored answer. The same key with a different request is refused. Keys expire. This is a widely used convention; an IETF draft has described it, and its status should be checked before citing it as a standard. The reference app implements it, including across a restart.

## 7. Calling outside services

- Credentials come from the environment or a secret store at run time. They are never in code, in the page, in a log line or in an example file.
- Read rate-limit headers when the service provides them and slow down before being refused.
- Verify webhook signatures over the raw body with a constant-time comparison, and reject old timestamps if the scheme includes one.
- Treat everything an outside service returns as input to validate, including its error bodies.
- Names of models, endpoints and parameters go stale quickly. Look them up in the provider's current documentation when writing the call, and put them in configuration.
- A write that must also notify (an email, an SMS, a webhook) uses an **outbox**: in the same transaction as the write, insert a row describing the message; a sender (a loop in the process, or the next request; no queue needed) sends pending rows with an idempotency key and marks each sent or records the failed attempt. The check: point the mail endpoint at a closed port, create the record (201, pending row), restore the endpoint, see exactly one send, still one after a restart.
- Inbound webhooks store each event id under `UNIQUE` in the same transaction as their effect, answer 200 to a repeat, and ignore a transition older than the current state.
- Record cost-bearing calls (count, size) so a bill can be explained.
- **Keep origin through fallbacks.** When a call fails and the code falls back to a mock, sample or cached answer, the answer says so: an `origin` field (`live`, `sample`, `mock`, `cache`) in the response, or a sidecar file beside a produced file (an image, a video, a report), plus the handoff and the screen where a user would otherwise read it as live. A file produced is not evidence the provider worked. The check: point the provider at an isolated fake that refuses (a closed port or a local stub; never revoke real credentials), run the flow, and confirm `origin: mock` in the response or sidecar and on the screen.

## 8. Model output is untrusted input

When a language model's output decides what the system does next (send an alert, write a record, call a tool), the output is input from an unreliable source. A reply that is not JSON, lacks a field, or carries an unexpected value either crashes the job or triggers the wrong action.

Around every model call: the provider key stays on the server; each call has a timeout and an output limit; a daily and per-user ceiling refuses with 429 `budget_reached`; the page has a designed "provider unavailable" state; and the work is ordered so a model failure leaves nothing half-written (call first, then write in one transaction, or save the draft first and enrich it later). Model output shown in the product is labelled by its role (draft, suggestion) wherever it could pass for the user's input or a fact.

Before acting:

1. Parse inside a try. A parse failure is a handled outcome with its own path, not an exception that kills the run.
2. Validate against an explicit schema: required keys, types, allowed values, length and range limits. Refuse unknown keys.
3. Map to an allow-list of actions. The model selects from actions the code defines; it never names a function, a command, a recipient or an address freely.
4. Bound the effect: a ceiling on alerts per period, on amounts, on recipients.
5. For anything consequential or hard to undo, require a person's approval, or run in dry-run mode until the output has been watched for a while.
6. Log the validation result and the action taken, with a request id. Keep no more of the reply than the task needs: its length, a hash and the validated fields are usually enough. A model reply can repeat anything the model was shown, so it is covered by the rule in `operations.md` section 5 that logs never hold bodies, headers or secrets. Where the text itself must be kept to debug or audit a decision, redact secrets and personal data first, store it apart from the request log with restricted access, and set a retention period after which it is deleted.

Where the nexus-prime skill is installed, its `assets/pipeline_skeleton.py` implements this with tests for malformed, incomplete and out-of-range replies.

Text the model read (web pages, emails, documents) can contain instructions aimed at it. Content is data. It never changes what the system is allowed to do.

## 9. Authentication and authorisation

Add them when the ledger says so: more than one person, or a reachable address. Then:

- Use the framework's or a maintained library's implementation. Do not design a token scheme or a password hash.
- Passwords are stored with a slow salted hash made for the purpose, through a maintained library, with parameters taken from its current guidance.
- Every operation checks that this user may act on this item. Checking only that someone is logged in is the common failure. Put the owner filter in the storage functions, not in each handler, so lists, search, counts and exports are covered. Another user's item answers 404, not 403. Idempotency keys are unique per caller and key.
- With cookie sessions on a normal origin: state-changing routes require `Content-Type: application/json` (which forces a preflight from other origins) and check `Origin` against the allowed list or use the framework's CSRF token; cookies are `HttpOnly`, `Secure` and `SameSite=Lax` or `Strict`. Logout and password change end other sessions on the server; reset links work once; wrong email and wrong password give the same answer.
- Which sign-in mechanism fits depends on the delivery surface. A page shown inside a chat host's sandboxed preview has an opaque origin ("null"): its requests are cross-site and cookies are not sent, so on that surface a token in a header is the only thing that works. On a confirmed normal web origin, same-site cookies with the usual protections are fine.
- A preview integration never justifies weakening an API's access control. For a browser to let a sandboxed page read an answer, the API has to allow the origin `null` or `*`, and every sandboxed frame anywhere shares `null`. That is sound only for an API where each request is authorised by a header token and nothing rests on cookies, on the origin or on network position. If the API was reviewed with a narrower boundary, keep it: do not add `null` or `*`, and do not drop a login or ownership check, so that a preview can call it. Point the preview at a separate demonstration back end with throwaway data, or run the page against fixtures and say so.
- `Access-Control-Allow-Origin: *` cannot be combined with credentials; browsers refuse that pairing. An API with credentials lists its origins. The reference server allows any origin because it has no login, holds throwaway data and listens on 127.0.0.1. That setting is for local demonstration only and is not a pattern for a deployed API.
- Rate-limit anything public, and anything that guesses (login, codes).

## 9a. A local server with no login

A tool that runs on the user's own machine and opens in their browser is reachable by every website they visit: a page can send simple POSTs to `127.0.0.1`, and DNS rebinding can make a hostile page's reads same-origin. So, by default:

- bind to `127.0.0.1`, never `0.0.0.0`;
- refuse any request whose `Host` header is not one of the server's own names (`127.0.0.1:PORT`, `localhost:PORT`) with 403 `bad_host`;
- require `Content-Type: application/json` on every write (415 otherwise), which forces a preflight that a foreign origin fails;
- send no `Access-Control-Allow-Origin` unless the brief needs a sandboxed preview to call this server, and then only for a server that holds throwaway data (the reference app's case, which is labelled as a demonstration pattern).

The checks: a write with `Host: evil.example` gets 403 and changes nothing; a write sent as `text/plain` gets 415; the answer to a cross-origin request carries no CORS header.

## 9b. File uploads

Enforce the size limit before reading the body (413). Identify the type by sniffing content against an allow-list, not by the filename (422 for an HTML file named `photo.png`). Store under random names outside the served directory, and serve with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`.

## 10. Checks to write

The minimum for a slice, all in the reference steps file:

- the happy path, and reading the result back;
- each validation failure, with the field named;
- each rule refusal, and that nothing changed afterwards;
- wrong types that a lax parser would coerce;
- malformed and oversized bodies;
- unknown route, wrong method;
- the same create sent twice with a key;
- concurrent writes against a limit, and against a range for anything booked;
- a server-owned field sent by the client, refused and not applied;
- an edit with a stale version, refused with the current record;
- a request that raises inside the server (a fault route that exists only when the server is started with `--faults`): 500 in the error shape with a request id, and no traceback, path or SQL in the body (`$not_contains`);
- for a local server: a foreign `Host` and a `text/plain` write, both refused;
- a restart, then read;
- for anything with dates: the clock set by a test flag (`--now 2026-11-02T09:30+11:00`; the server prints a warning at start and the page shows a banner while it is set), a day boundary in the business zone, and a local event viewed from a zone with daylight saving;
- for a schema that has changed: the upgrade test above.

`scripts/api_check.py` substitutes saved values into paths, headers and bodies, offers `$not_contains`, `$absent`, `$gte` and `$lte`, reads keys that contain dots through a path starting with `/` (`/error/fields/dogs.0.name`), and refuses to run when something already answers on the port, so a restart step cannot pass against a stale server.

Then break the server on purpose, once, and see the checks fail. A check that has never failed has not been shown to check anything.
