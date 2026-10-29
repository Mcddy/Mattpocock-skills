#!/usr/bin/env python3
"""Find controls on a page that do nothing when used.

Usage:
  python dead_controls.py PAGE [--width 1100] [--height 800] [--limit 60] [--prep-js "JS"] [--keyboard] [--json]

--prep-js runs after every fresh load, before controls are listed or tried: use it to reach a populated state
(load sample data, open a panel). It must be repeatable, because it runs once per control.

PAGE is an HTML file or an http(s) address.

Why this exists: a page can look finished and be a shell. Buttons with no handler, menu items that
go nowhere and "Export" links that point at "#" all survive a source scan and a screenshot. The
only way to find them is to use them. This script loads the page fresh for each control, activates
it once, and watches for any effect: a change to the page, a network request, a move of keyboard
focus, a change of address, a download or a dialog.

WARNING. It clicks every button and link it finds, including ones that delete or send. Run it only
against a throwaway copy with throwaway data. Never point it at a live system.

A control reported as NO OBSERVABLE EFFECT is a candidate, not a verdict. Three honest reasons a
working control lands there: it needs other input first (a Save with an empty form may rightly do
nothing, though it should say why), its effect is outside the page (a copy to the clipboard with no
confirmation, which is itself worth fixing), or it only works after a step this script does not
take. Read each one. A page where most controls have no effect is a mock-up, whatever it looks like.

Two keyboard checks (forge 3.3):
  MOUSE ONLY  Always run. An element that changes something when clicked but is not a Tab stop (a table row, a
              header cell, a card, or a control with tabindex="-1"): a click handler on the element itself, an
              onclick attribute, or a pointer cursor that a handler on a parent answers (delegated handling). It
              is reported only when a fresh click really has an effect, and never when the element holds or sits
              inside a control that is a Tab stop. tabindex="-1" is not a fault in itself: inside a composite widget
              (radio group, tab list, listbox, menu, tree, grid, toolbar) items are reached with arrow keys from one
              Tab stop (roving tabindex or aria-activedescendant). For those the script focuses the widget's Tab stop
              and presses the arrow keys: reached is OK; not reached is UNRESOLVED (partial coverage, read it), not a
              verdict. MOUSE ONLY means no Tab stop and no composite path.
              Fix: a native <button> inside it (in a sortable header: <th aria-sort><button>), not tabindex on a row.
  --keyboard  Also activates each Tab-stop control from the keyboard, with the activation keys for its role (W3C
              ARIA APG): Enter for links; Enter and Space for buttons and summary; Space for checkboxes, switches and
              radios (Enter is optional for a switch; moving through a radio group with arrows is navigation, not
              activation); Enter for menu items. Tabs are not tested (activation varies by design). A control whose
              click had an effect and whose key press had none, apart from background requests, is CLICK ONLY.
              Doubles the run time.

Limits: one activation per control, from the page's starting state. Controls that appear only after
another action are not reached. Text fields, selects and sliders are not exercised.

Needs the Python "playwright" package and a Chromium it can launch.
Exit codes (references/results.md): 0 completed (it ran; candidates are listed, not verdicts). 2 usage error.
3 partial: a composite item's keyboard path could not be shown (UNRESOLVED), a control could not be clicked, a
listed control was not present on a fresh load (it was never tried), some controls were over --limit, or nothing
was activated.
4 runner error (prints NOT RUN: no playwright, no Chromium, or the page would not load). A RECEIPT line on
stderr states the result, the controls tried and the candidates, in every case.
"""
import json
import sys
from pathlib import Path
import pathlib

VERSION = "forge 3.3.2"

FLAGS = {"--json", "--keyboard"}
VALUES = {"--width", "--height", "--limit"}

LIST_JS = r"""
() => {
  const sel = 'button, [role=button], [role=tab], [role=menuitem], [role=menuitemcheckbox], [role=menuitemradio], [role=switch], [role=checkbox], [role=radio], [role=option], a[href], summary, input[type=button], input[type=submit], input[type=checkbox], input[type=radio]';
  const out = [];
  [...document.querySelectorAll(sel)].forEach((e, i) => {
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    if (cs.display === 'none' || cs.visibility !== 'visible' || r.width === 0 || r.height === 0) return;
    if (e.disabled || e.getAttribute('aria-disabled') === 'true') return;
    const href = e.tagName === 'A' ? (e.getAttribute('href') || '') : null;
    const label = (e.getAttribute('aria-label') || e.textContent || e.value || e.getAttribute('title') || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    const tag = e.tagName.toLowerCase(), type = (e.getAttribute('type') || '').toLowerCase();
    const role = e.getAttribute('role') || (tag === 'a' ? 'link' : tag === 'summary' ? 'summary' : tag === 'input' ? (type === 'checkbox' ? 'checkbox' : type === 'radio' ? 'radio' : 'button') : 'button');
    out.push({index: i, tag, role, label, href, reachable: e.tabIndex >= 0, external: href !== null && /^(https?:)?\/\//.test(href) && !href.startsWith(location.origin)});
  });
  return out;
}
"""

ARM_JS = r"""
(i) => {
  const sel = 'button, [role=button], [role=tab], [role=menuitem], [role=menuitemcheckbox], [role=menuitemradio], [role=switch], [role=checkbox], [role=radio], [role=option], a[href], summary, input[type=button], input[type=submit], input[type=checkbox], input[type=radio]';
  const e = document.querySelectorAll(sel)[i];
  if (!e) return false;
  e.setAttribute('data-dc-target', '1');
  const bare = u => u.replace(/#$/, '');
  window.__dc = {mut: 0, target: e, focus0: document.activeElement, url0: bare(location.href), bare, dialogs: 0};
  ['alert', 'confirm', 'prompt'].forEach(n => { window[n] = () => { window.__dc.dialogs++; return n === 'confirm'; }; });
  // any change to the page counts, including the control marking itself as pressed
  new MutationObserver(list => { window.__dc.mut += list.length; })
    .observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
  return true;
}
"""

READ_JS = r"""
() => {
  const d = window.__dc; if (!d) return {gone: true};
  const a = document.activeElement;
  return {mut: d.mut, dialogs: d.dialogs, url: d.bare(location.href) !== d.url0,
          focus: a !== d.focus0 && a !== d.target && a !== document.body,
          checked: d.target.checked === true};
}
"""


MOUSE_ONLY_JS = r"""
(limit) => {
  // An element can be clicked but not reached with Tab when its tabIndex is negative (no tabindex on a non-control,
  // or tabindex="-1"). Elements inside or holding a Tab-reachable control are skipped: the control is the way in.
  const interactive = 'a[href],button,input,select,textarea,summary,[contenteditable=""],[contenteditable=true],iframe,audio[controls],video[controls],[role],[tabindex]';
  const reach = el => el.tabIndex >= 0 && !el.disabled && !el.closest('[inert]') && el.matches(interactive);
  const composite = '[role=radiogroup],[role=tablist],[role=listbox],[role=menu],[role=menubar],[role=tree],[role=grid],[role=treegrid],[role=toolbar]';
  const out = [];
  const all = [...document.body.querySelectorAll('*')];
  for (let i = 0; i < all.length && out.length < limit; i++) {
    const e = all[i];
    if (e.closest('svg') && e.tagName.toLowerCase() !== 'svg') continue;
    if (/^(SCRIPT|STYLE|TEMPLATE|HTML|BODY|MAIN|LABEL|OPTION)$/.test(e.tagName) || e.closest('label')) continue;
    let anc = e, inReach = false;
    while (anc && anc !== document.body) { if (reach(anc)) { inReach = true; break; } anc = anc.parentElement; }
    if (inReach || [...e.querySelectorAll(interactive)].some(reach)) continue;
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    if (cs.display === 'none' || cs.visibility !== 'visible' || r.width < 4 || r.height < 4) continue;
    const parentPointer = e.parentElement && getComputedStyle(e.parentElement).cursor === 'pointer';
    const pointer = cs.cursor === 'pointer' && !parentPointer;      // the outermost pointer element only
    const attr = e.hasAttribute('onclick');
    const c = e.closest(composite);
    out.push({index: i, tag: e.tagName.toLowerCase(), role: e.getAttribute('role'), pointer, attr, tabindex: e.getAttribute('tabindex'),
              composite: c ? [...document.body.querySelectorAll('*')].indexOf(c) : null, compositeRole: c ? c.getAttribute('role') : null,
              label: (e.getAttribute('aria-label') || e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)});
  }
  return out;
}
"""

ARM_ANY_JS = r"""
(i) => {
  const e = document.body.querySelectorAll('*')[i];
  if (!e) return false;
  e.setAttribute('data-dc-target', '1');
  const bare = u => u.replace(/#$/, '');
  window.__dc = {mut: 0, target: e, focus0: document.activeElement, url0: bare(location.href), bare, dialogs: 0};
  ['alert', 'confirm', 'prompt'].forEach(n => { window[n] = () => { window.__dc.dialogs++; return n === 'confirm'; }; });
  new MutationObserver(list => { window.__dc.mut += list.filter(m => !(m.type === 'attributes' && m.attributeName === 'data-dc-target')).length; })
    .observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
  return true;
}
"""


def own_click_listeners(page, indexes):
    """Indexes (from MOUSE_ONLY_JS) of elements with a click, mousedown, mouseup or pointer listener of their own."""
    if not indexes:
        return set()
    try:
        cdp = page.context.new_cdp_session(page)
    except Exception:  # noqa: BLE001  not Chromium: fall back to cursor and onclick only
        return set()
    found = set()
    for i in indexes:
        try:
            obj = cdp.send("Runtime.evaluate", {"expression": "document.body.querySelectorAll('*')[%d]" % i})["result"]
            if "objectId" not in obj:
                continue
            ls = cdp.send("DOMDebugger.getEventListeners", {"objectId": obj["objectId"]})["listeners"]
            if any(x["type"] in ("click", "mousedown", "mouseup", "pointerdown", "pointerup") for x in ls):
                found.add(i)
        except Exception:  # noqa: BLE001
            continue
    return found


def fresh(ctx, uri, prep):
    pg = ctx.new_page()
    pg.goto(uri, timeout=10000)
    pg.wait_for_timeout(450)
    if prep:
        pg.evaluate("async () => { %s\n }" % prep); pg.wait_for_timeout(400)
    return pg


def effects_of(pg, events):
    got = pg.evaluate(READ_JS)
    eff = []
    if got.get("gone") or got.get("url"):
        eff.append("the address changed")
    if got.get("mut"):
        eff.append("the page changed")
    if got.get("focus"):
        eff.append("focus moved")
    if got.get("checked"):
        eff.append("it became checked")
    if got.get("dialogs"):
        eff.append("it opened a browser dialog")
    if events["req"]:
        eff.append("%d request(s)" % events["req"])
    return eff


def mouse_only(ctx, uri, prep, limit):
    """Elements that are not controls and cannot take focus, yet change the page when clicked."""
    pg = fresh(ctx, uri, prep)
    cands = pg.evaluate(MOUSE_ONLY_JS, 1500)
    probe = [c["index"] for c in cands if not (c["pointer"] or c["attr"])]
    own = own_click_listeners(pg, probe[:600])
    pg.close()
    cands = [c for c in cands if c["pointer"] or c["attr"] or c["index"] in own][:limit]
    found = []
    for c in cands:
        events = {"req": 0}
        pg = fresh(ctx, uri, prep)
        try:
            if not pg.evaluate(ARM_ANY_JS, c["index"]):
                pg.close(); continue
            pg.on("request", lambda q, ev=events: ev.__setitem__("req", ev["req"] + 1))
            pg.locator("[data-dc-target]").first.click(timeout=2500)
            pg.wait_for_timeout(400)
            eff = effects_of(pg, events)
        except Exception as e:  # noqa: BLE001
            msg = str(e).split("\n")[0]
            eff = ["the address changed"] if ("context was destroyed" in msg or "navigation" in msg.lower()) else []
        pg.close()
        if eff:
            item = {"index": c["index"], "tag": c["tag"], "role": c["role"], "label": c["label"] or "(no text)", "effects": eff,
                    "why": "own click handler" if c["index"] in own else ("onclick attribute" if c["attr"] else "pointer cursor")}
            if c["composite"] is not None:
                item["composite"] = c["compositeRole"]
                item["keyboard_path"] = composite_path(ctx, uri, prep, c["composite"], c["index"])
            else:
                item["keyboard_path"] = "none: not reachable with Tab and not part of a composite widget"
            found.append(item)
    # a container whose handler answers clicks on children that are themselves reported (delegated handling) is not
    # reported twice: the children are the things a person tries to use
    if found:
        pg = fresh(ctx, uri, prep)
        idx = [f["index"] for f in found]
        inner = set(pg.evaluate("""(idx) => { const all = document.body.querySelectorAll('*');
            return idx.filter(i => idx.some(j => j !== i && all[i].contains(all[j]))); }""", idx))
        pg.close()
        found = [f for f in found if f["index"] not in inner]
    return found, len(cands)


COMPOSITE_ENTRY_JS = r"""
(ci) => {
  const all = document.body.querySelectorAll('*'), c = all[ci];
  if (!c) return null;
  const reach = el => el.tabIndex >= 0 && !el.disabled;
  if (reach(c) && c.hasAttribute('aria-activedescendant')) { c.setAttribute('data-dc-entry', '1'); return 'container'; }
  const m = [...c.querySelectorAll('*')].find(reach);
  if (m) { m.setAttribute('data-dc-entry', '1'); return 'member'; }
  if (reach(c)) { c.setAttribute('data-dc-entry', '1'); return 'container'; }
  return null;
}
"""
AT_TARGET_JS = r"""
(args) => { const all = document.body.querySelectorAll('*'), c = all[args[0]], t = all[args[1]];
  return document.activeElement === t || (!!t.id && !!c && c.getAttribute('aria-activedescendant') === t.id); }
"""


def composite_path(ctx, uri, prep, ci, ti):
    """Whether keyboard focus (or aria-activedescendant) reaches item ti from the composite's Tab stop with arrow keys."""
    for key in ("ArrowRight", "ArrowDown"):
        pg = fresh(ctx, uri, prep)
        try:
            entry = pg.evaluate(COMPOSITE_ENTRY_JS, ci)
            if entry is None:
                pg.close()
                return "none: the composite widget has no Tab stop"
            pg.locator("[data-dc-entry]").first.focus(timeout=2500)
            for _ in range(40):
                if pg.evaluate(AT_TARGET_JS, [ci, ti]):
                    pg.close()
                    return "reached with Tab, then %s" % key
                pg.keyboard.press(key)
                pg.wait_for_timeout(40)
        except Exception:  # noqa: BLE001
            pass
        pg.close()
    return "unresolved: the composite has a Tab stop, but arrow keys did not reach this item"


def key_effect(ctx, uri, prep, index, tag, key):
    events = {"req": 0}
    pg = fresh(ctx, uri, prep)
    try:
        if not pg.evaluate(ARM_JS, index):
            pg.close(); return None
        pg.on("request", lambda q, ev=events: ev.__setitem__("req", ev["req"] + 1))
        pg.locator("[data-dc-target]").first.focus(timeout=2500)
        pg.evaluate("() => { window.__dc.mut = 0; window.__dc.focus0 = document.activeElement; }")
        pg.keyboard.press(key)
        pg.wait_for_timeout(400)
        eff = effects_of(pg, events)
    except Exception as e:  # noqa: BLE001
        msg = str(e).split("\n")[0]
        eff = ["the address changed"] if ("context was destroyed" in msg or "navigation" in msg.lower()) else []
    pg.close()
    return eff


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    flags, opts, args, it = set(), {}, [], iter(argv)
    prep = None
    for a in it:
        if a == "--prep-js":
            prep = next(it, None)
            if not prep:
                print("dead_controls: --prep-js needs JavaScript to run", file=sys.stderr)
                return 2
        elif a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip().isdigit() or int(v) <= 0:
                print("dead_controls: %s needs a positive whole number" % a, file=sys.stderr)
                return 2
            opts[a] = int(v)
        elif a.startswith("--"):
            print("dead_controls: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    served = args[0].lower().startswith(("http://", "https://"))
    if not served and not Path(args[0]).is_file():
        print("dead_controls: cannot read " + args[0], file=sys.stderr)
        return 2
    uri = args[0] if served else Path(args[0]).resolve().as_uri()
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % str(e)[:80])
        return 4
    rows = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e)[:120])
            return 4
        ctx = browser.new_context(viewport={"width": opts.get("--width", 1100), "height": opts.get("--height", 800)}, accept_downloads=True)
        page = ctx.new_page()
        try:
            page.goto(uri, timeout=10000)
            page.wait_for_timeout(500)
            if prep:
                page.evaluate("async () => { %s\n }" % prep); page.wait_for_timeout(400)
            controls = page.evaluate(LIST_JS)
        except Exception as e:  # noqa: BLE001
            browser.close()
            print("NOT RUN: the page did not load (%s)" % str(e).split("\n")[0][:120])
            return 4
        total = len(controls)
        for c in controls[: opts.get("--limit", 60)]:
            row = {"label": c["label"] or "(no label)", "tag": c["tag"], "role": c["role"], "effects": [], "outcome": "activated"}
            if c["external"]:
                row["outcome"] = "external link, not followed"
                rows.append(row)
                continue
            if c["href"] is not None and c["href"].strip() in ("", "#", "javascript:void(0)", "javascript:;"):
                row["note"] = 'href is "%s"' % c["href"]
            events = {"req": 0, "download": 0, "popup": 0}
            pg = ctx.new_page()
            try:
                pg.goto(uri, timeout=10000)
                pg.wait_for_timeout(450)
                if prep:
                    pg.evaluate("async () => { %s\n }" % prep); pg.wait_for_timeout(400)
                if not pg.evaluate(ARM_JS, c["index"]):
                    row["outcome"] = "not present on a fresh load"
                    rows.append(row)
                    pg.close()
                    continue
                pg.on("request", lambda q, ev=events: ev.__setitem__("req", ev["req"] + 1))
                pg.on("download", lambda d, ev=events: ev.__setitem__("download", ev["download"] + 1))
                pg.on("popup", lambda w, ev=events: ev.__setitem__("popup", ev["popup"] + 1))
                pg.locator("[data-dc-target]").first.click(timeout=2500)
                pg.wait_for_timeout(450)
                got = pg.evaluate(READ_JS)
            except Exception as e:  # noqa: BLE001
                msg = str(e).split("\n")[0]
                if "context was destroyed" in msg or "navigation" in msg.lower():
                    got = {"gone": True}
                else:
                    row["outcome"] = "could not be clicked (%s)" % msg[:60]
                    rows.append(row)
                    pg.close()
                    continue
            if got.get("gone") or got.get("url"):
                row["effects"].append("the address changed")
            if got.get("mut"):
                row["effects"].append("the page changed")
            if got.get("focus"):
                row["effects"].append("focus moved")
            if got.get("checked"):
                row["effects"].append("it became checked")
            if got.get("dialogs"):
                row["effects"].append("it opened a browser dialog (blocked in sandboxed frames)")
            if events["req"]:
                row["effects"].append("%d request(s)" % events["req"])
            if events["download"]:
                row["effects"].append("a download")
            if events["popup"]:
                row["effects"].append("a new window")
            rows.append(row)
            pg.close()
        mouse, probed = mouse_only(ctx, uri, prep, opts.get("--limit", 60))
        click_only, keyboard_untested = [], []
        if "--keyboard" in flags:
            # Activation keys by role (W3C ARIA APG): link Enter; button and summary Enter and Space; checkbox, switch
            # and radio Space (Enter is optional for a switch; arrow-key movement in a radio group is group navigation,
            # checked separately by reach, not here); menuitem Enter. Tabs activate on focus or on a key depending on
            # the design, so they are not tested here.
            KEYS = {"link": ["Enter"], "button": ["Enter", "Space"], "summary": ["Enter", "Space"], "checkbox": ["Space"],
                    "switch": ["Space"], "radio": ["Space"], "menuitem": ["Enter"], "menuitemcheckbox": ["Space"], "menuitemradio": ["Space"]}
            for c, r in zip(controls, rows):
                if r["outcome"] != "activated" or not r["effects"]:
                    continue
                keys = KEYS.get(c["role"])
                if keys is None:
                    keyboard_untested.append({"role": c["role"], "label": r["label"]})
                    continue
                if not c["reachable"]:
                    keyboard_untested.append({"role": c["role"], "label": r["label"], "why": "not a Tab stop; reach is reported by the MOUSE ONLY scan"})
                    continue
                click_requests = any(x.endswith("request(s)") for x in r["effects"])
                for k in keys:
                    eff = key_effect(ctx, uri, prep, c["index"], c["tag"], k)
                    if eff is None:
                        continue
                    # background traffic alone does not show the key did what the click did
                    real = [x for x in eff if not x.endswith("request(s)")] or ([x for x in eff if x.endswith("request(s)")] if click_requests else [])
                    if not real:
                        click_only.append({"tag": c["tag"], "role": c["role"], "label": r["label"], "key": k})
        browser.close()
    activated = [r for r in rows if r["outcome"] == "activated"]
    dead = [r for r in activated if not r["effects"]]
    mouse_only_rows = [m for m in mouse if m["keyboard_path"].startswith("none")]
    unresolved = [m for m in mouse if m["keyboard_path"].startswith("unresolved")]
    via_composite = [m for m in mouse if m["keyboard_path"].startswith("reached")]
    RECEIPT.update({"page": args[0], "controls_found": total, "activated": len(activated),
                    "external_not_followed": sum(1 for r in rows if r["outcome"] == "external link, not followed"),
                    "absent_on_fresh_load": sum(1 for r in rows if r["outcome"] == "not present on a fresh load"),
                    "could_not_click": sum(1 for r in rows if r["outcome"].startswith("could not")),
                    "untested_over_limit": total - len(rows), "no_effect": len(dead),
                    "click_effect_scan": {"candidates_clicked": probed, "mouse_only": len(mouse_only_rows),
                                          "reached_via_composite": len(via_composite), "unresolved_composite": len(unresolved)},
                    "keyboard_activation": ({"click_only": len(click_only), "not_tested": len(keyboard_untested)} if "--keyboard" in flags else "not requested"),
                    "meaning": "candidates to read, not verdicts; an effect is an observable change, not proof the promised action worked"})
    if "--json" in flags:
        text = json.dumps({"page": args[0], "controls_found": total, "activated": len(activated), "no_effect": dead, "all": rows,
                           "mouse_only": mouse_only_rows, "reached_via_composite": via_composite, "unresolved_composite": unresolved,
                           "click_only": click_only if "--keyboard" in flags else None,
                           "keyboard_not_tested": keyboard_untested if "--keyboard" in flags else None}, indent=1, ensure_ascii=True)
    else:
        skipped = len(rows) - len(activated)
        L = ["dead_controls: %s: %d control(s) found, %d activated, %d skipped (external, absent or unclickable), %d not tried; %d with no observable effect"
             % (args[0] if served else Path(args[0]).name, total, len(activated), skipped, total - len(rows), len(dead))]
        for r in rows:
            if r["outcome"] != "activated":
                L.append("  SKIPPED     %-8s %r: %s" % (r["tag"], r["label"], r["outcome"]))
        for r in dead:
            L.append("  NO OBSERVABLE EFFECT  %-8s %r%s" % (r["tag"], r["label"], ("  (" + r["note"] + ")") if r.get("note") else ""))
        for m in mouse_only_rows:
            L.append("  MOUSE ONLY  %-8s %r: %s on click (%s); keyboard path %s" % (m["tag"], m["label"], ", ".join(m["effects"]), m["why"], m["keyboard_path"]))
        for m in unresolved:
            L.append("  UNRESOLVED  %-8s %r in a %s: %s" % (m["tag"], m["label"], m.get("composite"), m["keyboard_path"]))
        for m in via_composite:
            L.append("  OK          %-8s %r in a %s: %s" % (m["tag"], m["label"], m.get("composite"), m["keyboard_path"]))
        for c in click_only:
            L.append("  CLICK ONLY  %-8s %r (%s): works by click, nothing observable on %s" % (c["tag"], c["label"], c["role"], c["key"]))
        if total > len(rows):
            L.append("  %d control(s) were not tried (raise --limit)." % (total - len(rows)))
        if not activated:
            L.append("  No control was activated, so this says nothing about the page.")
        elif len(dead) * 2 > len(activated):
            L.append("  More than half the controls do nothing. That is a mock-up, not a working page.")
        L.append("Each control was tried once from a fresh load. A control with no effect is a candidate: read it before calling it dead.")
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    # coverage gaps make the run partial: composite items whose keyboard path could not be shown, controls that
    # could not be clicked, were absent on a fresh load or were over the limit, or nothing activated at all
    if (unresolved or (total - len(rows)) or not activated
            or any(r["outcome"].startswith("could not") or r["outcome"] == "not present on a fresh load" for r in rows)):
        return 3
    return 0

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
    sys.exit(_contract("dead_controls", main, sys.argv[1:]))
