#!/usr/bin/env python3
"""Pack a multi-file page into ONE self-contained HTML file (Demo tier, or anything that must open offline).

Usage:
  python single_file.py PAGE.html OUT.html [--keep-fonts "Fraunces,DM Sans"] [--dir fresh-green]

Inlines every local stylesheet (<link rel="stylesheet" href="...">), script (<script src="...">), image
(<img src>, CSS url(...)) and font, as text or data: URIs, so OUT.html works with no other files and no
network. Remote URLs (http, https, //) are left alone and listed, because a demo that needs them is not
offline. --keep-fonts keeps only the @font-face rules for the named families (the chosen direction's faces),
which cuts the file from about 2 MB to a few hundred KB. --dir sets data-dir on <html>, drops the kit-dir.js
switcher and drops the CSS rules that only style other directions, so the file opens in the chosen direction.

Exit codes: 0 written (remote references, if any, are listed as WARNING). 2 bad arguments or a missing file.
It is a converter, not a check: exit 0 says the file was written, nothing about whether the page works.
pack() is also used by direction_board.py to make a board that opens with no other files.
"""
import base64, mimetypes, pathlib, re, sys

VERSION = "forge 3.3.2"
REMOTE = re.compile(r'^(https?:)?//', re.I)
mimetypes.add_type('font/woff2', '.woff2'); mimetypes.add_type('image/svg+xml', '.svg')


def data_uri(path):
    mt = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    return 'data:%s;base64,%s' % (mt, base64.b64encode(path.read_bytes()).decode())


def inline_css(css, base, remote, keep):
    if keep is not None:
        def keep_face(m):
            fam = re.search(r"font-family:\s*['\"]?([^;'\"]+)", m.group(0))
            return m.group(0) if fam and fam.group(1).strip() in keep else ''
        css = re.sub(r'@font-face\s*\{[^}]*\}', keep_face, css)

    def url(m):
        ref = m.group(2).strip()
        if ref.startswith('data:') or ref.startswith('#'):
            return m.group(0)
        if REMOTE.match(ref):
            remote.append(ref); return m.group(0)
        p = (base / ref.split('?')[0].split('#')[0]).resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        return 'url(%s)' % data_uri(p)
    return re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", url, css)


DIR_RE = re.compile(r'\[data-dir=["\']?([a-z0-9-]+)["\']?\]')


def prune_dirs(css, keep):
    """Drop top-level rules (and rules inside @media) that only style other directions."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find('{', i)
        if j < 0:
            out.append(css[i:]); break
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {'{': 1, '}': -1}.get(css[k], 0); k += 1
        prelude, body = css[i:j], css[j + 1:k - 1]
        if prelude.strip().startswith('@media') or prelude.strip().startswith('@supports'):
            out.append(prelude + '{' + prune_dirs(body, keep) + '}')
        else:
            dirs = set(DIR_RE.findall(prelude))
            if not dirs or keep in dirs or prelude.strip() == '[data-dir]':
                out.append(css[i:k])
        i = k
    return ''.join(out)


def pack(page, keep=None, direction=None):
    """Return (html, remote_refs) for PAGE with its local stylesheets, scripts, images and fonts inlined.
    Raises FileNotFoundError naming a linked file that is missing."""
    page = pathlib.Path(page)
    base, html, remote = page.parent, page.read_text(encoding='utf-8'), []
    def link(m):
        tag = m.group(0); hm = re.search(r'href=["\']([^"\']+)', tag)
        if not hm:
            return tag
        href = hm.group(1)
        if REMOTE.match(href):
            remote.append(href); return tag
        p = (base / href).resolve()
        css = inline_css(p.read_text(encoding='utf-8'), p.parent, remote, keep)
        return '<style>\n%s\n</style>' % (prune_dirs(css, direction) if direction else css)
    html = re.sub(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', link, html, flags=re.I)

    def script(m):
        src = m.group(1)
        if REMOTE.match(src):
            remote.append(src); return m.group(0)
        if direction and src.endswith('kit-dir.js'):
            return ''
        body = (base / src).resolve().read_text(encoding='utf-8').replace('</script', '<\\/script')
        return '<script>\n%s\n</script>' % body
    html = re.sub(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>\s*</script>', script, html, flags=re.I)

    def img(m):
        src = m.group(2)
        if src.startswith('data:') or REMOTE.match(src):
            if REMOTE.match(src): remote.append(src)
            return m.group(0)
        return m.group(1) + data_uri((base / src).resolve()) + m.group(3)
    html = re.sub(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])', img, html, flags=re.I)
    html = re.sub(r'<style>(.*?)</style>', lambda m: '<style>%s</style>' % inline_css(m.group(1), base, remote, keep), html, flags=re.S)
    if direction:
        html, n = re.subn(r'(<html\b[^>]*?)\sdata-dir=["\'][^"\']*["\']', r'\1', html, count=1)
        html = re.sub(r'<html\b', '<html data-dir="%s"' % direction, html, count=1)
    return html, remote


def main(argv):
    if '--version' in argv:
        print(VERSION); return 0
    if '--help' in argv:
        print(__doc__); return 0
    keep = direction = None
    args = []
    it = iter(argv)
    for a in it:
        if a == '--keep-fonts':
            keep = {f.strip() for f in next(it, '').split(',') if f.strip()}
        elif a == '--dir':
            direction = next(it, '')
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__); return 2
    page, out = pathlib.Path(args[0]), pathlib.Path(args[1])
    if not page.exists():
        print('single_file: %s not found' % page, file=sys.stderr); return 2
    try:
        html, remote = pack(page, keep, direction)
    except FileNotFoundError as e:
        print('single_file: a file the page links is missing: %s' % e, file=sys.stderr); return 2
    out.write_text(html, encoding='utf-8')
    print('single file: %s (%d KB)' % (out, len(html.encode()) // 1024))
    for r in sorted(set(remote)):
        print('WARNING: still points outside the file, so it will not work offline: %s' % r)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
