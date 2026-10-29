#!/usr/bin/env python3
"""Render one page in several visual directions, on a phone and a desktop, as an options board to choose from.

Usage:
  python direction_board.py PAGE OUTDIR [--dirs warm-pop,lime-night,...] [--recommend a,b,c] [--notes notes.json]
                            [--prep-js "JS"] [--query "sample=1"] [--title "Plant round"] [--live-only]

PAGE is an HTML file or an http(s) address. The page must take its colours, type and shapes from the visual kit's
tokens (assets/visual-kit/kit.css, kit2.css and kit3.css), switched by a data-dir attribute: the script sets data-dir
on <html> and on every element that already has one. --prep-js runs after load to reach a populated state (for
example, seed data, or open the main view). It runs once per viewport, so a prep that writes data should be repeatable.

--recommend names the directions you advise for this case (usually three). They come first on every board with a
"Recommended" badge.

--query adds a query string to the page address for both boards: an app that opens empty can load labelled sample
data when it sees, say, ?sample=1, so the live board and the captures show it populated (--prep-js reaches the
captures only).

--notes takes a JSON file mapping a direction to one line on why it fits, for example
{"fresh-green": "Calm morning round; green without the garden-centre look"}; give at least the recommended ones a line.

The default board is the sixteen expressive directions. Ink Paper, the quiet direction for dense professional tools,
is added with --dirs when the case calls for it (for example --dirs ink-paper,coral-editorial,navy-gold,...).

Output in OUTDIR:
  board-live.html   always: a live switcher. The page itself runs in two frames (390 x 844 and 1280 x 800, scaled to
                    fit), and each direction chip switches both. Needs assets/visual-kit/kit-dir.js in the page; the
                    board says so if a frame does not answer. For a PAGE that is a file, the page and everything it
                    links (kit CSS, fonts, images, scripts) are packed into board-live.html itself (with
                    single_file.py's packer), so it opens offline as one file, from anywhere, with no browser needed
                    to make it. The frames load the same file with ?forge-frame=1, which shows the packed page. A
                    page that fetches its data from a server must be given as an http(s) address instead; then the
                    board links to it and the server must be running.
  <dir>-phone.png, <dir>-desktop.png, board.png (a grid), board.html (cards with Pick buttons)
                    unless --live-only. Picking copies a line such as "Direction: lime-night" to paste back.

--live-only skips the browser and Pillow entirely (for hosts without Playwright): only board-live.html is written,
and the hard-coded-colour check below does not run. A board made this way has not been rendered by anyone yet:
it is ready to open, and the report says "board written, not yet viewed" until someone has looked at it.

Warnings (not with --live-only): a direction that defines no --sig; every direction rendering the same colours; and
elements that kept the same background or text colour in every direction (usually a component with a hard-coded
colour, which will also break the dark directions). Drawings inside <svg> are skipped, since they may keep their
subject's colours.

Why this exists: a direction is chosen faster and better from rendered options on the real screen than from words.
It is a board, not a design review: look at the captures, then run the craft test on the chosen one.

Needs Python playwright with Chromium, and Pillow (except with --live-only, which needs only Python).
Exit codes (references/results.md): 0 completed (with --live-only: the live board was written; captures were not
requested). 2 usage error. 3 partial: the live board was written but the captures could not run (prints NOT RUN).
4 runner error: nothing usable was written. Every run ends with one RECEIPT line on stderr, which also records the
semantic check of the board: the directions it holds, in order, their count, and whether the page was packed in.
"""
import argparse, html, json, os, pathlib, sys, urllib.parse

VERSION = "forge 3.3.2"
DEFAULT = ['warm-pop', 'lime-night', 'lilac-soft', 'fresh-green', 'coral-editorial', 'sky-illustrated', 'mono-flood', 'candy-pastel',
           'cherry-noir', 'aqua-mint', 'rose-studio', 'terracotta-arch', 'arcade-pixel', 'navy-gold', 'photo-bold', 'plum-peach']
NAMES = {'warm-pop': 'Warm Pop', 'lime-night': 'Lime Night', 'lilac-soft': 'Lilac Soft', 'fresh-green': 'Fresh Green',
         'coral-editorial': 'Coral Editorial', 'sky-illustrated': 'Sky Illustrated', 'mono-flood': 'Mono Flood',
         'candy-pastel': 'Candy Pastel', 'cherry-noir': 'Cherry Noir', 'aqua-mint': 'Aqua Mint', 'rose-studio': 'Rose Studio',
         'terracotta-arch': 'Terracotta Arch', 'arcade-pixel': 'Arcade Pixel', 'navy-gold': 'Navy Gold', 'photo-bold': 'Photo Bold',
         'plum-peach': 'Plum Peach', 'ink-paper': 'Ink Paper'}

SET_DIR = """(d) => { document.documentElement.setAttribute('data-dir', d);
  document.querySelectorAll('[data-dir]').forEach(e => e.setAttribute('data-dir', d)); return document.fonts.ready.then(() => true); }"""
PROBE = """() => { const cs = getComputedStyle(document.documentElement);
  return {bg: getComputedStyle(document.body).backgroundColor, sig: cs.getPropertyValue('--sig').trim()}; }"""
# Per element: a stable path, its background if visible, and its text colour if it holds text of its own.
ELEMENTS = """() => {
  const path = e => { const parts = []; while (e && e.nodeType === 1 && e !== document.body) {
      let p = e.tagName.toLowerCase(); if (e.id) { parts.unshift(p + '#' + e.id); break; }
      const cls = typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\\s+/)[0] : '';
      const sib = e.parentElement ? [...e.parentElement.children].indexOf(e) + 1 : 1;
      parts.unshift(p + cls + ':nth-child(' + sib + ')'); e = e.parentElement; } return parts.join(' > '); };
  const out = {};
  for (const e of document.body.querySelectorAll('*')) {
    if (e.closest('svg') || /^(SCRIPT|STYLE|TEMPLATE)$/.test(e.tagName)) continue;
    const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const cs = getComputedStyle(e); if (cs.visibility !== 'visible') continue;
    const bg = cs.backgroundColor, hasBg = !/^(transparent|rgba\\(0, 0, 0, 0\\))$/.test(bg);
    const ownText = [...e.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim());
    if (!hasBg && !ownText) continue;
    out[path(e)] = [hasBg ? bg : null, ownText ? cs.color : null];
  }
  return out; }"""


def capture(page_url, dirs, prep, out):
    from playwright.sync_api import sync_playwright
    shots, probes, elements = {}, {}, {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for kind, vp in (('phone', {'width': 390, 'height': 844}), ('desktop', {'width': 1280, 'height': 800})):
            ctx = b.new_context(viewport=vp, device_scale_factor=2 if kind == 'phone' else 1, locale='en-AU', timezone_id='Australia/Brisbane')
            pg = ctx.new_page()
            pg.goto(page_url); pg.wait_for_load_state('load'); pg.wait_for_timeout(600)
            if prep:
                pg.evaluate('async () => { %s\n }' % prep); pg.wait_for_timeout(500)
            for d in dirs:
                pg.evaluate(SET_DIR, d); pg.wait_for_timeout(250)
                probes.setdefault(d, pg.evaluate(PROBE))
                if kind == 'desktop':
                    elements[d] = pg.evaluate(ELEMENTS)
                f = out / f'{d}-{kind}.png'
                pg.screenshot(path=str(f))
                shots[(d, kind)] = f
            ctx.close()
        b.close()
    return shots, probes, elements


def unchanged(elements, dirs):
    """Elements whose background, or own text colour, is the same in every direction."""
    if len(dirs) < 2:
        return [], []
    common = set.intersection(*(set(elements[d]) for d in dirs))
    bgs, texts = [], []
    for k in sorted(common):
        vals = [elements[d][k] for d in dirs]
        if vals[0][0] and all(v[0] == vals[0][0] for v in vals):
            bgs.append((k, vals[0][0]))
        if vals[0][1] and all(v[1] == vals[0][1] for v in vals):
            texts.append((k, vals[0][1]))
    return bgs, texts


def font(size):
    from PIL import ImageFont
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
              '/Library/Fonts/Arial Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow before 10.1
        return ImageFont.load_default()


def board_png(dirs, shots, out, title, notes, rec):
    from PIL import Image, ImageDraw
    cell_w, cell_h, pad, head = 1180, 700, 30, 96
    cols = 2
    rows = (len(dirs) + cols - 1) // cols
    W, H = cols * cell_w + (cols + 1) * pad, rows * cell_h + (rows + 1) * pad + head
    board = Image.new('RGB', (W, H), (24, 24, 24))
    dr = ImageDraw.Draw(board)
    f_title, f_name, f_note, f_badge = font(38), font(30), font(21), font(19)
    sub = ' (recommended first)' if rec else ''
    dr.text((pad, 28), f'{title}: {len(dirs)} directions, phone and desktop{sub}', fill=(240, 240, 240), font=f_title)
    for i, d in enumerate(dirs):
        x0 = pad + (i % cols) * (cell_w + pad); y0 = head + pad + (i // cols) * (cell_h + pad)
        dr.rounded_rectangle([x0, y0, x0 + cell_w, y0 + cell_h], 24, fill=(52, 46, 30) if d in rec else (36, 36, 36),
                             outline=(240, 200, 90) if d in rec else None, width=3)
        label = f'{i + 1}. {NAMES.get(d, d)}'
        dr.text((x0 + 24, y0 + 18), label, fill=(255, 255, 255), font=f_name)
        if d in rec:
            bx = x0 + 24 + dr.textlength(label, font=f_name) + 16
            bw = dr.textlength('Recommended', font=f_badge) + 28
            dr.rounded_rectangle([bx, y0 + 20, bx + bw, y0 + 52], 16, fill=(240, 200, 90))
            dr.text((bx + 14, y0 + 25), 'Recommended', fill=(30, 24, 10), font=f_badge)
        note = notes.get(d, '')
        lines = []
        if note:                                   # wrap the note to two lines within the cell
            words, line = note.split(), ''
            for w in words:
                trial = (line + ' ' + w).strip()
                if dr.textlength(trial, font=f_note) <= cell_w - 48:
                    line = trial
                else:
                    lines.append(line); line = w
            lines.append(line)
            if len(lines) > 2:
                lines = [lines[0], lines[1]]
                while dr.textlength(lines[1] + '...', font=f_note) > cell_w - 48 and ' ' in lines[1]:
                    lines[1] = lines[1].rsplit(' ', 1)[0]
                lines[1] += '...'
            for k, ln in enumerate(lines):
                dr.text((x0 + 24, y0 + 60 + 26 * k), ln, fill=(200, 200, 200), font=f_note)
        top = y0 + 66 + 26 * len(lines) + (6 if lines else 0)
        ph = Image.open(shots[(d, 'phone')]).convert('RGB'); ph.thumbnail((270, cell_h - (top - y0) - 20))
        dk = Image.open(shots[(d, 'desktop')]).convert('RGB'); dk.thumbnail((850, cell_h - (top - y0) - 20))
        board.paste(ph, (x0 + 24, top)); board.paste(dk, (x0 + 24 + ph.width + 24, top))
    board.save(out / 'board.png')


PICK_JS = """document.querySelectorAll('[data-pick]').forEach(b=>b.addEventListener('click',()=>{const t='Direction: '+b.dataset.pick;
const o=document.getElementById('out');o.textContent=t+' (copy this into the chat)';try{navigator.clipboard.writeText(t).then(()=>o.textContent=t+' (copied)',()=>{})}catch(e){}}));"""
BASE_CSS = """body{margin:0;background:#161616;color:#f4f4f4;font:16px/1.45 system-ui,sans-serif} main{max-width:1600px;margin:0 auto;padding:24px 16px}
h1{font-size:24px;margin:0 0 4px} .lead{color:#b8b8b8;margin:0 0 18px} button{font:600 14px system-ui;border:0;border-radius:999px;padding:10px 16px;min-height:44px;cursor:pointer;flex:none}
button:focus-visible{outline:3px solid #9ad;outline-offset:2px} .badge{display:inline-block;margin-left:8px;padding:3px 9px;border-radius:999px;background:#f0c85a;color:#1e180a;font:700 12px/1.2 system-ui;vertical-align:2px}
#out{position:sticky;bottom:0;background:#000;padding:12px 16px;border-radius:14px;margin-top:16px}"""

BOARD_HTML = """<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@: directions</title><style>@@BASE@@
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,800px),1fr));gap:16px}
.opt{margin:0;background:#232323;border-radius:20px;padding:16px} .opt.is-rec{background:#2e2a1d;box-shadow:inset 0 0 0 2px #f0c85a}
figcaption{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px} figcaption .why{margin:4px 0 0;font-size:14px;color:#c8c8c8}
.pair{display:flex;gap:14px;align-items:flex-start;overflow-x:auto} img{border-radius:14px;display:block;height:auto;max-width:100%} button{background:#f4f4f4;color:#161616}
</style></head><body><main><h1>@@TITLE@@: pick a direction</h1><p class="lead">The same screen and data in each direction@@RECFIRST@@. Open a capture to see it full size; board-live.html shows the page itself.</p>
<div class="grid">@@CARDS@@</div><div id="out" role="status">Nothing picked yet.</div></main>
<script>@@PICK@@</script>
</body></html>"""

LIVE_HTML = """<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">@@FRAMESHIM@@
<title>@@TITLE@@: live directions</title><style>@@BASE@@
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px} .chip{background:#262626;color:#f4f4f4;padding:8px 14px} .chip[aria-pressed="true"]{background:#f4f4f4;color:#161616}
.chip.is-rec{box-shadow:inset 0 0 0 2px #f0c85a} .chip .star{color:#f0c85a;margin-left:6px;font-size:12px} .chip[aria-pressed="true"] .star{color:#7a5a00}
.row{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;justify-content:space-between;margin:0 0 14px} .why{margin:0;color:#d0d0d0;max-width:80ch;min-height:1.45em}
.pick{background:#f0c85a;color:#1e180a} .warn{margin:0 0 12px;padding:10px 14px;border-radius:12px;background:#3a2414;color:#ffd9b8}
.stage{display:flex;gap:18px;align-items:flex-start;justify-content:center;background:#0d0d0d;border-radius:18px;padding:18px;overflow:hidden}
.dev p{margin:0 0 8px;font:700 11.5px/1 system-ui;letter-spacing:.08em;text-transform:uppercase;color:#a8a8a8}
.box{position:relative;overflow:hidden;border-radius:22px;box-shadow:0 16px 40px rgba(0,0,0,.4);background:#222} .box.desk{border-radius:10px}
.box iframe{border:0;transform-origin:0 0;position:absolute;left:0;top:0;background:#fff}
@media (max-width:760px){.stage{flex-direction:column;align-items:center}}
</style></head><body><main><h1>@@TITLE@@: pick a direction</h1>
<p class="lead">Your page, live, in each direction@@RECFIRST@@. Scroll and use the page inside the frames; the chips switch both.</p>
<div class="chips" id="chips" role="group" aria-label="Directions"></div>
<div class="row"><p class="why" id="why"></p><button type="button" class="pick" id="pick">Pick</button></div>
<p class="warn" id="warn" hidden>The page did not answer the switch. Add the kit's kit-dir.js to it (a script tag in the page head) so the board can change its direction.</p>
<div class="stage" id="stage">
  <div class="dev"><p>Phone, 390 px</p><div class="box" id="box-phone"><iframe id="f-phone" title="The page at phone size" width="390" height="844"></iframe></div></div>
  <div class="dev"><p>Desktop, 1280 px</p><div class="box desk" id="box-desk"><iframe id="f-desk" title="The page at desktop size" width="1280" height="800"></iframe></div></div>
</div>
<div id="out" role="status">Nothing picked yet.</div></main>
<script>
const D = @@DATA@@;@@SELFSRC@@
const frames = [document.getElementById('f-phone'), document.getElementById('f-desk')];
const chips = document.getElementById('chips'), why = document.getElementById('why'), warn = document.getElementById('warn');
let current = D.dirs[0].id, acks = 0, timer = null;
chips.innerHTML = D.dirs.map(d => `<button type="button" class="chip${d.rec ? ' is-rec' : ''}" data-dir="${d.id}" aria-pressed="false">${d.name}${d.rec ? '<span class="star">Recommended</span>' : ''}</button>`).join('');
function send(f) { try { f.contentWindow.postMessage({ forgeDir: current }, '*'); } catch (e) {} }
function show(id) {
  current = id; acks = 0;
  chips.querySelectorAll('.chip').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.dir === id)));
  const d = D.dirs.find(x => x.id === id); why.textContent = d.note || '';
  document.getElementById('pick').textContent = 'Pick ' + d.name;
  frames.forEach(send);
  clearTimeout(timer); timer = setTimeout(() => { warn.hidden = acks > 0; }, 2000);
}
window.addEventListener('message', e => { if (e.data && e.data.forgeDirApplied === current) { acks++; warn.hidden = true; } });
frames.forEach(f => { f.addEventListener('load', () => send(f)); f.src = D.src + (D.src.includes('?') ? '&' : '?') + 'dir=' + encodeURIComponent(current); });
chips.addEventListener('click', e => { const b = e.target.closest('[data-dir]'); if (b) show(b.dataset.dir); });
document.getElementById('pick').addEventListener('click', () => { const t = 'Direction: ' + current, o = document.getElementById('out');
  o.textContent = t + ' (copy this into the chat)'; try { navigator.clipboard.writeText(t).then(() => o.textContent = t + ' (copied)', () => {}); } catch (e) {} });
const stage = document.getElementById('stage');
function fit() {
  const W = stage.clientWidth - 36, narrow = matchMedia('(max-width: 760px)').matches;
  let ps, ds;
  if (narrow) { ps = Math.min(1, W / 390); ds = Math.min(1, W / 1280); }
  else { ps = Math.max(0.45, Math.min(0.8, (W - 18) / (390 + 1280 * 0.62))); ds = Math.min(1, (W - 18 - 390 * ps) / 1280); }
  [[frames[0], 'box-phone', 390, 844, ps], [frames[1], 'box-desk', 1280, 800, ds]].forEach(([f, id, w, h, s]) => {
    f.style.transform = `scale(${s})`; const b = document.getElementById(id); b.style.width = (w * s) + 'px'; b.style.height = (h * s) + 'px'; });
}
addEventListener('resize', fit); fit(); show(current);
</script></body></html>"""


def fill(tpl, **kv):
    for k, v in kv.items():
        tpl = tpl.replace('@@' + k + '@@', v)
    return tpl


def board_html(dirs, out, title, notes, rec):
    cards = []
    for i, d in enumerate(dirs):
        n = html.escape(NAMES.get(d, d))
        badge = '<span class="badge">Recommended</span>' if d in rec else ''
        note = f'<p class="why">{html.escape(notes[d])}</p>' if notes.get(d) else ''
        cls = 'opt is-rec' if d in rec else 'opt'
        cards.append(f'<figure class="{cls}"><figcaption><div><b>{i + 1}. {n}</b>{badge}{note}</div><button type="button" data-pick="{d}">Pick {n}</button></figcaption>\n'
                     f'<div class="pair"><a href="{d}-phone.png"><img src="{d}-phone.png" alt="{n} on a phone" width="195" height="422"></a>\n'
                     f'<a href="{d}-desktop.png"><img src="{d}-desktop.png" alt="{n} on a desktop" width="560" height="350"></a></div></figure>')
    page = fill(BOARD_HTML, TITLE=html.escape(title), BASE=BASE_CSS, RECFIRST=', recommended first' if rec else '', CARDS=''.join(cards), PICK=PICK_JS)
    (out / 'board.html').write_text(page, encoding='utf-8')


def page_src(page, out):
    """The address board-live.html uses for PAGE: the URL itself, or a path relative to OUTDIR so the two travel together."""
    if page.startswith(('http://', 'https://')):
        return page
    target = pathlib.Path(page).resolve()
    try:
        rel = os.path.relpath(target, out.resolve())
        return urllib.parse.quote(pathlib.PurePath(rel).as_posix())
    except ValueError:  # another drive on Windows
        return target.as_uri()


# Standalone board (forge 3.3): plumbing only. The page is packed into the board file; a frame that loads the board
# with ?forge-frame=1 writes the packed page in place of the board (the trailing <plaintext> hides the board markup
# that follows). Nothing about the board's own markup, styles, directions or behaviour changes.
FRAME_SHIM = """<script>if (/[?&]forge-frame=1(&|$)/.test(location.search)) document.write(@@PAGE@@ + '<plaintext hidden>');</script>"""
SELF_SRC = """ if (D.self) D.src = location.href.split(/[?#]/)[0] + '?forge-frame=1' + (D.q ? '&' + D.q : '');"""


def packed_page(page):
    """The page with everything it links inlined, via single_file.pack (loaded by path, so it works under python -I)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('forge_single_file', pathlib.Path(__file__).resolve().parent / 'single_file.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.pack(page)


def owned_payload(written, nonce):
    """The board's own data, read back from between this run's markers (never the first 'const D' in the file: the
    packed page sits before it and may contain one)."""
    a, b = '/*forge-board-data:%s*/' % nonce, '/*end-forge-board-data:%s*/' % nonce
    if written.count(a) != 1 or written.count(b) != 1:
        return None
    return json.loads(written.split(a, 1)[1].split(b, 1)[0].replace('<\\/', '</'))


def board_live(dirs, out, title, notes, rec, src, packed=None, q='', nonce=''):
    items = [{'id': d, 'name': NAMES.get(d, d), 'note': notes.get(d, ''), 'rec': d in rec} for d in dirs]
    mark = lambda s: '/*forge-board-data:%s*/%s/*end-forge-board-data:%s*/' % (nonce, s, nonce)
    if packed is None:
        data = mark(json.dumps({'src': src, 'dirs': items}).replace('</', '<\\/'))
        page = fill(LIVE_HTML, TITLE=html.escape(title), BASE=BASE_CSS, RECFIRST=', recommended first' if rec else '', DATA=data,
                    FRAMESHIM='', SELFSRC='')
    else:
        data = mark(json.dumps({'src': '', 'self': True, 'q': q, 'dirs': items}).replace('</', '<\\/'))
        shim = FRAME_SHIM.replace('@@PAGE@@', json.dumps(packed).replace('<', '\\u003c'))  # no '<' inside the script at all
        page = fill(LIVE_HTML, TITLE=html.escape(title), BASE=BASE_CSS, RECFIRST=', recommended first' if rec else '', DATA=data,
                    FRAMESHIM=shim, SELFSRC=SELF_SRC)
    (out / 'board-live.html').write_text(page, encoding='utf-8')
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page'); ap.add_argument('outdir')
    ap.add_argument('--dirs', default=','.join(DEFAULT))
    ap.add_argument('--recommend', default='', help='comma-separated directions to badge and show first')
    ap.add_argument('--prep-js')
    ap.add_argument('--title', default='Options')
    ap.add_argument('--notes', help='JSON file: {"direction": "why it fits this case"}')
    ap.add_argument('--live-only', action='store_true', help='write board-live.html only; no browser or Pillow needed')
    ap.add_argument('--query', default='', help='added to the page address for the captures and the live board, e.g. "sample=1" for an app that starts empty and loads labelled sample data with that flag')
    ap.add_argument('--version', action='version', version=VERSION)
    a = ap.parse_args(argv)
    dirs = [d.strip() for d in a.dirs.split(',') if d.strip()]
    rec = [d.strip() for d in a.recommend.split(',') if d.strip()]
    unknown = [d for d in rec if d not in dirs]
    if unknown:
        print('direction_board: --recommend names directions not on the board: ' + ', '.join(unknown), file=sys.stderr); return 2
    dirs = rec + [d for d in dirs if d not in rec]
    notes = {}
    if a.notes:
        try:
            notes = json.loads(pathlib.Path(a.notes).read_text(encoding='utf-8'))
            assert isinstance(notes, dict)
        except Exception as e:  # noqa: BLE001
            print(f'direction_board: --notes must be a JSON object of direction to text ({e})', file=sys.stderr); return 2
    if not a.page.startswith(('http://', 'https://')) and not pathlib.Path(a.page).exists():
        print(f'direction_board: no such page: {a.page}', file=sys.stderr); return 2
    out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    q = a.query.lstrip('?&')
    addq = (lambda u: u + ('&' if '?' in u else '?') + q) if q else (lambda u: u)
    served = a.page.startswith(('http://', 'https://'))
    packed, remote = (None, [])
    if not served:
        try:
            packed, remote = packed_page(a.page)
        except FileNotFoundError as e:
            print(f'direction_board: a file the page links is missing: {e}', file=sys.stderr); return 2
    import hashlib, secrets
    nonce = secrets.token_hex(8)
    written = board_live(dirs, out, a.title, notes, set(rec), addq(page_src(a.page, out)), packed, q, nonce)
    # semantic check of what was written, not just that a file exists: the directions, in order, read back from this
    # run's own marked payload, and the page inside
    payload = owned_payload(written, nonce)
    held = [x['id'] for x in payload['dirs']] if payload else []
    RECEIPT.update({'board_live': str(out / 'board-live.html'), 'directions': held, 'direction_count': len(held),
                    'directions_match_request': held == dirs, 'default_sixteen_in_order': held == DEFAULT if a.dirs == ','.join(DEFAULT) and not rec else None,
                    'page_packed_in': packed is not None, 'remote_refs': sorted(set(remote)), 'rendered': False,
                    'bytes': len(written.encode('utf-8')), 'board_sha256': hashlib.sha256(written.encode('utf-8')).hexdigest(),
                    'packed_page_sha256': hashlib.sha256(packed.encode('utf-8')).hexdigest() if packed is not None else None,
                    'payload_found': payload is not None})
    if held != dirs:
        print('direction_board: the written board does not hold the requested directions', file=sys.stderr); return 4
    print(f'live board: {out / "board-live.html"} ({len(dirs)} directions' + (', page packed in: opens offline as one file)' if packed is not None else ', links to the running page)'))
    for r in sorted(set(remote)):
        print(f'WARNING: the page still points outside itself, so the board needs the network for: {r}')
    if rec and any(not notes.get(d) for d in rec):
        print('NOTE: give each recommended direction a --notes line saying why it fits')
    if a.live_only:
        print('NOTE: --live-only: no captures and no hard-coded-colour check were run. Board written, not yet viewed: '
              'open board-live.html and look at every direction before calling it rendered.')
        RECEIPT['captures'] = 'not requested (--live-only)'
        return 0
    url = addq(a.page if a.page.startswith(('http://', 'https://')) else pathlib.Path(a.page).resolve().as_uri())
    try:
        shots, probes, elements = capture(url, dirs, a.prep_js, out)
    except Exception as e:  # noqa: BLE001
        print(f'NOT RUN: {e!r}'[:300] + ' (board-live.html was still written; --live-only skips the browser)')
        RECEIPT['captures'] = 'not run: ' + repr(e)[:200]
        return 3
    missing_sig = [d for d in dirs if not probes[d]['sig']]
    same = len({json.dumps(v, sort_keys=True) for v in probes.values()}) == 1 and len(dirs) > 1
    bgs, texts = unchanged(elements, dirs)
    board_png(dirs, shots, out, a.title, notes, set(rec)); board_html(dirs, out, a.title, notes, set(rec))
    print(f'board: {out / "board.png"} and {out / "board.html"} ({len(dirs)} directions)')
    RECEIPT.update({'captures': 'run', 'rendered': True, 'board_png': str(out / 'board.png'),
                    'captured_directions': [d for d in dirs if (d, 'phone') in shots and (d, 'desktop') in shots]})
    if missing_sig:
        print('WARNING: no --sig token under ' + ', '.join(missing_sig) + ': include kit.css, kit2.css and kit3.css, or define these directions')
    if same:
        print('WARNING: every direction rendered the same colours: does the page take its colours from the kit tokens?')
    for label, items in (('background', bgs), ('text colour', texts)):
        if items:
            print(f'WARNING: {len(items)} element(s) kept the same {label} in every direction (a hard-coded colour?):')
            for k, v in items[:8]:
                print(f'  {v:24} ' + ' > '.join(k.split(' > ')[-4:]))
            if len(items) > 8:
                print(f'  ... and {len(items) - 8} more')
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
    sys.exit(_contract("direction_board", main, sys.argv[1:]))
