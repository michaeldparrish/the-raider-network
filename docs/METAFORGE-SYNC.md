# MetaForge map data — sync & cache

## Architecture

```
MetaForge API ──(occasional sync job)──► tools/sync_metaforge.py ──► data/maps/*.json ──► Raider Network UI
```

* Visitors' browsers **never** call MetaForge. Map pages read `data/maps/<map>-markers.json`, which is served with the site.
* MetaForge asks API users to be respectful and says large requests may be throttled. The sync job sends **one request per map** with a 2-second delay between them. Run it only when you want fresher data (for example weekly, or after a patch).
* Coordinates are stored exactly as MetaForge returns them. They are never edited or invented.

## Endpoint (as used by MetaForge's own interactive map, observed 5 Oct 2026)

```
GET https://metaforge.app/api/game-map-data?tableID=arc_map_data&mapID=<mapID>
→ { "allData": [ { id, mapID, category, subcategory, lat, lng, zlayers, instanceName,
                   behindLockedDoor, lootAreas, eventConditionMask, community, routeID,
                   sourceID, updated_at, added_by, last_edited_by }, … ] }
```

The public docs list the endpoint without its parameters, and the `tableID` and `mapID` values aren't documented. **The endpoint may change.** If the sync fails, open a map on metaforge.app and check which request it makes.

| MetaForge `mapID` | Raider Network `mapId` | Cache file |
|---|---|---|
| dam | dam-battlegrounds | `data/maps/dam-battlegrounds-markers.json` |
| buried-city | buried-city | `data/maps/buried-city-markers.json` |
| spaceport | spaceport | `data/maps/spaceport-markers.json` |
| stella-montis | stella-montis | `data/maps/stella-montis-markers.json` |
| blue-gate | the-blue-gate | `data/maps/blue-gate-markers.json` |
| riven-tides | riven-tides | `data/maps/riven-tides-markers.json` |
| pendola-pass | pendola-pass | `data/maps/pendola-pass-markers.json` (empty on 5 Oct 2026; map not live) |

## Normalised marker

```json
{ "id": "…", "mapId": "stella-montis", "category": "quests", "subcategory": "with-a-view",
  "x": 2758.85, "y": 3223.1, "label": "With a View - …", "layer": 2, "locked": false,
  "lootAreas": [], "eventMask": 1, "updated": "2026-09-30", "source": "MetaForge",
  "links": { "questId": "with-a-view" } }
```

* `x = lng` and `y = lat` in MetaForge's map units (Leaflet CRS.Simple, where y grows upward).
* `layer: "all"` replaces MetaForge's sentinel value `2147483647`.
* `links` connects a marker to our data. Nature markers link to item IDs (e.g. Moss, Candleberries), quest markers to quest IDs, and ARC markers to ARC IDs.
* The categories are whatever MetaForge returns: `containers, arc, quests, locations, events, nature`. None are hardcoded.

## Running a sync

```bash
# Where metaforge.app is reachable (your machine or a server):
python3 tools/sync_metaforge.py --fetch
python3 tools/build_data.py            # merges marker-derived locations into items.json / maps.json

# Where the network blocks it, export from a browser instead (this is how v5.1 was built).
# Open https://metaforge.app/arc-raiders/map/dam, then in the browser console run:
#   const ids=['dam','spaceport','buried-city','blue-gate','stella-montis','riven-tides','pendola-pass'],out={source:'MetaForge game-map-data API',fetchedAt:new Date().toISOString(),maps:{}};
#   for(const id of ids){const j=await (await fetch('/api/game-map-data?tableID=arc_map_data&mapID='+id)).json();
#     out.maps[id]=(j.allData||[]).map(m=>({id:m.id,category:m.category,subcategory:m.subcategory,lat:m.lat,lng:m.lng,name:m.instanceName||'',locked:!!m.behindLockedDoor,lootAreas:m.lootAreas||'',zlayers:m.zlayers,eventMask:m.eventConditionMask,community:!!m.community,updated:(m.updated_at||'').slice(0,10)}));}
#   const b=await new Response(new Blob([JSON.stringify(out)]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
#   Object.assign(document.createElement('a'),{href:URL.createObjectURL(b),download:'metaforge-export.json.gz'}).click();
python3 tools/sync_metaforge.py --from-export ~/Downloads/metaforge-export.json.gz
python3 tools/build_data.py
```

## Adding real base-map images (next session)

1. Save each image as `assets/images/maps/base/<mapId>.webp`.
2. In `tools/source-data/research.json`, add `"mapImage": {"src": "assets/images/maps/base/<mapId>.webp", "bounds": {"minX":…, "maxX":…, "minY":…, "maxY":…}}` to that map. The bounds are the MetaForge coordinates at the image's left, right, bottom and top edges. They default to the extents of the marker data.
3. Run `python3 tools/build_data.py`. No layout changes are needed: the image fills the plot and the markers are drawn on top.

## Attribution and terms

* **Required for public projects:** credit MetaForge and link to https://metaforge.app/arc-raiders. The site shows *"Map data sourced in part from MetaForge community data."* on every map page, on the Maps page and in the footer.
* **Commercial use:** MetaForge's API terms ask that any paid, subscription or otherwise monetised project contact them (via Discord) first. **Before enabling monetization, confirm commercial API permission with MetaForge per their API terms.** The current build is the free version with no monetization integrations.
* MetaForge markers are community-contributed, so facts derived from them carry the `COMMUNITY REPORT` confidence label.
