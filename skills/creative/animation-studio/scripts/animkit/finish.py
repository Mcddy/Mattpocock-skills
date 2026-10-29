"""Backend-independent finishing passes on RGB uint8 frames (numpy only)."""
from __future__ import annotations

import numpy as np


def accumulate(frames: list) -> np.ndarray:
    """Average sub-frame renders in (approximately) linear light for motion blur."""
    acc = None
    for fr in frames:
        lin = (fr.astype(np.float32) / 255.0) ** 2.2
        acc = lin if acc is None else acc + lin
    acc /= len(frames)
    return np.clip(acc ** (1 / 2.2) * 255.0 + 0.5, 0, 255).astype(np.uint8)


_VIG: dict = {}


def vignette(img: np.ndarray, strength=0.18) -> np.ndarray:
    h, w = img.shape[:2]
    key = (h, w, strength)
    if key not in _VIG:
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _VIG[key] = (1 - strength * np.clip(d - 0.35, 0, 1) ** 1.6).astype(np.float32)[..., None]
    return np.clip(img.astype(np.float32) * _VIG[key], 0, 255).astype(np.uint8)


_GRAIN: dict = {}


_DITHER: dict = {}


def dither(img: np.ndarray, amount=1.5, seed=3) -> np.ndarray:
    """Static screen-space dither (~1.5 levels): breaks gradient banding in vignettes, skies and soft
    light, and survives H.264 at normal bitrates because it is the same every frame (measured: flat
    gradient steps 43-54% -> 0% at ~2 Mbps). Use this for banding; use grain() only for a film look."""
    h, w = img.shape[:2]
    key = (h, w, amount, seed)
    if key not in _DITHER:
        _DITHER[key] = np.random.default_rng(seed).normal(0, amount, (h, w)).astype(np.float32)[..., None]
    return np.clip(np.rint(img.astype(np.float32) + _DITHER[key]), 0, 255).astype(np.uint8)


def grain(img: np.ndarray, frame: int, amount=3.0, seed=7, cycle=12) -> np.ndarray:
    """Moving film grain (a style choice, not a banding fix). Keep subtle.

    Encoder cost: x264 -tune animation smooths fine moving grain away (the banding returns); keeping it
    needs -tune grain and 15-50 Mbps at 1080p. For banding alone use dither().
    A cycle of pre-generated fields keeps it cheap; 12 fields at 24 fps never reads as a loop.
    """
    h, w = img.shape[:2]
    key = (h, w, amount, seed, cycle)
    if key not in _GRAIN:
        rng = np.random.default_rng(seed)
        _GRAIN[key] = [rng.normal(0, amount, (h, w)).astype(np.int16) for _ in range(cycle)]
    n = _GRAIN[key][int(frame) % cycle]
    return np.clip(img.astype(np.int16) + n[..., None], 0, 255).astype(np.uint8)
