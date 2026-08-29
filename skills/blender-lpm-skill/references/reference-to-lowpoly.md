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
| Organic parts? | none (lion, eagle, skull → faceted primitives, see below) |

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

## Organic parts (lion, eagle, skull, faces, animals) — still primitives

Build them as **faceted stand-ins**, top-down, 8–14 parts, each a kit organic builder:

| Body part | Builder | Notes |
| --- | --- | --- |
| torso, haunch, head, skull | `kit.blob(size=(x,y,z), segments=8, rings=4–5)` | squash/scale for ellipsoids; two blobs for chest + hindquarters |
| muzzle, beak, ears, claws | `kit.wedge` | direction toward the face |
| legs, arms, tail, neck | `kit.limb(r0, r1, length, pitch, yaw)` | 6 sides; tail = 2 chained limbs |
| mane, ruff, feathers | `lathe` collar / `sweep` spiky outline | mane = lathe with a wavy 6-point profile |
| eyes, nostrils | `paint()` on the head blob or tiny dark prisms | read-ability > accuracy |

Accept organic stand-ins at silhouette IoU ≥ 0.65 (3/4 view) when the 5-view sheet reads as the animal. Symmetry by
`mirror_x`. Budget: figure ≤ 50 % of the asset budget.

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
Önce audit tablosunu yaz (parçalar → primitif/kit builder, oranlar, kamera), sonra tarif, sonra üret.
Referans kamerasıyla quarter render + compare_silhouette; en fazla 3 iterasyon; kabul: IoU ≥ 0.75 (organik figürlü asset ≥ 0.70), oran farkı ≤ %5, 5-görünüm sayfası okunaklı.
Teslim: .blend + .fbx (+_COL) + tex + materials.json + 5-görünüm + overlay + gates + asset card. Kaynak: _work\lpm\env\<asset>\.
```

Worked example: `examples/env_lion_altar.py` — two iterations from the prompt above to IoU 0.77 / aspect 0.5 % / 1 980 tris
(iteration 1 failed on a block-course depth typo and a lion half the right size; the overlay pointed at both).
Batch form: *"Assets\09_Environment\*.png içindeki her görsel için aynı prosedürü uygula; her asset için ayrı klasör ve
kart; sonunda tek bir özet tablo (asset, üçgen, IoU, oran farkı, iterasyon sayısı, organik parça var mı)."*
