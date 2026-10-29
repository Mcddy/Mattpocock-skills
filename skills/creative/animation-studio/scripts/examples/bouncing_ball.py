#!/usr/bin/env python3
"""The classic first exercise, done properly: a ball bouncing to rest.

Shows: parabolic arcs (in_quad up / out_quad down), decaying bounce heights,
squash on contact and stretch at speed (volume preserved), contact shadow that
shrinks with height, forward travel that slows with each bounce, a moving
hold at rest, and impact sounds placed from the CueSheet with decreasing level.

python3 bouncing_ball.py --out ball.mp4 [--w 1280 --h 720]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from animkit import audio as A                        # noqa: E402
from animkit.canvas import Canvas, vignette           # noqa: E402
from animkit.curves import Channel, K                 # noqa: E402
from animkit.principles import impact_squash, squash_stretch, breathe  # noqa: E402
from animkit.timeline import CueSheet, render, mux    # noqa: E402

FPS = 24
W, H = 1280, 720
FLOOR = 600.0
R = 38.0

# bounce plan: each bounce ~55% of the previous height, shorter air time
heights = [380, 210, 116, 64, 34, 16]
keys_y = [K(0, FLOOR - 420, "in_quad")]
contacts = []
f = 16
for i, h in enumerate(heights):
    keys_y.append(K(f, FLOOR - R, "out_quad"))       # contact: fastest
    contacts.append((f, h))
    air = max(6, int(round(2 * (h / 380) ** 0.5 * 14)))
    keys_y.append(K(f + air / 2, FLOOR - R - h, "in_quad"))  # apex: slowest
    f += air
keys_y.append(K(f, FLOOR - R, "settle"))
contacts.append((f, 6))
REST = f
TAIL = 14                                  # end on the settle, not on a dead hold
y = Channel(keys_y + [K(REST + TAIL, FLOOR - R)])
x = Channel([K(0, 140, "out_sine"), K(REST + TAIL * 0.6, 900, "out_cubic"), K(REST + TAIL, 900)])
N = int(REST + TAIL)

cues = CueSheet(FPS)
for cf, h in contacts:
    cues.add(cf, "impact", strength=min(1.0, h / 380 + 0.05))


def scale_at(fr):
    # squash at the nearest contact; stretch with vertical speed otherwise
    for cf, h in contacts:
        d = fr - cf
        if -0.5 <= d < 5:
            sx, sy = impact_squash(max(0.0, d), amount=0.32 * min(1, h / 200 + 0.2), recover=5)
            return sx, sy
    vy = float(y.velocity(fr))
    along, across = squash_stretch(vy, k=0.0012, max_stretch=0.28)
    return across, along   # stretch vertically


def draw(cv: Canvas, fr: float):
    cv.rect(0, 0, W, H, cv.linear((0, 0), (0, H), ["#1C2430", "#11161E"]))
    cv.rect(0, FLOOR, W, H - FLOOR, "#0D1117")
    cv.line((0, FLOOR), (W, FLOOR), "#2B3646", 2)
    cy = float(y(fr))
    cx = float(x(fr))
    lift = FLOOR - R - cy
    cv.shadow(cx, FLOOR + 3, R * (1.1 - min(0.7, lift / 600)), 7, alpha=0.55 - min(0.4, lift / 900), blur=4)
    sx, sy = scale_at(fr)
    if fr > REST:
        sy *= breathe(fr, FPS, 0.25, 0.008)
        sx = 1 / sy
    with cv.at(cx, cy + R, 0, sx, sy):        # pivot at the contact point
        cv.circle(0, -R, R, cv.radial((-12, -R - 14), R * 1.6, ["#F2B24C", "#C9792A", "#7A3F18"], [0, 0.6, 1]))
        cv.circle(-12, -R - 14, 7, "#FFE2A8", alpha=0.55, blur=3)


def build_audio(path, dur):
    m = A.Mix(dur)
    m.add(A.noise(dur, "brown", 3) * 0.02, 0, -30, bus="amb")
    for k, c in enumerate(cues.cues):
        s = c["strength"]
        m.add(A.thump(seed=k, pitch=1.0 + (1 - s) * 0.5), c["t"], -4 + 20 * np.log10(max(s, 0.05)), 0.0)
    m.process("sfx", lambda s: A.reverb(s, 0.12, 0.6, 0.008))
    return A.master(m.render(), path, target_lufs=-16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mb", type=int, default=3)
    a = ap.parse_args()
    silent = os.path.splitext(a.out)[0] + "_silent.mp4"
    render(draw, N, silent, w=W, h=H, fps=FPS, mb_samples=a.mb, post=lambda im, i: vignette(im, 0.2), log_every=0)
    wav = os.path.splitext(a.out)[0] + ".wav"
    print("loudness", build_audio(wav, N / FPS + 0.3))
    mux(silent, wav, a.out)
    print("wrote", a.out, "frames", N)


if __name__ == "__main__":
    main()
