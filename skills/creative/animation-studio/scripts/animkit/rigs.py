"""Reusable 2-D character rig: a round 'blob' body with a face that acts.

Extracted from the doorstep reference shot so new jobs start from a rig that already
obeys the rules: arms hang from the silhouette edge, the face slides for 2-D turns,
eyes lead with gaze, blinks and happy cheeks, hood/antenna tip with overlapping
action, a bag with secondary swing, legs with two-bone IK on locked feet, and
lighting by albedo x light plus a src_atop key/rim (it sits in the scene's light).

Usage
-----
    rig = BlobRig(RigStyle(coat="#3FA7A0"))                    # restyle freely
    perf = Performer(rig, walks=[Walk(...)], frames=range(0, 240),
                     channels=dict(facing=Channel(...), gaze_y=Channel(...), ...),
                     blinks=[30, 95])
    def draw(cv, f):
        ...background...
        rig.draw(cv, perf.pose(f), light=Light(ambient=(0.65, 0.68, 0.86), key_dir=1, key_col="#FFD38A", key=0.3))

Channels (all optional; defaults in Performer.DEFAULTS): facing (-1..1), body_dx (px, hip offset: jumps, shoves), body_dy (px, +down: crouch/dip; negative lifts the body and tucks the feet when < -2),
squash (sy), lean (rad), gaze_x, gaze_y (-1..1), eye_open (1 = normal), happy (0..1),
near_hand, far_hand ((dx, dy) from the shoulder, facing-right space), near_stretch, far_stretch (limb
stretch for reaches, 1 = rest; limbs thin to keep volume).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from .canvas import mix, rgba
from .curves import Channel, K
from .principles import baked, blink, breathe, lag_chain, simulate_positional, two_bone_ik


@dataclass
class RigStyle:
    body_rx: float = 52.0
    body_ry: float = 66.0
    thigh: float = 42.0
    shin: float = 42.0
    upper: float = 30.0
    fore: float = 30.0
    hip_height: float = 74.0
    coat: str = "#E2A63A"
    coat_shade: str = "#B47A22"
    coat_hi: str = "#F6CB6B"
    face: str = "#18202E"
    eye: str = "#F4F1EA"
    pupil: str = "#0D1119"
    limb_far: str = "#2C3240"
    limb_near: str = "#3F4658"
    hood: bool = True
    hood_segments: int = 3
    bag: bool = True
    bag_col: str = "#7A3A2C"
    strap_col: str = "#5A2A22"
    buttons: bool = True
    wobble: float = 0.012
    seed: int = 3
    face_rig: bool = False         # brows, shaped lids, mouth, pupils (see animkit.face); off keeps the classic visor
    brow_col: str | None = None    # default: eye colour
    mouth_col: str | None = None   # default: eye colour
    mouth_in: str = "#4A1E2C"
    tongue: str = "#C4566A"


@dataclass
class Light:
    """Lighting environment for the rig. Colours are multiplied into the albedo."""
    ambient: Sequence[float] = (1.0, 1.0, 1.0)
    key_col: str = "#FFFFFF"
    key: float = 0.0             # src_atop key strength (0..1)
    key_dir: float = 1.0         # +1 key from screen right, -1 from left
    warm_add: Sequence[float] = (0.0, 0.0, 0.0)   # added to ambient (e.g. a nearby practical)
    rim_col: str = "#BFE0EE"
    rim: float = 0.0             # cool top light strength (0..1)

    def lit(self, col, extra=0.0):
        c = rgba(col)
        m = np.asarray(self.ambient, float) + np.asarray(self.warm_add, float) + extra
        return (min(1, c.fR * m[0]), min(1, c.fG * m[1]), min(1, c.fB * m[2]), c.fA)


@dataclass
class Pose:
    hip: np.ndarray
    facing: float = 1.0
    squash: float = 1.0
    lean: float = 0.0
    gaze: tuple = (1.0, 0.0)
    eye_open: float = 1.0
    lid: float = 0.0
    happy: float = 0.0
    near_hand: tuple | None = (2.0, 44.0)
    far_hand: tuple | None = (-6.0, 44.0)
    feet: dict = field(default_factory=dict)      # name -> (pos, angle)
    airborne: bool = False
    arm_swing: float = 0.0
    hood: Sequence[float] = (0.0, 0.0, 0.0)
    hood_off: Sequence[float] = (0.0, 0.0)
    bag_off: Sequence[float] = (0.0, 0.0)
    prop: Callable | None = None                  # prop(cv, hand_xy, facing_sign) drawn in the near hand
    face: dict = field(default_factory=dict)      # face_rig values (animkit.face.FACE_DEFAULTS keys)
    near_stretch: float = 1.0                     # cartoon limb stretch (reaches); limbs thin to keep volume
    far_stretch: float = 1.0


class BlobRig:
    def __init__(self, style: RigStyle | None = None):
        self.s = style or RigStyle()

    # geometry shared by drawing and review checks
    def centre(self, p: Pose):
        return p.hip + np.array([math.sin(p.lean) * 56, -math.cos(p.lean) * 56 * p.squash])

    def shoulder(self, p: Pose, side: int):
        """Shoulder joint in world space. It rotates with the body's lean, so a character leaning into
        a push keeps its arms attached below the face instead of the face swinging down over them."""
        fs = 1.0 if p.facing >= 0 else -1.0
        ox, oy = side * 36 * fs / p.squash, 10 * p.squash
        c, s_ = math.cos(p.lean), math.sin(p.lean)
        return self.centre(p) + np.array([ox * c - oy * s_, ox * s_ + oy * c])

    def hand_target(self, p: Pose, side: int):
        off = p.near_hand if side > 0 else p.far_hand
        fs = 1.0 if p.facing >= 0 else -1.0
        o = np.array(off, float)
        o[0] *= fs
        return self.shoulder(p, side) + o + np.array([p.arm_swing * 14 * side * fs, 0])

    def bbox(self, p: Pose, ground: float):
        x, y = p.hip
        return [(x - 70, y - 56 - self.s.body_ry - 30), (x + 70, y - 56 - self.s.body_ry - 30),
                (x - 70, ground + 8), (x + 70, ground + 8)]

    def draw(self, cv, p: Pose, light: Light | None = None, ground: float | None = None, shadow=True):
        s = self.s
        L = light or Light()
        fx = p.facing
        fs = 1.0 if fx >= 0 else -1.0
        sy = p.squash
        sx = 1.0 / sy
        hip = np.asarray(p.hip, float)
        C = self.centre(p)
        if shadow and ground is not None:
            lift = max(0.0, ground - s.hip_height - hip[1])
            cv.shadow(hip[0], ground + 4, 58 - lift * 0.35, 9 - lift * 0.05, alpha=max(0.1, 0.5 - lift * 0.004), blur=5)
        # far arm
        fsh = self.shoulder(p, -1)
        k_f = max(0.5, p.far_stretch)
        fe, fh = two_bone_ik(fsh, self.hand_target(p, -1), s.upper * k_f, s.fore * k_f, bend_dir=fs)
        for a_, b_, w_ in ((fsh, fe, 15), (fe, fh, 14)):
            cv.line(a_, b_, L.lit(s.coat_shade), w_ / math.sqrt(k_f))
        cv.circle(fh[0], fh[1], 9, L.lit(s.coat_shade))
        # legs
        for name, side in (("far", -1), ("near", 1)):
            fp, fa = p.feet.get(name, (hip + np.array([side * 8 * fs, s.thigh + s.shin - 6]), 0.0))
            foot = np.asarray(fp, float)
            if p.airborne:
                foot = hip + np.array([side * 8 * fs, s.thigh + s.shin - 18])
                fa = 0.0
            root = hip + np.array([side * 9 * fs, 0])
            knee, end = two_bone_ik(root, foot, s.thigh, s.shin, bend_dir=-fs)
            col = L.lit(s.limb_far if name == "far" else s.limb_near, 0.0 if name == "far" else 0.06)
            cv.line(root, knee, col, 15)
            cv.line(knee, end, col, 14)
            with cv.at(end[0], end[1], fa):
                cv.rect(-12 + 6 * fs, -9, 30, 15, col, r=7)
        bpos = hip + np.array([16 * fs, -2]) + np.array([p.bag_off[0] * 0.8, max(-10, p.bag_off[1] * 0.5)])
        # body layer (so key/rim can be applied with src_atop)
        with cv.layer(bounds=(C[0] - 170, C[1] - 200, 340, 360)):
            with cv.at(C[0], C[1], p.lean, sx, sy):
                cv.blob(0, 0, s.body_rx, s.body_ry, fill=L.lit(s.coat), wobble=s.wobble, seed=s.seed)
                if s.hood:
                    base = np.array([-12 * fs, -s.body_ry + 10])
                    pts = [base]
                    dirn = -math.pi / 2 - 0.6 * fs
                    for i, aa in enumerate(list(p.hood)[: s.hood_segments]):
                        dirn += aa * (1.0 + 0.5 * i) - p.hood_off[0] * 0.005 * fs + p.hood_off[1] * 0.004 * fs
                        seg = 22 - 5 * i
                        pts.append(pts[-1] + np.array([math.cos(dirn) * seg, math.sin(dirn) * seg]))
                    tip = [(base[0] - 20 * fs, base[1] + 16)] + [tuple(q) for q in pts[1:]] + [(base[0] + 22 * fs, base[1] + 4)]
                    cv.poly(tip, L.lit(s.coat))
                    cv.circle(pts[-1][0], pts[-1][1], 4.5, L.lit(s.coat))
                cv.ellipse(0, s.body_ry * 0.55, s.body_rx * 0.95, s.body_ry * 0.45, L.lit(s.coat_shade), alpha=0.6, blur=8)
                cv.ellipse(-10 * fs, -s.body_ry * 0.5, s.body_rx * 0.55, s.body_ry * 0.26, L.lit(s.coat_hi), alpha=0.3, blur=10)
                cv.line((-s.body_rx * 0.8, s.body_ry * 0.62), (s.body_rx * 0.8, s.body_ry * 0.62), L.lit(s.coat_shade), 3, alpha=0.8)
                if s.bag:
                    loc = np.array([(bpos[0] - C[0]) / sx, (bpos[1] - C[1]) / sy])
                    ca, sa = math.cos(-p.lean), math.sin(-p.lean)
                    loc = np.array([loc[0] * ca - loc[1] * sa, loc[0] * sa + loc[1] * ca])
                    cv.line((-30 * fs, -36), (loc[0], loc[1] - 4), L.lit(s.strap_col), 5)
                if s.buttons:
                    for by in (14, 32):
                        cv.circle(10 * fx, by, 3.5, L.lit(s.coat_shade))
                # face slides across the body for 2-D turns; eyes act
                if s.face_rig:
                    self._draw_face_rig(cv, p, L, fx, fs)
                else:
                    self._draw_classic_face(cv, p, L, fx, fs)
                if L.key > 0:
                    g = cv.linear((L.key_dir * s.body_rx * 0.9, -s.body_ry), (-L.key_dir * s.body_rx * 0.5, s.body_ry * 0.5),
                                  [L.key_col + "AA", L.key_col + "00"])
                    cv.rect(-s.body_rx * 2, -s.body_ry * 2, s.body_rx * 4, s.body_ry * 4, g, alpha=L.key, blend="src_atop")
                if L.rim > 0:
                    g2 = cv.linear((0, -s.body_ry), (0, 0), [L.rim_col + "99", L.rim_col + "00"])
                    cv.rect(-s.body_rx * 2, -s.body_ry * 2, s.body_rx * 4, s.body_ry * 4, g2, alpha=L.rim, blend="src_atop")
        if s.bag:
            with cv.at(bpos[0], bpos[1], -p.bag_off[0] * 0.012):
                cv.rect(-21, -6, 42, 32, L.lit(s.bag_col), r=6)
                cv.rect(-21, -6, 42, 13, L.lit(s.strap_col), r=5)
        nsh = self.shoulder(p, 1)
        k_n = max(0.5, p.near_stretch)
        ne, nh = two_bone_ik(nsh, self.hand_target(p, 1), s.upper * k_n, s.fore * k_n, bend_dir=fs)
        if p.prop:
            p.prop(cv, nh, fs)
        arm = L.lit(s.coat, 0.05)
        cv.line(nsh, ne, arm, 15 / math.sqrt(k_n))
        cv.line(ne, nh, arm, 14 / math.sqrt(k_n))
        cv.circle(nh[0], nh[1], 10, arm)
        return {"hand": nh, "shoulder": nsh, "centre": C}

    def _eye_colour(self, L):
        lit_amt = max(0.0, min(1.0, L.key))
        return mix(mix(self.s.eye, "#9FB0C8", 0.35 * (1 - min(1, sum(L.ambient) / 3))), "#FFF2DC", lit_amt * 0.8), lit_amt

    def _draw_classic_face(self, cv, p, L, fx, fs):
        s = self.s
        fxo = 18 * fx
        frx = 35 * (1 - 0.2 * abs(fx))
        gx, gy = p.gaze
        fy = -26 + gy * 4
        cv.ellipse(fxo, fy, frx, 29, s.face)
        eye_col, lit_amt = self._eye_colour(L)
        for ex in (-12.5, 12.5):
            exx = fxo + ex * (1 - 0.25 * abs(fx)) + 3 * fx
            ey = fy + 1
            ry = 11.0 * min(p.eye_open, 1.25) * (1 - p.lid * 0.92)
            rx = 8.8 * (1 - 0.15 * abs(fx))
            if ry > 0.6:
                cv.ellipse(exx, ey, rx, ry, eye_col)
                px = exx + gx * 3.0 * fs
                py = ey + gy * 3.6
                cv.circle(px, py, 5.0 * min(p.eye_open, 1.1), s.pupil)
                cv.circle(px + 2.0 * L.key_dir, py - 2.2, 1.6, mix("#C9D8EA", "#FFE7BE", lit_amt))
                if p.happy > 0:
                    cv.ellipse(exx, ey + ry + 3 - p.happy * 7, rx + 2.5, 6, s.face)
                if p.lid > 0:
                    cv.line((exx - rx, ey - ry + 1), (exx + rx, ey - ry + 1), s.face, 2)

    def _draw_face_rig(self, cv, p, L, fx, fs):
        """Visor face with brows, shaped upper lids, smile lids, pupils and a mouth (animkit.face values)."""
        from .face import FACE_DEFAULTS
        s = self.s
        F = {**FACE_DEFAULTS, **(p.face or {})}
        fxo = 18 * fx
        frx = 37 * (1 - 0.2 * abs(fx))
        gx, gy = p.gaze
        fy = -24 + gy * 3
        cv.ellipse(fxo, fy, frx, 33, s.face)
        eye_col, lit_amt = self._eye_colour(L)
        brow_col = s.brow_col or eye_col
        mouth_col = s.mouth_col or eye_col
        ey = fy - 6
        happy = max(F["happy"], p.happy)
        for side, ex in ((-1, -12.5), (1, 12.5)):            # side -1: screen-left eye
            exx = fxo + ex * (1 - 0.25 * abs(fx)) + 3 * fx
            rx = 8.6 * (1 - 0.15 * abs(fx))
            ry0 = 10.5 * F["eye_sq"]
            ry = ry0 * min(p.eye_open, 1.25) * (1 - p.lid * 0.92)
            inner = -side                                    # x direction of the eye's inner corner
            if ry > 0.6:
                cv.ellipse(exx, ey, rx, ry, eye_col)
                px = exx + gx * 3.0 * fs
                py = ey + gy * 3.4
                pr = 4.8 * min(p.eye_open, 1.1) * F["pupil"]
                cv.circle(px, py, pr, s.pupil)
                cv.circle(px + 1.8 * L.key_dir, py - 2.0, 1.4 + 0.3 * F["pupil"], mix("#C9D8EA", "#FFE7BE", lit_amt))
                lt, tilt = F["lid_top"], F["lid_tilt"]
                if lt > 0.01 or abs(tilt) > 0.01:
                    base = ey - ry + 2 * ry * lt
                    y_in = base + tilt * ry * 0.55
                    y_out = base - tilt * ry * 0.55
                    xi, xo = exx + inner * (rx + 3), exx - inner * (rx + 3)
                    cv.poly([(xo, ey - ry - 5), (xi, ey - ry - 5), (xi, y_in), (xo, y_out)], s.face)
                if happy > 0:
                    cv.ellipse(exx, ey + ry + 3 - happy * 7, rx + 2.5, 6, s.face)
            by = ey - ry0 - 5.5 - F["brow_l" if side < 0 else "brow_r"] * 4.5
            ang = F["brow_la" if side < 0 else "brow_ra"]
            hl = rx * 0.95
            pin = (exx + inner * hl, by - ang * 5.5)
            pout = (exx - inner * hl, by + ang * 2.5 + 1)
            cv.polyline(_quad_pts(pout, ((pin[0] + pout[0]) / 2, (pin[1] + pout[1]) / 2 - 3.2), pin, 8), brow_col, 4.6,
                        smooth=False)
        self._mouth(cv, fxo + 2 * fx, fy + 16, F, mouth_col)

    def _mouth(self, cv, mx, my, F, col):
        s = self.s
        o = max(0.0, min(1.0, F["mouth_open"]))
        c = max(-1.0, min(1.0, F["mouth_curve"]))
        r = max(0.0, min(1.0, F["mouth_round"]))
        sk = F["mouth_skew"]
        w = (6.0 + 9.0 * F["mouth_width"]) * (1 - 0.5 * r)
        lc = (mx - w, my - c * 3.4 - sk * 1.8)
        rc = (mx + w, my - c * 3.4 + sk * 1.8)
        h = o * 10.5 + r * o * 2.5
        if h < 1.2:
            cv.polyline(_quad_pts(lc, (mx + sk * 1.2, my + c * 3.4), rc, 10), col, 3.0, smooth=False)
            return
        upper = _quad_pts(lc, (mx + sk, my - h * 0.3 + c * 1.0 - r * h * 0.3), rc, 12)
        lower = _quad_pts(rc, (mx + sk, my + h * 1.15 + c * 2.0), lc, 12)
        shape = upper + lower[1:]
        cv.poly(shape, s.mouth_in)
        if o > 0.35:
            cv.ellipse(mx + sk, my + h * 0.55, w * 0.5, max(1.0, h * 0.24), s.tongue)
        cv.poly(shape, None, stroke=col, sw=2.6)


def _quad_pts(a, c, b, n=10):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
                    (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]))
    return out


class Performer:
    """Turns channels + walks into Poses, with springs for hood and bag baked over `frames`."""

    DEFAULTS = dict(facing=1.0, body_dy=0.0, body_dx=0.0, squash=1.0, lean=0.0, gaze_x=1.0, gaze_y=0.0, eye_open=1.0,
                    happy=0.0, near_hand=(2.0, 44.0), far_hand=(-6.0, 44.0), near_stretch=1.0, far_stretch=1.0)

    def __init__(self, rig: BlobRig, walks: Sequence, frames, channels: dict | None = None, blinks=(), fps=24.0,
                 breathe_amt=0.012):
        self.rig, self.fps = rig, fps
        # walks: Walk objects (active from their own start) or (from_frame, Walk) to switch on a stationary
        # walk at a chosen frame (e.g. standing on a crate after a jump: ground changes at the landing frame)
        self.walks = [(w[0], w[1]) if isinstance(w, tuple) else (w.start, w) for w in walks]
        self.ch = {k: (v if isinstance(v, Channel) else Channel([K(0, v)])) for k, v in self.DEFAULTS.items()}
        for k, v in (channels or {}).items():
            self.ch[k] = v if isinstance(v, Channel) else Channel([K(0, v)])
        from .face import FACE_DEFAULTS
        self.face_keys = [k for k in FACE_DEFAULTS if k in self.ch or k in (channels or {})]
        for k, v in FACE_DEFAULTS.items():
            self.ch.setdefault(k, Channel([K(0, v)]))
        self.face_keys = list(FACE_DEFAULTS)
        self.blinks = list(blinks)
        self.breathe_amt = breathe_amt
        grid = np.arange(min(frames) - 24, max(frames) + 2, 0.25)
        hood = lag_chain(lambda f: self.ch["lean"](f) + self._walk(f).pose(f)["tilt"], grid, n=3,
                         stiffness=(150, 110, 80), damping=0.22, gain=1.4)
        self._hood = baked(hood)
        self._hood_off = baked(simulate_positional(lambda f: (self._walk(f).pose(f)["hip"][0] + self.ch["body_dx"](f),
                                                              self.ch["body_dy"](f)), grid,
                                                   stiffness=120, damping=0.25))
        self._bag = baked(simulate_positional(lambda f: tuple(self._walk(f).pose(f)["hip"] + np.array([self.ch["body_dx"](f), self.ch["body_dy"](f)])),
                                              grid, stiffness=95, damping=0.2))

    def _walk(self, f):
        cur = self.walks[0][1]
        for frm, w in self.walks:
            if f >= frm:
                cur = w
        return cur

    def pose(self, f) -> Pose:
        w = self._walk(f)
        wp = w.pose(f)
        c = {k: ch(f) for k, ch in self.ch.items()}
        hip = np.array([wp["hip"][0] + float(c["body_dx"]), wp["hip"][1] + float(c["body_dy"])])
        feet = {k: (v[0], v[1]) for k, v in wp["feet"].items()}
        face = {k: float(c[k]) for k in self.face_keys}
        if "lip_open" in self.ch:                      # lip sync (animkit.lipsync) layered over the expression
            lo = float(c["lip_open"])
            if lo > 0.02:
                face["mouth_open"] = max(face["mouth_open"], lo)
                k = min(1.0, lo / 0.25)
                face["mouth_round"] = face["mouth_round"] * (1 - k) + float(c.get("lip_round", 0.0)) * k
                face["mouth_width"] = face["mouth_width"] * (1 - k) + float(c.get("lip_width", 0.5)) * k
        return Pose(face=face,hip=hip, facing=float(c["facing"]), squash=float(c["squash"]) * breathe(f, self.fps, 0.3, self.breathe_amt),
                    lean=float(c["lean"]) + wp["tilt"] * 0.8, gaze=(float(c["gaze_x"]), float(c["gaze_y"])),
                    eye_open=float(c["eye_open"]), lid=blink(f, self.blinks), happy=float(c["happy"]),
                    near_hand=tuple(c["near_hand"]), far_hand=tuple(c["far_hand"]), feet=feet,
                    airborne=float(c["body_dy"]) < -2, arm_swing=wp["arm"] if wp["moving"] else 0.0,
                    hood=tuple(self._hood(f)), hood_off=tuple(self._hood_off(f)), bag_off=tuple(self._bag(f)))
