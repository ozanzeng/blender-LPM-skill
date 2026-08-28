# Unity export contract

- FBX: `axis_forward="-Z"`, `axis_up="Y"`, `apply_scale_options="FBX_SCALE_NONE"`, `mesh_smooth_type="FACE"`,
  `use_tspace=True`, mesh only, no animation, textures not embedded.
- Import in Unity: scale factor 1, "Convert Units" on, Normals = Import, Smoothing = Import; material via the
  three textures in `tex/`.
- URP/HDRP Lit: BaseColor → Base Map (sRGB); MaskMap → Metallic Map / Mask Map (R metallic, G occlusion, A smoothness,
  **sRGB off**); Normal map not used (flat-shaded).
- Texture import for palettes: Filter Mode = Point, Compression = None or high quality, mip maps off (tiny textures).
- Pivot: base centre (props) or snapping corner (kit modules); check `inspect_scene.py` bounds min z = 0.
- Collision: box/capsule primitives in Unity, or a `collision-proxy` mesh if the shape needs it.
- GLB: `lpm.export_unity(ob, stem, glb=True)` also writes `<stem>.glb` for Godot / web viewers.
