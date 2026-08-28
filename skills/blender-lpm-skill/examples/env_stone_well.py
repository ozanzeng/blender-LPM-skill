"""Ref: Assets/09_Environment/75_stone_well.png - octagonal stone well with meander band, red/gold panels, dark shaft. 1.6 m tall. Budget 1500."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lpm, out_stem
import lpm_kit as kit, math

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
parts = []
parts += kit.plinth_steps("base", 2.7, 2.7, [0.16, 0.14], at=(0, 0, 0), color=P["stone_dark"], inset=0.12)
parts += [lpm.prism("body", 8, 1.12, 0.98, at=(0, 0, 0.30), color=P["stone"], rotate=22.5)]   # taller body: reference aspect 1.11
# red panels with gold frame and medallion on 4 alternating faces
for k in range(4):
    a = 22.5 + 90 * k + 45
    x, y = 1.13 * math.cos(math.radians(a)), 1.13 * math.sin(math.radians(a))
    frame = lpm.box(f"frame{k}", (0.62, 0.04, 0.56), at=(0, 0, 0.48), color=P["gold"]); lpm.rotate(frame, a + 90, "Z"); lpm.move(frame, x, y, 0)
    panel = lpm.box(f"panel{k}", (0.52, 0.05, 0.46), at=(0, 0, 0.53), color=P["red"]); lpm.rotate(panel, a + 90, "Z"); lpm.move(panel, x, y, 0)
    disc = lpm.prism(f"disc{k}", 8, 0.11, 0.05, at=(0, 0, 0), color=P["gold"], rotate=22.5); lpm.rotate(disc, 90, "X"); lpm.rotate(disc, a + 90, "Z"); lpm.move(disc, x * 1.01, y * 1.01, 0.76)
    parts += [frame, panel, disc]
# meander band ring
parts += [lpm.prism("band", 8, 1.18, 0.28, at=(0, 0, 1.28), color=P["cream"], rotate=22.5)]
for k in range(8):
    a = 22.5 + 45 * k + 22.5
    for j, off in enumerate((-0.28, 0.0, 0.28)):
        x, y = 1.185 * math.cos(math.radians(a)), 1.185 * math.sin(math.radians(a))
        key = lpm.box(f"key{k}{j}", (0.14, 0.03, 0.12), at=(off, 0, 1.36), color=P["stone_dark"]); lpm.rotate(key, a + 90, "Z"); lpm.move(key, x, y, 0)
        parts.append(key)
parts += [lpm.prism("rim", 8, 1.28, 0.22, at=(0, 0, 1.56), color=P["stone_dark"], rotate=22.5),
          lpm.prism("rim_top", 8, 1.24, 0.06, at=(0, 0, 1.78), color=P["stone"], rotate=22.5),
          lpm.prism("shaft", 8, 0.90, 1.53, at=(0, 0, 0.32), color=P["black"], rotate=22.5)]     # dark interior reads as the hole
well = lpm.finish("SM_StoneWell", parts, P, budget=1500)
lpm.export_unity(well, out_stem("_work/lpm/env/stone_well/SM_StoneWell"), extra=[lpm.collision_box(well)])
