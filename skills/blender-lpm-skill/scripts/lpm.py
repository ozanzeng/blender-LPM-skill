"""
lpm.py - Low Poly Modelling toolkit for Blender (import inside Blender, headless or GUI).

    import sys; sys.path.insert(0, r"<skill>/scripts"); import lpm
    lpm.reset()
    P = lpm.Palette([("steel", "#c9ccd1", 1.0, 0.35), ("wood", "#7a4a22", 0.0, 0.7)])
    blade = lpm.sweep("blade", [(-0.025, 0), (0.025, 0), (0.02, 0.45), (0, 0.5), (-0.02, 0.45)], depth=0.006, color=P["steel"])
    grip  = lpm.prism("grip", sides=8, radius=0.015, height=0.10, at=(0, 0, -0.1), color=P["wood"])
    sword = lpm.finish("SM_Gladius", [blade, grip], P, budget=1200)
    lpm.export_unity(sword, "out/gladius")          # .blend + .fbx + tex/<name>_BaseColor.png (+ _MaskMap.png)

Design rules baked in: flat shading, every part carries an integer face attribute `lpm_color` pointing to a
palette cell; `finish()` joins parts, applies transforms, puts the base on z=0, writes UVs so each face sits in
the centre of its palette cell, builds ONE material (palette BaseColor + palette MaskMap), checks the budget.
All builders take metres. Z is up, -Y is the front (Blender convention; the Unity exporter converts).
"""
from __future__ import annotations

import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

__all__ = ["reset", "Palette", "box", "grid_box", "prism", "lathe", "sweep", "plate", "bend", "mirror_x", "move", "rotate",
           "scale", "taper", "paint", "finish", "collision_box", "tri_count", "report", "export_unity", "save", "PALETTE_ROMAN"]

# A ready-made Roman / gladiator palette: (name, hex, metallic, roughness)
PALETTE_ROMAN = [
    ("iron", "#8f949a", 1.0, 0.45), ("steel", "#c9ccd1", 1.0, 0.30), ("bronze", "#b0783a", 1.0, 0.40),
    ("gold", "#d8a93a", 1.0, 0.35), ("wood", "#7a4a22", 0.0, 0.75), ("wood_light", "#a9743c", 0.0, 0.75),
    ("leather", "#5a3a25", 0.0, 0.65), ("red", "#b3302e", 0.0, 0.70), ("crimson", "#6e1a22", 0.0, 0.70),
    ("cream", "#e8dcc4", 0.0, 0.80), ("sand", "#d9c28f", 0.0, 0.90), ("stone", "#b9b2a4", 0.0, 0.90),
    ("stone_dark", "#7d776c", 0.0, 0.90), ("skin", "#d9a075", 0.0, 0.60), ("black", "#1e1c1a", 0.0, 0.60),
    ("white", "#f2f0ea", 0.0, 0.80),
]


# --------------------------------------------------------------------------- scene / palette

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _col("COL_LowPoly")


def _col(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


class Palette:
    """Ordered colour cells. Index by name: P["steel"] -> cell index."""

    def __init__(self, entries, cell=16):
        # (name, hex, metallic, roughness, emission_strength) - emission optional (flames, embers, glowing runes)
        self.entries = [(e[0], e[1], float(e[2]) if len(e) > 2 else 0.0, float(e[3]) if len(e) > 3 else 0.8, float(e[4]) if len(e) > 4 else 0.0) for e in entries]
        self.cell = cell
        self.cols = max(1, min(8, len(self.entries)))
        self.rows = math.ceil(len(self.entries) / self.cols)
        self._index = {e[0]: i for i, e in enumerate(self.entries)}

    def __getitem__(self, name):
        return self._index[name]

    def uv(self, index):
        r, c = divmod(index, self.cols)
        return ((c + 0.5) / self.cols, 1.0 - (r + 0.5) / self.rows)

    def images(self, name):
        w, h = self.cols * self.cell, self.rows * self.cell
        base = bpy.data.images.new(f"{name}_BaseColor", w, h, alpha=False)
        mask = bpy.data.images.new(f"{name}_MaskMap", w, h, alpha=True)
        mask.colorspace_settings.name = "Non-Color"
        bpx = [0.0] * (w * h * 4)
        mpx = [0.0] * (w * h * 4)
        for i, (_n, hx, metal, rough, _em) in enumerate(self.entries):
            r, c = divmod(i, self.cols)
            lin = [_srgb_to_linear(v) for v in _hex(hx)]
            for y in range(r * self.cell, (r + 1) * self.cell):
                yy = h - 1 - y
                for x in range(c * self.cell, (c + 1) * self.cell):
                    o = (yy * w + x) * 4
                    bpx[o:o + 4] = [lin[0], lin[1], lin[2], 1.0]
                    mpx[o:o + 4] = [metal, 1.0, 0.0, 1.0 - rough]      # R metal, G AO, B -, A smoothness
        base.pixels = bpx
        mask.pixels = mpx
        base.pack(); mask.pack()
        return base, mask

    def definitions(self):
        """PBR *definitions* (no baked textures): one entry per palette cell, Unity/URP Lit parameter names."""
        return [{"cell": i, "name": n, "baseColor": hx, "metallic": m, "smoothness": round(1.0 - r, 3), "roughness": r,
                 "emission": em, "uv_center": [round(v, 4) for v in self.uv(i)]} for i, (n, hx, m, r, em) in enumerate(self.entries)]

    def material(self, name):
        base, mask = self.images(name)
        m = bpy.data.materials.new(f"M_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = base; tb.interpolation = "Closest"
        tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = mask; tm.interpolation = "Closest"
        nt.links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Red"], bsdf.inputs["Metallic"])
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(tm.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
        if any(e[4] > 0 for e in self.entries):        # emission from the base colour, masked per cell via a second palette image
            emi = bpy.data.images.new(f"{name}_Emission", base.size[0], base.size[1], alpha=False)
            px = [0.0] * (base.size[0] * base.size[1] * 4)
            w = base.size[0]
            for i, (_n, hx, _m, _r, em) in enumerate(self.entries):
                if em <= 0: continue
                r_, c_ = divmod(i, self.cols); lin = [_srgb_to_linear(v) * em for v in _hex(hx)]
                for y in range(r_ * self.cell, (r_ + 1) * self.cell):
                    yy = base.size[1] - 1 - y
                    for x in range(c_ * self.cell, (c_ + 1) * self.cell):
                        o = (yy * w + x) * 4; px[o:o + 4] = [lin[0], lin[1], lin[2], 1.0]
            emi.pixels = px; emi.pack()
            te = nt.nodes.new("ShaderNodeTexImage"); te.image = emi; te.interpolation = "Closest"
            nt.links.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 1.0
            m["lpm_emission_image"] = emi.name
        m["lpm_base_image"] = base.name; m["lpm_mask_image"] = mask.name
        m["lpm_palette_json"] = json.dumps(self.definitions())
        return m


# --------------------------------------------------------------------------- mesh helpers

def _object(name, bm, color):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    _col("COL_LowPoly").objects.link(ob)
    attr = me.attributes.new("lpm_color", "INT", "FACE")
    for i in range(len(me.polygons)):
        attr.data[i].value = int(color)
    for p in me.polygons:
        p.use_smooth = False
    return ob


def _bm_from(verts, faces):
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(v)) for v in verts]
    bm.verts.ensure_lookup_table()
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def box(name, size, at=(0, 0, 0), color=0, taper=(1.0, 1.0)):
    """Axis-aligned box; `size` is (x, y, z) in metres, `at` is the centre of the base; taper scales the top face."""
    sx, sy, sz = size
    tx, ty = taper
    x, y, z = at
    b = [(x - sx / 2, y - sy / 2, z), (x + sx / 2, y - sy / 2, z), (x + sx / 2, y + sy / 2, z), (x - sx / 2, y + sy / 2, z)]
    t = [(x - sx * tx / 2, y - sy * ty / 2, z + sz), (x + sx * tx / 2, y - sy * ty / 2, z + sz), (x + sx * tx / 2, y + sy * ty / 2, z + sz), (x - sx * tx / 2, y + sy * ty / 2, z + sz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return _object(name, _bm_from(b + t, faces), color)


def grid_box(name, size, at=(0, 0, 0), color=0, nx=8, nz=1):
    """Box whose front/back faces are an nx x nz grid so it can be bent or tapered smoothly (shield bodies, curved bands)."""
    sx, sy, sz = size
    x0, y0, z0 = at
    verts, faces = [], []
    def ring(k):
        return [(x0 - sx / 2 + sx * i / nx, y0 - sy / 2, z0 + sz * k / nz) for i in range(nx + 1)] + \
               [(x0 - sx / 2 + sx * i / nx, y0 + sy / 2, z0 + sz * k / nz) for i in range(nx + 1)]
    for k in range(nz + 1):
        verts += ring(k)
    w = 2 * (nx + 1)
    for k in range(nz):
        a, b = k * w, (k + 1) * w
        for i in range(nx):
            faces.append((a + i, b + i, b + i + 1, a + i + 1))                          # front (-y): outward
            fb, bb = a + nx + 1, b + nx + 1
            faces.append((fb + i + 1, bb + i + 1, bb + i, fb + i))                     # back (+y)
        faces.append((a + nx + 1, b + nx + 1, b, a))                                   # left end (-x)
        faces.append((a + nx, b + nx, b + 2 * nx + 1, a + 2 * nx + 1))                 # right end (+x)
    for i in range(nx):                                                                # bottom and top
        faces.append((i + nx + 1, i + nx + 2, i + 1, i))
        t = nz * w
        faces.append((t + i, t + i + 1, t + i + nx + 2, t + i + nx + 1))
    return _object(name, _bm_from(verts, faces), color)


def prism(name, sides, radius, height, at=(0, 0, 0), color=0, radius_top=None, rotate=0.0, cap=True):
    """Regular n-gon prism standing on its base at `at`."""
    rt = radius if radius_top is None else radius_top
    x, y, z = at
    verts = []
    for rr, zz in ((radius, z), (rt, z + height)):
        for i in range(sides):
            a = math.radians(rotate) + 2 * math.pi * i / sides
            verts.append((x + rr * math.cos(a), y + rr * math.sin(a), zz))
    faces = [(i, (i + 1) % sides, sides + (i + 1) % sides, sides + i) for i in range(sides)]
    if cap:
        faces += [tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))]
    return _object(name, _bm_from(verts, faces), color)


def lathe(name, profile, segments=8, at=(0, 0, 0), color=0):
    """Revolve a (radius, z) profile around Z. Radius 0 points become poles. Profile goes bottom -> top."""
    x, y, z = at
    verts, rings = [], []
    for r, zz in profile:
        if r <= 1e-6:
            verts.append((x, y, z + zz)); rings.append([len(verts) - 1])
        else:
            base = len(verts)
            verts += [(x + r * math.cos(2 * math.pi * i / segments), y + r * math.sin(2 * math.pi * i / segments), z + zz) for i in range(segments)]
            rings.append(list(range(base, base + segments)))
    faces = []
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            faces += [(a[0], b[(i + 1) % segments], b[i]) for i in range(segments)]
        elif len(b) == 1:
            faces += [(a[i], a[(i + 1) % segments], b[0]) for i in range(segments)]
        else:
            faces += [(a[i], a[(i + 1) % segments], b[(i + 1) % segments], b[i]) for i in range(segments)]
    if len(rings[0]) > 1:
        faces.append(tuple(reversed(rings[0])))
    if len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    return _object(name, _bm_from(verts, faces), color)


def sweep(name, outline, depth, at=(0, 0, 0), color=0, axis="y"):
    """Extrude a closed 2D outline. axis='y': outline is (x, z), extruded along Y by `depth` (a blade, a plate seen from the front).
    axis='z': outline is (x, y), extruded up by `depth` (a floor slab, a step)."""
    x0, y0, z0 = at
    n = len(outline)
    if axis == "y":
        front = [(x0 + px, y0 - depth / 2, z0 + pz) for px, pz in outline]
        back = [(x0 + px, y0 + depth / 2, z0 + pz) for px, pz in outline]
    else:
        front = [(x0 + px, y0 + py, z0) for px, py in outline]
        back = [(x0 + px, y0 + py, z0 + depth) for px, py in outline]
    bm = bmesh.new()
    vf = [bm.verts.new(Vector(v)) for v in front]
    vb = [bm.verts.new(Vector(v)) for v in back]
    bm.verts.ensure_lookup_table()
    cap_f = bm.faces.new(vf); cap_b = bm.faces.new(list(reversed(vb)))
    for i in range(n):
        bm.faces.new([vf[i], vb[i], vb[(i + 1) % n], vf[(i + 1) % n]])
    bmesh.ops.triangulate(bm, faces=[cap_f, cap_b], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object(name, bm, color)


def plate(name, width, height, thickness, corner=0.0, at=(0, 0, 0), color=0, corner_cuts=2):
    """Front-facing plate (x = width, z = height, y = thickness) with chamfered/rounded corners; base at `at`."""
    w, h = width / 2, height
    pts = []
    def arc(cx, cz, a0, a1):
        for k in range(corner_cuts + 1):
            a = math.radians(a0 + (a1 - a0) * k / corner_cuts)
            pts.append((cx + corner * math.cos(a), cz + corner * math.sin(a)))
    if corner > 0:
        arc(-w + corner, corner, 180, 270); arc(w - corner, corner, 270, 360)
        arc(w - corner, h - corner, 0, 90); arc(-w + corner, h - corner, 90, 180)
    else:
        pts = [(-w, 0), (w, 0), (w, h), (-w, h)]
    return sweep(name, pts, thickness, at=at, color=color, axis="y")


def bend(ob, radius, axis="z"):
    """Cylindrical bend: x -> angle around a vertical (axis='z') or horizontal (axis='x') axis at the given radius. Curves shields."""
    me = ob.data
    for v in me.vertices:
        if axis == "z":
            t = v.co.x / radius
            v.co.x, v.co.y = radius * math.sin(t), v.co.y + radius * (1 - math.cos(t))
        else:
            t = v.co.z / radius
            v.co.z, v.co.y = radius * math.sin(t), v.co.y + radius * (1 - math.cos(t))
    me.update()
    return ob


def mirror_x(ob, merge=True):
    """Duplicate across X (symmetry) - returns the mirrored copy as a new part."""
    new = ob.copy(); new.data = ob.data.copy(); new.name = ob.name + "_R"
    _col("COL_LowPoly").objects.link(new)
    new.data.transform(Matrix.Scale(-1, 4, Vector((1, 0, 0))))
    new.data.flip_normals()
    return new


def move(ob, dx=0, dy=0, dz=0):
    ob.data.transform(Matrix.Translation(Vector((dx, dy, dz)))); return ob


def rotate(ob, deg, axis="Z", about=(0, 0, 0)):
    p = Vector(about)
    ob.data.transform(Matrix.Translation(p) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-p)); return ob


def scale(ob, sx=1, sy=1, sz=1, about=(0, 0, 0)):
    p = Vector(about)
    ob.data.transform(Matrix.Translation(p) @ Matrix.Diagonal(Vector((sx, sy, sz, 1))) @ Matrix.Translation(-p)); return ob


def taper(ob, factor_top, z0, z1, axes="xy"):
    """Linear taper between heights z0..z1: scale in x/y goes from 1 at z0 to factor_top at z1."""
    for v in ob.data.vertices:
        t = min(max((v.co.z - z0) / max(z1 - z0, 1e-9), 0), 1)
        f = 1 + (factor_top - 1) * t
        if "x" in axes: v.co.x *= f
        if "y" in axes: v.co.y *= f
    ob.data.update(); return ob


def paint(ob, color, where=None):
    """Recolour faces of a part before finish(). `where(center, normal, index)` -> bool selects faces (all when None).
    Examples: alternate planks  where=lambda c, n, i: i % 2 == 0 ; front faces  where=lambda c, n, i: n.y < -0.5 ;
    the top  where=lambda c, n, i: n.z > 0.5 ; below a height  where=lambda c, n, i: c.z < 0.2"""
    me = ob.data
    attr = me.attributes.get("lpm_color") or me.attributes.new("lpm_color", "INT", "FACE")
    n = 0
    for poly in me.polygons:
        if where is None or where(poly.center.copy(), poly.normal.copy(), poly.index):
            attr.data[poly.index].value = int(color)
            n += 1
    return n


# --------------------------------------------------------------------------- finishing

def tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def finish(name, parts, palette, budget=None, ground=True, center=True, merge_distance=0.0005):
    """Join parts into one flat-shaded object (welding only inside each part), apply transforms, ground it,
    write palette UVs from the `lpm_color` face attribute, assign ONE palette material, check the budget."""
    # Weld PER PART, never across parts: parts that touch at exact coordinates (a lid cap on a body edge) must
    # stay separate shells, otherwise the merged faces flip normals and render black.
    for p in parts:
        bm = bmesh.new(); bm.from_mesh(p.data)
        if merge_distance:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_distance)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(p.data); bm.free()
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name; ob.data.name = name
    me = ob.data
    lo = min((v.co.z for v in me.vertices), default=0)
    if ground and abs(lo) > 1e-6:
        me.transform(Matrix.Translation(Vector((0, 0, -lo))))
    if center:
        xs = [v.co.x for v in me.vertices]
        cx = (min(xs) + max(xs)) / 2
        if abs(cx) > 1e-6:
            me.transform(Matrix.Translation(Vector((-cx, 0, 0))))
    ob.matrix_world = Matrix.Identity(4)
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    attr = me.attributes.get("lpm_color")
    for poly in me.polygons:
        idx = attr.data[poly.index].value if attr else 0
        u, v = palette.uv(idx)
        for li in poly.loop_indices:
            uv.data[li].uv = (u, v)
        poly.use_smooth = False
    me.materials.clear()
    me.materials.append(palette.material(name))
    for p in me.polygons:
        p.material_index = 0
    tris = tri_count(ob)
    ob["lpm_tris"] = tris
    if budget is not None:
        ob["lpm_budget"] = budget
        print(f"[lpm] {name}: {tris} tris / budget {budget} -> {'OK' if tris <= budget else 'OVER BUDGET'}")
    return ob


def collision_box(ob, name=None, margin=0.0, collection="COL_Collision"):
    """Simple 12-triangle collision proxy around `ob` (Unity: add a MeshCollider (convex) or BoxCollider to it).
    Parented to the asset, no material, wire display, in its own collection. Name defaults to <asset>_COL."""
    name = name or f"{ob.name}_COL"
    lo = Vector((min(v.co.x for v in ob.data.vertices) - margin, min(v.co.y for v in ob.data.vertices) - margin, min(v.co.z for v in ob.data.vertices) - margin))
    hi = Vector((max(v.co.x for v in ob.data.vertices) + margin, max(v.co.y for v in ob.data.vertices) + margin, max(v.co.z for v in ob.data.vertices) + margin))
    verts = [(lo.x, lo.y, lo.z), (hi.x, lo.y, lo.z), (hi.x, hi.y, lo.z), (lo.x, hi.y, lo.z),
             (lo.x, lo.y, hi.z), (hi.x, lo.y, hi.z), (hi.x, hi.y, hi.z), (lo.x, hi.y, hi.z)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    bm = _bm_from(verts, faces); bm.to_mesh(me); bm.free()
    col = bpy.data.objects.new(name, me)
    _col(collection).objects.link(col)
    col.display_type = "WIRE"
    col.hide_render = True                      # never in renders; still exported to FBX
    col.parent = ob
    col["lpm_collision"] = True
    return col


def report(ob):
    d = ob.dimensions
    return {"name": ob.name, "tris": tri_count(ob), "verts": len(ob.data.vertices), "dims_m": [round(d.x, 4), round(d.y, 4), round(d.z, 4)],
            "budget": ob.get("lpm_budget"), "within_budget": (ob.get("lpm_budget") is None) or tri_count(ob) <= ob["lpm_budget"],
            "materials": [m.name for m in ob.data.materials]}


def save(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path), relative_remap=True)
    return os.path.abspath(path)


def export_unity(ob, out_stem, glb=False, extra=()):
    """Writes <stem>.blend, <stem>.fbx (Unity axes: -Z forward, Y up) and tex/<name>_BaseColor.png + _MaskMap.png.
    `extra` = additional objects to include in the FBX (collision proxies, LODs)."""
    out_stem = os.path.abspath(out_stem)
    out_dir = os.path.dirname(out_stem)
    tex_dir = os.path.join(out_dir, "tex")
    os.makedirs(tex_dir, exist_ok=True)
    m = ob.data.materials[0]
    written = {}
    for key, suffix in (("lpm_base_image", "BaseColor"), ("lpm_mask_image", "MaskMap"), ("lpm_emission_image", "Emission")):
        if key not in m: continue
        img = bpy.data.images[m[key]]
        img.filepath_raw = os.path.join(tex_dir, f"{ob.name}_{suffix}.png")
        img.file_format = "PNG"
        img.save()
        written[suffix] = img.filepath_raw
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    for e in extra:
        e.select_set(True)
    bpy.ops.export_scene.fbx(filepath=out_stem + ".fbx", use_selection=True, apply_scale_options="FBX_SCALE_NONE",
                             axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True, use_tspace=True, mesh_smooth_type="FACE",
                             object_types={"MESH"}, bake_anim=False, path_mode="COPY", embed_textures=False)
    if glb:
        bpy.ops.export_scene.gltf(filepath=out_stem + ".glb", use_selection=True, export_format="GLB")
    # PBR definitions (the contract for Unity materials) + per-cell face usage
    attr = ob.data.attributes.get("lpm_color")
    usage = {}
    if attr:
        for i in range(len(ob.data.polygons)):
            usage[attr.data[i].value] = usage.get(attr.data[i].value, 0) + 1
    defs = json.loads(m.get("lpm_palette_json", "[]"))
    for d in defs:
        d["faces"] = usage.get(d["cell"], 0)
    mat_json = out_stem + ".materials.json"
    with open(mat_json, "w", encoding="utf-8") as f:
        json.dump({"asset": ob.name, "material": m.name, "shader": "Universal Render Pipeline/Lit", "palette_size": [bpy.data.images[m["lpm_base_image"]].size[0], bpy.data.images[m["lpm_base_image"]].size[1]],
                   "textures": {k: os.path.basename(v) for k, v in written.items()}, "maskmap_layout": "R=metallic G=occlusion B=unused A=smoothness",
                   "cells": [d for d in defs if d["faces"] > 0]}, f, indent=2)
    written["MaterialsJson"] = mat_json
    blend = save(out_stem + ".blend")
    rep = report(ob); rep.update({"blend": blend, "fbx": out_stem + ".fbx", "textures": written,
                                  "extra_objects": [{"name": e.name, "tris": tri_count(e)} for e in extra]})
    print("##JSON##" + json.dumps(rep))
    return rep
