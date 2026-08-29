"""
wire_pbr_export.py - run INSIDE Blender. Wires BaseColor + MaskMap (R metallic, G occlusion, A smoothness) into the
material, adds a box collider, and exports .blend + Unity FBX with the textures beside it.

  bl.py --script wire_pbr_export.py -- --input mesh.blend --base tex/X_BaseColor.png --mask tex/X_MaskMap.png --out <dir>/SM_X [--flat] [--collider]
"""
import argparse, json, os, sys
import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--out", required=True)
    p.add_argument("--base", required=True); p.add_argument("--mask", default="")
    p.add_argument("--flat", action="store_true"); p.add_argument("--collider", action="store_true")
    return p.parse_args(argv)


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    ob = next(o for o in bpy.data.objects if o.type == "MESH" and not o.name.endswith("_COL"))
    me = ob.data
    me.materials.clear()
    mat = bpy.data.materials.new(ob.name); mat.use_nodes = True; nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = bpy.data.images.load(os.path.abspath(a.base))
    nt.links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    if a.mask:
        tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = bpy.data.images.load(os.path.abspath(a.mask))
        tm.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Red"], bsdf.inputs["Metallic"])
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(tm.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
    me.materials.append(mat)
    for poly in me.polygons:
        poly.material_index = 0
        if a.flat: poly.use_smooth = False
    extra = []
    if a.collider:
        vs = [v.co for v in me.vertices]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        verts = [(lo.x, lo.y, lo.z), (hi.x, lo.y, lo.z), (hi.x, hi.y, lo.z), (lo.x, hi.y, lo.z),
                 (lo.x, lo.y, hi.z), (hi.x, lo.y, hi.z), (hi.x, hi.y, hi.z), (lo.x, hi.y, hi.z)]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        cm = bpy.data.meshes.new(ob.name + "_COL"); cm.from_pydata(verts, [], faces); cm.update()
        col = bpy.data.objects.new(ob.name + "_COL", cm); bpy.context.scene.collection.objects.link(col)
        col.display_type = "WIRE"; col.hide_render = True; col.parent = ob; col["lpm_collision"] = True
        extra.append(col)
    stem = os.path.abspath(a.out); os.makedirs(os.path.dirname(stem), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    for e in extra: e.select_set(True)
    bpy.ops.export_scene.fbx(filepath=stem + ".fbx", use_selection=True, apply_scale_options="FBX_SCALE_NONE",
                             axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True, use_tspace=True,
                             mesh_smooth_type="FACE", object_types={"MESH"}, bake_anim=False, path_mode="COPY", embed_textures=False)
    bpy.ops.wm.save_as_mainfile(filepath=stem + ".blend")
    me.calc_loop_triangles()
    print("##JSON##" + json.dumps({"blend": stem + ".blend", "fbx": stem + ".fbx", "tris": len(me.loop_triangles),
                                   "dims": [round(c, 3) for c in ob.dimensions], "collider": bool(extra)}))


main()
