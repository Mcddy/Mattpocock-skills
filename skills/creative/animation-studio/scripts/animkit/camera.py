"""2-D camera with parallax, eased moves, handheld drift and impact shake.

World units are pixels at zoom 1. A layer's `depth` sets parallax: 1.0 moves with
the camera (the action plane), 0.3 is far background, 1.4 is foreground.
Camera moves should be motivated (follow action, reveal, emphasise) and eased;
see references/cinematography.md.
"""
from __future__ import annotations

import math
from contextlib import contextmanager

from .curves import Channel, K
from .principles import smooth_noise


class Camera:
    def __init__(self, w, h, x=None, y=None, zoom=1.0, rot=0.0):
        self.w, self.h = w, h
        self.x = x if isinstance(x, Channel) else Channel([K(0, w / 2 if x is None else x)])
        self.y = y if isinstance(y, Channel) else Channel([K(0, h / 2 if y is None else y)])
        self.zoom = zoom if isinstance(zoom, Channel) else Channel([K(0, zoom)])
        self.rot = rot if isinstance(rot, Channel) else Channel([K(0, rot)])
        self.handheld = 0.0
        self._nx = smooth_noise(11)
        self._ny = smooth_noise(23)
        self._nr = smooth_noise(37)
        self.shakes = []  # (frame, amplitude, decay_frames)

    def shake(self, frame, amplitude=10.0, decay=10.0):
        self.shakes.append((frame, amplitude, decay))
        return self

    def offset(self, f, fps=24.0):
        ox = oy = orot = 0.0
        if self.handheld:
            t = f / fps
            ox += self._nx(t * 0.7) * self.handheld
            oy += self._ny(t * 0.6) * self.handheld * 0.7
            orot += self._nr(t * 0.5) * self.handheld * 0.0008
        for f0, amp, dec in self.shakes:
            d = f - f0
            if 0 <= d < dec * 4:
                env = math.exp(-d / dec)
                ox += amp * env * math.sin(d * 2.1)
                oy += amp * env * math.cos(d * 2.9) * 0.7
        return ox, oy, orot

    @contextmanager
    def view(self, canvas, f, depth=1.0):
        """Draw a layer in world space at the given parallax depth."""
        cx, cy = float(self.x(f)), float(self.y(f))
        z = float(self.zoom(f))
        zd = 1 + (z - 1) * depth          # deeper layers zoom less
        ox, oy, orot = self.offset(f)
        c = canvas.c
        c.save()
        c.translate(self.w / 2 + ox * depth, self.h / 2 + oy * depth)
        rot = float(self.rot(f)) + orot
        if rot:
            c.rotate(math.degrees(rot))
        c.scale(zd, zd)
        c.translate(-(self.w / 2 + (cx - self.w / 2) * depth), -(self.h / 2 + (cy - self.h / 2) * depth))
        try:
            yield canvas
        finally:
            c.restore()

    def to_screen(self, f, wx, wy, depth=1.0):
        cx, cy = float(self.x(f)), float(self.y(f))
        z = 1 + (float(self.zoom(f)) - 1) * depth
        ox, oy, _ = self.offset(f)
        sx = (wx - (self.w / 2 + (cx - self.w / 2) * depth)) * z + self.w / 2 + ox * depth
        sy = (wy - (self.h / 2 + (cy - self.h / 2) * depth)) * z + self.h / 2 + oy * depth
        return sx, sy
