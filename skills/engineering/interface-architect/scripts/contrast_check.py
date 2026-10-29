#!/usr/bin/env python3
"""Measure text contrast on a rendered page, as the browser computed it.

Usage:
  python contrast_check.py PAGE [--set "SELECTOR@ATTR=VALUE"]... [--click SELECTOR]...
                                [--width 1100] [--height 800] [--json]

PAGE is an HTML file or an http(s) address. --set changes an attribute before measuring, which is
how a theme is selected, for example --set "html@data-theme=ember". --click opens something first.

What it does: for every visible element that directly holds text, it takes the computed text colour
and the nearest solid background behind it, and works out the WCAG contrast ratio. It compares that
with SC 1.4.3 Contrast (Minimum), Level AA: 4.5 to 1, or 3 to 1 for large text (at least 24 CSS
pixels, or at least 18.66 CSS pixels and bold).

What it cannot do, and says so in its output:
  - Text over an image or a gradient is listed as NOT MEASURED. Check those by eye or by sampling.
  - It measures the state the page is in. Hover, focus, error and disabled states need their own run
    or a look. Disabled controls are skipped: the criterion exempts them.
  - Placeholder text, text in images and non-text contrast (SC 1.4.11: borders, icons, focus rings)
    are not measured.
A clean result means the measured text meets 1.4.3 in that state. It is not an accessibility audit.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes (references/results.md): 0 completed: text was measured, none below its threshold, none left
unmeasured. 1 failed: some measured text is below. 2 usage error. 3 partial: nothing below, but some text could not
be measured (over an image or gradient) or nothing was measured at all; that text is missing coverage, not a pass.
4 runner error (prints NOT RUN). The RECEIPT line on stderr gives the counts and the reasons text went unmeasured.
"""
import json
import sys
from pathlib import Path
import pathlib

VERSION = "forge 3.3.2"

FLAGS = {"--json"}
VALUES = {"--set", "--click", "--width", "--height"}

MEASURE_JS = r"""
() => {
  const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d', {willReadFrequently: true});
  // rgb()/rgba() directly; anything else Chromium may report (color(srgb ...) from color-mix, oklab(), oklch()) through a canvas pixel.
  const parse = s => { if (!s || s === 'transparent') return null; const m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const p = m[1].split(/[,\s\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; }
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = 'rgba(1, 2, 3, 0.5)'; const before = cx.fillStyle; cx.fillStyle = s;
    if (cx.fillStyle === before && s.replace(/\s/g, '') !== 'rgba(1,2,3,0.5)') return null;
    cx.fillRect(0, 0, 1, 1); const d = cx.getImageData(0, 0, 1, 1).data; return {r: d[0], g: d[1], b: d[2], a: d[3] / 255}; };
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


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    flags, opts, sets, clicks, args, it = set(), {}, [], [], [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip():
                print("contrast_check: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--set":
                at = v.rfind("@")
                if at < 1 or "=" not in v[at:]:
                    print("contrast_check: --set needs SELECTOR@ATTR=VALUE, got %r" % v, file=sys.stderr)
                    return 2
                attr, val = v[at + 1:].split("=", 1)
                sets.append((v[:at].strip(), attr.strip(), val))
            elif a == "--click":
                clicks.append(v)
            else:
                opts[a] = v
        elif a.startswith("--"):
            print("contrast_check: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    served = args[0].lower().startswith(("http://", "https://"))
    if not served and not Path(args[0]).is_file():
        print("contrast_check: cannot read " + args[0], file=sys.stderr)
        return 2
    try:
        width, height = int(opts.get("--width", "1100")), int(opts.get("--height", "800"))
        if width <= 0 or height <= 0:
            raise ValueError
    except ValueError:
        print("contrast_check: --width and --height need positive whole numbers", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 4
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e)[:120])
            return 4
        page = browser.new_page(viewport={"width": width, "height": height})
        try:
            page.goto(args[0] if served else Path(args[0]).resolve().as_uri(), timeout=10000)
            page.wait_for_timeout(500)
            for sel in clicks:
                page.locator(sel).first.click(timeout=3000)
            for sel, attr, val in sets:
                if page.locator(sel).count() == 0:
                    raise RuntimeError("nothing matches %r" % sel)
                page.locator(sel).first.evaluate("(e, a) => e.setAttribute(a[0], a[1])", [attr, val])
            page.wait_for_timeout(450)          # let colour transitions finish before reading colours
            rows = page.evaluate(MEASURE_JS)
        except Exception as e:  # noqa: BLE001
            browser.close()
            print("NOT RUN: %s" % str(e).split("\n")[0][:140])
            return 4
        browser.close()
    measured = [r for r in rows if r["measured"]]
    low = sorted([r for r in measured if r["ratio"] < r["need"]], key=lambda r: r["ratio"])
    unmeasured = [r for r in rows if not r["measured"]]
    state = ", ".join("%s %s=%s" % s for s in sets) or "as loaded"
    if "--json" in flags:
        text = json.dumps({"page": args[0], "state": state, "measured": len(measured), "below": low, "not_measured": unmeasured,
                           "lowest": min((r["ratio"] for r in measured), default=None)}, indent=1, ensure_ascii=True)
    else:
        L = ["contrast_check: %s (%s): %d text element(s) measured, %d below the AA threshold, %d not measured"
             % (args[0] if served else Path(args[0]).name, state, len(measured), len(low), len(unmeasured))]
        for r in low[:25]:
            L.append("  BELOW  %.2f (needs %s)  %s on %s  %-18s %r" % (r["ratio"], r["need"], r["fg"], r["bg"], r["el"][:18], r["text"]))
        for r in unmeasured[:10]:
            L.append("  NOT MEASURED (%s)  %-18s %r" % (r["why"], r["el"][:18], r["text"]))
        if len(unmeasured) > 10:
            L.append("  ... and %d more not measured" % (len(unmeasured) - 10))
        if measured:
            L.append("  lowest measured ratio: %.2f" % min(r["ratio"] for r in measured))
        if not measured:
            L.append("  No text was measured, so this says nothing about the page.")
        L.append("Measures text in the current state only. Hover, focus, error states and non-text contrast are not covered.")
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    # Text the scanner could not measure (over an image or gradient) is missing coverage, not a pass and not
    # "not applicable": the run is partial. Nothing measured at all is partial too. Disabled controls are exempt by
    # the criterion and are not counted (they are skipped before measuring).
    code = 1 if low else (3 if (unmeasured or not measured) else 0)
    RECEIPT.update({"page": args[0], "state": state, "measured": len(measured), "below_threshold": len(low),
                    "not_measured": len(unmeasured), "not_measured_reasons": sorted({r["why"] for r in unmeasured}),
                    "lowest_ratio": round(min((r["ratio"] for r in measured), default=0), 2) if measured else None,
                    "criterion": "WCAG 2.x SC 1.4.3, text in the state measured"})
    return code

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
    sys.exit(_contract("contrast_check", main, sys.argv[1:]))
