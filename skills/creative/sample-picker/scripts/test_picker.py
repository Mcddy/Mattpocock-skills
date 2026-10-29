#!/usr/bin/env python3
"""Drive a built picker the way a person would, and check what it hands back.

Usage:
  python test_picker.py PICKER.html [PICKER.html ...] [--save-choice DIR] [--json]
  python test_picker.py --self-test [--engine PATH/picker.html] [--json]

With picker files (run this on every picker before showing it): each file is driven at 390 and at
1280 pixels wide, in a plain tab and inside <iframe sandbox="allow-scripts">. Named tests per file:
  journey                 shortlist two, compare them (by tabs on the narrow width), open one,
                          change a tweak, choose it, leave a note, open Result. No page errors and
                          no sideways overflow in any view
  export-names-choice     the result names the option that was chosen, the tweak values that were
                          set, the two shortlisted options and the note
  block-round-trip        parse_choice.py turns the short text into the same object as the page's
                          JSON form, and that object passes its checks against the picker's data
  clipboard               where copying is allowed the clipboard holds the text; where it is refused
                          the page says so and leaves the text box focused with its text selected
  reload                  where storage works, a reload brings back the shortlist, choice, tweak and
                          note; where it does not, the page says the session is not saved
  session-import          the JSON form loads into a fresh page of the same width and reproduces the
                          session, measured facts included; a wrong
                          app, a newer schema, malformed JSON and an empty paste are each refused
                          with the session untouched; another picker's session asks first, and
                          "keep" leaves the session untouched
  reset-and-undo          clearing is confirmed in the page and names what will go; undo restores it
  large-notes             a 5,000 character note on every option survives export and import
  focus-clear-of-bar      at 390 wide, tabbing through the options and the compare view never leaves
                          the focused control under the bar fixed to the bottom of the screen
  theme-contrast          (kind theme) every contrast number the page shows equals a ratio worked
                          out separately in Python from the colours the browser computed, and the
                          lowest equals the lowest that validate_picker.py computes from the tokens
--save-choice DIR writes NAME.choice.txt and NAME.choice.json from the 1280 tab journey.

--self-test checks the engine and the other scripts, using the fixtures beside this file:
  fixtures-build-and-run          the seven fixtures build and pass every per-file test: theme, type,
                                  layout, copy as a notice, component as a button and as a field,
                                  and custom
  planted-wrong-option-is-caught  a copy of the engine is broken on purpose so that changing a tweak
                                  moves the choice to another option; export-names-choice must FAIL
  planted-low-contrast-is-refused a theme whose body text is 3.59 to 1 is refused by
                                  validate_picker.py and build_picker.py, and so is one at 4.48;
                                  at 4.54, the next grey darker, it is accepted
  validator-refusals              one option, nine options, placeholder text, twin notes, a dead
                                  control and more, each beside its nearest valid neighbour
  parse-refusals                  a cut-off block, an unknown line, final with nothing chosen, an
                                  impossible date, a result for another picker; and a block with
                                  curly quotes and quote marks that must still parse
  host-storage                    a host storage object is used when present, and a failing one
                                  falls back without losing the session
  missing-font-is-named           a font that is not installed is reported as not installed
  custom-tweak-redraws            a tweak re-runs a custom renderer

What it cannot tell: whether the options are good, differ enough, or look right. Look at the page.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes: 0 every test passed. 1 a test failed. 2 bad arguments. 3 NOT RUN.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parse_choice as pc  # noqa: E402
import validate_picker as vp  # noqa: E402
import picker_result as pr  # noqa: E402


FLAGS = {"--json", "--self-test"}
VALUES = {"--save-choice", "--engine"}
NOTE = "Like the colour, not the weight. \"Calmer\" would suit; caf" + chr(233) + " menu test\nsecond line"

COLOURS_JS = r"""
() => [...document.querySelectorAll('#main .smp [data-role]')].map(e => {
  const out = {role: e.getAttribute('data-role'), fg: getComputedStyle(e).color, bg: null, shown: null};
  for (let c = e; c && c.nodeType === 1; c = c.parentElement) {
    const b = getComputedStyle(c).backgroundColor;
    const m = b.match(/rgba?\(([^)]+)\)/); const p = m ? m[1].split(/[,\s\/]+/).filter(Boolean).map(Number) : null;
    if (p && (p.length < 4 || p[3] >= 1)) { out.bg = b; break; }
  }
  return out;
})
"""


def rgb_hex(text):
    nums = [float(x) for x in text[text.index("(") + 1:text.index(")")].replace("/", " ").replace(",", " ").split()]
    return "#" + "".join("%02x" % int(round(v)) for v in nums[:3])


def plan_control(c):
    """The value the journey will set, and how. Never the default."""
    if c["type"] == "toggle":
        return (not c["default"]), ("click", None)
    if c["type"] == "choice":
        vals = [o if isinstance(o, str) else o["value"] for o in c["options"]]
        v = [x for x in vals if x != c["default"]][0]
        return v, ("click", v)
    step = c.get("step", 1)
    if c["default"] + 2 * step <= c["max"]:
        return c["default"] + 2 * step, ("press", "ArrowRight")
    return c["default"] - 2 * step, ("press", "ArrowLeft")


class Run:
    def __init__(self, browser, path, width, mode, tmp, grant=True):
        self.path, self.width, self.mode = Path(path).resolve(), width, mode
        self.ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 700 else 900})
        if grant and mode == "tab":
            try:
                self.ctx.grant_permissions(["clipboard-read", "clipboard-write"])
            except Exception:  # noqa: BLE001
                pass
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)[:140]))
        self.page.on("console", lambda m: self.errors.append(m.text[:140]) if m.type == "error" else None)
        if mode == "frame":
            wrapper = Path(tmp) / ("frame-%s-%d.html" % (self.path.stem, width))
            wrapper.write_text('<!doctype html><html lang="en"><title>frame</title><body style="margin:0">'
                               '<iframe id="f" sandbox="allow-scripts" src="%s" style="border:0;width:100vw;height:100vh"></iframe></body></html>' % self.path.as_uri(), encoding="utf-8")
            self.uri = wrapper.as_uri()
        else:
            self.uri = self.path.as_uri()
        self.open()

    def open(self):
        self.page.goto(self.uri)
        self.page.wait_for_timeout(450)
        self.t = self.page if self.mode == "tab" else [f for f in self.page.frames if f != self.page.main_frame][0]

    def reload(self):
        self.page.reload()
        self.page.wait_for_timeout(500)
        self.t = self.page if self.mode == "tab" else [f for f in self.page.frames if f != self.page.main_frame][0]

    def overflow(self):
        return self.t.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")

    def session(self):
        """The session as the page would export it, without the time."""
        self.t.locator("#nav-result").click()
        self.t.locator("#r-mode-json").click()
        d = json.loads(self.t.locator("#r-text").input_value())
        d.pop("saved_at", None)
        return d

    def close(self):
        self.ctx.close()


def journey(run, picker):
    """Returns (facts for the named tests, list of reasons the journey itself failed)."""
    t, why, out = run.t, [], {}
    opts = picker["options"]
    a, b = (opts[-2]["id"], opts[-1]["id"]) if len(opts) > 2 else (opts[0]["id"], opts[1]["id"])
    out["a"], out["b"] = a, b

    def need(cond, text):
        if not cond:
            why.append(text)
    try:
        need(t.locator("#main .card").count() == len(opts), "one card per option: found %d for %d" % (t.locator("#main .card").count(), len(opts)))
        need(run.overflow() <= 1, "options view overflows sideways by %s px" % run.overflow())
        t.locator('[data-shortlist="%s"]' % a).click()
        t.locator('[data-shortlist="%s"]' % b).click()
        need(t.locator('[data-shortlist="%s"]' % b).get_attribute("aria-pressed") == "true", "the shortlist control shows as pressed")
        need("(2)" in (t.locator("#nav-compare").text_content() or ""), "the Compare button counts 2")
        t.locator("#nav-compare").click()
        need(t.locator("[data-cmp-col]").count() == 2, "compare holds both shortlisted options")
        if run.width < 760:
            need(t.locator('[data-cmp-col="%s"]' % a).is_visible() and not t.locator('[data-cmp-col="%s"]' % b).is_visible(), "narrow: one option shows at a time")
            tab = t.locator('[data-cmp-tab="%s"]' % b)
            box = tab.bounding_box()
            need(box is not None and box["height"] >= 44, "narrow: the compare tabs are at least 44 px tall")
            tab.click()
            need(t.locator('[data-cmp-col="%s"]' % b).is_visible() and not t.locator('[data-cmp-col="%s"]' % a).is_visible(), "narrow: the tab switches the option shown")
        else:
            need(t.locator('[data-cmp-col="%s"]' % a).is_visible() and t.locator('[data-cmp-col="%s"]' % b).is_visible(), "wide: both options show side by side")
            xa = t.locator('[data-cmp-col="%s"]' % a).bounding_box()
            xb = t.locator('[data-cmp-col="%s"]' % b).bounding_box()
            need(xa and xb and abs(xa["y"] - xb["y"]) < 2 and xa["x"] != xb["x"], "wide: the two columns sit on one row")
        need(run.overflow() <= 1, "compare view overflows sideways by %s px" % run.overflow())
        t.locator('[data-cmp-col="%s"] [data-open="%s"]' % (b, b)).click()
        need(run.overflow() <= 1, "detail view overflows sideways by %s px" % run.overflow())
        expected = {c["id"]: c["default"] for c in picker.get("controls", [])}
        if picker.get("controls"):
            c = picker["controls"][0]
            value, (how, arg) = plan_control(c)
            expected[c["id"]] = value
            if c["type"] == "choice":
                t.locator('[data-control="%s"][data-value="%s"]' % (c["id"], arg)).click()
            elif c["type"] == "toggle":
                t.locator('[data-control="%s"]' % c["id"]).click()
            else:
                t.locator("#ctl-" + c["id"]).press(arg)
                t.locator("#ctl-" + c["id"]).press(arg)
            attr = "data-ctl-" + c["id"]
            if c["type"] != "range":
                got = t.locator("#main .smp").first.get_attribute(attr)
                need(got == (("on" if value else "off") if c["type"] == "toggle" else str(value)), "the tweak reached the sample (%s is %r)" % (attr, got))
            else:
                got = t.locator("#main .smp").first.evaluate("(e, k) => e.style.getPropertyValue(k)", "--ctl-%s-n" % c["id"])
                need(float(got or "nan") == float(value), "the tweak reached the sample (--ctl-%s-n is %r, wanted %s)" % (c["id"], got, value))
        out["expected_controls"] = expected
        t.locator("#d-choose").click()
        need(t.locator("#d-choose").get_attribute("aria-pressed") == "true", "Choose this shows as chosen")
        t.locator("#d-note").fill(NOTE)
        t.locator("#nav-result").click()
        need(run.overflow() <= 1, "result view overflows sideways by %s px" % run.overflow())
        out["summary"] = t.locator("#r-summary").text_content() or ""
        out["text"] = t.locator("#r-text").input_value()
        t.locator("#r-mode-json").click()
        out["json"] = t.locator("#r-text").input_value()
        t.locator("#r-mode-text").click()
        # the box is drawn again here with a new saved time, so what Copy takes is read at this moment
        out["box_at_copy"] = t.locator("#r-text").input_value()
        t.locator("#r-copy").click()
        run.page.wait_for_timeout(350)
        out["copy_status"] = t.locator("#r-status").text_content() or ""
        out["selection"] = t.evaluate("() => { const b = document.getElementById('r-text'); return [document.activeElement === b, b.selectionStart, b.selectionEnd, b.value.length]; }")
        out["clipboard"] = None
        if run.mode == "tab":
            try:
                out["clipboard"] = run.page.evaluate("() => navigator.clipboard.readText()")
            except Exception:  # noqa: BLE001
                out["clipboard"] = None
        out["storage_words"] = t.locator("#main p.muted").last.text_content() or ""
    except Exception as e:  # noqa: BLE001
        why.append("stopped: " + str(e).split("\n")[0][:120])
    need(not run.errors, "page errors: %s" % run.errors[:2])
    return out, why


def test_file(browser, path, tmp, record, save_dir=None):
    name = Path(path).name
    try:
        picker = vp.read_data(path)
    except vp.Bad as e:
        record("%s: readable" % name, False, str(e))
        return
    errors, _, computed = vp.check(picker)
    record("%s: data passes validate_picker" % name, not errors, "; ".join(errors[:3]))
    if errors:
        return
    for width in (390, 1280):
        for mode in ("tab", "frame"):
            tag = "%s @%d %s" % (name, width, mode)
            run = Run(browser, path, width, mode, tmp)
            out, why = journey(run, picker)
            record("journey [%s]" % tag, not why, "; ".join(why))
            if "storage_words" not in out:   # the journey stopped part way; there is nothing more to check
                run.close()
                continue
            # export-names-choice
            bad = []
            try:
                env = pc.parse(out["text"])
                d = env["data"]
                if d["chosen"] != out["b"]:
                    bad.append("chosen is %r, the journey chose %r" % (d["chosen"], out["b"]))
                if d["controls"] != out["expected_controls"]:
                    bad.append("controls are %r, the journey set %r" % (d["controls"], out["expected_controls"]))
                if d["shortlist"] != [out["a"], out["b"]]:
                    bad.append("shortlist is %r" % d["shortlist"])
                if d["notes"].get(out["b"]) != NOTE:
                    bad.append("the note came back as %r" % d["notes"].get(out["b"]))
                if d["status"] != "final" or env["content_id"] != "%s@%s" % (picker["id"], picker.get("version", 1)):
                    bad.append("status %r, picker %r" % (d["status"], env["content_id"]))
                chosen_name = [o["name"] for o in picker["options"] if o["id"] == out["b"]][0]
                if chosen_name not in out["summary"]:
                    bad.append("the sentence above the box does not name %s: %r" % (chosen_name, out["summary"][:80]))
                if any(ord(ch) > 126 for ch in out["text"]):
                    bad.append("the short text is not plain ASCII")
            except pc.Bad as e:
                env = None
                bad.append("the short text does not parse: %s" % e)
            record("export-names-choice [%s]" % tag, not bad, "; ".join(bad))
            # block-round-trip
            bad = []
            try:
                from_json = pc.parse(out["json"])
                if env is None:
                    bad.append("no parsed text to compare")
                else:
                    x, y = json.loads(json.dumps(env)), json.loads(json.dumps(from_json))
                    x.pop("saved_at"), y.pop("saved_at")
                    if x != y:
                        diff = [k for k in x["data"] if x["data"][k] != y["data"].get(k)]
                        bad.append("the two forms differ in: %s" % (diff or "the envelope"))
                    for label, e2 in (("text", env), ("JSON", from_json)):
                        errs, _ = pc.check(e2, picker)
                        if errs:
                            bad.append("%s form: %s" % (label, errs[0]))
            except pc.Bad as e:
                bad.append("the JSON form does not parse: %s" % e)
            record("block-round-trip [%s]" % tag, not bad, "; ".join(bad))
            # clipboard
            held = out["clipboard"] == out["box_at_copy"]
            if held and "Copied" in out["copy_status"]:
                record("clipboard [%s]" % tag, True)
            else:
                sel = out["selection"]
                ok = "refused" in out["copy_status"] and sel[0] and sel[1] == 0 and sel[2] == sel[3] and not held
                record("clipboard [%s]" % tag, ok, "status %r, selection %r, clipboard matched %s" % (out["copy_status"][:60], sel, held))
            if mode == "frame":
                record("reload [%s]" % tag, "Not saved" in out["storage_words"], "a sandboxed frame has no storage; the page said %r" % out["storage_words"][:70])
            else:
                before = run.session()
                run.reload()
                bad = []
                if run.t.locator('[data-shortlist="%s"]' % out["a"]).get_attribute("aria-pressed") != "true":
                    bad.append("the shortlist did not come back")
                after = run.session()
                if after != before:
                    bad.append("the session after reload differs in: %s" % [k for k in before["data"] if before["data"][k] != after["data"].get(k)])
                if "Saved in this browser" not in out["storage_words"]:
                    bad.append("the page said %r" % out["storage_words"][:60])
                record("reload [%s]" % tag, not bad, "; ".join(bad))
                if save_dir and width == 1280:
                    stem = Path(path).stem
                    (Path(save_dir) / (stem + ".choice.txt")).write_text(out["text"] + "\n", encoding="utf-8")
                    (Path(save_dir) / (stem + ".choice.json")).write_text(out["json"] + "\n", encoding="utf-8")
            run.close()
    session_tests(browser, path, tmp, picker, record)
    focus_test(browser, path, tmp, picker, record)
    if picker["kind"] == "theme":
        contrast_test(browser, path, tmp, picker, computed, record)


def load_session(run, text, expect_confirm=None):
    t = run.t
    if t.locator("#i-text").count() == 0:
        t.locator("#page-toggle").click()
    t.locator("#i-text").fill(text)
    t.locator("#i-load").click()
    run.page.wait_for_timeout(150)
    if expect_confirm == "keep":
        t.locator("#i-cancel").click()
    elif expect_confirm == "load":
        t.locator("#i-continue").click()
    return (t.locator("#i-status").text_content() or ""), t.locator("#i-confirm").count()


def session_tests(browser, path, tmp, picker, record):
    name = Path(path).name
    opts = picker["options"]
    # build a session, export it, load it into a fresh page
    run = Run(browser, path, 1280, "tab", tmp)
    out, why = journey(run, picker)
    bad = list(why)
    try:
        exported = out.get("json", "")
        before = run.session()
        # A frame has no storage, so nothing is there already. It is the same width as the page the session
        # came from, because the facts in a session are measured where the page is shown: characters per line
        # at 390 wide are not the characters per line at 1280, and that is a true difference, not a lost session.
        fresh = Run(browser, path, 1280, "frame", tmp)
        status, _ = load_session(fresh, exported)
        got = fresh.session()
        if got != before:
            bad.append("import did not reproduce the session: differs in %s" % [k for k in before["data"] if before["data"][k] != got["data"].get(k)])
        if "Loaded" not in status:
            bad.append("the page said %r after a good import" % status[:60])
        wrong_app = json.dumps(dict(json.loads(exported), app="pocket-app"))
        newer = json.dumps(dict(json.loads(exported), schema=2))
        other = json.dumps(dict(json.loads(exported), content_id="another-picker@7"))
        for label, text, words in (("wrong app", wrong_app, "not by a sample picker"), ("newer schema", newer, "newer picker"),
                                   ("malformed JSON", exported[:-9], "not valid JSON"), ("empty paste", "   ", "Nothing was pasted")):
            status, _ = load_session(fresh, text)
            now = fresh.session()
            if words not in status:
                bad.append("%s: the page said %r" % (label, status[:70]))
            if now != before:
                bad.append("%s: the session changed" % label)
        status, asked = load_session(fresh, other, expect_confirm="keep")
        if fresh.session() != before:
            bad.append("another picker's session: keeping changed the session")
        fresh.t.locator("#page-toggle").click()
        fresh.t.locator("#i-text").fill(other)
        fresh.t.locator("#i-load").click()
        said = fresh.t.locator("#i-confirm").text_content() or ""
        if "another-picker@7" not in said or picker["id"] not in said:
            bad.append("the question does not say what differs: %r" % said[:90])
        fresh.t.locator("#i-continue").click()
        if fresh.session() != before:
            bad.append("another picker's session: loading it anyway did not reproduce the session")
        if fresh.errors:
            bad.append("page errors: %s" % fresh.errors[:2])
        fresh.close()
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:120])
    record("session-import [%s]" % name, not bad, "; ".join(bad))
    # reset and undo, on the same run
    bad = []
    try:
        t = run.t
        before = run.session()
        t.locator("#page-toggle").click()
        t.locator("#s-reset").click()
        words = t.locator("#s-confirm").text_content() or ""
        if "2 shortlisted options" not in words or "1 note" not in words:
            bad.append("the confirmation does not name what will go: %r" % words[:100])
        focus = t.evaluate("() => document.activeElement && document.activeElement.id")
        if focus != "s-reset-no":
            bad.append("focus is on %r, not on the safe choice" % focus)
        t.locator("#s-reset-no").click()
        if run.session() != before:
            bad.append("keeping everything changed the session")
        t.locator("#page-toggle").click()
        t.locator("#s-reset").click()
        t.locator("#s-reset-yes").click()
        cleared = run.session()["data"]
        if cleared["shortlist"] or cleared["chosen"] or cleared["notes"] or cleared["controls"] != {c["id"]: c["default"] for c in picker.get("controls", [])}:
            bad.append("the session was not cleared: %r" % {k: cleared[k] for k in ("shortlist", "chosen", "notes", "controls")})
        t.locator("#page-toggle").click()
        t.locator("#s-undo").click()
        if run.session() != before:
            bad.append("undo did not bring the session back")
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:120])
    record("reset-and-undo [%s]" % name, not bad, "; ".join(bad))
    run.close()
    # a long note on every option
    bad = []
    try:
        big = Run(browser, path, 1280, "frame", tmp)
        env = {"app": "sample-picker", "schema": 1, "content_id": "%s@%s" % (picker["id"], picker.get("version", 1)), "saved_at": "2026-10-09T00:00:00Z",
               "data": {"kind": picker["kind"], "status": "in progress", "chosen": None, "chosen_name": None,
                        "controls": {c["id"]: c["default"] for c in picker.get("controls", [])}, "shortlist": [o["id"] for o in opts], "rejected": [],
                        "notes": {o["id"]: ("%s: " % o["id"]) + ("a note with \"quotes\", commas and = signs. " * 125)[:5000] for o in opts}, "facts": []}}
        load_session(big, json.dumps(env))
        got = big.session()
        if got["data"]["notes"] != env["data"]["notes"] or got["data"]["shortlist"] != env["data"]["shortlist"]:
            bad.append("the notes or the shortlist changed on the way through")
        big.t.locator("#r-mode-text").click()
        back = pc.parse(big.t.locator("#r-text").input_value())
        if back["data"]["notes"] != env["data"]["notes"]:
            bad.append("the short text form lost part of a long note")
        if big.errors:
            bad.append("page errors: %s" % big.errors[:2])
        big.close()
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:120])
    record("large-notes [%s]" % name, not bad, "; ".join(bad))


UNDER_BAR_JS = r"""
() => {
  const e = document.activeElement;
  if (!e || e === document.body || e.closest('.bar, .cmp-tabs')) return null;
  const tabs = document.querySelector('.cmp-tabs'), bar = document.querySelector('.bar').getBoundingClientRect();
  const top = tabs && getComputedStyle(tabs).display !== 'none' ? tabs.getBoundingClientRect().top : bar.top;
  const r = e.getBoundingClientRect();
  return {name: e.id || e.getAttribute('data-fk') || e.tagName, under: r.bottom > top + 1 && r.top < bar.bottom};
}
"""


def focus_test(browser, path, tmp, picker, record):
    """Keyboard focus must not land under the bar that is fixed to the bottom of a narrow screen."""
    name, bad, stops = Path(path).name, [], 0
    run = Run(browser, path, 390, "tab", tmp)
    try:
        for view in ("options", "compare"):
            if view == "compare":
                for o in picker["options"][:2]:
                    run.t.locator('[data-shortlist="%s"]' % o["id"]).click()
                run.t.locator("#nav-compare").click()
            run.t.evaluate("() => { window.scrollTo(0, 0); if (document.activeElement) document.activeElement.blur(); }")
            count = run.t.evaluate("() => document.querySelectorAll('button, textarea, input, [tabindex]').length")
            for _ in range(count + 3):
                run.page.keyboard.press("Tab")
                got = run.t.evaluate(UNDER_BAR_JS)
                if got is None:
                    continue
                stops += 1
                if got["under"] and got["name"] not in [b.split(" ")[0] for b in bad]:
                    bad.append("%s (%s view)" % (got["name"], view))
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:120])
    run.close()
    record("focus-clear-of-bar [%s] (%d focus stops)" % (name, stops), not bad and stops >= 8, "focused under the bar: " + "; ".join(bad[:4]))


def contrast_test(browser, path, tmp, picker, computed, record):
    name, bad, checked = Path(path).name, [], 0
    run = Run(browser, path, 1280, "tab", tmp)
    try:
        for o in picker["options"]:
            run.t.locator("#nav-options").click()
            run.t.locator('[data-open="%s"]' % o["id"]).click()
            run.page.wait_for_timeout(150)
            shown = run.t.evaluate("() => [...document.querySelectorAll('.factlist li')].map(li => [li.querySelector('span').textContent, Number(li.querySelector('b').textContent)])")
            cols = run.t.evaluate(COLOURS_JS)
            mine = {}
            for c in cols:
                if c["bg"] is None:
                    continue
                r = vp.contrast(rgb_hex(c["fg"]), rgb_hex(c["bg"]))
                mine[c["role"]] = min(r, mine.get(c["role"], 99))
            for label, value in shown:
                roles = label.replace(" (under 4.5)", "").replace(" contrast", "").split(", ")
                for role in roles:
                    checked += 1
                    if role not in mine or abs(mine[role] - value) > 0.011:
                        bad.append("%s, %s: the page shows %.2f, worked out separately as %s" % (o["id"], role, value, mine.get(role)))
            low_tokens = min(p["ratio"] for p in computed[o["id"]])
            low_page = min(v for _, v in shown) if shown else None
            if low_page is None or abs(low_page - low_tokens) > 0.011:
                bad.append("%s: lowest on the page is %s, lowest from the tokens is %.2f" % (o["id"], low_page, low_tokens))
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:120])
    run.close()
    record("theme-contrast [%s] (%d numbers compared)" % (name, checked), not bad and checked > 0, "; ".join(bad[:4]))


# One fixture per renderer, named for the file: every kind, with "component" as a button and as a field, and
# "copy" as a notice. "copy" as a page header has no fixture here.
FIXTURES = ("theme", "type", "layout", "notice", "component", "field", "custom")


def run_script(name, *args):
    r = subprocess.run([sys.executable, str(HERE / name)] + [str(a) for a in args], capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def self_test(browser, tmp, engine, record):
    tmp = Path(tmp)
    fx = HERE / "fixtures"
    built = {}
    notes = []
    for kind in FIXTURES:
        out = tmp / ("fx-%s.html" % kind)
        args = [fx / ("%s-fixture.json" % kind), "--out", out, "--engine", engine]
        if kind == "custom":
            args += ["--renderers", fx / "custom-renderers.js"]
        code, so, se = run_script("build_picker.py", *args)
        if code != 0:
            notes.append("%s fixture did not build: %s %s" % (kind, so.strip()[-120:], se.strip()[-120:]))
        built[kind] = out
    sub = []

    def rec2(name, ok, detail=""):
        sub.append((name, ok, detail))
    if not notes:
        for kind in FIXTURES:
            test_file(browser, built[kind], tmp, rec2)
    failed = ["%s [%s]" % (n, d[:90]) for n, ok, d in sub if not ok]
    record("fixtures-build-and-run (%d checks on %d fixtures)" % (len(sub), len(FIXTURES)), not notes and not failed and len(sub) >= 25 * len(FIXTURES), "; ".join(notes + failed[:6]))

    # planted failure 1: a broken engine that moves the choice when a tweak changes
    src = Path(engine).read_text(encoding="utf-8")
    hook = "    S.controls[c.id] = v;\n"
    broken = tmp / "engine-broken.html"
    detail = ""
    if src.count(hook) != 1:
        ok, detail = False, "could not plant the fault: the engine no longer has the line it is planted after"
    else:
        broken.write_text(src.replace(hook, hook + "    if (S.chosen) S.chosen = P.options[0].id;\n"), encoding="utf-8")
        out = tmp / "fx-theme-broken.html"
        run_script("build_picker.py", fx / "theme-fixture.json", "--out", out, "--engine", broken)
        picker = vp.read_data(out)
        # choose first, then change a tweak: the order in which the fault bites
        run = Run(browser, out, 1280, "tab", tmp)
        t = run.t
        last = picker["options"][-1]["id"]
        t.locator('[data-open="%s"]' % last).click()
        t.locator("#d-choose").click()
        t.locator('[data-control="density"][data-value="compact"]').click()
        t.locator("#nav-result").click()
        env = pc.parse(t.locator("#r-text").input_value())
        run.close()
        caught_bad = env["data"]["chosen"] != last
        good = tmp / "fx-theme.html"
        run = Run(browser, good, 1280, "tab", tmp)
        t = run.t
        t.locator('[data-open="%s"]' % last).click()
        t.locator("#d-choose").click()
        t.locator('[data-control="density"][data-value="compact"]').click()
        t.locator("#nav-result").click()
        env2 = pc.parse(t.locator("#r-text").input_value())
        run.close()
        ok = caught_bad and env2["data"]["chosen"] == last and env2["data"]["controls"]["density"] == "compact"
        detail = "broken engine exported %r (the fault must show as not %r); sound engine exported %r" % (env["data"]["chosen"], last, env2["data"]["chosen"])
    record("planted-wrong-option-is-caught", ok, detail)

    # planted failure 2: body text under 4.5
    base = json.loads((fx / "theme-fixture.json").read_text(encoding="utf-8"))

    def variant(change):
        d = json.loads(json.dumps(base))
        change(d)
        return d

    def verdict(d, script="validate_picker.py"):
        p = tmp / "v.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        args = [p] if script == "validate_picker.py" else [p, "--out", tmp / "v.html", "--engine", engine]
        return run_script(script, *args)
    grey = lambda h: variant(lambda d: d["options"][0]["tokens"].update({"bg": "#ffffff", "surface": "#ffffff", "text": h}))  # noqa: E731
    low, near, edge = grey("#878787"), grey("#777777"), grey("#767676")   # 3.59, 4.48 and 4.54 to 1 on white
    c_low, o_low, _ = verdict(low)
    c_near, o_near, _ = verdict(near)
    c_edge, _, _ = verdict(edge)
    c_build, o_build, _ = verdict(low, "build_picker.py")
    (tmp / "v.html").unlink(missing_ok=True)
    c_build2, _, _ = verdict(near, "build_picker.py")
    wrote = (tmp / "v.html").exists()
    ok = (c_low == 1 and "body text on the page is 3.59" in o_low and c_near == 1 and "body text on the page is 4.48" in o_near and c_edge == 0
          and c_build == 1 and "Nothing was written" in o_build and c_build2 == 1 and not wrote)
    record("planted-low-contrast-is-refused", ok, "3.59 exit %d, 4.48 exit %d, 4.54 exit %d, build exit %d and %d, file written %s: %s"
           % (c_low, c_near, c_edge, c_build, c_build2, wrote, o_low.strip().splitlines()[1][:100] if len(o_low.strip().splitlines()) > 1 else ""))

    # validator refusals beside valid neighbours
    extra = lambda n: {"id": "extra-%s" % "abcdefgh"[n], "name": "Extra %s" % "ABCDEFGH"[n], "note": "A further option that differs in its own way, number %d." % n,  # noqa: E731
                       "tokens": dict(base["options"][0]["tokens"], line="#d%dd0bc" % n)}
    pairs = [
        ("one option", variant(lambda d: d.__setitem__("options", d["options"][:1])), variant(lambda d: (d.__setitem__("options", d["options"][:2])))),
        ("nine options", variant(lambda d: d["options"].extend(extra(i) for i in range(6))), variant(lambda d: d["options"].extend(extra(i) for i in range(5)))),
        ("lorem ipsum", variant(lambda d: d["context"].__setitem__("body", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.")), base),
        ("Sample text", variant(lambda d: d["context"].__setitem__("title", "Sample text")), base),
        ("twin notes", variant(lambda d: d["options"][1].__setitem__("note", d["options"][0]["note"])), base),
        ("twin renderings", variant(lambda d: d["options"][1].__setitem__("tokens", d["options"][0]["tokens"])), base),
        ("dead control", variant(lambda d: d["controls"].append({"id": "sparkle", "label": "Sparkle", "type": "toggle", "default": False})), base),
        ("default off the grid", variant(lambda d: d["controls"][1].__setitem__("default", 16.5)), variant(lambda d: d["controls"][1].__setitem__("default", 17))),
        ("default outside the range", variant(lambda d: d["controls"][1].__setitem__("default", 21)), variant(lambda d: d["controls"][1].__setitem__("default", 20))),
        ("number as text", variant(lambda d: d["controls"][1].__setitem__("min", "14")), base),
        ("id with capitals", variant(lambda d: d["options"][0].__setitem__("id", "Seed_Packet")) , base),
        ("missing token", variant(lambda d: d["options"][2]["tokens"].pop("danger")), base),
        ("token not hex", variant(lambda d: d["options"][2]["tokens"].__setitem__("accent", "skyblue")), base),
        ("recommended names nothing", variant(lambda d: d["recommended"].__setitem__("id", "no-such-option")), base),
        ("no context", variant(lambda d: d.pop("context")), base),
        ("two-line note", variant(lambda d: d["options"][0].__setitem__("note", "Cream paper.\nAnd a green accent, on a second line.")), base),
    ]
    bad = []
    for label, refuse, accept in pairs:
        if "recommended" in refuse and refuse["recommended"]["id"] not in [o["id"] for o in refuse["options"]] and label != "recommended names nothing":
            refuse["recommended"]["id"] = refuse["options"][0]["id"]
        if accept is not base and accept["recommended"]["id"] not in [o["id"] for o in accept["options"]]:
            accept["recommended"]["id"] = accept["options"][0]["id"]
        cr, _, er = verdict(refuse)
        ca, oa, _ = verdict(accept)
        if cr != 1 or ca != 0 or "Traceback" in er:
            bad.append("%s: refused exit %d, neighbour exit %d %s" % (label, cr, ca, oa.strip().splitlines()[1][:80] if ca else ""))
    (tmp / "raw.json").write_bytes(b'{"id": "x", ' + bytes([255]) + b'}')
    c1, _, _ = run_script("validate_picker.py", tmp / "raw.json")
    (tmp / "raw.json").write_bytes(b'{"id": NaN}')
    c2, _, _ = run_script("validate_picker.py", tmp / "raw.json")
    c3, _, e3 = run_script("validate_picker.py", fx / "theme-fixture.json", "--loud")
    c4, _, _ = run_script("validate_picker.py", tmp / "no-such-file.json")
    seven = variant(lambda d: d["options"].extend(extra(i) for i in range(4)))
    c5, o5, _ = verdict(seven)
    if (c1, c2, c3, c4) != (2, 2, 2, 2) or "Traceback" in e3 or c5 != 0 or "more than six" not in o5:
        bad.append("bytes, NaN, unknown option, missing file gave %s (want all 2); seven options exit %d with advisory %s" % ((c1, c2, c3, c4), c5, "more than six" in o5))
    record("validator-refusals (%d pairs)" % len(pairs), not bad, "; ".join(bad[:4]))

    # parse_choice refusals and tolerance
    good_block = "\n".join([
        "=== sample-picker choice v1 ===", "picker: ledger-theme-fixture@2", "kind: theme", "status: final", "chosen: night-frost", 'chosen-name: "Night frost"',
        'control: density = "compact"', "control: text-size = 16", "control: radius = 6", "shortlist: potting-shed, night-frost", "rejected: (none)",
        'note: night-frost = "Calm, but check it \\"outdoors\\" = in sun"', 'fact: "body text contrast" = 15.2', "saved: 2026-10-09T02:03:04Z", "=== end ==="])
    cases = [
        ("valid block", good_block, 0),
        ("quoted, fenced and with curly quotes", "Here you go:\n```\n" + "\n".join("> " + ln for ln in good_block.replace('"', chr(0x201c)).splitlines()) + "\n```\nthanks", 0),
        ("Windows line ends", good_block.replace("\n", "\r\n"), 0),
        ("cut off before the end", good_block.replace("\n=== end ===", ""), 1),
        ("unknown line", good_block.replace("kind: theme", "kind: theme\nmood: sunny"), 1),
        ("final with nothing chosen", good_block.replace("chosen: night-frost", "chosen: (none)").replace('chosen-name: "Night frost"\n', ""), 1),
        ("impossible date", good_block.replace("2026-10-09T02:03:04Z", "2026-13-40T02:03:04Z"), 1),
        ("date without dashes", good_block.replace("2026-10-09T02:03:04Z", "20261009T020304Z"), 1),
        ("another picker's result", good_block.replace("ledger-theme-fixture@2", "ledger-theme-fixture@1"), 1),
        ("an option the picker lacks", good_block.replace("chosen: night-frost", "chosen: day-frost"), 1),
        ("a tweak value the control lacks", good_block.replace('density = "compact"', 'density = "airy"'), 1),
        ("range value as text", good_block.replace("text-size = 16", 'text-size = "16"'), 1),
        ("range value at its top", good_block.replace("text-size = 16", "text-size = 20"), 0),
        ("range value past its top", good_block.replace("text-size = 16", "text-size = 21"), 1),
        ("chosen and rejected at once", good_block.replace("rejected: (none)", "rejected: night-frost"), 1),
    ]
    bad = []
    for label, text, want in cases:
        (tmp / "c.txt").write_text(text, encoding="utf-8")
        code, so, se = run_script("parse_choice.py", tmp / "c.txt", "--picker", fx / "theme-fixture.json", "--json")
        if code != want or "Traceback" in se:
            bad.append("%s: exit %d, wanted %d" % (label, code, want))
        elif want == 0 and json.loads(so)["choice"]["data"]["notes"]["night-frost"] != 'Calm, but check it "outdoors" = in sun':
            bad.append("%s: the note came back changed" % label)
    c1, _, _ = run_script("parse_choice.py", tmp / "none.txt")
    c2, _, e2 = run_script("parse_choice.py", tmp / "c.txt", "--frob")
    if (c1, c2) != (2, 2) or "Traceback" in e2:
        bad.append("missing file and unknown option gave %s, want (2, 2)" % ((c1, c2),))
    record("parse-refusals (%d cases)" % len(cases), not bad, "; ".join(bad[:4]))

    # host storage: used when present, and a failing one falls back
    bad = []
    for label, script, want in (
            ("working host storage", "window.__hs = {}; window.storage = {get: k => Promise.resolve(window.__hs[k] || null), set: (k, v) => { window.__hs[k] = v; window.__sets = (window.__sets || 0) + 1; return Promise.resolve(); }};", "Saved by the app showing this page"),
            ("failing host storage", "window.storage = {get: k => Promise.reject(new Error('no')), set: (k, v) => Promise.reject(new Error('no'))};", "Saved in this browser")):
        run = Run(browser, built["theme"], 1280, "tab", tmp)
        run.page.add_init_script(script)
        run.open()
        try:
            first = base["options"][0]["id"]
            run.t.locator('[data-shortlist="%s"]' % first).click()
            run.page.wait_for_timeout(200)
            run.t.locator("#nav-result").click()
            words = run.t.locator("#main p.muted").last.text_content() or ""
            if want not in words:
                bad.append("%s: the page said %r" % (label, words[:60]))
            if label.startswith("working") and not run.page.evaluate("() => (window.__sets || 0) > 0 && Object.keys(window.__hs).some(k => window.__hs[k].indexOf('\"shortlist\"') > 0)"):
                bad.append("working host storage was not written to")
            if run.session()["data"]["shortlist"] != [first]:
                bad.append("%s: the session was lost" % label)
            if run.errors:
                bad.append("%s: page errors %s" % (label, run.errors[:1]))
        except Exception as e:  # noqa: BLE001
            bad.append("%s stopped: %s" % (label, str(e).split("\n")[0][:100]))
        run.close()
    record("host-storage", not bad, "; ".join(bad))

    # a font that cannot be installed is named as missing
    bad = []
    d = json.loads((fx / "type-fixture.json").read_text(encoding="utf-8"))
    d["options"][0]["sample"]["stack"] = "\"Zzqx Not A Typeface\", serif"
    (tmp / "t.json").write_text(json.dumps(d), encoding="utf-8")
    run_script("build_picker.py", tmp / "t.json", "--out", tmp / "t.html", "--engine", engine)
    run = Run(browser, tmp / "t.html", 1280, "tab", tmp)
    try:
        run.t.locator('[data-open="%s"]' % d["options"][0]["id"]).click()
        text = run.t.locator(".factlist").text_content() or ""
        if "Zzqx Not A Typeface" not in text or "not installed here" not in text or "serif (the browser's default serif)" not in text:
            bad.append("the facts read %r" % text[:160])
        size0 = run.t.locator("#main .y-p").first.evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
        run.t.locator("#ctl-scale").press("ArrowRight")
        size1 = run.t.locator("#main .y-p").first.evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
        if not abs(size1 - size0 * 1.05) < 0.05:
            bad.append("the size tweak moved the text from %s to %s px, wanted 5 percent more" % (size0, size1))
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:100])
    run.close()
    record("missing-font-is-named", not bad, "; ".join(bad))

    bad = []
    run = Run(browser, built["custom"], 390, "frame", tmp)
    try:
        before = run.t.locator("#main .smp").first.text_content() or ""
        run.t.locator('[data-open="plain-count"]').click()
        run.t.locator('[data-control="show-file"]').click()
        after = run.t.locator("#main .smp").first.text_content() or ""
        if "Now sending" not in before or "Now sending" in after:
            bad.append("before %r, after %r" % (before[-50:], after[-50:]))
    except Exception as e:  # noqa: BLE001
        bad.append("stopped: " + str(e).split("\n")[0][:100])
    run.close()
    record("custom-tweak-redraws", not bad, "; ".join(bad))


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--") or not v.strip():
                print("test_picker: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("test_picker: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if ("--self-test" in flags) == bool(args):
        print(__doc__)
        return 2
    for a in args:
        if not Path(a).is_file():
            print("test_picker: cannot read " + a, file=sys.stderr)
            return 2
    engine = Path(opts.get("--engine", str(HERE.parent / "assets" / "picker.html")))
    if "--self-test" in flags and not engine.is_file():
        print("test_picker: cannot find the engine " + str(engine), file=sys.stderr)
        return 2
    if "--save-choice" in opts and not Path(opts["--save-choice"]).is_dir():
        print("test_picker: --save-choice needs an existing folder", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 3
    results = []

    def record(name, ok, detail=""):
        results.append({"test": name, "ok": bool(ok), "detail": detail})
        if not ok:
            pr.observe_failures([name + ": " + detail], "A named picker test failed before any later teardown/interruption.")
        if "--json" not in flags:
            print(("%-5s %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + detail + "]") if (detail and not ok) else "")).encode("ascii", "replace").decode("ascii"), flush=True)
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e)[:120])
            return 3
        if "--self-test" in flags:
            self_test(browser, tmp, engine, record)
        else:
            for a in args:
                test_file(browser, a, tmp, record, opts.get("--save-choice"))
        browser.close()
    failed = [r for r in results if not r["ok"]]
    pr.result("failed" if failed else "completed" if results else "partial", {"tests_run": len(results), "passed": len(results) - len(failed), "failed": [r["test"] for r in failed], "mode": "self-test" if "--self-test" in flags else "picker files", "requested_files": list(args), "meaning": "Named behaviour tests, not visual option quality, real-device smoothness or host verification."}, "Named picker tests finished." if results else "No tests ran.")
    if "--json" in flags:
        print(json.dumps({"tests": results, "failed": len(failed)}, indent=1, ensure_ascii=True))
    else:
        print("RESULT: %s. %d of %d test(s) passed. A pass says the picker works, not that the options are good." % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(pr.run("test_picker", main, sys.argv[1:]))
