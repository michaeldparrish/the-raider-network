"""v6.4 page bodies for the Amplification Guide (amplification.html) and Amplification Hunt (amplification/hunt.html).
The Guide is pre-rendered from data/amplification.json + data/items.json so it reads (and indexes) without JavaScript;
assets/js/amplification.js adds the item detail dialog, the library filter and the section highlight."""
import json, os, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
e = lambda s: html.escape(str(s if s is not None else ''), quote=True)
STATUS = {'CONFIRMED': ('Confirmed', 'ok'), 'REPORTED': ('Community-reported', 'rep'), 'UNVERIFIED': ('Unverified', 'unv'), 'CONFLICT': ('Conflicting reports', 'con')}


def st(s, short=False):
    t, c = STATUS.get(s or 'UNVERIFIED', STATUS['UNVERIFIED'])
    return f'<span class="amp-st amp-st--{c}">{e(t.split(" ")[0] if short else t)}</span>'


def load():
    amp = json.load(open(os.path.join(ROOT, 'data', 'amplification.json')))
    items = {i['id']: i for i in json.load(open(os.path.join(ROOT, 'data', 'items.json')))['items']}
    return amp, items


def guide_body(I):
    amp, items = load()
    mat = {m['itemId']: m for m in amp['materials']}
    loc = {l['id']: l for l in amp['locations']}
    weapon = {w['id']: w for w in amp['weapons']}
    img = lambda iid: 'assets/images/' + (mat.get(iid, {}).get('card') or items[iid]['image'])
    thumb = lambda iid: 'assets/images/' + (mat.get(iid, {}).get('thumb') or items[iid]['image'])
    nm = lambda iid: items[iid]['name'] if iid in items else iid
    out = []
    out.append(f'''
<section class="amp-hero">
  <img class="amp-hero__bg" src="assets/images/heroes/loot-hunt-squad.webp" alt="">
  <div class="amp-hero__shade"></div>
  <div class="amp-hero__copy">
    <span class="eyebrow">{I('loot-intel')} RAIDER NETWORK FIELD GUIDE · FROZEN TRAIL 2.0</span>
    <h1>Amplification Guide</h1>
    <p>{e(amp['intro']['summary'])}</p>
    <div class="btn-row"><a class="btn btn-lg btn-amp" href="amplification/hunt.html"><svg class="amp-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 3 7v10l9 5 9-5V7Z"/><path d="m3 7 9 5 9-5M12 12v10"/></svg> Start an Amplification Hunt</a><a class="btn btn-ghost btn-lg" href="#library">Browse the 15 materials</a></div>
    <p class="amp-hero__legend">How sure we are: {st('CONFIRMED')} {st('REPORTED')} {st('UNVERIFIED')} {st('CONFLICT')} <span class="muted">Data checked {e(amp['meta']['asOf'])}.</span></p>
  </div>
  <div class="amp-hero__mods" aria-hidden="true">{''.join(f'<img class="amp-mod-{e(t["id"])}" src="{img(t["itemId"])}" alt="">' for t in amp['tiers'])}</div>
</section>
<nav class="amp-toc" aria-label="Guide sections"><a href="#overview">Overview</a><a href="#modules">Modules &amp; weapons</a><a href="#farming">Farming locations</a><a href="#library">All 15 materials</a><a href="#upgrades">Upgrade requirements</a><a href="#sources">Sources</a></nav>
<div class="page-shell amp-shell">''')

    # ---- overview
    ov = amp['intro']
    out.append(f'''<section class="amp-sec" id="overview"><header class="amp-sec__head"><span class="eyebrow">01 · OVERVIEW</span><h2>What amplification is</h2></header>
  <div class="amp-ov">
    <div class="amp-ov__text">{''.join(f'<p>{e(p["text"])} {st(p["status"], True)}</p>' for p in ov['what'])}</div>
    <aside class="panel amp-ov__unlock"><h3>{I('settings')} How to unlock it</h3><ol>{''.join(f'<li>{e(p["text"])} {st(p["status"], True)}</li>' for p in amp['prerequisites'])}</ol></aside>
  </div>
  <div class="amp-ov__cards">
    <div class="amp-mini"><b>1</b><strong>Activate</strong><p>{e(ov['steps']['activate'])}</p></div>
    <div class="amp-mini"><b>2</b><strong>Research &amp; upgrade</strong><p>{e(ov['steps']['upgrade'])}</p></div>
    <div class="amp-mini"><b>3</b><strong>Repair</strong><p>{e(ov['steps']['repair'])}</p></div>
  </div>
  <div class="panel amp-branches" id="branches"><h3>Upgrade branches and restrictions</h3>{''.join(f'<p>{e(p["text"])} {st(p["status"], True)}</p>' for p in ov['branches'])}</div>
</section>''')

    # ---- modules
    out.append('<section class="amp-sec" id="modules"><header class="amp-sec__head"><span class="eyebrow">02 · MODULES &amp; SUPPORTED WEAPONS</span><h2>Amplification Modules Mk. I – V</h2><p>Each weapon rarity has its own module. The module is spent to activate amplification on one tier IV weapon.</p></header><div class="amp-tiers">')
    for t in amp['tiers']:
        ws = ''.join(f'<a class="amp-wchip" href="item.html?id={e(weapon[w]["itemId"])}"><img src="assets/images/{e(items[weapon[w]["itemId"]]["image"])}" alt="">{e(weapon[w]["name"])}</a>' for w in t['weapons'])
        out.append(f'''<article class="amp-tier amp-tier--{e(t['id'])}"><button type="button" class="amp-tier__art" data-amp-item="{e(t['itemId'])}" aria-label="Details: {e(t['name'])}"><img src="{img(t['itemId'])}" alt="{e(t['name'])}" loading="lazy"></button>
  <div class="amp-tier__body"><span class="amp-tier__mk">{e(t['short'])}</span><strong>{e(t['weaponRarity'])} weapons</strong> {st(t['status'], True)}<div class="amp-tier__ws">{ws}</div></div></article>''')
    out.append('</div></section>')

    # ---- farming
    out.append('<section class="amp-sec" id="farming"><header class="amp-sec__head"><span class="eyebrow">03 · WHERE TO FIND MATERIALS</span><h2>Farming locations</h2><p>Reports are still coming in after the Frozen Trail update. Every location below shows how sure we are, and no source we checked publishes drop rates.</p></header><div class="amp-locs">')
    for l in amp['locations']:
        mats = [m for m in amp['materials'] if any(x['locationId'] == l['id'] for x in m['locations'])]
        rows = ''.join(f'''<button type="button" class="amp-locmat" data-amp-item="{e(m['itemId'])}"><img src="{thumb(m['itemId'])}" alt="" loading="lazy"><span><strong>{e(nm(m['itemId']))}</strong><small>{e(next(x for x in m['locations'] if x['locationId'] == l['id']).get('detail') or '')}</small></span>{st(next(x for x in m['locations'] if x['locationId'] == l['id'])['status'], True)}</button>''' for m in mats)
        facts = ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v["text"])} {st(v["status"], True)}</dd></div>' for k, v in l.get('facts', {}).items())
        out.append(f'''<article class="amp-loc amp-loc--{e(l['kind'])}" id="loc-{e(l['id'])}"><header><span class="amp-loc__kind">{e(l['kindLabel'])}</span><h3>{e(l['name'])}</h3>{st(l['status'])}</header>
  <p>{e(l['what'])}</p><dl class="amp-loc__facts">{facts}</dl>
  <div class="amp-loc__mats">{rows or '<p class="muted">No amplification material is confirmed here yet.</p>'}</div></article>''')
    out.append('</div></section>')

    # ---- library
    cards = []
    for m in amp['materials']:
        it = items[m['itemId']]
        search = ' '.join([it['name'], m['role'], m['purpose']] + [loc[x['locationId']]['name'] for x in m['locations']]).lower()
        cards.append(f'''<article class="amp-lib__card amp-rar-{e(it['rarity'].lower())}" id="lib-{e(m['itemId'])}" data-role="{e(m['role'])}" data-search="{e(search)}">
  <a class="amp-lib__art" href="item.html?id={e(m['itemId'])}" data-amp-item="{e(m['itemId'])}" aria-label="Details: {e(it['name'])}"><img src="{img(m['itemId'])}" alt="{e(it['name'])} illustration" loading="lazy"></a>
  <div class="amp-lib__body"><span class="amp-role amp-role--{e(m['role'])}">{e({'activation': 'Activation', 'upgrade': 'Upgrade', 'repair': 'Repair'}[m['role']])}</span><h3>{e(it['name'])}</h3><p>{e(m['purpose'])}</p>
    <p class="amp-lib__where">{I('location')}<span>{e(', '.join(loc[x['locationId']]['name'] for x in m['locations']) or 'Location being verified')}</span></p>
    <a class="btn btn-ghost btn-sm" href="item.html?id={e(m['itemId'])}" data-amp-item="{e(m['itemId'])}">View details</a></div></article>''')
    out.append(f'''<section class="amp-sec" id="library"><header class="amp-sec__head"><span class="eyebrow">04 · ALL 15 MATERIALS</span><h2>Amplification item library</h2></header>
  <div class="toolbar amp-lib__tools"><div class="search-wrap"><svg class="svg-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg><input id="ampSearch" class="input" placeholder="Search materials or locations" aria-label="Search amplification materials"></div>
    <select id="ampRole" class="input" aria-label="Material type"><option value="">All materials</option><option value="activation">Activation modules</option><option value="upgrade">Upgrade materials</option><option value="repair">Repair</option></select></div>
  <p class="result-line"><b id="ampLibCount">{len(cards)}</b> materials shown</p>
  <div class="amp-lib">{''.join(cards)}</div><p class="empty-note hidden" id="ampLibEmpty">No materials match.</p></section>''')

    # ---- upgrade requirements
    out.append('<section class="amp-sec" id="upgrades"><header class="amp-sec__head"><span class="eyebrow">05 · WEAPON UPGRADE REQUIREMENTS</span><h2>Upgrade trees and quantities</h2><p>Every quantity shows how sure we are: confirmed by two or more sources, reported by one, or conflicting. Branches marked &ldquo;Excludes&rdquo; cannot be active together, and upgrades cannot be reverted.</p></header><div class="amp-trees">')
    for t in amp['tiers']:
        for wid in t['weapons']:
            w = weapon[wid]
            rows = ''.join(f'''<tr><th scope="row">{e(u['name'])}{f'<small>{e(u["effect"]["text"])}</small>' if u.get('effect', {}).get('text') else ''}</th>
  <td>{''.join(f'<span class="amp-cost"><img src="{thumb(c["itemId"])}" alt="">{"?" if c["qty"] is None else "×" + str(c["qty"])} {e(nm(c["itemId"]))} {st(c["status"], True)}</span>' for c in u['cost']) or '<span class="muted">Not documented</span>'}</td>
  <td>{e(', '.join(next(x['name'] for x in w['upgrades'] if x['id'] == r) for r in u.get('requires', [])) or '—')}</td>
  <td>{e(', '.join(next(x['name'] for x in w['upgrades'] if x['id'] == r) for r in u.get('excludes', [])) or '—')}</td></tr>''' for u in w['upgrades'])
            out.append(f'''<details class="amp-tree" id="tree-{e(wid)}"><summary><img src="assets/images/{e(items[w['itemId']]['image'])}" alt=""><strong>{e(w['name'])}</strong><span class="amp-tree__mk">{e(t['short'])}</span><span class="muted">{len(w['upgrades'])} upgrades</span></summary>
  <div class="amp-tree__wrap"><table class="amp-table"><thead><tr><th>Upgrade</th><th>Materials</th><th>Requires</th><th>Excludes</th></tr></thead><tbody>{rows}</tbody></table></div>
  {f'<p class="small-note">{e(w["treeNote"]["text"])} {st(w["treeNote"]["status"], True)}</p>' if w.get('treeNote') else ''}
  <a class="btn btn-ghost btn-sm" href="amplification/hunt.html?weapon={e(wid)}">Plan a {e(w['name'])} hunt</a></details>''')
    out.append('</div></section>')

    # ---- conflicts + sources
    out.append(f'''<section class="amp-sec" id="sources"><header class="amp-sec__head"><span class="eyebrow">06 · VERIFICATION</span><h2>Open questions and sources</h2></header>
  <div class="amp-ov"><div class="panel"><h3>Needs checking in game</h3><ul class="amp-conf">{''.join(f'<li>{st(c["status"], True)} {e(c["text"])}</li>' for c in amp['openQuestions'])}</ul></div>
  <div class="panel"><h3>Sources (checked {e(amp['meta']['asOf'])})</h3><ul class="amp-src">{''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])}</a></li>' for s in amp['meta']['sources'])}</ul>
  <p class="small-note">Item illustrations are Raider Network artwork, not in-game renders. Unofficial fan site, not affiliated with Embark Studios.</p></div></div></section>
</div>
<div class="modal hidden" id="ampDetail" role="dialog" aria-modal="true" aria-labelledby="ampDetailTitle"><div class="modal-card amp-detail"><button class="modal-close" type="button" aria-label="Close">×</button><div id="ampDetailBody"></div></div></div>''')
    return '\n'.join(out)


def hunt_body(I):
    return f'''
<section class="amp-hero amp-hero--hunt">
  <img class="amp-hero__bg" src="assets/images/heroes/loot-hunt-squad.webp" alt="">
  <div class="amp-hero__shade"></div>
  <div class="amp-hero__copy">
    <span class="eyebrow">{I('route')} MISSION PLANNER · NEW</span>
    <h1>Amplification Hunt</h1>
    <p>Select a weapon, tell us whether it is already amplified and choose the enhancements you want. We build the full material plan, show where Raiders report finding each part, and track it in a Loot Hunt or one of your Loot Trails.</p>
    <p class="amp-hero__legend"><a class="text-btn" href="amplification.html">How amplification works → Guide</a></p>
  </div>
</section>
<div class="page-shell amp-shell"><div id="ampHuntRoot" class="amp-hunt"><p class="muted">Loading the mission planner…</p></div>
<noscript><p class="notice-bar">The Amplification Hunt needs JavaScript. The <a href="amplification.html#upgrades">Amplification Guide</a> lists every upgrade and material without it.</p></noscript></div>'''
