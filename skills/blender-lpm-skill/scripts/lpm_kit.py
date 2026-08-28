"""
lpm_kit.py - reusable Roman / stylized-kit builders on top of lpm.py. Import next to lpm:

    import lpm, lpm_kit as kit
    parts += kit.banner("flag", 0.6, 1.0, at=(0, -0.5, 1.0), color=P["red"], border=P["gold"])

Every helper returns a LIST of parts (already coloured) ready for lpm.finish(). Metres, Z up, front = -Y.
"""
from __future__ import annotations

import math
import random

from mathutils import Vector

import lpm


def ring_of(n, radius, maker, at=(0, 0, 0), start_deg=0.0):
    """Place n items on a circle: maker(i, x, y, angle_deg) -> part or list of parts."""
    out = []
    for i in range(n):
        a = start_deg + 360.0 * i / n
        x = at[0] + radius * math.cos(math.radians(a))
        y = at[1] + radius * math.sin(math.radians(a))
        r = maker(i, x, y, a)
        out += r if isinstance(r, list) else [r]
    return out


def wall_ring(name, n, radius, height, thickness, at=(0, 0, 0), color=0, top_taper=1.0):
    """Closed polygonal wall (well, barricade, tower) made of n flat segments."""
    seg = 2 * radius * math.tan(math.pi / n) + 0.002
    def mk(i, x, y, a):
        b = lpm.box(f"{name}_{i}", (seg, thickness, height), at=(0, 0, 0), color=color, taper=(top_taper, 1.0))
        lpm.rotate(b, a + 90, "Z")
        lpm.move(b, x, y, at[2])
        return b
    return ring_of(n, radius, mk, at=(at[0], at[1], 0))


def banner(name, width, height, at=(0, 0, 0), color=0, border=None, depth=0.02, tip=0.25, border_w=0.03):
    """Hanging cloth with a V tip (Roman vexillum-style), facing -Y. `at` = top-centre. Optional border cloth behind it."""
    w, h, t = width / 2, height, height * tip
    outline = [(-w, 0.0), (w, 0.0), (w, -h + t), (0.0, -h), (-w, -h + t)]
    parts = [lpm.sweep(f"{name}_cloth", outline, depth, at=at, color=color, axis="y")]
    if border is not None:
        bw = border_w
        outline_b = [(-w - bw, bw), (w + bw, bw), (w + bw, -h + t - bw * 0.4), (0.0, -h - bw * 1.4), (-w - bw, -h + t - bw * 0.4)]
        parts.append(lpm.sweep(f"{name}_border", outline_b, depth * 0.6, at=(at[0], at[1] + depth * 0.5, at[2]), color=border, axis="y"))
    return parts


def medallion(name, radius, at=(0, 0, 0), color=0, center=None, thickness=0.03, facing="-y"):
    """Round boss / medallion on a wall: 8-gon disc + smaller centre disc. facing: -y, +y, -x, +x, +z."""
    ring = lpm.prism(f"{name}_ring", 8, radius, thickness, at=(0, 0, 0), color=color, rotate=22.5)
    parts = [ring]
    if center is not None:
        parts.append(lpm.prism(f"{name}_center", 8, radius * 0.55, thickness * 1.6, at=(0, 0, 0), color=center, rotate=22.5))
    rot = {"-y": (90, "X"), "+y": (-90, "X"), "-x": (-90, "Y"), "+x": (90, "Y"), "+z": (0, "Z")}[facing]
    for p in parts:
        lpm.rotate(p, rot[0], rot[1])
        lpm.move(p, *at)
    return parts


def rivets(name, points, radius=0.02, height=0.012, color=0, facing="-y"):
    """Small hex studs at world points, facing a wall direction."""
    rot = {"-y": (90, "X"), "+y": (-90, "X"), "-x": (-90, "Y"), "+x": (90, "Y"), "+z": (0, "Z")}[facing]
    out = []
    for i, p in enumerate(points):
        r = lpm.prism(f"{name}_{i}", 6, radius, height, at=(0, 0, 0), color=color)
        lpm.rotate(r, rot[0], rot[1]); lpm.move(r, *p)
        out.append(r)
    return out


def meander_band(name, length, height, depth, at=(0, 0, 0), bg=0, fg=1, n=8, facing="-y"):
    """Greek-key band simplified to alternating raised squares on a strip. `at` = centre of the strip's bottom edge on the wall."""
    strip = lpm.box(f"{name}_bg", (length, depth, height), at=(0, 0, 0), color=bg)
    parts = [strip]
    cell = length / n
    for i in range(n):
        if i % 2 == 0:
            parts.append(lpm.box(f"{name}_k{i}", (cell * 0.55, depth * 0.6, height * 0.55), at=(-length / 2 + cell * (i + 0.5), -depth * 0.55, height * 0.22), color=fg))
    rot = {"-y": 0, "+y": 180, "-x": -90, "+x": 90}[facing]
    for p in parts:
        if rot:
            lpm.rotate(p, rot, "Z")
        lpm.move(p, *at)
    return parts


def block_course(name, length, height, depth, at=(0, 0, 0), n=5, color=0, seed=1, jitter=0.15, gap=0.02, facing="-y"):
    """Row of stone blocks with slight size jitter (deterministic). `at` = centre of the course's bottom front edge."""
    rnd = random.Random(seed)
    parts, x = [], -length / 2
    base = (length - gap * (n - 1)) / n
    widths = [base * (1 + rnd.uniform(-jitter, jitter)) for _ in range(n)]
    scale = (length - gap * (n - 1)) / sum(widths)
    for i, w in enumerate(widths):
        w *= scale
        d = depth * (1 + rnd.uniform(-jitter * 0.5, jitter * 0.5))
        parts.append(lpm.box(f"{name}_{i}", (w, d, height), at=(x + w / 2, -(d - depth) / 2, 0), color=color))
        x += w + gap
    rot = {"-y": 0, "+y": 180, "-x": -90, "+x": 90}[facing]
    for p in parts:
        if rot:
            lpm.rotate(p, rot, "Z")
        lpm.move(p, *at)
    return parts


def flame(name, height, at=(0, 0, 0), color=0, core=None, width=None):
    """Two crossed spiky sweeps that read as a low-poly flame from any angle. `at` = base centre."""
    w = width or height * 0.55
    hw = w / 2
    outline = [(-hw, 0.0), (hw, 0.0), (hw * 0.75, height * 0.35), (hw * 0.35, height * 0.55), (hw * 0.25, height * 0.8), (0.0, height),
               (-hw * 0.2, height * 0.7), (-hw * 0.45, height * 0.6), (-hw * 0.8, height * 0.3)]
    a = lpm.sweep(f"{name}_a", outline, 0.02, at=at, color=color, axis="y")
    b = lpm.sweep(f"{name}_b", outline, 0.02, at=at, color=color, axis="y")
    lpm.rotate(b, 90, "Z", about=at)
    parts = [a, b]
    if core is not None:
        inner = [(x * 0.5, z * 0.6) for x, z in outline]
        c = lpm.sweep(f"{name}_core", inner, 0.03, at=at, color=core, axis="y")
        d = lpm.sweep(f"{name}_core2", inner, 0.03, at=at, color=core, axis="y"); lpm.rotate(d, 90, "Z", about=at)
        parts += [c, d]
    return parts


def handle_arc(name, radius, thickness, arc_deg, at=(0, 0, 0), color=0, plane="xz", segments=6, flip=False):
    """Curved handle / ring segment (a bent bar). The arc starts at `at`, its chord runs along +Y (plane 'xy') or +Z
    (plane 'xz'), and it bulges toward +X (toward -X with flip=True). arc_deg=180 gives a half loop whose ends are
    2*radius apart."""
    return [_arc_bar(name, radius, thickness, arc_deg, at, color, plane, segments, flip)]


def _arc_bar(name, radius, thickness, arc_deg, at, color, plane, segments, flip):
    """Deterministic arc: polyline of `segments` boxes is overkill; build the ring segment as a bent grid box in the XY
    plane with the chord on +Y and the bulge on +X, then rotate into the requested plane."""
    length = radius * math.radians(arc_deg)
    bar = lpm.grid_box(f"{name}", (length, thickness, thickness), at=(0, 0, -thickness / 2), color=color, nx=segments)
    # grid_box is centred on x=0: shift so it starts at x=0, then bend around Z: x -> angle, y -> R(1-cos): bulge toward +Y
    lpm.move(bar, length / 2, 0, 0)
    lpm.bend(bar, radius, axis="z")
    # now: start (0,0), end (R sin a, R(1-cos a)); for 180 deg: end (0, 2R); bulge toward +X. Chord along +Y. Good.
    if plane == "xz":
        lpm.rotate(bar, 90, "X", about=(0, 0, 0))       # y -> z: chord along +Z, bulge stays +X
    if flip:
        lpm.rotate(bar, 180, "Z" if plane == "xz" else "Z", about=(0, 0, 0))   # bulge toward -X
    lpm.move(bar, *at)
    return bar


def column(name, radius, height, at=(0, 0, 0), color=0, base=None, cap=None, sides=10, fluted=False):
    """Simple Doric/Tuscan column with optional base and capital colours."""
    parts = []
    z = at[2]
    if base is not None:
        parts.append(lpm.box(f"{name}_plinth", (radius * 2.6, radius * 2.6, radius * 0.5), at=(at[0], at[1], z), color=base)); z += radius * 0.5
        parts.append(lpm.lathe(f"{name}_base", [(radius * 1.25, 0), (radius * 1.3, radius * 0.2), (radius * 1.05, radius * 0.4), (radius, radius * 0.5)], segments=sides, at=(at[0], at[1], z), color=base)); z += radius * 0.5
    shaft_h = height - (z - at[2]) - (radius * 0.6 if cap is not None else 0)
    parts.append(lpm.prism(f"{name}_shaft", sides, radius, shaft_h, at=(at[0], at[1], z), color=color, radius_top=radius * 0.88, rotate=180 / sides))
    if fluted:
        for i in range(sides):
            a = math.radians(360 * i / sides)
            parts.append(lpm.box(f"{name}_flute{i}", (radius * 0.18, radius * 0.12, shaft_h * 0.9), at=(at[0] + radius * 0.96 * math.cos(a), at[1] + radius * 0.96 * math.sin(a), z + shaft_h * 0.05), color=color))
    z += shaft_h
    if cap is not None:
        parts.append(lpm.lathe(f"{name}_cap", [(radius * 0.88, 0), (radius * 1.1, radius * 0.25), (radius * 1.3, radius * 0.4)], segments=sides, at=(at[0], at[1], z), color=cap))
        parts.append(lpm.box(f"{name}_abacus", (radius * 2.7, radius * 2.7, radius * 0.2), at=(at[0], at[1], z + radius * 0.4), color=cap))
    return parts


def plinth_steps(name, width, depth, heights, at=(0, 0, 0), color=0, inset=0.12):
    """Stacked stepped base: list of heights bottom->top, each level inset."""
    parts, z, w, d = [], at[2], width, depth
    for i, h in enumerate(heights):
        parts.append(lpm.box(f"{name}_{i}", (w, d, h), at=(at[0], at[1], z), color=color))
        z += h; w -= inset * 2; d -= inset * 2
    return parts
