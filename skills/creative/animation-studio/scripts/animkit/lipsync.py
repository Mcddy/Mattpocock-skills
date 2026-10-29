"""Audio-driven lip sync for BlobRig(face_rig=True) (or any mouth you draw).

    lip = lipsync.from_audio("line.wav", fps=24, start_frame=48)
    perf = Performer(rig, walks, frames, channels={**track.channels(), **lip.channels()})

How it works (no speech model, offline): per frame, loudness drives jaw opening;
spectral centroid separates round vowels (O/U, low centroid) from wide ones (E/I,
high centroid); hiss-like frames (S/F/SH: high zero-crossing rate, high centroid)
get a narrow, slightly open mouth; quiet frames close (M/B/P and rests).

Animator rules applied: the mouth shape leads the sound by one frame, mouth changes
are held at least two frames (on twos), tiny flutters are removed, and every
phrase ends closed. It reads as convincing dialogue at a distance and in
stylised work; for close-ups or exact visemes, key the shapes by hand from the
transcript (the expression's mouth_curve still carries the emotion underneath).
"""
from __future__ import annotations

import numpy as np

from .curves import Channel, K


def _load(src, sr=None):
    if isinstance(src, str):
        import subprocess
        raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "24000",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32).astype(np.float64), 24000
    x = np.asarray(src, np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1 if x.shape[1] <= 8 else 0)
    return x, int(sr or 24000)


class LipSync:
    def __init__(self, open_, round_, width, fps, start_frame):
        self.open, self.round, self.width = open_, round_, width
        self.fps, self.start = fps, start_frame

    def channels(self) -> dict:
        """{'lip_open', 'lip_round', 'lip_width'} Channels (Performer layers them over the expression's mouth)."""
        out = {}
        for name, arr in (("lip_open", self.open), ("lip_round", self.round), ("lip_width", self.width)):
            ks = [K(self.start - 1, 0.0 if name != "lip_width" else 0.5)]
            for i, v in enumerate(arr):
                ks.append(K(self.start + i, float(v)))
            ks.append(K(self.start + len(arr), 0.0 if name != "lip_width" else 0.5))
            out[name] = Channel(ks)
        return out

    def report(self) -> dict:
        o = self.open
        return {"frames": len(o), "open_frames": int((o > 0.05).sum()), "closures": int(((o[1:] <= 0.05) & (o[:-1] > 0.05)).sum()),
                "max_open": round(float(o.max()) if len(o) else 0.0, 2)}


def from_audio(src, sr=None, fps=24.0, start_frame=0, lead=1, min_hold=2, floor_pct=20, peak_pct=95) -> LipSync:
    x, sr = _load(src, sr)
    hop = sr / fps
    n = int(len(x) / hop)
    win = int(hop * 1.5)
    rms, cen, zcr = np.zeros(n), np.zeros(n), np.zeros(n)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    band = (freqs > 150) & (freqs < 6000)
    hann = np.hanning(win)
    for i in range(n):
        c = int((i + 0.5) * hop)
        seg = x[max(0, c - win // 2): max(0, c - win // 2) + win]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        rms[i] = np.sqrt(np.mean(seg ** 2)) + 1e-9
        mag = np.abs(np.fft.rfft(seg * hann))[band]
        cen[i] = float((freqs[band] * mag).sum() / (mag.sum() + 1e-12))
        zcr[i] = float(np.mean(np.abs(np.diff(np.sign(seg))) > 0))
    db = 20 * np.log10(rms)
    lo, hi = np.percentile(db, floor_pct), np.percentile(db, peak_pct)
    if hi - lo < 6:
        lo = hi - 30
    op = np.clip((db - lo - 6) / max(1e-6, hi - lo - 6), 0, 1) ** 0.85
    rnd = np.clip((1100 - cen) / 500, 0, 1)
    wid = np.clip((cen - 1300) / 1300, 0, 1) * 0.6 + 0.4 * (1 - rnd)
    hiss = (zcr > 0.25) & (cen > 3000)
    op = np.where(hiss, np.minimum(op, 0.22), op)
    rnd = np.where(hiss, 0.0, rnd)
    wid = np.where(hiss, 0.7, wid)
    op = np.where(op < 0.08, 0.0, op)
    # median-of-3 to kill flutter, then hold on twos
    def med3(a):
        b = a.copy()
        b[1:-1] = np.median(np.stack([a[:-2], a[1:-1], a[2:]]), 0)
        return b
    op, rnd, wid = med3(op), med3(rnd), med3(wid)
    if min_hold > 1:
        for a in (op, rnd, wid):
            for i in range(0, len(a), min_hold):
                a[i:i + min_hold] = a[i]
    if lead:
        op, rnd, wid = (np.r_[a[lead:], np.zeros(lead) if a is not wid else np.full(lead, 0.5)] for a in (op, rnd, wid))
    return LipSync(op, rnd, wid, fps, start_frame)
