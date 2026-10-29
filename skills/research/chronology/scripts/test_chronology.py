#!/usr/bin/env python3
"""Tests for chronology_check.py and build_timeline.py, with planted faults. Standard library only.

Usage:
  python test_chronology.py                 run every named test against the scripts beside this file
  python test_chronology.py --only NAME     run one test
  python test_chronology.py --dir FOLDER    test the copies of the scripts in FOLDER
  python test_chronology.py --mutants       plant each fault below in a temporary copy and require
                                            the named test to fail on it

Every timeline used here is SYNTHETIC and is written by this script to a temporary folder, which it
removes afterwards. Nothing in the skill folder is written to. The builder tests use the viewer
template at ../assets/timeline.html.

Why --mutants exists: a test that has never failed has not been shown to test anything. Each
planted fault is a small edit to a copy of a script, for example treating a month-precision date as
the first of that month. The run fails if a fault is not caught by the test named for it.

Each refusal is paired with its valid neighbour: the nearest accepted input is run in the same test.

This does not test the viewer in a browser. test_timeline.py does that and needs Playwright.

Exit codes: 0 every test passed (with --mutants: every fault was caught). 1 otherwise. 2 bad arguments.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ("chronology_check.py", "build_timeline.py")
TEMPLATE = HERE.parent / "assets" / "timeline.html"
ECOLS = ["event_id", "date", "date_precision", "end_date", "time", "title", "detail", "actors", "source_id", "locator", "status", "conflicts_with", "tags"]
SCOLS = ["source_id", "title", "publisher", "address", "tier", "published", "accessed", "read_level", "family", "notes"]


def sources():
    def s(i, title, tier, level):
        return {"source_id": i, "title": title, "publisher": "SYNTHETIC publisher", "address": "https://example.org/" + i, "tier": tier,
                "published": "", "accessed": "" if level == "not_opened" else "2026-01-10", "read_level": level, "family": "", "notes": "SYNTHETIC"}
    return [s("S1", "Register of notices", "primary", "full"), s("S2", "Trade press report", "secondary", "section"),
            s("S3", "Weekly digest", "aggregator", "snippet"), s("S4", "Forum thread", "unverified", "section"),
            s("S5", "Register page not opened", "primary", "not_opened")]


def ev(i, date, precision, title="Something happened", status="REPORTED", source="S2", **more):
    row = {"event_id": i, "date": date, "date_precision": precision, "end_date": "", "time": "", "title": title, "detail": "", "actors": "Authority",
           "source_id": source, "locator": "para 1", "status": status, "conflicts_with": "", "tags": "test"}
    row.update(more)
    return row


def base():
    return [ev("A1", "2024-03-19", "day", "Notice published", "FACT", "S1"), ev("A2", "2024-03", "month", "Works began"),
            ev("A3", "2024", "year", "Contract awarded"), ev("A4", "2024-06-12", "approx", "Inspection"),
            ev("A5", "", "undated", "Complaint lodged"), ev("A6", "2024-09-01", "day", "Statement issued", "FACT", "S1")]


def to_csv(cols, rows):
    def cell(v):
        v = str(v)
        return '"' + v.replace('"', '""') + '"' if any(c in v for c in ',"\n') else v
    return ("\n".join([",".join(cols)] + [",".join(cell(r.get(c, "")) for c in cols) for r in rows]) + "\n").encode("utf-8")


class Box:
    def __init__(self, folder, tmp):
        self.folder, self.tmp, self.n = Path(folder), Path(tmp), 0

    def path(self, suffix=".csv"):
        self.n += 1
        return self.tmp / ("f%03d%s" % (self.n, suffix))

    def write(self, raw):
        p = self.path()
        p.write_bytes(raw)
        return str(p)

    def run(self, script, *args):
        r = subprocess.run([sys.executable, "-B", str(self.folder / script)] + [str(a) for a in args], capture_output=True, timeout=120)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    def check(self, events, srcs=None, *args):
        e = self.write(events if isinstance(events, bytes) else to_csv(ECOLS, events))
        s = self.write(srcs if isinstance(srcs, bytes) else to_csv(SCOLS, srcs if srcs is not None else sources()))
        return self.run("chronology_check.py", e, s, *args)

    def check_json(self, events, srcs=None, *args):
        code, out, err = self.check(events, srcs, "--json", *args)
        return code, json.loads(out)


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def has(messages, *parts):
    return any(all(p in m for p in parts) for m in messages)


def verdict(r, a, b):
    return next(x for x in r["before"] if x["a"] == a and x["b"] == b)


# ---------------- dates are never more precise than their source ----------------

def test_valid_base_passes(b):
    code, r = b.check_json(base())
    need(code == 0 and r["errors"] == [], "the base timeline did not pass: %s" % r["errors"])
    need(r["counts"]["dated"] == 5 and r["undated"] == ["A5"], "counts: %s" % r["counts"])


def test_month_precision_written_as_a_day_is_refused(b):
    rows = base()
    rows[1]["date"] = "2024-03-01"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A2", "never fill in a day"), "a month-precision date written 2024-03-01 was accepted: %s" % r["errors"])
    rows[1]["date"] = "2024-03"
    need(b.check(rows)[0] == 0, "the valid neighbour (2024-03) was refused")
    rows = base()
    rows[2]["date"] = "2024-01"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A3", "never fill in a month"), "a year-precision date written 2024-01 was accepted")
    rows = base()
    rows[0]["date"] = "2024-03"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A1", "has no day"), "a day-precision date written 2024-03 was accepted")


def test_dates_are_shown_at_their_own_precision(b):
    code, r = b.check_json(base())
    shown = {e["id"]: e["display"] for e in r["events"]}
    need(shown == {"A1": "19 Mar 2024", "A2": "Mar 2024", "A3": "2024", "A4": "about 12 Jun 2024", "A5": "undated", "A6": "1 Sep 2024"}, "display: %s" % shown)
    code, out, err = b.check(base())
    need("1 Mar 2024" not in out and "1 Jan 2024" not in out, "the text output shows a first-of-period day for an imprecise date")


def test_bad_dates_are_refused(b):
    for bad in ("20240319", "2024-02-30", "2024-13-01", "2023-02-29", "19/03/2024", "2024-3-19", "2024-03-19T10:00"):
        rows = base()
        rows[0]["date"] = bad
        code, r = b.check_json(rows)
        need(code == 1 and has(r["errors"], "A1", "not a real date"), "day date %r was accepted" % bad)
    for bad in ("2024-13", "2024-00", "202403"):
        rows = base()
        rows[1]["date"] = bad
        need(b.check(rows)[0] == 1, "month date %r was accepted" % bad)
    for bad in ("24", "0000", "20240"):
        rows = base()
        rows[2]["date"] = bad
        need(b.check(rows)[0] == 1, "year date %r was accepted" % bad)
    rows = base()
    rows[0]["date"] = "2024-02-29"
    need(b.check(rows)[0] == 0, "the valid neighbour (29 February in a leap year) was refused")


def test_undated_rows_are_listed_apart_and_never_placed(b):
    code, r = b.check_json(base())
    need("A5" not in r["order"] and r["undated"] == ["A5"], "an undated row was placed in the order")
    rows = base()
    rows[4]["date"] = "2024-05-01"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A5", "marked undated but has the date"), "an undated row with a date was accepted")
    code, r = b.check_json(base(), None, "--before", "A5", "A6")
    need(verdict(r, "A5", "A6")["verdict"] == "undecided" and "undated" in verdict(r, "A5", "A6")["reason"], "an undated row was given a place in a sequence check")


def test_end_before_start_is_refused(b):
    rows = base()
    rows[0]["end_date"] = "2024-03-18"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A1", "before the start"), "an end before the start was accepted")
    for good in ("2024-03-19", "2024-03", "2024", "2025-01-01"):
        rows[0]["end_date"] = good
        need(b.check(rows)[0] == 0, "the valid neighbour end_date %r was refused" % good)
    rows[0]["end_date"] = "2024-02"
    need(b.check(rows)[0] == 1, "an end month before the start was accepted")


def test_time_rules(b):
    for bad in ("25:00 UTC", "09:60 UTC", "09:00", "9:00 UTC", "09:00 +15:00", "09:00 GMT", "09:00+02:00"):
        rows = base()
        rows[0]["time"] = bad
        code, r = b.check_json(rows)
        need(code == 1 and has(r["errors"], "A1"), "time %r was accepted" % bad)
    for good in ("09:00 local", "23:59 UTC", "00:00 Z", "09:00 +14:00", "09:00 -05:30"):
        rows = base()
        rows[0]["time"] = good
        need(b.check(rows)[0] == 0, "the valid neighbour time %r was refused" % good)
    rows = base()
    rows[1]["time"] = "09:00 UTC"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A2", "a time needs a day-precision date"), "a time on a month-precision date was accepted")


# ---------------- ids, references, enumerations ----------------

def test_unknown_values_are_refused(b):
    for index, key, bad, good in ((0, "date_precision", "week", "day"), (0, "status", "TRUE", "FACT"), (0, "status", "fact", "FACT")):
        rows = base()
        rows[index][key] = bad
        code, r = b.check_json(rows)
        need(code == 1 and has(r["errors"], repr(bad)), "%s %r was accepted" % (key, bad))
        rows[index][key] = good
        need(b.check(rows)[0] == 0, "the valid neighbour %s %r was refused" % (key, good))
    srcs = sources()
    srcs[0]["tier"] = "blog"
    code, r = b.check_json(base(), srcs)
    need(code == 1 and has(r["errors"], "S1", "'blog'"), "tier 'blog' was accepted")
    rows = base()
    rows[0]["conflicts_with"], rows[1]["conflicts_with"] = "A2:clash", "A1:clash"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "conflict class 'clash'"), "conflict class 'clash' was accepted")


def test_ids_and_references(b):
    rows = base()
    rows[1]["event_id"] = "A1"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "event_id A1 is used twice"), "a duplicate event id was accepted")
    srcs = sources()
    srcs[1]["source_id"] = "S1"
    code, r = b.check_json(base(), srcs)
    need(code == 1 and has(r["errors"], "source_id S1 is used twice"), "a duplicate source id was accepted")
    rows = base()
    rows[1]["source_id"] = "S9"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A2", "'S9' is not in the sources file"), "a missing source was accepted")
    rows = base()
    rows[0]["conflicts_with"] = "A9"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A1", "'A9', which is not an event id"), "a conflict with a missing event was accepted")
    rows = base()
    rows[0]["conflicts_with"] = "A1"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A1 lists itself"), "a conflict with itself was accepted")
    rows = base()
    rows[0]["source_id"] = "S1; S2"
    need(b.check(rows)[0] == 0, "a list of two sources was refused")


def test_fact_needs_an_opened_secondary_source_and_a_locator(b):
    for source, why in (("S3", "none of its sources is of secondary tier or better"), ("S4", "none of its sources is of secondary tier or better"),
                        ("S5", "were not opened"), ("", "cites no source")):
        rows = base()
        rows[0]["source_id"] = source
        code, r = b.check_json(rows)
        need(code == 1 and has(r["errors"], "A1 is a FACT", why), "a FACT citing %r was accepted: %s" % (source, r["errors"]))
    rows = base()
    rows[0]["locator"] = ""
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A1 is a FACT with no locator"), "a FACT with no locator was accepted")
    rows = base()
    rows[0]["source_id"] = "S2"
    need(b.check(rows)[0] == 0, "the valid neighbour (a secondary source read in part, with a locator) was refused")
    rows[0]["source_id"] = "S3; S2"
    need(b.check(rows)[0] == 0, "a FACT with one weak and one sound source was refused")
    rows = base()
    rows[1]["source_id"] = ""
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A2 is REPORTED with no source"), "a REPORTED row with no source was accepted")
    rows[1]["status"] = "ASSESSMENT"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "A2 is an ASSESSMENT with no source and no detail"), "an ASSESSMENT with no basis was accepted")
    rows[1]["detail"] = "Inferred from the order for materials."
    need(b.check(rows)[0] == 0, "the valid neighbour (an ASSESSMENT that says its basis) was refused")
    srcs = sources()
    srcs[0]["accessed"] = ""
    code, r = b.check_json(base(), srcs)
    need(code == 1 and has(r["errors"], "S1", "accessed is blank"), "an opened source with no access date was accepted")


def test_weak_sourcing_is_listed(b):
    rows = base()
    rows[1]["source_id"] = "S4"
    code, r = b.check_json(rows)
    need(code == 0 and r["weak"] == ["A2"] and has(r["advisories"], "rest only on sources below secondary tier", "A2"), "weak: %s" % r["weak"])
    need(b.check_json(base())[1]["weak"] == [], "the valid neighbour was listed as weakly sourced")


# ---------------- conflicts are two rows, recorded on both ----------------

def pair(d1, p1, d2, p2, cls, **more):
    rows = [ev("C1", d1, p1, "Bridge reopened", "FACT", "S1"), ev("C2", d2, p2, "Bridge reopened")]
    rows[0]["conflicts_with"] = "C2" + ((":" + cls) if cls else "")
    rows[1]["conflicts_with"] = "C1" + ((":" + cls) if cls else "")
    for k, v in more.items():
        rows[int(k[1]) - 1][k[3:]] = v
    return rows


def test_conflict_must_be_recorded_on_both_rows(b):
    rows = pair("2024-09-09", "day", "2024-09-16", "day", "disagreement")
    rows[1]["conflicts_with"] = ""
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "C1 lists a conflict with C2, but C2 does not list C1"), "a one-sided conflict was accepted: %s" % r["errors"])
    rows = pair("2024-09-09", "day", "2024-09-16", "day", "disagreement")
    code, r = b.check_json(rows)
    need(code == 0 and len(r["conflicts"]) == 1 and r["conflicts"][0]["dates"] == "not compatible", "the valid neighbour was not accepted as one pair")
    rows[1]["conflicts_with"] = "C1:announcement"
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "different classes"), "two different classes on one pair were accepted")


def test_conflicting_dates_stay_as_two_rows(b):
    rows = pair("2024-09-09", "day", "2024-09-16", "day", "disagreement")
    code, r = b.check_json(rows)
    need(r["order"] == ["C1", "C2"] and r["conflicts"][0]["a_date"] == "9 Sep 2024" and r["conflicts"][0]["b_date"] == "16 Sep 2024",
         "a conflicting pair was not kept as two rows with their own dates: %s" % r["conflicts"])


def test_precision_class_needs_compatible_dates(b):
    code, r = b.check_json(pair("2024-03-18", "day", "2024-03", "month", "precision"))
    need(code == 0 and r["conflicts"][0]["dates"] == "compatible", "a day inside its month was not accepted as compatible")
    code, r = b.check_json(pair("2024-04-01", "day", "2024-03", "month", "precision"))
    need(code == 1 and has(r["errors"], "classed precision", "cannot both be right"), "a day outside the month was accepted as precision-compatible")
    code, r = b.check_json(pair("2024-03-31", "day", "2024-03", "month", "precision"))
    need(code == 0, "the valid neighbour (the last day of the month) was refused")
    code, r = b.check_json(pair("2024-03-18", "day", "2024-03", "month", ""))
    need(code == 0 and has(r["advisories"], "no class", "compatible: probably precision"), "an unclassed compatible pair got no hint: %s" % r["advisories"])
    code, r = b.check_json(pair("2024-03-18", "day", "2024-04-02", "day", ""))
    need(code == 0 and has(r["advisories"], "no class", "not compatible"), "an unclassed incompatible pair got no hint")
    code, r = b.check_json(pair("2024-03-18", "day", "2024-03", "month", "disagreement"))
    need(code == 0 and has(r["advisories"], "classed disagreement", "compatible"), "a disagreement with compatible dates got no advisory")


def test_timezone_class(b):
    rows = pair("2024-09-01", "day", "2024-09-02", "day", "timezone", r1_time="23:30 -05:00", r2_time="06:30 +02:00")
    code, r = b.check_json(rows)
    need(code == 0 and r["conflicts"][0]["dates"] == "the same instant", "the same instant in two zones was not recognised: %s" % r["conflicts"])
    rows = pair("2024-09-01", "day", "2024-09-02", "day", "timezone", r1_time="23:30 -05:00", r2_time="06:31 +02:00")
    code, r = b.check_json(rows)
    need(code == 1 and has(r["errors"], "classed timezone", "differ by 1 minute"), "instants one minute apart were accepted as a time zone difference")
    code, r = b.check_json(pair("2024-09-01", "day", "2024-09-04", "day", "timezone"))
    need(code == 1 and has(r["errors"], "classed timezone", "no more than a day apart"), "dates three days apart were accepted as a time zone difference")
    code, r = b.check_json(pair("2024-09-01", "day", "2024-09-02", "day", "timezone"))
    need(code == 0 and has(r["advisories"], "classed timezone", "cannot be confirmed"), "an unconfirmable time zone class got no advisory")


def test_same_title_different_dates_is_flagged(b):
    rows = [ev("C1", "2024-09-09", "day", "Bridge reopened", "FACT", "S1"), ev("C2", "2024-09-16", "day", "bridge  reopened")]
    code, r = b.check_json(rows)
    need(code == 0 and has(r["advisories"], "C1 and C2 have the same title and different dates"), "no advisory: %s" % r["advisories"])
    need(not has(b.check_json(pair("2024-09-09", "day", "2024-09-16", "day", "disagreement"))[1]["advisories"], "same title"), "a marked pair was flagged")


# ---------------- order ----------------

def test_order_rule_and_stability(b):
    rows = [ev("D", "2024-01-01", "day"), ev("T9", "2024-01-01", "day", time="09:00 UTC"), ev("M", "2024-01", "month"), ev("Y", "2024", "year"),
            ev("T8", "2024-01-01", "day", time="08:00 local"), ev("X1", "2024-02-10", "day"), ev("X2", "2024-02-10", "day"),
            ev("AP", "2024-02-10", "approx"), ev("E", "2023-12-31", "day")]
    code, r = b.check_json(rows)
    need(r["order"] == ["E", "Y", "M", "D", "T8", "T9", "X1", "X2", "AP"], "order: %s" % r["order"])
    rows[5], rows[6] = rows[6], rows[5]
    code, r = b.check_json(rows)
    need(r["order"][6:8] == ["X2", "X1"], "rows with the same date did not keep file order: %s" % r["order"])
    need("not a claim" in r["order_rule"], "the order rule does not say the listing is not a claim of sequence")


def test_instants_against_written_order_are_flagged(b):
    rows = [ev("P", "2024-09-01", "day", time="23:30 -05:00"), ev("Q", "2024-09-02", "day", time="03:00 UTC")]
    code, r = b.check_json(rows, None, "--before", "P", "Q")
    need(r["order"] == ["P", "Q"], "written order: %s" % r["order"])
    need(has(r["advisories"], "P is listed before Q", "90 minute(s) later"), "no advisory that the instants run the other way: %s" % r["advisories"])
    need(verdict(r, "P", "Q")["verdict"] == "violated" and code == 1, "P before Q should be violated by the recorded instants")


# ---------------- sequence checks ----------------

def seq(b, rows, a, c, *args):
    code, r = b.check_json(rows, None, "--before", a, c, *args)
    return code, verdict(r, a, c)


def test_before_day_against_day(b):
    rows = [ev("A", "2024-03-18", "day"), ev("B", "2024-03-20", "day"), ev("C", "2024-03-19", "day"), ev("D", "2024-03-18", "day")]
    code, v = seq(b, rows, "A", "B")
    need(code == 0 and v["verdict"] == "holds" and "caveat" not in v, "18 before 20 March: %s" % v)
    code, v = seq(b, rows, "B", "A")
    need(code == 1 and v["verdict"] == "violated", "20 before 18 March was not a violation: %s" % v)
    code, v = seq(b, rows, "A", "D")
    need(code == 0 and v["verdict"] == "undecided" and "same day" in v["reason"], "the same day was decided: %s" % v)
    code, v = seq(b, rows, "A", "C")
    need(v["verdict"] == "holds" and "one calendar day apart" in v.get("caveat", ""), "one day apart has no zone caveat: %s" % v)


def test_before_month_against_a_day_inside_it_is_undecided(b):
    rows = [ev("M", "2024-03", "month"), ev("D", "2024-03-19", "day"), ev("L", "2024-03-31", "day"), ev("N", "2024-04-01", "day"), ev("F", "2024-02-29", "day")]
    for a, c in (("M", "D"), ("D", "M"), ("M", "L"), ("L", "M")):
        code, v = seq(b, rows, a, c)
        need(code == 0 and v["verdict"] == "undecided", "%s before %s was reported as %s. A month does not say which day: %s" % (a, c, v["verdict"], v["reason"]))
        need("known only to the month" in v["reason"], "the reason does not name the precision: %s" % v["reason"])
    code, v = seq(b, rows, "M", "N")
    need(code == 0 and v["verdict"] == "holds", "the valid neighbour (March before 1 April) was %s" % v["verdict"])
    code, v = seq(b, rows, "F", "M")
    need(code == 0 and v["verdict"] == "holds", "the valid neighbour (29 February before March) was %s" % v["verdict"])
    code, v = seq(b, rows, "N", "M")
    need(code == 1 and v["verdict"] == "violated", "1 April before March was %s" % v["verdict"])


def test_before_year_and_approximate(b):
    rows = [ev("Y", "2024", "year"), ev("D", "2024-06-28", "day"), ev("E", "2025-01-01", "day"), ev("AP", "2024-06-12", "approx"), ev("K", "2024-06-27", "day"),
            ev("AM", "2024-06", "approx"), ev("J", "2024-07-31", "day"), ev("G", "2024-08-01", "day")]
    need(seq(b, rows, "Y", "D")[1]["verdict"] == "undecided", "a year against a day inside it was decided")
    need(seq(b, rows, "Y", "E")[1]["verdict"] == "holds", "2024 before 1 January 2025 was not held")
    need(seq(b, rows, "AP", "D")[1]["verdict"] == "holds", "about 12 June (15 days each side) before 28 June was not held")
    code, v = seq(b, rows, "AP", "K")
    need(v["verdict"] == "undecided" and "approximate" in v["reason"], "about 12 June before 27 June was decided: %s" % v)
    need(seq(b, rows, "AP", "K", "--approx-days", "14")[1]["verdict"] == "holds", "with --approx-days 14, about 12 June before 27 June should hold")
    need(seq(b, rows, "AM", "J")[1]["verdict"] == "undecided", "about June (May to July) before 31 July was decided")
    need(seq(b, rows, "AM", "G")[1]["verdict"] == "holds", "about June before 1 August was not held")


def test_before_with_instants_and_unknown_ids(b):
    rows = [ev("P", "2024-09-01", "day", time="23:30 -05:00"), ev("Q", "2024-09-02", "day", time="06:30 +02:00"), ev("R", "2024-09-02", "day", time="06:31 +02:00"),
            ev("L", "2024-09-02", "day", time="09:00 local")]
    need(seq(b, rows, "P", "Q")[1]["verdict"] == "undecided", "the same instant was decided")
    need(seq(b, rows, "P", "R")[1]["verdict"] == "holds", "one minute apart by instants was not held")
    need(seq(b, rows, "Q", "L")[1]["verdict"] == "undecided", "a zoned time against a local time on the same day was decided")
    code, out, err = b.check(rows, None, "--before", "P", "ZZ")
    need(code == 1 and "ZZ is not an event id" in out, "an unknown id in --before was accepted (exit %d)" % code)


# ---------------- gaps ----------------

def test_gap_boundary(b):
    rows = [ev("A", "2024-01-01", "day"), ev("B", "2024-04-10", "day")]
    code, r = b.check_json(rows, None, "--gap-days", "99")
    need(r["gaps"] and r["gaps"][0]["at_least_days"] == 100 and r["gaps"][0]["after"] == "A" and r["gaps"][0]["before"] == "B", "gaps: %s" % r["gaps"])
    code, r = b.check_json(rows, None, "--gap-days", "100")
    need(r["gaps"] == [], "a gap of exactly 100 days was listed at --gap-days 100")


def test_gap_uses_the_whole_window_of_an_imprecise_date(b):
    rows = [ev("A", "2024-01", "month"), ev("B", "2024-04-10", "day")]
    code, r = b.check_json(rows, None, "--gap-days", "90")
    need(r["gaps"] == [], "a month-precision event was treated as its first day: a 70 day certain gap was reported as %s" % r["gaps"])
    code, r = b.check_json(rows, None, "--gap-days", "69")
    need(r["gaps"] and r["gaps"][0]["at_least_days"] == 70 and r["gaps"][0]["from"] == "2024-01-31", "gaps: %s" % r["gaps"])
    rows = [ev("Y", "2024", "year"), ev("A", "2024-02-01", "day"), ev("B", "2024-11-01", "day")]
    need(b.check_json(rows, None, "--gap-days", "90")[1]["gaps"] == [], "a gap was reported inside a year in which a year-precision event could fall anywhere")
    rows = [ev("A", "2024-01-01", "day", end_date="2024-03-01"), ev("B", "2024-04-10", "day")]
    code, r = b.check_json(rows, None, "--gap-days", "39")
    need(r["gaps"] and r["gaps"][0]["at_least_days"] == 40, "an end date did not shorten the gap: %s" % r["gaps"])


def test_future_dates_are_flagged_only_with_today(b):
    code, r = b.check_json(base(), None, "--today", "2024-08-31")
    need(code == 0 and has(r["advisories"], "A6", "scheduled date"), "a date after --today was not flagged")
    need(not has(b.check_json(base(), None, "--today", "2024-09-01")[1]["advisories"], "scheduled date"), "the valid neighbour (dated on --today) was flagged")
    need(not has(b.check_json(base())[1]["advisories"], "scheduled date"), "a scheduled-date note appeared with no --today")


# ---------------- input handling ----------------

def test_unreadable_input_exits_2(b):
    good_e, good_s = to_csv(ECOLS, base()), to_csv(SCOLS, sources())
    cases = {"latin-1 bytes": good_e.replace(b"Works began", b"Caf" + bytes([0xE9])), "NUL byte": good_e + bytes([0]), "empty file": b"",
             "unclosed quote": good_e.replace(b"Works began", b'"Works began')}
    for name, raw in cases.items():
        code, out, err = b.check(raw, good_s)
        need(code == 2 and err.strip() and "Traceback" not in err, "%s: exit %d, stderr %r" % (name, code, err[:120]))
    code, out, err = b.check(bytes([0xEF, 0xBB, 0xBF]) + good_e, bytes([0xEF, 0xBB, 0xBF]) + good_s)
    need(code == 0, "the valid neighbour (UTF-8 with a byte-order mark) was refused: %d %s" % (code, err))
    code, out, err = b.run("chronology_check.py", b.tmp / "missing.csv", b.write(good_s))
    need(code == 2, "a missing file gave exit %d" % code)


def test_columns(b):
    cols = [c for c in ECOLS if c != "locator"]
    code, out, err = b.check(to_csv(cols, base()))
    need(code == 1 and "has no column(s): locator" in out, "a missing column was accepted (exit %d)" % code)
    rows = base()
    for r in rows:
        r["owner"] = "x"
    code, r = b.check_json(to_csv(ECOLS + ["owner"], rows))
    need(code == 0 and has(r["advisories"], "does not read: owner"), "an extra column was not reported")
    raw = to_csv(ECOLS, base()).replace(b"A2,2024-03,month,", b"A2,2024-03,month,extra,")
    code, r = b.check_json(raw)
    need(code == 1 and has(r["errors"], "cell(s)"), "a row with too many cells was accepted")
    shuffled = list(reversed(ECOLS))
    need(b.check(to_csv(shuffled, base()))[0] == 0, "columns in another order were refused")


def test_strict_arguments(b):
    e, s = b.write(to_csv(ECOLS, base())), b.write(to_csv(SCOLS, sources()))
    for args in ([e, s, "--frobnicate"], [e, s, "--gap-days"], [e, s, "--gap-days", "-1"], [e, s, "--gap-days", "3.5"], [e, s, "--before", "A1"],
                 [e, s, "--today", "20240901"], [e, s, "--today", "2024-02-30"], [e], [e, s, s]):
        code, out, err = b.run("chronology_check.py", *args)
        need(code == 2 and "Traceback" not in err and len(err.strip().splitlines()) == 1, "%s: exit %d, stderr %r" % (args[2:], code, err[:160]))
    need(b.run("chronology_check.py", e, s, "--gap-days", "0", "--today", "2024-09-01")[0] == 0, "the valid neighbours (--gap-days 0, a real --today) were refused")


def test_inputs_are_not_modified_and_output_is_ascii(b):
    rows = base()
    rows[1]["title"] = "Works began " + chr(0x2014) + " caf" + chr(0xE9)
    e, s = b.write(to_csv(ECOLS, rows)), b.write(to_csv(SCOLS, sources()))
    before = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (e, s)]
    for flag in ((), ("--json",)):
        code, out, err = b.run("chronology_check.py", e, s, *flag)
        need(code == 0 and all(ord(c) < 128 for c in out), "non-ASCII output or failure with %s" % (flag or "text",))
    out_file = b.path(".html")
    b.run("build_timeline.py", e, s, "--out", out_file)
    need(before == [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (e, s)], "an input file was changed by a run")


# ---------------- the builder ----------------

def embedded(path):
    text = Path(path).read_text(encoding="utf-8")
    start = text.index('<script type="application/json" id="timeline-data">') + len('<script type="application/json" id="timeline-data">')
    return text, json.loads(text[start:text.index("</script>", start)])


def test_builder_refuses_data_that_fails_the_checker(b):
    rows = base()
    rows[1]["date"] = "2024-03-01"
    out_file = b.path(".html")
    code, out, err = b.run("build_timeline.py", b.write(to_csv(ECOLS, rows)), b.write(to_csv(SCOLS, sources())), "--out", out_file, "--template", TEMPLATE)
    need(code == 1 and "nothing was written" in out and not out_file.exists(), "a page was built from data that fails the checker (exit %d)" % code)
    rows[1]["date"] = "2024-03"
    code, out, err = b.run("build_timeline.py", b.write(to_csv(ECOLS, rows)), b.write(to_csv(SCOLS, sources())), "--out", out_file, "--template", TEMPLATE)
    need(code == 0 and out_file.exists(), "the valid neighbour was not built: %d %s %s" % (code, out, err))


def test_builder_embeds_dates_as_written(b):
    out_file = b.path(".html")
    e, s = b.write(to_csv(ECOLS, base())), b.write(to_csv(SCOLS, sources()))
    code, out, err = b.run("build_timeline.py", e, s, "--out", out_file, "--title", "SYNTHETIC test", "--template", TEMPLATE)
    need(code == 0, "build failed: %s %s" % (out, err))
    text, data = embedded(out_file)
    got = {x["id"]: (x["date"], x["precision"]) for x in data["events"]}
    need(got == {"A3": ("2024", "year"), "A2": ("2024-03", "month"), "A1": ("2024-03-19", "day"), "A4": ("2024-06-12", "approx"),
                 "A6": ("2024-09-01", "day"), "A5": ("", "undated")}, "embedded dates: %s" % got)
    need([x["id"] for x in data["events"]] == ["A3", "A2", "A1", "A4", "A6", "A5"], "embedded order: %s" % [x["id"] for x in data["events"]])
    by = {x["id"]: x for x in data["events"]}
    need(by["A2"]["l"] - by["A2"]["e"] == 30 and by["A3"]["l"] - by["A3"]["e"] == 365 and by["A4"]["l"] - by["A4"]["e"] == 30 and by["A5"]["e"] is None,
         "embedded windows are not the whole month, the whole year and 15 days each side")
    need(data["app"] == "chronology-timeline" and data["schema"] == 1 and data["title"] == "SYNTHETIC test" and "<title>SYNTHETIC test</title>" in text, "title or envelope")
    again = b.path(".html")
    code, out, err = b.run("build_timeline.py", e, s, "--out", again, "--title", "SYNTHETIC test", "--template", TEMPLATE, "--json")
    need(Path(out_file).read_bytes() == Path(again).read_bytes(), "two builds from the same inputs differ")
    info = json.loads(out)
    need(code == 0 and info["events"] == 6 and info["undated"] == 1 and info["bytes"] == Path(again).stat().st_size and info["errors"] == [], "--json result: %s" % info)


def test_builder_embeds_awkward_text_safely(b):
    rows = base()
    rows[0]["title"] = 'Notice </script><script>alert(1)</script> & "quoted" <!-- x'
    out_file = b.path(".html")
    code, out, err = b.run("build_timeline.py", b.write(to_csv(ECOLS, rows)), b.write(to_csv(SCOLS, sources())), "--out", out_file, "--template", TEMPLATE)
    need(code == 0, "build failed")
    text, data = embedded(out_file)
    need(next(x for x in data["events"] if x["id"] == "A1")["title"] == rows[0]["title"], "the title did not survive embedding unchanged")
    need("alert(1)</script>" not in text and text.count("</script>") == TEMPLATE.read_text(encoding="utf-8").count("</script>"), "a value closed the data block")


def test_builder_arguments(b):
    e, s = b.write(to_csv(ECOLS, base())), b.write(to_csv(SCOLS, sources()))
    for args in ([e, s], [e, s, "--out"], [e, s, "--out", e, "--template", TEMPLATE], [e, s, "--out", b.path(".html"), "--nope"], [e, "--out", b.path(".html")]):
        code, out, err = b.run("build_timeline.py", *args)
        need(code == 2 and "Traceback" not in err, "%s: exit %d %r" % ([str(a)[-12:] for a in args[2:]], code, err[:120]))
    code, out, err = b.run("build_timeline.py", e, s, "--out", b.path(".html"), "--template", b.tmp / "no-such-template.html")
    need(code == 3 and "NOT RUN" in out, "a missing template gave exit %d" % code)
    bad = b.path(".html")
    bad.write_text("<html><body>no data block</body></html>", encoding="utf-8")
    code, out, err = b.run("build_timeline.py", e, s, "--out", b.path(".html"), "--template", bad)
    need(code == 2 and "exactly one timeline-data block" in err, "a template with no data block gave exit %d" % code)


def test_fixtures_pass_and_have_every_feature(b):
    fx = HERE / "fixtures"
    code, out, err = b.run("chronology_check.py", fx / "events.csv", fx / "sources.csv", "--json")
    r = json.loads(out)
    need(code == 0 and r["errors"] == [], "the fixtures beside this script do not pass: %s" % r["errors"])
    need({p["class"] for p in r["conflicts"]} == {"precision", "timezone", "announcement", "disagreement", ""}, "fixture conflict classes: %s" % [p["class"] for p in r["conflicts"]])
    need({e["precision"] for e in r["events"]} == {"day", "month", "year", "approx", "undated"}, "fixture precisions")
    need(len(r["gaps"]) == 1 and r["gaps"][0]["at_least_days"] == 241, "fixture gaps: %s" % r["gaps"])


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

# Planted faults. "old" must appear in the file exactly once; it is replaced by "new" in a temporary copy.
MUTANTS = [
    {"name": "a month-precision date is treated as the first of the month, so a false A precedes B is reported", "file": "chronology_check.py",
     "old": '        return "month", dt.date(y, mo, 1), dt.date(y, mo, calendar.monthrange(y, mo)[1])',
     "new": '        return "month", dt.date(y, mo, 1), dt.date(y, mo, 1)',
     "caught_by": "test_before_month_against_a_day_inside_it_is_undecided"},
    {"name": "a date more precise than its stated precision is accepted", "file": "chronology_check.py",
     "old": '                if p != "approx" and form != p:', "new": '                if False:',
     "caught_by": "test_month_precision_written_as_a_day_is_refused"},
    {"name": "dates without hyphens are accepted", "file": "chronology_check.py",
     "old": 'YMD = re.compile(r"(\\d{4})-(\\d{2})-(\\d{2})")', "new": 'YMD = re.compile(r"(\\d{4})-?(\\d{2})-?(\\d{2})")',
     "caught_by": "test_bad_dates_are_refused"},
    {"name": "a FACT is accepted on a source that was not opened", "file": "chronology_check.py",
     "old": 'if not any(s["tier"] in GOOD_TIERS and s["read_level"] in OPENED for s in cited):', "new": 'if not any(s["tier"] in GOOD_TIERS for s in cited):',
     "caught_by": "test_fact_needs_an_opened_secondary_source_and_a_locator"},
    {"name": "a conflict recorded on one row only is accepted", "file": "chronology_check.py",
     "old": '            back = [c for o, c in by_id[other]["conflicts"] if o == e["id"]]',
     "new": '            back = [c for o, c in by_id[other]["conflicts"] if o == e["id"]] or [cls]',
     "caught_by": "test_conflict_must_be_recorded_on_both_rows"},
    {"name": "a pair classed precision is not checked for compatible dates", "file": "chronology_check.py",
     "old": '            if not overlap:\n                errors.append("events %s are classed precision', "new": '            if False:\n                errors.append("events %s are classed precision',
     "caught_by": "test_precision_class_needs_compatible_dates"},
    {"name": "an approximate date is given no window", "file": "chronology_check.py",
     "old": 'ev["wlow"], ev["whigh"] = widen(form, low, high, approx_days) if p == "approx" else (low, high)', "new": 'ev["wlow"], ev["whigh"] = (low, high)',
     "caught_by": "test_before_year_and_approximate"},
    {"name": "the gap threshold is off by one day", "file": "chronology_check.py",
     "old": '            if days > gap_days:', "new": '            if days >= gap_days:', "caught_by": "test_gap_boundary"},
    {"name": "an undated row is placed at the start of the order", "file": "chronology_check.py",
     "old": '    out["order"] = [e["id"] for e in dated]', "new": '    out["order"] = [e["id"] for e in undated] + [e["id"] for e in dated]',
     "caught_by": "test_undated_rows_are_listed_apart_and_never_placed"},
    {"name": "the builder writes a page even when the checker reports errors", "file": "build_timeline.py",
     "old": '    if res["errors"]:\n        if "--json" in flags:', "new": '    if False:\n        if "--json" in flags:',
     "caught_by": "test_builder_refuses_data_that_fails_the_checker"},
    {"name": "the builder embeds text without escaping angle brackets", "file": "build_timeline.py",
     "old": '    return text.replace("<", bs + "u003c").replace(">", bs + "u003e").replace("&", bs + "u0026")', "new": '    return text',
     "caught_by": "test_builder_embeds_awkward_text_safely"},
]


def run_suite(folder, only=None, quiet=False):
    tmp = tempfile.mkdtemp(prefix="chronology-test-")
    failed = []
    try:
        box = Box(folder, tmp)
        for t in TESTS:
            if only and t.__name__ != only:
                continue
            try:
                t(box)
                if not quiet:
                    print("PASS  " + t.__name__)
            except AssertionError as e:
                failed.append(t.__name__)
                if not quiet:
                    print("FAIL  %s\n      %s" % (t.__name__, str(e).replace("\n", "\n      ")[:900]))
            except Exception as e:  # noqa: BLE001  a crash in the script under test is a failed test
                failed.append(t.__name__)
                if not quiet:
                    print("FAIL  %s\n      %s: %s" % (t.__name__, type(e).__name__, str(e)[:300]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return failed


def run_mutants():
    survived = 0
    for m in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="chronology-mutant-")
        try:
            for s in SCRIPTS:
                shutil.copy(HERE / s, Path(tmp) / s)
            shutil.copytree(HERE / "fixtures", Path(tmp) / "fixtures")
            p = Path(tmp) / m["file"]
            src = p.read_text(encoding="utf-8")
            if src.count(m["old"]) != 1:
                print("BROKEN    %s: the text to replace appears %d times in %s, not once" % (m["name"], src.count(m["old"]), m["file"]))
                survived += 1
                continue
            p.write_text(src.replace(m["old"], m["new"]), encoding="utf-8")
            failed = run_suite(tmp, quiet=True)
            if m["caught_by"] in failed:
                print("CAUGHT    %s\n          by %s (%d test(s) failed in all: %s)" % (m["name"], m["caught_by"], len(failed), ", ".join(failed)))
            else:
                survived += 1
                print("SURVIVED  %s\n          %s did not fail. Tests that failed: %s" % (m["name"], m["caught_by"], ", ".join(failed) or "none"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d planted fault(s), %d caught, %d not caught" % (len(MUTANTS), len(MUTANTS) - survived, survived))
    return 1 if survived else 0


def main(argv):
    only, folder, mutants, it = None, HERE, False, iter(argv)
    for a in it:
        if a == "--mutants":
            mutants = True
        elif a in ("--only", "--dir"):
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_chronology: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--only":
                only = v
            else:
                folder = Path(v)
        else:
            print("test_chronology: unknown argument " + a, file=sys.stderr)
            return 2
    if only and only not in [t.__name__ for t in TESTS]:
        print("test_chronology: no test named " + only, file=sys.stderr)
        return 2
    if not all((Path(folder) / s).is_file() for s in SCRIPTS) or not TEMPLATE.is_file():
        print("test_chronology: %s must hold %s, and the viewer template must be at %s" % (folder, " and ".join(SCRIPTS), TEMPLATE), file=sys.stderr)
        return 2
    if mutants:
        return run_mutants()
    failed = run_suite(folder, only)
    ran = 1 if only else len(TESTS)
    print("\n%d test(s) run, %d passed, %d failed" % (ran, ran - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.exit(main(sys.argv[1:]))
