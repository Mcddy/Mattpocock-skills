#!/usr/bin/env python3
"""Run a list of HTTP steps against a running back end and check each answer. Standard library only.

Usage:
  python api_check.py BASE_URL STEPS.json [--start "COMMAND"] [--ready /api/health] [--json] [--version]

BASE_URL    for example http://127.0.0.1:8765  (http or https, no path)
STEPS.json  a JSON list of steps (see below)
--start     a command that starts the server. The script runs it without a shell, waits for --ready
            to answer, runs the steps and stops the server at the end. It is needed for "restart"
            steps, which stop and start the server to prove data survives.
--ready     a path that answers 200 when the server is up. Default /api/health.

Why this exists: a back end is not checked by reading its code or by the page appearing to work.
It is checked by sending it the requests that should fail as well as the ones that should succeed,
and by restarting it. This runs those and prints what came back.

A step is an object:
  {"name": "create",                       shown in the report
   "method": "POST", "path": "/api/items", path may use {saved} values
   "headers": {"Idempotency-Key": "k1"},
   "json": {...}                            or "raw": "text sent as the body, as is"
   "expect": {"status": 201,
              "json": {"qty": 5, "error.code": "invalid", "items": {"$len": 2},
                       "error.message": {"$contains": "stock"}, "id": {"$exists": true}},
              "headers": {"Idempotent-Replay": "true"}},
   "save": {"id": "id", "rid": "header:X-Request-Id"}}
                                            keep a value from the answer (or a header) for later steps
Saved values fill "{name}" in paths, header values, "raw" bodies and "json" bodies. In a json body a
string that is exactly "{name}" becomes the saved value with its type (a number stays a number).
Operators in expect.json: $exists, $absent, $len, $contains, $not_contains, $gte, $lte.
Keys are dotted paths ("error.fields.name"). A key whose names contain dots is written as a path
starting with "/", JSON-pointer style: "/error/fields/dogs.0.name" (~1 for "/", ~0 for "~").
Header expectations: a plain string must be contained in the header; or use {"$exists": true},
{"$absent": true} or {"$not_contains": "text"}.
Other step kinds:
  {"restart": true}                         stop and start the server (needs --start)
  {"name": ..., "parallel": 20, ...request..., "expect": {"status_counts": {"200": 10, "409": 10}}}
                                            send the same request N times at once

With --start, the script refuses to run if something already answers at BASE_URL, and after every
start checks that the process it launched is still running once the server answers. Otherwise a stale server can hold the
port, the new one fails to bind, and a restart step "passes" without restarting anything.

Limits. This checks the answers a server gives to the requests you list. It does not find requests
you did not think of, measure load, or test security beyond what the steps ask. Run it against a
throwaway data file: the steps create and delete data.

Exit codes: 0 every step passed. 1 a step failed. 2 bad arguments or steps file.
3 partial: some steps did not run (a restart step was given without --start); the report says NOT RUN for
those and nothing should be read as a pass. 4 runner error: the server did not start.
A RECEIPT line on stderr states the result (references/results.md).
"""
import json
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
import pathlib
from urllib.parse import urlparse

FLAGS = {"--json", "--version"}
VERSION = "forge 3.3.2"
VALUES = {"--start", "--ready"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
MISSING = object()


def dig(data, path):
    cur = data
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path[1:].split("/")] if path.startswith("/") else path.split(".")
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return MISSING
    return cur


def send(base, method, path, headers, body):
    req = urllib.request.Request(base + path, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, str(v))
    if body is not None and not any(k.lower() == "content-type" for k in (headers or {})):
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers.items()), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read()
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, {}, str(getattr(e, "reason", e)).encode("utf-8", "replace")


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_value(got, want):
    if isinstance(want, dict) and len(want) == 1 and next(iter(want)).startswith("$"):
        op, arg = next(iter(want.items()))
        if op == "$exists":
            return (got is not MISSING) == bool(arg), "exists" if got is not MISSING else "missing"
        if op == "$absent":
            return (got is MISSING) == bool(arg), "missing" if got is MISSING else "present: " + repr(got)[:50]
        if got is MISSING:
            return False, "missing"
        if op == "$len":
            return hasattr(got, "__len__") and len(got) == arg, "length %s" % (len(got) if hasattr(got, "__len__") else "n/a")
        if op == "$contains":
            return isinstance(got, str) and str(arg) in got, repr(got)[:60]
        if op == "$not_contains":
            text = got if isinstance(got, str) else json.dumps(got)
            return str(arg) not in text, repr(got)[:60]
        if op in ("$gte", "$lte"):
            if not (is_number(got) and is_number(arg)):
                return False, repr(got)[:60] + " (not a number)"
            return (got >= arg if op == "$gte" else got <= arg), repr(got)[:60]
        return False, "unknown operator " + op
    if got is MISSING:
        return False, "missing"
    return (got == want and type(got) is type(want)), repr(got)[:60]


def fill(value, saved):
    """Put saved values into strings, lists and dicts. A string that is exactly {name} takes the value's type."""
    if isinstance(value, str):
        for k, v in saved.items():
            token = "{%s}" % k
            if value == token:
                return v
            if token in value:
                value = value.replace(token, v if isinstance(v, str) else json.dumps(v))
        return value
    if isinstance(value, list):
        return [fill(x, saved) for x in value]
    if isinstance(value, dict):
        return {k: fill(v, saved) for k, v in value.items()}
    return value


def check_header(lower, name, want):
    got = lower.get(name.lower())
    if isinstance(want, dict) and len(want) == 1 and next(iter(want)).startswith("$"):
        op, arg = next(iter(want.items()))
        if op == "$exists":
            return (got is not None) == bool(arg), got
        if op == "$absent":
            return (got is None) == bool(arg), got
        if op == "$not_contains":
            return got is None or str(arg) not in got, got
        return False, "unknown operator " + op
    return got is not None and str(want) in got, got


def valid_steps(data):
    if not isinstance(data, list) or not data:
        return "the steps file must hold a non-empty JSON list"
    for i, st in enumerate(data):
        if not isinstance(st, dict):
            return "step %d is not an object" % (i + 1)
        if st.get("restart") is True:
            continue
        if st.get("method") not in METHODS:
            return "step %d needs a method from %s" % (i + 1, ", ".join(sorted(METHODS)))
        if not isinstance(st.get("path"), str) or not st["path"].startswith("/"):
            return "step %d needs a path starting with /" % (i + 1)
        if "json" in st and "raw" in st:
            return "step %d has both json and raw; give one" % (i + 1)
        if "raw" in st and not isinstance(st["raw"], str):
            return "step %d: raw must be text" % (i + 1)
        exp = st.get("expect")
        if not isinstance(exp, dict) or not exp:
            return "step %d needs an expect object: a step that expects nothing checks nothing" % (i + 1)
        if "parallel" in st:
            n = st["parallel"]
            if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 200:
                return "step %d: parallel must be a whole number from 2 to 200" % (i + 1)
            if not isinstance(exp.get("status_counts"), dict):
                return "step %d: a parallel step needs expect.status_counts" % (i + 1)
        elif "status" not in exp or isinstance(exp["status"], bool) or not isinstance(exp["status"], int):
            return "step %d: expect.status must be a whole number" % (i + 1)
        for k in ("headers", "json", "save"):
            holder = st if k == "save" else exp
            if k in holder and not isinstance(holder[k], dict):
                return "step %d: %s must be an object" % (i + 1, k)
    return None


class Server:
    def __init__(self, cmd, base, ready):
        self.cmd, self.base, self.ready, self.proc = cmd, base, ready, None

    def start(self):
        for _ in range(20):                       # a stopped server may take a moment to release the port
            status, _h, _b = send(self.base, "GET", self.ready, {}, None)
            if status is None:
                break
            time.sleep(0.25)
        else:
            return ("something is already answering at %s. Stop it first: otherwise every step, including "
                    "restarts, runs against that process instead of the one this run starts" % self.base)
        try:
            self.proc = subprocess.Popen(self.cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            return "could not start %r (%s)" % (self.cmd[0], e.strerror or e)
        for _ in range(60):
            if self.proc.poll() is not None:
                return ("the server command exited with code %s before it was ready (is the port already held by "
                        "another process?)" % self.proc.returncode)
            status, _h, _b = send(self.base, "GET", self.ready, {}, None)
            if status == 200:
                time.sleep(0.2)
                if self.proc.poll() is not None:
                    return ("a server answered, but the process this run started exited with code %s. "
                            "Another process holds the port" % self.proc.returncode)
                return None
            time.sleep(0.1)
        return "the server did not answer 200 on %s within 6 seconds" % self.ready

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None


def run_step(base, st, saved):
    path = st["path"]
    for k, v in saved.items():
        path = path.replace("{%s}" % k, str(v))
    if "{" in path:
        return False, ["path still has an unfilled value: " + path]
    headers = fill(st.get("headers") or {}, saved)
    body = None
    if "json" in st:
        body = json.dumps(fill(st["json"], saved)).encode("utf-8")
    elif "raw" in st:
        body = fill(st["raw"], saved).encode("utf-8")
    exp = st["expect"]
    if "parallel" in st:
        results, reasons = [], []

        def one():
            status, _h, raw = send(base, st["method"], path, headers, body)
            results.append(status)
            if status is None:
                reasons.append(raw.decode("utf-8", "replace")[:80])
        threads = [threading.Thread(target=one) for _ in range(st["parallel"])]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        counts = {}
        for s in results:
            counts[str(s)] = counts.get(str(s), 0) + 1
        want = {str(k): v for k, v in exp["status_counts"].items()}
        problems = [] if counts == want else ["status counts were %s, expected %s" % (json.dumps(counts, sort_keys=True), json.dumps(want, sort_keys=True))]
        if reasons:
            problems.append("%d request(s) got no answer, for example: %s (a listen backlog that is too small drops connections under parallel load)" % (len(reasons), reasons[0]))
        return counts == want, problems
    status, resp_headers, raw = send(base, st["method"], path, headers, body)
    problems = []
    if status is None:
        return False, ["no answer from the server (%s)" % raw.decode("utf-8", "replace")[:80]]
    if status != exp["status"]:
        problems.append("status %s, expected %s" % (status, exp["status"]))
    data = MISSING
    if raw:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            data = MISSING
    for k, want in (exp.get("json") or {}).items():
        ok, got = check_value(dig(data, k) if data is not MISSING else MISSING, want)
        if not ok:
            problems.append("%s was %s, expected %s" % (k, got, json.dumps(want)))
    lower = {k.lower(): v for k, v in resp_headers.items()}
    for k, want in (exp.get("headers") or {}).items():
        ok, got = check_header(lower, k, want)
        if not ok:
            problems.append("header %s was %r, expected %s" % (k, got, json.dumps(want)))
    for var, k in (st.get("save") or {}).items():
        if k.startswith("header:"):
            v = lower.get(k[7:].lower(), MISSING)
        else:
            v = dig(data, k) if data is not MISSING else MISSING
        if v is MISSING:
            problems.append("could not save %s: %s is not in the answer" % (var, k))
        else:
            saved[var] = v
    return not problems, problems


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip():
                print("api_check: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("api_check: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if "--version" in flags:
        print(VERSION)
        return 0
    if len(args) != 2:
        print(__doc__)
        return 2
    base = args[0].rstrip("/")
    u = urlparse(base)
    if u.scheme not in ("http", "https") or not u.netloc or u.path not in ("", "/") or u.query:
        print("api_check: BASE_URL must look like http://127.0.0.1:8765 with no path", file=sys.stderr)
        return 2
    ready = opts.get("--ready", "/api/health")
    if not ready.startswith("/"):
        print("api_check: --ready needs a path starting with /", file=sys.stderr)
        return 2
    try:
        steps = json.loads(Path(args[1]).read_bytes().decode("utf-8-sig"))
    except OSError as e:
        print("api_check: cannot read %s: %s" % (args[1], e.strerror or e), file=sys.stderr)
        return 2
    except (UnicodeDecodeError, ValueError) as e:
        print("api_check: %s is not valid UTF-8 JSON (%s)" % (args[1], str(e)[:60]), file=sys.stderr)
        return 2
    err = valid_steps(steps)
    if err:
        print("api_check: " + err, file=sys.stderr)
        return 2
    server = None
    if "--start" in opts:
        try:
            cmd = shlex.split(opts["--start"])
        except ValueError as e:
            print("api_check: --start could not be parsed (%s)" % e, file=sys.stderr)
            return 2
        if not cmd:
            print("api_check: --start needs a command", file=sys.stderr)
            return 2
        server = Server(cmd, base, ready)
        err = server.start()
        if err:
            server.stop()
            print("NOT RUN: " + err)
            RECEIPT.update({"base": base, "steps_total": len(steps), "steps_passed": 0, "error": "server did not start: " + err})
            return 4

    rows, saved, not_run = [], {}, 0
    try:
        for i, st in enumerate(steps):
            if st.get("restart") is True:
                if not server:
                    rows.append({"n": i + 1, "name": "restart the server", "state": "NOT RUN", "problems": ["needs --start"]})
                    not_run += 1
                    continue
                server.stop()
                err = server.start()
                rows.append({"n": i + 1, "name": "restart the server", "state": "FAIL" if err else "ok", "problems": [err] if err else []})
                if err:
                    break
                continue
            ok, problems = run_step(base, st, saved)
            rows.append({"n": i + 1, "name": st.get("name") or "%s %s" % (st["method"], st["path"]), "state": "ok" if ok else "FAIL", "problems": problems})
    finally:
        if server:
            server.stop()

    failed = [r for r in rows if r["state"] == "FAIL"]
    skipped = len(steps) - len(rows)
    code = 1 if failed else (3 if (not_run or skipped) else 0)
    RECEIPT.update({"base": base, "steps_total": len(steps), "steps_passed": sum(1 for r in rows if r["state"] == "ok"),
                    "steps_failed": [r["n"] for r in failed], "steps_not_run": [r["n"] for r in rows if r["state"] == "NOT RUN"],
                    "steps_not_reached": list(range(len(rows) + 1, len(steps) + 1)), "server_started_by_check": bool(server)})
    if "--json" in flags:
        text = json.dumps({"base": base, "steps": rows, "failed": len(failed), "not_run": not_run + skipped}, indent=1, ensure_ascii=True)
    else:
        L = ["api_check: %d step(s) against %s" % (len(steps), base)]
        for r in rows:
            L.append("  %-7s %2d  %s" % (r["state"], r["n"], r["name"]))
            for p in r["problems"]:
                L.append("              " + p)
        if skipped:
            L.append("  %d later step(s) were not reached." % skipped)
        ok_n = sum(1 for r in rows if r["state"] == "ok")
        if code == 0:
            L.append("RESULT: PASS. %d of %d steps gave the expected answer." % (ok_n, len(steps)))
        elif code == 1:
            L.append("RESULT: FAIL. %d of %d steps gave the expected answer; %d did not." % (ok_n, len(steps), len(failed)))
        else:
            L.append("RESULT: NOT RUN in full. %d of %d steps ran and passed; %d did not run. Do not report this as a pass." % (ok_n, len(steps), not_run + skipped))
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
    sys.exit(_contract("api_check", main, sys.argv[1:]))
