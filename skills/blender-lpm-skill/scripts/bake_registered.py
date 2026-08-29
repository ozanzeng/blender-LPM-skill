"""
bake_registered.py - run INSIDE Blender (via bl.py). Projects the REGISTERED reference views onto a mesh using the
canonical world<->image mapping from frame.json (no per-view bbox fitting, so nothing slides) and bakes them into a
single atlas. Per face the view whose direction the face points at most is used; a fill colour covers faces that see
no view (undersides).

  bl.py --script bake_registered.py -- --input mesh.blend --frame frame.json --out <dir>/SM_Name [--size 2048] [--samples 4] [--device GPU] [--flat]
"""
import argparse, json, math, os, sys
import bpy, numpy as np
from mathutils import Vector

HDIR = {"front": Vector((0, -1, 0)), "back": Vector((0, 1, 0)), "right": Vector((1, 0, 0)), "left": Vector((-1, 0, 0))}


def basis(view, elev_deg):
    """Same basis as exact_hull.py: right = Z x h, d = h cos(e) + Z sin(e), up = d x right."""
    h = HDIR[view]; e = math.radians(elev_deg)
    r = Vector((0, 0, 1)).cross(h).normalized()
    d = (h * math.cos(e) + Vector((0, 0, 1)) * math.sin(e)).normalized()
    u = d.cross(r).normalized()
    return r, u, d


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="bake_registered")
    p.add_argument("--input", required=True); p.add_argument("--frame", required=True); p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=2048); p.add_argument("--samples", type=int, default=4)
    p.add_argument("--device", default="GPU", choices=["GPU", "CPU"]); p.add_argument("--margin", type=float, default=0.004)
    p.add_argument("--bake-margin", type=int, default=16)
    p.add_argument("--flat", action="store_true"); p.add_argument("--power", type=float, default=3.0, help="view-weight sharpness")
    p.add_argument("--no-bake", action="store_true", help="keep the live projection material instead of baking an atlas (upper bound test)")
    return p.parse_args(argv)


def mean_colour(path):
    img = bpy.data.images.load(path, check_existing=False); img.colorspace_settings.name = "sRGB"
    w, h = img.size; a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4); bpy.data.images.remove(img)
    fg = a[..., 3] > 0.5
    return a[..., :3][fg].mean(axis=0) if fg.any() else np.array([0.5, 0.5, 0.5])


def main():
    a = parse()
    fr = json.load(open(a.frame))
    fdir = os.path.dirname(os.path.abspath(a.frame))
    fr["views"] = {k: (v if os.path.isabs(v) else os.path.normpath(os.path.join(fdir, v))) for k, v in fr["views"].items()}
    for k, v in list(fr["views"].items()):
        if not os.path.exists(v):
            alt = os.path.abspath(os.path.join(os.getcwd(), os.path.basename(os.path.dirname(v)), os.path.basename(v)))
            if os.path.exists(alt): fr["views"][k] = alt
    S, y_base = fr["canvas"], fr["y_base"]
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    ob = next(o for o in bpy.data.objects if o.type == "MESH" and not o.name.endswith("_COL"))
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    me = ob.data
    order = [v for v in ("front", "right", "back", "left") if v in fr["views"]]
    fill = mean_colour(fr["views"]["front"])
    fill_lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in fill]
    # projection UVs from the tilt-aware mapping solved by exact_hull.py (frame.json)
    elev = fr.get("elev", 0.0); mp = fr["map"]
    bas = {v: basis(v, elev) for v in order}
    for v in order:
        r, u, _d = bas[v]; m = mp[v]; scale = m["scale_px_per_m"]
        layer = me.uv_layers.new(name=f"proj_{v}")
        for poly in me.polygons:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                col = S / 2 + (co.dot(r) - m["centre_r"]) * scale
                row = y_base - (co.dot(u) - m["u_min"]) * scale
                layer.data[li].uv = (col / S, 1.0 - row / S)
    bake_uv = me.uv_layers.new(name="UVMap_bake"); me.uv_layers.active = bake_uv
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=a.margin); bpy.ops.object.mode_set(mode="OBJECT")
    target = bpy.data.images.new("bake", a.size, a.size, alpha=False)
    # ONE material that blends every view by how much each face turns toward it:
    #   colour = sum_i w_i * C_i / sum_i w_i,  w_i = max(0, N . d_i)^k * alpha_i
    # Soft weights remove the seams and the stretching that a hard per-face choice produces on grazing surfaces.
    me.materials.clear()
    mat = bpy.data.materials.new("proj_blend"); mat.use_nodes = True; nt = mat.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sum_c = None; sum_w = None
    for v in order:
        _r, _u, d = bas[v]
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(fr["views"][v])
        tex.extension = "EXTEND"; tex.image.colorspace_settings.name = "sRGB"; tex.interpolation = "Cubic"
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = f"proj_{v}"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = (d.x, d.y, d.z)
        nt.links.new(geo.outputs["Normal"], dot.inputs[0])
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.inputs[1].default_value = 0.0
        nt.links.new(dot.outputs["Value"], mx.inputs[0])
        pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = a.power
        nt.links.new(mx.outputs["Value"], pw.inputs[0])
        wa = nt.nodes.new("ShaderNodeMath"); wa.operation = "MULTIPLY"
        nt.links.new(pw.outputs["Value"], wa.inputs[0]); nt.links.new(tex.outputs["Alpha"], wa.inputs[1])
        cw = nt.nodes.new("ShaderNodeVectorMath"); cw.operation = "SCALE"
        nt.links.new(tex.outputs["Color"], cw.inputs[0]); nt.links.new(wa.outputs["Value"], cw.inputs["Scale"])
        if sum_c is None:
            sum_c, sum_w = cw.outputs["Vector"], wa.outputs["Value"]
        else:
            addc = nt.nodes.new("ShaderNodeVectorMath"); addc.operation = "ADD"
            nt.links.new(sum_c, addc.inputs[0]); nt.links.new(cw.outputs["Vector"], addc.inputs[1]); sum_c = addc.outputs["Vector"]
            addw = nt.nodes.new("ShaderNodeMath"); addw.operation = "ADD"
            nt.links.new(sum_w, addw.inputs[0]); nt.links.new(wa.outputs["Value"], addw.inputs[1]); sum_w = addw.outputs["Value"]
    safe = nt.nodes.new("ShaderNodeMath"); safe.operation = "MAXIMUM"; safe.inputs[1].default_value = 1e-4
    nt.links.new(sum_w, safe.inputs[0])
    div = nt.nodes.new("ShaderNodeVectorMath"); div.operation = "DIVIDE"
    nt.links.new(sum_c, div.inputs[0])
    div_vec = nt.nodes.new("ShaderNodeCombineXYZ")
    for sock in ("X", "Y", "Z"):
        nt.links.new(safe.outputs["Value"], div_vec.inputs[sock])
    nt.links.new(div_vec.outputs["Vector"], div.inputs[1])
    # where no view sees the surface at all, fall back to the fill colour
    cover = nt.nodes.new("ShaderNodeMath"); cover.operation = "MULTIPLY"; cover.inputs[1].default_value = 12.0
    nt.links.new(sum_w, cover.inputs[0])
    clampn = nt.nodes.new("ShaderNodeClamp"); nt.links.new(cover.outputs["Value"], clampn.inputs["Value"])
    fin = nt.nodes.new("ShaderNodeMix"); fin.data_type = "RGBA"; fin.inputs[6].default_value = (*fill_lin, 1.0)
    nt.links.new(clampn.outputs["Result"], fin.inputs[0]); nt.links.new(div.outputs["Vector"], fin.inputs[7])
    nt.links.new(fin.outputs[2], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
    bn = nt.nodes.new("ShaderNodeTexImage"); bn.image = target; nt.nodes.active = bn
    me.materials.append(mat)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = a.samples; sc.cycles.device = a.device
    sc.render.bake.margin = a.bake_margin
    if a.no_bake:
        stem = os.path.abspath(a.out); os.makedirs(os.path.dirname(stem), exist_ok=True)
        for poly in me.polygons:
            if a.flat: poly.use_smooth = False
        bpy.ops.wm.save_as_mainfile(filepath=stem + ".blend")
        print("##JSON##" + json.dumps({"blend": stem + ".blend", "mode": "live-projection", "views": order}))
        return
    bpy.ops.object.bake(type="EMIT", use_clear=True)
    stem = os.path.abspath(a.out); os.makedirs(os.path.dirname(stem), exist_ok=True)
    target.filepath_raw = stem + "_BaseColor.png"; target.file_format = "PNG"; target.save()
    me.materials.clear()
    for nm in [l.name for l in me.uv_layers if l.name.startswith("proj_")]:
        me.uv_layers.remove(me.uv_layers[nm])
    me.uv_layers["UVMap_bake"].name = "UVMap"
    mat = bpy.data.materials.new(os.path.basename(stem)); mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(stem + "_BaseColor.png")
    b = mat.node_tree.nodes["Principled BSDF"]; mat.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    me.materials.append(mat)
    for poly in me.polygons:
        poly.material_index = 0
        if a.flat: poly.use_smooth = False
    bpy.ops.wm.save_as_mainfile(filepath=stem + ".blend")
    print("##JSON##" + json.dumps({"blend": stem + ".blend", "basecolor": stem + "_BaseColor.png", "views": order, "faces": len(me.polygons)}))


main()
