#!/usr/bin/env python3
"""
calibrate_elevation.py - find the elevation angle of a "orthographic" reference sheet by HOLD-ONE-OUT test:
carve the visual hull from three views, project it onto the fourth, and measure how well it predicts that view.
A wrong elevation makes the views mutually inconsistent, so the held-out prediction degrades. Self-consistency
(carving and checking with the same views) cannot see this, which is why it is not used here.

  python calibrate_elevation.py --reg <dir> --height 3.9 --res 160 --range 0:24:3 [--out report.json]
"""
from __future__ import annotations

import argparse, json, os
import numpy as np
from PIL import Image

HDIR = {"front": np.array([0.0, -1.0, 0.0]), "back": np.array([0.0, 1.0, 0.0]),
        "right": np.array([1.0, 0.0, 0.0]), "left": np.array([-1.0, 0.0, 0.0])}
Z = np.array([0.0, 0.0, 1.0])


def basis(view, e_deg):
    h = HDIR[view]; e = np.radians(e_deg)
    r = np.cross(Z, h); r /= np.linalg.norm(r)
    d = h * np.cos(e) + Z * np.sin(e)
    u = np.cross(d, r); u /= np.linalg.norm(u)
    return r, u


def load_masks(reg):
    out = {}
    for v, info in reg["views"].items():
        a = np.asarray(Image.open(info["file"]).convert("RGBA"), dtype=np.float32) / 255.0
        out[v] = a[..., 3] > 0.5
    return out


def downsample(mask, Q):
    im = Image.fromarray((mask * 255).astype(np.uint8)).resize((Q, Q), Image.BILINEAR)
    return np.asarray(im) > 80


def carve_and_check(masks, elev, S, inner, y_base, height, pts, held_out, iters=3):
    use = [v for v in masks if v != held_out]
    state = {v: None for v in masks}
    vol = np.ones(pts.shape[:3], bool)
    for _ in range(iters):
        nv = np.ones_like(vol)
        for v in use:
            r, u = basis(v, elev)
            pr = pts @ r; pu = pts @ u
            cr, umin, umax = state[v] if state[v] else (0.0, 0.0, height)
            sc = inner / max(umax - umin, 1e-6)
            col = np.clip(np.round(S / 2 + (pr - cr) * sc).astype(np.int32), 0, S - 1)
            row = np.clip(np.round(y_base - (pu - umin) * sc).astype(np.int32), 0, S - 1)
            nv &= masks[v][row, col]
        nv |= nv[::-1, :, :]
        vol = nv
        if not vol.any():
            return 0.0, 0
        occ = pts[vol]
        for v in masks:
            r, u = basis(v, elev)
            pr = occ @ r; pu = occ @ u
            state[v] = (float(0.5 * (pr.min() + pr.max())), float(pu.min()), float(pu.max()))
    # predict the held-out view at a resolution close to the voxel grid
    occ = pts[vol]
    r, u = basis(held_out, elev)
    cr, umin, umax = state[held_out]; sc = inner / max(umax - umin, 1e-6)
    Q = int(pts.shape[2] * 1.15)
    col = np.clip(((S / 2 + (occ @ r - cr) * sc) / S * Q).astype(np.int32), 0, Q - 1)
    row = np.clip((((y_base - (occ @ u - umin) * sc)) / S * Q).astype(np.int32), 0, Q - 1)
    proj = np.zeros((Q, Q), bool); proj[row, col] = True
    ref = downsample(masks[held_out], Q)
    inter = (proj & ref).sum(); union = (proj | ref).sum()
    return float(inter / max(union, 1)), int(vol.sum())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reg", required=True); p.add_argument("--height", type=float, required=True)
    p.add_argument("--res", type=int, default=160); p.add_argument("--range", default="0:24:3")
    p.add_argument("--out", default="")
    a = p.parse_args()
    reg = json.load(open(os.path.join(a.reg, "registration.json")))
    S, inner = reg["size"], reg["inner_height_px"]
    y_base = max(reg["views"][v]["obj_box"][3] for v in reg["views"])
    masks = load_masks(reg)
    mpp0 = a.height / inner
    w_front = max(reg["views"][v]["src_w"] * reg["views"][v]["scale"] for v in ("front", "back") if v in reg["views"])
    w_side = max(reg["views"][v]["src_w"] * reg["views"][v]["scale"] for v in ("left", "right") if v in reg["views"])
    Zn = a.res; Xn = max(int(round(a.res * w_front / inner)), 8); Yn = max(int(round(a.res * w_side / inner)), 8)
    ex, ey, ez = w_front * mpp0 * 1.08, w_side * mpp0 * 1.08, a.height * 1.08
    gx = (np.arange(Xn) + 0.5) / Xn * ex - ex / 2
    gy = (np.arange(Yn) + 0.5) / Yn * ey - ey / 2
    gz = (np.arange(Zn) + 0.5) / Zn * ez
    PX, PY, PZ = np.meshgrid(gx, gy, gz, indexing="ij")
    pts = np.stack([PX, PY, PZ], axis=-1)
    lo, hi, step = [float(x) for x in a.range.split(":")]
    rows = []
    for e in np.arange(lo, hi + 1e-6, step):
        scores = {}
        for held in masks:
            iou, filled = carve_and_check(masks, e, S, inner, y_base, a.height, pts, held)
            scores[held] = round(iou, 4)
        mean = float(np.mean(list(scores.values())))
        rows.append({"elev": float(e), "mean_holdout_iou": round(mean, 4), "per_view": scores})
        print(f"elev {e:5.1f}  holdout IoU mean {mean:.4f}   " + "  ".join(f"{k} {v:.3f}" for k, v in scores.items()), flush=True)
    best = max(rows, key=lambda r: r["mean_holdout_iou"])
    print(f"BEST elevation: {best['elev']:.1f} deg  (mean holdout IoU {best['mean_holdout_iou']:.4f})")
    if a.out:
        json.dump({"rows": rows, "best": best}, open(a.out, "w"), indent=2)
    print("##JSON##" + json.dumps({"best_elev": best["elev"], "mean_holdout_iou": best["mean_holdout_iou"]}))


main()
