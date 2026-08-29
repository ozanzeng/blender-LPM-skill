#!/usr/bin/env python3
"""
register_views.py - step 0.5: measure and REGISTER a 4-view reference sheet so that all views share one
coordinate frame (same height, same base line, same centre). Without this, every downstream step (hull,
projection texture, comparison) is off by the amount the views disagree - the "sliding texture" problem.

  python register_views.py --front f.png --back b.png --left l.png --right r.png --out <dir> [--size 1024] [--pad 0.04]

Outputs:
  <out>/reg_<view>.png    RGBA, square <size>, object scaled to a common height, base on a common line, centred
  <out>/registration.json measurements + consistency report (height ratios, width agreement front/back, left/right)
  <out>/registration_sheet.png  the four registered views side by side with guide lines
Host python: numpy, PIL, scipy/skimage optional.
"""
from __future__ import annotations

import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw


def mask_of(path, sat_thr=0.12, val_thr=0.55):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im, dtype=np.float32) / 255.0
    if a[..., 3].min() < 0.5:
        fg = a[..., 3] > 0.5
    else:
        rgb = a[..., :3]; mx, mn = rgb.max(-1), rgb.min(-1)
        sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
        fg = ~((sat < sat_thr) & (mx > val_thr))
    try:
        from skimage import measure
        lab = measure.label(fg)
        if lab.max() > 1:
            sizes = np.bincount(lab.ravel()); sizes[0] = 0
            fg = lab == sizes.argmax()
        from scipy import ndimage
        fg = ndimage.binary_fill_holes(fg)
    except Exception:
        pass
    return a, fg


def measure(fg):
    ys, xs = np.where(fg)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    h, w = y1 - y0, x1 - x0
    # width profile in 20 bands from the top of the object
    bands = []
    for i in range(20):
        a, b = y0 + int(h * i / 20), y0 + int(h * (i + 1) / 20)
        rows = fg[a:max(b, a + 1)]
        bands.append(float(rows.sum(axis=1).mean()) / max(w, 1))
    cx = float(xs.mean())
    return {"bbox": [x0, y0, x1, y1], "h": h, "w": w, "aspect": w / h, "centroid_x_frac": (cx - x0) / max(w, 1), "bands": bands}


def main():
    p = argparse.ArgumentParser()
    for v in ("front", "back", "left", "right"):
        p.add_argument(f"--{v}", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--pad", type=float, default=0.04, help="empty margin fraction around the object")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    views = {v: getattr(a, v) for v in ("front", "back", "left", "right") if getattr(a, v)}
    data, masks, meas = {}, {}, {}
    for v, path in views.items():
        rgba, fg = mask_of(path)
        data[v], masks[v], meas[v] = rgba, fg, measure(fg)
    S = a.size
    inner = int(S * (1 - 2 * a.pad))
    reg = {}
    for v, m in meas.items():
        x0, y0, x1, y1 = m["bbox"]
        scale = inner / m["h"]                      # every view: object height -> inner
        rgb = data[v][..., :3].copy(); fgm = masks[v]
        # bleed the object's colour outward into the transparent area: edge samples during baking must never
        # pick up the black of an empty pixel (that is what produced dark streaks on the model)
        try:
            from scipy import ndimage
            idx = ndimage.distance_transform_edt(~fgm, return_distances=False, return_indices=True)
            rgb = rgb[tuple(idx)]
        except Exception:
            pass
        obj = Image.fromarray((np.dstack([rgb, fgm.astype(np.float32)]) * 255).astype(np.uint8), "RGBA").crop((x0, y0, x1, y1))
        nw, nh = max(int(round(m["w"] * scale)), 1), inner
        obj = obj.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ox, oy = (S - nw) // 2, S - int(S * a.pad) - nh     # base on a common line
        canvas.paste(obj, (ox, oy))
        out_path = os.path.abspath(os.path.join(a.out, f"reg_{v}.png"))
        canvas.save(out_path)
        reg[v] = {"file": out_path, "src": os.path.abspath(views[v]), "src_bbox": m["bbox"], "src_h": m["h"], "src_w": m["w"],
                  "scale": round(scale, 5), "obj_box": [ox, oy, ox + nw, oy + nh], "aspect": round(m["aspect"], 4),
                  "centroid_x_frac": round(m["centroid_x_frac"], 4), "bands": [round(b, 4) for b in m["bands"]]}
    # consistency report
    hs = {v: meas[v]["h"] for v in meas}
    ref_h = hs.get("front") or list(hs.values())[0]
    rep = {"height_ratio_vs_front": {v: round(hs[v] / ref_h, 4) for v in hs}}
    if "front" in meas and "back" in meas:
        rep["front_back_width_ratio"] = round(meas["back"]["w"] / meas["front"]["w"] * (meas["front"]["h"] / meas["back"]["h"]), 4)
        rep["front_back_band_rmse"] = round(float(np.sqrt(np.mean((np.array(meas["front"]["bands"]) - np.array(meas["back"]["bands"])) ** 2))), 4)
    if "left" in meas and "right" in meas:
        rep["left_right_width_ratio"] = round(meas["right"]["w"] / meas["left"]["w"] * (meas["left"]["h"] / meas["right"]["h"]), 4)
        # left and right are mirror images of one another: compare left to mirrored right
        rep["left_right_band_rmse"] = round(float(np.sqrt(np.mean((np.array(meas["left"]["bands"]) - np.array(meas["right"]["bands"])) ** 2))), 4)
    rep["centroid_x_frac"] = {v: reg[v]["centroid_x_frac"] for v in reg}
    out = {"size": S, "pad": a.pad, "inner_height_px": inner, "views": reg, "consistency": rep}
    json.dump(out, open(os.path.join(a.out, "registration.json"), "w"), indent=2)
    # sheet with guide lines
    order = [v for v in ("front", "right", "back", "left") if v in reg]
    sheet = Image.new("RGB", (S * len(order), S), (245, 245, 245)); d = ImageDraw.Draw(sheet)
    for i, v in enumerate(order):
        im = Image.open(reg[v]["file"]).convert("RGBA"); bg = Image.new("RGBA", im.size, (245, 245, 245, 255)); bg.alpha_composite(im)
        sheet.paste(bg.convert("RGB"), (i * S, 0))
        d.text((i * S + 8, 8), v, fill=(0, 0, 0))
    base_y = S - int(S * a.pad); top_y = base_y - inner
    for y in (base_y, top_y):
        d.line([(0, y), (sheet.width, y)], fill=(220, 40, 40), width=2)
    for i in range(len(order)):
        d.line([(i * S + S // 2, 0), (i * S + S // 2, S)], fill=(40, 120, 220), width=1)
    sheet.save(os.path.join(a.out, "registration_sheet.png"))
    print(json.dumps(rep, indent=2))
    print("##JSON##" + json.dumps({"out": a.out, "views": list(reg), "consistency": rep}))


main()
