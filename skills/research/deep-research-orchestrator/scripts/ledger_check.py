#!/usr/bin/env python3
"""Check a research ledger before anything is written from it. Standard library only.

Usage:
  python ledger_check.py SOURCES.csv CLAIMS.csv [--today YYYY-MM-DD] [--fresh-days 365]
                                                [--questions Q1,Q2,...] [--json]

The ledger is two CSV files (templates in assets/).

SOURCES.csv, one row per source actually consulted:
  source_id      short unique id, for example S1
  title, publisher
  address        URL or file path. Needed to find the source again
  tier           primary | peer_reviewed | secondary | aggregator | unverified
  published      YYYY-MM-DD, or blank if unknown
  accessed       YYYY-MM-DD
  read_level     full | section | snippet | relayed
                 "snippet" is a search-result extract. "relayed" is what another tool or person
                 said the source says. Neither is the source having been opened.
  family         sources that repeat one original share a family id. Blank means its own family
  notes

CLAIMS.csv, one row per atomic claim:
  claim_id       short unique id, for example C1
  question_id    which sub-question it answers
  statement      one assertion, with its value, unit and scope
  status         FACT | REPORTED | ASSESSMENT | MODEL_OUTPUT | GAP
  source_ids     ids separated by ; (blank for ASSESSMENT built on other claims, and for GAP)
  locator        where in the source: a quotation, page, section or table row
  load_bearing   yes | no   (does the answer depend on it)
  confidence     high | moderate | low  (needed for ASSESSMENT)
  conflicts_with claim ids separated by ;
  conflict_class scope_mismatch | time_supersession | method_difference | direct_conflict |
                 insufficient_evidence   (needed when conflicts_with is set)
  resolution     how the conflict was settled, or blank if it is open
  basis          optional column, for FACT rows: observed | documented | corroborated
                 observed      a measurement, or a dataset's own rows: the source is the observation
                 documented    the source is the record of the statement: what the law, standard,
                               filing or product documentation itself says, at its date
                 corroborated  a statement about the world, checked against a second independent
                               source family
                 Blank on every other status. A reported assertion is REPORTED, not a FACT.

What it enforces (ERROR, exit 1):
  - ids are unique; every reference points at something that exists; conflicts are recorded on both sides
  - a FACT has a source, a locator, at least one source that was opened (read_level full or section),
    with an address, at primary, peer_reviewed or secondary tier
    (this shows the source was opened and can be found again, not that what it says is true)
  - when the basis column is present: its values are from the list, it is set on FACT rows only,
    and a corroborated FACT rests on at least two independent families of opened sources
  - MODEL_OUTPUT is never load-bearing. To use it, open what it cites and record a new claim
  - an ASSESSMENT states its confidence
  - dates are real calendar dates written YYYY-MM-DD; fixed vocabularies are respected
What it reports for a person to decide (ADVISORY, exit 0):
  - a load-bearing FACT resting on one independent family
  - when the basis column is present: a load-bearing FACT that does not say which kind it is
  - a load-bearing claim that is only REPORTED
  - open conflicts, which must be shown in the write-up, not averaged away
  - sources past the freshness window, missing publication dates, sources never cited
  - sub-questions with no claim at all (give the list with --questions)

This checks that the ledger is internally sound and that labels match what was recorded. It cannot
tell whether a source is right, whether a locator really says what the claim says, or whether the
search was thorough. Those take reading.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TIERS = ("primary", "peer_reviewed", "secondary", "aggregator", "unverified")
FACT_TIERS = ("primary", "peer_reviewed", "secondary")
READ = ("full", "section", "snippet", "relayed")
OPENED = ("full", "section")
STATUS = ("FACT", "REPORTED", "ASSESSMENT", "MODEL_OUTPUT", "GAP")
CONF = ("high", "moderate", "low")
BASIS = ("observed", "documented", "corroborated")
CLASSES = ("scope_mismatch", "time_supersession", "method_difference", "direct_conflict", "insufficient_evidence")
SRC_COLS = ("source_id", "title", "publisher", "address", "tier", "published", "accessed", "read_level", "family", "notes")
CLAIM_COLS = ("claim_id", "question_id", "statement", "status", "source_ids", "locator", "load_bearing", "confidence",
              "conflicts_with", "conflict_class", "resolution")
FLAGS = {"--json"}
VALUES = {"--today", "--fresh-days", "--questions"}


def parse_date(text):
    if not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def read_csv(path, required):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        return None, "cannot read %s: %s" % (path, e.strerror or e)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "%s is not valid UTF-8" % path
    if "\x00" in text:
        return None, "%s contains NUL bytes; is it really a CSV file?" % path
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in required if c not in header]
        if missing:
            return None, "%s is missing column(s): %s" % (path, ", ".join(missing))
        rows = []
        for n, r in enumerate(reader, start=2):
            if None in r:
                return None, "%s line %d has more cells than the header" % (path, n)
            row = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
            if any(row.values()):
                row["_line"] = n
                rows.append(row)
    except csv.Error as e:
        return None, "%s could not be parsed as CSV (%s)" % (path, e)
    return rows, None


def ids(cell):
    return [x.strip() for x in cell.split(";") if x.strip()]


def check(sources, claims, today, fresh_days, questions):
    errors, advisories = [], []

    def err(where, msg):
        errors.append("%s: %s" % (where, msg))

    def adv(where, msg):
        advisories.append("%s: %s" % (where, msg))

    src = {}
    for s in sources:
        sid = s["source_id"]
        where = "source %s (line %d)" % (sid or "?", s["_line"])
        if not sid:
            err(where, "has no source_id")
            continue
        if sid in src:
            err(where, "duplicate source_id")
            continue
        src[sid] = s
        if s["tier"] not in TIERS:
            err(where, "tier %r is not one of %s" % (s["tier"], ", ".join(TIERS)))
        if s["read_level"] not in READ:
            err(where, "read_level %r is not one of %s" % (s["read_level"], ", ".join(READ)))
        for col in ("published", "accessed"):
            v = s[col]
            if not v:
                if col == "accessed":
                    err(where, "accessed date is missing")
                continue
            d = parse_date(v)
            if d is None:
                err(where, "%s %r is not a real date written YYYY-MM-DD" % (col, v))
            elif d > today:
                err(where, "%s %s is in the future" % (col, v))
        p, a = parse_date(s["published"]), parse_date(s["accessed"])
        if p and a and p > a:
            err(where, "published after it was accessed")

    cl = {}
    for c in claims:
        cid = c["claim_id"]
        where = "claim %s (line %d)" % (cid or "?", c["_line"])
        if not cid:
            err(where, "has no claim_id")
            continue
        if cid in cl:
            err(where, "duplicate claim_id")
            continue
        cl[cid] = c

    cited = set()
    has_basis = any("basis" in c for c in claims)
    for cid, c in cl.items():
        where = "claim %s" % cid
        st, lb = c["status"], c["load_bearing"].lower()
        basis = (c.get("basis") or "").lower()
        if st not in STATUS:
            err(where, "status %r is not one of %s" % (st, ", ".join(STATUS)))
            continue
        if lb not in ("yes", "no"):
            err(where, "load_bearing must be yes or no, got %r" % c["load_bearing"])
        if not c["statement"]:
            err(where, "has no statement")
        refs = ids(c["source_ids"])
        unknown = [r for r in refs if r not in src]
        if unknown:
            err(where, "cites unknown source(s) %s" % ", ".join(unknown))
        known = [src[r] for r in refs if r in src]
        cited.update(r for r in refs if r in src)
        if c["confidence"] and c["confidence"] not in CONF:
            err(where, "confidence %r is not one of %s" % (c["confidence"], ", ".join(CONF)))
        if basis and basis not in BASIS:
            err(where, "basis %r is not one of %s" % (c.get("basis"), ", ".join(BASIS)))
        elif basis and st != "FACT":
            err(where, "basis is for FACT rows only. A reported assertion is REPORTED with basis blank")

        if st == "FACT":
            if not refs:
                err(where, "is a FACT with no source")
            if not c["locator"]:
                err(where, "is a FACT with no locator. Record where in the source it is")
            good = [s for s in known if s["read_level"] in OPENED and s["tier"] in FACT_TIERS and s["address"]]
            if known and not good:
                why = []
                if not any(s["read_level"] in OPENED for s in known):
                    why.append("no source was opened (only snippet or relayed)")
                if not any(s["tier"] in FACT_TIERS for s in known):
                    why.append("every source is aggregator or unverified tier")
                if not any(s["address"] for s in known):
                    why.append("no source has an address")
                if not why:
                    why.append("no single source is opened, addressed and at secondary tier or better")
                err(where, "cannot be a FACT: %s. Use REPORTED, or open a better source" % "; ".join(why))
            if basis == "corroborated" and good and len({s["family"] or s["source_id"] for s in good}) < 2:
                err(where, "basis is corroborated but its opened sources are one family. Open a second independent source, or use documented or observed")
            if has_basis and not basis and lb == "yes":
                adv(where, "load-bearing FACT with no basis: say whether it is observed, documented or corroborated")
            if lb == "yes" and good:
                fams = {s["family"] or s["source_id"] for s in good}
                if len(fams) == 1 and not any(s["tier"] == "primary" for s in good):
                    adv(where, "load-bearing FACT rests on one independent source family, none of it primary")
        elif st == "REPORTED":
            if not refs:
                err(where, "is REPORTED with no source. If nothing was found it is a GAP")
            if lb == "yes":
                adv(where, "the answer depends on a claim that is only REPORTED; say so where it is used")
        elif st == "MODEL_OUTPUT":
            if lb == "yes":
                err(where, "MODEL_OUTPUT cannot be load-bearing. Open what it cites and record that as a new claim")
        elif st == "ASSESSMENT":
            if not c["confidence"]:
                err(where, "is an ASSESSMENT with no confidence")
        elif st == "GAP":
            if refs:
                adv(where, "is a GAP but cites sources; if they say something, record that as its own claim")

        others = ids(c["conflicts_with"])
        if others:
            if c["conflict_class"] not in CLASSES:
                err(where, "conflicts_with is set, so conflict_class must be one of %s" % ", ".join(CLASSES))
            for o in others:
                if o == cid:
                    err(where, "is recorded as conflicting with itself")
                elif o not in cl:
                    err(where, "conflicts_with unknown claim %s" % o)
                elif cid not in ids(cl[o]["conflicts_with"]):
                    err(where, "conflict with %s is recorded on one side only" % o)
            if not c["resolution"] and c["conflict_class"] in ("direct_conflict", "insufficient_evidence"):
                if all(o not in cl or cid < o for o in others) or lb == "yes":
                    adv(where, "open %s with %s: show both in the write-up and name what would settle it"
                        % (c["conflict_class"].replace("_", " "), ", ".join(others)))
        elif c["conflict_class"]:
            err(where, "conflict_class is set but conflicts_with is empty")

    for sid, s in src.items():
        if sid not in cited:
            adv("source %s" % sid, "is never cited. Remove it or record what it contributed")
            continue
        if not s["address"]:
            adv("source %s" % sid, "has no address, so it cannot be found again")
        if not s["published"]:
            adv("source %s" % sid, "has no publication date")
        d = parse_date(s["published"]) or parse_date(s["accessed"])
        used_lb = any(sid in ids(c["source_ids"]) and c["load_bearing"].lower() == "yes" for c in cl.values())
        if d and used_lb and (today - d).days > fresh_days:
            adv("source %s" % sid, "is %d days old and supports a load-bearing claim; recheck if the subject changes over time" % (today - d).days)

    answered = {c["question_id"] for c in cl.values() if c["question_id"]}
    for q in questions:
        if q not in answered:
            adv("question %s" % q, "has no claim at all. If nothing was found, record a GAP so the absence is visible")
    counts = {s: sum(1 for c in cl.values() if c["status"] == s) for s in STATUS}
    return errors, advisories, counts, len(src), len(cl)


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("ledger_check: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v.strip()
        elif a.startswith("--"):
            print("ledger_check: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__)
        return 2
    today = dt.date.today()
    if "--today" in opts:
        today = parse_date(opts["--today"])
        if today is None:
            print("ledger_check: --today needs a real date written YYYY-MM-DD", file=sys.stderr)
            return 2
    fd = opts.get("--fresh-days", "365")
    if not fd.isdigit() or int(fd) < 1:
        print("ledger_check: --fresh-days needs a positive whole number", file=sys.stderr)
        return 2
    questions = [q.strip() for q in opts.get("--questions", "").split(",") if q.strip()]
    sources, e = read_csv(args[0], SRC_COLS)
    if e:
        print("ledger_check: " + e, file=sys.stderr)
        return 2
    claims, e = read_csv(args[1], CLAIM_COLS)
    if e:
        print("ledger_check: " + e, file=sys.stderr)
        return 2
    if not claims:
        print("ledger_check: %s has no claims, so there is nothing to check" % args[1], file=sys.stderr)
        return 2
    errors, advisories, counts, ns, nc = check(sources, claims, today, int(fd), questions)
    if "--json" in flags:
        text = json.dumps({"sources": ns, "claims": nc, "by_status": counts, "errors": errors, "advisories": advisories}, indent=1, ensure_ascii=True)
    else:
        L = ["ledger_check: %d source(s), %d claim(s): %s" % (ns, nc, ", ".join("%d %s" % (counts[s], s) for s in STATUS if counts[s]))]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("RESULT: %s. %d error(s), %d advisory note(s). This checks the ledger's bookkeeping, not whether the sources are right."
                 % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
