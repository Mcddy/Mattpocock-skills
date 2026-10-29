"""Timing, cue sheets and the render loop.

* Beats: name story beats in seconds, get frames back. Lock timing in the
  animatic, then animate to it.
* CueSheet: every sound-worthy event (contacts, impacts, switches, cuts) is
  logged here by the animation code itself, so audio is synced by construction.
* render(): draws frames (optionally motion-blurred), pipes them to ffmpeg,
  writes review stills, and muxes audio.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .canvas import Canvas, accumulate


@dataclass
class Beats:
    fps: float = 24.0
    marks: dict = field(default_factory=dict)

    def at(self, name: str, seconds: float):
        self.marks[name] = seconds
        return self

    def f(self, name: str) -> float:
        return self.marks[name] * self.fps

    def table(self) -> str:
        rows = sorted(self.marks.items(), key=lambda kv: kv[1])
        return "\n".join(f"{v:7.2f}s  f{v * self.fps:6.0f}  {k}" for k, v in rows)


@dataclass
class CueSheet:
    fps: float = 24.0
    cues: list = field(default_factory=list)

    def add(self, frame: float, kind: str, **params):
        self.cues.append({"frame": float(frame), "t": float(frame) / self.fps, "kind": kind, **params})
        return self

    def of(self, kind: str):
        return [c for c in self.cues if c["kind"] == kind]

    def save(self, path: str):
        with open(path, "w") as fh:
            json.dump(sorted(self.cues, key=lambda c: c["frame"]), fh, indent=1)


def ffmpeg_writer(out_path, w, h, fps, crf=16, preset="medium", tune="animation", pix_fmt="yuv420p"):
    # tune "animation" smooths away fine *moving* grain, so gradients band unless they carry a static
    # dither (finish.dither, used by the examples' post). Pass tune="grain" only when moving film grain
    # is part of the look; it costs 15-50 Mbps at 1080p.
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-tune", tune,
           "-pix_fmt", pix_fmt, "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-movflags", "+faststart", out_path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


_JOB: dict = {}


def _frame(i: int) -> np.ndarray:
    j = _JOB
    w, h, mb, shutter = j["w"], j["h"], j["mb"], j["shutter"]
    if mb > 1:
        subs = []
        for s in range(mb):
            off = shutter * ((s + 0.5) / mb - 0.5)
            cv = Canvas(w, h)
            j["draw"](cv, i + off)
            subs.append(cv.array())
        img = accumulate(subs)
    else:
        cv = Canvas(w, h)
        j["draw"](cv, float(i))
        img = cv.array()
    if j["post"]:
        img = j["post"](img, i)
    return img


def _mem_available() -> int | None:
    """Bytes this process can still use: the smaller of MemAvailable and any cgroup limit."""
    vals = []
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    vals.append(int(line.split()[1]) * 1024)
    except OSError:
        pass
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            raw = open(path).read().strip()
            if raw.isdigit() and int(raw) < 1 << 60:
                used = 0
                for upath in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
                    try:
                        used = int(open(upath).read().strip())
                        break
                    except (OSError, ValueError):
                        continue
                vals.append(int(raw) - used)
        except OSError:
            continue
    return min(vals) if vals else None


def auto_workers(w: int, h: int) -> int:
    """Parallel workers that fit in memory. Measured peak per worker at 1080p: ~410 MB on the soft
    backend, ~260 MB on Skia (plus motion-blur buffers). Too many workers get killed by the
    out-of-memory killer, which used to stall the render silently."""
    from . import canvas as _CV
    soft = _CV.BACKEND == "soft"
    per = w * h * (460 if soft else 200)          # 2x the measured peak: scenes with many layers use more
    cpus = min(os.cpu_count() or 1, 4 if soft else 8)
    avail = _mem_available()
    if avail is None:
        return max(1, min(cpus, 2))
    return max(1, min(cpus, int(avail * 0.6 // per)))


class WorkerDied(RuntimeError):
    def __init__(self, done, workers):
        super().__init__(f"a render worker died after {done} frames (usually out of memory with {workers} workers)")
        self.done, self.workers = done, workers


def _ordered(fn, frames, workers):
    """Yield fn(i) in order, in forked worker processes. A worker that dies (usually out of memory)
    raises an error with the fix instead of hanging the render."""
    if workers <= 1:
        yield from map(fn, frames)
        return
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool
    frames = list(frames)
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as ex:
        done = 0
        try:
            for k in range(0, len(frames), workers * 4):          # bounded look-ahead keeps memory flat
                batch = frames[k:k + workers * 4]
                for img in ex.map(fn, batch):
                    done += 1
                    yield img
        except BrokenProcessPool:
            raise WorkerDied(done, workers) from None


def _resilient(fn, frames, workers, state):
    """_ordered, but when a worker dies (memory) it carries on from the same frame with half the
    workers, down to one, so a long render survives a scene that needs more memory than estimated."""
    frames = list(frames)
    pos = 0
    while True:
        try:
            for img in _ordered(fn, frames[pos:], workers):
                pos += 1
                yield img
            return
        except WorkerDied:
            if workers <= 1:
                raise RuntimeError("the render process ran out of memory with one worker: lower the "
                                   "resolution of heavy layers, bound blurred layers, or render in chunks") from None
            workers = max(1, workers // 2)
            state["workers"] = workers
            print(f"render: a worker died (out of memory?) at frame {frames[pos]}; continuing with "
                  f"{workers} worker(s)", flush=True)


def render(draw: Callable[[Canvas, float], None], n_frames: int, out_path: str, *, w=1920, h=1080,
           fps=24.0, mb_samples=1, shutter=0.5, post: Callable[[np.ndarray, int], np.ndarray] | None = None,
           stills_dir: str | None = None, stills_every: int = 24, start: int = 0, crf=16,
           log_every: int = 48, workers: int | None = None, tune: str = "animation") -> dict:
    """Render frames [start, start+n_frames) to an H.264 file.

    draw(canvas, f) must be a pure function of time f (float), so sub-frame
    samples for motion blur are exact. shutter=0.5 is a 180-degree shutter.
    workers > 1 renders frames in forked processes (draw/post must be module-level
    and deterministic); frames are written in order.
    """
    if stills_dir:
        os.makedirs(stills_dir, exist_ok=True)
    _JOB.update(draw=draw, w=w, h=h, mb=mb_samples, shutter=shutter, post=post)
    workers = workers or auto_workers(w, h)
    proc = ffmpeg_writer(out_path, w, h, fps, crf=crf, tune=tune)
    t0 = time.time()
    frames = range(start, start + n_frames)
    state = {"workers": workers}
    it = _resilient(_frame, frames, workers, state)
    try:
        for k, img in enumerate(it):           # exhaust the generator so the worker pool shuts down
            i = start + k
            proc.stdin.write(img.tobytes())
            if stills_dir and (i - start) % stills_every == 0:
                from PIL import Image
                Image.fromarray(img).save(os.path.join(stills_dir, f"f{i:05d}.png"))
            if log_every and (i - start) % log_every == 0:
                el = time.time() - t0
                print(f"frame {i - start}/{n_frames}  {el:.0f}s elapsed", flush=True)
    except BaseException:
        proc.stdin.close()
        proc.kill()
        proc.wait()
        raise
    proc.stdin.close()
    proc.wait()
    return {"frames": n_frames, "seconds": round(time.time() - t0, 1), "path": out_path, "workers": state["workers"]}


def _frame_rgba(i: int) -> np.ndarray:
    j = _JOB
    w, h, mb, shutter = j["w"], j["h"], j["mb"], j["shutter"]
    subs = []
    for s in range(max(1, mb)):
        off = shutter * ((s + 0.5) / mb - 0.5) if mb > 1 else 0.0
        cv = Canvas(w, h)                       # transparent: draw() must not paint a full background
        j["draw"](cv, i + off)
        a = cv.rgba_array().astype(np.float32) / 255.0
        a[..., :3] *= a[..., 3:4]               # average premultiplied, so edges don't darken
        subs.append(a)
    acc = sum(subs) / len(subs)
    rgb = np.where(acc[..., 3:4] > 1e-6, acc[..., :3] / np.maximum(acc[..., 3:4], 1e-6), 0.0)
    return np.clip(np.concatenate([rgb, acc[..., 3:4]], -1) * 255.0 + 0.5, 0, 255).astype(np.uint8)


def render_rgba(draw: Callable[[Canvas, float], None], n_frames: int, out_dir: str, *, w=1920, h=1080,
                mb_samples=1, shutter=0.5, start: int = 0, workers: int | None = None, prefix="f_") -> dict:
    """Render transparent frames to a PNG sequence (straight alpha) for compositing deliverables.

    Convert with animkit.deliver: webm_alpha(), prores4444(), apng(), gif(). draw() must leave
    the background unpainted (no cv.clear / full-frame rect) where it should be transparent.
    """
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    _JOB.update(draw=draw, w=w, h=h, mb=mb_samples, shutter=shutter, post=None)
    workers = workers or auto_workers(w, h)
    t0 = time.time()
    frames = range(start, start + n_frames)
    for k, img in enumerate(_resilient(_frame_rgba, frames, workers, {"workers": workers})):
        Image.fromarray(img, "RGBA").save(os.path.join(out_dir, f"{prefix}{start + k:05d}.png"))
    return {"frames": n_frames, "seconds": round(time.time() - t0, 1), "dir": out_dir,
            "pattern": os.path.join(out_dir, f"{prefix}%05d.png"), "start": start}


def mux(video_path: str, audio_path: str, out_path: str, audio_bitrate="320k"):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video_path, "-i", audio_path,
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", audio_bitrate,
           "-shortest", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True)
    return out_path


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def concat(parts: list, out_path: str) -> str:
    """Join chunk renders (same codec/size/fps) without re-encoding.

    Use when a sandbox kills long tool calls: render(--frames a:b) per call, then concat.
    """
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        for p in parts:
            fh.write(f"file '{os.path.abspath(p)}'\n")
        lst = fh.name
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", out_path], check=True)
    os.unlink(lst)
    return out_path
