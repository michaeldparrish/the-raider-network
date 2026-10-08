# Premium item renders (v6.1)

Original procedural 3D models rendered in Blender (bpy 5.x, Cycles). The RaidTheory in-game icon is a visual reference for shape and features only; it is never given to any tool as an image input.

    python trn3d.py <item-id> ...          # TRN_RES=900 TRN_SAMPLES=64 -> renders/<id>.png  (items_v2.py overrides items_models.py)
    python strip_shadow.py <item-id> ...   # removes the studio ground shadow (house style: no baked shadow)
    python icon_qa.py <id> <clean.png> --ref <in-game icon>   # gates + 512 px WebP for assets/images/items/game/
Register approved files in tools/source-data/premium-art.json, then run tools/build_data.py.
