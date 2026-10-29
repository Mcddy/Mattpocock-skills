# Release tier templates

Copy these into an app's `release/` folder for the Release tier (`references/tiers.md`).

| File | Edit | What it does |
|---|---|---|
| `launcher.py` | CONFIG at the top | Starts the server on a free 127.0.0.1 port, waits for it, opens a native window (pywebview) or the browser with an Open / Quit window, stops the server on close. Data in `%APPDATA%\<app_id>`. `--self-test`, `--no-window`, `--version` |
| `app.spec` | NAME, PAGES, APP | PyInstaller recipe: bundles the launcher, the server module, the page files and the visual kit files |
| `requirements-build.txt` | nothing | PyInstaller 6.22.3 and pywebview 6.2.1, pinned |
| `build_exe.bat` | `set APP=` | Double-click on Windows: build environment, self-test from source, build, self-test the EXE |

Make the icon with `scripts/make_icon.py icon.svg icon.ico`. `../reference-app-plants/release/` is a filled-in, tested example.
