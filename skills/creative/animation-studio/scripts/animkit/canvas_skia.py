"""Skia backend for animkit.canvas (preferred when skia-python is installed).

Anti-aliased 2-D drawing on Skia with film-style lighting helpers.

Why Skia: real anti-aliasing, gradients, blend modes (additive light, multiply
shade), blur filters (glow, soft shadows) and proper font rendering. PIL lacks
most of these, which is why sandbox animation so often looks flat and cheap.

Colours: '#rrggbb', '#rrggbbaa', (r, g, b) or (r, g, b, a) with 0-255 ints or
0-1 floats, or a skia.Shader for gradients.
"""
from __future__ import annotations

import math
from contextlib import contextmanager
from typing import Sequence

import numpy as np
import skia

BLEND = {
    None: skia.BlendMode.kSrcOver,
    "normal": skia.BlendMode.kSrcOver,
    "plus": skia.BlendMode.kPlus,          # additive light
    "screen": skia.BlendMode.kScreen,      # soft light add
    "multiply": skia.BlendMode.kMultiply,  # shadows, night grade
    "overlay": skia.BlendMode.kOverlay,
    "softlight": skia.BlendMode.kSoftLight,
    "color_dodge": skia.BlendMode.kColorDodge,
    "dst_in": skia.BlendMode.kDstIn,        # affects only pixels under the drawn shape: for masks use vector.mask_to
    "dst_out": skia.BlendMode.kDstOut,      # erase: bites, holes, wipe reveals (use inside a layer)
    "src_atop": skia.BlendMode.kSrcATop,    # paint only where already drawn (rim light!)
}


def rgba(c, alpha: float = 1.0) -> skia.Color4f:
    if isinstance(c, skia.Color4f):
        return skia.Color4f(c.fR, c.fG, c.fB, c.fA * alpha)
    if isinstance(c, str):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return skia.Color4f(r, g, b, a * alpha)
    vals = list(c)
    if any(v > 1.0 for v in vals[:3]):
        vals = [v / 255 for v in vals[:3]] + ([vals[3] / 255] if len(vals) > 3 and vals[3] > 1 else vals[3:])
    if len(vals) == 3:
        vals.append(1.0)
    return skia.Color4f(vals[0], vals[1], vals[2], vals[3] * alpha)


def mix(c1, c2, t: float):
    a, b = rgba(c1), rgba(c2)
    return skia.Color4f(a.fR + (b.fR - a.fR) * t, a.fG + (b.fG - a.fG) * t,
                        a.fB + (b.fB - a.fB) * t, a.fA + (b.fA - a.fA) * t)


def _argb(c) -> int:
    return rgba(c).toColor()


_TYPEFACES: dict = {}


def typeface(family="Inter", weight=400, italic=False, path: str | None = None):
    key = (family, weight, italic, path)
    if key not in _TYPEFACES:
        if path:
            _TYPEFACES[key] = skia.Typeface.MakeFromFile(path)
        else:
            slant = skia.FontStyle.kItalic_Slant if italic else skia.FontStyle.kUpright_Slant
            _TYPEFACES[key] = skia.Typeface(family, skia.FontStyle(weight, skia.FontStyle.kNormal_Width, slant))
    return _TYPEFACES[key]


class Canvas:
    def __init__(self, w: int, h: int, bg=None):
        self.w, self.h = int(w), int(h)
        self.surface = skia.Surface(self.w, self.h)
        self.c = self.surface.getCanvas()
        if bg is not None:
            self.clear(bg)

    # ------------------------------------------------------------ paint
    def _paint(self, fill=None, *, stroke=None, sw=1.0, alpha=1.0, blend=None, blur=0.0,
               cap="round", join="round"):
        p = skia.Paint(AntiAlias=True)
        if isinstance(fill, skia.Shader):
            p.setShader(fill)
            p.setAlphaf(alpha)
        elif fill is not None:
            p.setColor4f(rgba(fill, alpha))
        if stroke is not None:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(sw)
            if isinstance(stroke, skia.Shader):
                p.setShader(stroke)
                p.setAlphaf(alpha)
            else:
                p.setColor4f(rgba(stroke, alpha))
            p.setStrokeCap({"round": skia.Paint.kRound_Cap, "butt": skia.Paint.kButt_Cap,
                            "square": skia.Paint.kSquare_Cap}[cap])
            p.setStrokeJoin({"round": skia.Paint.kRound_Join, "miter": skia.Paint.kMiter_Join,
                             "bevel": skia.Paint.kBevel_Join}[join])
        p.setBlendMode(BLEND[blend])
        if blur > 0:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        return p

    def _paints(self, fill=None, **kw):
        """Paints for one shape: fill, then stroke. Passing both fill= and stroke= draws both (a single
        Skia paint would keep only the stroke and silently drop the fill)."""
        if fill is not None and kw.get("stroke") is not None:
            fkw = {k: v for k, v in kw.items() if k not in ("stroke", "sw", "cap", "join")}
            return [self._paint(fill, **fkw), self._paint(None, **kw)]
        return [self._paint(fill, **kw)]

    def clear(self, color):
        self.c.clear(rgba(color))

    # ------------------------------------------------------------ shapes
    def rect(self, x, y, w, h, fill=None, r=0.0, **kw):
        rect = skia.Rect.MakeXYWH(x, y, w, h)
        for p in self._paints(fill, **kw):
            if r:
                self.c.drawRRect(skia.RRect.MakeRectXY(rect, r, r), p)
            else:
                self.c.drawRect(rect, p)

    def circle(self, x, y, r, fill=None, **kw):
        for p in self._paints(fill, **kw):
            self.c.drawCircle(x, y, r, p)

    def ellipse(self, cx, cy, rx, ry, fill=None, **kw):
        for p in self._paints(fill, **kw):
            self.c.drawOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry), p)

    def poly(self, pts: Sequence, fill=None, closed=True, **kw):
        path = skia.Path()
        path.moveTo(*map(float, pts[0]))
        for q in pts[1:]:
            path.lineTo(*map(float, q))
        if closed:
            path.close()
        for p in self._paints(fill, **kw):
            self.c.drawPath(path, p)

    def path(self, path: skia.Path, fill=None, rule=None, **kw):
        """Draw a path from new_path(). rule: None (keep), 'nonzero' or 'evenodd' (holes in letters, logos)."""
        if rule:
            path.setFillType(skia.PathFillType.kEvenOdd if rule == "evenodd" else skia.PathFillType.kWinding)
        for p in self._paints(fill, **kw):
            self.c.drawPath(path, p)

    def image(self, img, x=0.0, y=0.0, w=None, h=None, alpha=1.0, blend=None):
        """Draw an RGBA/RGB image (numpy uint8 HxWx3/4, PIL image or file path) into rect (x, y, w, h)."""
        arr = _rgba_u8(img)
        key = (id(img), arr.shape) if not isinstance(img, str) else (img, arr.shape)
        sk = _IMAGES.get(key)
        if sk is None:
            sk = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType,
                                      alphaType=skia.kUnpremul_AlphaType)
            if len(_IMAGES) > 64:
                _IMAGES.clear()
            _IMAGES[key] = sk
        ih, iw = arr.shape[:2]
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(alpha)
        p.setBlendMode(BLEND[blend])
        self.c.drawImageRect(sk, skia.Rect.MakeXYWH(x, y, w or iw, h or ih),
                             skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)

    def line(self, p0, p1, color, width=2.0, **kw):
        self.c.drawLine(float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1]),
                        self._paint(None, stroke=color, sw=width, **kw))

    def polyline(self, pts, color, width=2.0, smooth=True, **kw):
        path = skia.Path()
        pts = [tuple(map(float, q)) for q in pts]
        path.moveTo(*pts[0])
        if smooth and len(pts) > 2:
            for i in range(1, len(pts) - 1):
                mx = (pts[i][0] + pts[i + 1][0]) / 2
                my = (pts[i][1] + pts[i + 1][1]) / 2
                path.quadTo(pts[i][0], pts[i][1], mx, my)
            path.lineTo(*pts[-1])
        else:
            for q in pts[1:]:
                path.lineTo(*q)
        self.c.drawPath(path, self._paint(None, stroke=color, sw=width, **kw))

    def blob(self, cx, cy, rx, ry, squash=(1.0, 1.0), wobble=0.0, seed=0, n=48, fill=None, **kw):
        """Soft organic ellipse; wobble adds subtle irregularity (alive, not CAD)."""
        rng = np.random.default_rng(seed)
        ph = rng.uniform(0, 2 * math.pi, 3)
        path = skia.Path()
        for i in range(n + 1):
            a = 2 * math.pi * i / n
            k = 1 + wobble * (0.5 * math.sin(3 * a + ph[0]) + 0.3 * math.sin(5 * a + ph[1]))
            x = cx + rx * squash[0] * k * math.cos(a)
            y = cy + ry * squash[1] * k * math.sin(a)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.close()
        self.c.drawPath(path, self._paint(fill, **kw))

    # ------------------------------------------------------------ gradients
    def linear(self, p0, p1, colors, stops=None) -> skia.Shader:
        return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)],
                                              [_argb(c) for c in colors], stops)

    def radial(self, center, radius, colors, stops=None) -> skia.Shader:
        return skia.GradientShader.MakeRadial(skia.Point(*center), float(radius),
                                              [_argb(c) for c in colors], stops)

    # ------------------------------------------------------------ light
    def light(self, x, y, radius, color, intensity=1.0, blend="plus", falloff=2.0):
        """Additive point light with smooth (approximately inverse-square) falloff."""
        col = rgba(color)
        stops = [0.0, 0.15, 0.35, 0.6, 1.0]
        cols = []
        for s in stops:
            a = intensity / (1 + (s * 4) ** falloff) * (1 - s) ** 1.5
            cols.append(skia.Color4f(col.fR, col.fG, col.fB, max(0.0, min(1.0, a))).toColor())
        sh = skia.GradientShader.MakeRadial(skia.Point(x, y), float(radius), cols, stops)
        p = skia.Paint(AntiAlias=True, Shader=sh)
        p.setBlendMode(BLEND[blend])
        self.c.drawRect(skia.Rect.MakeXYWH(x - radius, y - radius, 2 * radius, 2 * radius), p)

    def cone(self, apex, base_l, base_r, color, intensity=0.6, blend="plus", soften=18.0):
        """Volumetric light cone (window spill, lamp beam) fading away from the source."""
        ax, ay = apex
        mx = (base_l[0] + base_r[0]) / 2
        my = (base_l[1] + base_r[1]) / 2
        col = rgba(color)
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(ax, ay), skia.Point(mx, my)],
            [skia.Color4f(col.fR, col.fG, col.fB, min(1, intensity)).toColor(),
             skia.Color4f(col.fR, col.fG, col.fB, min(1, intensity * 0.35)).toColor(),
             skia.Color4f(col.fR, col.fG, col.fB, 0.0).toColor()],
            [0.0, 0.55, 1.0])
        path = skia.Path()
        path.moveTo(ax, ay)
        path.lineTo(*base_l)
        path.lineTo(*base_r)
        path.close()
        p = skia.Paint(AntiAlias=True, Shader=sh)
        p.setBlendMode(BLEND[blend])
        if soften:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, soften))
        self.c.drawPath(path, p)

    def shadow(self, cx, cy, rx, ry, alpha=0.35, blur=6.0, color="#000000"):
        """Contact shadow (multiply). Shrink + fade it as the object lifts."""
        self.ellipse(cx, cy, rx, ry, color, alpha=alpha, blend="multiply", blur=blur)

    # ------------------------------------------------------------ text
    def text(self, s, x, y, size=48, family="Inter", weight=600, color="#111111", align="left",
             tracking=0.0, alpha=1.0, path=None):
        font = skia.Font(typeface(family, weight, path=path), size)
        p = self._paint(color, alpha=alpha)
        if tracking:
            cur = x
            widths = [font.measureText(ch) + tracking for ch in s]
            total = sum(widths) - tracking
            cur = x - (total / 2 if align == "center" else total if align == "right" else 0)
            for ch, wdt in zip(s, widths):
                self.c.drawString(ch, cur, y, font, p)
                cur += wdt
            return total
        wdt = font.measureText(s)
        ox = x - (wdt / 2 if align == "center" else wdt if align == "right" else 0)
        self.c.drawString(s, ox, y, font, p)
        return wdt

    # ------------------------------------------------------------ transforms & layers
    @contextmanager
    def at(self, x=0.0, y=0.0, rot=0.0, sx=1.0, sy=1.0, pivot=(0.0, 0.0)):
        """Transform block. rot in radians. pivot is in local (pre-transform) coords."""
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
        """Isolated group: composite with alpha / blend mode / blur as one unit.

        Always pass `bounds` (x, y, w, h in current coords) for blurred layers:
        an unbounded blurred layer is a full-frame blur and costs ~50x more.
        """
        p = skia.Paint()
        p.setAlphaf(alpha)
        p.setBlendMode(BLEND[blend])
        if blur > 0:
            p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        rect = skia.Rect.MakeXYWH(*bounds) if bounds else None
        self.c.saveLayer(rect, p)
        try:
            yield self
        finally:
            self.c.restore()

    @contextmanager
    def clip_rect(self, x, y, w, h):
        self.c.save()
        self.c.clipRect(skia.Rect.MakeXYWH(x, y, w, h), skia.ClipOp.kIntersect, True)
        try:
            yield self
        finally:
            self.c.restore()

    # ------------------------------------------------------------ output
    def array(self) -> np.ndarray:
        a = self.surface.makeImageSnapshot().toarray()
        return np.ascontiguousarray(a[..., [2, 1, 0]])  # BGRA -> RGB

    def rgba_array(self) -> np.ndarray:
        """Straight-alpha RGBA uint8 (for transparent deliverables: WebM/ProRes 4444/APNG/PNG)."""
        a = self.surface.makeImageSnapshot().toarray(colorType=skia.kBGRA_8888_ColorType,
                                                    alphaType=skia.kUnpremul_AlphaType)
        return np.ascontiguousarray(a[..., [2, 1, 0, 3]])

    def save_png(self, path: str):
        self.surface.makeImageSnapshot().save(path, skia.kPNG)


_IMAGES: dict = {}


def _rgba_u8(img) -> np.ndarray:
    """numpy (HxWx3/4 uint8 or float 0-1), PIL image or path -> straight-alpha RGBA uint8."""
    if isinstance(img, str):
        from PIL import Image
        img = Image.open(img)
    if not isinstance(img, np.ndarray):
        img = np.asarray(img.convert("RGBA"))
    a = np.asarray(img)
    if a.dtype != np.uint8:
        a = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a, a, a, np.full_like(a, 255)], -1)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, np.uint8)], -1)
    return a


def new_path() -> skia.Path:
    """Backend-neutral path builder: moveTo/lineTo/quadTo/cubicTo/close, then cv.path(p, fill, rule=...)."""
    return skia.Path()
