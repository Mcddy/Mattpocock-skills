#!/usr/bin/env python3
"""reel_critic - objective QA pass for any animation deliverable.

Measures what a supervisor would otherwise eyeball, so reviews start from
evidence, not vibes. It does NOT judge acting, appeal or story; it tells you
where to look and catches the mechanical failures that make work read as cheap.

Usage
  python3 reel_critic.py VIDEO --out DIR [--reel] [--target-lufs -14] [--max-sheet 40]

Outputs in DIR
  report.md / report.json   flags with severity, numbers, and the fix
  contact_sheet.png         timestamped frames for visual review
  motion.png                per-second motion energy with cuts and frozen spans
  spectrum.png              full-length spectrogram

Checks
  picture   cuts, shot lengths, frozen seconds, near-still seconds, effective
            unique-frame rate per shot, luminance clipping
  sound     integrated loudness / LRA / true peak, silence, score looping
            (self-similarity), sameness of score across shots, flat white-noise
            ambience, cut-to-sound-onset sync (heuristic)
  delivery  bitrate vs platform guidance, frame rate, duration (reel mode)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys

from result_contract import CheckArgumentParser, CheckRunnerError, check, result, emit, error_detail

try:
    import numpy as np
    _dependency_error = None
except Exception as exc:
    np = None
    _dependency_error = type(exc).__name__

AW, AH = 128, 72          # analysis resolution for motion
ASR = 16000               # analysis sample rate for music/onsets


def sh(cmd, binary=False):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckRunnerError("Media command could not run", stage="media", code=type(exc).__name__) from exc
    if r.returncode:
        raise CheckRunnerError("Media command failed", stage="media", returncode=r.returncode,
                               stderr_tail=r.stderr.decode(errors="replace")[-800:])
    return r.stdout if binary else r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")


def probe(path):
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
                           capture_output=True, text=True, timeout=30)
        if p.returncode:
            raise CheckRunnerError("ffprobe failed", stage="probe", returncode=p.returncode, stderr_tail=p.stderr[-800:])
        js = json.loads(p.stdout)
        v = next((s for s in js["streams"] if s["codec_type"] == "video"), None)
        a = next((s for s in js["streams"] if s["codec_type"] == "audio"), None)
        if v is None:
            raise ValueError("No video stream")
        num, den = v["r_frame_rate"].split("/")
        fps = float(num) / float(den)
        dur = float(js["format"]["duration"])
        if not all(math.isfinite(n) and n > 0 for n in (fps, dur, int(v["width"]), int(v["height"]))):
            raise ValueError("Invalid duration, frame rate or dimensions")
        # Convert all optional numeric fields within the same truthful probe boundary.
        for stream, key in ((v, "bit_rate"), (js["format"], "bit_rate"), (a, "sample_rate"), (a, "channels")):
            if stream is not None:
                stream[key] = int(stream.get(key, 0) or 0)
                if stream[key] < 0:
                    raise ValueError("Negative optional metadata field")
    except CheckRunnerError:
        raise
    except Exception as exc:
        raise CheckRunnerError("Video probe invalid or unavailable", stage="probe", code=type(exc).__name__) from exc
    return {
        "duration": dur,
        "width": int(v["width"]) if v else 0,
        "height": int(v["height"]) if v else 0,
        "fps": fps,
        "vcodec": v.get("codec_name") if v else None,
        "v_bitrate": int(v.get("bit_rate", 0) or 0) if v else 0,
        "total_bitrate": int(js["format"].get("bit_rate", 0) or 0),
        "has_audio": a is not None,
        "acodec": a.get("codec_name") if a else None,
        "a_rate": int(a.get("sample_rate", 0)) if a else 0,
        "a_channels": int(a.get("channels", 0)) if a else 0,
        "x264_crf": x264_crf(path),
    }


def x264_crf(path, scan_bytes=4_000_000):
    """CRF from the x264 settings string embedded in the stream (None if absent or not x264)."""
    try:
        with open(path, "rb") as fh:
            blob = fh.read(scan_bytes)
    except OSError:
        return None
    i = blob.find(b"x264 - core")
    if i < 0:
        return None
    m = re.search(rb"\bcrf=([\d.]+)", blob[i:i + 4000])
    return float(m.group(1)) if m else None


# ------------------------------------------------------------------ picture
def read_gray(path, fps):
    fps_use = min(fps, 60) if fps else 24
    raw = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf",
              f"fps={fps_use},scale={AW}:{AH}:flags=area,format=gray", "-f", "rawvideo", "-"], binary=True)
    if not raw or len(raw) % (AH * AW) or len(raw) < 2 * AH * AW:
        raise CheckRunnerError("Need at least two complete decoded picture frames", stage="picture-decode")
    a = np.frombuffer(raw, np.uint8).reshape(-1, AH, AW).astype(np.int16)
    return a, fps_use


def norm24(d, fps):
    """Express frame-to-frame change in 24 fps-equivalent units so thresholds hold at any rate."""
    return d * (fps / 24.0)


def subject_heights(frames, fps, cut_idx=()):
    """Per second: height (fraction of frame) of the largest region that changes between frames, i.e.
    the main moving subject. Measured: a character in a medium ~0.3-0.6; the same film shrunk to a
    wide ~0.08-0.15; a logo lock-up's letters ~0.1. A camera move counts as full frame."""
    try:
        from scipy import ndimage as ndi
    except ImportError:
        return None
    H, W = frames.shape[1:]
    cuts = set(cut_idx)
    hs = np.full(len(frames) - 1, np.nan)
    for i in range(len(frames) - 1):
        if i in cuts:
            continue
        m = np.abs(frames[i + 1] - frames[i]) > 5
        if m.sum() < 3:
            continue
        lab, n = ndi.label(ndi.binary_dilation(m, iterations=2))
        sizes = ndi.sum(m, lab, range(1, n + 1))
        k = int(np.argmax(sizes)) + 1
        if sizes[k - 1] > 0.6 * H * W:
            hs[i] = 1.0
            continue
        ys = np.nonzero((lab == k) & m)[0]
        hs[i] = (ys.max() - ys.min() + 1) / H
    out = []
    for s_ in range(int(len(hs) // fps)):
        seg = hs[int(s_ * fps):int((s_ + 1) * fps)]
        out.append(round(float(np.nanmedian(seg)), 3) if np.any(~np.isnan(seg)) else None)
    return out


def picture_analysis(path, info):
    frames, fps = read_gray(path, info["fps"])
    d_raw = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    d = norm24(d_raw, fps)
    n = len(d)
    # cuts: spikes far above the local median
    pad = int(fps)
    med = np.array([np.median(d[max(0, i - pad):i + pad + 1]) for i in range(n)])
    cut_idx = [i for i in range(n) if d_raw[i] > max(9.0, 6 * med[i] * 24 / fps + 4)]
    merged = []
    for i in cut_idx:
        if not merged or i - merged[-1] > fps * 0.25:
            merged.append(i)
    cuts = [round((i + 1) / fps, 3) for i in merged]
    bounds = [0.0] + cuts + [info["duration"]]
    shots = [(round(bounds[i], 3), round(bounds[i + 1], 3)) for i in range(len(bounds) - 1)
             if bounds[i + 1] - bounds[i] > 0.05]
    # per-second energy, excluding cut frames
    d_nc = d.copy()
    for i in merged:
        d_nc[max(0, i - 1):i + 2] = np.nan
    secs = int(math.floor(n / fps))
    energy = [float(np.nanmean(d_nc[int(s * fps):int((s + 1) * fps)])) if np.any(~np.isnan(d_nc[int(s * fps):int((s + 1) * fps)])) else 0.0
              for s in range(secs)]
    # frozen = nothing visibly changes anywhere (not "the average change is small": a small character
    # moving in a wide has a tiny average but is not frozen)
    peak = np.abs(np.diff(frames, axis=0)).max(axis=(1, 2)).astype(float)
    for i in merged:
        peak[max(0, i - 1):i + 2] = np.nan
    frozen = [s for s in range(secs) if np.any(~np.isnan(peak[int(s * fps):int((s + 1) * fps)]))
              and float(np.nanmedian(peak[int(s * fps):int((s + 1) * fps)])) < 3.0]
    # near-still: 0.5. (v2 used 0.6 on renders with moving grain, which adds ~0.1 to every second; the
    # same film with a static dither instead measures ~0.1 lower.) References at 1080p: a character
    # walking in a medium-wide ~0.6; a breathing hold or a 1.5% scale drift on a logo ~0.1-0.4.
    still = [s for s, e in enumerate(energy) if e < 0.5 and s not in frozen]
    # effective unique-frame rate per shot
    per_shot = []
    for a, b in shots:
        i0, i1 = int(a * fps), max(int(a * fps) + 1, int(b * fps) - 1)
        seg = d[i0:i1]
        seg = seg[~np.isin(np.arange(i0, i0 + len(seg)), merged)]
        uniq = float((seg > 0.02 * fps / 24).mean()) * fps if len(seg) else 0.0
        mean_e = float(seg.mean()) if len(seg) else 0.0
        # variation of per-second motion inside the shot: ~0 means metronomic, constant-speed movement
        ps = [float(seg[int(k * fps):int((k + 1) * fps)].mean()) for k in range(int(len(seg) // fps))]
        var = float(np.std(ps) / (np.mean(ps) + 1e-6)) if len(ps) >= 3 else None
        per_shot.append({"start": a, "end": b, "len": round(b - a, 2), "unique_fps": round(uniq, 1),
                         "motion": round(mean_e, 3), "motion_cv": round(var, 3) if var is not None else None})
    subject = subject_heights(frames, fps, merged)
    # clipping
    full = frames.astype(np.uint8)
    clip_lo = float((full <= 2).mean())
    clip_hi = float((full >= 253).mean())
    analysis_errors = []
    try:
        banding = banding_analysis(path, info)
    except Exception as exc:
        banding = None
        analysis_errors.append(error_detail(exc, "banding"))
    return {"fps_analysed": fps, "diff": d.tolist(), "cuts": cuts, "shots": per_shot, "energy": energy,
            "frozen_seconds": frozen, "still_seconds": still, "clip_black": clip_lo, "clip_white": clip_hi,
            "subject_height": subject, "banding": banding, "analysis_errors": analysis_errors}


def _box(a, r):
    """Mean filter with a (2r+1)^2 window via integral images (no scipy needed)."""
    k = 2 * r + 1
    p = np.pad(a, r + 1, mode="edge").astype(np.float64)
    c = p.cumsum(0).cumsum(1)
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return (s / (k * k))[:a.shape[0], :a.shape[1]]


def banding_analysis(path, info, samples=5):
    """Gradient banding: in gentle, detail-free gradients (vignettes, skies, soft light), how much of the
    area sits in perfectly flat 5x5 patches. Dithered or grained gradients score ~0-0.1; an encoder
    that stripped moving grain (e.g. x264 -tune animation) scores 0.4-0.8 and shows
    contour lines on large or dark screens."""
    w, h, dur = info["width"], info["height"], info["duration"]
    if not (w and h and dur):
        return None
    sw, sh_ = min(w, 1920), int(round(min(w, 1920) * h / w / 2) * 2)
    res = []
    for k in range(samples):
        t = dur * (k + 0.5) / samples
        raw = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", path, "-vframes", "1",
                  "-vf", f"scale={sw}:{sh_}:flags=neighbor,format=gray", "-f", "rawvideo", "-"], binary=True)
        if len(raw) < sw * sh_:
            raise CheckRunnerError("Incomplete banding sample", stage="banding-decode")
        y = np.frombuffer(raw[:sw * sh_], np.uint8).reshape(sh_, sw).astype(np.float64)
        big = _box(_box(y, 15), 15)
        gy, gx = np.gradient(big)
        g = np.hypot(gx, gy)
        tex = _box((y - _box(y, 4)) ** 2, 4)
        smooth = (g > 0.03) & (g < 0.8) & (tex < 4.0)
        if smooth.mean() < 0.02:
            continue
        var5 = _box(y * y, 2) - _box(y, 2) ** 2
        res.append((float((var5[smooth] < 0.02).mean()), float(smooth.mean()), round(t, 2)))
    if not res:
        return None
    return {"flat_share": round(float(np.median([r[0] for r in res])), 3),
            "gradient_area": round(float(np.mean([r[1] for r in res])), 3),
            "worst_t": max(res)[2]}


def contact_sheet(path, info, out_png, max_tiles=40, cols=5):
    from PIL import Image, ImageDraw, ImageFont
    dur = info["duration"]
    nt = int(min(max_tiles, max(1, dur / 1.0)))
    times = [dur * (i + 0.5) / nt for i in range(nt)]
    tw = 384
    th = int(tw * info["height"] / max(1, info["width"])) if info["width"] else 216
    rows = math.ceil(nt / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (20, 20, 20))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    dr = ImageDraw.Draw(sheet)
    for k, t in enumerate(times):
        raw = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                  "-vf", f"scale={tw}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], binary=True)
        if len(raw) < tw * th * 3:
            raise CheckRunnerError("Incomplete contact-sheet frame", stage="sheet-decode")
        im = Image.frombytes("RGB", (tw, th), raw[: tw * th * 3])
        x, y = (k % cols) * tw, (k // cols) * (th + 22)
        sheet.paste(im, (x, y))
        dr.text((x + 6, y + th + 3), f"{int(t // 60)}:{t % 60:05.2f}", fill=(220, 220, 220), font=font)
    sheet.save(out_png)
    return out_png


# ------------------------------------------------------------------ sound
def read_audio(path):
    raw = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(ASR),
              "-f", "f32le", "-"], binary=True)
    return _audio_samples(raw)


def read_audio_hi(path):
    raw = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "48000",
              "-f", "f32le", "-"], binary=True)
    return _audio_samples(raw)


def _audio_samples(raw):
    if not raw or len(raw) % 4:
        raise CheckRunnerError("Audio decode empty or misaligned", stage="audio-decode")
    samples = np.frombuffer(raw, np.float32)
    if not np.isfinite(samples).all():
        raise CheckRunnerError("Audio decode contains nonfinite samples", stage="audio-decode")
    return samples


def ebur(path):
    txt = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    txt = txt[txt.rfind("Summary:"):]
    def g(label):
        m = re.search(label + r":\s+(-?[\d.]+|-inf)", txt)
        if not m:
            return None
        return None if m.group(1) == "-inf" else float(m.group(1))
    return {"I": g("I"), "LRA": g("LRA"), "TP": g("Peak")}


def sound_analysis(path, info, shots, cuts):
    x = read_audio(path)
    if not len(x):
        return None
    loud = ebur(path)
    sec = ASR
    rms_db = [20 * math.log10(np.sqrt(np.mean(x[i:i + sec] ** 2)) + 1e-9) for i in range(0, len(x) - sec + 1, sec)]
    silent = [i for i, v in enumerate(rms_db) if v < -50]
    # spectral frames 0.1 s hop, 50-2000 Hz (tonal/music band)
    hop, win = ASR // 10, ASR // 5
    nfr = max(0, (len(x) - win) // hop)
    S = np.empty((nfr, 0))
    if nfr > 0:
        idx = np.arange(win)[None, :] + hop * np.arange(nfr)[:, None]
        frames = x[idx] * np.hanning(win)[None, :]
        mag = np.abs(np.fft.rfft(frames, axis=1))
        freqs = np.fft.rfftfreq(win, 1 / ASR)
        band = (freqs >= 50) & (freqs <= 2000)
        S = mag[:, band]
        S = S / (np.linalg.norm(S, axis=1, keepdims=True) + 1e-9)
    # loop detection: similarity at lag L, best L in 2..40 s
    loop = {"best_lag_s": None, "similarity": None, "repeats": None, "contrast": None}
    if len(S) > 200:
        sims = []
        for L in range(20, min(400, len(S) // 3), 5):
            sims.append((float((S[:-L] * S[L:]).sum(1).mean()), L))
        best_sim, best_L = max(sims)
        med = float(np.median([v for v, _ in sims]))
        loop = {"best_lag_s": best_L / 10, "similarity": round(best_sim, 3),
                "repeats": round(info["duration"] / (best_L / 10), 1), "contrast": round(best_sim - med, 3)}
    # sameness of the score across shots
    shot_sim = None
    if len(S) and len(shots) >= 3:
        vecs = []
        for s in shots:
            a, b = int(s["start"] * 10), int(s["end"] * 10)
            if b - a >= 10:
                v = S[a:b].mean(0)
                vecs.append(v / (np.linalg.norm(v) + 1e-9))
        if len(vecs) >= 3:
            M = np.array(vecs) @ np.array(vecs).T
            iu = np.triu_indices(len(vecs), 1)
            shot_sim = round(float(M[iu].mean()), 3)
    # flat (white) noise ambience per shot, 3-18 kHz
    flat = []
    xh = read_audio_hi(path)
    for s in shots:
        a, b = int(s["start"] * 48000), int(s["end"] * 48000)
        seg = xh[a:b]
        if len(seg) < 48000:
            continue
        n = 4096
        fr = seg[: (len(seg) // n) * n].reshape(-1, n) * np.hanning(n)
        m = np.abs(np.fft.rfft(fr, axis=1)).mean(0)
        f = np.fft.rfftfreq(n, 1 / 48000)
        band = (f > 3000) & (f < 18000)
        spec = 20 * np.log10(m[band] + 1e-9)
        from scipy import signal as _sg
        hp = _sg.sosfilt(_sg.butter(4, (3000, 18000), btype="bandpass", fs=48000, output="sos"), seg)
        level = 20 * math.log10(float(np.sqrt(np.mean(hp ** 2))) + 1e-12)
        p = np.polyfit(np.log2(f[band]), spec, 1)
        resid = float(np.std(spec - np.polyval(p, np.log2(f[band]))))
        if abs(p[0]) < 1.0 and resid < 0.6 and level > -70:
            flat.append({"start": s["start"], "end": s["end"], "slope_db_oct": round(float(p[0]), 2),
                         "resid_db": round(resid, 2)})
    # onsets (spectral flux) for sync heuristic
    onsets = []
    if len(S):
        flux = np.maximum(0, np.diff(S, axis=0)).sum(1)
        thr = np.median(flux) + 2.5 * np.std(flux)
        onsets = [(i + 1) / 10 for i in range(1, len(flux) - 1)
                  if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    tol = 2.5 / max(info["fps"], 1) + 0.1
    synced = sum(1 for c in cuts if any(abs(c - o) <= tol for o in onsets))
    return {"loudness": loud, "rms_db_per_s": [round(v, 1) for v in rms_db], "silent_seconds": silent,
            "loop": loop, "score_sameness_across_shots": shot_sim, "flat_noise_shots": flat,
            "onsets": len(onsets), "cuts_on_audio_onset": f"{synced}/{len(cuts)}"}


# ------------------------------------------------------------------ plots
def motion_plot(pic, out_png, duration):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e = pic["energy"]
    fig, ax = plt.subplots(figsize=(14, 3.2), dpi=110)
    ax.bar(range(len(e)), e, width=1.0, color="#3b6e8f")
    for s in pic["frozen_seconds"]:
        ax.axvspan(s, s + 1, color="#d1495b", alpha=0.35, lw=0)
    for c in pic["cuts"]:
        ax.axvline(c, color="#222", lw=0.6, alpha=0.6)
    ax.set_xlim(0, max(1, duration))
    ax.set_ylim(0, max(3, np.percentile(e, 98) * 1.2 if e else 3))
    ax.set_xlabel("seconds")
    ax.set_ylabel("motion energy")
    ax.set_title("Motion energy per second (red = frozen, lines = cuts)")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


# ------------------------------------------------------------------ verdicts
YT_RECOMMENDED_MBPS = {  # YouTube SDR upload guidance (standard / high frame rate)
    2160: (35, 53), 1440: (16, 24), 1080: (8, 12), 720: (5, 7.5), 480: (2.5, 4),
}


def _runs(secs):
    """[2, 3, 4, 7] -> '2-5 s, 7-8 s' (each second s covers s..s+1)."""
    if not secs:
        return "-"
    out, a = [], secs[0]
    for p, q in zip(secs, secs[1:] + [None]):
        if q != p + 1:
            out.append(f"{a}-{p + 1} s")
            a = q
    return ", ".join(out)


def verdicts(info, pic, snd, reel=False, target_lufs=-14.0, *, mode="film", allow_still=()):
    flags = []

    def flag(sev, area, msg, fix, **data):
        flags.append({"severity": sev, "area": area, "finding": msg, "fix": fix, **data})

    dur = info["duration"]
    pic = dict(pic)
    for key in ("frozen_seconds", "still_seconds"):
        pic[key] = [s for s in pic[key] if not any(a <= s and s + 1 <= b for a, b in allow_still)]
        if mode in ("ui", "loop"):
            pic[key] = []
    frozen = len(pic["frozen_seconds"])
    if frozen / max(dur, 1) > 0.05 or frozen >= 4:
        flag("high", "picture", f"{frozen}s of fully frozen picture ({frozen / max(dur, 1):.0%} of runtime)",
             "Review undeclared frozen spans against the brief. Keep purposeful resting/read states or revise timing and staging when they obscure the intended action.",
             seconds=pic["frozen_seconds"])
    still = pic["still_seconds"]
    still_ratio = len(still) / max(dur, 1)
    if still_ratio > 0.25:
        flag("medium" if (frozen or still_ratio >= 0.45) else "low", "picture",
             f"{len(still)}s of near-still picture ({still_ratio:.0%} of runtime, at {_runs(still)})",
             "Review scale and timing against the intended beat. A legible logo lock-up or read hold can be correct; declare its interval and inspect the transition into and out of it.", seconds=still)
    sub = [v for v in (pic.get("subject_height") or []) if v is not None]
    if mode == "film" and len(sub) >= 2:
        med = float(np.median(sub))
        if med < 0.2:
            flag("medium" if (med < 0.12 and dur >= 6) else "low", "staging",
                 f"Main moving subject is small in frame: median {med:.0%} of frame height across moving seconds",
                 "Character work: acting reads at a medium (character ~35-60% of frame height) and closer for "
                 "thought beats; keep the wide for establishing and travel, and push in or cut closer for the beats "
                 "that carry the story. Stings and logos: play the mark's moment at hero scale, then pull back to "
                 "the lock-up (type moving at its final size is fine after that).",
                 seconds=[i for i, v in enumerate(pic["subject_height"] or []) if v is not None and v < 0.2])
    long = [s for s in pic["shots"] if s["len"] > 12]
    if mode == "film" and long:
        flag("medium", "edit", f"{len(long)} shots longer than 12 s", "Re-time in the animatic; long shots need evolving staging or camera.",
             shots=[(s["start"], s["len"]) for s in long])
    mech = [s for s in pic["shots"] if s["len"] >= 4 and s["motion"] > 1.0 and s["motion_cv"] is not None and s["motion_cv"] < 0.1]
    if mode == "film" and mech:
        flag("medium", "animation", f"{len(mech)} shots with metronomic, constant-speed motion",
             "Constant velocity reads as mechanical. Add ease in/out, accents, acceleration changes and holds.",
             shots=[(s["start"], s["len"]) for s in mech])
    if mode == "film" and info["fps"] >= 48 and reel:
        flag("low", "look", f"Delivered at {info['fps']:.0f} fps",
             "Character and stylised animation are conventionally 24 fps (often on 2s); 60 fps tweening reads as UI/screensaver motion unless it's a deliberate game-capture look.")
    rates = [s["unique_fps"] for s in pic["shots"] if s["len"] > 1.5 and s["motion"] > 0.3]
    if mode == "film" and rates and (max(rates) - min(rates)) > info["fps"] * 0.5:
        flag("low", "look", f"Mixed frame cadence across shots ({min(rates):.0f}-{max(rates):.0f} unique fps)",
             "Pick a cadence per style (1s / 2s) and keep it consistent, or make the change a visible choice.")
    if pic["clip_white"] > 0.02 or pic["clip_black"] > 0.05:
        flag("low", "picture", f"Luminance clipping: white {pic['clip_white']:.1%}, black {pic['clip_black']:.1%}",
             "Keep highlight/shadow detail unless the style is intentionally graphic.")

    bd = pic.get("banding")
    if bd and bd["gradient_area"] >= 0.05 and bd["flat_share"] >= 0.25:
        flag("medium" if bd["flat_share"] >= 0.45 else "low", "delivery",
             f"Gradient banding: {bd['flat_share']:.0%} of the soft-gradient area ({bd['gradient_area']:.0%} of frame) is "
             f"perfectly flat steps (worst near {bd['worst_t']} s)",
             "Add a static dither before encoding (animkit finish.dither(img, 1.5): ~0% flat steps at ~2 Mbps); "
             "moving grain alone is smoothed away by x264 -tune animation and only survives -tune grain at "
             "15-50 Mbps. Check a dark-room or large-screen view.")

    h = info["height"]
    key = min(YT_RECOMMENDED_MBPS, key=lambda k: abs(k - h)) if h else None
    if key:
        rec = YT_RECOMMENDED_MBPS[key][1 if info["fps"] > 31 else 0]
        mbps = (info["v_bitrate"] or info["total_bitrate"]) / 1e6
        crf = info.get("x264_crf")
        if mbps and mbps < rec * 0.5 and crf is not None and crf <= 18:
            flag("info", "delivery",
                 f"Video bitrate {mbps:.1f} Mbps, but encoded at x264 CRF {crf:g} (quality-targeted)",
                 "Low bitrate here reflects simple content, not starvation. Spot-check gradients for banding; "
                 "no action needed otherwise.")
        elif mbps and mbps < rec * 0.5:
            busy = float(np.mean(pic["energy"])) > 0.8 if pic["energy"] else False
            flag("medium" if busy else "low", "delivery",
                 f"Video bitrate {mbps:.1f} Mbps vs ~{rec} Mbps platform upload guidance",
                 "Inspect for blocking/banding (flat graphics can legitimately encode small); for upload, export a "
                 "high-quality master (CRF 14-18 H.264 or ProRes) and let the platform transcode.")
    if mode == "film" and reel:
        if dur > 180:
            flag("high", "edit", f"Reel runs {dur / 60:.1f} min",
                 "Studio guidance is roughly 1-3 minutes (Pixar's careers FAQ says 'approximately one to three minutes'). Cut to the strongest 60-90 s; best work first.")
        flag("info", "edit", "Reel essentials checklist",
             "Best shot first; name + role + contact on first and last card; breakdown sheet listing what you did per shot; no filler holds.")

    if snd:
        L = snd["loudness"]
        if L["I"] is not None and abs(L["I"] - target_lufs) > 2:
            flag("medium", "sound", f"Integrated loudness {L['I']} LUFS (target {target_lufs})",
                 "Master with two-pass loudnorm to the platform target; keep true peak <= -1 dBTP.")
        if L["TP"] is not None and L["TP"] > -1.0:
            flag("medium", "sound", f"True peak {L['TP']} dBTP", "Leave >= 1 dB true-peak headroom for lossy encodes.")
        if mode == "film" and L["LRA"] is not None and L["LRA"] < 3 and dur > 30:
            flag("high", "sound", f"Loudness range {L['LRA']} LU: the mix is flat for the whole piece",
                 "Score and mix to the story: quiet beats, swells, silence before reveals, impacts that land.")
        lp = snd["loop"]
        if mode == "film" and lp["similarity"] and lp["similarity"] > 0.93 and (lp["contrast"] or 0) > 0.2 and lp["repeats"] >= 4:
            flag("high", "sound", f"Score is a {lp['best_lag_s']} s loop repeated ~{lp['repeats']}x (self-similarity {lp['similarity']})",
                 "Write sections that change with the picture (intro, development, lift, resolve); vary instrumentation and dynamics.")
        if mode == "film" and snd["score_sameness_across_shots"] and snd["score_sameness_across_shots"] > 0.95 and len(pic["shots"]) >= 4:
            flag("high", "sound", f"Music is near-identical across shots (similarity {snd['score_sameness_across_shots']})",
                 "Different pieces need different sonic identities; at minimum change key, tempo, palette or density per piece.")
        if snd["flat_noise_shots"]:
            flag("medium", "sound", f"{len(snd['flat_noise_shots'])} shots use flat white-noise ambience",
                 "Rain, traffic, wind and machinery are textured: shape the spectrum, add discrete events (drops, passes, clacks) and space.",
                 shots=[(s["start"], s["end"]) for s in snd["flat_noise_shots"]])
        if len(snd["silent_seconds"]) > dur * 0.2:
            flag("low", "sound", f"{len(snd['silent_seconds'])} silent seconds", "Confirm silence is intentional.")
    for item in flags:
        item.update(kind="review-candidate", mode=mode)
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    return sorted(flags, key=lambda f: order[f["severity"]])


def write_report(out_dir, path, info, pic, snd, flags):
    lines = [f"# QA report: {os.path.basename(path)}", ""]
    lines.append(f"{info['width']}x{info['height']} @ {info['fps']:.2f} fps, {info['duration']:.1f} s, "
                 f"video {((info['v_bitrate'] or info['total_bitrate']) / 1e6):.2f} Mbps, "
                 f"audio {'%s %d Hz %dch' % (info['acodec'], info['a_rate'], info['a_channels']) if info['has_audio'] else 'none'}")
    lines.append("")
    lines.append("## Flags")
    if not flags:
        lines.append("No automated flags. Automated checks do not cover acting, appeal, story or design: review the contact sheet and the film.")
    for f in flags:
        lines.append(f"- **{f['severity'].upper()} · {f['area']}**: {f['finding']}. Fix: {f['fix']}")
    lines.append("")
    lines.append("## Picture")
    shots = pic["shots"]
    lens = [s["len"] for s in shots]
    if lens:
        lines.append(f"- Cuts: {len(pic['cuts'])}; shots: {len(shots)}; average shot length {np.mean(lens):.2f} s; longest {max(lens):.2f} s")
    else:
        lines.append("- No shot interval long enough for the shot-length summary.")
    lines.append(f"- Frozen seconds: {len(pic['frozen_seconds'])}; near-still seconds: {len(pic['still_seconds'])}")
    lines.append("")
    lines.append("| # | start | len s | unique fps | motion | motion CV |")
    lines.append("|---|---|---|---|---|---|")
    for i, s in enumerate(shots, 1):
        lines.append(f"| {i} | {s['start']:.2f} | {s['len']:.2f} | {s['unique_fps']} | {s['motion']} | {s['motion_cv']} |")
    if snd:
        L = snd["loudness"]
        lines.append("")
        lines.append("## Sound")
        lines.append(f"- Integrated {L['I']} LUFS, LRA {L['LRA']} LU, true peak {L['TP']} dBTP")
        lp = snd["loop"]
        lines.append(f"- Strongest repetition: lag {lp['best_lag_s']} s, similarity {lp['similarity']} (contrast vs typical lag {lp['contrast']}), ~{lp['repeats']} repeats")
        lines.append(f"- Score sameness across shots: {snd['score_sameness_across_shots']}")
        lines.append(f"- Flat-noise ambience shots: {len(snd['flat_noise_shots'])}")
        lines.append(f"- Cuts landing on an audio onset (heuristic): {snd['cuts_on_audio_onset']}")
    lines.append("")
    lines.append("Requested artefact outcomes and measured coverage are recorded in report.json and its receipt.")
    lines.append("")
    lines.append("Scope: mechanical review candidates only. Acting, appeal, story clarity, design and staging still need visual review against references/qa-rubric.md; label model review and human review accurately.")
    with open(os.path.join(out_dir, "report.md"), "w") as fh:
        fh.write("\n".join(lines))


def main(argv=None):
    checks, errors, outputs = [], [], {}
    info = pic = snd = None
    flags, intervals = [], []
    a, fatal = None, False

    def artefact(id, filename, fn):
        path = os.path.join(a.out, filename)
        try:
            fn(path)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise CheckRunnerError("Expected output was not written", stage=id)
            outputs[id] = {"path": path, "status": "completed"}
            checks.append(check(id, "completed", "Nonempty output observed", observed=path))
        except Exception as exc:
            errors.append(error_detail(exc, id))
            outputs[id] = {"path": path, "status": "partial"}
            checks.append(check(id, "partial", "Requested output unavailable", evidence=errors[-1]))

    try:
        ap = CheckArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("video")
        ap.add_argument("--out", required=True)
        ap.add_argument("--reel", action="store_true", help="apply film reel review heuristics")
        ap.add_argument("--target-lufs", type=float, default=-14.0)
        ap.add_argument("--max-sheet", type=int, default=40)
        ap.add_argument("--no-sheet", action="store_true")
        ap.add_argument("--mode", choices=("film", "ui", "logo", "loop"), default="film")
        ap.add_argument("--sound", choices=("auto", "required", "silent"), default="auto")
        ap.add_argument("--allow-still", action="append", default=[], metavar="START:END")
        a = ap.parse_args(argv)
        if not math.isfinite(a.target_lufs) or a.max_sheet < 1:
            raise CheckRunnerError("Require finite target loudness and positive max-sheet", stage="input")
        for value in a.allow_still:
            start, end = map(float, value.split(":"))
            if not all(math.isfinite(v) for v in (start, end)) or not 0 <= start < end:
                raise CheckRunnerError("Still interval requires finite 0 <= start < end", stage="input")
            intervals.append((start, end))
        intervals.sort()
        if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
            raise CheckRunnerError("Still intervals overlap", stage="input")
        if _dependency_error:
            raise CheckRunnerError("numpy unavailable", stage="dependencies", code=_dependency_error)
        os.makedirs(a.out, exist_ok=True)
        info = probe(a.video)
        checks.append(check("probe", "completed", "Video metadata validated", observed=info))
        if any(end > info["duration"] for _, end in intervals):
            raise CheckRunnerError("Still interval exceeds duration", stage="input")
        if a.sound == "required":
            checks.append(check("sound-policy", "completed" if info["has_audio"] else "failed",
                                "Audio stream required by brief", observed=info["has_audio"], expected=True))
        elif a.sound == "silent":
            checks.append(check("sound-policy", "failed" if info["has_audio"] else "completed",
                                "Silent delivery requires no audio stream (track presence, not perceptual silence)",
                                observed=info["has_audio"], expected=False))
        else:
            checks.append(check("sound-policy", "not-applicable", "No hard audio-presence requirement"))
        pic = picture_analysis(a.video, info)
        checks.append(check("picture", "completed", "Decoded picture metrics measured"))
        if pic.get("subject_height") is None:
            checks.append(check("subject-height", "partial", "Optional subject analysis unavailable"))
        else:
            checks.append(check("subject-height", "completed" if pic["subject_height"] else "not-applicable",
                                "Subject metric measured" if pic["subject_height"] else "Too short for per-second subject metric"))
        analysis_errors = pic.get("analysis_errors", [])
        if analysis_errors:
            errors.extend(analysis_errors)
            checks.append(check("banding", "partial", "Banding samples incomplete", evidence=analysis_errors))
        else:
            checks.append(check("banding", "completed" if pic.get("banding") is not None else "not-applicable",
                                "Gradient samples measured" if pic.get("banding") is not None else "No eligible gentle gradient in sampled frames"))
        if a.sound == "silent" or not info["has_audio"]:
            checks.append(check("audio-analysis", "not-applicable", "Declared silent delivery" if a.sound == "silent" else "No audio stream"))
            checks.append(check("loudness", "not-applicable", "No requested audio analysis"))
        else:
            try:
                snd = sound_analysis(a.video, info, pic["shots"], pic["cuts"])
                if snd is None:
                    raise CheckRunnerError("Audio analysis did not yield measurements", stage="audio-analysis")
                checks.append(check("audio-analysis", "completed", "Audio metrics measured"))
                loud = snd.get("loudness", {})
                if any(loud.get(k) is None for k in ("I", "LRA", "TP")):
                    checks.append(check("loudness", "partial", "Loudness values unavailable; absent or -inf is not a zero measurement", observed=loud))
                else:
                    checks.append(check("loudness", "completed", "Loudness values observed", observed=loud))
            except ImportError as exc:
                errors.append(error_detail(exc, "audio-analysis"))
                checks.append(check("audio-analysis", "partial", "Optional analysis dependency unavailable", evidence=errors[-1]))
                checks.append(check("loudness", "partial", "Audio analysis unavailable"))
        flags = verdicts(info, pic, snd, reel=a.reel, target_lufs=a.target_lufs, mode=a.mode, allow_still=intervals)
        for id in ("staging", "long-shots", "mechanical-motion", "frame-cadence", "story-score"):
            state = "completed" if a.mode == "film" else "not-applicable"
            reason = "Film review heuristic evaluated, not a hard quality gate" if a.mode == "film" else f"Film assumption omitted for {a.mode} mode"
            if a.mode == "film" and id == "staging" and pic.get("subject_height") is None:
                state, reason = "partial", "Subject analysis unavailable; staging heuristic not evaluated"
            if a.mode == "film" and id == "story-score" and snd is None:
                state = "partial" if info["has_audio"] and a.sound != "silent" else "not-applicable"
                reason = "Audio analysis unavailable" if state == "partial" else "No requested audio analysis"
            checks.append(check(id, state, reason))
        checks.append(check("stillness", "not-applicable" if a.mode in ("ui", "loop") else "completed",
                            "Resting states valid in this mode" if a.mode in ("ui", "loop") else "Review heuristic excludes only fully declared one-second intervals",
                            declared_intervals=intervals))
        checks.append(check("loop-seam", "partial" if a.mode == "loop" else "not-applicable",
                            "Loop seam requires separate playback/frame comparison; not implemented by this scan" if a.mode == "loop" else "Not loop mode"))
        if a.no_sheet:
            checks.append(check("contact-sheet", "not-applicable", "Explicitly not requested"))
        else:
            artefact("contact-sheet", "contact_sheet.png", lambda path: contact_sheet(a.video, info, path, a.max_sheet))
        artefact("motion-plot", "motion.png", lambda path: motion_plot(pic, path, info["duration"]))
        if info["has_audio"] and a.sound != "silent":
            artefact("spectrum", "spectrum.png", lambda path: sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.video,
                     "-lavfi", "showspectrumpic=s=1600x420:legend=1:scale=log", path]))
        else:
            checks.append(check("spectrum", "not-applicable", "No requested audio analysis"))
        artefact("human-report", "report.md", lambda path: write_report(a.out, a.video, info, pic, snd, flags))
    except Exception as exc:
        fatal = True
        errors.append(error_detail(exc))
        checks.append(check("execution", "runner-error", "Scan interrupted; prior observations retained", evidence=errors[-1]))
    # Every stage that could not be reached remains explicit, including after a late error.
    seen = {c["id"] for c in checks}
    for id in ("probe", "sound-policy", "picture", "subject-height", "banding", "audio-analysis", "loudness", "staging", "long-shots",
               "mechanical-motion", "frame-cadence", "story-score", "stillness", "loop-seam", "contact-sheet", "motion-plot", "spectrum", "human-report"):
        if id not in seen:
            checks.append(check(id, "partial", "Not reached after runner error"))
    observations = {"info": info, "picture": {k: v for k, v in pic.items() if k != "diff"} if pic else None,
                    "sound": snd, "flags": flags}

    def assemble():
        return result("reel_critic", checks, errors, fatal=fatal, outputs=outputs, **observations,
                      mode=a.mode if a else None, sound_policy=a.sound if a else None, declared_still=intervals,
                      meaning="Measured review candidates and applicable hard criteria; completed is not visual approval. Loop seam/browser behaviour require separate evidence.")

    receipt = assemble()
    if a is not None:
        target = os.path.join(a.out, "report.json")
        outputs["machine-report"] = {"path": target, "status": "completed"}
        try:
            receipt = assemble()
            with open(target, "w", encoding="utf-8") as fh:
                json.dump(receipt, fh, indent=1, allow_nan=False)
        except Exception as exc:
            fatal = True
            errors.append(error_detail(exc, "machine-report"))
            outputs["machine-report"]["status"] = "runner-error"
            checks.append(check("machine-report", "runner-error", "Final report not persisted; stderr retains observations", evidence=errors[-1]))
            receipt = assemble()
        if outputs.get("human-report", {}).get("status") == "completed":
            try:
                with open(os.path.join(a.out, "report.md"), encoding="utf-8") as fh:
                    print(fh.read())
            except OSError:
                pass  # Delivery state is already recorded; stdout is a convenience copy.
    return emit(receipt)


if __name__ == "__main__":
    sys.exit(main())
