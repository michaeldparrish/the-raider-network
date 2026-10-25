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
  function totals(w, set, { includeModule = true } = {}) {
    const rows = new Map(), add = (itemId, qty, status, why, label, research) => {
      const key = itemId || 'label:' + label;
      const r = rows.get(key) || { itemId, label, qty: 0, statuses: new Set(), why: [], unknown: false, research: true };
      if (qty == null) r.unknown = true; else r.qty += qty;
      if (!research) r.research = false;
      r.statuses.add(status); r.why.push(why); rows.set(key, r);
    };
    const t = tier(w.tier);
    if (includeModule) add(t.itemId, 1, t.status || 'UNVERIFIED', 'Activates amplification on this weapon', null, false);
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

  /* ---------------------------------------------------------------- Hunt: weapon -> already amplified? -> enhancements -> review -> track
     The plan here is only a draft in the page. "Track in a Loot Trail" sends weapon + answer + enhancements (+ what you
     already have) and the server recalculates every quantity; "Post a Quick Hunt" hands one multi-material post to the
     existing Loot Hunt popup. */
  const QTY_MAX = 999;
  const encPlan = o => btoa(unescape(encodeURIComponent(JSON.stringify(o)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  function setupHunt() {
    const root = $('#ampHuntRoot'); if (!root) return;
    const S = { weapon: null, amplified: null, chosen: new Set(), have: {}, skip: new Set(), track: null };
    const params = new URLSearchParams(location.search);
    const smooth = () => (matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth');
    const rowsNow = () => S.weapon ? totals(S.weapon, closure(S.weapon, [...S.chosen]), { includeModule: S.amplified === false }) : [];
    const keyOf = r => r.itemId || 'label:' + r.label;
    const outstanding = r => r.unknown && !r.qty ? null : Math.max(0, r.qty - (S.have[keyOf(r)] || 0));
    const selected = () => rowsNow().filter(r => r.itemId && !S.skip.has(keyOf(r)));

    function weaponGrid() {
      return A().tiers.map(t => `<section class="amp-tierrow" aria-label="${esc(t.name)}"><header><img src="${thumb(t.itemId)}" alt="" class="amp-tierrow__mod amp-mod-${esc(t.id)}"><div><strong>${esc(t.short)}</strong><small>${esc(t.weaponRarity)} weapons</small></div></header>
        <div class="amp-wgrid">${t.weapons.map(wid => { const w = weapon(wid), it = item(w.itemId); return `<button type="button" class="amp-wbtn ${S.weapon?.id === wid ? 'on' : ''}" data-weapon="${esc(wid)}" aria-pressed="${S.weapon?.id === wid}">
          <img src="${TRN.img(it?.image)}" alt=""><span><strong>${esc(w.name)}</strong><small>${esc(it?.category || '')}</small></span></button>`; }).join('')}</div></section>`).join('');
    }
    function amplifiedHtml(w) {
      const t = tier(w.tier);
      return `<div class="amp-ask" role="radiogroup" aria-label="Is your ${esc(w.name)} already amplified?">
        <button type="button" role="radio" aria-checked="${S.amplified === false}" class="amp-ask__opt ${S.amplified === false ? 'on' : ''}" data-amp="no">
          <img src="${thumb(t.itemId)}" alt=""><span><strong>No — I am starting amplification</strong><small>Adds 1 × ${esc(t.name)} to your plan as the activation step.</small></span></button>
        <button type="button" role="radio" aria-checked="${S.amplified === true}" class="amp-ask__opt ${S.amplified === true ? 'on' : ''}" data-amp="yes">
          <span class="amp-ask__done" aria-hidden="true">${TRN.svg('check')}</span><span><strong>Yes — my weapon is already amplified</strong><small>The module is left out; plan your enhancements only.</small></span></button></div>`;
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
    const qtyTxt = (q, unknown) => unknown ? (q ? '≥' + q : '?') : '×' + q;
    const line = (key, img, label, q, unknown, status, sub) => `<div class="amp-pl__row"><img src="${img}" alt=""><span><strong>${label}</strong>${sub ? `<small>${sub}</small>` : ''}</span><b>${qtyTxt(q, unknown)}</b>${st(status, true)}</div>`;
    function reviewHtml(w) {
      const set = closure(w, [...S.chosen]), t = tier(w.tier), rows = rowsNow();
      const ups = w.upgrades.filter(u => set.has(u.id));
      const act = S.amplified === false ? `<section class="amp-pl" id="planActivation"><h3><span class="amp-pl__n">1</span>Initial amplification</h3>
          ${line(t.itemId, thumb(t.itemId), esc(t.name), 1, false, t.status, `Activates amplification on your tier IV ${esc(w.name)}`)}</section>`
        : `<section class="amp-pl amp-pl--skip" id="planActivation"><h3><span class="amp-pl__n">1</span>Initial amplification</h3><p class="muted">Not needed — your ${esc(w.name)} is already amplified.</p></section>`;
      const enh = `<section class="amp-pl" id="planEnhancements"><h3><span class="amp-pl__n">2</span>Selected enhancements</h3>${ups.length ? ups.map(u => `<div class="amp-pl__enh"><header><strong>${esc(u.name)}</strong>${S.chosen.has(u.id) ? '' : '<em class="amp-up__auto">prerequisite</em>'}</header>
          ${u.cost.map(c => line(c.itemId, thumb(c.itemId), esc(name(c.itemId)), c.qty, c.qty == null, c.status, 'Install cost')).join('')}
          ${(u.research?.cost || []).map(c => line(c.itemId, thumb(c.itemId), esc(c.itemId ? name(c.itemId) : c.label), c.qty, c.qty == null, c.status, `${esc(u.research.name)} research`)).join('')}</div>`).join('')
          : '<p class="muted">No enhancements chosen yet. Pick them in step 3, or plan the activation only.</p>'}</section>`;
      const sel = selected().length, all = rows.filter(r => r.itemId).length;
      const combo = `<section class="amp-pl" id="planCombined"><h3><span class="amp-pl__n">3</span>Combined materials</h3>
        <div class="amp-pl__tools"><button type="button" class="text-btn" id="ampSelAll">Select all</button><button type="button" class="text-btn" id="ampSelNone">Select none</button><span class="muted" id="ampSelCount">${sel} of ${all} selected for hunting</span></div>
        <div class="amp-table-wrap"><table class="amp-table amp-combined"><thead><tr><th scope="col"><span class="sr-only">Hunt</span></th><th scope="col">Material</th><th scope="col">Needed</th><th scope="col">I have</th><th scope="col">Still to hunt</th><th scope="col">Status</th></tr></thead><tbody>
        ${rows.map(r => { const k = keyOf(r), o = outstanding(r), dis = !r.itemId; return `<tr class="${r.research ? 'is-research' : ''} ${S.skip.has(k) || dis ? 'is-skipped' : ''}" data-row="${esc(k)}">
          <td><input type="checkbox" aria-label="Hunt ${esc(rowName(r))}" data-sel="${esc(k)}" ${!S.skip.has(k) && !dis ? 'checked' : ''} ${dis ? 'disabled' : ''}></td>
          <th scope="row"><span class="amp-cm"><img src="${thumb(r.itemId)}" alt=""><span><strong>${r.itemId ? `<a href="${r.research ? 'item.html?id=' + enc(r.itemId) : guideHref(r.itemId)}">${esc(rowName(r))}</a>` : esc(rowName(r))}</strong><small>${esc([...new Set(r.why)].join(' · '))}</small></span></span></th>
          <td class="amp-cm__q">${qtyTxt(r.qty, r.unknown)}</td>
          <td>${dis ? '<span class="muted">—</span>' : `<input class="input amp-have" type="number" inputmode="numeric" min="0" max="${QTY_MAX}" step="1" value="${S.have[k] || 0}" data-have="${esc(k)}" aria-label="How many ${esc(rowName(r))} you already have">`}</td>
          <td class="amp-cm__o" data-out="${esc(k)}">${o == null ? '?' : o === 0 ? '<span class="amp-done">Done</span>' : '×' + o}</td>
          <td>${st(r.status, true)}</td></tr>`; }).join('')}</tbody></table></div>
        ${rows.some(r => r.status !== 'CONFIRMED') ? '<p class="small-note amp-warn">Some quantities are not confirmed yet (Community-reported, Unverified or Conflicting). Check the upgrade screen in game before farming.</p>' : ''}
        ${ups.some(u => u.research?.name) ? `<p class="small-note">Research projects: ${ups.filter(u => u.research?.name).map(u => esc(u.research.name)).join(', ')}. Each is reported to cost 5,000 research points plus a task. Whether research is shared between weapons is not verified.</p>` : ''}</section>`;
      return act + enh + combo + `<details class="amp-pl__where" id="step-where"><summary>Where to hunt these materials</summary>${whereHtml(w)}</details>`;
    }
    function whereHtml(w) {
      const rows = rowsNow().filter(r => !r.research && r.itemId);
      return `<div class="amp-hw">${rows.map(r => { const m = mat(r.itemId); return `<article class="amp-hw__card"><header><img src="${thumb(r.itemId)}" alt=""><div><strong>${esc(name(r.itemId))}</strong><small>${esc(m?.purpose || '')}</small></div></header>
          ${m?.locations.length ? `<ul>${m.locations.map(l => `<li><span>${esc(loc(l.locationId)?.name || l.locationId)}</span><small>${esc(l.detail || '')}</small>${st(l.status, true)}</li>`).join('')}</ul>` : '<p class="muted">Location being verified.</p>'}
          <div class="amp-hw__foot"><a class="text-btn" href="${guideHref(r.itemId)}">Guide details</a></div></article>`; }).join('')}</div><p class="small-note"><a class="text-btn" href="amplification.html#farming">All farming locations</a></p>`;
    }
    function trackHtml(w) {
      const sel = selected();
      const single = rowsNow().filter(r => r.itemId);
      const first = single.find(r => r.itemId !== tier(w.tier).itemId) || single[0];
      return `<div class="amp-track">
        <button type="button" class="btn btn-primary btn-lg amp-track__go" id="ampTrackGo" ${sel.length ? '' : 'disabled'}>${TRN.icon('route')} Start Hunt for Selected Materials <b>(${sel.length})</b></button>
        <div class="amp-track__choice ${S.track ? '' : 'hidden'}" id="ampTrackChoice">
          <article class="amp-track__opt amp-track__opt--trail"><h3>${TRN.icon('route')} Track in a Loot Trail <em class="new-tag">RECOMMENDED</em></h3>
            <p>Saves the weapon, your activation answer, the enhancements, every quantity and what you already have. Your squad can join the same build, and each Raider tracks their own progress.</p>
            <div id="ampTrailPick" class="amp-track__trail"><p class="muted">Checking your Loot Trails…</p></div></article>
          <article class="amp-track__opt"><h3>${TRN.icon('squad')} Post a Quick Hunt</h3>
            <p>One Loot Hunt post listing the <b id="ampQuickCount">${sel.length} selected material${sel.length === 1 ? '' : 's'}</b> and the build, so Raiders can squad up. Quick Hunts are still saved in this browser only.</p>
            ${quickHref(w) ? `<a class="btn btn-ghost" id="ampQuickPlan" href="${quickHref(w)}">Post a Quick Hunt</a>` : '<a class="btn btn-ghost is-disabled" id="ampQuickPlan" aria-disabled="true">Post a Quick Hunt</a>'}
            <small class="muted">Materials you already have enough of are left out of the post.</small></article>
        </div>
        <details class="amp-track__single"><summary>Hunt a single material instead</summary>
          <div class="amp-act"><label class="amp-act__pick">Material to hunt<select class="input" id="ampHuntMat">${single.map(r => `<option value="${esc(r.itemId)}" ${r === first ? 'selected' : ''}>${esc(name(r.itemId))}${r.unknown ? '' : ' (×' + r.qty + ')'}</option>`).join('')}</select></label>
            <a class="btn btn-ghost" id="ampStartHunt" href="hunts.html?new=${enc(first?.itemId || '')}">${TRN.icon('squad')} Start Loot Hunt</a>
            <a class="btn btn-amp-trail" id="ampAddTrail" href="trails.html?item=${enc(first?.itemId || '')}">${TRN.icon('route')} Add to Loot Trail</a></div></details></div>`;
    }
    async function trailPicker() {
      const host = $('#ampTrailPick'); if (!host) return;
      const w = S.weapon;
      if (TRN.mode !== 'server') { host.innerHTML = '<p class="notice-bar">Loot Trails need the live server, so they are not available in local demo mode.</p>'; return; }
      const u = await TRN.auth.currentUser();
      if (!u) { host.innerHTML = `<a class="btn btn-primary" href="auth.html?next=${enc(location.pathname.replace(/^\//, '') + location.search)}#login">Log in to track this plan</a>`; return; }
      let trails = [];
      try { trails = (await TRN.api.get('/trails')).trails.filter(t => t.status === 'ACTIVE'); } catch (e) { host.innerHTML = `<p class="form-note">${esc(e.message)}</p>`; return; }
      const maps = TRN.db.maps.filter(m => m.status === 'live');
      host.innerHTML = `<form id="ampTrailForm" class="stack-sm">
        <label>Loot Trail<select class="input" name="trail">${trails.map(t => `<option value="${esc(t.id)}">${esc(t.title)} · ${esc(TRN.data.mapName(t.mapId))}${t.myRole === 'OWNER' ? '' : ' (joined)'}</option>`).join('')}<option value="__new" ${trails.length ? '' : 'selected'}>+ Start a new Loot Trail</option></select></label>
        <div class="amp-track__new ${trails.length ? 'hidden' : ''}"><label>Trail name<input class="input" name="title" maxlength="100" value="${esc(w.name + ' amplification')}"></label>
          <label>Map for discovery pins<select class="input" name="mapId">${maps.map(m => `<option value="${esc(m.id)}" ${m.id === 'pendola-pass' ? 'selected' : ''}>${esc(m.name)}</option>`).join('')}</select></label>
          <p class="small-note">The map is only used for pinning discoveries. You can add more weapon plans to the same trail later.</p></div>
        <button class="btn btn-primary" type="submit">Save plan to Loot Trail</button><p class="form-note" role="status" id="ampTrailMsg"></p></form>`;
      const f = $('#ampTrailForm');
      f.elements.trail.onchange = () => $('.amp-track__new', f).classList.toggle('hidden', f.elements.trail.value !== '__new');
      f.onsubmit = async e => {
        e.preventDefault(); const msg = $('#ampTrailMsg'), btn = $('button[type=submit]', f); btn.disabled = true; msg.textContent = 'Saving your plan…';
        try {
          let trailId = f.elements.trail.value;
          if (trailId === '__new') trailId = (await TRN.api.post('/trails', { title: String(f.elements.title.value || '').trim() || w.name + ' amplification', description: '', mapId: f.elements.mapId.value })).trail.id;
          const rows = rowsNow(), had = {}, hunting = {};
          for (const r of rows) { const k = keyOf(r); if (S.have[k]) had[k] = S.have[k]; if (S.skip.has(k)) hunting[k] = false; }
          const d = await TRN.api.post(`/trails/${enc(trailId)}/plans`, { weaponId: w.id, alreadyAmplified: !!S.amplified, enhancements: [...S.chosen], had, hunting });
          location.href = `trails.html?id=${enc(trailId)}#plan-${enc(d.plan.id)}`;
        } catch (err) { msg.textContent = err.message; btn.disabled = false; }
      };
    }
    function paint() {
      const w = S.weapon, answered = S.amplified !== null;
      root.innerHTML = `
        <section class="panel amp-step" id="step-weapon"><header class="panel-head"><span class="amp-stepn">1</span><h2>Select the weapon</h2><span class="muted">Amplification needs the weapon at tier IV.</span></header>${weaponGrid()}</section>
        ${w ? `<section class="panel amp-step" id="step-amplified"><header class="panel-head"><span class="amp-stepn">2</span><h2>Is your ${esc(w.name)} already amplified?</h2></header>${amplifiedHtml(w)}</section>` : '<p class="empty-note pad">Pick a weapon to plan its amplification.</p>'}
        ${w && answered ? `<section class="panel amp-step" id="step-upgrade"><header class="panel-head"><span class="amp-stepn">3</span><h2>Choose enhancements</h2><span class="chip-row">${st(w.status || 'REPORTED')}<a class="text-btn" href="amplification.html#branches">How branches work</a></span></header>${upgradesHtml(w)}</section>
        <section class="panel amp-step" id="step-materials"><header class="panel-head"><span class="amp-stepn">4</span><h2>Review materials</h2></header>${reviewHtml(w)}</section>
        <section class="panel amp-step amp-step--go" id="step-go"><header class="panel-head"><span class="amp-stepn">5</span><h2>Track the hunt</h2></header>${trackHtml(w)}</section>`
        : (w ? '<p class="empty-note pad">Answer step 2 to choose enhancements and build your plan.</p>' : '')}`;
      $$('[data-weapon]', root).forEach(b => b.onclick = () => { S.weapon = weapon(b.dataset.weapon); S.amplified = null; S.chosen = new Set(); S.have = {}; S.skip = new Set(); S.track = null; sync(); paint(); $('#step-amplified')?.scrollIntoView({ behavior: smooth(), block: 'start' }); });
      $$('[data-amp]', root).forEach(b => b.onclick = () => { const first = S.amplified === null; S.amplified = b.dataset.amp === 'yes'; sync(); paint(); $(`[data-amp="${b.dataset.amp}"]`, root)?.focus(); if (first) $('#step-upgrade')?.scrollIntoView({ behavior: smooth(), block: 'start' }); });
      $$('[data-up]', root).forEach(c => c.onchange = () => { if (c.checked) S.chosen.add(c.dataset.up); else S.chosen.delete(c.dataset.up); sync(); paint(); $(`[data-up="${CSS.escape(c.dataset.up)}"]`, root)?.focus(); });
      $$('[data-sel]', root).forEach(c => c.onchange = () => { if (c.checked) S.skip.delete(c.dataset.sel); else S.skip.add(c.dataset.sel); paintTrack(); c.closest('tr').classList.toggle('is-skipped', !c.checked); });
      $$('[data-have]', root).forEach(inp => inp.oninput = () => {
        const v = Math.max(0, Math.min(QTY_MAX, Math.floor(Number(inp.value) || 0))); S.have[inp.dataset.have] = v;
        const r = rowsNow().find(x => keyOf(x) === inp.dataset.have), o = outstanding(r), cell = $(`[data-out="${CSS.escape(inp.dataset.have)}"]`, root);
        if (cell) cell.innerHTML = o == null ? '?' : o === 0 ? '<span class="amp-done">Done</span>' : '×' + o;
        paintTrack();
      });
      $('#ampSelAll') && ($('#ampSelAll').onclick = () => { S.skip = new Set(); paint(); $('#ampSelAll')?.focus(); });
      $('#ampSelNone') && ($('#ampSelNone').onclick = () => { S.skip = new Set(rowsNow().map(keyOf)); paint(); $('#ampSelNone')?.focus(); });
      wireTrack();
    }
    function quickHref(w) {
      // only what is still to hunt: rows you already have enough of are left out; unknown quantities post as their known part (or 1)
      const items = selected().map(r => [r, outstanding(r)]).filter(([, o]) => o !== 0).map(([r, o]) => [r.itemId, Math.max(1, Math.min(QTY_MAX, o ?? (r.qty || 1)))]);
      return items.length ? 'hunts.html?plan=' + encPlan({ w: w.id, a: !!S.amplified, e: [...S.chosen], i: items }) : null;
    }
    function paintTrack() {   // update step 5 in place (count, button state, Quick Hunt payload); the trail form keeps its state
      if (!S.weapon) return;
      const sel = selected().length, all = rowsNow().filter(r => r.itemId).length;
      const go = $('#ampTrackGo'); if (go) { go.disabled = !sel; $('b', go).textContent = `(${sel})`; }
      const q = $('#ampQuickPlan'), qh = quickHref(S.weapon);
      if (q) { if (qh) { q.href = qh; q.removeAttribute('aria-disabled'); q.classList.remove('is-disabled'); } else { q.removeAttribute('href'); q.setAttribute('aria-disabled', 'true'); q.classList.add('is-disabled'); } }
      const n = $('#ampQuickCount'); if (n) n.textContent = `${sel} selected material${sel === 1 ? '' : 's'}`;
      if ($('#ampSelCount')) $('#ampSelCount').textContent = `${sel} of ${all} selected for hunting`;
    }
    function wireTrack() {
      const go = $('#ampTrackGo');
      if (go) go.onclick = () => { S.track = 'open'; $('#ampTrackChoice').classList.remove('hidden'); trailPicker(); $('#ampTrackChoice').scrollIntoView({ behavior: smooth(), block: 'nearest' }); };
      const sel = $('#ampHuntMat');
      if (sel) sel.onchange = () => { $('#ampStartHunt').href = 'hunts.html?new=' + enc(sel.value); $('#ampAddTrail').href = 'trails.html?item=' + enc(sel.value); };
    }
    function sync() {
      const p = new URLSearchParams();
      if (S.weapon) p.set('weapon', S.weapon.id);
      if (S.amplified !== null) p.set('amplified', S.amplified ? 'yes' : 'no');
      if (S.chosen.size) p.set('upgrade', [...S.chosen].join(','));
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
    }
    // deep links: ?weapon=&amplified=yes|no&upgrade=a,b  or  ?material=<itemId> (opens the first weapon whose build uses it)
    if (params.get('weapon') && weapon(params.get('weapon'))) {
      S.weapon = weapon(params.get('weapon'));
      for (const u of (params.get('upgrade') || '').split(',').filter(Boolean)) if (S.weapon.upgrades.some(x => x.id === u) && !blockedBy(S.weapon, S.chosen, u)) S.chosen.add(u);
    } else if (params.get('material')) {
      const m = params.get('material');
      const hit = A().weapons.find(w => tier(w.tier).itemId === m || w.upgrades.some(u => u.cost.some(c => c.itemId === m)));
      if (hit) { S.weapon = hit; if (tier(hit.tier).itemId === m) S.amplified = false; const u = hit.upgrades.find(x => x.cost.some(c => c.itemId === m)); if (u && !blockedBy(hit, S.chosen, u.id)) S.chosen.add(u.id); }
    }
    if (S.weapon && ['yes', 'no'].includes(params.get('amplified'))) S.amplified = params.get('amplified') === 'yes';
    paint();
  }

  TRN.amp = { setupGuide, setupHunt, detailHtml, encPlan };
})();
