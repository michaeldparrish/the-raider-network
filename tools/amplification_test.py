"""v6.4 Amplification Guide + Hunt tests (data, images, pages, navigation, hand-offs) on Cloudflare's local runtime
with a THROW-AWAY local D1 database (tools/devserver.py). Never touches production.
  python3 tools/amplification_test.py [--shots DIR]
Covers: all 15 catalog entries (10 new + 5 preserved IDs, no duplicates), card/thumbnail images, module tiers and the
15 weapons, upgrade quantities vs the owner cheat sheet (conflicts flagged), prerequisites and exclusive branches, the
Guide (library, detail dialog, links), the Hunt (selection rules, totals without double counting, deep links),
Loot Hunt preselection, Loot Trails item carry + server-side item validation, trading a new item, site search,
the Loot Hunts dropdown (mouse, keyboard, touch drawer), the /hunts NEW button, clean URLs and mobile layouts."""
import sys, os, json, uuid
from playwright.sync_api import sync_playwright
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import DevServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
RESULTS, ERRORS = [], []
PW = 'Amp-Test-Pass-77'
NAMES = ['Amplification Module Mk. I', 'Amplification Module Mk. II', 'Amplification Module Mk. III', 'Amplification Module Mk. IV',
         'Amplification Module Mk. V', 'Pressure Regulator', 'Pneumatic Actuator', 'Fluted Rotor Core', 'Propellant Valve Assembly',
         'Fossilized Lightning', 'Assessor Matrix', 'Turbine Compressor', 'Queen Reactor', 'Matriarch Reactor', 'Amplified Fragments']
EXISTING = ['fossilized-lightning', 'assessor-matrix', 'turbine-compressor', 'queen-reactor', 'matriarch-reactor']
TIERS = {'mk-i': ['hairpin', 'kettle', 'rattler'], 'mk-ii': ['burletta', 'il-toro'], 'mk-iii': ['anvil', 'canto', 'osprey', 'rascal', 'renegade'],
         'mk-iv': ['bettina', 'hullcracker'], 'mk-v': ['aphelion', 'equalizer', 'jupiter']}
# owner cheat sheet (weapon, upgrade, material, qty)
SHEET = """hairpin incendiary-rounds fossilized-lightning 3|hairpin semi-auto pneumatic-actuator 3|hairpin sprint-shooting fluted-rotor-core 3|hairpin tracker-rounds matriarch-reactor 1
rattler incendiary-rounds fossilized-lightning 3|rattler more-reload propellant-valve-assembly 2|rattler drum-mag pressure-regulator 4
kettle x-rounds fossilized-lightning 3|kettle anti-shield assessor-matrix 3|kettle full-auto pneumatic-actuator 3
burletta sprint-shooting fluted-rotor-core 3|burletta full-auto pneumatic-actuator 3|burletta burst-fire queen-reactor 2|burletta increased-burst pressure-regulator 2
il-toro more-reload propellant-valve-assembly 2|il-toro slug-rounds turbine-compressor 4|anvil x-rounds fossilized-lightning 3|anvil anvil-splitter turbine-compressor 3
canto incendiary-rounds fossilized-lightning 3|canto carbine-conversion propellant-valve-assembly 3|canto sprint-shooting fluted-rotor-core 3
osprey ergonomic-bolt fluted-rotor-core 3|osprey tracker-rounds matriarch-reactor 2|osprey anti-weak-point assessor-matrix 2
rascal high-velocity pneumatic-actuator 2|rascal sprint-shooting fluted-rotor-core 2|rascal incendiary-grenades fossilized-lightning 3
renegade more-reload propellant-valve-assembly 2|renegade scoped fluted-rotor-core 4|bettina bigger-mag pressure-regulator 3|bettina semi-auto pneumatic-actuator 3|bettina x-rounds fossilized-lightning 3
hullcracker incendiary-grenades fossilized-lightning 3|hullcracker mag-reload propellant-valve-assembly 3
aphelion bigger-mag pressure-regulator 3|aphelion incendiary-rounds fossilized-lightning 3|aphelion charged-burst queen-reactor 2|aphelion increased-burst pressure-regulator 2
equalizer bigger-mag pressure-regulator 3|equalizer ramping-damage queen-reactor 3|equalizer anti-weak-point assessor-matrix 2
jupiter bigger-mag pressure-regulator 3|jupiter scoped fluted-rotor-core 3|jupiter ergonomic-bolt fluted-rotor-core 3"""
KNOWN_CONFLICTS = {('burletta', 'sprint-shooting'), ('canto', 'sprint-shooting')}


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def shot(page, name, full=True):
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name + '.png'), full_page=full)


def data_checks():
    items = json.load(open(os.path.join(ROOT, 'data/items.json')))['items']
    amp = json.load(open(os.path.join(ROOT, 'data/amplification.json')))
    by_name = {}
    for i in items: by_name.setdefault(i['name'].lower(), []).append(i)
    check(all(len(by_name.get(n.lower(), [])) == 1 for n in NAMES), 'all 15 amplification materials are in the catalog exactly once (exact names)')
    check(len({i['id'] for i in items}) == len(items) and len(by_name) == len(items), 'catalog has no duplicate IDs or names')
    idx = {i['id']: i for i in items}
    check(all(e in idx and idx[e]['imageKind'] != 'illustration' and 'coreConfidence' not in idx[e] for e in EXISTING),
          'the 5 existing items keep their IDs and v6.3 records (only an amplification link is added)')
    new = [i for i in items if i['imageKind'] == 'illustration']
    check(len(new) == 10 and all(i['addedIn'] == '2.0' and i['coreConfidence'] == 'COMMUNITY REPORT' for i in new), '10 new items added, marked Frozen Trail 2.0 / community data')
    check(all(idx[by_name[n.lower()][0]['id']].get('amplification', {}).get('guide', '').startswith('amplification.html#item-') for n in NAMES), 'all 15 link to the Amplification Guide')
    ok_img = True
    for m in amp['materials']:
        for rel in (m['card'], m['thumb'], idx[m['itemId']]['image']):
            p = os.path.join(ROOT, 'assets/images', rel)
            try:
                if rel.endswith('.svg'): assert os.path.getsize(p) > 100 and open(p).read(5) in ('<svg ', '<?xml')
                else: Image.open(p).verify()
            except Exception: ok_img = False; print('   bad image', rel)
    check(ok_img and len(amp['materials']) == 15, 'every material has a valid card image, thumbnail and catalog image (incl. Assessor Matrix, Pneumatic Actuator)')
    mods = [Image.open(os.path.join(ROOT, f'assets/images/amplification/cards/amplification-module-{t}.webp')) for t in TIERS]
    check(all(abs(im.width - 434) <= 2 and im.height == 724 for im in mods), 'Mk. I–V module cards keep the supplied gold portrait artwork (434×724)')
    check(all(os.path.exists(os.path.join(ROOT, 'tools/source-art/amplification', f)) for f in ('assessor-matrix.png', 'pneumatic-actuator.png')) and
          len(os.listdir(os.path.join(ROOT, 'tools/source-art/amplification'))) == 15, 'the 15 original PNGs are preserved unmodified in tools/source-art/amplification')
    check({t['id']: t['weapons'] for t in amp['tiers']} == TIERS, 'module tiers map to the 15 eligible weapons exactly as specified')
    W = {w['id']: w for w in amp['weapons']}
    check(len(W) == 15 and all(w['itemId'] in idx for w in W.values()), 'all 15 weapons resolve to catalog weapon records (tier IV)')
    bad = []
    for line in SHEET.replace('\n', '|').split('|'):
        w, u, m, q = line.split(); q = int(q)
        up = next((x for x in W[w]['upgrades'] if x['id'] == u), None)
        c = next((x for x in (up or {}).get('cost', []) if x['itemId'] == m), None)
        if not c: bad.append(line); continue
        if (w, u) in KNOWN_CONFLICTS:
            if c['status'] != 'CONFLICT': bad.append(line + ' (should be flagged CONFLICT)')
        elif c['qty'] != q: bad.append(line + f' (have {c["qty"]})')
    check(not bad, f'44 cheat-sheet upgrade costs present; Burletta/Canto Sprint Shooting flagged as conflicting {bad[:3]}')
    check(sum(len(w['upgrades']) for w in W.values()) == 44, 'exactly 44 upgrades across 15 weapons')
    sym = all(u['id'] in next(x for x in w['upgrades'] if x['id'] == e)['excludes'] for w in W.values() for u in w['upgrades'] for e in u['excludes'])
    req_ok = all(r in {x['id'] for x in w['upgrades']} for w in W.values() for u in w['upgrades'] for r in u['requires'])
    check(sym and req_ok, 'exclusive branches are symmetric and every prerequisite exists')
    ex = {(w['id'], u['id']): set(u['excludes']) for w in W.values() for u in w['upgrades']}
    check(ex[('bettina', 'bigger-mag')] >= {'semi-auto'} and ex[('hairpin', 'incendiary-rounds')] == {'semi-auto', 'tracker-rounds'} and ex[('kettle', 'x-rounds')] == {'anti-shield', 'full-auto'}
          and ex[('anvil', 'x-rounds')] == {'anvil-splitter'} and ex[('osprey', 'tracker-rounds')] == {'anti-weak-point'} and ex[('equalizer', 'ramping-damage')] == {'anti-weak-point'},
          'known exclusions are modelled (Bettina, Hairpin, Kettle, Anvil, Osprey, Equalizer)')
    statuses = {c['status'] for w in W.values() for u in w['upgrades'] for c in u['cost']} | {l['status'] for m in amp['materials'] for l in m['locations']}
    check(statuses <= {'CONFIRMED', 'REPORTED', 'UNVERIFIED', 'CONFLICT'} and 'CONFLICT' in statuses and 'REPORTED' in statuses, 'every quantity and location carries a verification status')
    tc = next(m for m in amp['materials'] if m['itemId'] == 'turbine-compressor')
    check(all(l['status'] != 'CONFIRMED' for l in tc['locations']), 'Turbine Compressor location is not presented as confirmed')
    return items, amp


def api(page, method, path, body=None):
    return page.evaluate("""async ([m, p, b]) => { const r = await fetch('/api' + p, { method: m, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-TRN-CSRF': '1', Accept: 'application/json' }, body: b ? JSON.stringify(b) : undefined });
        return { status: r.status, data: await r.json().catch(() => null) }; }""", [method, path, body])


def new_user(browser, base, name, mobile=False):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844} if mobile else {'width': 1440, 'height': 900}, is_mobile=mobile, has_touch=mobile)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: ERRORS.append(f'{name}: {e}'))
    pg.goto(base + 'index.html'); pg.wait_for_load_state('networkidle')
    u = (name.lower() + uuid.uuid4().hex[:5])[:20]
    r = api(pg, 'POST', '/auth/register', {'username': u, 'display_name': name, 'email': f'{u}@example.com', 'password': PW, 'confirm_password': PW, 'region': 'NA East', 'platform': 'PC'})
    assert r['status'] == 201, r
    return pg


def overflow(pg): return pg.evaluate('document.documentElement.scrollWidth > innerWidth + 1 || innerWidth > screen.width + 1')


def main():
    items, amp = data_checks()
    srv = DevServer(port=8796); srv.migrate(); srv.start(); B = srv.base
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            anon = br.new_context(viewport={'width': 1440, 'height': 900}).new_page(); anon.on('pageerror', lambda e: ERRORS.append(f'anon: {e}'))
            # ---- clean URLs
            for path in ('amplification', 'amplification/hunt'):
                r = anon.goto(B + path); check(r.status == 200, f'/{path} serves the page (clean URL, 200)')
            # ---- Guide
            anon.goto(B + 'amplification', wait_until='networkidle')
            check(anon.locator('.amp-lib__card').count() == 15 and anon.locator('.amp-tier').count() == 5 and anon.locator('.amp-loc').count() >= 8 and anon.locator('.amp-tree').count() == 15,
                  'Guide shows 15 materials, 5 module tiers, the farming locations and 15 upgrade trees')
            check(all(anon.locator(f'#{s}').count() == 1 for s in ('overview', 'modules', 'farming', 'library', 'upgrades', 'sources')) and anon.locator('.amp-toc a').count() == 6,
                  'Guide has the overview / modules / farming / materials / upgrades sections with a section nav')
            check(anon.locator('.amp-hero a[href="amplification/hunt.html"]', has_text='Start an Amplification Hunt').count() == 1, 'Guide has a Start an Amplification Hunt button')
            for name in ('arc-frigate', 'fallen-emperor', 'redirection', 'pendola-pass', 'electromagnetic-storm', 'arc-assessor', 'queen', 'matriarch'):
                pass
            check(all(anon.locator(f'#loc-{n}').count() == 1 for n in ('arc-frigate', 'fallen-emperor', 'redirection', 'pendola-pass', 'electromagnetic-storm', 'arc-assessor', 'queen', 'matriarch')),
                  'dedicated sections for ARC Frigate, Fallen Emperor, Emperor Payloads/Redirection, Pendola Pass, Electromagnetic Storm, ARC Assessor, Queen, Matriarch')
            check(anon.locator('.amp-st--con').count() > 0 and anon.locator('.amp-st--unv').count() > 0 and anon.locator('.amp-st--rep').count() > 0, 'confirmed / reported / unverified / conflicting labels are visible')
            for _ in range(30): anon.mouse.wheel(0, 800); anon.wait_for_timeout(40)
            anon.wait_for_timeout(500)
            broken = anon.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src'))")
            check(not broken, f'no broken images on the Guide {broken[:3]}')
            opened = 0
            for n in NAMES:
                iid = next(i['id'] for i in items if i['name'] == n)
                anon.click(f'#lib-{iid} .amp-lib__art'); anon.wait_for_selector('#ampDetail:not(.hidden)')
                t = anon.inner_text('#ampDetail')
                if n.upper() in t.upper() and anon.locator(f'#ampDetail a[href="hunts.html?new={iid}"]').count() == 1 and anon.locator(f'#ampDetail a[href="item.html?id={iid}"]').count() == 1 \
                        and anon.locator(f'#ampDetail a[href="trails.html?item={iid}"]').count() == 1 and anon.evaluate("document.querySelector('#ampDetail img').naturalWidth > 0"):
                    opened += 1
                if n == 'Assessor Matrix': shot(anon, 'v64-guide-detail-assessor', False)
                anon.keyboard.press('Escape')
                if n == 'Queen Reactor': focus_back = anon.evaluate("document.activeElement?.closest('#lib-queen-reactor') !== null")
            check(focus_back, 'closing the detail view returns focus to the card that opened it')
            check(opened == 15, f'each of the 15 materials opens a detail view with image, Loot Hunt, Loot Trail and catalog links ({opened}/15)')
            anon.goto(B + 'amplification#item-%E0', wait_until='networkidle'); anon.fill('#ampSearch', 'frigate'); anon.wait_for_timeout(150)
            check(int(anon.inner_text('#ampLibCount')) < 15, 'a malformed #item- link does not break the Guide')
            anon.fill('#ampSearch', '')
            anon.goto(B + 'amplification#item-amplified-fragments', wait_until='networkidle')
            check(anon.is_visible('#ampDetail') and 'AMPLIFIED FRAGMENTS' in anon.inner_text('#ampDetailTitle').upper(), 'a #item- link opens that material directly')
            anon.keyboard.press('Escape')
            anon.fill('#ampSearch', 'frigate'); anon.wait_for_timeout(150)
            n_frig = int(anon.inner_text('#ampLibCount'))
            anon.fill('#ampSearch', ''); anon.select_option('#ampRole', 'activation'); anon.wait_for_timeout(150)
            check(0 < n_frig < 15 and int(anon.inner_text('#ampLibCount')) == 5, 'library search and type filter work')
            shot(anon, 'v64-guide')
            # ---- item pages + search
            bad_items = []
            for n in NAMES:
                iid = next(i['id'] for i in items if i['name'] == n)
                anon.goto(B + f'item.html?id={iid}', wait_until='networkidle')
                if anon.locator('.amp-item-link a[href^="amplification.html#item-"]').count() != 1 or n.upper() not in anon.inner_text('h1').upper(): bad_items.append(iid)
            check(not bad_items, f'all 15 catalog item pages render and link to the Guide {bad_items}')
            anon.goto(B + 'loot.html', wait_until='networkidle'); anon.click('#openSearch'); anon.fill('#overlaySearch', 'pneumatic'); anon.wait_for_timeout(300)
            check('Pneumatic Actuator' in anon.inner_text('#searchOverlay'), 'site-wide search finds a new amplification material')
            anon.goto(B + 'loot.html?q=Amplification', wait_until='networkidle')
            check(anon.locator('#lootResults .item-card', has_text='Amplification Module').count() >= 5, 'Loot Intel search lists the Amplification Modules')
            # ---- Hunt: Select weapon -> Already amplified? -> Enhancements -> Review materials -> Track
            h = anon
            COMBINED = "rs => Object.fromEntries(rs.map(r => [r.querySelector('th strong').textContent.trim(), [r.querySelector('.amp-cm__q').textContent.trim(), r.querySelector('.amp-cm__o').textContent.trim()]]))"
            comb = lambda pg: pg.eval_on_selector_all('#planCombined tbody tr', COMBINED)
            h.goto(B + 'amplification/hunt', wait_until='networkidle')
            check(h.locator('[data-weapon]').count() == 15 and h.locator('.amp-tierrow').count() == 5, 'Hunt step 1 lists all 15 weapons grouped by module tier')
            broken = h.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src'))")
            check(not broken, f'weapon images load on the Hunt page (base href) {broken[:2]}')
            h.click('[data-weapon=burletta]')
            check(h.locator('#step-amplified [data-amp]').count() == 2 and h.locator('#step-upgrade').count() == 0, 'step 2 asks whether the weapon is already amplified before enhancements are shown')
            check('MK. II' in h.inner_text('#step-amplified').upper(), 'the "No" option names the matching module (Mk. II for Burletta)')
            h.click('[data-amp=no]')
            h.click('[data-up=increased-burst]'); h.click('[data-up=sprint-shooting]')
            check(h.is_checked('[data-up=burst-fire]') and h.is_disabled('[data-up=burst-fire]') and h.is_disabled('[data-up=full-auto]'),
                  'step 3: Increased Burst pulls in Burst Fire and blocks the exclusive Full-Auto')
            check('weapon=burletta' in h.url and 'amplified=no' in h.url and 'increased-burst' in h.url, 'the plan (weapon, activation answer, enhancements) is kept in the URL')
            check(h.locator('#planActivation .amp-pl__row', has_text='Amplification Module Mk. II').count() == 1 and h.locator('#planEnhancements .amp-pl__enh').count() == 3,
                  'review separates initial amplification (module) from the selected enhancements (incl. prerequisite)')
            c = comb(h)
            check(c.get('Amplification Module Mk. II') == ['×1', '×1'] and c.get('Queen Reactor') == ['×2', '×2'] and c.get('Pressure Regulator') == ['×2', '×2']
                  and c.get('Fluted Rotor Core') == ['×4', '×4'] and c.get('Pop Trigger') == ['×20', '×20'] and c.get('Comet Igniter') == ['×10', '×10'],
                  f'combined materials total every stage, prerequisite and research part {c}')
            check(h.locator('#planCombined tr', has_text='Fluted Rotor Core').locator('.amp-st--con').count() == 1, 'the conflicting Sprint Shooting quantity is labelled')
            h.fill('[data-have=pressure-regulator]', '1'); h.fill('[data-have=fluted-rotor-core]', '4')
            c = comb(h)
            check(c['Pressure Regulator'][1] == '×1' and c['Fluted Rotor Core'][1].upper() == 'DONE', 'materials I already have reduce what is still to hunt')
            n_all = h.locator('[data-sel]:not([disabled])').count()
            check(f'({n_all})' in h.inner_text('#ampTrackGo'), 'Start Hunt for Selected Materials starts with every material selected')
            h.click('#ampSelNone'); check(h.is_disabled('#ampTrackGo') and '(0)' in h.inner_text('#ampTrackGo'), 'Select none clears the selection and disables the action')
            h.click('#ampSelAll'); h.uncheck('[data-sel=pop-trigger]')
            check(f'({n_all - 1})' in h.inner_text('#ampTrackGo'), 'individual materials can be deselected')
            h.click('[data-amp=yes]')
            c = comb(h)
            check('Amplification Module Mk. II' not in c and 'NOT NEEDED' in h.inner_text('#planActivation').upper(), 'answering "already amplified" leaves the module out of the plan')
            h.click('[data-amp=no]')
            shot(h, 'v64-hunt-burletta-plan')
            h.goto(B + 'amplification/hunt?weapon=equalizer&amplified=no&upgrade=ramping-damage', wait_until='networkidle')
            check(comb(h).get('Queen Reactor', [''])[0] == '×5' and h.is_disabled('[data-up=anti-weak-point]'), 'a material used by an enhancement and its research is totalled once (Queen Reactor 3 + 2 = 5)')
            h.goto(B + 'amplification/hunt?weapon=aphelion&amplified=yes&upgrade=increased-burst,bigger-mag', wait_until='networkidle')
            c = comb(h)
            check(c.get('Pressure Regulator', [''])[0] == '×5' and c.get('Queen Reactor', [''])[0] == '×2' and 'Amplification Module Mk. V' not in c, 'shared material adds across enhancements without double-counting the prerequisite')
            h.goto(B + 'amplification/hunt?weapon=hairpin&amplified=no&upgrade=sprint-shooting', wait_until='networkidle')
            check(h.is_checked('[data-up=semi-auto]') and h.is_disabled('[data-up=incendiary-rounds]') and h.is_disabled('[data-up=tracker-rounds]'), 'Hairpin Sprint Shooting requires Semi-Auto, which closes Incendiary and Tracker Rounds')
            h.goto(B + 'amplification/hunt?material=turbine-compressor', wait_until='networkidle')
            check(h.locator('.amp-wbtn.on').count() == 1 and h.locator('#step-amplified').count() == 1, '?material= opens the weapon that needs it and asks the activation question')
            h.goto(B + 'amplification/hunt?weapon=kettle&amplified=no&upgrade=anti-shield', wait_until='networkidle')
            h.click('.amp-track__single summary'); h.select_option('#ampHuntMat', 'assessor-matrix')
            check(h.get_attribute('#ampStartHunt', 'href') == 'hunts.html?new=assessor-matrix' and h.get_attribute('#ampAddTrail', 'href') == 'trails.html?item=assessor-matrix',
                  'the single-material option is kept')
            h.click('#ampTrackGo'); h.wait_for_selector('#ampTrailPick a, #ampTrailPick .notice-bar, #ampTrailForm')
            check(h.locator('#ampTrailPick a[href^="auth.html?next="]').count() == 1, 'tracking in a Loot Trail asks a logged-out Raider to log in (and comes back)')
            h.locator('#mainNav > a[data-nav=hunts]').hover(); h.wait_for_timeout(200)
            check(h.is_visible('#navHuntsMenu .is-amp') and h.locator('#mainNav > a.active[data-nav=hunts]').count() == 1, 'Loot Hunts is highlighted and its dropdown works on the Hunt page')
            h.mouse.move(1430, 890); h.wait_for_timeout(300)
            h.locator('.amp-hero__legend a').click(); h.wait_for_load_state('networkidle')
            check(h.evaluate('document.body.dataset.page') == 'amplification', 'Hunt page links to the Guide (relative links work under /amplification/)')
            # ---- logged-in: multi-material Quick Hunt
            u = new_user(br, B, 'Ampy')
            u.goto(B + 'amplification/hunt?weapon=burletta&amplified=no&upgrade=increased-burst,sprint-shooting', wait_until='networkidle')
            u.uncheck('[data-sel=pop-trigger]'); u.uncheck('[data-sel=comet-igniter]'); u.fill('[data-have=queen-reactor]', '1'); u.fill('[data-have=pressure-regulator]', '5')
            u.click('#ampTrackGo'); u.click('#ampQuickPlan'); u.wait_for_selector('#huntPlanBox')
            pb = u.inner_text('#huntPlanBox')
            check('BURLETTA AMPLIFICATION' in pb.upper() and 'INCREASED BURST' in pb.upper() and 'Queen Reactor\n×1' in pb and 'Pop Trigger' not in pb and 'Pressure Regulator' not in pb,
                  'Post a Quick Hunt opens the Loot Hunt popup with the whole build and only the selected materials (quantities still to hunt)')
            shot(u, 'v64-quick-hunt-plan', False)
            u.fill('#huntForm [name=description]', 'Burletta parts run'); u.click('#huntForm button[type=submit]'); u.wait_for_timeout(900)
            card = u.locator('#huntGrid .hunt-card--multi').first
            check(card.count() == 1 and 'MATERIALS' in card.inner_text().upper() and card.locator('.hunt-mats li').count() >= 3, 'the board shows one multi-material hunt card listing the materials')
            check(card.locator('h3 a').get_attribute('href').startswith('amplification/hunt.html?weapon=burletta&amplified=no'), 'the hunt card links back to the saved build')
            u.goto(B + 'hunts.html?item=fluted-rotor-core', wait_until='networkidle')
            check(u.locator('#huntGrid .hunt-card--multi').first.is_visible(), 'filtering the board by any listed material finds the multi-material hunt')
            u.goto(B + 'item.html?id=fluted-rotor-core', wait_until='networkidle')
            check('1 hunting this now' in u.inner_text('main').lower() or u.locator('a.link-row', has_text='Ampy').count() >= 1, 'the material\'s item page lists the multi-material hunt')
            # ---- single-material Quick Hunt still works
            u.goto(B + 'amplification/hunt?weapon=kettle&amplified=yes&upgrade=anti-shield', wait_until='networkidle')
            u.click('.amp-track__single summary'); u.select_option('#ampHuntMat', 'assessor-matrix'); u.click('#ampStartHunt'); u.wait_for_selector('#huntModal:not(.hidden)')
            check(u.input_value('#huntForm [name=itemName]') == 'Assessor Matrix' and u.locator('#huntPlanBox').count() == 0, 'single-material Start Loot Hunt opens the normal Quick Hunt form')
            u.fill('#huntForm [name=description]', 'v6.4 test'); u.click('#huntForm button[type=submit]'); u.wait_for_timeout(800)
            check(u.locator('#huntGrid .hunt-card:not(.hunt-card--multi)', has_text='Assessor Matrix').count() >= 1, 'the single-material Quick Hunt publishes as before')
            # ---- logged-in: Loot Trail plan
            u.goto(B + 'amplification/hunt?weapon=burletta&amplified=no&upgrade=increased-burst,sprint-shooting', wait_until='networkidle')
            u.fill('[data-have=pressure-regulator]', '1'); u.uncheck('[data-sel=pop-trigger]')
            u.click('#ampTrackGo'); u.wait_for_selector('#ampTrailForm')
            check(u.input_value('#ampTrailForm [name=trail]') == '__new' and u.is_visible('#ampTrailForm [name=mapId]'), 'with no trails yet, the plan offers to start a new Loot Trail (with a map for pins)')
            u.click('#ampTrailForm button[type=submit]'); u.wait_for_url('**/trails*id=*', timeout=15000); u.wait_for_selector('.plan-card')
            pc = u.locator('.plan-card').first; ptxt = pc.inner_text().upper()
            check('BURLETTA AMPLIFICATION' in ptxt and 'INCREASED BURST' in ptxt and 'BURST FIRE' in ptxt and 'ACTIVATION NEEDED' in ptxt and 'PREREQUISITE' in ptxt,
                  'the saved plan keeps the weapon, activation stage and enhancements (chosen + prerequisite)')
            pr = u.eval_on_selector_all('.plan-mats tbody tr', "rs => Object.fromEntries(rs.map(r => [r.querySelector('th strong').textContent.trim(), [r.children[1].textContent.trim(), r.querySelector('[data-phad]')?.value, r.querySelector('[data-phunt]')?.checked]]))")
            check(pr.get('Pressure Regulator') == ['2', '1', True] and pr.get('Pop Trigger', [None, None, None])[2] is False and pr.get('Amplification Module Mk. II', [''])[0] == '1',
                  f'quantities (server-calculated), what I had and my selection are saved {pr}')
            shot(u, 'v64-trail-plan', True)
            tid = u.url.split('id=')[1].split('&')[0].split('#')[0]
            u.click('[data-pact][data-a=COMPLETED]'); u.wait_for_selector('[data-pact][data-a=COMPLETED]', state='detached')
            pr = u.eval_on_selector_all('.plan-mats tbody tr', "rs => Object.fromEntries(rs.map(r => [r.querySelector('th strong').textContent.trim(), r.children[1].textContent.trim()]))")
            check(pr.get('Amplification Module Mk. II') == '0', 'marking activation complete removes the module from what is still needed')
            u.locator('[data-pinst][data-u=burst-fire] + span').click(); u.wait_for_function("() => document.querySelector('[data-pinst][data-u=burst-fire] + span')?.textContent === 'Installed'")
            pr = u.eval_on_selector_all('.plan-mats tbody tr', "rs => Object.fromEntries(rs.map(r => [r.querySelector('th strong').textContent.trim(), [r.children[1].textContent.trim(), r.querySelector('.plan-step b').textContent]]))")
            check(pr.get('Queen Reactor', [''])[0] == '0' and pr.get('Pressure Regulator', [''])[0] == '2', 'marking an enhancement installed stops only its materials counting')
            for want in ('1', '2'):
                u.click('[data-pcol][data-k=fluted-rotor-core][data-d="1"]')
                u.wait_for_function(f"() => [...document.querySelectorAll('.plan-mats tbody tr')].find(r => r.textContent.includes('Fluted Rotor Core'))?.querySelector('.plan-step b').textContent === '{want}'")
            pr = u.eval_on_selector_all('.plan-mats tbody tr', "rs => Object.fromEntries(rs.map(r => [r.querySelector('th strong').textContent.trim(), r.querySelector('.plan-step b').textContent]))")
            check(pr.get('Fluted Rotor Core') == '2', 'collected counts go up with +')
            u.reload(); u.wait_for_selector('.plan-card')
            check('ACTIVATION COMPLETE' in u.inner_text('.plan-card').upper() and u.is_checked('[data-pinst][data-u=burst-fire]'), 'stages and counts persist after reload')
            api(u, 'POST', f'/trails/{tid}/sessions', {'title': 'Frigate run', 'notes': ''}); u.reload(); u.wait_for_selector('.plan-card')
            u.click('.plan-mats a.text-btn[href*="item=fluted-rotor-core"]'); u.wait_for_selector('#discForm')
            check(u.input_value('#discForm [name=title]') == 'Fluted Rotor Core', 'Record discovery from a plan opens the existing discovery form with that material')
            # ---- existing single-material Loot Trail hand-off
            u.goto(B + 'amplification/hunt?weapon=kettle&amplified=yes&upgrade=anti-shield', wait_until='networkidle')
            u.click('.amp-track__single summary'); u.select_option('#ampHuntMat', 'assessor-matrix'); u.click('#ampAddTrail'); u.wait_for_selector('#carryNotice'); u.wait_for_selector('#ownedTrails .trail-card')
            check('Assessor Matrix' in u.inner_text('#carryNotice') and u.locator('.trail-card[href*="item=assessor-matrix"]').count() >= 1, 'single-material Add to Loot Trail still lists trails and carries the material')
            u.click('.trail-card'); u.wait_for_selector('#discForm')
            check(u.input_value('#discForm [name=title]') == 'Assessor Matrix' and 'item=' not in u.url, 'the trail opens the discovery form with the material once')
            t = tid
            sid = srv.sql(f"SELECT id FROM loot_trail_sessions WHERE trail_id = '{t}'")[0]['id']
            r1 = api(u, 'POST', f'/trails/{t}/discoveries', {'title': 'Assessor Matrix', 'sessionId': sid, 'mapLevel': 'all', 'x': .4, 'y': .5, 'itemId': 'amplification-module-mk-v'})
            r2 = api(u, 'POST', f'/trails/{t}/discoveries', {'title': 'Fake', 'sessionId': sid, 'mapLevel': 'all', 'x': .4, 'y': .5, 'itemId': 'not-a-real-item'})
            check(r1['status'] == 201 and r2['status'] == 400, 'Loot Trails accepts new catalog items and rejects unknown item IDs (server-side)')
            r = api(u, 'POST', '/trades', {'wanted_item_id': 'amplification-module-mk-v', 'offered_item_id': 'pneumatic-actuator', 'region': 'NA East', 'platform': 'PC'})
            check(r['status'] == 201, 'a trade request can be posted for new amplification items')
            r = api(u, 'POST', '/trades', {'wanted_item_id': 'tempest-blueprint', 'offered_item_id': 'anvil-blueprint', 'region': 'NA East', 'platform': 'PC'})
            check(r['status'] == 201, 'existing trade items still work')
            # ---- /hunts buttons + dropdown keyboard
            u.goto(B + 'hunts.html', wait_until='networkidle')
            bt = u.locator('.hunts-actions > *'); labels = [bt.nth(i).inner_text().strip() for i in range(bt.count())]
            check(labels[:2] == ['+ Start a Loot Hunt', 'My Loot Trails'] and labels[2].startswith('Amplification Hunt') and 'NEW' in labels[2]
                  and u.get_attribute('.btn-amp', 'href') == 'amplification/hunt.html', '/hunts keeps Start a Loot Hunt + My Loot Trails and adds Amplification Hunt · NEW to the right')
            b1, b2 = u.locator('.btn-trails').bounding_box(), u.locator('.hunts-actions .btn-amp').bounding_box()
            check(b2['x'] > b1['x'] and abs(b2['y'] - b1['y']) < 4, 'Amplification Hunt sits immediately right of My Loot Trails')
            shot(u, 'v64-hunts-desktop', False)
            u.focus('#mainNav > a[data-nav=hunts]'); u.keyboard.press('ArrowDown')
            check(u.evaluate("document.activeElement.classList.contains('nav-drop__item')") and u.is_visible('#navHuntsMenu'), 'keyboard: ArrowDown on Loot Hunts opens the menu and focuses the first entry')
            u.keyboard.press('ArrowDown')
            check(u.evaluate("document.activeElement.getAttribute('href')") == 'amplification/hunt.html', 'keyboard: ArrowDown moves to Amplification Hunt')
            u.keyboard.press('Escape')
            check(not u.is_visible('#navHuntsMenu') and u.evaluate("document.activeElement.id") == 'navHuntsToggle', 'keyboard: Escape closes the menu and returns focus')
            u.click('#navHuntsToggle'); check(u.is_visible('#navHuntsMenu') and u.get_attribute('#navHuntsToggle', 'aria-expanded') == 'true', 'the chevron button toggles the menu (touch / click)')
            u.mouse.click(1200, 700); check(not u.is_visible('#navHuntsMenu'), 'clicking outside closes the menu')
            check(u.locator('.subbar a.nav-amp[href="amplification.html"]').count() == 1, 'AMPLIFICATION guide link is in the secondary bar')
            # ---- mobile
            m = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True).new_page(); m.on('pageerror', lambda e: ERRORS.append(f'mobile: {e}'))
            for path in ('amplification', 'amplification/hunt?weapon=equalizer&amplified=no&upgrade=ramping-damage', 'hunts.html', 'amplification/hunt'):
                m.goto(B + path, wait_until='networkidle'); m.wait_for_timeout(300)
                check(not overflow(m), f'mobile 390px: no horizontal overflow on /{path.split("?")[0]}')
            shot(m, 'v64-mobile-hunt')
            mu = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, storage_state=u.context.storage_state()).new_page()
            mu.on('pageerror', lambda e: ERRORS.append(f'mobile-user: {e}'))
            mu.goto(B + f'trails.html?id={tid}', wait_until='networkidle'); mu.wait_for_selector('.plan-card'); mu.wait_for_timeout(300)
            check(not overflow(mu), 'mobile 390px: no horizontal overflow on a trail with an amplification plan')
            shot(mu, 'v64-mobile-trail-plan')
            mu.goto(B + 'amplification/hunt?weapon=burletta&amplified=no&upgrade=increased-burst,sprint-shooting', wait_until='networkidle'); mu.wait_for_timeout(300)
            check(not overflow(mu), 'mobile 390px: no horizontal overflow on the full Burletta plan review')
            shot(mu, 'v64-mobile-plan-review')
            m.goto(B + 'hunts.html', wait_until='networkidle'); m.click('#menuBtn'); m.wait_for_timeout(200)
            check(m.is_visible('#navHuntsMenu .is-amp') and not m.is_visible('#navHuntsToggle'), 'mobile drawer shows Loot Hunts and Amplification Hunt entries')
            shot(m, 'v64-mobile-menu', False)
            m.click('#navHuntsMenu .is-amp'); m.wait_for_load_state('networkidle')
            check(m.evaluate('document.body.dataset.page') == 'amphunt', 'tapping Amplification Hunt in the drawer opens the Hunt')
            m.click('[data-weapon=rattler]'); m.wait_for_timeout(200); m.click('[data-amp=no]'); m.wait_for_timeout(200); m.click('[data-up=drum-mag]')
            check(m.is_checked('[data-up=more-reload]') and not overflow(m), 'mobile: weapon + upgrade selection works without overflow')
            br.close()
    finally:
        srv.cleanup()
    check(not ERRORS, f'no page errors ({ERRORS[:2]})')
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} amplification checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
