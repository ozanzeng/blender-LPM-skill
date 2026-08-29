#!/usr/bin/env python3
"""
hull_n_views.py - visual hull from N calibrated orthographic views (views.json from render_n_views.py).
More views = a much better hull: 4 views cannot see a lion's muzzle, 8-12 can.

  python hull_n_views.py --views <dir/views.json> --res 384 --out <dir> [--mirror]
"""
from __future__ import annotations

import argparse, json, os
import numpy as np
from PIL import Image

Z = np.array([0.0, 0.0, 1.0])


def basis(az_deg, el_deg):
    e, z = np.radians(el_deg), np.radians(az_deg)
    d = np.array([np.cos(e) * np.sin(z), -np.cos(e) * np.cos(z), np.sin(e)])
    r = np.cross(Z, d); r /= np.linalg.norm(r)
    u = np.cross(d, r); u /= np.linalg.norm(u)
    return r, u


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--views", required=True); p.add_argument("--out", required=True)
    p.add_argument("--res", type=int, default=384); p.add_argument("--mirror", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    info = json.load(open(a.views))
    S = info["size"]; ortho = info["ortho_scale"]; ctr = np.array(info["centre"]); base_z = info["base_z"]
    mpp = ortho / S                                            # metres per pixel (uniform, known camera)
    masks = []
    for v in info["views"]:
        arr = np.asarray(Image.open(v["file"]).convert("RGBA"), dtype=np.float32) / 255.0
        masks.append((arr[..., 3] > 0.5, v["az"], v["elev"]))
    ext = ortho * 0.55
    Zn = a.res
    Xn = Yn = max(int(round(a.res * (2 * ext) / info["height_m"])), 8)
    gx = (np.arange(Xn) + 0.5) / Xn * (2 * ext) - ext
    gy = (np.arange(Yn) + 0.5) / Yn * (2 * ext) - ext
    gz = (np.arange(Zn) + 0.5) / Zn * info["height_m"]
    PX, PY, PZ = np.meshgrid(gx, gy, gz, indexing="ij")
    pts = np.stack([PX + ctr[0], PY + ctr[1], PZ + base_z], axis=-1)
    rel = pts - ctr
    vol = np.ones((Xn, Yn, Zn), bool)
    for m, az, el in masks:
        r, u = basis(az, el)
        col = np.clip(np.round(S / 2 + (rel @ r) / mpp).astype(np.int32), 0, S - 1)
        row = np.clip(np.round(S / 2 - (rel @ u) / mpp).astype(np.int32), 0, S - 1)
        vol &= m[row, col]
    if a.mirror:
        vol |= vol[::-1, :, :]
    try:
        from skimage.morphology import remove_small_holes
        vol = remove_small_holes(vol, area_threshold=max(64, int(vol.size * 0.001)))
    except Exception:
        pass
    from skimage import measure
    verts, faces, _n, _v = measure.marching_cubes(np.pad(vol.astype(np.float32), 1), level=0.5)
    verts -= 1.0
    world = np.empty_like(verts)
    world[:, 0] = (verts[:, 0] + 0.5) / Xn * (2 * ext) - ext
    world[:, 1] = (verts[:, 1] + 0.5) / Yn * (2 * ext) - ext
    world[:, 2] = (verts[:, 2] + 0.5) / Zn * info["height_m"]
    world[:, 2] -= world[:, 2].min()
    world[:, 0] -= 0.5 * (world[:, 0].min() + world[:, 0].max())
    world[:, 1] -= 0.5 * (world[:, 1].min() + world[:, 1].max())
    npz = os.path.abspath(os.path.join(a.out, "hull.npz"))
    np.savez_compressed(npz, verts=world.astype(np.float32), faces=faces.astype(np.int32))
    print("##JSON##" + json.dumps({"npz": npz, "views": len(masks), "tris": int(len(faces)),
                                   "dims_m": [round(float(world[:, i].max() - world[:, i].min()), 4) for i in range(3)]}))


main()
