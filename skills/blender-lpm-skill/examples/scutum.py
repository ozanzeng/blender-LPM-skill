"""Roman scutum: curved rectangular shield 1.05 m x 0.65 m, boss, rim, spine, bands. Budget 1500 tris."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
W, H, T = 0.52, 1.05, 0.014   # concept reference aspect 0.455 (w/h after bend)
R = 0.40  # bend radius around the vertical axis (concave toward the arm, +Y)

body = lpm.grid_box("body", (W, T, H), at=(0, 0, 0), color=P["red"], nx=8, nz=1)
rim_l = lpm.grid_box("rim_l", (0.035, T + 0.010, H), at=(-W / 2 + 0.0175, 0, 0), color=P["bronze"], nx=1)
rim_r = lpm.grid_box("rim_r", (0.035, T + 0.010, H), at=(W / 2 - 0.0175, 0, 0), color=P["bronze"], nx=1)
rim_b = lpm.grid_box("rim_b", (W, T + 0.010, 0.035), at=(0, 0, 0), color=P["bronze"], nx=8)
rim_t = lpm.grid_box("rim_t", (W, T + 0.010, 0.035), at=(0, 0, H - 0.035), color=P["bronze"], nx=8)
spine = lpm.grid_box("spine", (0.05, 0.012, H - 0.08), at=(0, -T / 2 - 0.004, 0.04), color=P["gold"], nx=1)
band1 = lpm.grid_box("band1", (W - 0.07, 0.012, 0.04), at=(0, -T / 2 - 0.004, H * 0.28), color=P["gold"], nx=8)
band2 = lpm.grid_box("band2", (W - 0.07, 0.012, 0.04), at=(0, -T / 2 - 0.004, H * 0.68), color=P["gold"], nx=8)
parts = [body, rim_l, rim_r, rim_b, rim_t, spine, band1, band2]
for p in parts:
    lpm.bend(p, R, axis="z")
boss = lpm.lathe("boss", [(0.0, 0.0), (0.065, 0.0), (0.065, 0.012), (0.048, 0.042), (0.0, 0.06)], segments=10, at=(0, 0, 0), color=P["iron"])
lpm.rotate(boss, 90, "X")               # dome points to -Y (front)
lpm.move(boss, 0, -T / 2 - 0.004, H / 2)
shield = lpm.finish("SM_Scutum", parts + [boss], P, budget=1500)
lpm.export_unity(shield, out_stem("_work/lpm/scutum/SM_Scutum"))
