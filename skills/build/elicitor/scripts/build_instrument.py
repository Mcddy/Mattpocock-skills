#!/usr/bin/env python3
"""Put an instrument into a copy of the engine, after checking it. Standard library only.

Usage:
  python build_instrument.py INSTRUMENT.json --engine ENGINE.html --out QUESTIONNAIRE.html [--json]

INSTRUMENT.json holds one instrument object (the fields are listed in validate_instrument.py and
described in references/modes.md). ENGINE.html is assets/engine.html or any questionnaire built
from it. The script replaces the object between the engine's "BEGIN INSTRUMENT DATA" and
"END INSTRUMENT DATA" marker lines and writes the result to --out. Nothing outside the data block
is changed, and the two input files are never written to.

What it enforces (ERROR, exit 1, and nothing is written):
  - every error that validate_instrument.py reports for the instrument
  - --out is not the engine and not the instrument file
What it reports for a person to decide (ADVISORY): the advisories of validate_instrument.py. Read
them: they are the wording problems a script can only point at.

The data block is written as ASCII JSON, with characters outside ASCII as escapes and "</" split
so that text inside an answer option can never close the script element.

What it cannot tell: whether the built page works in a given host's preview. Open it and use it.

Exit codes: 0 written. 1 the instrument has errors. 2 bad arguments or unreadable input.
"""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_instrument import InputError, check, load_instrument, read_text, split_engine  # noqa: E402

FLAGS = {"--json"}
VALUES = {"--engine", "--out"}


def build(engine_text, instrument, engine_path="engine"):
    """Return the engine text with its data block replaced by the instrument."""
    before, _old, after = split_engine(engine_text, engine_path)
    body = json.dumps(instrument, indent=2, ensure_ascii=True).replace("</", "<\\/")
    return before + body + after


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
                print("build_instrument: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("build_instrument: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1 or "--engine" not in opts or "--out" not in opts:
        print("build_instrument: usage: build_instrument.py INSTRUMENT.json --engine ENGINE.html --out QUESTIONNAIRE.html [--json]", file=sys.stderr)
        return 2
    out_real = os.path.realpath(opts["--out"])
    if out_real in (os.path.realpath(opts["--engine"]), os.path.realpath(args[0])):
        print("build_instrument: --out names an input file; inputs are never overwritten", file=sys.stderr)
        return 2
    try:
        inst, kind = load_instrument(args[0])
        if kind != "json":
            raise InputError("%s is a built page; give the instrument as a .json file" % args[0])
        engine_text = read_text(opts["--engine"])
        errors, adv, facts = check(inst)
        page = build(engine_text, inst, opts["--engine"]) if not errors else None
    except InputError as e:
        print("build_instrument: %s" % e, file=sys.stderr)
        return 2
    if page is not None:
        try:
            Path(opts["--out"]).write_bytes(page.encode("utf-8"))
        except OSError as e:
            print("build_instrument: cannot write %s: %s" % (opts["--out"], e.strerror or e), file=sys.stderr)
            return 2
    if "--json" in flags:
        emit(json.dumps({"errors": errors, "advisories": adv, "facts": facts, "wrote": opts["--out"] if page is not None else None}, indent=1, ensure_ascii=True))
    else:
        L = ["build_instrument: %s, %d question(s)" % (args[0], facts.get("questions", 0))]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in adv]
        if page is not None:
            L.append("  wrote %s (%d bytes). Open it and walk it once before handing it over." % (opts["--out"], len(page.encode("utf-8"))))
        L.append("RESULT: %s. %d error(s), %d advisory note(s).%s" % ("FAIL" if errors else "PASS", len(errors), len(adv), " Nothing was written." if errors else ""))
        emit("\n".join(L))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
