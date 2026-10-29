#!/usr/bin/env python3
"""Capture a page in every declared state, theme and width, and lay the frames out on one contact sheet.

Usage:
  python state_gallery.py STATES.json [--page PAGE] [--out DIR] [--template FILE]
                          [--max-image-width 1280] [--image-scale 1] [--quality 70] [--encoding base64|hex]
                          [--max-frames 240] [--no-sheets] [--dry-run] [--fail-on-problems] [--json]
  python state_gallery.py --compare OLD_gallery.json NEW_gallery.json [--json]

STATES.json (one JSON object; paths are relative to the folder the file is in):
  {"page": "app.html",                       an HTML file or an http(s) address; --page overrides it
   "title": "optional heading for the sheet",
   "widths": [390, 1280],                     whole numbers 240 to 3840, or {"width": 390, "height": 844}
   "themes": [{"name": "paper", "set": "html@data-theme=paper"},     optional; leave out to capture
              {"name": "ember", "set": "html@data-theme=ember"}],    the page as loaded
   "settle_ms": 350,                          optional, 0 to 10000: how long the page must be still
   "states": [
     {"name": "empty", "steps": []},
     {"name": "populated", "steps": ["click:#load-demo", "expect-count:.row=8"],
      "shows": "one line on what a person should see here"},
     {"name": "loading", "route_delay": ["**/api/**"]},
     {"name": "server down", "route_fail": ["**/api/**"]},
     {"name": "busy", "route_delay": [{"url": "**/api/items/*/adjust", "method": "POST"}],
      "steps": ["click:.plus"], "scroll_to": ".row", "page": "http://127.0.0.1:8181/"}]}

  A theme's "set" is SELECTOR@ATTR=VALUE (or a list of them), applied after the page loads and again
  after a reload: step. A theme may also carry "steps", for pages that switch theme with a control.
  Steps use the grammar of delivery_check.py:
    click:SEL  fill:SEL=VALUE  check:SEL  press:SEL=KEY  expect:SEL=TEXT  expect-attr:SEL@ATTR=VAL
    expect-count:SEL=N  expect-gone:SEL  expect-focus:SEL  reload:  wait:MS
  route_fail aborts matching requests, so an error state can be shown with a healthy server.
  route_delay holds matching requests until the frame has been captured, so a loading or busy state
  can be shown. An entry is a glob ("*" stops at "/", "**" does not) or {"url": GLOB, "method": "POST"}.
  The page's own document is never failed or held. A state may name its own "page" (for example a
  second server with an empty data file) and a "scroll_to" selector to bring into view before the shot.

What it does. For each state, theme and width: a fresh browser context, load, apply the theme, run
the steps, wait until the page is still, measure, screenshot. It writes into --out (default: a
folder called gallery beside STATES.json):
  gallery.html   one self-contained page: states down the side, widths and themes across the top,
                 each frame captioned with its measured facts, problems marked in words
  gallery.json   every measured fact, for --compare and for reading
  frames/*.png   the captures at full size, for looking at one frame closely
  sheets/*.png   one picture per state and width, every theme together at half size with its
                 captions, for looking at a whole state
Pictures left in frames/ and sheets/ by an earlier run under other state names are not removed.

How big gallery.html gets. Every frame is embedded in it as a WebP picture, and the size is printed
when it is written. Eighty frames of one real app came to about 2.4 MB with the wide frames embedded
1024 px wide, and to under 0.9 MB with the three options below. They bring the size down
at the cost of sharpness when a frame is opened: --image-scale 0.7 embeds every frame at that
fraction of its captured size (0.25 to 1); --max-image-width 720 caps the wide frames only;
--quality 30 compresses harder (30 to 95). The pictures in frames/ always stay at full size, and
the sheet says beside an opened frame what percent of the captured size it is showing.

Measured per frame (facts, written beside the frame):
  - whether every step passed. A state whose step failed was NOT REACHED: it is shown as a labelled
    empty frame, never left out, and nothing is measured for it
  - sideways overflow of the document, in pixels
  - text elements that are cut off (hidden or clipped overflow smaller than their content)
  - lowest text contrast and how many elements are below WCAG 1.4.3 AA (4.5, or 3 for large text)
  - pointer targets under 24 by 24 CSS pixels with no spacing exception (WCAG 2.5.8 geometry)
  - console errors written by the page and uncaught page errors
  - requests that failed (not counting the ones this script aborted or held itself), and requests
    answered with a server error (500 and above) or with any error for a page, script, style sheet,
    image or font
A frame "has a measured problem" when it was not reached or any of those counts is above zero.
Reported but not counted as a problem: a data request answered 400 to 499 (that is how a server
refuses invalid input, and a refusal state is meant to cause one), targets under 44 by 44, and text
over an image or gradient that could not be measured.

What it cannot tell. The facts are aids. A frame with no measured problem can still be wrong: a
blank empty state, a weak hierarchy, a layout that suits no task. The sheet exists so that a person
looks. Hover states are not captured: the pointer is parked in the top left corner before each shot,
so that a hover style left by the last click is not mistaken for part of the state. Focus is captured
where a step put it. An emulated width is not a device. --compare compares measured facts only; pixel
comparison is out of scope, so two frames with identical facts can look different.

Steps must not change stored data, or later frames of the same state see something different. Use a
throwaway data file, and states that end where they began.

Exit codes: 0 the gallery was built (or the comparison ran, or --dry-run found the file valid).
1 with --fail-on-problems when any frame has a measured problem. 2 bad arguments or a bad states
file. 3 could not run (prints NOT RUN): Playwright or Chromium missing, or the page did not load.
These legacy process exits are retained. The receipt is authoritative: completed, partial,
not-applicable, failed or runner-error. A built gallery can exit 0 while its receipt is failed
or partial. Dry-run is validation only; comparison is stored facts only. Missing capture/sheet
coverage is partial unless a measured defect is known. Final gallery.json includes the receipt
and output inventory after the sheet attempt; late errors preserve observed facts separately.
"""
import base64
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

FLAGS = {"--json", "--dry-run", "--fail-on-problems", "--no-sheets", "--compare"}
VALUES = {"--page", "--out", "--template", "--max-image-width", "--image-scale", "--quality", "--encoding", "--max-frames"}
WIDTH_MIN, WIDTH_MAX = 240, 3840
HEIGHT_MIN, HEIGHT_MAX = 240, 4000
FRAMES_DEFAULT = 240
SCHEMA = 1
REVISION = "1.2.0"
RESULT_STATES = {"completed", "partial", "not-applicable", "failed", "runner-error"}
DATA_START, DATA_END = "/*GALLERY-DATA:START*/", "/*GALLERY-DATA:END*/"
TOP_KEYS = {"page", "title", "widths", "themes", "states", "settle_ms"}
STATE_KEYS = {"name", "steps", "route_fail", "route_delay", "page", "scroll_to", "shows"}
THEME_KEYS = {"name", "set", "steps"}

# ---------------------------------------------------------------------------------------------
# Step grammar. split_selector, parse_step and run_steps are copied from the interface-architect
# skill's scripts/delivery_check.py so that this script stands alone. Two changes: run_steps takes
# an after_reload callback (the theme is applied again after a reload: step), and it stops at the
# first failed step, because the steps after it would run against the wrong state.
# ---------------------------------------------------------------------------------------------
KINDS = ("click", "fill", "check", "press", "expect", "expect-attr", "expect-count", "expect-gone", "expect-focus", "reload", "wait")
RETRY_MS = 2000


def split_selector(arg):
    """Split SELECTOR=VALUE at the first = that is outside [brackets] and quotes."""
    depth, quote = 0, ""
    for i, ch in enumerate(arg):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif ch == "=" and depth == 0:
            return arg[:i], arg[i + 1:]
    return None, None


def parse_step(s):
    s = s.strip()
    if ":" not in s:
        return None, "step %r has no kind (expected kind:arg)" % s
    kind, arg = s.split(":", 1)
    kind = kind.strip().lower()
    if kind not in KINDS:
        return None, "step kind %r is not one of %s" % (kind, ", ".join(KINDS))
    if kind == "reload":
        if arg.strip():
            return None, "reload takes no argument"
        return {"kind": kind, "text": s}, None
    if kind == "wait":
        if not arg.strip().isdigit():
            return None, "wait needs whole milliseconds, got %r" % arg
        return {"kind": kind, "ms": int(arg), "text": s}, None
    if kind in ("click", "check", "expect-gone", "expect-focus"):
        if not arg.strip():
            return None, "%s needs a selector" % kind
        return {"kind": kind, "sel": arg.strip(), "text": s}, None
    if kind == "expect-count":
        if "=" not in arg or not arg.rsplit("=", 1)[1].strip().isdigit() or not arg.rsplit("=", 1)[0].strip():
            return None, "expect-count needs SELECTOR=N with a whole number, got %r" % arg
        sel, n = arg.rsplit("=", 1)
        return {"kind": kind, "sel": sel.strip(), "n": int(n), "text": s}, None
    if kind == "expect-attr":
        at = max((i for i, ch in enumerate(arg) if ch == "@" and "=" in arg[i:] and "]" not in arg[i:arg.index("=", i)]), default=-1)
        if at < 1:
            return None, "expect-attr needs SELECTOR@ATTR=VALUE, got %r" % arg
        sel, rest = arg[:at], arg[at + 1:]
        attr, val = rest.split("=", 1)
        return {"kind": kind, "sel": sel.strip(), "attr": attr.strip(), "value": val, "text": s}, None
    sel, val = split_selector(arg)
    if sel is None:
        return None, "%s needs SELECTOR=VALUE, got %r" % (kind, arg)
    if not sel.strip():
        return None, "%s needs a selector" % kind
    return {"kind": kind, "sel": sel.strip(), "value": val, "text": s}, None


def run_steps(page, steps, after_reload=None):
    """Run steps against the page. Returns a list of {step, ok, detail}; stops after the first failure."""
    out = []
    for st in steps:
        ok, detail = True, ""
        try:
            if st["kind"] == "wait":
                page.wait_for_timeout(st["ms"])
            elif st["kind"] == "reload":
                page.reload(timeout=10000)
                page.wait_for_timeout(400)
                if after_reload:
                    after_reload()
            elif st["kind"] == "click":
                page.locator(st["sel"]).first.click(timeout=3000)
            elif st["kind"] == "check":
                page.locator(st["sel"]).first.check(timeout=3000)
            elif st["kind"] == "fill":
                loc = page.locator(st["sel"]).first
                loc.fill(st["value"], timeout=3000)
                loc.blur()
            elif st["kind"] == "press":
                page.locator(st["sel"]).first.press(st["value"], timeout=3000)
            else:
                waited = 0
                while True:
                    page.wait_for_timeout(120)
                    waited += 120
                    loc = page.locator(st["sel"])
                    if st["kind"] == "expect":
                        got = loc.first.evaluate("e => (e.value !== undefined && e.value !== null && typeof e.value === 'string' && e.tagName !== 'BUTTON' ? e.value : e.textContent) || ''", timeout=3000) if loc.count() else None
                        ok = got is not None and st["value"] in got
                        detail = "" if ok else ("nothing matches the selector" if got is None else "found %r" % got.strip()[:60])
                    elif st["kind"] == "expect-attr":
                        got = loc.first.get_attribute(st["attr"], timeout=3000) if loc.count() else None
                        ok = got == st["value"]
                        detail = "" if ok else "found %r" % got
                    elif st["kind"] == "expect-focus":
                        where = page.evaluate("s => { const a = document.activeElement; if (!a || a === document.body) return 'nothing'; return a.matches(s) ? '' : (a.id ? '#' + a.id : a.tagName.toLowerCase()); }", st["sel"])
                        ok = where == ""
                        detail = "" if ok else "focus is on %s" % where
                    else:
                        n = loc.count()
                        want = st["n"] if st["kind"] == "expect-count" else 0
                        ok = n == want
                        detail = "" if ok else "found %d, expected %d" % (n, want)
                    if ok or waited >= RETRY_MS:
                        break
        except Exception as e:  # noqa: BLE001
            ok, detail = False, str(e).split("\n")[0][:100]
            try:                                            # say the plain reason when there is one
                if st.get("sel") and page.locator(st["sel"]).count() == 0:
                    detail = "nothing matches the selector"
                elif "Timeout" in detail:
                    detail = "the element was found but could not be used within 3 seconds"
            except Exception:  # noqa: BLE001
                pass
        out.append({"step": st["text"], "ok": ok, "detail": detail})
        if not ok:
            break
    return out


# ---------------------------------------------------------------------------------------------
# Measuring. CONTRAST_JS is MEASURE_JS from the interface-architect skill's
# scripts/contrast_check.py, unchanged. TARGETS_JS is EXTRACT_JS from its scripts/target_size.py,
# unchanged, and small_targets() below applies that script's evaluate() geometry.
# ---------------------------------------------------------------------------------------------
CONTRAST_JS = r"""
() => {
  const parse = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[,\s\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const over = (top, under) => ({r: top.r * top.a + under.r * (1 - top.a), g: top.g * top.a + under.g * (1 - top.a), b: top.b * top.a + under.b * (1 - top.a), a: 1});
  const lin = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = c => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const hex = c => '#' + [c.r, c.g, c.b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  const name = e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/)[0] : ''));
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.nodeValue.trim()) continue;
    const e = node.parentElement;
    if (!e || seen.has(e) || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|OPTION)$/.test(e.tagName)) continue;
    seen.add(e);
    const cs = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    if (cs.display === 'none' || cs.visibility !== 'visible' || r.width === 0 || r.height === 0 || Number(cs.opacity) === 0) continue;
    if (e.closest('[disabled],[aria-disabled="true"],[hidden],[aria-hidden="true"]')) continue;
    const stack = [];
    let image = false, cur = e, opacity = 1;
    while (cur && cur.nodeType === 1) {
      const s = getComputedStyle(cur);
      opacity *= Number(s.opacity);
      if (s.backgroundImage && s.backgroundImage !== 'none') { image = true; break; }
      const bg = parse(s.backgroundColor);
      if (bg && bg.a > 0) { stack.push(bg); if (bg.a >= 1) break; }
      cur = cur.parentElement;
    }
    const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const text = node.nodeValue.trim().replace(/\s+/g, ' ').slice(0, 40);
    if (image) { out.push({el: name(e), text, measured: false, why: 'over an image or gradient'}); continue; }
    let bg = {r: 255, g: 255, b: 255, a: 1};
    for (let i = stack.length - 1; i >= 0; i--) bg = over(stack[i], bg);
    let fg = parse(cs.color); if (!fg) continue;
    fg = over({r: fg.r, g: fg.g, b: fg.b, a: fg.a * opacity}, bg);
    const cr = ratio(fg, bg);
    out.push({el: name(e), text, measured: true, ratio: Math.round(cr * 100) / 100, need: large ? 3 : 4.5, fg: hex(fg), bg: hex(bg), size: Math.round(size * 10) / 10});
  }
  return out;
}
"""

TARGETS_JS = r"""
(labelUnion) => {
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],[role=checkbox],[role=radio],[role=switch],[role=menuitem],[onclick]';
  const vis = e => { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility !== 'visible' || cs.pointerEvents === 'none') return false;
    const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const out = []; let n = 0;
  document.querySelectorAll(sel).forEach(e => {
    if (!vis(e) || e.disabled) return;
    let r = e.getBoundingClientRect(); let box = {l: r.left, t: r.top, r: r.right, b: r.bottom};
    if (labelUnion && /^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName)) {
      const labs = [...(e.labels || [])];
      labs.forEach(l => { if (!vis(l)) return; const q = l.getBoundingClientRect(); box = {l: Math.min(box.l, q.left), t: Math.min(box.t, q.top), r: Math.max(box.r, q.right), b: Math.max(box.b, q.bottom)}; });
    }
    const p = e.parentElement;
    const inline = e.tagName === 'A' && p && [...p.childNodes].some(c => c.nodeType === 3 && c.nodeValue.trim().length > 0);
    const name = (e.id ? '#' + e.id : e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/)[0] : '')) + ' ' + JSON.stringify((e.getAttribute('aria-label') || e.textContent || e.value || '').trim().slice(0, 18));
    out.push({id: (n++) + ' ' + name, x: box.l + scrollX, y: box.t + scrollY, w: box.r - box.l, h: box.b - box.t, inline});
  });
  return out;
}
"""

# Written for this script: sideways overflow of the document and text that is cut off.
LAYOUT_JS = r"""
() => {
  const de = document.documentElement, body = document.body;
  const client = de.clientWidth;
  const full = Math.max(de.scrollWidth, body ? body.scrollWidth : 0);
  const name = e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/)[0] : ''));
  const shown = e => { const cs = getComputedStyle(e), r = e.getBoundingClientRect(); return cs.display !== 'none' && cs.visibility === 'visible' && r.width > 0 && r.height > 0; };
  const scrollsX = e => { for (let p = e.parentElement; p && p !== de; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return true; } return false; };
  const out = {client_width: client, overflow_px: Math.max(0, Math.round(full - client)), overflow_from: [], clipped: []};
  if (full - client > 1 && body) {
    const wide = [];
    body.querySelectorAll('*').forEach(e => {
      if (!shown(e) || getComputedStyle(e).position === 'fixed') return;
      const r = e.getBoundingClientRect();
      if (r.right + scrollX > client + 1 && !scrollsX(e)) wide.push({el: name(e), by: Math.round(r.right + scrollX - client), n: e.querySelectorAll('*').length});
    });
    // name the innermost offenders: the ones that hold the fewest other elements
    wide.sort((a, b) => a.n - b.n || b.by - a.by);
    out.overflow_from = wide.slice(0, 3).map(w => w.el + ' (' + w.by + ' px past the edge)');
  }
  if (body) {
    body.querySelectorAll('*').forEach(e => {
      if (/^(INPUT|TEXTAREA|SELECT|OPTION|SCRIPT|STYLE)$/.test(e.tagName)) return;
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.display === 'inline' || cs.visibility !== 'visible') return;
      if (e.clientWidth <= 2 || e.clientHeight <= 2) return;                 // visually hidden helpers
      if (e.closest('[hidden],[aria-hidden="true"]')) return;
      const cutX = (cs.overflowX === 'hidden' || cs.overflowX === 'clip') && e.scrollWidth > e.clientWidth + 1;
      const cutY = (cs.overflowY === 'hidden' || cs.overflowY === 'clip') && e.scrollHeight > e.clientHeight + 1;
      if (!cutX && !cutY) return;
      const text = (e.textContent || '').trim().replace(/\s+/g, ' ');
      if (!text) return;
      out.clipped.push({el: name(e), text: text.slice(0, 40), how: cutX ? 'sideways' : 'downwards'});
    });
  }
  return out;
}
"""

QUIET_JS = r"""
([ms, cap]) => new Promise(resolve => {
  let t = null, obs = null;
  const done = () => { if (obs) obs.disconnect(); clearTimeout(t); clearTimeout(limit); resolve(true); };
  const limit = setTimeout(done, cap);
  obs = new MutationObserver(() => { clearTimeout(t); t = setTimeout(done, ms); });
  obs.observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
  t = setTimeout(done, ms);
})
"""

ENCODE_JS = r"""
async ([b64, maxw, quality, scale]) => {
  const img = new Image();
  img.src = 'data:image/png;base64,' + b64;
  await img.decode();
  const k = Math.min(1, scale, maxw / img.naturalWidth);
  const w = Math.max(1, Math.round(img.naturalWidth * k)), h = Math.max(1, Math.round(img.naturalHeight * k));
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); g.imageSmoothingQuality = 'high'; g.drawImage(img, 0, 0, w, h);
  let url = c.toDataURL('image/webp', quality);
  if (url.indexOf('data:image/webp') !== 0) url = c.toDataURL('image/jpeg', quality);
  return {url, w, h, scale: k};
}
"""

# For the per-state sheet pictures: the gallery page itself, one width at a time, frames wrapped.
SHEET_CSS = (".cols{display:none!important}.sheet{overflow:visible!important}"
             ".state{display:grid!important;grid-template-columns:230px minmax(0,1fr)!important;width:auto!important;min-width:0!important}"
             ".strip{flex-wrap:wrap!important;overflow:visible!important}.frame.group-start{margin-left:0!important}")
SHEET_ONLY_WIDTH_JS = r"""
async (w) => {
  document.querySelectorAll('[data-width-chip]').forEach(b => {
    const on = b.getAttribute('aria-pressed') === 'true', want = b.getAttribute('data-width-chip') === w;
    if (on !== want) b.click();
  });
  await new Promise(r => setTimeout(r, 60));
  await Promise.all([...document.images].map(i => i.decode().catch(() => null)));
}
"""
SHEET_BOXES_JS = r"""
() => [...document.querySelectorAll('section.state')].map(e => {
  const r = e.getBoundingClientRect();
  return {n: Number(e.getAttribute('aria-labelledby').replace('state-', '')), x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height};
})
"""

SIZE, R24, EPS = 24.0, 12.0, 0.01


def small_targets(targets):
    """target_size.py evaluate(): returns (unresolved under 24 by 24, count under 44 by 44)."""
    def under(t):
        return t["w"] < SIZE - EPS or t["h"] < SIZE - EPS

    def centre(t):
        return t["x"] + t["w"] / 2.0, t["y"] + t["h"] / 2.0

    def gap(c, t):
        dx = max(t["x"] - c[0], 0.0, c[0] - (t["x"] + t["w"]))
        dy = max(t["y"] - c[1], 0.0, c[1] - (t["y"] + t["h"]))
        return math.hypot(dx, dy)

    def overlap(a, b):
        return (min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) > EPS
                and min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) > EPS)

    unresolved = []
    for i, t in enumerate(targets):
        if any(j != i and overlap(t, o) for j, o in enumerate(targets)):
            continue                                   # overlapping targets are not measured, as in target_size.py
        if not under(t):
            continue
        c = centre(t)
        clash = False
        for j, o in enumerate(targets):
            if j == i:
                continue
            if gap(c, o) < R24 - EPS:
                clash = True
            elif under(o) and math.hypot(c[0] - centre(o)[0], c[1] - centre(o)[1]) < SIZE - EPS:
                clash = True
        if clash and not t.get("inline"):
            unresolved.append("%s %gx%g" % (t["id"][:40], round(t["w"], 1), round(t["h"], 1)))
    under44 = sum(1 for t in targets if t["w"] < 44 - EPS or t["h"] < 44 - EPS)
    return unresolved, under44


# ---------------------------------------------------------------------------------------------
# Reading and checking the states file
# ---------------------------------------------------------------------------------------------
class Bad(Exception):
    pass


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def is_url(s):
    return isinstance(s, str) and s.lower().startswith(("http://", "https://"))


def read_json(path, what):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise Bad("cannot read %s %s: %s" % (what, path, e.strerror or e))
    if bytes([0]) in raw:
        raise Bad("%s %s contains a NUL byte" % (what, path))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Bad("%s %s is not valid UTF-8" % (what, path))

    def no_constant(c):
        raise ValueError("%s is not allowed" % c)
    try:
        return json.loads(text, parse_constant=no_constant)
    except ValueError as e:
        raise Bad("%s %s is not valid JSON (%s)" % (what, path, str(e)[:70]))


def glob_to_regex(glob):
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**", i):
            out += ".*"
            i += 2
        elif glob[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(glob[i])
            i += 1
    return re.compile("^" + out + "$")


def parse_routes(v, where):
    if v is None:
        return []
    if not isinstance(v, list):
        raise Bad("%s must be a list of globs" % where)
    out = []
    for r in v:
        if isinstance(r, str) and r.strip():
            out.append({"url": r.strip(), "method": None, "re": glob_to_regex(r.strip())})
        elif isinstance(r, dict) and isinstance(r.get("url"), str) and r["url"].strip() and set(r) <= {"url", "method"}:
            m = r.get("method")
            if m is not None and (not isinstance(m, str) or m.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")):
                raise Bad("%s: method %r is not an HTTP method" % (where, m))
            out.append({"url": r["url"].strip(), "method": m.upper() if m else None, "re": glob_to_regex(r["url"].strip())})
        else:
            raise Bad("%s: each entry is a glob or {\"url\": GLOB, \"method\": \"POST\"}, got %r" % (where, r))
    return out


def parse_sets(v, where):
    if v is None:
        return []
    items = v if isinstance(v, list) else [v]
    out = []
    for s in items:
        if not isinstance(s, str):
            raise Bad("%s: set must be SELECTOR@ATTR=VALUE, got %r" % (where, s))
        at = s.rfind("@")
        if at < 1 or "=" not in s[at:]:
            raise Bad("%s: set must be SELECTOR@ATTR=VALUE, got %r" % (where, s))
        attr, val = s[at + 1:].split("=", 1)
        if not attr.strip():
            raise Bad("%s: set must be SELECTOR@ATTR=VALUE, got %r" % (where, s))
        out.append((s[:at].strip(), attr.strip(), val))
    return out


def parse_steps(v, where):
    if v is None:
        return []
    if not isinstance(v, list):
        raise Bad("%s: steps must be a list of step strings" % where)
    out = []
    for s in v:
        if not isinstance(s, str):
            raise Bad("%s: a step must be text like click:#id, got %r" % (where, s))
        st, err = parse_step(s)
        if err:
            raise Bad("%s: %s" % (where, err))
        out.append(st)
    return out


def resolve_page(spec, base):
    """Returns (address to load, text to show). Refuses a file that does not exist."""
    if not isinstance(spec, str) or not spec.strip():
        raise Bad("page must be a file path or an http(s) address")
    spec = spec.strip()
    if is_url(spec):
        return spec, spec
    p = Path(spec)
    if not p.is_absolute():
        p = base / p
    if not p.is_file():
        raise Bad("page %s does not exist (looked for %s)" % (spec, p.name if p.parent == base else p))
    return p.resolve().as_uri(), spec


def load_plan(path, page_override, max_frames):
    data = read_json(path, "states file")
    base = Path(path).resolve().parent
    if not isinstance(data, dict):
        raise Bad("the states file must hold one JSON object")
    unknown = sorted(set(data) - TOP_KEYS)
    if unknown:
        raise Bad("unknown key %r in the states file (known: %s)" % (unknown[0], ", ".join(sorted(TOP_KEYS))))
    page_spec = page_override if page_override is not None else data.get("page")
    if page_spec is None:
        raise Bad("no page: give \"page\" in the states file or --page")
    uri, shown = resolve_page(page_spec, base if page_override is None else Path.cwd())
    widths = data.get("widths")
    if not isinstance(widths, list) or not widths:
        raise Bad("widths must be a non-empty list of whole numbers, for example [390, 1280]")
    sizes = []
    for w in widths:
        if is_int(w):
            ww, hh = w, (844 if w < 700 else 800)
        elif isinstance(w, dict) and set(w) == {"width", "height"} and is_int(w["width"]) and is_int(w["height"]):
            ww, hh = w["width"], w["height"]
        else:
            raise Bad("a width must be a whole number or {\"width\": N, \"height\": N}, got %r (text and true are not numbers)" % (w,))
        if not WIDTH_MIN <= ww <= WIDTH_MAX:
            raise Bad("width %d is outside %d to %d" % (ww, WIDTH_MIN, WIDTH_MAX))
        if not HEIGHT_MIN <= hh <= HEIGHT_MAX:
            raise Bad("height %d is outside %d to %d" % (hh, HEIGHT_MIN, HEIGHT_MAX))
        if any(s["width"] == ww for s in sizes):
            raise Bad("width %d is listed twice" % ww)
        sizes.append({"width": ww, "height": hh})
    themes_in = data.get("themes")
    themes = []
    if themes_in is None:
        themes = [{"name": "as loaded", "sets": [], "steps": []}]
    else:
        if not isinstance(themes_in, list) or not themes_in:
            raise Bad("themes must be a non-empty list; leave the key out to capture the page as loaded")
        for i, t in enumerate(themes_in):
            where = "theme %d" % (i + 1)
            if not isinstance(t, dict) or not isinstance(t.get("name"), str) or not t["name"].strip():
                raise Bad("%s needs a name" % where)
            where = "theme %r" % t["name"].strip()
            bad = sorted(set(t) - THEME_KEYS)
            if bad:
                raise Bad("%s: unknown key %r" % (where, bad[0]))
            if any(x["name"] == t["name"].strip() for x in themes):
                raise Bad("%s is listed twice" % where)
            themes.append({"name": t["name"].strip(), "sets": parse_sets(t.get("set"), where), "steps": parse_steps(t.get("steps"), where)})
    states_in = data.get("states")
    if not isinstance(states_in, list) or not states_in:
        raise Bad("states must be a non-empty list")
    states = []
    for i, s in enumerate(states_in):
        where = "state %d" % (i + 1)
        if not isinstance(s, dict) or not isinstance(s.get("name"), str) or not s["name"].strip():
            raise Bad("%s needs a name" % where)
        name = " ".join(s["name"].split())
        where = "state %r" % name
        bad = sorted(set(s) - STATE_KEYS)
        if bad:
            raise Bad("%s: unknown key %r (known: %s)" % (where, bad[0], ", ".join(sorted(STATE_KEYS))))
        if any(x["name"].lower() == name.lower() for x in states):
            raise Bad("%s is listed twice" % where)
        for k in ("scroll_to", "shows"):
            if s.get(k) is not None and (not isinstance(s[k], str) or not s[k].strip()):
                raise Bad("%s: %s must be text" % (where, k))
        st = {"name": name, "steps": parse_steps(s.get("steps"), where),
              "route_fail": parse_routes(s.get("route_fail"), where + " route_fail"),
              "route_delay": parse_routes(s.get("route_delay"), where + " route_delay"),
              "scroll_to": s.get("scroll_to"), "shows": (s.get("shows") or "").strip(), "uri": uri, "page": shown}
        if s.get("page") is not None:
            st["uri"], st["page"] = resolve_page(s["page"], base)
        states.append(st)
    settle = data.get("settle_ms", 350)
    if not is_int(settle) or not 0 <= settle <= 10000:
        raise Bad("settle_ms must be a whole number from 0 to 10000")
    title = data.get("title")
    if title is not None and (not isinstance(title, str) or not title.strip()):
        raise Bad("title must be text")
    total = len(states) * len(themes) * len(sizes)
    if total > max_frames:
        raise Bad("%d state(s) x %d theme(s) x %d width(s) is %d frames, over the limit of %d (raise --max-frames, or split the file)"
                  % (len(states), len(themes), len(sizes), total, max_frames))
    return {"page": shown, "uri": uri, "title": (title or "").strip(), "sizes": sizes, "themes": themes, "states": states,
            "settle": settle, "total": total, "file": Path(path).name}


# ---------------------------------------------------------------------------------------------
# Capturing
# ---------------------------------------------------------------------------------------------
def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "x"


def problems_of(facts):
    """Words for each measured problem in a reached frame."""
    out = []
    if facts["overflow_px"] > 1:
        out.append("Overflows sideways by %d px" % facts["overflow_px"])
    if facts["clipped_count"]:
        out.append("%d text element%s cut off" % (facts["clipped_count"], "" if facts["clipped_count"] == 1 else "s"))
    if facts["contrast_below"]:
        out.append("%d text element%s below contrast (lowest %.2f)" % (facts["contrast_below"], "" if facts["contrast_below"] == 1 else "s", facts["contrast_lowest"]))
    if facts["small_targets"]:
        out.append("%d target%s under 24 by 24 with no spacing" % (facts["small_targets"], "" if facts["small_targets"] == 1 else "s"))
    if facts["console_errors"]:
        out.append("%d console error%s" % (facts["console_errors"], "" if facts["console_errors"] == 1 else "s"))
    if facts["failed_requests"]:
        out.append("%d request%s failed" % (facts["failed_requests"], "" if facts["failed_requests"] == 1 else "s"))
    if facts["broken_answers"]:
        out.append("%d request%s answered with a server error or a missing file" % (facts["broken_answers"], "" if facts["broken_answers"] == 1 else "s"))
    return out


def missing_frame(state, theme, size, reason, stage):
    """Keep a requested combination even when its capture helper cannot return."""
    return {"state": state["name"], "theme": theme["name"], "width": size["width"], "height": size["height"],
            "reached": False, "why_not": reason, "steps": [], "facts": None, "problems": [reason], "png": None,
            "measured_facts": None, "measured_problems": [], "incomplete_stage": stage}


def mark_capture_missing(frame, reason, stage):
    """Legacy reached/facts still mean a usable capture; earlier measurements survive separately."""
    if frame.get("facts") is not None:
        frame["measured_facts"] = frame["facts"]
        frame["measured_problems"] = list(frame.get("problems", []))
    frame.update(reached=False, facts=None, why_not=reason, problems=[reason], incomplete_stage=stage)
    frame.pop("_img", None)
    return frame


def capture_frame(browser, plan, state, theme, size, png_path):
    """Returns the frame record. Writes a PNG of the page as it stood, reached or not."""
    frame = {"state": state["name"], "theme": theme["name"], "width": size["width"], "height": size["height"],
             "reached": False, "why_not": "", "steps": [], "facts": None, "problems": [], "png": None,
             "measured_facts": None, "measured_problems": []}
    ctx = browser.new_context(viewport={"width": size["width"], "height": size["height"]}, device_scale_factor=1)
    page = ctx.new_page()
    errors, aborted, held, inflight, answers, lost = [], set(), [], set(), [], []
    held_reqs, answered = set(), set()

    def short(url):
        m = re.match(r"https?://[^/]+(/.*)?$", url)
        return ((m.group(1) or "/") if m else url)[:80]

    def on_console(m):
        # The browser writes its own "Failed to load resource" line for every refused or failed
        # request. Those are counted from the network events below, not here, so that a server's
        # 422 for invalid input is not reported as a script error.
        if m.type == "error" and not m.text.startswith("Failed to load resource"):
            errors.append(m.text[:160])

    def on_response(r):
        answered.add((r.request.method, r.request.url))
        if r.status >= 400:
            q = r.request
            answers.append({"status": r.status, "method": q.method, "url": short(q.url), "type": q.resource_type})

    def on_failed(q):
        inflight.discard(q)
        if q.url in aborted or q in held_reqs:
            return                                          # this script aborted or held it on purpose
        if (q.method, q.url) in answered:
            return                                          # Chromium reports an answered request with no body (a 204) as failed
        lost.append("%s %s (%s)" % (q.method, short(q.url), (q.failure or "failed")[:40]))
    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append("uncaught: " + str(e)[:160]))
    page.on("request", lambda q: inflight.add(q))
    page.on("requestfinished", lambda q: inflight.discard(q))
    page.on("requestfailed", on_failed)
    page.on("response", on_response)

    def matches(rules, request):
        return any(r["re"].match(request.url) and (r["method"] is None or r["method"] == request.method) for r in rules)

    def handler(route, request):
        if request.is_navigation_request() and request.frame == page.main_frame:
            route.continue_()
        elif matches(state["route_fail"], request):
            aborted.add(request.url)
            route.abort("connectionrefused")
        elif matches(state["route_delay"], request):
            held.append(route)
            held_reqs.add(request)
        else:
            route.continue_()
    if state["route_fail"] or state["route_delay"]:
        page.route("**/*", handler)

    def apply_theme():
        for sel, attr, val in theme["sets"]:
            if page.locator(sel).count() == 0:
                raise RuntimeError("theme %s: nothing matches %r" % (theme["name"], sel))
            page.locator(sel).first.evaluate("(e, a) => e.setAttribute(a[0], a[1])", [attr, val])

    try:
        try:
            page.goto(state["uri"], wait_until="commit", timeout=10000)
            try:
                page.wait_for_load_state("load", timeout=5000)
            except Exception:  # noqa: BLE001
                pass                                        # a held request can keep "load" from firing
            page.wait_for_timeout(250)
        except Exception as e:  # noqa: BLE001
            frame["why_not"] = "the page did not load (%s)" % str(e).split("\n")[0][:90]
            frame["problems"] = [frame["why_not"]]
            return frame
        try:
            apply_theme()
        except Exception as e:  # noqa: BLE001
            frame["why_not"] = str(e).split("\n")[0][:120]
        if not frame["why_not"]:
            frame["steps"] = run_steps(page, theme["steps"] + state["steps"], after_reload=apply_theme)
            bad = [s for s in frame["steps"] if not s["ok"]]
            if bad:
                n = len(frame["steps"])
                frame["why_not"] = "step %d failed: %s%s" % (n, bad[0]["step"][:60], (" (" + bad[0]["detail"] + ")") if bad[0]["detail"] else "")
        if not frame["why_not"] and state["scroll_to"]:
            try:
                page.locator(state["scroll_to"]).first.scroll_into_view_if_needed(timeout=3000)
            except Exception as e:  # noqa: BLE001
                frame["why_not"] = "scroll_to %s: %s" % (state["scroll_to"][:40], str(e).split("\n")[0][:70])
        try:
            page.mouse.move(0, 0)                           # park the pointer: a hover style left by the last click is not part of the state
        except Exception:  # noqa: BLE001
            pass
        # wait until nothing is in flight (apart from requests held on purpose) and the page is still
        waited = 0
        while waited < 3000 and any(q not in held_reqs for q in inflight):
            page.wait_for_timeout(50)
            waited += 50
        try:
            page.evaluate(QUIET_JS, [plan["settle"], 4000])
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(120)                          # colour transitions
        if not frame["why_not"]:
            contrast = page.evaluate(CONTRAST_JS)
            layout = page.evaluate(LAYOUT_JS)
            unresolved, under44 = small_targets(page.evaluate(TARGETS_JS, True))
            measured = [r for r in contrast if r["measured"]]
            low = sorted([r for r in measured if r["ratio"] < r["need"]], key=lambda r: r["ratio"])
            facts = {
                "overflow_px": layout["overflow_px"], "overflow_from": layout["overflow_from"],
                "clipped_count": len(layout["clipped"]), "clipped": layout["clipped"][:8],
                "contrast_measured": len(measured), "contrast_lowest": min((r["ratio"] for r in measured), default=None),
                "contrast_below": len(low),
                "contrast_below_list": [{"el": r["el"], "text": r["text"], "ratio": r["ratio"], "need": r["need"], "fg": r["fg"], "bg": r["bg"]} for r in low[:8]],
                "contrast_not_measured": len(contrast) - len(measured),
                "small_targets": len(unresolved), "small_targets_list": unresolved[:8], "targets_under_44": under44,
                "console_errors": len(errors), "console_messages": errors[:5],
                "failed_requests": len(lost), "failed_requests_list": lost[:5],
                "refused_answers": len([a for a in answers if a["status"] < 500 and a["type"] in ("fetch", "xhr")]),
                "broken_answers": len([a for a in answers if a["status"] >= 500 or a["type"] not in ("fetch", "xhr")]),
                "answers_list": ["%d %s %s%s" % (a["status"], a["method"], a["url"], "" if a["type"] in ("fetch", "xhr") else " (" + a["type"] + ")") for a in answers[:6]],
                "requests_aborted_on_purpose": len(aborted), "requests_held_on_purpose": len(held),
            }
            frame["facts"] = facts
            frame["reached"] = True
            frame["problems"] = problems_of(facts)
            frame["measured_facts"] = facts
            frame["measured_problems"] = list(frame["problems"])
        else:
            frame["problems"] = [frame["why_not"]]
        try:
            page.screenshot(path=str(png_path), animations="disabled", caret="hide")
            frame["png"] = png_path.name
        except Exception as e:  # noqa: BLE001
            if frame["reached"]:
                mark_capture_missing(frame, "the screenshot failed (%s)" % str(e).split("\n")[0][:80], "screenshot")
        return frame
    finally:
        for r in held:
            try:
                r.abort()
            except Exception:  # noqa: BLE001
                pass
        try:
            ctx.close()
        except Exception:  # noqa: BLE001
            pass


def ascii_only(text):
    return text.encode("ascii", "replace").decode("ascii")


def emit(text):
    try:
        sys.stdout.write(ascii_only(text) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def frame_key(f):
    return "%s / %s / %d x %s" % (f["state"], f["theme"], f["width"], f.get("height", "unknown"))


def receipt_for(phase, status, exit_code, coverage=None, reasons=None):
    if status not in RESULT_STATES:
        raise ValueError("unknown result status: " + status)
    meanings = {
        "validation": "States-file validation only; no browser discovery, capture, measurement or visual judgement.",
        "capture": "Capture coverage and measured facts only; no aesthetic verdict, full accessibility claim or benchmark score.",
        "compare": "Comparison of stored facts only; no recapture, pixel comparison or quality verdict.",
    }
    return {"tool": "state_gallery", "revision": REVISION, "phase": phase, "status": status,
            "exit": exit_code, "exit_policy": "legacy: 0 build/validation/compare; 1 --fail-on-problems; 2 input/output setup; 3 could not run. Read status, not exit alone.",
            "coverage": coverage or {}, "reasons": reasons or [], "meaning": meanings[phase]}


def finish_result(receipt, flags, payload=None, human=None):
    result = dict(payload or {})
    result.update(status=receipt["status"], phase=receipt["phase"], receipt=receipt)
    if "--json" in flags:
        emit(json.dumps(result, indent=1, ensure_ascii=True))
    elif human:
        emit(human)
    print("RECEIPT " + json.dumps(receipt, ensure_ascii=True, separators=(",", ":")), file=sys.stderr)
    return receipt["exit"]


def stopped(phase, status, exit_code, reason, flags, coverage=None):
    return finish_result(receipt_for(phase, status, exit_code, coverage, [reason]), flags)


def _build(plan, opts, flags, progress):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        if "--json" not in flags:
            emit("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return stopped("capture", "runner-error", 3, "Playwright is unavailable", flags, {"requested_frames": plan["total"], "captured_frames": 0})
    tpl_path = Path(opts["--template"]) if "--template" in opts else Path(__file__).resolve().parent.parent / "assets" / "gallery-template.html"
    try:
        template = tpl_path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        print("state_gallery: cannot read the gallery template %s (%s)" % (tpl_path, str(e)[:60]), file=sys.stderr)
        return stopped("capture", "runner-error", 2, "Gallery template could not be read", flags)
    if template.count(DATA_START) != 1 or template.count(DATA_END) != 1:
        print("state_gallery: the template must contain %s and %s once each" % (DATA_START, DATA_END), file=sys.stderr)
        return stopped("capture", "runner-error", 2, "Gallery template markers are invalid", flags)
    out_dir = Path(opts["--out"]) if "--out" in opts else Path(opts["_states_path"]).resolve().parent / "gallery"
    progress["out_dir"] = out_dir
    frames_dir, sheets_dir = out_dir / "frames", out_dir / "sheets"
    try:
        frames_dir.mkdir(parents=True, exist_ok=True)
        if "--no-sheets" not in flags:
            sheets_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print("state_gallery: cannot create %s (%s)" % (out_dir, e.strerror or e), file=sys.stderr)
        return stopped("capture", "runner-error", 2, "Output directory could not be created", flags)
    maxw, quality, enc, scale = opts["_maxw"], opts["_quality"], opts.get("--encoding", "base64"), opts["_scale"]
    frames, lines = progress["frames"], []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            if "--json" not in flags:
                emit("NOT RUN: Chromium could not be launched (%s)" % str(e)[:120])
            return stopped("capture", "runner-error", 3, "Chromium could not launch", flags, {"requested_frames": plan["total"], "captured_frames": 0})
        # every distinct page must load once before any frame is attempted
        for uri in sorted({s["uri"] for s in plan["states"]}):
            probe = browser.new_page()
            try:
                probe.goto(uri, timeout=10000)
            except Exception as e:  # noqa: BLE001
                browser.close()
                if "--json" not in flags:
                    emit("NOT RUN: %s did not load%s. %s" % (uri if is_url(uri) else Path(uri).name, " (is the server running?)" if is_url(uri) else "", str(e).split("\n")[0][:100]))
                return stopped("capture", "runner-error", 3, "A required page did not load before capture", flags, {"requested_frames": plan["total"], "captured_frames": 0})
            probe.close()
        conv = browser.new_page()
        n = 0
        for si, state in enumerate(plan["states"]):
            for size in plan["sizes"]:
                for theme in plan["themes"]:
                    n += 1
                    png = frames_dir / ("%02d-%s--%s--%d.png" % (si + 1, slug(state["name"]), slug(theme["name"]), size["width"]))
                    try:
                        f = capture_frame(browser, plan, state, theme, size, png)
                    except Exception as e:  # preserve the requested combination, not a fabricated measurement
                        f = missing_frame(state, theme, size, "capture could not finish (%s)" % str(e).split("\n")[0][:100], "capture")
                    f["index"] = n
                    frames.append(f)
                    if f["reached"]:
                        try:
                            got = conv.evaluate(ENCODE_JS, [base64.b64encode(png.read_bytes()).decode("ascii"), maxw, quality / 100.0, scale])
                            head, b64 = got["url"].split(",", 1)
                            mime = head[5:].split(";")[0]
                            f["_img"] = {"mime": mime, "enc": enc, "w": got["w"], "h": got["h"], "scale": round(got["scale"], 4),
                                         "data": b64 if enc == "base64" else base64.b64decode(b64).hex()}
                        except Exception as e:
                            mark_capture_missing(f, "capture could not be embedded (%s)" % str(e).split("\n")[0][:100], "encoding")
                    for prob in f["problems"]:
                        lines.append("  %-11s %s: %s" % ("PROBLEM" if f["reached"] else "NOT REACHED", frame_key(f), prob))
        conv.close()
        problem_frames = [f for f in frames if f["problems"]]
        measured_problem_frames = [f for f in frames if f.get("measured_problems") or (f.get("facts") and problems_of(f["facts"]))]
        unreached = [f for f in frames if not f["reached"]]
        record = {
            "tool": "state_gallery", "schema": SCHEMA, "title": plan["title"] or ("Every state of " + plan["page"]),
            "page": plan["page"], "states_file": plan["file"],
            "built_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "widths": plan["sizes"], "themes": [t["name"] for t in plan["themes"]],
            "states": [{"name": s["name"], "shows": s["shows"], "page": s["page"]} for s in plan["states"]],
            "thresholds": {"contrast_normal": 4.5, "contrast_large": 3, "target_px": 24},
            "summary": {"frames": len(frames), "with_measured_problem": len(problem_frames), "not_reached": len(unreached),
                        "measured_problem_frames": len(measured_problem_frames), "legacy_combined_problem_frames": len(problem_frames),
                        "with_measured_problem_meaning": "Legacy combined count includes not-reached frames; use measured_problem_frames for measurements only.",
                        "states_not_reached": sorted({f["state"] for f in unreached})},
            "frames": [{k: v for k, v in f.items() if not k.startswith("_")} for f in frames],
        }
        progress["record"] = record
        page_data = dict(record)
        page_data["frames"] = [dict({k: v for k, v in f.items() if not k.startswith("_")}, img=f.get("_img")) for f in frames]
        blob = json.dumps(page_data, ensure_ascii=True, separators=(",", ":")).replace("<", chr(92) + "u003c")
        a, b = template.index(DATA_START) + len(DATA_START), template.index(DATA_END)
        html = template[:a] + blob + template[b:]
        html = html.replace("<title>State gallery</title>", "<title>%s</title>" % record["title"].replace("&", "&amp;").replace("<", "&lt;"), 1)
        (out_dir / "gallery.html").write_text(html, encoding="utf-8")
        sheets, sheet_names, sheet_errors = 0, [], []
        progress["sheet_names"], progress["sheet_errors"] = sheet_names, sheet_errors
        if "--no-sheets" not in flags:
            try:
                pg = browser.new_page(viewport={"width": 1640, "height": 900})
                pg.goto((out_dir / "gallery.html").resolve().as_uri(), timeout=20000)
                pg.wait_for_timeout(400)
                pg.add_style_tag(content=SHEET_CSS)
                pg.evaluate("() => document.querySelector('[data-frames-choice=\"large\"]').click()")
                for size in plan["sizes"]:
                    pg.evaluate(SHEET_ONLY_WIDTH_JS, str(size["width"]))
                    pg.wait_for_timeout(150)
                    boxes = pg.evaluate(SHEET_BOXES_JS)
                    for bx in boxes:
                        clip = {"x": max(0, bx["x"] - 12), "y": max(0, bx["y"] - 4), "width": bx["w"] + 24, "height": bx["h"] + 8}
                        name = "%02d-%s--%d.png" % (bx["n"], slug(plan["states"][bx["n"] - 1]["name"]), size["width"])
                        pg.screenshot(path=str(sheets_dir / name), clip=clip, full_page=True, animations="disabled")
                        sheet_names.append(name)
                        sheets += 1
                pg.close()
            except Exception as e:  # noqa: BLE001
                lines.append("  NOTE  the per-state sheet pictures could not be made (%s)" % str(e).split("\n")[0][:90])
                sheet_errors.append(str(e).split("\n")[0][:120])
        browser.close()
    size_bytes = (out_dir / "gallery.html").stat().st_size
    record["output"] = {"dir": str(out_dir), "gallery_html_bytes": size_bytes, "frame_pngs": len([f for f in frames if f["png"]]), "sheet_pngs": sheets,
                         "sheets": sorted(sheet_names), "final_record_written": True}
    progress["output"] = record["output"]
    requested_sheets = 0 if "--no-sheets" in flags else len(plan["states"]) * len(plan["sizes"])
    coverage = {"requested_frames": plan["total"], "attempted_frames": len(frames),
                "captured_frames": len(frames) - len(unreached), "measured_frames": sum(f.get("measured_facts") is not None or f.get("facts") is not None for f in frames),
                "measured_problem_frames": len(measured_problem_frames), "missing_frames": len(unreached),
                "requested_sheets": requested_sheets, "written_sheets": sheets,
                "sheets_status": "not-applicable" if not requested_sheets else ("completed" if sheets == requested_sheets and not sheet_errors else "partial")}
    reasons = [{"frame": frame_key(f), "reason": f["why_not"], "stage": f.get("incomplete_stage", "state not reached")} for f in unreached]
    reasons += [{"stage": "sheet export", "reason": e} for e in sheet_errors]
    status = "failed" if measured_problem_frames else ("partial" if unreached or len(frames) != plan["total"] or sheets != requested_sheets or sheet_errors else "completed")
    exit_code = 1 if (problem_frames and "--fail-on-problems" in flags) else 0
    receipt = receipt_for("capture", status, exit_code, coverage, reasons)
    record.update(status=status, phase="capture", receipt=receipt)
    (out_dir / "gallery.json").write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    if "--json" in flags:
        brief = {k: record[k] for k in ("tool", "schema", "page", "built_at", "summary", "output")}
        brief["problems"] = [{"frame": frame_key(f), "reached": f["reached"], "problems": f["problems"]} for f in problem_frames]
        return finish_result(receipt, flags, brief)
    else:
        L = ["state_gallery: %s: %d state(s) x %d theme(s) x %d width(s) = %d frame(s)" % (plan["file"], len(plan["states"]), len(plan["themes"]), len(plan["sizes"]), len(frames))]
        L += lines
        L.append("Wrote %s (%s bytes), gallery.json, %d frame picture(s) in frames/%s"
                 % (out_dir / "gallery.html", format(size_bytes, ","), record["output"]["frame_pngs"], (", %d state sheet(s) in sheets/" % sheets) if sheets else ""))
        L.append("RESULT: %s. %d of %d frame(s) have measured problems; %d frame(s) not reached%s."
                 % (status, len(measured_problem_frames), len(frames), len(unreached), (" (" + ", ".join(record["summary"]["states_not_reached"]) + ")") if unreached else ""))
        L.append("The facts are aids. A frame with no measured problem can still be wrong: look at every row of the sheet.")
        return finish_result(receipt, flags, human="\n".join(L))


def build(plan, opts, flags):
    progress = {"frames": [], "sheet_names": [], "sheet_errors": [], "record": None, "output": {}}
    try:
        return _build(plan, opts, flags, progress)
    except Exception as e:
        reason = "Capture/output execution stopped: %s" % str(e).split("\n")[0][:160]
        frames = progress["frames"]
        attempted = len(frames)
        found = {frame_key(f) for f in frames}
        n = 0
        for state in plan["states"]:
            for size in plan["sizes"]:
                for theme in plan["themes"]:
                    n += 1
                    f = missing_frame(state, theme, size, "not attempted after execution stopped", "not attempted")
                    if frame_key(f) not in found:
                        f["index"] = n
                        frames.append(f)
        frames.sort(key=lambda f: f["index"])
        measured = [f for f in frames if f.get("measured_problems") or (f.get("facts") and problems_of(f["facts"]))]
        missing = [f for f in frames if not f["reached"]]
        status = "failed" if measured else ("partial" if attempted else "runner-error")
        coverage = {"requested_frames": plan["total"], "attempted_frames": attempted,
                    "captured_frames": sum(bool(f.get("_img")) for f in frames),
                    "measured_frames": sum(f.get("measured_facts") is not None or f.get("facts") is not None for f in frames),
                    "measured_problem_frames": len(measured), "missing_frames": len(missing),
                    "not_attempted_frames": plan["total"] - attempted,
                    "requested_sheets": 0 if "--no-sheets" in flags else len(plan["states"]) * len(plan["sizes"]),
                    "written_sheets": len(progress["sheet_names"])}
        receipt = receipt_for("capture", status, 3, coverage, [reason])
        receipt["execution_status"] = "runner-error"
        receipt["runner_errors"] = [{"stage": "capture/output", "reason": reason}]
        receipt["frame_evidence"] = [{k: v for k, v in f.items() if not k.startswith("_")} for f in frames]
        record = progress["record"] or {"tool": "state_gallery", "schema": SCHEMA, "page": plan["page"],
                                        "title": plan["title"], "states_file": plan["file"]}
        record["frames"] = [{k: v for k, v in f.items() if not k.startswith("_")} for f in frames]
        record.setdefault("summary", {})
        record["summary"].update(frames=len(frames), not_reached=len(missing),
                                  measured_problem_frames=len(measured), states_not_reached=sorted({f["state"] for f in missing}))
        output = dict(progress["output"])
        output.update(dir=str(progress.get("out_dir", "not created")), frame_pngs=sum(bool(f["png"]) for f in frames),
                      sheet_pngs=len(progress["sheet_names"]), sheets=list(progress["sheet_names"]),
                      final_record_written=False)
        record.update(status=status, phase="capture", receipt=receipt, output=output)
        if progress.get("out_dir"):
            try:
                output["final_record_written"] = True
                (progress["out_dir"] / "gallery.json").write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
            except OSError as write_error:
                output["final_record_written"] = False
                receipt["runner_errors"].append({"stage": "final receipt write", "reason": str(write_error)[:160]})
        return finish_result(receipt, flags, record)


# ---------------------------------------------------------------------------------------------
# Comparing two gallery.json files
# ---------------------------------------------------------------------------------------------
COMPARED = ("measurement_context", "thresholds", "overflow_px", "clipped_count", "contrast_lowest", "contrast_below", "small_targets", "console_errors", "failed_requests",
            "broken_answers", "refused_answers", "targets_under_44")


def load_gallery(path):
    d = read_json(path, "gallery file")
    if not isinstance(d, dict) or d.get("tool") != "state_gallery" or not isinstance(d.get("frames"), list):
        raise Bad("%s is not a gallery.json written by state_gallery" % path)
    if not is_int(d.get("schema")) or d["schema"] > SCHEMA:
        raise Bad("%s has schema %r; this script reads schema %d and older" % (path, d.get("schema"), SCHEMA))
    out = {}
    for f in d["frames"]:
        if not isinstance(f, dict) or not all(k in f for k in ("state", "theme", "width", "reached")):
            raise Bad("%s has a frame without state, theme, width and reached" % path)
        out[frame_key(f)] = f
    return out


def compare(old_path, new_path, flags):
    old, new = load_gallery(old_path), load_gallery(new_path)
    changed, same = [], 0
    for k in [k for k in new if k in old]:
        a, b, diffs = old[k], new[k], []
        if bool(a["reached"]) != bool(b["reached"]):
            diffs.append({"fact": "reached", "old": bool(a["reached"]), "new": bool(b["reached"])})
        fa, fb = a.get("facts") or {}, b.get("facts") or {}
        if a["reached"] and b["reached"]:
            for name in COMPARED:
                if fa.get(name) != fb.get(name):
                    diffs.append({"fact": name, "old": fa.get(name), "new": fb.get(name)})
        if len(a.get("problems", [])) != len(b.get("problems", [])):
            diffs.append({"fact": "measured problems", "old": len(a.get("problems", [])), "new": len(b.get("problems", []))})
        if diffs:
            changed.append({"frame": k, "changes": diffs})
        else:
            same += 1
    added, removed = [k for k in new if k not in old], [k for k in old if k not in new]
    common = len(set(old) & set(new))
    receipt = receipt_for("compare", "completed" if common else "not-applicable", 0,
                          {"common_frames": common, "changed": len(changed), "unchanged": same,
                           "added": len(added), "removed": len(removed), "captured_frames": 0},
                          [] if common else ["No common frame keys; added/removed keys are listed, no shared facts compared."])
    result = {"old": str(old_path), "new": str(new_path), "changed": changed, "added": added, "removed": removed, "unchanged": same,
              "note": "Measured facts only. Pixel comparison is out of scope."}
    if "--json" in flags:
        return finish_result(receipt, flags, result)
    L = ["state_gallery compare: %s (%d frame(s)) against %s (%d frame(s))" % (Path(old_path).name, len(old), Path(new_path).name, len(new))]
    for c in changed:
        L.append("  CHANGED  " + c["frame"])
        for d in c["changes"]:
            L.append("      %s: %s -> %s" % (d["fact"].replace("_", " "), d["old"], d["new"]))
    L += ["  ADDED    " + k for k in added] + ["  REMOVED  " + k for k in removed]
    L.append("RESULT: %d frame(s) changed, %d added, %d removed, %d unchanged." % (len(changed), len(added), len(removed), same))
    L.append("Measured facts only. Pixel comparison is out of scope: two frames with the same facts can look different, so look at both sheets.")
    return finish_result(receipt, flags, result, "\n".join(L))


def main(argv):
    output_flags = {"--json"} if "--json" in argv else set()
    phase = "compare" if "--compare" in argv else "validation"

    def invalid(reason):
        print("state_gallery: " + ascii_only(reason), file=sys.stderr)
        return stopped(phase, "runner-error", 2, reason, output_flags, {"captured_frames": 0})

    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--") or not v.strip():
                return invalid("%s needs a value" % a)
            opts[a] = v
        elif a.startswith("--"):
            return invalid("unknown option " + a)
        else:
            args.append(a)
    try:
        if "--compare" in flags:
            if len(args) != 2 or opts or (flags - {"--compare", "--json"}):
                return invalid("--compare takes OLD_gallery.json NEW_gallery.json and, optionally, --json")
            return compare(args[0], args[1], flags)
        if len(args) != 1:
            if "--json" not in flags:
                print(__doc__)
            return invalid("one states file is required")
        nums = {}
        for name, lo, hi, default in (("--max-image-width", 200, 3840, 1280), ("--quality", 30, 95, 70), ("--max-frames", 1, 2000, FRAMES_DEFAULT)):
            v = opts.get(name, str(default))
            if not v.isdigit() or not lo <= int(v) <= hi:
                return invalid("%s needs a whole number from %d to %d" % (name, lo, hi))
            nums[name] = int(v)
        sv = opts.get("--image-scale", "1")
        if not re.fullmatch(r"(0\.\d{1,3}|1(\.0{1,3})?)", sv) or not 0.25 <= float(sv) <= 1:
            return invalid("--image-scale needs a number from 0.25 to 1, written like 0.75")
        if opts.get("--encoding", "base64") not in ("base64", "hex"):
            return invalid("--encoding is base64 or hex")
        plan = load_plan(args[0], opts.get("--page"), nums["--max-frames"])
    except Bad as e:
        return invalid(str(e))
    except Exception as e:
        return stopped(phase, "runner-error", 3, "Operation could not finish: %s" % str(e).split("\n")[0][:160], output_flags)
    if "--dry-run" in flags:
        text = "state_gallery: %s is valid: %d state(s) x %d theme(s) x %d width(s) = %d frame(s). Nothing was captured (--dry-run)." % (plan["file"], len(plan["states"]), len(plan["themes"]), len(plan["sizes"]), plan["total"])
        return finish_result(receipt_for("validation", "completed", 0, {"planned_frames": plan["total"], "captured_frames": 0}), flags,
                             {"tool": "state_gallery", "valid": True, "planned_frames": plan["total"], "captured_frames": 0}, text)
    opts["_states_path"], opts["_maxw"], opts["_quality"], opts["_scale"] = args[0], nums["--max-image-width"], nums["--quality"], float(sv)
    return build(plan, opts, flags)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
