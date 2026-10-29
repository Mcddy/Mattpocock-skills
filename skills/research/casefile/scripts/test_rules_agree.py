#!/usr/bin/env python3
"""Check that build_casefile.py applies the same ledger rules as ledger_check.py. Standard library only.

Usage:
  python test_rules_agree.py [--ledger-check PATH/ledger_check.py] [--planted] [--json]

build_casefile.py implements the rules of deep-research-orchestrator's ledger_check.py on its
own, importing nothing from that skill. This test shows the two agree.

What it compares, for four ledgers in the fixtures folder beside this script (the real EAA
ledger, the checker's own bad sample, a SYNTHETIC ledger written to trip every rule, and a
SYNTHETIC ledger of valid neighbours that must pass):
  - the list of errors, the list of advisory notes, the counts by status and the row counts,
    as exact text and in order
against fixtures/expected.json, which is ledger_check.py's own --json output recorded on
2026-10-09 with --today 2026-10-09. With --ledger-check it also runs that script now and
compares against its live output, which is the stronger check when the other skill is installed.

It also checks build_casefile.py's command line: a bad ledger exits 1 and writes nothing, the
good neighbour exits 0, an unknown option and a missing column exit 2.

--planted breaks the rules in memory in three ways (aggregator sources allowed to carry a FACT,
open insufficient-evidence conflicts no longer reported, a one-sided conflict accepted) and
checks that the comparison fails each time.

What it cannot tell: whether the rules themselves are the right rules.

Exit codes: 0 everything agreed (or every planted failure was caught). 1 a disagreement (or a
planted failure was missed). 2 bad arguments or unreadable fixtures.
"""
import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
CASES = ("eaa", "bad", "edge", "near")
FLAGS = {"--planted", "--json"}
VALUES = {"--ledger-check"}

sys.dont_write_bytecode = True      # leave no cache folder inside the skill
sys.path.insert(0, str(HERE))
import build_casefile as bc  # noqa: E402


def mine(case, today):
    sources, e1 = bc.load_table(str(FIX / (case + "-sources.csv")), bc.SOURCE_COLUMNS)
    claims, e2 = bc.load_table(str(FIX / (case + "-claims.csv")), bc.CLAIM_COLUMNS)
    if e1 or e2:
        raise RuntimeError(e1 or e2)
    errors, advisories, counts, src, cl = bc.check_ledger(sources, claims, today)
    return {"sources": len(src), "claims": len(cl), "by_status": counts, "errors": errors, "advisories": advisories}


def differences(name, got, want):
    out = []
    for key in ("sources", "claims", "by_status"):
        if got[key] != want[key]:
            out.append("%s: %s is %r here and %r from ledger_check.py" % (name, key, got[key], want[key]))
    for key in ("errors", "advisories"):
        if got[key] != want[key]:
            only_here = [m for m in got[key] if m not in want[key]]
            only_there = [m for m in want[key] if m not in got[key]]
            if not only_here and not only_there:
                out.append("%s: the same %s in a different order" % (name, key))
            for m in only_here[:4]:
                out.append("%s: only build_casefile.py reports %s: %s" % (name, key[:-1] if key == "errors" else "advisory", m))
            for m in only_there[:4]:
                out.append("%s: only ledger_check.py reports %s: %s" % (name, key[:-1] if key == "errors" else "advisory", m))
    return out


def compare_all(expected, today, live_script=None):
    problems, lines = [], []
    for case in CASES:
        got = mine(case, today)
        want = expected["cases"][case]
        diff = differences(case + " (recorded)", got, want)
        if live_script:
            run = subprocess.run([sys.executable, str(live_script), str(FIX / (case + "-sources.csv")), str(FIX / (case + "-claims.csv")),
                                  "--json", "--today", today.isoformat()], capture_output=True, text=True)
            try:
                live = json.loads(run.stdout)
            except ValueError:
                diff.append("%s (live): ledger_check.py gave no JSON (exit %d)" % (case, run.returncode))
            else:
                diff += differences(case + " (live)", got, live)
        problems += diff
        lines.append("  %s  %-4s %d source(s), %d claim(s): %d error(s) and %d advisory note(s), %s"
                     % ("FAIL" if diff else "PASS", case, got["sources"], got["claims"], len(got["errors"]), len(got["advisories"]),
                        "differs" if diff else ("identical to ledger_check.py, recorded" + (" and live" if live_script else ""))))
    return problems, lines


def command_line(today):
    """build_casefile.py as a program: exit codes, and nothing written for a refused ledger."""
    problems = []
    script = str(HERE / "build_casefile.py")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.html"
        engine = Path(td) / "engine.html"
        engine.write_text("<!doctype html><title>x</title>\n<!-- casefile-data: begin -->\n<!-- casefile-data: end -->\n", encoding="utf-8")

        def run(*extra):
            return subprocess.run([sys.executable, script] + list(extra), capture_output=True, text=True)
        r = run(str(FIX / "bad-sources.csv"), str(FIX / "bad-claims.csv"), "--out", str(out), "--engine", str(engine), "--today", today)
        if r.returncode != 1 or out.exists() or "Nothing was written" not in r.stdout:
            problems.append("a ledger with errors should exit 1 and write nothing (exit %d, file written: %s)" % (r.returncode, out.exists()))
        r = run(str(FIX / "near-sources.csv"), str(FIX / "near-claims.csv"), "--out", str(out), "--engine", str(engine), "--today", today)
        if r.returncode != 0 or not out.exists():
            problems.append("the ledger of valid neighbours should build (exit %d: %s)" % (r.returncode, (r.stderr or r.stdout).strip()[:120]))
        elif '"claims":[{"id":"C1"' not in out.read_text(encoding="utf-8"):
            problems.append("the built page does not hold the ledger in its data block")
        first = out.read_bytes() if out.exists() else b""
        r = run(str(FIX / "near-sources.csv"), str(FIX / "near-claims.csv"), "--out", str(out), "--engine", str(engine), "--today", today)
        if first and out.read_bytes() != first:
            problems.append("two builds from the same inputs and the same --today differ")
        r = run(str(FIX / "near-sources.csv"), str(FIX / "near-claims.csv"), "--out", str(out), "--engine", str(engine), "--today", "20261009")
        if r.returncode != 2:
            problems.append("--today 20261009 should be refused with exit 2 (exit %d)" % r.returncode)
        r = run(str(FIX / "near-sources.csv"), str(FIX / "near-claims.csv"), "--out", str(out), "--bogus")
        if r.returncode != 2 or "Traceback" in r.stderr:
            problems.append("an unknown option should exit 2 with one line (exit %d)" % r.returncode)
        r = run(str(FIX / "near-claims.csv"), str(FIX / "near-claims.csv"), "--check-only")
        if r.returncode != 2 or "missing column" not in r.stderr:
            problems.append("a claims file given as the sources file should exit 2 naming the missing columns (exit %d)" % r.returncode)
        r = run(str(FIX / "near-sources.csv"), str(FIX / "near-claims.csv"), "--out", str(FIX / "near-claims.csv"), "--engine", str(engine))
        if r.returncode != 2:
            problems.append("--out naming an input file should be refused with exit 2 (exit %d)" % r.returncode)
        future = Path(td) / "future-sources.csv"
        future.write_text((FIX / "near-sources.csv").read_text(encoding="utf-8"), encoding="utf-8")
        r = run(str(future), str(FIX / "near-claims.csv"), "--check-only", "--today", "2026-10-08")
        if r.returncode != 1 or "is in the future" not in r.stdout:
            problems.append("a date one day after --today should be an error (exit %d)" % r.returncode)
        r = run(str(future), str(FIX / "near-claims.csv"), "--check-only", "--today", "2026-10-09")
        if r.returncode != 0:
            problems.append("a date equal to --today should be accepted (exit %d)" % r.returncode)
    return problems


def planted(expected, today):
    """Break the rules three ways in memory. The comparison must fail each time."""
    keep = (bc.FACT_TIERS, bc.OPEN_CLASSES, bc.split_ids)
    missed, lines = 0, []

    def lenient_split(cell):
        # Treats a claim's own id as if every partner listed it back.
        class Everything(list):
            def __contains__(self, item):
                return True
        return Everything(part.strip() for part in cell.split(";") if part.strip())
    plants = [
        ("aggregator sources allowed to carry a FACT", lambda: setattr(bc, "FACT_TIERS", keep[0] + ("aggregator",))),
        ("open insufficient-evidence conflicts no longer reported", lambda: setattr(bc, "OPEN_CLASSES", ("direct_conflict",))),
        ("a conflict recorded on one side accepted", lambda: setattr(bc, "split_ids", lenient_split)),
    ]
    for what, apply in plants:
        apply()
        try:
            problems, _ = compare_all(expected, today)
        except Exception as e:  # noqa: BLE001
            problems = ["the check crashed: %s" % str(e)[:80]]
        bc.FACT_TIERS, bc.OPEN_CLASSES, bc.split_ids = keep
        if problems:
            lines.append("PLANTED: caught. %s" % what)
            lines.append("    %s" % problems[0][:170])
            lines.append("    disagreements found: %d" % len(problems))
        else:
            missed += 1
            lines.append("PLANTED: NOT CAUGHT. %s" % what)
    return missed, lines


def main(argv):
    flags, opts, it = set(), {}, iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("test_rules_agree: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        else:
            print("test_rules_agree: unknown argument " + a, file=sys.stderr)
            return 2
    try:
        expected = json.loads((FIX / "expected.json").read_bytes().decode("utf-8-sig"))
        today = dt.date.fromisoformat(expected["today"])
    except (OSError, ValueError, KeyError) as e:
        print("test_rules_agree: cannot read fixtures/expected.json (%s)" % str(e)[:80], file=sys.stderr)
        return 2
    live = None
    if "--ledger-check" in opts:
        live = Path(opts["--ledger-check"])
        if not live.is_file():
            print("test_rules_agree: cannot read " + str(live), file=sys.stderr)
            return 2
    if "--planted" in flags:
        missed, lines = planted(expected, today)
        lines.append("RESULT: %s" % ("FAIL. %d planted failure(s) were not caught." % missed if missed else "PASS. 3 of 3 planted failures were caught."))
        print("\n".join(lines).encode("ascii", "replace").decode("ascii"))
        return 1 if missed else 0
    try:
        problems, lines = compare_all(expected, today, live)
    except RuntimeError as e:
        print("test_rules_agree: %s" % e, file=sys.stderr)
        return 2
    cli = command_line(expected["today"])
    lines.append("  %s  command line: refused ledger writes nothing, valid neighbour builds, bad arguments exit 2" % ("FAIL" if cli else "PASS"))
    problems += cli
    if "--json" in flags:
        text = json.dumps({"compared_live": bool(live), "problems": problems, "lines": lines}, indent=1, ensure_ascii=True)
    else:
        text = "\n".join(["test_rules_agree: build_casefile.py against ledger_check.py, with --today %s" % expected["today"]] + lines
                         + ["  DIFF  " + p for p in problems]
                         + ["RESULT: %s. %d disagreement(s)." % ("FAIL" if problems else "PASS", len(problems))])
        text = text.encode("ascii", "replace").decode("ascii")
    print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
