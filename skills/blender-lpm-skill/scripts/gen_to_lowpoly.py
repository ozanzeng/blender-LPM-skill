"""
gen_to_lowpoly.py - run INSIDE Blender (via bl.py). Post-process a generated GLB (Hunyuan3D etc.): import, orient
(front = -Y), scale to a real height, base on z=0, merge doubles, optional decimate-to-budget that keeps UVs and the
generator's textures, flat or smooth shading, unpack textures, export .blend + .fbx (+ textures folder).

  bl.py --script gen_to_lowpoly.py -- --glb model.glb --height 3.9 --out <dir>/SM_Name [--budget 6000] [--flat] [--yaw 0] [--name SM_Name]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="gen_to_lowpoly")
    p.add_argument("--glb", required=True); p.add_argument("--out", required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--budget", type=int, default=0, help="target triangles (0 = keep)")
    p.add_argument("--flat", action="store_true")
    p.add_argument("--yaw", type=float, default=0.0, help="rotate about Z so the front faces -Y")
    p.add_argument("--name", default="SM_Generated")
    return p.parse_args(argv)


def tris(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)


def main():
    a = parse()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(a.glb))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object; ob.name = a.name; ob.data.name = a.name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print("imported tris", tris(ob), "dims", [round(c, 3) for c in ob.dimensions])
    if a.yaw:
        ob.data.transform(Matrix.Rotation(math.radians(a.yaw), 4, "Z"))
    # scale to height, centre x/y, base on z = 0
    zs = [v.co.z for v in ob.data.vertices]; s = a.height / (max(zs) - min(zs))
    ob.data.transform(Matrix.Scale(s, 4))
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]; zs = [v.co.z for v in ob.data.vertices]
    ob.data.transform(Matrix.Translation(Vector((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs)))))
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.remove_doubles(threshold=0.0005); bpy.ops.object.mode_set(mode="OBJECT")
    if a.budget and tris(ob) > a.budget:
        d = ob.modifiers.new("Collapse", "DECIMATE"); d.decimate_type = "COLLAPSE"; d.ratio = a.budget / tris(ob); d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="Collapse")
    for p in ob.data.polygons: p.use_smooth = not a.flat
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    tex_dir = os.path.join(os.path.dirname(out), "tex"); os.makedirs(tex_dir, exist_ok=True)
    textures = []
    for img in bpy.data.images:
        if img.size[0] == 0: continue
        img.filepath_raw = os.path.join(tex_dir, f"{a.name}_{img.name.replace('.', '_')}.png"); img.file_format = "PNG"
        try:
            img.save(); textures.append(img.filepath_raw)
        except Exception as exc:
            print("texture save failed", img.name, exc)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=out + ".fbx", use_selection=True, apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True, use_tspace=True, mesh_smooth_type="FACE", object_types={"MESH"}, bake_anim=False, path_mode="COPY", embed_textures=False)
    bpy.ops.wm.save_as_mainfile(filepath=out + ".blend", relative_remap=True)
    print("##JSON##" + str({"blend": out + ".blend", "fbx": out + ".fbx", "tris": tris(ob), "dims": [round(c, 3) for c in ob.dimensions], "materials": [m.name for m in ob.data.materials], "textures": textures}).replace("'", '"'))


main()
