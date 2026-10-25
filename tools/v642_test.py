"""v6.4.2 tests: amplification plan autosave status + "Find Missing Items on Trade Board" (local runtime, THROW-AWAY D1).
  python3 tools/v642_test.py [--shots DIR]
Covers: Saving… -> "Progress Auto Saved" only after the server confirms, failed save with visible error + Retry
(idempotent, no double count), refused change shown and reverted, refresh persistence, Archive removed (records and API kept),
missing-material list (server quantities, unknown/conflicting quantities, non-catalog parts), selection, Trade Board review,
explicit publish + confirmation, duplicate prevention, no automatic collected changes, login redirect, tampered links."""
import sys, os, json, base64
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import DevServer
from amplification_test import new_user, api

SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
RESULTS, ERRORS = [], []


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def shot(page, name, full=False):
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name + '.png'), full_page=full)


def wants(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')


def collected(page, name):
    return page.evaluate("""n => { const r = [...document.querySelectorAll('.plan-mats tbody tr')].find(r => r.querySelector('th strong').textContent.trim() === n);
      return r ? r.querySelector('.plan-step b').textContent : null; }""", name)


def main():
    srv = DevServer(port=8799); srv.migrate(); srv.start(); B = srv.base
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            u = new_user(br, B, 'Saver'); u.on('pageerror', lambda e: ERRORS.append(str(e)))
            T = api(u, 'POST', '/trails', {'title': 'Burletta parts', 'description': '', 'mapId': 'pendola-pass'})['data']['trail']['id']
            P = api(u, 'POST', f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': ['increased-burst', 'sprint-shooting'],
                                                     'had': {'pressure-regulator': 1}})['data']['plan']['id']
            u.goto(B + f'trails.html?id={T}', wait_until='networkidle'); u.wait_for_selector('.plan-card')
            badge = lambda: u.inner_text(f'[data-psave="{P}"]')
            check('save automatically' in badge().lower(), 'autosave status sits next to the Materials heading (idle: "Changes save automatically")')
            hb, pb = u.locator('.plan-mats-head h4').bounding_box(), u.locator(f'[data-psave="{P}"]').bounding_box()
            bar = u.locator('.plan-stage .trail-progress').first.bounding_box()
            check(pb['x'] > hb['x'] + hb['width'] - 5 and abs(pb['y'] - hb['y']) < 20 and pb['y'] < bar['y'], 'indicator is right of the 3 MATERIALS heading, above the progress bar')
            check(u.locator('.plan-card button', has_text='Save').count() == 0, 'no separate Save button')

            # ---- success: Saving… while pending, "Progress Auto Saved" only after the server confirms
            held = []
            u.route('**/api/trails/*/plans/*/me', lambda route: held.append(route))
            u.click('[data-pcol][data-k=fluted-rotor-core][data-d="1"]')
            for _ in range(40):
                if held: break
                u.wait_for_timeout(50)
            mid = badge()
            check('Saving' in mid and 'Auto Saved' not in mid, 'shows "Saving…" while the change is pending (server has not answered)')
            held[0].continue_(); u.unroute('**/api/trails/*/plans/*/me')
            u.wait_for_function("() => document.querySelector('.plan-save--saved') !== null")
            check('Progress Auto Saved' in badge() and u.locator(f'[data-psave="{P}"] .svg-ico').count() == 1 and collected(u, 'Fluted Rotor Core') == '1',
                  'green check + "Progress Auto Saved" appears after the server confirms')
            shot(u, 'v642-autosaved')
            u.fill('[data-phad][data-k=queen-reactor]', '1'); u.locator('[data-phad][data-k=queen-reactor]').dispatch_event('change')
            u.wait_for_function("() => document.querySelector('.plan-save--saved') !== null && document.querySelector('[data-phad][data-k=queen-reactor]').value === '1'")
            check(True, 'editing "Had" autosaves the same way')

            # ---- refresh persistence
            u.reload(); u.wait_for_selector('.plan-card')
            check(collected(u, 'Fluted Rotor Core') == '1' and u.input_value('[data-phad][data-k=queen-reactor]') == '1', 'saved progress survives a page refresh')

            # ---- failure: visible error + Retry; retry is idempotent (absolute count)
            state = {'fail': True}
            def flaky(route):
                if state['fail']: route.abort('failed')
                else: route.continue_()
            u.route('**/api/trails/*/plans/*/me', flaky)
            u.click('[data-pcol][data-k=fluted-rotor-core][data-d="1"]')
            u.wait_for_selector('.plan-save--error')
            check('save failed' in badge().lower() and u.locator('[data-pretry]').count() == 1 and u.get_attribute(f'[data-psave="{P}"]', 'role') == 'alert',
                  'a failed save shows a visible error with Retry (and no "Auto Saved")')
            shot(u, 'v642-save-failed')
            check(srv.sql(f"SELECT collected_qty FROM loot_trail_plan_progress WHERE plan_id = '{P}' AND item_key = 'fluted-rotor-core'")[0]['collected_qty'] == 1, 'nothing was saved while offline')
            state['fail'] = False
            u.click('[data-pretry]'); u.wait_for_selector('.plan-save--saved')
            u.click('[data-pretry]') if u.locator('[data-pretry]').count() else None
            check(collected(u, 'Fluted Rotor Core') == '2', 'Retry saves the change')
            u.unroute('**/api/trails/*/plans/*/me')
            u.reload(); u.wait_for_selector('.plan-card')
            check(collected(u, 'Fluted Rotor Core') == '2', 'after refresh the retried change is there once (no double count)')

            # ---- refused change: shown, then the saved state is restored
            u.click('[data-pact][data-a=COMPLETED]'); u.wait_for_selector('.plan-save--saved')
            u.locator('[data-pinst][data-u=increased-burst] + span').click()
            u.wait_for_selector('.plan-save--error')
            check('install the required enhancement first' in badge().lower() and u.locator('[data-pretry]').count() == 0 and not u.is_checked('[data-pinst][data-u=increased-burst]'),
                  'a change the server refuses is explained (no Retry) and the checkbox returns to the saved state')

            # ---- Archive replaced
            check(u.locator('.plan-card', has_text='Archive plan').count() == 0 and u.locator(f'[data-ptrade="{P}"]').count() == 1,
                  '"Archive plan" is gone; "Find Missing Items on Trade Board" is shown')

            # ---- missing-material list
            u.click(f'[data-ptrade="{P}"]')
            rows = u.eval_on_selector_all(f'#ptrade-{P} li', "ls => ls.map(l => ({k: l.querySelector('input').value, q: l.querySelector('input').dataset.q, on: l.querySelector('input').checked, dis: l.querySelector('input').disabled, t: l.innerText}))")
            by = {r['k']: r for r in rows}
            _, d, _ = (None, api(u, 'GET', f'/trails/{T}/plans', None)['data'], None)
            mats = {m['itemKey']: m for m in d['plans'][0]['me']['materials']}
            exp = {k for k, m in mats.items() if m['outstanding'] > 0 or m['unknownQty']}
            check(set(by) == exp and 'amplification-module-mk-ii' not in by, 'lists only materials still needed (module done after activation)')
            check(by['fluted-rotor-core']['q'] == str(mats['fluted-rotor-core']['outstanding']) and by['pressure-regulator']['q'] == str(mats['pressure-regulator']['outstanding'])
                  and by['queen-reactor']['q'] == '1', f'quantities are the plan\'s calculated "still to hunt" {[(k, r["q"]) for k, r in by.items()]}')
            check('Conflicting quantity' in by['fluted-rotor-core']['t'], 'disputed quantities are flagged')
            lab = next(r for k, r in by.items() if k.startswith('label:'))
            check(lab['dis'] and not lab['on'] and "can't be requested" in lab['t'], 'a part that is not in the catalog is listed but cannot be requested')
            shot(u, 'v642-trade-panel')
            u.click(f'[data-ptnone="{P}"]')
            check('Select at least one' in u.inner_text(f'[data-ptgo="{P}"]'), 'Select none disables the hand-off')
            u.check(f'[data-ptsel="{P}"][value=queen-reactor]'); u.check(f'[data-ptsel="{P}"][value=fluted-rotor-core]')
            check('Create 2 Trade Requests' in u.inner_text(f'[data-ptgo="{P}"]'), 'individual materials can be selected (Create Trade Request)')
            before = srv.sql('SELECT COUNT(*) AS n FROM trade_posts')[0]['n']
            u.click(f'[data-ptgo="{P}"]'); u.wait_for_selector('#wantsModal:not(.hidden) .wants-list li')
            check(srv.sql('SELECT COUNT(*) AS n FROM trade_posts')[0]['n'] == before, 'opening the Trade Board review posts nothing')
            wl = u.eval_on_selector_all('#wantsModal .wants-list li', "ls => ls.map(l => [l.querySelector('[name=pick]').value, l.querySelector('input[type=number]').value])")
            check(sorted(wl) == sorted([['queen-reactor', '1'], ['fluted-rotor-core', str(mats['fluted-rotor-core']['outstanding'])]]) and 'Post 2 Requests' in u.inner_text('#wantsPublish'), f'Trade Board review is prefilled with the selected materials and quantities {wl}')
            shot(u, 'v642-trade-review')
            u.click('#wantsPublish'); u.wait_for_selector('#wantsDone')
            res = u.inner_text('#wantsModal')
            check('2 REQUESTS POSTED' in res.upper() and 'unchanged' in res, 'publishing shows a confirmation (and says plan counts are unchanged)')
            tp = srv.sql(f"SELECT wanted_item_id, wanted_quantity, status, open_to_offers FROM trade_posts WHERE wanted_item_id IN ('queen-reactor','fluted-rotor-core') ORDER BY wanted_item_id")
            check([(r['wanted_item_id'], r['wanted_quantity'], r['status']) for r in tp] == [('fluted-rotor-core', mats['fluted-rotor-core']['outstanding'], 'OPEN'), ('queen-reactor', 1, 'OPEN')],
                  'two normal Trade Board requests were created through the existing API')
            shot(u, 'v642-trade-posted')
            u.click('#wantsDone'); u.wait_for_timeout(500)
            check(u.locator('#tradeRequestGrid .trade-card', has_text='Queen Reactor').count() >= 1, 'the new requests appear on the Trade Board')
            d2 = api(u, 'GET', f'/trails/{T}/plans', None)['data']['plans'][0]['me']['materials']
            check(all(m['collected'] == mats[m['itemKey']]['collected'] for m in d2), 'requesting materials does not mark them collected')

            # ---- duplicate prevention
            u.goto(B + f'trails.html?id={T}', wait_until='networkidle'); u.wait_for_selector('.plan-card')
            u.click(f'[data-ptrade="{P}"]'); u.click(f'[data-ptgo="{P}"]'); u.wait_for_selector('#wantsModal .wants-list li')
            dup = u.eval_on_selector_all('#wantsModal .wants-list li', "ls => Object.fromEntries(ls.map(l => [l.querySelector('[name=pick]').value, l.querySelector('[name=pick]').disabled]))")
            check(dup.get('queen-reactor') is True and dup.get('fluted-rotor-core') is True and dup.get('pressure-regulator') is False, 'materials with an open request of mine are not offered again')
            check('already have an open request' in u.inner_text('#wantsModal'), 'the duplicate is explained with a link to the existing request')
            u.click('#wantsPublish'); u.wait_for_selector('#wantsDone')
            n_pr = srv.sql("SELECT COUNT(*) AS n FROM trade_posts WHERE wanted_item_id IN ('queen-reactor','fluted-rotor-core')")[0]['n']
            check(n_pr == 2, 'publishing again does not duplicate existing requests')

            # ---- unknown quantity must be entered; tampered link is sanitised
            link = wants({'title': 'Test <b>x</b>', 'i': [['assessor-matrix', None, 'CONFLICT'], ['not-a-real-item', 3, 'CONFIRMED'], ['assessor-matrix', 4, 'CONFIRMED'], ['turbine-compressor', 500, 'BOGUS']]})
            u.goto(B + 'trade.html?wants=' + link, wait_until='networkidle'); u.wait_for_selector('#wantsModal .wants-list li')
            wl = u.eval_on_selector_all('#wantsModal .wants-list li', "ls => ls.map(l => [l.querySelector('[name=pick]').value, l.querySelector('input[type=number]').value])")
            check(wl == [['assessor-matrix', ''], ['turbine-compressor', '99']] and '<b>' in u.input_value('#wantsForm [name=notes]') and u.locator('#wantsModal b', has_text='x').count() == 0,
                  'tampered link: unknown items and duplicates dropped, quantities clamped to 1–99, text kept as plain text')
            u.click('#wantsPublish'); u.wait_for_timeout(300)
            check(u.locator('#wantsDone').count() == 0 and srv.sql("SELECT COUNT(*) AS n FROM trade_posts WHERE wanted_item_id = 'assessor-matrix'")[0]['n'] == 0,
                  'an unknown quantity must be entered before anything is posted')
            u.fill('#wantsForm [name="qty-assessor-matrix"]', '2'); u.uncheck('#wantsForm [name=pick][value=turbine-compressor]')
            u.click('#wantsPublish'); u.wait_for_selector('#wantsDone')
            check(srv.sql("SELECT wanted_quantity FROM trade_posts WHERE wanted_item_id = 'assessor-matrix'")[0]['wanted_quantity'] == 2
                  and srv.sql("SELECT COUNT(*) AS n FROM trade_posts WHERE wanted_item_id = 'turbine-compressor'")[0]['n'] == 0, 'only the selected materials are posted, with the entered quantity')

            # ---- logged out -> login, keeping the link
            anon = br.new_context().new_page()
            anon.goto(B + 'trade.html?wants=' + wants({'title': 'x', 'i': [['queen-reactor', 1, 'CONFIRMED']]})); anon.wait_for_url('**/auth*', timeout=10000)
            check('wants%3D' in anon.url or 'wants=' in anon.url, 'logged-out Raiders are sent to log in and come back to the same review')

            # ---- archived records + status API kept
            r = api(u, 'POST', f'/trails/{T}/plans/{P}/status', {'status': 'ARCHIVED'})
            check(r['status'] == 200 and srv.sql(f"SELECT status FROM loot_trail_plans WHERE id = '{P}'")[0]['status'] == 'ARCHIVED'
                  and srv.sql(f"SELECT COUNT(*) AS n FROM loot_trail_plan_progress WHERE plan_id = '{P}'")[0]['n'] > 0, 'archived plan records and the status API are preserved')

            # ---- mobile
            m = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, storage_state=u.context.storage_state()).new_page()
            P2 = api(u, 'POST', f'/trails/{T}/plans', {'weaponId': 'kettle', 'alreadyAmplified': True, 'enhancements': ['anti-shield']})['data']['plan']['id']
            m.goto(B + f'trails.html?id={T}', wait_until='networkidle'); m.wait_for_selector('.plan-card'); m.click(f'[data-ptrade="{P2}"]'); m.wait_for_timeout(200)
            check(not m.evaluate('document.documentElement.scrollWidth > innerWidth + 1 || innerWidth > 391'), 'mobile 390px: plan card with autosave + trade panel has no overflow')
            shot(m, 'v642-mobile', True)
            br.close()
    finally:
        srv.cleanup()
    check(not ERRORS, f'no page errors ({ERRORS[:2]})')
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} v6.4.2 checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
