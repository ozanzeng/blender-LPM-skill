"""Roman loot chest (arca): closed, 1.20 m wide, wood body with bronze straps, hipped lid, rosettes, lock, lion-ring handles,
bronze feet. Budget 2 500 tris (mobile Unity/URP). Delivers .blend + .fbx (+ separate collision box) + palette textures."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
W, D, H, FOOT = 1.14, 0.62, 0.52, 0.07          # body width (handles bring the closed width to 1.20 m), depth, height, foot height
TOP = FOOT + H
LID_H, LID_RIM = 0.16, 0.035

# --- body and lid --------------------------------------------------------------------------------------------
body = lpm.box("body", (W, D, H), at=(0, 0, FOOT), color=P["wood"])
panel_f = lpm.box("panel_f", (W - 0.34, 0.014, H - 0.20), at=(0, -D / 2 - 0.005, FOOT + 0.10), color=P["wood_light"])
panel_b = lpm.box("panel_b", (W - 0.34, 0.014, H - 0.20), at=(0, D / 2 + 0.005, FOOT + 0.10), color=P["wood_light"])
panel_l = lpm.box("panel_l", (0.014, D - 0.22, H - 0.20), at=(-W / 2 - 0.005, 0, FOOT + 0.10), color=P["wood_light"])
panel_r = lpm.box("panel_r", (0.014, D - 0.22, H - 0.20), at=(W / 2 + 0.005, 0, FOOT + 0.10), color=P["wood_light"])
lid_rim = lpm.box("lid_rim", (W + 0.03, D + 0.03, LID_RIM), at=(0, 0, TOP - 0.004), color=P["leather"])          # 4 mm into the body: never coplanar
lid = lpm.box("lid", (W + 0.02, D + 0.02, LID_H), at=(0, 0, TOP + LID_RIM - 0.006), color=P["wood"], taper=(0.90, 0.55))   # hipped lid
lpm.paint(lid, P["wood_light"], where=lambda c, n, i: n.z > 0.9)                                                      # lighter top plank
ridge = lpm.box("ridge", (W * 0.92, 0.06, 0.02), at=(0, 0, TOP + LID_RIM + LID_H - 0.008), color=P["bronze"])         # bronze ridge cap

# --- bronze straps: 3 verticals front/back, continuing up the lid slopes ------------------------------------------
straps = []
for x in (-W * 0.33, 0.0, W * 0.33):
    for y, sy in ((-D / 2 - 0.006, -1), (D / 2 + 0.006, 1)):
        straps.append(lpm.box(f"strap_{x:+.2f}_{sy}", (0.07, 0.014, H + LID_RIM - 0.01), at=(x, y, FOOT), color=P["bronze"]))
        # sloped lid strap: box rotated to follow the hip (angle from lid taper)
        import math
        run = (D + 0.02) * (1 - 0.55) / 2
        ang = math.degrees(math.atan2(LID_H, run))
        length = math.hypot(LID_H, run) - 0.012          # stop just under the ridge cap, no tabs poking above it
        s = lpm.box(f"lidstrap_{x:+.2f}_{sy}", (0.07, 0.014, length), at=(x, 0, 0), color=P["bronze"])
        lpm.rotate(s, sy * (90 - ang), "X", about=(0, 0, 0))
        lpm.move(s, 0, sy * ((D + 0.02) / 2 - 0.004), TOP + LID_RIM - 0.004)
        straps.append(s)
# horizontal bands around the body
bands = [lpm.box(f"band_{k}", (W + 0.012, D + 0.012, 0.05), at=(0, 0, FOOT + z), color=P["bronze"]) for k, z in enumerate((0.03, H - 0.09))]
# rosettes (8-gon bosses) where straps cross the upper band, front and back
rosettes = []
for x in (-W * 0.33, 0.0, W * 0.33):
    for y, sy in ((-D / 2 - 0.02, -1), (D / 2 + 0.02, 1)):
        r = lpm.prism(f"rosette_{x:+.2f}_{sy}", 8, 0.045, 0.014, at=(0, 0, 0), color=P["gold"], radius_top=0.03)
        lpm.rotate(r, -90 * sy, "X"); lpm.move(r, x, y, FOOT + H - 0.065)
        rosettes.append(r)
# --- lock, handles, corners, feet ------------------------------------------------------------------------------------
lock = lpm.box("lock", (0.18, 0.016, 0.16), at=(0, -D / 2 - 0.008, TOP - 0.19), color=P["bronze"])
hasp = lpm.box("hasp", (0.07, 0.024, 0.08), at=(0, -D / 2 - 0.018, TOP - 0.10), color=P["gold"], taper=(0.8, 1.0))
keyhole = lpm.box("keyhole", (0.03, 0.006, 0.045), at=(0, -D / 2 - 0.022, TOP - 0.155), color=P["black"])
handles = []
for sx in (-1, 1):
    plate = lpm.prism(f"hplate_{sx}", 8, 0.07, 0.014, at=(0, 0, 0), color=P["bronze"])
    lpm.rotate(plate, 90, "Y"); lpm.move(plate, sx * (W / 2 + 0.014) - 0.007 * sx, 0, FOOT + H * 0.6)
    ring = lpm.prism(f"hring_{sx}", 8, 0.055, 0.018, at=(0, 0, 0), color=P["gold"], radius_top=0.05)
    lpm.rotate(ring, 90, "Y"); lpm.move(ring, sx * (W / 2 + 0.03) - 0.009 * sx, 0, FOOT + H * 0.6 - 0.06)
    handles += [plate, ring]
corners = [lpm.box(f"corner_{sx}{sy}", (0.10, 0.10, 0.12), at=(sx * (W / 2 - 0.045), sy * (D / 2 - 0.045), FOOT - 0.004), color=P["bronze"]) for sx in (-1, 1) for sy in (-1, 1)]
feet = []
for sx in (-1, 1):
    for sy in (-1, 1):
        f = lpm.lathe(f"foot_{sx}{sy}", [(0.05, 0.0), (0.06, 0.02), (0.045, 0.05), (0.06, FOOT + 0.004)], segments=8, at=(sx * (W / 2 - 0.09), sy * (D / 2 - 0.09), 0), color=P["bronze"])
        feet.append(f)

chest = lpm.finish("SM_RomanChest", [body, panel_f, panel_b, panel_l, panel_r, lid_rim, lid, ridge, *straps, *bands, *rosettes, lock, hasp, keyhole, *handles, *corners, *feet], P, budget=2500)
collider = lpm.collision_box(chest)
lpm.export_unity(chest, out_stem("_work/lpm/roman_chest/SM_RomanChest"), extra=[collider])
