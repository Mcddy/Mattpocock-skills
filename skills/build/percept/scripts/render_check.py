"""Rendered check for a percept course file, in a real browser.

Usage:
    python3 percept_render_check.py COURSE.html [--shots DIR] [--json]

Needs the Python "playwright" package and a Chromium it can launch. If either is missing the script
says so and exits 3; that is "not run", not a pass.

What it measures, for each theme at a desktop and a phone size:
  - page errors and console errors while every lesson is opened and stepped through every beat
  - that the animation markup changes between the first and last beat (reveal progresses)
  - that no "NaN" or "undefined" reaches the animation markup
  - contrast of every visible piece of HTML text against the backgrounds painted behind it
  - horizontal overflow of the page, controls pushed off screen, drawings spilling out of the stage,
    and text labels inside a drawing that overlap each other
  - whether any caption, key phrase or lesson title is cut off, on two phone sizes and desktop
  - the smallest rendered text inside each drawing, in pixels (reported, not failed)
  - pointer target sizes on the home, module, lesson, display sheet and drawer views, using the
    WCAG 2.2 SC 2.5.8 geometry: 24 by 24, or a centred 24px circle clear of other targets
And once: the display sheet (select, persist across reload, reset), reduced motion, keyboard reach,
a full autoplay run with timers shortened, and a run inside a scripts-only sandboxed frame (no
forms, no storage, no popups), which is how chat hosts embed pages.

The sandboxed frame is a local stand-in for a host frame. Passing it shows the course does not
depend on forms, storage or dialogs. It does not show the course works inside a particular product;
only opening the delivered preview shows that.

Limits: text inside SVG drawings is checked against the page background behind the SVG, not against
the shape under the text, so those figures are approximate. A browser check is not a design review;
whether a lesson looks good is still a person's call.
"""
import json
import sys
from pathlib import Path

THEMES = ["auto-light", "auto-dark", "paper", "mist", "dusk", "midnight"]
SIZES = {"desktop": (1280, 800), "phone": (390, 844)}

CONTRAST_JS = r"""
() => {
  const parse = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r:p[0], g:p[1], b:p[2], a:p.length>3?p[3]:1}; };
  const lum = c => { const f = v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const over = (f, b) => ({r:f.a*f.r+(1-f.a)*b.r, g:f.a*f.g+(1-f.a)*b.g, b:f.a*f.b+(1-f.a)*b.b, a:1});
  const bgOf = el => { const chain = []; let n = el;
    while (n && n.nodeType === 1) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0) chain.push(c); if (c && c.a === 1) break; n = n.parentElement; }
    let base = {r:255, g:255, b:255, a:1};
    for (let i = chain.length-1; i >= 0; i--) base = over(chain[i], base);
    return base; };
  const out = []; let measured = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const txt = node.nodeValue.trim(); if (!txt) continue;
    const el = node.parentElement; if (!el) continue;
    if (el.closest('script,style,[aria-hidden="true"]')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue;
    if (r.right < 0 || r.bottom < 0 || r.left > innerWidth || r.top > innerHeight) continue;
    let op = 1, n = el; while (n && n.nodeType === 1) { op *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; }
    if (op < 0.5) continue;                       // deliberately dimmed, not-yet-revealed content
    const inSvg = !!el.closest('svg');
    const fg = parse(inSvg ? cs.fill : cs.color); if (!fg) continue;
    const bg = bgOf(inSvg ? el.closest('svg').parentElement : el);
    const col = over({r:fg.r, g:fg.g, b:fg.b, a:fg.a}, bg);
    const l1 = lum(col), l2 = lum(bg); const ratio = (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
    measured++;
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700;
    const target = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
    if (ratio < target) out.push({text: txt.slice(0, 40), cls: (el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className) || el.tagName,
      ratio: Math.round(ratio*100)/100, target, svg: inSvg});
  }
  return {low: out, measured};
}
"""

LAYOUT_JS = r"""
() => {
  const off = [];
  ['#menuBtn','#themeBtn','#homeBtn','#tpPlay','#tpNext','#tpSpeed','#topProg'].forEach(s => { const e = document.querySelector(s); if (!e) return;
    const cs = getComputedStyle(e); if (cs.display === 'none') return; const r = e.getBoundingClientRect(); if (r.width === 0) return;
    if (r.left < -0.5 || r.right > innerWidth + 0.5) off.push(s); });
  let m = 99; const cv = document.querySelector('#animCanvas');
  if (cv) { const sc = cv.getBoundingClientRect().width / (cv.offsetWidth || 1);
    cv.querySelectorAll('text').forEach(t => { const s = t.ownerSVGElement; const k = s.getBoundingClientRect().width / s.viewBox.baseVal.width;
      m = Math.min(m, parseFloat(getComputedStyle(t).fontSize) * k); });
    cv.querySelectorAll('div,span').forEach(e => { if ([...e.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim())) m = Math.min(m, parseFloat(getComputedStyle(e).fontSize) * sc); }); }
  let clash = 0;
  if (cv) { const ts = [...cv.querySelectorAll('text')].filter(t => { let o = 1, n = t; while (n && n.nodeType === 1 && n !== cv) { o *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; } return o >= 0.5 && t.textContent.trim(); }).map(t => t.getBoundingClientRect());
    for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
      const w = Math.min(ts[i].right, ts[j].right) - Math.max(ts[i].left, ts[j].left), h = Math.min(ts[i].bottom, ts[j].bottom) - Math.max(ts[i].top, ts[j].top);
      if (w > 1 && h > 1) clash++; } }
  const st = document.querySelector('.l-stage'); let spill = false;
  if (cv && st) { const a = cv.getBoundingClientRect(), b = st.getBoundingClientRect(); spill = a.left < b.left - 1 || a.right > b.right + 1 || a.bottom > b.bottom + 1; }
  return {off, minText: Math.round(m * 10) / 10, spill, clash};
}
"""

CARDS_JS = r"""
() => [...document.querySelectorAll('.mod-card,.lcard,#playAll,#playMod')].filter(e => { const r = e.getBoundingClientRect();
  return r.width > 0 && (r.left < -0.5 || r.right > innerWidth + 0.5); }).length
"""

TARGETS_JS = r"""
() => {
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[onclick]';
  const out = [];
  document.querySelectorAll(sel).forEach(e => {
    const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility !== 'visible' || cs.pointerEvents === 'none' || e.disabled) return;
    let n = e, hidden = false; while (n && n.nodeType === 1) { const c = getComputedStyle(n); if (c.visibility === 'hidden' || c.display === 'none') hidden = true; n = n.parentElement; }
    if (hidden) return;
    const r = e.getBoundingClientRect(); if (r.width <= 0 || r.height <= 0) return;
    if (r.right <= 0 || r.bottom <= 0 || r.left >= innerWidth || r.top >= innerHeight) return;
    let b = {l: r.left, t: r.top, r: r.right, b: r.bottom};
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName)) [...(e.labels || [])].forEach(l => { const q = l.getBoundingClientRect(); b = {l: Math.min(b.l, q.left), t: Math.min(b.t, q.top), r: Math.max(b.r, q.right), b: Math.max(b.b, q.bottom)}; });
    out.push({id: (e.id ? '#' + e.id : e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0]) + ' ' + (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 16), x: b.l, y: b.t, w: b.r - b.l, h: b.b - b.t});
  });
  return out;
}
"""


def target_states(rects):
    """WCAG 2.2 SC 2.5.8 geometry. Returns (meets size, passes by spacing, list of unresolved ids).
    A target meets size at 24 by 24. An undersized one passes if a 24px circle centred on it is clear
    of every other target and of every other undersized target's circle. Touching is allowed."""
    eps, meets, spaced, unresolved = 0.01, 0, 0, []
    small = lambda t: t["w"] < 24 - eps or t["h"] < 24 - eps  # noqa: E731
    for i, t in enumerate(rects):
        if not small(t):
            meets += 1
            continue
        cx, cy, clear = t["x"] + t["w"] / 2, t["y"] + t["h"] / 2, True
        for j, o in enumerate(rects):
            if j == i:
                continue
            dx = max(o["x"] - cx, 0, cx - (o["x"] + o["w"]))
            dy = max(o["y"] - cy, 0, cy - (o["y"] + o["h"]))
            if (dx * dx + dy * dy) ** 0.5 < 12 - eps:
                clear = False
            elif small(o):
                ox, oy = o["x"] + o["w"] / 2, o["y"] + o["h"] / 2
                if ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5 < 24 - eps:
                    clear = False
        if clear:
            spaced += 1
        else:
            unresolved.append("%s %gx%g" % (t["id"], round(t["w"], 1), round(t["h"], 1)))
    return meets, spaced, unresolved


TRUNCATION_JS = r"""
() => { const out = [];
  for (let i = 0; i < LESSONS.length; i++) { goLesson(i, 'none'); const total = document.querySelectorAll('.dpip').length;
    for (let s = 0; s <= total; s++) { setStep(s);
      const e = document.querySelector('#dcText'); if (e && e.scrollHeight > e.clientHeight + 1) out.push('lesson ' + (i + 1) + ' beat ' + s + ' text (' + e.textContent.length + ' chars)');
      const k = document.querySelector('#dcKey'); if (k && k.scrollWidth > k.clientWidth + 1) out.push('lesson ' + (i + 1) + ' beat ' + s + ' key phrase'); }
    const h = document.querySelector('.l-head h2'); if (h && h.scrollHeight > h.clientHeight + 1) out.push('lesson ' + (i + 1) + ' title (' + h.textContent.length + ' chars)'); }
  return out; }
"""

COMPRESS_TIMERS = "const _s=window.setTimeout.bind(window);window.setTimeout=(f,m,...a)=>_s(f,(m&&m>16)?8:m,...a);"


def measure(page, where, r):
    got = page.evaluate(CONTRAST_JS)
    r["text_nodes_measured"] += got["measured"]
    for item in got["low"]:
        item["where"] = where
    return got["low"]


def set_theme(page, name):
    if name.startswith("auto-"):
        page.emulate_media(color_scheme=name.split("-")[1])
        page.evaluate("resetPrefs()")
    else:
        page.evaluate("setPref('theme', %s)" % json.dumps(name))
    page.wait_for_timeout(60)


def run(course, shots):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("NOT RUN: the playwright package is not available (%s)" % e)
        return 3, None
    url = Path(course).resolve().as_uri()
    res = {"file": str(course), "themes": {}, "errors": [], "checks": {}, "targets": {}}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            print("NOT RUN: Chromium could not be launched (%s)" % str(e)[:160])
            return 3, None
        res["browser"] = "Chromium " + browser.version
        for size_name, (w, h) in SIZES.items():
            ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:200]))
            page.on("console", lambda m: errs.append("console: " + m.text[:200]) if m.type == "error" else None)
            page.goto(url)
            page.wait_for_function("document.querySelectorAll('.ditem').length>0")
            n = page.evaluate("document.querySelectorAll('.ditem').length")
            for theme in THEMES:
                set_theme(page, theme)
                key = "%s/%s" % (theme, size_name)
                r = {"lessons": n, "no_progress": [], "bad_markup": [], "low_contrast": [], "overflow_px": 0,
                     "controls_off_screen": [], "drawing_spills_stage": [], "labels_collide": [], "min_drawing_text_px": 99, "lessons_with_text_under_9px": 0}
                page.evaluate("goHome('none')")
                page.wait_for_timeout(40)
                r["text_nodes_measured"] = 0
                r["cards_off_screen"] = page.evaluate(CARDS_JS)
                r["low_contrast"] += measure(page, "home", r)
                page.evaluate("goModule(0,'none')")
                page.wait_for_timeout(40)
                r["cards_off_screen"] += page.evaluate(CARDS_JS)
                r["low_contrast"] += measure(page, "module 0", r)
                for i in range(n):
                    info = page.evaluate(
                        """(i)=>{goLesson(i,'none');const total=document.querySelectorAll('.dpip').length;
                        setStep(1);const a=document.querySelector('#animCanvas').innerHTML;
                        setStep(total);const b=document.querySelector('#animCanvas').innerHTML;
                        return {total, same:a===b, bad:/NaN|undefined/.test(b)};}""", i)
                    if info["same"] and info["total"] >= 2:
                        r["no_progress"].append(i)
                    if info["bad"]:
                        r["bad_markup"].append(i)
                    page.wait_for_timeout(25)
                    r["low_contrast"] += measure(page, "lesson %d" % i, r)
                    lay = page.evaluate(LAYOUT_JS)
                    if lay["off"]:
                        r["controls_off_screen"].append([i, lay["off"]])
                    if lay["spill"]:
                        r["drawing_spills_stage"].append(i)
                    if lay["clash"]:
                        r["labels_collide"].append(i + 1)
                    r["min_drawing_text_px"] = min(r["min_drawing_text_px"], lay["minText"])
                    r["lessons_with_text_under_9px"] += 1 if lay["minText"] < 9 else 0
                    over = page.evaluate("document.documentElement.scrollWidth-window.innerWidth")
                    r["overflow_px"] = max(r["overflow_px"], over)
                page.evaluate("goHome('none');openSettings()")
                page.wait_for_timeout(120)
                r["low_contrast"] += measure(page, "display sheet", r)
                page.evaluate("closeSheet()")
                r["hidden_toast_visible"] = page.evaluate(
                    "(()=>{const t=document.querySelector('#toast');return !t.classList.contains('show')&&t.getBoundingClientRect().top<innerHeight;})()")
                if theme == THEMES[0]:
                    tm = {"meets": 0, "spaced": 0, "unresolved": []}
                    views = ["goHome('none')", "goModule(0,'none')", "goLesson(0,'none')", "goHome('none');openSettings()", "closeSheet();openDrawer()"]
                    for v in views:
                        page.evaluate(v)
                        page.wait_for_timeout(420)
                        a, b_, c_ = target_states(page.evaluate(TARGETS_JS))
                        tm["meets"] += a
                        tm["spaced"] += b_
                        tm["unresolved"] += ["%s: %s" % (v.split("(")[0].split(";")[-1], x) for x in c_]
                    page.evaluate("closeDrawer();goHome('none')")
                    page.wait_for_timeout(350)
                    res["targets"][size_name] = tm
                r["body_bg"] = page.evaluate("getComputedStyle(document.body).backgroundColor")
                r["accent_now"] = page.evaluate("C.blue")
                res["themes"][key] = r
                if shots and theme in ("auto-light", "dusk", "midnight", "mist"):
                    page.evaluate("goHome('none')")
                    page.wait_for_timeout(80)
                    page.screenshot(path=str(Path(shots) / ("home-%s-%s.png" % (theme, size_name))))
                    page.evaluate("goLesson(7,'none');setStep(99)")
                    page.wait_for_timeout(80)
                    page.screenshot(path=str(Path(shots) / ("lesson-%s-%s.png" % (theme, size_name))))
            res["errors"] += ["%s: %s" % (size_name, e) for e in errs]
            ctx.close()

        # ---- display sheet, persistence, reset, keyboard, motion ----
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, color_scheme="light")
        page = ctx.new_page()
        page.goto(url)
        page.wait_for_function("document.querySelectorAll('.ditem').length>0")
        c = res["checks"]
        # negative control: a deliberately low-contrast label must be reported, or the audit is blind
        page.evaluate("(()=>{const s=document.createElement('span');s.id='negctl';s.textContent='control';"
                      "s.style.cssText='position:fixed;left:8px;top:80px;color:#999999;background:#aaaaaa;font-size:14px';document.body.appendChild(s);})()")
        got = page.evaluate(CONTRAST_JS)
        c["negative_control_low_contrast_is_caught"] = any(x["text"] == "control" for x in got["low"])
        page.evaluate("document.querySelector('#negctl').remove()")
        c["default_theme_attr_absent"] = page.evaluate("!document.documentElement.hasAttribute('data-percept-theme')")
        bg_light = page.evaluate("getComputedStyle(document.body).backgroundColor")
        c["default_light_bg"] = bg_light
        page.click("#themeBtn")
        page.wait_for_selector("#sheet.show")
        c["sheet_opens"] = True
        page.wait_for_timeout(150)
        c["focus_moves_into_sheet"] = page.evaluate("document.activeElement && document.activeElement.name==='set-theme'")
        page.check("input[name=set-theme][value=dusk]")
        page.wait_for_timeout(60)
        c["select_dusk_sets_attr"] = page.evaluate("document.documentElement.getAttribute('data-percept-theme')") == "dusk"
        bg_dusk = page.evaluate("getComputedStyle(document.body).backgroundColor")
        c["select_dusk_changes_bg"] = bg_dusk != bg_light
        c["module_accent_follows_theme"] = page.evaluate("(()=>{const m=MODULES[0];return TONES.includes(String(m._accent).toLowerCase())?m.accent===C[String(m._accent).toLowerCase()]:m.accent===m._accent;})()")
        if shots:
            page.wait_for_timeout(500)
            page.screenshot(path=str(Path(shots) / "display-sheet-dusk-desktop.png"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(60)
        c["escape_closes_sheet"] = page.evaluate("!document.querySelector('#sheet').classList.contains('show')")
        c["focus_returns_to_button"] = page.evaluate("document.activeElement && document.activeElement.id==='themeBtn'")
        page.wait_for_timeout(450)
        c["closed_sheet_not_focusable"] = page.evaluate("getComputedStyle(document.querySelector('#sheet')).visibility==='hidden'")
        c["closed_drawer_not_focusable"] = page.evaluate("getComputedStyle(document.querySelector('#drawer')).visibility==='hidden'")
        page.reload()
        page.wait_for_function("document.querySelectorAll('.ditem').length>0")
        page.wait_for_timeout(100)
        c["choice_survives_reload"] = page.evaluate("document.documentElement.getAttribute('data-percept-theme')") == "dusk"
        page.click("#themeBtn")
        page.check("input[name=set-motion][value=reduced]")
        page.wait_for_timeout(40)
        c["reduced_motion_sets_attr"] = page.evaluate("document.documentElement.getAttribute('data-percept-motion')") == "reduced"
        c["reduced_motion_shortens_transitions"] = page.evaluate(
            "parseFloat(getComputedStyle(document.querySelector('.icon-btn')).transitionDuration)<0.001")
        page.click("#setReset")
        page.wait_for_timeout(60)
        c["reset_clears_theme"] = page.evaluate("!document.documentElement.hasAttribute('data-percept-theme')")
        c["reset_clears_motion"] = page.evaluate("!document.documentElement.hasAttribute('data-percept-motion')")
        c["reset_restores_light_bg"] = page.evaluate("getComputedStyle(document.body).backgroundColor") == bg_light
        c["reset_shows_auto_checked"] = page.evaluate("document.querySelector('input[name=set-theme]:checked').value==='auto'")
        page.keyboard.press("Escape")
        c["drawer_entries_are_buttons"] = page.evaluate(
            "[...document.querySelectorAll('.ditem,.dmod-head')].every(e=>e.tagName==='BUTTON')")
        c["viewport_allows_zoom"] = page.evaluate(
            "!/user-scalable\\s*=\\s*no|maximum-scale/.test(document.querySelector('meta[name=viewport]').content)")
        # keyboard reach: tab from the top must land on the display button within a few stops
        page.reload()
        page.wait_for_function("document.querySelectorAll('.ditem').length>0")
        reached = False
        for _ in range(6):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement && document.activeElement.id") == "themeBtn":
                reached = True
                break
        c["display_button_reachable_by_tab"] = reached
        c["network_requests_other_than_file"] = 0
        ctx.close()

        # ---- network and autoplay ----
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        reqs = []
        page.on("request", lambda r: reqs.append(r.url) if not r.url.startswith("file:") else None)
        errs = []
        page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:200]))
        page.add_init_script(COMPRESS_TIMERS)
        page.goto(url)
        page.wait_for_function("document.querySelectorAll('.ditem').length>0")
        n = page.evaluate("document.querySelectorAll('.ditem').length")
        page.evaluate("goHome('none');play()")
        try:
            page.wait_for_function("document.querySelectorAll('.ditem.done').length===%d" % n, timeout=30000)
            c["autoplay_completes_all_lessons"] = True
        except Exception:  # noqa: BLE001
            c["autoplay_completes_all_lessons"] = False
        c["network_requests_other_than_file"] = len(reqs)
        res["errors"] += ["autoplay: " + e for e in errs]
        ctx.close()

        # ---- teaching text must not be cut off: every caption, key phrase and title, at three sizes ----
        res["truncated"] = {}
        for label, (tw, th) in (("phone 390x844", (390, 844)), ("small phone 360x640", (360, 640)), ("desktop 1280x800", (1280, 800))):
            ctx = browser.new_context(viewport={"width": tw, "height": th}, reduced_motion="reduce")
            page = ctx.new_page()
            page.goto(url)
            page.wait_for_function("document.querySelectorAll('.ditem').length>0")
            res["truncated"][label] = page.evaluate(TRUNCATION_JS)
            ctx.close()

        # ---- delivery stand-in: the course inside a scripts-only sandboxed frame ----
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            wrap = Path(td) / "frame.html"
            wrap.write_text('<!doctype html><html lang="en"><title>frame</title><body style="margin:0"><iframe sandbox="allow-scripts" src="%s" '
                            'style="border:0;width:100vw;height:100vh"></iframe></body></html>' % url, encoding="utf-8")
            ctx = browser.new_context(viewport={"width": 1100, "height": 760})
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:200]))
            page.on("console", lambda m: errs.append("console: " + m.text[:200]) if m.type == "error" else None)
            page.goto(wrap.as_uri())
            page.wait_for_timeout(600)
            frames = [f for f in page.frames if f != page.main_frame]
            if not frames:
                c["sandbox_frame_boots"] = False
            else:
                fr = frames[0]
                try:
                    c["sandbox_frame_boots"] = fr.evaluate("document.querySelectorAll('.ditem').length") == n
                    c["sandbox_storage_is_blocked_there"] = fr.evaluate("(()=>{try{localStorage.getItem('x');return false}catch(e){return true}})()")
                    info = fr.evaluate("(()=>{goLesson(1,'none');const t=document.querySelectorAll('.dpip').length;setStep(1);const a=document.querySelector('#animCanvas').innerHTML;setStep(t);return a!==document.querySelector('#animCanvas').innerHTML;})()")
                    c["sandbox_lesson_steps"] = bool(info)
                    fr.locator("#themeBtn").click()
                    page.wait_for_timeout(200)
                    fr.locator("input[name=set-theme][value=dusk]").check()
                    page.wait_for_timeout(120)
                    c["sandbox_theme_control_works"] = fr.evaluate("document.documentElement.getAttribute('data-percept-theme')") == "dusk"
                    fr.locator("#setReset").click()
                    page.wait_for_timeout(120)
                    c["sandbox_reset_works"] = fr.evaluate("!document.documentElement.hasAttribute('data-percept-theme')")
                    fr.evaluate("closeSheet();goHome('none')")
                    fr.locator("#playAll").click()
                    page.wait_for_timeout(300)
                    c["sandbox_play_button_starts_a_lesson"] = fr.evaluate("ST.view==='lesson'&&PLAY.on")
                    c["sandbox_uses_no_form"] = fr.evaluate("document.forms.length") == 0
                except Exception as e:  # noqa: BLE001
                    c["sandbox_frame_boots"] = False
                    errs.append("sandbox: " + str(e).split("\n")[0][:160])
            res["errors"] += ["sandbox: " + e for e in errs]
            ctx.close()
        browser.close()
    return 0, res


def main(argv):
    args, shots, as_json, it = [], None, False, iter(argv[1:])
    for a in it:
        if a == "--json":
            as_json = True
        elif a == "--shots":
            shots = next(it, None)
            if shots is None or shots.startswith("--"):
                print("render_check: --shots needs a folder")
                return 2
        elif a.startswith("--"):
            print("render_check: unknown option " + a)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    if not Path(args[0]).is_file():
        print("render_check: cannot read " + args[0])
        return 2
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
    code, res = run(args[0], shots)
    if res is None:
        return code
    fails = 0
    if as_json:
        print(json.dumps(res, indent=1))
    else:
        print("browser: %s" % res["browser"])
        for key, r in res["themes"].items():
            low_html = [x for x in r["low_contrast"] if not x["svg"]]
            low_svg = [x for x in r["low_contrast"] if x["svg"]]
            bad = (len(r["no_progress"]) + len(r["bad_markup"]) + len(low_html) + (1 if r["overflow_px"] > 0 else 0)
                   + len(r["controls_off_screen"]) + len(r["drawing_spills_stage"]) + (1 if r["hidden_toast_visible"] else 0)
                   + r["cards_off_screen"] + len(r["labels_collide"]))
            fails += bad
            print("%-20s lessons %d | text measured %d | no progress %d | bad markup %d | low-contrast text %d | svg text to review %d | overflow %dpx | bg %s"
                  % (key, r["lessons"], r["text_nodes_measured"], len(r["no_progress"]), len(r["bad_markup"]), len(low_html), len(low_svg), r["overflow_px"], r["body_bg"]))
            if r["labels_collide"]:
                print("     drawing labels collide in lesson(s): %s" % ", ".join(str(x) for x in r["labels_collide"]))
            print("     cards off screen %d | controls off screen %d | drawing spills stage %d | hidden toast visible %s | smallest drawing text %.1fpx, %d lesson(s) under 9px (reported, not failed)"
                  % (r["cards_off_screen"], len(r["controls_off_screen"]), len(r["drawing_spills_stage"]), r["hidden_toast_visible"], r["min_drawing_text_px"], r["lessons_with_text_under_9px"]))
            seen = set()
            for x in low_html + low_svg:
                k = (x["cls"], x["ratio"])
                if k in seen:
                    continue
                seen.add(k)
                print("     %s %-9s %-22s %.2f (target %.1f) %r" % ("svg " if x["svg"] else "html", x["where"], str(x["cls"])[:22], x["ratio"], x["target"], x["text"]))
        for label, items in res.get("truncated", {}).items():
            fails += len(items)
            print("truncated/%-20s %d caption, key phrase or title cut off" % (label, len(items)))
            for x in items[:6]:
                print("     cut off: " + x)
        for size_name, tm in res["targets"].items():
            fails += len(tm["unresolved"])
            print("targets/%-12s %d meet 24 by 24 | %d pass by the spacing circle | %d unresolved" % (size_name, tm["meets"], tm["spaced"], len(tm["unresolved"])))
            for x in tm["unresolved"][:8]:
                print("     unresolved: " + x)
        for k, v in res["checks"].items():
            ok = (v == 0) if k == "network_requests_other_than_file" else (bool(v) if isinstance(v, bool) else True)
            fails += 0 if ok else 1
            print("%-40s %s" % (k, v))
        print("errors: %d" % len(res["errors"]))
        for e in res["errors"][:10]:
            print("   " + e)
        fails += len(res["errors"])
    print("RESULT: %s" % ("PASS" if fails == 0 else "%d item(s) need attention" % fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
