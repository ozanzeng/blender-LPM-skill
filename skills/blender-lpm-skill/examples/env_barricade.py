"""Ref: Assets/09_Environment/80_wooden_arena_barricade.png - round wooden palisade with iron bands, red banners. 2.6 m across, 1.0 m tall. Budget 1500."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lpm, out_stem
import lpm_kit as kit, math

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
R, N = 1.40, 16          # wider ring: reference aspect 1.45
parts = []
def plank(i, x, y, a):
    tall = (i % 4 == 0)
    b = lpm.box(f"plank{i}", (0.47, 0.10, 1.08 if tall else 0.82), at=(0, 0, 0), color=P["wood"] if i % 2 else P["wood_light"], taper=(0.7, 1.0) if tall else (1.0, 1.0))
    lpm.rotate(b, a + 90, "Z"); lpm.move(b, x, y, 0)
    return b
parts += kit.ring_of(N, R, plank)
for z in (0.18, 0.54):
    parts += kit.wall_ring(f"band{z:.0f}", N, R + 0.065, 0.10, 0.03, at=(0, 0, z), color=P["iron"])
    parts += kit.rivets(f"riv{z:.0f}", [(1.0 * (R + 0.09) * math.cos(math.radians(a)), (R + 0.09) * math.sin(math.radians(a)), z + 0.05) for a in range(0, 360, 45)], radius=0.025, color=P["iron"], facing="+z")
for a in (270, 330, 210):
    x, y = (R + 0.11) * math.cos(math.radians(a)), (R + 0.11) * math.sin(math.radians(a))
    bn = kit.banner(f"banner{a}", 0.34, 0.46, at=(0, 0, 0.80), color=P["red"], border=P["gold"], depth=0.02, tip=0.3)
    for p in bn:
        lpm.rotate(p, a + 90, "Z"); lpm.move(p, x, y, 0)
    parts += bn
fence = lpm.finish("SM_ArenaBarricade", parts, P, budget=1500)
lpm.export_unity(fence, out_stem("_work/lpm/env/barricade/SM_ArenaBarricade"), extra=[lpm.collision_box(fence)])
