"""
compare_silhouette.py - run INSIDE Blender (via bl.py; needs only numpy). Scores a rendered orthographic
view against a reference image by silhouette and writes an overlay PNG.

  bl.py --script compare_silhouette.py -- --ref reference.png --render front.png --out overlay.png [--bands 12] [--ref-bg auto|alpha|light]

Background detection: alpha channel when the image has one; otherwise "light" = low-saturation bright pixels
(white / checkerboard greys) are background. Both masks are cropped to their bounding boxes and scaled to the
same height before comparison, so the score is about shape and proportion, not framing.
Metrics: IoU, aspect difference, centroid offset (fraction of height), per-band width error, max band error.
"""
import argparse
import json
import os
import sys

import bpy
import numpy as np


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="compare_silhouette")
    p.add_argument("--ref", required=True)
    p.add_argument("--render", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bands", type=int, default=12)
    p.add_argument("--ref-bg", default="auto", choices=["auto", "alpha", "light"])
    p.add_argument("--size", type=int, default=512, help="comparison height in pixels")
    return p.parse_args(argv)


def load_rgba(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return arr


def foreground(arr, mode):
    alpha = arr[..., 3]
    has_alpha = alpha.min() < 0.5
    if mode == "alpha" or (mode == "auto" and has_alpha):
        return alpha > 0.5
    rgb = arr[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    background = (sat < 0.12) & (mx > 0.55)
    return ~background


def crop_scale(mask, height):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        raise SystemExit("empty silhouette")
    m = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = m.shape
    scale = height / h
    new_w = max(1, int(round(w * scale)))
    yi = (np.arange(height) / scale).astype(int).clip(0, h - 1)
    xi = (np.arange(new_w) / scale).astype(int).clip(0, w - 1)
    return m[yi][:, xi], (w / h)


def pad_to(a, b):
    w = max(a.shape[1], b.shape[1])
    def pad(m):
        left = (w - m.shape[1]) // 2
        out = np.zeros((m.shape[0], w), dtype=bool)
        out[:, left:left + m.shape[1]] = m
        return out
    return pad(a), pad(b)


def main():
    a = parse()
    ref = foreground(load_rgba(os.path.abspath(a.ref)), a.ref_bg)
    ren = foreground(load_rgba(os.path.abspath(a.render)), "auto")
    r, ref_aspect = crop_scale(ref, a.size)
    g, ren_aspect = crop_scale(ren, a.size)
    r, g = pad_to(r, g)
    inter, union = np.logical_and(r, g).sum(), np.logical_or(r, g).sum()
    iou = float(inter / max(union, 1))
    def centroid(m):
        ys, xs = np.where(m); return float(xs.mean()), float(ys.mean())
    rc, gc = centroid(r), centroid(g)
    centroid_off = float(np.hypot(rc[0] - gc[0], rc[1] - gc[1]) / a.size)
    bands = []
    edges = np.linspace(0, a.size, a.bands + 1).astype(int)
    ref_w_max = max(r.sum(1).max(), 1)
    for i in range(a.bands):
        rw = float(r[edges[i]:edges[i + 1]].sum(1).mean())
        gw = float(g[edges[i]:edges[i + 1]].sum(1).mean())
        bands.append({"band_from_top": i, "ref_width": round(rw, 1), "render_width": round(gw, 1), "error": round((gw - rw) / ref_w_max, 3)})
    max_band = max(abs(b["error"]) for b in bands)
    overlay = np.zeros((a.size, r.shape[1], 4), dtype=np.float32)
    overlay[..., 3] = 1.0
    overlay[r & ~g] = (0.9, 0.15, 0.15, 1)     # reference only: red
    overlay[g & ~r] = (0.15, 0.85, 0.2, 1)     # render only: green
    overlay[r & g] = (0.95, 0.9, 0.2, 1)       # both: yellow
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    img = bpy.data.images.new("overlay", overlay.shape[1], overlay.shape[0], alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels = overlay[::-1].ravel().tolist()
    img.filepath_raw = os.path.abspath(a.out); img.file_format = "PNG"; img.save()
    result = {
        "ref": a.ref, "render": a.render, "overlay": os.path.abspath(a.out),
        "iou": round(iou, 4),
        "aspect_ref": round(ref_aspect, 4), "aspect_render": round(ren_aspect, 4),
        "aspect_diff_pct": round(100 * abs(ren_aspect - ref_aspect) / max(ref_aspect, 1e-6), 2),
        "centroid_offset_frac": round(centroid_off, 4),
        "max_band_error_frac": round(max_band, 4),
        "bands": bands,
    }
    print(f"IoU={result['iou']} aspect_diff={result['aspect_diff_pct']}% centroid={result['centroid_offset_frac']} max_band={result['max_band_error_frac']}")
    print("##JSON##" + json.dumps({k: v for k, v in result.items() if k != "bands"}))


main()
