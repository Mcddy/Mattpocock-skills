# Step 4: build the back end

Read before step 4. Detail for each item is in backend.md.

- Write the API checks with the API: refusals and invalid cases, not only the happy path. Pair each refusal with its valid neighbour (the largest allowed value next to the smallest refused). A validator that rejects everything passes every refusal check.
- Rules live in storage where it can enforce them (unique, not null, check, foreign keys switched on). Check-then-change is one atomic statement or one transaction; overlapping ranges are checked inside the same transaction as the insert.
- From the first table: a schema version and numbered migrations; a catch-all handler that answers 500 in the error shape with the request id; a request id on every answer; logs without user text; bounded lists; a version check on records that two sessions can edit (409 `stale_version`, whose body carries the current record, so a client retrying its own lost edit can see the change already landed and treat it as done).
- Test seams stay out of real use: a frozen clock (`--now`) and a fault route (`--faults`) are accepted only with their flags, print a warning at start, and the page shows a visible banner while the clock is frozen.
- A local app that holds real records ships a backup command (SQLite's backup API, to a folder the user chooses) and a restore that has been run once.
- A local server with no login binds to 127.0.0.1, checks the `Host` header against its own names, requires JSON on writes and sends no wildcard CORS, because any website the user visits can reach localhost.
- **Break it once on purpose**: plant a race, a coercion or a lost write, watch a check fail, restore it. A suite that has never failed has not been shown to work.
- Then build the page against the real API. No mock data, no typed-in numbers.
