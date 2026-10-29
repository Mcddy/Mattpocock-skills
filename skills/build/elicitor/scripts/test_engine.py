#!/usr/bin/env python3
"""Drive the questionnaire engine in a real browser and check what it does. Needs Python Playwright.

Usage:
  python test_engine.py [--engine ENGINE.html] [--only NAME[,NAME...]] [--revision OLD NEW]
                        [--instrument BUILT.html]... [--shots DIR] [--list] [--json]

--engine      the engine to test (default: ../assets/engine.html beside this script). The tests
              put their own fixtures into its data block, so a changed engine can be tested as is.
--only        run only the named tests. --list prints the names and what each covers.
--revision    two instruments (.json or built .html), an old version and its revision, for the
              test revision_keeps_ids (default: fixtures/all_types.json and all_types_v2.json).
--instrument  a built questionnaire to add to the test export_round_trip. May be repeated.
--shots       a folder to save screenshots of the main screens into (nothing is saved without it).
--write-fixtures  fill the three fixture instruments with the fixed answer set and write their
              exports to fixtures/ (export_all_types.md, export_quiz.md, response_survey.txt), for
              test_tools.py to read. Run it after a deliberate change to an export format. The
              test export_round_trip fails while those files differ from what the engine produces.

What it does: serves the pages to a headless Chromium from memory under the made-up address
https://elicitor.test (no socket is opened and nothing leaves the machine), then uses the page the
way a person would: clicks, typing, reloads, pasting. Each test runs at a 390 by 844 viewport, and
the first twelve listed below also at 1280 by 800. A viewport is not a phone.

What it enforces (FAIL, exit 1): every assertion in the named tests. The tests and what they cover:
  intake_journey          answer, note, Back and change, Skip, review, edit from review, finish;
                          the export holds every id, the changed answer, the note word for word
                          and the skipped mark, and parse_export.py reads it back exactly
  clipboard_refused       clipboard refused (stubbed, and inside a sandboxed frame): the complete
                          export is in the text box and selected; with permission, the copy is real
  reload_resume           reload mid-way resumes at the same question with answers intact
  storage_throwing        storage that throws: the page works, says it is not saving, and a resume
                          code restores progress in a fresh load; a host storage object, a slow
                          one (the loading state) and one that never answers
  import_refusals         wrong questionnaire, wrong app, newer schema, bad schema, cut-off text,
                          empty paste: each refused with answers untouched; the valid neighbour
                          loads; a different version asks first
  quiz_scoring            a known answer pattern gives the exact score; immediate and at-end
                          marking; every option explained for a missed item; skipped not wrong
  show_if                 a hidden question is passed over and absent from the export; changing
                          the controlling answer brings it back
  long_instrument         120 questions: time to draw a question; 400 questions: state round trip
  export_round_trip       every type, and each --instrument: export, parse, compare with the
                          saved state; then load the finished export into a fresh page
  awkward_text            answers and notes holding lines that look like export structure, and
                          text in five scripts: parsed back exactly, and loaded back by the page
  revision_keeps_ids      a revision keeps ids, and old answers land on the same questions, from
                          an old export and from answers saved in the browser under the old version
  survey_mode             disclosure first; the response block; hidden and skipped markers
  tallies                 counts with denominators and the fixed caveat, on screen and exported
  section_layout          a section at a time: same export as one at a time
  display_settings        each theme, text size, spacing, movement: applied, shown, kept, reset
  no_overflow             long content at 360, 390 and 1280 wide, at the largest text size
  undo_and_reset          reset is confirmed and can be undone; skip of an answered question too
  data_block_faults       a broken or empty data block gives a stated fault, not a blank page
  keyboard_and_focus      Enter advances, focus follows the screen, moves keep focus
  page_rules              no form element, no dialogs, no outside requests, no console errors
What it reports without judging: timings, and what the clipboard did in the sandboxed frame.

What it cannot tell: how the page behaves in any real host's preview, on a real phone, with a
screen reader, or in a browser other than this Chromium.

Exit codes: 0 every test passed. 1 a test failed. 2 bad arguments or unreadable input.
3 could not run because Playwright or its browser is missing (prints NOT RUN).
"""
import copy
import json
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_instrument import build  # noqa: E402
from parse_export import parse_text  # noqa: E402
from validate_instrument import InputError, check, compare, load_instrument, read_text  # noqa: E402

ORIGIN = "https://elicitor.test"
TALLY_LINE = "These totals are counts of your answers. They are not a validated measure of anything."
STORED = {"fixture-all-types": "export_all_types.md", "fixture-quiz": "export_quiz.md", "fixture-survey": "response_survey.txt"}
NOTE_ON = ("single", "multi", "likert", "scale", "rank")
FLAGS = {"--json", "--list", "--write-fixtures"}
VALUES = {"--engine", "--only", "--shots"}
READY = "#btn-start, #main article.q, #btn-finish, #export-text, #data-problems, #no-questions"
THROWING_STORAGE = "Object.defineProperty(window, 'localStorage', {get: function () { throw new DOMException('The operation is insecure.', 'SecurityError'); }});"
CLIPBOARD_REFUSED = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: function () { return Promise.reject(new DOMException('Write permission denied.', 'NotAllowedError')); }}});"
                     "document.execCommand = function () { return false; };")
SLOW_HOST_STORAGE = ("window.storage = {get: function (k) { return new Promise(function (res) { setTimeout(function () { res(null); }, 700); }); },"
                     "set: function (k, v) { return Promise.resolve(true); }};")
SILENT_HOST_STORAGE = "window.storage = {get: function (k) { return new Promise(function () {}); }, set: function (k, v) { return new Promise(function () {}); }};"
HOST_STORAGE = ("window.__hostCalls = 0; window.storage = {"
                "get: function (k) { window.__hostCalls++; return Promise.resolve({value: sessionStorage.getItem('host:' + k)}); },"
                "set: function (k, v) { window.__hostCalls++; sessionStorage.setItem('host:' + k, v); return Promise.resolve(true); }};")


# ---------------------------------------------------------------- a second, independent reading of the rules
def one_line(s):
    return " ".join(str(s or "").split())


def canon(s):
    lines = str(s).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(ln.rstrip(" \t") for ln in lines).strip(" \t\n")


def opt_texts(q):
    return [o["text"] if isinstance(o, dict) else o for o in q.get("options", [])]


def note_on(inst, q):
    if isinstance(q.get("note"), bool):
        return q["note"]
    default = inst.get("notes", "off" if inst["mode"] == "quiz" else "on")
    return default == "on" and q["type"] in NOTE_ON


def valid(q, v):
    t = q["type"]
    if v is None:
        return False
    if t == "single":
        return isinstance(v, str) and v in opt_texts(q)
    if t == "multi":
        return isinstance(v, list) and len(v) > 0 and all(x in opt_texts(q) for x in v) and len(set(v)) == len(v)
    if t == "rank":
        return isinstance(v, list) and sorted(v) == sorted(opt_texts(q))
    if t == "text":
        return isinstance(v, str) and canon(v) != ""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    if t == "likert":
        return v == int(v) and 1 <= v <= len(q["labels"])
    if t == "scale":
        return v == int(v) and q["min"] <= v <= q["max"] and (v - q["min"]) % q.get("step", 1) == 0
    return (q.get("min") is None or v >= q["min"]) and (q.get("max") is None or v <= q["max"]) and (not q.get("integer") or v == int(v))


def fits(v, c):
    if "equals" in c:
        return not isinstance(v, list) and v == c["equals"] and type(v) is not bool
    if "includes" in c:
        return isinstance(v, list) and c["includes"] in v
    if "at_least" in c:
        return isinstance(v, (int, float)) and v >= c["at_least"]
    if "at_most" in c:
        return isinstance(v, (int, float)) and v <= c["at_most"]
    return True


def visible(inst, answers):
    out, shown, byid = [], set(), {q["id"]: q for q in inst["questions"]}
    for q in inst["questions"]:
        c, ok = q.get("show_if"), True
        if c:
            dep = byid.get(c["q"])
            has = dep is not None and valid(dep, answers.get(dep["id"], {}).get("v"))
            if dep is None or dep["id"] not in shown:
                ok = False
            elif "answered" in c:
                ok = has if c["answered"] else not has
            else:
                ok = has and fits(answers[dep["id"]]["v"], c)
        if ok:
            out.append(q)
            shown.add(q["id"])
    return out


def status_of(q, answers):
    a = answers.get(q["id"], {})
    return "answered" if valid(q, a.get("v")) else ("skipped" if a.get("skipped") is True else "no_answer")


def correct_set(q):
    return [o["text"] for o in q["options"] if isinstance(o, dict) and o.get("correct") is True]


def is_correct(q, v):
    c = correct_set(q)
    return (v == c[0] and len(c) == 1) if q["type"] == "single" else (isinstance(v, list) and sorted(v) == sorted(c))


def expected_record(inst, env):
    """What parse_export.py should return for the markdown export of this saved state."""
    answers = env["data"]["answers"]
    vis = visible(inst, answers)
    secs = {s["id"]: one_line(s.get("title")) or s["id"] for s in inst.get("sections", [])}
    last = inst["sections"][0]["id"] if inst.get("sections") else None
    qs, n = [], {"answered": 0, "skipped": 0, "no_answer": 0}
    sec_of = {}
    for q in inst["questions"]:
        if q.get("section") in secs:
            last = q["section"]
        sec_of[q["id"]] = secs.get(last) if last else None
    for q in vis:
        a, st = answers.get(q["id"], {}), status_of(q, answers)
        n[st] += 1
        v = a.get("v") if st == "answered" else None
        rec = {"id": q["id"], "section": sec_of[q["id"]], "text": one_line(q["text"]), "type": q["type"], "status": st,
               "answer": canon(v) if (q["type"] == "text" and st == "answered") else v,
               "note": (canon(a["note"]) or None) if (note_on(inst, q) and a.get("note")) else None}
        if q["type"] == "likert" and st == "answered":
            rec["points"], rec["label"] = len(q["labels"]), one_line(q["labels"][v - 1])
        if q["type"] == "number" and st == "answered":
            rec["unit"] = one_line(q.get("unit")) or None
        if inst["mode"] == "quiz":
            right = st == "answered" and is_correct(q, v)
            rec["result"] = ("correct" if right else "incorrect") if st == "answered" else ("skipped" if st == "skipped" else "no answer")
            if not right:
                rec["correct_answer"] = correct_set(q)[0] if q["type"] == "single" else correct_set(q)
        qs.append(rec)
    out = {"instrument": {"id": inst["id"], "version": inst["version"], "mode": inst["mode"], "title": one_line(inst["title"])},
           "finished": env["data"].get("finished_at"), "purpose": one_line(inst.get("purpose")) or None,
           "counts": {"shown": len(vis), "answered": n["answered"], "skipped": n["skipped"], "no_answer": n["no_answer"], "hidden": len(inst["questions"]) - len(vis)},
           "questions": qs, "tallies": expected_tallies(inst, answers), "score": None}
    if inst["mode"] == "quiz":
        out["score"] = {"correct": sum(1 for r in qs if r["result"] == "correct"), "attempted": n["answered"], "total": len(vis), "skipped": n["skipped"], "no_answer": n["no_answer"]}
    return out


def expected_tallies(inst, answers):
    if inst["mode"] == "quiz":
        return []
    vis, out = visible(inst, answers), []
    for t in inst.get("tallies", []):
        items = [q for q in vis if t["tag"] in q.get("tags", [])]
        got = [q for q in items if valid(q, answers.get(q["id"], {}).get("v"))]
        when = t.get("when", {"answered": True})
        out.append({"id": t["id"], "label": one_line(t["label"]), "count": sum(1 for q in got if "answered" in when or fits(answers[q["id"]]["v"], when)),
                    "of": len(items), "answered": len(got)})
    return out


def expected_response(inst, env):
    answers = env["data"]["answers"]
    shown = {q["id"] for q in visible(inst, answers)}
    out = []
    for q in inst["questions"]:
        a = answers.get(q["id"], {})
        st = status_of(q, answers) if q["id"] in shown else "hidden"
        v = a.get("v") if st == "answered" else None
        out.append({"id": q["id"], "status": st, "answer": canon(v) if (q["type"] == "text" and st == "answered") else v,
                    "note": (canon(a["note"]) or None) if (q["id"] in shown and note_on(inst, q) and a.get("note")) else None})
    return out


def diff_record(got, want):
    """List the differences between a parsed export and the expected record."""
    out = []
    for k in ("instrument", "finished", "purpose", "counts"):
        if got.get(k) != want[k]:
            out.append("%s: parsed %r, expected %r" % (k, got.get(k), want[k]))
    gq = got.get("questions", [])
    if [q["id"] for q in gq] != [q["id"] for q in want["questions"]]:
        out.append("question ids differ: parsed %r, expected %r" % ([q["id"] for q in gq], [q["id"] for q in want["questions"]]))
    else:
        for g, w in zip(gq, want["questions"]):
            for k in w:
                if g.get(k) != w[k]:
                    out.append("question %s, field %s: parsed %r, expected %r" % (w["id"], k, g.get(k), w[k]))
    if (got.get("tallies") or []) != want["tallies"]:
        out.append("tallies: parsed %r, expected %r" % (got.get("tallies"), want["tallies"]))
    if want["score"] is not None:
        gs = {k: (got.get("score") or {}).get(k) for k in want["score"]}
        if gs != want["score"]:
            out.append("score: parsed %r, expected %r" % (gs, want["score"]))
    return out


def auto_plan(inst):
    """A fixed, varied set of answers for any instrument: every type, some notes, some skips."""
    plan = {}
    for k, q in enumerate(inst["questions"]):
        t, opts = q["type"], opt_texts(q)
        if not q.get("required") and k % 7 == 4:
            plan[q["id"]] = {"skip": True}
            continue
        if t == "single":
            v = opts[k % len(opts)]
        elif t == "multi":
            v = [o for i, o in enumerate(opts) if (i + k) % 2 == 0] or [opts[0]]
        elif t == "rank":
            v = opts[1:] + opts[:1]
        elif t == "text":
            v = ("Text for %s: 50%% sure & <not> certain." % q["id"]) + ("\n\n  An indented second paragraph.\nThird line." if q.get("long") else "")
        elif t == "likert":
            v = 1 + k % len(q["labels"])
        elif t == "scale":
            n = (q["max"] - q["min"]) // q.get("step", 1) + 1
            v = q["min"] + q.get("step", 1) * ((k * 3) % n)
        else:
            lo = q["min"] if q.get("min") is not None else 0
            hi = q["max"] if q.get("max") is not None else lo + 100
            v = lo + (hi - lo) // 3 if q.get("integer") else min(hi, lo + (hi - lo) // 3 + 0.5)
        step = {"v": v}
        if note_on(inst, q) and k % 3 == 0:
            step["note"] = "Note on %s: \"quoted\", 100%% & <tag>?\nSecond line of the note." % q["id"]
        plan[q["id"]] = step
    return plan


# ---------------------------------------------------------------- driving the page the way a person would
class T:
    """Collects the failures of one test."""

    def __init__(self):
        self.fails, self.notes = [], []

    def ok(self, cond, msg):
        if not cond:
            self.fails.append(msg)
        return bool(cond)

    def eq(self, got, want, what):
        return self.ok(got == want, "%s: got %r, expected %r" % (what, got, want))

    def has(self, text, part, what):
        return self.ok(part in (text or ""), "%s: %r not found in %r" % (what, part, (text or "")[:160]))

    def note(self, msg):
        self.notes.append(msg)


def stage(s):
    return s.evaluate("""() => document.getElementById('export-text') ? 'done' : document.getElementById('btn-finish') ? 'review'
        : document.querySelector('#main article.q') ? 'q' : document.getElementById('btn-start') ? 'start' : 'other'""")


def cur_q(s):
    return s.evaluate("() => { const a = document.querySelector('#main article.q'); return a ? a.getAttribute('data-q') : null; }")


def text_of(s, sel):
    return s.evaluate("(sel) => { const n = document.querySelector(sel); return n ? n.textContent : null; }", sel)


def facts(s, sel):
    """The label and value pairs of a facts list, as a dict."""
    return dict(s.evaluate("(sel) => Array.from(document.querySelectorAll(sel + ' .facts li')).map(n => [n.querySelector('.k').textContent, n.querySelector('.v').textContent])", sel))


def is_hidden(s, sel):
    return s.evaluate("(sel) => { const n = document.querySelector(sel); return !n || n.hidden || !!n.closest('[hidden]'); }", sel)


def set_answer(s, q, v):
    qid, t, opts = q["id"], q["type"], opt_texts(q)
    if t == "single":
        s.check("#in-%s-%d" % (qid, opts.index(v)))
    elif t == "multi":
        for i, o in enumerate(opts):
            (s.check if o in v else s.uncheck)("#in-%s-%d" % (qid, i))
    elif t in ("text", "number"):
        s.fill("#in-" + qid, str(v))
    elif t == "likert":
        s.check("#in-%s-%d" % (qid, v - 1))
    elif t == "scale":
        step = q.get("step", 1)
        n = (q["max"] - q["min"]) // step + 1
        if n <= 11:
            s.click("label[for='in-%s-%d']" % (qid, (v - q["min"]) // step))
        else:
            s.click("#more-" + qid)                       # the first press records the value the slider shows
            now = int(s.input_value("#in-" + qid))
            for _ in range(abs(v - now) // step):
                s.click(("#more-" if v > now else "#less-") + qid)
    elif t == "rank":
        cur = s.evaluate("(id) => Array.from(document.querySelectorAll('[data-q=\"' + id + '\"] .rank .t')).map(n => n.textContent)", qid)
        if cur == v:
            if not is_hidden(s, "#keep-" + qid):
                s.click("#keep-" + qid)
            return
        for i, want in enumerate(v):
            j = cur.index(want)
            while j > i:
                s.click("#up-%s-%d" % (qid, j))
                cur[j - 1], cur[j] = cur[j], cur[j - 1]
                j -= 1


def do_step(s, q, step):
    """Apply one planned step to the question on screen and leave it."""
    qid = q["id"]
    if step is None or step.get("skip"):
        s.click("#btn-skip")
        return
    if "v" in step:
        set_answer(s, q, step["v"])
    if "note" in step:
        s.fill("#note-" + qid, step["note"])
    s.click("#btn-next")
    if stage(s) == "q" and cur_q(s) == qid:               # quiz, marked after each item: the first press checks
        err = text_of(s, "#qe-" + qid)
        if err:
            raise AssertionError("could not leave %s: %s" % (qid, err))
        s.click("#btn-next")


def walk(s, inst, plan, start=True):
    """From the first screen to the review screen, one question at a time."""
    byid = {q["id"]: q for q in inst["questions"]}
    if start:
        s.click("#btn-start")
    for _ in range(len(inst["questions"]) + 2):
        if stage(s) != "q":
            break
        qid = cur_q(s)
        do_step(s, byid[qid], plan.get(qid))
    if stage(s) != "review":
        raise AssertionError("the walk did not reach the review screen (stage %s, question %s)" % (stage(s), cur_q(s)))


def finish(s):
    s.click("#btn-finish")
    s.wait_for_selector("#export-text")
    return s.input_value("#export-text")


def open_panel(s):
    if s.evaluate("() => document.getElementById('panel').hidden"):
        s.click("#panel-toggle")


def resume_code(s):
    open_panel(s)
    s.click("#resume-make")
    text = s.input_value("#resume-text")
    s.click("#panel-close")
    return text


def do_import(s, text):
    open_panel(s)
    if s.evaluate("() => document.getElementById('import-box').hidden"):
        s.click("#import-open")
    s.fill("#import-text", text)
    s.click("#import-go")


def answers_of(env_text):
    return json.loads(env_text)["data"]["answers"]


class Env:
    def __init__(self, browser, engine_text, shots):
        self.browser, self.engine_text, self.shots = browser, engine_text, shots
        self.files, self.noise, self.count, self.write_fixtures = {}, [], 0, False
        self.fix = {n: load_instrument(str(HERE / "fixtures" / (n + ".json")))[0] for n in ("all_types", "all_types_v2", "quiz", "survey")}

    def put(self, inst, name=None, raw=None):
        """Add a page built from an instrument (or raw page text) and return its file name."""
        self.count += 1
        name = name or "p%d.html" % self.count
        self.files["/" + name] = (raw if raw is not None else build(self.engine_text, inst)).encode("utf-8")
        frame = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>frame</title></head><body style="margin:0">'
                 '<iframe id="f" name="f" sandbox="allow-scripts" src="%s/%s" style="border:0;width:100vw;height:100vh"></iframe></body></html>' % (ORIGIN, name))
        self.files["/framed-" + name] = frame.encode("utf-8")
        return name

    def context(self, width=390, height=844, init=None, permissions=None):
        ctx = self.browser.new_context(viewport={"width": width, "height": height})
        ctx.set_default_timeout(6000)
        if permissions:
            ctx.grant_permissions(permissions, origin=ORIGIN)
        if init:
            ctx.add_init_script(init)

        def handle(route):
            path = urlsplit(route.request.url).path
            body = self.files.get(path)
            if path == "/favicon.ico":
                route.fulfill(status=204, body="")
            elif body is None:
                route.fulfill(status=404, content_type="text/plain", body="not found")
            else:
                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)

        ctx.route(ORIGIN + "/**", handle)
        ctx.on("request", lambda r: None if r.url.startswith((ORIGIN, "data:", "blob:", "about:")) else self.noise.append("outside request: " + r.url[:120]))
        return ctx

    def page(self, ctx, name):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: self.noise.append("page error: " + str(e)[:200]))
        pg.on("console", lambda m: self.noise.append("console %s: %s" % (m.type, m.text[:200])) if m.type == "error" and "favicon" not in m.text else None)
        pg.goto(ORIGIN + "/" + name)
        pg.wait_for_selector(READY)
        return pg

    def framed(self, ctx, name):
        pg = ctx.new_page()
        pg.goto(ORIGIN + "/framed-" + name)
        fr = pg.frame(name="f")
        fr.wait_for_selector(READY)
        return pg, fr

    def shot(self, pg, name):
        if self.shots:
            Path(self.shots).mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(Path(self.shots) / (name + ".png")))


NOTE1 = 'Shed door is 76 cm wide; a "floating" look is preferred & <no> brackets. 100% sure?'
WHY = "The room is being painted on the 14th.\n\n  Anything on the wall has to be up before then.\nAfter that it can wait."


# ---------------------------------------------------------------- the tests
def test_intake_journey(env, t, width, height):
    inst = env.fix["all_types"]
    byid = {q["id"]: q for q in inst["questions"]}
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    t.has(text_of(pg, "#main"), "16 questions in 3 sections", "intro states the length")
    pg.click("#btn-start")
    t.eq(cur_q(pg), "purpose", "first question")
    t.has(text_of(pg, "#progress-text"), "1 of 12", "progress on the first question")
    set_answer(pg, byid["purpose"], "Books")
    pg.fill("#note-purpose", NOTE1)
    env.shot(pg, "intake-question-%d" % width)
    pg.click("#btn-next")
    set_answer(pg, byid["rooms"], ["Kitchen", "Somewhere else"])
    pg.click("#btn-next")
    t.eq(cur_q(pg), "other-room", "the conditional question appears after its trigger")
    pg.fill("#in-other-room", "Garage")
    pg.click("#btn-back")
    pg.click("#btn-back")
    t.eq(cur_q(pg), "purpose", "Back twice returns to the first question")
    t.ok(pg.is_checked("#in-purpose-0"), "the first answer is still selected after Back")
    t.eq(pg.input_value("#note-purpose"), NOTE1, "the note is still there after Back")
    set_answer(pg, byid["purpose"], "Plants")
    pg.click("#btn-next")
    pg.click("#btn-next")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "width", "reached the required question")
    t.ok(pg.locator("#btn-skip").count() == 0, "a required question offers no Skip")
    pg.click("#btn-next")
    t.has(text_of(pg, "#qe-width"), "needs an answer", "required question refuses an empty Next")
    pg.fill("#in-width", "abc")
    pg.click("#btn-next")
    t.has(text_of(pg, "#qe-width"), "digits only", "text in a number field is refused")
    t.eq(pg.get_attribute("#in-width", "aria-invalid"), "true", "the field is marked invalid")
    pg.fill("#in-width", "401")
    pg.click("#btn-next")
    t.has(text_of(pg, "#qe-width"), "largest value accepted is 400", "401 is refused where 400 is the limit")
    t.eq(cur_q(pg), "width", "a refused number keeps the reader on the question")
    env.shot(pg, "intake-number-error-%d" % width)
    pg.fill("#in-width", "400")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "load", "400 is accepted where 400 is the limit")
    pg.click("#btn-back")
    pg.fill("#in-width", "120")
    pg.click("#btn-next")
    pg.click("#btn-skip")
    t.eq(cur_q(pg), "sturdy", "Skip moves on")
    set_answer(pg, byid["sturdy"], 4)
    pg.click("#btn-next")
    set_answer(pg, byid["finish"], 3)
    pg.click("#btn-next")
    set_answer(pg, byid["urgency"], 9)
    pg.click("#btn-next")
    set_answer(pg, byid["budget"], 300)
    t.has(text_of(pg, "#val-budget"), "Chosen: 300", "the slider reports its value in words")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "why-rush", "a question shown by an exact scale value appears")
    pg.fill("#in-why-rush", WHY)
    pg.click("#btn-next")
    pg.click("#btn-next")
    t.has(text_of(pg, "#qe-order"), "Use this order", "an untouched ranking is not taken as an answer")
    set_answer(pg, byid["order"], ["Strength", "Cost", "Speed of delivery", "Looks"])
    pg.click("#btn-next")
    set_answer(pg, byid["wall"], "No")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "power", "the question hidden by the answer No is passed over")
    set_answer(pg, byid["power"], "Yes")
    pg.click("#btn-next")
    pg.click("#btn-skip")
    t.eq(stage(pg), "review", "after the last question comes the review screen")
    t.has(text_of(pg, "[data-rv='load']"), "Skipped", "the review screen shows the skipped question")
    t.has(text_of(pg, "#review-counts"), "14 shown: 12 answered, 2 skipped, 0 with no answer", "review counts")
    env.shot(pg, "intake-review-%d" % width)
    pg.click("#edit-sturdy")
    t.eq(cur_q(pg), "sturdy", "Change on the review screen opens that question")
    t.eq(text_of(pg, "#btn-next"), "Back to review", "the main button returns to review")
    set_answer(pg, byid["sturdy"], 2)
    pg.click("#btn-next")
    t.eq(stage(pg), "review", "back on the review screen")
    t.has(text_of(pg, "[data-rv='sturdy']"), "2 of 5, Disagree", "the review screen shows the edited answer")
    export = finish(pg)
    env.shot(pg, "intake-finished-%d" % width)
    saved = json.loads(resume_code(pg))
    for q in visible(inst, saved["data"]["answers"]):
        t.has(export, "### [%s] " % q["id"], "export holds question id")
    for hidden in ("wall-type", "follow-up"):
        t.ok("[%s]" % hidden not in export, "the hidden question %s is absent from the export" % hidden)
    block = export.split("### [purpose]")[1].split("###")[0]
    t.has(block, "Answer: Plants", "export holds the changed answer")
    t.ok("Books" not in block, "export does not hold the first answer that was replaced")
    t.has(block, "Note:\n> " + NOTE1, "export holds the note word for word")
    t.has(export.split("### [load]")[1].split("###")[0], "Answer: (skipped)", "export marks the skipped question")
    t.has(export.split("### [sturdy]")[1].split("###")[0], "Answer: 2 of 5, Disagree", "export holds the answer edited from review")
    t.has(export, "Questions shown: 14. Answered: 12. Skipped: 2. No answer: 0. Hidden by earlier answers: 2.", "export header counts")
    parsed = parse_text(export)
    t.eq(parsed.get("errors"), [], "parse_export reads the export without errors")
    for d in diff_record(parsed, expected_record(inst, saved)):
        t.ok(False, "round trip: " + d)
    why = [q for q in parsed.get("questions", []) if q["id"] == "why-rush"]
    t.eq(why[0]["answer"] if why else None, WHY, "a long answer with a blank line and an indent comes back exactly")
    ctx.close()


def quick_finish(env, ctx, inst, scope_kind="tab"):
    name = env.put(inst)
    if scope_kind == "frame":
        pg, s = env.framed(ctx, name)
    else:
        pg = env.page(ctx, name)
        s = pg
    walk(s, inst, auto_plan(inst))
    return pg, s, finish(s)


def box_state(s):
    return s.evaluate("""() => { const b = document.getElementById('export-text');
        return {len: b.value.length, start: b.selectionStart, end: b.selectionEnd, focused: document.activeElement === b, disabled: b.disabled, readonly: b.readOnly}; }""")


def test_clipboard_refused(env, t, width, height):
    inst = env.fix["all_types"]
    blocked = "Copying is blocked here. The complete text is in the box and is selected"
    # 1. clipboard and the older copy command both refuse
    ctx = env.context(width, height, init=CLIPBOARD_REFUSED)
    pg, s, export = quick_finish(env, ctx, inst)
    s.click("#copy-export")
    s.wait_for_function("() => document.getElementById('copy-status').textContent.length > 0")
    t.has(text_of(s, "#copy-status"), blocked, "refused copy is reported in the page")
    st = box_state(s)
    t.ok(st["focused"] and st["start"] == 0 and st["end"] == st["len"] == len(export), "after a refused copy the whole export is selected in the box (%r)" % st)
    t.ok(not st["disabled"] and st["readonly"], "the box can be selected and cannot be edited by accident")
    t.has(export, "End of export: ", "the box holds the export down to its last line")
    t.eq(parse_text(export).get("errors"), [], "the text in the box is a complete, readable export")
    t.eq(text_of(s, "#copy-export"), "Copy the export", "the copy button returns to its label")
    env.shot(pg, "clipboard-refused-%d" % width)
    ctx.close()
    # 2. the same page inside a sandboxed frame, with nothing stubbed
    ctx = env.context(width, height, permissions=["clipboard-read", "clipboard-write"])
    pg, s, export = quick_finish(env, ctx, inst, "frame")
    pg.evaluate("() => navigator.clipboard.writeText('before the copy')")
    s.click("#copy-export")
    s.wait_for_function("() => document.getElementById('copy-status').textContent.length > 0")
    said = text_of(s, "#copy-status")
    t.ok(said.startswith("Copied.") or blocked in said, "in the frame the page reports the copy one way or the other (%r)" % said)
    held = pg.evaluate("() => navigator.clipboard.readText()")
    if said.startswith("Copied."):
        t.eq(held, export, "in the frame, when the page says Copied the clipboard really holds the whole export")
    else:
        t.eq(held, "before the copy", "in the frame, when the page says the copy was blocked the clipboard is unchanged")
    t.note("sandboxed frame, nothing stubbed, %dpx: the page said %r" % (width, said[:60]))
    t.eq(parse_text(s.input_value("#export-text")).get("errors"), [], "in the frame the box holds a complete, readable export")
    t.eq(len(s.input_value("#export-text")), len(export), "in the frame the box is not shortened")
    t.has(text_of(s, "#save-banner"), "Not saved", "in the frame the page says it is not saving")
    s.click("#download-export")
    t.has(text_of(s, "#copy-status"), "copy the text from the box instead", "a download that may not arrive points back to the box")
    ctx.close()
    # 3. with clipboard permission the copy is real
    ctx = env.context(width, height, permissions=["clipboard-read", "clipboard-write"])
    pg, s, export = quick_finish(env, ctx, inst)
    s.click("#copy-export")
    s.wait_for_function("() => document.getElementById('copy-status').textContent.length > 0")
    t.has(text_of(s, "#copy-status"), "Copied. Paste it into the chat.", "an allowed copy is confirmed")
    t.eq(s.evaluate("() => navigator.clipboard.readText()"), export, "the clipboard holds the whole export")
    ctx.close()


def test_reload_resume(env, t, width, height):
    inst = env.fix["all_types"]
    byid = {q["id"]: q for q in inst["questions"]}
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    t.has(text_of(pg, "#main"), "Saved in this browser.", "the first screen says where answers are kept")
    pg.click("#btn-start")
    set_answer(pg, byid["purpose"], "Tools")
    pg.fill("#note-purpose", NOTE1)
    pg.click("#btn-next")
    set_answer(pg, byid["rooms"], ["Hallway", "Workshop"])
    pg.click("#btn-next")
    pg.fill("#in-width", "88.5")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "load", "on the fourth question before the reload")
    pg.fill("#in-load", "12")
    pg.wait_for_timeout(250)
    before = answers_of(resume_code(pg))
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq(cur_q(pg), "load", "after a reload the page is on the same question")
    t.eq(pg.input_value("#in-load"), "12", "the half-finished answer on that question survives the reload")
    t.has(text_of(pg, "#status"), "Picked up where you left off", "the page says it resumed")
    t.eq(answers_of(resume_code(pg)), before, "every answer and note survives the reload")
    pg.click("#btn-back")
    t.eq(pg.input_value("#in-width"), "88.5", "an earlier answer is shown again after the reload")
    pg.click("#btn-back")
    pg.click("#btn-back")
    t.ok(pg.is_checked("#in-purpose-1"), "the first answer is still selected after the reload")
    t.eq(pg.input_value("#note-purpose"), NOTE1, "the note survives the reload")
    ctx.close()


def test_storage_throwing(env, t, width, height):
    inst = env.fix["all_types"]
    byid = {q["id"]: q for q in inst["questions"]}
    name = env.put(inst)
    for kind in ("tab with storage that throws", "sandboxed frame"):
        ctx = env.context(width, height, init=THROWING_STORAGE if kind.startswith("tab") else None)
        if kind.startswith("tab"):
            pg = env.page(ctx, name)
            s = pg
            t.ok(pg.evaluate("() => { try { window.localStorage.getItem('x'); return false; } catch (e) { return true; } }"), "the stub makes storage throw")
        else:
            pg, s = env.framed(ctx, name)
            t.ok(s.evaluate("() => { try { window.localStorage.getItem('x'); return false; } catch (e) { return true; } }"), "storage really throws inside the frame")
        t.has(text_of(s, "#save-banner"), "Not saved: this page cannot store data here. Get a resume code to keep your work.", kind + ": the page says it is not saving")
        t.ok(not is_hidden(s, "#save-banner"), kind + ": the not-saved note is visible")
        s.click("#btn-start")
        set_answer(s, byid["purpose"], "Mixed use")
        s.fill("#note-purpose", NOTE1)
        s.click("#btn-next")
        set_answer(s, byid["rooms"], ["Bedroom"])
        s.click("#btn-next")
        s.fill("#in-width", "64")
        s.click("#btn-next")
        t.eq(cur_q(s), "load", kind + ": the page works without storage")
        code = resume_code(s)
        if kind.startswith("tab"):
            env.shot(pg, "not-saved-%d" % width)
        pg.reload()
        pg.wait_for_selector(READY if kind.startswith("tab") else "#f")
        s = pg if kind.startswith("tab") else pg.frame(name="f")
        s.wait_for_selector(READY)
        t.eq(stage(s), "start", kind + ": with no storage a reload starts again, as the page warned")
        ctx.close()
        ctx = env.context(width, height, init=THROWING_STORAGE if kind.startswith("tab") else None)
        if kind.startswith("tab"):
            pg = env.page(ctx, name)
            s = pg
        else:
            pg, s = env.framed(ctx, name)
        do_import(s, code)
        s.wait_for_selector("#main article.q")
        t.eq(cur_q(s), "load", kind + ": the resume code returns a fresh load to the same question")
        t.has(text_of(s, "#status"), "Loaded the resume code: 3 questions restored.", kind + ": the page says what it loaded")
        t.eq(answers_of(resume_code(s)), answers_of(code), kind + ": the resume code restores every answer and note")
        ctx.close()
    # a host storage object is used before localStorage
    ctx = env.context(width, height, init=HOST_STORAGE)
    pg = env.page(ctx, name)
    pg.click("#btn-start")
    set_answer(pg, byid["purpose"], "Books")
    pg.click("#btn-next")
    pg.wait_for_timeout(250)
    t.has(text_of(pg, "#foot"), "Saved by the app that is showing this page.", "a host storage object is named as the place answers are kept")
    t.ok(pg.evaluate("() => sessionStorage.getItem('host:elicitor:state:fixture-all-types') !== null && localStorage.getItem('elicitor:state:fixture-all-types') === null"),
         "with a host storage object the state goes there and not to localStorage")
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq(cur_q(pg), "rooms", "state kept by a host storage object resumes after a reload")
    ctx.close()
    # a host storage object that is slow: the page shows that it is looking, then opens
    ctx = env.context(width, height, init=SLOW_HOST_STORAGE)
    pg = ctx.new_page()
    pg.goto(ORIGIN + "/" + name, wait_until="commit")
    pg.wait_for_selector("#loading")
    t.has(text_of(pg, "#main"), "Looking for saved answers.", "while storage is being read the page says so")
    t.eq(pg.get_attribute("#main", "aria-busy"), "true", "the loading state is marked busy")
    t.ok(pg.locator("#btn-start").count() == 0, "nothing can be started while saved answers are being looked for")
    pg.wait_for_selector(READY)
    t.eq(stage(pg), "start", "the page opens once storage has answered")
    ctx.close()
    # a host storage object that never answers is given up on, and the page still opens
    ctx = env.context(width, height, init=SILENT_HOST_STORAGE)
    pg = ctx.new_page()
    pg.goto(ORIGIN + "/" + name, wait_until="commit")
    pg.wait_for_selector(READY, timeout=4000)
    t.has(text_of(pg, "#main"), "Saved in this browser.", "a host storage object that never answers is passed over for the browser's own storage")
    ctx.close()


def test_import_refusals(env, t, width, height):
    inst = env.fix["all_types"]
    byid = {q["id"]: q for q in inst["questions"]}
    ctx = env.context(width, height)
    name = env.put(inst)
    pg = env.page(ctx, name)
    pg.click("#btn-start")
    set_answer(pg, byid["purpose"], "Tools")
    pg.fill("#note-purpose", "keep me")
    pg.click("#btn-next")
    set_answer(pg, byid["rooms"], ["Kitchen"])
    pg.click("#btn-next")
    good_text = resume_code(pg)
    good = json.loads(good_text)
    before = good["data"]

    def variant(**kw):
        e = copy.deepcopy(good)
        e["data"]["answers"] = {"purpose": {"v": "Books"}, "width": {"v": 77}}
        e["data"]["cur"] = "width"
        e.update(kw)
        return json.dumps(e)

    other_export = "# Other\n\nInstrument: some-other-form, version 1, intake mode\nFinished: 2026-10-09T03:12:45Z\nQuestions shown: 0. Answered: 0. Skipped: 0. No answer: 0. Hidden by earlier answers: 0.\n\nEnd of export: 0 questions.\n"
    cases = [
        ("wrong questionnaire id", variant(content_id="some-other-form@1"), "different questionnaire"),
        ("wrong app", variant(app="stockcount"), "different app"),
        ("newer schema (2, where 1 is the newest read)", variant(schema=2), "newer copy of this page (schema 2)"),
        ("schema that is not a whole number", variant(schema=1.5), "no usable schema number"),
        ("schema written as text", variant(schema="1"), "no usable schema number"),
        ("schema 0, with no migration", variant(schema=0), "no usable schema number"),
        ("malformed: cut short", variant()[:-40], "not complete JSON"),
        ("malformed: not JSON at all", "these are just some words", "not complete JSON"),
        ("empty paste", "", "Nothing was pasted or chosen"),
        ("spaces and line breaks only", "  \n\n  ", "Nothing was pasted or chosen"),
        ("no content id", variant(content_id=None), "does not say which questionnaire"),
        ("answers that do not fit the questions", variant(data={"stage": "q", "cur": "width", "answers": {"purpose": {"v": "Bricks"}}}), "does not fit this questionnaire"),
        ("an export from another questionnaire", other_export, "different questionnaire"),
        ("a cut-off finished export", "# x\n\nInstrument: fixture-all-types, version 1, intake mode\n\n### [purpose] What?\nType: single\nAnswer: Books\n", "cut short"),
    ]
    for label, text, reason in cases:
        do_import(pg, text)
        msg = text_of(pg, "#import-msg")
        t.has(msg, reason, "refused (%s)" % label)
        t.has(msg, "Nothing was changed", "refusal says nothing was changed (%s)" % label)
        if label == "newer schema (2, where 1 is the newest read)":
            env.shot(pg, "import-refused-%d" % width)
        now = json.loads(resume_code(pg))["data"]
        t.eq(now, before, "current answers and position are untouched after a refused import (%s)" % label)
    # a different version of the same questionnaire: asked first, and keeping is the default
    do_import(pg, variant(content_id="fixture-all-types@7"))
    t.ok(not is_hidden(pg, "#import-confirm"), "a code from another version asks before loading")
    t.has(text_of(pg, "#import-confirm-text"), "version 7 of the questionnaire, and this page is version 1", "the question says exactly what differs")
    t.eq(pg.evaluate("() => document.activeElement.id"), "import-keep", "keeping the current answers has the focus")
    pg.click("#import-keep")
    t.eq(json.loads(resume_code(pg))["data"], before, "choosing to keep leaves the answers untouched")
    do_import(pg, variant(content_id="fixture-all-types@7"))
    pg.click("#import-continue")
    pg.wait_for_selector("#main article.q")
    t.eq(answers_of(resume_code(pg)), {"purpose": {"v": "Books"}, "width": {"v": 77}}, "choosing to load replaces the answers with the matching ones")
    pg.click("#undo")
    t.eq(json.loads(resume_code(pg))["data"], before, "Undo after a load brings the earlier answers back")
    # the valid neighbour: schema 1, this questionnaire, this version
    do_import(pg, variant())
    pg.wait_for_selector("#main article.q")
    t.eq(cur_q(pg), "width", "a valid code loads and opens at its question")
    t.eq(answers_of(resume_code(pg)), {"purpose": {"v": "Books"}, "width": {"v": 77}}, "a valid code replaces the answers")
    # a saved file works the same as a paste
    open_panel(pg)
    if pg.evaluate("() => document.getElementById('import-box').hidden"):
        pg.click("#import-open")
    pg.set_input_files("#import-file", files=[{"name": "resume.json", "mimeType": "application/json", "buffer": good_text.encode("utf-8")}])
    pg.wait_for_function("() => document.getElementById('panel').hidden")
    t.eq(json.loads(resume_code(pg))["data"]["answers"], before["answers"], "a chosen file loads the same way as pasted text")
    ctx.close()


QUIZ_PLAN = {
    "minutes-in-day": {"v": "1,440"},                 # correct
    "metres-in-km": {"v": "250"},                     # wrong
    "leap-february": {"skip": True},
    "even-numbers": {"v": ["14", "36"]},              # correct: the exact set
    "multiples-of-three": {"v": ["12", "27"]},        # wrong: one correct option left out
    "hours-in-week": {"skip": True},
}


def check_quiz_result(env, t, s, inst, label):
    byid = {q["id"]: q for q in inst["questions"]}
    t.eq(one_line(text_of(s, "#score-main")), "2 correct of 4 attempted", label + ": correct out of attempted")
    score = facts(s, "#score")
    t.eq(score.get("Out of all items"), "2 of 6", label + ": correct out of total")
    t.eq(score.get("Skipped"), "2 (not counted as wrong)", label + ": skipped counted separately")
    t.eq(score.get("Not answered"), "0", label + ": not answered counted separately")
    t.has(score.get("Scoring rule"), "One mark per item.", label + ": the rule is shown with the score")
    t.eq(text_of(s, "#missed-h"), "Missed: 2", label + ": two missed items")
    missed = s.evaluate("() => Array.from(document.querySelectorAll('#missed-list > li')).map(n => n.getAttribute('data-missed'))")
    t.eq(missed, ["metres-in-km", "multiples-of-three"], label + ": the missed list holds the wrong answers and not the skipped ones")
    for qid in missed:
        body = text_of(s, "#missed-list [data-missed='%s']" % qid)
        for o in byid[qid]["options"]:
            t.has(body, o["explain"], label + ": the explanation of every option is shown for missed item " + qid)
    t.eq(s.evaluate("() => Array.from(document.querySelectorAll('#passed-list > li')).map(n => n.getAttribute('data-missed'))"), ["leap-february", "hours-in-week"], label + ": skipped items are listed apart")
    export = s.input_value("#export-text")
    for line in ("Correct: 2", "Attempted: 4", "Total: 6", "Skipped: 2", "No answer: 0"):
        t.has(export, "\n" + line + "\n", label + ": score line in the export")
    parsed = parse_text(export)
    t.eq(parsed.get("errors"), [], label + ": parse_export reads the quiz export")
    for d in diff_record(parsed, expected_record(inst, json.loads(resume_code(s)))):
        t.ok(False, label + ": round trip: " + d)


def test_quiz_scoring(env, t, width, height):
    inst = env.fix["quiz"]
    byid = {q["id"]: q for q in inst["questions"]}
    # marked after each item
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    intro = text_of(pg, "#main")
    t.has(intro, "One mark per item.", "the scoring rule is printed on the first screen")
    t.has(intro, "Skipped items earn no mark and are reported separately", "the rule says how skipped items are treated")
    t.eq(pg.get_attribute("#fb-immediate", "aria-pressed"), "true", "marking after each item is shown as selected")
    pg.click("#btn-start")
    t.eq(text_of(pg, "#btn-next"), "Check answer", "the main button checks the answer first")
    set_answer(pg, byid["minutes-in-day"], "1,440")
    t.ok(pg.locator(".fb").count() == 0, "no marking is shown before the answer is checked")
    pg.click("#btn-next")
    t.has(text_of(pg, "#fb-minutes-in-day"), "Correct.", "a right answer is marked correct")
    for o in byid["minutes-in-day"]["options"]:
        t.has(text_of(pg, "#fb-minutes-in-day"), o["explain"], "feedback explains every option")
    t.eq(pg.evaluate("() => document.activeElement.id"), "fb-minutes-in-day", "focus moves to the feedback")
    pg.click("label[for='in-minutes-in-day-1']", force=True)     # a tap on a locked option; Playwright itself treats aria-disabled as not clickable
    t.ok(pg.is_checked("#in-minutes-in-day-0") and not pg.is_checked("#in-minutes-in-day-1"), "a checked item cannot be changed")
    t.ok(pg.locator("#btn-skip").count() == 0, "a checked item cannot be skipped")
    pg.click("#btn-next")
    set_answer(pg, byid["metres-in-km"], "250")
    pg.click("#btn-next")
    fb = text_of(pg, "#fb-metres-in-km")
    t.has(fb, "Not correct.", "a wrong answer is marked not correct")
    t.has(fb, "Your answer250", "the chosen option is labelled in words")
    t.has(fb, "Correct answer2,500", "the correct option is labelled in words")
    env.shot(pg, "quiz-feedback-%d" % width)
    pg.click("#btn-next")
    walk(pg, inst, QUIZ_PLAN, start=False)
    pg.click("#edit-hours-in-week")
    t.eq(text_of(pg, "#btn-next"), "Check answer", "an item opened from review is checked before returning")
    t.ok(pg.locator("#btn-back").count() == 0, "an item opened from review has no Back, only the way back to review")
    pg.click("#btn-skip")
    t.eq(stage(pg), "review", "skipping it again returns to review")
    finish(pg)
    check_quiz_result(env, t, pg, inst, "marked after each item")
    env.shot(pg, "quiz-result-%d" % width)
    ctx.close()
    # marked at the end, set in the data block
    late = copy.deepcopy(inst)
    late["feedback"] = "at_end"
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(late))
    t.eq(pg.get_attribute("#fb-at_end", "aria-pressed"), "true", "marking at the end is shown as selected when the data block sets it")
    pg.click("#btn-start")
    t.eq(text_of(pg, "#btn-next"), "Next", "with marking at the end the main button is Next")
    set_answer(pg, byid["minutes-in-day"], "3,600")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "metres-in-km", "with marking at the end, Next moves straight on")
    pg.click("#btn-back")
    t.ok(pg.locator(".fb").count() == 0, "no marking is shown before the end")
    set_answer(pg, byid["minutes-in-day"], "1,440")
    pg.click("#btn-next")
    walk(pg, late, {k: v for k, v in QUIZ_PLAN.items()}, start=False)
    t.ok("Marked:" not in text_of(pg, "#main"), "the review screen shows no marking before the end")
    finish(pg)
    check_quiz_result(env, t, pg, late, "marked at the end")
    ctx.close()
    # marked at the end, chosen on the first screen
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    pg.click("#fb-at_end")
    t.eq(pg.get_attribute("#fb-at_end", "aria-pressed"), "true", "the reader can choose marking at the end")
    walk(pg, inst, QUIZ_PLAN)
    t.ok(pg.locator(".fb").count() == 0, "choosing marking at the end shows no marking on the way")
    finish(pg)
    check_quiz_result(env, t, pg, inst, "marked at the end by the reader's choice")
    # everything skipped: nothing attempted, nothing correct
    pg.click("#start-again")
    pg.click("#reset-go")
    walk(pg, inst, {})
    finish(pg)
    t.eq(one_line(text_of(pg, "#score-main")), "0 correct of 0 attempted", "all skipped: none correct of none attempted")
    t.eq(facts(pg, "#score").get("Skipped"), "6 (not counted as wrong)", "all skipped: six skipped")
    t.eq(facts(pg, "#score").get("Out of all items"), "0 of 6", "all skipped: none correct of six")
    t.eq(text_of(pg, "#missed-h"), "Missed: 0", "all skipped: nothing is listed as missed")
    # the exact-match boundary of a select-all item: every correct option plus one more is not correct, the exact set is
    pg.click("#start-again")
    pg.click("#reset-go")
    walk(pg, inst, {"even-numbers": {"v": ["14", "36", "49"]}, "multiples-of-three": {"v": ["12", "27", "33"]}})
    finish(pg)
    t.eq(one_line(text_of(pg, "#score-main")), "1 correct of 2 attempted", "select-all: every correct option plus a wrong one earns no mark, and the exact set earns one")
    t.eq(pg.evaluate("() => Array.from(document.querySelectorAll('#missed-list > li')).map(n => n.getAttribute('data-missed'))"), ["even-numbers"],
         "select-all: the answer with one option too many is the one listed as missed")
    t.eq(facts(pg, "#score").get("Skipped"), "4 (not counted as wrong)", "select-all boundary: the other four are skipped")
    ctx.close()


def test_show_if(env, t, width, height):
    inst = env.fix["all_types"]
    byid = {q["id"]: q for q in inst["questions"]}
    plan = auto_plan(inst)
    plan.update({"wall": {"v": "No"}, "rooms": {"v": ["Kitchen"]}, "urgency": {"v": 3}, "anything": {"skip": True}})
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    walk(pg, inst, plan)
    export = finish(pg)
    t.ok("[wall-type]" not in export, "a question hidden by an answer is absent from the export")
    t.has(export, "Hidden by earlier answers: 4.", "the export counts the hidden questions")
    t.has(export, "End of export: 12 questions.", "the export counts only the questions shown")
    pg.click("#change-answers")
    t.ok(pg.locator("[data-rv='wall-type']").count() == 0, "the hidden question is not on the review screen")
    pg.click("#edit-wall")
    set_answer(pg, byid["wall"], "Yes")
    pg.click("#btn-next")
    t.has(text_of(pg, "[data-rv='wall-type']"), "No answer", "changing the controlling answer brings the question back, unanswered")
    pg.click("#edit-wall-type")
    set_answer(pg, byid["wall-type"], "Timber")
    pg.click("#btn-next")
    export = finish(pg)
    t.has(export.split("### [wall-type]")[1].split("###")[0] if "### [wall-type]" in export else "", "Answer: Timber", "the question that came back is in the export with its answer")
    t.has(export, "End of export: 13 questions.", "the count of questions rises by one")
    # in the normal flow the question now sits between its neighbours
    pg.click("#change-answers")
    pg.click("#edit-wall")
    set_answer(pg, byid["wall"], "Not sure")
    pg.click("#btn-next")
    export = finish(pg)
    t.ok("[wall-type]" not in export, "hiding the question again removes it from the export although it was answered")
    pg.click("#change-answers")
    pg.click("#edit-wall")
    set_answer(pg, byid["wall"], "Yes")
    pg.click("#btn-next")
    t.has(text_of(pg, "[data-rv='wall-type']"), "Timber", "showing it again brings back the answer given before")
    ctx.close()
    # a chain: a question that depends on a hidden question stays hidden
    chain = {"id": "fixture-chain", "version": 1, "mode": "intake", "title": "Chain (SYNTHETIC)", "questions": [
        {"id": "first", "type": "single", "text": "First?", "options": ["Yes", "No"]},
        {"id": "second", "type": "single", "text": "Second?", "options": ["Yes", "No"], "show_if": {"q": "first", "equals": "Yes"}},
        {"id": "third", "type": "text", "text": "Third?", "show_if": {"q": "second", "equals": "Yes"}},
        {"id": "fourth", "type": "text", "text": "Fourth?", "show_if": {"q": "first", "answered": False}}]}
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(chain))
    pg.click("#btn-start")
    t.eq(one_line(text_of(pg, "#progress-text")), "1 of 2", "progress counts only the questions that apply: two of the four before any answer")
    set_answer(pg, chain["questions"][0], "Yes")
    pg.click("#btn-next")
    t.eq(one_line(text_of(pg, "#progress-text")), "2 of 2", "progress follows the answers: the second of two once the first answer hides one question and opens another")
    set_answer(pg, chain["questions"][1], "Yes")
    pg.click("#btn-next")
    pg.fill("#in-third", "deep")
    pg.click("#btn-next")
    t.eq(stage(pg), "review", "three questions shown in the chain")
    pg.click("#edit-first")
    set_answer(pg, chain["questions"][0], "No")
    pg.click("#btn-next")
    export = finish(pg)
    t.ok("[second]" not in export and "[third]" not in export, "hiding the first link hides the whole chain")
    t.has(export, "End of export: 1 question.", "only the first question is exported")
    ctx.close()


def long_instrument(n):
    kinds = ["single", "multi", "likert", "scale", "number", "text", "rank"]
    qs = []
    for i in range(n):
        k = kinds[i % len(kinds)]
        q = {"id": "item-%03d-%s" % (i + 1, k), "section": "part-%d" % (i // 30 + 1), "type": k, "text": "Synthetic question %d of %d, of type %s, with enough words to wrap on a narrow screen?" % (i + 1, n, k)}
        if k in ("single", "multi", "rank"):
            q["options"] = ["Option %s for item %d" % (c, i + 1) for c in "ABCDE"]
        if k == "likert":
            q["labels"] = ["Strongly disagree", "Disagree", "Neither", "Agree", "Strongly agree"]
        if k == "scale":
            q.update({"min": 0, "max": 10, "min_label": "Low", "max_label": "High"})
        if k == "number":
            q.update({"min": 0, "max": 1000, "unit": "units"})
        qs.append(q)
    return {"id": "fixture-long-%d" % n, "version": 1, "mode": "intake", "title": "Long fixture: %d questions (SYNTHETIC)" % n,
            "sections": [{"id": "part-%d" % (j + 1), "title": "Part %d" % (j + 1)} for j in range((n + 29) // 30)], "questions": qs}


def test_long_instrument(env, t, width, height):
    inst = long_instrument(120)
    ctx = env.context(width, height)
    t0 = time.time()
    pg = env.page(ctx, env.put(inst))
    load_ms = (time.time() - t0) * 1000
    pg.click("#btn-start")
    times = []
    for _ in range(119):
        times.append(pg.evaluate("() => { const b = document.getElementById('btn-skip'); const t0 = performance.now(); b.click(); return performance.now() - t0; }"))
    med, worst = statistics.median(times), max(times)
    high = sorted(times)[int(len(times) * 0.95)]          # one stalled draw on a busy machine is reported, not failed on
    frame = pg.evaluate("""() => new Promise(res => { const b = document.getElementById('btn-back'); const t0 = performance.now(); b.click();
        requestAnimationFrame(() => requestAnimationFrame(() => res(performance.now() - t0))); })""")
    t.note("120 questions at %dpx: drawing the next question took a median of %.1f ms, %.1f ms at the 95th percentile and at most %.1f ms over %d moves; a move through to the next painted frame took %.0f ms; load to first screen took %.0f ms by the test's clock"
           % (width, med, high, worst, len(times), frame, load_ms))
    t.ok(med < 30, "median time to draw a question is under 30 ms with 120 questions (was %.1f ms)" % med)
    t.ok(high < 100, "95 in 100 draws of a question take under 100 ms with 120 questions (the 95th percentile was %.1f ms)" % high)
    t.ok(worst < 1000, "no draw of a question takes a second with 120 questions (the slowest was %.1f ms)" % worst)
    t.eq(cur_q(pg), inst["questions"][118]["id"], "Back from the last of 120 questions lands on the one before")
    ctx.close()
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    t0 = time.time()
    walk(pg, inst, auto_plan(inst))
    per_q = (time.time() - t0) * 1000 / 120
    t0 = time.time()
    export = finish(pg)
    t.note("120 questions answered through the page at %.0f ms each including the test driver; finishing and drawing the export took %.0f ms" % (per_q, (time.time() - t0) * 1000))
    parsed = parse_text(export)
    t.eq(parsed.get("errors"), [], "the export of 120 questions parses")
    t.eq(len(parsed.get("questions", [])), 120, "the export of 120 questions holds 120 blocks")
    for d in diff_record(parsed, expected_record(inst, json.loads(resume_code(pg))))[:5]:
        t.ok(False, "120-question round trip: " + d)
    ctx.close()
    # state with hundreds of items: a resume code made by hand for 400 questions, loaded into a fresh page
    big = long_instrument(400)
    answers, big_plan = {}, auto_plan(big)
    for q in big["questions"]:
        step = big_plan[q["id"]]
        if "v" in step:
            answers[q["id"]] = {"v": step["v"]}
            if note_on(big, q):
                answers[q["id"]]["note"] = "A note of ordinary length for %s, long enough to be realistic." % q["id"]
        else:
            answers[q["id"]] = {"skipped": True}
    code = json.dumps({"app": "elicitor", "schema": 1, "content_id": "fixture-long-400@1", "saved_at": "2026-10-09T00:00:00Z",
                       "data": {"stage": "review", "cur": None, "feedback": "immediate", "agreed": False, "finished_at": None, "answers": answers}})
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(big))
    t0 = time.time()
    do_import(pg, code)
    pg.wait_for_selector("#btn-finish")
    t.note("400 questions: a %d-byte resume code holding %d answers loaded and the review screen drew in %.0f ms by the test's clock" % (len(code), len(answers), (time.time() - t0) * 1000))
    back = resume_code(pg)
    t.eq(answers_of(back), answers, "a 400-question state comes back out exactly as it went in")
    pg.reload()
    pg.wait_for_selector("#btn-finish")
    t.eq(answers_of(resume_code(pg)), answers, "a 400-question state survives a reload from storage")
    ctx.close()


def round_trip(env, t, inst, label, width, height):
    """Fill, finish, export; parse; compare with the saved state; then load the export into a fresh page."""
    plan = auto_plan(inst)
    ctx = env.context(width, height)
    name = env.put(inst)
    pg = env.page(ctx, name)
    walk(pg, inst, plan)
    export = finish(pg)
    saved = json.loads(resume_code(pg))
    ctx.close()
    parsed = parse_text(export)
    t.eq(parsed.get("errors"), [], label + ": parse_export reports no errors")
    if inst["mode"] == "survey":
        t.eq(parsed.get("format"), "elicitor-response-1", label + ": the survey export is a response block")
        t.eq(parsed.get("instrument"), {"id": inst["id"], "version": inst["version"]}, label + ": the block names its instrument and version")
        t.eq(parsed.get("questions"), expected_response(inst, saved), label + ": every answer, note and marker comes back exactly")
        t.eq([{k: x[k] for k in ("id", "count", "of")} for x in expected_tallies(inst, saved["data"]["answers"])], parsed.get("tallies"), label + ": tallies come back exactly")
    else:
        for d in diff_record(parsed, expected_record(inst, saved)):
            t.ok(False, label + ": " + d)
    types = {q["type"] for q in visible(inst, saved["data"]["answers"]) if status_of(q, saved["data"]["answers"]) == "answered"}
    stored = STORED.get(inst["id"])
    if stored is not None and env.write_fixtures:
        (HERE / "fixtures" / stored).write_text(export, encoding="utf-8")
        t.note("wrote fixtures/" + stored)
    elif stored is not None:
        path = HERE / "fixtures" / stored
        no_time = lambda x: "\n".join(ln for ln in x.split("\n") if not ln.lower().startswith("finished: "))  # noqa: E731
        t.ok(path.is_file() and no_time(path.read_text(encoding="utf-8")) == no_time(export),
             label + ": the stored export fixtures/%s is what the engine produces now, apart from the time (if the format was changed on purpose, run --write-fixtures)" % stored)
    # the finished export goes back into a fresh page
    ctx = env.context(width, height)
    pg = env.page(ctx, name)
    do_import(pg, export)
    pg.wait_for_selector("#btn-finish, #export-text")
    again = json.loads(resume_code(pg))

    def plain(answers):
        shown = {q["id"] for q in visible(inst, answers)}
        out = {}
        for q in inst["questions"]:
            a = answers.get(q["id"], {})
            if q["id"] not in shown or not a:
                continue
            e = {}
            if valid(q, a.get("v")):
                e["v"] = canon(a["v"]) if q["type"] == "text" else a["v"]
            elif a.get("skipped"):
                e["skipped"] = True
            if note_on(inst, q) and a.get("note") and canon(a["note"]):
                e["note"] = canon(a["note"])
            if e:
                out[q["id"]] = e
        return out

    t.eq(plain(again["data"]["answers"]), plain(saved["data"]["answers"]), label + ": loading the finished export into a fresh page restores every answer, note and skip")
    if again["data"]["stage"] != "done":
        export2 = finish(pg)
    else:
        export2 = pg.input_value("#export-text")
    strip = lambda x: "\n".join(ln for ln in x.split("\n") if not ln.startswith(("Finished: ", "finished: ")))  # noqa: E731
    t.eq(strip(export2), strip(export), label + ": exporting again after loading gives the same text, apart from the time")
    ctx.close()
    return types


def test_export_round_trip(env, t, width, height, extra):
    seen = set()
    for label, inst in [("fixture all_types", env.fix["all_types"]), ("fixture quiz", env.fix["quiz"]), ("fixture survey", env.fix["survey"])] + extra:
        seen |= round_trip(env, t, inst, label, width, height)
    t.eq(sorted(seen), sorted(["single", "multi", "text", "likert", "scale", "number", "rank"]), "the round trip exercised every question type with an answer")
    # numbers keep their exact value
    nums = {"id": "fixture-numbers", "version": 1, "mode": "intake", "title": "Numbers (SYNTHETIC)", "questions": [
        {"id": "num-%d" % i, "type": "number", "text": "Number %d?" % i} for i in range(6)]}
    typed = ["0", "-3", "12.50", "0.000001", "123456789012.123456", "007"]
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(nums))
    walk(pg, nums, {"num-%d" % i: {"v": typed[i]} for i in range(6)})
    export = finish(pg)
    parsed = parse_text(export)
    t.eq(parsed.get("errors"), [], "numbers: the export parses")
    t.eq([q["answer"] for q in parsed.get("questions", [])], [0, -3, 12.5, 0.000001, 123456789012.123456, 7], "numbers: each typed value comes back as the same number")
    ctx.close()


def awkward_lines():
    """Lines a person could type that look like parts of an export, then text in four scripts besides Latin and one astral character."""
    cjk = "".join(chr(c) for c in (0x8CB8, 0x51FA, 0x8A18, 0x9332))
    cyr = "".join(chr(c) for c in (0x041F, 0x0440, 0x0438, 0x0432, 0x0435, 0x0442))
    arabic = "".join(chr(c) for c in (0x0633, 0x0644, 0x0627, 0x0645))
    greek = "".join(chr(c) for c in (0x03B3, 0x03B5, 0x03B9, 0x03AC))
    return "\n".join([
        "### [purpose] not a heading", "Answer: (skipped)", "> quoted already", "- a dash", "1. a number", "Note:", "Type: single",
        "Result: correct", "## Section: no such section", "End of export: 1 questions.", "",
        "=== elicitor response ===", "width = 3", "=== end elicitor response: 1 questions, 0 notes ===",
        "Instrument: another-one, version 9, intake mode", "", "",
        cjk + " | " + cyr + " | " + arabic + " | " + greek + " " + chr(0x1F527) + ' "q" <b>x</b> a\\nb 100% & it\'s'])


def test_awkward_text(env, t, width, height):
    hard = awkward_lines()
    strip = lambda x: "\n".join(ln for ln in x.split("\n") if not ln.startswith(("Finished: ", "finished: ")))  # noqa: E731
    for label, inst, text_q, note_q in (("intake", env.fix["all_types"], "anything", "purpose"), ("survey", env.fix["survey"], "one-change", "useful")):
        plan = auto_plan(inst)
        plan[text_q] = {"v": hard}
        plan[note_q] = dict(plan[note_q], note=hard)
        ctx = env.context(width, height)
        name = env.put(inst)
        pg = env.page(ctx, name)
        walk(pg, inst, plan)
        t.ok(pg.locator("#main b").count() == 0, label + ": typed angle brackets are shown as text on the review screen, not built into the page")
        export = finish(pg)
        saved = json.loads(resume_code(pg))
        ctx.close()
        parsed = parse_text(export)
        t.eq(parsed.get("errors"), [], label + ": parse_export reads an export whose answers contain lines that look like export structure")
        got = {q["id"]: q for q in parsed.get("questions", [])}
        t.eq(got.get(text_q, {}).get("answer"), canon(hard), label + ": the typed text comes back line for line, in every script")
        t.eq(got.get(note_q, {}).get("note"), canon(hard), label + ": the note comes back line for line, in every script")
        if inst["mode"] == "survey":
            t.eq(parsed.get("questions"), expected_response(inst, saved), label + ": every other answer is untouched by the awkward text")
        else:
            for d in diff_record(parsed, expected_record(inst, saved)):
                t.ok(False, label + ": " + d)
        # the page reads its own export back, whatever the answers say
        ctx = env.context(width, height)
        pg = env.page(ctx, name)
        do_import(pg, "Here it is:\n\n" + export + "\nThanks.\n")
        pg.wait_for_timeout(300)
        t.eq(text_of(pg, "#import-msg"), "", label + ": the page accepts its own export although an answer contains export markers")
        if stage(pg) == "review":
            t.eq(strip(finish(pg)), strip(export), label + ": loaded into a fresh page and exported again, the text is the same apart from the time")
        else:
            t.ok(False, label + ": the export did not load into a fresh page (stage %s)" % stage(pg))
        ctx.close()


def test_revision_keeps_ids(env, t, width, height, old, new):
    errors, adv, facts = compare(old, new)
    for e in errors:
        t.ok(False, "the revision does not keep ids stable: " + e)
    t.note("revision check: %d id(s) kept, %d added, %d removed, %d advisory note(s)" % (facts.get("kept", 0), len(facts.get("added", [])), len(facts.get("removed", [])), len(adv)))
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(old))
    walk(pg, old, auto_plan(old))
    export = finish(pg)
    saved = json.loads(resume_code(pg))["data"]["answers"]
    ctx.close()
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(new))
    do_import(pg, export)
    if new.get("version") != old.get("version"):
        t.ok(not is_hidden(pg, "#import-confirm"), "an export from the old version asks before loading into the new one")
        pg.click("#import-continue")
    pg.wait_for_selector("#btn-finish, #export-text")
    loaded = json.loads(resume_code(pg))["data"]["answers"]
    newq = {q["id"]: q for q in new.get("questions", [])}
    for q in visible(old, saved):
        a = saved.get(q["id"], {})
        if not valid(q, a.get("v")):
            continue
        nq = newq.get(q["id"])
        if nq is None:
            t.ok(False, "the old answer to %r has nowhere to go: the id is gone from the new version" % q["id"])
            continue
        same = one_line(nq.get("text", "")).lower() == one_line(q["text"]).lower() or len(set(one_line(nq.get("text", "")).lower().split()) & set(one_line(q["text"]).lower().split())) * 2 >= len(set(one_line(q["text"]).lower().split()))
        t.ok(same, "id %r now labels a different question (old: %r, new: %r), so an old answer would be read against the wrong question" % (q["id"], q["text"][:40], str(nq.get("text"))[:40]))
        want = canon(a["v"]) if q["type"] == "text" else a["v"]
        t.eq(loaded.get(q["id"], {}).get("v"), want, "the old answer to %r lands on the same id in the new version" % q["id"])
    ctx.close()
    if new.get("version") == old.get("version") or new.get("id") != old.get("id"):
        return
    # answers saved in the browser under the old version, then the same address serves the new one
    ctx = env.context(width, height)
    name = env.put(old, name="revised-in-place.html")
    pg = env.page(ctx, name)
    walk(pg, old, auto_plan(old))
    pg.wait_for_timeout(300)
    env.put(new, name=name)
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq(stage(pg), "start", "answers saved under the old version are not loaded into the new one unasked")
    t.has(text_of(pg, "#status"), "another version of this questionnaire were found and not loaded", "the page says saved answers from another version were found")
    open_panel(pg)
    t.ok(not is_hidden(pg, "#import-box"), "the box that holds the old saved code is open")
    held = pg.input_value("#import-text")
    t.has(held, '"content_id":"%s@%s"' % (old["id"], old["version"]), "the old saved code is waiting in the box")
    pg.click("#import-go")
    t.ok(not is_hidden(pg, "#import-confirm"), "loading the old saved code asks first, naming both versions")
    pg.click("#import-continue")
    pg.wait_for_selector("#btn-finish, #export-text")
    loaded = json.loads(resume_code(pg))["data"]["answers"]
    for q in visible(old, saved):
        a = saved.get(q["id"], {})
        nq = newq.get(q["id"])
        if valid(q, a.get("v")) and nq is not None and nq["type"] == q["type"]:
            t.eq(loaded.get(q["id"], {}).get("v"), canon(a["v"]) if q["type"] == "text" else a["v"], "saved in the browser under the old version, the answer to %r comes back on the same id" % q["id"])
    ctx.close()


def test_survey_mode(env, t, width, height):
    inst = env.fix["survey"]
    byid = {q["id"]: q for q in inst["questions"]}
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    first = text_of(pg, "#main")
    for k in ("who", "purpose", "handling", "contact"):
        t.has(first, inst["disclosure"][k], "the first screen states disclosure." + k)
    t.has(first, "It sends nothing.", "the first screen says the page sends nothing")
    t.ok(pg.locator("#main article.q").count() == 0, "no question is shown before the disclosure is passed")
    t.eq(text_of(pg, "#btn-start"), "I have read this. Start", "the button names what the respondent is confirming")
    env.shot(pg, "survey-disclosure-%d" % width)
    pg.click("#btn-start")
    set_answer(pg, byid["useful"], 4)
    pg.fill("#note-useful", "Second half was better.")
    pg.click("#btn-next")
    set_answer(pg, byid["pace"], "About right")
    pg.click("#btn-next")
    t.eq(cur_q(pg), "kept", "the conditional question is passed over")
    pg.click("#btn-skip")
    set_answer(pg, byid["recommend"], 8)
    pg.click("#btn-next")
    pg.fill("#in-one-change", "Start with the worked example.\nThen the theory.")
    pg.click("#btn-next")
    block = finish(pg)
    env.shot(pg, "survey-finished-%d" % width)
    want = "\n".join(["=== elicitor response ===", "instrument: fixture-survey", "version: 1"])
    t.ok(block.startswith(want), "the block opens with its marker, instrument and version")
    for line in ('useful = 4', 'useful.note = "Second half was better."', 'pace = "About right"', 'pace-where = HIDDEN', 'kept = SKIPPED', 'recommend = 8',
                 'one-change = "Start with the worked example.\\nThen the theory."', 'tally:rated-high = [2,2]', '=== end elicitor response: 6 questions, 1 note ==='):
        t.has(block, "\n" + line + "\n", "response block line")
    t.has(text_of(pg, "#main"), "Nothing has been sent.", "the last screen says nothing has been sent")
    t.has(text_of(pg, "#main"), "It goes to: The organiser of the test session.", "the last screen says who the block goes to")
    pg.click("#copy-export")
    pg.wait_for_function("() => document.getElementById('copy-status').textContent.length > 0")
    said = text_of(pg, "#copy-status")
    t.ok("It goes to: The organiser of the test session." in said or "Copying is blocked here" in said, "after Copy the page says where the block goes, or that copying was blocked (%r)" % said[:60])
    t.has(text_of(pg, "#tally-caveat"), TALLY_LINE, "the tally caveat is shown in survey mode")
    parsed = parse_text(block)
    t.eq(parsed.get("errors"), [], "parse_export reads the response block")
    t.eq(parsed.get("questions"), expected_response(inst, json.loads(resume_code(pg))), "the response block round trips")
    ctx.close()
    # a survey with a disclosure field missing does not open
    broken = copy.deepcopy(inst)
    del broken["disclosure"]["handling"]
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(broken))
    t.has(text_of(pg, "#data-problems"), "disclosure.handling", "a survey with no statement of what happens to answers refuses to open")
    t.ok(pg.locator("#btn-start").count() == 0, "and offers no way in")
    ctx.close()


def test_tallies(env, t, width, height):
    inst = env.fix["all_types"]
    plan = auto_plan(inst)
    plan.update({"wall": {"v": "Yes"}, "wall-type": {"skip": True}, "power": {"v": "Yes"}, "sturdy": {"v": 5}, "finish": {"v": 2}, "urgency": {"v": 4}})
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    walk(pg, inst, plan)
    export = finish(pg)
    rows = pg.evaluate("() => Array.from(document.querySelectorAll('#tallies li')).map(n => [n.getAttribute('data-tally'), n.textContent])")
    t.eq([r[0] for r in rows], ["site-yes", "quality-high"], "both tallies are listed")
    t.has(rows[0][1], "Site checks answered Yes (2 of 3 answered)", "a tally says how many of its items were answered")
    t.has(rows[0][1], "2 of 3", "a tally is a count with its denominator")
    t.has(rows[1][1], "2 of 3", "the second tally counts 5 and 4 and not 2")
    t.eq(text_of(pg, "#tally-caveat"), TALLY_LINE, "the fixed caveat is printed under the tallies")
    t.has(export, "## Tallies\n\n- [site-yes] Site checks answered Yes: 2 of 3 (answered: 2)\n- [quality-high] Quality statements rated 4 or above: 2 of 3 (answered: 3)\n" + TALLY_LINE + "\n", "the export holds the tallies and the caveat")
    body = text_of(pg, "#main")
    t.ok("%" not in body.replace("50%", "").replace("100%", ""), "no percentage is shown with the tallies")
    env.shot(pg, "tallies-%d" % width)
    # the 3-of-3 boundary: at_least 4 counts a 4 and not a 3
    pg.click("#change-answers")
    pg.click("#edit-finish")
    set_answer(pg, {"id": "finish", "type": "likert", "labels": [1, 2, 3, 4]}, 3)
    pg.click("#btn-next")
    finish(pg)
    t.has(text_of(pg, "[data-tally='quality-high']"), "2 of 3", "a rating of 3 is not counted by 'at least 4'")
    pg.click("#change-answers")
    pg.click("#edit-finish")
    set_answer(pg, {"id": "finish", "type": "likert", "labels": [1, 2, 3, 4]}, 4)
    pg.click("#btn-next")
    finish(pg)
    t.has(text_of(pg, "[data-tally='quality-high']"), "3 of 3", "a rating of 4 is counted by 'at least 4'")
    # a tagged question hidden by an earlier answer leaves the denominator
    wall = [q for q in inst["questions"] if q["id"] == "wall"][0]
    pg.click("#change-answers")
    pg.click("#edit-wall")
    set_answer(pg, wall, "No")
    pg.click("#btn-next")
    export = finish(pg)
    t.has(text_of(pg, "[data-tally='site-yes']"), "1 of 2", "a tagged question hidden by an earlier answer is not counted in the denominator")
    t.has(export, "- [site-yes] Site checks answered Yes: 1 of 2 (answered: 2)\n", "and the export gives the same count")
    ctx.close()


def test_section_layout(env, t, width, height):
    inst = copy.deepcopy(env.fix["all_types"])
    plan = auto_plan(inst)
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    walk(pg, inst, plan)
    one = finish(pg)
    ctx.close()
    inst2 = copy.deepcopy(inst)
    inst2["layout"] = "sections"
    byid = {q["id"]: q for q in inst2["questions"]}
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst2))
    t.has(text_of(pg, "#main"), "One section at a time", "the first screen describes the section layout")
    pg.click("#btn-start")
    shown = pg.evaluate("() => Array.from(document.querySelectorAll('#main article.q')).map(n => n.getAttribute('data-q'))")
    t.eq(shown, ["purpose", "rooms", "width"], "the first section shows its questions together")
    pg.click("#btn-next")
    t.has(text_of(pg, "#qe-width"), "needs an answer", "a required question holds the section")
    t.has(text_of(pg, "#status"), "1 question in this section needs attention.", "the section says how many questions need attention")
    env.shot(pg, "sections-error-%d" % width)
    guard = 0
    while stage(pg) == "q" and guard < 6:
        guard += 1
        done = set()
        for _ in range(12):
            ids = pg.evaluate("() => Array.from(document.querySelectorAll('#main article.q')).map(n => n.getAttribute('data-q'))")
            todo = [i for i in ids if i not in done]
            if not todo:
                break
            qid = todo[0]
            done.add(qid)
            step = plan.get(qid)
            if step is None or step.get("skip"):
                pg.click("#skip-" + qid)
                t.eq(pg.get_attribute("#skip-" + qid, "aria-pressed"), "true", "a skip in the section layout is shown as pressed")
            else:
                set_answer(pg, byid[qid], step["v"])
                if "note" in step:
                    pg.fill("#note-" + qid, step["note"])
        pg.click("#btn-next")
    t.eq(stage(pg), "review", "the section layout reaches the review screen")
    sect = finish(pg)
    strip = lambda x: "\n".join(ln for ln in x.split("\n") if not ln.startswith("Finished: "))  # noqa: E731
    t.eq(strip(sect), strip(one), "the same answers give the same export in either layout")
    # the reader can switch layout in the page, and the choice is kept
    pg.click("#change-answers")
    pg.click("#edit-purpose")
    open_panel(pg)
    pg.click("[data-set='layout'][data-val='one']")
    pg.click("#panel-close")
    t.eq(pg.locator("#main article.q").count(), 1, "switching to one at a time shows one question")
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq(pg.locator("#main article.q").count(), 1, "the layout choice is kept across a reload")
    ctx.close()


def test_display_settings(env, t, width, height):
    inst = env.fix["all_types"]
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    root = lambda a: pg.evaluate("(a) => document.documentElement.getAttribute(a)", a)  # noqa: E731
    t.eq([root("data-theme"), root("data-size"), root("data-density"), root("data-motion")], ["paper", "standard", "comfortable", "on"], "defaults: warm light theme, standard size, comfortable, movement on")
    open_panel(pg)
    env.shot(pg, "panel-%d" % width)
    bgs = {}
    for theme in ("slate", "dusk", "ink", "paper"):
        pg.click("[data-set='theme'][data-val='%s']" % theme)
        t.eq(root("data-theme"), theme, "theme %s is applied at once" % theme)
        t.eq(pg.get_attribute("[data-set='theme'][data-val='%s']" % theme, "aria-pressed"), "true", "theme %s is shown as selected" % theme)
        t.eq(pg.locator("[data-set='theme'][aria-pressed='true']").count(), 1, "only one theme is shown as selected")
        bgs[theme] = pg.evaluate("() => getComputedStyle(document.body).backgroundColor + '|' + getComputedStyle(document.body).color + '|' + getComputedStyle(document.querySelector('.btn.primary') || document.body).backgroundColor")
    t.eq(len(set(bgs.values())), 4, "the four themes are four different sets of colours")
    base = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.lead h1')).fontSize)")
    for size, factor in (("large", 1.125), ("larger", 1.25)):
        pg.click("[data-set='size'][data-val='%s']" % size)
        got = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.lead h1')).fontSize)")
        t.ok(abs(got - base * factor) < 0.6, "text size %s scales the heading by %s (from %.1f to %.1f)" % (size, factor, base, got))
    pg.click("[data-set='density'][data-val='compact']")
    pg.click("[data-set='motion'][data-val='off']")
    pg.click("[data-set='theme'][data-val='dusk']")
    pg.click("#panel-close")
    pg.click("#btn-start")
    t.eq(pg.evaluate("() => getComputedStyle(document.querySelector('.q.enter')).animationName"), "none", "with movement off a new question does not animate")
    pad_compact = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.opt')).paddingTop)")
    env.shot(pg, "dusk-compact-larger-%d" % width)
    pg.wait_for_timeout(250)
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq([root("data-theme"), root("data-size"), root("data-density"), root("data-motion")], ["dusk", "larger", "compact", "off"], "display choices are kept across a reload")
    open_panel(pg)
    pg.click("#display-reset")
    t.eq([root("data-theme"), root("data-size"), root("data-density"), root("data-motion")], ["paper", "standard", "comfortable", "on"], "Reset display returns every choice to its default")
    t.eq(pg.locator("[data-set][aria-pressed='true']").count(), 5, "after a reset each group shows one selected choice")
    pg.click("#panel-close")
    pad_comfy = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.opt')).paddingTop)")
    t.ok(pad_comfy > pad_compact, "compact spacing is tighter than comfortable (%.1f against %.1f)" % (pad_compact, pad_comfy))
    t.ok(pg.evaluate("() => getComputedStyle(document.querySelector('.cell')).transitionDuration") != "0s", "with movement on the progress strip animates")
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq(root("data-theme"), "paper", "the reset is what is kept")
    ctx.close()
    # reduced motion asked for by the device is the default
    ctx = env.browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
    ctx.route(ORIGIN + "/**", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=env.files.get(urlsplit(route.request.url).path, b"")))
    pg = ctx.new_page()
    pg.goto(ORIGIN + "/" + env.put(inst))
    pg.wait_for_selector(READY)
    t.eq(pg.evaluate("() => document.documentElement.getAttribute('data-motion')"), "off", "a device that asks for reduced motion gets movement off by default")
    ctx.close()
    # without storage the choices still apply, and the page says they will not be kept
    ctx = env.context(width, height, init=THROWING_STORAGE)
    pg = env.page(ctx, env.put(inst))
    open_panel(pg)
    pg.click("[data-set='theme'][data-val='ink']")
    t.eq(pg.evaluate("() => document.documentElement.getAttribute('data-theme')"), "ink", "without storage a theme still applies")
    t.has(text_of(pg, "#display-note"), "Display choices last for this visit only.", "without storage the page says display choices will not be kept")
    ctx.close()


LONG = {
    "id": "fixture-long-text", "version": 1, "mode": "intake",
    "title": "A questionnaire with an unusually long title that has to wrap across several lines on a narrow screen (SYNTHETIC)",
    "purpose": "Checks that long words such as Donaudampfschifffahrtsgesellschaftskapitaensmuetze and https://example.org/a/very/long/path/with-no-spaces-in-it-at-all/index.html do not push the page sideways.",
    "sections": [{"id": "only", "title": "A section with a rather long heading that also needs to wrap on a phone"}],
    "questions": [
        {"id": "a-very-long-question-identifier-that-keeps-going-and-going-0001", "section": "only", "type": "single", "required": True,
         "text": "When the thing you are describing has a name like Donaudampfschifffahrtsgesellschaftskapitaensmuetze, which of these long options is closest to what you mean by it?",
         "help": "See https://example.org/a/very/long/path/with-no-spaces-in-it-at-all/index.html for the background.",
         "options": ["An option that runs to a full sentence and then a little further, to be sure that it wraps inside its row and does not widen the page",
                     "Supercalifragilisticexpialidocious-and-then-some-more-letters-without-a-break", "Short", "Another fairly long option, for balance, with a comma",
                     "Fifth", "Sixth option", "Seventh option, also long enough to wrap on a narrow phone screen", "Eighth"]},
        {"id": "long-likert", "section": "only", "type": "likert", "text": "A statement to rate, with labels that are longer than usual.",
         "labels": ["Completely and utterly disagree", "Somewhat disagree", "Neither agree nor disagree", "Somewhat agree", "Completely and utterly agree"]},
        {"id": "long-scale", "section": "only", "type": "scale", "text": "A scale with long end labels?", "min": 0, "max": 10,
         "min_label": "Not at all, under any circumstances whatsoever", "max_label": "Entirely, in every circumstance imaginable"},
        {"id": "long-rank", "section": "only", "type": "rank", "text": "Rank these long items.",
         "options": ["A ranked item whose label is long enough to wrap onto a second line on a phone", "Supercalifragilisticexpialidocious-unbroken-label", "Short"]},
        {"id": "long-number", "section": "only", "type": "number", "text": "A number with a long unit?", "min": 0, "max": 100000, "unit": "kilowatt-hours per square metre per year"},
        {"id": "long-text", "section": "only", "type": "text", "long": True, "text": "Free text?"}
    ],
    "tallies": [{"id": "t", "label": "A tally with a long label that explains at some length what is being counted here", "tag": "x", "when": {"answered": True}}]
}
LONG["questions"][1]["tags"] = ["x"]

OVERFLOW_JS = """() => {
  const out = [], vw = window.innerWidth, de = document.documentElement;
  if (de.scrollWidth > vw + 1) out.push('the page scrolls sideways: content is ' + de.scrollWidth + 'px wide in a ' + vw + 'px viewport');
  document.querySelectorAll('#app *').forEach(n => {
    if (n.closest('[hidden]')) return;
    const r = n.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && (r.right > vw + 1 || r.left < -1)) out.push(n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + (n.className ? '.' + String(n.className).split(' ')[0] : '') + ' sticks out to ' + Math.round(r.right) + 'px');
  });
  document.querySelectorAll('#app button, #app .t, #app .q-text, #app .rv-q, #app .rv-a, #app label, #app .doc-title, #app h1, #app h2').forEach(n => {
    if (n.closest('[hidden]') || n.classList.contains('chip')) return;
    const cs = getComputedStyle(n);
    if ((n.scrollWidth > n.clientWidth + 1 && cs.overflowX !== 'visible') || cs.textOverflow === 'ellipsis') out.push('text is cut off in ' + n.tagName.toLowerCase() + (n.id ? '#' + n.id : ''));
  });
  return out.slice(0, 6);
}"""


def test_no_overflow(env, t, width, height):
    name = env.put(LONG)
    for w in (360, 390, 1280):
        for size in ("standard", "larger"):
            ctx = env.context(w, 800)
            pg = env.page(ctx, name)
            open_panel(pg)
            pg.click("[data-set='size'][data-val='%s']" % size)
            where = "%dpx, %s text" % (w, size)
            for p in pg.evaluate(OVERFLOW_JS):
                t.ok(False, "%s, settings panel: %s" % (where, p))
            pg.click("#resume-make")
            pg.click("#import-open")
            pg.click("#reset-ask")
            for p in pg.evaluate(OVERFLOW_JS):
                t.ok(False, "%s, settings panel fully open: %s" % (where, p))
            pg.click("#reset-cancel")
            pg.click("#panel-close")
            for p in pg.evaluate(OVERFLOW_JS):
                t.ok(False, "%s, first screen: %s" % (where, p))
            pg.click("#btn-start")
            pg.click("#btn-next")
            n = 0
            byid = {q["id"]: q for q in LONG["questions"]}
            plan = auto_plan(LONG)
            while stage(pg) == "q":
                n += 1
                for p in pg.evaluate(OVERFLOW_JS):
                    t.ok(False, "%s, question %s: %s" % (where, cur_q(pg), p))
                if size == "larger" and w == 360:
                    env.shot(pg, "long-content-360-larger-q%d" % n)
                do_step(pg, byid[cur_q(pg)], plan.get(cur_q(pg)))
            for p in pg.evaluate(OVERFLOW_JS):
                t.ok(False, "%s, review: %s" % (where, p))
            if size == "larger" and w == 360:
                env.shot(pg, "long-content-360-larger-review")
            finish(pg)
            for p in pg.evaluate(OVERFLOW_JS):
                t.ok(False, "%s, finished: %s" % (where, p))
            small = pg.evaluate("""() => Array.from(document.querySelectorAll('#app button, #app .opt, #app .chip')).filter(n => !n.closest('[hidden]')).map(n => [n.id || n.className, n.getBoundingClientRect()])
                .filter(x => x[1].width > 0 && (x[1].width < 43.5 || x[1].height < 43.5)).map(x => x[0] + ' ' + Math.round(x[1].width) + 'x' + Math.round(x[1].height))""")
            t.eq(small, [], "%s: every button and option row is at least 44 by 44" % where)
            ctx.close()


def test_undo_and_reset(env, t, width, height):
    inst = env.fix["all_types"]
    byid = {q["id"]: q for q in inst["questions"]}
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    pg.click("#btn-start")
    set_answer(pg, byid["purpose"], "Tools")
    pg.fill("#note-purpose", "a note")
    pg.click("#btn-next")
    set_answer(pg, byid["rooms"], ["Kitchen"])
    before = json.loads(resume_code(pg))["data"]
    pg.click("#btn-skip")
    t.has(text_of(pg, "#status"), 'Skipped "rooms" and removed its answer.', "skipping an answered question says the answer was removed")
    t.eq(answers_of(resume_code(pg)).get("rooms"), {"skipped": True}, "the skipped question holds a skip mark and no answer")
    pg.click("#undo")
    t.eq(json.loads(resume_code(pg))["data"], before, "Undo after a skip brings the answer and the place back")
    pg.click("#btn-next")
    pg.fill("#in-width", "55")
    before = json.loads(resume_code(pg))["data"]
    open_panel(pg)
    pg.click("#reset-ask")
    t.has(text_of(pg, "#reset-text"), "Starting again clears 3 answers, 0 skip marks and 1 note from this page and from its saved copy.", "the confirmation names what will be lost")
    t.has(text_of(pg, "#reset-text"), "Get a resume code first", "the confirmation offers a resume code first")
    t.eq(pg.evaluate("() => document.activeElement.id"), "reset-cancel", "keeping the answers has the focus")
    env.shot(pg, "reset-confirm-%d" % width)
    pg.click("#reset-cancel")
    t.eq(json.loads(resume_code(pg))["data"], before, "choosing to keep changes nothing")
    open_panel(pg)
    pg.click("#reset-ask")
    pg.click("#reset-export")
    t.ok(not is_hidden(pg, "#resume-text") and json.loads(pg.input_value("#resume-text"))["data"]["answers"] == before["answers"], "the resume code offered before a reset holds the answers")
    pg.click("#reset-go")
    t.eq(stage(pg), "start", "after a reset the page is at its first screen")
    t.eq(answers_of(resume_code(pg)), {}, "after a reset there are no answers")
    pg.click("#undo")
    t.eq(json.loads(resume_code(pg))["data"], before, "Undo after a reset brings everything back")
    pg.reload()
    pg.wait_for_selector(READY)
    t.eq(json.loads(resume_code(pg))["data"]["answers"], before["answers"], "what Undo restored is also what is saved")
    ctx.close()


def test_data_block_faults(env, t, width, height):
    inst = env.fix["all_types"]
    good = build(env.engine_text, inst)
    ctx = env.context(width, height)
    broken = good.replace('"version": 1,', '"version": 1,,', 1)
    t.ok(broken != good, "the fault was planted")
    pg = env.page(ctx, env.put(None, raw=broken))
    t.has(text_of(pg, "#main"), "This questionnaire cannot open", "a data block with a syntax fault gives a stated fault")
    t.has(text_of(pg, "#data-problems"), "strict JSON", "the fault names the likely cause")
    t.ok(pg.locator("#btn-start").count() == 0, "a faulty questionnaire offers no way in")
    env.shot(pg, "data-block-fault-%d" % width)
    env.noise[:] = [n for n in env.noise if "Unexpected token" not in n and "SyntaxError" not in n]
    empty = copy.deepcopy(inst)
    empty["questions"] = []
    empty["tallies"] = []
    pg = env.page(ctx, env.put(None, raw=build(env.engine_text, empty)))
    t.has(text_of(pg, "#no-questions"), "No questions yet", "an empty question list gives an empty state")
    env.shot(pg, "no-questions-%d" % width)
    dup = copy.deepcopy(inst)
    dup["questions"][1]["id"] = "purpose"
    pg = env.page(ctx, env.put(None, raw=build(env.engine_text, dup)))
    t.has(text_of(pg, "#data-problems"), "uses an id twice", "a repeated id is named")
    ctx.close()


def test_keyboard_and_focus(env, t, width, height):
    inst = env.fix["all_types"]
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(inst))
    pg.focus("#btn-start")
    pg.keyboard.press("Enter")
    t.eq(pg.evaluate("() => document.activeElement.id"), "qt-purpose", "after Start, focus is on the question")
    pg.keyboard.press("Tab")
    t.eq(pg.evaluate("() => document.activeElement.id"), "in-purpose-0", "Tab moves from the question to its first option")
    pg.keyboard.press("Space")
    pg.keyboard.press("ArrowDown")
    t.ok(pg.is_checked("#in-purpose-1"), "arrow keys move the choice")
    t.ok(pg.evaluate("() => { const o = getComputedStyle(document.activeElement.closest('.opt')); return o.outlineStyle !== 'none' && parseFloat(o.outlineWidth) >= 2; }"), "the row of the focused option has a visible focus ring")
    pg.focus("#btn-next")
    t.ok(pg.evaluate("() => { const o = getComputedStyle(document.querySelector('#in-purpose-1').closest('.opt')); return o.outlineStyle === 'none' || parseFloat(o.outlineWidth) === 0; }"), "the ring leaves the option when focus moves on")
    pg.focus("#btn-next")
    pg.keyboard.press("Enter")
    t.eq(pg.evaluate("() => document.activeElement.id"), "qt-rooms", "after Next, focus is on the next question")
    pg.click("#btn-skip")
    pg.focus("#in-width")
    pg.keyboard.type("90")
    pg.keyboard.press("Enter")
    t.eq(cur_q(pg), "load", "Enter in a one-line field does what Next does")
    for _ in range(5):
        pg.click("#btn-skip")
    t.eq(cur_q(pg), "order", "at the ranking question")
    pg.focus("#down-order-0")
    pg.keyboard.press("Enter")
    t.eq(pg.evaluate("() => document.activeElement.id"), "down-order-1", "after a move, focus stays on the same item's button")
    t.has(text_of(pg, "#rk-order"), 'Moved "Cost" to position 2 of 4', "a move is announced in words")
    pg.focus("#up-order-1")
    pg.keyboard.press("Enter")
    t.eq(pg.evaluate("() => document.activeElement.id"), "up-order-0", "moving to the top keeps focus on a button that is now at its limit")
    t.eq(pg.get_attribute("#up-order-0", "aria-disabled"), "true", "a button at its limit is marked aria-disabled")
    t.ok(pg.evaluate("() => document.querySelectorAll('button[disabled], input[disabled], textarea[disabled]').length") == 0, "no control uses the disabled attribute, which would drop focus")
    open_panel(pg)
    t.eq(pg.evaluate("() => document.activeElement.id"), "panel-h", "opening the panel moves focus into it")
    t.ok(is_hidden(pg, "#btn-next"), "the question's buttons are put away while the panel is open")
    pg.click("#panel-close")
    t.eq(pg.evaluate("() => document.activeElement.id"), "panel-toggle", "closing the panel returns focus to its button")
    t.ok(not is_hidden(pg, "#btn-next"), "the question's buttons come back when the panel closes")
    labels = pg.evaluate("""() => Array.from(document.querySelectorAll('input, textarea, select')).filter(n => !n.closest('[hidden]')).filter(n =>
        !(n.labels && n.labels.length) && !n.getAttribute('aria-label') && !n.getAttribute('aria-labelledby')).map(n => n.id || n.name)""")
    t.eq(labels, [], "every field on the screen has a label")
    ctx.close()


def test_page_rules(env, t, width, height):
    src = env.engine_text
    low = src.lower()
    t.ok("<form" not in low, "the page has no form element")
    for word in ("alert(", "confirm(", "prompt("):
        t.ok(word not in src, "the page never calls %s)" % word)
    t.ok("innerhtml" not in low and "insertadjacenthtml" not in low and "document.write" not in low, "the page never builds markup from text")
    t.ok("http://" not in low.replace("http://www.w3.org/2000/svg", "") and "https://" not in low, "the page names no outside address")
    t.ok("user-scalable" not in low and "maximum-scale" not in low, "zoom is not limited")
    t.ok(all(ord(c) < 128 for c in src), "the engine file is plain ASCII")
    hostile = copy.deepcopy(env.fix["all_types"])
    hostile["title"] = 'Title <img src=x onerror="window.__hit=1"> & </script><script>window.__hit=2</script>'
    hostile["questions"][0]["text"] = 'Question <b onmouseover="window.__hit=3">bold?</b> </script>'
    hostile["questions"][0]["options"][0] = '<script>window.__hit=4</script>'
    ctx = env.context(width, height)
    pg = env.page(ctx, env.put(hostile))
    pg.click("#btn-start")
    t.eq(text_of(pg, "#qt-purpose"), 'Question <b onmouseover="window.__hit=3">bold?</b> </script>', "markup in a question is shown as text")
    t.ok(pg.evaluate("() => window.__hit === undefined && document.querySelectorAll('#main img, #main b, #main script').length === 0"), "markup in the data block is never run or built")
    plan = auto_plan(hostile)
    plan["purpose"] = {"v": hostile["questions"][0]["options"][0], "note": '<img src=x onerror="window.__hit=5">'}
    walk(pg, hostile, plan, start=False)
    t.has(text_of(pg, "[data-rv='purpose']"), '<img src=x onerror="window.__hit=5">', "markup typed into a note is shown as text on the review screen")
    finish(pg)
    t.ok(pg.evaluate("() => window.__hit === undefined"), "nothing typed into the page is run")
    ctx.close()
    t.eq(env.noise, [], "no outside request, page error or console error during the whole run")


TESTS = [
    ("intake_journey", True), ("clipboard_refused", True), ("reload_resume", True), ("storage_throwing", True), ("import_refusals", True),
    ("quiz_scoring", True), ("show_if", True), ("long_instrument", True), ("export_round_trip", True), ("awkward_text", True), ("revision_keeps_ids", True),
    ("survey_mode", True), ("tallies", False), ("section_layout", False), ("display_settings", False), ("no_overflow", False),
    ("undo_and_reset", False), ("data_block_faults", False), ("keyboard_and_focus", False), ("page_rules", False),
]


def main(argv):
    flags, opts, extra_paths, revision, it = set(), {}, [], None, iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_engine: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a == "--instrument":
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_engine: --instrument needs a file", file=sys.stderr)
                return 2
            extra_paths.append(v)
        elif a == "--revision":
            old, new = next(it, None), next(it, None)
            if old is None or new is None or old.startswith("--") or new.startswith("--"):
                print("test_engine: --revision needs two files, OLD then NEW", file=sys.stderr)
                return 2
            revision = (old, new)
        else:
            print("test_engine: unknown option " + a, file=sys.stderr)
            return 2
    names = [n for n, _ in TESTS]
    if "--list" in flags:
        print("\n".join(names))
        return 0
    only = names
    if "--only" in opts:
        only = [x for x in opts["--only"].split(",") if x]
        bad = [x for x in only if x not in names]
        if bad or not only:
            print("test_engine: unknown test %r. Known: %s" % (", ".join(bad), ", ".join(names)), file=sys.stderr)
            return 2
    engine_path = opts.get("--engine", str(HERE.parent / "assets" / "engine.html"))
    try:
        engine_text = read_text(engine_path)
        build(engine_text, {"id": "probe"}, engine_path)
        extra = [(Path(p).name, load_instrument(p)[0]) for p in extra_paths]
        rev = [load_instrument(p)[0] for p in revision] if revision else None
        for label, inst in extra:
            errs = check(inst)[0]
            if errs:
                raise InputError("%s does not validate: %s" % (label, errs[0]))
    except InputError as e:
        print("test_engine: %s" % e, file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("NOT RUN: the Python package 'playwright' is not installed, so no browser test was run.")
        return 3
    results = []
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch()
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: Playwright could not start a Chromium (%s)." % str(e).split("\n")[0][:120])
        return 3
    try:
        env = Env(browser, engine_text, opts.get("--shots"))
        if "--write-fixtures" in flags:
            env.write_fixtures = True
            only = ["export_round_trip"]
        for name, both in TESTS:
            if name not in only:
                continue
            fn = globals()["test_" + name]
            for width, height in ((390, 844), (1280, 800)) if both else ((390, 844),):
                t = T()
                t0 = time.time()
                try:
                    if name == "export_round_trip":
                        fn(env, t, width, height, extra)
                    elif name == "revision_keeps_ids":
                        fn(env, t, width, height, *(rev or [env.fix["all_types"], env.fix["all_types_v2"]]))
                    else:
                        fn(env, t, width, height)
                except Exception as e:  # noqa: BLE001
                    t.fails.append("stopped early: %s: %s" % (type(e).__name__, " | ".join(x.strip() for x in str(e).split("\n")[:4] if x.strip())[:300]))
                results.append({"test": name, "viewport": "%dx%d" % (width, height), "passed": not t.fails, "failures": t.fails, "notes": t.notes, "seconds": round(time.time() - t0, 1)})
    finally:
        browser.close()
        pw.stop()
    failed = [r for r in results if not r["passed"]]
    if "--json" in flags:
        text = json.dumps({"engine": engine_path, "results": results, "failed": len(failed)}, indent=1, ensure_ascii=True)
    else:
        L = ["test_engine: %s" % engine_path]
        for r in results:
            L.append("%-4s %-20s %-9s %5.1fs" % ("PASS" if r["passed"] else "FAIL", r["test"], r["viewport"], r["seconds"]))
            L += ["       FAILED  " + f for f in r["failures"][:12]]
            if len(r["failures"]) > 12:
                L.append("       ... and %d more" % (len(r["failures"]) - 12))
            L += ["       note    " + n for n in r["notes"]]
        L.append("RESULT: %s. %d of %d test run(s) passed. This is one Chromium at two viewport sizes, not a phone and not a host's preview."
                 % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
        text = "\n".join(L)
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
