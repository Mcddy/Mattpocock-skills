#!/usr/bin/env python3
"""Check a questionnaire's data block before anyone fills it in. Standard library only.

Usage:
  python validate_instrument.py ENGINE_OR_JSON [--engine REFERENCE.html] [--json]
  python validate_instrument.py --compare OLD NEW [--json]

ENGINE_OR_JSON is either a built questionnaire (an .html copy of assets/engine.html, in which case
the object between the "BEGIN INSTRUMENT DATA" and "END INSTRUMENT DATA" marker lines is read) or a
.json file holding the same object. The object must be strict JSON: double quotes, no trailing
commas, no comments, no NaN or Infinity, no key written twice.

Instrument fields (the full contract is in references/modes.md):
  {"id": "project-intake", "version": 1, "mode": "intake" | "survey" | "quiz", "title": "...",
   "purpose": "...", "intro": "...", "layout": "one" | "sections", "notes": "on" | "off",
   "feedback": "immediate" | "at_end",                       quiz only
   "disclosure": {"who": "...", "purpose": "...", "handling": "..."},   required in survey mode
   "sections": [{"id": "scope", "title": "Scope"}],
   "questions": [{"id": "goal", "section": "scope", "type": "single", "text": "...",
                  "options": ["...", "..."], "required": false, "note": true, "tags": ["x"],
                  "show_if": {"q": "earlier-id", "equals": "..."}}],
   "tallies": [{"id": "habits", "label": "Habits that apply", "tag": "x", "when": {"equals": "Yes"}}]}
Types: single, multi, text, likert (labels: 4 or 5), scale (min, max, step, min_label, max_label),
number (min, max, unit, integer), rank. Quiz options are objects:
  {"text": "...", "correct": true, "explain": "why this option is right or wrong"}

What it enforces (ERROR, exit 1):
  - id, version, mode, title and a non-empty question list are present and well formed
  - every question has an id matching [a-z0-9_-]+ that is not a bare position (7, q7, item-7),
    and no id is used twice; positions change when a questionnaire is revised and ids must not
  - every type is known and has what it needs; a choice question has 2 to 8 options, none empty,
    none repeated, none equal to an export marker such as "(skipped)"
  - a quiz item is single or multi, has a correct answer (exactly one for single), and an
    explanation on every option
  - survey mode has all three disclosure fields
  - show_if names an earlier question and uses a test that fits that question's type
  - a tally names a tag that some question carries, and its "when" test is well formed
  - with --engine: everything outside the data block is identical to the reference engine
What it reports for a person to decide (ADVISORY, never a failure):
  - wording that may ask two things at once (" and " or " or " in a question with one answer;
    not checked in quiz mode, where these words usually join the facts given)
  - a leading opener ("Don't you", "Wouldn't you agree")
  - an absolute ("always", "never") in a statement to rate
  - number ranges in an option list that overlap or leave a gap
  - quiz: correct answers bunched in one position; one option much longer than the others;
    "all of the above" style options
  - more than 60 questions; a large share of free-text questions; a tally label that reads like
    a diagnosis, a type or a percentile; fields this version does not know
With --compare OLD NEW it checks a revision. ERROR: a different instrument id; a version that was
not raised although questions changed; an id that was removed; an id whose type changed; an id
whose wording changed so much that it looks reused for a different question. ADVISORY: reworded
questions that still look like the same question; options removed from a kept question. New ids
are fine.

What it cannot tell: whether the questions are the right ones, whether a flagged wording is really
a problem, whether a quiz's marked answer is true, or whether respondents will understand an item.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import difflib
import json
import math
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"[a-z0-9_-]+")
POSITION_RE = re.compile(r"(?:q|qn|question|item|no|n)?[-_]?\d+")
TYPES = ("single", "multi", "text", "likert", "scale", "number", "rank")
MODES = ("intake", "survey", "quiz")
RESERVED_OPTIONS = ("(skipped)", "(no answer)")
BEGIN_MARK = "/* ====== BEGIN INSTRUMENT DATA"
END_MARK = "/* ====== END INSTRUMENT DATA"
TOP_KEYS = {"id", "version", "mode", "title", "purpose", "intro", "layout", "notes", "feedback", "minutes",
            "disclosure", "sections", "questions", "tallies"}
Q_KEYS = {"id", "section", "type", "text", "help", "options", "labels", "min", "max", "step", "min_label", "max_label",
          "unit", "integer", "long", "required", "note", "note_label", "show_if", "tags"}
FLAGS = {"--json", "--compare"}
VALUES = {"--engine"}
LEADING = ("don't you", "dont you", "do you not", "wouldn't you", "wouldnt you", "isn't it", "isnt it", "surely",
           "do you agree that", "would you agree", "how much do you love", "how great", "how bad")
ABSOLUTES = ("always", "never", "every", "everyone", "everybody", "nobody", "no one", "all", "none")
SOFT_WORDS = ("percentile", "diagnos", "disorder", "personality", " type", "iq", "syndrome", "clinical")


class InputError(Exception):
    """The input could not be read at all (exit 2)."""


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def is_num(v):
    try:
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    except (OverflowError, ValueError):
        return False


def text_ok(v):
    return isinstance(v, str) and v.strip() != ""


def norm(s):
    return " ".join(str(s).casefold().split())


def no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError("the key %r is written twice in one object" % k)
        seen[k] = v
    return seen


def refuse_constant(name):
    raise ValueError("%s is not allowed; write a real number" % name)


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


def split_engine(text, path):
    """Return (before, json_text, after) for a built questionnaire, or raise InputError."""
    if text.count(BEGIN_MARK) != 1 or text.count(END_MARK) != 1:
        raise InputError("%s must contain exactly one BEGIN INSTRUMENT DATA and one END INSTRUMENT DATA marker line (found %d and %d)"
                         % (path, text.count(BEGIN_MARK), text.count(END_MARK)))
    a, b = text.index(BEGIN_MARK), text.index(END_MARK)
    if b < a:
        raise InputError("%s has its END marker before its BEGIN marker" % path)
    m = re.compile(r"const\s+INSTRUMENT\s*=\s*").search(text, a, b)
    if not m:
        raise InputError("%s has no 'const INSTRUMENT =' between the marker lines" % path)
    body = text[m.end():b]
    stripped = body.rstrip()
    if not stripped.endswith(";"):
        raise InputError("%s: the data block must end with a semicolon before the END marker line" % path)
    end = m.end() + len(stripped) - 1
    return text[:m.end()], text[m.end():end], text[end:]


def load_instrument(path):
    """Read an instrument from a built .html file or a .json file. Returns (object, kind)."""
    text = read_text(path)
    kind = "json"
    src = text
    offset = 0
    if BEGIN_MARK in text or "<html" in text.lower()[:2000]:
        kind = "engine"
        before, src, _after = split_engine(text, path)
        offset = before.count("\n")
    try:
        data = json.loads(src, object_pairs_hook=no_dupes, parse_constant=refuse_constant)
    except ValueError as e:
        line = getattr(e, "lineno", None)
        where = (" at line %d of the file" % (line + offset)) if line else ""
        raise InputError("%s: the data block is not strict JSON%s (%s)" % (path, where, str(e)[:110]))
    return data, kind


def number_ranges(options):
    """Pull whole-number ranges out of option texts. Returns [(lo, hi, text)] with None for open ends."""
    out = []
    for t in options:
        s = str(t).lower().replace(",", "")
        m = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", s)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), t))
            continue
        m = re.search(r"(?:under|below|less than|fewer than)\s+(\d+)", s)
        if m:
            out.append((None, int(m.group(1)) - 1, t))
            continue
        m = re.search(r"up to\s+(\d+)|(\d+)\s+or (?:less|fewer)", s)
        if m:
            out.append((None, int(m.group(1) or m.group(2)), t))
            continue
        m = re.search(r"(?:over|above|more than)\s+(\d+)", s)
        if m:
            out.append((int(m.group(1)) + 1, None, t))
            continue
        m = re.search(r"(\d+)\s*(?:\+|or more|and over|and above)", s)
        if m:
            out.append((int(m.group(1)), None, t))
    return out


def check_cond(c, dep, where, errors, allowed):
    """Check one test object (show_if or a tally's when) against the question it reads."""
    ops = [k for k in c if k != "q"]
    if len(ops) != 1 or ops[0] not in allowed:
        errors.append("%s needs exactly one test from: %s" % (where, ", ".join(allowed)))
        return
    op, val = ops[0], c[ops[0]]
    if op == "answered":
        if not isinstance(val, bool):
            errors.append("%s: answered must be true or false" % where)
        return
    if op in ("at_least", "at_most"):
        if not is_num(val):
            errors.append("%s: %s needs a number (text, true and NaN are not numbers)" % (where, op))
        elif dep is not None and dep.get("type") not in ("likert", "scale", "number"):
            errors.append("%s: %s only works on a likert, scale or number question" % (where, op))
        return
    if dep is None:
        return
    t = dep.get("type")
    opts = [o.get("text") if isinstance(o, dict) else o for o in dep.get("options", [])] if isinstance(dep.get("options"), list) else []
    if op == "includes":
        if t != "multi":
            errors.append("%s: includes only works on a multi question; %r is %s" % (where, dep.get("id"), t))
        elif val not in opts:
            errors.append("%s: %r is not one of the options of %r" % (where, val, dep.get("id")))
    elif op == "equals":
        if t == "single":
            if val not in opts:
                errors.append("%s: %r is not one of the options of %r" % (where, val, dep.get("id")))
        elif t in ("likert", "scale", "number"):
            if not is_num(val):
                errors.append("%s: equals on a %s question needs a number" % (where, t))
        elif t == "text":
            if not isinstance(val, str):
                errors.append("%s: equals on a text question needs text" % where)
        else:
            errors.append("%s: equals does not work on a %s question; use includes or answered" % (where, t))


def check(inst):
    """Return (errors, advisories, facts) for one instrument object."""
    errors, adv, facts = [], [], {}
    if not isinstance(inst, dict):
        return ["the data block must be one JSON object"], [], {}
    for k in sorted(set(inst) - TOP_KEYS):
        adv.append("unknown field %r at the top level; the engine ignores it. Check the spelling" % k)
    iid = inst.get("id")
    if not isinstance(iid, str) or not ID_RE.fullmatch(iid):
        errors.append("id must be lower-case letters, digits, hyphens or underscores, for example 'project-intake'")
    ver = inst.get("version")
    if not is_int(ver) or ver < 1:
        errors.append("version must be a whole number from 1 (true and \"1\" are not numbers)")
    mode = inst.get("mode")
    if mode not in MODES:
        errors.append("mode must be one of: %s" % ", ".join(MODES))
    if not text_ok(inst.get("title")) or "\n" in str(inst.get("title")):
        errors.append("title is missing, empty or runs over more than one line")
    if "layout" in inst and inst["layout"] not in ("one", "sections"):
        errors.append("layout must be 'one' or 'sections'")
    if "notes" in inst and inst["notes"] not in ("on", "off"):
        errors.append("notes must be 'on' or 'off'")
    if "minutes" in inst and (not is_num(inst["minutes"]) or inst["minutes"] <= 0):
        errors.append("minutes must be a positive number")
    if mode == "quiz":
        if "feedback" in inst and inst["feedback"] not in ("immediate", "at_end"):
            errors.append("feedback must be 'immediate' or 'at_end'")
        if inst.get("layout") == "sections":
            adv.append("layout 'sections' is ignored in quiz mode: a quiz always shows one item at a time")
        if inst.get("tallies"):
            errors.append("tallies are not used in quiz mode; a quiz reports its score")
    elif "feedback" in inst:
        adv.append("feedback is only used in quiz mode")
    if mode == "survey":
        d = inst.get("disclosure")
        for k, what in (("who", "who is asking"), ("purpose", "what it is for"), ("handling", "what happens to the answers")):
            if not isinstance(d, dict) or not text_ok(d.get(k)):
                errors.append("survey mode needs disclosure.%s (%s): the respondent is told this before the first question" % (k, what))
    sec_ids = []
    secs = inst.get("sections", [])
    if not isinstance(secs, list):
        errors.append("sections must be a list")
        secs = []
    for i, s in enumerate(secs):
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not ID_RE.fullmatch(s["id"]):
            errors.append("section %d needs an id of lower-case letters, digits, hyphens or underscores" % (i + 1))
            continue
        if s["id"] in sec_ids:
            errors.append("section id %r is used twice" % s["id"])
        sec_ids.append(s["id"])
        if not text_ok(s.get("title")):
            errors.append("section %r has no title" % s["id"])
    qs = inst.get("questions")
    if not isinstance(qs, list) or not qs:
        errors.append("questions must be a non-empty list")
        return errors, adv, facts
    seen, order, tags_used, correct_pos, n_text = {}, [], set(), [], 0
    for i, q in enumerate(qs):
        where = "question %d" % (i + 1)
        if not isinstance(q, dict):
            errors.append(where + " is not an object")
            continue
        qid = q.get("id")
        if qid is None or qid == "":
            errors.append(where + " has no id")
            continue
        if not isinstance(qid, str) or not ID_RE.fullmatch(qid):
            errors.append("%s: id %r must match [a-z0-9_-]+ (lower-case letters, digits, hyphens, underscores)" % (where, qid))
            continue
        where = "question %r" % qid
        if POSITION_RE.fullmatch(qid):
            errors.append("%s: the id is a bare position. Positions change when the list is revised and old exports stop lining up; name it for what it asks, for example 'goal' or 'q7-goal'" % where)
        if qid in seen:
            errors.append("%s: the id is used twice (questions %d and %d)" % (where, seen[qid] + 1, i + 1))
            continue
        seen[qid] = i
        order.append(qid)
        for k in sorted(set(q) - Q_KEYS):
            adv.append("%s: unknown field %r; the engine ignores it" % (where, k))
        qtype = q.get("type")
        if qtype not in TYPES:
            errors.append("%s: unknown type %r; use one of %s" % (where, qtype, ", ".join(TYPES)))
            continue
        text = q.get("text")
        if not text_ok(text):
            errors.append(where + " has no text")
            text = ""
        elif "\n" in text:
            errors.append(where + ": the text runs over more than one line; put detail in 'help'")
        if sec_ids and q.get("section") not in sec_ids:
            errors.append("%s: section %r is not one of the sections listed (%s)" % (where, q.get("section"), ", ".join(sec_ids)))
        for k in ("required", "note", "integer", "long"):
            if k in q and not isinstance(q[k], bool):
                errors.append("%s: %s must be true or false, not %r" % (where, k, q[k]))
        tags = q.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) and ID_RE.fullmatch(t) for t in tags):
            errors.append(where + ": tags must be a list of short lower-case names")
        else:
            tags_used.update(tags)
        opt_texts = []
        if mode == "quiz" and qtype not in ("single", "multi"):
            errors.append("%s: quiz items must be single or multi, so that every option can be marked and explained; %s is not" % (where, qtype))
        if qtype in ("single", "multi", "rank"):
            opts = q.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                errors.append("%s: a %s question needs at least 2 options (has %d)" % (where, qtype, len(opts) if isinstance(opts, list) else 0))
                opts = opts if isinstance(opts, list) else []
            elif len(opts) > 8:
                errors.append("%s: has %d options; the most a person can weigh on one screen is 8. Split it or group the options" % (where, len(opts)))
            n_correct = 0
            for j, o in enumerate(opts):
                ot = o.get("text") if isinstance(o, dict) else o
                if not text_ok(ot):
                    errors.append("%s: option %d is empty or not text" % (where, j + 1))
                    continue
                if ot != ot.strip() or "\n" in ot or "\t" in ot:
                    errors.append("%s: option %d has a line break, a tab or spaces at its ends" % (where, j + 1))
                if ot.strip().lower() in RESERVED_OPTIONS:
                    errors.append("%s: option %r is the same as an export marker and could not be told apart from it" % (where, ot))
                opt_texts.append(ot)
                if mode == "quiz":
                    if not isinstance(o, dict):
                        errors.append("%s: option %r must be an object with text, correct and explain" % (where, ot))
                        continue
                    if "correct" in o and not isinstance(o["correct"], bool):
                        errors.append("%s: option %r: correct must be true or false" % (where, ot))
                    if o.get("correct") is True:
                        n_correct += 1
                    if not text_ok(o.get("explain")):
                        errors.append("%s: option %r has no explanation; every option is explained, right or wrong" % (where, ot))
                elif isinstance(o, dict) and "correct" in o:
                    adv.append("%s: option %r marks a correct answer, which is ignored outside quiz mode" % (where, ot))
            keyed = [norm(t) for t in opt_texts]
            for t in sorted({opt_texts[k] for k in range(len(keyed)) if keyed.count(keyed[k]) > 1}):
                errors.append("%s: the option %r appears more than once" % (where, t))
            if mode == "quiz" and qtype in ("single", "multi"):
                if n_correct == 0:
                    errors.append("%s: no option is marked correct" % where)
                elif qtype == "single" and n_correct > 1:
                    errors.append("%s: %d options are marked correct; a single-answer item has exactly one. Use type 'multi' for select-all" % (where, n_correct))
                elif qtype == "multi" and n_correct == len(opts):
                    adv.append("%s: every option is marked correct, so ticking everything always scores" % where)
                if qtype == "single" and n_correct == 1:
                    correct_pos.append((len(opts), [k for k, o in enumerate(opts) if isinstance(o, dict) and o.get("correct") is True][0]))
                lens = [len(t) for t in opt_texts]
                if len(lens) >= 3:
                    longest = max(range(len(lens)), key=lambda k: lens[k])
                    rest = [x for k, x in enumerate(lens) if k != longest]
                    if lens[longest] >= 1.8 * (sum(rest) / len(rest)) and lens[longest] - max(rest) >= 15:
                        is_key = isinstance(opts[longest], dict) and opts[longest].get("correct") is True
                        adv.append("%s: one option is much longer than the others (%d characters against an average of %d)%s"
                                   % (where, lens[longest], round(sum(rest) / len(rest)), ", and it is the correct one: length can give the answer away" if is_key else ""))
                for t in opt_texts:
                    if re.search(r"\b(all|none|both) of the above\b|\ball of these\b|\bnone of these\b", t.lower()):
                        adv.append("%s: the option %r tests reading of the list more than knowledge of the topic" % (where, t))
            rng = number_ranges(opt_texts)
            if qtype == "single" and len(rng) >= 2:
                srt = sorted(rng, key=lambda r: (-1 if r[0] is None else r[0]))
                for a, b in zip(srt, srt[1:]):
                    if a[1] is None or b[0] is None:
                        if a[1] is None:
                            adv.append("%s: the ranges %r and %r overlap" % (where, a[2], b[2]))
                    elif b[0] <= a[1]:
                        adv.append("%s: the ranges %r and %r overlap at %d; a person with that value has two right answers" % (where, a[2], b[2], b[0]))
                    elif b[0] > a[1] + 1:
                        adv.append("%s: there is a gap between %r and %r (%d to %d has no option)" % (where, a[2], b[2], a[1] + 1, b[0] - 1))
        if qtype == "likert":
            labs = q.get("labels")
            if not isinstance(labs, list) or len(labs) not in (4, 5) or not all(text_ok(x) for x in labs):
                errors.append("%s: a likert question needs 'labels' with 4 or 5 entries, one for each point" % where)
            elif len({norm(x) for x in labs}) != len(labs):
                errors.append("%s: two likert labels are the same" % where)
        if qtype == "scale":
            lo, hi, step = q.get("min"), q.get("max"), q.get("step", 1)
            if not (is_int(lo) and is_int(hi) and is_int(step)) or hi <= lo or step < 1 or (hi - lo) % step != 0:
                errors.append("%s: a scale needs whole-number min, max and step, with max above min and the step dividing the range" % where)
            elif (hi - lo) // step > 100:
                errors.append("%s: the scale has more than 101 points; use type 'number'" % where)
            if not text_ok(q.get("min_label")) or not text_ok(q.get("max_label")):
                adv.append("%s: a scale end has no label, so the numbers have no stated meaning" % where)
        if qtype == "number":
            for k in ("min", "max"):
                if k in q and not is_num(q[k]):
                    errors.append("%s: %s must be a number (text, true and NaN are not numbers)" % (where, k))
            if is_num(q.get("min")) and is_num(q.get("max")) and q["min"] > q["max"]:
                errors.append("%s: min is above max" % where)
            if "unit" in q and not isinstance(q["unit"], str):
                errors.append("%s: unit must be text" % where)
        if qtype == "text":
            n_text += 1
        low = " " + norm(text) + " "
        if mode != "quiz" and qtype in ("single", "likert", "scale", "number") and re.search(r" (and|or) ", low):
            adv.append("%s: the wording joins two things with 'and' or 'or' and takes one answer. If they can differ, split it: %r" % (where, text[:90]))
        if any(low.strip().startswith(norm(p)) for p in LEADING):
            adv.append("%s: the opening leads towards an answer: %r" % (where, text[:60]))
        if qtype in ("likert", "scale"):
            hit = [w for w in ABSOLUTES if " %s " % w in low]
            if hit:
                adv.append("%s: a statement to rate contains an absolute (%s); most people read these as direction, not literally, so agreement is hard to interpret" % (where, ", ".join(hit)))
        si = q.get("show_if")
        if si is not None:
            if not isinstance(si, dict) or not isinstance(si.get("q"), str):
                errors.append("%s: show_if must be an object naming an earlier question in 'q'" % where)
            elif si["q"] not in seen or si["q"] == qid:
                later = any(isinstance(x, dict) and x.get("id") == si["q"] for x in qs[i:])
                errors.append("%s: show_if points at %r, which is %s. It can only read a question that comes before this one"
                              % (where, si["q"], "this question or a later one" if later else "not a question in this instrument"))
            else:
                check_cond(si, qs[seen[si["q"]]], where + " show_if", errors, ("equals", "includes", "answered"))
    facts["questions"] = len(order)
    facts["sections"] = len(sec_ids)
    if len(order) > 60:
        adv.append("there are %d questions; past about 60, answers get shorter and more careless. Cut, or split into two sittings" % len(order))
    if mode != "quiz" and len(order) >= 6 and n_text * 3 > len(order):
        adv.append("%d of %d questions are free text; typing that much on a phone is slow. Keep free text for what choices cannot capture" % (n_text, len(order)))
    if len(correct_pos) >= 6:
        counts = {}
        for _n, pos in correct_pos:
            counts[pos] = counts.get(pos, 0) + 1
        pos, top = max(counts.items(), key=lambda kv: kv[1])
        if top * 2 > len(correct_pos):
            adv.append("the correct answer is in position %d in %d of %d single-answer items; a test-wise reader can score by position. Reorder the options"
                       % (pos + 1, top, len(correct_pos)))
    tl = inst.get("tallies", [])
    if tl and not isinstance(tl, list):
        errors.append("tallies must be a list")
        tl = []
    t_ids = set()
    for i, t in enumerate(tl or []):
        where = "tally %d" % (i + 1)
        if not isinstance(t, dict) or not isinstance(t.get("id"), str) or not ID_RE.fullmatch(t["id"]):
            errors.append(where + " needs an id of lower-case letters, digits, hyphens or underscores")
            continue
        where = "tally %r" % t["id"]
        if t["id"] in t_ids:
            errors.append(where + ": the id is used twice")
        t_ids.add(t["id"])
        if not text_ok(t.get("label")):
            errors.append(where + " has no label")
        elif any(w in " " + t["label"].lower() for w in SOFT_WORDS):
            adv.append("%s: the label %r reads like a diagnosis, a type or a ranking. A tally is a count of answers and must be named as one" % (where, t["label"]))
        if not isinstance(t.get("tag"), str) or t.get("tag") not in tags_used:
            errors.append("%s: the tag %r is not carried by any question, so the tally would count nothing" % (where, t.get("tag")))
        if "when" in t:
            if not isinstance(t["when"], dict):
                errors.append(where + ": when must be an object with one test")
            else:
                check_cond(t["when"], None, where + " when", errors, ("equals", "includes", "at_least", "at_most", "answered"))
    return errors, adv, facts


def by_id(inst):
    out = {}
    for q in inst.get("questions", []) if isinstance(inst, dict) and isinstance(inst.get("questions"), list) else []:
        if isinstance(q, dict) and isinstance(q.get("id"), str) and q["id"] not in out:
            out[q["id"]] = q
    return out


def option_texts(q):
    src = q.get("options") if isinstance(q.get("options"), list) else (q.get("labels") if isinstance(q.get("labels"), list) else [])
    return [o.get("text") if isinstance(o, dict) else o for o in src]


def compare(old, new):
    """Check that a revision keeps question ids stable. Returns (errors, advisories, facts)."""
    errors, adv = [], []
    if not isinstance(old, dict) or not isinstance(new, dict):
        return ["both files must hold one instrument object"], [], {}
    if old.get("id") != new.get("id"):
        errors.append("the instrument id changed from %r to %r; that makes it a different questionnaire, and old exports will be refused" % (old.get("id"), new.get("id")))
    a, b = by_id(old), by_id(new)
    removed = [k for k in a if k not in b]
    added = [k for k in b if k not in a]
    changed = False
    for k in removed:
        changed = True
        errors.append("id %r (%r) is in the old version and missing from the new one. Old exports carry it; keep the id, or keep the question and stop showing it"
                      % (k, str(a[k].get("text"))[:50]))
    for k in a:
        if k not in b:
            continue
        qa, qb = a[k], b[k]
        semantic = ("options", "labels", "show_if", "min", "max", "step", "integer", "required", "unit")
        fields = [field for field in semantic if qa.get(field) != qb.get(field)]
        if fields:
            changed = True
            adv.append("id %r changed answer or scoring semantics: %s; verify migration before reusing saved answers" % (k, ", ".join(fields)))
        if qa.get("type") != qb.get("type"):
            changed = True
            errors.append("id %r changed type from %s to %s; old answers to it cannot be read as the new type. Give the new question a new id" % (k, qa.get("type"), qb.get("type")))
        ta, tb = norm(qa.get("text", "")), norm(qb.get("text", ""))
        if ta != tb:
            changed = True
            ratio = difflib.SequenceMatcher(None, ta.split(), tb.split()).ratio()
            if ratio < 0.6:
                errors.append("id %r now carries different wording, so it looks reused for another question (word overlap %.2f). Old: %r. New: %r. A new question needs a new id"
                              % (k, ratio, str(qa.get("text"))[:60], str(qb.get("text"))[:60]))
            else:
                adv.append("id %r was reworded (word overlap %.2f). Confirm it still asks the same thing. Old: %r. New: %r" % (k, ratio, str(qa.get("text"))[:60], str(qb.get("text"))[:60]))
        gone = [t for t in option_texts(qa) if t not in option_texts(qb)]
        if gone and qa.get("type") == qb.get("type"):
            changed = True
            adv.append("id %r lost or renamed %d option(s): %s. Old answers that used them will not load into the new version" % (k, len(gone), ", ".join(repr(t) for t in gone[:4])))
        elif option_texts(qa) != option_texts(qb):
            changed = True
    if added:
        changed = True
    va, vb = old.get("version"), new.get("version")
    if is_int(va) and is_int(vb):
        if vb < va:
            errors.append("the version went down from %d to %d" % (va, vb))
        elif vb == va and changed:
            errors.append("questions changed but the version is still %d; raise it so that saved answers and exports can tell the two apart" % va)
    else:
        errors.append("both versions must be whole numbers")
    facts = {"kept": len([k for k in a if k in b]), "added": added, "removed": removed}
    return errors, adv, facts


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("validate_instrument: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("validate_instrument: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    want = 2 if "--compare" in flags else 1
    if len(args) != want:
        print("validate_instrument: expected %d file(s), got %d. Usage: validate_instrument.py ENGINE_OR_JSON [--engine REFERENCE.html] [--json]  |  --compare OLD NEW [--json]"
              % (want, len(args)), file=sys.stderr)
        return 2
    if "--compare" in flags and "--engine" in opts:
        print("validate_instrument: --engine cannot be used with --compare", file=sys.stderr)
        return 2
    try:
        loaded = [load_instrument(p) for p in args]
        if "--compare" in flags:
            errors, adv, facts = compare(loaded[0][0], loaded[1][0])
            head = "validate_instrument: comparing %s (old) with %s (new): %d id(s) kept, %d added, %d removed" % (
                args[0], args[1], facts.get("kept", 0), len(facts.get("added", [])), len(facts.get("removed", [])))
        else:
            errors, adv, facts = check(loaded[0][0])
            if "--engine" in opts:
                if loaded[0][1] != "engine":
                    print("validate_instrument: --engine compares two built .html files; %s is a .json file" % args[0], file=sys.stderr)
                    return 2
                mine = split_engine(read_text(args[0]), args[0])
                ref = split_engine(read_text(opts["--engine"]), opts["--engine"])
                if (mine[0], mine[2]) != (ref[0], ref[2]):
                    la, lb = (mine[0] + "\n@@\n" + mine[2]).split("\n"), (ref[0] + "\n@@\n" + ref[2]).split("\n")
                    first = next((n for n, (x, y) in enumerate(zip(la, lb)) if x != y), min(len(la), len(lb)))
                    errors.append("the page outside the data block differs from the reference engine, first at line %d of the part outside the block. Only the data block may be edited; rebuild from the reference engine"
                                  % (first + 1))
                facts["engine_identical"] = (mine[0], mine[2]) == (ref[0], ref[2])
            head = "validate_instrument: %s, %d question(s) in %d section(s)" % (args[0], facts.get("questions", 0), facts.get("sections", 0))
    except InputError as e:
        print("validate_instrument: %s" % e, file=sys.stderr)
        return 2
    if "--json" in flags:
        emit(json.dumps({"errors": errors, "advisories": adv, "facts": facts}, indent=1, ensure_ascii=True))
    else:
        L = [head]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in adv]
        L.append("RESULT: %s. %d error(s), %d advisory note(s). Advisories are candidates for a person to judge. This checks form, not whether the questions are the right ones."
                 % ("FAIL" if errors else "PASS", len(errors), len(adv)))
        emit("\n".join(L))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
