"""Ref: Assets/09_Environment/79_amphora_urn.png - cream amphora with red bands, gold meander, two handles. 1.1 m tall. Budget 900."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lpm, out_stem
import lpm_kit as kit, math

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
profile = [(0.0, 0.0), (0.16, 0.0), (0.19, 0.06), (0.14, 0.14), (0.24, 0.30), (0.33, 0.50), (0.34, 0.62), (0.30, 0.78), (0.21, 0.90), (0.15, 0.96), (0.14, 1.02), (0.19, 1.08), (0.20, 1.12), (0.0, 1.12)]
body = lpm.lathe("body", profile, segments=12, at=(0, 0, 0), color=P["cream"])
lpm.paint(body, P["red"], where=lambda c, n, i: 0.42 < c.z < 0.50 or 0.70 < c.z < 0.78 or 0.03 < c.z < 0.08)
lpm.paint(body, P["gold"], where=lambda c, n, i: 1.02 < c.z < 1.13 and n.z < 0.7)
lpm.paint(body, P["gold"], where=lambda c, n, i: c.z < 0.03)
parts = [body]
# meander band as small dark squares around the belly
for k in range(12):
    a = 360 * k / 12 + 15
    x, y = 0.325 * math.cos(math.radians(a)), 0.325 * math.sin(math.radians(a))
    key = lpm.box(f"key{k}", (0.07, 0.02, 0.07), at=(0, 0, 0.55), color=P["red"]); lpm.rotate(key, a + 90, "Z"); lpm.move(key, x, y, 0)
    parts.append(key)
# handles: half loops from the shoulder (z 0.80) up to the neck (z 1.04), bulging outward
for sx in (-1, 1):
    parts += kit.handle_arc(f"handle{sx}", 0.12, 0.05, 180, at=(sx * 0.27, 0, 0.80), color=P["gold"], plane="xz", flip=(sx < 0))
urn = lpm.finish("SM_Amphora", parts, P, budget=900)
lpm.export_unity(urn, out_stem("_work/lpm/env/amphora/SM_Amphora"), extra=[lpm.collision_box(urn)])
