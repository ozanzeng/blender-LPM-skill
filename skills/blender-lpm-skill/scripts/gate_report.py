#!/usr/bin/env python3
"""
gate_report.py - turn an inspect_scene.py JSON into a PASS/FAIL gate report (plain Python, no bpy).

  python gate_report.py _work/asset.inspect.json --class static-prop [--budget 1200] [--max-parts 6] [--out report.md]

Exit code 0 = all hard gates pass, 1 = at least one hard gate failed.
"""
from __future__ import annotations

import argparse
import json
import sys

CLASSES = {
    "static-prop":        {"budget": 1200, "max_parts": 6,  "nonmanifold": "warn", "boundary": "warn", "shading": "flat",   "materials": 2},
    "hard-surface":       {"budget": 1500, "max_parts": 8,  "nonmanifold": "warn", "boundary": "warn", "shading": "flat",   "materials": 3},
    "environment-module": {"budget": 3000, "max_parts": 12, "nonmanifold": "warn", "boundary": "ok",   "shading": "flat",   "materials": 2},
    "character":          {"budget": 8000, "max_parts": 3,  "nonmanifold": "fail", "boundary": "fail", "shading": "smooth", "materials": 4},
    "generator-mesh":     {"budget": 0,    "max_parts": 0,  "nonmanifold": "ok",   "boundary": "ok",   "shading": "any",    "materials": 0},
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("inspect_json")
    p.add_argument("--class", dest="cls", default="static-prop", choices=sorted(CLASSES))
    p.add_argument("--budget", type=int, default=0)
    p.add_argument("--max-parts", type=int, default=0)
    p.add_argument("--max-materials", type=int, default=0)
    p.add_argument("--ground-tolerance", type=float, default=0.02)
    p.add_argument("--allow-floating", action="store_true")
    p.add_argument("--out", default="")
    a = p.parse_args()
    d = json.load(open(a.inspect_json, encoding="utf-8"))
    rules = dict(CLASSES[a.cls])
    if a.budget: rules["budget"] = a.budget
    if a.max_parts: rules["max_parts"] = a.max_parts
    if a.max_materials: rules["materials"] = a.max_materials

    rows: list[tuple[str, str, str, str, str]] = []   # gate, measured, threshold, verdict, fix

    def gate(name, measured, threshold, ok, hard=True, fix=""):
        rows.append((name, str(measured), str(threshold), ("PASS" if ok else ("FAIL" if hard else "WARN")), fix if not ok else ""))

    tris = d["totals"]["tris"]
    if rules["budget"]:
        gate("triangle budget", tris, f"<= {rules['budget']}", tris <= rules["budget"], fix="decimate planar/collapse or remesh+decimate (repairs.md)")
    else:
        gate("triangle count (input)", tris, "report only", True)
    dims = d["bounds_world"]["dims"]
    gate("dimensions (m)", dims, "plausible for the object", True, hard=False)
    zmin = d["bounds_world"]["min"][2]
    if not a.allow_floating:
        gate("lowest point z", round(zmin, 4), f"|z| <= {a.ground_tolerance}", abs(zmin) <= a.ground_tolerance, fix="move to ground and apply transforms")
    meshes = d.get("meshes", [])
    for m in meshes:
        n = m["name"]
        gate(f"{n}: transforms applied", m["transforms_applied"], "True", m["transforms_applied"], fix="transform_apply(location, rotation, scale)")
        gate(f"{n}: negative scale", m["negative_scale"], "False", not m["negative_scale"], fix="apply scale + recalc normals")
        gate(f"{n}: UV layers", len(m["uv_layers"]), ">= 1", len(m["uv_layers"]) >= 1, fix="seams + unwrap")
        gate(f"{n}: empty material slots", m["empty_material_slots"], "0", m["empty_material_slots"] == 0, fix="assign or remove slot")
        gate(f"{n}: degenerate faces", m["degenerate_faces"], "0", m["degenerate_faces"] == 0, fix="dissolve_degenerate + remove_doubles")
        gate(f"{n}: loose vertices", m["loose_verts"], "0", m["loose_verts"] == 0, fix="select_loose + delete")
        if rules["max_parts"]:
            gate(f"{n}: loose parts", m["loose_parts"], f"<= {rules['max_parts']}", m["loose_parts"] <= rules["max_parts"], hard=False, fix="delete debris islands / join intended parts")
        if rules["nonmanifold"] != "ok":
            gate(f"{n}: non-manifold edges", m["non_manifold_edges"], "0", m["non_manifold_edges"] == 0, hard=(rules["nonmanifold"] == "fail"), fix="fill holes / merge / remove interior faces")
        if rules["boundary"] != "ok":
            gate(f"{n}: boundary edges", m["boundary_edges"], "0 on closed shapes", m["boundary_edges"] == 0, hard=(rules["boundary"] == "fail"), fix="fill_holes or confirm open geometry is intended")
        if rules["shading"] == "flat":
            gate(f"{n}: flat shading", f"{m['smooth_faces_pct']}% smooth", "0% smooth", m["smooth_faces_pct"] == 0, hard=False, fix="shade_flat()")
        elif rules["shading"] == "smooth":
            gate(f"{n}: smooth shading", f"{m['smooth_faces_pct']}% smooth", "100% smooth", m["smooth_faces_pct"] == 100, hard=False, fix="shade_smooth() / smooth by angle")
        if rules["materials"]:
            gate(f"{n}: materials", len(m["materials"]), f"<= {rules['materials']}", len(m["materials"]) <= rules["materials"], hard=False, fix="merge materials into an atlas")
    hard_fail = [r for r in rows if r[3] == "FAIL"]
    warns = [r for r in rows if r[3] == "WARN"]
    lines = [f"# Geometry gate report — {d.get('input', '')}", "",
             f"class: **{a.cls}** · meshes: {len(meshes)} · triangles: {tris} · dims: {dims} · Blender {d.get('blender', '')}", "",
             f"**Result: {'FAIL' if hard_fail else 'PASS'}** ({len(hard_fail)} hard failures, {len(warns)} warnings)", "",
             "| Gate | Measured | Threshold | Verdict | Fix |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {g} | {mv} | {t} | {v} | {f} |" for g, mv, t, v, f in rows]
    for extra in d.get("gates", []):
        lines.append(f"| inspector note | {extra} | — | WARN | — |")
    text = "\n".join(lines) + "\n"
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
