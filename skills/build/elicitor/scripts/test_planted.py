#!/usr/bin/env python3
"""Show that the browser tests can fail: plant one fault at a time and require the named test to catch it.

Usage:
  python test_planted.py [--only WORD] [--list] [--keep DIR] [--json]

For each planted fault it writes a copy of ../assets/engine.html with one small change (for example
the note left out of the export, or a skipped quiz item scored as correct), runs
test_engine.py --engine COPY --only TEST, and requires that run to FAIL. A test that still passes
on a faulty engine has not been shown to check anything, and is reported as MISSED.
One fault is not in the engine but in a revision: a second version of the fixture whose ids were
renumbered by position. It is handed to the test revision_keeps_ids with --revision.

--only WORD  plant only the faults whose name contains WORD.
--keep DIR   keep the faulty copies in DIR (they are written to a temporary folder otherwise).

What it enforces (exit 1): a fault that the named test did not catch (MISSED), and a fault whose
text to replace is no longer in the engine exactly once (STALE: the engine changed, so the plant
must be rewritten to match).
What it cannot tell: that the tests catch faults other than these. It shows each named test
failing once for a stated reason, no more.

Exit codes: 0 every planted fault was caught. 1 one was missed or stale. 2 bad arguments.
3 could not run because Playwright is missing (prints NOT RUN).
"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "assets" / "engine.html"

# name, test that must catch it, text to find (exactly once), replacement
PLANTS = [
    ("note_left_out_of_export", "intake_journey",
     "if (note) L = L.concat(['Note:'], quote(note));", "if (note && false) L = L.concat(['Note:'], quote(note));"),
    ("first_answer_kept_after_change", "intake_journey",
     "if (v === undefined) delete e.v; else e.v = v;", "if (v === undefined) delete e.v; else if (e.v === undefined) e.v = v;"),
    ("skip_not_marked_in_export", "intake_journey",
     "if (st === 'skipped') return ['Answer: (skipped)'];", "if (st === 'skipped') return ['Answer: (no answer)'];"),
    ("quiz_scores_skipped_as_correct", "quiz_scoring",
     "else { if (st === 'skipped') s.skipped++; else s.none++; s.passed.push(q); }", "else { if (st === 'skipped') { s.skipped++; s.correct++; } else s.none++; s.passed.push(q); }"),
    ("quiz_explains_only_the_chosen_option", "quiz_scoring",
     "bits.push(el('span', {class: 'why', text: o.explain}));", "if (chosen(o.text)) bits.push(el('span', {class: 'why', text: o.explain}));"),
    ("export_box_cut_short", "clipboard_refused",
     "    box.value = text;\n", "    box.value = text.slice(0, 400);\n"),
    ("copy_reported_when_refused", "clipboard_refused",
     "ok = document.execCommand('copy') === true; } catch (e) { ok = false; }\n      done(ok);", "ok = document.execCommand('copy') === true; } catch (e) { ok = false; }\n      done(true);"),
    ("saved_state_not_loaded", "reload_resume",
     "if (res && res.ok && res.version === I.version && !res.dropped.length) {", "if (false) {"),
    ("storage_error_not_caught", "storage_throwing",
     "finish('local');\n          } catch (e) { finish('memory'); }", "finish('local');\n          } catch (e) { throw e; }"),
    ("silent_host_storage_hangs_the_page", "storage_throwing",
     "setTimeout(function () { if (!settled) tryLocal(); }, 1500);", "setTimeout(function () { if (!settled) tryLocal(); }, 1500000);"),
    ("not_saved_note_missing", "storage_throwing",
     "$('save-banner').hidden = !bad;", "$('save-banner').hidden = true;"),
    ("failed_import_clears_answers", "import_refusals",
     "if (!res.ok) { importMsg(res.why", "if (!res.ok) { ST = freshState(); importMsg(res.why"),
    ("newer_schema_accepted", "import_refusals",
     "if (env.schema > SCHEMA) return", "if (env.schema > SCHEMA + 5) return"),
    ("other_questionnaire_accepted", "import_refusals",
     "if (m[1] !== I.id) return {ok: false, why: 'This code is for a different questionnaire", "if (false) return {ok: false, why: 'This code is for a different questionnaire"),
    ("hidden_question_exported", "show_if",
     "var vis = visible(), c = counts(vis), L = [], sec = null;", "var vis = Q, c = counts(vis), L = [], sec = null;"),
    ("slow_to_draw_a_question", "long_instrument",
     "    opts = opts || {};\n    var main = $('main'), keep = null;", "    opts = opts || {};\n    var spin = Date.now(); while (Date.now() - spin < 60) { spin = spin + 0; }\n    var main = $('main'), keep = null;"),
    ("likert_line_format_changed", "export_round_trip",
     "if (q.type === 'likert') return ['Answer: ' + v + ' of ' + q.points + ', ' + q.labels[v - 1]];", "if (q.type === 'likert') return ['Answer: ' + v + ' / ' + q.points + ', ' + q.labels[v - 1]];"),
    ("blank_line_lost_from_text", "export_round_trip",
     "function quote(text) { return text.split('\\n').map(function (l) { return l ? '> ' + l : '>'; }); }", "function quote(text) { return text.split('\\n').filter(function (l) { return l; }).map(function (l) { return '> ' + l; }); }"),
    ("disclosure_screen_skipped", "survey_mode",
     "return {stage: I.mode === 'survey' ? 'disclosure' : 'intro', cur: null,", "return {stage: 'intro', cur: null,"),
    ("tally_caveat_left_out", "tallies",
     "      L.push(TALLY_LINE);\n", ""),
    ("tally_counts_everything_answered", "tallies",
     "var n = answered.filter(function (q) { return ('answered' in t.when) ? true : matches(entry(q).v, t.when); }).length;", "var n = answered.length;"),
    ("section_layout_ignores_required", "section_layout",
     "    if (dir > 0 || UI.fromReview) {\n      var bad = sectionQuestions(here)", "    if (false) {\n      var bad = sectionQuestions(here)"),
    ("display_reset_does_nothing", "display_settings",
     "      display = displayDefaults(); writeDisplay(); applyDisplay();\n      if (was !== display.layout", "      writeDisplay(); applyDisplay();\n      if (was !== display.layout"),
    ("option_text_does_not_wrap", "no_overflow",
     ".opt .t{flex:1 1 auto;min-width:0;overflow-wrap:anywhere}", ".opt .t{flex:1 0 auto;white-space:nowrap}"),
    ("targets_made_small", "no_overflow",
     "--gap:1rem;--opt-pad:.7rem;--q-size:1.42rem;--target:2.75rem;", "--gap:1rem;--opt-pad:.2rem;--q-size:1.42rem;--target:2rem;"),
    ("undo_does_nothing", "undo_and_reset",
     "function restore(snap, words) { ST = JSON.parse(snap);", "function restore(snap, words) {"),
    ("reset_without_confirmation", "undo_and_reset",
     "    $('reset-ask').addEventListener('click', askReset);", "    $('reset-ask').addEventListener('click', function () { $('reset-go').click(); });"),
    ("blank_page_on_broken_data", "data_block_faults",
     "try { raw = (typeof INSTRUMENT === 'undefined') ? null : INSTRUMENT; } catch (e) { raw = null; }", "raw = INSTRUMENT;"),
    ("focus_lost_after_a_move", "keyboard_and_focus",
     "draw((d < 0 ? 'up-' : 'down-') + q.id + '-' + j);", "draw(null); if (document.activeElement) document.activeElement.blur();"),
    ("form_element_added", "page_rules",
     '<main id="main" tabindex="-1"></main>', '<form><main id="main" tabindex="-1"></main></form>'),
    ("markup_built_from_text", "page_rules",
     "if (k === 'text') n.textContent = v;", "if (k === 'text') n.innerHTML = v;"),
    ("select_all_with_one_too_many_marked_correct", "quiz_scoring",
     "return Array.isArray(v) && v.length === c.length && c.every(", "return Array.isArray(v) && c.every("),
    ("quiz_skipped_counted_as_attempted", "quiz_scoring",
     "else { if (st === 'skipped') s.skipped++; else s.none++; s.passed.push(q); }", "else { if (st === 'skipped') { s.skipped++; s.attempted++; } else s.none++; s.passed.push(q); }"),
    ("hidden_question_counted_in_tally", "tallies",
     "var items = vis.filter(function (q) { return q.tags.indexOf(t.tag) >= 0; });", "var items = Q.filter(function (q) { return q.tags.indexOf(t.tag) >= 0; });"),
    ("progress_counts_hidden_questions", "show_if",
     "t.appendChild(document.createTextNode(' of ' + vis.length + (c.skipped ? ', ' + c.skipped + ' skipped' : '')));\n    } else {",
     "t.appendChild(document.createTextNode(' of ' + Q.length + (c.skipped ? ', ' + c.skipped + ' skipped' : '')));\n    } else {"),
    ("export_markers_in_an_answer_stop_loading", "awkward_text",
     "if (/^Instrument: [a-z0-9_-]+, version \\d+, /m.test(t) && /^End of export: /m.test(t)) return readMarkdown(t);",
     "if (t.indexOf('=== elicitor response') >= 0) return readResponse(t);"),
    ("quoted_line_read_as_a_heading", "awkward_text",
     "if ((m = /^### \\[([a-z0-9_-]+)\\] /.exec(l))) {", "if ((m = /^(?:> )?### \\[([a-z0-9_-]+)\\] /.exec(l))) {"),
    ("answers_from_another_version_loaded_unasked", "revision_keeps_ids",
     "if (res && res.ok && res.version === I.version && !res.dropped.length) {", "if (res && res.ok && !res.dropped.length) {"),
    ("back_loses_the_answer_left_behind", "intake_journey",
     "} else if (i > 0) goTo(vis[i - 1].id);", "} else if (i > 0) { delete ST.ans[q.id]; goTo(vis[i - 1].id); }"),
    ("ill_fitting_code_loaded_anyway", "import_refusals",
     "if (res.dropped.length && res.kind === 'resume code') {", "if (false) {"),
]
REVISION_PLANT = ("revision_renumbers_ids", "revision_keeps_ids")


def renumbered(v1):
    """A second version in which a question was put first and every id moved down one place."""
    v2 = copy.deepcopy(v1)
    ids = [q["id"] for q in v2["questions"]]
    v2["questions"].insert(0, {"id": "", "section": v2["sections"][0]["id"], "type": "single", "text": "Who is the shelf for?", "options": ["Me", "Someone else"]})
    for q, new_id in zip(v2["questions"], ids + ["added-at-the-end"]):
        q["id"] = new_id
    for q in v2["questions"]:
        q.pop("show_if", None)
    v2["tallies"] = []
    v2["version"] = 2
    return v2


def main(argv):
    only, keep, as_json, it = None, None, False, iter(argv)
    for a in it:
        if a == "--json":
            as_json = True
        elif a == "--list":
            print("\n".join("%-36s caught by %s" % (p[0], p[1]) for p in PLANTS + [REVISION_PLANT]))
            return 0
        elif a in ("--only", "--keep"):
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("test_planted: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--only":
                only = v
            else:
                keep = v
        else:
            print("test_planted: unknown option " + a, file=sys.stderr)
            return 2
    sys.path.insert(0, str(HERE))
    from build_instrument import build
    engine = ENGINE.read_text(encoding="utf-8")
    tmp = Path(keep) if keep else Path(tempfile.mkdtemp(prefix="elicitor-planted-"))
    tmp.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        jobs = [p for p in PLANTS if not only or only in p[0]]
        for name, test, find, repl in jobs:
            if engine.count(find) != 1:
                rows.append({"plant": name, "test": test, "outcome": "STALE", "detail": "the text to replace occurs %d time(s) in the engine, not once" % engine.count(find)})
                continue
            path = tmp / (name + ".html")
            path.write_text(engine.replace(find, repl), encoding="utf-8")
            rows.append(run_one(name, test, ["--engine", str(path)]))
        if not only or only in REVISION_PLANT[0]:
            v1 = json.loads((HERE / "fixtures" / "all_types.json").read_text(encoding="utf-8"))
            old, new = tmp / "revision-old.html", tmp / "revision-renumbered.html"
            old.write_text(build(engine, v1), encoding="utf-8")
            new.write_text(build(engine, renumbered(v1)), encoding="utf-8")
            rows.append(run_one(REVISION_PLANT[0], REVISION_PLANT[1], ["--revision", str(old), str(new)]))
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
    if any(r["outcome"] == "NOT RUN" for r in rows):
        print("NOT RUN: test_engine.py could not start a browser, so no planted fault was tried.")
        return 3
    bad = [r for r in rows if r["outcome"] != "CAUGHT"]
    if as_json:
        text = json.dumps({"plants": len(rows), "caught": len(rows) - len(bad), "results": rows}, indent=1, ensure_ascii=True)
    else:
        L = ["%-7s %-36s by %-20s %s" % (r["outcome"], r["plant"], r["test"], r["detail"][:150]) for r in rows]
        L.append("RESULT: %s. %d of %d planted fault(s) were caught by the test named for them." % ("FAIL" if bad else "PASS", len(rows) - len(bad), len(rows)))
        text = "\n".join(L)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    return 1 if bad else 0


def run_one(name, test, extra):
    r = subprocess.run([sys.executable, "-B", str(HERE / "test_engine.py"), "--only", test, "--json"] + extra, capture_output=True, text=True)
    if r.returncode == 3:
        return {"plant": name, "test": test, "outcome": "NOT RUN", "detail": r.stdout.strip()[:150]}
    try:
        res = json.loads(r.stdout)
        fails = [f for x in res["results"] for f in x["failures"]]
    except (ValueError, KeyError):
        return {"plant": name, "test": test, "outcome": "MISSED", "detail": "test_engine gave no result: " + (r.stderr or r.stdout).strip()[:120]}
    if r.returncode == 1 and fails:
        return {"plant": name, "test": test, "outcome": "CAUGHT", "detail": "%d assertion(s) failed, first: %s" % (len(fails), fails[0])}
    return {"plant": name, "test": test, "outcome": "MISSED", "detail": "the test passed on the faulty engine (exit %d)" % r.returncode}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
