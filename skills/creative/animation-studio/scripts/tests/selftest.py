#!/usr/bin/env python3
"""Verify the animation-studio toolkit in this environment.

python3 scripts/tests/selftest.py [--render]   (--render also renders + QA's the bouncing ball)
Exit code 0 = all checks passed.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def main():
    import numpy as np
    from animkit import easing as E
    from animkit.curves import Channel, K, ArcPath
    from animkit.principles import anticipate, two_bone_ik, Spring, impact_squash, squash_stretch
    from animkit.walk import Walk

    check("ffmpeg present", shutil.which("ffmpeg") is not None)
    for n in E.names():
        e = E.get(n)
        if n == "hold":
            continue
        check(f"ease {n} endpoints", abs(e(0.0)) < 1e-6 and abs(e(1.0) - 1) < 1e-6, f"{e(0):.3f}->{e(1):.3f}")
    bz = E.cubic_bezier(0.45, 0, 0.55, 1)
    check("bezier monotonic", all(bz(i / 100) <= bz((i + 1) / 100) + 1e-9 for i in range(100)))
    ch = Channel([K(0, 0.0), K(10, 100.0, "slow_in_out", hold=0), K(20, 100.0)])
    check("channel interp", abs(ch(5) - 50) < 1e-6 and ch(15) == 100.0)
    check("channel stepped", ch.stepped(9.9) == 0.0)
    ant = anticipate(0, 0.0, 100.0)
    vals = [ant(f) for f in range(0, 30)]
    check("anticipation dips then overshoots", min(vals) < 0 and max(vals) > 100 and abs(vals[-1] - 100) < 0.5)
    j, e = two_bone_ik((0, 0), (20, 60), 40, 40, 1)
    check("IK preserves bone lengths", abs(np.linalg.norm(j) - 40) < 1e-6 and abs(np.linalg.norm(np.array(e) - j) - 40) < 1e-6)
    s = Spring(0.0, 160, 0.3)
    xs = [float(s.step(1.0)) for _ in range(96)]
    check("spring overshoots and settles", max(xs) > 1.0 and abs(xs[-1] - 1.0) < 0.02)
    sx, sy = impact_squash(1.0)
    check("squash preserves volume", abs(sx * sy - 1) < 1e-9)
    a, b = squash_stretch(20)
    check("stretch preserves volume", abs(a * b - 1) < 1e-9)
    w = Walk(0, 800, 880, stride=80, step_frames=10)
    check("walk feet locked", w.foot_slide_report() == 0.0, f"slide {w.foot_slide_report()} px")
    check("walk has contacts", len(w.contacts) >= 8, f"{len(w.contacts)} contacts")
    brisk = Walk(0, 600, 400, stride=92, step_frames=6)
    mt = max(abs(brisk.pose(f_)["tilt"]) for f_ in np.arange(-2, brisk.t_stop + 4, 0.5))
    check("walk lean stays bounded on brisk starts/stops", mt < 0.35, f"max tilt {mt:.2f} rad")
    w2 = Walk(800, 1200, 880, stride=80, step_frames=10, start=w.end_frame + 10, start_feet=w.final_feet())
    check("chained walk continuous", abs(w2.pose(w2.start - 1)["feet"]["near"][0][0] - w.final_feet()[0]) < 1e-6)
    arc = ArcPath([(0, (0, 0)), (10, (100, 0))], bend=[40])
    check("arc bows upward", arc(5)[1] < -10)

    from animkit import canvas as CV
    from animkit.canvas import Canvas, accumulate
    print(f"INFO canvas backend: {CV.BACKEND}")
    cv = Canvas(64, 32, "#000000")
    cv.light(32, 16, 30, "#FFFFFF", 1.0)
    arr = cv.array()
    check(f"canvas ({CV.BACKEND}) + additive light", arr.shape == (32, 64, 3) and arr[16, 32].mean() > 100)
    check("motion-blur accumulate", accumulate([arr, arr]).shape == arr.shape)
    # the software backend must work everywhere and match Skia when both exist
    import animkit.canvas_soft as SOFT
    def scene(c):
        c.clear("#202830")
        c.rect(10, 10, 100, 60, c.linear((0, 0), (0, 80), ["#E2A63A", "#7A3A2C"]), r=8)
        with c.at(150, 60, 0.3, 1.2, 0.8):
            c.ellipse(0, 0, 40, 25, "#BFE0EE", alpha=0.8)
        with c.layer(bounds=(180, 10, 120, 100)):
            c.circle(240, 60, 40, "#F2B24C")
            c.rect(180, 10, 120, 100, "#FFD38A", alpha=0.5, blend="src_atop")
        c.light(80, 90, 60, "#FFD38A", 0.6)
        c.line((10, 110), (300, 100), "#A8C0D8", 3)
        c.shadow(240, 112, 40, 6)
    s = SOFT.Canvas(320, 120)
    scene(s)
    sa = s.array()
    check("soft backend renders", sa.shape == (120, 320, 3) and sa.std() > 5)
    if CV.BACKEND == "skia":
        k = CV.Canvas(320, 120)
        scene(k)
        diff = float(np.abs(k.array().astype(int) - sa.astype(int)).mean())
        check("soft backend matches skia (mean diff < 2/255)", diff < 2.0, f"{diff:.2f}")

    # reusable parts: shapes, kinetic type, character rig
    from animkit.shapes import circle as _circ, star as _star, morph
    m0, m1 = morph(_circ(0, 0, 50), _star(0, 0, 60, 25), 0.0), morph(_circ(0, 0, 50), _star(0, 0, 60, 25), 1.0)
    check("morph endpoints", abs(np.hypot(*m0.T).mean() - 50) < 1.0 and np.hypot(*m1.T).max() <= 60.5)
    from animkit.typeanim import KineticText, stagger_in
    tc = Canvas(400, 120, "#000000")
    kt = KineticText("Hi", size=64, family="DejaVu Sans", weight=700)
    wdt = kt.draw(tc, 200, 90, 30, stagger_in(start=0, per=2, dur=10), color="#FFFFFF", align="center")
    check("kinetic text draws", wdt > 20 and tc.array().max() > 200, f"width {wdt:.0f}")
    from animkit.rigs import BlobRig, Light, Performer
    wk = Walk(0, 300, 400, stride=80, step_frames=10)
    pf = Performer(BlobRig(), [wk], range(0, 60))
    rc = Canvas(600, 480, "#20262E")
    out = BlobRig().draw(rc, pf.pose(30), Light(ambient=(0.8, 0.8, 0.9), key=0.3), ground=400)
    check("blob rig draws a posed character", rc.array().std() > 10 and "hand" in out)
    import warnings as _w
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        Channel([K(0, 0.0), K(120, 1.0), K(100, 0.0)])
    check("out-of-order keys raise a warning", any("out of chronological order" in str(c.message) for c in caught))

    # ---- v3: fill rules, images, alpha, erase
    from animkit.canvas import new_path
    hc = Canvas(200, 200, "#000000")
    p_ = new_path()
    for r_, sgn in ((80, 1), (40, -1)):
        for i in range(65):
            a_ = sgn * 2 * math.pi * i / 64
            (p_.moveTo if i == 0 else p_.lineTo)(100 + r_ * math.cos(a_), 100 + r_ * math.sin(a_))
        p_.close()
    hc.path(p_, "#FFFFFF", rule="nonzero")
    ha = hc.array()
    check("fill rule leaves a hole (logo counters)", ha[100, 100].max() < 20 and ha[100, 35].min() > 230)
    img = np.zeros((10, 10, 4), np.uint8)
    img[..., 1] = 255
    img[..., 3] = 255
    ic = Canvas(40, 40)
    ic.image(img, 10, 10, 20, 20)
    rg = ic.rgba_array()
    check("image draws + transparent RGBA output", rg[20, 20, 1] > 240 and rg[20, 20, 3] > 240 and rg[2, 2, 3] == 0)
    ec = Canvas(40, 40)
    with ec.layer(bounds=(0, 0, 40, 40)):
        ec.rect(0, 0, 40, 40, "#FF0000")
        ec.circle(20, 20, 8, "#000000", blend="dst_out")
    check("dst_out erases inside a layer", ec.rgba_array()[20, 20, 3] < 10 and ec.rgba_array()[2, 2, 3] > 240)

    # ---- v3: vectors, SVG artwork, Lottie/CSS export
    from animkit.vector import VPath, draw_stroke
    vp = VPath().moveTo(0, 0).lineTo(100, 0).lineTo(100, 100)
    half = vp.trim(0, 0.5)
    check("vector trim (draw-on) by arc length", abs(sum(np.linalg.norm(np.diff(h_, axis=0), axis=1).sum() for h_ in half) - 100) < 1.0)
    from animkit.svg import SVGArt
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><style>.a{fill:#123456}</style>'
           '<g id="mark" transform="translate(50 50)"><path class="a" fill-rule="evenodd" d="M-40 0A40 40 0 1 0 40 0A40 40 0 1 0 -40 0Z'
           'M-20 0A20 20 0 1 1 20 0A20 20 0 1 1 -20 0Z"/><rect x="-5" y="30" width="10" height="5" rx="2" fill="red"/></g></svg>')
    art = SVGArt(svg)
    sc_ = Canvas(200, 200, "#FFFFFF")
    art.draw(sc_, 100, 100, height=160)
    sa_ = sc_.array()
    check("SVG: arcs, classes, evenodd hole, groups", len(art.shapes) == 2 and art.shapes[0].fill == "#123456"
          and sa_[100, 100].min() > 230 and sa_[100, 40].max() < 120 and art.shapes[0].groups == ["mark"])
    from animkit.web import css_animation, Lottie
    from animkit.easing import bezier_of
    css = css_animation("t", {"rot": Channel([K(0, 0.3, "slow_in_out"), K(12, 0.0)]), "opacity": Channel([K(0, 0.0, "settle"), K(10, 1.0)])})
    check("CSS export: keyframes, exact bezier, spring as linear(), reduced motion",
          "@keyframes t-rotate" in css and "cubic-bezier(0.45, 0.0, 0.55, 1.0)" in css and "linear(" in css
          and "prefers-reduced-motion" in css)
    lt = Lottie(100, 100, 24, 24)
    lt.layer_from_vpaths("m", [(art.shapes[0].path, "#123456", "#000000", 2, "evenodd")], anchor=(50, 50),
                         tracks={"scale": Channel([K(0, 0.0, "snap"), K(10, 1.0)])}, trim=Channel([K(0, 0.0), K(12, 1.0)]))
    grp = lt.doc["layers"][0]["shapes"][0]["it"]
    kinds = [g["ty"] for g in grp]
    check("Lottie export: shape group with trim inside, animated scale", kinds.index("tm") > kinds.index("sh")
          and lt.doc["layers"][0]["ks"]["s"]["a"] == 1 and bezier_of("snap") == (0.2, 0.0, 0.0, 1.0))

    from animkit.vector import mask_to, circle_vp
    mc = Canvas(60, 60)
    with mc.layer(bounds=(0, 0, 60, 60)):
        mc.rect(0, 0, 60, 60, "#FF8800")
        mask_to(mc, circle_vp(30, 30, 15), (0, 0, 60, 60))
    ma = mc.rgba_array()
    check("mask_to keeps only the inside of the shape", ma[30, 30, 3] > 240 and ma[3, 3, 3] < 10 and ma[30, 52, 3] < 10)
    lm = Lottie(100, 100, 24, 24)
    par = lm.null_layer("hold", anchor=(50, 50), tracks={"scale": Channel([K(0, 1.0, "in_out_sine"), K(24, 1.02)])})
    lm.layer_from_vpaths("sun", [(circle_vp(50, 60, 10), "#E9A23B", None, 0)], anchor=(50, 60), position=(50, 60),
                         tracks={"y": Channel([K(0, 30.0, "slow_in_out"), K(12, 0.0)])}, mask=circle_vp(50, 50, 20),
                         parent=par)
    sl = lm.doc["layers"][0]
    check("Lottie mask: static layer mask, motion inside the group, null parent",
          sl.get("hasMask") and sl["masksProperties"][0]["mode"] == "a" and sl["ks"]["p"]["a"] == 0
          and sl["shapes"][0]["it"][-1]["p"]["a"] == 1 and sl["parent"] == par and lm.doc["layers"][1]["ty"] == 3)
    fs_ = Canvas(60, 60, "#FFFFFF")
    fs_.circle(30, 30, 20, "#FF0000", stroke="#000000", sw=4)
    fa_ = fs_.array()
    check("fill + stroke in one call draws both (fill was silently dropped before v3.0.3)",
          fa_[30, 30, 0] > 200 and fa_[30, 30, 1] < 60 and fa_[30, 10].max() < 80)
    from animkit.finish import dither
    flat = np.full((60, 80, 3), 128, np.uint8)
    d1, d2 = dither(flat), dither(flat)
    check("dither: static (same every frame), breaks flat steps, mean preserved",
          np.array_equal(d1, d2) and d1.std() > 0.8 and abs(float(d1.mean()) - 128) < 0.3)
    from animkit.curves import Tremor
    tr_ = Tremor(Channel([K(0, 5.0)]), 10, 30, amp=2.0)
    vals = [tr_(f_) for f_ in range(0, 40)]
    check("Tremor: alternates inside its window only, pure in f", vals[0] == 5.0 and vals[35] == 5.0
          and (vals[20] - 5.0) * (vals[21] - 5.0) < 0 and tr_(20.0) == tr_(20.0) and max(abs(v - 5) for v in vals) <= 2.0)

    # ---- v3: face rig, expressions, lip sync, limb stretch, body_dy convention
    from animkit.rigs import RigStyle
    from animkit.face import ExpressionTrack, expression, eye_darts
    tr = ExpressionTrack([(0, "neutral"), (20, "idea", "snap")]).channels()
    brow_t = next(f for f in np.arange(0, 30, 0.25) if tr["brow_l"](f) > 0.2)
    mouth_t = next(f for f in np.arange(0, 30, 0.25) if tr["mouth_round"](f) > 0.2)
    check("expressions: brows lead the mouth", brow_t < mouth_t, f"brows {brow_t}, mouth {mouth_t}")
    fr = BlobRig(RigStyle(face_rig=True))
    pf2 = Performer(fr, [Walk(0, 1, 400, start=1e6)], range(0, 40),
                    channels={**tr, **eye_darts([(5, (-1.0, 0.0))]), "body_dy": Channel([K(0, -30.0)])})
    p2 = pf2.pose(25)
    check("body_dy: negative lifts the body (and tucks the feet)", p2.hip[1] < 400 - 74 - 20 and p2.airborne)
    import copy
    p3 = copy.copy(p2)
    p3.lean = 0.3
    v0 = fr.shoulder(p2, 1) - fr.centre(p2)
    v1 = fr.shoulder(p3, 1) - fr.centre(p3)
    ang = math.atan2(v1[1], v1[0]) - math.atan2(v0[1], v0[0])
    check("shoulders rotate with the body lean (arms stay below the face)", abs(ang - (0.3 - p2.lean)) < 1e-6,
          f"{ang:.3f} rad")
    fc = Canvas(300, 300, "#20262E")
    fr.draw(fc, p2, Light(), ground=400)
    check("face rig draws (brows, lids, mouth)", fc.array().std() > 10 and p2.face["mouth_round"] > 0.5)
    p3 = pf2.pose(25)
    p3.near_hand, p3.near_stretch = (0.0, -200.0), 1.6
    h_far = fr.draw(Canvas(300, 300), p3)["hand"]
    p3.near_stretch = 1.0
    h_near = fr.draw(Canvas(300, 300), p3)["hand"]
    check("limb stretch extends the reach", h_far[1] < h_near[1] - 20, f"{h_near[1] - h_far[1]:.0f} px")
    from animkit import lipsync
    sr_ = 24000
    t_ = np.arange(int(0.4 * sr_)) / sr_
    ah = 0.3 * sum((np.exp(-((130 * h - 750) / 150) ** 2) + np.exp(-((130 * h - 1200) / 200) ** 2))
                   * np.sin(2 * np.pi * 130 * h * t_) for h in range(1, 30))
    oo = 0.3 * sum(np.exp(-((130 * h - 320) / 80) ** 2) * np.sin(2 * np.pi * 130 * h * t_) for h in range(1, 30))
    sil = np.zeros(int(0.3 * sr_))
    ls = lipsync.from_audio(np.concatenate([sil, ah, sil, oo, sil]), sr_, fps=24)
    seg = lambda a, b: slice(int(a * 24) + 2, int(b * 24) - 1)  # noqa: E731
    check("lip sync: open on vowels, round on OO, closed in silence",
          ls.open[seg(0.3, 0.7)].mean() > 0.5 and ls.round[seg(1.0, 1.4)].mean() > ls.round[seg(0.3, 0.7)].mean() + 0.3
          and ls.open[1:4].max() == 0.0)

    # ---- v3: FX, delivery, deslop lint
    from animkit import fx
    b_ = fx.dust_puff(10, (100, 100), ground=100)
    c1, c2 = Canvas(200, 160), Canvas(200, 160)
    b_.draw(c1, 15.0)
    b_.draw(c2, 15.0)
    check("FX are pure functions of time", np.array_equal(c1.rgba_array(), c2.rgba_array()) and c1.rgba_array()[..., 3].max() > 0)
    from animkit import deliver as D
    from animkit.timeline import render
    with tempfile.TemporaryDirectory() as td:
        def spin(cv, f):
            cv.clear("#F3EDE2")
            with cv.at(40, 30, 2 * math.pi * f / 24):
                cv.rect(-15, -15, 30, 30, "#3FA7A0")
        render(spin, 24, os.path.join(td, "l.mp4"), w=80, h=60, workers=1, log_every=0)
        render(spin, 25, os.path.join(td, "d.mp4"), w=80, h=60, workers=1, log_every=0)
        _main = os.getpid()

        def _die(cv, f):
            if f >= 6 and os.getpid() != _main:
                os._exit(9)
            cv.clear("#202020")
        rr = render(_die, 16, os.path.join(td, "die.mp4"), w=64, h=48, workers=2, log_every=0)
        n_out = D.count_frames(os.path.join(td, "die.mp4"))
        check("parallel render: a killed worker is replaced by a smaller pool, every frame still written",
              rr["workers"] == 1 and n_out == 16, f"workers {rr['workers']}, frames {n_out}")
        check("loop check: seamless passes, duplicated end frame fails",
              D.loop_report(os.path.join(td, "l.mp4"))["seamless"] and not D.loop_report(os.path.join(td, "d.mp4"))["seamless"])
        g = D.gif(os.path.join(td, "l.mp4"), os.path.join(td, "l.gif"), fps=12, width=80, max_mb=1)
        check("GIF export within budget", g["mb"] <= 1 and os.path.exists(g["path"]))
        from PIL import Image as _Im
        for i_ in (0, 1, 2, 4):
            _Im.fromarray(np.full((16, 16, 4), 200, np.uint8), "RGBA").save(os.path.join(td, f"q_{i_:05d}.png"))
        try:
            D.apng(os.path.join(td, "q_%05d.png"), os.path.join(td, "q.png"), fps=12)
            gap_ok = False
        except RuntimeError:
            gap_ok = True
        _Im.fromarray(np.full((16, 16, 4), 200, np.uint8), "RGBA").save(os.path.join(td, "q_00003.png"))
        ap = D.apng(os.path.join(td, "q_%05d.png"), os.path.join(td, "q.png"), fps=12)
        check("alpha exports refuse gapped sequences and confirm every frame", gap_ok and ap["frames"] == 5)
    lint =subprocess.run([sys.executable, os.path.join(SCRIPTS, "qa", "slop_lint.py"), "--text",
                           "Unleash a seamless experience", "--text", "Fourteen of 20 sessions stopped at bank linking."],
                          capture_output=True, text=True).stdout
    check("slop_lint flags stock copy only", "unleash" in lint and "seamless" in lint and "Fourteen" not in lint)

    with tempfile.TemporaryDirectory() as td:
        sys.path.insert(0, os.path.join(SCRIPTS, "qa"))
        import reel_critic as RC
        yy = np.linspace(0, 1, 360)[:, None] * np.ones((1, 640))
        grad = 150 + 20 * (yy + 0.3 * np.linspace(0, 1, 640)[None, :])
        rng = np.random.default_rng(1)
        for name, img in (("band", np.round(grad)), ("dith", np.round(grad + rng.normal(0, 1.3, grad.shape)))):
            fr = np.clip(img, 0, 255).astype(np.uint8)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "640x360", "-r", "1",
                            "-i", "-", "-frames:v", "2", "-c:v", "ffv1", os.path.join(td, name + ".mkv")],
                           input=fr.tobytes() * 2, check=True)
        info = {"width": 640, "height": 360, "duration": 2.0}
        bb = RC.banding_analysis(os.path.join(td, "band.mkv"), info, samples=2)
        bd = RC.banding_analysis(os.path.join(td, "dith.mkv"), info, samples=2)
        check("banding check: flat steps flagged, dithered gradient passes",
              bb and bd and bb["flat_share"] > 0.45 and bd["flat_share"] < 0.25,
              f"banded {bb and bb['flat_share']}, dithered {bd and bd['flat_share']}")

    from animkit import audio as A
    with tempfile.TemporaryDirectory() as td:
        m = A.Mix(3.0)
        m.add(A.rain(3.0, 0.6, seed=1), 0, -10, bus="amb")
        for i in range(5):
            m.add(A.footstep(seed=i, wet=0.5), 0.4 + i * 0.45, -4)
        stats = A.master(m.render(), os.path.join(td, "t.wav"), target_lufs=-16)
        check("audio master hits target", stats["I"] is not None and abs(stats["I"] + 16) < 1.0, json.dumps(stats))
        check("audio true peak headroom", stats["TP"] is not None and stats["TP"] <= -1.0, str(stats["TP"]))

    if "--render" in sys.argv:
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "ball.mp4")
            subprocess.run([sys.executable, os.path.join(SCRIPTS, "examples", "bouncing_ball.py"), "--out", out, "--mb", "2"],
                           check=True)
            qa = os.path.join(td, "qa")
            subprocess.run([sys.executable, os.path.join(SCRIPTS, "qa", "reel_critic.py"), out, "--out", qa, "--no-sheet",
                            "--target-lufs", "-16"], check=True, capture_output=True)
            rep = json.load(open(os.path.join(qa, "report.json")))
            highs = [f for f in rep["flags"] if f["severity"] == "high"]
            check("bouncing ball renders with no HIGH QA flags", not highs, "; ".join(f["finding"] for f in highs))

    try:
        import bpy  # noqa: F401
        check("bpy available (optional)", True, bpy.app.version_string)
    except ImportError:
        print("SKIP bpy not installed (optional: pip install bpy for the 3-D kit)")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
