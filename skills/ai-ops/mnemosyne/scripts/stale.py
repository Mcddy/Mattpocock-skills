#!/usr/bin/env python3
"""List continuity entries that are due for review. Standard library only. Reads files, changes nothing.

Usage:
  python stale.py <folder-or-file> [<file> ...] [--today YYYY-MM-DD] [--json]

Reads decisions.md and beliefs.md (or any files given) in the formats of the templates:

  ## D-001 | 2026-01-15 | review: 2026-03-15          a decision heading
  - [2026-01-15] (confidence: likely) (review: 2026-04-15) Statement ...     a belief line

Reports three lists: OVERDUE (review date is today or earlier), UNDATED (an entry with no review
date) and MALFORMED (an entry date or review date that is not a real date written as YYYY-MM-DD;
20260301, 2026/03/01 and 2026-3-1 are all rejected). A decision whose Outcome line is filled in is
treated as closed and is not reported as overdue or undated.

Exit code 0 when the files were read, whatever was found. Exit 2 for bad arguments or no readable file.
"""
import datetime
import json
import re
import sys
from pathlib import Path

HEAD = re.compile(r"^##\s+(\S+)\s*\|\s*([^|]*?)\s*(?:\|\s*(.*))?$")
BELIEF = re.compile(r"^-\s+\[([^\]]*)\]\s*(.*)$")
REVIEW = re.compile(r"review:\s*([^\s|)]+)", re.I)


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


def scan_file(path, today, notes):
    over, undated, bad = [], [], []
    try:
        data = path.read_bytes()
    except OSError:
        return None
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        lines = data.decode("utf-8", errors="replace").splitlines()
        notes.append("%s is not valid UTF-8: unreadable bytes were replaced" % path.name)

    def judge(label, text, lineno, rest):
        m = REVIEW.search(rest)
        if not m:
            undated.append({"file": path.name, "line": lineno, "entry": label, "text": text})
            return
        d = parse_date(m.group(1))
        if d is None:
            bad.append({"file": path.name, "line": lineno, "entry": label, "text": text, "value": m.group(1), "field": "review"})
        elif d <= today:
            over.append({"file": path.name, "line": lineno, "entry": label, "text": text,
                         "review": d.isoformat(), "days_overdue": (today - d).days})

    i = 0
    while i < len(lines):
        line = lines[i]
        h = HEAD.match(line)
        if h and "|" in line:
            body, j = [], i + 1
            while j < len(lines) and not lines[j].startswith("## "):
                body.append(lines[j])
                j += 1
            closed = any(re.match(r"^Outcome:\s*\S", b) for b in body)
            first = next((b for b in body if b.lower().startswith("decision:")), "")
            if parse_date(h.group(2)) is None:
                bad.append({"file": path.name, "line": i + 1, "entry": h.group(1), "text": first[:120] or line[:120], "value": h.group(2), "field": "date"})
            if not closed:
                judge(h.group(1), first[:120] or line[:120], i + 1, h.group(3) or "")
            i = j
            continue
        b = BELIEF.match(line)
        if b:
            rest = b.group(2)
            statement = re.sub(r"^(\([^)]*\)\s*)+", "", rest)[:120]
            if parse_date(b.group(1)) is None:
                bad.append({"file": path.name, "line": i + 1, "entry": "belief " + b.group(1)[:20], "text": statement, "value": b.group(1), "field": "date"})
            judge("belief " + b.group(1), statement, i + 1, rest)
        i += 1
    return over, undated, bad


def main(argv):
    args, today, as_json = [], datetime.date.today(), False
    it = iter(argv)
    for a in it:
        if a == "--json":
            as_json = True
        elif a == "--today":
            v = next(it, None)
            d = parse_date(v) if v else None
            if d is None:
                print("stale: --today needs a date as YYYY-MM-DD", file=sys.stderr)
                return 2
            today = d
        elif a.startswith("--"):
            print("stale: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if not args:
        print(__doc__)
        return 2
    files = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            files += [p / n for n in ("decisions.md", "beliefs.md") if (p / n).is_file()]
        elif p.is_file():
            files.append(p)
    rep = {"today": today.isoformat(), "files": [], "overdue": [], "undated": [], "malformed": [], "notes": []}
    for f in files:
        got = scan_file(f, today, rep["notes"])
        if got is None:
            continue
        rep["files"].append(f.name)
        rep["overdue"] += got[0]
        rep["undated"] += got[1]
        rep["malformed"] += got[2]
    if not rep["files"]:
        print("stale: no readable decisions.md or beliefs.md in " + ", ".join(args), file=sys.stderr)
        return 2
    rep["overdue"].sort(key=lambda x: -x["days_overdue"])
    if as_json:
        out = json.dumps(rep, indent=1, ensure_ascii=True)
    else:
        L = ["stale: %d file(s) read, as of %s: %d overdue, %d undated, %d malformed"
             % (len(rep["files"]), rep["today"], len(rep["overdue"]), len(rep["undated"]), len(rep["malformed"]))]
        for x in rep["overdue"]:
            L.append("  OVERDUE   %-16s review %s (%d days)  %s  [%s:%d]" % (x["entry"], x["review"], x["days_overdue"], x["text"], x["file"], x["line"]))
        for x in rep["undated"]:
            L.append("  UNDATED   %-16s no review date  %s  [%s:%d]" % (x["entry"], x["text"], x["file"], x["line"]))
        for x in rep["malformed"]:
            L.append("  MALFORMED %-16s %s value %r is not a YYYY-MM-DD date  [%s:%d]" % (x["entry"], x["field"], x["value"], x["file"], x["line"]))
        for note in rep["notes"]:
            L.append("  NOTE      " + note)
        out = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
