# Budgets, facet counts and palettes

## Triangle budgets (mobile / stylized PC)

| Asset | Mobile | Stylized PC | Notes |
| --- | ---: | ---: | --- |
| Hand weapon (sword, axe, spear) | 600–1 200 | 2 000 | blade = sweep with 7–9 outline points |
| Shield | 800–1 500 | 2 500 | bend radius ≈ 0.4–0.6 m for scuta, flat for parma |
| Helmet | 1 000–1 500 | 3 000 | bowl lathe 10–12 segments, 5–6 profile rings |
| Small prop (crate, amphora, bucket) | 200–800 | 1 200 | lathe 8 segments for pottery |
| Furniture / bench / cage | 400–1 200 | 2 000 | |
| Kit module (wall, column, stair, arch) | 300–3 000 | 5 000 | flat contact faces, exact grid size |
| Character (body) | 3 000–8 000 | 15 000 | this skill covers equipment; bodies use character-artist + retopology |

## Facet counts

| Feature | Sides / segments |
| --- | ---: |
| rivet, ring, small peg | 6 |
| grip, shaft, spear haft | 8 |
| dome, pommel, boss, amphora body | 8–12 |
| column shaft, wheel, large shield boss | 10–16 |
| bend of a curved shield | 6–10 strips across the width |

## Palette design

- 8–16 cells per asset family; reuse the same palette across a whole set so materials share one texture.
- Pair each hue with a darker shade (wood / wood_dark) for recesses and undersides — cheap fake AO.
- Metals: metallic 1.0, roughness 0.3–0.45; painted / cloth / wood: metallic 0, roughness 0.65–0.9.
- Keep saturation moderate for large areas (shield face, tunic), saturated only on accents (crest, trim).
- Included `PALETTE_ROMAN` (16 cells): iron, steel, bronze, gold, wood, wood_light, leather, red, crimson, cream,
  sand, stone, stone_dark, skin, black, white.

## Proportions cheat-sheet (Roman kit)

| Object | Size (m) | Key ratios |
| --- | --- | --- |
| gladius | 0.60–0.70 total, blade 0.45–0.50 | blade width 0.05, grip 0.10, guard width 1.5 × blade |
| spatha | 0.85–1.00 | blade width 0.045 |
| pilum | 2.0 | iron shank 0.6, wooden haft 1.4 |
| scutum | 1.05 × 0.65, curved | boss ⌀ 0.15 at centre |
| parma (round) | ⌀ 0.90 | |
| galea helmet | 0.30 tall, 0.22 wide, 0.26 deep | crest adds 0.08 |
| arena column | 3.0 tall, ⌀ 0.5 | plinth 0.7 square |
| arena wall module | 4.0 wide × 3.0 tall × 0.6 deep | |
