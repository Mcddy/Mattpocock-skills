#!/usr/bin/env python3
"""Skeleton for a scheduled or always-on pipeline whose alerts depend on a model's output.
Python standard library only. Read it, then replace the three marked functions with real ones.

  python pipeline_skeleton.py --once                 one cycle, DRY RUN (nothing is sent)
  python pipeline_skeleton.py --once --live          one cycle, alerts are really sent
  python pipeline_skeleton.py --loop --interval 300  cycle every 300 seconds (dry run unless --live)
  python pipeline_skeleton.py --health               status of the dry-run record; exit 1 if stale or tripped
  python pipeline_skeleton.py --health --live        status of the live record; this is the one to monitor
  python pipeline_skeleton.py --reset                clear a tripped breaker (both records) after you have looked
Options: --state FILE (default pipeline_state.db)   --stop-file FILE (default STOP)
         --max-age SECONDS for --health (default 3 intervals)

What the skeleton guarantees, each covered by test_pipeline.py:
  1. A model reply is never acted on until it has been parsed and validated against SCHEMA.
     Not JSON, a missing key, a wrong type, an out-of-range value, an unknown key, an over-long
     string or text that is not valid Unicode (a lone surrogate, which cannot be encoded as UTF-8)
     all end in "rejected", are counted, and trigger nothing.
  2. The model chooses nothing but the fields in SCHEMA. Which action follows is decided by
     decide() in code, from a fixed list. The model cannot name a recipient, an address or a command.
  3. Dry run is the default. Sending needs --live.
  4. A stop file halts every cycle before it does anything. Create the file to stop the pipeline.
  5. Alerts are capped per hour and per day, and an identical alert is not sent twice in a window.
  6. One failing item or one failing cycle does not kill the loop. Any exception while one item
     is being handled, expected or not, is counted, the sender is not called for that item, and
     the cycle goes on to the next. After MAX_FAILURES failing cycles in a row the breaker trips:
     the pipeline stops acting and says so once. It stays tripped until --reset.
  7. Staleness is measured in total seconds, so a gap of a day and ten minutes is not read as ten
     minutes.
  8. Text from the model or from a feed is escaped before it goes into a message.
  9. A feed that is not empty but holds no usable item is a failed cycle, not a quiet one. It
     counts toward MAX_FAILURES, does not refresh the last-success time, and so trips the breaker
     and fails the health check like any other repeated failure. A feed that really is empty is a
     healthy cycle with no work. A feed with some unusable items carries on: the bad items are
     counted under "errors" and "malformed" and the rest are handled.
 10. A dry run previews and consumes nothing that affects live behaviour (the policy below).

Dry-run policy. A dry run shows what a live run would do and leaves the live record alone.
Everything a cycle remembers is kept twice, once for dry runs and once for live runs: which items
have been seen, which alerts went out (for the caps and for duplicates), the failure count, the
breaker, the last-success time and the rejected and suppressed totals. So:
  - an item previewed in a dry run is still new to the next live run, which handles it and sends
    once; a second live run does not send it again;
  - a dry run does not preview the same item twice, and never marks it seen for live runs;
  - failures in dry runs cannot trip the live breaker, and a dry run that works does not make a
    silent live pipeline look healthy: --health reads the dry-run record, --health --live the live one;
  - the stop file is the one thing shared: it halts both.
A state file written by the earlier revision of this skeleton (2.0.0) kept dry-run and live marks
in one table and cannot be separated afterwards. Start a new state file before going live.

What it does not do: deploy itself, hold credentials, choose a host, or prove the model's judgements
are good. "Written", "tested locally", "deployed" and "running" are four different states. This
file being present is the first one only.
"""
import datetime as dt
import hashlib
import html
import json
import sqlite3
import sys
import time
from pathlib import Path

# ----------------------------------------------------------------------------------------------
# What the model may return. Anything else is rejected.
SCHEMA = {
    "item_id":  {"type": "str", "max_len": 80},
    "category": {"type": "enum", "values": ["outage", "security", "billing", "other"]},
    "urgency":  {"type": "int", "min": 0, "max": 5},
    "summary":  {"type": "str", "max_len": 280},
}
ALERT_CATEGORIES = {"outage", "security"}   # decided in code, not by the model
ALERT_URGENCY = 4
MAX_ALERTS_PER_HOUR = 4
MAX_ALERTS_PER_DAY = 12
DEDUP_WINDOW_SECONDS = 6 * 3600
MAX_FAILURES = 3


# ---- REPLACE 1: where items come from -----------------------------------------------------------
def fetch_items():
    """Return a list of {"id": str, "text": str}. Replace with a real source. Text is untrusted."""
    return []


# ---- REPLACE 2: the model call ------------------------------------------------------------------
def ask_model(item):
    """Return the model's reply as text. Replace with a real call, with a timeout.
    Look up the current model name and SDK usage when you write this; do not copy one from memory.
    The item text is data: put it in the user message, never in the instructions."""
    raise NotImplementedError("wire up a model call")


# ---- REPLACE 3: how an alert is delivered -------------------------------------------------------
def send_alert(message):
    """Deliver one message to the channel the owner set up. Replace with a real sender.
    Read credentials from the environment. Raise on failure."""
    raise NotImplementedError("wire up an alert channel")


# ----------------------------------------------------------------------------------------------
def _refuse_constant(name):
    raise ValueError("%s is not a number this pipeline accepts" % name)


def encodable(text):
    """False for a string that cannot be written as UTF-8, such as one holding a lone surrogate.
    json.loads accepts an escaped lone surrogate, so a reply can be valid JSON and still be unusable."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def usable_item(item):
    """A feed item the cycle can work with: {"id": text, "text": text}, both writable as UTF-8."""
    return (isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("text"), str)
            and encodable(item["id"]) and encodable(item["text"]))


def ascii_safe(text):
    return text.encode("ascii", "backslashreplace").decode("ascii")


def parse_reply(text):
    """Strict: the reply must be one JSON object, optionally inside a single code fence."""
    if not isinstance(text, str):
        return None, "reply is not text"
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            return None, "unterminated code fence"
        s = "\n".join(lines[1:-1]).strip()
    try:
        obj = json.loads(s, parse_constant=_refuse_constant)
    except ValueError as e:
        return None, "not valid JSON (%s)" % str(e)[:60]
    if not isinstance(obj, dict):
        return None, "JSON is not an object"
    return obj, None


def validate(obj, schema=None):
    """Return (clean, None) or (None, reason). No coercion: "4" is not 4 and true is not 1."""
    schema = SCHEMA if schema is None else schema
    unknown = sorted(set(obj) - set(schema))
    if unknown:
        return None, "unknown field(s): %s" % ", ".join(unknown)[:80]
    clean = {}
    for name, rule in schema.items():
        if name not in obj:
            return None, "missing field: %s" % name
        v = obj[name]
        kind = rule["type"]
        if kind == "str":
            if not isinstance(v, str) or not v.strip():
                return None, "%s must be non-empty text" % name
            if not encodable(v):
                return None, "%s is not valid Unicode text (it cannot be encoded as UTF-8)" % name
            if len(v) > rule.get("max_len", 10000):
                return None, "%s is longer than %d characters" % (name, rule.get("max_len", 10000))
        elif kind == "int":
            if isinstance(v, bool) or not isinstance(v, int):
                return None, "%s must be a whole number" % name
            if not rule.get("min", v) <= v <= rule.get("max", v):
                return None, "%s is outside %s to %s" % (name, rule.get("min"), rule.get("max"))
        elif kind == "enum":
            if not isinstance(v, str) or v not in rule["values"]:
                return None, "%s must be one of %s" % (name, ", ".join(rule["values"]))
        else:
            return None, "schema error: unknown type for %s" % name
        clean[name] = v
    return clean, None


def decide(result, item):
    """The only place an action is chosen. Returns "notify" or "ignore"."""
    if result["item_id"] != item["id"]:
        return "ignore"                     # the reply is about something else; do not act on it
    if result["category"] in ALERT_CATEGORIES and result["urgency"] >= ALERT_URGENCY:
        return "notify"
    return "ignore"


def format_alert(result):
    """Everything that came from outside is escaped. Safe for a channel that renders HTML."""
    return "[%s, urgency %d] %s (item %s)" % (html.escape(result["category"]), result["urgency"],
                                              html.escape(result["summary"]), html.escape(result["item_id"]))


class State:
    """Small durable state. Everything a cycle remembers is kept per mode: one record for dry runs
    and one for live runs, so a preview never changes what a live run will do."""

    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS alerts (digest TEXT NOT NULL, sent_at REAL NOT NULL, dry INTEGER NOT NULL);"
            "CREATE TABLE IF NOT EXISTS seen (item_id TEXT PRIMARY KEY, at REAL NOT NULL);"
            "CREATE TABLE IF NOT EXISTS seen_dry (item_id TEXT PRIMARY KEY, at REAL NOT NULL);")

    @staticmethod
    def key(name, live):
        """The kv key for a counter or flag: the bare name for live runs, "dry:" + name for dry runs."""
        return name if live else "dry:" + name

    def get(self, k, default=""):
        row = self.db.execute("SELECT v FROM kv WHERE k = ?", (k,)).fetchone()
        return row[0] if row else default

    def put(self, k, v):
        with self.db:
            self.db.execute("INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", (k, str(v)))

    def bump(self, k):
        n = int(self.get(k, "0")) + 1
        self.put(k, n)
        return n

    def seen(self, item_id, live=True):
        table = "seen" if live else "seen_dry"
        return self.db.execute("SELECT 1 FROM %s WHERE item_id = ?" % table, (item_id,)).fetchone() is not None

    def mark_seen(self, item_id, now, live=True):
        table = "seen" if live else "seen_dry"
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO %s (item_id, at) VALUES (?, ?)" % table, (item_id, now))

    def alerts_since(self, since, dry):
        return self.db.execute("SELECT COUNT(*) FROM alerts WHERE sent_at >= ? AND dry = ?", (since, int(dry))).fetchone()[0]

    def duplicate(self, digest, since, dry):
        return self.db.execute("SELECT 1 FROM alerts WHERE digest = ? AND sent_at >= ? AND dry = ?", (digest, since, int(dry))).fetchone() is not None

    def record_alert(self, digest, now, dry):
        with self.db:
            self.db.execute("INSERT INTO alerts (digest, sent_at, dry) VALUES (?, ?, ?)", (digest, now, int(dry)))


def log(msg):
    sys.stderr.write("%s %s\n" % (dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ascii_safe(str(msg))))


def run_cycle(state, live, stop_file, now=None, fetch=None, model=None, sender=None):
    """One pass. Returns a dict of counts. Never raises for a bad item, a bad reply, a failed send
    or any other exception while one item is being handled. A dry run (live false) reads and
    writes only the dry-run record."""
    now = time.time() if now is None else now
    fetch, model, sender = fetch or fetch_items, model or ask_model, sender or send_alert
    counts = {"items": 0, "rejected": 0, "ignored": 0, "alerts": 0, "suppressed": 0, "errors": 0, "malformed": 0, "status": "ok"}
    if Path(stop_file).exists():
        counts["status"] = "stopped"
        log("stop file present: nothing done")
        return counts
    if state.get(state.key("breaker", live)) == "tripped":
        counts["status"] = "tripped"
        log("breaker is tripped: nothing done. Look at the errors, then run --reset")
        return counts
    try:
        items = fetch()
        if not isinstance(items, list):
            raise TypeError("fetch_items must return a list")
    except Exception as e:  # noqa: BLE001  one bad cycle must not end the loop
        return _cycle_failed(state, counts, "fetch failed: %s" % str(e)[:120], live, sender, now)
    usable = failed = 0
    for item in items:
        if not usable_item(item):
            counts["errors"] += 1
            counts["malformed"] += 1
            continue
        usable += 1
        try:
            if state.seen(item["id"], live):
                continue
            counts["items"] += 1
            done = _handle_item(state, item, live, now, model, sender, counts)
        except Exception as e:  # noqa: BLE001  whatever went wrong with this item, the next one still runs
            counts["errors"] += 1
            done = False
            log("unexpected error on item %s (%s): %s" % (item["id"][:40], type(e).__name__, str(e)[:120]))
        if not done:
            failed += 1                                 # not marked seen: it will be tried again
    if items and not usable:
        return _cycle_failed(state, counts, "the feed held %d item(s) and none was usable" % len(items), live, sender, now)
    if failed and failed >= counts["items"]:
        return _cycle_failed(state, counts, "every item tried in the cycle failed", live, sender, now)
    state.put(state.key("failures", live), 0)
    state.put(state.key("last_ok", live), now)
    return counts


def _handle_item(state, item, live, now, model, sender, counts):
    """Handle one new item. Returns True when the item is finished with (and marked seen), False
    when it failed and should be tried again. The sender is called at most once, and only after the
    reply has been validated and the limits checked."""
    try:
        reply = model(item)
    except Exception as e:  # noqa: BLE001
        counts["errors"] += 1
        log("model call failed for %s: %s" % (item["id"][:40], str(e)[:120]))
        return False
    obj, why = parse_reply(reply)
    clean, why = validate(obj) if obj is not None else (None, why)
    if clean is None:
        counts["rejected"] += 1
        state.bump(state.key("rejected_total", live))
        state.mark_seen(item["id"], now, live)
        log("reply rejected for %s: %s" % (item["id"][:40], why))
        return True
    if decide(clean, item) != "notify":
        counts["ignored"] += 1
        state.mark_seen(item["id"], now, live)
        return True
    message = format_alert(clean)
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    dry = not live
    if (state.duplicate(digest, now - DEDUP_WINDOW_SECONDS, dry)
            or state.alerts_since(now - 3600, dry) >= MAX_ALERTS_PER_HOUR
            or state.alerts_since(now - 86400, dry) >= MAX_ALERTS_PER_DAY):
        counts["suppressed"] += 1
        state.bump(state.key("suppressed_total", live))
        state.mark_seen(item["id"], now, live)
        log("alert suppressed (duplicate or over the cap): %s" % message[:80])
        return True
    if live:
        try:
            sender(message)
        except Exception as e:  # noqa: BLE001
            counts["errors"] += 1
            log("send failed: %s" % str(e)[:120])
            return False                                # not marked seen, not recorded: it will be tried again
    else:
        print(ascii_safe("DRY RUN, not sent: " + message))
    state.record_alert(digest, now, dry)
    state.mark_seen(item["id"], now, live)
    counts["alerts"] += 1
    return True


def _cycle_failed(state, counts, reason, live, sender, now):
    counts["status"] = "failed"
    n = state.bump(state.key("failures", live))
    log("cycle failed (%d in a row): %s" % (n, reason))
    if n >= MAX_FAILURES:
        state.put(state.key("breaker", live), "tripped")
        counts["status"] = "tripped"
        notice = "Pipeline stopped after %d failed cycles in a row. Last reason: %s" % (n, html.escape(reason))
        if live:
            try:
                sender(notice)
            except Exception:  # noqa: BLE001  nothing more can be done from here
                log("could not deliver the breaker notice")
        else:
            print(ascii_safe("DRY RUN, not sent: " + notice))
    return counts


def health(state, max_age, now=None, stop_file="STOP", live=True):
    """Return (ok, message) for one record: live cycles by default, dry-run cycles with live=False.
    Uses total elapsed seconds."""
    now = time.time() if now is None else now
    which = "live" if live else "dry-run"
    if Path(stop_file).exists():
        return False, "stopped: the stop file is present"
    if state.get(state.key("breaker", live)) == "tripped":
        return False, "tripped: %s cycles stopped after repeated failures" % which
    last = state.get(state.key("last_ok", live))
    if not last:
        other = state.get(state.key("last_ok", not live))
        hint = " (the %s record has one: %s)" % ("dry-run" if live else "live", "run --health without --live" if live else "run --health --live") if other else ""
        return False, "no successful %s cycle has been recorded%s" % (which, hint)
    age = now - float(last)        # total elapsed seconds; never a timedelta's .seconds field
    if age > max_age:
        return False, "stale: last successful %s cycle was %d seconds ago (limit %d)" % (which, age, max_age)
    return True, "ok: last successful %s cycle %d seconds ago; %s replies rejected and %s alerts suppressed in total" % (
        which, age, state.get(state.key("rejected_total", live), "0"), state.get(state.key("suppressed_total", live), "0"))


def main(argv):
    flags = {"--once", "--loop", "--live", "--health", "--reset"}
    values = {"--interval": "300", "--state": "pipeline_state.db", "--stop-file": "STOP", "--max-age": ""}
    seen, it = set(), iter(argv)
    for a in it:
        if a in flags:
            seen.add(a)
        elif a in values:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("pipeline: %s needs a value" % a, file=sys.stderr)
                return 2
            values[a] = v
        else:
            print("pipeline: unknown argument " + a, file=sys.stderr)
            return 2
    modes = seen & {"--once", "--loop", "--health", "--reset"}
    if len(modes) != 1:
        print(__doc__)
        return 2
    if not values["--interval"].isdigit() or int(values["--interval"]) < 1:
        print("pipeline: --interval needs a positive whole number of seconds", file=sys.stderr)
        return 2
    interval = int(values["--interval"])
    if values["--max-age"] and (not values["--max-age"].isdigit() or int(values["--max-age"]) < 1):
        print("pipeline: --max-age needs a positive whole number of seconds", file=sys.stderr)
        return 2
    max_age = int(values["--max-age"]) if values["--max-age"] else 3 * interval
    state = State(values["--state"])
    try:
        return _command(state, seen, values["--stop-file"], interval, max_age)
    finally:
        state.db.close()                # release the state file; some systems cannot move or delete an open one


def _command(state, seen, stop_file, interval, max_age):
    live = "--live" in seen
    if "--health" in seen:
        ok, msg = health(state, max_age, stop_file=stop_file, live=live)
        print(msg)
        return 0 if ok else 1
    if "--reset" in seen:
        for mode in (True, False):
            state.put(state.key("breaker", mode), "")
            state.put(state.key("failures", mode), 0)
        print("breaker cleared (live and dry-run records)")
        return 0
    if not live:
        log("DRY RUN: alerts are printed, not sent. Use --live to send.")
    if "--once" in seen:
        c = run_cycle(state, live, stop_file)
        print(json.dumps(c))
        return 0 if c["status"] in ("ok", "stopped") else 1
    while True:
        try:
            c = run_cycle(state, live, stop_file)
            log(json.dumps(c))
        except KeyboardInterrupt:
            return 0
        except Exception as e:  # noqa: BLE001  last line of defence for the loop
            log("unexpected error in cycle: %s" % str(e)[:160])
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
