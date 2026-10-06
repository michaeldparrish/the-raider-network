# Map pages — base maps and marker calibration (v5.2)

## Page order

1. **Cinematic hero**: scenic art, overview, difficulty, environment, loot profile. Buttons: *View Map*, *View All Loot on This Map*, *View Active Hunts*.
2. **Level map / topography**: the real base map, with zoom (buttons, scroll wheel, pinch, keyboard), drag to pan, full screen, a level switcher where the map has more than one level, and a toggle for the MetaForge marker overlay.
3. **Map intelligence controls**: category toggles, *Show all* / *Hide all*, a subcategory filter, search, *Loot Intel linked*, *Locked doors*, and a collapsible marker list. Clicking a marker in the list zooms to it.
4. **Key locations / POIs**.
5. **Items found on this map**: *Top loot on this map* and *View All Loot on This Map* (`loot.html?map=<id>`).
6. **Active loot hunts and trade interest**.
7. **Field brief** (ARC presence and quests), then **routes / guides**.

## Configuration (`data/maps.json → mapImage`, written by `tools/build_data.py`)

```json
"mapImage": {
  "calibrated": true,
  "levels": [{
    "id": "all", "label": "Full map", "layer": null,
    "src": "assets/images/maps/base/dam-battlegrounds.webp",
    "srcSmall": "assets/images/maps/base/dam-battlegrounds-sm.webp",
    "width": 4260, "height": 3890,
    "scaleX": 0.8376, "scaleY": 0.8331, "offsetX": -1032, "offsetY": -300,
    "calibrated": true, "calibration": { "rmsPx": 5.8, "maxPx": 8.4, "points": 7 }
  }]
}
```

* The page templates contain no fixed sizes: `width` and `height` set the aspect ratio, and screens under 900px load the smaller image.
* **Transform** (one per map, or one per level): `imagePx = scale × metaforgeCoord + offset`, measured in the original image's pixels, so the same numbers work for any resized copy. MetaForge `x = lng`, `y = lat`.
* Markers are drawn **only** when the level is `calibrated: true`. Otherwise the base map still shows, the overlay toggle is disabled, and the marker list stays searchable.

## Calibration (`tools/calibrate_maps.py`)

Each map is calibrated on its own; there is no global scaling rule. Control points pair a named MetaForge marker (a hatch, extraction, elevator, airshaft or metro station) with the pixel position of the same icon on the labelled base map. A least-squares fit is run for each axis.

| Map | Image | Control points | RMS error | Max error |
|---|---|---|---|---|
| Dam Battlegrounds | 4260×3890 labelled | 7 | 5.8px | 8.4px |
| Buried City | 6144×6144 labelled | 8 | 24.8px | 55.4px |
| The Blue Gate | 4096×3072 labelled | 8 | 1.8px | 2.7px |
| Spaceport | 4096×4096 labelled | 8 | 3.0px | 5.6px |
| Stella Montis, main level (layer 2) | 5120×3072 labelled | 6 | 11.1px | 19.7px |
| Stella Montis, Sandbox / Metro / Seed Vault level (layer 1) | 4096×3072 labelled | 6 | 9.1px | 13.7px |
| Riven Tides | 4000×4000 unlabelled | — | **not calibrated** | overlay off |
| Pendola Pass | — | — | no image | placeholder panel |

Riven Tides has no labelled map with icons to anchor on, and its marker clusters don't match the image unambiguously, so no transform was guessed. To calibrate it:

1. Add a labelled image, or read 4–6 hatch or elevator positions off the current image.
2. Add the control points to `CONTROL` in `tools/calibrate_maps.py`.
3. Run `python3 tools/calibrate_maps.py && python3 tools/build_data.py`.

## Replacing or adding a base map

1. Export `assets/images/maps/base/<mapId>.webp` (around 2560px) and `<mapId>-sm.webp` (around 1200px).
2. Add the original size to `tools/source-data/basemap-sizes.json`.
3. Add control points to `tools/calibrate_maps.py`, then run it.
4. Run `python3 tools/build_data.py`. No layout or template changes are needed.
