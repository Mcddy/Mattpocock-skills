"""Backend-neutral vector paths: build, transform, measure, trim (draw-on) and draw.

VPath keeps real curves (lines, quadratics, cubics), so it can be transformed, measured
by arc length, trimmed for stroke draw-on reveals, exported to Lottie/CSS, and drawn on
either canvas backend.

    vp = VPath().moveTo(0, 0).cubicTo(40, -60, 120, -60, 160, 0).close()
    draw_fill(cv, vp, "#E8A33D", rule="nonzero")
    draw_stroke(cv, vp, "#1B2A3A", 6, t0=0.0, t1=reveal(f))      # draw-on
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def _q(p0, c, p1, t):
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t * t * p1


def _c(p0, c1, c2, p1, t):
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * p1


class VPath:
    """Subpaths of segments: ('L', p) | ('Q', c, p) | ('C', c1, c2, p); each subpath has a start and closed flag."""

    def __init__(self):
        self.subs: list[dict] = []

    # -- building (same verbs as canvas paths)
    def moveTo(self, x, y):
        self.subs.append({"start": np.array([float(x), float(y)]), "segs": [], "closed": False})
        return self

    def _need(self):
        if not self.subs:
            self.moveTo(0, 0)
        return self.subs[-1]

    def _cur(self):
        s = self._need()
        return s["segs"][-1][-1] if s["segs"] else s["start"]

    def lineTo(self, x, y):
        self._need()["segs"].append(("L", np.array([float(x), float(y)])))
        return self

    def quadTo(self, cx, cy, x, y):
        self._need()["segs"].append(("Q", np.array([float(cx), float(cy)]), np.array([float(x), float(y)])))
        return self

    def cubicTo(self, c1x, c1y, c2x, c2y, x, y):
        self._need()["segs"].append(("C", np.array([float(c1x), float(c1y)]), np.array([float(c2x), float(c2y)]),
                                     np.array([float(x), float(y)])))
        return self

    def close(self):
        if self.subs:
            s = self.subs[-1]
            if s["segs"] and np.linalg.norm(s["segs"][-1][-1] - s["start"]) > 1e-9:
                s["segs"].append(("L", s["start"].copy()))
            s["closed"] = True
        return self

    # -- geometry
    def transform(self, m) -> "VPath":
        m = np.asarray(m, float)
        A, t = m[:2, :2], m[:2, 2]
        out = VPath()
        for s in self.subs:
            out.subs.append({"start": A @ s["start"] + t, "closed": s["closed"],
                             "segs": [(sg[0],) + tuple(A @ p + t for p in sg[1:]) for sg in s["segs"]]})
        return out

    def flatten(self, step=2.0) -> list:
        """[(Nx2 array, closed)] with curves sampled about every `step` units."""
        out = []
        for s in self.subs:
            pts = [s["start"]]
            cur = s["start"]
            for sg in s["segs"]:
                kind, *ps = sg
                if kind == "L":
                    pts.append(ps[0])
                else:
                    ctrl = [cur] + ps
                    est = sum(np.linalg.norm(ctrl[i + 1] - ctrl[i]) for i in range(len(ctrl) - 1))
                    n = int(min(96, max(4, est / step)))
                    ts = np.linspace(0, 1, n + 1)[1:, None]
                    pts.extend(_q(cur, ps[0], ps[1], ts) if kind == "Q" else _c(cur, ps[0], ps[1], ps[2], ts))
                cur = ps[-1]
            out.append((np.array(pts, float), s["closed"]))
        return out

    def bounds(self):
        allp = np.concatenate([p for p, _ in self.flatten(4.0)] or [np.zeros((1, 2))])
        (x0, y0), (x1, y1) = allp.min(0), allp.max(0)
        return float(x0), float(y0), float(x1 - x0), float(y1 - y0)

    def centre(self):
        x, y, w, h = self.bounds()
        return x + w / 2, y + h / 2

    def length(self, step=1.0) -> float:
        return float(sum(np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for p, _ in self.flatten(step)))

    def trim(self, t0=0.0, t1=1.0, step=1.0) -> list:
        """Open polylines covering [t0, t1] of the total arc length (subpaths in order): stroke draw-on."""
        t0, t1 = max(0.0, min(1.0, t0)), max(0.0, min(1.0, t1))
        if t1 <= t0:
            return []
        polys = [p for p, _ in self.flatten(step)]
        lens = [np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))] for p in polys]
        total = sum(L[-1] for L in lens) or 1.0
        a, b = t0 * total, t1 * total
        out, off = [], 0.0
        for p, L in zip(polys, lens):
            lo, hi = a - off, b - off
            off += L[-1]
            if hi <= 0 or lo >= L[-1] or len(p) < 2:
                continue
            lo, hi = max(lo, 0.0), min(hi, L[-1])
            xs = np.interp(np.r_[lo, L[(L > lo) & (L < hi)], hi], L, p[:, 0])
            ys = np.interp(np.r_[lo, L[(L > lo) & (L < hi)], hi], L, p[:, 1])
            out.append(np.stack([xs, ys], 1))
        return out

    def point_at(self, t, step=1.0):
        """Position and unit tangent at fraction t of the arc length (motion along a path)."""
        seg = self.trim(0.0, max(1e-6, min(1.0, t)), step)
        if not seg:
            p = self.flatten(step)[0][0]
            return p[0], np.array([1.0, 0.0])
        last = seg[-1]
        d = last[-1] - last[-2] if len(last) > 1 else np.array([1.0, 0.0])
        n = np.linalg.norm(d) or 1.0
        return last[-1], d / n

    def to_backend(self):
        """A canvas path (skia.Path or soft Path) for cv.path()."""
        from .canvas import new_path
        bp = new_path()
        for s in self.subs:
            bp.moveTo(*s["start"])
            for sg in s["segs"]:
                kind, *ps = sg
                if kind == "L":
                    bp.lineTo(*ps[0])
                elif kind == "Q":
                    bp.quadTo(*ps[0], *ps[1])
                else:
                    bp.cubicTo(*ps[0], *ps[1], *ps[2])
            if s["closed"]:
                bp.close()
        return bp


def mat(a=1.0, b=0.0, c=0.0, d=1.0, e=0.0, f=0.0) -> np.ndarray:
    """SVG-style matrix(a b c d e f) as 3x3."""
    return np.array([[a, c, e], [b, d, f], [0, 0, 1]], float)


def about(m: np.ndarray, cx: float, cy: float) -> np.ndarray:
    """Apply m around pivot (cx, cy)."""
    return mat(e=cx, f=cy) @ m @ mat(e=-cx, f=-cy)


def trs(dx=0.0, dy=0.0, rot=0.0, sx=1.0, sy=None) -> np.ndarray:
    sy = sx if sy is None else sy
    c, s = math.cos(rot), math.sin(rot)
    return mat(e=dx, f=dy) @ mat(c, s, -s, c) @ mat(sx, 0, 0, sy)


def draw_fill(cv, vp: VPath, fill, rule="nonzero", **kw):
    if fill is None or not vp.subs:
        return
    cv.path(vp.to_backend(), fill, rule=rule, **kw)


def draw_stroke(cv, vp: VPath, color, width=2.0, t0=0.0, t1=1.0, **kw):
    """Stroke the whole path (t0=0, t1=1) or a trimmed part of it (draw-on, write-on, travelling dash)."""
    if color is None or width <= 0:
        return
    if t0 <= 0.0 and t1 >= 1.0:
        cv.path(vp.to_backend(), None, stroke=color, sw=width, **kw)
        return
    for poly in vp.trim(t0, t1):
        if len(poly) >= 2:
            cv.polyline(poly, color, width, smooth=False, **kw)


def mask_to(cv, vp: VPath, bounds, feather=0.0):
    """Inside a cv.layer(bounds=...): erase everything outside `vp` (a shape mask).

    Use this rather than drawing the mask with blend="dst_in": a dst_in draw only touches pixels
    under the drawn shape (Skia) or its bounding box (soft backend), so content outside it survives.
    This draws the inverse (bounds rect + vp, even-odd) with dst_out, which behaves the same on both.
    """
    x, y, w, h = bounds
    pad = 4.0
    inv = VPath().moveTo(x - pad, y - pad).lineTo(x + w + pad, y - pad).lineTo(x + w + pad, y + h + pad) \
        .lineTo(x - pad, y + h + pad).close()
    inv.subs.extend(vp.subs)
    kw = {"blur": feather} if feather > 0 else {}
    cv.path(inv.to_backend(), "#000000", rule="evenodd", blend="dst_out", **kw)


def circle_vp(cx, cy, r) -> VPath:
    k = 0.5522847498 * r
    return (VPath().moveTo(cx, cy - r).cubicTo(cx + k, cy - r, cx + r, cy - k, cx + r, cy)
            .cubicTo(cx + r, cy + k, cx + k, cy + r, cx, cy + r).cubicTo(cx - k, cy + r, cx - r, cy + k, cx - r, cy)
            .cubicTo(cx - r, cy - k, cx - k, cy - r, cx, cy - r).close())


def from_points(pts: Iterable, closed=True) -> VPath:
    pts = [tuple(map(float, p)) for p in pts]
    vp = VPath().moveTo(*pts[0])
    for p in pts[1:]:
        vp.lineTo(*p)
    return vp.close() if closed else vp
