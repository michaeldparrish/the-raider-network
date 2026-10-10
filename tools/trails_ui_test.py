"""v6.3 browser test for the Loot Trails UI on Cloudflare's local runtime with a THROW-AWAY local D1 database + local R2.
  python3 tools/trails_ui_test.py [--shots DIR]
Covers: Start a Loot Hunt popup chooser (Quick Hunt still works; Loot Trail creates a private trail), dashboard (owned /
joined / invitations), invite + accept, contributor permissions in the UI, sessions (start / end), manual pin placement
on a multi-level map, two separate screenshot pickers with previews and client-side limits, upload with progress,
private thumbnails, per-Raider progress (restored after reload, owner-only squad counts), owner review, remove-to-replace
and the approved lock, publishing, public view (no description / screenshots / squad), outsider 404, mobile layout."""
import sys, os, io, uuid, tempfile
from playwright.sync_api import sync_playwright
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import DevServer

SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
RESULTS, ERRORS = [], []
PW = 'Trails-Ui-Pass-77'
TMP = tempfile.mkdtemp(prefix='trn-trails-ui-')


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def shot(page, name, full=True):
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name + '.png'), full_page=full)


def img_file(name, fmt, color, size=(640, 400)):
    path = os.path.join(TMP, name); Image.new('RGB', size, color).save(path, fmt); return path


def big_png(name, nbytes):
    """A real PNG header followed by padding: large enough to trip the 20 MB client-side check."""
    buf = io.BytesIO(); Image.new('RGB', (8, 8), (1, 2, 3)).save(buf, 'PNG')
    path = os.path.join(TMP, name)
    with open(path, 'wb') as f: f.write(buf.getvalue()); f.write(b'\0' * (nbytes - len(buf.getvalue())))
    return path


def api(page, method, path, body=None):
    return page.evaluate("""async ([m, p, b]) => { const r = await fetch('/api' + p, { method: m, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-TRN-CSRF': '1', Accept: 'application/json' }, body: b ? JSON.stringify(b) : undefined });
        return { status: r.status, data: await r.json().catch(() => null) }; }""", [method, path, body])


def upload(page, trail, disc, kind, path, ctype):
    data = list(open(path, 'rb').read())
    return page.evaluate("""async ([u, d, t]) => { const r = await fetch(u, { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': t, 'X-TRN-CSRF': '1' }, body: new Uint8Array(d) }); return r.status; }""",
                         [f'/api/trails/{trail}/discoveries/{disc}/images/{kind}', data, ctype])


def new_user(browser, base, name, mobile=False):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844} if mobile else {'width': 1360, 'height': 900}, is_mobile=mobile, has_touch=mobile)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: ERRORS.append(f'{name}: {e}'))
    pg.goto(base + 'index.html'); pg.wait_for_load_state('networkidle')
    u = (name.lower() + uuid.uuid4().hex[:5])[:20]
    body = {'username': u, 'display_name': name, 'email': f'{u}@example.com', 'password': PW, 'confirm_password': PW, 'region': 'NA East', 'platform': 'PlayStation'}
    r = api(pg, 'POST', '/auth/register', body); assert r['status'] == 201, r
    pg.username, pg.uid, pg.name = u, r['data']['user']['id'], name
    return pg


def wait_map(pg):
    pg.wait_for_function("() => { const i = document.querySelector('.tm-img'); return i && i.complete && i.naturalWidth > 0; }", timeout=20000)


def main():
    srv = DevServer(port=8795); srv.migrate(); srv.start(); B = srv.base
    map_png = img_file('map.png', 'PNG', (20, 120, 200)); loot_jpg = img_file('loot.jpg', 'JPEG', (220, 120, 20))
    loot2_png = img_file('loot2.png', 'PNG', (40, 200, 90)); huge = big_png('huge.png', 20 * 1024 * 1024 + 1)
    gif = os.path.join(TMP, 'anim.gif'); Image.new('RGB', (8, 8)).save(gif, 'GIF')
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ow = new_user(br, B, 'Olivia')     # trail owner
            co = new_user(br, B, 'Cass')       # contributor
            out = new_user(br, B, 'Otto')      # logged-in outsider

            # ---- popup chooser: Quick Hunt default and unchanged
            ow.goto(B + 'hunts.html'); ow.wait_for_selector('#huntGrid', state='attached')
            check(ow.locator('.page-banner a', has_text='My Loot Trails').count() == 1, 'Loot Hunts banner links to My Loot Trails')
            ow.click('#openHuntModal'); ow.wait_for_selector('#huntModal:not(.hidden)')
            check(ow.locator('[data-hunt-mode]').count() == 2 and ow.is_visible('#huntForm') and not ow.is_visible('#huntTrailPane'),
                  'Start a Loot Hunt popup offers Quick Hunt and Loot Trail; Quick Hunt form shown by default')
            shot(ow, 'v63-popup-quick', full=False)
            ow.fill('#huntForm [name=itemName]', 'Rotary Encoder'); ow.fill('#huntForm [name=description]', 'v6.3 regression quick hunt')
            ow.click('#huntForm button[type=submit]'); ow.wait_for_selector('#huntModal.hidden', state='attached', timeout=8000)
            ow.wait_for_timeout(500)
            check(ow.locator('#huntGrid', has_text='Rotary Encoder').count() == 1, 'Quick Hunt still publishes from the popup exactly as before')
            check(srv.sql('SELECT COUNT(*) AS n FROM loot_trails')[0]['n'] == 0, 'publishing a Quick Hunt creates no Loot Trail')

            # ---- popup: Loot Trail
            ow.click('#openHuntModal'); ow.click('[data-hunt-mode=trail]')
            check(ow.is_visible('#huntTrailForm') and not ow.is_visible('#huntForm'), 'choosing Loot Trail swaps in the trail form and hides the Quick Hunt form')
            shot(ow, 'v63-popup-trail', full=False)
            ow.fill('#huntTrailForm [name=title]', 'Stella blueprint sweep')
            ow.select_option('#huntTrailForm [name=mapId]', 'stella-montis')
            ow.fill('#huntTrailForm [name=description]', 'SECRET squad plan: meet at the Metro at 9.')
            ow.click('#huntTrailForm button[type=submit]'); ow.wait_for_url('**/trails*id=*created=1*', timeout=15000)
            ow.wait_for_selector('.trail-head h1')
            tid = ow.url.split('id=')[1].split('&')[0]
            head = ow.inner_text('.trail-head').upper()
            check('STELLA BLUEPRINT SWEEP' in head and 'PRIVATE' in head and 'YOU OWN THIS TRAIL' in head, 'trail created from the popup opens privately with the owner role')
            check(ow.locator('.notice-bar--ok').count() == 1 and ow.locator('#visBtn').count() == 1 and ow.locator('#inviteForm').count() == 1, 'owner sees next steps, invite form and visibility control')
            row = srv.sql(f"SELECT visibility, map_id FROM loot_trails WHERE id = '{tid}'")[0]
            check(row['visibility'] == 'PRIVATE' and row['map_id'] == 'stella-montis', 'trail is stored in D1 as PRIVATE on the chosen map')

            # ---- outsider cannot open a private trail
            out.goto(B + f'trails.html?id={tid}'); out.wait_for_selector('.notice-bar')
            check('not found' in out.inner_text('#trailsRoot').lower() and 'SECRET' not in out.content(), 'logged-in outsider gets "not found" for a private trail')

            # ---- invite + accept
            ow.fill('#inviteForm [name=username]', 'nobody_' + uuid.uuid4().hex[:6]); ow.click('#inviteForm button'); ow.wait_for_timeout(600)
            check('No Raider with that username' in ow.inner_text('#inviteForm'), 'inviting an unknown username explains the problem')
            ow.fill('#inviteForm [name=username]', '@' + co.username); ow.click('#inviteForm button')
            ow.wait_for_selector('#squadList >> text=Invited · waiting')
            check(True, 'owner sees the invited Raider as "Invited · waiting"')
            co.goto(B + 'trails.html'); co.wait_for_selector('.invite-row')
            check('Stella blueprint sweep' in co.inner_text('.invite-row'), 'invited Raider sees the invitation on the Loot Trails dashboard')
            shot(co, 'v63-dashboard-invitation')
            co.click('.invite-row [data-d=ACCEPT]'); co.wait_for_url(f'**/trails*id={tid}*', timeout=15000); co.wait_for_selector('.trail-head h1')
            ctext = co.inner_text('#trailsRoot')
            check('CONTRIBUTOR' in co.inner_text('.trail-head').upper() and co.locator('#visBtn').count() == 0 and co.locator('#inviteForm').count() == 0,
                  'accepted contributor opens the trail without invite or visibility controls')
            check('SECRET squad plan' in ctext, 'accepted contributor can read the private description')

            # ---- sessions
            co.fill('#sessionForm [name=title]', 'Friday night run'); co.fill('#sessionForm [name=notes]', 'Metro side first')
            co.click('#sessionForm button'); co.wait_for_selector('.session-row >> text=Friday night run')
            check('ACTIVE' in co.inner_text('.session-row').upper(), 'contributor starts a session; it shows as ACTIVE with its notes')

            # ---- record a discovery: pin + two screenshots
            wait_map(co)
            co.click('#addDiscoveryBtn'); co.wait_for_selector('#discForm')
            check(co.locator('#discForm [data-file=MAP_POSITION]').count() == 1 and co.locator('#discForm [data-file=LOOT]').count() == 1,
                  'discovery form has two separate screenshot controls')
            co.select_option('#discForm [name=mapLevel]', '1'); co.wait_for_timeout(300)
            wait_map(co)
            co.fill('#discForm [name=title]', 'Rotary Encoder'); co.wait_for_timeout(200)
            co.click('#discForm button[type=submit]'); co.wait_for_timeout(200)
            check('Place the pin' in co.inner_text('#discMsg'), 'saving without a pin asks for the pin first')
            check(co.locator('#discItemPreview a').count() == 1, 'typing a known item name links it to Loot Intel')
            box = co.locator('.tm-world').bounding_box()
            co.locator('.tm-world').click(position={'x': box['width'] * 0.25, 'y': box['height'] * 0.5})
            check('Pin placed' in co.inner_text('#pinStatus') and co.locator('.tm-pin--draft').count() == 1, 'clicking the map places a draft pin and confirms it')
            # client-side checks
            co.set_input_files('#discForm [data-file=MAP_POSITION]', huge); co.wait_for_timeout(200)
            check('20 MB' in co.inner_text('[data-shot=MAP_POSITION] .shot-pick__status'), 'a screenshot over 20 MB is rejected before upload')
            co.set_input_files('#discForm [data-file=LOOT]', gif); co.wait_for_timeout(200)
            check('PNG, JPEG or WebP' in co.inner_text('[data-shot=LOOT] .shot-pick__status'), 'a GIF is rejected before upload')
            co.set_input_files('#discForm [data-file=MAP_POSITION]', map_png); co.set_input_files('#discForm [data-file=LOOT]', loot_jpg); co.wait_for_timeout(400)
            check(co.locator('[data-shot=MAP_POSITION] .shot-pick__preview img').count() == 1 and co.locator('[data-shot=LOOT] .shot-pick__preview img').count() == 1,
                  'both screenshots show a local preview before saving')
            check(srv.sql('SELECT COUNT(*) AS n FROM loot_trail_images')[0]['n'] == 0, 'choosing files uploads nothing until Save is pressed')
            shot(co, 'v63-discovery-form')
            co.click('#discForm button[type=submit]'); co.wait_for_selector('.disc-card', timeout=20000)
            d = srv.sql("SELECT id, map_level, x_normalized AS x, y_normalized AS y, item_id, review_status FROM loot_trail_discoveries")
            check(len(d) == 1 and d[0]['map_level'] == '1' and 0.2 < d[0]['x'] < 0.3 and 0.45 < d[0]['y'] < 0.55 and d[0]['item_id'] == 'rotary-encoder' and d[0]['review_status'] == 'PENDING',
                  'discovery saved with normalized pin on the chosen level, linked item and PENDING review')
            did = d[0]['id']
            imgs = srv.sql(f"SELECT image_type, content_type FROM loot_trail_images WHERE discovery_id = '{did}' ORDER BY image_type")
            check([(i['image_type'], i['content_type']) for i in imgs] == [('LOOT', 'image/jpeg'), ('MAP_POSITION', 'image/png')], 'both screenshots stored privately (PNG + JPEG)')
            co.wait_for_function("() => [...document.querySelectorAll('.shot-thumb img')].length === 2 && [...document.querySelectorAll('.shot-thumb img')].every(i => i.complete && i.naturalWidth > 0)", timeout=10000)
            check(True, 'both screenshot thumbnails load for the squad')
            check(f'trails/{tid}/{did}/' not in co.content() and 'r2_key' not in co.content(), 'page never contains the private R2 object key')
            check(co.locator('.tm-pin:not(.tm-pin--draft)').count() == 0, 'pin for level 1 is hidden while viewing level 2 (default)')
            co.click('[data-show]'); co.wait_for_timeout(400)
            check(co.locator('.tm-pin.is-active').count() == 1 and co.locator('.mv-level.on').inner_text().upper().startswith('SANDBOX'), '"Show on map" switches to the right level and highlights the pin')
            check(co.locator('[data-review]').count() == 0 and co.locator('[data-pub]').count() == 0, 'contributor sees no review or publish controls')
            shot(co, 'v63-trail-contributor')

            # ---- progress (per Raider)
            co.click('.done-toggle span'); co.wait_for_timeout(800)
            check('1 of 1' in co.inner_text('.trail-progress-box'), 'contributor ticks completion; their progress shows 1 of 1')
            co.reload(); co.wait_for_selector('.disc-card')
            check(co.is_checked('[data-done]'), 'completion is restored after reload (myCompletedDiscoveryIds)')
            ow.goto(B + f'trails.html?id={tid}'); ow.wait_for_selector('.disc-card')
            check(not ow.is_checked('[data-done]') and '0 of 1' in ow.inner_text('.trail-progress-box'), "owner's own progress is separate (0 of 1)")
            check('1 of 1 completed' in ow.inner_text('#squadList'), 'owner sees the squad member completion count')
            check('completed' not in co.inner_text('#squadList'), "contributor does not see other Raiders' progress")

            # ---- remove to replace (before approval), then approve locks it
            check(co.locator('[data-rm]').count() == 2, 'creator can remove a screenshot to replace it while pending')
            co.click('[data-rm][data-t=LOOT]'); co.click('[data-rm][data-t=LOOT]'); co.wait_for_selector('[data-add][data-t=LOOT]', state='attached', timeout=8000)
            co.set_input_files('[data-add][data-t=LOOT]', loot2_png); co.wait_for_function("() => document.querySelectorAll('.shot-thumb img').length === 2", timeout=10000)
            n = srv.sql(f"SELECT content_type FROM loot_trail_images WHERE discovery_id = '{did}' AND image_type = 'LOOT'")
            check(n and n[0]['content_type'] == 'image/png', 'replacement screenshot uploaded (remove, then add)')

            ow.reload(); ow.wait_for_selector('[data-review]')
            ow.click('[data-review][data-s=APPROVED]'); ow.wait_for_selector('.disc-card >> text=APPROVED')
            check(ow.locator('[data-pub]').count() == 1, 'owner approves; Publish becomes available')
            co.reload(); co.wait_for_selector('.disc-card')
            check(co.locator('[data-rm]').count() == 0 and 'Locked (approved)' in co.inner_text('.disc-card'), 'approved discovery screenshots are locked for the creator')

            # ---- end session
            co.click('[data-end]'); co.click('[data-end]'); co.wait_for_selector('.session-row >> text=ENDED')
            co.click('#addDiscoveryBtn'); co.wait_for_timeout(200)
            check('Start a session first' in co.inner_text('#discoveryFormHost'), 'after the session ends, new discoveries ask for a new session')

            # ---- publish + public view
            ow.click('[data-pub]'); ow.click('[data-pub]'); ow.wait_for_selector('.disc-card >> text=PUBLISHED')
            ow.click('#visBtn'); check('does not publish discoveries' in ow.inner_text('#visNote'), 'making the trail public asks for confirmation and explains what becomes visible')
            ow.click('#visBtn'); ow.wait_for_selector('.trail-head >> text=PUBLIC')
            shot(ow, 'v63-trail-owner')
            api(ow, 'POST', f'/trails/{tid}/sessions', {'title': 'Second run', 'notes': ''})
            sid2 = srv.sql(f"SELECT id FROM loot_trail_sessions WHERE trail_id = '{tid}' AND ended_at IS NULL")[0]['id']
            r = api(co, 'POST', f'/trails/{tid}/discoveries', {'title': 'Unreviewed cache', 'notes': 'PRIVATE NOTE', 'sessionId': sid2, 'mapLevel': '2', 'x': 0.5, 'y': 0.5})
            check(r['status'] == 201, 'second (pending) discovery created')
            anon = br.new_context().new_page(); anon.on('pageerror', lambda e: ERRORS.append(f'anon: {e}'))
            anon.goto(B + f'trails.html?id={tid}'); anon.wait_for_selector('.trail-head h1')
            at = anon.inner_text('#trailsRoot'); html = anon.content()
            check('PUBLIC LOOT TRAIL' in at.upper() and 'Rotary Encoder' in at, 'anonymous visitor sees the public trail with the approved + published discovery')
            check('Unreviewed cache' not in at and 'PRIVATE NOTE' not in html, 'pending discovery is not shown publicly')
            check('SECRET squad plan' not in html and co.username not in html and ow.username not in html and 'images/MAP_POSITION' not in html and 'images/LOOT' not in html,
                  'public view shows no description, usernames or screenshot URLs')
            wait_map(anon); anon.click('.mv-level >> nth=1'); anon.wait_for_timeout(200)
            check(anon.locator('.tm-pin').count() == 1, 'public map shows the published pin')
            shot(anon, 'v63-trail-public')

            # ---- dashboards
            ow.goto(B + 'trails.html'); ow.wait_for_selector('#ownedTrails .trail-card')
            oc = ow.inner_text('#ownedTrails')
            check('STELLA BLUEPRINT SWEEP' in oc.upper() and '2 discoveries' in oc.replace('\n', ' ') and '2 in squad' in oc.replace('\n', ' '), 'owner dashboard lists the trail with stats')
            shot(ow, 'v63-dashboard-owner')
            co.goto(B + 'trails.html'); co.wait_for_selector('#joinedTrails .trail-card')
            check('by Olivia' in co.inner_text('#joinedTrails') and co.locator('#ownedTrails .trail-card').count() == 0, 'contributor dashboard lists it under Joined')
            check(co.locator('#mainNav a.active[data-nav=hunts]').count() == 1, 'Loot Hunts nav item is highlighted on Loot Trails')

            # ---- removal
            ow.goto(B + f'trails.html?id={tid}'); ow.wait_for_selector('[data-remove]')
            ow.click('[data-remove]'); ow.click('[data-remove]'); ow.wait_for_selector('#squadList >> text=Removed')
            co.goto(B + f'trails.html?id={tid}'); co.wait_for_selector('.trail-head h1')
            check('PUBLIC LOOT TRAIL' in co.inner_text('#trailsRoot').upper() and co.locator('#addDiscoveryBtn').count() == 0, 'removed Raider only sees the public view')

            # ---- mobile
            mo = new_user(br, B, 'Mobi', mobile=True)
            mt = api(mo, 'POST', '/trails', {'title': 'Mobile trail with a fairly long name to wrap', 'description': 'x', 'mapId': 'pendola-pass'})['data']['trail']['id']
            api(mo, 'POST', f'/trails/{mt}/sessions', {'title': 'Phone run', 'notes': ''})
            for path, name in (('trails.html', 'v63-mobile-dashboard'), (f'trails.html?id={mt}', 'v63-mobile-trail'), ('hunts.html', 'v63-mobile-hunts')):
                mo.goto(B + path); mo.wait_for_load_state('networkidle'); mo.wait_for_timeout(600)
                check(not mo.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), f'mobile 390px: no horizontal overflow on {path.split("?")[0]}{" (detail)" if "id=" in path else ""}')
                shot(mo, name)
            mo.goto(B + f'trails.html?id={mt}'); wait_map(mo); mo.click('#addDiscoveryBtn'); mo.wait_for_selector('#discForm')
            check('not calibrated' in mo.inner_text('.tm-note'), 'uncalibrated map (Pendola Pass) says pins are not calibrated to game coordinates')
            bx = mo.locator('.tm-world').bounding_box(); mo.locator('.tm-world').tap(position={'x': bx['width'] * 0.6, 'y': bx['height'] * 0.4})
            check('Pin placed' in mo.inner_text('#pinStatus'), 'mobile: tapping the map places the pin')
            check(not mo.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'mobile 390px: discovery form has no horizontal overflow')
            shot(mo, 'v63-mobile-discovery-form')
            mo.goto(B + 'hunts.html'); mo.click('#openHuntModal'); mo.click('[data-hunt-mode=trail]'); mo.wait_for_timeout(200)
            check(not mo.evaluate('document.documentElement.scrollWidth > innerWidth + 1') and mo.is_visible('#huntTrailForm'), 'mobile: popup chooser + trail form fit the screen')
            shot(mo, 'v63-mobile-popup-trail', full=False)
            br.close()
    finally:
        srv.cleanup()
    check(not ERRORS, f'no page errors ({ERRORS[:2]})')
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} Loot Trails UI checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
