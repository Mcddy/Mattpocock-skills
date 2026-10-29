#!/usr/bin/env python3
"""Test the four command-line tools against planted bad inputs and their valid neighbours.

Usage:
  python test_tools.py [--only WORD] [--json]

Standard library only; no browser is needed. It runs validate_instrument.py, build_instrument.py,
parse_export.py and collect_responses.py as separate processes on inputs it writes into a temporary
folder (removed afterwards), and checks each run's exit code and that a stated phrase is in its
output. The inputs are made from the fixtures beside this script, each changed in one way.

What it enforces (FAIL, exit 1): every case below. A case is either a planted fault that the tool
must refuse with the right reason, or the nearest valid input that the tool must accept. For
example: one option is refused and two are accepted; nine options are refused and eight accepted;
sixty questions raise no fatigue note and sixty-one do.
--only WORD runs the cases whose name contains WORD.

What it cannot tell: anything about the page in a browser (see test_engine.py), or whether the
advisory wording checks catch every badly written question. They are prompts, not proofs.

Exit codes: 0 every case passed. 1 a case failed. 2 bad arguments.
"""
import copy
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
ENGINE = HERE.parent / "assets" / "engine.html"
E_ACUTE = chr(0xE9)
CURLY_OPEN, CURLY_CLOSE = chr(0x201C), chr(0x201D)


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class Runner:
    def __init__(self, tmp, only):
        self.tmp, self.only, self.n, self.results = Path(tmp), only, 0, []

    def path(self, name, content):
        self.n += 1
        p = self.tmp / ("%03d-%s" % (self.n, name))
        if isinstance(content, bytes):
            p.write_bytes(content)
        elif isinstance(content, str):
            p.write_bytes(content.encode("utf-8"))
        else:
            p.write_bytes(json.dumps(content, indent=1).encode("utf-8"))
        return str(p)

    def case(self, name, tool, args, code, *phrases, absent=(), check=None):
        """Run one tool. Expect the exit code, each phrase in its output, and none of the absent ones."""
        if self.only and self.only not in name:
            return
        r = subprocess.run([sys.executable, "-B", str(HERE / tool)] + [str(a) for a in args], capture_output=True, text=True)
        out = r.stdout + r.stderr
        why = []
        if r.returncode != code:
            why.append("exit code %d, expected %d" % (r.returncode, code))
        why += ["missing phrase %r" % p for p in phrases if p not in out]
        why += ["unexpected phrase %r" % p for p in absent if p in out]
        if "Traceback" in out:
            why.append("a traceback was printed")
        if not why and check is not None:
            extra = check(r)
            if extra:
                why.append(extra)
        self.results.append({"case": name, "tool": tool, "passed": not why, "why": why, "output": out.strip().split("\n")[-3:]})


def q_of(inst, qid):
    return next(q for q in inst["questions"] if q["id"] == qid)


def changed(base, fn):
    inst = copy.deepcopy(base)
    fn(inst)
    return inst


def validate_cases(R):
    base, quiz, survey = load("all_types.json"), load("quiz.json"), load("survey.json")
    V = "validate_instrument.py"

    def bad(name, fn, phrase, src=base, code=1):
        R.case("validate: " + name, V, [R.path("v.json", changed(src, fn))], code, phrase)

    def good(name, fn, src=base, absent=("ERROR",)):
        R.case("validate: " + name, V, [R.path("v.json", changed(src, fn))], 0, "RESULT: PASS", absent=absent)

    good("the fixture as it is", lambda i: None)
    good("the quiz fixture", lambda i: None, quiz)
    good("the survey fixture", lambda i: None, survey)
    bad("an id used twice", lambda i: q_of(i, "rooms").update(id="purpose"), "the id is used twice")
    bad("a question with no id", lambda i: q_of(i, "rooms").pop("id"), "has no id")
    bad("an id with capitals", lambda i: q_of(i, "sturdy").update(id="Sturdy"), "must match [a-z0-9_-]+")
    for pos in ("7", "q7", "item-7", "question_12"):
        bad("a bare position as an id (%s)" % pos, lambda i, pos=pos: q_of(i, "sturdy").update(id=pos), "bare position")
    for ok in ("q7-sturdy", "sturdy-7", "ipv4"):
        good("a named id next to a position (%s)" % ok, lambda i, ok=ok: q_of(i, "sturdy").update(id=ok))
    bad("an unknown type", lambda i: q_of(i, "purpose").update(type="dropdown"), "unknown type 'dropdown'")
    bad("one option", lambda i: q_of(i, "purpose").update(options=["Only"]), "needs at least 2 options (has 1)")
    good("two options", lambda i: q_of(i, "purpose").update(options=["One", "Two"]))
    good("eight options", lambda i: q_of(i, "purpose").update(options=["Opt %d" % k for k in range(8)]))
    bad("nine options", lambda i: q_of(i, "purpose").update(options=["Opt %d" % k for k in range(9)]), "has 9 options")
    bad("the same option twice, in different case", lambda i: q_of(i, "purpose").update(options=["Books", "Tools", "BOOKS"]), "appears more than once")
    bad("an option equal to an export marker", lambda i: q_of(i, "purpose").update(options=["Books", "(skipped)"]), "export marker")
    bad("an option with a line break", lambda i: q_of(i, "purpose").update(options=["Books", "Tools\nand more"]), "line break")
    bad("a likert question with three labels", lambda i: q_of(i, "sturdy").update(labels=["No", "Maybe", "Yes"]), "4 or 5 entries")
    bad("a likert question with six labels", lambda i: q_of(i, "sturdy").update(labels=list("abcdef")), "4 or 5 entries")
    good("a likert question with four labels", lambda i: q_of(i, "sturdy").update(labels=["No", "Mostly no", "Mostly yes", "Yes"]))
    bad("a scale with max equal to min", lambda i: q_of(i, "urgency").update(min=5, max=5), "max above min")
    bad("a scale whose step does not divide its range", lambda i: q_of(i, "urgency").update(step=3), "step dividing the range")
    good("a scale whose step divides its range", lambda i: q_of(i, "urgency").update(step=2))
    bad("a number with text for a limit", lambda i: q_of(i, "width").update(max="400"), "max must be a number")
    bad("required written as text", lambda i: q_of(i, "width").update(required="true"), "required must be true or false")
    bad("version written as text", lambda i: i.update(version="1"), "version must be a whole number")
    bad("version given as true", lambda i: i.update(version=True), "version must be a whole number")
    bad("version given as 1.5", lambda i: i.update(version=1.5), "version must be a whole number")
    bad("an unknown mode", lambda i: i.update(mode="exam"), "mode must be one of")
    bad("no questions", lambda i: i.update(questions=[], tallies=[]), "questions must be a non-empty list")
    bad("a section that is not listed", lambda i: q_of(i, "purpose").update(section="nowhere"), "is not one of the sections listed")
    bad("show_if pointing at a later question", lambda i: q_of(i, "rooms").update(show_if={"q": "width", "answered": True}), "this question or a later one")
    bad("show_if pointing at itself", lambda i: q_of(i, "rooms").update(show_if={"q": "rooms", "answered": True}), "this question or a later one")
    bad("show_if pointing at an unknown question", lambda i: q_of(i, "rooms").update(show_if={"q": "nothing", "answered": True}), "not a question in this instrument")
    good("show_if pointing at the question just before", lambda i: q_of(i, "rooms").update(show_if={"q": "purpose", "answered": True}))
    bad("show_if testing for a value that is not an option", lambda i: q_of(i, "wall-type").update(show_if={"q": "wall", "equals": "Maybe"}), "is not one of the options")
    bad("show_if using includes on a single-answer question", lambda i: q_of(i, "wall-type").update(show_if={"q": "wall", "includes": "Yes"}), "includes only works on a multi question")
    bad("show_if with two tests", lambda i: q_of(i, "wall-type").update(show_if={"q": "wall", "equals": "Yes", "answered": True}), "exactly one test")
    bad("show_if with a test the engine does not have", lambda i: q_of(i, "why-rush").update(show_if={"q": "urgency", "at_least": 9}), "exactly one test")
    bad("a tally with a tag no question carries", lambda i: i["tallies"][0].update(tag="nothing"), "is not carried by any question")
    bad("a tally with a malformed test", lambda i: i["tallies"][0].update(when={"at_least": "4"}), "needs a number")
    bad("survey mode with no statement of what happens to answers", lambda i: i["disclosure"].pop("handling"), "disclosure.handling", survey)
    bad("survey mode with an empty statement of who is asking", lambda i: i["disclosure"].update(who="  "), "disclosure.who", survey)
    bad("survey mode with no disclosure at all", lambda i: i.pop("disclosure"), "disclosure.purpose", survey)
    bad("a quiz item with no correct answer", lambda i: [o.pop("correct", None) for o in i["questions"][0]["options"]], "no option is marked correct", quiz)
    bad("a quiz option with no explanation", lambda i: i["questions"][0]["options"][2].pop("explain"), "has no explanation", quiz)
    bad("a quiz option with an empty explanation", lambda i: i["questions"][0]["options"][2].update(explain=" "), "has no explanation", quiz)
    bad("a single-answer quiz item with two correct answers", lambda i: i["questions"][0]["options"][1].update(correct=True), "exactly one", quiz)
    bad("a quiz option written as plain text", lambda i: i["questions"][0]["options"].__setitem__(1, "1,240"), "must be an object", quiz)
    bad("a quiz item of a type that cannot be marked", lambda i: i["questions"][0].update(type="text"), "quiz items must be single or multi", quiz)
    bad("a ranking item in a quiz", lambda i: i["questions"][0].update(type="rank"), "quiz items must be single or multi", quiz)
    bad("tallies in a quiz", lambda i: i.update(tallies=[{"id": "t", "label": "Count", "tag": "x"}]), "tallies are not used in quiz mode", quiz)
    bad("correct written as text in a quiz", lambda i: i["questions"][0]["options"][0].update(correct="yes"), "correct must be true or false", quiz)

    # advisories: reported, never failures
    def advice(name, fn, phrase, src=base):
        R.case("validate advisory: " + name, V, [R.path("v.json", changed(src, fn))], 0, "ADVISORY", phrase, "RESULT: PASS")

    advice("two things in one question", lambda i: q_of(i, "wall").update(text="Is the wall solid and can it be drilled?"), "joins two things")
    advice("a leading opener", lambda i: q_of(i, "wall").update(text="Don't you think it should be fixed to the wall?"), "leads towards an answer")
    advice("an absolute in a statement to rate", lambda i: q_of(i, "sturdy").update(text="I always check that furniture is solid."), "contains an absolute (always)")
    advice("number ranges that overlap", lambda i: q_of(i, "purpose").update(options=["1-5", "5-10", "More than 10"]), "overlap at 5")
    advice("number ranges with a gap", lambda i: q_of(i, "purpose").update(options=["1-5", "7-10", "More than 10"]), "gap between")
    good("number ranges that meet exactly", lambda i: q_of(i, "purpose").update(options=["1 to 5", "6 to 10", "More than 10"]), absent=("ERROR", "overlap", "gap between"))
    advice("a tally named like a diagnosis", lambda i: i["tallies"][0].update(label="Anxiety disorder score"), "reads like a diagnosis")
    advice("an unknown field", lambda i: i.update(tally=[]), "unknown field 'tally'")
    advice("a correct answer marked outside quiz mode", lambda i: q_of(i, "purpose").update(options=[{"text": "Books", "correct": True}, "Tools"]), "ignored outside quiz mode")

    def cluster(i):
        for q in i["questions"]:
            if q["type"] == "single":
                q["options"].sort(key=lambda o: not o.get("correct"))
        i["questions"] += [{"id": "extra-%d" % k, "type": "single", "text": "Extra item %d?" % k, "options": [
            {"text": "Right %d" % k, "correct": True, "explain": "It is."}, {"text": "Wrong %d" % k, "explain": "It is not."}]} for k in range(3)]

    advice("quiz answers bunched in the first position", cluster, "the correct answer is in position 1 in 7 of 7", quiz)
    advice("one quiz option much longer than the others", lambda i: i["questions"][0]["options"][0].update(text="1,440, because there are 24 hours of 60 minutes in every day"), "much longer than the others", quiz)
    advice("an all-of-the-above option", lambda i: i["questions"][0]["options"][3].update(text="All of the above"), "tests reading of the list", quiz)

    def many(n):
        def fn(i):
            i["questions"] = [{"id": "item-%d-x" % k, "section": "basics", "type": "single", "text": "Item %d?" % k, "options": ["Yes", "No"]} for k in range(n)]
            i["tallies"] = []
        return fn

    good("sixty questions", many(60), absent=("ERROR", "past about 60"))
    advice("sixty-one questions", many(61), "there are 61 questions")
    # reading the input
    text = json.dumps(base, indent=1)
    R.case("validate: a trailing comma", V, [R.path("v.json", text.replace('"version": 1,', '"version": 1,,', 1))], 2, "not strict JSON")
    R.case("validate: NaN as a number", V, [R.path("v.json", text.replace('"min": 20', '"min": NaN', 1))], 2, "not strict JSON")
    R.case("validate: a key written twice", V, [R.path("v.json", text.replace('"version": 1,', '"version": 1, "version": 2,', 1))], 2, "written twice")
    R.case("validate: a file that is not UTF-8", V, [R.path("v.json", b'{"id": "\xff\xfe"}')], 2, "not valid UTF-8")
    R.case("validate: a file with NUL bytes", V, [R.path("v.json", b'{"id": "a\x00b"}')], 2, "NUL bytes")
    R.case("validate: a byte-order mark is accepted", V, [R.path("v.json", b"\xef\xbb\xbf" + text.encode("utf-8"))], 0, "RESULT: PASS")
    R.case("validate: a missing file", V, [R.tmp / "nothing.json"], 2, "cannot read")
    R.case("validate: an unknown option", V, [R.path("v.json", base), "--frobnicate"], 2, "unknown option --frobnicate")
    R.case("validate: an option with no value", V, [R.path("v.json", base), "--engine"], 2, "--engine needs a value")
    R.case("validate: no file", V, [], 2, "expected 1 file(s), got 0")
    # built pages
    engine = ENGINE.read_text(encoding="utf-8")
    R.case("validate: the shipped engine and its demo", V, [ENGINE, "--engine", ENGINE], 0, "RESULT: PASS")
    R.case("validate: a page with no END marker", V, [R.path("p.html", engine.replace("/* ====== END INSTRUMENT DATA", "/* ====== FINISH", 1))], 2, "exactly one BEGIN INSTRUMENT DATA and one END INSTRUMENT DATA")
    R.case("validate: a page whose engine was edited outside the data block", V, [R.path("p.html", engine.replace("var SCHEMA = 1;", "var SCHEMA = 2;", 1)), "--engine", ENGINE], 1, "differs from the reference engine")
    # revisions
    v2 = load("all_types_v2.json")

    def cmp(name, new, code, *phrases):
        R.case("compare: " + name, V, ["--compare", R.path("old.json", base), R.path("new.json", new)], code, *phrases)

    cmp("a revision that adds questions, reorders and rewords lightly", v2, 0, "16 id(s) kept, 2 added, 0 removed", "RESULT: PASS")
    cmp("the same file twice", base, 0, "RESULT: PASS")

    def renumber(i):
        ids = [q["id"] for q in i["questions"]]
        i["questions"].insert(0, {"id": "", "section": "basics", "type": "single", "text": "Who is the shelf for?", "options": ["Me", "Someone else"]})
        for q, new_id in zip(i["questions"], ids + ["extra-last"]):
            q["id"] = new_id
        for q in i["questions"]:
            q.pop("show_if", None)
        i["version"] = 2

    cmp("ids renumbered after a question was put first", changed(base, renumber), 1, "looks reused for another question", "changed type")
    cmp("an id removed", changed(base, lambda i: (i["questions"].pop(4), i.update(version=2))), 1, "is in the old version and missing from the new one")
    cmp("an id whose type changed", changed(base, lambda i: (q_of(i, "urgency").update(type="number"), i.update(version=2))), 1, "changed type from scale to number")
    cmp("questions changed with the version left alone", changed(v2, lambda i: i.update(version=1)), 1, "the version is still 1")
    cmp("a version that went down", changed(base, lambda i: i.update(version=0)), 1, "went down")
    cmp("a different instrument id", changed(v2, lambda i: i.update(id="another-form")), 1, "the instrument id changed")
    cmp("an option removed from a kept question", changed(base, lambda i: (q_of(i, "purpose")["options"].pop(), i.update(version=2))), 0, "lost or renamed 1 option(s)")
    R.case("compare: one file only", V, ["--compare", R.path("old.json", base)], 2, "expected 2 file(s), got 1")


def build_cases(R):
    base = load("all_types.json")
    B, V = "build_instrument.py", "validate_instrument.py"
    out = R.tmp / "built.html"
    src = R.path("i.json", base)

    def same_back(r):
        from validate_instrument import load_instrument
        return None if load_instrument(str(out))[0] == base else "the instrument read back from the built page differs from the one put in"

    R.case("build: a valid instrument", B, [src, "--engine", ENGINE, "--out", out], 0, "wrote", "RESULT: PASS", check=same_back)
    R.case("build: the built page differs from the engine only in its data block", V, [out, "--engine", ENGINE], 0, "RESULT: PASS")
    nasty = changed(base, lambda i: (i.update(title="Caf%s </script><script>alert(1)</script>" % E_ACUTE), q_of(i, "purpose").update(options=["</script>", "<!--", "Tools"])))
    out2 = R.tmp / "nasty.html"

    def nasty_ok(r):
        from validate_instrument import load_instrument
        text = out2.read_text(encoding="utf-8")
        if load_instrument(str(out2))[0] != nasty:
            return "the instrument read back differs"
        if text.count("</script>") != ENGINE.read_text(encoding="utf-8").count("</script>"):
            return "text in the data block closed the script element"
        return None if all(ord(c) < 128 for c in text) else "the built page is not plain ASCII"

    R.case("build: text that would close the script element, and a letter outside ASCII", B, [R.path("i.json", nasty), "--engine", ENGINE, "--out", out2], 0, "wrote", check=nasty_ok)
    out3 = R.tmp / "never.html"
    R.case("build: an instrument with an error writes nothing", B, [R.path("i.json", changed(base, lambda i: q_of(i, "rooms").update(id="purpose"))), "--engine", ENGINE, "--out", out3], 1,
           "the id is used twice", "Nothing was written", check=lambda r: "a file was written despite the error" if out3.exists() else None)
    R.case("build: --out naming the instrument file", B, [src, "--engine", ENGINE, "--out", src], 2, "inputs are never overwritten")
    R.case("build: no --out", B, [src, "--engine", ENGINE], 2, "usage:")
    R.case("build: a built page given where the instrument should be", B, [out, "--engine", ENGINE, "--out", R.tmp / "x.html"], 2, "give the instrument as a .json file")
    R.case("build: an unknown option", B, [src, "--engine", ENGINE, "--out", out, "--fast"], 2, "unknown option --fast")


def parse_cases(R):
    P = "parse_export.py"
    md = (FIX / "export_all_types.md").read_text(encoding="utf-8")
    quiz = (FIX / "export_quiz.md").read_text(encoding="utf-8")
    block = (FIX / "response_survey.txt").read_text(encoding="utf-8")

    def js(r):
        return json.loads(r.stdout)

    R.case("parse: the stored intake export", P, [R.path("e.md", md)], 0, "13 question(s) shown: 11 answered, 2 skipped", "RESULT: PASS")
    R.case("parse: the summary gives the hidden count the export states", P, [R.path("e.md", md)], 0, "3 hidden by earlier answers", absent=("0 hidden",))
    R.case("parse: the summary of a response block counts its HIDDEN lines", P, [R.path("b.txt", block)], 0, "5 question(s) shown", "1 hidden by earlier answers")
    R.case("parse: the stored intake export as JSON", P, [R.path("e.md", md), "--json"], 0, '"format": "elicitor-markdown-1"',
           check=lambda r: None if [q["type"] for q in js(r)["questions"]].count("rank") == 1 and js(r)["errors"] == [] else "unexpected structure")
    plain = subprocess.run([sys.executable, "-B", str(HERE / P), R.path("e.md", md), "--json"], capture_output=True, text=True).stdout

    def same_as_plain(r):
        return None if json.loads(r.stdout)["questions"] == json.loads(plain)["questions"] else "the questions differ from the plain parse"

    R.case("parse: Windows line endings give the same result", P, [R.path("e.md", md.replace("\n", "\r\n")), "--json"], 0, check=same_as_plain)
    R.case("parse: a byte-order mark gives the same result", P, [R.path("e.md", b"\xef\xbb\xbf" + md.encode("utf-8")), "--json"], 0, check=same_as_plain)
    R.case("parse: spaces added at line ends give the same result", P, [R.path("e.md", md.replace("\n", "   \n")), "--json"], 0, check=same_as_plain)
    R.case("parse: chat text around the export is ignored and counted", P, [R.path("e.md", "Here you go, filled it in on the train.\n\n" + md + "\nLet me know if anything is unclear.\n")], 0, "2 line(s) outside the export were ignored")
    lines = md.split("\n")
    R.case("parse: an export cut off before its last line", P, [R.path("e.md", "\n".join(lines[:-8]))], 1, "cut short")
    start = lines.index(next(ln for ln in lines if ln.startswith("### [rooms]")))
    R.case("parse: one question block removed", P, [R.path("e.md", "\n".join(lines[:start] + lines[start + 6:]))], 1, "the last line states 13 question(s) but 12 block(s)", "the header says shown = 13")
    R.case("parse: a count in the header edited", P, [R.path("e.md", md.replace("Answered: 11.", "Answered: 12."))], 1, "the header says answered = 12 but the blocks give 11")
    R.case("parse: a likert answer out of range", P, [R.path("e.md", md.replace("Answer: 1 of 5, Strongly disagree", "Answer: 9 of 5, Strongly disagree"))], 1, "does not fit type likert")
    R.case("parse: a number answer that is not a number", P, [R.path("e.md", md.replace("Answer: 146.5 cm", "Answer: about 150 cm"))], 1, "does not fit type number")
    R.case("parse: an unknown type", P, [R.path("e.md", md.replace("Type: rank", "Type: sorting"))], 1, "unknown type 'sorting'")
    R.case("parse: a block repeated", P, [R.path("e.md", "\n".join(lines[:start] + lines[start:start + 6] + lines[start:]))], 1, "question id 'rooms' appears twice")
    R.case("parse: the tally caveat removed", P, [R.path("e.md", md.replace("These totals are counts of your answers. They are not a validated measure of anything.\n", ""))], 1, "lost its caveat line")
    R.case("parse: a finished time that is not a real time", P, [R.path("e.md", "\n".join("Finished: 2026-13-45T25:61:00Z" if ln.startswith("Finished: ") else ln for ln in lines))], 1, "not a real time")
    R.case("parse: text that is not an export", P, [R.path("e.md", "Dear all,\nplease find my thoughts below.\n")], 1, "this is not a questionnaire export")
    R.case("parse: the stored quiz export", P, [R.path("q.md", quiz)], 0, "score:", "RESULT: PASS")
    R.case("parse: a quiz score line edited", P, [R.path("q.md", quiz.replace("\nCorrect: ", "\nCorrect: 9"))], 1, "the Score section says correct")
    R.case("parse: a quiz result flipped", P, [R.path("q.md", quiz.replace("Result: incorrect", "Result: correct", 1))], 1, "the Score section says correct")
    R.case("parse: a quiz with its Score section cut off", P, [R.path("q.md", quiz.split("## Score")[0] + "\nEnd of export: 6 questions.\n")], 1, "the Score section is missing")
    R.case("parse: the stored response block", P, [R.path("r.txt", block)], 0, "elicitor-response-1", "RESULT: PASS")
    R.case("parse: a response block with no closing line", P, [R.path("r.txt", "\n".join(block.split("\n")[:-2]))], 1, "has no closing line")
    R.case("parse: a response block with one line lost", P, [R.path("r.txt", "\n".join(ln for ln in block.split("\n") if not ln.startswith("pace = ")))], 1, "states 6 question(s) but 5 were found")
    R.case("parse: a response block whose quotes were made curly", P, [R.path("r.txt", block.replace('pace = "', "pace = " + CURLY_OPEN).replace('"\nkept', CURLY_CLOSE + "\nkept"))], 1, "is damaged")
    R.case("parse: an empty file", P, [R.path("e.md", "")], 2, "is empty")
    R.case("parse: a file that is not UTF-8", P, [R.path("e.md", b"\xff\xfe\x00bad")], 2, "NUL bytes")
    R.case("parse: an unknown option", P, [R.path("e.md", md), "--pretty"], 2, "unknown option --pretty")
    R.case("parse: two files", P, [R.path("e.md", md), R.path("e.md", md)], 2, "expected one file")


def collect_cases(R):
    C = "collect_responses.py"
    block = (FIX / "response_survey.txt").read_text(encoding="utf-8")

    def variant(n, **kw):
        text = block.replace("finished: 20", "finished: 21", 1) if n else block
        lines = text.split("\n")
        stamp = next(i for i, ln in enumerate(lines) if ln.startswith("finished: "))
        lines[stamp] = "finished: 2026-10-%02dT09:00:00Z" % (10 + n)
        text = "\n".join(lines)
        for old, new in kw.get("swap", []):
            assert old in text, old
            text = text.replace(old, new)
        return text

    a, b, c = variant(1), variant(2, swap=[("useful = ", "useful = 5\nxx-removed = ")]), variant(3)
    b = "\n".join(ln for ln in b.split("\n") if not ln.startswith("xx-removed"))
    fa, fb, fc = R.path("a.txt", "Hello,\nmy answers are below.\n\n" + a + "\nThanks\n"), R.path("b.txt", b), R.path("c.txt", c)
    out = R.tmp / "merged.csv"

    def rows(path=out):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.reader(f))

    def three(r):
        got = rows()
        if len(got) != 4:
            return "expected a header and 3 rows, found %d lines" % len(got)
        head = got[0]
        if head[:4] != ["source", "instrument", "version", "finished"] or "pace" not in head or "tally:rated-high" not in head:
            return "unexpected header %r" % head
        if got[1][0] != Path(fa).name + "#1":
            return "the row is not named after its file"
        cellmap = dict(zip(head, got[1]))
        return None if cellmap["pace-where"] in ("(not shown)", "(skipped)", "") or cellmap["pace-where"] else "bad cell"

    R.case("collect: three blocks, one wrapped in a message", C, [fa, fb, fc, "--out", out], 0, "wrote", "3 row(s)", "RESULT: PASS", check=three)
    R.case("collect: the rows as JSON with no file", C, [fa, fb, "--json"], 0, '"rows": [', check=lambda r: None if len(json.loads(r.stdout)["rows"]) == 2 else "expected 2 rows")
    other = variant(4, swap=[("instrument: fixture-survey", "instrument: another-survey")])
    out2 = R.tmp / "never.csv"
    R.case("collect: a block from another instrument", C, [fa, R.path("o.txt", other), fc, "--out", out2], 1, "is for instrument 'another-survey' version 1; expected 'fixture-survey' version 1", "Nothing was written",
           check=lambda r: "a CSV was written despite the error" if out2.exists() else None)
    newer = variant(5, swap=[("version: 1", "version: 2")])
    fn = R.path("n.txt", newer)
    R.case("collect: a block from another version", C, [fa, fn, "--out", out2], 1, "is for instrument 'fixture-survey' version 2; expected 'fixture-survey' version 1", "taken from")
    R.case("collect: the expected version given on the command line", C, [fa, fn, "--out", out2, "--instrument", "fixture-survey", "--version", "2"], 1, "a.txt#1 is for instrument 'fixture-survey' version 1; expected 'fixture-survey' version 2 (given on the command line)")
    R.case("collect: the same block twice", C, [fa, R.path("dup.txt", a), "--out", out2], 1, "is an exact repeat of")
    R.case("collect: two blocks in one file", C, [R.path("two.txt", a + "\n\n" + c), "--out", R.tmp / "two.csv"], 0, "2 block(s) in 1 file(s)", check=lambda r: None if [x[0][-2:] for x in rows(R.tmp / "two.csv")[1:]] == ["#1", "#2"] else "rows are not numbered within the file")
    R.case("collect: a file with no block beside one with a block", C, [fa, R.path("none.txt", "nothing here\n"), "--out", R.tmp / "one.csv"], 0, "holds no response block")
    R.case("collect: no block anywhere", C, [R.path("none.txt", "nothing here\n"), "--out", out2], 1, "no response block was found")
    missing = "\n".join(ln for ln in variant(6).split("\n") if not ln.startswith(("kept = ", "kept.note = "))).replace("6 questions, 2 notes", "5 questions, 1 note")
    R.case("collect: a block with a different set of question ids", C, [fa, R.path("m.txt", missing), "--out", out2], 1, "lists different question ids", "missing: kept")
    cut = "\n".join(variant(7).split("\n")[:-2])
    R.case("collect: a block cut short", C, [fa, R.path("cut.txt", cut), "--out", out2], 1, "has no closing line")
    formula = variant(8, swap=[('one-change = "', 'one-change = "=HYPERLINK(1) ')])
    ff = R.path("f.txt", formula)
    R.case("collect: an answer that a spreadsheet would run as a formula", C, [ff, "--out", R.tmp / "g.csv"], 0, "1 text cell(s) began with", check=lambda r: None if any(x.startswith("'=HYPERLINK") for x in rows(R.tmp / "g.csv")[1]) else "the cell was not guarded")
    R.case("collect: the same with the guard turned off", C, [ff, "--out", R.tmp / "ng.csv", "--no-guard"], 0, "RESULT: PASS", absent=("began with",), check=lambda r: None if any(x.startswith("=HYPERLINK") for x in rows(R.tmp / "ng.csv")[1]) else "the cell was changed")
    piped = variant(9, swap=[('kept = ["', 'kept = ["A | B","')])
    fp = R.path("p.txt", piped)
    R.case("collect: a chosen option that contains the separator", C, [fp, "--out", out2], 1, "contains ' | '", "--multi json")
    R.case("collect: the same with --multi json", C, [fp, "--out", R.tmp / "j.csv", "--multi", "json"], 0, "RESULT: PASS", check=lambda r: None if any(x.startswith('["A | B"') for x in rows(R.tmp / "j.csv")[1]) else "the list was not written as JSON")
    marker = variant(10, swap=[('one-change = "', 'one-change = "(skipped)"\nxx = "')])
    marker = "\n".join(ln for ln in marker.split("\n") if not ln.startswith("xx = "))
    R.case("collect: a typed answer identical to a marker", C, [R.path("mk.txt", marker), "--out", out2], 1, "cannot be told apart from the marker")
    long_line = next(ln for ln in a.split("\n") if ln.startswith("one-change = "))
    wrapped = a.replace(long_line, long_line[:30] + "\n" + long_line[30:])
    R.case("collect: a long line that a mail program wrapped", C, [R.path("w.txt", wrapped), "--out", R.tmp / "w.csv"], 0, "1 wrapped line(s) were joined back",
           check=lambda r: None if json.loads(long_line.split(" = ", 1)[1]) in rows(R.tmp / "w.csv")[1] else "the rejoined text differs from the original")
    R.case("collect: --out naming an input", C, [fa, "--out", fa], 2, "inputs are never overwritten")
    R.case("collect: no --out and no --json", C, [fa], 2, "--out RESPONSES.csv is needed")
    R.case("collect: an unknown --multi value", C, [fa, "--out", out2, "--multi", "csv"], 2, "--multi takes pipe or json")
    R.case("collect: --version without --instrument", C, [fa, "--out", out2, "--version", "1"], 2, "give --instrument and --version together")
    R.case("collect: --version that is not a whole number", C, [fa, "--out", out2, "--instrument", "x", "--version", "1.5"], 2, "--version needs a whole number")
    R.case("collect: no files", C, ["--out", out2], 2, "give at least one file")
    R.case("collect: an unknown option", C, [fa, "--out", out2, "--quiet"], 2, "unknown option --quiet")


def main(argv):
    only, as_json, it = None, False, iter(argv)
    for a in it:
        if a == "--json":
            as_json = True
        elif a == "--only":
            only = next(it, None)
            if only is None:
                print("test_tools: --only needs a word", file=sys.stderr)
                return 2
        else:
            print("test_tools: unknown option " + a, file=sys.stderr)
            return 2
    sys.path.insert(0, str(HERE))
    tmp = tempfile.mkdtemp(prefix="elicitor-tools-")
    try:
        R = Runner(tmp, only)
        validate_cases(R)
        build_cases(R)
        parse_cases(R)
        collect_cases(R)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [r for r in R.results if not r["passed"]]
    if as_json:
        text = json.dumps({"cases": len(R.results), "failed": len(failed), "results": R.results}, indent=1, ensure_ascii=True)
    else:
        L = []
        for r in R.results:
            if not r["passed"]:
                L.append("FAIL %s" % r["case"])
                L += ["       " + w for w in r["why"]]
                L += ["       | " + ln[:200] for ln in r["output"]]
        by_tool = {}
        for r in R.results:
            k = by_tool.setdefault(r["tool"], [0, 0])
            k[0] += 1
            k[1] += r["passed"]
        L += ["%-26s %d of %d case(s) passed" % (tool, v[1], v[0]) for tool, v in by_tool.items()]
        L.append("RESULT: %s. %d of %d case(s) passed. Each case is a planted fault that must be refused or its nearest valid input that must be accepted."
                 % ("FAIL" if failed else "PASS", len(R.results) - len(failed), len(R.results)))
        text = "\n".join(L)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
