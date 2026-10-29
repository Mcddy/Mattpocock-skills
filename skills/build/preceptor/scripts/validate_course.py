#!/usr/bin/env python3
"""Check a preceptor course before it is built or shipped. Standard library only. Changes nothing.

Usage:
  python validate_course.py COURSE [--json]
  python validate_course.py --compare OLD NEW [--json]
  python validate_course.py --selftest [--json]

COURSE, OLD and NEW are each either a course JSON file or a built course page (.html). In a page,
the course is read from between the "COURSE DATA: BEGIN" and "COURSE DATA: END" markers.
The data format is documented in references/data-format.md.

What it enforces (ERROR, exit 1):
  - structure: a usable id and version; every id unique across the course
  - the prerequisite graph: no prerequisite naming an unknown module, no cycle, no module that can
    never be reached from a starting module, no written module waiting on a planned one
  - mastery wiring: every objective has at least one gate item; every gate item maps to an
    objective of its own module; practice items map to an objective of the module or of a
    module it depends on
  - items: exactly one correct option, at least three options, an explanation on every option,
    "correct" given as true or false (not text, not 1), no duplicate option text
  - worked examples: all three levels present (full, partial, independent); the partial level has
    at least one blank; the independent level has answers and a solution
  - a module marked "ready" has every required part filled: title, summary, objectives, theory for
    every objective, worked example, practice, gate, cheat sheet, cards
  - a planned module carries no content parts
  - cards: neither side empty
  - visuals: known type, required fields, and every formula parses, uses only declared variables
    and allowed functions, and has a value at the default settings
  - placeholder text ("lorem ipsum", "TODO", "TBD", "content goes here", "coming soon",
    "to be written") anywhere in a written module
What it reports for a person to decide (ADVISORY):
  - the correct answer clustering in one position; a run of four items with the same position
  - the correct option much longer than the others; one option much longer than the rest
  - a written module with no visual; more than 12 new terms in one module
  - fewer than 6 practice items or 8 cards in a module (not for the "demo" size)
  - fewer than 2 gate items on an objective
  - a module listed before one of its prerequisites; a module count outside the declared size
  - a custom visual whose renderer could not be confirmed (JSON input has no renderer block)
  - answers containing digits that carry no "check" field, so no verifier can recompute them
  - em or en dashes in course text
--compare reports ids that exist in OLD and not in NEW, or that moved to another module (saved
progress for them would be orphaned), and ids kept with changed wording (possibly re-purposed).
A removed or moved id is an ERROR when the version number was not raised, and an ADVISORY when it
was, because the course page then reports the unmatched entries itself on import.

--selftest plants each fault above, one at a time, in a small made-up course and confirms the
validator reports it, with the valid neighbours beside the refusals (a pass mark of 50 and of 100
accepted, 49 and 101 refused; twelve terms quiet, thirteen noted).

What it cannot tell: whether the content is correct, well taught or well ordered. A clean result
means the course is wired so the engine can run it. Read the built course.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import json
import math
import re
import sys
from pathlib import Path

FLAGS = {"--json", "--compare", "--selftest"}
SIZES = {"demo": (1, 3), "primer": (4, 6), "course": (10, 14), "full": (24, 30)}
BLOOM = {"remember", "understand", "apply", "analyse", "analyze", "evaluate", "create"}
BLOCKS = {"p", "list", "steps", "note", "code", "table"}
VISUALS = {"steps", "slider", "compare", "number-line", "table-builder", "custom"}
FORMATS = {"int", "fixed1", "fixed2", "bin8", "bin"}
CONTENT_PARTS = ("objectives", "theory", "visuals", "worked", "quiz", "gate", "cheatsheet", "cards", "challenge", "terms")
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PLACEHOLDER = re.compile(r"lorem ipsum|\bTODO\b|\bTBD\b|content goes here|coming soon|to be written", re.I)
DASHES = (chr(0x2014), chr(0x2013))
DATA_RE = re.compile(r"/\* === COURSE DATA: BEGIN[^\n]*\*/\s*const COURSE\s*=\s*(.*?);\s*/\* === COURSE DATA: END === \*/", re.S)
RENDER_RE = re.compile(r"/\* === CUSTOM RENDERERS: BEGIN[^\n]*\*/(.*?)/\* === CUSTOM RENDERERS: END === \*/", re.S)


class InputError(Exception):
    pass


# ---------- the formula language of visuals: the same grammar as the engine's ----------
class FormulaError(Exception):
    pass


FUNCS = {
    "floor": (1, lambda a: float(math.floor(a))),
    "ceil": (1, lambda a: float(math.ceil(a))),
    "round": (1, lambda a: float(math.floor(a + 0.5))),
    "abs": (1, abs),
    "sqrt": (1, lambda a: math.sqrt(a) if a >= 0 else float("nan")),
    "log2": (1, lambda a: math.log2(a) if a > 0 else float("nan")),
    "min": (2, min),
    "max": (2, max),
    "mod": (2, lambda a, b: a - b * math.floor(a / b) if b != 0 else float("nan")),
    "band": (2, lambda a, b: float(int(a) & int(b)) if (a >= 0 and b >= 0 and a == int(a) and b == int(b) and a <= 4294967295 and b <= 4294967295) else float("nan")),
}
TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|([-+*/^(),]))")


def formula_compile(src):
    """Parse a formula. Returns (tree, variable names). Raises FormulaError with a reason."""
    if not isinstance(src, str):
        raise FormulaError("a formula must be text")
    toks, pos = [], 0
    while pos < len(src):
        if src[pos:].strip() == "":
            break
        m = TOKEN.match(src, pos)
        if not m:
            bad = src[pos:].lstrip()[:1]
            raise FormulaError('disallowed character "%s"' % bad)
        if m.group(1) is not None:
            toks.append(("num", float(m.group(1))))
        elif m.group(2) is not None:
            toks.append(("id", m.group(2)))
        else:
            toks.append((m.group(3), None))
        pos = m.end()
    if not toks:
        raise FormulaError("the formula is empty")
    names, i = [], [0]

    def peek():
        return toks[i[0]][0] if i[0] < len(toks) else None

    def expr():
        left = term()
        while peek() in ("+", "-"):
            op = toks[i[0]][0]
            i[0] += 1
            left = ("bin", op, left, term())
        return left

    def term():
        left = unary()
        while peek() in ("*", "/"):
            op = toks[i[0]][0]
            i[0] += 1
            left = ("bin", op, left, unary())
        return left

    def unary():
        if peek() == "-":
            i[0] += 1
            return ("neg", unary())
        return power()

    def power():
        base = primary()
        if peek() == "^":
            i[0] += 1
            return ("bin", "^", base, unary())
        return base

    def primary():
        if i[0] >= len(toks):
            raise FormulaError("the formula ends where a value was expected")
        kind, val = toks[i[0]]
        if kind == "num":
            i[0] += 1
            return ("num", val)
        if kind == "id":
            i[0] += 1
            if peek() == "(":
                i[0] += 1
                if val not in FUNCS:
                    raise FormulaError('unknown function "%s"' % val)
                args = []
                if peek() != ")":
                    args.append(expr())
                    while peek() == ",":
                        i[0] += 1
                        args.append(expr())
                if peek() != ")":
                    raise FormulaError('missing ")" after the arguments of %s' % val)
                i[0] += 1
                if len(args) != FUNCS[val][0]:
                    raise FormulaError("%s takes %d argument(s), not %d" % (val, FUNCS[val][0], len(args)))
                return ("call", val, args)
            if val in FUNCS:
                raise FormulaError('"%s" is a function and needs arguments in brackets' % val)
            if val not in names:
                names.append(val)
            return ("var", val)
        if kind == "(":
            i[0] += 1
            inner = expr()
            if peek() != ")":
                raise FormulaError('missing ")"')
            i[0] += 1
            return inner
        raise FormulaError('unexpected "%s"' % kind)

    tree = expr()
    if i[0] < len(toks):
        kind, val = toks[i[0]]
        raise FormulaError('unexpected "%s" after the end of the formula' % (val if kind in ("num", "id") else kind))
    return tree, names


def _ev(node, env):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "var":
        v = env.get(node[1])
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else float("nan")
    if kind == "neg":
        return -_ev(node[1], env)
    if kind == "call":
        args = [_ev(a, env) for a in node[2]]
        if any(math.isnan(a) or math.isinf(a) for a in args):
            return float("nan")
        return float(FUNCS[node[1]][1](*args))
    a, b = _ev(node[2], env), _ev(node[3], env)
    op = node[1]
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b if b != 0 else float("nan")
    try:
        r = math.pow(a, b)
    except (OverflowError, ValueError):
        return float("nan")
    return r


def formula_eval(src, env):
    """Value of a formula for the given variables, or None when it has no value."""
    try:
        tree, _ = formula_compile(src)
        v = _ev(tree, env)
    except (FormulaError, OverflowError, ValueError, ZeroDivisionError):
        return None
    return v if isinstance(v, float) and math.isfinite(v) else None


def format_value(v, fmt):
    """The engine's display of a computed value, reproduced exactly."""
    if v is None or not math.isfinite(v):
        return "no value"
    if fmt in ("fixed1", "fixed2"):
        d = 1 if fmt == "fixed1" else 2
        scale = 10 ** d
        r = int(math.floor(abs(v) * scale + 0.5 + 1e-9))
        s = "%d.%0*d" % (r // scale, d, r % scale)
        return ("-" if (v < 0 and r != 0) else "") + s
    r = int(math.floor(v + 0.5 + 1e-9))
    if fmt in ("bin8", "bin"):
        if r < 0 or r > 4294967295:
            return "no value"
        bits = format(r, "b")
        return bits.rjust(8, "0") if fmt == "bin8" else bits
    return str(r)


# ---------- reading ----------
def _no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise InputError('the same key "%s" appears twice in one object' % k)
        seen[k] = v
    return seen


def _no_constants(name):
    raise InputError("%s is not allowed in course data" % name)


def read_course(path):
    """Return (course, renderer_block_or_None). Raises InputError."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise InputError("cannot read %s: %s" % (path, e.strerror or e))
    if b"\x00" in raw:
        raise InputError("%s contains NUL bytes; it is not a text file" % path)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError("%s is not valid UTF-8" % path)
    renderers = None
    if not text.lstrip().startswith("{"):
        m = DATA_RE.search(text)
        if not m:
            raise InputError("%s is neither a JSON object nor a course page with the COURSE DATA markers" % path)
        if len(DATA_RE.findall(text)) != 1:
            raise InputError("%s has more than one COURSE DATA block" % path)
        r = RENDER_RE.search(text)
        renderers = r.group(1) if r else ""
        text = m.group(1)
    try:
        course = json.loads(text, object_pairs_hook=_no_dupes, parse_constant=_no_constants)
    except InputError:
        raise
    except ValueError as e:
        raise InputError("the course data in %s is not strict JSON (%s)" % (path, str(e)[:90]))
    if not isinstance(course, dict):
        raise InputError("the course data in %s must be one JSON object" % path)
    return course, renderers


# ---------- helpers ----------
def is_text(v, n=1):
    return isinstance(v, str) and len(v.strip()) >= n


def is_num(v):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return False
    try:
        return math.isfinite(v)
    except OverflowError:
        return False


def is_whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def strings_in(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            for s in strings_in(v):
                yield s
    elif isinstance(node, list):
        for v in node:
            for s in strings_in(v):
                yield s


class Report:
    def __init__(self):
        self.errors, self.advisories = [], []

    def err(self, where, msg):
        self.errors.append("%s: %s" % (where, msg) if where else msg)

    def adv(self, where, msg):
        self.advisories.append("%s: %s" % (where, msg) if where else msg)


def check_formula(rep, where, src, allowed, env=None, need_value=True):
    try:
        _, names = formula_compile(src)
    except FormulaError as e:
        rep.err(where, 'formula "%s" is refused: %s' % (str(src)[:60], e))
        return False
    unknown = [n for n in names if n not in allowed]
    if unknown:
        rep.err(where, 'formula "%s" uses unknown variable%s %s (declared: %s)' % (src, "s" if len(unknown) > 1 else "", ", ".join(unknown), ", ".join(sorted(allowed)) or "none"))
        return False
    if env is not None and need_value and formula_eval(src, env) is None:
        rep.err(where, 'formula "%s" has no value at the default settings' % src)
        return False
    return True


def check_blocks(rep, where, blocks):
    if not isinstance(blocks, list) or not blocks:
        rep.err(where, "has no content blocks")
        return
    for i, b in enumerate(blocks):
        w = "%s block %d" % (where, i + 1)
        if not isinstance(b, dict) or b.get("type") not in BLOCKS:
            rep.err(w, "unknown block type %r (allowed: %s)" % (b.get("type") if isinstance(b, dict) else b, ", ".join(sorted(BLOCKS))))
            continue
        t = b["type"]
        if t in ("p", "code", "note") and not is_text(b.get("text")):
            rep.err(w, "a %s block with no text" % t)
        if t in ("list", "steps") and not (isinstance(b.get("items"), list) and b["items"] and all(is_text(x) for x in b["items"])):
            rep.err(w, "a %s block needs a non-empty list of text items" % t)
        if t == "table":
            head, rows = b.get("head"), b.get("rows")
            if not (isinstance(head, list) and head and all(is_text(h) for h in head)):
                rep.err(w, "a table needs a head row of text")
            elif not (isinstance(rows, list) and rows and all(isinstance(r, list) and len(r) == len(head) and all(isinstance(c, str) for c in r) for r in rows)):
                rep.err(w, "every table row must be a list of %d text cells" % len(head))


def check_item(rep, where, item, allowed_objectives, kind):
    """A multiple-choice item. Returns the position of the correct option, or None."""
    if not is_text(item.get("stem"), 5):
        rep.err(where, "has no stem")
    if item.get("objective") not in allowed_objectives:
        if kind == "gate":
            rep.err(where, "gate item is mapped to %r, which is not an objective of this module" % item.get("objective"))
        else:
            rep.err(where, "practice item is mapped to %r, which is not an objective of this module or of one it depends on" % item.get("objective"))
    opts = item.get("options")
    if not isinstance(opts, list) or len(opts) < 3:
        rep.err(where, "needs at least three options")
        return None
    correct, texts = [], []
    for i, o in enumerate(opts):
        w = "%s option %d" % (where, i + 1)
        if not isinstance(o, dict):
            rep.err(w, "is not an object")
            continue
        if not is_text(o.get("text")):
            rep.err(w, "has no text")
        else:
            texts.append(o["text"].strip().lower())
            if re.search(r"\b(all|none) of the above\b", o["text"], re.I):
                rep.err(w, '"all of the above" and "none of the above" are not allowed')
        if not isinstance(o.get("correct"), bool):
            rep.err(w, '"correct" must be true or false (found %r)' % (o.get("correct"),))
        elif o["correct"]:
            correct.append(i)
        if not is_text(o.get("why"), 8):
            rep.err(w, "has no explanation: every option must say why it is right or wrong")
    if len(set(texts)) != len(texts):
        rep.err(where, "two options have the same text")
    if len(correct) == 0:
        rep.err(where, "no option is marked correct")
    elif len(correct) > 1:
        rep.err(where, "%d options are marked correct; exactly one is expected" % len(correct))
    if len(correct) == 1 and all(isinstance(o, dict) and is_text(o.get("text")) for o in opts):
        lens = [len(o["text"]) for o in opts]
        others = [n for i, n in enumerate(lens) if i != correct[0]]
        if lens[correct[0]] > 1.6 * (sum(others) / len(others)) and lens[correct[0]] - max(others) >= 15:
            rep.adv(where, "the correct option is much longer than the others (%d characters against at most %d): length gives it away" % (lens[correct[0]], max(others)))
        else:
            srt = sorted(lens)
            if srt[-1] > 2.2 * srt[-2] and srt[-1] - srt[-2] >= 25:
                rep.adv(where, "one option is much longer than the rest (%d characters against %d)" % (srt[-1], srt[-2]))
    return correct[0] if len(correct) == 1 else None


def check_answer(rep, where, a, need_label=True):
    if not isinstance(a, dict) or not is_text(a.get("answer")):
        rep.err(where, "has no answer")
        return
    if need_label and not is_text(a.get("label")):
        rep.err(where, "has no label for its input")
    if "accept" in a and not (isinstance(a["accept"], list) and all(isinstance(x, str) for x in a["accept"])):
        rep.err(where, '"accept" must be a list of text')


def check_steps_list(rep, where, steps):
    if not isinstance(steps, list) or not steps:
        rep.err(where, "has no steps")
        return 0
    blanks = 0
    for i, s in enumerate(steps):
        w = "%s step %d" % (where, i + 1)
        if not isinstance(s, dict) or not is_text(s.get("text")):
            rep.err(w, "has no text")
            continue
        if "blank" in s:
            blanks += 1
            check_answer(rep, w + " blank", s["blank"])
            if "result" in s:
                rep.err(w, "has both a blank and a printed result, which gives the answer away")
        elif "result" in s and not isinstance(s["result"], str):
            rep.err(w, "result must be text")
    return blanks


def check_visual(rep, where, v, objectives, renderers):
    if not isinstance(v, dict) or v.get("type") not in VISUALS:
        rep.err(where, "unknown visual type %r (allowed: %s)" % (v.get("type") if isinstance(v, dict) else v, ", ".join(sorted(VISUALS))))
        return
    t = v["type"]
    if not is_text(v.get("title")):
        rep.err(where, "has no title")
    if not is_text(v.get("caption"), 10):
        rep.err(where, "has no caption saying what to notice; a visual must carry meaning")
    if v.get("objective") not in objectives:
        rep.err(where, "is mapped to %r, which is not an objective of this module" % v.get("objective"))

    def outputs(key, allowed, env):
        outs = v.get(key)
        if not isinstance(outs, list) or not outs:
            rep.err(where, '"%s" must be a non-empty list' % key)
            return
        for i, o in enumerate(outs):
            w = "%s %s %d" % (where, key, i + 1)
            if not isinstance(o, dict) or not is_text(o.get("label")):
                rep.err(w, "has no label")
                continue
            if o.get("format", "int") not in FORMATS:
                rep.err(w, "unknown format %r (allowed: %s)" % (o.get("format"), ", ".join(sorted(FORMATS))))
            if isinstance(o.get("parts"), list) and o["parts"]:
                for f in o["parts"]:
                    check_formula(rep, w, f, allowed, env)
            elif "formula" in o:
                check_formula(rep, w, o["formula"], allowed, env)
            else:
                rep.err(w, "needs a formula or a list of parts")
            if "bar_max" in o:
                check_formula(rep, w, o["bar_max"], allowed, env)

    if t == "steps":
        steps = v.get("steps")
        if not isinstance(steps, list) or len(steps) < 2 or not all(isinstance(s, dict) and is_text(s.get("caption")) for s in steps):
            rep.err(where, "needs at least two steps, each with a caption")
            return
        n = len(steps)
        rows, nodes = v.get("rows"), v.get("nodes")
        if isinstance(rows, list) and rows:
            for i, r in enumerate(rows):
                if not isinstance(r, dict) or not is_text(r.get("label")) or not (isinstance(r.get("cells"), list) and r["cells"] and all(isinstance(c, str) for c in r["cells"])):
                    rep.err("%s row %d" % (where, i + 1), "needs a label and a list of text cells")
                elif "show_at" in r and not (is_whole(r["show_at"]) and 1 <= r["show_at"] <= n):
                    rep.err("%s row %d" % (where, i + 1), "show_at must be a whole number from 1 to %d" % n)
                elif "cells_at" in r and not (isinstance(r["cells_at"], list) and len(r["cells_at"]) == len(r["cells"]) and all(is_whole(x) and 1 <= x <= n for x in r["cells_at"])):
                    rep.err("%s row %d" % (where, i + 1), "cells_at must give one step number from 1 to %d for each cell" % n)
            for i, s in enumerate(steps):
                for pair in s.get("highlight", []):
                    ok = (isinstance(pair, list) and len(pair) == 2 and all(is_whole(x) for x in pair) and 0 <= pair[0] < len(rows)
                          and isinstance(rows[pair[0]], dict) and isinstance(rows[pair[0]].get("cells"), list) and 0 <= pair[1] < len(rows[pair[0]]["cells"]))
                    if not ok:
                        rep.err("%s step %d" % (where, i + 1), "highlight %r points outside the grid" % (pair,))
        elif isinstance(nodes, list) and nodes:
            for i, nd in enumerate(nodes):
                if not isinstance(nd, dict) or not is_text(nd.get("label")):
                    rep.err("%s node %d" % (where, i + 1), "has no label")
                elif "show_at" in nd and not (is_whole(nd["show_at"]) and 1 <= nd["show_at"] <= n):
                    rep.err("%s node %d" % (where, i + 1), "show_at must be a whole number from 1 to %d" % n)
            if not any("show_at" in nd for nd in nodes if isinstance(nd, dict)) and len(nodes) != n:
                rep.err(where, "has %d nodes and %d steps; without show_at they must match one to one" % (len(nodes), n))
        else:
            rep.err(where, "needs rows (a labelled grid) or nodes (a flow)")
    elif t == "slider":
        params = v.get("params")
        if not isinstance(params, list) or not 1 <= len(params) <= 2:
            rep.err(where, "needs one or two params")
            return
        env, bad = {}, False
        for i, p in enumerate(params):
            w = "%s param %d" % (where, i + 1)
            if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not NAME_RE.fullmatch(p["name"]) or p["name"] in FUNCS:
                rep.err(w, "needs a name that is a plain identifier and not a function name")
                bad = True
                continue
            if not is_text(p.get("label")):
                rep.err(w, "has no label")
            if not all(is_num(p.get(k)) for k in ("min", "max", "value")) or not p["min"] < p["max"] or not p["min"] <= p["value"] <= p["max"]:
                rep.err(w, "needs numbers with min below max and the starting value between them")
                bad = True
                continue
            if "step" in p and not (is_num(p["step"]) and p["step"] > 0):
                rep.err(w, "step must be a positive number")
            env[p["name"]] = p["value"]
        if bad:
            return
        outputs("outputs", set(env), env)
        strip = v.get("strip")
        if strip is not None:
            if not isinstance(strip, dict) or not (is_whole(strip.get("cells")) and 1 <= strip["cells"] <= 64):
                rep.err(where, "strip needs a whole number of cells from 1 to 64")
            elif not isinstance(strip.get("regions"), list) or not 1 <= len(strip["regions"]) <= 3:
                rep.err(where, "strip needs one to three regions")
            else:
                for i, rg in enumerate(strip["regions"]):
                    w = "%s strip region %d" % (where, i + 1)
                    if not isinstance(rg, dict) or not is_text(rg.get("label")):
                        rep.err(w, "has no label")
                    else:
                        check_formula(rep, w, rg.get("upto"), set(env), env)
    elif t == "compare":
        states = v.get("states")
        if not isinstance(states, list) or len(states) != 2:
            rep.err(where, "needs exactly two states")
            return
        for i, s in enumerate(states):
            w = "%s state %d" % (where, i + 1)
            if not isinstance(s, dict) or not is_text(s.get("name")):
                rep.err(w, "has no name")
                continue
            facts, segs = s.get("facts", []), s.get("segments", [])
            if not (isinstance(facts, list) and all(isinstance(f, dict) and is_text(f.get("label")) and is_text(f.get("value")) for f in facts)):
                rep.err(w, "facts must each have a label and a text value")
            if not (isinstance(segs, list) and all(isinstance(g, dict) and is_text(g.get("label")) and is_num(g.get("size")) and g["size"] > 0 for g in segs)):
                rep.err(w, "segments must each have a label and a positive size")
            if not facts and not segs:
                rep.err(w, "shows nothing: give facts, segments or both")
    elif t == "number-line":
        p = v.get("point")
        if not (is_num(v.get("min")) and is_num(v.get("max")) and v["min"] < v["max"]):
            rep.err(where, "needs min below max")
            return
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not NAME_RE.fullmatch(p["name"]) or p["name"] in FUNCS or not is_text(p.get("label")) or not is_num(p.get("value")):
            rep.err(where, "point needs a name, a label and a starting value")
            return
        top = p.get("max", v["max"])
        if not is_num(top) or not v["min"] <= p["value"] <= top <= v["max"]:
            rep.err(where, "the point's starting value and max must lie on the line")
        env = {p["name"]: p["value"]}
        ch = v.get("choice")
        if ch is not None:
            ok = (isinstance(ch, dict) and isinstance(ch.get("name"), str) and NAME_RE.fullmatch(ch["name"]) and ch["name"] not in FUNCS and ch["name"] != p["name"]
                  and is_text(ch.get("label")) and isinstance(ch.get("options"), list) and len(ch["options"]) >= 2
                  and all(isinstance(o, dict) and is_text(o.get("label")) and is_num(o.get("value")) for o in ch["options"]))
            if not ok:
                rep.err(where, "choice needs a name, a label and at least two options with a label and a number")
                return
            if ch.get("value") not in [o["value"] for o in ch["options"]]:
                rep.err(where, "the choice's starting value is not one of its options")
                return
            env[ch["name"]] = ch["value"]
        if "segment_size" in v:
            if check_formula(rep, where + " segment_size", v["segment_size"], set(env), env):
                size = formula_eval(v["segment_size"], env)
                if size is not None and size <= 0:
                    rep.err(where, "segment_size must be positive")
        outputs("readouts", set(env), env)
    elif t == "table-builder":
        cols, rows = v.get("columns"), v.get("rows")
        if not isinstance(cols, list) or len(cols) < 2 or not all(isinstance(c, dict) and isinstance(c.get("key"), str) and NAME_RE.fullmatch(c["key"]) and c["key"] not in FUNCS and is_text(c.get("label")) for c in cols):
            rep.err(where, "needs at least two columns, each with an identifier key and a label")
            return
        keys = [c["key"] for c in cols]
        if len(set(keys)) != len(keys):
            rep.err(where, "two columns share a key")
            return
        given = [c["key"] for c in cols if c.get("given") is True]
        computed = [c for c in cols if c.get("given") is not True]
        if not given or not computed:
            rep.err(where, "needs at least one given column and one column for the learner to fill")
            return
        if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) and all(is_num(r.get(k)) for k in given) for r in rows):
            rep.err(where, "every row needs a number for each given column (%s)" % ", ".join(given))
            return
        for c in computed:
            w = '%s column "%s"' % (where, c["key"])
            if c.get("format", "int") not in FORMATS:
                rep.err(w, "unknown format %r" % (c.get("format"),))
            if "formula" not in c:
                rep.err(w, "a column the learner fills needs a formula for its answers")
                continue
            if check_formula(rep, w, c["formula"], set(given)):
                for i, r in enumerate(rows):
                    if formula_eval(c["formula"], r) is None:
                        rep.err(w, "has no value in row %d" % (i + 1))
    elif t == "custom":
        name = v.get("renderer")
        if not is_text(name):
            rep.err(where, "a custom visual must name its renderer")
        elif renderers is None:
            rep.adv(where, 'needs a renderer named "%s"; a JSON file carries no renderer block, so check the built page' % name)
        elif not re.search(r"""(?:["']%s["']|(?<![\w$])%s)\s*:\s*function""" % (re.escape(name), re.escape(name)), renderers):
            rep.err(where, 'needs a renderer named "%s", which the CUSTOM RENDERERS block does not define' % name)
        if "data" in v and not isinstance(v["data"], dict):
            rep.err(where, '"data" must be an object')


def has_digit_answer(text):
    return isinstance(text, str) and re.search(r"\d", text) is not None


def validate(course, renderers):
    rep = Report()
    stats = {"modules_ready": 0, "modules_planned": 0, "objectives": 0, "practice_items": 0, "gate_items": 0, "cards": 0, "visuals": 0,
             "worked_examples": 0, "checks": 0, "numeric_answers_without_check": 0}
    if not isinstance(course.get("id"), str) or not ID_RE.fullmatch(course["id"]):
        rep.err("course", "id must be lower-case letters, digits and hyphens (found %r)" % (course.get("id"),))
    if not is_whole(course.get("version")) or course["version"] < 1:
        rep.err("course", "version must be a whole number, 1 or more (found %r)" % (course.get("version"),))
    if not is_text(course.get("title")):
        rep.err("course", "has no title")
    size = course.get("size")
    if not isinstance(size, str) or size not in SIZES:
        rep.err("course", "size must be one of %s (found %r)" % (", ".join(SIZES), size))
    elif not is_text(course.get("size_reason"), 10):
        rep.err("course", "size_reason must say in one line why this size was chosen")
    if "gate_threshold" in course and not (is_whole(course["gate_threshold"]) and 50 <= course["gate_threshold"] <= 100):
        rep.err("course", "gate_threshold must be a whole number of percent from 50 to 100")
    if "check_after_days" in course and not (is_whole(course["check_after_days"]) and course["check_after_days"] >= 1):
        rep.err("course", "check_after_days must be a whole number of days, 1 or more")
    mods = course.get("modules")
    if not isinstance(mods, list) or not mods:
        rep.err("course", "has no modules")
        return rep, stats
    ids, mod_ids = {}, []

    def claim(kind, value, where):
        if not isinstance(value, str) or not ID_RE.fullmatch(value):
            rep.err(where, "%s id must be lower-case letters, digits and hyphens (found %r)" % (kind, value))
            return
        if value in ids:
            rep.err(where, 'duplicate id "%s" (already used by %s)' % (value, ids[value]))
        else:
            ids[value] = where

    for i, m in enumerate(mods):
        if not isinstance(m, dict):
            rep.err("module %d" % (i + 1), "is not an object")
            mods[i] = m = {}
        claim("module", m.get("id"), "module %d" % (i + 1))
        mod_ids.append(m.get("id") if isinstance(m.get("id"), str) else "?%d" % i)
    by_id = {mid: m for mid, m in zip(mod_ids, mods)}
    # ---------- the graph ----------
    for mid, m in zip(mod_ids, mods):
        pre = m.get("prereqs", [])
        if not isinstance(pre, list) or not all(isinstance(p, str) for p in pre):
            rep.err("module %s" % mid, "prereqs must be a list of module ids")
            m["prereqs"] = []
            continue
        for p in pre:
            if p not in by_id:
                rep.err("module %s" % mid, 'prerequisite "%s" is not a module in this course' % p)
            elif p == mid:
                rep.err("module %s" % mid, "lists itself as a prerequisite")
        if len(set(pre)) != len(pre):
            rep.err("module %s" % mid, "lists a prerequisite twice")
        if m.get("status") not in ("ready", "planned"):
            rep.err("module %s" % mid, 'status must be "ready" or "planned" (found %r)' % (m.get("status"),))
    colour, cycles = {}, []

    def visit(mid, trail):
        if colour.get(mid) == 2:
            return
        if colour.get(mid) == 1:
            cyc = trail[trail.index(mid):] + [mid]
            if not any(set(cyc) == set(c) for c in cycles):
                cycles.append(cyc)
            return
        colour[mid] = 1
        for p in by_id[mid].get("prereqs", []):
            if p in by_id and p != mid:
                visit(p, trail + [mid])
        colour[mid] = 2

    for mid in mod_ids:
        visit(mid, [])
    for cyc in cycles:
        rep.err("graph", "the prerequisites form a cycle: " + " needs ".join(cyc))
    reach, grew = set(), True
    while grew:
        grew = False
        for mid in mod_ids:
            pre = by_id[mid].get("prereqs", [])
            if mid not in reach and all(p in reach for p in pre) and all(p in by_id for p in pre):
                reach.add(mid)
                grew = True
    if not any(not by_id[mid].get("prereqs") for mid in mod_ids):
        rep.err("graph", "no module is a starting point: every module has a prerequisite")
    for mid in mod_ids:
        if mid not in reach:
            rep.err("module %s" % mid, "can never be reached from a starting module")
    open_set, grew = set(), True
    while grew:
        grew = False
        for mid in mod_ids:
            if mid not in open_set and mid in reach and by_id[mid].get("status") == "ready" and all(p in open_set for p in by_id[mid].get("prereqs", [])):
                open_set.add(mid)
                grew = True
    for mid in mod_ids:
        if by_id[mid].get("status") == "ready" and mid in reach and mid not in open_set:
            blockers = [p for p in by_id[mid].get("prereqs", []) if p not in open_set]
            rep.err("module %s" % mid, "is written but can never open, because it waits on a module that is planned or blocked (%s)" % ", ".join(blockers))
    seen_order = set()
    for mid in mod_ids:
        late = [p for p in by_id[mid].get("prereqs", []) if p in by_id and p not in seen_order and p != mid]
        if late and not cycles:
            rep.adv("module %s" % mid, "is listed before its prerequisite %s; list modules in an order a learner could follow" % ", ".join(late))
        seen_order.add(mid)

    def ancestors(mid, acc):
        for p in by_id[mid].get("prereqs", []):
            if p in by_id and p not in acc:
                acc.add(p)
                ancestors(p, acc)
        return acc

    # ---------- module contents ----------
    positions = []
    for mid, m in zip(mod_ids, mods):
        w = "module %s" % mid
        if not is_text(m.get("title")):
            rep.err(w, "has no title")
        if m.get("status") == "planned":
            stats["modules_planned"] += 1
            filled = [k for k in CONTENT_PARTS if m.get(k)]
            if filled:
                rep.err(w, "is marked planned but carries content (%s). A planned module is never shown, so either finish it and mark it ready or remove the parts" % ", ".join(filled))
            continue
        if m.get("status") != "ready":
            continue
        stats["modules_ready"] += 1
        if not is_text(m.get("summary"), 10):
            rep.err(w, "is marked ready with no summary")
        for s in strings_in(m):
            hit = PLACEHOLDER.search(s)
            if hit:
                rep.err(w, 'contains placeholder text ("%s") in "%s"' % (hit.group(0), s.strip()[:50]))
            if any(d in s for d in DASHES):
                rep.adv(w, 'contains an em or en dash in "%s"' % s.strip()[:40].encode("ascii", "replace").decode("ascii"))
        objs = m.get("objectives")
        own = []
        if not isinstance(objs, list) or not objs:
            rep.err(w, "is marked ready with no objectives")
            objs = []
        for i, o in enumerate(objs):
            ow = "%s objective %d" % (w, i + 1)
            if not isinstance(o, dict):
                rep.err(ow, "is not an object")
                continue
            claim("objective", o.get("id"), ow)
            if isinstance(o.get("id"), str):
                own.append(o["id"])
            if not is_text(o.get("text"), 10):
                rep.err(ow, "has no text")
            if not isinstance(o.get("bloom"), str) or o.get("bloom") not in BLOOM:
                rep.err(ow, "bloom must be one of remember, understand, apply, analyse, evaluate, create (found %r)" % (o.get("bloom"),))
        stats["objectives"] += len(own)
        anc = ancestors(mid, set()) if not cycles else set()
        wider = set(own)
        for a in anc:
            for o in by_id[a].get("objectives", []) or []:
                if isinstance(o, dict) and isinstance(o.get("id"), str):
                    wider.add(o["id"])
        # terms
        terms = m.get("terms", [])
        if not (isinstance(terms, list) and all(isinstance(t, dict) and is_text(t.get("term")) and is_text(t.get("definition"), 5) for t in terms)):
            rep.err(w, "terms must each have a term and a definition")
        elif len(terms) > 12:
            rep.adv(w, "defines %d new terms; more than about 12 in one module is a heavy load. Consider splitting it" % len(terms))
        # theory
        theory = m.get("theory")
        covered = set()
        if not isinstance(theory, list) or not theory:
            rep.err(w, "is marked ready with no theory")
            theory = []
        for i, sec in enumerate(theory):
            sw = "%s theory section %d" % (w, i + 1)
            if not isinstance(sec, dict) or not is_text(sec.get("heading")):
                rep.err(sw, "has no heading")
                continue
            if sec.get("objective") not in own:
                rep.err(sw, "is mapped to %r, which is not an objective of this module" % (sec.get("objective"),))
            covered.add(sec.get("objective"))
            check_blocks(rep, sw, sec.get("blocks"))
        for oid in own:
            if oid not in covered:
                rep.err(w, 'objective "%s" has no theory section, so a failed gate would have nowhere to send the learner' % oid)
        # visuals
        visuals = m.get("visuals", [])
        if not isinstance(visuals, list):
            rep.err(w, "visuals must be a list")
            visuals = []
        if not visuals:
            rep.adv(w, "has no visual. Every module should have one that carries meaning")
        for i, v in enumerate(visuals):
            vw = "%s visual %d" % (w, i + 1)
            if isinstance(v, dict):
                claim("visual", v.get("id"), vw)
            check_visual(rep, vw, v, own, renderers)
        stats["visuals"] += len(visuals)
        # worked examples
        worked = m.get("worked")
        if not isinstance(worked, list) or not worked:
            rep.err(w, "is marked ready with no worked example")
            worked = []
        for i, ex in enumerate(worked):
            ew = "%s worked example %d" % (w, i + 1)
            if not isinstance(ex, dict):
                rep.err(ew, "is not an object")
                continue
            claim("worked example", ex.get("id"), ew)
            if not is_text(ex.get("title")):
                rep.err(ew, "has no title")
            if ex.get("objective") not in own:
                rep.err(ew, "is mapped to %r, which is not an objective of this module" % (ex.get("objective"),))
            missing = [lv for lv in ("full", "partial", "independent") if not isinstance(ex.get(lv), dict)]
            if missing:
                rep.err(ew, "is missing the %s level%s; a worked example must fade through full, partial and independent" % (" and ".join(missing), "s" if len(missing) > 1 else ""))
                continue
            for lv in ("full", "partial", "independent"):
                if not is_text(ex[lv].get("problem"), 8):
                    rep.err("%s %s level" % (ew, lv), "has no problem statement")
            if check_steps_list(rep, ew + " full level", ex["full"].get("steps")):
                rep.err(ew + " full level", "contains a blank; the full level shows every step")
            if check_steps_list(rep, ew + " partial level", ex["partial"].get("steps")) == 0 and isinstance(ex["partial"].get("steps"), list) and ex["partial"]["steps"]:
                rep.err(ew + " partial level", "has no blank for the learner to fill")
            ans = ex["independent"].get("answers")
            if not isinstance(ans, list) or not ans:
                rep.err(ew + " independent level", "has no answer for the learner to give")
            else:
                for j, a in enumerate(ans):
                    check_answer(rep, "%s independent level answer %d" % (ew, j + 1), a)
            if check_steps_list(rep, ew + " independent level solution", ex["independent"].get("solution")):
                rep.err(ew + " independent level solution", "contains a blank")
            if ex["full"].get("problem") == ex["partial"].get("problem") or ex["partial"].get("problem") == ex["independent"].get("problem"):
                rep.adv(ew, "two levels use the same problem; each level should be a fresh problem of the same kind")
        stats["worked_examples"] += len(worked)
        # practice and gate
        quiz = m.get("quiz")
        if not isinstance(quiz, list) or not quiz:
            rep.err(w, "is marked ready with no practice items")
            quiz = []
        gate = m.get("gate")
        gitems = gate.get("items") if isinstance(gate, dict) else None
        if not isinstance(gitems, list) or not gitems:
            rep.err(w, "is marked ready with no gate items")
            gitems = []
        per_obj = {oid: 0 for oid in own}
        local_pos = []
        for kind, items, allowed in (("practice", quiz, wider), ("gate", gitems, set(own))):
            for i, it in enumerate(items):
                iw = "%s %s item %d" % (w, kind, i + 1)
                if not isinstance(it, dict):
                    rep.err(iw, "is not an object")
                    continue
                claim("item", it.get("id"), iw)
                pos = check_item(rep, iw, it, allowed, kind)
                if pos is not None:
                    local_pos.append((pos, len(it["options"]), iw))
                if kind == "gate" and it.get("objective") in per_obj:
                    per_obj[it["objective"]] += 1
        for oid, n in per_obj.items():
            if n == 0:
                rep.err(w, 'objective "%s" has no gate item, so it could never be demonstrated' % oid)
            elif n == 1:
                rep.adv(w, 'objective "%s" has one gate item; with two or more, one slip does not decide it' % oid)
        stats["practice_items"] += len(quiz)
        stats["gate_items"] += len(gitems)
        positions.append((mid, local_pos))
        if size != "demo" and 0 < len(quiz) < 6:
            rep.adv(w, "has %d practice items; aim for at least 6" % len(quiz))
        # challenge
        ch = m.get("challenge")
        if ch is not None:
            cw = w + " challenge"
            if not isinstance(ch, dict) or not is_text(ch.get("title")):
                rep.err(cw, "has no title")
            else:
                if ch.get("objective") not in own:
                    rep.err(cw, "is mapped to %r, which is not an objective of this module" % (ch.get("objective"),))
                check_blocks(rep, cw + " brief", ch.get("brief"))
                tasks = ch.get("tasks")
                if not isinstance(tasks, list) or not tasks:
                    rep.err(cw, "has no tasks")
                else:
                    for j, a in enumerate(tasks):
                        check_answer(rep, "%s task %d" % (cw, j + 1), a)
                if check_steps_list(rep, cw + " solution", ch.get("solution")):
                    rep.err(cw + " solution", "contains a blank")
        # cheat sheet and cards
        if not isinstance(m.get("cheatsheet"), list) or not m["cheatsheet"]:
            rep.err(w, "is marked ready with no cheat sheet")
        else:
            check_blocks(rep, w + " cheat sheet", m["cheatsheet"])
        cards = m.get("cards")
        if not isinstance(cards, list) or not cards:
            rep.err(w, "is marked ready with no cards")
            cards = []
        for i, c in enumerate(cards):
            cw = "%s card %d" % (w, i + 1)
            if not isinstance(c, dict):
                rep.err(cw, "is not an object")
                continue
            claim("card", c.get("id"), cw)
            if not is_text(c.get("front")) or not is_text(c.get("back")):
                rep.err(cw, "has an empty side")
            if c.get("objective") not in own:
                rep.err(cw, "is mapped to %r, which is not an objective of this module" % (c.get("objective"),))
        stats["cards"] += len(cards)
        if size != "demo" and 0 < len(cards) < 8:
            rep.adv(w, "has %d cards; aim for at least 8" % len(cards))
        # machine-check coverage
        for holder, answer_text in _answers_of(m):
            cks = ([holder["check"]] if "check" in holder else []) + (holder["checks"] if isinstance(holder.get("checks"), list) else [])
            if cks:
                stats["checks"] += 1
                for ck in cks:
                    if not isinstance(ck, dict) or not is_text(ck.get("op")) or not isinstance(ck.get("args", []), list):
                        rep.err(w, 'a "check" needs an "op" and a list of "args" (found %r)' % (ck,))
            elif has_digit_answer(answer_text):
                stats["numeric_answers_without_check"] += 1
    # ---------- answer position ----------
    flat = [p for _, lp in positions for p in lp]
    if len(flat) >= 8:
        counts = {}
        for pos, _, _ in flat:
            counts[pos] = counts.get(pos, 0) + 1
        top = max(counts, key=lambda k: counts[k])
        if counts[top] * 100 > 45 * len(flat):
            rep.adv("course", "the correct answer is option %d in %d of %d items; spread the correct position" % (top + 1, counts[top], len(flat)))
    for mid, lp in positions:
        run = 1
        for a, b in zip(lp, lp[1:]):
            run = run + 1 if a[0] == b[0] else 1
            if run == 4:
                rep.adv("module %s" % mid, "four items in a row have the correct answer in position %d (ending at %s)" % (b[0] + 1, b[2].split(": ")[-1].replace("module %s " % mid, "")))
    n = len(mods)
    if isinstance(size, str) and size in SIZES and not SIZES[size][0] <= n <= SIZES[size][1]:
        rep.adv("course", 'declares size "%s" (%d to %d modules) but has %d' % (size, SIZES[size][0], SIZES[size][1], n))
    if stats["numeric_answers_without_check"]:
        rep.adv("course", "%d answer(s) containing digits carry no \"check\" field (%d do). Without one, no verifier can recompute them; confirm each by hand or add checks"
                % (stats["numeric_answers_without_check"], stats["checks"]))
    return rep, stats


def _answers_of(m):
    """Yield (holder, answer text) for every place a module states an answer."""
    for key in ("quiz",):
        for it in m.get(key) or []:
            if isinstance(it, dict):
                good = [o for o in it.get("options") or [] if isinstance(o, dict) and o.get("correct") is True]
                yield it, good[0].get("text") if good else None
    for it in (m.get("gate") or {}).get("items") or [] if isinstance(m.get("gate"), dict) else []:
        if isinstance(it, dict):
            good = [o for o in it.get("options") or [] if isinstance(o, dict) and o.get("correct") is True]
            yield it, good[0].get("text") if good else None
    for ex in m.get("worked") or []:
        if not isinstance(ex, dict):
            continue
        for lv in ("full", "partial"):
            for s in (ex.get(lv) or {}).get("steps") or [] if isinstance(ex.get(lv), dict) else []:
                if isinstance(s, dict):
                    if isinstance(s.get("blank"), dict):
                        yield s["blank"], s["blank"].get("answer")
                    elif "result" in s:
                        yield s, s.get("result")
        ind = ex.get("independent") if isinstance(ex.get("independent"), dict) else {}
        for a in ind.get("answers") or []:
            if isinstance(a, dict):
                yield a, a.get("answer")
        for s in ind.get("solution") or []:
            if isinstance(s, dict) and "result" in s:
                yield s, s.get("result")
    ch = m.get("challenge") if isinstance(m.get("challenge"), dict) else {}
    for a in ch.get("tasks") or []:
        if isinstance(a, dict):
            yield a, a.get("answer")
    for s in ch.get("solution") or []:
        if isinstance(s, dict) and "result" in s:
            yield s, s.get("result")
    for c in m.get("cards") or []:
        if isinstance(c, dict):
            yield c, c.get("back")


# ---------- compare two versions ----------
def id_index(course):
    out = {"module": {}, "objective": {}, "card": {}, "practice or gate item": {}, "worked example": {}}
    for m in course.get("modules") or []:
        if not isinstance(m, dict) or not isinstance(m.get("id"), str):
            continue
        out["module"][m["id"]] = (m["id"], m.get("title"))
        for o in m.get("objectives") or []:
            if isinstance(o, dict) and isinstance(o.get("id"), str):
                out["objective"][o["id"]] = (m["id"], o.get("text"))
        for c in m.get("cards") or []:
            if isinstance(c, dict) and isinstance(c.get("id"), str):
                out["card"][c["id"]] = (m["id"], c.get("front"))
        items = list(m.get("quiz") or []) + list((m.get("gate") or {}).get("items") or [] if isinstance(m.get("gate"), dict) else [])
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("id"), str):
                out["practice or gate item"][it["id"]] = (m["id"], it.get("stem"))
        for ex in m.get("worked") or []:
            if isinstance(ex, dict) and isinstance(ex.get("id"), str):
                out["worked example"][ex["id"]] = (m["id"], ex.get("title"))
    return out


def compare(old, new):
    rep = Report()
    if old.get("id") != new.get("id"):
        rep.err("course", "the two files are different courses (%r and %r); progress never carries between courses" % (old.get("id"), new.get("id")))
        return rep, {}
    vo, vn = old.get("version"), new.get("version")
    raised = is_whole(vo) and is_whole(vn) and vn > vo
    if is_whole(vo) and is_whole(vn) and vn < vo:
        rep.err("course", "NEW has version %d, lower than OLD's %d" % (vn, vo))
    a, b = id_index(old), id_index(new)
    counts = {"removed": 0, "moved": 0, "reworded": 0, "added": 0}
    for kind in a:
        for key, (mod, text) in sorted(a[kind].items()):
            if key not in b[kind]:
                counts["removed"] += 1
                msg = '%s "%s" was removed; saved progress for it would be orphaned' % (kind, key)
                (rep.adv if raised else rep.err)("compare", msg + ("" if raised else ". Raise the version number so the course page reports this on import"))
            else:
                mod2, text2 = b[kind][key]
                if mod2 != mod:
                    counts["moved"] += 1
                    msg = '%s "%s" moved from module "%s" to "%s"' % (kind, key, mod, mod2)
                    (rep.adv if raised else rep.err)("compare", msg + ("" if raised else ". Raise the version number"))
                if isinstance(text, str) and isinstance(text2, str) and text.strip() != text2.strip():
                    counts["reworded"] += 1
                    rep.adv("compare", '%s "%s" keeps its id with changed wording ("%s" became "%s"). If it now means something else, give it a new id so old progress is not credited to it'
                            % (kind, key, text.strip()[:40], text2.strip()[:40]))
        counts["added"] += len([k for k in b[kind] if k not in a[kind]])
    if not raised and vo == vn and json.dumps(old, sort_keys=True) != json.dumps(new, sort_keys=True):
        rep.adv("compare", "the content differs and the version number is the same (%r). Raise it whenever ids or wording change" % (vn,))
    return rep, counts


# ---------- self-test: every rule is shown to fail on a planted fault ----------
def _selftest_course():
    """A small valid course of made-up content. SYNTHETIC. Used only to plant faults in."""
    def item(iid, obj, right):
        opts = [{"text": "option %s %d" % (iid, k), "correct": k == right, "why": "Explanation for option %d of %s." % (k, iid)} for k in range(3)]
        return {"id": iid, "objective": obj, "stem": "SYNTHETIC stem for %s?" % iid, "options": opts}

    def module(mid, pre, shift):
        o1, o2 = mid + "-o1", mid + "-o2"
        return {
            "id": mid, "title": "SYNTHETIC " + mid, "summary": "Made-up module for the self-test.", "status": "ready", "prereqs": pre,
            "objectives": [{"id": o1, "text": "SYNTHETIC first objective of %s." % mid, "bloom": "apply"}, {"id": o2, "text": "SYNTHETIC second objective of %s." % mid, "bloom": "understand"}],
            "terms": [{"term": "term", "definition": "A made-up definition."}],
            "theory": [{"objective": o1, "heading": "One", "blocks": [{"type": "p", "text": "Made-up theory one."}]}, {"objective": o2, "heading": "Two", "blocks": [{"type": "p", "text": "Made-up theory two."}]}],
            "visuals": [{"type": "slider", "id": mid + "-v1", "title": "Made-up slider", "objective": o1, "caption": "A made-up slider that doubles x.",
                         "params": [{"name": "x", "label": "x", "min": 0, "max": 10, "step": 1, "value": 4}], "outputs": [{"label": "double", "formula": "x * 2", "format": "int"}]}],
            "worked": [{"id": mid + "-w1", "objective": o1, "title": "Made-up example",
                        "full": {"problem": "Double four in full.", "steps": [{"text": "Double it.", "result": "eight"}]},
                        "partial": {"problem": "Double five with a blank.", "steps": [{"text": "Double it.", "blank": {"label": "Double", "answer": "ten", "accept": [], "hint": "Add it to itself."}}]},
                        "independent": {"problem": "Double six alone.", "answers": [{"label": "Double", "answer": "twelve", "accept": []}], "solution": [{"text": "Double it.", "result": "twelve"}]}}],
            "quiz": [item(mid + "-q1", o1, (0 + shift) % 3), item(mid + "-q2", o2, (1 + shift) % 3)],
            "gate": {"items": [item(mid + "-g1", o1, (2 + shift) % 3), item(mid + "-g2", o1, (0 + shift) % 3), item(mid + "-g3", o2, (1 + shift) % 3), item(mid + "-g4", o2, (2 + shift) % 3)]},
            "cheatsheet": [{"type": "note", "label": "Rule", "text": "Double by adding a number to itself."}],
            "cards": [{"id": mid + "-c1", "objective": o1, "front": "Front one", "back": "Back one"}, {"id": mid + "-c2", "objective": o2, "front": "Front two", "back": "Back two"}],
        }
    return {"id": "selftest", "version": 1, "title": "SYNTHETIC self-test course", "size": "demo", "size_reason": "Two modules are enough to plant faults in.",
            "gate_threshold": 80, "check_after_days": 30, "modules": [module("a", [], 0), module("b", ["a"], 1)]}


def _planted():
    """(name, change, text expected among the errors). Each change is one fault in an otherwise valid course."""
    import copy

    def planned(c):
        c["modules"][0] = {"id": "a", "title": "SYNTHETIC a", "status": "planned", "prereqs": []}

    def side_cycle(c):
        x, y = copy.deepcopy(c["modules"][1]), copy.deepcopy(c["modules"][1])
        for m, mid, pre in ((x, "x", ["y"]), (y, "y", ["x"])):
            text = json.dumps(m).replace('"b', '"' + mid)
            m.clear()
            m.update(json.loads(text))
            m["prereqs"] = pre
        c["modules"] += [x, y]

    g = lambda c: c["modules"][0]["gate"]["items"]  # noqa: E731
    return [
        ("two modules with one id", lambda c: c["modules"][1].update(id="a"), "duplicate id"),
        ("an objective id used twice", lambda c: c["modules"][1]["objectives"][0].update(id="a-o1"), 'duplicate id "a-o1"'),
        ("a prerequisite naming no module", lambda c: c["modules"][1].update(prereqs=["zz"]), 'prerequisite "zz" is not a module'),
        ("a prerequisite cycle", lambda c: c["modules"][0].update(prereqs=["b"]), "form a cycle"),
        ("modules reachable from no starting module", side_cycle, "can never be reached from a starting module"),
        ("an objective with no gate item", lambda c: c["modules"][0]["gate"].update(items=g(c)[:2]), 'objective "a-o2" has no gate item'),
        ("a gate item mapped to no objective", lambda c: g(c)[0].update(objective="nothing"), "gate item is mapped to 'nothing'"),
        ("a gate item mapped to another module's objective", lambda c: c["modules"][1]["gate"]["items"][0].update(objective="a-o1"), "which is not an objective of this module"),
        ("an option with no explanation", lambda c: g(c)[0]["options"][1].update(why=""), "has no explanation"),
        ("an item with no correct option", lambda c: [o.update(correct=False) for o in g(c)[0]["options"]], "no option is marked correct"),
        ("an item with two correct options", lambda c: g(c)[0]["options"][0].update(correct=True), "2 options are marked correct"),
        ("correct given as text", lambda c: g(c)[0]["options"][0].update(correct="false"), '"correct" must be true or false'),
        ("an item with two options", lambda c: g(c)[0].update(options=g(c)[0]["options"][:2]), "needs at least three options"),
        ("two options with the same text", lambda c: g(c)[0]["options"][1].update(text=g(c)[0]["options"][0]["text"]), "two options have the same text"),
        ("an all-of-the-above option", lambda c: g(c)[0]["options"][2].update(text="All of the above"), "are not allowed"),
        ("a worked example with no partial level", lambda c: c["modules"][0]["worked"][0].pop("partial"), "is missing the partial level"),
        ("a partial level with no blank", lambda c: c["modules"][0]["worked"][0]["partial"].update(steps=[{"text": "Double it.", "result": "ten"}]), "has no blank for the learner"),
        ("an independent level with no solution", lambda c: c["modules"][0]["worked"][0]["independent"].update(solution=[]), "independent level solution: has no steps"),
        ("a ready module with no theory", lambda c: c["modules"][0].update(theory=[]), "marked ready with no theory"),
        ("an objective with no theory section", lambda c: c["modules"][0].update(theory=c["modules"][0]["theory"][:1]), 'objective "a-o2" has no theory section'),
        ("a ready module with no cards", lambda c: c["modules"][0].update(cards=[]), "marked ready with no cards"),
        ("a ready module with no cheat sheet", lambda c: c["modules"][0].update(cheatsheet=[]), "marked ready with no cheat sheet"),
        ("a ready module with no summary", lambda c: c["modules"][0].update(summary=" "), "marked ready with no summary"),
        ("a ready module with no gate", lambda c: c["modules"][0].update(gate={"items": []}), "marked ready with no gate items"),
        ("a formula using an unknown variable", lambda c: c["modules"][0]["visuals"][0]["outputs"][0].update(formula="x * k"), "uses unknown variable k"),
        ("a formula with a disallowed token", lambda c: c["modules"][0]["visuals"][0]["outputs"][0].update(formula="x ** 2"), "is refused"),
        ("a formula calling an unknown function", lambda c: c["modules"][0]["visuals"][0]["outputs"][0].update(formula="alert(x)"), 'unknown function "alert"'),
        ("a formula with no value at the start", lambda c: c["modules"][0]["visuals"][0]["outputs"][0].update(formula="1 / (x - x)"), "has no value at the default settings"),
        ("a card with an empty side", lambda c: c["modules"][0]["cards"][0].update(back=""), "has an empty side"),
        ("a planned module carrying content", lambda c: c["modules"][1].update(status="planned"), "is marked planned but carries content"),
        ("a written module waiting on a planned one", planned, "can never open"),
        ("placeholder text", lambda c: c["modules"][0]["theory"][0]["blocks"][0].update(text="TODO write this"), "contains placeholder text"),
        ("a version given as text", lambda c: c.update(version="1"), "version must be a whole number"),
        ("a pass mark of 49", lambda c: c.update(gate_threshold=49), "gate_threshold must be"),
        ("a pass mark of 101", lambda c: c.update(gate_threshold=101), "gate_threshold must be"),
        ("an unknown visual type", lambda c: c["modules"][0]["visuals"][0].update(type="pie"), "unknown visual type"),
        ("a visual with no caption", lambda c: c["modules"][0]["visuals"][0].update(caption=""), "has no caption"),
    ]


def selftest():
    import copy
    results = []
    base = _selftest_course()
    rep0, _ = validate(copy.deepcopy(base), "")
    results.append(("the unmodified self-test course has no errors", not rep0.errors, "; ".join(rep0.errors[:2])))
    for name, change, expect in _planted():
        c = copy.deepcopy(base)
        change(c)
        r, _ = validate(c, "")
        hit = [e for e in r.errors if expect in e]
        results.append(("planted fault caught: " + name, bool(hit), (hit[0] if hit else "expected an error containing %r; got %s" % (expect, r.errors[:2]))))
    for mark in (50, 100):
        c = copy.deepcopy(base)
        c["gate_threshold"] = mark
        r, _ = validate(c, "")
        results.append(("valid neighbour accepted: a pass mark of %d" % mark, not r.errors, "; ".join(r.errors[:1])))
    adv = [
        ("the correct answer always in one position", lambda c: [[o.update(correct=(k == 0)) for k, o in enumerate(it["options"])] for m in c["modules"] for it in m["quiz"] + m["gate"]["items"]], "spread the correct position"),
        ("a correct option much longer than the rest", lambda c: c["modules"][0]["quiz"][0]["options"][0].update(text="the one option that happens to be very much longer than either of the others"), "much longer than the others"),
        ("a module with no visual", lambda c: c["modules"][0].update(visuals=[]), "has no visual"),
        ("thirteen new terms in one module", lambda c: c["modules"][0].update(terms=[{"term": "t%d" % k, "definition": "A made-up definition."} for k in range(13)]), "defines 13 new terms"),
    ]
    for name, change, expect in adv:
        c = copy.deepcopy(base)
        change(c)
        r, _ = validate(c, "")
        results.append(("advisory raised: " + name, any(expect in a for a in r.advisories) and not r.errors, "advisories: %s; errors: %s" % (r.advisories[:2], r.errors[:1])))
    c = copy.deepcopy(base)
    c["modules"][0]["terms"] = [{"term": "t%d" % k, "definition": "A made-up definition."} for k in range(12)]
    r, _ = validate(c, "")
    results.append(("valid neighbour: twelve terms raise no advisory", not any("new terms" in a for a in r.advisories), ""))
    new = copy.deepcopy(base)
    new["modules"][1]["objectives"][1]["id"] = "b-o2x"
    for it in new["modules"][1]["gate"]["items"] + new["modules"][1]["quiz"] + new["modules"][1]["cards"] + new["modules"][1]["theory"]:
        if it.get("objective") == "b-o2":
            it["objective"] = "b-o2x"
    r, _ = compare(base, new)
    results.append(("compare: an objective id removed without raising the version is an error", any('"b-o2" was removed' in e for e in r.errors), "; ".join(r.errors[:1])))
    new["version"] = 2
    r, _ = compare(base, new)
    results.append(("compare: the same removal with the version raised is an advisory", not r.errors and any('"b-o2" was removed' in a for a in r.advisories), "; ".join(r.errors[:1])))
    new = copy.deepcopy(base)
    new["version"] = 2
    new["modules"][0]["objectives"][0]["text"] = "SYNTHETIC objective that now says something else."
    r, _ = compare(base, new)
    results.append(("compare: an id kept with changed wording is reported", any("changed wording" in a for a in r.advisories), ""))
    r, counts = compare(base, copy.deepcopy(base))
    results.append(("compare: identical courses report nothing", not r.errors and not r.advisories, "; ".join(r.errors + r.advisories)[:120]))
    return results



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
            print("validate_course: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if "--selftest" in flags:
        if args or "--compare" in flags:
            print("validate_course: --selftest takes no file", file=sys.stderr)
            return 2
        results = selftest()
        failed = [r for r in results if not r[1]]
        if "--json" in flags:
            emit(json.dumps({"checks": [{"check": r[0], "ok": r[1], "detail": r[2]} for r in results], "failed": len(failed), "total": len(results)}, indent=1, ensure_ascii=True))
        else:
            for name, ok, detail in results:
                emit("%-5s %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + detail[:160] + "]") if (detail and not ok) else ""))
            emit("RESULT: %s. %d of %d checks passed." % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
        return 1 if failed else 0
    want = 2 if "--compare" in flags else 1
    if len(args) != want:
        if not argv:
            print(__doc__)
        else:
            print("validate_course: expected %s" % ("--compare OLD NEW" if want == 2 else "one course file (JSON or built page)"), file=sys.stderr)
        return 2
    try:
        loaded = [read_course(p) for p in args]
    except InputError as e:
        print("validate_course: %s" % e, file=sys.stderr)
        return 2
    if "--compare" in flags:
        rep, counts = compare(loaded[0][0], loaded[1][0])
        head = "validate_course --compare: %s version %r against version %r" % (loaded[1][0].get("id"), loaded[0][0].get("version"), loaded[1][0].get("version"))
        tail = "%d removed, %d moved, %d reworded, %d added." % (counts.get("removed", 0), counts.get("moved", 0), counts.get("reworded", 0), counts.get("added", 0))
        extra = {"counts": counts}
    else:
        rep, stats = validate(loaded[0][0], loaded[0][1])
        head = "validate_course: %s version %r: %d written and %d planned module(s), %d objective(s), %d practice and %d gate item(s), %d worked example(s), %d visual(s), %d card(s)" % (
            loaded[0][0].get("id"), loaded[0][0].get("version"), stats["modules_ready"], stats["modules_planned"], stats["objectives"],
            stats["practice_items"], stats["gate_items"], stats["worked_examples"], stats["visuals"], stats["cards"])
        tail = "This checks wiring and form, not whether the content is correct."
        extra = {"counts": stats}
    if "--json" in flags:
        out = {"errors": rep.errors, "advisories": rep.advisories}
        out.update(extra)
        emit(json.dumps(out, indent=1, ensure_ascii=True))
    else:
        lines = [head] + ["  ERROR     " + m for m in rep.errors] + ["  ADVISORY  " + m for m in rep.advisories]
        lines.append("RESULT: %s. %d error(s), %d advisory note(s). %s" % ("FAIL" if rep.errors else "PASS", len(rep.errors), len(rep.advisories), tail))
        emit("\n".join(lines))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
