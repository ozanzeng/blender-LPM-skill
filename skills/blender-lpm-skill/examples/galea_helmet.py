"""Imperial Gallic galea: bowl, brow ridge, neck guard, cheek plates, crest holder. ~0.30 m tall. Budget 1500 tris."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)

bowl = lpm.lathe("bowl", [(0.105, 0.0), (0.108, 0.04), (0.100, 0.09), (0.080, 0.13), (0.045, 0.16), (0.0, 0.17)], segments=12, at=(0, 0, 0.06), color=P["iron"])
lpm.scale(bowl, 1.0, 1.15, 1.0)                                            # skulls are longer than wide
brow = lpm.box("brow", (0.20, 0.03, 0.02), at=(0, -0.115, 0.115), color=P["bronze"], taper=(0.9, 0.6))
neck = lpm.sweep("neck", [(-0.12, 0.0), (0.12, 0.0), (0.15, -0.045), (0.0, -0.065), (-0.15, -0.045)], depth=0.008, at=(0, 0.11, 0.08), color=P["iron"], axis="y")
lpm.rotate(neck, -35, "X", about=(0, 0.11, 0.08))
cheek_l = lpm.sweep("cheek_l", [(-0.02, 0.0), (0.06, 0.0), (0.075, 0.07), (0.05, 0.13), (-0.02, 0.12)], depth=0.008, at=(-0.115, -0.02, -0.06), color=P["bronze"], axis="y")
lpm.rotate(cheek_l, 90, "Z", about=(-0.115, -0.02, -0.06))
cheek_r = lpm.mirror_x(cheek_l)
crest_base = lpm.box("crest_base", (0.03, 0.14, 0.02), at=(0, -0.02, 0.225), color=P["bronze"])
crest = lpm.sweep("crest", [(-0.09, 0.0), (0.09, 0.0), (0.11, 0.05), (0.06, 0.09), (-0.06, 0.09), (-0.11, 0.05)], depth=0.02, at=(0, 0, 0.24), color=P["red"], axis="y")
lpm.rotate(crest, 90, "Z", about=(0, 0, 0.24))
ear_l = lpm.box("ear_l", (0.02, 0.05, 0.05), at=(-0.115, -0.015, 0.06), color=P["bronze"])
ear_r = lpm.mirror_x(ear_l)

helmet = lpm.finish("SM_Galea", [bowl, brow, neck, cheek_l, cheek_r, crest_base, crest, ear_l, ear_r], P, budget=1500)
lpm.export_unity(helmet, out_stem("_work/lpm/galea/SM_Galea"))
