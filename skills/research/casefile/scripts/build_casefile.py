#!/usr/bin/env python3
"""Build a casefile (one HTML file) from a research ledger. Standard library only.

Usage:
  python build_casefile.py SOURCES.csv CLAIMS.csv --out FILE.html [--title "Title"]
                           [--extra EXTRA.json] [--engine ENGINE.html]
                           [--today YYYY-MM-DD] [--fresh-days 365] [--json]
  python build_casefile.py SOURCES.csv CLAIMS.csv --check-only [--today YYYY-MM-DD] [--json]

Input is the two-file ledger that deep-research-orchestrator's ledger_check.py reads:

SOURCES.csv  source_id, title, publisher, address, tier, published, accessed, read_level, family, notes
             tier: primary | peer_reviewed | secondary | aggregator | unverified
             read_level: full | section | snippet | relayed
CLAIMS.csv   claim_id, question_id, statement, status, source_ids, locator, load_bearing, confidence,
             conflicts_with, conflict_class, resolution
             status: FACT | REPORTED | ASSESSMENT | MODEL_OUTPUT | GAP
             source_ids and conflicts_with are ids separated by ;   load_bearing: yes | no
EXTRA.json   optional: {"questions": [{"id": "Q1", "text": "..."}],
                        "assessments": [{"id": "A1", "question_id": "Q1", "judgement": "...",
                          "likelihood": "likely", "confidence": "moderate", "confidence_reason": "...",
                          "claim_ids": ["C1", "C2"], "written": "2026-10-09"}]}
             likelihood is one of: almost no chance, very unlikely, unlikely, roughly even chance,
             likely, very likely, almost certain, no basis.

What it does: checks the ledger, then writes a copy of the engine page (assets/casefile.html
beside this scripts folder unless --engine is given) with the ledger placed in its data block.
The inputs and the engine are never modified. The same inputs and the same --today give the
same bytes.

What it enforces (ERROR, exit 1, nothing written). These are the rules of ledger_check.py,
implemented here independently and in the same words, so the two tools can be compared:
  - ids are unique; every reference points at something that exists; conflicts are recorded on both sides
  - a FACT has a source, a locator, and at least one source that was opened (read_level full or
    section), has an address, and is at primary, peer_reviewed or secondary tier
  - MODEL_OUTPUT is never load-bearing; an ASSESSMENT states its confidence
  - dates are real calendar dates written YYYY-MM-DD and not in the future; fixed vocabularies are respected
and, for EXTRA.json: an assessment has a judgement, a likelihood word, a confidence, a real
written date, and rests on at least one claim that exists.
What it reports for a person to decide (ADVISORY, exit 0): the same notes ledger_check.py gives,
such as a load-bearing claim that is only REPORTED, an open conflict, a source with no address.

It cannot tell whether a source is right, whether a locator says what the claim says, or whether
the research was thorough. It checks bookkeeping and builds the page.

Exit codes: 0 built (or, with --check-only, no errors). 1 the ledger has errors. 2 bad arguments
or unreadable input.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"
TIERS = ("primary", "peer_reviewed", "secondary", "aggregator", "unverified")
FACT_TIERS = ("primary", "peer_reviewed", "secondary")
READ_LEVELS = ("full", "section", "snippet", "relayed")
OPENED = ("full", "section")
STATUSES = ("FACT", "REPORTED", "ASSESSMENT", "MODEL_OUTPUT", "GAP")
CONFIDENCE = ("high", "moderate", "low")
CONFLICT_CLASSES = ("scope_mismatch", "time_supersession", "method_difference", "direct_conflict", "insufficient_evidence")
OPEN_CLASSES = ("direct_conflict", "insufficient_evidence")
LIKELIHOOD = ("almost no chance", "very unlikely", "unlikely", "roughly even chance", "likely", "very likely", "almost certain", "no basis")
SOURCE_COLUMNS = ("source_id", "title", "publisher", "address", "tier", "published", "accessed", "read_level", "family", "notes")
CLAIM_COLUMNS = ("claim_id", "question_id", "statement", "status", "source_ids", "locator", "load_bearing", "confidence",
                 "conflicts_with", "conflict_class", "resolution")
DATE_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}")
FLAGS = {"--json", "--check-only"}
VALUES = {"--out", "--title", "--extra", "--engine", "--today", "--fresh-days"}
DATA_BEGIN = "<!-- casefile-data: begin -->"
DATA_END = "<!-- casefile-data: end -->"


def real_date(text):
    """A date written YYYY-MM-DD that exists in the calendar, or None."""
    if not isinstance(text, str) or not DATE_SHAPE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def split_ids(cell):
    return [part.strip() for part in cell.split(";") if part.strip()]


def load_table(path, columns):
    """Read one CSV file. Returns (rows, None) or (None, message). Each row is a dict of stripped
    strings plus "_line", numbered the way ledger_check.py numbers them."""
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
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        header = [(h or "").strip() for h in (reader.fieldnames or [])]
        absent = [c for c in columns if c not in header]
        if absent:
            return None, "%s is missing column(s): %s" % (path, ", ".join(absent))
        number = 1
        for record in reader:
            number += 1
            if None in record:
                return None, "%s line %d has more cells than the header" % (path, number)
            row = {(k or "").strip(): (v or "").strip() for k, v in record.items()}
            if any(row.values()):
                row["_line"] = number
                rows.append(row)
    except csv.Error as e:
        return None, "%s could not be parsed as CSV (%s)" % (path, e)
    return rows, None


class Findings:
    def __init__(self):
        self.errors, self.advisories = [], []

    def error(self, where, message):
        self.errors.append("%s: %s" % (where, message))

    def advise(self, where, message):
        self.advisories.append("%s: %s" % (where, message))


def index_sources(rows, today, out):
    """Check each source row on its own and return the usable ones by id, in file order."""
    by_id = {}
    for row in rows:
        sid = row["source_id"]
        where = "source %s (line %d)" % (sid or "?", row["_line"])
        if not sid:
            out.error(where, "has no source_id")
            continue
        if sid in by_id:
            out.error(where, "duplicate source_id")
            continue
        by_id[sid] = row
        if row["tier"] not in TIERS:
            out.error(where, "tier %r is not one of %s" % (row["tier"], ", ".join(TIERS)))
        if row["read_level"] not in READ_LEVELS:
            out.error(where, "read_level %r is not one of %s" % (row["read_level"], ", ".join(READ_LEVELS)))
        for column in ("published", "accessed"):
            value = row[column]
            if not value:
                if column == "accessed":
                    out.error(where, "accessed date is missing")
                continue
            when = real_date(value)
            if when is None:
                out.error(where, "%s %r is not a real date written YYYY-MM-DD" % (column, value))
            elif when > today:
                out.error(where, "%s %s is in the future" % (column, value))
        published, accessed = real_date(row["published"]), real_date(row["accessed"])
        if published and accessed and published > accessed:
            out.error(where, "published after it was accessed")
    return by_id


def index_claims(rows, out):
    by_id = {}
    for row in rows:
        cid = row["claim_id"]
        where = "claim %s (line %d)" % (cid or "?", row["_line"])
        if not cid:
            out.error(where, "has no claim_id")
        elif cid in by_id:
            out.error(where, "duplicate claim_id")
        else:
            by_id[cid] = row
    return by_id


def fact_shortfall(cited):
    """Why none of the cited sources can carry a FACT, as the list of reasons."""
    reasons = []
    if not any(s["read_level"] in OPENED for s in cited):
        reasons.append("no source was opened (only snippet or relayed)")
    if not any(s["tier"] in FACT_TIERS for s in cited):
        reasons.append("every source is aggregator or unverified tier")
    if not any(s["address"] for s in cited):
        reasons.append("no source has an address")
    return reasons or ["no single source is opened, addressed and at secondary tier or better"]


def check_claim(cid, row, sources, claims, out):
    """Check one claim. Returns the set of source ids it cites that exist."""
    where = "claim %s" % cid
    status, bearing = row["status"], row["load_bearing"].lower()
    if status not in STATUSES:
        out.error(where, "status %r is not one of %s" % (status, ", ".join(STATUSES)))
        return set()
    if bearing not in ("yes", "no"):
        out.error(where, "load_bearing must be yes or no, got %r" % row["load_bearing"])
    if not row["statement"]:
        out.error(where, "has no statement")
    cited_ids = split_ids(row["source_ids"])
    missing = [s for s in cited_ids if s not in sources]
    if missing:
        out.error(where, "cites unknown source(s) %s" % ", ".join(missing))
    cited = [sources[s] for s in cited_ids if s in sources]
    if row["confidence"] and row["confidence"] not in CONFIDENCE:
        out.error(where, "confidence %r is not one of %s" % (row["confidence"], ", ".join(CONFIDENCE)))

    if status == "FACT":
        if not cited_ids:
            out.error(where, "is a FACT with no source")
        if not row["locator"]:
            out.error(where, "is a FACT with no locator. Record where in the source it is")
        carrying = [s for s in cited if s["read_level"] in OPENED and s["tier"] in FACT_TIERS and s["address"]]
        if cited and not carrying:
            out.error(where, "cannot be a FACT: %s. Use REPORTED, or open a better source" % "; ".join(fact_shortfall(cited)))
        if bearing == "yes" and carrying:
            families = {s["family"] or s["source_id"] for s in carrying}
            if len(families) == 1 and not any(s["tier"] == "primary" for s in carrying):
                out.advise(where, "load-bearing FACT rests on one independent source family, none of it primary")
    elif status == "REPORTED":
        if not cited_ids:
            out.error(where, "is REPORTED with no source. If nothing was found it is a GAP")
        if bearing == "yes":
            out.advise(where, "the answer depends on a claim that is only REPORTED; say so where it is used")
    elif status == "MODEL_OUTPUT":
        if bearing == "yes":
            out.error(where, "MODEL_OUTPUT cannot be load-bearing. Open what it cites and record that as a new claim")
    elif status == "ASSESSMENT":
        if not row["confidence"]:
            out.error(where, "is an ASSESSMENT with no confidence")
    elif status == "GAP":
        if cited_ids:
            out.advise(where, "is a GAP but cites sources; if they say something, record that as its own claim")

    partners = split_ids(row["conflicts_with"])
    if not partners:
        if row["conflict_class"]:
            out.error(where, "conflict_class is set but conflicts_with is empty")
        return {s["source_id"] for s in cited}
    if row["conflict_class"] not in CONFLICT_CLASSES:
        out.error(where, "conflicts_with is set, so conflict_class must be one of %s" % ", ".join(CONFLICT_CLASSES))
    for other in partners:
        if other == cid:
            out.error(where, "is recorded as conflicting with itself")
        elif other not in claims:
            out.error(where, "conflicts_with unknown claim %s" % other)
        elif cid not in split_ids(claims[other]["conflicts_with"]):
            out.error(where, "conflict with %s is recorded on one side only" % other)
    if not row["resolution"] and row["conflict_class"] in OPEN_CLASSES:
        first_side = all(other not in claims or cid < other for other in partners)
        if first_side or bearing == "yes":
            out.advise(where, "open %s with %s: show both in the write-up and name what would settle it"
                       % (row["conflict_class"].replace("_", " "), ", ".join(partners)))
    return {s["source_id"] for s in cited}


def check_ledger(source_rows, claim_rows, today, fresh_days=365, questions=()):
    """Apply every rule. Returns (errors, advisories, counts_by_status, sources_by_id, claims_by_id)."""
    out = Findings()
    sources = index_sources(source_rows, today, out)
    claims = index_claims(claim_rows, out)
    used = set()
    for cid, row in claims.items():
        used |= check_claim(cid, row, sources, claims, out)
    bearing_sources = set()
    for row in claims.values():
        if row["load_bearing"].lower() == "yes":
            bearing_sources.update(split_ids(row["source_ids"]))
    for sid, row in sources.items():
        where = "source %s" % sid
        if sid not in used:
            out.advise(where, "is never cited. Remove it or record what it contributed")
            continue
        if not row["address"]:
            out.advise(where, "has no address, so it cannot be found again")
        if not row["published"]:
            out.advise(where, "has no publication date")
        dated = real_date(row["published"]) or real_date(row["accessed"])
        if dated and sid in bearing_sources and (today - dated).days > fresh_days:
            out.advise(where, "is %d days old and supports a load-bearing claim; recheck if the subject changes over time" % (today - dated).days)
    answered = {row["question_id"] for row in claims.values() if row["question_id"]}
    for q in questions:
        if q not in answered:
            out.advise("question %s" % q, "has no claim at all. If nothing was found, record a GAP so the absence is visible")
    counts = {s: sum(1 for row in claims.values() if row["status"] == s) for s in STATUSES}
    return out.errors, out.advisories, counts, sources, claims


def read_extra(path, claims, question_ids, today=None):
    """Read and check EXTRA.json. Returns (questions, assessments, errors) or raises ValueError for an unreadable file."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise ValueError("cannot read %s: %s" % (path, e.strerror or e))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("%s is not valid UTF-8" % path)
    if "\x00" in text:
        raise ValueError("%s contains NUL bytes" % path)

    def no_constants(name):
        raise ValueError("%s contains %s, which is not a JSON number" % (path, name))
    try:
        doc = json.loads(text, parse_constant=no_constants)
    except ValueError as e:
        raise ValueError("%s is not valid JSON (%s)" % (path, str(e)[:80]))
    if not isinstance(doc, dict):
        raise ValueError("%s must hold one JSON object with questions and assessments" % path)
    unknown = sorted(set(doc) - {"questions", "assessments"})
    if unknown:
        raise ValueError("%s has unknown field(s): %s" % (path, ", ".join(unknown)))
    errors, questions, assessments = [], [], []
    seen_q = set()
    for i, q in enumerate(doc.get("questions", []) if isinstance(doc.get("questions", []), list) else [None]):
        if not isinstance(q, dict) or not isinstance(q.get("id"), str) or not isinstance(q.get("text", ""), str):
            errors.append("question %d: must be an object with a text id and text" % (i + 1))
            continue
        qid = q["id"].strip()
        if not qid:
            errors.append("question ?: has no id")
        elif qid in seen_q:
            errors.append("question %s: duplicate id" % qid)
        else:
            seen_q.add(qid)
            questions.append({"id": qid, "text": q.get("text", "").strip()})
    known_q = seen_q | set(question_ids)
    seen_a = set()
    for i, a in enumerate(doc.get("assessments", []) if isinstance(doc.get("assessments", []), list) else [None]):
        if not isinstance(a, dict):
            errors.append("assessment %d: must be an object" % (i + 1))
            continue
        text_fields = ("id", "question_id", "judgement", "likelihood", "confidence", "confidence_reason", "written")
        if any(not isinstance(a.get(k, ""), str) for k in text_fields) or not isinstance(a.get("claim_ids", []), list) \
                or any(not isinstance(c, str) for c in a.get("claim_ids", [])):
            errors.append("assessment %d: every field must be text, and claim_ids a list of text ids" % (i + 1))
            continue
        aid = a.get("id", "").strip()
        where = "assessment %s" % (aid or "?")
        if not aid:
            errors.append("%s: has no id" % where)
            continue
        if aid in seen_a:
            errors.append("%s: duplicate id" % where)
            continue
        seen_a.add(aid)
        item = {k: a.get(k, "").strip() for k in text_fields}
        item["claim_ids"] = [c.strip() for c in a.get("claim_ids", []) if c.strip()]
        if item["question_id"] and item["question_id"] not in known_q:
            errors.append("%s: question %s is not in the question list" % (where, item["question_id"]))
        if not item["judgement"]:
            errors.append("%s: has no judgement" % where)
        if item["likelihood"] not in LIKELIHOOD:
            errors.append("%s: likelihood %r is not one of %s" % (where, item["likelihood"], ", ".join(LIKELIHOOD)))
        if not item["confidence"]:
            errors.append("%s: is an assessment with no confidence" % where)
        elif item["confidence"] not in CONFIDENCE:
            errors.append("%s: confidence %r is not one of %s" % (where, item["confidence"], ", ".join(CONFIDENCE)))
        if not item["claim_ids"]:
            errors.append("%s: rests on no claims. An assessment cannot rest on nothing" % where)
        else:
            absent = [c for c in item["claim_ids"] if c not in claims]
            if absent:
                errors.append("%s: rests on unknown claim(s) %s" % (where, ", ".join(absent)))
        if real_date(item["written"]) is None:
            errors.append("%s: written %r is not a real date written YYYY-MM-DD" % (where, item["written"]))
        elif real_date(item["written"]) > (today or dt.date.today()):
            errors.append("%s: written date is in the future" % where)
        assessments.append(item)
    return questions, assessments, errors


def casefile_data(title, sources, claims, questions, assessments, today, note):
    """The data the page holds: the ledger in the page's own shape."""
    listed = {q["id"] for q in questions}
    for row in claims.values():
        if row["question_id"] and row["question_id"] not in listed:
            listed.add(row["question_id"])
            questions.append({"id": row["question_id"], "text": ""})
    return {
        "title": title,
        "questions": questions,
        "sources": [{"id": s["source_id"], "title": s["title"], "publisher": s["publisher"], "address": s["address"], "tier": s["tier"],
                     "published": s["published"], "accessed": s["accessed"], "read_level": s["read_level"], "family": s["family"],
                     "notes": s["notes"]} for s in sources.values()],
        "claims": [{"id": c["claim_id"], "question_id": c["question_id"], "statement": c["statement"], "status": c["status"],
                    "source_ids": split_ids(c["source_ids"]), "locator": c["locator"], "load_bearing": c["load_bearing"].lower() == "yes",
                    "confidence": c["confidence"], "conflicts_with": split_ids(c["conflicts_with"]), "conflict_class": c["conflict_class"],
                    "resolution": c["resolution"]} for c in claims.values()],
        "assessments": assessments,
        "log": [{"at": today.isoformat() + "T00:00:00.000Z", "text": note}],
    }


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48] or "casefile"


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("build_casefile: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v.strip()
        elif a.startswith("--"):
            print("build_casefile: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__)
        return 2
    check_only = "--check-only" in flags
    if not check_only and "--out" not in opts:
        print("build_casefile: --out FILE.html is needed (or use --check-only)", file=sys.stderr)
        return 2
    today = dt.date.today()
    if "--today" in opts:
        today = real_date(opts["--today"])
        if today is None:
            print("build_casefile: --today needs a real date written YYYY-MM-DD", file=sys.stderr)
            return 2
    fresh = opts.get("--fresh-days", "365")
    if not (fresh.isascii() and fresh.isdigit()) or int(fresh) < 1:
        print("build_casefile: --fresh-days needs a positive whole number", file=sys.stderr)
        return 2
    source_rows, problem = load_table(args[0], SOURCE_COLUMNS)
    if problem:
        print("build_casefile: " + problem, file=sys.stderr)
        return 2
    claim_rows, problem = load_table(args[1], CLAIM_COLUMNS)
    if problem:
        print("build_casefile: " + problem, file=sys.stderr)
        return 2
    if not claim_rows:
        print("build_casefile: %s has no claims, so there is nothing to build from" % args[1], file=sys.stderr)
        return 2

    errors, advisories, counts, sources, claims = check_ledger(source_rows, claim_rows, today, int(fresh))
    questions, assessments, extra_errors = [], [], []
    if "--extra" in opts:
        try:
            questions, assessments, extra_errors = read_extra(opts["--extra"], claims, {c["question_id"] for c in claims.values() if c["question_id"]}, today)
        except ValueError as e:
            print("build_casefile: %s" % e, file=sys.stderr)
            return 2
    all_errors = errors + extra_errors

    written = None
    if not all_errors and not check_only:
        engine_path = Path(opts["--engine"]) if "--engine" in opts else Path(__file__).resolve().parent.parent / "assets" / "casefile.html"
        out_path = Path(opts["--out"])
        for given in [Path(args[0]), Path(args[1]), engine_path] + ([Path(opts["--extra"])] if "--extra" in opts else []):
            if given.exists() and out_path.resolve() == given.resolve():
                print("build_casefile: --out must not name an input file (%s)" % given, file=sys.stderr)
                return 2
        try:
            engine = engine_path.read_bytes().decode("utf-8-sig")
        except (OSError, UnicodeDecodeError) as e:
            print("build_casefile: cannot read the engine page %s (%s)" % (engine_path, str(e)[:80]), file=sys.stderr)
            return 2
        if engine.count(DATA_BEGIN) != 1 or engine.count(DATA_END) != 1 or engine.index(DATA_BEGIN) > engine.index(DATA_END):
            print("build_casefile: %s is not a casefile engine: its data block markers are missing or repeated" % engine_path, file=sys.stderr)
            return 2
        title = opts.get("--title") or Path(args[0]).stem.replace("-sources", "").replace("_", " ").replace("-", " ").strip() or "Casefile"
        digest = hashlib.sha256()
        for part in (Path(args[0]).read_bytes(), Path(args[1]).read_bytes(), json.dumps([questions, assessments], sort_keys=True).encode("utf-8")):
            digest.update(hashlib.sha256(part).digest())
        note = "Built from %s and %s: %d source(s), %d claim(s), %d assessment(s)." % (Path(args[0]).name, Path(args[1]).name, len(sources), len(claims), len(assessments))
        block = {
            "content_id": "casefile:%s@%s" % (slug(title), digest.hexdigest()[:12]),
            "built": {"tool": "build_casefile.py " + VERSION, "on": today.isoformat(), "sources_file": Path(args[0]).name, "claims_file": Path(args[1]).name},
            "data": casefile_data(title, sources, claims, questions, assessments, today, note),
        }
        # Inside a script element the text must never contain "<", or a closing tag in a statement
        # would end the block early. JSON allows the same character as an escape.
        payload = json.dumps(block, ensure_ascii=True, separators=(",", ":")).replace("<", "\\" + "u003c")
        start = engine.index(DATA_BEGIN) + len(DATA_BEGIN)
        page = engine[:start] + '\n<script type="application/json" id="casefile-data">' + payload + "</script>\n" + engine[engine.index(DATA_END):]
        page = re.sub(r"<title>[^<]*</title>", lambda m: "<title>" + title.replace("&", "&amp;").replace("<", "&lt;") + ": casefile</title>", page, count=1)
        try:
            out_path.write_bytes(page.encode("utf-8"))
        except OSError as e:
            print("build_casefile: cannot write %s: %s" % (out_path, e.strerror or e), file=sys.stderr)
            return 2
        written = {"path": str(out_path), "bytes": len(page.encode("utf-8")), "content_id": block["content_id"], "title": title}

    if "--json" in flags:
        text = json.dumps({"sources": len(sources), "claims": len(claims), "by_status": counts, "errors": all_errors, "advisories": advisories,
                           "questions": len(questions), "assessments": len(assessments), "written": written}, indent=1, ensure_ascii=True)
    else:
        L = ["build_casefile: %d source(s), %d claim(s): %s" % (len(sources), len(claims), ", ".join("%d %s" % (counts[s], s) for s in STATUSES if counts[s]))]
        L += ["  ERROR     " + m for m in all_errors]
        L += ["  ADVISORY  " + m for m in advisories]
        if written:
            L.append("  WROTE     %s (%d bytes), content id %s" % (written["path"], written["bytes"], written["content_id"]))
        if all_errors:
            L.append("RESULT: FAIL. %d error(s), %d advisory note(s). Nothing was written. Fix the ledger and build again." % (len(all_errors), len(advisories)))
        else:
            L.append("RESULT: PASS. 0 error(s), %d advisory note(s). This checks the ledger's bookkeeping, not whether the sources are right." % len(advisories))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
