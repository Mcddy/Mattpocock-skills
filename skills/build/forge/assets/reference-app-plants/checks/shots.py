"""Captures the chosen direction (fresh-green) at 390 x 844 (2x) and 1280 x 800 for each state.
Usage: python3 checks/shots.py PORT   (a server started by the caller on data/shots.db; this script reseeds it)"""
import json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(sys.argv[1])
BASE = f"http://127.0.0.1:{PORT}"
OUT = ROOT / "shots"
OUT.mkdir(exist_ok=True)
DB = ROOT / "data/shots.db"


def reseed(empty=False):
    for f in DB.parent.glob("shots.db*"):
        f.unlink()
    if empty:
        subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, '{ROOT}/app'); import server; server.migrate('{DB}')"], check=True)
    else:
        subprocess.run([sys.executable, str(ROOT / "checks/seed_sample.py"), str(DB)], check=True, capture_output=True)


def api_water(page, name):
    plants = page.request.get(BASE + "/api/plants?limit=200").json()["plants"]
    pid = next(p["id"] for p in plants if p["name"] == name)
    return page.request.post(BASE + f"/api/plants/{pid}/waterings", data=json.dumps({}), headers={"Content-Type": "application/json"}).status


def press(page, label):
    page.click(f'button[aria-label="{label}"]')
    page.wait_for_timeout(750)


STATES = {
    "populated": (False, lambda pg: None),
    "empty": (True, lambda pg: None),
    "success-ticked": (False, lambda pg: press(pg, "Watered Boston fern")),
    "refused-already-watered": (False, lambda pg: (api_water(pg, "Monstera"), press(pg, "Watered Monstera"))),
    "refused-duplicate-name": (False, lambda pg: (pg.click("#add-open"), pg.fill("#f-name", "monstera"), pg.click('[data-every="7"]'), pg.check("#k-split"), pg.click("#add-go"), pg.wait_for_timeout(600))),
    "error-load": (False, lambda pg: (pg.evaluate("async () => { window.fetch = () => Promise.reject(new TypeError('blocked')); S.phase = 'loading'; await loadAll(); }"), pg.wait_for_timeout(300))),
    "success-all-watered": (False, None),
}

SHEET = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for state, (empty, act) in STATES.items():
        for kind, vp, scale in (("390", {"width": 390, "height": 844}, 2), ("1280", {"width": 1280, "height": 800}, 1)):
            reseed(empty)
            ctx = b.new_context(viewport=vp, device_scale_factor=scale, locale="en-AU", timezone_id="Australia/Brisbane")
            pg = ctx.new_page()
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            if state == "success-all-watered":
                pg.goto(BASE + "/"); pg.wait_for_timeout(600)
                for pl in pg.request.get(BASE + "/api/plants?limit=200").json()["plants"]:
                    if pl["status"] in ("due", "overdue"):
                        api_water(pg, pl["name"])
            pg.goto(BASE + "/"); pg.wait_for_load_state("load"); pg.wait_for_timeout(700)
            if act:
                act(pg)
            # bring the changed thing into view on the phone
            if kind == "390":
                target = {"success-ticked": '[aria-label="Undo watering Boston fern"]', "refused-already-watered": ".rowmsg",
                          "refused-duplicate-name": "#e-name"}.get(state)
                if target:
                    pg.locator(target).first.scroll_into_view_if_needed(); pg.evaluate("() => window.scrollBy(0, 180)"); pg.wait_for_timeout(200)
            if kind == "1280" and state == "refused-duplicate-name":
                pg.locator("#add-msg").scroll_into_view_if_needed(); pg.wait_for_timeout(200)
            pg.screenshot(path=str(OUT / f"{state}-{kind}.png"))
            if state == "populated" and kind == "390":
                pg.screenshot(path=str(OUT / "populated-390-fullpage.png"), full_page=True)
            print(state, kind, "errors:", errors, "| status:", pg.evaluate("() => document.getElementById('status').textContent"), "| rowmsg:", pg.evaluate("() => [...document.querySelectorAll('.rowmsg, #add-msg, #e-name')].map(e => e.textContent).filter(Boolean).join(' / ')"))
            if kind == "390":
                SHEET.append("=== " + state + "\n" + pg.inner_text("body"))
            ctx.close()
    b.close()
(ROOT / "checks/string-sheet.txt").write_text("\n\n".join(SHEET))
