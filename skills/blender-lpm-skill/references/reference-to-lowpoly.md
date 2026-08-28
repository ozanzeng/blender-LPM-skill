# Reference image → low-poly model (the promptable procedure)

A concept image (like the Roman environment set: lion altar, stone well, torch sconce, amphora…) becomes a model
through **five fixed steps**. The prompt only needs to name the image, the size, the budget and the engine — the
steps below are what the agent does with it. Skipping step 1 is the #1 cause of bad results.

## 1. Read the image → write the audit table BEFORE any code

| Field | Example (torch sconce) |
| --- | --- |
| Object & real size | wall torch, ≈1.45 m tall incl. flame, plate 0.45 × 1.0 m |
| Camera in the image | three-quarter from front-left, elevation ≈ 30°, plate on the right |
| Parts, top-down, with primitive | flame (kit.flame) · coals (prism) · cup (lathe) · gold rim + 8 studs (prism + kit.rivets) · cup band (prism) · handle tapered (prism) · 2 gold rings · pointed tip (lathe) · horizontal arm + diagonal brace (box, rotated) · collar (prism) · wall plate rounded slab (sweep) · gold frame + red panel (sweep) · stud (rivet) |
| Proportions | cup ⌀ ≈ 0.5 × plate width; torch height ≈ 1.2 × plate height; arm length ≈ plate width |
| Palette cells | iron, gold, red, stone, stone_dark, flame, flame_core, coal |
| Symmetry | torch radial; plate mirror-X |
| Organic parts? | none (lion, eagle, skull → fal.ai lane, see below) |

Rules: 6–20 parts; every part maps to `box / grid_box / prism / lathe / sweep / plate` or a `lpm_kit` builder
(`banner, medallion, rivets, meander_band, block_course, flame, handle_arc, column, plinth_steps, wall_ring, ring_of`).
Proportions are written as ratios, then converted to metres from the real size.

## 2. Recipe from the table

One part per table row, positioned in metres, colours from the palette. Kit builders first, primitives second.
Never coplanar parts (sink ≥ 2 mm). `finish()` → `collision_box()` → `export_unity()`.

## 3. Render at the reference's camera, then compare

```
render_views.py --views quarter --yaw <deg> --quarter-elev <deg>   # match the image's camera (yaw 90 = plate on the right)
compare_silhouette.py --ref <image> --render views/quarter.png     # IoU, aspect, centroid, band errors + overlay
```
Also render the 5-view sheet and **look at it** — the numbers cannot see colour, detail or read-ability.

## 4. Iterate (max 3 rounds), one cause per round

Read the overlay: red = reference only (we are missing volume there), green = model only (we have extra volume).
Fix the part that owns the biggest red/green area, re-run. Typical fixes: wrong overall aspect (scale one axis),
missing part, part too small, camera yaw off by 90°.

## 5. Accept

| Reference type | Silhouette IoU | Aspect diff | Plus |
| --- | ---: | ---: | --- |
| Orthographic front/side | ≥ 0.90 | ≤ 3 % | gates PASS |
| Three-quarter concept (most kit images) | ≥ 0.75 | ≤ 5 % | 5-view sheet reads as the object; parts and colours present |

Three-quarter references cannot reach ortho-level IoU (perspective, unknown elevation, painted highlights); judge
them by the table + sheet, not by IoU alone. Deliver `.blend`, `.fbx`, textures, sheet, overlay, gates, asset card.

## Organic parts (lion, eagle, skull, faces, animals)

Primitives cannot do them convincingly. Split the asset: build the architectural part with the recipe, generate the
organic part with the fal.ai lane (`hunyuan3d-v3/image-to-3d`, `generate_type=LowPoly`, cropped reference, cost
stated first), gate it, decimate to budget, paint it one palette colour, place it on the recipe's mount point.
Without fal: a blocky stand-in from lathe/box (expect IoU ≈ 0.6–0.7) — say so in the report.

## Prompt template that triggers all of this

```
Referans: <path.png>. Bu görseli blender-lpm-skill ile low-poly modele çevir.
Gerçek boyut: <yükseklik/genişlik m>. Bütçe: <n> üçgen. Hedef: Unity URP mobil. Palette: PALETTE_ROMAN (+gerekirse ek hücre).
Önce audit tablosunu yaz (parçalar → primitif/kit builder, oranlar, kamera açısı), sonra tarifi yaz ve üret.
Referans kamerasıyla quarter render alıp compare_silhouette ile karşılaştır; en fazla 3 iterasyon; kabul: IoU ≥ 0.75, oran farkı ≤ %5.
Organik parça varsa fal.ai LowPoly ile üret (önce fiyat söyle). Teslim: .blend + .fbx + tex + 5-görünüm + overlay + gates + asset card.
```
Batch form: *"Assets\09_Environment\*.png içindeki her görsel için aynı prosedürü uygula; her asset için ayrı klasör ve
kart; sonunda tek bir özet tablo (asset, üçgen, IoU, oran farkı, iterasyon sayısı, organik parça var mı)."*
