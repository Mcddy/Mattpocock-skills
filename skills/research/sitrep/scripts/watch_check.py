#!/usr/bin/env python3
"""Validate one sitrep watch file. Standard library only. Reads the file, changes nothing.

Usage:
  python watch_check.py WATCH.json [--stale-days N] [--json]

WATCH.json (the full field list is in references/watch-file.md):
  {"watch_id": "kebab-case-id", "schema": 1, "title": "...", "purpose": "...",
   "requirements": [{"id": "R1", "question": "...", "priority": "high|medium|low"}],
   "indicators":   [{"id": "I1", "requirement": "R1", "watch_for": "...", "where": "...",
                     "would_mean": "...", "status": "not seen|seen|contradicted",
                     "seen_on": null, "evidence": [{"source_id": "S1", "note": "..."}]}],
   "sources":      [{"id": "S1", "title": "...", "address": "...",
                     "tier": "primary|peer_reviewed|secondary|aggregator|unverified",
                     "check": "each run|monthly",
                     "last_checked": "YYYY-MM-DD" or null,
                     "last_result": "reached|unreachable|not checked"}],
   "state":        [{"id": "F1", "requirement": "R1", "statement": "...",
                     "status": "FACT|REPORTED|ASSESSMENT|GAP", "source_ids": ["S1"],
                     "as_of": "YYYY-MM-DD"}],
   "withdrawn":    [{"id": "F9", "statement": "...", "withdrawn_on": "YYYY-MM-DD", "reason": "..."}],
   "runs":         [{"date": "YYYY-MM-DD", "summary": "...", "changes": 0}]}
"withdrawn", "last_checked" and "last_result" are optional. Everything else is required.

What it enforces (ERROR, exit 1):
  - the shape above: required fields present, text fields not empty, lists are lists
  - schema is the whole number 1 (true, "1" and 1.0 are refused; 2 is refused as newer)
  - watch_id is lower case with hyphens; every id is unique across the whole file
  - references resolve: an indicator's and a state item's requirement, every source id
  - every value is from its list (priority, tier, check, last_result, both status fields)
  - dates are real calendar dates written YYYY-MM-DD exactly; run dates do not go backwards;
    no as_of is later than the last run
  - a FACT has at least one source of secondary tier or better; a REPORTED item has a source
  - an indicator marked seen or contradicted has a seen_on date and at least one evidence
    entry; an indicator marked not seen has seen_on null
  - an id listed under withdrawn is not also in use in state
What it reports for a person to decide (ADVISORY):
  - an indicator worded as a trend with no threshold or observable event ("further
    deterioration", "increased activity")
  - a requirement with no indicator, or with no state item
  - a high-priority requirement whose state rests only on sources below secondary tier
  - fewer than two or more than five requirements
  - a source to check each run that has no address
  - a state item older than --stale-days (default 30) at the last run
  - fields this script does not read

It cannot tell whether a statement is true, whether a source says what the item claims, or
whether the indicators are the right ones. The indicator wording check is a word list: it can
miss a vague indicator and can flag a sound one.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = 1
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
KEBAB = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
ITEM_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}")
PRIORITIES = ("high", "medium", "low")
IND_STATUS = ("not seen", "seen", "contradicted")
TIERS = ("primary", "peer_reviewed", "secondary", "aggregator", "unverified")
GOOD_TIERS = ("primary", "peer_reviewed", "secondary")
CHECKS = ("each run", "monthly")
RESULTS = ("reached", "unreachable", "not checked")
STATE_STATUS = ("FACT", "REPORTED", "ASSESSMENT", "GAP")
KNOWN = {
    "top": {"watch_id", "schema", "title", "purpose", "requirements", "indicators", "sources", "state", "withdrawn", "runs"},
    "requirements": {"id", "question", "priority"},
    "indicators": {"id", "requirement", "watch_for", "where", "would_mean", "status", "seen_on", "evidence"},
    "sources": {"id", "title", "address", "tier", "check", "last_checked", "last_result", "note"},
    "state": {"id", "requirement", "statement", "status", "source_ids", "as_of", "editorial_reason"},
    "withdrawn": {"id", "statement", "withdrawn_on", "reason"},
    "runs": {"date", "summary", "changes"},
}
VAGUE = re.compile(
    r"\b(further|increas\w*|decreas\w*|deteriorat\w*|worsen\w*|improv\w*|grow\w*|heighten\w*|escalat\w*|"
    r"intensif\w*|significant\w*|notabl\w*|major|more|less|rising|falling|tensions?|activity|momentum|"
    r"concerns?|pressure|developments?|signs? of|any (?:change|news|update)s?|news|updates?|progress|"
    r"movement|shifts?|trend\w*)\b", re.I)
CONCRETE = re.compile(
    r"\d|\b(publish\w*|list(?:s|ed|ing)?|appears?|announc\w*|cit(?:e|es|ed|ing)|issu\w*|signed|"
    r"vot\w*|fil(?:e|es|ed|ing)|adopt\w*|releas\w*|withdraw\w*|repeal\w*|enters? into force|"
    r"nam(?:e|es|ed)|post(?:s|ed)?|records?|exceeds?)\b", re.I)
SINGULAR = {"requirements": "requirement", "indicators": "indicator", "sources": "source", "state": "state item"}
FLAGS = {"--json"}
VALUES = {"--stale-days"}


class InputError(Exception):
    """The file could not be read as UTF-8 JSON. Exit code 2."""


def parse_date(text):
    if not isinstance(text, str) or not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def text_ok(v):
    return isinstance(v, str) and bool(v.strip())


def load_json(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise InputError("cannot read %s: %s" % (path, e.strerror or e))
    if bytes([0]) in raw:
        raise InputError("%s contains NUL bytes; it is not a text file" % path)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise InputError("%s is not valid UTF-8 (first bad byte at offset %d)" % (path, e.start))

    def no_constant(name):
        raise ValueError("%s is not a number this script accepts" % name)

    def finite(s):
        v = float(s)
        if not math.isfinite(v):
            raise ValueError("%s is not a finite number" % s)
        return v

    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("the key %r appears twice in one object" % k)
            out[k] = v
        return out

    try:
        return json.loads(text, parse_constant=no_constant, parse_float=finite, object_pairs_hook=pairs)
    except ValueError as e:
        raise InputError("%s is not valid JSON (%s)" % (path, str(e)[:90]))


def last_run_date(d):
    """The date of the newest run, or None if the runs list cannot be read."""
    runs = d.get("runs") if isinstance(d, dict) else None
    if isinstance(runs, list) and runs and isinstance(runs[-1], dict):
        return parse_date(runs[-1].get("date"))
    return None


def validate_watch(d, stale_days=30):
    """Return (errors, advisories, facts). facts holds counts for the summary line."""
    errors, adv, facts = [], [], {}
    if not isinstance(d, dict):
        return ["the file must hold one JSON object"], [], {}

    def extra(kind, obj, where):
        unknown = sorted(k for k in obj if k not in KNOWN[kind])
        if unknown:
            adv.append("%s has field(s) this script does not read: %s" % (where, ", ".join(unknown)))

    def rows(key, required=True):
        v = d.get(key)
        if v is None and not required:
            return []
        if not isinstance(v, list):
            errors.append("%s must be a list" % key)
            return []
        good = []
        for i, x in enumerate(v):
            if isinstance(x, dict):
                good.append(x)
            else:
                errors.append("%s entry %d is not an object" % (key, i + 1))
        return good

    extra("top", d, "the watch file")
    wid = d.get("watch_id")
    if not isinstance(wid, str) or not KEBAB.fullmatch(wid):
        errors.append("watch_id must be lower case letters and digits joined by hyphens, for example port-fees-watch")
    sch = d.get("schema")
    if not is_int(sch):
        errors.append("schema must be the whole number %d (text, true and 1.0 are not accepted)" % SCHEMA)
    elif sch > SCHEMA:
        errors.append("schema %d is newer than this script reads (%d); use the script that came with that file" % (sch, SCHEMA))
    elif sch < SCHEMA:
        errors.append("schema %d is not a version this script knows; the only schema is %d" % (sch, SCHEMA))
    for key in ("title", "purpose"):
        if not text_ok(d.get(key)):
            errors.append("%s is missing or empty" % key)

    seen_ids = {}

    def take_id(obj, kind, n):
        i = obj.get("id")
        where = "%s entry %d" % (kind, n)
        if not isinstance(i, str) or not ITEM_ID.fullmatch(i):
            errors.append("%s: id must start with a letter and use letters, digits, hyphen or underscore" % where)
            return None, where
        where = "%s %s" % (SINGULAR[kind], i)
        if i in seen_ids:
            errors.append("id %s is used twice (%s and %s); every id must be unique across the file" % (i, seen_ids[i], kind))
            return None, where
        seen_ids[i] = kind
        return i, where

    # requirements
    reqs = {}
    for n, r in enumerate(rows("requirements"), 1):
        rid, where = take_id(r, "requirements", n)
        extra("requirements", r, where)
        if not text_ok(r.get("question")):
            errors.append("%s: question is missing or empty" % where)
        if r.get("priority") not in PRIORITIES:
            errors.append("%s: priority %r is not one of %s" % (where, r.get("priority"), ", ".join(PRIORITIES)))
        if rid:
            reqs[rid] = r
    if isinstance(d.get("requirements"), list) and not d["requirements"]:
        errors.append("requirements is empty; a watch needs at least one question whose answer could change")
    elif reqs and not 2 <= len(reqs) <= 5:
        adv.append("there are %d requirement(s); two to five is the working range for a watch run by hand" % len(reqs))

    # sources
    srcs = {}
    for n, s in enumerate(rows("sources"), 1):
        sid, where = take_id(s, "sources", n)
        extra("sources", s, where)
        if not text_ok(s.get("title")):
            errors.append("%s: title is missing or empty" % where)
        if not isinstance(s.get("address"), str):
            errors.append("%s: address must be text (empty text if no address was kept)" % where)
        elif not s["address"].strip() and s.get("check") == "each run":
            adv.append("%s is to be checked each run but has no address, so it cannot be looked up again" % where)
        if s.get("tier") not in TIERS:
            errors.append("%s: tier %r is not one of %s" % (where, s.get("tier"), ", ".join(TIERS)))
        if s.get("check") not in CHECKS:
            errors.append("%s: check %r is not one of %s" % (where, s.get("check"), ", ".join(CHECKS)))
        lc, lr = s.get("last_checked"), s.get("last_result")
        if lc is not None and parse_date(lc) is None:
            errors.append("%s: last_checked %r must be null or a real date written YYYY-MM-DD" % (where, lc))
        if lr is not None and lr not in RESULTS:
            errors.append("%s: last_result %r is not one of %s" % (where, lr, ", ".join(RESULTS)))
        if lr in ("reached", "unreachable") and lc is None:
            errors.append("%s: last_result is %r but last_checked is null; say when it was tried" % (where, lr))
        if sid:
            srcs[sid] = s

    # indicators
    inds = {}
    by_req_ind = {}
    for n, x in enumerate(rows("indicators"), 1):
        iid, where = take_id(x, "indicators", n)
        extra("indicators", x, where)
        if (not isinstance(x.get("requirement"), str) or x.get("requirement") not in reqs):
            errors.append("%s: requirement %r does not match any requirement id" % (where, x.get("requirement")))
        else:
            by_req_ind.setdefault(x["requirement"], []).append(iid)
        for key in ("watch_for", "where", "would_mean"):
            if not text_ok(x.get(key)):
                errors.append("%s: %s is missing or empty" % (where, key))
        st = x.get("status")
        if st not in IND_STATUS:
            errors.append("%s: status %r is not one of %s" % (where, st, ", ".join(IND_STATUS)))
        so = x.get("seen_on")
        if so is not None and parse_date(so) is None:
            errors.append("%s: seen_on %r must be null or a real date written YYYY-MM-DD" % (where, so))
        ev = x.get("evidence")
        good_ev = 0
        if not isinstance(ev, list):
            errors.append("%s: evidence must be a list (empty if there is none)" % where)
        else:
            for k, e in enumerate(ev, 1):
                if not isinstance(e, dict) or not text_ok(e.get("note")) or not isinstance(e.get("source_id"), str):
                    errors.append("%s: evidence entry %d must be an object with a source_id and a note" % (where, k))
                elif e["source_id"] not in srcs:
                    errors.append("%s: evidence entry %d names source %r, which is not in sources" % (where, k, e["source_id"]))
                else:
                    good_ev += 1
        if st in ("seen", "contradicted"):
            if so is None:
                errors.append("%s is marked %s but has no seen_on date" % (where, st))
            if isinstance(ev, list) and good_ev == 0:
                errors.append("%s is marked %s with no evidence; an indicator changes status only on something a source shows" % (where, st))
        elif st == "not seen" and so is not None:
            errors.append("%s is marked not seen but has a seen_on date; one of the two is wrong" % where)
        wf = x.get("watch_for")
        if text_ok(wf) and VAGUE.search(wf) and not CONCRETE.search(wf):
            adv.append("%s may not be observable as written (%r): name the event or the threshold that would be seen" % (where, " ".join(wf.split())[:70]))
        if iid:
            inds[iid] = x

    # runs
    run_dates = []
    for n, r in enumerate(rows("runs"), 1):
        where = "run %d" % n
        extra("runs", r, where)
        rd = parse_date(r.get("date"))
        if rd is None:
            errors.append("%s: date %r must be a real date written YYYY-MM-DD" % (where, r.get("date")))
        else:
            if run_dates and rd < run_dates[-1]:
                errors.append("%s: date %s is earlier than the run before it" % (where, r["date"]))
            run_dates.append(rd)
        if not text_ok(r.get("summary")):
            errors.append("%s: summary is missing or empty" % where)
        if not is_int(r.get("changes")) or r["changes"] < 0:
            errors.append("%s: changes must be a whole number, zero or more (text and true are not accepted)" % where)
    if isinstance(d.get("runs"), list) and not d["runs"]:
        errors.append("runs is empty; record the baseline run")
    last = run_dates[-1] if run_dates and len(run_dates) == len(d.get("runs", [])) else None

    # state
    state = {}
    by_req_state = {}
    counts = dict.fromkeys(STATE_STATUS, 0)
    for n, f in enumerate(rows("state"), 1):
        fid, where = take_id(f, "state", n)
        extra("state", f, where)
        if (not isinstance(f.get("requirement"), str) or f.get("requirement") not in reqs):
            errors.append("%s: requirement %r does not match any requirement id" % (where, f.get("requirement")))
        else:
            by_req_state.setdefault(f["requirement"], []).append(f)
        if not text_ok(f.get("statement")):
            errors.append("%s: statement is missing or empty" % where)
        st = f.get("status")
        if st not in STATE_STATUS:
            errors.append("%s: status %r is not one of %s" % (where, st, ", ".join(STATE_STATUS)))
        else:
            counts[st] += 1
        sids = f.get("source_ids")
        tiers = []
        if not isinstance(sids, list) or not all(isinstance(x, str) for x in sids):
            errors.append("%s: source_ids must be a list of source ids (empty if there is none)" % where)
        else:
            for x in sids:
                if x not in srcs:
                    errors.append("%s: source %r is not in sources" % (where, x))
                else:
                    tiers.append(srcs[x].get("tier"))
            if st == "FACT" and not any(t in GOOD_TIERS for t in tiers):
                errors.append("%s is a FACT with no source of secondary tier or better attached; attach one or mark it REPORTED" % where)
            if st == "REPORTED" and not sids:
                errors.append("%s is REPORTED with no source; say who reports it, or mark it ASSESSMENT or GAP" % where)
        ao = parse_date(f.get("as_of"))
        if ao is None:
            errors.append("%s: as_of %r must be a real date written YYYY-MM-DD" % (where, f.get("as_of")))
        elif last is not None:
            if ao > last:
                errors.append("%s: as_of %s is later than the last run (%s)" % (where, f["as_of"], last.isoformat()))
            elif (last - ao).days > stale_days:
                adv.append("%s was last confirmed %d days before the last run (as of %s); the limit set is %d days" % (where, (last - ao).days, f["as_of"], stale_days))
        if fid:
            state[fid] = f

    # withdrawn
    for n, w in enumerate(rows("withdrawn", required=False), 1):
        where = "withdrawn entry %d" % n
        extra("withdrawn", w, where)
        i = w.get("id")
        if not isinstance(i, str) or not ITEM_ID.fullmatch(i):
            errors.append("%s: id is missing or not an id" % where)
        elif i in seen_ids:
            errors.append("%s: id %s is listed as withdrawn and is also in use (%s); ids are never reused" % (where, i, seen_ids[i]))
        else:
            seen_ids[i] = "withdrawn"
        if not text_ok(w.get("statement")):
            errors.append("%s: statement is missing or empty" % where)
        if parse_date(w.get("withdrawn_on")) is None:
            errors.append("%s: withdrawn_on %r must be a real date written YYYY-MM-DD" % (where, w.get("withdrawn_on")))
        if not text_ok(w.get("reason")):
            errors.append("%s: reason is missing or empty" % where)

    # advisories that need the whole picture
    for rid, r in reqs.items():
        if rid not in by_req_ind:
            adv.append("requirement %s has no indicator; nothing observable would show its answer changing" % rid)
        items = by_req_state.get(rid, [])
        if not items:
            adv.append("requirement %s has no state item; record what is known, or a GAP" % rid)
        elif r.get("priority") == "high":
            cited = [srcs[x].get("tier") for f in items if isinstance(f.get("source_ids"), list) for x in f["source_ids"] if x in srcs]
            if cited and not any(t in GOOD_TIERS for t in cited):
                adv.append("high-priority requirement %s rests only on sources below secondary tier (%s); find a better source or say so in the sitrep"
                           % (rid, ", ".join(sorted(set(cited)))))
    facts.update({"watch_id": wid if isinstance(wid, str) else "", "requirements": len(reqs), "indicators": len(inds), "sources": len(srcs),
                  "state": len(state), "status_counts": counts, "runs": len(run_dates), "last_run": last.isoformat() if last else None})
    return errors, adv, facts


def parse_args(argv, name, flags, values, n_paths):
    """Strict parsing. Returns (flags, options, paths) or raises SystemExit(2) after one stderr line."""
    got, opts, paths, it = set(), {}, [], iter(argv)
    for a in it:
        if a in flags:
            got.add(a)
        elif a in values:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("%s: %s needs a value" % (name, a), file=sys.stderr)
                raise SystemExit(2)
            opts[a] = v
        elif a.startswith("--"):
            print("%s: unknown option %s" % (name, a), file=sys.stderr)
            raise SystemExit(2)
        else:
            paths.append(a)
    if len(paths) != n_paths:
        print("%s: expected %d file(s), got %d. Run with no arguments to see the usage." % (name, n_paths, len(paths)), file=sys.stderr)
        raise SystemExit(2)
    return got, opts, paths


def whole_days(text, name):
    if not re.fullmatch(r"\d{1,5}", text or ""):
        print("%s: --stale-days needs a whole number of days, zero or more" % name, file=sys.stderr)
        raise SystemExit(2)
    return int(text)


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    flags, opts, paths = parse_args(argv, "watch_check", FLAGS, VALUES, 1)
    stale = whole_days(opts.get("--stale-days", "30"), "watch_check")
    try:
        d = load_json(paths[0])
    except InputError as e:
        print("watch_check: %s" % e, file=sys.stderr)
        return 2
    errors, adv, facts = validate_watch(d, stale)
    if "--json" in flags:
        emit(json.dumps({"errors": errors, "advisories": adv, "summary": facts}, indent=1, ensure_ascii=True))
        return 1 if errors else 0
    c = facts.get("status_counts", {})
    L = ["watch_check: %s: %d requirement(s), %d indicator(s), %d source(s), %d state item(s), %d run(s), last run %s"
         % (facts.get("watch_id") or "(no id)", facts.get("requirements", 0), facts.get("indicators", 0), facts.get("sources", 0),
            facts.get("state", 0), facts.get("runs", 0), facts.get("last_run") or "not readable")]
    if c:
        L.append("  state: %d FACT, %d REPORTED, %d ASSESSMENT, %d GAP" % (c["FACT"], c["REPORTED"], c["ASSESSMENT"], c["GAP"]))
    L += ["  ERROR     " + m for m in errors]
    L += ["  ADVISORY  " + m for m in adv]
    L.append("RESULT: %s. %d error(s), %d advisory note(s). This checks the form of the watch file, not whether its statements are true."
             % ("FAIL" if errors else "PASS", len(errors), len(adv)))
    emit("\n".join(L))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
