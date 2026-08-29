#!/usr/bin/env python3
"""
hy3d_local_mv.py - LOCAL multi-view shape generation with open-weights Hunyuan3D-2mv (no paid service).
Runs in the C:\\ppx\\hy3d\\.venv Python (torch + hy3dgen). Views: front / left / back / right PNGs (any background:
a light background is converted to alpha here, so rembg is not needed).

  python hy3d_local_mv.py --front f.png --left l.png --back b.png [--right r.png] --out <dir> [--steps 30] [--octree 320] [--chunks 8000] [--seed 1]

Output: <out>/model.obj + model.glb (trimesh), generation.json. ~6 GB VRAM for shape; lower --octree/--chunks on 8 GB cards.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time

import numpy as np
from PIL import Image


def to_rgba(path: str, sat_thr=0.12, val_thr=0.55) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im, dtype=np.float32) / 255.0
    if a[..., 3].min() < 0.5:
        return im
    rgb = a[..., :3]; mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    bg = (sat < sat_thr) & (mx > val_thr)
    # keep largest component of foreground
    try:
        from scipy import ndimage
        lab, n = ndimage.label(~bg)
        if n > 1:
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)); keep = 1 + int(np.argmax(sizes)); fg = lab == keep
        else:
            fg = ~bg
    except Exception:
        fg = ~bg
    a[..., 3] = fg.astype(np.float32)
    out = Image.fromarray((a * 255).astype(np.uint8), "RGBA")
    # crop to bbox + margin, square canvas (models like centred subjects)
    ys, xs = np.where(fg); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    m = int(0.08 * max(y1 - y0, x1 - x0))
    out = out.crop((max(x0 - m, 0), max(y0 - m, 0), min(x1 + m, out.width), min(y1 + m, out.height)))
    s = max(out.size); canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0)); canvas.paste(out, ((s - out.width) // 2, (s - out.height) // 2))
    return canvas


def main() -> int:
    p = argparse.ArgumentParser()
    for v in ("front", "left", "back", "right"):
        p.add_argument(f"--{v}", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="tencent/Hunyuan3D-2mv"); p.add_argument("--subfolder", default="hunyuan3d-dit-v2-mv")
    p.add_argument("--steps", type=int, default=30); p.add_argument("--octree", type=int, default=320); p.add_argument("--chunks", type=int, default=8000)
    p.add_argument("--guidance", type=float, default=5.0); p.add_argument("--seed", type=int, default=1)
    p.add_argument("--cpu-offload", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    views = {}
    for v in ("front", "left", "back", "right"):
        path = getattr(a, v)
        if path:
            im = to_rgba(path); im.save(os.path.join(a.out, f"in_{v}.png")); views[v] = im
    if "front" not in views:
        sys.exit("front view required")
    import torch
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
    t0 = time.time()
    print("loading", a.model, a.subfolder, flush=True)
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(a.model, subfolder=a.subfolder, use_safetensors=True, device="cuda" if torch.cuda.is_available() else "cpu")
    if a.cpu_offload and hasattr(pipe, "enable_model_cpu_offload"):
        pipe.enable_model_cpu_offload()
    print(f"loaded in {time.time() - t0:.0f}s, generating (views={list(views)}, steps={a.steps}, octree={a.octree})", flush=True)
    t1 = time.time()
    mesh = pipe(image=views, num_inference_steps=a.steps, octree_resolution=a.octree, num_chunks=a.chunks, guidance_scale=a.guidance,
                generator=torch.manual_seed(a.seed), output_type="trimesh")[0]
    obj = os.path.join(a.out, "model.obj"); glb = os.path.join(a.out, "model.glb")
    mesh.export(obj); mesh.export(glb)
    info = {"model": a.model, "subfolder": a.subfolder, "views": list(views), "steps": a.steps, "octree": a.octree, "chunks": a.chunks, "guidance": a.guidance, "seed": a.seed,
            "faces": int(len(mesh.faces)), "verts": int(len(mesh.vertices)), "extents": [round(float(x), 4) for x in mesh.extents], "load_s": round(t1 - t0, 1), "gen_s": round(time.time() - t1, 1),
            "generated": dt.datetime.now().isoformat(timespec="seconds"), "cost_usd": 0.0}
    json.dump(info, open(os.path.join(a.out, "generation.json"), "w"), indent=2)
    print("##JSON##" + json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
