"""
render_views.py - run INSIDE Blender (via bl.py). Headless replacement for viewport
screenshots: renders front / side / back / three-quarter / top of the scene (or an imported
asset) with EEVEE, neutral lighting and transparent film, then writes a contact sheet.

  bl.py --script render_views.py -- --input <file> --out <dir> [--size 768] [--views front,side,back,quarter,top]
        [--ortho] [--engine EEVEE|CYCLES] [--keep-lights] [--no-sheet] [--yaw 0]

Outputs <dir>/<view>.png and <dir>/sheet.png (numpy-only, no PIL required).
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

VIEW_ANGLES = {            # (azimuth deg around Z from +X→+Y, elevation deg)
    "front": (-90.0, 8.0),    # camera on -Y looking toward +Y (Blender front view)
    "side": (0.0, 8.0),       # camera on +X
    "back": (90.0, 8.0),
    "quarter": (-45.0, 25.0),
    "top": (-90.0, 89.0),
}


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="render_views")
    p.add_argument("--input", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=768)
    p.add_argument("--views", default="front,side,back,quarter,top")
    p.add_argument("--ortho", action="store_true", help="orthographic cameras (best for reference overlays)")
    p.add_argument("--engine", default="EEVEE", choices=["EEVEE", "CYCLES", "WORKBENCH"])
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--keep-lights", action="store_true", help="keep scene lights/world instead of the neutral rig")
    p.add_argument("--no-sheet", action="store_true")
    p.add_argument("--yaw", type=float, default=0.0, help="extra rotation (deg) about Z applied to every camera")
    p.add_argument("--margin", type=float, default=1.15)
    p.add_argument("--quarter-elev", type=float, default=None, help="override the three-quarter view elevation (deg) to match a reference camera")
    p.add_argument("--quarter-az", type=float, default=None, help="override the three-quarter view azimuth (deg)")
    return p.parse_args(argv)


def load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=path)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=path)
        else:
            raise SystemExit(f"unsupported input: {path}")


def scene_bounds(depsgraph):
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for o in bpy.data.objects:
        if o.type != "MESH" or o.hide_render or o.get("lpm_collision") or o.name.endswith("_COL"):
            continue
        ev = o.evaluated_get(depsgraph)
        me = ev.to_mesh()
        mw = o.matrix_world
        for v in me.vertices:
            w = mw @ v.co
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
        ev.to_mesh_clear()
    if lo.x is math.inf:
        raise SystemExit("no renderable mesh objects")
    return lo, hi


def set_engine(scene, engine, samples):
    ids = {"EEVEE": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"], "CYCLES": ["CYCLES"], "WORKBENCH": ["BLENDER_WORKBENCH"]}[engine]
    for e in ids:
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    if scene.render.engine.startswith("BLENDER_EEVEE"):
        scene.eevee.taa_render_samples = samples
    elif scene.render.engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True


def neutral_rig(scene, center, radius):
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    world = bpy.data.worlds.get("RV_World") or bpy.data.worlds.new("RV_World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.5, 0.5, 0.5, 1.0)
        bg.inputs[1].default_value = 0.6
    scene.world = world
    for name, az, el, energy in (("RV_Key", -60, 45, 3.0), ("RV_Fill", 120, 25, 1.2), ("RV_Rim", 30, 60, 1.5)):
        data = bpy.data.lights.new(name, "SUN")
        data.energy = energy
        data.angle = math.radians(8)
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        direction = -dir_from_angles(az, el)
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        ob.location = center + dir_from_angles(az, el) * radius * 3


def dir_from_angles(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))


def make_camera(scene, name, center, radius, az, el, ortho, margin, aspect=1.0):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    d = dir_from_angles(az, el)
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 2 * radius * margin
        dist = radius * 4
    else:
        cam_data.type = "PERSP"
        cam_data.lens = 50
        fov = 2 * math.atan(cam_data.sensor_width / (2 * cam_data.lens))
        dist = radius * margin / math.sin(fov / 2)
    cam.location = center + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam_data.clip_start = max(dist - radius * 4, 0.01)
    cam_data.clip_end = dist + radius * 4
    return cam


def contact_sheet(paths, out, size):
    try:
        import numpy as np
    except ImportError:
        print("numpy missing, no sheet")
        return
    tiles = []
    for p in paths:
        im = bpy.data.images.load(p)
        w, h = im.size
        arr = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
        bpy.data.images.remove(im)
        rgb = arr[..., :3] * arr[..., 3:4] + 0.18 * (1 - arr[..., 3:4])  # composite on dark grey
        tiles.append(rgb)
    n = len(tiles)
    cols = min(n, 3)
    rows = math.ceil(n / cols)
    sheet = np.full((rows * size, cols * size, 3), 0.18, dtype=np.float32)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * size:(r + 1) * size, c * size:(c + 1) * size] = t[:size, :size]
    img = bpy.data.images.new("RV_Sheet", cols * size, rows * size, alpha=False)
    rgba = np.concatenate([sheet[::-1], np.ones((rows * size, cols * size, 1), dtype=np.float32)], axis=2)
    img.pixels = rgba.ravel().tolist()
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    print("sheet", out)


def main():
    a = parse()
    if a.input:
        load(os.path.abspath(a.input))
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.get("lpm_collision") or o.name.endswith("_COL"):
            o.hide_render = True
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo, hi = scene_bounds(depsgraph)
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    set_engine(scene, a.engine, a.samples)
    scene.render.resolution_x = scene.render.resolution_y = a.size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    if not a.keep_lights:
        neutral_rig(scene, center, radius)
    written = []
    for view in [v.strip() for v in a.views.split(",") if v.strip()]:
        az, el = VIEW_ANGLES[view]
        if view == "quarter":
            az = a.quarter_az if a.quarter_az is not None else az
            el = a.quarter_elev if a.quarter_elev is not None else el
        cam = make_camera(scene, f"RV_{view}", center, radius, az + a.yaw, el, a.ortho, a.margin)
        scene.camera = cam
        path = os.path.join(out, f"{view}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        written.append(path)
        print("view", view, path)
    if not a.no_sheet and written:
        contact_sheet(written, os.path.join(out, "sheet.png"), a.size)
    print("##JSON##" + str({"out": out, "views": written, "dims": [round(c, 4) for c in (hi - lo)], "center": [round(c, 4) for c in center]}).replace("'", '"'))


main()
