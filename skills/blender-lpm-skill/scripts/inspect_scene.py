"""
inspect_scene.py - run INSIDE Blender (via bl.py). Deterministic metrics for the current
scene or an imported asset; the headless equivalent of get_scene_info + validation.

  bl.py --script inspect_scene.py -- --input <file.blend|.glb|.gltf|.fbx|.obj> [--out metrics.json] [--per-object]

Reports per mesh object: evaluated vertices/faces/triangles, dimensions, world bounds,
transform state, loose parts, non-manifold/boundary edges, degenerate faces, negative scale,
UV layers, materials (and empty slots), custom normals, armature modifiers; plus armatures,
images (size, packed), scene totals, and a list of gate failures.
"""
import argparse
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="inspect_scene")
    p.add_argument("--input", default="", help="file to open/import; empty = current scene")
    p.add_argument("--out", default="", help="write JSON here")
    p.add_argument("--per-object", action="store_true", help="print per-object rows")
    p.add_argument("--degenerate-area", type=float, default=1e-9)
    return p.parse_args(argv)


def load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=path)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=path)
        else:
            raise SystemExit(f"unsupported input: {path}")


def mesh_metrics(obj, depsgraph, degenerate_area):
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        degenerate = sum(1 for f in bm.faces if f.calc_area() <= degenerate_area)
        loose_verts = sum(1 for v in bm.verts if not v.link_edges)
        # connected components (loose parts)
        seen = set()
        parts = 0
        for v in bm.verts:
            if v.index in seen:
                continue
            parts += 1
            stack = [v]
            seen.add(v.index)
            while stack:
                cur = stack.pop()
                for e in cur.link_edges:
                    o = e.other_vert(cur)
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
        bm.free()
        mw = obj.matrix_world
        pts = [mw @ v.co for v in me.vertices]
        if pts:
            lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
            hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        else:
            lo = hi = Vector((0, 0, 0))
        smooth = sum(1 for p in me.polygons if p.use_smooth)
        data = {
            "name": obj.name,
            "mesh": me.name if hasattr(me, "name") else obj.data.name,
            "verts": len(me.vertices),
            "edges": len(me.edges),
            "faces": len(me.polygons),
            "tris": tris,
            "smooth_faces_pct": round(100.0 * smooth / len(me.polygons), 1) if me.polygons else 0.0,
            "dims_world": [round(hi[i] - lo[i], 4) for i in range(3)],
            "bounds_world": {"min": [round(c, 4) for c in lo], "max": [round(c, 4) for c in hi]},
            "location": [round(c, 4) for c in obj.location],
            "rotation_deg": [round(math.degrees(c), 2) for c in obj.rotation_euler],
            "scale": [round(c, 4) for c in obj.scale],
            "transforms_applied": all(abs(c) < 1e-6 for c in obj.location) and all(abs(c) < 1e-6 for c in obj.rotation_euler) and all(abs(c - 1) < 1e-6 for c in obj.scale),
            "negative_scale": any(c < 0 for c in obj.scale),
            "loose_parts": parts,
            "loose_verts": loose_verts,
            "non_manifold_edges": non_manifold,
            "boundary_edges": boundary,
            "degenerate_faces": degenerate,
            "uv_layers": [uv.name for uv in obj.data.uv_layers],
            "has_custom_normals": bool(getattr(obj.data, "has_custom_normals", False)),
            "materials": [s.material.name if s.material else None for s in obj.material_slots],
            "empty_material_slots": sum(1 for s in obj.material_slots if s.material is None),
            "modifiers": [f"{m.type}:{m.name}" for m in obj.modifiers],
            "armature": next((m.object.name for m in obj.modifiers if m.type == "ARMATURE" and m.object), None),
            "vertex_groups": len(obj.vertex_groups),
            "parent": obj.parent.name if obj.parent else None,
            "collections": [c.name for c in obj.users_collection],
        }
    finally:
        ev.to_mesh_clear()
    return data


def main():
    a = parse()
    if a.input:
        load(os.path.abspath(a.input))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    rows = [mesh_metrics(o, depsgraph, a.degenerate_area) for o in meshes]
    armatures = [{"name": o.name, "bones": len(o.data.bones), "children": [c.name for c in o.children]}
                 for o in bpy.data.objects if o.type == "ARMATURE"]
    images = [{"name": im.name, "size": list(im.size), "packed": bool(im.packed_file), "filepath": im.filepath}
              for im in bpy.data.images if im.size[0] > 0]
    all_lo = [min((r["bounds_world"]["min"][i] for r in rows), default=0) for i in range(3)]
    all_hi = [max((r["bounds_world"]["max"][i] for r in rows), default=0) for i in range(3)]
    gates = []
    for r in rows:
        if not r["uv_layers"]:
            gates.append(f"{r['name']}: no UV layer")
        if r["empty_material_slots"]:
            gates.append(f"{r['name']}: {r['empty_material_slots']} empty material slot(s)")
        if r["negative_scale"]:
            gates.append(f"{r['name']}: negative scale")
        if not r["transforms_applied"]:
            gates.append(f"{r['name']}: transforms not applied (loc/rot/scale)")
        if r["degenerate_faces"]:
            gates.append(f"{r['name']}: {r['degenerate_faces']} degenerate face(s)")
        if r["loose_verts"]:
            gates.append(f"{r['name']}: {r['loose_verts']} loose vert(s)")
        if r["loose_parts"] > 8:
            gates.append(f"{r['name']}: {r['loose_parts']} loose parts (shell soup?)")
    if all_lo and rows and abs(all_lo[2]) > 0.02:
        gates.append(f"scene: lowest point z={all_lo[2]:.3f}, feet/base not on z=0")
    report = {
        "input": a.input or bpy.data.filepath,
        "blender": bpy.app.version_string,
        "objects": {"mesh": len(meshes), "armature": len(armatures), "total": len(bpy.data.objects)},
        "totals": {"verts": sum(r["verts"] for r in rows), "faces": sum(r["faces"] for r in rows), "tris": sum(r["tris"] for r in rows)},
        "bounds_world": {"min": [round(c, 4) for c in all_lo], "max": [round(c, 4) for c in all_hi],
                          "dims": [round(all_hi[i] - all_lo[i], 4) for i in range(3)]},
        "materials": [m.name for m in bpy.data.materials],
        "images": images,
        "armatures": armatures,
        "gates": gates,
        "meshes": rows,
    }
    if a.per_object:
        for r in rows:
            print(f"  {r['name']:40} tris={r['tris']:>8} dims={r['dims_world']} uv={len(r['uv_layers'])} mats={len(r['materials'])} parts={r['loose_parts']}")
    print(f"meshes={len(meshes)} tris={report['totals']['tris']} dims={report['bounds_world']['dims']} gates={len(gates)}")
    for g in gates:
        print("  GATE:", g)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print("wrote", a.out)
    summary = {k: report[k] for k in ("input", "objects", "totals", "bounds_world", "gates")}
    print("##JSON##" + json.dumps(summary))


main()
