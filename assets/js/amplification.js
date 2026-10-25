/* The Raider Network v6.4 — Amplification Guide (/amplification) and Amplification Hunt (/amplification/hunt).
 * Everything comes from data/amplification.json (built from tools/source-data/amplification.json) and the Loot Intel
 * catalog. Every fact carries a status: CONFIRMED, REPORTED (community), UNVERIFIED or CONFLICT. Nothing here writes data:
 * hunting hands off to the existing Loot Hunt popup and the existing Loot Trails pages. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  const enc = encodeURIComponent;
  const A = () => TRN.db.amp;

  /* ---------------------------------------------------------------- shared helpers */
  const STATUS = {
    CONFIRMED: ['Confirmed', 'amp-st--ok', 'Two or more independent sources agree, or the in-game item page states it.'],
    REPORTED: ['Community-reported', 'amp-st--rep', 'Reported by a single source. Treat as likely, not guaranteed.'],
    UNVERIFIED: ['Unverified', 'amp-st--unv', 'Not yet confirmed by any source we could check.'],
    CONFLICT: ['Conflicting reports', 'amp-st--con', 'Sources disagree. Check in game before you farm.'],
  };
  const st = (s, short) => { const [t, c, tip] = STATUS[s] || STATUS.UNVERIFIED; return `<span class="amp-st ${c}" title="${esc(tip)}">${esc(short ? t.split(' ')[0] : t)}</span>`; };
  const item = id => TRN.data.item(id);
  const mat = id => A().materials.find(m => m.itemId === id);
  const loc = id => A().locations.find(l => l.id === id);
  const tier = id => A().tiers.find(t => t.id === id);
  const weapon = id => A().weapons.find(w => w.id === id);
  const card = id => TRN.img(id ? mat(id)?.card || item(id)?.image : null);
  const thumb = id => TRN.img(id ? mat(id)?.thumb || item(id)?.image : null);   // small icons: art crop without the card label
  const name = id => item(id)?.name || mat(id)?.name || id;
  const rowName = r => r.itemId ? name(r.itemId) : r.label;
  const guideHref = id => `amplification.html#item-${enc(id)}`;

  /* Upgrade selection maths: every chosen upgrade pulls in its prerequisites (transitively); a set is valid only if
     no two members exclude each other. Totals add each upgrade once, so shared prerequisites are never double-counted. */
  function closure(w, ids) {
    const out = new Set(), walk = id => { if (out.has(id)) return; const u = w.upgrades.find(x => x.id === id); if (!u) return; out.add(id); (u.requires || []).forEach(walk); };
    ids.forEach(walk); return out;
  }
  function conflicts(w, set) {
    const bad = [];
    for (const id of set) for (const x of (w.upgrades.find(u => u.id === id)?.excludes || [])) if (set.has(x)) bad.push([id, x]);
    return bad;
  }
  function blockedBy(w, set, candidate) {   // which chosen upgrade would conflict with adding `candidate` (incl. its prereqs)
    const next = closure(w, [...set, candidate]);
    const c = conflicts(w, next);
    return c.length ? c[0].find(id => id !== candidate && set.has(id)) || c[0][0] : null;
  }
  function totals(w, set) {
    const rows = new Map(), add = (itemId, qty, status, why, label, research) => {
      const key = itemId || 'label:' + label;
      const r = rows.get(key) || { itemId, label, qty: 0, statuses: new Set(), why: [], unknown: false, research: true };
      if (qty == null) r.unknown = true; else r.qty += qty;
      if (!research) r.research = false;
      r.statuses.add(status); r.why.push(why); rows.set(key, r);
    };
    const t = tier(w.tier);
    add(t.itemId, 1, t.status || 'UNVERIFIED', 'Activates amplification on this weapon', null, false);
    for (const u of w.upgrades.filter(x => set.has(x.id))) {
      for (const c of u.cost) add(c.itemId, c.qty, c.status, u.name);
      for (const c of (u.research?.cost || [])) add(c.itemId, c.qty, c.status, `${u.research.name} research`, c.label, true);
    }
    const order = ['CONFLICT', 'UNVERIFIED', 'REPORTED', 'CONFIRMED'];
    return [...rows.values()].map(r => ({ ...r, status: order.find(s => r.statuses.has(s)) || 'UNVERIFIED' }));
  }
  TRN.ampMath = { closure, conflicts, blockedBy, totals };   // exposed for tests

  /* ---------------------------------------------------------------- Guide: item detail dialog + filters */
  function detailHtml(id) {
    const m = mat(id), it = item(id); if (!m) return '';
    const f = m.facts || {}, fact = (k, label, fmt = v => esc(v)) => f[k] && f[k].value != null && f[k].value !== ''
      ? `<div><dt>${label}</dt><dd>${fmt(f[k].value)} ${st(f[k].status, true)}</dd></div>` : `<div><dt>${label}</dt><dd><span class="muted">Not verified</span></dd></div>`;
    const uses = A().weapons.flatMap(w => w.upgrades.flatMap(u => [...u.cost.filter(c => c.itemId === id).map(c => ({ w, u, c })),
      ...(u.research?.cost || []).filter(c => c.itemId === id).map(c => ({ w, u, c, research: true }))]));
    const tiersUsing = A().tiers.filter(t => t.itemId === id);
    return `<div class="amp-detail__grid">
      <figure class="amp-detail__art amp-rar-${esc((it?.rarity || 'common').toLowerCase())}"><img src="${card(id)}" alt="${esc(name(id))} illustration"><figcaption>Raider Network illustration · not an in-game render</figcaption></figure>
      <div class="amp-detail__copy">
        <span class="eyebrow">${esc({ activation: 'ACTIVATION MODULE', upgrade: 'UPGRADE MATERIAL', repair: 'REPAIR MATERIAL' }[m.role] || 'MATERIAL')}</span>
        <h2 id="ampDetailTitle">${esc(name(id))}</h2>
        ${m.description ? `<p class="lede">${esc(m.description.value)} ${st(m.description.status, true)}</p>` : ''}
        <p>${esc(m.purpose)}</p>
        <dl class="amp-facts">${fact('rarity', 'Rarity')}${fact('category', 'Category')}${fact('sellValue', 'Sell value', v => TRN.num(v) + ' coins')}${fact('weight', 'Weight')}${fact('stackSize', 'Stack size')}${fact('recycling', 'Recycling')}</dl>
      </div></div>
      <h3>Where to find it</h3>
      <div class="amp-where">${m.locations.length ? m.locations.map(l => `<div class="amp-where__row"><a href="amplification.html#loc-${enc(l.locationId)}" data-close>${esc(loc(l.locationId)?.name || l.locationId)}</a><span>${esc(l.detail || '')}</span>${st(l.status)}</div>`).join('')
        : '<p class="muted">Location being verified. No source we checked names a reliable source yet.</p>'}</div>
      <h3>What uses it</h3>
      ${tiersUsing.length ? `<p>Activates amplification on ${tiersUsing.map(t => `${esc(t.weaponRarity)} weapons (${t.weapons.map(w => esc(weapon(w).name)).join(', ')})`).join('; ')}.</p>` : ''}
      ${uses.length ? `<div class="amp-uses">${uses.map(({ w, u, c, research }) => `<a class="amp-uses__row" href="amplification/hunt.html?weapon=${enc(w.id)}&upgrade=${enc(u.id)}"><strong>${esc(w.name)}</strong><span>${esc(u.name)}${research ? ' (research)' : ''}</span><b>${c.qty == null ? '?' : '×' + c.qty}</b>${st(c.status, true)}</a>`).join('')}</div>`
        : (tiersUsing.length ? '' : `<p class="muted">${esc(m.usesNote || 'No amplified-weapon upgrade in our data uses this material.')}</p>`)}
      ${m.notes?.length ? `<ul class="amp-notes">${m.notes.map(n => `<li>${esc(n.text)} ${st(n.status, true)}</li>`).join('')}</ul>` : ''}
      <div class="btn-row amp-detail__actions">
        <a class="btn btn-primary" href="hunts.html?new=${enc(id)}">${TRN.icon('squad')} Start a Loot Hunt</a>
        <a class="btn btn-ghost" href="trails.html?item=${enc(id)}">${TRN.icon('route')} Add to Loot Trail</a>
        <a class="btn btn-ghost" href="item.html?id=${enc(id)}">${TRN.icon('loot-intel')} Loot Intel entry</a>
      </div>`;
  }
  function setupGuide() {
    const dlg = $('#ampDetail'), body = $('#ampDetailBody'), page = [$('main > .amp-hero'), $('.amp-toc'), $('.amp-shell'), $('#siteHeader'), $('#siteFooter')].filter(Boolean);
    let opener = null;
    const open = (id, push = true) => {
      if (!mat(id)) return; opener = document.activeElement; body.innerHTML = detailHtml(id);
      dlg.classList.remove('hidden'); document.body.classList.add('amp-modal-open'); page.forEach(el => el.setAttribute('inert', ''));
      if (push) history.replaceState(null, '', '#item-' + id);
      $('.modal-close', dlg).focus();
    };
    const close = () => {
      if (dlg.classList.contains('hidden')) return;
      dlg.classList.add('hidden'); document.body.classList.remove('amp-modal-open'); page.forEach(el => el.removeAttribute('inert'));
      if (location.hash.startsWith('#item-')) history.replaceState(null, '', '#library');
      opener?.focus?.({ preventScroll: true }); opener = null;
    };
    $$('[data-amp-item]').forEach(b => b.addEventListener('click', e => { if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return; e.preventDefault(); open(b.dataset.ampItem); }));
    dlg.addEventListener('click', e => { if (e.target === dlg || e.target.closest('[data-close]') || e.target.closest('.modal-close')) close(); });
    document.addEventListener('keydown', e => {
      if (dlg.classList.contains('hidden')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'Tab') {   // keep focus inside the dialog
        const f = $$('a[href],button:not([disabled])', dlg); if (!f.length) return;
        if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
      }
    });
    const fromHash = () => { const m = location.hash.match(/^#item-(.+)$/); if (!m) { close(); return; } let id; try { id = decodeURIComponent(m[1]); } catch { return; } open(id, false); };
    addEventListener('hashchange', fromHash);
    /* library filters */
    const q = $('#ampSearch'), role = $('#ampRole'), cards = $$('.amp-lib__card');
    const apply = () => {
      const s = (q.value || '').trim().toLowerCase(); let n = 0;
      cards.forEach(c => { const ok = (!s || c.dataset.search.includes(s)) && (!role.value || c.dataset.role === role.value); c.classList.toggle('hidden', !ok); n += ok; });
      $('#ampLibCount').textContent = n; $('#ampLibEmpty').classList.toggle('hidden', n > 0);
    };
    q?.addEventListener('input', apply); role?.addEventListener('change', apply);
    /* section nav highlight */
    const links = $$('.amp-toc a'), secs = links.map(a => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
    if ('IntersectionObserver' in window && secs.length) {
      const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id)); }), { rootMargin: '-40% 0px -55% 0px' });
      secs.forEach(s => io.observe(s));
    }
    fromHash();
  }

  /* ---------------------------------------------------------------- Hunt: weapon -> upgrades -> checklist -> where -> act */
  function setupHunt() {
    const root = $('#ampHuntRoot'); if (!root) return;
    const S = { weapon: null, chosen: new Set() };
    const params = new URLSearchParams(location.search);

    function weaponGrid() {
      return A().tiers.map(t => `<section class="amp-tierrow" aria-label="${esc(t.name)}"><header><img src="${thumb(t.itemId)}" alt="" class="amp-tierrow__mod amp-mod-${esc(t.id)}"><div><strong>${esc(t.short)}</strong><small>${esc(t.weaponRarity)} weapons</small></div></header>
        <div class="amp-wgrid">${t.weapons.map(wid => { const w = weapon(wid), it = item(w.itemId); return `<button type="button" class="amp-wbtn ${S.weapon?.id === wid ? 'on' : ''}" data-weapon="${esc(wid)}" aria-pressed="${S.weapon?.id === wid}">
          <img src="${TRN.img(it?.image)}" alt=""><span><strong>${esc(w.name)}</strong><small>${esc(it?.category || '')}</small></span></button>`; }).join('')}</div></section>`).join('');
    }
    function upgradesHtml(w) {
      return `<div class="amp-ups">${w.upgrades.map(u => {
        const on = S.chosen.has(u.id), auto = !on && closure(w, [...S.chosen]).has(u.id), block = !on && !auto ? blockedBy(w, S.chosen, u.id) : null;
        const req = (u.requires || []).map(r => w.upgrades.find(x => x.id === r)?.name).filter(Boolean), exc = (u.excludes || []).map(r => w.upgrades.find(x => x.id === r)?.name).filter(Boolean);
        return `<label class="amp-up ${on ? 'on' : ''} ${auto ? 'auto' : ''} ${block ? 'blocked' : ''}">
          <input type="checkbox" data-up="${esc(u.id)}" ${on || auto ? 'checked' : ''} ${auto || block ? 'disabled' : ''}>
          <span class="amp-up__body"><strong>${esc(u.name)}</strong>
            <small>${u.effect?.text ? esc(u.effect.text) : '<span class="muted">Effect not yet documented by a source we could check.</span>'} ${u.effect?.text ? st(u.effect.status, true) : ''}</small>
            <span class="amp-up__cost">${u.cost.map(c => `<span><img src="${thumb(c.itemId)}" alt="">${c.qty == null ? '?' : '×' + c.qty} ${esc(name(c.itemId))} ${st(c.status, true)}</span>`).join('') || '<span class="muted">Material cost not documented</span>'}</span>
            ${req.length ? `<em class="amp-up__req">Requires: ${req.map(esc).join(', ')}</em>` : ''}${exc.length ? `<em class="amp-up__exc">Excludes: ${exc.map(esc).join(', ')}</em>` : ''}
            ${auto ? '<em class="amp-up__auto">Included as a prerequisite</em>' : ''}${block ? `<em class="amp-up__blk">Not compatible with ${esc(w.upgrades.find(x => x.id === block)?.name || '')}</em>` : ''}</span></label>`;
      }).join('')}</div>${w.treeNote ? `<p class="small-note">${esc(w.treeNote.text)} ${st(w.treeNote.status, true)}</p>` : ''}`;
    }
    function checklistHtml(w) {
      const set = closure(w, [...S.chosen]); const rows = totals(w, set);
      const row = r => `<div class="amp-check__row ${r.research ? 'is-research' : ''}"><img src="${thumb(r.itemId)}" alt=""><div><strong>${r.itemId ? `<a href="${r.research ? 'item.html?id=' + enc(r.itemId) : guideHref(r.itemId)}">${esc(rowName(r))}</a>` : esc(rowName(r))}</strong><small>${esc([...new Set(r.why)].join(' · '))}</small></div>
          <b class="amp-check__qty">${r.unknown ? (r.qty ? '≥' + r.qty : '?') : '×' + r.qty}</b>${st(r.status)}</div>`;
      const projects = w.upgrades.filter(u => set.has(u.id) && u.research?.name);
      return `<h3 class="amp-check__h">Amplification materials</h3><div class="amp-check">${rows.filter(r => !r.research).map(row).join('')}</div>
        ${rows.some(r => r.research) ? `<h3 class="amp-check__h">Research parts <small>(ARC parts from the Loot Intel catalog)</small></h3><div class="amp-check">${rows.filter(r => r.research).map(row).join('')}</div>` : ''}
        ${projects.length ? `<p class="small-note">${projects.length} research project${projects.length > 1 ? 's' : ''}: ${projects.map(u => esc(u.research.name)).join(', ')}. Each is reported to cost 5,000 research points plus a task. Whether research is shared between weapons is not verified.</p>` : ''}
        ${set.size ? '' : '<p class="small-note">Pick one or more upgrades above to add their materials. The module alone activates amplification.</p>'}
        ${rows.some(r => r.status !== 'CONFIRMED') ? '<p class="small-note amp-warn">Some quantities are not confirmed yet (shown as Community-reported, Unverified or Conflicting). Check the upgrade screen in game before farming.</p>' : ''}`;
    }
    function whereHtml(w) {
      const rows = totals(w, closure(w, [...S.chosen])).filter(r => !r.research);
      return `<div class="amp-hw">${rows.map(r => { const m = mat(r.itemId); return `<article class="amp-hw__card"><header><img src="${thumb(r.itemId)}" alt=""><div><strong>${esc(name(r.itemId))}</strong><small>${esc(m?.purpose || '')}</small></div></header>
          ${m?.locations.length ? `<ul>${m.locations.map(l => `<li><span>${esc(loc(l.locationId)?.name || l.locationId)}</span><small>${esc(l.detail || '')}</small>${st(l.status, true)}</li>`).join('')}</ul>` : '<p class="muted">Location being verified.</p>'}
          <div class="amp-hw__foot"><a class="text-btn" href="${guideHref(r.itemId)}">Guide details</a><a class="text-btn" href="hunts.html?new=${enc(r.itemId)}">Start a Loot Hunt</a><a class="text-btn" href="trails.html?item=${enc(r.itemId)}">Add to Loot Trail</a></div></article>`; }).join('')}</div>`;
    }
    function actionsHtml(w) {
      const rows = totals(w, closure(w, [...S.chosen])).filter(r => r.itemId);
      const first = rows.find(r => r.itemId !== tier(w.tier).itemId) || rows[0];
      return `<div class="amp-act">
        <label class="amp-act__pick">Material to hunt<select class="input" id="ampHuntMat"><optgroup label="Amplification materials">${rows.filter(r => !r.research).map(r => `<option value="${esc(r.itemId)}" ${r === first ? 'selected' : ''}>${esc(name(r.itemId))}${r.unknown ? '' : ' (×' + r.qty + ')'}</option>`).join('')}</optgroup>${rows.some(r => r.research) ? `<optgroup label="Research parts">${rows.filter(r => r.research).map(r => `<option value="${esc(r.itemId)}">${esc(name(r.itemId))}${r.unknown ? '' : ' (×' + r.qty + ')'}</option>`).join('')}</optgroup>` : ''}</select></label>
        <a class="btn btn-primary btn-lg" id="ampStartHunt" href="hunts.html?new=${enc(first.itemId)}">${TRN.icon('squad')} Start Loot Hunt</a>
        <a class="btn btn-lg btn-amp-trail" id="ampAddTrail" href="trails.html?item=${enc(first.itemId)}">${TRN.icon('route')} Add to Loot Trail</a>
        <p class="small-note">Start Loot Hunt opens the usual Loot Hunt form with this material filled in. Add to Loot Trail lets you pick one of your trails (or start one) and fills it into the discovery form. Loot Trails need you to be logged in.</p></div>`;
    }
    function paint() {
      const w = S.weapon;
      root.innerHTML = `
        <section class="panel amp-step" id="step-weapon"><header class="panel-head"><span class="amp-stepn">1</span><h2>Choose a weapon</h2><span class="muted">Amplification needs the weapon at tier IV and the matching module.</span></header>${weaponGrid()}</section>
        ${w ? `<section class="panel amp-step" id="step-upgrade"><header class="panel-head"><span class="amp-stepn">2</span><h2>Choose upgrades for ${esc(w.name)}</h2><span class="chip-row">${st(w.status || 'REPORTED')}<a class="text-btn" href="amplification.html#upgrades">How branches work</a></span></header>${upgradesHtml(w)}</section>
        <section class="panel amp-step" id="step-materials"><header class="panel-head"><span class="amp-stepn">3</span><h2>Materials checklist</h2></header>${checklistHtml(w)}</section>
        <section class="panel amp-step" id="step-where"><header class="panel-head"><span class="amp-stepn">4</span><h2>Where to hunt</h2><a class="text-btn" href="amplification.html#farming">All farming locations</a></header>${whereHtml(w)}</section>
        <section class="panel amp-step amp-step--go" id="step-go"><header class="panel-head"><span class="amp-stepn">5</span><h2>Start hunting</h2></header>${actionsHtml(w)}</section>`
        : '<p class="empty-note pad">Pick a weapon to see its amplification upgrades and the materials to hunt.</p>'}`;
      $$('[data-weapon]', root).forEach(b => b.onclick = () => { S.weapon = weapon(b.dataset.weapon); S.chosen = new Set(); sync(); paint(); $('#step-upgrade')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); });
      $$('[data-up]', root).forEach(c => c.onchange = () => {
        if (c.checked) S.chosen.add(c.dataset.up); else S.chosen.delete(c.dataset.up);
        // drop explicit picks that became prerequisites of something else (they stay included automatically)
        sync(); paint(); $(`[data-up="${CSS.escape(c.dataset.up)}"]`, root)?.focus();
      });
      const sel = $('#ampHuntMat');
      if (sel) sel.onchange = () => { $('#ampStartHunt').href = 'hunts.html?new=' + enc(sel.value); $('#ampAddTrail').href = 'trails.html?item=' + enc(sel.value); };
    }
    function sync() {
      const p = new URLSearchParams();
      if (S.weapon) p.set('weapon', S.weapon.id);
      if (S.chosen.size) p.set('upgrade', [...S.chosen].join(','));
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
    }
    // deep links: ?weapon=&upgrade=a,b  or  ?material=<itemId> (pre-selects the first weapon that needs it)
    if (params.get('weapon') && weapon(params.get('weapon'))) {
      S.weapon = weapon(params.get('weapon'));
      for (const u of (params.get('upgrade') || '').split(',').filter(Boolean)) if (S.weapon.upgrades.some(x => x.id === u) && !blockedBy(S.weapon, S.chosen, u)) S.chosen.add(u);
    } else if (params.get('material')) {
      const m = params.get('material');
      const hit = A().weapons.find(w => tier(w.tier).itemId === m || w.upgrades.some(u => u.cost.some(c => c.itemId === m)));
      if (hit) { S.weapon = hit; const u = hit.upgrades.find(x => x.cost.some(c => c.itemId === m)); if (u && !blockedBy(hit, S.chosen, u.id)) S.chosen.add(u.id); }
    }
    paint();
  }

  TRN.amp = { setupGuide, setupHunt, detailHtml };
})();
