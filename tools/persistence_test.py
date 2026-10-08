"""End-to-end persistence test (v6): real browser + Cloudflare's local runtime + a throw-away local D1 database.

  1. User A registers through the UI (starting from POST A TRADE REQUEST while logged out) and posts a trade.
  2. The server is restarted (same D1 data, like a new deployment).
  3. A brand-new browser context (no cookies, no localStorage) sees the trade logged out, then logs in as A.
  4. Clearing localStorage does not lose anything; the account and trade are server-side.
  5. User B (another fresh context) sees A's trade, cannot manage it, and makes an offer.
  6. A edits, sees and accepts the offer, closes and deletes the trade through the UI.
Usage: python3 tools/persistence_test.py   (needs Node.js + wrangler, and Playwright with Chromium)"""
import sys, uuid
from playwright.sync_api import sync_playwright
from devserver import DevServer

RESULTS = []


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def new_page(browser, base, **kw):
    ctx = browser.new_context(**kw)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())   # offline: no fonts/CDNs
    return ctx, page, errors


def main():
    srv = DevServer(port=8798); srv.migrate(); srv.start(); B = srv.base
    tag = uuid.uuid4().hex[:6]
    ua, ub, pw = f'pers_a_{tag}', f'pers_b_{tag}', 'Persist-Test-77'
    note = f'Persistence check {tag}'
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            # ---------------------------------------------------------------- 1. register + post as A
            ctx, pg, errs = new_page(br, B, viewport={'width': 1440, 'height': 900})
            pg.goto(B + 'trade.html', wait_until='networkidle')
            check(pg.evaluate('TRN.mode') == 'server', 'site runs in server mode against the API')
            check(pg.locator('#navLogin:not(.hidden)').count() == 1 and pg.locator('#navJoin:not(.hidden)').count() == 1, 'logged-out header shows Log in + Register')
            check(pg.locator('#modePill:not(.hidden)').count() == 0, 'no DEMO MODE indicator in server mode')
            pg.click('#openTradeModal'); pg.wait_for_url(lambda u: '/auth' in u)
            check('next=trade.html' in pg.url, 'POST A TRADE REQUEST while logged out goes to login/register with a return path')
            pg.click('#registerTab'); f = pg.locator('#registerForm')
            f.locator('[name=username]').fill(ua); f.locator('[name=display_name]').fill('Persist A'); f.locator('[name=email]').fill(f'{ua}@example.com')
            f.locator('[name=password]').fill(pw); f.locator('[name=confirm_password]').fill(pw + 'x')
            f.locator('button[type=submit]').click(); pg.wait_for_timeout(300)
            check('do not match' in pg.inner_text('#registerMsg'), 'client-side validation catches mismatched passwords')
            f.locator('[name=confirm_password]').fill(pw); f.locator('button[type=submit]').click()
            pg.wait_for_url(lambda u: '/trade' in u, timeout=10000); pg.wait_for_selector('#tradeModal:not(.hidden)')
            check(True, 'after registering, the visitor is returned to the trade form')
            pg.fill('#tradeForm [name=want]', 'Rotary Encoder'); pg.fill('#tradeForm [name=have]', 'Snap Hook'); pg.fill('#tradeForm [name=notes]', note)
            pg.select_option('#tradeForm [name=region]', 'Europe'); pg.click('#tradeSubmit')
            pg.wait_for_selector(f'.trade-card:has-text("{note}")', timeout=8000)
            check(pg.locator(f'.trade-card:has-text("{note}") .owner-bar--server').count() == 1, 'trade created; owner controls shown to A')
            keys = pg.evaluate('Object.keys(localStorage)')
            check(not any(k in keys for k in ['trn_users', 'trn_session', 'trn_trades']), f'no account/trade data in localStorage ({keys})')
            check(pg.evaluate("document.cookie").find('trn_session') == -1, 'session cookie is not readable by JavaScript (HttpOnly)')
            ctx.close()

            # ---------------------------------------------------------------- 2. restart the server
            srv.restart()
            rows = srv.sql(f"SELECT u.username, t.notes FROM trade_posts t JOIN users u ON u.id = t.user_id WHERE t.notes = '{note}'")
            check(len(rows) == 1 and rows[0]['username'] == ua, 'after restart the trade row is still in D1')

            # ---------------------------------------------------------------- 3. fresh browser, logged out, then log in
            ctx2, pg2, errs2 = new_page(br, B, viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            pg2.goto(B + 'trade.html', wait_until='networkidle')
            check(pg2.locator(f'.trade-card:has-text("{note}")').count() == 1, 'fresh browser (logged out) sees the trade after restart')
            pg2.goto(B + 'auth.html#login'); pg2.fill('#loginForm [name=login]', ua); pg2.fill('#loginForm [name=password]', pw); pg2.click('#loginForm button')
            pg2.wait_for_url(lambda u: '/profile' in u, timeout=10000); pg2.wait_for_selector('#profileMeta .handle')
            check(pg2.text_content('#profileName') == 'Persist A' and f'@{ua}' in pg2.inner_text('#profileMeta'), 'User A still exists: log in from a fresh browser works')
            check('Joined' in pg2.inner_text('#profileMeta'), 'profile shows join date')
            try: pg2.wait_for_function("document.querySelector('#statActive') && document.querySelector('#statActive').textContent === '1'", timeout=8000)
            except Exception: pass
            check(pg2.text_content('#statActive') == '1' and pg2.text_content('#statActiveLabel') == 'Active trades', f"profile shows 1 active trade ({pg2.text_content('#statActive')} {pg2.text_content('#statActiveLabel')})")
            check(f'{ua}@example.com' not in pg2.inner_text('body'), 'email is not shown on the profile page')
            pg2.evaluate('localStorage.clear(); sessionStorage.clear()'); pg2.goto(B + 'trade.html', wait_until='networkidle')
            check(pg2.locator(f'.trade-card:has-text("{note}") .owner-bar--server').count() == 1, 'clearing browser storage loses nothing (still logged in, trade still there)')

            # ---------------------------------------------------------------- 5. user B
            ctx3, pg3, errs3 = new_page(br, B, viewport={'width': 1440, 'height': 900})
            pg3.goto(B + 'auth.html#register'); f = pg3.locator('#registerForm')
            f.locator('[name=username]').fill(ub); f.locator('[name=display_name]').fill('Persist B'); f.locator('[name=email]').fill(f'{ub}@example.com')
            f.locator('[name=password]').fill(pw); f.locator('[name=confirm_password]').fill(pw); f.locator('button[type=submit]').click()
            pg3.wait_for_url(lambda u: '/profile' in u, timeout=10000)
            pg3.goto(B + 'trade.html', wait_until='networkidle')
            card = pg3.locator(f'.trade-card:has-text("{note}")')
            check(card.count() == 1 and card.locator('.owner-bar--server').count() == 0, "user B sees A's trade without owner controls")
            card.locator('.trade-respond').click(); pg3.wait_for_selector('#offerModal:not(.hidden)')
            pg3.fill('#offerForm [name=offer]', 'Snap Hook'); pg3.fill('#offerForm [name=message]', 'Can trade tonight, EU.')
            pg3.click('#offerForm button[type=submit]'); pg3.wait_for_selector(f'.trade-card:has-text("{note}") .offer-sent', timeout=8000)
            check(True, 'user B sends an offer through the UI')

            # ---------------------------------------------------------------- 6. A manages the trade
            pg2.goto(B + 'trade.html', wait_until='networkidle')
            c2 = pg2.locator(f'.trade-card:has-text("{note}")')
            check(c2.locator('.count-pill').inner_text() == '1', 'A sees 1 pending offer on the card')
            c2.locator('[data-offers]').click(); pg2.wait_for_selector('.offer-panel .offer-row')
            check('Can trade tonight' in c2.locator('.offer-panel').inner_text(), "A can read B's offer")
            c2.locator('[data-offer-act=accept]').click(); pg2.wait_for_timeout(800)
            c2 = pg2.locator(f'.trade-card:has-text("{note}")')
            c2.locator('[data-edit]').click(); pg2.wait_for_selector('#tradeModal:not(.hidden)')
            check(pg2.input_value('#tradeForm [name=notes]') == note, 'edit form is pre-filled with the stored trade')
            pg2.fill('#tradeForm [name=notes]', note + ' (edited)'); pg2.click('#tradeSubmit')
            pg2.wait_for_selector(f'.trade-card:has-text("{note} (edited)")', timeout=8000)
            check(True, 'A edits the trade through the UI')
            pg3.goto(B + 'trade.html', wait_until='networkidle')
            check(pg3.locator(f'.trade-card:has-text("{note} (edited)")').count() == 1, "B sees A's edit")
            check(srv.sql(f"SELECT o.status FROM trade_offers o JOIN trade_posts t ON t.id = o.trade_post_id WHERE t.notes = '{note} (edited)'")[0]['status'] == 'ACCEPTED', 'offer accepted in D1')
            # B tries to change A's trade from the browser console: the server refuses
            tid = pg3.locator(f'.trade-card:has-text("{note} (edited)")').get_attribute('id')
            res = pg3.evaluate("async id => { try { await TRN.store.updateTrade(id, { status: 'closed' }); return 'changed'; } catch (e) { return e.status + ' ' + e.message; } }", tid)
            check(res.startswith('403'), f"B cannot close A's trade even by calling the API directly ({res})")
            res = pg3.evaluate("async id => { try { await TRN.store.deleteTrade(id); return 'deleted'; } catch (e) { return String(e.status); } }", tid)
            check(res == '403', "B cannot delete A's trade even by calling the API directly")
            c2 = pg2.locator(f'#{tid}')
            c2.locator('[data-set-status][data-to=closed]').click(); pg2.wait_for_timeout(800)
            pg2.select_option('#tradeStatus', 'closed'); pg2.wait_for_timeout(200)
            check(pg2.locator(f'#{tid}').is_visible() and 'CLOSED' in pg2.locator(f'#{tid} .status-chip').first.inner_text(), 'A closes the trade through the UI')
            pg2.locator(f'#{tid} [data-delete]').click(); pg2.locator(f'#{tid} [data-delete]').click(); pg2.wait_for_timeout(1000)
            check(pg2.locator(f'#{tid}').count() == 0, 'A deletes the trade (two-step confirm)')
            check(srv.sql(f"SELECT COUNT(*) AS n FROM trade_posts WHERE id = '{tid}'")[0]['n'] == 0, 'trade removed from D1')
            check(not (errs + errs2 + errs3), f'no JavaScript errors ({(errs + errs2 + errs3)[:3]})')
            br.close()
    finally:
        srv.cleanup()
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} persistence checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
