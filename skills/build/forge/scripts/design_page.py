#!/usr/bin/env python3
"""Render a forge design pack (docs/design.md) as one self-contained HTML page, with every Mermaid diagram drawn
as inline SVG, so it reads offline, in a sandboxed preview and after being downloaded from a chat.

Usage:
  python design_page.py DESIGN.md OUT.html [--title "Plant round: design"]
  python design_page.py --version          prints the forge version
  python design_page.py --help             prints this text

What it does
  - Converts the Markdown with python-markdown when it is installed, otherwise with a small built-in converter
    (headings, paragraphs, bullet and numbered lists, tables, block quotes, inline code, code blocks, bold, italics,
    links, images). Raw HTML in the Markdown is shown as text, never run. Only http, https, mailto and in-page
    links are kept. Nest lists with four spaces so both converters and GitHub agree.
  - Draws each ```mermaid block in headless Chromium (Python playwright) with Mermaid 11.17.2, twice: a light and a
    dark version, switched by the reader's prefers-color-scheme. Print uses the light one.
  - A paragraph straight after a diagram that starts with "Look at" (optionally in *italics*) becomes its caption.
    A diagram with no caption gets a warning.
  - The page has a contents list from the headings, embedded fonts (Hanken Grotesk, used for the diagrams too, so
    labels fit their boxes on any machine), and no scripts at all: a Content-Security-Policy forbids them.
    Local images are embedded; remote images are replaced by their alt text, with a warning.

Where Mermaid comes from
  ../assets/vendor/mermaid-11.17.2.min.js.gz (bundled, checked against a SHA-256). If that file is missing, the
  same version is fetched once with `npm pack` into ~/.cache/forge-mermaid (needs npm and registry access).

Exit codes
  0  page written, every diagram drawn
  1  page written, but at least one diagram has a Mermaid syntax error: each is named with Mermaid's message,
     and the page shows its source with the error in place of the drawing
  2  bad arguments, or DESIGN.md could not be read
  3  page written with each diagram's source shown as code instead of a drawing: NOT RUN, with the reason
     (no Python playwright, Chromium could not start, or Mermaid could not be found). Status: partial
  4  runner error: the tool itself crashed (a RECEIPT line on stderr says so)
Every run ends with a RECEIPT line on stderr (references/results.md).
"""
import base64
import datetime as dt
import gzip
import hashlib
import html
import os
import re
import secrets
import subprocess
import sys
import tarfile
from pathlib import Path
import pathlib

VERSION = "forge 3.3.2"
MERMAID_VERSION = "11.17.2"
MERMAID_SHA256 = "581ed7d74bd9048d0e3a91363927d72ef22942d7722546b27f7cc29e35390eb8"
ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "assets" / "vendor"
CACHE = Path(os.path.expanduser("~/.cache/forge-mermaid"))
FONT_FILES = [("400", "normal", "hanken-grotesk-latin-400-normal.woff2"),
              ("400", "italic", "hanken-grotesk-latin-400-italic.woff2"),
              ("700", "normal", "hanken-grotesk-latin-700-normal.woff2")]
FONT_STACK = '"Hanken Grotesk", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
MIN_SCALE = 0.72          # a diagram never shrinks below this share of its drawn width; past that it scrolls in its frame
TIMEOUT_MS = 20000        # per diagram, per theme
MAX_IMAGE = 2 * 1024 * 1024


class NotRun(Exception):
    """Diagrams cannot be drawn here. The page is still written, with the sources shown."""


def say(msg):
    print("design_page: " + msg)


def warn(msg):
    print("design_page: warning: " + msg, file=sys.stderr)


# ---------------------------------------------------------------- Mermaid themes
# Colours match the page's light and dark palettes below. Diagrams should not set their own colours.
COMMON = {
    "startOnLoad": False, "securityLevel": "strict", "theme": "base", "deterministicIds": True, "handDrawnSeed": 7,
    "fontFamily": FONT_STACK,
    "flowchart": {"htmlLabels": True, "curve": "basis", "padding": 12, "nodeSpacing": 40, "rankSpacing": 50, "useMaxWidth": True,
                  "wrappingWidth": 240},
    "sequence": {"mirrorActors": False, "useMaxWidth": True, "wrap": True, "width": 150, "actorMargin": 110, "messageMargin": 36,
                 "boxMargin": 8, "messageFontSize": 15, "noteFontSize": 14, "actorFontSize": 15},
    "er": {"useMaxWidth": True, "fontSize": 14},
    "state": {"useMaxWidth": True},
}
INK, INK_D = "#1f2328", "#e8e6e1"
THEMES = {
    "light": {
        "darkMode": False, "fontFamily": FONT_STACK, "background": "#ffffff",
        "primaryColor": "#eaf2f2", "primaryTextColor": INK, "primaryBorderColor": "#4d6a70",
        "secondaryColor": "#f2efe8", "secondaryTextColor": INK, "secondaryBorderColor": "#4d6a70",
        "tertiaryColor": "#f6f4ef", "tertiaryTextColor": INK, "tertiaryBorderColor": "#a39c8e",
        "mainBkg": "#eaf2f2", "nodeBorder": "#4d6a70", "nodeTextColor": INK, "textColor": INK, "titleColor": INK,
        "lineColor": "#4a525c", "defaultLinkColor": "#4a525c",
        "clusterBkg": "#f8f7f3", "clusterBorder": "#a39c8e", "edgeLabelBackground": "#ffffff",
        "noteBkgColor": "#fbf1cc", "noteTextColor": "#3b3315", "noteBorderColor": "#c2a547",
        "actorBkg": "#eaf2f2", "actorBorder": "#4d6a70", "actorTextColor": INK, "actorLineColor": "#9aa1aa",
        "signalColor": "#2b3138", "signalTextColor": INK,
        "labelBoxBkgColor": "#f2efe8", "labelBoxBorderColor": "#4d6a70", "labelTextColor": INK, "loopTextColor": INK,
        "activationBkgColor": "#d9e7e8", "activationBorderColor": "#4d6a70", "sequenceNumberColor": "#ffffff",
        "attributeBackgroundColorOdd": "#ffffff", "attributeBackgroundColorEven": "#f6f4ef",
        "stateBkg": "#eaf2f2", "stateLabelColor": INK, "transitionColor": "#4a525c", "transitionLabelColor": INK,
        "compositeBackground": "#f5f2ec", "altBackground": "#f5f2ec", "specialStateColor": "#2b3138",
    },
    "dark": {
        "darkMode": True, "fontFamily": FONT_STACK, "background": "#1b1e22",
        "primaryColor": "#1f3338", "primaryTextColor": INK_D, "primaryBorderColor": "#7fa9b0",
        "secondaryColor": "#2a2e34", "secondaryTextColor": INK_D, "secondaryBorderColor": "#7fa9b0",
        "tertiaryColor": "#23272c", "tertiaryTextColor": INK_D, "tertiaryBorderColor": "#5d646d",
        "mainBkg": "#1f3338", "nodeBorder": "#7fa9b0", "nodeTextColor": INK_D, "textColor": INK_D, "titleColor": INK_D,
        "lineColor": "#b3bac2", "defaultLinkColor": "#b3bac2",
        "clusterBkg": "#202327", "clusterBorder": "#5d646d", "edgeLabelBackground": "#1b1e22",
        "noteBkgColor": "#3a3320", "noteTextColor": "#f1e7c4", "noteBorderColor": "#8f7b3c",
        "actorBkg": "#1f3338", "actorBorder": "#7fa9b0", "actorTextColor": INK_D, "actorLineColor": "#6b737c",
        "signalColor": "#d5dade", "signalTextColor": INK_D,
        "labelBoxBkgColor": "#2a2e34", "labelBoxBorderColor": "#7fa9b0", "labelTextColor": INK_D, "loopTextColor": INK_D,
        "activationBkgColor": "#2a4248", "activationBorderColor": "#7fa9b0", "sequenceNumberColor": "#1b1e22",
        "attributeBackgroundColorOdd": "#23272c", "attributeBackgroundColorEven": "#1e2226",
        "stateBkg": "#1f3338", "stateLabelColor": INK_D, "transitionColor": "#b3bac2", "transitionLabelColor": INK_D,
        "compositeBackground": "#23272c", "altBackground": "#23272c", "specialStateColor": "#d5dade",
    },
}

RENDER_JS = """async ({items, themes, common, timeoutMs}) => {
  const out = items.map(() => ({}));
  const within = (p, what) => Promise.race([p, new Promise((_, no) =>
    setTimeout(() => no(new Error(what + ' took longer than ' + timeoutMs / 1000 + ' seconds')), timeoutMs))]);
  const text = e => String((e && (e.message || e.str)) || e);
  for (const [name, vars] of Object.entries(themes)) {
    mermaid.initialize(Object.assign({}, common, {themeVariables: vars, darkMode: !!vars.darkMode}));
    for (let i = 0; i < items.length; i++) {
      if (out[i].error) continue;
      try { await within(mermaid.parse(items[i]), 'Checking the diagram'); }
      catch (e) { out[i].error = text(e); continue; }
      try { out[i][name] = (await within(mermaid.render('mmd' + (i + 1) + name[0], items[i]), 'Drawing the diagram')).svg; }
      catch (e) { out[i].error = text(e); }
      document.querySelectorAll('body > :not(script)').forEach(n => n.remove());
    }
  }
  return out;
}"""


# ---------------------------------------------------------------- Mermaid: find, fetch, check
def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_mermaid():
    """Return (javascript, where it came from). Raise NotRun when it cannot be had."""
    problems = []
    for f in (VENDOR / ("mermaid-%s.min.js.gz" % MERMAID_VERSION), VENDOR / ("mermaid-%s.min.js" % MERMAID_VERSION)):
        if f.is_file():
            try:
                data = gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
            except OSError as e:
                problems.append("%s could not be read (%s)" % (f.name, e))
                continue
            if sha256(data) == MERMAID_SHA256:
                return data.decode("utf-8"), str(f)
            problems.append("%s is not the pinned Mermaid %s (checksum differs)" % (f.name, MERMAID_VERSION))
    cached = CACHE / ("mermaid-%s.min.js" % MERMAID_VERSION)
    if not cached.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        try:
            r = subprocess.run(["npm", "pack", "mermaid@" + MERMAID_VERSION, "--pack-destination", str(CACHE), "--loglevel=error"],
                               capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise NotRun("Mermaid is not bundled here and npm could not run (%s)" % e)
        tgz = CACHE / ("mermaid-%s.tgz" % MERMAID_VERSION)
        if r.returncode != 0 or not tgz.is_file():
            lines = [l for l in (r.stderr or r.stdout or "no output").strip().splitlines() if "complete log" not in l]
            why = next((l for l in lines if re.search(r"\b(code|404|E[A-Z]{4,})\b", l)), lines[0] if lines else "no output")
            raise NotRun("Mermaid is not bundled here and npm could not fetch mermaid@%s (%s)" % (MERMAID_VERSION, why.strip()[:200]))
        try:
            with tarfile.open(tgz, "r:gz") as t:   # read one member as bytes; nothing is extracted to disk by name
                member = t.extractfile("package/dist/mermaid.min.js")
                data = member.read() if member else b""
        except (tarfile.TarError, KeyError, OSError) as e:
            raise NotRun("the fetched Mermaid package could not be opened (%s)" % e)
        finally:
            tgz.unlink(missing_ok=True)
        if sha256(data) != MERMAID_SHA256:
            raise NotRun("the fetched Mermaid %s does not match the pinned checksum" % MERMAID_VERSION)
        cached.write_bytes(data)
    data = cached.read_bytes()
    if sha256(data) != MERMAID_SHA256:
        raise NotRun("%s does not match the pinned checksum; delete it and run again" % cached)
    for p in problems:
        warn(p)
    return data.decode("utf-8"), str(cached)


def font_css():
    rules = []
    for weight, style, name in FONT_FILES:
        f = VENDOR / "fonts" / name
        if not f.is_file():
            warn("font %s is missing from assets/vendor/fonts; using system fonts, so diagram labels may not fit "
                 "their boxes on other machines" % name)
            return ""
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        rules.append("@font-face{font-family:'Hanken Grotesk';font-style:%s;font-weight:%s;font-display:block;"
                     "src:url(data:font/woff2;base64,%s) format('woff2')}" % (style, weight, b64))
    return "\n".join(rules)


def draw(sources, fonts):
    """Draw every diagram in light and dark. Returns a list of dicts: {'light': svg, 'dark': svg} or {'error': msg}."""
    js, _source = load_mermaid()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise NotRun("Python playwright is not installed (pip install playwright, then: playwright install chromium)")
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:  # noqa: BLE001 - any launch failure means no browser here
                first = str(e).strip().splitlines()[0] if str(e).strip() else repr(e)
                raise NotRun("Chromium could not start (%s)" % first[:240])
            try:
                page = browser.new_page(viewport={"width": 1200, "height": 900})
                page.set_content("<!doctype html><html><head><meta charset='utf-8'><style>%s body{font-family:%s}"
                                 "</style></head><body></body></html>" % (fonts, FONT_STACK))
                page.evaluate("""async () => { for (const f of ['400 16px "Hanken Grotesk"', 'italic 400 16px "Hanken Grotesk"',
                                 '700 16px "Hanken Grotesk"']) { try { await document.fonts.load(f); } catch (e) {} }
                                 await document.fonts.ready; }""")
                page.add_script_tag(content=js)
                return page.evaluate(RENDER_JS, {"items": sources, "themes": THEMES, "common": COMMON, "timeoutMs": TIMEOUT_MS})
            finally:
                browser.close()
    except NotRun:
        raise
    except Exception as e:  # noqa: BLE001 - the driver itself failed
        detail = str(e).strip().splitlines()[0][:240] if str(e).strip() else repr(e)
        raise NotRun("the browser run failed (%s)" % detail)


# ---------------------------------------------------------------- SVG clean-up
SVG_NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")   # how SVG itself splits "1.5.25-3" into numbers


def compact_numbers(value):
    """Round every number in an SVG attribute to 2 decimals, keeping numbers that touch apart."""
    out, last = [], 0
    for m in SVG_NUMBER.finditer(value):
        between, tok = value[last:m.start()], m.group(0)
        if "." in tok and "e" not in tok.lower() and len(tok.split(".", 1)[1]) > 2:
            tok = ("%.2f" % float(tok)).rstrip("0").rstrip(".")
            if tok in ("-0", "+0", ""):
                tok = "0"
        if not between and out and out[-1][-1:] in "0123456789." and tok[:1] in "0123456789.":
            between = " "       # "1.5" then "25" must not become "1.525"
        out.append(between + tok)
        last = m.end()
    out.append(value[last:])
    return "".join(out)


def finish_svg(svg, label):
    """Make one Mermaid SVG safe to inline next to others and sized for the page. Returns (svg, natural width)."""
    svg = re.sub(r"<script\b.*?</script\s*>", "", svg, flags=re.S | re.I)
    svg = re.sub(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg, flags=re.I)
    svg = re.sub(r"((?:xlink:)?href\s*=\s*\")\s*javascript:[^\"]*\"", r'\1#"', svg, flags=re.I)
    m = re.match(r"\s*<svg\b([^>]*)>", svg)
    if not m:
        return svg, 600.0
    # Geometry comes out of Mermaid with up to 15 decimals (one rounded box can be 30 KB of path); 2 are plenty.
    svg = re.sub(r'(\s(?:d|points|transform|x|y|x1|y1|x2|y2|cx|cy|r|rx|ry|width|height)=")([^"]*)(")',
                 lambda a: a.group(1) + compact_numbers(a.group(2)) + a.group(3), svg)
    m = re.match(r"\s*<svg\b([^>]*)>", svg)
    attrs = m.group(1)
    rid = (re.search(r'(?<![\w-])id="([^"]+)"', attrs) or [None, "mmd"])[1]
    width = None
    mw = re.search(r"max-width:\s*([\d.]+)px", attrs)
    vb = re.search(r'viewBox="\s*[-\d.e]+[\s,]+[-\d.e]+[\s,]+([\d.e]+)[\s,]+([\d.e]+)\s*"', attrs)
    if mw:
        width = float(mw.group(1))
    elif vb:
        width = float(vb.group(1))
    width = width or 600.0
    attrs = re.sub(r'\s(?:style|width|height|role)="[^"]*"', "", attrs)
    attrs += ' width="100%%" role="img" aria-label="%s"' % html.escape(label, quote=True)
    svg = "<svg" + attrs + ">" + svg[m.end():]
    # Inner ids (edges, actors) repeat across diagrams and across the light and dark copies: prefix them.
    inner = {i for i in re.findall(r'(?<![\w-])id="([^"]+)"', svg) if i != rid and not i.startswith(rid)}
    if inner:
        mapping = {i: "%s-%s" % (rid, i) for i in inner}
        svg = re.sub(r'(?<![\w-])id="([^"]+)"', lambda x: 'id="%s"' % mapping.get(x.group(1), x.group(1)), svg)
        svg = re.sub(r"url\(#([^)]+)\)", lambda x: "url(#%s)" % mapping.get(x.group(1), x.group(1)), svg)
        svg = re.sub(r'((?:xlink:)?href=")#([^"]+)"', lambda x: '%s#%s"' % (x.group(1), mapping.get(x.group(2), x.group(2))), svg)
    return svg, width


# ---------------------------------------------------------------- Markdown: diagrams out first
FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([^`\s]*)[^`]*$")
CAPTION = re.compile(r"^\s*[*_]?\s*(look at|what to look at)\b", re.I)
HEAD_LINE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")


def extract_diagrams(text, token):
    """Pull ```mermaid blocks (and the caption paragraph after each) out of the Markdown.
    Returns (markdown with a placeholder line per diagram, list of diagram dicts)."""
    lines = text.split("\n")
    out, diagrams, heading, i = [], [], "the top of the file", 0
    while i < len(lines):
        line = lines[i]
        m = FENCE_OPEN.match(line)
        if not m:
            h = HEAD_LINE.match(line)
            if h:
                heading = h.group(2).strip()
            out.append(line)
            i += 1
            continue
        indent, fence, info = m.group(1), m.group(2), m.group(3).lower()
        close = re.compile(r"^\s*%s{%d,}\s*$" % (re.escape(fence[0]), len(fence)))
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            j += 1
        body = lines[i + 1:j]
        if info != "mermaid":
            out.extend(lines[i:j + 1])
            i = j + 1
            continue
        src = "\n".join(l[len(indent):] if l.startswith(indent) else l.lstrip() for l in body).strip("\n")
        k = j + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        caption = ""
        if k < len(lines) and CAPTION.match(lines[k]):
            cap = []
            while k < len(lines) and lines[k].strip():
                cap.append(lines[k].strip())
                k += 1
            caption = " ".join(cap)
            if len(caption) > 1 and caption[0] in "*_" and caption[-1] == caption[0]:
                caption = caption[1:-1].strip()
            next_i = k
        else:
            next_i = j + 1
        n = len(diagrams) + 1
        diagrams.append({"n": n, "src": src, "caption": caption, "line": i + 1, "heading": heading,
                         "kind": diagram_kind(src)})
        out.extend(["", indent + "%sN%dE" % (token, n), ""])
        i = next_i
    return "\n".join(out), diagrams


def diagram_kind(src):
    in_front = False
    for l in src.split("\n"):
        s = l.strip()
        if not s or s.startswith("%%"):
            continue
        if s == "---":
            in_front = not in_front
            continue
        if not in_front:
            return s.split()[0]
    return "empty"


def short_error(msg):
    """Mermaid's parser lists every token it would have accepted; keep the first few and what it got."""
    out = []
    for line in msg.strip().split("\n"):
        m = re.match(r"(Expecting )(.*?)(, got .*)$", line)
        if m and len(line) > 140:
            wanted = m.group(2).split(", ")
            line = m.group(1) + ", ".join(wanted[:4]) + (" or %d others" % (len(wanted) - 4) if len(wanted) > 4 else "") + m.group(3)
        out.append(line)
    return "\n".join(out)


def diagram_name(d, md_name):
    return 'diagram %d (%s, under "%s", %s line %d)' % (d["n"], d["kind"], d["heading"], md_name, d["line"])


# ---------------------------------------------------------------- Markdown: built-in converter
class MiniMarkdown:
    """A small, strict Markdown converter: everything is escaped first, then a known set of marks is applied."""
    LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+)(.*)$")
    HR = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
    TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")

    def convert(self, text):
        return self.blocks(text.split("\n"))

    @staticmethod
    def indent(line):
        return len(line) - len(line.lstrip(" "))

    def starts_block(self, lines, i):
        line = lines[i]
        return bool(HEAD_LINE.match(line) or FENCE_OPEN.match(line) or self.HR.match(line)
                    or line.lstrip().startswith(">") or self.LIST_ITEM.match(line) or self.table_at(lines, i))

    def table_at(self, lines, i):
        return ("|" in lines[i] and i + 1 < len(lines) and "-" in lines[i + 1]
                and bool(self.TABLE_SEP.match(lines[i + 1])) and "|" in lines[i + 1] + lines[i])

    def blocks(self, lines):
        out, i, n = [], 0, len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            m = FENCE_OPEN.match(line)
            if m:
                indent, fence, info = m.group(1), m.group(2), m.group(3)
                close = re.compile(r"^\s*%s{%d,}\s*$" % (re.escape(fence[0]), len(fence)))
                j = i + 1
                body = []
                while j < n and not close.match(lines[j]):
                    body.append(lines[j][len(indent):] if lines[j].startswith(indent) else lines[j].lstrip())
                    j += 1
                cls = ' class="language-%s"' % html.escape(info, quote=True) if info else ""
                out.append("<pre><code%s>%s\n</code></pre>" % (cls, html.escape("\n".join(body), quote=False)))
                i = j + 1
                continue
            h = HEAD_LINE.match(line)
            if h:
                lvl = len(h.group(1))
                out.append("<h%d>%s</h%d>" % (lvl, inline(h.group(2)), lvl))
                i += 1
                continue
            if self.HR.match(line):
                out.append("<hr>")
                i += 1
                continue
            if line.lstrip().startswith(">"):
                inner = []
                while i < n and lines[i].lstrip().startswith(">"):
                    inner.append(re.sub(r"^\s*> ?", "", lines[i]))
                    i += 1
                out.append("<blockquote>\n%s\n</blockquote>" % self.blocks(inner))
                continue
            if self.table_at(lines, i):
                i = self.table(lines, i, out)
                continue
            if self.LIST_ITEM.match(line):
                i = self.list_block(lines, i, out)
                continue
            para = [line.strip()]
            i += 1
            while i < n and lines[i].strip() and not self.starts_block(lines, i):
                para.append(lines[i].strip())
                i += 1
            out.append("<p>%s</p>" % inline(" ".join(para)))
        return "\n".join(out)

    @staticmethod
    def cells(line):
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|") and not s.endswith("\\|"):
            s = s[:-1]
        cells, cur, in_code = [], "", False
        k = 0
        while k < len(s):
            ch = s[k]
            if ch == "\\" and k + 1 < len(s) and s[k + 1] == "|":
                cur += "|"
                k += 2
                continue
            if ch == "`":
                in_code = not in_code
            if ch == "|" and not in_code:
                cells.append(cur.strip())
                cur = ""
            else:
                cur += ch
            k += 1
        cells.append(cur.strip())
        return cells

    def table(self, lines, i, out):
        head = self.cells(lines[i])
        aligns = []
        for c in self.cells(lines[i + 1]):
            c = c.strip()
            aligns.append("center" if c.startswith(":") and c.endswith(":") else "right" if c.endswith(":") else
                          "left" if c.startswith(":") else "")
        def row(cells, tag):
            tds = []
            for k in range(len(head)):
                a = aligns[k] if k < len(aligns) else ""
                style = ' style="text-align: %s;"' % a if a else ""
                tds.append("<%s%s>%s</%s>" % (tag, style, inline(cells[k]) if k < len(cells) else "", tag))
            return "<tr>\n" + "\n".join(tds) + "\n</tr>"
        rows = []
        i += 2
        while i < len(lines) and lines[i].strip() and "|" in lines[i]:
            rows.append(row(self.cells(lines[i]), "td"))
            i += 1
        out.append("<table>\n<thead>\n%s\n</thead>\n<tbody>\n%s\n</tbody>\n</table>" % (row(head, "th"), "\n".join(rows)))
        return i

    def list_block(self, lines, i, out):
        n = len(lines)
        first = self.LIST_ITEM.match(lines[i])
        base = len(first.group(1))
        ordered = first.group(2)[0].isdigit()
        start = int(re.match(r"\d+", first.group(2)).group(0)) if ordered else 1
        items, loose = [], False
        while i < n:
            m = self.LIST_ITEM.match(lines[i])
            if not m or len(m.group(1)) != base or m.group(2)[0].isdigit() != ordered:
                break
            offset = len(m.group(1)) + len(m.group(2)) + min(len(m.group(3)), 4)
            body = [m.group(4)]
            i += 1
            while i < n:
                line = lines[i]
                if not line.strip():
                    j = i
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and self.indent(lines[j]) > base:
                        body.extend([""] * (j - i))
                        i = j
                        loose = True
                        continue
                    if j < n:
                        nxt = self.LIST_ITEM.match(lines[j])
                        if nxt and len(nxt.group(1)) == base and nxt.group(2)[0].isdigit() == ordered:
                            loose = True
                            i = j
                    break
                if self.indent(line) > base:
                    body.append(line[min(offset, self.indent(line)):])
                    i += 1
                    continue
                if self.LIST_ITEM.match(line) or self.starts_block(lines, i):
                    break
                body.append(line.strip())   # a lazy continuation line
                i += 1
            items.append(body)
        tag = "ol" if ordered else "ul"
        attr = ' start="%d"' % start if ordered and start != 1 else ""
        lis = []
        for body in items:
            inner = self.blocks(body)
            if not loose and inner.startswith("<p>"):
                end = inner.index("</p>")
                inner = inner[3:end] + inner[end + 4:]
            lis.append("<li>%s</li>" % inner)
        out.append("<%s%s>\n%s\n</%s>" % (tag, attr, "\n".join(lis), tag))
        return i


def safe_url(raw):
    """raw is attribute text (may hold entities). Returns an escaped attribute value, or None to drop the link."""
    u = html.unescape(raw).strip()
    u = re.sub(r"[\x00-\x20\x7f]", "", u)
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", u)
    if scheme and scheme.group(1).lower() not in ("http", "https", "mailto"):
        return None
    return html.escape(u, quote=True)


def inline(text):
    """Escape a line of Markdown, then apply code, links, images, bold and italics."""
    store = []

    def keep(s):
        store.append(s)
        return "\x00%d\x00" % (len(store) - 1)

    out, k = "", 0
    while k < len(text):            # code spans first: their contents are never touched
        if text[k] == "`":
            run = len(re.match(r"`+", text[k:]).group(0))
            end = text.find("`" * run, k + run)
            while end != -1 and end + run < len(text) and text[end + run] == "`":
                end = text.find("`" * run, end + run + 1)
            if end != -1:
                out += keep("<code>%s</code>" % html.escape(text[k + run:end].strip(), quote=False))
                k = end + run
                continue
            out += "`" * run
            k += run
            continue
        out += text[k]
        k += 1
    out = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>~<])", lambda m: keep(html.escape(m.group(1))), out)
    out = html.escape(out, quote=True)
    out = out.replace("&#x27;", "'")

    def image(m):
        alt, src = m.group(1), m.group(2)
        url = safe_url(src)
        title = ' title="%s"' % m.group(3) if m.group(3) else ""
        return keep('<img alt="%s" src="%s"%s>' % (alt, url or "", title)) if url else alt

    url_pat = r"((?:[^()\s]|\([^()\s]*\))+)"     # a URL, allowing one level of balanced brackets
    out = re.sub(r"!\[([^\]]*)\]\(\s*" + url_pat + r"(?:\s+&quot;(.*?)&quot;)?\s*\)", image, out)

    def link(m):
        url = safe_url(m.group(2))
        title = ' title="%s"' % m.group(3) if m.group(3) else ""
        if not url:
            warn("a link to %r was removed: only http, https, mailto and in-page links are kept" % html.unescape(m.group(2))[:80])
            return m.group(1)
        return keep('<a href="%s"%s>' % (url, title)) + m.group(1) + keep("</a>")

    out = re.sub(r"\[([^\]]+)\]\(\s*" + url_pat + r"(?:\s+&quot;(.*?)&quot;)?\s*\)", link, out)
    out = re.sub(r"&lt;((?:https?://|mailto:)[^\s<>]+?)&gt;",
                 lambda m: keep('<a href="%s">%s</a>' % (safe_url(m.group(1)), m.group(1))), out)
    out = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"(?<!\w)_(?=[^\s_])(.+?)(?<=[^\s_])_(?!\w)", r"<em>\1</em>", out)
    while "\x00" in out:
        new = re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], out)
        if new == out:
            break
        out = new
    return out


def to_html(md_text):
    """Returns (html, which converter)."""
    try:
        import markdown  # noqa: WPS433
    except ImportError:
        return MiniMarkdown().convert(md_text), "built-in converter"
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"], output_format="html")
    for reg, name in ((md.preprocessors, "html_block"), (md.inlinePatterns, "html")):
        try:
            reg.deregister(name)      # raw HTML in the Markdown stays text
        except (KeyError, ValueError):
            pass
    return md.convert(md_text), "python-markdown %s" % getattr(markdown, "__version__", "")


# ---------------------------------------------------------------- page assembly
def label_tables(body):
    """Give each cell of a table with 3 or more columns its column name, so phones can show rows as cards."""
    def one(m):
        t = m.group(0)
        heads = [html.unescape(re.sub(r"<[^>]+>", "", h)).strip() for h in re.findall(r"<th\b[^>]*>(.*?)</th>", t, flags=re.S)]
        if len(heads) < 3:
            return t

        def row(rm):
            k = [0]

            def cell(cm):
                label = heads[k[0]] if k[0] < len(heads) else ""
                k[0] += 1
                return '<td data-label="%s"%s>' % (html.escape(label, quote=True), cm.group(1))
            return re.sub(r"<td\b([^>]*)>", cell, rm.group(0))
        t = re.sub(r"<tr>.*?</tr>", row, t, flags=re.S)
        return t.replace('<div class="table-wrap">', '<div class="table-wrap stack">', 1)
    return re.sub(r'<div class="table-wrap"><table>.*?</table></div>', one, body, flags=re.S)


def slugify(text):
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.U)
    return re.sub(r"[\s_-]+", "-", s).strip("-")[:64]


def headings_and_toc(body, reserved):
    used, toc = set(reserved), []

    def repl(m):
        level, inner = m.group(1), m.group(3)
        text = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        base = slugify(text) or "section"
        slug, k = base, 2
        while slug in used:
            slug, k = "%s-%d" % (base, k), k + 1
        used.add(slug)
        if level in "23":
            toc.append((int(level), slug, html.escape(text)))
        return '<h%s id="%s">%s</h%s>' % (level, slug, inner, level)

    body = re.sub(r"<h([1-6])(\s[^>]*)?>(.*?)</h\1>", repl, body, flags=re.S)
    return body, toc


def toc_html(toc):
    if not toc:
        return ""
    items = []
    for level, slug, text in toc:
        items.append('<li class="l%d"><a href="#%s">%s</a></li>' % (level, slug, text))
    return '<ol class="toc-list">%s</ol>' % "".join(items)


def fix_links_and_images(body, base_dir):
    def a(m):
        url = safe_url(m.group(1))
        if url is None:
            warn("a link to %r was removed: only http, https, mailto and in-page links are kept" % html.unescape(m.group(1))[:80])
            return '<a class="dropped"'
        return '<a href="%s"' % url
    body = re.sub(r'<a href="([^"]*)"', a, body)

    def img(m):
        tag = m.group(0)
        src = html.unescape((re.search(r'\ssrc="([^"]*)"', tag) or [None, ""])[1])
        alt = (re.search(r'\salt="([^"]*)"', tag) or [None, ""])[1]
        if src.startswith("data:image/") and re.match(r"data:image/(png|jpeg|gif|webp|svg\+xml)[;,]", src):
            return tag
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", src) and src:
            f = (base_dir / src).resolve()
            types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                     ".webp": "image/webp", ".svg": "image/svg+xml"}
            if f.is_file() and f.suffix.lower() in types and f.stat().st_size <= MAX_IMAGE:
                data = "data:%s;base64,%s" % (types[f.suffix.lower()], base64.b64encode(f.read_bytes()).decode("ascii"))
                return re.sub(r'\ssrc="[^"]*"', ' src="%s"' % data, tag)
            warn("image %r was not embedded (missing, not png/jpg/gif/webp/svg, or over 2 MB); its alt text is shown" % src)
        else:
            warn("image %r is remote; the page loads nothing from outside, so its alt text is shown" % src)
        return '<span class="img-missing">[image: %s]</span>' % (alt or "no description")
    return re.sub(r"<img\b[^>]*>", img, body)


CSS = """
:root{color-scheme:light dark;--bg:#fbfaf7;--text:#1f2328;--muted:#5b616a;--rule:#e2ded5;--surface:#f3f1ec;
--fig:#ffffff;--code:#efece5;--accent:#1d5f6b;--note-bg:#fbefd2;--note-text:#5e4300;--bad-bg:#fbe4e1;--bad-text:#8a1c12;
--body:"Hanken Grotesk",system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}
@media (prefers-color-scheme:dark){:root{--bg:#141619;--text:#e8e6e1;--muted:#a4a9b0;--rule:#2e3237;--surface:#1b1e22;
--fig:#1b1e22;--code:#22262b;--accent:#82c4cf;--note-bg:#3a3014;--note-text:#f3dfa4;--bad-bg:#3d1c19;--bad-text:#ffc9c2}}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:400 17px/1.65 var(--body);font-kerning:normal;
  -webkit-font-smoothing:antialiased}
.skip{position:absolute;left:-9999px;top:8px;background:var(--text);color:var(--bg);padding:8px 12px;border-radius:6px;z-index:2}
.skip:focus{left:16px}
.layout{max-width:1320px;margin:0 auto;padding:28px 16px 64px}
main{max-width:780px;min-width:0;margin:0 auto}
.toc-side{display:none}
@media (min-width:1100px){
  .layout{display:grid;grid-template-columns:232px minmax(0,1fr);gap:48px;padding-top:48px}
  main{margin:0;max-width:1000px}
  .doc>:not(.diagram):not(.table-wrap),.doc-foot,main>.note{max-width:780px}
  .toc-side{display:block;position:sticky;top:32px;align-self:start;max-height:calc(100vh - 64px);overflow:auto;
    font-size:14px;line-height:1.4;padding-right:8px}
  .toc-top{display:none}
}
.toc-h{font-weight:700;margin:0 0 10px;font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.toc-list{list-style:none;margin:0;padding:0}
.toc-list li{margin:0}
.toc-list a{display:block;padding:4px 0;color:var(--muted);text-decoration:none}
.toc-list a:hover{color:var(--text);text-decoration:underline}
.toc-list .l3 a{padding-left:14px;font-size:.94em}
.toc-top{margin:4px 0 28px;border:1px solid var(--rule);border-radius:10px;padding:0 14px;background:var(--surface)}
.toc-top summary{cursor:pointer;font-weight:700;padding:11px 0;min-height:44px;display:flex;align-items:center}
.toc-top .toc-list{padding:0 0 12px;font-size:15px}
.toc-top .toc-list a{padding:7px 0}
h1,h2,h3,h4{line-height:1.22;font-weight:700;letter-spacing:-.005em;scroll-margin-top:16px}
h1{font-size:clamp(1.85rem,6vw,2.45rem);line-height:1.12;margin:0 0 .5em;letter-spacing:-.015em}
h2{font-size:1.5rem;margin:2.4em 0 .6em;padding-top:1em;border-top:1px solid var(--rule)}
h3{font-size:1.17rem;margin:2em 0 .45em}
h4{font-size:1rem;margin:1.6em 0 .35em}
p,ul,ol,dl{margin:0 0 1em}
ul,ol{padding-left:1.4em}
li{margin:.25em 0}
li>ul,li>ol{margin:.25em 0 .4em}
a{color:var(--accent);text-underline-offset:2px;text-decoration-thickness:1px}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
a.dropped{color:inherit;text-decoration:underline dotted}
strong{font-weight:700}
hr{border:0;border-top:1px solid var(--rule);margin:2em 0}
code{font-family:var(--mono);font-size:.86em;background:var(--code);padding:.08em .32em;border-radius:4px;overflow-wrap:anywhere}
pre{background:var(--code);padding:14px 16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.5;margin:0 0 1.2em}
pre code{background:none;padding:0;font-size:inherit;overflow-wrap:normal;white-space:pre}
blockquote{margin:0 0 1.2em;padding:2px 0 2px 16px;border-left:3px solid var(--accent)}
blockquote p:last-child{margin-bottom:0}
.table-wrap{overflow-x:auto;margin:0 0 1.3em;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:15px;line-height:1.45}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--rule)}
th{font-weight:700;border-bottom:2px solid var(--rule);white-space:nowrap}
td code{font-size:.84em;overflow-wrap:break-word}
@media (max-width:640px){.stack table,.stack tbody,.stack tr,.stack td{display:block;width:100%}
  .stack thead{position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden}
  .stack tr{border:1px solid var(--rule);border-radius:8px;padding:6px 12px;margin:0 0 10px;background:var(--fig)}
  .stack td{border:0;padding:5px 0}.stack td:empty{display:none}
  .stack td::before{content:attr(data-label);display:block;font-size:12px;font-weight:700;letter-spacing:.03em;color:var(--muted)}}
figure.diagram{margin:1.5em 0 2em}
.fig-panel{background:var(--fig);border:1px solid var(--rule);border-radius:10px;padding:16px;overflow-x:auto}
.mm svg{display:block;margin:0 auto;width:100%;height:auto;max-width:var(--w);min-width:min(var(--w),var(--minw))}
.mm-dark{display:none}
@media (prefers-color-scheme:dark){.mm-light{display:none}.mm-dark{display:block}}
.scroll-hint{display:none;margin:6px 0 0;font-size:13px;color:var(--muted)}
figcaption{margin-top:8px;font-size:15px;line-height:1.5;color:var(--muted)}
figcaption b{color:var(--text)}
details.src{margin-top:6px;font-size:14px}
details.src summary{cursor:pointer;color:var(--muted);padding:6px 0;display:inline-block}
details.src pre{margin-top:6px}
.note{padding:12px 14px;border-radius:8px;background:var(--note-bg);color:var(--note-text);margin:0 0 1.2em;font-size:15px}
.note.bad{background:var(--bad-bg);color:var(--bad-text)}
.note code{background:transparent;padding:0}
.note p{margin:0 0 6px}
.note pre.err{background:transparent;padding:0;margin:0;font-size:13px;white-space:pre-wrap;color:inherit}
.fig-panel pre{margin:0}
.img-missing{color:var(--muted);font-style:italic}
img{max-width:100%;height:auto}
.doc-foot{margin-top:4em;padding-top:1em;border-top:1px solid var(--rule);font-size:13px;color:var(--muted)}
@media (max-width:520px){body{font-size:16px}.fig-panel{padding:12px}th,td{padding:7px 8px}table{font-size:14px}
  h2{font-size:1.32rem}}
@media print{body{background:#fff;color:#000}.toc-side,.toc-top,.skip,details.src{display:none!important}
  .layout{display:block;padding:0}.mm-light{display:block!important}.mm-dark{display:none!important}
  .fig-panel{border-color:#ccc;break-inside:avoid}a{color:inherit}}
"""


def scroll_hint_css(n, minw):
    """Show "scroll sideways" only at widths where the diagram's smallest size is wider than its frame.
    Frame inner width = main width - 34 (16 px padding and 1 px border a side). Below 1100 px main is
    min(viewport - 32, 780); from 1100 px the contents list takes 232 + 48 px and main is at most 1000."""
    rule = "#figure-%d .scroll-hint{display:block}" % n
    if minw > 1000 - 34:
        return rule
    if minw > 780 - 34:
        return "@media (max-width:%dpx){%s}" % (max(1100, minw + 32 + 280 + 34) - 1, rule)
    return "@media (max-width:%dpx){%s}" % (minw + 32 + 34 - 1, rule)


def figure_html(d, result, why_not):
    n, cap = d["n"], d["caption"]
    cap_html = inline(cap) if cap else ""
    label = "Figure %d. %s" % (n, re.sub(r"[*_`]", "", cap)) if cap else "Figure %d" % n
    src_block = '<pre><code class="language-mermaid">%s\n</code></pre>' % html.escape(d["src"], quote=False)
    parts = ['<figure class="diagram" id="figure-%d">' % n]
    css = ""
    if result and "light" in result and "dark" in result:
        light, w = finish_svg(result["light"], label)
        dark, _ = finish_svg(result["dark"], label)
        minw = int(round(min(w, w * MIN_SCALE)))
        style = "--w:%dpx;--minw:%dpx" % (round(w), minw)
        parts.append('<div class="fig-panel"><div class="mm mm-light" style="%s">%s</div>'
                     '<div class="mm mm-dark" style="%s">%s</div></div>' % (style, light, style, dark))
        parts.append('<p class="scroll-hint">This diagram is wide: scroll sideways inside its frame to see all of it.</p>')
        css = scroll_hint_css(n, minw)
        parts.append('<figcaption><b>Figure %d.</b> %s</figcaption>' % (n, cap_html))
        parts.append('<details class="src"><summary>Mermaid source</summary>%s</details>' % src_block)
    elif result and "error" in result:
        msg = short_error(result["error"])
        m = re.search(r"line (\d+)", msg)
        where = " The problem is on line %s below." % m.group(1) if m else ""
        lines = d["src"].split("\n")
        numbered = "\n".join("%*d  %s" % (len(str(len(lines))), i + 1, l) for i, l in enumerate(lines))
        parts.append('<div class="fig-panel"><div class="note bad"><p>This diagram has a Mermaid syntax error, so it was '
                     'not drawn.%s Mermaid says:</p><pre class="err">%s</pre></div><pre><code class="language-mermaid">%s\n'
                     '</code></pre></div>' % (where, html.escape(msg, quote=False), html.escape(numbered, quote=False)))
        parts.append('<figcaption><b>Figure %d.</b> %s</figcaption>' % (n, cap_html))
    else:
        parts.append('<div class="fig-panel"><p class="note">Not drawn here: %s. The Mermaid source is below; GitHub and '
                     'editors with a Mermaid preview draw it.</p>%s</div>' % (html.escape(why_not or "no browser"), src_block))
        parts.append('<figcaption><b>Figure %d.</b> %s</figcaption>' % (n, cap_html))
    parts.append("</figure>")
    return "".join(parts), css


def build_page(title, body, toc, fonts, extra_css, status_note, foot):
    toc_list = toc_html(toc)
    side = '<nav class="toc-side" aria-label="Contents"><p class="toc-h">Contents</p>%s</nav>' % toc_list if toc_list else ""
    top = '<details class="toc-top"><summary>Contents</summary><nav aria-label="Contents">%s</nav></details>' % toc_list if toc_list else ""
    if top and "</h1>" in body:
        body = body.replace("</h1>", "</h1>" + top, 1)
    elif top:
        body = top + body
    csp = ("default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; "
           "base-uri 'none'; form-action 'none'")
    return ("<!doctype html>\n<html lang=\"en-AU\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"%s\">\n"
            "<meta name=\"referrer\" content=\"no-referrer\">\n<meta name=\"color-scheme\" content=\"light dark\">\n"
            "<meta name=\"generator\" content=\"%s design_page.py\">\n<title>%s</title>\n<style>\n%s\n%s\n%s\n</style>\n</head>\n"
            "<body>\n<a class=\"skip\" href=\"#doc\">Skip to the document</a>\n<div class=\"layout\">\n%s\n"
            "<main id=\"doc\">\n%s<article class=\"doc\">\n%s\n</article>\n<footer class=\"doc-foot\">%s</footer>\n</main>\n"
            "</div>\n</body>\n</html>\n") % (csp, VERSION, html.escape(title), fonts, CSS, extra_css, side,
                                             status_note, body, foot)


# ---------------------------------------------------------------- main
def parse_args(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        sys.exit(0)
    if "--version" in argv:
        print(VERSION)
        sys.exit(0)
    pos, title, i = [], None, 0
    while i < len(argv):
        a = argv[i]
        if a == "--title":
            if i + 1 >= len(argv) or not argv[i + 1].strip():
                print("design_page: --title needs a value", file=sys.stderr)
                sys.exit(2)
            title = argv[i + 1]
            i += 2
            continue
        if a.startswith("--title="):
            title = a.split("=", 1)[1]
        elif a.startswith("-"):
            print("design_page: unknown option %s (see --help)" % a, file=sys.stderr)
            sys.exit(2)
        else:
            pos.append(a)
        i += 1
    if len(pos) != 2:
        print("design_page: give the Markdown file and the HTML file to write, e.g.\n"
              "  python design_page.py docs/design.md docs/design.html", file=sys.stderr)
        sys.exit(2)
    return Path(pos[0]), Path(pos[1]), title


def main(argv):
    src_path, out_path, title = parse_args(argv)
    try:
        text = src_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, UnicodeDecodeError) as e:
        print("design_page: cannot read %s (%s)" % (src_path, e), file=sys.stderr)
        return 2
    if out_path.resolve() == src_path.resolve():
        print("design_page: the output would overwrite the Markdown; give another file name", file=sys.stderr)
        return 2
    token = "FORGEFIG" + secrets.token_hex(4).upper().replace("E", "Q")
    md_text, diagrams = extract_diagrams(text, token)
    md_name = src_path.name

    for d in diagrams:
        if not d["caption"]:
            warn("%s has no caption. Add a line right below it that starts \"Look at\"." % diagram_name(d, md_name))
        if re.search(r"(?<![\w-])(fill|color|stroke)\s*:", d["src"]):
            warn("%s sets its own colours; they stay the same in dark mode. Prefer shapes and dashed lines." % diagram_name(d, md_name))
        if "%%{" in d["src"]:
            warn("%s carries a Mermaid init directive; the page's light and dark themes may not apply to it." % diagram_name(d, md_name))

    fonts = font_css()
    results, why_not = [None] * len(diagrams), None
    if diagrams:
        try:
            results = draw([d["src"] for d in diagrams], fonts)
        except NotRun as e:
            why_not = str(e)

    body, converter = to_html(md_text)
    figure_css = []
    for d, r in zip(diagrams, results):
        fig, css = figure_html(d, r, why_not)
        figure_css.append(css)
        pat = re.compile(r"(?:<p>|<pre><code>)?\s*%sN%dE\s*(?:</p>|\n?</code></pre>)?" % (token, d["n"]))
        body, count = pat.subn(lambda _m, f=fig: f, body, count=1)
        if not count:
            body += fig
    body = re.sub(r"<table>", '<div class="table-wrap"><table>', body)
    body = re.sub(r"</table>", "</table></div>", body)
    body = label_tables(body)
    body = fix_links_and_images(body, src_path.resolve().parent)
    body, toc = headings_and_toc(body, {"figure-%d" % d["n"] for d in diagrams} | {"doc"})
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.S)
    if not title:
        title = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else src_path.stem
    if not h1:
        body = "<h1>%s</h1>\n%s" % (html.escape(title), body)

    errors = [(d, r["error"]) for d, r in zip(diagrams, results) if r and "error" in r]
    drawn = sum(1 for r in results if r and "light" in r)
    status = ""
    if why_not:
        status = ('<p class="note">The diagrams in this page were not drawn: %s. Each one shows its Mermaid source '
                  'instead. Run scripts/design_page.py where Python playwright and Chromium work to draw them.</p>\n'
                  % html.escape(why_not))
    elif errors:
        status = ('<p class="note bad">%d of %d diagrams have a Mermaid syntax error and are shown as source: %s.</p>\n'
                  % (len(errors), len(diagrams), ", ".join('<a href="#figure-%d">figure %d</a>' % (d["n"], d["n"]) for d, _ in errors)))
    today = dt.date.today()
    foot = ("Rendered from %s on %d %s by forge design_page.py (%s) with %s. %s No scripts; fonts and diagrams are inside "
            "this file, so it reads offline. The Markdown file is the source to edit." % (
                html.escape(md_name), today.day, today.strftime("%b %Y"), VERSION, html.escape(converter),
                ("Mermaid %s drew %d of %d diagrams, in light and dark." % (MERMAID_VERSION, drawn, len(diagrams))) if diagrams else "No diagrams."))
    page = build_page(title, body, toc, fonts, "\n".join(c for c in figure_css if c), status, foot)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    size = "%d KB" % round(len(page.encode("utf-8")) / 1024)
    import hashlib as _hl
    RECEIPT.update({"source": md_name, "page": str(out_path), "page_sha256": _hl.sha256(page.encode("utf-8")).hexdigest(),
                    "page_meaning": "the design pack as HTML; diagrams drawn as inline SVG where 'diagrams_drawn' says so, Mermaid source otherwise",
                    "diagrams": len(diagrams), "diagrams_drawn": drawn,
                    "diagrams_with_errors": [d["n"] for d, _ in errors], "diagrams_as_source_only": len(diagrams) if why_not else len(errors),
                    "not_drawn_reason": why_not or None})

    if why_not:
        print("NOT RUN: diagrams not drawn: %s. Wrote %s (%s) with each diagram's Mermaid source shown instead."
              % (why_not, out_path, size), file=sys.stderr)
        return 3
    if errors:
        for d, msg in errors:
            msg = short_error(msg)
            m = re.search(r"line (\d+)", msg)
            where = " (that is %s line %d)" % (md_name, d["line"] + int(m.group(1))) if m else ""
            print("design_page: %s has a syntax error%s. Mermaid says:\n  %s" % (
                diagram_name(d, md_name), where, msg.replace("\n", "\n  ")), file=sys.stderr)
        say("wrote %s (%s), but %d of %d diagrams were not drawn" % (out_path, size, len(errors), len(diagrams)))
        return 1
    if not diagrams:
        warn("no ```mermaid blocks found in %s" % md_name)
        say("wrote %s (%s): no diagrams; Markdown by %s" % (out_path, size, converter))
        return 0
    say("wrote %s (%s): %d of %d diagrams drawn, light and dark; Markdown by %s" % (out_path, size, drawn, len(diagrams), converter))
    return 0

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
    sys.exit(_contract("design_page", main, sys.argv[1:]))
