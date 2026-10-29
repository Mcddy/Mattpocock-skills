#!/usr/bin/env python3
"""Completion gate. Runs the checks named in a config file and reports whether the work may be called done.
Standard library only.

Usage:
  python gate.py [--config .done-gate.json] [--block-code 2] [--list] [--reset]

Config (JSON):
{
  "brief": "path/to/task-brief.md",          optional, printed by --brief
  "max_blocks": 8,                            consecutive failures before reporting needs_attention
  "checks": [
    {"name": "tests", "cmd": "python -m pytest -q", "timeout_s": 900},
    {"name": "build output exists", "cmd": "python -c \"import pathlib,sys; sys.exit(0 if pathlib.Path('dist/index.html').exists() else 1)\""}
  ]
}

Exit codes:
  0            every check passed
  --block-code at least one check failed and the limit is not reached (default 2). Failures go to stderr.
  3            needs_attention at the failure limit, or invalid configuration or block-code argument
The gate never edits the config or the checks. Wiring it to a host's hook events is done per host, from that host's own documentation.
"""
import json
import subprocess
import sys
import time
from pathlib import Path


def main(argv):
    def opt(flag, default):
        return argv[argv.index(flag) + 1] if flag in argv else default

    cfg_path = Path(opt("--config", ".done-gate.json"))
    block_code = int(opt("--block-code", "2"))
    if block_code <= 0 or block_code > 255:
        print("done-gate: block code must be between 1 and 255", file=sys.stderr)
        return 3
    state_path = cfg_path.with_name(cfg_path.stem + ".state.json")
    if "--reset" in argv:
        if state_path.exists():
            state_path.unlink()
        print(json.dumps({"status": "reset"}))
        return 0
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        checks = cfg["checks"]
        assert isinstance(checks, list) and checks
    except Exception as exc:  # noqa: BLE001
        print("done-gate: cannot read a usable config at %s (%s)" % (cfg_path, exc), file=sys.stderr)
        return 3
    if "--brief" in argv:
        b = cfg.get("brief")
        print(Path(b).read_text(encoding="utf-8") if b and Path(b).exists() else "done-gate: no brief file configured")
        return 0
    if "--list" in argv:
        for c in checks:
            print("%-30s %s" % (c["name"], c["cmd"]))
        return 0

    cwd = cfg_path.resolve().parent
    results = []
    for c in checks:
        t0 = time.time()
        try:
            p = subprocess.run(c["cmd"], shell=True, cwd=str(cwd), capture_output=True, text=True,
                               timeout=float(c.get("timeout_s", 600)))
            ok, tail = p.returncode == 0, (p.stdout + p.stderr).strip()[-600:]
        except subprocess.TimeoutExpired:
            ok, tail = False, "timed out after %ss" % c.get("timeout_s", 600)
        results.append({"name": c["name"], "passed": ok, "seconds": round(time.time() - t0, 2), "output_tail": tail})

    failed = [r for r in results if not r["passed"]]
    state = {"blocks": 0}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            state = {"blocks": 0}
    if not failed:
        if state_path.exists():
            state_path.unlink()
        print(json.dumps({"status": "passed", "checks": results}, indent=1))
        return 0

    state["blocks"] = int(state.get("blocks", 0)) + 1
    limit = int(cfg.get("max_blocks", 8))
    if state["blocks"] > limit:
        state_path.unlink(missing_ok=True)
        print(json.dumps({"status": "needs_attention", "blocks": limit, "failing": [r["name"] for r in failed],
                          "checks": results}, indent=1))
        print("done-gate: block limit reached. The work is NOT done. Report these failing checks to the user: "
              + ", ".join(r["name"] for r in failed), file=sys.stderr)
        return 3
    state_path.write_text(json.dumps(state), encoding="utf-8")
    print(json.dumps({"status": "blocked", "block": state["blocks"], "of": limit, "checks": results}, indent=1))
    print("done-gate: not done. Failing checks (%d of %d blocks used):" % (state["blocks"], limit), file=sys.stderr)
    for r in failed:
        print("  - %s\n    %s" % (r["name"], r["output_tail"].replace("\n", "\n    ")), file=sys.stderr)
    return block_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
