"""
beauty_render.py - run INSIDE Blender (via bl.py). Presentation render of an LPM asset: studio ground, three-sun
rig with soft shadows, grey-blue world, three-quarter camera framed on the object, EEVEE (or Cycles).

  bl.py --script beauty_render.py -- --input <asset.blend> --out <render.png> [--size 1536] [--engine EEVEE|CYCLES]
        [--azimuth -35] [--elevation 22] [--ground 1] [--samples 64]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="beauty_render")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=1536)
    p.add_argument("--aspect", type=float, default=0.75, help="height / width")
    p.add_argument("--engine", default="EEVEE", choices=["EEVEE", "CYCLES"])
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--azimuth", type=float, default=-35.0)
    p.add_argument("--elevation", type=float, default=22.0)
    p.add_argument("--ground", type=int, default=1)
    return p.parse_args(argv)


def bounds():
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
    for o in bpy.data.objects:
        if o.type != "MESH":
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
    lo, hi = bounds()
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    # world
    world = bpy.data.worlds.get("BR_World") or bpy.data.worlds.new("BR_World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.32, 0.36, 0.42, 1.0); bg.inputs[1].default_value = 0.8
    scene.world = world
    # ground
    if a.ground:
        bpy.ops.mesh.primitive_plane_add(size=radius * 40, location=(center.x, center.y, lo.z))
        ground = bpy.context.active_object; ground.name = "BR_Ground"
        m = bpy.data.materials.new("BR_Ground"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.42, 0.40, 0.37, 1); b.inputs["Roughness"].default_value = 0.95
        ground.data.materials.append(m)
    # lights: key / fill / rim suns with soft angle
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    for name, az, el, energy, angle, col in (("BR_Key", -55, 48, 4.0, 6, (1.0, 0.96, 0.9)), ("BR_Fill", 110, 28, 1.4, 25, (0.85, 0.9, 1.0)), ("BR_Rim", 25, 55, 2.0, 10, (1.0, 1.0, 1.0))):
        ld = bpy.data.lights.new(name, "SUN"); ld.energy = energy; ld.angle = math.radians(angle); ld.color = col
        ob = bpy.data.objects.new(name, ld); scene.collection.objects.link(ob)
        ob.rotation_euler = (-d(az, el)).to_track_quat("-Z", "Y").to_euler()
    # camera
    cam_d = bpy.data.cameras.new("BR_Cam"); cam_d.lens = 45
    cam = bpy.data.objects.new("BR_Cam", cam_d); scene.collection.objects.link(cam)
    fov = 2 * math.atan(cam_d.sensor_width / (2 * cam_d.lens))
    dist = radius * 1.25 / math.sin(fov / 2)
    look = Vector((center.x, center.y, center.y * 0 + lo.z + (hi.z - lo.z) * 0.45))
    cam.location = look + d(a.azimuth, a.elevation) * dist
    cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    # render settings
    for e in (["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"] if a.engine == "EEVEE" else ["CYCLES"]):
        try:
            scene.render.engine = e; break
        except TypeError:
            continue
    if scene.render.engine.startswith("BLENDER_EEVEE"):
        scene.eevee.taa_render_samples = a.samples
        for attr, val in (("use_shadows", True), ("use_gtao", True), ("use_raytracing", False)):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, val)
    else:
        scene.cycles.samples = a.samples; scene.cycles.use_denoising = True
    scene.render.resolution_x = a.size; scene.render.resolution_y = int(a.size * a.aspect); scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    scene.view_settings.look = "AgX - Medium High Contrast" if scene.view_settings.view_transform == "AgX" else "None"
    scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGB"
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("##JSON##" + str({"out": out, "engine": scene.render.engine, "size": [scene.render.resolution_x, scene.render.resolution_y]}).replace("'", '"'))


main()
