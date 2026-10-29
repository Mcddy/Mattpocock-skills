# Verification patterns: the test that shows a mitigation works

A mitigation with no verification is a hope. For each common mitigation this file gives the test that shows it, the valid neighbour that stops a "refuse everything" server from passing, and what a pass still does not show.

Rules for every verification:

- **Pair the refusal with its valid neighbour.** The smallest refused input sits next to the largest accepted one. A test that only checks refusals passes against a server that is switched off.
- **Check that nothing changed** after a refusal: read the state back.
- **Run it against your own system**, on a scratch copy with throwaway data, on loopback or a test environment. Never against a system you do not own or run.
- **Record what happened.** In the model file: `last_result` (`pass`, `fail`, `not_run`) and `last_run` as a real date. A failing test is recorded as `fail`, and its threat stays open.
- **Break it once.** Remove the mitigation in a scratch copy and watch the test fail. A test that has never failed has not been shown to check anything.
- Use harmless marker strings. A test needs to show that text is treated as text; it never needs a working payload.

Kinds, for the `kind` field: `automated_test` (a named test or a command), `manual_check` (exact steps a person follows), `review` (a named person reads named code against a named rule), `config_scan` (a tool reads configuration). Prefer the first. A review is the weakest: say what was read.

## 1. Authorisation check per object

Mitigation: every operation checks that **this** user may act on **this** item, with the user taken from the session and never from the request.

| Assert | Valid neighbour |
|---|---|
| User B requests user A's item by id: 404 (or 403), and the body carries none of A's data | User A requests the same id: 200 with the item |
| User B updates or deletes A's item: refused, and A's item is unchanged when read back | User B updates their own item: accepted |
| A request with no credential: 401 | The same request with a valid credential: 200 |
| A list route as user B returns only B's items | It returns all of B's items |

Write one such test per route that takes an id, not one for the whole app. The common failure is a route that was added later and missed.

```python
def test_other_users_note_is_not_readable(client_a, client_b):
    note = client_a.post("/notes", json={"text": "private"}).json()
    assert client_a.get("/notes/%d" % note["id"]).status_code == 200      # valid neighbour
    r = client_b.get("/notes/%d" % note["id"])
    assert r.status_code in (403, 404)
    assert "private" not in r.text
```

Not run in this package's session; adapt it to the test client in use. A pass does not show that every route is covered: count the routes that take an id and count the tests.

## 2. Input validation with valid neighbours

Mitigation: input is validated once at the edge, with no silent coercion, and every value is bounded.

| Assert | Valid neighbour |
|---|---|
| A number sent as text (`"7"`), as `true`, as `3.5`: 422 naming the field | `7`: accepted |
| One over the maximum length or range | Exactly the maximum |
| One under the minimum | Exactly the minimum |
| An unknown field: refused, naming it | The same request without it: accepted |
| A body one byte over the size limit: 413, before the body is read | A body exactly at the limit: accepted |
| Text that looks like a query or a pattern (a quote, `%`, `_`) in a search box: matched as plain text, 200 | An ordinary word still finds its item |
| Malformed JSON, or JSON that is not an object: 400 in the fixed error shape | |

After each refusal, read the list back and assert the count has not changed. In this package's build session, tests of this kind were run on loopback against a small reference app and passed, and the same tests failed against a scratch copy with each check removed.

## 3. Output encoding

Mitigation: every string from a user or a server is put on the page as text. The page never assembles markup from data.

Test, in a headless browser against a scratch copy:

1. Store an item whose name is a harmless marker written as markup, for example `<img src=x onerror="window.__marker=1"><b>bold</b>`.
2. Load every view that shows the name: the list, the detail, a confirmation message, a search "no results" message that echoes the query.
3. Assert: the element's text equals the string character for character; the view contains no `img`, `b` or `script` element made from it; `window.__marker` is undefined; no dialog opened.

Valid neighbour: an ordinary name is shown unchanged. A pass covers the views you loaded and no others; list them in `how`.

## 4. Rate limit

Mitigation: a ceiling on requests per client and period, and on anything that costs money or guesses (sign-in, codes, model calls).

| Assert | Valid neighbour |
|---|---|
| The request after the limit: 429 with a `Retry-After` header, and the action did not run | The request at the limit: accepted |
| After the stated wait, the next request is accepted | |
| For a cost-bearing call: the refused request sent nothing to the paid service (count calls on a stub) | |

A pass on one address says nothing about many addresses at once. Say so in the report.

## 5. Secret not in logs

Mitigation: credentials, tokens and personal data are never written to logs, error answers or prompts.

Test: send a request carrying a unique marker string in each place a secret travels (a header, a body field, a query string). Trigger the error path too. Then search the log file, the error answer and, where a model is called, the outbound request body recorded by a stub, for the marker. Assert it is absent.

Valid neighbour: the request id for that request **is** in the log, so the test is reading the right file.

Also check what the log writes for untrusted text. A request path or a user name copied raw into a terminal log can carry control characters. In the build session, one request carrying an escape byte showed that a reference app wrote it raw to its terminal log.

## 6. Model-output validation

Mitigation: the six steps in the forge skill's back-end reference, section 8. The model's reply is parsed in a try, validated against a schema, mapped to an allow-list of actions, bounded in effect, held for approval where it matters, and logged.

Feed the handler these replies from a stub in place of the model and assert each outcome:

| Reply from the stub | Assert |
|---|---|
| Not JSON | Handled as an outcome; the job continues; no action taken |
| Valid JSON, a required key missing | Refused; no action |
| An unknown key | Refused; no action |
| A value outside the allowed list (an action, a recipient, a command the code does not define) | Refused; no action |
| A number outside its range, or text over its length | Refused; no action |
| A well-formed reply choosing an allowed action | Exactly that action runs, once (the valid neighbour) |
| More actions in a period than the ceiling allows | The one after the ceiling is refused |

For instructions hidden in content: give the system a document that contains a marker instruction, such as a sentence telling the reader to reply with the word PLANTED and to call an action the user did not ask for. Assert the action taken is one the user's request allows, and that the forbidden action did not run. This shows the allow-list holds for that document. It does not show the model cannot be steered: assume it can, and rely on the code around it.

## 7. Transport, origin and exposure

| Mitigation | Assert | Valid neighbour |
|---|---|---|
| HTTPS only | An `http://` request is refused or redirected; nothing sensitive is in the redirected request | The `https://` request works with no certificate warning |
| Named origins only | A request with another `Origin` gets no `Access-Control-Allow-Origin` for it, and never `*` together with credentials | The page's own origin is allowed |
| Listening address | A connection to the machine's network address is refused when the service is meant to be local | Loopback answers |
| Least privilege for the process | As the service's account, reading the owner's home folder is refused (manual) | It can read its own data folder |

## 8. Backups

Mitigation: a dated copy on a schedule. The verification is a **restore**, not the existence of a file: copy the latest backup to a scratch folder, start the service on it, and compare a count or a checksum with the day it was taken. An untested backup is recorded as `not_run`.

## 9. When no automated test is possible

Write a `manual_check` with exact steps a person can follow without you, and what they should see. "Review the code" is not a procedure. "Open `routes.py`; for each of the 9 functions that take an `item_id`, confirm the query has `AND owner_id = ?` bound to the session user" is one. Record who did it and when.
