Teaching example, not a reference: an earlier slice that does not meet current forge rules. "What not to copy" below lists where it differs; copy patterns from `../reference-app-plants/` instead.

# Stock count: teaching slice

A small full-stack app used as the worked example for the forge skill: one page, one API, one SQLite file, Python standard library only. It exists to show a first slice that is complete, and to give the checking scripts something real to run against.

## Run it

```bash
python server.py --port 8765 --db stock.db
# then open http://127.0.0.1:8765/
```

## Check it

From the skill folder, with a throwaway data file:

```bash
python scripts/api_check.py http://127.0.0.1:8765 assets/reference-app/api-steps.json \
  --start "python assets/reference-app/server.py --port 8765 --db /tmp/stock-check.db"

python assets/reference-app/server.py --port 8765 --db /tmp/stock-ui.db &
python scripts/delivery_check.py http://127.0.0.1:8765/ --steps assets/reference-app/ui-steps.txt
python scripts/contrast_check.py http://127.0.0.1:8765/ --click "#display-toggle" --set "html@data-theme=ember"
python scripts/target_size.py --page http://127.0.0.1:8765/ --width 390
python scripts/dead_controls.py http://127.0.0.1:8765/
```

The API steps create and delete data and restart the server. The page steps start and end with an empty sheet. `dead_controls.py` clicks everything. Use a data file you can throw away.

## What it demonstrates

| Point | Where |
|---|---|
| The server owns every rule | `validate_item`, the schema's `UNIQUE` and `CHECK`, the atomic `UPDATE ... WHERE qty + ? >= 0` |
| One error shape | `ApiError` and `Handler.fail` |
| No silent coercion | `as_int` refuses `true`, `3.5` and `"7"` |
| A create that is safe to retry | `Idempotency-Key` handling in `create_item`; the page keeps one key per attempt in `add()` |
| An unsafe write is not retried | `adjust()` in the page: no answer means "unconfirmed", then a re-read |
| Works in a sandboxed frame | No form element, no dialogs, storage optional, cross-origin answers from the API. This is the strict set for a sandboxed or unknown surface; on a confirmed normal web origin a real form is preferred |
| Every state designed | Loading, empty, no results, load error, field errors, rule refusal, busy, confirm, success |
| Focus survives a redraw | `aria-disabled` on busy controls; `data-fk` keys restore focus |
| Text is never markup | `el()` sets `textContent`; nothing is assembled as HTML |
| Customisation that works | Four themes as full token sets, density, reset, storage optional |

## What not to copy

The app predates some of forge's own rules. Agents copy what they read, so these are listed here; in a new build, do what the right-hand column says.

| In this app | In a new build |
|---|---|
| `list_items` returns every row | Bounded lists with a cursor (`backend.md` section 2) |
| No request id; unexpected exceptions drop the connection | A catch-all 500 in the error shape and `X-Request-Id` on every answer (section 4) |
| The log line includes the raw path, so search text is logged | Log the route template, status, duration and id only |
| `CREATE TABLE IF NOT EXISTS` on start, no migrations | Numbered migrations with a version marker (section 5) |
| Create caps a count at 1,000,000 but adjust can exceed it | Invariants in a `CHECK` so every write path obeys them (section 1) |
| One process-wide `LOCK` around every operation | Correctness from the atomic statement or transaction; a lock covers one process only |
| `Access-Control-Allow-Origin: *`, no `Host` check | For a local tool: a `Host` allow-list, JSON-only writes, no wildcard CORS (section 9a). The wildcard here exists only so the sandboxed-frame demonstration can call a server holding throwaway data |
| System font and the Paper theme | An identity chosen from your subject (`frontend.md` section 2). Restyling this app is not building one |

## What it is not

- It has no login. It listens on 127.0.0.1 only. Do not expose it.
- It allows any origin, which is acceptable only because there are no credentials and it is local. That setting is for local demonstration and is not a pattern for a deployed API.
- SQLite with one global lock: one process, modest use. Not measured under load.
- Idempotency keys are kept for a day and cover creates only.
- No backups, no migrations beyond `CREATE TABLE IF NOT EXISTS`.
- It is an example to read. Restyling it is not building an app.
