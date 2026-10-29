#!/usr/bin/env python3
"""Embed a checked timeline into the single-file viewer. Standard library only.

Usage:
  python build_timeline.py EVENTS.csv SOURCES.csv --out FILE.html [--title T]
                           [--gap-days N] [--approx-days N] [--template PATH] [--json]

EVENTS.csv and SOURCES.csv are in the format chronology_check.py reads. chronology_check.py must
sit beside this script: the two files are checked with it first, and nothing is written if it
reports an error. The viewer template is ../assets/timeline.html relative to this script unless
--template names another copy.

What it does: runs the checker, puts the events in the checker's reading order with each date's
possible range, the sources and the conflict pairs into the template's data block as JSON, and
writes the result to --out. The same inputs always give the same file. Text is embedded as data;
the characters <, > and & are written as JSON escapes so no value can close the data block.

What it enforces (exit 1, nothing written): any checker error. Advisories are printed and do not
stop the build. --json prints the result as one JSON object: written, bytes, counts, errors and
advisories.
What it refuses (exit 2): a missing --out, an --out that is one of the inputs or the template, a
template without exactly one data block.

It cannot tell whether the rows are true. A built page is a view of the CSV, no more.

Exit codes: 0 written. 1 the data failed the checker. 2 bad arguments or unreadable input.
3 could not run because chronology_check.py or the template is missing (prints NOT RUN).
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
try:
    import chronology_check as cc
except ImportError:
    print("NOT RUN: build_timeline needs chronology_check.py in the same folder")
    sys.exit(3)

APP, SCHEMA = "chronology-timeline", 1
BLOCK = re.compile(r'(<script type="application/json" id="timeline-data">)(.*?)(</script>)', re.S)
EPOCH = dt.date(1970, 1, 1).toordinal()
FLAGS = {"--json"}
VALUES = {"--out": 1, "--title": 1, "--gap-days": 1, "--approx-days": 1, "--template": 1}


def day_number(iso):
    return dt.date.fromisoformat(iso).toordinal() - EPOCH if iso else None


def label_for(n):
    """A, B ... Z, AA, AB ... for conflict pairs."""
    text = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        text = chr(65 + r) + text
    return text


def build_data(res, title, events_name, sources_name):
    by_id = {e["id"]: e for e in res["events"]}
    rows = []
    for i in res["order"] + res["undated"]:
        e = by_id[i]
        rows.append({"id": e["id"], "date": e["date"], "precision": e["precision"], "end": e["end_date"], "time": e["time"],
                     "title": e["title"], "detail": e["detail"], "actors": e["actors"], "sources": e["sources"], "locator": e["locator"],
                     "status": e["status"], "tags": e["tags"], "conflicts": e["conflicts"],
                     "e": day_number(e["earliest"]), "l": day_number(e["span_latest"])})
    order = {r["id"]: n for n, r in enumerate(rows)}
    pairs = sorted(res["conflicts"], key=lambda p: (order.get(p["a"], 0), order.get(p["b"], 0)))
    conflicts = [{"a": p["a"], "b": p["b"], "cls": p["class"], "dates": p.get("dates", "not compared"), "label": label_for(n)} for n, p in enumerate(pairs)]
    sources = [dict(v, id=k) for k, v in res["sources"].items()]
    for s in sources:
        s.pop("source_id", None)
    return {"app": APP, "schema": SCHEMA, "title": title, "built_from": {"events": events_name, "sources": sources_name},
            "gap_days": res["settings"]["gap_days"], "approx_days": res["settings"]["approx_days"], "order_rule": res["order_rule"],
            "events": rows, "sources": sources, "conflicts": conflicts}


def safe_json(data):
    """JSON that cannot close a script element or start a comment, built without typing an escape."""
    text = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    bs = chr(92)
    return text.replace("<", bs + "u003c").replace(">", bs + "u003e").replace("&", bs + "u0026")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    flags, opts, paths = cc.parse_args(argv, "build_timeline", FLAGS, VALUES)
    if len(paths) != 2:
        print("build_timeline: expected EVENTS.csv and SOURCES.csv, got %d file(s)" % len(paths), file=sys.stderr)
        return 2
    if "--out" not in opts:
        print("build_timeline: --out FILE.html is required", file=sys.stderr)
        return 2
    gap = cc.whole(opts, "--gap-days", 90, "build_timeline")
    approx = cc.whole(opts, "--approx-days", 15, "build_timeline")
    title = " ".join(opts.get("--title", ["Timeline"])[-1].split()) or "Timeline"
    template = Path(opts["--template"][-1]) if "--template" in opts else Path(__file__).resolve().parent.parent / "assets" / "timeline.html"
    out = Path(opts["--out"][-1])
    if not template.is_file():
        print("NOT RUN: the viewer template was not found at %s" % template)
        return 3
    try:
        same = [p for p in (Path(paths[0]), Path(paths[1]), template) if p.resolve() == out.resolve()]
    except OSError:
        same = []
    if same:
        print("build_timeline: --out is the same file as %s; inputs are never written to" % same[0], file=sys.stderr)
        return 2
    try:
        res = cc.run(paths[0], paths[1], gap, approx)
        page = template.read_bytes().decode("utf-8-sig")
    except cc.InputError as e:
        print("build_timeline: %s" % e, file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as e:
        print("build_timeline: cannot read the template %s: %s" % (template, e), file=sys.stderr)
        return 2
    if len(BLOCK.findall(page)) != 1:
        print("build_timeline: %s does not have exactly one timeline-data block" % template, file=sys.stderr)
        return 2
    if res["errors"]:
        if "--json" in flags:
            cc.emit(json.dumps({"written": None, "errors": res["errors"], "advisories": res["advisories"]}, indent=1, ensure_ascii=True))
        else:
            cc.emit("\n".join(["build_timeline: the data failed chronology_check, so nothing was written"] + ["  ERROR     " + m for m in res["errors"]]
                              + ["RESULT: NOT BUILT. %d error(s). Fix the CSV and run again." % len(res["errors"])]))
        return 1
    data = build_data(res, title, Path(paths[0]).name, Path(paths[1]).name)
    blob = safe_json(data)
    page = BLOCK.sub(lambda m: m.group(1) + blob + m.group(3), page, count=1)
    page = re.sub(r"<title>.*?</title>", lambda m: "<title>" + title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</title>", page, count=1, flags=re.S)
    try:
        out.write_bytes(page.encode("utf-8"))
    except OSError as e:
        print("build_timeline: cannot write %s: %s" % (out, e.strerror or e), file=sys.stderr)
        return 2
    n = {k: sum(1 for c in data["conflicts"] if c["cls"] == k) for k in ("precision", "timezone", "announcement", "disagreement", "")}
    if "--json" in flags:
        cc.emit(json.dumps({"written": str(out), "bytes": len(page.encode("utf-8")), "events": len(data["events"]), "dated": res["counts"]["dated"],
                            "undated": res["counts"]["undated"], "sources": len(data["sources"]), "conflict_pairs": len(data["conflicts"]),
                            "conflicts_by_class": {(k or "not classed"): v for k, v in n.items()}, "errors": [], "advisories": res["advisories"]},
                           indent=1, ensure_ascii=True))
        return 0
    cc.emit("\n".join(
        ["build_timeline: wrote %s (%d bytes)" % (out, len(page.encode("utf-8"))),
         "  %d event(s): %d dated, %d undated. %d source(s). %d conflict pair(s): %d disagreement, %d announcement, %d precision, %d timezone, %d not classed."
         % (len(data["events"]), res["counts"]["dated"], res["counts"]["undated"], len(data["sources"]), len(data["conflicts"]),
            n["disagreement"], n["announcement"], n["precision"], n["timezone"], n[""])]
        + ["  ADVISORY  " + m for m in res["advisories"]]
        + ["RESULT: BUILT. The page is a view of the CSV; it has not been opened or looked at by this script."]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
