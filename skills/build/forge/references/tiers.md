# Tiers: how far a build goes

Every build has a tier. The tier decides what gets delivered and how it runs, not how carefully it is made: a demo still has real states, honest copy and the chosen direction. Forge proposes the tier at the architecture stop (`design.md`); a Demo has no architecture stop, so its tier is stated in the look-pick message instead.

## Choosing the tier

| The request says or implies | Tier |
|---|---|
| "quick", "demo", "mock up", "try the idea", "see if I like it", "prototype", "one file", or nothing needs keeping beyond this browser | **Demo** |
| "build me an app", "tool", "system", or anything that keeps data, has users, or will be worked on again (the default) | **Repo** |
| "exe", "installer", "desktop app", "release", "ship it", "give it to someone", "icon", "double-click" | **Release** |

When two readings fit, take the lower tier and say what moving up would add. A tier can be raised later without starting again: Demo to Repo keeps the page and direction and adds the back end; Repo to Release adds the launcher and packaging.

## Demo: one HTML file

For checking a concept quickly. Delivered as a single file that opens by double-click, offline, with nothing installed.

- One self-contained HTML file: the page, its script and the chosen direction's CSS inlined, only that direction's fonts embedded, illustrations as inline SVG. Build it as normal files, then pack it with `scripts/single_file.py page.html demo.html --dir <direction> --keep-fonts "Display Face,Body Face"`; it lists anything that still points outside the file.
- No back end. State lives in memory, or in browser storage when keeping it between visits matters. When the pocket-app skill is present, use its tested save library (versioned data, migrations, export and import that cannot half-apply) rather than hand-written `localStorage`; otherwise wrap storage in try/catch and say what it does not do (no migration, no backup). The page says plainly where data lives ("Saved in this browser only") and never implies a server.
- Sample data is realistic and labelled as sample where a reader could mistake it for theirs.
- Still required: every state the data can be in, the string sheet, the direction board and the look stop. Skipped: the architecture stop, the contract and the API checks (there is no API). A short design note (what it would take to become a Repo) goes at the end of the report.
- Checks: `render_gate.py demo.html OUT` and `delivery_check.py demo.html --steps FILE` with `--block-outside`, which proves it works offline.

## Repo: run it the way developers do

The default. A project folder another developer (or a future you) can open, run, test and change.

- Layout: `app/` (server and page), `checks/` (API steps, UI steps, seed data), `docs/` (`design.md`, `design.html`), `README.md`, a pinned dependency file (`requirements.txt` or `package.json` with a lockfile), `.gitignore` (data files, virtual environments, build output, secrets).
- One start command, and a double-click on Windows: `run.bat` (starts the server in its own window, then opens the browser) and `run.sh` for macOS and Linux. `assets/reference-app-plants/run.bat` and `run.sh` are the pattern.
- A checks runner (`checks/run_all.sh`, plus `checks/run_all.bat` when the user is on Windows) that runs every check in step 7 and prints one line per check.
- Git: `git init`, then small commits in the order the work happened (contract, back end with its checks, page, direction, states, docs), each with a plain message saying what changed and why. Never commit data files, `.env` or keys.
- The README says, in this order: what it is (one line), how to start it, how to run the checks, where data is kept and how to back it up, the folder map, and what is not done yet.
- Everything in step 2's acceptance list, the design pack, and the full verification table.

## Release: a Windows app with an icon

For something to use every day or hand to someone: double-click an icon, a window opens, no terminal.

- Everything in Repo, plus a `release/` folder:
  - `launcher.py`, copied from `assets/release/launcher.py` with its CONFIG filled in. It starts the server on a free 127.0.0.1 port, waits until it answers, opens a native window (pywebview, using Microsoft Edge WebView2, which Windows 10 and 11 include) or falls back to the browser with a small Open / Quit window, and stops the server when the app closes. Data goes to `%APPDATA%\<AppId>`, never beside the EXE; a second launch reuses the running copy; the server log is in `%APPDATA%\<AppId>\logs`.
  - `icon.svg` (a mark drawn for 16 px: two or three bold shapes on a solid rounded square, no text) and `icon.ico` made with `scripts/make_icon.py icon.svg icon.ico`.
  - `app.spec` (from `assets/release/app.spec`): bundles the page, its scripts and the kit files the page links.
  - `requirements-build.txt` with PyInstaller and pywebview pinned, and `build_exe.bat`, which makes a build virtual environment in the folder, self-tests from source, builds, self-tests the EXE and prints where it is.
- The EXE is built on Windows by double-clicking `build_exe.bat`. PyInstaller does not cross-compile, so a build session on Linux or macOS cannot produce the EXE: it writes and tests everything else (the launcher's `--self-test`, and a PyInstaller build for the host platform as a stand-in that proves the bundle carries its files) and reports the Windows build as **not run**. A Windows CI runner can build it instead, if the user sets one up.
- Say plainly what Windows will do: an unsigned EXE triggers SmartScreen ("Windows protected your PC": More info, then Run anyway). Code signing removes that but costs money each year, so it needs the user's go-ahead.
- Optional, when asked: an installer with Start menu and desktop shortcuts (Inno Setup, free), an About box with the version, automatic backups to a folder the user picks, and an update check that only reads.
- Node stacks: the same shape with Electron or Tauri; the launcher's jobs (free port, health wait, data folder, single instance, stop on close) stay the same.

The worked example is `assets/reference-app-plants/release/`: its launcher, spec, icon and build script were tested on Linux (self-test from source; a PyInstaller build whose page loaded with every kit file and font, nothing failing; SIGTERM stopped the server). The Windows EXE itself has not been built in a forge session.

## What each tier reports

| | Demo | Repo | Release |
|---|---|---|---|
| Deliverable | `demo.html` | the project folder (and a zip of it) | the project folder with `release/`, and the EXE if it was built on Windows |
| How to run, in the report | "Double-click demo.html" | "Double-click run.bat" (or the shell command) | "Double-click build_exe.bat once, then use dist\<App>\<App>.exe" |
| Status words | written / run locally | written / run locally / exercised per requirement | as Repo, plus the EXE build as run or not run |
