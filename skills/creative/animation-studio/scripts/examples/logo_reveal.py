#!/usr/bin/env python3
"""LOGO REVEAL - animate a client's own SVG logo from the mark's idea, then ship every format.

The test logo (assets/sunhill_logo.svg) is fictional: a sun over a hill inside a ring, plus an
outlined wordmark. The reveal is built from what the mark depicts, not a stock template:
  frame    the sunrise plays big (the mark at twice lock-up size, centred), then the camera pulls
           back to the lock-up as the name arrives: the hero moment gets the hero scale
  ring     draws on (it frames the scene first)
  hill     the land forms: grows up from its base
  sun      rises from behind the hill, clipped to the ring (a sunrise, the mark's own story)
  letters  rise from behind the baseline in reading order, like the sun
  line     the underline draws on under the name; everything settles on the exact static logo
  hold     a moving hold: the whole lock-up drifts 1.5% larger; every part stays exactly on-model

Deliverables: MP4 with sound, transparent WebM (VP9 alpha), GIF (size budget) and a Lottie
JSON variant (no clipping masks in the Lottie exporter, so the sun scales in instead).

python3 logo_reveal.py --out logo.mp4 [--svg your_logo.svg] [--variants DIR] [--review DIR]
With --svg, read `SVGArt(path).summary()` first and re-map the parts in `ROLE` to your ids.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from animkit import audio as A                                  # noqa: E402
from animkit.canvas import Canvas, dither, vignette              # noqa: E402
from animkit.curves import Channel, K                           # noqa: E402
from animkit.easing import get as ease                          # noqa: E402
from animkit.svg import SVGArt                                  # noqa: E402
from animkit.timeline import CueSheet, mux, render, render_rgba  # noqa: E402
from animkit.vector import VPath, about, circle_vp, draw_fill, draw_stroke, mask_to, mat, trs  # noqa: E402

W, H, FPS = 1920, 1080, 30
N = 140
BG = "#F4EDE0"
ROLE = dict(ring="ring", hill="hill", sun="sun", underline="underline", letters="L")   # ids in the SVG

art = None
M = None
SCALE = 1.0
B = dict(ring=0, hill=10, sun=24, letters=48, line=66, settle=82, end=N)


def setup(svg_path):
    global art, M, SCALE
    art = SVGArt(svg_path)
    M, SCALE = art.placement(W / 2, H / 2, height=360)


def shape(id_):
    return next(s for s in art.shapes if s.id == id_)


def letters():
    return [s for s in art.shapes if s.id.startswith(ROLE["letters"])]


def _u(f, a, b, e="slow_in_out"):
    return ease(e)(min(1.0, max(0.0, (f - a) / max(1e-6, b - a))))


def tracks():
    """One set of Channels drives both the rendered video and the Lottie export (svg units, frames)."""
    t = {"ring_trim": Channel([K(0, 0.0), K(B["ring"], 0.0, "snap"), K(B["ring"] + 18, 1.0)]),
         "hill_dy": Channel([K(0, 64.0), K(B["hill"], 64.0, "snap"), K(B["hill"] + 16, 0.0)]),
         "sun_dy": Channel([K(0, 70.0), K(B["sun"], 70.0, "slow_in_out"), K(B["sun"] + 26, 0.0)]),
         "line_trim": Channel([K(0, 0.0), K(B["line"], 0.0, "snap"), K(B["line"] + 16, 1.0)]),
         "hold": Channel([K(0, 1.0), K(B["settle"], 1.0, "in_out_sine"), K(N, 1.015)]),
         "zoom": Channel([K(0, 2.0, "in_out_sine"), K(B["sun"] + 20, 1.94, "slow_in_out"), K(B["letters"] + 18, 1.0)]),
         "pull": Channel([K(0, 0.0), K(B["sun"] + 20, 0.0, "slow_in_out"), K(B["letters"] + 18, 1.0)])}
    for i in range(len(letters())):
        a0 = B["letters"] + i * 3
        t[f"letter{i}_dy"] = Channel([K(0, 74.0), K(a0, 74.0, "snap"), K(a0 + 12, 0.0)])
    return t


TR = {}


def T():
    if not TR:
        TR.update(tracks())
    return TR


def geometry(G):
    ring = shape(ROLE["ring"])
    x0, y0, w0, h0 = ring.path.transform(G).bounds()
    r_out = w0 / 2
    return x0 + r_out, y0 + h0 / 2, r_out, r_out / 8.0          # centre, outer radius, ring thickness (8 of 64 units)


def _mark_centre():
    cx, cy, _, _ = geometry(M)
    return np.array([cx, cy])


def view(f):
    """Frame transform: scale s about a focus point P that slides from the mark's centre to the frame
    centre (u: 0 -> 1). At u=1 it reduces to the moving hold about the frame centre."""
    tr = T()
    s_, u = tr["zoom"](f) * tr["hold"](f), tr["pull"](f)
    C, A = np.array([W / 2, H / 2]), _mark_centre()
    pos = C - s_ * u * (C - A)                                           # where the mark's centre lands
    return mat(e=pos[0], f=pos[1]) @ mat(s_, 0, 0, s_) @ mat(e=-A[0], f=-A[1])


def baseline_box(G):
    bs = [s.path.transform(G).bounds() for s in letters()]
    lx0, lx1 = min(b[0] for b in bs), max(b[0] + b[2] for b in bs)
    base = max(b[1] + b[3] for b in bs)
    return lx0 - 20, 0.0, lx1 - lx0 + 40, base + 1


def draw_logo(cv, f):
    tr = T()
    G = view(f) @ M                                                      # camera + moving hold on the lock-up
    sk = tr["zoom"](f) * tr["hold"](f) * SCALE                           # svg units -> px right now
    ring, hill, sun = shape(ROLE["ring"]), shape(ROLE["hill"]), shape(ROLE["sun"])
    cx, cy, r_out, thick = geometry(G)
    # the land rises into the ring, then the sun rises from behind it (both masked to the ring's centreline,
    # so their edges tuck under the ring)
    if f >= B["hill"]:
        box = (cx - r_out, cy - r_out, 2 * r_out, 2 * r_out)
        with cv.layer(bounds=box):
            if f >= B["sun"]:
                draw_fill(cv, sun.path.transform(mat(f=tr["sun_dy"](f) * sk) @ G), sun.fill)
            draw_fill(cv, hill.path.transform(mat(f=tr["hill_dy"](f) * sk) @ G), hill.fill)
            mask_to(cv, circle_vp(cx, cy, r_out - thick / 2), box)          # not blend="dst_in": see vector.mask_to
    # ring: draws on along its centreline (clockwise from the top), then the exact SVG ring takes over
    t_ring = tr["ring_trim"](f)
    if t_ring < 1.0:
        draw_stroke(cv, circle_vp(cx, cy, r_out - thick / 2), ring.fill, thick, 0.0, t_ring)
    else:
        draw_fill(cv, ring.path.transform(G), ring.fill, rule=ring.rule)
    # letters rise from behind the baseline in reading order
    if letters():
        with cv.clip_rect(*baseline_box(G)):
            for i, s in enumerate(letters()):
                dy = tr[f"letter{i}_dy"](f)
                if dy < 73.9:
                    draw_fill(cv, s.path.transform(mat(f=dy * sk) @ G), s.fill, rule=s.rule)
    # underline draws on under the name
    ul = next((s for s in art.shapes if s.id == ROLE["underline"]), None)
    if ul is not None and tr["line_trim"](f) > 0:
        draw_stroke(cv, ul.path.transform(G), ul.stroke, ul.sw * sk, 0.0, tr["line_trim"](f))


def draw(cv: Canvas, f: float):
    cv.clear(BG)
    draw_logo(cv, f)


def post(img, i):
    return dither(vignette(img, 0.08))


cues = CueSheet(FPS)


def _arrive(ch, frac=0.03):
    """First frame where a move is within `frac` of its end value (where its sound belongs)."""
    v0, v1 = ch.keys[0].value, ch.keys[-1].value
    for f in range(int(ch.keys[0].frame), int(ch.keys[-1].frame) + 1):
        if abs(ch(f) - v1) <= frac * abs(v1 - v0):
            return f
    return int(ch.keys[-1].frame)


def build_cues():
    tr = T()
    cues.add(B["ring"] + 1, "draw").add(_arrive(tr["hill_dy"]), "land").add(B["sun"] + 6, "rise")
    for i in range(len(letters())):
        cues.add(_arrive(tr[f"letter{i}_dy"]), "letter", i=i)
    cues.add(B["line"], "line")


def build_audio(path):
    dur = N / FPS + 1.0
    m = A.Mix(dur)
    for k, c in enumerate(cues.cues):
        t = c["t"]
        if c["kind"] == "draw":
            m.add(A.filt(A.noise(0.55, "pink", k), "bp", (900, 5000)) * np.linspace(0, 1, int(0.55 * A.SR)) ** 2, t, -30)
        elif c["kind"] == "land":
            m.add(A.thump(seed=k, pitch=0.7), t, -18)
        elif c["kind"] == "rise":
            m.add(A.pad([A.hz("D3"), A.hz("A3"), A.hz("F#4")], 2.6, attack=0.9, release=1.2, bright=0.3), t, -20, bus="music")
        elif c["kind"] == "letter":
            notes = ["D5", "E5", "F#5", "A5", "B5", "D6", "E6"]
            m.add(A.karplus(A.hz(notes[c["i"] % len(notes)]), 0.7, seed=k, bright=0.35) * 0.7, t, -21,
                  (c["i"] - 3) * 0.12, bus="music")
        elif c["kind"] == "line":
            m.add(A.filt(A.noise(0.5, "pink", k), "bp", (1500, 6000)) * np.linspace(1, 0, int(0.5 * A.SR)) ** 2, t, -26)
    m.process("music", lambda s: A.reverb(s, 0.25, 1.8, 0.02))
    return A.master(m.render(), path, target_lufs=-16.0)


def variants(out_dir):
    """Transparent WebM, GIF and a Lottie JSON variant of the same reveal."""
    from animkit import deliver as D
    from animkit.web import Lottie
    os.makedirs(out_dir, exist_ok=True)
    seq = render_rgba(lambda cv, f: draw_logo(cv, f), N, os.path.join(out_dir, "alpha_seq"), w=W, h=H, mb_samples=1)
    res = {"webm_alpha": D.webm_alpha(seq["pattern"], os.path.join(out_dir, "logo_alpha.webm"), fps=FPS)}
    # Lottie variant: same Channels, same masks (layer masks), a null parent carries the moving hold
    tr = T()
    doc = Lottie(W, H, FPS, N)
    k = SCALE

    def px(ch, scale):                                     # Channel in svg units -> Channel in px
        return Channel([K(kk.frame, kk.value * scale, kk.ease) for kk in ch.keys])
    A_ = _mark_centre()
    sc_keys, x_keys, y_keys = [], [], []
    for f in range(N + 1):                                # camera + hold baked per frame (exact match)
        Vf = view(f)
        sc_keys.append(K(f, float(Vf[0, 0]), "linear"))
        x_keys.append(K(f, float(Vf[0, 2] + Vf[0, 0] * A_[0] - A_[0]), "linear"))
        y_keys.append(K(f, float(Vf[1, 2] + Vf[1, 1] * A_[1] - A_[1]), "linear"))
    hold = doc.null_layer("camera", anchor=tuple(A_), position=tuple(A_),
                          tracks={"scale": Channel(sc_keys), "x": Channel(x_keys), "y": Channel(y_keys)})
    cx, cy, r_out, thick = geometry(M)
    bowl = circle_vp(cx, cy, r_out - thick / 2)
    for s_ in art.shapes:
        vp = s_.path.transform(M)
        item = [(vp, s_.fill, s_.stroke, s_.sw * k, s_.rule)]
        c = vp.centre()
        if s_.id == ROLE["sun"]:
            doc.layer_from_vpaths("sun", item, anchor=c, position=c, tracks={"y": px(tr["sun_dy"], k)},
                                  mask=bowl, start=B["sun"], parent=hold)
        elif s_.id == ROLE["hill"]:
            doc.layer_from_vpaths("hill", item, anchor=c, position=c, tracks={"y": px(tr["hill_dy"], k)},
                                  mask=bowl, start=B["hill"], parent=hold)
        elif s_.id == ROLE["ring"]:
            doc.layer_from_vpaths("ring draw-on", [(bowl, None, s_.fill, thick)], trim=tr["ring_trim"],
                                  end=B["ring"] + 18, parent=hold)
            doc.layer_from_vpaths("ring", item, start=B["ring"] + 18, parent=hold)
        elif s_.id.startswith(ROLE["letters"]):
            i = int(s_.id[len(ROLE["letters"]):].split("_")[0])
            x, y, w, h = baseline_box(M)
            doc.layer_from_vpaths(s_.id, item, anchor=c, position=c, tracks={"y": px(tr[f"letter{i}_dy"], k)},
                                  mask=VPath().moveTo(x, y).lineTo(x + w, y).lineTo(x + w, y + h).lineTo(x, y + h).close(),
                                  parent=hold)
        elif s_.id == ROLE["underline"]:
            doc.layer_from_vpaths("underline", item, trim=tr["line_trim"], parent=hold)
    res["lottie"] = doc.save(os.path.join(out_dir, "logo.json"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--svg", default=os.path.join(HERE, "assets", "sunhill_logo.svg"))
    ap.add_argument("--variants", default=None)
    ap.add_argument("--review", default=None)
    a = ap.parse_args()
    setup(a.svg)
    print(art.summary().splitlines()[0])
    if a.review:
        from animkit import review as R
        print(R.beat_stills(draw, {k: v for k, v in B.items() if k != "end"} | {"mid_sun": B["sun"] + 13, "mid_letters": B["letters"] + 9},
                            a.review, W, H, post=post))
        return
    build_cues()
    silent = os.path.splitext(a.out)[0] + "_silent.mp4"
    print(render(draw, N, silent, w=W, h=H, fps=FPS, mb_samples=2, post=post))
    wav = os.path.splitext(a.out)[0] + ".wav"
    print("loudness", build_audio(wav))
    cues.save(os.path.splitext(a.out)[0] + "_cues.json")
    mux(silent, wav, a.out)
    if a.variants:
        from animkit import deliver as D
        print(variants(a.variants))
        print(D.gif(a.out, os.path.join(a.variants, "logo.gif"), fps=15, width=720, max_mb=4))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
