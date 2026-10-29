"""Keyframe channels: the pose-to-pose backbone.

A Channel holds Keys (frame, value, ease). The ease on a key shapes the segment
that LEAVES that key and arrives at the next one. Values may be floats or
tuples/arrays (positions, colours). Frames may be fractional, which is how
motion blur samples sub-frames.

Typical use
-----------
    x = Channel([K(0, 100), K(18, 640, "snap"), K(40, 640)])
    x(12.5)              # value at frame 12.5
    x.stepped(12.5)      # blocking preview: holds on the previous key
    x.on(12.5, 2)        # sample on twos (limited animation look)

Arcs
----
Living things move on arcs. Use ArcPath for 2-D travel between poses instead of
straight-line interpolation of x and y.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from . import easing as E


@dataclass
class Key:
    frame: float
    value: object
    ease: object = None          # ease spec for the segment leaving this key
    hold: float = 0.0            # frames to hold this value before travelling on
    drift: float = 0.0           # 'moving hold' amplitude, as fraction of next delta

    def __post_init__(self):
        self.frame = float(self.frame)


def K(frame, value, ease=None, hold=0.0, drift=0.0) -> Key:
    return Key(frame, value, ease, hold, drift)


def _lerp(a, b, t):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return a + (b - a) * t


@dataclass
class Channel:
    keys: list = field(default_factory=list)

    def __post_init__(self):
        if not self.keys:
            raise ValueError("Channel needs at least one key")
        frames = [k.frame for k in self.keys]
        if any(b < a for a, b in zip(frames, frames[1:])):
            # Keys are authored in story order; a key landing before its predecessor almost
            # always means a beat was timed past the end of the shot (e.g. K(N, ...) with N
            # smaller than a later beat), which silently re-orders the curve.
            import warnings
            warnings.warn(f"Channel keys out of chronological order {frames}: a beat is probably timed past the "
                          f"shot end or before an earlier beat; sorting them changes the motion.", stacklevel=2)
        self.keys = sorted(self.keys, key=lambda k: k.frame)

    # -- authoring helpers -------------------------------------------------
    def add(self, frame, value, ease=None, hold=0.0, drift=0.0) -> "Channel":
        self.keys.append(Key(frame, value, ease, hold, drift))
        self.keys.sort(key=lambda k: k.frame)
        return self

    def then(self, dframes, value, ease=None, hold=0.0, drift=0.0) -> "Channel":
        """Append a key `dframes` after the last key (timing-chart style)."""
        last = self.keys[-1]
        return self.add(last.frame + dframes, value, ease, hold, drift)

    @property
    def start(self) -> float:
        return self.keys[0].frame

    @property
    def end(self) -> float:
        return self.keys[-1].frame

    # -- evaluation ----------------------------------------------------------
    def _segment(self, f):
        ks = self.keys
        if f <= ks[0].frame:
            return None, ks[0]
        if f >= ks[-1].frame:
            return None, ks[-1]
        lo, hi = 0, len(ks) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if ks[mid].frame <= f:
                lo = mid
            else:
                hi = mid
        return ks[lo], ks[hi]

    def __call__(self, f: float):
        a, b = self._segment(f)
        if a is None:
            return b.value
        start = a.frame + a.hold
        if f <= start:
            if a.drift and b.frame > start:
                # moving hold: creep 'drift' of the way toward the next value
                u = (f - a.frame) / max(a.hold, 1e-6)
                return _lerp(a.value, b.value, a.drift * E.in_out_sine(u))
            return a.value
        span = b.frame - start
        t = (f - start) / span if span > 0 else 1.0
        p = E.get(a.ease)(E.clamp01(t))
        base = a.value if not a.drift else _lerp(a.value, b.value, a.drift)
        return _lerp(base, b.value, p)

    def stepped(self, f: float):
        """Blocking view: value of the last key at or before f (no in-betweens)."""
        a, b = self._segment(f)
        if a is None:
            return b.value
        return a.value

    def on(self, f: float, n: int = 2, origin: float = 0.0):
        """Sample on n's (hold every pose for n frames) for a hand-drawn cadence."""
        q = origin + math.floor((f - origin) / n) * n
        return self(q)

    def velocity(self, f: float, h: float = 0.25):
        a = np.asarray(self(f - h), float)
        b = np.asarray(self(f + h), float)
        v = (b - a) / (2 * h)
        return float(v) if v.ndim == 0 else v

    def sample(self, frames: Iterable[float]):
        return [self(f) for f in frames]


# ------------------------------------------------------------------- arcs
def quad_bezier(p0, c, p1, t):
    p0, c, p1 = (np.asarray(v, float) for v in (p0, c, p1))
    u = 1 - t
    return u * u * p0 + 2 * u * t * c + t * t * p1


@dataclass
class ArcPath:
    """2-D travel along arcs between poses.

    points: list of (frame, (x, y)) poses; bend: per-segment arc height in px
    (positive bows 'up' on screen, i.e. negative y). ease per segment.
    """
    poses: Sequence
    bend: Sequence = ()
    eases: Sequence = ()

    def __call__(self, f: float):
        poses = self.poses
        if f <= poses[0][0]:
            return np.asarray(poses[0][1], float)
        if f >= poses[-1][0]:
            return np.asarray(poses[-1][1], float)
        for i in range(len(poses) - 1):
            f0, p0 = poses[i]
            f1, p1 = poses[i + 1]
            if f0 <= f <= f1:
                t = (f - f0) / (f1 - f0) if f1 > f0 else 1.0
                ease = E.get(self.eases[i] if i < len(self.eases) else None)
                t = ease(t)
                p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
                mid = (p0a + p1a) / 2
                d = p1a - p0a
                n = np.array([d[1], -d[0]])
                ln = np.linalg.norm(n)
                h = self.bend[i] if i < len(self.bend) else 0.0
                ctrl = mid + (n / ln * h * (1 if n[1] <= 0 else -1) if ln > 0 else 0)
                return quad_bezier(p0a, ctrl, p1a, t)
        return np.asarray(poses[-1][1], float)


def timing_chart(start: float, end: float, n: int, ease="slow_in_out"):
    """Spacing of n in-betweens between two keys, as an animator's timing chart.

    Returns the normalised progress at each in-between; handy to *see* the
    spacing (bunched near keys = slow in/out) before committing.
    """
    e = E.get(ease)
    return [round(e(i / (n + 1)), 4) for i in range(1, n + 1)]


class Tremor(Channel):
    """A Channel plus an effort vibration between `start` and `end` frames: strain, cold, fear, a held
    heavy weight. Classic hand-drawn vibration alternates sides every frame (on ones) with uneven
    amplitude; `amp` is the peak offset in the channel's units, faded in/out over `ramp` frames.
    Pure in f (motion blur safe). Works for scalar and 2-tuple channels (hands)."""

    def __init__(self, base: Channel, start: float, end: float, amp: float, ramp: float = 4.0, seed: int = 0):
        super().__init__(list(base.keys))
        self.base, self.t0, self.t1, self.amp, self.ramp, self.seed = base, start, end, amp, ramp, seed

    def _env(self, f):
        if f <= self.t0 or f >= self.t1:
            return 0.0
        a = min(1.0, (f - self.t0) / max(self.ramp, 1e-6), (self.t1 - f) / max(self.ramp, 1e-6))
        return E.in_out_sine(a)

    def _n(self, i, k=0):
        x = math.sin((i * 12.9898 + k * 78.233 + self.seed * 37.719)) * 43758.5453
        return x - math.floor(x)                      # deterministic hash in 0..1

    def __call__(self, f: float):
        v = self.base(f)
        e = self._env(f)
        if e <= 0:
            return v
        i = int(round(f))
        side = 1.0 if i % 2 == 0 else -1.0
        if isinstance(v, (tuple, list)):
            return tuple(float(c) + side * self.amp * e * (0.45 + 0.55 * self._n(i, j)) for j, c in enumerate(v))
        return float(v) + side * self.amp * e * (0.45 + 0.55 * self._n(i))
