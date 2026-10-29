"""Worked example: the grooming-book direction board (eight directions, three phone screens and a desktop view each).
Builds out/board.html with embedded fonts from ../fonts, and with --shots renders out/shots/*.png. Run from this folder."""
import base64, pathlib, sys

ROOT = pathlib.Path(__file__).parent
FONTS = {  # family: (package, weights)
    'Bricolage Grotesque': ('bricolage-grotesque', (600, 700, 800)),
    'Plus Jakarta Sans': ('plus-jakarta-sans', (500, 600, 700)),
    'Sora': ('sora', (600, 700)),
    'Manrope': ('manrope', (500, 600, 700)),
    'Outfit': ('outfit', (500, 600, 700)),
    'Fraunces': ('fraunces', (600, 700)),
    'DM Sans': ('dm-sans', (500, 600, 700)),
    # Second set of directions (kit2.css, gallery2.js)
    'Schibsted Grotesk': ('schibsted-grotesk', (500, 600, 700, 800, 900)),
    'Rubik': ('rubik', (600, 700, 800)),
    'Figtree': ('figtree', (500, 600, 700, 800)),
    'Anton': ('anton', (400,)),
    'Archivo': ('archivo', (500, 600, 700, 800)),
    'Fredoka': ('fredoka', (500, 600, 700)),
    'Nunito': ('nunito', (600, 700, 800)),
}
CSS = ('../kit.css', '../kit2.css')        # later files extend earlier ones
JS = ('../illustrations.js', 'gallery.js', 'gallery2.js')   # gallery2.js appends to #board after gallery.js renders


def font_css():
    out = []
    for fam, (pkg, weights) in FONTS.items():
        for w in weights:
            f = ROOT.parent / 'fonts' / f'{pkg}-latin-{w}-normal.woff2'
            b64 = base64.b64encode(f.read_bytes()).decode()
            out.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
                       f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return '\n'.join(out)


def build(out_path):
    css = '\n'.join((ROOT / f).read_text() for f in CSS)
    js = '\n'.join(f'<script>{(ROOT / f).read_text()}</script>' for f in JS)
    html = f"""<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Direction board: grooming book</title>
<style>{font_css()}
html,body{{margin:0;background:#1a1a1a}}
{css}</style></head><body><main id="board"></main>{js}</body></html>"""
    pathlib.Path(out_path).write_text(html)
    print('wrote', out_path, len(html) // 1024, 'KB')


def shots(html_path, out_dir, scale=1, only=None):
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=scale)
        pg.goto(pathlib.Path(html_path).resolve().as_uri())
        pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(500)
        for el in pg.locator('section.shot, section.desk-shot').all():
            sid = el.get_attribute('id')
            if only and not any(o in sid for o in only):
                continue
            el.screenshot(path=str(out / f'{sid}.png'))
            print('shot', sid)
        b.close()


if __name__ == '__main__':
    target = ROOT / 'out/board.html'
    target.parent.mkdir(exist_ok=True)
    build(target)
    if '--shots' in sys.argv:
        only = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--only=')]  # e.g. --only=coral
        shots(target, ROOT / 'out/shots', scale=2 if '--hi' in sys.argv else 1, only=only or None)
