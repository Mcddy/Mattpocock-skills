"""Particle FX that stay pure functions of time (parallel renders and motion blur stay exact).

    dust = dust_puff(frame=118, pos=(840, 860), ground=860)     # a landing contact
    burst = sparks(frame=40, pos=(500, 400))
    snow = Emitter(0, 240, rate=40, origin=lambda f, r: (r.uniform(0, 1920), -20), ...)
    ...in draw(cv, f): dust.draw(cv, f); burst.draw(cv, f, blend="plus")

Physics per particle is closed form (gravity + linear drag), so any frame can be drawn
without simulating the frames before it. Use FX to *support* a beat (a contact, an
impact, a reveal); sparkles and glows sprinkled for "magic" are a stock tell (see
references/deslop-motion.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class _P:
    birth: float
    x0: float
    y0: float
    vx: float
    vy: float
    life: float
    size: float
    col: str
    spin: float
    rot0: float


def _pos(p: _P, t, g, k, ground):
    if k > 1e-6:
        e = 1 - math.exp(-k * t)
        x = p.x0 + p.vx / k * e
        y = p.y0 + g / k * t + (p.vy - g / k) / k * e
        vy = g / k + (p.vy - g / k) * math.exp(-k * t)
        vx = p.vx * math.exp(-k * t)
    else:
        x, y = p.x0 + p.vx * t, p.y0 + p.vy * t + 0.5 * g * t * t
        vx, vy = p.vx, p.vy + g * t
    if ground is not None and y > ground:
        y, vy = ground, 0.0
    return x, y, vx, vy


class Burst:
    """One-off emission at `frame` (contact, impact, pop)."""

    def __init__(self, frame, pos, n=24, speed=(120.0, 320.0), angle=(-math.pi, 0.0), gravity=900.0, drag=2.0,
                 life=(0.4, 0.9), size=(3.0, 8.0), grow=1.0, colors=("#FFFFFF",), kind="dot", seed=0, ground=None,
                 fps=24.0, spin=(-8.0, 8.0), jitter=4.0, alpha=1.0, blur=0.0):
        r = np.random.default_rng(seed)
        self.ps = []
        for i in range(n):
            a = r.uniform(*angle)
            s = r.uniform(*speed)
            self.ps.append(_P(frame, pos[0] + r.normal(0, jitter), pos[1] + r.normal(0, jitter * 0.5),
                              math.cos(a) * s, math.sin(a) * s, r.uniform(*life), r.uniform(*size),
                              colors[i % len(colors)], r.uniform(*spin), r.uniform(0, math.tau)))
        self.g, self.k, self.ground, self.fps = gravity, drag, ground, fps
        self.kind, self.grow, self.alpha, self.blur = kind, grow, alpha, blur

    def alive(self, f):
        return any(0 <= (f - p.birth) / self.fps <= p.life for p in self.ps)

    def draw(self, cv, f, blend=None):
        for p in self.ps:
            t = (f - p.birth) / self.fps
            if t < 0 or t > p.life:
                continue
            u = t / p.life
            x, y, vx, vy = _pos(p, t, self.g, self.k, self.ground)
            fade = min(1.0, u / 0.08) * (1 - u) ** 1.4
            a = self.alpha * fade
            sz = p.size * (1 + (self.grow - 1) * u)
            if self.kind == "spark":
                L = min(0.05 * math.hypot(vx, vy), 28.0)
                ang = math.atan2(vy, vx)
                cv.line((x - math.cos(ang) * L, y - math.sin(ang) * L), (x, y), p.col, max(1.0, sz * 0.5), alpha=a,
                        blend=blend)
            elif self.kind == "confetti":
                rot = p.rot0 + p.spin * t
                flip = abs(math.cos(p.spin * 1.7 * t))
                with cv.at(x, y, rot, 1.0, max(0.15, flip)):
                    cv.rect(-sz, -sz * 0.45, sz * 2, sz * 0.9, p.col, alpha=a, blend=blend)
            elif self.kind == "puff":
                cv.circle(x, y, sz, p.col, alpha=a * 0.85, blend=blend, blur=self.blur or sz * 0.35)
            else:
                cv.circle(x, y, sz, p.col, alpha=a, blend=blend, blur=self.blur)


class Emitter(Burst):
    """Continuous emission between frames [start, end) at `rate` particles per second.

    origin(frame, rng) -> (x, y) chooses where each particle is born (a line for snow,
    a point for steam). Other args as Burst.
    """

    def __init__(self, start, end, rate, origin, fps=24.0, seed=0, **kw):
        r = np.random.default_rng(seed)
        n = int((end - start) / fps * rate)
        super().__init__(start, (0, 0), n=0, fps=fps, seed=seed, **{k: v for k, v in kw.items() if k not in ("n",)})
        speed = kw.get("speed", (40.0, 80.0))
        angle = kw.get("angle", (math.pi / 2 - 0.2, math.pi / 2 + 0.2))
        life = kw.get("life", (2.0, 4.0))
        size = kw.get("size", (2.0, 4.0))
        colors = kw.get("colors", ("#FFFFFF",))
        spin = kw.get("spin", (-2.0, 2.0))
        for i in range(n):
            b = start + i * fps / rate + r.uniform(0, fps / rate)
            x0, y0 = origin(b, r)
            a = r.uniform(*angle)
            s = r.uniform(*speed)
            self.ps.append(_P(b, x0, y0, math.cos(a) * s, math.sin(a) * s, r.uniform(*life), r.uniform(*size),
                              colors[i % len(colors)], r.uniform(*spin), r.uniform(0, math.tau)))


# ---------------------------------------------------------------- presets
def dust_puff(frame, pos, ground=None, scale=1.0, color="#CDB99D", seed=1, fps=24.0):
    """Low, sideways puffs to both sides at a landing or a heavy step: sells weight. Keep it small and quick."""
    out = None
    for side, (a0, a1) in ((-1, (math.pi - 0.05, math.pi + 0.55)), (1, (-0.55, 0.05))):
        b = Burst(frame, (pos[0] + side * 8 * scale, pos[1] - 3 * scale), n=int(14 * scale) + 4,
                  speed=(90 * scale, 380 * scale), angle=(a0, a1), gravity=-40.0, drag=4.2, life=(0.35, 0.8),
                  size=(4 * scale, 10 * scale), grow=2.8, colors=(color,), kind="puff", seed=seed + (side > 0),
                  ground=ground, fps=fps, alpha=0.45, jitter=6 * scale)
        out = b if out is None else (out.ps.extend(b.ps) or out)
    return out


def sparks(frame, pos, n=26, color=("#FFE3A3", "#FFB347", "#FFFFFF"), seed=2, fps=24.0, ground=None):
    """Hot metal / electrical sparks: fast streaks with gravity. Draw with blend='plus'."""
    return Burst(frame, pos, n=n, speed=(260, 620), angle=(-math.pi * 0.95, -math.pi * 0.05), gravity=1400.0, drag=1.2,
                 life=(0.25, 0.6), size=(2.0, 4.0), colors=color, kind="spark", seed=seed, ground=ground, fps=fps)


def confetti(frame, pos, colors=("#E8A33D", "#3FA7A0", "#E4572E", "#F3EDE2"), n=60, seed=3, fps=24.0, ground=None):
    """Celebration burst: up and out, then a slow fluttering fall (high drag)."""
    return Burst(frame, pos, n=n, speed=(300, 700), angle=(-math.pi * 0.85, -math.pi * 0.15), gravity=700.0, drag=3.2,
                 life=(1.4, 2.4), size=(4.0, 7.0), colors=colors, kind="confetti", seed=seed, ground=ground, fps=fps,
                 spin=(-9.0, 9.0))


def snow(start, end, width, fps=24.0, rate=60, seed=4, color="#FFFFFF"):
    return Emitter(start, end, rate, lambda f, r: (r.uniform(-40, width + 40), -20.0), fps=fps, seed=seed,
                   speed=(30.0, 70.0), angle=(math.pi / 2 - 0.35, math.pi / 2 + 0.35), gravity=20.0, drag=0.6,
                   life=(6.0, 9.0), size=(1.5, 4.0), colors=(color,), kind="dot", blur=0.6)


def steam(start, end, pos, fps=24.0, rate=10, seed=5, color="#FFFFFF"):
    return Emitter(start, end, rate, lambda f, r: (pos[0] + r.normal(0, 4), pos[1]), fps=fps, seed=seed,
                   speed=(20.0, 45.0), angle=(-math.pi / 2 - 0.25, -math.pi / 2 + 0.25), gravity=-25.0, drag=0.8,
                   life=(1.2, 2.2), size=(5.0, 9.0), grow=3.0, colors=(color,), kind="puff", alpha=0.35)
