"""Calibrate MetaForge marker coordinates to each base-map image (per map, independently).

Model (per axis, no rotation):   image_px = scale * metaforge_coord + offset
   x_px = scaleX * marker.x + offsetX      (marker.x = MetaForge lng)
   y_px = scaleY * marker.y + offsetY      (marker.y = MetaForge lat; increases DOWN the image)

Control points pair a named MetaForge marker (hatch / extraction / metro station) with the pixel
position of the same icon on the base-map image (read from a gridded zoom of the image).
The fit is ordinary least squares per axis; residuals are reported in image pixels.

Usage:  python3 tools/calibrate_maps.py [--preview DIR]
Writes: tools/source-data/map-calibration.json  (consumed by tools/build_data.py -> maps.json mapImage)
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (MetaForge label, mfX, mfY, imageX, imageY) — image px in the ORIGINAL base-map file
CONTROL = {
    'dam-battlegrounds': {'image': 'dam-battlegrounds', 'points': [
        ("Sunroof Hatch", 3095, 1736, 1560, 1150), ("Good Old Baron's Hatch", 2881, 3292, 1385, 2440),
        ("Spillway Hatch", 4917, 2918, 3080, 2125), ("Pump House Hatch", 5402, 2180, 3495, 1510),
        ("Central Swamp Lift", 3242, 2314, 1680, 1630), ("Water Treatment Elevator", 3581, 2913, 1965, 2125),
        ("Red Lakes Balcony Lift", 4833, 3377, 3020, 2520)]},
    'buried-city': {'image': 'buried-city', 'points': [
        ("Northern Station Evac", 7046, 3978, 3002, 2299), ("Western Station Evac", 6424, 4920, 2424, 3168),
        ("Eastern Station Evac", 7733, 5663, 3634, 3857), ("Southern Station Evac", 7168, 6232, 3130, 4470),
        ("Hatch Extraction", 7343, 3282, 3279, 1664), ("Train Station Hatch", 6070, 4167, 2103, 2480),
        ("Highway Overpass Hatch", 7579, 5117, 3499, 3358), ("Old Town Hatch", 6403, 5908, 2409, 4091)]},
    'the-blue-gate': {'image': 'the-blue-gate', 'points': [
        ("Reinforced Hatch", 5078, 4583, 993, 1277), ("Fragrant Hatch", 6483, 5942, 1680, 1943), ("Lucky Hatch", 6828, 3364, 1852, 677),
        ("Prefab Hatch", 9627, 4491, 3223, 1234), ("Cliffside Airshaft", 6576, 4037, 1727, 1011), ("Warehouse Airshaft", 8687, 4431, 2764, 1205),
        ("Forest Airshaft", 5430, 5600, 1164, 1777), ("Overlook Airshaft", 7931, 5691, 2391, 1823)]},
    'spaceport': {'image': 'spaceport', 'points': [
        ("Trench Hatch West", 3972, 1165, 2145, 614), ("Central Elevator", 3799, 1683, 1974, 1135), ("Trench Hatch East", 4678, 1809, 2861, 1269),
        ("West Elevator", 3071, 2086, 1229, 1546), ("Departures Hatch", 4127, 2224, 2304, 1690), ("Control Hatch", 3993, 2402, 2165, 1870),
        ("East Elevator", 4706, 2531, 2890, 2004), ("South Elevator", 3718, 2568, 1888, 2036)]},
    # Stella Montis: two level images, each with its own transform. Layer 1 markers -> 'upper' file, layer 2 -> 'lower' file.
    'stella-montis': {'image': 'stella-montis-upper', 'layer': 1, 'points': [
        ("Lobby Metro Station", 4554, 1569, 2114, 250), ("Loading Bay Metro Station", 3135, 3162, 582, 1962), ("Sandbox Hatch", 3939, 3648, 1442, 2474),
        ("Seed Vault Airshaft", 4728, 3721, 2298, 2556), ("Eastern Tunnel Hatch", 5278, 3235, 2888, 2024), ("Assembly Hatch", 3462, 1486, 950, 176)]},
    'stella-montis#2': {'image': 'stella-montis-lower', 'layer': 2, 'points': [
        ("Lobby Metro Station", 4554, 1569, 2970, 538), ("Loading Bay Metro Station", 3135, 3162, 1475, 2289), ("Sandbox Hatch", 3939, 3648, 2330, 2801),
        ("Seed Vault Airshaft", 4728, 3721, 3175, 2883), ("Eastern Tunnel Hatch", 5278, 3235, 3774, 2360), ("Assembly Hatch", 3462, 1486, 1818, 461)]},
    # riven-tides: NOT calibrated — the only base image available is unlabelled, so no reliable control points. Overlay stays off.
}


def fit(points):
    def ls(a, b):
        n = len(a); ma = sum(a) / n; mb = sum(b) / n
        s = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / sum((x - ma) ** 2 for x in a)
        return s, mb - s * ma
    sx, ox = ls([p[1] for p in points], [p[3] for p in points])
    sy, oy = ls([p[2] for p in points], [p[4] for p in points])
    res = [((sx * p[1] + ox - p[3]) ** 2 + (sy * p[2] + oy - p[4]) ** 2) ** .5 for p in points]
    return {'scaleX': round(sx, 6), 'offsetX': round(ox, 2), 'scaleY': round(sy, 6), 'offsetY': round(oy, 2),
            'rmsPx': round((sum(r * r for r in res) / len(res)) ** .5, 1), 'maxPx': round(max(res), 1)}, res


def main():
    out = {}
    for mid, cfg in CONTROL.items():
        t, res = fit(cfg['points'])
        out[mid] = {'image': cfg['image'], 'layer': cfg.get('layer'), 'transform': t, 'controlPoints': [
            {'label': p[0], 'mf': [p[1], p[2]], 'px': [p[3], p[4]], 'residualPx': round(r, 1)} for p, r in zip(cfg['points'], res)]}
        print(f"{mid:20s} scale=({t['scaleX']:.4f},{t['scaleY']:.4f}) offset=({t['offsetX']:.0f},{t['offsetY']:.0f}) rms={t['rmsPx']}px max={t['maxPx']}px")
    json.dump(out, open(os.path.join(ROOT, 'tools', 'source-data', 'map-calibration.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
