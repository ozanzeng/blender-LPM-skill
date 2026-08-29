#!/usr/bin/env python3
"""
shape_from_views.py - visual hull ("shape from silhouette") from turnaround views: front / side / back / top
masks are extruded through a voxel volume and intersected; the surface is extracted with marching cubes and
written as OBJ (metres, Z up, front = -Y). Optional mirror symmetry of the front/back masks.

  python shape_from_views.py --front f.png --side s.png [--back b.png] [--top t.png] --height 1.5 --out lion.obj
        [--res 160] [--dilate 2] [--mirror] [--crop-top 0.0 --crop-bottom 0.0]  (crop fractions of the front view)

Host Python: numpy + scikit-image (+ PIL). Masks come from the light background (white/checker) of generated views.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
from PIL import Image


def mask_from(path: str, sat_thr=0.12, val_thr=0.55) -> np.ndarray:
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im, dtype=np.float32) / 255.0
    alpha = a[..., 3]
    if alpha.min() < 0.5:
        m = alpha > 0.5
    else:
        rgb = a[..., :3]; mx, mn = rgb.max(-1), rgb.min(-1)
        sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
        m = ~((sat < sat_thr) & (mx > val_thr))
    # keep the largest connected component (drop stray specks)
    from skimage import measure
    lab = measure.label(m)
    if lab.max() > 1:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        m = lab == sizes.argmax()
    return m


def crop_bbox(m: np.ndarray, pad=2) -> np.ndarray:
    ys, xs = np.where(m)
    y0, y1, x0, x1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, m.shape[0]), max(xs.min() - pad, 0), min(xs.max() + pad + 1, m.shape[1])
    return m[y0:y1, x0:x1]


def resample(m: np.ndarray, h: int, w: int) -> np.ndarray:
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(im) > 127


def dilate(m: np.ndarray, r: int) -> np.ndarray:
    if r <= 0:
        return m
    from skimage.morphology import binary_dilation, disk
    return binary_dilation(m, disk(r))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--front", required=True); p.add_argument("--side", required=True)
    p.add_argument("--back", default=""); p.add_argument("--top", default="")
    p.add_argument("--height", type=float, required=True, help="object height in metres (z extent of the front mask)")
    p.add_argument("--out", required=True)
    p.add_argument("--res", type=int, default=160, help="voxels along the height")
    p.add_argument("--dilate", type=int, default=2, help="mask dilation in px (generated views are not pixel-consistent)")
    p.add_argument("--mirror", action="store_true", help="enforce left/right symmetry (front/back/top masks mirrored about X)")
    p.add_argument("--side-faces", default="-x", choices=["-x", "+x"], help="which side the side view shows (left side view = camera at -x)")
    p.add_argument("--crop-top", type=float, default=0.0); p.add_argument("--crop-bottom", type=float, default=0.0)
    for v in ("front", "side", "back", "top"):
        p.add_argument(f"--region-{v}", default="", help="l,t,r,b fractions of the view's object bbox to keep (e.g. the lion only: 0,0,1,0.46)")
    a = p.parse_args()

    def load(path, region):
        m = crop_bbox(mask_from(path))
        if region:
            l, t, r, b = [float(x) for x in region.split(",")]
            h, w = m.shape
            m = m[int(h * t): int(h * b), int(w * l): int(w * r)]
            m = crop_bbox(m)
        return m
    F = load(a.front, a.region_front)
    if a.crop_top or a.crop_bottom:
        h = F.shape[0]; F = F[int(h * a.crop_top): h - int(h * a.crop_bottom)]; F = crop_bbox(F)
    S = load(a.side, a.region_side)
    B = load(a.back, a.region_back) if a.back else None
    T = load(a.top, a.region_top) if a.top else None
    if a.mirror:
        F = F | F[:, ::-1]
        if B is not None: B = B | B[:, ::-1]
    # world scale from the front view: height -> z, width -> x; depth (y) from the side view width
    Z = a.res
    X = max(int(round(Z * F.shape[1] / F.shape[0])), 4)
    Y = max(int(round(Z * S.shape[1] / S.shape[0])), 4)
    Fm = dilate(resample(F, Z, X), a.dilate)            # rows = z (top->bottom), cols = x
    Sm = dilate(resample(S, Z, Y), a.dilate)            # rows = z, cols = y (left side view: image left = back(+y)? see below)
    vol = np.ones((X, Y, Z), dtype=bool)                # index [x, y, z]
    # front view: camera at -y looking +y: image x -> world x (left = -x), image row -> z (top = +z)
    vol &= Fm[::-1, :].T[:, None, :]                    # Fm[z_row, x] -> [x, z]; flip rows so index 0 = bottom
    # left side view (camera at -x looking +x): image left = -y (front) ... front is -y, so image left = front(-y)
    Sz = Sm[::-1, :]                                    # [z, y_img]
    if a.side_faces == "-x":
        Sy = Sz                                         # image left (-y) -> y index 0 = -y
    else:
        Sy = Sz[:, ::-1]
    vol &= Sy.T[None, :, :]                             # [y, z]
    if B is not None:
        Bm = dilate(resample(B, Z, X), a.dilate)[::-1, ::-1]   # back view is mirrored in x
        vol &= Bm.T[:, None, :]
    if T is not None:
        Tm = dilate(resample(T, Y, X), a.dilate)        # top view: rows = y (image top = back +y), cols = x
        Tm = Tm[::-1, :]                                # row 0 = -y (front)
        vol &= Tm.T[:, :, None]
    if a.mirror:
        vol = vol | vol[::-1, :, :]
    from skimage import measure
    padded = np.pad(vol.astype(np.float32), 1)
    verts, faces, _n, _v = measure.marching_cubes(padded, level=0.5)
    verts -= 1.0
    scale = a.height / Z
    verts = verts * scale
    verts[:, 0] -= (X * scale) / 2                      # centre x
    verts[:, 1] -= (Y * scale) / 2                      # centre y
    with open(a.out, "w") as f:
        f.write("# visual hull\n")
        for v in verts: f.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
        for t in faces: f.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")
    info = {"out": a.out, "voxels": [X, Y, Z], "filled": int(vol.sum()), "verts": int(len(verts)), "tris": int(len(faces)),
            "dims_m": [round(X * scale, 3), round(Y * scale, 3), round(a.height, 3)]}
    print("##JSON##" + json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
