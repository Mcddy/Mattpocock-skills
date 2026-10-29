#!/usr/bin/env python3
"""filmstrip - frame-by-frame review strips, the way an animation supervisor checks spacing.

A contact sheet shows rhythm; a filmstrip shows *animation*: every 2nd or 3rd frame
of one beat, cropped tight on the subject, labelled with frame numbers. This is how
pops, skating feet, limbs crossing the face, floating props and dead holds are found.

Usage
  python3 filmstrip.py VIDEO --ranges 20:52:2 84:130:3 --out DIR
        [--track auto | color:#E2A63A | box:x,y,w,h] [--crop 360x420] [--cols 8]

  --ranges  start:end:step in frames (inclusive start, exclusive end); one strip per range
  --track   auto   = follow the most saturated blob (good for a hero colour); after the first
                     frame the search stays near the last position (pass --seed x,y to start)
            color  = follow pixels near a hex colour (tolerance --tol, default 60)
            box    = fixed crop (x,y,w,h in source pixels)
            none   = full frame scaled down
Outputs strip_<start>_<end>.png per range and prints their paths.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    w, h = out.strip().split(",")[:2]
    return int(w), int(h)


def frames(path, a, b, step, w, h):
    sel = f"select='between(n\\,{a}\\,{b - 1})*not(mod(n-{a}\\,{step}))'"
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf", sel, "-vsync", "vfr",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    arr = np.frombuffer(raw, np.uint8)
    n = arr.size // (w * h * 3)
    return arr[: n * w * h * 3].reshape(n, h, w, 3)


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def centre(im, mode, tol, last, radius=None):
    """Subject centre. With `radius`, search only near the last position, so a
    similar-coloured object elsewhere (a lit window, a lamp) can't steal the track."""
    if mode == "auto":
        f = im.astype(int)
        mx, mn = f.max(2), f.min(2)
        sat = (mx - mn) / (mx + 1)
        m = (sat > 0.45) & (mx > 90)
    elif mode.startswith("color:"):
        d = np.abs(im.astype(float) - hex_rgb(mode[6:])).sum(2)
        m = d < tol
    else:
        return last
    if radius is not None and last is not None:
        h, w = m.shape
        x0, x1 = max(0, last[0] - radius[0]), min(w, last[0] + radius[0])
        y0, y1 = max(0, last[1] - radius[1]), min(h, last[1] + radius[1])
        ys, xs = np.nonzero(m[y0:y1, x0:x1])
        if len(xs) >= 40:
            return int(np.median(xs)) + x0, int(np.median(ys)) + y0
        return last
    ys, xs = np.nonzero(m)
    if len(xs) < 40:
        return last
    return int(np.median(xs)), int(np.median(ys))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--ranges", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--track", default="auto")
    ap.add_argument("--tol", type=float, default=60)
    ap.add_argument("--crop", default="360x420")
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--seed", default=None, help="x,y of the subject in the first frame (else found globally)")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    W, H = probe(a.video)
    cw, ch = map(int, a.crop.split("x"))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    outs = []
    for r in a.ranges:
        s, e, st = (list(map(int, r.split(":"))) + [1])[:3]
        arr = frames(a.video, s, e, st, W, H)
        tiles = []
        last = tuple(map(int, a.seed.split(","))) if a.seed else None
        for k, im in enumerate(arr):
            if a.track == "none":
                t = Image.fromarray(im).resize((cw, int(cw * H / W)))
            elif a.track.startswith("box:"):
                x, y, bw, bh = map(int, a.track[4:].split(","))
                t = Image.fromarray(im[y:y + bh, x:x + bw]).resize((cw, ch))
            else:
                last = centre(im, a.track, a.tol, last, None if last is None else (cw, ch)) or (W // 2, H // 2)
                x0 = max(0, min(W - cw, last[0] - cw // 2))
                y0 = max(0, min(H - ch, last[1] - int(ch * 0.55)))
                t = Image.fromarray(im[y0:y0 + ch, x0:x0 + cw])
            d = ImageDraw.Draw(t)
            d.rectangle([0, 0, 64, 22], fill=(0, 0, 0))
            d.text((5, 3), f"f{s + k * st}", fill=(255, 255, 255), font=font)
            tiles.append(t)
        if not tiles:
            print(f"range {r}: no frames decoded", file=sys.stderr)
            continue
        tw, th = tiles[0].size
        rows = (len(tiles) + a.cols - 1) // a.cols
        sheet = Image.new("RGB", (a.cols * tw, rows * th), (12, 12, 14))
        for k, t in enumerate(tiles):
            sheet.paste(t, ((k % a.cols) * tw, (k // a.cols) * th))
        p = os.path.join(a.out, f"strip_{s}_{e}.png")
        sheet.save(p)
        outs.append(p)
        print(p)
    return 0 if outs else 1


if __name__ == "__main__":
    sys.exit(main())
