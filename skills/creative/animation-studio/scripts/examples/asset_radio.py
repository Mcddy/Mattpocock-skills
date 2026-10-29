#!/usr/bin/env python3
"""ASSET + PRODUCT SHOT - reference 3-D job for the animation-studio skill.

Builds an original compact field radio as a clean, real-scale asset (metres,
applied scale, named parts, bevelled edges, procedural wood / grille / glass),
then:
  1. exports a GLB and prints an asset report (tris, size, materials, UVs)
  2. renders a 4-view asset sheet (front, three-quarter, side, top)
  3. renders a short product beat where the product *does its thing*: power LED
     on, tuning knob turns with anticipation and settle, the needle follows with
     spring lag, the dial backlight warms up; camera eases in with shallow DOF.

Run:
  python3 asset_radio.py --out DIR [--frames 72] [--samples 24] [--res 960x540]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "blender"))

import bpy  # noqa: E402
import scene_kit as K  # noqa: E402
from animkit.curves import Channel, K as Key  # noqa: E402
from animkit.principles import Spring  # noqa: E402


def build():
    wood = K.wood("Walnut", light="#8E5A30", dark="#4E2B14", scale=1.0, axis="X")
    trim = K.material("Trim", "#2B2D30", 0.35, 0.0, coat=0.2)
    brass = K.material("Brass", "#C89B52", 0.28, 1.0)
    steel = K.material("Steel", "#B8BCC2", 0.22, 1.0)
    grille = K.grille("Grille", "#26292D", "#08090A", density=520)
    dial_glass = K.material("DialGlass", "#D9C7A2", 0.15, 0.0, emission="#FFA54A", emit=0.0)
    led = K.material("LED", "#3A0F0A", 0.3, 0.0, emission="#FF4A2A", emit=0.0)
    needle_m = K.material("Needle", "#D2402C", 0.4)
    knob_m = K.material("Knob", "#1C1D1F", 0.45, 0.0, coat=0.5)

    root = K.empty("Radio")
    W, D, H = 0.30, 0.11, 0.17                       # real size: 30 x 11 x 17 cm
    body = K.box("Body", (W, D, H), (0, 0, H / 2 + 0.012), wood, bevel=0.012, segments=4)
    face = K.box("Faceplate", (W - 0.024, 0.006, H - 0.03), (0, -D / 2 - 0.002, H / 2 + 0.012), trim, bevel=0.004)
    spk = K.cylinder("Speaker", 0.052, 0.006, (-0.065, -D / 2 - 0.006, H / 2 + 0.012), (math.pi / 2, 0, 0), grille, bevel=0.002)
    ring = K.cylinder("SpeakerRing", 0.056, 0.004, (-0.065, -D / 2 - 0.004, H / 2 + 0.012), (math.pi / 2, 0, 0), brass, bevel=0.0015)
    dial = K.box("Dial", (0.105, 0.004, 0.034), (0.07, -D / 2 - 0.006, H / 2 + 0.045), dial_glass, bevel=0.003)
    needle = K.box("Needle", (0.0016, 0.002, 0.026), (0.03, -D / 2 - 0.0095, H / 2 + 0.045), needle_m)
    knob1 = K.cylinder("TuneKnob", 0.019, 0.016, (0.095, -D / 2 - 0.012, H / 2 - 0.012), (math.pi / 2, 0, 0), knob_m, bevel=0.003)
    knob1.rotation_mode = "ZXY"          # so rotation_euler[2] spins the knob about its own axis
    mark = K.box("TuneMark", (0.0025, 0.010, 0.002), (0, 0, 0), K.material("Mark", "#E8E2D6", 0.4))
    mark.parent = knob1
    mark.location = (0, 0.009, 0.0085)
    knob2 = K.cylinder("VolumeKnob", 0.014, 0.014, (0.045, -D / 2 - 0.011, H / 2 - 0.012), (math.pi / 2, 0, 0), knob_m, bevel=0.003)
    ledo = K.sphere("PowerLED", 0.0035, (0.13, -D / 2 - 0.006, H / 2 - 0.045), led)
    handle_l = K.cylinder("HandlePostL", 0.006, 0.03, (-0.11, 0, H + 0.025), (0, 0, 0), brass)
    handle_r = K.cylinder("HandlePostR", 0.006, 0.03, (0.11, 0, H + 0.025), (0, 0, 0), brass)
    handle = K.cylinder("Handle", 0.008, 0.23, (0, 0, H + 0.042), (0, math.pi / 2, 0), trim, bevel=0.002)
    ant = K.cylinder("Antenna", 0.0022, 0.15, (0.105, 0.02, H + 0.07), (0.0, 0.62, 0.0), steel)
    tickm = K.material("Ticks", "#3A3128", 0.5)
    ticks = [K.box(f"Tick{i}", (0.0009, 0.002, 0.007 if i % 3 == 0 else 0.004),
                   (0.03 + i * 0.0075, -D / 2 - 0.0085, H / 2 + 0.054), tickm) for i in range(11)]
    feet = [K.box(f"Foot{i}", (0.03, 0.02, 0.012), (x, y, 0.006), trim, bevel=0.003)
            for i, (x, y) in enumerate([(-0.11, -0.035), (0.11, -0.035), (-0.11, 0.035), (0.11, 0.035)])]
    parts = [body, face, spk, ring, dial, needle, knob1, knob2, ledo, handle_l, handle_r, handle, ant] + feet + ticks
    for p in parts:
        K.parent(p, root)
    # smart-UV every part so the GLB carries UVs (procedural shaders use object coords in Blender)
    for p in parts:
        bpy.context.view_layer.objects.active = p
        p.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
        p.select_set(False)
    return dict(root=root, parts=parts, export=parts + [mark], knob=knob1, needle=needle, dial=dial_glass,
                led=led, body=body)


def studio():
    K.world((0.012, 0.012, 0.014), 1.0)
    cyc = K.cyclorama(4, 3, 2, 0.5, "#2A2C30", 0.9)
    cyc.location = (0, 0.6, 0)
    K.three_point((0, 0, 0.09), dist=0.7, key=60.0)
    return cyc


def animate(a, frames, fps=24):
    sc = bpy.context.scene
    # power LED + dial warm-up
    led_bsdf = a["led"].node_tree.nodes["Principled BSDF"]
    dial_bsdf = a["dial"].node_tree.nodes["Principled BSDF"]
    for f, v in [(1, 0.0), (9, 0.0), (10, 6.0), (frames, 6.0)]:
        led_bsdf.inputs["Emission Strength"].default_value = v
        K.key(led_bsdf.inputs["Emission Strength"], "default_value", f, interp="CONSTANT")
    warm = Channel([Key(1, 0.0), Key(11, 0.0, "snap"), Key(13, 3.0), Key(15, 1.2, "out_quad"), Key(24, 5.0, "slow_in_out"),
                    Key(frames, 5.0)])
    K.animkit_channel_bake(dial_bsdf.inputs["Emission Strength"], "default_value", -1, warm, range(1, frames + 1))
    # tuning knob: anticipation, turn, settle (animkit channel baked to Blender keys)
    knob = a["knob"]
    turn = Channel([Key(1, 0.0), Key(18, 0.0, "anticipate"), Key(28, -2.1, "settle"), Key(44, -2.1), Key(frames, -2.1)])
    for f in range(1, frames + 1):
        knob.rotation_euler[2] = turn(f)
        knob.keyframe_insert("rotation_euler", index=2, frame=f)
    # needle follows the knob through a spring (lag + overshoot): mechanical linkage feel
    needle = a["needle"]
    x0 = needle.location.x
    s = Spring(0.0, stiffness=140, damping=0.45)
    tuning = {}
    for f in range(1, frames + 1):
        target = -turn(f) / 2.1 * 0.075
        dx = float(s.step(target, 1 / fps))
        tuning[f] = dx / 0.075                     # 0 = off-station, 1 = on the station
        needle.location.x = x0 + dx
        needle.keyframe_insert("location", index=0, frame=f)
    a["turn"], a["tuning"], a["warm"] = turn, tuning, warm
    # camera: slow push with eased arc; focus on the dial
    rig = K.empty("CamRig", (0, 0, 0.09))
    cam = K.camera((0.0, -0.82, 0.21), (0.02, 0, 0.1), lens=50, dof_target=a["dial_obj"], fstop=2.8)
    K.parent(cam, rig)
    for f, rz, dist in [(1, -0.5, 1.0), (frames, -0.14, 0.74)]:
        rig.rotation_euler[2] = rz
        K.key(rig, "rotation_euler", f, index=2, interp="BEZIER")
        rig.scale = (dist, dist, dist)
        K.key(rig, "scale", f, interp="BEZIER")
    # framing gate: the radio body must stay inside a 5% safe margin for the whole move
    # (the antenna may leave frame on the push-in; that's a choice, not an accident)
    hero = [bpy.data.objects[n] for n in ("Body", "Faceplate", "Handle")]
    end_scale, rep = K.fit_rig_scale(rig, cam, hero, frames, range(1, frames + 1, 3), margin=0.05)
    print("FRAMING", json.dumps({"end_scale": round(end_scale, 3), **rep}))
    a["framing"] = rep
    sc.frame_set(1)
    return cam


def build_audio(a, frames, out_wav, cues_json, fps=24):
    """Sound from the animation: power click, mains hum with the warm-up, a detent tick
    every 1/10 of the knob's travel, a settle clunk, tuning static and whistle that follow
    the needle, then the station fades in through a small-speaker EQ."""
    import numpy as np
    from animkit import audio as A
    t_of = lambda f: (f - 1) / fps          # Blender frame 1 is t = 0 in the video   # noqa: E731
    dur = frames / fps + 0.4
    m = A.Mix(dur)
    cues = []
    m.add(A.filt(A.noise(dur, "brown", 3), "lp", 300) * 0.25, 0, -30, bus="amb")       # room tone
    cues.append({"frame": 10, "t": t_of(10), "kind": "switch"})
    m.add(A.switch_click(seed=1), t_of(10), -6)
    m.add(A.thump(seed=2, pitch=2.4) * 0.5, t_of(11), -16)                               # speaker pop
    # mains hum follows the dial warm-up (50 Hz)
    n = int(dur * A.SR)
    tt = np.arange(n) / A.SR
    env = np.array([a["warm"](1 + x * fps) for x in tt]) / 5.0
    m.add(A.hum(dur, 50.0, 1.0) * env, 0, -30, bus="amb")
    # detent ticks: one per 1/10 of travel, timed at the sub-frame crossing
    turn = a["turn"]
    step = 2.1 / 10
    prev = 0.0
    k = 0
    for f10 in range(10, frames * 10):
        f = f10 / 10
        ang = -turn(f)
        if math.floor(ang / step) != math.floor(prev / step) and f > 17:
            m.add(A.switch_click(seed=10 + k) * 0.55, t_of(f), -12 - 2 * (k % 2), 0.15)
            cues.append({"frame": f, "t": t_of(f), "kind": "detent"})
            k += 1
        prev = ang
    cues.append({"frame": 28, "t": t_of(28), "kind": "settle"})
    m.add(A.thump(seed=5, pitch=1.8) * 0.7, t_of(28), -12, 0.15)
    # tuning: static + heterodyne whistle driven by the needle position
    tun = a["tuning"]
    pos = np.interp(1 + tt * fps, list(tun.keys()), list(tun.values()))
    on = np.clip((tt - t_of(12)) / 0.25, 0, 1)
    off_station = np.clip(1 - pos, 0, 1)
    static = A.filt(A.noise(dur, "pink", 11), "bp", (700, 5200))
    m.add(static * on * (0.15 + 0.85 * off_station ** 0.7) * 0.6, 0, -16, bus="radio")
    whistle_f = 180 + 2600 * off_station
    phase = 2 * np.pi * np.cumsum(whistle_f) / A.SR
    m.add(np.sin(phase) * on * off_station * (pos > 0.02) * 0.25, 0, -20, bus="radio")
    # the station: a short warm phrase, small-speaker EQ, slight saturation
    t_station = t_of(34)
    chords = [("D4", "F#4", "A4", "C#5"), ("B3", "D4", "F#4", "A4"), ("G3", "B3", "D4", "F#4")]
    for i, ch in enumerate(chords):
        for nn in ch:
            m.add(A.keys_note(A.hz(nn), 1.2, 0.45), t_station + i * 0.55, -12, bus="station")
    m.add(A.keys_note(A.hz("A5"), 0.8, 0.5), t_station + 0.27, -14, bus="station")
    m.add(A.keys_note(A.hz("F#5"), 0.8, 0.45), t_station + 0.82, -15, bus="station")
    st = m.bus("station")
    st[:] = np.tanh(A.filt(st, "bp", (220, 4200)) * 2.2) * 0.6
    fade = np.clip((tt - t_station + 0.15) / 0.4, 0, 1)[:, None]
    m.buses["station"] = st * fade
    cues.append({"frame": 34, "t": t_station, "kind": "station"})
    m.process("sfx", lambda x: A.reverb(x, 0.12, 0.5, 0.006))
    mixdown = m.render(levels={"amb": 0.0, "sfx": 0.0, "radio": -2.0, "station": -1.0})
    stats = A.master(mixdown, out_wav, target_lufs=-16.0, true_peak=-1.5, lra=12)
    with open(cues_json, "w") as fh:
        json.dump(cues, fh, indent=1)
    return stats


def asset_sheet(out_png, size=520, samples=16):
    """Front / three-quarter / side / top on a neutral cyc, tiled to one image."""
    from PIL import Image
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.cycles.samples = samples
    sc.render.use_motion_blur = False
    views = [("front", (0, -0.75, 0.1), 60), ("three_quarter", (0.48, -0.55, 0.3), 60),
             ("side", (0.75, 0, 0.1), 60), ("top", (0.0, -0.05, 0.8), 55)]
    tiles = []
    tmp = os.path.dirname(out_png)
    for name, loc, lens in views:
        cam = K.camera(loc, (0, 0, 0.09), lens=lens, name=f"Sheet_{name}")
        p = os.path.join(tmp, f"sheet_{name}.png")
        K.render_still(p, frame=1)
        tiles.append(Image.open(p).convert("RGB"))
    sheet = Image.new("RGB", (size * 4, size), (20, 20, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * size, 0))
    sheet.save(out_png)
    return out_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=72)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--res", default="960x540")
    ap.add_argument("--skip-anim", action="store_true")
    ap.add_argument("--audio-only", action="store_true", help="reuse rendered frames; rebuild sound + mux")
    a = ap.parse_args([x for x in sys.argv[1:] if x != "--"])
    os.makedirs(a.out, exist_ok=True)
    rx, ry = map(int, a.res.split("x"))
    K.reset(24, (rx, ry), (1, a.frames))
    K.engine("CYCLES", samples=a.samples, denoise=True, motion_blur=True)
    parts = build()
    parts["dial_obj"] = bpy.data.objects["Dial"]
    studio()
    rep = K.asset_report(parts["export"])
    print("ASSET REPORT", json.dumps(rep))
    K.export_glb(os.path.join(a.out, "field_radio.glb"), parts["export"])
    with open(os.path.join(a.out, "asset_report.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    if not a.audio_only:
        asset_sheet(os.path.join(a.out, "asset_sheet.png"))
    if not a.skip_anim:
        sc = bpy.context.scene
        sc.render.resolution_x, sc.render.resolution_y = rx, ry
        sc.cycles.samples = a.samples
        sc.render.use_motion_blur = True
        animate(parts, a.frames)
        if parts["framing"]["bad"]:
            print("WARNING framing still violated on frames", parts["framing"]["bad"])
        silent = os.path.join(a.out, "product_beat_silent.mp4")
        if not a.audio_only:
            K.render_sequence(os.path.join(a.out, "frames"))
            K.encode(os.path.join(a.out, "frames"), silent)
        wav = os.path.join(a.out, "product_beat.wav")
        print("AUDIO", build_audio(parts, a.frames, wav, os.path.join(a.out, "product_beat_cues.json")))
        from animkit.timeline import mux
        mux(silent, wav, os.path.join(a.out, "product_beat.mp4"))
    print("done", a.out)


if __name__ == "__main__":
    main()
