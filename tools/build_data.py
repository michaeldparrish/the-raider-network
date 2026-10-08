"""Build /data/*.json for The Raider Network v5.

Inputs
  tools/source-data/raidtheory-snapshot.json   English-only snapshot of RaidTheory/arcraiders-data
                                               (MIT, https://github.com/RaidTheory/arcraiders-data)
  tools/source-data/research.json              Hand-researched location / project facts with source URLs

Refresh the snapshot from a fresh clone:
  git clone --depth 1 https://github.com/RaidTheory/arcraiders-data /tmp/ard
  python3 tools/build_data.py --snapshot /tmp/ard
Then rebuild:
  python3 tools/build_data.py

Rules
  * Core item facts (rarity, type, value, weight, stack, recycle/salvage, recipes, quest + project
    requirements, ARC drop tables) come ONLY from the snapshot -> confidence VERIFIED COMMUNITY.
  * Map/area facts come from ARC drop tables (VERIFIED COMMUNITY) or research.json (COMMUNITY REPORT).
  * Nothing is taken from the generated concept art.
  * Difficulty / demand / Intel Score / recommendation are Raider Network estimates computed below.
"""
import json, glob, math, os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'source-data')
DATA = os.path.join(ROOT, 'data')
AS_OF = datetime.date(2026, 10, 5)
LAUNCH = datetime.date(2025, 10, 30)  # source start dates earlier than launch are placeholders -> unknown
REPO = 'https://github.com/RaidTheory/arcraiders-data'
SNAP_SOURCE = {'label': 'RaidTheory arcraiders-data (community game data, MIT)', 'url': REPO,
               'confidence': 'VERIFIED COMMUNITY'}

MAP_ID = {'dam_battlegrounds': 'dam-battlegrounds', 'the_spaceport': 'spaceport', 'buried_city': 'buried-city',
          'the_blue_gate': 'the-blue-gate', 'stella_montis_upper': 'stella-montis',
          'stella_montis_lower': 'stella-montis', 'stella_montis': 'stella-montis', 'riven_tides': 'riven-tides'}


def kebab(s):
    return s.replace('_', '-')


def en(v):
    return v.get('en') if isinstance(v, dict) else v


# --------------------------------------------------------------------------- snapshot
def make_snapshot(clone):
    snap = {'commit': os.popen(f'git -C "{clone}" log -1 --format="%H %cs"').read().strip(),
            'items': [], 'quests': [], 'projects': [], 'bots': [], 'hideout': [], 'mapEvents': []}
    for f in sorted(glob.glob(os.path.join(clone, 'items', '*.json'))):
        d = json.load(open(f))
        keep = {k: d.get(k) for k in ('id', 'type', 'rarity', 'value', 'weightKg', 'stackSize', 'foundIn',
                                      'recyclesInto', 'salvagesInto', 'recipe', 'craftBench', 'questItem',
                                      'updatedAt', 'addedIn', 'isWeapon', 'blueprintLocked')}
        keep['name'] = en(d['name']); keep['description'] = en(d.get('description')) or ''
        snap['items'].append(keep)
    for f in sorted(glob.glob(os.path.join(clone, 'quests', '*.json'))):
        d = json.load(open(f))
        snap['quests'].append({'id': d['id'], 'name': en(d['name']), 'trader': d.get('trader'), 'map': d.get('map'),
                               'objectives': [en(o) for o in d.get('objectives', [])],
                               'requiredItemIds': d.get('requiredItemIds') or [],
                               'rewardItemIds': d.get('rewardItemIds') or [],
                               'previousQuestIds': d.get('previousQuestIds') or [],
                               'nextQuestIds': d.get('nextQuestIds') or []})
    for p in json.load(open(os.path.join(clone, 'projects.json'))):
        snap['projects'].append({'id': p['id'], 'name': en(p['name']), 'description': en(p.get('description')),
                                 'startDate': p.get('startDate'), 'endDate': p.get('endDate'),
                                 'phases': [{'phase': ph.get('phase'), 'name': en(ph.get('name')),
                                             'description': en(ph.get('description')),
                                             'requirementItemIds': ph.get('requirementItemIds') or [],
                                             'hasCategoryRequirements': bool(ph.get('requirementCategories'))}
                                            for ph in p['phases']]})
    for b in json.load(open(os.path.join(clone, 'bots.json'))):
        snap['bots'].append({k: b.get(k) for k in ('id', 'name', 'type', 'threat', 'maps', 'drops')})
    for f in sorted(glob.glob(os.path.join(clone, 'hideout', '*.json'))):
        d = json.load(open(f))
        snap['hideout'].append({'id': d['id'], 'name': en(d['name']),
                                'levels': [{'level': l['level'], 'requirementItemIds': l.get('requirementItemIds') or []}
                                           for l in d.get('levels', [])]})
    ev = json.load(open(os.path.join(clone, 'map-events', 'map-events.json')))
    snap['mapEvents'] = [{'id': k, 'name': v['displayName'], 'category': v.get('category')}
                         for k, v in ev['eventTypes'].items() if k != 'none']
    os.makedirs(SRC, exist_ok=True)
    json.dump(snap, open(os.path.join(SRC, 'raidtheory-snapshot.json'), 'w'), separators=(',', ':'))
    print('snapshot', snap['commit'], len(snap['items']), 'items')


# --------------------------------------------------------------------------- art
DEDICATED_ART = {
    'rotary_encoder': 'rotary-encoder', 'magnetron': 'magnetron', 'ion_sputter': 'ion-sputter',
    'magnetic_accelerator': 'magnetic-accelerator', 'industrial_battery': 'industrial-battery',
    'advanced_mechanical_components': 'advanced-mechanical-components',
    'electrical_components': 'electrical-components', 'processor': 'processor',
    'voltage_converter': 'voltage-converter', 'sensors': 'sensor-module', 'arc_powercell': 'power-cell',
    'headphones': 'headphones', 'vaporizer_regulator': 'vaporizer-regulator',
    'sentinel_firing_core': 'sentinel-firing-core', 'queen_reactor': 'queen-reactor',
    'matriarch_reactor': 'matriarch-reactor', 'exodus_modules': 'exodus-module',
    'breathtaking_snow_globe': 'snow-globe', 'mechanical_components': 'art-mechanical-components',
    'wires': 'art-wiring-bundle', 'battery': 'art-battery-cells',
}
_UNUSED_TYPE_ART = {
    'Trinket': ('raiders', 'gear-trader-coins'), 'Blueprint': ('raiders', 'gear-leader-tablet'),
    'Key': ('raiders', 'gear-trader-device'), 'Augment': ('raiders', 'gear-leader-backpack'),
    'Shield': ('raiders', 'gear-engineer-case'), 'Modification': ('raiders', 'gear-engineer-tools'),
    'Ammunition': ('raiders', 'gear-rusher-ammo'), 'Nature': ('items', 'art-ration-crate'),
    'Basic Material': ('items', 'art-alloy-plate'), 'Refined Material': ('items', 'stabilizer-coil'),
    'Topside Material': ('items', 'art-circuit-board'), 'Special': ('items', 'prototype-relay'),
    'Misc': ('items', 'art-alloy-plate'),
}
WEAPON_TYPES = {'Assault Rifle', 'SMG', 'Pistol', 'Shotgun', 'Battle Rifle', 'Sniper Rifle', 'LMG', 'Hand Cannon'}


ART_POOLS = {
    'arc': [('items', 'trophy-component'), ('items', 'prototype-relay'), ('items', 'survey-sensor'), ('items', 'field-transmitter'), ('items', 'stabilizer-coil')],
    'tech': [('items', 'art-scrap-electronics'), ('items', 'art-circuit-board'), ('items', 'field-transmitter'), ('items', 'survey-sensor')],
    'industrial': [('items', 'art-filter-cartridge'), ('items', 'art-tool-kit'), ('items', 'art-canister-fuel'), ('items', 'stabilizer-coil')],
    'medical': [('items', 'medical-canister'), ('items', 'art-med-supply-pack')],
    'household': [('items', 'art-tool-kit'), ('items', 'art-adhesive-tube'), ('items', 'art-canister-fuel'), ('items', 'art-ration-crate'), ('items', 'art-scrap-electronics')],
    'topside': [('items', 'art-circuit-board'), ('items', 'art-scrap-electronics'), ('items', 'art-alloy-plate'), ('items', 'stabilizer-coil')],
    'refined': [('items', 'stabilizer-coil'), ('items', 'art-circuit-board'), ('items', 'art-alloy-plate')],
    'basic': [('items', 'art-alloy-plate')], 'nature': [('items', 'art-ration-crate')],
    'heal': [('items', 'art-med-supply-pack'), ('items', 'medical-canister')],
    'quick': [('items', 'art-adhesive-tube'), ('items', 'art-canister-fuel'), ('items', 'art-tool-kit')],
    'trinket': [('raiders', 'gear-trader-coins'), ('raiders', 'gear-leader-compass')],
    'blueprint': [('raiders', 'gear-leader-tablet'), ('raiders', 'gear-comms-terminal')],
    'key': [('raiders', 'gear-trader-device'), ('raiders', 'gear-comms-radio')],
    'weapon': [('raiders', 'gear-rusher-ammo'), ('raiders', 'gear-engineer-case')],
    'mod': [('raiders', 'gear-engineer-tools'), ('raiders', 'gear-engineer-drone')],
    'augment': [('raiders', 'gear-leader-backpack'), ('raiders', 'gear-trader-pack')],
    'shield': [('raiders', 'gear-engineer-case')], 'special': [('items', 'prototype-relay'), ('raiders', 'gear-engineer-drone')],
    'ammo': [('raiders', 'gear-rusher-ammo')],
}


def art_for(it):
    """Dedicated concept art where it exists; otherwise a category pool, picked deterministically per item
    so neighbouring cards do not all repeat the same picture. All art is visual only."""
    if it['id'] in DEDICATED_ART:
        return f"assets/images/items/{DEDICATED_ART[it['id']]}.webp", 'dedicated'
    t = it['type']; found = it.get('foundIn') or ''; name = it['name'].lower()
    if t in WEAPON_TYPES: pool = 'weapon'
    elif t == 'Quick Use': pool = 'heal' if any(w in name for w in ('bandage', 'med', 'syringe', 'vita', 'herbal', 'adrenaline', 'defib', 'heal')) else 'quick'
    elif t in ('Recyclable', 'Topside Material') and 'ARC' in found: pool = 'arc'
    elif t == 'Recyclable':
        pool = 'medical' if 'Medical' in found else 'industrial' if ('Industrial' in found or 'Mechanical' in found) else 'tech' if ('Electrical' in found or 'Technological' in found) else 'household'
    else:
        pool = {'Topside Material': 'topside', 'Refined Material': 'refined', 'Basic Material': 'basic', 'Nature': 'nature', 'Trinket': 'trinket',
                'Blueprint': 'blueprint', 'Key': 'key', 'Modification': 'mod', 'Augment': 'augment', 'Shield': 'shield', 'Special': 'special',
                'Ammunition': 'ammo', 'Misc': 'basic'}.get(t, 'household')
    opts = ART_POOLS[pool]
    folder, name_ = opts[sum(map(ord, it['id'])) % len(opts)]
    return f'assets/images/{folder}/{name_}.webp', 'category'


def group_for(t):
    if t in WEAPON_TYPES or t in ('Shield', 'Augment', 'Modification', 'Ammunition', 'Special'):
        return 'Gear'
    if t == 'Blueprint': return 'Blueprint'
    if t == 'Key': return 'Key'
    if t == 'Trinket': return 'Trinket'
    if t == 'Quick Use': return 'Consumable'
    return 'Loot & Materials'


# --------------------------------------------------------------------------- build
def status_for(start, end, today=AS_OF):
    if not end:
        return 'HISTORICAL' if start else 'HISTORICAL'
    if end.year >= 2040:
        return 'ACTIVE'
    if today > end:
        return 'HISTORICAL'
    if start and today < start:
        return 'UPCOMING'
    return 'ENDING SOON' if (end - today).days <= 3 else 'ACTIVE'


BASE_SOURCE = {'label': 'Base map images: RaidTheory arcraiders-data / arctracker.io (MIT); game content © Embark Studios',
               'url': 'https://github.com/RaidTheory/arcraiders-data'}


PENDOLA_SOURCE = {'short': 'in-game map (owner screenshots, 8 Oct 2026), labels by The Raider Network', 'label': 'Pendola Pass: in-game map and topographic destination screen (owner screenshots, 8 Oct 2026); labels and key by The Raider Network. Game imagery © Embark Studios AB',
                  'url': 'https://arcraiders.com/news/frozen-trail-2-0-update', 'confidence': 'OFFICIAL'}


def base_map_config(mid, bounds):
    """Per-map base image + independent MetaForge->image calibration (tools/calibrate_maps.py).
    Transform: imgPx = scale * metaforgeCoord + offset, in ORIGINAL image pixels (width/height).
    The browser divides by width/height, so any resized copy (src / srcSmall) uses the same numbers."""
    cal_p = os.path.join(SRC, 'map-calibration.json'); sz_p = os.path.join(SRC, 'basemap-sizes.json')
    cal = json.load(open(cal_p)) if os.path.exists(cal_p) else {}
    sizes = json.load(open(sz_p)) if os.path.exists(sz_p) else {}
    def level(img_key, cal_key, label, layer):
        sz = sizes.get(img_key)
        if not sz or not os.path.exists(os.path.join(ROOT, 'assets/images/maps/base', img_key + '.webp')):
            return None
        c = cal.get(cal_key)
        t = c['transform'] if c else None
        return {'id': str(layer) if layer is not None else 'all', 'label': label, 'layer': layer,
                'src': f'assets/images/maps/base/{img_key}.webp', 'srcSmall': f'assets/images/maps/base/{img_key}-sm.webp',
                'width': sz['origW'], 'height': sz['origH'],
                'calibrated': bool(t), 'scaleX': t and t['scaleX'], 'scaleY': t and t['scaleY'], 'offsetX': t and t['offsetX'], 'offsetY': t and t['offsetY'],
                'calibration': {'rmsPx': t['rmsPx'], 'maxPx': t['maxPx'], 'points': len(c['controlPoints'])} if t else None}
    if mid == 'stella-montis':
        levels = [level('stella-montis', 'stella-montis#2', 'Main level — Assembly · Medical · Lobby', 2),
                  level('stella-montis-upper', 'stella-montis', 'Sandbox · Metro · Seed Vault level', 1)]
    elif mid == 'pendola-pass':   # v6.1: labelled in-game map + topographic overview (not MetaForge-calibrated)
        levels = [level('pendola-pass', 'pendola-pass', 'Detailed map', None),
                  level('pendola-pass-terrain', 'pendola-pass-terrain', 'Terrain overview', None)]
    else:
        levels = [level(mid, mid, 'Full map', None)]
    levels = [l for l in levels if l]
    src = PENDOLA_SOURCE if mid == 'pendola-pass' else BASE_SOURCE
    return {'levels': levels, 'markerBounds': bounds, 'source': src if levels else None,
            'note': None if levels else 'Base map image not available yet. Add assets/images/maps/base/<mapId>.webp (+ -sm.webp), its size to tools/source-data/basemap-sizes.json, and control points to tools/calibrate_maps.py.',
            'calibrated': bool(levels) and all(l['calibrated'] for l in levels)}


def build():
    snap = json.load(open(os.path.join(SRC, 'raidtheory-snapshot.json')))
    research = json.load(open(os.path.join(SRC, 'research.json')))
    raw = {i['id']: i for i in snap['items']}
    name_of = lambda rid: raw[rid]['name'] if rid in raw else rid.replace('_', ' ').title()

    # ---------------- projects
    projects = []
    for p in snap['projects']:
        s = datetime.datetime.fromtimestamp(p['startDate'], datetime.timezone.utc).date() if p.get('startDate') else None
        e = datetime.datetime.fromtimestamp(p['endDate'], datetime.timezone.utc).date() if p.get('endDate') else None
        permanent = bool(e and e.year >= 2040)
        name = p['name'] + (' (Part 2)' if p['id'] == 'phantom_targets_part_2_project' else '')
        pid = {'expedition_project': 'expedition-2', 'expedition_project_s1': 'expedition-1', 'expedition_project_s3': 'expedition-3',
               'expedition_project_s4': 'expedition-4', 'expedition_project_s5': 'expedition-5'}.get(p['id'], kebab(p['id']).replace('-project', ''))
        stages = []
        for ph in p['phases']:
            stages.append({'stage': ph['phase'], 'name': ph['name'], 'description': ph['description'],
                           'requiredItems': [{'itemId': kebab(r['itemId']), 'quantity': r['quantity']}
                                             for r in ph['requirementItemIds']],
                           'rewards': [{'itemId': kebab(rw['itemId']), 'quantity': rw['quantity'],
                                        'forItemId': kebab(r['itemId'])}
                                       for r in ph['requirementItemIds'] for rw in (r.get('rewardItemIds') or [])],
                           'nonItemRequirement': ph['hasCategoryRequirements'] or not ph['requirementItemIds']})
        projects.append({'id': pid, 'name': name,
                         'type': 'Permanent' if permanent else ('Expedition' if 'expedition' in p['id'] else 'Limited-time'),
                         'startDate': s.isoformat() if s and s >= LAUNCH else None,
                         'endDate': None if permanent else (e.isoformat() if e else None),
                         'statusAsOf': status_for(s, e), 'description': p['description'], 'stages': stages,
                         'rewardsNote': 'Per-stage rewards are only listed where the source data includes them.',
                         'dataConfidence': 'VERIFIED COMMUNITY' if (s or permanent) else 'COMMUNITY REPORT',
                         'datesNote': None if (s or permanent) else 'Start/end dates are not present in the source data.',
                         'sources': [SNAP_SOURCE]})
    for rp in research['projects']:
        rp = dict(rp)
        s = datetime.date.fromisoformat(rp['startDate']); e = datetime.date.fromisoformat(rp['endDate'])
        rp['statusAsOf'] = status_for(s, e)
        projects.insert(0, rp)
    for p in projects:
        p['aliases'] = research['projectAliases'].get(p['id'], [])
    proj_by_id = {p['id']: p for p in projects}

    # usage indexes (item id -> uses)
    proj_uses, quest_uses, craft_uses, hideout_uses = {}, {}, {}, {}
    for p in projects:
        for st in p['stages']:
            for r in st['requiredItems']:
                proj_uses.setdefault(r['itemId'], []).append({'projectId': p['id'], 'stage': st['stage'],
                                                              'quantity': r['quantity']})
    quests = []
    for q in snap['quests']:
        qid = kebab(q['id'])
        maps = sorted({MAP_ID.get(m, kebab(m)) for m in (q.get('map') or [])})
        quests.append({'id': qid, 'name': q['name'], 'trader': q['trader'], 'maps': maps,
                       'objectives': q['objectives'],
                       'requiredItems': [{'itemId': kebab(r['itemId']), 'quantity': r['quantity']} for r in q['requiredItemIds']],
                       'rewards': [{'itemId': kebab(r['itemId']), 'quantity': r['quantity']} for r in q['rewardItemIds']],
                       'previous': [kebab(x) for x in q['previousQuestIds']], 'next': [kebab(x) for x in q['nextQuestIds']],
                       'dataConfidence': 'VERIFIED COMMUNITY'})
        for r in q['requiredItemIds']:
            quest_uses.setdefault(kebab(r['itemId']), []).append({'questId': qid, 'quantity': r['quantity']})
    for it in snap['items']:
        for ing, qty in (it.get('recipe') or {}).items():
            craft_uses.setdefault(kebab(ing), []).append({'itemId': kebab(it['id']), 'quantity': qty})
    hideout = []
    for h in snap['hideout']:
        hideout.append({'id': kebab(h['id']), 'name': h['name'],
                        'levels': [{'level': l['level'], 'requiredItems': [{'itemId': kebab(r['itemId']), 'quantity': r['quantity']}
                                                                         for r in l['requirementItemIds']]} for l in h['levels']]})
        for l in h['levels']:
            for r in l['requirementItemIds']:
                hideout_uses.setdefault(kebab(r['itemId']), []).append({'stationId': kebab(h['id']), 'level': l['level'],
                                                                         'quantity': r['quantity']})

    # ARC drops -> maps
    arc_drops = {}
    arcs = []
    for b in snap['bots']:
        maps = sorted({MAP_ID.get(m, kebab(m)) for m in (b.get('maps') or [])})
        arcs.append({'id': kebab(b['id']), 'name': b['name'].title(), 'type': b.get('type'), 'threat': b.get('threat'),
                     'maps': maps, 'drops': [kebab(d) for d in (b.get('drops') or [])]})
        for d in b.get('drops') or []:
            arc_drops.setdefault(kebab(d), []).append({'arc': b['name'].title(), 'maps': maps})

    # ---------------- items
    RARITY_SCORE = {'Common': 15, 'Uncommon': 35, 'Rare': 60, 'Epic': 85, 'Legendary': 100}
    BASE_DIFF = {'Common': 2, 'Uncommon': 3.5, 'Rare': 6, 'Epic': 7.5, 'Legendary': 9}
    value_of = lambda rid: (raw.get(rid.replace('-', '_')) or {}).get('value') or 0
    current = {p['id'] for p in projects if p['statusAsOf'] in ('ACTIVE', 'ENDING SOON')}
    loc_research = research['itemLocations']
    # ---- MetaForge cache (data/maps/*.json, produced by tools/sync_metaforge.py) — community map markers
    mf_index_path = os.path.join(DATA, 'maps', 'index.json')
    mf_index = json.load(open(mf_index_path)) if os.path.exists(mf_index_path) else {'maps': {}}
    mf_nature, mf_arc = {}, {}
    for mid, info in mf_index['maps'].items():
        fp = os.path.join(ROOT, info['file'])
        if not os.path.exists(fp): continue
        for mk in json.load(open(fp))['markers']:
            if mk.get('links', {}).get('itemId'):
                mf_nature.setdefault(mk['links']['itemId'], {}).setdefault(mid, 0)
                mf_nature[mk['links']['itemId']][mid] += 1
            if mk['category'] == 'arc':
                mf_arc.setdefault(mk['subcategory'], {}).setdefault(mid, 0)
                mf_arc[mk['subcategory']][mid] += 1
    MF_SOURCE = {'label': 'MetaForge community map data', 'url': 'https://metaforge.app/arc-raiders', 'confidence': 'COMMUNITY REPORT'}
    arc_sub = lambda name: name.lower().replace('the ', '').strip()
    db_art_path = os.path.join(SRC, 'db-art.json')
    db_art = json.load(open(db_art_path)) if os.path.exists(db_art_path) else {}
    pa_path = os.path.join(SRC, 'premium-art.json')
    premium_art = {k: v for k, v in (json.load(open(pa_path)) if os.path.exists(pa_path) else {}).items() if not k.startswith('_')}
    for k, v in premium_art.items():
        assert os.path.exists(os.path.join(ROOT, 'assets/images', v['file'])), 'missing premium art file ' + v['file']
    items = []
    SOURCE_REG = {'raidtheory': SNAP_SOURCE}
    for it in snap['items']:
        iid = kebab(it['id'])
        rec = [{'itemId': kebab(k), 'quantity': v} for k, v in (it.get('recyclesInto') or {}).items()]
        sal = [{'itemId': kebab(k), 'quantity': v} for k, v in (it.get('salvagesInto') or {}).items()]
        pu = proj_uses.get(iid, []); qu = quest_uses.get(iid, []); cu = craft_uses.get(iid, []); hu = hideout_uses.get(iid, [])
        drops = arc_drops.get(iid, [])

        # locations
        locations, maps, loc_conf = [], [], None
        if iid in loc_research:
            r = loc_research[iid]
            locations = r['locations']; loc_conf = r['confidence']
        elif drops and len(drops) <= 3:
            for d in drops:
                for m in d['maps']:
                    locations.append({'map': m, 'areas': [], 'method': f"Dropped by {d['arc']}",
                                      'confidence': 'VERIFIED COMMUNITY'})
            loc_conf = 'VERIFIED COMMUNITY'
        elif drops:
            allm = sorted({m for d in drops for m in d['maps']})
            for m in allm:
                locations.append({'map': m, 'areas': [], 'method': f"Common drop from {len(drops)} ARC types",
                                  'confidence': 'VERIFIED COMMUNITY', 'common': True})
            loc_conf = 'VERIFIED COMMUNITY'
        if it['type'] == 'Key' and not locations:
            for pre, mid in (('Dam ', 'dam-battlegrounds'), ('Buried City', 'buried-city'), ('Spaceport', 'spaceport'), ('Stella Montis', 'stella-montis'),
                             ('Blue Gate', 'the-blue-gate'), ('Riven Tides', 'riven-tides'), ('Seed Vault', 'stella-montis'), ('Hidden Bunker', 'spaceport')):
                if it['name'].startswith(pre) or pre.strip() in (it['description'] or ''):
                    locations.append({'map': mid, 'areas': [], 'method': (it['description'] or 'Opens a door on this map').rstrip('.'),
                                      'confidence': 'VERIFIED COMMUNITY'})
                    loc_conf = 'VERIFIED COMMUNITY'; break
        used_mf = False
        if iid in mf_nature:
            for mid, n in sorted(mf_nature[iid].items(), key=lambda kv: -kv[1]):
                locations.append({'map': mid, 'areas': [], 'method': f'{n} resource node{"s" if n != 1 else ""} mapped (MetaForge)',
                                  'confidence': 'COMMUNITY REPORT', 'source': 'metaforge', 'markerCount': n})
            used_mf = True
        arc_names = [d['arc'] for d in drops] if (drops and len(drops) <= 3) else []
        if iid == 'vaporizer-regulator': arc_names = ['Vaporizer']
        have = {l.get('map') for l in locations}
        for an in arc_names:
            for mid, n in sorted(mf_arc.get(arc_sub(an), {}).items(), key=lambda kv: -kv[1]):
                if mid in have: continue
                locations.append({'map': mid, 'areas': [], 'method': f'{an} spawn marker{"s" if n != 1 else ""} ×{n} (MetaForge)',
                                  'confidence': 'COMMUNITY REPORT', 'source': 'metaforge', 'markerCount': n})
                have.add(mid); used_mf = True
        if used_mf and not loc_conf: loc_conf = 'COMMUNITY REPORT'
        for l in locations:
            if l.get('map') and l['map'] not in maps:
                maps.append(l['map'])

        # ---- scores (Raider Network estimates)
        rarity = it['rarity']
        cur_proj = [u for u in pu if u['projectId'] in current]
        hist_proj = {u['projectId'] for u in pu if u['projectId'] not in current}
        demand = 1.0
        if cur_proj: demand += 4
        demand += min(2.0, 0.75 * len(hist_proj))
        if qu: demand += 2
        demand += min(2.0, 0.25 * len(cu))
        demand += min(1.0, 0.5 * len(hu))
        if rarity in ('Epic', 'Legendary'): demand += 1
        override = research['editorial'].get(iid, {})
        if 'demand' in override: demand = override['demand']
        demand = round(max(1, min(10, demand)), 1)

        difficulty = BASE_DIFF.get(rarity, 3)
        if maps and len(maps) == 1 and not any(l.get('common') for l in locations): difficulty += 1
        if any(d['arc'] in ('The Queen', 'Matriarch') for d in drops): difficulty += 1
        if 'difficulty' in override: difficulty = override['difficulty']
        difficulty = round(max(1, min(10, difficulty)), 1)

        rec_val = sum(value_of(r['itemId']) * r['quantity'] for r in rec)
        recycle_util = min(100, round(100 * rec_val / it['value'])) if rec and it['value'] else 0
        craft_util = min(100, len(cu) * 12 + len(hu) * 10)
        rc_util = max(recycle_util, craft_util)
        quest_util = 100 if qu else 0
        project_util = 100 if cur_proj else (60 if hist_proj else 0)
        value_score = min(100, round(100 * math.log10((it['value'] or 0) + 1) / math.log10(12001)))
        intel = round(0.20 * RARITY_SCORE.get(rarity, 15) + 0.20 * demand * 10 + 0.15 * quest_util +
                      0.15 * project_util + 0.15 * rc_util + 0.10 * difficulty * 10 + 0.05 * value_score)

        # ---- recommendation
        t = it['type']
        if cur_proj: recm = 'PROJECT CRITICAL'
        elif qu and all(u['quantity'] == 1 for u in qu) and not cu: recm = 'KEEP ONE'
        elif qu or len(cu) >= 3 or hu: recm = 'KEEP'
        elif t in ('Blueprint', 'Key'): recm = 'KEEP'
        elif group_for(t) in ('Gear', 'Consumable'): recm = None
        elif t == 'Trinket': recm = 'SELL'
        elif rec and recycle_util >= 60: recm = 'RECYCLE'
        elif rec and not cu: recm = 'RECYCLE' if recycle_util >= 40 else 'SELL'
        elif cu: recm = 'KEEP'
        else: recm = 'SELL'
        if 'recommendation' in override: recm = override['recommendation']

        detailed = iid in loc_research or (bool(locations) and (pu or qu))
        conf_level = 'High' if detailed else ('Medium' if (pu or qu or cu or rec) else 'Low')
        if not it.get('weightKg') and it.get('weightKg') != 0: conf_level = 'Low'
        img, img_kind = art_for(it)
        hero_img = img if img_kind == 'dedicated' else None
        if iid in db_art:
            img, img_kind = 'assets/images/' + db_art[iid]['file'], 'database'
        if iid in premium_art:   # v6.1: owner-approved premium art (tools/source-data/premium-art.json)
            img, img_kind = 'assets/images/' + premium_art[iid]['file'], 'premium'
        found = [s.strip() for s in (it.get('foundIn') or '').split(',') if s.strip()]
        notes = override.get('notes', '')
        sources = ['raidtheory'] + (['metaforge'] if used_mf else [])
        if used_mf: SOURCE_REG['metaforge'] = MF_SOURCE
        for src in (loc_research.get(iid, {}).get('sources') or []):
            key = re.sub(r'[^a-z0-9]+', '-', src['label'].lower()).strip('-')[:40]
            SOURCE_REG[key] = src; sources.append(key)
        items.append({
            'id': iid, 'name': it['name'], 'rarity': rarity, 'category': t, 'group': group_for(t),
            'description': it['description'] or None,
            'sellValue': it['value'], 'weight': it.get('weightKg'), 'stackSize': it.get('stackSize'),
            'lootZones': found, 'maps': maps, 'locations': locations,
            'containers': loc_research.get(iid, {}).get('containers', []),
            'arcSources': [d['arc'] for d in drops],
            'difficulty': difficulty, 'demand': demand,
            'recyclable': bool(rec), 'recycleOutputs': rec, 'salvageOutputs': sal,
            'quests': [u['questId'] for u in qu], 'projects': sorted({u['projectId'] for u in pu}),
            'craftingUses': [u['itemId'] for u in cu], 'workshopUses': [f"{u['stationId']}:{u['level']}" for u in hu],
            'recipe': [{'itemId': kebab(k), 'quantity': v} for k, v in (it.get('recipe') or {}).items()],
            'craftBench': it.get('craftBench'),
            'recommendation': recm, 'intelScore': intel,
            'scores': [RARITY_SCORE.get(rarity, 15), round(demand * 10), quest_util, project_util,
                       recycle_util, craft_util, round(difficulty * 10), value_score],
            'dataConfidence': conf_level,
            'locationConfidence': loc_conf or 'UNVERIFIED',
            'image': img.replace('assets/images/', ''), 'imageKind': img_kind,
            'heroImage': hero_img.replace('assets/images/', '') if hero_img else None,
            'addedIn': it.get('addedIn'), 'sourceUpdated': it.get('updatedAt'),
            'notes': notes, 'sources': sources,
        })
    items.sort(key=lambda x: (-x['intelScore'], x['name']))

    # ---------------- maps (merge research)
    maps_out = []
    for m in research['maps']:
        m = dict(m)
        m['arcs'] = [a['id'] for a in arcs if m['id'] in a['maps']]
        m['quests'] = [q['id'] for q in quests if m['id'] in q['maps']]
        mi = mf_index['maps'].get(m['id'])
        if mi:
            m['markerData'] = {'file': mi['file'], 'status': mi['status'], 'count': mi['count'], 'categories': mi['categories'],
                               'topSubcategories': mi['topSubcategories'], 'fetchedAt': mf_index.get('fetchedAt'), 'source': 'MetaForge'}
            m['arcMarkers'] = {sub: by[m['id']] for sub, by in mf_arc.items() if m['id'] in by}
        # Base map image slot: drop the real image in and set src (+ calibrate bounds to the image extents if needed).
        m['mapImage'] = base_map_config(m['id'], (mi or {}).get('bounds'))
        m.setdefault('status', 'live')
        maps_out.append(m)

    meta = {'sources': SOURCE_REG,
            'scoreKeys': ['rarity', 'demand', 'quest', 'project', 'recycling', 'crafting', 'difficulty', 'value'],
            'defaults': {'coreConfidence': 'VERIFIED COMMUNITY', 'usageConfidence': 'VERIFIED COMMUNITY',
                         'scoreConfidence': 'NETWORK ESTIMATE', 'imagesBase': 'assets/images/',
                         'imageNote': 'Item images are generated concept art for visual identity only - not in-game appearance.'},
            'generated': AS_OF.isoformat(), 'sourceCommit': snap['commit'], 'source': REPO,
            'counts': {'items': len(items), 'projects': len(projects), 'quests': len(quests), 'maps': sum(1 for m in maps_out if m.get('status') == 'live'),
                       'arcs': len(arcs)},
            'confidenceScale': ['OFFICIAL', 'VERIFIED COMMUNITY', 'COMMUNITY REPORT', 'UNVERIFIED'],
            'intelScore': {'weights': {'rarity': .20, 'demand': .20, 'quest': .15, 'project': .15,
                                       'recyclingOrCrafting': .15, 'difficulty': .10, 'merchantValue': .05},
                           'bands': [[0, 39, 'LOW VALUE'], [40, 59, 'USEFUL'], [60, 74, 'VALUABLE'],
                                     [75, 89, 'HIGH PRIORITY'], [90, 100, 'CRITICAL']],
                           'asOf': AS_OF.isoformat()}}

    os.makedirs(DATA, exist_ok=True)
    dump = lambda name, obj: json.dump(obj, open(os.path.join(DATA, name), 'w'), separators=(',', ':'), ensure_ascii=False)
    dump('items.json', {'meta': meta, 'items': items})
    dump('projects.json', {'meta': meta, 'projects': projects})
    dump('quests.json', {'meta': meta, 'quests': quests})
    for a in arcs:
        a['metaforgeMaps'] = mf_arc.get(arc_sub(a['name']), {})
    dump('arcs.json', {'meta': meta, 'arcs': arcs})
    dump('workshop.json', {'meta': meta, 'stations': hideout})
    json.dump({'meta': meta, 'maps': maps_out}, open(os.path.join(DATA, 'maps.json'), 'w'), indent=1, ensure_ascii=False)
    json.dump({'meta': {'note': 'Map condition names come from community data; the schedule below is DEMO data.'},
               'eventTypes': snap['mapEvents'], 'demoSchedule': research['demoConditions']},
              open(os.path.join(DATA, 'map-conditions.json'), 'w'), indent=1)
    print(meta['counts'])
    hi = [i['name'] for i in items if i['dataConfidence'] == 'High']
    print('High:', len(hi), hi)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--snapshot':
        make_snapshot(sys.argv[2])
    else:
        build()
