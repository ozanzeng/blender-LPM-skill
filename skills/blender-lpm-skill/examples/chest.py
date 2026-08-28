"""Low-poly treasure / equipment chest: 0.80 x 0.50 x 0.55 m, barrel lid with planks, iron straps with rivets,
lock plate, corner brackets, feet, side handles, raised panels. Budget 800 tris."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender does not add the script dir
from _common import lpm, out_stem

lpm.reset()
P = lpm.Palette(lpm.PALETTE_ROMAN)
W, D, H_BODY, LID_R, FOOT = 0.80, 0.50, 0.36, 0.25, 0.05
TOP = FOOT + H_BODY

body = lpm.box("body", (W, D, H_BODY), at=(0, 0, FOOT), color=P["wood"])
# raised panels on front/back/sides (lighter wood) - cheap "carpentry" read
panels = [
    lpm.box("panel_f", (W - 0.30, 0.012, H_BODY - 0.16), at=(0, -D / 2 - 0.004, FOOT + 0.08), color=P["wood_light"]),
    lpm.box("panel_b", (W - 0.30, 0.012, H_BODY - 0.16), at=(0, D / 2 + 0.004, FOOT + 0.08), color=P["wood_light"]),
    lpm.box("panel_l", (0.012, D - 0.16, H_BODY - 0.16), at=(-W / 2 - 0.004, 0, FOOT + 0.08), color=P["wood_light"]),
    lpm.box("panel_r", (0.012, D - 0.16, H_BODY - 0.16), at=(W / 2 + 0.004, 0, FOOT + 0.08), color=P["wood_light"]),
]
# barrel lid (10-sided prism on its side, flattened) painted as alternating planks
LID_LEN = W + 0.012                                   # 6 mm overhang each side: never leave two parts coplanar (Cycles renders the seam black)
lid = lpm.prism("lid", 10, LID_R, LID_LEN, at=(0, 0, 0), color=P["wood_light"])
lpm.rotate(lid, 90, "Y"); lpm.scale(lid, 1.0, 1.0, 0.7, about=(0, 0, 0)); lpm.move(lid, -LID_LEN / 2, 0, TOP)
lpm.paint(lid, P["wood"], where=lambda c, n, i: i % 2 == 0 and i < 10)          # every other facet darker
lid_rim = lpm.box("lid_rim", (W + 0.02, D + 0.02, 0.03), at=(0, 0, TOP - 0.015), color=P["leather"])
# iron straps: front/back verticals + over the lid, with bronze rivets
straps, rivets = [], []
for x in (-W * 0.3, W * 0.3):
    straps.append(lpm.box(f"strap_f{x:+.2f}", (0.06, 0.012, H_BODY), at=(x, -D / 2 - 0.005, FOOT), color=P["iron"]))
    straps.append(lpm.box(f"strap_b{x:+.2f}", (0.06, 0.012, H_BODY), at=(x, D / 2 + 0.005, FOOT), color=P["iron"]))
    arc = lpm.prism(f"strap_lid{x:+.2f}", 10, LID_R + 0.008, 0.06, at=(0, 0, 0), color=P["iron"])
    lpm.rotate(arc, 90, "Y"); lpm.scale(arc, 1.0, 1.0, 0.7, about=(0, 0, 0)); lpm.move(arc, x - 0.03, 0, TOP)
    straps.append(arc)
    for z in (FOOT + 0.05, TOP - 0.06):
        for y, sy in ((-D / 2 - 0.011, -1), (D / 2 + 0.011, 1)):
            r = lpm.prism(f"rivet{x:+.2f}{z:.2f}{sy}", 6, 0.012, 0.008, at=(0, 0, 0), color=P["bronze"])
            lpm.rotate(r, -90 * sy, "X"); lpm.move(r, x, y, z)
            rivets.append(r)
# lock plate, hasp, keyhole
lock = lpm.box("lock", (0.14, 0.014, 0.12), at=(0, -D / 2 - 0.006, TOP - 0.10), color=P["iron"])
hasp = lpm.box("hasp", (0.06, 0.022, 0.06), at=(0, -D / 2 - 0.014, TOP - 0.055), color=P["bronze"], taper=(0.8, 1.0))
keyhole = lpm.box("keyhole", (0.025, 0.006, 0.035), at=(0, -D / 2 - 0.02, TOP - 0.09), color=P["black"])
# corner brackets, feet, handles
corners = [lpm.box(f"corner_{sx}{sy}", (0.08, 0.08, 0.09), at=(sx * (W / 2 - 0.035), sy * (D / 2 - 0.035), FOOT), color=P["bronze"]) for sx in (-1, 1) for sy in (-1, 1)]
feet = [lpm.box(f"foot_{sx}{sy}", (0.10, 0.10, FOOT), at=(sx * (W / 2 - 0.07), sy * (D / 2 - 0.07), 0), color=P["stone_dark"]) for sx in (-1, 1) for sy in (-1, 1)]
handles = []
for sx in (-1, 1):
    h = lpm.prism(f"handle_{sx}", 8, 0.045, 0.02, at=(0, 0, 0), color=P["bronze"])
    lpm.rotate(h, 90, "Y"); lpm.move(h, sx * (W / 2 + 0.012) - 0.01, 0, FOOT + H_BODY * 0.55)   # 2 mm proud of the side, not coplanar
    handles.append(h)

chest = lpm.finish("SM_Chest", [body, *panels, lid, lid_rim, *straps, *rivets, lock, hasp, keyhole, *corners, *feet, *handles], P, budget=800)
lpm.export_unity(chest, out_stem("_work/lpm/chest/SM_Chest"))
