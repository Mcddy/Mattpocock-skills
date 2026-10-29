#!/usr/bin/env python3
"""Merge survey response blocks into one CSV, one row per respondent. Standard library only.

Usage:
  python collect_responses.py FILE [FILE ...] --out RESPONSES.csv
         [--instrument ID] [--version N] [--multi pipe|json] [--all-notes] [--no-guard] [--json]

Each FILE is a text file into which one or more response blocks were pasted. A block is what a
survey-mode questionnaire shows on its last screen, from the line "=== elicitor response ===" to
the line that starts "=== end elicitor response:". Anything around a block (a greeting, a
signature) is ignored. One block per respondent; a row is named after its file and its position
in that file, because a block carries no name.

The CSV has the columns: source, instrument, version, finished, then one column per question id
in the order the first block lists them, a "<id>.note" column after any question that has a note
in at least one block (every question with --all-notes), and "tally:<id>" and "tally:<id>:of"
columns when the blocks carry tallies. Cells:
  an answer             the text or number; several choices joined with " | " (or a JSON list
                        with --multi json)
  skipped               (skipped)
  hidden by show_if     (not shown)
  reached, no answer    empty
The file is UTF-8 with no byte-order mark.

What it enforces (ERROR, exit 1, and no CSV is written):
  - every block is whole and readable (the checks of parse_export.py)
  - every block is for the same instrument id and the same version. The first block sets what is
    expected unless --instrument and --version say so; each block that differs is named with
    what it has
  - every block lists the same question ids
  - no block is an exact repeat of another (same finished time and same answers)
  - with --multi pipe, no chosen option contains " | "; and no typed answer is exactly
    "(skipped)" or "(not shown)", which could not be told apart from the markers
  - --out is not one of the input files
What it reports for a person to decide (ADVISORY):
  - text cells that begin with =, +, - or @ were prefixed with an apostrophe so that a spreadsheet
    does not run them as formulas (count given; --no-guard turns this off)
  - wrapped lines that were joined back together inside a block
  - a file with no block in it
  - tallies are counts of answers, not a validated measure

What it cannot tell: who each respondent is, whether one person sent two different blocks, or
whether a block was edited by hand in a way that keeps its counts consistent.

Exit codes: 0 merged with no errors. 1 errors (nothing written). 2 bad arguments or unreadable input.
"""
import csv
import io
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_export import InputError, TALLY_LINE, parse_response_blocks, read_text, to_lines  # noqa: E402

FLAGS = {"--json", "--no-guard", "--all-notes"}
VALUES = {"--out", "--instrument", "--version", "--multi"}
MARKERS = ("(skipped)", "(not shown)")
RISKY = ("=", "+", "-", "@", "\t", "\r")


def collect(paths, want_id=None, want_version=None, multi="pipe", guard=True, all_notes=False):
    """Return (header, rows, errors, advisories, facts). rows is empty when there are errors."""
    errors, adv, blocks = [], [], []
    for p in paths:
        found = parse_response_blocks(to_lines(read_text(p)), os.path.basename(p))
        if not found:
            adv.append("%s holds no response block" % p)
        for n, b in enumerate(found):
            b["name"] = "%s#%d" % (os.path.basename(p), n + 1)
            for e in b["errors"]:
                errors.append("%s: %s" % (b["name"], e))
            for a in b["advisories"]:
                adv.append("%s: %s" % (b["name"], a))
            blocks.append(b)
    facts = {"files": len(paths), "blocks": len(blocks)}
    if not blocks:
        errors.append("no response block was found in %d file(s)" % len(paths))
        return [], [], errors, adv, facts
    ref = blocks[0]
    exp_id = want_id if want_id is not None else ref["instrument"]["id"]
    exp_ver = want_version if want_version is not None else ref["instrument"]["version"]
    said = "given on the command line" if (want_id is not None or want_version is not None) else "taken from %s" % ref["name"]
    facts["instrument"], facts["version"] = exp_id, exp_ver
    for b in blocks:
        got = (b["instrument"]["id"], b["instrument"]["version"])
        if got[0] is None or got[1] is None:
            continue
        if got != (exp_id, exp_ver):
            errors.append("%s is for instrument %r version %s; expected %r version %s (%s). It was not merged"
                          % (b["name"], got[0], got[1], exp_id, exp_ver, said))
    same = [b for b in blocks if (b["instrument"]["id"], b["instrument"]["version"]) == (exp_id, exp_ver) and not b["errors"]]
    ids = [q["id"] for q in same[0]["questions"]] if same else []
    for b in same[1:]:
        mine = [q["id"] for q in b["questions"]]
        if set(mine) != set(ids):
            extra, missing = sorted(set(mine) - set(ids)), sorted(set(ids) - set(mine))
            errors.append("%s lists different question ids from %s (extra: %s; missing: %s) although both state the same version"
                          % (b["name"], same[0]["name"], ", ".join(extra) or "none", ", ".join(missing) or "none"))
    seen = {}
    for b in same:
        key = json.dumps([b["finished"], [(q["id"], q["status"], q["answer"], q["note"]) for q in b["questions"]]], sort_keys=True)
        if key in seen:
            errors.append("%s is an exact repeat of %s (same finished time and same answers); remove one" % (b["name"], seen[key]))
        seen[key] = b["name"]
    noted = [i for i in ids if all_notes or any(q["id"] == i and q["note"] for b in same for q in b["questions"])]
    tally_ids = []
    for b in same:
        for t in b["tallies"]:
            if t["id"] not in tally_ids:
                tally_ids.append(t["id"])
    header = ["source", "instrument", "version", "finished"]
    for i in ids:
        header.append(i)
        if i in noted:
            header.append(i + ".note")
    for t in tally_ids:
        header += ["tally:" + t, "tally:" + t + ":of"]
    guarded = 0

    def cell(v):
        nonlocal guarded
        if isinstance(v, str) and guard and v.startswith(RISKY):
            guarded += 1
            return "'" + v
        return v

    rows = []
    for b in same:
        byid = {q["id"]: q for q in b["questions"]}
        row = [b["name"], exp_id, exp_ver, b["finished"]]
        for i in ids:
            q = byid.get(i, {"status": None, "answer": None, "note": None})
            a = q["answer"]
            if q["status"] == "skipped":
                val = "(skipped)"
            elif q["status"] == "hidden":
                val = "(not shown)"
            elif q["status"] != "answered":
                val = ""
            elif isinstance(a, list):
                if multi == "json":
                    val = json.dumps(a, ensure_ascii=False)
                else:
                    if any(" | " in x for x in a):
                        errors.append("%s: an option chosen for %r contains ' | ', which is the separator; run again with --multi json" % (b["name"], i))
                    val = cell(" | ".join(a))
            elif isinstance(a, str):
                if a in MARKERS:
                    errors.append("%s: the typed answer to %r is exactly %r, which cannot be told apart from the marker; edit that block by agreement with the respondent" % (b["name"], i, a))
                val = cell(a)
            else:
                val = a
            row.append(val)
            if i in noted:
                row.append(cell(q["note"]) if q["note"] else "")
        tl = {t["id"]: t for t in b["tallies"]}
        for t in tally_ids:
            row += [tl[t]["count"], tl[t]["of"]] if t in tl else ["", ""]
        rows.append(row)
    if guarded:
        adv.append("%d text cell(s) began with =, +, - or @ and were prefixed with an apostrophe so a spreadsheet will not run them as formulas (--no-guard to keep them as typed)" % guarded)
    if tally_ids:
        adv.append("tally columns: " + TALLY_LINE)
    facts.update({"rows": len(rows), "questions": len(ids), "note_columns": len(noted), "tally_columns": len(tally_ids) * 2})
    if errors:
        return header, [], errors, adv, facts
    return header, rows, errors, adv, facts


def to_csv(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


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
                print("collect_responses: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("collect_responses: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if not args:
        print("collect_responses: give at least one file. Usage: collect_responses.py FILE [FILE ...] --out RESPONSES.csv", file=sys.stderr)
        return 2
    if "--out" not in opts and "--json" not in flags:
        print("collect_responses: --out RESPONSES.csv is needed (or --json to print the rows as JSON)", file=sys.stderr)
        return 2
    multi = opts.get("--multi", "pipe")
    if multi not in ("pipe", "json"):
        print("collect_responses: --multi takes pipe or json", file=sys.stderr)
        return 2
    want_version = None
    if "--version" in opts:
        if not opts["--version"].isdigit() or int(opts["--version"]) < 1:
            print("collect_responses: --version needs a whole number from 1", file=sys.stderr)
            return 2
        want_version = int(opts["--version"])
    if ("--version" in opts) != ("--instrument" in opts):
        print("collect_responses: give --instrument and --version together", file=sys.stderr)
        return 2
    if "--out" in opts:
        out_real = os.path.realpath(opts["--out"])
        if any(os.path.realpath(p) == out_real for p in args):
            print("collect_responses: --out names one of the input files; inputs are never overwritten", file=sys.stderr)
            return 2
    try:
        header, rows, errors, adv, facts = collect(args, opts.get("--instrument"), want_version, multi, "--no-guard" not in flags, "--all-notes" in flags)
    except InputError as e:
        print("collect_responses: %s" % e, file=sys.stderr)
        return 2
    wrote = None
    if not errors and "--out" in opts:
        try:
            Path(opts["--out"]).write_bytes(to_csv(header, rows).encode("utf-8"))
            wrote = opts["--out"]
        except OSError as e:
            print("collect_responses: cannot write %s: %s" % (opts["--out"], e.strerror or e), file=sys.stderr)
            return 2
    if "--json" in flags:
        emit(json.dumps({"errors": errors, "advisories": adv, "facts": facts, "header": header, "rows": rows, "wrote": wrote}, indent=1, ensure_ascii=True))
    else:
        L = ["collect_responses: %d block(s) in %d file(s), instrument %r version %s" % (facts.get("blocks", 0), facts.get("files", 0), facts.get("instrument"), facts.get("version"))]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in adv]
        if wrote:
            L.append("  wrote %s: %d row(s), %d question column(s), %d note column(s), %d tally column(s)"
                     % (wrote, facts["rows"], facts["questions"], facts["note_columns"], facts["tally_columns"]))
        L.append("RESULT: %s. %d error(s), %d advisory note(s).%s" % ("FAIL" if errors else "PASS", len(errors), len(adv), " Nothing was written." if errors else ""))
        emit("\n".join(L))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
