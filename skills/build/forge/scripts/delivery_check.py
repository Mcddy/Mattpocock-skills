#!/usr/bin/env python3
"""Exercise a page inside a sandboxed frame, the way a chat host embeds it.

Usage:
  python delivery_check.py PAGE [--sandbox "allow-scripts"] [--steps FILE] [--step "kind:arg"]...
                                [--width 1100] [--height 800] [--tab-only] [--reduced-motion]
                                [--block-outside] [--json] [--version]

PAGE is an HTML file, or an http(s) address for a page served by a running back end.

Why this exists: a page can work in a browser tab and fail where it is delivered. Hosts show
generated pages inside an iframe with a sandbox attribute. If the sandbox leaves out allow-forms,
the browser drops form submission before the submit event fires, so a Save wired to a form's
submit handler does nothing, with no error on the page. The same page with a click handler on a
type=button control works. This script reproduces that locally.

What it does:
  1. Opens the page in a plain tab and runs your steps.
  2. Opens the page inside <iframe sandbox="..."> and runs the same steps.
  3. Probes the frame: is browser storage available, and does each form's submit event fire.
  4. Reports each step for both runs, and names any step that passes in the tab and fails in the
     frame. That difference is the signature of a delivery failure.

Steps (one per --step, or one per line in a --steps file; lines starting with # are ignored):
  click:SELECTOR                 click an element
  fill:SELECTOR=VALUE            type a value into an input, then leave the field
  check:SELECTOR                 tick a checkbox or select a radio
  select:SELECTOR=VALUE          choose an option in a <select> by its value, or else by its label
  press:SELECTOR=KEY             focus the element and press a key, for example Enter
  expect:SELECTOR=TEXT           the element's text or value contains TEXT
  expect-attr:SELECTOR@ATTR=VAL  the attribute equals VAL
  expect-count:SELECTOR=N        exactly N elements match
  expect-gone:SELECTOR           no element matches
  expect-focus:SELECTOR          keyboard focus is on an element that matches
  reload:                        load the page again, to show what survives a reload
  wait:MILLISECONDS
expect steps retry for up to two seconds, so a page that is waiting on its server has time to answer.

A served page in a frame without allow-same-origin has the origin "null". Its requests to its own
back end are then cross-origin: the back end must answer preflights and allow that origin, and
cookies are not sent. This script exercises that path when PAGE is an address.

--tab-only runs the steps in a plain tab and skips the frame. Use it when the delivery surface is a
confirmed normal web origin (a local server opened in a tab, a deployed address), where the frame
run is irrelevant and only slows the check. A page that refuses to be framed (frame-ancestors or
X-Frame-Options) is reported as such rather than as a delivery failure.

--reduced-motion runs with prefers-reduced-motion: reduce emulated. --block-outside aborts every
request that is not to the page's own origin (or file:, data:, blob:), to show the page still works
when fonts, libraries and outside services fail. Run the steps once with each.

--sandbox takes the tokens to allow, space separated. The default, allow-scripts only, is the
strictest setting under which a scripted page runs at all. A page that passes there needs nothing
else from its host. If you know the host's real token list, pass it.

Limits. This is a stand-in, not the host. A real host adds its own content security policy,
permissions policy and nesting, and its sandbox tokens may differ from what you pass. A pass here
is evidence the page does not depend on forms, storage, popups or dialogs. It is not evidence the
page works in a given product. The only proof of that is exercising the page in the delivered
preview, and a report should say which of the two was done.
The form probe calls requestSubmit() on each form after your steps, on this local copy.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes: 0 every step passed in the frame and no form submission was blocked. 1 a step failed in
the frame, or a form's submission was blocked. 2 bad arguments. 3 partial: no steps were given, so nothing was
exercised. 4 runner error: could not run (prints NOT RUN).
A RECEIPT line on stderr states the result (references/results.md).
"""
import json
import sys
import tempfile
from pathlib import Path
import pathlib

FLAGS = {"--json", "--tab-only", "--reduced-motion", "--block-outside", "--version"}
VERSION = "forge 3.3.2"
VALUES = {"--sandbox", "--steps", "--step", "--width", "--height"}
KINDS = ("click", "fill", "check", "select", "press", "expect", "expect-attr", "expect-count", "expect-gone", "expect-focus", "reload", "wait")
RETRY_MS = 2000

PROBE_JS = r"""
() => {
  const r = {forms: [], storage: 'available'};
  try { localStorage.setItem('__delivery_probe', '1'); localStorage.removeItem('__delivery_probe'); }
  catch (e) { r.storage = 'blocked (' + e.name + ')'; }
  [...document.forms].forEach((f, i) => {
    let fired = false;
    const h = ev => { fired = true; ev.preventDefault(); };
    f.addEventListener('submit', h, true);
    try { f.requestSubmit ? f.requestSubmit() : f.dispatchEvent(new Event('submit', {cancelable: true})); } catch (e) {}
    f.removeEventListener('submit', h, true);
    r.forms.push({index: i, id: f.id || null, submit_event_fired: fired});
  });
  return r;
}
"""


def split_selector(arg):
    """Split SELECTOR=VALUE at the first = that is outside [brackets] and quotes."""
    depth, quote = 0, ""
    for i, ch in enumerate(arg):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif ch == "=" and depth == 0:
            return arg[:i], arg[i + 1:]
    return None, None


def parse_step(s):
    s = s.strip()
    if ":" not in s:
        return None, "step %r has no kind (expected kind:arg)" % s
    kind, arg = s.split(":", 1)
    kind = kind.strip().lower()
    if kind not in KINDS:
        return None, "step kind %r is not one of %s" % (kind, ", ".join(KINDS))
    if kind == "reload":
        if arg.strip():
            return None, "reload takes no argument"
        return {"kind": kind, "text": s}, None
    if kind == "wait":
        if not arg.strip().isdigit():
            return None, "wait needs whole milliseconds, got %r" % arg
        return {"kind": kind, "ms": int(arg), "text": s}, None
    if kind in ("click", "check", "expect-gone", "expect-focus"):
        if not arg.strip():
            return None, "%s needs a selector" % kind
        return {"kind": kind, "sel": arg.strip(), "text": s}, None
    if kind == "expect-count":
        if "=" not in arg or not arg.rsplit("=", 1)[1].strip().isdigit() or not arg.rsplit("=", 1)[0].strip():
            return None, "expect-count needs SELECTOR=N with a whole number, got %r" % arg
        sel, n = arg.rsplit("=", 1)
        return {"kind": kind, "sel": sel.strip(), "n": int(n), "text": s}, None
    if kind == "expect-attr":
        at = max((i for i, ch in enumerate(arg) if ch == "@" and "=" in arg[i:] and "]" not in arg[i:arg.index("=", i)]), default=-1)
        if at < 1:
            return None, "expect-attr needs SELECTOR@ATTR=VALUE, got %r" % arg
        sel, rest = arg[:at], arg[at + 1:]
        attr, val = rest.split("=", 1)
        return {"kind": kind, "sel": sel.strip(), "attr": attr.strip(), "value": val, "text": s}, None
    sel, val = split_selector(arg)
    if sel is None:
        return None, "%s needs SELECTOR=VALUE, got %r" % (kind, arg)
    if not sel.strip():
        return None, "%s needs a selector" % kind
    return {"kind": kind, "sel": sel.strip(), "value": val, "text": s}, None


def make_gate(own_origin, blocked):
    """A route handler that lets through the page's own origin and local schemes and aborts the rest."""
    def gate(route):
        u = route.request.url
        if u.startswith(("file:", "data:", "blob:", "about:")) or (own_origin and u.startswith(own_origin + "/")):
            route.continue_()
        else:
            blocked.append(u[:120])
            route.abort()
    return gate


def run_steps(get_target, page, steps):
    """get_target() returns the Page or Frame to act on. Returns a list of {step, ok, detail}."""
    out = []
    target = get_target()
    for st in steps:
        ok, detail = True, ""
        try:
            if st["kind"] == "wait":
                page.wait_for_timeout(st["ms"])
            elif st["kind"] == "reload":
                page.reload(timeout=10000)
                page.wait_for_timeout(400)
                target = get_target()
                if target is None:
                    raise RuntimeError("the page did not come back after the reload")
            elif st["kind"] == "click":
                target.locator(st["sel"]).first.click(timeout=3000)
            elif st["kind"] == "check":
                target.locator(st["sel"]).first.check(timeout=3000)
            elif st["kind"] == "select":
                if target.locator(st["sel"]).count() == 0:
                    raise RuntimeError("nothing matches the selector")
                loc = target.locator(st["sel"]).first
                opts = loc.evaluate("(e, v) => e.tagName === 'SELECT' ? [...e.options].filter(o => o.value === v || o.label.trim() === v).map(o => ({value: o.value, disabled: o.disabled})) : null", st["value"], timeout=3000)
                if opts is None:
                    raise RuntimeError("the element is not a <select>")
                if not opts:
                    raise RuntimeError("no option has the value or label %r" % st["value"])
                if all(o["disabled"] for o in opts):
                    raise RuntimeError("the option %r is disabled" % st["value"])
                loc.select_option(value=next(o["value"] for o in opts if not o["disabled"]), timeout=3000)
            elif st["kind"] == "fill":
                loc = target.locator(st["sel"]).first
                loc.fill(st["value"], timeout=3000)
                loc.blur()
            elif st["kind"] == "press":
                target.locator(st["sel"]).first.press(st["value"], timeout=3000)
            elif st["kind"] in ("expect", "expect-attr", "expect-count", "expect-gone", "expect-focus"):
                waited = 0
                while True:
                    page.wait_for_timeout(120)
                    waited += 120
                    loc = target.locator(st["sel"])
                    if st["kind"] == "expect":
                        got = loc.first.evaluate("e => (e.value !== undefined && e.value !== null && typeof e.value === 'string' && e.tagName !== 'BUTTON' ? e.value : e.textContent) || ''", timeout=3000) if loc.count() else None
                        ok = got is not None and st["value"] in got
                        detail = "" if ok else ("nothing matches the selector" if got is None else "found %r" % got.strip()[:60])
                    elif st["kind"] == "expect-attr":
                        got = loc.first.get_attribute(st["attr"], timeout=3000) if loc.count() else None
                        ok = got == st["value"]
                        detail = "" if ok else "found %r" % got
                    elif st["kind"] == "expect-focus":
                        where = target.evaluate("s => { const a = document.activeElement; if (!a || a === document.body) return 'nothing'; return a.matches(s) ? '' : (a.id ? '#' + a.id : a.tagName.toLowerCase()); }", st["sel"])
                        ok = where == ""
                        detail = "" if ok else "focus is on %s" % where
                    else:
                        n = loc.count()
                        want = st["n"] if st["kind"] == "expect-count" else 0
                        ok = n == want
                        detail = "" if ok else "found %d, expected %d" % (n, want)
                    if ok or waited >= RETRY_MS:
                        break
        except Exception as e:  # noqa: BLE001
            ok, detail = False, str(e).split("\n")[0][:100]
        out.append({"step": st["text"], "ok": ok, "detail": detail})
    return out


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    flags, opts, steps_raw, args, it = set(), {}, [], [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None:
                print("delivery_check: %s needs a value" % a, file=sys.stderr)
                return 2
            if a == "--step":
                steps_raw.append(v)
            else:
                opts[a] = v
        elif a.startswith("--"):
            print("delivery_check: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if "--version" in flags:
        print(VERSION)
        return 0
    if len(args) != 1:
        print(__doc__)
        return 2
    served = args[0].lower().startswith(("http://", "https://"))
    page_path = Path(args[0])
    if not served and not page_path.is_file():
        print("delivery_check: cannot read " + args[0], file=sys.stderr)
        return 2
    if "--steps" in opts:
        try:
            lines = Path(opts["--steps"]).read_bytes().decode("utf-8-sig").splitlines()
        except (OSError, UnicodeDecodeError) as e:
            print("delivery_check: cannot read steps file %s (%s)" % (opts["--steps"], str(e)[:60]), file=sys.stderr)
            return 2
        steps_raw = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")] + steps_raw
    steps = []
    for s in steps_raw:
        st, err = parse_step(s)
        if err:
            print("delivery_check: " + err, file=sys.stderr)
            return 2
        steps.append(st)
    try:
        width, height = int(opts.get("--width", "1100")), int(opts.get("--height", "800"))
        if width <= 0 or height <= 0:
            raise ValueError
    except ValueError:
        print("delivery_check: --width and --height need positive whole numbers", file=sys.stderr)
        return 2
    sandbox = " ".join(opts.get("--sandbox", "allow-scripts").split())
    bad_tokens = [t for t in sandbox.split() if not t.startswith("allow-")]
    if bad_tokens:
        print("delivery_check: sandbox tokens start with allow-, got %r" % bad_tokens[0], file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 4

    uri = args[0] if served else page_path.resolve().as_uri()
    shown = args[0] if served else page_path.name
    res = {"page": args[0], "sandbox": sandbox, "plain": {}, "framed": {}}
    blocked_outside = []
    with sync_playwright() as p, tempfile.TemporaryDirectory() as td:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e)[:120])
            return 4
        wrapper = Path(td) / "frame.html"
        wrapper.write_text('<!doctype html><html lang="en"><title>frame</title><body style="margin:0">'
                           '<iframe id="f" sandbox="%s" src="%s" style="border:0;width:100vw;height:100vh"></iframe></body></html>' % (sandbox, uri), encoding="utf-8")
        for mode in (("plain",) if "--tab-only" in flags else ("plain", "framed")):
            page = browser.new_page(viewport={"width": width, "height": height},
                                    reduced_motion="reduce" if "--reduced-motion" in flags else "no-preference")
            if "--block-outside" in flags:
                page.route("**/*", make_gate("/".join(uri.split("/", 3)[:3]) if served else None, blocked_outside))
            logs = []
            page.on("console", lambda m, logs=logs: logs.append(m.text[:200]) if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e, logs=logs: logs.append("pageerror: " + str(e)[:200]))
            answered = set()
            page.on("response", lambda r, answered=answered: answered.add((r.request.method, r.url[:120])))
            page.on("requestfailed", lambda q, logs=logs: logs.append("request failed: %s %s" % (q.method, q.url[:120])))
            try:
                page.goto(uri if mode == "plain" else wrapper.as_uri(), timeout=10000)
            except Exception as e:  # noqa: BLE001
                res[mode] = {"steps": [], "error": "the page did not load (%s)" % str(e).split("\n")[0][:100]}
                page.close()
                continue
            page.wait_for_timeout(400)
            def get_target(page=page, mode=mode):
                if mode == "plain":
                    return page
                frames = [f for f in page.frames if f != page.main_frame]
                return frames[0] if frames else None
            if get_target() is None:
                res[mode] = {"steps": [], "error": "the frame did not load"}
                page.close()
                continue
            if mode == "framed" and any("refused to" in m.lower() and ("frame" in m.lower() or "display" in m.lower()) for m in logs):
                res[mode] = {"steps": [], "error": "the page refuses to be framed (frame-ancestors or X-Frame-Options). "
                             "That is a deliberate choice for a page opened in a tab: run with --tab-only", "refused_framing": True}
                page.close()
                continue
            if mode == "framed" and ("request failed: GET " + uri[:120]) in logs and ("GET", uri[:120]) not in answered:
                res[mode] = {"steps": [], "error": "the page did not load inside the frame"}
                page.close()
                continue
            r = {"steps": run_steps(get_target, page, steps)}
            try:
                r["probe"] = get_target().evaluate(PROBE_JS)
            except Exception as e:  # noqa: BLE001
                r["probe"] = {"error": str(e).split("\n")[0][:120]}
            page.wait_for_timeout(150)
            # Chromium reports an answered request with no body (a 204) as aborted. Those got an answer and are not failures.
            logs = [m for m in logs if not (m.startswith("request failed: ") and tuple(m[len("request failed: "):].split(" ", 1)) in answered)]
            r["blocked_messages"] = [m for m in logs if "sandbox" in m.lower() or "blocked" in m.lower() or m.startswith("request failed")]
            r["errors"] = [m for m in logs if m.startswith("pageerror")]
            res[mode] = r
            page.close()
        browser.close()

    framed, plain = res["framed"], res["plain"]
    f_steps, p_steps = framed.get("steps", []), plain.get("steps", [])
    regress = [f["step"] for f, q in zip(f_steps, p_steps) if q["ok"] and not f["ok"]]
    forms_blocked = [x for x in framed.get("probe", {}).get("forms", []) if not x["submit_event_fired"]]
    res["passes_in_tab_fails_in_frame"] = regress
    res["forms_blocked_in_frame"] = len(forms_blocked)
    failed_framed = [f for f in f_steps if not f["ok"]]
    failed_plain = [q for q in p_steps if not q["ok"]]
    if plain.get("error"):
        print("NOT RUN: %s did not load in a tab%s. %s" % (args[0], " (is the server running?)" if served else "", plain["error"]))
        return 4
    tab_only = "--tab-only" in flags
    if tab_only:
        code = 1 if failed_plain else 0
    else:
        code = 1 if (failed_plain or failed_framed or forms_blocked or framed.get("error")) else 0
    if code == 0 and not steps:
        code = 3   # nothing was exercised: only loading (and the frame probes) ran, so this is partial, never a pass
    RECEIPT.update({"page": args[0], "steps": len(steps),
                    "tab": {"passed": len(p_steps) - len(failed_plain), "failed": [q["step"] for q in failed_plain][:20]},
                    "frame": "not run (--tab-only)" if tab_only else ("refused framing" if framed.get("refused_framing") else
                             {"sandbox": sandbox, "passed": len(f_steps) - len(failed_framed), "failed": [f["step"] for f in failed_framed][:20],
                              "pass_in_tab_fail_in_frame": regress[:20], "forms_blocked": len(forms_blocked), "error": framed.get("error")}),
                    "modes": [m for m in ("--reduced-motion", "--block-outside") if m in flags],
                    "outside_requests_blocked": len(set(blocked_outside)) if "--block-outside" in flags else None})
    if "--json" in flags:
        text = json.dumps(res, indent=1, ensure_ascii=True)
    elif tab_only:
        mode_note = "".join([", reduced motion" if "--reduced-motion" in flags else "", ", outside requests blocked" if "--block-outside" in flags else ""])
        L = ["delivery_check: %s in a tab only (--tab-only: no frame run%s)" % (shown, mode_note)]
        if "--block-outside" in flags:
            L.append("  outside requests blocked: %d%s" % (len(set(blocked_outside)), (" (" + ", ".join(sorted(set(blocked_outside))[:3]) + ")") if blocked_outside else ""))
        for q in p_steps:
            L.append("  %-4s in tab | %s%s" % ("ok" if q["ok"] else "FAIL", q["step"], ("   [" + q["detail"] + "]") if q["detail"] else ""))
        for m in plain.get("errors", [])[:5]:
            L.append("  " + m)
        if not steps:
            L.append("  No steps were given, so no interaction was exercised.")
        L.append("RESULT: %s. %d of %d steps passed in a tab. The sandboxed-frame surface was not exercised." % ({0: "PASS", 1: "FAIL", 3: "PARTIAL"}[code], len(p_steps) - len(failed_plain), len(p_steps)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    else:
        mode_note = "".join([", reduced motion" if "--reduced-motion" in flags else "", ", outside requests blocked" if "--block-outside" in flags else ""])
        L = ['delivery_check: %s in a frame with sandbox="%s"%s' % (shown, sandbox, mode_note)]
        if framed.get("error"):
            L.append("  FRAME ERROR " + framed["error"])
        if plain.get("error"):
            L.append("  TAB ERROR " + plain["error"])
        for f, q in zip(f_steps, p_steps):
            notes = []
            if not f["ok"] and f["detail"]:
                notes.append("frame: " + f["detail"])
            if not q["ok"] and q["detail"]:
                notes.append("tab: " + q["detail"])
            L.append("  %-4s in frame | %-4s in tab | %s%s" % ("ok" if f["ok"] else "FAIL", "ok" if q["ok"] else "FAIL", f["step"], ("   [" + "; ".join(notes) + "]") if notes else ""))
        if framed.get("refused_framing"):
            for q in p_steps:
                L.append("  %-4s in tab | %s%s" % ("ok" if q["ok"] else "FAIL", q["step"], ("   [" + q["detail"] + "]") if q["detail"] else ""))
        pr = framed.get("probe", {})
        L.append("  storage in frame: %s" % pr.get("storage", pr.get("error", "unknown")))
        for x in pr.get("forms", []):
            L.append("  form %s: submit event %s in frame" % (x["id"] or "#%d" % x["index"], "fired" if x["submit_event_fired"] else "DID NOT FIRE (needs allow-forms)"))
        for m in framed.get("blocked_messages", [])[:5]:
            L.append("  browser said: " + m)
        for m in framed.get("errors", [])[:5]:
            L.append("  " + m)
        if regress:
            L.append("  %d step(s) pass in a tab and fail in the frame: a delivery failure a local browser test would miss, if the page is delivered in a sandboxed frame." % len(regress))
        if failed_plain:
            L.append("  %d step(s) fail in a plain tab as well: these are defects in the page or its server, not delivery failures." % len(failed_plain))
        if not steps:
            L.append("  No steps were given, so no interaction was exercised. Only the probes ran.")
        L.append("RESULT: %s. This is a local stand-in for a host frame, not the host." % {0: "PASS", 1: "FAIL", 3: "PARTIAL (no steps)"}[code])
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return code

# ---- forge result contract (references/results.md) --------------------------------------------------------------
# Every check prints one RECEIPT line on stderr before it exits, whatever happened, and writes it to --receipt FILE
# when given. status: completed (0), failed (1), usage_error (2), partial (3: an applicable check did not run or
# coverage is incomplete), runner_error (4: the tool could not do its job). Help and --version print no receipt.
# If --receipt FILE cannot be written, the product result is kept as product_status/product_exit and the run as a
# whole is a runner_error (exit 4): a result nobody can read back is not delivered.
STATUS_BY_EXIT = {0: "completed", 1: "failed", 2: "usage_error", 3: "partial", 4: "runner_error"}
RECEIPT = {}


def _contract(tool, main, argv):
    import json as _json
    argv = list(argv)
    path = None

    def emit(code, extra=None):
        rec = {"tool": tool, "version": VERSION, "status": STATUS_BY_EXIT.get(code, "runner_error"), "exit": code}
        rec.update(RECEIPT)
        if extra:
            rec.update(extra)
        if path:
            try:
                pathlib.Path(path).write_text(_json.dumps(rec, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            except OSError as e:
                rec.update({"product_status": rec["status"], "product_exit": code, "status": "runner_error", "exit": 4,
                            "receipt_error": "could not write %s: %s" % (path, e)})
                code = 4
        print("RECEIPT " + _json.dumps(rec, ensure_ascii=False, default=str), file=sys.stderr)
        return code

    if "--receipt" in argv:
        i = argv.index("--receipt")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            print(tool + ": --receipt needs a file path", file=sys.stderr)
            return emit(2, {"error": "--receipt needs a file path"})
        path = argv[i + 1]
        del argv[i:i + 2]
        sys.argv = [sys.argv[0]] + argv
    if any(a in ("-h", "--help", "--version") for a in argv):
        try:
            return main(argv) or 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 0
    try:
        code = main(argv)
        code = 0 if code is None else code
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 2)
    except BaseException as e:  # noqa: BLE001  any crash is a runner error, never a pass or a product failure
        RECEIPT.setdefault("error", repr(e)[:400])
        print("runner error: %r" % (e,), file=sys.stderr)
        code = 4
    return emit(code)


if __name__ == "__main__":
    sys.exit(_contract("delivery_check", main, sys.argv[1:]))
