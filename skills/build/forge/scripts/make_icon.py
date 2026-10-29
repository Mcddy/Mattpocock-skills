#!/usr/bin/env python3
"""Make a Windows app icon (.ico, 16 to 256 px) and a 512 px PNG from an SVG or PNG mark.

Usage:
  python make_icon.py icon.svg icon.ico          also writes icon.png (512 px) beside the .ico
  python make_icon.py mark.png icon.ico

Draw the mark for 16 px first: two or three bold shapes on a solid rounded square, no text, no thin lines.
An SVG is rendered with Playwright's Chromium (transparent background); a PNG should be square, 512 px or more.

Exit codes: 0 written. 2 bad arguments. 4 could not run (prints NOT RUN with the reason). A converter, not a check.
"""
import io, pathlib, sys

VERSION = "forge 3.3.2"
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def render_svg(svg_path, px=1024):
    from playwright.sync_api import sync_playwright
    svg = pathlib.Path(svg_path).read_text(encoding='utf-8')
    html = ('<!doctype html><html><head><style>html,body{margin:0;background:transparent}svg{display:block;width:%dpx;height:%dpx}</style>'
            '</head><body>%s</body></html>') % (px, px, svg)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': px, 'height': px})
        pg.set_content(html); png = pg.screenshot(omit_background=True, clip={'x': 0, 'y': 0, 'width': px, 'height': px})
        b.close()
    return png


def main(argv):
    if '--version' in argv:
        print(VERSION); return 0
    if '--help' in argv or len(argv) != 2:
        print(__doc__); return 0 if '--help' in argv else 2
    src, out = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    if not src.exists():
        print('make_icon: %s not found' % src, file=sys.stderr); return 2
    if out.suffix.lower() != '.ico':
        print('make_icon: the output must end in .ico', file=sys.stderr); return 2
    try:
        from PIL import Image
    except ImportError:
        print('NOT RUN: Pillow is not installed (pip install pillow)'); return 4
    try:
        data = render_svg(src) if src.suffix.lower() == '.svg' else src.read_bytes()
    except Exception as e:  # noqa: BLE001
        print('NOT RUN: could not render %s (%s)' % (src, str(e)[:200])); return 4
    im = Image.open(io.BytesIO(data)).convert('RGBA')
    if im.width != im.height:
        print('make_icon: the mark must be square (got %dx%d)' % im.size, file=sys.stderr); return 2
    im.resize((512, 512), Image.LANCZOS).save(out.with_suffix('.png'))
    im.save(out, sizes=[(s, s) for s in SIZES])
    print('icon: %s (%s px) and %s' % (out, ', '.join(map(str, SIZES)), out.with_suffix('.png')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
