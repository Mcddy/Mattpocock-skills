"""Easing and dynamics primitives.

Every function maps t in [0, 1] -> progress (usually 0..1, may overshoot).
Use `get(spec)` to resolve a name, callable, or tuple spec:
    "linear", "in_cubic", "out_back", "in_out_sine", ...
    ("bezier", x1, y1, x2, y2)          CSS-style cubic-bezier
    ("spring", zeta, omega)             damped spring step response
    ("back", s)                          out-back with custom overshoot
    ("steps", n)                         stepped (holds) - for blocking / limited animation
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable, Union

Ease = Callable[[float], float]
EaseSpec = Union[str, Ease, tuple, None]


def clamp01(t: float) -> float:
    return 0.0 if t < 0.0 else 1.0 if t > 1.0 else t


def linear(t: float) -> float:
    return t


def _poly(p: int):
    def e_in(t):
        return t ** p

    def e_out(t):
        return 1 - (1 - t) ** p

    def e_in_out(t):
        return (2 ** (p - 1)) * t ** p if t < 0.5 else 1 - ((-2 * t + 2) ** p) / 2

    return e_in, e_out, e_in_out


in_quad, out_quad, in_out_quad = _poly(2)
in_cubic, out_cubic, in_out_cubic = _poly(3)
in_quart, out_quart, in_out_quart = _poly(4)
in_quint, out_quint, in_out_quint = _poly(5)


def in_sine(t):
    return 1 - math.cos(t * math.pi / 2)


def out_sine(t):
    return math.sin(t * math.pi / 2)


def in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def in_expo(t):
    return 0.0 if t == 0 else 2 ** (10 * t - 10)


def out_expo(t):
    return 1.0 if t == 1 else 1 - 2 ** (-10 * t)


def in_out_expo(t):
    if t in (0.0, 1.0):
        return t
    return 2 ** (20 * t - 10) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2


def in_circ(t):
    return 1 - math.sqrt(1 - t * t)


def out_circ(t):
    return math.sqrt(1 - (t - 1) ** 2)


def in_out_circ(t):
    if t < 0.5:
        return (1 - math.sqrt(1 - (2 * t) ** 2)) / 2
    return (math.sqrt(1 - (-2 * t + 2) ** 2) + 1) / 2


def make_back(s: float = 1.70158):
    def in_back(t):
        return (s + 1) * t ** 3 - s * t ** 2

    def out_back(t):
        u = t - 1
        return 1 + (s + 1) * u ** 3 + s * u ** 2

    def in_out_back(t):
        s2 = s * 1.525
        if t < 0.5:
            return ((2 * t) ** 2 * ((s2 + 1) * 2 * t - s2)) / 2
        return ((2 * t - 2) ** 2 * ((s2 + 1) * (t * 2 - 2) + s2) + 2) / 2

    return in_back, out_back, in_out_back


in_back, out_back, in_out_back = make_back()


def out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def in_bounce(t):
    return 1 - out_bounce(1 - t)


def out_elastic(t):
    if t in (0.0, 1.0):
        return t
    c4 = (2 * math.pi) / 3
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


# ---------------------------------------------------------------- cubic bezier
@lru_cache(maxsize=256)
def cubic_bezier(x1: float, y1: float, x2: float, y2: float) -> Ease:
    """CSS cubic-bezier(x1, y1, x2, y2). x must stay in [0,1]; y may overshoot."""
    if not (0 <= x1 <= 1 and 0 <= x2 <= 1):
        raise ValueError("bezier x control points must be within [0, 1]")
    cx = 3 * x1
    bx = 3 * (x2 - x1) - cx
    ax = 1 - cx - bx
    cy = 3 * y1
    by = 3 * (y2 - y1) - cy
    ay = 1 - cy - by

    def sx(u):
        return ((ax * u + bx) * u + cx) * u

    def sy(u):
        return ((ay * u + by) * u + cy) * u

    def dsx(u):
        return (3 * ax * u + 2 * bx) * u + cx

    def solve(x):
        u = x
        for _ in range(8):  # Newton
            err = sx(u) - x
            if abs(err) < 1e-7:
                return u
            d = dsx(u)
            if abs(d) < 1e-6:
                break
            u -= err / d
        lo, hi = 0.0, 1.0  # bisection fallback
        u = x
        for _ in range(40):
            v = sx(u)
            if abs(v - x) < 1e-7:
                break
            if v < x:
                lo = u
            else:
                hi = u
            u = (lo + hi) / 2
        return u

    def ease(t):
        t = clamp01(t)
        return sy(solve(t))

    ease.bezier = (x1, y1, x2, y2)      # exporters (CSS, Lottie) reuse the exact curve
    return ease


# CSS/Lottie bezier equivalents for the maths easings (easings.net fits; close, not identical)
BEZIER_FITS = {
    "linear": (0.0, 0.0, 1.0, 1.0),
    "in_quad": (0.11, 0.0, 0.5, 0.0), "out_quad": (0.5, 1.0, 0.89, 1.0), "in_out_quad": (0.45, 0.0, 0.55, 1.0),
    "in_cubic": (0.32, 0.0, 0.67, 0.0), "out_cubic": (0.33, 1.0, 0.68, 1.0), "in_out_cubic": (0.65, 0.0, 0.35, 1.0),
    "in_quart": (0.5, 0.0, 0.75, 0.0), "out_quart": (0.25, 1.0, 0.5, 1.0), "in_out_quart": (0.76, 0.0, 0.24, 1.0),
    "in_quint": (0.64, 0.0, 0.78, 0.0), "out_quint": (0.22, 1.0, 0.36, 1.0), "in_out_quint": (0.83, 0.0, 0.17, 1.0),
    "in_sine": (0.12, 0.0, 0.39, 0.0), "out_sine": (0.61, 1.0, 0.88, 1.0), "in_out_sine": (0.37, 0.0, 0.63, 1.0),
    "in_expo": (0.7, 0.0, 0.84, 0.0), "out_expo": (0.16, 1.0, 0.3, 1.0), "in_out_expo": (0.87, 0.0, 0.13, 1.0),
    "in_circ": (0.55, 0.0, 1.0, 0.45), "out_circ": (0.0, 0.55, 0.45, 1.0), "in_out_circ": (0.85, 0.0, 0.15, 1.0),
    "in_back": (0.36, 0.0, 0.66, -0.56), "out_back": (0.34, 1.56, 0.64, 1.0), "in_out_back": (0.68, -0.6, 0.32, 1.6),
}


def bezier_of(spec):
    """(x1, y1, x2, y2) if the ease is a cubic bezier (exactly or by a standard fit), else None (spring, bounce...)."""
    if spec is None:
        spec = "slow_in_out"
    if isinstance(spec, str) and spec in BEZIER_FITS:
        return BEZIER_FITS[spec]
    f = get(spec)
    return getattr(f, "bezier", None)


# ------------------------------------------------------------------- springs
def spring(zeta: float = 0.45, omega: float = 14.0) -> Ease:
    """Damped-spring step response normalised so that t=1 is ~settled.

    zeta < 1 overshoots (bouncy), zeta = 1 critically damped, > 1 sluggish.
    omega sets how many oscillations fit in the segment (higher = more wobbles).
    The response is forced to land exactly on 1.0 at t=1 so keys stay honest.
    """
    zeta = max(1e-4, zeta)

    def raw(t):
        if zeta < 1:
            wd = omega * math.sqrt(1 - zeta * zeta)
            return 1 - math.exp(-zeta * omega * t) * (
                math.cos(wd * t) + (zeta / math.sqrt(1 - zeta * zeta)) * math.sin(wd * t)
            )
        if zeta == 1:
            return 1 - math.exp(-omega * t) * (1 + omega * t)
        r1 = -omega * (zeta - math.sqrt(zeta * zeta - 1))
        r2 = -omega * (zeta + math.sqrt(zeta * zeta - 1))
        c2 = r1 / (r1 - r2)
        c1 = 1 - c2
        return 1 - (c1 * math.exp(r1 * t) + c2 * math.exp(r2 * t))

    end = raw(1.0)

    def ease(t):
        t = clamp01(t)
        # blend the residual error out over the last 15% so value(1) == 1 exactly
        v = raw(t)
        w = clamp01((t - 0.85) / 0.15)
        return v + (1 - end) * w * w * (3 - 2 * w) if t < 1 else 1.0

    return ease


def steps(n: int) -> Ease:
    """Hold-then-jump: n discrete steps (blocking / limited animation)."""
    n = max(1, int(n))
    return lambda t: math.floor(clamp01(t) * n) / n if t < 1 else 1.0


# ------------------------------------------------------------------- registry
_NAMED = {
    "linear": linear,
    "in_quad": in_quad, "out_quad": out_quad, "in_out_quad": in_out_quad,
    "in_cubic": in_cubic, "out_cubic": out_cubic, "in_out_cubic": in_out_cubic,
    "in_quart": in_quart, "out_quart": out_quart, "in_out_quart": in_out_quart,
    "in_quint": in_quint, "out_quint": out_quint, "in_out_quint": in_out_quint,
    "in_sine": in_sine, "out_sine": out_sine, "in_out_sine": in_out_sine,
    "in_expo": in_expo, "out_expo": out_expo, "in_out_expo": in_out_expo,
    "in_circ": in_circ, "out_circ": out_circ, "in_out_circ": in_out_circ,
    "in_back": in_back, "out_back": out_back, "in_out_back": in_out_back,
    "in_bounce": in_bounce, "out_bounce": out_bounce, "out_elastic": out_elastic,
    # Character-animation presets (named for intent, not maths)
    "slow_in_out": cubic_bezier(0.45, 0.0, 0.55, 1.0),     # default pose-to-pose
    "snap": cubic_bezier(0.2, 0.0, 0.0, 1.0),               # fast attack, long settle
    "anticipate": cubic_bezier(0.6, -0.35, 0.7, 0.0),       # pulls back before going
    "heavy": cubic_bezier(0.7, 0.0, 0.35, 1.0),             # mass: slow start, firm stop
    "float": cubic_bezier(0.35, 0.0, 0.25, 1.0),            # light objects, cloth
    "settle": spring(0.55, 13.0),                           # overshoot + one wobble
    "wobble": spring(0.28, 22.0),                           # jelly / antenna
    "hold": steps(1),
}


def get(spec: EaseSpec) -> Ease:
    if spec is None:
        return _NAMED["slow_in_out"]
    if callable(spec):
        return spec
    if isinstance(spec, str):
        try:
            return _NAMED[spec]
        except KeyError as exc:
            raise KeyError(f"unknown ease '{spec}'. Options: {sorted(_NAMED)}") from exc
    if isinstance(spec, tuple):
        kind, *args = spec
        if kind == "bezier":
            return cubic_bezier(*args)
        if kind == "spring":
            return spring(*args)
        if kind == "back":
            return make_back(*args)[1]
        if kind == "steps":
            return steps(*args)
    raise ValueError(f"cannot resolve ease spec {spec!r}")


def names() -> list[str]:
    return sorted(_NAMED)
