#!/usr/bin/env python3
"""Run the verifications named in the stock-count threat model against a running copy of the app.

Usage:
  python verify_stock_count.py --app DIR --port N --scratch DIR [--only V1,V3] [--json]

  --app      the folder holding the app's server.py and index.html. It is only read and run.
  --port     a free local port for the test server
  --scratch  an existing folder for the throwaway database and the captured server log. New files
             are created in it per run and left there; nothing is deleted.

What it does: starts "python server.py --port N --db SCRATCH/verify-<time>.db" on 127.0.0.1, waits
for it to answer, runs each check below with ordinary HTTP requests (and one headless browser
visit), stops the server, and prints one line per check with what was expected and what was seen.
It talks only to the server it started, on loopback, with data it created itself.

The checks. Each is the test for one mitigation in threat-model.json, and each refusal is run
beside its valid neighbour so that a server which refuses everything cannot pass:
  V1  a body one byte over the 64 kB limit is refused with 413; a body exactly at the limit is stored
  V2  percent, underscore and quote characters typed into search are matched as plain text
  V3  an item name that looks like markup is shown as text in the page (needs Playwright)
  V4  a count sent as text, true, a fraction or a negative is refused; a whole number is stored;
      an adjustment that would go below zero is refused and the neighbouring one to zero is applied
  V5  error answers carry the fixed shape and no stack trace, file path or query text
  V6  a field the API does not know is refused; the same request without it is stored
  V7  a request with no credential is refused (mitigation NOT BUILT: this is expected to fail)
  V8  a request from another origin is not given a wildcard allow header (NOT BUILT: expected to fail)
  V9  a burst of requests meets a limit (NOT BUILT: expected to fail)
  V10 request text reaches the server's log with control characters removed (the escape byte, 27)
  B1  baseline, not part of the exposed model: as shipped, the server answers on 127.0.0.1 and
      refuses a connection on the machine's other address. Not run if the machine has no other address
A check that fails is reported as fail. Nothing is retried and nothing is softened.

What it cannot tell: anything about a network it did not run on, load, timing attacks, or faults
in the Python standard library server itself. It is ten tests, not a penetration test.

Exit codes: 0 every check that ran passed. 1 at least one check failed. 2 bad arguments.
3 the server could not be started or did not answer (prints NOT RUN).
"""
import datetime as dt
import http.client
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

LIMIT = 64 * 1024
MARKUP_NAME = '<img src=x onerror="window.__tm_marker=1"><b>bold</b>'
MARKUP_QUERY = '<img src=x onerror="window.__tm_marker=2">'
ALL = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10", "B1"]
VALUES = {"--app", "--port", "--scratch", "--only"}
FLAGS = {"--json"}


class Client:
    def __init__(self, port, log_path=None):
        self.port, self.log_path = port, log_path

    def call(self, method, path, body=None, headers=None, raw=None):
        """One request. body is sent as JSON; raw is sent as bytes. Returns (status, headers, parsed-or-None, text)."""
        h = dict(headers or {})
        data = None
        if raw is not None:
            data = raw
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
        if data is not None:
            h.setdefault("Content-Type", "application/json")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=data, headers=h)
            res = conn.getresponse()
            text = res.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(text) if text else None
            except ValueError:
                parsed = None
            return res.status, {k.lower(): v for k, v in res.getheaders()}, parsed, text
        finally:
            conn.close()

    def declare_length(self, path, length):
        """Send only the headers of a POST that declares a body of the given length, and read the answer.
        The server decides from the declared length, so the body itself is never needed."""
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            s.sendall(("POST %s HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % (path, length)).encode("ascii"))
            s.settimeout(3)
            chunks = []
            try:
                while True:
                    part = s.recv(4096)
                    if not part:
                        break
                    chunks.append(part)
            except socket.timeout:
                pass
            head = b"".join(chunks).decode("utf-8", "replace")
            first = head.split("\r\n", 1)[0].split(" ")
            return (int(first[1]) if len(first) > 1 and first[1].isdigit() else None), head
        finally:
            s.close()


def v10_log_scrubbed(c):
    esc = bytes([27])
    s = socket.create_connection(("127.0.0.1", c.port), timeout=10)
    try:
        s.sendall(b"GET /api/health?probe=tm-log-" + esc + b"[31m-end HTTP/1.1" + bytes([13, 10]) + b"Host: 127.0.0.1" + bytes([13, 10, 13, 10]))
        s.settimeout(3)
        try:
            while s.recv(4096):
                pass
        except socket.timeout:
            pass
    finally:
        s.close()
    time.sleep(0.3)
    log = Path(c.log_path).read_bytes() if c.log_path else b""
    reached = b"tm-log-" in log
    raw = esc in log
    return reached and not raw, "the probe request appears in the log and the log holds no escape byte", \
        "probe line in the log: %s; escape bytes in the log: %d" % ("yes" if reached else "no", log.count(esc))


def b1_loopback_only(c):
    expected = "an answer on 127.0.0.1 and a refused connection on the machine's other address"
    try:
        others = sorted(a for a in socket.gethostbyname_ex(socket.gethostname())[2] if not a.startswith("127."))
    except OSError:
        others = []
    if not others:
        # Ask the routing table which local address would be used to leave the machine. Connecting a
        # datagram socket sends nothing. 192.0.2.1 is a documentation address (RFC 5737).
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 9))
            if not probe.getsockname()[0].startswith("127."):
                others = [probe.getsockname()[0]]
        except OSError:
            pass
        finally:
            probe.close()
    if not others:
        return None, expected, "NOT RUN: this machine reports no address other than loopback"
    local = c.call("GET", "/api/health")[0]
    try:
        socket.create_connection((others[0], c.port), timeout=3).close()
        outside = "accepted"
    except ConnectionRefusedError:
        outside = "refused"
    except OSError as e:
        outside = "no connection (%s)" % (e.strerror or type(e).__name__)
    return local == 200 and outside == "refused", expected, "127.0.0.1 -> %s; the machine's other address -> %s" % (local, outside)


def names(parsed):
    return sorted(i["name"] for i in (parsed or {}).get("items", []))


def error_code(parsed):
    return ((parsed or {}).get("error") or {}).get("code")


def v1_body_limit(c):
    over, _ = c.declare_length("/api/items", LIMIT + 1)
    item = json.dumps({"sku": "PAD-AT-LIMIT", "name": "padded to the limit", "qty": 1}).encode("ascii")
    at_status, _, at, _ = c.call("POST", "/api/items", raw=item + b" " * (LIMIT - len(item)))
    ok = over == 413 and at_status == 201
    return ok, "413 for %d bytes; 201 for %d bytes" % (LIMIT + 1, LIMIT), "%s for %d bytes; %s for %d bytes" % ("no answer" if over is None else over, LIMIT + 1, at_status, LIMIT)


def v2_search_literal(c):
    made = []
    for sku, name in (("S-BOLT", "M8 bolt"), ("S-MIX", "50% mix"), ("S-TAG", "snake_case tag")):
        made.append(c.call("POST", "/api/items", {"sku": sku, "name": name, "qty": 3})[0])
    seen = {}
    for label, q in (("percent", "%25"), ("underscore", "_"), ("quote", "%27"), ("plain", "bolt"), ("clause", "%27%20OR%20%271%27%3D%271")):
        status, _, parsed, _ = c.call("GET", "/api/items?q=" + q)
        seen[label] = (status, names(parsed))
    total = (c.call("GET", "/api/items")[2] or {}).get("total")
    want = {"percent": (200, ["50% mix"]), "underscore": (200, ["snake_case tag"]), "quote": (200, []), "plain": (200, ["M8 bolt"]), "clause": (200, [])}
    ok = made == [201, 201, 201] and seen == want and isinstance(total, int) and total >= 3
    return ok, "percent finds only '50% mix'; underscore only 'snake_case tag'; a quote and a quoted clause find nothing; 'bolt' finds 'M8 bolt'", \
        "; ".join("%s -> %s %s" % (k, seen[k][0], seen[k][1]) for k in ("percent", "underscore", "quote", "clause", "plain")) + "; total %s" % total


def v3_markup_as_text(c):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "the name is shown as text and creates no element", "NOT RUN: the Python playwright package is not installed"
    made = c.call("POST", "/api/items", {"sku": "MARKUP-1", "name": MARKUP_NAME, "qty": 2})[0]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            dialogs = []
            page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
            page.goto("http://127.0.0.1:%d/" % c.port)
            page.wait_for_selector('[data-sku="MARKUP-1"]', timeout=8000)
            shown = page.eval_on_selector('[data-sku="MARKUP-1"] .name', "n => n.textContent")
            page.click('[data-sku="MARKUP-1"] [data-act="plus"]')
            page.wait_for_function("document.querySelector('[data-qty=\"MARKUP-1\"]').textContent === '3'", timeout=8000)
            page.click('[data-sku="MARKUP-1"] [data-act="remove"]')
            page.wait_for_selector('[data-sku="MARKUP-1"] .confirm', timeout=8000)
            page.click('[data-sku="MARKUP-1"] [data-act="keep"]')
            page.fill("#q", MARKUP_QUERY)
            page.wait_for_selector("#sheet .blank h2", timeout=8000)
            heading = page.eval_on_selector("#sheet .blank h2", "n => n.textContent")
            made_elements = page.evaluate("document.querySelectorAll('#sheet img, #sheet b, #sheet script').length")
            marker = page.evaluate("typeof window.__tm_marker")
            browser.close()
    except Exception as e:  # noqa: BLE001
        return None, "the name is shown as text and creates no element", "NOT RUN: the browser check could not finish (%s)" % str(e).splitlines()[0][:120]
    ok = made == 201 and shown == MARKUP_NAME and MARKUP_QUERY in heading and made_elements == 0 and marker == "undefined" and not dialogs
    return ok, "name and search text appear character for character; 0 img, b or script elements made from them; marker undefined; no dialog", \
        "name shown exactly: %s; search text shown exactly: %s; elements made: %d; marker: %s; dialogs: %d" % (
            shown == MARKUP_NAME, MARKUP_QUERY in heading, made_elements, marker, len(dialogs))


def v4_no_coercion(c):
    seen = []
    for n, qty in enumerate(("7", True, 3.5, -1)):
        status, _, parsed, _ = c.call("POST", "/api/items", {"sku": "COERCE-%d" % n, "name": "coercion probe", "qty": qty})
        seen.append((status, "qty" in ((parsed or {}).get("error") or {}).get("fields", {})))
    good, _, created, _ = c.call("POST", "/api/items", {"sku": "COERCE-OK", "name": "whole number", "qty": 7})
    item = (created or {}).get("id")
    below, _, below_body, _ = c.call("POST", "/api/items/%s/adjust" % item, {"delta": -8})
    still = next((i["qty"] for i in (c.call("GET", "/api/items?q=COERCE-OK")[2] or {}).get("items", [])), None)
    zero, _, zero_body, _ = c.call("POST", "/api/items/%s/adjust" % item, {"delta": -7})
    ok = seen == [(422, True)] * 4 and good == 201 and below == 409 and error_code(below_body) == "would_go_negative" and still == 7 \
        and zero == 200 and (zero_body or {}).get("qty") == 0
    return ok, "422 naming qty for \"7\", true, 3.5 and -1; 201 for 7; 409 for 7 minus 8 with the count still 7; 200 and a count of 0 for 7 minus 7", \
        "probes -> %s; whole number -> %s; minus 8 -> %s %s, count then %s; minus 7 -> %s, count %s" % (
            [s for s, _ in seen], good, below, error_code(below_body), still, zero, (zero_body or {}).get("qty"))


def v5_error_shape(c):
    seen, leaks = [], []
    probes = (("POST", "/api/items", b"{not json"), ("POST", "/api/items", b"[1, 2]"), ("GET", "/api/nothing-here", None),
              ("PUT", "/api/items", b"{}"), ("POST", "/api/items/999999/adjust", b'{"delta": 1}'))
    for method, path, raw in probes:
        status, _, parsed, text = c.call(method, path, raw=raw)
        err = (parsed or {}).get("error") if isinstance(parsed, dict) else None
        shaped = isinstance(err, dict) and set(err) == {"code", "message", "fields"} and set(parsed) == {"error"}
        seen.append((status, shaped))
        for word in ("Traceback", 'File "', ".py", "sqlite", "SELECT", "INSERT"):
            if word in text:
                leaks.append(word)
    ok = seen == [(400, True), (400, True), (404, True), (405, True), (404, True)] and not leaks
    return ok, "400, 400, 404, 405, 404, each with exactly error.code, error.message and error.fields, and no trace, path or query text", \
        "statuses and shape -> %s; leaked words: %s" % (seen, leaks or "none")


def v6_unknown_field(c):
    bad, _, parsed, _ = c.call("POST", "/api/items", {"sku": "EXTRA-1", "name": "extra field", "qty": 1, "admin": True})
    reason = ((parsed or {}).get("error") or {}).get("fields", {}).get("admin")
    good = c.call("POST", "/api/items", {"sku": "EXTRA-1", "name": "extra field", "qty": 1})[0]
    return bad == 422 and reason == "unknown field" and good == 201, "422 naming the unknown field; 201 without it", \
        "with the extra field -> %s (%s); without -> %s" % (bad, reason, good)


def v7_credential_required(c):
    read = c.call("GET", "/api/items")[0]
    write, _, made, _ = c.call("POST", "/api/items", {"sku": "NO-CRED", "name": "created with no credential", "qty": 1})
    return read == 401 and write == 401, "401 for a read and for a write that carry no credential", "read -> %s; write -> %s" % (read, write)


def v8_origin_restricted(c):
    pre = c.call("OPTIONS", "/api/items", headers={"Origin": "http://other.example", "Access-Control-Request-Method": "POST"})
    get = c.call("GET", "/api/items", headers={"Origin": "http://other.example"})
    allow = [pre[1].get("access-control-allow-origin"), get[1].get("access-control-allow-origin")]
    return all(a not in ("*", "http://other.example") for a in allow), "no allow-origin header for an origin that is not the page's own", \
        "allow-origin on the preflight: %s; on the read: %s" % (allow[0], allow[1])


def v9_request_limit(c):
    statuses = [c.call("GET", "/api/health")[0] for _ in range(60)]
    limited = sum(1 for s in statuses if s == 429)
    return limited > 0, "at least one 429 within 60 requests sent one after another", "%d of 60 answered 429; %d answered 200" % (limited, statuses.count(200))


CHECKS = {"V1": ("body size limit", v1_body_limit), "V2": ("search text is literal", v2_search_literal), "V3": ("markup shown as text", v3_markup_as_text),
          "V4": ("no silent coercion", v4_no_coercion), "V5": ("error answers leak nothing", v5_error_shape), "V6": ("unknown field refused", v6_unknown_field),
          "V7": ("credential required", v7_credential_required), "V8": ("origin restricted", v8_origin_restricted), "V9": ("request limit", v9_request_limit),
          "V10": ("log lines are scrubbed", v10_log_scrubbed), "B1": ("baseline: loopback only", b1_loopback_only)}


def port_free(port):
    """True when nothing accepts a connection on the port."""
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
        return False
    except OSError:
        return True


def main(argv):
    opts, flags, it = {}, set(), iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("verify_stock_count: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        else:
            print("verify_stock_count: unknown argument " + a, file=sys.stderr)
            return 2
    for need in ("--app", "--port", "--scratch"):
        if need not in opts:
            print("verify_stock_count: %s is required" % need, file=sys.stderr)
            return 2
    if not opts["--port"].isdigit() or not 1024 <= int(opts["--port"]) <= 65535:
        print("verify_stock_count: --port needs a number from 1024 to 65535", file=sys.stderr)
        return 2
    port, app, scratch = int(opts["--port"]), Path(opts["--app"]), Path(opts["--scratch"])
    if not (app / "server.py").is_file() or not scratch.is_dir():
        print("verify_stock_count: --app must hold server.py and --scratch must be an existing folder", file=sys.stderr)
        return 2
    only = [x.strip() for x in opts.get("--only", ",".join(ALL)).split(",")]
    if any(x not in CHECKS for x in only):
        print("verify_stock_count: --only takes ids from " + ",".join(ALL), file=sys.stderr)
        return 2
    if not port_free(port):
        print("NOT RUN: port %d is already in use" % port)
        return 3
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    db, log_path = scratch / ("verify-%s.db" % stamp), scratch / ("verify-%s.server-log.txt" % stamp)
    log_file = open(log_path, "wb")
    proc = subprocess.Popen([sys.executable, "-B", str(app / "server.py"), "--port", str(port), "--db", str(db)],
                            stdout=subprocess.DEVNULL, stderr=log_file)
    c, up = Client(port, log_path), False
    try:
        for _ in range(50):
            time.sleep(0.1)
            try:
                up = c.call("GET", "/api/health")[0] == 200
            except OSError:
                up = False
            if up or proc.poll() is not None:
                break
        if not up:
            print("NOT RUN: the server did not answer on port %d" % port)
            return 3
        results = []
        for vid in only:
            name, fn = CHECKS[vid]
            try:
                ok, expected, observed = fn(c)
            except OSError as e:
                ok, expected, observed = False, "an answer from the server", "the request failed: %s" % e
            results.append({"id": vid, "name": name, "result": "not_run" if ok is None else ("pass" if ok else "fail"), "expected": expected, "observed": observed})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()
    stopped = proc.poll() is not None and port_free(port)
    out = {"ran_on": dt.date.today().isoformat(), "address": "127.0.0.1:%d" % port, "server_stopped": stopped, "checks": results}
    if "--json" in flags:
        text = json.dumps(out, indent=1, ensure_ascii=True)
    else:
        L = ["verify_stock_count: %s on %s" % (out["ran_on"], out["address"])]
        for r in results:
            L.append("  %-7s %s  %s" % (r["result"].upper().replace("_", " "), r["id"], r["name"]))
            L.append("          expected: " + r["expected"])
            L.append("          observed: " + r["observed"])
        n = {k: sum(1 for r in results if r["result"] == k) for k in ("pass", "fail", "not_run")}
        L.append("RESULT: %d pass, %d fail, %d not run, of %d. Server stopped: %s." % (n["pass"], n["fail"], n["not_run"], len(results), "yes" if stopped else "NO"))
        text = "\n".join(L)
    print(text.encode("ascii", "replace").decode("ascii"))
    return 1 if any(r["result"] == "fail" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
