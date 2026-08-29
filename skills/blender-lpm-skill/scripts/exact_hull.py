#!/usr/bin/env python3
"""
exact_hull.py v2 - tilt-aware visual hull in the REGISTERED frame.

Concept-sheet "orthographic" views are almost never at 0 deg elevation; they are rendered from slightly above.
Carving with them as if they were level shifts every depth-varying feature vertically - the sliding texture.
This version models the elevation explicitly: per view the image basis is right = Z x h, up = d x right with
d = h*cos(e) + Z*sin(e), and the object's own extent in that basis fixes the scale (the registration normalised
each view's apparent height to `inner` px). The mapping is solved by iteration: carve at the current estimate,
recompute the extents from the volume, carve again.

  python exact_hull.py --reg <dir> --height 3.9 --res 384 --elev 10 --iters 3 --mirror --out <dir>

Writes hull.obj (metres, Z up, base z=0, front = -Y) and frame.json with the exact per-view mapping the bake needs.
"""
from __future__ import annotations

import argparse, json, os
import numpy as np
from PIL import Image

HDIR = {"front": np.array([0.0, -1.0, 0.0]), "back": np.array([0.0, 1.0, 0.0]),
        "right": np.array([1.0, 0.0, 0.0]), "left": np.array([-1.0, 0.0, 0.0])}
Z = np.array([0.0, 0.0, 1.0])


def basis(view, elev_deg):
    h = HDIR[view]; e = np.radians(elev_deg)
    r = np.cross(Z, h); r /= np.linalg.norm(r)
    d = h * np.cos(e) + Z * np.sin(e)
    u = np.cross(d, r); u /= np.linalg.norm(u)
    return r, u, d


def mask_of(path):
    a = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0
    return a[..., 3] > 0.5


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reg", required=True); p.add_argument("--out", required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--res", type=int, default=384)
    p.add_argument("--elev", type=float, default=0.0, help="elevation of the reference views in degrees")
    p.add_argument("--iters", type=int, default=3)
    p.add_argument("--mirror", action="store_true")
    p.add_argument("--dilate", type=int, default=0)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    reg = json.load(open(os.path.join(a.reg, "registration.json")))
    S, inner = reg["size"], reg["inner_height_px"]
    masks = {v: mask_of(reg["views"][v]["file"]) for v in reg["views"]}
    if a.dilate:
        try:
            from skimage.morphology import binary_dilation, disk
            masks = {v: binary_dilation(m, disk(a.dilate)) for v, m in masks.items()}
        except Exception:
            pass
    y_base = max(reg["views"][v]["obj_box"][3] for v in reg["views"])
    # working volume: start from the apparent sizes, in metres, base at z=0
    mpp0 = a.height / inner
    w_front = max(reg["views"][v]["src_w"] * reg["views"][v]["scale"] for v in ("front", "back") if v in reg["views"])
    w_side = max(reg["views"][v]["src_w"] * reg["views"][v]["scale"] for v in ("left", "right") if v in reg["views"])
    Zn = a.res
    Xn = max(int(round(a.res * w_front / inner)), 8); Yn = max(int(round(a.res * w_side / inner)), 8)
    ext_x, ext_y, ext_z = w_front * mpp0 * 1.06, w_side * mpp0 * 1.06, a.height * 1.06
    gx = (np.arange(Xn) + 0.5) / Xn * ext_x - ext_x / 2
    gy = (np.arange(Yn) + 0.5) / Yn * ext_y - ext_y / 2
    gz = (np.arange(Zn) + 0.5) / Zn * ext_z
    PX, PY, PZ = np.meshgrid(gx, gy, gz, indexing="ij")
    pts = np.stack([PX, PY, PZ], axis=-1)            # (Xn,Yn,Zn,3)
    # per-view mapping state: (centre_r, u_min, u_max); first pass uses the level assumption
    state = {v: None for v in masks}
    vol = np.ones((Xn, Yn, Zn), dtype=bool)
    report = []
    for it in range(a.iters):
        newvol = np.ones_like(vol)
        for v, m in masks.items():
            r, u, _d = basis(v, a.elev)
            pr = pts @ r; pu = pts @ u
            if state[v] is None:
                cr, umin, umax = 0.0, 0.0, a.height          # level assumption for the first pass
            else:
                cr, umin, umax = state[v]
            scale = inner / max(umax - umin, 1e-6)           # px per metre in this view
            col = np.clip(np.round(S / 2 + (pr - cr) * scale).astype(np.int32), 0, S - 1)
            row = np.clip(np.round(y_base - (pu - umin) * scale).astype(np.int32), 0, S - 1)
            newvol &= m[row, col]
        if a.mirror:
            newvol |= newvol[::-1, :, :]
        try:
            from skimage.morphology import remove_small_holes
            newvol = remove_small_holes(newvol, area_threshold=max(64, int(newvol.size * 0.0015)))
        except Exception:
            pass
        vol = newvol
        # refresh the per-view extents from the current volume
        occ = pts[vol]
        for v in masks:
            r, u, _d = basis(v, a.elev)
            pr = occ @ r; pu = occ @ u
            state[v] = (float(0.5 * (pr.min() + pr.max())), float(pu.min()), float(pu.max()))
        # self-check against the masks
        check = {}
        for v, m in masks.items():
            r, u, _d = basis(v, a.elev)
            cr, umin, umax = state[v]; scale = inner / max(umax - umin, 1e-6)
            col = np.clip(np.round(S / 2 + (occ @ r - cr) * scale).astype(np.int32), 0, S - 1)
            row = np.clip(np.round(y_base - (occ @ u - umin) * scale).astype(np.int32), 0, S - 1)
            proj = np.zeros((S, S), bool); proj[row, col] = True
            # the projection of a voxel set is sparse; close it before comparing
            try:
                from skimage.morphology import binary_closing, disk
                proj = binary_closing(proj, disk(2))
            except Exception:
                pass
            inter = (proj & m).sum(); union = (proj | m).sum()
            check[v] = round(float(inter / max(union, 1)), 4)
        report.append({"iter": it, "filled": int(vol.sum()), "hull_vs_mask_iou": check})
    from skimage import measure
    padded = np.pad(vol.astype(np.float32), 1)
    verts, faces, _n, _v = measure.marching_cubes(padded, level=0.5)
    verts -= 1.0
    world = np.empty_like(verts)
    world[:, 0] = (verts[:, 0] + 0.5) / Xn * ext_x - ext_x / 2
    world[:, 1] = (verts[:, 1] + 0.5) / Yn * ext_y - ext_y / 2
    world[:, 2] = (verts[:, 2] + 0.5) / Zn * ext_z
    world[:, 2] -= world[:, 2].min()
    world[:, 0] -= 0.5 * (world[:, 0].min() + world[:, 0].max())
    world[:, 1] -= 0.5 * (world[:, 1].min() + world[:, 1].max())
    obj = os.path.abspath(os.path.join(a.out, "hull.obj"))
    with open(obj, "w") as f:
        f.write("# tilt-aware hull\n")
        np.savetxt(f, world, fmt="v %.6f %.6f %.6f")
        np.savetxt(f, faces + 1, fmt="f %d %d %d")
    npz = os.path.abspath(os.path.join(a.out, "hull.npz"))   # exact transfer: no file-format axis conversion
    np.savez_compressed(npz, verts=world.astype(np.float32), faces=faces.astype(np.int32))
    frame = {"elev": a.elev, "canvas": S, "inner_px": inner, "y_base": y_base, "height_m": a.height,
             "views": {v: os.path.abspath(reg["views"][v]["file"]) for v in reg["views"]},
             "map": {v: {"centre_r": state[v][0], "u_min": state[v][1], "u_max": state[v][2],
                         "scale_px_per_m": inner / max(state[v][2] - state[v][1], 1e-6)} for v in state},
             "voxels": [Xn, Yn, Zn], "tris": int(len(faces)), "iters": report,
             "dims_m": [round(float(world[:, i].max() - world[:, i].min()), 4) for i in range(3)]}
    json.dump(frame, open(os.path.abspath(os.path.join(a.out, "frame.json")), "w"), indent=2)
    print("##JSON##" + json.dumps({"obj": obj, "npz": npz, "tris": int(len(faces)), "dims_m": frame["dims_m"],
                                   "hull_vs_mask_iou": report[-1]["hull_vs_mask_iou"], "elev": a.elev}))


main()
