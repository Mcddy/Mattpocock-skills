#!/usr/bin/env python3
"""Recompute a study's headline numbers from its own counts. Standard library only.

Usage:
  python effect.py two-by-two --a-events 30 --a-total 1000 --b-events 20 --b-total 1000
                              [--a-label NAME] [--b-label NAME] [--treated a|b --event bad|good]
                              [--reported-p 0.03 [--p-relation eq|lt|gt]]
  python effect.py proportion --events 37 --total 120
  python effect.py means --mean1 M --sd1 S --n1 N --mean2 M --sd2 S --n2 N
  python effect.py check-percent --count 37 --total 120 --reported 31
  python effect.py attrition --start 500 --analysed 380 [--by-group NAME:START:ANALYSED ...]
  python effect.py relative-to-absolute --baseline 0.002 (--relative 1.5 | --percent-change 50)
  python effect.py check-mean --mean 5.19 --n 28 [--items 1]
  python effect.py check-p --test t|z|chi2|f --statistic 2.10 [--df 28] [--df2 N] --reported 0.045
                           [--relation eq|lt|gt] [--tails 2|1]
Every command also takes --json. two-by-two, proportion, means and attrition take --level 90|95|99
(default 95).

What each command computes, and by which method:
  two-by-two   risk in each group with a Wilson score interval (Wilson 1927); the absolute
               difference A minus B with Newcombe's hybrid score interval, his method 10
               (Newcombe 1998, Statistics in Medicine 17:873-890); the risk ratio with the log
               method of Katz and others (1978) and the odds ratio with Woolf's log method (1955);
               the number needed for one event of difference, 1 / |difference|, with its interval
               taken from the interval for the difference (Altman 1998, BMJ 317:1309-1312). When
               that interval includes zero the number needed has no finite interval and is
               reported as not estimable. Every NNT figure is rounded up (Cochrane Handbook).
               With --reported-p, the p value the paper prints for this table is compared with
               Pearson's chi-square on the counts, without and with the continuity correction
               (1 degree of freedom). It is CONSISTENT if either gives the printed value at the
               precision printed. Fisher's exact test and tests from a fitted model are not
               computed, so a MISMATCH names them as possible explanations.
  proportion   a proportion with its Wilson score interval.
  means        the difference in means with Welch's interval (unequal variances, Welch-
               Satterthwaite degrees of freedom), and Cohen's d, the difference divided by the
               pooled standard deviation. d is a convention for comparing across scales, not a
               verdict: no "small", "medium" or "large" is attached.
  check-percent  whether a reported percentage is what the counts give when rounded to the
               precision reported. A tie (12.5 reported as 12 or 13) passes either way.
  attrition    participants lost overall and by group, and whether loss differs between groups
               (Newcombe interval for the difference in loss).
  relative-to-absolute  what a relative change means in absolute terms at a stated baseline risk.
  check-mean   whether a reported mean of whole-number data (a count, a response on a numbered
               scale) can arise from the stated sample size: the GRIM test of Brown and Heathers
               (2017). n people give a total that is a whole number, so the mean must be a whole
               number divided by n (by n times --items for a scale averaged over several items).
               When n times items is at least 10 to the power of the decimal places printed, every
               mean is possible and the test says nothing: CANNOT CHECK.
  check-p      whether a reported p value is the one its test statistic gives. The statistic is
               taken as printed, so anything it could have been before rounding is allowed for,
               and the reported p is compared at the precision printed. t and z are two-sided
               unless --tails 1; chi2 and f use the upper tail. --relation lt checks "p < 0.05"
               style statements. Without the degrees of freedom a t, chi2 or f statistic has no
               p value: CANNOT CHECK.

What it enforces (exit 2, nothing computed): counts are whole numbers written in digits; events
do not exceed totals; totals are above zero; nothing is negative, NaN or infinite; a risk cannot
exceed 1. check-percent, attrition, check-mean, check-p and two-by-two with --reported-p exit 1
when the figures do not agree with each other, and check-mean, check-p and two-by-two with
--reported-p exit 3 with a CANNOT CHECK line when what was given cannot settle the question. A check that could not be made is never reported as consistent.
What it reports for a person to decide: the numbers, with the counts beside every percentage and
no more decimal places than the group sizes support (none under 100, one from 100, two from 10,000).

What it cannot tell: whether the counts were copied correctly, whether the comparison was fair,
whether people dropped out for reasons tied to the outcome, or whether the outcome was the one
planned. An interval here covers sampling variation in the counts given and nothing else. For two
systems scored on the same test items, two-by-two treats the scores as unpaired; with per-item
results a paired analysis is the right one and this script does not do it.

A mismatch found by any of the checks is a discrepancy in the document. It has ordinary causes (a
misprint, a different denominator, a one-sided test, a correction not mentioned) and the output
names what would settle it. It is never, by itself, a statement about why the numbers disagree.

Exit codes: 0 computed, and for a check, consistent. 1 a consistency check found a mismatch
(check-percent, attrition, check-mean, check-p, two-by-two with --reported-p). 2 bad arguments or
impossible input. 3 the check
could not be made from what was given (CANNOT CHECK: the reason).
"""
import json
import math
import re
import statistics
import sys
from fractions import Fraction

LEVELS = ("90", "95", "99")
WHOLE = re.compile(r"[0-9]{1,15}")
DECIMAL = re.compile(r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]{1,3})?")
PERCENT = re.compile(r"[0-9]{1,3}(?:\.[0-9]{1,6})?")
PRINTED = re.compile(r"-?(?:[0-9]{1,9}(?:\.[0-9]{0,6})?|\.[0-9]{1,6})")
PVALUE = re.compile(r"(?:0|1)?\.[0-9]{1,8}|0|1")
TESTS = ("t", "z", "chi2", "f")
SPEC = {
    "two-by-two": ({"--json"}, {"--a-events", "--a-total", "--b-events", "--b-total", "--a-label", "--b-label", "--treated", "--event", "--level",
                              "--reported-p", "--p-relation"},
                   ("--a-events", "--a-total", "--b-events", "--b-total")),
    "proportion": ({"--json"}, {"--events", "--total", "--level"}, ("--events", "--total")),
    "means": ({"--json"}, {"--mean1", "--sd1", "--n1", "--mean2", "--sd2", "--n2", "--level"}, ("--mean1", "--sd1", "--n1", "--mean2", "--sd2", "--n2")),
    "check-percent": ({"--json"}, {"--count", "--total", "--reported"}, ("--count", "--total", "--reported")),
    "attrition": ({"--json"}, {"--start", "--analysed", "--by-group", "--level"}, ("--start", "--analysed")),
    "relative-to-absolute": ({"--json"}, {"--baseline", "--relative", "--percent-change"}, ("--baseline",)),
    "check-mean": ({"--json"}, {"--mean", "--n", "--items"}, ("--mean",)),
    "check-p": ({"--json"}, {"--test", "--statistic", "--df", "--df2", "--reported", "--relation", "--tails"}, ("--test", "--statistic", "--reported")),
}
REPEATABLE = {"--by-group"}


class Stop(Exception):
    """Bad arguments or impossible input: one line on stderr, exit 2."""


# ---------------------------------------------------------------- statistics (full precision)

def z_for(level):
    return statistics.NormalDist().inv_cdf(0.5 + level / 200.0)


def wilson(k, n, z):
    """Wilson score interval for k events in n, without continuity correction."""
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denom
    lo, hi = max(0.0, centre - half), min(1.0, centre + half)
    if k == 0:
        lo = 0.0
    if k == n:
        hi = 1.0
    return lo, hi


def newcombe_difference(k1, n1, k2, n2, z):
    """Difference p1 - p2 with Newcombe's hybrid score interval (method 10)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, max(-1.0, lo), min(1.0, hi)


def risk_ratio(k1, n1, k2, n2, z):
    """Risk ratio p1/p2 with the log-method interval. Returns (rr, lo, hi) or (None, reason)."""
    if k1 == 0 or k2 == 0:
        return None, "a group has no events, so the ratio and its log-method interval cannot be computed"
    rr = (k1 / n1) / (k2 / n2)
    se = math.sqrt(1.0 / k1 - 1.0 / n1 + 1.0 / k2 - 1.0 / n2)
    return rr, math.exp(math.log(rr) - z * se), math.exp(math.log(rr) + z * se)


def odds_ratio(k1, n1, k2, n2, z):
    """Odds ratio with Woolf's log-method interval. Returns (or, lo, hi) or (None, reason)."""
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    if 0 in (a, b, c, d):
        return None, "a cell of the table is zero, so the odds ratio and its log-method interval cannot be computed"
    value = (a * d) / (b * c)
    se = math.sqrt(1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    return value, math.exp(math.log(value) - z * se), math.exp(math.log(value) + z * se)


def number_needed(d, lo, hi):
    """1/|difference| and its interval. The interval is None when the difference interval includes zero."""
    if d == 0:
        return None, None
    point = 1.0 / abs(d)
    if lo <= 0.0 <= hi:
        return point, None
    a, b = 1.0 / abs(lo), 1.0 / abs(hi)
    return point, (min(a, b), max(a, b))


def _betacf(a, b, x):
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularised incomplete beta function I_x(a, b), by continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    """Cumulative probability of Student's t with df degrees of freedom (df may be fractional)."""
    tail = 0.5 * betainc(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t > 0 else tail


def t_quantile(p, df):
    """The value t with t_cdf(t, df) = p, for 0.5 < p < 1, by bisection."""
    lo, hi = 0.0, 1.0
    while t_cdf(hi, df) < p:
        hi *= 2.0
        if hi > 1e12:
            break
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def gamma_upper(a, x):
    """Regularised upper incomplete gamma function Q(a, x): series below a + 1, continued fraction above."""
    if x <= 0.0:
        return 1.0
    front = math.exp(-x + a * math.log(x) - math.lgamma(a))
    if x < a + 1.0:
        term = total = 1.0 / a
        n = a
        for _ in range(100000):
            n += 1.0
            term *= x / n
            total += term
            if abs(term) < abs(total) * 3e-16:
                break
        return max(0.0, 1.0 - front * total)
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 100000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-16:
            break
    return min(1.0, front * h)


def p_from_statistic(test, stat, df, df2, tails):
    """The p value a test statistic gives. t and z: both tails unless tails is 1. chi2 and f: upper tail."""
    x = abs(stat)
    if test == "z":
        both = math.erfc(x / math.sqrt(2.0))
    elif test == "t":
        both = betainc(df / 2.0, 0.5, df / (df + x * x))
    elif test == "chi2":
        return gamma_upper(df / 2.0, x / 2.0)
    else:
        return betainc(df2 / 2.0, df / 2.0, df2 / (df2 + df * x)) if x > 0 else 1.0
    return both / 2.0 if tails == 1 else both


def chi_square_2x2(k1, n1, k2, n2):
    """Pearson's chi-square for a two-by-two table, without and with the continuity correction, each
    with its p value on 1 degree of freedom. None when a margin is zero and the statistic is undefined."""
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    n = n1 + n2
    margins = n1 * n2 * (a + c) * (b + d)
    if margins == 0:
        return None
    cross = abs(a * d - b * c)
    plain = n * cross * cross / margins
    reduced = max(0.0, cross - n / 2.0)
    corrected = n * reduced * reduced / margins
    return {"plain": plain, "p_plain": gamma_upper(0.5, plain / 2.0), "corrected": corrected, "p_corrected": gamma_upper(0.5, corrected / 2.0)}


def welch(m1, s1, n1, m2, s2, n2, level):
    """Difference m1 - m2 with Welch's interval. Returns a dict of full-precision values."""
    v1, v2 = s1 * s1 / n1, s2 * s2 / n2
    se = math.sqrt(v1 + v2)
    df = (v1 + v2) ** 2 / (v1 * v1 / (n1 - 1) + v2 * v2 / (n2 - 1))
    tcrit = t_quantile(0.5 + level / 200.0, df)
    diff = m1 - m2
    return {"difference": diff, "se": se, "df": df, "t_critical": tcrit, "low": diff - tcrit * se, "high": diff + tcrit * se}


def pooled_sd(s1, n1, s2, n2):
    return math.sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2))


def cohen_d(m1, s1, n1, m2, s2, n2):
    sp = pooled_sd(s1, n1, s2, n2)
    return None if sp == 0 else (m1 - m2) / sp


def percent_check(count, total, reported):
    """Is the reported percentage (text, as printed) what count/total gives at that precision?
    Returns a dict. Exact arithmetic; a tie passes."""
    places = len(reported.split(".")[1]) if "." in reported else 0
    stated = Fraction(reported)
    exact = Fraction(count * 100, total)
    tol = Fraction(1, 2 * 10 ** places)
    step = Fraction(1, 10 ** places)
    truncated = (exact // step) * step
    fits = [k for k in candidate_counts(stated, tol, total)]
    return {"consistent": abs(exact - stated) <= tol, "places": places, "exact": exact, "stated": stated,
            "truncation_matches": truncated == stated and abs(exact - stated) > tol, "counts_that_fit": fits}


def candidate_counts(stated, tol, total):
    """Whole counts out of total whose percentage rounds to the stated one."""
    low = (stated - tol) * total / 100
    high = (stated + tol) * total / 100
    first = max(0, math.ceil(low))
    last = min(total, math.floor(high), first + 11)
    return list(range(first, last + 1))


# ---------------------------------------------------------------- input and output helpers

def places_for(n):
    """Decimal places a percentage out of n can carry: none under 100, one from 100, two from 10,000."""
    if n < 100:
        return 0
    return 1 if n < 10000 else 2


def pct(x, places):
    return "%.*f" % (places, round(100.0 * x, places) + 0.0)


def num(x, places):
    v = round(x, places)
    return "%.*f" % (places, 0.0 if v == 0 else v)


def jnum(x, places):
    v = round(x, places)
    return 0.0 if v == 0 else v


def grouped(n):
    return "{:,}".format(n)


def whole(opts, key, least=0):
    text = opts[key]
    if not WHOLE.fullmatch(text):
        raise Stop("%s must be a whole number written in digits, got %r" % (key, text[:20]))
    v = int(text)
    if v < least:
        raise Stop("%s must be at least %d" % (key, least))
    return v


def decimal(opts, key):
    text = opts[key]
    if not DECIMAL.fullmatch(text):
        raise Stop("%s must be a plain number, got %r (NaN, infinity and words are refused)" % (key, text[:20]))
    v = float(text)
    if not math.isfinite(v):
        raise Stop("%s is not a finite number" % key)
    if abs(v) > 1e12:
        raise Stop("%s is larger than a million million, which this script does not handle" % key)
    return v


def decimals_typed(text):
    mantissa = re.split(r"[eE]", text)[0]
    return len(mantissa.split(".")[1]) if "." in mantissa else 0


def level_of(opts):
    text = opts.get("--level", "95")
    if text not in LEVELS:
        raise Stop("--level must be 90, 95 or 99")
    return int(text)


def label_of(opts, key, default):
    text = opts.get(key, default).strip()
    if not text or len(text) > 60 or not text.isprintable():
        raise Stop("%s must be 1 to 60 printable characters" % key)
    return text


def events_and_total(opts, ek, tk):
    k, n = whole(opts, ek), whole(opts, tk)
    if n == 0:
        raise Stop("%s is zero; a proportion needs at least one person or item" % tk)
    if k > n:
        raise Stop("%s (%d) is larger than %s (%d), which is impossible" % (ek, k, tk, n))
    return k, n


CANNOT = "CANNOT CHECK"
RESOLVE_MEAN = ("What would settle it: the item's own number of responses (people who skipped it lower n), whether the "
                "figure is a mean of whole numbers at all, and whether it was rounded or cut short. Ask for the "
                "table's denominators or the data.")
RESOLVE_P = ("What would settle it: the paper's own statement of the test, whether it was one-sided, the degrees of "
             "freedom, and any correction applied (for many comparisons, for unequal variances, for sphericity). "
             "Check the extraction first.")


METHODS = {
    "wilson": "Wilson score interval, no continuity correction (Wilson 1927; Newcombe 1998, Stat Med 17:857-872)",
    "newcombe": "difference by Newcombe's hybrid score interval, method 10 (Newcombe 1998, Stat Med 17:873-890)",
    "katz": "risk ratio interval on the log scale (Katz, Baptista, Azen and Pike 1978, Biometrics 34:469-474)",
    "woolf": "odds ratio interval on the log scale (Woolf 1955)",
    "altman": "number needed = 1 / |difference|, interval from the interval for the difference (Altman 1998, BMJ 317:1309-1312), rounded up",
    "welch": "Welch's interval for a difference in means, Welch-Satterthwaite degrees of freedom",
    "cohen": "Cohen's d with the pooled standard deviation (Cohen 1988)",
    "grim": "granularity of a mean of whole numbers: the total is a whole number, so the mean is that number divided by n "
            "times the number of items (the GRIM test: Brown and Heathers 2017, Social Psychological and Personality Science 8:363-369)",
    "pvalue": "p recomputed from the statistic as printed, allowing for its rounding, and compared at the precision of the "
              "reported p (the approach of statcheck: Nuijten and others 2016, Behavior Research Methods 48:1205-1226)",
}
LIMIT = ("An interval here covers sampling variation in the counts given and nothing else: not bias, not dropout, "
         "not a changed outcome.")


# ---------------------------------------------------------------- commands

def cmd_two_by_two(opts):
    level = level_of(opts)
    z = z_for(level)
    ka, na = events_and_total(opts, "--a-events", "--a-total")
    kb, nb = events_and_total(opts, "--b-events", "--b-total")
    la, lb = label_of(opts, "--a-label", "A"), label_of(opts, "--b-label", "B")
    treated, event = opts.get("--treated"), opts.get("--event")
    if (treated is None) != (event is None):
        raise Stop("give --treated and --event together, or neither")
    if treated is not None and treated not in ("a", "b"):
        raise Stop("--treated must be a or b")
    if event is not None and event not in ("bad", "good"):
        raise Stop("--event must be bad or good")
    if "--p-relation" in opts and "--reported-p" not in opts:
        raise Stop("--p-relation needs --reported-p")
    reported_p = None
    if "--reported-p" in opts:
        reported_p = reported_p_of(opts["--reported-p"], opts.get("--p-relation", "eq"))
    pp = places_for(min(na, nb))
    pa, pb = ka / na, kb / nb
    wa, wb = wilson(ka, na, z), wilson(kb, nb, z)
    d, dlo, dhi = newcombe_difference(ka, na, kb, nb, z)
    rr, orr = risk_ratio(ka, na, kb, nb, z), odds_ratio(ka, na, kb, nb, z)
    point, interval = number_needed(d, dlo, dhi)
    name = "number needed for one event of difference"
    if treated is not None and d != 0:
        fewer_in_treated = (d < 0) == (treated == "a")
        helped = fewer_in_treated == (event == "bad")
        name = "number needed to treat (NNT)" if helped else "number needed to harm (NNH)"
    res = {
        "group_a": {"label": la, "events": ka, "total": na, "risk_percent": jnum(100 * pa, pp),
                    "interval_percent": [jnum(100 * wa[0], pp), jnum(100 * wa[1], pp)]},
        "group_b": {"label": lb, "events": kb, "total": nb, "risk_percent": jnum(100 * pb, pp),
                    "interval_percent": [jnum(100 * wb[0], pp), jnum(100 * wb[1], pp)]},
        "absolute_difference": {"a_minus_b_percentage_points": jnum(100 * d, pp),
                                "interval_percentage_points": [jnum(100 * dlo, pp), jnum(100 * dhi, pp)],
                                "interval_includes_zero": dlo <= 0.0 <= dhi},
    }
    if rr[0] is None:
        res["risk_ratio"] = {"value": None, "interval": None, "reason": rr[1]}
    else:
        res["risk_ratio"] = {"value": jnum(rr[0], 2), "interval": [jnum(rr[1], 2), jnum(rr[2], 2)],
                             "relative_change_percent": jnum(100 * (rr[0] - 1), 0)}
    if orr[0] is None:
        res["odds_ratio"] = {"value": None, "interval": None, "reason": orr[1]}
    else:
        res["odds_ratio"] = {"value": jnum(orr[0], 2), "interval": [jnum(orr[1], 2), jnum(orr[2], 2)]}
    if point is None:
        res["number_needed"] = {"name": name, "value": None, "interval": None,
                                "reason": "the two risks are identical, so there is no difference to divide into"}
    elif interval is None:
        res["number_needed"] = {"name": name, "value": math.ceil(point - 1e-9), "unrounded": jnum(point, 1), "interval": None,
                                "reason": "not estimable: the interval for the difference includes zero, so the data are "
                                          "compatible with no difference and with a difference in either direction"}
    else:
        res["number_needed"] = {"name": name, "value": math.ceil(point - 1e-9), "unrounded": jnum(point, 1),
                                "interval": [math.ceil(interval[0] - 1e-9), math.ceil(interval[1] - 1e-9)],
                                "interval_unrounded": [jnum(interval[0], 1), jnum(interval[1], 1)]}
    methods = [METHODS[k] for k in ("wilson", "newcombe", "katz", "woolf", "altman")]
    L = ["effect two-by-two (%d%% intervals)" % level]
    for g, lab in ((res["group_a"], la), (res["group_b"], lb)):
        L.append("  %s: %s of %s had the event = %s%% (Wilson interval %s%% to %s%%)"
                 % (lab, grouped(g["events"]), grouped(g["total"]), pct(g["events"] / g["total"], pp),
                    num(g["interval_percent"][0], pp), num(g["interval_percent"][1], pp)))
    L.append("  ABSOLUTE  %s minus %s = %s percentage points (Newcombe interval %s to %s). The interval %s zero."
             % (la, lb, num(100 * d, pp), num(100 * dlo, pp), num(100 * dhi, pp), "includes" if dlo <= 0.0 <= dhi else "excludes"))
    if rr[0] is None:
        L.append("  RELATIVE  risk ratio: not estimable (%s)" % rr[1])
    else:
        change = 100 * (rr[0] - 1)
        word = "the same" if round(change) == 0 else ("%d%% %s" % (abs(round(change)), "higher" if change > 0 else "lower"))
        L.append("  RELATIVE  risk ratio %s/%s = %s (log-method interval %s to %s): %s in %s, relatively"
                 % (la, lb, num(rr[0], 2), num(rr[1], 2), num(rr[2], 2), word, la))
    if orr[0] is None:
        L.append("            odds ratio: not estimable (%s)" % orr[1])
    else:
        L.append("            odds ratio = %s (log-method interval %s to %s). It is not the risk ratio; they are close only when the event is rare."
                 % (num(orr[0], 2), num(orr[1], 2), num(orr[2], 2)))
    if rr[0] is not None:
        L.append("  TOGETHER  \"%s\" here means %s%% against %s%%: a difference of %s percentage points."
                 % (word, pct(pa, pp), pct(pb, pp), num(abs(100 * d), pp)))
    nn = res["number_needed"]
    if nn["value"] is None:
        L.append("  NUMBER NEEDED  not estimable (%s)" % nn["reason"])
    else:
        direction = "more" if d > 0 else "fewer"
        L.append("  NUMBER NEEDED  1 / |difference| = %s, rounded up to %s: about one %s event for every %s in %s in place of %s."
                 % (num(point, 1), grouped(nn["value"]), direction, grouped(nn["value"]), la, lb))
        if name != "number needed for one event of difference":
            L.append("            With %s as the treated group and the event counted as %s, this is the %s." % (la if treated == "a" else lb, event, name))
        if nn["interval"] is None:
            L.append("            Interval: " + nn["reason"] + ".")
        else:
            L.append("            Interval: %s to %s (from the interval for the difference)." % (grouped(nn["interval"][0]), grouped(nn["interval"][1])))
    code = 0
    if reported_p is not None:
        text, value, places, relation = reported_p
        sign = {"eq": "=", "lt": "<", "gt": ">"}[relation]
        chi = chi_square_2x2(ka, na, kb, nb)
        if chi is None:
            reason = "one row or one column of the table is empty (no events at all, or nobody without one), so the chi-square statistic is undefined"
            res["p_value_check"] = {"reported_p": text, "relation": relation, "consistent": None, "verdict": "cannot_check", "reason": reason}
            L.append("  P VALUE  reported p %s %s. %s  %s." % (sign, text, CANNOT, reason))
            L.append("            This is not a pass. Say that the p value could not be checked against the counts.")
            code = 3
        else:
            tol = 0.5 * 10 ** (-places)

            def agrees(pv):
                if relation == "eq":
                    return abs(pv - value) <= tol * (1 + 1e-9)
                return pv < value if relation == "lt" else pv > value

            m1, m2 = agrees(chi["p_plain"]), agrees(chi["p_corrected"])
            which = "both" if (m1 and m2) else ("uncorrected" if m1 else ("continuity-corrected" if m2 else None))
            res["p_value_check"] = {"reported_p": text, "relation": relation, "chi_square": jnum(chi["plain"], 2), "p": float("%.4g" % chi["p_plain"]),
                                    "chi_square_with_continuity_correction": jnum(chi["corrected"], 2),
                                    "p_with_continuity_correction": float("%.4g" % chi["p_corrected"]),
                                    "consistent": bool(which), "verdict": "consistent" if which else "mismatch", "matches": which}
            L.append("  P VALUE  Pearson chi-square on these counts = %s (1 d.f.), p = %s; with the continuity correction %s, p = %s. Reported: p %s %s."
                     % (num(chi["plain"], 2), p_text(chi["p_plain"]), num(chi["corrected"], 2), p_text(chi["p_corrected"]), sign, text))
            if which:
                L.append("            CONSISTENT  with %s. That the figures agree does not show the test suited the design."
                         % ("both" if which == "both" else "the %s test" % which))
            else:
                L.append("            MISMATCH  neither chi-square gives the reported value at %d decimal place(s)." % places)
                L.append("            What would settle it: the test the paper names (Fisher's exact test and tests from a fitted or adjusted model")
                L.append("            are not computed here), whether it was one-sided, and the denominators it used. Check the extraction first.")
                L.append("            If the numbers are copied correctly, this is a finding: the paper disagrees with itself.")
                code = 1
            methods = methods + ["Pearson's chi-square for a two-by-two table, without and with the continuity correction, 1 degree of freedom"]
    L.append("  Methods: " + "; ".join(methods) + ".")
    L.append("  " + LIMIT)
    return code, {"command": "two-by-two", "level": level, "results": res, "methods": methods, "limit": LIMIT}, L


def cmd_proportion(opts):
    level = level_of(opts)
    k, n = events_and_total(opts, "--events", "--total")
    lo, hi = wilson(k, n, z_for(level))
    pp = places_for(n)
    res = {"events": k, "total": n, "percent": jnum(100 * k / n, pp), "interval_percent": [jnum(100 * lo, pp), jnum(100 * hi, pp)]}
    L = ["effect proportion (%d%% interval)" % level,
         "  %s of %s = %s%% (Wilson interval %s%% to %s%%)" % (grouped(k), grouped(n), pct(k / n, pp), num(100 * lo, pp), num(100 * hi, pp)),
         "  With %s in the denominator one person or item is worth %s percentage points." % (grouped(n), "%.2g" % (100.0 / n)),
         "  Method: " + METHODS["wilson"] + ".", "  " + LIMIT]
    return 0, {"command": "proportion", "level": level, "results": res, "methods": [METHODS["wilson"]], "limit": LIMIT}, L


def cmd_means(opts):
    level = level_of(opts)
    m1, s1, m2, s2 = (decimal(opts, k) for k in ("--mean1", "--sd1", "--mean2", "--sd2"))
    n1, n2 = whole(opts, "--n1", 2), whole(opts, "--n2", 2)
    if s1 < 0 or s2 < 0:
        raise Stop("a standard deviation cannot be negative")
    if s1 == 0 and s2 == 0:
        raise Stop("both standard deviations are zero, so there is no spread to build an interval from")
    dp = min(6, max(decimals_typed(opts[k]) for k in ("--mean1", "--sd1", "--mean2", "--sd2")))
    try:
        w = welch(m1, s1, n1, m2, s2, n2, level)
        d = cohen_d(m1, s1, n1, m2, s2, n2)
        usable = d is not None and all(math.isfinite(x) for x in list(w.values()) + [d])
    except (ZeroDivisionError, OverflowError, ValueError):
        usable = False
    if not usable:
        raise Stop("the standard deviations are too small beside the means for this arithmetic; check the figures")
    res = {"group_1": {"mean": m1, "sd": s1, "n": n1}, "group_2": {"mean": m2, "sd": s2, "n": n2},
           "difference": jnum(w["difference"], dp), "interval": [jnum(w["low"], dp), jnum(w["high"], dp)],
           "interval_includes_zero": w["low"] <= 0.0 <= w["high"], "degrees_of_freedom": jnum(w["df"], 1),
           "standardised_difference_d": None if d is None else jnum(d, 2), "pooled_sd": jnum(pooled_sd(s1, n1, s2, n2), dp + 1)}
    methods = [METHODS["welch"], METHODS["cohen"]]
    L = ["effect means (%d%% interval)" % level,
         "  Group 1: mean %s, SD %s, n %s" % (opts["--mean1"], opts["--sd1"], grouped(n1)),
         "  Group 2: mean %s, SD %s, n %s" % (opts["--mean2"], opts["--sd2"], grouped(n2)),
         "  DIFFERENCE  group 1 minus group 2 = %s (Welch interval %s to %s, %s degrees of freedom). The interval %s zero."
         % (num(w["difference"], dp), num(w["low"], dp), num(w["high"], dp), num(w["df"], 1),
            "includes" if w["low"] <= 0.0 <= w["high"] else "excludes"),
         "  STANDARDISED  d = %s: the difference is %s pooled standard deviations (pooled SD %s)."
         % (num(d, 2), num(abs(d), 2), num(pooled_sd(s1, n1, s2, n2), dp + 1)),
         "            d is a convention for comparing across scales. Whether the difference matters is judged in the",
         "            outcome's own units, against what a real change on that scale looks like.",
         "  Check that each spread is a standard deviation and not a standard error: a standard error entered here",
         "  makes d too large by about the square root of the group size.",
         "  Methods: " + "; ".join(methods) + ".", "  " + LIMIT]
    return 0, {"command": "means", "level": level, "results": res, "methods": methods, "limit": LIMIT}, L


def cmd_check_percent(opts):
    count, total = events_and_total(opts, "--count", "--total")
    reported = opts["--reported"].strip()
    if reported.endswith("%"):
        raise Stop("--reported takes the number as printed, without the percent sign")
    if not PERCENT.fullmatch(reported) or Fraction(reported) > 100:
        raise Stop("--reported must be a percentage from 0 to 100 written as the paper prints it, for example 31 or 30.8")
    r = percent_check(count, total, reported)
    show = max(2, r["places"] + 2)
    exact_text = "%.*f" % (show, float(r["exact"]))
    res = {"count": count, "total": total, "reported_percent": reported, "computed_percent": exact_text,
           "consistent": r["consistent"], "decimal_places_reported": r["places"],
           "truncation_matches": r["truncation_matches"], "counts_that_would_fit": r["counts_that_fit"]}
    L = ["effect check-percent", "  %s of %s = %s%%. Reported: %s%%." % (grouped(count), grouped(total), exact_text, reported)]
    if r["consistent"]:
        L.append("  CONSISTENT  the count gives the reported percentage at %d decimal place(s)." % r["places"])
    else:
        fits = r["counts_that_fit"]
        L.append("  MISMATCH  %s of %s rounds to %s%%, not %s%%." % (grouped(count), grouped(total), "%.*f" % (r["places"], float(r["exact"])), reported))
        if fits:
            L.append("            %s%% of %s would need a count of %s." % (reported, grouped(total), " or ".join(grouped(k) for k in fits)))
        else:
            L.append("            No whole count out of %s gives %s%%, so the percentage or the denominator is wrong." % (grouped(total), reported))
        if r["truncation_matches"]:
            L.append("            The figure matches if the percentage was cut short instead of rounded.")
        L.append("            Check the extraction first. If the numbers are copied correctly, this is a finding: the paper disagrees with itself.")
    return (0 if r["consistent"] else 1), {"command": "check-percent", "results": res}, L


def cmd_attrition(opts):
    level = level_of(opts)
    z = z_for(level)
    start, analysed = whole(opts, "--start", 1), whole(opts, "--analysed")
    if analysed > start:
        raise Stop("--analysed (%d) is larger than --start (%d), which is impossible" % (analysed, start))
    groups = []
    for spec in opts.get("--by-group", []):
        parts = spec.rsplit(":", 2)
        if len(parts) != 3 or not parts[0].strip() or not WHOLE.fullmatch(parts[1]) or not WHOLE.fullmatch(parts[2]):
            raise Stop("--by-group must look like NAME:START:ANALYSED with whole numbers, got %r" % spec[:40])
        name, gs, ga = parts[0].strip(), int(parts[1]), int(parts[2])
        if gs == 0:
            raise Stop("group %s starts with zero people" % name)
        if ga > gs:
            raise Stop("group %s has more analysed (%d) than started (%d), which is impossible" % (name, ga, gs))
        if name in [g["name"] for g in groups]:
            raise Stop("group %s is given twice" % name)
        groups.append({"name": name, "start": gs, "analysed": ga, "lost": gs - ga})
    lost = start - analysed
    pp = places_for(start)
    findings = []
    res = {"overall": {"start": start, "analysed": analysed, "lost": lost, "lost_percent": jnum(100 * lost / start, pp)}, "groups": [], "balance": None}
    L = ["effect attrition (%d%% interval)" % level,
         "  Overall: %s started, %s analysed: %s lost = %s%% of %s" % (grouped(start), grouped(analysed), grouped(lost), pct(lost / start, pp), grouped(start))]
    if groups:
        for g in groups:
            gp = places_for(g["start"])
            g["lost_percent"] = jnum(100 * g["lost"] / g["start"], gp)
            res["groups"].append(g)
            L.append("  %s: %s started, %s analysed: %s lost = %s%% of %s"
                     % (g["name"], grouped(g["start"]), grouped(g["analysed"]), grouped(g["lost"]), pct(g["lost"] / g["start"], gp), grouped(g["start"])))
        ts, ta = sum(g["start"] for g in groups), sum(g["analysed"] for g in groups)
        if ts != start:
            findings.append("the groups start with %s in all, but --start is %s" % (grouped(ts), grouped(start)))
        if ta != analysed:
            findings.append("the groups have %s analysed in all, but --analysed is %s" % (grouped(ta), grouped(analysed)))
    if len(groups) >= 2:
        ordered = sorted(groups, key=lambda g: g["lost"] / g["start"])
        low, high = ordered[0], ordered[-1]
        d, dlo, dhi = newcombe_difference(high["lost"], high["start"], low["lost"], low["start"], z)
        bp = places_for(min(high["start"], low["start"]))
        clear = not (dlo <= 0.0 <= dhi)
        res["balance"] = {"most_lost": high["name"], "least_lost": low["name"], "difference_percentage_points": jnum(100 * d, bp),
                          "interval_percentage_points": [jnum(100 * dlo, bp), jnum(100 * dhi, bp)], "unbalanced": clear,
                          "groups_compared": 2 if len(groups) == 2 else "the highest and lowest of %d" % len(groups)}
        L.append("  BALANCE  %s lost %s percentage points more than %s (Newcombe interval %s to %s): %s"
                 % (high["name"], num(100 * d, bp), low["name"], num(100 * dlo, bp), num(100 * dhi, bp),
                    "UNBALANCED. Loss differed between the groups." if clear else
                    "no clear imbalance. The interval includes zero, which is not proof the loss was balanced."))
        if len(groups) > 2:
            L.append("            Only the highest and lowest of %d groups are compared, which overstates the gap a little." % len(groups))
    else:
        res["balance"] = {"unbalanced": None, "reason": "balance cannot be judged without the loss in each group (--by-group)"}
        L.append("  BALANCE  cannot be judged without the loss in each group (--by-group NAME:START:ANALYSED).")
    res["findings"] = findings
    for f in findings:
        L.append("  MISMATCH  " + f + ". Check the extraction; if it is right, the paper's numbers disagree.")
    L.append("  Loss matters most when it differs between groups or is tied to the outcome. The counts cannot show the second; read why people left.")
    return (1 if findings else 0), {"command": "attrition", "level": level, "results": res, "methods": [METHODS["newcombe"]]}, L


def natural(risk):
    """Write a risk as 'x in N', N a power of ten from 100 up: the smallest N that makes x a whole
    number of at least 1, or failing that the smallest that makes x at least 1."""
    den, first = 100, None
    while den <= 10 ** 9:
        x = risk * den
        if x >= 1 - 1e-9:
            first = first or den
            if abs(x - round(x)) < 1e-9 * max(1.0, x):
                first = den
                break
            if den >= first * 1000:
                break
        den *= 10
    den = first or 10 ** 9
    x = risk * den
    text = ("%.3g" % x) if x < 1000 else grouped(int(round(x)))
    if "e" in text:
        text = grouped(int(round(float(text))))
    return text, den


def cmd_relative(opts):
    baseline = decimal(opts, "--baseline")
    if not 0 < baseline <= 1:
        raise Stop("--baseline is a risk and must be above 0 and at most 1 (for 2 in 1,000 write 0.002)")
    if baseline < 1e-9:
        raise Stop("--baseline is below one in a thousand million, too small for this arithmetic to mean anything")
    if ("--relative" in opts) == ("--percent-change" in opts):
        raise Stop("give exactly one of --relative (a ratio, 1.5 for 50 percent more) or --percent-change (50 or -40)")
    if "--relative" in opts:
        ratio = decimal(opts, "--relative")
    else:
        ratio = 1.0 + decimal(opts, "--percent-change") / 100.0
    if ratio < 0:
        raise Stop("the relative change takes the risk below zero, which is impossible")
    new = baseline * ratio
    if new > 1.0 + 1e-12:
        raise Stop("the baseline times the relative change is %.4g, a risk above 1, which is impossible" % new)
    new = min(new, 1.0)
    diff = new - baseline
    btext, den = natural(baseline)
    ntext = ("%.3g" % (new * den)) if new * den < 1000 else grouped(int(round(new * den)))
    dtext = ("%.3g" % (abs(diff) * den)) if abs(diff) * den < 1000 else grouped(int(round(abs(diff) * den)))
    change = 100 * (ratio - 1)
    word = "no change" if diff == 0 else "%.3g%% %s" % (abs(change), "higher" if change > 0 else "lower")
    if abs(diff) < 1e-12:
        diff = 0.0
    needed = None if diff == 0 else math.ceil(1.0 / abs(diff) - 1e-9)
    res = {"baseline_risk": baseline, "relative": float("%.6g" % ratio), "new_risk": float("%.6g" % new),
           "absolute_change": float("%.6g" % diff), "per": den, "baseline_per": float(btext.replace(",", "")),
           "new_per": float(ntext.replace(",", "")), "change_per": float(dtext.replace(",", "")) * (1 if diff >= 0 else -1),
           "absolute_change_percentage_points": float("%.3g" % (100 * diff)), "people_per_one_event_of_difference": needed}
    L = ["effect relative-to-absolute",
         "  Baseline: %s in %s" % (btext, grouped(den)),
         "  Relative change: times %.4g (%s)" % (ratio, word),
         "  After: %s in %s" % (ntext, grouped(den))]
    if diff == 0:
        L.append("  ABSOLUTE  no change.")
    else:
        L.append("  ABSOLUTE  %s %s per %s (%.3g percentage points): about one %s event for every %s people."
                 % (dtext, "more" if diff > 0 else "fewer", grouped(den), abs(100 * diff), "more" if diff > 0 else "fewer", grouped(needed)))
    L.append("  This is arithmetic on the two figures given. It is only as good as the baseline, which must come from the")
    L.append("  study's own comparison group or a stated source, for the same people over the same period.")
    return 0, {"command": "relative-to-absolute", "results": res}, L


def printed(opts, key):
    text = opts[key].strip()
    if not PRINTED.fullmatch(text):
        raise Stop("%s must be the number as printed, for example 5.19 or -0.4 (words, NaN and exponents are refused), got %r" % (key, text[:20]))
    return text, (len(text.split(".")[1]) if "." in text else 0)


def cannot(command, reason, given, lines, then="Record the missing figure as not reported (GAP)."):
    """A check that could not be made: exit 3, the words CANNOT CHECK, and consistent set to null."""
    L = lines + ["  %s  %s." % (CANNOT, reason), "            This is not a pass. " + then]
    return 3, {"command": command, "results": dict(given, consistent=None, verdict="cannot_check", reason=reason)}, L


def listed(values):
    values = [grouped(v) for v in values]
    return values[0] if len(values) == 1 else ", ".join(values[:-1]) + " or " + values[-1]


def cmd_check_mean(opts):
    text, places = printed(opts, "--mean")
    stated = Fraction(text)
    items = whole(opts, "--items", 1) if "--items" in opts else 1
    given = {"reported_mean": text, "decimal_places_reported": places, "items": items}
    head = ["effect check-mean"]
    if "--n" not in opts:
        return cannot("check-mean", "the sample size is needed and was not given. A mean cannot be tested against a sample size nobody states",
                      dict(given, n=None), head + ["  Reported mean: %s. Sample size: not given." % text])
    n = whole(opts, "--n", 1)
    if n > 10 ** 9 or items > 1000:
        raise Stop("--n above a thousand million or --items above 1,000 is not a study this check applies to")
    cells = n * items
    given.update(n=n, responses_in_the_mean=cells)
    head.append("  Reported mean: %s, from n = %s%s. The total of whole-number responses must itself be a whole number."
                % (text, grouped(n), "" if items == 1 else " people answering %d items (%s responses)" % (items, grouped(cells))))
    if cells >= 10 ** places:
        return cannot("check-mean", "with %s responses, means %s apart are possible, which is no coarser than the %d decimal place(s) printed, "
                      "so every printed value can arise and the test says nothing either way" % (grouped(cells), "%.3g" % (1.0 / cells), places),
                      given, head, "At this sample size the check has nothing to say about the mean, for or against.")
    slack = Fraction(1, 2 * 10 ** places)
    first = math.ceil((stated - slack) * cells)
    last = math.floor((stated + slack) * cells)
    fits = list(range(first, last + 1))
    below, above = math.floor(stated * cells), math.ceil(stated * cells)

    def exact_round(total):
        q = Fraction(total, cells) * 10 ** places
        nearest = math.floor(q + Fraction(1, 2))
        return "%.*f" % (places, float(Fraction(nearest, 10 ** places)))

    step = Fraction(1, 10 ** places)
    truncated = [t for t in (below, above) if (Fraction(t, cells) // step) * step == stated] if not fits else []
    near = []
    if not fits:
        for other in range(max(1, n - 3), n + 4):
            if other == n:
                continue
            oc = other * items
            if oc < 10 ** places and math.ceil((stated - slack) * oc) <= math.floor((stated + slack) * oc):
                near.append(other)
    res = dict(given, consistent=bool(fits), verdict="consistent" if fits else "mismatch", totals_that_fit=fits[:12],
               total_implied=float("%.6g" % float(stated * cells)),
               nearest_possible_means=sorted(set([exact_round(below), exact_round(above)])),
               truncation_matches=bool(truncated), nearby_sample_sizes_that_fit=near)
    if below == above:
        L = head + ["  %s x %s = %s, a whole number: %s/%s = %s." % (text, grouped(cells), grouped(below), grouped(below), grouped(cells), exact_round(below))]
    else:
        L = head + ["  %s x %s = %s, so the total would be %s or %s: %s/%s = %s and %s/%s = %s."
                    % (text, grouped(cells), "%.6g" % float(stated * cells), grouped(below), grouped(above), grouped(below), grouped(cells),
                       exact_round(below), grouped(above), grouped(cells), exact_round(above))]
    if fits:
        L.append("  CONSISTENT  a total of %s gives the reported mean at %d decimal place(s)." % (listed(fits[:4]), places))
        L.append("            This shows the mean is possible, not that it is right.")
    else:
        L.append("  MISMATCH  no whole total out of %s responses gives %s. The nearest possible means are %s."
                 % (grouped(cells), text, " and ".join(res["nearest_possible_means"])))
        if truncated:
            L.append("            The figure matches if the mean was cut short instead of rounded.")
        if near:
            L.append("            It would fit a sample size of %s." % listed(near))
        L.append("            This applies only if every response is a whole number. " + RESOLVE_MEAN)
        L.append("            Check the extraction first. If the numbers are copied correctly, this is a finding: the paper disagrees with itself.")
    L.append("  Method: " + METHODS["grim"] + ".")
    return (0 if fits else 1), {"command": "check-mean", "results": res, "methods": [METHODS["grim"]]}, L


def p_text(p):
    if p >= 0.0001:
        return "%.4f" % p
    return "%.2g" % p


def reported_p_of(raw, relation):
    """A p value as printed: returns (text, value, decimal places, relation)."""
    text = raw.strip()
    if text.lower().startswith("p") or text[:1] in "<>=":
        raise Stop("the reported p takes the number alone, as printed (0.045 or .045); say < or > with the relation option (lt or gt)")
    if not PVALUE.fullmatch(text) or Fraction(text) > 1:
        raise Stop("the reported p must be a p value from 0 to 1 as the paper prints it, for example 0.045 or .001, got %r" % text[:20])
    if relation not in ("eq", "lt", "gt"):
        raise Stop("the relation must be eq (p = x), lt (p < x) or gt (p > x)")
    return text, float(Fraction(text)), (len(text.split(".")[1]) if "." in text else 0), relation


def cmd_check_p(opts):
    test = opts["--test"].strip().lower()
    if test not in TESTS:
        raise Stop("--test must be one of %s" % ", ".join(TESTS))
    stat_text, sdp = printed(opts, "--statistic")
    stat = float(stat_text)
    if test in ("chi2", "f") and stat < 0:
        raise Stop("a %s statistic cannot be negative" % test)
    if abs(stat) > 1e6:
        raise Stop("--statistic is beyond a million, which this check does not handle")
    rep_text, _value, pdp, relation = reported_p_of(opts["--reported"], opts.get("--relation", "eq"))
    reported = Fraction(rep_text)
    tails_text = opts.get("--tails", "2")
    if tails_text not in ("1", "2"):
        raise Stop("--tails must be 1 or 2")
    tails = int(tails_text)
    if test in ("chi2", "f") and "--tails" in opts:
        raise Stop("--tails applies to t and z only; chi2 and f use the upper tail")
    dfs = {}
    for key in ("--df", "--df2"):
        if key in opts:
            v = decimal(opts, key)
            if not 0 < v <= 1e6:
                raise Stop("%s must be above 0 and at most a million" % key)
            dfs[key] = v
    if test == "z" and dfs:
        raise Stop("a z statistic has no degrees of freedom; leave out --df")
    if test != "f" and "--df2" in dfs:
        raise Stop("--df2 is the second degrees of freedom of an F statistic only")
    sign = {"eq": "=", "lt": "<", "gt": ">"}[relation]
    name = {"t": "t", "z": "z", "chi2": "chi-square", "f": "F"}[test]
    given = {"test": test, "statistic": stat_text, "df": dfs.get("--df"), "df2": dfs.get("--df2"), "reported_p": rep_text,
             "relation": relation, "tails": tails if test in ("t", "z") else None}
    head = ["effect check-p"]
    need = [k for k in (("--df",) if test in ("t", "chi2") else ("--df", "--df2") if test == "f" else ()) if k not in dfs]
    if need:
        return cannot("check-p", "%s %s needed and not given. A %s statistic has no p value without %s"
                      % (" and ".join(need), "is" if len(need) == 1 else "are", name, "it" if len(need) == 1 else "them"),
                      given, head + ["  Reported: %s = %s, p %s %s. Degrees of freedom: not given." % (name, stat_text, sign, rep_text)])
    df, df2 = dfs.get("--df", 0.0), dfs.get("--df2", 0.0)
    half = 0.5 * 10 ** (-sdp)
    lo_stat, hi_stat = max(0.0, abs(stat) - half), abs(stat) + half
    p_mid = p_from_statistic(test, stat, df, df2, tails)
    p_high = p_from_statistic(test, lo_stat, df, df2, tails)
    p_low = p_from_statistic(test, hi_stat, df, df2, tails)
    if not all(math.isfinite(x) and 0.0 <= x <= 1.0 for x in (p_mid, p_low, p_high)):
        raise Stop("the p value could not be computed for these figures; check the statistic and the degrees of freedom")
    tol = 0.5 * 10 ** (-pdp)
    r = float(reported)

    def agrees(low, high):
        if relation == "eq":
            return r - tol <= high * (1 + 1e-12) and r + tol >= low * (1 - 1e-12)
        if relation == "lt":
            return low < r
        return high > r

    ok = agrees(p_low, p_high)
    other = None
    if not ok and test in ("t", "z"):
        t2 = 1 if tails == 2 else 2
        o_low, o_high = (p_from_statistic(test, hi_stat, df, df2, t2), p_from_statistic(test, lo_stat, df, df2, t2))
        other = {"tails": t2, "p": float("%.4g" % p_from_statistic(test, stat, df, df2, t2)), "matches": agrees(o_low, o_high)}
    label = name + ("(%g)" % df if test in ("t", "chi2") else "(%g, %g)" % (df, df2) if test == "f" else "")
    side = None
    if relation == "eq" and not ok and ((r < 0.05) != (p_mid < 0.05)) and not (p_low < 0.05 <= p_high):
        side = "reported %s 0.05, recomputed %s" % ("below" if r < 0.05 else "at or above", "below" if p_mid < 0.05 else "at or above")
    res = dict(given, recomputed_p=float("%.4g" % p_mid), recomputed_p_range=[float("%.4g" % p_low), float("%.4g" % p_high)],
               consistent=ok, verdict="consistent" if ok else "mismatch", other_tails=other, side_of_0_05=side)
    kind = ("a two-sided" if tails == 2 else "a one-sided") if test in ("t", "z") else "an upper-tail"
    L = head + ["  %s = %s gives %s p of %s (%s to %s, allowing for the statistic having been rounded to %d decimal place(s))."
                % (label, stat_text, kind, p_text(p_mid), p_text(p_low), p_text(p_high), sdp),
                "  Reported: p %s %s." % (sign, rep_text)]
    if ok:
        L.append("  CONSISTENT  the reported p is what the statistic gives, at the precision printed.")
        L.append("            This shows the two figures agree, not that the right test was used.")
    else:
        L.append("  MISMATCH  the statistic as printed gives p %s to %s, which is not p %s %s." % (p_text(p_low), p_text(p_high), sign, rep_text))
        if other and other["matches"]:
            L.append("            A %s test would give p = %s, which matches. See whether the paper says the test was %s."
                     % ("one-sided" if other["tails"] == 1 else "two-sided", p_text(other["p"]), "one-sided" if other["tails"] == 1 else "two-sided"))
        if side:
            L.append("            The two fall on different sides of 0.05 (%s). Where the paper leans on that line, the difference matters." % side)
        L.append("            " + RESOLVE_P)
        L.append("            If the numbers are copied correctly, this is a finding: the paper disagrees with itself.")
    L.append("  Method: " + METHODS["pvalue"] + ".")
    return (0 if ok else 1), {"command": "check-p", "results": res, "methods": [METHODS["pvalue"]]}, L


COMMANDS = {"check-mean": cmd_check_mean, "check-p": cmd_check_p, "two-by-two": cmd_two_by_two, "proportion": cmd_proportion, "means": cmd_means, "check-percent": cmd_check_percent,
            "attrition": cmd_attrition, "relative-to-absolute": cmd_relative}


def say(text):
    """Print to standard output; a reader that closes the pipe early is not an error."""
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        say(__doc__)
        return 0 if argv else 2
    cmd = argv[0]
    if cmd not in SPEC:
        print("effect: unknown command %s (use %s)" % (cmd.encode("ascii", "replace").decode("ascii"), ", ".join(SPEC)), file=sys.stderr)
        return 2
    flag_names, value_names, required = SPEC[cmd]
    flags, opts, it = set(), {}, iter(argv[1:])
    for a in it:
        if a in flag_names:
            flags.add(a)
        elif a in value_names:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("effect: %s needs a value" % a, file=sys.stderr)
                return 2
            if a in REPEATABLE:
                opts.setdefault(a, []).append(v)
            elif a in opts:
                print("effect: %s is given twice" % a, file=sys.stderr)
                return 2
            else:
                opts[a] = v
        else:
            print("effect: unknown argument %s for %s" % (a.encode("ascii", "replace").decode("ascii"), cmd), file=sys.stderr)
            return 2
    missing = [k for k in required if k not in opts]
    if missing:
        print("effect: %s needs %s" % (cmd, ", ".join(missing)), file=sys.stderr)
        return 2
    try:
        code, payload, lines = COMMANDS[cmd](opts)
    except Stop as e:
        print("effect: " + str(e).encode("ascii", "replace").decode("ascii"), file=sys.stderr)
        return 2
    if "--json" in flags:
        text = json.dumps(payload, indent=1, ensure_ascii=True, allow_nan=False)
    else:
        text = "\n".join(lines).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
