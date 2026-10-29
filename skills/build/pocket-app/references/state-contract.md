# The state contract, and how the library meets it

Read this when writing the state shape, a validator or a migration, when an import is refused and the reason has to be explained, or when no browser is available and the checks must be walked by hand. The full API is in the comment at the top of `assets/pocket-state.js`; the panel helpers are described at the top of `assets/pocket-ui.js`.

## 1. What a saved copy is

One JSON object, the envelope:

```json
{"app": "reading-log", "schema": 2, "content_id": "reading-log@1",
 "saved_at": "2026-10-09T02:00:00.000Z", "data": {"books": [], "nextId": 1}}
```

| Field | Rule |
|---|---|
| `app` | Stable id of the tool. Never changes once a copy has been handed over. A file from another app is refused |
| `schema` | Whole number, starts at 1, rises by exactly one each time the shape of `data` changes |
| `content_id` | What the state belongs to, with its version. For a general tool, the tool's own name and `@1`. For a tool built around supplied content (a ledger, a course, a set of questions), the id of that content, so that work saved against one set is not silently loaded over another |
| `saved_at` | ISO 8601, UTC, written by the library |
| `data` | Plain JSON only: objects, lists, text, finite numbers, true, false, null. No dates as objects, no undefined, no NaN |

The same envelope is what autosave stores, what export hands over and what import reads. There is one format, so a storage copy pasted into the import box works.

## 2. Shape first, then the validator

Write the empty shape as literal JSON before any markup. Then write `validate(data)`, which returns a list of sentences and an empty list when the data is sound. It is the only gate: `create` refuses an initial value that fails it, `update` refuses a change that fails it, and imports and migrations that fail it change nothing.

- Check types strictly. `"7"` is not `7`, `true` is not `1`. A rating is `null` or a whole number in range, never an empty string.
- Check every cross-reference and every id for uniqueness. Keep a `nextId` counter in the data, and check it is above every id in use, so that an id is never reused after a deletion.
- Bound every free-text field. Dates are text, written `YYYY-MM-DD`, and must be real calendar dates.
- Word each problem so a person can act on it: `book 3 has a rating that is neither blank nor a whole number from 1 to 5`.
- Never repair inside `validate`. Repair belongs in a migration, where it is deliberate and numbered.

## 3. Changing the shape: migrations

When the shape changes, `schema` goes up by one and one step is added. Step `N` takes schema `N` data and returns schema `N + 1` data. Steps run in order, each result must be plain data, and the final result must pass `validate`. A file with no step for its schema is refused by name.

```js
var MIGRATIONS = {
  // Schema 1 kept {title, done}. Schema 2 has ids, a status and a nextId counter.
  1: function (d) {
    if (!d || !Array.isArray(d.items)) throw new Error('the schema 1 file has no list of items');
    return {
      items: d.items.map(function (it, i) {
        it = it || {};
        return {id: i + 1, title: it.title, status: it.done === true ? 'done' : 'open'};
      }),
      nextId: d.items.length + 1
    };
  }
};
var store = PocketState.create({app: 'checklist', schema: 2, contentId: 'checklist@1',
  initial: {items: [], nextId: 1}, migrations: MIGRATIONS, validate: validate});
```

Rules for steps:

1. Carry values across as they are. Do not invent a value the old file did not hold; use `null` or an empty string and let the validator decide whether that is allowed.
2. A step that cannot understand its input throws, with a sentence. The import is then refused and nothing changes.
3. Never edit a step after a copy of the tool has been handed over. A mistake in step 1 is fixed by step 2.
4. Keep one export from each old schema as a test file, and import it after every change of shape.
5. A stored copy written by an older schema is migrated on load, and the copy from before the migration is kept in storage under a separate backup key (`store.ready` reports it as `backupKey`). A stored copy from a newer schema is never overwritten: saving stops and the page says so.

## 4. Import: the order of checks and the reasons given

`store.importText(text)` checks in this order and stops at the first failure. `store.inspect(text)` runs the same checks without applying anything. The state object, its serialised bytes, the undo history and the stored copy are all untouched by a refusal.

| Order | Reason code | When | The message begins |
|---|---|---|---|
| 1 | `empty` | nothing but white space | Nothing to import: the box is empty |
| 2 | `not_json` | does not parse | This is not a saved file: it could not be read as JSON |
| 3 | `not_envelope` | not an object, or `app`, `schema` or `data` missing | This is JSON, but it is not a file saved by this tool |
| 4 | `wrong_app` | `app` differs | This file was saved by "other". This page is "this" and cannot read it |
| 5 | `bad_schema` | `schema` is not a whole number of 1 or more (`"2"` and `2.5` are refused) | The schema in this file must be a whole number |
| 6 | `newer_schema` | above this page's schema | This file uses schema 3, which is newer than this page (schema 2) |
| 7 | `no_migration`, `migration_failed`, `migration_invalid` | an older file whose steps are missing, throw, or produce data that does not fit | Bringing this file from schema 1 to schema 2 ... |
| 8 | `invalid_data` | the data fails `validate` | The data in this file does not fit this tool, followed by the problems |
| 9 | `content_mismatch` | `content_id` differs | This file belongs to "x" |

A content mismatch is the one refusal the user can overrule. The panel shows both ids and asks in the page; `Import it anyway` calls `importText` again with `allowContentMismatch: true`. A good import is one undo step.

## 5. Where the data lives, in the words the page uses

On load the library tries, in order, a host storage object (`window.storage` with asynchronous `get` and `set`), then `localStorage`, then memory. Every access is inside try and catch. `store.persistence().text` is the sentence to show, and `PocketUI.note` keeps it current:

| Mode | Sentence | What to tell the user |
|---|---|---|
| host | Saved in this app's storage | Kept by the host that is showing the page. Its lifetime is the host's to state, not this skill's |
| local | Saved in this browser | Kept by this browser, for this file at this address. Another browser, another device, a private window or cleared site data will not have it |
| memory | Not saved: this page cannot store data here. Export to keep your work | Typical of a sandboxed chat preview. The work lasts until the page is closed or reloaded |

A layer that fails later (a full quota, storage withdrawn) is left for the next one down, a `persistence` event fires, the sentence changes and the layer is tried again on later saves. Two further sentences appear when saving has stopped on purpose: another tab saved different data (`store.conflict()`, settled with `resolveConflict('mine' | 'theirs')`), or the stored copy could not be read (`store.recovery()`, left as it is until `discardStored()`). The panel draws both with their choices.

None of this is synchronisation. Two devices never see each other's data. The honest route between devices is export on one and import on the other; anything automatic needs a server, which is a different build.

## 6. Size

The default warning level is 1,000,000 bytes of envelope (`warnBytes`); above it `store.size().over` is true and the panel says so. Browser storage commonly allows a few megabytes per origin and refuses beyond that, at which point the library falls back to memory and says so. Measured in the authoring session with 5,000 items (571,235 bytes), under Node on one shared machine, across five runs: one update 18 to 228 ms, export 17 to 108 ms, import with validation 12 to 134 ms, undo under 1 ms. A text box holding several hundred thousand characters is slow for the browser to lay out (0.2 to 0.6 seconds for 400,000 characters in Chromium on the same machine), so a tool whose export is that large should say that export takes a moment.

A single file is the wrong container when the data is shared between people, must be reached from two devices without a manual step, holds secrets that must not sit in browser storage, or will grow past a few megabytes.

## 7. Checks by hand, when no browser test can be run

Say that these were done by hand, or not done.

1. Open the page. Read the sentence that says where the data lives. Make one change. Reload. The change is there, or the sentence said it would not be.
2. Export. The text box holds one JSON object with the five fields. Copy it.
3. Open the page in a private window, or use Start again. Paste and import. The same items appear.
4. Paste each of these and import: nothing; `{`; `{"a":1}`; the export with `app` changed; the export with `schema` raised by one; the export with one item made invalid. Each is refused with its reason and the list is unchanged.
5. Delete something, then undo.
6. Wrap the file in a page containing `<iframe sandbox="allow-scripts" src="tool.html">` and repeat steps 1 to 4. Storage is refused there, and the sentence must say so.


## 8. Check receipts and legacy exits

Both Python tools retain their ordinary successful stdout/JSON fields and add one stderr line beginning `RECEIPT ` with tool/version, exact status, exit and semantic coverage. Shared status words are `completed`, `partial`, `not-applicable`, `failed` and `runner-error`. The status is authoritative because legacy exits are retained:

| Tool | 0 | 1 | 2 | 3 | 5 |
|---|---|---|---|---|---|
| test_demo.py | completed requested scope | actual assertion failed, or a planted defect was not caught | runner-error: invalid input or unreadable page | runner-error: missing browser/tool exception; partial: missing expected coverage | not-applicable only for a genuinely empty applicable plan |
| pocket_embed.py | completed embed check/refresh | failed marked-library contract | runner-error: input/read/write/readback problem | partial: intended block coverage incomplete | reserved for justified whole-check not-applicability |

Missing Playwright/Chromium is `runner-error`, even though the historical `NOT RUN` exit remains3. An unexpected test infrastructure exception is not a failed product assertion. A `Failed` assertion retains failed status and detail. Missing/duplicate/unexpected result rows cannot make a completed suite. A requested tab-only or frame-only scope is explicit in the receipt; frame-inapplicable storage tests are named `not-applicable`, not silently passed. `--planted --only` is rejected. Planted catches require the named actual failed assertions, never runner exceptions.

The browser receipt names requested/observed tests, per-test outcomes, not-reached coverage and surface/viewport. Test names describe semantic observations such as changed data surviving reload, refused import preserving the earlier data, and export/import reproducing the same data. Library block receipts identify intended names and comparison results; a requested refreshed output is read back and its intended blocks checked. Check-only write/readback and application runtime testing are explicitly not applicable to the embed tool. Hash equality alone is no save/reload or interface proof.

Neither teaching examples, retained raw records nor offline stubs establish a real host preview or rendered product quality. Browser tests still use temporary working files in their normal implementation; no-deletion exercises must use a retained stub workspace instead of running those cleanup paths. The separate revision receipts state what actually ran.
