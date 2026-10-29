#!/usr/bin/env python3
"""Plants: the morning watering round for indoor plants. Python standard library and SQLite only.

Run:      python3 server.py --port 8710 --db plants.db
Open:     http://127.0.0.1:8710/
Backup:   python3 server.py backup --db plants.db --to FOLDER
Restore:  python3 server.py restore --db plants.db --from FILE --replace     (replaces every plant and watering in plants.db)
Test seams (refused unless given, each prints a warning at start):
          --now 2026-10-24T06:30+10:00   freeze the clock (the page shows a banner)
          --faults                        add GET /api/_fault, which raises inside the server

Ownership. The server owns every rule: what a valid plant is, that names are unique, that a plant is
watered at most once per Brisbane day, what "today" is, when each plant is next due. The page shows
what the server says.

API (JSON in and out; writes need Content-Type: application/json)
  GET    /api/health
  GET    /api/today                      today's date in Brisbane, counts, the next seven days
  GET    /api/plants?limit=&after=       plants by next due date, then name; bounded, with a cursor
  POST   /api/plants                     {name, room?, every_days, kind}; Idempotency-Key honoured
  POST   /api/plants/<id>/waterings      {}; once per plant per Brisbane day; Idempotency-Key honoured
  DELETE /api/waterings/<id>             undo; only a watering made today

Errors: {"error": {"code", "message", "fields", "request_id"}}, and X-Request-Id on every answer.
  400 bad_json  403 bad_host  404 not_found  405 method_not_allowed  409 duplicate_name
  409 already_watered  409 too_old  409 key_reused  413 too_large  415 not_json  422 invalid  500 server_fault

Time. watered_at is an instant in UTC. local_date and next_due are date-only values in
Australia/Brisbane, computed here. Brisbane has no daylight saving, so a fixed +10:00 is used if the
platform has no time-zone data.

Exposure. Binds 127.0.0.1 only, refuses a foreign Host header, sends no CORS headers: any website the
user visits can reach localhost, and this server has no login.
"""
import base64
import contextlib
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
import time
import traceback
import unicodedata
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
# The visual kit: a kit/ folder beside this file if present (a copied app), otherwise forge's shared assets/visual-kit.
KIT = HERE / "kit" if (HERE / "kit").is_dir() else HERE.parent.parent / "visual-kit"
MAX_BODY = 16 * 1024
KINDS = ("split", "fern", "upright", "round", "trailing", "tree", "spiky", "flower")
PLANT_FIELDS = {"name", "room", "every_days", "kind"}
SERVER_OWNED = {"id", "created_at", "last_watered_at", "last_watered_on", "next_due", "status",
                "days_overdue", "days_until", "watering_today_id", "name_key"}
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

try:
    from zoneinfo import ZoneInfo
    ZONE = ZoneInfo("Australia/Brisbane")
except Exception:  # no tzdata on this platform: Brisbane is UTC+10 all year
    ZONE = dt.timezone(dt.timedelta(hours=10), "Australia/Brisbane")

MIGRATIONS = [
    """CREATE TABLE plant (
         id INTEGER PRIMARY KEY,
         name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 60),
         name_key TEXT NOT NULL UNIQUE,
         room TEXT NOT NULL DEFAULT '' CHECK (length(room) <= 40),
         every_days INTEGER NOT NULL CHECK (every_days BETWEEN 1 AND 60),
         kind TEXT NOT NULL CHECK (kind IN ('split','fern','upright','round','trailing','tree','spiky','flower')),
         created_at TEXT NOT NULL
       ) STRICT""",
    """CREATE TABLE watering (
         id INTEGER PRIMARY KEY,
         plant_id INTEGER NOT NULL REFERENCES plant(id) ON DELETE CASCADE,
         watered_at TEXT NOT NULL,
         local_date TEXT NOT NULL CHECK (local_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
         UNIQUE (plant_id, local_date)
       ) STRICT""",
    """CREATE TABLE idem (
         key TEXT PRIMARY KEY,
         scope TEXT NOT NULL,
         request_hash TEXT NOT NULL,
         status INTEGER NOT NULL,
         body TEXT NOT NULL,
         created_at TEXT NOT NULL
       ) STRICT""",
]

# Kept data: plant name, room, interval, shape; each watering's time. Purpose: the watering round.
# Retention: until the user removes it (remove flow is the next slice). Idempotency keys: one day.

FROZEN = None   # set by --now
FAULTS = False  # set by --faults


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None):
        super().__init__(code)
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}


# ---------- time ----------
def now_utc():
    return FROZEN if FROZEN else dt.datetime.now(dt.timezone.utc)


def iso_instant(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_today(t=None):
    return (t or now_utc()).astimezone(ZONE).date()


def day_label(d):  # the user's own form: "Tue 2 Mar"
    return "%s %d %s" % (DAYS[d.weekday()], d.day, MONTHS[d.month - 1])


def time_label(instant):  # 24-hour, Brisbane
    t = dt.datetime.strptime(instant, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    return t.astimezone(ZONE).strftime("%H:%M")


# ---------- storage ----------
def connect(path):
    c = sqlite3.connect(path, timeout=5, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA busy_timeout = 5000")
    return c


def migrate(path):
    c = connect(path)
    try:
        c.execute("PRAGMA journal_mode = WAL")
        have = c.execute("PRAGMA user_version").fetchone()[0]
        for number, sql in enumerate(MIGRATIONS[have:], start=have + 1):
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute(sql)
                c.execute("PRAGMA user_version = %d" % number)
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
        return c.execute("PRAGMA user_version").fetchone()[0]
    finally:
        c.close()


@contextlib.contextmanager
def tx(c):
    """One write transaction. Any exception rolls it back, so a failed write changes nothing."""
    c.execute("BEGIN IMMEDIATE")
    try:
        yield c
        c.execute("COMMIT")
    except BaseException:
        c.execute("ROLLBACK")
        raise


PLANT_SQL = """
SELECT p.id, p.name, p.name_key, p.room, p.every_days, p.kind, p.created_at,
       w.id AS w_id, w.watered_at AS w_at, w.local_date AS w_on,
       COALESCE(date(w.local_date, '+' || p.every_days || ' days'), :today) AS next_due
FROM plant p
LEFT JOIN watering w ON w.plant_id = p.id
  AND w.local_date = (SELECT MAX(x.local_date) FROM watering x WHERE x.plant_id = p.id)
"""


def plant_out(r, today):
    nd = dt.date.fromisoformat(r["next_due"])
    on = r["w_on"]
    if on == today.isoformat():
        status = "done"
    elif on is None or nd == today:
        status = "due"
    elif nd < today:
        status = "overdue"
    else:
        status = "later"
    return {
        "id": r["id"], "name": r["name"], "room": r["room"], "every_days": r["every_days"], "kind": r["kind"],
        "created_at": r["created_at"], "last_watered_at": r["w_at"], "last_watered_on": on,
        "next_due": nd.isoformat(), "status": status,
        "days_overdue": (today - nd).days if status == "overdue" else 0,
        "days_until": (nd - today).days if status in ("later", "done") else 0,
        "watering_today_id": r["w_id"] if status == "done" else None,
    }


def get_plant(c, pid, today):
    r = c.execute("SELECT * FROM (" + PLANT_SQL + ") WHERE id = :id", {"today": today.isoformat(), "id": pid}).fetchone()
    return plant_out(r, today) if r else None


# ---------- validation ----------
def as_int(v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int):
        return None
    return v if lo <= v <= hi else None


def name_key(name):
    return " ".join(name.split()).casefold()


def validate_plant(body):
    fields = {}
    for k in sorted(set(body) - PLANT_FIELDS):
        fields[k] = "is set by the server" if k in SERVER_OWNED else "is not a plant field"
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        fields["name"] = "is required"
    else:
        name = unicodedata.normalize("NFC", name.strip())
        if len(name) > 60:
            fields["name"] = "must be 60 characters or fewer"
    room = body.get("room", "")
    if room is None:
        room = ""
    if not isinstance(room, str):
        fields["room"] = "must be text"
    else:
        room = unicodedata.normalize("NFC", room.strip())
        if len(room) > 40:
            fields["room"] = "must be 40 characters or fewer"
    every = as_int(body.get("every_days"), 1, 60)
    if every is None:
        fields["every_days"] = "must be a whole number of days from 1 to 60"
    kind = body.get("kind")
    if kind not in KINDS:
        fields["kind"] = "must be one of the shapes shown"
    if fields:
        raise ApiError(422, "invalid", "Check the highlighted fields.", fields)
    return {"name": name, "name_key": name_key(name), "room": room, "every_days": every, "kind": kind}


# ---------- idempotency ----------
def idem_lookup(c, key, scope, digest):
    if not key:
        return None
    c.execute("DELETE FROM idem WHERE created_at < ?", (iso_instant(now_utc() - dt.timedelta(days=1)),))
    seen = c.execute("SELECT scope, request_hash, status, body FROM idem WHERE key = ?", (key,)).fetchone()
    if seen and (seen["scope"] != scope or seen["request_hash"] != digest):
        raise ApiError(409, "key_reused", "This request key was already used for a different change. Reload and try again.")
    return seen


def idem_store(c, key, scope, digest, status, body):
    if key:
        c.execute("INSERT INTO idem (key, scope, request_hash, status, body, created_at) VALUES (?,?,?,?,?,?)",
                  (key, scope, digest, status, json.dumps(body), iso_instant(now_utc())))


def digest_of(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


# ---------- HTTP ----------
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/plant-art.js": ("plant-art.js", "text/javascript; charset=utf-8"),
    "/kit/kit.css": ("kit/kit.css", "text/css; charset=utf-8"),
    "/kit/kit2.css": ("kit/kit2.css", "text/css; charset=utf-8"),
    "/kit/kit3.css": ("kit/kit3.css", "text/css; charset=utf-8"),
    "/kit/kit-dir.js": ("kit/kit-dir.js", "text/javascript; charset=utf-8"),
    "/kit/fonts.css": ("kit/fonts.css", "text/css; charset=utf-8"),
    "/kit/illustrations.js": ("kit/illustrations.js", "text/javascript; charset=utf-8"),
}
FONT = re.compile(r"/kit/fonts/([a-z0-9-]+\.woff2)")
RID = re.compile(r"[A-Za-z0-9-]{1,64}")
PID = re.compile(r"[1-9][0-9]{0,11}")


class Handler(BaseHTTPRequestHandler):
    server_version = "Plants/1"
    db_path = "plants.db"
    hosts = set()

    def log_message(self, fmt, *args):  # replaced by log_line: route template, status, duration, id
        pass

    def log_line(self):
        ms = (time.monotonic() - self.t0) * 1000
        sys.stderr.write("%s %s %d %.1fms rid=%s\n" % (self.command, self.template, self.status_sent, ms, self.rid))

    def send(self, status, payload=None, ctype="application/json; charset=utf-8", extra=None, raw=None):
        data = raw if raw is not None else (b"" if payload is None else json.dumps(payload).encode("utf-8"))
        self.status_sent = status
        self.send_response(status)
        if data:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-Id", self.rid)
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if data and self.command != "HEAD":
            self.wfile.write(data)

    def fail(self, e):
        self.send(e.status, {"error": {"code": e.code, "message": e.message, "fields": e.fields, "request_id": self.rid}})

    def read_json(self):
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            raise ApiError(415, "not_json", "Send the request as JSON (Content-Type: application/json).")
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "bad_json", "The request length is not a number.")
        if n > MAX_BODY:
            raise ApiError(413, "too_large", "The request is too large. A plant needs only a name, room, interval and shape.")
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(400, "bad_json", "The request is not valid JSON.")
        if not isinstance(body, dict):
            raise ApiError(400, "bad_json", "The request must be a JSON object.")
        return body

    def need(self, *allowed):
        if self.command not in allowed:
            raise ApiError(405, "method_not_allowed", "Use %s here." % " or ".join(allowed))

    def handle_any(self):
        self.t0, self.status_sent, self.template = time.monotonic(), 0, "?"
        rid = self.headers.get("X-Request-Id") or ""
        self.rid = rid if RID.fullmatch(rid) else uuid.uuid4().hex[:16]
        try:
            if self.headers.get("Host", "") not in self.hosts:
                self.template = "(foreign host)"
                raise ApiError(403, "bad_host", "This server answers only on its own address.")
            self.route()
        except ApiError as e:
            self.fail(e)
        except Exception:
            sys.stderr.write("fault rid=%s\n%s" % (self.rid, traceback.format_exc()))
            if not self.status_sent:
                self.send(500, {"error": {"code": "server_fault", "message": "Something failed on the plant server. Reload the page to see what was saved.",
                                          "fields": {}, "request_id": self.rid}})
        finally:
            self.log_line()

    do_GET = do_POST = do_DELETE = do_PUT = do_PATCH = do_HEAD = do_OPTIONS = handle_any

    def route(self):
        url = urlparse(self.path)
        path = url.path
        m = self.command
        if path in STATIC or FONT.fullmatch(path):
            self.template = path if path in STATIC else "/kit/fonts/{file}"
            self.need("GET", "HEAD")
            rel, ctype = STATIC[path] if path in STATIC else ("kit/fonts/" + FONT.fullmatch(path).group(1), "font/woff2")
            f = KIT / rel[4:] if rel.startswith("kit/") else HERE / rel
            if not f.is_file():
                raise ApiError(404, "not_found", "No such file.")
            return self.send(200, ctype=ctype, raw=f.read_bytes())
        parts = [p for p in path.split("/") if p]
        if parts[:1] != ["api"]:
            self.template = "(other)"
            raise ApiError(404, "not_found", "No such page.")
        if m == "OPTIONS":  # no CORS: a foreign origin's preflight gets no allow headers
            self.template = "OPTIONS /api/*"
            return self.send(204)
        c = connect(self.db_path)
        try:
            today = local_today()
            if parts == ["api", "health"]:
                self.template = "/api/health"
                self.need("GET")
                c.execute("SELECT 1").fetchone()
                return self.send(200, {"status": "ok"})
            if parts == ["api", "today"]:
                self.template = "/api/today"
                self.need("GET")
                return self.send(200, self.today_summary(c, today))
            if parts == ["api", "plants"]:
                self.template = "/api/plants"
                self.need("GET", "POST")
                return self.list_plants(c, today, parse_qs(url.query)) if m == "GET" else self.create_plant(c, today)
            if len(parts) == 4 and parts[:2] == ["api", "plants"] and parts[3] == "waterings":
                self.template = "/api/plants/{id}/waterings"
                self.need("POST")
                return self.water(c, self.ident(parts[2], "plant"))
            if len(parts) == 3 and parts[:2] == ["api", "waterings"]:
                self.template = "/api/waterings/{id}"
                self.need("DELETE")
                return self.undo(c, today, self.ident(parts[2], "watering"))
            if FAULTS and parts == ["api", "_fault"]:
                self.template = "/api/_fault"
                raise RuntimeError("planted fault: /srv/secret/plants.db SELECT * FROM plant")
            self.template = "/api/(unknown)"
            raise ApiError(404, "not_found", "No such route.")
        except sqlite3.OperationalError:
            raise ApiError(503, "storage_busy", "The plant list is busy or unreadable. Nothing was changed. Try again.")
        finally:
            c.close()

    @staticmethod
    def ident(text, what):
        if not PID.fullmatch(text):
            raise ApiError(404, "not_found", "No such %s." % what)
        return int(text)

    # ---------- operations ----------
    def today_summary(self, c, today):
        rows = [plant_out(r, today) for r in c.execute(PLANT_SQL, {"today": today.isoformat()})]
        left = sum(p["status"] in ("due", "overdue") for p in rows)
        done = sum(p["status"] == "done" for p in rows)
        week = []
        for i in range(7):
            d = today + dt.timedelta(days=i)
            if i == 0:
                n = left + done
            else:
                n = 0
                for p in rows:
                    base = today if p["status"] in ("due", "overdue") else dt.date.fromisoformat(p["next_due"])
                    if d >= base and (d - base).days % p["every_days"] == 0:
                        n += 1
            week.append({"date": d.isoformat(), "due": n})
        return {"today": today.isoformat(), "zone": "Australia/Brisbane", "now": iso_instant(now_utc()),
                "frozen": bool(FROZEN), "counts": {"plants": len(rows), "left": left, "done": done}, "week": week}

    def list_plants(self, c, today, q):
        fields = {}
        raw_limit = (q.get("limit") or ["100"])[0]
        limit = int(raw_limit) if raw_limit.isdigit() and 1 <= int(raw_limit) <= 200 else None
        if limit is None:
            fields["limit"] = "must be a whole number from 1 to 200"
        after = (q.get("after") or [""])[0]
        cur = None
        if after:
            try:
                d, k, i = json.loads(base64.urlsafe_b64decode(after + "=" * (-len(after) % 4)).decode("utf-8"))
                dt.date.fromisoformat(d)
                assert isinstance(k, str) and isinstance(i, int) and not isinstance(i, bool)
                cur = (d, k, i)
            except Exception:
                fields["after"] = "is not a cursor this list gave out"
        if fields:
            raise ApiError(422, "invalid", "Check the list request.", fields)
        args = {"today": today.isoformat(), "lim": limit + 1}
        sql = "SELECT * FROM (" + PLANT_SQL + ")"
        if cur:
            sql += " WHERE (next_due, name_key, id) > (:d, :k, :i)"
            args.update(d=cur[0], k=cur[1], i=cur[2])
        rows = c.execute(sql + " ORDER BY next_due, name_key, id LIMIT :lim", args).fetchall()
        more = len(rows) > limit
        rows = rows[:limit]
        nxt = base64.urlsafe_b64encode(json.dumps([rows[-1]["next_due"], rows[-1]["name_key"], rows[-1]["id"]]).encode("utf-8")).decode("ascii").rstrip("=") if more else None
        return self.send(200, {"today": today.isoformat(), "plants": [plant_out(r, today) for r in rows], "next": nxt})

    def create_plant(self, c, today):
        key = (self.headers.get("Idempotency-Key") or "").strip()[:80]
        p = validate_plant(self.read_json())
        digest = digest_of(p)
        with tx(c):
            seen = idem_lookup(c, key, "POST /api/plants", digest)
            if seen:
                return self.send(seen["status"], json.loads(seen["body"]), extra={"Idempotent-Replay": "true"})
            try:
                cur = c.execute("INSERT INTO plant (name, name_key, room, every_days, kind, created_at) VALUES (?,?,?,?,?,?)",
                                (p["name"], p["name_key"], p["room"], p["every_days"], p["kind"], iso_instant(now_utc())))
            except sqlite3.IntegrityError:
                other = c.execute("SELECT name, room FROM plant WHERE name_key = ?", (p["name_key"],)).fetchone()
                where = " (%s)" % other["room"] if other and other["room"] else ""
                raise ApiError(409, "duplicate_name",
                               "You already have a plant called %s%s. Give this one another name, such as %s 2." % (other["name"] if other else p["name"], where, other["name"] if other else p["name"]),
                               {"name": "is already used by another plant"})
            created = get_plant(c, cur.lastrowid, today)
            idem_store(c, key, "POST /api/plants", digest, 201, created)
        return self.send(201, created)

    def water(self, c, pid):
        key = (self.headers.get("Idempotency-Key") or "").strip()[:80]
        body = self.read_json()
        if body:
            raise ApiError(422, "invalid", "A watering needs no details; the server records the time.",
                           {k: ("is set by the server" if k in ("watered_at", "local_date", "id", "plant_id") else "is not a watering field") for k in sorted(body)})
        t = now_utc()
        today = local_today(t)
        scope = "POST /api/plants/%d/waterings" % pid
        with tx(c):
            seen = idem_lookup(c, key, scope, digest_of({}))
            if seen:
                return self.send(seen["status"], json.loads(seen["body"]), extra={"Idempotent-Replay": "true"})
            plant = c.execute("SELECT name, every_days FROM plant WHERE id = ?", (pid,)).fetchone()
            if not plant:
                raise ApiError(404, "not_found", "That plant is no longer on the list. Reload to see the current list.")
            try:
                cur = c.execute("INSERT INTO watering (plant_id, watered_at, local_date) VALUES (?,?,?)",
                                (pid, iso_instant(t), today.isoformat()))
            except sqlite3.IntegrityError:
                w = c.execute("SELECT watered_at FROM watering WHERE plant_id = ? AND local_date = ?", (pid, today.isoformat())).fetchone()
                nxt = today + dt.timedelta(days=plant["every_days"])
                raise ApiError(409, "already_watered",
                               "%s was already watered today at %s. It is next due %s." % (plant["name"], time_label(w["watered_at"]), day_label(nxt)),
                               {})
            out = {"watering": {"id": cur.lastrowid, "plant_id": pid, "watered_at": iso_instant(t), "local_date": today.isoformat()},
                   "plant": get_plant(c, pid, today)}
            idem_store(c, key, scope, digest_of({}), 201, out)
        return self.send(201, out)

    def undo(self, c, today, wid):
        with tx(c):
            w = c.execute("SELECT w.plant_id, w.local_date, p.name FROM watering w JOIN plant p ON p.id = w.plant_id WHERE w.id = ?", (wid,)).fetchone()
            if not w:
                raise ApiError(404, "not_found", "That watering is not on record. Reload to see the current list.")
            if w["local_date"] != today.isoformat():
                raise ApiError(409, "too_old", "Only today's watering can be undone. %s was watered %s." % (w["name"], day_label(dt.date.fromisoformat(w["local_date"]))))
            c.execute("DELETE FROM watering WHERE id = ?", (wid,))
            plant = get_plant(c, w["plant_id"], today)
        return self.send(200, {"plant": plant})


# ---------- commands ----------
def backup(db, folder):
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    target = out / ("plants-%s.db" % dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    src, dst = sqlite3.connect(db), sqlite3.connect(target)
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    print("backup written: %s" % target)
    return 0


def restore(db, file, replace):
    if not replace:
        print("restore replaces every plant and watering in %s. Run again with --replace to do it." % db, file=sys.stderr)
        return 2
    src = sqlite3.connect("file:%s?mode=ro" % file, uri=True)
    try:
        v = src.execute("PRAGMA user_version").fetchone()[0]
        n = src.execute("SELECT COUNT(*) FROM plant").fetchone()[0]
    except sqlite3.Error:
        print("restore: %s is not a plants backup" % file, file=sys.stderr)
        return 2
    if v < 1 or v > len(MIGRATIONS):
        print("restore: %s has schema version %d; this server knows 1 to %d" % (file, v, len(MIGRATIONS)), file=sys.stderr)
        return 2
    dst = sqlite3.connect(db)
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    migrate(db)
    print("restored %d plants from %s into %s" % (n, file, db))
    return 0


def main(argv):
    global FROZEN, FAULTS
    if argv[:1] in (["backup"], ["restore"]):
        cmd, rest = argv[0], argv[1:]
        opts, flags, it = {}, set(), iter(rest)
        for a in it:
            if a in ("--db", "--to", "--from"):
                opts[a] = next(it, "")
            elif a == "--replace":
                flags.add(a)
            else:
                print("server: unknown argument " + a, file=sys.stderr); return 2
        if not opts.get("--db"):
            print("server: --db is required", file=sys.stderr); return 2
        if cmd == "backup":
            return backup(opts["--db"], opts.get("--to") or ".")
        if not opts.get("--from"):
            print("server: restore needs --from FILE", file=sys.stderr); return 2
        return restore(opts["--db"], opts["--from"], "--replace" in flags)
    port, db, it = 8710, "plants.db", iter(argv)
    for a in it:
        if a == "--port":
            v = next(it, "")
            if not v.isdigit() or not 1 <= int(v) <= 65535:
                print("server: --port needs a number from 1 to 65535", file=sys.stderr); return 2
            port = int(v)
        elif a == "--db":
            db = next(it, "")
        elif a == "--now":
            v = next(it, "")
            try:
                FROZEN = dt.datetime.fromisoformat(v)
                assert FROZEN.tzinfo is not None
            except Exception:
                print("server: --now needs a date-time with an offset, e.g. 2026-10-24T06:30+10:00", file=sys.stderr); return 2
        elif a == "--faults":
            FAULTS = True
        else:
            print("server: unknown argument " + a, file=sys.stderr); return 2
    version = migrate(db)
    Handler.db_path = db
    Handler.hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
    if FROZEN:
        print("WARNING: clock frozen at %s for testing (--now). The page shows a banner." % FROZEN.isoformat(), flush=True)
    if FAULTS:
        print("WARNING: fault route /api/_fault is on (--faults). Testing only.", flush=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Plants on http://127.0.0.1:%d/  (data in %s, schema %d)" % (port, db, version), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
