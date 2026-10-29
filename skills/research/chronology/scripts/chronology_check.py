#!/usr/bin/env python3
"""Check a sourced timeline and report its order, conflicts and gaps. Standard library only.

Usage:
  python chronology_check.py EVENTS.csv SOURCES.csv [--gap-days N] [--approx-days N]
                             [--before A B]... [--today YYYY-MM-DD] [--json]

EVENTS.csv columns (the header row must name all of them; order is free):
  event_id, date, date_precision, end_date, time, title, detail, actors, source_id, locator,
  status, conflicts_with, tags
SOURCES.csv columns, the research ledger's format:
  source_id, title, publisher, address, tier, published, accessed, read_level, family, notes

How a date is written. The date carries exactly the precision its source gave, and no more:
  day      2024-03-19     the source gives the day
  month    2024-03        the source gives the month only. 2024-03-01 is refused
  year     2024           the source gives the year only
  approx   2024-03-19, 2024-03 or 2024    "about" that day, month or year, for example a relative
                          date ("three weeks later") resolved from a dated anchor
  undated  (blank)        the source gives no date. Listed separately and never placed
end_date is blank or a date in any of the three forms. time is blank or HH:MM followed by a zone:
UTC, Z, an offset such as +02:00, or the word local when the source names no zone. source_id,
actors, tags and conflicts_with are lists separated by semicolons. Each entry in conflicts_with is
an event id, optionally followed by a colon and a class: precision, timezone, announcement or
disagreement.

What it enforces (ERROR, exit 1):
  - every column present; ids unique; every source id and conflict id resolves
  - a date written to match its stated precision; real calendar dates; an end not before its start;
    a time only on a day-precision date
  - values from their lists (precision, status, tier, conflict class)
  - a FACT has a locator and at least one source that is of secondary tier or better and was
    opened (read_level full or section). A REPORTED row has a source. An ASSESSMENT has a source
    or says its basis in detail
  - a conflict is recorded on both rows, with the same class on both
  - a pair classed precision has dates that could both be right; a pair classed timezone does not
    differ by more than a day, and names the same instant where both rows record a time and offset
  - every --before assertion that the dates contradict (reported as VIOLATED)
What it reports for a person to decide (ADVISORY):
  - conflicts with no class, with what the dates allow; a pair classed disagreement whose dates are
    compatible; rows with the same title and different dates that are not marked as conflicting
  - events whose only source is below secondary tier; sources with no address; unused sources;
    a read_level it does not know
  - events dated after --today (scheduled, not yet happened)
  - a pair whose recorded instants run against the order of their written dates
  - --before assertions that cannot be decided at the recorded precision (UNDECIDED)

Order. Events are listed by the earliest day the written date could be. On a tie the less precise
date comes first, then an untimed event before a timed one, then clock time as written, then file
order. An approximate date is listed at the date written. This order is for reading. It is not a
claim about sequence: only --before answers that, and it answers UNDECIDED whenever the two
dates' possible ranges overlap.

Windows. A month covers its first to last day and a year its first to last day. An approximate day
is widened by --approx-days each side (default 15), an approximate month by one month each side,
an approximate year by one year each side. These widths are a convention for deciding what may be
called decided. They are not a claim about the source.

Gaps. A gap is a stretch in which no listed event can fall: from the latest day any earlier event
could be to the earliest day any later event could be. Gaps longer than --gap-days (default 90)
are listed with "at least" the certain length.

It cannot tell whether a source says what a row claims, whether two rows describe the same event,
whether a gap matters, or why anything happened.

Exit codes: 0 no errors and no violated assertion. 1 otherwise. 2 bad arguments or unreadable input.
"""
import calendar
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

EVENT_COLS = ["event_id", "date", "date_precision", "end_date", "time", "title", "detail", "actors", "source_id", "locator",
              "status", "conflicts_with", "tags"]
SOURCE_COLS = ["source_id", "title", "publisher", "address", "tier", "published", "accessed", "read_level", "family", "notes"]
PRECISIONS = ("day", "month", "year", "approx", "undated")
STATUSES = ("FACT", "REPORTED", "ASSESSMENT")
CLASSES = ("precision", "timezone", "announcement", "disagreement")
TIERS = ("primary", "peer_reviewed", "secondary", "aggregator", "unverified")
GOOD_TIERS = ("primary", "peer_reviewed", "secondary")
OPENED = ("full", "section")
READ_LEVELS = ("full", "section", "abstract", "snippet", "not_opened")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}")
YMD = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
YM = re.compile(r"(\d{4})-(\d{2})")
Y = re.compile(r"(\d{4})")
TIME = re.compile(r"(\d{2}):(\d{2}) (UTC|Z|local|[+-]\d{2}:\d{2})")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
EPOCH = dt.date(1970, 1, 1).toordinal()
FLAGS = {"--json"}
VALUES = {"--gap-days": 1, "--approx-days": 1, "--today": 1, "--before": 2}
ORDER_RULE = ("Listed by the earliest day each written date could be; on a tie the less precise date first, then untimed before timed, "
              "then clock time as written, then file order. The listing is for reading. It is not a claim that one event preceded another.")


class InputError(Exception):
    """The file could not be read as UTF-8 CSV. Exit code 2."""


def split_list(text):
    return [x.strip() for x in text.split(";") if x.strip()]


def read_csv(path):
    """Return (header, rows). Each row is a dict of stripped text plus "_row", its line number."""
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
    table = []
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        for r in reader:
            if any(c.strip() for c in r):
                table.append((reader.line_num, r))
    except csv.Error as e:
        raise InputError("%s is not well-formed CSV (%s)" % (path, e))
    if not table:
        raise InputError("%s is empty; it needs a header row" % path)
    header = [h.strip() for h in table[0][1]]
    rows = []
    for n, r in table[1:]:
        row = {"_row": n, "_cells": len(r)}
        for i, h in enumerate(header):
            row[h] = r[i].strip() if i < len(r) else ""
        rows.append(row)
    return header, rows


def parse_written(text):
    """Return (form, low, high) for a written date, or None. form is day, month or year."""
    m = YMD.fullmatch(text)
    if m:
        try:
            d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
        return "day", d, d
    m = YM.fullmatch(text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if y < 1 or not 1 <= mo <= 12:
            return None
        return "month", dt.date(y, mo, 1), dt.date(y, mo, calendar.monthrange(y, mo)[1])
    m = Y.fullmatch(text)
    if m:
        y = int(m.group(1))
        if y < 1:
            return None
        return "year", dt.date(y, 1, 1), dt.date(y, 12, 31)
    return None


def strict_day(text):
    got = parse_written(text) if isinstance(text, str) else None
    return got[1] if got and got[0] == "day" else None


def widen(form, low, high, approx_days):
    """The window for an approximate date. See the docstring: a convention, not a finding."""
    try:
        if form == "day":
            return low - dt.timedelta(days=approx_days), high + dt.timedelta(days=approx_days)
        if form == "month":
            py, pm = (low.year, low.month - 1) if low.month > 1 else (low.year - 1, 12)
            ny, nm = (low.year, low.month + 1) if low.month < 12 else (low.year + 1, 1)
            return dt.date(py, pm, 1), dt.date(ny, nm, calendar.monthrange(ny, nm)[1])
        return dt.date(low.year - 1, 1, 1), dt.date(low.year + 1, 12, 31)
    except (ValueError, OverflowError):
        return low, high


def show_day(d):
    return "%d %s %04d" % (d.day, MONTHS[d.month - 1], d.year)


def show(form, low, approx=False):
    """A date as a person reads it, with its precision in the wording itself."""
    text = show_day(low) if form == "day" else ("%s %04d" % (MONTHS[low.month - 1], low.year) if form == "month" else "%04d" % low.year)
    return ("about " + text) if approx else text


def window_words(ev):
    if ev["wlow"] == ev["whigh"]:
        return show_day(ev["wlow"])
    return "%s to %s" % (show_day(ev["wlow"]), show_day(ev["whigh"]))


def load(events_path, sources_path, approx_days=15, today=None):
    """Read and validate both files. Return (errors, advisories, events, sources, pairs)."""
    errors, adv = [], []
    sh, srows = read_csv(sources_path)
    eh, erows = read_csv(events_path)
    for name, header, cols in (("sources", sh, SOURCE_COLS), ("events", eh, EVENT_COLS)):
        missing = [c for c in cols if c not in header]
        if missing:
            errors.append("the %s file has no column(s): %s" % (name, ", ".join(missing)))
        dup = sorted({c for c in header if header.count(c) > 1})
        if dup:
            errors.append("the %s file names column(s) twice: %s" % (name, ", ".join(dup)))
        extra = [c for c in header if c and c not in cols]
        if extra:
            adv.append("the %s file has column(s) this script does not read: %s" % (name, ", ".join(extra)))
    if errors:
        return errors, adv, [], {}, []
    for name, header, rows in (("sources", sh, srows), ("events", eh, erows)):
        for r in rows:
            if r["_cells"] != len(header):
                errors.append("%s row %d has %d cell(s) and the header has %d; a comma inside a value needs the value in double quotes"
                              % (name, r["_row"], r["_cells"], len(header)))

    sources = {}
    for r in srows:
        sid, where = r["source_id"], "sources row %d" % r["_row"]
        if not ID.fullmatch(sid):
            errors.append("%s: source_id %r must start with a letter and use letters, digits, hyphen or underscore" % (where, sid))
            continue
        where = "source %s" % sid
        if sid in sources:
            errors.append("source_id %s is used twice (rows %d and %d)" % (sid, sources[sid]["_row"], r["_row"]))
            continue
        if not r["title"]:
            errors.append("%s: title is empty" % where)
        if r["tier"] not in TIERS:
            errors.append("%s: tier %r is not one of %s" % (where, r["tier"], ", ".join(TIERS)))
        for key in ("published", "accessed"):
            if r[key] and strict_day(r[key]) is None:
                errors.append("%s: %s %r must be blank or a real date written YYYY-MM-DD" % (where, key, r[key]))
        if r["read_level"] in OPENED and not r["accessed"]:
            errors.append("%s: read_level is %s but accessed is blank; say when it was read" % (where, r["read_level"]))
        if r["read_level"] not in READ_LEVELS:
            adv.append("%s: read_level %r is not one this script knows (%s); it is treated as not opened" % (where, r["read_level"], ", ".join(READ_LEVELS)))
        sources[sid] = r

    events, seen = [], {}
    for index, r in enumerate(erows):
        eid, where = r["event_id"], "events row %d" % r["_row"]
        if not ID.fullmatch(eid):
            errors.append("%s: event_id %r must start with a letter and use letters, digits, hyphen or underscore" % (where, eid))
            continue
        where = "event %s" % eid
        if eid in seen:
            errors.append("event_id %s is used twice (rows %d and %d)" % (eid, seen[eid], r["_row"]))
            continue
        seen[eid] = r["_row"]
        ev = {"id": eid, "row": r["_row"], "index": index, "date": r["date"], "precision": r["date_precision"], "end_date": r["end_date"],
              "time": r["time"], "title": r["title"], "detail": r["detail"], "actors": split_list(r["actors"]),
              "sources": split_list(r["source_id"]), "locator": r["locator"], "status": r["status"], "tags": split_list(r["tags"]),
              "conflicts": [], "form": None, "low": None, "high": None, "wlow": None, "whigh": None, "span_high": None,
              "instant": None, "clock": None, "ok": True}
        if not ev["title"]:
            errors.append("%s: title is empty" % where)
        # ---- the date, exactly as precise as stated ----
        p = ev["precision"]
        if p not in PRECISIONS:
            errors.append("%s: date_precision %r is not one of %s" % (where, p, ", ".join(PRECISIONS)))
            ev["ok"] = False
        elif p == "undated":
            if ev["date"]:
                errors.append("%s is marked undated but has the date %r; give the precision the source gives, or clear the date" % (where, ev["date"]))
                ev["ok"] = False
            if ev["end_date"] or ev["time"]:
                errors.append("%s is undated, so it cannot have an end_date or a time" % where)
        else:
            got = parse_written(ev["date"])
            if got is None:
                errors.append("%s: date %r is not a real date written YYYY-MM-DD, YYYY-MM or YYYY" % (where, ev["date"]))
                ev["ok"] = False
            else:
                form, low, high = got
                if p != "approx" and form != p:
                    want = {"day": "YYYY-MM-DD", "month": "YYYY-MM", "year": "YYYY"}[p]
                    if ("day", "month", "year").index(form) < ("day", "month", "year").index(p):
                        errors.append("%s: precision is %s, so the date is written %s. %r adds detail the source did not give; never fill in a %s"
                                      % (where, p, want, ev["date"], "day" if form == "day" else "month"))
                    else:
                        errors.append("%s: precision is %s but the date %r has no %s; write it %s or lower the precision"
                                      % (where, p, ev["date"], p, want))
                    ev["ok"] = False
                else:
                    ev.update({"form": form, "low": low, "high": high})
                    ev["wlow"], ev["whigh"] = widen(form, low, high, approx_days) if p == "approx" else (low, high)
                    ev["span_high"] = ev["whigh"]
        if ev["ok"] and p != "undated" and ev["end_date"]:
            got = parse_written(ev["end_date"])
            if got is None:
                errors.append("%s: end_date %r is not a real date written YYYY-MM-DD, YYYY-MM or YYYY" % (where, ev["end_date"]))
            elif got[2] < ev["low"]:
                errors.append("%s: end_date %s is before the start %s" % (where, ev["end_date"], ev["date"]))
            else:
                ev["end"] = got
                ev["span_high"] = max(ev["whigh"], got[2])
        if ev["time"] and p != "undated":
            m = TIME.fullmatch(ev["time"])
            if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
                errors.append("%s: time %r must be HH:MM and a zone: UTC, Z, an offset such as +02:00, or local" % (where, ev["time"]))
            elif p != "day":
                errors.append("%s: a time needs a day-precision date; this one is %s" % (where, p))
            elif ev["ok"]:
                hh, mm, zone = int(m.group(1)), int(m.group(2)), m.group(3)
                ev["clock"] = hh * 60 + mm
                if zone != "local":
                    off = 0
                    if zone not in ("UTC", "Z"):
                        oh, om = int(zone[1:3]), int(zone[4:6])
                        if oh > 14 or om > 59:
                            errors.append("%s: the offset in %r is not a real zone offset" % (where, ev["time"]))
                            off = None
                        else:
                            off = (oh * 60 + om) * (1 if zone[0] == "+" else -1)
                    if off is not None:
                        ev["instant"] = (ev["low"].toordinal() - EPOCH) * 1440 + ev["clock"] - off
        # ---- status and sourcing ----
        st = ev["status"]
        missing = [s for s in ev["sources"] if s not in sources]
        for s in missing:
            errors.append("%s: source %r is not in the sources file" % (where, s))
        cited = [sources[s] for s in ev["sources"] if s in sources]
        if st not in STATUSES:
            errors.append("%s: status %r is not one of %s" % (where, st, ", ".join(STATUSES)))
        elif st == "FACT":
            if not ev["locator"]:
                errors.append("%s is a FACT with no locator; say where in the source the date is given" % where)
            if not any(s["tier"] in GOOD_TIERS and s["read_level"] in OPENED for s in cited):
                why = "it cites no source" if not ev["sources"] else (
                    "none of its sources is of secondary tier or better" if not any(s["tier"] in GOOD_TIERS for s in cited)
                    else "its sources were not opened (read_level is not full or section)")
                errors.append("%s is a FACT, but %s. A FACT needs an opened source of secondary tier or better; otherwise mark it REPORTED" % (where, why))
        elif st == "REPORTED" and not ev["sources"]:
            errors.append("%s is REPORTED with no source; say who reports it" % where)
        elif st == "ASSESSMENT" and not ev["sources"] and not ev["detail"]:
            errors.append("%s is an ASSESSMENT with no source and no detail; say what it is inferred from" % where)
        if cited and not missing and not any(s["tier"] in GOOD_TIERS for s in cited):
            ev["weak"] = True
        # ---- conflicts, as written ----
        for token in split_list(r["conflicts_with"]):
            other, _, cls = token.partition(":")
            other, cls = other.strip(), cls.strip()
            if cls and cls not in CLASSES:
                errors.append("%s: conflict class %r is not one of %s" % (where, cls, ", ".join(CLASSES)))
                cls = ""
            ev["conflicts"].append((other, cls))
        if today and ev["ok"] and ev["low"] and ev["low"] > today:
            adv.append("%s is dated %s, after %s: a scheduled date, not something that has happened" % (where, show(ev["form"], ev["low"], p == "approx"), today.isoformat()))
        events.append(ev)

    by_id = {e["id"]: e for e in events}
    pairs, done = [], set()
    for e in events:
        for other, cls in e["conflicts"]:
            if other == e["id"]:
                errors.append("event %s lists itself in conflicts_with" % e["id"])
                continue
            if other not in by_id:
                errors.append("event %s: conflicts_with names %r, which is not an event id" % (e["id"], other))
                continue
            back = [c for o, c in by_id[other]["conflicts"] if o == e["id"]]
            if not back:
                errors.append("event %s lists a conflict with %s, but %s does not list %s; record a conflict on both rows" % (e["id"], other, other, e["id"]))
                continue
            key = tuple(sorted((e["id"], other), key=lambda i: by_id[i]["index"]))
            if key in done:
                continue
            done.add(key)
            if back[0] != cls:
                errors.append("events %s and %s give different classes for their conflict (%s and %s); use the same on both rows"
                              % (e["id"], other, cls or "none", back[0] or "none"))
                cls = ""
            pairs.append({"a": key[0], "b": key[1], "class": cls})
    for p in pairs:
        a, b = by_id[p["a"]], by_id[p["b"]]
        if not (a["ok"] and b["ok"]) or a["low"] is None or b["low"] is None:
            p["dates"] = "not compared"
            if (a["precision"] == "undated" or b["precision"] == "undated") and a["ok"] and b["ok"]:
                adv.append("events %s and %s are marked as conflicting but one is undated, so the dates cannot be compared" % (p["a"], p["b"]))
            continue
        overlap = a["wlow"] <= b["whigh"] and b["wlow"] <= a["whigh"]
        same_instant = a["instant"] is not None and a["instant"] == b["instant"]
        p["dates"] = "the same instant" if same_instant else ("compatible" if overlap else "not compatible")
        both = "%s (%s) and %s (%s)" % (p["a"], display(a), p["b"], display(b))
        cls = p["class"]
        if cls == "precision":
            if not overlap:
                errors.append("events %s are classed precision, but those dates cannot both be right. If one is an announcement and the other "
                              "the event, class it announcement; otherwise disagreement" % both)
            elif a["precision"] == b["precision"] and a["date"] == b["date"]:
                adv.append("events %s are classed precision but give the same date at the same precision; that is agreement, not a conflict" % both)
        elif cls == "timezone":
            apart = abs((a["low"] - b["low"]).days)
            if a["instant"] is not None and b["instant"] is not None:
                if a["instant"] != b["instant"]:
                    errors.append("events %s are classed timezone, but their recorded instants differ by %d minute(s)" % (both, abs(a["instant"] - b["instant"])))
            elif apart > 1 or a["form"] != "day" or b["form"] != "day":
                errors.append("events %s are classed timezone, but a zone difference needs two day-precision dates no more than a day apart" % both)
            else:
                adv.append("events %s are classed timezone; that cannot be confirmed because a time and an offset are not recorded on both rows" % both)
        elif cls == "disagreement" and overlap:
            adv.append("events %s are classed disagreement, but the dates are compatible at the recorded precision. If the sources disagree about "
                       "something other than the date, say so in detail; otherwise class it precision" % both)
        elif cls == "":
            hint = ("the same instant: class it timezone" if same_instant else
                    "compatible: probably precision" if overlap else "not compatible: announcement or disagreement, decided by reading both sources")
            adv.append("events %s are marked as conflicting with no class. The dates are %s" % (both, hint))
    # same title, different dates, not marked
    titles = {}
    for e in events:
        if e["ok"] and e["title"]:
            titles.setdefault(" ".join(e["title"].lower().split()), []).append(e)
    linked = {(p["a"], p["b"]) for p in pairs} | {(p["b"], p["a"]) for p in pairs}
    for group in titles.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if (a["date"], a["precision"]) != (b["date"], b["precision"]) and (a["id"], b["id"]) not in linked:
                    adv.append("events %s and %s have the same title and different dates and are not marked as conflicting; if they are one event, "
                               "record the conflict on both rows" % (a["id"], b["id"]))
    used = {s for e in events for s in e["sources"]}
    for sid, s in sources.items():
        if sid not in used:
            adv.append("source %s is not cited by any event" % sid)
        elif not s["address"]:
            adv.append("source %s has no address; a reader cannot go to it" % sid)
    return errors, adv, events, sources, pairs


def display(ev):
    if ev["precision"] == "undated" or ev["low"] is None:
        return "undated"
    text = show(ev["form"], ev["low"], ev["precision"] == "approx")
    if ev.get("end"):
        text += " to " + show(ev["end"][0], ev["end"][1])
    if ev["time"]:
        text += " " + ev["time"]
    return text


def sort_key(ev):
    return (ev["low"].toordinal(), -ev["high"].toordinal(), 0 if ev["clock"] is None else 1, ev["clock"] or 0, ev["index"])


def analyse(events, pairs, gap_days, before):
    """Order, gaps, weak sourcing and sequence checks, on rows that passed validation."""
    adv, out = [], {}
    dated = sorted([e for e in events if e["ok"] and e["low"] is not None], key=sort_key)
    undated = [e for e in events if e["ok"] and e["precision"] == "undated"]
    out["order"] = [e["id"] for e in dated]
    out["undated"] = [e["id"] for e in undated]
    # gaps: a stretch in which no listed event can fall
    gaps = []
    if dated:
        prefix, best = [], None
        for e in dated:
            if best is None or e["span_high"] > best["span_high"]:
                best = e
            prefix.append(best)
        suffix, best = [None] * len(dated), None
        for i in range(len(dated) - 1, -1, -1):
            if best is None or dated[i]["wlow"] <= best["wlow"]:
                best = dated[i]
            suffix[i] = best
        for i in range(len(dated) - 1):
            a, b = prefix[i], suffix[i + 1]
            days = (b["wlow"] - a["span_high"]).days
            if days > gap_days:
                gaps.append({"after": dated[i]["id"], "before": dated[i + 1]["id"], "at_least_days": days, "from": a["span_high"].isoformat(),
                             "to": b["wlow"].isoformat(), "bounded_by": [a["id"], b["id"]]})
    out["gaps"] = gaps
    out["weak"] = [e["id"] for e in events if e.get("weak")]
    # instants against written order
    timed = [e for e in dated if e["instant"] is not None]
    pos = {e["id"]: i for i, e in enumerate(dated)}
    for i, a in enumerate(timed):
        for b in timed[i + 1:]:
            if (pos[a["id"]] < pos[b["id"]]) != (a["instant"] <= b["instant"]) and a["instant"] != b["instant"]:
                first, second = (a, b) if pos[a["id"]] < pos[b["id"]] else (b, a)
                adv.append("event %s is listed before %s by written date and time, but its recorded instant is %d minute(s) later once the zones "
                           "are applied" % (first["id"], second["id"], first["instant"] - second["instant"]))
    by_id = {e["id"]: e for e in events}
    checks = []
    for a_id, b_id in before:
        row = {"a": a_id, "b": b_id}
        a, b = by_id.get(a_id), by_id.get(b_id)
        if a is None or b is None:
            row.update({"verdict": "unknown id", "reason": "%s is not an event id" % (a_id if a is None else b_id)})
        elif not a["ok"] or not b["ok"]:
            row.update({"verdict": "undecided", "reason": "one of the rows did not pass validation"})
        elif a["low"] is None or b["low"] is None:
            row.update({"verdict": "undecided", "reason": "%s is undated" % (a_id if a["low"] is None else b_id)})
        elif a["instant"] is not None and b["instant"] is not None:
            if a["instant"] < b["instant"]:
                row.update({"verdict": "holds", "reason": "by recorded instants, %s is %d minute(s) earlier" % (a_id, b["instant"] - a["instant"])})
            elif a["instant"] > b["instant"]:
                row.update({"verdict": "violated", "reason": "by recorded instants, %s is %d minute(s) earlier" % (b_id, a["instant"] - b["instant"])})
            else:
                row.update({"verdict": "undecided", "reason": "the two rows record the same minute"})
        elif a["whigh"] < b["wlow"]:
            row.update({"verdict": "holds", "reason": "the latest %s could be is %s; the earliest %s could be is %s"
                        % (a_id, show_day(a["whigh"]), b_id, show_day(b["wlow"]))})
            if (b["wlow"] - a["whigh"]).days == 1 and a["precision"] == "day" and b["precision"] == "day":
                row["caveat"] = "the dates are one calendar day apart and a zone is not recorded on both rows; this holds if both dates are in the same zone"
        elif b["whigh"] < a["wlow"]:
            row.update({"verdict": "violated", "reason": "the latest %s could be is %s; the earliest %s could be is %s, so %s is the earlier"
                        % (b_id, show_day(b["whigh"]), a_id, show_day(a["wlow"]), b_id)})
        else:
            parts = []
            for e in (a, b):
                if e["precision"] == "approx":
                    parts.append("%s is approximate (%s, taken as %s)" % (e["id"], display(e), window_words(e)))
                elif e["form"] != "day":
                    parts.append("%s is known only to the %s (%s)" % (e["id"], e["form"], window_words(e)))
                else:
                    parts.append("%s is %s" % (e["id"], display(e)))
            why = "; ".join(parts)
            if a["form"] == "day" and b["form"] == "day" and a["precision"] == "day" and b["precision"] == "day":
                why += "; the same day, and a time with a zone is not recorded on both"
            row.update({"verdict": "undecided", "reason": why})
        checks.append(row)
    out["before"] = checks
    return adv, out


def parse_args(argv, name, flags, values):
    """Strict parsing. Returns (flags, {option: [values...]}, paths); exits 2 with one line on a problem."""
    got, opts, paths, i = set(), {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in flags:
            got.add(a)
        elif a in values:
            need = argv[i + 1:i + 1 + values[a]]
            if len(need) < values[a] or any(v.startswith("--") for v in need):
                print("%s: %s needs %d value(s)" % (name, a, values[a]), file=sys.stderr)
                raise SystemExit(2)
            opts.setdefault(a, []).append(need if values[a] > 1 else need[0])
            i += values[a]
        elif a.startswith("--"):
            print("%s: unknown option %s" % (name, a), file=sys.stderr)
            raise SystemExit(2)
        else:
            paths.append(a)
        i += 1
    return got, opts, paths


def whole(opts, key, default, name):
    if key not in opts:
        return default
    v = opts[key][-1]
    if not re.fullmatch(r"\d{1,5}", v):
        print("%s: %s needs a whole number, zero or more" % (name, key), file=sys.stderr)
        raise SystemExit(2)
    return int(v)


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def run(events_path, sources_path, gap_days=90, approx_days=15, before=(), today=None):
    """Everything the command line does, as one dictionary. Raises InputError for unreadable files."""
    errors, adv, events, sources, pairs = load(events_path, sources_path, approx_days, today)
    more, out = analyse(events, pairs, gap_days, list(before)) if not errors or events else ([], {"order": [], "undated": [], "gaps": [], "weak": [], "before": []})
    adv += more
    for c in out["before"]:
        if c["verdict"] == "unknown id":
            errors.append("--before %s %s: %s" % (c["a"], c["b"], c["reason"]))
    if out["weak"]:
        adv.append("%d event(s) rest only on sources below secondary tier: %s" % (len(out["weak"]), ", ".join(out["weak"])))
    by_id = {e["id"]: e for e in events}
    rows = []
    for e in events:
        rows.append({"id": e["id"], "date": e["date"], "precision": e["precision"], "end_date": e["end_date"], "time": e["time"],
                     "display": display(e) if e["ok"] else "", "title": e["title"], "detail": e["detail"], "actors": e["actors"],
                     "sources": e["sources"], "locator": e["locator"], "status": e["status"], "tags": e["tags"],
                     "conflicts": [{"id": o, "class": c} for o, c in e["conflicts"]],
                     "earliest": e["wlow"].isoformat() if e["wlow"] else None, "latest": e["whigh"].isoformat() if e["whigh"] else None,
                     "span_latest": e["span_high"].isoformat() if e["span_high"] else None,
                     "listed_at": e["low"].isoformat() if e["low"] else None})
    for p in pairs:
        p["a_date"], p["b_date"] = display(by_id[p["a"]]), display(by_id[p["b"]])
    counts = {s: sum(1 for e in events if e["status"] == s) for s in STATUSES}
    violated = [c for c in out["before"] if c["verdict"] == "violated"]
    return {"errors": errors, "advisories": adv, "events": rows, "sources": {k: {c: v[c] for c in SOURCE_COLS} for k, v in sources.items()},
            "conflicts": pairs, "order": out["order"], "undated": out["undated"], "gaps": out["gaps"], "weak": out["weak"], "before": out["before"],
            "counts": {"events": len(events), "dated": len(out["order"]), "undated": len(out["undated"]), "sources": len(sources), "status": counts},
            "settings": {"gap_days": gap_days, "approx_days": approx_days, "today": today.isoformat() if today else None},
            "order_rule": ORDER_RULE, "ok": not errors and not violated}


def text_report(res):
    c = res["counts"]
    by_id = {e["id"]: e for e in res["events"]}
    L = ["chronology_check: %d event row(s), %d source(s). %d dated, %d undated. %d FACT, %d REPORTED, %d ASSESSMENT."
         % (c["events"], c["sources"], c["dated"], c["undated"], c["status"]["FACT"], c["status"]["REPORTED"], c["status"]["ASSESSMENT"])]
    if res["order"]:
        L.append("TIMELINE  " + res["order_rule"])
        wid = max(len(i) for i in res["order"])
        wd = max(len(by_id[i]["display"]) for i in res["order"])
        for i in res["order"]:
            e = by_id[i]
            L.append("  %-*s  %-*s  %-10s  %s" % (wid, i, wd, e["display"], e["status"], e["title"]))
    if res["undated"]:
        L.append("UNDATED  not placed in the order")
        for i in res["undated"]:
            L.append("  %s  %-10s  %s" % (i, by_id[i]["status"], by_id[i]["title"]))
    if res["conflicts"]:
        L.append("DATE CONFLICTS  %d pair(s)" % len(res["conflicts"]))
        for p in res["conflicts"]:
            L.append("  %s (%s) against %s (%s): class %s; the dates are %s" % (p["a"], p["a_date"], p["b"], p["b_date"], p["class"] or "not given", p.get("dates", "not compared")))
    L.append("GAPS  %d longer than %d days" % (len(res["gaps"]), res["settings"]["gap_days"]))
    for g in res["gaps"]:
        L.append("  at least %d days: after %s, before %s (nothing listed can fall between %s and %s)"
                 % (g["at_least_days"], g["after"], g["before"], g["from"], g["to"]))
    if res["before"]:
        L.append("SEQUENCE  A must precede B")
        for s in res["before"]:
            L.append("  %-9s %s before %s: %s%s" % (s["verdict"].upper(), s["a"], s["b"], s["reason"], (". Note: " + s["caveat"]) if s.get("caveat") else ""))
    L += ["  ERROR     " + m for m in res["errors"]]
    L += ["  ADVISORY  " + m for m in res["advisories"]]
    n = {v: sum(1 for s in res["before"] if s["verdict"] == v) for v in ("holds", "violated", "undecided")}
    seq = (" Sequence: %d hold, %d violated, %d cannot be decided." % (n["holds"], n["violated"], n["undecided"])) if res["before"] else ""
    L.append("RESULT: %s. %d error(s), %d advisory note(s).%s This checks form and date arithmetic. It does not check that a source says what a row claims."
             % ("PASS" if res["ok"] else "FAIL", len(res["errors"]), len(res["advisories"]), seq))
    return "\n".join(L)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    flags, opts, paths = parse_args(argv, "chronology_check", FLAGS, VALUES)
    if len(paths) != 2:
        print("chronology_check: expected EVENTS.csv and SOURCES.csv, got %d file(s)" % len(paths), file=sys.stderr)
        return 2
    gap = whole(opts, "--gap-days", 90, "chronology_check")
    approx = whole(opts, "--approx-days", 15, "chronology_check")
    today = None
    if "--today" in opts:
        today = strict_day(opts["--today"][-1])
        if today is None:
            print("chronology_check: --today needs a real date written YYYY-MM-DD", file=sys.stderr)
            return 2
    try:
        res = run(paths[0], paths[1], gap, approx, [tuple(x) for x in opts.get("--before", [])], today)
    except InputError as e:
        print("chronology_check: %s" % e, file=sys.stderr)
        return 2
    emit(json.dumps(res, indent=1, ensure_ascii=True) if "--json" in flags else text_report(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
