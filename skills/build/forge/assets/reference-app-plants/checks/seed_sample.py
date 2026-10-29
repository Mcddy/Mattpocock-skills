"""Sample data for screenshots and the direction board only (a throwaway file, never the user's plants).
Fifteen plants, waterings backdated relative to today in Brisbane, so the round shows its busiest case:
overdue, due, watered today, coming up, and the longest name."""
import datetime as dt, sqlite3, sys
sys.path.insert(0, __file__.rsplit('/checks/', 1)[0] + '/app')
import server

db = sys.argv[1]
server.migrate(db)
today = server.local_today()
PLANTS = [  # name, room, every_days, kind, days since last watering (0 = today, None = never)
    ("Monstera", "Lounge", 7, "split", 7), ("Boston fern", "Bathroom", 3, "fern", 5), ("Maidenhair fern", "Bathroom", 3, "fern", 3),
    ("Snake plant", "Bedroom", 14, "upright", 6), ("ZZ plant", "Hallway", 14, "upright", 12), ("Chinese money plant", "Kitchen windowsill", 7, "round", 8),
    ("Golden pothos", "Kitchen", 7, "trailing", 2), ("Fiddle-leaf fig", "Lounge", 7, "tree", 0), ("Rubber plant", "Study", 10, "tree", 4),
    ("Aloe vera", "Kitchen windowsill", 14, "spiky", 13), ("Peace lily", "Lounge", 5, "flower", 5), ("Calathea orbifolia", "Bedroom", 4, "round", 4),
    ("String of pearls", "Study", 10, "trailing", 1), ("Philodendron 'Pink Princess' by the big lounge window", "Lounge", 6, "split", 6),
    ("Bird of paradise", "Balcony door", 7, "tree", 0),
]
c = server.connect(db)
c.execute("BEGIN")
for i, (name, room, every, kind, ago) in enumerate(PLANTS):
    p = server.validate_plant({"name": name, "room": room, "every_days": every, "kind": kind})
    cur = c.execute("INSERT INTO plant (name, name_key, room, every_days, kind, created_at) VALUES (?,?,?,?,?,?)",
                    (p["name"], p["name_key"], p["room"], p["every_days"], p["kind"], "2026-09-01T00:00:00Z"))
    if ago is not None:
        d = today - dt.timedelta(days=ago)
        local = dt.datetime(d.year, d.month, d.day, 7, 12 + i % 9, tzinfo=server.ZONE)
        c.execute("INSERT INTO watering (plant_id, watered_at, local_date) VALUES (?,?,?)", (cur.lastrowid, server.iso_instant(local), d.isoformat()))
c.execute("COMMIT")
print("seeded", len(PLANTS), "plants for", today)
