#!/usr/bin/env python3
"""
make_turnaround.py - step 0 of reference-to-lowpoly: turn ONE concept image into orthographic turnaround views
(front / left side / back / top) with a fal.ai image-edit model, so the audit table and compare_silhouette work on
measurable views instead of a single three-quarter shot.

  python make_turnaround.py --ref Assets/09_Environment/71_lion_statue_altar.png [--views front,side,back,top] [--model fal-ai/nano-banana/edit] [--out <dir>]

Cost: ~$0.039 per image with nano-banana (4 views ~ $0.16). The key is read from $FAL_KEY or from Claude Code's
~/.claude.json (fal-ai MCP header) and is never printed or written anywhere. Outputs: <out>/<stem>_<view>.png,
<out>/<stem>.turnaround.json (model, prompts, seeds, estimated cost) and <out>/<stem>_sheet.png (ref + views).
Plain Python 3.9+, stdlib only (PIL optional for the sheet).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.request

PRICE = {"fal-ai/nano-banana/edit": 0.039, "fal-ai/flux-pro/kontext": 0.04}
VIEW_PROMPTS = {
    "front": "Orthographic FRONT view of exactly this same object, straight on at eye level, no perspective, no rotation. Keep the identical design, proportions, materials and colors. Centered, whole object visible, plain white background, no ground shadow, no text. Stylized low-poly game asset turnaround sheet style.",
    "side": "Orthographic LEFT SIDE view (profile, 90 degrees from the front) of exactly this same object, straight on at eye level, no perspective. Keep the identical design, proportions, materials and colors. Centered, whole object visible, plain white background, no ground shadow, no text.",
    "back": "Orthographic BACK view (180 degrees from the front) of exactly this same object, straight on at eye level, no perspective. Keep the identical design, proportions, materials and colors. Centered, whole object visible, plain white background, no ground shadow, no text.",
    "top": "Orthographic TOP-DOWN view (straight down from above) of exactly this same object, no perspective. Keep the identical design, proportions, materials and colors. Centered, whole object visible, plain white background, no ground shadow, no text.",
}


def fal_key() -> str:
    k = os.environ.get("FAL_KEY")
    if k:
        return k
    cfg = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.exists(cfg):
        data = json.load(open(cfg, encoding="utf-8"))
        for scope in [data] + list((data.get("projects") or {}).values()):
            srv = (scope.get("mcpServers") or {}).get("fal-ai") or {}
            auth = (srv.get("headers") or {}).get("Authorization", "")
            m = re.match(r"Bearer\s+(\S+)", auth)
            if m:
                return m.group(1)
    sys.exit("no fal key: set FAL_KEY or configure the fal-ai MCP server")


def call(model: str, payload: dict, key: str, timeout: int = 180) -> dict:
    req = urllib.request.Request(f"https://fal.run/{model}", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Authorization": f"Key {key}", "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ref", required=True)
    p.add_argument("--views", default="front,side,back,top")
    p.add_argument("--model", default="fal-ai/nano-banana/edit")
    p.add_argument("--out", default="")
    p.add_argument("--extra", default="", help="extra prompt text appended to every view (e.g. 'Roman stone lion statue on an altar')")
    a = p.parse_args()
    ref = os.path.abspath(a.ref)
    stem = os.path.splitext(os.path.basename(ref))[0]
    out = os.path.abspath(a.out) if a.out else os.path.join(os.path.dirname(ref), "turnarounds")
    os.makedirs(out, exist_ok=True)
    key = fal_key()
    mime = "image/png" if ref.lower().endswith(".png") else "image/jpeg"
    data_uri = f"data:{mime};base64," + base64.b64encode(open(ref, "rb").read()).decode("ascii")
    views = [v.strip() for v in a.views.split(",") if v.strip()]
    log = {"ref": ref, "model": a.model, "generated": dt.datetime.now().isoformat(timespec="seconds"), "views": {}, "estimated_cost_usd": round(PRICE.get(a.model, 0.04) * len(views), 3)}
    for v in views:
        prompt = VIEW_PROMPTS[v] + (" " + a.extra if a.extra else "")
        payload = {"prompt": prompt, "image_urls": [data_uri], "num_images": 1, "output_format": "png", "aspect_ratio": "1:1"}
        print(f"[{v}] calling {a.model} ...", flush=True)
        try:
            res = call(a.model, payload, key)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            print(f"[{v}] HTTP {e.code}: {body}")
            log["views"][v] = {"error": f"HTTP {e.code}", "detail": body}
            continue
        imgs = res.get("images") or []
        if not imgs:
            print(f"[{v}] no image in response: {str(res)[:200]}")
            log["views"][v] = {"error": "no image"}
            continue
        url = imgs[0]["url"]
        path = os.path.join(out, f"{stem}_{v}.png")
        with urllib.request.urlopen(url, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
        log["views"][v] = {"file": path, "prompt": prompt, "description": res.get("description", "")}
        print(f"[{v}] saved {path}")
    json.dump(log, open(os.path.join(out, f"{stem}.turnaround.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    try:
        from PIL import Image, ImageDraw
        files = [ref] + [log["views"][v]["file"] for v in views if "file" in log["views"][v]]
        cell = 512
        sheet = Image.new("RGB", (cell * len(files), cell + 24), (35, 35, 35)); d = ImageDraw.Draw(sheet)
        for i, f in enumerate(files):
            im = Image.open(f).convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg.convert("RGB"); im.thumbnail((cell, cell))
            sheet.paste(im, (i * cell + (cell - im.width) // 2, 24 + (cell - im.height) // 2)); d.text((i * cell + 6, 5), ("reference" if i == 0 else views[i - 1]), fill=(255, 255, 255))
        sheet.save(os.path.join(out, f"{stem}_sheet.png"))
        print("sheet:", os.path.join(out, f"{stem}_sheet.png"))
    except Exception as exc:
        print("sheet skipped:", exc)
    print("##JSON##" + json.dumps({"out": out, "views": {v: ("ok" if "file" in d_ else d_.get("error")) for v, d_ in log["views"].items()}, "estimated_cost_usd": log["estimated_cost_usd"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
