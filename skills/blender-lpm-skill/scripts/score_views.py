#!/usr/bin/env python3
"""
score_views.py - the real quality metric: how close is a RENDER to its REFERENCE view, in image space.
Crops both to the object bbox, scales the render to the reference size, then reports silhouette IoU,
RGB RMSE, SSIM and mean colour error over the shared foreground; writes a side-by-side + difference sheet.

  python score_views.py --pairs front:ref_front.png:render_front.png side:ref_side.png:render_side.png ... --out <dir> [--label name]
"""
from __future__ import annotations

import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw


def load(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im, dtype=np.float32) / 255.0
    if a[..., 3].min() < 0.5:
        fg = a[..., 3] > 0.5
    else:
        rgb = a[..., :3]; mx, mn = rgb.max(-1), rgb.min(-1)
        sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
        fg = ~((sat < 0.12) & (mx > 0.55))
    return a, fg


def crop(a, fg):
    ys, xs = np.where(fg)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return a[y0:y1, x0:x1], fg[y0:y1, x0:x1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+", required=True, help="name:reference.png:render.png")
    p.add_argument("--out", required=True); p.add_argument("--label", default="")
    p.add_argument("--raw", action="store_true", help="compare the images as they are (same registered frame) instead of normalising each to its bounding box")
    p.add_argument("--erode", type=int, default=4, help="also report metrics on the interior (edge pixels removed) - sub-pixel edge shifts dominate RMSE/SSIM otherwise")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows, tiles = [], []
    for spec in a.pairs:
        name, refp, renp = spec.split(":", 2)
        ra, rf = load(refp); ga, gf = load(renp)
        if a.raw:
            H, W = ra.shape[:2]
            if ga.shape[:2] != (H, W):
                gi = Image.fromarray((np.clip(ga, 0, 1) * 255).astype(np.uint8), "RGBA").resize((W, H), Image.LANCZOS)
                ga = np.asarray(gi, dtype=np.float32) / 255.0
                gf = np.asarray(Image.fromarray((gf * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)) > 127
        else:
            ra, rf = crop(ra, rf); ga, gf = crop(ga, gf)
            H, W = ra.shape[:2]
            gi = Image.fromarray((np.clip(ga, 0, 1) * 255).astype(np.uint8), "RGBA").resize((W, H), Image.LANCZOS)
            ga = np.asarray(gi, dtype=np.float32) / 255.0
            gf = np.asarray(Image.fromarray((gf * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)) > 127
        inter, union = (rf & gf).sum(), (rf | gf).sum()
        iou = float(inter / max(union, 1))
        both = rf & gf
        inner = both.copy()
        for _ in range(a.erode):
            inner = inner & np.roll(inner, 1, 0) & np.roll(inner, -1, 0) & np.roll(inner, 1, 1) & np.roll(inner, -1, 1)
        rref = ra[..., :3]; rren = ga[..., :3]
        rmse = float(np.sqrt(np.mean((rref[both] - rren[both]) ** 2))) if both.any() else 1.0
        dcol = [round(float(rren[both][:, c].mean() - rref[both][:, c].mean()), 4) for c in range(3)] if both.any() else [0, 0, 0]
        try:
            from skimage.metrics import structural_similarity as ssim
            g1 = (rref * [0.299, 0.587, 0.114]).sum(-1) * both; g2 = (rren * [0.299, 0.587, 0.114]).sum(-1) * both
            sval = float(ssim(g1, g2, data_range=1.0))
        except Exception:
            sval = float("nan")
        rmse_in = float(np.sqrt(np.mean((rref[inner] - rren[inner]) ** 2))) if inner.any() else float("nan")
        try:
            from skimage.metrics import structural_similarity as ssim2
            gi1 = (rref * [0.299, 0.587, 0.114]).sum(-1) * inner; gi2 = (rren * [0.299, 0.587, 0.114]).sum(-1) * inner
            ssim_in = float(ssim2(gi1, gi2, data_range=1.0))
        except Exception:
            ssim_in = float("nan")
        pct_close = float((np.abs(rref - rren).max(-1)[inner] < 0.05).mean()) if inner.any() else 0.0
        rows.append({"view": name, "iou": round(iou, 4), "rgb_rmse": round(rmse, 4), "ssim": round(sval, 4),
                     "rgb_rmse_interior": round(rmse_in, 4), "ssim_interior": round(ssim_in, 4),
                     "pct_pixels_within_5pct": round(pct_close, 4), "mean_colour_delta": dcol, "size": [W, H]})
        # tile: ref | render | abs diff
        diff = np.zeros((H, W, 3), np.float32)
        diff[both] = np.abs(rref - rren)[both] * 2.0
        diff[rf & ~gf] = [1, 0, 0]; diff[gf & ~rf] = [0, 1, 0]
        strip = np.concatenate([np.clip(rref, 0, 1), np.clip(rren, 0, 1), np.clip(diff, 0, 1)], axis=1)
        tiles.append((name, (strip * 255).astype(np.uint8)))
    w = max(t.shape[1] for _, t in tiles); h = sum(t.shape[0] for _, t in tiles) + 22 * len(tiles)
    sheet = Image.new("RGB", (w, h), (25, 25, 25)); d = ImageDraw.Draw(sheet); y = 0
    for name, t in tiles:
        d.text((6, y + 4), f"{name}   ref | render | diff (red=ref only, green=render only)", fill=(255, 255, 255)); y += 22
        sheet.paste(Image.fromarray(t), (0, y)); y += t.shape[0]
    sheet.save(os.path.join(a.out, "score_sheet.png"))
    mean = {k: round(float(np.mean([r[k] for r in rows])), 4) for k in ("iou", "rgb_rmse", "ssim", "rgb_rmse_interior", "ssim_interior", "pct_pixels_within_5pct")}
    res = {"label": a.label, "rows": rows, "mean": mean, "sheet": os.path.join(a.out, "score_sheet.png")}
    json.dump(res, open(os.path.join(a.out, "score.json"), "w"), indent=2)
    for r in rows:
        print(f"  {r['view']:6} IoU {r['iou']:.3f}  RMSE {r['rgb_rmse']:.3f}/{r['rgb_rmse_interior']:.3f}in  SSIM {r['ssim']:.3f}/{r['ssim_interior']:.3f}in  within5% {r['pct_pixels_within_5pct']*100:.1f}%")
    print(f"  MEAN   IoU {mean['iou']:.3f}  RMSE {mean['rgb_rmse']:.3f} (interior {mean['rgb_rmse_interior']:.3f})  SSIM {mean['ssim']:.3f} (interior {mean['ssim_interior']:.3f})  pixels within 5%: {mean['pct_pixels_within_5pct']*100:.1f}%   [{a.label}]")
    print("##JSON##" + json.dumps({"label": a.label, "mean": mean}))


main()
