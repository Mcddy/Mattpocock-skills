#!/usr/bin/env python3
"""Check the engine's JavaScript logic against the Python references, outside any browser.

Usage:
  python test_logic.py [ENGINE.html] [--json]

ENGINE.html defaults to assets/engine.html. The script cuts out the section between the
"PURE LOGIC: BEGIN" and "PURE LOGIC: END" markers (which touches no page), runs it in Node, and
compares its answers with sm2.py and with the formula functions in validate_course.py.

What it enforces (exit 1 on any failure):
  - schedule: every grade sequence of length 1 to 5 (9330 sequences) and 300 random sequences of
    length 40 give the same repetition number, interval and E-Factor in JavaScript and in sm2.py
  - dates: adding days and validating dates agree with Python's calendar on 3000 random cases,
    and 20261009, 2026-02-30 and 2026-13-01 are refused while 2024-02-29 is accepted
  - formulas: 44 expressions over a grid of values give the same result, or both give no value;
    12 malformed formulas are refused by both; displayed formats agree
  - gates: for every count of correct answers out of 1 to 12 items at pass marks 50 to 100,
    JavaScript passes exactly when correct * 100 >= mark * items
  - backups: twelve hand-labelled envelopes get the expected verdict
  - five planted faults in the JavaScript are each caught by the comparison above
What it cannot tell: anything about the page itself. test_engine.py drives the page.

Needs Node (any version from 12). Standard library only on the Python side.
Exit codes: 0 everything agreed. 1 a disagreement. 2 bad arguments or unreadable input.
3 Node is not installed (prints NOT RUN).
"""
import datetime as dt
import itertools
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sm2 as ref  # noqa: E402
import validate_course as vc  # noqa: E402

LOGIC = re.compile(r"/\* === PURE LOGIC: BEGIN[^\n]*\*/(.*?)/\* === PURE LOGIC: END === \*/", re.S)
HARNESS = r"""
var fs = require('fs');
var Logic = new Function(fs.readFileSync(process.argv[2], 'utf8') + '; return Logic;')();
var job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
var out = {};
out.sm2 = job.sequences.map(function (seq) {
  var c = Logic.newCard();
  return seq.map(function (q) { c = Logic.sm2(c, q); return [c.n, c.interval, c.ef100]; });
});
out.dates = job.dates.map(function (d) { return Logic.addDays(d[0], d[1]); });
out.isdate = job.isdate.map(function (s) { return Logic.isDate(s); });
out.formulas = job.formulas.map(function (f) { return job.envs.map(function (e) { return Logic.evalFormula(f, e); }); });
out.badformulas = job.badformulas.map(function (f) { return Logic.compileFormula(f).ok; });
out.formats = job.formats.map(function (x) { return Logic.formatValue(x[0], x[1]); });
out.gates = job.gates.map(function (g) {
  var items = [], answers = {}, i;
  for (i = 0; i < g[0]; i++) { items.push({id: 'i' + i, objective: 'o', options: [{correct: true}, {correct: false}]}); answers['i' + i] = i < g[1] ? 0 : 1; }
  return Logic.scoreGate({objectives: [{id: 'o'}], gate: {items: items}}, answers, g[2]).passed;
});
out.envelopes = job.envelopes.map(function (t) { var r = Logic.readEnvelope(t, job.course); return r.ok ? r.mode : r.code; });
out.refused = [6, -1, 2.5, '4', true, null].map(function (q) { try { Logic.sm2(Logic.newCard(), q); return false; } catch (e) { return true; } });
process.stdout.write(JSON.stringify(out));
"""

FORMULAS = ["x", "x + y", "x - y * 2", "(x - y) * 2", "x / y", "2 ^ x", "2 ^ (8 - x)", "-2 ^ 2", "2 ^ 3 ^ 2", "-x ^ 2", "2 ^ -1", "x * -y", "floor(x / y)", "ceil(x / y)",
            "round(x / y)", "round(-2.5)", "round(2.5)", "abs(x - y)", "min(x, y)", "max(x, y)", "mod(x, y)", "mod(-x, y)", "sqrt(x)", "sqrt(x - y)", "log2(x)", "log2(0)",
            "band(x, y)", "band(77, 192)", "band(x, 0 - 1)", "256 - 2^(8 - min(8, max(0, x - 8)))", "floor(x / 64) * 64 + 64 - 1", "2^(32 - x) - 2", "(y - x) / x * 100",
            "x / 0", "1 / (x - x)", "x + z", "0.1 + 0.2", "1.5 * 4", "10 / 4", "max(min(x, 3), 1) ^ 2", "x - -y", "((x))", "3", "mod(x, 0)"]
BAD_FORMULAS = ["", "2 ** 3", "alert(1)", "a.b", "1 +", "min(1)", "floor", "x y", "(x", "x)", "1e3", "x; y"]
ENVS = [{"x": x, "y": y} for x in (0, 1, 2, 5, 8, 26, 77, 255) for y in (1, 3, 4, 64)]
FORMATS = [(v, f) for v in (0, 1, 7, 77, 255, 256, 0.345, 0.335, 2.5, -0.2, -0.04, 36.0, 1022.5, -3) for f in ("int", "fixed1", "fixed2", "bin8", "bin")]
MUTANTS = [
    ("a lapse changes the E-Factor", "if (q < 3) return {n: 1, interval: 1, ef100: ef100};", "if (q < 3) return {n: 1, interval: 1, ef100: Math.max(MIN_EF100, ef100 + 10 - (5 - q) * (8 + (5 - q) * 2))};"),
    ("interval rounded to nearest, not up", "Math.floor((interval * ef100 + 99) / 100)", "Math.round(interval * ef100 / 100)"),
    ("the second interval is 4 days, not 6", "else if (n === 2) interval = 6;", "else if (n === 2) interval = 4;"),
    ("the pass mark is exclusive", "passed: items.length > 0 && correct * 100 >= threshold * items.length", "passed: items.length > 0 && correct * 100 > threshold * items.length"),
    ("unary minus binds tighter than a power", "if (peek() === '-') { pos++; return {k: 'neg', a: unary()}; }\n      return power();", "if (peek() === '-') { pos++; return {k: 'neg', a: primary()}; }\n      return power();"),
]


def build_job():
    rng = random.Random(20261009)
    seqs = [list(s) for n in range(1, 6) for s in itertools.product(range(6), repeat=n)]
    seqs += [[rng.choice((0, 1, 2, 3, 3, 4, 4, 4, 5, 5)) for _ in range(40)] for _ in range(300)]
    base = dt.date(1999, 12, 25)
    dates = []
    for _ in range(3000):
        d = base + dt.timedelta(days=rng.randrange(0, 40000))
        dates.append([d.isoformat(), rng.choice((0, 1, 6, 16, 365, 366, 1461, 36500, rng.randrange(0, 3000)))])
    isdate = ["2026-10-09", "2024-02-29", "2026-02-29", "2026-02-30", "2026-13-01", "20261009", "2026-1-9", "2026-10-9", "0000-01-01", "2026-00-10", "2026-10-00", "2026-10-32", " 2026-10-09", "2026-10-09T00:00"]
    course = {"id": "c", "version": 2, "modules": [{"id": "m1", "status": "ready", "objectives": [{"id": "o1"}], "cards": [{"id": "k1"}], "quiz": [], "worked": []}]}
    data = {"course_version": 2, "day_high": "2026-10-09", "modules": {"m1": {"gate": {"attempts": 1, "passed_on": "2026-10-09", "last": {"date": "2026-10-09", "correct": 2, "total": 2, "passed": True}}}},
            "objectives": {"o1": {"demonstrated_on": "2026-10-09", "gate": [2, 2, "2026-10-09"], "recalled_on": None, "misses": {"gate": 0, "quiz": 0, "cards": 0}}},
            "cards": {"k1": {"n": 2, "interval": 6, "ef100": 250, "due": "2026-10-15", "last": "2026-10-09", "reviews": 2, "lapses": 0, "again": None}},
            "activity": {"points": 12, "days": {"2026-10-09": 3}, "counts": {"tabs": 1}}}

    def env(**over):
        e = {"app": "preceptor-course", "schema": 1, "content_id": "c@2", "saved_at": "2026-10-09T01:00:00Z", "data": json.loads(json.dumps(data))}
        for k, v in over.items():
            e[k] = v
        return e

    def with_data(change, cid="c@2"):
        e = env(content_id=cid)
        change(e["data"])
        return json.dumps(e)

    envelopes = [
        (json.dumps(env()), "exact"),
        (with_data(lambda d: (d.update(course_version=1), d["cards"].update(gone={"n": 1, "interval": 1, "ef100": 250, "due": "2026-10-10", "last": "2026-10-09", "reviews": 1, "lapses": 0, "again": None})), "c@1"), "mapped"),
        ("", "empty"),
        ("{\"app\": \"preceptor-course\", \"schema\": 1, \"conte", "not-json"),
        ("[]", "not-object"),
        (json.dumps(env(app="other")), "wrong-app"),
        (json.dumps(env(schema=2)), "newer-schema"),
        (json.dumps(env(schema="1")), "bad-schema"),
        (json.dumps(env(content_id="d@2")), "other-course"),
        (with_data(lambda d: d.update(course_version=3), "c@3"), "newer-course"),
        (with_data(lambda d: d["cards"]["k1"].update(ef100=129)), "bad-data"),
        (with_data(lambda d: d["cards"]["k1"].update(ef100=130)), "exact"),
        (with_data(lambda d: d["cards"]["k1"].update(due="20261015")), "bad-data"),
        (with_data(lambda d: d["cards"]["k1"].update(interval=36501)), "bad-data"),
        (with_data(lambda d: d["cards"]["k1"].update(interval=36500)), "exact"),
        (with_data(lambda d: d["activity"].update(points=True)), "bad-data"),
        (with_data(lambda d: d["modules"].update(ghost={})), "bad-data"),
    ]
    gates = [[n, k, thr] for n in range(1, 13) for k in range(0, n + 1) for thr in (50, 60, 70, 75, 80, 90, 100)]
    return {"sequences": seqs, "dates": dates, "isdate": isdate, "formulas": FORMULAS, "badformulas": BAD_FORMULAS, "envs": ENVS,
            "formats": [[v, f] for v, f in FORMATS], "gates": gates, "envelopes": [e[0] for e in envelopes], "course": course}, [e[1] for e in envelopes]


def py_isdate(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    try:
        dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def compare(out, job, verdicts):
    """Return a list of (check name, ok, detail)."""
    res = []
    bad = None
    for seq, got in zip(job["sequences"], out["sm2"]):
        n, i, e = 0, 0, ref.START_EF100
        for step, q in enumerate(seq):
            n, i, e = ref.sm2(n, i, e, q)
            if got[step] != [n, i, e]:
                bad = "grades %s: JavaScript gives n %d, interval %d, E-Factor %d at step %d; sm2.py gives %d, %d, %d" % (seq[:step + 1], got[step][0], got[step][1], got[step][2], step + 1, n, i, e)
                break
        if bad:
            break
    res.append(("schedule agrees with sm2.py on %d grade sequences" % len(job["sequences"]), bad is None, bad or ""))
    res.append(("grades 6, -1, 2.5, text, true and null are refused", all(out["refused"]), "accepted: %s" % out["refused"]))
    bad = [(d, n, g) for (d, n), g in zip(job["dates"], out["dates"]) if (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat() != g]
    res.append(("adding days agrees with the calendar on %d cases" % len(job["dates"]), not bad, "first: %s" % (bad[:1],)))
    bad = [s for s, g in zip(job["isdate"], out["isdate"]) if py_isdate(s) != g]
    res.append(("date validation agrees on %d samples (2024-02-29 accepted; 2026-02-30 and 20261009 refused)" % len(job["isdate"]),
                not bad and out["isdate"][1] is True and out["isdate"][3] is False and out["isdate"][5] is False, "differs on %s" % bad))
    bad = []
    for f, row in zip(job["formulas"], out["formulas"]):
        for env, g in zip(job["envs"], row):
            w = vc.formula_eval(f, env)
            if not close(w, g):
                bad.append("%s at x=%s y=%s: JavaScript %s, Python %s" % (f, env["x"], env["y"], g, w))
    res.append(("%d formulas agree at %d settings each" % (len(job["formulas"]), len(job["envs"])), not bad, "; ".join(bad[:2])))
    py_ok = []
    for f in job["badformulas"]:
        try:
            vc.formula_compile(f)
            py_ok.append(True)
        except vc.FormulaError:
            py_ok.append(False)
    res.append(("%d malformed formulas are refused by both" % len(job["badformulas"]), not any(py_ok) and not any(out["badformulas"]),
                "accepted by Python: %s; by JavaScript: %s" % ([f for f, o in zip(job["badformulas"], py_ok) if o], [f for f, o in zip(job["badformulas"], out["badformulas"]) if o])))
    bad = ["%s as %s: JavaScript %s, Python %s" % (v, f, g, vc.format_value(float(v), f)) for (v, f), g in zip(job["formats"], out["formats"]) if vc.format_value(float(v), f) != g]
    res.append(("%d displayed formats agree" % len(job["formats"]), not bad, "; ".join(bad[:2])))
    bad = ["%d of %d at %d percent: JavaScript %s" % (k, n, thr, g) for (n, k, thr), g in zip(job["gates"], out["gates"]) if g != (k * 100 >= thr * n)]
    res.append(("gate pass rule agrees on %d cases, including every exact pass mark" % len(job["gates"]), not bad, "; ".join(bad[:2])))
    bad = ["envelope %d: expected %s, got %s" % (i + 1, w, g) for i, (w, g) in enumerate(zip(verdicts, out["envelopes"])) if w != g]
    res.append(("%d labelled backups get the expected verdict (E-Factor 1.30 and interval 36500 accepted; 1.29 and 36501 refused)" % len(verdicts), not bad, "; ".join(bad[:3])))
    return res


def run_node(node, logic_src, job, tmp):
    (tmp / "logic.js").write_text(logic_src, encoding="utf-8")
    (tmp / "harness.js").write_text(HARNESS, encoding="utf-8")
    (tmp / "job.json").write_text(json.dumps(job), encoding="utf-8")
    p = subprocess.run([node, str(tmp / "harness.js"), str(tmp / "logic.js"), str(tmp / "job.json")], capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stderr.strip().splitlines() or ["node failed"])[-1][:200]
    return json.loads(p.stdout), ""


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a == "--json":
            flags.add(a)
        elif a.startswith("--"):
            print("test_logic: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) > 1:
        print("test_logic: expected at most one engine file", file=sys.stderr)
        return 2
    path = Path(args[0]) if args else HERE.parent / "assets" / "engine.html"
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        print("test_logic: cannot read %s: %s" % (path, e), file=sys.stderr)
        return 2
    m = LOGIC.search(text)
    if not m:
        print("test_logic: %s has no PURE LOGIC section" % path, file=sys.stderr)
        return 2
    logic = m.group(1)
    if re.search(r"\b(document|window|localStorage|navigator)\b", logic):
        print("test_logic: the PURE LOGIC section refers to the page (document, window, localStorage or navigator); it must not", file=sys.stderr)
        return 1
    node = shutil.which("node")
    if not node:
        emit("NOT RUN: Node is not installed, so the JavaScript logic was not compared with the Python references.")
        return 3
    job, verdicts = build_job()
    tmp = Path(tempfile.mkdtemp(prefix="preceptor-logic-"))
    try:
        out, err = run_node(node, logic, job, tmp)
        if out is None:
            results = [("the logic section runs in Node", False, err)]
        else:
            results = compare(out, job, verdicts)
            for label, old, new in MUTANTS:
                if logic.count(old) != 1:
                    results.append(("planted fault caught: " + label, False, "the fault could not be planted: its target text occurs %d times" % logic.count(old)))
                    continue
                mout, merr = run_node(node, logic.replace(old, new), job, tmp)
                caught = [r for r in compare(mout, job, verdicts) if not r[1]] if mout is not None else [("", False, merr)]
                results.append(("planted fault caught: " + label, bool(caught), caught[0][2][:150] if caught else "no comparison noticed this fault"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [r for r in results if not r[1]]
    if "--json" in flags:
        emit(json.dumps({"checks": [{"check": r[0], "ok": r[1], "detail": r[2]} for r in results], "failed": len(failed), "total": len(results)}, indent=1, ensure_ascii=True))
    else:
        for name, ok, detail in results:
            shown = detail if (detail and (not ok or name.startswith("planted"))) else ""
            emit("%-5s %s%s" % ("PASS" if ok else "FAIL", name, ("\n      " + shown) if shown else ""))
        emit("RESULT: %s. %d of %d checks passed. This compares arithmetic and validation, not the page." % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
