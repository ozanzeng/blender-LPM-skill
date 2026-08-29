"""
render_unlit_views.py - run INSIDE Blender. Renders orthographic views with the mesh's base colour as pure
EMISSION (no lights, no tonemapping, transparent film) so a comparison against the reference measures texture +
geometry only, not our studio lighting.

  bl.py --script render_unlit_views.py -- --input asset.blend --out <dir> [--size 900] [--views front,right,back,left]
"""
import argparse, math, os, sys
import bpy
from mathutils import Vector

DIRS = {"front": (0, -1), "back": (0, 1), "right": (1, 1), "left": (1, -1)}


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=900); p.add_argument("--views", default="front,right,back,left")
    p.add_argument("--margin", type=float, default=1.02)
    p.add_argument("--elev", type=float, default=0.0)
    return p.parse_args(argv)


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.input))
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type in ("LIGHT", "CAMERA") or o.name.endswith("_COL") or o.get("lpm_collision"):
            bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    lo = Vector((min(min((o.matrix_world @ v.co)[i] for o in meshes for v in o.data.vertices) for i in [0]) if False else 0, 0, 0))
    xs = [(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector((min(p.x for p in xs), min(p.y for p in xs), min(p.z for p in xs)))
    hi = Vector((max(p.x for p in xs), max(p.y for p in xs), max(p.z for p in xs)))
    ctr = (lo + hi) / 2
    # replace every material by an emission of its base colour texture / colour
    for m in bpy.data.materials:
        if not m.use_nodes: m.use_nodes = True
        nt = m.node_tree; bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        src_img = None; src_col = (0.8, 0.8, 0.8, 1)
        if bsdf:
            inp = bsdf.inputs["Base Color"]
            if inp.is_linked:
                n = inp.links[0].from_node
                if n.type == "TEX_IMAGE": src_img = n.image
            else:
                src_col = tuple(inp.default_value)
        for n in list(nt.nodes): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
        if src_img is not None:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = src_img; t.interpolation = "Closest" if src_img.size[0] <= 256 else "Linear"
            nt.links.new(t.outputs["Color"], em.inputs["Color"])
        else:
            em.inputs["Color"].default_value = src_col
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    world = bpy.data.worlds.new("W"); world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    sc.world = world
    sc.render.engine = "CYCLES"; sc.cycles.samples = 8; sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_x = sc.render.resolution_y = a.size
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    written = []
    for v in [x.strip() for x in a.views.split(",") if x.strip()]:
        ax, sgn = DIRS[v]
        h = Vector((0, 0, 0)); h[ax] = sgn
        e = math.radians(a.elev)
        d = (h * math.cos(e) + Vector((0, 0, 1)) * math.sin(e)).normalized()
        cam_d = bpy.data.cameras.new("C"); cam_d.type = "ORTHO"
        half = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) / 2
        cam_d.ortho_scale = 2 * half * a.margin
        cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam)
        cam.location = ctr + d * (half * 6)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam
        path = os.path.join(out, f"{v}.png"); sc.render.filepath = path
        bpy.ops.render.render(write_still=True); written.append(path)
        bpy.data.objects.remove(cam, do_unlink=True)
    print("##JSON##" + str({"out": out, "views": written}).replace("'", '"'))


main()
