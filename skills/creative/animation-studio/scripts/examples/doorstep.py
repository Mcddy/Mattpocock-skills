#!/usr/bin/env python3
"""DOORSTEP - reference shot for the animation-studio skill.

A courier in a yellow raincoat makes the last delivery of the night, gets no
answer, turns to leave, and the upstairs light clicks on.

It exists to prove the toolkit end to end and to show the craft rules in code:
  * acting beats with a goal, an obstacle and a turn (references/acting-and-story.md)
  * walk with locked foot plants, stop with overshoot, eyes lead the head
  * anticipation / squash & stretch / follow-through on hood tip and satchel
  * motivated camera: follow with lag, settle, late push-in on the payoff
  * colour script: cool night, one warm event; light that actually lights the
    character (src_atop key), wet-ground reflections, textured rain
  * sound placed from the CueSheet: every contact, flap, click and landing
  * score in sections that follow the beats, mastered to -14 LUFS

Run:  python3 doorstep.py --out /path/doorstep.mp4 [--preview] [--mb 3]
"""
from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from animkit import audio as A                      # noqa: E402
from animkit import easing as E                     # noqa: E402
from animkit.camera import Camera                   # noqa: E402
from animkit.canvas import Canvas, mix, rgba, vignette, dither   # noqa: E402
from animkit.curves import Channel, K               # noqa: E402
from animkit.principles import (baked, blink, breathe, lag_chain, simulate_positional,  # noqa: E402
                                two_bone_ik, smooth_noise)
from animkit.timeline import CueSheet, mux, render  # noqa: E402
from animkit.walk import Walk                       # noqa: E402

W, H, FPS = 1920, 1080, 24
GROUND = 880.0

# ------------------------------------------------------------------ colour script
P = {
    "sky_top": "#060A13", "sky_low": "#17263B", "far": "#0A101B", "far_win": "#C99654",
    "mid": "#101826", "mid2": "#131C2B", "mid_win": "#0B111B",
    "wall": "#2A374E", "brick": "#222D43", "trim": "#151D2B",
    "door": "#5B2B2B", "door_dark": "#3F1E1F", "brass": "#A88442", "brass_hi": "#E2C27A",
    "glass": "#0F1724", "lit": "#FFD38A", "lit_edge": "#F0A54C", "curtain": "#E7B46E",
    "pave": "#131B27", "kerb": "#1D2737", "road": "#0C121B",
    "coat": "#E2A63A", "coat_shade": "#B47A22", "coat_hi": "#F6CB6B", "face": "#18202E",
    "boot": "#232834", "satchel": "#7A3A2C", "strap": "#5A2A22", "letter": "#F3E8D2", "stamp": "#C9453B",
    "eye": "#F4F1EA", "pupil": "#0D1119", "rain": "#A8C0D8", "lamp": "#BFE0EE",
}

# ------------------------------------------------------------------ beats (frames @24)
B = dict(
    walk_start=4, arrive=None,          # arrive filled by the walk solver
    look_up=0, reach=0, letter_out=0, to_slot=0, push=0, flap_shut=0,
    wait=0, blink1=0, look_up2=0, sag=0, turn_away=0, click=0, take=0,
    turn_back=0, hop=0, land=0, wave=0, wave_end=0, exit_walk=0, end=0,
)

walk_in = Walk(x0=150, x1=1030, ground=GROUND, stride=84, step_frames=8, start=B["walk_start"],
               hip_height=74, bob=5, lift=13, stance_gap=7, lean=0.07)
B["arrive"] = walk_in.t_stop
a = B["arrive"]
B.update(look_up=a + 10, reach=a + 34, letter_out=a + 46, to_slot=a + 52, push=a + 66, flap_shut=a + 76,
         wait=a + 80, blink1=a + 92, look_up2=a + 100, sag=a + 116, turn_away=a + 128, click=a + 140,
         take=a + 142, turn_back=a + 154, hop=a + 170, land=a + 184, wave=a + 196, wave_end=a + 232,
         exit_walk=a + 238)
walk_out = Walk(x0=1030, x1=2250, ground=GROUND, stride=84, step_frames=8, start=B["exit_walk"],
                hip_height=74, bob=5, lift=13, stance_gap=7, lean=0.07, start_feet=walk_in.final_feet())
B["end"] = int(B["exit_walk"] + 120)
N_FRAMES = B["end"]

DOOR_X0, DOOR_X1, DOOR_TOP = 1090.0, 1236.0, 596.0
SLOT = (1124.0, 1202.0, 752.0)            # x0, x1, y
WIN = (1100.0, 1226.0, 318.0, 470.0)      # x0, x1, y0, y1
LAMP_X = 520.0

cues = CueSheet(FPS)

# ------------------------------------------------------------------ acting channels
# Facing: +1 right, -1 left; values between slide the face across the body (2-D turn).
facing = Channel([K(0, 1.0), K(B["turn_away"], 1.0, "anticipate"), K(B["turn_away"] + 9, -1.0, hold=0),
                  K(B["take"] + 6, -1.0, "snap"), K(B["turn_back"] + 2, 1.0), K(1e6, 1.0)])
# vertical body offset in px, +down (dips, crouches); negative is up (the hop). squash: sy, sx = 1/sy
body_dy = Channel([
    K(0, 0.0), K(B["reach"], 0.0, "in_out_sine"), K(B["reach"] + 8, 7.0, "slow_in_out"),
    K(B["letter_out"] + 4, 0.0), K(B["sag"], 0.0, "heavy"), K(B["sag"] + 10, 6.0, hold=8),
    K(B["turn_away"] + 10, 0.0), K(B["take"], 0.0, "snap"), K(B["take"] + 5, 9.0, "snap"),
    K(B["take"] + 10, -10.0, "settle"), K(B["take"] + 22, 0.0),
    K(B["hop"], 0.0, "snap"), K(B["hop"] + 6, 12.0, "out_quad"),            # anticipation crouch
    K(B["hop"] + 9, -46.0, "out_quad"), K(B["hop"] + 13, -58.0, "in_quad"),  # rise, apex
    K(B["land"], 0.0, "snap"), K(B["land"] + 3, 10.0, "settle"), K(B["land"] + 14, 0.0),
    K(1e6, 0.0)])
squash = Channel([
    K(0, 1.0), K(B["take"], 1.0, "snap"), K(B["take"] + 5, 0.86, "snap"), K(B["take"] + 10, 1.13, "settle"),
    K(B["take"] + 22, 1.0), K(B["hop"], 1.0, "snap"), K(B["hop"] + 6, 0.82, "snap"),
    K(B["hop"] + 9, 1.16, "out_quad"), K(B["hop"] + 13, 1.04, "in_quad"), K(B["land"] - 1, 1.12, "snap"),
    K(B["land"] + 2, 0.8, "settle"), K(B["land"] + 14, 1.0), K(1e6, 1.0)])
lean_ch = Channel([
    K(0, 0.0), K(B["look_up"], 0.0, "slow_in_out"), K(B["look_up"] + 10, -0.10, hold=12),
    K(B["reach"], -0.02, "slow_in_out"), K(B["reach"] + 8, -0.16), K(B["letter_out"] + 2, 0.02, "slow_in_out"),
    K(B["push"], 0.12, "snap"), K(B["push"] + 6, 0.16, "settle"), K(B["flap_shut"] + 4, 0.0),
    K(B["look_up2"], 0.0, "slow_in_out"), K(B["look_up2"] + 10, -0.12, hold=4),
    K(B["sag"], -0.06, "heavy"), K(B["sag"] + 10, 0.10, hold=10), K(B["turn_away"] + 8, 0.0),
    K(B["take"], 0.0, "snap"), K(B["take"] + 8, -0.14, "settle"), K(B["take"] + 16, -0.08),
    K(B["turn_back"] + 6, -0.12, hold=6), K(B["hop"], -0.04), K(B["wave"], -0.06, "slow_in_out"),
    K(B["wave_end"], -0.06, "slow_in_out"), K(B["exit_walk"], 0.0), K(1e6, 0.0)])
# look: eyes lead (gaze), head follows; -1 up, 0 level, +1 down
gaze_y = Channel([K(0, 0.1), K(B["look_up"] - 3, 0.1, "snap"), K(B["look_up"] + 3, -1.0, hold=14),
                  K(B["reach"] - 2, 0.2, "snap"), K(B["reach"] + 4, 0.9), K(B["letter_out"] + 4, 0.3, "slow_in_out"),
                  K(B["push"], 0.4), K(B["wait"], 0.2, "slow_in_out"), K(B["look_up2"] - 2, 0.2, "snap"),
                  K(B["look_up2"] + 3, -1.0, hold=8), K(B["sag"], 0.5, "heavy"), K(B["sag"] + 12, 0.8, hold=6),
                  K(B["turn_away"] + 6, 0.2), K(B["click"], 0.2, "snap"), K(B["take"] + 4, -1.0, hold=8),
                  K(B["hop"], -0.6), K(B["wave"], -0.9, hold=24), K(B["exit_walk"], 0.0), K(1e6, 0.0)])
gaze_x = Channel([K(0, 1.0), K(B["look_up"], 1.0), K(B["look_up"] + 4, 0.5), K(B["reach"] - 2, 0.5, "snap"),
                  K(B["reach"] + 4, 0.1), K(B["letter_out"] + 4, 0.8), K(B["wait"], 0.6),
                  K(B["click"] - 1, -1.0), K(B["take"] + 2, -0.2, "snap"), K(B["turn_back"] + 4, 0.6),
                  K(1e6, 0.8)])
happy = Channel([K(0, 0.0), K(B["take"] + 8, 0.0, "slow_in_out"), K(B["take"] + 16, 1.0, hold=60),
                 K(B["exit_walk"] + 30, 0.4), K(1e6, 0.4)])
eye_open = Channel([K(0, 1.0), K(B["sag"], 1.0, "heavy"), K(B["sag"] + 10, 0.62, hold=14),
                    K(B["click"], 0.7, "snap"), K(B["take"] + 4, 1.22, "settle"), K(B["take"] + 16, 1.05),
                    K(1e6, 1.05)])
blinks = [a - 40, B["blink1"], B["sag"] + 22, B["take"] + 26, B["wave_end"] - 6, B["exit_walk"] + 40]


def root_x(f):
    if f < B["exit_walk"]:
        return walk_in.pose(f)["hip"][0]
    return walk_out.pose(f)["hip"][0]


def walk_pose(f):
    return walk_in.pose(f) if f < B["exit_walk"] else walk_out.pose(f)


# arm targets (offsets from shoulder, in facing-right space; y down)
near_hand = Channel([
    K(0, (2.0, 44.0)), K(B["reach"], (2.0, 44.0), "slow_in_out"), K(B["reach"] + 8, (-20.0, 38.0), hold=6),
    K(B["letter_out"], (-18.0, 36.0), "out_back"), K(B["to_slot"], (16.0, -6.0), "slow_in_out"),
    K(B["push"] - 6, (34.0, -10.0), "anticipate"), K(B["push"] + 4, (57.0, -12.0), "settle"),
    K(B["flap_shut"] + 2, (52.0, -8.0), "slow_in_out"), K(B["wait"] + 6, (2.0, 44.0)),
    K(B["wave"], (2.0, 44.0), "anticipate"), K(B["wave"] + 7, (22.0, -56.0), hold=0),
    K(B["wave_end"] - 4, (22.0, -56.0), "slow_in_out"), K(B["wave_end"] + 6, (2.0, 44.0)),
    K(1e6, (2.0, 44.0))])
far_hand = Channel([K(0, (-6.0, 44.0)), K(B["take"], (-6.0, 44.0), "snap"), K(B["take"] + 8, (-22.0, 20.0), hold=6),
                    K(B["turn_back"] + 8, (-6.0, 44.0)), K(1e6, (-6.0, 44.0))])
letter_state = [(0, "bag"), (B["letter_out"], "hand"), (B["push"] - 2, "slot"), (B["flap_shut"], "gone")]


def state_at(f, table):
    s = table[0][1]
    for t, v in table:
        if f >= t:
            s = v
    return s


flap = Channel([K(0, 0.0), K(B["push"] - 3, 0.0, "snap"), K(B["push"] + 2, 0.95, hold=6),
                K(B["flap_shut"] - 2, 0.95, "in_cubic"), K(B["flap_shut"], 0.0, "settle"),
                K(B["flap_shut"] + 8, 0.0), K(1e6, 0.0)])
light = Channel([K(0, 0.0), K(B["click"], 0.0, "snap"), K(B["click"] + 1, 0.85), K(B["click"] + 2, 0.35),
                 K(B["click"] + 4, 1.0, "out_quad"), K(B["click"] + 10, 1.0), K(1e6, 1.0)])
curtain = Channel([K(0, 0.0), K(B["take"] + 14, 0.0, "slow_in_out"), K(B["take"] + 30, 1.0, hold=70),
                   K(B["wave_end"] + 30, 0.55), K(1e6, 0.55)])
silhouette_wave = Channel([K(0, 0.0), K(B["wave"] + 10, 0.0, "slow_in_out"), K(B["wave"] + 18, 1.0, hold=16),
                           K(B["wave_end"], 0.0), K(1e6, 0.0)])

# camera: follows with lag, settles on the door, pushes in on the payoff
cam = Camera(W, H,
             x=Channel([K(0, 700.0, "slow_in_out"), K(B["arrive"] + 8, 1130.0),
                        K(B["click"], 1130.0, "slow_in_out"), K(B["wave_end"], 1150.0),
                        K(B["exit_walk"] + 10, 1150.0, "slow_in_out"), K(N_FRAMES, 1168.0)]),
             y=Channel([K(0, 560.0, "slow_in_out"), K(B["arrive"] + 8, 618.0),
                        K(B["click"], 618.0, "slow_in_out"), K(B["wave_end"], 596.0),
                        K(B["exit_walk"] + 10, 596.0, "slow_in_out"), K(N_FRAMES, 560.0)]),
             zoom=Channel([K(0, 1.0), K(30, 1.0, "slow_in_out"), K(B["arrive"] + 8, 1.6),
                           K(B["click"], 1.6, "slow_in_out"), K(B["wave_end"], 1.7),
                           K(B["exit_walk"] + 10, 1.7, "slow_in_out"), K(N_FRAMES, 1.82)]))
cam.handheld = 2.2

# ------------------------------------------------------------------ simulated secondary motion
GRID = np.arange(-30, N_FRAMES + 2, 0.25)


def body_anchor(f):
    wp = walk_pose(f)
    return np.array([root_x(f), wp["hip"][1] + body_dy(f) + 0.0])


_hood = lag_chain(lambda f: lean_ch(f) + walk_pose(f)["tilt"] - 0.012 * body_dy(f) * 0, GRID, n=3,
                  stiffness=(150, 110, 80), damping=0.22, gain=1.4)
hood_ang = baked({k: v for k, v in _hood.items()})
_hood_v = simulate_positional(lambda f: (root_x(f), body_dy(f) * 1.0), GRID, stiffness=120, damping=0.25)
hood_off = baked(_hood_v)
_bag = simulate_positional(lambda f: (root_x(f), walk_pose(f)["hip"][1] + body_dy(f)), GRID,
                           stiffness=95, damping=0.2, gravity=(0, 0))
bag_off = baked(_bag)
noise_sway = smooth_noise(5)

# ------------------------------------------------------------------ cues from animation
for t, foot, x in walk_in.contacts:
    cues.add(t, "step", foot=foot, x=x)
for t, foot, x in walk_out.contacts:
    cues.add(t, "step", foot=foot, x=x)
cues.add(B["reach"] + 2, "cloth").add(B["letter_out"] - 6, "paper").add(B["push"] - 1, "paper_slide")
cues.add(B["push"] - 1, "flap_open").add(B["flap_shut"], "flap_shut").add(B["sag"], "cloth")
cues.add(B["turn_away"] + 2, "cloth").add(B["click"], "switch").add(B["take"] + 1, "cloth")
cues.add(B["hop"] + 7, "whoosh").add(B["land"], "land").add(B["wave"] + 2, "cloth")


# ------------------------------------------------------------------ environment
rng = np.random.default_rng(42)
BRICKS = [(x, y, rng.uniform(-0.05, 0.05)) for y in range(200, 880, 26) for x in range(-40, 2600, 64)]
FAR_WINS = [(rng.uniform(-300, 2900), rng.uniform(250, 560), rng.random() < 0.18) for _ in range(40)]
DROPS = [(rng.uniform(-400, 2800), rng.uniform(0, 1400), rng.uniform(26, 40), rng.uniform(0.6, 1.0)) for _ in range(900)]
SPLASH = [(rng.uniform(-200, 2700), rng.uniform(0, 1000), rng.uniform(0.6, 1.0)) for _ in range(260)]
RIPPLE = [(rng.uniform(1260, 1560), rng.uniform(904, 934), rng.uniform(0, 1000)) for _ in range(26)]


def draw_sky_and_far(cv, f):
    cv.rect(0, 0, W, H, cv.linear((0, 0), (0, 760), [P["sky_top"], P["sky_low"]]))
    with cam.view(cv, f, depth=0.35):
        # distant roofline
        pts = [(-600, 620)]
        x = -600
        k = 0
        while x < 3200:
            h = 380 + 60 * math.sin(k * 1.7) + 40 * math.sin(k * 0.6)
            pts += [(x, h), (x + 140, h)]
            x += 140 + 30 * (k % 3)
            k += 1
        pts += [(3200, 900), (-600, 900)]
        cv.poly(pts, P["far"])
        for wx, wy, lit in FAR_WINS:
            if lit:
                cv.rect(wx, wy, 18, 24, P["far_win"], alpha=0.55)
                cv.light(wx + 9, wy + 12, 60, P["far_win"], 0.12)
            else:
                cv.rect(wx, wy, 18, 24, "#0E1520")
        cv.rect(-600, 640, 3800, 300, cv.linear((0, 560), (0, 760), ["#1E304600", "#24384F"]))  # haze


def draw_mid(cv, f):
    with cam.view(cv, f, depth=0.7):
        for i, (x0, w, top, col) in enumerate([(-300, 520, 300, P["mid"]), (240, 420, 250, P["mid2"]),
                                                (1580, 560, 280, P["mid"]), (2160, 600, 230, P["mid2"])]):
            cv.rect(x0, top, w, 900 - top, col)
            for r in range(3):
                for c in range(3):
                    cv.rect(x0 + 50 + c * (w - 100) / 3, top + 60 + r * 160, 56, 84, P["mid_win"])


def draw_house(cv, f, li):
    # left neighbour + target house + right neighbour on the action plane
    cv.rect(-400, 200, 1300, 680, "#1A2334")
    cv.rect(900, 150, 520, 730, P["wall"])
    cv.rect(1420, 210, 900, 670, "#172030")
    for x0 in (180, 640, 1560, 1900):     # neighbours' dark windows
        cv.rect(x0, 330, 110, 150, P["trim"])
        cv.rect(x0 + 8, 338, 94, 134, "#0C121C")
    # brick texture: low-contrast courses, slight per-brick variation (not a grid of outlines)
    for x, y, v in BRICKS:
        if 900 <= x < 1420 and y > 150:
            off = 32 if (y // 26) % 2 else 0
            cv.rect(x + off, y, 60, 22, mix(P["brick"], P["wall"], 0.5 + v * 4), alpha=0.55)
    cv.rect(890, 140, 540, 16, P["trim"])
    # upstairs window
    x0, x1, y0, y1 = WIN
    cv.rect(x0 - 12, y0 - 12, x1 - x0 + 24, y1 - y0 + 30, P["trim"])
    glass = cv.linear((x0, y0), (x0, y1), [mix(P["glass"], P["lit"], li), mix(P["glass"], P["lit_edge"], li)])
    cv.rect(x0, y0, x1 - x0, y1 - y0, glass)
    if li > 0:
        # curtain + someone inside
        c = curtain(f)
        cw = (x1 - x0) / 2 * (1 - 0.55 * c)
        cv.rect(x0, y0, cw, y1 - y0, mix(P["glass"], P["curtain"], li * 0.9))
        cv.rect(x1 - cw, y0, cw, y1 - y0, mix(P["glass"], P["curtain"], li * 0.9))
        sw = silhouette_wave(f)
        if c > 0.3:
            sx = x0 + (x1 - x0) * 0.5
            al = min(1, (c - 0.3) * 2.5) * li
            cv.ellipse(sx, y1 - 70, 20, 24, "#5A3A2A", alpha=0.75 * al)
            cv.rect(sx - 30, y1 - 48, 60, 50, "#5A3A2A", r=18, alpha=0.75 * al)
            if sw > 0:
                ang = -0.6 - 0.35 * math.sin((f - B["wave"]) * 0.55)
                hx, hy = sx + 26, y1 - 40
                ex, ey = hx + 34 * math.cos(ang) * sw, hy + 34 * math.sin(ang) * sw
                cv.line((hx, hy), (ex, ey), "#5A3A2A", 12, alpha=0.75 * al)
                cv.circle(ex, ey, 8, "#5A3A2A", alpha=0.75 * al)
    cv.line((x0 + (x1 - x0) / 2, y0), (x0 + (x1 - x0) / 2, y1), P["trim"], 6)
    cv.line((x0, y0 + (y1 - y0) * 0.45), (x1, y0 + (y1 - y0) * 0.45), P["trim"], 6)
    cv.rect(x0 - 18, y1 + 10, x1 - x0 + 36, 10, "#3A4760")   # sill
    # door
    cv.rect(DOOR_X0 - 14, DOOR_TOP - 14, DOOR_X1 - DOOR_X0 + 28, GROUND - DOOR_TOP + 6, P["trim"])
    cv.rect(DOOR_X0, DOOR_TOP, DOOR_X1 - DOOR_X0, GROUND - DOOR_TOP - 8, P["door"])
    for (px, py, pw, ph) in [(14, 20, 50, 110), (82, 20, 50, 110), (14, 190, 50, 50), (82, 190, 50, 50)]:
        cv.rect(DOOR_X0 + px, DOOR_TOP + py, pw, ph, P["door_dark"], r=4, alpha=0.7)
    cv.circle(DOOR_X1 - 18, 742, 6, P["brass"])
    # letterbox with hinged flap
    sx0, sx1, sy = SLOT
    cv.rect(sx0 - 8, sy - 16, sx1 - sx0 + 16, 32, P["brass"], r=3)
    cv.rect(sx0, sy - 6, sx1 - sx0, 12, "#0B0F16")
    fo = flap(f)
    cv.rect(sx0, sy - 6 - 10 * fo, sx1 - sx0, 12 * (1 - fo) + 2, mix(P["brass"], P["brass_hi"], 0.25 + 0.4 * fo))
    cv.rect(DOOR_X0 - 20, GROUND - 12, DOOR_X1 - DOOR_X0 + 40, 14, "#3A4760")  # step
    # street lamp (action plane, left)
    cv.rect(LAMP_X - 7, 380, 14, GROUND - 380, "#151C28")
    cv.poly([(LAMP_X - 28, 380), (LAMP_X + 28, 380), (LAMP_X + 16, 352), (LAMP_X - 16, 352)], "#151C28")
    cv.ellipse(LAMP_X, 384, 20, 6, P["lamp"])
    # pavement, kerb, road
    cv.rect(-400, GROUND, 3000, 70, P["pave"])
    cv.rect(-400, GROUND + 70, 3000, 10, P["kerb"])
    cv.rect(-400, GROUND + 80, 3000, 400, P["road"])
    # puddle
    cv.ellipse(1410, 918, 170, 20, "#18212E")


def draw_lights(cv, f, li):
    """Additive light pass on the action plane (after characters, before rain)."""
    cv.cone((LAMP_X, 390), (LAMP_X - 170, GROUND + 4), (LAMP_X + 170, GROUND + 4), P["lamp"], 0.22, soften=24)
    cv.light(LAMP_X, 386, 120, P["lamp"], 0.55)
    cv.light(LAMP_X, 520, 460, P["lamp"], 0.10)
    cv.ellipse(LAMP_X, GROUND + 6, 170, 16, P["lamp"], alpha=0.14, blend="plus", blur=10)
    if li > 0:
        x0, x1, y0, y1 = WIN
        cv.cone(((x0 + x1) / 2, y1 - 20), (x0 - 210, GROUND + 6), (x1 + 230, GROUND + 6), P["lit"], 0.20 * li, soften=36)
        cv.light((x0 + x1) / 2, (y0 + y1) / 2, 330, P["lit"], 0.38 * li)
        cv.ellipse((x0 + x1) / 2 + 10, GROUND + 8, 300, 22, P["lit"], alpha=0.16 * li, blend="plus", blur=14)


def draw_reflections(cv, f, li):
    """Wet pavement: vertical smears of bright sources below the ground line."""
    with cv.clip_rect(-400, GROUND, 3000, 400):
        cv.rect(LAMP_X - 12, GROUND + 4, 24, 150, cv.linear((0, GROUND), (0, GROUND + 150), [P["lamp"] + "55", P["lamp"] + "00"]), blend="plus", blur=6)
        if li > 0:
            x0, x1, _, _ = WIN
            cv.rect(x0 + 10, GROUND + 6, x1 - x0 - 20, 190,
                    cv.linear((0, GROUND), (0, GROUND + 190), [P["lit"] + "66", P["lit"] + "00"]), alpha=li,
                    blend="plus", blur=10)
        # puddle mirror is sharper
        with cv.clip_rect(1240, 898, 340, 40):
            if li > 0:
                cv.ellipse(1300, 918, 70, 14, P["lit"], alpha=0.30 * li, blend="plus", blur=6)
            for rx, ry, ph in RIPPLE:
                age = ((f * 0.9 + ph) % 22) / 22
                cv.ellipse(rx, ry, 4 + 26 * age, 1.2 + 4 * age, None, stroke=P["rain"], sw=1.2,
                           alpha=0.45 * (1 - age))


def draw_rain(cv, f, depth, alpha, width, length_k, density_skip, blur=0.0):
    with cam.view(cv, f, depth=depth):
        for i, (x, y0, v, s) in enumerate(DROPS):
            if i % density_skip:
                continue
            y = (y0 + f * v * depth) % 1400 - 200
            xx = x + y * 0.12
            ln = length_k * v * depth
            cv.line((xx, y), (xx + ln * 0.12, y + ln), P["rain"], width * s, alpha=alpha * s, blur=blur)


def draw_splashes(cv, f):
    for x, ph, s in SPLASH:
        age = ((f + ph) % 9) / 9
        if age < 0.6:
            u = age / 0.6
            y = GROUND + 2 + (s - 0.6) * 60
            cv.ellipse(x, y, 3 + 9 * u, 1 + 2 * u, None, stroke=P["rain"], sw=1.1, alpha=0.5 * (1 - u) * s)
            cv.line((x - 2, y - 2), (x - 5 - 4 * u, y - 4 - 6 * u * (1 - u) * 4), P["rain"], 1.0, alpha=0.4 * (1 - u))
            cv.line((x + 2, y - 2), (x + 5 + 4 * u, y - 4 - 6 * u * (1 - u) * 4), P["rain"], 1.0, alpha=0.4 * (1 - u))


# ------------------------------------------------------------------ the character
BODY_RX, BODY_RY = 52.0, 66.0
THIGH, SHIN = 42.0, 42.0
UPPER, FORE = 30.0, 30.0
AMB = np.array([0.64, 0.66, 0.86])       # night ambient (cool, dim)
WARM = np.array([0.24, 0.16, 0.05])      # window spill once the light is on
LAMPC = np.array([0.30, 0.42, 0.52])     # cool street lamp when passing under it


def lit(col, li, lamp_k=0.0, extra=0.0):
    """Colour under the scene's lights: base albedo x (ambient + warm spill + lamp)."""
    c = rgba(col)
    m = AMB + li * WARM + lamp_k * LAMPC + extra
    return (min(1, c.fR * m[0]), min(1, c.fG * m[1]), min(1, c.fB * m[2]), c.fA)


def character(cv, f, li, reflect=False):
    wp = walk_pose(f)
    fx = facing(f)
    fs = 1.0 if fx >= 0 else -1.0
    sy = squash(f) * breathe(f, FPS, 0.3, 0.012)
    sx = 1.0 / sy
    hip = np.array([root_x(f), wp["hip"][1] + body_dy(f)])
    lean = lean_ch(f) + wp["tilt"] * 0.8
    lamp_k = max(0.0, 1 - abs(hip[0] - LAMP_X) / 240) ** 1.5
    L = lambda col, extra=0.0: lit(col, li, lamp_k, extra)  # noqa: E731
    feet = wp["feet"]
    legs = []
    for name, side in (("far", -1), ("near", 1)):
        (fp, fa, swing) = feet[name]
        foot = np.array(fp, float)
        if body_dy(f) < -2:              # airborne during the hop: tuck the feet
            foot = np.array([hip[0] + side * 8 * fs, hip[1] + THIGH + SHIN - 18])
        root = hip + np.array([side * 9 * fs, 0])
        knee, end = two_bone_ik(root, foot, THIGH, SHIN, bend_dir=-fs)
        legs.append((name, root, knee, end, fa, swing))
    c_off = np.array([math.sin(lean) * 56, -math.cos(lean) * 56 * sy])
    C = hip + c_off
    lift = max(0.0, -body_dy(f))
    if not reflect:   # contact shadow shrinks and fades with height
        cv.shadow(hip[0], GROUND + 4, 58 - lift * 0.35, 9 - lift * 0.05, alpha=0.5 - lift * 0.004, blur=5)

    def shoulder(side):
        # arms hang from the body's silhouette edge, never from inside the face/chest
        return C + np.array([side * 36 * fs * sx, 10 * sy])

    def hand_target(ch, side):
        off = np.array(ch(f), float)
        off[0] *= fs
        swing = wp["arm"] * 14 * side * (1 if wp["moving"] else 0)
        return shoulder(side) + off + np.array([swing * fs, 0])

    # far arm + legs (behind the body)
    fsh = shoulder(-1)
    fe, fh = two_bone_ik(fsh, hand_target(far_hand, -1), UPPER, FORE, bend_dir=fs)
    cv.line(fsh, fe, L(P["coat_shade"]), 15)
    cv.line(fe, fh, L(P["coat_shade"]), 14)
    cv.circle(fh[0], fh[1], 9, L(P["coat_shade"]))
    for name, root, knee, end, fa, _ in legs:
        col = L("#2C3240") if name == "far" else L("#3F4658", 0.06)
        cv.line(root, knee, col, 15)
        cv.line(knee, end, col, 14)
        with cv.at(end[0], end[1], fa):
            cv.rect(-12 + 6 * fs, -9, 30, 15, col, r=7)
    # satchel on the front hip, swinging (secondary motion); drawn after the body
    bo = bag_off(f)
    bpos = hip + np.array([16 * fs, -2]) + np.array([bo[0] * 0.8, max(-10, bo[1] * 0.5)])
    bang = -bo[0] * 0.012
    # body: own layer so key/rim light can be painted only onto the coat (src_atop)
    bounds = (C[0] - 160, C[1] - 190, 320, 340)
    with cv.layer(bounds=bounds):
        with cv.at(C[0], C[1], lean, sx, sy):
            cv.blob(0, 0, BODY_RX, BODY_RY, fill=L(P["coat"]), wobble=0.012, seed=3)
            # hood tip: 3-segment chain with overlapping action
            ang = hood_ang(f)
            ho = hood_off(f)
            base = np.array([-12 * fs, -BODY_RY + 10])
            pts = [base]
            dirn = -math.pi / 2 - 0.6 * fs
            for i, aa in enumerate(ang):
                dirn += aa * (1.0 + 0.5 * i) - ho[0] * 0.005 * fs + ho[1] * 0.004 * fs
                seg = 22 - 5 * i
                pts.append(pts[-1] + np.array([math.cos(dirn) * seg, math.sin(dirn) * seg]))
            tip = [(base[0] - 20 * fs, base[1] + 16)] + [tuple(p) for p in pts[1:]] + [(base[0] + 22 * fs, base[1] + 4)]
            cv.poly(tip, L(P["coat"]))
            cv.circle(pts[-1][0], pts[-1][1], 4.5, L(P["coat"]))
            # form shading: underside, top highlight
            cv.ellipse(0, BODY_RY * 0.55, BODY_RX * 0.95, BODY_RY * 0.45, L(P["coat_shade"]), alpha=0.6, blur=8)
            cv.ellipse(-10 * fs, -BODY_RY * 0.5, BODY_RX * 0.55, BODY_RY * 0.26, L(P["coat_hi"]), alpha=0.3, blur=10)
            cv.line((-BODY_RX * 0.8, BODY_RY * 0.62), (BODY_RX * 0.8, BODY_RY * 0.62), L(P["coat_shade"]), 3, alpha=0.8)
            # strap runs across the chest, under the face opening
            loc = np.array([(bpos[0] - C[0]) / sx, (bpos[1] - C[1]) / sy])
            ca, sa = math.cos(-lean), math.sin(-lean)
            loc = np.array([loc[0] * ca - loc[1] * sa, loc[0] * sa + loc[1] * ca])
            cv.line((-30 * fs, -36), (loc[0], loc[1] - 4), L(P["strap"]), 5)
            for by in (14, 32):
                cv.circle(10 * fx, by, 3.5, L(P["coat_shade"]))
            # face opening slides with facing (2-D turn); eyes big enough to act
            fxo = 18 * fx
            frx = 35 * (1 - 0.2 * abs(fx))
            gy = gaze_y(f)
            fy = -26 + gy * 4
            cv.ellipse(fxo, fy, frx, 29, P["face"])
            eo = eye_open(f)
            lid = blink(f, blinks)
            hp = happy(f)
            eye_col = mix(mix(P["eye"], "#9FB0C8", 0.35), "#FFF2DC", li * 0.8)
            for ex in (-12.5, 12.5):
                exx = fxo + ex * (1 - 0.25 * abs(fx)) + 3 * fx
                ey = fy + 1
                ry = 11.0 * min(eo, 1.25) * (1 - lid * 0.92)
                rx = 8.8 * (1 - 0.15 * abs(fx))
                if ry > 0.6:
                    cv.ellipse(exx, ey, rx, ry, eye_col)
                    px = exx + gaze_x(f) * 3.0 * fs
                    py = ey + gy * 3.6
                    cv.circle(px, py, 5.0 * min(eo, 1.1), P["pupil"])
                    cl = mix("#C9D8EA", "#FFE7BE", li)
                    cv.circle(px + (2.0 if li > 0.5 else -1.8), py - 2.2, 1.6, cl)
                    if hp > 0:   # happy: cheeks push the lower lids up
                        cv.ellipse(exx, ey + ry + 3 - hp * 7, rx + 2.5, 6, P["face"])
                    if lid > 0:  # upper lid line reads the blink at any size
                        cv.line((exx - rx, ey - ry + 1), (exx + rx, ey - ry + 1), P["face"], 2)
            if not reflect:
                if li > 0:   # warm key from the window side, high
                    wdir = 1.0 if (WIN[0] + WIN[1]) / 2 > C[0] else -1.0
                    sh_ = cv.linear((wdir * BODY_RX * 0.9, -BODY_RY), (-wdir * BODY_RX * 0.5, BODY_RY * 0.5),
                                    [P["lit"] + "AA", P["lit"] + "00"])
                    cv.rect(-BODY_RX * 2, -BODY_RY * 2, BODY_RX * 4, BODY_RY * 4, sh_, alpha=0.32 * li, blend="src_atop")
                if lamp_k > 0:  # cool top light when passing under the street lamp
                    sh2 = cv.linear((0, -BODY_RY), (0, 0), [P["lamp"] + "99", P["lamp"] + "00"])
                    cv.rect(-BODY_RX * 2, -BODY_RY * 2, BODY_RX * 4, BODY_RY * 4, sh2, alpha=0.6 * lamp_k, blend="src_atop")
    with cv.at(bpos[0], bpos[1], bang):
        if state_at(f, letter_state) == "bag" and f > B["reach"] + 4:
            cv.rect(-12, -14, 24, 12, L(P["letter"]))
        cv.rect(-21, -6, 42, 32, L(P["satchel"]), r=6)
        flap_up = 0.0 if not (B["reach"] + 2 < f < B["letter_out"] + 4) else 1.0
        with cv.at(-21, -6, -0.35 * flap_up * fs):
            cv.rect(0, 0, 42, 13, L(P["strap"]), r=5)
    # near arm (in front) + letter
    nsh = shoulder(1)
    ne, nh = two_bone_ik(nsh, hand_target(near_hand, 1), UPPER, FORE, bend_dir=fs)
    st = state_at(f, letter_state)
    if st == "hand":
        with cv.at(nh[0] + 8 * fs, nh[1] - 6, -0.15 * fs):
            cv.rect(-18, -11, 36, 22, L(P["letter"], 0.15), r=2)
            cv.line((-18, -11), (0, 2), L("#CDBFA6"), 1.5)
            cv.line((18, -11), (0, 2), L("#CDBFA6"), 1.5)
            cv.rect(8, -8, 7, 8, L(P["stamp"]))
    elif st == "slot":
        prog = E.in_out_sine(min(1, max(0, (f - (B["push"] - 2)) / 10)))
        sx0, sx1, sy_ = SLOT
        with cv.clip_rect(-4000, -4000, sx0 + 2 + 4000, 8000):   # only the part outside the door shows
            lx = sx0 - 30 + 52 * prog
            cv.rect(lx - 18, sy_ - 9, 40, 18, L(P["letter"], 0.15), r=2)
            cv.rect(lx + 10, sy_ - 7, 7, 7, L(P["stamp"]))
    arm_col = L(P["coat"], 0.05)
    cv.line(nsh, ne, arm_col, 15)
    cv.line(ne, nh, arm_col, 14)
    cv.circle(nh[0], nh[1], 10, arm_col)


def near_arm(f):
    """(shoulder, hand target) of the near arm in world space - mirrors character() for reach checks."""
    wp = walk_pose(f)
    fs = 1.0 if facing(f) >= 0 else -1.0
    sy = squash(f) * breathe(f, FPS, 0.3, 0.012)
    hip = np.array([root_x(f), wp["hip"][1] + body_dy(f)])
    lean = lean_ch(f) + wp["tilt"] * 0.8
    C = hip + np.array([math.sin(lean) * 56, -math.cos(lean) * 56 * sy])
    sh = C + np.array([36 * fs / sy, 10 * sy])
    off = np.array(near_hand(f), float)
    off[0] *= fs
    swing = wp["arm"] * 14 * (1 if wp["moving"] else 0)
    return sh, sh + off + np.array([swing * fs, 0])


def subject_box(f):
    """World-space corners of the courier, for framing checks."""
    x = root_x(f)
    top = walk_pose(f)["hip"][1] + body_dy(f) - 56 - BODY_RY - 30
    return [(x - 70, top), (x + 70, top), (x - 70, GROUND + 8), (x + 70, GROUND + 8)]


def run_review(out_dir):
    """Director's-loop review pack: beat stills, filmstrips, framing + reach reports."""
    from animkit import review as R
    os.makedirs(out_dir, exist_ok=True)
    keys = {k: B[k] for k in ("arrive", "look_up", "reach", "letter_out", "push", "flap_shut", "sag",
                              "turn_away", "click", "take", "hop", "land", "wave", "exit_walk")}
    print("beats grid:", R.beat_stills(draw, keys, os.path.join(out_dir, "beats"), W, H, post=post))
    loc = lambda f: cam.to_screen(f, root_x(f), walk_pose(f)["hip"][1] + body_dy(f) - 60)  # noqa: E731
    for name, a, b, st in (("walk", 20, 52, 2), ("deliver", int(B["reach"]), int(B["flap_shut"]) + 6, 3),
                           ("turn_take", int(B["sag"]), int(B["turn_back"]) + 8, 3), ("hop", int(B["hop"]) - 2,
                           int(B["land"]) + 14, 2)):
        p = R.subject_strip(draw, [float(f) for f in range(a, b, st)], loc,
                            os.path.join(out_dir, f"strip_{name}.png"), W, H, post=post)
        print("strip:", p)
    bad = R.framing_report(cam, [float(f) for f in range(0, N_FRAMES, 4)], subject_box, W, H, margin=0.03,
                           min_height=0.0, exits_ok=[(0, 24), (B["exit_walk"] + 20, N_FRAMES)])
    print("framing: %d frames outside safe area" % len(bad), [int(f) for f, _ in bad][:12])
    pairs = [(f, *near_arm(f)) for f in np.arange(B["reach"], B["wait"] + 8, 1.0)]
    print("reach: out-of-reach frames", R.reach_report(pairs, UPPER, FORE))
    hts = [R.on_screen(cam, f, subject_box(f), W, H)["height_frac"] for f in (B["push"], B["take"], B["wave"])]
    print("subject height (fraction of frame) at push/take/wave:", [round(h, 2) for h in hts])


# ------------------------------------------------------------------ frame
def draw(cv: Canvas, f: float):
    li = float(light(f))
    draw_sky_and_far(cv, f)
    draw_mid(cv, f)
    draw_rain(cv, f, 0.55, 0.16, 1.0, 0.9, 2)
    with cam.view(cv, f, 1.0):
        draw_house(cv, f, li)
        draw_reflections(cv, f, li)
        # character reflection on wet pavement
        rx = root_x(f)
        with cv.layer(alpha=0.10, blur=3, bounds=(rx - 200, GROUND, 400, 260)):
            with cv.at(0, 2 * GROUND + 6, 0, 1, -1):
                character(cv, f, li, reflect=True)
        character(cv, f, li)
        draw_lights(cv, f, li)
        draw_splashes(cv, f)
    draw_rain(cv, f, 1.0, 0.28, 1.4, 1.0, 3)
    # foreground post (out of focus, parallax)
    with cam.view(cv, f, 1.35):
        with cv.layer(blur=7, bounds=(120, 300, 120, 860)):
            cv.rect(160, 360, 34, 760, "#06090F")
            cv.rect(150, 340, 54, 26, "#06090F", r=6)
    draw_rain(cv, f, 1.35, 0.22, 2.4, 1.4, 9, blur=2.0)


def post(img, i):
    return dither(vignette(img, 0.22), 1.6)


# ------------------------------------------------------------------ sound
def build_audio(out_wav):
    dur = N_FRAMES / FPS + 0.5
    m = A.Mix(dur)
    # ambience: textured rain + far traffic rumble + gutter drip
    m.add(A.rain(dur, 0.7, seed=4), 0, -9, bus="amb")
    m.add(A.filt(A.noise(dur, "brown", 9), "lp", 180) * 0.5, 0, -18, bus="amb")
    for k, c in enumerate(cues.cues):
        t = c["t"]
        kind = c["kind"]
        if kind == "step":
            screen_x = c["x"] - float(cam.x(c["frame"])) + W / 2
            pan = max(-0.9, min(0.9, (screen_x - W / 2) / (W / 2)))
            m.add(A.footstep(seed=k, wet=0.8, weight=0.8), t, -6, pan)
        elif kind == "cloth":
            m.add(A.cloth(0.45, seed=k, level=0.6), t, -14, 0.2)
        elif kind == "paper":
            m.add(A.paper(0.45, seed=k), t, -21, 0.25)
        elif kind == "paper_slide":
            m.add(A.paper(0.5, seed=k + 3), t, -19, 0.3)
        elif kind == "flap_open":
            m.add(A.metal_flap(seed=k, size=1.3) * 0.5, t, -10, 0.3)
        elif kind == "flap_shut":
            m.add(A.metal_flap(seed=k, size=1.0), t, -3, 0.3)
        elif kind == "switch":
            m.add(A.switch_click(seed=k), t, -10, 0.25)
            m.add(A.hum(dur - t - 0.2, 100, 0.02), t + 0.05, -26, 0.25)
        elif kind == "whoosh":
            m.add(A.whoosh(0.35, seed=k, lo=500, hi=3000), t, -16, 0.2)
        elif kind == "land":
            m.add(A.footstep(seed=k, wet=1.0, weight=1.3), t, -3, 0.15)
            m.add(A.footstep(seed=k + 1, wet=1.0, weight=1.3), t + 0.03, -6, 0.15)
    # score: sections follow the beats (not a loop)
    tb = lambda name: B[name] / FPS  # noqa: E731
    beat = 8 * 2 / FPS                     # one beat = two steps (sync to the walk)
    # 1) walk: soft pulse on the steps, B minor colour
    t = B["walk_start"] / FPS
    prog = [["B2", "D3", "F#3"], ["G2", "B2", "D3"], ["D3", "F#3", "A3"], ["A2", "C#3", "E3"]]
    i = 0
    while t < tb("arrive") - 0.2:
        ch = prog[(i // 2) % 4]
        m.add(A.keys_note(A.hz(ch[i % 3].replace("2", "4").replace("3", "4")), 0.6, 0.45), t, -16, -0.2, bus="music")
        if i % 2 == 0:
            m.add(A.pad([A.hz(n) for n in ch], beat * 2 + 0.6, 0.4, 0.6, 0.3, seed=i), t, -14, 0, bus="music")
            m.add(A.bass(A.hz(ch[0].replace("3", "2")), beat * 1.8, 0.6), t, -12, 0, bus="music")
        t += beat
        i += 1
    # 2) delivery + wait: thin out to a single held note, then near silence (tension)
    m.add(A.pad([A.hz("B2"), A.hz("F#3")], tb("sag") - tb("arrive") + 1.0, 1.0, 1.6, 0.2), tb("arrive"), -16, bus="music")
    m.add(A.keys_note(A.hz("F#4"), 1.6, 0.35), tb("look_up"), -18, bus="music")
    m.add(A.keys_note(A.hz("E4"), 1.6, 0.3), tb("look_up2"), -19, bus="music")
    m.add(A.keys_note(A.hz("D4"), 2.0, 0.25), tb("sag") + 0.2, -20, bus="music")
    # 3) light on: warm D major add9 swell, bell-like melody
    tl = tb("click") + 0.15
    m.add(A.pad([A.hz(n) for n in ("D3", "A3", "E4", "F#4")], N_FRAMES / FPS - tl, 1.4, 2.0, 0.45, seed=7),
          tl, -12, bus="music")
    mel = [("A4", 0.0), ("F#4", 0.5), ("A4", 1.0), ("D5", 1.5), ("C#5", 2.6), ("A4", 3.1), ("B4", 3.6), ("A4", 4.6)]
    for n, dt in mel:
        m.add(A.keys_note(A.hz(n), 1.4, 0.55), tl + 0.6 + dt, -13, 0.15, bus="music")
    m.add(A.bass(A.hz("D2"), 3.0, 0.7), tl + 0.6, -12, bus="music")
    m.add(A.bass(A.hz("G2"), 2.4, 0.6), tl + 3.6, -13, bus="music")
    # 4) exit: resolve on D, pulse returns with the steps
    te = tb("exit_walk")
    for j, n in enumerate(["D4", "F#4", "A4", "F#4", "E4", "D4"]):
        m.add(A.keys_note(A.hz(n), 0.9, 0.4), te + j * beat, -16, -0.1, bus="music")
    m.add(A.bass(A.hz("D2"), 4.0, 0.6), te, -13, bus="music")
    m.process("sfx", lambda s: A.reverb(s, 0.16, 1.1, 0.012))
    m.process("music", lambda s: A.reverb(s, 0.25, 2.2, 0.02))
    mixdown = m.render(levels={"amb": 0.0, "sfx": 0.0, "music": -2.0}, duck=("music", "sfx", 3))
    return A.master(mixdown, out_wav, target_lufs=-16.0, true_peak=-1.5, lra=14)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mb", type=int, default=3, help="motion-blur samples (1 = off)")
    ap.add_argument("--preview", action="store_true", help="half-res, no blur, every frame")
    ap.add_argument("--stills", default=None)
    ap.add_argument("--frames", default=None, help="a:b subrange for tests")
    ap.add_argument("--audio-only", action="store_true", help="rebuild sound and re-mux an existing render")
    ap.add_argument("--review", default=None, help="write the review pack (beats, strips, checks) to DIR and exit")
    a = ap.parse_args()
    if a.review:
        run_review(a.review)
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    print("beats (frames):", {k: round(v, 1) for k, v in B.items() if v is not None})
    print("walk-in foot slide px:", walk_in.foot_slide_report(), " walk-out:", walk_out.foot_slide_report())
    cues.save(os.path.splitext(a.out)[0] + "_cues.json")
    silent = os.path.splitext(a.out)[0] + "_silent.mp4"
    start, n = 0, N_FRAMES
    if a.frames:
        s0, s1 = map(int, a.frames.split(":"))
        start, n = s0, s1 - s0
    if a.audio_only:
        wav = os.path.splitext(a.out)[0] + ".wav"
        print("master loudness:", build_audio(wav))
        mux(silent, wav, a.out)
        print("wrote", a.out)
        return
    stats = render(draw, n, silent, w=W, h=H, fps=FPS, mb_samples=1 if a.preview else a.mb, shutter=0.5,
                   post=post, stills_dir=a.stills, stills_every=24, start=start)
    print("render:", stats)
    if a.frames:
        print("chunk rendered (silent). Join chunks with animkit.timeline.concat, then run "
              "--audio-only with --out pointing at the joined file's name (<name>_silent.mp4).")
        return
    wav = os.path.splitext(a.out)[0] + ".wav"
    loud = build_audio(wav)
    print("master loudness:", loud)
    mux(silent, wav, a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
