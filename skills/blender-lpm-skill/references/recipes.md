# Writing a recipe

```python
from _common import lpm, out_stem        # inside examples/; elsewhere: sys.path.insert(0, "<skill>/scripts"); import lpm
lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)       # or your own list of (name, hex, metallic, roughness)

head  = lpm.sweep("head", [(-0.09, 0), (0.09, 0), (0.12, 0.14), (0, 0.19), (-0.12, 0.14)], depth=0.02, at=(0, 0, 1.15), color=P["iron"])
haft  = lpm.prism("haft", 8, 0.018, 1.15, at=(0, 0, 0), color=P["wood"], radius_top=0.016)
cap   = lpm.prism("cap", 6, 0.02, 0.03, at=(0, 0, 0), color=P["bronze"])
axe = lpm.finish("SM_Axe", [head, haft, cap], P, budget=900)
lpm.export_unity(axe, out_stem("_work/lpm/axe/SM_Axe"))
```

Rules of thumb
- Build parts at their final position; use `at=` for the base point of each part.
- `sweep` outlines are (x, z) for front-facing shapes extruded along Y (`axis="y"`), or (x, y) for slabs extruded up (`axis="z"`). Outlines must be simple (non-self-intersecting) polygons listed in order.
- `lathe` profiles go bottom → top as (radius, z); start/end with radius 0 for closed poles.
- Deformers (`bend`, `taper`, `scale`, `rotate`, `move`) edit mesh data in place — apply them before `finish`.
- Colour is per part; if one part needs two colours, split it into two parts — or use `lpm.paint(part, colour, where=...)` to recolour faces by position/normal/index.
- **Never leave two parts coplanar** (a lid end cap on the body's side plane, a strap flush with a panel). Overlap by ≥ 2 mm or stand proud by ≥ 2 mm. Coplanar faces z-fight in the viewport and render black seams in Cycles (shadow rays hit the twin face).
- `finish` welds vertices closer than 0.5 mm; overlapping parts are fine (they are one object, not one manifold) — the engine does not care, the silhouette does.
- Always run through `bl.py` so Blender starts from factory settings and the run is reproducible.
