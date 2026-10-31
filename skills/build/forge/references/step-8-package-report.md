# Step 8: package by tier, then report

Read before step 8. Tier details are in tiers.md.

Package as the tier says (`references/tiers.md`):
- **Demo**: `scripts/single_file.py page.html demo.html --dir <direction> --keep-fonts "..."`, checked offline. "Double-click demo.html."
- **Repo**: the project layout, `run.bat` and `run.sh`, a checks runner, a pinned dependency file, `.gitignore`, a README in the set order, and git with small commits in the order the work happened. "Double-click run.bat."
- **Release**: everything in Repo plus `release/` from `assets/release/` (launcher, spec, icon from `scripts/make_icon.py`, `build_exe.bat`), with the launcher's `--self-test` run. The EXE is built on Windows by `build_exe.bat`; a session on another platform reports that build as not run, and says that an unsigned EXE meets a SmartScreen warning.

Then the report. Use these words exactly: **written**, **run locally**, **run in a sandboxed frame stand-in**, **run in the delivered surface**, **deployed**. Give each requirement one status: **exercised** (a check ran and showed it), **source-supported** (the code appears to do it; nothing ran) or **not run**. An emulated screen is a viewport size, never a device.
