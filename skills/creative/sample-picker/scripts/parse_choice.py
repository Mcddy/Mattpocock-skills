#!/usr/bin/env python3
"""Turn a pasted sample-picker result into JSON, and check it against the picker it came from.

Usage:
  python parse_choice.py CHOICE.txt [--picker PICKER.json|PICKER.html] [--json]
  python parse_choice.py - [--picker ...]            reads the pasted text from standard input

Input: the text a person copied from a picker's Result view. Either form is accepted:
  - the short text block, from "=== sample-picker choice v1 ===" to "=== end ===". Anything a chat
    adds around it is ignored: other sentences, quote marks at the start of lines, code fences,
    Windows line ends, curly quotation marks in place of straight ones
  - the JSON form (one object with "app": "sample-picker")
Output: the JSON form, always the same shape:
  {"app": "sample-picker", "schema": 1, "content_id": "picker-id@version", "saved_at": "...Z",
   "data": {"kind", "status": "final" | "in progress", "chosen", "chosen_name", "controls": {},
            "shortlist": [], "rejected": [], "notes": {}, "facts": [{"label", "value"}]}}
The short block and the JSON a picker shows for the same session parse to the same object.

What it enforces (ERROR, exit 1):
  - the block is complete (both marker lines) and every line in it is one it knows
  - picker, kind, status, chosen, shortlist, rejected and saved are each present once
  - status "final" has a chosen option, and "in progress" has none
  - the chosen option is not also in the rejected list; an option is not both shortlisted and rejected
  - saved is a real UTC time written YYYY-MM-DDTHH:MM:SSZ
  - with --picker: the picker id and version match, every option id exists in that picker, every
    control exists and its value is one the control allows
What it reports for a person to decide (ADVISORY):
  - the choice is still in progress
  - the chosen option was not the recommended one (so the reason for recommending it did not hold)
  - notes were left on options: read them before acting

What it cannot tell: whether the person meant it. The facts in the block were measured in their
browser at the time; they are not re-measured here.

Exit codes: 0 parsed with no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from fractions import Fraction

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_picker as vp  # noqa: E402
import picker_result as pr  # noqa: E402


FLAGS = {"--json"}
VALUES = {"--picker"}
START, END = "=== sample-picker choice v1 ===", "=== end ==="
KEBAB = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
# curly quotation marks a chat may substitute; the block itself is written in plain ASCII
CURLY = {chr(0x201c): '"', chr(0x201d): '"', chr(0x2018): "'", chr(0x2019): "'"}


class Bad(Exception):
    pass


def no_constant(c):
    raise ValueError("%s is not allowed" % c)


def json_value(text, what):
    try:
        return json.loads(text, parse_constant=no_constant)
    except ValueError:
        raise Bad("%s is not a JSON value: %r" % (what, text[:60]))


def id_list(text, what):
    if text == "(none)":
        return []
    out = [x.strip() for x in text.split(",")]
    for x in out:
        if not KEBAB.fullmatch(x):
            raise Bad("%s holds %r, which is not an option id" % (what, x))
    if len(set(out)) != len(out):
        raise Bad("%s lists an option twice" % what)
    return out


def parse_block(text):
    """The short text form. Returns the envelope."""
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        ln = raw.strip()
        while ln.startswith(">"):
            ln = ln[1:].strip()
        if ln and not ln.startswith("```"):
            lines.append(ln)
    if START not in lines or END not in lines:
        raise Bad("no complete block found: paste everything from %r to %r" % (START, END))
    a = lines.index(START)
    if END not in lines[a:]:
        raise Bad("the block has no end line %r after its start" % END)
    body = lines[a + 1:lines.index(END, a)]
    seen, controls, notes, facts = {}, {}, {}, []
    for ln in body:
        if ": " not in ln and not ln.endswith(":"):
            raise Bad("line %r is not 'key: value'" % ln[:60])
        key, _, rest = ln.partition(":")
        key, rest = key.strip(), rest.strip()
        if key in ("picker", "kind", "status", "chosen", "chosen-name", "shortlist", "rejected", "saved"):
            if key in seen:
                raise Bad("%r appears twice" % key)
            seen[key] = rest
        elif key == "control":
            cid, sep, val = rest.partition(" = ")
            if not sep or not KEBAB.fullmatch(cid.strip()):
                raise Bad("control line %r is not 'control: id = value'" % ln[:60])
            if cid.strip() in controls:
                raise Bad("control %r appears twice" % cid.strip())
            v = json_value(val.strip(), "the value of control %s" % cid.strip())
            if isinstance(v, (dict, list)) or v is None:
                raise Bad("the value of control %s must be text, a number, true or false" % cid.strip())
            controls[cid.strip()] = v
        elif key == "note":
            oid, sep, val = rest.partition(" = ")
            if not sep or not KEBAB.fullmatch(oid.strip()):
                raise Bad("note line %r is not 'note: option-id = \"text\"'" % ln[:60])
            v = json_value(val.strip(), "the note on %s" % oid.strip())
            if not isinstance(v, str) or oid.strip() in notes:
                raise Bad("the note on %s must be one quoted text" % oid.strip())
            notes[oid.strip()] = v
        elif key == "fact":
            try:
                label, end = json.JSONDecoder().raw_decode(rest)
            except ValueError:
                raise Bad("fact line %r does not start with a quoted label" % ln[:60])
            tail = rest[end:]
            if not isinstance(label, str) or not tail.startswith(" = "):
                raise Bad("fact line %r is not 'fact: \"label\" = value'" % ln[:60])
            v = json_value(tail[3:].strip(), "the value of fact %s" % label)
            if isinstance(v, (dict, list, bool)) or v is None:
                raise Bad("the value of fact %s must be text or a number" % label)
            facts.append({"label": label, "value": v})
        else:
            raise Bad("unknown line %r" % ln[:60])
    for need in ("picker", "kind", "status", "chosen", "shortlist", "rejected", "saved"):
        if need not in seen:
            raise Bad("the block has no %r line" % need)
    chosen = None if seen["chosen"] == "(none)" else seen["chosen"]
    if chosen is not None and not KEBAB.fullmatch(chosen):
        raise Bad("chosen holds %r, which is not an option id" % chosen)
    name = None
    if "chosen-name" in seen:
        name = json_value(seen["chosen-name"], "chosen-name")
        if not isinstance(name, str):
            raise Bad("chosen-name must be quoted text")
    return {"app": "sample-picker", "schema": 1, "content_id": seen["picker"], "saved_at": seen["saved"],
            "data": {"kind": seen["kind"], "status": seen["status"], "chosen": chosen, "chosen_name": name, "controls": controls,
                     "shortlist": id_list(seen["shortlist"], "shortlist"), "rejected": id_list(seen["rejected"], "rejected"),
                     "notes": notes, "facts": facts}}


def parse(text):
    if START in text:
        return parse_block(text)
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i:
        try:
            d = json.loads(text[i:j + 1], parse_constant=no_constant)
        except ValueError as e:
            raise Bad("the pasted JSON does not parse (%s)" % str(e)[:60])
        if isinstance(d, dict) and d.get("app") == "sample-picker":
            return d
        raise Bad("the pasted JSON was not saved by a sample picker (app is %r)" % (d.get("app") if isinstance(d, dict) else None))
    raise Bad("no result found: paste everything from %r to %r, or the JSON form" % (START, END))


def on_step(value, minimum, step):
    """Exact decimal-string arithmetic; tolerate at most 1e-9 of one step for float noise."""
    q = (Fraction(str(value)) - Fraction(str(minimum))) / Fraction(str(step))
    lower = q.numerator // q.denominator
    return min(q - lower, lower + 1 - q) <= Fraction(1, 1000000000)


def check(env, picker):
    errors, advisories = [], []
    d = env.get("data")
    if env.get("schema") != 1 or isinstance(env.get("schema"), bool):
        errors.append("schema is %r; this script reads schema 1" % env.get("schema"))
    if not isinstance(d, dict):
        return ["the result has no data"], []
    for k, kind in (("shortlist", list), ("rejected", list), ("notes", dict), ("controls", dict), ("facts", list)):
        if not isinstance(d.get(k), kind):
            errors.append("%s is missing or the wrong shape" % k)
    if errors:
        return errors, advisories
    ident = lambda value: isinstance(value, str) and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", value) is not None
    if d.get("kind") not in vp.KINDS:
        errors.append("kind is not a supported picker kind")
    if d.get("chosen") is not None and not ident(d["chosen"]):
        errors.append("chosen must be an option id or null")
    if d.get("chosen_name") is not None and not isinstance(d["chosen_name"], str):
        errors.append("chosen_name must be text or null")
    for key in ("shortlist", "rejected"):
        values = d[key]
        if not all(ident(v) for v in values):
            errors.append(key + " must contain option ids")
        elif len(set(values)) != len(values):
            errors.append(key + " contains duplicate ids")
    if not all(ident(k) and isinstance(v, str) for k, v in d["notes"].items()):
        errors.append("notes must map option ids to text")
    if not all(ident(k) and (isinstance(v, (str, bool)) or vp.is_num(v)) for k, v in d["controls"].items()):
        errors.append("controls must map ids to text, booleans or finite numbers")
    if not all(isinstance(f, dict) and isinstance(f.get("label"), str) and
               (isinstance(f.get("value"), (str, bool)) or vp.is_num(f.get("value"))) for f in d["facts"]):
        errors.append("facts need a text label and a finite scalar value")
    if errors:
        return errors, advisories
    cid = env.get("content_id")
    if not isinstance(cid, str) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*@[1-9][0-9]*", cid):
        errors.append("picker must be an id and a version, like notes-theme@1; got %r" % cid)
    stamp = env.get("saved_at")
    ok_stamp = isinstance(stamp, str) and STAMP.fullmatch(stamp) is not None
    if ok_stamp:
        try:
            dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            ok_stamp = False
    if not ok_stamp:
        errors.append("saved must be a real UTC time written YYYY-MM-DDTHH:MM:SSZ; got %r" % stamp)
    status, chosen = d.get("status"), d.get("chosen")
    if status not in ("final", "in progress"):
        errors.append("status must be final or in progress; got %r" % status)
    elif status == "final" and not chosen:
        errors.append("status is final but no option is chosen")
    elif status == "in progress" and chosen:
        errors.append("an option is chosen but status says in progress")
    elif status == "in progress":
        advisories.append("the choice is still in progress: there is a shortlist, not a decision. Do not act as if one was made")
    if chosen and chosen in d["rejected"]:
        errors.append("the chosen option %s is also in the rejected list" % chosen)
    both = sorted(set(d["shortlist"]) & set(d["rejected"]))
    if both:
        errors.append("%s is both shortlisted and rejected" % both[0])
    if d["notes"]:
        advisories.append("%d note(s) were left; read them before acting: %s" % (len(d["notes"]), ", ".join(sorted(d["notes"]))))
    if picker is not None:
        want = "%s@%s" % (picker.get("id"), picker.get("version", 1))
        if cid != want:
            errors.append("this result is for %s, but the picker given is %s" % (cid, want))
        if d.get("kind") != picker.get("kind"):
            errors.append("kind %r does not match the source picker kind %r" % (d.get("kind"), picker.get("kind")))
        by_id = {o["id"]: o for o in picker["options"]}
        if d.get("chosen_name") is not None:
            if chosen not in by_id or d["chosen_name"] != by_id[chosen]["name"]:
                errors.append("chosen_name must match the current name for the actual chosen option")
        ids = set(by_id)
        for oid in ([chosen] if chosen else []) + list(d["shortlist"]) + list(d["rejected"]) + list(d["notes"]):
            if oid not in ids:
                errors.append("option %r is not in the picker" % oid)
        ctls = {c.get("id"): c for c in picker.get("controls", []) if isinstance(c, dict)}
        for k, v in d["controls"].items():
            c = ctls.get(k)
            if c is None:
                errors.append("control %r is not in the picker" % k)
            elif c.get("type") == "toggle" and not isinstance(v, bool):
                errors.append("control %s is a toggle; its value must be true or false, got %r" % (k, v))
            elif c.get("type") == "choice" and v not in [o if isinstance(o, str) else o.get("value") for o in c.get("options", [])]:
                errors.append("control %s has no option %r" % (k, v))
            elif c.get("type") == "range" and (not vp.is_num(v) or not c["min"] <= v <= c["max"]):
                errors.append("control %s must be a number from %s to %s, got %r" % (k, c["min"], c["max"], v))
            elif c.get("type") == "range" and not on_step(v, c["min"], c.get("step", 1)):
                errors.append("control %s must align to its step from min (tolerance 1e-9 of a step)" % k)
        for k in ctls:
            if k not in d["controls"]:
                errors.append("control %r has no value in the result" % k)
        rec = picker.get("recommended") or {}
        if chosen and rec.get("id") and chosen != rec["id"] and chosen in ids:
            advisories.append("the person chose %s, not the recommended %s. Apply their choice; do not argue for the recommendation again" % (chosen, rec["id"]))
    return errors, advisories


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--") or not v.strip():
                print("parse_choice: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("parse_choice: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    picker = None
    if "--picker" in opts:
        try:
            picker = vp.read_data(opts["--picker"])
        except vp.Bad as e:
            print("parse_choice: " + str(e), file=sys.stderr)
            return 2
        if not isinstance(picker, dict):
            print("parse_choice: the picker file does not hold a picker", file=sys.stderr)
            return 2
        try:
            source_errors, source_advisories, _ = vp.check(picker)
        except Exception as e:
            pr.result("runner-error", {"source_picker_valid": False, "source": opts["--picker"], "error_type": type(e).__name__}, "Source picker validation could not finish; no choice was checked.")
            print("parse_choice: invalid source picker (%s)" % str(e)[:160], file=sys.stderr)
            return 2
        if source_errors:
            pr.result("runner-error", {"source_picker_valid": False, "source": opts["--picker"], "errors": source_errors}, "Invalid source picker; no choice was checked.")
            print("parse_choice: invalid source picker: " + source_errors[0], file=sys.stderr)
            return 2
    try:
        raw = sys.stdin.buffer.read() if args[0] == "-" else Path(args[0]).read_bytes()
    except OSError as e:
        print("parse_choice: cannot read %s: %s" % (args[0], e.strerror or e), file=sys.stderr)
        return 2
    if bytes([0]) in raw:
        print("parse_choice: the input contains a NUL byte", file=sys.stderr)
        return 2
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        print("parse_choice: the input is not valid UTF-8", file=sys.stderr)
        return 2
    try:
        env = parse(text)
        errors, advisories = check(env, picker)
    except Bad as e:
        env, errors, advisories = None, [str(e)], []
    pr.observe_failures(errors, "The returned choice failed validation before receipt assembly.")
    d = env.get("data", {}) if isinstance(env, dict) and isinstance(env.get("data"), dict) else {}
    known = {o["id"]: o for o in picker["options"]} if picker is not None else {}
    pr.result("failed" if errors else "partial" if picker is None else "completed", {"picker_bound": picker is not None, "source_picker_valid": picker is not None, "content_id": env.get("content_id") if isinstance(env, dict) else None, "kind": d.get("kind"), "choice_status": d.get("status"), "chosen_id": d.get("chosen"), "chosen_name_from_picker": known.get(d.get("chosen") if isinstance(d.get("chosen"), str) else None, {}).get("name"), "controls": d.get("controls", {}), "errors": errors, "advisories": advisories, "apply_final_allowed": not errors and picker is not None and d.get("status") == "final", "facts": "Reported from the returned block; not remeasured."}, "Choice parsed and checked against source picker." if picker is not None else "Structure parsed only; picker/version/options/tweaks were not checked against a source picker.")
    if "--json" in flags:
        out = json.dumps({"errors": errors, "advisories": advisories, "choice": env}, indent=1, ensure_ascii=True)
    else:
        L = []
        if env is not None and not errors:
            d = env["data"]
            L.append("parse_choice: %s, %s. Chosen: %s%s" % (env["content_id"], d["status"], d["chosen"] or "nothing yet",
                                                         (" (" + d["chosen_name"] + ")") if d.get("chosen_name") else ""))
            if d["controls"]:
                L.append("  controls  " + ", ".join("%s = %s" % (k, json.dumps(v)) for k, v in d["controls"].items()))
            L.append("  shortlist %s" % (", ".join(d["shortlist"]) or "(none)"))
            L.append("  rejected  %s" % (", ".join(d["rejected"]) or "(none)"))
            for k, v in d["notes"].items():
                L.append("  note      %s: %s" % (k, v.replace("\n", " / ")))
        else:
            L.append("parse_choice: the pasted result could not be used")
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("RESULT: %s. %d error(s), %d advisory note(s).%s" % ("FAIL" if errors else "PASS", len(errors), len(advisories),
                                                                    "" if picker is not None else " Not checked against a picker (no --picker)."))
        out = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(pr.run("parse_choice", main, sys.argv[1:]))
