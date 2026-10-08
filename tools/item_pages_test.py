"""v6.1: open every item page (all 581 catalog IDs) and fail on any render error, page error or broken item image.
Usage: python3 tools/item_pages_test.py [--base http://localhost:8080/]"""
import sys, json, os
from playwright.sync_api import sync_playwright
BASE = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else 'http://localhost:8080/'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ids = [i['id'] for i in json.load(open(os.path.join(ROOT, 'data', 'items.json')))['items']]
bad = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    for n, iid in enumerate(ids):
        errs.clear(); pg.goto(BASE + f'item.html?id={iid}'); pg.wait_for_selector('footer', state='attached'); pg.wait_for_timeout(120)
        body = pg.inner_text('body')
        img_ok = pg.evaluate("() => [...document.querySelectorAll('main img')].filter(i => i.src.includes('/items/')).every(i => i.complete && i.naturalWidth > 0)")
        if 'went wrong' in body or errs or not img_ok or 'Item not found' in body:
            bad.append((iid, 'render-error' if 'went wrong' in body else 'image' if not img_ok else 'not-found' if 'Item not found' in body else errs[:1]))
    b.close()
print(f'{len(ids) - len(bad)}/{len(ids)} item pages render cleanly')
for x in bad[:40]: print('FAIL', x)
sys.exit(1 if bad else 0)
