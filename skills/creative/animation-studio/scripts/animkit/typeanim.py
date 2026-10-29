"""Kinetic typography that respects type: per-letter motion, tracking, never squashed glyphs.

    word = KineticText("SETTLE", size=160, family=fonts.best_available("display"), weight=800)
    def draw(cv, f):
        word.draw(cv, 960, 560, f, stagger_in(start=10, per=2, dur=14, ease="settle", rise=90),
                  color="#F3E8D2", align="center")

Effects are functions (index, n, f) -> dict(dx, dy, rot, scale, alpha, track) per glyph,
so they compose: combine(stagger_in(...), tracking_breathe(...)).
Scale is always uniform: stretch a word with tracking, never by squashing letters.
"""
from __future__ import annotations

import math
from typing import Callable

from . import easing as E


class KineticText:
    def __init__(self, text, size=96, family="Inter", weight=700, path=None, tracking=0.0):
        self.text, self.size, self.family, self.weight, self.path, self.tracking = text, size, family, weight, path, tracking
        self._widths = None

    def _measure(self, cv):
        if self._widths is None:
            # measure with the canvas so both backends agree
            self._widths = [cv.text(ch, -10_000, -10_000, self.size, self.family, self.weight, "#00000000",
                                    path=self.path) for ch in self.text]
        return self._widths

    def draw(self, cv, x, y, f, effect: Callable | None = None, color="#FFFFFF", align="left"):
        ws = self._measure(cv)
        n = len(self.text)
        states = [effect(i, n, f) if effect else {} for i in range(n)]
        extra = [st.get("track", 0.0) for st in states]
        total = sum(ws) + self.tracking * (n - 1) + sum(extra[:-1])
        cx = x - (total / 2 if align == "center" else total if align == "right" else 0)
        for i, ch in enumerate(self.text):
            st = states[i]
            a = st.get("alpha", 1.0)
            if a > 0.001 and ch.strip():
                gx = cx + ws[i] / 2
                with cv.at(gx + st.get("dx", 0.0), y + st.get("dy", 0.0), st.get("rot", 0.0),
                           st.get("scale", 1.0), st.get("scale", 1.0)):
                    cv.text(ch, -ws[i] / 2, 0, self.size, self.family, self.weight, color, alpha=a, path=self.path)
            cx += ws[i] + self.tracking + extra[i]
        return total


def stagger_in(start=0, per=2.0, dur=12.0, ease="settle", rise=60.0, fade=0.35, rot=0.0):
    e = E.get(ease)

    def fx(i, n, f):
        t = (f - start - i * per) / dur
        if t <= 0:
            return {"alpha": 0.0}
        p = e(min(1.0, t))
        return {"dy": (1 - p) * rise, "alpha": min(1.0, t / fade), "rot": (1 - p) * rot}
    return fx


def stagger_out(start=0, per=1.5, dur=10.0, ease="in_cubic", drop=50.0):
    e = E.get(ease)

    def fx(i, n, f):
        t = (f - start - (n - 1 - i) * per) / dur
        if t <= 0:
            return {}
        p = e(min(1.0, t))
        return {"dy": p * drop, "alpha": 1 - p}
    return fx


def tracking_to(start, dur, amount, ease="snap"):
    """Stretch a word by opening its letter spacing (the honest 'stretch')."""
    e = E.get(ease)

    def fx(i, n, f):
        t = max(0.0, min(1.0, (f - start) / dur))
        return {"track": amount * e(t)}
    return fx


def pop_on_beats(beats, dur=6.0, amount=0.18):
    """Uniform scale pop on given frames (e.g. sync letters to footsteps or music hits)."""
    def fx(i, n, f):
        b = beats[i] if i < len(beats) else None
        if b is None or f < b:
            return {}
        t = (f - b) / dur
        if t > 3:
            return {}
        return {"scale": 1 + amount * math.exp(-2.5 * t) * math.cos(math.pi * t)}
    return fx


def combine(*effects):
    def fx(i, n, f):
        out = {"dx": 0.0, "dy": 0.0, "rot": 0.0, "scale": 1.0, "alpha": 1.0, "track": 0.0}
        for e in effects:
            st = e(i, n, f)
            out["dx"] += st.get("dx", 0.0)
            out["dy"] += st.get("dy", 0.0)
            out["rot"] += st.get("rot", 0.0)
            out["scale"] *= st.get("scale", 1.0)
            out["alpha"] *= st.get("alpha", 1.0)
            out["track"] += st.get("track", 0.0)
        return out
    return fx


def draw_number(cv, x, y, value, decimals=0, size=96, family="DejaVu Sans", weight=700, color="#111111",
                align="right", path=None, sep=",", prefix="", suffix="", alpha=1.0):
    """Counter-friendly number: digits sit in fixed-width cells (tabular), so a count-up doesn't jitter.

    Animate the value (e.g. Channel with 'snap' to the exact final figure) and land on the real number."""
    s = f"{prefix}{value:,.{decimals}f}{suffix}".replace(",", "\x00").replace("\x00", sep)
    cells = [(ch, size * (0.62 if ch.isdigit() else 0.34 if ch in ",.' " else 0.6)) for ch in s]
    total = sum(w for _, w in cells)
    cur = x - (total if align == "right" else total / 2 if align == "center" else 0)
    for ch, w in cells:
        cv.text(ch, cur + w / 2, y, size=size, family=family, weight=weight, color=color, align="center",
                path=path, alpha=alpha)
        cur += w
    return total
