"""Functional mobile-navigation test (v6). For every width and page it really uses the menu:
  open with the hamburger → every primary link is visible, inside the viewport and is the element actually hit at
  its centre (so nothing covers or clips it) → aria-expanded is correct → no horizontal overflow → close with the
  hamburger → reopen → close with Escape and with an outside tap → reopen → navigate with a menu link → the new
  page loaded. A test that only checks that the hamburger exists is not enough.
Also checks desktop (1440/1920): inline navigation visible, hamburger hidden.
Usage: python3 -m http.server 8080 &  then  python3 tools/nav_test.py [--base http://127.0.0.1:8788/]"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else 'http://localhost:8080/'
MOBILE = [(390, 844), (393, 852), (430, 932), (768, 1024)]
DESKTOP = [(1440, 900), (1920, 1080)]
PAGES = ['index.html', 'loot.html', 'trade.html', 'map.html?id=dam-battlegrounds', 'item.html?id=rotary-encoder']
PRIMARY = ['Home', 'Loot Intel', 'Maps', 'Loot Hunts', 'Trade Board', 'Messages', 'My Profile']
RESULTS = []

LINKS_JS = '''() => { const W = document.documentElement.clientWidth, H = innerHeight;
  return [...document.querySelectorAll('#mainNav > a')].map(a => { const r = a.getBoundingClientRect(), cs = getComputedStyle(a);
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2, hit = document.elementFromPoint(cx, cy);
    return { text: a.textContent.trim(), w: r.width, h: r.height, inView: r.left >= 0 && r.right <= W + 0.5 && r.top >= 0 && r.bottom <= H + 0.5,
             visible: cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0, hit: !!hit && (hit === a || a.contains(hit)) }; }); }'''


def check(cond, label):
    RESULTS.append((bool(cond), label))
    if not cond: print('FAIL ' + label)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h in MOBILE:
            ctx = b.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 768, has_touch=True, device_scale_factor=2)
            pg = ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
            for path in PAGES:
                L = f'[{w}] {path}:'
                pg.goto(BASE + path, wait_until='networkidle'); pg.wait_for_timeout(200)
                btn = pg.locator('#menuBtn')
                check(btn.is_visible(), f'{L} hamburger visible')
                check(pg.locator('#mainNav').is_hidden(), f'{L} primary nav hidden until opened')
                bb = btn.bounding_box(); check(bb and bb['width'] >= 44 and bb['height'] >= 44, f'{L} hamburger touch target >= 44px ({bb})')
                check(btn.get_attribute('aria-expanded') == 'false', f'{L} aria-expanded=false initially')
                row = pg.evaluate("(()=>{const t=document.querySelector('.site-header .topbar').getBoundingClientRect(),a=document.querySelector('.account-actions').getBoundingClientRect();return a.bottom<=t.bottom+0.5&&a.right<=document.documentElement.clientWidth+0.5})()")
                check(row, f'{L} header controls fit on one row (nothing wraps onto the sub-bar)')
                # open
                btn.tap() if w < 768 else btn.click(); pg.wait_for_timeout(150)
                check(btn.get_attribute('aria-expanded') == 'true', f'{L} aria-expanded=true after tap')
                links = pg.evaluate(LINKS_JS)
                check([x['text'] for x in links] == PRIMARY, f'{L} all seven primary destinations present ({[x["text"] for x in links]})')
                for x in links:
                    check(x['visible'] and x['w'] > 0 and x['h'] >= 44, f"{L} '{x['text']}' visible with >=44px target (h={x['h']:.0f})")
                    check(x['inView'], f"{L} '{x['text']}' inside the viewport")
                    check(x['hit'], f"{L} '{x['text']}' is clickable (not covered or clipped)")
                sw, cw = pg.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
                check(sw <= cw, f'{L} no horizontal overflow with menu open ({sw}>{cw})')
                # close with hamburger, reopen
                btn.click(); pg.wait_for_timeout(100)
                check(pg.locator('#mainNav').is_hidden() and btn.get_attribute('aria-expanded') == 'false', f'{L} hamburger closes the menu')
                btn.click(); pg.wait_for_timeout(100)
                check(pg.locator('#mainNav').is_visible(), f'{L} menu reopens')
                check(pg.evaluate("document.activeElement?.closest('#mainNav') !== null"), f'{L} focus moves into the menu on open (keyboard)')
                pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
                check(pg.locator('#mainNav').is_hidden() and pg.evaluate("document.activeElement?.id") == 'menuBtn', f'{L} Escape closes and returns focus to the hamburger')
                btn.click(); pg.wait_for_timeout(100)
                pg.locator('main').dispatch_event('pointerdown')   # a tap outside the drawer
                pg.wait_for_timeout(100)
                check(pg.locator('#mainNav').is_hidden(), f'{L} tapping outside closes the menu')
            # navigate with a menu link (once per width)
            pg.goto(BASE + 'index.html', wait_until='networkidle')
            pg.locator('#menuBtn').click(); pg.wait_for_timeout(100)
            pg.locator('#mainNav > a', has_text='Maps').click(); pg.wait_for_load_state('networkidle')
            check(pg.evaluate("document.body.dataset.page") == 'maps' and pg.locator('#mainNav').is_hidden(), f'[{w}] menu link navigates to Maps')
            pg.locator('#menuBtn').click(); pg.wait_for_timeout(100)
            pg.locator('#mainNav > a', has_text='Trade Board').click(); pg.wait_for_load_state('networkidle')
            check(pg.evaluate("document.body.dataset.page") == 'trade', f'[{w}] menu link navigates to Trade Board')
            check(not errs, f'[{w}] no JavaScript errors ({errs[:2]})')
            ctx.close()
        for w, h in DESKTOP:
            ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page()
            pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
            pg.goto(BASE + 'index.html', wait_until='networkidle')
            check(pg.locator('#menuBtn').is_hidden(), f'[{w}] desktop: hamburger hidden')
            links = pg.evaluate(LINKS_JS)
            check([x['text'] for x in links] == PRIMARY and all(x['visible'] and x['inView'] and x['hit'] for x in links), f'[{w}] desktop: inline navigation visible and clickable')
            ctx.close()
        b.close()
    fails = [l for ok, l in RESULTS if not ok]
    print(f'{len(RESULTS) - len(fails)}/{len(RESULTS)} navigation checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
