"""Ref: Assets/09_Environment/76_wall_torch_sconce.png - tall stone wall plate with red/gold panel, iron bracket with brace,
big iron torch cup with gold studs, coals and flame. 1.45 m tall. Budget 1200."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lpm, out_stem
import lpm_kit as kit, math

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN + [("flame", "#f2a13a", 0.0, 0.5), ("flame_core", "#ffe27a", 0.0, 0.5), ("coal", "#3a2a22", 0.0, 0.8)])
parts = []
WALL = 0.30                         # wall plane y; everything hangs toward -Y
# wall plate: tall rounded-corner slab, gold frame, red panel, gold stud
plate_o = [(-0.16, 0.0), (0.16, 0.0), (0.22, 0.08), (0.22, 0.92), (0.16, 1.0), (-0.16, 1.0), (-0.22, 0.92), (-0.22, 0.08)]
parts.append(lpm.sweep("plate", plate_o, 0.10, at=(0, WALL, 0.22), color=P["stone"], axis="y"))
frame_o = [(-0.10, 0.10), (0.10, 0.10), (0.15, 0.16), (0.15, 0.84), (0.10, 0.90), (-0.10, 0.90), (-0.15, 0.84), (-0.15, 0.16)]
parts.append(lpm.sweep("frame", frame_o, 0.05, at=(0, WALL - 0.06, 0.22), color=P["gold"], axis="y"))
panel_o = [(x * 0.78, 0.5 + (z - 0.5) * 0.9) for x, z in frame_o]
parts.append(lpm.sweep("panel", panel_o, 0.05, at=(0, WALL - 0.08, 0.22), color=P["red"], axis="y"))
parts += kit.rivets("stud", [(0, WALL - 0.11, 0.72)], radius=0.035, height=0.02, color=P["gold"], facing="-y")
# bracket: horizontal arm + diagonal brace, iron; collar on the torch
TY = -0.42                          # torch axis y
parts.append(lpm.box("arm", (0.07, WALL - TY + 0.02, 0.07), at=(0, (WALL + TY) / 2, 0.86), color=P["iron"]))
brace = lpm.box("brace", (0.06, 0.06, 0.62), at=(0, 0, 0), color=P["iron"])
lpm.rotate(brace, -48, "X", about=(0, 0, 0)); lpm.move(brace, 0, WALL - 0.02, 0.42)
parts.append(brace)
parts += kit.rivets("armstud", [(0, WALL - 0.12, 0.90), (0, TY + 0.06, 0.90)], radius=0.02, height=0.04, color=P["gold"], facing="-y")
parts.append(lpm.prism("collar", 8, 0.085, 0.08, at=(0, TY, 0.82), color=P["iron"]))
# torch: pointed tip, tapered handle with gold rings, iron cup with gold studs, coals, flame
parts += [lpm.lathe("tip", [(0.0, 0.0), (0.045, 0.14)], segments=8, at=(0, TY, 0.0), color=P["iron"]),
          lpm.prism("handle", 8, 0.045, 0.78, at=(0, TY, 0.14), color=P["iron"], radius_top=0.065),
          lpm.prism("ring1", 8, 0.06, 0.05, at=(0, TY, 0.26), color=P["gold"]),
          lpm.prism("ring2", 8, 0.075, 0.05, at=(0, TY, 0.60), color=P["gold"]),
          lpm.lathe("cup", [(0.065, 0.0), (0.16, 0.10), (0.22, 0.26), (0.24, 0.34), (0.20, 0.34), (0.19, 0.12), (0.08, 0.02)], segments=8, at=(0, TY, 0.92), color=P["iron"]),
          lpm.prism("cup_rim", 8, 0.25, 0.05, at=(0, TY, 1.24), color=P["gold"], radius_top=0.24),
          lpm.prism("coals", 8, 0.19, 0.07, at=(0, TY, 1.27), color=P["coal"], radius_top=0.15)]
def stud(i, x, y, a):
    s = lpm.prism(f"cupstud{i}", 6, 0.028, 0.03, at=(0, 0, 0), color=P["gold"])
    lpm.rotate(s, 90, "X"); lpm.rotate(s, a + 90, "Z"); lpm.move(s, x, y, 1.10)
    return s
parts += kit.ring_of(8, 0.215, stud, at=(0, TY, 0))
parts += kit.flame("flame", 0.60, at=(0, TY, 1.30), color=P["flame"], core=P["flame_core"], width=0.36)
for k, (dx, dy, dz, s) in enumerate(((0.16, 0.05, 1.85, 0.05), (-0.18, -0.04, 1.75, 0.04), (0.06, -0.12, 1.98, 0.035))):   # sparks
    parts.append(lpm.prism(f"spark{k}", 4, s, s * 1.6, at=(dx, TY + dy, dz), color=P["flame"], rotate=45))
torch = lpm.finish("SM_WallTorch", parts, P, budget=1200)
lpm.export_unity(torch, out_stem("_work/lpm/env/torch_sconce/SM_WallTorch"), extra=[lpm.collision_box(torch)])
