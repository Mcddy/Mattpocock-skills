Threat model: data flows, STRIDE at the trust boundaries, one test per mitigation.

# Stock count, if its server were opened to the Wi-Fi so a phone can reach it

Author-run example, 9 Oct 2026: the reply the skill's Output section asks for, written from the files beside it. The request it answers: "Is this app safe to expose on my network so I can use it from my phone at the shelves?"

## The answer

**Not as it stands.** Keep it on loopback, which is how it ships and which was checked today (B1 below). Opened to a shared network, anyone on that network can read, change or wipe the sheet, and so can a web page open in any browser on it. Three things would change the answer: a token on every request, a named origin in place of the wildcard, and a backup that has been restored once. Until those exist and their tests pass, the exposure is not worth the convenience on any network other people also use.

Confidence: high that the open threats are real (four of them were shown by tests that ran). ASSESSMENT, medium confidence, that they are the ones that matter most: the model covers the app's own code, not the router, the host or the phone.

## The four that matter most

| | Threat | Impact | Likelihood | Status and next action |
|---|---|---|---|---|
| T1 | Another device on the same network sends create, adjust and remove requests straight to the API, and they are carried out as if the user had made them. | Counts changed or the sheet removed, found at the next count, nothing to restore from. | Depends on who shares the network. It needs only the address. FACT: V7 sent a read and a write with no credential and got 200 and 201 (9 Oct 2026). | Open, nothing built. Build M7 (a token in a header, checked before any route); V7 is its test and fails today. |
| T2 | A page from another website, open in any browser on the network, sends requests to the API in the background and reads or changes the sheet. | The sheet is read or changed by a site someone merely visited. | Unknown. FACT: V8 found `Access-Control-Allow-Origin: *` on the preflight and on the read. | Open, nothing built. M7 and M8 (the page's own origin only); V7 and V8 are the tests. |
| T7 | The data file is deleted, the disk fails, or T1 happens, and the sheet is gone because the SQLite file is its only copy. | Every shelf counted again. | Unknown. FACT: the app's README lists backups as absent. | Open, nothing built. M13 (a dated copy and one restore tried); V13 is a manual check, not run. |
| T3 | A fault in the server code or in Python's `http.server` lets a device on the network act as the host computer account. | Everything that account can reach, not only the sheet. | Unknown. FACT: the Python documentation says `http.server` is not recommended for production and implements only basic security checks (read 9 Oct 2026). GAP: no fault of this kind was looked for. | Open, nothing built. M9 (its own account, behind a maintained web server); V11 is a manual check, not run. |

## Mitigated and verified (4 of 13 threats, 6 of 13 mitigations)

All run on 9 Oct 2026 against the unmodified app on loopback, by `verify_stock_count.py`. Each also failed against a scratch copy of the app with that control removed.

| Threat | Mitigation, and where | Test and result |
|---|---|---|
| T10 a name written as markup runs as script in the user's page | M3: the page sets every string as text (`index.html`, `el()`) | V3 pass: the name and a search string appeared character for character; 0 elements made; marker undefined |
| T11 SQL fragments or wildcards in search and item fields | M2: parameterised queries, wildcards escaped, schema constraints (`server.py`) | V2 pass: a percent sign found only "50% mix", an underscore only "snake_case tag", a quote and a quoted clause found nothing, "bolt" found its item |
| T12 counts sent as text, true, fractions, negatives, or with unknown fields | M4 and M6 (`as_int`, `validate_item`, `adjust_item`) | V4 pass: 422 four times, 201 for 7, 409 for 7 minus 8 with the count still 7, 0 for 7 minus 7. V6 pass: 422 naming the extra field, 201 without it |
| T13 error answers that describe the host's files | M5: one fixed error shape (`ApiError`, `Handler.fail`) | V5 pass: five malformed or misdirected requests, each the fixed shape, no trace, path or query text |

One open threat is partly mitigated: **T6** (requests or items without limit). M1, the 64 kB body limit, is verified (V1 pass: 413 for 65537 bytes, 201 for 65536). M11, a request limit, is not built (V9 fail: 0 of 60 requests answered 429).

## Built but not verified

None. Every built mitigation in the model has a test that ran and passed.

## Open, with nothing built (8 of 13)

T1, T2, T3, T7 above, and:

- **T4** Another device reads the whole sheet: reads need no credential (V7 fail). Closed by M7.
- **T5** Traffic is plain HTTP, so a device that can observe or redirect Wi-Fi traffic can read or alter it, or answer in place of the server. M10 (HTTPS through a reverse proxy) is not built; V12 not run. Likelihood unknown: it depends on the network's isolation settings, which are out of scope.
- **T8** Nothing records which device changed a count. No mitigation is proposed; with M7 in place the token at least separates the user from everyone else.
- **T9** Request text reaches the terminal log raw. FACT: V10 sent one escape byte in a request path and found it in the log (9 Oct 2026). FACT: the standard library's own `log_message` removes control characters from Python 3.12; `server.py` replaces it with a raw write. M12 is a one-line fix and V10 is its test.

## Accepted or transferred

None. Acceptance is the owner's decision and nobody has made one. Candidates the owner might reasonably accept on a network only they use: T8 (no record of who changed a count) and T5 (plain HTTP). If so, record who accepted and why in the model file.

## Assumptions and out of scope

Modelled: the server bound to the machine's network address, on a home or workshop Wi-Fi that other people's devices also join, one user, no accounts. This is not how the app ships: it binds 127.0.0.1 only.

Out of scope: the router and its password, the host's operating system, exposure to the internet (a forwarded port or a tunnel makes this model wrong), physical access, and language-model cases (the app calls no model).

## What was not established

- GAP: behaviour when actually bound to a network address. The verifications ran on loopback. The behaviours tested do not depend on the address, but nothing was run from a second device.
- GAP: load. No test sent concurrent or sustained traffic.
- GAP: faults in the server or the standard library that would give more than the API offers (T3). Not looked for.
- GAP: whether the Wi-Fi isolates its clients from each other, which decides how likely T1, T4 and T5 are.
- Baseline B1 (not part of the exposed model): the unmodified server answered on 127.0.0.1 and refused a connection on the machine's other address. FACT, 9 Oct 2026.

## Files

- `threat-model.json`: 3 zones, 8 elements, 9 flows (4 across a trust boundary), 13 threats, 13 mitigations, 13 verifications.
- `threat-check-output.txt`: PASS, 0 errors, 4 advisory notes (the four boundary flows are not authenticated, which is T1, T2, T4 and T5).
- `verification-output.txt`: 11 checks, 7 pass, 4 fail, 0 not run.
- `diagram.html`: the drawing. Choose a flow label or an element to read its threats; "Open" filters to the 9.

Revisit when the listening address, the login, the origin list or the storage changes, and rerun the verifications then. The checker flags results older than 90 days.

This is a threat model with tests. It is not a penetration test, not a compliance audit and not a guarantee.
