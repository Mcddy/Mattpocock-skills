#!/usr/bin/env python3
"""The SM-2 review schedule as one pure function, with a self-test and a trace mode. Standard library only.

Usage:
  python sm2.py --selftest [--json]
  python sm2.py --trace "5,4,2,3,5" [--start YYYY-MM-DD] [--json]

This is the reference the course engine's JavaScript is tested against. It follows algorithm SM-2 as
published in the SuperMemo archive ("Application of a computer to improve the results obtained in
working with the SuperMemo method", read 9 Oct 2026):

  - a card starts with E-Factor 2.5
  - grades q are whole numbers 0 to 5
  - intervals in days: I(1) = 1, I(2) = 6, and for n > 2: I(n) = I(n-1) * EF, rounded up
  - after a grade of 3 or more: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)), floor 1.3
  - after a grade below 3: repetitions start again from I(1) and the E-Factor is not changed
  - a card graded below 4 is repeated the same day until it scores at least 4 (reported here as
    "repeat today"; those extra repeats do not change the schedule)

Representation. The E-Factor is held as a whole number of hundredths (2.5 is 250), so the arithmetic
is exact and the Python and JavaScript versions cannot drift apart. Every published E-Factor change
is a whole number of hundredths: +10 for grade 5, 0 for grade 4, -14 for grade 3.

Two readings the publication leaves open, fixed here and stated in references/scheduling.md:
  1. The next interval is computed with the E-Factor as updated by the grade just given.
  2. After a lapse the card waits I(1) = 1 day, and the next successful review moves it to I(2) = 6.
One deliberate departure: an interval is capped at 36500 days so a due date always exists. The
published algorithm has no cap. The cap is first reached at the tenth straight grade of 5.

--trace input: grades separated by commas, each a single digit 0 to 5. Each review is assumed to
happen on the day it falls due. With --start, due dates are printed as real calendar dates.

What --selftest enforces (exit 1 on any failure):
  - six sequences worked out by hand match the function, step by step
  - the whole-number E-Factor change equals the published formula for every grade
  - a lapse never changes the E-Factor; the E-Factor never falls below 1.30
  - refusals sit beside their valid neighbours: grade 5 accepted and 6 refused, 0 accepted and -1
    refused, and true, "4" and 4.0 refused as not whole-number grades
  - four deliberately wrong schedules (planted mutants) are each caught by the hand-worked table
What it cannot tell: whether this schedule suits a given learner or subject. It checks arithmetic.

Exit codes: 0 ran and nothing failed. 1 a self-test check failed. 2 bad arguments.
"""
import datetime as dt
import json
import re
import sys

START_EF100 = 250
MIN_EF100 = 130
MAX_INTERVAL = 36500
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
FLAGS = {"--selftest", "--json"}
VALUES = {"--trace", "--start"}


def is_grade(q):
    return isinstance(q, int) and not isinstance(q, bool) and 0 <= q <= 5


def ef_change100(q):
    """Published E-Factor change for grade q, in hundredths. Whole-number arithmetic."""
    return 10 - (5 - q) * (8 + (5 - q) * 2)


def sm2(n, interval, ef100, q):
    """One review. n is the index of the interval the card is waiting through (0 for a new card).

    Returns (n, interval_days, ef100). Pure: no clock, no input or output.
    """
    if not is_grade(q):
        raise ValueError("grade must be a whole number from 0 to 5")
    for name, v in (("n", n), ("interval", interval), ("ef100", ef100)):
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise ValueError("%s must be a whole number, zero or more" % name)
    if q < 3:
        return 1, 1, ef100
    ef100 = max(MIN_EF100, ef100 + ef_change100(q))
    n += 1
    if n == 1:
        interval = 1
    elif n == 2:
        interval = 6
    else:
        interval = min(MAX_INTERVAL, (interval * ef100 + 99) // 100)
    return n, interval, ef100


def trace(grades, start=None):
    """Run a new card through the grades. Returns one dict per review."""
    n, interval, ef100 = 0, 0, START_EF100
    day, rows = start, []
    for i, q in enumerate(grades):
        n, interval, ef100 = sm2(n, interval, ef100, q)
        row = {"review": i + 1, "grade": q, "n": n, "interval": interval, "ef100": ef100,
               "e_factor": "%d.%02d" % divmod(ef100, 100), "repeat_today": q < 4}
        if day is not None:
            row["on"] = day.isoformat()
            try:
                day = day + dt.timedelta(days=interval)
                row["due"] = day.isoformat()
            except OverflowError:
                row["due"] = None
                day = None
        rows.append(row)
    return rows


# Hand-worked sequences. Each entry: grades, then the expected (interval, ef100) after each grade.
# Worked on paper from the published rules; see references/scheduling.md for the arithmetic.
HAND = [
    ("all perfect", [5, 5, 5, 5, 5], [(1, 260), (6, 270), (17, 280), (50, 290), (150, 300)]),
    ("all correct after hesitation", [4, 4, 4, 4], [(1, 250), (6, 250), (15, 250), (38, 250)]),
    ("all correct with difficulty", [3] * 10,
     [(1, 236), (6, 222), (13, 208), (26, 194), (47, 180), (79, 166), (121, 152), (167, 138), (218, 130), (284, 130)]),
    ("a lapse in the middle", [5, 4, 2, 3, 5], [(1, 260), (6, 260), (1, 260), (6, 246), (16, 256)]),
    ("nothing but lapses", [0, 1, 2], [(1, 250), (1, 250), (1, 250)]),
    ("recover after a lapse", [4, 4, 4, 1, 4, 4], [(1, 250), (6, 250), (15, 250), (1, 250), (6, 250), (15, 250)]),
]


def _mutant_lapse_changes_ef(n, interval, ef100, q):
    if q < 3:
        return 1, 1, max(MIN_EF100, ef100 + ef_change100(q))
    return sm2(n, interval, ef100, q)


def _mutant_rounds_to_nearest(n, interval, ef100, q):
    n2, i2, e2 = sm2(n, interval, ef100, q)
    if q >= 3 and n2 > 2:
        i2 = int(interval * e2 / 100.0 + 0.5)
    return n2, i2, e2


def _mutant_no_floor(n, interval, ef100, q):
    if q < 3:
        return 1, 1, ef100
    e2 = ef100 + ef_change100(q)
    n2 = n + 1
    i2 = 1 if n2 == 1 else 6 if n2 == 2 else (interval * e2 + 99) // 100
    return n2, i2, e2


def _mutant_old_ef_for_interval(n, interval, ef100, q):
    n2, i2, e2 = sm2(n, interval, ef100, q)
    if q >= 3 and n2 > 2:
        i2 = (interval * ef100 + 99) // 100
    return n2, i2, e2


MUTANTS = [("a lapse changes the E-Factor", _mutant_lapse_changes_ef),
           ("interval rounded to nearest, not up", _mutant_rounds_to_nearest),
           ("no 1.30 floor on the E-Factor", _mutant_no_floor),
           ("interval uses the E-Factor from before the grade", _mutant_old_ef_for_interval)]


def run_table(fn):
    """Return the list of mismatches between fn and the hand-worked table."""
    bad = []
    for name, grades, want in HAND:
        n, interval, ef100 = 0, 0, START_EF100
        for i, q in enumerate(grades):
            n, interval, ef100 = fn(n, interval, ef100, q)
            if (interval, ef100) != want[i]:
                bad.append("%s: after grade %d at step %d expected interval %d and E-Factor %d.%02d, got %d and %d.%02d"
                           % ((name, q, i + 1, want[i][0]) + divmod(want[i][1], 100) + (interval,) + divmod(ef100, 100)))
                break
    return bad


def selftest():
    results = []

    def record(name, ok, detail=""):
        results.append({"check": name, "ok": bool(ok), "detail": detail})

    bad = run_table(sm2)
    record("%d hand-worked sequences match (%d steps)" % (len(HAND), sum(len(g) for _, g, _ in HAND)), not bad, "; ".join(bad))
    diffs = [q for q in range(6) if round((0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)) * 100) != ef_change100(q)]
    record("whole-number E-Factor change equals the published formula for grades 0 to 5", not diffs, "differs at %s" % diffs)
    lapse_ok = all(sm2(n, i, e, q)[2] == e and sm2(n, i, e, q)[:2] == (1, 1)
                   for n in range(0, 8) for i in (0, 1, 6, 15, 400) for e in (130, 180, 250, 320) for q in (0, 1, 2))
    record("a grade below 3 gives interval 1 and leaves the E-Factor unchanged (480 states)", lapse_ok)
    n, i, e, low = 0, 0, START_EF100, START_EF100
    for _ in range(40):
        n, i, e = sm2(n, i, e, 3)
        low = min(low, e)
    record("E-Factor never falls below 1.30 over 40 grades of 3", low == MIN_EF100, "lowest was %d" % low)
    pairs = []
    for good, refused in ((5, 6), (0, -1)):
        try:
            sm2(0, 0, START_EF100, good)
            ok_good = True
        except ValueError:
            ok_good = False
        try:
            sm2(0, 0, START_EF100, refused)
            ok_bad = False
        except ValueError:
            ok_bad = True
        pairs.append(ok_good and ok_bad)
    record("grade 5 accepted and 6 refused; grade 0 accepted and -1 refused", all(pairs))
    coerced = []
    for v in (True, "4", 4.0, None, float("nan")):
        try:
            sm2(0, 0, START_EF100, v)
            coerced.append(repr(v))
        except ValueError:
            pass
    record("true, text, 4.0, null and NaN are refused as grades", not coerced, "accepted: " + ", ".join(coerced))
    n, i, e = 0, 0, START_EF100
    seen = []
    for _ in range(12):
        n, i, e = sm2(n, i, e, 5)
        seen.append(i)
    record("interval is capped at 36500 days and 16698 (the ninth straight 5) is not", seen[8] == 16698 and seen[9] == MAX_INTERVAL and seen[11] == MAX_INTERVAL,
           "saw %s" % seen)
    for name, fn in MUTANTS:
        caught = run_table(fn)
        record("planted mutant caught: " + name, bool(caught), "" if caught else "the table did not notice this mutant")
    return results


def parse_date(text):
    if not isinstance(text, str) or not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


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
                print("sm2: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("sm2: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if args or (("--selftest" in flags) == ("--trace" in opts)):
        print("sm2: give exactly one of --selftest or --trace \"5,4,2\" (see the docstring: python sm2.py with no arguments)" if (args or flags or opts) else __doc__,
              file=sys.stderr if (args or flags or opts) else sys.stdout)
        return 2
    if "--selftest" in flags:
        if "--start" in opts:
            print("sm2: --start only applies to --trace", file=sys.stderr)
            return 2
        results = selftest()
        failed = [r for r in results if not r["ok"]]
        if "--json" in flags:
            emit(json.dumps({"checks": results, "failed": len(failed), "total": len(results)}, indent=1, ensure_ascii=True))
        else:
            for r in results:
                emit("%-5s %s%s" % ("PASS" if r["ok"] else "FAIL", r["check"], ("  [" + r["detail"] + "]") if (r["detail"] and not r["ok"]) else ""))
            emit("RESULT: %s. %d of %d checks passed." % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
        return 1 if failed else 0
    raw = opts["--trace"]
    if not re.fullmatch(r"\s*[0-5]\s*(,\s*[0-5]\s*)*", raw):
        print("sm2: --trace needs grades 0 to 5 separated by commas, for example \"5,4,2,3,5\"", file=sys.stderr)
        return 2
    grades = [int(x) for x in raw.replace(" ", "").split(",")]
    start = None
    if "--start" in opts:
        start = parse_date(opts["--start"])
        if start is None:
            print("sm2: --start needs a real date written YYYY-MM-DD", file=sys.stderr)
            return 2
    rows = trace(grades, start)
    if "--json" in flags:
        emit(json.dumps({"start_e_factor": "2.50", "reviews": rows}, indent=1, ensure_ascii=True))
        return 0
    emit("sm2 trace: new card, E-Factor 2.50, %d review(s), each done on the day it falls due" % len(rows))
    for r in rows:
        line = "  review %-2d" % r["review"]
        if "on" in r:
            line += " on %s" % r["on"]
        line += "  grade %d  n %-2d interval %-5d E-Factor %s" % (r["grade"], r["n"], r["interval"], r["e_factor"])
        if "on" in r:
            line += "  due %s" % (r["due"] or "beyond the calendar")
        line += "  repeat today: %s" % ("yes" if r["repeat_today"] else "no")
        emit(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
