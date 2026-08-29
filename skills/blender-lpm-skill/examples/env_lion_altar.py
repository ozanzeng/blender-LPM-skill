"""Ref: Assets/09_Environment/71_lion_statue_altar.png - sitting stone lion (faceted primitives) on a two-tier altar:
rough block base, pilastered upper tier with red/gold panels, gold medallions, red banner with laurel, thick cap.
Pedestal 2.0 x 2.0 x 2.2 m, lion 1.5 m -> 3.7 m total. Budget 3000 (lion <= 1500). PBR = palette definitions only."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lpm, out_stem
import lpm_kit as kit, math

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN + [("stone_light", "#cbbf9f", 0.0, 0.9), ("lion", "#b9a97f", 0.0, 0.85), ("lion_dark", "#8f8261", 0.0, 0.85)])
parts = []
# ---------------------------------------------------------------- tier 0: rough block base 2.2 x 2.2 x 0.75
parts.append(lpm.box("tier0", (2.2, 2.2, 0.75), at=(0, 0, 0), color=P["stone_dark"]))
for facing, at in (("-y", (0, -1.1, 0)), ("+y", (0, 1.1, 0)), ("-x", (-1.1, 0, 0)), ("+x", (1.1, 0, 0))):
    for j, z in enumerate((0.0, 0.38)):
        parts += kit.block_course(f"blk{facing}{j}", 2.2, 0.36, 0.14, at=(at[0], at[1], z), n=4 if j == 0 else 3, color=P["stone"], seed=7 + j, jitter=0.2, gap=0.03, facing=facing)
parts.append(lpm.box("tier0_top", (2.25, 2.25, 0.12), at=(0, 0, 0.75), color=P["stone_light"]))
# ---------------------------------------------------------------- tier 1: pilasters, panels, frieze, cap  (0.87 .. 2.20)
Z1 = 0.87
parts.append(lpm.box("tier1", (1.7, 1.7, 1.0), at=(0, 0, Z1), color=P["stone"]))
for sx in (-1, 1):
    for sy in (-1, 1):
        parts += [lpm.box(f"pil{sx}{sy}", (0.26, 0.26, 1.0), at=(sx * 0.80, sy * 0.80, Z1), color=P["stone_light"]),
                  lpm.box(f"pilbase{sx}{sy}", (0.32, 0.32, 0.10), at=(sx * 0.80, sy * 0.80, Z1 - 0.004), color=P["stone_dark"]),
                  lpm.box(f"pilcap{sx}{sy}", (0.32, 0.32, 0.10), at=(sx * 0.80, sy * 0.80, Z1 + 0.90), color=P["stone_dark"])]
        # red panel + gold frame on each pilaster's front and side faces
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
# banner on the front, hanging from the frieze over the tier-1 face, laurel = two leaf arcs
parts += kit.banner("banner", 0.64, 1.05, at=(0, -0.90, Z1 + 1.05), color=P["red"], border=P["gold"], depth=0.03, tip=0.22, border_w=0.035)
for k in range(6):
    a = math.radians(-60 + 24 * k)                                   # left arc
    for sx in (-1, 1):
        leaf = lpm.box(f"leaf{k}{sx}", (0.045, 0.02, 0.11), at=(0, 0, -0.055), color=P["gold"], taper=(0.25, 1.0))
        lpm.rotate(leaf, sx * (35 - 14 * k), "Y", about=(0, 0, 0))
        lpm.move(leaf, sx * (0.16 - 0.02 * abs(k - 2.5) / 2.5), -0.945, Z1 + 0.45 + 0.055 * k)
        parts.append(leaf)
# ---------------------------------------------------------------- lion, sitting, facing -Y, on the cap (Z = 2.32), ~1.5 m tall
Z = Z1 + 1.41 + 0.07 - 0.004; C, D = P["lion"], P["lion_dark"]
def at(x, y, z): return (x, y, Z + z)
parts += [kit.blob("hind", (1.05, 1.05, 0.85), at=at(0, 0.40, 0.04), color=C, segments=8, rings=4),
          kit.blob("chest", (0.92, 0.95, 1.0), at=at(0, -0.30, 0.22), color=C, segments=8, rings=4),
          kit.blob("belly", (0.80, 1.15, 0.55), at=at(0, 0.05, 0.14), color=C, segments=8, rings=3)]
mane = lpm.lathe("mane", [(0.0, 0.0), (0.48, 0.04), (0.60, 0.25), (0.58, 0.55), (0.42, 0.78), (0.0, 0.86)], segments=8, at=at(0, -0.42, 0.78), color=D)
lpm.scale(mane, 1.0, 0.8, 1.0, about=at(0, -0.42, 0.78)); parts.append(mane)
parts += [kit.blob("head", (0.54, 0.60, 0.50), at=at(0, -0.62, 1.05), color=C, segments=8, rings=4),
          kit.wedge("muzzle", (0.36, 0.28, 0.24), at=at(0, -0.90, 1.08), color=C, direction="-y"),
          lpm.box("nose", (0.12, 0.07, 0.07), at=at(0, -1.05, 1.20), color=D),
          lpm.box("jaw", (0.24, 0.22, 0.10), at=at(0, -0.86, 1.02), color=D)]
for sx in (-1, 1):
    parts += [kit.wedge(f"ear{sx}", (0.12, 0.08, 0.14), at=at(sx * 0.20, -0.52, 1.46), color=D, direction="-y"),
              lpm.box(f"eye{sx}", (0.07, 0.03, 0.04), at=at(sx * 0.12, -0.90, 1.30), color=P["black"]),
              kit.limb(f"foreleg{sx}", 0.14, 0.11, 0.95, at=at(sx * 0.32, -0.55, 0.95), color=C, pitch=-4),
              lpm.box(f"forepaw{sx}", (0.28, 0.42, 0.16), at=at(sx * 0.32, -0.72, 0.0), color=C),
              kit.blob(f"haunch{sx}", (0.36, 0.72, 0.62), at=at(sx * 0.48, 0.32, 0.02), color=D, segments=6, rings=3),
              lpm.box(f"hindpaw{sx}", (0.24, 0.44, 0.16), at=at(sx * 0.50, -0.02, 0.0), color=C)]
parts.append(kit.limb("tail", 0.07, 0.05, 0.85, at=at(0.36, 0.85, 0.32), color=C, pitch=-100, yaw=25))
parts.append(lpm.prism("tailtuft", 6, 0.09, 0.14, at=at(0.62, 0.95, 0.0), color=D))
altar = lpm.finish("SM_LionAltar", parts, P, budget=3000)
lpm.export_unity(altar, out_stem("_work/lpm/env/lion_altar/SM_LionAltar"), extra=[lpm.collision_box(altar)])
