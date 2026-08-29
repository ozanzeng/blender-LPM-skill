# Reference image → low-poly model (the promptable procedure)

A concept image (like the Roman environment set: lion altar, stone well, torch sconce, amphora…) becomes a model
through **six fixed steps**. The prompt only needs to name the image, the size, the budget and the engine — the
steps below are what the agent does with it. Skipping steps 0–1 is the #1 cause of bad results.

## 0. Turnaround first (one concept → front / side / back / top)

```
python scripts/make_turnaround.py --ref <concept.png> --out _work/lpm/env/<asset>/turnaround --extra "<one-line subject description>"
```
Uses fal.ai `nano-banana/edit` (≈ $0.04 / view, 4 views ≈ $0.16; state the cost, the key stays in the machine's config).
Output: `<stem>_front/side/back/top.png` + a sheet. The generated views are consistent enough to **measure**
proportions (lion = 44 % of total height, pedestal 0.5 H wide…) and to run `compare_silhouette` on orthographic
renders (`render_views.py --ortho`) with the ortho thresholds (IoU ≥ 0.85). The original concept stays the
authority for style and colour; when a generated view contradicts it, the concept wins.
Lion altar result: 3/4-only workflow reached IoU 0.77; with the turnaround, ortho front 0.86 / side 0.85 in one extra round.

## 1. Read the image → write the audit table BEFORE any code

| Field | Example (torch sconce) |
| --- | --- |
| Object & real size | wall torch, ≈1.45 m tall incl. flame, plate 0.45 × 1.0 m |
| Camera in the image | three-quarter from front-left, elevation ≈ 30°, plate on the right (plus the generated ortho views from step 0) |
| Parts, top-down, with primitive | flame (kit.flame) · coals (prism) · cup (lathe) · gold rim + 8 studs (prism + kit.rivets) · cup band (prism) · handle tapered (prism) · 2 gold rings · pointed tip (lathe) · horizontal arm + diagonal brace (box, rotated) · collar (prism) · wall plate rounded slab (sweep) · gold frame + red panel (sweep) · stud (rivet) |
| Proportions | cup ⌀ ≈ 0.5 × plate width; torch height ≈ 1.2 × plate height; arm length ≈ plate width |
| Palette cells | iron, gold, red, stone, stone_dark, flame, flame_core, coal |
| Symmetry | torch radial; plate mirror-X |
| Organic parts? | lion → visual hull from the turnaround (route B) + primitive face features |

Rules: 6–20 parts; every part maps to `box / grid_box / prism / lathe / sweep / plate` or a `lpm_kit` builder
(`banner, medallion, rivets, meander_band, block_course, flame, handle_arc, column, plinth_steps, wall_ring, ring_of`).
Proportions are written as ratios, then converted to metres from the real size.

## 2. Recipe from the table

One part per table row, positioned in metres, colours from the palette. Kit builders first, primitives second.
Never coplanar parts (sink ≥ 2 mm). `finish()` → `collision_box()` → `export_unity()`.

## 3. Render and compare — ortho against the turnaround, quarter against the concept

```
render_views.py --ortho                                            # front/side/back/top orthographic renders
compare_silhouette.py --ref turnaround/<stem>_front.png --render views/front.png
compare_silhouette.py --ref turnaround/<stem>_side.png  --render views/side.png
render_views.py --views quarter --yaw <deg> --quarter-elev <deg>   # optional: the concept's own camera
compare_silhouette.py --ref <concept.png> --render views/quarter.png
```
Also render the 5-view sheet and **look at it** — the numbers cannot see colour, detail or read-ability.

## 4. Iterate (max 3 rounds), one cause per round

Read the overlay: red = reference only (we are missing volume there), green = model only (we have extra volume).
Fix the part that owns the biggest red/green area, re-run. Typical fixes: wrong overall aspect (scale one axis),
missing part, part too small, camera yaw off by 90°.

## 5. Accept

| Reference type | Silhouette IoU | Aspect diff | Plus |
| --- | ---: | ---: | --- |
| Generated turnaround front + side (step 0) | ≥ 0.85 each | ≤ 5 % | gates PASS, 5-view sheet reads as the object |
| Hand-drawn orthographic front/side | ≥ 0.90 | ≤ 3 % | gates PASS |
| Three-quarter concept only (no turnaround) | ≥ 0.75 | ≤ 5 % | parts and colours present |

Three-quarter references cannot reach ortho-level IoU (perspective, unknown elevation, painted highlights); judge
them by the table + sheet, not by IoU alone. Deliver `.blend`, `.fbx`, textures, sheet, overlay, gates, asset card.

## Organic parts (lion, eagle, skull, faces, animals) — three routes

**Route C — multi-view generator (when the brief demands near-identical reproduction):** with a consistent
front / back / left / right sheet (hand-made or from `make_turnaround.py`), `scripts/multiview_to_mesh.py` sends the
four views to fal `hunyuan3d-v3/image-to-3d` (multi-view conditioning, `enable_pbr`) and downloads a textured mesh;
`scripts/gen_to_lowpoly.py` orients, scales to the real height, decimates to the budget keeping UVs, and exports
`.blend/.fbx`; `scripts/gltf_pbr_to_unity.py` converts the glTF PBR set into BaseColor / Normal / MaskMap at 2048 px.
Lion altar from the 4-view sheet: 120 k tris in 168 s, ortho IoU **front 0.92 / side 0.95 / back 0.96** — the lion's
face, mane and legs are real. Cost: one fal run (state it first). Route C is the only route that reaches the
"looks like the reference" bar for figures; A and B stay for props and silhouettes.

**Route C-local — no paid service:** the same model family has open weights. `scripts/hy3d_local_mv.py` runs
`tencent/Hunyuan3D-2mv` (multi-view DiT, shape only, ~6 GB VRAM, no compiled extensions) in a local venv
(`C:\ppx\hy3d\.venv`, Python 3.11 via uv, torch cu124). Texturing is then done **for free in Blender** by
`scripts/project_views_bake.py`: the four reference views are projected orthographically onto the mesh (per-face
view choice by horizontal normal, alpha-masked references, fill colour for edges) and baked into one atlas.
Setup notes: HF anonymous downloads via the xet bridge stalled — set `HF_HUB_ENABLE_HF_TRANSFER=1` and
`HF_HUB_DISABLE_XET=1` (12 MB/s afterwards); on 8 GB cards use `--octree 256 --chunks 8000`. Lion altar, local: 558 k faces, ortho IoU 0.91 / 0.93 / 0.95, textured by
projection bake — equal to the paid run.



**Route A — faceted primitives** (`kit.blob / wedge / limb` + lathe mane): fast, cheap, but reads as "a four-legged
animal" rather than a lion (lion altar: quarter IoU 0.77, ortho 0.86/0.85, looked like a dog).

**Route B — visual hull from the turnaround** (`scripts/shape_from_views.py` → `scripts/hull_to_lowpoly.py`):
the front/side/back(/top) masks are extruded through a voxel grid and intersected (shape-from-silhouette), the
surface is extracted with marching cubes, smoothed, planar+collapse-decimated to the budget, flat-shaded, and
imported into the recipe as a part carrying the palette cell (`lpm_color`) — one material, one mesh, same pipeline.

```
python scripts/shape_from_views.py --front T/x_front.png --side T/x_side.png --back T/x_back.png --height 1.7 --res 160 --dilate 1 --mirror \
       --region-front 0,0,1,0.47 --region-side 0,0,1,0.47 --region-back 0,0,1,0.47 --out hull/lion_hull.obj      # crop each view to the figure
python scripts/bl.py --script scripts/hull_to_lowpoly.py -- --obj hull/lion_hull.obj --budget 1400 --smooth 10 --planar 8 --out hull/lion_lp.blend
# recipe: import hull/lion_lp.obj, set lpm_color, append to parts -> lpm.finish()   (see examples/env_lion_altar_hull.py)
```
Lion altar hybrid (primitive pedestal + hull lion): 2 880 tris, ortho front 0.88 / side 0.87 — the side reads as a
sitting lion. Needs `scikit-image` in the host Python (`pip install scikit-image`).

What the hull cannot do: concavities (eye sockets, mouth, gaps between mane layers). Options, in order of cost:
1. add the features as primitives on top of the hull (eye wedges, nose box, ear wedges) — 20 tris, 5 minutes;
2. carve the front surface with a monocular depth map (Depth Anything V2 / MoGe-2) — relative depth, calibrate the
   range with the side view; 3. accept the statue as a "stone lion" silhouette. Generated views are not pixel-consistent:
   `--dilate 1–2` keeps the hull from thinning; `--mirror` enforces symmetry from the better half.


## Exact reproduction from a 4-view sheet (no paid service) — the measured pipeline

When the brief is "match this reference sheet", the answer is not a generator: it is a **calibrated visual hull plus
projective texturing**, and a metric that can tell you when you are done. Measured on the Roman lion altar:
silhouette IoU **0.972**, interior RGB RMSE **0.022**, SSIM **0.993**, **98.5 %** of pixels within 5 % — while
shifting the reference by a single pixel already costs RMSE 0.035. Cost: $0, ~6 minutes on an RTX 3070 Ti.

| Step | Script | What it does / why |
| --- | --- | --- |
| 1 | `register_views.py` | Puts all views in one frame (same height, base line, centre) and bleeds the object colour into the transparent border. Reports how consistent the sheet is (this one: heights within 0.4 %). Everything downstream depends on this. |
| 2 | `calibrate_elevation.py` | Concept sheets are rarely level. Hold-one-out carving finds the elevation (~3° here). |
| 3 | `exact_hull.py` | Tilt-aware visual hull on a voxel grid, extents solved by iteration; writes `hull.npz` **and** `frame.json` (the exact world↔image mapping every later step reuses). Voxel-vs-mask agreement 0.98–0.99. |
| 4 | `hull_prep.py` | Marching-cubes mesh → weld → planar + collapse decimation to the budget. Loads the `.npz` directly: **never round-trip a mesh through OBJ/FBX between these steps** — an axis conversion silently rotated the model and cost a day. |
| 5a | `bake_registered.py` | Projects the views with the `frame.json` mapping and bakes one atlas, weighting each view by `max(0, N·d)^k`. Seamless; the delivery default. |
| 5b | `atlas_from_views.py` | Packs the four views into a 2×2 atlas and points each face at its dominant quadrant. Texels are the reference pixels 1:1 (SSIM 0.990) but view switches leave hard seams. Use for hero shots from the canonical angles. |
| 6 | `pbr_from_basecolor.py` | Classifies metal (gold/bronze) from the baked colour → MaskMap (R metallic, G AO, A smoothness) + `materials.json`. PBR stays a *definition*, no generated maps. |
| 7 | `wire_pbr_export.py` | Wires the maps, adds the box collider, exports the Unity FBX. |
| ✔ | `render_ref_views.py` + `score_views.py` | Renders from the reference cameras (unlit) and scores. **Use `--raw`**: normalising each image to its bounding box hides a 2 % silhouette difference as a 3-pixel blur and made the pipeline look four times worse than it was. |

Two traps worth remembering: a mesh that round-trips through OBJ picks up an axis conversion (front/back swap or a
90° yaw — you see it as "the texture is on the wrong side"), and a comparison that rescales both images to their own
bounding box cannot measure registration at all.


## The mandatory held-out test (learned the hard way)

A reconstruction scored only on the views it was built from is **not evaluated at all**. A visual hull + projective
texturing reproduces its own four views at 98 % and can still look broken from 45°, because between the views both
the surface and its colour are invented: the hull surface is unconstrained, the projection stretches, the view
handover leaves a seam down the middle of a face, and horizontal surfaces no view sees get smeared with a side
projection.

**Always keep one view out.** `scripts/find_view.py` sweeps azimuth/elevation to find the camera a held-out
reference was rendered from, then `score_views.py` scores it. Measured on the lion altar, against the original
three-quarter concept that no step used:

| Build | held-out IoU | held-out SSIM | verdict |
| --- | ---: | ---: | --- |
| visual hull + projection | 0.863 | 0.589 | seams, smears — unusable at 45° |
| local generator (octree 256, 30 steps) + projection | 0.880 | 0.615 | pose wrong |
| paid generator + its own PBR | 0.878 | 0.654 | good |
| **local generator (octree 384, 50 steps) + projection** | **0.887** | 0.621 | **best; delivered** |

Consequences for the procedure:
- Hulls are for **silhouette-locked props** and for measuring, not for figures seen from arbitrary angles.
- Figures need geometry with a 3D prior: `hy3d_local_mv.py` at **octree ≥ 384 and ≥ 50 steps** (the low settings
  produce a plausible-from-4-views blob), then texture with `bake_registered.py --fit-mesh --top-color auto`
  (`--fit-mesh` re-solves the mapping for that mesh; `--top-color` stops upward faces being painted with a side view).
- Report both numbers: the four training views (how faithful the texture is) and the held-out view (whether the
  object is actually right).


## How many reference angles do you actually need?

Measured on the lion altar (held-out 3/4 concept, hull carved from N calibrated silhouettes, our own texture, no
generator in the geometry):

| reference views | held-out IoU | the lion's head |
| ---: | ---: | --- |
| 4 (front/back/left/right) | 0.868 | mush — the muzzle and mane are simply not in four silhouettes |
| 8 (every 45°) | 0.879 | recognisable |
| 16 (every 22.5°) | 0.881 | **clean faceted lion, delivery quality** |

So: **four views are enough for boxy props and for the texture, and not enough for a figure.** If you want the
whole asset built in Blender with no 3D generator anywhere, supply 8–16 angles of the concept (the same way the
4-view sheet was made) and `render_n_views.py` / `hull_n_views.py` will carve it. With only four, either accept a
generator for the figure's geometry or model the figure by hand.

Symmetry: model one half and mirror it (`hull_prep.py --mirror` bisects at x=0 and applies a Mirror modifier).
Unioning a shape with its mirror instead inflates it — that was an early mistake here.
The reference look is **flat shading with large facets**: `--planar2 8 --flat` after the collapse pass gives it;
smooth shading on a hull is what made the first attempt look like a blob.

## PBR = definitions only

Every colour is a palette cell with `(name, baseColor hex, metallic, roughness[, emission])`. `export_unity()`
writes `<Name>.materials.json` (URP Lit names: baseColor, metallic, smoothness, emission) alongside the 128 px
palette PNGs. No texture generation, no baking, no PATINA for these assets.

## Prompt template that triggers all of this

```
Referans: <path.png>. Bu görseli blender-lpm-skill ile low-poly modele çevir.
Gerçek boyut: <tek anchor, m>. Bütçe: <n> üçgen (organik parça ≤ %50). Hedef: Unity URP mobil. Palette: PALETTE_ROMAN (+gerekirse ek hücre).
Parça ayrımı: tüm parçalar primitif/kit; organik figür (aslan, kartal, kafatası) kit.blob/wedge/limb + lathe ile blok-heykel.
PBR = tanım: her hücre (baseColor, metallic, roughness[, emission]) → materials.json; doku üretimi/bake yok.
Kamera: <3/4 sol-ön / sağ-ön, ~N°> (bilinmiyorsa ajan tahmin eder, overlay'de doğrular).
Adım 0: make_turnaround.py ile ön/yan/arka/üst görünümleri üret (≈ $0.16, maliyeti söyle). Sonra audit tablosunu bu görünümlerden ölçerek yaz (parçalar → primitif/kit builder, oranlar), sonra tarif, sonra üret.
Ortografik ön+yan render'ı turnaround ile compare_silhouette; en fazla 3 iterasyon; kabul: ön ve yan IoU ≥ 0.85, oran farkı ≤ %5, 5-görünüm sayfası okunaklı.
Teslim: .blend + .fbx (+_COL) + tex + materials.json + 5-görünüm + overlay + gates + asset card. Kaynak: _work\lpm\env\<asset>\.
```

Worked example: `examples/env_lion_altar.py` — two iterations from the prompt above to IoU 0.77 / aspect 0.5 % / 1 980 tris
(iteration 1 failed on a block-course depth typo and a lion half the right size; the overlay pointed at both).
Batch form: *"Assets\09_Environment\*.png içindeki her görsel için aynı prosedürü uygula; her asset için ayrı klasör ve
kart; sonunda tek bir özet tablo (asset, üçgen, IoU, oran farkı, iterasyon sayısı, organik parça var mı)."*
