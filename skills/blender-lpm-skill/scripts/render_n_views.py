"""
render_n_views.py - run INSIDE Blender. Renders N orthographic silhouette views around an object at a fixed
elevation, with a KNOWN camera for each (written to views.json), so a hull can be carved from them exactly.

  bl.py --script render_n_views.py -- --input asset.blend --out <dir> --n 8 [--elev 3] [--size 1024] [--start 0]
"""
import argparse, json, math, os, sys
import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=8); p.add_argument("--elev", type=float, default=3.0)
    p.add_argument("--size", type=int, default=1024); p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--pad", type=float, default=0.04)
    return p.parse_args(argv)


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type in ("CAMERA",) or o.name.endswith("_COL") or o.get("lpm_collision"):
            bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    pts = [(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (lo + hi) / 2; radius = max((p - ctr).length for p in pts)
    height = hi.z - lo.z
    sc.render.engine = "CYCLES"; sc.cycles.samples = 2; sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_x = sc.render.resolution_y = a.size
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    ortho = 2 * radius * 1.05
    info = {"n": a.n, "elev": a.elev, "size": a.size, "ortho_scale": ortho, "centre": [ctr.x, ctr.y, ctr.z],
            "height_m": height, "base_z": lo.z, "views": []}
    for i in range(a.n):
        az = a.start + 360.0 * i / a.n
        e, z = math.radians(a.elev), math.radians(az)
        d = Vector((math.cos(e) * math.sin(z), -math.cos(e) * math.cos(z), math.sin(e)))
        cam_d = bpy.data.cameras.new("C"); cam_d.type = "ORTHO"; cam_d.ortho_scale = ortho
        cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam)
        cam.location = ctr + d * (radius * 6); cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam
        path = os.path.join(out, f"v{i:02d}.png"); sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
        info["views"].append({"file": path, "az": az, "elev": a.elev})
    json.dump(info, open(os.path.join(out, "views.json"), "w"), indent=2)
    print("##JSON##" + json.dumps({"out": out, "n": a.n, "height_m": round(height, 4)}))


main()
