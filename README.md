# Blender Low Poly Modelling Skill (blender-LPM-skill)

**An AI agent skill that makes Claude Code (and Codex / Cursor) model low-poly, flat-shaded, game-ready 3D
assets in Blender — from a one-line brief to an exported Unity FBX with a palette texture, in one headless run.**

Keywords: Blender low poly modelling · AI 3D asset generation · Claude Code skill · Blender MCP · procedural
low-poly · palette texture · flat shading · game-ready FBX · Unity · Godot · stylized 3D · Blender Python (bpy)
automation · agent skills.

---

## What it does

Give the agent a brief — *"low-poly Roman gladius, 0.65 m, 1 200 triangles, Unity"* — and the skill:

1. decomposes the object into primitive parts with a fixed triangle budget,
2. writes a short **recipe script** using the bundled `lpm.py` toolkit (box, prism, lathe, sweep, plate, grid,
   bend, taper, mirror),
3. runs Blender **headless** (or through Blender MCP) to build it, flat-shaded, with **one palette material**
   (BaseColor + Unity MaskMap: R metallic · G AO · A smoothness),
4. renders front / side / back / three-quarter / top views and a contact sheet, **looks at them**, and iterates,
5. overlays the result on your concept art (IoU, aspect, centroid, band errors),
6. runs geometry gates (budget, transforms, ground, UVs, degenerate faces, loose vertices) and
7. exports `.blend` + `.fbx` (−Z forward, Y up) + `tex/*.png` with a measured report.

No decimation of high-poly meshes, no bakes, no normal maps: real low-poly discipline — silhouette first,
every triangle earns its place, numbers before opinions.

## Results from the first run (Blender 5.2, RTX 3070 Ti, headless)

| Asset (recipe in `examples/`) | Triangles | Budget | Size (m) | Gates |
| --- | ---: | ---: | --- | --- |
| Roman gladius | 268 | 1 200 | 0.075 × 0.06 × 0.65 | PASS |
| Curved scutum with boss, rim, spine, bands | ~300 | 1 500 | 0.59 × 0.20 × 1.05 | PASS |
| Imperial Gallic galea helmet with crest and cheek plates | 234 | 1 500 | 0.30 × 0.25 × 0.39 | PASS |
| Arena column module (plinth, shaft, capital) | 224 | 600 | 0.72 × 0.72 × 2.88 | PASS |

Each one is a ~30-line recipe and builds in seconds; the whole set shares one 16-colour palette (`PALETTE_ROMAN`).

## Install

```bash
git clone https://github.com/ozanzeng/blender-LPM-skill.git
cp -r blender-LPM-skill/skills/blender-lpm-skill /path/to/your/project/.claude/skills/
```

Requirements: Blender 4.2+ (tested on 5.2 LTS), Python 3.9+ on the host, Claude Code (or any agent runtime that
reads `SKILL.md`). Set `BLENDER_EXE` if Blender is not in the default install path. Optional: Blender MCP
(official Blender Lab server or ahujasid/blender-mcp) for interactive sessions.

## Try it in 60 seconds

```bash
S=.claude/skills/blender-lpm-skill
python $S/scripts/bl.py --script $S/examples/gladius.py -- --out _work/gladius/SM_Gladius
python $S/scripts/bl.py --script $S/scripts/render_views.py -- --input _work/gladius/SM_Gladius.blend --out _work/gladius/views --ortho
python $S/scripts/bl.py --script $S/scripts/inspect_scene.py -- --input _work/gladius/SM_Gladius.blend --out _work/gladius/inspect.json
python $S/scripts/gate_report.py _work/gladius/inspect.json --class hard-surface --budget 1200
```

Open `_work/gladius/views/sheet.png`, then `_work/gladius/SM_Gladius.fbx` in Unity with the two PNGs in `tex/`.

## Write your own recipe

```python
import os, sys; sys.path.insert(0, ".claude/skills/blender-lpm-skill/scripts"); import lpm
lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
head = lpm.sweep("head", [(-0.09, 0), (0.09, 0), (0.12, 0.14), (0, 0.19), (-0.12, 0.14)], depth=0.02, at=(0, 0, 1.15), color=P["iron"])
haft = lpm.prism("haft", 8, 0.018, 1.15, at=(0, 0, 0), color=P["wood"], radius_top=0.016)
axe  = lpm.finish("SM_Axe", [head, haft], P, budget=900)
lpm.export_unity(axe, "_work/axe/SM_Axe")
```

`Palette` cells carry colour, metallic and roughness; `finish()` joins the parts, welds, grounds and centres the
mesh, writes per-face palette UVs, assigns the single material and checks the budget; `export_unity()` writes
the deliverables and a JSON report.

## What is in the skill

```
skills/blender-lpm-skill/
  SKILL.md                      procedure, style rules, toolkit summary (what the agent reads)
  references/
    budgets-and-style.md        triangle budgets, facet counts, palette design, Roman proportions cheat-sheet
    recipes.md                  how to write recipes
    export-unity.md             FBX / texture import contract for Unity (and GLB for Godot)
    qa-checklist.md             delivery checklist
  scripts/
    lpm.py                      the toolkit (builders, deformers, palette material, finish, export)
    bl.py                       run Blender headless from the agent
    render_views.py             5-view render + contact sheet (screenshot substitute)
    inspect_scene.py            deterministic metrics for .blend/.glb/.fbx/.obj
    gate_report.py              PASS/FAIL gates from the metrics
    compare_silhouette.py       silhouette overlay vs reference image (IoU, aspect, bands)
  examples/                     gladius, scutum, galea helmet, arena column
```

## How it compares

| | High-poly → decimate | Image-to-3D generators | **blender-LPM-skill** |
| --- | --- | --- | --- |
| Topology | shredded silhouettes | 100k–1.5M-tri shell soups, needs retopo | clean primitives, budget by design |
| Texturing | bakes, seams, texel density | 4K atlases | one 16-cell palette PNG |
| Reproducible | no | seed-dependent, paid | yes — the recipe *is* the asset |
| Editable later | hard | hard | change two numbers, re-run |
| Cost | time | per generation | free, offline |

Generators still have their place for organic forms; pair this skill with a retopology skill for those.

## Related

- [blender-modelling-skills](https://github.com/ozanzeng/blender-modelling-skills) — a curated, verified
  collection of 32 Blender agent skills (routing hub, retopology, UV/PBR, rigging, reference matching, Unity
  export) plus a research catalog of 631 unique Blender skills found on GitHub. This skill slots into that hub as
  the "model it from scratch" lane.

## License

MIT © 2026 Ozan Zengin. Original work; no third-party skill content.
