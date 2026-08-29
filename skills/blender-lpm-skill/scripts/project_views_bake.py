"""
project_views_bake.py - run INSIDE Blender (via bl.py). FREE texturing: projects the four reference views
(front / left / back / right, orthographic) onto a mesh and bakes them into one texture on a fresh UV atlas.
Each face takes the view its normal faces most; projection UVs are computed from world coordinates and the
object's bounds (the reference views are assumed to frame the whole object, base at the bottom).

  bl.py --script project_views_bake.py -- --input model.blend --front f.png --left l.png --back b.png --right r.png --out <dir>/SM_Name [--size 2048] [--margin 0.03]

Writes <stem>.blend (+ <stem>_BaseColor.png) with a single material using the baked atlas. Top/bottom faces take the
nearest side view; seams between views are hidden by choosing per face, not per pixel.
"""
import argparse
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="project_views_bake")
    p.add_argument("--input", required=True); p.add_argument("--out", required=True)
    for v in ("front", "left", "back", "right"):
        p.add_argument(f"--{v}", default="")
    p.add_argument("--size", type=int, default=2048); p.add_argument("--margin", type=float, default=0.02)
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--device", default="GPU", choices=["GPU", "CPU"])
    p.add_argument("--fill", default="", help="fallback colour hex for background/edge pixels (default: mean foreground colour of the front view)")
    return p.parse_args(argv)


def masked_reference(path, out_path):
    """Write an RGBA copy with the light background removed (eroded 2 px so edge halos never reach the mesh) and
    return (bbox fractions x0,y0,x1,y1 from the top, mean foreground colour)."""
    img = bpy.data.images.load(path, check_existing=False); img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    if a[..., 3].min() < 0.5:
        fg = a[..., 3] > 0.5
    else:
        rgb = a[..., :3]; mx, mn = rgb.max(-1), rgb.min(-1)
        sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0); fg = ~((sat < 0.12) & (mx > 0.55))
    er = fg.copy()
    for _ in range(2):   # 4-neighbour erosion
        er = er & np.roll(er, 1, 0) & np.roll(er, -1, 0) & np.roll(er, 1, 1) & np.roll(er, -1, 1)
    mean = a[..., :3][er].mean(axis=0) if er.any() else np.array([0.5, 0.5, 0.5])
    a[..., 3] = er.astype(np.float32)
    out = bpy.data.images.new(os.path.basename(out_path), w, h, alpha=True); out.colorspace_settings.name = "Non-Color"
    out.pixels = a.ravel().tolist(); out.filepath_raw = out_path; out.file_format = "PNG"; out.save(); bpy.data.images.remove(out)
    ys, xs = np.where(fg)
    yt = (h - 1 - ys)   # rows from the top
    return (xs.min() / w, yt.min() / h, (xs.max() + 1) / w, (yt.max() + 1) / h), [float(c) for c in mean]


# view -> (horizontal world axis (sign, index), whether image x increases with +axis), plus the outward normal
VIEWS = {
    "front": {"normal": Vector((0, -1, 0)), "haxis": (0, +1)},   # camera at -y: image x = +x
    "back":  {"normal": Vector((0, 1, 0)),  "haxis": (0, -1)},   # camera at +y: image x = -x
    "left":  {"normal": Vector((-1, 0, 0)), "haxis": (1, -1)},   # camera at -x: image x = -y (front on the right)
    "right": {"normal": Vector((1, 0, 0)),  "haxis": (1, +1)},   # camera at +x: image x = +y (front on the left)
}


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    ob = next(o for o in bpy.data.objects if o.type == "MESH" and not o.get("lpm_collision") and not o.name.endswith("_COL"))
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    me = ob.data
    src = {v: os.path.abspath(getattr(a, v)) for v in VIEWS if getattr(a, v)}
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_proj_masks"); os.makedirs(tmpdir, exist_ok=True)
    views, bboxes, means = {}, {}, {}
    for v, pth in src.items():
        mp = os.path.join(tmpdir, f"{v}_rgba.png"); bboxes[v], means[v] = masked_reference(pth, mp); views[v] = mp
    if a.fill:
        hx = a.fill.lstrip("#"); fill = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    else:
        fill = means.get("front", list(means.values())[0])
    fill_lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in fill]
    lo = Vector((min(v.co.x for v in me.vertices), min(v.co.y for v in me.vertices), min(v.co.z for v in me.vertices)))
    hi = Vector((max(v.co.x for v in me.vertices), max(v.co.y for v in me.vertices), max(v.co.z for v in me.vertices)))
    # per-view projection UV layers
    for v in views:
        layer = me.uv_layers.new(name=f"proj_{v}")
        ax, sgn = VIEWS[v]["haxis"]
        extent = (hi[ax] - lo[ax]) or 1e-6
        x0, y0, x1, y1 = bboxes[v]
        for poly in me.polygons:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                u = (co[ax] - lo[ax]) / extent
                if sgn < 0: u = 1.0 - u
                w = (co.z - lo.z) / ((hi.z - lo.z) or 1e-6)
                layer.data[li].uv = (x0 + u * (x1 - x0), 1.0 - (y1 - w * (y1 - y0)))   # image v: 0 at bottom in Blender
    # per-face view choice (attribute) -> material index
    order = list(views)
    idx_attr = me.attributes.new("proj_view", "INT", "FACE")
    for poly in me.polygons:
        n = Vector((poly.normal.x, poly.normal.y, 0.0))      # choose by horizontal direction only (tops/bottoms take the nearest side)
        if n.length < 1e-6: n = Vector((0, -1, 0))
        best = max(order, key=lambda v: n.dot(VIEWS[v]["normal"]))
        idx_attr.data[poly.index].value = order.index(best)
    # bake target UV
    bake_uv = me.uv_layers.new(name="UVMap_bake"); me.uv_layers.active = bake_uv
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=a.margin); bpy.ops.object.mode_set(mode="OBJECT")
    target = bpy.data.images.new("bake", a.size, a.size, alpha=False); target.generated_color = (0.5, 0.5, 0.5, 1)
    # one material per view (emission of the projected image through its UV layer) + bake node
    me.materials.clear()
    for v in order:
        mat = bpy.data.materials.new(f"proj_{v}"); mat.use_nodes = True; nt = mat.node_tree
        for n in list(nt.nodes): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(views[v]); tex.extension = "EXTEND"; tex.image.colorspace_settings.name = "sRGB"
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = f"proj_{v}"
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[6].default_value = (*fill_lin, 1.0)
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"]); nt.links.new(tex.outputs["Alpha"], mix.inputs[0]); nt.links.new(tex.outputs["Color"], mix.inputs[7])
        nt.links.new(mix.outputs[2], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
        bake_node = nt.nodes.new("ShaderNodeTexImage"); bake_node.image = target; nt.nodes.active = bake_node
        me.materials.append(mat)
    for poly in me.polygons:
        poly.material_index = idx_attr.data[poly.index].value
    scene = bpy.context.scene; scene.render.engine = "CYCLES"; scene.cycles.samples = a.samples; scene.cycles.device = a.device
    scene.render.bake.use_selected_to_active = False; scene.render.bake.margin = 8
    bpy.ops.object.bake(type="EMIT", use_clear=True)
    stem = os.path.abspath(a.out); os.makedirs(os.path.dirname(stem), exist_ok=True)
    target.filepath_raw = stem + "_BaseColor.png"; target.file_format = "PNG"; target.save()
    # final: single material with the baked atlas on UVMap_bake, drop projection layers
    me.materials.clear()
    for lname in [l.name for l in me.uv_layers if l.name.startswith("proj_")]:
        me.uv_layers.remove(me.uv_layers[lname])
    me.uv_layers["UVMap_bake"].name = "UVMap"
    mat = bpy.data.materials.new(os.path.basename(stem)); mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(stem + "_BaseColor.png")
    bsdf = mat.node_tree.nodes["Principled BSDF"]; mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.85
    me.materials.append(mat)
    for poly in me.polygons: poly.material_index = 0
    me.attributes.remove(me.attributes["proj_view"])
    bpy.ops.wm.save_as_mainfile(filepath=stem + ".blend")
    print("##JSON##" + str({"blend": stem + ".blend", "basecolor": stem + "_BaseColor.png", "views": order, "size": a.size}).replace("'", '"'))


main()
