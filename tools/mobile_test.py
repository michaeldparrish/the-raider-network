"""Mobile overflow regression test (v5.3).
Fails if document.documentElement.scrollWidth > clientWidth on any page at the tested widths.
Also fails if any element extends past the right edge of the viewport, including content clipped inside an
overflow:hidden/auto box. The only exemption is the deliberate swipe strips listed in INTENTIONAL_SCROLLERS.
It also fails if html/body hide horizontal overflow (that would mask the problem rather than fix it), and checks that
the interactive map lets one-finger swipes scroll the page at fit zoom and captures drags once zoomed.
Usage: python3 -m http.server 8080 &  then  python3 tools/mobile_test.py [--shots DIR]"""
import sys, os, json
from playwright.sync_api import sync_playwright
BASE = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else 'http://localhost:8080/'
SERVER_LOGIN = """async () => { await TRN.api.init(); if (TRN.mode !== 'server') return TRN.mode;
  const u = 'qa_layout', pw = 'Qa-Test-Pass-1';   // throw-away local test account: log in, or create it the first time
  try { await TRN.api.post('/auth/login', { login: u, password: pw }); }
  catch (e) { await TRN.api.post('/auth/register', { username: u, display_name: 'QA Raider', email: u + '@example.com', password: pw, confirm_password: pw, region: 'Europe', platform: 'PC', avatar_url: 'raiders/raider-tech-specialist.webp' }); }
  return 'server'; }"""
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
WIDTHS = [(390, 844), (393, 852), (430, 932), (768, 1024), (1440, 900), (1920, 1080)]
PAGES = ['index.html', 'loot.html', 'loot.html?map=stella-montis', 'item.html?id=rotary-encoder', 'item.html?id=kinetic-converter',
         'maps.html', 'map.html?id=dam-battlegrounds', 'map.html?id=stella-montis', 'map.html?id=riven-tides', 'map.html?id=pendola-pass',
         'projects.html', 'hunts.html', 'trade.html', 'auth.html', 'LOGIN', 'profile.html', 'messages.html', 'trails.html',
         'messages.html?to=perisher&name=Perisher&tradeId=pt1&itemId=wolfpack-blueprint&intent=trade']
INTENTIONAL_SCROLLERS = ['gallery-strip']
OFFENDERS = '''(()=>{const W=document.documentElement.clientWidth;const out=[];
 for(const e of document.querySelectorAll('body *')){const r=e.getBoundingClientRect();if(!r.width||r.right<=W+0.5)continue;
  if(getComputedStyle(e).position==='fixed')continue;
  let p=e.parentElement,inScroller=false;while(p&&p!==document.body){if(getComputedStyle(p).overflowX!=='visible'&&%s.some(c=>p.classList.contains(c))){inScroller=true;break}p=p.parentElement}
  if(inScroller)continue;
  if([...e.children].some(c=>c.getBoundingClientRect().right>W+0.5))continue; // report the deepest offender
  out.push(e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+'.'+String(e.className||'').split(' ').slice(0,2).join('.')+' right='+Math.round(r.right)+' w='+Math.round(r.width))}
 return out.slice(0,8)})()''' % json.dumps(INTENTIONAL_SCROLLERS)
fails = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in WIDTHS:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=w < 768, has_touch=True)
        page = ctx.new_page()
        page.route('**/*', lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
        for path in PAGES:
            if path == 'LOGIN':
                if page.evaluate(SERVER_LOGIN) == 'server':
                    continue   # server mode: a real (throw-away) account was registered and the session cookie set
                page.evaluate("()=>{const u={id:'perisher',user_id:'perisher',email:'qa@example.com',password:'password123',display_name:'Perisher',raider_tag:'PER#1',platform:'Cross-platform',region:'NA East',avatar:'raiders/raider-veteran-trader.webp'};localStorage.setItem('trn_users',JSON.stringify([u]));localStorage.setItem('trn_session',JSON.stringify(u))}")
                continue
            page.goto(BASE + path, wait_until='networkidle'); page.wait_for_timeout(500)
            sw, cw = page.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
            bad = page.evaluate(OFFENDERS)
            masks = page.evaluate("[getComputedStyle(document.documentElement).overflowX, getComputedStyle(document.body).overflowX]")
            if any(m in ('hidden', 'clip') for m in masks): bad = bad + ['html/body overflow-x is ' + '/'.join(masks)]
            if path.startswith('map.html') and w < 768 and page.locator('#mvStage').count():
                t0 = page.evaluate("getComputedStyle(document.getElementById('mvStage')).touchAction")
                page.click('#mvIn'); page.wait_for_timeout(100)
                t1 = page.evaluate("getComputedStyle(document.getElementById('mvStage')).touchAction")
                page.click('#mvReset')
                if t0 != 'pan-y' or t1 != 'none': bad = bad + [f'map touch-action fit={t0} zoomed={t1} (want pan-y / none)']
            if sw > cw or bad:
                fails.append({'width': w, 'page': path, 'scrollWidth': sw, 'clientWidth': cw, 'offenders': bad})
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                page.screenshot(path=os.path.join(SHOTS, f"{w}-{path.replace('?', '_').replace('=', '-').replace('&', '_').replace('.html', '')[:60]}.png"), full_page=True)
        ctx.close()
    b.close()
print(json.dumps(fails, indent=1) if fails else 'NO HORIZONTAL OVERFLOW at ' + ', '.join(str(w) for w, _ in WIDTHS))
sys.exit(1 if fails else 0)
