#!/usr/bin/env python3
"""Tests for fermi.py, with hand-worked expected values and planted failures. Standard library only.

Usage:
  python test_fermi.py                    run every test against the fermi.py beside this file
  python test_fermi.py --script PATH      run every test against another copy of the script
  python test_fermi.py --only NAME        run one test
  python test_fermi.py --planted          build broken copies of fermi.py in a temporary folder and
                                          show that the named test fails on each of them

Each expected value is worked by hand in a comment beside the test, from the definitions in the
fermi.py docstring, so a test does not depend on the code it checks. Fixtures are written to a
temporary folder and removed afterwards; nothing is written next to the scripts.

What it enforces: every test passes (exit 0) or a test fails (exit 1). With --planted: the real
script passes every test AND each broken copy is caught by the test named for it; otherwise exit 1.
What it cannot tell: whether a model's ranges are sensible, or whether the estimate is right.

Exit codes: 0 all passed. 1 a test failed, or a planted failure was not caught. 2 bad arguments.
"""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
Z = 1.6448536269514722  # standard normal 95th percentile, from tables (1.645 to three places)
_COUNT = [0]


def load_module(path):
    _COUNT[0] += 1
    spec = importlib.util.spec_from_file_location("fermi_under_test_%d" % _COUNT[0], str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Ctx:
    def __init__(self, script):
        self.script = Path(script)
        self.mod = load_module(self.script)
        self.tmp = Path(tempfile.mkdtemp(prefix="fermi_test_"))
        self.n = 0

    def write(self, obj, raw=None):
        self.n += 1
        p = self.tmp / ("model_%03d.json" % self.n)
        p.write_bytes(raw if raw is not None else json.dumps(obj).encode("utf-8"))
        return p

    def cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, "-B", str(self.script)] + [str(a) for a in args], capture_output=True, env=env, timeout=300)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    def close(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)


def near(a, b, tol):
    return abs(a - b) <= tol


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def base_model(**over):
    m = {"quantity": "Test quantity", "unit": "things", "timeframe": "one year", "scope": "test",
         "inputs": {"a": {"dist": "uniform", "low": 1, "high": 3, "why": "bounds are known for this test"}},
         "formula": "a", "runs": 2000, "seed": 7}
    m.update(over)
    return m


# ---------------------------------------------------------------- conversions

def test_z90_constant(c):
    # Tables give the 95th percentile of the standard normal as 1.6449 (1.645 to three places).
    expect(near(c.mod.Z90, Z, 1e-9), "Z90 is %r, expected 1.6448536" % c.mod.Z90)


def test_normal_low_high_are_5th_and_95th_percentiles(c):
    # low 10, high 30. mean = (10 + 30) / 2 = 20. sd = (30 - 10) / (2 * 1.6448536) = 20 / 3.2897073 = 6.07957.
    mu, sd = c.mod.normal_params(10, 30)
    expect(near(mu, 20.0, 1e-12) and near(sd, 6.07957, 1e-5), "normal_params(10, 30) gave %r, %r" % (mu, sd))
    s = {"dist": "normal", "low": 10, "high": 30}
    # 5th percentile = 20 - 1.6448536 * 6.07957 = 10; 95th = 30; median = 20.
    for u, want in ((0.05, 10.0), (0.5, 20.0), (0.95, 30.0)):
        expect(near(c.mod.quantile(s, u), want, 1e-9), "normal quantile(%g) is %r, expected %g" % (u, c.mod.quantile(s, u), want))
    m = base_model(inputs={"a": dict(s, why="a symmetric additive quantity")}, runs=20000)
    out, _, _ = c.mod.simulate(m, c.mod.check_model(m)[2])
    # 5 percent of 20,000 draws should fall below low: 1,000. Standard error of that share is
    # sqrt(0.05 * 0.95 / 20000) = 0.00154, so four standard errors is 0.0062.
    below = sum(1 for x in out if x < 10) / len(out)
    above = sum(1 for x in out if x > 30) / len(out)
    expect(near(below, 0.05, 0.0062) and near(above, 0.05, 0.0062), "shares outside 10..30 are %.4f and %.4f, expected 0.05 each" % (below, above))


def test_lognormal_low_high_are_5th_and_95th_percentiles(c):
    # low 2, high 50. ln 2 = 0.693147, ln 50 = 3.912023.
    # mean of ln X = (0.693147 + 3.912023) / 2 = 2.302585 = ln 10, so the median is sqrt(2 * 50) = 10.
    # sd of ln X = (3.912023 - 0.693147) / (2 * 1.6448536) = 3.218876 / 3.2897073 = 0.978469.
    mu, sd = c.mod.lognormal_params(2, 50)
    expect(near(mu, 2.302585, 1e-6) and near(sd, 0.978469, 1e-6), "lognormal_params(2, 50) gave %r, %r" % (mu, sd))
    s = {"dist": "lognormal", "low": 2, "high": 50}
    # 5th percentile = exp(2.302585 - 1.6448536 * 0.978469) = exp(0.693147) = 2; 95th = 50; median = 10.
    for u, want in ((0.05, 2.0), (0.5, 10.0), (0.95, 50.0)):
        expect(near(c.mod.quantile(s, u), want, 1e-9 * want), "lognormal quantile(%g) is %r, expected %g" % (u, c.mod.quantile(s, u), want))
    m = base_model(inputs={"a": dict(s, why="a positive multiplicative quantity")}, runs=20000)
    out, _, _ = c.mod.simulate(m, c.mod.check_model(m)[2])
    # One draw in twenty lies STRICTLY below low and one in twenty strictly above high. A copy that
    # treats low and high as the minimum and maximum puts almost none there.
    # Tolerance as in the normal test: four standard errors = 0.0062.
    below = sum(1 for x in out if x < 2) / len(out)
    above = sum(1 for x in out if x > 50) / len(out)
    expect(near(below, 0.05, 0.0062) and near(above, 0.05, 0.0062),
           "shares of draws below low and above high are %.4f and %.4f; each must be 0.05 because low and high are the 5th and 95th percentiles" % (below, above))


def test_product_of_two_lognormals_matches_the_analytic_result(c):
    # X: low 2, high 50  -> ln X normal, mean ln 10, sd 0.978469 (worked in the test above).
    # Y: low 1, high 4   -> mean of ln Y = (0 + 1.386294) / 2 = 0.693147 = ln 2; sd = 1.386294 / 3.2897073 = 0.421404.
    # A product of independent lognormals is lognormal: ln(XY) has mean ln 10 + ln 2 = ln 20 and
    # sd = sqrt(0.978469^2 + 0.421404^2) = sqrt(0.957402 + 0.177581) = sqrt(1.134983) = 1.065356.
    # Median = 20. 95th percentile = 20 * exp(1.6448536 * 1.065356) = 20 * exp(1.752355) = 20 * 5.76816 = 115.363.
    # 5th percentile = 20 / 5.76816 = 3.46731.
    n = 200000
    m = base_model(inputs={"x": {"dist": "lognormal", "low": 2, "high": 50, "why": "wide positive factor"},
                           "y": {"dist": "lognormal", "low": 1, "high": 4, "why": "narrow positive factor"}},
                   formula="x * y", runs=n, seed=11)
    out, _, _ = c.mod.simulate(m, c.mod.check_model(m)[2])
    xs = sorted(out)
    s = 1.065356
    # Simulation error, in log units. Sample median: 1.2533 * s / sqrt(n) = 1.2533 * 1.065356 / 447.214 = 0.002986.
    # Sample 5th or 95th percentile: sqrt(0.05 * 0.95 / n) * s / phi(1.6449), phi(1.6449) = 0.103136,
    # = 0.00048734 * 1.065356 / 0.103136 = 0.005034. Allow four standard errors each.
    se_med = 1.2533 * s / math.sqrt(n)
    se_tail = math.sqrt(0.05 * 0.95 / n) * s / 0.103136
    for p, want, se in ((0.5, 20.0, se_med), (0.95, 115.363, se_tail), (0.05, 3.46731, se_tail)):
        got = c.mod.percentile(xs, p)
        expect(abs(math.log(got) - math.log(want)) <= 4 * se,
               "percentile %g of the product is %.4f, analytic %.4f, outside four standard errors (%.4f in log units)" % (p, got, want, 4 * se))


def test_uniform_triangular_and_choice_quantiles(c):
    q = c.mod.quantile
    # uniform 0.05..0.3: quantile(u) = 0.05 + u * 0.25. u = 0.5 -> 0.175; u = 0.05 -> 0.0625.
    u = {"dist": "uniform", "low": 0.05, "high": 0.3}
    expect(near(q(u, 0.5), 0.175, 1e-12) and near(q(u, 0.05), 0.0625, 1e-12), "uniform quantiles wrong")
    # triangular low 0, mode 2, high 10. Share below the mode = (2 - 0) / (10 - 0) = 0.2.
    # u = 0.1 (below): 0 + sqrt(0.1 * 10 * 2) = sqrt(2) = 1.414214.
    # u = 0.6 (above): 10 - sqrt(0.4 * 10 * 8) = 10 - sqrt(32) = 10 - 5.656854 = 4.343146.
    t = {"dist": "triangular", "low": 0, "mode": 2, "high": 10}
    expect(near(q(t, 0.1), 1.414214, 1e-6) and near(q(t, 0.6), 4.343146, 1e-6) and near(q(t, 0.2), 2.0, 1e-9), "triangular quantiles wrong")
    # choice values 3, 1, 2 with weights 2, 1, 1: sorted 1 (0.25), 2 (0.25), 3 (0.5); cumulative 0.25, 0.5, 1.
    ch = {"dist": "choice", "values": [3, 1, 2], "weights": [2, 1, 1]}
    expect(q(ch, 0.2) == 1.0 and q(ch, 0.5) == 2.0 and q(ch, 0.51) == 3.0 and q(ch, 0.999) == 3.0, "choice quantiles wrong")
    m = base_model(inputs={"a": dict(ch, why="three discrete cases for this test")}, runs=20000)
    out, _, _ = c.mod.simulate(m, c.mod.check_model(m)[2])
    # Half the draws should be 3. Four standard errors: 4 * sqrt(0.5 * 0.5 / 20000) = 0.0141.
    share3 = sum(1 for x in out if x == 3.0) / len(out)
    expect(near(share3, 0.5, 0.0141) and set(out) == {1.0, 2.0, 3.0}, "choice draws: share of 3 is %.4f, values %r" % (share3, sorted(set(out))))


# ---------------------------------------------------------------- arithmetic helpers

def test_percentile_function(c):
    # xs = 1..5 (n = 5). Position = (n - 1) * p.
    # p 0.5 -> position 2.0 -> 3.  p 0.25 -> position 1.0 -> 2.
    # p 0.95 -> position 3.8 -> 4 + 0.8 * (5 - 4) = 4.8.  p 0.05 -> position 0.2 -> 1.2.
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    for p, want in ((0.5, 3.0), (0.25, 2.0), (0.95, 4.8), (0.05, 1.2), (0.0, 1.0), (1.0, 5.0)):
        expect(near(c.mod.percentile(xs, p), want, 1e-12), "percentile(%g) is %r, expected %g" % (p, c.mod.percentile(xs, p), want))


def test_spearman_hand_worked(c):
    # No ties: x = 1 2 3 4 5, y = 2 1 4 3 5. Rank differences -1 1 -1 1 0, squares sum to 4.
    # rho = 1 - 6 * 4 / (5 * (25 - 1)) = 1 - 24 / 120 = 0.8.
    expect(near(c.mod.spearman([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]), 0.8, 1e-12), "spearman without ties is wrong")
    # Ties: x = 1 2 2 3 -> ranks 1, 2.5, 2.5, 4. y = 1 2 3 4 -> ranks 1 2 3 4. Both rank means are 2.5.
    # Deviations x: -1.5, 0, 0, 1.5. y: -1.5, -0.5, 0.5, 1.5.
    # Sum of products = 2.25 + 0 + 0 + 2.25 = 4.5. Sum of squares x = 4.5, y = 5.
    # rho = 4.5 / sqrt(4.5 * 5) = 4.5 / 4.743416 = 0.948683.
    expect(c.mod.average_ranks([1, 2, 2, 3]) == [1.0, 2.5, 2.5, 4.0], "average ranks with a tie are wrong")
    expect(near(c.mod.spearman([1, 2, 2, 3], [1, 2, 3, 4]), 0.948683, 1e-6), "spearman with ties is wrong")
    expect(near(c.mod.spearman([1, 2, 3], [3, 2, 1]), -1.0, 1e-12), "a perfectly reversed order must give -1")
    expect(c.mod.spearman([1, 1, 1], [1, 2, 3]) is None, "a constant input has no rank correlation and must give None")


def test_rounding_never_adds_precision(c):
    rs, ff = c.mod.round_sig, c.mod.figures_for
    # 237.4 to one figure is 200, to two is 240. 0.05477 to two is 0.055. 0.0949 to one is 0.09.
    expect(rs(237.4, 1) == 200.0 and rs(237.4, 2) == 240.0 and rs(0.05477, 2) == 0.055 and rs(0.0949, 1) == 0.09, "round_sig is wrong")
    # Two figures while the high end is at most one hundred times the low end, one figure beyond that.
    # 3 to 300 is exactly a factor of one hundred (two figures); 3 to 303 is just over (one figure).
    expect(ff(3, 20) == 2 and ff(3, 300) == 2 and ff(3, 303) == 1 and ff(1, 1000) == 1 and ff(-300, -3) == 2 and ff(-5, 5) == 2, "figures_for is wrong")
    for inputs in ({"a": {"dist": "lognormal", "low": 3.137, "high": 91.44, "why": "a wide range typed with spare digits"}},
                   {"a": {"dist": "lognormal", "low": 3.137, "high": 9144.7, "why": "a very wide range typed with spare digits"}},
                   {"a": {"dist": "normal", "low": 101.37, "high": 133.91, "why": "a narrow range typed with spare digits"}}):
        code, out, _ = c.cli(c.write(base_model(inputs=inputs, runs=5000)), "--json")
        r = json.loads(out)["result"]
        sig = r["significant_figures"]
        vals = list(r["percentiles"].values()) + [r["mean"], r["all_inputs_at_median"]]
        expect(code == 0 and all(v == rs(v, sig) for v in vals), "a printed figure carries more than %d significant figures: %r" % (sig, vals))
        expect(sig == (1 if inputs["a"]["high"] > 9000 else 2), "wrong number of significant figures (%d) for %r" % (sig, inputs))
        swings = [x for s in r["sensitivity"] for x in (s["result_at_input_5th"], s["result_at_input_95th"], s["swing_factor"])]
        expect(all(v == rs(v, 2) for v in swings), "a sensitivity figure carries more than two significant figures: %r" % swings)
    # A narrow input range still prints a median that lies between its own bounds.
    narrow = {"dist": "uniform", "low": 1.03, "high": 1.10, "why": "a narrow range for this test"}
    expect("median 1.06" in c.mod.describe_input("g", narrow) or "median 1.07" in c.mod.describe_input("g", narrow), "narrow input median printed badly: %r" % c.mod.describe_input("g", narrow))


# ---------------------------------------------------------------- the formula parser

def test_parser_precedence(c):
    env = {"a": 6.0, "b": 3.0}
    cases = (("2 + 3 * 4", 14.0),            # multiplication before addition
             ("(2 + 3) * 4", 20.0),
             ("2 ** 3 ** 2", 512.0),         # right associative: 2 ** 9
             ("-2 ** 2", -4.0),              # power binds tighter than the minus: -(2 ** 2)
             ("2 ** -1", 0.5),
             ("8 / 4 / 2", 1.0),             # left associative: (8 / 4) / 2
             ("10 - 4 - 3", 3.0),            # left associative: (10 - 4) - 3
             ("2 * 3 ** 2", 18.0),
             ("a / b + 1", 3.0),             # 6 / 3 + 1
             ("a - -b", 9.0),
             ("min(3, 1, 2) + max(a, 2 * b + 1)", 8.0),   # 1 + max(6, 7)
             ("1e3 * 2", 2000.0), (".5 + 1.", 1.5), ("2.5E-1 * 4", 1.0),
             ("+a", 6.0), ("((a))", 6.0), ("  a\t*\nb ", 18.0))
    for text, want in cases:
        tree, _ = c.mod.parse_formula(text, ["a", "b"])
        got = c.mod.evaluate(tree, env)
        expect(near(got, want, 1e-12), "%r evaluated to %r, expected %r" % (text, got, want))
    _, used = c.mod.parse_formula("a * 2", ["a", "b"])
    expect(used == {"a"}, "the parser must report which names the formula uses")


def test_parser_refusals(c):
    bad = ("", "   ", "a +", "* a", "(a", "a)", "a b", "a 2", "2a", "1_000", "a // b", "a % b", "a ^ b", "a, b", "min(a)", "min a",
           "max", "abs(a)", "a.real", "a[0]", "a; b", "a if b else a", "lambda: 1", "'x'", "\"x\"", "a == b", "a < b", "a = 2",
           "z * a", "_a", "a__b__ * q", "2 ** ", "min(a, )", "a ** ** b", "$a", "a\\b", "{a}", "a @ b", "a & b", "~a", "!a")
    for text in bad:
        try:
            c.mod.parse_formula(text, ["a", "b"])
        except c.mod.FormulaError:
            continue
        raise AssertionError("the parser accepted %r" % text)
    # valid neighbours of the refusals above
    for text in ("a + b", "(a)", "a * 2", "2 * a", "1000 * a", "a / b", "min(a, b)", "max(a, b, 1)", "a ** b"):
        c.mod.parse_formula(text, ["a", "b"])
    deep = "(" * 200 + "a" + ")" * 200
    try:
        c.mod.parse_formula(deep, ["a"])
        raise AssertionError("200 nested parentheses were accepted")
    except c.mod.FormulaError:
        pass
    c.mod.parse_formula("(" * 20 + "a" + ")" * 20, ["a"])
    try:
        c.mod.parse_formula("a + " * 600 + "a", ["a"])
        raise AssertionError("a formula over the length limit was accepted")
    except c.mod.FormulaError:
        pass
    # 200 names joined by 199 plus signs is 399 symbols (allowed, and sums to 200); 201 names is 401 (refused).
    tree, _ = c.mod.parse_formula("+".join(["a"] * 200), ["a"])
    expect(c.mod.evaluate(tree, {"a": 1.0}) == 200.0, "a 399-symbol sum is wrong")
    try:
        c.mod.parse_formula("+".join(["a"] * 201), ["a"])
        raise AssertionError("a formula of 401 symbols was accepted")
    except c.mod.FormulaError:
        pass


def test_parser_never_crashes_on_random_text(c):
    # 4,000 random strings, fixed seed: half from the pieces of valid formulas, half with junk mixed in. Each must
    # either parse and evaluate to a finite number or raise FormulaError. Any other exception is a failure.
    import random
    rng = random.Random(20261009)
    clean = ["a", "b", "1", "2", ".5", "1e3", "+", "-", "*", "/", "**", "(", ")", ",", "min(", "max(", " "]
    junk = clean + ["_", "x", "'", "[", "]", ".", "e", "0", "%", "=", ";", "__import__", "\\", "\n"]
    ok = refused = 0
    for i in range(4000):
        pieces = clean if i % 2 == 0 else junk
        text = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 9)))
        try:
            tree, _used = c.mod.parse_formula(text, ["a", "b"])
            v = c.mod.evaluate(tree, {"a": 3.0, "b": 0.5})
            expect(isinstance(v, float) and math.isfinite(v), "%r evaluated to %r" % (text, v))
            ok += 1
        except c.mod.FormulaError:
            refused += 1
    # The counts below only confirm the generator reached both outcomes often; they are not a property of the script.
    expect(ok >= 200 and refused >= 1000, "the random formulas did not exercise both paths: %d accepted, %d refused" % (ok, refused))


def test_parser_refuses_code_like_text(c):
    # None of these may run. Each is harmless if it does, and each must be refused with exit 1.
    for text in ("__import__('math').pi * a", "__import__(\"os\").getcwd() and a", "a.__class__", "(lambda: a)()", "[a][0]",
                 "a if a else a", "abs(a)", "exec('1')", "open('x')", "a; a", "eval('a')", "a and a", "not a"):
        code, out, err = c.cli(c.write(base_model(formula=text)))
        expect(code == 1 and "ERROR" in out and "formula" in out and "RESULT: REFUSED" in out,
               "formula %r was not refused: exit %d, output %r" % (text, code, (out + err)[:200]))
        expect("Traceback" not in out + err, "formula %r produced a traceback" % text)
    code, out, _ = c.cli(c.write(base_model(formula="max(a, 2) * 1")))
    expect(code == 0 and "RESULT: RAN" in out, "the valid neighbour max(a, 2) * 1 was refused")
    # Source check: no call to Python's own evaluators anywhere after the module docstring.
    # (re.compile is a regular expression, not code, and is excluded by the look-behind for a dot.)
    import re
    src = c.script.read_text(encoding="utf-8").split('"""', 2)[2]
    calls = re.findall(r"(?<![\w.])(?:ev" + r"al|ex" + r"ec|compile|__import__)\s*\(", src)
    expect(not calls, "the script body calls %r; the formula must only ever go through the parser" % calls)


def test_runtime_arithmetic_failures_are_refused(c):
    code, out, _ = c.cli(c.write(base_model(formula="1 / (a - a)")))
    expect(code == 1 and "division by zero" in out and "run 1 of" in out, "division by zero was not refused: %r" % out[:200])
    code, out, _ = c.cli(c.write(base_model(formula="(0 - a) ** 0.5")))
    expect(code == 1 and "no finite real answer" in out, "a negative number to a fractional power was not refused: %r" % out[:200])
    code, out, _ = c.cli(c.write(base_model(formula="10 ** (a * 400)")))
    expect(code == 1 and "REFUSED" in out, "an overflow was not refused")
    code, out, _ = c.cli(c.write(base_model(formula="1 / a")))
    expect(code == 0, "the valid neighbour 1 / a was refused")


# ---------------------------------------------------------------- whole models

def test_fixed_only_model_is_exact_arithmetic(c):
    # 26000 * 0.1 * 0.25 = 2600 * 0.25 = 650.   (3 + 4) * 2 ** 3 / 7 = 7 * 8 / 7 = 8.
    m = base_model(unit="customers", formula="households * share * reach",
                   inputs={"households": {"dist": "fixed", "value": 26000, "source": "SYNTHETIC table"},
                           "share": {"dist": "fixed", "value": 0.1, "source": "SYNTHETIC survey"},
                           "reach": {"dist": "fixed", "value": 0.25, "source": "SYNTHETIC records"}})
    code, out, _ = c.cli(c.write(m), "--json")
    r = json.loads(out)
    expect(code == 0 and r["result"]["exact"] is True and set(r["result"]["percentiles"].values()) == {650.0}, "fixed-only model did not give 650 exactly: %r" % r["result"])
    expect(any("arithmetic" in a for a in r["advisories"]), "a fixed-only model must be labelled as arithmetic, not an estimate")
    code, out, _ = c.cli(c.write(m))
    expect("650 customers exactly" in out and "SENSITIVITY" not in out, "text output for a fixed-only model is wrong: %r" % out[:300])
    m2 = base_model(formula="(a + 4) * 2 ** a / 7", inputs={"a": {"dist": "fixed", "value": 3, "source": "SYNTHETIC"}})
    code, out, _ = c.cli(c.write(m2), "--json")
    expect(json.loads(out)["result"]["percentiles"]["50"] == 8.0, "(3 + 4) * 2 ** 3 / 7 should be 8")
    # 123456789 * 3 = 370370367: a fixed-only answer is not rounded to two figures.
    m3 = base_model(formula="a * 3", inputs={"a": {"dist": "fixed", "value": 123456789, "source": "SYNTHETIC"}})
    code, out, _ = c.cli(c.write(m3))
    expect("370,370,367 things exactly" in out, "a fixed-only answer was rounded: %r" % out[:300])


def test_seed_reproducibility(c):
    m = base_model(inputs={"a": {"dist": "lognormal", "low": 2, "high": 50, "why": "wide positive factor"},
                           "b": {"dist": "triangular", "low": 1, "mode": 2, "high": 6, "why": "most likely two, at most six"}},
                   formula="a * b", runs=5000, seed=42)
    p = c.write(m)
    before = p.read_bytes()
    one, two = c.cli(p, "--json"), c.cli(p, "--json")
    expect(one[0] == 0 and one[1] == two[1], "the same model and seed gave different output")
    expect(p.read_bytes() == before, "the model file was modified")
    tree = c.mod.check_model(m)[2]
    out_a, _, _ = c.mod.simulate(m, tree)
    out_b, _, _ = c.mod.simulate(dict(m), tree)
    out_c, _, _ = c.mod.simulate(dict(m, seed=43), tree)
    expect(out_a == out_b, "simulate is not reproducible for one seed")
    expect(out_a != out_c, "a different seed gave identical draws")
    # The first draw is fixed by the definition: random.Random(42).random() through the inverse
    # distribution function, input a first. Recompute it here without the script's sampler.
    import random
    import statistics
    u = random.Random(42).random()
    first_a = math.exp((math.log(2) + math.log(50)) / 2 + (math.log(50) - math.log(2)) / (2 * Z) * statistics.NormalDist().inv_cdf(u))
    _, draws, _ = c.mod.simulate(m, tree)
    expect(near(draws["a"][0], first_a, 1e-9 * first_a), "the first draw of a is %r, expected %r from the documented method" % (draws["a"][0], first_a))


def test_refusals_and_their_valid_neighbours(c):
    def run(model):
        code, out, _ = c.cli(c.write(model), "--json")
        return code, json.loads(out)["errors"]

    def pair(refused, allowed, needle):
        code, errs = run(refused)
        expect(code == 1 and any(needle in e for e in errs), "expected a refusal mentioning %r, got exit %d %r" % (needle, code, errs))
        code, errs = run(allowed)
        expect(code == 0 and not errs, "the valid neighbour was refused: %r" % errs)

    why = "reasoning for this test range"
    pair(base_model(runs=999), base_model(runs=1000), "runs must be")
    pair(base_model(runs=1000001), base_model(runs=1000000, formula="a"), "runs must be")
    pair(base_model(runs=2000.0), base_model(runs=2000), "runs must be")
    pair(base_model(seed=1.5), base_model(seed=0), "seed must be")
    pair(base_model(seed=True), base_model(seed=-3), "seed must be")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": 3, "high": 3, "why": why}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 3, "high": 3.0001, "why": why}}), "must be below high")
    pair(base_model(inputs={"a": {"dist": "normal", "low": 5, "high": 4, "why": why}}),
         base_model(inputs={"a": {"dist": "normal", "low": 4, "high": 5, "why": why}}), "must be below high")
    pair(base_model(inputs={"a": {"dist": "lognormal", "low": 0, "high": 4, "why": why}}),
         base_model(inputs={"a": {"dist": "lognormal", "low": 1e-9, "high": 4, "why": why}}), "low above zero")
    pair(base_model(inputs={"a": {"dist": "lognormal", "low": -1, "high": 4, "why": why}}),
         base_model(inputs={"a": {"dist": "normal", "low": -1, "high": 4, "why": why}}), "low above zero")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": 0.2, "high": 1.0001, "kind": "probability", "why": why}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 0.2, "high": 1, "kind": "probability", "why": why}}), "outside 0 to 1")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": -0.0001, "high": 0.5, "kind": "probability", "why": why}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 0, "high": 0.5, "kind": "probability", "why": why}}), "outside 0 to 1")
    pair(base_model(inputs={"a": {"dist": "fixed", "value": 1.2, "kind": "probability", "source": "SYNTHETIC"}}),
         base_model(inputs={"a": {"dist": "fixed", "value": 1, "kind": "probability", "source": "SYNTHETIC"}}), "outside 0 to 1")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why}}), "needs a why")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": "guess"}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": "ten chars."}}), "needs a why")
    pair(base_model(inputs={"a": {"dist": "fixed", "value": 3}}),
         base_model(inputs={"a": {"dist": "fixed", "value": 3, "source": "SYNTHETIC table"}}), "needs a source")
    pair(base_model(inputs={"a": {"dist": "fixed", "value": 3, "source": "SYNTHETIC", "as_of": "20261009"}}),
         base_model(inputs={"a": {"dist": "fixed", "value": 3, "source": "SYNTHETIC", "as_of": "2026-10-09"}}), "real date")
    pair(base_model(inputs={"a": {"dist": "fixed", "value": 3, "source": "SYNTHETIC", "as_of": "2026-02-30"}}),
         base_model(inputs={"a": {"dist": "fixed", "value": 3, "source": "SYNTHETIC", "as_of": "2026-02-28"}}), "real date")
    pair(base_model(inputs={"a": {"dist": "triangular", "low": 1, "mode": 3.01, "high": 3, "why": why}}),
         base_model(inputs={"a": {"dist": "triangular", "low": 1, "mode": 3, "high": 3, "why": why}}), "mode between")
    pair(base_model(inputs={"a": {"dist": "choice", "values": [1, 2], "weights": [1, 0], "why": why}}),
         base_model(inputs={"a": {"dist": "choice", "values": [1, 2], "weights": [1, 0.001], "why": why}}), "weights must be")
    pair(base_model(inputs={"a": {"dist": "choice", "values": [1], "weights": [1], "why": why}}),
         base_model(inputs={"a": {"dist": "choice", "values": [1, 1], "weights": [1, 1], "why": why}}), "at least two numbers")
    pair(base_model(inputs={"a": {"dist": "beta", "low": 1, "high": 3, "why": why}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why}}), "is not one of")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": "1", "high": 3, "why": why}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why}}), "must both be numbers")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": True, "high": 3, "why": why}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why}}), "must both be numbers")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why, "hihg": 4}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why, "note": "kept"}}), "unknown key")
    pair(base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why}, "b": {"dist": "fixed", "value": 2, "source": "SYNTHETIC"}}),
         base_model(inputs={"a": {"dist": "uniform", "low": 1, "high": 3, "why": why}, "b": {"dist": "fixed", "value": 2, "source": "SYNTHETIC"}}, formula="a * b"),
         "never uses it")
    pair(base_model(formula="a * c"), base_model(formula="a * 2"), "unknown name")
    pair(base_model(inputs={"min": {"dist": "uniform", "low": 1, "high": 3, "why": why}}, formula="min"),
         base_model(inputs={"minimum": {"dist": "uniform", "low": 1, "high": 3, "why": why}}, formula="minimum"), "input name")
    pair(base_model(inputs={"_a": {"dist": "uniform", "low": 1, "high": 3, "why": why}}, formula="_a"),
         base_model(inputs={"a_1": {"dist": "uniform", "low": 1, "high": 3, "why": why}}, formula="a_1"), "input name")
    pair(base_model(colour="red"), base_model(notes="kept"), "unknown key")
    pair(base_model(unit=""), base_model(unit="km"), "unit is missing")
    pair(base_model(anchors=[{"name": "cap"}]), base_model(anchors=[{"name": "cap", "max": 3}]), "needs a max or a min")
    code, out, _ = c.cli(c.write(base_model(runs=999)))
    expect(code == 1 and "Nothing was simulated" in out and "median" not in out, "a refused model still printed a result")


def test_anchor_breach_counts(c):
    # x is uniform on 0..10 and the anchor says it cannot exceed 9. One tenth of runs breach it.
    # Four standard errors of that share at 20,000 runs: 4 * sqrt(0.1 * 0.9 / 20000) = 0.0085.
    # The 95th percentile of x is 9.5, above the anchor, so the advisory must appear.
    m = base_model(inputs={"a": {"dist": "uniform", "low": 0, "high": 10, "why": "bounds are known for this test"}}, runs=20000,
                   anchors=[{"name": "cap of nine", "max": 9}, {"name": "floor of one", "min": 1}])
    code, out, _ = c.cli(c.write(m), "--json")
    r = json.loads(out)
    a = r["result"]["anchors"]
    expect(code == 0 and near(a[0]["runs_above_max"] / 20000.0, 0.1, 0.0085) and near(a[1]["runs_below_min"] / 20000.0, 0.1, 0.0085),
           "anchor breach counts are wrong: %r" % a)
    expect(a[0]["runs"] == 20000, "the denominator must travel with the count")
    expect(sum(1 for x in r["advisories"] if "reaches past the anchor" in x) == 2, "both breached anchors must be reported: %r" % r["advisories"])
    m["anchors"] = [{"name": "cap of ten", "max": 10}, {"name": "floor of zero", "min": 0}]
    code, out, _ = c.cli(c.write(m), "--json")
    r = json.loads(out)
    expect(r["result"]["anchors"][0]["runs_above_max"] == 0 and not any("anchor" in x for x in r["advisories"]), "an anchor at the bound was reported as breached")
    code, out, _ = c.cli(c.write(m))
    expect("0 of 20,000 runs" in out, "anchor counts must be printed with their denominator: %r" % out)


def test_probability_draws_are_clipped_and_reported(c):
    # lognormal with 5th and 95th percentiles 0.3 and 0.9, declared a probability.
    # mean of ln X = (ln 0.3 + ln 0.9) / 2 = (-1.203973 - 0.105361) / 2 = -0.654667.
    # sd = (ln 0.9 - ln 0.3) / 3.2897073 = 1.098612 / 3.2897073 = 0.333954.
    # P(X > 1) = P(Z > 0.654667 / 0.333954) = P(Z > 1.96035) = 0.02498.
    # At 20,000 runs that is about 500 draws; four standard errors of the share = 4 * sqrt(0.025 * 0.975 / 20000) = 0.0044.
    m = base_model(inputs={"a": {"dist": "lognormal", "low": 0.3, "high": 0.9, "kind": "probability", "why": "a share that is probably high"}}, runs=20000)
    code, out, _ = c.cli(c.write(m), "--json")
    r = json.loads(out)
    clipped = r["result"]["clipped"].get("a", 0)
    expect(code == 0 and near(clipped / 20000.0, 0.02498, 0.0044), "clipped draws: %d of 20000, expected about 500" % clipped)
    expect(any("set to the bound" in x and "of 20,000 runs" in x for x in r["advisories"]), "clipping must be reported with its count: %r" % r["advisories"])
    outs, draws, _ = c.mod.simulate(m, c.mod.check_model(m)[2])
    expect(max(draws["a"]) == 1.0 and min(draws["a"]) > 0, "a probability draw left 0 to 1")


def test_sensitivity_ranks_the_wide_input_first(c):
    # wide: lognormal 1..100 (median 10). narrow: lognormal 9..11 (median sqrt(99) = 9.9499).
    # One at a time: wide at 1 and 100 with narrow at its median gives 9.95 and 995, a factor of 100.
    # narrow at 9 and 11 with wide at its median gives 90 and 110, a factor of 11 / 9 = 1.2222 -> 1.2.
    m = base_model(inputs={"narrow": {"dist": "lognormal", "low": 9, "high": 11, "why": "known to within ten percent"},
                           "wide": {"dist": "lognormal", "low": 1, "high": 100, "why": "could be anywhere over two orders"}},
                   formula="narrow * wide", runs=10000)
    code, out, _ = c.cli(c.write(m), "--json")
    s = json.loads(out)["result"]["sensitivity"]
    expect(code == 0 and [x["input"] for x in s] == ["wide", "narrow"], "sensitivity order is wrong: %r" % s)
    expect(s[0]["rank_correlation"] > 0.95 and abs(s[1]["rank_correlation"]) < 0.2, "rank correlations are wrong: %r" % s)
    expect(s[0]["swing_factor"] == 100.0 and s[1]["swing_factor"] == 1.2, "one-at-a-time swings are wrong: %r" % s)
    code, out, _ = c.cli(c.write(m))
    expect("Drives the spread most: wide" in out, "the text output must name the input that matters")


def test_wide_result_is_flagged(c):
    why = "a positive factor of uncertain size"
    wide = base_model(inputs={"a": {"dist": "lognormal", "low": 1, "high": 1000, "why": why}}, runs=5000)
    code, out, _ = c.cli(c.write(wide), "--json")
    expect(code == 0 and any("two orders of magnitude" in x for x in json.loads(out)["advisories"]), "a range of a factor of 1000 was not flagged")
    ok = base_model(inputs={"a": {"dist": "lognormal", "low": 1, "high": 50, "why": why}}, runs=5000)
    code, out, _ = c.cli(c.write(ok), "--json")
    expect(code == 0 and not any("orders of magnitude" in x for x in json.loads(out)["advisories"]), "a range of a factor of 50 was flagged")


def test_mean_is_never_printed_without_the_median(c):
    m = base_model(inputs={"a": {"dist": "lognormal", "low": 1, "high": 100, "why": "a positive factor of uncertain size"}}, runs=5000)
    code, out, _ = c.cli(c.write(m))
    lines = out.splitlines()
    i_med = next(i for i, l in enumerate(lines) if l.startswith("RESULT   median"))
    i_mean = next(i for i, l in enumerate(lines) if l.strip().startswith("mean "))
    expect(i_med < i_mean and "Quote the median and the range, not the mean" in lines[i_mean], "the mean must follow the median and carry its warning: %r" % lines[i_mean])


def test_compare_hand_worked(c):
    # A: 5th 100, median 300, 95th 1000.  B: 5th 500, median 1500, 95th 4000.
    # Overlap is 500 to 1000. On a log scale:
    #   share of A = ln(1000 / 500) / ln(1000 / 100) = 0.693147 / 2.302585 = 0.30103 -> 0.3
    #   share of B = ln(1000 / 500) / ln(4000 / 500) = 0.693147 / 2.079442 = 0.33333 -> 0.3
    # B's median is 1500 / 300 = 5 times A's. A's median 300 is outside B's range; B's 1500 is outside A's.
    def res(p5, p50, p95):
        return {"raw": {5: p5, 25: p5, 50: p50, 75: p95, 95: p95}, "result": {"exact": False}}
    out, adv = c.mod.compare(res(100.0, 300.0, 1000.0), res(500.0, 1500.0, 4000.0))
    expect(out["overlap"] is True and out["overlap_low"] == 500.0 and out["overlap_high"] == 1000.0, "overlap interval is wrong: %r" % out)
    expect(out["share_of_a"] == 0.3 and out["share_of_b"] == 0.3 and out["scale"] == "log", "overlap shares are wrong: %r" % out)
    expect(out["median_ratio_b_over_a"] == 5.0 and not out["a_median_inside_b"] and not out["b_median_inside_a"], "median comparison is wrong: %r" % out)
    # Each median is outside the other range, so the overlap is at the edges only and that is said: one advisory, and the flag is set.
    expect(out["edge_overlap_only"] is True and len(adv) == 1 and "only at their edges" in adv[0], "an overlap at the edges only must be flagged: %r %r" % (out, adv))
    # Valid neighbour: B 200..2000 with median 600 lies inside A's 100..1000, and A's 300 inside B's range: compatible, no advisory.
    out, adv = c.mod.compare(res(100.0, 300.0, 1000.0), res(200.0, 600.0, 2000.0))
    expect(out["overlap"] is True and out["edge_overlap_only"] is False and not adv, "two ranges with each median inside the other need no advisory: %r %r" % (out, adv))
    # No overlap: A 100..1000, B 3000..9000. The higher range starts 3000 / 1000 = 3 times above where the lower ends.
    out, adv = c.mod.compare(res(100.0, 300.0, 1000.0), res(3000.0, 5000.0, 9000.0))
    expect(out["overlap"] is False and out["gap_factor"] == 3.0 and len(adv) == 1 and "do not overlap" in adv[0], "non-overlap is wrong: %r %r" % (out, adv))
    # Touching ranges count as overlapping (the valid neighbour of the refusal above), and are the plainest case of an overlap at the edges only.
    out, adv = c.mod.compare(res(100.0, 300.0, 1000.0), res(1000.0, 5000.0, 9000.0))
    expect(out["overlap"] is True and out["gap_factor"] is None and len(adv) == 1 and "only at their edges" in adv[0], "ranges that touch must count as overlapping, at the edges only: %r %r" % (out, adv))
    # A range crossing zero is compared on a linear scale: A -10..10, B 0..40 overlap 0..10 = half of A, a quarter of B.
    out, adv = c.mod.compare(res(-10.0, 0.0, 10.0), res(0.0, 20.0, 40.0))
    expect(out["scale"] == "linear" and out["share_of_a"] == 0.5 and out["share_of_b"] in (0.2, 0.3), "linear overlap is wrong: %r" % out)


def test_compare_command(c):
    why = "a positive factor of uncertain size"
    a = base_model(inputs={"a": {"dist": "lognormal", "low": 100, "high": 1000, "why": why}}, runs=5000)
    b = base_model(inputs={"a": {"dist": "lognormal", "low": 400, "high": 4000, "why": why}}, runs=5000)
    far = base_model(inputs={"a": {"dist": "lognormal", "low": 5000, "high": 9000, "why": why}}, runs=5000)
    pa, pb, pf = c.write(a), c.write(b), c.write(far)
    code, out, _ = c.cli("--compare", pa, pb)
    expect(code == 0 and "The ranges overlap" in out and "RESULT: COMPARED" in out, "compare of overlapping models failed: %r" % out[-400:])
    # a: 100 to 1,000, median sqrt(100 * 1000) = 316. b: 400 to 4,000, median sqrt(400 * 4000) = 1,265. The ranges share 400 to 1,000,
    # yet 316 is below b's low of 400 and 1,265 is above a's high of 1,000: each median is outside the other range. That is an
    # overlap at the edges only, and it must not be called compatible.
    expect("each median is outside the other range" in out and "are compatible" not in out and "overlap only at their edges" in out,
           "an overlap at the edges only was called compatible: %r" % out[-500:])
    # Valid neighbour: c is 150 to 1,500, median 474, which lies inside a's 100 to 1,000; a's median 316 lies inside 150 to 1,500.
    near = base_model(inputs={"a": {"dist": "lognormal", "low": 150, "high": 1500, "why": why}}, runs=5000)
    code, out, _ = c.cli("--compare", pa, c.write(near))
    expect(code == 0 and "are compatible" in out and "overlap only at their edges" not in out, "two ranges with each median inside the other must be called compatible: %r" % out[-400:])
    code, out, _ = c.cli("--compare", pa, pb, "--json")
    expect(json.loads(out)["comparison"]["edge_overlap_only"] is True, "the JSON must carry edge_overlap_only")
    code, out, _ = c.cli("--compare", pa, pf)
    expect(code == 0 and "The ranges do NOT overlap" in out and "Do not average" in out and "are compatible" not in out, "text for disjoint ranges is wrong: %r" % out[-300:])
    code, out, _ = c.cli("--compare", pa, pf, "--json")
    j = json.loads(out)
    expect(code == 0 and j["comparison"]["overlap"] is False and any("do not overlap" in x for x in j["advisories"]), "compare of disjoint models is wrong: %r" % j["comparison"])
    code, out, _ = c.cli("--compare", pa, c.write(dict(b, unit="dollars")))
    expect(code == 1 and "different units" in out and "RESULT: REFUSED" in out, "comparing different units was not refused")
    code, out, _ = c.cli("--compare", pa, c.write(base_model(runs=10)))
    expect(code == 1 and "nothing was compared" in out, "comparing with an invalid model was not refused")
    code, out, err = c.cli("--compare", pa)
    expect(code == 2 and "expected 2 model files" in err and "Traceback" not in err, "--compare with one file must exit 2: %r" % err)


def test_bad_arguments_and_unreadable_input(c):
    good = c.write(base_model())
    code, out, err = c.cli(good, "--frobnicate")
    expect(code == 2 and "unknown option --frobnicate" in err and "Traceback" not in err and out == "", "an unknown option must exit 2 with one line: %r" % err)
    code, _, err = c.cli(c.tmp / "nope.json")
    expect(code == 2 and "cannot read" in err, "a missing file must exit 2")
    code, _, err = c.cli(c.write(None, raw=b'{"quantity": "caf\xe9"}'))
    expect(code == 2 and "not valid UTF-8" in err, "invalid UTF-8 must exit 2: %r" % err)
    code, _, err = c.cli(c.write(None, raw=b'{"quantity": "x\x00"}'))
    expect(code == 2 and "NUL" in err, "a NUL byte must exit 2: %r" % err)
    code, _, err = c.cli(c.write(None, raw=b'{"quantity": '))
    expect(code == 2 and "not valid JSON" in err, "malformed JSON must exit 2")
    code, _, err = c.cli(c.write(None, raw=json.dumps(base_model()).replace('"seed": 7', '"seed": NaN').encode()))
    expect(code == 2 and "not a JSON number" in err, "NaN must be refused: %r" % err)
    code, _, err = c.cli(c.write(None, raw=json.dumps(base_model()).replace('"low": 1', '"low": Infinity').encode()))
    expect(code == 2 and "not a JSON number" in err, "Infinity must be refused: %r" % err)
    dup = b'{"quantity": "Test", "unit": "u", "inputs": {"a": {"dist": "fixed", "value": 1, "source": "SYNTHETIC"}, "a": {"dist": "fixed", "value": 2, "source": "SYNTHETIC"}}, "formula": "a"}'
    code, _, err = c.cli(c.write(None, raw=dup))
    expect(code == 2 and "appears twice" in err, "a duplicated input name must be refused: %r" % err)
    code, out, _ = c.cli(c.write(None, raw=b"\xef\xbb\xbf" + json.dumps(base_model()).encode()))
    expect(code == 0, "a UTF-8 byte-order mark must be accepted")
    code, out, _ = c.cli(c.write([1, 2]))
    expect(code == 1 and "one JSON object" in out, "a JSON list must be refused as a model")
    code, out, err = c.cli()
    expect(code == 2, "no arguments must exit 2")


def test_output_is_ascii_and_standard_json(c):
    m = base_model(quantity="Caf" + chr(0xe9) + " visits " + chr(0x2014) + " weekly", unit="visits")
    p = c.write(None, raw=json.dumps(m, ensure_ascii=False).encode("utf-8"))
    for args in ((p,), (p, "--json")):
        code, out, _ = c.cli(*args)
        expect(code == 0 and all(ord(ch) < 128 for ch in out), "output is not plain ASCII")
    def refuse(x):
        raise ValueError(x)
    json.loads(c.cli(p, "--json")[1], parse_constant=refuse)


def test_model_template_in_assets(c):
    # The template handed to users is refused until its REPLACE text is filled in, and for no other reason.
    template = HERE.parent / "assets" / "model-template.json"
    code, out, _ = c.cli(template, "--json")
    errs = json.loads(out)["errors"]
    expect(code == 1 and len(errs) == 8 and all("REPLACE" in e for e in errs), "the untouched template should be refused only for its 8 REPLACE texts: %r" % errs)
    filled = json.loads(template.read_text(encoding="utf-8").replace("REPLACE", "Filled in"))
    code, out, _ = c.cli(c.write(filled), "--json")
    r = json.loads(out)
    # households 26,000 x lognormal share (median sqrt(0.02 * 0.15) = 0.05477) x uniform reach (median 0.175):
    # every input at its median gives 26000 * 0.05477 * 0.175 = 249.2 -> 250 to two figures.
    expect(code == 0 and not r["errors"] and r["result"]["all_inputs_at_median"] == 250.0, "the filled-in template did not run as documented: %r" % (r["errors"] or r["result"]["all_inputs_at_median"]))


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

# Broken copies of the script. Each replaces text that must occur exactly once in fermi.py, and names
# the test that has to catch it.
PLANTED = [
    {"name": "two ranges that only touch at their edges called compatible",
     "caught_by": "test_compare_command",
     "edits": [("        if not out[\"a_median_inside_b\"] and not out[\"b_median_inside_a\"]:\n", "        if False:\n")]},
    {"name": "lognormal low and high treated as minimum and maximum (three sd either side)",
     "caught_by": "test_lognormal_low_high_are_5th_and_95th_percentiles",
     "edits": [("    sigma = (math.log(high) - math.log(low)) / (2.0 * Z90)\n    return mu, sigma\n",
                "    sigma = (math.log(high) - math.log(low)) / 6.0\n    return mu, sigma\n")]},
    {"name": "lognormal draws clamped into low..high (bounds treated as hard limits)",
     "caught_by": "test_lognormal_low_high_are_5th_and_95th_percentiles",
     "edits": [("        return math.exp(mu + sigma * ND.inv_cdf(u))\n",
                "        return min(spec[\"high\"], max(spec[\"low\"], math.exp(mu + sigma * ND.inv_cdf(u))))\n")]},
    {"name": "formula handed to Python instead of the parser (accepts __import__)",
     "caught_by": "test_parser_refuses_code_like_text",
     "edits": [("    tokens = tokenise(text)\n    p = Parser(tokens, set(names))\n",
                "    return (\"py\", text), set(names)\n    tokens = tokenise(text)\n    p = Parser(tokens, set(names))\n"),
               ("    kind = node[0]\n    if kind == \"num\":\n",
                "    kind = node[0]\n    if kind == \"py\":\n        return float(ev" + "al(node[1], {}, dict(env)))\n    if kind == \"num\":\n")]},
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
                results[t.__name__] = "%s: %s" % (type(e).__name__, str(e)[:300])
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
        d = Path(tempfile.mkdtemp(prefix="fermi_planted_"))
        try:
            broken = d / "fermi.py"
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
    script, only, planted, it = HERE / "fermi.py", None, False, iter(argv)
    for a in it:
        if a == "--planted":
            planted = True
        elif a in ("--script", "--only"):
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_fermi: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--script":
                script = Path(v)
            else:
                only = v
        else:
            print("test_fermi: unknown argument " + a, file=sys.stderr)
            return 2
    if not Path(script).is_file():
        print("test_fermi: cannot find the script %s" % script, file=sys.stderr)
        return 2
    if only and only not in [t.__name__ for t in TESTS]:
        print("test_fermi: no test is called %s" % only, file=sys.stderr)
        return 2
    if planted:
        return run_planted(script)
    results = run_suite(script, only)
    failed = [n for n, msg in results.items() if msg is not None]
    print("RESULT: %d of %d tests passed%s" % (len(results) - len(failed), len(results), "" if not failed else "; FAILED: " + ", ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
