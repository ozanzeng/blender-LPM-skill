# QA checklist (copy into the delivery report)

- [ ] Brief line: asset · size (m) · budget · palette · engine
- [ ] Triangles ≤ budget (`lpm.finish` line and `gate_report.py`)
- [ ] Dimensions match the brief (±5 %); base on z = 0; centred on x = 0
- [ ] Five-view sheet reviewed: front / side / back / three-quarter / top
- [ ] Silhouette overlay vs reference (if any): IoU ≥ 0.90, aspect diff ≤ 3 %
- [ ] Parts readable by colour at distance; no two similar greys touching
- [ ] Flat shading only; no smooth faces; no normal map
- [ ] One material; palette PNGs exported; UVs inside their cells
- [ ] Gate report PASS (transforms, UVs, slots, degenerate, loose)
- [ ] `.blend` + `.fbx` + `tex/` delivered together; recipe script kept with the asset
