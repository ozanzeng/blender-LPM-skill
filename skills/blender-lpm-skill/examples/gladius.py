"""Roman gladius (Pompeii type): 0.65 m overall, 1200-tri budget, palette material. Blade along +Z, point up."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)

# Blade: waisted double edge, short triangular point. Outline (x, z), z from guard (0) to tip (0.48).
blade_outline = [(-0.024, 0.0), (0.024, 0.0), (0.026, 0.06), (0.022, 0.30), (0.024, 0.38), (0.0, 0.48), (-0.024, 0.38), (-0.022, 0.30), (-0.026, 0.06)]
blade = lpm.sweep("blade", blade_outline, depth=0.007, at=(0, 0, 0.17), color=P["steel"])
# central ridge line: a thin diamond strip on both faces reads as the fuller/ridge in flat shading
ridge = lpm.sweep("ridge", [(-0.006, 0.02), (0.006, 0.02), (0.006, 0.36), (0.0, 0.40), (-0.006, 0.36)], depth=0.010, at=(0, 0, 0.17), color=P["iron"])
# Guard: wooden block, slightly tapered
guard = lpm.box("guard", (0.075, 0.032, 0.035), at=(0, 0, 0.135), color=P["wood"], taper=(0.85, 0.85))
# Grip: octagonal, ribbed with 4 bronze rings
grip = lpm.prism("grip", 8, 0.016, 0.095, at=(0, 0, 0.04), color=P["wood_light"], radius_top=0.015)
rings = [lpm.prism(f"ring{i}", 8, 0.0175, 0.006, at=(0, 0, 0.055 + i * 0.022), color=P["bronze"]) for i in range(4)]
# Pommel: spherical-ish lathe + rivet
pommel = lpm.lathe("pommel", [(0.0, 0.0), (0.024, 0.006), (0.030, 0.020), (0.022, 0.036), (0.0, 0.040)], segments=8, at=(0, 0, 0.0), color=P["wood"])
rivet = lpm.prism("rivet", 6, 0.006, 0.012, at=(0, 0, 0.038), color=P["bronze"])

sword = lpm.finish("SM_Gladius", [blade, ridge, guard, grip, *rings, pommel, rivet], P, budget=1200)
lpm.export_unity(sword, out_stem("_work/lpm/gladius/SM_Gladius"))
