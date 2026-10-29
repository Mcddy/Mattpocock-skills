#!/usr/bin/env python3
"""HELLO - a ~5-second greeting sting built from the reusable parts (BlobRig, KineticText).

Shows how fast a principled shot comes together from the library:
  * restyled BlobRig (teal coat, daylight) driven by a Performer: walk in with locked
    feet, stop and settle, turn to camera (face slides), eyes lead, blink, wave with
    anticipation, happy eyes
  * kinetic type: each letter of "hello" pops in ON a footstep contact (cue-synced),
    real display font (fetched online, best installed face offline)
  * sound from cues: footsteps, a rising pluck per letter, cloth on the wave, a chime

python3 hello_sting.py --out hello.mp4 [--mb 2] [--review DIR]

Review history (kept as a lesson): the first draft keyed the wave after the clip end,
so sorted keys made the happy eyes fade in during the walk; the character also
entered so late that the first letters popped before it was in shot. Both were caught
by the --review pack before rendering, and Channel now warns on out-of-order keys.
v2.1: reel_critic flagged 46% near-still (an empty first second while the character
was off-screen, and a long static tail). Now the character is in shot from frame 0,
the tail is ~1 s, and the finished word breathes as a moving hold.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from animkit import audio as A                                  # noqa: E402
from animkit import fonts                                       # noqa: E402
from animkit.camera import Camera                               # noqa: E402
from animkit.canvas import Canvas, dither, vignette              # noqa: E402
from animkit.curves import Channel, K                           # noqa: E402
from animkit.rigs import BlobRig, Light, Performer, RigStyle    # noqa: E402
from animkit.timeline import CueSheet, mux, render              # noqa: E402
from animkit.typeanim import KineticText, pop_on_beats, stagger_in  # noqa: E402
from animkit.walk import Walk                                   # noqa: E402

W, H, FPS = 1920, 1080, 24
GROUND = 860.0

rig = BlobRig(RigStyle(coat="#3FA7A0", coat_shade="#2B7C77", coat_hi="#8FDCD3", bag_col="#D9A23A",
                       strap_col="#9C6A1E", limb_far="#3A3F4C", limb_near="#4A5060"))
# x0=230: the character is already entering at the left edge on frame 0 (no empty opening)
walk = Walk(x0=230, x1=860, ground=GROUND, stride=84, step_frames=7, start=2, hip_height=74, bob=5, lift=13,
            stance_gap=7, lean=0.07)
A_ = walk.t_stop
N = int(A_ + 70)                                           # wave, then a ~1 s moving hold; end on the settle
B = dict(arrive=A_, turn=A_ + 4, look=A_ + 10, wave=A_ + 22, wave_end=A_ + 46, end=N)
perf = Performer(rig, [walk], range(0, N), blinks=[B["turn"] + 2, B["wave_end"] + 4], channels=dict(
    facing=Channel([K(0, 1.0), K(B["turn"], 1.0, "anticipate"), K(B["turn"] + 8, 0.0), K(N, 0.0)]),
    gaze_x=Channel([K(0, 1.0), K(B["turn"] - 2, 1.0, "snap"), K(B["turn"] + 2, 0.0), K(N, 0.0)]),
    gaze_y=Channel([K(0, 0.1), K(B["look"] - 3, 0.1, "snap"), K(B["look"] + 2, -0.35), K(N, -0.35)]),
    body_dy=Channel([K(0, 0.0), K(B["wave"] - 4, 0.0, "snap"), K(B["wave"], 6.0, "snap"), K(B["wave"] + 6, -4.0, "settle"),
                     K(B["wave"] + 16, 0.0), K(N, 0.0)]),
    squash=Channel([K(0, 1.0), K(B["wave"] - 4, 1.0, "snap"), K(B["wave"], 0.9, "snap"), K(B["wave"] + 6, 1.06, "settle"),
                    K(B["wave"] + 16, 1.0), K(N, 1.0)]),
    lean=Channel([K(0, 0.0), K(B["arrive"], 0.0, "settle"), K(B["arrive"] + 8, -0.05), K(N, -0.04)]),
    happy=Channel([K(0, 0.0), K(B["wave"], 0.0, "slow_in_out"), K(B["wave"] + 8, 1.0), K(N, 1.0)]),
    near_hand=Channel([K(0, (2.0, 44.0)), K(B["wave"] - 4, (2.0, 44.0), "anticipate"), K(B["wave"] + 4, (24.0, -56.0)),
                       K(B["wave_end"], (24.0, -56.0), "slow_in_out"), K(B["wave_end"] + 10, (2.0, 44.0)), K(N, (2.0, 44.0))]),
))
PUSH = (B["arrive"] - 6, B["wave"] + 6)                    # push to a medium for the hello (the thought beat)
cam = Camera(W, H, x=Channel([K(0, 860.0), K(N, 860.0)]),
             y=Channel([K(0, 640.0), K(PUSH[0], 640.0, "slow_in_out"), K(PUSH[1], 614.0), K(N, 612.0)]),
             zoom=Channel([K(0, 1.4), K(PUSH[0], 1.4, "slow_in_out"), K(PUSH[1], 1.75, "slow_in_out"), K(N, 1.8)]))
cam.handheld = 1.5

steps = [c for c in walk.contacts]
letter_beats = [t for t, _, _ in steps[-6:-1]]            # one letter per footstep as the character approaches
font_path = fonts.fetch("Fraunces", 700) or None
word = KineticText("hello", size=150, family="Fraunces" if font_path else (fonts.best_available("display") or "DejaVu Sans"),
                   weight=700, path=font_path)


def letter_fx(i, n, f):
    b = letter_beats[i]
    if f < b - 1:
        return {"alpha": 0.0}
    st = stagger_in(start=b - 1, per=0, dur=10, ease="settle", rise=-70, fade=0.15)(0, 1, f)
    pop = pop_on_beats([b], dur=6, amount=0.22)(0, 1, f)
    st["scale"] = pop.get("scale", 1.0)
    # moving hold: once the word is complete, the letters breathe in a slow offset wave
    t0 = letter_beats[-1] + 10
    if f > t0:
        k = min(1.0, (f - t0) / 12.0)
        st["dy"] = st.get("dy", 0.0) + k * 5.0 * math.sin(2 * math.pi * (f - t0) / 40.0 + i * 0.9)
    return st


cues = CueSheet(FPS)
for t, foot, x in steps:
    cues.add(t, "step")
for i, b in enumerate(letter_beats):
    cues.add(b, "letter", i=i)
cues.add(B["wave"], "cloth").add(B["wave"] + 8, "chime")

LIGHT = Light(ambient=(1.0, 0.98, 0.95), key_col="#FFE2B0", key=0.28, key_dir=1.0)


def draw(cv: Canvas, f: float):
    cv.rect(0, 0, W, H, cv.linear((0, 0), (0, H), ["#F1E7D7", "#E4D6C1"]))
    with cam.view(cv, f, 0.6):
        cv.ellipse(980, 560, 900, 360, "#FFF6E8", alpha=0.55, blur=60)          # soft light pool on the wall
    with cam.view(cv, f, 1.0):
        cv.rect(-600, GROUND, 3200, 600, cv.linear((0, GROUND), (0, GROUND + 300), ["#D8C7AE", "#CDB99D"]))
        cv.line((-600, GROUND), (2600, GROUND), "#BFA889", 2)
        word.draw(cv, 860, 500, f, letter_fx, color="#2B3A42", align="center")
        p = perf.pose(f)
        rig.draw(cv, p, LIGHT, ground=GROUND)


def post(img, i):
    return dither(vignette(img, 0.12))


def build_audio(path):
    dur = N / FPS + 0.6
    m = A.Mix(dur)
    m.add(A.filt(A.noise(dur, "brown", 2), "lp", 250) * 0.2, 0, -32, bus="amb")
    notes = ["C5", "D5", "E5", "G5", "A5"]
    for k, c in enumerate(cues.cues):
        t = c["t"]
        if c["kind"] == "step":
            m.add(A.footstep(seed=k, wet=0.0, weight=0.7, surface="wood"), t, -10, -0.2)
        elif c["kind"] == "letter":
            m.add(A.karplus(A.hz(notes[c["i"]]), 0.9, seed=k, bright=0.6) * 0.8, t, -12, (c["i"] - 2) * 0.25,
                  bus="music")
        elif c["kind"] == "cloth":
            m.add(A.cloth(0.4, seed=k, level=0.6), t, -14, 0.1)
        elif c["kind"] == "chime":
            for j, nn in enumerate(("C6", "E6", "G6")):
                m.add(A.keys_note(A.hz(nn), 1.6, 0.4), t + j * 0.06, -16, 0.2, bus="music")
    m.process("music", lambda s: A.reverb(s, 0.22, 1.4, 0.015))
    return A.master(m.render(), path, target_lufs=-16.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mb", type=int, default=2)
    ap.add_argument("--review", default=None)
    a = ap.parse_args()
    if a.review:
        from animkit import review as R
        print(R.beat_stills(draw, {"mid_walk": 30, **{k: v for k, v in B.items() if k != "end"}}, a.review, W, H, post=post))
        loc = lambda f: cam.to_screen(f, perf.pose(f).hip[0], perf.pose(f).hip[1] - 60)  # noqa: E731
        print(R.subject_strip(draw, [float(f) for f in range(int(B["turn"]) - 2, int(B["wave"]) + 20, 2)], loc,
                              os.path.join(a.review, "strip_turn_wave.png"), W, H, post=post))
        bad = R.framing_report(cam, [float(f) for f in range(0, N, 3)], lambda f: rig.bbox(perf.pose(f), GROUND), W, H,
                               margin=0.03, exits_ok=[(0, 14)])
        print("framing violations:", len(bad))
        print("foot slide px:", walk.foot_slide_report())
        return
    silent = os.path.splitext(a.out)[0] + "_silent.mp4"
    print(render(draw, N, silent, w=W, h=H, fps=FPS, mb_samples=a.mb, post=post))
    wav = os.path.splitext(a.out)[0] + ".wav"
    print("loudness", build_audio(wav))
    cues.save(os.path.splitext(a.out)[0] + "_cues.json")
    mux(silent, wav, a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
