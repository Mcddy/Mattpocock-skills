#!/usr/bin/env python3
"""Tests for effect.py and extraction_check.py against hand-worked and published values.
Standard library only.

Usage:
  python test_effect.py [--scripts DIR] [--only NAME[,NAME...]] [--list] [--planted] [--workdir DIR] [--json]

  --scripts DIR   the folder holding the effect.py and extraction_check.py to test (default: this folder)
  --only NAMES    run only these tests
  --list          print the test names and stop
  --planted       build broken copies of the scripts, one planted fault each, and require the named
                  tests to fail on each copy. Shows that the tests can fail
  --workdir DIR   where to make temporary folders (default: the system temporary folder)

Where the expected values come from. Each is written out in the test beside its arithmetic.
  HAND       worked with a calculator from the formula, shown step by step in a comment
  NEWCOMBE   the worked examples of Newcombe (1998), Statistics in Medicine 17:873-890, Table II,
             method 10. The limits used here (56/70 against 48/80: 0.0524 to 0.3339; 9/10 against
             3/10: 0.1705 to 0.8090; 10/10 against 0/20: 0.6791 to 1.0000) and a fourth example
             (84/101 against 89/105: -0.1177 to 0.0851) were read from paper 127 of the WUSS 2016
             proceedings, which reprints them. Newcombe's own paper was not opened
  WILSON     81/263, 15/148, 0/20 and 1/29 are the examples of Newcombe (1998), Statistics in
             Medicine 17:857-872, Table I (the R DescTools manual names them as such). The limits
             are the author's recollection of that table, each reproduced by hand; no page
             printing them was retrieved. The Newcombe limits above depend on the same function
  KATZ       the SciPy documentation for scipy.stats.contingency.relative_risk (v1.12): 10 of 75
             against 12 of 225 gives 2.5 with a 95 percent interval 1.1261564 to 5.5498508
  BLAND      Bland and Altman (2000), BMJ 320:1468: 141 of 561 against 928 of 14,453 gives an odds
             ratio of 4.89, 95 percent interval 4.00 to 5.99
  NIST       NIST/SEMATECH e-Handbook of Statistical Methods: section 1.3.5.3 for the pooled
             standard deviation 6.34260 and the equal-variance statistic -12.62059 (249 and 79
             observations), and the unequal-variance formulas; section 1.3.6.7.2 for critical
             values of Student's t
  ALTMAN     the number needed is 1 / |risk difference| and has no finite interval when the
             interval for the difference includes zero (Altman 1998, BMJ 317:1309-1312, as
             described in the R meta package manual; the article itself is behind a login and
             was not opened). Rounding up is the convention in the Cochrane Handbook (5.1, 12.5.4)

  GRIM       the two worked examples in the preprint of Brown and Heathers' GRIM paper (PeerJ
             Preprints 2064, read 2026-10-09): a mean of 5.19 from 28 people and a mean of 6.28
             from 52 people are both impossible
  CLOSED     tails that have a closed form and can be worked by hand: t with 1 and 2 degrees of
             freedom, chi-square with 1, 2 and 4, F with 1 or 2 numerator degrees of freedom, and
             z through the complementary error function. Used for check-p and for the p value
             of a two-by-two table

What it cannot tell: whether these are the right methods for a given paper. That is a judgement.

Exit codes: 0 every test passed. 1 a test failed (or, with --planted, a planted fault was not
caught). 2 bad arguments.
"""
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TESTS = []
Z95 = 1.959964


def test(fn):
    TESTS.append((fn.__name__[2:], fn))
    return fn


def close(got, want, tol, what):
    assert got is not None and abs(got - want) <= tol, "%s: got %r, expected %r (tolerance %g)" % (what, got, want, tol)


class Ctx(object):
    def __init__(self, scripts, workdir):
        self.scripts = Path(scripts)
        self.root = Path(tempfile.mkdtemp(prefix="effect-test-", dir=workdir))
        self._m = None
        self._n = 0

    def cleanup(self):
        shutil.rmtree(str(self.root), ignore_errors=True)

    def m(self):
        if self._m is None:
            spec = importlib.util.spec_from_file_location("effect_under_test_%d" % id(self), str(self.scripts / "effect.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._m = mod
        return self._m

    def run(self, script, *args):
        p = subprocess.run([sys.executable, "-B", str(self.scripts / script)] + [str(a) for a in args], capture_output=True, timeout=60)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

    def effect(self, *args):
        return self.run("effect.py", *args)

    def js(self, *args):
        code, out, err = self.effect(*(list(args) + ["--json"]))
        assert "Traceback" not in err, err[-300:]

        def refuse(const):
            raise ValueError("non-standard JSON constant %s" % const)

        try:
            return code, json.loads(out, parse_constant=refuse)
        except ValueError as e:
            raise AssertionError("output is not standard JSON (%s): %s" % (e, out[:200]))

    def refused(self, *args):
        code, out, err = self.effect(*args)
        assert "Traceback" not in err, "a traceback was printed: " + err[-300:]
        assert code == 2 and err.startswith("effect:") and err.strip().count("\n") == 0 and not out.strip(), \
            "wanted a refusal (exit 2, one line on stderr, nothing computed) for %s; got exit %d, stdout %r, stderr %r" % (" ".join(args), code, out[:80], err[:160])
        return err

    def accepted(self, *args):
        code, out, err = self.effect(*args)
        assert code == 0 and "Traceback" not in err, "wanted %s to be accepted; got exit %d, %s" % (" ".join(args), code, err[:200])
        return out

    def extraction(self, data, name="x.json"):
        self._n += 1
        f = self.root / ("%03d-%s" % (self._n, name))
        f.write_bytes(data if isinstance(data, bytes) else json.dumps(data, indent=1).encode("utf-8"))
        code, out, err = self.run("extraction_check.py", f, "--json")
        assert "Traceback" not in err, err[-300:]
        return code, (json.loads(out) if out.strip().startswith("{") else None), err


# ---------------------------------------------------------------- intervals for proportions

@test
def t_wilson_matches_hand_worked_values(ctx):
    m = ctx.m()
    z = m.z_for(95)
    close(z, Z95, 5e-7, "the 95 percent normal quantile (table value 1.959964)")
    # HAND 30 of 1,000. p = 0.03, z^2 = 3.841459, z^2/n = 0.003841459, denominator = 1.003841459
    #   centre = (0.03 + 0.0019207295) / 1.003841459 = 0.031798577
    #   half   = 1.959964 * sqrt(0.03*0.97/1000 + 3.841459/4000000) / 1.003841459
    #          = 1.959964 * sqrt(0.0000291 + 0.00000096036) / 1.003841459
    #          = 1.959964 * 0.005482733 / 1.003841459 = 0.010704837
    #   limits = 0.021093740 and 0.042503414
    lo, hi = m.wilson(30, 1000, z)
    close(lo, 0.021093740, 2e-8, "Wilson lower limit for 30/1000")
    close(hi, 0.042503414, 2e-8, "Wilson upper limit for 30/1000")
    # HAND 20 of 1,000. centre = (0.02 + 0.0019207295) / 1.003841459 = 0.021836845
    #   half = 1.959964 * sqrt(0.0000196 + 0.00000096036) / 1.003841459 = 1.959964 * 0.004534353 / 1.003841459 = 0.008853160
    lo, hi = m.wilson(20, 1000, z)
    close(lo, 0.012983685, 2e-8, "Wilson lower limit for 20/1000")
    close(hi, 0.030690005, 2e-8, "Wilson upper limit for 20/1000")
    # HAND 37 of 120. p = 0.308333, z^2/n = 0.0320122, denominator = 1.0320122
    #   centre = (0.308333 + 0.0160061) / 1.0320122 = 0.314278
    #   half   = 1.959964 * sqrt(0.308333*0.691667/120 + 3.841459/57600) / 1.0320122
    #          = 1.959964 * sqrt(0.00177720 + 0.0000666920) / 1.0320122 = 1.959964 * 0.0429406 / 1.0320122 = 0.0815514
    lo, hi = m.wilson(37, 120, z)
    close(lo, 0.232727, 2e-6, "Wilson lower limit for 37/120")
    close(hi, 0.395829, 2e-6, "Wilson upper limit for 37/120")
    # HAND 41 of 50. p = 0.82, z^2/n = 0.07682918, denominator = 1.07682918
    #   centre = (0.82 + 0.03841459) / 1.07682918 = 0.797169
    #   half   = 1.959964 * sqrt(0.82*0.18/50 + 3.841459/10000) / 1.07682918
    #          = 1.959964 * sqrt(0.002952 + 0.0003841459) / 1.07682918 = 1.959964 * 0.0577594 / 1.07682918 = 0.105129
    lo, hi = m.wilson(41, 50, z)
    close(lo, 0.692040, 2e-6, "Wilson lower limit for 41/50")
    close(hi, 0.902298, 2e-6, "Wilson upper limit for 41/50")
    assert m.wilson(0, 20, z)[0] == 0.0 and m.wilson(20, 20, z)[1] == 1.0, "the limits must stay inside 0 to 1"


@test
def t_wilson_matches_newcombe_table_one(ctx):
    m = ctx.m()
    z = m.z_for(95)
    # WILSON (see the docstring for how far these were checked)
    for k, n, lo, hi in ((81, 263, 0.2553, 0.3662), (15, 148, 0.0624, 0.1605), (0, 20, 0.0, 0.1611), (1, 29, 0.0061, 0.1718)):
        got = m.wilson(k, n, z)
        close(got[0], lo, 5.1e-5, "Wilson lower limit for %d/%d" % (k, n))
        close(got[1], hi, 5.1e-5, "Wilson upper limit for %d/%d" % (k, n))


@test
def t_proportion_command_reports_counts_and_wilson_interval(ctx):
    out = ctx.accepted("proportion", "--events", "37", "--total", "120")
    assert "37 of 120 = 30.8% (Wilson interval 23.3% to 39.6%)" in out, out
    out = ctx.accepted("proportion", "--events", "41", "--total", "50")
    assert "41 of 50 = 82% (Wilson interval 69% to 90%)" in out, "under 100 in the denominator there are no decimal places: " + out
    assert "one person or item is worth 2 percentage points" in out, out
    code, j = ctx.js("proportion", "--events", "41", "--total", "50")
    assert j["results"] == {"events": 41, "total": 50, "percent": 82, "interval_percent": [69, 90]}, j["results"]
    assert "Wilson" in j["methods"][0]


@test
def t_newcombe_difference_matches_published_examples(ctx):
    m = ctx.m()
    z = m.z_for(95)
    # NEWCOMBE
    for (k1, n1, k2, n2), lo, hi in (((56, 70, 48, 80), 0.0524, 0.3339), ((9, 10, 3, 10), 0.1705, 0.8090),
                                     ((10, 10, 0, 20), 0.6791, 1.0000), ((84, 101, 89, 105), -0.1177, 0.0851)):
        d, glo, ghi = m.newcombe_difference(k1, n1, k2, n2, z)
        close(d, k1 / n1 - k2 / n2, 1e-12, "difference")
        close(glo, lo, 5.1e-5, "Newcombe lower limit for %d/%d against %d/%d" % (k1, n1, k2, n2))
        close(ghi, hi, 5.1e-5, "Newcombe upper limit for %d/%d against %d/%d" % (k1, n1, k2, n2))
    # HAND 30/1000 against 20/1000, from the Wilson limits worked in the first test:
    #   lower = 0.01 - sqrt((0.03 - 0.021093740)^2 + (0.030690005 - 0.02)^2) = 0.01 - sqrt(0.00007932147 + 0.00011427621) = 0.01 - 0.013913939
    #   upper = 0.01 + sqrt((0.042503414 - 0.03)^2 + (0.02 - 0.012983685)^2) = 0.01 + sqrt(0.00015633536 + 0.00004922868) = 0.01 + 0.014337505
    d, lo, hi = m.newcombe_difference(30, 1000, 20, 1000, z)
    close(d, 0.01, 1e-12, "difference for 30/1000 against 20/1000")
    close(lo, -0.003913939, 3e-8, "Newcombe lower limit for 30/1000 against 20/1000")
    close(hi, 0.024337505, 3e-8, "Newcombe upper limit for 30/1000 against 20/1000")
    # A Wald interval for the same counts would be 0.01 +/- 1.959964 * sqrt(0.0000291 + 0.0000196) = -0.00368 to 0.02368.
    assert abs(lo - (-0.003678)) > 1e-4, "the interval is the Wald interval, not Newcombe's"


@test
def t_risk_ratio_matches_published_example(ctx):
    m = ctx.m()
    z = m.z_for(95)
    # KATZ
    rr, lo, hi = m.risk_ratio(10, 75, 12, 225, z)
    close(rr, 2.5, 1e-12, "risk ratio for 10/75 against 12/225")
    close(lo, 1.1261564, 2e-7, "risk ratio lower limit")
    close(hi, 5.5498508, 2e-7, "risk ratio upper limit")
    # HAND 30/1000 against 20/1000: RR = 1.5, ln 1.5 = 0.405465
    #   se = sqrt(1/30 - 1/1000 + 1/20 - 1/1000) = sqrt(0.0813333) = 0.285190; 1.959964 * 0.285190 = 0.558962
    #   limits = exp(-0.153497) = 0.857704 and exp(0.964427) = 2.623285
    rr, lo, hi = m.risk_ratio(30, 1000, 20, 1000, z)
    close(rr, 1.5, 1e-12, "risk ratio for 30/1000 against 20/1000")
    close(lo, 0.857704, 3e-6, "risk ratio lower limit for 30/1000 against 20/1000")
    close(hi, 2.623285, 3e-6, "risk ratio upper limit for 30/1000 against 20/1000")


@test
def t_odds_ratio_matches_published_example(ctx):
    m = ctx.m()
    z = m.z_for(95)
    # BLAND: eczema and hay fever. se of the log odds ratio 0.103, interval for the log odds ratio 1.386 to 1.790
    value, lo, hi = m.odds_ratio(141, 561, 928, 14453, z)
    close(value, 4.89, 0.005, "odds ratio for the eczema and hay fever table")
    close(lo, 4.00, 0.005, "odds ratio lower limit")
    close(hi, 5.99, 0.005, "odds ratio upper limit")
    close(math.log(lo), 1.386, 0.0006, "lower limit on the log scale")
    close(math.log(hi), 1.790, 0.0006, "upper limit on the log scale")
    # HAND 30/1000 against 20/1000: OR = (30*980)/(20*970) = 1.515464, ln = 0.415722
    #   se = sqrt(1/30 + 1/970 + 1/20 + 1/980) = sqrt(0.0853847) = 0.292207; 1.959964 * 0.292207 = 0.572715
    #   limits = exp(-0.156993) = 0.854710 and exp(0.988437) = 2.687031
    value, lo, hi = m.odds_ratio(30, 1000, 20, 1000, z)
    close(value, 1.515464, 1e-6, "odds ratio for 30/1000 against 20/1000")
    close(lo, 0.854710, 3e-6, "odds ratio lower limit for 30/1000 against 20/1000")
    close(hi, 2.687031, 4e-6, "odds ratio upper limit for 30/1000 against 20/1000")
    assert abs(value - 1.5) > 0.01, "the odds ratio must not be the risk ratio"


# ---------------------------------------------------------------- the two-by-two command

@test
def t_two_by_two_reports_absolute_difference_with_relative(ctx):
    out = ctx.accepted("two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000")
    lines = out.splitlines()
    absolute = [i for i, x in enumerate(lines) if x.strip().startswith("ABSOLUTE")]
    relative = [i for i, x in enumerate(lines) if x.strip().startswith("RELATIVE")]
    assert absolute, "two-by-two printed no ABSOLUTE line. A relative figure must never appear without the absolute one:\n" + out
    assert relative and absolute[0] < relative[0], "the absolute difference must come before the relative one"
    assert "A minus B = 1.0 percentage points (Newcombe interval -0.4 to 2.4). The interval includes zero." in lines[absolute[0]], lines[absolute[0]]
    assert "risk ratio A/B = 1.50 (log-method interval 0.86 to 2.62): 50% higher in A" in out, out
    assert "\"50% higher\" here means 3.0% against 2.0%: a difference of 1.0 percentage points." in out, "the two must be stated together"
    assert "30 of 1,000 had the event = 3.0% (Wilson interval 2.1% to 4.3%)" in out and "20 of 1,000 had the event = 2.0% (Wilson interval 1.3% to 3.1%)" in out
    assert "odds ratio = 1.52 (log-method interval 0.85 to 2.69)" in out
    code, j = ctx.js("two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000")
    r = j["results"]
    assert "absolute_difference" in r, "the JSON has no absolute_difference"
    assert r["absolute_difference"] == {"a_minus_b_percentage_points": 1.0, "interval_percentage_points": [-0.4, 2.4], "interval_includes_zero": True}, r["absolute_difference"]
    assert r["risk_ratio"] == {"value": 1.5, "interval": [0.86, 2.62], "relative_change_percent": 50}, r["risk_ratio"]
    assert r["group_a"]["events"] == 30 and r["group_a"]["total"] == 1000 and r["group_b"]["risk_percent"] == 2.0
    for needle in ("Wilson", "Newcombe", "Katz", "Woolf", "Altman"):
        assert any(needle in x for x in j["methods"]), "the method %s is not named" % needle


@test
def t_number_needed_comes_from_the_absolute_difference(ctx):
    # ALTMAN, HAND. 30/1000 against 20/1000: difference 0.01, so 1 / 0.01 = 100.
    #   The relative figures give something else entirely: 1 / (1.5 - 1) = 2, and 1 / (1 - 0.667) = 3.
    code, j = ctx.js("two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000")
    assert j["results"]["number_needed"]["value"] == 100, "number needed for a 1 point difference is 100, got %r" % j["results"]["number_needed"]["value"]
    # HAND 24/816 against 53/1080: 0.0294118 - 0.0490741 = -0.0196623; 1 / 0.0196623 = 50.86, rounded up to 51.
    #   From the risk ratio 0.599 it would be 1 / 0.401 = 2.5.
    code, j = ctx.js("two-by-two", "--a-events", "24", "--a-total", "816", "--b-events", "53", "--b-total", "1080")
    nn = j["results"]["number_needed"]
    assert nn["value"] == 51 and nn["unrounded"] == 50.9, nn
    # HAND 2 in 1,000 against 3 in 1,000 at 100,000 each: difference 0.001, number needed 1,000 (not 2).
    code, j = ctx.js("two-by-two", "--a-events", "300", "--a-total", "100000", "--b-events", "200", "--b-total", "100000")
    assert j["results"]["number_needed"]["value"] == 1000 and j["results"]["risk_ratio"]["value"] == 1.5, j["results"]["number_needed"]
    m = ctx.m()
    point, interval = m.number_needed(0.2, 0.0524, 0.3339)
    close(point, 5.0, 1e-12, "number needed for a difference of 0.2")
    close(interval[0], 1 / 0.3339, 1e-9, "lower limit of the number needed")
    close(interval[1], 1 / 0.0524, 1e-9, "upper limit of the number needed")


@test
def t_number_needed_interval_follows_the_difference_interval(ctx):
    # ALTMAN. 30/1000 against 20/1000: the Newcombe interval -0.4 to 2.4 points includes zero, so no finite interval.
    code, j = ctx.js("two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000")
    nn = j["results"]["number_needed"]
    assert nn["interval"] is None and "not estimable" in nn["reason"] and "includes zero" in nn["reason"], nn
    out = ctx.accepted("two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000")
    assert "Interval: not estimable" in out, out
    # NEWCOMBE, HAND. 56/70 against 48/80: difference 0.2, interval 0.0524 to 0.3339, which excludes zero.
    #   1/0.2 = 5; 1/0.3339 = 2.995, rounded up to 3; 1/0.0524 = 19.08, rounded up to 20.
    code, j = ctx.js("two-by-two", "--a-events", "56", "--a-total", "70", "--b-events", "48", "--b-total", "80")
    nn = j["results"]["number_needed"]
    assert nn["value"] == 5 and nn["interval"] == [3, 20] and nn["interval_unrounded"] == [3.0, 19.1], nn
    assert j["results"]["absolute_difference"]["interval_includes_zero"] is False
    # Naming: treated group a with fewer bad events is a benefit; more bad events is a harm; and the mirror cases.
    cases = ((("24", "816", "53", "1080"), "a", "bad", "treat"), (("53", "1080", "24", "816"), "a", "bad", "harm"),
             (("56", "70", "48", "80"), "a", "good", "treat"), (("56", "70", "48", "80"), "b", "good", "harm"),
             (("24", "816", "53", "1080"), "b", "bad", "harm"))
    for (ae, at, be, bt), treated, event, word in cases:
        code, j = ctx.js("two-by-two", "--a-events", ae, "--a-total", at, "--b-events", be, "--b-total", bt, "--treated", treated, "--event", event)
        assert ("needed to %s" % word) in j["results"]["number_needed"]["name"], "%s %s %s: %s" % (ae, treated, event, j["results"]["number_needed"]["name"])
    code, j = ctx.js("two-by-two", "--a-events", "24", "--a-total", "816", "--b-events", "53", "--b-total", "1080")
    assert j["results"]["number_needed"]["name"] == "number needed for one event of difference", "without --treated and --event no direction is claimed"


@test
def t_zero_cells_give_null_with_a_reason(ctx):
    code, j = ctx.js("two-by-two", "--a-events", "0", "--a-total", "50", "--b-events", "5", "--b-total", "50")
    r = j["results"]
    assert code == 0 and r["risk_ratio"]["value"] is None and "no events" in r["risk_ratio"]["reason"], r["risk_ratio"]
    assert r["odds_ratio"]["value"] is None and "zero" in r["odds_ratio"]["reason"], r["odds_ratio"]
    assert r["absolute_difference"]["a_minus_b_percentage_points"] == -10 and r["number_needed"]["value"] == 10
    code, j = ctx.js("two-by-two", "--a-events", "50", "--a-total", "50", "--b-events", "45", "--b-total", "50")
    assert j["results"]["odds_ratio"]["value"] is None and j["results"]["risk_ratio"]["value"] == 1.11, "everyone having the event leaves the risk ratio defined"
    code, j = ctx.js("two-by-two", "--a-events", "0", "--a-total", "50", "--b-events", "0", "--b-total", "50")
    r = j["results"]
    assert r["number_needed"]["value"] is None and "identical" in r["number_needed"]["reason"] and r["absolute_difference"]["a_minus_b_percentage_points"] == 0
    out = ctx.accepted("two-by-two", "--a-events", "0", "--a-total", "50", "--b-events", "5", "--b-total", "50")
    assert "not estimable" in out and "nan" not in out.lower() and "inf" not in out.lower().replace("interval", ""), out


# ---------------------------------------------------------------- means

@test
def t_student_t_quantile_matches_nist_table(ctx):
    m = ctx.m()
    # NIST section 1.3.6.7.2, column 0.975
    for df, want in ((1, 12.706), (2, 4.303), (5, 2.571), (7, 2.365), (8, 2.306), (10, 2.228), (20, 2.086), (30, 2.042), (60, 2.000), (100, 1.984)):
        close(m.t_quantile(0.975, df), want, 0.00051, "t quantile 0.975 with %d degrees of freedom" % df)
    close(m.t_quantile(0.95, 10), 1.812, 0.00051, "t quantile 0.95 with 10 degrees of freedom")
    close(m.t_quantile(0.995, 10), 3.169, 0.00051, "t quantile 0.995 with 10 degrees of freedom")
    close(m.t_quantile(0.975, 1e7), 1.960, 0.00051, "t quantile with very many degrees of freedom")

    def density(t, df):
        return math.exp(math.lgamma((df + 1) / 2.0) - math.lgamma(df / 2.0)) / math.sqrt(df * math.pi) * (1 + t * t / df) ** (-(df + 1) / 2.0)

    def integrate(upper, df, steps=20000):
        h = upper / steps
        total = density(0, df) + density(upper, df)
        for i in range(1, steps):
            total += (4 if i % 2 else 2) * density(i * h, df)
        return 0.5 + total * h / 3.0

    # An independent check for fractional degrees of freedom: integrate the density by Simpson's rule.
    for df in (2.5, 7.3, 22.9927, 136.875):
        t = m.t_quantile(0.975, df)
        close(integrate(t, df), 0.975, 2e-7, "area under the t density up to the 0.975 quantile, %s degrees of freedom" % df)
        close(m.t_cdf(1.3, df), integrate(1.3, df), 2e-7, "t distribution function at 1.3, %s degrees of freedom" % df)


@test
def t_welch_interval_matches_hand_worked_values(ctx):
    m = ctx.m()
    # HAND group 1: mean 10, SD 2, n 10. Group 2: mean 8, SD 3, n 15.
    #   s1^2/n1 = 4/10 = 0.4; s2^2/n2 = 9/15 = 0.6; se = sqrt(1.0) = 1.0
    #   df = 1.0^2 / (0.4^2/9 + 0.6^2/14) = 1 / (0.0177778 + 0.0257143) = 22.9927
    #   t(0.975, 23) = 2.069 in the NIST table; at 22.99 it is a shade larger. Interval = 2 +/- 2.069 * 1.0 = -0.069 to 4.069
    w = m.welch(10, 2, 10, 8, 3, 15, 95)
    close(w["difference"], 2.0, 1e-12, "difference in means")
    close(w["se"], 1.0, 1e-12, "standard error")
    close(w["df"], 22.9927, 5e-5, "Welch-Satterthwaite degrees of freedom")
    close(w["t_critical"], 2.069, 0.0006, "critical value")
    close(w["low"], -0.069, 0.0006, "lower limit")
    close(w["high"], 4.069, 0.0006, "upper limit")
    assert abs(w["df"] - 23.0) > 0.005, "the degrees of freedom are the pooled n1 + n2 - 2, not Welch's"
    # NIST 1.3.5.3 summary statistics: 249 observations, mean 20.14458, SD 6.41470; 79 observations, mean 30.48101, SD 6.10771.
    # HAND s1^2/n1 = 41.14837/249 = 0.165255; s2^2/n2 = 37.30412/79 = 0.472204; se = sqrt(0.637459) = 0.798410
    #   df = 0.637459^2 / (0.165255^2/248 + 0.472204^2/78) = 0.406354 / (0.00011012 + 0.00285870) = 136.87
    w = m.welch(20.14458, 6.41470, 249, 30.48101, 6.10771, 79, 95)
    close(w["difference"], -10.33643, 1e-9, "difference in means, NIST data")
    close(w["se"], 0.798410, 2e-6, "standard error, NIST data")
    close(w["df"], 136.87, 0.01, "Welch-Satterthwaite degrees of freedom, NIST data")
    # NIST: pooled standard deviation 6.34260 and the equal-variance statistic -12.62059
    sp = m.pooled_sd(6.41470, 249, 6.10771, 79)
    close(sp, 6.34260, 6e-6, "pooled standard deviation, NIST data")
    close(-10.33643 / (sp * math.sqrt(1 / 249.0 + 1 / 79.0)), -12.62059, 6e-6, "equal-variance statistic rebuilt from the pooled SD")
    out = ctx.accepted("means", "--mean1", "10", "--sd1", "2", "--n1", "10", "--mean2", "8", "--sd2", "3", "--n2", "15")
    assert "group 1 minus group 2 = 2 (Welch interval 0 to 4, 23.0 degrees of freedom). The interval includes zero." in out, \
        "whole-number inputs give whole-number output, and the output must still say the interval includes zero: " + out
    out = ctx.accepted("means", "--mean1", "10.0", "--sd1", "2.0", "--n1", "10", "--mean2", "8.0", "--sd2", "3.0", "--n2", "15")
    assert "group 1 minus group 2 = 2.0 (Welch interval -0.1 to 4.1, 23.0 degrees of freedom). The interval includes zero." in out, out
    out = ctx.accepted("means", "--mean1", "20.14458", "--sd1", "6.41470", "--n1", "249", "--mean2", "30.48101", "--sd2", "6.10771", "--n2", "79")
    assert "The interval excludes zero." in out and "136.9 degrees of freedom" in out, out
    code, j = ctx.js("means", "--mean1", "10.00", "--sd1", "2.0", "--n1", "10", "--mean2", "8.0", "--sd2", "3.0", "--n2", "15")
    assert j["results"]["difference"] == 2.0 and j["results"]["interval"] == [-0.07, 4.07] and j["results"]["interval_includes_zero"] is True, j["results"]
    code, j99 = ctx.js("means", "--mean1", "10.00", "--sd1", "2.0", "--n1", "10", "--mean2", "8.0", "--sd2", "3.0", "--n2", "15", "--level", "99")
    assert j99["results"]["interval"][0] < j["results"]["interval"][0] and j99["results"]["interval"][1] > j["results"]["interval"][1], "a 99 percent interval is wider"


@test
def t_cohens_d_uses_the_pooled_standard_deviation(ctx):
    m = ctx.m()
    # HAND means 10 and 8, SDs 2 and 3, n 10 and 15: pooled SD = sqrt((9*4 + 14*9)/23) = sqrt(7.04348) = 2.65396; d = 2/2.65396 = 0.75359
    close(m.cohen_d(10, 2, 10, 8, 3, 15), 0.75359, 1e-5, "Cohen's d")
    assert abs(m.cohen_d(10, 2, 10, 8, 3, 15) - 2.0) > 0.5, "d was computed with the standard error (1.0), not the pooled SD"
    out = ctx.accepted("means", "--mean1", "10", "--sd1", "2", "--n1", "10", "--mean2", "8", "--sd2", "3", "--n2", "15")
    assert "d = 0.75" in out and "convention" in out, out
    for word in ("small", "medium", "large effect", "moderate"):
        assert word not in out.lower(), "the output attaches the label %r to d" % word
    assert "standard error" in out, "the output must warn about a standard error entered as an SD"


# ---------------------------------------------------------------- percentages, attrition, relative claims

@test
def t_check_percent_boundary_rounding(ctx):
    def run(count, total, reported):
        code, j = ctx.js("check-percent", "--count", str(count), "--total", str(total), "--reported", reported)
        assert (code == 0) == j["results"]["consistent"], "the exit code must be 1 exactly when the figures disagree"
        return j["results"]

    # 37/120 = 30.8333...: 31 and 30.8 and 30.83 are what rounding gives; 30, 30.9, 31.0 and 30.84 are not.
    for reported, ok in (("31", True), ("30", False), ("30.8", True), ("30.9", False), ("30.83", True), ("30.84", False),
                         ("31.0", False), ("30.7", False), ("32", False)):
        assert run(37, 120, reported)["consistent"] is ok, "37 of 120 reported as %s%%: expected %s" % (reported, "consistent" if ok else "a mismatch")
    # 1/8 = 12.5 exactly: a tie rounds either way, so 12 and 13 both pass; 11 and 14 do not.
    for reported, ok in (("12", True), ("13", True), ("12.5", True), ("11", False), ("14", False), ("12.4", False), ("12.6", False)):
        assert run(1, 8, reported)["consistent"] is ok, "1 of 8 reported as %s%%" % reported
    # 617/2000 = 30.85 exactly: a tie at one decimal place.
    for reported, ok in (("30.8", True), ("30.9", True), ("30.7", False), ("31.0", False)):
        assert run(617, 2000, reported)["consistent"] is ok, "617 of 2000 reported as %s%%" % reported
    # 1/3 = 33.33...
    for reported, ok in (("33", True), ("33.3", True), ("33.4", False), ("34", False)):
        assert run(1, 3, reported)["consistent"] is ok, "1 of 3 reported as %s%%" % reported
    assert run(0, 50, "0")["consistent"] and run(50, 50, "100")["consistent"] and not run(49, 50, "100")["consistent"]
    r = run(37, 120, "30")
    assert r["counts_that_would_fit"] == [36] and r["truncation_matches"] is True and r["computed_percent"] == "30.83", r
    assert run(37, 120, "31")["counts_that_would_fit"] == [37]
    assert run(3, 10, "7")["counts_that_would_fit"] == [], "7 percent of 10 is no whole count"
    big = run(500000000000000, 999999999999999, "50")
    assert big["consistent"] and len(big["counts_that_would_fit"]) == 12, "a very large total must not exhaust memory listing counts"
    code, out, err = ctx.effect("check-percent", "--count", "37", "--total", "120", "--reported", "30")
    assert code == 1 and "MISMATCH" in out and "would need a count of 36" in out and "cut short instead of rounded" in out, out
    code, out, err = ctx.effect("check-percent", "--count", "3", "--total", "10", "--reported", "7")
    assert code == 1 and "No whole count out of 10 gives 7%" in out, out
    for bad in ("31%", "abc", "101", "-3", "3e1", ""):
        ctx.refused("check-percent", "--count", "37", "--total", "120", "--reported", bad) if bad else None
    ctx.accepted("check-percent", "--count", "120", "--total", "120", "--reported", "100")


@test
def t_attrition_overall_by_group_and_balance(ctx):
    # HAND loss 80/250 = 32.0% against 40/250 = 16.0%: a gap of 16.0 points.
    #   Wilson 80/250: centre = (0.32 + 0.007682918)/1.015365836 = 0.322724, half = 1.959964*sqrt(0.0008704 + 0.0000153658)/1.015365836 = 0.0574494 -> 0.265275 to 0.380173
    #   Wilson 40/250: centre = 0.165145, half = 1.959964*sqrt(0.0005376 + 0.0000153658)/1.015365836 = 0.0453916 -> 0.119754 to 0.210537
    #   lower = 0.16 - sqrt(0.054725^2 + 0.050537^2) = 0.16 - 0.074490 = 0.0855; upper = 0.16 + sqrt(0.060173^2 + 0.040246^2) = 0.16 + 0.072392 = 0.2324
    code, j = ctx.js("attrition", "--start", "500", "--analysed", "380", "--by-group", "Intervention:250:170", "--by-group", "Control:250:210")
    r = j["results"]
    assert code == 0 and r["overall"] == {"start": 500, "analysed": 380, "lost": 120, "lost_percent": 24.0}, r["overall"]
    assert [g["lost"] for g in r["groups"]] == [80, 40] and [g["lost_percent"] for g in r["groups"]] == [32.0, 16.0], r["groups"]
    b = r["balance"]
    assert b["unbalanced"] is True and b["difference_percentage_points"] == 16.0 and b["interval_percentage_points"] == [8.6, 23.2], b
    assert b["most_lost"] == "Intervention" and b["least_lost"] == "Control"
    out = ctx.accepted("attrition", "--start", "500", "--analysed", "380", "--by-group", "Intervention:250:170", "--by-group", "Control:250:210")
    assert "120 lost = 24.0% of 500" in out and "UNBALANCED" in out and "80 lost = 32.0% of 250" in out, out
    code, j = ctx.js("attrition", "--start", "500", "--analysed", "458", "--by-group", "Intervention:250:228", "--by-group", "Control:250:230")
    assert j["results"]["balance"]["unbalanced"] is False, "22 lost against 20 lost of 250 each is not a clear imbalance"
    out = ctx.accepted("attrition", "--start", "500", "--analysed", "458", "--by-group", "Intervention:250:228", "--by-group", "Control:250:230")
    assert "no clear imbalance" in out and "not proof" in out, out
    code, j = ctx.js("attrition", "--start", "500", "--analysed", "380")
    assert code == 0 and j["results"]["balance"]["unbalanced"] is None and "each group" in j["results"]["balance"]["reason"]
    code, out, err = ctx.effect("attrition", "--start", "500", "--analysed", "380", "--by-group", "Intervention:250:170", "--by-group", "Control:240:210")
    assert code == 1 and "MISMATCH" in out and "490" in out, "groups that do not add up to the overall figure are a mismatch: " + out
    ctx.accepted("attrition", "--start", "500", "--analysed", "500")
    ctx.refused("attrition", "--start", "500", "--analysed", "501")
    ctx.refused("attrition", "--start", "0", "--analysed", "0")
    ctx.refused("attrition", "--start", "500", "--analysed", "380", "--by-group", "Intervention:250")
    ctx.refused("attrition", "--start", "500", "--analysed", "380", "--by-group", "Intervention:250:251")
    ctx.refused("attrition", "--start", "500", "--analysed", "380", "--by-group", "A:250:170", "--by-group", "A:250:210")
    out = ctx.accepted("attrition", "--start", "500", "--analysed", "380", "--by-group", "Arm 1: high dose:250:170", "--by-group", "Arm 2:250:210")
    assert "Arm 1: high dose: 250 started" in out, "a group name may contain a colon"


@test
def t_relative_to_absolute_states_both(ctx):
    # HAND baseline 0.002 = 2 in 1,000; times 1.5 = 0.003 = 3 in 1,000; 1 more per 1,000; 1/0.001 = 1,000 people.
    out = ctx.accepted("relative-to-absolute", "--baseline", "0.002", "--relative", "1.5")
    for needle in ("Baseline: 2 in 1,000", "times 1.5 (50% higher)", "After: 3 in 1,000", "1 more per 1,000 (0.1 percentage points)", "for every 1,000 people"):
        assert needle in out, "wanted %r in:\n%s" % (needle, out)
    code, j = ctx.js("relative-to-absolute", "--baseline", "0.002", "--percent-change", "50")
    r = j["results"]
    assert r["new_risk"] == 0.003 and r["absolute_change"] == 0.001 and r["per"] == 1000 and r["baseline_per"] == 2 and r["new_per"] == 3, r
    assert r["change_per"] == 1 and r["people_per_one_event_of_difference"] == 1000 and r["absolute_change_percentage_points"] == 0.1, r
    # HAND baseline 0.049 (49 in 1,000), 40 percent lower: 0.049 * 0.6 = 0.0294; 19.6 fewer per 1,000; 1/0.0196 = 51.02, rounded up to 52.
    code, j = ctx.js("relative-to-absolute", "--baseline", "0.049", "--percent-change", "-40")
    r = j["results"]
    assert r["new_risk"] == 0.0294 and r["change_per"] == -19.6 and r["per"] == 1000 and r["people_per_one_event_of_difference"] == 52, r
    out = ctx.accepted("relative-to-absolute", "--baseline", "0.049", "--percent-change", "-40")
    assert "Baseline: 49 in 1,000" in out and "After: 29.4 in 1,000" in out and "19.6 fewer per 1,000" in out and "40% lower" in out, out
    # HAND baseline 0.3: 30 in 100; doubled is 60 in 100; 30 more per 100; 1/0.3 = 3.33, rounded up to 4.
    code, j = ctx.js("relative-to-absolute", "--baseline", "0.3", "--relative", "2")
    assert j["results"]["per"] == 100 and j["results"]["new_per"] == 60 and j["results"]["people_per_one_event_of_difference"] == 4
    code, j = ctx.js("relative-to-absolute", "--baseline", "0.3", "--relative", "1")
    assert j["results"]["absolute_change"] == 0 and j["results"]["people_per_one_event_of_difference"] is None
    # HAND 0.0125 is 1.25 in 100 and 12.5 in 1,000; the first whole count is 125 in 10,000.
    out = ctx.accepted("relative-to-absolute", "--baseline", "0.0125", "--relative", "2")
    assert "Baseline: 125 in 10,000" in out and "After: 250 in 10,000" in out, out
    # HAND 1/3 is never a whole count, so the smallest denominator with at least 1 is used: 33.3 in 100.
    out = ctx.accepted("relative-to-absolute", "--baseline", "0.333333", "--relative", "0.5")
    assert "Baseline: 33.3 in 100" in out, out
    ctx.accepted("relative-to-absolute", "--baseline", "0.5", "--relative", "2")
    assert "above 1" in ctx.refused("relative-to-absolute", "--baseline", "0.5", "--relative", "2.01")
    ctx.accepted("relative-to-absolute", "--baseline", "1", "--relative", "0.5")
    ctx.refused("relative-to-absolute", "--baseline", "1.01", "--relative", "0.5")
    ctx.refused("relative-to-absolute", "--baseline", "0", "--relative", "2")
    ctx.refused("relative-to-absolute", "--baseline", "1e-320", "--relative", "2")
    ctx.refused("relative-to-absolute", "--baseline", "0.0000000009", "--relative", "2")
    ctx.accepted("relative-to-absolute", "--baseline", "0.000000001", "--relative", "2")
    ctx.refused("relative-to-absolute", "--baseline", "0.01", "--relative", "-1")
    ctx.accepted("relative-to-absolute", "--baseline", "0.01", "--percent-change", "-100")
    ctx.refused("relative-to-absolute", "--baseline", "0.01", "--percent-change", "-101")
    ctx.refused("relative-to-absolute", "--baseline", "0.01")
    ctx.refused("relative-to-absolute", "--baseline", "0.01", "--relative", "2", "--percent-change", "100")
    ctx.refused("relative-to-absolute", "--baseline", "2%", "--relative", "2")


# ---------------------------------------------------------------- refusals, precision, output

@test
def t_impossible_inputs_refused_with_valid_neighbours(ctx):
    base = ["two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000"]

    def swap(flag, value):
        args = list(base)
        args[args.index(flag) + 1] = value
        return args

    ctx.accepted(*swap("--a-events", "1000"))
    assert "impossible" in ctx.refused(*swap("--a-events", "1001"))
    ctx.accepted(*swap("--b-events", "0"))
    ctx.refused(*swap("--b-events", "-1"))
    ctx.refused(*swap("--b-total", "0"))
    ctx.accepted("two-by-two", "--a-events", "1", "--a-total", "1", "--b-events", "0", "--b-total", "1")
    for bad in ("30.0", "3e1", "thirty", "NaN", "inf", "+30", "0x1e", "1,000", " 30"):
        ctx.refused(*swap("--a-events", bad))
    ctx.accepted("proportion", "--events", "120", "--total", "120")
    ctx.refused("proportion", "--events", "121", "--total", "120")
    ctx.refused("proportion", "--events", "0", "--total", "0")
    ctx.accepted("proportion", "--events", "0", "--total", "1")
    means = ["means", "--mean1", "10", "--sd1", "2", "--n1", "10", "--mean2", "8", "--sd2", "3", "--n2", "15"]

    def mswap(flag, value):
        args = list(means)
        args[args.index(flag) + 1] = value
        return args

    for bad in ("nan", "NaN", "inf", "-inf", "Infinity", "ten", "1e999", "--5", "1_0", "10 ", " 10", chr(0x661) + chr(0x660), "0x10", "1,5"):
        ctx.refused(*mswap("--mean1", bad))
    ctx.accepted(*mswap("--mean1", "-3.2"))
    ctx.accepted(*mswap("--mean1", "1e-3"))
    ctx.refused(*mswap("--sd1", "-0.1"))
    ctx.accepted(*mswap("--sd1", "0"))
    ctx.refused("means", "--mean1", "10", "--sd1", "0", "--n1", "10", "--mean2", "8", "--sd2", "0", "--n2", "15")
    ctx.refused("means", "--mean1", "10", "--sd1", "1e-320", "--n1", "10", "--mean2", "8", "--sd2", "1e-320", "--n2", "15")
    ctx.refused(*mswap("--mean1", "1e13"))
    ctx.accepted(*mswap("--mean1", "1e12"))
    ctx.refused(*mswap("--n1", "1"))
    ctx.accepted(*mswap("--n1", "2"))
    ctx.refused(*mswap("--n1", "10.5"))
    for level, ok in (("90", True), ("95", True), ("99", True), ("80", False), ("0.95", False), ("100", False)):
        (ctx.accepted if ok else ctx.refused)(*(base + ["--level", level]))


@test
def t_arguments_are_strict(ctx):
    base = ["two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000"]
    assert "unknown argument --bogus" in ctx.refused(*(base + ["--bogus"]))
    assert "--a-events needs a value" in ctx.refused("two-by-two", "--a-events")
    assert "--a-total needs a value" in ctx.refused("two-by-two", "--a-events", "30", "--a-total", "--b-events", "20", "--b-total", "1000")
    assert "needs --b-events, --b-total" in ctx.refused("two-by-two", "--a-events", "30", "--a-total", "1000")
    assert "given twice" in ctx.refused(*(base + ["--a-events", "31"]))
    assert "unknown argument 30" in ctx.refused("two-by-two", "30", "1000", "20", "1000")
    assert "unknown argument --events" in ctx.refused(*(base + ["--events", "3"]))
    assert "together" in ctx.refused(*(base + ["--treated", "a"]))
    ctx.refused(*(base + ["--treated", "c", "--event", "bad"]))
    ctx.refused(*(base + ["--treated", "a", "--event", "neutral"]))
    ctx.refused(*(base + ["--a-label", "x" * 61]))
    ctx.accepted(*(base + ["--a-label", "x" * 60]))
    code, out, err = ctx.effect("frobnicate")
    assert code == 2 and "unknown command" in err
    code, out, err = ctx.effect()
    assert code == 2 and "Usage" in out


@test
def t_precision_follows_the_group_size(ctx):
    def line(*args):
        return ctx.accepted(*args).splitlines()[1]

    assert "9 of 99 = 9% (Wilson interval 5% to 16%)" in line("proportion", "--events", "9", "--total", "99"), "under 100: no decimal places"
    assert "9 of 100 = 9.0% " in line("proportion", "--events", "9", "--total", "100"), "from 100: one decimal place"
    assert "= 9.0% " in line("proportion", "--events", "900", "--total", "9999")
    assert "= 9.00% " in line("proportion", "--events", "900", "--total", "10000"), "from 10,000: two decimal places"
    out = ctx.accepted("two-by-two", "--a-events", "41", "--a-total", "50", "--b-events", "360", "--b-total", "500")
    assert "A minus B = 10 percentage points" in out, "the smaller group sets the precision of the difference: " + out
    out = ctx.accepted("means", "--mean1", "1.9", "--sd1", "3.1", "--n1", "816", "--mean2", "2.1", "--sd2", "3.4", "--n2", "1080")
    assert "= -0.2 (Welch interval -0.5 to 0.1" in out, "one decimal place in, one out: " + out
    out = ctx.accepted("means", "--mean1", "1.90", "--sd1", "3.1", "--n1", "816", "--mean2", "2.1", "--sd2", "3.4", "--n2", "1080")
    assert "= -0.20 (Welch interval -0.49 to 0.09" in out, "two decimal places in, two out: " + out


@test
def t_json_is_standard_and_output_is_ascii(ctx):
    runs = [["two-by-two", "--a-events", "0", "--a-total", "50", "--b-events", "0", "--b-total", "50"],
            ["two-by-two", "--a-events", "50", "--a-total", "50", "--b-events", "50", "--b-total", "50"],
            ["two-by-two", "--a-events", "30", "--a-total", "1000", "--b-events", "20", "--b-total", "1000", "--a-label", "Caf" + chr(0xE9)],
            ["proportion", "--events", "0", "--total", "1"], ["proportion", "--events", "1", "--total", "1"],
            ["means", "--mean1", "0", "--sd1", "0", "--n1", "2", "--mean2", "0", "--sd2", "1", "--n2", "2"],
            ["means", "--mean1", "5", "--sd1", "1e-9", "--n1", "2", "--mean2", "5", "--sd2", "1e-9", "--n2", "2"],
            ["check-percent", "--count", "0", "--total", "7", "--reported", "0"],
            ["attrition", "--start", "10", "--analysed", "10", "--by-group", "A:5:5", "--by-group", "B:5:5"],
            ["relative-to-absolute", "--baseline", "1e-9", "--relative", "3"],
            ["relative-to-absolute", "--baseline", "1e-9", "--relative", "1.0000001"],
            ["relative-to-absolute", "--baseline", "1", "--relative", "0"]]
    for args in runs:
        code, j = ctx.js(*args)
        assert isinstance(j, dict) and "results" in j
        code, out, err = ctx.effect(*(args + ["--json"]))
        for token in ("NaN", "Infinity"):
            assert token not in out, "%s appears in the JSON for %s" % (token, " ".join(args))
        assert all(ord(c) < 128 for c in out), "non-ASCII JSON output"
        code, out, err = ctx.effect(*args)
        assert all(ord(c) < 128 for c in out + err), "non-ASCII text output for %s" % " ".join(args)
        assert "nan" not in out.lower().split() and "Traceback" not in err, out
    m = ctx.m()
    close(m.z_for(90), 1.644854, 5e-7, "90 percent normal quantile (table value 1.644854)")
    close(m.z_for(99), 2.575829, 5e-7, "99 percent normal quantile (table value 2.575829)")
    code, j90 = ctx.js("proportion", "--events", "37", "--total", "120", "--level", "90")
    code, j99 = ctx.js("proportion", "--events", "37", "--total", "120", "--level", "99")
    assert j90["results"]["interval_percent"][0] > 23.3 and j99["results"]["interval_percent"][0] < 23.3, "the level must change the interval"


# ---------------------------------------------------------------- the extraction file

def val(v, loc="Table 2"):
    return {"value": v, "locator": loc}


def good_extraction():
    return {
        "audit_of": {"title": "SYNTHETIC test trial", "source": "Invented for the tests", "date": "2026-05-04", "locator": "report.md", "material": "full_text"},
        "claim": {"quote": "The drink reduced colds by 40 percent.", "locator": "abstract, sentence 4"},
        "supporting_result": {"quote": "24 of 816 (2.9%) against 53 of 1,080 (4.9%)", "locator": "Table 2, row 1"},
        "design": {"type": "randomised_trial", "locator": "Methods, paragraph 1", "ceiling": "Can show cause in the people analysed if allocation and follow-up were sound."},
        "groups": [{"name": "Drink", "n_start": val(1200, "Figure 1"), "n_analysed": val(816, "Figure 1")},
                   {"name": "Usual diet", "n_start": val(1200, "Figure 1"), "n_analysed": val(1080, "Figure 1")}],
        "outcomes": [{"name": "Three or more days of cold symptoms", "definition": "Self-reported in a weekly diary", "time_frame": "12 weeks",
                      "locator": "Table 2, row 1", "status": "reported_primary",
                      "results": [{"group": "Drink", "events": val(24), "total": val(816), "reported_percent": val("2.9")},
                                  {"group": "Usual diet", "events": val(53), "total": val(1080), "reported_percent": val("4.9")}]},
                     {"name": "GP-confirmed infection", "definition": "Recorded by a general practitioner", "time_frame": "12 weeks",
                      "locator": "Table 2, row 2", "status": "registered_primary",
                      "results": [{"group": "Drink", "events": val(31), "total": val(816), "reported_percent": val("3.8")},
                                  {"group": "Usual diet", "events": val(44), "total": val(1080), "reported_percent": val("4.1")}]}],
        "other_percentages": [{"label": "completed follow-up, drink", "count": val(816, "Figure 1"), "total": val(1200, "Figure 1"), "reported_percent": val("68", "abstract")}],
        "reporting": [{"item": "funding", "text": "Funded by the maker of the drink", "locator": "Funding statement"},
                      {"item": "blinding", "not_reported": True}, {"item": "registration", "text": "Registered before recruitment", "locator": "Methods"},
                      {"item": "allocation_method", "not_reported": True}, {"item": "analysis_population", "text": "Completers only", "locator": "Methods"},
                      {"item": "reasons_for_loss", "text": "Given by group", "locator": "Figure 1"}, {"item": "author_affiliations", "not_reported": True},
                      {"item": "data_availability", "not_reported": True}, {"item": "replication", "not_reported": True}]}


@test
def t_extraction_valid_file_passes_and_suggests_commands(ctx):
    code, j, err = ctx.extraction(good_extraction())
    assert code == 0 and j["result"] == "PASS" and j["errors"] == [] and j["findings"] == [], j
    assert j["summary"]["numbers_with_locators"] == 19, "every extracted number is counted: %s" % j["summary"]["numbers_with_locators"]
    for item in ("blinding", "allocation method", "author affiliations", "data availability", "replication"):
        assert item in j["not_reported"], "%s is marked not reported and must be listed: %s" % (item, j["not_reported"])
    assert any("lost 384 of 1200" in a and "lost 120 of 1200" in a for a in j["advisories"]), "unbalanced loss must be pointed out: %s" % j["advisories"]
    assert any("not the one registered as primary" in a for a in j["advisories"]), "a switched primary outcome must be pointed out"
    assert [r["lost"] for r in j["summary"]["attrition"]] == [384, 120]
    assert len(j["commands"]) == 3 and "--a-events 24 --a-total 816 --b-events 53 --b-total 1080" in j["commands"][1], j["commands"]
    for cmd in j["commands"]:
        import shlex
        parts = shlex.split(cmd)
        assert parts[:2] == ["python", "effect.py"]
        code, out, err = ctx.effect(*parts[2:])
        assert code == 0, "a suggested command does not run: %s\n%s" % (cmd, err)
    code, out, err = ctx.run("extraction_check.py", ctx.root / "missing.json")
    assert code == 2 and "cannot read" in err
    f = ctx.root / "bad.json"
    for data in (b"{not json", b"\xff\xfe{}", b'{"a": NaN}', b'{"a": "\x00"}'.replace(b"\\x00", b"\x00")):
        f.write_bytes(data)
        code, out, err = ctx.run("extraction_check.py", f)
        assert code == 2 and "Traceback" not in err and "not valid UTF-8 JSON" in err, (data, code, err)
    code, out, err = ctx.run("extraction_check.py", f, "--verbose")
    assert code == 2 and "unknown option" in err
    f.write_bytes(b"\xef\xbb\xbf" + json.dumps(good_extraction()).encode("utf-8"))
    code, out, err = ctx.run("extraction_check.py", f)
    assert code == 0 and "RESULT: PASS" in out and "NOT REPORTED" in out and "RECOMPUTE with:" in out and all(ord(ch) < 128 for ch in out), out


@test
def t_extraction_template_passes_its_own_check(ctx):
    template = HERE.parent / "assets" / "extraction-template.json"
    assert template.is_file(), "the template is missing from assets"
    code, out, err = ctx.run("extraction_check.py", template, "--json")
    j = json.loads(out)
    assert j["errors"] == [] and j["findings"] == [], "the template the skill hands out must have no errors and no findings: %s %s" % (j["errors"], j["findings"])
    assert code == 3 and j["result"] == "INCOMPLETE" and len(j["cannot_check"]) == 1 and "sd not reported" in j["cannot_check"][0], \
        "the template leaves one standard deviation unreported, so one comparison cannot be made and the result is INCOMPLETE: %s %s" % (code, j["cannot_check"])
    assert "reasons for loss" in j["not_reported"] and any("sd" in x for x in j["not_reported"]), j["not_reported"]
    assert any("--a-events 150 --a-total 400 --b-events 120 --b-total 400" in c for c in j["commands"]), j["commands"]
    d = good_extraction()
    d["groups"].append({"name": "Placebo drink", "n_start": val(1200, "Figure 1"), "n_analysed": val(1000, "Figure 1")})
    d["outcomes"][0]["results"].append({"group": "Placebo drink", "events": val(40), "total": val(1000), "reported_percent": val("4.0")})
    code, j, err = ctx.extraction(d)
    two = [c for c in j["commands"] if "two-by-two" in c and "--a-events 24 " in c]
    assert len(two) == 2 and any("--b-events 40 --b-total 1000" in c for c in two), "three groups give the first against each other: %s" % j["commands"]


@test
def t_extraction_every_number_needs_a_locator(ctx):
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = {"value": 24}
    code, j, err = ctx.extraction(d)
    assert code == 1 and j["result"] == "FAIL" and any("events has no locator" in e for e in j["errors"]), j["errors"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = 24
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("a bare value has no locator" in e for e in j["errors"]), j["errors"]
    d = good_extraction()
    d["groups"][0]["n_start"] = {"value": 1200, "locator": "  "}
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("n_start has no locator" in e for e in j["errors"]), j["errors"]
    d = good_extraction()
    d["groups"][0]["n_start"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert j["errors"] == [] and "group Drink n_start" in j["not_reported"], "a number marked not reported needs no locator and is listed"
    assert code == 3 and j["result"] == "INCOMPLETE" and any("group Drink: loss cannot be worked out (n_start not reported)" in x for x in j["cannot_check"]), \
        "a loss that cannot be worked out is CANNOT CHECK, never a pass: %s %s" % (code, j["cannot_check"])
    d = good_extraction()
    d["claim"] = {"quote": "The drink reduced colds by 40 percent."}
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("claim has no locator" in e for e in j["errors"])
    d = good_extraction()
    d["reporting"][0] = {"item": "funding", "text": "Funded by the maker"}
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("funding has no locator" in e for e in j["errors"])


@test
def t_extraction_percentages_checked_against_counts(ctx):
    d = good_extraction()
    d["outcomes"][0]["results"][0]["reported_percent"] = val("3.9")
    code, j, err = ctx.extraction(d)
    assert code == 1 and j["errors"] == [] and len(j["findings"]) == 1 and j["result"] == "FINDINGS", j
    assert "reported 3.9%, but 24 of 816 is 2.94%" in j["findings"][0] and "would need a count of 32" in j["findings"][0], j["findings"]
    d = good_extraction()
    d["other_percentages"].append({"label": "stomach upset, drink", "count": val(139, "Table 3"), "total": val(1200, "Table 3"), "reported_percent": val("9.6", "Table 3")})
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("stomach upset" in f and "139 of 1200 is 11.58%" in f for f in j["findings"]), j["findings"]
    # 31 of 816 = 3.799: reported as 3.7 it has been cut short, not rounded, and that is a mismatch here as in check-percent.
    d = good_extraction()
    d["outcomes"][1]["results"][0]["reported_percent"] = val("3.7")
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("reported 3.7%, but 31 of 816 is 3.80%" in f for f in j["findings"]), "a truncated percentage must be a finding: %s" % j["findings"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["reported_percent"] = val(2.9)
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("as text, exactly as printed" in e for e in j["errors"]), "a percentage typed as a number loses its precision and is refused"
    d = good_extraction()
    d["outcomes"][0]["results"][0]["reported_percent"] = val("3")
    code, j, err = ctx.extraction(d)
    assert code == 0, "24 of 816 is 2.94, which rounds to 3 at no decimal places"


@test
def t_extraction_sizes_must_be_consistent(ctx):
    d = good_extraction()
    d["groups"][0]["n_analysed"] = val(1201, "Figure 1")
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("analysed (1201) is more than started (1200)" in e for e in j["errors"]), j["errors"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = val(817)
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("events (817) are more than the total (816)" in e for e in j["errors"]), j["errors"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["total"] = val(1201)
    d["outcomes"][0]["results"][0]["reported_percent"] = val("2.0")
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("more than the group started with" in e for e in j["errors"]), j["errors"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["total"] = val(800)
    d["outcomes"][0]["results"][0]["reported_percent"] = val("3.0")
    code, j, err = ctx.extraction(d)
    assert code == 0 and any("out of 800, but the group's analysed size is 816" in a for a in j["advisories"]), j["advisories"]
    d = good_extraction()
    d["groups"][0]["n_analysed"] = val(1200, "Figure 1")
    d["groups"][1]["n_analysed"] = val(1200, "Figure 1")
    code, j, err = ctx.extraction(d)
    assert not any("attrition" in c for c in j["commands"]), "with nobody lost there is no attrition to recompute: %s" % j["commands"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["group"] = "Placebo"
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("no group with that name" in e for e in j["errors"])
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = val(24.5)
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("must be a whole number" in e for e in j["errors"])
    d = good_extraction()
    d["outcomes"][0]["results"][0]["total"] = val(10 ** 400)
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("must be a whole number" in e for e in j["errors"]), "an absurdly large count is refused, not computed with"
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = val(True)
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("must be a whole number" in e for e in j["errors"]), "true is not 1"


@test
def t_extraction_required_fields_and_vocabularies(ctx):
    for key in ("audit_of", "claim", "design", "groups", "outcomes"):
        d = good_extraction()
        del d[key]
        code, j, err = ctx.extraction(d)
        assert code == 1 and j["errors"], "a file with no %s must fail" % key
    d = good_extraction()
    d["design"]["type"] = "experiment"
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("design.type must be one of" in e for e in j["errors"])
    d = good_extraction()
    d["design"]["ceiling"] = ""
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("design.ceiling is missing" in e for e in j["errors"])
    d = good_extraction()
    d["outcomes"][0]["status"] = "primary"
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("status must be one of" in e for e in j["errors"])
    other_digits = "".join(chr(0x660 + int(c)) if c.isdigit() else c for c in "2026-05-04")
    for bad in ("20260504", "2026-02-30", "May 2026", 2026, other_digits, "2026-5-4"):
        d = good_extraction()
        d["audit_of"]["date"] = bad
        code, j, err = ctx.extraction(d)
        assert code == 1 and any("real date written YYYY-MM-DD" in e for e in j["errors"]), "date %r must be refused" % (bad,)
    d = good_extraction()
    d["audit_of"]["date"] = None
    code, j, err = ctx.extraction(d)
    assert code == 0 and "audit_of.date" in j["not_reported"]
    d = good_extraction()
    d["audit_of"]["material"] = "abstract_only"
    code, j, err = ctx.extraction(d)
    assert code == 0 and any("only the abstract only is available" in a and "full text" in a for a in j["advisories"]), j["advisories"]
    d = good_extraction()
    d["supporting_result"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert code == 0 and any("supporting_result" in x for x in j["not_reported"])
    d = good_extraction()
    d["reporting"] = [x for x in d["reporting"] if x["item"] != "blinding"]
    code, j, err = ctx.extraction(d)
    assert code == 0 and any("not addressed for a randomised trial: blinding" in a for a in j["advisories"]), j["advisories"]
    d = good_extraction()
    d["design"]["type"] = "non_randomised_comparison"
    code, j, err = ctx.extraction(d)
    assert code == 0 and any("not addressed for a non randomised comparison: how_groups_were_formed, baseline_comparison, other_differences_between_groups" in a for a in j["advisories"]), \
        "a comparison of groups not formed by chance has its own questions: %s" % j["advisories"]
    d = good_extraction()
    d["design"]["type"] = "benchmark"
    code, j, err = ctx.extraction(d)
    assert any("number_of_runs" in a and "contamination_check" in a and "baseline_tuning" in a for a in j["advisories"]), "a benchmark is asked the benchmark questions"
    code, j, err = ctx.extraction([1, 2])
    assert code == 1 and "one JSON object" in j["errors"][0]


@test
def t_extraction_continuous_results(ctx):
    d = good_extraction()
    d["outcomes"].append({"name": "Days off work", "definition": "Self-reported days absent", "time_frame": "12 weeks", "locator": "Table 2, row 3", "status": "secondary",
                          "results": [{"group": "Drink", "mean": val(1.9), "sd": val(3.1), "n": val(816)},
                                      {"group": "Usual diet", "mean": val(2.1), "sd": val(3.4), "n": val(1080)}]})
    code, j, err = ctx.extraction(d)
    assert code == 0 and any("means --mean1 1.9 --sd1 3.1 --n1 816 --mean2 2.1 --sd2 3.4 --n2 1080" in c for c in j["commands"]), j["commands"]
    d["outcomes"][-1]["results"][0]["sd"] = val(-3.1)
    code, j, err = ctx.extraction(d)
    assert code == 1 and any("cannot be negative" in e for e in j["errors"])
    d["outcomes"][-1]["results"][0]["sd"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert any("Days off work" in x and "sd" in x for x in j["not_reported"]) and not any("means" in c for c in j["commands"])
    assert code == 3 and j["result"] == "INCOMPLETE" and any("Days off work" in x and "cannot be recomputed (sd not reported)" in x for x in j["cannot_check"]), j["cannot_check"]


@test
def t_extraction_missing_inputs_are_cannot_check_never_pass(ctx):
    """A comparison the file sets up but cannot make is reported as CANNOT CHECK, the result is
    INCOMPLETE and the exit code is 3. Each case sits beside its valid neighbour, which passes."""
    code, j, err = ctx.extraction(good_extraction())
    made = j["summary"]["comparisons_made"]
    # HAND: the valid file has 4 outcome percentages and 1 other percentage = 5 compared; 2 groups with both sizes = 2 losses.
    assert code == 0 and j["result"] == "PASS" and j["cannot_check"] == [] and made == {"percentages_against_counts": 5, "group_losses": 2}, (code, j["result"], made)
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert code == 3 and j["result"] == "INCOMPLETE" and j["errors"] == [] and j["findings"] == [], (code, j["result"])
    assert any("Drink: the reported 2.9% cannot be checked against its counts (count not reported)" in x for x in j["cannot_check"]), j["cannot_check"]
    assert j["summary"]["comparisons_made"]["percentages_against_counts"] == 4, "one comparison fewer was made, and the count must say so"
    f = ctx.root / "incomplete.json"
    f.write_bytes(json.dumps(d).encode("utf-8"))
    code, out, err = ctx.run("extraction_check.py", f)
    assert code == 3 and "RESULT: INCOMPLETE" in out and "RESULT: PASS" not in out and "CANNOT CHECK (not a pass" in out and "4 percentage(s) compared" in out, out[-600:]
    d = good_extraction()
    d["outcomes"][1]["results"][1]["total"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert code == 3 and any("the reported 4.1% cannot be checked against its counts (total not reported)" in x for x in j["cannot_check"]), j["cannot_check"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["reported_percent"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert code == 3 and any("24 of 816 has no reported percentage to be checked against" in x for x in j["cannot_check"]), j["cannot_check"]
    d = good_extraction()
    d["other_percentages"][0]["count"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert code == 3 and any("completed follow-up, drink" in x and "cannot be checked" in x for x in j["cannot_check"]), j["cannot_check"]
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = {"not_reported": True}
    d["outcomes"][0]["results"][0]["reported_percent"] = {"not_reported": True}
    code, j, err = ctx.extraction(d)
    assert code == 3 and any("the risk and any difference cannot be recomputed (events not reported)" in x for x in j["cannot_check"]), j["cannot_check"]
    # a mismatch elsewhere still wins: FINDINGS and exit 1, with the comparison that could not be made listed beside it
    d = good_extraction()
    d["outcomes"][0]["results"][0]["events"] = {"not_reported": True}
    d["outcomes"][1]["results"][0]["reported_percent"] = val("4.8")
    code, j, err = ctx.extraction(d)
    assert code == 1 and j["result"] == "FINDINGS" and len(j["cannot_check"]) == 1 and len(j["findings"]) == 1, (code, j["result"], j["cannot_check"])


# ---------------------------------------------------------------- consistency of means and p values

@test
def t_check_mean_matches_hand_worked_and_published_cases(ctx):
    """GRIM. n whole-number responses have a whole-number total, so a mean is a whole number over n.
    HAND and PUBLISHED (Brown and Heathers, preprint pages 4 and 9, read 2026-10-09):
      5.19 with n 28: 5.19 x 28 = 145.32. 145/28 = 5.178571 -> 5.18; 146/28 = 5.214286 -> 5.21. 5.19 is impossible.
      6.28 with n 52: 6.28 x 52 = 326.56. 326/52 = 6.269231 -> 6.27; 327/52 = 6.288462 -> 6.29. 6.28 is impossible,
                      and 6.288 cut short is 6.28, so the figure matches truncation.
    HAND:
      3.48 with n 12 and 4 items: 48 responses. 3.48 x 48 = 167.04; 167/48 = 3.479167 -> 3.48. Possible.
      3.48 with n 12 and 1 item: 3.48 x 12 = 41.76; 41/12 = 3.416667 -> 3.42; 42/12 = 3.5 -> 3.50. Impossible.
      2.5 with n 4: 10/4 = 2.5 exactly. Possible. 2.4 with n 4: 9/4 = 2.25 -> 2.3 or 2.2 (a tie), 10/4 = 2.5. Impossible.
      2.3 with n 4: 9/4 = 2.25, a tie between 2.2 and 2.3; a tie passes either way. Possible; so is 2.2."""
    code, j = ctx.js("check-mean", "--mean", "5.19", "--n", "28")
    r = j["results"]
    assert code == 1 and r["consistent"] is False and r["verdict"] == "mismatch" and r["nearest_possible_means"] == ["5.18", "5.21"] and r["totals_that_fit"] == [], r
    close(r["total_implied"], 145.32, 1e-9, "5.19 x 28")
    for ok in ("5.18", "5.21"):
        code, j = ctx.js("check-mean", "--mean", ok, "--n", "28")
        assert code == 0 and j["results"]["consistent"] is True, "the valid neighbour %s must pass: %s" % (ok, j["results"])
    code, j = ctx.js("check-mean", "--mean", "6.28", "--n", "52")
    assert code == 1 and j["results"]["nearest_possible_means"] == ["6.27", "6.29"] and j["results"]["truncation_matches"] is True, j["results"]
    code, j = ctx.js("check-mean", "--mean", "6.29", "--n", "52")
    assert code == 0 and j["results"]["totals_that_fit"] == [327], j["results"]
    code, j = ctx.js("check-mean", "--mean", "3.48", "--n", "12", "--items", "4")
    assert code == 0 and j["results"]["totals_that_fit"] == [167] and j["results"]["responses_in_the_mean"] == 48, j["results"]
    code, j = ctx.js("check-mean", "--mean", "3.48", "--n", "12")
    assert code == 1 and j["results"]["nearest_possible_means"] == ["3.42", "3.50"], j["results"]
    for mean, want in (("2.5", 0), ("2.4", 1), ("2.3", 0), ("2.2", 0), ("2.1", 1)):
        code, j = ctx.js("check-mean", "--mean", mean, "--n", "4")
        assert code == want, "mean %s with n 4: wanted exit %d, got %d (%s)" % (mean, want, code, j["results"])
    code, out, err = ctx.effect("check-mean", "--mean", "5.19", "--n", "28")
    assert code == 1 and "MISMATCH" in out and "5.18 and 5.21" in out and "What would settle it" in out and "the paper disagrees with itself" in out, out
    for word in ("fraud", "fabricat", "falsif", "misconduct", "made up", "invented"):
        assert word not in out.lower(), "a mismatch is a discrepancy, not an accusation: %r is in the output" % word
    # 5.19 fits n = 26 (135/26 = 5.1923), 27 (140/27 = 5.1852) and 31 (161/31 = 5.1935); it does not fit 25, 29 or 30.
    code, j = ctx.js("check-mean", "--mean", "5.19", "--n", "28")
    assert j["results"]["nearby_sample_sizes_that_fit"] == [26, 27, 31], j["results"]["nearby_sample_sizes_that_fit"]


@test
def t_check_mean_says_cannot_check_when_it_cannot(ctx):
    """With 100 or more responses and two decimal places every mean is possible (steps of 1/100 or
    finer), so the check has nothing to say. That is CANNOT CHECK and exit 3, never a pass. 99 is
    the largest sample that can still be tested at two decimals; 9 at one decimal."""
    for args, want in ((["--mean", "5.19", "--n", "100"], 3), (["--mean", "5.19", "--n", "99"], 0),   # 514/99 = 5.1919 -> 5.19
                       (["--mean", "5.2", "--n", "10"], 3), (["--mean", "5.2", "--n", "9"], 0),       # 47/9 = 5.222 -> 5.2
                       (["--mean", "5", "--n", "1"], 3), (["--mean", "5.19", "--n", "25", "--items", "4"], 3),
                       (["--mean", "5.19"], 3)):
        code, j = ctx.js("check-mean", *args)
        assert code == want, "check-mean %s: wanted exit %d, got %d" % (" ".join(args), want, code)
        if want == 3:
            assert j["results"]["consistent"] is None and j["results"]["verdict"] == "cannot_check" and j["results"]["reason"], j["results"]
            code, out, err = ctx.effect("check-mean", *args)
            assert code == 3 and "CANNOT CHECK" in out and "This is not a pass" in out and "CONSISTENT" not in out, out
    ctx.refused("check-mean", "--n", "28")
    ctx.refused("check-mean", "--mean", "five", "--n", "28")
    ctx.refused("check-mean", "--mean", "nan", "--n", "28")
    ctx.refused("check-mean", "--mean", "5.19", "--n", "0")
    ctx.refused("check-mean", "--mean", "5.19", "--n", "28.5")
    ctx.refused("check-mean", "--mean", "5.19", "--n", "28", "--items", "0")
    ctx.refused("check-mean", "--mean", "5.19e0", "--n", "28")
    code, j = ctx.js("check-mean", "--mean", "-0.25", "--n", "8")     # a mean of whole-number differences may be negative: -2/8
    assert code == 0 and j["results"]["totals_that_fit"] == [-2], j["results"]


def p_of(ctx, *args):
    code, j = ctx.js("check-p", *args)
    return code, j["results"]


@test
def t_p_from_statistic_matches_closed_forms(ctx):
    """Each distribution is checked where its tail has a closed form that can be worked by hand.
      z:            two-sided p = erfc(|z| / sqrt 2). z = 1.959964 gives 0.05 (the 97.5 percent point).
      t, 1 d.f.:    two-sided p = 1 - (2/pi) atan(t).      t = 1 gives 0.5; t = 12.7062 gives 0.05.
      t, 2 d.f.:    two-sided p = 1 - t / sqrt(2 + t^2).   t = 4.3027 gives 1 - 4.3027/4.52913 = 0.0500.
      chi2, 2 d.f.: p = exp(-x/2).                         x = 5.9915 gives 0.0500; x = 2 gives 0.36788.
      chi2, 4 d.f.: p = exp(-x/2) (1 + x/2).               x = 9.4877 gives 0.0500.
      chi2, 1 d.f.: p = erfc(sqrt(x/2)), the square of z.  x = 3.8415 gives 0.0500.
      F(2, d):      p = (1 + 2F/d)^(-d/2).                 F = 3.3541, d = 27 gives 1.24845^-13.5 = 0.0500.
      F(1, d):      the square of t with d d.f.            F = 18.5128 = 4.3027^2, d = 2 gives 0.0500."""
    m = ctx.m()
    f = m.p_from_statistic
    close(f("z", 1.959964, 0, 0, 2), 0.05, 1e-7, "z 1.959964 two-sided")
    close(f("z", 1.959964, 0, 0, 1), 0.025, 1e-7, "z 1.959964 one-sided")
    close(f("z", -2.575829, 0, 0, 2), 0.01, 1e-7, "z -2.575829 two-sided (the sign does not matter)")
    for t in (0.5, 1.0, 3.0, 12.7062, 63.6567):
        close(f("t", t, 1.0, 0, 2), 1.0 - (2.0 / math.pi) * math.atan(t), 1e-10, "t with 1 d.f. at %g" % t)
    close(f("t", 1.0, 1.0, 0, 2), 0.5, 1e-12, "t = 1 with 1 d.f.")
    close(f("t", 12.7062, 1.0, 0, 2), 0.05, 5e-6, "t = 12.7062 with 1 d.f. (a table value, so five figures)")
    for t in (0.5, 1.0, 2.92, 4.3027, 9.925):
        close(f("t", t, 2.0, 0, 2), 1.0 - t / math.sqrt(2.0 + t * t), 1e-10, "t with 2 d.f. at %g" % t)
    close(f("t", 4.3027, 2.0, 0, 2), 0.05, 5e-6, "t = 4.3027 with 2 d.f. (a table value, so five figures)")
    close(f("t", 2.92, 2.0, 0, 1), 0.05, 1e-5, "t = 2.92 with 2 d.f., one-sided")
    for x in (0.1, 2.0, 5.9915, 13.8155, 40.0):
        close(f("chi2", x, 2.0, 0, 2), math.exp(-x / 2.0), 1e-12, "chi-square with 2 d.f. at %g" % x)
        close(f("chi2", x, 4.0, 0, 2), math.exp(-x / 2.0) * (1.0 + x / 2.0), 1e-12, "chi-square with 4 d.f. at %g" % x)
        close(f("chi2", x, 1.0, 0, 2), math.erfc(math.sqrt(x / 2.0)), 1e-12, "chi-square with 1 d.f. at %g" % x)
    close(f("chi2", 5.9915, 2.0, 0, 2), 0.05, 5e-6, "chi-square 5.9915 with 2 d.f.")
    close(f("chi2", 9.4877, 4.0, 0, 2), 0.05, 5e-6, "chi-square 9.4877 with 4 d.f.")
    close(f("chi2", 3.8415, 1.0, 0, 2), 0.05, 5e-6, "chi-square 3.8415 with 1 d.f.")
    for F, d in ((3.3541, 27.0), (1.0, 10.0), (19.0, 2.0), (0.2, 300.0)):
        close(f("f", F, 2.0, d, 2), (1.0 + 2.0 * F / d) ** (-d / 2.0), 1e-10, "F(2, %g) at %g" % (d, F))
    close(f("f", 3.3541, 2.0, 27.0, 2), 0.05, 1e-5, "F(2, 27) = 3.3541")
    for t, d in ((4.3027, 2.0), (2.0484, 28.0), (1.0, 1.0)):
        close(f("f", t * t, 1.0, d, 2), f("t", t, d, 0, 2), 1e-10, "F(1, %g) is the square of t" % d)
    close(f("t", 2.0484, 28.0, 0, 2), 0.05, 2e-6, "t = 2.0484 with 28 d.f. (NIST table: 2.048)")
    close(f("chi2", 0.0, 3.0, 0, 2), 1.0, 0, "chi-square of zero")
    close(f("f", 0.0, 3.0, 9.0, 2), 1.0, 0, "F of zero")
    close(f("t", 2.0, 1e6, 0, 2), f("z", 2.0, 0, 0, 2), 1e-6, "t with a million d.f. is close to z")


@test
def t_check_p_consistent_and_not_with_rounding_allowed(ctx):
    """HAND, with 2 d.f. where p = 1 - t/sqrt(2 + t^2):
      t = 4.30 as printed lies in 4.295 to 4.305.
        p(4.30)  = 1 - 4.30/sqrt(20.49)      = 1 - 4.30/4.526588   = 0.050057
        p(4.305) = 1 - 4.305/sqrt(20.533025) = 1 - 4.305/4.531338  = 0.049949   (lowest p)
        p(4.295) = 1 - 4.295/sqrt(20.447025) = 1 - 4.295/4.521839  = 0.050165   (highest p)
      Reported 0.050 means 0.0495 to 0.0505: overlaps, consistent. Reported 0.05 (0.045 to 0.055): consistent.
      Reported 0.049 means 0.0485 to 0.0495: below 0.049949, mismatch. Reported 0.051 (0.0505 to 0.0515): above 0.050165, mismatch.
      "p < 0.05": the lowest p, 0.049949, is below 0.05, so consistent. "p < 0.04": mismatch.
      "p > 0.05": the highest p, 0.050165, is above 0.05, so consistent. "p > 0.06": mismatch."""
    base = ["--test", "t", "--statistic", "4.30", "--df", "2"]
    code, r = p_of(ctx, *(base + ["--reported", "0.050"]))
    assert code == 0 and r["consistent"] is True, r
    close(r["recomputed_p"], 0.05006, 6e-6, "p for t = 4.30 with 2 d.f.")
    close(r["recomputed_p_range"][0], 0.04995, 6e-6, "lowest p allowing for rounding")
    close(r["recomputed_p_range"][1], 0.05017, 6e-6, "highest p allowing for rounding")
    for reported, relation, want in (("0.05", "eq", 0), (".050", "eq", 0), ("0.049", "eq", 1), ("0.051", "eq", 1), ("0.04", "eq", 1), ("0.06", "eq", 1),
                                     ("0.05", "lt", 0), ("0.04", "lt", 1), ("0.05", "gt", 0), ("0.06", "gt", 1), ("0.001", "lt", 1), ("0.10", "lt", 0)):
        code, r = p_of(ctx, *(base + ["--reported", reported, "--relation", relation]))
        assert code == want and r["consistent"] is (want == 0), "t(2) = 4.30 with p %s %s: wanted exit %d, got %d (%s)" % (relation, reported, want, code, r)
    # chi-square with 2 d.f.: p = exp(-x/2). x = 9.21 gives exp(-4.605) = 0.010002; printed 9.21 spans 0.009977 to 0.010027.
    for reported, want in (("0.01", 0), ("0.010", 0), ("0.011", 1), ("0.009", 1), ("0.02", 1), ("0.001", 1)):
        code, r = p_of(ctx, "--test", "chi2", "--statistic", "9.21", "--df", "2", "--reported", reported)
        assert code == want, "chi-square(2) = 9.21 with p = %s: wanted exit %d, got %d (%s)" % (reported, want, code, r)
    # p printed as .000 means below 0.0005: chi-square(2) = 20 gives exp(-10) = 0.0000454, consistent; chi-square(2) = 12 gives 0.00248, not.
    assert p_of(ctx, "--test", "chi2", "--statistic", "20", "--df", "2", "--reported", ".000")[0] == 0
    assert p_of(ctx, "--test", "chi2", "--statistic", "12", "--df", "2", "--reported", ".000")[0] == 1
    # F(2, 27): p = (1 + 2F/27)^-13.5. F = 3.35 gives 0.05017; F = 5.49 gives 1.40667^-13.5 = 0.00999.
    assert p_of(ctx, "--test", "f", "--statistic", "5.49", "--df", "2", "--df2", "27", "--reported", "0.01")[0] == 0
    assert p_of(ctx, "--test", "f", "--statistic", "5.49", "--df", "2", "--df2", "27", "--reported", "0.05")[0] == 1
    # z = 1.96: erfc(1.96/1.414214) = 0.049996; z = 2.58 gives 0.00988.
    assert p_of(ctx, "--test", "z", "--statistic", "1.96", "--reported", "0.05")[0] == 0
    assert p_of(ctx, "--test", "z", "--statistic", "-1.96", "--reported", "0.05")[0] == 0
    assert p_of(ctx, "--test", "z", "--statistic", "2.58", "--reported", "0.05")[0] == 1
    code, out, err = ctx.effect(*(["check-p"] + base + ["--reported", "0.049"]))
    assert code == 1 and "MISMATCH" in out and "What would settle it" in out and "the paper disagrees with itself" in out, out
    for word in ("fraud", "fabricat", "falsif", "misconduct", "made up", "invented"):
        assert word not in out.lower(), "a mismatch is a discrepancy, not an accusation: %r is in the output" % word


@test
def t_check_p_one_sided_and_the_0_05_line(ctx):
    """HAND, 2 d.f.: t = 2.92 gives a two-sided p of 1 - 2.92/sqrt(10.5264) = 1 - 2.92/3.244441 = 0.10000,
    and a one-sided p of 0.05000. A paper that prints p = 0.05 beside t(2) = 2.92 has reported a
    one-sided value: a mismatch for a two-sided test, with the one-sided match pointed out."""
    base = ["--test", "t", "--statistic", "2.92", "--df", "2"]
    code, r = p_of(ctx, *(base + ["--reported", "0.10"]))
    assert code == 0, r
    code, r = p_of(ctx, *(base + ["--reported", "0.05"]))
    assert code == 1 and r["other_tails"]["tails"] == 1 and r["other_tails"]["matches"] is True, r
    close(r["other_tails"]["p"], 0.05, 1e-5, "one-sided p")
    code, out, err = ctx.effect(*(["check-p"] + base + ["--reported", "0.05"]))
    assert "A one-sided test would give p = 0.0500, which matches" in out, out
    code, r = p_of(ctx, *(base + ["--reported", "0.05", "--tails", "1"]))
    assert code == 0 and r["tails"] == 1, r
    code, r = p_of(ctx, *(base + ["--reported", "0.03"]))
    assert code == 1 and r["other_tails"]["matches"] is False and r["side_of_0_05"] == "reported below 0.05, recomputed at or above", r
    code, r = p_of(ctx, *(base + ["--reported", "0.12"]))
    assert code == 1 and r["side_of_0_05"] is None, "both at or above 0.05: no change of side: %s" % r


@test
def t_check_p_says_cannot_check_without_degrees_of_freedom(ctx):
    for args in (["--test", "t", "--statistic", "2.10", "--reported", "0.045"], ["--test", "chi2", "--statistic", "5.99", "--reported", "0.05"],
                 ["--test", "f", "--statistic", "3.35", "--df", "2", "--reported", "0.05"], ["--test", "f", "--statistic", "3.35", "--reported", "0.05"]):
        code, j = ctx.js("check-p", *args)
        assert code == 3 and j["results"]["consistent"] is None and j["results"]["verdict"] == "cannot_check", "check-p %s: %s %s" % (" ".join(args), code, j["results"])
        code, out, err = ctx.effect("check-p", *args)
        assert code == 3 and "CANNOT CHECK" in out and "This is not a pass" in out and "CONSISTENT" not in out, out
    # the valid neighbours: the same statistics with their degrees of freedom, and z, which has none
    assert p_of(ctx, "--test", "t", "--statistic", "2.10", "--df", "28", "--reported", "0.045")[0] == 0
    assert p_of(ctx, "--test", "chi2", "--statistic", "5.99", "--df", "2", "--reported", "0.05")[0] == 0
    assert p_of(ctx, "--test", "z", "--statistic", "1.96", "--reported", "0.05")[0] == 0
    good = ["check-p", "--test", "t", "--statistic", "2.10", "--df", "28", "--reported", "0.045"]
    ctx.accepted(*good)
    for key, value in (("--test", "q"), ("--statistic", "big"), ("--statistic", "nan"), ("--statistic", "inf"), ("--statistic", "2e1"), ("--reported", "1.5"),
                       ("--reported", "p<.05"), ("--reported", "<0.05"), ("--reported", "-0.01"), ("--reported", "0.05%"), ("--relation", "le"), ("--tails", "3"),
                       ("--df", "0"), ("--df", "-3"), ("--df", "nan"), ("--df2", "5")):
        args = list(good)
        if key in args:
            args[args.index(key) + 1] = value
        else:
            args += [key, value]
        ctx.refused(*args)
    ctx.refused("check-p", "--test", "z", "--statistic", "1.96", "--df", "10", "--reported", "0.05")
    ctx.refused("check-p", "--test", "chi2", "--statistic", "-5.99", "--df", "2", "--reported", "0.05")
    ctx.refused("check-p", "--test", "chi2", "--statistic", "5.99", "--df", "2", "--reported", "0.05", "--tails", "1")
    ctx.refused("check-p", "--test", "t", "--df", "28", "--reported", "0.045")
    ctx.refused("check-p", "--test", "t", "--statistic", "2.10", "--df", "28")
    ctx.accepted("check-p", "--test", "t", "--statistic", "2.10", "--df", "27.4", "--reported", "0.045")   # Welch gives fractional d.f.


@test
def t_two_by_two_reported_p_against_the_counts(ctx):
    """HAND. Pearson's chi-square for a two-by-two table is N (ad - bc)^2 / (row1 x row2 x col1 x col2), and
    with 1 degree of freedom its p value is erfc(sqrt(chi-square / 2)).
      10 of 20 against 5 of 20: a = 10, b = 10, c = 5, d = 15, N = 40. ad - bc = 150 - 50 = 100.
        chi-square = 40 x 100^2 / (20 x 20 x 15 x 25) = 400,000 / 150,000 = 2.666667; p = erfc(1.154701) = 0.102470.
        With the continuity correction: (100 - 40/2)^2 = 6,400; 40 x 6,400 / 150,000 = 1.706667; p = erfc(0.923760) = 0.191418.
      24 of 816 against 53 of 1,080: ad - bc = 24 x 1,027 - 792 x 53 = 24,648 - 41,976 = -17,328; N = 1,896.
        chi-square = 1,896 x 17,328^2 / (816 x 1,080 x 77 x 1,819) = 5.692922e11 / 1.234347e11 = 4.61209; p = erfc(1.518567) = 0.03175."""
    m = ctx.m()
    c = m.chi_square_2x2(10, 20, 5, 20)
    close(c["plain"], 2.666667, 1e-6, "chi-square, 10/20 against 5/20")
    close(c["p_plain"], math.erfc(math.sqrt(2.666667 / 2.0)), 1e-7, "its p value")
    close(c["p_plain"], 0.102470, 1e-6, "its p value, as worked")
    close(c["corrected"], 1.706667, 1e-6, "chi-square with the continuity correction")
    close(c["p_corrected"], 0.191418, 1e-6, "its p value")
    c = m.chi_square_2x2(24, 816, 53, 1080)
    close(c["plain"], 1896.0 * 17328.0 ** 2 / (816.0 * 1080.0 * 77.0 * 1819.0), 1e-9, "chi-square, 24/816 against 53/1080, from the formula")
    close(c["plain"], 4.61209, 1e-5, "the same, as worked")
    close(c["p_plain"], 0.03175, 1e-5, "its p value")
    assert m.chi_square_2x2(0, 20, 0, 20) is None and m.chi_square_2x2(20, 20, 20, 20) is None, "an empty margin has no chi-square"
    base = ["two-by-two", "--a-events", "10", "--a-total", "20", "--b-events", "5", "--b-total", "20"]
    for reported, relation, want, which in (("0.10", "eq", 0, "uncorrected"), ("0.1", "eq", 0, "uncorrected"), ("0.19", "eq", 0, "continuity-corrected"),
                                            ("0.2", "eq", 0, "continuity-corrected"), ("0.15", "eq", 1, None), ("0.11", "eq", 1, None), ("0.09", "eq", 1, None),
                                            ("0.18", "eq", 1, None), ("0.20", "eq", 1, None), ("0.05", "gt", 0, "both"), ("0.05", "lt", 1, None),
                                            ("0.15", "lt", 0, "uncorrected"), ("0.15", "gt", 0, "continuity-corrected")):
        code, j = ctx.js(*(base + ["--reported-p", reported, "--p-relation", relation]))
        chk = j["results"]["p_value_check"]
        assert code == want and chk["consistent"] is (want == 0) and chk["matches"] == which, "p %s %s: wanted exit %d matching %s, got %d: %s" % (relation, reported, want, which, code, chk)
        assert "absolute_difference" in j["results"], "the p check is added to the table's results, it does not replace them"
    code, j = ctx.js("two-by-two", "--a-events", "24", "--a-total", "816", "--b-events", "53", "--b-total", "1080", "--reported-p", "0.03")
    assert code == 0 and j["results"]["p_value_check"]["p"] == 0.03175 and j["results"]["p_value_check"]["chi_square"] == 4.61, j["results"]["p_value_check"]
    code, out, err = ctx.effect(*(base + ["--reported-p", "0.15"]))
    assert code == 1 and "MISMATCH" in out and "What would settle it" in out and "Fisher's exact test" in out, out
    for word in ("fraud", "fabricat", "falsif", "misconduct", "made up", "invented"):
        assert word not in out.lower(), "a mismatch is a discrepancy, not an accusation: %r is in the output" % word
    # no events in either group: the statistic is undefined. That is CANNOT CHECK and exit 3, never a pass.
    for args in (["--a-events", "0", "--a-total", "20", "--b-events", "0", "--b-total", "20"], ["--a-events", "20", "--a-total", "20", "--b-events", "20", "--b-total", "20"]):
        code, j = ctx.js("two-by-two", *(args + ["--reported-p", "0.5"]))
        assert code == 3 and j["results"]["p_value_check"]["consistent"] is None and j["results"]["p_value_check"]["verdict"] == "cannot_check", j["results"]["p_value_check"]
        code, out, err = ctx.effect("two-by-two", *(args + ["--reported-p", "0.5"]))
        assert code == 3 and "CANNOT CHECK" in out and "This is not a pass" in out and "CONSISTENT" not in out, out
    code, j = ctx.js(*base)
    assert code == 0 and "p_value_check" not in j["results"], "without --reported-p nothing about p values is printed"
    ctx.refused(*(base + ["--p-relation", "lt"]))
    ctx.refused(*(base + ["--reported-p", "1.2"]))
    ctx.refused(*(base + ["--reported-p", "p=0.03"]))
    ctx.refused(*(base + ["--reported-p", "0.03", "--p-relation", "le"]))
    ctx.refused(*(base + ["--reported-p", "nan"]))


# ---------------------------------------------------------------- planted faults

PLANTED = [
    {"name": "relative_without_absolute", "what": "a copy of two-by-two that reports the risk ratio and leaves out the absolute difference",
     "file": "effect.py",
     "edits": [('    L.append("  ABSOLUTE  %s minus %s = %s percentage points (Newcombe interval %s to %s). The interval %s zero."\n             % (la, lb, num(100 * d, pp), num(100 * dlo, pp), num(100 * dhi, pp), "includes" if dlo <= 0.0 <= dhi else "excludes"))\n', ""),
               ('    if rr[0] is None:\n        res["risk_ratio"] = {"value": None,', '    del res["absolute_difference"]\n    if rr[0] is None:\n        res["risk_ratio"] = {"value": None,'),
               ('    if rr[0] is not None:\n        L.append("  TOGETHER', '    if False:\n        L.append("  TOGETHER')],
     "tests": ["two_by_two_reports_absolute_difference_with_relative"]},
    {"name": "nnt_from_relative_risk", "what": "a copy that computes the number needed to treat from the relative risk",
     "file": "effect.py",
     "edits": [("    point, interval = number_needed(d, dlo, dhi)\n", "    point, interval = number_needed((rr[0] - 1.0) if rr[0] else d, dlo, dhi)\n")],
     "tests": ["number_needed_comes_from_the_absolute_difference"]},
    {"name": "nnt_interval_when_zero_included", "what": "a copy that prints a finite NNT interval although the difference interval includes zero",
     "file": "effect.py", "edits": [("    if lo <= 0.0 <= hi:\n        return point, None\n", "")],
     "tests": ["number_needed_interval_follows_the_difference_interval"]},
    {"name": "wald_for_wilson", "what": "a copy whose proportion interval is the Wald interval",
     "file": "effect.py",
     "edits": [("    centre = (p + z2 / (2.0 * n)) / denom\n    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denom\n",
                "    centre = p\n    half = z * math.sqrt(p * (1.0 - p) / n)\n")],
     "tests": ["wilson_matches_hand_worked_values", "wilson_matches_newcombe_table_one", "newcombe_difference_matches_published_examples",
               "proportion_command_reports_counts_and_wilson_interval"]},
    {"name": "wald_for_newcombe", "what": "a copy whose difference interval is the Wald interval",
     "file": "effect.py",
     "edits": [("    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)\n    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)\n",
                "    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)\n    lo, hi = d - z * se, d + z * se\n")],
     "tests": ["newcombe_difference_matches_published_examples"]},
    {"name": "wrong_z", "what": "a copy that uses the one-sided 95 percent quantile 1.645",
     "file": "effect.py", "edits": [("    return statistics.NormalDist().inv_cdf(0.5 + level / 200.0)", "    return statistics.NormalDist().inv_cdf(level / 100.0)")],
     "tests": ["wilson_matches_hand_worked_values", "risk_ratio_matches_published_example", "odds_ratio_matches_published_example"]},
    {"name": "risk_ratio_se_drops_totals", "what": "a copy whose risk ratio standard error leaves out the 1/n terms",
     "file": "effect.py", "edits": [("    se = math.sqrt(1.0 / k1 - 1.0 / n1 + 1.0 / k2 - 1.0 / n2)", "    se = math.sqrt(1.0 / k1 + 1.0 / k2)")],
     "tests": ["risk_ratio_matches_published_example"]},
    {"name": "odds_ratio_is_risk_ratio", "what": "a copy that reports the risk ratio under the name odds ratio",
     "file": "effect.py", "edits": [("    value = (a * d) / (b * c)\n", "    value = (a / (a + b)) / (c / (c + d))\n")],
     "tests": ["odds_ratio_matches_published_example"]},
    {"name": "pooled_degrees_of_freedom", "what": "a copy whose Welch interval uses n1 + n2 - 2 degrees of freedom",
     "file": "effect.py", "edits": [("    df = (v1 + v2) ** 2 / (v1 * v1 / (n1 - 1) + v2 * v2 / (n2 - 1))", "    df = float(n1 + n2 - 2)")],
     "tests": ["welch_interval_matches_hand_worked_values"]},
    {"name": "d_from_standard_error", "what": "a copy whose Cohen's d divides by the standard error",
     "file": "effect.py", "edits": [("    return None if sp == 0 else (m1 - m2) / sp", "    return None if sp == 0 else (m1 - m2) / math.sqrt(s1 * s1 / n1 + s2 * s2 / n2)")],
     "tests": ["cohens_d_uses_the_pooled_standard_deviation"]},
    {"name": "normal_for_t", "what": "a copy that uses the normal quantile in place of Student's t",
     "file": "effect.py", "edits": [("    tcrit = t_quantile(0.5 + level / 200.0, df)", "    tcrit = z_for(level)")],
     "tests": ["welch_interval_matches_hand_worked_values"]},
    {"name": "percent_truncates", "what": "a copy whose percent check accepts a figure cut short instead of rounded",
     "file": "effect.py", "edits": [('"consistent": abs(exact - stated) <= tol,', '"consistent": abs(exact - stated) <= tol or truncated == stated,')],
     "tests": ["check_percent_boundary_rounding", "extraction_percentages_checked_against_counts"]},
    {"name": "percent_too_lenient", "what": "a copy whose percent check allows a whole unit of the last place",
     "file": "effect.py", "edits": [("    tol = Fraction(1, 2 * 10 ** places)", "    tol = Fraction(1, 10 ** places)")],
     "tests": ["check_percent_boundary_rounding"]},
    {"name": "percent_rejects_ties", "what": "a copy whose percent check fails an exact tie",
     "file": "effect.py", "edits": [('"consistent": abs(exact - stated) <= tol,', '"consistent": abs(exact - stated) < tol,')],
     "tests": ["check_percent_boundary_rounding"]},
    {"name": "accepts_events_above_total", "what": "a copy that computes with more events than people",
     "file": "effect.py", "edits": [("    if k > n:\n        raise Stop(\"%s (%d) is larger than %s (%d), which is impossible\" % (ek, k, tk, n))\n", "")],
     "tests": ["impossible_inputs_refused_with_valid_neighbours"]},
    {"name": "parses_numbers_loosely", "what": "a copy that takes whatever float() takes: underscores, padding, other scripts' digits",
     "file": "effect.py", "edits": [("    if not DECIMAL.fullmatch(text):\n        raise Stop(\"%s must be a plain number, got %r (NaN, infinity and words are refused)\" % (key, text[:20]))\n    v = float(text)\n    if not math.isfinite(v):\n        raise Stop(\"%s is not a finite number\" % key)\n",
                                     "    try:\n        v = float(text)\n    except ValueError:\n        raise Stop(\"%s must be a number\" % key)\n")],
     "tests": ["impossible_inputs_refused_with_valid_neighbours"]},
    {"name": "attrition_ignores_groups", "what": "a copy that calls unequal loss balanced",
     "file": "effect.py", "edits": [("        clear = not (dlo <= 0.0 <= dhi)\n        res[\"balance\"]", "        clear = False\n        res[\"balance\"]")],
     "tests": ["attrition_overall_by_group_and_balance"]},
    {"name": "relative_reported_as_absolute", "what": "a copy that reports the relative change as the absolute one",
     "file": "effect.py", "edits": [("    diff = new - baseline\n    btext, den = natural(baseline)", "    diff = ratio - 1.0\n    btext, den = natural(baseline)")],
     "tests": ["relative_to_absolute_states_both"]},
    {"name": "too_many_decimals", "what": "a copy that prints two decimal places whatever the group size",
     "file": "effect.py", "edits": [("    if n < 100:\n        return 0\n    return 1 if n < 10000 else 2", "    return 2")],
     "tests": ["precision_follows_the_group_size", "proportion_command_reports_counts_and_wilson_interval"]},
    {"name": "locators_optional", "what": "a copy of the extraction check that does not require locators",
     "file": "extraction_check.py", "edits": [('        if not text_ok(obj.get("locator")):\n            self.errors.append("%s has no locator: say where in the paper the number is" % where)\n', "")],
     "tests": ["extraction_every_number_needs_a_locator"]},
    {"name": "extraction_skips_percent_check", "what": "a copy of the extraction check that does not compare percentages with counts",
     "file": "extraction_check.py", "edits": [('        if not r["consistent"]:\n            fits', '        if False:\n            fits')],
     "tests": ["extraction_percentages_checked_against_counts"]},
    {"name": "extraction_ignores_sizes", "what": "a copy of the extraction check that accepts more events than people",
     "file": "extraction_check.py", "edits": [("                if ev > tot:\n                    c.errors.append", "                if False:\n                    c.errors.append")],
     "tests": ["extraction_sizes_must_be_consistent"]},
    {"name": "extraction_hides_not_reported", "what": "a copy of the extraction check that does not list what is marked not reported",
     "file": "extraction_check.py", "edits": [('        if r.get("not_reported") is True:\n            c.not_reported.append(item.replace("_", " "))', '        if r.get("not_reported") is True:\n            pass')],
     "tests": ["extraction_valid_file_passes_and_suggests_commands"]},
    {"name": "extraction_passes_what_it_could_not_check", "what": "a copy of the extraction check that reports PASS when a comparison could not be made",
     "file": "extraction_check.py", "edits": [('("INCOMPLETE" if c.cannot else "PASS")', '"PASS"'), ("    return 1 if failed else (3 if c.cannot else 0)", "    return 1 if failed else 0")],
     "tests": ["extraction_missing_inputs_are_cannot_check_never_pass", "extraction_template_passes_its_own_check"]},
    {"name": "extraction_drops_missing_percent_silently", "what": "a copy of the extraction check that skips a percentage with a missing count and says nothing",
     "file": "extraction_check.py", "edits": [("            if raw is not None:\n                names = (", "            if False:\n                names = (")],
     "tests": ["extraction_missing_inputs_are_cannot_check_never_pass"]},
    {"name": "mean_check_ignores_items", "what": "a copy whose mean check forgets the number of scale items",
     "file": "effect.py", "edits": [("    cells = n * items\n", "    cells = n\n")], "tests": ["check_mean_matches_hand_worked_and_published_cases"]},
    {"name": "mean_check_one_unit_slack", "what": "a copy whose mean check allows a whole unit of the last decimal place",
     "file": "effect.py", "edits": [("    slack = Fraction(1, 2 * 10 ** places)\n", "    slack = Fraction(1, 10 ** places)\n")],
     "tests": ["check_mean_matches_hand_worked_and_published_cases"]},
    {"name": "mean_check_passes_when_blind", "what": "a copy whose mean check says CONSISTENT at sample sizes where it cannot tell",
     "file": "effect.py", "edits": [("    if cells >= 10 ** places:\n", "    if False:\n")], "tests": ["check_mean_says_cannot_check_when_it_cannot"]},
    {"name": "p_check_one_tail_by_default", "what": "a copy whose p check halves every t and z p value",
     "file": "effect.py", "edits": [("    return both / 2.0 if tails == 1 else both", "    return both / 2.0")],
     "tests": ["p_from_statistic_matches_closed_forms", "check_p_consistent_and_not_with_rounding_allowed", "check_p_one_sided_and_the_0_05_line"]},
    {"name": "p_check_ignores_rounding_of_p", "what": "a copy whose p check wants the reported p to equal the recomputed one to many places",
     "file": "effect.py", "edits": [("    tol = 0.5 * 10 ** (-pdp)\n", "    tol = 0.0\n")], "tests": ["check_p_consistent_and_not_with_rounding_allowed"]},
    {"name": "p_check_too_lenient", "what": "a copy whose p check allows a whole unit of the last place of the reported p",
     "file": "effect.py", "edits": [("    tol = 0.5 * 10 ** (-pdp)\n", "    tol = 1.0 * 10 ** (-pdp)\n")], "tests": ["check_p_consistent_and_not_with_rounding_allowed"]},
    {"name": "p_check_guesses_degrees_of_freedom", "what": "a copy whose p check assumes 30 degrees of freedom when none are given and reports a verdict",
     "file": "effect.py", "edits": [("    if need:\n        return cannot(", "    for k in need:\n        dfs[k] = 30.0\n    if False:\n        return cannot(")],
     "tests": ["check_p_says_cannot_check_without_degrees_of_freedom"]},
    {"name": "chi2_uses_lower_tail", "what": "a copy whose chi-square p value is the lower tail",
     "file": "effect.py", "edits": [("        return gamma_upper(df / 2.0, x / 2.0)", "        return 1.0 - gamma_upper(df / 2.0, x / 2.0)")],
     "tests": ["p_from_statistic_matches_closed_forms", "check_p_consistent_and_not_with_rounding_allowed"]},
    {"name": "chi_square_forgets_the_column_totals", "what": "a copy whose table chi-square divides by the row totals only",
     "file": "effect.py", "edits": [("    margins = n1 * n2 * (a + c) * (b + d)\n", "    margins = n1 * n2 * n\n")], "tests": ["two_by_two_reported_p_against_the_counts"]},
    {"name": "table_p_passes_when_undefined", "what": "a copy that calls a reported p consistent when the chi-square cannot be computed",
     "file": "effect.py", "edits": [("    if margins == 0:\n        return None\n", "    if margins == 0:\n        return {\"plain\": 0.0, \"p_plain\": 0.5, \"corrected\": 0.0, \"p_corrected\": 0.5}\n")],
     "tests": ["two_by_two_reported_p_against_the_counts"]},
    {"name": "f_swaps_degrees_of_freedom", "what": "a copy whose F p value swaps the two degrees of freedom",
     "file": "effect.py", "edits": [("        return betainc(df2 / 2.0, df / 2.0, df2 / (df2 + df * x)) if x > 0 else 1.0", "        return betainc(df / 2.0, df2 / 2.0, df / (df + df2 * x)) if x > 0 else 1.0")],
     "tests": ["p_from_statistic_matches_closed_forms"]},
]


def run_tests(ctx, names):
    results, lookup = [], dict(TESTS)
    for name in names:
        try:
            lookup[name](ctx)
            results.append((name, "PASS", ""))
        except AssertionError as e:
            results.append((name, "FAIL", str(e) or "assertion failed"))
        except Exception as e:  # noqa: BLE001  a crash in a test is a failure, reported not raised
            results.append((name, "FAIL", "%s: %s" % (type(e).__name__, e)))
    return results


def main(argv):
    flags, opts, it = set(), {}, iter(argv)
    for a in it:
        if a in ("--list", "--planted", "--json"):
            flags.add(a)
        elif a in ("--scripts", "--only", "--workdir"):
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("test_effect: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        else:
            print("test_effect: unknown argument " + a.encode("ascii", "replace").decode("ascii"), file=sys.stderr)
            return 2
    names = [n for n, _f in TESTS]
    if "--list" in flags:
        print("\n".join(names))
        return 0
    if "--only" in opts:
        wanted = [x.strip() for x in opts["--only"].split(",") if x.strip()]
        unknown = [x for x in wanted if x not in names]
        if unknown:
            print("test_effect: no test named " + ", ".join(unknown), file=sys.stderr)
            return 2
        names = wanted
    scripts = Path(opts.get("--scripts", str(HERE)))
    if not (scripts / "effect.py").is_file() or not (scripts / "extraction_check.py").is_file():
        print("test_effect: %s does not hold effect.py and extraction_check.py" % scripts, file=sys.stderr)
        return 2
    workdir = opts.get("--workdir")
    if workdir and not Path(workdir).is_dir():
        print("test_effect: --workdir %s is not a folder" % workdir, file=sys.stderr)
        return 2
    lines, fails, report = [], 0, {"tests": [], "planted": []}
    if "--planted" in flags:
        base = Path(tempfile.mkdtemp(prefix="effect-planted-", dir=workdir))
        try:
            for plant in PLANTED:
                if "--only" in opts and not set(plant["tests"]) & set(names):
                    continue
                folder = base / plant["name"]
                folder.mkdir()
                problem = None
                for fname in ("effect.py", "extraction_check.py"):
                    source = (scripts / fname).read_text(encoding="ascii")
                    if fname == plant["file"]:
                        for old, new in plant["edits"]:
                            if source.count(old) != 1:
                                problem = "the text to change occurs %d times in %s, wanted once: %r" % (source.count(old), fname, old[:50])
                            source = source.replace(old, new)
                    (folder / fname).write_text(source, encoding="ascii")
                if problem:
                    lines.append("FAIL     planted %s: %s" % (plant["name"], problem))
                    fails += 1
                    continue
                ctx = Ctx(folder, workdir)
                try:
                    res = run_tests(ctx, [t for t in plant["tests"] if "--only" not in opts or t in names])
                finally:
                    ctx.cleanup()
                for name, status, detail in res:
                    caught = status == "FAIL"
                    if not caught:
                        fails += 1
                    lines.append("%-8s planted %s (%s)" % ("CAUGHT" if caught else "MISSED", plant["name"], plant["what"]))
                    lines.append("           by %s: %s" % (name, (detail or "the test passed on the broken copy").replace("\n", " ")[:230]))
                    report["planted"].append({"fault": plant["name"], "test": name, "caught": caught, "detail": detail})
        finally:
            shutil.rmtree(str(base), ignore_errors=True)
        total = len(report["planted"])
        caught = sum(1 for p in report["planted"] if p["caught"])
        lines.append("RESULT: %s. %d of %d planted fault checks caught, %d missed." % ("FAIL" if fails else "PASS", caught, total, total - caught))
    else:
        ctx = Ctx(scripts, workdir)
        try:
            res = run_tests(ctx, names)
        finally:
            ctx.cleanup()
        for name, status, detail in res:
            if status == "FAIL":
                fails += 1
            lines.append("%-8s %s%s" % (status, name, ("  [%s]" % detail.replace("\n", " ")[:320]) if detail else ""))
            report["tests"].append({"name": name, "status": status, "detail": detail})
        lines.append("RESULT: %s. %d test(s): %d passed, %d failed." % ("FAIL" if fails else "PASS", len(res), len(res) - fails, fails))
    if "--json" in flags:
        report["failed"] = fails
        text = json.dumps(report, indent=1, ensure_ascii=True)
    else:
        text = "\n".join(lines)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
