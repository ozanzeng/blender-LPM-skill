#!/usr/bin/env python3
"""
asset_card.py - bundle an LPM asset's prompt, recipe, metrics, gates and renders into ONE shareable file
(self-contained HTML with embedded images) plus a Markdown twin. Plain Python, no Blender needed.

  python asset_card.py --name SM_Chest --prompt "low poly treasure chest, 0.8 m, 800 tris, Unity" \
      --recipe examples/chest.py --render _work/lpm/chest/beauty_cycles.png --render _work/lpm/chest/views/sheet.png \
      --inspect _work/lpm/chest/inspect.json --gates _work/lpm/chest/gates.md --out _work/lpm/chest/SM_Chest_card.html
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
from pathlib import Path


def b64(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--prompt", required=True, help="the brief / prompt that produced the asset")
    p.add_argument("--recipe", help="recipe .py to embed")
    p.add_argument("--render", action="append", default=[], help="PNG to embed (repeatable)")
    p.add_argument("--inspect", help="inspect_scene.py JSON")
    p.add_argument("--gates", help="gate_report.py markdown")
    p.add_argument("--notes", default="", help="free text: iterations, decisions, deviations")
    p.add_argument("--out", required=True, help="output .html (a .md twin is written next to it)")
    a = p.parse_args()

    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    metrics = {}
    if a.inspect and Path(a.inspect).exists():
        d = json.loads(Path(a.inspect).read_text(encoding="utf-8"))
        metrics = {"triangles": d["totals"]["tris"], "vertices": d["totals"]["verts"], "faces": d["totals"]["faces"],
                   "dimensions_m": d["bounds_world"]["dims"], "meshes": d["objects"]["mesh"], "blender": d.get("blender", ""),
                   "materials": d.get("materials", []), "images": [i["name"] + " " + "x".join(map(str, i["size"])) for i in d.get("images", [])]}
    gates = Path(a.gates).read_text(encoding="utf-8") if a.gates and Path(a.gates).exists() else ""
    verdict = "PASS" if "**Result: PASS**" in gates else ("FAIL" if "**Result: FAIL**" in gates else "n/a")
    recipe = Path(a.recipe).read_text(encoding="utf-8") if a.recipe and Path(a.recipe).exists() else ""
    renders = [Path(r) for r in a.render if Path(r).exists()]
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---------- markdown twin (relative image links)
    md = [f"# {a.name}", "", f"*Generated {stamp} with blender-lpm-skill*", "", "## Prompt", "", f"> {a.prompt}", ""]
    if a.notes:
        md += ["## Notes", "", a.notes, ""]
    if metrics:
        md += ["## Metrics", "", "| Metric | Value |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in metrics.items()] + [f"| gates | {verdict} |", ""]
    if renders:
        md += ["## Renders", ""] + [f"![{r.name}]({os.path.relpath(r, out.parent).replace(os.sep, '/')})" for r in renders] + [""]
    if recipe:
        md += ["## Recipe", "", "```python", recipe.rstrip(), "```", ""]
    if gates:
        md += ["## Gate report", "", gates.rstrip(), ""]
    out.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")

    # ---------- self-contained html
    esc = html.escape
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(a.name)} — LPM asset card</title>
<style>
body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#222;background:#fafafa}}
h1{{margin:.2em 0}} .meta{{color:#666}} blockquote{{background:#fff;border-left:4px solid #b3302e;padding:12px 16px;margin:12px 0;font-size:17px}}
img{{max-width:100%;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.15);margin:10px 0}}
table{{border-collapse:collapse;background:#fff}} td,th{{border:1px solid #ddd;padding:6px 10px;text-align:left}}
pre{{background:#1e1e1e;color:#e6e6e6;padding:14px;border-radius:8px;overflow:auto;font-size:13px}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-weight:600;color:#fff;background:{'#2e8b57' if verdict == 'PASS' else '#b3302e' if verdict == 'FAIL' else '#888'}}}
details{{margin:14px 0}} summary{{cursor:pointer;font-weight:600}}
</style></head><body>
<h1>{esc(a.name)}</h1><div class="meta">Generated {stamp} · blender-lpm-skill · gates <span class="badge">{verdict}</span></div>
<h2>Prompt</h2><blockquote>{esc(a.prompt)}</blockquote>"""]
    if a.notes:
        parts.append(f"<h2>Notes</h2><p>{esc(a.notes)}</p>")
    if metrics:
        parts.append("<h2>Metrics</h2><table>" + "".join(f"<tr><th>{esc(k)}</th><td>{esc(str(v))}</td></tr>" for k, v in metrics.items()) + "</table>")
    for r in renders:
        parts.append(f"<h2>{esc(r.name)}</h2><img src=\"{b64(r)}\" alt=\"{esc(r.name)}\">")
    if recipe:
        parts.append(f"<details open><summary>Recipe ({esc(Path(a.recipe).name)})</summary><pre>{esc(recipe)}</pre></details>")
    if gates:
        parts.append(f"<details><summary>Gate report</summary><pre>{esc(gates)}</pre></details>")
    parts.append("</body></html>")
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"card: {out} ({out.stat().st_size // 1024} KB) + {out.with_suffix('.md').name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
