---
name: blender-lpm-skill
description: Blender Low Poly Modelling Skill — build stylized, flat-shaded, game-ready low-poly assets (weapons, shields, armor, props, modular architecture) from primitives with a fixed triangle budget, a single palette material, Unity-ready FBX + BaseColor/MaskMap export, and a measured render-inspect loop. Use for any "make a low-poly X", "stylized game asset", "flat-shaded", "palette texture", "1000 tris" request in Blender, headless or through MCP.
---

# Blender Low Poly Modelling Skill (LPM)

Low-poly is a discipline, not a decimate button: **silhouette first, one palette material, every triangle
earns its place, numbers before opinions.** This skill gives you a procedure and a toolkit (`scripts/lpm.py`)
that turns a brief into a finished, exported, measured asset in one headless run.

## Procedure

1. **Brief → budget.** Write one line: *asset, real size in metres, triangle budget, palette cells, target
   engine.* Budgets: hero weapon 1 200 · shield/helmet 1 500 · prop 800 · kit module 600–3 000 · character 8 000
   (see [references/budgets-and-style.md](references/budgets-and-style.md)).
2. **Part list.** Decompose the object into 4–12 primitive parts, top-down (a gladius = blade, ridge, guard, grip,
   rings, pommel, rivet). Give each part a palette colour. Note which parts are mirrored.
3. **Recipe script.** Write a short Python recipe using `lpm` (copy the pattern from `examples/`): `box`, `prism`,
   `lathe`, `sweep`, `plate`, then `bend` / `taper` / `mirror_x` / `rotate` / `move`. Metres, Z up, front = −Y.
   Finish with `lpm.finish(name, parts, palette, budget)` and `lpm.export_unity(...)`.
   Run: `python scripts/bl.py --script my_recipe.py -- --out _work/<asset>/<Name>`.
4. **Look at it.** Render five views + contact sheet:
   `python scripts/bl.py --script scripts/render_views.py -- --input _work/<asset>/<Name>.blend --out _work/<asset>/views --ortho`
   Read the sheet. Judge silhouette (front, side), proportion (compare against the brief's metres), read-ability of
   parts (do colours separate parts?), facet count (is any curve wasting triangles?). Fix the recipe, re-run.
   Three iterations is normal; more than five means the part list was wrong — redo step 2.
5. **Reference overlay** when a concept exists: `scripts/compare_silhouette.py --ref concept.png --render views/front.png`
   → IoU ≥ 0.90, aspect diff ≤ 3 %, then argue about details.
6. **Gates.** `python scripts/bl.py --script scripts/inspect_scene.py -- --input <Name>.blend --out <Name>.inspect.json`
   then `python scripts/gate_report.py <Name>.inspect.json --class <static-prop|hard-surface|environment-module|character> --budget <n>`.
   PASS required: budget, transforms applied, base at z = 0, UVs present, no empty slots, no degenerate faces,
   no loose vertices.
7. **Deliver**: `<Name>.blend`, `<Name>.fbx` (Unity axes −Z forward / Y up), `tex/<Name>_BaseColor.png`,
   `tex/<Name>_MaskMap.png` (R metallic · G AO · A smoothness), plus the contact sheet and the gate report.
   Report triangles vs budget, dimensions, and any deliberate deviation from the reference.

## Style rules

- **Flat shading everywhere**; curvature comes from facet count: 6–8 sides for grips and rivets, 8–12 for domes
  and shafts, 10–16 for hero wheels and shields. Never subdivide.
- **Silhouette > surface.** Spend triangles where the outline changes (tips, guards, crests, capitals); flat
  regions are single quads.
- **Palette, not textures.** One material, one 8×N-cell palette image (`Closest` interpolation), each face's UV in
  the centre of its cell; metallic / smoothness live in the matching MaskMap palette. No bakes, no seams, no
  texel-density worries. Detail like rings, bands and rivets is *geometry* so it shows in the palette.
- **Real scale.** 1 unit = 1 m; a gladius is 0.65 m, a scutum 1.05 m, a helmet 0.30 m, a door 2.2 m.
  Base on z = 0, centred on x = 0, pivot at the base centre (props) or the snapping corner (kit modules).
- **Read-ability at 3 m**: contrast between neighbouring parts (wood next to steel next to bronze); avoid two
  similar mid-greys touching.
- **Symmetry by mirror**, never by remodeling; asymmetric details only when the reference has them.
- **Kit modules** sit on a metric grid (0.5 / 1 m), share the palette, and have flat contact faces.

## Toolkit summary (`scripts/lpm.py`)

| Call | Makes |
| --- | --- |
| `Palette([(name, "#hex", metallic, roughness), …])` / `PALETTE_ROMAN` | palette cells; `P["steel"]` → index |
| `box(name, (x, y, z), at, color, taper)` | block, optional top taper |
| `prism(name, sides, r, h, at, color, radius_top, rotate)` | n-gon column / ring / rivet |
| `lathe(name, [(r, z), …], segments, at, color)` | revolved profile (pommel, boss, dome, base) |
| `sweep(name, [(x, z), …], depth, at, color, axis)` | extruded outline (blade, plate, crest, cheek) |
| `plate(name, w, h, t, corner, at, color)` | rounded rectangular plate (shield body) |
| `bend(ob, radius, axis)` · `taper(ob, f, z0, z1)` · `mirror_x(ob)` · `rotate` · `move` · `scale` | deformers |
| `finish(name, parts, palette, budget)` | join, weld, ground, centre, palette UVs, single material, budget check |
| `export_unity(ob, stem)` | `.blend` + Unity FBX + palette PNGs; prints `##JSON##` report |

Companion scripts: `bl.py` (run Blender headless), `render_views.py` (5 views + sheet), `inspect_scene.py`,
`gate_report.py`, `compare_silhouette.py`. Worked recipes in `examples/`: gladius, scutum, galea helmet, arena column.

## With Blender MCP instead of headless

Paste the recipe into `execute_blender_code` after `sys.path.insert(0, "<skill>/scripts")`; use the server's
screenshot/render tool instead of `render_views.py`. The procedure does not change.

## Do not

- Do not decimate a high-poly mesh and call it low-poly; rebuild from primitives.
- Do not add a normal map to fake detail on a flat-shaded asset.
- Do not accept an asset from one flattering view; the side and top views expose thickness and proportion errors.
- Do not exceed the budget "just a little": remove a facet ring, merge two parts, or drop a rivet.
