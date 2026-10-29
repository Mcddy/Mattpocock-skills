#!/usr/bin/env python3
"""Tests for analyse_responses.py, with hand-worked expected values and planted failures.
Standard library only.

Usage:
  python test_analyse_responses.py                 run every test against the script beside this file
  python test_analyse_responses.py --script PATH   run every test against another copy of the script
  python test_analyse_responses.py --only NAME     run one test
  python test_analyse_responses.py --planted       build broken copies of the script in a temporary
                                                   folder and show the named test fails on each

Every statistic is checked against a value worked by hand in a comment beside the test, from the
definitions in the script's docstring, so a test does not depend on the code it checks. All
fixtures are SYNTHETIC, are written to a temporary folder, and are removed afterwards.

What it enforces: every test passes (exit 0) or a test fails (exit 1). With --planted: the real
script passes every test AND each broken copy is caught by the test named for it; otherwise exit 1.
What it cannot tell: whether a set of findings written from the output is fair to the respondents.

Exit codes: 0 all passed. 1 a test failed, or a planted failure was not caught. 2 bad arguments.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
Z = 1.959964          # standard normal 97.5th percentile, from tables (1.96 to two places)
Z2 = 3.841459         # Z squared
_COUNT = [0]


def load_module(path):
    _COUNT[0] += 1
    spec = importlib.util.spec_from_file_location("analyse_under_test_%d" % _COUNT[0], str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Ctx:
    def __init__(self, script):
        self.script = Path(script)
        self.mod = load_module(self.script)
        self.tmp = Path(tempfile.mkdtemp(prefix="analyse_test_"))
        self.n = 0

    def path(self, suffix):
        self.n += 1
        return self.tmp / ("f%03d%s" % (self.n, suffix))

    def csv(self, text, raw=None):
        p = self.path(".csv")
        p.write_bytes(raw if raw is not None else text.encode("utf-8"))
        return p

    def inst(self, obj):
        p = self.path(".json")
        p.write_bytes(json.dumps(obj).encode("utf-8"))
        return p

    def cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, "-B", str(self.script)] + [str(a) for a in args], capture_output=True, env=env, timeout=120)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    def js(self, *args):
        code, out, err = self.cli(*(list(args) + ["--json"]))
        try:
            return code, json.loads(out)
        except ValueError:
            raise AssertionError("no JSON came back: exit %d, stdout %r, stderr %r" % (code, out[:200], err[:200]))

    def close(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)


def near(a, b, tol=5e-6):
    return abs(a - b) <= tol


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def question(result, qid):
    return next(q for q in result["questions"] if q["id"] == qid)


def option(q, name):
    return next(o for o in q["options"] if o["option"] == name)


# ---------------------------------------------------------------- intervals

def test_wilson_interval_hand_worked(c):
    w = c.mod.wilson
    z = c.mod.z_for(95)
    expect(near(z, Z, 1e-6), "z for 95 per cent is %r, expected 1.959964" % z)
    # 3 of 4. p = 0.75, n = 4, z^2 = 3.841459.
    #   centre = (0.75 + 3.841459 / 8) / (1 + 3.841459 / 4) = (0.75 + 0.480182) / 1.960365 = 0.627527
    #   half   = 1.959964 * sqrt(0.75 * 0.25 / 4 + 3.841459 / 64) / 1.960365
    #          = 1.959964 * sqrt(0.046875 + 0.060023) / 1.960365 = 1.959964 * 0.326953 / 1.960365 = 0.326886
    #   interval = 0.627527 - 0.326886, 0.627527 + 0.326886 = 0.300641, 0.954413
    lo, hi = w(3, 4, z)
    expect(near(lo, 0.300641) and near(hi, 0.954413), "Wilson 3 of 4 gave %.6f, %.6f; expected 0.300641, 0.954413" % (lo, hi))
    # 5 of 9. p = 0.555556.
    #   centre = (0.555556 + 3.841459 / 18) / (1 + 3.841459 / 9) = (0.555556 + 0.213414) / 1.426829 = 0.538936
    #   half   = 1.959964 * sqrt(0.555556 * 0.444444 / 9 + 3.841459 / 324) / 1.426829
    #          = 1.959964 * sqrt(0.027435 + 0.011856) / 1.426829 = 1.959964 * 0.198220 / 1.426829 = 0.272285
    #   interval = 0.266651, 0.811221
    lo, hi = w(5, 9, z)
    expect(near(lo, 0.266651) and near(hi, 0.811221), "Wilson 5 of 9 gave %.6f, %.6f; expected 0.266651, 0.811221" % (lo, hi))
    # 0 of 10: the lower limit is exactly 0, the upper is z^2 / (n + z^2) = 3.841459 / 13.841459 = 0.277533.
    lo, hi = w(0, 10, z)
    expect(lo == 0.0 and near(hi, 0.277533), "Wilson 0 of 10 gave %r, %r" % (lo, hi))
    # 10 of 10: the upper limit is exactly 1, the lower is n / (n + z^2) = 10 / 13.841459 = 0.722467.
    lo, hi = w(10, 10, z)
    expect(hi == 1.0 and near(lo, 0.722467), "Wilson 10 of 10 gave %r, %r" % (lo, hi))
    expect(w(0, 0, z) is None, "nobody in the denominator must give no interval, not a number")
    # A 90 per cent interval is narrower than a 95 per cent one: z = 1.644854.
    #   3 of 4: z^2 = 2.705543. centre = (0.75 + 0.338193) / 1.676386 = 0.649130
    #   half = 1.644854 * sqrt(0.046875 + 2.705543 / 64) / 1.676386 = 1.644854 * sqrt(0.089149) / 1.676386 = 0.292962
    lo, hi = w(3, 4, c.mod.z_for(90))
    expect(near(lo, 0.356168, 2e-5) and near(hi, 0.942092, 2e-5), "Wilson 90 per cent for 3 of 4 gave %.6f, %.6f" % (lo, hi))


def test_difference_interval_hand_worked(c):
    z = c.mod.z_for(95)
    # 3 of 4 against 5 of 9, with the Wilson intervals worked above: (0.300641, 0.954413) and (0.266651, 0.811221).
    #   d = 0.75 - 0.555556 = 0.194444
    #   lower = d - sqrt((p1 - l1)^2 + (u2 - p2)^2) = 0.194444 - sqrt(0.449359^2 + 0.255665^2)
    #         = 0.194444 - sqrt(0.201924 + 0.065365) = 0.194444 - 0.517000 = -0.322556
    #   upper = d + sqrt((u1 - p1)^2 + (p2 - l2)^2) = 0.194444 + sqrt(0.204413^2 + 0.288905^2)
    #         = 0.194444 + sqrt(0.041785 + 0.083466) = 0.194444 + 0.353908 = 0.548352
    d, lo, hi = c.mod.newcombe(3, 4, 5, 9, z)
    expect(near(d, 0.194444) and near(lo, -0.322556) and near(hi, 0.548352), "Newcombe 3/4 against 5/9 gave %.6f, %.6f, %.6f" % (d, lo, hi))
    # Second form of the same interval, as printed in trial analysis plans that cite Newcombe (1998):
    #   lower = d - z * sqrt(l1 (1 - l1) / n1 + u2 (1 - u2) / n2), upper = d + z * sqrt(u1 (1 - u1) / n1 + l2 (1 - l2) / n2).
    # With the same numbers: lower = 0.194444 - 1.959964 * sqrt(0.300641 * 0.699359 / 4 + 0.811221 * 0.188779 / 9)
    #   = 0.194444 - 1.959964 * sqrt(0.052564 + 0.017016) = 0.194444 - 1.959964 * 0.263780 = -0.322555
    import math
    l1, u1 = c.mod.wilson(3, 4, z)
    l2, u2 = c.mod.wilson(5, 9, z)
    alt_lo = 0.194444 - 1.959964 * math.sqrt(l1 * (1 - l1) / 4 + u2 * (1 - u2) / 9)
    alt_hi = 0.194444 + 1.959964 * math.sqrt(u1 * (1 - u1) / 4 + l2 * (1 - l2) / 9)
    expect(near(lo, alt_lo, 2e-6) and near(hi, alt_hi, 2e-6), "the two published forms of the interval disagree")
    # 56 of 70 against 48 of 80: d = 0.8 - 0.6 = 0.2. Newcombe's own worked example for method 10 gives
    # 0.0524 to 0.3339. (That table was not fetched in the authoring session; the two figures are as the
    # author recalls them, so this line is corroboration and the hand-worked case above is the check.)
    d, lo, hi = c.mod.newcombe(56, 70, 48, 80, z)
    expect(near(d, 0.2, 1e-12) and near(lo, 0.0524, 5e-5) and near(hi, 0.3339, 5e-5), "Newcombe 56/70 against 48/80 gave %.4f to %.4f" % (lo, hi))
    # Equal proportions: the difference is 0 and the interval straddles it symmetrically.
    d, lo, hi = c.mod.newcombe(5, 10, 5, 10, z)
    expect(d == 0.0 and near(lo, -hi, 1e-12) and lo < 0 < hi, "equal proportions must give a symmetric interval around zero")
    expect(c.mod.newcombe(1, 0, 1, 2, z) is None, "an empty group must give no interval")


def test_compare_two_groups_end_to_end(c):
    # Group A: 3 of 4 said Yes. Group B: 5 of 9 said Yes. One respondent has no group and is left out.
    # Difference A minus B = +19 points; interval -32 to +55 points (worked in the test above).
    # Overlap of the two Wilson intervals is 0.300641 to 0.811221 = 0.510580 wide; the narrower interval
    # (B) is 0.544570 wide; 0.510580 / 0.544570 = 0.94, so they "overlap almost entirely".
    rows = ["respondent,grp,ans"] + ["a%d,A,%s" % (i, "Yes" if i < 3 else "No") for i in range(4)]
    rows += ["b%d,B,%s" % (i, "Yes" if i < 5 else "No") for i in range(9)] + ["x1,,Yes"]
    data = c.csv("\n".join(rows) + "\n")
    inst = c.inst({"questions": [{"id": "grp", "type": "single", "options": ["A", "B"]}, {"id": "ans", "type": "single", "options": ["Yes", "No"]}]})
    code, r = c.js(data, "--instrument", inst, "--compare", "ans=Yes", "--by", "grp")
    cmp_ = r["compare"]
    g = {x["group"]: x["chose"] for x in cmp_["groups"]}
    expect(code == 0 and (g["A"]["count"], g["A"]["n"], g["B"]["count"], g["B"]["n"]) == (3, 4, 5, 9), "group counts are wrong: %r" % g)
    d = cmp_["difference"]
    expect(d["points"] == 19 and d["interval_points"] == [-32, 55] and d["includes_zero"] is True, "difference is wrong: %r" % d)
    expect(near(d["interval"][0], -0.3226, 1e-4) and near(d["interval"][1], 0.5484, 1e-4), "difference interval is wrong: %r" % d["interval"])
    expect(d["group_intervals"] == "overlap almost entirely" and cmp_["left_out"] == 1, "overlap wording or left-out count is wrong: %r" % cmp_)
    code, out, _ = c.cli(data, "--instrument", inst, "--compare", "ans=Yes", "--by", "grp")
    expect("3 of 4 who answered both (75%" in out and "5 of 9 who answered both (56%" in out and "+19 points" in out and "-32 to +55 points" in out, "text comparison is wrong")
    expect("includes zero" in out and "significant" not in out.lower(), "the comparison must be worded with the interval, never with 'significant'")
    # 18 of 20 against 4 of 20: an interval that excludes zero is reported as excluding it.
    rows = ["respondent,grp,ans"] + ["a%d,A,%s" % (i, "Yes" if i < 18 else "No") for i in range(20)] + ["b%d,B,%s" % (i, "Yes" if i < 4 else "No") for i in range(20)]
    code, r = c.js(c.csv("\n".join(rows) + "\n"), "--instrument", inst, "--compare", "ans=Yes", "--by", "grp")
    expect(r["compare"]["difference"]["includes_zero"] is False and r["compare"]["difference"]["points"] == 70, "a clear difference was not reported: %r" % r["compare"]["difference"])


# ---------------------------------------------------------------- denominators and non-response

SKIP_CSV = ("respondent,q1,q2\n"
            "p01,Yes,Good\np02,Yes,Good\np03,Yes,Bad\np04,Yes,Good\np05,Yes,\np06,Yes,\n"
            "p07,No,\np08,No,\np09,,\np10,,\n")
SKIP_INST = {"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No"]},
                           {"id": "q2", "type": "single", "options": ["Good", "Bad"], "shown_if": {"question": "q1", "in": ["Yes"]}}]}


def test_skipped_respondents_stay_in_the_denominator(c):
    # q1: 10 respondents, all shown. 6 Yes, 2 No, 2 left it empty.
    #   Yes = 6 of 8 who answered (75%) and 6 of 10 shown (60%). Skipped = 2 of 10 shown (20%).
    # q2 is shown only when q1 is Yes: shown to 6, not shown to 4 (2 said No, 2 skipped q1).
    #   Of the 6 shown: 4 answered, 2 skipped. Good = 3 of 4 who answered (75%) and 3 of 6 shown (50%).
    code, r = c.js(c.csv(SKIP_CSV), "--instrument", c.inst(SKIP_INST))
    q1, q2 = question(r, "q1"), question(r, "q2")
    expect(code == 0 and (q1["respondents"], q1["shown"], q1["answered"], q1["skipped"], q1["not_shown"]) == (10, 10, 8, 2, 0),
           "q1 counts are %r; skipped respondents must be counted as shown and skipped, never dropped" % ((q1["respondents"], q1["shown"], q1["answered"], q1["skipped"], q1["not_shown"]),))
    yes = option(q1, "Yes")
    expect((yes["of_answered"]["count"], yes["of_answered"]["n"], yes["of_answered"]["percent"]) == (6, 8, 75), "Yes of answered is wrong: %r" % yes["of_answered"])
    expect((yes["of_shown"]["count"], yes["of_shown"]["n"], yes["of_shown"]["percent"]) == (6, 10, 60), "Yes of shown must be 6 of 10: %r" % yes["of_shown"])
    expect(q1["skipped_ids"] == ["R09", "R10"] and q1["skipped_of_shown"]["percent"] == 20, "skipped ids or share wrong: %r" % q1["skipped_ids"])
    expect((q2["shown"], q2["not_shown"], q2["answered"], q2["skipped"]) == (6, 4, 4, 2), "q2: skipped (2) and not shown (4) must be told apart: %r"
           % ((q2["shown"], q2["not_shown"], q2["answered"], q2["skipped"]),))
    good = option(q2, "Good")
    expect((good["of_answered"]["n"], good["of_shown"]["n"], good["of_shown"]["percent"], good["of_respondents"]["n"]) == (4, 6, 50, 10), "q2 denominators are wrong: %r" % good)
    code, out, _ = c.cli(c.csv(SKIP_CSV), "--instrument", c.inst(SKIP_INST))
    expect("skipped 2 = 20% of those shown (R09, R10)" in out and "6 of 10 shown (60%)" in out, "the text output must show the skips and the shown denominator")
    expect("shown to 6 of 10 respondents (4 not shown; routing: shown when q1 is Yes); answered 4; skipped 2 = 33% of those shown" in out, "the routed question's line is wrong")


def test_every_percentage_carries_count_and_denominator(c):
    import re
    code, out, _ = c.cli(c.csv(SKIP_CSV), "--instrument", c.inst(SKIP_INST), "--cross", "q1", "q2")
    expect(code == 0, "run failed")
    for line in out.splitlines():
        for m in re.finditer(r"(\d+)%", line):
            if "interval" in line[max(0, m.start() - 30):m.start()] or " to " in line[max(0, m.start() - 8):m.start()] or line.lstrip().startswith("Intervals are"):
                continue
            expect(re.search(r"\d+ of \d+", line[:m.start()]) or "skipped" in line[:m.start()],
                   "a percentage is printed with no count and denominator before it: %r" % line.strip())


def test_routing_violation_is_reported_not_counted(c):
    data = c.csv("respondent,q1,q2\np1,Yes,Good\np2,No,Bad\np3,No,\n")
    code, r = c.js(data, "--instrument", c.inst(SKIP_INST))
    q2 = question(r, "q2")
    expect(code == 0 and (q2["shown"], q2["not_shown"], q2["answered"]) == (1, 2, 1), "an answer to a question that was not shown was counted: %r" % q2)
    expect(any("q2" in a and "not shown" in a and "R02" in a for a in r["advisories"]), "the routing violation was not reported with the respondent id: %r" % r["advisories"])


def test_scale_reports_full_distribution(c):
    # 7 answers on a 4-point scale: SD 0, D 2, A 4, SA 1. Options with no answers are still printed.
    # Ordered answers: D D A A A A SA. The 4th of 7 is A, so the middle answer is A.
    # --scale-means: (2 + 2 + 3 + 3 + 3 + 3 + 4) / 7 = 20 / 7 = 2.857 -> 2.86, labelled as treating the scale as numbers.
    opts = ["Strongly disagree", "Disagree", "Agree", "Strongly agree"]
    rows = ["respondent,s"] + ["p%d,%s" % (i, v) for i, v in enumerate(["Disagree"] * 2 + ["Agree"] * 4 + ["Strongly agree"])]
    data, inst = c.csv("\n".join(rows) + "\n"), c.inst({"questions": [{"id": "s", "type": "scale", "options": opts}]})
    code, r = c.js(data, "--instrument", inst)
    q = question(r, "s")
    expect([o["count"] for o in q["options"]] == [0, 2, 4, 1] and [o["option"] for o in q["options"]] == opts, "scale distribution is wrong or out of order")
    expect(q["middle_answer"] == ["Agree"] and "numeric_mean" not in q, "middle answer wrong, or a mean was printed without being asked for")
    code, r = c.js(data, "--instrument", inst, "--scale-means")
    m = question(r, "s")["numeric_mean"]
    expect(m["mean"] == 2.86 and m["n"] == 7 and "treats the 4 scale points as the numbers 1 to 4" in m["caveat"], "scale mean or its caveat is wrong: %r" % m)
    # --combine: Agree or Strongly agree = 4 + 1 = 5 of 7 who answered (71%).
    #   Wilson: centre = (0.714286 + 3.841459 / 14) / (1 + 3.841459 / 7) = 0.988676 / 1.548780 = 0.638358
    #   half = 1.959964 * sqrt(0.714286 * 0.285714 / 7 + 3.841459 / 196) / 1.548780 = 1.959964 * sqrt(0.029155 + 0.019599) / 1.548780 = 0.279423
    #   interval 0.358935 to 0.917781 -> 36% to 92%
    code, r = c.js(data, "--instrument", inst, "--combine", "s=Agree|Strongly agree")
    cb = r["combined"][0]
    expect(code == 0 and (cb["of_answered"]["count"], cb["of_answered"]["n"], cb["of_answered"]["percent"], cb["of_answered"]["interval_percent"]) == (5, 7, 71, [36, 92]),
           "combined options are wrong: %r" % cb)
    expect(abs(cb["of_answered"]["interval"][0] - 0.3589) < 1e-4 and abs(cb["of_answered"]["interval"][1] - 0.9178) < 1e-4, "combined interval is wrong: %r" % cb["of_answered"]["interval"])
    code, out, _ = c.cli(data, "--instrument", inst, "--combine", "s=Agree|Strongly agree")
    expect("COMBINED  s = Agree or Strongly agree: 5 of 7 who answered (71%, interval 36% to 92%); 5 of 7 shown (71%); 5 of 7 respondents (71%)" in out, "combined line is wrong")
    code, _, err = c.cli(data, "--instrument", inst, "--combine", "s=Agree|Sometimes")
    expect(code == 2 and "'Sometimes' is not an option of s" in err, "an unknown option in --combine must exit 2: %r" % err)
    # An even number of answers whose two middle answers differ reports both: D D A A -> Disagree / Agree.
    rows = ["respondent,s", "a,Disagree", "b,Disagree", "c,Agree", "d,Agree"]
    code, r = c.js(c.csv("\n".join(rows) + "\n"), "--instrument", inst)
    expect(question(r, "s")["middle_answer"] == ["Disagree", "Agree"], "two different middle answers must both be reported")


def test_multi_choice_counts_respondents(c):
    # 4 respondents answered. a: p1, p2 = 2. b: p1, p3 = 2. c: nobody. p4 chose "a" twice in one cell: still one respondent.
    data = c.csv("respondent,m\np1,a;b\np2,a\np3,b\np4,a; a\np5,\n")
    code, r = c.js(data, "--instrument", c.inst({"questions": [{"id": "m", "type": "multi", "options": ["a", "b", "c"]}]}))
    q = question(r, "m")
    expect(code == 0 and [(o["count"], o["of_answered"]["n"]) for o in q["options"]] == [(3, 4), (2, 4), (0, 4)], "multi-choice counts are wrong: %r" % q["options"])
    expect(q["skipped"] == 1, "the empty cell must be a skip")


def test_cross_tab_hand_worked(c):
    # mode x rating, 9 respondents; one has no rating and is left out, so 8 answered both.
    #   Online (5):   Good 4, Bad 1   -> 80%, 20%; one respondent = 20 points
    #   In person (3): Good 1, Bad 2  -> 33%, 67%; one respondent = 33 points
    rows = ["respondent,mode,rating", "a,Online,Good", "b,Online,Good", "c,Online,Good", "d,Online,Good", "e,Online,Bad",
            "f,In person,Good", "g,In person,Bad", "h,In person,Bad", "i,In person,"]
    inst = c.inst({"questions": [{"id": "mode", "type": "single", "options": ["Online", "In person"]}, {"id": "rating", "type": "single", "options": ["Good", "Bad"]}]})
    data = c.csv("\n".join(rows) + "\n")
    code, r = c.js(data, "--instrument", inst, "--cross", "mode", "rating")
    x = r["cross"][0]
    got = [(row["option"], row["n"], row["one_respondent_points"], [(cell["of_row"]["count"], cell["of_row"]["percent"]) for cell in row["cells"]]) for row in x["rows"]]
    expect(code == 0 and got == [("Online", 5, 20, [(4, 80), (1, 20)]), ("In person", 3, 33, [(1, 33), (2, 67)])], "cross-tab is wrong: %r" % got)
    expect((x["answered_both"], x["left_out"], x["columns_unanswered"]) == (8, 1, 1), "cross-tab left-out counts are wrong")
    code, out, _ = c.cli(data, "--instrument", inst, "--cross", "mode", "rating")
    expect("CAVEAT" in out and "one respondent = 33 points" in out and "4 of 5 in this row (80%" in out, "cross-tab text lacks counts or its small-row caveat")
    # Joined options: "Good|Bad" covers every answer, so each group is n of n; "Good" alone is 4 of 5 and 1 of 3.
    code, r = c.js(data, "--instrument", inst, "--compare", "rating=Good|Bad", "--by", "mode")
    got = [(g["group"], g["chose"]["count"], g["chose"]["n"]) for g in r["compare"]["groups"]]
    expect(code == 0 and got == [("Online", 5, 5), ("In person", 3, 3)] and r["compare"]["option"] == "Good or Bad", "joined options are counted wrongly: %r" % got)
    code, r = c.js(data, "--instrument", inst, "--compare", "rating=Good", "--by", "mode")
    got = [(g["group"], g["chose"]["count"], g["chose"]["n"]) for g in r["compare"]["groups"]]
    expect(got == [("Online", 4, 5), ("In person", 1, 3)], "single-option comparison is wrong: %r" % got)
    code, _, err = c.cli(data, "--instrument", inst, "--compare", "rating=Good|Fine", "--by", "mode")
    expect(code == 2 and "'Fine' is not an option of rating" in err, "an unknown option inside a joined list must exit 2: %r" % err)
    code, _, err = c.cli(data, "--instrument", inst, "--cross", "mode", "nope")
    expect(code == 2 and "not a question" in err, "an unknown question in --cross must exit 2: %r" % err)
    code, _, err = c.cli(data, "--instrument", inst, "--cross", "mode")
    expect(code == 2 and "needs 2 values" in err, "--cross with one value must exit 2: %r" % err)


# ---------------------------------------------------------------- quiz item analysis

QUIZ_CSV = ("respondent,i1,i2,i3,i4\n"
            "s01,B,A,C,D\ns02,B,A,C,A\ns03,B,A,A,D\ns04,B,C,C,D\ns05,B,A,B,B\n"
            "s06,A,A,C,B\ns07,B,B,A,A\ns08,C,A,A,B\ns09,A,C,A,D\ns10,A,B,A,\n")
QUIZ_INST = {"questions": [{"id": "i1", "type": "single", "options": ["A", "B", "C", "D"], "correct": "B"},
                           {"id": "i2", "type": "single", "options": ["A", "B", "C", "D"], "correct": "A"},
                           {"id": "i3", "type": "single", "options": ["A", "B", "C", "D"], "correct": "C"},
                           {"id": "i4", "type": "single", "options": ["A", "B", "C", "D"], "correct": "D"}]}
# Scored by hand (1 = keyed answer):
#        i1 i2 i3 i4  total
#   s01   1  1  1  1    4
#   s02   1  1  1  0    3
#   s03   1  1  0  1    3
#   s04   1  0  1  1    3
#   s05   1  1  0  0    2
#   s06   0  1  1  0    2
#   s07   1  0  0  0    1
#   s08   0  1  0  0    1
#   s09   0  0  0  1    1
#   s10   0  0  0  0    0     (i4 left empty: omitted, scored as not correct)
# Groups at 27 per cent of 10: k = 2.7 rounded = 3. The 3rd highest score is 3, so the upper group is
# everyone on 3 or more: s01 to s04 (4 people, because the tie at 3 is kept together). The 3rd lowest
# score is 1, so the lower group is everyone on 1 or fewer: s07 to s10 (4 people).
#   i1: correct 6 of 10. Upper 4 of 4, lower 1 of 4 (s07). D = 1.00 - 0.25 = +0.75
#   i2: correct 6 of 10. Upper 3 of 4, lower 1 of 4 (s08). D = 0.75 - 0.25 = +0.50
#   i3: correct 4 of 10. Upper 3 of 4, lower 0 of 4.       D = 0.75 - 0.00 = +0.75
#   i4: correct 4 of 10. Upper 3 of 4, lower 1 of 4 (s09). D = 0.75 - 0.25 = +0.50, 1 omitted


def test_discrimination_index_hand_worked(c):
    code, r = c.js(c.csv(QUIZ_CSV), "--instrument", c.inst(QUIZ_INST))
    qz = r["quiz"]
    g = qz["groups"]
    expect(code == 0 and g["formed"] and g["target_size"] == 3 and (g["upper"]["size"], g["upper"]["min_score"], g["lower"]["size"], g["lower"]["max_score"]) == (4, 3, 4, 1),
           "score groups are wrong: %r" % g)
    expect(g["upper"]["ids"] == ["R01", "R02", "R03", "R04"] and g["lower"]["ids"] == ["R07", "R08", "R09", "R10"], "group membership is wrong")
    want = {"i1": (6, 4, 1, 0.75), "i2": (6, 3, 1, 0.5), "i3": (4, 3, 0, 0.75), "i4": (4, 3, 1, 0.5)}
    for it in qz["item_analysis"]:
        got = (it["difficulty"]["count"], it["upper"]["correct"], it["lower"]["correct"], it["discrimination"])
        expect(got == want[it["id"]] and it["difficulty"]["n"] == 10 and it["upper"]["n"] == 4 and it["lower"]["n"] == 4,
               "%s: correct, upper, lower, D = %r; worked by hand as %r" % (it["id"], got, want[it["id"]]))
    # One respondent changing one answer moves D by 1 / 4 = 0.25 with groups of four.
    expect(g["one_respondent_moves_d_by"] == 0.25, "the step size of D must be printed: %r" % g["one_respondent_moves_d_by"])
    # Total scores: 4, 3, 3, 3, 2, 2, 1, 1, 1, 0. Sum 20, mean 2.0, median (2 + 2) / 2 = 2.
    s = qz["scores"]
    expect((s["min"], s["median"], s["max"], s["mean"]) == (0, 2, 4, 2.0), "score summary is wrong: %r" % s)
    expect([(d["score"], d["respondents"]) for d in s["distribution"]] == [(0, 1), (1, 3), (2, 2), (3, 3), (4, 1)], "score distribution is wrong")
    code, out, _ = c.cli(c.csv(QUIZ_CSV), "--instrument", c.inst(QUIZ_INST))
    expect("i1  keyed B  correct 6 of 10 shown (60%, interval 31% to 83%); upper 4 of 4, lower 1 of 4, D = +0.75" in out, "item line is wrong:\n" + out)
    expect("Upper group: the 4 respondent(s) scoring 3 or more. Lower group: the 4 scoring 1 or fewer." in out, "group definition and sizes must be printed")


def test_distractor_counts_and_dead_option(c):
    # i3 (keyed C): A chosen by s03, s07, s08, s09, s10 = 5 (upper 1, lower 4). B by s05 = 1 (0, 0).
    #               C by s01, s02, s04, s06 = 4 (upper 3, lower 0). D by nobody.
    # i4 (keyed D): A by s02, s07 = 2 (1, 1). B by s05, s06, s08 = 3 (0, 1). C by nobody. D = 4 (3, 1). Omitted: s10 (lower).
    code, r = c.js(c.csv(QUIZ_CSV), "--instrument", c.inst(QUIZ_INST))
    items = {it["id"]: it for it in r["quiz"]["item_analysis"]}
    got = [(o["option"], o["all"], o["upper"], o["lower"]) for o in items["i3"]["options"]]
    expect(got == [("A", 5, 1, 4), ("B", 1, 0, 0), ("C", 4, 3, 0), ("D", 0, 0, 0)], "i3 option counts are wrong: %r" % got)
    got = [(o["option"], o["all"], o["upper"], o["lower"]) for o in items["i4"]["options"]]
    expect(got == [("A", 2, 1, 1), ("B", 3, 0, 1), ("C", 0, 0, 0), ("D", 4, 3, 1)], "i4 option counts are wrong: %r" % got)
    expect(items["i4"]["omitted"] == 1 and items["i4"]["omitted_by_group"] == {"upper": 0, "lower": 1}, "the omitted answer must be counted")
    flags = {i: [f["flag"] for f in items[i]["flags"]] for i in items}
    expect(flags == {"i1": ["option nobody chose"], "i2": ["option nobody chose"], "i3": ["option nobody chose"], "i4": ["option nobody chose"]}, "flags are wrong: %r" % flags)
    expect("'D' was chosen by 0 of 10" in items["i3"]["flags"][0]["detail"], "the dead option must be named with its count")


def test_miskeyed_item_is_flagged_as_a_candidate(c):
    # jm is keyed C, but the two top scorers both chose B.
    #        j1 j2 j3 jm   scored (keys A A A C)  total
    #   t01   A  A  A  B    1 1 1 0                 3
    #   t02   A  A  A  B    1 1 1 0                 3
    #   t03   A  A  B  B    1 1 0 0                 2
    #   t04   A  B  B  A    1 0 0 0                 1
    #   t05   B  A  B  D    0 1 0 0                 1
    #   t06   B  B  A  C    0 0 1 1                 2
    #   t07   B  B  B  C    0 0 0 1                 1
    #   t08   B  B  B  C    0 0 0 1                 1
    # k = 27 per cent of 8 = 2.16 -> 2. The 2nd highest score is 3: upper = t01, t02. The 2nd lowest is 1:
    # lower = t04, t05, t07, t08 (four tied on 1).
    # jm: correct 3 of 8. Upper 0 of 2, lower 2 of 4: D = 0 - 0.5 = -0.50.
    #     Option B: chosen by 3 (upper 2 of 2, lower 0 of 4). The upper group's most-chosen answer is B, not the key.
    data = c.csv("respondent,j1,j2,j3,jm\nt01,A,A,A,B\nt02,A,A,A,B\nt03,A,A,B,B\nt04,A,B,B,A\nt05,B,A,B,D\nt06,B,B,A,C\nt07,B,B,B,C\nt08,B,B,B,C\n")
    inst = c.inst({"questions": [{"id": q, "type": "single", "options": ["A", "B", "C", "D"], "correct": k} for q, k in (("j1", "A"), ("j2", "A"), ("j3", "A"), ("jm", "C"))]})
    code, r = c.js(data, "--instrument", inst)
    items = {it["id"]: it for it in r["quiz"]["item_analysis"]}
    jm = items["jm"]
    expect(code == 0 and (jm["difficulty"]["count"], jm["upper"], jm["lower"], jm["discrimination"]) == (3, {"correct": 0, "n": 2}, {"correct": 2, "n": 4}, -0.5),
           "jm analysis is wrong: %r" % jm)
    names = [f["flag"] for f in jm["flags"]]
    expect(names == ["wrong option chosen more by the upper group", "possible miskey", "negative discrimination"], "jm flags are %r" % names)
    expect("'B': 2 of 2 in the upper group against 0 of 4 in the lower" in jm["flags"][0]["detail"], "the flag must carry its counts: %r" % jm["flags"][0])
    expect(not any(f["flag"] == "possible miskey" for i in ("j1", "j2", "j3") for f in items[i]["flags"]), "a sound item was flagged as a possible miskey")
    code, out, _ = c.cli(data, "--instrument", inst)
    expect("CANDIDATE  possible miskey" in out and "They are not verdicts" in out, "flags must be printed as candidates for a person to read")
    # One upper-group respondent choosing a wrong option is a slip, not a flag; two are a candidate.
    #        a1 a2 a3 x    scored (keys A A A A)   total
    #   r1    A  A  A  B    1 1 1 0                  3
    #   r2    A  A  A  A    1 1 1 1                  4      (second version: x = B, total 3)
    #   r3    A  A  B  A    1 1 0 1                  3
    #   r4    A  B  B  A    1 0 0 1                  2
    #   r5    A  B  B  C    1 0 0 0                  1
    #   r6    B  B  B  A    0 0 0 1                  1
    #   r7    B  B  B  C    0 0 0 0                  0
    #   r8    B  B  B  C    0 0 0 0                  0
    # k = 2. The 2nd highest score is 3, so the upper group is r1, r2, r3; the 2nd lowest is 0, so the lower is r7, r8.
    # First version: B is chosen by 1 of 3 in the upper group and 0 of 2 in the lower: a larger share, but one person. No flag.
    # Second version: B by 2 of 3 against 0 of 2: flagged, and B (2) now beats the keyed A (1) in the upper group.
    inst2 = c.inst({"questions": [{"id": q, "type": "single", "options": ["A", "B", "C"], "correct": "A"} for q in ("a1", "a2", "a3", "x")]})
    base = "respondent,a1,a2,a3,x\nr1,A,A,A,B\nr2,A,A,A,%s\nr3,A,A,B,A\nr4,A,B,B,A\nr5,A,B,B,C\nr6,B,B,B,A\nr7,B,B,B,C\nr8,B,B,B,C\n"
    def x_item(r2_answer):
        r = c.js(c.csv(base % r2_answer), "--instrument", inst2)[1]
        it = next(i for i in r["quiz"]["item_analysis"] if i["id"] == "x")
        b = next(o for o in it["options"] if o["option"] == "B")
        return (b["upper"], it["upper"]["n"], b["lower"], it["lower"]["n"]), [f["flag"] for f in it["flags"]]
    counts, flags = x_item("A")
    expect(counts == (1, 3, 0, 2) and flags == [], "one upper-group slip must not be flagged: %r %r" % (counts, flags))
    counts, flags = x_item("B")
    expect(counts == (2, 3, 0, 2) and flags == ["wrong option chosen more by the upper group", "possible miskey"], "two upper-group choices of a wrong option must be flagged: %r %r" % (counts, flags))


def test_point_biserial_hand_worked(c):
    # i1 against the total score. Totals 4 3 3 3 2 2 1 1 1 0; i1 scored 1 1 1 1 1 0 1 0 0 0.
    #   mean total = 20 / 10 = 2. Squared deviations 4 1 1 1 0 0 1 1 1 4 sum to 14; s = sqrt(14 / 10) = 1.183216.
    #   M1 (the six who got i1 right: 4 3 3 3 2 1) = 16 / 6 = 2.666667. M0 (2 1 1 0) = 4 / 4 = 1.
    #   p = 0.6, q = 0.4, sqrt(pq) = 0.489898.
    #   r = (2.666667 - 1) / 1.183216 * 0.489898 = 1.408591 * 0.489898 = 0.690066 -> 0.69
    # i1 against the rest score (total minus i1): 3 2 2 2 1 2 0 1 1 0. Mean 1.4; squared deviations sum to 8.4;
    #   s = sqrt(0.84) = 0.916515. M1 = (3 + 2 + 2 + 2 + 1 + 0) / 6 = 1.666667. M0 = (2 + 1 + 1 + 0) / 4 = 1.
    #   r = (0.666667 / 0.916515) * 0.489898 = 0.727393 * 0.489898 = 0.356348 -> 0.36
    pb = c.mod.point_biserial
    expect(near(pb([1, 1, 1, 1, 1, 0, 1, 0, 0, 0], [4, 3, 3, 3, 2, 2, 1, 1, 1, 0]), 0.690066), "point-biserial with the total is wrong")
    expect(near(pb([1, 1, 1, 1, 1, 0, 1, 0, 0, 0], [3, 2, 2, 2, 1, 2, 0, 1, 1, 0]), 0.356348), "point-biserial with the rest score is wrong")
    expect(pb([1, 1, 1], [1, 2, 3]) is None and pb([1, 0, 1], [2, 2, 2]) is None, "an item or score with no spread has no correlation")
    code, r = c.js(c.csv(QUIZ_CSV), "--instrument", c.inst(QUIZ_INST), "--point-biserial")
    i1 = r["quiz"]["item_analysis"][0]
    expect(i1["point_biserial"] == {"with_total": 0.69, "with_rest": 0.36, "n": 10}, "point-biserial in the output is wrong: %r" % i1.get("point_biserial"))
    code, r = c.js(c.csv(QUIZ_CSV), "--instrument", c.inst(QUIZ_INST))
    expect("point_biserial" not in r["quiz"]["item_analysis"][0], "point-biserial is an option and must not appear unasked")


def test_bunched_scores_and_easy_items(c):
    # Three respondents, all right on e1 (3 of 3: "nearly everyone right"), all wrong on e2 (0 of 3: "nearly everyone wrong").
    # Every total is 1, so no upper and lower group can be formed: D is not printed, the rest still is.
    data = c.csv("respondent,e1,e2\na,A,B\nb,A,B\nc,A,C\n")
    inst = c.inst({"questions": [{"id": "e1", "type": "single", "options": ["A", "B"], "correct": "A"}, {"id": "e2", "type": "single", "options": ["A", "B", "C"], "correct": "A"}]})
    code, r = c.js(data, "--instrument", inst)
    qz = r["quiz"]
    items = {it["id"]: it for it in qz["item_analysis"]}
    expect(code == 0 and qz["groups"]["formed"] is False and items["e1"]["discrimination"] is None, "bunched scores must give no D, not a made-up one")
    expect(items["e1"]["difficulty"]["count"] == 3 and items["e1"]["difficulty"]["interval_percent"] == [44, 100], "difficulty must still be printed with its interval: %r" % items["e1"]["difficulty"])
    expect([f["flag"] for f in items["e1"]["flags"]] == ["nearly everyone right", "option nobody chose"], "e1 flags: %r" % items["e1"]["flags"])
    expect([f["flag"] for f in items["e2"]["flags"]] == ["nearly everyone wrong"], "e2 flags: %r" % items["e2"]["flags"])
    code, out, _ = c.cli(data, "--instrument", inst)
    expect("could not be formed" in out and "e1  keyed A  correct 3 of 3 shown (100%, interval 44% to 100%)" in out, "text for bunched scores is wrong")
    # Valid neighbour of "nearly everyone right": 8 of 10 (80 per cent) is not flagged, 9 of 10 is.
    def easy(k):
        rows = ["respondent,e1,e2"] + ["p%d,%s,%s" % (i, "A" if i < k else "B", "A" if i % 2 else "B") for i in range(10)]
        return [f["flag"] for f in c.js(c.csv("\n".join(rows) + "\n"), "--instrument", inst)[1]["quiz"]["item_analysis"][0]["flags"]]
    expect("nearly everyone right" in easy(9) and "nearly everyone right" not in easy(8), "the nine-in-ten reading threshold is wrong")


# ---------------------------------------------------------------- free text and themes

TEXT_CSV = ("respondent,q1,q5,q5__note,q6\n"
            "Ana,Yes,Too fast in the afternoon,It dragged then rushed,More breaks\n"
            "Ben,No,Loved the worked examples,,\n"
            "Cal,Yes,Pace was too quick,Really too quick,Slow down please\n"
            "Dee,Yes,Could not hear at the back,,\n"
            "Eli,No,,,Nothing to add\n"
            "Fay,Yes,,,\n")
TEXT_INST = {"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No"]}, {"id": "q5", "type": "text"}, {"id": "q6", "type": "text"}]}
CODED = ("respondent,question,text,screen,themes\n"
         "R01,q5,Too fast in the afternoon,,pace\n"
         "R01,q5__note,It dragged then rushed,,pace\n"
         "R01,q6,More breaks,,breaks\n"
         "R02,q5,Loved the worked examples,,examples\n"
         "R03,q5,Pace was too quick,,pace; pace\n"
         "R03,q5__note,Really too quick,,pace\n"
         "R03,q6,Slow down please,,pace\n"
         "R04,q5,Could not hear at the back,,\n"
         "R05,q6,Nothing to add,,\n")
BOOK = "code,definition\npace,Says the session moved too fast or too slowly\nexamples,Praises or asks for worked examples\nbreaks,Asks for more or longer breaks\nvenue,Comments on the room or equipment\n"


def test_coding_sheet_export(c):
    out_path = c.path(".csv")
    data, inst = c.csv(TEXT_CSV), c.inst(TEXT_INST)
    before = data.read_bytes()
    code, out, _ = c.cli(data, "--instrument", inst, "--coding-sheet", out_path)
    sheet = out_path.read_text(encoding="utf-8").splitlines()
    expect(code == 0 and sheet[0] == "respondent,question,text,screen,themes" and len(sheet) == 10, "coding sheet has %d lines, expected a header and 9 passages" % len(sheet))
    expect(sheet[1] == "R01,q5,Too fast in the afternoon,," and "wrote 9 passage(s) from 5 respondent(s)" in out, "coding sheet content or its summary is wrong: %r" % sheet[1])
    expect("Ana" not in "\n".join(sheet) and data.read_bytes() == before, "names leaked into the sheet, or the input was modified")
    code, _, err = c.cli(data, "--instrument", inst, "--coding-sheet", out_path)
    expect(code == 2 and "already exists" in err, "an existing sheet must not be overwritten silently: %r" % err)
    code, _, _ = c.cli(data, "--instrument", inst, "--coding-sheet", out_path, "--overwrite")
    expect(code == 0, "--overwrite must allow replacing the sheet")
    code, _, err = c.cli(data, "--instrument", inst, "--coding-sheet", data, "--overwrite")
    expect(code == 2 and "never overwritten" in err and data.read_bytes() == before, "the responses file must never be overwritten: %r" % err)


def test_themes_count_respondents_not_mentions(c):
    # Five respondents wrote something (R01 to R05), in 9 passages. R06 wrote nothing.
    # pace: R01 (two passages) and R03 (three passages, one of them coded "pace; pace") = 2 respondents, 5 coded passages.
    #       2 of 5 who wrote something (40%); 2 of 6 respondents (33%). Counting mentions would give 5 or 6.
    # examples: R02 = 1 of 5. breaks: R01 = 1 of 5. venue: in the codebook, used by nobody = 0 of 5.
    # R04 and R05 have no code at all: reported, and still in the denominator.
    data, inst, coded, book = c.csv(TEXT_CSV), c.inst(TEXT_INST), c.csv(CODED), c.csv(BOOK)
    code, r = c.js(data, "--instrument", inst, "--themes", coded, "--codebook", book)
    a = r["themes"]["all_free_text"]
    t = {x["code"]: x for x in a["themes"]}
    expect(code == 0 and (a["writers"], a["passages"], a["passages_with_no_code"]) == (5, 9, 2), "writers and passages are wrong: %r" % ((a["writers"], a["passages"], a["passages_with_no_code"]),))
    expect((t["pace"]["respondents"], t["pace"]["of_writers"]["n"], t["pace"]["of_writers"]["percent"], t["pace"]["coded_passages"]) == (2, 5, 40, 5),
           "pace must count 2 respondents of 5 (in 5 coded passages), got %r respondents of %r in %r passages"
           % (t["pace"]["respondents"], t["pace"]["of_writers"]["n"], t["pace"]["coded_passages"]))
    expect(t["pace"]["respondent_ids"] == ["R01", "R03"] and t["pace"]["of_all_respondents"]["n"] == 6 and t["pace"]["of_all_respondents"]["percent"] == 33, "pace ids or all-respondent share wrong")
    expect((t["examples"]["respondents"], t["breaks"]["respondents"], t["venue"]["respondents"]) == (1, 1, 0), "other theme counts are wrong")
    expect(a["respondents_with_no_code"] == ["R04", "R05"], "respondents with no code must be listed: %r" % a["respondents_with_no_code"])
    # By question: q6 has three writers (R01, R03, R05); pace there is R03 only = 1 of 3.
    q6 = next(b for b in r["themes"]["by_question"] if b["question"] == "q6")
    p6 = next(x for x in q6["themes"] if x["code"] == "pace")
    expect((q6["writers"], p6["respondents"], p6["of_writers"]["n"]) == (3, 1, 3), "per-question theme counts are wrong")
    code, out, _ = c.cli(data, "--instrument", inst, "--themes", coded, "--codebook", book)
    expect("pace      2 of 5 who wrote something (40%, interval 12% to 77%); 2 of 6 respondents (33%) [in 5 coded passage(s); R01, R03]" in out, "theme line is wrong:\n" + out)
    expect("the analyst's coding" in out and "pace: Says the session moved too fast or too slowly" in out and "No code at all: 2 respondent(s) (R04, R05)" in out, "themes text lacks the coding label, codebook or uncoded cases")


def test_coded_sheet_problems_are_refused(c):
    data, inst, book = c.csv(TEXT_CSV), c.inst(TEXT_INST), c.csv(BOOK)

    def run(sheet, *extra):
        code, r = c.js(data, "--instrument", inst, "--themes", c.csv(sheet), *extra)
        return code, " | ".join(r["errors"]), r

    code, errs, _ = run(CODED.replace("R02,q5", "R77,q5"))
    expect(code == 1 and "respondent 'R77' is not in the responses" in errs, "an unknown respondent in the coded sheet was accepted: %r" % errs)
    code, errs, _ = run(CODED.replace("R02,q5,Loved", "R02,q6,Loved"))
    expect(code == 1 and "R02 gave no free-text answer to 'q6'" in errs, "a passage that does not exist was accepted: %r" % errs)
    code, errs, _ = run(CODED + "R05,q6,Nothing to add,,pace\n")
    expect(code == 1 and "appears twice" in errs, "a repeated passage was accepted: %r" % errs)
    code, errs, _ = run(CODED.replace(",,examples", ",,exmaples"), "--codebook", book)
    expect(code == 1 and "code 'exmaples' is not in the codebook" in errs, "a code outside the codebook was accepted: %r" % errs)
    code, errs, _ = run(CODED.replace("R03,q6,Slow down please,,pace", "R03,q6,Slow down please,,Pace"))
    expect(code == 1 and "differ only in capital letters" in errs, "Pace and pace were treated as two codes: %r" % errs)
    code, errs, r = run(CODED)
    expect(code == 0 and any("no codebook was given" in a for a in r["advisories"]), "a coded sheet with no codebook must run with an advisory")
    # A passage left out of the coded sheet stays in the denominator and is reported.
    code, errs, r = run(CODED.replace("R05,q6,Nothing to add,,\n", ""))
    expect(code == 0 and r["themes"]["all_free_text"]["writers"] == 5 and any("missing from the coded sheet" in a and "R05/q6" in a for a in r["advisories"]),
           "a passage missing from the coded sheet was dropped silently")
    code, _, err = c.cli(data, "--instrument", inst, "--themes", c.csv("respondent,question\nR01,q5\n"))
    expect(code == 2 and "needs the columns" in err, "a coded sheet with no themes column must exit 2")


def test_contact_details_are_screened(c):
    data = c.csv("respondent,q5\na,Call me on 0412 345 678 about this\nb,Email jo@example.org or see www.example.org\nc,It ran from 2019 to 2021 and was fine\n")
    out_path = c.path(".csv")
    code, r = c.js(data, "--instrument", c.inst({"questions": [{"id": "q5", "type": "text"}]}), "--coding-sheet", out_path)
    sheet = out_path.read_text(encoding="utf-8").splitlines()
    expect(code == 0 and sheet[1].endswith(",phone number,") and sheet[2].endswith(",email address; web address,") and sheet[3].endswith(",,"), "screen column is wrong: %r" % sheet[1:])
    expect(any("2 free-text passage(s) contain what looks like contact details" in a and "Names, workplaces and roles are not detected" in a for a in r["advisories"]),
           "contact details were not reported, or the limit of the screen was not stated")


# ---------------------------------------------------------------- malformed input

def test_ragged_rows_are_refused(c):
    data = c.csv("respondent,q1,q2\na,Yes,Good\nb,No\nc,Yes,Good,extra\nd,Yes,\"Good, mostly\"\n")
    code, out, _ = c.cli(data)
    expect(code == 1 and "line 3 has 2 cells but the header has 3" in out and "line 4 has 4 cells but the header has 3" in out, "ragged rows were not reported by line: %r" % out)
    expect("RESULT: REFUSED" in out and "No analysis was produced" in out and "WHO ANSWERED" not in out and "INFERRED" not in out, "an analysis or a type guess was printed for a ragged file")
    code, out, _ = c.cli(c.csv("respondent,q1,q2\na,Yes,Good\nb,No,\nd,Yes,\"Good, mostly\"\n\n"))
    expect(code == 0, "a well-formed file with a quoted comma and a trailing blank line was refused")


def test_unknown_option_values_are_refused_or_counted(c):
    inst = c.inst({"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No", "Maybe"]}]})
    data = c.csv("respondent,q1\na,Yes\nb,Mabye\nc,yes\nd,No\ne,\n")
    code, out, _ = c.cli(data, "--instrument", inst)
    expect(code == 1 and "R02 answered 'Mabye', which is not an option" in out and "R03 answered 'yes'" in out and "differs from 'Yes' only in capital letters" in out
           and "Options: Yes, No, Maybe" in out, "unknown option values were not reported precisely: %r" % out)
    code, r = c.js(data, "--instrument", inst, "--allow-unknown")
    q = question(r, "q1")
    counts = {o["option"]: (o["count"], o["of_answered"]["n"]) for o in q["options"]}
    # With --allow-unknown: Yes 1, No 1, other 2, all of 4 who answered; 1 skipped; nobody dropped.
    expect(code == 0 and counts == {"Yes": (1, 4), "No": (1, 4), "Maybe": (0, 4), "other (not an instrument option)": (2, 4)} and q["skipped"] == 1, "counts with --allow-unknown are wrong: %r" % counts)
    expect(any("Counted as" in a for a in r["advisories"]), "--allow-unknown must still report what it counted")
    code, out, _ = c.cli(c.csv("respondent,n\na,3\nb,three\n"), "--instrument", c.inst({"questions": [{"id": "n", "type": "number"}]}))
    expect(code == 1 and "R02 answered 'three', which is not a number" in out, "a non-numeric answer to a number question was accepted")


def test_duplicate_and_empty_respondent_ids_are_refused(c):
    data = c.csv("respondent,q1\nSam,Yes\nKim,No\nSam,No\n,Yes\n")
    code, out, _ = c.cli(data)
    expect(code == 1 and "appears on 2 rows (lines 2, 4)" in out and "line 5 has an empty respondent value" in out, "duplicate or empty respondent values were not reported: %r" % out)
    expect("Sam" not in out, "a respondent value was printed although ids are replaced by default")
    code, out, _ = c.cli(data, "--keep-ids")
    expect(code == 1 and "'Sam' appears on 2 rows" in out, "with --keep-ids the repeated value should be named")
    code, out, _ = c.cli(c.csv("respondent,q1\nSam,Yes\nKim,No\nsam,No\n"))
    expect(code == 0, "values that differ are different respondents (the valid neighbour)")


def test_unreadable_files_exit_2(c):
    code, _, err = c.cli(c.csv(None, raw=b"respondent,q1\na,caf\xe9\n"))
    expect(code == 2 and "not valid UTF-8" in err and "Traceback" not in err, "a non-UTF-8 file must exit 2: %r" % err)
    code, _, err = c.cli(c.csv(None, raw="respondent,q1\na,Yes\n".encode("utf-16")))
    expect(code == 2 and ("NUL" in err or "UTF-8" in err), "a UTF-16 file must exit 2: %r" % err)
    code, _, err = c.cli(c.csv(None, raw=b""))
    expect(code == 2 and "empty" in err, "an empty file must exit 2: %r" % err)
    code, _, err = c.cli(c.tmp / "missing.csv")
    expect(code == 2 and "cannot read" in err, "a missing file must exit 2")
    code, _, err = c.cli(c.csv("Respondent,q1\na,Yes\n"))
    expect(code == 2 and "no column called respondent" in err and "lower case" in err, "a missing respondent column must exit 2 with a hint: %r" % err)
    code, _, err = c.cli(c.csv("respondent,q1,q1\na,Yes,No\n"))
    expect(code == 2 and "names a column twice" in err, "a repeated column name must exit 2")
    code, out, _ = c.cli(c.csv("respondent,q1\n"))
    expect(code == 1 and "no respondents" in out, "a header with no rows must be refused")
    code, out, _ = c.cli(c.csv(None, raw=b"\xef\xbb\xbfrespondent,q1\na,Yes\nb,No\n"))
    expect(code == 0 and "Respondents (rows): 2" in out, "a UTF-8 byte-order mark must be accepted")
    data = c.csv("respondent,q1\na,Yes\n")
    code, _, err = c.cli(data, "--instrument", c.csv(None, raw=b'{"questions": [{"id": "q1", "type": "single", "options": ["Yes", NaN]}]}'))
    expect(code == 2 and "not valid JSON" in err, "NaN in the instrument must exit 2: %r" % err)


def test_instrument_that_does_not_match_the_data(c):
    data = c.csv("respondent,q1,q2,extra\na,Yes,3,x\nb,No,4,y\n")

    def errs(questions, **top):
        code, r = c.js(data, "--instrument", c.inst(dict({"questions": questions}, **top)))
        return code, " | ".join(r["errors"]), r

    ok = [{"id": "q1", "type": "single", "options": ["Yes", "No"]}, {"id": "q2", "type": "number"}]
    code, e, r = errs(ok)
    expect(code == 0 and any("column 'extra' is in the responses file but not in the instrument" in a for a in r["advisories"]), "a column outside the instrument must be reported and left out")
    expect([q["id"] for q in r["questions"]] == ["q1", "q2"], "the unlisted column was analysed")
    code, e, _ = errs(ok + [{"id": "q9", "type": "text"}])
    expect(code == 1 and "instrument question 'q9' has no column in the responses file" in e, "a question with no column was accepted: %r" % e)
    code, e, _ = errs([{"id": "Q1", "type": "single", "options": ["Yes", "No"]}])
    expect(code == 1 and "there is a column 'q1': ids must match exactly" in e, "a case mismatch in an id needs a hint: %r" % e)
    code, e, _ = errs([{"id": "q1", "type": "single", "options": ["Yes", "No"], "correct": "Maybe"}])
    expect(code == 1 and "the correct answer 'Maybe' is not one of its options" in e, "a key outside the options was accepted: %r" % e)
    code, e, _ = errs([{"id": "q1", "type": "single", "options": ["Yes", "No"], "shown_if": {"question": "q2", "in": ["3"]}}, ok[1]])
    expect(code == 1 and "not an earlier question" in e, "routing that points forward was accepted: %r" % e)
    code, e, _ = errs([ok[0], {"id": "q2", "type": "number", "shown_if": {"question": "q1", "in": ["Perhaps"]}}])
    expect(code == 1 and "not an option of 'q1'" in e, "routing on a value that is not an option was accepted: %r" % e)
    code, e, _ = errs([{"id": "q1", "type": "dropdown", "options": ["Yes", "No"]}])
    expect(code == 1 and "type 'dropdown' is not one of" in e, "an unknown type was accepted: %r" % e)
    code, e, _ = errs([{"id": "q1", "type": "single", "options": ["Yes", "No"], "weight": 2}])
    expect(code == 1 and "unknown key 'weight'" in e, "an unknown key was accepted: %r" % e)
    code, e, _ = errs([{"id": "q1", "type": "single", "options": ["Yes", True]}])
    expect(code == 1 and "options must be a list" in e, "true was accepted as an option: %r" % e)
    code, e, _ = errs(ok, collection={"invited": "40"})
    expect(code == 1 and "invited must be a whole number" in e, "invited given as text was accepted: %r" % e)
    code, e, r = errs(ok, collection={"invited": 40, "reached": "link emailed to all 40 attendees"})
    expect(code == 0 and r["overview"]["responded_of_invited"]["count"] == 2 and r["overview"]["responded_of_invited"]["n"] == 40, "responded of invited is wrong")
    code, e, _ = errs(ok + [ok[0]])
    expect(code == 1 and "the id is repeated" in e, "a repeated question id was accepted: %r" % e)


def test_bad_arguments_exit_2(c):
    data = c.csv("respondent,q1,q2\na,Yes,X\nb,No,Y\n")

    def bad(args, needle):
        code, out, err = c.cli(*args)
        expect(code == 2 and needle in err and "Traceback" not in err and out == "", "%r should exit 2 mentioning %r: exit %d, %r" % (args, needle, code, err))

    def good(args):
        code, out, err = c.cli(*args)
        expect(code == 0, "%r should run: exit %d, %r" % (args, code, err or out[-200:]))

    bad([data, "--frobnicate"], "unknown option --frobnicate")
    bad([data, "--level"], "--level needs 1 value")
    bad([data, "--level", "50"], "above 50 and below 100")
    good([data, "--level", "50.1"])
    bad([data, "--level", "100"], "above 50 and below 100")
    good([data, "--level", "99.9"])
    bad([data, "--level", "ninety"], "above 50 and below 100")
    bad([data, "--group-fraction", "0.09"], "from 0.1 to 0.5")
    good([data, "--group-fraction", "0.1"])
    bad([data, "--group-fraction", "0.51"], "from 0.1 to 0.5")
    good([data, "--group-fraction", "0.5"])
    bad([data, "--compare", "q1=Yes"], "go together")
    bad([data, "--compare", "q1", "--by", "q2"], "QUESTION=OPTION")
    bad([data, "--compare", "q1=Perhaps", "--by", "q2"], "is not an option of q1")
    bad([data, "--compare", "q1=Yes", "--by", "q2", "--pair", "X", "Q"], "is not a group of q2")
    good([data, "--compare", "q1=Yes", "--by", "q2", "--pair", "X", "Y"])
    bad([data, "--codebook", data], "only used with --themes")
    bad([data, data], "expected one responses file")
    bad(["--json"], "expected one responses file")
    bad([data, "--instrument", c.tmp / "none.json"], "cannot read")
    code, out, _ = c.cli()
    expect(code == 2 and "Usage" in out, "no arguments must print the usage and exit 2")


# ---------------------------------------------------------------- behaviour that always holds

def test_names_are_replaced_by_ids(c):
    data, inst = c.csv(TEXT_CSV), c.inst(TEXT_INST)
    map_path = c.path(".csv")
    code, out, _ = c.cli(data, "--instrument", inst, "--id-map", map_path)
    code2, js, _ = c.cli(data, "--instrument", inst, "--json")
    for name in ("Ana", "Ben", "Cal", "Dee", "Eli", "Fay"):
        expect(name not in out and name not in js, "the respondent value %r appears in the output" % name)
    expect("R01" in js and "replaced by R01 to R06 in file order" in out, "replacement ids are missing")
    expect(map_path.read_text(encoding="utf-8").splitlines()[:2] == ["id,respondent", "R01,Ana"] and "keep it private" in out, "the id map is wrong")
    code, out, _ = c.cli(data, "--instrument", inst, "--keep-ids")
    expect(code == 0 and "skipped 2 = 33% of those shown (Eli, Fay)" in out, "--keep-ids must print the values as given")


def test_tiny_sample_still_reports_and_never_says_significant(c):
    # Three respondents. Yes = 2 of 3 (67%); Wilson 95 per cent interval:
    #   centre = (0.666667 + 3.841459 / 6) / (1 + 3.841459 / 3) = 1.306910 / 2.280486 = 0.573084
    #   half = 1.959964 * sqrt(0.666667 * 0.333333 / 3 + 3.841459 / 36) / 2.280486 = 1.959964 * sqrt(0.074074 + 0.106707) / 2.280486 = 0.365422
    #   interval = 0.207662 to 0.938506 -> 21% to 94%
    data = c.csv("respondent,q1,grp\na,Yes,A\nb,Yes,B\nc,No,B\n")
    inst = c.inst({"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No"]}, {"id": "grp", "type": "single", "options": ["A", "B"]}]})
    code, out, _ = c.cli(data, "--instrument", inst, "--cross", "grp", "q1", "--compare", "q1=Yes", "--by", "grp")
    expect(code == 0 and "Yes  2 of 3 who answered (67%, interval 21% to 94%)" in out, "a three-person file must still be described with counts and an interval:\n" + out)
    low = out.lower()
    for word in ("significant", "minimum sample", "too few respondents", "insufficient", "not enough respondents", "at least 30"):
        expect(word not in low, "the output says %r; small samples are described, not refused, and 'significant' is never printed" % word)
    code, r = c.js(data, "--instrument", inst)
    y = option(question(r, "q1"), "Yes")["of_answered"]
    expect(near(y["interval"][0], 0.2077, 1e-4) and near(y["interval"][1], 0.9385, 1e-4), "interval for 2 of 3 is wrong: %r" % y["interval"])
    # One respondent is still a description.
    code, out, _ = c.cli(c.csv("respondent,q1\na,Yes\n"), "--instrument", c.inst({"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No"]}]}))
    expect(code == 0 and "1 of 1 who answered (100%, interval 21% to 100%)" in out, "one respondent must still be reported")


def test_no_instrument_infers_and_says_so(c):
    data = c.csv("respondent,pick,rate,many,age,say,say__note\n"
                 "a,Tea,4,x;y,34,The room was far too cold for a full day,brr\n"
                 "b,Coffee,5,x,51,I would have liked the slides beforehand,\n"
                 "c,Tea,4,y;z,28,Great facilitator and a good pace,\n"
                 "d,Tea,2,,47.5,,\n")
    code, r = c.js(data)
    types = {q["id"]: (q["type"], q["inferred"]) for q in r["questions"]}
    expect(code == 0 and types == {"pick": ("single", True), "rate": ("scale", True), "many": ("multi", True), "age": ("number", True), "say": ("text", True), "say__note": ("text", True)},
           "inferred types are %r" % types)
    adv = " | ".join(r["advisories"])
    for needle in ("INFERRED pick: single choice", "INFERRED rate: a scale", "INFERRED many: several choices", "INFERRED age: a number", "INFERRED say: free text",
                   "no instrument was given", "how respondents were reached is NOT STATED"):
        expect(needle in adv, "the output does not say %r" % needle)
    expect(r["quiz"] is None, "nothing can be scored without an instrument")
    # rate holds 4, 5, 4, 2: inferred as a scale, and summarised as numbers too in case it is a count. Median of 2 4 4 5 is 4.
    rate = question(r, "rate")
    expect([o["option"] for o in rate["options"]] == ["2", "4", "5"] and rate["numbers"]["median"] == 4 and rate["numbers"]["n"] == 4, "inferred numeric scale is wrong: %r" % rate.get("numbers"))
    # A choose-any column with many combinations is still several choices, not free text: 4 options give 15
    # different non-empty cells here, more than the 12 distinct values that would otherwise suggest free text.
    import itertools
    combos = [";".join(x) for n in range(1, 5) for x in itertools.combinations(["w", "x", "y", "z"], n)]
    code, r2 = c.js(c.csv("respondent,m\n" + "".join("p%d,%s\n" % (i, v) for i, v in enumerate(combos))))
    m = question(r2, "m")
    # Each option appears in 8 of the 15 combinations.
    expect(code == 0 and m["type"] == "multi" and [(o["option"], o["count"]) for o in m["options"]] == [("w", 8), ("x", 8), ("y", 8), ("z", 8)], "a choose-any column with 15 combinations was inferred as %r" % m["type"])
    # Free text that happens to contain semicolons stays free text: no part recurs.
    code, r3 = c.js(c.csv("respondent,say\na,Too long; too warm\nb,Good pace; nice room\nc,Fine\n"))
    expect(question(r3, "say")["type"] in ("text", "single") and question(r3, "say")["type"] != "multi", "free text with semicolons was inferred as several choices")
    # A file with only free text says so and does not claim everyone completed the closed questions.
    code, out, _ = c.cli(c.csv("respondent,say\na,The room was far too cold for a full day\nb,\n"))
    expect(code == 0 and "There are no closed questions in this file" in out and "Answered every closed question" not in out, "a free-text-only file printed a completeness figure")


def test_overview_states_who_answered_first(c):
    inst = dict(SKIP_INST, title="Demo", collection={"reached": "paper form handed out at the door", "invited": 25, "missing": "people who left before the end"})
    code, out, _ = c.cli(c.csv(SKIP_CSV), "--instrument", c.inst(inst))
    lines = out.splitlines()
    expect(code == 0 and lines[1] == "WHO ANSWERED" and "Responded: 10 of 25 invited (40%). The other 15 are not described by anything below." in out, "the overview must come first and give the response count")
    expect("How they were reached: paper form handed out at the door" in out and "Who is missing: people who left before the end" in out, "reach and who is missing must be printed")
    expect(out.index("WHO ANSWERED") < out.index("QUESTIONS"), "who answered must come before the questions")
    # q1 was answered by 8 of 10; q2 was shown to the 6 who said Yes and answered by 4 of them. So 4 respondents (p01 to p04)
    # answered every closed question shown to them, plus p07 and p08, who said No and were never shown q2: 6 of 10.
    expect("Answered every closed question shown to them: 6 of 10 respondents (60%)" in out, "the completeness count is wrong")
    code, out, _ = c.cli(c.csv(SKIP_CSV), "--instrument", c.inst(dict(SKIP_INST, collection={"invited": 5})))
    expect(code == 0 and "collection.invited is 5 but there are 10 respondents" in out, "more respondents than invited must be reported, not turned into a percentage over 100")
    # p09 and p10 answered nothing at all: counted, and said so.
    expect("2 respondent(s) answered nothing (R09, R10)" in out, "respondents who answered nothing must be reported")


def test_output_is_ascii_and_standard_json(c):
    text = "respondent,q5\na,Caf" + chr(0xe9) + " was " + chr(0x201c) + "fine" + chr(0x201d) + " " + chr(0x2014) + " mostly\nb,ok then\n"
    data = c.csv(text)
    before = data.read_bytes()
    for extra in ((), ("--json",)):
        code, out, _ = c.cli(data, *extra)
        expect(code == 0 and all(ord(ch) < 128 for ch in out), "output is not plain ASCII")

    def refuse(x):
        raise ValueError(x)
    json.loads(c.cli(data, "--json")[1], parse_constant=refuse)
    # A denominator of zero gives null, never NaN: nobody answered q1.
    code, out, _ = c.cli(c.csv("respondent,q1\na,\nb,\n"), "--instrument", c.inst({"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No"]}]}), "--json")
    r = json.loads(out, parse_constant=refuse)
    y = option(question(r, "q1"), "Yes")
    expect(code == 0 and y["of_answered"] == {"count": 0, "n": 0, "proportion": None, "percent": None, "interval": None, "interval_percent": None}, "0 of 0 must give nulls: %r" % y["of_answered"])
    code, out, _ = c.cli(c.csv("respondent,q1\na,\nb,\n"), "--instrument", c.inst({"questions": [{"id": "q1", "type": "single", "options": ["Yes", "No"]}]}))
    expect("0 of 0 who answered (no percentage: nobody in the denominator)" in out, "0 of 0 must be printed as a count with no percentage")
    expect(data.read_bytes() == before, "the responses file was modified")


def test_templates_in_assets_are_usable(c):
    # The instrument template handed to users must itself be a valid instrument, and the codebook template a valid codebook.
    assets = HERE.parent / "assets"
    data = c.csv("respondent,q1,q2,q3,q4,q5,q6,q7\na,Yes,Agree,First;Third,3,Some words here,B,Often\nb,No,Disagree,Second,5,,C,\n")
    code, r = c.js(data, "--instrument", assets / "instrument-template.json")
    expect(code == 1 and len(r["errors"]) == 3 and all("REPLACE" in e for e in r["errors"]), "the untouched template should be refused only for its 3 REPLACE texts: %r" % r["errors"])
    filled = json.loads((assets / "instrument-template.json").read_text(encoding="utf-8").replace("REPLACE", "Filled in"))
    code, r = c.js(data, "--instrument", c.inst(filled))
    expect(code == 0 and not r["errors"], "the filled-in instrument template was refused: %r" % r["errors"])
    q7 = question(r, "q7")
    expect((q7["shown"], q7["not_shown"]) == (1, 1) and r["quiz"]["items"] == 1, "the template's routing or quiz item did not behave as described")
    book = c.mod.read_codebook(str(assets / "codebook-template.csv"))
    expect(list(book) == ["short_code_name", "second_code"], "the codebook template was not read: %r" % list(book))


# ---------------------------------------------------------------- the elicitor collector's own layout

# SYNTHETIC. This text is what the elicitor skill's collect_responses.py wrote on 2026-10-09 when it
# merged nine invented reply files for an invented tool-library questionnaire. It is kept here byte
# for byte so the test needs no other skill installed. The collector's layout is described in its
# own docstring: source, instrument, version, finished, then one column per question, "<id>.note"
# columns, "(skipped)" and "(not shown)" markers, " | " between several choices, and an apostrophe
# put before text that begins with =, +, - or @.
COLLECTOR_CSV = (
    'source,instrument,version,finished,visits,found-tool,found-tool.note,why-not,borrowed,recommend,one-change\n'
    'reply-01.txt#1,tool-library-feedback,2,2026-09-11T01:15:00Z,Weekly,Yes,,(not shown),Drill | Ladder,Likely,Longer Saturday hours.\n'
    'reply-02.txt#1,tool-library-feedback,2,2026-09-12T02:15:00Z,Weekly,Yes,,(not shown),Drill,Likely,(skipped)\n'
    'reply-03.txt#1,tool-library-feedback,2,2026-09-13T03:15:00Z,Monthly,Partly,"It had the drill, not the sander.",The sander was booked out for three weeks.,Sander | Drill,Maybe,\'- a waiting list would help\n'
    "reply-04.txt#1,tool-library-feedback,2,2026-09-14T04:15:00Z,Monthly,No,,No pressure washer in the catalogue.,Sander,Unlikely,'= cheaper late fees\n"
    'reply-05.txt#1,tool-library-feedback,2,2026-09-15T05:15:00Z,Rarely,Yes,,(not shown),Ladder,Likely,"Nothing, it works."\n'
    'reply-06.txt#1,tool-library-feedback,2,2026-09-16T06:15:00Z,Weekly,Partly,,(skipped),Drill | Ladder | Sander,Likely,Longer Saturday hours and a waiting list.\n'
    'reply-07.txt#1,tool-library-feedback,2,2026-09-17T07:15:00Z,Monthly,Yes,,(not shown),(skipped),Maybe,(skipped)\n'
    'reply-08.txt#1,tool-library-feedback,2,2026-09-18T08:15:00Z,Rarely,No,Asked twice.,Nobody at the desk knew where the ladder was.,Ladder,(skipped),Staff who know the stock.\n'
    'reply-09.txt#1,tool-library-feedback,2,2026-09-19T09:15:00Z,Weekly,Yes,,(not shown),Drill | Pressure washer,Likely,\n')
COLLECTOR_INSTRUMENT = {
    "title": "SYNTHETIC tool library feedback",
    "collection": {"reached": "a link on the borrowing receipt for one fortnight", "invited": 40, "missing": "members who did not borrow in that fortnight"},
    "questions": [
        {"id": "visits", "type": "single", "options": ["Weekly", "Monthly", "Rarely"]},
        {"id": "found-tool", "type": "single", "options": ["Yes", "Partly", "No"]},
        {"id": "why-not", "type": "text", "shown_if": {"question": "found-tool", "in": ["Partly", "No"]}},
        {"id": "borrowed", "type": "multi", "options": ["Drill", "Ladder", "Sander", "Pressure washer"]},
        {"id": "recommend", "type": "scale", "options": ["Unlikely", "Maybe", "Likely"]},
        {"id": "one-change", "type": "text"}]}


def test_elicitor_collector_layout_is_read_as_written(c):
    """The nine rows, counted by hand from COLLECTOR_CSV:
      visits       Weekly 4 (rows 1, 2, 6, 9), Monthly 3 (3, 4, 7), Rarely 2 (5, 8); all 9 answered.
      found-tool   Yes 5 (1, 2, 5, 7, 9), Partly 2 (3, 6), No 2 (4, 8).
      why-not      marked (not shown) for the 5 who said Yes; of the 4 shown, 3 answered (3, 4, 8) and row 6 is marked (skipped).
      borrowed     row 7 is marked (skipped); of the 8 who answered: Drill 5 (1, 2, 3, 6, 9), Ladder 4 (1, 5, 6, 8), Sander 3 (3, 4, 6), Pressure washer 1 (9).
      recommend    Likely 5 (1, 2, 5, 6, 9), Maybe 2 (3, 7), Unlikely 1 (4); row 8 is marked (skipped).
      one-change   6 answered (1, 3, 4, 5, 6, 8); rows 2 and 7 are marked (skipped) and row 9 is empty: 3 skipped.
      found-tool.note  rows 3 and 8.
    Wilson for Drill, 5 of 8: centre = (0.625 + 3.841459/16) / (1 + 3.841459/8) = 0.865091 / 1.480182 = 0.584449;
      half = 1.959964 * sqrt(0.625 * 0.375 / 8 + 3.841459/256) / 1.480182 = 1.959964 * 0.210483 / 1.480182 = 0.278708;
      interval 0.305741 to 0.863157."""
    f, inst = c.csv(COLLECTOR_CSV), c.inst(COLLECTOR_INSTRUMENT)
    code, r = c.js(f, "--instrument", inst)
    expect(code == 0 and not r["errors"], "the collector's file was refused: %s" % r["errors"])
    expect(r["overview"]["respondents"] == 9 and r["overview"]["questions"] == 6, "9 respondents and 6 questions, got %s and %s" % (r["overview"]["respondents"], r["overview"]["questions"]))
    expect(r["layout"]["layout"] == "elicitor collector" and r["layout"]["instruments"] == [{"id": "tool-library-feedback", "version": "2"}], "layout facts: %s" % r["layout"])
    expect(r["layout"]["marked_skipped"] == 5 and r["layout"]["marked_not_shown"] == 5 and r["layout"]["spreadsheet_guards_removed"] == 2, "marks: %s" % r["layout"])
    for qid, want in (("visits", {"Weekly": 4, "Monthly": 3, "Rarely": 2}), ("found-tool", {"Yes": 5, "Partly": 2, "No": 2}),
                      ("borrowed", {"Drill": 5, "Ladder": 4, "Sander": 3, "Pressure washer": 1}), ("recommend", {"Unlikely": 1, "Maybe": 2, "Likely": 5})):
        q = question(r, qid)
        got = dict((o["option"], o["count"]) for o in q["options"])
        expect(got == want, "%s counts are %s; counted by hand as %s" % (qid, got, want))
    w, b, rec, one = question(r, "why-not"), question(r, "borrowed"), question(r, "recommend"), question(r, "one-change")
    expect((w["shown"], w["not_shown"], w["answered"], w["skipped"]) == (4, 5, 3, 1), "why-not shown, not shown, answered, skipped = %s; by hand (4, 5, 3, 1)" % ((w["shown"], w["not_shown"], w["answered"], w["skipped"]),))
    expect((b["shown"], b["answered"], b["skipped"], b["skipped_ids"]) == (9, 8, 1, ["R07"]), "borrowed: %s" % ((b["shown"], b["answered"], b["skipped"], b["skipped_ids"]),))
    expect((rec["answered"], rec["skipped"], rec["skipped_ids"]) == (8, 1, ["R08"]), "recommend: %s" % ((rec["answered"], rec["skipped"]),))
    expect((one["answered"], one["skipped"], one["skipped_ids"]) == (6, 3, ["R02", "R07", "R09"]), "one-change: a (skipped) mark and an empty cell are both skips: %s" % ((one["answered"], one["skipped"], one["skipped_ids"]),))
    drill = option(b, "Drill")["of_answered"]
    expect(drill["count"] == 5 and drill["n"] == 8 and near(drill["interval"][0], 0.3057, 6e-5) and near(drill["interval"][1], 0.8632, 6e-5), "Drill 5 of 8: %s; by hand 0.3057 to 0.8632" % drill)
    note = question(r, "found-tool__note")
    expect(note["note_of"] == "found-tool" and note["answered"] == 2, "the .note column must be read as the note on found-tool, with 2 notes: %s" % note)
    code, out, err = c.cli(f, "--instrument", inst)
    expect(code == 0 and "(skipped)" not in out.split("NOTES")[0] and "(not shown)" not in out.split("NOTES")[0], "a marker was counted or printed as an answer")
    expect("Invited: 40. Responded: 9 of 40 invited (23%)" in out and "elicitor collector's layout (instrument 'tool-library-feedback' version 2)" in out, out[-900:])
    expect("reply-0" not in out, "the source file names must be replaced by ids unless --keep-ids is given")
    sheet = c.path(".csv")
    code, out, err = c.cli(f, "--instrument", inst, "--coding-sheet", sheet, "--skip-questions")
    text = sheet.read_text(encoding="utf-8")
    expect("R03,one-change,'- a waiting list would help," in text and "R04,one-change,'= cheaper late fees," in text and "''" not in text,
           "in the sheet a passage that begins with - or = carries one apostrophe, so a spreadsheet does not run it: %s" % text)
    expect("2 passage(s) begin with =, +, - or @" in out, "the sheet's guard must be announced: %s" % out[-400:])
    coded = c.path(".csv")
    coded.write_text(text.replace("would help,,", "would help,,wait").replace("late fees,,", "late fees,,fees"), encoding="utf-8")
    code, rt = c.js(f, "--instrument", inst, "--themes", coded)
    expect(code == 0 and not any("differ from the responses file" in a for a in rt["advisories"]), "the guard is not an edit: %s" % rt["advisories"])
    expect(not any("'" in str(v) for t in rt["themes"]["all_free_text"]["themes"] for v in t["respondent_ids"]), "ids are unchanged")
    code, rj = c.js(f, "--instrument", inst)
    expect(question(rj, "one-change")["answered"] == 6, "the guard does not change what was answered")
    expect(text.count("\n") == 1 + 3 + 6 + 2, "the sheet holds 3 why-not answers, 6 one-change answers and 2 notes, got %d lines" % (text.count("\n") - 1))
    expect("(skipped)" not in text and "(not shown)" not in text, "a marker reached the coding sheet as if it were an answer")
    # with no instrument the file's own marks still separate not shown from skipped
    code, r2 = c.js(f)
    w2 = question(r2, "why-not")
    expect(code == 0 and (w2["shown"], w2["not_shown"], w2["answered"], w2["skipped"]) == (4, 5, 3, 1), "without an instrument: %s" % ((w2["shown"], w2["not_shown"], w2["answered"], w2["skipped"]),))
    b2 = question(r2, "borrowed")
    expect(b2["type"] == "multi" and dict((o["option"], o["count"]) for o in b2["options"]) == {"Drill": 5, "Ladder": 4, "Sander": 3, "Pressure washer": 1}, "inferred multi on ' | ': %s" % b2.get("options"))
    # an instrument whose routing disagrees with the file's marks is reported, and the file's marks are used
    wrong = json.loads(json.dumps(COLLECTOR_INSTRUMENT))
    wrong["questions"][2]["shown_if"] = {"question": "found-tool", "in": ["No"]}
    code, r3 = c.js(f, "--instrument", c.inst(wrong))
    w3 = question(r3, "why-not")
    expect(code == 0 and (w3["shown"], w3["answered"], w3["skipped"]) == (4, 3, 1) and any("why-not: for 2 respondent(s) the file and the instrument's routing disagree" in a for a in r3["advisories"]),
           "rows 3 and 6 said Partly, which this routing would hide, yet the file shows one answer and one skip: shown %s, notes %s" % (w3["shown"], r3["advisories"]))
    # the valid neighbour of the refusal: a file with neither a respondent column nor the collector's four
    code, out, err = c.cli(c.csv(COLLECTOR_CSV.replace("source,instrument,version,finished", "source,instrument,version,ended")))
    expect(code == 2 and "no column called respondent" in err and "elicitor collector's layout" in err and "Traceback" not in err, "exit %d: %s" % (code, err))
    # the collector's other way of writing several choices is not guessed at: it is refused with the cell named
    code, r4 = c.js(c.csv(COLLECTOR_CSV.replace("Drill | Ladder,Likely", '"[""Drill"", ""Ladder""]",Likely')), "--instrument", inst)
    expect(code == 1 and any("borrowed" in e and "not an option" in e for e in r4["errors"]), "a JSON list in a cell must be refused, not half-read: %s" % r4["errors"])


# SYNTHETIC. What collect_responses.py wrote on 2026-10-09 from the elicitor skill's own fixture reply
# (one respondent): tally columns, two note columns, a note with quotation marks and line breaks.
COLLECTOR_ONE = 'source,instrument,version,finished,useful,useful.note,pace,pace-where,kept,kept.note,recommend,one-change,tally:rated-high,tally:rated-high:of\nresponse_survey.txt#1,fixture-survey,1,2026-10-08T16:25:54Z,1,"Note on useful: ""quoted"", 100% & <tag>?\nSecond line of the note.",About right,(not shown),The group exercise | The questions at the end,"Note on kept: ""quoted"", 100% & <tag>?\nSecond line of the note.",(skipped),"Text for one-change: 50% sure & <not> certain.\n\n  An indented second paragraph.\nThird line.",0,2\n'


def test_elicitor_collector_tallies_and_notes_are_placed(c):
    """One row: useful = 1; a note on useful; pace answered; pace-where marked (not shown); kept holds two
    choices joined by " | "; a note on kept; recommend marked (skipped); one-change is three lines of text.
    The two tally columns are the questionnaire's own counts and are left out of the analysis."""
    code, r = c.js(c.csv(COLLECTOR_ONE))
    expect(code == 0 and r["overview"]["respondents"] == 1 and r["overview"]["questions"] == 6, "one respondent, six questions: %s" % r.get("errors"))
    lay = r["layout"]
    expect(lay["tally_columns_not_analysed"] == ["tally:rated-high", "tally:rated-high:of"] and lay["note_columns"] == 2 and lay["marked_skipped"] == 1 and lay["marked_not_shown"] == 1, "layout: %s" % lay)
    ids = [q["id"] for q in r["questions"]]
    expect(not [i for i in ids if i.startswith("tally") or i in ("instrument", "version", "finished", "source")], "a bookkeeping column was analysed as a question: %s" % ids)
    expect(any("tally column(s) tally:rated-high, tally:rated-high:of were not analysed" in a and "not a score on a validated scale" in a for a in r["advisories"]), "the tally note is missing: %s" % r["advisories"])
    pw, rec = question(r, "pace-where"), question(r, "recommend")
    expect((pw["shown"], pw["not_shown"]) == (0, 1) and (rec["shown"], rec["skipped"]) == (1, 1), "pace-where is not shown, recommend is skipped: %s %s" % ((pw["shown"], pw["not_shown"]), (rec["shown"], rec["skipped"])))
    sheet = c.path(".csv")
    c.cli(c.csv(COLLECTOR_ONE), "--coding-sheet", sheet)
    text = sheet.read_text(encoding="utf-8")
    expect("An indented second paragraph." in text and "Second line of the note." in text, "multi-line text and notes must reach the coding sheet whole: %s" % text[:300])


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

# Broken copies of the script. Each replaces text that must occur exactly once in analyse_responses.py,
# and names the test that has to catch it.
PLANTED = [
    {"name": "skipped respondents silently dropped from denominators (an empty cell treated as never shown)",
     "caught_by": "test_skipped_respondents_stay_in_the_denominator",
     "edits": [("            if not cell:\n                status.append(\"skipped\")\n",
                "            if not cell:\n                status.append(\"not_shown\")\n")]},
    {"name": "themes counted by mention instead of by respondent",
     "caught_by": "test_themes_count_respondents_not_mentions",
     "edits": [("            who = sorted({k[0] for k in keys if c in coded.get(k, [])}, key=order.get)\n",
                "            who = sorted([k[0] for k in keys if c in coded.get(k, [])], key=order.get)\n")]},
    {"name": "normal-approximation (Wald) half-width used in place of the Wilson one",
     "caught_by": "test_wilson_interval_hand_worked",
     "edits": [("    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / (1.0 + z2 / n)\n",
                "    half = z * math.sqrt(p * (1.0 - p) / n)\n")]},
    {"name": "discrimination computed as lower minus upper",
     "caught_by": "test_discrimination_index_hand_worked",
     "edits": [("entry[\"upper\"][\"correct\"] / len(up) - entry[\"lower\"][\"correct\"] / len(lo), 2)",
                "entry[\"lower\"][\"correct\"] / len(lo) - entry[\"upper\"][\"correct\"] / len(up), 2)")]},
    {"name": "difference interval built from the wrong pair of Wilson limits",
     "caught_by": "test_difference_interval_hand_worked",
     "edits": [("    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)\n",
                "    return d, d - math.sqrt((p1 - l1) ** 2 + (p2 - l2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (u2 - p2) ** 2)\n")]},
    {"name": "the collector's (not shown) mark counted as a skip, so routed-past respondents become non-response",
     "caught_by": "test_elicitor_collector_layout_is_read_as_written",
     "edits": [("                elif cell == MARK_NOT_SHOWN:\n                    marks[(n, name)] = \"not_shown\"\n",
                "                elif cell == MARK_NOT_SHOWN:\n                    marks[(n, name)] = \"skipped\"\n")]},
    {"name": "the collector's (skipped) mark left in the cell and counted as an answer",
     "caught_by": "test_elicitor_collector_layout_is_read_as_written",
     "edits": [("                if cell == MARK_SKIPPED:\n                    marks[(n, name)] = \"skipped\"\n                    cell = \"\"\n",
                "                if False:\n                    marks[(n, name)] = \"skipped\"\n                    cell = \"\"\n")]},
]


def run_suite(script, only=None, quiet=False):
    """Run the tests against one script. Returns {test name: None or failure message}."""
    results = {}
    c = Ctx(script)
    try:
        for t in TESTS:
            if only and t.__name__ != only:
                continue
            try:
                t(c)
                results[t.__name__] = None
            except Exception as e:  # noqa: BLE001  a crash in the script under test is a failure, not a harness error
                results[t.__name__] = "%s: %s" % (type(e).__name__, str(e)[:400])
            if not quiet:
                msg = results[t.__name__]
                print("%-5s %s%s" % ("PASS" if msg is None else "FAIL", t.__name__, "" if msg is None else "\n        " + msg))
    finally:
        c.close()
    return results


def run_planted(script):
    print("Step 1: the real script must pass every test.")
    real = run_suite(script, quiet=True)
    bad = [n for n, msg in real.items() if msg is not None]
    print("  %d of %d tests pass on %s" % (len(real) - len(bad), len(real), Path(script).name))
    ok = not bad
    for n in bad:
        print("  FAIL %s: %s" % (n, real[n]))
    print("Step 2: each broken copy must be caught by its named test.")
    src = Path(script).read_text(encoding="utf-8")
    for i, plant in enumerate(PLANTED, 1):
        text = src
        for old, new in plant["edits"]:
            if text.count(old) != 1:
                print("  FAIL planted failure %d could not be built: its target text occurs %d times in the script, not once" % (i, text.count(old)))
                ok = False
                text = None
                break
            text = text.replace(old, new)
        if text is None:
            continue
        d = Path(tempfile.mkdtemp(prefix="analyse_planted_"))
        try:
            broken = d / "analyse_responses.py"
            broken.write_text(text, encoding="utf-8")
            res = run_suite(broken, quiet=True)
        finally:
            shutil.rmtree(str(d), ignore_errors=True)
        failed = sorted(n for n, msg in res.items() if msg is not None)
        caught = plant["caught_by"] in failed
        ok = ok and caught
        print("  %s planted failure %d: %s" % ("CAUGHT" if caught else "MISSED", i, plant["name"]))
        print("         named test: %s -> %s" % (plant["caught_by"], "failed, as it must" if caught else "PASSED on the broken copy"))
        if caught:
            print("         message: %s" % res[plant["caught_by"]][:230])
        print("         all tests failing on this copy: %s" % (", ".join(failed) or "none"))
    print("RESULT: %s" % ("PASS. The real script passes and every planted failure is caught by its named test." if ok else "FAIL."))
    return 0 if ok else 1


def main(argv):
    script, only, planted, it = HERE / "analyse_responses.py", None, False, iter(argv)
    for a in it:
        if a == "--planted":
            planted = True
        elif a in ("--script", "--only"):
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_analyse_responses: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--script":
                script = Path(v)
            else:
                only = v
        else:
            print("test_analyse_responses: unknown argument " + a, file=sys.stderr)
            return 2
    if not Path(script).is_file():
        print("test_analyse_responses: cannot find the script %s" % script, file=sys.stderr)
        return 2
    if only and only not in [t.__name__ for t in TESTS]:
        print("test_analyse_responses: no test is called %s" % only, file=sys.stderr)
        return 2
    if planted:
        return run_planted(script)
    results = run_suite(script, only)
    failed = [n for n, msg in results.items() if msg is not None]
    print("RESULT: %d of %d tests passed%s" % (len(results) - len(failed), len(results), "" if not failed else "; FAILED: " + ", ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
