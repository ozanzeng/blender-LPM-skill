#!/usr/bin/env python3
"""
pbr_from_basecolor.py - derive a Unity URP mask map from a baked base colour, by classifying the palette:
saturated warm/yellow areas -> metal (gold/bronze), everything else dielectric. Smoothness follows the class,
occlusion stays 1 (the base colour already carries the concept's painted shading).

  python pbr_from_basecolor.py --base <BaseColor.png> --out <dir> --name SM_X [--metal-smooth 0.6] [--dielectric-smooth 0.15]

Writes <name>_MaskMap.png (R metallic, G occlusion, B 0, A smoothness) and <name>.materials.json.
"""
from __future__ import annotations

import argparse, json, os
import numpy as np
from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True); p.add_argument("--out", required=True); p.add_argument("--name", required=True)
    p.add_argument("--metal-smooth", type=float, default=0.6); p.add_argument("--dielectric-smooth", type=float, default=0.15)
    p.add_argument("--hue-lo", type=float, default=25.0); p.add_argument("--hue-hi", type=float, default=65.0)
    p.add_argument("--sat-min", type=float, default=0.35); p.add_argument("--val-min", type=float, default=0.35)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    img = Image.open(a.base).convert("RGB")
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    v = mx; s = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(v); d = mx - mn + 1e-6
    m = (mx == r); h[m] = ((g - b) / d)[m] % 6
    m = (mx == g); h[m] = ((b - r) / d + 2)[m]
    m = (mx == b); h[m] = ((r - g) / d + 4)[m]
    h = h * 60.0
    metal = ((h >= a.hue_lo) & (h <= a.hue_hi) & (s >= a.sat_min) & (v >= a.val_min)).astype(np.float32)
    # feather the classification a little so the mask does not alias
    try:
        from scipy import ndimage
        metal = ndimage.gaussian_filter(metal, 1.5)
        metal = np.clip((metal - 0.35) / 0.3, 0, 1)
    except Exception:
        pass
    smooth = a.dielectric_smooth + metal * (a.metal_smooth - a.dielectric_smooth)
    mask = np.stack([metal, np.ones_like(metal), np.zeros_like(metal), smooth], axis=-1)
    out_png = os.path.join(a.out, f"{a.name}_MaskMap.png")
    Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "RGBA").save(out_png)
    doc = {"asset": a.name, "shader": "Universal Render Pipeline/Lit",
           "textures": {"baseMap": os.path.basename(a.base), "maskMap": os.path.basename(out_png)},
           "maskmap_layout": "R=metallic G=occlusion B=unused A=smoothness",
           "import": {"baseMap": "sRGB on", "maskMap": "sRGB OFF"},
           "classes": [{"name": "metal (gold/bronze)", "metallic": 1.0, "smoothness": a.metal_smooth, "coverage": round(float(metal.mean()), 4)},
                       {"name": "stone / paint", "metallic": 0.0, "smoothness": a.dielectric_smooth, "coverage": round(float(1 - metal.mean()), 4)}],
           "note": "base colour carries the concept's painted shading; occlusion left at 1 to avoid double darkening"}
    json.dump(doc, open(os.path.join(a.out, f"{a.name}.materials.json"), "w"), indent=2)
    print("##JSON##" + json.dumps({"maskmap": out_png, "metal_coverage": round(float(metal.mean()), 4)}))


main()
