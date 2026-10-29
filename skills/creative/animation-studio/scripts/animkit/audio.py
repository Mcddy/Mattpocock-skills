"""Sound design, score and mix in numpy, mastered with ffmpeg loudnorm.

Principles baked in (references/sound.md):
* Every on-screen contact gets a sound, placed from the CueSheet (sync by construction).
* Never repeat an identical sample: footsteps/drops get per-instance pitch, level
  and timbre variation (the 'machine-gun' effect reads as fake instantly).
* Ambience is textured (bed + discrete events + space), not flat white noise.
* Music follows the story: sections, dynamics and silence are scored to beats,
  not a loop under everything.
* Master to a stated loudness target with true-peak headroom; keep dynamic range.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
A4 = 440.0
_NOTE = {"C": -9, "C#": -8, "Db": -8, "D": -7, "D#": -6, "Eb": -6, "E": -5, "F": -4, "F#": -3,
         "Gb": -3, "G": -2, "G#": -1, "Ab": -1, "A": 0, "A#": 1, "Bb": 1, "B": 2}


def hz(note: str) -> float:
    """'A4' -> 440.0, 'C#3' -> 138.59"""
    m = re.fullmatch(r"([A-G][#b]?)(-?\d)", note)
    if not m:
        raise ValueError(note)
    n, octv = m.group(1), int(m.group(2))
    return A4 * 2 ** ((_NOTE[n] + 12 * (octv - 4)) / 12)


def db(x: float) -> float:
    return 10 ** (x / 20)


def t_axis(dur: float):
    return np.arange(int(dur * SR)) / SR


# ------------------------------------------------------------------ envelopes
def adsr(n: int, a=0.01, d=0.1, s=0.7, r=0.2):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, n - a_n - d_n - r_n)
    env = np.concatenate([
        np.linspace(0, 1, max(a_n, 1), endpoint=False) ** 1.5,
        np.linspace(1, s, max(d_n, 1), endpoint=False),
        np.full(s_n, s),
        np.linspace(s, 0, max(r_n, 1)) ** 1.3,
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def decay(n: int, tau: float):
    return np.exp(-np.arange(n) / (tau * SR))


def fade(sig, fin=0.005, fout=0.01):
    """Micro-fades: no clicks at sample boundaries, ever."""
    sig = sig.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a:
        sig[:a] *= np.linspace(0, 1, a)[:, None] if sig.ndim == 2 else np.linspace(0, 1, a)
    if b:
        sig[-b:] *= np.linspace(1, 0, b)[:, None] if sig.ndim == 2 else np.linspace(1, 0, b)
    return sig


# ------------------------------------------------------------------ sources
def sine(f, dur, phase=0.0):
    return np.sin(2 * np.pi * f * t_axis(dur) + phase)


def saw(f, dur, harmonics=None):
    """Band-limited saw (additive) - no aliasing fizz."""
    t = t_axis(dur)
    nmax = harmonics or max(1, int((SR / 2 - 1000) / max(f, 1)))
    nmax = min(nmax, 60)
    out = np.zeros_like(t)
    for k in range(1, nmax + 1):
        out += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * f * t) / k
    return out * (2 / np.pi)


def tri(f, dur):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for i, k in enumerate(range(1, 30, 2)):
        out += ((-1) ** i) * np.sin(2 * np.pi * k * f * t) / (k * k)
    return out * (8 / np.pi ** 2)


def noise(dur, color="pink", seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    w = rng.standard_normal(n)
    if color == "white":
        return w / 3
    spec = np.fft.rfft(w)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    freqs[0] = freqs[1]
    if color == "pink":
        spec /= np.sqrt(freqs)
    elif color == "brown":
        spec /= freqs
    out = np.fft.irfft(spec, n)
    return out / (np.max(np.abs(out)) + 1e-9)


def filt(sig, kind, f, order=2):
    """kind: 'lp' | 'hp' | 'bp' (f=(lo, hi))"""
    btype = {"lp": "lowpass", "hp": "highpass", "bp": "bandpass"}[kind]
    sos = signal.butter(order, f, btype=btype, fs=SR, output="sos")
    return signal.sosfilt(sos, sig, axis=0)


def karplus(f, dur, damp=0.996, seed=0, bright=0.5):
    """Plucked string."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    buf = filt(buf, "lp", min(SR / 2 - 100, 2000 + 8000 * bright), 1)
    blocks = []
    for _ in range(n // p + 1):          # block-wise update: fast, near-identical tone
        blocks.append(buf.copy())
        buf = damp * 0.5 * (buf + np.roll(buf, -1))
    return np.concatenate(blocks)[:n]


def modal(freqs, decays, amps, dur, seed=0, jitter=0.02):
    """Struck object: sum of exponentially decaying partials (metal, wood, glass)."""
    rng = np.random.default_rng(seed)
    t = t_axis(dur)
    out = np.zeros_like(t)
    for f, d, a in zip(freqs, decays, amps):
        f2 = f * (1 + rng.uniform(-jitter, jitter))
        out += a * np.sin(2 * np.pi * f2 * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    return out


# ------------------------------------------------------------------ SFX library
def footstep(seed=0, wet=0.0, weight=1.0, surface="stone"):
    rng = np.random.default_rng(seed)
    dur = 0.35
    n = int(dur * SR)
    pitch = rng.uniform(0.85, 1.15)
    thud = sine(70 * pitch * (0.8 + 0.4 / weight), dur) * decay(n, 0.035 * weight)
    scuff = filt(noise(dur, "pink", seed), "bp", (500 * pitch, 3500 * pitch)) * decay(n, 0.02)
    sig = 0.9 * thud + (0.5 if surface == "stone" else 0.3) * scuff
    if wet > 0:
        spl = filt(noise(dur, "white", seed + 99), "bp", (1500, 7000)) * decay(n, 0.05)
        delay = int(rng.uniform(0.004, 0.012) * SR)
        spl = np.concatenate([np.zeros(delay), spl])[:n]
        sig += wet * 0.6 * spl
    return fade(sig * rng.uniform(0.8, 1.0))


def cloth(dur=0.4, seed=0, level=0.5):
    """Rustle: band-passed noise with a lumpy amplitude contour."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    base = filt(noise(dur, "pink", seed), "bp", (900, 6000))
    lumps = np.interp(np.arange(n), np.linspace(0, n, 9), rng.uniform(0.2, 1.0, 9))
    return fade(base * lumps * adsr(n, 0.05, 0.1, 0.8, 0.15) * level)


def paper(dur=0.5, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    crisp = filt(noise(dur, "white", seed), "hp", 2500)
    crackle = np.zeros(n)
    for _ in range(int(dur * 40)):
        i = rng.integers(0, n - 200)
        crackle[i:i + 200] += rng.uniform(0.3, 1.0) * decay(200, 0.0008)
    body = filt(0.35 * crisp + 0.6 * filt(crackle, "hp", 1800), "lp", 8500)
    return fade(body * adsr(n, 0.04, 0.1, 0.6, 0.2))


def metal_flap(seed=0, size=1.0):
    """Letterbox flap / latch: inharmonic metal partials + click transient."""
    rng = np.random.default_rng(seed)
    base = 520 / size
    ratios = [1.0, 2.32, 3.61, 4.95, 6.7, 8.9]
    tone = modal([base * r for r in ratios], [0.18, 0.11, 0.08, 0.05, 0.04, 0.03],
                 [1, 0.6, 0.45, 0.3, 0.2, 0.15], 0.6, seed)
    click = filt(noise(0.6, "white", seed), "hp", 3000) * decay(int(0.6 * SR), 0.003)
    return fade(0.55 * tone + 0.8 * click) * rng.uniform(0.9, 1.0)


def switch_click(seed=0):
    n = int(0.12 * SR)
    a = filt(noise(0.12, "white", seed), "bp", (1800, 9000)) * decay(n, 0.0025)
    b = np.roll(a, int(0.018 * SR)) * 0.6
    return fade(a + b)


def thump(seed=0, pitch=1.0):
    n = int(0.4 * SR)
    t = t_axis(0.4)
    sweep = np.sin(2 * np.pi * (90 * pitch) * t * (1 - 0.6 * t)) * decay(n, 0.06)
    return fade(sweep + 0.2 * filt(noise(0.4, "pink", seed), "lp", 900) * decay(n, 0.03))


def whoosh(dur=0.6, seed=0, lo=300, hi=4000):
    n = int(dur * SR)
    src = noise(dur, "pink", seed)
    out = np.zeros(n)
    hop = 1024
    centres = np.geomspace(lo, hi, n // hop + 1)
    for i, c in enumerate(centres):
        s = i * hop
        seg = src[s:s + hop]
        if not len(seg):
            break
        out[s:s + len(seg)] = filt(seg, "bp", (c * 0.7, min(c * 1.4, SR / 2 - 100)), 1)
    return fade(out * np.sin(np.linspace(0, np.pi, n)) ** 1.5)


def hum(dur, f=60.0, level=0.05):
    t = t_axis(dur)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t)) * level


def rain(dur, intensity=0.6, seed=0, drops_per_s=120):
    """Textured rain: shaped bed + discrete droplets + occasional heavier drips (stereo)."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    bed_l = filt(noise(dur, "pink", seed), "bp", (400, 9000))
    bed_r = filt(noise(dur, "pink", seed + 1), "bp", (400, 9000))
    swell = 0.75 + 0.25 * np.interp(np.arange(n), np.linspace(0, n, max(3, int(dur / 2))),
                                     rng.uniform(0, 1, max(3, int(dur / 2))))
    out = np.stack([bed_l * swell, bed_r * swell], 1) * 0.35 * intensity
    m = int(dur * drops_per_s * intensity)
    for _ in range(m):
        i = rng.integers(0, max(1, n - 3000))
        L = rng.integers(400, 2400)
        f0 = rng.uniform(1800, 6500)
        d = np.sin(2 * np.pi * f0 * np.arange(L) / SR * (1 + 0.5 * np.arange(L) / L)) * decay(L, rng.uniform(0.002, 0.01))
        g = rng.uniform(0.02, 0.16) * intensity
        pan = rng.uniform(-1, 1)
        out[i:i + L, 0] += d * g * math.cos((pan + 1) * math.pi / 4)
        out[i:i + L, 1] += d * g * math.sin((pan + 1) * math.pi / 4)
    for _ in range(int(dur * 1.5)):
        i = rng.integers(0, max(1, n - 12000))
        drip = modal([rng.uniform(700, 1400)], [0.04], [1], 0.25, int(rng.integers(0, 1e6)))
        L = len(drip)
        g = rng.uniform(0.05, 0.12)
        out[i:i + L, 0] += drip * g
        out[i:i + L, 1] += drip * g * rng.uniform(0.5, 1.0)
    return out


# ------------------------------------------------------------------ space
def reverb(sig, mix=0.2, decay_s=1.2, predelay=0.02, damp=6000, seed=3):
    """Convolution with a synthetic stereo IR. Use for space, not mud: keep mix low."""
    rng = np.random.default_rng(seed)
    n = int(decay_s * SR)
    env = np.exp(-6.9 * np.arange(n) / n)
    irl = filt(rng.standard_normal(n) * env, "lp", damp)
    irr = filt(rng.standard_normal(n) * env, "lp", damp)
    pd = int(predelay * SR)
    irl = np.concatenate([np.zeros(pd), irl])
    irr = np.concatenate([np.zeros(pd), irr])
    irl /= np.sqrt(np.sum(irl ** 2)) + 1e-9
    irr /= np.sqrt(np.sum(irr ** 2)) + 1e-9
    if sig.ndim == 1:
        sig = np.stack([sig, sig], 1)
    wl = signal.fftconvolve(sig[:, 0], irl)[: len(sig)]
    wr = signal.fftconvolve(sig[:, 1], irr)[: len(sig)]
    return sig * (1 - mix) + np.stack([wl, wr], 1) * mix * 2.5


# ------------------------------------------------------------------ mixer
class Mix:
    def __init__(self, duration: float):
        self.n = int(math.ceil(duration * SR))
        self.buses: dict[str, np.ndarray] = {}

    def bus(self, name):
        if name not in self.buses:
            self.buses[name] = np.zeros((self.n, 2))
        return self.buses[name]

    def add(self, sig, at: float, gain_db=0.0, pan=0.0, bus="sfx"):
        b = self.bus(bus)
        sig = np.asarray(sig, float)
        if sig.ndim == 1:
            a = (pan + 1) * math.pi / 4
            sig = np.stack([sig * math.cos(a), sig * math.sin(a)], 1) * math.sqrt(2)
        i = int(round(at * SR))
        if i >= self.n:
            return self
        if i < 0:
            sig = sig[-i:]
            i = 0
        L = min(len(sig), self.n - i)
        b[i:i + L] += sig[:L] * db(gain_db)
        return self

    def process(self, bus, fn):
        self.buses[bus] = fn(self.bus(bus))
        return self

    def render(self, levels: dict | None = None, duck: tuple | None = None):
        """Sum buses. duck=(target_bus, key_bus, depth_db) sidechains music under SFX/VO."""
        levels = levels or {}
        out = np.zeros((self.n, 2))
        if duck:
            tgt, key, depth = duck
            if tgt in self.buses and key in self.buses:
                env = np.abs(self.buses[key]).max(1)
                env = signal.sosfilt(signal.butter(1, 8, fs=SR, output="sos"), env)
                env = env / (env.max() + 1e-9)
                self.buses[tgt] = self.buses[tgt] * (1 - (1 - db(-abs(depth))) * env)[:, None]
        for name, b in self.buses.items():
            out += b * db(levels.get(name, 0.0))
        return out


# ------------------------------------------------------------------ mastering
def write_wav(path, sig):
    sig = np.asarray(sig, np.float32)
    peak = np.max(np.abs(sig))
    if peak > 1:
        sig = sig / peak
    wavfile.write(path, SR, sig)
    return path


def loudness(path: str) -> dict:
    """Integrated LUFS, LRA, true peak via ffmpeg ebur128."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    def grab(label):
        m = re.search(label + r":\s+(-?[\d.]+)", txt)
        return float(m.group(1)) if m else None
    return {"I": grab("I"), "LRA": grab("LRA"), "TP": grab("Peak")}


def master(sig, out_path: str, target_lufs=-14.0, true_peak=-1.5, lra=11.0) -> dict:
    """Two-pass EBU R128 loudnorm. Returns measured stats of the result.

    -1.5 dBTP default: AAC/MP3 encoding adds inter-sample overshoot, so a -1.0 master
    measures above -1.0 after encoding.
    """
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "premaster.wav")
        write_wav(raw, sig * 0.5)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af",
                            f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True)
        js = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
        af = (f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:measured_I={js['input_i']}:"
              f"measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:"
              f"offset={js['target_offset']}:linear=true,aresample={SR}")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-af", af,
                        "-ar", str(SR), "-c:a", "pcm_s24le", out_path], check=True)
    return loudness(out_path)


# ------------------------------------------------------------------ score helpers
def pad(freqs, dur, attack=1.2, release=1.5, bright=0.35, detune=0.006, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    for f in freqs:
        for d in (-detune, 0, detune):
            out += saw(f * (1 + d + rng.uniform(-0.001, 0.001)), dur, harmonics=18)
    out = filt(out, "lp", 400 + 3600 * bright)
    out *= adsr(n, attack, 0.3, 0.85, release)
    return out / (len(freqs) * 3)


def keys_note(f, dur, vel=0.7, seed=0):
    """Soft electric-piano-ish tone (good for gentle melodies)."""
    n = int(dur * SR)
    t = t_axis(dur)
    mod = np.sin(2 * np.pi * f * 1.0 * t) * 1.2 * np.exp(-t / 0.5)
    car = np.sin(2 * np.pi * f * t + mod)
    return car * adsr(n, 0.004, 0.4, 0.35, 0.4) * vel * np.exp(-t / 2.5)


def bass(f, dur, vel=0.8):
    n = int(dur * SR)
    return filt(tri(f, dur), "lp", 600) * adsr(n, 0.01, 0.2, 0.6, 0.15) * vel


# ---------------------------------------------------------------- more Foley (v3)
def scrape(speed_env, sr=SR, seed=0, wood=True):
    """Something dragged/pushed across a floor. speed_env: per-sample (or short array resampled) speed 0..1.
    Stick-slip grain comes from noise bursts gated by speed; louder and brighter as it moves faster."""
    env = np.asarray(speed_env, float)
    n = len(env) if len(env) > 1000 else int(len(env) * sr / 24)
    if len(env) != n:
        env = np.interp(np.linspace(0, len(env) - 1, n), np.arange(len(env)), env)
    rng = np.random.default_rng(seed)
    base = noise(n / sr, "pink", seed)[:n]
    grain = (rng.random(n) < 0.004 + 0.02 * env).astype(float)
    grain = np.convolve(grain, np.exp(-np.arange(int(0.004 * sr)) / (0.001 * sr)), "same")
    sig = filt(base, "bp", (180, 2200) if wood else (400, 6000)) * (0.35 + 0.65 * env) + filt(base * grain, "bp", (300, 3000)) * 2.0
    return fade(sig * env, 0.02, 0.05)


def spring_boing(f0=180.0, dur=0.45, seed=0):
    """A springy antenna/hood tip snapping and wobbling (pitch bends down as it settles)."""
    t = t_axis(dur)
    f = f0 * (1.6 * np.exp(-t * 18) + 1.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    wob = 1 + 0.25 * np.sin(2 * np.pi * 11 * t) * np.exp(-t * 6)
    sig = np.sin(ph) * np.exp(-t * 7) * wob + 0.3 * np.sin(2 * ph) * np.exp(-t * 10)
    return fade(sig * 0.6, 0.002, 0.05)


def crunch(seed=0, dur=0.22):
    """A biscuit bite: a cluster of short, bright cracks."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    sig = np.zeros(n)
    for _ in range(rng.integers(6, 11)):
        at = int(rng.uniform(0, 0.6) * n)
        ln = int(rng.uniform(0.003, 0.012) * SR)
        burst = rng.normal(0, 1, ln) * np.exp(-np.arange(ln) / (ln / 4))
        sig[at:at + ln] += burst[: max(0, min(ln, n - at))] * rng.uniform(0.4, 1.0)
    return fade(filt(sig, "bp", (1500, 7000)) * 0.8, 0.001, 0.02)
