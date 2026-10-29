#!/usr/bin/env python3
"""Embed open-licence web fonts in a page as base64 @font-face rules, so the page keeps its type offline,
in sandboxed previews and when outside requests are blocked.

Usage:
  python embed_fonts.py "Bricolage Grotesque:700,800" "Plus Jakarta Sans:500,700" > fonts.css
  python embed_fonts.py --list-dir DIR ...       look for fonts in DIR/node_modules/@fontsource instead of the cache

Fonts are looked for first in the visual kit (../assets/visual-kit/fonts: the faces the seventeen directions use, no
network needed), then in the @fontsource packages from the npm registry (open-licence families from Google Fonts,
latin subset, woff2). A package that is missing is installed with npm into a cache folder (~/.cache/forge-fonts),
which needs npm and registry access. Each weight adds about 12 to 30 KB before base64 (about a third more after).

Pick faces for the words, not by habit: forge's guidance rules out Inter, Geist, Poppins and Montserrat as
defaults, and the Space Grotesk with Instrument Serif pairing.

Exit codes: 0 printed CSS. 2 bad arguments. 4 could not get a font (prints NOT RUN with the reason). A converter,
not a check: exit 0 says the CSS was written, nothing about the page.
"""
import base64, os, pathlib, re, subprocess, sys

VERSION = "forge 3.3.2"


def slug(family):
    return re.sub(r'[^a-z0-9]+', '-', family.lower()).strip('-')


KIT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'visual-kit' / 'fonts'


def find(base, family, weight):
    name = f'{slug(family)}-latin-{weight}-normal.woff2'
    for f in (KIT / name, base / 'node_modules' / '@fontsource' / slug(family) / 'files' / name):
        if f.exists():
            return f
    return None


def main(argv):
    if '--version' in argv:
        print(VERSION); return 0
    if '--help' in argv or '-h' in argv:
        print(__doc__); return 0
    base = pathlib.Path(os.path.expanduser('~/.cache/forge-fonts'))
    if '--list-dir' in argv:
        i = argv.index('--list-dir')
        if i + 1 >= len(argv):
            print('embed_fonts: --list-dir needs a folder', file=sys.stderr); return 2
        base = pathlib.Path(argv[i + 1]); argv = argv[:i] + argv[i + 2:]
    specs = [a for a in argv if not a.startswith('--')]
    if not specs:
        print(__doc__); return 2
    wanted = []
    for s in specs:
        if ':' not in s:
            print('embed_fonts: give each font as "Family:weight,weight", got %r' % s, file=sys.stderr); return 2
        fam, ws = s.split(':', 1)
        try:
            weights = [int(w) for w in ws.split(',') if w.strip()]
        except ValueError:
            print('embed_fonts: weights must be numbers like 400,700, got %r' % ws, file=sys.stderr); return 2
        wanted.append((fam.strip(), weights))
    missing = sorted({fam for fam, ws in wanted for w in ws if not find(base, fam, w)})
    if missing:
        base.mkdir(parents=True, exist_ok=True)
        pkgs = ['@fontsource/' + slug(f) for f in missing]
        r = subprocess.run(['npm', 'install', '--prefix', str(base), '--no-audit', '--no-fund', *pkgs], capture_output=True, text=True)
        if r.returncode != 0:
            lines = (r.stderr or r.stdout).strip().splitlines()
            why = next((l for l in lines if '404' in l), lines[-1] if lines else 'no output')
            print('NOT RUN: npm could not install %s (%s)' % (', '.join(pkgs), why.strip()), file=sys.stderr)
            return 4
    out = [f'/* Embedded by embed_fonts.py: {", ".join(s for s in specs)}. Open-licence fonts from @fontsource. */']
    for fam, weights in wanted:
        for w in weights:
            f = find(base, fam, w)
            if not f:
                print('NOT RUN: %s weight %d is not in @fontsource/%s (check the family name and that the weight exists)' % (fam, w, slug(fam)), file=sys.stderr)
                return 4
            b64 = base64.b64encode(f.read_bytes()).decode()
            out.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
                       f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    sys.stdout.write('\n'.join(out) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
