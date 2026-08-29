"""
gltf_pbr_to_unity.py - run INSIDE Blender (via bl.py; numpy only). Converts a glTF PBR texture set (baseColor,
metallicRoughness [G = roughness, B = metallic], normal) into the Unity URP trio at a mobile-friendly size:

  <name>_BaseColor.png (sRGB) · <name>_Normal.png (OpenGL +Y) · <name>_MaskMap.png (R metallic, G AO=1, B 0, A smoothness)

  bl.py --script gltf_pbr_to_unity.py -- --base <basecolor.png> --mr <metallicRoughness.png> [--normal <normal.png>] --name SM_X --out <dir> [--size 2048]
"""
import argparse
import json
import os
import sys

import bpy
import numpy as np


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="gltf_pbr_to_unity")
    p.add_argument("--base", required=True); p.add_argument("--mr", required=True); p.add_argument("--normal", default="")
    p.add_argument("--name", required=True); p.add_argument("--out", required=True); p.add_argument("--size", type=int, default=2048)
    return p.parse_args(argv)


def load(path, size):
    img = bpy.data.images.load(path, check_existing=False); img.colorspace_settings.name = "Non-Color"
    if size and (img.size[0] != size or img.size[1] != size):
        img.scale(size, size)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img); return arr


def save(arr, path):
    h, w, _ = arr.shape
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True); img.colorspace_settings.name = "Non-Color"
    img.pixels = np.clip(arr, 0, 1).astype(np.float32).ravel().tolist(); img.filepath_raw = path; img.file_format = "PNG"; img.save(); bpy.data.images.remove(img)


def main():
    a = parse(); os.makedirs(a.out, exist_ok=True)
    base = load(a.base, a.size); base[..., 3] = 1.0
    p_base = os.path.join(a.out, f"{a.name}_BaseColor.png"); save(base, p_base)
    mr = load(a.mr, a.size)
    mask = np.stack([mr[..., 2], np.ones_like(mr[..., 1]), np.zeros_like(mr[..., 1]), 1.0 - mr[..., 1]], axis=-1)
    p_mask = os.path.join(a.out, f"{a.name}_MaskMap.png"); save(mask, p_mask)
    out = {"BaseColor": p_base, "MaskMap": p_mask, "size": a.size, "metallic_mean": round(float(mr[..., 2].mean()), 3), "smoothness_mean": round(float((1 - mr[..., 1]).mean()), 3)}
    if a.normal:
        nm = load(a.normal, a.size); nm[..., 3] = 1.0
        p_n = os.path.join(a.out, f"{a.name}_Normal.png"); save(nm, p_n); out["Normal"] = p_n
    print("##JSON##" + json.dumps(out))


main()
