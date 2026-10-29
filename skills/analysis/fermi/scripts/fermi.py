#!/usr/bin/env python3
"""Order-of-magnitude estimate from a model of factors with ranges. Standard library only.

Usage:
  python fermi.py MODEL.json [--json]
  python fermi.py --compare MODEL_A.json MODEL_B.json [--json]

MODEL.json (one JSON object):
  {"quantity": "Paying customers reachable in year one", "unit": "customers",
   "timeframe": "first twelve months", "scope": "one town",        both optional, advised
   "inputs": {
     "households": {"dist": "fixed", "value": 26000, "source": "census table, 2021", "as_of": "2021-08-10"},
     "share":      {"dist": "lognormal", "low": 0.02, "high": 0.15, "kind": "probability", "why": "..."},
     "reach":      {"dist": "uniform", "low": 0.05, "high": 0.3, "why": "..."}},
   "formula": "households * share * reach",
   "anchors": [{"name": "cannot exceed households", "max": 26000}],
   "runs": 20000, "seed": 1}

Distributions and what low and high mean in each (this is the definition the script uses):
  fixed       value. A looked-up fact. Needs "source"; "as_of" is optional, a real date YYYY-MM-DD.
  normal      low and high are the 5th and 95th percentiles (a 90 percent interval).
              mean = (low + high) / 2, sd = (high - low) / (2 * z), z = 1.6448536 (the standard
              normal 95th percentile).
  lognormal   low and high are the 5th and 95th percentiles, both above zero.
              ln X is normal with mean (ln low + ln high) / 2 and sd (ln high - ln low) / (2 * z),
              so the median is sqrt(low * high). low and high are NOT a minimum and maximum:
              one draw in twenty falls below low and one in twenty above high.
  uniform     low and high are hard bounds. Nothing falls outside them.
  triangular  low and high are hard bounds, "mode" is the most likely value.
  choice      "values" with "weights" (any positive numbers; they are scaled to add to 1).
  Every input that is not fixed needs "why": the reasoning for its range.
  "kind": "probability" declares a share between 0 and 1; bounds outside 0 to 1 are refused.

Formula: numbers, input names, + - * / ** and parentheses, min(...) and max(...). It is read by a
small parser in this file. Nothing in the model is ever evaluated as code.

Method: every draw is made from Python's random.random() through the inverse distribution
function. random.random() is the generator Python documents as giving the same sequence for the
same seed across versions, so a model and seed should reproduce on any Python 3.8+ (only 3.13 was
run by the authoring session). Percentiles of the result
are linear interpolation between order statistics (position (n - 1) * p). Sensitivity is (a)
Spearman's rank correlation (Pearson's correlation of average ranks) between each uncertain input
and the result, and (b) the result with that input alone at its 5th and its 95th percentile and
every other input at its median.

Precision: percentiles and the mean are printed to two significant figures, or one when the 90
percent range is wider than a factor of one hundred. The one-at-a-time sensitivity figures are
printed to two. A model with only fixed inputs is arithmetic and is printed in full.

What it enforces (ERROR, exit 1, nothing is simulated):
  - quantity, unit, inputs and formula present; no unknown keys; numbers are JSON numbers
    (true, "7", NaN and Infinity are refused)
  - every uncertain input has a why, every fixed input a source; no text still begins with the
    template marker REPLACE
  - low below high; lognormal bounds above zero; triangular mode within its bounds; probability
    inputs within 0 to 1; choice weights positive
  - the formula uses only numbers, declared input names, the operators above, min and max, and
    uses every declared input
  - runs is a whole number from 1,000 to 1,000,000; seed is a whole number
  - the formula gives a finite number on every run (no division by zero, no overflow)
  - with --compare: both models are valid and share a unit
What it reports for a person to decide (ADVISORY):
  - no timeframe or scope; all inputs fixed; draws of a probability input clipped to 0 or 1
  - a 90 percent range spanning more than two orders of magnitude
  - a reported range that reaches past an anchor (a contradiction if the anchor is a hard limit)
  - with --compare: ranges that do not overlap, ranges that overlap only at their edges (neither
    median inside the other range), and differing quantity text

It cannot tell whether a range is a good one, whether a source says what the model claims, whether
the decomposition leaves something out, or whether inputs that the model treats as independent
move together. Correlated inputs make the real range wider or narrower than the one printed.

Exit codes: 0 ran and nothing failed. 1 the model was refused. 2 bad arguments or unreadable input.
"""
import datetime as dt
import json
import math
import random
import re
import statistics
import sys
from pathlib import Path

ND = statistics.NormalDist()
Z90 = ND.inv_cdf(0.95)  # 1.6448536...: a 90 percent interval runs from -Z90 to +Z90 standard deviations
MIN_RUNS, MAX_RUNS, DEFAULT_RUNS, DEFAULT_SEED = 1000, 1000000, 20000, 1
MAX_FORMULA, MAX_DEPTH, MAX_TOKENS = 2000, 60, 400
DIGITS = "0123456789"
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
NUMBER_RE = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
FUNCS = ("min", "max")
TOP_KEYS = {"quantity", "unit", "timeframe", "scope", "inputs", "formula", "anchors", "runs", "seed", "notes"}
DIST_KEYS = {"fixed": {"value", "source", "as_of"}, "uniform": {"low", "high", "why"}, "normal": {"low", "high", "why"},
             "lognormal": {"low", "high", "why"}, "triangular": {"low", "mode", "high", "why"}, "choice": {"values", "weights", "why"}}
COMMON_KEYS = {"dist", "kind", "note"}
ALLOWED = "only numbers, input names, + - * / ** ( ) , min and max are allowed"
FLAGS = {"--json", "--compare"}


class FormulaError(Exception):
    pass


# ---------------------------------------------------------------- formula: tokens, parser, evaluator

def tokenise(text):
    """Split a formula into (kind, value, position) tokens. Refuses every character it does not know."""
    if len(text) > MAX_FORMULA:
        raise FormulaError("the formula is longer than %d characters" % MAX_FORMULA)
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in DIGITS or (c == "." and i + 1 < n and text[i + 1] in DIGITS):
            m = NUMBER_RE.match(text, i)
            i = m.end()
            if i < n and (text[i] in LETTERS or text[i] == "_"):
                raise FormulaError("a number runs into a name at position %d (%r); %s" % (m.start(), text[m.start():i + 1], ALLOWED))
            tokens.append(("num", float(m.group()), m.start()))
        elif c in LETTERS:
            j = i
            while j < n and (text[j] in LETTERS or text[j] in DIGITS or text[j] == "_"):
                j += 1
            tokens.append(("name", text[i:j], i))
            i = j
        elif text.startswith("**", i):
            tokens.append(("op", "**", i))
            i += 2
        elif c in "+-*/(),":
            tokens.append(("op", c, i))
            i += 1
        else:
            raise FormulaError("%r at position %d is not allowed (names start with a letter); %s" % (c, i, ALLOWED))
        if len(tokens) > MAX_TOKENS:
            raise FormulaError("the formula has more than %d numbers, names and symbols; split the model into smaller ones" % MAX_TOKENS)
    return tokens


class Parser:
    """Recursive descent. Grammar, loosest binding first:
         expr  := term (('+' | '-') term)*
         term  := unary (('*' | '/') unary)*
         unary := ('+' | '-') unary | power
         power := atom ('**' unary)?            right associative; -2 ** 2 is -(2 ** 2), as in Python
         atom  := number | name | ('min' | 'max') '(' expr (',' expr)+ ')' | '(' expr ')'
    """

    def __init__(self, tokens, names):
        self.t, self.i, self.names, self.used = tokens, 0, names, set()

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("end", None, None)

    def take(self, value=None):
        tok = self.peek()
        if value is not None and not (tok[0] == "op" and tok[1] == value):
            raise FormulaError("expected %r %s" % (value, self.where(tok)))
        self.i += 1
        return tok

    @staticmethod
    def where(tok):
        return "at the end of the formula" if tok[0] == "end" else "at position %d (found %r)" % (tok[2], tok[1])

    def is_op(self, *values):
        tok = self.peek()
        return tok[0] == "op" and tok[1] in values

    def expr(self, depth):
        if depth > MAX_DEPTH:
            raise FormulaError("the formula is nested more than %d levels deep" % MAX_DEPTH)
        node = self.term(depth)
        while self.is_op("+", "-"):
            op = self.take()[1]
            node = ("bin", op, node, self.term(depth))
        return node

    def term(self, depth):
        node = self.unary(depth)
        while self.is_op("*", "/"):
            op = self.take()[1]
            node = ("bin", op, node, self.unary(depth))
        return node

    def unary(self, depth):
        if depth > MAX_DEPTH:
            raise FormulaError("the formula is nested more than %d levels deep" % MAX_DEPTH)
        if self.is_op("-"):
            self.take()
            return ("neg", self.unary(depth + 1))
        if self.is_op("+"):
            self.take()
            return self.unary(depth + 1)
        return self.power(depth)

    def power(self, depth):
        base = self.atom(depth)
        if self.is_op("**"):
            self.take()
            return ("bin", "**", base, self.unary(depth + 1))
        return base

    def atom(self, depth):
        tok = self.peek()
        if tok[0] == "num":
            self.take()
            return ("num", tok[1])
        if tok[0] == "name":
            self.take()
            name = tok[1]
            if self.is_op("("):
                if name not in FUNCS:
                    raise FormulaError("%r at position %d is called like a function; the only functions are min and max" % (name, tok[2]))
                self.take("(")
                args = [self.expr(depth + 1)]
                while self.is_op(","):
                    self.take()
                    args.append(self.expr(depth + 1))
                self.take(")")
                if len(args) < 2:
                    raise FormulaError("%s needs at least two arguments" % name)
                return ("call", name, args)
            if name in FUNCS:
                raise FormulaError("%s at position %d must be followed by its arguments in parentheses" % (name, tok[2]))
            if name not in self.names:
                raise FormulaError("unknown name %r at position %d: every name must be a declared input (%s)"
                                   % (name, tok[2], ", ".join(sorted(self.names)) or "none declared"))
            self.used.add(name)
            return ("name", name)
        if self.is_op("("):
            self.take()
            node = self.expr(depth + 1)
            self.take(")")
            return node
        raise FormulaError("expected a number, an input name or '(' %s" % self.where(tok))


def parse_formula(text, names):
    """Return (tree, names used). Raises FormulaError for anything outside the small grammar."""
    if not isinstance(text, str) or not text.strip():
        raise FormulaError("the formula is empty")
    tokens = tokenise(text)
    p = Parser(tokens, set(names))
    tree = p.expr(0)
    if p.peek()[0] != "end":
        raise FormulaError("unexpected %r at position %d; %s" % (p.peek()[1], p.peek()[2], ALLOWED))
    return tree, p.used


def evaluate(node, env):
    """Evaluate a parsed formula with floats. Raises FormulaError where the arithmetic has no finite answer."""
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "name":
        return env[node[1]]
    if kind == "neg":
        return -evaluate(node[1], env)
    if kind == "call":
        vals = [evaluate(a, env) for a in node[2]]
        return min(vals) if node[1] == "min" else max(vals)
    op, a, b = node[1], evaluate(node[2], env), evaluate(node[3], env)
    try:
        if op == "+":
            r = a + b
        elif op == "-":
            r = a - b
        elif op == "*":
            r = a * b
        elif op == "/":
            if b == 0:
                raise FormulaError("division by zero")
            r = a / b
        else:
            r = math.pow(a, b)
    except (OverflowError, ValueError, ZeroDivisionError):
        raise FormulaError("%g %s %g has no finite real answer" % (a, op, b))
    if not math.isfinite(r):
        raise FormulaError("%g %s %g is not finite" % (a, op, b))
    return r


# ---------------------------------------------------------------- distributions

def lognormal_params(low, high):
    """low and high are the 5th and 95th percentiles. Returns (mean, sd) of ln X."""
    mu = (math.log(low) + math.log(high)) / 2.0
    sigma = (math.log(high) - math.log(low)) / (2.0 * Z90)
    return mu, sigma


def normal_params(low, high):
    """low and high are the 5th and 95th percentiles. Returns (mean, sd)."""
    return (low + high) / 2.0, (high - low) / (2.0 * Z90)


def quantile(spec, u):
    """The value below which a share u (0 < u < 1) of the distribution lies."""
    d = spec["dist"]
    if d == "fixed":
        return float(spec["value"])
    if d == "uniform":
        return spec["low"] + u * (spec["high"] - spec["low"])
    if d == "normal":
        mu, sigma = normal_params(spec["low"], spec["high"])
        return mu + sigma * ND.inv_cdf(u)
    if d == "lognormal":
        mu, sigma = lognormal_params(spec["low"], spec["high"])
        return math.exp(mu + sigma * ND.inv_cdf(u))
    if d == "triangular":
        lo, mode, hi = spec["low"], spec["mode"], spec["high"]
        if u < (mode - lo) / (hi - lo):
            return lo + math.sqrt(u * (hi - lo) * (mode - lo))
        return hi - math.sqrt((1.0 - u) * (hi - lo) * (hi - mode))
    pairs = sorted(zip(spec["values"], spec["weights"]))
    total, run = float(sum(w for _, w in pairs)), 0.0
    for v, w in pairs:
        run += w / total
        if u <= run + 1e-12:
            return float(v)
    return float(pairs[-1][0])


def clip_probability(spec, x):
    if spec.get("kind") == "probability":
        if x < 0.0:
            return 0.0, True
        if x > 1.0:
            return 1.0, True
    return x, False


# ---------------------------------------------------------------- validation

def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def text_ok(v, min_len=1):
    return isinstance(v, str) and len(v.strip()) >= min_len


def placeholders(obj, path=""):
    """Paths of every text value still holding the template's REPLACE marker."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            found += placeholders(v, "%s.%s" % (path, k) if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += placeholders(v, "%s[%d]" % (path, i + 1))
    elif isinstance(obj, str) and obj.strip().startswith("REPLACE"):
        found.append(path)
    return found


def real_date(v):
    if not isinstance(v, str) or not ISO_DATE.fullmatch(v):
        return False
    try:
        dt.date.fromisoformat(v)
        return True
    except ValueError:
        return False


def check_input(name, s, errors):
    where = "input %r" % name
    if not NAME_RE.match(name) or name in FUNCS:
        errors.append("%s: an input name starts with a letter, uses letters, digits and underscores, and is not min or max" % where)
    if not isinstance(s, dict):
        errors.append("%s must be an object with a dist" % where)
        return
    d = s.get("dist")
    if d not in DIST_KEYS:
        errors.append("%s: dist %r is not one of %s" % (where, d, ", ".join(sorted(DIST_KEYS))))
        return
    for k in sorted(set(s) - DIST_KEYS[d] - COMMON_KEYS):
        errors.append("%s: unknown key %r for a %s input" % (where, k, d))
    if "kind" in s and s["kind"] != "probability":
        errors.append("%s: kind %r is not known; the only kind is \"probability\"" % (where, s["kind"]))
    prob = s.get("kind") == "probability"
    if d == "fixed":
        if not number(s.get("value")):
            errors.append("%s: value must be a number (true, text, NaN and Infinity are not numbers)" % where)
        elif prob and not 0 <= s["value"] <= 1:
            errors.append("%s: declared a probability but its value %g is outside 0 to 1" % (where, s["value"]))
        if not text_ok(s.get("source"), 3):
            errors.append("%s: a fixed input is a looked-up fact and needs a source. If it is a judgement, give it a range and a why" % where)
        if "as_of" in s and not real_date(s["as_of"]):
            errors.append("%s: as_of must be a real date written YYYY-MM-DD" % where)
        return
    if not text_ok(s.get("why"), 10):
        errors.append("%s: an uncertain input needs a why: the reasoning for its range, in a sentence" % where)
    if d == "choice":
        vals, wts = s.get("values"), s.get("weights")
        if not isinstance(vals, list) or len(vals) < 2 or not all(number(v) for v in vals):
            errors.append("%s: values must be a list of at least two numbers" % where)
            return
        if not isinstance(wts, list) or len(wts) != len(vals) or not all(number(w) and w > 0 for w in wts):
            errors.append("%s: weights must be a list of positive numbers, one for each value" % where)
        if prob and not all(0 <= v <= 1 for v in vals):
            errors.append("%s: declared a probability but a value is outside 0 to 1" % where)
        return
    lo, hi = s.get("low"), s.get("high")
    if not number(lo) or not number(hi):
        errors.append("%s: low and high must both be numbers (true, text, NaN and Infinity are not numbers)" % where)
        return
    if not lo < hi:
        errors.append("%s: low (%g) must be below high (%g). For a value with no uncertainty use dist fixed with a source" % (where, lo, hi))
        return
    if d == "lognormal" and lo <= 0:
        errors.append("%s: a lognormal input needs low above zero (got %g); a quantity that can be zero or negative is not lognormal" % (where, lo))
    if d == "triangular":
        mode = s.get("mode")
        if not number(mode) or not lo <= mode <= hi:
            errors.append("%s: a triangular input needs a mode between low and high" % where)
    if prob and (lo < 0 or hi > 1):
        errors.append("%s: declared a probability but its range %g to %g is outside 0 to 1" % (where, lo, hi))


def check_model(m):
    """Return (errors, advisories, tree). tree is None when there are errors."""
    errors, advisories = [], []
    if not isinstance(m, dict):
        return ["the file must hold one JSON object"], [], None
    for k in sorted(set(m) - TOP_KEYS):
        errors.append("unknown key %r at the top level (known: %s)" % (k, ", ".join(sorted(TOP_KEYS))))
    for where in placeholders(m):
        errors.append("%s still holds the template text beginning REPLACE; write the real value" % where)
    if not text_ok(m.get("quantity"), 3):
        errors.append("quantity is missing: say what is being estimated")
    if not text_ok(m.get("unit")):
        errors.append("unit is missing: an estimate with no unit cannot be checked")
    for k in ("timeframe", "scope"):
        if k in m and not text_ok(m[k]):
            errors.append("%s must be text when given" % k)
        elif k not in m:
            advisories.append("no %s given: state it, so the quantity could in principle be checked" % k)
    inputs = m.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        errors.append("inputs must be a non-empty object of named inputs")
        inputs = {}
    for name, s in inputs.items():
        check_input(name, s, errors)
    runs = m.get("runs", DEFAULT_RUNS)
    if not whole(runs) or not MIN_RUNS <= runs <= MAX_RUNS:
        errors.append("runs must be a whole number from %d to %d (got %r); fewer runs make the 5th and 95th percentiles unstable"
                      % (MIN_RUNS, MAX_RUNS, runs))
    if not whole(m.get("seed", DEFAULT_SEED)):
        errors.append("seed must be a whole number (got %r)" % (m.get("seed"),))
    anchors = m.get("anchors", [])
    if not isinstance(anchors, list):
        errors.append("anchors must be a list")
        anchors = []
    for i, a in enumerate(anchors):
        if not isinstance(a, dict) or not text_ok(a.get("name")):
            errors.append("anchor %d needs a name" % (i + 1))
            continue
        for k in sorted(set(a) - {"name", "max", "min", "source"}):
            errors.append("anchor %r: unknown key %r" % (a["name"], k))
        if "max" not in a and "min" not in a:
            errors.append("anchor %r needs a max or a min" % a["name"])
        for k in ("max", "min"):
            if k in a and not number(a[k]):
                errors.append("anchor %r: %s must be a number" % (a["name"], k))
        if number(a.get("min")) and number(a.get("max")) and a["min"] > a["max"]:
            errors.append("anchor %r: min is above max" % a["name"])
    tree = None
    try:
        tree, used = parse_formula(m.get("formula"), [n for n in inputs if isinstance(n, str)])
        for name in inputs:
            if name not in used:
                errors.append("input %r is declared but the formula never uses it" % name)
    except FormulaError as e:
        errors.append("formula: %s" % e)
    if not errors and all(s["dist"] == "fixed" for s in inputs.values()):
        advisories.append("every input is fixed: this is arithmetic on looked-up figures, not an estimate, and no range can be given")
    return errors, advisories, (tree if not errors else None)


# ---------------------------------------------------------------- simulation and summaries

def simulate(m, tree):
    """Return (outputs, draws by input name, clipped counts). Raises FormulaError naming the run that failed."""
    inputs = m["inputs"]
    runs, rng = m.get("runs", DEFAULT_RUNS), random.Random(m.get("seed", DEFAULT_SEED))
    names = list(inputs)
    fixed = {n: float(inputs[n]["value"]) for n in names if inputs[n]["dist"] == "fixed"}
    uncertain = [n for n in names if n not in fixed]
    draws = {n: [] for n in uncertain}
    clipped = {n: 0 for n in uncertain}
    out = []
    env = dict(fixed)
    for r in range(runs):
        for n in uncertain:
            u = rng.random()
            while u == 0.0:
                u = rng.random()
            x, was = clip_probability(inputs[n], quantile(inputs[n], u))
            clipped[n] += 1 if was else 0
            env[n] = x
            draws[n].append(x)
        try:
            out.append(evaluate(tree, env))
        except FormulaError as e:
            raise FormulaError("the formula failed on run %d of %d: %s. Check for an input that can reach zero under a division" % (r + 1, runs, e))
    return out, draws, clipped


def percentile(sorted_xs, p):
    """Linear interpolation between order statistics at position (n - 1) * p, for p from 0 to 1."""
    h = (len(sorted_xs) - 1) * p
    lo = int(math.floor(h))
    hi = min(lo + 1, len(sorted_xs) - 1)
    return sorted_xs[lo] + (h - lo) * (sorted_xs[hi] - sorted_xs[lo])


def average_ranks(xs):
    """Ranks from 1, with tied values sharing the average of the ranks they span."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks, i = [0.0] * len(xs), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def spearman(xs, ys):
    """Spearman's rank correlation: Pearson's correlation of the average ranks. None when either side is constant."""
    return pearson(average_ranks(xs), average_ranks(ys))


def round_sig(x, sig):
    """Round to sig significant figures."""
    if x == 0 or not math.isfinite(x):
        return 0.0 if x == 0 else x
    return float("%.*e" % (sig - 1, x))


def figures_for(p5, p95):
    """How many significant figures a result with this 90 percent range is printed to."""
    if (p5 > 0 and p95 > 0) or (p5 < 0 and p95 < 0):
        lo, hi = sorted((abs(p5), abs(p95)))
        return 2 if hi / lo <= 100.0 else 1
    return 2


def make_rounder(p5, p95, exact):
    """Return a function that rounds any figure for this result the same way."""
    if exact:
        return lambda x: float("%.12g" % x)
    sig = figures_for(p5, p95)
    if (p5 > 0 and p95 > 0) or (p5 < 0 and p95 < 0):
        return lambda x: round_sig(x, sig)
    big = max(abs(p5), abs(p95))
    if big == 0:
        return lambda x: round_sig(x, 2)
    place = int(math.floor(math.log10(big))) - 1  # the range crosses zero: keep two figures of its larger end
    return lambda x: float(round(x / 10.0 ** place) * 10.0 ** place) if place >= 0 else round(x, -place)


def fmt(x):
    """A rounded number as plain ASCII text, with thousands separators."""
    if x is None:
        return "n/a"
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1e15 or a < 1e-4:
        return "%.2g" % x
    if a >= 1000 and float(x).is_integer():
        return "{:,.0f}".format(x)
    return "%.12g" % x


def share_text(count, total):
    if count == 0:
        return "0 of %s runs" % "{:,}".format(total)
    pct = 100.0 * count / total
    return "%s of %s runs (%s)" % ("{:,}".format(count), "{:,}".format(total), "under 1%" if pct < 1 else "%d%%" % int(pct + 0.5))


def describe_input(name, s):
    d = s["dist"]
    med = clip_probability(s, quantile(s, 0.5))[0]
    if d in ("uniform", "normal", "lognormal") and not s["low"] < round_sig(med, 2) < s["high"]:
        med = round_sig(med, 3)  # a narrow range: two figures would print the median as one of its own bounds
    else:
        med = round_sig(med, 2)
    if d == "fixed":
        return "FACT        fixed %s%s; source: %s" % (fmt(float("%.12g" % s["value"])), (" (as of %s)" % s["as_of"]) if "as_of" in s else "", s["source"].strip())
    if d in ("normal", "lognormal"):
        body = "%s, 5th to 95th percentile %s to %s, median %s" % (d, fmt(s["low"]), fmt(s["high"]), fmt(med))
    elif d == "uniform":
        body = "uniform, hard bounds %s to %s, median %s" % (fmt(s["low"]), fmt(s["high"]), fmt(med))
    elif d == "triangular":
        body = "triangular, hard bounds %s to %s, most likely %s" % (fmt(s["low"]), fmt(s["high"]), fmt(s["mode"]))
    else:
        body = "choice of " + ", ".join("%s (weight %s)" % (fmt(v), fmt(w)) for v, w in zip(s["values"], s["weights"]))
    return "ASSESSMENT  %s%s; why: %s" % (body, " [probability]" if s.get("kind") == "probability" else "", s["why"].strip())


def run_model(m):
    """Validate and simulate one model. Returns a dict: errors, advisories and, when valid, result and raw."""
    errors, advisories, tree = check_model(m)
    if errors:
        return {"errors": errors, "advisories": advisories, "result": None, "raw": None}
    inputs, runs = m["inputs"], m.get("runs", DEFAULT_RUNS)
    try:
        out, draws, clipped = simulate(m, tree)
    except FormulaError as e:
        return {"errors": [str(e)], "advisories": advisories, "result": None, "raw": None}
    xs = sorted(out)
    raw = {p: percentile(xs, p / 100.0) for p in (5, 25, 50, 75, 95)}
    exact = not draws
    rnd = make_rounder(raw[5], raw[95], exact)
    medians = {n: clip_probability(inputs[n], quantile(inputs[n], 0.5))[0] for n in inputs}
    try:
        at_medians = evaluate(tree, medians)
    except FormulaError:
        at_medians = None
    result = {"quantity": m["quantity"].strip(), "unit": m["unit"].strip(), "runs": runs, "seed": m.get("seed", DEFAULT_SEED),
              "exact": exact, "significant_figures": None if exact else figures_for(raw[5], raw[95]),
              "percentiles": {str(p): rnd(raw[p]) for p in (5, 25, 50, 75, 95)},
              "mean": rnd(math.fsum(x / len(out) for x in out)),
              "all_inputs_at_median": None if at_medians is None else rnd(at_medians),
              "range_factor": None, "anchors": [], "sensitivity": [], "clipped": {}}
    if raw[5] > 0:
        factor = raw[95] / raw[5]
        result["range_factor"] = round_sig(factor, 2)
        if factor > 100:
            advisories.append("the 90 percent range spans more than two orders of magnitude (a factor of about %s): too wide to decide most things. Pin down the input at the top of the sensitivity table"
                              % fmt(round_sig(factor, 1)))
    for n, c in clipped.items():
        if c:
            result["clipped"][n] = c
            advisories.append("input %r is a probability and %s fell outside 0 to 1 and were set to the bound; a uniform or triangular range cannot leave 0 to 1" % (n, share_text(c, runs)))
    for a in m.get("anchors", []):
        above = sum(1 for x in out if "max" in a and x > a["max"])
        below = sum(1 for x in out if "min" in a and x < a["min"])
        result["anchors"].append({"name": a["name"].strip(), "max": a.get("max"), "min": a.get("min"), "runs_above_max": above if "max" in a else None,
                                  "runs_below_min": below if "min" in a else None, "runs": runs})
        if ("max" in a and raw[95] > a["max"]) or ("min" in a and raw[5] < a["min"]):
            advisories.append("the reported 90 percent range reaches past the anchor %r. If that anchor is a hard limit, the model contradicts it: fix the model before reporting. "
                              "If it is a threshold, the count of runs beyond it is how often this model crosses it" % a["name"].strip())
    for n in draws:
        rho = spearman(draws[n], out)
        lo_env, hi_env = dict(medians), dict(medians)
        lo_env[n] = clip_probability(inputs[n], quantile(inputs[n], 0.05))[0]
        hi_env[n] = clip_probability(inputs[n], quantile(inputs[n], 0.95))[0]
        try:
            a, b = evaluate(tree, lo_env), evaluate(tree, hi_env)
        except FormulaError:
            a = b = None
        swing = None
        if a is not None and a > 0 and b > 0:
            swing = round_sig(max(a, b) / min(a, b), 2)
        result["sensitivity"].append({"input": n, "rank_correlation": None if rho is None else round(rho, 2),
                                      "result_at_input_5th": None if a is None else round_sig(a, 2), "result_at_input_95th": None if b is None else round_sig(b, 2),
                                      "swing_factor": swing})
    result["sensitivity"].sort(key=lambda r: -abs(r["rank_correlation"] or 0.0))
    return {"errors": [], "advisories": advisories, "result": result, "raw": raw}


def render_model(path, m, res):
    L = []
    if res["errors"]:
        L.append("fermi: %s was refused" % path)
        L += ["  ERROR     " + e for e in res["errors"]]
        L += ["  ADVISORY  " + a for a in res["advisories"]]
        L.append("RESULT: REFUSED. %d error(s). Nothing was simulated." % len(res["errors"]))
        return L
    r = res["result"]
    unit = r["unit"]
    L.append("fermi: %s" % r["quantity"])
    extra = [m[k].strip() for k in ("timeframe", "scope") if k in m]
    if extra:
        L.append("  " + "; ".join(extra))
    L.append("INPUTS")
    width = max(len(n) for n in m["inputs"])
    for n, s in m["inputs"].items():
        L.append("  %-*s  %s" % (width, n, describe_input(n, s)))
    L.append("FORMULA  %s" % " ".join(m["formula"].split()))
    pc = r["percentiles"]
    if r["exact"]:
        L.append("RESULT   %s %s exactly (arithmetic on fixed inputs; no range)" % (fmt(pc["50"]), unit))
    else:
        L.append("RESULT   median %s %s; 90 percent range %s to %s" % (fmt(pc["50"]), unit, fmt(pc["5"]), fmt(pc["95"])))
        L.append("  percentiles  5th %s | 25th %s | 50th %s | 75th %s | 95th %s" % tuple(fmt(pc[k]) for k in ("5", "25", "50", "75", "95")))
        mean_note = ""
        if r["mean"] > pc["50"]:
            mean_note = " (above the median: the upper tail pulls it up. Quote the median and the range, not the mean)"
        elif r["mean"] < pc["50"]:
            mean_note = " (below the median: the lower tail pulls it down. Quote the median and the range, not the mean)"
        L.append("  mean %s%s" % (fmt(r["mean"]), mean_note))
        L.append("  every input at its median gives %s" % fmt(r["all_inputs_at_median"]))
        L.append("  %s runs, seed %d; printed to %d significant figure%s%s" % ("{:,}".format(r["runs"]), r["seed"], r["significant_figures"],
                 "" if r["significant_figures"] == 1 else "s", "" if r["range_factor"] is None else "; high end is about %s times the low end" % fmt(r["range_factor"])))
    if r["anchors"]:
        L.append("ANCHORS")
        for a in r["anchors"]:
            bits = []
            if a["max"] is not None:
                bits.append("above the max of %s: %s" % (fmt(float("%.12g" % a["max"])), share_text(a["runs_above_max"], a["runs"])))
            if a["min"] is not None:
                bits.append("below the min of %s: %s" % (fmt(float("%.12g" % a["min"])), share_text(a["runs_below_min"], a["runs"])))
            L.append("  %s. %s" % (a["name"], "; ".join(bits)))
    if r["sensitivity"]:
        L.append("SENSITIVITY  (rank correlation with the result; then the result with this input alone at its 5th and 95th percentile, the rest at their medians)")
        for s in r["sensitivity"]:
            L.append("  %-*s  %-6s %s to %s%s" % (width, s["input"], "n/a" if s["rank_correlation"] is None else "%+.2f" % s["rank_correlation"],
                     fmt(s["result_at_input_5th"]), fmt(s["result_at_input_95th"]),
                     "" if s["swing_factor"] is None else "   (a factor of %s)" % fmt(s["swing_factor"])))
        top = r["sensitivity"][0]
        if top["rank_correlation"] is not None:
            L.append("  Drives the spread most: %s. Narrowing it narrows the answer more than narrowing any other input." % top["input"])
    L += ["  ADVISORY  " + a for a in res["advisories"]]
    L.append("RESULT: RAN. 0 errors, %d advisory note(s). The range is only as good as the input ranges and the decomposition." % len(res["advisories"]))
    return L


def compare(a, b):
    """Compare two valid results on their 90 percent ranges. Returns (dict, advisories)."""
    ra, rb, adv = a["raw"], b["raw"], []
    lo, hi = max(ra[5], rb[5]), min(ra[95], rb[95])
    positive = ra[5] > 0 and rb[5] > 0
    out = {"overlap": lo <= hi, "scale": "log" if positive else "linear", "overlap_low": None, "overlap_high": None,
           "share_of_a": None, "share_of_b": None, "gap_factor": None, "median_ratio_b_over_a": None,
           "a_median_inside_b": rb[5] <= ra[50] <= rb[95], "b_median_inside_a": ra[5] <= rb[50] <= ra[95], "edge_overlap_only": False}
    f = math.log if positive else (lambda x: x)
    if positive and ra[50] > 0:
        out["median_ratio_b_over_a"] = round_sig(rb[50] / ra[50], 2)
    if lo <= hi:
        rnd_a = make_rounder(ra[5], ra[95], a["result"]["exact"])
        out["overlap_low"], out["overlap_high"] = rnd_a(lo), rnd_a(hi)
        for key, r in (("share_of_a", ra), ("share_of_b", rb)):
            width = f(r[95]) - f(r[5])
            out[key] = 1.0 if width <= 0 else round((f(hi) - f(lo)) / width, 1)
        if not out["a_median_inside_b"] and not out["b_median_inside_a"]:
            out["edge_overlap_only"] = True
            adv.append("the ranges overlap only at their edges: neither median lies inside the other range. Treat this as a "
                       "disagreement to explain before using either figure, and do not average them")
    else:
        if positive:
            out["gap_factor"] = round_sig(lo / hi, 2)
        adv.append("the two 90 percent ranges do not overlap: the decompositions disagree. Find out why before reporting either")
    return out, adv


def share_words(x):
    if x is None:
        return "n/a"
    if x >= 0.95:
        return "all or nearly all"
    if x < 0.05:
        return "under a tenth"
    return "about %d%%" % int(round(x * 10) * 10)


def load(path):
    """Read a model file. Returns (model, None) or (None, message)."""
    def refuse(c):
        raise ValueError("%s is not a JSON number" % c)
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        return None, "cannot read %s: %s" % (path, e.strerror or e)
    if b"\x00" in raw:
        return None, "%s contains NUL bytes; it is not a text file" % path
    def no_duplicates(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise ValueError("the key %r appears twice in one object" % k)
            seen[k] = v
        return seen
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_constant=refuse, object_pairs_hook=no_duplicates), None
    except UnicodeDecodeError:
        return None, "%s is not valid UTF-8" % path
    except ValueError as e:
        return None, "%s is not valid JSON (%s)" % (path, str(e)[:70])


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a in FLAGS:
            flags.add(a)
        elif a.startswith("--"):
            print("fermi: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    want = 2 if "--compare" in flags else 1
    if len(args) != want:
        if not argv:
            emit(__doc__)
        else:
            print("fermi: expected %d model file%s, got %d. Usage: fermi.py MODEL.json [--json] | fermi.py --compare A.json B.json [--json]"
                  % (want, "" if want == 1 else "s", len(args)), file=sys.stderr)
        return 2
    models = []
    for p in args:
        m, err = load(p)
        if err:
            print("fermi: " + err, file=sys.stderr)
            return 2
        models.append(m)
    results = [run_model(m) for m in models]
    public = [{"file": p, "errors": r["errors"], "advisories": r["advisories"], "result": r["result"]} for p, r in zip(args, results)]
    failed = any(r["errors"] for r in results)
    if "--compare" not in flags:
        if "--json" in flags:
            emit(json.dumps(public[0], indent=1, ensure_ascii=True, allow_nan=False))
        else:
            emit("\n".join(render_model(args[0], models[0], results[0])))
        return 1 if failed else 0
    cmp_out, cmp_adv, cmp_err = None, [], []
    if not failed:
        ua, ub = results[0]["result"]["unit"], results[1]["result"]["unit"]
        if ua != ub:
            cmp_err.append("the models are in different units (%r and %r); ranges in different units cannot be compared" % (ua, ub))
        else:
            cmp_out, cmp_adv = compare(results[0], results[1])
            if results[0]["result"]["quantity"] != results[1]["result"]["quantity"]:
                cmp_adv.append("the two models word the quantity differently; check they estimate the same thing over the same period and scope")
    if "--json" in flags:
        emit(json.dumps({"models": public, "comparison": cmp_out, "errors": cmp_err, "advisories": cmp_adv}, indent=1, ensure_ascii=True, allow_nan=False))
        return 1 if (failed or cmp_err) else 0
    L = []
    for label, p, m, r in zip("AB", args, models, results):
        L.append("=== MODEL %s: %s" % (label, p))
        L += render_model(p, m, r)
    L.append("=== COMPARISON")
    if failed:
        L.append("RESULT: REFUSED. A model has errors, so nothing was compared.")
    elif cmp_err:
        L += ["  ERROR     " + e for e in cmp_err]
        L.append("RESULT: REFUSED. Nothing was compared.")
    else:
        ra, rb = results[0]["result"], results[1]["result"]
        unit = ra["unit"]
        for label, r in (("A", ra), ("B", rb)):
            L.append("  %s  median %s; 90 percent range %s to %s %s" % (label, fmt(r["percentiles"]["50"]), fmt(r["percentiles"]["5"]), fmt(r["percentiles"]["95"]), unit))
        if cmp_out["overlap"]:
            L.append("  The ranges overlap, from %s to %s %s. That is %s of A's range and %s of B's, measured on a %s scale."
                     % (fmt(cmp_out["overlap_low"]), fmt(cmp_out["overlap_high"]), unit, share_words(cmp_out["share_of_a"]), share_words(cmp_out["share_of_b"]), cmp_out["scale"]))
        else:
            L.append("  The ranges do NOT overlap.%s" % ("" if cmp_out["gap_factor"] is None else " The higher range starts about %s times above where the lower one ends." % fmt(cmp_out["gap_factor"])))
        if cmp_out["median_ratio_b_over_a"] is not None:
            L.append("  B's median is about %s times A's. A's median is %s B's range; B's median is %s A's range."
                     % (fmt(cmp_out["median_ratio_b_over_a"]), "inside" if cmp_out["a_median_inside_b"] else "outside", "inside" if cmp_out["b_median_inside_a"] else "outside"))
        L += ["  ADVISORY  " + a for a in cmp_adv]
        if cmp_out["overlap"] and cmp_out["edge_overlap_only"]:
            L.append("RESULT: COMPARED. The ranges touch, but each median is outside the other range: the decompositions mostly disagree. "
                     "Find the input that explains the gap.")
        else:
            L.append("RESULT: COMPARED. %s" % ("Overlap shows the two decompositions are compatible, not that either is right." if cmp_out["overlap"]
                                               else "Do not average two ranges that do not overlap. Find the input that explains the gap."))
    emit("\n".join(L))
    return 1 if (failed or cmp_err) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
