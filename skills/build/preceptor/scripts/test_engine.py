#!/usr/bin/env python3
"""Drive the course engine in a real browser and check that it does what the skill says it does.

Usage:
  python test_engine.py [--engine ENGINE.html] [--course COURSE.json] [--renderers FILE.js]
                        [--page BUILT.html] [--only t1,t4] [--mutants] [--port 8120] [--json]

With no options it builds a page from assets/engine.html, assets/sample-course-ipv4.json and
assets/sample-renderers-ipv4.js in a temporary folder and tests that. --page tests an already
built course page instead (its course must have a first module with at least two objectives and
at least one module that depends on it). Nothing in the skill folder is written.

Each test runs at 390 by 844 and at 1280 by 800, in a fresh browser profile, against a page
served from 127.0.0.1 on the first free port from --port to 8139.

  t1  gates       a dependent module is locked; passing the gate opens it; failing on one
                  objective names that objective, links to its material and leaves the next
                  module locked; the pass mark's two neighbours (largest fail, smallest pass);
                  an incomplete submission records nothing
  t2  fading      full shows every step; partial has blanks that check typed input; independent
                  hides the solution until asked
  t3  feedback    choosing each option of every practice item shows that option's own explanation
  t4  schedule    a card driven through Good, Easy, Again, Hard, Easy, Good on a test clock has
                  the interval, E-Factor and due date printed by sm2.py --trace; a lapse leaves
                  the E-Factor alone; a card graded below Good returns the same day and its
                  repeats change nothing; a clock moved backwards un-dues nothing; ?today= is
                  ignored on a page that does not carry the data-test mark
  t5  backup      progress survives a reload; export then import into a fresh profile gives
                  identical data, by pasted text and by file; the page works with storage refused;
                  a host storage object (window.storage) is used first, and a failing one falls
                  back to browser storage
  t6  imports     nine bad backups are each refused with stored progress byte-identical, and the
                  valid one beside them is accepted; an older version is mapped by id with the
                  unmatched entries named; unreadable stored data is left untouched
  t7  mastery     reading every part, practising and reviewing cards raises activity and leaves
                  mastery at zero; a passed gate raises mastery; an objective is listed as due for
                  a check on the stated day and not the day before, and the totals do not move
  t8  planned     a planned module shows as not yet written, cannot be opened, and is left out
                  of every total
  t9  display     every theme and setting applies, shows as selected, survives a reload, resets
  t10 scale       a 28-module course with 280 scheduled cards imports, renders and round-trips
  t11 layout      no sideways overflow, cut-off label or over-wide table at 360, 390 and 1280 on
                  every screen of every module (at the largest text size a grid may scroll in place)
  t12 frame       the page runs inside <iframe sandbox="allow-scripts"> and says it cannot save
  t13 visuals     every visual draws and responds; sliders and tables agree with the formulas
  t14 broken      a course with a prerequisite cycle, a data block that does not parse and a
                  missing custom renderer each fail with an explanation, not a blank page

--mutants proves the tests can fail. It makes twenty deliberately broken copies of the engine,
one fault in each, and runs the test that should catch it at 390 wide. Exit 0 only if every
mutant is caught. Among them: a failed gate still opens the next module (t1); the pass mark is
treated as exclusive (t1, on the built-in demo, where 4 of 5 is exactly 80 percent); a lapse
changes the E-Factor (t4); a same-day repeat reschedules the card (t4); a refused import wipes
progress (t6); reading a tab or reviewing a card marks an objective demonstrated (t7); planned
modules are counted in totals (t8). The full list is the MUTANTS table below.

What this cannot tell: whether a course teaches well, whether the page works in a particular
product's preview (this is a local browser and a local sandboxed frame), or anything about screen
readers. Contrast and target size are measured by other tools.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes: 0 every test passed (or every mutant was caught). 1 a test failed (or a mutant
survived). 2 bad arguments. 3 could not run (prints NOT RUN).
"""
import copy
import datetime as dt
import functools
import http.server
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_course as vc  # noqa: E402

FLAGS = {"--mutants", "--json"}
VALUES = {"--engine", "--course", "--renderers", "--page", "--only", "--port"}
SIZES = [(390, 844), (1280, 800)]
DAY0 = "2026-10-09"
DATA_BLOCK = re.compile(r"(/\* === COURSE DATA: BEGIN[^\n]*\*/\s*const COURSE\s*=\s*)(.*?)(;\s*/\* === COURSE DATA: END === \*/)", re.S)


class Failed(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Failed(msg)


def plain(text):
    """Course text as the page shows it: inline marks removed."""
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", re.sub(r"`([^`]+)`", r"\1", text))


# ---------- pages under test ----------
def embed(engine_text, course, renderers=None):
    data = json.dumps(course, indent=1, ensure_ascii=True).replace("</", "<\\/")
    page = DATA_BLOCK.sub(lambda m: m.group(1) + data + m.group(3), engine_text, count=1)
    if renderers:
        page = re.sub(r"(const CUSTOM_RENDERERS\s*=\s*)(.*?)(;\s*/\* === CUSTOM RENDERERS: END === \*/)", lambda m: m.group(1) + renderers + m.group(3), page, count=1, flags=re.S)
    return page


def with_test_clock(page_text):
    out, n = re.subn(r"<html lang=\"en\"", "<html lang=\"en\" data-test=\"1\"", page_text, count=1)
    if n != 1:
        raise Failed("the page has no <html lang=\"en\"> tag to mark for the test clock")
    return out


def synthetic_course(n, planned=(), cards=10):
    """A structurally complete course of made-up content, for size and planned-module tests. SYNTHETIC."""
    mods = []
    for i in range(n):
        mid = "syn-%02d" % (i + 1)
        pre = [] if i == 0 else ["syn-%02d" % i] + (["syn-%02d" % (i - 1)] if i % 4 == 0 and i > 1 else [])
        if i > 2 and i % 3 == 0:
            pre = ["syn-%02d" % (i - 1)]
        if (i + 1) in planned:
            mods.append({"id": mid, "title": "SYNTHETIC module %d (planned)" % (i + 1), "status": "planned", "prereqs": pre})
            continue
        o1, o2 = mid + "-o1", mid + "-o2"

        def item(iid, obj, k):
            return {"id": iid, "objective": obj, "stem": "SYNTHETIC item: what is %d plus %d?" % (k, i),
                    "options": [{"text": str(k + i), "correct": True, "why": "The sum of the two numbers is correct."},
                                {"text": str(k + i + 1), "correct": False, "why": "This is one more than the sum."},
                                {"text": str(k * 2 + i + 7), "correct": False, "why": "This doubles the first number."}]}
        mods.append({
            "id": mid, "title": "SYNTHETIC module %d" % (i + 1), "summary": "Made-up content used only to test the engine at size.", "status": "ready", "prereqs": pre,
            "objectives": [{"id": o1, "text": "SYNTHETIC objective one of module %d, stated in full." % (i + 1), "bloom": "apply"},
                           {"id": o2, "text": "SYNTHETIC objective two of module %d, stated in full." % (i + 1), "bloom": "apply"}],
            "terms": [{"term": "sum", "definition": "The result of adding."}],
            "theory": [{"objective": o1, "heading": "First idea", "blocks": [{"type": "p", "text": "SYNTHETIC theory paragraph for the first objective."}]},
                       {"objective": o2, "heading": "Second idea", "blocks": [{"type": "p", "text": "SYNTHETIC theory paragraph for the second objective."}]}],
            "visuals": [{"type": "slider", "id": mid + "-v1", "title": "SYNTHETIC slider", "objective": o1, "caption": "A made-up slider that adds a constant.",
                         "params": [{"name": "x", "label": "x", "min": 0, "max": 10, "step": 1, "value": 3}],
                         "outputs": [{"label": "x plus the module number", "formula": "x + %d" % (i + 1), "format": "int"}]}],
            "worked": [{"id": mid + "-w1", "objective": o1, "title": "SYNTHETIC worked example",
                        "full": {"problem": "Add 2 and 3 in full.", "steps": [{"text": "Add the numbers.", "result": "5"}]},
                        "partial": {"problem": "Add 4 and 5 with one blank.", "steps": [{"text": "Add the numbers.", "blank": {"label": "Sum", "answer": "9", "accept": [], "hint": "Count on from 4."}}]},
                        "independent": {"problem": "Add 6 and 7 alone.", "answers": [{"label": "Sum", "answer": "13", "accept": []}], "solution": [{"text": "Add the numbers.", "result": "13"}]}}],
            "quiz": [item(mid + "-q1", o1, 1), item(mid + "-q2", o2, 2)],
            "gate": {"items": [item(mid + "-g1", o1, 3), item(mid + "-g2", o1, 4), item(mid + "-g3", o2, 5), item(mid + "-g4", o2, 6), item(mid + "-g5", o2, 8)]},
            "cheatsheet": [{"type": "note", "label": "Rule", "text": "SYNTHETIC rule: add the numbers."}],
            "cards": [{"id": "%s-c%d" % (mid, c + 1), "objective": o1 if c % 2 == 0 else o2, "front": "SYNTHETIC card %d of module %d" % (c + 1, i + 1), "back": "Back of card %d." % (c + 1)} for c in range(cards)],
        })
    size = "full" if n >= 24 else "course" if n >= 10 else "primer" if n >= 4 else "demo"
    return {"id": "synthetic-%d" % n, "version": 1, "title": "SYNTHETIC course of %d modules" % n, "subtitle": "Made-up content for testing the engine.", "size": size,
            "size_reason": "Chosen only to exercise the engine at this size.", "for": "Nobody. This is test data.", "gate_threshold": 80, "check_after_days": 30, "modules": mods}


def next_version(course):
    """Version 2 of a course: one objective id renamed and one card removed from the first module, so an import has something unmatched."""
    c = copy.deepcopy(course)
    m = c["modules"][0]
    old = m["objectives"][-1]["id"]
    gone_card = m["cards"][-1]["id"]
    m["cards"] = m["cards"][:-1]
    text = json.dumps(c).replace('"%s"' % old, '"%sb"' % old)
    c = json.loads(text)
    c["version"] = course["version"] + 1
    return c, old, gone_card


class Server:
    def __init__(self, folder, first_port):
        self.folder, self.port, self.httpd = folder, None, None
        handler = functools.partial(QuietHandler, directory=str(folder))
        for port in range(first_port, 8140):
            try:
                self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
                self.port = port
                break
            except OSError:
                continue
        if self.httpd is None:
            raise Failed("no free port from %d to 8139" % first_port)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def url(self, name, today=None):
        return "http://127.0.0.1:%d/%s%s" % (self.port, name, ("?today=" + today) if today else "")

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


# ---------- driving the page ----------
class Rig:
    """One browser profile at one viewport, with helpers that speak the page's language."""

    def __init__(self, browser, server, size, name="course.html", init_script=None):
        self.server, self.name = server, name
        self.ctx = browser.new_context(viewport={"width": size[0], "height": size[1]})
        if init_script:
            self.ctx.add_init_script(init_script)
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(8000)
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        self.course = None

    def open(self, today=DAY0, name=None):
        self.page.goto(self.server.url(name or self.name, today))
        self.page.wait_for_selector("#map, #fatal", timeout=8000)
        self.course = self.page.evaluate("COURSE")
        return self

    def close(self):
        self.ctx.close()

    def key(self):
        return "preceptor:" + self.course["id"]

    def raw(self):
        return self.page.evaluate("k => { try { return localStorage.getItem(k); } catch (e) { return null; } }", self.key())

    def data(self):
        r = self.raw()
        return json.loads(r)["data"] if r else None

    def text(self, sel):
        return self.page.inner_text(sel)

    def view(self, name):
        self.page.click("#nav-" + name)

    def module(self, i):
        return self.course["modules"][i]

    def node_state(self, mid):
        return self.page.get_attribute('[data-module="%s"]' % mid, "data-state")

    def open_module(self, mid, tab=None):
        self.view("map")
        self.page.click('[data-module="%s"]' % mid)
        self.page.wait_for_selector("#lesson-h")
        if tab:
            self.page.click("#tab-" + tab)

    def answer_gate(self, m, wrong_objectives=(), wrong_count=None, submit=True):
        """Choose the correct option for every gate item, except: all items of the named objectives, or the first wrong_count items."""
        self.open_module(m["id"], "gate")
        if self.page.query_selector("#gate-result"):
            self.page.click("#gate-retake")
        for n, it in enumerate(m["gate"]["items"]):
            right = [i for i, o in enumerate(it["options"]) if o["correct"]][0]
            wrong = [i for i, o in enumerate(it["options"]) if not o["correct"]][0]
            miss = it["objective"] in wrong_objectives or (wrong_count is not None and n < wrong_count)
            self.page.check("#gate-%s-%d" % (it["id"], wrong if miss else right))
        if submit:
            self.page.click("#gate-submit")
            self.page.wait_for_selector("#gate-result")

    def gate_passed(self):
        return self.page.get_attribute("#gate-result", "data-passed") == "true"

    def review_card(self):
        el = self.page.query_selector("#review-card")
        return (el.get_attribute("data-card"), el.get_attribute("data-phase")) if el else (None, None)

    def grade(self, q):
        self.page.click("#show-answer")
        self.page.click('[data-grade="%d"]' % q)

    def progress_numbers(self):
        self.view("progress")
        return {"objectives": self.text("#mastery-objectives"), "modules": self.text("#mastery-modules"), "points": int(self.text("#activity-points"))}

    def export_text(self):
        self.view("backup")
        self.page.click("#export-go")
        return self.page.input_value("#export-text")

    def try_import(self, text):
        self.view("backup")
        self.page.fill("#import-text", text)
        self.page.click("#import-go")
        return self.page.get_attribute("#import-msg", "data-result"), self.text("#import-msg")

    def no_errors(self):
        need(not self.errors, "the page logged errors: " + "; ".join(self.errors[:3]))


def sm2_trace(grades, start):
    out = subprocess.run([sys.executable, str(HERE / "sm2.py"), "--trace", ",".join(str(g) for g in grades), "--start", start, "--json"],
                         capture_output=True, text=True)
    need(out.returncode == 0, "sm2.py --trace failed: " + out.stderr.strip())
    return json.loads(out.stdout)["reviews"]


# ---------- the tests ----------
def t1_gates(T):
    r = T.rig().open()
    m1 = r.module(0)
    deps = [m for m in r.course["modules"] if m1["id"] in m.get("prereqs", []) and m.get("status") == "ready"]
    need(deps, "the course has no written module that depends on the first one")
    m2 = deps[0]
    need(r.node_state(m2["id"]) == "locked", "module 2 should start locked, found %s" % r.node_state(m2["id"]))
    r.page.click('[data-module="%s"]' % m2["id"], force=True)   # marked aria-disabled: a person can still press it
    need(r.page.query_selector("#lesson-h") is None, "clicking a locked module opened it")
    need(m1["title"] in r.text("#map-msg"), "the locked message does not name the module to pass: " + r.text("#map-msg"))
    # incomplete submission records nothing
    r.open_module(m1["id"], "gate")
    r.page.check("#gate-%s-0" % m1["gate"]["items"][0]["id"])
    r.page.click("#gate-submit")
    need("Answer every item" in r.text("#gate-error"), "an incomplete gate was not refused in words")
    need(r.page.query_selector("#gate-result") is None, "an incomplete gate produced a result")
    d = r.data()
    need(not (d["modules"].get(m1["id"], {}).get("gate") or {}).get("attempts"), "an incomplete gate was recorded as an attempt")
    # fail on exactly one objective
    target = m1["objectives"][1]
    r.answer_gate(m1, wrong_objectives={target["id"]})
    need(not r.gate_passed(), "a gate with every item of one objective wrong was passed")
    weak = r.page.query_selector_all("[data-weak-objective]")
    need([w.get_attribute("data-weak-objective") for w in weak] == [target["id"]], "the failed gate should name exactly the weak objective %s, named %s" % (target["id"], [w.get_attribute("data-weak-objective") for w in weak]))
    need(target["text"] in weak[0].inner_text(), "the weak objective's text is not shown")
    r.page.click('[data-goto-objective="%s"]' % target["id"])
    r.page.wait_for_selector("#sec-" + target["id"])
    need(r.page.get_attribute("#tab-theory", "aria-selected") == "true", "the link did not open the theory")
    need("flagged" in (r.page.get_attribute("#sec-" + target["id"], "class") or ""), "the objective's section is not flagged for review")
    need(r.page.evaluate("id => document.getElementById(id).contains(document.activeElement)", "sec-" + target["id"]), "focus was not moved into the weak objective's material")
    others = [o["id"] for o in m1["objectives"] if o["id"] != target["id"]]
    need(all("flagged" not in (r.page.get_attribute("#sec-" + o, "class") or "") for o in others), "an objective that was met is flagged too")
    r.view("map")
    need(r.node_state(m2["id"]) == "locked", "module 2 opened after a FAILED gate (state %s)" % r.node_state(m2["id"]))
    need(r.data()["modules"][m1["id"]]["gate"]["passed_on"] is None, "a failed gate was stored as passed")
    # the two neighbours of the pass mark
    n = len(m1["gate"]["items"])
    thr = r.course.get("gate_threshold", 80)
    need_n = math.ceil(n * thr / 100 - 1e-9)
    if need_n >= 1:
        r.answer_gate(m1, wrong_count=n - need_n + 1)
        need(not r.gate_passed(), "%d of %d passed, below the pass mark of %d" % (need_n - 1, n, need_n))
        r.view("map")
        need(r.node_state(m2["id"]) == "locked", "module 2 opened one item below the pass mark")
    r.answer_gate(m1, wrong_count=n - need_n)
    need(r.gate_passed(), "%d of %d did not pass, at the pass mark of %d" % (need_n, n, need_n))
    need(m2["title"] in r.text("#gate-result"), "the passed gate does not say what it opened")
    r.view("map")
    need(r.node_state(m2["id"]) in ("available", "progress"), "module 2 did not open after a passed gate (state %s)" % r.node_state(m2["id"]))
    need(r.node_state(m1["id"]) == "mastered", "module 1 is not shown as mastered")
    later = [m for m in r.course["modules"] if m2["id"] in m.get("prereqs", [])]
    need(all(r.node_state(m["id"]) == "locked" for m in later), "a module two steps on opened early")
    # a later failed attempt does not remove the pass
    r.answer_gate(m1, wrong_objectives={o["id"] for o in m1["objectives"]})
    r.view("map")
    need(r.node_state(m1["id"]) == "mastered" and r.node_state(m2["id"]) != "locked", "a failed retake removed an earlier pass")
    r.no_errors()
    return "locked, refused incomplete, failed on %s with link, %d of %d fails and %d of %d passes, module opened" % (target["id"], need_n - 1, n, need_n, n)


def t2_fading(T):
    r = T.rig().open()
    m = r.module(0)
    w = m["worked"][0]
    r.open_module(m["id"], "worked")
    box = '[data-worked="%s"] ' % w["id"]
    need(r.page.is_visible(box + '[data-pane="full"]') and not r.page.is_visible(box + '[data-pane="partial"]'), "the worked example should open at the full level")
    need(r.page.locator(box + '[data-pane="full"] input').count() == 0, "the full level has an input")
    for s in w["full"]["steps"]:
        need(s["result"] in r.text(box + '[data-pane="full"]'), "the full level does not show the result %r" % s["result"])
    r.page.click(box + '[data-level="partial"]')
    blanks = [s["blank"] for s in w["partial"]["steps"] if "blank" in s]
    need(r.page.locator(box + '[data-pane="partial"] input').count() == len(blanks), "the partial level should have %d blanks" % len(blanks))
    for b in blanks:
        need(b["answer"] not in [x.strip() for x in r.page.locator(box + '[data-pane="partial"] .result').all_inner_texts()], "a blank's answer is printed on the page")
    ids = ["#w-%s-p-f%d" % (w["id"], i) for i in range(len(blanks))]
    r.page.fill(ids[0], "no such answer")
    r.page.click(box + '[data-action="check-blanks"]')
    need("Not correct" in r.text(ids[0] + "-m"), "a wrong blank was not marked")
    need(r.page.get_attribute(ids[0], "aria-invalid") == "true", "a wrong blank is not marked invalid")
    need(not r.data()["modules"][m["id"]].get("worked"), "a wrong attempt was recorded as completing the level")
    for i, b in enumerate(blanks):
        r.page.fill(ids[i], "  " + b["answer"].upper() + " ")
    r.page.press(ids[-1], "Enter")
    need(all("Correct." == r.text(i + "-m").strip() for i in ids), "correct blanks were not all accepted")
    need(r.data()["modules"][m["id"]]["worked"][w["id"]]["partial"] == DAY0, "completing the partial level was not recorded")
    r.page.click(box + '[data-level="independent"]')
    sol = "#w-%s-i-solution" % w["id"]
    need(not r.page.is_visible(sol), "the independent level shows its solution before it is asked for")
    for s in w["independent"]["solution"]:
        need(not r.page.get_by_text(s["text"], exact=True).first.is_visible(), "a solution step is visible before it is asked for")
    answers = w["independent"]["answers"]
    r.page.fill("#w-%s-i-f0" % w["id"], "0")
    r.page.click(box + '[data-pane="independent"] [data-action="check-answers"]')
    need("Not correct" in r.text("#w-%s-i-f0-m" % w["id"]), "a wrong independent answer was not marked")
    need(not r.page.is_visible(sol), "checking a wrong answer revealed the solution")
    r.page.click(box + '[data-pane="independent"] [data-action="show-solution"]')
    need(r.page.is_visible(sol) and w["independent"]["solution"][-1]["result"] in r.text(sol), "the solution did not appear when asked for")
    for i, a in enumerate(answers):
        r.page.fill("#w-%s-i-f%d" % (w["id"], i), a["answer"])
    r.page.click(box + '[data-pane="independent"] [data-action="check-answers"]')
    need(r.data()["modules"][m["id"]]["worked"][w["id"]]["independent"] == DAY0, "completing the independent level was not recorded")
    r.no_errors()
    return "full shows %d steps, partial checked %d blanks, independent solution hidden until asked" % (len(w["full"]["steps"]), len(blanks))


def t3_feedback(T):
    r = T.rig().open()
    m = r.module(0)
    r.open_module(m["id"], "practice")
    shown = 0
    for it in m["quiz"]:
        need(not r.page.is_visible("#fb-" + it["id"]), "feedback is visible before any choice")
        for i, o in enumerate(it["options"]):
            r.page.check("#quiz-%s-%d" % (it["id"], i))
            fb = r.text("#fb-" + it["id"])
            need(plain(o["why"]) in fb, "option %d of %s did not show its own explanation; saw: %s" % (i + 1, it["id"], fb[:80]))
            need(("Correct." in fb) == bool(o["correct"]) and ("Not correct." in fb) == (not o["correct"]), "option %d of %s has the wrong verdict" % (i + 1, it["id"]))
            for j, other in enumerate(it["options"]):
                if j != i and plain(other["why"]) != plain(o["why"]):
                    need(plain(other["why"]) not in fb, "option %d of %s also shows the explanation of option %d" % (i + 1, it["id"], j + 1))
            shown += 1
    first = m["quiz"][0]
    rec = r.data()["modules"][m["id"]]["quiz"][first["id"]]
    need(rec["first"] == bool(first["options"][0]["correct"]), "the first choice was not the one recorded")
    r.no_errors()
    return "%d options across %d items each showed their own explanation" % (shown, len(m["quiz"]))


def clear_until(r, cid):
    """Grade whatever else is offered as Good until the wanted card is the one showing. False if it never shows."""
    guard = 0
    while r.review_card()[0] != cid:
        if r.review_card()[0] is None or guard > 600:
            return False
        r.grade(4)
        guard += 1
    return True


def t4_schedule(T):
    grades = [4, 5, 1, 3, 5, 4]
    r = T.rig().open(DAY0)
    r.view("review")
    cid, phase = r.review_card()
    need(cid and phase == "scheduled", "no card is offered for review on a fresh course")
    today, before, seen_drill = DAY0, None, 0
    for step, q in enumerate(grades):
        want = sm2_trace(grades[:step + 1], DAY0)[-1]
        need(want["on"] == today, "test bookkeeping: expected to review on %s, the trace says %s" % (today, want["on"]))
        r.open(today)
        r.view("review")
        clear_until(r, cid)
        need(r.review_card() == (cid, "scheduled"), "on %s the card %s should be due for a scheduled review; saw %s" % (today, cid, r.review_card()))
        r.grade(q)
        rec = r.data()["cards"][cid]
        got = (rec["interval"], rec["ef100"], rec["due"], rec["n"])
        need(got == (want["interval"], want["ef100"], want["due"], want["n"]),
             "after grades %s the page has interval %d, E-Factor %d, due %s, n %d; sm2.py has interval %d, E-Factor %d, due %s, n %d"
             % ((grades[:step + 1],) + got + (want["interval"], want["ef100"], want["due"], want["n"])))
        need(want["e_factor"] in r.text("#review-last") and want["due"] in r.text("#review-last"), "the page does not report the new due date and E-Factor")
        if q < 3:
            need(rec["interval"] == 1 and rec["due"] == (dt.date.fromisoformat(today) + dt.timedelta(days=1)).isoformat(), "a lapse did not reset the interval to 1 day")
            need(rec["ef100"] == before["ef100"], "a lapse changed the E-Factor from %d to %d" % (before["ef100"], rec["ef100"]))
        if q < 4:
            need(rec["again"] == today, "a card graded below Good is not marked to come back today")
            need(clear_until(r, cid), "the card graded %d never came back in the same session" % q)
            need(r.review_card() == (cid, "drill"), "the returning card is not marked as a repeat")
            frozen = json.dumps(r.data()["cards"][cid], sort_keys=True)
            r.grade(1)
            again = r.data()["cards"][cid]
            need(json.dumps(again, sort_keys=True) == frozen, "a same-day repeat graded Again changed the card's schedule")
            need(r.review_card() == (cid, "drill"), "a repeat graded Again did not come back")
            r.grade(4)
            after = r.data()["cards"][cid]
            need(after["again"] is None, "a repeat graded Good did not clear the card for today")
            need({k: v for k, v in after.items() if k != "again"} == {k: v for k, v in json.loads(frozen).items() if k != "again"}, "a same-day repeat graded Good changed the schedule")
            seen_drill += 1
        before = r.data()["cards"][cid]
        today = want["due"]
    # the card list in the module shows the same schedule
    owner = [m for m in r.course["modules"] if any(c["id"] == cid for c in m.get("cards", []))][0]
    r.open_module(owner["id"])
    r.page.click("#aside-cards")
    row = '[data-card-row="%s"]' % cid
    need(r.page.get_attribute(row, "data-due") == before["due"] and r.page.get_attribute(row, "data-ef") == "%d.%02d" % divmod(before["ef100"], 100), "the module's card list disagrees with the stored schedule")
    # clock moved backwards: nothing becomes un-due, nothing is recomputed
    r.open(before["due"])
    r.view("review")
    need(clear_until(r, cid), "the card is not due on its due date")
    frozen_all = json.dumps(r.data()["cards"], sort_keys=True)
    earlier = (dt.date.fromisoformat(before["due"]) - dt.timedelta(days=3)).isoformat()
    r.open(earlier)
    r.view("review")
    need(r.review_card()[0] == cid, "after the clock moved back 3 days, a card that was due stopped being due")
    need(json.dumps(r.data()["cards"], sort_keys=True) == frozen_all, "moving the clock backwards changed a schedule")
    need(r.page.get_attribute("#clock-note", "data-today") == before["due"] and "backwards" in r.text("#clock-note"), "the page does not explain the backwards clock")
    r.no_errors()
    # the test clock is read only on a page marked for testing: the same page without the mark ignores ?today=
    far = "2031-01-01"
    device_js = "(() => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); })()"
    p = T.rig("plain.html")
    p.page.goto(T.server.url("blank.html"))
    day_before = p.page.evaluate(device_js)
    p.open(far)
    shown, day_after = p.page.get_attribute("#clock-note", "data-today"), p.page.evaluate(device_js)
    need(shown != far, "a page that is not marked for testing obeyed ?today=%s" % far)
    need(shown in (day_before, day_after), "an unmarked page shows %s as today, and the device clock says %s" % (shown, day_after))
    need("Test clock" not in p.text("#clock-note"), "an unmarked page says a test clock is in use")
    p.no_errors()
    return "grades %s matched sm2.py at every step; %d same-day returns; backwards clock un-dued nothing; ?today= ignored without the test mark" % (grades, seen_drill)


def make_progress(r):
    m = r.module(0)
    r.answer_gate(m)
    need(r.gate_passed(), "could not pass the first gate to set up progress")
    r.open_module(m["id"], "practice")
    r.page.check("#quiz-%s-0" % m["quiz"][0]["id"])
    r.view("review")
    for q in (4, 5, 3, 1):
        if r.review_card()[0]:
            r.grade(q)
    return m


def t5_backup(T):
    r = T.rig().open()
    m = make_progress(r)
    before = r.data()
    raw_before = r.raw()
    need(before["cards"] and before["modules"][m["id"]]["gate"]["passed_on"] == DAY0, "set-up did not produce progress")
    need(r.page.get_attribute("#store-note", "data-store") == "local" and "Saved in this browser" in r.text("#store-note"), "the page does not say it is saving in this browser")
    r.open()
    need(r.raw() == raw_before, "reloading the page changed the stored progress")
    need(r.node_state(m["id"]) == "mastered", "progress was not restored after a reload")
    exported = r.export_text()
    env = json.loads(exported)
    need(env["app"] == "preceptor-course" and env["schema"] == 1 and env["content_id"] == "%s@%d" % (r.course["id"], r.course["version"]) and env["data"] == before,
         "the exported envelope does not hold the stored progress")
    need(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", env["saved_at"]) is not None, "saved_at is not an ISO 8601 UTC time")
    # fresh profile, pasted text
    r2 = T.rig().open()
    need(r2.data() is None or not r2.data()["cards"], "the fresh profile is not fresh")
    result, msg = r2.try_import(exported)
    need(result == "done", "a valid backup was not imported into a fresh page: " + msg)
    need(r2.data() == before, "progress after import differs from the progress exported")
    r2.view("map")
    need(r2.node_state(m["id"]) == "mastered", "the imported gate pass is not shown")
    # fresh profile, chosen file
    r3 = T.rig().open()
    r3.view("backup")
    path = Path(T.tmp) / ("backup-%d.json" % T.size[0])
    path.write_text(exported, encoding="utf-8")
    r3.page.set_input_files("#import-file", str(path))
    r3.page.wait_for_function("document.getElementById('import-text').value.length > 20")
    r3.page.click("#import-go")
    need(r3.page.get_attribute("#import-msg", "data-result") == "done" and r3.data() == before, "import from a chosen file did not reproduce the progress")
    # undo of an import
    r3.page.click("#undo-go")
    need(not r3.data()["cards"], "undoing the import did not bring back the earlier (empty) progress")
    # storage refused: the page still works, says so, and can export and import
    block = "Object.defineProperty(window, 'localStorage', {get: function () { throw new Error('refused'); }});"
    r4 = T.rig(init_script=block).open()
    need(r4.page.get_attribute("#store-note", "data-store") == "memory" and "Not saved" in r4.text("#store-note"), "with storage refused the page does not say it is not saving")
    r4.answer_gate(r4.module(0))
    need(r4.gate_passed(), "with storage refused the gate could not be passed")
    out = r4.export_text()
    need(json.loads(out)["data"]["modules"][m["id"]]["gate"]["passed_on"] == DAY0, "with storage refused the export does not hold the progress")
    result, msg = r4.try_import(exported)
    need(r4.page.query_selector("#import-confirm") is not None, "an import over existing progress did not ask first")
    r4.page.click("#import-confirm-go")
    need(json.loads(r4.export_text())["data"] == before, "with storage refused the import did not replace the progress")
    # a host storage object (window.storage with get and set) is used before browser storage, and the page says so
    host = ("window.storage = {get: function (k) { return Promise.resolve(window.localStorage.getItem('host:' + k)); },"
            " set: function (k, v) { window.localStorage.setItem('host:' + k, v); return Promise.resolve(true); }};")
    r5 = T.rig(init_script=host).open()
    need(r5.page.get_attribute("#store-note", "data-store") == "host" and "Saved by the app" in r5.text("#store-note"), "with a host storage object present the page does not say it is using it")
    r5.answer_gate(r5.module(0))
    held = r5.page.evaluate("k => window.localStorage.getItem('host:' + k)", r5.key())
    need(held is not None and json.loads(held)["data"]["modules"][m["id"]]["gate"]["passed_on"] == DAY0, "the host storage object was not given the progress")
    need(r5.raw() is None, "progress was written to browser storage although a host storage object was in use")
    r5.open()
    need(r5.node_state(m["id"]) == "mastered", "progress held by the host storage object was not restored on reload")
    # a host storage object that refuses to write: the page falls back to browser storage and keeps working
    failing = "window.storage = {get: function () { return Promise.resolve(null); }, set: function () { return Promise.reject(new Error('host refused')); }};"
    r6 = T.rig(init_script=failing).open()
    r6.answer_gate(r6.module(0))
    need(r6.gate_passed(), "with a failing host storage object the gate could not be passed")
    need(r6.page.get_attribute("#store-note", "data-store") == "local" and r6.raw() is not None and json.loads(r6.raw())["data"]["modules"][m["id"]]["gate"]["passed_on"] == DAY0,
         "when the host storage object refused a write the page did not fall back to browser storage")
    for x in (r, r2, r3, r4, r5, r6):
        x.no_errors()
    return "reload kept %d card schedules; paste and file import reproduced them exactly; storage refused still works; a host storage object is used first and survives its own failure" % len(before["cards"])


def t6_imports(T):
    r = T.rig().open()
    m = make_progress(r)
    good = r.export_text()
    env = json.loads(good)
    raw0 = r.raw()
    other = T.rig(name="other.html").open()
    other.answer_gate(other.module(0))
    foreign = other.export_text()
    other.close()

    def variant(change):
        e = copy.deepcopy(env)
        change(e)
        return json.dumps(e)

    first_card = sorted(env["data"]["cards"])[0]
    bad = [
        ("another course's backup", foreign, "other-course"),
        ("a newer schema", variant(lambda e: e.update(schema=2)), "newer-schema"),
        ("malformed text", "{this is not json", "not-json"),
        ("a truncated file", good[: len(good) // 2], "not-json"),
        ("an empty paste", "   ", "empty"),
        ("a different app's file", variant(lambda e: e.update(app="some-other-app")), "wrong-app"),
        ("a newer version of this course", variant(lambda e: (e.update(content_id="%s@%d" % (r.course["id"], r.course["version"] + 1)), e["data"].update(course_version=r.course["version"] + 1))), "newer-course"),
        ("a card with a text E-Factor", variant(lambda e: e["data"]["cards"][first_card].update(ef100="250")), "bad-data"),
        ("a card with interval 0", variant(lambda e: e["data"]["cards"][first_card].update(interval=0)), "bad-data"),
        ("JSON that is a list", "[1, 2, 3]", "not-object"),
        ("an unknown module id under the same version", variant(lambda e: e["data"]["modules"].update({"no-such-module": {}})), "bad-data"),
    ]
    for label, text, code in bad:
        result, msg = r.try_import(text)
        need(result == "refused", "%s was not refused (%s)" % (label, msg[:80]))
        need(r.page.get_attribute("#import-msg", "data-code") == code, "%s was refused for the wrong reason: %s" % (label, r.page.get_attribute("#import-msg", "data-code")))
        need("Nothing was changed" in msg, "%s: the refusal does not say nothing was changed" % label)
        need(r.raw() == raw0, "%s CHANGED the stored progress" % label)
        need(r.page.query_selector("#import-confirm") is None, "%s was offered for confirmation" % label)
    need(json.loads(r.export_text())["data"] == env["data"], "the progress in the page changed after the refused imports")
    r.view("map")
    need(r.node_state(m["id"]) == "mastered", "the mastered module was lost after the refused imports")
    # the valid neighbour: the largest allowed E-Factor floor and a normal backup are accepted
    edge = variant(lambda e: e["data"]["cards"][first_card].update(ef100=130, interval=36500))
    result, msg = r.try_import(edge)
    need(result == "pending" and r.page.query_selector("#import-confirm") is not None, "a valid backup (E-Factor 1.30, interval 36500) was not offered for import: " + msg)
    r.page.click("#import-cancel")
    need(r.raw() == raw0, "cancelling an import changed the stored progress")
    r.try_import(edge)
    r.page.click("#import-confirm-go")
    need(r.data()["cards"][first_card]["ef100"] == 130, "the confirmed import was not applied")
    r.page.click("#undo-go")
    need(r.data() == env["data"], "undo did not restore the progress from before the import")
    # an older version of the same course is mapped by id, and the unmatched are named
    v2 = T.rig(name="v2.html").open()
    result, msg = v2.try_import(good)
    need(v2.page.query_selector("#import-confirm") is not None, "a backup from an older version was not offered for mapping: " + msg)
    listing = v2.text("#import-confirm")
    need(T.renamed in listing, "the mapping report does not name the unmatched objective %s" % T.renamed)
    if T.removed_card in env["data"]["cards"]:
        need(T.removed_card in listing, "the mapping report does not name the removed card %s" % T.removed_card)
    need(v2.data() is None or not v2.data()["cards"], "the older backup was applied before it was confirmed")
    v2.page.click("#import-confirm-go")
    d2 = v2.data()
    need(d2["course_version"] == v2.course["version"] and T.renamed not in d2["objectives"] and T.removed_card not in d2["cards"], "unmatched entries were carried into the new version")
    need(d2["modules"][m["id"]]["gate"]["passed_on"] == DAY0 and len(d2["cards"]) >= len(env["data"]["cards"]) - 1, "matched progress was lost in the mapping")
    # stored progress from an older version, met at load
    v2b = T.rig(name="v2.html")
    v2b.page.goto(T.server.url("blank.html"))
    v2b.page.evaluate("([k, v]) => localStorage.setItem(k, v)", ["preceptor:" + r.course["id"], good])
    v2b.open()
    need(v2b.page.query_selector("#notice") is not None and T.renamed in v2b.text("#notice"), "stored progress from an older version was mapped without a report")
    need(v2b.page.evaluate("k => localStorage.getItem(k)", "preceptor:%s@v%d" % (r.course["id"], r.course["version"])) == good, "the older stored record was not kept beside the mapped one")
    # unreadable stored data is left exactly as it was
    for junk in ("%%% not a backup %%%", good[:200]):
        h = T.rig()
        h.page.goto(T.server.url("blank.html"))
        h.page.evaluate("([k, v]) => localStorage.setItem(k, v)", ["preceptor:" + r.course["id"], junk])
        h.open()
        need(h.page.get_attribute("#store-note", "data-store") == "held" and h.page.query_selector("#hold-replace") is not None, "unreadable stored data did not put saving on hold")
        h.open_module(h.module(0)["id"], "visual")
        need(h.raw() == junk, "unreadable stored data was overwritten")
        h.view("backup")
        need(h.page.input_value("#rescue-text") == junk, "the unreadable stored text is not offered for copying")
        h.close()
    for x in (r, v2, v2b):
        x.no_errors()
    return "%d bad backups refused with storage byte-identical; valid neighbour accepted, cancelled, confirmed, undone; older version mapped with %s reported" % (len(bad), T.renamed)


def t7_mastery(T):
    r = T.rig().open()
    m = r.module(0)
    base = r.progress_numbers()
    need(base["points"] == 0 and base["objectives"].startswith("0 of") and base["modules"].startswith("0 of"), "a fresh course does not start at zero: %s" % base)
    r.open_module(m["id"])
    for tab in ("theory", "visual", "worked", "practice"):
        r.page.click("#tab-" + tab)
    after_tabs = r.progress_numbers()
    need(after_tabs["points"] > base["points"], "reading the four parts did not raise activity")
    r.open_module(m["id"], "practice")
    for it in m["quiz"]:
        right = [i for i, o in enumerate(it["options"]) if o["correct"]][0]
        r.page.check("#quiz-%s-%d" % (it["id"], right))
    r.page.click("#tab-worked")
    w = m["worked"][0]
    r.page.click('[data-worked="%s"] [data-level="partial"]' % w["id"])
    for i, b in enumerate([s["blank"] for s in w["partial"]["steps"] if "blank" in s]):
        r.page.fill("#w-%s-p-f%d" % (w["id"], i), b["answer"])
    r.page.click('[data-worked="%s"] [data-action="check-blanks"]' % w["id"])
    after_practice = r.progress_numbers()
    need(after_practice["points"] > after_tabs["points"], "practice and worked examples did not raise activity")
    r.view("review")
    reviewed = 0
    while r.review_card()[0] and reviewed < 400:
        r.grade(5)
        reviewed += 1
    need(reviewed >= len(m["cards"]), "not every card of the open module could be reviewed")
    after_cards = r.progress_numbers()
    need(after_cards["points"] > after_practice["points"], "reviewing cards did not raise activity")
    need(after_cards["objectives"] == base["objectives"] and after_cards["modules"] == base["modules"], "activity raised mastery: %s became %s" % (base, after_cards))
    need("effort" in r.text("#activity").lower() and "demonstrated" in r.text("#mastery").lower(), "the two sections are not labelled as different things")
    d = r.data()
    need(not any(o.get("demonstrated_on") or o.get("gate") for o in d["objectives"].values()), "an objective is marked demonstrated without a gate")
    need(not any((x.get("gate") or {}).get("passed_on") for x in d["modules"].values()), "a module is marked mastered without a gate")
    r.view("map")
    dep = [x for x in r.course["modules"] if m["id"] in x.get("prereqs", [])][0]
    need(r.node_state(dep["id"]) == "locked", "effort alone opened the next module")
    r.answer_gate(m)
    final = r.progress_numbers()
    need(final["objectives"].startswith("%d of" % len(m["objectives"])) and final["modules"].startswith("1 of"), "a passed gate did not raise mastery: %s" % final)
    # evidence is dated and never fades: old evidence is listed as due for a check on the stated day, and the totals do not move
    after = r.course.get("check_after_days", 30)

    def listed(days_on):
        r.open((dt.date.fromisoformat(DAY0) + dt.timedelta(days=days_on)).isoformat())
        r.view("progress")
        return sorted(e.get_attribute("data-check-objective") for e in r.page.query_selector_all("[data-check-objective]"))
    early = listed(after - 1)
    need(early == [], "%d days after the evidence (one short of %d) these objectives are already listed for a check: %s" % (after - 1, after, early))
    need(r.page.locator("#check-none").count() == 1, "with nothing due for a check the page does not say so")
    on_day = listed(after)
    need(on_day == sorted(o["id"] for o in m["objectives"]), "%d days after the evidence the objectives due for a check are %s, expected the %d demonstrated ones" % (after, on_day, len(m["objectives"])))
    need(DAY0 in r.text('[data-check-objective="%s"]' % m["objectives"][0]["id"]), "an objective due for a check does not show the date of its evidence")
    later = r.progress_numbers()
    need(later["objectives"] == final["objectives"] and later["modules"] == final["modules"], "mastery changed with the passing of time: %s became %s" % (final, later))
    r.no_errors()
    return "activity %d to %d points with mastery fixed at %s; the gate then gave %s; due for a check at %d days and not at %d" % (
        base["points"], after_cards["points"], base["objectives"], final["objectives"], after, after - 1)


def t8_planned(T):
    r = T.rig(name="planned.html").open()
    c = r.course
    planned = [m for m in c["modules"] if m["status"] == "planned"]
    ready = [m for m in c["modules"] if m["status"] == "ready"]
    need(planned, "the planned-module page has no planned module")
    for p in planned:
        sel = '[data-module="%s"]' % p["id"]
        need(r.node_state(p["id"]) == "planned" and "Not yet written" in r.text(sel), "a planned module is not shown as not yet written")
        need(r.page.get_attribute(sel, "aria-disabled") == "true", "a planned module is not marked unavailable")
        r.page.click(sel, force=True)
        need(r.page.query_selector("#lesson-h") is None, "a planned module was opened")
        need("not yet written" in r.text("#map-msg"), "clicking a planned module gave no explanation")
    need("of %d written module" % len(ready) in r.text("#map-totals") and "%d more" % len(planned) in r.text("#map-totals"), "map totals do not exclude planned modules: " + r.text("#map-totals"))
    nums = r.progress_numbers()
    objectives = sum(len(m["objectives"]) for m in ready)
    need(nums["modules"] == "0 of %d" % len(ready) and nums["objectives"] == "0 of %d" % objectives, "progress totals count planned modules: %s" % nums)
    need("planned" in r.text("#mastery"), "the progress page does not mention the planned modules it left out")
    r.view("sheets")
    need("not yet written" in r.text("#sheet-list"), "the cheat sheets do not mark the planned module")
    need(not any(k in json.dumps(r.page.content()) for k in ("lorem ipsum", "content goes here")), "placeholder text is on the page")
    # mastering everything written still leaves the planned module shut and uncounted
    r.view("map")
    for m in ready:
        if r.node_state(m["id"]) == "locked":
            continue
        r.answer_gate(m)
        r.view("map")
    done = sum(1 for m in ready if r.node_state(m["id"]) == "mastered")
    need(all(r.node_state(p["id"]) == "planned" for p in planned), "a planned module changed state")
    need(r.progress_numbers()["modules"] == "%d of %d" % (done, len(ready)), "totals changed their base after gates were passed")
    r.no_errors()
    return "%d planned of %d modules: not openable, totals over %d written modules and %d objectives" % (len(planned), len(c["modules"]), len(ready), objectives)


def t9_display(T):
    r = T.rig().open()
    r.view("display")
    root = "document.documentElement"

    def attr(name):
        return r.page.evaluate("n => document.documentElement.getAttribute(n)", name)

    def bg():
        return r.page.evaluate("getComputedStyle(document.body).backgroundColor")

    def font():
        return r.page.evaluate("parseFloat(getComputedStyle(%s).fontSize)" % root)

    def pad():
        return r.page.evaluate("getComputedStyle(%s).getPropertyValue('--pad').trim()" % root)

    need(attr("data-theme") == "study" and bg() == "rgb(251, 247, 239)", "the default theme is not Warm Study on cream paper (found %s, %s)" % (attr("data-theme"), bg()))
    seen = {bg()}
    themes = [b.get_attribute("data-theme-choice") for b in r.page.query_selector_all("[data-theme-choice]")]
    need(len(themes) >= 4, "fewer than four themes are offered")
    for t in themes[1:]:
        r.page.click('[data-theme-choice="%s"]' % t)
        need(attr("data-theme") == t and r.page.get_attribute('[data-theme-choice="%s"]' % t, "aria-pressed") == "true", "theme %s did not apply or does not show as selected" % t)
        need(bg() not in seen, "theme %s has the same background as another theme" % t)
        seen.add(bg())
        need(r.page.evaluate("document.activeElement && document.activeElement.getAttribute('data-theme-choice')") == t, "focus was lost when the theme changed")
    f0 = font()
    r.page.click('[data-size-choice="larger"]')
    need(font() > f0 * 1.2, "the larger text size did not enlarge the text")
    r.page.click('[data-size-choice="large"]')
    need(f0 * 1.05 < font() < f0 * 1.2, "the large text size is not between standard and larger")
    p0 = pad()
    r.page.click('[data-density-choice="compact"]')
    need(pad() != p0, "compact spacing changed nothing")
    r.page.click('[data-motion-choice="reduced"]')
    need(attr("data-motion") == "reduced" and r.page.evaluate("getComputedStyle(%s).getPropertyValue('--ease').trim()" % root) in ("0ms", "0s"), "motion off still leaves transitions on")
    r.page.click('[data-motion-choice="full"]')
    need(r.page.evaluate("getComputedStyle(%s).getPropertyValue('--ease').trim()" % root) not in ("0ms", "0s"), "motion on leaves transitions off")
    chosen = {k: attr("data-" + k) for k in ("theme", "size", "density", "motion")}
    r.open()
    need({k: attr("data-" + k) for k in chosen} == chosen, "display choices did not survive a reload")
    r.view("display")
    need(r.page.get_attribute('[data-theme-choice="%s"]' % chosen["theme"], "aria-pressed") == "true", "the remembered theme does not show as selected")
    r.page.click("#display-reset")
    defaults = {"theme": "study", "size": "standard", "density": "comfortable", "motion": "auto"}
    need({k: attr("data-" + k) for k in defaults} == defaults and bg() == "rgb(251, 247, 239)", "reset did not restore the defaults")
    r.open()
    need({k: attr("data-" + k) for k in defaults} == defaults, "the reset did not survive a reload")
    block = "Object.defineProperty(window, 'localStorage', {get: function () { throw new Error('refused'); }});"
    r2 = T.rig(init_script=block).open()
    r2.view("display")
    r2.page.click('[data-theme-choice="%s"]' % themes[1])
    need(r2.page.evaluate("document.documentElement.getAttribute('data-theme')") == themes[1] and "last for this visit" in r2.text("#display-note"), "with storage refused the theme did not apply or the page did not say it will not persist")
    r.no_errors()
    r2.no_errors()
    return "%d themes, 3 text sizes, 2 spacings, 3 motion settings applied; persisted; reset" % len(themes)


def t10_scale(T):
    r = T.rig(name="big.html").open()
    c = r.course
    data = {"course_version": 1, "day_high": DAY0, "modules": {}, "objectives": {}, "cards": {},
            "activity": {"points": 5000, "days": {(dt.date.fromisoformat(DAY0) - dt.timedelta(days=k)).isoformat(): 1 + k % 9 for k in range(80)},
                         "counts": {"tabs": 112, "quiz": 56, "worked": 56, "gates": 40, "cards": 900}}}
    for i, m in enumerate(c["modules"]):
        data["modules"][m["id"]] = {"tabs": {t: DAY0 for t in ("theory", "visual", "worked", "practice")},
                                    "gate": {"attempts": 1 + i % 3, "passed_on": DAY0, "last": {"date": DAY0, "correct": 5, "total": 5, "passed": True}}}
        for o in m["objectives"]:
            data["objectives"][o["id"]] = {"demonstrated_on": DAY0, "gate": [2, 2, DAY0], "recalled_on": None, "misses": {"gate": i % 2, "quiz": 0, "cards": i % 3}}
        for k, card in enumerate(m["cards"]):
            data["cards"][card["id"]] = {"n": 2 + k % 4, "interval": 6 + 3 * k, "ef100": 130 + 10 * ((i + k) % 15), "due": (dt.date.fromisoformat(DAY0) + dt.timedelta(days=(k % 7) - 2)).isoformat(),
                                         "last": DAY0, "reviews": 3 + k, "lapses": k % 2, "again": None}
    text = json.dumps({"app": "preceptor-course", "schema": 1, "content_id": "%s@1" % c["id"], "saved_at": "2026-10-09T00:00:00Z", "data": data})
    result, msg = r.try_import(text)
    need(result == "done", "a large valid backup was refused: " + msg)
    need(r.data() == data, "the large backup was not stored exactly")
    r.view("map")
    need(r.page.locator(".node").count() == len(c["modules"]) and r.page.locator('.node[data-state="mastered"]').count() == len(c["modules"]), "not every module of the large course is drawn as mastered")
    need(r.page.locator("svg.links path.open").count() >= len(c["modules"]) - 1, "the large map is missing its connectors")
    need(r.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "the large map overflows sideways")
    for v in ("review", "progress", "sheets"):
        r.view(v)
        need(r.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "the %s screen overflows sideways with large state" % v)
    again = json.loads(r.export_text())
    need(again["data"] == data, "export after a large import does not round-trip")
    r2 = T.rig(name="big.html").open()
    result, msg = r2.try_import(json.dumps(again))
    need(result == "done" and r2.data() == data, "the large export did not import into a fresh profile")
    r.no_errors()
    return "%d modules, %d card schedules, %d characters of backup round-tripped" % (len(c["modules"]), len(data["cards"]), len(text))


def t11_layout(T):
    widths = [360, 390] if T.size[0] < 700 else [1280]
    screens = 0
    for w in widths:
        r = T.rig(size=(w, 800)).open()
        m = r.module(0)

        def fits(where, tables=True):
            over = r.page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            need(over <= 0, "%s overflows sideways by %d pixels at %d wide" % (where, over, w))
            clipped = r.page.evaluate("""() => Array.from(document.querySelectorAll('button, .n-title, legend, h1, h2, h3, th, td'))
                .filter(e => e.offsetParent !== null && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1 && !e.closest('.tablewrap')).map(e => e.textContent.trim().slice(0, 30))""")
            need(not clipped, "%s has cut-off text at %d wide: %s" % (where, w, clipped[:3]))
            wide = r.page.evaluate("""() => Array.from(document.querySelectorAll('.tablewrap')).filter(e => e.offsetParent !== null && e.scrollWidth > e.clientWidth + 1)
                .map(e => (e.querySelector('th') || e).textContent.trim().slice(0, 24) + ' (' + e.scrollWidth + ' in ' + e.clientWidth + ')')""")
            need(not (tables and wide), "%s has a table wider than the screen at %d wide: %s" % (where, w, wide[:3]))
            return 1
        screens += fits("the map")
        r.open_module(m["id"])
        for tab in ("theory", "visual", "worked", "practice", "gate"):
            r.page.click("#tab-" + tab)
            screens += fits("the %s tab" % tab)
        r.page.click("#aside-sheet")
        screens += fits("the cheat sheet")
        r.page.click("#aside-cards")
        screens += fits("the card list")
        r.answer_gate(m, wrong_objectives={m["objectives"][0]["id"]})
        screens += fits("the failed gate")
        for v in ("review", "sheets", "progress", "backup", "display"):
            r.view(v)
            screens += fits("the %s screen" % v)
        r.view("review")
        r.page.click("#show-answer")
        screens += fits("the review screen with the answer shown")
        r.view("backup")
        r.page.click("#export-go")
        r.page.click("#reset-go")
        screens += fits("the backup screen with export and reset open")
        # every other written module: open them all by import, then walk their parts
        data = {"course_version": r.course["version"], "day_high": DAY0, "modules": {}, "objectives": {}, "cards": {},
                "activity": {"points": 0, "days": {}, "counts": {"tabs": 0, "quiz": 0, "worked": 0, "gates": 0, "cards": 0}}}
        for x in r.course["modules"]:
            if x["status"] == "ready":
                data["modules"][x["id"]] = {"gate": {"attempts": 1, "passed_on": DAY0, "last": {"date": DAY0, "correct": 1, "total": 1, "passed": True}}}
        r.try_import(json.dumps({"app": "preceptor-course", "schema": 1, "content_id": "%s@%d" % (r.course["id"], r.course["version"]), "saved_at": "2026-10-09T00:00:00Z", "data": data}))
        if r.page.query_selector("#import-confirm-go"):
            r.page.click("#import-confirm-go")
        for x in r.course["modules"][1:]:
            if x["status"] != "ready":
                continue
            r.open_module(x["id"], "theory")
            for tab in ("theory", "visual", "worked", "practice", "gate"):
                r.page.click("#tab-" + tab)
                if tab == "worked":
                    for lv in ("partial", "independent"):
                        for b in r.page.query_selector_all('[data-level="%s"]' % lv):
                            b.click()
                        screens += fits("the worked tab of %s at the %s level" % (x["id"], lv))
                screens += fits("the %s tab of %s" % (tab, x["id"]))
        r.view("sheets")
        screens += fits("all the cheat sheets")
        r.page.evaluate("document.documentElement.setAttribute('data-size', 'larger')")
        for x in r.course["modules"]:
            if x["status"] == "ready":
                r.open_module(x["id"], "visual")
                # at the largest text size a wide grid may scroll inside its own frame; the page itself must still not
                screens += fits("the visual tab of %s at the largest text size" % x["id"], tables=False)
        r.view("map")
        screens += fits("the map at the largest text size")
        r.no_errors()
        r.close()
    return "%d screens at %s wide with no sideways overflow or cut-off labels" % (screens, " and ".join(str(w) for w in widths))


def t12_frame(T):
    r = T.rig()
    r.page.goto(T.server.url("frame.html"))
    f = r.page.frame_locator("#f")
    f.locator("#map").wait_for(timeout=8000)
    need("Not saved" in f.locator("#store-note").inner_text(), "inside the sandboxed frame the page does not say it cannot save")
    course = json.loads((Path(T.tmp) / "course.json").read_text(encoding="utf-8"))
    m = course["modules"][0]
    f.locator('[data-module="%s"]' % m["id"]).click()
    f.locator("#tab-gate").click()
    for it in m["gate"]["items"]:
        right = [i for i, o in enumerate(it["options"]) if o["correct"]][0]
        f.locator("#gate-%s-%d" % (it["id"], right)).check()
    f.locator("#gate-submit").click()
    need(f.locator("#gate-result").get_attribute("data-passed") == "true", "the gate could not be passed inside the sandboxed frame")
    f.locator("#nav-backup").click()
    f.locator("#export-go").click()
    exported = f.locator("#export-text").input_value()
    need(json.loads(exported)["data"]["modules"][m["id"]]["gate"]["passed_on"], "the export inside the frame does not hold the progress")
    f.locator("#export-copy").click()
    f.locator("#export-msg").get_by_text("Cop").wait_for(timeout=4000)
    copied = f.locator("#export-msg").inner_text()
    need("refused" in copied or "Copied" in copied, "copy inside the frame gave no usable message: " + copied)
    f.locator("#export-download").click()
    need("download" in f.locator("#export-msg").inner_text().lower(), "download inside the frame gave no message")
    f.locator("#reset-go").click()
    f.locator("#reset-confirm-go").click()
    f.locator("#nav-map").click()
    need(f.locator('[data-module="%s"]' % m["id"]).get_attribute("data-state") != "mastered", "reset inside the frame did not clear progress")
    f.locator("#nav-backup").click()
    f.locator("#import-text").fill(exported)
    f.locator("#import-go").click()
    if f.locator("#import-confirm-go").count():
        f.locator("#import-confirm-go").click()
    f.locator("#nav-map").click()
    need(f.locator('[data-module="%s"]' % m["id"]).get_attribute("data-state") == "mastered", "import inside the frame did not restore progress")
    r.errors = [e for e in r.errors if "Clipboard API has been blocked" not in e]   # the browser's own note that the frame refused the clipboard
    r.no_errors()
    return "gate, export, reset and import all worked inside a sandboxed frame with storage refused"


def t13_visuals(T):
    r = T.rig().open()
    drawn, kinds = 0, set()
    # open every module by importing a state in which every gate is passed
    data = {"course_version": r.course["version"], "day_high": DAY0, "modules": {}, "objectives": {}, "cards": {},
            "activity": {"points": 0, "days": {}, "counts": {"tabs": 0, "quiz": 0, "worked": 0, "gates": 0, "cards": 0}}}
    for m in r.course["modules"]:
        if m["status"] == "ready":
            data["modules"][m["id"]] = {"gate": {"attempts": 1, "passed_on": DAY0, "last": {"date": DAY0, "correct": 1, "total": 1, "passed": True}}}
    env = {"app": "preceptor-course", "schema": 1, "content_id": "%s@%d" % (r.course["id"], r.course["version"]), "saved_at": "2026-10-09T00:00:00Z", "data": data}
    result, msg = r.try_import(json.dumps(env))
    need(result == "done", "could not open every module for the visual test: " + msg)
    for m in r.course["modules"]:
        if m["status"] != "ready":
            continue
        need(m.get("visuals"), "module %s has no visual" % m["id"])
        r.open_module(m["id"], "visual")
        for v in m["visuals"]:
            fig = "#vis-" + v["id"]
            need(r.page.query_selector(fig) is not None, "visual %s was not drawn" % v["id"])
            need(r.page.locator(fig + " .msg.bad").count() == 0, "visual %s shows an error: %s" % (v["id"], r.page.locator(fig + " .msg.bad").first.inner_text() if r.page.locator(fig + " .msg.bad").count() else ""))
            kinds.add(v["type"])
            drawn += 1
            if v["type"] == "slider":
                env_v = {p["name"]: p["value"] for p in v["params"]}
                p = v["params"][0]
                target = p["min"] if p["value"] != p["min"] else p["max"]
                r.page.evaluate("([sel, val]) => { const i = document.querySelector(sel); i.value = val; i.dispatchEvent(new Event('input', {bubbles: true})); }", ["%s [data-param='%s']" % (fig, p["name"]), str(target)])
                env_v[p["name"]] = target
                for i, o in enumerate(v["outputs"]):
                    want = (o.get("join", " ").join(vc.format_value(vc.formula_eval(f, env_v), o.get("format", "int")) for f in o["parts"]) if "parts" in o
                            else vc.format_value(vc.formula_eval(o["formula"], env_v), o.get("format", "int")))
                    got = r.text("%s [data-output='%d'] span" % (fig, i)).strip()
                    need(got.split(" ")[0] == want or got == want + (" " + o["unit"] if o.get("unit") else ""), "slider %s output %d shows %r where the formula gives %r" % (v["id"], i + 1, got, want))
                if v.get("strip"):
                    need(r.page.locator(fig + " .strip .cell").count() == v["strip"]["cells"], "slider %s strip has the wrong number of cells" % v["id"])
            elif v["type"] == "number-line":
                p = v["point"]
                env_v = {p["name"]: p["value"]}
                if v.get("choice"):
                    opt = [o for o in v["choice"]["options"] if o["value"] != v["choice"]["value"]][0]
                    r.page.click("%s [data-choice='%s']" % (fig, str(opt["value"])))
                    env_v[v["choice"]["name"]] = opt["value"]
                top = p.get("max", v["max"])
                r.page.evaluate("([sel, val]) => { const i = document.querySelector(sel); i.value = val; i.dispatchEvent(new Event('input', {bubbles: true})); }", ["%s [data-param='%s']" % (fig, p["name"]), str(top)])
                env_v[p["name"]] = top
                for i, o in enumerate(v["readouts"]):
                    want = (o.get("join", " ").join(vc.format_value(vc.formula_eval(f, env_v), o.get("format", "int")) for f in o["parts"]) if "parts" in o
                            else vc.format_value(vc.formula_eval(o["formula"], env_v), o.get("format", "int")))
                    need(r.text("%s [data-output='%d'] span" % (fig, i)).strip().startswith(want), "number line %s readout %d disagrees with its formula" % (v["id"], i + 1))
                need(r.page.locator(fig + " .nl .pt").count() == 1, "number line %s has no marker" % v["id"])
            elif v["type"] == "table-builder":
                cells = [(ri, c) for ri in range(len(v["rows"])) for c in v["columns"] if not c.get("given")]
                ri, c = cells[0]
                r.page.fill("%s [data-cell='%d-%s']" % (fig, ri, c["key"]), "-99999")
                r.page.click(fig + " [data-action='check-table']")
                need("not correct" in r.text(fig) and r.text("%s-msg" % fig).startswith("0 of"), "table %s accepted a wrong cell" % v["id"])
                for ri, c in cells:
                    r.page.fill("%s [data-cell='%d-%s']" % (fig, ri, c["key"]), vc.format_value(vc.formula_eval(c["formula"], v["rows"][ri]), c.get("format", "int")))
                r.page.click(fig + " [data-action='check-table']")
                need("All %d cells correct" % len(cells) in r.text("%s-msg" % fig), "table %s did not accept the computed answers: %s" % (v["id"], r.text("%s-msg" % fig)))
            elif v["type"] == "steps":
                n = len(v["steps"])
                for k in range(1, n + 1):
                    need(r.page.get_attribute(fig + " [data-step-now]", "data-step-now") == str(k), "steps %s is not at step %d" % (v["id"], k))
                    need(plain(v["steps"][k - 1]["caption"]) in r.text(fig + "-cap"), "steps %s shows the wrong caption at step %d" % (v["id"], k))
                    if k < n:
                        r.page.click(fig + " [data-step='next']")
                r.page.click(fig + " [data-step='next']", force=True)
                need(r.page.get_attribute(fig + " [data-step-now]", "data-step-now") == str(n), "steps %s ran past its last step" % v["id"])
                r.page.click(fig + " [data-step='back']")
                need(r.page.get_attribute(fig + " [data-step-now]", "data-step-now") == str(n - 1), "steps %s did not go back" % v["id"])
            elif v["type"] == "compare":
                r.page.click(fig + " [data-cmp='1']")
                need(r.page.locator(fig + " .side").count() == 1 and v["states"][1]["name"] in r.text(fig + " .side"), "compare %s did not show the second state alone" % v["id"])
                r.page.click(fig + " [data-cmp='both']")
                need(r.page.locator(fig + " .side").count() == 2, "compare %s did not show both states" % v["id"])
            elif v["type"] == "custom" and r.page.locator(fig + " [data-bit]").count() == 8:
                for bits in ("00000000", "11111111", "10101100", "01001101"):
                    now = r.text(fig + " [data-bits-out='binary']").strip()
                    for i in range(8):
                        if now[i] != bits[i]:
                            r.page.click("%s [data-bit='%d']" % (fig, i))
                    need(r.text(fig + " [data-bits-out='binary']").strip() == bits and r.text(fig + " [data-bits-out='decimal']").strip() == str(int(bits, 2)),
                         "the bit toggles show %s for %s" % (r.text(fig + " [data-bits-out='decimal']"), bits))
    r.no_errors()
    return "%d visuals of %d kinds drew and responded (%s)" % (drawn, len(kinds), ", ".join(sorted(kinds)))


def t14_broken(T):
    r = T.rig(name="cycle.html")
    r.page.goto(T.server.url("cycle.html", DAY0))
    r.page.wait_for_selector("#fatal")
    need("cycle" in r.text("#fatal") and "Nothing was saved" in r.text("#fatal"), "a course with a prerequisite cycle did not stop with an explanation: " + r.text("#fatal")[:120])
    need(r.page.locator(".node").count() == 0, "a broken course still drew a map")
    r2 = T.rig(name="nodata.html")
    r2.page.goto(T.server.url("nodata.html", DAY0))
    r2.page.wait_for_selector("#fatal")
    need("course data block" in r2.text("#fatal"), "a page whose data block does not parse did not say so")
    r3 = T.rig(name="norenderer.html").open()
    m = [x for x in r3.course["modules"] if any(v["type"] == "custom" for v in x.get("visuals", []))]
    if m:
        r3.open_module(m[0]["id"], "visual")
        need("does not define" in r3.text('[data-visual="custom"]'), "a custom visual with no renderer did not explain itself")
        need(r3.page.locator("#next-tab").count() == 1, "a visual that cannot be drawn took the rest of the lesson with it")
    return "a cycle and an unparseable data block each stop with a message; a missing renderer fails alone"


TESTS = [("t14", "broken", t14_broken), ("t1", "gates", t1_gates), ("t2", "fading", t2_fading), ("t3", "feedback", t3_feedback), ("t4", "schedule", t4_schedule), ("t5", "backup", t5_backup),
         ("t6", "imports", t6_imports), ("t7", "mastery", t7_mastery), ("t8", "planned", t8_planned), ("t9", "display", t9_display), ("t10", "scale", t10_scale),
         ("t11", "layout", t11_layout), ("t12", "frame", t12_frame), ("t13", "visuals", t13_visuals)]

MUTANTS = [
    ("a failed gate still opens the next module", "t1", "course.html",
     "if (res.passed && !mr.gate.passed_on) mr.gate.passed_on = day;", "if (!mr.gate.passed_on) mr.gate.passed_on = day;"),
    ("a lapse changes the E-Factor", "t4", "course.html",
     "if (q < 3) return {n: 1, interval: 1, ef100: ef100};", "if (q < 3) return {n: 1, interval: 1, ef100: Math.max(MIN_EF100, ef100 + 10 - (5 - q) * (8 + (5 - q) * 2))};"),
    ("a refused import wipes progress", "t6", "course.html",
     "if (!r.ok) { setImportMsg(r.message + ' Nothing was changed.', true);", "if (!r.ok) { A.data = L.emptyData(A.course); save(); setImportMsg(r.message + ' Nothing was changed.', true);"),
    ("reading a tab marks an objective demonstrated", "t7", "course.html",
     "      r.tabs[tab] = day;\n", "      r.tabs[tab] = day;\n      objRec(d, m.objectives[0].id).demonstrated_on = day;\n"),
    ("the pass mark is treated as exclusive", "t1", "other.html",
     "passed: items.length > 0 && correct * 100 >= threshold * items.length", "passed: items.length > 0 && correct * 100 > threshold * items.length"),
    ('the weak objective is not the one named', 't1', 'course.html',
     'weak = res.objectives.filter(function (o) { return !o.met; }), met = res.objectives.filter(function (o) { return o.met; });', 'weak = res.objectives.filter(function (o) { return o.met; }), met = res.objectives.filter(function (o) { return !o.met; });'),
    ('the independent solution is shown from the start', 't2', 'course.html',
     "sol = el('div', {id: idp + '-solution', hidden: true, class: 'paper'}", "sol = el('div', {id: idp + '-solution', class: 'paper'}"),
    ("every option shows the first option's explanation", 't3', 'course.html',
     "add(fb, [el('span', {class: 'verdict', text: ok ? 'Correct.' : 'Not correct.'}), el('span', {rich: o.why})]);", "add(fb, [el('span', {class: 'verdict', text: ok ? 'Correct.' : 'Not correct.'}), el('span', {rich: item.options[0].why})]);"),
    ('a same-day repeat reschedules the card', 't4', 'course.html',
     '        if (g.q >= 4) rec.again = null;\n', '        d.cards[cid] = L.schedule(rec, g.q, day);\n'),
    ('a clock moved backwards moves the course day back', 't4', 'course.html',
     'function courseDay() { return A.data.day_high || clockToday(); }', 'function courseDay() { return clockToday(); }'),
    ('an import drops the card schedules', 't5', 'course.html',
     "    A.data = r.data; A.hold = null; A.gate = null; A.session = null; A.lastReview = null; B.pending = null; B.importText = '';", "    A.data = r.data; A.data.cards = {}; A.hold = null; A.gate = null; A.session = null; A.lastReview = null; B.pending = null; B.importText = '';"),
    ('a good card review marks its objective demonstrated', 't7', 'course.html',
     'if (g.q >= 4) objRec(d, o).recalled_on = day;', 'if (g.q >= 4) { objRec(d, o).recalled_on = day; objRec(d, o).demonstrated_on = day; }'),
    ('planned modules are counted in the totals', 't8', 'course.html',
     'if (!isReady(m)) { t.modulesPlanned++; continue; }', 'if (!isReady(m)) { t.modulesPlanned++; }'),
    ('reset leaves the display as it was', 't9', 'course.html',
     'A.prefs = clone(DEFAULT_PREFS); applyPrefs(); Store.remove(PREF_KEY); render();', 'A.prefs = clone(DEFAULT_PREFS); Store.remove(PREF_KEY); render();'),
    ('module titles cannot wrap', 't11', 'course.html',
     'line-height:1.25;color:var(--heading);overflow-wrap:anywhere}', 'line-height:1.25;color:var(--heading);white-space:nowrap}'),
    ('storage is probed without a guard', 't12', 'course.html',
     "try { var k = 'preceptor:probe'; window.localStorage.setItem(k, '1'); window.localStorage.removeItem(k); return true; } catch (e) { return false; }", "var k = 'preceptor:probe'; window.localStorage.setItem(k, '1'); window.localStorage.removeItem(k); return true;"),
    ('a host storage object is never used', 't5', 'course.html',
     "        if (window.storage && typeof window.storage.get === 'function' && typeof window.storage.set === 'function') { Store.kind = 'host'; return; }\n", ""),
    ('the test clock is read on a page not marked for testing', 't4', 'course.html',
     "    if (!root.hasAttribute('data-test')) return null;\n", ""),
    ('an objective is listed for a check one day late', 't7', 'course.html',
     "if (today && diffDays(today, latest) >= after)", "if (today && diffDays(today, latest) > after)"),
    ('slider outputs are never redrawn', 't13', 'course.html',
     "      shown.forEach(function (s) { s.pv.textContent = env[s.p.name] + (s.p.unit ? ' ' + s.p.unit : ''); });\n      outs.update(env);", "      shown.forEach(function (s) { s.pv.textContent = env[s.p.name] + (s.p.unit ? ' ' + s.p.unit : ''); });"),
]


class Run:
    """Shared set-up for one engine: the temporary folder, the pages in it, the server."""

    def __init__(self, engine_text, course, renderers, built_page, port):
        self.tmp = tempfile.mkdtemp(prefix="preceptor-test-")
        self.server = None
        tmp = Path(self.tmp)
        if built_page is not None:
            page = built_page
            course = json.loads(DATA_BLOCK.search(built_page).group(2))
        else:
            page = embed(engine_text, course, renderers)
        engine_for_others = engine_text if engine_text is not None else built_page
        v2, self.renamed, self.removed_card = next_version(course)
        for made in (synthetic_course(3), synthetic_course(6, planned={5, 6}, cards=3), synthetic_course(28)):
            rep, _ = vc.validate(copy.deepcopy(made), "")
            if rep.errors:
                raise Failed("the test's own synthetic course is invalid: " + rep.errors[0])
        (tmp / "course.html").write_text(with_test_clock(page), encoding="utf-8")
        (tmp / "plain.html").write_text(page, encoding="utf-8")
        (tmp / "course.json").write_text(json.dumps(course), encoding="utf-8")
        (tmp / "v2.html").write_text(with_test_clock(embed(page, v2)), encoding="utf-8")
        (tmp / "other.html").write_text(with_test_clock(engine_for_others if engine_text is not None else embed(page, synthetic_course(3))), encoding="utf-8")
        (tmp / "planned.html").write_text(with_test_clock(embed(page, synthetic_course(6, planned={5, 6}, cards=3))), encoding="utf-8")
        (tmp / "big.html").write_text(with_test_clock(embed(page, synthetic_course(28))), encoding="utf-8")
        cyc = copy.deepcopy(course)
        cyc["modules"][0]["prereqs"] = [cyc["modules"][-1]["id"]]
        (tmp / "cycle.html").write_text(with_test_clock(embed(page, cyc)), encoding="utf-8")
        (tmp / "nodata.html").write_text(with_test_clock(DATA_BLOCK.sub(lambda m: m.group(1) + "{ this is not : valid" + m.group(3), page, count=1)), encoding="utf-8")
        (tmp / "norenderer.html").write_text(with_test_clock(re.sub(r"(const CUSTOM_RENDERERS\s*=\s*)(.*?)(;\s*/\* === CUSTOM RENDERERS: END === \*/)", lambda m: m.group(1) + "{}" + m.group(3), page, count=1, flags=re.S)), encoding="utf-8")
        (tmp / "blank.html").write_text("<!doctype html><html lang=\"en\"><title>blank</title><p>blank</p></html>", encoding="utf-8")
        srcdoc = page.replace("&", "&amp;").replace('"', "&quot;")
        (tmp / "frame.html").write_text("<!doctype html><html lang=\"en\"><title>frame</title><body style=\"margin:0\"><iframe id=\"f\" sandbox=\"allow-scripts\" style=\"width:100%;height:95vh;border:0\" srcdoc=\"" + srcdoc + "\"></iframe></body></html>", encoding="utf-8")
        self.server = Server(tmp, port)

    def close(self):
        if self.server:
            self.server.close()
        shutil.rmtree(self.tmp, ignore_errors=True)


class Ctx:
    def __init__(self, browser, run, size):
        self.browser, self.run, self.size = browser, run, size
        self.server, self.tmp, self.renamed, self.removed_card = run.server, run.tmp, run.renamed, run.removed_card
        self.rigs = []

    def rig(self, name="course.html", init_script=None, size=None):
        r = Rig(self.browser, self.server, size or self.size, name, init_script)
        self.rigs.append(r)
        return r

    def close(self):
        for r in self.rigs:
            try:
                r.close()
            except Exception:  # noqa: BLE001
                pass


def run_tests(browser, run, only, sizes=SIZES, main_page="course.html"):
    results = []
    for tid, name, fn in TESTS:
        if only and tid not in only:
            continue
        for size in sizes:
            T = Ctx(browser, run, size)
            if main_page != "course.html":
                original = T.rig
                T.rig = lambda name="course.html", init_script=None, size=None, _o=original: _o(main_page if name == "course.html" else name, init_script, size)
            try:
                detail = fn(T)
                results.append({"test": tid, "name": name, "width": size[0], "ok": True, "detail": detail})
            except Failed as e:
                results.append({"test": tid, "name": name, "width": size[0], "ok": False, "detail": str(e)})
            except Exception as e:  # noqa: BLE001  (a crash in the page or the driver is a failed test, not a crashed run)
                results.append({"test": tid, "name": name, "width": size[0], "ok": False, "detail": "%s: %s" % (type(e).__name__, str(e).splitlines()[0][:200])})
            finally:
                T.close()
    return results


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, opts, it = set(), {}, iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_engine: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        else:
            print("test_engine: unknown %s %s" % ("option" if a.startswith("--") else "argument", a), file=sys.stderr)
            return 2
    known = {t[0] for t in TESTS}
    only = set(opts["--only"].split(",")) if "--only" in opts else set()
    if only - known:
        print("test_engine: unknown test %s (tests are %s)" % (", ".join(sorted(only - known)), ", ".join(t[0] for t in TESTS)), file=sys.stderr)
        return 2
    if "--page" in opts and any(k in opts for k in ("--engine", "--course", "--renderers")):
        print("test_engine: --page cannot be combined with --engine, --course or --renderers", file=sys.stderr)
        return 2
    if "--page" in opts and "--mutants" in flags:
        print("test_engine: --mutants needs the engine source, so it cannot be combined with --page", file=sys.stderr)
        return 2
    try:
        port = int(opts.get("--port", "8120"))
        if not 1024 <= port <= 8139:
            raise ValueError
    except ValueError:
        print("test_engine: --port must be a whole number from 1024 to 8139", file=sys.stderr)
        return 2
    assets = HERE.parent / "assets"
    try:
        engine_text = course = renderers = built = None
        if "--page" in opts:
            built = Path(opts["--page"]).read_bytes().decode("utf-8-sig")
            if not DATA_BLOCK.search(built):
                print("test_engine: %s has no COURSE DATA block" % opts["--page"], file=sys.stderr)
                return 2
        else:
            engine_text = Path(opts.get("--engine", assets / "engine.html")).read_bytes().decode("utf-8-sig")
            course, _ = vc.read_course(opts.get("--course", str(assets / "sample-course-ipv4.json")))
            rpath = opts.get("--renderers", str(assets / "sample-renderers-ipv4.js") if "--course" not in opts else None)
            renderers = Path(rpath).read_bytes().decode("utf-8-sig").strip() if rpath else None
    except (OSError, UnicodeDecodeError, vc.InputError) as e:
        print("test_engine: cannot read an input: %s" % e, file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        emit("NOT RUN: the Python playwright package is not installed, so no browser test was run.")
        return 3
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch()
    except Exception as e:  # noqa: BLE001
        emit("NOT RUN: Chromium could not be launched (%s)." % str(e).splitlines()[0][:120])
        return 3
    out, failed = [], 0
    try:
        if "--mutants" in flags:
            for label, tid, page_name, old, new in MUTANTS:
                if only and tid not in only:
                    continue
                if engine_text.count(old) != 1:
                    out.append({"mutant": label, "caught": False, "detail": "the mutation could not be applied: its target text occurs %d times in the engine" % engine_text.count(old)})
                    failed += 1
                    continue
                run = Run(engine_text.replace(old, new), course, renderers, None, port)
                try:
                    res = run_tests(browser, run, {tid}, sizes=SIZES[:1], main_page=page_name)
                finally:
                    run.close()
                caught = [x for x in res if not x["ok"]]
                out.append({"mutant": label, "test": tid, "caught": bool(caught), "detail": caught[0]["detail"] if caught else "the test passed on the broken engine"})
                failed += 0 if caught else 1
        else:
            run = Run(engine_text, course, renderers, built, port)
            try:
                out = run_tests(browser, run, only)
            finally:
                run.close()
            failed = sum(1 for x in out if not x["ok"])
    finally:
        browser.close()
        pw.stop()
    if "--json" in flags:
        emit(json.dumps({"mode": "mutants" if "--mutants" in flags else "tests", "results": out, "failed": failed, "total": len(out)}, indent=1, ensure_ascii=True))
    elif "--mutants" in flags:
        for x in out:
            emit("%-8s mutant: %s%s\n         %s" % ("CAUGHT" if x["caught"] else "SURVIVED", x["mutant"], (" (by %s)" % x["test"]) if x.get("test") else "", x["detail"][:230]))
        emit("RESULT: %s. %d of %d planted faults were caught by the named test." % ("FAIL" if failed else "PASS", len(out) - failed, len(out)))
    else:
        for x in out:
            emit("%-5s %-3s %-9s at %4d wide  %s" % ("PASS" if x["ok"] else "FAIL", x["test"], x["name"], x["width"], x["detail"][:260]))
        emit("RESULT: %s. %d of %d test runs passed (%d tests at %d widths). A local browser and a local sandboxed frame; not any product's preview."
             % ("FAIL" if failed else "PASS", len(out) - failed, len(out), len({x["test"] for x in out}), len(SIZES)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
