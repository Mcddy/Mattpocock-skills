"""Load SVG artwork (logos, icons, illustrations) as animatable vector shapes.

    art = SVGArt("logo.svg")                       # or SVGArt(svg_text)
    print(art.summary())                           # ids, groups, colours, warnings
    art.draw(cv, 960, 540, height=420, per_shape=lambda sh, i: {...})

Each Shape keeps its own VPath (in SVG user units, transforms applied), fill/stroke
colours, opacity, fill rule, id and ancestor group ids, so every element can move on
its own: transform about its centre (dx, dy, rot, sx, sy), alpha, stroke draw-on
(`draw_on` 0..1) and a fill reveal (`fill_alpha`).

Supported: path (all commands incl. arcs), rect (rx/ry), circle, ellipse, line,
polyline, polygon, g, use, nested transforms, inline style, <style> class rules,
fill-rule, opacity. Gradients become their average stop colour (flagged in
warnings). <text> is drawn with cv.text in the nearest font (flagged: outline text
in the source for exact logos). Filters, masks, patterns and images are skipped
(flagged).

Treat SVG files as untrusted input: only geometry and colours are read; nothing is
fetched or executed.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import numpy as np

from .vector import VPath, about, draw_fill, draw_stroke, mat, trs

_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_NAMED = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
    "yellow": "#ffff00", "orange": "#ffa500", "purple": "#800080", "gray": "#808080", "grey": "#808080",
    "silver": "#c0c0c0", "navy": "#000080", "teal": "#008080", "maroon": "#800000", "olive": "#808000",
    "lime": "#00ff00", "aqua": "#00ffff", "cyan": "#00ffff", "fuchsia": "#ff00ff", "magenta": "#ff00ff",
    "gold": "#ffd700", "pink": "#ffc0cb", "brown": "#a52a2a", "darkgray": "#a9a9a9", "lightgray": "#d3d3d3",
    "transparent": None, "none": None,
}


def _strip_ns(tag):
    return tag.split("}", 1)[-1]


def _num(s, default=0.0):
    if s is None:
        return default
    m = _NUM.search(str(s))
    if not m:
        return default
    v = float(m.group(0))
    unit = str(s)[m.end():].strip().lower()
    return v * {"pt": 4 / 3, "pc": 16, "mm": 3.7795, "cm": 37.795, "in": 96}.get(unit, 1.0)


def parse_colour(v, current="#000000"):
    """-> '#rrggbb' / None (none) / ('url', id)."""
    if v is None:
        return "inherit"
    v = v.strip()
    lv = v.lower()
    if lv in ("inherit", ""):
        return "inherit"
    if lv == "currentcolor":
        return current
    if lv.startswith("url("):
        return ("url", v[v.find("#") + 1:v.rfind(")")].strip())
    if lv in _NAMED:
        return _NAMED[lv]
    if lv.startswith("#"):
        h = lv[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        return "#" + h[:8]
    m = re.match(r"rgba?\(([^)]*)\)", lv)
    if m:
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",") if p.strip()]
        vals = [(_num(p) * 2.55 if p.endswith("%") else _num(p)) for p in parts[:3]]
        a = parts[3] if len(parts) > 3 else None
        hx = "#" + "".join(f"{int(max(0, min(255, round(x)))):02x}" for x in vals)
        if a is not None:
            af = _num(a) / 100 if a.endswith("%") else _num(a)
            hx += f"{int(max(0, min(1, af)) * 255):02x}"
        return hx
    return "#000000"


def parse_transform(s) -> np.ndarray:
    m = np.eye(3)
    if not s:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s):
        a = [float(x) for x in _NUM.findall(args)]
        if name == "matrix" and len(a) == 6:
            t = mat(*a)
        elif name == "translate":
            t = mat(e=a[0], f=a[1] if len(a) > 1 else 0.0)
        elif name == "scale":
            t = mat(a[0], 0, 0, a[1] if len(a) > 1 else a[0])
        elif name == "rotate":
            r = math.radians(a[0])
            t = mat(math.cos(r), math.sin(r), -math.sin(r), math.cos(r))
            if len(a) == 3:
                t = about(t, a[1], a[2])
        elif name == "skewX":
            t = mat(1, 0, math.tan(math.radians(a[0])), 1)
        elif name == "skewY":
            t = mat(1, math.tan(math.radians(a[0])), 0, 1)
        else:
            continue
        m = m @ t
    return m


def _arc_to_cubics(p0, rx, ry, phi, large, sweep, p1):
    """SVG elliptical arc (endpoint form) -> list of cubic control tuples."""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [("L", (x2, y2))]
    rx, ry = abs(rx), abs(ry)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p ** 2) / rx ** 2 + (y1p ** 2) / ry ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(u, v):
        a = math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])
        return a

    t1 = ang((1, 0), ((x1p - cxp) / rx, (y1p - cyp) / ry))
    dt = ang(((x1p - cxp) / rx, (y1p - cyp) / ry), ((-x1p - cxp) / rx, (-y1p - cyp) / ry))
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(1, int(math.ceil(abs(dt) / (math.pi / 2) - 1e-9)))
    d = dt / n
    k = 4 / 3 * math.tan(d / 4)
    out = []
    for i in range(n):
        a1, a2 = t1 + i * d, t1 + (i + 1) * d
        e1 = np.array([math.cos(a1), math.sin(a1)])
        e2 = np.array([math.cos(a2), math.sin(a2)])
        q1 = e1 + k * np.array([-e1[1], e1[0]])
        q2 = e2 - k * np.array([-e2[1], e2[0]])

        def tf(q):
            x, y = q[0] * rx, q[1] * ry
            return (cp * x - sp * y + cx, sp * x + cp * y + cy)

        out.append(("C", tf(q1), tf(q2), tf(e2)))
    return out


def parse_path_d(d: str) -> VPath:
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d or "")
    vp = VPath()
    i, cmd = 0, None
    cur = np.zeros(2)
    start = np.zeros(2)
    last_c = None      # last cubic control (for S)
    last_q = None      # last quad control (for T)

    def nums(k):
        nonlocal i
        vals = [float(t) for t in toks[i:i + k]]
        i += k
        return vals

    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                vp.close()
                cur = start.copy()
                last_c = last_q = None
                continue
        if cmd is None:
            break
        rel = cmd.islower()
        C = cmd.upper()
        base = cur if rel else np.zeros(2)
        try:
            if C == "M":
                x, y = nums(2)
                cur = base + (x, y)
                start = cur.copy()
                vp.moveTo(*cur)
                cmd = "l" if rel else "L"            # implicit lineto after moveto
                last_c = last_q = None
            elif C == "L":
                x, y = nums(2)
                cur = base + (x, y)
                vp.lineTo(*cur)
                last_c = last_q = None
            elif C == "H":
                (x,) = nums(1)
                cur = np.array([cur[0] + x if rel else x, cur[1]])
                vp.lineTo(*cur)
                last_c = last_q = None
            elif C == "V":
                (y,) = nums(1)
                cur = np.array([cur[0], cur[1] + y if rel else y])
                vp.lineTo(*cur)
                last_c = last_q = None
            elif C == "C":
                a = nums(6)
                c1, c2, p = base + a[0:2], base + a[2:4], base + a[4:6]
                vp.cubicTo(*c1, *c2, *p)
                cur, last_c, last_q = p, c2, None
            elif C == "S":
                a = nums(4)
                c1 = 2 * cur - last_c if last_c is not None else cur.copy()
                c2, p = base + a[0:2], base + a[2:4]
                vp.cubicTo(*c1, *c2, *p)
                cur, last_c, last_q = p, c2, None
            elif C == "Q":
                a = nums(4)
                c, p = base + a[0:2], base + a[2:4]
                vp.quadTo(*c, *p)
                cur, last_q, last_c = p, c, None
            elif C == "T":
                a = nums(2)
                c = 2 * cur - last_q if last_q is not None else cur.copy()
                p = base + a[0:2]
                vp.quadTo(*c, *p)
                cur, last_q, last_c = p, c, None
            elif C == "A":
                rx, ry, rot, large, sweep, x, y = nums(7)
                p = base + (x, y)
                for sg in _arc_to_cubics(tuple(cur), rx, ry, math.radians(rot), int(large), int(sweep), tuple(p)):
                    if sg[0] == "L":
                        vp.lineTo(*sg[1])
                    else:
                        vp.cubicTo(*sg[1], *sg[2], *sg[3])
                cur, last_c, last_q = p, None, None
            else:
                i += 1
        except ValueError:
            break
    return vp


def _ellipse_vp(cx, cy, rx, ry) -> VPath:
    k = 0.5522847498
    vp = VPath().moveTo(cx + rx, cy)
    vp.cubicTo(cx + rx, cy + k * ry, cx + k * rx, cy + ry, cx, cy + ry)
    vp.cubicTo(cx - k * rx, cy + ry, cx - rx, cy + k * ry, cx - rx, cy)
    vp.cubicTo(cx - rx, cy - k * ry, cx - k * rx, cy - ry, cx, cy - ry)
    vp.cubicTo(cx + k * rx, cy - ry, cx + rx, cy - k * ry, cx + rx, cy)
    return vp.close()


def _rect_vp(x, y, w, h, rx=0.0, ry=0.0) -> VPath:
    rx, ry = min(rx, w / 2), min(ry, h / 2)
    if rx <= 0 or ry <= 0:
        return VPath().moveTo(x, y).lineTo(x + w, y).lineTo(x + w, y + h).lineTo(x, y + h).close()
    k = 0.5522847498
    vp = VPath().moveTo(x + rx, y).lineTo(x + w - rx, y)
    vp.cubicTo(x + w - rx + k * rx, y, x + w, y + ry - k * ry, x + w, y + ry).lineTo(x + w, y + h - ry)
    vp.cubicTo(x + w, y + h - ry + k * ry, x + w - rx + k * rx, y + h, x + w - rx, y + h).lineTo(x + rx, y + h)
    vp.cubicTo(x + rx - k * rx, y + h, x, y + h - ry + k * ry, x, y + h - ry).lineTo(x, y + ry)
    vp.cubicTo(x, y + ry - k * ry, x + rx - k * rx, y, x + rx, y)
    return vp.close()


@dataclass
class Shape:
    id: str
    tag: str
    path: VPath
    fill: object = "#000000"
    stroke: object = None
    sw: float = 1.0
    opacity: float = 1.0
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    rule: str = "nonzero"
    groups: list = field(default_factory=list)
    text: dict | None = None          # for <text>: {"s", "x", "y", "size", "family", "weight", "anchor"}

    def centre(self):
        return self.path.centre() if self.path.subs else (self.text["x"], self.text["y"])

    def bounds(self):
        return self.path.bounds() if self.path.subs else (self.text["x"], self.text["y"] - self.text["size"], 1, 1)


class SVGArt:
    def __init__(self, src: str):
        txt = open(src, encoding="utf-8", errors="replace").read() if not src.lstrip().startswith("<") else src
        if "<!ENTITY" in txt:
            raise ValueError("SVG declares XML entities; refusing to parse (untrusted input).")
        self.root = ET.fromstring(txt)
        self.shapes: list[Shape] = []
        self.warnings: list[str] = []
        self.ids = {}
        for el in self.root.iter():
            if el.get("id"):
                self.ids[el.get("id")] = el
        self.classes = self._css(self.root)
        self.gradients = self._gradients()
        vb = self.root.get("viewBox")
        if vb:
            self.viewbox = tuple(float(v) for v in _NUM.findall(vb)[:4])
        else:
            self.viewbox = (0.0, 0.0, _num(self.root.get("width"), 100), _num(self.root.get("height"), 100))
        self._walk(self.root, np.eye(3), {"fill": "#000000", "stroke": None, "stroke-width": "1", "opacity": "1",
                                          "fill-opacity": "1", "stroke-opacity": "1", "fill-rule": "nonzero",
                                          "color": "#000000"}, [], 1.0)

    # -- parsing helpers
    def _css(self, root):
        rules = {}
        for el in root.iter():
            if _strip_ns(el.tag) == "style" and el.text:
                css = re.sub(r"/\*.*?\*/", "", el.text, flags=re.S)
                for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
                    decl = dict((k.strip(), v.strip()) for k, v in
                                (d.split(":", 1) for d in body.split(";") if ":" in d))
                    for s in sel.split(","):
                        s = s.strip()
                        if s.startswith("."):
                            rules.setdefault(s[1:], {}).update(decl)
        return rules

    def _gradients(self):
        g = {}
        for el in self.root.iter():
            if _strip_ns(el.tag) in ("linearGradient", "radialGradient") and el.get("id"):
                stops = [s for s in el.iter() if _strip_ns(s.tag) == "stop"]
                href = el.get("{http://www.w3.org/1999/xlink}href") or el.get("href")
                if not stops and href and href.lstrip("#") in self.ids:
                    stops = [s for s in self.ids[href.lstrip("#")].iter() if _strip_ns(s.tag) == "stop"]
                cols = []
                for s in stops:
                    st = dict((k.strip(), v.strip()) for k, v in (d.split(":", 1) for d in (s.get("style") or "").split(";")
                                                                  if ":" in d))
                    c = parse_colour(st.get("stop-color", s.get("stop-color", "#000000")))
                    if isinstance(c, str) and c.startswith("#"):
                        cols.append(np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], float))
                if cols:
                    avg = np.mean(cols, 0)
                    g[el.get("id")] = "#" + "".join(f"{int(v):02x}" for v in avg)
        return g

    def _style(self, el, inherited):
        st = dict(inherited)
        for k in ("fill", "stroke", "stroke-width", "opacity", "fill-opacity", "stroke-opacity", "fill-rule", "color",
                  "font-size", "font-family", "font-weight", "text-anchor", "display", "visibility"):
            if el.get(k) is not None:
                st[k] = el.get(k)
        for cls in (el.get("class") or "").split():
            st.update(self.classes.get(cls, {}))
        if el.get("style"):
            for d in el.get("style").split(";"):
                if ":" in d:
                    k, v = d.split(":", 1)
                    st[k.strip()] = v.strip()
        st["opacity"] = "1"   # opacity does not inherit; group opacity is multiplied separately
        return st

    def _paint(self, v, st):
        c = parse_colour(v, st.get("color", "#000000"))
        if isinstance(c, tuple):
            gid = c[1]
            if gid in self.gradients:
                self.warnings.append(f"gradient #{gid} drawn as its average colour {self.gradients[gid]}")
                return self.gradients[gid]
            self.warnings.append(f"paint url(#{gid}) not resolved; drawn black")
            return "#000000"
        return c

    def _walk(self, el, m, inherited, groups, op):
        tag = _strip_ns(el.tag)
        if tag in ("defs", "clipPath", "mask", "symbol", "style", "title", "desc", "metadata", "linearGradient",
                   "radialGradient", "pattern", "filter", "marker"):
            if tag in ("mask", "filter", "pattern"):
                self.warnings.append(f"<{tag}> skipped")
            return
        raw = {k: el.get(k) for k in ("opacity",)}
        st = self._style(el, inherited)
        if st.get("display") == "none" or st.get("visibility") == "hidden":
            return
        own_op = _num(raw["opacity"], 1.0) if raw["opacity"] is not None else 1.0
        sty = el.get("style") or ""
        mo = re.search(r"(?:^|;)\s*opacity\s*:\s*([^;]+)", sty)
        if mo:
            own_op = _num(mo.group(1), 1.0)
        m = m @ parse_transform(el.get("transform"))
        if tag in ("svg", "g", "a", "switch") or tag == "svg":
            gid = el.get("id")
            ng = groups + [gid] if gid and el is not self.root else groups
            for ch in el:
                self._walk(ch, m, st, ng, op * own_op)
            return
        if tag == "use":
            href = (el.get("{http://www.w3.org/1999/xlink}href") or el.get("href") or "").lstrip("#")
            tgt = self.ids.get(href)
            if tgt is not None:
                mm = m @ mat(e=_num(el.get("x")), f=_num(el.get("y")))
                self._walk(tgt, mm, st, groups, op * own_op)
            return
        vp = None
        text = None
        if tag == "path":
            vp = parse_path_d(el.get("d", ""))
        elif tag == "rect":
            rx, ry = el.get("rx"), el.get("ry")
            rxv = _num(rx if rx is not None else ry, 0.0)
            ryv = _num(ry if ry is not None else rx, 0.0)
            vp = _rect_vp(_num(el.get("x")), _num(el.get("y")), _num(el.get("width")), _num(el.get("height")), rxv, ryv)
        elif tag == "circle":
            r = _num(el.get("r"))
            vp = _ellipse_vp(_num(el.get("cx")), _num(el.get("cy")), r, r)
        elif tag == "ellipse":
            vp = _ellipse_vp(_num(el.get("cx")), _num(el.get("cy")), _num(el.get("rx")), _num(el.get("ry")))
        elif tag == "line":
            vp = VPath().moveTo(_num(el.get("x1")), _num(el.get("y1"))).lineTo(_num(el.get("x2")), _num(el.get("y2")))
        elif tag in ("polyline", "polygon"):
            pts = [float(v) for v in _NUM.findall(el.get("points", ""))]
            pts = list(zip(pts[0::2], pts[1::2]))
            if len(pts) >= 2:
                vp = VPath().moveTo(*pts[0])
                for p in pts[1:]:
                    vp.lineTo(*p)
                if tag == "polygon":
                    vp.close()
        elif tag == "text":
            s = "".join(el.itertext()).strip()
            if s:
                p = m @ np.array([_num(el.get("x")), _num(el.get("y")), 1.0])
                scale = math.sqrt(abs(np.linalg.det(m[:2, :2]))) or 1.0
                text = {"s": s, "x": float(p[0]), "y": float(p[1]), "size": _num(st.get("font-size"), 16) * scale,
                        "family": (st.get("font-family") or "sans-serif").split(",")[0].strip("'\" "),
                        "weight": int(_num(st.get("font-weight"), 400)) if str(st.get("font-weight", "")).strip()[:1].isdigit()
                        else (700 if "bold" in str(st.get("font-weight", "")) else 400),
                        "anchor": {"middle": "center", "end": "right"}.get(st.get("text-anchor", "start"), "left")}
                self.warnings.append(f"<text> '{s[:24]}' drawn with an installed font; outline text in the source for an exact logo")
                vp = VPath()
        elif tag == "image":
            self.warnings.append("<image> skipped (draw raster parts with cv.image)")
            return
        else:
            return
        if vp is None:
            return
        if vp.subs:
            vp = vp.transform(m)
        sw = _num(st.get("stroke-width"), 1.0) * (math.sqrt(abs(np.linalg.det(m[:2, :2]))) or 1.0)
        fill = self._paint(st.get("fill"), st)
        stroke = self._paint(st.get("stroke"), st)
        self.shapes.append(Shape(
            id=el.get("id") or f"{tag}{len(self.shapes)}", tag=tag, path=vp,
            fill=None if fill in (None, "inherit") else fill, stroke=None if stroke in (None, "inherit") else stroke,
            sw=sw, opacity=op * own_op, fill_opacity=_num(st.get("fill-opacity"), 1.0),
            stroke_opacity=_num(st.get("stroke-opacity"), 1.0), rule=st.get("fill-rule", "nonzero") or "nonzero",
            groups=[g for g in groups if g], text=text))

    # -- queries
    def bounds(self):
        bs = [s.bounds() for s in self.shapes if s.path.subs]
        if not bs:
            x, y, w, h = self.viewbox
            return x, y, w, h
        x0 = min(b[0] for b in bs)
        y0 = min(b[1] for b in bs)
        x1 = max(b[0] + b[2] for b in bs)
        y1 = max(b[1] + b[3] for b in bs)
        return x0, y0, x1 - x0, y1 - y0

    def select(self, key: str):
        """Shapes whose id or any ancestor group id starts with `key`."""
        return [s for s in self.shapes if s.id.startswith(key) or any(g.startswith(key) for g in s.groups)]

    def summary(self) -> str:
        cols = sorted({str(s.fill) for s in self.shapes if s.fill} | {str(s.stroke) for s in self.shapes if s.stroke})
        groups = sorted({g for s in self.shapes for g in s.groups})
        lines = [f"{len(self.shapes)} shapes, viewBox {self.viewbox}, bounds {tuple(round(v, 1) for v in self.bounds())}",
                 f"groups: {groups}", f"colours: {cols}"]
        lines += [f"  {i:2d} {s.id:<18} {s.tag:<8} fill={s.fill} stroke={s.stroke} groups={s.groups}"
                  for i, s in enumerate(self.shapes[:60])]
        if self.warnings:
            lines.append("warnings: " + "; ".join(sorted(set(self.warnings))))
        return "\n".join(lines)

    # -- drawing
    def placement(self, x, y, height=None, width=None, anchor="center"):
        bx, by, bw, bh = self.bounds()
        s = (height / bh) if height else (width / bw) if width else 1.0
        ax = {"center": bx + bw / 2, "left": bx, "right": bx + bw}.get(anchor, bx + bw / 2)
        ay = by + bh / 2
        return mat(e=x, f=y) @ mat(s, 0, 0, s) @ mat(e=-ax, f=-ay), s

    def draw(self, cv, x, y, height=None, width=None, per_shape=None, anchor="center"):
        """Draw at (x, y). per_shape(shape, index) -> dict(dx, dy, rot, sx, sy, alpha, draw_on, fill_alpha,
        stroke, sw, fill) animates each element about its own centre (units: output pixels, radians)."""
        M, s = self.placement(x, y, height, width, anchor)
        for i, sh in enumerate(self.shapes):
            o = per_shape(sh, i) if per_shape else {}
            a = sh.opacity * o.get("alpha", 1.0)
            if a <= 0.001:
                continue
            cx, cy = sh.centre()
            pc = M @ np.array([cx, cy, 1.0])
            local = about(trs(o.get("dx", 0.0), o.get("dy", 0.0), o.get("rot", 0.0), o.get("sx", 1.0), o.get("sy")),
                          pc[0], pc[1]) @ M
            if sh.text:
                p = local @ np.array([sh.text["x"], sh.text["y"], 1.0])
                sc = math.sqrt(abs(np.linalg.det(local[:2, :2])))
                cv.text(sh.text["s"], float(p[0]), float(p[1]), size=sh.text["size"] * sc, family=sh.text["family"],
                        weight=sh.text["weight"], color=o.get("fill", sh.fill or "#000000"), align=sh.text["anchor"],
                        alpha=a * o.get("fill_alpha", 1.0))
                continue
            vp = sh.path.transform(local)
            fill = o.get("fill", sh.fill)
            fa = a * sh.fill_opacity * o.get("fill_alpha", 1.0)
            if fill and fa > 0.001:
                draw_fill(cv, vp, fill, rule=sh.rule, alpha=fa)
            don = o.get("draw_on")
            stroke = o.get("stroke", sh.stroke)
            sw = o.get("sw", sh.sw * s)
            if stroke and a * sh.stroke_opacity > 0.001:
                if don is None or don >= 1.0:
                    draw_stroke(cv, vp, stroke, sw, alpha=a * sh.stroke_opacity)
                elif don > 0:
                    draw_stroke(cv, vp, stroke, sw, 0.0, don, alpha=a * sh.stroke_opacity)
