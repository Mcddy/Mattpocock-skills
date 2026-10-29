"""Template: recompute a course's answers from their "check" fields. Copy it, add your subject's operations, run it.

Usage:
  python verifier-template.py COURSE [--json]
  python verifier-template.py --selftest [--json]

COURSE is a course JSON file or a built course page (.html; the course is read from between the
"COURSE DATA: BEGIN" and "COURSE DATA: END" markers). Standard library only. Reads the file, changes nothing.

How to use it. Beside each answer in the course, write a check: {"op": "name", "args": [...]}.
Then add one function per operation to OPS below. Compute each with a trusted library or with
plain arithmetic from the arguments. Never look the answer up in the course: a check that reads
the course's own answer confirms nothing. The two operations shipped here (add, mul) are only
there so the self-test has something to run.

What it enforces (ERROR, exit 1):
  - practice and gate items: the option marked correct states the computed value, and no other
    option states it
  - blanks, independent answers and challenge tasks: the stated answer equals the computed value
    (spaces and letter case ignored)
  - worked steps and solution steps: the printed result states the computed value
  - cards: the back states the computed value
  - any of those that contains a digit and carries no check: every numeric answer must be recomputed
  - a check naming an operation that OPS does not define
What it reports for a person to read (ADVISORY):
  - how many explanations, hints, captions and theory blocks contain digits. This template does
    not recompute prose. Read each one, or extend the template with patterns for your subject.
What it cannot tell: whether a non-numeric answer is right, whether an explanation is sound, or
whether your operation is itself correct. Test each operation on a case you worked by hand.

--selftest runs the template on a four-answer course held in this file, then plants a wrong
option, a wrong blank, a wrong card and a missing check, and confirms each is reported.

Exit codes: 0 nothing failed. 1 a check failed. 2 bad arguments or unreadable input.
"""
import copy
import json
import re
import sys
from pathlib import Path

FLAGS = {"--json", "--selftest"}
DATA_BLOCK = re.compile(r"/\* === COURSE DATA: BEGIN[^\n]*\*/\s*const COURSE\s*=\s*(.*?);\s*/\* === COURSE DATA: END === \*/", re.S)

# ---------- ADD YOUR SUBJECT'S OPERATIONS HERE ----------
# name -> function of the check's args, returning the value as the course should print it.
OPS = {
    "add": lambda a, b: a + b,
    "mul": lambda a, b: a * b,
}


class InputError(Exception):
    pass


def read_course(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise InputError("cannot read %s: %s" % (path, e.strerror or e))
    if b"\x00" in raw:
        raise InputError("%s contains NUL bytes; it is not a text file" % path)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError("%s is not valid UTF-8" % path)
    if str(path).lower().endswith((".html", ".htm")):
        m = DATA_BLOCK.search(text)
        if not m:
            raise InputError("%s has no COURSE DATA block" % path)
        text = m.group(1)

    def refuse(token):
        raise InputError("%s is not allowed in course data" % token)
    try:
        course = json.loads(text, parse_constant=refuse)
    except ValueError as e:
        raise InputError("%s is not valid JSON: %s" % (path, str(e)[:80]))
    if not isinstance(course, dict) or not isinstance(course.get("modules"), list):
        raise InputError("%s is not a course: it has no list of modules" % path)
    return course


def checks_of(holder):
    out = [holder["check"]] if isinstance(holder.get("check"), dict) else []
    return out + [c for c in holder.get("checks", []) if isinstance(c, dict)] if isinstance(holder.get("checks"), list) else out


def compute(check):
    """The value of one check, as text. Raises ValueError with a message a person can act on."""
    op = check.get("op")
    if op not in OPS:
        raise ValueError('the check names "%s", which OPS does not define' % op)
    try:
        return str(OPS[op](*check.get("args", [])))
    except Exception as e:  # noqa: BLE001  (a malformed argument must not stop the run)
        raise ValueError("check %s(%s) could not be computed: %s" % (op, ", ".join(str(a) for a in check.get("args", [])), str(e)[:80]))


def has_digit(s):
    return isinstance(s, str) and re.search(r"\d", s) is not None


def states(text, value):
    """True when value stands in text as a whole value, not inside a longer number."""
    t, k = str(text).lower(), str(value).lower()
    i = t.find(k)
    while i >= 0:
        before = t[i - 1] if i > 0 else " "
        after = t[i + len(k):i + len(k) + 2]
        if not (before.isalnum() or before in "./") and not (after[:1].isalnum() or (after[:1] == "." and after[1:2].isdigit())):
            return True
        i = t.find(k, i + 1)
    return False


def norm(s):
    return re.sub(r"\s+", "", str(s)).lower()


class Tally:
    def __init__(self):
        self.errors, self.recomputed, self.conceptual, self.prose = [], 0, 0, 0

    def values(self, where, holder, shown):
        """The computed values for holder, or None after logging why there are none."""
        checks = checks_of(holder)
        if not checks:
            if has_digit(shown):
                self.errors.append('%s: "%s" contains a number and has no check' % (where, str(shown)[:50]))
            else:
                self.conceptual += 1
            return None
        try:
            return [compute(c) for c in checks]
        except ValueError as e:
            self.errors.append("%s: %s" % (where, e))
            return None

    def contains(self, where, holder, shown):
        want = self.values(where, holder, shown)
        if want is None:
            return
        missing = [w for w in want if not states(shown, w)]
        if missing:
            self.errors.append('%s: states "%s" and the computed value is "%s"' % (where, str(shown)[:60], "; ".join(missing)))
        else:
            self.recomputed += 1

    def equals(self, where, holder):
        want = self.values(where, holder, holder.get("answer"))
        if want is None:
            return
        if len(want) != 1 or norm(holder.get("answer")) != norm(want[0]):
            self.errors.append('%s: the stated answer is "%s" and the computed answer is "%s"' % (where, holder.get("answer"), "; ".join(want)))
        else:
            self.recomputed += 1

    def item(self, where, it):
        opts = [o for o in it.get("options", []) if isinstance(o, dict)]
        right = [o for o in opts if o.get("correct") is True]
        self.prose += sum(1 for o in opts if has_digit(o.get("why")))
        if len(right) != 1:
            self.errors.append("%s: does not have exactly one correct option" % where)
            return
        want = self.values(where, it, right[0].get("text"))
        if want is None:
            return
        if not all(states(right[0].get("text", ""), w) for w in want):
            self.errors.append('%s: the option marked correct is "%s" and the computed answer is "%s"' % (where, right[0].get("text", "")[:60], "; ".join(want)))
            return
        for o in opts:
            if o is not right[0] and all(states(o.get("text", ""), w) for w in want):
                self.errors.append('%s: the option "%s" is marked wrong and states the computed answer' % (where, o.get("text", "")[:60]))
                return
        self.recomputed += 1

    def step(self, where, s):
        self.prose += 1 if has_digit(s.get("text")) else 0
        if isinstance(s.get("blank"), dict):
            self.prose += 1 if has_digit(s["blank"].get("hint")) else 0
            self.equals(where + " blank", s["blank"])
        elif "result" in s:
            self.contains(where, s, s.get("result"))


def verify(course):
    T = Tally()
    for m in course.get("modules", []):
        if not isinstance(m, dict) or m.get("status") != "ready":
            continue
        mw = "module %s" % m.get("id")
        for sec in m.get("theory", []):
            T.prose += sum(1 for b in sec.get("blocks", []) if has_digit(json.dumps(b)))
        T.prose += sum(1 for v in m.get("visuals", []) if has_digit(v.get("caption")))
        for kind, items in (("practice", m.get("quiz", [])), ("gate", (m.get("gate") or {}).get("items", []))):
            for it in items:
                T.item("%s %s item %s" % (mw, kind, it.get("id")), it)
        for ex in m.get("worked", []):
            ew = "%s worked %s" % (mw, ex.get("id"))
            for lv in ("full", "partial"):
                for i, s in enumerate((ex.get(lv) or {}).get("steps", [])):
                    T.step("%s %s step %d" % (ew, lv, i + 1), s)
            ind = ex.get("independent") or {}
            for i, a in enumerate(ind.get("answers", [])):
                T.equals("%s independent answer %d" % (ew, i + 1), a)
            for i, s in enumerate(ind.get("solution", [])):
                T.step("%s independent solution step %d" % (ew, i + 1), s)
        ch = m.get("challenge")
        if isinstance(ch, dict):
            for i, a in enumerate(ch.get("tasks", [])):
                T.equals("%s challenge task %d" % (mw, i + 1), a)
            for i, s in enumerate(ch.get("solution", [])):
                T.step("%s challenge solution step %d" % (mw, i + 1), s)
        for c in m.get("cards", []):
            T.contains("%s card %s" % (mw, c.get("id")), c, c.get("back"))
    return T


# ---------- self-test ----------
def _sample():
    """SYNTHETIC. Only the parts this template reads; it is not a complete course."""
    return {"id": "template-selftest", "version": 1, "modules": [{
        "id": "m", "status": "ready",
        "quiz": [{"id": "q1", "stem": "What is 17 plus 5?", "check": {"op": "add", "args": [17, 5]}, "options": [
            {"text": "22", "correct": True, "why": "17 plus 5 is 22."},
            {"text": "85", "correct": False, "why": "That multiplies the two numbers."},
            {"text": "12", "correct": False, "why": "That subtracts the smaller from the larger."}]},
            {"id": "q2", "stem": "Which word names the result of adding?", "options": [
                {"text": "sum", "correct": True, "why": "Adding gives a sum."},
                {"text": "product", "correct": False, "why": "A product comes from multiplying."},
                {"text": "quotient", "correct": False, "why": "A quotient comes from dividing."}]}],
        "worked": [{"id": "w1",
                    "full": {"steps": [{"text": "Multiply 6 by 7.", "result": "42", "check": {"op": "mul", "args": [6, 7]}}]},
                    "partial": {"steps": [{"text": "Multiply 8 by 9.", "blank": {"label": "Product", "answer": "72", "hint": "Eight nines.", "check": {"op": "mul", "args": [8, 9]}}}]},
                    "independent": {"answers": [], "solution": []}}],
        "cards": [{"id": "c1", "front": "12 plus 30", "back": "42", "check": {"op": "add", "args": [12, 30]}}]}]}


def selftest():
    base = verify(_sample())
    results = [("the sample verifies: 4 recomputed, 1 answer with no number, no errors", not base.errors and base.recomputed == 4 and base.conceptual == 1, "; ".join(base.errors[:2]))]

    def plant(name, change):
        c = copy.deepcopy(_sample())
        change(c["modules"][0])
        T = verify(c)
        results.append(("planted fault caught: " + name, len(T.errors) == 1, T.errors[0] if T.errors else "nothing was reported"))

    def swap(m):
        m["quiz"][0]["options"][0]["correct"], m["quiz"][0]["options"][1]["correct"] = False, True
    plant("the wrong option marked correct", swap)
    plant("a wrong answer for a blank (73, where 72 is accepted)", lambda m: m["worked"][0]["partial"]["steps"][0]["blank"].update(answer="73"))
    plant("a wrong card (420 is not 42)", lambda m: m["cards"][0].update(back="420"))
    plant("a numeric result with its check removed", lambda m: m["worked"][0]["full"]["steps"][0].pop("check"))
    plant("a check naming an operation that is not defined", lambda m: m["cards"][0]["check"].update(op="cube"))
    return results


def emit(text):
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a in FLAGS:
            flags.add(a)
        elif a.startswith("--"):
            print("verifier-template: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if "--selftest" in flags:
        if args:
            print("verifier-template: --selftest takes no file", file=sys.stderr)
            return 2
        results = selftest()
        failed = [r for r in results if not r[1]]
        if "--json" in flags:
            emit(json.dumps({"checks": [{"check": r[0], "ok": r[1], "detail": r[2]} for r in results], "failed": len(failed), "total": len(results)}, indent=1, ensure_ascii=True))
        else:
            for name, ok, detail in results:
                emit("%-5s %s%s" % ("PASS" if ok else "FAIL", name, ("\n      " + detail[:160]) if detail else ""))
            emit("RESULT: %s. %d of %d checks passed." % ("FAIL" if failed else "PASS", len(results) - len(failed), len(results)))
        return 1 if failed else 0
    if len(args) != 1:
        print(__doc__ if not argv else "verifier-template: expected one course file (page or JSON)", file=sys.stdout if not argv else sys.stderr)
        return 2
    try:
        course = read_course(args[0])
    except InputError as e:
        print("verifier-template: %s" % e, file=sys.stderr)
        return 2
    T = verify(course)
    if "--json" in flags:
        emit(json.dumps({"course": course.get("id"), "version": course.get("version"), "errors": T.errors, "recomputed": T.recomputed,
                         "answers_with_no_number": T.conceptual, "prose_with_digits_not_recomputed": T.prose}, indent=1, ensure_ascii=True))
        return 1 if T.errors else 0
    lines = ["verifier-template: %s version %r" % (course.get("id"), course.get("version"))]
    lines += ["  ERROR     " + e for e in T.errors]
    if T.prose:
        lines.append("  ADVISORY  %d explanation(s), hint(s), caption(s) or theory block(s) contain digits and were not recomputed. Read them" % T.prose)
    lines.append("RESULT: %s. %d answer(s) recomputed, %d error(s), %d answer(s) with no number in them. A recomputed number says nothing about how well it is explained."
                 % ("FAIL" if T.errors else "PASS", T.recomputed, len(T.errors), T.conceptual))
    emit("\n".join(lines))
    return 1 if T.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
