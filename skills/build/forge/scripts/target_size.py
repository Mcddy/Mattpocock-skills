#!/usr/bin/env python3
"""Apply WCAG 2.2 SC 2.5.8 Target Size (Minimum) geometry to a set of pointer targets.

Usage:
  python target_size.py RECTS.json [--json] [--fail-on-unresolved]
  python target_size.py --page PAGE.html [--width 390] [--height 844] [--prep-js "JS"] [--no-label-union] [--json] [--fail-on-unresolved]

RECTS.json is a list of targets in CSS pixels:
  [{"id": "save", "x": 10, "y": 10, "w": 20, "h": 20, "inline": false, "group": "optional"}, ...]
Targets that share a "group" perform the same action and are not tested against each other.
x, y, w and h are JSON numbers. "inline" is optional and must be the JSON value true or false.
"group" is optional and must be text or null. "id" is optional text or a number. Nothing is
coerced: "false", 0 and "20" are refused, with the target named, and the script exits 2. A
string "false" read as true would hand out the inline exception to a target that never asked for it.
PAGE.html may also be an http(s) address for a page served by a running back end.
--page needs the Python "playwright" package and a Chromium it can launch; without them the script
prints NOT RUN and exits 3.

What the criterion says (W3C, WCAG 2.2, Level AA), and what this script does with it:

  Size       A target meets the size if a 24 by 24 CSS pixel square fits inside it. For a rectangle:
             width >= 24 and height >= 24.
  Spacing    An undersized target passes if a 24 CSS pixel diameter circle centred on its bounding
             box does not intersect another target, and does not intersect the circle of another
             undersized target. Touching is not intersecting: two 20 by 20 targets 4px apart pass,
             and a 16 by 16 target 4px from a large one passes. Abutting targets fail.
  The other four exceptions cannot be decided from geometry: an equivalent control elsewhere on
  the page that meets the size, a target inline in a sentence, a control sized by the browser and
  not restyled, and a presentation that is essential or legally required.

So each target ends in one of three states:
  MEETS SIZE          24 by 24 or larger.
  PASSES BY SPACING   undersized, circle clear of every other target and undersized circle.
  CHECK EXCEPTIONS    undersized and not clear. It fails 2.5.8 unless one of the other four
                      exceptions applies. That needs a person. A link laid out inline inside running
                      text (display inline, at least three words around it), or a target declared
                      "inline": true in RECTS.json, gets the inline exception and is noted. A link that
                      may be inline but is not established (only separators around it) stays undecided,
                      so the run is partial; a block-style action link beside a separator is not inline.

24 by 24 is the AA criterion, not a design goal. Aim for 44 by 44 on primary and touch actions
(SC 2.5.5, Level AAA).

Interpretation, not W3C text: in --page mode a form control and its label are measured as one
target (their combined box), because a label accepts the pointer action for its control. Use
--no-label-union to measure the bare control. Overlapping targets with different actions are
reported and not measured, since the overlapping area must be left out of the size.

Exit codes: 0 completed: every target meets the size or passes by spacing. 1 with --fail-on-unresolved if any
target is CHECK EXCEPTIONS and not inline. 2 for bad arguments or unreadable input. 3 partial: some targets need
an exception decided by a person, some overlap and were not measured, or no targets were found. 4 runner error:
--page could not run (prints NOT RUN).
A RECEIPT line on stderr states the result (references/results.md).
"""
import json
import math
import sys
from pathlib import Path
import pathlib

VERSION = "forge 3.3.2"

SIZE = 24.0
R = SIZE / 2
EPS = 0.01
OPTIONS_FLAG = {"--json", "--fail-on-unresolved", "--no-label-union"}
OPTIONS_VALUE = {"--page", "--width", "--height", "--prep-js"}


def centre(t):
    return t["x"] + t["w"] / 2.0, t["y"] + t["h"] / 2.0


def undersized(t):
    return t["w"] < SIZE - EPS or t["h"] < SIZE - EPS


def circle_rect_gap(c, t):
    """Distance from circle centre c to the nearest point of rectangle t. 0 if the centre is inside."""
    dx = max(t["x"] - c[0], 0.0, c[0] - (t["x"] + t["w"]))
    dy = max(t["y"] - c[1], 0.0, c[1] - (t["y"] + t["h"]))
    return math.hypot(dx, dy)


def overlap(a, b):
    return (min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) > EPS
            and min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) > EPS)


def evaluate(targets):
    out = []
    for i, t in enumerate(targets):
        row = {"id": t.get("id", "target %d" % i), "w": round(t["w"], 2), "h": round(t["h"], 2), "conflicts": [], "notes": []}
        same = lambda o: t.get("group") is not None and t.get("group") == o.get("group")  # noqa: E731
        overl = [o.get("id", "?") for j, o in enumerate(targets) if j != i and not same(o) and overlap(t, o)]
        if overl:
            row["state"] = "OVERLAPS"
            row["notes"].append("overlaps %s: leave the shared area out of the size and measure by hand" % ", ".join(overl[:3]))
            out.append(row)
            continue
        if not undersized(t):
            row["state"] = "MEETS SIZE"
            out.append(row)
            continue
        c = centre(t)
        for j, o in enumerate(targets):
            if j == i or same(o):
                continue
            gap = circle_rect_gap(c, o)
            if gap < R - EPS:
                row["conflicts"].append({"with": o.get("id", "target %d" % j), "why": "circle reaches into this target", "short_by_px": round(R - gap, 2)})
            elif undersized(o):
                d = math.hypot(c[0] - centre(o)[0], c[1] - centre(o)[1])
                if d < SIZE - EPS:
                    row["conflicts"].append({"with": o.get("id", "target %d" % j), "why": "the two 24px circles overlap", "short_by_px": round(SIZE - d, 2)})
        if not row["conflicts"]:
            row["state"] = "PASSES BY SPACING"
        else:
            row["state"] = "CHECK EXCEPTIONS"
            how = t.get("inline")
            if how is True:
                row["notes"].append("declared inline in the input: the inline exception applies")
                row["exempt"] = True
            elif how == "sentence":
                row["notes"].append("inline in running text (display inline, words around it): the inline exception applies")
                row["exempt"] = True
            elif how == "uncertain":
                row["notes"].append("possibly inline (display inline, but only separators or a few characters around it): not established")
        out.append(row)
    return out


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def shown(v):
    """A short ASCII rendering of a refused value, for the error message."""
    kind = "text" if isinstance(v, str) else "number" if is_number(v) else "value"
    return "the %s %s" % (kind, json.dumps(v, ensure_ascii=True)[:40])


def valid_targets(data, from_page=False):
    """Return (targets, None) or (None, one-line reason naming the target). Nothing is coerced. RECTS.json may only
    declare inline as true or false; rectangles measured from a page may also carry the measured "sentence" or
    "uncertain"."""
    if not isinstance(data, list):
        return None, "the file must hold a JSON list of targets"
    clean = []
    for i, t in enumerate(data):
        if not isinstance(t, dict):
            return None, "target %d is not an object" % i
        tid = t.get("id", "target %d" % i)
        if isinstance(tid, bool) or not isinstance(tid, (str, int, float)):
            return None, "target %d: id must be text or a number" % i
        name = "target %d" % i if "id" not in t else "target %d (id %s)" % (i, json.dumps(str(tid), ensure_ascii=True)[:40])
        if not all(is_number(t.get(k)) for k in ("x", "y", "w", "h")):
            return None, "%s needs numeric x, y, w and h (JSON numbers; text and true or false are not numbers)" % name
        vals = {k: float(t[k]) for k in ("x", "y", "w", "h")}
        if not all(math.isfinite(v) for v in vals.values()) or vals["w"] <= 0 or vals["h"] <= 0:
            return None, "%s has a non-finite value or a width or height that is not positive" % name
        inline = t.get("inline", False)
        if not isinstance(inline, bool) and not (from_page and inline in ("sentence", "uncertain")):
            return None, "%s: inline must be true or false, not %s" % (name, shown(inline))
        group = t.get("group")
        if group is not None and not isinstance(group, str):
            return None, "%s: group must be text or null, not %s" % (name, shown(group))
        vals.update({"id": str(tid), "inline": inline, "group": group})
        clean.append(vals)
    return clean, None


EXTRACT_JS = r"""
(labelUnion) => {
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],[role=checkbox],[role=radio],[role=switch],[role=menuitem],[onclick]';
  const vis = e => { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility !== 'visible' || cs.pointerEvents === 'none') return false;
    const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const out = []; let n = 0;
  const all = [...document.querySelectorAll(sel)].filter(e => vis(e) && !e.disabled);
  const bare = new Map(all.map(e => { const r = e.getBoundingClientRect(); return [e, {l: r.left, t: r.top, r: r.right, b: r.bottom}]; }));
  const hits = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
  all.forEach(e => {
    let box = {...bare.get(e)};
    if (labelUnion && /^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName)) {
      // A label that wraps its control joins it. A separate label joins only when the combined box would not
      // swallow another target (a label above a field, with chips between, stays separate).
      [...(e.labels || [])].forEach(l => { if (!vis(l)) return; const q = l.getBoundingClientRect();
        const u = {l: Math.min(box.l, q.left), t: Math.min(box.t, q.top), r: Math.max(box.r, q.right), b: Math.max(box.b, q.bottom)};
        const swallows = !l.contains(e) && all.some(o => o !== e && !l.contains(o) && hits(u, bare.get(o)));
        if (!swallows) box = u; });
    }
    const p = e.parentElement;
    // Inline exception (WCAG 2.5.8): the target is in a sentence, or its size is set by the line-height of the text
    // around it. Established only for a link that is laid out inline (display: inline) inside running text with words
    // around it. A block-style action link (block, inline-block, flex, grid) beside a separator is not in a sentence.
    let inline = false;
    if (e.tagName === 'A' && p && getComputedStyle(e).display === 'inline') {
      const around = [...p.childNodes].filter(c => c.nodeType === 3).map(c => c.nodeValue).join(' ').trim();
      const words = around.split(/\s+/).filter(w => /[A-Za-z\u00C0-\u024F]{2,}/.test(w)).length;
      inline = words >= 3 ? 'sentence' : (around.length ? 'uncertain' : false);
    }
    const name = (e.id ? '#' + e.id : e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/)[0] : '')) + ' ' + JSON.stringify((e.getAttribute('aria-label') || e.textContent || e.value || '').trim().slice(0, 18));
    out.push({id: (n++) + ' ' + name, x: box.l + scrollX, y: box.t + scrollY, w: box.r - box.l, h: box.b - box.t, inline});
  });
  // an element nested inside another interactive element shares its action
  return out;
}
"""


def is_url(s):
    return s.lower().startswith(("http://", "https://"))


def from_page(page_path, width, height, label_union, prep=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        return None, "NOT RUN: the playwright package is not available (%s)" % str(e)[:80]
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            return None, "NOT RUN: Chromium could not be launched (%s)" % str(e)[:120]
        page = browser.new_page(viewport={"width": width, "height": height})
        try:
            page.goto(page_path if is_url(page_path) else Path(page_path).resolve().as_uri(), timeout=10000)
        except Exception as e:  # noqa: BLE001
            browser.close()
            return None, "NOT RUN: the page did not load (%s)" % str(e).split("\n")[0][:100]
        page.wait_for_timeout(500)
        if prep:
            page.evaluate("async () => { %s\n }" % prep); page.wait_for_timeout(400)
        rects = page.evaluate(EXTRACT_JS, label_union)
        browser.close()
    return rects, None


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    flags, values, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in OPTIONS_FLAG:
            flags.add(a)
        elif a in OPTIONS_VALUE:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("target_size: %s needs a value" % a, file=sys.stderr)
                return 2
            values[a] = v
        elif a.startswith("--"):
            print("target_size: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if "--page" in values:
        if args:
            print("target_size: give either RECTS.json or --page, not both", file=sys.stderr)
            return 2
        try:
            w, h = int(values.get("--width", "390")), int(values.get("--height", "844"))
            if w <= 0 or h <= 0:
                raise ValueError
        except ValueError:
            print("target_size: --width and --height need positive whole numbers", file=sys.stderr)
            return 2
        if not is_url(values["--page"]) and not Path(values["--page"]).is_file():
            print("target_size: cannot read " + values["--page"], file=sys.stderr)
            return 2
        data, err = from_page(values["--page"], w, h, "--no-label-union" not in flags, values.get("--prep-js"))
        if err:
            print(err)
            return 4
    else:
        if len(args) != 1:
            print(__doc__)
            return 2
        try:
            data = json.loads(Path(args[0]).read_bytes().decode("utf-8-sig"))
        except OSError as e:
            print("target_size: cannot read %s: %s" % (args[0], e.strerror or e), file=sys.stderr)
            return 2
        except (UnicodeDecodeError, ValueError) as e:
            print("target_size: %s is not valid UTF-8 JSON (%s)" % (args[0], str(e)[:60]), file=sys.stderr)
            return 2
    targets, err = valid_targets(data, from_page="--page" in values)
    if err:
        print("target_size: " + err, file=sys.stderr)
        return 2
    rows = evaluate(targets)
    counts = {s: sum(1 for r in rows if r["state"] == s) for s in ("MEETS SIZE", "PASSES BY SPACING", "CHECK EXCEPTIONS", "OVERLAPS")}
    unresolved = [r for r in rows if r["state"] == "CHECK EXCEPTIONS" and not r.get("exempt")]
    if "--json" in flags:
        text = json.dumps({"counts": counts, "targets": rows}, indent=1, ensure_ascii=True)
    else:
        L = ["target_size: %d target(s): %d meet 24 by 24, %d pass by spacing, %d need another exception checked, %d overlap"
             % (len(rows), counts["MEETS SIZE"], counts["PASSES BY SPACING"], counts["CHECK EXCEPTIONS"], counts["OVERLAPS"])]
        for r in rows:
            if r["state"] in ("MEETS SIZE",):
                continue
            L.append("  %-17s %-34s %gx%g%s" % (r["state"], r["id"][:34], r["w"], r["h"], ("  " + "; ".join(r["notes"])) if r["notes"] else ""))
            for c in r["conflicts"][:4]:
                L.append("      %s: %s (short by %gpx)" % (c["with"][:34], c["why"], c["short_by_px"]))
        L.append("CHECK EXCEPTIONS means: fails unless an equivalent control, inline, browser-default or essential exception applies.")
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    overlaps = [r for r in rows if r["state"] == "OVERLAPS"]
    if unresolved and "--fail-on-unresolved" in flags:
        code = 1
    else:
        # undecided exceptions and overlapping targets were not measured, and no targets says nothing: partial
        code = 3 if (unresolved or overlaps or not rows) else 0
    RECEIPT.update({"source": values.get("--page") or (args[0] if args else None), "targets": len(rows), "counts": counts,
                    "undecided_exceptions": [r["id"] for r in unresolved][:30], "overlapping": [r["id"] for r in overlaps][:30],
                    "criterion": "WCAG 2.2 SC 2.5.8 geometry only; the four non-geometric exceptions are not decided"})
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
    sys.exit(_contract("target_size", main, sys.argv[1:]))
