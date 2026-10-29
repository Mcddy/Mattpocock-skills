#!/usr/bin/env python3
"""Tests for sitrep_diff.py and watch_check.py, with planted faults. Standard library only.

Usage:
  python test_sitrep_diff.py                 run every named test against the scripts beside this file
  python test_sitrep_diff.py --only NAME     run one test
  python test_sitrep_diff.py --dir FOLDER    test the copies of the two scripts in FOLDER
  python test_sitrep_diff.py --mutants       plant each fault below in a temporary copy and require
                                             the named test to fail on it

Every watch file used here is SYNTHETIC and is built by this script in a temporary folder, which it
removes afterwards. Nothing in the skill folder is written to.

Why --mutants exists: a test that has never failed has not been shown to test anything. Each planted
fault is a small edit to a copy of a script (for example: label withdrawn items as false; match
items by similar text). The run fails if a fault is not caught by the test named for it.

Each refusal is paired with its valid neighbour: the smallest change that turns the refused input
into an accepted one is run in the same test and must pass.

Exit codes: 0 every test passed (with --mutants: every fault was caught). 1 otherwise. 2 bad arguments.
"""
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ("sitrep_diff.py", "watch_check.py")
BASE_DAY, NEXT_DAY = "2026-09-01", "2026-09-08"


def base():
    """A small SYNTHETIC watch at its baseline run."""
    src = lambda i, title, tier: {"id": i, "title": title, "address": "https://example.org/" + i.lower(), "tier": tier,
                                  "check": "each run", "last_checked": BASE_DAY, "last_result": "reached"}
    ind = lambda i, r, w: {"id": i, "requirement": r, "watch_for": w, "where": "official register", "would_mean": "The answer to the requirement changes",
                           "status": "not seen", "seen_on": None, "evidence": []}
    item = lambda i, r, s, st, sids: {"id": i, "requirement": r, "statement": s, "status": st, "source_ids": sids, "as_of": BASE_DAY}
    return {
        "watch_id": "test-watch", "schema": 1, "title": "SYNTHETIC test watch", "purpose": "Exercise the comparison",
        "requirements": [{"id": "R1", "question": "Has the rule been published?", "priority": "high"},
                         {"id": "R2", "question": "What is the fee?", "priority": "low"}],
        "indicators": [ind("I1", "R1", "The register lists the rule with a number"), ind("I2", "R2", "The fee schedule shows a fee above 100")],
        "sources": [src("S1", "Official register", "primary"), src("S2", "Trade press note", "secondary"), src("S3", "Forum post", "unverified")],
        "state": [item("F1", "R1", "The rule had not been published when the register was read.", "FACT", ["S1"]),
                  item("F2", "R1", "A draft of the rule is expected within weeks.", "REPORTED", ["S2"]),
                  item("F3", "R2", "The fee is 80.", "FACT", ["S1"]),
                  item("F4", "R2", "A forum post says the fee will double.", "REPORTED", ["S3"])],
        "runs": [{"date": BASE_DAY, "summary": "Baseline.", "changes": 0}]}


def later(d, day=NEXT_DAY, changes=0):
    """The same watch one run on: every source reached, every item rechecked, nothing changed."""
    n = copy.deepcopy(d)
    n["runs"].append({"date": day, "summary": "Run.", "changes": changes})
    for s in n["sources"]:
        s["last_checked"], s["last_result"] = day, "reached"
    for f in n["state"]:
        f["as_of"] = day
    return n


def find(rows, i):
    return next(x for x in rows if x["id"] == i)


class Box:
    def __init__(self, folder, tmp):
        self.folder, self.tmp, self.n = Path(folder), Path(tmp), 0

    def write(self, obj):
        self.n += 1
        p = self.tmp / ("w%03d.json" % self.n)
        p.write_bytes(obj if isinstance(obj, bytes) else json.dumps(obj, indent=1).encode("utf-8"))
        return str(p)

    def run(self, script, *args):
        r = subprocess.run([sys.executable, "-B", str(self.folder / script)] + list(args), capture_output=True, timeout=60)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    def diff(self, old, new, *args):
        return self.run("sitrep_diff.py", self.write(old), self.write(new), *args)

    def diff_json(self, old, new, *args):
        code, out, err = self.diff(old, new, "--json", *args)
        return code, json.loads(out)

    def check(self, d, *args):
        return self.run("watch_check.py", self.write(d), *args)


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def ids(rows):
    return [x["id"] for x in rows]


# ---------------- comparison ----------------

def test_unchanged_run_is_one_line(b):
    code, out, err = b.diff(base(), later(base()))
    need(code == 0, "exit %d" % code)
    lines = [x for x in out.splitlines() if x.strip()]
    need(len(lines) == 1, "an unchanged run printed %d lines, not 1:\n%s" % (len(lines), out))
    need("NO CHANGE" in lines[0] and "4 of 4" in lines[0], "the line does not say NO CHANGE with the count: " + lines[0])


def test_unchanged_markdown_is_one_line(b):
    code, out, err = b.diff(base(), later(base()), "--markdown")
    lines = [x for x in out.splitlines() if x.strip()]
    need(code == 0 and len(lines) == 1 and lines[0].startswith("**Sitrep, changes since last run.**") and ("No change since " + BASE_DAY) in lines[0],
         "markdown for an unchanged run:\n" + out)


def test_markdown_first_line_names_the_method(b):
    n = later(base(), changes=1)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    code, out, err = b.diff(base(), n, "--markdown")
    first = out.splitlines()[0] if out else ""
    need(code == 0 and first.startswith("**Sitrep, changes since last run.**") and NEXT_DAY in first and BASE_DAY in first and "1 change(s)" in first,
         "the skeleton does not open with the method name, the two run dates and the count:\n" + first)


def test_new_item_is_listed_as_new(b):
    n = later(base(), changes=1)
    n["state"].append({"id": "F5", "requirement": "R2", "statement": "The fee schedule now lists a late fee of 20.", "status": "FACT", "source_ids": ["S1"], "as_of": NEXT_DAY})
    code, r = b.diff_json(base(), n)
    need(code == 0, "exit %d" % code)
    need(ids(r["state"]["new"]) == ["F5"] and not r["state"]["changed"] and not r["state"]["withdrawn"], "state: %s" % json.dumps(r["state"])[:300])
    need(r["change_count"] == 1 and r["no_change"] is False, "count %s" % r["change_count"])


def test_changed_item_shows_old_and_new(b):
    n = later(base(), changes=1)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    code, r = b.diff_json(base(), n)
    ch = r["state"]["changed"]
    need(code == 0 and ids(ch) == ["F3"], "changed: %s" % ids(ch))
    need(ch[0]["old"]["statement"] == "The fee is 80." and ch[0]["new"]["statement"] == "The fee is 95.", "old and new statement are not both carried")
    code, out, err = b.diff(base(), n)
    need("was: The fee is 80." in out and "now: The fee is 95." in out, "the text output does not show was and now:\n" + out)


def test_recheck_with_same_text_is_unchanged(b):
    n = later(base())
    find(n["state"], "F3")["statement"] = "The  fee is   80."
    code, r = b.diff_json(base(), n)
    need(code == 0 and r["no_change"] is True and "F3" in r["state"]["unchanged_rechecked"], "a recheck with only spacing changed was counted as a change")


def test_withdrawn_item_is_listed_as_withdrawn(b):
    n = later(base(), changes=1)
    n["state"] = [f for f in n["state"] if f["id"] != "F2"]
    code, r = b.diff_json(base(), n)
    need(code == 0, "exit %d: %s" % (code, r.get("errors")))
    need(ids(r["state"]["withdrawn"]) == ["F2"] and not r["state"]["dropped"], "withdrawn: %s" % ids(r["state"]["withdrawn"]))
    need(r["state"]["withdrawn"][0]["statement"].startswith("A draft of the rule"), "the withdrawn item's old statement is not carried")


BANNED = re.compile(r"\b(false|untrue|disproved|disproven|refuted|debunked|incorrect|wrong|no longer true|not true)\b", re.I)
ALLOWED = ("not a finding that it is false", "not the same as false")


def test_withdrawn_is_never_called_false(b):
    n = later(base(), changes=1)
    n["state"] = [f for f in n["state"] if f["id"] != "F2"]
    for flag in ((), ("--markdown",)):
        code, out, err = b.diff(base(), n, *flag)
        need("WITHDRAWN" in out, "%s output has no WITHDRAWN label:\n%s" % (flag or "text", out))
        scrubbed = out
        for phrase in ALLOWED:
            scrubbed = scrubbed.replace(phrase, "")
        hit = BANNED.search(scrubbed)
        need(hit is None, "%s output words a withdrawn item as %r:\n%s" % (flag or "text", hit.group(0) if hit else "", out))
        need("not a finding that it is false" in out, "%s output lacks the note that withdrawn is not a finding of falsity" % (flag or "text",))
    code, r = b.diff_json(base(), n)

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                need(not BANNED.search(k), "JSON key %r words a withdrawn item as false" % k)
                walk(x, path + [k])
        elif isinstance(v, list):
            for x in v:
                walk(x, path)
        elif isinstance(v, str) and path and path[0] != "matching":
            s = v
            for phrase in ALLOWED:
                s = s.replace(phrase, "")
            need(not BANNED.search(s), "JSON text at %s words a withdrawn item as false: %r" % ("/".join(path), v))
    walk(r, [])
    need("withdrawn" in r["state"], "JSON has no withdrawn list")


def test_reworded_item_with_a_new_id_is_new_plus_withdrawn(b):
    n = later(base(), changes=2)
    old = find(n["state"], "F3")
    n["state"] = [f for f in n["state"] if f["id"] != "F3"]
    n["state"].append(dict(old, id="F9", statement="The fee is 80 per filing."))
    code, r = b.diff_json(base(), n)
    need(code == 0, "exit %d: %s" % (code, r.get("errors")))
    need(ids(r["state"]["new"]) == ["F9"] and ids(r["state"]["withdrawn"]) == ["F3"] and not r["state"]["changed"],
         "items with different ids were matched by their text: new %s, withdrawn %s, changed %s"
         % (ids(r["state"]["new"]), ids(r["state"]["withdrawn"]), ids(r["state"]["changed"])))
    need(any("not compared by text" in a and "F3" in a and "F9" in a for a in r["advisories"]), "no advisory says the pair was not compared by text")


def test_matching_rule_is_stated(b):
    n = later(base(), changes=1)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    code, out, err = b.diff(base(), n)
    need("matched by id only" in out, "the text output does not say items are matched by id only")


def test_indicator_status_change_is_listed(b):
    n = later(base(), changes=1)
    i = find(n["indicators"], "I2")
    i.update({"status": "seen", "seen_on": NEXT_DAY, "evidence": [{"source_id": "S1", "note": "Fee schedule shows 120."}]})
    code, r = b.diff_json(base(), n)
    mv = r["indicators"]["status_changed"]
    need(code == 0 and ids(mv) == ["I2"] and mv[0]["old"] == "not seen" and mv[0]["new"] == "seen", "indicator change: %s" % mv)
    need(mv[0]["evidence"] == ["S1 (primary): Fee schedule shows 120."], "evidence is not carried with its source tier: %s" % mv[0]["evidence"])
    need(r["change_count"] == 1, "an indicator status change is not counted as a change")


def test_indicator_seen_without_evidence_is_refused(b):
    n = later(base(), changes=1)
    i = find(n["indicators"], "I2")
    i.update({"status": "seen", "seen_on": NEXT_DAY, "evidence": []})
    code, out, err = b.diff(base(), n)
    need(code == 1 and "I2" in out and "no evidence" in out, "seen with no evidence was accepted (exit %d):\n%s" % (code, out))
    i["evidence"] = [{"source_id": "S1", "note": "Fee schedule shows 120."}]
    code, out, err = b.diff(base(), n)
    need(code == 0, "the valid neighbour (one evidence entry) was refused:\n" + out)


def test_unreachable_source_is_listed_with_what_rests_on_it(b):
    n = later(base())
    s = find(n["sources"], "S2")
    s["last_result"] = "unreachable"
    find(n["state"], "F2")["as_of"] = BASE_DAY
    code, r = b.diff_json(base(), n)
    un = r["sources"]["unreachable"]
    need(code == 0 and ids(un) == ["S2"] and un[0]["items"] == ["F2"], "unreachable: %s" % un)
    need(r["state"]["unchanged_carried_forward"] == [{"id": "F2", "as_of": BASE_DAY}], "F2 is not shown as carried forward")
    code, out, err = b.diff(base(), n)
    need(len([x for x in out.splitlines() if x.strip()]) == 1 and "Not checked: S2" in out, "an unchanged run with one source unreachable should be one line naming it:\n" + out)


def test_unreachable_source_appears_in_the_written_report(b):
    # The JSON can be right while the report a person reads leaves the source out. Check the text and the skeleton.
    n = later(base(), changes=1)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    find(n["sources"], "S2")["last_result"] = "unreachable"
    find(n["state"], "F2")["as_of"] = BASE_DAY
    for flag in ((), ("--markdown",)):
        code, out, err = b.diff(base(), n, *flag)
        line = [x for x in out.splitlines() if "S2 unreachable" in x]
        need(code == 0 and len(line) == 1 and "Rests on it: F2" in line[0], "%s output does not list S2 as unreachable with F2 resting on it:\n%s" % (flag or "text", out))
        need("Carried forward without a recheck: F2 (as of %s)" % BASE_DAY in out, "%s output does not list F2 as carried forward:\n%s" % (flag or "text", out))
        nochange = [x for x in out.splitlines() if "rechecked and the same" in x]
        need(len(nochange) == 1 and "F2" not in nochange[0].split("carried forward")[0], "F2 is reported among the rechecked items:\n" + out)


def test_other_changes_put_medium_before_low(b):
    # File order would put the low-priority change first. The report must not.
    d = base()
    d["requirements"].append({"id": "R3", "question": "Is the night berth open?", "priority": "medium"})
    d["indicators"].append({"id": "I3", "requirement": "R3", "watch_for": "The register lists the night berth as open", "where": "official register",
                            "would_mean": "Night arrivals can be booked", "status": "not seen", "seen_on": None, "evidence": []})
    d["state"].append({"id": "F5", "requirement": "R3", "statement": "The night berth is closed.", "status": "FACT", "source_ids": ["S1"], "as_of": BASE_DAY})
    n = later(d, changes=2)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    find(n["state"], "F5")["statement"] = "The night berth is open."
    for flag, head in (((), "OTHER CHANGES"), (("--markdown",), "**Other changes**")):
        code, out, err = b.diff(d, n, *flag)
        need(code == 0 and head in out, "exit %d, or no other-changes section:\n%s" % (code, out))
        part = out[out.find(head):]
        need(0 < part.find("CHANGED F5") < part.find("CHANGED F3") or 0 < part.find("F5 (R3, medium)") < part.find("F3 (R2, low)"),
             "%s output lists the low-priority change (F3) before the medium one (F5):\n%s" % (flag or "text", part[:600]))


def test_item_removed_while_its_source_was_unreachable_is_refused(b):
    n = later(base(), changes=1)
    find(n["sources"], "S2")["last_result"] = "unreachable"
    n["state"] = [f for f in n["state"] if f["id"] != "F2"]
    code, out, err = b.diff(base(), n)
    need(code == 1 and "Not checked is not withdrawn" in out, "an item was reported withdrawn though its source was not reached (exit %d):\n%s" % (code, out))
    n["withdrawn"] = [{"id": "F2", "statement": "A draft of the rule is expected within weeks.", "withdrawn_on": NEXT_DAY, "reason": "The user no longer wants this tracked."}]
    code, r = b.diff_json(base(), n)
    need(code == 0 and ids(r["state"]["dropped"]) == ["F2"] and not r["state"]["withdrawn"], "the valid neighbour (listed under withdrawn with a reason) was not reported as dropped")


def test_recheck_claimed_without_a_reached_source_is_refused(b):
    n = later(base())
    find(n["sources"], "S2")["last_result"] = "unreachable"
    code, out, err = b.diff(base(), n)
    need(code == 1 and "F2" in out and "none of its sources" in out, "F2 was dated as of the run though S2 was unreachable (exit %d):\n%s" % (code, out))
    find(n["state"], "F2")["as_of"] = BASE_DAY
    code, out, err = b.diff(base(), n)
    need(code == 0, "the valid neighbour (as_of left at the old date) was refused:\n" + out)


def test_promotion_to_fact_needs_a_secondary_source(b):
    n = later(base(), changes=1)
    find(n["state"], "F4")["status"] = "FACT"
    code, out, err = b.diff(base(), n)
    need(code == 1 and "F4 rose from REPORTED to FACT" in out, "REPORTED to FACT on an unverified source was accepted (exit %d):\n%s" % (code, out))
    n = later(base(), changes=1)
    find(n["state"], "F2")["status"] = "FACT"
    code, r = b.diff_json(base(), n)
    need(code == 0 and ids(r["state"]["changed"]) == ["F2"] and r["state"]["changed"][0]["fields"] == ["status REPORTED -> FACT"],
         "the valid neighbour (REPORTED to FACT on a secondary source) was not accepted as a change")


def test_stale_boundary(b):
    n = later(base())
    find(n["sources"], "S3")["last_result"] = "not checked"
    find(n["sources"], "S3")["last_checked"] = BASE_DAY
    find(n["state"], "F4")["as_of"] = BASE_DAY
    code, r = b.diff_json(base(), n, "--stale-days", "7")
    need(code == 0 and r["stale"] == [], "an item exactly 7 days old was called stale at --stale-days 7: %s" % r["stale"])
    code, r = b.diff_json(base(), n, "--stale-days", "6")
    need(code == 0 and r["stale"] == [{"id": "F4", "as_of": BASE_DAY, "days": 7}], "an item 7 days old was not called stale at --stale-days 6: %s" % r["stale"])


def test_reporting_order(b):
    n = later(base(), changes=4)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    n["state"].append({"id": "F5", "requirement": "R1", "statement": "The register lists the rule as number 12.", "status": "FACT", "source_ids": ["S1"], "as_of": NEXT_DAY})
    find(n["indicators"], "I1").update({"status": "seen", "seen_on": NEXT_DAY, "evidence": [{"source_id": "S1", "note": "Listed as number 12."}]})
    find(n["sources"], "S3")["last_result"] = "unreachable"
    find(n["state"], "F4")["as_of"] = BASE_DAY
    n["state"] = [f for f in n["state"] if f["id"] != "F2"]
    for flag, heads in (((), ["HIGH PRIORITY", "INDICATORS", "OTHER CHANGES", "NOT CHECKED THIS RUN", "NO CHANGE"]),
                        (("--markdown",), ["**High priority**", "**Indicators**", "**Other changes**", "**Not checked this run**", "**No change:**"])):
        code, out, err = b.diff(base(), n, *flag)
        need(code == 0, "exit %d:\n%s" % (code, out))
        at = [out.find(h) for h in heads]
        need(all(x >= 0 for x in at) and at == sorted(at), "sections are missing or out of order (%s): %s" % (flag or "text", list(zip(heads, at))))
        hi, other = out[at[0]:at[1]], out[at[2]:at[3]]
        need("F5" in hi and "F2" in hi and "F3" not in hi, "high-priority section does not hold exactly the R1 changes")
        need("F3" in other and "F5" not in other, "other-changes section does not hold the low-priority change")


def test_changes_count_mismatch_is_flagged(b):
    n = later(base(), changes=0)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    code, r = b.diff_json(base(), n)
    need(code == 0 and any("changes: 0" in a and "counts 1" in a for a in r["advisories"]), "no advisory about the changes count: %s" % r["advisories"])


def test_as_of_backwards_is_refused(b):
    o = later(base())
    n = later(o, day="2026-09-15")
    find(n["state"], "F3")["as_of"] = BASE_DAY
    code, out, err = b.diff(o, n)
    need(code == 1 and "moved backwards" in out, "as_of moving backwards was accepted (exit %d)" % code)


def test_missing_new_run_is_refused(b):
    code, out, err = b.diff(base(), base())
    need(code == 1 and "no run that OLD lacks" in out, "two files with the same runs were compared without complaint (exit %d):\n%s" % (code, out))


# ---------------- validation refusals, each with its valid neighbour ----------------

def test_mismatched_watch_ids_are_refused(b):
    n = later(base())
    n["watch_id"] = "another-watch"
    code, out, err = b.diff(base(), n)
    need(code == 1 and "different watches" in out, "different watch ids were compared (exit %d):\n%s" % (code, out))
    n["watch_id"] = "test-watch"
    need(b.diff(base(), n)[0] == 0, "the valid neighbour (same watch id) was refused")


def test_duplicate_ids_are_refused(b):
    d = base()
    d["state"][1]["id"] = "F1"
    code, out, err = b.check(d)
    need(code == 1 and "F1 is used twice" in out, "duplicate state ids were accepted (exit %d)" % code)
    d = base()
    d["indicators"][0]["id"] = "R1"
    code, out, err = b.check(d)
    need(code == 1 and "R1 is used twice" in out, "an id shared by a requirement and an indicator was accepted")
    need(b.check(base())[0] == 0, "the valid neighbour (unique ids) was refused")


def test_bad_dates_are_refused(b):
    for bad in ("20261009", "2026-02-30", "2026-9-01", "09/01/2026", "2026-09-01T00:00:00", ""):
        d = base()
        d["state"][0]["as_of"] = bad
        code, out, err = b.check(d)
        need(code == 1 and "as_of" in out, "as_of %r was accepted (exit %d)" % (bad, code))
    d = base()
    d["runs"][0]["date"] = "20260901"
    need(b.check(d)[0] == 1, "run date 20260901 was accepted")
    d = base()
    d["state"][0]["as_of"] = "2026-02-28"
    d["runs"][0]["date"] = "2026-09-01"
    need(b.check(d, "--stale-days", "400")[0] == 0, "the valid neighbour (2026-02-28) was refused")


def test_unknown_values_are_refused(b):
    for path, key, bad, good in ((("state", 0), "status", "TRUE", "FACT"), (("indicators", 0), "status", "maybe", "not seen"),
                                 (("sources", 0), "tier", "blog", "primary"), (("requirements", 0), "priority", "urgent", "high"),
                                 (("sources", 0), "check", "weekly", "each run"), (("sources", 0), "last_result", "ok", "reached")):
        d = base()
        d[path[0]][path[1]][key] = bad
        code, out, err = b.check(d)
        need(code == 1 and repr(bad) in out, "%s %r was accepted (exit %d)" % (key, bad, code))
        d[path[0]][path[1]][key] = good
        need(b.check(d)[0] == 0, "the valid neighbour %s %r was refused" % (key, good))


def test_dangling_references_are_refused(b):
    d = base()
    d["state"][0]["requirement"] = "R9"
    need(b.check(d)[0] == 1, "a state item pointing at a missing requirement was accepted")
    d = base()
    d["state"][0]["source_ids"] = ["S9"]
    code, out, err = b.check(d)
    need(code == 1 and "'S9' is not in sources" in out, "a state item citing a missing source was accepted")
    d = base()
    d["indicators"][0]["requirement"] = "R9"
    need(b.check(d)[0] == 1, "an indicator pointing at a missing requirement was accepted")
    d = base()
    d["indicators"][0].update({"status": "seen", "seen_on": BASE_DAY, "evidence": [{"source_id": "S9", "note": "x"}]})
    need(b.check(d)[0] == 1, "evidence citing a missing source was accepted")


def test_unreadable_input_exits_2(b):
    good = json.dumps(base()).encode("utf-8")
    cases = {"latin-1 bytes": good.replace(b"Baseline.", b"Caf" + bytes([0xE9]) + b"."), "NUL byte": good + bytes([0]),
             "malformed JSON": good[:-1], "empty file": b"", "NaN": good.replace(b'"changes": 0', b'"changes": NaN'),
             "a key given twice": good[:-1] + b', "schema": 1}'}
    for name, raw in cases.items():
        code, out, err = b.run("watch_check.py", b.write(raw))
        need(code == 2 and err.strip() and "Traceback" not in err, "%s: exit %d, stderr %r" % (name, code, err[:120]))
        code, out, err = b.run("sitrep_diff.py", b.write(good), b.write(raw))
        need(code == 2 and "Traceback" not in err, "%s as NEW: exit %d" % (name, code))
    code, out, err = b.run("watch_check.py", b.write(bytes([0xEF, 0xBB, 0xBF]) + good))
    need(code == 0, "the valid neighbour (UTF-8 with a byte-order mark) was refused: exit %d %s" % (code, err))
    code, out, err = b.run("watch_check.py", str(b.tmp / "missing.json"))
    need(code == 2, "a missing file gave exit %d" % code)


def test_no_silent_coercion(b):
    for key, bad in (("schema", "1"), ("schema", True), ("schema", 1.0), ("schema", 2), ("schema", 0)):
        d = base()
        d[key] = bad
        code, out, err = b.check(d)
        need(code == 1 and "schema" in out, "schema %r was accepted (exit %d)" % (bad, code))
    d = base()
    d["schema"] = 2
    need("newer than this script reads" in b.check(d)[1], "schema 2 is not described as newer")
    for bad in ("0", True, -1, 1.5):
        d = base()
        d["runs"][0]["changes"] = bad
        need(b.check(d)[0] == 1, "changes %r was accepted" % (bad,))
    d = base()
    d["indicators"][0]["evidence"] = ["S1: seen it"]
    d["indicators"][0].update({"status": "seen", "seen_on": BASE_DAY})
    need(b.check(d)[0] == 1, "an evidence entry written as plain text was accepted")


def test_strict_arguments(b):
    w = b.write(base())
    for script, args in (("sitrep_diff.py", [w, w, "--frobnicate"]), ("sitrep_diff.py", [w, w, "--stale-days"]), ("sitrep_diff.py", [w, w, "--stale-days", "-1"]),
                         ("sitrep_diff.py", [w, w, "--stale-days", "abc"]), ("sitrep_diff.py", [w, w, "--stale-days", "7.5"]),
                         ("sitrep_diff.py", [w, w, "--json", "--markdown"]), ("sitrep_diff.py", [w]), ("watch_check.py", [w, "--nope"]),
                         ("watch_check.py", [w, w]), ("watch_check.py", [w, "--stale-days"])):
        code, out, err = b.run(script, *args)
        need(code == 2 and "Traceback" not in err and len(err.strip().splitlines()) == 1, "%s %s: exit %d, stderr %r" % (script, args[1:], code, err[:160]))
    need(b.run("sitrep_diff.py", w, b.write(later(base())), "--stale-days", "0")[0] == 0, "the valid neighbour (--stale-days 0) was refused")


def test_inputs_are_not_modified(b):
    n = later(base(), changes=1)
    find(n["state"], "F3")["statement"] = "The fee is 95."
    po, pn = b.write(base()), b.write(n)
    before = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (po, pn)]
    for flag in ((), ("--json",), ("--markdown",)):
        b.run("sitrep_diff.py", po, pn, *flag)
    b.run("watch_check.py", pn)
    need(before == [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (po, pn)], "an input file was changed by a run")
    need(not (b.folder / "__pycache__").exists() or b.folder != HERE, "a cache folder was written beside the scripts")


def test_output_is_ascii(b):
    n = later(base(), changes=1)
    find(n["state"], "F3")["statement"] = "The fee is 95" + chr(0x20AC) + " " + chr(0x2014) + " up from 80."
    for flag in ((), ("--json",), ("--markdown",)):
        code, out, err = b.diff(base(), n, *flag)
        need(code == 0 and all(ord(c) < 128 for c in out), "non-ASCII output with %s" % (flag or "text",))


def test_json_output_has_every_category(b):
    code, r = b.diff_json(base(), later(base()))
    for key in ("new", "changed", "withdrawn", "dropped", "unchanged_rechecked", "unchanged_carried_forward"):
        need(key in r["state"], "JSON state lacks %r" % key)
    need(set(r["sources"]) >= {"unreachable", "not_checked", "reached", "total"} and "status_changed" in r["indicators"] and "stale" in r, "JSON lacks a category")


def test_missing_sibling_exits_3(b):
    alone = b.tmp / "alone"
    alone.mkdir(exist_ok=True)
    shutil.copy(b.folder / "sitrep_diff.py", alone / "sitrep_diff.py")
    w = b.write(base())
    r = subprocess.run([sys.executable, "-B", str(alone / "sitrep_diff.py"), w, w], capture_output=True, timeout=60)
    need(r.returncode == 3 and b"NOT RUN" in r.stdout, "without watch_check.py beside it: exit %d %r" % (r.returncode, r.stdout[:80]))


# ---------------- watch_check advisories ----------------

def advisories(b, d):
    code, out, err = b.check(d, "--json")
    return code, json.loads(out)["advisories"]


def test_vague_indicators_are_flagged(b):
    for vague in ("Further deterioration in relations", "Increased activity around the port", "Signs of growing pressure"):
        d = base()
        d["indicators"][0]["watch_for"] = vague
        code, adv = advisories(b, d)
        need(code == 0 and any("I1" in a and "observable" in a for a in adv), "%r was not flagged: %s" % (vague, adv))
    for sound in ("Activity above 3 incidents in a week at the port", "The regulator publishes the final rule", "The register lists the rule with a number"):
        d = base()
        d["indicators"][0]["watch_for"] = sound
        code, adv = advisories(b, d)
        need(not any("I1" in a and "observable" in a for a in adv), "the valid neighbour %r was flagged" % sound)


def test_requirement_without_indicator_is_flagged(b):
    d = base()
    d["indicators"] = [d["indicators"][0]]
    code, adv = advisories(b, d)
    need(code == 0 and any("requirement R2 has no indicator" in a for a in adv), "no advisory: %s" % adv)
    need(not any("has no indicator" in a for a in advisories(b, base())[1]), "the valid neighbour was flagged")


def test_high_priority_on_weak_sources_is_flagged(b):
    d = base()
    d["state"][0].update({"status": "REPORTED", "source_ids": ["S3"]})
    d["state"][1]["source_ids"] = ["S3"]
    code, adv = advisories(b, d)
    need(code == 0 and any("high-priority requirement R1 rests only on sources below secondary tier" in a for a in adv), "no advisory: %s" % adv)
    d["state"][1]["source_ids"] = ["S3", "S2"]
    need(not any("rests only on" in a for a in advisories(b, d)[1]), "the valid neighbour (one secondary source) was flagged")


def test_fact_needs_a_secondary_source(b):
    d = base()
    d["state"][0]["source_ids"] = ["S3"]
    code, out, err = b.check(d)
    need(code == 1 and "F1 is a FACT with no source of secondary tier or better" in out, "a FACT on an unverified source was accepted (exit %d)" % code)
    d["state"][0]["source_ids"] = ["S2"]
    need(b.check(d)[0] == 0, "the valid neighbour (a secondary source) was refused")


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

# Planted faults. "old" must appear in the file exactly once; it is replaced by "new" in a temporary copy.
MUTANTS = [
    {"name": "withdrawn items are labelled false", "file": "sitrep_diff.py",
     "old": 'WITHDRAWN_LABEL = "WITHDRAWN"\nWITHDRAWN_NOTE = "No source reached this run still says this. That is not a finding that it is false."',
     "new": 'WITHDRAWN_LABEL = "FALSE"\nWITHDRAWN_NOTE = "No source says this any more, so it is now false."',
     "caught_by": "test_withdrawn_is_never_called_false"},
    {"name": "items with different ids are silently matched by similar text", "file": "sitrep_diff.py",
     "old": '    both, only_old, only_new = pair_by_id(old["state"], new["state"])\n',
     "new": '    import difflib\n'
            '    _olds = {x["id"]: x for x in old["state"]}\n'
            '    _taken = {x["id"] for x in new["state"]}\n'
            '    _renamed = []\n'
            '    for _x in new["state"]:\n'
            '        if _x["id"] not in _olds:\n'
            '            for _i, _o in _olds.items():\n'
            '                if _i not in _taken and difflib.SequenceMatcher(None, norm(_o["statement"]), norm(_x["statement"])).ratio() > 0.6:\n'
            '                    _x = dict(_x, id=_i)\n'
            '                    _taken.add(_i)\n'
            '                    break\n'
            '        _renamed.append(_x)\n'
            '    new = dict(new, state=_renamed)\n'
            '    both, only_old, only_new = pair_by_id(old["state"], new["state"])\n',
     "caught_by": "test_reworded_item_with_a_new_id_is_new_plus_withdrawn"},
    {"name": "an unchanged run is padded into a full report", "file": "sitrep_diff.py",
     "old": '    if res["no_change"] and not errors and not adv:\n', "new": '    if False:\n',
     "caught_by": "test_unchanged_run_is_one_line"},
    {"name": "an item removed while its source was unreachable is reported as withdrawn", "file": "sitrep_diff.py",
     "old": '        if had and not any(s in reached for s in had):\n            if i in reasons:', "new": '        if False:\n            if i in reasons:',
     "caught_by": "test_item_removed_while_its_source_was_unreachable_is_refused"},
    {"name": "the freshness window is off by one day", "file": "sitrep_diff.py",
     "old": '        if age > stale_days:\n', "new": '        if age >= stale_days:\n', "caught_by": "test_stale_boundary"},
    {"name": "a FACT no longer needs a secondary source", "file": "watch_check.py",
     "old": '            if st == "FACT" and not any(t in GOOD_TIERS for t in tiers):', "new": '            if False:',
     "caught_by": "test_promotion_to_fact_needs_a_secondary_source"},
    {"name": "dates without hyphens are accepted", "file": "watch_check.py",
     "old": 'ISO_DATE = re.compile(r"\\d{4}-\\d{2}-\\d{2}")', "new": 'ISO_DATE = re.compile(r"\\d{4}-?\\d{2}-?\\d{2}")',
     "caught_by": "test_bad_dates_are_refused"},
    {"name": "the order of priorities is reversed, so low-priority changes come before medium ones", "file": "sitrep_diff.py",
     "old": 'RANK = {"high": 0, "medium": 1, "low": 2}', "new": 'RANK = {"high": 2, "medium": 1, "low": 0}',
     "caught_by": "test_other_changes_put_medium_before_low"},
    {"name": "an unreachable source is left out of the written report", "file": "sitrep_diff.py",
     "old": '    for x in so["unreachable"]:\n        L.append(', "new": '    for x in []:\n        L.append(',
     "caught_by": "test_unreachable_source_appears_in_the_written_report"},
    {"name": "the skeleton no longer opens with the method name", "file": "sitrep_diff.py",
     "old": 'METHOD_LINE = "**Sitrep, changes since last run.**"', "new": 'METHOD_LINE = "**Update.**"',
     "caught_by": "test_markdown_first_line_names_the_method"},
]


def run_suite(folder, only=None, quiet=False):
    tmp = tempfile.mkdtemp(prefix="sitrep-test-")
    failed = []
    try:
        box = Box(folder, tmp)
        for t in TESTS:
            if only and t.__name__ != only:
                continue
            try:
                t(box)
                if not quiet:
                    print("PASS  " + t.__name__)
            except AssertionError as e:
                failed.append(t.__name__)
                if not quiet:
                    print("FAIL  %s\n      %s" % (t.__name__, str(e).replace("\n", "\n      ")[:900]))
            except Exception as e:  # noqa: BLE001  a crash in the script under test is a failed test
                failed.append(t.__name__)
                if not quiet:
                    print("FAIL  %s\n      %s: %s" % (t.__name__, type(e).__name__, str(e)[:300]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return failed


def run_mutants():
    survived = 0
    for m in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="sitrep-mutant-")
        try:
            for s in SCRIPTS:
                shutil.copy(HERE / s, Path(tmp) / s)
            p = Path(tmp) / m["file"]
            src = p.read_text(encoding="utf-8")
            if src.count(m["old"]) != 1:
                print("BROKEN    %s: the text to replace appears %d times in %s, not once" % (m["name"], src.count(m["old"]), m["file"]))
                survived += 1
                continue
            p.write_text(src.replace(m["old"], m["new"]), encoding="utf-8")
            failed = run_suite(tmp, quiet=True)
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
    only, folder, mutants, it = None, HERE, False, iter(argv)
    for a in it:
        if a == "--mutants":
            mutants = True
        elif a in ("--only", "--dir"):
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_sitrep_diff: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--only":
                only = v
            else:
                folder = Path(v)
        else:
            print("test_sitrep_diff: unknown argument " + a, file=sys.stderr)
            return 2
    if only and only not in [t.__name__ for t in TESTS]:
        print("test_sitrep_diff: no test named " + only, file=sys.stderr)
        return 2
    if not all((Path(folder) / s).is_file() for s in SCRIPTS):
        print("test_sitrep_diff: %s does not hold %s" % (folder, " and ".join(SCRIPTS)), file=sys.stderr)
        return 2
    if mutants:
        return run_mutants()
    failed = run_suite(folder, only)
    ran = 1 if only else len(TESTS)
    print("\n%d test(s) run, %d passed, %d failed" % (ran, ran - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.exit(main(sys.argv[1:]))
