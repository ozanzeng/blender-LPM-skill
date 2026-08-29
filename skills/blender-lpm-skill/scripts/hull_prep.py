"""
hull_prep.py - run INSIDE Blender. Import a hull OBJ (metres, Z up, base z=0) and prepare it for baking:
optional smoothing, planar + collapse decimation to a budget, weld, normals, keeping the silhouette.

  bl.py --script hull_prep.py -- --obj hull.obj --budget 8000 --out <dir>/mesh.blend [--smooth 0] [--planar 4] [--name SM_X]
"""
import argparse, math, os, sys
import bpy


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--obj", default=""); p.add_argument("--npz", default="", help="hull.npz from exact_hull.py (no axis conversion)")
    p.add_argument("--out", required=True)
    p.add_argument("--budget", type=int, default=8000); p.add_argument("--smooth", type=int, default=0)
    p.add_argument("--planar", type=float, default=4.0); p.add_argument("--name", default="SM_Hull")
    p.add_argument("--weld", type=float, default=0.0015)
    return p.parse_args(argv)


def tris(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)


def main():
    a = parse()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if a.npz:
        import numpy as np
        d = np.load(a.npz)
        me = bpy.data.meshes.new(a.name)
        me.from_pydata([tuple(v) for v in d["verts"].tolist()], [], [tuple(f) for f in d["faces"].tolist()])
        me.update()
        ob = bpy.data.objects.new(a.name, me)
        bpy.context.scene.collection.objects.link(ob)
    else:
        bpy.ops.wm.obj_import(filepath=os.path.abspath(a.obj), forward_axis="NEGATIVE_Y", up_axis="Z")
        ob = bpy.context.selected_objects[0]; ob.name = a.name; ob.data.name = a.name
    for o in bpy.context.scene.objects: o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    print("hull tris", tris(ob))
    if a.weld:
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=a.weld); bpy.ops.object.mode_set(mode="OBJECT")
    if a.smooth:
        m = ob.modifiers.new("Smooth", "SMOOTH"); m.iterations = a.smooth; m.factor = 0.5
        bpy.ops.object.modifier_apply(modifier="Smooth")
    if a.planar:
        d = ob.modifiers.new("Planar", "DECIMATE"); d.decimate_type = "DISSOLVE"; d.angle_limit = math.radians(a.planar)
        bpy.ops.object.modifier_apply(modifier="Planar")
        print("after planar", tris(ob))
    if a.budget and tris(ob) > a.budget:
        d = ob.modifiers.new("Collapse", "DECIMATE"); d.decimate_type = "COLLAPSE"; d.ratio = a.budget / tris(ob); d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="Collapse")
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
    for p in ob.data.polygons: p.use_smooth = True
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("##JSON##" + str({"blend": out, "tris": tris(ob), "dims": [round(c, 3) for c in ob.dimensions]}).replace("'", '"'))


main()
