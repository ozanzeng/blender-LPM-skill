"""
turntable.py - run INSIDE Blender (via bl.py). 360-degree turntable of an asset: MP4 (H.264) + an 8-frame
contact sheet, studio ground and three-sun rig, EEVEE by default.

  bl.py --script turntable.py -- --input <asset.blend> --out <dir> [--frames 48] [--size 1024] [--fps 24] [--engine EEVEE|CYCLES] [--elevation 18]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="turntable")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--frames", type=int, default=48)
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--engine", default="EEVEE", choices=["EEVEE", "CYCLES"])
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--elevation", type=float, default=18.0)
    p.add_argument("--sheet-frames", type=int, default=8)
    return p.parse_args(argv)


def bounds():
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
    for o in bpy.data.objects:
        if o.type != "MESH" or o.get("lpm_collision"):
            continue
        me = o.evaluated_get(dg).to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        o.evaluated_get(dg).to_mesh_clear()
    return lo, hi


def d(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.get("lpm_collision"):
            o.hide_render = True
    lo, hi = bounds()
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    world = bpy.data.worlds.get("TT_World") or bpy.data.worlds.new("TT_World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.32, 0.36, 0.42, 1.0); bg.inputs[1].default_value = 0.8
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=radius * 400, location=(center.x, center.y, lo.z))
    ground = bpy.context.active_object; ground.name = "TT_Ground"
    gm = bpy.data.materials.new("TT_Ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.40, 0.37, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(gm)
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    for name, az, el, energy, angle in (("TT_Key", -55, 48, 4.0, 6), ("TT_Fill", 110, 28, 1.4, 25), ("TT_Rim", 25, 55, 2.0, 10)):
        ld = bpy.data.lights.new(name, "SUN"); ld.energy = energy; ld.angle = math.radians(angle)
        ob = bpy.data.objects.new(name, ld); scene.collection.objects.link(ob)
        ob.rotation_euler = (-d(az, el)).to_track_quat("-Z", "Y").to_euler()
    # camera on a pivot empty that spins 360 degrees
    pivot = bpy.data.objects.new("TT_Pivot", None); scene.collection.objects.link(pivot)
    pivot.location = Vector((center.x, center.y, lo.z + (hi.z - lo.z) * 0.45))
    cam_d = bpy.data.cameras.new("TT_Cam"); cam_d.lens = 45
    cam = bpy.data.objects.new("TT_Cam", cam_d); scene.collection.objects.link(cam)
    fov = 2 * math.atan(cam_d.sensor_width / (2 * cam_d.lens))
    dist = radius * 1.3 / math.sin(fov / 2)
    cam.parent = pivot
    cam.location = d(-35, a.elevation) * dist
    cam.rotation_euler = (-cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.frame_start, scene.frame_end = 1, a.frames
    pivot.rotation_euler = (0, 0, 0); pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler = (0, 0, math.radians(360 * (a.frames) / a.frames)); pivot.keyframe_insert("rotation_euler", frame=a.frames + 1)
    for fc in pivot.animation_data.action.fcurves if hasattr(pivot.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    try:  # Blender 4.4+ layered actions
        for layer in pivot.animation_data.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags(pivot.animation_data.action.slots[0]) if hasattr(strip, "channelbags") else []:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"
    except Exception:
        pass
    for e in (["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"] if a.engine == "EEVEE" else ["CYCLES"]):
        try:
            scene.render.engine = e; break
        except TypeError:
            continue
    if scene.render.engine.startswith("BLENDER_EEVEE"):
        scene.eevee.taa_render_samples = a.samples
        for attr in ("use_shadows", "use_gtao"):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, True)
    else:
        scene.cycles.samples = a.samples; scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = a.size; scene.render.resolution_percentage = 100
    scene.render.fps = a.fps; scene.render.film_transparent = False
    if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items]:
        scene.view_settings.view_transform = "AgX"
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    # stills for the sheet
    stills = []
    scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGB"
    for i in range(a.sheet_frames):
        f = 1 + int(round(i * a.frames / a.sheet_frames))
        scene.frame_set(f)
        path = os.path.join(out, f"tt_{i:02d}.png"); scene.render.filepath = path
        bpy.ops.render.render(write_still=True); stills.append(path)
    try:
        import numpy as np
        tiles = []
        for pth in stills:
            im = bpy.data.images.load(pth); w, h = im.size
            tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1][..., :3]); bpy.data.images.remove(im)
        cols = 4; rows = math.ceil(len(tiles) / cols); s = a.size
        sheet = np.zeros((rows * s, cols * s, 3), dtype=np.float32)
        for i, t in enumerate(tiles):
            r, c = divmod(i, cols); sheet[r * s:(r + 1) * s, c * s:(c + 1) * s] = t[:s, :s]
        img = bpy.data.images.new("TT_Sheet", cols * s, rows * s, alpha=False)
        img.pixels = np.concatenate([sheet[::-1], np.ones((rows * s, cols * s, 1), np.float32)], axis=2).ravel().tolist()
        img.filepath_raw = os.path.join(out, "turntable_sheet.png"); img.file_format = "PNG"; img.save()
    except Exception as exc:
        print("sheet failed:", exc)
    # video: Blender 5.x selects video output through image_settings.media_type; 4.x through file_format="FFMPEG"
    video_ok = True
    try:
        if hasattr(scene.render.image_settings, "media_type"):
            scene.render.image_settings.media_type = "VIDEO"
        else:
            scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"; scene.render.ffmpeg.codec = "H264"; scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    except Exception as exc:
        print("video output not available, keeping PNG frames:", exc)
        video_ok = False
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = os.path.join(out, "frames", "f_")
    if video_ok:
        scene.render.filepath = os.path.join(out, "turntable")
    scene.frame_set(1)
    bpy.ops.render.render(animation=True)
    mp4 = next((os.path.join(out, f) for f in os.listdir(out) if f.startswith("turntable") and f.endswith(".mp4")), "")
    print("##JSON##" + str({"out": out, "mp4": mp4, "sheet": os.path.join(out, "turntable_sheet.png"), "frames": a.frames, "engine": scene.render.engine}).replace("'", '"'))


main()
