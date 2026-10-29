"""Procedural side-view walk with real foot plants (no skating).

Mechanics encoded here (see references/principles.md):
* Contact -> Down -> Passing -> Up, one cycle per step; the hip is lowest just
  after contact (weight lands) and highest at the up position.
* Gait: each foot is planted ~60% of a two-step cycle; swing is 0.8 of a step,
  leaving brief double support. Planted feet are locked in world space.
* Hip velocity follows a trapezoid: accelerate over the first step, cruise,
  decelerate into a closing step. Strides shrink as speed drops.
* Arms counter-swing to the legs; bob, arm swing and lean scale with speed so a
  standing character settles instead of freezing mid-cycle.
* `contacts` lists every heel-strike frame for sound sync.

Coordinates are screen space (y down). Facing +x by default.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import easing as E


@dataclass
class Walk:
    x0: float
    x1: float
    ground: float
    stride: float = 90.0          # px between successive plants at cruise
    step_frames: float = 12.0     # frames per step at cruise (12 @24fps = brisk, 16 = stroll)
    start: float = 0.0            # frame the hip starts moving
    hip_height: float = 90.0      # hip above ground at contact
    bob: float = 5.0              # vertical hip travel (px)
    lift: float = 16.0            # swing-foot clearance (px)
    stance_gap: float = 8.0       # half-distance between feet when standing
    swing_frac: float = 0.8       # swing duration / step duration
    lean: float = 0.06            # forward lean (rad) at cruise
    start_feet: tuple | None = None  # (near_x, far_x) to continue from a previous pose without a pop
    contacts: list = field(default_factory=list, init=False)

    def __post_init__(self):
        self.dir = 1.0 if self.x1 >= self.x0 else -1.0
        dist = abs(self.x1 - self.x0)
        self.vmax = self.stride / self.step_frames
        self.ramp = self.step_frames * 1.0
        cruise = max(0.0, dist / self.vmax - self.ramp)   # trapezoid area = vmax*(cruise+ramp)
        self.t_cruise_end = self.start + self.ramp + cruise
        self.t_stop = self.t_cruise_end + self.ramp
        self._build_plants()

    # ------------------------------------------------------------ hip motion
    def speed(self, f):
        if f <= self.start or f >= self.t_stop:
            return 0.0
        if f < self.start + self.ramp:
            u = (f - self.start) / self.ramp
            return self.vmax * E.in_out_sine(u)
        if f > self.t_cruise_end:
            u = (self.t_stop - f) / self.ramp
            return self.vmax * E.in_out_sine(u)
        return self.vmax

    def hip_x(self, f):
        # integrate the speed profile analytically-enough (fine steps, cached)
        if not hasattr(self, "_xs"):
            fs = np.arange(self.start - 1, self.t_stop + 2, 0.05)
            vs = np.array([self.speed(x) for x in fs])
            xs = np.concatenate([[0.0], np.cumsum((vs[1:] + vs[:-1]) / 2 * 0.05)])
            # normalise so we land exactly on x1
            if xs[-1] > 0:
                xs *= abs(self.x1 - self.x0) / xs[-1]
            self._fs, self._xs = fs, xs
        if f <= self._fs[0]:
            d = 0.0
        elif f >= self._fs[-1]:
            d = self._xs[-1]
        else:
            d = float(np.interp(f, self._fs, self._xs))
        return self.x0 + self.dir * d

    # ------------------------------------------------------------ foot plants
    def _build_plants(self):
        sf = self.step_frames
        # contact times: first heel strike after a quarter step of lean-in
        c = self.start + sf * 0.75
        near0, far0 = self.start_feet or (self.x0 - self.dir * self.stance_gap, self.x0 + self.dir * self.stance_gap)
        plants = {"near": [(-1e9, near0)], "far": [(-1e9, far0)]}
        foot = "far"
        events = []
        while c < self.t_stop - sf * 0.3:
            v = self.speed(c)
            reach = 0.5 * self.stride * max(0.35, v / self.vmax)
            x = self.hip_x(c) + self.dir * reach
            plants[foot].append((c, x))
            events.append((c, foot, x))
            foot = "near" if foot == "far" else "far"
            c += sf
        # closing step: trailing foot comes alongside the hip
        c = max(c, self.t_stop - sf * 0.1)
        xe = self.hip_x(self.t_stop)
        other = "near" if foot == "far" else "far"
        lead_x = plants[other][-1][1]
        close_x = xe - self.dir * self.stance_gap if self.dir * (lead_x - xe) > 0 else xe + self.dir * self.stance_gap
        plants[foot].append((c, close_x))
        events.append((c, foot, close_x))
        self.plants = plants
        self.contacts = [(round(t, 2), ft, x) for t, ft, x in events]
        self.end_frame = c + 4

    def _foot(self, name, f):
        sf = self.step_frames
        swing = sf * self.swing_frac
        seq = self.plants[name]
        # find the last plant whose contact <= f
        idx = 0
        for i, (t, _) in enumerate(seq):
            if t <= f:
                idx = i
        cur_t, cur_x = seq[idx]
        if idx + 1 < len(seq):
            nxt_t, nxt_x = seq[idx + 1]
            lift_off = nxt_t - swing
            if f >= lift_off:
                u = (f - lift_off) / swing
                ue = E.in_out_sine(u)
                x = cur_x + (nxt_x - cur_x) * ue
                y = self.ground - self.lift * math.sin(math.pi * u) ** 0.85 * min(1.0, abs(nxt_x - cur_x) / (self.stride * 0.6))
                # toe-off then heel-strike rotation
                ang = self.dir * (-0.5 * math.sin(math.pi * min(1, u * 1.6)) + 0.35 * math.sin(math.pi * max(0, (u - 0.6) / 0.4)))
                return np.array([x, y]), ang, True
        # planted: locked in world space; slight heel peel just before lift-off
        ang = 0.0
        if idx + 1 < len(seq):
            nxt_t, _ = seq[idx + 1]
            pre = (nxt_t - swing) - f
            if 0 <= pre < sf * 0.25:
                ang = -self.dir * 0.35 * (1 - pre / (sf * 0.25))
        return np.array([cur_x, self.ground]), ang, False

    # ------------------------------------------------------------ public pose
    def pose(self, f: float) -> dict:
        v = self.speed(f)
        k = v / self.vmax if self.vmax else 0.0
        hx = self.hip_x(f)
        # phase within current step (0 at contact)
        last_c = None
        for t, _, _ in self.contacts:
            if t <= f:
                last_c = t
        phase = ((f - last_c) / self.step_frames) if last_c is not None else 0.0
        phase = phase % 1.0
        bob_amt = self.bob * min(1.0, k * 1.2)
        hy = self.ground - self.hip_height - (-bob_amt * math.sin(2 * math.pi * phase))
        near, near_a, near_sw = self._foot("near", f)
        far, far_a, far_sw = self._foot("far", f)
        # hip never higher than legs allow: keep hip above the feet midpoint
        arm = math.cos(math.pi * ((f - (self.contacts[0][0] if self.contacts else 0)) / self.step_frames)) * min(1.0, k * 1.1)
        accel = (self.speed(f + 0.5) - self.speed(f - 0.5))          # px/frame per frame
        acc_n = accel * self.ramp / max(self.vmax, 1e-6)               # normalised: about -1.6..1.6 on the ramps
        tilt = self.dir * (self.lean * k + max(-0.2, min(0.2, 0.12 * acc_n)))   # lean into starts, back into stops
        return {
            "hip": np.array([hx, hy]),
            "feet": {"near": (near, near_a, near_sw), "far": (far, far_a, far_sw)},
            "arm": arm,             # +1: near arm forward
            "speed": v,
            "speed_ratio": k,
            "tilt": tilt,           # radians, positive leans toward travel
            "phase": phase,
            "moving": v > 1e-3 or near_sw or far_sw,
        }

    def final_feet(self):
        """(near_x, far_x) where the feet end up - feed into the next Walk's start_feet."""
        return (self.plants["near"][-1][1], self.plants["far"][-1][1])

    def foot_slide_report(self, fps_samples: int = 4) -> float:
        """Max world-space drift (px) of any planted foot. Should be 0.0."""
        worst = 0.0
        for name in ("near", "far"):
            prev = None
            f = self.start - 2
            while f < self.end_frame + 2:
                p, _, swinging = self._foot(name, f)
                if not swinging:
                    if prev is not None:
                        worst = max(worst, abs(p[0] - prev[0]))
                    prev = p
                else:
                    prev = None
                f += 1.0 / fps_samples
        return worst
