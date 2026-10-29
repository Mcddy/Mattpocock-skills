#!/usr/bin/env python3
"""Browser tests for the timeline viewer, with planted faults. Needs the Python "playwright" package.

Usage:
  python test_timeline.py                 run every named test, in a tab and in a sandboxed frame
  python test_timeline.py --only NAME     run one test
  python test_timeline.py --template PATH test another copy of the viewer
  python test_timeline.py --mutants       plant each fault below in a temporary copy of the viewer and
                                          require the named test to fail on it

What it does: builds a page from the SYNTHETIC fixtures beside this script (fixtures/events.csv and
fixtures/sources.csv) with build_timeline.py, opens it in headless Chromium, and uses it. Most tests
run twice: in a plain tab, and inside <iframe sandbox="allow-scripts">, where storage, downloads,
dialogs and form submission are refused. What the page should show is taken from
chronology_check.py --json on the same fixtures, so the viewer is checked against the checker and
not against numbers typed into this file.

Everything is written to a temporary folder that is removed afterwards.

Limits. The sandboxed frame is a stand-in for a chat host's preview, not the host. A pass here says
the page does not depend on storage, downloads, dialogs or forms. It does not say the page works in
any given product, and it says nothing about how the page reads to a person: look at it.

Exit codes: 0 every test passed (with --mutants: every fault was caught). 1 otherwise.
2 bad arguments. 3 could not run because Playwright or Chromium is missing (prints NOT RUN).
"""
import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FX = HERE / "fixtures"
TEMPLATE = HERE.parent / "assets" / "timeline.html"
ECOLS = ["event_id", "date", "date_precision", "end_date", "time", "title", "detail", "actors", "source_id", "locator", "status", "conflicts_with", "tags"]
SANDBOX = "allow-scripts"
READY = "#timeline[aria-busy=false]"
IDS = "Array.from(document.querySelectorAll('article.event')).map(function (a) { return a.getAttribute('data-id'); })"


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


class World:
    """Shared state for a run: the browser, a temporary folder, the built page and the checker's answers."""

    def __init__(self, browser, tmp, template):
        self.browser, self.tmp, self.template, self.n = browser, Path(tmp), Path(template), 0
        self.page_path = self.build(FX / "events.csv", FX / "sources.csv", "SYNTHETIC: river bridge closure")
        r = subprocess.run([sys.executable, "-B", str(HERE / "chronology_check.py"), str(FX / "events.csv"), str(FX / "sources.csv"), "--json"],
                           capture_output=True, timeout=60)
        self.expect = json.loads(r.stdout.decode("utf-8"))
        self.by_id = {e["id"]: e for e in self.expect["events"]}

    def new_path(self, suffix):
        self.n += 1
        return self.tmp / ("p%03d%s" % (self.n, suffix))

    def build(self, events, sources, title):
        out = self.new_path(".html")
        r = subprocess.run([sys.executable, "-B", str(HERE / "build_timeline.py"), str(events), str(sources), "--out", str(out), "--title", title,
                            "--template", str(self.template)], capture_output=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError("build_timeline failed: %s %s" % (r.stdout.decode()[:300], r.stderr.decode()[:300]))
        return out

    def open(self, mode, path=None, width=1100, height=900, init=None, bindings=None, ready=READY):
        path = Path(path or self.page_path)
        ctx = self.browser.new_context(viewport={"width": width, "height": height})
        page = ctx.new_page()
        page.problems, page.requests = [], []
        page.on("pageerror", lambda e: page.problems.append("page error: %s" % e))
        page.on("console", lambda m: page.problems.append("console %s: %s" % (m.type, m.text)) if m.type == "error" else None)
        page.on("dialog", lambda d: (page.problems.append("dialog opened: %s" % d.message), d.dismiss()))
        page.on("request", lambda r: page.requests.append(r.url))
        for name, fn in (bindings or {}).items():
            page.expose_function(name, fn)
        if init:
            page.add_init_script(init)
        if mode == "frame":
            host = self.new_path(".html")
            host.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>host</title></head><body style="margin:0">'
                            '<iframe id="f" title="page under test" sandbox="%s" src="%s" style="border:0;width:100%%;height:%dpx"></iframe></body></html>'
                            % (SANDBOX, path.name, height), encoding="utf-8")
            if path.parent != host.parent:
                shutil.copy(path, host.parent / path.name)
            page.goto(host.as_uri())
            frame = page.frame_locator("#f")
            page.wait_for_selector("#f")
            f = [x for x in page.frames if x != page.main_frame][0]
        else:
            page.goto(path.as_uri())
            f = page.main_frame
        if ready:
            f.wait_for_selector(ready, timeout=10000)
        return ctx, page, f


def ids(f):
    return f.evaluate(IDS)


def settle(f):
    f.wait_for_timeout(200)


def focus_id(f):
    return f.evaluate("document.activeElement ? (document.activeElement.getAttribute('data-open') || document.activeElement.id || document.activeElement.tagName) : ''")


def open_filters(f):
    if f.evaluate("document.getElementById('filters').hidden"):
        f.click("#filters-toggle")


# ---------------- tests: each takes the world and a mode ("tab" or "frame") ----------------

def test_events_are_listed_in_the_checkers_order(w, mode):
    ctx, page, f = w.open(mode)
    try:
        want = w.expect["order"] + w.expect["undated"]
        need(ids(f) == want, "order in the page %s is not the checker's %s" % (ids(f), want))
        need(f.inner_text("#facts").startswith("19 events, 2023 to 2025, from 6 sources. 5 date conflicts, 2 not reconciled. 1 undated."), "facts line: " + f.inner_text("#facts"))
        heads = f.evaluate("Array.from(document.querySelectorAll('h2.year')).map(function (h) { return h.firstChild.textContent; })")
        need(heads == ["2023", "2024", "2025", "Undated"], "year headings: %s" % heads)
        last = f.evaluate("document.querySelector('article.event:last-of-type').getAttribute('data-id')")
        need(last == "B17" and f.inner_text('[data-when="B17"]').startswith("Undated"), "the undated row is not last and labelled Undated")
        need(not page.problems, "problems: %s" % page.problems)
    finally:
        ctx.close()


def test_dates_show_their_precision(w, mode):
    ctx, page, f = w.open(mode)
    try:
        got = f.evaluate("(function () { var o = {}; document.querySelectorAll('[data-when]').forEach(function (n) { o[n.getAttribute('data-when')] = n.getAttribute('data-label'); }); return o; })()")
        for i, e in w.by_id.items():
            want = "Undated" if e["precision"] == "undated" else e["display"]
            need(got.get(i) == want, "%s is shown as %r; the checker gives %r" % (i, got.get(i), want))
        need(f.inner_text('[data-when="B02"] span') == "Nov 2023" and "day not recorded" in f.inner_text('[data-when="B02"]'), "a month-precision date is not shown as a month: %r" % f.inner_text('[data-when="B02"]'))
        need(f.inner_text('[data-when="B01"] span') == "2023" and "month not recorded" in f.inner_text('[data-when="B01"]'), "a year-precision date is not shown as a year")
        need(f.inner_text('[data-when="B08"] span') == "about 8 Apr 2024", "an approximate date is not shown with the word about")
        f.click("#display-toggle")
        f.click('[data-set="dates"][data-value="iso"]')
        need(f.inner_text('[data-when="B02"] span') == "2023-11" and f.inner_text('[data-when="B01"] span') == "2023" and f.inner_text('[data-when="B08"] span') == "about 2024-04-08",
             "in ISO style a date gained or lost precision: %r %r" % (f.inner_text('[data-when="B02"] span'), f.inner_text('[data-when="B08"] span')))
    finally:
        ctx.close()


def test_conflicting_events_are_visibly_paired(w, mode):
    ctx, page, f = w.open(mode)
    try:
        pairs = w.expect["conflicts"]
        need(f.evaluate("document.querySelectorAll('.pair').length") == 2 * len(pairs), "expected %d conflict blocks, one on each side of %d pairs, found %d"
             % (2 * len(pairs), len(pairs), f.evaluate("document.querySelectorAll('.pair').length")))
        words = {"precision": "Different precision, compatible", "timezone": "Time zone", "announcement": "Announcement against occurrence",
                 "disagreement": "Real disagreement", "": "Not classified"}
        for p in pairs:
            a_txt = f.inner_text('article[data-id="%s"] .pair' % p["a"])
            b_txt = f.inner_text('article[data-id="%s"] .pair' % p["b"])
            la = f.get_attribute('article[data-id="%s"] .pair' % p["a"], "data-pair")
            lb = f.get_attribute('article[data-id="%s"] .pair' % p["b"], "data-pair")
            need(la and la == lb, "%s and %s do not carry the same pair letter (%r, %r)" % (p["a"], p["b"], la, lb))
            need(p["b"] in a_txt and p["b_date"] in a_txt and words[p["class"]] in a_txt, "%s does not show its partner's id, date and class: %r" % (p["a"], a_txt))
            need(p["a"] in b_txt and p["a_date"] in b_txt and words[p["class"]] in b_txt, "%s does not show its partner's id, date and class: %r" % (p["b"], b_txt))
        f.click('article[data-id="B12"] [data-goto="B13"]')
        settle(f)
        need(focus_id(f) == "B13", "Go to B13 left focus on %r" % focus_id(f))
        need(f.get_attribute('[data-open="B13"]', "aria-expanded") == "true", "the partner was not opened")
    finally:
        ctx.close()


def test_pairing_survives_filters(w, mode):
    ctx, page, f = w.open(mode)
    try:
        open_filters(f)
        f.click('[data-status="FACT"]')
        shown = ids(f)
        need("B12" in shown and "B13" not in shown, "status FACT should show B12 and hide B13: %s" % shown)
        txt = f.inner_text('article[data-id="B12"] .pair')
        need("B13" in txt and "16 Sep 2024" in txt and "Real disagreement" in txt, "with its partner filtered out, B12 no longer shows the other date: %r" % txt)
        f.click('article[data-id="B12"] [data-goto="B13"]')
        settle(f)
        need("B13" in ids(f) and focus_id(f) == "B13", "Go to a filtered-out partner did not show and focus it")
        need("Filters were cleared to show B13" in f.inner_text("#status"), "the page did not say the filters were cleared: %r" % f.inner_text("#status"))
    finally:
        ctx.close()


def test_filters(w, mode):
    ctx, page, f = w.open(mode)
    try:
        ev = w.expect["events"]
        tiers = {k: v["tier"] for k, v in w.expect["sources"].items()}
        order = w.expect["order"] + w.expect["undated"]
        open_filters(f)
        f.select_option("#f-tag", "ferry")
        need(ids(f) == [i for i in order if "ferry" in w.by_id[i]["tags"]], "tag ferry: %s" % ids(f))
        need("Showing 3 of 19 events. Filters: tag ferry." in f.inner_text("#status"), "status: %r" % f.inner_text("#status"))
        f.select_option("#f-tag", "")
        f.select_option("#f-actor", "Council")
        need(ids(f) == [i for i in order if "Council" in w.by_id[i]["actors"]], "actor Council: %s" % ids(f))
        f.select_option("#f-actor", "")
        f.select_option("#f-tier", "unverified")
        need(ids(f) == [i for i in order if any(tiers[s] == "unverified" for s in w.by_id[i]["sources"])], "tier unverified: %s" % ids(f))
        f.select_option("#f-tier", "")
        f.click('[data-status="ASSESSMENT"]')
        need(ids(f) == ["B18"], "status ASSESSMENT: %s" % ids(f))
        f.click('[data-status="REPORTED"]')
        need(ids(f) == [i for i in order if w.by_id[i]["status"] in ("ASSESSMENT", "REPORTED")], "two statuses: %s" % ids(f))
        f.click("#clear")
        need(len(ids(f)) == len(ev) and focus_id(f) == "q", "Clear filters did not restore all events and move focus to the search box")
        need(f.get_attribute('[data-status="REPORTED"]', "aria-pressed") == "false", "a status button stayed pressed after Clear filters")
        f.click("#conflicts-only")
        in_pairs = {p["a"] for p in w.expect["conflicts"]} | {p["b"] for p in w.expect["conflicts"]}
        need(ids(f) == [i for i in order if i in in_pairs], "date conflicts only: %s" % ids(f))
        f.click("#conflicts-only")
        f.fill("#q", "minutes ferry")
        settle(f)
        need(ids(f) == ["B16"], "search for two words: %s" % ids(f))
    finally:
        ctx.close()


def test_no_results_state(w, mode):
    ctx, page, f = w.open(mode)
    try:
        f.fill("#q", "zzzz no such thing")
        f.wait_for_selector(".blank")
        txt = f.inner_text(".blank")
        need("Nothing matches" in txt and 'search "zzzz no such thing"' in txt, "the no-results state does not say what was searched: %r" % txt)
        need("Showing 0 of 19 events" in f.inner_text("#status"), "status: %r" % f.inner_text("#status"))
        f.click(".blank button")
        need(len(ids(f)) == 19 and f.input_value("#q") == "" and focus_id(f) == "q", "Show all did not restore the list, clear the box and keep focus")
    finally:
        ctx.close()


def test_gaps_toggle(w, mode):
    ctx, page, f = w.open(mode)
    try:
        gaps = w.expect["gaps"]
        need(f.evaluate("document.querySelectorAll('.gap').length") == 0, "gaps are shown before the toggle is pressed")
        f.click("#gaps-toggle")
        need(f.get_attribute("#gaps-toggle", "aria-pressed") == "true", "the toggle does not show as pressed")
        shown = f.evaluate("Array.from(document.querySelectorAll('.gap')).map(function (g) { return [g.getAttribute('data-gap'), g.previousElementSibling.getAttribute('data-id'), g.textContent]; })")
        need([[int(g[0]), g[1]] for g in shown] == [[g["at_least_days"], g["after"]] for g in gaps], "gaps in the page %s; the checker gives %s" % (shown, gaps))
        need("At least 241 days" in shown[0][2] and "3 Oct 2024" in shown[0][2] and "1 Jun 2025" in shown[0][2], "gap wording: %r" % shown[0][2])
        need("1 gap longer than 90 days." in f.inner_text("#status"), "status: %r" % f.inner_text("#status"))
        open_filters(f)
        f.fill("#gap-days", "241")
        need(f.evaluate("document.querySelectorAll('.gap').length") == 0, "a gap of exactly 241 days is shown at a threshold of 241")
        f.fill("#gap-days", "240")
        need(f.evaluate("document.querySelectorAll('.gap').length") == 1, "a gap of 241 days is not shown at a threshold of 240")
        f.fill("#gap-days", "abc")
        need(f.get_attribute("#gap-days", "aria-invalid") == "true" and f.get_attribute("#gap-err", "data-show") == "yes" and f.is_visible("#gap-err"), "an invalid threshold shows no error")
        need(f.evaluate("document.querySelectorAll('.gap').length") == 1, "an invalid threshold changed the gaps shown")
        f.fill("#gap-days", "0")
        need(f.get_attribute("#gap-days", "aria-invalid") == "true", "a threshold of 0 was accepted")
        f.fill("#gap-days", "90")
        need(f.get_attribute("#gap-days", "aria-invalid") == "false" and not f.is_visible("#gap-err"), "the error stayed after a valid number")
        f.select_option("#f-tag", "survey")
        need(ids(f) == ["B02", "B03"] and f.evaluate("document.querySelectorAll('.gap').length") == 0,
             "Nov 2023 to 14 Feb 2024 is at most 76 certain days, but a gap over 90 is shown: the month was treated as its first day")
        f.fill("#gap-days", "75")
        txt = f.inner_text(".gap")
        need("At least 76 days" in txt and "in this filtered view" in txt and "30 Nov 2023" in txt, "filtered gap wording: %r" % txt)
    finally:
        ctx.close()


def test_open_an_event(w, mode):
    ctx, page, f = w.open(mode)
    try:
        need(f.evaluate("document.querySelectorAll('.more').length") == 0, "details are open at the start")
        meta = f.inner_text('article[data-id="B03"] .meta')
        need("FACT" in meta and "Council" in meta and "Minutes, item 3" in meta, "the closed row does not show status, source and locator: %r" % meta)
        f.focus('[data-open="B03"]')
        f.press('[data-open="B03"]', "Enter")
        need(f.get_attribute('[data-open="B03"]', "aria-expanded") == "true" and focus_id(f) == "B03", "Enter did not open the event or focus moved to %r" % focus_id(f))
        txt = f.inner_text("#more-B03")
        for part in ('calls this "immediate" & unconditional', "2024-02-14, precision day", "Council; Surveyor", "Minutes, item 3", "SYNTHETIC: Council meeting minutes",
                     "Tier primary; read section; accessed 10 Jan 2026", "https://example.org/minutes"):
            need(part in txt, "the opened event lacks %r: %r" % (part, txt))
        link = f.get_attribute("#more-B03 a", "href"), f.get_attribute("#more-B03 a", "rel"), f.get_attribute("#more-B03 a", "target")
        need(link == ("https://example.org/minutes", "noopener noreferrer", "_blank"), "source link: %s" % (link,))
        f.press('[data-open="B03"]', "Enter")
        need(f.get_attribute('[data-open="B03"]', "aria-expanded") == "false" and f.evaluate("document.getElementById('more-B03') === null"), "the event did not close")
        f.click("#open-all")
        need(f.evaluate("document.querySelectorAll('.more').length") == 19 and f.get_attribute("#open-all", "aria-pressed") == "true", "Open all did not open 19 events")
        f.click("#open-all")
        need(f.evaluate("document.querySelectorAll('.more').length") == 0, "Open all pressed again did not close them")
    finally:
        ctx.close()


def read_csv_text(text):
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]


def test_export_follows_the_view(w, mode):
    ctx, page, f = w.open(mode)
    try:
        f.click("#export-toggle")
        need(f.is_visible("#export") and f.get_attribute("#export-toggle", "aria-expanded") == "true", "the export panel did not open")
        md = f.input_value("#export-text")
        need(md.startswith("# SYNTHETIC: river bridge closure\n") and "View exported: 19 of 19 events. No filters." in md, "markdown head: %r" % md[:200])
        table = [ln for ln in md.splitlines() if ln.startswith("| ") and not ln.startswith("| Date")]
        need(len(table) == 18, "the markdown table has %d rows, not the 18 dated events" % len(table))
        need("| Nov 2023 | Council commissions a structural survey | FACT | S2: Minutes, item 7 | B02 |" in md, "a month-precision row is not exported as a month")
        need("## Date conflicts" in md and "B12 (9 Sep 2024, Harbour authority) against B13 (16 Sep 2024, Freight digest). Real disagreement." in md, "conflicts section missing or wrong")
        need("## Undated, not placed" in md and "- B17: Complaint lodged" in md and "## Sources" in md, "undated or sources section missing")
        need("\\| pipe" in md, "a pipe in a title was not escaped in the markdown table")
        f.click('[data-export="csv"]')
        header, rows = read_csv_text(f.input_value("#export-text"))
        need(header == ECOLS and [r["event_id"] for r in rows] == w.expect["order"] + w.expect["undated"], "CSV export header or rows are wrong")
        need(next(r for r in rows if r["event_id"] == "B02")["date"] == "2023-11" and next(r for r in rows if r["event_id"] == "B12")["conflicts_with"] == "B13:disagreement",
             "CSV export changed a date or a conflict")
        out = w.new_path(".csv")
        out.write_text(f.input_value("#export-text"), encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(HERE / "chronology_check.py"), str(out), str(FX / "sources.csv"), "--json"], capture_output=True, timeout=60)
        back = json.loads(r.stdout.decode("utf-8"))
        need(r.returncode == 0 and back["order"] == w.expect["order"] and len(back["conflicts"]) == len(w.expect["conflicts"]), "the exported CSV does not pass the checker with the same result")
        open_filters(f)
        f.select_option("#f-tag", "reopening")
        header, rows = read_csv_text(f.input_value("#export-text"))
        need([r["event_id"] for r in rows] == ["B12", "B13"], "the CSV export did not follow the filter: %s" % [r["event_id"] for r in rows])
        f.click('[data-export="md"]')
        md = f.input_value("#export-text")
        need("View exported: 2 of 19 events. Filters: tag reopening." in md and "B02" not in md, "the markdown export did not follow the filter")
        f.click("#export-copy")
        f.wait_for_function("document.getElementById('export-msg').textContent.length > 0")
        msg = f.inner_text("#export-msg")
        if not msg.startswith("Copied"):
            sel = f.evaluate("(function () { var t = document.getElementById('export-text'); return [t.selectionStart, t.selectionEnd, t.value.length]; })()")
            need("refused" in msg and sel[0] == 0 and sel[1] == sel[2], "copy was refused but the text was not selected for copying by hand: %r %s" % (msg, sel))
        f.click("#export-download")
        need("copy the text" in f.inner_text("#export-msg").lower() or "Download requested" in f.inner_text("#export-msg"), "download gave no message: %r" % f.inner_text("#export-msg"))
        f.click("#export-close")
        need(not f.is_visible("#export") and focus_id(f) == "export-toggle", "closing the export did not return focus to its button")
        # A sandboxed frame is refused the clipboard, and Chromium logs that refusal itself. The page's
        # handling of it is asserted above; any other console error still fails the test.
        other = [x for x in page.problems if "Clipboard API has been blocked" not in x]
        need(not other, "problems: %s" % other)
        if mode == "frame":
            need("refused" in msg, "in the sandboxed frame the copy was expected to be refused, and the page said: %r" % msg)
    finally:
        ctx.close()


def test_awkward_text_is_shown_as_text(w, mode):
    ctx, page, f = w.open(mode)
    try:
        title = w.by_id["B19"]["title"]
        need(f.inner_text("#h-B19") == title, "the title is not shown as written: %r" % f.inner_text("#h-B19"))
        need(f.evaluate("document.querySelectorAll('#timeline script, #timeline img, #timeline iframe').length") == 0, "markup from a title became elements")
        need(not page.problems, "problems: %s" % page.problems)
    finally:
        ctx.close()


def test_display_settings_apply_and_reset(w, mode):
    ctx, page, f = w.open(mode)
    try:
        f.click("#display-toggle")
        for name, value, attr in (("theme", "night", "data-theme"), ("density", "compact", "data-density"), ("text", "larger", "data-text")):
            f.click('[data-set="%s"][data-value="%s"]' % (name, value))
            need(f.evaluate("document.documentElement.getAttribute('%s')" % attr) == value, "%s %s did not apply" % (name, value))
            need(f.get_attribute('[data-set="%s"][data-value="%s"]' % (name, value), "aria-pressed") == "true", "%s %s does not show as selected" % (name, value))
        size = f.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)")
        need(abs(size - 20) < 0.01, "Larger text gives a root size of %s px, not 20" % size)
        note = f.inner_text("#store-note")
        if mode == "frame":
            need(note.startswith("Not saved: this page cannot store data here."), "in the sandboxed frame the page does not say settings are not kept: %r" % note)
        else:
            need(note == "Display settings are saved in this browser.", "note: %r" % note)
            page.reload()
            f.wait_for_selector(READY)
            need(f.evaluate("document.documentElement.getAttribute('data-theme')") == "night" and f.evaluate("document.documentElement.getAttribute('data-text')") == "larger",
                 "settings did not survive a reload in a tab")
            f.click("#display-toggle")
        f.click("#display-reset")
        got = f.evaluate("[document.documentElement.getAttribute('data-theme'), document.documentElement.getAttribute('data-density'), document.documentElement.getAttribute('data-text')]")
        need(got == ["paper", "comfortable", "standard"], "Reset display left %s" % got)
        need(f.get_attribute('[data-set="theme"][data-value="paper"]', "aria-pressed") == "true", "after reset Paper does not show as selected")
        if mode == "tab":
            page.reload()
            f.wait_for_selector(READY)
            need(f.evaluate("document.documentElement.getAttribute('data-theme')") == "paper", "the reset did not survive a reload")
        need(not page.problems, "problems: %s" % page.problems)
    finally:
        ctx.close()


def test_host_storage_is_used_when_present(w, mode):
    if mode == "frame":
        return
    saved = {}
    init = "window.storage = {get: function (k) { return window.hostGet(k); }, set: function (k, v) { return window.hostSet(k, v); }};"
    ctx, page, f = w.open(mode, init=init, bindings={"hostGet": lambda k: saved.get(k), "hostSet": lambda k, v: saved.__setitem__(k, v)})
    try:
        f.click("#display-toggle")
        f.click('[data-set="theme"][data-value="ember"]')
        need(f.inner_text("#store-note") == "Display settings are saved by the app showing this page.", "note: %r" % f.inner_text("#store-note"))
        f.wait_for_timeout(150)
        need(len(saved) == 1, "nothing was written to the host storage object")
        env = json.loads(list(saved.values())[0])
        need(env["app"] == "chronology-timeline" and env["schema"] == 1 and env["content_id"] == "display-settings" and env["saved_at"].endswith("Z")
             and env["data"]["theme"] == "ember", "saved envelope: %s" % env)
        need(f.evaluate("window.localStorage.getItem('chronology-timeline:display')") is None, "the browser store was written although a host store was present")
        page.reload()
        f.wait_for_selector(READY)
        f.wait_for_function("document.documentElement.getAttribute('data-theme') === 'ember'", timeout=3000)
    finally:
        ctx.close()


def test_storage_that_throws_does_not_break_the_page(w, mode):
    if mode == "frame":
        return
    init = ("Object.defineProperty(window, 'localStorage', {get: function () { throw new Error('storage blocked'); }});"
            "window.storage = {get: function () { return Promise.reject(new Error('host refused')); }, set: function () { throw new Error('host refused'); }};")
    ctx, page, f = w.open(mode, init=init)
    try:
        need(len(ids(f)) == 19, "the timeline did not render when storage throws")
        f.click("#display-toggle")
        f.click('[data-set="theme"][data-value="slate"]')
        need(f.evaluate("document.documentElement.getAttribute('data-theme')") == "slate", "the theme did not apply when storage throws")
        need(f.inner_text("#store-note").startswith("Not saved: this page cannot store data here."), "note: %r" % f.inner_text("#store-note"))
        need(not page.problems, "problems: %s" % page.problems)
    finally:
        ctx.close()


def test_saved_settings_of_another_app_or_schema_are_ignored(w, mode):
    if mode == "frame":
        return
    for bad in ('{"app":"another-page","schema":1,"content_id":"display-settings","saved_at":"2026-01-01T00:00:00Z","data":{"theme":"night"}}',
                '{"app":"chronology-timeline","schema":2,"content_id":"display-settings","saved_at":"2026-01-01T00:00:00Z","data":{"theme":"night"}}',
                '{"app":"chronology-timeline","schema":1,"data":{"theme":"<img>"}}', "not json", ""):
        init = "try { window.localStorage.setItem('chronology-timeline:display', %s); } catch (e) {}" % json.dumps(bad)
        ctx, page, f = w.open(mode, init=init)
        try:
            need(f.evaluate("document.documentElement.getAttribute('data-theme')") == "paper", "a saved value that should be ignored changed the theme: %r" % bad[:60])
            need(len(ids(f)) == 19 and not page.problems, "the page did not render cleanly with a bad saved value: %s" % page.problems)
        finally:
            ctx.close()
    good = '{"app":"chronology-timeline","schema":1,"content_id":"display-settings","saved_at":"2026-01-01T00:00:00Z","data":{"theme":"night"}}'
    ctx, page, f = w.open(mode, init="try { window.localStorage.setItem('chronology-timeline:display', %s); } catch (e) {}" % json.dumps(good))
    try:
        need(f.evaluate("document.documentElement.getAttribute('data-theme')") == "night", "the valid neighbour (a well-formed saved value) was not applied")
    finally:
        ctx.close()


def test_empty_template_shows_the_empty_state(w, mode):
    ctx, page, f = w.open(mode, path=w.template)
    try:
        txt = f.inner_text(".blank")
        need("No events are embedded in this page" in txt and "build_timeline.py" in txt, "empty state: %r" % txt)
        need(not f.is_visible("#tools") and f.inner_text("#facts") == "No events.", "the tools are shown with nothing to act on")
        need(not page.problems, "problems: %s" % page.problems)
    finally:
        ctx.close()


def test_bad_data_block_shows_an_error_state(w, mode):
    text = w.page_path.read_text(encoding="utf-8")
    marker = '<script type="application/json" id="timeline-data">'
    start = text.index(marker) + len(marker)
    end = text.index("</script>", start)
    cases = (("{not json", "could not be read"), (text[start:end].replace('"schema":1', '"schema":2', 1), "schema 2 and this viewer reads schema 1"),
             (text[start:end].replace('"app":"chronology-timeline"', '"app":"another-page"', 1), "does not hold timeline data"),
             ('{"app":"chronology-timeline","schema":1,"title":"x"}', "incomplete"))
    for block, phrase in cases:
        p = w.new_path(".html")
        p.write_text(text[:start] + block + text[end:], encoding="utf-8")
        ctx, page, f = w.open(mode, path=p)
        try:
            txt = f.inner_text(".blank")
            need(phrase in txt, "error state for %r: %r" % (block[:30], txt))
            need(f.get_attribute(".blank", "role") == "alert" and not f.is_visible("#tools"), "the error is not announced or the tools are still shown")
            need(not page.problems, "problems: %s" % page.problems)
        finally:
            ctx.close()


def test_no_sideways_overflow_with_everything_open(w, mode):
    for width in (360, 390, 1280):
        ctx, page, f = w.open(mode, width=width, height=900)
        try:
            f.click("#display-toggle")
            f.click('[data-set="text"][data-value="larger"]')
            open_filters(f)
            f.click("#gaps-toggle")
            f.click("#open-all")
            f.click("#export-toggle")
            over = f.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            need(over <= 0, "at %d wide the page scrolls sideways by %d px" % (width, over))
            wide = f.evaluate("Array.from(document.querySelectorAll('#timeline *, .tools *, #display *')).filter(function (n) { var r = n.getBoundingClientRect(); "
                              "return r.width > 0 && r.right > document.documentElement.clientWidth + 1; }).map(function (n) { return n.tagName + '.' + n.className; }).slice(0, 5)")
            need(not wide, "at %d wide these stick out of the page: %s" % (width, wide))
        finally:
            ctx.close()


def test_a_large_timeline_renders(w, mode):
    if mode == "frame":
        return
    cols = ECOLS
    lines = [",".join(cols)]
    for n in range(600):
        year, month, day = 2000 + n // 30, 1 + (n % 12), 1 + (n * 7) % 28
        precision = ("day", "month", "year")[n % 3]
        date = "%04d-%02d-%02d" % (year, month, day) if precision == "day" else ("%04d-%02d" % (year, month) if precision == "month" else "%04d" % year)
        lines.append(",".join(["L%03d" % n, date, precision, "", "", "SYNTHETIC event number %d with a title long enough to wrap on a narrow screen" % n, "SYNTHETIC detail",
                               "Actor %d" % (n % 9), "S%d" % (1 + n % 3), "row %d" % n, "REPORTED", "", "tag%d" % (n % 7)]))
    ev = w.new_path(".csv")
    ev.write_text("\n".join(lines) + "\n", encoding="utf-8")
    big = w.build(ev, FX / "sources.csv", "SYNTHETIC: 600 events")
    ctx, page, f = w.open(mode, path=big, width=390, height=844)
    try:
        need(len(ids(f)) == 600, "600 events were built but %d are shown" % len(ids(f)))
        took = f.evaluate("(function () { var t = performance.now(); document.getElementById('open-all').click(); document.getElementById('gaps-toggle').click(); return performance.now() - t; })()")
        need(f.evaluate("document.querySelectorAll('.more').length") == 600 and took < 4000, "opening 600 events took %d ms" % took)
        need(f.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0, "600 events overflow sideways at 390 wide")
        f.fill("#q", "number 599")
        settle(f)
        need(ids(f) == ["L599"], "search in 600 events: %s" % ids(f)[:5])
    finally:
        ctx.close()


def test_no_outside_requests(w, mode):
    ctx, page, f = w.open(mode)
    try:
        f.click("#gaps-toggle")
        f.click("#export-toggle")
        outside = [u for u in page.requests if not u.startswith("file:") and not u.startswith("blob:")]
        need(not outside, "the page asked for %s" % outside)
        need(f.evaluate("document.querySelectorAll('form').length") == 0, "the page has a form element")
    finally:
        ctx.close()


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

# Planted faults in the viewer. "old" must appear exactly once; it is replaced by "new" in a temporary copy.
MUTANTS = [
    {"name": "the conflict pairing is dropped: conflicting events look like any other", "old": "    (pairsOf[ev.id] || []).forEach(function (p) { what.appendChild(pairBlock(ev, p)); });\n", "new": "",
     "caught_by": "test_conflicting_events_are_visibly_paired"},
    {"name": "a month-precision date is shown as the first of the month", "old": "return p.length === 2 ? m + ' ' + p[0] :", "new": "return p.length === 2 ? '1 ' + m + ' ' + p[0] :",
     "caught_by": "test_dates_show_their_precision"},
    {"name": "gaps are measured from the first day of an imprecise date", "old": "best = Math.max(best, dated[i].l); hi.push(best);", "new": "best = Math.max(best, dated[i].e); hi.push(best);",
     "caught_by": "test_gaps_toggle"},
    {"name": "the export ignores the filters", "old": "    var shown = D.events.filter(matches), words = filterWords();\n    $('export-text').value",
     "new": "    var shown = D.events, words = filterWords();\n    $('export-text').value", "caught_by": "test_export_follows_the_view"},
    {"name": "text from the data is written as markup", "old": "if (k === 'text') n.textContent = attrs[k];", "new": "if (k === 'text') n.innerHTML = attrs[k];",
     "caught_by": "test_awkward_text_is_shown_as_text"},
    {"name": "the browser store is used without a try", "old": "      } catch (e) { store.kind = 'memory'; finish(null); }\n    }\n    var h = hostStorage();",
     "new": "      } catch (e) { throw e; }\n    }\n    var h = hostStorage();", "caught_by": "test_display_settings_apply_and_reset"},
    {"name": "a filtered-out partner cannot be reached from its pair", "old": "    if (!matches(target)) { clearFilters(); cleared = true; }\n", "new": "",
     "caught_by": "test_pairing_survives_filters"},
]


def run_suite(browser, template, only=None, quiet=False):
    tmp = tempfile.mkdtemp(prefix="timeline-test-")
    failed = []
    try:
        try:
            world = World(browser, tmp, template)
        except Exception as e:  # noqa: BLE001
            if not quiet:
                print("FAIL  could not build the fixture page: %s" % str(e)[:300])
            return ["(build)"] + [t.__name__ for t in TESTS]
        for t in TESTS:
            if only and t.__name__ != only:
                continue
            for mode in ("tab", "frame"):
                label = "%s [%s]" % (t.__name__, mode)
                try:
                    t(world, mode)
                    if not quiet:
                        print("PASS  " + label)
                except AssertionError as e:
                    failed.append(t.__name__)
                    if not quiet:
                        print("FAIL  %s\n      %s" % (label, str(e).replace("\n", "\n      ")[:900]))
                except Exception as e:  # noqa: BLE001  a crash or a timeout in the page is a failed test
                    failed.append(t.__name__)
                    if not quiet:
                        print("FAIL  %s\n      %s: %s" % (label, type(e).__name__, str(e).splitlines()[0][:300]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return sorted(set(failed))


def run_mutants(browser, template):
    survived = 0
    src = Path(template).read_text(encoding="utf-8")
    for m in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="timeline-mutant-")
        try:
            if src.count(m["old"]) != 1:
                print("BROKEN    %s: the text to replace appears %d times in the viewer, not once" % (m["name"], src.count(m["old"])))
                survived += 1
                continue
            copy = Path(tmp) / "timeline.html"
            copy.write_text(src.replace(m["old"], m["new"]), encoding="utf-8")
            failed = run_suite(browser, copy, quiet=True)
            if m["caught_by"] in failed:
                print("CAUGHT    %s\n          by %s (%d test(s) failed in all: %s)" % (m["name"], m["caught_by"], len(failed), ", ".join(failed)))
            else:
                survived += 1
                print("SURVIVED  %s\n          %s did not fail. Tests that failed: %s" % (m["name"], m["caught_by"], ", ".join(failed) or "none"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d planted fault(s), %d caught, %d not caught" % (len(MUTANTS), len(MUTANTS) - survived, survived))
    return 1 if survived else 0


def main(argv):
    only, template, mutants, it = None, TEMPLATE, False, iter(argv)
    for a in it:
        if a == "--mutants":
            mutants = True
        elif a in ("--only", "--template"):
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_timeline: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--only":
                only = v
            else:
                template = Path(v)
        else:
            print("test_timeline: unknown argument " + a, file=sys.stderr)
            return 2
    if only and only not in [t.__name__ for t in TESTS]:
        print("test_timeline: no test named " + only, file=sys.stderr)
        return 2
    if not Path(template).is_file():
        print("test_timeline: no viewer at %s" % template, file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("NOT RUN: the Python playwright package is not installed, so the viewer was not opened in a browser")
        return 3
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e).splitlines()[0][:120])
            return 3
        try:
            if mutants:
                return run_mutants(browser, template)
            failed = run_suite(browser, template, only)
        finally:
            browser.close()
    ran = 1 if only else len(TESTS)
    print("\n%d test(s) run in a tab and in a sandboxed frame, %d passed, %d failed" % (ran, ran - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.exit(main(sys.argv[1:]))
