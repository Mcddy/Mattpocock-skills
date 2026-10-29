# Historical teaching examples: pocket-app (not newly validated)

These examples were made by the original authoring session by following the skill's procedure. They are included in this package as historical teaching material. Their original reports below are not fresh validation of this revision or of another host.

| File | What it is |
|---|---|
| `reading-log.html` | A reading log built on `pocket-state.js` and `pocket-ui.js`: title, author, shelf, rating and notes, with add, edit in place, remove with undo, find, shelf filter, ordering, export, import, four themes, two row spacings and three text sizes. Schema 2. Opens empty |
| `reading-log-schema1.json` | SYNTHETIC export in the schema 1 shape (`title`, `author`, `done`, `stars`, `note`). The nine titles are real published books; the ratings and notes are invented. Import it into the page to see the migration |
| `reading-log-export.json` | What the page exported after that import: the same nine books at schema 2. Importing it into a fresh page reproduces them |
| `reading-log.steps.txt` | The primary journey as steps for `delivery_check.py` (interface-architect's script), run in a tab and in a sandboxed frame |

## Try it

1. Open `reading-log.html`. The line under "Keep your log" says where the data lives.
2. Paste the contents of `reading-log-schema1.json` into the import box and choose Import. The page reports nine books brought up from schema 1 to schema 2. Undo puts the empty log back.
3. Edit the pasted text before importing to see a refusal: change `"app"` to another name, raise `"schema"` to 3, or set a `stars` value to 9. Each is refused with its reason and the log is unchanged.
4. Reload. In a browser tab the books are still there. Inside a sandboxed frame they are not, and the page said so beforehand.

## Regenerate

From the skill folder:

```
python3 scripts/pocket_embed.py examples/reading-log.html
python3 scripts/test_demo.py examples/reading-log.html --change "fill:#a-title=Middlemarch" --change "click:#add-go" --proof "#books=Middlemarch"
```

The first command shows that the two library copies pasted into the page are the files in `assets/`. The second runs the state contract tests against the page in a tab and in a sandboxed frame. To refresh the pasted copies after a change to the library, run `pocket_embed.py examples/reading-log.html --out NEW.html` and replace the page with `NEW.html`; the page itself is the source, and there is no separate template. `reading-log-export.json` was produced by importing the schema 1 file in the page and copying the export box.

## What the authoring session ran on these files

See the section "What has and has not been tested" in `SKILL.md` for the numbers. In short: the library tests under Node, the browser tests on this page at 390 by 844 and 1280 by 800 in a tab and a frame, the steps file through `delivery_check.py` at both sizes, contrast in all four themes with an error showing, target sizes at 390 wide, the dead-control scan, and screenshots at both widths. Not run: any real chat host's preview, any screen reader, any browser other than the Chromium that Playwright launches.
