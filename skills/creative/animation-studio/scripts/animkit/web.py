"""Export animkit motion to the web and apps: CSS keyframes and Lottie JSON.

The same Channels that drive a rendered shot can drive a website or an app, so timing
designed and reviewed in animkit ships unchanged:

    css = css_animation("cta-pop", {"y": Channel([...]), "scale": Channel([...]), "opacity": ...}, fps=60)
    doc = Lottie(512, 512, fps=60, frames=90)
    doc.layer_from_vpaths("mark", [(vp, "#1D2B36", None, 0)], anchor=(256, 256),
                          tracks={"scale": Channel([...]), "rot": Channel([...])}, trim=Channel([...]))
    doc.save("mark.json")                     # plays in lottie-web / lottie-ios / lottie-android

Eases: bezier eases export exactly (cubic-bezier / Lottie tangents); springs, bounces and
holds are sampled (CSS linear() / per-frame Lottie keys), so overshoot survives export.
CSS uses individual transform properties (translate/rotate/scale) and linear(): current
Chrome, Edge, Firefox and Safari support both; give an older-browser fallback when that matters.
UI motion rules (durations, reduced motion, what to animate) are in references/ui-motion.md.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping

import numpy as np

from . import easing as E
from .curves import Channel


# ---------------------------------------------------------------- shared
def _segments(ch: Channel):
    """[(t0, v0, t1, v1, bezier|None, ease)] covering the channel; holds become flat segments."""
    out = []
    ks = ch.keys
    for a, b in zip(ks, ks[1:]):
        start = a.frame + a.hold
        if a.hold > 0:
            out.append((a.frame, a.value, start, a.value, (0.0, 0.0, 1.0, 1.0), "linear"))
        if a.drift:
            out.append((start, None, b.frame, b.value, None, "sampled"))
        else:
            out.append((start, a.value, b.frame, b.value, E.bezier_of(a.ease), a.ease))
    return out


def _val(v):
    return float(v) if np.ndim(v) == 0 else [float(x) for x in np.ravel(v)]


# ---------------------------------------------------------------- CSS
def _css_value(prop, v):
    if prop == "translate":
        return f"{v[0]:.2f}px {v[1]:.2f}px"
    if prop == "rotate":
        return f"{math.degrees(v):.3f}deg"
    if prop == "scale":
        return f"{v[0]:.4f} {v[1]:.4f}" if isinstance(v, (list, tuple, np.ndarray)) else f"{v:.4f}"
    return f"{v:.4f}"


def _linear_fn(ease, n=18):
    f = E.get(ease)
    pts = ", ".join(f"{f(i / n):.4f}" for i in range(n + 1))
    return f"linear({pts})"


def css_animation(name: str, tracks: dict, fps=60.0, duration_frames=None, iterations="1", delay_s=0.0,
                  fill="both", *, stable_reduced_state=None) -> str:
    """tracks: x, y (px), rot (radians), scale or sx/sy, opacity -> CSS (@keyframes + .name rule).

    x/y merge into `translate`, sx/sy into `scale`. Each property gets its own @keyframes, so
    their timings stay independent (overlap and offset survive).
    Reduced motion uses the export end state by default. Pass "start", "end", or a
    mapping of channel values for a deliberate loop resting state or hidden exit.
    Values use the channel units; normal-motion keyframes are unchanged."""
    props = {}
    if "x" in tracks or "y" in tracks:
        props["translate"] = (tracks.get("x"), tracks.get("y"))
    if "rot" in tracks:
        props["rotate"] = tracks["rot"]
    if "scale" in tracks:
        props["scale"] = tracks["scale"]
    elif "sx" in tracks or "sy" in tracks:
        props["scale"] = (tracks.get("sx"), tracks.get("sy"))
    if "opacity" in tracks:
        props["opacity"] = tracks["opacity"]
    end = duration_frames or max(c.end for v in props.values() for c in (v if isinstance(v, tuple) else (v,)) if c)
    end = max(end, 1.0)
    blocks, anims = [], []
    for prop, tr in props.items():
        kname = f"{name}-{prop}"
        if isinstance(tr, tuple):              # two channels -> sample every frame (exact, simple)
            a, b = tr
            default = 0.0 if prop == "translate" else 1.0
            frames = sorted(set(np.r_[np.arange(0, end + 1e-6, 1.0), end]))
            lines = []
            for f in frames:
                v = (a(f) if a else default, b(f) if b else default)
                lines.append(f"  {100 * f / end:.3f}% {{ {prop}: {_css_value(prop, v)}; }}")
            blocks.append(f"@keyframes {kname} {{\n" + "\n".join(lines) + "\n}")
        else:
            lines = []
            segs = _segments(tr)
            if not segs:
                v = tr(0)
                lines.append(f"  0%, 100% {{ {prop}: {_css_value(prop, v)}; }}")
            for t0, v0, t1, v1, bez, ease in segs:
                if bez is not None:
                    tf = f"cubic-bezier({bez[0]}, {bez[1]}, {bez[2]}, {bez[3]})"
                    lines.append(f"  {100 * t0 / end:.3f}% {{ {prop}: {_css_value(prop, tr(t0))}; animation-timing-function: {tf}; }}")
                elif ease == "sampled":
                    for f in np.arange(t0, t1, 1.0):
                        lines.append(f"  {100 * f / end:.3f}% {{ {prop}: {_css_value(prop, tr(f))}; animation-timing-function: linear; }}")
                else:
                    lines.append(f"  {100 * t0 / end:.3f}% {{ {prop}: {_css_value(prop, tr(t0))}; "
                                 f"animation-timing-function: {_linear_fn(ease)}; }}")
            last = tr.keys[-1]
            lines.append(f"  {100 * last.frame / end:.3f}% {{ {prop}: {_css_value(prop, tr(last.frame))}; }}")
            if last.frame < end:
                lines.append(f"  100% {{ {prop}: {_css_value(prop, tr(last.frame))}; }}")
            if segs and segs[0][0] > 0:
                lines.insert(0, f"  0% {{ {prop}: {_css_value(prop, tr(0))}; }}")
            blocks.append(f"@keyframes {kname} {{\n" + "\n".join(lines) + "\n}")
        anims.append(f"{kname} {end / fps:.3f}s linear {delay_s:.3f}s {iterations} {fill}")
    if stable_reduced_state is None:
        at, overrides = end, {}
    elif isinstance(stable_reduced_state, str):
        if stable_reduced_state not in ("start", "end"):
            raise ValueError("stable_reduced_state must be start, end, or a channel mapping")
        at, overrides = (0 if stable_reduced_state == "start" else end), {}
    elif isinstance(stable_reduced_state, Mapping):
        at, overrides = end, dict(stable_reduced_state)
    else:
        raise ValueError("stable_reduced_state must be start, end, or a channel mapping")
    allowed = {"x", "y", "rot", "scale", "sx", "sy", "opacity"}
    if set(overrides) - allowed:
        raise ValueError("Unknown stable reduced-state channel")
    if "scale" in overrides and ("sx" in overrides or "sy" in overrides):
        raise ValueError("Use scale or sx/sy overrides, not both")
    state = {k: c(at) for k, c in tracks.items() if k in allowed and c is not None}
    # A legacy scale Channel may itself contain a two-axis tuple/array.
    if "scale" in state and not np.isscalar(state["scale"]):
        pair = np.asarray(state.pop("scale"))
        if pair.shape != (2,):
            raise ValueError("Derived scale requires one value or two axes")
        state["sx"], state["sy"] = pair
    if "scale" in overrides:
        state.pop("sx", None)
        state.pop("sy", None)
    elif "sx" in overrides or "sy" in overrides:
        scale = state.pop("scale", 1.0)
        state.setdefault("sx", scale)
        state.setdefault("sy", scale)
    state.update(overrides)
    for key, value in state.items():
        if isinstance(value, (str, bytes, bool)) or not np.isscalar(value):
            raise ValueError("Stable reduced-state values must be finite numbers")
        try:
            state[key] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Stable reduced-state values must be finite numbers") from exc
        if not math.isfinite(state[key]) or (key == "opacity" and not 0 <= state[key] <= 1):
            raise ValueError("Invalid stable reduced-state " + key)
    reduced = {}
    if "x" in state or "y" in state:
        reduced["translate"] = (state.get("x", 0), state.get("y", 0))
    if "rot" in state:
        reduced["rotate"] = state["rot"]
    if "scale" in state:
        reduced["scale"] = state["scale"]
    elif "sx" in state or "sy" in state:
        reduced["scale"] = (state.get("sx", 1), state.get("sy", 1))
    if "opacity" in state:
        reduced["opacity"] = state["opacity"]
    declarations = " ".join(f"{p}: {_css_value(p, v)};" for p, v in reduced.items())
    rule = (f".{name} {{\n  animation: {', '.join(anims)};\n}}\n"
            f"@media (prefers-reduced-motion: reduce) {{\n  .{name} {{ animation: none; {declarations} }}\n}}")
    return "\n".join(blocks) + "\n" + rule


# ---------------------------------------------------------------- Lottie
def _rgb01(col):
    from .canvas import rgba
    c = rgba(col)
    return [round(c.fR, 4), round(c.fG, 4), round(c.fB, 4), 1]


def _prop(ch: Channel | None, default, scale=1.0, wrap=False, offset=0.0, fps_end=None):
    """Lottie animatable property from a Channel (bezier eases exact, others baked per frame)."""
    def fmt(v):
        v = _val(v)
        if isinstance(v, list):
            return [x * scale + offset for x in v]
        return [v * scale + offset] if wrap else v * scale + offset
    if ch is None:
        return {"a": 0, "k": fmt(default)}
    if len(ch.keys) == 1:
        return {"a": 0, "k": fmt(ch.keys[0].value)}
    ks = []
    for t0, v0, t1, v1, bez, ease in _segments(ch):
        if bez is not None:
            x1, y1, x2, y2 = bez
            ks.append({"t": t0, "s": _as_list(fmt(ch(t0))), "o": {"x": [x1], "y": [y1]}, "i": {"x": [x2], "y": [y2]}})
        else:
            for f in np.arange(t0, t1, 1.0):
                ks.append({"t": float(f), "s": _as_list(fmt(ch(f))), "o": {"x": [0], "y": [0]}, "i": {"x": [1], "y": [1]}})
    ks.append({"t": ch.keys[-1].frame, "s": _as_list(fmt(ch.keys[-1].value))})
    return {"a": 1, "k": ks}


def _as_list(v):
    return v if isinstance(v, list) else [v]


def _shape_from_vpath(vp):
    """VPath -> list of Lottie 'sh' items (one per subpath), tangents relative to vertices."""
    items = []
    for s in vp.subs:
        verts = [np.asarray(s["start"], float)]
        ins = [np.zeros(2)]
        outs = [np.zeros(2)]
        cur = verts[0]
        for sg in s["segs"]:
            kind, *ps = sg
            if kind == "L":
                p = np.asarray(ps[0], float)
                c1, c2 = cur, p
            elif kind == "Q":
                q, p = (np.asarray(x, float) for x in ps)
                c1, c2 = cur + 2 / 3 * (q - cur), p + 2 / 3 * (q - p)
            else:
                c1, c2, p = (np.asarray(x, float) for x in ps)
            outs[-1] = c1 - cur
            verts.append(p)
            ins.append(c2 - p)
            outs.append(np.zeros(2))
            cur = p
        closed = bool(s["closed"])
        if closed and len(verts) > 1 and np.linalg.norm(verts[-1] - verts[0]) < 1e-6:
            ins[0] = ins[-1]
            verts, ins, outs = verts[:-1], ins[:-1], outs[:-1]
        items.append({"ty": "sh", "ks": {"a": 0, "k": {"c": closed, "v": [v.round(3).tolist() for v in verts],
                                                        "i": [v.round(3).tolist() for v in ins],
                                                        "o": [v.round(3).tolist() for v in outs]}}})
    return items


class Lottie:
    """Minimal Lottie (bodymovin 5.x) writer: shape layers with animated transform, opacity and trim."""

    def __init__(self, w, h, fps=60.0, frames=120, name="animkit"):
        self.doc = {"v": "5.7.4", "fr": fps, "ip": 0, "op": frames, "w": w, "h": h, "nm": name, "ddd": 0,
                    "assets": [], "layers": []}

    def null_layer(self, name, anchor=(0.0, 0.0), position=None, tracks=None):
        """Invisible parent (ty 3). Children passed parent=<returned ind> inherit its transform:
        e.g. a whole lock-up's moving hold (scale 1 -> 1.015 about the frame centre)."""
        tracks = tracks or {}
        ax, ay = anchor
        px, py = position if position is not None else anchor
        ks = {"o": {"a": 0, "k": 100}, "r": _prop(tracks.get("rot"), 0.0, 180.0 / math.pi),
              "p": self._pos(tracks.get("x"), tracks.get("y"), px, py), "a": {"a": 0, "k": [ax, ay, 0]},
              "s": _scale_prop(tracks.get("scale"))}
        ind = len(self.doc["layers"]) + 1
        self.doc["layers"].insert(0, {"ddd": 0, "ind": ind, "ty": 3, "nm": name, "sr": 1, "ks": ks, "ao": 0,
                                      "ip": 0, "op": self.doc["op"], "st": 0, "bm": 0})
        return ind

    def layer_from_vpaths(self, name, shapes, anchor=(0.0, 0.0), position=None, tracks=None, trim=None, start=0,
                          end=None, parent=None, mask=None, mask_inv=False):
        """shapes: [(VPath, fill|None, stroke|None, stroke_width[, 'nonzero'|'evenodd'])] in layer pixels.

        tracks (Channels, all optional): x, y (offset px), rot (radians), scale (1 = 100%), opacity (0..1).
        trim: Channel 0..1 for stroke draw-on (applies to strokes in the layer).
        mask: VPath (or list) in layer pixels; content shows only inside it (outside with mask_inv).
        With a mask, the tracks move the shapes *inside* the layer (group transform), so the mask stays
        put: a sun rising from behind a hill, letters rising from behind a baseline."""
        tracks = tracks or {}
        ax, ay = anchor
        px, py = position if position is not None else anchor
        in_group = mask is not None
        groups = []
        for item in shapes:
            vp, fill, stroke, sw = item[:4]
            rule = item[4] if len(item) > 4 else "nonzero"
            it = _shape_from_vpath(vp)
            if trim is not None:                       # trim modifies the paths above it in the stack
                it.append({"ty": "tm", "s": {"a": 0, "k": 0}, "e": _prop(trim, 1.0, 100.0, wrap=True),
                           "o": {"a": 0, "k": 0}, "m": 1})
            if fill:
                it.append({"ty": "fl", "c": {"a": 0, "k": _rgb01(fill)}, "o": {"a": 0, "k": 100},
                           "r": 2 if rule == "evenodd" else 1})
            if stroke and sw > 0:
                it.append({"ty": "st", "c": {"a": 0, "k": _rgb01(stroke)}, "o": {"a": 0, "k": 100},
                           "w": {"a": 0, "k": sw}, "lc": 2, "lj": 2})
            if in_group:
                it.append({"ty": "tr", "o": _prop(tracks.get("opacity"), 1.0, 100.0),
                           "r": _prop(tracks.get("rot"), 0.0, 180.0 / math.pi),
                           "p": self._pos(tracks.get("x"), tracks.get("y"), px, py),
                           "a": {"a": 0, "k": [ax, ay, 0]}, "s": _scale_prop(tracks.get("scale"))})
            else:
                it.append({"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]},
                           "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}})
            groups.append({"ty": "gr", "nm": name, "it": it})
        if in_group:
            ks = {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [0, 0, 0]},
                  "a": {"a": 0, "k": [0, 0, 0]}, "s": {"a": 0, "k": [100, 100, 100]}}
        else:
            ks = {"o": _prop(tracks.get("opacity"), 1.0, 100.0),
                  "r": _prop(tracks.get("rot"), 0.0, 180.0 / math.pi),
                  "p": self._pos(tracks.get("x"), tracks.get("y"), px, py),
                  "a": {"a": 0, "k": [ax, ay, 0]},
                  "s": _scale_prop(tracks.get("scale"))}
        layer = {"ddd": 0, "ind": len(self.doc["layers"]) + 1, "ty": 4, "nm": name, "sr": 1, "ks": ks, "ao": 0,
                 "shapes": groups, "ip": start, "op": end if end is not None else self.doc["op"], "st": 0, "bm": 0}
        if in_group:
            mvps = mask if isinstance(mask, (list, tuple)) else [mask]
            layer["hasMask"] = True
            layer["masksProperties"] = [{"inv": bool(mask_inv), "mode": "a", "nm": f"Mask {i + 1}",
                                         "pt": {"a": 0, "k": sh["ks"]["k"]}, "o": {"a": 0, "k": 100},
                                         "x": {"a": 0, "k": 0}}
                                        for i, mv in enumerate(mvps) for sh in _shape_from_vpath(mv)]
        if parent:
            layer["parent"] = parent
        self.doc["layers"].insert(0, layer)       # later layers draw on top
        return layer["ind"]

    def _pos(self, cx, cy, px, py):
        if cx is None and cy is None:
            return {"a": 0, "k": [px, py, 0]}
        frames = sorted({k.frame for c in (cx, cy) if c for k in c.keys})
        same = cx and cy and [k.frame for k in cx.keys] == [k.frame for k in cy.keys] and \
            [E.bezier_of(k.ease) for k in cx.keys] == [E.bezier_of(k.ease) for k in cy.keys]
        if same and all(E.bezier_of(k.ease) for k in cx.keys[:-1]) and not any(k.hold or k.drift for k in cx.keys):
            ks = []
            for a, b in zip(cx.keys, cx.keys[1:]):
                x1, y1, x2, y2 = E.bezier_of(a.ease)
                ks.append({"t": a.frame, "s": [px + cx(a.frame), py + cy(a.frame), 0],
                           "o": {"x": [x1], "y": [y1]}, "i": {"x": [x2], "y": [y2]}})
            ks.append({"t": cx.keys[-1].frame, "s": [px + cx(cx.keys[-1].frame), py + cy(cx.keys[-1].frame), 0]})
            return {"a": 1, "k": ks}
        lo, hi = frames[0], frames[-1]
        ks = [{"t": float(f), "s": [px + (cx(f) if cx else 0), py + (cy(f) if cy else 0), 0],
               "o": {"x": [0], "y": [0]}, "i": {"x": [1], "y": [1]}} for f in np.arange(lo, hi, 1.0)]
        ks.append({"t": hi, "s": [px + (cx(hi) if cx else 0), py + (cy(hi) if cy else 0), 0]})
        return {"a": 1, "k": ks}

    def json(self) -> str:
        return json.dumps(self.doc, separators=(",", ":"))

    def save(self, path):
        with open(path, "w") as fh:
            fh.write(self.json())
        return path


def _scale_prop(ch):
    if ch is None:
        return {"a": 0, "k": [100, 100, 100]}
    p = _prop(ch, 1.0, 100.0, wrap=True)
    if p["a"] == 0:
        v = p["k"][0] if isinstance(p["k"], list) else p["k"]
        return {"a": 0, "k": [v, v, 100]}
    for k in p["k"]:
        v = k["s"][0]
        k["s"] = [v, v, 100]
    return p


def lottie_from_svg(art, w, h, fps, frames, x, y, height=None, per_shape=None):
    """SVGArt -> Lottie with one layer per shape (anchored at its own centre).

    per_shape(shape, index) -> dict of Channels: x, y, rot, scale, opacity, trim (any subset)."""
    doc = Lottie(w, h, fps, frames)
    M, s = art.placement(x, y, height)
    for i, sh in enumerate(art.shapes):
        if sh.text or not sh.path.subs:
            continue
        vp = sh.path.transform(M)
        cx, cy = vp.centre()
        tr = per_shape(sh, i) if per_shape else {}
        shapes = [(vp, sh.fill, sh.stroke, sh.sw * s, sh.rule)]
        doc.layer_from_vpaths(sh.id, shapes, anchor=(cx, cy), position=(cx, cy),
                              tracks={k: v for k, v in tr.items() if k != "trim"}, trim=tr.get("trim"))
    return doc
