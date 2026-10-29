#!/usr/bin/env python3
"""Work an Analysis of Competing Hypotheses matrix. Standard library only.

Usage:
  python ach.py MATRIX.csv [--weights high=1,medium=0.6,low=0.3] [--json]

MATRIX.csv has one row per item of evidence or argument:
  evidence      a short label and description
  credibility   high | medium | low   (how far the item itself can be trusted; optional, default medium)
  relevance     high | medium | low   (how much it bears on the question; optional, default medium)
  one column per hypothesis, named as you like (H1 ..., H2 ...), each cell one of:
    CC  very consistent      C  consistent      N  neutral or not applicable
    I   inconsistent         II very inconsistent      ?  not yet assessed

Incomplete rows. A row with ? in any cell is incomplete. The whole row is left out: it adds to no
tally (not even under the hypotheses it does rate), it is not used in the sensitivity test, and it
plays no part in judging which hypotheses are separated. Comparing hypotheses on a row that rates
only some of them would count evidence against one and silence about another as a difference. Each
incomplete row is listed as NOT ASSESSED: rate it before relying on the ranking. The output says
how many rows of how many were complete.

What it does, on the complete rows:
  1. Marks items that are not diagnostic: the same rating under every hypothesis. Such an item
     cannot help choose between them, however striking it is.
  2. For each hypothesis, tallies the evidence against it: an unweighted count of I and II, and a
     weighted score (II counts double; each item scaled by its credibility and relevance).
  3. Tests sensitivity: removes each diagnostic item in turn and reports whether the
     least-contradicted hypothesis changes. It also compares the unweighted and weighted orderings.
  4. Lists pairs of hypotheses the evidence does not separate, and hypotheses with nothing against
     them, which have not been tested rather than confirmed.
  5. Gives one verdict, and every line of the summary is written from it:
       stable leader   one hypothesis has the least against it under every weighting tried and
                       with any single diagnostic item removed
       stable tie      the same two or more hypotheses share the top under all of those
       not stable      the top changes with the weighting or with one item removed
       no basis        there is no complete diagnostic row, so there is no ordering at all
     In --json: "verdict" holds one of those four; "leader" is a hypothesis name only for
     "stable leader" and null otherwise; "ordering_stable" is true, false, or null for "no basis".
     Under "no basis" the least-contradicted lists are empty and "not_separated" is null (not
     judged), because nothing has been compared; the report then prints the tallies, the verdict
     and the rows set aside, and nothing about leaders, sensitivity or separation.

What it does not do, on purpose:
  It never outputs a probability or a percentage. A count of inconsistencies is not a likelihood:
  items are not independent, not equally important, and one solid disproof outweighs many weak
  points. The weights are a convenience and are arbitrary; the script shows whether the ordering
  survives changing them, and that is the only use to make of them. The ratings are the analyst's
  judgements. The matrix organises that judgement; it does not replace it or dictate the conclusion.

Method: R. J. Heuer, Psychology of Intelligence Analysis (1999), chapter 8.

Exit codes: 0 the matrix was worked. 2 bad arguments or an unusable matrix.
"""
import csv
import io
import json
import sys
from pathlib import Path

RATINGS = {"CC": 0, "C": 0, "N": 0, "I": 1, "II": 2}
KIND = {"CC": "for", "C": "for", "N": "neutral", "I": "against", "II": "against"}
LEVELS = ("high", "medium", "low")
DEFAULT_W = {"high": 1.0, "medium": 0.6, "low": 0.3}
FLAGS = {"--json"}
VALUES = {"--weights"}
META = ("evidence", "credibility", "relevance")


def parse_weights(text):
    w = dict(DEFAULT_W)
    for part in text.split(","):
        if "=" not in part:
            return None, "weights look like high=1,medium=0.6,low=0.3"
        k, v = part.split("=", 1)
        k = k.strip().lower()
        if k not in LEVELS:
            return None, "unknown weight name %r" % k
        try:
            f = float(v)
        except ValueError:
            return None, "weight %r is not a number" % v
        if not (f == f and 0 < f <= 10):
            return None, "weights must be greater than 0 and at most 10"
        w[k] = f
    if not (w["high"] >= w["medium"] >= w["low"]):
        return None, "weights must not increase from high to low"
    return w, None


def load(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        return None, None, "cannot read %s: %s" % (path, e.strerror or e)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, None, "%s is not valid UTF-8" % path
    if "\x00" in text:
        return None, None, "%s contains NUL bytes; is it really a CSV file?" % path
    try:
        reader = csv.reader(io.StringIO(text, newline=""))
        table = [[c.strip() for c in row] for row in reader if any(c.strip() for c in row)]
    except csv.Error as e:
        return None, None, "%s could not be parsed as CSV (%s)" % (path, e)
    if len(table) < 2:
        return None, None, "the matrix needs a header row and at least one evidence row"
    header = table[0]
    low = [h.lower() for h in header]
    if "evidence" not in low:
        return None, None, 'the matrix needs an "evidence" column'
    if len(set(low)) != len(low):
        return None, None, "two columns have the same name"
    hyps = [h for h in header if h.lower() not in META]
    if len(hyps) < 2:
        return None, None, "the matrix needs at least two hypothesis columns; one hypothesis cannot compete"
    items = []
    for n, row in enumerate(table[1:], start=2):
        if len(row) != len(header):
            return None, None, "line %d has %d cells; the header has %d" % (n, len(row), len(header))
        rec = dict(zip(low, row))
        if not rec["evidence"]:
            return None, None, "line %d has no evidence label" % n
        item = {"label": rec["evidence"], "ratings": {}}
        for col in ("credibility", "relevance"):
            v = (rec.get(col) or "medium").lower()
            if v not in LEVELS:
                return None, None, "line %d: %s %r is not high, medium or low" % (n, col, rec.get(col))
            item[col] = v
        for h in hyps:
            v = rec[h.lower()].upper()
            if v not in RATINGS and v != "?":
                return None, None, "line %d: rating %r under %r is not one of CC, C, N, I, II or ?" % (n, rec[h.lower()], h)
            item["ratings"][h] = v
        items.append(item)
    labels = [i["label"] for i in items]
    if len(set(labels)) != len(labels):
        return None, None, "two evidence rows have the same label"
    return hyps, items, None


def complete(item):
    """A row counts only if every hypothesis has a rating. One ? makes the whole row incomplete."""
    return "?" not in item["ratings"].values()


def tally(hyps, items, w):
    """Evidence against each hypothesis, from complete rows only. An incomplete row adds nothing,
    even under the hypotheses it does rate."""
    out = {}
    rows = [it for it in items if complete(it)]
    for h in hyps:
        count, score = 0, 0.0
        for it in rows:
            r = it["ratings"][h]
            count += 1 if RATINGS[r] else 0
            score += RATINGS[r] * w[it["credibility"]] * w[it["relevance"]]
        out[h] = {"against_count": count, "against_weighted": round(score, 3)}
    return out


def leaders(t, key):
    best = min(v[key] for v in t.values())
    return sorted(h for h, v in t.items() if abs(v[key] - best) < 1e-9)


VERDICTS = ("stable leader", "stable tie", "not stable", "no basis")


def analyse(hyps, items, w):
    assessed = [it for it in items if complete(it)]
    unassessed = [it["label"] for it in items if not complete(it)]
    nondiag = [it["label"] for it in assessed if len(set(it["ratings"].values())) == 1]
    weak_diag = [it["label"] for it in assessed if it["label"] not in nondiag and len({KIND[r] for r in it["ratings"].values()}) == 1]
    diag = [it for it in assessed if it["label"] not in nondiag]
    t = tally(hyps, assessed, w)
    alt_weights = (("all items equal", {"high": 1.0, "medium": 1.0, "low": 1.0}),
                   ("low-credibility items nearly ignored", {"high": 1.0, "medium": 0.5, "low": 0.05}))
    r = {"hypotheses": hyps, "items": len(items), "rows_total": len(items), "rows_complete": len(assessed),
         "rows_diagnostic": len(diag), "tallies": t, "not_diagnostic": nondiag, "weakly_diagnostic": weak_diag,
         "not_assessed": unassessed, "nothing_against": [h for h in hyps if t[h]["against_count"] == 0], "weights_used": w}
    if not diag:
        # Nothing complete tells the hypotheses apart, so nothing is ordered, tested or separated.
        r.update({"least_contradicted_unweighted": [], "least_contradicted_weighted": [],
                  "other_weightings": [{"weights": name, "least_contradicted": []} for name, _ in alt_weights],
                  "sensitive_to": [], "not_separated": None, "ordering_stable": None, "leader": None, "verdict": "no basis"})
        r["verdict_text"] = verdict_text(r)
        return r
    lead_c, lead_w = leaders(t, "against_count"), leaders(t, "against_weighted")
    sens = []
    for it in diag:
        rest = [x for x in assessed if x is not it]
        t2 = tally(hyps, rest, w)
        lc, lw = leaders(t2, "against_count"), leaders(t2, "against_weighted")
        if lc != lead_c or lw != lead_w:
            sens.append({"without": it["label"], "credibility": it["credibility"], "least_contradicted_unweighted": lc, "least_contradicted_weighted": lw})
    unsep = []
    for i, a in enumerate(hyps):
        for b in hyps[i + 1:]:
            if all(KIND[it["ratings"][a]] == KIND[it["ratings"][b]] for it in diag):
                unsep.append([a, b])
    alt_orders = [{"weights": name, "least_contradicted": leaders(tally(hyps, assessed, alt), "against_weighted")} for name, alt in alt_weights]
    stable = lead_c == lead_w and all(a["least_contradicted"] == lead_w for a in alt_orders) and not sens
    # The one place the verdict is decided. Everything a person reads is written from it.
    # A sole leader cannot also sit in a not-separated pair (alike in direction on every diagnostic
    # row means an equal count against), but that is checked here, not assumed: if it ever happened
    # the answer would be "not stable", never a leader.
    if stable and len(lead_w) > 1:
        verdict = "stable tie"
    elif stable and not any(lead_w[0] in pair for pair in unsep):
        verdict = "stable leader"
    else:
        verdict = "not stable"
        stable = False
    r.update({"least_contradicted_unweighted": lead_c, "least_contradicted_weighted": lead_w, "other_weightings": alt_orders,
              "sensitive_to": sens, "not_separated": unsep, "ordering_stable": stable,
              "leader": lead_w[0] if verdict == "stable leader" else None, "verdict": verdict})
    r["verdict_text"] = verdict_text(r)
    return r


def verdict_text(r):
    """The summary sentence for each verdict. No other code states who leads or whether it holds."""
    v = r["verdict"]
    if v == "no basis":
        s = ("NO BASIS for an ordering: no complete row tells the hypotheses apart, so there is no leader and no "
             "judgement on which hypotheses are separated.")
    elif v == "stable leader":
        s = "The ordering at the top holds: %s has the least against it under every weighting tried and with any single diagnostic item removed." % r["leader"]
    elif v == "stable tie":
        s = ("No single leader: %s are level, with the least against them, under every weighting tried and with any single "
             "diagnostic item removed. The matrix does not choose between them." % ", ".join(r["least_contradicted_weighted"]))
    else:
        s = ("The ordering at the top is NOT stable: it changes with the weighting or with one item removed. "
             "Do not report a leading hypothesis without saying what it depends on.")
    s += " %d of %d row(s) complete." % (r["rows_complete"], r["rows_total"])
    if r["not_assessed"]:
        s += " %d not assessed: rate before relying on the ranking." % len(r["not_assessed"])
    return s


def render(r):
    """The human-readable report. Which sections appear is decided by r["verdict"] alone."""
    hyps, v = r["hypotheses"], r["verdict"]
    L = ["ach: %d hypotheses, %d row(s) of evidence: %d complete, %d not assessed; of the complete rows %d diagnostic, %d not diagnostic"
         % (len(hyps), r["rows_total"], r["rows_complete"], len(r["not_assessed"]), r["rows_diagnostic"], len(r["not_diagnostic"]))]
    L.append("Evidence against each hypothesis, from the %d complete row(s) (a ranking aid; NOT a probability):" % r["rows_complete"])
    for h in sorted(hyps, key=lambda x: (r["tallies"][x]["against_weighted"], r["tallies"][x]["against_count"])):
        L.append("  %-44s against: %d item(s), weighted %.2f" % (h[:44], r["tallies"][h]["against_count"], r["tallies"][h]["against_weighted"]))
    if v != "no basis":
        L.append("Least contradicted: %s (count)  |  %s (weighted)" % (", ".join(r["least_contradicted_unweighted"]), ", ".join(r["least_contradicted_weighted"])))
        for a in r["other_weightings"]:
            L.append("  with %s: %s" % (a["weights"], ", ".join(a["least_contradicted"])))
    L.append(r["verdict_text"])
    if v != "no basis":
        for s in r["sensitive_to"]:
            L.append("  SENSITIVE  without %r (%s credibility): least contradicted by count %s; weighted %s"
                     % (s["without"][:44], s["credibility"], ", ".join(x.split(" ")[0] for x in s["least_contradicted_unweighted"]),
                        ", ".join(x.split(" ")[0] for x in s["least_contradicted_weighted"])))
        for a, b in r["not_separated"]:
            L.append("  NOT SEPARATED  %s and %s are rated alike on every diagnostic item. Find evidence that would differ between them." % (a[:30], b[:30]))
        for h in r["nothing_against"]:
            L.append("  UNTESTED  nothing is rated against %s in any complete row. That is absence of a test, not confirmation." % h[:40])
    for e in r["not_diagnostic"]:
        L.append("  NOT DIAGNOSTIC  %r has the same rating under every hypothesis; set it aside." % e[:60])
    for e in r["weakly_diagnostic"]:
        L.append("  WEAK  %r differs only in strength, not direction." % e[:60])
    for e in r["not_assessed"]:
        L.append("  NOT ASSESSED  %r: rate before relying on the ranking. A row with ? in any cell is left out of every tally, "
                 "the sensitivity test and the separation judgement." % e[:60])
    L.append("The ratings are your judgements. This arranges them; it does not decide. No percentage follows from a count.")
    return "\n".join(L).encode("ascii", "replace").decode("ascii")


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("ach: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("ach: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    w = dict(DEFAULT_W)
    if "--weights" in opts:
        w, err = parse_weights(opts["--weights"])
        if err:
            print("ach: " + err, file=sys.stderr)
            return 2
    hyps, items, err = load(args[0])
    if err:
        print("ach: " + err, file=sys.stderr)
        return 2
    r = analyse(hyps, items, w)
    if "--json" in flags:
        text = json.dumps(r, indent=1, ensure_ascii=True, allow_nan=False)
    else:
        text = render(r)
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
