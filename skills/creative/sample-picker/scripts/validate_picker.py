#!/usr/bin/env python3
"""Check the data for a sample picker before it is shown to anyone. Standard library only.

Usage:
  python validate_picker.py PICKER.json [--json]
  python validate_picker.py PICKER.html [--json]      reads the PICKER object out of a built picker

The data is one strict JSON object (see references/picker-data.md for every field):
  {"id": "kebab-case-id", "version": 1, "title": "...", "question": "what is being chosen",
   "kind": "theme" | "type" | "layout" | "copy" | "component" | "custom",
   "recommended": {"id": "an-option-id", "reason": "why, in a clause"},
   "options": [{"id": "...", "name": "...", "note": "one line on what is different about it",
                "tokens": {...}, "sample": {...}}],
   "controls": [{"id": "density", "label": "...", "type": "choice" | "range" | "toggle", ...}],
   "context": {... the real content the options are drawn on ...}}

What it enforces (ERROR, exit 1):
  - the picker id, option ids and control ids are lower-case words joined by hyphens, and unique
  - 2 to 8 options. One option is not a choice; more than eight is a list
  - every option has a name and a one-line note, and no two names, notes or renderings are the same
  - the context is present and holds real content: lorem ipsum, "Sample text", "Your text here"
    and their relatives are refused wherever they appear
  - each kind has what its renderer needs (for a theme: nine colour tokens as hex and every part of
    the specimen; for type: a font stack; for layout: columns and rows; for copy: a heading)
  - for kind "theme", each option's contrast pairs are computed, and body text under 4.5 to 1 on
    the page or on a surface is refused
  - controls are well formed, their defaults are valid, and each one is a control the kind's
    built-in renderer responds to. A control that changes nothing is refused
  - "recommended", when given, names an option and has a reason
What it reports for a person to decide (ADVISORY):
  - seven or eight options: more than six is hard to hold in mind
  - no recommended option: the person should be reacting to a commitment
  - ids that are positions ("a", "option-2"), which change meaning when the order changes
  - theme pairs other than body text that are under 4.5 (the picker will name them on the card)
  - a font stack with no generic family at its end

What it cannot tell: whether the options differ in a way that matters, whether the content is
really the user's, or how anything looks. Look at the built picker.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import picker_result as pr  # noqa: E402

FLAGS = {"--json"}
KEBAB = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
KINDS = ("theme", "type", "layout", "copy", "component", "custom")
TOP_KEYS = {"id", "version", "title", "question", "kind", "recommended", "options", "controls", "context"}
OPTION_KEYS = {"id", "name", "note", "tokens", "sample"}
THEME_TOKENS = ("bg", "surface", "text", "muted", "line", "accent", "on-accent", "danger", "ok")
OPTIONAL_TOKENS = ("accent-strong", "focus", "field")
# control ids each built-in renderer responds to, and the values a choice may take
CONTROLS = {
    "theme": {"density": "choice", "text-size": "range", "radius": "range"},
    "type": {"scale": "range", "measure": "range"},
    "layout": {"density": "choice", "text-size": "range", "stripes": "toggle"},
    "copy": {"align": "choice", "heading-size": "range", "action": "toggle", "density": "choice"},
    "component": {"density": "choice", "text-size": "range"},
}
CHOICE_VALUES = {"density": ("compact", "comfortable", "roomy"), "align": ("left", "centre")}
RANGE_UNITS = {"text-size": "px", "radius": "px", "heading-size": "px", "scale": "", "measure": "ch"}
PLACEHOLDER = re.compile(
    r"lorem\s+ipsum|dolor\s+sit\s+amet|\bsample\s+text\b|\bplaceholder\b|\byour\s+(text|title|heading|content|name)\s+here\b|"
    r"\b(heading|title|text|content)\s+goes\s+here\b|\bfoo\s*bar\b|\binsert\s+(text|copy)\b|\bexample\s+(heading|text|title)\b|\btbd\b|\bxxx+\b", re.I)
POSITIONAL = re.compile(r"(?:[a-z]|(?:option|opt|variant|version|choice|v)-?\d+|\d+)")
GENERIC_FONTS = ("serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded")
DATA_START, DATA_END = "/* PICKER-DATA:START */", "/* PICKER-DATA:END */"


class Bad(Exception):
    pass


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf")) and (not isinstance(v, int) or v.bit_length() <= 1023)


def text_ok(v, min_len=1):
    return isinstance(v, str) and len(v.strip()) >= min_len


def read_data(path):
    """Returns the PICKER object from a .json file or from between the markers of a built .html picker."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise Bad("cannot read %s: %s" % (path, e.strerror or e))
    if bytes([0]) in raw:
        raise Bad("%s contains a NUL byte" % path)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Bad("%s is not valid UTF-8" % path)
    if str(path).lower().endswith((".html", ".htm")):
        if text.count(DATA_START) != 1 or text.count(DATA_END) != 1:
            raise Bad("%s does not hold one PICKER-DATA block" % path)
        block = text[text.index(DATA_START) + len(DATA_START):text.index(DATA_END)].strip()
        m = re.fullmatch(r"const PICKER = (.*);", block, re.S)
        if not m:
            raise Bad("the PICKER-DATA block must be exactly: const PICKER = {strict JSON};")
        text = m.group(1)

    def no_constant(c):
        raise ValueError("%s is not allowed" % c)
    try:
        return json.loads(text, parse_constant=no_constant)
    except ValueError as e:
        raise Bad("%s does not hold strict JSON (%s)" % (path, str(e)[:70]))


# ---- WCAG contrast from hex tokens ----
def rgb(hex_text):
    h = hex_text.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(c):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def contrast(fg, bg):
    a, b = luminance(rgb(fg)), luminance(rgb(bg))
    return round((max(a, b) + 0.05) / (min(a, b) + 0.05), 2)


def theme_pairs(t):
    """The text pairs the theme specimen draws, as (label, foreground token, background token, is body text)."""
    field = t.get("field", t["surface"])
    pairs = [("body text on the page", "text", t["bg"], True), ("text on a surface", "text", t["surface"], True),
             ("input text", "text", field, True), ("muted text on the page", "muted", t["bg"], False),
             ("muted text on a surface", "muted", t["surface"], False), ("link on the page", "accent", t["bg"], False),
             ("button label", "on-accent", t["accent"], False), ("error text on a surface", "danger", t["surface"], False),
             ("status message on the page", "ok", t["bg"], False)]
    if "accent-strong" in t:
        pairs.append(("button label, hover", "on-accent", t["accent-strong"], False))
    return [(label, contrast(t[fg], bg), body) for label, fg, bg, body in pairs]


def strings_in(v, path=""):
    if isinstance(v, str):
        yield path, v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from strings_in(x, (path + "." + str(k)) if path else str(k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from strings_in(x, "%s[%d]" % (path, i))


def check(d):
    errors, advisories, computed = [], [], {}
    if not isinstance(d, dict):
        return ["the picker must be one JSON object"], [], {}
    for k in sorted(set(d) - TOP_KEYS):
        errors.append("unknown key %r at the top level" % k)
    if not isinstance(d.get("id"), str) or not KEBAB.fullmatch(d["id"]):
        errors.append("id must be lower-case words joined by hyphens, for example notes-theme")
    if "version" in d and (not isinstance(d["version"], int) or isinstance(d["version"], bool) or d["version"] < 1):
        errors.append("version must be a whole number, 1 or more")
    if not text_ok(d.get("title"), 3):
        errors.append("title is missing")
    if not text_ok(d.get("question"), 8):
        errors.append("question is missing: say what is being chosen")
    kind = d.get("kind")
    if kind not in KINDS:
        errors.append("kind must be one of %s" % ", ".join(KINDS))
        kind = None
    ctx = d.get("context")
    if isinstance(ctx, str):
        ctx = {"text": ctx} if kind == "type" else ctx
    if ctx is None or ctx == "" or ctx == {}:
        errors.append("context is missing: the options must be drawn on the real content")
    for where, s in strings_in({"context": d.get("context"), "options": [{"sample": o.get("sample")} for o in d.get("options", []) if isinstance(o, dict)] if isinstance(d.get("options"), list) else []}):
        m = PLACEHOLDER.search(s)
        if m:
            errors.append("%s holds placeholder text (%r): use the real content, or the nearest real thing" % (where, m.group(0)))

    opts = d.get("options")
    if not isinstance(opts, list) or not all(isinstance(o, dict) for o in opts):
        errors.append("options must be a list of objects")
        opts = []
    if not 2 <= len(opts) <= 8:
        errors.append("there are %d option(s); a picker has 2 to 8 (one is not a choice, more than eight is a list)" % len(opts))
    elif len(opts) > 6:
        advisories.append("there are %d options; more than six is hard to hold in mind. Cut to the ones that differ most" % len(opts))
    ids, names, notes, renders = {}, {}, {}, {}
    for i, o in enumerate(opts):
        where = "option %d" % (i + 1)
        oid = o.get("id")
        if not isinstance(oid, str) or not KEBAB.fullmatch(oid):
            errors.append(where + ": id must be lower-case words joined by hyphens")
        else:
            where = "option %r" % oid
            if oid in ids:
                errors.append(where + ": id is used twice")
            ids[oid] = i
            if POSITIONAL.fullmatch(oid):
                advisories.append(where + ": the id is a position. Name it for what it is, so it still means the same if the order changes")
        for k in sorted(set(o) - OPTION_KEYS):
            errors.append("%s: unknown key %r" % (where, k))
        if not text_ok(o.get("name"), 2):
            errors.append(where + ": name is missing")
        else:
            key = " ".join(o["name"].lower().split())
            if key in names:
                errors.append("%s: has the same name as option %d" % (where, names[key] + 1))
            names[key] = i
        note = o.get("note")
        if not text_ok(note, 8):
            errors.append(where + ": note is missing. Say in one line what is different about this option")
        elif "\n" in note.strip() or len(note.strip()) > 140:
            errors.append(where + ": note must be one line of 140 characters or fewer")
        else:
            key = re.sub(r"[^a-z0-9]+", " ", note.lower()).strip()
            if key in notes:
                errors.append("%s: has the same note as option %d. If you cannot say how they differ, they are one option" % (where, notes[key] + 1))
            notes[key] = i
        if o.get("tokens") is not None and not isinstance(o["tokens"], dict):
            errors.append(where + ": tokens must be an object")
        if o.get("sample") is not None and not isinstance(o["sample"], dict):
            errors.append(where + ": sample must be an object")
        if kind != "custom":
            key = json.dumps({"t": o.get("tokens") or {}, "s": o.get("sample") or {}}, sort_keys=True)
            if key in renders:
                errors.append("%s: has the same tokens and sample as option %d, so the two would look identical" % (where, renders[key] + 1))
            renders[key] = i
        check_option_for_kind(kind, o, where, errors, advisories, computed)
    check_context_for_kind(kind, ctx, errors)

    rec = d.get("recommended")
    if rec is None:
        advisories.append("no option is marked as recommended. Commit to one, with the reason, so the person is reacting to a recommendation")
    elif not isinstance(rec, dict) or rec.get("id") not in ids or not text_ok(rec.get("reason"), 8):
        errors.append("recommended must be {\"id\": an option id, \"reason\": why in a clause}")

    ctls = d.get("controls", [])
    if not isinstance(ctls, list) or not all(isinstance(c, dict) for c in ctls):
        errors.append("controls must be a list of objects")
        ctls = []
    seen = set()
    for i, c in enumerate(ctls):
        cid = c.get("id")
        where = "control %r" % cid if isinstance(cid, str) else "control %d" % (i + 1)
        if not isinstance(cid, str) or not KEBAB.fullmatch(cid):
            errors.append(where + ": id must be lower-case words joined by hyphens")
            continue
        if cid in seen:
            errors.append(where + ": id is used twice")
        seen.add(cid)
        if not text_ok(c.get("label"), 2):
            errors.append(where + ": label is missing")
        ctype = c.get("type")
        if ctype not in ("choice", "range", "toggle"):
            errors.append(where + ": type must be choice, range or toggle")
            continue
        if kind in CONTROLS:
            want = CONTROLS[kind].get(cid)
            if want is None:
                errors.append("%s: the built-in %s renderer does not respond to it, so it would change nothing. It responds to: %s" % (where, kind, ", ".join(sorted(CONTROLS[kind]))))
                continue
            if want != ctype:
                errors.append("%s: must be of type %s for kind %s" % (where, want, kind))
                continue
        if ctype == "toggle":
            if not isinstance(c.get("default"), bool):
                errors.append(where + ": a toggle's default is true or false")
        elif ctype == "choice":
            vals = [o if isinstance(o, str) else (o.get("value") if isinstance(o, dict) else None) for o in c.get("options", [])] if isinstance(c.get("options"), list) else []
            if len(vals) < 2 or not all(isinstance(v, str) and v for v in vals) or len(set(vals)) != len(vals):
                errors.append(where + ": a choice needs two or more different options")
            elif not all(isinstance(o, str) or text_ok(o.get("label")) for o in c["options"]):
                errors.append(where + ": each option needs a label")
            elif c.get("default") not in vals:
                errors.append(where + ": default must be one of its options")
            elif kind in CONTROLS and cid in CHOICE_VALUES and not set(vals) <= set(CHOICE_VALUES[cid]):
                errors.append("%s: its options must come from %s" % (where, ", ".join(CHOICE_VALUES[cid])))
        else:
            lo, hi, step, dv = c.get("min"), c.get("max"), c.get("step", 1), c.get("default")
            if not (is_num(lo) and is_num(hi) and is_num(step) and is_num(dv)):
                errors.append(where + ": a range needs numeric min, max and default (text and true are not numbers)")
            elif not lo < hi or step <= 0:
                errors.append(where + ": a range needs min below max and a step above zero")
            elif not lo <= dv <= hi:
                errors.append(where + ": default %s is outside %s to %s" % (dv, lo, hi))
            elif abs(round((dv - lo) / step) * step - (dv - lo)) > 1e-9:
                errors.append(where + ": default %s is not on the step grid from %s in steps of %s" % (dv, lo, step))
            elif kind in CONTROLS and cid in RANGE_UNITS and c.get("unit", "") != RANGE_UNITS[cid]:
                errors.append("%s: unit must be %r for this control" % (where, RANGE_UNITS[cid]))
    return errors, advisories, computed


def check_option_for_kind(kind, o, where, errors, advisories, computed):
    tokens = o.get("tokens") if isinstance(o.get("tokens"), dict) else {}
    sample = o.get("sample") if isinstance(o.get("sample"), dict) else {}
    for k, v in tokens.items():
        if kind in ("theme", "copy", "layout", "component") and (not isinstance(v, str) or not HEX.fullmatch(v)):
            errors.append("%s: token %r must be a hex colour such as #2a2320, got %r" % (where, k, v))
    if kind == "theme":
        missing = [k for k in THEME_TOKENS if not (isinstance(tokens.get(k), str) and HEX.fullmatch(tokens[k]))]
        if missing:
            errors.append("%s: a theme needs these colour tokens as hex: %s" % (where, ", ".join(missing)))
            return
        extra = sorted(set(tokens) - set(THEME_TOKENS) - set(OPTIONAL_TOKENS))
        if extra:
            errors.append("%s: unknown theme token %r (known: %s)" % (where, extra[0], ", ".join(THEME_TOKENS + OPTIONAL_TOKENS)))
            return
        if any(not HEX.fullmatch(str(tokens[k])) for k in OPTIONAL_TOKENS if k in tokens):
            return
        pairs = theme_pairs(tokens)
        computed[o.get("id")] = [{"pair": label, "ratio": r, "body_text": body} for label, r, body in pairs]
        for label, r, body in pairs:
            if r < 4.5 and body:
                errors.append("%s: %s is %.2f to 1, under 4.5. Body text below the minimum is not offered as an option" % (where, label, r))
            elif r < 4.5:
                advisories.append("%s: %s is %.2f to 1, under 4.5. The picker will name it on the card" % (where, label, r))
    elif kind == "type":
        if not text_ok(sample.get("stack"), 3):
            errors.append(where + ": sample.stack (the font stack) is missing")
        else:
            last = sample["stack"].split(",")[-1].strip().strip("'\"").lower()
            if last not in GENERIC_FONTS:
                advisories.append("%s: the font stack does not end in a generic family (serif, sans-serif, monospace), so the fallback is the browser's default" % where)
        for k, lo, hi in (("size", 8, 96), ("weight", 100, 900), ("leading", 0.9, 3), ("measure", 20, 120), ("heading_size", 8, 160), ("heading_weight", 100, 900)):
            if k in sample and (not is_num(sample[k]) or not lo <= sample[k] <= hi):
                errors.append("%s: sample.%s must be a number from %s to %s" % (where, k, lo, hi))
    elif kind == "layout":
        if sample.get("layout") not in ("table", "cards", "list"):
            errors.append(where + ": sample.layout must be table, cards or list")
    elif kind == "copy":
        if not text_ok(sample.get("heading"), 2):
            errors.append(where + ": sample.heading is missing")
        for k in ("sub", "action"):
            if k in sample and not text_ok(sample[k]):
                errors.append("%s: sample.%s is empty" % (where, k))
    elif kind == "component":
        if "variant" in sample and sample["variant"] not in ("solid", "outline", "soft"):
            errors.append(where + ": sample.variant must be solid, outline or soft")
        for k, lo, hi in (("radius", 0, 40), ("border", 0, 6), ("weight", 100, 900), ("pad_y", 0, 40), ("pad_x", 0, 60)):
            if k in sample and (not is_num(sample[k]) or not lo <= sample[k] <= hi):
                errors.append("%s: sample.%s must be a number from %s to %s" % (where, k, lo, hi))


def check_context_for_kind(kind, ctx, errors):
    if kind is None or kind == "custom" or ctx in (None, "", {}):
        return
    if not isinstance(ctx, dict):
        errors.append("context must be an object for kind %s (see references/picker-data.md)" % kind)
        return
    if isinstance(ctx.get("tokens"), dict):
        for k, v in ctx["tokens"].items():
            if not isinstance(v, str) or not HEX.fullmatch(v):
                errors.append("context.tokens.%s must be a hex colour" % k)
    if kind == "theme":
        for k in ("title", "body", "primary"):
            if not text_ok(ctx.get(k)):
                errors.append("context.%s is missing: the theme specimen needs the real %s" % (k, {"title": "heading", "body": "paragraph", "primary": "button label"}[k]))
        f = ctx.get("field")
        if not isinstance(f, dict) or not all(text_ok(f.get(k)) for k in ("label", "value", "error")):
            errors.append("context.field needs a real label, value and error message")
        cols, rows = ctx.get("columns"), ctx.get("rows")
        if not isinstance(cols, list) or not cols or not isinstance(rows, list) or not rows or not all(isinstance(r, list) and len(r) == len(cols) for r in rows):
            errors.append("context.columns and context.rows are needed: at least one real table row, with one value per column")
    elif kind == "type":
        t = ctx.get("text")
        if not (text_ok(t, 40) or (isinstance(t, list) and t and all(text_ok(x, 20) for x in t))):
            errors.append("context.text is missing or too short: give the real paragraph or paragraphs the type will set")
    elif kind == "layout":
        cols, rows = ctx.get("columns"), ctx.get("rows")
        if not isinstance(cols, list) or len(cols) < 2 or not all(isinstance(c, dict) and text_ok(c.get("key")) and text_ok(c.get("label")) for c in cols):
            errors.append("context.columns needs two or more {key, label} objects")
            return
        if any(c.get("role") not in (None, "title", "value", "status") for c in cols):
            errors.append("a column's role is title, value or status, or is left out")
        if not isinstance(rows, list) or len(rows) < 2 or not all(isinstance(r, dict) and all(c["key"] in r for c in cols) for r in rows):
            errors.append("context.rows needs two or more objects with a value for every column key")
    elif kind == "copy":
        if ctx.get("component", "header") not in ("header", "notice"):
            errors.append("context.component must be header or notice")
        if ctx.get("component", "header") == "header" and not text_ok(ctx.get("brand")):
            errors.append("context.brand is missing: the header sample needs the real product name")
    elif kind == "component":
        if ctx.get("component") not in ("button", "field"):
            errors.append("context.component must be button or field")
        if not text_ok(ctx.get("label")):
            errors.append("context.label is missing: use the real label")
        if ctx.get("component") == "field" and not all(text_ok(ctx.get(k)) for k in ("value", "error")):
            errors.append("a field needs a real value and a real error message in the context")


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a in FLAGS:
            flags.add(a)
        elif a.startswith("--"):
            print("validate_picker: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        data = read_data(args[0])
    except Bad as e:
        print("validate_picker: " + str(e).encode("ascii", "replace").decode("ascii"), file=sys.stderr)
        return 2
    errors, advisories, computed = check(data)
    pr.result('failed' if errors else 'completed', {'source': args[0], 'picker_id': data.get('id') if isinstance(data, dict) else None, 'kind': data.get('kind') if isinstance(data, dict) else None, 'option_ids': [o.get('id') for o in data.get('options', []) if isinstance(o, dict)] if isinstance(data, dict) and isinstance(data.get('options'), list) else [], 'errors': errors, 'advisories': advisories, 'contrast_options': list(computed)}, 'Picker data checked; appearance and meaningful differences were not judged.')
    if "--json" in flags:
        text = json.dumps({"errors": errors, "advisories": advisories, "contrast": computed}, indent=1, ensure_ascii=True)
    else:
        n = len(data.get("options", [])) if isinstance(data, dict) and isinstance(data.get("options"), list) else 0
        L = ["validate_picker: %s: %d option(s), kind %s" % (Path(args[0]).name, n, data.get("kind") if isinstance(data, dict) else "?")]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        for oid, pairs in computed.items():
            low = min(pairs, key=lambda p: p["ratio"])
            L.append("  contrast  %-22s %d pair(s) from tokens, lowest %.2f (%s)" % (oid, len(pairs), low["ratio"], low["pair"]))
        L.append("RESULT: %s. %d error(s), %d advisory note(s). This checks the data, not how the options look."
                 % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(pr.run("validate_picker", main, sys.argv[1:]))
