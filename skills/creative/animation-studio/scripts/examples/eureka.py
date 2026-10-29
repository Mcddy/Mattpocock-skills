#!/usr/bin/env python3
"""EUREKA - a 16-second pantomime built to the feature-animation acting process.

Logline: Pip wants the last biscuit on a high shelf; it's out of reach; Pip gets an idea,
shoves the old crate over, climbs it and gets the biscuit.

Thoughts per beat (written before animating; see references/acting-and-story.md):
  want      "there it is"            eyes up at the jar, a small rise onto the toes
  try       "I can get it"            crouch, stretch, both arms up (offset, not twinned)
  fail      "it's too high"           strain (vibrating), sag; CUT to a medium on the sag; frustrated face
  search    "what's here?"            eye darts: left, back to the jar, down-left... the crate
  idea      "the crate!"              (in the medium since the sag) brows and eyes first, then mouth; hood springs
  effort    "come on"                 walk over, turn, lean into the crate, slow first shove
  climb     "up we go"                crouch, jump, land with a squash on the crate
  win       "got it"                  stretch, the hand reaches the biscuit, takes it
  payoff    "mine"                    turns to us with it; CUT on the turn to a medium; a bite, crumbs, contentment

Tools shown: BlobRig(face_rig=True) + ExpressionTrack + eye_darts, switchable walks
(standing on the crate), body_dx/body_dy jump, hands pinned to what they touch, a camera
with cuts and pushes, fx.dust_puff and crumbs, sound from cues (steps, scrape driven by the
crate's speed, thuds, spring boing, glass clink, crunch).

python3 eureka.py --out eureka.mp4 [--mb 2] [--review DIR] [--frames a:b]
"""
from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from animkit import audio as A                                  # noqa: E402
from animkit import fx                                          # noqa: E402
from animkit.camera import Camera                               # noqa: E402
from animkit.canvas import Canvas, dither, vignette              # noqa: E402
from animkit.curves import Channel, K, Tremor                   # noqa: E402
from animkit.easing import get as ease                          # noqa: E402
from animkit.face import ExpressionTrack, eye_darts             # noqa: E402
from animkit.rigs import BlobRig, Light, Performer, RigStyle    # noqa: E402
from animkit.timeline import CueSheet, mux, render              # noqa: E402
from animkit.walk import Walk                                   # noqa: E402

W, H, FPS = 1920, 1080, 24
GROUND = 860.0
SHELF_Y, SHELF_X0, SHELF_X1 = 652.0, 1010.0, 1430.0
JAR_X, JAR_W, JAR_H = 1236.0, 96.0, 98.0
BISCUIT = np.array([JAR_X - 26, SHELF_Y - JAR_H - 2])      # the last one, poking out of the left of the open jar
CRATE_W, CRATE_H, CRATE_X0 = 150.0, 134.0, 760.0
CRATE_BASE = GROUND + 6.0                       # a touch forward in depth: Pip can walk behind it
CRATE_TOP = CRATE_BASE - CRATE_H
X_IDLE, X_PUSH0 = 1120.0, CRATE_X0 - CRATE_W / 2 - 86     # far enough back that the arms extend to push
PUSH_DIST = 420.0
X_TOP = CRATE_X0 + PUSH_DIST - 32               # where Pip stands on the crate: left of the jar, so the jar stays in view

# ---------------------------------------------------------------- beats (frames)
B = dict(want=0, reach=24, strain=36, give_up=54, search=68, idea=96, turn_l=112, walk1=118)
walk1 = Walk(x0=X_IDLE, x1=X_PUSH0, ground=GROUND, stride=92, step_frames=6, start=B["walk1"], hip_height=74, bob=5,
             lift=14, stance_gap=7, lean=0.09)
B.update(arrive=walk1.t_stop, turn_r=walk1.t_stop + 2)
B.update(brace=B["turn_r"] + 10, push=B["turn_r"] + 18)
push = Walk(x0=X_PUSH0, x1=X_PUSH0 + PUSH_DIST, ground=GROUND, stride=58, step_frames=9, start=B["push"], hip_height=74,
            bob=3, lift=9, stance_gap=8, lean=0.02, start_feet=walk1.final_feet())
B.update(stop=push.t_stop, crouch=push.t_stop + 14, jump=push.t_stop + 20, land=push.t_stop + 30)
B.update(reach2=B["land"] + 18, grab=B["land"] + 32, joy=B["land"] + 46, bite=B["land"] + 80, end=B["land"] + 128)
N = int(B["end"])
top = Walk(x0=X_TOP, x1=X_TOP + 1, ground=CRATE_TOP, start=1e6, hip_height=74, stance_gap=7)
WALKS = [walk1, (B["push"] - 0.001, push), (B["land"], top)]

rig = BlobRig(RigStyle(coat="#D9583B", coat_shade="#A63D27", coat_hi="#F39A7B", face_rig=True, bag=False,
                       limb_far="#3B3540", limb_near="#4C4552", seed=7))


def crate_x(f):
    """The crate moves only while hands push it: its left face stays at Pip's hands."""
    if f < B["push"]:
        return CRATE_X0
    return CRATE_X0 + (push.hip_x(f) - X_PUSH0)


# ---------------------------------------------------------------- performance
J = B["jump"]
L_ = B["land"]
DX = X_TOP - (X_PUSH0 + PUSH_DIST)
RISE = GROUND - CRATE_TOP
chan = dict(
    facing=Channel([K(0, 0.85), K(B["reach"], 0.85, "slow_in_out"), K(B["reach"] + 8, 0.45),   # 3/4 to us for the strain,
                    K(B["search"] + 3, 0.45, "slow_in_out"), K(B["search"] + 8, 0.15),           # arm clear of the face
                    K(B["search"] + 12, 0.15, "slow_in_out"), K(B["search"] + 16, 0.75),
                    K(B["search"] + 22, 0.75, "snap"), K(B["search"] + 27, -0.05), K(B["idea"], -0.05, "snap"),
                    K(B["idea"] + 5, -0.3), K(B["turn_l"], -0.3, "anticipate"), K(B["turn_l"] + 6, -1.0),
                    K(B["arrive"], -1.0, "snap"), K(B["turn_r"] + 5, 1.0), K(B["joy"], 1.0, "slow_in_out"),
                    K(B["joy"] + 12, -0.3), K(N, -0.3)]),          # turns to us with the prize: 'mine'
    body_dy=Channel([K(0, 0.0), K(4, 0.0, "slow_in_out"), K(12, -5.0), K(20, 0.0, "slow_in_out"),     # want: up on toes
                     K(B["reach"], 0.0, "slow_in_out"), K(B["reach"] + 6, 9.0, "snap"),               # crouch
                     K(B["reach"] + 12, -16.0, "slow_in_out"), K(B["give_up"], -15.0, "heavy"),        # stretch, strain
                     K(B["give_up"] + 10, 7.0, "settle"), K(B["give_up"] + 24, 3.0),                   # sag
                     K(B["idea"] - 2, 3.0, "snap"), K(B["idea"] + 4, -7.0, "settle"), K(B["idea"] + 16, 0.0),
                     K(B["brace"], 0.0, "slow_in_out"), K(B["push"], 6.0),
                     K(B["stop"], 6.0, "settle"), K(B["stop"] + 8, 0.0),
                     K(B["crouch"], 0.0, "heavy"), K(J, 14.0, "out_quad"),                            # crouch
                     K(J + 5, -RISE - 34, "out_quad"), K(L_ - 0.01, -RISE, "in_quad"),                   # apex, fall
                     K(L_, 0.0, "snap"), K(L_ + 3, 10.0, "settle"), K(L_ + 14, 0.0),                     # land
                     K(B["reach2"], 0.0, "slow_in_out"), K(B["reach2"] + 10, -12.0), K(B["grab"] + 2, -12.0, "settle"),
                     K(B["grab"] + 10, 0.0), K(B["joy"], 0.0, "snap"), K(B["joy"] + 4, -10.0, "settle"),
                     K(B["joy"] + 12, 0.0, "snap"), K(B["joy"] + 16, -6.0, "settle"), K(B["joy"] + 26, 0.0), K(N, 0.0)]),
    body_dx=Tremor(Tremor(Channel([K(0, 0.0), K(J, 0.0, "out_quad"), K(L_ - 0.01, DX), K(L_, 0.0),
                                   K(B["bite"] + 30, 0.0, "in_out_sine"), K(B["bite"] + 40, 4.0, "in_out_sine"),
                                   K(N, -2.0)]),                                        # savour: a contented sway
                          B["strain"] - 4, B["give_up"] + 2, amp=1.6, seed=2),          # strain: effort vibration
                   B["brace"] + 2, B["push"] + 4, amp=1.2, seed=5),                     # "it's heavy": the first shove
    squash=Channel([K(0, 1.0), K(B["reach"], 1.0, "snap"), K(B["reach"] + 6, 0.9, "slow_in_out"),
                    K(B["reach"] + 12, 1.12, hold=8), K(B["give_up"], 1.1, "heavy"), K(B["give_up"] + 10, 0.95, "settle"),
                    K(B["give_up"] + 24, 1.0), K(B["idea"] - 2, 1.0, "snap"), K(B["idea"] + 4, 1.07, "settle"),
                    K(B["idea"] + 16, 1.0), K(J - 6, 1.0, "snap"), K(J, 0.86, "out_quad"), K(J + 5, 1.14, "in_quad"),
                    K(L_ - 1, 1.08, "snap"), K(L_ + 2, 0.84, "settle"), K(L_ + 14, 1.0),
                    K(B["reach2"], 1.0, "slow_in_out"), K(B["reach2"] + 10, 1.1), K(B["grab"] + 2, 1.1, "settle"),
                    K(B["grab"] + 10, 1.0), K(B["joy"], 1.0, "snap"), K(B["joy"] + 4, 1.08, "settle"), K(B["joy"] + 14, 1.0),
                    K(N, 1.0)]),
    lean=Channel([K(0, 0.0), K(B["reach"] + 8, 0.0, "slow_in_out"), K(B["reach"] + 14, 0.05),
                  K(B["give_up"], 0.05, "heavy"), K(B["give_up"] + 10, -0.04), K(B["search"], -0.02),
                  K(B["brace"], 0.0, "anticipate"), K(B["push"] - 2, -0.06, "heavy"), K(B["push"] + 6, 0.26),   # lean in
                  K(B["stop"] - 4, 0.24, "settle"), K(B["stop"] + 8, 0.02), K(B["crouch"], 0.02, "slow_in_out"),
                  K(J, 0.12), K(J + 4, -0.04), K(L_ + 6, 0.0), K(B["bite"] + 28, 0.0, "in_out_sine"),
                  K(B["bite"] + 36, 0.06, "in_out_sine"), K(B["bite"] + 44, -0.05, "in_out_sine"),   # savouring: a slow rock
                  K(N, 0.03)]),
    near_stretch=Channel([K(0, 1.0), K(B["reach"] + 8, 1.0, "slow_in_out"), K(B["strain"], 1.55, hold=10),
                          K(B["give_up"], 1.5, "heavy"), K(B["give_up"] + 10, 1.0), K(B["reach2"], 1.0, "slow_in_out"),
                          K(B["grab"] - 2, 1.3), K(B["grab"] + 4, 1.3, "settle"), K(B["grab"] + 12, 1.0), K(N, 1.0)]),
    far_stretch=Channel([K(0, 1.0), K(B["reach"] + 11, 1.0, "slow_in_out"), K(B["strain"] + 3, 1.45, hold=8),
                         K(B["give_up"] + 2, 1.4, "heavy"), K(B["give_up"] + 12, 1.0), K(N, 1.0)]),
    near_hand=Channel([K(0, (2.0, 44.0)), K(B["bite"], (2.0, 44.0), "slow_in_out"), K(B["bite"] + 14, (20.0, -6.0)),
                       K(N, (20.0, -4.0))]),                       # after the bite: keeps the prize up where we see it
    far_hand=Channel([K(0, (-6.0, 44.0)), K(B["reach"] + 9, (-6.0, 44.0), "slow_in_out"),
                      K(B["reach"] + 15, (8.0, -86.0)), K(B["give_up"] + 2, (6.0, -84.0), "heavy"),
                      K(B["give_up"] + 12, (-8.0, 44.0)), K(N, (-8.0, 44.0))]),
)
track = ExpressionTrack([(0, "curious"), (B["reach"] + 8, "effort"), (B["give_up"] + 4, "frustrated"),
                         (B["search"], "thinking"), (B["idea"], "idea", "snap"), (B["turn_l"] + 2, "determined"),
                         (B["push"], "effort"), (B["stop"] + 6, "determined"), (B["crouch"], "effort"),
                         (L_ + 6, "determined"), (B["reach2"] + 4, {"brow_l": 0.3, "brow_r": 0.25, "lid_top": 0.1,
                                                                   "mouth_open": 0.15, "mouth_round": 0.5, "pupil": 1.1}),
                         (B["grab"] + 2, "surprised", "snap"), (B["grab"] + 9, "joy"), (B["bite"] + 30, "content")])
darts = eye_darts([(6, (0.55, -0.85)), (B["give_up"] + 6, (0.3, 0.45)), (B["search"] + 2, (-0.9, 0.05)),
                   (B["search"] + 10, (0.6, -0.8)), (B["search"] + 20, (-0.75, 0.4)), (B["turn_l"] + 2, (1.0, 0.1)),
                   (B["arrive"] - 2, (1.0, 0.3)), (B["stop"] + 4, (0.4, -0.6)), (B["crouch"] - 2, (0.5, -0.4)),
                   (L_ + 6, (0.4, -0.9)), (B["grab"] + 10, (0.1, 0.35)), (B["joy"] + 18, (0.0, 0.0)),
                   (B["bite"] - 6, (-0.4, 0.45)), (B["bite"] + 34, (0.0, 0.0))], start=(0.55, -0.85))
chew = Channel([K(0, 0.0), K(B["bite"] - 4, 0.0, "snap"), K(B["bite"], 0.7, "snap"), K(B["bite"] + 3, 0.05),
                K(B["bite"] + 9, 0.35), K(B["bite"] + 13, 0.05), K(B["bite"] + 18, 0.3), K(B["bite"] + 22, 0.04),
                K(B["bite"] + 27, 0.0), K(N, 0.0)])
perf = Performer(rig, WALKS, range(0, N + 1),
                 channels={**chan, **track.channels(), **darts, "lip_open": chew, "lip_round": Channel([K(0, 0.35)])},
                 blinks=[B["give_up"] + 3, B["idea"] - 3, B["turn_l"] + 1, B["stop"] + 2, L_ + 1, B["bite"] + 40,
                         B["bite"] + 80])

# ---------------------------------------------------------------- hands: pinned to what they touch
def _blend(f, a, b, ease_name="slow_in_out"):
    return ease(ease_name)(min(1.0, max(0.0, (f - a) / max(1e-6, b - a))))


def mouth_world(p):
    """Approximate world position of the face rig's mouth (face slides with facing; body scale sx=1/sy)."""
    C = rig.centre(p)
    return C + np.array([20 * p.facing / p.squash, -8 * p.squash])


def hand_targets(f, p):
    """World-space near-hand target (or None to keep the keyed arm)."""
    if B["reach"] + 6 <= f < B["give_up"] + 12:           # reaching for the jar: hand stretches at the biscuit
        k = _blend(f, B["reach"] + 6, B["reach"] + 14) * (1 - _blend(f, B["give_up"], B["give_up"] + 12, "heavy"))
        return BISCUIT, k
    if B["brace"] <= f < B["stop"] + 6:                    # hands on the crate face
        k = _blend(f, B["brace"], B["push"] - 2) * (1 - _blend(f, B["stop"], B["stop"] + 6))
        return np.array([crate_x(f) - CRATE_W / 2 + 3, CRATE_TOP + 30]), k   # chest height, arm extended (clear of the face)
    if B["crouch"] <= f < J + 3:                           # hands on the crate's top edge for the jump
        k = _blend(f, B["crouch"], B["crouch"] + 5) * (1 - _blend(f, J, J + 3))
        return np.array([crate_x(f) - CRATE_W / 2 + 4, CRATE_TOP + 26]), k   # the crate's near top corner
    if B["reach2"] <= f < B["grab"] + 4:                   # the successful reach
        k = _blend(f, B["reach2"], B["grab"] - 2)
        return BISCUIT, k
    if B["grab"] + 4 <= f < B["bite"] - 8:
        return None, 0.0
    if B["bite"] - 8 <= f < B["bite"] + 30:                # biscuit to mouth
        k = _blend(f, B["bite"] - 8, B["bite"] - 1, "snap") * (1 - _blend(f, B["bite"] + 2, B["bite"] + 14))
        return mouth_world(p) + np.array([10 * np.sign(p.facing), 8]), k
    return None, 0.0


def posed(f):
    p = perf.pose(f)
    T, k = hand_targets(f, p)
    fs = 1.0 if p.facing >= 0 else -1.0
    if T is not None and k > 0:
        sh = rig.shoulder(p, 1)
        o = (np.asarray(T, float) - sh)
        o[0] *= fs
        base = np.asarray(p.near_hand, float)
        p.near_hand = tuple(base + (o - base) * k)
        p.arm_swing = 0.0
    if B["grab"] + 4 <= f < B["bite"] - 8:                  # holding the prize up at chest height, clear of the jar
        p.near_hand = (14.0, 10.0) if f < B["joy"] + 4 else \
            tuple(np.array((14.0, 10.0)) + (np.array((24.0, -16.0)) - (14.0, 10.0)) * _blend(f, B["joy"] + 4, B["joy"] + 12))
    if B["brace"] <= f < B["stop"] + 4:
        p.far_hand = (58.0, 24.0)                           # second hand on the crate too, a little lower
    if f >= B["grab"]:
        bitten = f >= B["bite"]
        p.prop = lambda cv, hand, fsg, b=bitten: draw_biscuit(cv, hand[0] + 6 * fsg, hand[1] - 4, bitten=b)
    return p


# ---------------------------------------------------------------- world
LIGHT = Light(ambient=(0.98, 0.94, 0.88), key_col="#FFE3B8", key=0.32, key_dir=-1.0, rim_col="#FFD9A8", rim=0.12)


def draw_biscuit(cv, x, y, bitten=False, r=13.0):
    with cv.layer(bounds=(x - r - 2, y - r - 2, 2 * r + 4, 2 * r + 4)):
        cv.circle(x, y, r, "#D39A52")
        cv.circle(x - 3, y - 3, r * 0.75, "#E2B06C", alpha=0.6)
        for dx, dy in ((-5, -2), (4, 3), (1, -6), (-2, 5)):
            cv.circle(x + dx, y + dy, 1.8, "#6B3B1E")
        if bitten:                                   # a bite taken out (erase inside the layer)
            for bx, by in ((0.3, -0.95), (-0.2, -1.05)):   # out of the top edge, so the bite reads in any hand
                cv.circle(x + r * bx, y + r * by, r * 0.42, "#000000", blend="dst_out")


def draw_set(cv, f):
    # wall: tiles above, sage panelling below; motivated window light from the left
    cv.rect(-400, -200, 2800, 1100, cv.linear((0, 0), (0, 700), ["#EFE6D2", "#E6DAC1"]))
    for y in range(0, 700, 54):
        cv.line((-400, y), (2400, y), "#D7C9AC", 2)
    for i, x in enumerate(range(-400, 2400, 54)):
        cv.line((x, 0), (x, 700), "#DDD0B5", 1.5)
    cv.rect(-400, 700, 2800, GROUND - 700, "#8D9C90")
    cv.rect(-400, 700, 2800, 10, "#7A897D")
    for x in range(-400, 2400, 120):
        cv.line((x, 712), (x, GROUND), "#7F8E82", 3)
    cv.rect(-400, GROUND, 2800, 400, cv.linear((0, GROUND), (0, GROUND + 260), ["#B98356", "#9E6B44"]))
    for x in range(-400, 2400, 180):
        cv.line((x, GROUND), (x - 120, GROUND + 260), "#A87650", 2)
    cv.cone((60, 120), (420, GROUND + 20), (1300, GROUND + 20), "#FFE9C4", intensity=0.32, soften=40)
    # shelf, brackets, jar, lid, tin
    cv.rect(SHELF_X0, SHELF_Y, SHELF_X1 - SHELF_X0, 22, "#7A4A2C", r=3)
    cv.rect(SHELF_X0, SHELF_Y + 22, SHELF_X1 - SHELF_X0, 6, "#5E3820", alpha=0.6)
    for bx in (SHELF_X0 + 60, SHELF_X1 - 60):
        cv.poly([(bx - 6, SHELF_Y + 22), (bx + 6, SHELF_Y + 22), (bx + 6, SHELF_Y + 90)], "#5E3820")
    cv.shadow(JAR_X, SHELF_Y + 2, JAR_W * 0.55, 5, alpha=0.35, blur=4)
    cv.rect(JAR_X - JAR_W / 2, SHELF_Y - JAR_H, JAR_W, JAR_H, "#DDEAF0", r=16, alpha=0.55)
    for bx, by in ((-24, -22), (0, -30), (22, -20), (-12, -48), (14, -52)):
        draw_biscuit(cv, JAR_X + bx, SHELF_Y + by, r=12)
    cv.rect(JAR_X - JAR_W / 2, SHELF_Y - JAR_H, JAR_W, JAR_H, None, r=16, stroke="#9FB6C1", sw=3)
    cv.rect(JAR_X - JAR_W / 2 + 10, SHELF_Y - JAR_H + 14, 8, JAR_H - 30, "#FFFFFF", r=4, alpha=0.5)
    if f < B["grab"]:
        draw_biscuit(cv, *BISCUIT)
    cv.ellipse(JAR_X + 92, SHELF_Y - 8, 40, 9, "#C5D7DF")                     # the lid someone left off
    cv.ellipse(JAR_X + 92, SHELF_Y - 12, 34, 6, "#DDEAF0")
    cv.rect(SHELF_X0 + 40, SHELF_Y - 70, 60, 70, "#5F7F82", r=6)               # a tin (muted: red is Pip's colour)
    cv.rect(SHELF_X0 + 40, SHELF_Y - 70, 60, 12, "#4B6669", r=5)


def draw_crate(cv, f):
    x = crate_x(f)
    x0 = x - CRATE_W / 2
    cv.shadow(x, CRATE_BASE + 2, CRATE_W * 0.58, 7, alpha=0.45, blur=5)
    cv.rect(x0, CRATE_TOP, CRATE_W, CRATE_H, "#B8854F", r=4)
    for k in range(1, 4):
        cv.line((x0 + 6, CRATE_TOP + k * CRATE_H / 4), (x0 + CRATE_W - 6, CRATE_TOP + k * CRATE_H / 4), "#94683A", 3)
    cv.line((x0 + 12, CRATE_BASE - 10), (x0 + CRATE_W - 12, CRATE_TOP + 10), "#9E7041", 9)
    cv.rect(x0, CRATE_TOP, CRATE_W, 10, "#C9975D", r=3)
    cv.rect(x0, CRATE_TOP, CRATE_W, CRATE_H, None, r=4, stroke="#7C5530", sw=3)
    cv.rect(x0 + CRATE_W - 18, CRATE_TOP, 18, CRATE_H, "#000000", alpha=0.12)


DUST = [fx.dust_puff(B["push"] + 4, (CRATE_X0 - CRATE_W / 2 + 10, CRATE_BASE), CRATE_BASE, 0.6, "#D9C2A2", seed=3),
        fx.dust_puff(B["stop"], (X_PUSH0 + PUSH_DIST + 132, CRATE_BASE), CRATE_BASE, 1.0, "#D9C2A2", seed=5),
        fx.dust_puff(L_, (X_TOP, CRATE_TOP), CRATE_TOP, 0.55, "#D9C2A2", seed=7)]
_MOUTH_AT_BITE = None


def crumbs():
    global _MOUTH_AT_BITE
    if _MOUTH_AT_BITE is None:
        m = mouth_world(perf.pose(B["bite"] + 1))
        _MOUTH_AT_BITE = fx.Burst(B["bite"] + 1, (m[0] + 8, m[1] + 6), n=10, speed=(40, 160),
                                  angle=(-math.pi * 0.9, -math.pi * 0.1), gravity=900, drag=1.0, life=(0.5, 0.9),
                                  size=(2.0, 3.5), colors=("#D39A52", "#B97E3E"), seed=11, ground=CRATE_TOP)
    return _MOUTH_AT_BITE

# ---------------------------------------------------------------- camera: wide, CUT to medium for the idea, CUT to medium for the payoff
E_ = 0.01                                                   # cut = two keys 0.01 frames apart
GC, TC = B["give_up"] + 3, B["turn_l"] + 7                  # cut in on the sag (thought beats in a medium), out for the action
PC = B["joy"] + 7                                           # cut on the action (mid-turn) to a medium for the payoff
cam = Camera(W, H,
             x=Channel([K(0, 1000.0, "slow_in_out"), K(GC - E_, 1068.0, "linear"), K(GC, 1108.0, "slow_in_out"),
                        K(TC - E_, 1116.0, "linear"), K(TC, 980.0, "slow_in_out"), K(B["arrive"], 860.0, "slow_in_out"),
                        K(B["push"], 860.0, "slow_in_out"), K(B["stop"], 1100.0, "slow_in_out"), K(L_ + 10, 1180.0, "slow_in_out"),
                        K(B["joy"] + 6, X_TOP + 30, "linear"), K(PC - E_, X_TOP + 31, "linear"), K(PC, X_TOP - 18, "slow_in_out"),
                        K(N, X_TOP - 22)]),
             y=Channel([K(0, 690.0, "slow_in_out"), K(GC - E_, 700.0, "linear"), K(GC, 704.0, "slow_in_out"),
                        K(TC - E_, 712.0, "linear"), K(TC, 700.0, "slow_in_out"), K(B["stop"], 690.0, "slow_in_out"),
                        K(L_ + 10, 640.0, "slow_in_out"), K(B["joy"] + 6, 612.0, "linear"), K(PC - E_, 612.0, "linear"),
                        K(PC, 618.0, "slow_in_out"), K(N, 614.0)]),
             zoom=Channel([K(0, 1.36, "slow_in_out"), K(GC - E_, 1.7, "linear"), K(GC, 2.15, "slow_in_out"),
                           K(TC - E_, 2.45, "linear"), K(TC, 1.5, "slow_in_out"), K(B["arrive"], 1.55, "slow_in_out"),
                           K(B["push"], 1.55, "slow_in_out"), K(B["stop"], 1.6, "slow_in_out"), K(L_ + 10, 1.9, "slow_in_out"),
                           K(B["joy"] + 6, 2.35, "linear"), K(PC - E_, 2.36, "linear"), K(PC, 3.5, "slow_in_out"), K(N, 3.75)]))
cam.handheld = 0.8

# ---------------------------------------------------------------- draw
def draw(cv: Canvas, f: float):
    cv.clear("#E6DAC1")
    with cam.view(cv, f, 1.0):
        draw_set(cv, f)
        p = posed(f)
        front = f < B["arrive"]                                   # Pip walks behind the crate on the way over
        if not front:
            draw_crate(cv, f)
        ground = perf._walk(f).ground
        rig.draw(cv, p, LIGHT, ground=ground)
        if front:
            draw_crate(cv, f)
        for d in DUST:
            d.draw(cv, f)
        if f >= B["bite"]:
            crumbs().draw(cv, f)


def post(img, i):
    return dither(vignette(img, 0.16))


# ---------------------------------------------------------------- sound from the action
cues = CueSheet(FPS)
for w in (walk1, push):
    for t, foot, x in w.contacts:
        cues.add(t, "step", heavy=w is push)
cues.add(B["reach"] + 12, "cloth").add(B["give_up"] + 8, "cloth").add(B["idea"], "boing")
cues.add(B["push"] + 2, "thud", pitch=0.8).add(B["stop"], "thud", pitch=0.75).add(J + 1, "cloth").add(L_, "land")
cues.add(B["reach2"] + 6, "cloth").add(B["grab"], "clink").add(B["bite"], "crunch")
for k in (B["bite"] + 9, B["bite"] + 18):
    cues.add(k, "chew")


def build_audio(path):
    dur = N / FPS + 0.8
    m = A.Mix(dur)
    m.add(A.filt(A.noise(dur, "brown", 4), "lp", 300) * 0.2, 0, -30, bus="amb")       # room tone
    sp = np.array([abs(push.speed(f)) / push.vmax for f in np.arange(B["push"], B["stop"] + 1, 1.0)])
    m.add(A.scrape(sp, seed=2), B["push"] / FPS, -15, 0.1)
    for k, c in enumerate(cues.cues):
        t = c["t"]
        kind = c["kind"]
        if kind == "step":
            m.add(A.footstep(seed=k, weight=1.0 if c.get("heavy") else 0.6, surface="wood"), t, -12 if c.get("heavy") else -15)
        elif kind == "cloth":
            m.add(A.cloth(0.35, seed=k, level=0.5), t, -17)
        elif kind == "boing":
            m.add(A.spring_boing(210, 0.5, seed=k), t, -16, 0.1)
        elif kind == "thud":
            m.add(A.thump(seed=k, pitch=c.get("pitch", 1.0)), t, -10)
        elif kind == "land":
            m.add(A.thump(seed=k, pitch=0.9), t, -9)
            m.add(A.footstep(seed=k + 1, weight=1.0, surface="wood"), t + 0.01, -13)
        elif kind == "clink":
            m.add(A.modal([2350, 3710, 5240], [0.25, 0.18, 0.12], [1.0, 0.6, 0.35], 0.5, seed=k), t, -18, 0.2)
        elif kind == "crunch":
            m.add(A.crunch(seed=k), t, -12, 0.1)
        elif kind == "chew":
            m.add(A.crunch(seed=k, dur=0.12) * 0.5, t, -20, 0.1)
    # underscore: a small plucked score that follows each thought (see references/sound.md)
    def pz(note, frame, db=-22, pan=0.0, dur=0.6, bright=0.45):
        m.add(A.karplus(A.hz(note), dur, seed=int(frame), bright=bright), frame / FPS, db, pan, bus="music")
    pz("G4", 6), pz("C5", 12)                                                    # want: "there it is"
    reach_motif = ("C5", "D5", "E5")
    for j, nn in enumerate(reach_motif):                                         # try: the motif climbs with the arm
        pz(nn, B["reach"] + 3 * j, -21)
    m.add(A.pad([A.hz("C4"), A.hz("E4"), A.hz("G4")], 0.9, attack=0.5, release=0.4, bright=0.45),
          B["strain"] / FPS, -27, bus="music")                                   # strain: held tension
    for j, nn in enumerate(reach_motif[::-1] + ("G4",)):                         # fail: the same motif, reversed, sinking
        pz(nn, B["give_up"] + 2 + 4 * j, -24 - j)
    for j, f_ in enumerate(range(int(B["search"]) + 2, int(B["idea"]) - 4, 8)):  # search: ticking thought
        pz("G3" if j % 2 == 0 else "D4", f_, -27, dur=0.35, bright=0.3)
    for nn in ("C5", "E5", "G5"):                                                # idea: the chord lands with the boing
        m.add(A.keys_note(A.hz(nn), 0.9, 0.5), (B["idea"] + 1) / FPS, -24, bus="music")
    for j, (t, foot, x) in enumerate(walk1.contacts):                            # determined walk: bass on the steps
        pz("C3" if j % 2 == 0 else "G2", t, -24, dur=0.4, bright=0.25)
    m.add(A.pad([A.hz("C3"), A.hz("G3")], (B["stop"] - B["push"]) / FPS, attack=1.2, release=0.3, bright=0.3),
          B["push"] / FPS, -25, bus="music")                                     # effort swells under the push
    # silence in the score from the stop to the grab: the climb plays on Foley alone
    for j, nn in enumerate(("E5", "G5", "C6")):                                  # win: the motif completes, higher
        m.add(A.keys_note(A.hz(nn), 1.4, 0.45), B["grab"] / FPS + 0.25 + j * 0.11, -21, 0.15, bus="music")
    m.add(A.pad([A.hz("C4"), A.hz("E4"), A.hz("G4"), A.hz("B4")], (N - B["bite"]) / FPS + 0.8, attack=0.8,
                release=1.2, bright=0.35), (B["bite"] + 8) / FPS, -27, bus="music")      # savour: warm and open
    m.process("music", lambda s: A.reverb(s, 0.25, 1.6, 0.02))
    return A.master(m.render(), path, target_lufs=-16.0)


def review(out_dir):
    from animkit import review as R
    os.makedirs(out_dir, exist_ok=True)
    beats = {k: v for k, v in B.items() if k not in ("end", "walk1", "turn_r")}
    print("beats grid:", R.beat_stills(draw, beats, out_dir, W, H, post=post))
    loc = lambda f: cam.to_screen(f, *(posed(f).hip + np.array([0, -70])))  # noqa: E731
    for name, a, b, step in (("try_fail", B["reach"], B["give_up"] + 14, 3), ("idea", B["search"], B["turn_l"] + 6, 3),
                             ("push", B["brace"], B["stop"] + 10, 4), ("climb", B["crouch"], L_ + 14, 2),
                             ("win", B["reach2"], B["bite"] + 30, 4)):
        print("strip:", R.subject_strip(draw, [float(f) for f in np.arange(a, b, step)], loc,
                                        os.path.join(out_dir, f"strip_{name}.png"), W, H, post=post))
    print("framing:", R.framing_report(cam, [float(f) for f in range(0, N, 3)],
                                       lambda f: rig.bbox(posed(f), perf._walk(f).ground), W, H, margin=0.03))
    # reach: the first try must fail (gap), the second must land on the biscuit
    for label, f in (("try", B["give_up"] - 2), ("win", B["grab"])):
        p = posed(f)
        sh = rig.shoulder(p, 1)
        gap = float(np.linalg.norm(BISCUIT - sh)) - (rig.s.upper + rig.s.fore) * p.near_stretch
        print(f"reach {label}: gap to biscuit {gap:.0f}px ({'out of reach' if gap > 0 else 'reached'})")
    print("foot slide px:", walk1.foot_slide_report(), push.foot_slide_report())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mb", type=int, default=2)
    ap.add_argument("--review", default=None)
    ap.add_argument("--frames", default=None)
    a = ap.parse_args()
    if a.review:
        review(a.review)
        return
    if a.frames:
        s, e = (int(v) for v in a.frames.split(":"))
        print(render(draw, e - s, a.out, w=W, h=H, fps=FPS, mb_samples=a.mb, post=post, start=s))
        return
    silent = os.path.splitext(a.out)[0] + "_silent.mp4"
    print(render(draw, N, silent, w=W, h=H, fps=FPS, mb_samples=a.mb, post=post))
    wav = os.path.splitext(a.out)[0] + ".wav"
    print("loudness", build_audio(wav))
    cues.save(os.path.splitext(a.out)[0] + "_cues.json")
    mux(silent, wav, a.out)
    print("wrote", a.out, "frames", N)


if __name__ == "__main__":
    main()
