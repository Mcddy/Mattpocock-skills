#!/usr/bin/env python3
"""Exercise the state contract of a single-file tool in a browser tab and in a sandboxed frame.

Usage:
  python test_demo.py [PAGE.html] [--change STEP]... [--proof SELECTOR=TEXT] [--panel STEP]...
                      [--width 390] [--height 844] [--only tab|frame] [--planted] [--json]

With no PAGE it tests the starter page (assets/pocket-demo.html beside this scripts folder) with
its own change and proof. For another page built with pocket-state.js and the pocket-ui.js panel,
say how to make one change and how to see it:
  --change "fill:#a-title=Middlemarch" --change "click:#add-go" --proof "#books=Middlemarch"
STEP is click:SELECTOR, fill:SELECTOR=VALUE, press:SELECTOR=KEY or select:SELECTOR=VALUE.
The proof is an element whose text contains TEXT once the change has been made, and not before.
If the export and import panel sits in its own view, give the step that brings it into view
with --panel, for example --panel "click:#keep-tab". It is run before the panel is used.

What it does. Each test opens the page fresh, in a plain tab and inside
<iframe sandbox="allow-scripts">, where storage, downloads and dialogs are refused:
  loads_cleanly                      no script error, dialog, form, outside request or sideways overflow,
                                     at the given width and again with text 25 percent larger
  says_where_the_data_lives          "Saved in this browser" in the tab; "Not saved: ..." in the frame
  a_change_shows_and_is_saved        the change appears; the tab reports a save, the frame does not
  export_offers_text_and_download    the read-only box holds the envelope; a download link is set
  reload_keeps_or_honestly_loses     the tab still has the change after a reload; the frame does not
                                     and still says so
  import_restores_into_a_fresh_page  pasted text, and a chosen file, reproduce the exported data
  bad_imports_change_nothing         empty, malformed, not an envelope, wrong app, newer schema,
                                     schema as text and wrong shape are each refused with the data
                                     unchanged; the valid neighbour (the page's own export) is accepted
  other_content_is_asked_about       a file for other content is named and asked about in the page;
                                     Cancel changes nothing; Import it anyway loads it
  start_again_is_confirmed           reset asks in the page, Keep everything keeps, removal can be undone
  storage_that_throws_is_survived    (tab) every storage call throws: the page works and says so
  storage_filling_up_is_reported     (tab) a refused write changes the sentence; the last save survives
  second_tab_is_noticed              (tab) a save from another tab stops saving here until a choice is made

--planted writes deliberately broken copies of the page to a temporary folder and checks that
the named test fails for each: a note that always claims the data is saved, an export box left
empty, a refused import that still applies, a panel that overflows a narrow window, and a
storage error that is not handled.

What it enforces: every test above (exit 1 on any failure). What it cannot tell: whether the
tool is any good, whether it works in a real host's preview (this frame is a stand-in), or
anything about screen readers. Look at the page as well.

Needs the Python "playwright" package and a Chromium it can launch.
Each check emits one stderr RECEIPT with completed, partial, not-applicable, failed or runner-error
and semantic scope. Successful stdout/JSON fields are retained. Legacy exits: 0 completed;
1 an actual assertion failed (or a planted failure was missed); 2 invalid input/unreadable page;
3 runner-error (including NOT RUN/missing browser) or partial missing coverage; 5 not-applicable
only for a genuinely empty applicable plan. Status disambiguates exits 2/3. Known failures stay
failed if a later runner error occurs; execution_status and runner_errors retain that error.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

FLAGS = {"--planted", "--json"}
VALUES = {"--change", "--proof", "--panel", "--width", "--height", "--only"}
DEFAULT_CHANGE = ["fill:#new-item=Post the parcel", "click:#add-go"]
DEFAULT_PROOF = "#items=Post the parcel"
SAVED = "Saved in this browser"
NOT_SAVED = "Not saved: this page cannot store data here. Export to keep your work"
VERSION = "1.1.0"
CONTRACT = {}

THROWING_STORAGE = """
(() => {
  const deny = () => { throw new DOMException('The operation is insecure.', 'SecurityError'); };
  Storage.prototype.getItem = deny; Storage.prototype.setItem = deny; Storage.prototype.removeItem = deny;
})();
"""
FILLING_STORAGE = """
(() => {
  const real = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (window.__storageFull) throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
    return real.call(this, k, v);
  };
})();
"""

# Names up to three visible elements that reach past the side of the window. Elements inside a
# box that scrolls or clips on purpose are skipped.
FIT_JS = """
() => {
  const w = document.documentElement.clientWidth, bad = [];
  for (const e of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility !== 'visible') continue;
    const r = e.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) continue;
    if (r.right <= w + 1 && r.left >= -1) continue;
    let clipped = false;
    for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
      if (getComputedStyle(a).overflowX !== 'visible') { clipped = true; break; }
    }
    if (!clipped) bad.push((e.id ? '#' + e.id : e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/)[0] : '')) + ' (to ' + Math.round(r.right) + 'px of ' + w + ')');
    if (bad.length >= 3) break;
  }
  return bad;
}
"""

PLANTED = [
    {"id": "note-lies", "what": "the page always claims the data is saved",
     "caught_by": [("frame", "says_where_the_data_lives")],
     "edits": [("memory: 'Not saved: this page cannot store data here. Export to keep your work',", "memory: 'Saved in this browser',")]},
    {"id": "empty-export", "what": "the export text box is left empty",
     "caught_by": [("tab", "export_offers_text_and_download"), ("frame", "export_offers_text_and_download")],
     "edits": [("      exportArea.value = ex.text;\n", "      exportArea.value = '';\n")]},
    {"id": "import-applies", "what": "a refused import still writes part of the file into the data",
     "caught_by": [("tab", "bad_imports_change_nothing"), ("frame", "bad_imports_change_nothing")],
     "edits": [("      problems = problemsOf(cfg.validate, data);\n      if (problems.length) {\n        if (steps.length) {",
                "      (function () { var k0 = Object.keys(Object(data))[0], half = JSON.parse(stateText); if (k0 !== undefined) { half[k0] = data[k0]; state = half; stateText = JSON.stringify(half); } })();\n"
                "      problems = problemsOf(cfg.validate, data);\n      if (problems.length) {\n        if (steps.length) {")]},
    {"id": "panel-overflows", "what": "the panel's columns take the width of their longest sentence, so text runs off a narrow window",
     "caught_by": [("tab", "loads_cleanly"), ("frame", "loads_cleanly")],
     "edits": [(".pk-block{display:grid;grid-template-columns:minmax(0,1fr);", ".pk-block{display:grid;"),
               (".pk-panel{display:grid;grid-template-columns:minmax(0,1fr);", ".pk-panel{display:grid;")]},
    {"id": "storage-unhandled", "what": "a storage error during a save is not handled",
     "caught_by": [("tab", "storage_filling_up_is_reported")],
     "edits": [("        try { ls.setItem(key, text); return {ok: true}; } catch (e) { return {ok: false, error: e}; }", "        ls.setItem(key, text); return {ok: true};")]},
]


class Failed(Exception):
    pass


class RunnerError(Exception):
    pass


def planned_tests(cfg):
    both, tab_only = build_tests(cfg)
    return [{"mode": mode, "name": fn.__name__}
            for mode in cfg["modes"] for fn in both + (tab_only if mode == "tab" else [])]


def suite_coverage(cfg, results):
    expected = planned_tests(cfg)
    wanted = {(r["mode"], r["name"]) for r in expected}
    seen, duplicate = set(), []
    for row in results:
        key = (row["mode"], row["name"])
        if key in seen:
            duplicate.append({"mode": key[0], "name": key[1]})
        seen.add(key)
    _, tab_only = build_tests(cfg)
    return {"requested_modes": cfg["modes"], "expected": expected, "results": results,
            "not_reached": [r for r in expected if (r["mode"], r["name"]) not in seen],
            "unexpected": [r for r in results if (r["mode"], r["name"]) not in wanted],
            "duplicates": duplicate,
            "not_applicable": ([{"mode": "frame", "name": fn.__name__,
                                 "status": "not-applicable", "reason": "This storage test applies only to a tab."}
                                for fn in tab_only] if "frame" in cfg["modes"] else []),
            "excluded_modes": [m for m in ("tab", "frame") if m not in cfg["modes"]]}


def suite_outcome(coverage):
    rows = coverage["results"]
    if any(r.get("status", "completed" if r["ok"] else "failed") == "failed" for r in rows):
        return "failed", 1
    if any(r.get("status") == "runner-error" for r in rows):
        return "runner-error", 3
    if coverage["not_reached"] or coverage["unexpected"] or coverage["duplicates"]:
        return "partial", 3
    if not coverage["expected"]:
        return "not-applicable", 5
    return "completed", 0


def known_failure():
    if CONTRACT.get("kind") == "planted":
        return any(p["status"] == "failed" for p in CONTRACT.get("planted_results", []))
    return any(r.get("status", "completed" if r["ok"] else "failed") == "failed"
               for r in CONTRACT.get("coverage", {}).get("results", []))


def run(argv):
    CONTRACT.clear()
    CONTRACT.update({"tool": "test_demo", "version": VERSION,
                     "reason": "The requested browser-contract check could not complete.",
                     "coverage": {"phase": "input", "results": []}})
    try:
        code = main(argv)
    except Exception as error:  # tool failures are never product assertions
        code = 1 if known_failure() else 3
        CONTRACT.update({"status": "failed" if known_failure() else "runner-error",
                         "execution_status": "runner-error", "error": str(error)[:240],
                         "error_type": type(error).__name__,
                         "runner_errors": [{"type": type(error).__name__, "detail": str(error)[:240]}]})
    if code in (2, 3) and known_failure():
        CONTRACT.update({"status": "failed", "execution_status": "runner-error", "execution_exit": code})
        code = 1
    CONTRACT.setdefault("status", {0: "completed", 1: "failed", 2: "runner-error", 3: "runner-error", 5: "not-applicable"}.get(code, "runner-error"))
    CONTRACT["exit"] = code
    print("RECEIPT " + json.dumps(CONTRACT, ensure_ascii=True), file=sys.stderr)
    return code


def need(cond, message):
    if not cond:
        raise Failed(message)


def split_step(arg):
    """Split SELECTOR=VALUE at the first = outside [brackets] and quotes."""
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
            return arg[:i].strip(), arg[i + 1:]
    return None, None


def parse_step(text):
    if ":" not in text:
        return None, "step %r has no kind (expected kind:argument)" % text
    kind, arg = text.split(":", 1)
    kind = kind.strip().lower()
    if kind == "click":
        if not arg.strip():
            return None, "click needs a selector"
        return {"kind": kind, "sel": arg.strip()}, None
    if kind in ("fill", "press", "select"):
        sel, val = split_step(arg)
        if not sel:
            return None, "%s needs SELECTOR=VALUE, got %r" % (kind, arg)
        return {"kind": kind, "sel": sel, "value": val}, None
    return None, "step kind %r is not one of click, fill, press, select" % kind


class Session:
    """One fresh load of the page, in a tab or inside a sandboxed frame."""

    def __init__(self, browser, uri, wrapper_uri, mode, width, height, context=None, init_script=None, panel_steps=None):
        self.mode, self.uri = mode, uri
        self.panel_steps = panel_steps or []
        self.own_context = context is None
        self.context = context or browser.new_context(viewport={"width": width, "height": height})
        if init_script:
            self.context.add_init_script(init_script)
        self.page = self.context.new_page()
        self.errors, self.dialogs, self.outside = [], [], []
        self.page.on("pageerror", lambda e: self.errors.append("script error: " + str(e).split("\n")[0][:160]))
        # A refused clipboard write is logged by the browser itself. It is the refusal the page's
        # fallback exists for, so it is not counted as a page error.
        self.page.on("console", lambda m: self.errors.append("console error: " + m.text[:160])
                     if m.type == "error" and not m.text.startswith("Permissions policy violation") else None)
        self.page.on("dialog", self._dialog)
        self.page.on("request", lambda r: self.outside.append(r.url[:120]) if not r.url.startswith(("file:", "blob:", "data:", "about:")) else None)
        self.page.goto(uri if mode == "tab" else wrapper_uri, timeout=15000)
        self.wait(lambda: self.count("#pk-note") == 1 and self.text("#pk-note").strip() != "", "the page never showed where its data lives (#pk-note)")
        self.wait(lambda: "Opening saved data" not in self.text("#pk-note"), "the page never finished opening its saved data")

    def _dialog(self, d):
        self.dialogs.append(d.type)
        d.dismiss()

    @property
    def t(self):
        if self.mode == "tab":
            return self.page
        frames = [f for f in self.page.frames if f != self.page.main_frame]
        need(frames, "the frame did not load")
        return frames[0]

    def wait(self, fn, message, timeout=4.0):
        end = time.time() + timeout
        last = None
        while True:
            try:
                if fn():
                    return
                last = None
            except Failed:
                raise
            except Exception as e:  # noqa: BLE001
                last = e
            if time.time() > end:
                if last is not None:
                    raise RunnerError(message + " (observation failed: " + str(last).split("\n")[0][:100] + ")") from last
                raise Failed(message)
            self.page.wait_for_timeout(60)

    def count(self, sel):
        return self.t.locator(sel).count()

    def text(self, sel):
        loc = self.t.locator(sel)
        return (loc.first.text_content(timeout=3000) or "") if loc.count() else ""

    def value(self, sel):
        return self.t.locator(sel).first.input_value(timeout=3000)

    def shown(self, sel):
        loc = self.t.locator(sel)
        return loc.count() > 0 and loc.first.is_visible()

    def click(self, sel):
        self.t.locator(sel).first.click(timeout=4000)

    def fill(self, sel, value):
        self.t.locator(sel).first.fill(value, timeout=4000)

    def focused(self):
        return self.t.evaluate("() => { const a = document.activeElement; return a && a.id ? a.id : (a ? a.tagName : ''); }")

    def do(self, steps):
        for s in steps:
            loc = self.t.locator(s["sel"]).first
            if s["kind"] == "click":
                loc.click(timeout=4000)
            elif s["kind"] == "fill":
                loc.fill(s["value"], timeout=4000)
            elif s["kind"] == "press":
                loc.press(s["value"], timeout=4000)
            elif s["kind"] == "select":
                loc.select_option(s["value"], timeout=4000)

    def has_proof(self, proof):
        sel, text = proof
        return text in self.text(sel)

    def panel(self):
        """Bring the export and import panel into view, when the page keeps it in a view of its own."""
        if self.panel_steps and not self.shown("#pk-export"):
            self.do(self.panel_steps)

    def export(self):
        self.panel()
        self.click("#pk-export")
        self.wait(lambda: self.shown("#pk-export-out"), "the export box did not open")
        text = self.value("#pk-export-text")
        try:
            return text, json.loads(text)
        except ValueError:
            raise Failed("the export text box does not hold JSON (it holds %r)" % text[:60])

    def data(self):
        return json.dumps(self.export()[1].get("data"), sort_keys=True)

    def import_text(self, text):
        self.panel()
        self.fill("#pk-import-text", text)
        self.click("#pk-import")

    def reload(self):
        self.page.reload(timeout=15000)
        self.wait(lambda: self.count("#pk-note") == 1 and self.text("#pk-note").strip() != "", "the page did not come back after a reload")

    def close(self):
        if self.own_context:
            self.context.close()
        else:
            self.page.close()


def build_tests(cfg):
    change, proof = cfg["change"], cfg["proof"]

    def changed(s):
        need(not s.has_proof(proof), "the proof %r is already on the page before any change; pick a proof that the change creates" % proof[1])
        s.do(change)
        s.wait(lambda: s.has_proof(proof), "the change did not appear: %s never contained %r" % proof)

    def saved(s):
        s.wait(lambda: "Last saved" in s.text("#pk-note"), "the page never reported a save (note says %r)" % s.text("#pk-note"))

    def loads_cleanly(new):
        s = new()
        s.page.wait_for_timeout(300)
        need(not s.errors, "; ".join(s.errors[:3]))
        need(not s.dialogs, "the page opened a %s dialog" % (s.dialogs or [""])[0])
        need(not s.outside, "the page made an outside request: %s" % (s.outside or [""])[0])
        need(s.t.evaluate("() => document.forms.length") == 0, "the page has a form element")
        over = s.t.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        need(over <= 0, "the page is %d CSS pixels wider than a %d pixel window" % (over, cfg["width"]))
        out = s.t.evaluate(FIT_JS)
        need(not out, "at this width %s runs off the side of the window" % ", ".join(out))
        # The same again with text a quarter larger and the panel's hidden parts open, which is
        # where long sentences and wide boxes first break a narrow layout.
        s.panel()
        s.click("#pk-export")
        s.click("#pk-reset")
        s.t.evaluate("() => { document.documentElement.style.fontSize = '125%'; }")
        s.page.wait_for_timeout(150)
        out = s.t.evaluate(FIT_JS)
        need(not out, "with text 25 percent larger %s runs off the side of the window" % ", ".join(out))

    def says_where_the_data_lives(new):
        s = new()
        note = s.text("#pk-note")
        if s.mode == "tab":
            need(SAVED in note, "in a tab the note should say %r and says %r" % (SAVED, note))
        else:
            need(NOT_SAVED in note, "in the frame the note should say %r and says %r" % (NOT_SAVED, note))

    def a_change_shows_and_is_saved(new):
        s = new()
        changed(s)
        if s.mode == "tab":
            saved(s)
        else:
            s.page.wait_for_timeout(700)
            need("Last saved" not in s.text("#pk-note") and NOT_SAVED in s.text("#pk-note"), "the frame cannot store data, and the note says %r" % s.text("#pk-note"))
        need(not s.errors, "; ".join(s.errors[:3]))

    def export_offers_text_and_download(new):
        s = new()
        changed(s)
        text, env = s.export()
        need(list(env.keys()) == ["app", "schema", "content_id", "saved_at", "data"], "the envelope fields are %s" % list(env.keys()))
        need(isinstance(env["app"], str) and env["app"], "the envelope has no app id")
        need(isinstance(env["schema"], int) and not isinstance(env["schema"], bool) and env["schema"] >= 1, "the schema is %r" % env["schema"])
        need(isinstance(env["content_id"], str) and env["content_id"], "the envelope has no content id")
        need(s.t.locator("#pk-export-text").first.get_attribute("readonly") is not None, "the export box can be typed into")
        href = s.t.locator("#pk-download").first.get_attribute("href") or ""
        name = s.t.locator("#pk-download").first.get_attribute("download") or ""
        need(href.startswith(("blob:", "data:")), "the download link has no content (href %r)" % href[:30])
        need(name.endswith(".json"), "the download has no .json file name (%r)" % name)
        s.click("#pk-copy")
        s.wait(lambda: ("Copied" in s.text("#pk-export-msg")) or ("Copying was refused" in s.text("#pk-export-msg")), "pressing Copy gave no answer (message %r)" % s.text("#pk-export-msg"))
        need(not s.errors, "; ".join(s.errors[:3]))

    def reload_keeps_or_honestly_loses(new):
        s = new()
        changed(s)
        if s.mode == "tab":
            saved(s)
            s.reload()
            s.wait(lambda: s.has_proof(proof), "the change was lost by a reload although the page said it was saved")
        else:
            s.reload()
            s.page.wait_for_timeout(300)
            need(not s.has_proof(proof), "the frame kept data across a reload, which this test's frame cannot do; check the test")
            need(NOT_SAVED in s.text("#pk-note"), "after a reload in the frame the note says %r" % s.text("#pk-note"))

    def import_restores_into_a_fresh_page(new):
        a = new()
        changed(a)
        text, env = a.export()
        want = json.dumps(env["data"], sort_keys=True)
        b = new()
        need(not b.has_proof(proof), "a fresh page already shows the change")
        b.import_text(text)
        b.wait(lambda: b.text("#pk-import-msg").startswith("Imported"), "the paste was not imported: %r" % b.text("#pk-import-msg"))
        need(b.has_proof(proof), "the import said it worked and the change is not on the page")
        need(b.data() == want, "the imported data is not identical to the exported data")
        c = new()
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "saved-copy.json"
            f.write_text(text, encoding="utf-8")
            c.panel()
            c.t.locator("#pk-import-file").first.set_input_files(str(f))
            c.wait(lambda: "Press Import" in c.text("#pk-import-msg"), "choosing a file did nothing: %r" % c.text("#pk-import-msg"))
            c.click("#pk-import")
            c.wait(lambda: c.text("#pk-import-msg").startswith("Imported"), "the chosen file was not imported: %r" % c.text("#pk-import-msg"))
        need(c.data() == want, "the data imported from a file is not identical to the exported data")

    def bad_imports_change_nothing(new):
        s = new()
        changed(s)
        text, env = s.export()
        base = json.dumps(env["data"], sort_keys=True)

        def variant(**over):
            e = dict(env)
            e.update(over)
            return json.dumps(e)
        bad = [
            ("an empty box", ""),
            ("malformed JSON", '{"app": "' + env["app"] + '", '),
            ("JSON that is not an envelope", "[1, 2, 3]"),
            ("a CSV file", "claim_id,question_id,statement\nC1,Q1,Not JSON at all"),
            ("another app's file", variant(app=env["app"] + "-other")),
            ("a newer schema", variant(schema=env["schema"] + 1)),
            ("a schema written as text", variant(schema=str(env["schema"]))),
            ("data of the wrong shape", variant(data={"__not_this_shape__": True})),
        ]
        for label, payload in bad:
            s.import_text(payload)
            s.wait(lambda: s.text("#pk-import-msg").startswith("Not imported."), "%s was not refused (message %r)" % (label, s.text("#pk-import-msg")))
            need("Nothing was changed." in s.text("#pk-import-msg"), "refusing %s did not say that nothing was changed" % label)
            need(s.has_proof(proof), "after refusing %s the earlier change is gone" % label)
            need(s.data() == base, "after refusing %s the data is different" % label)
        s.import_text(text)
        s.wait(lambda: s.text("#pk-import-msg").startswith("Imported"), "the page refused its own export: %r" % s.text("#pk-import-msg"))
        need(not s.errors, "; ".join(s.errors[:3]))

    def other_content_is_asked_about(new):
        a = new()
        changed(a)
        text, env = a.export()
        other = dict(env)
        other["content_id"] = env["content_id"] + "-other"
        other["data"] = json.loads(json.dumps(env["data"]))
        b = new()
        blank = b.data()
        b.import_text(json.dumps(other))
        b.wait(lambda: b.shown("#pk-mismatch"), "a file for other content was not asked about (message %r)" % b.text("#pk-import-msg"))
        said = b.text("#pk-mismatch")
        need(env["content_id"] in said and other["content_id"] in said, "the question does not name both contents: %r" % said[:160])
        need(b.focused() == "pk-mismatch-no", "focus should be on Cancel and is on %r" % b.focused())
        b.click("#pk-mismatch-no")
        b.wait(lambda: b.text("#pk-import-msg").startswith("Not imported."), "Cancel did not refuse the import")
        need(not b.has_proof(proof) and b.data() == blank, "Cancel changed the data")
        b.import_text(json.dumps(other))
        b.wait(lambda: b.shown("#pk-mismatch"), "the question did not come back on a second try")
        b.click("#pk-mismatch-yes")
        b.wait(lambda: b.text("#pk-import-msg").startswith("Imported"), "Import it anyway did not import: %r" % b.text("#pk-import-msg"))
        need(b.has_proof(proof), "Import it anyway said it worked and the change is not on the page")

    def start_again_is_confirmed(new):
        s = new()
        changed(s)
        s.panel()
        s.click("#pk-reset")
        s.wait(lambda: s.shown("#pk-reset-confirm"), "Remove everything did not ask first")
        need(s.has_proof(proof), "the data was removed before the question was answered")
        need(len(s.text("#pk-reset-confirm").strip()) > 40, "the question does not say what will be lost")
        need(s.focused() == "pk-reset-no", "focus should be on Keep everything and is on %r" % s.focused())
        s.click("#pk-reset-no")
        need(not s.shown("#pk-reset-confirm") and s.has_proof(proof), "Keep everything did not keep everything")
        s.click("#pk-reset")
        s.click("#pk-reset-export")
        s.wait(lambda: s.shown("#pk-export-out") and s.value("#pk-export-text").startswith("{"), "Export a copy first did not show the export")
        s.click("#pk-reset-yes")
        s.wait(lambda: not s.has_proof(proof), "Remove everything did not remove the change")
        s.click("#pk-undo")
        s.wait(lambda: s.has_proof(proof), "Undo did not bring the data back")
        need(not s.dialogs, "the page used a %s dialog" % (s.dialogs or [""])[0])

    def storage_that_throws_is_survived(new):
        s = new(init_script=THROWING_STORAGE)
        need(NOT_SAVED in s.text("#pk-note"), "with storage throwing the note says %r" % s.text("#pk-note"))
        changed(s)
        s.export()
        need(not s.errors, "; ".join(s.errors[:3]))

    def storage_filling_up_is_reported(new):
        s = new(init_script=FILLING_STORAGE)
        changed(s)
        saved(s)
        s.page.evaluate("() => { window.__storageFull = true; }")
        s.do(change)
        s.wait(lambda: "storage is full" in s.text("#pk-note") and "Export to keep your work" in s.text("#pk-note"),
               "a refused write did not change the note (it says %r)" % s.text("#pk-note"))
        need(not s.errors, "; ".join(s.errors[:3]))
        s.export()
        s.reload()
        s.wait(lambda: s.has_proof(proof), "the last good save did not survive the full storage")

    def second_tab_is_noticed(new):
        a = new()
        b = new(context=a.context)
        changed(a)
        saved(a)
        b.panel()
        b.wait(lambda: b.shown("#pk-conflict"), "the second tab was not told that the first one saved")
        need(b.text("#pk-note").startswith("Not saving"), "the second tab's note says %r" % b.text("#pk-note"))
        need(not b.has_proof(proof), "the second tab changed its data without being asked")
        b.click("#pk-take-theirs")
        b.wait(lambda: b.has_proof(proof), "loading the other copy did not show its change")
        b.wait(lambda: not b.shown("#pk-conflict") and SAVED in b.text("#pk-note"), "the second tab is still not saving after the choice")

    both = [loads_cleanly, says_where_the_data_lives, a_change_shows_and_is_saved, export_offers_text_and_download,
            reload_keeps_or_honestly_loses, import_restores_into_a_fresh_page, bad_imports_change_nothing,
            other_content_is_asked_about, start_again_is_confirmed]
    tab_only = [storage_that_throws_is_survived, storage_filling_up_is_reported, second_tab_is_noticed]
    return both, tab_only


def run_suite(pw_browser, page_path, cfg):
    """Run every test against one page file. Returns a list of {mode, name, ok, detail}."""
    results = []
    CONTRACT["coverage"] = suite_coverage(cfg, results)
    both, tab_only = build_tests(cfg)
    uri = Path(page_path).resolve().as_uri()
    with tempfile.TemporaryDirectory() as td:
        wrapper = Path(td) / "frame.html"
        wrapper.write_text('<!doctype html><html lang="en"><title>frame</title><body style="margin:0">'
                           '<iframe id="f" sandbox="allow-scripts" src="%s" style="border:0;width:100vw;height:100vh"></iframe></body></html>' % uri, encoding="utf-8")
        for mode in cfg["modes"]:
            for fn in both + (tab_only if mode == "tab" else []):
                opened = []

                def new(context=None, init_script=None, mode=mode, opened=opened):
                    s = Session(pw_browser, uri, wrapper.as_uri(), mode, cfg["width"], cfg["height"], context=context, init_script=init_script, panel_steps=cfg.get("panel"))
                    opened.append(s)
                    return s
                ok, detail, status, close_errors = True, "", "completed", []
                try:
                    fn(new)
                except Failed as e:
                    ok, detail, status = False, str(e), "failed"
                except Exception as e:  # noqa: BLE001
                    ok, detail, status = False, "the test could not finish: " + str(e).split("\n")[0][:160], "runner-error"
                for s in reversed(opened):
                    try:
                        s.close()
                    except Exception as e:  # noqa: BLE001
                        close_errors.append(str(e).split("\n")[0][:100])
                        ok = False
                        if status != "failed":
                            status = "runner-error"
                        detail += ("; " if detail else "") + "session close failed: " + str(e).split("\n")[0][:100]
                results.append({"mode": mode, "name": fn.__name__, "ok": ok, "detail": detail, "status": status})
                if close_errors:
                    results[-1]["runner_errors"] = close_errors
                CONTRACT["coverage"] = suite_coverage(cfg, results)
    return results


def main(argv):
    flags, opts, changes, panel_raw, args, it = set(), {}, [], [], [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("test_demo: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--change":
                changes.append(v)
            elif a == "--panel":
                panel_raw.append(v)
            else:
                opts[a] = v
        elif a.startswith("--"):
            print("test_demo: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) > 1:
        print(__doc__)
        return 2
    default_page = Path(__file__).resolve().parent.parent / "assets" / "pocket-demo.html"
    page_path = Path(args[0]) if args else default_page
    if not page_path.is_file():
        print("test_demo: cannot read " + str(page_path), file=sys.stderr)
        return 2
    try:
        source = page_path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeError) as e:
        CONTRACT["reason"] = "The requested page could not be read as UTF-8."
        print("test_demo: cannot read %s as UTF-8 (%s)" % (page_path, str(e)[:120]), file=sys.stderr)
        return 2
    if args and (not changes or "--proof" not in opts):
        print("test_demo: for a page of your own, give at least one --change and a --proof", file=sys.stderr)
        return 2
    steps = []
    for c in (changes or DEFAULT_CHANGE):
        st, err = parse_step(c)
        if err:
            print("test_demo: " + err, file=sys.stderr)
            return 2
        steps.append(st)
    panel_steps = []
    for c in panel_raw:
        st, err = parse_step(c)
        if err:
            print("test_demo: " + err, file=sys.stderr)
            return 2
        panel_steps.append(st)
    psel, ptext = split_step(opts.get("--proof", DEFAULT_PROOF))
    if not psel or not ptext:
        print("test_demo: --proof needs SELECTOR=TEXT", file=sys.stderr)
        return 2
    try:
        width, height = int(opts.get("--width", "390")), int(opts.get("--height", "844"))
        if width < 200 or height < 200:
            raise ValueError
    except ValueError:
        print("test_demo: --width and --height need whole numbers of 200 or more", file=sys.stderr)
        return 2
    only = opts.get("--only")
    if only not in (None, "tab", "frame"):
        print("test_demo: --only takes tab or frame", file=sys.stderr)
        return 2
    if "--planted" in flags and only is not None:
        print("test_demo: --planted and --only cannot be combined; planted checks require their declared tab and frame scope", file=sys.stderr)
        return 2
    cfg = {"change": steps, "proof": (psel, ptext), "panel": panel_steps, "width": width, "height": height, "modes": [only] if only else ["tab", "frame"]}
    CONTRACT.update({"page": str(page_path), "width": width, "height": height,
                     "kind": "planted" if "--planted" in flags else "ordinary",
                     "coverage": suite_coverage(cfg, []), "reason": "Requested state-contract checks and their actual coverage."})

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        CONTRACT.update({"status": "runner-error", "reason": "Playwright is unavailable.", "error": str(e)[:120]})
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 3
    out = {"page": str(page_path), "width": width, "height": height}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            CONTRACT.update({"status": "runner-error", "reason": "Chromium could not launch.", "error": str(e).split("\n")[0][:120]})
            print("NOT RUN: Chromium could not be launched (%s)" % str(e).split("\n")[0][:120])
            return 3
        if "--planted" in flags:
            missed, lines, plants = 0, [], []
            CONTRACT["planted_results"] = plants
            with tempfile.TemporaryDirectory() as td:
                for plant in PLANTED:
                    text = source
                    for old, new_text in plant["edits"]:
                        if text.count(old) != 1:
                            browser.close()
                            print("test_demo: planted failure %s does not match this page's embedded library; it is written for pocket-state.js and pocket-ui.js 1.0.0" % plant["id"], file=sys.stderr)
                            return 2
                        text = text.replace(old, new_text)
                    broken = Path(td) / ("planted-" + plant["id"] + ".html")
                    broken.write_text(text, encoding="utf-8")
                    CONTRACT["active_plant"] = plant["id"]
                    res = run_suite(browser, broken, dict(cfg, modes=["tab", "frame"]))
                    coverage = suite_coverage(cfg, res)
                    failed = {(r["mode"], r["name"]): r["detail"] for r in res
                              if r.get("status", "completed" if r["ok"] else "failed") == "failed"}
                    not_caught = [c for c in plant["caught_by"] if tuple(c) not in failed]
                    if any(r.get("status") == "runner-error" for r in res):
                        plant_status = "runner-error"
                        lines.append("PLANTED %s: RUNNER ERROR; infrastructure failure is not a caught defect." % plant["id"])
                    elif coverage["not_reached"] or coverage["unexpected"] or coverage["duplicates"]:
                        plant_status = "partial"
                        lines.append("PLANTED %s: PARTIAL; requested test coverage is incomplete." % plant["id"])
                    elif not_caught:
                        plant_status = "failed"
                        missed += 1
                        lines.append("PLANTED %s: NOT CAUGHT by %s. %s" % (plant["id"], ", ".join("%s/%s" % c for c in not_caught), plant["what"]))
                    else:
                        plant_status = "completed"
                        lines.append("PLANTED %s: caught. %s" % (plant["id"], plant["what"]))
                        for c in plant["caught_by"]:
                            lines.append("    %s %s FAILED: %s" % (c[0], c[1], failed[tuple(c)][:150]))
                        lines.append("    tests failing against this copy: %d of %d" % (len(failed), len(res)))
                    plants.append({"id": plant["id"], "status": plant_status,
                                   "named_failures_not_caught": not_caught, "coverage": coverage})
                    CONTRACT["coverage"] = {"requested_modes": cfg["modes"], "plants_expected": [p["id"] for p in PLANTED], "plants": plants}
            browser.close()
            status = ("failed" if missed else "runner-error" if any(p["status"] == "runner-error" for p in plants)
                      else "partial" if len(plants) != len(PLANTED) or any(p["status"] == "partial" for p in plants) else "completed")
            CONTRACT["status"] = status
            lines.append("RESULT: %s" % ("FAIL. %d planted failure(s) were not caught." % missed if missed else
                                         "PASS. %d of %d planted failures were caught by their named tests." % (len(PLANTED), len(PLANTED)) if status == "completed" else
                                         "NOT COMPLETE. " + status))
            print("\n".join(lines).encode("ascii", "replace").decode("ascii"))
            return {"completed": 0, "failed": 1, "partial": 3, "runner-error": 3}[status]
        results = run_suite(browser, page_path, cfg)
        CONTRACT["coverage"] = suite_coverage(cfg, results)
        browser.close()
    coverage = suite_coverage(cfg, results)
    status, code = suite_outcome(coverage)
    CONTRACT.update({"status": status, "coverage": coverage})
    failed = [r for r in results if not r["ok"]]
    out["results"] = [{k: r[k] for k in ("mode", "name", "ok", "detail")} for r in results]
    if "--json" in flags:
        text = json.dumps(out, indent=1, ensure_ascii=True)
    else:
        L = ["test_demo: %s at %d by %d CSS pixels" % (page_path.name, width, height)]
        for r in results:
            L.append("  %-4s %-5s %s%s" % ("PASS" if r["ok"] else "ERROR" if r.get("status") == "runner-error" else "FAIL", r["mode"], r["name"], ("\n         " + r["detail"]) if r["detail"] else ""))
        L.append("RESULT: %s. %d of %d tests passed. The frame is a local stand-in for a chat preview, not the real host."
                 % ("PASS" if status == "completed" else status.upper(), len(results) - len(failed), len(results)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    sys.stdout.write(text + "\n")
    return code


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
