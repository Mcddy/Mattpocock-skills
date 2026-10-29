"""Writes api-steps.json (main run, server started with --faults) and the two clock files."""
import json
from pathlib import Path

HERE = Path(__file__).parent
J = {"Content-Type": "application/json"}


def post(name, path, body, expect, headers=None, save=None, **kw):
    s = {"name": name, "method": "POST", "path": path, "json": body, "expect": expect}
    if headers:
        s["headers"] = headers
    if save:
        s["save"] = save
    s.update(kw)
    return s


def get(name, path, expect, headers=None, save=None):
    s = {"name": name, "method": "GET", "path": path, "expect": expect}
    if headers:
        s["headers"] = headers
    if save:
        s["save"] = save
    return s


FERN = {"name": "Boston fern", "room": "Bathroom", "every_days": 3, "kind": "fern"}
steps = [
    get("health answers", "/api/health", {"status": 200, "json": {"status": "ok"}, "headers": {"X-Request-Id": {"$exists": True}}}),
    get("empty list", "/api/plants", {"status": 200, "json": {"plants": {"$len": 0}, "next": None}}),
    get("empty today", "/api/today", {"status": 200, "json": {"counts.plants": 0, "counts.left": 0, "week": {"$len": 7}, "zone": "Australia/Brisbane"}}),
    post("add Boston fern", "/api/plants", FERN, {"status": 201, "json": {"name": "Boston fern", "status": "due", "last_watered_at": None, "every_days": 3, "id": {"$exists": True}}},
         headers={"Idempotency-Key": "add-fern-1"}, save={"fern": "id"}),
    post("same key and body replays, adds nothing", "/api/plants", FERN, {"status": 201, "json": {"name": "Boston fern"}, "headers": {"Idempotent-Replay": "true"}},
         headers={"Idempotency-Key": "add-fern-1"}),
    post("same key, other body refused", "/api/plants", {"name": "Aloe", "every_days": 14, "kind": "spiky"}, {"status": 409, "json": {"error.code": "key_reused"}},
         headers={"Idempotency-Key": "add-fern-1"}),
    get("still exactly one plant, read from storage", "/api/plants", {"status": 200, "json": {"plants": {"$len": 1}, "plants.0.name": "Boston fern", "plants.0.room": "Bathroom"}}),
    post("duplicate name refused (case and spaces ignored)", "/api/plants", {"name": "  boston   FERN ", "every_days": 4, "kind": "fern"},
         {"status": 409, "json": {"error.code": "duplicate_name", "error.fields.name": "is already used by another plant", "error.message": {"$contains": "Boston fern (Bathroom)"}, "error.request_id": {"$exists": True}}}),
    post("invalid fields named, each with a reason", "/api/plants", {"name": "", "every_days": "lots", "kind": "cactus", "colour": "green", "next_due": "2026-10-30"},
         {"status": 422, "json": {"error.code": "invalid", "error.fields.name": "is required", "error.fields.every_days": "must be a whole number of days from 1 to 60",
                                  "error.fields.kind": "must be one of the shapes shown", "error.fields.colour": "is not a plant field", "error.fields.next_due": "is set by the server"}}),
    post("true is not a number of days", "/api/plants", {"name": "X", "every_days": True, "kind": "fern"}, {"status": 422, "json": {"error.fields.every_days": {"$exists": True}}}),
    post("3.5 is not a whole number of days", "/api/plants", {"name": "X", "every_days": 3.5, "kind": "fern"}, {"status": 422, "json": {"error.fields.every_days": {"$exists": True}}}),
    post("text '7' is not a number", "/api/plants", {"name": "X", "every_days": "7", "kind": "fern"}, {"status": 422, "json": {"error.fields.every_days": {"$exists": True}}}),
    post("neighbour: 0 days refused", "/api/plants", {"name": "X", "every_days": 0, "kind": "fern"}, {"status": 422, "json": {"error.fields.every_days": {"$exists": True}}}),
    post("neighbour: 61 days refused", "/api/plants", {"name": "X", "every_days": 61, "kind": "fern"}, {"status": 422, "json": {"error.fields.every_days": {"$exists": True}}}),
    post("neighbour: 60 days and a 60-character name allowed", "/api/plants", {"name": "N" * 60, "room": "R" * 40, "every_days": 60, "kind": "tree"},
         {"status": 201, "json": {"every_days": 60}}, save={"edge": "id"}),
    post("neighbour: 1 day allowed", "/api/plants", {"name": "Maidenhair fern", "every_days": 1, "kind": "fern"}, {"status": 201, "json": {"every_days": 1}}),
    post("neighbour: 61-character name refused", "/api/plants", {"name": "M" * 61, "every_days": 5, "kind": "tree"}, {"status": 422, "json": {"error.fields.name": "must be 60 characters or fewer"}}),
    post("neighbour: 41-character room refused", "/api/plants", {"name": "Y", "room": "R" * 41, "every_days": 5, "kind": "tree"}, {"status": 422, "json": {"error.fields.room": "must be 40 characters or fewer"}}),
    get("invalid creates added nothing", "/api/today", {"status": 200, "json": {"counts.plants": 3}}),
    post("add Snake plant", "/api/plants", {"name": "Snake plant", "room": "Bedroom", "every_days": 14, "kind": "upright"}, {"status": 201}, save={"snake": "id"}),
    post("water Boston fern", "/api/plants/{fern}/waterings", {}, {"status": 201, "json": {"plant.status": "done", "plant.days_until": 3, "watering.local_date": {"$exists": True}}},
         headers={"Idempotency-Key": "water-fern-1"}, save={"wid": "watering.id", "today": "watering.local_date"}),
    get("watering shown back from storage", "/api/plants?limit=200", {"status": 200, "json": {"plants": {"$len": 4}}}),
    get("today counts the fern as done", "/api/today", {"status": 200, "json": {"counts.done": 1}}),
    post("second watering the same day refused", "/api/plants/{fern}/waterings", {},
         {"status": 409, "json": {"error.code": "already_watered", "error.message": {"$contains": "Boston fern was already watered today at"}}}),
    post("retry of the first watering replays, no refusal", "/api/plants/{fern}/waterings", {}, {"status": 201, "headers": {"Idempotent-Replay": "true"}},
         headers={"Idempotency-Key": "water-fern-1"}),
    post("a client-set watering time is refused", "/api/plants/{snake}/waterings", {"watered_at": "2026-01-01T00:00:00Z"},
         {"status": 422, "json": {"error.fields.watered_at": "is set by the server"}}),
    post("watering an unknown plant", "/api/plants/999999/waterings", {}, {"status": 404, "json": {"error.code": "not_found"}}),
    {"name": "20 ticks of one plant at once: exactly one lands", "method": "POST", "path": "/api/plants/{snake}/waterings", "json": {}, "parallel": 20,
     "expect": {"status_counts": {"201": 1, "409": 19}}},
    get("snake plant watered once", "/api/today", {"status": 200, "json": {"counts.done": 2}}),
    {"name": "undo the fern's watering", "method": "DELETE", "path": "/api/waterings/{wid}", "expect": {"status": 200, "json": {"plant.status": "due", "plant.watering_today_id": None}}},
    {"name": "undo again: gone", "method": "DELETE", "path": "/api/waterings/{wid}", "expect": {"status": 404, "json": {"error.code": "not_found"}}},
    post("foreign Host refused", "/api/plants", {"name": "Evil fern", "every_days": 3, "kind": "fern"}, {"status": 403, "json": {"error.code": "bad_host"}},
         headers={"Host": "evil.example"}),
    {"name": "text/plain write refused", "method": "POST", "path": "/api/plants", "headers": {"Content-Type": "text/plain"},
     "raw": "{\"name\": \"Evil fern\", \"every_days\": 3, \"kind\": \"fern\"}", "expect": {"status": 415, "json": {"error.code": "not_json"}}},
    get("refused writes changed nothing", "/api/today", {"status": 200, "json": {"counts.plants": 4}}),
    {"name": "cross-origin preflight gets no CORS", "method": "OPTIONS", "path": "/api/plants",
     "headers": {"Origin": "https://evil.example", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
     "expect": {"status": 204, "headers": {"Access-Control-Allow-Origin": {"$absent": True}}}},
    get("cross-origin read gets no CORS", "/api/plants", {"status": 200, "headers": {"Access-Control-Allow-Origin": {"$absent": True}}}, headers={"Origin": "https://evil.example"}),
    {"name": "malformed JSON", "method": "POST", "path": "/api/plants", "headers": J, "raw": "{\"name\": ", "expect": {"status": 400, "json": {"error.code": "bad_json"}}},
    {"name": "a JSON list is not an object", "method": "POST", "path": "/api/plants", "headers": J, "raw": "[1,2]", "expect": {"status": 400, "json": {"error.code": "bad_json"}}},
    {"name": "oversized body", "method": "POST", "path": "/api/plants", "headers": J, "raw": "{\"name\": \"" + "x" * 20000 + "\"}", "expect": {"status": 413, "json": {"error.code": "too_large"}}},
    get("unknown route answers in the error shape", "/api/nothing", {"status": 404, "json": {"error.code": "not_found"}}),
    {"name": "wrong method", "method": "PUT", "path": "/api/plants", "json": {}, "expect": {"status": 405, "json": {"error.code": "method_not_allowed"}}},
    get("a fault inside the server: 500 in the error shape, nothing internal", "/api/_fault",
        {"status": 500, "json": {"error.code": "server_fault", "error.request_id": "fault-check-1",
                                 "error.message": {"$not_contains": "SELECT"}}}, headers={"X-Request-Id": "fault-check-1"}),
    {"name": "fault body leaks no path or traceback", "method": "GET", "path": "/api/_fault",
     "expect": {"status": 500, "json": {"error.message": {"$not_contains": "/srv"}, "error.code": {"$not_contains": "Traceback"}}, "headers": {"X-Request-Id": {"$exists": True}}}},
    get("page 1 of 2", "/api/plants?limit=2", {"status": 200, "json": {"plants": {"$len": 2}, "next": {"$exists": True}}}, save={"cur": "next"}),
    get("page 2 of 2", "/api/plants?limit=2&after={cur}", {"status": 200, "json": {"plants": {"$len": 2}, "next": None}}),
    get("limit 0 refused", "/api/plants?limit=0", {"status": 422, "json": {"error.fields.limit": {"$exists": True}}}),
    get("limit 201 refused", "/api/plants?limit=201", {"status": 422, "json": {"error.fields.limit": {"$exists": True}}}),
    get("a made-up cursor refused", "/api/plants?after=bm9wZQ", {"status": 422, "json": {"error.fields.after": {"$exists": True}}}),
    post("water the fern again before the restart", "/api/plants/{fern}/waterings", {}, {"status": 201}, headers={"Idempotency-Key": "water-fern-2"}),
    {"restart": True},
    get("plants survived the restart", "/api/plants?limit=200", {"status": 200, "json": {"plants": {"$len": 4}}}),
    get("waterings survived the restart", "/api/today", {"status": 200, "json": {"counts.plants": 4, "counts.done": 2}}),
    post("same-day rule survived the restart", "/api/plants/{fern}/waterings", {}, {"status": 409, "json": {"error.code": "already_watered"}}),
    post("the create key survived the restart", "/api/plants", FERN, {"status": 201, "headers": {"Idempotent-Replay": "true"}}, headers={"Idempotency-Key": "add-fern-1"}),
]
(HERE / "api-steps.json").write_text(json.dumps(steps, indent=1))

# Clock: Brisbane is UTC+10 with no daylight saving. 13:59:59Z is 23:59:59 on the 23rd; 14:00Z is the 24th.
clock_a = [
    get("frozen clock is reported", "/api/today", {"status": 200, "json": {"today": "2026-10-23", "frozen": True}}),
]
clock_b = [
    get("one second later it is the next day in Brisbane", "/api/today", {"status": 200, "json": {"today": "2026-10-24", "frozen": True}}),
    post("add Peace lily", "/api/plants", {"name": "Peace lily", "every_days": 5, "kind": "flower"}, {"status": 201, "json": {"next_due": "2026-10-24", "status": "due"}}, save={"lily": "id"}),
    post("water it: stored as the instant, dated by Brisbane", "/api/plants/{lily}/waterings", {},
         {"status": 201, "json": {"watering.watered_at": "2026-10-23T14:00:00Z", "watering.local_date": "2026-10-24", "plant.next_due": "2026-10-29"}}),
    get("next seven days: due again on the 29th", "/api/today", {"status": 200, "json": {"week.0.date": "2026-10-24", "week.5.date": "2026-10-29", "week.5.due": 1, "week.4.due": 0}}),
]
(HERE / "api-clock-a.json").write_text(json.dumps(clock_a, indent=1))
(HERE / "api-clock-b.json").write_text(json.dumps(clock_b, indent=1))
print("wrote", len(steps), "main steps")
