#!/usr/bin/env python3
"""
multiview_to_mesh.py - 4 orthographic views (front/back/left/right) -> textured 3D mesh via fal.ai Hunyuan3D v3
(multi-view conditioning), with optional PBR textures. Saves GLB (+FBX/OBJ if offered), thumbnail and a JSON log.

  python multiview_to_mesh.py --front f.png --back b.png --left l.png --right r.png --out <dir> [--face-count 100000]
        [--type Normal|LowPoly|Geometry] [--pbr] [--model fal-ai/hunyuan3d-v3/image-to-3d]

Key from $FAL_KEY or the fal-ai MCP entry in ~/.claude.json (never printed). Uses the fal queue API (long job).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request


def fal_key() -> str:
    k = os.environ.get("FAL_KEY")
    if k:
        return k
    cfg = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.exists(cfg):
        data = json.load(open(cfg, encoding="utf-8"))
        for scope in [data] + list((data.get("projects") or {}).values()):
            auth = (((scope.get("mcpServers") or {}).get("fal-ai") or {}).get("headers") or {}).get("Authorization", "")
            m = re.match(r"Bearer\s+(\S+)", auth)
            if m:
                return m.group(1)
    sys.exit("no fal key")


def req(url: str, key: str, payload: dict | None = None, timeout=120) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    r = urllib.request.Request(url, data=data, headers={"Authorization": f"Key {key}", "Content-Type": "application/json", "Accept": "application/json"}, method="POST" if data else "GET")
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def data_uri(path: str) -> str:
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode("ascii")


def download(url: str, path: str) -> None:
    with urllib.request.urlopen(url, timeout=600) as r, open(path, "wb") as f:
        f.write(r.read())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--front", required=True); p.add_argument("--back", default=""); p.add_argument("--left", default=""); p.add_argument("--right", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="fal-ai/hunyuan3d-v3/image-to-3d")
    p.add_argument("--face-count", type=int, default=100000)
    p.add_argument("--type", default="Normal", choices=["Normal", "LowPoly", "Geometry"])
    p.add_argument("--pbr", action="store_true")
    p.add_argument("--polygon", default="triangle", choices=["triangle", "quadrilateral"])
    p.add_argument("--timeout", type=int, default=1500)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    key = fal_key()
    payload = {"input_image_url": data_uri(a.front), "face_count": a.face_count, "generate_type": a.type, "enable_pbr": bool(a.pbr), "polygon_type": a.polygon}
    for k, v in (("back_image_url", a.back), ("left_image_url", a.left), ("right_image_url", a.right)):
        if v:
            payload[k] = data_uri(v)
    print(f"submitting to {a.model} (views: {sum(1 for v in (a.front, a.back, a.left, a.right) if v)}, type={a.type}, pbr={a.pbr}, faces={a.face_count}) ...", flush=True)
    t0 = time.time()
    try:
        sub = req(f"https://queue.fal.run/{a.model}", key, payload, timeout=300)
    except urllib.error.HTTPError as e:
        print("submit HTTP", e.code, e.read().decode("utf-8", "replace")[:600]); return 1
    status_url, response_url = sub.get("status_url"), sub.get("response_url")
    print("request", sub.get("request_id"), flush=True)
    last = ""
    while True:
        st = req(status_url + "?logs=1", key)
        s = st.get("status")
        if s != last:
            print(f"  [{int(time.time() - t0):4d}s] {s} queue_position={st.get('queue_position')}", flush=True); last = s
        if s == "COMPLETED":
            break
        if s in ("FAILED", "ERROR"):
            print("failed:", json.dumps(st)[:800]); return 1
        if time.time() - t0 > a.timeout:
            print("timeout"); return 1
        time.sleep(6)
    res = req(response_url, key)
    log = {"model": a.model, "payload": {k: (v if not str(v).startswith("data:") else "<image>") for k, v in payload.items()}, "generated": dt.datetime.now().isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1), "files": {}}
    urls = {}
    if res.get("model_glb"):
        urls["glb"] = res["model_glb"]["url"]
    for k, v in (res.get("model_urls") or {}).items():
        if isinstance(v, dict) and v.get("url"):
            urls[k] = v["url"]
        elif isinstance(v, str):
            urls[k] = v
    if res.get("thumbnail"):
        urls["thumbnail"] = res["thumbnail"]["url"]
    for k, u in urls.items():
        ext = {"thumbnail": ".png"}.get(k, "." + k)
        path = os.path.join(a.out, f"model{ext}")
        try:
            download(u, path); log["files"][k] = path; print("saved", path, os.path.getsize(path) // 1024, "KB")
        except Exception as exc:
            print("download failed", k, exc)
    log["seed"] = res.get("seed")
    json.dump(log, open(os.path.join(a.out, "generation.json"), "w", encoding="utf-8"), indent=2)
    print("##JSON##" + json.dumps({"out": a.out, "files": list(log["files"].keys()), "seconds": log["seconds"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
