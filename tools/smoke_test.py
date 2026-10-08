"""Smoke test for The Raider Network v5.
Usage:  python3 -m http.server 8080   (in project root, separate terminal)
        python3 tools/smoke_test.py [--shots DIR]
Checks every page at desktop (1440) and mobile (390) widths for JS errors, failed local requests,
horizontal overflow and empty render containers. Requires: pip install playwright (Chromium)."""
import sys, os, json
from playwright.sync_api import sync_playwright

BASE = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else 'http://localhost:8080/'
SERVER_LOGIN = """async () => { await TRN.api.init(); if (TRN.mode !== 'server') return TRN.mode;
  const u = 'qa_layout', pw = 'Qa-Test-Pass-1';   // throw-away local test account: log in, or create it the first time
  try { await TRN.api.post('/auth/login', { login: u, password: pw }); }
  catch (e) { await TRN.api.post('/auth/register', { username: u, display_name: 'QA Raider', email: u + '@example.com', password: pw, confirm_password: pw, region: 'Europe', platform: 'PC', avatar_url: 'raiders/raider-tech-specialist.webp' }); }
  return 'server'; }"""
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
PAGES = [
    ('index.html', '#popularLoot .item-card'), ('loot.html', '#lootResults .item-card'),
    ('item.html?id=rotary-encoder', '.where-panel'), ('item.html?id=vaporizer-regulator', '.where-panel'),
    ('item.html?id=queen-reactor', '.where-panel'), ('maps.html', '#mapGrid .map-card'),
    ('map.html?id=stella-montis', '.mv-stage'), ('map.html?id=pendola-pass', '.cond-card'), ('map.html?id=dam-battlegrounds', '#mvImg'), ('loot.html?map=spaceport', '.loot-map-banner'), ('item.html?id=leaper-pulse-unit', '.where-panel'), ('map.html?id=riven-tides', '.poi-card'), ('projects.html', '.project-full'),
    ('hunts.html', '#huntGrid .hunt-card'), ('trade.html', '#tradeRequestGrid .trade-card'), ('auth.html', '#loginForm'),
    ('loot.html?quest=with-a-view', '#lootResults .item-card'), ('item.html?id=does-not-exist', '.empty-state'),
    ('LOGIN', None), ('profile.html', '#profileForm'), ('messages.html?to=perisher&name=Perisher&tradeId=pt1&itemId=wolfpack-blueprint&intent=trade', '#chatRegarding'),
]
problems = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome' if os.path.exists('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') else None)
    for label, vp in [('desktop', {'width': 1440, 'height': 900}), ('mobile', {'width': 390, 'height': 844})]:
        ctx = b.new_context(viewport=vp, device_scale_factor=1)
        page = ctx.new_page()
        FONTS = os.environ.get('TRN_FONT_DIR')  # optional: folder with @fontsource woff2 files
        def router(r):
            u = r.request.url
            if u.startswith(BASE): return r.continue_()
            if FONTS and 'fonts.googleapis.com/css2' in u:
                css = ''.join(f"@font-face{{font-family:'{fam}';font-weight:{w};font-display:swap;src:url(https://fonts.local/{f}-latin-{w}-normal.woff2) format('woff2')}}"
                              for fam, f, ws in [('Barlow Condensed', 'barlow-condensed', (500, 600, 700, 800)), ('Inter', 'inter', (400, 500, 600, 700))] for w in ws)
                return r.fulfill(status=200, content_type='text/css', body=css)
            if FONTS and u.startswith('https://fonts.local/'):
                return r.fulfill(status=200, content_type='font/woff2', body=open(os.path.join(FONTS, u.rsplit('/', 1)[1]), 'rb').read())
            return r.abort()
        page.route('**/*', router)
        errs = []
        page.on('pageerror', lambda e: errs.append(('pageerror', str(e))))
        page.on('console', lambda m: m.type == 'error' and errs.append(('console', m.text)))
        page.on('requestfailed', lambda r: r.url.startswith(BASE) and errs.append(('requestfailed', r.url)))
        page.on('response', lambda r: r.url.startswith(BASE) and r.status >= 400 and errs.append(('http', f'{r.status} {r.url}')))
        for path, sel in PAGES:
            if path == 'LOGIN':
                if page.evaluate(SERVER_LOGIN) == 'server':
                    continue   # server mode: a real (throw-away) account was registered and the session cookie set
                page.evaluate("()=>{const u={id:'u1',user_id:'u1',email:'qa@example.com',password:'password123',display_name:'QA Raider',raider_tag:'QA#0001',platform:'PC',region:'Europe',avatar:'raiders/raider-tech-specialist.webp'};localStorage.setItem('trn_users',JSON.stringify([u]));localStorage.setItem('trn_session',JSON.stringify(u))}")
                continue
            errs.clear()
            page.goto(BASE + path, wait_until='networkidle')
            try:
                page.wait_for_selector(sel, timeout=6000)
            except Exception:
                problems.append((label, path, 'missing ' + sel))
            page.wait_for_timeout(250)
            # look for any element poking past the viewport (tools/mobile_test.py also checks scrollWidth)
            wide = page.evaluate('''[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();if(!r.width||r.right<=innerWidth+1||getComputedStyle(e).position==='fixed')return false;let p=e.parentElement;while(p&&p!==document.body){if(getComputedStyle(p).overflowX!=='visible')return false;p=p.parentElement}return true}).slice(0,6).map(e=>e.tagName+'.'+(e.className||'').toString().slice(0,40)+' r='+Math.round(e.getBoundingClientRect().right))''')
            if wide:
                problems.append((label, path, 'element wider than viewport', wide))
            # In demo mode (python http.server) the backend probe GET /api/health returns 404 by design: that is how
            # the page knows there is no API. Ignore that one response and its matching console line.
            if any(e[0] == 'http' and e[1].startswith('404') and '/api/health' in e[1] for e in errs):
                errs[:] = [e for e in errs if not (e[0] == 'http' and '/api/health' in e[1])]
                i = next((k for k, e in enumerate(errs) if e[0] == 'console' and '404' in e[1]), None)
                if i is not None: errs.pop(i)
            for e in errs:
                if any(k in e[1] for k in ('supabase', 'fonts.g', 'jsdelivr', 'ERR_TUNNEL', 'ERR_FAILED')):
                    continue
                problems.append((label, path) + e)
            if SHOTS:
                page.evaluate('async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,40))}scrollTo(0,0)}')
                page.wait_for_timeout(300)
                os.makedirs(SHOTS, exist_ok=True)
                page.screenshot(path=os.path.join(SHOTS, f"{label}-{path.replace('?', '_').replace('=', '-').replace('.html', '')}.png"), full_page=True)
        ctx.close()
    b.close()
print(json.dumps(problems, indent=1) if problems else 'ALL CLEAR')
sys.exit(1 if problems else 0)
