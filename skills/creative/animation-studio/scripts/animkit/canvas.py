"""animkit.canvas - one drawing API, two backends.

* skia  (preferred): skia-python, GPU-grade anti-aliasing, fast, exact blend modes.
* soft  (fallback):  numpy + Pillow only. For offline sandboxes where pip can't reach
                     PyPI (e.g. ChatGPT's code environment). Same API, same look within
                     a few percent; slower (roughly 1-4 s per 1080p frame).

Select with ANIMKIT_BACKEND=skia|soft|auto (default auto: skia if importable).
`BACKEND` tells you which one is active; report it in delivery notes.

Colours: '#rrggbb', '#rrggbbaa', (r, g, b) or (r, g, b, a) with 0-255 ints or
0-1 floats, or a gradient from Canvas.linear()/radial().
"""
from __future__ import annotations

import os

_want = os.environ.get("ANIMKIT_BACKEND", "auto").lower()
BACKEND = None
if _want in ("auto", "skia"):
    try:
        from .canvas_skia import Canvas, rgba, mix, typeface, BLEND, new_path  # noqa: F401
        BACKEND = "skia"
    except ImportError:
        if _want == "skia":
            raise
if BACKEND is None:
    from .canvas_soft import Canvas, rgba, mix, typeface, BLEND, new_path  # noqa: F401
    BACKEND = "soft"

from .finish import accumulate, dither, grain, vignette  # noqa: E402,F401
