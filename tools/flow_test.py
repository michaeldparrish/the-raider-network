"""End-to-end demo-mode flow test (needs `python3 -m http.server 8080` running).
Covers: v4 localStorage migration, register, create hunt + trade, join hunt -> message with context,
respond to trade, demo reply, profile lists, mark complete, logout/login, global search, loot filters."""
import sys, json, os
from playwright.sync_api import sync_playwright, expect

BASE = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else 'http://localhost:8080/'
V4_HUNTS = [{"id": "h1", "user_id": "u-local", "display_name": "LocalRaider", "item": "Wolfpack Blueprint", "map": "Dam Battlegrounds", "region": "NA East", "platform": "PlayStation", "squad_size": 3, "current_members": 1, "desired_time": "Tonight", "details": "v4 record", "status": "open", "created_at": "2026-10-05T10:00:00Z"},
            {"id": "h4", "user_id": "u-local", "display_name": "LocalRaider", "item": "ARC Powercell", "map": "The Blue Gate", "region": "NA West", "platform": "PlayStation", "squad_size": 3, "current_members": 1, "desired_time": "Weekend", "details": "v4", "status": "open", "created_at": "2026-10-05T09:00:00Z"},
            {"id": "h9", "user_id": "u-local", "display_name": "LocalRaider", "item": "Some Unknown Thing", "map": "Spaceport", "region": "Europe", "platform": "PC", "squad_size": 2, "current_members": 1, "desired_time": "", "details": "", "status": "open", "created_at": "2026-10-05T09:00:00Z"}]
V4_TRADES = [{"id": "t1", "user_id": "u-local", "display_name": "LocalRaider", "want": "Rotary Encoder", "have": "Open to offers", "region": "NA East", "platform": "Cross-platform", "details": "v4", "created_at": "2026-10-05T10:00:00Z"}]
ok = []
def check(cond, msg):
    ok.append((bool(cond), msg)); print(('PASS ' if cond else 'FAIL ') + msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1300, 'height': 900})
    page = ctx.new_page()
    page.route('**/*', lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    # --- v4 migration
    page.goto(BASE + 'index.html')
    page.evaluate("([h,t])=>{localStorage.clear();localStorage.setItem('trn_users',JSON.stringify([{id:'u-local',user_id:'u-local',email:'l@example.com',password:'password123',display_name:'LocalRaider'}]));localStorage.setItem('trn_hunts',JSON.stringify(h));localStorage.setItem('trn_trades',JSON.stringify(t))}", [V4_HUNTS, V4_TRADES])
    page.goto(BASE + 'hunts.html'); page.wait_for_selector('#huntGrid .hunt-card')
    mig = {h['id']: h for h in page.evaluate("JSON.parse(localStorage.getItem('trn_hunts'))")}
    check(mig['h1']['itemId'] == 'wolfpack-blueprint' and mig['h1']['mapId'] == 'dam-battlegrounds', 'v4 hunt migrated to itemId/mapId')
    check(mig['h4']['itemId'] == 'arc-powercell' and mig['h4']['mapId'] == 'the-blue-gate', 'v4 "ARC Powercell"/"The Blue Gate" resolved')
    check(mig['h9']['itemId'] is None and mig['h9']['itemName'] == 'Some Unknown Thing', 'unknown v4 item kept as free text')
    check(sum(1 for h in mig.values() if h['userId'] == 'perisher') == 10, 'Perisher seed hunts added alongside local records')
    page.goto(BASE + 'trade.html'); page.wait_for_selector('#tradeRequestGrid .trade-card')
    tm = {t['id']: t for t in page.evaluate("JSON.parse(localStorage.getItem('trn_trades'))")}
    check(tm['t1']['lookingFor'][0]['itemId'] == 'rotary-encoder' and tm['t1']['openToOffers'], 'v4 trade migrated (want -> lookingFor, open to offers)')
    # stale v5.1-era browser: RaiderOne/NomadSix/EchoTrader listings with unknown owners + version marker 5.1
    page.evaluate("""()=>{localStorage.clear();localStorage.setItem('trn_seed_trn_trades','5.1');
      const fake=['RaiderOne','NomadSix','EchoTrader','NightWolf','RaiderOne','NomadSix'].map((n,i)=>({id:'x'+i,userId:'f'+i,displayName:n,lookingFor:[{itemId:'anvil-blueprint',quantity:1}],offering:[],openToOffers:true,region:'NA East',platform:'PC',status:'open',createdAt:'2026-10-01T00:00:00Z'}));
      localStorage.setItem('trn_trades',JSON.stringify(fake));localStorage.setItem('trn_messages',JSON.stringify([{id:'m1',sender_id:'f0',recipient_id:'u9',body:'hi',created_at:'2026-10-01T00:00:00Z'}]));}""")
    page.goto(BASE + 'trade.html'); page.wait_for_selector('#tradeRequestGrid .trade-card')
    tn = page.locator('#tradeRequestGrid .trade-card:visible .raider-id strong').all_inner_texts()
    check(set(tn) == {'Perisher'} and len(tn) == 10 and page.inner_text('#statOpenTrades') == '10', f'stale RaiderOne-era data migrated -> 10 Perisher listings ({len(tn)})')
    check(page.evaluate("localStorage.getItem('trn_data_version')") == '"5.2"' and page.evaluate("JSON.parse(localStorage.getItem('trn_messages')).length") == 0, 'data version 5.2 stored; orphan messages removed')
    # legacy fictional demo Raiders are purged
    page.evaluate("()=>{localStorage.clear();localStorage.setItem('trn_hunts',JSON.stringify([{id:'h1',userId:'r1',displayName:'NightWolf',itemId:'anvil-blueprint',mapId:null,status:'open',createdAt:'2026-10-01T00:00:00Z'}]));localStorage.setItem('trn_trades',JSON.stringify([{id:'t2',userId:'r8',displayName:'ArcNomad',lookingFor:[{itemId:'ion-sputter'}],offering:[],status:'open',createdAt:'2026-10-01T00:00:00Z'}]))}")
    page.goto(BASE + 'hunts.html'); page.wait_for_selector('#huntGrid .hunt-card')
    names = set(page.locator('#huntGrid .hunt-card .raider-id strong').all_inner_texts())
    check(names == {'Perisher'}, f'only Perisher hunts on the board ({names})')
    page.goto(BASE + 'trade.html'); page.wait_for_selector('#tradeRequestGrid .trade-card')
    tnames = set(page.locator('#tradeRequestGrid .trade-card .raider-id strong').all_inner_texts())
    check(tnames == {'Perisher'}, f'only Perisher trade listings ({tnames})')

    # --- fresh seed
    page.evaluate('localStorage.clear()')
    page.goto(BASE + 'hunts.html'); page.wait_for_selector('#huntGrid .hunt-card')
    check(page.locator('#huntGrid .hunt-card:visible').count() == 10, 'exactly 10 open hunts visible')
    page.goto(BASE + 'trade.html'); page.wait_for_selector('#tradeRequestGrid .trade-card')
    check(page.locator('#tradeRequestGrid .trade-card:visible').count() == 10, 'exactly 10 open trade listings')
    inv = page.inner_text('#inventoryPanels')
    check('8\nunits owned' in inv or '8 units owned' in inv.replace('\n', ' '), 'inventory panel shows 8 owned units')
    page.goto(BASE + 'index.html'); page.wait_for_selector('#homeStats .stat-tile')
    st = {t: page.inner_text(f'#homeStats [data-stat="{t}"] strong') for t in ['founding-raiders', 'open-loot-hunts', 'trades-completed', 'loot-intel-records', 'maps', 'open-trade-requests']}
    check(st == {'founding-raiders': '10', 'open-loot-hunts': '10', 'trades-completed': '0', 'loot-intel-records': '581', 'maps': '7', 'open-trade-requests': '10'}, f'homepage stats {st}')
    body = page.inner_text('main')
    check(not any(n in body for n in ['NightWolf', 'RaiderMike', 'StormRider', 'LunaRook', 'SperanzaLocal', 'EchoUnit', 'ArcNomad', 'StellaScout', 'GrimTide', '2,847', '1,326']), 'no fake Raiders or old stats on homepage')
    page.goto(BASE + 'hunts.html'); page.wait_for_selector('#huntGrid .hunt-card')

    # --- join while logged out -> auth with next
    page.locator('.join-hunt:not([disabled])').first.click(); page.wait_for_url('**/auth.html**')
    check('next=' in page.url, 'logged-out join redirects to register with next param')

    # --- register
    page.click('#registerTab')
    f = page.locator('#registerForm')
    f.locator('[name=username]').fill('test_raider'); f.locator('[name=email]').fill('tester@example.com')
    f.locator('[name=password]').fill('raider-pass-123'); f.locator('[name=confirm_password]').fill('raider-pass-123')
    f.locator('[name=display_name]').fill('TestRaider'); f.locator('[name=raider_tag]').fill('TEST#1234')
    f.locator('[name=region]').select_option('Europe'); f.locator('.avatar-picker label').nth(2).click()
    f.locator('button[type=submit]').click()
    page.wait_for_url('**/messages.html**', timeout=8000)
    check('huntId=' in page.url, 'after register, returns to messages with hunt context')
    page.wait_for_selector('#chatRegarding:not(.hidden)')
    reg = page.inner_text('#chatRegarding')
    check('REGARDING' in reg.upper() and 'Loot Hunt' in reg, f'chat shows Regarding banner ({reg.strip()[:60]!r})')
    check('join' in page.input_value('#messageForm textarea').lower(), 'join intent pre-fills message')
    page.click('#messageForm button[type=submit]')
    page.wait_for_selector('.bubble.mine')
    page.wait_for_timeout(1500)
    check(page.locator('#messageThread .bubble:not(.mine)').count() == 0, 'no fake auto-reply from a real Raider')
    msgs = page.evaluate("JSON.parse(localStorage.getItem('trn_messages'))")
    check(msgs[0].get('hunt_id') and msgs[0].get('item_id'), 'stored message carries hunt_id + item_id')
    check('@' not in page.inner_text('main'), 'no email rendered on messages page')

    # --- create hunt from item page
    page.goto(BASE + 'item.html?id=magnetron'); page.wait_for_selector('.where-panel')
    page.click('text=Start a Loot Hunt'); page.wait_for_selector('#huntModal:not(.hidden)')
    check(page.input_value('#huntForm [name=itemName]') == 'Magnetron', 'hunt form pre-filled from item page')
    check(page.input_value('#huntForm [name=mapId]') == 'stella-montis', 'hunt map auto-set from item intel')
    page.fill('#huntForm [name=description]', 'Flow test hunt'); page.click('#huntForm button[type=submit]')
    page.wait_for_selector('#huntModal.hidden', state='attached', timeout=5000)
    page.wait_for_timeout(400)
    h = page.evaluate("JSON.parse(localStorage.getItem('trn_hunts'))[0]")
    check(h['itemId'] == 'magnetron' and h['mapId'] == 'stella-montis' and h['displayName'] == 'TestRaider', 'new hunt stored with shared IDs')

    # --- create trade
    page.goto(BASE + 'trade.html?new=queen-reactor'); page.wait_for_selector('#tradeModal:not(.hidden)')
    page.fill('#tradeForm [name=have]', 'Magnetic Accelerator'); page.fill('#tradeForm [name=haveQty]', '2')
    page.click('#tradeForm button[type=submit]'); page.wait_for_timeout(700)
    t = page.evaluate("JSON.parse(localStorage.getItem('trn_trades'))[0]")
    check(t['lookingFor'][0]['itemId'] == 'queen-reactor' and t['offering'][0]['itemId'] == 'magnetic-accelerator' and t['offering'][0]['quantity'] == 2, 'new trade stored with item IDs + qty')

    # --- respond to someone else's trade
    page.goto(BASE + 'trade.html'); page.wait_for_selector('.trade-card')
    page.locator('.trade-card[id=pt1] .trade-respond').click(); page.wait_for_url('**/messages.html**')
    page.wait_for_selector('#chatRegarding:not(.hidden)')
    check('Wolfpack Blueprint Trade' in page.inner_text('#chatRegarding'), 'trade response shows "Regarding: Wolfpack Blueprint Trade"')

    # --- item page shows hunts/trade interest
    page.goto(BASE + 'item.html?id=queen-reactor'); page.wait_for_selector('.where-panel')
    check('TestRaider' in page.inner_text('main'), 'item page lists the new trade request')

    # --- profile
    page.goto(BASE + 'profile.html'); page.wait_for_selector('#myHunts .mini-row')
    check(page.locator('#myHunts .mini-row').count() == 1 and page.locator('#myTrades .mini-row').count() == 1, 'profile shows my active hunt and open trade')
    check('TEST#1234' in page.inner_text('#profileMeta'), 'owner sees private Raider tag')
    page.click('[data-complete]'); page.wait_for_selector('#myCompleted .mini-row')
    check(page.locator('#myCompleted .mini-row').count() == 1, 'mark hunt complete moves it to Completed')
    page.fill('#profileForm [name=display_name]', 'TestRaider2'); page.click('#profileForm button'); page.wait_for_timeout(300)
    check(page.inner_text('#profileName').lower() == 'testraider2', 'profile edit saves')

    # --- logout / login
    page.click('#logoutBtn'); page.wait_for_url('**/index.html')
    page.goto(BASE + 'auth.html'); page.fill('#loginForm [name=login]', 'tester@example.com'); page.fill('#loginForm [name=password]', 'raider-pass-123')
    page.click('#loginForm button'); page.wait_for_url('**/profile.html')
    check(page.locator('#navUser:not(.hidden)').count() == 1, 'login works and nav shows user')

    # --- Perisher account claim + inventory safeguards
    page.click('#logoutBtn') if page.locator('#logoutBtn').count() else None
    page.goto(BASE + 'auth.html#register'); page.click('#registerTab')
    f = page.locator('#registerForm')
    f.locator('[name=username]').fill('perisher'); f.locator('[name=email]').fill('perisher@example.com')
    f.locator('[name=password]').fill('raider-pass-123'); f.locator('[name=confirm_password]').fill('raider-pass-123')
    f.locator('[name=display_name]').fill('Perisher'); f.locator('[name=raider_tag]').fill('PER#1')
    f.locator('button[type=submit]').click(); page.wait_for_url('**/profile.html', timeout=8000)
    page.wait_for_selector('#myInventory .inv-row')
    check(page.locator('#myHunts .mini-row').count() == 10 and page.locator('#myInventory .inv-row').count() == 5, 'Perisher account owns 10 hunts + 5-line inventory')
    page.goto(BASE + 'trade.html'); page.wait_for_selector('#openTradeModal')
    page.click('#openTradeModal'); page.wait_for_selector('#invOfferWrap:not(.hidden)')
    dis = page.evaluate("[...document.querySelectorAll('#tradeForm [name=invKey] option')].filter(o=>o.disabled).map(o=>o.value)")
    check(set(dis) == {'kinetic-converter', 'queen-reactor', 'snap-hook'}, f'fully reserved items cannot be allocated again ({dis})')
    r = page.evaluate("async()=>{try{await TRN.store.createTrade({lookingFor:[{itemId:'anvil-blueprint',quantity:1}],offering:[{inventoryKey:'queen-reactor',itemId:'queen-reactor',name:'Queen Reactor',quantity:1,fromInventory:true}],offerFromPool:true,openToOffers:true,region:'NA East',platform:'Cross-platform'},await TRN.auth.currentUser());return 'created'}catch(e){return e.message}}")
    check('Only 0 Queen Reactor available' in r, f'over-allocation blocked: {r}')
    page.click('#closeTradeModal')
    page.locator('.trade-card[id=pt7] [data-traded]').click()
    page.select_option('[data-form=pt7] select[name=key]', 'patina-blueprint')
    page.locator('[data-form=pt7] button').click(); page.wait_for_timeout(500)
    inv2 = page.evaluate("TRN.store.inventory('perisher', JSON.parse(localStorage.getItem('trn_trades'))).items.find(x=>x.key==='patina-blueprint')")
    check(inv2['owned'] == 0 and inv2['unavailable'], 'mark traded decrements Patina Blueprint to 0 and marks it unavailable')
    r2 = page.evaluate("async()=>{try{await TRN.store.completeTrade('pt8',[{key:'patina-blueprint',quantity:1}]);return 'ok'}catch(e){return e.message}}")
    check('Cannot give' in r2, f'cannot decrement below zero: {r2}')
    page.goto(BASE + 'index.html'); page.wait_for_selector('#homeStats .stat-tile')
    check(page.inner_text('#homeStats [data-stat="trades-completed"] strong') == '1', 'trades completed counter updates after a recorded trade')

    # --- map intelligence (v5.2 map-first)
    page.goto(BASE + 'map.html?id=dam-battlegrounds'); page.wait_for_selector('#mvImg[src*="maps/base/"]')
    page.wait_for_function("document.querySelector('#mvImg').complete && document.querySelector('#mvImg').naturalWidth > 0")
    first = page.evaluate("[...document.querySelectorAll('#mapRoot section')].map(s=>s.id||s.className).slice(0,2)")
    check('map-view' in first, f'base map section comes right after hero ({first})')
    check(page.locator('#mvOverlay:checked').count() == 1 and page.locator('a[href="loot.html?map=dam-battlegrounds"]').count() >= 2, 'overlay on by default + VIEW ALL LOOT ON THIS MAP links')
    page.click('#miNone'); page.wait_for_timeout(150); check(page.inner_text('#miCount').startswith('0 of'), 'Hide all clears markers')
    page.click('#miAll'); page.wait_for_timeout(150); check(page.inner_text('#miCount').startswith('7,662 of'), 'Show all shows every marker')
    page.goto(BASE + 'map.html?id=riven-tides'); page.wait_for_selector('#mvImg[src*="maps/base/"]')
    check(page.locator('#mvOverlay:disabled').count() == 1, 'uncalibrated map (Riven Tides) shows base map with overlay disabled')
    page.goto(BASE + 'loot.html?map=stella-montis'); page.wait_for_selector('#lootResults .item-card')
    check(page.input_value('#mapFilter') == 'stella-montis' and 'stella montis' in page.inner_text('#mapBanner').lower(), 'Loot Intel applies ?map= filter')
    page.goto(BASE + 'map.html?id=stella-montis'); page.wait_for_selector('.mi-row', state='attached'); page.click('#mvListWrap summary')
    n0 = page.locator('.mi-row').count()
    page.fill('#miSearch', 'with a view'); page.wait_for_timeout(300)
    rows = page.locator('.mi-row').all_inner_texts()
    check(n0 > 0 and rows and all('with a view' in r.lower() for r in rows), f'marker search/filter works ({len(rows)} rows)')
    check('MetaForge' in page.inner_text('#map-view'), 'MetaForge attribution on map page')
    check(page.locator('.mv-level').count() == 2, 'Stella Montis has two level images')
    # v6.1 Pendola Pass: labelled in-game map + terrain level, gondola warning, temporary Redirection condition, no invented markers
    page.goto(BASE + 'map.html?id=pendola-pass'); page.wait_for_selector('#mvImg[src*="pendola-pass"]', state='attached')
    page.wait_for_function("document.querySelector('#mvImg').naturalWidth > 0")
    check(page.locator('.mv-level').count() == 2, 'Pendola Pass has Detailed map + Terrain overview levels')
    src0 = page.get_attribute('#mvImg', 'src'); page.click('.mv-level[data-level="1"]')
    page.wait_for_function("document.querySelector('#mvImg').src.includes('terrain') && document.querySelector('#mvImg').naturalWidth > 0")
    check('terrain' not in src0 and 'terrain' in page.get_attribute('#mvImg', 'src'), 'Pendola level switch loads the terrain image')
    notes = page.inner_text('main')
    check('request points, not landing spots' in notes and 'Landing locations are not marked' in notes, 'gondola transceiver warning shown')
    check('TEMPORARY CONDITION' in notes.upper() and 'Redirection' in notes and 'NOT A PERMANENT LANDMARK' in notes.upper(), 'Redirection shown as a temporary condition')
    check(page.locator('.mi-row').count() == 0 and page.locator('#mvOverlay').is_disabled(), 'Pendola has no invented markers; overlay disabled')
    check('RaidTheory' not in page.inner_text('#map-view') and 'owner screenshots' in page.inner_text('#map-view'), 'Pendola map credit names the correct source')
    check(page.locator('.poi-card').count() == 9, f'Pendola lists the 9 named areas ({page.locator(".poi-card").count()})')

    # v6.1 premium renders: approved pilot icons load; everything else unchanged
    for iid in ('bastion-cell', 'geiger-counter'):
        page.goto(BASE + f'item.html?id={iid}'); page.wait_for_selector('main img[src*="items/game/%s.webp"]' % iid, state='attached')
        loaded = page.evaluate("id => [...document.querySelectorAll('main img')].filter(i => i.src.includes('items/game/' + id)).every(i => i.complete && i.naturalWidth > 0)", iid)
        check(loaded, f'{iid} shows the approved Raider Network render')
    page.goto(BASE + 'item.html?id=bombardier-cell'); page.wait_for_selector('main img', state='attached')
    check(page.locator('main img[src*="items/game/"]').count() == 0, 'Bombardier Cell keeps its current icon (pilot not approved)')

    # v6.1 weapon art: traced per-weapon outlines on weapon cards + weapon blueprints; item pages with a single-string craft bench render
    for iid in ('tempest-i', 'aphelion', 'venator-blueprint'):
        page.goto(BASE + f'item.html?id={iid}'); page.wait_for_selector('footer', state='attached'); page.wait_for_timeout(300)
        loaded = page.evaluate("() => [...document.querySelectorAll('main img')].filter(i => i.src.includes('/items/db/')).every(i => i.complete && i.naturalWidth > 0)")
        check('went wrong' not in page.inner_text('body') and loaded, f'{iid} item page renders with its v6.1 art')
    svg = page.evaluate("async () => (await (await fetch('assets/images/items/db/tempest-i.svg')).text())")
    check('id="gunV"' in svg and 'fill-rule="evenodd"' in svg, 'Tempest card uses the traced Tempest outline')
    svg = page.evaluate("async () => (await (await fetch('assets/images/items/db/rascal-i.svg')).text())")
    check('id="gunV"' not in svg, 'Rascal (no reference) keeps its class silhouette')
    svg = page.evaluate("async () => (await (await fetch('assets/images/items/db/venator-blueprint.svg')).text())")
    check('BLUEPRINT' in svg and 'SCHEMATIC' in svg and 'fill-rule="evenodd"' in svg, 'Venator blueprint keeps the card and gains the traced outline')

    # --- search + filters
    page.goto(BASE + 'index.html'); page.wait_for_selector('#popularLoot .item-card')
    page.fill('#homeSearch', 'stella'); page.wait_for_selector('#homeSearchForm .ac-row')
    check('Stella Montis' in page.inner_text('#homeSearchForm .ac-box'), 'global autocomplete finds maps')
    page.fill('#homeSearch', 'with a view'); page.wait_for_timeout(200)
    check('Quest' in page.inner_text('#homeSearchForm .ac-box'), 'global autocomplete finds quests')
    page.fill('#homeSearch', 'trophy'); page.wait_for_timeout(200)
    check('Project' in page.inner_text('#homeSearchForm .ac-box'), 'global autocomplete finds projects')
    page.goto(BASE + 'loot.html'); page.wait_for_selector('#lootResults .item-card')
    page.select_option('#mapFilter', 'stella-montis'); page.locator('.flag-toggle', has_text='Quest item').click(); page.wait_for_timeout(200)
    names = page.locator('#lootResults .item-card h3').all_inner_texts()
    check('Rotary Encoder' in names and 'Ion Sputter' in names, f'loot filters map+quest -> {names[:5]}')
    page.goto(BASE + 'projects.html'); page.wait_for_selector('.project-full')
    page.click('.tab-btn[data-status=HISTORICAL]'); page.wait_for_timeout(100)
    vis = page.locator('.project-full:visible').count()
    check(vis >= 10, f'projects historical filter ({vis})')
    check(not errors, 'no page errors: ' + '; '.join(errors[:3]))
    b.close()
fails = [m for c, m in ok if not c]
print(f'\n{len(ok) - len(fails)}/{len(ok)} checks passed')
sys.exit(1 if fails else 0)
