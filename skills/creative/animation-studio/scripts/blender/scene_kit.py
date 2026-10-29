"""Headless Blender helpers (bpy module or `blender -b -P script.py`).

Tested with the `bpy` 5.2 wheel (pip install bpy; needs the matching CPython,
e.g. bpy 5.2 -> Python 3.13). Written defensively for 4.2+ API differences:
EEVEE engine id, Principled BSDF socket names, slotted actions (4.4+/5.x).

Covers: scene/render setup, colour management, materials (incl. procedural
wood, brushed metal, glass, emission), primitives with bevels, camera with DOF,
lighting rigs (three-point, cyclorama), eased keyframes, spring-baked secondary
motion, seamless turntables, renders -> ffmpeg, GLB export, asset report.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


# ------------------------------------------------------------------ scene
def reset(fps=24, res=(1920, 1080), frames=(1, 120), pct=100):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = pct
    sc.frame_start, sc.frame_end = frames
    view = sc.view_settings
    for vt in ("AgX", "Filmic", "Standard"):
        try:
            view.view_transform = vt
            break
        except TypeError:
            continue
    for look in ("AgX - Medium High Contrast", "AgX - Base Contrast", "Medium High Contrast", "None"):
        try:
            view.look = look
            break
        except TypeError:
            continue
    return sc


def engine(kind="CYCLES", samples=64, denoise=True, motion_blur=True, shutter=0.5, device="CPU"):
    sc = bpy.context.scene
    ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if kind == "CYCLES":
        if "CYCLES" not in ids:
            import addon_utils
            addon_utils.enable("cycles", default_set=True)
        sc.render.engine = "CYCLES"
        sc.cycles.samples = samples
        sc.cycles.device = device
        sc.cycles.use_denoising = denoise
        try:
            sc.cycles.use_adaptive_sampling = True
        except AttributeError:
            pass
    else:
        sc.render.engine = next((i for i in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if i in ids), ids[0])
        try:
            sc.eevee.taa_render_samples = samples
        except AttributeError:
            pass
    sc.render.use_motion_blur = motion_blur
    sc.render.motion_blur_shutter = shutter
    return sc.render.engine


def world(color=(0.05, 0.06, 0.08), strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    out = w.node_tree.nodes.get("World Output") or w.node_tree.nodes.new("ShaderNodeOutputWorld")
    w.node_tree.links.new(bg.outputs[0], out.inputs[0])
    return w


# ------------------------------------------------------------------ materials
def _set(node, names, value):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def hexcol(h):
    """sRGB hex -> linear RGBA for Blender sockets."""
    h = h.lstrip("#")
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(int(h[0:2], 16)), lin(int(h[2:4], 16)), lin(int(h[4:6], 16)), 1.0)


def material(name, base="#808080", rough=0.5, metal=0.0, coat=0.0, emission=None, emit=0.0,
             transmission=0.0, ior=1.45, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    _set(bsdf, "Base Color", hexcol(base) if isinstance(base, str) else base)
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Metallic", metal)
    _set(bsdf, ["Coat Weight", "Clearcoat"], coat)
    _set(bsdf, ["Transmission Weight", "Transmission"], transmission)
    _set(bsdf, "IOR", ior)
    _set(bsdf, "Alpha", alpha)
    if emission:
        _set(bsdf, ["Emission Color", "Emission"], hexcol(emission) if isinstance(emission, str) else emission)
        _set(bsdf, "Emission Strength", emit)
    return m


def wood(name="Wood", light="#9A6234", dark="#5A3218", scale=1.0, rough=0.42, coat=0.35, axis="X"):
    """Procedural wood: noise stretched along the grain axis -> colour ramp, plus matching bump.

    Grain runs along `axis` in object space. `scale` multiplies grain density (1.0 suits
    objects 10-50 cm across; raise for larger objects).
    """
    m = material(name, light, rough, 0.0, coat)
    nt = m.node_tree
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    stretch = {"X": (4.0, 90.0, 90.0), "Y": (90.0, 4.0, 90.0), "Z": (90.0, 90.0, 4.0)}[axis]
    mp.inputs["Scale"].default_value = tuple(v * scale for v in stretch)
    wave = N.new("ShaderNodeTexNoise")
    wave.inputs["Scale"].default_value = 1.0
    wave.inputs["Detail"].default_value = 8.0
    try:
        wave.inputs["Distortion"].default_value = 1.5
    except KeyError:
        pass
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hexcol(dark)
    ramp.color_ramp.elements[1].color = hexcol(light)
    ramp.color_ramp.elements[0].position = 0.25
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bsdf = N.get("Principled BSDF")
    L = nt.links
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    L.new(mp.outputs["Vector"], wave.inputs["Vector"])
    L.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L.new(wave.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def grille(name="Grille", base="#1E2226", hole="#0A0B0C", density=60.0):
    """Perforated speaker grille without geometry: dot pattern drives colour + bump."""
    m = material(name, base, 0.55, 0.6)
    nt = m.node_tree
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = density
    try:
        vor.inputs["Randomness"].default_value = 0.0
    except KeyError:
        pass
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = hexcol(hole)
    ramp.color_ramp.elements[1].position = 0.22
    ramp.color_ramp.elements[1].color = hexcol(base)
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bsdf = N.get("Principled BSDF")
    L = nt.links
    L.new(tc.outputs["Object"], vor.inputs["Vector"])
    L.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L.new(vor.outputs["Distance"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def emission_node(mat):
    """Return (bsdf, socket name) for animating emission strength."""
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    return bsdf, "Emission Strength"


# ------------------------------------------------------------------ geometry
def _finish(obj, name, mat=None, bevel=0.0, segments=3, smooth=True, collection=None):
    obj.name = name
    if obj.data is not None:
        obj.data.name = name          # mesh names survive into GLB/FBX; keep them meaningful
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
        try:
            mod.harden_normals = True
        except AttributeError:
            pass
    if smooth:
        try:
            bpy.ops.object.shade_smooth_by_angle()
        except (AttributeError, RuntimeError):
            bpy.ops.object.shade_smooth()
    if collection:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.0, segments=3, **kw):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, name, mat, bevel, segments, **kw)


def cylinder(name, r, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, verts=64, bevel=0.0, **kw):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    return _finish(o, name, mat, bevel, **kw)


def sphere(name, r, loc=(0, 0, 0), mat=None, seg=48, **kw):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    return _finish(bpy.context.active_object, name, mat, **kw)


def empty(name, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def parent(child, par, keep_transform=True):
    # matrix_world of freshly created objects is stale until the depsgraph updates
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = par
    if keep_transform:
        child.matrix_world = mw
    return child


# ------------------------------------------------------------------ camera & light
def camera(loc, target=(0, 0, 0), lens=50.0, dof_target=None, fstop=4.0, name="Camera"):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    look_at(cam, target)
    cam.data.lens = lens
    if dof_target is not None:
        cam.data.dof.use_dof = True
        if isinstance(dof_target, bpy.types.Object):
            cam.data.dof.focus_object = dof_target
        else:
            cam.data.dof.focus_distance = float(dof_target)
        cam.data.dof.aperture_fstop = fstop
    bpy.context.scene.camera = cam
    return cam


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def area_light(name, loc, target, power=500.0, size=1.0, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = power
    ld.size = size
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    return o


def three_point(target=(0, 0, 0), dist=3.0, key=600.0, warm=(1.0, 0.92, 0.82), cool=(0.8, 0.9, 1.0)):
    """Key (warm, 45 deg), fill (cool, soft, opposite), rim (behind, hard edge)."""
    t = Vector(target)
    k = area_light("Key", t + Vector((dist * 0.8, -dist * 0.8, dist * 0.7)), t, key, dist * 0.5, warm)
    f = area_light("Fill", t + Vector((-dist, -dist * 0.5, dist * 0.3)), t, key * 0.25, dist * 0.9, cool)
    r = area_light("Rim", t + Vector((-dist * 0.3, dist * 1.0, dist * 0.9)), t, key * 0.8, dist * 0.2, (1, 1, 1))
    return k, f, r


def cyclorama(width=12.0, depth=8.0, height=5.0, radius=1.5, color="#D8D2C8", rough=0.8):
    """Seamless studio backdrop: floor curving up into a back wall (no horizon line)."""
    import bmesh
    mesh = bpy.data.meshes.new("Cyc")
    bm = bmesh.new()
    pts = [(-depth / 2, 0.0), (depth / 2 - radius, 0.0)]
    for i in range(1, 12):
        a = (math.pi / 2) * i / 11
        pts.append((depth / 2 - radius + math.sin(a) * radius, radius - math.cos(a) * radius))
    pts.append((depth / 2, height))
    rows = []
    for x in (-width / 2, width / 2):
        rows.append([bm.verts.new((x, y, z)) for y, z in pts])
    for i in range(len(pts) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("Cyclorama", mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(material("Cyc", color, rough))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ------------------------------------------------------------------ animation
def fcurves_of(id_data):
    """F-curves of an ID's action across legacy and slotted-action APIs."""
    ad = id_data.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    try:
        return list(act.fcurves)                      # <= 4.x legacy
    except AttributeError:
        pass
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        return list(cb.fcurves) if cb else []
    except Exception:  # noqa: BLE001
        out = []
        for layer in getattr(act, "layers", []):
            for strip in layer.strips:
                for cb in getattr(strip, "channelbags", []):
                    out += list(cb.fcurves)
        return out


def key(target, path, frame, value=None, index=-1, interp="BEZIER", easing="AUTO", handles="AUTO_CLAMPED"):
    """Insert a key and shape it. interp: BEZIER | LINEAR | CONSTANT | BACK | ELASTIC | SINE | ...

    easing: AUTO | EASE_IN | EASE_OUT | EASE_IN_OUT (for the dynamic interps).
    Holds = CONSTANT (blocking). Bezier + AUTO_CLAMPED = slow in/out without overshoot.
    """
    if value is not None:
        if index >= 0:
            getattr(target, path)[index] = value
        else:
            setattr(target, path, value)
    target.keyframe_insert(data_path=path, frame=frame, index=index)
    owner = target.id_data
    for fc in fcurves_of(owner):
        if fc.data_path.endswith(path) and (index < 0 or fc.array_index == index):
            for kp in fc.keyframe_points:
                if abs(kp.co[0] - frame) < 1e-4:
                    kp.interpolation = interp
                    kp.easing = easing
                    kp.handle_left_type = handles
                    kp.handle_right_type = handles
    return target


def linear_all(id_data):
    for fc in fcurves_of(id_data):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def turntable(obj, start, end, turns=1.0, axis=2):
    """Seamless loop: render [start, end-1] so the last frame isn't a duplicate of the first."""
    obj.rotation_euler[axis] = 0.0
    key(obj, "rotation_euler", start, index=axis, interp="LINEAR")
    obj.rotation_euler[axis] = 2 * math.pi * turns
    key(obj, "rotation_euler", end, index=axis, interp="LINEAR")


def spring_bake(target, path, index, drive, frames, stiffness=180.0, damping=0.3, fps=24.0, scale=1.0):
    """Bake secondary motion: value follows drive(frame) through a damped spring (animkit)."""
    from animkit.principles import Spring
    s = Spring(drive(frames[0]), stiffness, damping)
    for f in frames:
        v = float(s.step(drive(f), 1 / fps)) * scale
        getattr(target, path)[index] = v
        target.keyframe_insert(data_path=path, frame=f, index=index)


def animkit_channel_bake(target, path, index, channel, frames):
    """Drive any property from an animkit Channel (same easing vocabulary as the 2-D kit)."""
    for f in frames:
        v = float(channel(f))
        if index >= 0:
            getattr(target, path)[index] = v
        else:
            setattr(target, path, v)
        target.keyframe_insert(data_path=path, frame=f, index=index)


# ------------------------------------------------------------------ output
def render_still(path, frame=None):
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    sc.render.filepath = os.path.abspath(path)
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    return path


def render_sequence(out_dir, prefix="f_"):
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    sc.render.filepath = os.path.join(os.path.abspath(out_dir), prefix)
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
    return out_dir


def encode(out_dir, out_mp4, fps=24, prefix="f_", start=None, crf=16):
    sc = bpy.context.scene
    start = sc.frame_start if start is None else start
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps),
                    "-start_number", str(start), "-i", os.path.join(out_dir, f"{prefix}%04d.png"),
                    "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", out_mp4], check=True)
    return out_mp4


def export_glb(path, objects=None):
    bpy.ops.object.select_all(action="DESELECT")
    objs = objects or [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "Cyclorama"]
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(path), export_format="GLB", use_selection=True,
                              export_apply=True)
    return path


def asset_report(objects=None) -> dict:
    """Triangle count (evaluated), dimensions, materials, UVs: the asset QA basics."""
    dg = bpy.context.evaluated_depsgraph_get()
    objs = objects or [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "Cyclorama"]
    tris = 0
    mats = set()
    no_uv = []
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        if not me.uv_layers:
            no_uv.append(o.name)
        for v in me.vertices:
            w = ev.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
        for s in o.material_slots:
            if s.material:
                mats.add(s.material.name)
    return {"objects": len(objs), "triangles": tris, "size_m": [round(v, 3) for v in (hi - lo)],
            "materials": sorted(mats), "missing_uvs": no_uv}


# ------------------------------------------------------------------ framing checks
def _bbox_world(objects):
    pts = []
    for o in objects:
        mw = o.matrix_world
        pts.extend(mw @ Vector(c) for c in o.bound_box)
    return pts


def frame_report(cam, objects, frames, margin=0.04):
    """Where do `objects` sit in the camera frame across `frames`?

    Returns {"worst": (frame, min_x, max_x, min_y, max_y), "bad": [frames outside the safe
    margin]} in normalised camera coordinates (0..1). Run it before rendering any camera
    move: a push-in that crops the hero object is the classic unchecked mistake.
    """
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bad, worst, worst_val = [], None, -1.0
    for f in frames:
        sc.frame_set(int(f))
        co = [world_to_camera_view(sc, cam, p) for p in _bbox_world(objects)]
        xs = [c.x for c in co]
        ys = [c.y for c in co]
        over = max(margin - min(xs), max(xs) - (1 - margin), margin - min(ys), max(ys) - (1 - margin), 0.0)
        if over > 0:
            bad.append(int(f))
        if over > worst_val:
            worst_val = over
            worst = (int(f), round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3))
    sc.frame_set(sc.frame_start)
    return {"worst": worst, "overshoot": round(worst_val, 3), "bad": bad}


def fit_rig_scale(rig, cam, objects, key_frame, check_frames, margin=0.05, step=0.03, max_iter=20):
    """Back a dolly rig off (scale up its key at key_frame) until `objects` stay in frame.

    Assumes the camera is parented to `rig` and the move is keyed on rig.scale.
    Returns the final scale and the frame report.
    """
    rep = frame_report(cam, objects, check_frames, margin)
    it = 0
    while rep["bad"] and it < max_iter:
        bpy.context.scene.frame_set(key_frame)
        s = rig.scale[0] * (1 + step)
        rig.scale = (s, s, s)
        key(rig, "scale", key_frame, interp="BEZIER")
        rep = frame_report(cam, objects, check_frames, margin)
        it += 1
    bpy.context.scene.frame_set(key_frame)
    return rig.scale[0], rep
