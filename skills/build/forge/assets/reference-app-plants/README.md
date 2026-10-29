Known gap, kept on purpose for teaching: the brief infers phone use, and the recommended design (a server bound to 127.0.0.1) cannot be reached from a phone. The design pack shows that conflict first and leaves it open (open question 1) instead of hiding it.

# Plant round: forge's reference build

A complete small app, built by following forge 3.1 (architecture and back end), restyled under forge 3.2 and with its design pack corrected under forge 3.3, kept as the worked example of the whole method: the back-end rules in `references/backend.md` and the visual kit applied to a subject that is not the kit's own. Read it for patterns. Don't restyle it into a deliverable or copy its copy; a new app gets its own composition, direction and words.

**The job.** One person with about 15 indoor plants sees which need water today, ticks them off and sees when each was last watered, each morning. That they do it on a phone is an inference nobody confirmed (see the gap above). Brisbane time, Australian English, 24-hour clock. The brief, slice, contract, requirements and ledger are in `notes.txt`.

## What it shows

| Area | Where to look |
|---|---|
| Rules owned by the server | `app/server.py`: "today" computed in Australia/Brisbane on the server; once per plant per local day as `UNIQUE(plant_id, local_date)` (20 parallel ticks give 1 accepted, 19 refused); names unique ignoring case and spaces |
| Contract and errors | One error shape with `code`, `message`, per-field reasons and a request id; messages written as product copy; a catch-all 500 in the same shape |
| Safety for a local server | Binds 127.0.0.1, checks `Host`, JSON-only writes, no CORS headers |
| Repeats and races | Idempotency keys on creates (kept across restarts), undo, a bounded list with a cursor |
| Storage | Numbered migrations under `PRAGMA user_version`; backup and restore commands (`server.py backup --db F --to DIR`, `server.py restore --db F --from FILE --replace`) |
| Test seams | `--now` (frozen clock, with a banner on the page) and `--faults`, accepted only with their flags |
| Composition | The operative answer (plants still to water today) as the hero value; facts that decide each tick (last watered, interval, days overdue) beside its button; ticked rows stay in place; a seven-day strip |
| Visual kit use | Tokens only; the kit's shared components plus the generic ones; `.hero-value` for the count, `.slot.is-alert` for overdue rows so they never compete with the signature block |
| Illustration | `app/plant-art.js` (also in the kit as `illustrations-plants.js`): eight plant shapes and three scenes on the kit's clay helpers, drawn flat in Fresh Green and Mono Flood and clay elsewhere |
| States | Populated, empty (the form opens with a scene), refused (already watered, duplicate name), load error, success after a tick, all watered |
| Checks | `checks/`: API steps (54, including restart and a race), Brisbane day-boundary steps, UI steps (56), seed and capture scripts, the string sheet, and `run_all.sh` to rerun everything |

## Tiers and design, as forge 3.2 builds them

| Piece | Where |
|---|---|
| Design pack (Stop A): requirements, three options, eight diagrams, decision records, why notes, glossary, mistakes to watch for | `docs/design.md`, rendered as `docs/design.html` by `scripts/design_page.py` |
| Repo tier: double-click start | `run.bat` (Windows), `run.sh` (macOS, Linux) |
| Release tier: a Windows app with an icon | `release/`: `launcher.py`, `app.spec`, `icon.svg` and `icon.ico`, `requirements-build.txt`, `build_exe.bat` |

The release folder was tested on Linux: the launcher's `--self-test` from source, and a PyInstaller build for Linux whose page loaded every kit file and font with nothing failing; stopping it stopped the server. The Windows EXE itself is built by double-clicking `release/build_exe.bat` on Windows and has not been built in a forge session.

## Run it

```
python3 app/server.py --port 8710 --db plants.db
```

Then open http://127.0.0.1:8710/. The server looks for the kit in a `kit/` folder beside it, otherwise in forge's `assets/visual-kit/`. To try another direction, change `data-dir` on `<html>` in `app/index.html`, or render all of them with `scripts/direction_board.py http://127.0.0.1:8710/ OUTDIR`.

`sh checks/run_all.sh` reruns every check on ports 8711 to 8716 and writes results into `checks/` and `checks/render/` (set `AXE_DIR` to a folder with `node_modules/axe-core` for the accessibility scans).

## Record

Built in one session by an agent following forge 3.1 with no one to ask, so it chose the direction by the unattended rule (Fresh Green: a calm morning round). After the kit gained role classes, shape tokens and contrast fixes, it was re-pointed at the shared kit and every check was rerun from this folder: API 54 of 54 plus 1 and 4 boundary steps; UI 56 of 56 in a tab, with reduced motion and with outside requests blocked; render gate exit 0 for five states; contrast 0 below in three states; targets 16 of 16 and 15 of 15; dead controls 16 of 16 and 12 of 12. All of it ran locally in headless Chromium; nothing was deployed or tried by a real user.

Known limits: no edit or delete for plants yet; no photos; the "unknown outcome" path and the Brisbane-time suffix for viewers in other zones are supported by the source but were not exercised.
