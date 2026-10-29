"""The principles of animation as reusable, testable code.

Squash & stretch ........ squash_stretch(), impact_squash()
Anticipation ............ anticipate()
Staging ................. (layout/camera; see camera.py and references/cinematography.md)
Straight-ahead/pose ..... curves.Channel (pose-to-pose) + simulate() (straight-ahead)
Follow-through/overlap .. Spring, lag_chain(), follow()
Slow in / slow out ...... easing presets ("slow_in_out", "heavy", "snap")
Arcs .................... curves.ArcPath
Secondary action ........ Spring/lag_chain on appendages, blink(), breathe()
Timing .................. timing_chart(), frames-per-action tables in references/principles.md
Exaggeration ............ parameters on all of the above (amount, overshoot)
Solid drawing ........... (design; turnarounds in references/assets.md)
Appeal .................. (design; shape language in references/assets.md)

Everything here is deterministic (seeded) so renders are reproducible.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

import numpy as np

from .curves import Channel, Key


# ------------------------------------------------------------ squash & stretch
def squash_stretch(speed: float, k: float = 0.0009, max_stretch: float = 0.35):
    """Volume-preserving stretch along the direction of travel.

    speed in px/frame. Returns (along, across) scale factors with along*across == 1.
    """
    s = min(max_stretch, abs(speed) * k * 10)
    along = 1.0 + s
    return along, 1.0 / along


def impact_squash(frames_since_impact: float, amount: float = 0.28, recover: float = 6.0,
                  wobble: float = 0.35):
    """Squash on contact then spring back. Returns (sx, sy), sx*sy == 1."""
    if frames_since_impact < 0:
        return 1.0, 1.0
    t = frames_since_impact / recover
    env = math.exp(-3.2 * t)
    sq = amount * env * math.cos(math.pi * t * (1 + wobble))
    sy = 1.0 - sq
    return 1.0 / max(sy, 0.2), sy


# ---------------------------------------------------------------- anticipation
def anticipate(f0: float, v0, v1, *, antic_frames=6, action_frames=8, settle_frames=10,
               antic=0.15, overshoot=0.08, hold_before=0.0) -> Channel:
    """Build a channel: rest -> wind-up (opposite) -> fast action -> overshoot -> settle.

    antic / overshoot are fractions of the travel distance. Scalar or vector values.
    """
    a = np.asarray(v0, float)
    b = np.asarray(v1, float)
    d = b - a
    wind = a - d * antic
    over = b + d * overshoot

    def val(x):
        return float(x) if np.ndim(x) == 0 else x

    f = f0 + hold_before
    keys = [Key(f0, val(a), None, hold_before),
            Key(f + antic_frames, val(wind), "snap"),
            Key(f + antic_frames + action_frames, val(over), "settle"),
            Key(f + antic_frames + action_frames + settle_frames, val(b))]
    keys[0].ease = "in_out_sine"
    return Channel(keys)


# --------------------------------------------------- follow-through / overlap
class Spring:
    """Critically-tunable damped spring that chases a target (semi-implicit Euler).

    stiffness ~ how hard it pulls (higher = tighter), damping ~ how quickly wobble
    dies (0.0-1.0 as damping ratio). Step it once per (sub)frame.
    """

    def __init__(self, value=0.0, stiffness=180.0, damping=0.35, mass=1.0):
        self.x = np.asarray(value, float).copy()
        self.v = np.zeros_like(self.x)
        self.k = stiffness
        self.c = 2 * damping * math.sqrt(stiffness * mass)
        self.m = mass

    def step(self, target, dt=1 / 24):
        target = np.asarray(target, float)
        n = max(1, int(math.ceil(dt / (1 / 240))))  # sub-step for stability
        h = dt / n
        for _ in range(n):
            a = (-self.k * (self.x - target) - self.c * self.v) / self.m
            self.v = self.v + a * h
            self.x = self.x + self.v * h
        return self.x.copy()


def follow(target: Callable[[float], object], frames: Sequence[float], *, stiffness=160.0,
           damping=0.3, fps=24.0, warmup=24):
    """Pre-bake a springy follower of `target(frame)` over `frames` (ascending).

    Returns dict frame -> value. Warm-up frames run first so frame 0 is at rest.
    """
    frames = list(frames)
    s = Spring(target(frames[0]), stiffness, damping)
    out = {}
    prev = frames[0]
    for _ in range(warmup):
        s.step(target(frames[0]), 1 / fps)
    for f in frames:
        dt = max(1e-4, (f - prev)) / fps if f != prev else 1 / fps
        out[f] = s.step(target(f), dt)
        prev = f
    return out


def lag_chain(root_angle: Callable[[float], float], frames: Sequence[float], n: int = 4,
              stiffness=(220, 160, 120, 90), damping=0.28, fps=24.0, gain=1.0):
    """Overlapping action for tails, antennae, hood tips, ears, cloth ends.

    Each segment springs toward its parent's angle, so motion ripples down the chain.
    Returns dict frame -> [angle_0..angle_n-1] (radians, relative to parent).
    """
    frames = list(frames)
    stiff = list(stiffness) + [stiffness[-1]] * max(0, n - len(stiffness))
    springs = [Spring(0.0, stiff[i], damping) for i in range(n)]
    out = {}
    prev = frames[0]
    last_root = root_angle(frames[0])
    for f in frames:
        dt = max(1e-4, f - prev) / fps if f != prev else 1 / fps
        root = root_angle(f)
        # angular velocity of the parent drives the lag (inertia)
        drive = (root - last_root)
        target = -drive * 6.0 * gain
        angles = []
        for i, s in enumerate(springs):
            ang = float(s.step(target, dt))
            angles.append(ang)
            target = ang * 0.9
        out[f] = angles
        last_root = root
        prev = f
    return out


def simulate_positional(path: Callable[[float], Sequence[float]], frames, *, stiffness=140.0,
                        damping=0.32, fps=24.0, gravity=(0.0, 0.0)):
    """Secondary motion of a dangling object (bag, lantern) hanging from `path(f)`.

    Returns frame -> offset (dx, dy) of the object relative to its anchor.
    """
    frames = list(frames)
    s = Spring(np.zeros(2), stiffness, damping)
    out = {}
    prev = frames[0]
    last = np.asarray(path(frames[0]), float)
    for f in frames:
        dt = max(1e-4, f - prev) / fps if f != prev else 1 / fps
        p = np.asarray(path(f), float)
        vel = (p - last) / max(dt * fps, 1e-6)
        target = -vel * 0.9 + np.asarray(gravity, float)
        out[f] = s.step(target, dt)
        last = p
        prev = f
    return out


def baked(table: dict):
    """Turn a {frame: value} bake into a callable with linear interpolation.

    Simulations are stepped on a fixed grid; motion-blur sub-frames and preview
    frames read between grid points through this.
    """
    ks = np.array(sorted(table))
    vs = np.array([np.asarray(table[k], float) for k in ks])

    def get(f):
        if f <= ks[0]:
            return vs[0]
        if f >= ks[-1]:
            return vs[-1]
        i = int(np.searchsorted(ks, f)) - 1
        t = (f - ks[i]) / (ks[i + 1] - ks[i])
        return vs[i] * (1 - t) + vs[i + 1] * t

    return get


# ------------------------------------------------------------- life & acting
def smooth_noise(seed: int = 0):
    """1-D value noise, smooth, deterministic. Returns n(t) in [-1, 1]."""
    rng = np.random.default_rng(seed)
    table = rng.uniform(-1, 1, 1024)

    def n(t: float) -> float:
        i = int(math.floor(t)) & 1023
        j = (i + 1) & 1023
        u = t - math.floor(t)
        u = u * u * (3 - 2 * u)
        return float(table[i] * (1 - u) + table[j] * u)

    return n


def breathe(f: float, fps=24.0, rate_hz=0.28, amount=0.012, phase=0.0):
    """Moving-hold breathing scale (1 +/- amount). Never let a character freeze."""
    return 1.0 + amount * math.sin(2 * math.pi * (f / fps * rate_hz + phase))


def blink(f: float, blinks: Sequence[float], close=2.0, hold=1.0, open_=3.0):
    """Eyelid closure 0..1 for blink start frames. Fast close, brief hold, slower open."""
    for b in blinks:
        d = f - b
        if 0 <= d < close:
            return d / close
        if close <= d < close + hold:
            return 1.0
        if close + hold <= d < close + hold + open_:
            return 1.0 - (d - close - hold) / open_
    return 0.0


def eyes_lead(head_channel: Channel, lead_frames: float = 3.0):
    """Eyes arrive before the head: returns eye-target sampler offset in time."""
    return lambda f: head_channel(f + lead_frames)


# ------------------------------------------------------------------ IK helper
def two_bone_ik(root, target, l1, l2, bend_dir=1.0):
    """Planar two-bone IK. Returns (joint, end) points. bend_dir +1/-1 picks the knee side.

    End is clamped to reach; bone lengths are preserved exactly.
    """
    r = np.asarray(root, float)
    t = np.asarray(target, float)
    d = t - r
    dist = float(np.linalg.norm(d))
    dist = max(1e-6, min(dist, l1 + l2 - 1e-6))
    if np.linalg.norm(d) > 1e-9:
        dirn = d / np.linalg.norm(d)
    else:
        dirn = np.array([0.0, 1.0])
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    mid = r + dirn * a
    perp = np.array([-dirn[1], dirn[0]]) * bend_dir
    joint = mid + perp * h
    end = r + dirn * dist
    return joint, end
