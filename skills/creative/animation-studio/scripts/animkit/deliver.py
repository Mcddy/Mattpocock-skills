"""Delivery variants: GIF, transparent video, APNG, loops, captions, platform safe zones.

    gif("shot.mp4", "shot.gif", fps=15, width=640, max_mb=8)        # palette-optimised, size budget
    webm_alpha(seq["pattern"], "sticker.webm", fps=24)               # VP9 with alpha (web, stickers)
    prores4444(seq["pattern"], "overlay.mov", fps=24)                # alpha for editors (Premiere, Resolve, FCP)
    apng(seq["pattern"], "badge.png", fps=24)                        # alpha, lossless, plays in browsers
    loop_report("loop.mp4")                                          # is the loop seamless?
    write_srt(cues, "captions.srt"); write_vtt(cues, "captions.vtt") # sidecar captions
    draw_caption(cv, f, cues, W, H)                                  # burned-in captions inside safe zones
    safe_zone("vertical", W, H)                                      # area clear of platform UI

Recompose each aspect ratio from the scene (camera/layout per aspect); never centre-crop a
16:9 master into 9:16 (references/delivery.md).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import numpy as np


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return r


def _seq_numbers(src):
    d = os.path.dirname(src) or "."
    pre = os.path.basename(src).split("%")[0]
    return sorted(int(f[len(pre):len(pre) + 5]) for f in os.listdir(d) if f.startswith(pre) and f.endswith(".png"))


def _inputs(src, fps):
    """ffmpeg input args for an mp4/mov file or a printf-style image pattern.

    Refuses a numbered sequence with gaps: ffmpeg stops silently at the first missing frame (a test run
    shipped an alpha WebM with 63 of 120 frames after one render chunk failed)."""
    if "%" in src:
        nums = _seq_numbers(src)
        if not nums:
            raise RuntimeError(f"no frames match {src}")
        missing = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
        if missing:
            raise RuntimeError(f"frame sequence has {len(missing)} missing frames (first {missing[:5]}); re-render them")
        return ["-framerate", str(fps), "-start_number", str(nums[0]), "-i", src]
    return ["-i", src]


def count_frames(path) -> int:
    """Decoded frame count (use to confirm a delivery file holds every frame)."""
    r = _run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
              "stream=nb_read_frames", "-of", "csv=p=0", path])
    try:
        return int(r.stdout.strip().split(",")[0])
    except ValueError:
        return -1


def _done(src_pattern, out, **extra):
    n_in = len(_seq_numbers(src_pattern)) if "%" in src_pattern else None
    n_out = count_frames(out)
    if n_in is not None and n_out != n_in:
        raise RuntimeError(f"{out}: encoded {n_out} of {n_in} frames")
    return {"path": out, "frames": n_out, **extra}


def gif(src, out, fps=15, width=None, max_mb=None, loop=True, dither="sierra2_4a", colors=256):
    """High-quality GIF via palettegen/paletteuse. With max_mb, steps fps/width down until it fits."""
    tries = [(fps, width)]
    if max_mb:
        w0 = width or 960
        tries += [(min(fps, 12), w0), (min(fps, 12), int(w0 * 0.8)), (10, int(w0 * 0.66)), (10, int(w0 * 0.5))]
    for f_, w_ in tries:
        scale = f"scale={w_}:-2:flags=lanczos," if w_ else ""
        vf = (f"fps={f_},{scale}split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
              f"[b][p]paletteuse=dither={dither}:diff_mode=rectangle")
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *_inputs(src, fps), "-vf", vf,
              "-loop", "0" if loop else "-1", out])
        mb = os.path.getsize(out) / 1e6
        if not max_mb or mb <= max_mb:
            return {"path": out, "fps": f_, "width": w_, "mb": round(mb, 2)}
    return {"path": out, "fps": f_, "width": w_, "mb": round(mb, 2), "over_budget": True}


def webm_alpha(src_pattern, out, fps=24, crf=28):
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *_inputs(src_pattern, fps), "-c:v", "libvpx-vp9",
          "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(crf), "-row-mt", "1", "-auto-alt-ref", "0", out])
    return _done(src_pattern, out, has_alpha=probe_alpha(out))


def prores4444(src_pattern, out, fps=24):
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *_inputs(src_pattern, fps), "-c:v", "prores_ks",
          "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", out])
    return _done(src_pattern, out, has_alpha=probe_alpha(out))


def apng(src_pattern, out, fps=24, loop=True):
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *_inputs(src_pattern, fps), "-plays",
          "0" if loop else "1", "-f", "apng", out])
    return _done(src_pattern, out)


def probe_alpha(path) -> bool:
    """True if the first decoded frame has non-opaque alpha (decodes with libvpx for WebM alpha)."""
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "f.png")
        dec = ["-c:v", "libvpx-vp9"] if path.endswith(".webm") else []
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *dec, "-i", path, "-frames:v", "1",
                            "-pix_fmt", "rgba", png], capture_output=True)
        if r.returncode != 0 or not os.path.exists(png):
            return False
        from PIL import Image
        a = np.asarray(Image.open(png).convert("RGBA"))[..., 3]
        return bool(a.min() < 250)


def loop_report(path) -> dict:
    """Is a loop seamless? Compares the wrap-around step (last frame -> first frame) with the normal
    frame-to-frame steps. Render frames [0, N) of a cycle whose frame N equals frame 0, so the wrap is
    an ordinary step, not a repeat or a jump."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    w0, h0 = (int(v) for v in r.stdout.strip().split(",")[:2])
    h = int(320 * h0 / w0) // 2 * 2
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf",
                          f"scale=320:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8)
    n = a.size // (320 * h)
    fr = a[: n * 320 * h].reshape(n, h, 320).astype(np.float32)
    steps = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    seam = float(np.abs(fr[0] - fr[-1]).mean())
    typical = float(np.percentile(steps, 90)) if len(steps) else 0.0
    # a repeated frame shows as a seam step far smaller than the steps either side of it (a one-frame hitch);
    # an eased loop is slow on both sides of the seam, so it isn't flagged
    nb = min(float(steps[0]), float(steps[-1])) if len(steps) else 0.0
    dup = nb > 0.3 and seam < 0.25 * nb
    return {"frames": n, "seam_step": round(seam, 2), "typical_step_p90": round(typical, 2),
            "seamless": (seam <= max(1.0, typical * 1.5)) and not dup,
            "note": "last frame repeats the first (one-frame hitch); drop it" if dup else ""}


# ---------------------------------------------------------------- captions
def _ts(t, sep=","):
    h, rem = divmod(max(0.0, t), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)):03d}"


def write_srt(cues, path):
    """cues: [(start_s, end_s, text)]. One or two lines, <= ~42 characters per line, >= ~1 s on screen."""
    with open(path, "w", encoding="utf-8") as fh:
        for i, (a, b, t) in enumerate(cues, 1):
            fh.write(f"{i}\n{_ts(a)} --> {_ts(b)}\n{t}\n\n")
    return path


def write_vtt(cues, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("WEBVTT\n\n")
        for a, b, t in cues:
            fh.write(f"{_ts(a, '.')} --> {_ts(b, '.')}\n{t}\n\n")
    return path


def safe_zone(kind, w, h):
    """(x, y, w, h) area to keep text and key action inside.

    'title' : 5% action-safe margins (broadcast-style).
    'vertical': 9:16 feeds (Reels/TikTok/Shorts) - conservative margins clear of the usual
                caption/buttons overlay: top 14%, bottom 22%, sides 6%, right 14%.
                Approximate: platform UIs change; check the current spec when it matters.
    'square'  : 6% margins.
    """
    if kind == "vertical":
        return (0.06 * w, 0.14 * h, w - 0.06 * w - 0.14 * w, h - 0.14 * h - 0.22 * h)
    m = 0.05 if kind == "title" else 0.06
    return (m * w, m * h, w * (1 - 2 * m), h * (1 - 2 * m))


def _wrap(s, max_chars=42):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + (1 if cur else 0) > max_chars and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = f"{cur} {wd}" if cur else wd
    if cur:
        lines.append(cur)
    return lines[:2]


def draw_caption(cv, f, cues, w, h, fps=24.0, kind="title", size=None, family="DejaVu Sans", weight=600,
                 color="#FFFFFF", box="#000000B0", path=None):
    """Burned-in caption for frame f from [(start_s, end_s, text)], bottom-centred inside the safe zone."""
    t = f / fps
    cur = next((c for c in cues if c[0] <= t < c[1]), None)
    if not cur:
        return
    x, y, sw, sh = safe_zone(kind, w, h)
    size = size or max(18, int(h * (0.045 if kind == "vertical" else 0.05)))
    lines = _wrap(cur[2])
    lh = size * 1.25
    by = y + sh - lh * len(lines)
    for i, ln in enumerate(lines):
        yy = by + i * lh
        wdt = len(ln) * size * 0.55
        cv.rect(x + sw / 2 - wdt / 2 - size * 0.35, yy - size * 0.95, wdt + size * 0.7, lh, box, r=size * 0.2)
        cv.text(ln, x + sw / 2, yy, size=size, family=family, weight=weight, color=color, align="center", path=path)


def safe_zone_overlay(png_in, png_out, kind="vertical"):
    """Review still with the safe zone outlined (check nothing important sits under platform UI)."""
    from PIL import Image, ImageDraw
    im = Image.open(png_in).convert("RGB")
    x, y, w, h = safe_zone(kind, *im.size)
    d = ImageDraw.Draw(im)
    d.rectangle([x, y, x + w, y + h], outline=(255, 64, 64), width=max(2, im.size[0] // 300))
    im.save(png_out)
    return png_out


def have(codec) -> bool:
    if not shutil.which("ffmpeg"):
        return False
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return codec in r.stdout
