#!/usr/bin/env python3
"""Put a course into the engine: write one self-contained course page. Standard library only.

Usage:
  python build_course.py ENGINE.html COURSE.json OUT.html [--renderers FILE.js] [--allow-errors] [--json]
  python build_course.py --extract PAGE.html OUT.json

Build: copies ENGINE.html, replaces the object between the COURSE DATA markers with COURSE.json,
and writes OUT.html. Everything outside the markers is copied byte for byte. With --renderers,
FILE.js must hold one JavaScript object literal, { "name": function (host, data, api) { ... } },
and it replaces the value between the CUSTOM RENDERERS markers.

Extract: writes the course object found in a built page as indented JSON, so a course can be
revised from its page.

What it enforces (exit 1, nothing written):
  - the course passes validate_course.py with no errors (unless --allow-errors, which is for
    building test pages on purpose and is printed in the result)
  - the engine has exactly one COURSE DATA block and one CUSTOM RENDERERS block
  - the renderer file is plain ASCII and contains no script end tag
What it reports (ADVISORY): the validator's advisories, passed through.
What it cannot tell: whether the course is correct or teaches well.

The course JSON is written with every non-ASCII character escaped, and "</" written as "<\\/",
so course text cannot end the script block it sits in. OUT must not be the engine or the course
file: inputs are never modified.

Exit codes: 0 written. 1 a check failed. 2 bad arguments or unreadable input.
"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_course as vc  # noqa: E402

FLAGS = {"--allow-errors", "--json", "--extract"}
VALUES = {"--renderers"}
DATA_BLOCK = re.compile(r"(/\* === COURSE DATA: BEGIN[^\n]*\*/\s*const COURSE\s*=\s*)(.*?)(;\s*/\* === COURSE DATA: END === \*/)", re.S)
REND_BLOCK = re.compile(r"(/\* === CUSTOM RENDERERS: BEGIN[^\n]*\*/\s*const CUSTOM_RENDERERS\s*=\s*)(.*?)(;\s*/\* === CUSTOM RENDERERS: END === \*/)", re.S)


def read_text(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise vc.InputError("cannot read %s: %s" % (path, e.strerror or e))
    if b"\x00" in raw:
        raise vc.InputError("%s contains NUL bytes; it is not a text file" % path)
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise vc.InputError("%s is not valid UTF-8" % path)


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("build_course: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("build_course: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    try:
        if "--extract" in flags:
            if len(args) != 2 or opts or "--allow-errors" in flags:
                print("build_course: --extract takes PAGE.html and OUT.json", file=sys.stderr)
                return 2
            if Path(args[0]).resolve() == Path(args[1]).resolve():
                print("build_course: OUT must not be the input page", file=sys.stderr)
                return 2
            course, _ = vc.read_course(args[0])
            Path(args[1]).write_text(json.dumps(course, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
            emit("build_course: wrote the course data of %s to %s" % (args[0], args[1]))
            return 0
        if len(args) != 3:
            if not argv:
                print(__doc__)
            else:
                print("build_course: expected ENGINE.html COURSE.json OUT.html", file=sys.stderr)
            return 2
        engine_path, course_path, out_path = args
        inputs = [Path(engine_path).resolve(), Path(course_path).resolve()]
        if "--renderers" in opts:
            inputs.append(Path(opts["--renderers"]).resolve())
        if Path(out_path).resolve() in inputs:
            print("build_course: OUT must not be the engine or the course file; inputs are never modified", file=sys.stderr)
            return 2
        engine = read_text(engine_path)
        course, own_renderers = vc.read_course(course_path)
        renderers = None
        if "--renderers" in opts:
            renderers = read_text(opts["--renderers"]).strip()
            if any(ord(c) > 127 for c in renderers):
                raise vc.InputError("%s must be plain ASCII" % opts["--renderers"])
            if re.search(r"</script", renderers, re.I):
                raise vc.InputError("%s contains a script end tag" % opts["--renderers"])
            if not (renderers.startswith("{") and renderers.endswith("}")):
                raise vc.InputError("%s must hold one object literal: { \"name\": function (host, data, api) { ... } }" % opts["--renderers"])
        elif own_renderers is not None:
            m = REND_BLOCK.search(read_text(course_path))
            renderers = m.group(2).strip() if m else None
    except vc.InputError as e:
        print("build_course: %s" % e, file=sys.stderr)
        return 2
    problems = []
    if len(DATA_BLOCK.findall(engine)) != 1:
        problems.append("the engine must contain exactly one COURSE DATA block (found %d)" % len(DATA_BLOCK.findall(engine)))
    if len(REND_BLOCK.findall(engine)) != 1:
        problems.append("the engine must contain exactly one CUSTOM RENDERERS block (found %d)" % len(REND_BLOCK.findall(engine)))
    rep, stats = vc.validate(course, ("const CUSTOM_RENDERERS = " + renderers) if renderers is not None else "")
    forced = "--allow-errors" in flags and bool(rep.errors)
    if rep.errors and "--allow-errors" not in flags:
        problems += ["course: " + e for e in rep.errors]
    if problems:
        if "--json" in flags:
            emit(json.dumps({"written": False, "errors": problems, "advisories": rep.advisories}, indent=1, ensure_ascii=True))
        else:
            emit("\n".join(["build_course: NOT WRITTEN"] + ["  ERROR     " + p for p in problems] +
                           ["RESULT: FAIL. %d error(s). Fix the course and build again." % len(problems)]))
        return 1
    data = json.dumps(course, indent=1, ensure_ascii=True).replace("</", "<\\/")
    page = DATA_BLOCK.sub(lambda m: m.group(1) + data + m.group(3), engine, count=1)
    if renderers is not None:
        page = REND_BLOCK.sub(lambda m: m.group(1) + renderers + m.group(3), page, count=1)
    Path(out_path).write_bytes(page.encode("utf-8"))
    if "--json" in flags:
        emit(json.dumps({"written": True, "out": str(out_path), "bytes": len(page.encode("utf-8")), "built_with_errors": forced,
                         "validator_errors": rep.errors if forced else [], "advisories": rep.advisories, "counts": stats}, indent=1, ensure_ascii=True))
    else:
        lines = ["build_course: wrote %s (%d bytes): %s version %r, %d written and %d planned module(s)"
                 % (out_path, len(page.encode("utf-8")), course.get("id"), course.get("version"), stats["modules_ready"], stats["modules_planned"])]
        if forced:
            lines.append("  BUILT WITH %d VALIDATOR ERROR(S) because --allow-errors was given. This page is for testing only." % len(rep.errors))
        lines += ["  ADVISORY  " + a for a in rep.advisories]
        lines.append("RESULT: PASS. Open the page and read it; a build is not a review.")
        emit("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
