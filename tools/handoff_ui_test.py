"""v6.2 browser test for the trade handoff UI on Cloudflare's local runtime with a THROW-AWAY local D1 database.
  python3 tools/handoff_ui_test.py [--shots DIR]
Covers: accept -> handoff page, Embark ID display + Copy button (clipboard), missing-ID prompt and inline save,
one-time banner, View Trade Details on My Profile, Messages inbox, both-player confirmation, cancellation UI,
third-party denial, public "Awaiting exchange" chip, a pre-v6.2 completed trade opened read-only, mobile layout."""
import sys, os, uuid
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import DevServer

SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
RESULTS, ERRORS = [], []
PW = 'Handoff-Ui-Pass-77'


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def shot(page, name, full=True):
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name + '.png'), full_page=full)


def api(page, method, path, body=None):
    return page.evaluate("""async ([m, p, b]) => { const r = await fetch('/api' + p, { method: m, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-TRN-CSRF': '1', Accept: 'application/json' }, body: b ? JSON.stringify(b) : undefined });
        return { status: r.status, data: await r.json().catch(() => null) }; }""", [method, path, body])


def new_user(browser, base, name, embark, mobile=False):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844} if mobile else {'width': 1360, 'height': 900}, is_mobile=mobile, has_touch=mobile)
    ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=base.rstrip('/'))
    pg = ctx.new_page(); pg.on('pageerror', lambda e: ERRORS.append(f'{name}: {e}'))
    pg.goto(base + 'index.html'); pg.wait_for_load_state('networkidle')
    u = (name.lower() + uuid.uuid4().hex[:5])[:20]
    body = {'username': u, 'display_name': name, 'email': f'{u}@example.com', 'password': PW, 'confirm_password': PW, 'region': 'NA East', 'platform': 'PlayStation'}
    if embark: body['raider_tag'] = embark
    r = api(pg, 'POST', '/auth/register', body); assert r['status'] == 201, r
    pg.username, pg.uid, pg.name = u, r['data']['user']['id'], name
    return pg


def main():
    srv = DevServer(port=8794); srv.migrate(); srv.start(); B = srv.base
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ann = new_user(br, B, 'Annika', 'Annika.R#2048')      # trade owner
            bo = new_user(br, B, 'Bodhi', None)                    # offer sender, no Embark ID yet
            cy = new_user(br, B, 'Cyrus', 'Cyrus#9090')            # outsider
            t = api(ann, 'POST', '/trades', {'wanted_item_id': 'tempest-blueprint', 'offered_item_id': 'anvil-blueprint', 'region': 'NA East', 'platform': 'PlayStation'})['data']['trade']['id']
            o = api(bo, 'POST', f'/trades/{t}/offers', {'message': 'Tempest BP for your Anvil BP, tonight?', 'offered_item_id': 'tempest-blueprint'})['data']['offer']['id']

            # owner accepts on My Profile -> lands on the handoff page
            ann.goto(B + 'profile.html'); ann.wait_for_selector('#myOffers [data-act="accept"]')
            ann.click('#myOffers [data-act="accept"]'); ann.wait_for_url('**/handoff*id=*', timeout=15000); ann.wait_for_selector('.hp-head h1')
            hid = ann.url.split('id=')[1]
            txt = ann.inner_text('#handoffRoot')
            check('TRADE WITH BODHI' in txt.upper() and 'AWAITING EXCHANGE' in txt.upper(), 'accepting on My Profile opens the private handoff page')
            check("hasn't added their Embark ID" in txt, 'owner sees a prompt that the other Raider has no Embark ID yet')
            check('Anvil Blueprint' in txt and 'Tempest Blueprint' in txt and 'HOW TO CONNECT IN ARC RAIDERS' in txt.upper(), 'agreed items and connection instructions are shown')
            shot(ann, 'v62-handoff-owner-waiting-for-id')

            # public board shows "Awaiting exchange" without names/IDs
            anon = br.new_context().new_page(); anon.goto(B + 'trade.html'); anon.wait_for_selector('.trade-card')
            card = anon.locator('.trade-card', has_text='Annika').first.inner_text()
            check('AWAITING EXCHANGE' in card and 'Annika.R#2048' not in anon.content(), 'public Trade Board shows AWAITING EXCHANGE and no Embark ID')

            # sender: banner on My Profile, View Trade Details, inline Embark ID save
            bo.goto(B + 'profile.html'); bo.wait_for_selector('.handoff-banner')
            check('TRADE ACCEPTED' in bo.inner_text('.handoff-banner').upper(), 'offer sender sees the one-time "Trade accepted — view details" banner')
            check(bo.locator('#myOffers a', has_text='View Trade Details').count() >= 1 and bo.locator('#myHandoffs a', has_text='View Trade Details').count() == 1,
                  'sent offer shows ACCEPTED with an orange View Trade Details button; Accepted Trades panel lists it')
            shot(bo, 'v62-profile-banner-sender')
            bo.click('.handoff-banner a'); bo.wait_for_selector('#otherEmbarkId')
            check(bo.inner_text('#otherEmbarkId') == 'Annika.R#2048', 'sender sees the owner\'s Embark ID')
            bo.click('#copyEmbark'); bo.wait_for_timeout(300)
            check(bo.evaluate('navigator.clipboard.readText()') == 'Annika.R#2048' and 'Copied' in bo.inner_text('#copyEmbark'), 'Copy Embark ID puts the exact ID on the clipboard')
            check(bo.locator('#myIdForm').count() == 1, 'sender is prompted to add their own Embark ID')
            bo.fill('#myIdForm [name=raider_tag]', 'not valid'); bo.click('#myIdForm button'); bo.wait_for_timeout(500)
            check('Embark ID' in bo.inner_text('#myIdForm .form-note'), 'invalid Embark ID gets a helpful error')
            bo.fill('#myIdForm [name=raider_tag]', 'Bodhi_K#0007'); bo.click('#myIdForm button'); bo.wait_for_selector('text=Your Embark ID shared with')
            shot(bo, 'v62-handoff-sender')
            bo.goto(B + 'profile.html'); bo.wait_for_selector('#myHandoffs .handoff-row')
            check(bo.locator('.handoff-banner').count() == 0, 'banner does not repeat after the handoff was opened')

            # owner now sees the sender's ID
            ann.reload(); ann.wait_for_selector('#otherEmbarkId')
            check(ann.inner_text('#otherEmbarkId') == 'Bodhi_K#0007', 'owner sees the sender\'s Embark ID as soon as it is saved')

            # third party
            cy.goto(B + f'handoff.html?id={hid}'); cy.wait_for_selector('#handoffRoot .notice-bar')
            check('not found' in cy.inner_text('#handoffRoot').lower() and 'Annika.R#2048' not in cy.content() and 'Bodhi_K#0007' not in cy.content(),
                  'a third party opening the handoff URL sees "not found" and no IDs')

            # Messages inbox
            bo.goto(B + 'messages.html'); bo.wait_for_selector('#handoffList .handoff-row')
            check(bo.locator('.messages-shell').is_hidden() and 'Annika' in bo.inner_text('#handoffList') and 'View Trade Details' in bo.inner_text('#handoffList'),
                  'Messages shows the Trade Handoffs inbox (no chat)')
            shot(bo, 'v62-messages-inbox')

            # both-player confirmation (two-step button)
            bo.goto(B + f'handoff.html?id={hid}'); bo.wait_for_selector('#confirmBtn')
            bo.click('#confirmBtn'); check('Yes' in bo.inner_text('#confirmBtn'), 'confirm asks for a second click before recording')
            bo.click('#confirmBtn'); bo.wait_for_selector('.hp-waiting')
            check('waiting for annika' in bo.inner_text('.hp-waiting').lower(), 'after confirming, the sender waits for the owner')
            ann.reload(); ann.wait_for_selector('#confirmBtn')
            check('Bodhi has already confirmed' in ann.inner_text('.hp-actions'), 'owner sees the other Raider\'s confirmation')
            shot(ann, 'v62-handoff-owner-before-confirm')
            ann.click('#confirmBtn'); ann.click('#confirmBtn'); ann.wait_for_selector('.notice-bar--ok')
            check('Trade completed' in ann.inner_text('.notice-bar--ok'), 'second confirmation completes the trade')
            shot(ann, 'v62-handoff-completed')
            check(api(anon, 'GET', f'/trades/{t}')['data']['trade']['status'] == 'COMPLETED', 'trade post is COMPLETED')

            # cancellation UI
            t2 = api(ann, 'POST', '/trades', {'wanted_item_id': 'bobcat-blueprint', 'region': 'NA East', 'platform': 'PlayStation'})['data']['trade']['id']
            o2 = api(bo, 'POST', f'/trades/{t2}/offers', {'message': 'have it'})['data']['offer']['id']
            ann.goto(B + 'trade.html'); ann.wait_for_selector('.trade-card')
            ann.locator(f'[data-offers="{t2}"]').click(); ann.wait_for_selector(f'[data-offers-for="{t2}"] [data-offer-act="accept"]')
            ann.click(f'[data-offers-for="{t2}"] [data-offer-act="accept"]'); ann.wait_for_url('**/handoff*id=*', timeout=15000)
            check(True, 'accepting from the Trade Board offers panel opens the handoff page')
            ann.wait_for_selector('.hp-more summary'); ann.locator('.hp-actions .hp-more summary').click()
            ann.select_option('#cancelForm select', 'could_not_connect'); ann.click('#cancelForm button'); ann.wait_for_selector('text=This trade was cancelled')
            check('Bodhi_K#0007' not in ann.inner_text('#handoffRoot'), 'after cancelling, the other Raider\'s Embark ID is no longer shown')
            ann.locator('.hp-report summary').click(); ann.select_option('#reportForm select', 'no_show'); ann.click('#reportForm button'); ann.wait_for_selector('text=Your report was sent')
            check(True, 'report form submits privately')

            # pre-v6.2 completed trade (inserted exactly as v6.1 stored it) opens read-only
            now = '2026-10-08T20:54:55.464Z'
            srv.sql(f"INSERT INTO trade_posts (id, user_id, wanted_item_id, wanted_item_name, wanted_quantity, offered_item_id, offered_item_name, offered_quantity, open_to_offers, region, platform, desired_time, status, created_at, updated_at, closed_at) VALUES ('trd_legacy1', '{ann.uid}', NULL, 'Compensator 3', 1, 'tempest-blueprint', 'Tempest Blueprint', 1, 1, 'NA East', 'PlayStation', 'Anytime', 'COMPLETED', '{now}', '2026-10-08T21:00:07.205Z', '2026-10-08T21:00:07.205Z')")
            srv.sql(f"INSERT INTO trade_offers (id, trade_post_id, from_user_id, message, status, created_at, updated_at) VALUES ('ofr_legacy1', 'trd_legacy1', '{bo.uid}', 'Compensator III for your Tempest BP', 'ACCEPTED', '{now}', '{now}')")
            before = srv.sql("SELECT * FROM trade_posts WHERE id = 'trd_legacy1'")
            bo.goto(B + 'profile.html'); bo.wait_for_selector('#myHandoffs .handoff-row')
            row = bo.locator('#myHandoffs .handoff-row', has_text='Compensator 3')
            check(row.count() == 1 and 'ACCEPTED' in row.inner_text(), 'pre-v6.2 accepted trade is listed with View Trade Details')
            row.locator('a').click(); bo.wait_for_selector('.hp-head')
            check('Completed before trade handoffs existed' in bo.inner_text('#handoffRoot') and bo.locator('#confirmBtn').count() == 0 and bo.locator('#shareIdBtn').count() == 1 and bo.locator('#otherEmbarkId').count() == 0,
                  'it opens read-only with no confirm button; IDs are shared only with an explicit Share button')
            ann.goto(B + 'profile.html'); ann.wait_for_selector('#myHandoffs .handoff-row'); ann.locator('#myHandoffs .handoff-row', has_text='Compensator 3').locator('a').click(); ann.wait_for_selector('#shareIdBtn')
            ann.click('#shareIdBtn'); ann.wait_for_selector("text=You've shared your Embark ID")
            bo.reload(); bo.wait_for_selector('#otherEmbarkId')
            check(bo.inner_text('#otherEmbarkId') == 'Annika.R#2048', 'after the owner presses Share, the historical handoff shows their Embark ID')
            shot(bo, 'v62-handoff-historical')
            check(srv.sql("SELECT * FROM trade_posts WHERE id = 'trd_legacy1'") == before, 'opening it did not change the historical trade row')

            # mobile
            mo = new_user(br, B, 'Mobi', 'Mobi#1234', mobile=True)
            t3 = api(mo, 'POST', '/trades', {'wanted_item_id': 'arc-alloy', 'region': 'NA East', 'platform': 'PlayStation'})['data']['trade']['id']
            o3 = api(cy, 'POST', f'/trades/{t3}/offers', {'message': 'have 2'})['data']['offer']['id']
            h3 = api(mo, 'PATCH', f'/offers/{o3}', {'action': 'accept'})['data']['handoff']['id']
            for path, name in ((f'handoff.html?id={h3}', 'v62-mobile-handoff'), ('messages.html', 'v62-mobile-messages'), ('profile.html', 'v62-mobile-profile')):
                mo.goto(B + path); mo.wait_for_load_state('networkidle'); mo.wait_for_timeout(600)
                ov = mo.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                check(not ov, f'mobile 390px: no horizontal overflow on {path.split("?")[0]}')
                shot(mo, name)
            mo.goto(B + f'handoff.html?id={h3}'); mo.wait_for_selector('#copyEmbark')
            bx = mo.locator('#copyEmbark').bounding_box(); row = mo.locator('.hp-id__row').bounding_box(); check(bx and bx['width'] >= row['width'] * 0.95, 'mobile: Copy Embark ID is a full-width button')
            br.close()
    finally:
        srv.cleanup()
    check(not ERRORS, f'no page errors ({ERRORS[:2]})')
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} handoff UI checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
