#!/usr/bin/env python3
"""Turn a pasted questionnaire export back into structured JSON. Standard library only.

Usage:
  python parse_export.py EXPORT [--json]

EXPORT is a text file holding what a questionnaire page showed on its last screen:
  - the markdown export of intake or quiz mode (it has an "Instrument:" line, a block per question
    starting "### [id] question text", and a last line "End of export: N questions."), or
  - the response block of survey mode (from "=== elicitor response ===" to the line that starts
    "=== end elicitor response:").
Text before and after the export is ignored and counted in an advisory, so a whole chat message
can be saved to a file and parsed as it is.

Without --json it prints a short summary. With --json it prints one object:
  {"format": "elicitor-markdown-1" | "elicitor-response-1",
   "instrument": {"id": "...", "version": 1, "mode": "...", "title": "..."},
   "finished": "2026-10-09T03:12:45Z", "purpose": "...",
   "counts": {"shown": 0, "answered": 0, "skipped": 0, "no_answer": 0, "hidden": 0},
   "questions": [{"id": "...", "section": "...", "text": "...", "type": "single",
                  "status": "answered" | "skipped" | "no_answer" | "hidden",
                  "answer": ..., "note": "..." or null}],
   "tallies": [{"id": "...", "label": "...", "count": 0, "of": 0, "answered": 0}],
   "score": {"correct": 0, "attempted": 0, "total": 0, "skipped": 0, "no_answer": 0, "rule": "..."},
   "errors": [], "advisories": []}
Answers by type: single is text; multi and rank are lists of text; text is text with its line
breaks; likert is a whole number, with "points" and "label" beside it; scale and number are
numbers, number with "unit" beside it. Quiz items also carry "result" and, when not correct,
"correct_answer". A response block carries ids and values only: it has no question text.

What it enforces (ERROR, exit 1):
  - the export is whole: its header and its last line are present, and the number of question
    blocks equals the number its last line states
  - the counts in the header equal the counts worked out from the blocks
  - every block has a known type and an answer that fits that type; no id appears twice
  - quiz: every item has a result, and the Score section equals the count of results
  - a tallies section ends with its caveat line
What it reports for a person to decide (ADVISORY): lines outside the export that were ignored;
wrapped lines in a response block that were joined back together.

What it cannot tell: whether the export was edited by hand in a way that keeps the counts
consistent, or which version of the questions the answers were given to beyond the version number
the export states. It never guesses a damaged value: the block is reported and the exit code is 1.

Exit codes: 0 parsed with no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

TALLY_LINE = "These totals are counts of your answers. They are not a validated measure of anything."
TYPES = ("single", "multi", "text", "likert", "scale", "number", "rank")
ID = r"[a-z0-9_-]+"
RE_INSTRUMENT = re.compile(r"Instrument: (%s), version (\d+), (intake|survey|quiz) mode" % ID)
RE_COUNTS = re.compile(r"Questions shown: (\d+)\. Answered: (\d+)\. Skipped: (\d+)\. No answer: (\d+)\. Hidden by earlier answers: (\d+)\.")
RE_QUESTION = re.compile(r"### \[(%s)\] (.*)" % ID)
RE_END = re.compile(r"End of export: (\d+) questions?\.")
RE_TALLY = re.compile(r"- \[(%s)\] (.*): (\d+) of (\d+) \(answered: (\d+)\)" % ID)
RE_STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
RE_NUMBER = re.compile(r"(-?\d+(?:\.\d+)?)(?: (.*))?")
RE_KEY = re.compile(r"(%s)(\.note)? = (.*)" % ID)
RE_TALLY_KEY = re.compile(r"tally:(%s) = (.*)" % ID)
BLOCK_OPEN = "=== elicitor response ==="
RE_BLOCK_CLOSE = re.compile(r"=== end elicitor response: (\d+) questions?, (\d+) notes? ===")
FLAGS = {"--json"}


class InputError(Exception):
    """The input could not be read at all (exit 2)."""


def read_text(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise InputError("cannot read %s: %s" % (path, e.strerror or e))
    if b"\x00" in raw:
        raise InputError("%s contains NUL bytes; it is not a text file" % path)
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise InputError("%s is not valid UTF-8 (byte %d)" % (path, e.start))


def to_lines(text):
    """Split on line feeds only, and drop trailing spaces, tabs and carriage returns."""
    return [ln.rstrip(" \t\r") for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def real_stamp(s):
    if not isinstance(s, str) or not RE_STAMP.fullmatch(s):
        return False
    try:
        dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def unquote(lines):
    return "\n".join("" if ln == ">" else ln[2:] for ln in lines)


def to_number(s):
    return float(s) if "." in s else int(s)


def finish_block(b, mode, errors):
    """Turn the raw lines gathered for one question into its record."""
    where = "question %r" % b["id"]
    q = {"id": b["id"], "section": b["section"], "text": b["text"], "type": b["type"], "status": None, "answer": None, "note": None}
    if b["type"] is None:
        errors.append(where + " has no Type line")
        return q
    if b["type"] not in TYPES:
        errors.append("%s has an unknown type %r" % (where, b["type"]))
        return q
    head, body = b["head"], b["body"]
    if head is None:
        errors.append(where + " has no Answer line; the export may be cut inside this block")
        return q
    if head == "(skipped)" and not body:
        q["status"] = "skipped"
    elif head == "(no answer)" and not body:
        q["status"] = "no_answer"
    else:
        q["status"] = "answered"
        t, bad = b["type"], None
        if t == "single":
            if not head or body:
                bad = "expected one line of text"
            q["answer"] = head
        elif t == "multi":
            if head or not body or not all(ln.startswith("- ") for ln in body):
                bad = "expected a list of '- ' lines"
            q["answer"] = [ln[2:] for ln in body]
        elif t == "rank":
            items = [re.fullmatch(r"(\d+)\. (.*)", ln) for ln in body]
            if head or not body or not all(items) or [int(m.group(1)) for m in items if m] != list(range(1, len(body) + 1)):
                bad = "expected a numbered list starting at 1"
            q["answer"] = [m.group(2) for m in items if m]
        elif t == "text":
            if head or not body or not all(ln == ">" or ln.startswith("> ") for ln in body):
                bad = "expected quoted lines starting with '> '"
            q["answer"] = unquote(body)
        elif t == "likert":
            m = re.fullmatch(r"(\d+) of (\d+), (.*)", head)
            if not m or body or not 1 <= int(m.group(1)) <= int(m.group(2)):
                bad = "expected 'N of M, label'"
            else:
                q["answer"], q["points"], q["label"] = int(m.group(1)), int(m.group(2)), m.group(3)
        elif t == "scale":
            if not re.fullmatch(r"-?\d+", head) or body:
                bad = "expected a whole number"
            else:
                q["answer"] = int(head)
        elif t == "number":
            m = RE_NUMBER.fullmatch(head)
            if not m or body:
                bad = "expected a number, with its unit after a space"
            else:
                q["answer"], q["unit"] = to_number(m.group(1)), (m.group(2) or None)
        if bad:
            errors.append("%s: the answer does not fit type %s (%s)" % (where, t, bad))
            q["answer"] = None
            q["status"] = None
    if b["note"]:
        if not all(ln == ">" or ln.startswith("> ") for ln in b["note"]):
            errors.append(where + ": the note is not in quoted lines")
        else:
            q["note"] = unquote(b["note"])
    if mode == "quiz":
        q["result"] = b["result"]
        want = {"answered": ("correct", "incorrect"), "skipped": ("skipped",), "no_answer": ("no answer",)}.get(q["status"], ())
        if b["result"] not in want:
            errors.append("%s: the Result line %r does not go with a status of %s" % (where, b["result"], q["status"]))
        if b["correct_head"] is not None:
            q["correct_answer"] = [ln[2:] for ln in b["correct"]] if b["type"] == "multi" else b["correct_head"]
        elif b["result"] != "correct":
            errors.append(where + ": a quiz item that is not correct must state the correct answer")
    return q


def parse_markdown(lines):
    """Parse the markdown export. Returns the result object, with errors listed inside it."""
    errors, adv = [], []
    start = next((i for i, ln in enumerate(lines) if RE_INSTRUMENT.fullmatch(ln)), None)
    if start is None:
        return {"format": None, "errors": ["this is not a questionnaire export: no line reads 'Instrument: <id>, version <n>, <mode> mode'"], "advisories": []}
    m = RE_INSTRUMENT.fullmatch(lines[start])
    title_at = next((i for i in range(start - 1, -1, -1) if lines[i].startswith("# ")), None)
    title = lines[title_at][2:] if title_at is not None else None
    if title is None:
        errors.append("the title line ('# ...') above the Instrument line is missing")
    end = next((i for i in range(start, len(lines)) if RE_END.fullmatch(lines[i])), None)
    out = {"format": "elicitor-markdown-1", "instrument": {"id": m.group(1), "version": int(m.group(2)), "mode": m.group(3), "title": title},
           "finished": None, "purpose": None, "counts": None, "questions": [], "tallies": [], "score": None}
    mode = m.group(3)
    first = title_at if title_at is not None else start
    ignored = sum(1 for ln in lines[:first] if ln) + (sum(1 for ln in lines[end + 1:] if ln) if end is not None else 0)
    if ignored:
        adv.append("%d line(s) outside the export were ignored" % ignored)
    if end is None:
        errors.append("the export is cut short: its last line ('End of export: N questions.') is missing")
        end = len(lines)
    blocks, cur, state, section, area = [], None, None, None, "head"
    score, tallies, caveat = {}, [], False
    for ln in lines[start + 1:end]:
        if cur is None and area == "head":
            if ln.startswith("Finished: "):
                out["finished"] = ln[10:]
                if not real_stamp(out["finished"]):
                    errors.append("the Finished line %r is not a real time written YYYY-MM-DDTHH:MM:SSZ" % out["finished"])
                continue
            if ln.startswith("Purpose: "):
                out["purpose"] = ln[9:]
                continue
            c = RE_COUNTS.fullmatch(ln)
            if c:
                out["counts"] = dict(zip(("shown", "answered", "skipped", "no_answer", "hidden"), (int(x) for x in c.groups())))
                continue
        h = RE_QUESTION.fullmatch(ln)
        if h:
            cur = {"id": h.group(1), "text": h.group(2), "section": section, "type": None, "head": None, "body": [], "note": [],
                   "result": None, "correct_head": None, "correct": []}
            blocks.append(cur)
            state, area = None, "questions"
            continue
        if ln.startswith("## "):
            cur, state = None, None
            if ln.startswith("## Section: "):
                section, area = ln[12:], "questions"
            elif ln == "## Score":
                area = "score"
            elif ln == "## Tallies":
                area = "tallies"
            else:
                errors.append("unexpected heading %r" % ln)
            continue
        if cur is not None:
            if ln == "":
                state = None
            elif state in ("body", "note", "correct") and (ln.startswith(">") or ln.startswith("- ") or re.match(r"\d+\. ", ln)):
                cur[state].append(ln)
            elif ln.startswith("Type: "):
                cur["type"] = re.match(r"[a-z]*", ln[6:]).group(0)
                state = None
            elif ln == "Answer:" or ln.startswith("Answer: "):
                cur["head"], state = ln[8:], "body"
            elif ln == "Note:":
                state = "note"
            elif ln.startswith("Result: "):
                cur["result"], state = ln[8:], None
            elif ln == "Correct answer:" or ln.startswith("Correct answer: "):
                cur["correct_head"], state = ln[16:], "correct"
            else:
                errors.append("question %r: unexpected line %r" % (cur["id"], ln[:60]))
            continue
        if area == "score" and ln:
            k, _, v = ln.partition(": ")
            key = {"Correct": "correct", "Attempted": "attempted", "Total": "total", "Skipped": "skipped", "No answer": "no_answer"}.get(k)
            if key and re.fullmatch(r"\d+", v):
                score[key] = int(v)
            elif k == "Rule":
                score["rule"] = v
            else:
                errors.append("unexpected line in the Score section: %r" % ln[:60])
        elif area == "tallies" and ln:
            t = RE_TALLY.fullmatch(ln)
            if t:
                tallies.append({"id": t.group(1), "label": t.group(2), "count": int(t.group(3)), "of": int(t.group(4)), "answered": int(t.group(5))})
            elif ln == TALLY_LINE:
                caveat = True
            else:
                errors.append("unexpected line in the Tallies section: %r" % ln[:60])
        elif ln and area == "head":
            errors.append("unexpected line in the header: %r" % ln[:60])
    seen = set()
    for b in blocks:
        if b["id"] in seen:
            errors.append("question id %r appears twice" % b["id"])
        seen.add(b["id"])
        out["questions"].append(finish_block(b, mode, errors))
    stated = RE_END.fullmatch(lines[end]) if end < len(lines) else None
    if stated and int(stated.group(1)) != len(blocks):
        errors.append("the last line states %s question(s) but %d block(s) were found; part of the export is missing" % (stated.group(1), len(blocks)))
    got = {"shown": len(blocks), "answered": 0, "skipped": 0, "no_answer": 0}
    for q in out["questions"]:
        if q["status"] in got:
            got[q["status"]] += 1
    if out["counts"] is None:
        errors.append("the header line with the counts ('Questions shown: ...') is missing")
    else:
        for k in ("shown", "answered", "skipped", "no_answer"):
            if out["counts"][k] != got[k]:
                errors.append("the header says %s = %d but the blocks give %d" % (k, out["counts"][k], got[k]))
    if out["finished"] is None:
        errors.append("the Finished line is missing")
    if mode == "quiz":
        want = {"correct": sum(1 for q in out["questions"] if q.get("result") == "correct"), "attempted": got["answered"],
                "total": got["shown"], "skipped": got["skipped"], "no_answer": got["no_answer"]}
        if not all(k in score for k in want):
            errors.append("the Score section is missing or incomplete")
        else:
            for k, v in want.items():
                if score[k] != v:
                    errors.append("the Score section says %s = %d but the items give %d" % (k, score[k], v))
        out["score"] = score or None
    elif score:
        errors.append("a Score section appears in an export that is not from quiz mode")
    if tallies or area == "tallies":
        out["tallies"] = tallies
        if not caveat:
            errors.append("the Tallies section has lost its caveat line; a tally is never reported without it")
        out["tally_caveat"] = TALLY_LINE if caveat else None
    out["errors"], out["advisories"] = errors, adv
    return out


def parse_response_blocks(lines, source=""):
    """Find every survey response block in the lines. Returns a list of result objects."""
    found, i = [], 0
    while i < len(lines):
        if lines[i] != BLOCK_OPEN:
            i += 1
            continue
        errors, adv = [], []
        j = next((k for k in range(i + 1, len(lines)) if RE_BLOCK_CLOSE.fullmatch(lines[k]) or lines[k] == BLOCK_OPEN), None)
        out = {"format": "elicitor-response-1", "source": source, "line": i + 1, "instrument": {"id": None, "version": None},
               "finished": None, "questions": [], "tallies": []}
        if j is None or lines[j] == BLOCK_OPEN:
            errors.append("the response block that starts at line %d has no closing line ('=== end elicitor response: ...'); it was cut short" % (i + 1))
            out["errors"], out["advisories"] = errors, adv
            found.append(out)
            i = j if j is not None else len(lines)
            continue
        joined, rejoined = [], 0
        for ln in lines[i + 1:j]:
            if ln == "":
                continue
            if re.match(r"(instrument|version|finished): ", ln) or RE_KEY.fullmatch(ln) or RE_TALLY_KEY.fullmatch(ln) or not joined:
                joined.append(ln)
            else:
                joined[-1] += ln
                rejoined += 1
        if rejoined:
            adv.append("%d wrapped line(s) were joined back onto the line before; check the text of long answers" % rejoined)
        byid, order, notes = {}, [], 0
        for ln in joined:
            meta = re.fullmatch(r"(instrument|version|finished): (.*)", ln)
            if meta:
                k, v = meta.groups()
                if k == "instrument":
                    out["instrument"]["id"] = v if re.fullmatch(ID, v) else None
                elif k == "version":
                    out["instrument"]["version"] = int(v) if re.fullmatch(r"\d+", v) else None
                else:
                    out["finished"] = v
                continue
            t = RE_TALLY_KEY.fullmatch(ln)
            if t:
                try:
                    pair = json.loads(t.group(2))
                    assert isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in pair)
                    out["tallies"].append({"id": t.group(1), "count": pair[0], "of": pair[1]})
                except (ValueError, AssertionError):
                    errors.append("the tally line for %r is damaged" % t.group(1))
                continue
            m = RE_KEY.fullmatch(ln)
            if not m:
                errors.append("unreadable line in the block: %r" % ln[:60])
                continue
            qid, is_note, raw = m.groups()
            if qid not in byid:
                byid[qid] = {"id": qid, "status": None, "answer": None, "note": None}
                order.append(qid)
            q = byid[qid]
            if is_note:
                try:
                    note = json.loads(raw)
                    assert isinstance(note, str)
                    q["note"] = note
                    notes += 1
                except (ValueError, AssertionError):
                    errors.append("the note for %r is damaged; it is not guessed at" % qid)
                continue
            if q["status"] is not None:
                errors.append("question id %r appears twice in the block" % qid)
                continue
            if raw in ("SKIPPED", "HIDDEN", "NONE"):
                q["status"] = {"SKIPPED": "skipped", "HIDDEN": "hidden", "NONE": "no_answer"}[raw]
                continue
            try:
                val = json.loads(raw, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    try:
                        finite = math.isfinite(val)
                    except (OverflowError, ValueError):
                        finite = False
                    if not finite:
                        raise ValueError("answer is outside the finite numeric range")
            except ValueError:
                errors.append("the answer for %r is damaged (%r); it is not guessed at" % (qid, raw[:40]))
                continue
            ok = isinstance(val, str) or (isinstance(val, (int, float)) and not isinstance(val, bool)) or (isinstance(val, list) and val and all(isinstance(x, str) for x in val))
            if not ok:
                errors.append("the answer for %r is not text, a number or a list of text" % qid)
                continue
            q["status"], q["answer"] = "answered", val
        out["questions"] = [byid[k] for k in order]
        for q in out["questions"]:
            if q["status"] is None:
                errors.append("question %r has a note but no answer line" % q["id"])
        close = RE_BLOCK_CLOSE.fullmatch(lines[j])
        if int(close.group(1)) != len(order):
            errors.append("the closing line states %s question(s) but %d were found; part of the block is missing" % (close.group(1), len(order)))
        if int(close.group(2)) != notes:
            errors.append("the closing line states %s note(s) but %d were found; part of the block is missing" % (close.group(2), notes))
        if out["instrument"]["id"] is None or out["instrument"]["version"] is None:
            errors.append("the block does not state its instrument id and version")
        if not real_stamp(out["finished"]):
            errors.append("the block's finished line is missing or is not a real time written YYYY-MM-DDTHH:MM:SSZ")
        got = {"shown": 0, "answered": 0, "skipped": 0, "no_answer": 0, "hidden": 0}
        for q in out["questions"]:
            if q["status"] in got:
                got[q["status"]] += 1
            if q["status"] and q["status"] != "hidden":
                got["shown"] += 1
        out["counts"] = got
        out["errors"], out["advisories"] = errors, adv
        found.append(out)
        i = j + 1
    return found


def parse_text(text, source=""):
    """Parse either kind of export from text. Returns one result object."""
    lines = to_lines(text)
    if BLOCK_OPEN in lines:
        blocks = parse_response_blocks(lines, source)
        out = blocks[0]
        if len(blocks) > 1:
            out["errors"] = out["errors"] + ["the file holds %d response blocks; parse_export reads one. Use collect_responses.py for several" % len(blocks)]
        outside = sum(1 for ln in lines[:out["line"] - 1] if ln)
        if outside:
            out["advisories"] = out["advisories"] + ["%d line(s) before the block were ignored" % outside]
        return out
    return parse_markdown(lines)


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a in FLAGS:
            flags.add(a)
        elif a.startswith("--"):
            print("parse_export: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print("parse_export: expected one file. Usage: parse_export.py EXPORT [--json]", file=sys.stderr)
        return 2
    try:
        text = read_text(args[0])
    except InputError as e:
        print("parse_export: %s" % e, file=sys.stderr)
        return 2
    if not text.strip():
        print("parse_export: %s is empty" % args[0], file=sys.stderr)
        return 2
    out = parse_text(text, args[0])
    errors = out.get("errors", [])
    if "--json" in flags:
        emit(json.dumps(out, indent=1, ensure_ascii=True))
    else:
        L = []
        if out.get("format"):
            ins = out["instrument"]
            qs = out.get("questions", [])
            n = {s: sum(1 for q in qs if q["status"] == s) for s in ("answered", "skipped", "no_answer", "hidden")}
            L.append("parse_export: %s, instrument %s version %s%s" % (out["format"], ins.get("id"), ins.get("version"), (", %s mode" % ins["mode"]) if ins.get("mode") else ""))
            # A markdown export leaves hidden questions out and states their number in its header;
            # a response block lists them. Report the same figure for both.
            hidden = max(n["hidden"], (out.get("counts") or {}).get("hidden") or 0)
            L.append("  %d question(s) shown: %d answered, %d skipped, %d with no answer; %d hidden by earlier answers; %d with a note"
                     % (len(qs) - n["hidden"], n["answered"], n["skipped"], n["no_answer"], hidden, sum(1 for q in qs if q.get("note"))))
            if out.get("score"):
                s = out["score"]
                L.append("  score: %s correct of %s attempted, of %s in total; %s skipped" % (s.get("correct"), s.get("attempted"), s.get("total"), s.get("skipped")))
            for t in out.get("tallies") or []:
                L.append("  tally %s: %d of %d" % (t["id"], t["count"], t["of"]))
            if out.get("tallies"):
                L.append("  " + TALLY_LINE)
        else:
            L.append("parse_export: %s" % args[0])
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in out.get("advisories", [])]
        L.append("RESULT: %s. %d error(s). Use --json for the full structure." % ("FAIL" if errors else "PASS", len(errors)))
        emit("\n".join(L))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
