#!/usr/bin/env python3
"""Stock count: a small full-stack reference slice. Python standard library only.

Run:   python server.py [--port 8765] [--db stock.db]
Open:  http://127.0.0.1:8765/

Why it exists: it is the worked example for the forge skill. One real flow goes all the way through:
the page calls the API, the API enforces the rules, SQLite keeps the result, and a restart shows it
is still there. Everything in it is exercised by the checks beside it. Nothing is here for show.

Before copying a pattern from this file, read "What not to copy" in README.md: unbounded lists, no
request id or catch-all handler, logged search text, no migrations and the wildcard CORS are known
gaps, not patterns.

Ownership. The server owns every rule: what a valid item is, that codes are unique, that a count
cannot go below zero. The page asks; it never decides.

API (JSON in and out):
  GET    /api/items?q=&low=1        list, optional text search and low-stock filter
  POST   /api/items                  create {sku, name, qty, location, low_at}
  POST   /api/items/<id>/adjust      change the count by {delta}; refuses to go below zero
  DELETE /api/items/<id>             remove
  GET    /api/health                 liveness and a database round trip

Errors always have one shape: {"error": {"code": str, "message": str, "fields": {name: reason}}}
  400 bad_json           the body is not JSON, or not an object
  404 not_found          no such route or item
  405 method_not_allowed
  409 duplicate_sku      the item code is taken
  409 would_go_negative  the adjustment would take the count below zero
  409 key_reused         an Idempotency-Key was sent again with a different body
  413 too_large          body over 64 kB
  422 invalid            one or more fields failed validation (see "fields")

Safe retries. POST /api/items accepts an Idempotency-Key header. Sending the same key with the
same body again returns the first result and creates nothing, so a client that times out can retry
a create. The same key with a different body is refused (409 key_reused). Keys are kept for a day.
Adjust is not idempotent, so a client must not blindly retry it.

Frames. The page may be shown inside a sandboxed frame, where its origin is "null". The API answers
cross-origin requests and preflights from any origin and uses no cookies, so that works. That open
setting is for local demonstration only: this server has no login, holds throwaway data and listens
on 127.0.0.1. Do not copy it to an API that holds real data. If you add login, decide the allowed
origins as part of that review; a sandboxed preview is not a reason to widen them.
"""
import hashlib
import json
import re
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
MAX_BODY = 64 * 1024
SKU = re.compile(r"[A-Z0-9][A-Z0-9-]{1,23}")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  qty INTEGER NOT NULL CHECK (qty >= 0),
  location TEXT NOT NULL DEFAULT '',
  low_at INTEGER NOT NULL DEFAULT 0 CHECK (low_at >= 0),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS idempotency (
  key TEXT PRIMARY KEY,
  request_hash TEXT NOT NULL,
  status INTEGER NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
"""


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None):
        super().__init__(message)
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}


def connect(db_path):
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def as_int(v, name, fields, lo=0, hi=1_000_000):
    """Whole numbers only. True, 3.5, "7" and None are all refused: no silent coercion."""
    if isinstance(v, bool) or not isinstance(v, int):
        fields[name] = "must be a whole number"
        return None
    if not lo <= v <= hi:
        fields[name] = "must be between %d and %d" % (lo, hi)
        return None
    return v


def validate_item(body):
    fields = {}
    unknown = sorted(set(body) - {"sku", "name", "qty", "location", "low_at"})
    for k in unknown:
        fields[k] = "unknown field"
    sku = body.get("sku")
    if not isinstance(sku, str) or not SKU.fullmatch(sku):
        fields["sku"] = "2 to 24 characters: capital letters, digits and hyphens, starting with a letter or digit"
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        fields["name"] = "is required"
    elif len(name) > 80:
        fields["name"] = "must be 80 characters or fewer"
    qty = as_int(body.get("qty"), "qty", fields)
    low_at = as_int(body.get("low_at", 0), "low_at", fields)
    loc = body.get("location", "")
    if not isinstance(loc, str) or len(loc) > 40:
        fields["location"] = "must be text of 40 characters or fewer"
    if fields:
        raise ApiError(422, "invalid", "Some fields need fixing.", fields)
    return {"sku": sku, "name": name.strip(), "qty": qty, "location": loc.strip(), "low_at": low_at}


def row(r):
    d = dict(r)
    d["low"] = d["qty"] <= d["low_at"]
    return d


class Handler(BaseHTTPRequestHandler):
    server_version = "StockCount/1"
    db_path = "stock.db"

    def log_message(self, fmt, *args):   # quiet by default; one line per request to stderr
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    # ---- plumbing ----
    def send_json(self, status, payload, extra=None):
        data = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Idempotency-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        if payload is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if data:
            self.wfile.write(data)

    def fail(self, e):
        self.send_json(e.status, {"error": {"code": e.code, "message": e.message, "fields": e.fields}})

    def read_json(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "bad_json", "Content-Length is not a number.")
        if n > MAX_BODY:
            raise ApiError(413, "too_large", "The request body is too large.")
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(400, "bad_json", "The request body is not valid JSON.")
        if not isinstance(body, dict):
            raise ApiError(400, "bad_json", "The request body must be a JSON object.")
        return body

    def route(self, method):
        url = urlparse(self.path)
        parts = [p for p in url.path.split("/") if p]
        try:
            if url.path in ("/", "/index.html") and method == "GET":
                page = (HERE / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(page)
                return
            if parts[:1] != ["api"]:
                raise ApiError(404, "not_found", "No such page.")
            if parts == ["api", "health"]:
                self.need(method, "GET")
                with LOCK, connect(self.db_path) as c:
                    n = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
                return self.send_json(200, {"status": "ok", "items": n})
            if parts == ["api", "items"]:
                self.need(method, "GET", "POST")
                return self.list_items(parse_qs(url.query)) if method == "GET" else self.create_item()
            if len(parts) == 3 and parts[:2] == ["api", "items"]:
                self.need(method, "DELETE")
                return self.delete_item(self.item_id(parts[2]))
            if len(parts) == 4 and parts[:2] == ["api", "items"] and parts[3] == "adjust":
                self.need(method, "POST")
                return self.adjust_item(self.item_id(parts[2]))
            raise ApiError(404, "not_found", "No such route.")
        except ApiError as e:
            self.fail(e)
        except sqlite3.Error:
            self.fail(ApiError(500, "storage", "The data store did not respond. Nothing was changed."))

    def need(self, method, *allowed):
        if method not in allowed:
            raise ApiError(405, "method_not_allowed", "Use %s here." % " or ".join(allowed))

    @staticmethod
    def item_id(text):
        if not text.isdigit() or len(text) > 12:
            raise ApiError(404, "not_found", "No such item.")
        return int(text)

    # ---- the four operations ----
    def list_items(self, q):
        text = (q.get("q", [""])[0] or "").strip()[:60]
        low = q.get("low", ["0"])[0] == "1"
        sql, args = "SELECT * FROM items", []
        where = []
        if text:
            where.append("(sku LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' OR location LIKE ? ESCAPE '\\')")
            like = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            args += [like, like, like]
        if low:
            where.append("qty <= low_at")
        if where:
            sql += " WHERE " + " AND ".join(where)
        with LOCK, connect(self.db_path) as c:
            rows = [row(r) for r in c.execute(sql + " ORDER BY sku", args)]
            total = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        self.send_json(200, {"items": rows, "total": total})

    def create_item(self):
        key = (self.headers.get("Idempotency-Key") or "").strip()[:80]
        item = validate_item(self.read_json())
        with LOCK, connect(self.db_path) as c:
            if key:
                digest = hashlib.sha256(json.dumps(item, sort_keys=True).encode("utf-8")).hexdigest()
                c.execute("DELETE FROM idempotency WHERE created_at < strftime('%Y-%m-%dT%H:%M:%SZ','now','-1 day')")
                seen = c.execute("SELECT request_hash, status, body FROM idempotency WHERE key = ?", (key,)).fetchone()
                if seen and seen["request_hash"] != digest:
                    raise ApiError(409, "key_reused", "This Idempotency-Key was already used for a different item.")
                if seen:
                    return self.send_json(seen["status"], json.loads(seen["body"]), {"Idempotent-Replay": "true"})
            try:
                cur = c.execute("INSERT INTO items (sku, name, qty, location, low_at) VALUES (?,?,?,?,?)",
                                (item["sku"], item["name"], item["qty"], item["location"], item["low_at"]))
            except sqlite3.IntegrityError:
                raise ApiError(409, "duplicate_sku", "Item code %s is already in use." % item["sku"], {"sku": "already in use"})
            created = row(c.execute("SELECT * FROM items WHERE id = ?", (cur.lastrowid,)).fetchone())
            if key:
                c.execute("INSERT INTO idempotency (key, request_hash, status, body) VALUES (?,?,?,?)", (key, digest, 201, json.dumps(created)))
        self.send_json(201, created)

    def adjust_item(self, item_id):
        body = self.read_json()
        fields = {}
        for k in sorted(set(body) - {"delta"}):
            fields[k] = "unknown field"
        delta = as_int(body.get("delta"), "delta", fields, lo=-1_000_000)
        if delta == 0:
            fields["delta"] = "must not be zero"
        if fields:
            raise ApiError(422, "invalid", "Some fields need fixing.", fields)
        with LOCK, connect(self.db_path) as c:
            cur = c.execute("UPDATE items SET qty = qty + ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') "
                            "WHERE id = ? AND qty + ? >= 0", (delta, item_id, delta))
            found = c.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if not found:
                raise ApiError(404, "not_found", "No such item.")
            if cur.rowcount == 0:
                raise ApiError(409, "would_go_negative", "Only %d in stock. The count cannot go below zero." % found["qty"], {"delta": "too large"})
        self.send_json(200, row(found))

    def delete_item(self, item_id):
        with LOCK, connect(self.db_path) as c:
            cur = c.execute("DELETE FROM items WHERE id = ?", (item_id,))
            if cur.rowcount == 0:
                raise ApiError(404, "not_found", "No such item.")
        self.send_json(204, None)

    # ---- verbs ----
    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_DELETE(self):
        self.route("DELETE")

    def do_PUT(self):
        self.route("PUT")

    def do_PATCH(self):
        self.route("PATCH")

    def do_OPTIONS(self):
        self.send_json(204, None, {"Access-Control-Max-Age": "600"})


def main(argv):
    port, db, it = 8765, "stock.db", iter(argv)
    for a in it:
        if a == "--port":
            v = next(it, "")
            if not v.isdigit() or not 1 <= int(v) <= 65535:
                print("server: --port needs a number from 1 to 65535", file=sys.stderr)
                return 2
            port = int(v)
        elif a == "--db":
            db = next(it, None)
            if not db:
                print("server: --db needs a file path", file=sys.stderr)
                return 2
        else:
            print("server: unknown argument " + a, file=sys.stderr)
            return 2
    Handler.db_path = db
    connect(db).close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Stock count on http://127.0.0.1:%d/  (data in %s)" % (port, db), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
