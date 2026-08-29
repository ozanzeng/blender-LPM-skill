"""Ref: 71_lion_statue_altar.png - HYBRID: pedestal from primitives (relief + palette), lion from the visual hull of the
turnaround views (scripts/shape_from_views.py -> hull_to_lowpoly.py -> OBJ), coloured with the palette 'lion' cell and
joined into the same single-material mesh. Budget 3000."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lpm, out_stem
import lpm_kit as kit, math, bpy

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN + [("stone_light", "#cbbf9f", 0.0, 0.9), ("lion", "#b9a97f", 0.0, 0.85), ("lion_dark", "#8f8261", 0.0, 0.85)])
parts = []
parts.append(lpm.box("tier0", (2.2, 2.2, 0.75), at=(0, 0, 0), color=P["stone_dark"]))
for facing, at in (("-y", (0, -1.1, 0)), ("+y", (0, 1.1, 0)), ("-x", (-1.1, 0, 0)), ("+x", (1.1, 0, 0))):
    for j, z in enumerate((0.0, 0.38)):
        parts += kit.block_course(f"blk{facing}{j}", 2.2, 0.36, 0.14, at=(at[0], at[1], z), n=4 if j == 0 else 3, color=P["stone"], seed=7 + j, jitter=0.2, gap=0.03, facing=facing)
parts.append(lpm.box("tier0_top", (2.25, 2.25, 0.12), at=(0, 0, 0.75), color=P["stone_light"]))
Z1 = 0.87
parts.append(lpm.box("tier1", (1.7, 1.7, 1.0), at=(0, 0, Z1), color=P["stone"]))
for sx in (-1, 1):
    for sy in (-1, 1):
        parts += [lpm.box(f"pil{sx}{sy}", (0.26, 0.26, 1.0), at=(sx * 0.80, sy * 0.80, Z1), color=P["stone_light"]),
                  lpm.box(f"pilbase{sx}{sy}", (0.32, 0.32, 0.10), at=(sx * 0.80, sy * 0.80, Z1 - 0.004), color=P["stone_dark"]),
                  lpm.box(f"pilcap{sx}{sy}", (0.32, 0.32, 0.10), at=(sx * 0.80, sy * 0.80, Z1 + 0.90), color=P["stone_dark"])]
        for facing, off in (("y", (0, sy * 0.135)), ("x", (sx * 0.135, 0))):
            fx, fy = sx * 0.80 + off[0], sy * 0.80 + off[1]
            if facing == "y":
                parts += [lpm.box(f"pf{sx}{sy}y", (0.20, 0.03, 0.72), at=(fx, fy, Z1 + 0.14), color=P["gold"]), lpm.box(f"pp{sx}{sy}y", (0.14, 0.04, 0.62), at=(fx, fy + sy * 0.006, Z1 + 0.19), color=P["red"])]
            else:
                parts += [lpm.box(f"pf{sx}{sy}x", (0.03, 0.20, 0.72), at=(fx, fy, Z1 + 0.14), color=P["gold"]), lpm.box(f"pp{sx}{sy}x", (0.04, 0.14, 0.62), at=(fx + sx * 0.006, fy, Z1 + 0.19), color=P["red"])]
parts.append(lpm.box("frieze", (1.9, 1.9, 0.22), at=(0, 0, Z1 + 1.0 - 0.004), color=P["stone_light"]))
for x in (-0.55, 0.0, 0.55):
    parts += kit.medallion(f"medf{x:+.1f}", 0.12, at=(x, -0.955, Z1 + 1.11), color=P["gold"], center=P["crimson"], thickness=0.03, facing="-y")
    parts += kit.medallion(f"medb{x:+.1f}", 0.12, at=(x, 0.955, Z1 + 1.11), color=P["gold"], center=P["crimson"], thickness=0.03, facing="+y")
for y in (-0.45, 0.45):
    parts += kit.medallion(f"medl{y:+.1f}", 0.12, at=(-0.955, y, Z1 + 1.11), color=P["gold"], center=P["crimson"], thickness=0.03, facing="-x")
    parts += kit.medallion(f"medr{y:+.1f}", 0.12, at=(0.955, y, Z1 + 1.11), color=P["gold"], center=P["crimson"], thickness=0.03, facing="+x")
parts += [lpm.box("cap", (2.05, 2.05, 0.20), at=(0, 0, Z1 + 1.21), color=P["stone_dark"]),
          lpm.box("cap_top", (1.95, 1.95, 0.07), at=(0, 0, Z1 + 1.41 - 0.004), color=P["stone_light"])]
parts += kit.banner("banner", 0.64, 1.05, at=(0, -0.90, Z1 + 1.05), color=P["red"], border=P["gold"], depth=0.03, tip=0.22, border_w=0.035)
for k in range(6):
    for sx in (-1, 1):
        leaf = lpm.box(f"leaf{k}{sx}", (0.09, 0.02, 0.2), at=(0, 0, -0.1), color=P["gold"], taper=(0.25, 1.0))
        lpm.rotate(leaf, sx * (40 - 16 * k), "Y", about=(0, 0, 0))
        lpm.move(leaf, sx * (0.19 - 0.025 * abs(k - 2.5)), -0.945, Z1 + 0.42 + 0.065 * k)
        parts.append(leaf)
# ---- lion from the visual hull (already decimated by hull_to_lowpoly.py), base at the cap top
Z = Z1 + 1.41 + 0.07 - 0.004
lion_obj = os.environ.get("LION_HULL_OBJ", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "..", "_work", "lpm", "env", "lion_altar", "hull", "lion_lp.obj"))
bpy.ops.wm.obj_import(filepath=os.path.abspath(lion_obj), forward_axis="Y", up_axis="Z")
lion = bpy.context.selected_objects[0]; lion.name = "lion_hull"
lpm._col("COL_LowPoly").objects.link(lion) if lion.name not in lpm._col("COL_LowPoly").objects else None
lo = min(v.co.z for v in lion.data.vertices)
lion.data.transform(__import__("mathutils").Matrix.Translation((0, 0.05, Z - lo)))
attr = lion.data.attributes.get("lpm_color") or lion.data.attributes.new("lpm_color", "INT", "FACE")
for i in range(len(lion.data.polygons)): attr.data[i].value = P["lion"]
for poly in lion.data.polygons: poly.use_smooth = False
parts.append(lion)
altar = lpm.finish("SM_LionAltar", parts, P, budget=3000)
lpm.export_unity(altar, out_stem("_work/lpm/env/lion_altar/SM_LionAltar"), extra=[lpm.collision_box(altar)])
