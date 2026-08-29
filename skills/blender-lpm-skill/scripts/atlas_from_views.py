"""
atlas_from_views.py - run INSIDE Blender. Builds the texture by PACKING the four registered reference views into a
2x2 atlas and pointing each face's UVs at its dominant view's quadrant. No baking, no resampling: the texels are the
reference pixels, 1:1. This is the highest-fidelity option when the deliverable must match the reference sheet.

  bl.py --script atlas_from_views.py -- --input mesh.blend --frame frame.json --out <dir>/SM_Name [--flat] [--half]

Writes <stem>.blend and <stem>_BaseColor.png (2*canvas square, or canvas square with --half).
"""
import argparse, json, math, os, sys
import bpy, numpy as np
from mathutils import Vector

HDIR = {"front": Vector((0, -1, 0)), "back": Vector((0, 1, 0)), "right": Vector((1, 0, 0)), "left": Vector((-1, 0, 0))}
QUAD = {"front": (0, 0), "right": (1, 0), "back": (0, 1), "left": (1, 1)}


def basis(view, elev_deg):
    h = HDIR[view]; e = math.radians(elev_deg)
    r = Vector((0, 0, 1)).cross(h).normalized()
    d = (h * math.cos(e) + Vector((0, 0, 1)) * math.sin(e)).normalized()
    u = d.cross(r).normalized()
    return r, u, d


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--frame", required=True); p.add_argument("--out", required=True)
    p.add_argument("--flat", action="store_true"); p.add_argument("--half", action="store_true", help="downscale the atlas by 2")
    return p.parse_args(argv)


def load_rgb(path, fill):
    img = bpy.data.images.load(path, check_existing=False); img.colorspace_settings.name = "sRGB"
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    rgb = a[..., :3].copy()
    m = a[..., 3] < 0.5
    rgb[m] = fill                                    # transparent pixels already carry bled colour; this is a safety net
    return rgb


def main():
    a = parse()
    fr = json.load(open(a.frame))
    fdir = os.path.dirname(os.path.abspath(a.frame))
    views = {k: (v if os.path.isabs(v) else os.path.join(fdir, v)) for k, v in fr["views"].items()}
    S = fr["canvas"]; y_base = fr["y_base"]; elev = fr.get("elev", 0.0); mp = fr["map"]
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    ob = next(o for o in bpy.data.objects if o.type == "MESH" and not o.name.endswith("_COL"))
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    me = ob.data
    order = [v for v in ("front", "right", "back", "left") if v in views]
    first = load_rgb(views[order[0]], np.array([0.5, 0.5, 0.5], np.float32))
    fill = first.reshape(-1, 3).mean(axis=0)
    atlas = np.zeros((2 * S, 2 * S, 3), np.float32)
    for v in order:
        qx, qy = QUAD[v]
        rgb = load_rgb(views[v], fill)               # rows: 0 = bottom (Blender pixel order)
        atlas[qy * S:(qy + 1) * S, qx * S:(qx + 1) * S] = rgb
    img = bpy.data.images.new(os.path.basename(a.out) + "_BaseColor", 2 * S, 2 * S, alpha=False)
    img.colorspace_settings.name = "sRGB"
    img.pixels = np.concatenate([atlas, np.ones((2 * S, 2 * S, 1), np.float32)], axis=2).ravel().tolist()
    if a.half:
        img.scale(S, S)
    bas = {v: basis(v, elev) for v in order}
    uv = me.uv_layers.new(name="UVMap_atlas")
    for poly in me.polygons:
        n = poly.normal
        v = max(order, key=lambda k: n.dot(bas[k][2]))
        r, u, _d = bas[v]; m = mp[v]; sc = m["scale_px_per_m"]; qx, qy = QUAD[v]
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = S / 2 + (co.dot(r) - m["centre_r"]) * sc
            row = y_base - (co.dot(u) - m["u_min"]) * sc
            uu = col / S; vv = 1.0 - row / S
            # inset by ~2 texels so bilinear filtering never reaches into the neighbouring quadrant (white seams)
            eps = 2.0 / S
            uu = min(max(uu, eps), 1.0 - eps); vv = min(max(vv, eps), 1.0 - eps)
            uv.data[li].uv = ((qx + uu) / 2.0, (qy + vv) / 2.0)
    for lay in [l.name for l in me.uv_layers if l.name != "UVMap_atlas"]:
        me.uv_layers.remove(me.uv_layers[lay])
    me.uv_layers["UVMap_atlas"].name = "UVMap"
    stem = os.path.abspath(a.out); os.makedirs(os.path.dirname(stem), exist_ok=True)
    img.filepath_raw = stem + "_BaseColor.png"; img.file_format = "PNG"; img.save()
    me.materials.clear()
    mat = bpy.data.materials.new(os.path.basename(stem)); mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(stem + "_BaseColor.png")
    b = mat.node_tree.nodes["Principled BSDF"]; mat.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    me.materials.append(mat)
    for poly in me.polygons:
        poly.material_index = 0
        if a.flat: poly.use_smooth = False
    bpy.ops.wm.save_as_mainfile(filepath=stem + ".blend")
    print("##JSON##" + json.dumps({"blend": stem + ".blend", "basecolor": stem + "_BaseColor.png", "atlas": [img.size[0], img.size[1]], "views": order}))


main()
