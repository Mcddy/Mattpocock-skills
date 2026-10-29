"""Software backend for animkit.canvas: numpy + Pillow only, no network installs needed.

Same API as the Skia backend. Geometry is flattened to polygons in device space,
rasterised with supersampled coverage inside each shape's bounding box, and composited
into a premultiplied float RGBA buffer with real blend modes (src-over, plus, screen,
multiply, overlay, soft-light, colour-dodge, src-atop, dst-in), gradients, mask blur,
bounded layers with alpha/blend/blur, rectangular clips and TrueType text.

Built for offline code sandboxes (e.g. ChatGPT) where skia-python can't be installed.
Expect ~1-4 s per moderately busy 1080p frame; preview at half resolution.
"""
from __future__ import annotations

import functools
import math
import subprocess
from contextlib import contextmanager
from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


# ------------------------------------------------------------------ colour
class Color4f:
    __slots__ = ("fR", "fG", "fB", "fA")

    def __init__(self, r, g, b, a=1.0):
        self.fR, self.fG, self.fB, self.fA = float(r), float(g), float(b), float(a)

    def tup(self):
        return (self.fR, self.fG, self.fB, self.fA)

    def toColor(self):  # parity with skia.Color4f
        return tuple(int(round(v * 255)) for v in self.tup())

    def __repr__(self):
        return f"Color4f({self.fR:.3f}, {self.fG:.3f}, {self.fB:.3f}, {self.fA:.3f})"


def rgba(c, alpha: float = 1.0) -> Color4f:
    if isinstance(c, Color4f):
        return Color4f(c.fR, c.fG, c.fB, c.fA * alpha)
    if hasattr(c, "fR"):          # a skia.Color4f passed across backends
        return Color4f(c.fR, c.fG, c.fB, c.fA * alpha)
    if isinstance(c, str):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return Color4f(r, g, b, a * alpha)
    vals = list(c)
    if any(v > 1.0 for v in vals[:3]):
        vals = [v / 255 for v in vals[:3]] + ([vals[3] / 255] if len(vals) > 3 and vals[3] > 1 else vals[3:])
    if len(vals) == 3:
        vals.append(1.0)
    return Color4f(vals[0], vals[1], vals[2], vals[3] * alpha)


def mix(c1, c2, t: float) -> Color4f:
    a, b = rgba(c1), rgba(c2)
    return Color4f(a.fR + (b.fR - a.fR) * t, a.fG + (b.fG - a.fG) * t,
                   a.fB + (b.fB - a.fB) * t, a.fA + (b.fA - a.fA) * t)


BLEND = {None: "src_over", "normal": "src_over", "plus": "plus", "screen": "screen", "multiply": "multiply",
         "overlay": "overlay", "softlight": "softlight", "color_dodge": "color_dodge", "dst_in": "dst_in", "dst_out": "dst_out",
         "src_atop": "src_atop"}


# ------------------------------------------------------------------ gradients
class _Gradient:
    def __init__(self, kind, geom, colors, stops):
        self.kind = kind
        self.geom = geom
        cols = np.array([rgba(c).tup() for c in colors], np.float32)
        self.cols = cols
        n = len(colors)
        self.stops = np.array(stops if stops is not None else np.linspace(0, 1, n), np.float32)

    def colour_at(self, lx, ly):
        if self.kind == "linear":
            (x0, y0), (x1, y1) = self.geom
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy or 1e-9
            t = ((lx - x0) * dx + (ly - y0) * dy) / L2
        else:
            (cx, cy), r = self.geom
            t = np.sqrt((lx - cx) ** 2 + (ly - cy) ** 2) / max(r, 1e-9)
        t = np.clip(t, 0.0, 1.0)
        out = np.empty(t.shape + (4,), np.float32)
        for k in range(4):
            out[..., k] = np.interp(t, self.stops, self.cols[:, k])
        return out


# ------------------------------------------------------------------ fonts
@functools.lru_cache(maxsize=64)
def _font_file(family="Inter", weight=400, italic=False):
    style = f":weight={int(weight / 4.0)}" if weight else ""
    try:
        q = f"{family}{style}{':slant=100' if italic else ''}"
        p = subprocess.run(["fc-match", "-f", "%{file}", q], capture_output=True, text=True, timeout=5).stdout.strip()
        if p:
            return p
    except (OSError, subprocess.SubprocessError):
        pass
    for cand in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
                 "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            ImageFont.truetype(cand, 12)
            return cand
        except OSError:
            continue
    return None


def typeface(family="Inter", weight=400, italic=False, path: str | None = None):
    return path or _font_file(family, weight, italic)


@functools.lru_cache(maxsize=256)
def _pil_font(path, size):
    if path is None:
        return ImageFont.load_default()
    return ImageFont.truetype(path, max(1, int(round(size))))


# ------------------------------------------------------------------ geometry helpers
def _ellipse_pts(cx, cy, rx, ry, n):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([cx + rx * np.cos(a), cy + ry * np.sin(a)], 1)


def _rrect_pts(x, y, w, h, r, seg=8):
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 0:
        return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], float)
    pts = []
    for (cx, cy, a0) in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90),
                         (x + r, y + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts, float)


def _quad_flatten(p0, c, p1, n=8):
    t = np.linspace(0, 1, n + 1)[1:, None]
    p0, c, p1 = (np.asarray(v, float) for v in (p0, c, p1))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t * t * p1


def _adaptive_n(*ctrl):
    """Segments for a curve: ~1 per 2 units of control-polygon length (paths are usually built in pixels)."""
    est = sum(math.hypot(ctrl[i + 1][0] - ctrl[i][0], ctrl[i + 1][1] - ctrl[i][1]) for i in range(len(ctrl) - 1))
    return int(min(160, max(8, est / 2.0)))


def _cubic_flatten(p0, c1, c2, p1, n=12):
    t = np.linspace(0, 1, n + 1)[1:, None]
    p0, c1, c2, p1 = (np.asarray(v, float) for v in (p0, c1, c2, p1))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * p1


class Path:
    """Minimal path (moveTo/lineTo/quadTo/cubicTo/close) flattened to polygons."""

    def __init__(self):
        self.subpaths = []
        self._cur = None
        self._closed = []

    def moveTo(self, x, y):
        self._cur = [(float(x), float(y))]
        self.subpaths.append(self._cur)
        self._closed.append(False)
        return self

    def lineTo(self, x, y):
        if self._cur is None:
            return self.moveTo(x, y)
        self._cur.append((float(x), float(y)))
        return self

    def quadTo(self, cx, cy, x, y):
        self._cur.extend(map(tuple, _quad_flatten(self._cur[-1], (cx, cy), (x, y),
                                                  _adaptive_n(self._cur[-1], (cx, cy), (x, y)))))
        return self

    def cubicTo(self, c1x, c1y, c2x, c2y, x, y):
        self._cur.extend(map(tuple, _cubic_flatten(self._cur[-1], (c1x, c1y), (c2x, c2y), (x, y),
                                                   _adaptive_n(self._cur[-1], (c1x, c1y), (c2x, c2y), (x, y)))))
        return self

    def close(self):
        if self._closed:
            self._closed[-1] = True
        return self


# ------------------------------------------------------------------ the matrix context (.c)
class _Ctx:
    """Skia-like matrix/clip stack exposed as Canvas.c (used by camera.view and at())."""

    def __init__(self, canvas):
        self.cv = canvas
        self.m = np.eye(3)
        self.clip = (0, 0, canvas.w, canvas.h)
        self.stack = []

    def save(self):
        self.stack.append((self.m.copy(), self.clip, None))

    def restore(self):
        m, clip, layer = self.stack.pop()
        self.m, self.clip = m, clip
        if layer is not None:
            self.cv._pop_layer(layer)

    def translate(self, x, y):
        self.m = self.m @ np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], float)

    def rotate(self, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        self.m = self.m @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)

    def scale(self, sx, sy=None):
        sy = sx if sy is None else sy
        self.m = self.m @ np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], float)

    def clip_rect_device(self, x0, y0, x1, y1):
        cx0, cy0, cx1, cy1 = self.clip
        self.clip = (max(cx0, x0), max(cy0, y0), min(cx1, x1), min(cy1, y1))


# ------------------------------------------------------------------ blend maths (premultiplied)
def _blend(dst, src, mode):
    """dst, src: (...,4) premultiplied float32. Writes into dst."""
    sa = src[..., 3:4]
    da = dst[..., 3:4]
    if mode == "src_over":
        dst *= (1 - sa)
        dst += src
    elif mode == "plus":
        np.minimum(dst + src, 1.0, out=dst)
    elif mode == "dst_in":
        dst *= sa
    elif mode == "dst_out":
        dst *= (1 - sa)
    elif mode == "src_atop":
        rgb = src[..., :3] * da + dst[..., :3] * (1 - sa)
        dst[..., :3] = rgb
    else:
        sc, dc = src[..., :3], dst[..., :3]
        with np.errstate(divide="ignore", invalid="ignore"):
            cs = np.where(sa > 0, sc / np.maximum(sa, 1e-6), 0)
            cb = np.where(da > 0, dc / np.maximum(da, 1e-6), 0)
        if mode == "multiply":
            B = cb * cs
        elif mode == "screen":
            B = cb + cs - cb * cs
        elif mode == "overlay":
            B = np.where(cb <= 0.5, 2 * cb * cs, 1 - 2 * (1 - cb) * (1 - cs))
        elif mode == "softlight":
            D = np.where(cb <= 0.25, ((16 * cb - 12) * cb + 4) * cb, np.sqrt(cb))
            B = np.where(cs <= 0.5, cb - (1 - 2 * cs) * cb * (1 - cb), cb + (2 * cs - 1) * (D - cb))
        elif mode == "color_dodge":
            B = np.where(cb == 0, 0, np.where(cs >= 1, 1, np.minimum(1, cb / np.maximum(1 - cs, 1e-6))))
        else:
            B = cs
        out = (1 - sa) * dc + (1 - da) * sc + sa * da * B
        dst[..., :3] = out
        dst[..., 3:4] = sa + da - sa * da
    return dst


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w: int, h: int, bg=None):
        self.w, self.h = int(w), int(h)
        self.buf = np.zeros((self.h, self.w, 4), np.float32)
        self._target = (self.buf, 0, 0)      # (array, device x offset, device y offset)
        self.c = _Ctx(self)
        if bg is not None:
            self.clear(bg)

    # ---------------------------------------------------------- internals
    def _xf(self, pts):
        pts = np.asarray(pts, float).reshape(-1, 2)
        m = self.c.m
        return pts @ m[:2, :2].T + m[:2, 2]

    def _scale_factor(self):
        m = self.c.m
        return math.sqrt(abs(m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0])) or 1.0

    def _region(self, dev_polys, pad):
        allp = np.concatenate(dev_polys, 0)
        x0, y0 = allp.min(0) - pad
        x1, y1 = allp.max(0) + pad
        arr, ox, oy = self._target
        th, tw = arr.shape[:2]
        cx0, cy0, cx1, cy1 = self.c.clip
        X0 = int(max(math.floor(x0), cx0, ox))
        Y0 = int(max(math.floor(y0), cy0, oy))
        X1 = int(min(math.ceil(x1), cx1, ox + tw))
        Y1 = int(min(math.ceil(y1), cy1, oy + th))
        if X1 <= X0 or Y1 <= Y0:
            return None
        return X0, Y0, X1, Y1

    def _coverage(self, polys_fill, polys_hole, region, blur, rule=None):
        X0, Y0, X1, Y1 = region
        bw, bh = X1 - X0, Y1 - Y0
        area = bw * bh
        s = 4 if area < 300_000 else 2 if area < 2_500_000 else 1
        polys = [P for P in polys_fill if len(P) >= 3]
        if rule and len(polys) > 1:
            # winding-number fill: per-subpath masks signed by orientation (nonzero / evenodd)
            wind = np.zeros((bh * s, bw * s), np.int16)
            for P in polys:
                m = Image.new("L", (bw * s, bh * s), 0)
                ImageDraw.Draw(m).polygon([((x - X0) * s, (y - Y0) * s) for x, y in P], fill=1)
                mm = np.asarray(m, np.int16)
                if rule == "evenodd":
                    wind += mm
                else:
                    P = np.asarray(P, float)
                    a2 = float(np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))
                    wind += mm * (1 if a2 >= 0 else -1)
            on = (wind % 2 == 1) if rule == "evenodd" else (wind != 0)
            im = Image.fromarray((on * 255).astype(np.uint8), "L")
        else:
            im = Image.new("L", (bw * s, bh * s), 0)
            dr = ImageDraw.Draw(im)
            for P in polys:
                dr.polygon([((x - X0) * s, (y - Y0) * s) for x, y in P], fill=255)
        dr = ImageDraw.Draw(im)
        for P in polys_hole:
            if len(P) >= 3:
                dr.polygon([((x - X0) * s, (y - Y0) * s) for x, y in P], fill=0)
        if s > 1:
            im = im.reduce(s)
        if blur > 0:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return np.asarray(im, np.float32) / 255.0

    def _source(self, fill, alpha, region):
        X0, Y0, X1, Y1 = region
        if isinstance(fill, _Gradient):
            ys, xs = np.mgrid[Y0:Y1, X0:X1].astype(np.float32) + 0.5
            inv = np.linalg.inv(self.c.m)
            lx = inv[0, 0] * xs + inv[0, 1] * ys + inv[0, 2]
            ly = inv[1, 0] * xs + inv[1, 1] * ys + inv[1, 2]
            col = fill.colour_at(lx, ly)
            col[..., 3] *= alpha
            col[..., :3] *= col[..., 3:4]
            return col
        c = rgba(fill, alpha)
        return np.array([c.fR * c.fA, c.fG * c.fA, c.fB * c.fA, c.fA], np.float32)

    def _composite(self, cov, src, region, blend):
        X0, Y0, X1, Y1 = region
        arr, ox, oy = self._target
        dst = arr[Y0 - oy:Y1 - oy, X0 - ox:X1 - ox]
        if src.ndim == 1:
            s = cov[..., None] * src[None, None, :]
        else:
            s = src * cov[..., None]
        _blend(dst, s.astype(np.float32), BLEND.get(blend, blend) or "src_over")

    def _fill_polys(self, local_polys, fill, alpha=1.0, blend=None, blur=0.0, holes=(), rule=None):
        if fill is None:
            return
        dev = [self._xf(P) for P in local_polys if len(P) >= 3]
        dev_h = [self._xf(P) for P in holes if len(P) >= 3]
        if not dev:
            return
        blur = blur * self._scale_factor()          # Skia mask blur respects the CTM
        pad = 3 * blur + 1
        reg = self._region(dev, pad)
        if reg is None:
            return
        cov = self._coverage(dev, dev_h, reg, blur, rule)
        src = self._source(fill, alpha, reg)
        self._composite(cov, src, reg, blend)

    def _stroke_polys(self, segs, width, cap="round"):
        """Polygons (local coords) covering a stroked polyline."""
        polys = []
        r = width / 2
        for p0, p1 in segs:
            p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
            d = p1 - p0
            L = np.hypot(*d)
            if L < 1e-9:
                continue
            n = np.array([-d[1], d[0]]) / L * r
            e = d / L * (r if cap == "square" else 0)
            polys.append(np.array([p0 + n - e, p1 + n + e, p1 - n + e, p0 - n - e]))
        if cap == "round":
            n = max(8, min(32, int(width * 1.5)))
            pts = [segs[0][0]] + [b for _, b in segs]
            for p in pts:
                polys.append(_ellipse_pts(p[0], p[1], r, r, n))
        return polys

    def _paint_shape(self, polys_local, fill=None, *, stroke=None, sw=1.0, alpha=1.0, blend=None, blur=0.0,
                     cap="round", join="round", closed=True, holes=(), rule=None):
        if stroke is not None and fill is not None:     # both: fill first, then the stroke on top
            self._fill_polys(polys_local, fill, alpha, blend, blur, holes, rule)
        if stroke is not None:
            segs = []
            for P in polys_local:
                P = np.asarray(P, float)
                k = len(P)
                rng = range(k) if closed else range(k - 1)
                segs.extend((P[i], P[(i + 1) % k]) for i in rng)
            if segs:
                self._fill_polys(self._stroke_polys(segs, sw, cap if not closed else "round"), stroke, alpha, blend, blur)
        else:
            self._fill_polys(polys_local, fill, alpha, blend, blur, holes, rule)

    def _n_for(self, rx, ry):
        sc = self._scale_factor()
        per = 2 * math.pi * max(rx, ry) * sc
        return int(min(256, max(20, per / 3)))

    # ---------------------------------------------------------- public API
    def clear(self, color):
        c = rgba(color)
        arr, _, _ = self._target
        arr[...] = (c.fR * c.fA, c.fG * c.fA, c.fB * c.fA, c.fA)

    def rect(self, x, y, w, h, fill=None, r=0.0, **kw):
        self._paint_shape([_rrect_pts(x, y, w, h, r)], fill, **kw)

    def circle(self, x, y, r, fill=None, **kw):
        self.ellipse(x, y, r, r, fill, **kw)

    def ellipse(self, cx, cy, rx, ry, fill=None, **kw):
        n = self._n_for(rx, ry)
        if kw.get("stroke") is not None:
            if fill is not None:
                self._fill_polys([_ellipse_pts(cx, cy, rx, ry, n)], fill, kw.get("alpha", 1.0), kw.get("blend"),
                                 kw.get("blur", 0.0))
            sw = kw.pop("sw", 1.0)
            stroke = kw.pop("stroke")
            outer = _ellipse_pts(cx, cy, rx + sw / 2, ry + sw / 2, n)
            inner = _ellipse_pts(cx, cy, max(0.0, rx - sw / 2), max(0.0, ry - sw / 2), n)
            self._fill_polys([outer], stroke, kw.get("alpha", 1.0), kw.get("blend"), kw.get("blur", 0.0), holes=[inner])
            return
        self._paint_shape([_ellipse_pts(cx, cy, rx, ry, n)], fill, **kw)

    def poly(self, pts: Sequence, fill=None, closed=True, **kw):
        self._paint_shape([np.asarray(pts, float)], fill, closed=closed, **kw)

    def path(self, path, fill=None, rule=None, **kw):
        """Draw a path from new_path(). rule: None/'nonzero' or 'evenodd' (holes in letters, logos)."""
        polys = [np.array(sp, float) for sp in path.subpaths if len(sp) >= 2]
        closed = all(path._closed) if path._closed else True
        if fill is not None and kw.get("stroke") is None and len(polys) > 1:
            rule = rule or getattr(path, "rule", None) or "nonzero"
        self._paint_shape(polys, fill, closed=closed, rule=rule, **kw)

    def image(self, img, x=0.0, y=0.0, w=None, h=None, alpha=1.0, blend=None):
        """Draw an RGBA/RGB image (numpy uint8, PIL image or path) into rect (x, y, w, h) through the transform."""
        pim = _premul_image(img)
        iw, ih = pim.size
        w, h = float(w or iw), float(h or ih)
        corners = self._xf([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        reg = self._region([corners], 1)
        if reg is None:
            return
        X0, Y0, X1, Y1 = reg
        # device pixel -> image pixel: inv(CTM) then local -> image scale
        inv = np.linalg.inv(self.c.m)
        sx, sy = iw / w, ih / h
        a, b, c0 = inv[0, 0] * sx, inv[0, 1] * sx, (inv[0, 2] - x) * sx
        d, e, f0 = inv[1, 0] * sy, inv[1, 1] * sy, (inv[1, 2] - y) * sy
        # output pixel (i, j) is device (X0 + i, Y0 + j); PIL uses pixel centres on both sides
        cx = a * X0 + b * Y0 + c0
        cy = d * X0 + e * Y0 + f0
        out = pim.transform((X1 - X0, Y1 - Y0), Image.AFFINE, (a, b, cx, d, e, cy), resample=Image.BILINEAR)
        src = np.asarray(out, np.float32) / 255.0
        if alpha != 1.0:
            src = src * alpha
        self._composite(np.ones(src.shape[:2], np.float32), src, reg, blend)

    def line(self, p0, p1, color, width=2.0, **kw):
        cap = kw.pop("cap", "round")
        alpha = kw.pop("alpha", 1.0)
        blend = kw.pop("blend", None)
        blur = kw.pop("blur", 0.0)
        self._fill_polys(self._stroke_polys([(p0, p1)], width, cap), color, alpha, blend, blur)

    def polyline(self, pts, color, width=2.0, smooth=True, **kw):
        pts = [tuple(map(float, q)) for q in pts]
        if smooth and len(pts) > 2:
            flat = [pts[0]]
            for i in range(1, len(pts) - 1):
                mx = (pts[i][0] + pts[i + 1][0]) / 2
                my = (pts[i][1] + pts[i + 1][1]) / 2
                flat.extend(map(tuple, _quad_flatten(flat[-1], pts[i], (mx, my), 6)))
            flat.append(pts[-1])
            pts = flat
        segs = list(zip(pts[:-1], pts[1:]))
        cap = kw.pop("cap", "round")
        self._fill_polys(self._stroke_polys(segs, width, cap), color, kw.get("alpha", 1.0), kw.get("blend"),
                         kw.get("blur", 0.0))

    def blob(self, cx, cy, rx, ry, squash=(1.0, 1.0), wobble=0.0, seed=0, n=48, fill=None, **kw):
        rng = np.random.default_rng(seed)
        ph = rng.uniform(0, 2 * math.pi, 3)
        a = np.linspace(0, 2 * math.pi, max(n, self._n_for(rx, ry)), endpoint=False)
        k = 1 + wobble * (0.5 * np.sin(3 * a + ph[0]) + 0.3 * np.sin(5 * a + ph[1]))
        pts = np.stack([cx + rx * squash[0] * k * np.cos(a), cy + ry * squash[1] * k * np.sin(a)], 1)
        self._paint_shape([pts], fill, **kw)

    def linear(self, p0, p1, colors, stops=None):
        return _Gradient("linear", (tuple(p0), tuple(p1)), colors, stops)

    def radial(self, center, radius, colors, stops=None):
        return _Gradient("radial", (tuple(center), float(radius)), colors, stops)

    def light(self, x, y, radius, color, intensity=1.0, blend="plus", falloff=2.0):
        col = rgba(color)
        stops = [0.0, 0.15, 0.35, 0.6, 1.0]
        cols = []
        for s in stops:
            a = intensity / (1 + (s * 4) ** falloff) * (1 - s) ** 1.5
            cols.append((col.fR, col.fG, col.fB, max(0.0, min(1.0, a))))
        g = _Gradient("radial", ((x, y), float(radius)), cols, stops)
        self._fill_polys([_rrect_pts(x - radius, y - radius, 2 * radius, 2 * radius, 0)], g, 1.0, blend)

    def cone(self, apex, base_l, base_r, color, intensity=0.6, blend="plus", soften=18.0):
        ax, ay = apex
        mx = (base_l[0] + base_r[0]) / 2
        my = (base_l[1] + base_r[1]) / 2
        col = rgba(color)
        g = _Gradient("linear", ((ax, ay), (mx, my)),
                      [(col.fR, col.fG, col.fB, min(1, intensity)), (col.fR, col.fG, col.fB, min(1, intensity * 0.35)),
                       (col.fR, col.fG, col.fB, 0.0)], [0.0, 0.55, 1.0])
        self._fill_polys([np.array([apex, base_l, base_r], float)], g, 1.0, blend, soften)

    def shadow(self, cx, cy, rx, ry, alpha=0.35, blur=6.0, color="#000000"):
        self.ellipse(cx, cy, rx, ry, color, alpha=alpha, blend="multiply", blur=blur)

    def text(self, s, x, y, size=48, family="Inter", weight=600, color="#111111", align="left",
             tracking=0.0, alpha=1.0, path=None):
        sc = self._scale_factor()
        font = _pil_font(typeface(family, weight, path=path), size * sc)
        widths = [font.getlength(ch) / sc + tracking for ch in s] if tracking else None
        total = (sum(widths) - tracking) if tracking else font.getlength(s) / sc
        ox = x - (total / 2 if align == "center" else total if align == "right" else 0)
        dx, dy = self._xf([(ox, y)])[0]
        asc, desc = font.getmetrics()
        W = int(total * sc + size * sc) + 4
        H = int(asc + desc) + 4
        im = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(im)
        if tracking:
            cur = 0.0
            for ch, wd in zip(s, widths):
                dr.text((2 + cur * sc, 2 + asc), ch, fill=255, font=font, anchor="ls")
                cur += wd
        else:
            dr.text((2, 2 + asc), s, fill=255, font=font, anchor="ls")
        X0, Y0 = int(math.floor(dx)) - 2, int(math.floor(dy)) - asc - 2
        reg = (X0, Y0, X0 + W, Y0 + H)
        arr, ox_, oy_ = self._target
        cx0, cy0, cx1, cy1 = self.c.clip
        R = (max(X0, cx0, ox_), max(Y0, cy0, oy_), min(X0 + W, cx1, ox_ + arr.shape[1]), min(Y0 + H, cy1, oy_ + arr.shape[0]))
        if R[2] > R[0] and R[3] > R[1]:
            cov = np.asarray(im, np.float32)[R[1] - Y0:R[3] - Y0, R[0] - X0:R[2] - X0] / 255.0
            self._composite(cov, self._source(color, alpha, R), R, None)
        return total

    # ---------------------------------------------------------- transforms & layers
    @contextmanager
    def at(self, x=0.0, y=0.0, rot=0.0, sx=1.0, sy=1.0, pivot=(0.0, 0.0)):
        self.c.save()
        self.c.translate(float(x), float(y))
        if rot:
            self.c.rotate(math.degrees(rot))
        if sx != 1 or sy != 1:
            self.c.scale(float(sx), float(sy))
        if pivot != (0.0, 0.0):
            self.c.translate(-float(pivot[0]), -float(pivot[1]))
        try:
            yield self
        finally:
            self.c.restore()

    @contextmanager
    def layer(self, alpha=1.0, blend=None, blur=0.0, bounds=None):
        """Isolated group (alpha / blend / blur). Pass `bounds` for speed, as with Skia."""
        if bounds:
            x, y, w, h = bounds
            dev = self._xf([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
            pad = 3 * blur * self._scale_factor() + 1
            X0, Y0 = np.floor(dev.min(0) - pad).astype(int)
            X1, Y1 = np.ceil(dev.max(0) + pad).astype(int)
        else:
            X0, Y0, X1, Y1 = 0, 0, self.w, self.h
        cx0, cy0, cx1, cy1 = self.c.clip
        X0, Y0 = max(int(X0), int(cx0), 0), max(int(Y0), int(cy0), 0)
        X1, Y1 = min(int(X1), int(cx1), self.w), min(int(Y1), int(cy1), self.h)
        empty = X1 <= X0 or Y1 <= Y0
        if empty:
            X1, Y1 = X0 + 1, Y0 + 1
        buf = np.zeros((Y1 - Y0, X1 - X0, 4), np.float32)
        layer = {"prev": self._target, "buf": buf, "ox": X0, "oy": Y0, "alpha": alpha, "blend": blend,
                 "blur": blur * self._scale_factor(), "empty": empty}
        self.c.stack.append((self.c.m.copy(), self.c.clip, layer))
        self._target = (buf, X0, Y0)
        try:
            yield self
        finally:
            m, clip, lay = self.c.stack.pop()
            self.c.m, self.c.clip = m, clip
            self._pop_layer(lay)

    def _pop_layer(self, lay):
        self._target = lay["prev"]
        if lay["empty"]:
            return
        buf = lay["buf"]
        if lay["blur"] > 0:
            chans = []
            for k in range(4):
                im = Image.fromarray(np.clip(buf[..., k] * 255.0, 0, 255).astype(np.uint8))
                chans.append(np.asarray(im.filter(ImageFilter.GaussianBlur(lay["blur"])), np.float32) / 255.0)
            buf = np.stack(chans, -1)
        if lay["alpha"] != 1.0:
            buf = buf * lay["alpha"]
        arr, ox, oy = self._target
        X0, Y0 = lay["ox"], lay["oy"]
        h, w = buf.shape[:2]
        x0, y0 = max(X0, ox), max(Y0, oy)
        x1, y1 = min(X0 + w, ox + arr.shape[1]), min(Y0 + h, oy + arr.shape[0])
        if x1 <= x0 or y1 <= y0:
            return
        dst = arr[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        src = buf[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
        _blend(dst, np.ascontiguousarray(src), BLEND.get(lay["blend"], lay["blend"]) or "src_over")

    @contextmanager
    def clip_rect(self, x, y, w, h):
        self.c.save()
        dev = self._xf([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        self.c.clip_rect_device(dev[:, 0].min(), dev[:, 1].min(), dev[:, 0].max(), dev[:, 1].max())
        try:
            yield self
        finally:
            self.c.restore()

    # ---------------------------------------------------------- output
    def array(self) -> np.ndarray:
        return np.clip(self.buf[..., :3] * 255.0 + 0.5, 0, 255).astype(np.uint8)

    def rgba_array(self) -> np.ndarray:
        """Straight-alpha RGBA uint8 (for transparent deliverables)."""
        a = self.buf[..., 3:4]
        rgb = np.where(a > 1e-6, self.buf[..., :3] / np.maximum(a, 1e-6), 0.0)
        out = np.concatenate([rgb, a], -1)
        return np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)

    def save_png(self, path: str):
        Image.fromarray(self.array()).save(path)


_PIMG: dict = {}


def _premul_image(img):
    """numpy / PIL / path -> premultiplied PIL 'RGBa' image (cached by identity)."""
    key = img if isinstance(img, str) else id(img)
    hit = _PIMG.get(key)
    if hit is not None:
        return hit
    if isinstance(img, str):
        pil = Image.open(img).convert("RGBA")
    elif isinstance(img, np.ndarray):
        a = img
        if a.dtype != np.uint8:
            a = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
        if a.ndim == 2:
            a = np.stack([a, a, a], -1)
        pil = Image.fromarray(a, "RGBA" if a.shape[2] == 4 else "RGB").convert("RGBA")
    else:
        pil = img.convert("RGBA")
    out = pil.convert("RGBa")
    if len(_PIMG) > 64:
        _PIMG.clear()
    _PIMG[key] = out
    return out


def new_path() -> "Path":
    """Backend-neutral path builder: moveTo/lineTo/quadTo/cubicTo/close, then cv.path(p, fill, rule=...)."""
    return Path()
