"""Low-poly Roman villa (exterior kit piece): main block with hipped terracotta roof, side wing, tower, columned portico,
arched door, shuttered windows, stone plinth and steps, garden wall, two cypresses. ~22 x 16 m footprint. Budget 3 000 tris."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN + [("terracotta", "#b3552f", 0.0, 0.85), ("terracotta_dark", "#8a3d22", 0.0, 0.85), ("stucco", "#efe3cf", 0.0, 0.9),
                                     ("shutter", "#4f7a5a", 0.0, 0.8), ("leaf", "#3d6b3a", 0.0, 0.9), ("window", "#2a2622", 0.0, 0.5)])

parts = []
def add(*objs): parts.extend(objs)

# --- ground plinth and entry steps ------------------------------------------------------------------------------------
# plinth covers tower (x -9.8) .. wing (x 11.4) and the portico (y -7.05): 23 x 14.4 m, centred at x = 0.8
add(lpm.box("plinth", (23.0, 14.4, 0.35), at=(0.8, 0, 0), color=P["stone"]))
for i, y in enumerate((-7.7, -8.5, -9.3)):                      # three steps descending away from the plinth front edge (y = -7.2)
    add(lpm.box(f"step{i}", (6.0, 1.0, 0.35 - 0.117 * (i + 1) + 0.01), at=(0, y, 0), color=P["stone_dark"]))

# --- main block --------------------------------------------------------------------------------------------------
Z0 = 0.35
add(lpm.box("main", (12.0, 8.0, 3.4), at=(0, 0, Z0), color=P["stucco"]))
add(lpm.box("main_base", (12.1, 8.1, 0.5), at=(0, 0, Z0 - 0.002), color=P["stone_dark"]))         # dado band
add(lpm.box("main_cornice", (12.4, 8.4, 0.22), at=(0, 0, Z0 + 3.4 - 0.10), color=P["cream"]))
roof_main = lpm.box("roof_main", (13.0, 9.0, 1.7), at=(0, 0, Z0 + 3.4 + 0.12 - 0.01), color=P["terracotta"], taper=(0.42, 0.06))
add(roof_main, lpm.box("ridge_main", (5.8, 0.34, 0.14), at=(0, 0, Z0 + 3.4 + 0.12 + 1.7 - 0.06), color=P["terracotta_dark"]))

# --- side wing (east) with its own hipped roof -------------------------------------------------------------------------
WX = 6.0 + 2.6
add(lpm.box("wing", (5.6, 6.0, 2.8), at=(WX, 0.4, Z0), color=P["stucco"]))
add(lpm.box("wing_base", (5.7, 6.1, 0.5), at=(WX, 0.4, Z0 - 0.002), color=P["stone_dark"]))
add(lpm.box("wing_cornice", (6.0, 6.4, 0.2), at=(WX, 0.4, Z0 + 2.8 - 0.08), color=P["cream"]))
add(lpm.box("roof_wing", (6.4, 6.8, 1.3), at=(WX, 0.4, Z0 + 2.8 + 0.1), color=P["terracotta"], taper=(0.15, 0.12)))

# --- tower (west, taller, pyramid roof) --------------------------------------------------------------------------------
TX = -6.0 - 1.9
add(lpm.box("tower", (3.8, 3.8, 5.6), at=(TX, -0.6, Z0), color=P["stucco"]))
add(lpm.box("tower_base", (3.9, 3.9, 0.5), at=(TX, -0.6, Z0 - 0.002), color=P["stone_dark"]))
add(lpm.box("tower_cornice", (4.2, 4.2, 0.2), at=(TX, -0.6, Z0 + 5.6 - 0.08), color=P["cream"]))
add(lpm.box("roof_tower", (4.5, 4.5, 1.9), at=(TX, -0.6, Z0 + 5.6 + 0.1), color=P["terracotta"], taper=(0.06, 0.06)))

# --- portico: 4 columns, entablature, low pitched porch roof ----------------------------------------------------------------
PY = -4.0 - 1.4          # porch centre y (in front of the main block)
for x in (-2.7, -0.9, 0.9, 2.7):
    add(lpm.lathe(f"colbase{x:+.1f}", [(0.34, 0.0), (0.36, 0.06), (0.30, 0.12), (0.26, 0.16)], segments=8, at=(x, PY - 0.9, Z0), color=P["stone"]))
    add(lpm.prism(f"col{x:+.1f}", 8, 0.24, 2.55, at=(x, PY - 0.9, Z0 + 0.16), color=P["cream"], radius_top=0.21, rotate=22.5))
    add(lpm.lathe(f"colcap{x:+.1f}", [(0.21, 0.0), (0.24, 0.06), (0.32, 0.14), (0.34, 0.2)], segments=8, at=(x, PY - 0.9, Z0 + 2.71), color=P["stone"]))
add(lpm.box("entablature", (7.4, 3.0, 0.4), at=(0, PY, Z0 + 2.9), color=P["cream"]))
add(lpm.box("roof_porch", (7.8, 3.3, 0.9), at=(0, PY - 0.05, Z0 + 3.3 - 0.01), color=P["terracotta"], taper=(0.85, 0.05)))

# --- door (arched, dark inset) and windows ----------------------------------------------------------------------------------
import math
arch = [(-0.7, 0.0), (0.7, 0.0), (0.7, 1.6)] + [(0.7 * math.cos(math.radians(a)), 1.6 + 0.7 * math.sin(math.radians(a))) for a in (30, 60, 90, 120, 150)] + [(-0.7, 1.6)]
door = lpm.sweep("door", arch, depth=0.12, at=(0, -4.0 - 0.02, Z0 + 0.5), color=P["window"], axis="y")
add(door, lpm.sweep("door_frame", [(x * 1.18, z * 1.09 if z > 0 else z) for x, z in arch], depth=0.08, at=(0, -4.0 + 0.0, Z0 + 0.5), color=P["stone"], axis="y"))
def window(name, x, y, z, sy, w=0.9, h=1.2, shutters=True):
    # y is the wall plane; sy = -1 for a wall facing -Y, +1 facing +Y
    add(lpm.box(f"{name}_sill", (w + 0.3, 0.16, 0.1), at=(x, y + sy * 0.0, z - 0.08), color=P["stone"]))
    add(lpm.box(f"{name}_glass", (w, 0.14, h), at=(x, y + sy * 0.0, z), color=P["window"]))
    if shutters:
        add(lpm.box(f"{name}_shL", (0.42, 0.06, h), at=(x - w / 2 - 0.24, y + sy * 0.06, z), color=P["shutter"]))
        add(lpm.box(f"{name}_shR", (0.42, 0.06, h), at=(x + w / 2 + 0.24, y + sy * 0.06, z), color=P["shutter"]))
for x in (-4.6, -3.0, 3.0, 4.6):
    window(f"wf{x:+.1f}", x, -4.0, Z0 + 1.5, -1)
for x in (-4.2, -1.6, 1.6, 4.2):
    window(f"wb{x:+.1f}", x, 4.0, Z0 + 1.5, +1)
for y in (-1.2, 1.2):                                     # wing windows (east face)
    w = lpm.box(f"ww{y:+.1f}_glass", (0.14, 0.9, 1.2), at=(WX + 2.8, 0.4 + y, Z0 + 1.3), color=P["window"]); add(w)
    add(lpm.box(f"ww{y:+.1f}_sill", (0.16, 1.2, 0.1), at=(WX + 2.8, 0.4 + y, Z0 + 1.22), color=P["stone"]))
for z in (Z0 + 1.6, Z0 + 3.9):                           # tower windows (front + west)
    add(lpm.box(f"tw{z:.0f}f_glass", (0.7, 0.14, 1.0), at=(TX, -0.6 - 1.9, z), color=P["window"]))
    add(lpm.box(f"tw{z:.0f}w_glass", (0.14, 0.7, 1.0), at=(TX - 1.9, -0.6, z), color=P["window"]))

# --- gate piers flanking the steps, two cypresses ------------------------------------------------------------------------------
for x in (-3.9, 3.9):
    add(lpm.box(f"pier{x:+.0f}", (0.7, 0.7, 1.5), at=(x, -8.4, 0), color=P["stone_dark"]))
    add(lpm.box(f"piercap{x:+.0f}", (0.9, 0.9, 0.14), at=(x, -8.4, 1.5), color=P["stone"]))
for x, y in ((5.6, -5.4), (-5.0, -5.6)):
    add(lpm.prism(f"trunk{x:+.0f}", 6, 0.12, 0.8, at=(x, y, 0.35 - 0.02), color=P["leather"]))
    add(lpm.lathe(f"cyp{x:+.0f}", [(0.0, 0.0), (0.55, 0.9), (0.62, 2.2), (0.42, 3.6), (0.18, 4.6), (0.0, 5.2)], segments=8, at=(x, y, 0.35 + 0.6), color=P["leaf"]))

villa = lpm.finish("SM_RomanVilla", parts, P, budget=3000)
collider = lpm.collision_box(villa)
lpm.export_unity(villa, out_stem("_work/lpm/roman_villa/SM_RomanVilla"), extra=[collider])
