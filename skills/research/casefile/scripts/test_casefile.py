#!/usr/bin/env python3
"""Work a built casefile in a browser, in a tab and in a sandboxed frame, and check what it does.

Usage:
  python test_casefile.py [--ledger-check PATH/ledger_check.py] [--sizes 390x844,1280x800]
                          [--only NAME] [--modes tab,frame] [--no-large] [--planted] [--json]

The page under test is built here, by build_casefile.py, from the real EAA ledger in the fixtures
folder beside this script (two CSV files and eaa-extra.json, which adds four questions and one
assessment). Nothing outside a temporary folder is written.

Each test opens a fresh page. In the frame (<iframe sandbox="allow-scripts">) storage, downloads
and dialogs are refused, as in a chat preview. The tests, by name:
  loads_cleanly                        no script error, dialog, form, outside request, repeated id
                                       or overflow, in each view and form, also with text 25 percent larger
  library_copy_is_identical            the pocket-state.js and pocket-ui.js pasted into the page are
                                       identical to the copies in assets, and those two files have
                                       the SHA-256 recorded in assets/pocket-lib.sha256. That record
                                       is copied from the library's own release, whose own test
                                       holds the released files to the same two lines, so nothing
                                       outside this skill's folder is read
  t01_lineage_both_ways                assessment A1 to its claims, claim C1 to source S1, and from
                                       S1 back to the dependent claim and the assessment, one click each
  t02_if_this_source_falls             withdrawing S3 names C2 and the assessment that rests on it
  t03_refused_status_change            C2 to FACT is refused in the checker's words and nothing
                                       changes; with an address on its source it is allowed; undo
  t04_model_output_not_load_bearing    refused for C5; the valid neighbour (a REPORTED claim) is allowed
  t05_conflict_recorded_and_settled    a direct conflict is written to both claims, the open count
                                       rises, settling it lowers the count
  t06_exported_csv_passes_the_checker  the exported files are byte-identical to the originals, and
                                       the checker gives the same errors and advisory notes on both
  t07_round_trip_and_refused_imports   export, import into a fresh page: identical data. Another
                                       app's file, a casefile that breaks a rule, and bad CSV files
                                       are refused, with row numbers, and the data is unchanged
  t08_reload_or_honest_note            the tab keeps a change across a reload; the frame says it
                                       cannot save and export still works
  t09_large_ledger                     300 sources and 1,000 claims, generated here: load, filter,
                                       open lineage, change a status, export, with timings
  page_rules_agree_with_the_checker    the page's own rule messages for two bad ledgers, and its
                                       advisory notes, match ledger_check.py's recorded output
  filters_and_search                   question, status, tier, load-bearing, stale and text filters
  add_edit_delete_with_rules           adding and deleting under the rules, with undo
  brief_is_built_from_the_ledger       the Markdown brief leaves the answer blank and lists what is there
  unreadable_built_ledger_is_reported  a data block that is cut short, or that breaks a rule, is
                                       reported at the top and the page starts empty

For t06 the checker is ledger_check.py when --ledger-check gives its path. Without it the same
comparison is made with build_casefile.py's own rules (test_rules_agree.py shows those agree),
and the report says which was used.

--planted builds deliberately broken copies and checks that the named test fails for each: a
page where a refused status change still applies, one where a bad CSV import wipes the ledger,
one whose CSV export drops the conflict columns, one whose pasted library differs from the copy
in assets by a word, and a copy of the library files where one differs from its recorded hash.

Time limits in t09 (1,000 claims): 4,000 ms to open and draw; 700 ms for each working step
(search, filter, open lineage, change a status, undo); 2,500 ms for each step that writes the
whole ledger into a text box on the page (the two CSV files, the brief, the casefile export),
where nearly all the time is the browser laying out several hundred thousand characters.

What it cannot tell: whether the page works in a real host's preview (this frame is a local
stand-in), anything about screen readers, or whether the page is pleasant to use. Look at it.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes: 0 all passed (or every planted failure was caught). 1 a test failed (or a planted
failure was missed). 2 bad arguments. 3 could not run (prints NOT RUN).
"""
import csv
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
ASSETS = HERE.parent / "assets"
LIBRARY = ("pocket-state.js", "pocket-ui.js")
HASH_FILE = "pocket-lib.sha256"
FLAGS = {"--planted", "--json", "--no-large"}
VALUES = {"--ledger-check", "--sizes", "--only", "--modes"}
NOT_SAVED = "Not saved: this page cannot store data here. Export to keep your work"
C2_REASON = "claim C2: cannot be a FACT: no source has an address. Use REPORTED, or open a better source"
C5_REASON = "claim C5: MODEL_OUTPUT cannot be load-bearing. Open what it cites and record that as a new claim"
OTHER_APP = json.dumps({"app": "reading-log", "schema": 2, "content_id": "reading-log@1", "saved_at": "2026-10-09T02:00:00.000Z",
                        "data": {"books": [{"id": 1, "title": "SYNTHETIC entry", "author": "", "status": "to-read", "rating": None, "notes": "", "added": None, "finished": None}], "nextId": 2}})

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
# Run one action inside the page and time it: the handler, the redraw and the layout it forces.
TIMED_JS = """
([kind, sel, value]) => {
  const el = document.querySelector(sel);
  if (!el) return -1;
  const t0 = performance.now();
  if (kind === 'click') el.click();
  else { el.value = value; el.dispatchEvent(new Event('input', {bubbles: true})); }
  void document.body.offsetHeight;
  return performance.now() - t0;
}
"""

PLANTED = [
    {"id": "refusal-ignored", "what": "a refused status change still applies (the rules are no longer enforced when a change is made)",
     "caught_by": ["t03_refused_status_change", "t04_model_output_not_load_bearing"],
     "edits": [("      if (added.length) { refused = added; throw new Error('refused by a ledger rule'); }\n", ""),
               ("    return p.length ? p : ruleProblems(d, null);", "    return p;")]},
    {"id": "bad-csv-wipes", "what": "importing a bad CSV empties the ledger before the files are checked",
     "caught_by": ["t07_round_trip_and_refused_imports"],
     "edits": [("    $('csv-orphans').hidden = true;\n    showImportProblems([]);",
                "    store.update(function (d) { d.assessments = []; d.claims = []; d.sources = []; });\n    $('csv-orphans').hidden = true;\n    showImportProblems([]);")]},
    {"id": "csv-drops-conflicts", "what": "the exported claims CSV drops the three conflict columns",
     "caught_by": ["t06_exported_csv_passes_the_checker"],
     "edits": [("claims: toCsv(CLAIM_COLS, d.claims.map(claimRow))", "claims: toCsv(CLAIM_COLS.slice(0, 8), d.claims.map(claimRow))")]},
    {"id": "pasted-library-differs", "what": "the library pasted into the page differs from the copy in assets by one word",
     "caught_by": ["library_copy_is_identical"],
     "edits": [("local: 'Saved in this browser',", "local: 'Stored in this browser',")]},
    {"id": "library-not-as-recorded", "what": "a library file in assets differs from its recorded hash (one comment line added, in a copy of the files)",
     "caught_by": ["library_copy_is_identical"], "library": ("pocket-state.js", "// drift\n")},
]


WHOLE_LEDGER_STEPS = ("export the two CSV files", "build the brief", "export the casefile")


class Failed(Exception):
    pass


def need(cond, message):
    if not cond:
        raise Failed(message)


class Session:
    """One fresh load of a casefile page, in a tab or inside a sandboxed frame."""

    def __init__(self, browser, page_path, mode, size, tmp, context=None, init_script=None):
        self.mode, self.size = mode, size
        self.own = context is None
        self.context = context or browser.new_context(viewport={"width": size[0], "height": size[1]})
        if init_script:
            self.context.add_init_script(init_script)
        self.page = self.context.new_page()
        self.errors, self.dialogs, self.outside = [], [], []
        self.page.on("pageerror", lambda e: self.errors.append("script error: " + str(e).split("\n")[0][:160]))
        self.page.on("console", lambda m: self.errors.append("console error: " + m.text[:160])
                     if m.type == "error" and not m.text.startswith("Permissions policy violation") else None)
        self.page.on("dialog", self._dialog)
        self.page.on("request", lambda r: self.outside.append(r.url[:120]) if not r.url.startswith(("file:", "blob:", "data:", "about:")) else None)
        uri = Path(page_path).resolve().as_uri()
        if mode == "frame":
            wrapper = Path(tmp) / ("frame-%d.html" % (abs(hash(uri)) % 100000))
            wrapper.write_text('<!doctype html><html lang="en"><title>frame</title><body style="margin:0">'
                               '<iframe id="f" sandbox="allow-scripts" src="%s" style="border:0;width:100vw;height:100vh"></iframe></body></html>' % uri, encoding="utf-8")
            uri = wrapper.as_uri()
        self.started = time.time()
        self.page.goto(uri, timeout=20000)
        self.wait(lambda: self.count("#pk-note") == 1 and self.text("#pk-note").strip() not in ("", "Opening saved data."), "the page never finished opening")
        self.ready_ms = (time.time() - self.started) * 1000.0

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

    def wait(self, fn, message, timeout=5.0):
        end, last = time.time() + timeout, None
        while True:
            try:
                if fn():
                    return
                last = None
            except Failed:
                raise
            except Exception as e:  # noqa: BLE001
                last = str(e).split("\n")[0][:100]
            if time.time() > end:
                raise Failed(message + ((" (" + last + ")") if last else ""))
            self.page.wait_for_timeout(50)

    def count(self, sel):
        return self.t.locator(sel).count()

    def text(self, sel):
        loc = self.t.locator(sel)
        return (loc.first.text_content(timeout=3000) or "") if loc.count() else ""

    def value(self, sel):
        return self.t.locator(sel).first.input_value(timeout=3000)

    def attr(self, sel, name):
        loc = self.t.locator(sel)
        return loc.first.get_attribute(name, timeout=3000) if loc.count() else None

    def shown(self, sel):
        loc = self.t.locator(sel)
        return loc.count() > 0 and loc.first.is_visible()

    def click(self, sel):
        self.t.locator(sel).first.click(timeout=4000)

    def fill(self, sel, value):
        self.t.locator(sel).first.fill(value, timeout=4000)

    def to_list(self):
        """On a narrow screen the open item, or an open form, takes the place of the views: leave it first."""
        if not self.shown("#goto"):
            self.click("#form-cancel" if self.count("#form-cancel") else "#detail-back")
        if not self.shown("#goto"):
            self.click("#detail-back")

    def view(self, name):
        self.to_list()
        self.click('[data-view="%s"]' % name)

    def open(self, item_id):
        """Open an item by typing its id, the way a person would."""
        self.to_list()
        self.fill("#goto", item_id)
        self.t.locator("#goto").first.press("Enter")
        self.wait(lambda: self.attr("#detail", "data-id") == item_id, "typing the id %s did not open it (status: %r)" % (item_id, self.text("#status")))

    def detail(self):
        return (self.attr("#detail", "data-kind"), self.attr("#detail", "data-id"))

    def envelope(self):
        self.view("keep")
        self.click("#pk-export")
        self.wait(lambda: self.shown("#pk-export-out") and self.value("#pk-export-text").startswith("{"), "the casefile export did not appear")
        text = self.value("#pk-export-text")
        self.view("ledger")
        return text, json.loads(text)

    def data(self):
        return json.dumps(self.envelope()[1]["data"], sort_keys=True)

    def claim(self, cid):
        for c in self.envelope()[1]["data"]["claims"]:
            if c["id"] == cid:
                return c
        raise Failed("there is no claim %s in the exported data" % cid)

    def csvs(self):
        self.view("keep")
        self.click("#csv-export-go")
        self.wait(lambda: self.shown("#csv-export-out"), "the CSV export did not appear")
        out = (self.value("#csv-out-sources"), self.value("#csv-out-claims"))
        self.view("ledger")
        return out

    def import_csv(self, sources, claims):
        self.view("keep")
        self.fill("#csv-in-sources", sources)
        self.fill("#csv-in-claims", claims)
        self.click("#csv-import-go")

    def timed(self, kind, sel, value=""):
        ms = self.t.evaluate(TIMED_JS, [kind, sel, value])
        need(ms >= 0, "nothing matches %s" % sel)
        return ms

    def close(self):
        if self.own:
            self.context.close()
        else:
            self.page.close()


def read(name):
    return (FIX / name).read_bytes().decode("utf-8-sig")


def check_library(folder):
    """The two library files in `folder` are the ones its pocket-lib.sha256 describes. Returns the record."""
    folder = Path(folder)
    try:
        lines = [ln for ln in (folder / HASH_FILE).read_text(encoding="ascii").split("\n") if ln]
    except (OSError, UnicodeDecodeError):
        raise Failed("assets/%s is missing or unreadable" % HASH_FILE)
    record = {}
    for ln in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", ln)
        need(m is not None, 'assets/%s has a line that is not "HASH  NAME": %s' % (HASH_FILE, ln[:80]))
        need(m.group(2) not in record, "assets/%s names %s twice" % (HASH_FILE, m.group(2)))
        record[m.group(2)] = m.group(1)
    need(sorted(record) == sorted(LIBRARY), "assets/%s must name exactly %s" % (HASH_FILE, " and ".join(LIBRARY)))
    for name in LIBRARY:
        got = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        need(got == record[name], "assets/%s is not the released file: its SHA-256 starts %s and the record says %s" % (name, got[:16], record[name][:16]))
    return record


def stale_ids(today, days):
    """Claims of the EAA ledger with a source published (or, with no date, accessed) more than `days` ago."""
    ages = {}
    for row in csv.DictReader(io.StringIO(read("eaa-sources.csv"))):
        when = row["published"] or row["accessed"]
        ages[row["source_id"]] = (today - dt.date.fromisoformat(when)).days
    out = []
    for row in csv.DictReader(io.StringIO(read("eaa-claims.csv"))):
        if any(ages.get(s.strip(), -1) > days for s in row["source_ids"].split(";") if s.strip()):
            out.append(row["claim_id"])
    return out


def run_checker(cfg, sources_path, claims_path):
    """The checker's verdict on two files: (label, exit code, errors, advisories)."""
    if cfg["ledger_check"]:
        r = subprocess.run([sys.executable, str(cfg["ledger_check"]), str(sources_path), str(claims_path), "--json", "--today", cfg["today"].isoformat()], capture_output=True, text=True)
        label = "ledger_check.py"
    else:
        r = subprocess.run([sys.executable, str(HERE / "build_casefile.py"), str(sources_path), str(claims_path), "--check-only", "--json", "--today", cfg["today"].isoformat()], capture_output=True, text=True)
        label = "build_casefile.py --check-only (ledger_check.py was not given)"
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return label, r.returncode, None, (r.stderr or r.stdout).strip()[:160]
    return label, r.returncode, d["errors"], d["advisories"]


def make_large(folder, n_sources=300, n_claims=1000):
    """A SYNTHETIC ledger that passes the rules: 300 sources, 1,000 claims, 20 questions, 30 assessments."""
    tiers = ("primary", "secondary", "peer_reviewed", "aggregator", "secondary", "unverified")
    reads = ("full", "section", "full", "snippet", "section", "relayed")
    sources, good = [], set()
    for i in range(1, n_sources + 1):
        tier, read_level = tiers[i % 6], reads[(i * 7) % 6]
        address = "" if i % 11 == 0 else "https://example.org/source/%d" % i
        published = "" if i % 5 == 0 else "%d-%02d-%02d" % (2019 + i % 7, 1 + i % 12, 1 + i % 28)
        if published > "2026-09-30":
            published = "2026-09-%02d" % (1 + i % 28)
        sources.append(["S%d" % i, "SYNTHETIC source %d: a report with a title long enough to wrap on a narrow screen" % i, "Example publisher %d" % (i % 23),
                        address, tier, published, "2026-10-01", read_level, "F%d" % (i % 40) if i % 4 == 0 else "", ""])
        if tier in ("primary", "secondary", "peer_reviewed") and read_level in ("full", "section") and address:
            good.add(i)
    good_list = sorted(good)
    claims = []
    for i in range(1, n_claims + 1):
        a, b = 1 + (i * 37) % n_sources, 1 + (i * 91) % n_sources
        cited, status, locator, conf, bearing = [a], "REPORTED", "section %d" % (i % 9 + 1), "", "yes" if i % 7 == 0 else "no"
        if i % 10 == 3:
            status, cited, locator, bearing = "MODEL_OUTPUT", [], "", "no"
        elif i % 10 == 6:
            status, cited, locator, conf = "ASSESSMENT", [], "", ("high", "moderate", "low")[i % 3]
        elif i % 25 == 9:
            status, cited, locator = "GAP", [], ""
        elif i % 3 == 0:
            status, cited = "FACT", [good_list[i % len(good_list)], b]
        elif i % 4 == 0:
            cited = [a, b]
        claims.append(["C%d" % i, "Q%d" % (1 + i % 20), "SYNTHETIC claim %d: the measured value was %d units in region %d, as stated in the cited source." % (i, 100 + i * 3, i % 17),
                       status, ";".join("S%d" % s for s in dict.fromkeys(cited)), locator, bearing, conf, "", "", ""])
    for k in range(1, 41):              # forty conflicts on REPORTED pairs, half of them still open
        x, y = 20 * k + 1, 20 * k + 2
        cls = "direct_conflict" if k % 2 else "scope_mismatch"
        note = "" if k % 4 == 1 else "The later figure uses a wider region."
        claims[x - 1][8:11] = ["C%d" % y, cls, note]
        claims[y - 1][8:11] = ["C%d" % x, cls, note]
    extra = {"questions": [{"id": "Q%d" % q, "text": "SYNTHETIC question %d: what was measured in region %d, and by whom?" % (q, q)} for q in range(1, 21)],
             "assessments": [{"id": "A%d" % n, "question_id": "Q%d" % (1 + n % 20), "judgement": "SYNTHETIC judgement %d drawn from the claims listed." % n,
                              "likelihood": ("likely", "unlikely", "no basis")[n % 3], "confidence": ("high", "moderate", "low")[n % 3],
                              "confidence_reason": "SYNTHETIC reason.", "claim_ids": ["C%d" % (n * 31 + j) for j in range(1, 5)], "written": "2026-10-01"} for n in range(1, 31)]}
    for name, header, rows in (("large-sources.csv", ["source_id", "title", "publisher", "address", "tier", "published", "accessed", "read_level", "family", "notes"], sources),
                               ("large-claims.csv", ["claim_id", "question_id", "statement", "status", "source_ids", "locator", "load_bearing", "confidence", "conflicts_with", "conflict_class", "resolution"], claims)):
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
        (Path(folder) / name).write_text(buf.getvalue(), encoding="utf-8")
    (Path(folder) / "large-extra.json").write_text(json.dumps(extra), encoding="utf-8")
    out = Path(folder) / "large-casefile.html"
    r = subprocess.run([sys.executable, str(HERE / "build_casefile.py"), str(Path(folder) / "large-sources.csv"), str(Path(folder) / "large-claims.csv"),
                        "--extra", str(Path(folder) / "large-extra.json"), "--title", "SYNTHETIC large ledger", "--out", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("the large ledger did not build: " + (r.stdout + r.stderr).strip()[-300:])
    return out


def build_tests(cfg):
    notes = cfg["notes"]

    def loads_cleanly(new):
        s = new()
        s.page.wait_for_timeout(200)
        need(not s.errors, "; ".join(s.errors[:3]))
        need(not s.dialogs, "the page opened a %s dialog" % (s.dialogs or [""])[0])
        need(not s.outside, "the page made an outside request: %s" % (s.outside or [""])[0])
        need(s.t.evaluate("() => document.forms.length") == 0, "the page has a form element")
        for label, prepare in (("the ledger", lambda: None), ("an open claim", lambda: s.open("C3")), ("an open source", lambda: s.open("S1")),
                               ("an open assessment", lambda: s.open("A1")), ("the conflicts view", lambda: s.view("conflicts")),
                               ("the check view", lambda: s.view("check")),
                               ("a claim being edited", lambda: (s.open("C2"), s.click("#edit-item"))), ("a source being edited", lambda: (s.open("S3"), s.click("#edit-item"))),
                               ("a new assessment form", lambda: (s.view("ledger"), s.click("#add-assessment"))),
                               ("the keep view with its panels open", lambda: (s.view("keep"), s.click("#pk-export"), s.click("#csv-export-go"), s.click("#brief-go"), s.click("#pk-reset")))):
            prepare()
            twice = s.t.evaluate("() => { const seen = {}, dup = []; document.querySelectorAll('[id]').forEach(e => { if (seen[e.id]) dup.push(e.id); seen[e.id] = true; }); return dup; }")
            need(not twice, "in %s, the id %s is used by more than one element" % (label, ", ".join(sorted(set(twice))[:4])))
            for size in ("", "125%"):
                s.t.evaluate("(v) => { document.documentElement.style.fontSize = v; }", size)
                s.page.wait_for_timeout(80)
                out = s.t.evaluate(FIT_JS)
                need(not out, "in %s%s, %s runs off the side of the window" % (label, " with text 25 percent larger" if size else "", ", ".join(out)))
        need(not s.errors, "; ".join(s.errors[:3]))

    def library_copy_is_identical(new):
        page = Path(cfg["page"]).read_text(encoding="utf-8")
        for name in ("pocket-state.js", "pocket-ui.js"):
            begin, end = "/* pocket-embed: %s begin */" % name, "/* pocket-embed: %s end */" % name
            need(page.count(begin) == 1 and page.count(end) == 1, "the page has no marked copy of %s" % name)
            pasted = page[page.index(begin) + len(begin):page.index(end)].strip("\n")
            own = (ASSETS / name).read_text(encoding="utf-8").rstrip("\n")
            need(pasted == own, "the copy of %s pasted into the page differs from assets/%s" % (name, name))
        record = check_library(cfg.get("library", ASSETS))
        if "library_note" not in cfg:
            cfg["library_note"] = True
            notes.append("library copy: the pocket-state.js and pocket-ui.js pasted into the page are identical to assets, and assets has the recorded release (sha256 %s and %s, first 16 characters)"
                         % (record["pocket-state.js"][:16], record["pocket-ui.js"][:16]))

    def t01_lineage_both_ways(new):
        s = new()
        s.click('[data-open="assessment:A1"]')
        s.wait(lambda: s.detail() == ("assessment", "A1"), "opening A1 from the ledger did not show it")
        for cid in ("C1", "C2", "C4"):
            need(s.count('#rests-on [data-go="claim:%s"]' % cid) == 1, "A1 does not show %s among the claims it rests on" % cid)
        need(s.count('#rests-on [data-go="source:S1"]') == 1, "A1's line of support does not reach source S1 under C1")
        need("1 REPORTED claim (C2)" in s.text("#weakest"), "A1's weakest support should be named as 1 REPORTED claim (C2); the page says %r" % s.text("#weakest"))
        s.click('#rests-on [data-go="claim:C1"]')
        s.wait(lambda: s.detail() == ("claim", "C1"), "one click on C1 under A1 did not open C1")
        need(s.count('#supports [data-go="assessment:A1"]') == 1, "C1 does not show that A1 rests on it")
        s.click('#rests-on [data-go="source:S1"]')
        s.wait(lambda: s.detail() == ("source", "S1"), "one click on S1 under C1 did not open S1")
        facts = s.text("#detail")
        for wanted in ("primary", "read in full", "2021-08-12", "2026-10-08"):
            need(wanted in facts, "source S1 does not show %r (tier, read level and dates are needed)" % wanted)
        need(s.count('#dependents [data-go="claim:C1"]') == 1, "S1 does not list C1 as depending on it")
        need(s.count('#dependents [data-go="assessment:A1"]') == 1, "S1 does not show the assessment downstream of C1")
        s.click('#dependents [data-go="assessment:A1"]')
        s.wait(lambda: s.detail() == ("assessment", "A1"), "one click on A1 under S1 did not open A1")
        need(not s.errors, "; ".join(s.errors[:3]))

    def t02_if_this_source_falls(new):
        s = new()
        s.open("S3")
        need(s.count('#falls [data-falls-claim="C2"]') == 1, "withdrawing S3 does not name C2: %r" % s.text("#falls"))
        need("no source at all" in s.text('#falls [data-falls-claim="C2"]'), "C2 should be said to be left with no source: %r" % s.text('#falls [data-falls-claim="C2"]'))
        need(s.count('#falls [data-falls-assessment="A1"]') == 1 and "C2" in s.text('#falls [data-falls-assessment="A1"]'), "withdrawing S3 does not name A1 as resting on C2: %r" % s.text("#falls"))
        need(s.count('#falls [data-falls-claim="C8"]') == 0 and s.count('#falls [data-falls-still="C8"]') == 1, "C8 also cites S4, which was opened, so it should be listed as still supported")
        s.open("S4")              # the neighbour: without S4, C3 still has S5 and C8 still has S3, and both were opened
        need(s.count('#falls [data-falls-claim]') == 0, "withdrawing S4 leaves C3 with S5 and C8 with S3, both opened; nothing should be listed as unsupported: %r" % s.text("#falls"))
        s.open("S1")
        need(s.count('#falls [data-falls-claim="C1"]') == 1 and s.count('#falls [data-falls-assessment="A1"]') == 1, "withdrawing S1 should name C1 and A1: %r" % s.text("#falls"))

    def t03_refused_status_change(new):
        s = new()
        before = s.data()
        s.open("C2")
        s.click('#detail [data-status="FACT"]')
        s.wait(lambda: s.count("#refusal") == 1, "setting C2 to FACT gave no refusal (status line: %r)" % s.text("#status"))
        need(C2_REASON in s.text("#refusal"), "the refusal does not give the checker's reason: %r" % s.text("#refusal"))
        need(s.attr('#detail [data-status="REPORTED"]', "aria-pressed") == "true" and s.attr('#detail [data-status="FACT"]', "aria-pressed") == "false", "after the refusal the page shows C2 as something other than REPORTED")
        need(s.data() == before, "the refused change altered the data")
        s.open("S3")
        s.click("#edit-item")
        s.fill("#f-address", "https://example.org/found-again")
        s.click("#form-save")
        s.wait(lambda: s.detail() == ("source", "S3") and "https://example.org/found-again" in s.text("#detail"), "the address was not saved on S3: %r" % s.text("#form-problems"))
        s.open("C2")
        s.click('#detail [data-status="FACT"]')
        s.wait(lambda: s.attr('#detail [data-status="FACT"]', "aria-pressed") == "true", "with an address on S3, C2 should be allowed to become a FACT: %r" % s.text("#refusal"))
        need(s.count("#refusal") == 0, "a refusal is still showing after the change was allowed")
        need(s.claim("C2")["status"] == "FACT", "the page shows FACT and the exported data does not")
        s.click("#pk-undo")
        s.wait(lambda: s.claim("C2")["status"] == "REPORTED", "undo did not put C2 back to REPORTED")
        s.open("C2")
        need(s.attr('#detail [data-status="REPORTED"]', "aria-pressed") == "true", "after undo the page does not show C2 as REPORTED")
        need(not s.errors, "; ".join(s.errors[:3]))

    def t04_model_output_not_load_bearing(new):
        s = new()
        before = s.data()
        s.open("C5")
        s.click("#lb-toggle")
        s.wait(lambda: s.count("#refusal") == 1, "marking C5 load-bearing gave no refusal")
        need(C5_REASON in s.text("#refusal"), "the refusal does not give the checker's reason: %r" % s.text("#refusal"))
        need(s.attr("#lb-toggle", "aria-pressed") == "false", "C5 is shown as load-bearing after the refusal")
        need(s.data() == before, "the refused change altered the data")
        s.open("C3")
        s.click("#lb-toggle")
        s.wait(lambda: s.attr("#lb-toggle", "aria-pressed") == "true", "the valid neighbour, a REPORTED claim, could not be marked load-bearing: %r" % s.text("#refusal"))
        need(s.claim("C3")["load_bearing"] is True, "C3 is shown as load-bearing and the data does not say so")

    def t05_conflict_recorded_and_settled(new):
        s = new()
        need(s.text("#att-conflicts").startswith("0 open"), "the example should start with no open conflict: %r" % s.text("#att-conflicts"))
        before = s.data()
        s.view("conflicts")
        for a, b, why in (("C3", "C3", "itself"), ("C3", "C99", "no claim C99"), ("C2", "C5", "already")):
            s.fill("#cf-a", a)
            s.fill("#cf-b", b)
            s.click("#cf-go")
            s.wait(lambda: s.text("#cf-msg").startswith("Not recorded.") and why in s.text("#cf-msg"), "recording %s against %s should be refused mentioning %r: %r" % (a, b, why, s.text("#cf-msg")))
        need(s.data() == before, "a refused conflict altered the data")
        s.view("conflicts")
        s.fill("#cf-a", "C3")
        s.fill("#cf-b", "C8")
        s.t.locator("#cf-class").first.select_option("direct_conflict")
        s.click("#cf-go")
        s.wait(lambda: s.count('[data-pair="C3|C8"]') == 1, "the conflict between C3 and C8 was not recorded: %r" % s.text("#cf-msg"))
        need(s.attr('[data-pair="C3|C8"]', "data-open") == "true", "a new direct conflict should be open")
        need(s.text("#att-conflicts").startswith("1 open conflict (1 direct)"), "the open count on the main screen should read 1 open conflict (1 direct): %r" % s.text("#att-conflicts"))
        need(s.text("#n-conflicts") == "2", "the Conflicts view should now count 2 pairs: %r" % s.text("#n-conflicts"))
        d = json.loads(s.data())
        c3, c8 = [c for c in d["claims"] if c["id"] == "C3"][0], [c for c in d["claims"] if c["id"] == "C8"][0]
        need(c3["conflicts_with"] == ["C8"] and c8["conflicts_with"] == ["C3"] and c3["conflict_class"] == c8["conflict_class"] == "direct_conflict", "the conflict is not written on both claims: %r / %r" % (c3["conflicts_with"], c8["conflicts_with"]))
        for cid, other in (("C3", "C8"), ("C8", "C3")):
            s.open(cid)
            need(other in s.text("#conflict-line") and "direct conflict" in s.text("#conflict-line") and "open" in s.text("#conflict-line"), "%s does not show its open direct conflict with %s: %r" % (cid, other, s.text("#conflict-line")))
        s.view("conflicts")
        s.click('[data-pair="C3|C8"] [data-act="settle"]')
        s.wait(lambda: "Not changed." in s.text('[data-pair="C3|C8"] .pk-msg'), "settling with no note should be refused")
        need(s.text("#att-conflicts").startswith("1 open"), "an empty note settled the conflict")
        s.fill('[data-pair="C3|C8"] textarea', "C8 gives the date the Directive applies; C3 is about the standard. No real disagreement.")
        s.click('[data-pair="C3|C8"] [data-act="settle"]')
        s.wait(lambda: s.text("#att-conflicts").startswith("0 open"), "settling the conflict did not lower the open count: %r" % s.text("#att-conflicts"))
        d = json.loads(s.data())
        notes_on = [c["resolution"] for c in d["claims"] if c["id"] in ("C3", "C8")]
        need(len(set(notes_on)) == 1 and notes_on[0].startswith("C8 gives the date"), "the note is not on both claims: %r" % notes_on)
        s.click("#pk-undo")
        s.wait(lambda: s.text("#att-conflicts").startswith("1 open"), "undo did not reopen the conflict")

    def t06_exported_csv_passes_the_checker(new):
        s = new()
        sources, claims = s.csvs()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "sources.csv").write_text(sources, encoding="utf-8")
            (Path(td) / "claims.csv").write_text(claims, encoding="utf-8")
            label, code, errors, advisories = run_checker(cfg, Path(td) / "sources.csv", Path(td) / "claims.csv")
            need(errors is not None, "%s could not read the exported files: %s" % (label, advisories))
            _, code0, errors0, advisories0 = run_checker(cfg, FIX / "eaa-sources.csv", FIX / "eaa-claims.csv")
            need((code, errors, advisories) == (code0, errors0, advisories0), "%s gives a different result on the exported files: %d error(s) and %d advisory note(s), against %d and %d on the originals"
                 % (label, len(errors), len(advisories), len(errors0), len(advisories0)))
            need(code == 0 and not errors, "the exported ledger has errors: %r" % errors[:2])
            need(sources == read("eaa-sources.csv"), "the exported sources.csv is not byte-identical to the ledger the page was built from")
            need(claims == read("eaa-claims.csv"), "the exported claims.csv is not byte-identical to the ledger the page was built from")
            # after real changes the export must still be a ledger the checker accepts
            s.view("conflicts")
            s.fill("#cf-a", "C3")
            s.fill("#cf-b", "C8")
            s.click("#cf-go")
            s.wait(lambda: s.count('[data-pair="C3|C8"]') == 1, "could not record a conflict before the second export")
            sources2, claims2 = s.csvs()
            (Path(td) / "claims.csv").write_text(claims2, encoding="utf-8")
            (Path(td) / "sources.csv").write_text(sources2, encoding="utf-8")
            label, code2, errors2, advisories2 = run_checker(cfg, Path(td) / "sources.csv", Path(td) / "claims.csv")
            need(errors2 is not None and code2 == 0 and not errors2, "after recording a conflict the exported ledger is refused by %s: %r" % (label, errors2 if errors2 is not None else advisories2))
            need(len(advisories2) == len(advisories0) + 1 and any("claim C3: open direct conflict with C8" in a for a in advisories2), "the checker should add one note for the open conflict on C3: %r" % advisories2)
            header = claims2.split("\n", 1)[0]
            need(header.endswith("conflicts_with,conflict_class,resolution"), "the claims header lacks the conflict columns: %r" % header)
        if "t06" not in cfg:
            cfg["t06"] = True
            notes.append("t06 checker: %s. Unmodified example: %d error(s), %d advisory note(s) on the originals and on the exported files; exported files byte-identical to the originals" % (label, len(errors0), len(advisories0)))

    def t07_round_trip_and_refused_imports(new):
        a = new()
        a.open("C3")
        a.click("#lb-toggle")
        a.view("conflicts")
        a.fill("#cf-a", "C3")
        a.fill("#cf-b", "C8")
        a.click("#cf-go")
        a.wait(lambda: a.count('[data-pair="C3|C8"]') == 1, "could not make changes before exporting")
        text, env = a.envelope()
        need(list(env.keys()) == ["app", "schema", "content_id", "saved_at", "data"] and env["app"] == "casefile", "the export is not the state envelope: %r" % list(env.keys()))
        want = json.dumps(env["data"], sort_keys=True)
        b = new()
        need(b.data() != want, "a fresh page already holds the changed data")
        b.view("keep")
        b.fill("#pk-import-text", text)
        b.click("#pk-import")
        b.wait(lambda: b.text("#pk-import-msg").startswith("Imported"), "the exported casefile was not imported into a fresh page: %r" % b.text("#pk-import-msg"))
        need(b.data() == want, "after export and import the data is not identical")
        need(b.text("#att-conflicts").startswith("1 open conflict (1 direct)"), "the imported state is not what the page shows")

        def refused(label, do, said, where="#pk-import-msg", rows=False):
            do()
            b.wait(lambda: b.text(where).startswith("Not imported."), "%s was not refused: %r" % (label, b.text(where)))
            need(said in b.text(where), "refusing %s should say %r: %r" % (label, said, b.text(where)))
            if rows:
                items = b.t.locator("#csv-import-problems li").all_text_contents()
                need(items and all("line " in i for i in items), "refusing %s should list every problem with its row number: %r" % (label, items[:3]))
            need(b.data() == want, "after refusing %s the data is different" % label)

        def paste(payload):
            b.view("keep")
            b.fill("#pk-import-text", payload)
            b.click("#pk-import")
        refused("a pocket-app reading-log export", lambda: paste(OTHER_APP), 'This file was saved by "reading-log"')
        broken = json.loads(text)
        [c for c in broken["data"]["claims"] if c["id"] == "C5"][0]["load_bearing"] = True
        refused("a casefile that breaks a ledger rule", lambda: paste(json.dumps(broken)), "MODEL_OUTPUT cannot be load-bearing")
        newer = dict(env)
        newer["schema"] = env["schema"] + 1
        refused("a casefile from a newer schema", lambda: paste(json.dumps(newer)), "newer than this page")
        refused("malformed JSON", lambda: paste(text[:200]), "could not be read as JSON")
        good_s, good_c = read("eaa-sources.csv"), read("eaa-claims.csv")
        refused("the checker's bad sample ledger", lambda: b.import_csv(read("bad-sources.csv"), read("bad-claims.csv")), "13 errors", where="#csv-import-msg", rows=True)
        need(any("claim C5: MODEL_OUTPUT cannot be load-bearing" in i and "line 6" in i for i in b.t.locator("#csv-import-problems li").all_text_contents()), "the problem list should give claim C5's rule with its row, line 6")
        lines = good_c.split("\n")
        lines[3] = lines[3] + ",one cell too many"
        refused("a claims file with a row that has too many cells", lambda: b.import_csv(good_s, "\n".join(lines)), "line 4 has more cells than the header", where="#csv-import-msg")
        refused("a claims file with a quote that never closes", lambda: b.import_csv(good_s, good_c + 'C9,Q1,"a quote that is not closed,REPORTED,S1,x,no,,,,\n'), "opens on line 10 is never closed", where="#csv-import-msg")
        refused("a sources file with a column missing", lambda: b.import_csv(good_s.replace("read_level,", "", 1), good_c), "is missing column(s): read_level", where="#csv-import-msg")
        refused("the two files swapped", lambda: b.import_csv(good_c, good_s), "is missing column(s)", where="#csv-import-msg")
        refused("only one file", lambda: b.import_csv(good_s, ""), "Both files are needed", where="#csv-import-msg")
        # the valid neighbour: a sound ledger is imported, and undo brings the old one back.
        # Its claims are renamed N1 to N7 here, so that A1 no longer has its claims and the page must ask.
        other_claims = re.sub(r"\bC(\d+)\b", r"N\1", read("near-claims.csv"))
        b.import_csv(read("near-sources.csv"), other_claims)
        b.wait(lambda: b.shown("#csv-orphans") and "A1" in b.text("#csv-orphans-text"), "importing a ledger without A1's claims should ask before removing A1: %r" % b.text("#csv-import-msg"))
        b.click("#csv-orphans-no")
        need(b.data() == want, "the data changed although the question about the assessment was answered with Cancel")
        b.import_csv(read("near-sources.csv"), other_claims)
        b.click("#csv-orphans-yes")
        b.wait(lambda: b.text("#csv-import-msg").startswith("Imported 3 sources and 7 claims"), "the sound ledger was not imported: %r" % b.text("#csv-import-msg"))
        got = json.loads(b.data())
        need(len(got["sources"]) == 3 and len(got["claims"]) == 7 and not got["assessments"], "the imported ledger is not what the files hold")
        b.click("#pk-undo")
        b.wait(lambda: b.data() == want, "undo did not bring back the ledger that the import replaced")
        need(not b.errors and not a.errors, "; ".join((a.errors + b.errors)[:3]))

    def t08_reload_or_honest_note(new):
        s = new()
        s.open("C3")
        s.click("#lb-toggle")
        s.wait(lambda: s.attr("#lb-toggle", "aria-pressed") == "true", "could not make a change")
        if s.mode == "tab":
            s.wait(lambda: "Last saved" in s.text("#pk-note"), "the page never reported a save: %r" % s.text("#pk-note"))
            need(not s.shown("#top-note"), "a warning about saving is showing although the page saved")
            s.page.reload(timeout=20000)
            s.wait(lambda: s.count("#pk-note") == 1 and "Saved in this browser" in s.text("#pk-note"), "the page did not come back after a reload")
            need(s.claim("C3")["load_bearing"] is True, "the change was lost by a reload although the page said it was saved")
        else:
            need(s.shown("#top-note") and NOT_SAVED in s.text("#top-note-text"), "in the frame the page should say at the top that it cannot save: %r" % s.text("#top-note-text"))
            need(NOT_SAVED in s.text("#pk-note"), "the note in Keep should say the same: %r" % s.text("#pk-note"))
            need(s.claim("C3")["load_bearing"] is True, "export does not carry the change")
            sources, claims = s.csvs()
            need("C3,Q2," in claims and sources.startswith("source_id,"), "the CSV export does not work in the frame")
            s.view("keep")
            s.click("#brief-go")
            need(s.value("#brief-text").startswith("# EU accessibility"), "the brief does not work in the frame")
            s.click("#pk-copy")
            s.wait(lambda: "Copied" in s.text("#pk-export-msg") or "Copying was refused" in s.text("#pk-export-msg"), "Copy gave no answer in the frame")
            s.page.reload(timeout=20000)
            s.wait(lambda: s.count("#pk-note") == 1 and NOT_SAVED in s.text("#pk-note"), "the page did not come back after a reload")
            need(s.claim("C3")["load_bearing"] is False, "the frame kept data across a reload, which this test's frame cannot do")
        need(not s.errors, "; ".join(s.errors[:3]))

    def t09_large_ledger(new):
        s = new(page=cfg["large"])
        ms = {"open and draw (wall clock)": s.ready_ms, "first draw of the list": float(s.attr("#list", "data-render-ms") or 0)}
        need("300 sources, 1000 claims and 30 assessments" in s.text("#tally"), "the large ledger did not load: %r" % s.text("#tally"))
        need(s.count("#list .rowbtn") <= 200, "the list drew %d rows at once; it should draw a first part and offer more" % s.count("#list .rowbtn"))
        need(s.count("#show-more") == 1, "there is no way to see the claims beyond the first part")
        ms["search for a word"] = s.timed("input", "#flt-q", "claim 77")
        need("Showing" in s.text("#flt-summary") and s.count('[data-open="claim:C77"]') == 1, "the search did not find claim 77: %r" % s.text("#flt-summary"))
        ms["clear the search"] = s.timed("input", "#flt-q", "")
        s.click("#flt-more")
        ms["filter by status"] = s.timed("click", '[data-f-status="FACT"]')
        need("status FACT" in s.text("#flt-summary"), "the status filter did not apply: %r" % s.text("#flt-summary"))
        ms["add the load-bearing filter"] = s.timed("click", "#flt-lb")
        ms["open a claim's lineage"] = s.timed("click", '#list .rowbtn[data-open^="claim:"]')
        need(s.detail()[0] == "claim" and s.count("#rests-on .card") >= 1, "opening a claim did not show its sources")
        cid = s.detail()[1]
        ms["refuse or make a status change"] = s.timed("click", '#detail [data-status="REPORTED"]')
        s.wait(lambda: s.attr('#detail [data-status="REPORTED"]', "aria-pressed") == "true", "a FACT could not be set to REPORTED in the large ledger (%s): %r" % (cid, s.text("#refusal")))
        ms["undo"] = s.timed("click", "#pk-undo")
        s.open("A7")
        ms["open an assessment's lineage"] = s.timed("click", '#rests-on [data-go^="claim:"]')
        s.open("S37")
        need(s.count("#falls li") >= 1, "the large ledger's source shows nothing under If this source falls")
        s.view("conflicts")
        need(s.count("[data-pair]") == 40, "the large ledger should show 40 conflict pairs, and shows %d" % s.count("[data-pair]"))
        s.view("keep")
        ms["export the two CSV files"] = s.timed("click", "#csv-export-go")
        ms["build the brief"] = s.timed("click", "#brief-go")
        ms["export the casefile"] = s.timed("click", "#pk-export")
        size = len(s.value("#pk-export-text").encode("utf-8"))
        def limit(step):
            return 4000 if step.startswith("open and draw") else 2500 if step in WHOLE_LEDGER_STEPS else 700
        slow = {k: v for k, v in ms.items() if v > limit(k)}
        need(not slow, "too slow with 1,000 claims: " + ", ".join("%s %.0f ms" % kv for kv in slow.items()))
        need(not s.errors, "; ".join(s.errors[:3]))
        notes.append("t09 timings, %s at %dx%d, 300 sources and 1,000 claims (%d byte casefile export): %s" % (s.mode, s.size[0], s.size[1], size, "; ".join("%s %.0f ms" % kv for kv in ms.items())))

    def page_rules_agree_with_the_checker(new):
        expected = json.loads(read("expected.json"))["cases"]
        clock = " is in the future"            # the one rule that depends on the day the test is run
        s = new()
        for case in ("bad", "edge"):
            s.import_csv(read(case + "-sources.csv"), read(case + "-claims.csv"))
            s.wait(lambda: s.text("#csv-import-msg").startswith("Not imported."), "the %s ledger was not refused" % case)
            got = [re.sub(r"^(sources|claims) CSV, (line \d+: )?", "", x) for x in s.t.locator("#csv-import-problems li").all_text_contents()]
            want = expected[case]["errors"]
            got, want = [g for g in got if clock not in g], [w for w in want if clock not in w]
            only_page = [g for g in got if g not in want]
            only_checker = [w for w in want if w not in got]
            need(got == want, "the page and ledger_check.py disagree on the %s ledger. Only the page: %r. Only the checker: %r" % (case, only_page[:2], only_checker[:2]))
        s.import_csv(read("near-sources.csv"), re.sub(r"\bC(\d+)\b", r"N\1", read("near-claims.csv")))
        s.wait(lambda: s.shown("#csv-orphans"), "the ledger of valid neighbours should be found sound: %r" % s.text("#csv-import-msg"))
        s.click("#csv-orphans-no")
        s.view("check")
        got = [re.sub(r"^ADVISORY ", "", x.replace("Open " + x.split("Open ")[-1], "").strip()) if "Open " in x else x for x in s.t.locator('#check-list li[data-level="advisory"] p').all_text_contents()]
        got = [g.replace("ADVISORY ", "", 1).strip() for g in got]
        want = expected["eaa"]["advisories"]
        age = " days old and supports a load-bearing claim"
        need([g for g in got if age not in g] == [w for w in want if age not in w], "the page's advisory notes for the EAA ledger differ from ledger_check.py's: %r against %r" % (got, want))
        need(s.count('#check-list li[data-level="error"]') == 0, "the example should have no errors: %r" % s.text("#check-list"))
        if "agree" not in cfg:
            cfg["agree"] = True
            notes.append("page rules: the page's own errors for the bad ledger (%d) and the edge ledger (%d), and its advisory notes for the EAA ledger, match ledger_check.py's recorded output word for word (date-dependent lines aside)"
                         % (len(expected["bad"]["errors"]), len(expected["edge"]["errors"])))

    def filters_and_search(new):
        s = new()

        def rows():
            return [x.split(":")[1] for x in s.t.locator('#list .rowbtn[data-open^="claim:"]').evaluate_all("els => els.map(e => e.getAttribute('data-open'))")]
        need(rows() == ["C1", "C2", "C3", "C5", "C7", "C8", "C4", "C6"], "the ledger should list the eight claims under their questions: %r" % rows())
        s.click("#flt-more")
        s.click('[data-f-status="REPORTED"]')
        need(rows() == ["C2", "C3", "C8"], "status REPORTED should show C2, C3, C8: %r" % rows())
        s.click("#flt-lb")
        need(rows() == ["C2"], "REPORTED and load-bearing should show C2 only: %r" % rows())
        need("Showing 1 of 8 claims" in s.text("#flt-summary"), "the summary should say what is shown: %r" % s.text("#flt-summary"))
        s.click("#flt-clear")
        need(len(rows()) == 8, "Clear filters did not bring everything back")
        s.t.locator("#flt-question").first.select_option("Q2")
        need(rows() == ["C2", "C3", "C5", "C7", "C8"], "question Q2 should show its five claims: %r" % rows())
        s.click("#flt-clear")
        s.t.locator("#flt-tier").first.select_option("primary")
        need(rows() == ["C1", "C4"], "tier primary should show C1 and C4: %r" % rows())
        s.t.locator("#flt-tier").first.select_option("aggregator")
        need(rows() == ["C3"], "tier aggregator should show C3: %r" % rows())
        s.click("#flt-clear")
        s.click("#flt-stale")
        want = stale_ids(dt.date.today(), 365)
        need(sorted(rows()) == sorted(want), "sources older than 365 days should show %r: %r" % (want, rows()))
        s.fill("#flt-days", "99999")
        s.wait(lambda: s.count("#list .rowbtn") == 0 and "No claim matches" in s.text("#list"), "a filter that matches nothing should say so")
        s.fill("#flt-days", "abc")
        need("whole number" in s.text("#status"), "a day count that is not a number should be refused: %r" % s.text("#status"))
        s.click('#list [data-fk="clear-filters"]')
        need(len(rows()) == 8, "the way back from no results did not work")
        s.click("#flt-conflict")
        need(rows() == [], "no claim is in an open conflict in the example: %r" % rows())
        s.click("#flt-clear")
        s.fill("#flt-q", "etsi")
        need(rows() == ["C7"], "searching for etsi should find C7: %r" % rows())
        s.fill("#flt-q", "")
        s.click("#att-reported")
        need(rows() == ["C2"], "the count of load-bearing claims that are only REPORTED should lead to them: %r" % rows())
        s.click("#att-gaps")
        need(rows() == ["C7"], "the gap count should lead to the gap: %r" % rows())
        s.view("sources")
        s.t.locator("#flt-tier").first.select_option("secondary")
        got = s.t.locator('#list .rowbtn[data-open^="source:"]').evaluate_all("els => els.map(e => e.getAttribute('data-open'))")
        need(got == ["source:S3", "source:S4"], "the sources view filtered to secondary should show S3 and S4: %r" % got)
        s.view("check")
        need("0 errors and 8 advisory notes" in s.text("#check-sum") or dt.date.today() > dt.date(2027, 10, 8), "the check view should report 0 errors and 8 advisory notes for the example: %r" % s.text("#check-sum"))
        need(not s.errors, "; ".join(s.errors[:3]))

    def add_edit_delete_with_rules(new):
        s = new()
        start = s.data()
        s.view("sources")
        s.click("#add-source")
        s.fill("#f-title", "A new SYNTHETIC source")
        s.fill("#f-address", "https://example.org/new")
        s.fill("#f-accessed", "2026-02-30")
        s.click("#form-save")
        s.wait(lambda: "is not a real date written YYYY-MM-DD" in s.text("#form-problems"), "a date that does not exist should be refused: %r" % s.text("#form-problems"))
        s.fill("#f-accessed", "2999-01-01")
        s.click("#form-save")
        s.wait(lambda: "is in the future" in s.text("#form-problems"), "a date in the future should be refused: %r" % s.text("#form-problems"))
        need(s.data() == start, "a refused source was added")
        s.view("sources")
        s.click("#add-source")
        s.fill("#f-title", "A new SYNTHETIC source")
        s.fill("#f-address", "https://example.org/new")
        s.click("#form-save")
        s.wait(lambda: s.detail() == ("source", "S6"), "a sound source was not added: %r" % s.text("#form-problems"))
        s.view("ledger")
        s.click("#add-claim")
        s.fill("#f-statement", "A new SYNTHETIC claim resting on the new source.")
        s.t.locator("#f-status").first.select_option("FACT")
        s.fill("#f-source_ids", "S6")
        s.click("#form-save")
        s.wait(lambda: "claim C9: is a FACT with no locator. Record where in the source it is" in s.text("#form-problems"), "a FACT with no locator should be refused in the checker's words: %r" % s.text("#form-problems"))
        s.fill("#f-locator", "paragraph 2")
        s.click("#form-save")
        s.wait(lambda: s.detail() == ("claim", "C9"), "with a locator the FACT should be added: %r" % s.text("#form-problems"))
        s.view("ledger")
        s.click("#add-assessment")
        s.fill("#f-judgement", "A SYNTHETIC judgement.")
        s.click("#form-save")
        s.wait(lambda: "is an assessment with no confidence" in s.text("#form-problems") and "An assessment cannot rest on nothing" in s.text("#form-problems"), "an assessment with no confidence and no claims should be refused for both reasons: %r" % s.text("#form-problems"))
        s.t.locator("#f-confidence").first.select_option("low")
        s.fill("#f-claim_ids", "C9; C404")
        s.click("#form-save")
        s.wait(lambda: "rests on unknown claim(s) C404" in s.text("#form-problems"), "an assessment resting on a claim that does not exist should be refused: %r" % s.text("#form-problems"))
        s.fill("#f-claim_ids", "C9")
        s.click("#form-save")
        s.wait(lambda: s.detail() == ("assessment", "A2"), "a sound assessment was not added: %r" % s.text("#form-problems"))
        need("1 FACT" in s.text("#support"), "A2 should say it rests on 1 FACT claim: %r" % s.text("#support"))
        for item, reason in (("S6", "is cited by C9"), ("C9", "An assessment cannot rest on nothing")):
            s.open(item)
            s.click("#delete-item")
            s.wait(lambda: s.shown("#delete-yes"), "delete did not ask first")
            need(s.t.evaluate("() => document.activeElement && document.activeElement.id") == "delete-no", "focus should be on Keep it")
            s.click("#delete-yes")
            s.wait(lambda: s.count("#refusal") == 1 and reason in s.text("#refusal"), "deleting %s should be refused because it %s: %r" % (item, reason, s.text("#refusal")))
        for item in ("A2", "C9", "S6"):
            s.open(item)
            s.click("#delete-item")
            s.click("#delete-yes")
            s.wait(lambda: item in s.text("#status") and "Deleted" in s.text("#status"), "%s was not deleted: %r" % (item, s.text("#status")))
        d = json.loads(s.data())
        need([x["id"] for x in d["sources"]] == ["S1", "S2", "S3", "S4", "S5"] and len(d["claims"]) == 8 and len(d["assessments"]) == 1, "after deleting what was added the ledger is not back to its items")
        need(len(d["log"]) == 7, "the activity log should hold the build note and six changes, and holds %d entries" % len(d["log"]))
        s.click("#pk-undo")
        s.wait(lambda: len(json.loads(s.data())["sources"]) == 6, "undo did not bring the deleted source back")
        s.to_list()
        s.click("#rename")
        s.fill("#f-title", "")
        s.click("#form-save")
        s.wait(lambda: "needs a name" in s.text("#form-problems"), "an empty name should be refused: %r" % s.text("#form-problems"))
        s.fill("#f-title", "A renamed SYNTHETIC casefile")
        s.t.locator("#f-title").first.press("Enter")
        s.wait(lambda: s.text("#title") == "A renamed SYNTHETIC casefile", "the casefile was not renamed: %r" % s.text("#title"))
        need(not s.dialogs, "the page used a %s dialog" % (s.dialogs or [""])[0])
        need(not s.errors, "; ".join(s.errors[:3]))

    def brief_is_built_from_the_ledger(new):
        s = new()
        s.view("keep")
        s.click("#brief-go")
        text = s.value("#brief-text")
        need(text.startswith("# EU accessibility standards and SC 2.5.8\n"), "the brief should start with the casefile's title")
        need("## Answer\n\n(Write the answer here." in text, "the answer must be left for the user to write")
        for cid in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "A1"):
            need("(" + cid in text or "**" + cid + "**" in text, "the brief does not list %s" % cid)
        for tagged in ("[FACT] EN 301 549 V3.2.1", "[REPORTED] As of August 2026", "[MODEL_OUTPUT] SC 2.5.8 has been legally required", "(C5) Not evidence until what it cites has been opened.", "[GAP] Whether the Official Journal", "[ASSESSMENT, moderate confidence] Do not describe"):
            need(tagged in text, "the brief should carry the tag and statement %r" % tagged)
        need("- S1. Commission Implementing Decision" in text and "Tier: primary. Read in full. Published 2021-08-12, accessed 2026-10-08. https://eur-lex.europa.eu/eli/dec_impl/2021/1339/oj" in text, "the brief should list S1 with tier, read level, dates and address")
        need("- S3." in text and "No address kept." in text, "the brief should say that S3 has no address")
        need("## Open conflicts\n\nNone." in text and "## Conflicts settled or explained\n\n- C2 and C5, insufficient evidence." in text, "the brief should report no open conflict and the settled one")
        need("## Gaps\n\n- [GAP] Whether the Official Journal" in text, "the brief should list the gap")
        need("Weakest support: 1 REPORTED claim (C2)" in text, "the brief should say what the assessment rests on")
        need(chr(0x2014) not in text and chr(0x2013) not in text, "the brief contains a dash character the ledger does not")
        need(s.attr("#brief-dl", "download") == "brief.md", "the brief has no download name")

    def unreadable_built_ledger_is_reported(new):
        page = Path(cfg["page"]).read_text(encoding="utf-8")
        start = page.index('<script type="application/json" id="casefile-data">') + len('<script type="application/json" id="casefile-data">')
        end = page.index("</script>", start)
        block = json.loads(page[start:end])
        [c for c in block["data"]["claims"] if c["id"] == "C5"][0]["load_bearing"] = True
        cases = (("a data block cut short", page[:start] + page[start:end][:300] + page[end:], "could not be read"),
                 ("a built ledger that breaks a rule", page[:start] + json.dumps(block).replace("<", "\\" + "u003c") + page[end:], "MODEL_OUTPUT cannot be load-bearing"))
        for label, text, said in cases:
            broken = Path(cfg["page"]).parent / "broken-data.html"
            broken.write_text(text, encoding="utf-8")
            s = new(page=broken)
            need(s.shown("#load-error") and said in s.text("#load-error-text"), "%s should be reported at the top of the page: %r" % (label, s.text("#load-error-text")))
            need("Nothing in the ledger yet" in s.text("#tally") and "no ledger yet" in s.text("#list"), "with %s the page should start empty and say so" % label)
            need(not s.errors, "; ".join(s.errors[:3]))

    both = [loads_cleanly, t01_lineage_both_ways, t02_if_this_source_falls, t03_refused_status_change, t04_model_output_not_load_bearing,
            t05_conflict_recorded_and_settled, t06_exported_csv_passes_the_checker, t07_round_trip_and_refused_imports, t08_reload_or_honest_note]
    if cfg["large"]:
        both.append(t09_large_ledger)
    both += [page_rules_agree_with_the_checker, filters_and_search, add_edit_delete_with_rules, brief_is_built_from_the_ledger, unreadable_built_ledger_is_reported]
    return [library_copy_is_identical], both


def run_suite(browser, cfg, only=None, modes=None, sizes=None):
    results = []
    once, both = build_tests(cfg)
    with tempfile.TemporaryDirectory() as td:
        for fn in once:
            if only and fn.__name__ not in only:
                continue
            ok, detail = True, ""
            try:
                fn(None)
            except Failed as e:
                ok, detail = False, str(e)
            results.append({"mode": "file", "size": "", "name": fn.__name__, "ok": ok, "detail": detail})
        for size in (sizes or cfg["sizes"]):
            for mode in (modes or cfg["modes"]):
                for fn in both:
                    if only and fn.__name__ not in only:
                        continue
                    opened = []

                    def new(page=None, context=None, init_script=None, mode=mode, size=size, opened=opened):
                        s = Session(browser, page or cfg["page"], mode, size, td, context=context, init_script=init_script)
                        opened.append(s)
                        return s
                    ok, detail, started = True, "", time.time()
                    try:
                        fn(new)
                    except Failed as e:
                        ok, detail = False, str(e)
                    except Exception as e:  # noqa: BLE001
                        ok, detail = False, "the test could not finish: " + str(e).split("\n")[0][:200]
                    for s in reversed(opened):
                        try:
                            s.close()
                        except Exception:  # noqa: BLE001
                            pass
                    results.append({"mode": mode, "size": "%dx%d" % size, "name": fn.__name__, "ok": ok, "detail": detail, "seconds": round(time.time() - started, 1)})
    return results


def build_example(folder):
    out = Path(folder) / "eu-accessibility-casefile.html"
    r = subprocess.run([sys.executable, str(HERE / "build_casefile.py"), str(FIX / "eaa-sources.csv"), str(FIX / "eaa-claims.csv"), "--extra", str(FIX / "eaa-extra.json"),
                        "--title", "EU accessibility standards and SC 2.5.8", "--out", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("the example did not build: " + (r.stdout + r.stderr).strip()[-300:])
    return out


def main(argv):
    flags, opts, it = set(), {}, iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("test_casefile: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v.strip()
        else:
            print("test_casefile: unknown argument " + a, file=sys.stderr)
            return 2
    sizes = []
    for part in opts.get("--sizes", "390x844,1280x800").split(","):
        w, _, h = part.strip().partition("x")
        if not (w.isdigit() and h.isdigit() and int(w) >= 200 and int(h) >= 200):
            print("test_casefile: --sizes needs WIDTHxHEIGHT pairs such as 390x844,1280x800", file=sys.stderr)
            return 2
        sizes.append((int(w), int(h)))
    modes = [m.strip() for m in opts.get("--modes", "tab,frame").split(",") if m.strip()]
    if not modes or any(m not in ("tab", "frame") for m in modes):
        print("test_casefile: --modes takes tab, frame or both", file=sys.stderr)
        return 2
    ledger_check = None
    if "--ledger-check" in opts:
        ledger_check = Path(opts["--ledger-check"])
        if not ledger_check.is_file():
            print("test_casefile: cannot read " + str(ledger_check), file=sys.stderr)
            return 2
    only = [opts["--only"]] if "--only" in opts else None
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 3
    with tempfile.TemporaryDirectory() as td, sync_playwright() as p:
        try:
            page = build_example(td)
            large = None if ("--no-large" in flags or "--planted" in flags) else make_large(td)
        except RuntimeError as e:
            print("test_casefile: %s" % e, file=sys.stderr)
            return 2
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e).split("\n")[0][:120])
            return 3
        cfg = {"page": page, "large": large, "sizes": sizes, "modes": modes, "ledger_check": ledger_check, "today": dt.date.today(), "notes": []}
        if "--planted" in flags:
            source = page.read_text(encoding="utf-8")
            missed, lines = 0, []
            for plant in PLANTED:
                text = source
                if "library" in plant:
                    # A copy of the three library files with one altered; only the record check is run on it.
                    name, extra = plant["library"]
                    copy = Path(td) / ("library-" + plant["id"])
                    copy.mkdir()
                    for f in LIBRARY + (HASH_FILE,):
                        (copy / f).write_bytes((ASSETS / f).read_bytes())
                    (copy / name).write_bytes((copy / name).read_bytes() + extra.encode("ascii"))
                    try:
                        check_library(copy)
                        missed += 1
                        lines.append("PLANTED %s: NOT CAUGHT by library_copy_is_identical. %s" % (plant["id"], plant["what"]))
                    except Failed as e:
                        lines.append("PLANTED %s: caught. %s" % (plant["id"], plant["what"]))
                        lines.append("    library_copy_is_identical FAILED: %s" % str(e)[:170])
                    continue
                for old, new_text in plant["edits"]:
                    if text.count(old) != 1:
                        browser.close()
                        print("test_casefile: planted failure %s no longer matches the engine page; update PLANTED" % plant["id"], file=sys.stderr)
                        return 2
                    text = text.replace(old, new_text)
                broken = Path(td) / ("planted-" + plant["id"] + ".html")
                broken.write_text(text, encoding="utf-8")
                res = run_suite(browser, dict(cfg, page=broken, large=None, notes=[]), only=plant["caught_by"], modes=["tab"], sizes=[(1280, 800)])
                failed = {r["name"]: r["detail"] for r in res if not r["ok"]}
                not_caught = [n for n in plant["caught_by"] if n not in failed]
                if not_caught:
                    missed += 1
                    lines.append("PLANTED %s: NOT CAUGHT by %s. %s" % (plant["id"], ", ".join(not_caught), plant["what"]))
                else:
                    lines.append("PLANTED %s: caught. %s" % (plant["id"], plant["what"]))
                    for n in plant["caught_by"]:
                        lines.append("    %s FAILED: %s" % (n, failed[n][:170]))
            browser.close()
            lines.append("RESULT: %s" % ("FAIL. %d planted failure(s) were not caught." % missed if missed else "PASS. %d of %d planted failures were caught by their named tests." % (len(PLANTED), len(PLANTED))))
            print("\n".join(lines).encode("ascii", "replace").decode("ascii"))
            return 1 if missed else 0
        results = run_suite(browser, cfg, only=only)
        browser.close()
    if only and not results:
        print("test_casefile: no test is named " + only[0], file=sys.stderr)
        return 2
    failed = [r for r in results if not r["ok"]]
    if "--json" in flags:
        text = json.dumps({"results": results, "notes": cfg["notes"], "checker": "ledger_check.py" if ledger_check else "build_casefile.py"}, indent=1, ensure_ascii=True)
    else:
        L = ["test_casefile: the EAA example, built now from the fixtures"]
        for r in results:
            L.append("  %-4s %-5s %-9s %s%s" % ("PASS" if r["ok"] else "FAIL", r["mode"], r["size"], r["name"], ("\n         " + r["detail"]) if r["detail"] else ""))
        L += ["  NOTE  " + n for n in cfg["notes"]]
        L.append("RESULT: %s. %d of %d tests passed. The frame is a local stand-in for a chat preview, not the real host."
                 % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    sys.stdout.write(text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
