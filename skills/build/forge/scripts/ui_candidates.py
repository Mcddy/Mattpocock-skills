#!/usr/bin/env python3
"""List things to look at in generated interface code. Standard library only. Reads files, changes nothing.

Usage:
  python ui_candidates.py <file-or-dir> [<file-or-dir> ...] [--json] [--fail-on-defect]

Two kinds of finding:

  DEFECT     The source text is itself the fault, against a named standard, whatever the page looks
             like. There are three: a viewport tag that blocks or limits zoom, an image with no alt
             attribute, an html element with no lang attribute.
  CANDIDATE  A pattern matched. It may be fine. It is a prompt to look at the rendered interface, or
             to test in the place the interface will be delivered, and decide. A candidate is never a
             failure on its own.

Attributes are read by name. data-alt is not alt, data-lang is not lang, and an attribute that
follows a JSX arrow function or a value containing ">" is still found.

Exit codes: 0 completed. 1 if --fail-on-defect is given and at least one DEFECT was found.
2 for an unknown option, no path, or no interface files found.

Rule numbers refer to references/protocol.md. "pattern" means a common default with no numbered
rule. "delivery" means something that works in a plain browser tab and can be blocked inside a
sandboxed frame; see references/review.md.
A clean run does not mean the interface is good. It means none of these patterns matched.
"""
import colorsys
import json
import re
import sys
from pathlib import Path
import pathlib

VERSION = "forge 3.3.2"

EXT = {".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
OPTIONS = {"--json", "--fail-on-defect"}
SPARKLES = chr(0x2728) + chr(0x2726)
EMOJI = "[" + chr(0x1F300) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + "]"
LONG_DASH = chr(0x2014)

LINE_RULES = [
    # id, reference, regex, flags, message
    ("gradient-indigo-violet", "Rule 1", r"from-(indigo|violet|purple|fuchsia)-\d+[^\"'\n]*\bto-(purple|violet|indigo|blue|cyan|pink|fuchsia)-\d+", re.I, "indigo to violet gradient: is it this product's colour or the default?"),
    ("glow", "Rule 3", r"shadow-\[0_0_\d{2,}px|box-shadow:\s*0\s+0\s+(3\d|[4-9]\d|\d{3})px", re.I, "glow shadow around a card or button"),
    ("glass", "Rule 9", r"backdrop-filter:\s*blur|\bbackdrop-blur", re.I, "backdrop blur: check text over it stays readable"),
    ("gradient-text", "Rule 1", r"background-clip:\s*text|\bbg-clip-text\b", re.I, "gradient text"),
    ("sparkle-icon", "Rule 47", "[" + SPARKLES + r"]|<(Sparkles?|Wand2?)\b|\b(Sparkles?|Wand2?)\s*[,}]", 0, "sparkle or wand icon: does it mean anything on this action?"),
    ("buzzword", "Rule 41", r"\b(elevate|unleash|supercharge|revolutioni[sz]e|next-gen|ai-powered insights|seamless workflow)\b", re.I, "filler marketing word"),
    ("apology-toast", "Rule 45", r"\bOops\b|Something went wrong", 0, "error message that does not say what happened or what to do"),
    ("native-dialog", "delivery", r"(?<![\w.])(alert|confirm|prompt)\s*\(|window\.(alert|confirm|prompt|print)\s*\(", 0, "native dialog: ignored in a frame without allow-modals, and unstyled everywhere (Rule 67)"),
    ("long-dash", "user prefs", LONG_DASH, 0, "long dash in interface copy: check it against the user's writing preferences"),
    ("heading-emoji", "Rule 47", r"<h[1-6][^>]*>[^<]*" + EMOJI, 0, "emoji in a heading"),
    ("typewriter", "pattern", r"typewriter|typed\.js|\bTypeIt\b", re.I, "typewriter text effect"),
    ("generic-placeholder", "Rule 49", r"placeholder=[\"'](Enter text here|Type a message|Type here|Enter your text)", re.I, "generic placeholder text"),
    ("lazy-empty-state", "Rule 69", r"No data available", re.I, "empty state that only says there is no data"),
    ("default-font", "Rule 11", r"font-family:\s*[\"']?(Inter|Geist|Poppins|Space Grotesk)\b", re.I, "common default font: was it chosen for this product?"),
    ("pill-button", "Rule 33", r"<(button|Button)\b[^>]*rounded-full|border-radius:\s*9{3,4}px", 0, "fully rounded control: fine for chips, check utility buttons"),
    ("triplet-copy", "Rule 43", r">\s*[A-Z][a-z]+\. [A-Z][a-z]+\. [A-Z][a-z]+\.\s*<", 0, "three one-word sentences as a tagline"),
    ("scroll-fade", "Rule 73", r"data-aos|whileInView|\bfade-in(-up)?\b", 0, "fade-in on scroll"),
    ("tilt-hover", "Rule 73", r"vanilla-tilt|:hover[^{]*\{[^}]*rotate[XY]\(", re.I, "3D tilt on hover"),
    ("accent-edge", "pattern", r"\bborder-[lt]-4\b|border-(left|top):\s*[3-6]px\s+solid", re.I, "coloured edge stripe on a card: does the colour carry meaning?"),
    ("bento", "Rule 23", r"\bbento\b", re.I, "bento grid: does the content have that shape?"),
    ("wave-divider", "pattern", r"<svg[^>]*(class|id)=[\"'][^\"']*wave", re.I, "wavy SVG divider"),
    ("library-default-card", "Rule 25", r"rounded-lg border bg-card text-card-foreground shadow-sm", 0, "component-library default card, unmodified"),
    ("blurred-orb", "Rule 3", r"\bblur-(2xl|3xl)\b|filter:\s*blur\((4\d|[5-9]\d|\d{3})px", re.I, "large decorative blur"),
    ("outline-removed", "WCAG 2.4.7", r"outline:\s*(none|0)\b", re.I, "focus outline removed: confirm a visible replacement exists"),
    # delivery: fine in a browser tab, can be blocked in a sandboxed frame
    ("submit-handler", "delivery", r"\bonsubmit\s*=|\bonSubmit\s*=|addEventListener\(\s*[\"']submit[\"']|\.requestSubmit\(|\.submit\(\s*\)", 0, "depends on form submission: blocked in a frame without allow-forms. Use a click handler on a type=button control"),
    ("popup", "delivery", r"window\.open\s*\(|target\s*=\s*[\"']_blank[\"']", 0, "opens a new window or tab: blocked in a frame without allow-popups"),
    ("download", "delivery", r"\bdownload\s*=|createObjectURL\s*\(", 0, "file download: blocked in a frame without allow-downloads. Offer the content in the page as well"),
    ("storage", "delivery", r"\b(localStorage|sessionStorage|indexedDB)\b|document\.cookie", 0, "browser storage: throws in a frame without allow-same-origin. Wrap in try and catch and work without it"),
    ("top-navigation", "delivery", r"\b(top|parent)\.location\b|window\.(top|parent)\b", 0, "reaches the outer page: blocked in a sandboxed frame"),
    ("clipboard", "delivery", r"navigator\.clipboard\b", 0, "clipboard API: can be denied in a frame. Keep a select-the-text fallback"),
    ("fullscreen", "delivery", r"requestFullscreen\s*\(", 0, "fullscreen request: can be denied in a frame"),
]
COMPILED = [(i, ref, re.compile(rx, fl), msg) for i, ref, rx, fl, msg in LINE_RULES]
GRAD = re.compile(r"(linear|radial|conic)-gradient\(([^;{}]*)\)", re.I)
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
TAG_START = re.compile(r"<(img|html|meta|input|select|textarea|label|div|span|form|button)(?=[\s/>])", re.I)
WS = " \t\r\n\f"


def hue_sat(h):
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hh, _l, s = colorsys.rgb_to_hls(r, g, b)
    return hh * 360.0, s


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def match_brace(s, i):
    """s[i] is '{'. Return the index just past its matching '}', honouring quotes. End of string if unbalanced."""
    depth, quote, n = 0, None, len(s)
    while i < n:
        c = s[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def read_tag(text, i, limit=6000):
    """text[i] is '<'. Return the tag's source up to its closing '>', honouring quotes and braces, or None."""
    n, j, quote = len(text), i + 1, None
    while j < n and j - i < limit:
        c = text[j]
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "{":
            j = match_brace(text, j)
            continue
        elif c == ">":
            return text[i:j + 1]
        elif c == "<":
            return None
        j += 1
    return None


def parse_tag(raw):
    """Return (tag name, {attribute name: value}, has_spread). Names are lower-cased and matched whole."""
    m = re.match(r"<\s*([A-Za-z][\w:.-]*)", raw)
    if not m:
        return None, {}, False
    tag, i, n, attrs, spread = m.group(1).lower(), m.end(), len(raw), {}, False
    while i < n:
        while i < n and (raw[i] in WS or raw[i] == "/"):
            i += 1
        if i >= n or raw[i] == ">":
            break
        if raw[i] == "{":
            i = match_brace(raw, i)
            spread = True
            continue
        j = i
        while j < n and raw[j] not in WS and raw[j] not in "=/>":
            j += 1
        name = raw[i:j]
        if not name:
            i += 1
            continue
        i = j
        while i < n and raw[i] in WS:
            i += 1
        val = ""
        if i < n and raw[i] == "=":
            i += 1
            while i < n and raw[i] in WS:
                i += 1
            if i < n and raw[i] in "\"'":
                q = raw[i]
                k = raw.find(q, i + 1)
                k = n if k < 0 else k
                val, i = raw[i + 1:k], k + 1
            elif i < n and raw[i] == "{":
                k = match_brace(raw, i)
                val, i = raw[i:k], k
            else:
                k = i
                while k < n and raw[k] not in WS and raw[k] != ">":
                    k += 1
                val, i = raw[i:k], k
        attrs.setdefault(name.lower(), val)
    return tag, attrs, spread


def tags_in(text):
    """Yield (position, tag, attrs, has_spread, raw) for the tags this script inspects. HTML comments are skipped."""
    blanked = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    for m in TAG_START.finditer(blanked):
        raw = read_tag(blanked, m.start())
        if raw is None:
            continue
        tag, attrs, spread = parse_tag(raw)
        if tag:
            yield m.start(), tag, attrs, spread, raw


def viewport_findings(content):
    """Return (defect message or None, candidate message or None) for a viewport content value."""
    props = {}
    for part in re.split(r"[,;]", content):
        if "=" in part:
            k, v = part.split("=", 1)
            props[k.strip().lower()] = v.strip().lower()
    defect = cand = None
    if props.get("user-scalable") in ("no", "0"):
        defect = "viewport tag blocks pinch zoom (user-scalable=%s)" % props["user-scalable"]
    ms = props.get("maximum-scale")
    if ms is not None:
        if re.fullmatch(r"\d+(\.\d+)?|\.\d+", ms):
            if float(ms) < 2 and not defect:
                defect = "viewport tag limits zoom below 200%% (maximum-scale=%s)" % ms
        else:
            cand = "viewport maximum-scale value %r is not a number: browsers may ignore or misread it" % ms[:20]
    return defect, cand


def scan(paths):
    files = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.suffix.lower() in EXT and "node_modules" not in f.parts]
        elif p.is_file():
            files.append(p)
    findings, blob = [], ""

    def add(sev, f, n, rid, ref, msg, text=""):
        findings.append({"file": str(f), "line": n, "id": rid, "ref": ref, "severity": sev, "message": msg, "text": text.strip()[:140]})

    for f in files:
        try:
            data = f.read_bytes()
        except OSError:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
            add("CANDIDATE", f, 0, "not-utf8", "encoding", "file is not valid UTF-8: unreadable bytes were replaced before scanning")
        blob += "\n" + text
        for n, line in enumerate(text.splitlines(), 1):
            for rid, ref, rx, msg in COMPILED:
                if rx.search(line):
                    add("CANDIDATE", f, n, rid, ref, msg, line)
            for g in GRAD.finditer(line):
                cool = [h for h in HEX.findall(g.group(2)) if 225 <= hue_sat(h)[0] <= 300 and hue_sat(h)[1] >= 0.35]
                if len(cool) >= 2:
                    add("CANDIDATE", f, n, "gradient-indigo-violet", "Rule 1", "indigo to violet gradient: is it this product's colour or the default?", g.group(0))

        parsed = list(tags_in(text))
        label_for = {a.get("for") or a.get("htmlfor") for _p, t, a, _s, _r in parsed if t == "label"}
        label_for = {re.sub(r"^\{?[\"']?|[\"']?\}?$", "", v) for v in label_for if v}
        html_seen = False
        for pos, tag, attrs, spread, raw in parsed:
            ln = line_of(text, pos)
            if tag == "meta" and attrs.get("name", "").strip().lower() == "viewport":
                defect, cand = viewport_findings(attrs.get("content", ""))
                if defect:
                    add("DEFECT", f, ln, "zoom-disabled", "WCAG 1.4.4", defect, raw)
                if cand:
                    add("CANDIDATE", f, ln, "viewport-malformed", "WCAG 1.4.4", cand, raw)
            elif tag == "img":
                if "alt" not in attrs and not spread:
                    add("DEFECT", f, ln, "img-no-alt", "WCAG 1.1.1", "image with no alt attribute (use alt=\"\" if decorative)", raw)
            elif tag == "html" and not html_seen:
                html_seen = True
                lang = attrs.get("lang", attrs.get("xml:lang"))
                if (lang is None or lang.strip() == "") and not spread:
                    add("DEFECT", f, ln, "html-no-lang", "WCAG 3.1.1", "html element with no lang attribute" if lang is None else "html element with an empty lang attribute", raw)
            elif tag in ("input", "select", "textarea"):
                if attrs.get("type", "").strip("\"'{}").lower() in ("hidden", "submit", "button", "reset", "image") or spread:
                    continue
                named = any(k in attrs for k in ("aria-label", "aria-labelledby", "title"))
                if not named and attrs.get("id"):
                    named = re.sub(r"^\{?[\"']?|[\"']?\}?$", "", attrs["id"]) in label_for
                if not named:
                    before = text[max(0, pos - 400):pos].lower()
                    named = before.rfind("<label") > before.rfind("</label>")
                if not named:
                    add("CANDIDATE", f, ln, "control-no-label", "WCAG 4.1.2", "form control with no label found nearby: confirm it has an accessible name", raw)
            elif tag in ("div", "span"):
                if ("onclick" in attrs) and not ("role" in attrs and "tabindex" in attrs):
                    add("CANDIDATE", f, ln, "div-click", "Rule 83", "click handler on a div or span with no role and tabindex: confirm keyboard access", raw)
            elif tag == "button":
                pass
            elif tag == "form":
                add("CANDIDATE", f, ln, "form-element", "delivery", "form element: if saving or sending relies on submitting it, that is blocked in a frame without allow-forms", raw)

    def whole(rid, ref, msg):
        add("CANDIDATE", "(whole set)", 0, rid, ref, msg)

    if files:
        low = blob.lower()
        if re.search(r"intersectionobserver", low) and re.search(r"opacity:\s*0\b", low):
            whole("scroll-reveal", "Rule 73", "content starts hidden and waits for a scroll observer")
        if "mousemove" in low and "radial-gradient" in low:
            whole("cursor-light", "Rule 73", "cursor-following light effect")
        if re.search(r"animation:|transition:|@keyframes", low) and "prefers-reduced-motion" not in low:
            whole("no-reduced-motion", "Rule 76", "motion is used and no prefers-reduced-motion rule was found")
        if re.search(r"<button|<a\s|<input|<select", low) and "focus-visible" not in low and ":focus" not in low:
            whole("no-focus-style", "Rule 82", "interactive elements and no focus style found")
        if not re.search(r"loading|skeleton|aria-busy", low):
            whole("no-loading-state", "Rules 63-64", "no loading state found: fine if nothing loads")
        if not re.search(r"empty|no \w+ yet|nothing (here|to show)", low):
            whole("no-empty-state", "Rules 69-70", "no empty state found: fine if nothing can be empty")
        if not re.search(r"role=[\"']alert|\berror", low):
            whole("no-error-state", "Rules 45-46", "no error state found: fine if nothing can fail")
        root = re.search(r":root\s*\{([^}]*)\}", blob)
        if root and re.search(r"color-scheme:\s*dark", root.group(1)):
            whole("dark-default", "Section 0.1", "the default theme is dark: check it against the user's stated theme preference")
        if "prefers-color-scheme" not in low and "data-theme" not in low and "-theme=" not in low:
            whole("single-theme", "Section 0.1", "one colour scheme only: fine for a throwaway, check for anything used more than once")
        stripped = re.sub(r"--[\w-]+\s*:\s*[^;]+;", "", blob)
        n_hex = len(HEX.findall(stripped))
        if n_hex > 12:
            whole("literal-colours", "Rule 93", "%d colour literals outside token definitions" % n_hex)
    # delivery hazards are reported once per file and kind, with a count, so one habit does not flood the list
    merged, seen = [], {}
    for x in findings:
        if x["ref"] == "delivery":
            key = (x["file"], x["id"])
            if key in seen:
                seen[key]["count"] += 1
                continue
            x["count"] = 1
            seen[key] = x
        merged.append(x)
    for x in seen.values():
        if x["count"] > 1:
            x["message"] += " (%d places, first shown)" % x["count"]
    findings = merged
    defects = sum(1 for x in findings if x["severity"] == "DEFECT")
    return {"files": [str(f) for f in files], "defects": defects, "candidates": len(findings) - defects, "findings": findings}


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    unknown = [a for a in argv if a.startswith("--") and a not in OPTIONS]
    if unknown:
        print("ui_candidates: unknown option %s (known: %s)" % (unknown[0], ", ".join(sorted(OPTIONS))), file=sys.stderr)
        return 2
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    rep = scan(args)
    if not rep["files"]:
        print("ui_candidates: no interface files found in " + ", ".join(args), file=sys.stderr)
        return 2
    if "--json" in argv:
        text = json.dumps(rep, indent=1, ensure_ascii=True)
    else:
        out = ["ui_candidates: %d file(s), %d DEFECT, %d CANDIDATE to review in the render or the delivered frame" % (len(rep["files"]), rep["defects"], rep["candidates"])]
        for sev in ("DEFECT", "CANDIDATE"):
            for x in [y for y in rep["findings"] if y["severity"] == sev][:80]:
                where = "%s:%s" % (Path(x["file"]).name, x["line"]) if x["line"] else Path(x["file"]).name
                out.append("  %-9s %-22s %-11s %s  [%s]" % (sev, x["id"], x["ref"], x["message"], where))
        out.append("Candidates are prompts to look, not failures. Nothing here judges how the page looks.")
        text = "\n".join(out).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    from collections import Counter
    RECEIPT.update({"files": len(rep["files"]), "defects": rep["defects"], "candidates": rep["candidates"],
                    "defect_rules": dict(Counter(x["id"] for x in rep["findings"] if x["severity"] == "DEFECT")),
                    "candidate_rules": dict(Counter(x["id"] for x in rep["findings"] if x["severity"] == "CANDIDATE")),
                    "meaning": "completed means the scan ran; defects are listed here and fail the run only with --fail-on-defect"})
    return 1 if (rep["defects"] and "--fail-on-defect" in argv) else 0

# ---- forge result contract (references/results.md) --------------------------------------------------------------
# Every check prints one RECEIPT line on stderr before it exits, whatever happened, and writes it to --receipt FILE
# when given. status: completed (0), failed (1), usage_error (2), partial (3: an applicable check did not run or
# coverage is incomplete), runner_error (4: the tool could not do its job). Help and --version print no receipt.
# If --receipt FILE cannot be written, the product result is kept as product_status/product_exit and the run as a
# whole is a runner_error (exit 4): a result nobody can read back is not delivered.
STATUS_BY_EXIT = {0: "completed", 1: "failed", 2: "usage_error", 3: "partial", 4: "runner_error"}
RECEIPT = {}


def _contract(tool, main, argv):
    import json as _json
    argv = list(argv)
    path = None

    def emit(code, extra=None):
        rec = {"tool": tool, "version": VERSION, "status": STATUS_BY_EXIT.get(code, "runner_error"), "exit": code}
        rec.update(RECEIPT)
        if extra:
            rec.update(extra)
        if path:
            try:
                pathlib.Path(path).write_text(_json.dumps(rec, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            except OSError as e:
                rec.update({"product_status": rec["status"], "product_exit": code, "status": "runner_error", "exit": 4,
                            "receipt_error": "could not write %s: %s" % (path, e)})
                code = 4
        print("RECEIPT " + _json.dumps(rec, ensure_ascii=False, default=str), file=sys.stderr)
        return code

    if "--receipt" in argv:
        i = argv.index("--receipt")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            print(tool + ": --receipt needs a file path", file=sys.stderr)
            return emit(2, {"error": "--receipt needs a file path"})
        path = argv[i + 1]
        del argv[i:i + 2]
        sys.argv = [sys.argv[0]] + argv
    if any(a in ("-h", "--help", "--version") for a in argv):
        try:
            return main(argv) or 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 0
    try:
        code = main(argv)
        code = 0 if code is None else code
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 2)
    except BaseException as e:  # noqa: BLE001  any crash is a runner error, never a pass or a product failure
        RECEIPT.setdefault("error", repr(e)[:400])
        print("runner error: %r" % (e,), file=sys.stderr)
        code = 4
    return emit(code)


if __name__ == "__main__":
    sys.exit(_contract("ui_candidates", main, sys.argv[1:]))
