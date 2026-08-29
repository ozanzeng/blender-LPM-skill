"""
hull_to_lowpoly.py - run INSIDE Blender (via bl.py). Turns a visual-hull OBJ into a flat-shaded low-poly mesh:
smooth -> decimate planar -> decimate collapse to budget -> flat shade -> single palette colour -> optional place on a
point -> export .blend/.obj. Also reports tris.

  bl.py --script hull_to_lowpoly.py -- --obj lion.obj --budget 1500 --out _work/lion_lp.blend [--smooth 8] [--planar 8] [--color "#b9a97f"] [--at 0,0,2.32]
"""
import argparse
import os
import sys

import bpy


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="hull_to_lowpoly")
    p.add_argument("--obj", required=True); p.add_argument("--out", required=True)
    p.add_argument("--budget", type=int, default=1500)
    p.add_argument("--smooth", type=int, default=10, help="smooth iterations before decimation (removes voxel stairs)")
    p.add_argument("--planar", type=float, default=6.0, help="planar decimate angle (deg)")
    p.add_argument("--color", default="#b9a97f")
    p.add_argument("--at", default="0,0,0")
    p.add_argument("--name", default="SM_Hull")
    return p.parse_args(argv)


def tris(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)


def main():
    a = parse()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=os.path.abspath(a.obj), forward_axis="NEGATIVE_Y", up_axis="Z")   # identity: the file is already in Blender axes
    ob = bpy.context.selected_objects[0]; ob.name = a.name; ob.data.name = a.name
    bpy.context.view_layer.objects.active = ob
    print("hull tris", tris(ob))
    m = ob.modifiers.new("Smooth", "SMOOTH"); m.iterations = a.smooth; m.factor = 0.8
    bpy.ops.object.modifier_apply(modifier="Smooth")
    d1 = ob.modifiers.new("Planar", "DECIMATE"); d1.decimate_type = "DISSOLVE"; d1.angle_limit = __import__("math").radians(a.planar)
    bpy.ops.object.modifier_apply(modifier="Planar")
    print("after planar", tris(ob))
    if tris(ob) > a.budget:
        d2 = ob.modifiers.new("Collapse", "DECIMATE"); d2.decimate_type = "COLLAPSE"; d2.ratio = a.budget / tris(ob)
        bpy.ops.object.modifier_apply(modifier="Collapse")
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.002); bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in ob.data.polygons: p.use_smooth = False
    # palette-style single colour material
    mat = bpy.data.materials.new(a.name); mat.use_nodes = True
    h = a.color.lstrip("#"); rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*lin, 1); mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    ob.data.materials.append(mat)
    x, y, z = [float(v) for v in a.at.split(",")]
    lo = min(v.co.z for v in ob.data.vertices); ob.location = (x, y, z - lo)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    bpy.ops.wm.obj_export(filepath=out[:-6] + ".obj", forward_axis="NEGATIVE_Y", up_axis="Z", export_selected_objects=False, export_materials=False)   # identity
    print("##JSON##" + str({"blend": out, "tris": tris(ob), "budget": a.budget, "dims": [round(c, 3) for c in ob.dimensions]}).replace("'", '"'))


main()
