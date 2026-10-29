"""In-scene review helpers: check the work before spending render time on it.

beat_stills()      render one still per named beat (blocking review) + a labelled grid
stepped_preview()  an animatic-speed preview straight from the draw function
subject_strip()    character-tracked filmstrip rendered from the draw function
on_screen()        is a world-space subject inside the camera's safe area at frame f?
framing_report()   scan a frame range for subjects leaving the safe area
reach_report()     can two-bone limbs actually reach their targets? (IK clamps hide this)

These are the checks that caught real defects while building the reference shots:
characters too small in frame, a push-in that cropped the subject, a reach target the
arm could not hit, arms attached inside the face.
"""
from __future__ import annotations

import math
import os
from typing import Callable, Iterable, Sequence

import numpy as np

from .canvas import Canvas


def _font(size=18):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def beat_stills(draw: Callable[[Canvas, float], None], beats: dict, out_dir: str, w=1920, h=1080,
                post=None, cols=3, thumb=640) -> str:
    """Render a still at every beat frame; returns the path of a labelled grid image."""
    from PIL import Image, ImageDraw
    os.makedirs(out_dir, exist_ok=True)
    items = sorted(((float(v), k) for k, v in beats.items() if v is not None), key=lambda kv: kv[0])
    tiles = []
    for f, name in items:
        cv = Canvas(w, h)
        draw(cv, f)
        img = cv.array()
        if post:
            img = post(img, int(f))
        im = Image.fromarray(img)
        im.save(os.path.join(out_dir, f"beat_{int(f):05d}_{name}.png"))
        t = im.resize((thumb, int(thumb * h / w)))
        d = ImageDraw.Draw(t)
        d.rectangle([0, 0, thumb, 26], fill=(0, 0, 0))
        d.text((6, 4), f"f{f:.0f}  {name}", fill=(255, 255, 255), font=_font(16))
        tiles.append(t)
    th = tiles[0].size[1]
    rows = math.ceil(len(tiles) / cols)
    grid = Image.new("RGB", (cols * thumb, rows * th), (12, 12, 14))
    for i, t in enumerate(tiles):
        grid.paste(t, ((i % cols) * thumb, (i // cols) * th))
    p = os.path.join(out_dir, "beats_grid.png")
    grid.save(p)
    return p


def subject_strip(draw, frames: Iterable[float], locate: Callable[[float], Sequence[float]], out_png: str,
                  w=1920, h=1080, crop=(360, 420), cols=8, post=None) -> str:
    """Filmstrip rendered directly from the scene, cropped around locate(f) -> (x, y) screen px."""
    from PIL import Image, ImageDraw
    tiles = []
    cw, ch = crop
    for f in frames:
        cv = Canvas(w, h)
        draw(cv, f)
        img = cv.array()
        if post:
            img = post(img, int(f))
        x, y = locate(f)
        x0 = int(max(0, min(w - cw, x - cw / 2)))
        y0 = int(max(0, min(h - ch, y - ch * 0.55)))
        t = Image.fromarray(img[y0:y0 + ch, x0:x0 + cw])
        d = ImageDraw.Draw(t)
        d.rectangle([0, 0, 64, 22], fill=(0, 0, 0))
        d.text((5, 3), f"f{f:.0f}", fill=(255, 255, 255), font=_font(15))
        tiles.append(t)
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * cw, rows * ch), (12, 12, 14))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * cw, (i // cols) * ch))
    sheet.save(out_png)
    return out_png


def on_screen(cam, f: float, pts: Sequence[Sequence[float]], w=1920, h=1080, margin=0.05, depth=1.0) -> dict:
    """Project world points through an animkit Camera; report whether all are inside the safe area."""
    xs, ys = [], []
    for p in pts:
        sx, sy = cam.to_screen(f, p[0], p[1], depth)
        xs.append(sx)
        ys.append(sy)
    mx, my = w * margin, h * margin
    inside = min(xs) >= mx and max(xs) <= w - mx and min(ys) >= my and max(ys) <= h - my
    height_frac = (max(ys) - min(ys)) / h
    return {"inside": inside, "x": (min(xs), max(xs)), "y": (min(ys), max(ys)), "height_frac": height_frac}


def framing_report(cam, frames: Iterable[float], subject_pts: Callable[[float], Sequence], w=1920, h=1080,
                   margin=0.05, min_height=0.0, exits_ok: Iterable[tuple] = ()) -> list:
    """List frames where the subject leaves the safe area or reads too small.

    exits_ok: (start, end) frame spans where leaving frame is intended (entrances/exits).
    """
    bad = []
    for f in frames:
        if any(a <= f <= b for a, b in exits_ok):
            continue
        r = on_screen(cam, f, subject_pts(f), w, h, margin)
        if not r["inside"] or r["height_frac"] < min_height:
            bad.append((f, r))
    return bad


def reach_report(pairs: Iterable[tuple], l1: float, l2: float, tol=0.5) -> list:
    """pairs: (frame, root_xy, target_xy). Returns frames where the target is out of reach.

    two_bone_ik silently clamps, so an unreachable target looks like a hand that
    stops short of the prop. Check this before rendering any contact beat.
    """
    out = []
    for f, root, target in pairs:
        d = float(np.linalg.norm(np.asarray(target, float) - np.asarray(root, float)))
        if d > l1 + l2 + tol:
            out.append((f, round(d - (l1 + l2), 1)))
    return out
