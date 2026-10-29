#!/usr/bin/env python3
"""Score a prediction ledger. Standard library only. Reads one CSV file, changes nothing.

Usage:
  python brier.py LEDGER.csv [--today YYYY-MM-DD] [--by domain|made_by] [--json]

Ledger columns (header row required; extra columns are ignored):
  id            unique label
  date          when the prediction was made, YYYY-MM-DD exactly (20260115 and 2026/01/15 are rejected)
  statement     the claim, written so it can only be true or false
  probability   chance the statement is true: 0 to 1, or a percentage such as 70%
  resolve_by    when the outcome will be known, YYYY-MM-DD
  outcome       blank while pending; 1 or true if it happened; 0 or false if not; void if withdrawn
  domain        optional grouping
  made_by       optional: who made it (for example user, model)

What it prints:
  - rows rejected, with the reason (they are left out of every figure)
  - when any row is rejected, a PARTIAL RESULT line: how many of the file's resolved rows were
    scored. Every figure below that line covers the valid rows only. It is a diagnostic, not the
    ledger's score; fix the rejected rows and run again for a final figure. In --json the same
    fact is the "partial" flag with its counts.
  - Brier score over resolved rows: mean of (probability - outcome) squared. 0 is perfect, 0.25 is
    what always saying 50% scores, 1 is confidently wrong every time.
  - the score that always quoting this ledger's own base rate would have earned, for comparison
  - calibration by band: how often things said with 60 to 80% confidence actually happened
  - pending rows whose resolve_by date has passed

Small samples are flagged, not hidden: under 20 resolved rows overall, or under 10 in a band, the
figures are too noisy to read much into.

Exit code 0 when the ledger was read (even with rejected rows: check "partial", not the exit
code, to know whether the score is final). Exit 2 for bad arguments, an
unreadable file, a file that is not valid UTF-8 or not parseable as CSV, or missing columns. No
input should produce a traceback; if one does, that is a bug.
"""
import csv
import datetime
import json
import io
import math
import re
import sys

REQUIRED = ["id", "date", "statement", "probability", "resolve_by", "outcome"]
BANDS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
MIN_TOTAL, MIN_BAND = 20, 10


ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_date(s):
    """Accept YYYY-MM-DD only. Compact (20260301), slashed and partial dates are rejected."""
    s = (s or "").strip()
    if not ISO_DATE.fullmatch(s):
        return None
    try:
        return datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def parse_prob(s):
    s = (s or "").strip()
    if not s:
        return None
    pct = s.endswith("%")
    try:
        v = float(s[:-1] if pct else s)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    if pct:
        v /= 100.0
    return v if 0.0 <= v <= 1.0 else None


def parse_outcome(s):
    s = (s or "").strip().lower()
    if s == "":
        return "pending"
    if s in ("1", "true", "yes", "correct", "happened"):
        return 1
    if s in ("0", "false", "no", "incorrect", "did not happen"):
        return 0
    if s in ("void", "withdrawn", "n/a"):
        return "void"
    return None


def brier(rows):
    return sum((p - o) ** 2 for p, o in rows) / len(rows)


def summarise(rows):
    n = len(rows)
    if not n:
        return None
    base = sum(o for _p, o in rows) / n
    bs = brier(rows)
    ref = sum((base - o) ** 2 for _p, o in rows) / n
    bands = []
    for lo, hi in BANDS:
        inb = [(p, o) for p, o in rows if (lo <= p < hi) or (hi == 1.0 and p == 1.0)]
        if inb:
            bands.append({"band": "%d-%d%%" % (lo * 100, hi * 100), "n": len(inb),
                          "mean_forecast": round(sum(p for p, _o in inb) / len(inb), 3),
                          "observed": round(sum(o for _p, o in inb) / len(inb), 3),
                          "small_sample": len(inb) < MIN_BAND})
        else:
            bands.append({"band": "%d-%d%%" % (lo * 100, hi * 100), "n": 0})
    return {"n": n, "brier": round(bs, 4), "base_rate": round(base, 3), "base_rate_brier": round(ref, 4),
            "skill_vs_base_rate": (round(1 - bs / ref, 3) if ref > 0 else None),
            "small_sample": n < MIN_TOTAL, "bands": bands}


def load(path, today):
    try:
        with open(path, "rb") as bf:
            raw_bytes = bf.read()
    except OSError as e:
        return None, "cannot read %s: %s" % (path, e.strerror or e)
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        return None, "%s is not valid UTF-8 (byte %d). Save it as UTF-8 and run again" % (path, e.start)
    if "\x00" in text:
        return None, "%s contains NUL bytes; it is not a text CSV" % path
    try:
        return parse_rows(text, today)
    except csv.Error as e:
        return None, "%s could not be parsed as CSV: %s" % (path, e)


def parse_rows(text, today):
    rd = csv.DictReader(io.StringIO(text, newline=""))
    cols = [c.strip().lower() for c in (rd.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        return None, "missing column(s): " + ", ".join(missing)
    rows, rejected, seen = [], [], set()
    for lineno, raw in enumerate(rd, 2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
        if not any(r.values()):
            continue
        rid = r.get("id", "")
        why = []
        if not rid:
            why.append("no id")
        elif rid in seen:
            why.append("duplicate id")
        p = parse_prob(r.get("probability"))
        if p is None:
            why.append("probability %r is not a number from 0 to 1 or a percentage" % r.get("probability", ""))
        o = parse_outcome(r.get("outcome"))
        if o is None:
            why.append("outcome %r is not blank, 1, 0 or void" % r.get("outcome", ""))
        made, due = parse_date(r.get("date")), parse_date(r.get("resolve_by"))
        if made is None:
            why.append("date %r is not YYYY-MM-DD" % r.get("date", ""))
        if due is None:
            why.append("resolve_by %r is not YYYY-MM-DD" % r.get("resolve_by", ""))
        if made and due and due < made:
            why.append("resolve_by is before date")
        if not r.get("statement"):
            why.append("no statement")
        if why:
            state = "resolved" if o in (0, 1) else ("unreadable" if o is None else "not_resolved")
            rejected.append({"line": lineno, "id": rid, "reasons": why, "outcome_state": state})
            continue
        seen.add(rid)
        rows.append({"id": rid, "p": p, "outcome": o, "due": due, "statement": r["statement"],
                     "domain": r.get("domain", "") or "(none)", "made_by": r.get("made_by", "") or "(none)",
                     "overdue": o == "pending" and due < today})
    return {"rows": rows, "rejected": rejected}, None


def main(argv):
    args, today, as_json, by = [], datetime.date.today(), False, None
    it = iter(argv)
    for a in it:
        if a == "--json":
            as_json = True
        elif a == "--today":
            v = next(it, None)
            d = parse_date(v) if v else None
            if d is None:
                print("brier: --today needs a date as YYYY-MM-DD", file=sys.stderr)
                return 2
            today = d
        elif a == "--by":
            v = next(it, None)
            if v not in ("domain", "made_by"):
                print("brier: --by needs domain or made_by", file=sys.stderr)
                return 2
            by = v
        elif a.startswith("--"):
            print("brier: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    data, err = load(args[0], today)
    if err:
        print("brier: " + err, file=sys.stderr)
        return 2
    rows = data["rows"]
    resolved = [(r["p"], r["outcome"]) for r in rows if r["outcome"] in (0, 1)]
    rej = data["rejected"]
    rej_resolved = sum(1 for x in rej if x["outcome_state"] == "resolved")
    rej_unreadable = sum(1 for x in rej if x["outcome_state"] == "unreadable")
    partial = bool(rej)
    note = None
    if partial:
        note = ("PARTIAL RESULT: scored %d of %d resolved rows; %d row(s) rejected and listed "
                "(%d resolved, %d with an unreadable outcome, %d not resolved). This is not the ledger's score. "
                "Fix the rejected rows and rescore for a final figure."
                % (len(resolved), len(resolved) + rej_resolved, len(rej), rej_resolved, rej_unreadable,
                   len(rej) - rej_resolved - rej_unreadable))
    rep = {"today": today.isoformat(), "rows_read": len(rows) + len(rej), "rejected": rej,
           "partial": partial, "scored": len(resolved), "resolved_in_file": len(resolved) + rej_resolved,
           "rejected_resolved": rej_resolved, "rejected_outcome_unreadable": rej_unreadable, "partial_note": note,
           "resolved": len(resolved), "pending": sum(1 for r in rows if r["outcome"] == "pending"),
           "void": sum(1 for r in rows if r["outcome"] == "void"),
           "overdue": [{"id": r["id"], "resolve_by": r["due"].isoformat(), "statement": r["statement"][:100]} for r in rows if r["overdue"]],
           "overall": summarise(resolved), "groups": {}}
    if by:
        for key in sorted({r[by] for r in rows}):
            sub = [(r["p"], r["outcome"]) for r in rows if r[by] == key and r["outcome"] in (0, 1)]
            if sub:
                rep["groups"][key] = summarise(sub)
    if as_json:
        out = json.dumps(rep, indent=1, ensure_ascii=True)
    else:
        L = ["brier: %d row(s) read, %d rejected, %d resolved, %d pending, %d void, as of %s"
             % (rep["rows_read"], len(rep["rejected"]), rep["resolved"], rep["pending"], rep["void"], rep["today"])]
        for x in rep["rejected"]:
            L.append("  REJECTED line %d id %r: %s" % (x["line"], x["id"], "; ".join(x["reasons"])))
        if partial:
            L.append(note)

        def show(title, s):
            L.append("%s: n=%d  Brier %.4f  (always quoting the base rate of %.0f%% would score %.4f)%s"
                     % (title, s["n"], s["brier"], s["base_rate"] * 100, s["base_rate_brier"],
                        "  SMALL SAMPLE: under %d resolved, read loosely" % MIN_TOTAL if s["small_sample"] else ""))
            for b in s["bands"]:
                if b["n"]:
                    gap = b["observed"] - b["mean_forecast"]
                    lean = "about right" if abs(gap) < 0.1 else ("underconfident" if gap > 0 else "overconfident")
                    L.append("    said %-8s n=%-3d average forecast %3.0f%%  happened %3.0f%%  %s%s"
                             % (b["band"], b["n"], b["mean_forecast"] * 100, b["observed"] * 100,
                                "too few to call" if b["small_sample"] else lean, "" if not b["small_sample"] else " (n under %d)" % MIN_BAND))

        if rep["overall"]:
            show("Partial, valid rows only" if partial else "Overall", rep["overall"])
            for key, s in rep["groups"].items():
                show("  %s = %s" % (by, key), s)
        else:
            L.append("No valid resolved predictions. Nothing to score%s."
                     % (" until the rejected rows are fixed" if partial else " yet"))
        for x in rep["overdue"]:
            L.append("  OVERDUE %s was due %s: %s" % (x["id"], x["resolve_by"], x["statement"]))
        out = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
