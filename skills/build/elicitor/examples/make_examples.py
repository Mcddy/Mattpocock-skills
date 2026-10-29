#!/usr/bin/env python3
"""Rebuild the three example questionnaires and fill each one in through a real browser.

Usage:
  python make_examples.py [--shots DIR]

Run it from anywhere; it works on the folder it sits in. It follows the skill's own procedure:
  1. builds project-intake.html, workshop-feedback.html and subnetting-quiz.html from the
     instrument files in instruments/ with scripts/build_instrument.py (which validates first)
  2. checks the quiz's answer key with verify_subnetting.py
  3. opens each built page from disk in headless Chromium and answers it with the SYNTHETIC answer
     sets in answers/, by clicking and typing, then finishes and reads the export from the page
  4. writes project-intake.export.md, subnetting-quiz.export.md and the three files in
     workshop-responses/, and merges those three with scripts/collect_responses.py into
     workshop-responses.csv
  5. reads every export back with scripts/parse_export.py and compares it, field by field, with
     the state the page itself reported in its resume code

What it enforces (exit 1): a build that fails, an answer key that fails, a page that could not be
walked, an export that does not parse or does not match the page's own state, a merge that fails.
The time stamps in the exports are the time of the run, so the files change on every run.

Exit codes: 0 all built and checked. 1 a step failed. 2 bad arguments. 3 Playwright is missing
(prints NOT RUN).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import test_engine as te  # noqa: E402
from parse_export import parse_text  # noqa: E402
from validate_instrument import load_instrument  # noqa: E402

ENGINE = HERE.parent / "assets" / "engine.html"
NAMES = ("project-intake", "workshop-feedback", "subnetting-quiz")


def run(cmd):
    r = subprocess.run([sys.executable, "-B"] + [str(c) for c in cmd], capture_output=True, text=True)
    last = (r.stdout.strip().split("\n") or [""])[-1]
    print("  %s -> exit %d: %s" % (" ".join(Path(str(c)).name if "/" in str(c) else str(c) for c in cmd), r.returncode, last[:150]))
    return r.returncode


def fill(browser, name, plan, shots, tag):
    """Open the built page from disk, answer it, finish. Returns (export text, saved state)."""
    inst = load_instrument(str(HERE / (name + ".html")))[0]
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.set_default_timeout(8000)
    pg = ctx.new_page()
    problems = []
    pg.on("pageerror", lambda e: problems.append(str(e)))
    pg.goto((HERE / (name + ".html")).as_uri())
    pg.wait_for_selector(te.READY)
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(shots) / ("%s-first-390.png" % tag)))
    te.walk(pg, inst, plan)
    if shots:
        pg.screenshot(path=str(Path(shots) / ("%s-review-390.png" % tag)))
    export = te.finish(pg)
    if shots:
        pg.screenshot(path=str(Path(shots) / ("%s-finished-390.png" % tag)), full_page=True)
        pg.set_viewport_size({"width": 1280, "height": 800})
        pg.screenshot(path=str(Path(shots) / ("%s-finished-1280.png" % tag)), full_page=True)
    saved = json.loads(te.resume_code(pg))
    ctx.close()
    if problems:
        raise AssertionError("page errors while filling %s: %s" % (name, problems[0]))
    return inst, export, saved


def main(argv):
    shots = None
    if argv[:1] == ["--shots"] and len(argv) == 2:
        shots = argv[1]
    elif argv:
        print("make_examples: usage: make_examples.py [--shots DIR]", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("NOT RUN: the Python package 'playwright' is not installed, so the examples were not rebuilt.")
        return 3
    failed = 0
    print("1. build")
    for n in NAMES:
        failed += run([SCRIPTS / "build_instrument.py", HERE / "instruments" / (n + ".json"), "--engine", ENGINE, "--out", HERE / (n + ".html")]) != 0
    print("2. answer key")
    failed += run([HERE / "verify_subnetting.py", HERE / "subnetting-quiz.html"]) != 0
    if failed:
        print("RESULT: FAIL. A build or the answer key failed; nothing was filled in.")
        return 1
    print("3. fill in through the browser, 4. write exports, 5. read them back")
    answers = {n: json.loads((HERE / "answers" / (n + ".json")).read_text(encoding="utf-8")) for n in NAMES}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for name in ("project-intake", "subnetting-quiz"):
                plan = {k: v for k, v in answers[name].items() if not k.startswith("_")}
                inst, export, saved = fill(browser, name, plan, shots, name)
                out = HERE / (name + ".export.md")
                out.write_text(export, encoding="utf-8")
                parsed = parse_text(export)
                diffs = parsed.get("errors", []) + te.diff_record(parsed, te.expected_record(inst, saved))
                failed += bool(diffs)
                print("  %s: %d lines, %d question blocks, read back %s" % (out.name, export.count("\n"), len(parsed.get("questions", [])), "exactly" if not diffs else "WITH DIFFERENCES: " + "; ".join(diffs[:3])))
            (HERE / "workshop-responses").mkdir(exist_ok=True)
            for who in ("respondent-1", "respondent-2", "respondent-3"):
                inst, export, saved = fill(browser, "workshop-feedback", answers["workshop-feedback"][who], shots if who == "respondent-2" else None, "workshop-feedback")
                out = HERE / "workshop-responses" / (who + ".txt")
                out.write_text(export, encoding="utf-8")
                parsed = parse_text(export)
                same = parsed.get("questions") == te.expected_response(inst, saved)
                failed += bool(parsed.get("errors")) or not same
                print("  workshop-responses/%s: %d lines, read back %s" % (out.name, export.count("\n"), "exactly" if same and not parsed.get("errors") else "WITH DIFFERENCES"))
        finally:
            browser.close()
    print("6. merge the three responses")
    failed += run([SCRIPTS / "collect_responses.py"] + sorted((HERE / "workshop-responses").glob("respondent-*.txt")) + ["--out", HERE / "workshop-responses.csv"]) != 0
    print("RESULT: %s." % ("FAIL, %d step(s) failed" % failed if failed else "PASS. Three pages built, filled in through Chromium at a 390 pixel viewport, exported and read back"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
