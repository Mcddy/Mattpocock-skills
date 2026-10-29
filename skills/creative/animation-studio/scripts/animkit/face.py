"""Facial acting for BlobRig(face_rig=True): expressions, eyes that think, lip-sync merge.

Disney/Pixar practice built in:
* thought shows in the eyes first: brows and lids change 2-4 frames before the mouth
  (`ExpressionTrack(lead=...)`), the head/body follows the eyes;
* eye darts are fast (2-3 frames) with holds between (`eye_darts`), and a blink on
  big changes of thought or big head turns;
* no twinning: a small asymmetry is added to brows and mouth by default;
* one clear expression per thought, held long enough to read (8-16 frames at 24 fps),
  with a moving hold (breath, micro-darts) rather than a frozen face.

    track = ExpressionTrack([(0, "neutral"), (40, "frustrated"), (70, "idea", "snap"), (95, "joy")])
    perf = Performer(rig, walks, frames, channels={**track.channels(), **eye_darts([...])})
"""
from __future__ import annotations

from .curves import Channel, K

# brow_l/brow_r: raise (-1..1); brow_la/brow_ra: inner-end angle (+ worried/sad, - angry/determined)
# lid_top: upper-lid droop 0..1; lid_tilt: + angry (inner low), - sad (outer low)
# mouth_open 0..1, mouth_curve -1 (frown) .. 1 (smile), mouth_width 0..1, mouth_round 0..1, mouth_skew -1..1
# happy: lower-lid smile 0..1; eye_sq: eye height scale; pupil: pupil scale
FACE_DEFAULTS = dict(brow_l=0.0, brow_r=0.0, brow_la=0.0, brow_ra=0.0, lid_top=0.08, lid_tilt=0.0,
                     mouth_open=0.0, mouth_curve=0.12, mouth_width=0.5, mouth_round=0.0, mouth_skew=0.0,
                     happy=0.0, eye_sq=1.0, pupil=1.0)

EXPRESSIONS = {
    "neutral":    {},
    "curious":    dict(brow_l=0.55, brow_r=0.15, brow_la=0.15, lid_top=0.02, mouth_round=0.35, mouth_open=0.12,
                       mouth_curve=0.05, mouth_width=0.35, pupil=1.08),
    "thinking":   dict(brow_l=0.2, brow_r=-0.25, brow_la=0.1, brow_ra=-0.25, lid_top=0.3, mouth_curve=-0.1,
                       mouth_width=0.3, mouth_skew=0.6),
    "frustrated": dict(brow_l=-0.45, brow_r=-0.4, brow_la=-0.65, brow_ra=-0.6, lid_top=0.32, lid_tilt=0.45,
                       mouth_curve=-0.55, mouth_width=0.62, mouth_skew=-0.2),
    "effort":     dict(brow_l=-0.5, brow_r=-0.55, brow_la=-0.55, brow_ra=-0.6, lid_top=0.48, lid_tilt=0.35,
                       mouth_open=0.32, mouth_curve=-0.25, mouth_width=0.95),
    "determined": dict(brow_l=-0.22, brow_r=-0.2, brow_la=-0.42, brow_ra=-0.4, lid_top=0.26, lid_tilt=0.3,
                       mouth_curve=0.05, mouth_width=0.42, mouth_skew=0.25),
    "idea":       dict(brow_l=0.9, brow_r=0.85, brow_la=0.12, brow_ra=0.1, lid_top=0.0, eye_sq=1.14, pupil=1.22,
                       mouth_open=0.5, mouth_round=0.75, mouth_curve=0.15),
    "surprised":  dict(brow_l=1.0, brow_r=0.95, brow_la=0.2, brow_ra=0.2, lid_top=0.0, eye_sq=1.2, pupil=0.72,
                       mouth_open=0.7, mouth_round=0.85),
    "joy":        dict(brow_l=0.5, brow_r=0.45, brow_la=0.22, brow_ra=0.2, lid_top=0.0, happy=1.0, pupil=1.15,
                       mouth_open=0.62, mouth_curve=1.0, mouth_width=0.85),
    "content":    dict(brow_l=0.15, brow_r=0.12, lid_top=0.18, happy=0.55, mouth_curve=0.7, mouth_width=0.55),
    "sad":        dict(brow_l=0.25, brow_r=0.2, brow_la=0.75, brow_ra=0.7, lid_top=0.36, lid_tilt=-0.55,
                       mouth_curve=-0.65, mouth_width=0.42, eye_sq=0.95),
    "worried":    dict(brow_l=0.45, brow_r=0.4, brow_la=0.65, brow_ra=0.6, lid_top=0.05, mouth_curve=-0.3,
                       mouth_width=0.32, mouth_open=0.1, pupil=0.9),
    "sly":        dict(brow_l=0.4, brow_r=-0.25, brow_la=0.0, brow_ra=-0.35, lid_top=0.38, lid_tilt=0.15,
                       mouth_curve=0.55, mouth_width=0.48, mouth_skew=0.8),
    "sleepy":     dict(brow_l=-0.05, brow_r=-0.08, lid_top=0.62, mouth_open=0.08, mouth_round=0.4, mouth_curve=0.0),
}

GROUPS = {
    "brows": ("brow_l", "brow_r", "brow_la", "brow_ra"),
    "eyes": ("lid_top", "lid_tilt", "eye_sq", "pupil", "happy"),
    "mouth": ("mouth_open", "mouth_curve", "mouth_width", "mouth_round", "mouth_skew"),
}


def expression(name_or_dict, asym=0.06) -> dict:
    """Full face value set for a preset name or a dict of overrides (with a little asymmetry against twinning)."""
    base = dict(FACE_DEFAULTS)
    d = EXPRESSIONS[name_or_dict] if isinstance(name_or_dict, str) else dict(name_or_dict)
    base.update(d)
    if asym:
        base["brow_l"] += asym
        base["brow_ra"] -= asym * 0.5
        base["mouth_skew"] += asym * 0.5
    return base


def blend(a: dict, b: dict, t: float) -> dict:
    return {k: a[k] + (b[k] - a[k]) * t for k in a}


class ExpressionTrack:
    """Keyed expressions -> face Channels, with the eyes leading the mouth.

    keys: [(frame, preset_or_dict[, ease[, hold]])]. ease is the transition INTO that key
    (default 'slow_in_out'; 'snap' for a realisation). lead: frames each group starts early
    (negative) or late (positive) relative to the key; transition: frames per change.
    """

    def __init__(self, keys, lead=None, transition=6.0, asym=0.06):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.lead = {"brows": -3.0, "eyes": -2.0, "mouth": 1.0, **(lead or {})}
        self.transition = transition
        self.asym = asym

    def channels(self) -> dict:
        out = {}
        sets = [(k[0], expression(k[1], self.asym), k[2] if len(k) > 2 else "slow_in_out") for k in self.keys]
        for g, params in GROUPS.items():
            off = self.lead.get(g, 0.0)
            for p in params:
                ks = []
                prev = None
                for i, (f, vals, ease) in enumerate(sets):
                    trans = self.transition * (0.5 if ease == "snap" else 1.0)
                    start = f + off - trans
                    if prev is None:
                        ks.append(K(min(0.0, start), vals[p]))
                    else:
                        if ks and start <= ks[-1].frame:
                            start = ks[-1].frame + 0.5
                        ks.append(K(start, prev, ease))
                        ks.append(K(start + trans, vals[p]))
                    prev = vals[p]
                out[p] = Channel(ks)
        return out


def eye_darts(targets, dart_frames=2.5, start=(1.0, 0.0)):
    """[(frame, (gx, gy))] -> {'gaze_x': Channel, 'gaze_y': Channel}: fast darts, holds between.

    Real eyes don't drift: they jump (saccade) in 2-3 frames and hold. Add a blink
    when the gaze change accompanies a change of thought or a big head turn.
    """
    gx = [K(0, start[0])]
    gy = [K(0, start[1])]
    cur = start
    for f, (x, y) in sorted(targets, key=lambda t: t[0]):
        gx += [K(f, cur[0], "snap"), K(f + dart_frames, x)]
        gy += [K(f, cur[1], "snap"), K(f + dart_frames, y)]
        cur = (x, y)
    return {"gaze_x": Channel(gx), "gaze_y": Channel(gy)}
