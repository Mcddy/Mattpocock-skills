#!/usr/bin/env python3
"""Draw a threat model file as one self-contained HTML page. Standard library only.

Usage:
  python threat_diagram.py MODEL.json --out diagram.html [--allow-errors] [--today YYYY-MM-DD]
                                      [--stale-days 90] [--template FILE] [--json]

MODEL.json is the file threat_check.py reads; see that script's docstring for the format.

What it does: runs the same checks as threat_check.py, then copies the page template from
assets/threat-diagram-template.html and embeds the model, the checker's result and the derived
states in it as data. The page lays the zones out as rows, the elements inside them, and the flows
as lines with a label button; flows that cross a trust boundary are marked. Choosing an element, a
flow or a zone lists its threats with their status in words. The layout is computed in the page by
a fixed rule (zones in file order, elements in file order, two or three to a row), so the same
model always gives the same drawing.

What it enforces (exit 1, nothing written):
  - a model whose structure is broken (missing lists, unknown references, duplicate ids) is never
    drawn: the drawing could not be trusted
  - a model with any other checker error is not drawn unless --allow-errors is given. With that
    option the page is written and carries a banner naming the errors
What it reports for a person to decide: the checker's advisory count, printed and shown in the page.

What it cannot tell: whether the model matches the real system. The page is a reading aid, not a
design tool: it cannot be edited, and it is not a penetration test, an audit or a guarantee.

Output is deterministic: the same model, template and --today give the same bytes. Every string
from the model is embedded as JSON with the characters that could end a script block escaped, and
the page sets it as text. The input file is never changed, and --out may not name it.

Exit codes: 0 page written. 1 the model has errors and was not drawn. 2 bad arguments or
unreadable input.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import threat_check as tc  # noqa: E402

PLACEHOLDER = "__THREAT_MODEL_DATA__"
FLAGS = {"--json", "--allow-errors"}
VALUES = {"--out", "--today", "--stale-days", "--template"}


def embed(payload):
    """JSON that is safe inside a script element: no character that could close the block."""
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    esc = chr(92) + "u00"
    return text.replace("<", esc + "3c").replace(">", esc + "3e").replace("&", esc + "26")


def fail(msg, code=2):
    print("threat_diagram: " + msg, file=sys.stderr)
    return code


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                return fail("%s needs a value" % a)
            opts[a] = v
        elif a.startswith("-") and a != "-":
            return fail("unknown option " + a)
        else:
            args.append(a)
    if len(args) != 1 or "--out" not in opts:
        return fail("give one model file and --out. Usage: python threat_diagram.py MODEL.json --out diagram.html [--allow-errors]")
    today = dt.date.today()
    if "--today" in opts:
        today = tc.parse_date(opts["--today"])
        if today is None:
            return fail("--today needs a real date written YYYY-MM-DD")
    stale = 90
    if "--stale-days" in opts:
        if not re.fullmatch(r"\d{1,5}", opts["--stale-days"]) or int(opts["--stale-days"]) < 1:
            return fail("--stale-days needs a whole number of days, 1 or more")
        stale = int(opts["--stale-days"])
    src, out = Path(args[0]), Path(opts["--out"])
    template_path = Path(opts["--template"]) if "--template" in opts else HERE.parent / "assets" / "threat-diagram-template.html"
    try:
        model = tc.load(src)
    except tc.Unreadable as e:
        return fail(str(e))
    try:
        if out.resolve() == src.resolve() or out.resolve() == template_path.resolve():
            return fail("--out names the model or the template; choose another file")
        template = template_path.read_bytes().decode("utf-8")
    except OSError as e:
        return fail("cannot read the page template %s: %s" % (template_path, e.strerror or e))
    except UnicodeDecodeError:
        return fail("the page template %s is not valid UTF-8" % template_path)
    if template.count(PLACEHOLDER) != 1:
        return fail("the page template must contain %s exactly once" % PLACEHOLDER)

    errors, advisories, summary, derived = tc.check(model, today, stale)
    if derived is None:
        sys.stdout.write(tc.render(model, errors, advisories, summary) + "\n")
        return fail("the model's structure is broken, so it was not drawn. Fix the errors above first", 1)
    if errors and "--allow-errors" not in flags:
        sys.stdout.write(tc.render(model, errors, advisories, summary) + "\n")
        return fail("%d checker error(s), so nothing was written. Fix them, or pass --allow-errors to draw the file as written under a warning banner" % len(errors), 1)
    payload = {"model": model, "check": {"errors": errors, "advisories": advisories, "summary": summary}, "derived": derived, "source": src.name}
    page = template.replace(PLACEHOLDER, embed(payload))
    try:
        out.write_bytes(page.encode("utf-8"))
    except OSError as e:
        return fail("cannot write %s: %s" % (out, e.strerror or e))
    result = {"written": str(out), "bytes": len(page.encode("utf-8")), "zones": len(model["zones"]), "elements": len(model["elements"]),
              "flows": summary["flows"], "boundary_flows": summary["boundary_flows"], "threats": summary["threats"],
              "checker_errors": len(errors), "checker_advisories": len(advisories)}
    if "--json" in flags:
        text = json.dumps(result, indent=1, ensure_ascii=True)
    else:
        text = ("threat_diagram: wrote %(written)s (%(bytes)d bytes): %(zones)d zone(s), %(elements)d element(s), %(flows)d flow(s) of which "
                "%(boundary_flows)d cross a trust boundary, %(threats)d threat(s). Checker: %(checker_errors)d error(s), %(checker_advisories)d advisory note(s).\n"
                "Open it and look at it: this script does not check how the page renders." % result)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
