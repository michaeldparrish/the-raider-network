"""Crop the composite concept boards in /source-boards into individual web assets.

Run from the project root:  python3 tools/crop_assets.py
Requires Pillow. Re-running overwrites the generated files; source boards are never modified.
Writes assets/images/manifest.json (source board, box, category, usage) for ASSET-MANIFEST.md.
"""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SB = os.path.join(ROOT, 'source-boards')
OUT = os.path.join(ROOT, 'assets', 'images')

B = {
    1: 'board-01-maps-world-locations.png',
    2: 'board-02-maps-points-of-interest.png',
    3: 'board-03-raider-roles.png',
    4: 'board-04-raider-asset-board.png',
    5: 'board-05-loot-rare-components.png',
    6: 'board-06-loot-project-items.png',
    7: 'board-07-loot-common-components.png',
    8: 'board-08-icon-sheet.png',
    9: 'board-09-ui-asset-board.png',
    10: 'board-10-dashboard-mockup.png',
}

# (board, folder/filename, (x1,y1,x2,y2), usage)
C = []
def add(b, name, box, usage, **kw):
    C.append(dict(board=b, name=name, box=box, usage=usage, **kw))

# ---------- MAPS (board 1) ----------
add(1, 'maps/dam-battlegrounds-hero.webp', (24, 93, 826, 322), 'Map card, map hero, home Maps & Quick Access')
add(1, 'maps/buried-city-hero.webp', (848, 93, 1651, 322), 'Map card, map hero, home Maps & Quick Access')
add(1, 'maps/spaceport-hero.webp', (25, 533, 563, 736), 'Map card, map hero, home Maps & Quick Access')
add(1, 'maps/stella-montis-hero.webp', (587, 533, 1089, 736), 'Map card, map hero, home Maps & Quick Access')
add(1, 'maps/the-blue-gate-hero.webp', (1112, 533, 1651, 736), 'Map card, map hero, home Maps & Quick Access')
for i, x in enumerate([(36, 220), (234, 418), (432, 616), (630, 812)]):
    add(1, f'maps/dam-battlegrounds-thumb-{i+1}.webp', (x[0], 397, x[1], 495), 'Map detail gallery / POI tiles')
for i, x in enumerate([(862, 1045), (1060, 1243), (1257, 1440), (1454, 1637)]):
    add(1, f'maps/buried-city-thumb-{i+1}.webp', (x[0], 397, x[1], 495), 'Map detail gallery / POI tiles')
for i, x in enumerate([(32, 154), (167, 289), (301, 422), (435, 556)]):
    add(1, f'maps/spaceport-thumb-{i+1}.webp', (x[0], 802, x[1], 902), 'Map detail gallery / POI tiles')
for i, x in enumerate([(594, 710), (723, 837), (849, 963), (972, 1081)]):
    add(1, f'maps/stella-montis-thumb-{i+1}.webp', (x[0], 802, x[1], 902), 'Map detail gallery / POI tiles')
for i, x in enumerate([(1118, 1239), (1252, 1373), (1386, 1508), (1521, 1643)]):
    add(1, f'maps/the-blue-gate-thumb-{i+1}.webp', (x[0], 802, x[1], 902), 'Map detail gallery / POI tiles')

# ---------- MAPS / POIs (board 2) ----------
add(2, 'maps/riven-tides-hero.webp', (17, 151, 825, 382), 'Map card, map hero, home Maps & Quick Access')
add(2, 'maps/stella-montis-assembly.webp', (848, 151, 1655, 382), 'Featured route panel, Stella Montis Assembly POI, routes')
add(2, 'maps/stella-montis-medical-research.webp', (17, 591, 607, 786), 'Stella Montis Medical Research POI, routes')
add(2, 'maps/spaceport-launch-tower.webp', (626, 591, 1101, 786), 'Spaceport POI / route art')
add(2, 'maps/buried-city-town-square.webp', (1119, 591, 1655, 786), 'Buried City POI / route art')
for i, x in enumerate([(27, 180), (195, 348), (362, 515)]):
    add(2, f'maps/riven-tides-thumb-{i+1}.webp', (x[0], 395, x[1], 507), 'Riven Tides gallery / POI tiles')
for i, x in enumerate([(858, 1011), (1026, 1179), (1194, 1348)]):
    add(2, f'maps/stella-montis-assembly-thumb-{i+1}.webp', (x[0], 396, x[1], 509), 'Assembly POI gallery')
for i, x in enumerate([(26, 130), (143, 247), (260, 366)]):
    add(2, f'maps/stella-montis-medical-thumb-{i+1}.webp', (x[0], 797, x[1], 899), 'Medical Research POI gallery')
for i, x in enumerate([(637, 748), (761, 899)]):
    add(2, f'maps/spaceport-poi-thumb-{i+1}.webp', (x[0], 797, x[1], 899), 'Spaceport POI gallery')
for i, x in enumerate([(1128, 1222), (1236, 1330), (1345, 1439)]):
    add(2, f'maps/buried-city-poi-thumb-{i+1}.webp', (x[0], 797, x[1], 899), 'Buried City POI gallery')

# ---------- RAIDERS (board 3 + 4) ----------
for name, x in [('solo-scout', (19, 277)), ('heavy-looter', (298, 554)), ('tech-specialist', (573, 829)),
                ('mountain-runner', (849, 1103)), ('medic-support', (1123, 1379)), ('stealth-raider', (1398, 1654))]:
    add(3, f'raiders/raider-{name}.webp', (x[0], 160, x[1], 538), 'Raider archetype art: profiles, avatars, auth, hunts')
add(4, 'raiders/raider-squad-lineup.webp', (14, 130, 628, 509), 'Loot Hunts banner, Find Squad CTA')
add(4, 'raiders/raider-veteran-trader.webp', (746, 131, 1058, 444), 'Trade Board banner and sidebar')
add(4, 'raiders/raider-expedition-leader.webp', (1198, 131, 1436, 444), 'Routes / featured route, profile badge art')
add(4, 'raiders/raider-close-quarters.webp', (15, 584, 358, 849), 'Archetype gallery, hunts')
add(4, 'raiders/raider-engineer.webp', (589, 584, 888, 849), 'Archetype gallery, projects page')
add(4, 'raiders/raider-comms-operator.webp', (1123, 584, 1438, 849), 'Messages page banner')
for name, box in [('gear-trader-coins', (1066, 206, 1174, 289)), ('gear-trader-pack', (1066, 296, 1174, 369)),
                  ('gear-trader-device', (1066, 373, 1174, 444)), ('gear-leader-backpack', (1534, 148, 1651, 239)),
                  ('gear-leader-tablet', (1534, 251, 1651, 336)), ('gear-leader-compass', (1534, 346, 1651, 431)),
                  ('gear-rusher-helmet', (444, 591, 562, 679)), ('gear-rusher-knife', (444, 686, 562, 759)),
                  ('gear-rusher-ammo', (444, 766, 562, 844)), ('gear-engineer-drone', (979, 589, 1097, 677)),
                  ('gear-engineer-tools', (979, 684, 1097, 756)), ('gear-engineer-case', (979, 764, 1097, 844)),
                  ('gear-comms-radio', (1548, 589, 1651, 677)), ('gear-comms-dish', (1548, 678, 1651, 756)),
                  ('gear-comms-terminal', (1548, 761, 1651, 844))]:
    add(4, f'raiders/{name}.webp', box, 'Small decorative gear tiles (profile, messages, routes)')

# ---------- ITEMS (board 5, 6, 7) ----------
cols5 = [(24, 414), (436, 824), (848, 1236), (1258, 1648)]
rows5 = [(150, 338), (425, 615), (700, 897)]
names5 = [['rotary-encoder', 'magnetron', 'ion-sputter', 'magnetic-accelerator'],
          ['industrial-battery', 'advanced-mechanical-components', 'electrical-components', 'processor'],
          ['voltage-converter', 'sensor-module', 'power-cell', 'stabilizer-coil']]
for r, row in enumerate(names5):
    for c, n in enumerate(row):
        add(5, f'items/{n}.webp', (cols5[c][0], rows5[r][0], cols5[c][1], rows5[r][1]), 'Item card + item detail art (visual only)')
cols6 = [(18, 406), (433, 822), (850, 1239), (1267, 1654)]
rows6 = [(112, 268), (405, 560), (698, 838)]
names6 = [['headphones', 'vaporizer-regulator', 'sentinel-firing-core', 'queen-reactor'],
          ['matriarch-reactor', 'exodus-module', 'snow-globe', 'survey-sensor'],
          ['medical-canister', 'field-transmitter', 'trophy-component', 'prototype-relay']]
for r, row in enumerate(names6):
    for c, n in enumerate(row):
        add(6, f'items/{n}.webp', (cols6[c][0], rows6[r][0], cols6[c][1], rows6[r][1]), 'Item card + item detail art (visual only)')
cols7 = [(28, 286), (305, 557), (576, 827), (846, 1098), (1117, 1368), (1388, 1644)]
rows7 = [(136, 329), (558, 740)]
names7 = [['mechanical-components', 'wiring-bundle', 'battery-cells', 'scrap-electronics', 'circuit-board', 'tool-kit'],
          ['alloy-plate', 'adhesive-tube', 'filter-cartridge', 'canister-fuel', 'med-supply-pack', 'ration-crate']]
for r, row in enumerate(names7):
    for c, n in enumerate(row):
        add(7, f'items/art-{n}.webp', (cols7[c][0], rows7[r][0], cols7[c][1], rows7[r][1]), 'Category fallback art for item records without dedicated artwork')

# ---------- UI ICONS (board 8) ----------
cols8 = [(30, 213), (233, 417), (438, 622), (642, 826), (846, 1030), (1051, 1235), (1257, 1441), (1460, 1644)]
rows8 = [(172, 312), (420, 562), (668, 806)]
names8 = [['search', 'loot-intel', 'map', 'route', 'squad', 'message', 'trade', 'profile'],
          ['project', 'inventory', 'rarity', 'recycle', 'crafting', 'danger', 'difficulty', 'time'],
          ['value', 'filter', 'sort', 'location', 'extraction', 'warning', 'online', 'settings']]
for r, row in enumerate(names8):
    for c, n in enumerate(row):
        x1, x2 = cols8[c]; y1, y2 = rows8[r]
        cx = (x1 + x2) // 2; h = y2 - y1
        add(8, f'ui/icon-{n}.png', (cx - h // 2, y1, cx + h // 2, y2), 'UI icon (nav, stat rows, filters, buttons)', alpha=True)

# ---------- UI BOARD (board 9) ----------
for n, box in [('common', (596, 203, 673, 298)), ('uncommon', (699, 203, 777, 298)), ('rare', (802, 203, 880, 298)),
               ('epic', (906, 203, 984, 298)), ('legendary', (1013, 200, 1101, 300))]:
    add(9, f'ui/rarity-{n}.png', box, 'Rarity badge on item cards and item detail', alpha=True)
for n, box in [('low', (1170, 205, 1258, 285)), ('normal', (1290, 205, 1376, 285)),
               ('high', (1408, 205, 1497, 285)), ('very-high', (1529, 200, 1623, 285))]:
    add(9, f'ui/demand-{n}.png', box, 'Demand indicator on item cards / detail', alpha=True)
for n, box in [('safe', (44, 420, 118, 508)), ('risky', (143, 420, 219, 508)), ('high-threat', (245, 420, 322, 508)),
               ('hazard', (349, 418, 430, 508)), ('weather', (453, 420, 533, 508))]:
    add(9, f'ui/condition-{n}.png', box, 'Map conditions module, map risk', alpha=True)
for n, box in [('keep', (600, 436, 662, 496)), ('recycle', (717, 436, 779, 496)), ('sell', (831, 436, 893, 496)),
               ('trade', (945, 436, 1005, 486)), ('project', (1058, 436, 1118, 486))]:
    add(9, f'ui/action-{n}.png', box, 'Recommendation badge glyph (item detail)', alpha=True)
add(9, 'heroes/ring-city-strip.webp', (1180, 0, 1672, 128), 'Decorative header strip (projects / footer)')

# ---------- HEROES + BRANDING ----------
add(10, 'heroes/home-hero-overlook.webp', (668, 62, 1452, 356), 'Homepage hero background (right side)')
add(10, 'heroes/dam-run-route.webp', (806, 440, 1240, 520), 'Route card art (Dam route)')
add(3, 'heroes/raider-network-skyline.webp', (590, 0, 1540, 150), 'Page-banner background strip (maps / projects)')
add(9, 'branding/raider-network-mark.png', (48, 12, 160, 116), 'Header + footer brand mark', alpha=False)
add(8, 'branding/raider-network-mark-small.png', (62, 30, 160, 108), 'Favicon source', alpha=False)


def to_alpha(im):
    """Turn a dark-background glyph into transparent PNG: alpha from brightness above the backdrop."""
    im = im.convert('RGB')
    px = im.load(); w, h = im.size
    # sample backdrop from corners
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    bg = max(sum(c) / 3 for c in corners)
    out = Image.new('RGBA', im.size)
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            v = max(r, g, b)
            a = max(0, min(255, int((v - bg - 6) * 255 / max(1, 150 - bg))))
            op[x, y] = (r, g, b, a)
    return out


def main():
    cache = {}
    manifest = []
    for c in C:
        b = c['board']
        if b not in cache:
            cache[b] = Image.open(os.path.join(SB, B[b])).convert('RGB')
        im = cache[b].crop(c['box'])
        path = os.path.join(OUT, c['name'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if c.get('alpha'):
            im = to_alpha(im)
            im.save(path, optimize=True)
        elif path.endswith('.png'):
            im.save(path, optimize=True)
        else:
            im.save(path, 'WEBP', quality=86, method=6)
        manifest.append({'file': 'assets/images/' + c['name'], 'sourceBoard': 'source-boards/' + B[b],
                         'box': list(c['box']), 'size': list(im.size),
                         'category': c['name'].split('/')[0], 'usage': c['usage']})
    with open(os.path.join(OUT, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print(len(manifest), 'assets written')


if __name__ == '__main__':
    main()
