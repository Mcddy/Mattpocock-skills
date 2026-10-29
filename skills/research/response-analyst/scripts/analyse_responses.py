#!/usr/bin/env python3
"""Analyse survey, questionnaire and quiz responses: counts over named denominators, with intervals.
Standard library only.

Usage:
  python analyse_responses.py RESPONSES.csv [--instrument INSTRUMENT.json] [options]

Options:
  --instrument FILE      describes each question (below). Without it, types are inferred and listed.
  --level N              confidence level for intervals, above 50 and below 100 (default 95)
  --combine Q=A|B        one count for several options together ("Agree|Strongly agree"), with its
                         interval; a respondent who chose any of them counts once. May be repeated.
  --cross Q1 Q2          cross-tab of two questions; may be given more than once
  --compare Q=OPTION --by GROUPQ [--pair A B]
                         proportion choosing OPTION in each group of GROUPQ, and for two groups the
                         difference with an interval. --pair picks the two groups when there are more.
                         OPTION may join several options with "|" ("Agree|Strongly agree"): a
                         respondent counts once if they chose any of them.
  --coding-sheet OUT.csv write every free-text answer to a sheet (respondent, question, text, screen,
                         themes) ready for theme codes to be added. Refuses to overwrite a file
                         unless --overwrite is given. An answer that begins with =, +, - or @ gets
                         an apostrophe in front in the sheet, so a spreadsheet does not run it as a
                         formula; --themes reads it back without the apostrophe.
  --themes CODED.csv     read a coded sheet back: theme counts by respondent, with denominators
  --codebook FILE.csv    columns code, definition. Codes not in it are errors.
  --point-biserial       add the point-biserial correlation to the quiz item analysis
  --group-fraction F     size of the upper and lower score groups, 0.1 to 0.5 (default 0.27)
  --scale-means          also print a mean for scale questions, labelled as treating the scale as numbers
  --allow-unknown        count answers that are not instrument options as "other" (default: error)
  --skip-questions       leave the per-question block out of the text output, for a second run that
                         only adds a cross-tab, a comparison or themes
  --keep-ids             print the respondent column as it is (default: replace with R01, R02, ...)
  --id-map OUT.csv       write the original respondent value beside each replacement id
  --json                 machine-readable output

RESPONSES.csv: one row per respondent. A column called respondent; one column per question id;
optional columns called <id>__note holding a free-text note on that question. Cells are trimmed. An
empty cell is no answer. Several choices in one cell are separated by ";".

The file the elicitor skill's collect_responses.py writes is read as it is, with no editing. It is
recognised by its first four columns (source, instrument, version, finished) and then:
  source              is the respondent column
  instrument, version are reported and not analysed; finished is not analysed
  <id>.note           is the note on question <id>
  tally:<id> columns  are not analysed: a tally is the questionnaire's own count of answers
  (skipped)           the respondent was shown the question and gave no answer; so is an empty cell
  (not shown)         the questionnaire hid the question from this respondent; not non-response
  several choices     are separated by " | " (the collector's default, --multi pipe)
  a leading '         before =, +, - or @ is the collector's spreadsheet guard and is removed

INSTRUMENT.json:
  {"title": "...",
   "collection": {"reached": "how respondents were reached", "invited": 40, "missing": "who is not here"},
   "questions": [
     {"id": "q1", "text": "...", "type": "single", "options": ["Yes", "No"], "section": "..."},
     {"id": "q2", "type": "scale", "options": ["Disagree", "Neutral", "Agree"]},     in order, low to high
     {"id": "q3", "type": "multi", "options": ["a", "b", "c"]},
     {"id": "q4", "type": "number"},
     {"id": "q5", "type": "text"},
     {"id": "q6", "type": "single", "options": ["A", "B", "C"], "correct": "B"},     a quiz item
     {"id": "q7", "type": "single", "options": ["x", "y"],
      "shown_if": {"question": "q1", "in": ["Yes"]}}]}                               routing

Definitions used (see also the reference file that travels with the skill):
  respondents   rows in the file.
  shown         respondents the routing says saw the question (everyone, when it has no shown_if).
  not shown     respondents routed past it. They are not non-response.
  skipped       shown, and left it empty. Skipped respondents stay in the "shown" denominator.
  answered      shown, and gave a recognised answer.
  Every proportion is printed as a count over a named denominator: of those who answered, of those
  shown, of all respondents.
  Interval for one proportion: Wilson score interval without continuity correction (Wilson 1927):
    (p + z^2/2n +/- z * sqrt(p(1-p)/n + z^2/4n^2)) / (1 + z^2/n).
  Interval for a difference of two independent proportions: Newcombe's hybrid score interval
    (Newcombe 1998, method 10), built from the two Wilson intervals (l1, u1) and (l2, u2):
    lower = d - sqrt((p1-l1)^2 + (u2-p2)^2), upper = d + sqrt((u1-p1)^2 + (p2-l2)^2), d = p1 - p2.
  Quiz items: difficulty = proportion of those shown the item who answered it correctly (an omitted
    item counts as not correct). Discrimination D = proportion correct in the upper score group minus
    proportion correct in the lower score group (Kelley 1939 recommended groups of 27 per cent). The
    upper group is everyone at or above the score of the k-th highest scorer, the lower group
    everyone at or below the score of the k-th lowest, k = fraction * respondents rounded to the
    nearest whole number and at least 1, so tied scores are never split and group sizes are printed.
    Point-biserial = (M1 - M0) / s * sqrt(p * q): M1 and M0 the mean total scores of those right and
    wrong on the item, s the standard deviation of scores dividing by n, p the proportion right.
    It is printed against the total score and against the rest score (total minus this item).

What it enforces (ERROR, exit 1, no analysis is printed):
  - rows with the wrong number of cells, empty or repeated respondent values, no respondents
  - with an instrument: a question with no column, an answer that is not one of its options (unless
    --allow-unknown), a non-numeric answer to a number question, a correct answer that is not an
    option, routing that points at a later or unknown question, unknown keys or types, a title
    or collection text that still begins with the template marker REPLACE
  - a coded sheet that names a respondent, question or code that does not exist, repeats a passage,
    or uses two codes that differ only in capital letters
What it reports for a person to decide (ADVISORY):
  - columns it inferred or ignored; answers given to a question the routing says was not shown
  - respondents who answered nothing; how respondents were reached, when that was not stated
  - quiz item flags, which are candidates to read and not verdicts: nearly everyone right (nine in
    ten or more) or wrong (one in five or fewer), an option nobody chose, a wrong option chosen by
    a larger share of the upper group than the lower (and by at least two of the upper group: one
    person's slip is in the option counts but is not flagged), an item whose most-chosen
    upper-group answer is not the keyed one, negative discrimination
  - free-text passages that contain an email address, a phone number or a web address
  - passages with no code, and passages missing from the coded sheet

It cannot tell who did not respond or why, whether the respondents resemble anyone else, whether a
theme code was applied consistently, whether a quotation identifies someone by name or role, or
whether a flagged quiz item is actually faulty. A tally from an informal questionnaire is a count.
It is not a score on a validated scale and never a diagnosis.

Exit codes: 0 ran and nothing failed. 1 a check failed. 2 bad arguments or unreadable input
(including --cross, --combine or --compare naming a question, option or group that is not in the
data, a file that is not UTF-8 text, and an output file that already exists).
"""
import csv
import io
import json
import math
import re
import statistics
import sys
from pathlib import Path

TYPES = ("single", "multi", "scale", "number", "text")
Q_KEYS = {"id", "text", "type", "options", "correct", "section", "shown_if", "separator"}
TOP_KEYS = {"title", "collection", "questions", "notes"}
COLLECTION_KEYS = {"reached", "invited", "missing"}
NOTE_SUFFIX = "__note"
SEP = ";"
COLLECTOR_HEAD = ("source", "instrument", "version", "finished")
COLLECTOR_NOTE = ".note"
COLLECTOR_SEP = " | "
MARK_SKIPPED, MARK_NOT_SHOWN = "(skipped)", "(not shown)"
GUARDED = ("=", "+", "-", "@")
OTHER = "other (not an instrument option)"
EASY, HARD = 0.9, 0.2   # reading thresholds for "nearly everyone right" and "nearly everyone wrong"
FLAGS = {"--json", "--point-biserial", "--scale-means", "--allow-unknown", "--keep-ids", "--overwrite", "--skip-questions"}
VALUES = {"--instrument": 1, "--level": 1, "--cross": 2, "--combine": 1, "--compare": 1, "--by": 1, "--pair": 2, "--coding-sheet": 1,
          "--themes": 1, "--codebook": 1, "--group-fraction": 1, "--id-map": 1}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![0-9])(?:\+?[0-9][0-9 ()-]{7,}[0-9])(?![0-9])")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s]+", re.I)


class Refusal(Exception):
    """Unreadable input or bad arguments: exit 2."""


# ---------------------------------------------------------------- statistics

def z_for(level):
    return statistics.NormalDist().inv_cdf(0.5 + level / 200.0)


def wilson(x, n, z):
    """Wilson score interval for x successes in n trials. Returns (low, high), or None when n is 0."""
    if n <= 0:
        return None
    p = x / n
    z2 = z * z
    centre = (p + z2 / (2.0 * n)) / (1.0 + z2 / n)
    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / (1.0 + z2 / n)
    low = 0.0 if x == 0 else max(0.0, centre - half)
    high = 1.0 if x == n else min(1.0, centre + half)
    return low, high


def newcombe(x1, n1, x2, n2, z):
    """Newcombe hybrid score interval for p1 - p2. Returns (difference, low, high), or None when a group is empty."""
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1, z)
    l2, u2 = wilson(x2, n2, z)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def point_biserial(item, scores):
    """(M1 - M0) / s * sqrt(p * q) with s the standard deviation dividing by n. None when undefined."""
    n = len(item)
    n1 = sum(item)
    if n == 0 or n1 == 0 or n1 == n:
        return None
    mean = sum(scores) / n
    s = math.sqrt(sum((v - mean) ** 2 for v in scores) / n)
    if s == 0:
        return None
    m1 = sum(v for v, i in zip(scores, item) if i) / n1
    m0 = sum(v for v, i in zip(scores, item) if not i) / (n - n1)
    p = n1 / n
    return (m1 - m0) / s * math.sqrt(p * (1.0 - p))


def score_groups(scores, fraction):
    """Upper and lower groups by total score, ties kept together. Returns a dict; formed is False when they overlap."""
    n = len(scores)
    k = max(1, min(int(fraction * n + 0.5), n // 2))
    ordered = sorted(scores)
    lower_cut, upper_cut = ordered[min(k, n) - 1], ordered[max(n - k, 0)]
    upper = [i for i, s in enumerate(scores) if s >= upper_cut]
    lower = [i for i, s in enumerate(scores) if s <= lower_cut]
    formed = upper_cut > lower_cut
    return {"fraction": fraction, "target_size": k, "upper_cut": upper_cut, "lower_cut": lower_cut, "upper": upper, "lower": lower, "formed": formed}


def pct(count, n):
    return int(100.0 * count / n + 0.5)


def prop(count, n, z):
    """A proportion as a JSON-safe object that always carries its count and denominator."""
    if n <= 0:
        return {"count": count, "n": n, "proportion": None, "percent": None, "interval": None, "interval_percent": None}
    lo, hi = wilson(count, n, z)
    return {"count": count, "n": n, "proportion": round(count / n, 4), "percent": pct(count, n),
            "interval": [round(lo, 4), round(hi, 4)], "interval_percent": [int(100 * lo + 0.5), int(100 * hi + 0.5)]}


def prop_text(p, of_what, interval=True):
    if p["n"] <= 0:
        return "%d of 0 %s (no percentage: nobody in the denominator)" % (p["count"], of_what)
    s = "%d of %d %s (%d%%" % (p["count"], p["n"], of_what, p["percent"])
    if interval:
        s += ", interval %d%% to %d%%" % tuple(p["interval_percent"])
    return s + ")"


# ---------------------------------------------------------------- reading files

def read_text(path, what):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise Refusal("cannot read %s %s: %s" % (what, path, e.strerror or e))
    if b"\x00" in raw:
        raise Refusal("%s %s contains NUL bytes; it is not a UTF-8 text file. Files saved as UTF-16 or as a spreadsheet look like this; export as UTF-8 CSV" % (what, path))
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise Refusal("%s %s is not valid UTF-8 (byte %d); save it as UTF-8 and run again" % (what, path, e.start))


def read_csv(path, what):
    """Return (header, rows, line numbers, ragged). Cells are trimmed. Ragged rows are reported, not padded."""
    text = read_text(path, what)
    reader = csv.reader(io.StringIO(text, newline=""))
    header, rows, lines, ragged = None, [], [], []
    try:
        for cells in reader:
            if header is None:
                header = [c.strip() for c in cells]
                continue
            if not cells or all(not c.strip() for c in cells):
                continue
            if len(cells) != len(header):
                ragged.append((reader.line_num, len(cells)))
                continue
            rows.append([c.strip() for c in cells])
            lines.append(reader.line_num)
    except csv.Error as e:
        raise Refusal("%s %s is not a readable CSV (line %d: %s)" % (what, path, reader.line_num, e))
    if header is None or not any(header):
        raise Refusal("%s %s is empty: it needs a header row" % (what, path))
    if any(not h for h in header):
        raise Refusal("%s %s has a column with no name in its header row" % (what, path))
    dup = sorted({h for h in header if header.count(h) > 1})
    if dup:
        raise Refusal("%s %s names a column twice: %s" % (what, path, ", ".join(dup)))
    return header, rows, lines, ragged


def read_json(path, what):
    def refuse(c):
        raise ValueError("%s is not a JSON number" % c)

    def no_duplicates(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise ValueError("the key %r appears twice in one object" % k)
            seen[k] = v
        return seen
    try:
        return json.loads(read_text(path, what), parse_constant=refuse, object_pairs_hook=no_duplicates)
    except ValueError as e:
        raise Refusal("%s %s is not valid JSON (%s)" % (what, path, str(e)[:70]))


def text_ok(v):
    return isinstance(v, str) and bool(v.strip())


def option_text(v):
    """An instrument option as the text a cell would hold. Whole numbers are allowed; nothing else is converted."""
    if isinstance(v, str) and v.strip():
        return v.strip()
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return None


def as_number(cell):
    try:
        v = float(cell)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def from_collector(path, header, rows, advisories):
    """Rewrite the elicitor collector's layout into this script's own. Returns (header, rows, marks,
    facts): marks maps (row index, column name) to "skipped" or "not_shown" for the cells that held
    one of the collector's two markers. Nothing is guessed: a column this cannot place is refused."""
    qcols = [h for h in header if h not in COLLECTOR_HEAD and not h.startswith("tally:")]
    ids = [h for h in qcols if not (h.endswith(COLLECTOR_NOTE) and h[:-len(COLLECTOR_NOTE)] in header)]
    keep, names, tallies = [], [], [h for h in header if h.startswith("tally:")]
    for i, h in enumerate(header):
        if h == "source":
            keep.append(i)
            names.append("respondent")
        elif h in COLLECTOR_HEAD or h.startswith("tally:"):
            continue
        elif h in ids:
            keep.append(i)
            names.append(h)
        else:
            keep.append(i)
            names.append(h[:-len(COLLECTOR_NOTE)] + NOTE_SUFFIX)
    clash = sorted({n for n in names if names.count(n) > 1})
    if clash or "respondent" in ids:
        raise Refusal("responses file %s is in the elicitor collector's layout but its columns cannot be renamed without a clash (%s)"
                      % (path, ", ".join(clash) or "a question is called respondent"))
    col = {h: i for i, h in enumerate(header)}
    seen = sorted({(r[col["instrument"]], r[col["version"]]) for r in rows})
    marks, out, unguarded = {}, [], 0
    for n, r in enumerate(rows):
        new = []
        for i, name in zip(keep, names):
            cell = r[i]
            if name != "respondent":
                if cell == MARK_SKIPPED:
                    marks[(n, name)] = "skipped"
                    cell = ""
                elif cell == MARK_NOT_SHOWN:
                    marks[(n, name)] = "not_shown"
                    cell = ""
                elif len(cell) > 1 and cell[0] == "'" and cell[1] in GUARDED:
                    cell = cell[1:]
                    unguarded += 1
            new.append(cell)
        out.append(new)
    facts = {"layout": "elicitor collector", "instruments": [{"id": a, "version": b} for a, b in seen], "note_columns": sum(1 for n in names if n.endswith(NOTE_SUFFIX)),
             "tally_columns_not_analysed": tallies, "marked_skipped": sum(1 for v in marks.values() if v == "skipped"),
             "marked_not_shown": sum(1 for v in marks.values() if v == "not_shown"), "spreadsheet_guards_removed": unguarded}
    advisories.append("the file is in the elicitor collector's layout (%s): source is read as the respondent column; %d cell(s) marked %s are counted as "
                      "skipped and %d marked %s as not shown; choices in one cell are split on %r"
                      % ("; ".join("instrument %r version %s" % x for x in seen) or "no rows", facts["marked_skipped"], MARK_SKIPPED,
                         facts["marked_not_shown"], MARK_NOT_SHOWN, COLLECTOR_SEP))
    if len(seen) > 1:
        advisories.append("the rows come from %d different instrument ids or versions. The collector refuses to merge those, so this file was put together "
                          "some other way: check that every row answers the same questions" % len(seen))
    if tallies:
        advisories.append("tally column(s) %s were not analysed. A tally is the questionnaire's own count of answers; it is not a score on a validated scale"
                          % ", ".join(tallies))
    if unguarded:
        advisories.append("%d cell(s) began with an apostrophe put there by the collector to stop a spreadsheet reading the text as a formula; it was removed" % unguarded)
    return names, out, marks, facts


# ---------------------------------------------------------------- instrument

def check_instrument(inst, header, errors, advisories, sep=SEP):
    """Validate the instrument against the header. Returns the list of question dicts in analysis order."""
    if not isinstance(inst, dict):
        errors.append("the instrument must be one JSON object")
        return []
    for k in sorted(set(inst) - TOP_KEYS):
        errors.append("instrument: unknown key %r (known: %s)" % (k, ", ".join(sorted(TOP_KEYS))))
    coll = inst.get("collection", {})
    for where, v in [("title", inst.get("title"))] + [("collection." + k, v) for k, v in (coll.items() if isinstance(coll, dict) else [])]:
        if isinstance(v, str) and v.strip().startswith("REPLACE"):
            errors.append("instrument: %s still holds the template text beginning REPLACE; write the real value or remove the key" % where)
    if not isinstance(coll, dict):
        errors.append("instrument: collection must be an object")
    else:
        for k in sorted(set(coll) - COLLECTION_KEYS):
            errors.append("instrument: collection has an unknown key %r" % k)
        inv = coll.get("invited")
        if inv is not None and (not isinstance(inv, int) or isinstance(inv, bool) or inv < 1):
            errors.append("instrument: collection.invited must be a whole number of people invited (got %r)" % (inv,))
    qs = inst.get("questions")
    if not isinstance(qs, list) or not qs:
        errors.append("instrument: questions must be a non-empty list")
        return []
    out, seen = [], {}
    for n, q in enumerate(qs, 1):
        where = "instrument question %d" % n
        if not isinstance(q, dict) or not text_ok(q.get("id")):
            errors.append(where + " needs an id")
            continue
        qid = q["id"].strip()
        where = "instrument question %r" % qid
        if qid in seen or qid == "respondent" or qid.endswith(NOTE_SUFFIX):
            errors.append(where + ": the id is repeated, or is 'respondent', or ends in %s" % NOTE_SUFFIX)
            continue
        for k in sorted(set(q) - Q_KEYS):
            errors.append("%s: unknown key %r" % (where, k))
        t = q.get("type")
        if t not in TYPES:
            errors.append("%s: type %r is not one of %s" % (where, t, ", ".join(TYPES)))
            continue
        item = {"id": qid, "text": q["text"].strip() if text_ok(q.get("text")) else "", "type": t, "options": [], "correct": None,
                "section": q["section"].strip() if text_ok(q.get("section")) else "", "shown_if": None, "inferred": False,
                "sep": q.get("separator", sep), "note_of": None}
        if not isinstance(item["sep"], str) or not item["sep"]:
            errors.append("%s: separator must be a non-empty string" % where)
            item["sep"] = sep
        if t in ("single", "multi", "scale"):
            raw = q.get("options")
            opts = [option_text(o) for o in raw] if isinstance(raw, list) else []
            if len(opts) < 2 or any(o is None for o in opts) or len(set(opts)) != len(opts):
                errors.append("%s: options must be a list of at least two different texts or whole numbers" % where)
                continue
            item["options"] = opts
        elif "options" in q:
            errors.append("%s: a %s question takes no options" % (where, t))
        if "correct" in q:
            c = option_text(q["correct"])
            if t != "single":
                errors.append("%s: only a single-choice question can have a correct answer" % where)
            elif c not in item["options"]:
                errors.append("%s: the correct answer %r is not one of its options (%s)" % (where, q["correct"], ", ".join(item["options"])))
            else:
                item["correct"] = c
        if "shown_if" in q:
            s = q["shown_if"]
            vals = [option_text(v) for v in s.get("in", [])] if isinstance(s, dict) and isinstance(s.get("in"), list) else []
            ctrl = s.get("question") if isinstance(s, dict) else None
            if not isinstance(s, dict) or not vals or any(v is None for v in vals) or set(s) - {"question", "in"}:
                errors.append("%s: shown_if must be {\"question\": id, \"in\": [answers that show this question]}" % where)
            elif ctrl not in seen:
                errors.append("%s: shown_if points at %r, which is not an earlier question in the instrument" % (where, ctrl))
            elif seen[ctrl]["type"] not in ("single", "multi", "scale"):
                errors.append("%s: shown_if points at %r, which is not a choice question" % (where, ctrl))
            else:
                bad = [v for v in vals if v not in seen[ctrl]["options"]]
                if bad:
                    errors.append("%s: shown_if lists %s, not an option of %r" % (where, ", ".join(repr(b) for b in bad), ctrl))
                else:
                    item["shown_if"] = (ctrl, vals)
        if qid not in header:
            near = [h for h in header if h.lower() == qid.lower()]
            errors.append("%s has no column in the responses file%s" % (where, (" (there is a column %r: ids must match exactly)" % near[0]) if near else ""))
            continue
        seen[qid] = item
        out.append(item)
    known = set(seen) | {"respondent"}
    notes = {}
    for h in header:
        if h in known:
            continue
        if h.endswith(NOTE_SUFFIX) and h[:-len(NOTE_SUFFIX)] in seen:
            parent = seen[h[:-len(NOTE_SUFFIX)]]
            notes[parent["id"]] = {"id": h, "text": "note on %s" % parent["id"], "type": "text", "options": [], "correct": None, "section": parent["section"],
                                   "shown_if": parent["shown_if"], "inferred": False, "sep": sep, "note_of": parent["id"]}
        else:
            advisories.append("column %r is in the responses file but not in the instrument; it was not analysed" % h)
    ordered = []
    for item in out:
        ordered.append(item)
        if item["id"] in notes:
            ordered.append(notes[item["id"]])
    return ordered


def infer_questions(header, rows, col, advisories, sep=SEP):
    """With no instrument: guess each column's type from its values, and say so."""
    out = []
    for h in header:
        if h == "respondent":
            continue
        vals = [r[col[h]] for r in rows if r[col[h]]]
        distinct = sorted(set(vals))
        item = {"id": h, "text": "", "type": "text", "options": [], "correct": None, "section": "", "shown_if": None, "inferred": True, "sep": sep, "note_of": None}
        nums = [as_number(v) for v in vals]
        parts = sorted({p.strip() for v in vals for p in v.split(sep) if p.strip()})
        if h.endswith(NOTE_SUFFIX):
            why = "free text, because the column name ends in %s" % NOTE_SUFFIX
            if h[:-len(NOTE_SUFFIX)] in header:
                item["note_of"] = h[:-len(NOTE_SUFFIX)]
        elif not vals:
            why = "free text, because the column is empty"
        elif all(v is not None for v in nums):
            if len(distinct) <= 7 and all(v == str(int(x)) for v, x in zip(vals, nums) if float(x).is_integer()) and all(float(x).is_integer() for x in nums):
                item["type"], item["options"] = "scale", [str(int(v)) for v in sorted({int(x) for x in nums})]
                why = "a scale, because every answer is one of %d whole number%s. Scale points nobody chose cannot be seen; a numeric summary is printed as well in case these are counts" % (len(distinct), "" if len(distinct) == 1 else "s")
            else:
                item["type"] = "number"
                why = "a number, because every answer is numeric"
        elif any(len(v) > 60 for v in vals):
            why = "free text, because some answers are long"
        elif any(sep in v for v in vals) and len(parts) <= 12 and any(sum(1 for v in vals if p in [x.strip() for x in v.split(sep)]) > 1 for p in parts):
            item["type"], item["options"] = "multi", parts
            why = "several choices per answer, because cells contain %r and the same choices recur. Options nobody chose cannot be seen" % sep
        elif len(distinct) > 12 or (len(distinct) == len(vals) and sum(len(v.split()) for v in vals) >= 3 * len(vals)):
            why = "free text, because the answers are nearly all different, or all different and several words each"
        else:
            item["type"], item["options"] = "single", distinct
            why = "single choice from the %d value%s seen. Options nobody chose cannot be seen, and their order is alphabetical, not the questionnaire's" % (len(distinct), "" if len(distinct) == 1 else "s")
        advisories.append("INFERRED %s: %s" % (h, why))
        out.append(item)
    return out


# ---------------------------------------------------------------- classifying answers

def classify(questions, rows, col, ids, allow_unknown, errors, advisories, marks=None):
    """For each question, give every respondent a status and a list of values.
    status: answered | skipped | not_shown | other. Skipped respondents are kept and counted.
    marks is None for a plain file. For a file in the collector's layout it holds the cells marked
    (skipped) or (not shown), and the file decides who was shown a question: the questionnaire that
    produced it knew, and writes (not shown) in every cell it hid."""
    data = {}
    for q in questions:
        qid, status, values = q["id"], [], []
        problems, ghosts, disagree = [], [], []
        for i, r in enumerate(rows):
            cell = r[col[qid]]
            shown = True
            if q["shown_if"]:
                ctrl, wanted = q["shown_if"]
                shown = data[ctrl]["status"][i] == "answered" and any(v in wanted for v in data[ctrl]["values"][i])
            if marks is not None:
                in_file = marks.get((i, qid)) != "not_shown"
                if in_file != shown and q["shown_if"]:
                    disagree.append(ids[i])
                shown = in_file
            if not shown:
                if cell:
                    ghosts.append(ids[i])
                status.append("not_shown")
                values.append([])
                continue
            if not cell:
                status.append("skipped")
                values.append([])
                continue
            if q["type"] == "text":
                status.append("answered")
                values.append([cell])
            elif q["type"] == "number":
                v = as_number(cell)
                if v is None:
                    problems.append("%s answered %r, which is not a number" % (ids[i], cell))
                    status.append("other")
                    values.append([])
                else:
                    status.append("answered")
                    values.append([v])
            else:
                picked = [p.strip() for p in cell.split(q["sep"]) if p.strip()] if q["type"] == "multi" else [cell]
                picked = list(dict.fromkeys(picked))
                bad = [p for p in picked if p not in q["options"]]
                if bad:
                    for b in bad:
                        near = [o for o in q["options"] if o.lower() == b.lower()]
                        problems.append("%s answered %r, which is not an option%s" % (ids[i], b, (" (it differs from %r only in capital letters)" % near[0]) if near else ""))
                    if allow_unknown:
                        status.append("answered")
                        values.append([p for p in picked if p in q["options"]] + [OTHER])
                    else:
                        status.append("other")
                        values.append([])
                else:
                    status.append("answered")
                    values.append(picked)
        if problems:
            msg = "%s: %s%s. Options: %s" % (qid, "; ".join(problems[:5]), "" if len(problems) <= 5 else "; and %d more" % (len(problems) - 5),
                                            ", ".join(q["options"]) if q["options"] else "a number")
            if allow_unknown and q["type"] != "number":
                advisories.append(msg + ". Counted as %r because --allow-unknown was given" % OTHER)
            else:
                errors.append(msg)
        if disagree:
            advisories.append("%s: for %d respondent(s) the file and the instrument's routing disagree about whether the question was shown (%s). "
                              "The file was followed, because the questionnaire marks every cell it hid; check shown_if in the instrument"
                              % (qid, len(disagree), ", ".join(disagree[:8])))
        if ghosts:
            advisories.append("%s: %d respondent(s) have an answer although the routing says the question was not shown to them (%s). Those answers are not counted; check the routing or the export"
                              % (qid, len(ghosts), ", ".join(ghosts[:8])))
        data[qid] = {"status": status, "values": values}
    return data


# ---------------------------------------------------------------- per-question summaries

def summarise_question(q, d, ids, z, scale_means):
    n = len(ids)
    st = d["status"]
    answered = [i for i in range(n) if st[i] == "answered"]
    skipped = [ids[i] for i in range(n) if st[i] == "skipped"]
    not_shown = [ids[i] for i in range(n) if st[i] == "not_shown"]
    other = [ids[i] for i in range(n) if st[i] == "other"]
    shown = n - len(not_shown)
    out = {"id": q["id"], "text": q["text"], "type": q["type"], "section": q["section"], "inferred": q["inferred"], "note_of": q["note_of"],
           "routing": None if not q["shown_if"] else "shown when %s is %s" % (q["shown_if"][0], " or ".join(q["shown_if"][1])),
           "respondents": n, "shown": shown, "not_shown": len(not_shown), "answered": len(answered), "skipped": len(skipped), "unrecognised": len(other),
           "skipped_ids": skipped, "not_shown_ids": not_shown, "skipped_of_shown": prop(len(skipped), shown, z)}
    if q["type"] in ("single", "multi", "scale"):
        opts = list(q["options"])
        if any(OTHER in d["values"][i] for i in answered):
            opts.append(OTHER)
        out["options"] = []
        for o in opts:
            c = sum(1 for i in answered if o in d["values"][i])
            entry = {"option": o, "count": c, "of_answered": prop(c, len(answered), z), "of_shown": prop(c, shown, z), "of_respondents": prop(c, n, z)}
            if q["correct"] is not None:
                entry["keyed_correct"] = (o == q["correct"])
            out["options"].append(entry)
        if q["type"] == "scale" and answered:
            pos = sorted(q["options"].index(d["values"][i][0]) for i in answered if d["values"][i][0] in q["options"])
            if pos:
                mids = sorted({pos[(len(pos) - 1) // 2], pos[len(pos) // 2]})
                out["middle_answer"] = [q["options"][m] for m in mids]
                if scale_means:
                    out["numeric_mean"] = {"mean": round(sum(p + 1 for p in pos) / len(pos), 2), "n": len(pos), "points": len(q["options"]),
                                           "caveat": "treats the %d scale points as the numbers 1 to %d, equally spaced; the scale itself only gives an order" % (len(q["options"]), len(q["options"]))}
    if q["type"] == "number" or (q["type"] == "scale" and q["inferred"]):
        vals = sorted(as_number(str(d["values"][i][0])) for i in answered)
        out["numbers"] = None if not vals else {"n": len(vals), "min": vals[0], "median": statistics.median(vals), "max": vals[-1], "mean": float("%.3g" % (sum(vals) / len(vals)))}
    return out


def render_question(q, level):
    L = []
    head = "%s [%s%s]" % (q["id"], q["type"], ", inferred" if q["inferred"] else "")
    if q["text"]:
        head += " %s" % q["text"]
    if q["section"]:
        head += "  (section: %s)" % q["section"]
    L.append(head)
    if q["note_of"]:
        L.append("  optional note: %d of %d respondents shown %s wrote one" % (q["answered"], q["shown"], q["note_of"]))
        return L
    line = "  shown to %d of %d respondents" % (q["shown"], q["respondents"])
    if q["not_shown"]:
        line += " (%d not shown; routing: %s)" % (q["not_shown"], q["routing"] or "not recorded")
    line += "; answered %d; skipped %d" % (q["answered"], q["skipped"])
    if q["skipped"]:
        line += " = %d%% of those shown (%s)" % (q["skipped_of_shown"]["percent"], ids_text(q["skipped_ids"]))
    if q["unrecognised"]:
        line += "; unrecognised answers %d" % q["unrecognised"]
    L.append(line)
    if "options" in q:
        width = max(len(o["option"]) for o in q["options"])
        for o in q["options"]:
            mark = "*" if o.get("keyed_correct") else " "
            s = "  %s %-*s  %s" % (mark, width, o["option"], prop_text(o["of_answered"], "who answered"))
            if q["skipped"] or q["unrecognised"]:
                s += "; %d of %d shown (%s)" % (o["count"], q["shown"], "%d%%" % o["of_shown"]["percent"] if o["of_shown"]["percent"] is not None else "no percentage")
            L.append(s)
        if q["type"] == "multi":
            L.append("    respondents could choose several, so these percentages add to more than 100")
        if any(o.get("keyed_correct") for o in q["options"]):
            L.append("    * keyed as correct")
        if "middle_answer" in q:
            L.append("    middle answer (median category): %s" % " / ".join(q["middle_answer"]))
        if "numeric_mean" in q:
            m = q["numeric_mean"]
            L.append("    mean %.2f on 1 to %d (n=%d): %s" % (m["mean"], m["points"], m["n"], m["caveat"]))
        if q.get("numbers"):
            m = q["numbers"]
            L.append("    as numbers: n=%d  min %g  median %g  max %g  mean %g" % (m["n"], m["min"], m["median"], m["max"], m["mean"]))
    elif q["type"] == "number":
        m = q["numbers"]
        L.append("    no numeric answers" if not m else "    n=%d  min %g  median %g  max %g  mean %g" % (m["n"], m["min"], m["median"], m["max"], m["mean"]))
    else:
        L.append("    %d free-text answer(s). Use --coding-sheet to export them for theme coding" % q["answered"])
    return L


def ids_text(ids, limit=12):
    return ", ".join(ids[:limit]) + ("" if len(ids) <= limit else " and %d more" % (len(ids) - limit))


# ---------------------------------------------------------------- cross-tab and comparison

def choice_question(qmap, qid, what):
    if qid not in qmap:
        raise Refusal("%s names %r, which is not a question in the data (%s)" % (what, qid, ", ".join(qmap)))
    if qmap[qid]["type"] not in ("single", "multi", "scale"):
        raise Refusal("%s needs a choice question, and %r is %s" % (what, qid, qmap[qid]["type"]))
    return qmap[qid]


def cross_tab(q1, q2, data, ids, z):
    d1, d2 = data[q1["id"]], data[q2["id"]]
    n = len(ids)
    both = [i for i in range(n) if d1["status"][i] == "answered" and d2["status"][i] == "answered"]
    rows = []
    for a in q1["options"]:
        members = [i for i in both if a in d1["values"][i]]
        cells = [{"option": b, "of_row": prop(sum(1 for i in members if b in d2["values"][i]), len(members), z)} for b in q2["options"]]
        rows.append({"option": a, "n": len(members), "one_respondent_points": None if not members else int(100.0 / len(members) + 0.5), "cells": cells})
    return {"rows_question": q1["id"], "columns_question": q2["id"], "respondents": n, "answered_both": len(both),
            "left_out": n - len(both), "rows_unanswered": sum(1 for i in range(n) if d1["status"][i] != "answered"),
            "columns_unanswered": sum(1 for i in range(n) if d2["status"][i] != "answered"), "rows": rows,
            "multi": q1["type"] == "multi" or q2["type"] == "multi"}


def render_cross(c):
    L = ["CROSS-TAB %s (rows) by %s (columns)" % (c["rows_question"], c["columns_question"])]
    L.append("  %d of %d respondents answered both. Left out: %d (%s unanswered or not shown: %d; %s unanswered or not shown: %d; some may be both)"
             % (c["answered_both"], c["respondents"], c["left_out"], c["rows_question"], c["rows_unanswered"], c["columns_question"], c["columns_unanswered"]))
    small = False
    for r in c["rows"]:
        if r["n"] == 0:
            L.append("  %s = %s: nobody" % (c["rows_question"], r["option"]))
            continue
        star = "*" if r["n"] <= 10 else ""
        small = small or bool(star)
        L.append("  %s = %s: %d respondent(s)%s; one respondent = %d points" % (c["rows_question"], r["option"], r["n"], star, r["one_respondent_points"]))
        width = max(len(x["option"]) for x in r["cells"])
        for x in r["cells"]:
            L.append("      %-*s  %s" % (width, x["option"], prop_text(x["of_row"], "in this row")))
    L.append("  Percentages are of each row's respondents, not of everyone.")
    if small:
        L.append("  CAVEAT  rows marked * have 10 or fewer respondents, so one answer moves their percentages by 10 points or more. Read the counts; do not rank these rows on percentages.")
    if c["multi"]:
        L.append("  A respondent who chose several options is counted in each, so counts can add to more than the row.")
    return L


def compare_groups(q, option, gq, pair, data, ids, z, level):
    wanted = split_options(q, option, "--compare")
    option = " or ".join(wanted)
    d, g = data[q["id"]], data[gq["id"]]
    n = len(ids)
    groups = []
    for name in gq["options"]:
        members = [i for i in range(n) if g["status"][i] == "answered" and name in g["values"][i] and d["status"][i] == "answered"]
        hits = sum(1 for i in members if any(o in d["values"][i] for o in wanted))
        groups.append({"group": name, "chose": prop(hits, len(members), z)})
    out = {"question": q["id"], "option": option, "by": gq["id"], "level": level, "groups": groups, "difference": None, "note": None,
           "left_out": sum(1 for i in range(n) if not (g["status"][i] == "answered" and d["status"][i] == "answered"))}
    live = [x for x in groups if x["chose"]["n"] > 0]
    if pair:
        for p in pair:
            if p not in gq["options"]:
                raise Refusal("--pair: %r is not a group of %s (%s)" % (p, gq["id"], ", ".join(gq["options"])))
        chosen = [next(x for x in groups if x["group"] == p) for p in pair]
    elif len(live) == 2:
        chosen = live
    else:
        out["note"] = "%d groups have respondents; a difference is between two. Name them with --pair A B" % len(live)
        return out
    a, b = chosen
    if a["chose"]["n"] == 0 or b["chose"]["n"] == 0:
        out["note"] = "one of the two groups has nobody who answered both questions, so there is no difference to compute"
        return out
    dd, lo, hi = newcombe(a["chose"]["count"], a["chose"]["n"], b["chose"]["count"], b["chose"]["n"], z)
    (l1, u1), (l2, u2) = a["chose"]["interval"], b["chose"]["interval"]
    ov = max(0.0, min(u1, u2) - max(l1, l2))
    narrower = min(u1 - l1, u2 - l2)
    share = 1.0 if narrower <= 0 else ov / narrower
    words = "do not overlap" if ov <= 0 else "overlap almost entirely" if share >= 0.9 else "overlap for most of their width" if share >= 0.5 else "overlap in part"
    out["difference"] = {"first": a["group"], "second": b["group"], "points": int(round(100 * dd)), "difference": round(dd, 4),
                         "interval": [round(lo, 4), round(hi, 4)], "interval_points": [int(round(100 * lo)), int(round(100 * hi))],
                         "method": "Newcombe hybrid score interval (1998, method 10), from the two Wilson intervals",
                         "includes_zero": lo <= 0.0 <= hi, "group_intervals": words}
    return out


def render_compare(c):
    L = ["COMPARISON  %s = %s, by %s" % (c["question"], c["option"], c["by"])]
    for g in c["groups"]:
        L.append("  %s = %s: %s" % (c["by"], g["group"], prop_text(g["chose"], "who answered both")))
    if c["left_out"]:
        L.append("  Left out: %d respondent(s) who did not answer both questions" % c["left_out"])
    d = c["difference"]
    if d is None:
        L.append("  " + c["note"])
        return L
    L.append("  Difference, %s minus %s: %+d points; %g%% interval %+d to %+d points (%s)" % (d["first"], d["second"], d["points"], c["level"], d["interval_points"][0], d["interval_points"][1], d["method"]))
    L.append("  The two groups' own intervals %s." % d["group_intervals"])
    if d["includes_zero"]:
        L.append("  The interval for the difference includes zero: these responses do not show which group is higher. That is not evidence the groups are the same.")
    else:
        L.append("  The interval for the difference excludes zero. It describes these respondents; whether it carries to anyone else depends on how they were reached.")
    return L


# ---------------------------------------------------------------- quiz item analysis

def quiz_analysis(questions, data, ids, z, fraction, want_pb):
    items = [q for q in questions if q["correct"] is not None]
    n = len(ids)
    right = {q["id"]: [1 if (data[q["id"]]["status"][i] == "answered" and data[q["id"]]["values"][i] == [q["correct"]]) else 0 for i in range(n)] for q in items}
    scores = [sum(right[q["id"]][i] for q in items) for i in range(n)]
    g = score_groups(scores, fraction)
    dist = [{"score": s, "respondents": scores.count(s)} for s in sorted(set(scores))]
    out = {"items": len(items), "respondents": n, "scoring": "one point for each keyed answer; an omitted item scores nothing",
           "scores": {"min": min(scores), "median": statistics.median(scores), "max": max(scores), "mean": round(sum(scores) / n, 1), "distribution": dist},
           "groups": {"fraction": fraction, "target_size": g["target_size"], "formed": g["formed"],
                      "upper": {"size": len(g["upper"]), "min_score": g["upper_cut"], "ids": [ids[i] for i in g["upper"]]},
                      "lower": {"size": len(g["lower"]), "max_score": g["lower_cut"], "ids": [ids[i] for i in g["lower"]]},
                      "one_respondent_moves_d_by": None},
           "item_analysis": [], "routed_items": [q["id"] for q in items if q["shown_if"]]}
    if g["formed"]:
        out["groups"]["one_respondent_moves_d_by"] = round(1.0 / min(len(g["upper"]), len(g["lower"])), 2)
    for q in items:
        d = data[q["id"]]
        shown = [i for i in range(n) if d["status"][i] != "not_shown"]
        up = [i for i in g["upper"] if i in shown] if g["formed"] else []
        lo = [i for i in g["lower"] if i in shown] if g["formed"] else []
        r = right[q["id"]]
        correct = sum(r[i] for i in shown)
        entry = {"id": q["id"], "text": q["text"], "keyed": q["correct"], "shown": len(shown), "omitted": sum(1 for i in shown if d["status"][i] != "answered"),
                 "difficulty": prop(correct, len(shown), z), "upper": {"correct": sum(r[i] for i in up), "n": len(up)},
                 "lower": {"correct": sum(r[i] for i in lo), "n": len(lo)}, "discrimination": None, "options": [], "flags": []}
        if up and lo:
            entry["discrimination"] = round(entry["upper"]["correct"] / len(up) - entry["lower"]["correct"] / len(lo), 2)
        if want_pb:
            item_s = [r[i] for i in shown]
            tot = [scores[i] for i in shown]
            pb, pbr = point_biserial(item_s, tot), point_biserial(item_s, [t - s for t, s in zip(tot, item_s)])
            entry["point_biserial"] = {"with_total": None if pb is None else round(pb, 2), "with_rest": None if pbr is None else round(pbr, 2), "n": len(shown)}
        for o in q["options"]:
            entry["options"].append({"option": o, "keyed": o == q["correct"], "all": sum(1 for i in shown if d["values"][i] == [o]),
                                     "upper": sum(1 for i in up if d["values"][i] == [o]), "lower": sum(1 for i in lo if d["values"][i] == [o])})
        entry["omitted_by_group"] = {"upper": sum(1 for i in up if d["status"][i] != "answered"), "lower": sum(1 for i in lo if d["status"][i] != "answered")}
        fl = entry["flags"]
        if shown and correct / len(shown) >= EASY:
            fl.append({"flag": "nearly everyone right", "detail": "%d of %d correct. It separates nobody. Check whether it is too easy or the wording gives the answer away" % (correct, len(shown))})
        if shown and correct / len(shown) <= HARD:
            fl.append({"flag": "nearly everyone wrong", "detail": "%d of %d correct. Check the key, the wording and whether this was taught" % (correct, len(shown))})
        for o in entry["options"]:
            if not o["keyed"] and o["all"] == 0:
                fl.append({"flag": "option nobody chose", "detail": "%r was chosen by 0 of %d. It is not working as a distractor" % (o["option"], len(shown))})
        if up and lo:
            for o in entry["options"]:
                if not o["keyed"] and o["upper"] >= 2 and o["upper"] / len(up) > o["lower"] / len(lo):
                    fl.append({"flag": "wrong option chosen more by the upper group", "detail": "%r: %d of %d in the upper group against %d of %d in the lower. Possible second right answer or ambiguity"
                               % (o["option"], o["upper"], len(up), o["lower"], len(lo))})
            best = max(entry["options"], key=lambda o: o["upper"])
            keyed = next(o for o in entry["options"] if o["keyed"])
            if not best["keyed"] and best["upper"] > keyed["upper"]:
                fl.append({"flag": "possible miskey", "detail": "the upper group's most-chosen answer is %r (%d of %d), not the keyed %r (%d of %d). Read the item against the key"
                           % (best["option"], best["upper"], len(up), keyed["option"], keyed["upper"], len(up))})
            if entry["discrimination"] is not None and entry["discrimination"] < 0:
                fl.append({"flag": "negative discrimination", "detail": "the lower group did better than the upper (D = %+.2f)" % entry["discrimination"]})
        out["item_analysis"].append(entry)
    return out


def render_quiz(qz, level):
    s, g = qz["scores"], qz["groups"]
    L = ["QUIZ ITEM ANALYSIS  (descriptive: it shows how each item behaved for these %d respondents)" % qz["respondents"]]
    L.append("  %d scored items; %s." % (qz["items"], qz["scoring"]))
    L.append("  Total score out of %d: min %g, median %g, max %g, mean %g" % (qz["items"], s["min"], s["median"], s["max"], s["mean"]))
    L.append("  Score: respondents   " + "  ".join("%d: %d" % (x["score"], x["respondents"]) for x in s["distribution"]))
    if g["formed"]:
        L.append("  Upper group: the %d respondent(s) scoring %d or more. Lower group: the %d scoring %d or fewer. (Target %d each, %g%% of %d; tied scores are kept together.)"
                 % (g["upper"]["size"], g["upper"]["min_score"], g["lower"]["size"], g["lower"]["max_score"], g["target_size"], 100 * g["fraction"], qz["respondents"]))
        L.append("  With groups this size, one respondent changing one answer moves D by up to %.2f. D is a description of these respondents, not a property of the item." % g["one_respondent_moves_d_by"])
    else:
        L.append("  Upper and lower groups could not be formed: the scores are too bunched (the %d highest and %d lowest scorers cannot be separated; both cuts fall on the score %d). D is not printed; difficulty and option counts still are."
                 % (g["target_size"], g["target_size"], g["upper"]["min_score"]))
    if qz["routed_items"]:
        L.append("  ADVISORY  %s were not shown to everyone, so total scores are not on the same footing for all respondents." % ", ".join(qz["routed_items"]))
    for it in qz["item_analysis"]:
        d = it["difficulty"]
        line = "  %s  keyed %s  correct %s" % (it["id"], it["keyed"], prop_text(d, "shown"))
        if it["omitted"]:
            line += "; omitted %d" % it["omitted"]
        if it["discrimination"] is not None:
            line += "; upper %d of %d, lower %d of %d, D = %+.2f" % (it["upper"]["correct"], it["upper"]["n"], it["lower"]["correct"], it["lower"]["n"], it["discrimination"])
        if "point_biserial" in it:
            pb = it["point_biserial"]
            line += "; point-biserial %s with total, %s with rest (n=%d)" % tuple(["n/a" if pb[k] is None else "%+.2f" % pb[k] for k in ("with_total", "with_rest")] + [pb["n"]])
        L.append(line)
        opts = "      chosen by all / upper / lower:  " + "   ".join("%s%s %d / %d / %d" % (o["option"], "*" if o["keyed"] else "", o["all"], o["upper"], o["lower"]) for o in it["options"])
        L.append(opts if it["upper"]["n"] else "      chosen by:  " + "   ".join("%s%s %d" % (o["option"], "*" if o["keyed"] else "", o["all"]) for o in it["options"]))
        for f in it["flags"]:
            L.append("      CANDIDATE  %s: %s" % (f["flag"], f["detail"]))
    L.append("  * keyed answer. CANDIDATE lines are items for a person to read against the question. They are not verdicts.")
    return L


# ---------------------------------------------------------------- free text: coding sheet and themes

def screen_text(text):
    found = []
    if EMAIL_RE.search(text):
        found.append("email address")
    if URL_RE.search(text):
        found.append("web address")
    if any(sum(ch.isdigit() for ch in m) >= 8 for m in PHONE_RE.findall(text)):
        found.append("phone number")
    return found


def passages(questions, data, ids):
    """Every non-empty free-text answer as (respondent id, question id, text), in file order."""
    out = []
    for q in questions:
        if q["type"] != "text":
            continue
        d = data[q["id"]]
        for i, rid in enumerate(ids):
            if d["status"][i] == "answered":
                out.append((rid, q["id"], d["values"][i][0]))
    return out


def write_sheet(path, rows, header, overwrite, inputs):
    p = Path(path)
    if any(p.resolve() == Path(x).resolve() for x in inputs if x):
        raise Refusal("%s is one of the input files; an input is never overwritten" % path)
    if p.exists() and not overwrite:
        raise Refusal("%s already exists; pass --overwrite to replace it" % path)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    try:
        p.write_bytes(buf.getvalue().encode("utf-8"))
    except OSError as e:
        raise Refusal("cannot write %s: %s" % (path, e.strerror or e))


def read_codebook(path):
    header, rows, lines, ragged = read_csv(path, "codebook")
    if "code" not in header or "definition" not in header:
        raise Refusal("codebook %s needs the columns code and definition" % path)
    if ragged:
        raise Refusal("codebook %s: line %d has %d cells, the header has %d" % (path, ragged[0][0], ragged[0][1], len(header)))
    book = {}
    for r in rows:
        code, definition = r[header.index("code")], r[header.index("definition")]
        if not code or not definition or code in book:
            raise Refusal("codebook %s: every code needs a definition and may appear once (problem at %r)" % (path, code))
        book[code] = definition
    return book


def theme_counts(sheet_path, book, all_passages, ids, z, errors, advisories):
    header, rows, lines, ragged = read_csv(sheet_path, "coded sheet")
    for need in ("respondent", "question", "themes"):
        if need not in header:
            raise Refusal("coded sheet %s needs the columns respondent, question, text and themes (missing %s)" % (sheet_path, need))
    for line, got in ragged:
        errors.append("coded sheet line %d has %d cells, the header has %d" % (line, got, len(header)))
    ci = {h: header.index(h) for h in header}
    known = {(r, q): t for r, q, t in all_passages}
    order = {rid: i for i, rid in enumerate(ids)}
    coded, seen_codes, edited = {}, {}, 0
    for r, line in zip(rows, lines):
        key = (r[ci["respondent"]], r[ci["question"]])
        if key[0] not in order:
            errors.append("coded sheet line %d: respondent %r is not in the responses. Check the sheet was made with the same --keep-ids setting" % (line, key[0]))
            continue
        if key not in known:
            errors.append("coded sheet line %d: %s gave no free-text answer to %r in the responses" % (line, key[0], key[1]))
            continue
        if key in coded:
            errors.append("coded sheet line %d: the passage %s / %s appears twice" % (line, key[0], key[1]))
            continue
        if "text" in ci and r[ci["text"]] != known[key] and r[ci["text"]] != "'" + known[key]:
            edited += 1
        codes = list(dict.fromkeys(c.strip() for c in r[ci["themes"]].split(SEP) if c.strip()))
        for c in codes:
            if book is not None and c not in book:
                errors.append("coded sheet line %d: code %r is not in the codebook (%s)" % (line, c, ", ".join(book)))
            other = seen_codes.setdefault(c.lower(), c)
            if other != c:
                errors.append("coded sheet line %d: code %r and code %r differ only in capital letters; use one" % (line, c, other))
        coded[key] = codes
    if edited:
        advisories.append("%d passage(s) in the coded sheet differ from the responses file (edited, redacted, or from a different export)" % edited)
    missing = [k for k in known if k not in coded]
    if missing:
        advisories.append("%d passage(s) in the responses are missing from the coded sheet and stay in the denominators as uncoded: %s"
                          % (len(missing), ", ".join("%s/%s" % k for k in missing[:8]) + ("" if len(missing) <= 8 else " and more")))
    codes_all = list(book) if book is not None else sorted({c for cs in coded.values() for c in cs})

    def block(keys):
        writers = sorted({k[0] for k in keys}, key=order.get)
        themes = []
        for c in codes_all:
            who = sorted({k[0] for k in keys if c in coded.get(k, [])}, key=order.get)
            themes.append({"code": c, "definition": None if book is None else book[c], "respondents": len(who),
                           "of_writers": prop(len(who), len(writers), z), "of_all_respondents": prop(len(who), len(ids), z),
                           "respondent_ids": who, "coded_passages": sum(1 for k in keys if c in coded.get(k, []))})
        themes.sort(key=lambda t: -t["respondents"])
        uncoded = sorted({k[0] for k in keys} - {k[0] for k in keys if coded.get(k)}, key=order.get)
        return {"writers": len(writers), "passages": len(keys), "themes": themes, "respondents_with_no_code": uncoded,
                "passages_with_no_code": sum(1 for k in keys if not coded.get(k))}
    keys = list(known)
    out = {"codebook": book is not None, "respondents": len(ids), "all_free_text": block(keys), "by_question": []}
    for qid in dict.fromkeys(k[1] for k in keys):
        b = block([k for k in keys if k[1] == qid])
        b["question"] = qid
        out["by_question"].append(b)
    if book is None:
        advisories.append("no codebook was given: codes are taken as found. Write a definition for each code so someone else could apply them, and pass it with --codebook")
    return out


def render_themes(th):
    L = ["THEMES  (the analyst's coding of free text, not something the respondents chose. Counts are respondents, never mentions.)"]

    def lines(b, indent, zeros=True):
        out = []
        shown = [t for t in b["themes"] if zeros or t["respondents"]]
        width = max([len(t["code"]) for t in shown] + [1])
        for t in shown:
            out.append("%s%-*s  %s; %d of %d respondents (%s) [in %d coded passage(s); %s]"
                       % (indent, width, t["code"], prop_text(t["of_writers"], "who wrote something"), t["respondents"], t["of_all_respondents"]["n"],
                          "%d%%" % t["of_all_respondents"]["percent"], t["coded_passages"], ids_text(t["respondent_ids"]) or "nobody"))
        if b["respondents_with_no_code"]:
            out.append("%sNo code at all: %d respondent(s) (%s). Read these: a case that fits no theme belongs in the findings." % (indent, len(b["respondents_with_no_code"]), ids_text(b["respondents_with_no_code"])))
        return out
    a = th["all_free_text"]
    L.append("  All free text together: %d of %d respondents wrote something, in %d passage(s); %d passage(s) carry no code" % (a["writers"], th["respondents"], a["passages"], a["passages_with_no_code"]))
    L += lines(a, "    ")
    if th["codebook"]:
        L.append("  Codebook:")
        L += ["    %s: %s" % (t["code"], t["definition"]) for t in a["themes"]]
    for b in th["by_question"]:
        L.append("  %s: %d respondent(s) wrote something (codes nobody used here are not listed)" % (b["question"], b["writers"]))
        L += lines(b, "    ", zeros=False)
    return L


# ---------------------------------------------------------------- main

def parse_args(argv):
    flags, opts, crosses, combines, args, i = set(), {}, [], [], [], 0
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            flags.add(a)
            i += 1
        elif a in VALUES:
            need = VALUES[a]
            vals = argv[i + 1:i + 1 + need]
            if len(vals) < need or any(v.startswith("--") for v in vals):
                raise Refusal("%s needs %d value%s" % (a, need, "" if need == 1 else "s"))
            if a == "--cross":
                crosses.append(vals)
            elif a == "--combine":
                if "=" not in vals[0]:
                    raise Refusal("--combine needs QUESTION=OPTION|OPTION (got %r)" % vals[0])
                combines.append(vals[0])
            elif a in opts:
                raise Refusal("%s was given twice" % a)
            else:
                opts[a] = vals[0] if need == 1 else vals
            i += 1 + need
        elif a.startswith("--"):
            raise Refusal("unknown option " + a)
        else:
            args.append(a)
            i += 1
    if len(args) != 1:
        raise Refusal("expected one responses file, got %d. Usage: analyse_responses.py RESPONSES.csv [--instrument FILE] [options]" % len(args))
    level = 95.0
    if "--level" in opts:
        level = as_number(opts["--level"])
        if level is None or not 50 < level < 100:
            raise Refusal("--level needs a number above 50 and below 100 (got %r)" % opts["--level"])
    fraction = 0.27
    if "--group-fraction" in opts:
        fraction = as_number(opts["--group-fraction"])
        if fraction is None or not 0.1 <= fraction <= 0.5:
            raise Refusal("--group-fraction needs a number from 0.1 to 0.5 (got %r)" % opts["--group-fraction"])
    if ("--compare" in opts) != ("--by" in opts):
        raise Refusal("--compare Q=OPTION and --by GROUPQ go together")
    if "--pair" in opts and "--compare" not in opts:
        raise Refusal("--pair is only used with --compare")
    if "--compare" in opts and "=" not in opts["--compare"]:
        raise Refusal("--compare needs QUESTION=OPTION (got %r)" % opts["--compare"])
    if "--codebook" in opts and "--themes" not in opts:
        raise Refusal("--codebook is only used with --themes")
    if "--overwrite" in flags and "--coding-sheet" not in opts and "--id-map" not in opts:
        raise Refusal("--overwrite is only used with --coding-sheet or --id-map")
    opts["combines"] = combines
    return args[0], flags, opts, crosses, level, fraction


def split_options(q, text, what):
    wanted = list(dict.fromkeys(o.strip() for o in text.split("|") if o.strip()))
    for o in wanted or [text]:
        if o not in q["options"]:
            raise Refusal("%s: %r is not an option of %s (%s)" % (what, o, q["id"], ", ".join(q["options"])))
    return wanted


def combine_options(q, text, d, ids, z):
    wanted = split_options(q, text, "--combine")
    n = len(ids)
    answered = [i for i in range(n) if d["status"][i] == "answered"]
    shown = sum(1 for s in d["status"] if s != "not_shown")
    c = sum(1 for i in answered if any(o in d["values"][i] for o in wanted))
    return {"question": q["id"], "options": wanted, "label": " or ".join(wanted), "of_answered": prop(c, len(answered), z),
            "of_shown": prop(c, shown, z), "of_respondents": prop(c, n, z)}


def analyse(path, flags, opts, crosses, level, fraction):
    """Returns (result dict, text lines). Raises Refusal for exit 2."""
    errors, advisories = [], []
    z = z_for(level)
    header, rows, lines, ragged = read_csv(path, "responses file")
    marks, layout, sep = None, None, SEP
    if "respondent" not in header and all(h in header for h in COLLECTOR_HEAD):
        header, rows, marks, layout = from_collector(path, header, rows, advisories)
        sep = COLLECTOR_SEP
    if "respondent" not in header:
        near = [h for h in header if h.lower() == "respondent"]
        raise Refusal("responses file %s has no column called respondent%s, and it is not in the elicitor collector's layout (which begins source, instrument, version, finished)"
                      % (path, (" (found %r: the name must be lower case)" % near[0]) if near else ""))
    if len(header) < 2:
        raise Refusal("responses file %s has no question columns" % path)
    for line, got in ragged:
        errors.append("line %d has %d cells but the header has %d. The row was not guessed at; fix the file (an unquoted comma in an answer is the usual cause)" % (line, got, len(header)))
    col = {h: i for i, h in enumerate(header)}
    originals = [r[col["respondent"]] for r in rows]
    for line, v in zip(lines, originals):
        if not v:
            errors.append("line %d has an empty respondent value" % line)
    where = {}
    for line, v in zip(lines, originals):
        where.setdefault(v, []).append(line)
    for v in sorted(v for v in where if v and len(where[v]) > 1):
        errors.append("the respondent value %r appears on %d rows (lines %s). One row per respondent: merge or remove the repeats"
                      % (v if "--keep-ids" in flags else "<hidden>", len(where[v]), ", ".join(str(l) for l in where[v])))
    if not rows and not ragged:
        errors.append("the file has a header and no respondents")
    if "--keep-ids" in flags:
        ids = list(originals)
    else:
        width = max(2, len(str(len(rows))))
        ids = ["R%0*d" % (width, i + 1) for i in range(len(rows))]
    inst = None
    if "--instrument" in opts:
        inst = read_json(opts["--instrument"], "instrument")
        questions = check_instrument(inst, header, errors, advisories, sep)
    elif not errors:
        questions = infer_questions(header, rows, col, advisories, sep)
        if layout:
            advisories.append("no instrument was given: options nobody chose are invisible and quiz items cannot be scored. Not shown is known here, because the file marks it")
        else:
            advisories.append("no instrument was given: an empty cell cannot be told apart from a question that was not shown, options nobody chose are invisible, and quiz items cannot be scored")
    result = {"file": str(path), "instrument": opts.get("--instrument"), "level": level, "errors": errors, "advisories": advisories, "layout": layout}
    if errors:
        return result, None
    data = classify(questions, rows, col, ids, "--allow-unknown" in flags, errors, advisories, marks)
    if errors:
        return result, None
    qmap = {q["id"]: q for q in questions}
    n = len(ids)
    coll = (inst or {}).get("collection", {}) if inst else {}
    real = [q for q in questions if not q["note_of"]]
    closed = [q for q in real if q["type"] != "text"]
    complete = sum(1 for i in range(n) if all(data[q["id"]]["status"][i] in ("answered", "not_shown") for q in closed))
    blank = [ids[i] for i in range(n) if all(data[q["id"]]["status"][i] != "answered" for q in questions)]
    over = {"respondents": n, "questions": len(real), "title": (inst or {}).get("title") if inst else None,
            "reached": coll.get("reached") if text_ok(coll.get("reached")) else None, "missing": coll.get("missing") if text_ok(coll.get("missing")) else None,
            "invited": coll.get("invited"), "responded_of_invited": None, "closed_questions": len(closed),
            "answered_every_closed_question_shown": prop(complete, n, z) if closed else None, "answered_nothing": blank,
            "ids": "kept as given" if "--keep-ids" in flags else "replaced by %s to %s in file order" % (ids[0], ids[-1])}
    if over["invited"] is not None:
        if over["invited"] < n:
            advisories.append("collection.invited is %d but there are %d respondents; the response count over invited is not printed" % (over["invited"], n))
        else:
            over["responded_of_invited"] = prop(n, over["invited"], z)
    if over["reached"] is None:
        advisories.append("how respondents were reached is NOT STATED. Say it before anything else in the findings: without it these results describe the %d who answered and nobody else" % n)
    if blank:
        advisories.append("%d respondent(s) answered nothing (%s). They are counted as respondents and as skips" % (len(blank), ids_text(blank)))
    result["overview"] = over
    result["questions"] = [summarise_question(q, data[q["id"]], ids, z, "--scale-means" in flags) for q in questions]
    result["cross"] = [cross_tab(choice_question(qmap, a, "--cross"), choice_question(qmap, b, "--cross"), data, ids, z) for a, b in crosses]
    result["combined"] = []
    for text in opts.get("combines", []):
        qid, wanted = text.split("=", 1)
        cq = choice_question(qmap, qid.strip(), "--combine")
        result["combined"].append(combine_options(cq, wanted, data[cq["id"]], ids, z))
    result["compare"] = None
    if "--compare" in opts:
        qid, option = opts["--compare"].split("=", 1)
        result["compare"] = compare_groups(choice_question(qmap, qid.strip(), "--compare"), option.strip(), choice_question(qmap, opts["--by"], "--by"),
                                           opts.get("--pair"), data, ids, z, level)
    result["quiz"] = quiz_analysis(questions, data, ids, z, fraction, "--point-biserial" in flags) if any(q["correct"] is not None for q in questions) else None
    all_passages = passages(questions, data, ids)
    hits = [(r, q, screen_text(t)) for r, q, t in all_passages]
    flagged = [(r, q, f) for r, q, f in hits if f]
    if flagged:
        advisories.append("%d free-text passage(s) contain what looks like contact details (%s). Remove or mask them before quoting. Names, workplaces and roles are not detected: read every quotation"
                          % (len(flagged), ", ".join("%s/%s: %s" % (r, q, " and ".join(f)) for r, q, f in flagged[:6])))
    inputs = [path, opts.get("--instrument"), opts.get("--themes"), opts.get("--codebook")]
    result["coding_sheet"] = None
    if "--coding-sheet" in opts:
        guarded = sum(1 for _r, _q, t in all_passages if t.startswith(GUARDED))
        write_sheet(opts["--coding-sheet"], [[r, q, ("'" + t) if t.startswith(GUARDED) else t, "; ".join(screen_text(t)), ""] for r, q, t in all_passages],
                    ["respondent", "question", "text", "screen", "themes"], "--overwrite" in flags, inputs)
        result["coding_sheet"] = {"path": opts["--coding-sheet"], "passages": len(all_passages), "respondents": len({r for r, _, _ in all_passages}),
                                  "spreadsheet_guards_added": guarded}
    if "--id-map" in opts:
        write_sheet(opts["--id-map"], [[i, o] for i, o in zip(ids, originals)], ["id", "respondent"], "--overwrite" in flags, inputs + [opts.get("--coding-sheet")])
    result["themes"] = None
    if "--themes" in opts:
        book = read_codebook(opts["--codebook"]) if "--codebook" in opts else None
        th = theme_counts(opts["--themes"], book, all_passages, ids, z, errors, advisories)
        if errors:
            return result, None
        result["themes"] = th
    L = ["analyse_responses: %s%s" % (path, "" if not over["title"] else "  (%s)" % over["title"])]
    L.append("WHO ANSWERED")
    L.append("  Respondents (rows): %d. Questions: %d. Respondent ids: %s." % (n, over["questions"], over["ids"]))
    if over["responded_of_invited"]:
        p = over["responded_of_invited"]
        rest = "Everyone invited responded." if p["count"] == p["n"] else "The other %d are not described by anything below." % (p["n"] - p["count"])
        L.append("  Invited: %d. Responded: %d of %d invited (%d%%). %s" % (p["n"], p["count"], p["n"], p["percent"], rest))
    L.append("  How they were reached: %s" % (over["reached"] or "NOT STATED"))
    L.append("  Who is missing: %s" % (over["missing"] or "NOT STATED"))
    if closed:
        L.append("  Answered every closed question shown to them: %d of %d respondents (%d%%). Free-text questions are left out of this count."
                 % (complete, n, over["answered_every_closed_question_shown"]["percent"]))
    else:
        L.append("  There are no closed questions in this file, only free text.")
    L.append("  Intervals are %g%% Wilson score intervals. They show how far a proportion could move with this many answers; they do not correct for who was reached." % level)
    if "--skip-questions" in flags:
        L.append("QUESTIONS  (%d; per-question counts left out of this text because --skip-questions was given)" % over["questions"])
    else:
        L.append("QUESTIONS")
        for q in result["questions"]:
            L += render_question(q, level)
    for c in result["combined"]:
        L.append("COMBINED  %s = %s: %s; %d of %d shown (%s); %d of %d respondents (%s)"
                 % (c["question"], c["label"], prop_text(c["of_answered"], "who answered"), c["of_shown"]["count"], c["of_shown"]["n"],
                    "no percentage" if c["of_shown"]["percent"] is None else "%d%%" % c["of_shown"]["percent"],
                    c["of_respondents"]["count"], c["of_respondents"]["n"], "%d%%" % c["of_respondents"]["percent"]))
    for c in result["cross"]:
        L += render_cross(c)
    if result["compare"]:
        L += render_compare(result["compare"])
    if result["quiz"]:
        L += render_quiz(result["quiz"], level)
    if result["coding_sheet"]:
        cs = result["coding_sheet"]
        L.append("CODING SHEET  wrote %d passage(s) from %d respondent(s) to %s. Add theme codes in the themes column, separated by %r, then run again with --themes."
                 % (cs["passages"], cs["respondents"], cs["path"], SEP))
        if cs["spreadsheet_guards_added"]:
            L.append("  %d passage(s) begin with =, +, - or @. In the sheet each has an apostrophe in front so a spreadsheet does not run it as a formula; the apostrophe is not part of the answer."
                     % cs["spreadsheet_guards_added"])
    if "--id-map" in opts:
        L.append("ID MAP  wrote %s. It links ids to the original respondent values: keep it private." % opts["--id-map"])
    if result["themes"]:
        L += render_themes(result["themes"])
    if advisories:
        L.append("NOTES")
        L += ["  ADVISORY  " + a for a in advisories]
    L.append("RESULT: RAN. 0 errors, %d advisory note(s). Counts describe the %d respondents in this file." % (len(advisories), n))
    return result, L


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    if not argv:
        emit(__doc__)
        return 2
    try:
        path, flags, opts, crosses, level, fraction = parse_args(argv)
        result, lines = analyse(path, flags, opts, crosses, level, fraction)
    except Refusal as e:
        print("analyse_responses: %s" % str(e).encode("ascii", "replace").decode("ascii"), file=sys.stderr)
        return 2
    failed = bool(result["errors"])
    if "--json" in flags:
        emit(json.dumps(result, indent=1, ensure_ascii=True, allow_nan=False))
    elif failed:
        L = ["analyse_responses: %s was refused" % path]
        L += ["  ERROR     " + e for e in result["errors"]]
        L += ["  ADVISORY  " + a for a in result["advisories"]]
        L.append("RESULT: REFUSED. %d error(s). No analysis was produced." % len(result["errors"]))
        emit("\n".join(L))
    else:
        emit("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
