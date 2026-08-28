"""Arena column module: 3.0 m tall Doric-style column with plinth and capital, snaps on a 1 m grid. Budget 600 tris."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)

plinth = lpm.box("plinth", (0.70, 0.70, 0.12), at=(0, 0, 0.0), color=P["stone_dark"])
base = lpm.lathe("base", [(0.32, 0.0), (0.34, 0.05), (0.30, 0.10), (0.26, 0.14)], segments=10, at=(0, 0, 0.12), color=P["stone"])
shaft = lpm.prism("shaft", 10, 0.26, 2.30, at=(0, 0, 0.26), color=P["stone"], radius_top=0.22, rotate=18)
neck = lpm.lathe("neck", [(0.22, 0.0), (0.24, 0.03), (0.30, 0.10), (0.32, 0.14)], segments=10, at=(0, 0, 2.56), color=P["stone"])
abacus = lpm.box("abacus", (0.70, 0.70, 0.14), at=(0, 0, 2.70), color=P["stone_dark"])
band = lpm.box("band", (0.72, 0.72, 0.04), at=(0, 0, 2.84), color=P["sand"])

column = lpm.finish("SM_ArenaColumn", [plinth, base, shaft, neck, abacus, band], P, budget=600)
lpm.export_unity(column, out_stem("_work/lpm/column/SM_ArenaColumn"))
