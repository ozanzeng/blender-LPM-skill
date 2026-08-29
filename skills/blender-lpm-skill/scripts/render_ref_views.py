"""
render_ref_views.py - run INSIDE Blender. Renders the mesh from EXACTLY the reference cameras described in
frame.json (same elevation, same orthographic scale and framing), unlit by default, so a pixel comparison against
the registered reference is meaningful.

  bl.py --script render_ref_views.py -- --input asset.blend --frame frame.json --out <dir> [--lit] [--samples 16]
"""
import argparse, json, math, os, sys
import bpy
from mathutils import Vector

HDIR = {"front": Vector((0, -1, 0)), "back": Vector((0, 1, 0)), "right": Vector((1, 0, 0)), "left": Vector((-1, 0, 0))}


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
    p.add_argument("--lit", action="store_true"); p.add_argument("--samples", type=int, default=8)
    p.add_argument("--keep-materials", action="store_true", help="do not rebuild materials as emission (for live-projection blends)")
    return p.parse_args(argv)


def main():
    a = parse()
    fr = json.load(open(a.frame))
    S, y_base, inner = fr["canvas"], fr["y_base"], fr["inner_px"]
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type in ("CAMERA",) or o.name.endswith("_COL") or o.get("lpm_collision"):
            bpy.data.objects.remove(o, do_unlink=True)
    if not a.lit:
        for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
            bpy.data.objects.remove(o, do_unlink=True)
        for m in ([] if a.keep_materials else bpy.data.materials):
            if not m.use_nodes: m.use_nodes = True
            nt = m.node_tree; b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            img, col = None, (0.8, 0.8, 0.8, 1)
            if b:
                inp = b.inputs["Base Color"]
                if inp.is_linked and inp.links[0].from_node.type == "TEX_IMAGE":
                    img = inp.links[0].from_node.image
                elif not inp.is_linked:
                    col = tuple(inp.default_value)
            for n in list(nt.nodes): nt.nodes.remove(n)
            out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
            if img is not None:
                t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
                nt.links.new(t.outputs["Color"], em.inputs["Color"])
            else:
                em.inputs["Color"].default_value = col
            nt.links.new(em.outputs[0], out.inputs["Surface"])
        w = bpy.data.worlds.new("W"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
        sc.world = w
        sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    pts = [(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    ctr = sum(pts, Vector((0, 0, 0))) / len(pts)
    radius = max((p - ctr).length for p in pts)
    sc.render.engine = "CYCLES"; sc.cycles.samples = a.samples; sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_x = sc.render.resolution_y = S
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    written = {}
    for v, m in fr["map"].items():
        r, u, d = basis(v, fr.get("elev", 0.0))
        scale = m["scale_px_per_m"]                       # px per metre in this view
        cam_d = bpy.data.cameras.new("C"); cam_d.type = "ORTHO"
        cam_d.ortho_scale = S / scale                     # the canvas is exactly S px wide at this scale
        cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam)
        # camera looks along -d; place it so the registered framing is reproduced:
        # image centre is at (centre_r, u_centre) where u_centre corresponds to canvas row S/2
        u_at_canvas_centre = m["u_min"] + (y_base - S / 2) / scale
        target = Vector((0, 0, 0)) + r * m["centre_r"] + u * u_at_canvas_centre
        # keep the component along d free (orthographic): push the camera outside the object
        cam.location = target + d * (radius * 4)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam
        path = os.path.join(out, f"{v}.png"); sc.render.filepath = path
        bpy.ops.render.render(write_still=True); written[v] = path
        bpy.data.objects.remove(cam, do_unlink=True)
    print("##JSON##" + json.dumps({"out": out, "views": written}))


main()
