#!/usr/bin/env python3
"""Render gate: generic browser checks for any single-file HTML page or app.

It loads the page in headless Chromium and checks what a reviewer would
otherwise have to eyeball: script errors, broken or external resources,
sideways scrolling at four widths, pinch-zoom, an axe accessibility scan in
light and dark colour schemes, keyboard reach, visible focus, reduced motion,
small tap targets and clipped text. It saves screenshots of every width.

It tests one state per run. The default is first load. To test another state
(a form open, sample data loaded), pass JavaScript with --prep or --prep-js;
it runs after every load, in every browser context.

Usage:
  python3 render_gate.py PAGE.html OUTDIR [--label NAME] [--prep FILE.js | --prep-js CODE]
                         [--date 2026-10-21T10:00:00+10:00] [--tz Australia/Brisbane]

Exit codes (references/results.md): 0 completed, every applicable check ran and none failed. 1 failed: at least
one check failed. 2 usage error. 3 partial: nothing failed, but an applicable check did not run (for example the
accessibility scans without axe-core); this is never a pass. 4 runner error: the gate could not run (no Pillow, no
playwright, no Chromium, or a crash); nothing was checked. Every run ends with one RECEIPT line on stderr.
Needs Python playwright with Chromium, and Pillow. The accessibility scans need axe-core
(axe.min.js next to this script, or node_modules/axe-core in the working folder); without it they
report NOT RUN, the other checks still run, and the result is partial.
Results: OUTDIR/results.json, OUTDIR/report.md, OUTDIR/*.png
"""
import argparse, io, json, pathlib, re, sys, time
# Pillow and playwright are imported where they are used, so a missing one is reported as a runner error with a
# receipt instead of a traceback before any handler can run.

VERSION = 'forge 3.3.2'

HERE = pathlib.Path(__file__).resolve().parent
AXE_CANDIDATES = [HERE / 'axe.min.js', HERE.parent / 'node_modules/axe-core/axe.min.js',
                  pathlib.Path.cwd() / 'axe.min.js', pathlib.Path.cwd() / 'node_modules/axe-core/axe.min.js']
WIDTHS = [(320, 640), (390, 844), (768, 1024), (1280, 860)]
FOCUSABLE = ('a[href],area[href],button,input:not([type=hidden]),select,textarea,summary,iframe,'
             '[tabindex],[contenteditable=""],[contenteditable=true],audio[controls],video[controls]')

HELPERS = r"""
(() => {
  if (window.__rg) return;
  const FOC = %s;
  const rg = {};
  rg.describe = (el) => {
    if (!el || !el.tagName) return String(el);
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const cls = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (cls.length) s += '.' + cls.join('.');
    const t = (el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ').slice(0, 32);
    if (t) s += ' "' + t + '"';
    return s;
  };
  rg.path = (el) => {
    const parts = [];
    while (el && el.nodeType === 1 && el !== document.documentElement) {
      const p = el.parentElement;
      if (!p) break;
      const i = Array.prototype.indexOf.call(p.children, el) + 1;
      parts.unshift(el.tagName.toLowerCase() + ':nth-child(' + i + ')');
      el = p;
    }
    return 'html > ' + parts.join(' > ');
  };
  rg.visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false;
    if (el.closest('[inert],[aria-hidden="true"],[hidden]')) return false;
    if (el.checkVisibility && !el.checkVisibility({opacityProperty: true, visibilityProperty: true})) return false;
    const d = el.closest('details:not([open])');
    if (d) { const s = d.querySelector(':scope > summary'); if (!s || !s.contains(el)) return false; }
    let a = el;
    while (a && a !== document.body) { if (parseFloat(getComputedStyle(a).opacity) === 0) return false; a = a.parentElement; }
    return true;
  };
  rg.tabbable = (el) => {
    if (!el.matches(FOC)) return false;
    if (el.disabled) return false;
    if (el.hasAttribute('tabindex') && el.tabIndex < 0) return false;
    if (el.tagName === 'A' && !el.hasAttribute('href') && !el.hasAttribute('tabindex')) return false;
    return true;
  };
  rg.overlay = () => {
    // An open modal: a real dialog, or a fixed layer covering most of the viewport that holds controls.
    const dlg = [...document.querySelectorAll('dialog[open],[role=dialog],[role=alertdialog],[aria-modal=true]')].filter(rg.visible);
    if (dlg.length) return {el: dlg[dlg.length - 1], marked: true};
    const vw = innerWidth, vh = innerHeight;
    const fixed = [...document.querySelectorAll('body *')].filter(el => {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed') return false;
      if (!rg.visible(el)) return false;
      const r = el.getBoundingClientRect();
      return r.width >= vw * 0.7 && r.height >= vh * 0.7 && el.querySelector(FOC);
    });
    if (fixed.length) return {el: fixed[fixed.length - 1], marked: false};
    return null;
  };
  window.__rg = rg;
})();
""" % json.dumps(FOCUSABLE)

RAF_COUNTER = r"""
(() => { window.__rgRaf = 0; const o = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => { window.__rgRaf++; return o(cb); }; })();
"""


def fixed_date_script(iso):
    return ("(() => { const fixed = new Date(%s).getTime(); const D = Date; class FD extends D {"
            " constructor(...a){ if(a.length===0){ super(fixed); } else { super(...a); } }"
            " static now(){ return fixed; } } window.Date = FD; })();" % json.dumps(iso))


class Results:
    def __init__(self):
        self.rows = []

    def add(self, cid, name, result, detail=''):
        if result is True:
            result = 'PASS'
        elif result is False:
            result = 'FAIL'
        self.rows.append(dict(id=cid, check=name, result=result, detail=detail))
        short = json.dumps(detail)[:220] if not isinstance(detail, str) else detail[:220]
        print(f'{cid:4} {result:5} {name} :: {short}')


def axe_scan(page, axe_src):
    if not axe_src:
        return None, None
    page.add_script_tag(content=axe_src)
    v = page.evaluate("""async () => { const r = await axe.run(document, {resultTypes: ['violations']});
        return r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length,
            example: (v.nodes[0] && v.nodes[0].target || []).join(' ')})); }""")
    serious = [x for x in v if x['impact'] in ('serious', 'critical')]
    return serious, v


def pixel_change(a_png, b_png):
    from PIL import Image, ImageChops
    a = Image.open(io.BytesIO(a_png)).convert('RGB')
    b = Image.open(io.BytesIO(b_png)).convert('RGB')
    if a.size != b.size:
        return None
    d = ImageChops.difference(a, b)
    r, g, bl = d.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    return sum(m.point(lambda v: 255 if v > 40 else 0).histogram()[255:])


def run(path, outdir, label='first load', prep=None, date=None, tz='Australia/Brisbane', max_focus=40, locale='en-AU'):
    import PIL  # noqa: F401  fail before any check if Pillow is missing (runner error, not a product result)
    from playwright.sync_api import sync_playwright
    axe_path = next((p for p in AXE_CANDIDATES if p.exists()), None)
    axe_src = axe_path.read_text(encoding='utf-8') if axe_path else None   # without axe-core the scans report NOT RUN
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    url = path if path.startswith(('http://', 'https://')) else pathlib.Path(path).resolve().as_uri()
    own_origin = re.sub(r'^(\w+://[^/]+).*', r'\1', url) if url.startswith('http') else 'file:'
    R = Results()
    errors, external, broken, ext_failed = [], set(), [], set()

    def watch(page, where):
        # Resource load failures are reported by R2/R3, not counted as script errors.
        page.on('console', lambda m: errors.append(f'[{where}] {m.text}')
                if m.type == 'error' and not m.text.startswith('Failed to load resource') else None)
        page.on('requestfailed', lambda r: ext_failed.add(re.sub(r'^(\w+://[^/]+).*', r'\1', r.url))
                if r.url.startswith('http') else None)
        page.on('pageerror', lambda e: errors.append(f'[{where}] {e}'))
        page.on('request', lambda r: external.add(re.sub(r'^(\w+://[^/]+).*', r'\1', r.url))
                if not r.url.startswith(('file:', 'data:', 'blob:', 'about:', own_origin)) else None)
        page.on('requestfailed', lambda r: broken.append(r.url[:160]) if r.url.startswith('file:') else None)

    def load(page):
        page.goto(url)
        page.wait_for_load_state('load')
        page.wait_for_timeout(700)
        if prep:
            try:
                page.evaluate('async () => { %s\n }' % prep)
            except Exception as e:  # prep may navigate (e.g. seed storage then reload)
                if 'context was destroyed' not in str(e) and 'navigation' not in str(e).lower():
                    raise
                page.wait_for_load_state('load')
            page.wait_for_timeout(500)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def context(**kw):
            ctx = browser.new_context(timezone_id=tz, locale=locale, **kw)
            ctx.add_init_script(HELPERS)
            if date:
                ctx.add_init_script(fixed_date_script(date))
            return ctx

        # ---- Main context: load, widths, axe, keyboard, focus ----
        ctx = context(viewport={'width': 1280, 'height': 860})
        page = ctx.new_page()
        watch(page, 'load')
        load(page)
        light_bg = page.evaluate("[getComputedStyle(document.documentElement).backgroundColor, getComputedStyle(document.body).backgroundColor]")
        R.add('R1', 'Loads without script errors', not errors, errors[:4])
        R.add('R2', 'No broken local resources', not broken, broken[:6])
        R.add('R3', 'Self-contained (no requests to other hosts)', 'PASS' if not external else 'WARN',
              {'hosts': sorted(external)[:8], 'failed to load here': sorted(ext_failed)[:8],
               'note': 'the page needs a network connection for these; a failed load may be this test machine blocking the host'}
              if external else [])

        overflow = {}
        for w, h in WIDTHS:
            page.set_viewport_size({'width': w, 'height': h})
            page.wait_for_timeout(350)
            info = page.evaluate("""() => { const iw = innerWidth, sw = document.documentElement.scrollWidth;
                if (sw <= iw) return {sw, iw, offenders: []};
                const off = [...document.querySelectorAll('body *')].filter(el => {
                    const r = el.getBoundingClientRect(); return r.width > 0 && r.right > iw; });
                const leaves = off.filter(el => !off.some(o => o !== el && el.contains(o)));
                return {sw, iw, offenders: leaves.slice(0, 5).map(el => __rg.describe(el) + ' right=' + Math.round(el.getBoundingClientRect().right))}; }""")
            overflow[w] = info
            page.screenshot(path=str(out / f'{w}px.png'), full_page=True)
        bad = {w: i for w, i in overflow.items() if i['sw'] > i['iw']}
        R.add('R4', 'No sideways scrolling at 320, 390, 768 and 1280 px', not bad,
              {w: f"scrollWidth {i['sw']} > {i['iw']}; " + '; '.join(i['offenders']) for w, i in bad.items()} or 'all widths fit')

        vp = page.evaluate("(document.querySelector('meta[name=viewport]') || {}).content || ''")
        zoom_blocked = re.search(r'maximum-scale\s*=\s*1(\.0+)?\b|user-scalable\s*=\s*(no|0)\b', vp)
        R.add('R5', 'Pinch-zoom allowed (viewport meta)', 'FAIL' if zoom_blocked else ('PASS' if vp else 'WARN'),
              vp or 'no viewport meta: phones will render a zoomed-out desktop layout')

        page.set_viewport_size({'width': 1280, 'height': 860}); page.wait_for_timeout(250)
        s, allv = axe_scan(page, axe_src)
        R.add('R6', 'Accessibility scan at 1280 px: no serious or critical issues', 'NOT RUN' if s is None else not s,
              'axe-core not found: put axe.min.js next to this script, or npm install axe-core in the working folder' if s is None
              else (s or [f"{x['id']} ({x['impact']})" for x in allv]))
        page.set_viewport_size({'width': 390, 'height': 844}); page.wait_for_timeout(250)
        s, allv = axe_scan(page, axe_src)
        R.add('R7', 'Accessibility scan at 390 px: no serious or critical issues', 'NOT RUN' if s is None else not s,
              'axe-core not found: put axe.min.js next to this script, or npm install axe-core in the working folder' if s is None
              else (s or [f"{x['id']} ({x['impact']})" for x in allv]))

        small = page.evaluate("""() => [...document.querySelectorAll(%s)].filter(el => __rg.visible(el) && __rg.tabbable(el))
            .filter(el => { const cs = getComputedStyle(el); if (el.tagName === 'A' && cs.display === 'inline') return false;
                let r = el.getBoundingClientRect(), w = r.width, h = r.height;
                for (const l of (el.labels || [])) { const q = l.getBoundingClientRect(); w = Math.max(w, q.width); h = Math.max(h, q.height); }
                return w < 24 || h < 24; })
            .map(el => { const r = el.getBoundingClientRect(); return __rg.describe(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height); })""" % json.dumps(FOCUSABLE))
        R.add('R8', 'Tap targets at 390 px are at least 24 x 24 px', 'PASS' if not small else 'WARN', small[:8])

        page.set_viewport_size({'width': 1280, 'height': 860}); page.wait_for_timeout(250)

        # Clickable-looking elements the keyboard cannot reach (cursor:pointer or direct click listeners).
        cdp = ctx.new_cdp_session(page)
        arr = cdp.send('Runtime.evaluate', {'expression': "[...document.querySelectorAll('body *')].filter(el => !__rg.tabbable(el) && __rg.visible(el)).slice(0, 1500)"})
        props = cdp.send('Runtime.getProperties', {'objectId': arr['result']['objectId'], 'ownProperties': True})
        listened = []
        for pr in props['result']:
            if not pr['name'].isdigit():
                continue
            oid = pr['value']['objectId']
            ls = cdp.send('DOMDebugger.getEventListeners', {'objectId': oid})['listeners']
            if any(l['type'] in ('click', 'mousedown', 'mouseup', 'pointerdown', 'pointerup', 'touchstart') for l in ls):
                listened.append(cdp.send('Runtime.callFunctionOn', {'objectId': oid, 'returnByValue': True,
                                'functionDeclaration': 'function(){ this.setAttribute("data-rg-click", "1"); return 1; }'}))
        unreachable = page.evaluate("""(FOC) => {
            const cands = [...document.querySelectorAll('body *')].filter(el => {
                if (!__rg.visible(el)) return false;
                const pointer = getComputedStyle(el).cursor === 'pointer';
                if (!pointer && !el.hasAttribute('data-rg-click')) return false;
                const f = el.closest(FOC);
                if (f && __rg.tabbable(f)) return false;
                if (el.closest('label')) return false;
                if ([...el.querySelectorAll(FOC)].some(__rg.tabbable)) return false;
                return true; });
            const outer = cands.filter(el => !cands.some(o => o !== el && o.contains(el)));
            document.querySelectorAll('[data-rg-click]').forEach(e => e.removeAttribute('data-rg-click'));
            const COMP = '[role=radiogroup],[role=tablist],[role=listbox],[role=menu],[role=menubar],[role=tree],[role=grid],[role=treegrid],[role=toolbar]';
            return outer.slice(0, 20).map(el => { const c = el.closest(COMP);
                return {desc: __rg.describe(el), path: __rg.path(el), comp: c ? __rg.path(c) : null, role: c ? c.getAttribute('role') : null}; }); }""", FOCUSABLE)
        # tabindex="-1" inside a composite widget (roving tabindex, aria-activedescendant) is reached with arrow keys
        # from the widget's Tab stop: try that path in a fresh page before calling the item unreachable.
        no_path, unresolved, via = [], [], []
        for c in unreachable:
            if not c['comp']:
                no_path.append(c['desc']); continue
            verdict = None
            for key in ('ArrowRight', 'ArrowDown'):
                pg2 = ctx.new_page()
                try:
                    load(pg2)
                    entry = pg2.evaluate("""(a) => { const c = document.querySelector(a[0]); if (!c) return null;
                        if (__rg.tabbable(c) && c.hasAttribute('aria-activedescendant')) { c.setAttribute('data-rg-entry', '1'); return 'c'; }
                        const m = [...c.querySelectorAll('*')].find(__rg.tabbable); if (m) { m.setAttribute('data-rg-entry', '1'); return 'm'; }
                        if (__rg.tabbable(c)) { c.setAttribute('data-rg-entry', '1'); return 'c'; } return null; }""", [c['comp']])
                    if entry is None:
                        verdict = 'none'; pg2.close(); break
                    pg2.locator('[data-rg-entry]').first.focus(timeout=2500)
                    for _ in range(40):
                        if pg2.evaluate("""(a) => { const c = document.querySelector(a[0]), t = document.querySelector(a[1]);
                            return !!t && (document.activeElement === t || (!!t.id && c.getAttribute('aria-activedescendant') === t.id)); }""", [c['comp'], c['path']]):
                            verdict = 'reached'; break
                        pg2.keyboard.press(key); pg2.wait_for_timeout(40)
                except Exception:  # noqa: BLE001
                    pass
                pg2.close()
                if verdict:
                    break
            if verdict == 'reached':
                via.append(c['desc'] + ' (via its ' + str(c['role']) + ')')
            elif verdict == 'none':
                no_path.append(c['desc'] + ' (its ' + str(c['role']) + ' has no Tab stop)')
            else:
                unresolved.append(c['desc'] + ' (in a ' + str(c['role']) + '; arrow keys did not reach it)')
        R.add('R9', 'Everything clickable is reachable by keyboard', not no_path,
              no_path or ({'reached through a composite widget': via} if via else 'no clickable-but-unreachable elements found'))
        if unresolved:
            R.add('R9b', 'Composite items reachable with arrow keys', 'NOT RUN',
                  {'unresolved': unresolved, 'note': 'the widget has a Tab stop but the arrow-key path to these items could not be shown; read them'})

        # Tab walk: reach, traps, overlays, and focused-state screenshots for the focus check.
        page.mouse.move(1, 859)
        scope = page.evaluate("""() => { const o = __rg.overlay();
            const root = o ? o.el : document.body;
            const radios = new Set();
            const want = [...root.querySelectorAll(%s)].filter(el => __rg.visible(el) && __rg.tabbable(el)).filter(el => {
                if (el.type !== 'radio' || !el.name) return true;
                const group = [...document.querySelectorAll('input[type=radio]')].filter(r => r.name === el.name && r.form === el.form);
                const rep = group.find(r => r.checked) || group[0];
                return el === rep; }).map(__rg.path);
            return {overlay: o ? __rg.describe(o.el) : null, marked: o ? o.marked : null, rootPath: o ? __rg.path(o.el) : null, want}; }""" % json.dumps(FOCUSABLE))
        page.evaluate('document.activeElement && document.activeElement.blur()')
        max_tabs = min(200, max(40, len(scope['want']) * 2 + 6))
        seen, order, shots = set(), [], {}
        first = None
        for _ in range(max_tabs):
            page.keyboard.press('Tab')
            page.wait_for_timeout(60)
            info = page.evaluate("""() => { const el = document.activeElement;
                if (!el || el === document.body || el === document.documentElement) return null;
                let t = el; const r0 = el.getBoundingClientRect();
                if (r0.width * r0.height < 16 || !__rg.visible(el)) t = el.closest('label') || el.parentElement || el;
                t.scrollIntoView({block: 'center', inline: 'nearest'});
                const r = t.getBoundingClientRect();
                return {path: __rg.path(el), tpath: __rg.path(t), desc: __rg.describe(el), x: r.left, y: r.top, w: r.width, h: r.height}; }""")
            if info is None:
                continue
            if info['path'] == first:
                break
            first = first or info['path']
            order.append(info['path'])
            if info['path'] in seen:
                continue
            seen.add(info['path'])
            if len(shots) < max_focus:
                page.wait_for_timeout(120)
                clip = clamp(info, 1280, 860)
                if clip:
                    shots[info['path']] = dict(info, clip=clip, focused=page.screenshot(clip=clip, animations='disabled'))
        want = set(scope['want'])
        missed = sorted(want - seen)
        root = scope['rootPath']
        escaped = [p_ for p_ in seen if root and not p_.startswith(root + ' >')] if root else []
        desc_missed = page.evaluate("(ps) => ps.map(p => { const el = document.querySelector(p); return el ? __rg.describe(el) : p; })", missed[:8])
        detail = {'reached': len(seen), 'expected': len(want)}
        if scope['overlay']:
            detail['open overlay'] = scope['overlay'] + ('' if scope['marked'] else ' (not marked as a dialog)')
        if desc_missed:
            detail['not reached'] = desc_missed
        if escaped:
            detail['focus left the overlay'] = len(escaped)
        R.add('R10', 'Tab reaches every visible control, with no trap' + (' and stays inside the open overlay' if root else ''),
              not missed and not escaped, detail)
        if scope['overlay'] and not scope['marked']:
            R.add('R10b', 'Open overlay is marked as a dialog (dialog element, role=dialog or aria-modal)', 'WARN', scope['overlay'])

        # Unfocused pass: reload, same scroll target, no focus, compare pixels.
        page.reload(); page.wait_for_load_state('load'); page.wait_for_timeout(500)
        if prep:
            try:
                page.evaluate('async () => { %s\n }' % prep)
            except Exception:
                page.wait_for_load_state('load')
            page.wait_for_timeout(400)
        page.mouse.move(1, 859)
        no_focus_style, compared, pairs = [], 0, []
        for pth, sh in shots.items():
            ok = page.evaluate("""(a) => { const el = document.querySelector(a.path); const t = document.querySelector(a.tpath);
                if (!el || !t) return false; if (document.activeElement) document.activeElement.blur();
                t.scrollIntoView({block: 'center', inline: 'nearest'}); return true; }""", {'path': pth, 'tpath': sh['tpath']})
            if not ok:
                continue
            page.wait_for_timeout(80)
            unf = page.screenshot(clip=sh['clip'], animations='disabled')
            ch = pixel_change(sh['focused'], unf)
            if ch is None:
                continue
            compared += 1
            pairs.append((sh['desc'], unf, sh['focused'], ch >= 20))
            if ch < 20:
                no_focus_style.append(sh['desc'])
        if pairs:
            contact_sheet(pairs, out / 'focus-states.png')
        R.add('R11', 'Keyboard focus is visible on every control', not no_focus_style and compared > 0 if shots else 'WARN',
              {'compared': compared, 'no visible change when focused': no_focus_style[:10]} if shots else 'nothing focusable was reached')

        clipped = []
        for w in (390, 1280):
            page.set_viewport_size({'width': w, 'height': 844 if w == 390 else 860}); page.wait_for_timeout(250)
            # Text is cut when one of its line boxes reaches past a clipping container. Decoration that overflows on
            # purpose (a clipped circle behind a hero) and visually hidden text (1 px boxes) are not counted.
            clipped += page.evaluate("""(w) => [...document.querySelectorAll('body *')].filter(el => {
                const cs = getComputedStyle(el);
                if (!/(hidden|clip)/.test(cs.overflowX + cs.overflow)) return false;
                if (!__rg.visible(el)) return false;
                const box = el.getBoundingClientRect(); if (box.width <= 2 || box.height <= 2) return false;
                const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                while (tw.nextNode()) { const n = tw.currentNode; if (!n.nodeValue.trim()) continue;
                    const pe = n.parentElement; if (!pe || pe.closest('[aria-hidden="true"]')) continue;
                    const pr = pe.getBoundingClientRect(); if (pr.width <= 2 || pr.height <= 2) continue;
                    const r = document.createRange(); r.selectNodeContents(n);
                    for (const q of r.getClientRects()) if (q.width && (q.right > box.right + 1 || q.left < box.left - 1)) return true; }
                return false; })
                .slice(0, 6).map(el => w + 'px: ' + __rg.describe(el) + (getComputedStyle(el).textOverflow === 'ellipsis' ? ' (ellipsis)' : ''))""", w)
        R.add('R12', 'No text cut off by its container', 'PASS' if not clipped else 'WARN', clipped[:8])
        ctx.close()

        # ---- Dark colour scheme ----
        ctx = context(viewport={'width': 1280, 'height': 860}, color_scheme='dark')
        page = ctx.new_page(); watch(page, 'dark')
        load(page)
        page.screenshot(path=str(out / '1280px-dark.png'), full_page=True)
        page.set_viewport_size({'width': 390, 'height': 844}); page.wait_for_timeout(250)
        page.screenshot(path=str(out / '390px-dark.png'), full_page=True)
        page.set_viewport_size({'width': 1280, 'height': 860}); page.wait_for_timeout(250)
        dark_bg = page.evaluate("[getComputedStyle(document.documentElement).backgroundColor, getComputedStyle(document.body).backgroundColor]")
        if dark_bg == light_bg and not prep:
            R.add('R13b', 'Page follows the system dark colour scheme', 'WARN',
                  'the page looked the same with the system set to dark, so R13 scanned its light colours. If the app has an in-app dark theme, run again with --prep-js to switch it on')
        s, allv = axe_scan(page, axe_src)
        R.add('R13', 'Accessibility scan in dark colour scheme: no serious or critical issues', 'NOT RUN' if s is None else not s,
              'axe-core not found: put axe.min.js next to this script, or npm install axe-core in the working folder' if s is None
              else (s or [f"{x['id']} ({x['impact']})" for x in allv]))
        ctx.close()

        # ---- Reduced motion ----
        def motion(reduce):
            c = context(viewport={'width': 1280, 'height': 860}, reduced_motion='reduce' if reduce else 'no-preference')
            c.add_init_script(RAF_COUNTER)
            pg = c.new_page(); watch(pg, 'reduced-motion' if reduce else 'motion')
            load(pg)
            pg.wait_for_timeout(900)
            r0 = pg.evaluate('window.__rgRaf')
            pg.wait_for_timeout(1000)
            res = pg.evaluate("""() => ({
                anims: document.getAnimations().filter(a => a.playState === 'running').map(a => {
                    const t = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming() : {};
                    return {name: a.animationName || a.transitionProperty || 'script', iterations: t.iterations === Infinity ? 'infinite' : t.iterations,
                            duration: t.duration, target: a.effect && a.effect.target ? __rg.describe(a.effect.target) : ''}; }),
                smooth: getComputedStyle(document.documentElement).scrollBehavior === 'smooth' })""")
            res['raf_per_s'] = pg.evaluate('window.__rgRaf') - r0
            c.close()
            return res
        normal, reduced = motion(False), motion(True)
        long_ = [a for a in reduced['anims'] if a['iterations'] == 'infinite' or (isinstance(a['duration'], (int, float)) and a['duration'] > 300)]
        if not normal['anims'] and normal['raf_per_s'] < 30 and not reduced['smooth']:
            R.add('R14', 'Respects reduced motion', 'PASS', 'no running animation found at load (hover and click animations not exercised)')
        else:
            problems = [f"{a['target']} {a['name']} ({a['iterations']}x, {a['duration']} ms)" for a in long_[:6]]
            if reduced['raf_per_s'] >= 30:
                problems.append(f"script animation loop still running ({reduced['raf_per_s']} frames/s)")
            if reduced['smooth']:
                problems.append('smooth scrolling not switched off')
            R.add('R14', 'Respects reduced motion', not problems,
                  problems or f"{len(normal['anims'])} animation(s) at load normally, none long or looping under reduced motion")

        R.add('R15', 'No script errors in any run (light, dark, reduced motion)', not errors, errors[:5])
        browser.close()

    write_report(R.rows, out, path, label, date, tz, locale)
    fails = sum(r['result'] == 'FAIL' for r in R.rows)
    warns = sum(r['result'] == 'WARN' for r in R.rows)
    passes = sum(r['result'] == 'PASS' for r in R.rows)
    notrun = sum(r['result'] == 'NOT RUN' for r in R.rows)
    print(f'\n{pathlib.Path(path).name} [{label}]: {passes} pass, {fails} fail, {warns} warn' + (f', {notrun} not run' if notrun else ''))
    RECEIPT.update({'page': str(path), 'state': label, 'pass': passes, 'fail': fails, 'warn': warns,
                    'not_run': [r['id'] for r in R.rows if r['result'] == 'NOT RUN'],
                    'failed': [r['id'] for r in R.rows if r['result'] == 'FAIL'], 'results': str(out / 'results.json')})
    return 1 if fails else (3 if notrun else 0)


def contact_sheet(pairs, dest, gap=10, cap=320):
    """One image: per control, unfocused on the left, focused on the right, red bar when focus showed no change."""
    from PIL import Image, ImageDraw
    rows = []
    for desc, unf, foc, ok in pairs:
        a, b = Image.open(io.BytesIO(unf)).convert('RGB'), Image.open(io.BytesIO(foc)).convert('RGB')
        scale = min(1.0, cap / max(a.width, 1))
        if scale < 1:
            a = a.resize((int(a.width * scale), max(1, int(a.height * scale))))
            b = b.resize((int(b.width * scale), max(1, int(b.height * scale))))
        rows.append((desc, a, b, ok))
    width = 2 * cap + 3 * gap + 8
    height = sum(max(a.height, b.height) + 18 + gap for _, a, b, _ in rows) + gap
    sheet = Image.new('RGB', (width, height), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    y = gap
    for desc, a, b, ok in rows:
        d.rectangle([0, y, 5, y + 16 + max(a.height, b.height)], fill=(40, 160, 70) if ok else (210, 40, 40))
        d.text((gap + 8, y), desc[:80], fill=(20, 20, 20))
        sheet.paste(a, (gap + 8, y + 16)); sheet.paste(b, (2 * gap + 8 + cap, y + 16))
        y += max(a.height, b.height) + 18 + gap
    sheet.save(dest)


def clamp(info, vw, vh, pad=6):
    x0, y0 = max(0, info['x'] - pad), max(0, info['y'] - pad)
    x1, y1 = min(vw, info['x'] + info['w'] + pad), min(vh, info['y'] + info['h'] + pad)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return {'x': x0, 'y': y0, 'width': x1 - x0, 'height': y1 - y0}


def write_report(rows, out, path, label, date, tz, locale='en-AU'):
    fails = [r for r in rows if r['result'] == 'FAIL']
    warns = [r for r in rows if r['result'] == 'WARN']
    title = path.split('#')[0] if path.startswith(('http://', 'https://')) else pathlib.Path(path).name
    lines = [f'# Render gate: {title}', '',
             f'State tested: {label}. Headless Chromium, timezone {tz}, locale {locale}' + (f', clock fixed at {date}' if date else '') + '.',
             f'Run {time.strftime("%d/%m/%Y %H:%M")}.', '',
             f"**{sum(r['result'] == 'PASS' for r in rows)} pass, {len(fails)} fail, {len(warns)} warn, {sum(r['result'] == 'NOT RUN' for r in rows)} not run.**", '',
             '| # | Check | Result | Detail |', '|---|---|---|---|']
    for r in rows:
        d = r['detail'] if isinstance(r['detail'], str) else json.dumps(r['detail'], ensure_ascii=False)
        d = d.replace('|', '/').replace('\n', ' ')[:500]
        lines.append(f"| {r['id']} | {r['check']} | {r['result']} | {d} |")
    lines += ['', 'Screenshots: ' + ', '.join(sorted(p.name for p in out.glob('*.png'))), '',
              'Not covered here: behaviour (does the app do the job correctly), states other than the one tested, '
              'hover and click animations, real devices and screen readers, focus-indicator contrast, and visual judgement. '
              'Use an adapter harness for behaviour and look at the screenshots for design.']
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out / 'results.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding='utf-8')


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page'); ap.add_argument('outdir')
    ap.add_argument('--label', default='first load')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--prep', help='JavaScript file to run after each load')
    g.add_argument('--prep-js', help='JavaScript to run after each load')
    ap.add_argument('--date', help='fix the page clock, e.g. 2026-10-21T10:00:00+10:00')
    ap.add_argument('--tz', default='Australia/Brisbane')
    ap.add_argument('--locale', default='en-AU')
    ap.add_argument('--receipt', help='also write the RECEIPT line to this file')
    ap.add_argument('--version', action='version', version=VERSION)
    a = ap.parse_args(argv)
    prep = pathlib.Path(a.prep).read_text(encoding='utf-8') if a.prep else a.prep_js
    try:
        return run(a.page, a.outdir, a.label, prep, a.date, a.tz, locale=a.locale)
    except ImportError as e:
        print(f'NOT RUN: missing dependency ({e.name or e}); nothing was checked', file=sys.stderr)
        RECEIPT['error'] = f'missing dependency: {e.name or e}'
        return 4

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
    sys.exit(_contract("render_gate", main, sys.argv[1:]))
