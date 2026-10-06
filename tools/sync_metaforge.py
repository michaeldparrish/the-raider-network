"""MetaForge map-data sync -> cached, normalized JSON in /data/maps/.

Architecture:  MetaForge API  ->  this sync job (run occasionally)  ->  data/maps/*.json  ->  Raider Network UI
The website NEVER calls MetaForge from a visitor's browser; pages only read the cached files.

Endpoint (observed from MetaForge's own interactive map, Oct 2026):
  GET https://metaforge.app/api/game-map-data?tableID=arc_map_data&mapID=<mapID>
  -> {"allData": [ {id, mapID, category, subcategory, lat, lng, zlayers, instanceName, behindLockedDoor,
                    lootAreas, eventConditionMask, community, routeID, sourceID, updated_at, added_by, last_edited_by}, ... ]}
MetaForge map IDs: dam, spaceport, buried-city, blue-gate, stella-montis, riven-tides (pendola-pass returns [] as of 5 Oct 2026)

Usage
  python3 tools/sync_metaforge.py --fetch                 # direct API fetch (where metaforge.app is reachable), 1 request/map, polite delay
  python3 tools/sync_metaforge.py --from-export FILE.gz   # normalise a browser export (see docs/METAFORGE-SYNC.md)
  python3 tools/sync_metaforge.py                         # re-normalise from the stored export in tools/source-data/

Attribution (required by MetaForge for public projects): "Map data sourced in part from MetaForge community data."
Commercial use: MetaForge asks paid/monetised projects to contact them first — confirm before enabling monetisation.
Coordinates are MetaForge map units (Leaflet CRS.Simple: x = lng, y = lat, y grows upward). Never edited or invented.
"""
import gzip, json, os, sys, time, urllib.request, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'source-data')
OUT = os.path.join(ROOT, 'data', 'maps')
EXPORT = os.path.join(SRC, 'metaforge-export.json.gz')
API = 'https://metaforge.app/api/game-map-data?tableID=arc_map_data&mapID={}'
ATTR = {'label': 'MetaForge community map data', 'url': 'https://metaforge.app/arc-raiders', 'confidence': 'COMMUNITY REPORT'}
# MetaForge mapID -> (Raider Network mapId, cache filename)
MAPS = {'dam': ('dam-battlegrounds', 'dam-battlegrounds-markers.json'), 'buried-city': ('buried-city', 'buried-city-markers.json'),
        'spaceport': ('spaceport', 'spaceport-markers.json'), 'stella-montis': ('stella-montis', 'stella-montis-markers.json'),
        'blue-gate': ('the-blue-gate', 'blue-gate-markers.json'), 'riven-tides': ('riven-tides', 'riven-tides-markers.json'),
        'pendola-pass': ('pendola-pass', 'pendola-pass-markers.json')}
CATEGORY_LABEL = {'containers': 'Containers', 'nature': 'Nature / Resources', 'events': 'Events', 'locations': 'Locations',
                  'arc': 'ARC', 'quests': 'Quests'}
NATURE_ITEM = {'candleberries': 'candleberries', 'great-mullein': 'great-mullein', 'moss': 'moss', 'mushroom': 'mushroom', 'agave': 'agave',
               'fertilizer': 'fertilizer', 'prickly-pear': 'prickly-pear', 'apricot': 'apricot', 'lemons': 'lemon', 'olive': 'olives', 'roots': 'roots'}


def fetch_all():
    out = {'source': 'MetaForge game-map-data API', 'endpoint': API.format('<id>'), 'fetchedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'maps': {}}
    for mf in MAPS:
        req = urllib.request.Request(API.format(mf), headers={'User-Agent': 'TheRaiderNetwork-sync/1.0 (cached community site; attribution provided)'})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = json.load(r)
        out['maps'][mf] = [{'id': m['id'], 'category': m.get('category'), 'subcategory': m.get('subcategory'), 'lat': m.get('lat'), 'lng': m.get('lng'),
                            'name': m.get('instanceName') or '', 'locked': bool(m.get('behindLockedDoor')), 'lootAreas': m.get('lootAreas') or '',
                            'zlayers': m.get('zlayers'), 'eventMask': m.get('eventConditionMask'), 'community': bool(m.get('community')),
                            'updated': (m.get('updated_at') or '')[:10]} for m in raw.get('allData', [])]
        print(mf, len(out['maps'][mf])); time.sleep(2)
    with gzip.open(EXPORT, 'wt') as f: json.dump(out, f)
    return out


def normalise(exp):
    os.makedirs(OUT, exist_ok=True)
    items = {i['id'] for i in json.load(open(os.path.join(ROOT, 'data', 'items.json')))['items']}
    quests = {q['id'] for q in json.load(open(os.path.join(ROOT, 'data', 'quests.json')))['quests']}
    arcs = {a['id'] for a in json.load(open(os.path.join(ROOT, 'data', 'arcs.json')))['arcs']}
    index = {'source': exp['source'], 'endpoint': exp.get('endpoint'), 'fetchedAt': exp['fetchedAt'], 'attribution': ATTR,
             'coordinateSystem': 'MetaForge map units (Leaflet CRS.Simple): x = lng, y = lat; y increases upward.',
             'categoryLabels': CATEGORY_LABEL, 'maps': {}}
    for mf, (mid, fn) in MAPS.items():
        rows = exp['maps'].get(mf, [])
        markers = []
        for m in rows:
            sub = (m.get('subcategory') or '').strip()
            cat = (m.get('category') or '').strip()
            links = {}
            if cat == 'nature' and NATURE_ITEM.get(sub) in items: links['itemId'] = NATURE_ITEM[sub]
            if cat == 'quests' and sub in quests: links['questId'] = sub
            if cat == 'arc' and 'arc-' + sub in arcs: links['arcId'] = 'arc-' + sub
            la = m.get('lootAreas') or ''
            markers.append({'id': m['id'], 'mapId': mid, 'category': cat, 'subcategory': sub, 'x': m['lng'], 'y': m['lat'],
                            'label': (m.get('name') or '').strip(), 'layer': 'all' if m.get('zlayers') in (None, 2147483647) else m.get('zlayers'),
                            'locked': bool(m.get('locked')), 'lootAreas': [s.strip() for s in la.split(',') if s.strip()] if isinstance(la, str) else la,
                            'eventMask': m.get('eventMask'), 'updated': m.get('updated'), 'source': 'MetaForge', **({'links': links} if links else {})})
        cats = collections.Counter(x['category'] for x in markers)
        subs = collections.defaultdict(collections.Counter)
        for x in markers: subs[x['category']][x['subcategory']] += 1
        bounds = None
        if markers:
            xs = [x['x'] for x in markers]; ys = [x['y'] for x in markers]
            bounds = {'minX': min(xs), 'maxX': max(xs), 'minY': min(ys), 'maxY': max(ys)}
        status = 'live' if markers else 'no-data'
        meta = {'mapId': mid, 'metaforgeMapId': mf, 'status': status, 'fetchedAt': exp['fetchedAt'], 'source': 'MetaForge', 'attribution': ATTR,
                'coordinateSystem': index['coordinateSystem'], 'bounds': bounds, 'count': len(markers),
                'categories': dict(cats.most_common()), 'subcategories': {c: dict(s.most_common()) for c, s in subs.items()}}
        with open(os.path.join(OUT, fn), 'w') as f:
            json.dump({'meta': meta, 'markers': markers}, f, separators=(',', ':'), ensure_ascii=False)
        index['maps'][mid] = {k: meta[k] for k in ('metaforgeMapId', 'status', 'count', 'bounds', 'categories')} | {'file': 'data/maps/' + fn,
            'topSubcategories': {c: dict(s.most_common(8)) for c, s in subs.items()}}
        print(f'{mid:20s} {status:8s} {len(markers):6d}  {dict(cats)}')
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)


if __name__ == '__main__':
    if '--fetch' in sys.argv:
        exp = fetch_all()
    else:
        path = sys.argv[sys.argv.index('--from-export') + 1] if '--from-export' in sys.argv else EXPORT
        exp = json.load(gzip.open(path, 'rt'))
        if path != EXPORT:
            os.makedirs(SRC, exist_ok=True)
            with gzip.open(EXPORT, 'wt') as f: json.dump(exp, f)
    normalise(exp)
