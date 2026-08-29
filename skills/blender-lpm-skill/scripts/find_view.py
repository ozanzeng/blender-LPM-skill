"""
find_view.py - run INSIDE Blender. Finds which camera a reference image was rendered from, by sweeping azimuth /
elevation (and orthographic vs perspective) and scoring the silhouette against the reference. Use it to evaluate a
model from a view it was NOT built from - the only honest test of a reconstruction.

  bl.py --script find_view.py -- --input asset.blend --ref concept.png --out <dir> [--az -80:80:10] [--el 0:40:5] [--persp] [--size 512] [--final 1024]
"""
import argparse, json, math, os, sys
import bpy, numpy as np
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--ref", required=True); p.add_argument("--out", required=True)
    p.add_argument("--az", default="-80:80:10"); p.add_argument("--el", default="0:40:5")
    p.add_argument("--size", type=int, default=384); p.add_argument("--final", type=int, default=1024)
    p.add_argument("--persp", action="store_true"); p.add_argument("--lit", action="store_true")
    return p.parse_args(argv)


def ref_mask(path):
    img = bpy.data.images.load(path, check_existing=False); img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    if a[..., 3].min() < 0.5:
        return a[..., 3] > 0.5
    rgb = a[..., :3]; mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return ~((sat < 0.12) & (mx > 0.55))


def crop_norm(m, H, W):
    """Crop to the object and resample to H x W with nearest neighbour (numpy only - Blender has no PIL)."""
    ys, xs = np.where(m)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    yi = (np.arange(H) * m.shape[0] // H).clip(0, m.shape[0] - 1)
    xi = (np.arange(W) * m.shape[1] // W).clip(0, m.shape[1] - 1)
    return m[np.ix_(yi, xi)]


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type == "CAMERA" or o.name.endswith("_COL") or o.get("lpm_collision"):
            bpy.data.objects.remove(o, do_unlink=True)
    if not a.lit:
        for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
            bpy.data.objects.remove(o, do_unlink=True)
        for m in bpy.data.materials:
            if not m.use_nodes: m.use_nodes = True
            nt = m.node_tree; b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            img, col = None, (0.8, 0.8, 0.8, 1)
            if b:
                inp = b.inputs["Base Color"]
                if inp.is_linked and inp.links[0].from_node.type == "TEX_IMAGE": img = inp.links[0].from_node.image
                elif not inp.is_linked: col = tuple(inp.default_value)
            for n in list(nt.nodes): nt.nodes.remove(n)
            out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
            if img is not None:
                t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; nt.links.new(t.outputs["Color"], em.inputs["Color"])
            else:
                em.inputs["Color"].default_value = col
            nt.links.new(em.outputs[0], out.inputs["Surface"])
        w = bpy.data.worlds.new("W"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
        sc.world = w; sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    pts = [(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (lo + hi) / 2; radius = max((p - ctr).length for p in pts)
    sc.render.engine = "CYCLES"; sc.cycles.samples = 4; sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    ref = ref_mask(os.path.abspath(a.ref))
    RH, RW = 256, 256
    refn = crop_norm(ref, RH, RW)
    def render(az, el, size, path):
        sc.render.resolution_x = sc.render.resolution_y = size
        cam_d = bpy.data.cameras.new("C")
        if a.persp:
            cam_d.type = "PERSP"; cam_d.lens = 85
        else:
            cam_d.type = "ORTHO"; cam_d.ortho_scale = 2 * radius * 0.82
        cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam)
        e, z = math.radians(el), math.radians(az)
        d = Vector((math.cos(e) * math.sin(z), -math.cos(e) * math.cos(z), math.sin(e)))
        cam.location = ctr + d * (radius * 6); cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam; sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
        return path
    def score(path):
        m = ref_mask(path)
        if not m.any(): return 0.0
        mn = crop_norm(m, RH, RW)
        return float((refn & mn).sum() / max((refn | mn).sum(), 1))
    def rng(spec):
        lo_, hi_, st = [float(x) for x in spec.split(":")]
        return list(np.arange(lo_, hi_ + 1e-6, st))
    best, rows = None, []
    tmp = os.path.join(out, "_probe.png")
    for az in rng(a.az):
        for el in rng(a.el):
            s = score(render(az, el, a.size, tmp))
            rows.append({"az": az, "el": el, "iou": round(s, 4)})
            if best is None or s > best["iou"]:
                best = {"az": az, "el": el, "iou": round(s, 4)}
    # refine around the best
    for az in np.arange(best["az"] - 6, best["az"] + 6.1, 3):
        for el in np.arange(best["el"] - 4, best["el"] + 4.1, 2):
            s = score(render(float(az), float(el), a.size, tmp))
            if s > best["iou"]:
                best = {"az": float(az), "el": float(el), "iou": round(s, 4)}
    final = render(best["az"], best["el"], a.final, os.path.join(out, "best.png"))
    json.dump({"best": best, "grid": rows}, open(os.path.join(out, "view.json"), "w"), indent=2)
    print("##JSON##" + json.dumps({"best": best, "render": final}))


main()
