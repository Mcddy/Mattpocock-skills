# Inputs, tools and fallbacks

Read before promising anything about the delivery surface, and whenever a browser, shell or this skill's own files are missing.

Inputs: what the thing is for, in the user's words; anything they fixed (stack, host, codebase, deadline, brand, house theme, tier); where it will be used. If the user chose the stack or architecture, build that and say at Stop A what it costs or risks, in one line. Otherwise the stack is chosen per project at Stop A: the simplest one that does the job, every piece justified in the ledger.

Check what this session has before promising anything: this skill's own files (`scripts/`, `assets/`: list one folder); a shell that can run a server and which runtimes; a browser you can drive (the scripts need Python `playwright` and Chromium); how the result is delivered (file, preview frame, local tab, deployed address); web search for anything version-specific.
- **No browser**: the board runs with `--live-only` (one self-contained file, needing only Python); `design_page.py` writes the page with diagram source and reports partial; render checks are reported as not run, with their commands.
- **No shell**: write the code and the check files, report every check as not run, and give the exact commands.
- **This skill's files cannot be reached** (only this text is loaded): say so first, naming what is missing. Build from the rules here; never write output as if a script ran or a board was rendered. The look stop keeps all sixteen directions: hand over the exact command that makes the board on the user's own machine (`python scripts/direction_board.py page.html board --live-only`, Python only), or continue the build where the package is reachable. Do not imitate the kit's directions from memory and call them the board.
