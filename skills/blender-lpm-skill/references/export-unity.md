# Unity export contract

- FBX: `axis_forward="-Z"`, `axis_up="Y"`, `apply_scale_options="FBX_SCALE_NONE"`, `mesh_smooth_type="FACE"`,
  `use_tspace=True`, mesh only, no animation, textures not embedded.
- Import in Unity: scale factor 1, "Convert Units" on, Normals = Import, Smoothing = Import; material via the
  three textures in `tex/`.
- URP/HDRP Lit: BaseColor → Base Map (sRGB); MaskMap → Metallic Map / Mask Map (R metallic, G occlusion, A smoothness,
  **sRGB off**); Normal map not used (flat-shaded).
- Texture import for palettes: Filter Mode = Point, Compression = None or high quality, mip maps off (tiny textures).
- Pivot: base centre (props) or snapping corner (kit modules); check `inspect_scene.py` bounds min z = 0.
- Collision: `lpm.collision_box(asset)` adds `<Name>_COL` (12 tris, parented, hidden in renders) and `export_unity(..., extra=[col])`
  puts it in the same FBX. In Unity: add a **MeshCollider (Convex)** or a BoxCollider to `<Name>_COL`, disable its MeshRenderer,
  or let an import script do it by the `_COL` suffix. Use capsules/boxes in Unity directly when the shape is trivial.
- GLB: `lpm.export_unity(ob, stem, glb=True)` also writes `<stem>.glb` for Godot / web viewers.
