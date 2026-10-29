#!/usr/bin/env python3
"""Regression tests for state_gallery.py and the gallery page it writes. Run after changing either.

Usage:
  python test_state_gallery.py [--script PATH/state_gallery.py] [--keep DIR] [--json]

What it does. It writes two small fixture pages into a temporary folder (they are generated here,
so the tests need no other file), runs state_gallery.py on them as a separate process, and checks
what came out. One fixture has planted defects; the other is served from a loopback address by a
server this test starts on a free port and stops again. Nothing leaves the machine.

Named tests (each prints PASS or FAIL):
  overflow-right-frames      sideways overflow is flagged in the long state at 390, and nowhere else
  contrast-right-frames      low contrast is flagged in every frame of the dim theme, and nowhere else
  blank-state-not-measured   the blank empty state in the clean theme has NO measured problem:
                             measurement cannot see it, which is why a person must look
  unreached-is-labelled      a state whose step fails is in gallery.json as not reached and on the
                             sheet as a labelled empty frame
  fail-on-problems           exit 1 with --fail-on-problems on the planted page, exit 0 on a clean one
  compare-detects-change     --compare names the frames whose facts changed after the overflow is
                             fixed, names an added and a removed frame, and reports no change
                             between a gallery and itself
  bad-input-exits-2          unknown step kind, missing page, empty widths and nine more refusals,
                             each beside the nearest valid file, which must pass --dry-run
  route-fail-and-delay       on a served page, route_fail shows the error state without counting
                             the aborted request as a console error, and route_delay shows the
                             loading state
  answers-classified         a data request answered 422 is a reported fact and not a problem; a
                             500, a missing image and a console error written by the page are
                             each a problem
  sheets-hold-the-captures   the per-state sheet pictures exist for every state and width and
                             show the captured page, not an empty mat
  not-run-exits-3            an address nothing listens on exits 3 with NOT RUN
  sheet-in-tab-and-frame     the gallery page lays out every frame, opens one at full size, returns
                             focus on close, filters to problems, hides a width, changes theme and
                             resets, in a tab and inside <iframe sandbox="allow-scripts">
  hex-encoding               a gallery written with --encoding hex shows its images
  image-scale                --image-scale 0.5 embeds a 1280 capture 640 wide, says so in its data,
                             and leaves the picture in frames/ at full size

What it cannot tell: whether the sheet is pleasant to read, or whether the facts are the right
facts to measure. Look at a real gallery for that.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes: 0 every test passed. 1 a test failed. 2 bad arguments. 3 NOT RUN.
"""
import http.server
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

FLAGS = {"--json"}
VALUES = {"--script", "--keep"}

PLANTED = """<!doctype html>
<html lang="en" data-theme="paper"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Fixture</title>
<style>
:root{--bg:#f5efe4;--ink:#2a2320;--muted:#655a50}
:root[data-theme="dim"]{--bg:#262230;--ink:#efeaf5;--muted:#5f5872}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
.muted{color:var(--muted)}
button{min-height:44px;padding:0 14px;font:inherit}
li{padding:8px 0}
.code{white-space:NOWRAP_OR_NOT;font-family:monospace;overflow-wrap:anywhere}
</style></head><body>
<h1>Returns desk</h1>
<p class="muted" id="tally">Nothing logged.</p>
<ul id="list"></ul>
<button type="button" id="load">Load three returns</button>
<button type="button" id="load-long">Add a return with a long code</button>
<script>
(function () {
  var list = document.getElementById('list');
  function add(text, code) {
    var li = document.createElement('li');
    li.appendChild(document.createTextNode(text + ' '));
    var c = document.createElement('span'); c.className = 'code'; c.textContent = code; li.appendChild(c);
    list.appendChild(li);
    document.getElementById('tally').textContent = list.children.length + ' logged.';
  }
  document.getElementById('load').addEventListener('click', function () { add('Kettle', 'RT-1001'); add('Lamp', 'RT-1002'); add('Scales', 'RT-1003'); });
  document.getElementById('load-long').addEventListener('click', function () { add('Heater', 'RT-2026-10-08-WAREHOUSE-B-AISLE-14-SHELF-3-RETURN-TO-SUPPLIER-000042'); });
})();
</script></body></html>
"""

SERVED = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Served fixture</title><style>body{font:16px/1.5 system-ui,sans-serif;padding:16px;background:#fff;color:#222}</style></head><body>
<h1>Returns desk</h1><p id="state">Loading the list.</p><ul id="list"></ul>
<button type="button" id="refuse">Send an invalid return</button>
<button type="button" id="broken">Ask the broken report</button>
<button type="button" id="picture">Show the missing picture</button>
<button type="button" id="shout">Write a console error</button>
<p id="said"></p>
<script>
function ask(path) { fetch(path).then(function (r) { document.getElementById('said').textContent = 'Answer ' + r.status; }); }
document.getElementById('refuse').addEventListener('click', function () { ask('/api/refuse'); });
document.getElementById('broken').addEventListener('click', function () { ask('/api/broken'); });
document.getElementById('picture').addEventListener('click', function () { var i = new Image(); i.alt = 'missing'; i.src = '/missing.png'; i.onerror = function () { document.getElementById('said').textContent = 'No picture'; }; document.body.appendChild(i); });
document.getElementById('shout').addEventListener('click', function () { console.error('the page wrote this'); document.getElementById('said').textContent = 'Shouted'; });
fetch('/api/items').then(function (r) { return r.json(); }).then(function (d) {
  document.getElementById('state').textContent = d.items.length + ' returns.';
  d.items.forEach(function (t) { var li = document.createElement('li'); li.textContent = t; document.getElementById('list').appendChild(li); });
}, function () { document.getElementById('state').textContent = 'The server did not answer. Nothing was changed.'; });
</script></body></html>
"""


def planted_states(extra_state=None, drop_state=None):
    states = [
        {"name": "empty", "steps": ["expect-count:#list li=0"]},
        {"name": "populated", "steps": ["click:#load", "expect-count:#list li=3"]},
        {"name": "long code", "steps": ["click:#load-long", "expect-count:#list li=1"]},
        {"name": "archive", "steps": ["click:#open-archive"]},
    ]
    if drop_state:
        states = [s for s in states if s["name"] != drop_state]
    if extra_state:
        states.append({"name": extra_state, "steps": []})
    return {"page": "planted.html", "widths": [390, 1280],
            "themes": [{"name": "paper", "set": "html@data-theme=paper"}, {"name": "dim", "set": "html@data-theme=dim"}],
            "states": states}


class Quiet(http.server.BaseHTTPRequestHandler):
    page = b""

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        status = 200
        if self.path.startswith("/api/items"):
            body, kind = json.dumps({"items": ["Kettle", "Lamp"]}).encode("ascii"), "application/json"
        elif self.path in ("/api/refuse", "/api/broken", "/missing.png"):
            status = {"/api/refuse": 422, "/api/broken": 500, "/missing.png": 404}[self.path]
            body, kind = b"{}", "application/json"
        else:
            body, kind = self.page, "text/html; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(argv):
    flags, opts, it = set(), {}, iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_state_gallery: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        else:
            print("test_state_gallery: unknown argument " + a, file=sys.stderr)
            return 2
    script = Path(opts.get("--script", str(Path(__file__).resolve().parent / "state_gallery.py")))
    if not script.is_file():
        print("test_state_gallery: cannot find " + str(script), file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 3

    results = []

    def record(name, ok, detail=""):
        results.append({"test": name, "ok": bool(ok), "detail": detail})
        if "--json" not in flags:
            print(("%-5s %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + detail + "]") if (detail and not ok) else "")).encode("ascii", "replace").decode("ascii"), flush=True)

    def run(*args):
        r = subprocess.run([sys.executable, str(script)] + [str(a) for a in args], capture_output=True, text=True, timeout=540)
        return r.returncode, r.stdout, r.stderr

    keep = opts.get("--keep")
    holder = None if keep else tempfile.TemporaryDirectory()
    root = Path(keep) if keep else Path(holder.name)
    root.mkdir(parents=True, exist_ok=True)
    try:
        (root / "planted.html").write_text(PLANTED.replace("NOWRAP_OR_NOT", "nowrap"), encoding="utf-8")
        (root / "states.json").write_text(json.dumps(planted_states()), encoding="utf-8")
        code, out, err = run(root / "states.json", "--out", root / "g1")
        if code == 3:
            print(out.strip() or "NOT RUN")
            return 3
        if code != 0 or not (root / "g1" / "gallery.json").is_file():
            record("build", False, "exit %d: %s %s" % (code, out.strip()[-200:], err.strip()[-200:]))
            raise SystemExit
        g1 = json.loads((root / "g1" / "gallery.json").read_text(encoding="utf-8"))
        frames = {"%s/%s/%d" % (f["state"], f["theme"], f["width"]): f for f in g1["frames"]}

        over = sorted(k for k, f in frames.items() if f["reached"] and f["facts"]["overflow_px"] > 1)
        want = sorted(["long code/paper/390", "long code/dim/390"])
        record("overflow-right-frames", over == want, "flagged %s, expected %s" % (over, want))

        low = sorted(k for k, f in frames.items() if f["reached"] and f["facts"]["contrast_below"] > 0)
        want = sorted(k for k, f in frames.items() if f["reached"] and f["theme"] == "dim")
        record("contrast-right-frames", low == want and len(want) == 6, "flagged %s, expected %s" % (low, want))

        blank = [frames["empty/paper/390"], frames["empty/paper/1280"]]
        record("blank-state-not-measured", all(f["reached"] and not f["problems"] for f in blank),
               "the blank empty state was flagged: %s" % [f["problems"] for f in blank])

        missed = [f for f in g1["frames"] if not f["reached"]]
        ok = (len(missed) == 4 and all(f["state"] == "archive" and f["facts"] is None and f["problems"] for f in missed)
              and len(g1["frames"]) == 16 and g1["summary"]["not_reached"] == 4)
        record("unreached-is-labelled (json)", ok, "%d not reached of %d" % (len(missed), len(g1["frames"])))

        code_f, _, _ = run(root / "states.json", "--out", root / "g1b", "--fail-on-problems", "--no-sheets")
        clean = {"page": "planted.html", "widths": [1280], "states": [{"name": "populated", "steps": ["click:#load"]}]}
        (root / "clean.json").write_text(json.dumps(clean), encoding="utf-8")
        code_c, out_c, _ = run(root / "clean.json", "--out", root / "gclean", "--fail-on-problems", "--no-sheets")
        record("fail-on-problems", code_f == 1 and code_c == 0, "planted exit %d (want 1), clean exit %d (want 0)" % (code_f, code_c))

        # the same page with the overflow fixed, one state added and one dropped
        (root / "planted.html").write_text(PLANTED.replace("NOWRAP_OR_NOT", "normal"), encoding="utf-8")
        (root / "states2.json").write_text(json.dumps(planted_states(extra_state="as loaded again", drop_state="archive")), encoding="utf-8")
        code, out, err = run(root / "states2.json", "--out", root / "g2", "--no-sheets")
        code_cmp, out_cmp, _ = run("--compare", root / "g1" / "gallery.json", root / "g2" / "gallery.json", "--json")
        cmp_ = json.loads(out_cmp) if code_cmp == 0 else {}
        changed = sorted(c["frame"] for c in cmp_.get("changed", []))
        facts = sorted({d["fact"] for c in cmp_.get("changed", []) for d in c["changes"]})
        code_same, out_same, _ = run("--compare", root / "g1" / "gallery.json", root / "g1" / "gallery.json", "--json")
        same = json.loads(out_same) if code_same == 0 else {"changed": ["?"]}
        ok = (changed == ["long code / dim / 390", "long code / paper / 390"] and "overflow_px" in facts
              and len(cmp_.get("added", [])) == 4 and len(cmp_.get("removed", [])) == 4
              and same["changed"] == [] and same["unchanged"] == 16)
        record("compare-detects-change", ok, "changed %s facts %s added %d removed %d; self-compare changed %s"
               % (changed, facts, len(cmp_.get("added", [])), len(cmp_.get("removed", [])), same.get("changed")))
        (root / "planted.html").write_text(PLANTED.replace("NOWRAP_OR_NOT", "nowrap"), encoding="utf-8")

        # refusals, each beside its valid neighbour
        base = {"page": "planted.html", "widths": [390], "states": [{"name": "a", "steps": ["click:#load"]}]}

        def variant(change):
            d = json.loads(json.dumps(base))
            change(d)
            return d
        pairs = [
            ("unknown step kind", variant(lambda d: d["states"][0].__setitem__("steps", ["tap:#load"])), variant(lambda d: d["states"][0].__setitem__("steps", ["click:#load"]))),
            ("missing page", variant(lambda d: d.__setitem__("page", "no-such-page.html")), base),
            ("empty widths", variant(lambda d: d.__setitem__("widths", [])), variant(lambda d: d.__setitem__("widths", [390]))),
            ("width 239", variant(lambda d: d.__setitem__("widths", [239])), variant(lambda d: d.__setitem__("widths", [240]))),
            ("width 3841", variant(lambda d: d.__setitem__("widths", [3841])), variant(lambda d: d.__setitem__("widths", [3840]))),
            ("width as text", variant(lambda d: d.__setitem__("widths", ["390"])), base),
            ("width true", variant(lambda d: d.__setitem__("widths", [True])), base),
            ("unknown state key", variant(lambda d: d["states"][0].__setitem__("route_fial", ["**"])), variant(lambda d: d["states"][0].__setitem__("route_fail", ["**"]))),
            ("state listed twice", variant(lambda d: d["states"].append({"name": "A"})), variant(lambda d: d["states"].append({"name": "b"}))),
            ("empty themes", variant(lambda d: d.__setitem__("themes", [])), variant(lambda d: d.__setitem__("themes", [{"name": "x", "set": "html@data-theme=dim"}]))),
            ("theme set malformed", variant(lambda d: d.__setitem__("themes", [{"name": "x", "set": "html data-theme"}])), base),
            ("wait not a number", variant(lambda d: d["states"][0].__setitem__("steps", ["wait:soon"])), variant(lambda d: d["states"][0].__setitem__("steps", ["wait:50"]))),
        ]
        bad_ok, notes = True, []
        for label, bad, good in pairs:
            (root / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
            (root / "good.json").write_text(json.dumps(good), encoding="utf-8")
            cb, _, eb = run(root / "bad.json", "--dry-run")
            cg, _, _ = run(root / "good.json", "--dry-run")
            if cb != 2 or cg != 0 or "Traceback" in eb or not eb.strip():
                bad_ok = False
                notes.append("%s: refused exit %d, neighbour exit %d" % (label, cb, cg))
        (root / "raw.json").write_bytes(b'{"page": "planted.html", "widths": [390], "states": [{"name": "' + bytes([255]) + b'"}]}')
        c1, _, _ = run(root / "raw.json", "--dry-run")
        (root / "raw.json").write_bytes(b"{\"page\": \"planted.html\", " + bytes([0]) + b"\"widths\": [390]}")
        c2, _, _ = run(root / "raw.json", "--dry-run")
        (root / "raw.json").write_bytes(b"{not json")
        c3, _, _ = run(root / "raw.json", "--dry-run")
        (root / "twelve.json").write_text(json.dumps(planted_states()), encoding="utf-8")
        c4, _, _ = run(root / "twelve.json", "--dry-run", "--max-frames", "15")
        c5, _, _ = run(root / "twelve.json", "--dry-run", "--max-frames", "16")
        c6, _, e6 = run(root / "twelve.json", "--frobnicate")
        c7, _, _ = run(root / "twelve.json", "--out")
        c8, _, _ = run(root / "twelve.json", "--dry-run", "--image-scale", "0.24")
        c9, _, _ = run(root / "twelve.json", "--dry-run", "--image-scale", "0.25")
        c10, _, _ = run(root / "twelve.json", "--dry-run", "--image-scale", "1.01")
        c11, _, _ = run(root / "twelve.json", "--dry-run", "--image-scale", "1")
        got = (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11)
        if got != (2, 2, 2, 2, 0, 2, 2, 2, 0, 2, 0) or "Traceback" in e6:
            bad_ok = False
            notes.append("bytes, limits and options gave exits %s, want (2, 2, 2, 2, 0, 2, 2, 2, 0, 2, 0)" % (got,))
        record("bad-input-exits-2", bad_ok, "; ".join(notes))

        # a served page: error and loading states by interfering with requests
        Quiet.page = SERVED.encode("utf-8")
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            served = {"page": "http://127.0.0.1:%d/" % port, "widths": [390], "states": [
                {"name": "loaded", "steps": ["expect:#state=2 returns"]},
                {"name": "loading", "route_delay": ["**/api/**"], "steps": ["expect:#state=Loading the list", "expect-count:#list li=0"]},
                {"name": "server down", "route_fail": [{"url": "**/api/items", "method": "GET"}], "steps": ["expect:#state=did not answer"]},
                {"name": "post only is not matched", "route_fail": [{"url": "**/api/items", "method": "POST"}], "steps": ["expect:#state=2 returns"]},
                {"name": "refused 422", "steps": ["click:#refuse", "expect:#said=Answer 422"]},
                {"name": "broken 500", "steps": ["click:#broken", "expect:#said=Answer 500"]},
                {"name": "missing picture", "steps": ["click:#picture", "expect:#said=No picture"]},
                {"name": "console error", "steps": ["click:#shout", "expect:#said=Shouted"]}]}
            (root / "served.json").write_text(json.dumps(served), encoding="utf-8")
            code, out, err = run(root / "served.json", "--out", root / "gs", "--no-sheets")
            gs = json.loads((root / "gs" / "gallery.json").read_text(encoding="utf-8")) if code == 0 else {"frames": []}
            by = {f["state"]: f for f in gs["frames"]}
            first = ["loaded", "loading", "server down", "post only is not matched"]
            ok = (len(by) == 8 and all(f["reached"] for f in by.values())
                  and by["server down"]["facts"]["console_errors"] == 0 and by["server down"]["facts"]["failed_requests"] == 0
                  and by["server down"]["facts"]["requests_aborted_on_purpose"] == 1
                  and by["loading"]["facts"]["requests_held_on_purpose"] == 1 and not any(by[k]["problems"] for k in first))
            record("route-fail-and-delay", ok, "exit %d; %s" % (code, [(f["state"], f["reached"], f["problems"]) for f in gs["frames"]]))
            f422, f500, f404, fcon = (by.get(k, {}).get("facts") or {} for k in ("refused 422", "broken 500", "missing picture", "console error"))
            ok = (f422.get("refused_answers") == 1 and not by["refused 422"]["problems"]
                  and f500.get("broken_answers") == 1 and len(by["broken 500"]["problems"]) == 1
                  and f404.get("broken_answers") == 1 and len(by["missing picture"]["problems"]) == 1
                  and fcon.get("console_errors") == 1 and len(by["console error"]["problems"]) == 1)
            record("answers-classified", ok, "422 %s | 500 %s | 404 image %s | console %s"
                   % (by["refused 422"]["problems"], by["broken 500"]["problems"], by["missing picture"]["problems"], by["console error"]["problems"]))
        finally:
            httpd.shutdown()
            httpd.server_close()
        gone = {"page": "http://127.0.0.1:%d/" % port, "widths": [390], "states": [{"name": "a"}]}
        (root / "gone.json").write_text(json.dumps(gone), encoding="utf-8")
        code, out, _ = run(root / "gone.json", "--out", root / "ggone")
        record("not-run-exits-3", code == 3 and out.startswith("NOT RUN"), "exit %d: %s" % (code, out.strip()[:80]))

        # the sheet itself, in a tab and in a sandboxed frame
        gallery = (root / "g1" / "gallery.html").resolve()
        (root / "frame.html").write_text('<!doctype html><html lang="en"><title>frame</title><body style="margin:0">'
                                         '<iframe id="f" sandbox="allow-scripts" src="%s" style="border:0;width:100vw;height:100vh"></iframe></body></html>' % gallery.as_uri(), encoding="utf-8")
        code_h, _, _ = run(root / "clean.json", "--out", root / "ghex", "--encoding", "hex", "--no-sheets")
        code_s, _, _ = run(root / "clean.json", "--out", root / "ghalf", "--image-scale", "0.5", "--no-sheets")
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:  # noqa: BLE001
                print("NOT RUN: Chromium could not be launched (%s)" % str(e)[:120])
                return 3
            for mode in ("tab", "frame"):
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors = []
                page.on("pageerror", lambda e, errors=errors: errors.append(str(e)[:120]))
                page.goto(gallery.as_uri() if mode == "tab" else (root / "frame.html").resolve().as_uri())
                page.wait_for_timeout(500)
                t = page if mode == "tab" else [f for f in page.frames if f != page.main_frame][0]
                why = []

                def need(cond, text):
                    if not cond:
                        why.append(text)
                page.set_default_timeout(4000)
                try:
                    need(t.locator(".frame").count() == 16, "16 frames laid out, found %d" % t.locator(".frame").count())
                    need(t.locator(".thumb.none").count() == 4, "4 labelled empty frames, found %d" % t.locator(".thumb.none").count())
                    need("Not reached" in (t.locator(".thumb.none").first.text_content() or ""), "the empty frame says Not reached")
                    need(t.locator("section.state").nth(3).locator(".cap").first.text_content().find("nothing matches the selector") >= 0, "the caption gives the reason")
                    loaded = t.evaluate("() => [...document.querySelectorAll('.thumb img')].every(i => i.complete && i.naturalWidth > 0)")
                    need(loaded and t.locator(".thumb img").count() == 12, "12 captures decoded")
                    key = "long code / paper / 390"
                    t.locator('.thumb[data-key="%s"]' % key).click()
                    need(t.locator("#viewer").is_visible(), "the viewer opens")
                    need("long code, paper, 390 by 844" in (t.locator("#v-title").text_content() or ""), "the viewer names the frame")
                    need("Overflows sideways" in (t.locator("#v-facts").text_content() or ""), "the viewer lists the measured problem")
                    t.locator("#v-next").click()
                    need("long code, dim, 390" in (t.locator("#v-title").text_content() or ""), "Next moves to the next frame")
                    t.locator("#v-prev").click()
                    page.keyboard.press("Escape")
                    need(not t.locator("#viewer").is_visible(), "Escape closes the viewer")
                    need(t.evaluate("k => document.activeElement && document.activeElement.getAttribute('data-key') === k", key), "focus returns to the frame that was opened")
                    t.locator("#show-problems").click()
                    # 6 reached frames in the dim theme, 1 more overflowing in paper at 390, 4 not reached
                    need(t.locator(".frame").count() == 11, "problems only shows 11 frames, found %d" % t.locator(".frame").count())
                    t.locator("#show-problems").click()
                    t.locator("#columns-toggle").click()
                    t.locator('[data-width-chip="1280"]').click()
                    need(t.locator(".frame").count() == 8, "hiding 1280 leaves 8 frames, found %d" % t.locator(".frame").count())
                    t.locator('[data-width-chip="390"]').click()
                    need(t.locator("#blank-reset").count() == 1, "with every width off the page says nothing matches and offers a way back")
                    t.locator("#blank-reset").click()
                    need(t.locator(".frame").count() == 16, "the way back shows all 16 again")
                    t.locator("#display-toggle").click()
                    t.locator('[data-theme-choice="night"]').click()
                    need(t.locator("html").get_attribute("data-theme") == "night", "the sheet theme changes")
                    t.locator('[data-frames-choice="large"]').click()
                    wide = t.locator('.thumb[data-key="%s"]' % key).evaluate("e => e.getBoundingClientRect().width")
                    need(abs(wide - 195) < 2, "large frames are half size (195 px for a 390 capture), found %s" % wide)
                    note = t.locator("#display-note").text_content() or ""
                    need(("Saved in this browser" in note) if mode == "tab" else ("Not saved" in note), "the storage note is honest in a %s: %r" % (mode, note))
                    t.locator("#display-reset").click()
                    need(t.locator("html").get_attribute("data-theme") == "paper" and t.locator("html").get_attribute("data-frames") == "medium", "reset restores the defaults")
                except Exception as e:  # noqa: BLE001
                    why.append("stopped: " + str(e).split("\n")[0][:100])
                need(not errors, "no uncaught errors: %s" % errors[:2])
                record("sheet-in-tab-and-frame (%s)" % mode, not why, "; ".join(why))
                page.close()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            ok = False
            if code_h == 0:
                page.goto((root / "ghex" / "gallery.html").resolve().as_uri())
                page.wait_for_timeout(500)
                ok = page.evaluate("() => { const i = [...document.querySelectorAll('.thumb img')]; return i.length === 1 && i[0].naturalWidth === 1280; }")
                ok = ok and '"enc":"hex"' in (root / "ghex" / "gallery.html").read_text(encoding="utf-8")
            record("hex-encoding", ok, "exit %d" % code_h)
            ok, got = False, None
            if code_s == 0:
                page.goto((root / "ghalf" / "gallery.html").resolve().as_uri())
                page.wait_for_timeout(500)
                got = page.evaluate("() => [...document.querySelectorAll('.thumb img')].map(i => i.naturalWidth)")
                text = (root / "ghalf" / "gallery.html").read_text(encoding="utf-8")
                png = sorted((root / "ghalf" / "frames").glob("*.png"))
                full = png[0].read_bytes()[16:20] if png else b""
                ok = got == [640] and '"scale":0.5' in text and int.from_bytes(full, "big") == 1280
            record("image-scale", ok, "exit %d, embedded widths %s" % (code_s, got))
            code_j, out_j, _ = run(root / "states.json", "--out", root / "g1", "--json")
            sheets = json.loads(out_j)["output"]["sheets"] if code_j == 0 else []
            count = 0
            if "02-populated--390.png" in sheets:
                import base64
                b64 = base64.b64encode((root / "g1" / "sheets" / "02-populated--390.png").read_bytes()).decode("ascii")
                page.goto("about:blank")
                count = page.evaluate("""async (b64) => { const i = new Image(); i.src = 'data:image/png;base64,' + b64; await i.decode();
                    const c = document.createElement('canvas'); c.width = i.naturalWidth; c.height = i.naturalHeight; const g = c.getContext('2d'); g.drawImage(i, 0, 0);
                    const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0;
                    for (let k = 0; k < d.length; k += 4) if (Math.abs(d[k] - 0x26) < 6 && Math.abs(d[k + 1] - 0x22) < 6 && Math.abs(d[k + 2] - 0x30) < 6) n++;
                    return n; }""", b64)
            # 4 states by 2 widths; the dim capture is 195 by 422 on the sheet, mostly its background colour
            record("sheets-hold-the-captures", len(sheets) == 8 and count > 40000, "%d sheet picture(s); %d pixel(s) of the dim page background" % (len(sheets), count))
            # the labelled empty frame, as rendered
            page.goto(gallery.as_uri())
            page.wait_for_timeout(400)
            box = page.locator(".thumb.none").first.bounding_box() if page.locator(".thumb.none").count() else None
            record("unreached-is-labelled (sheet)", bool(box) and box["width"] > 100 and box["height"] > 100, "box %s" % box)
            browser.close()
    except SystemExit:
        pass
    finally:
        if holder:
            holder.cleanup()
    failed = [r for r in results if not r["ok"]]
    if "--json" in flags:
        print(json.dumps({"script": str(script), "tests": results, "failed": len(failed)}, indent=1, ensure_ascii=True))
    else:
        print("RESULT: %s. %d of %d test(s) passed." % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
