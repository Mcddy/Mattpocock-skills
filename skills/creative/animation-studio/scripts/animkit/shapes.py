"""Shape helpers for explainers and motion design: build, resample and morph polygons.

Explainers should *transform* one idea into the next (dot grid -> wave, cone -> bands)
rather than cut between diagrams. morph() makes any closed shape become any other.
"""
from __future__ import annotations

import math

import numpy as np


def circle(cx, cy, r, n=96):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], 1)


def rect(x, y, w, h):
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], float)


def star(cx, cy, r_out, r_in, points=5, rot=-math.pi / 2):
    out = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + math.pi * i / points
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(out, float)


def wave(x0, x1, y, amp, cycles, n=200, phase=0.0, thickness=None):
    """Polyline of a sine wave; with thickness, a closed ribbon polygon."""
    xs = np.linspace(x0, x1, n)
    ys = y + amp * np.sin(2 * math.pi * cycles * (xs - x0) / (x1 - x0) + phase)
    line = np.stack([xs, ys], 1)
    if thickness is None:
        return line
    return np.concatenate([line + [0, -thickness / 2], (line + [0, thickness / 2])[::-1]], 0)


def resample(poly, n, closed=True):
    """n points evenly spaced by arc length."""
    P = np.asarray(poly, float)
    if closed:
        P = np.concatenate([P, P[:1]], 0)
    seg = np.hypot(*np.diff(P, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=not closed)
    return np.stack([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], 1)


def _area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def morph(a, b, t, n=160):
    """Interpolate closed shape a -> b at t in [0, 1] (apply your ease to t first).

    Both are resampled to n points, matched in winding, and b is rotated in index so
    corresponding points are as close as possible (no twisting through the middle).
    """
    A = resample(a, n)
    B = resample(b, n)
    if np.sign(_area(A)) != np.sign(_area(B)):
        B = B[::-1]
    best, shift = None, 0
    for k in range(0, n, max(1, n // 64)):
        d = np.sum((A - np.roll(B, -k, axis=0)) ** 2)
        if best is None or d < best:
            best, shift = d, k
    B = np.roll(B, -shift, axis=0)
    return A + (B - A) * float(t)
