#!/usr/bin/env python3
"""slop_lint - flag stock copy, stock motion and stock looks for a human (or agent) decision.

Usage
  python3 slop_lint.py [--text FILE_OR_STRING ...] [--code scene.py ...] [--video out.mp4]
                       [--no-em-dash] [--json report.json]

Text   (on-screen copy, VO scripts, .srt/.vtt captions, delivery notes): hype verbs, empty
       evaluation words, stock phrases, em dashes (when the client avoids them), exclamation
       density, emoji in titles.
Code   (animkit scene files): one ease for nearly every key, overshoot on most keys, typewriter
       reveals, sandbox/default fonts, purple-blue gradients, identical per-letter staggers.
Video  : moments where most of the frame starts moving within two frames (everything animating
       at once), and a purple-blue dominated palette.

Every flag is a question ("is this doing a job here?"), not a verdict. Technical words in
their technical sense stay (see references/deslop-motion.md).
"""
from __future__ import annotations

import argparse
import colorsys
import json
import os
import re
import subprocess
import sys
from collections import Counter

import numpy as np

HYPE = ["elevate", "unleash", "supercharge", "revolutionize", "revolutionise", "unlock", "empower", "skyrocket",
        "game-changer", "game changer", "next-level", "next level", "cutting-edge", "cutting edge", "world-class",
        "best-in-class", "state-of-the-art", "synergy", "leverage", "transformative", "disrupt"]
EMPTY_EVAL = ["seamless", "seamlessly", "effortless", "effortlessly", "powerful", "innovative", "robust solution",
              "stunning", "magical", "delightful", "intuitive", "blazing fast", "lightning-fast"]
STOCK = [r"in today's (fast-paced|digital) world", r"imagine a world", r"say goodbye to", r"look no further",
         r"take (it|your \w+) to the next level", r"it'?s not just (a |an )?\w+[,.;]? it'?s", r"the power of",
         r"(your|the) journey", r"\bdelve\b", r"designed with you in mind", r"we've got you covered",
         r"like never before", r"at the end of the day", r"here'?s the (thing|kicker|key)", r"let'?s dive in"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def lint_text(name, txt, no_em_dash=False):
    out = []
    lines = txt.splitlines() or [txt]
    for n, line in enumerate(lines, 1):
        low = line.lower()
        if re.match(r"^\s*\d+\s*$|^\s*[\d:,.]+\s*-->\s*[\d:,.]+", line):
            continue
        for w in HYPE:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                out.append(("copy", f"{name}:{n}", f"hype word '{w}'", "Name the specific result or action instead"))
        for w in EMPTY_EVAL:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                out.append(("copy", f"{name}:{n}", f"evaluation word '{w}'",
                            "Show the visible consequence that makes it true, or cut it"))
        for pat in STOCK:
            if re.search(pat, low):
                out.append(("copy", f"{name}:{n}", f"stock phrase /{pat}/", "Write what is true and particular here"))
        if no_em_dash and "—" in line:
            out.append(("copy", f"{name}:{n}", "em dash", "Client convention: use a full stop, comma, colon or brackets"))
        if EMOJI.search(line) and len(line) < 60:
            out.append(("copy", f"{name}:{n}", "emoji in a short (title-like) line", "Keep emojis out of titles and headings"))
    bangs = txt.count("!")
    words = max(1, len(txt.split()))
    if bangs >= 3 and bangs / words > 0.02:
        out.append(("copy", name, f"{bangs} exclamation marks", "Let the picture carry the energy"))
    return out


def _hex_hue(h):
    h = h.lstrip("#")[:6]
    if len(h) != 6:
        return None
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, s, v = colorsys.rgb_to_hsv(r, g, b)
    return hh * 360, s, v


def lint_code(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    out = []
    eases = re.findall(r"\bK\([^()]*?,\s*[^()]*?,\s*\"([a-z_]+)\"", src) + re.findall(r"ease=\"([a-z_]+)\"", src)
    if len(eases) >= 8:
        c = Counter(eases)
        top, n = c.most_common(1)[0]
        if n / len(eases) > 0.7:
            out.append(("motion", path, f"'{top}' on {n}/{len(eases)} keys", "Vary spacing by mass and intent: snap, heavy, "
                        "float, settle, holds; contrast fast with slow"))
        over = sum(v for k, v in c.items() if k in ("out_back", "settle", "wobble", "out_elastic", "out_bounce"))
        if over / len(eases) > 0.6:
            out.append(("motion", path, f"overshoot on {over}/{len(eases)} keys", "Overshoot only where something has mass or spring"))
        if c.get("linear", 0) / len(eases) > 0.5:
            out.append(("motion", path, "mostly linear keys", "Linear reads mechanical; ease unless it's a machine or a camera dolly"))
    if re.search(r"\[\s*:\s*int\(", src) and re.search(r"text\(|KineticText", src):
        out.append(("motion", path, "typewriter reveal (string sliced by time)", "Reveal by meaning: masks, tracking, the word that matters"))
    for m in re.finditer(r"family\s*=\s*\"(Inter|Arial|Helvetica|DejaVu Sans|Liberation Sans|Roboto|Poppins|Montserrat)\"", src):
        if "fonts.fetch" not in src and "best_available" not in src:
            out.append(("look", path, f"default font '{m.group(1)}'", "Choose a typeface for the brand/story (fonts.fetch / best_available)"))
    for m in re.finditer(r"(?:linear|radial)\((.{0,160}?)\[([^\]]*)\]", src, re.S):
        hues = [_hex_hue(h) for h in re.findall(r"#[0-9A-Fa-f]{6}", m.group(2))]
        hues = [x for x in hues if x]
        if len(hues) >= 2 and all(225 <= hh <= 290 and s > 0.35 for hh, s, v in hues):
            out.append(("look", path, "purple-blue gradient", "Keep only if it is the brand; otherwise brand palette with one accent"))
    stag = re.findall(r"stagger_in\(([^)]*)\)", src)
    if len(stag) >= 3 and len(set(s.replace(" ", "") for s in stag)) == 1:
        out.append(("motion", path, f"identical stagger_in on {len(stag)} lines", "Give the line that matters its own move"))
    return out


def lint_video(path):
    out = []
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    w, h, fr = probe.strip().split(",")[:3]
    num, den = fr.split("/")
    fps = float(num) / float(den or 1)
    W, H = 128, max(8, int(128 * int(h) / int(w)) // 8 * 8)
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf",
                          f"scale={W}:{H}:flags=area", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8)
    n = a.size // (W * H * 3)
    fr_ = a[: n * W * H * 3].reshape(n, H, W, 3).astype(np.float32)
    g = fr_.mean(-1)
    d = np.abs(np.diff(g, axis=0))                                     # (n-1, H, W)
    th, tw = H // 8, W // 8
    tiles = d.reshape(n - 1, 8, th, 8, tw).mean(axis=(2, 4)).reshape(n - 1, 64)
    glob = d.mean(axis=(1, 2))
    moving = tiles > 1.2
    events = []
    for i in range(6, n - 3):
        if glob[i] > 25:                                               # a cut, not an entrance
            continue
        before_still = ~moving[i - 6:i].any(0)
        starts = moving[i:i + 2].any(0) & before_still
        busy = (tiles[i:i + 2] > 0.5).any(0).sum()
        if starts.sum() >= 0.4 * 64 and busy >= 0.5 * 64:
            events.append(round(i / fps, 2))
    dedup = [t for k, t in enumerate(events) if k == 0 or t - events[k - 1] > 0.5]
    for t in dedup[:5]:
        out.append(("motion", f"{path}@{t}s", "most of the frame starts moving in the same two frames",
                    "Camera move or a cut? Fine. Elements animating in together? Stagger by meaning"))
    sample = fr_[:: max(1, n // 24)].reshape(-1, 3) / 255.0
    mx, mn = sample.max(1), sample.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    r, gg, b = sample[:, 0], sample[:, 1], sample[:, 2]
    hue = np.degrees(np.arctan2(np.sqrt(3) * (gg - b), 2 * r - gg - b)) % 360
    pb = ((hue > 225) & (hue < 290) & (sat > 0.35) & (mx > 0.25)).mean()
    if pb > 0.35:
        out.append(("look", path, f"purple-blue covers {pb:.0%} of sampled pixels", "Brand colour or a default? Keep only with a reason"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", nargs="*", default=[], action="extend")
    ap.add_argument("--code", nargs="*", default=[], action="extend")
    ap.add_argument("--video", nargs="*", default=[], action="extend")
    ap.add_argument("--no-em-dash", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    flags = []
    for t in a.text:
        if os.path.exists(t):
            flags += lint_text(t, open(t, encoding="utf-8", errors="replace").read(), a.no_em_dash)
        else:
            flags += lint_text("text", t, a.no_em_dash)
    for c in a.code:
        flags += lint_code(c)
    for v in a.video:
        flags += lint_video(v)
    print(f"# slop_lint: {len(flags)} question(s)")
    for area, where, what, fix in flags:
        print(f"- **{area}** {where}: {what}. {fix}.")
    if not flags:
        print("No stock-pattern candidates found. Still run the transplant, swap and strip tests by eye.")
    if a.json:
        json.dump([dict(area=x[0], where=x[1], finding=x[2], fix=x[3]) for x in flags], open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
