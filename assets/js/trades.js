/* The Raider Network v6 — Trade Board. Item references use shared Loot Intel item IDs.
 * SERVER mode: posts, edits, status changes, deletes and offers go to /api (Cloudflare D1). Ownership is enforced
 *   by the server; the owner controls shown here are only a convenience.
 * DEMO mode (local development): v5 browser-only listings, including the Perisher trade-inventory safeguards
 *   (reservations + completed trades can never exceed what the Raider owns). No payments, no real money. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  let ALL = [];                                  // latest trade list, used to compute inventory reservations
  let MY_OFFERS = new Map();                     // server mode: tradeId -> my pending offer
  const srv = () => TRN.mode === 'server';
  const prep = rows => { ALL = rows || []; return ALL; };
  const inv = userId => TRN.store.inventory(userId, ALL);
  const itemsTxt = (list, fallback) => list.length ? list.map(x => `${TRN.data.itemLink(x.itemId, x.name)}${x.quantity > 1 ? ` <b>×${x.quantity}</b>` : ''}${x.itemId ? '' : ' <em class="unlisted" title="' + esc(x.note || 'Not in the Loot Intel database snapshot') + '">unlisted</em>'}`).join(', ') : fallback;
  const firstItem = t => t.lookingFor.find(x => x.itemId)?.itemId || '';
  /* Consistent placeholder art for blueprints that are not in the item snapshot (no invented IDs). */
  const UNLISTED = new Set(['patina-blueprint', 'silencer-iii-blueprint']);
  const unlistedArt = name => { const k = TRN.slug(name || ''); return TRN.IMG + 'items/db/unlisted-' + (UNLISTED.has(k) ? k : 'blueprint') + '.svg'; };
  const artFor = (itemId, name) => itemId && TRN.data.item(itemId) ? TRN.img(TRN.data.item(itemId).image) : unlistedArt(name);
  const poolChips = (st, compact) => st ? st.items.filter(x => x.available > 0).map(x => `<span class="pool-chip">${esc(x.label)} <b>×${x.available}</b></span>`).join('') || '<span class="muted">All units reserved or traded</span>' : '';

  function offerBlock(t, compact) {
    const st = inv(t.userId);
    const reserved = (t.offering || []).filter(o => o.fromInventory);
    const free = (t.offering || []).filter(o => !o.fromInventory);
    let h = '';
    if (reserved.length) h += `${itemsTxt(reserved, '')} <span class="reserve-tag">RESERVED</span>`;
    if (free.length) h += (h ? '<br>' : '') + itemsTxt(free, '');
    if (st && t.offerFromPool) h += `${h ? '<br>' : ''}<span class="pool-line">${reserved.length ? 'or' : 'Available to offer:'} from ${esc(t.displayName)}'s trade inventory</span>`;
    if (!h) h = t.openToOffers ? '<em class="open-offers">Open to Offers</em>' : '—';
    if (st && t.offerFromPool && !compact) h += `<div class="pool-row">${poolChips(st)}</div>`;
    return h;
  }

  function tradeCard(t, me) {
    const want = TRN.data.item(firstItem(t)), u = TRN.store.publicUser(t.userId), mine = me && (me.user_id || me.id) === t.userId;
    const avatar = t.avatar || u?.avatar, myOffer = MY_OFFERS.get(t.id);
    const search = [t.displayName, ...t.lookingFor.map(x => x.name || TRN.data.itemName(x.itemId)), ...t.offering.map(x => x.name || TRN.data.itemName(x.itemId)), t.region, t.platform, t.notes].join(' ').toLowerCase();
    const wantImg = want ? TRN.img(want.image) : unlistedArt(t.lookingFor[0]?.name);
    const st = mine ? inv(t.userId) : null;
    return `<article class="trade-card trade-${esc(t.status)}" id="${esc(t.id)}" data-search="${esc(search)}" data-region="${esc(t.region)}" data-platform="${esc(t.platform)}" data-status="${esc(t.status)}" data-items="${esc([...t.lookingFor, ...t.offering].map(x => x.itemId).join(' '))}">
      <header class="trade-card__head"><div class="raider-id">${avatar ? `<img class="avatar-img" src="${TRN.IMG + esc(avatar)}" alt="">` : `<span class="avatar">${esc((t.displayName || 'R')[0].toUpperCase())}</span>`}<div><strong>${esc(t.displayName || 'Raider')}</strong><small>${t.username ? `@${esc(t.username)} · ` : ''}${TRN.ageFromIso(t.createdAt)}${t.updatedAt && t.updatedAt !== t.createdAt ? ' · edited' : ''}</small></div></div>${t.awaiting ? '<span class="status-chip status-awaiting">AWAITING EXCHANGE</span>' : TRN.statusChip(t.status)}</header>
      <div class="trade-pair">
        <div class="trade-side want"><img src="${wantImg}" alt=""><div><span>LOOKING FOR</span><strong>${itemsTxt(t.lookingFor, '—')}</strong></div></div>
        <div class="trade-arrow">${TRN.icon('trade')}</div>
        <div class="trade-side have"><div><span>AVAILABLE TO OFFER</span><strong>${offerBlock(t)}</strong></div></div>
      </div>
      <dl class="kv kv-3"><div><dt>${TRN.icon('location')}Region</dt><dd>${esc(t.region)}</dd></div><div><dt>${TRN.icon('settings')}Platform</dt><dd>${esc(t.platform)}</dd></div><div><dt>${TRN.icon('time')}Desired time</dt><dd>${esc(t.desiredTime || 'Flexible')}</dd></div></dl>
      ${t.notes ? `<p>${esc(t.notes)}</p>` : ''}
      <div class="hunt-actions">
        ${srv() && mine ? '' : myOffer ? `<span class="offer-sent">${TRN.svg('check')} Offer sent <button class="btn btn-ghost btn-xs" data-withdraw="${esc(myOffer.id)}">Withdraw</button></span>`
          : `<button class="btn btn-primary trade-respond" ${t.status !== 'open' ? 'disabled' : ''} data-trade="${esc(t.id)}" data-user="${esc(t.userId)}" data-name="${esc(t.displayName)}" data-item="${esc(firstItem(t))}">${TRN.svg('swap')} Respond / Make Offer</button>`}
        ${srv() ? '' : `<button class="btn btn-ghost trade-message" data-trade="${esc(t.id)}" data-user="${esc(t.userId)}" data-name="${esc(t.displayName)}" data-item="${esc(firstItem(t))}">${TRN.svg('message')} Message Raider</button>`}
        ${want ? `<a class="btn btn-ghost" href="item.html?id=${encodeURIComponent(want.id)}">${TRN.icon('loot-intel')} View Item Intel</a>` : ''}
      </div>
      ${srv() && mine ? ownerBarServer(t) : ''}
      ${!srv() && mine && t.status === 'open' ? `<div class="owner-bar"><span>Your listing</span>
        <button class="btn btn-ghost btn-xs" data-traded="${esc(t.id)}">Mark traded…</button><button class="btn btn-ghost btn-xs" data-close="${esc(t.id)}">Close listing</button>
        <form class="traded-form hidden" data-form="${esc(t.id)}"><label>Gave
          <select name="key">${(st?.items || []).map(x => { const resHere = (t.offering || []).filter(o => o.inventoryKey === x.key).reduce((a, o) => a + (o.quantity || 1), 0); const can = x.available + resHere; return `<option value="${esc(x.key)}" ${can ? '' : 'disabled'}>${esc(x.label)} (${can} available)</option>`; }).join('')}<option value="">Nothing from inventory</option></select></label>
          <label>Qty <input name="qty" type="number" min="1" max="2" value="1"></label><button class="btn btn-primary btn-xs">Confirm</button><span class="form-note"></span></form></div>` : ''}
      </article>`;
  }
  /* Owner controls for a server-stored post. The server re-checks ownership on every request. */
  function ownerBarServer(t) {
    const id = esc(t.id);
    if (t.awaiting) return `<div class="owner-bar owner-bar--server"><span>Offer accepted · awaiting the in-game exchange</span>
      <a class="btn btn-primary btn-xs" href="messages.html">View Trade Details</a>
      <button class="btn btn-ghost btn-xs" data-offers="${id}" aria-expanded="false">Offers${t.pendingOffers ? ` <b class="count-pill">${t.pendingOffers}</b>` : ''}</button>
      <div class="offer-panel hidden" data-offers-for="${id}"></div></div>`;
    return `<div class="owner-bar owner-bar--server"><span>Your listing</span>
      ${t.status !== 'completed' ? `<button class="btn btn-ghost btn-xs" data-edit="${id}">Edit</button>` : ''}
      ${t.status === 'open' ? `<button class="btn btn-ghost btn-xs" data-set-status="${id}" data-to="closed">Close</button><button class="btn btn-ghost btn-xs" data-set-status="${id}" data-to="completed">Mark completed</button>` : ''}
      ${t.status === 'closed' ? `<button class="btn btn-ghost btn-xs" data-set-status="${id}" data-to="open">Reopen</button>` : ''}
      <button class="btn btn-ghost btn-xs" data-offers="${id}" aria-expanded="false">Offers${t.pendingOffers ? ` <b class="count-pill">${t.pendingOffers}</b>` : ''}</button>
      <button class="btn btn-ghost btn-xs btn-danger" data-delete="${id}">Delete</button>
      <div class="offer-panel hidden" data-offers-for="${id}"></div></div>`;
  }
  /* Compact row used on the homepage and map pages. */
  function tradeRow(t) {
    const want = TRN.data.item(firstItem(t)), u = TRN.store.publicUser(t.userId), avatar = t.avatar || u?.avatar;
    return `<div class="trade-row">
      ${avatar ? `<img class="avatar-img" src="${TRN.IMG + esc(avatar)}" alt="">` : `<span class="avatar">${esc((t.displayName || 'R')[0])}</span>`}
      <div class="trade-row__copy"><div class="trade-row__who"><strong>${esc(t.displayName)}</strong><i class="online-dot"></i><small>${TRN.ageFromIso(t.createdAt)}</small></div>
        <div><span class="lbl">Looking for</span> ${itemsTxt(t.lookingFor, '—')}</div>
        <div><span class="lbl">Offering</span> ${offerBlock(t, true)}</div>
        <div class="trade-row__meta"><span>${esc(t.region)}</span><span>${esc(t.platform)}</span></div></div>
      <a class="trade-row__thumb" href="${want ? 'item.html?id=' + encodeURIComponent(want.id) : 'trade.html#' + esc(t.id)}"><img src="${want ? TRN.img(want.image) : unlistedArt(t.lookingFor[0]?.name)}" alt="${esc(want?.name || t.lookingFor[0]?.name || '')}"></a>
      <button class="btn btn-outline btn-xs trade-respond" data-trade="${esc(t.id)}" data-user="${esc(t.userId)}" data-name="${esc(t.displayName)}" data-item="${esc(firstItem(t))}">Respond</button>
    </div>`;
  }
  /* Inventory panel (trade page sidebar + profile). */
  function inventoryPanel(userId) {
    const st = inv(userId); if (!st) return '';
    return `<div class="inv-head"><strong>${st.ownedUnits}</strong><span>units owned</span><strong>${st.availableUnits}</strong><span>unreserved</span>${st.ok ? '' : '<em class="warn">Over-reserved!</em>'}</div>
      <div class="inv-list">${st.items.map(x => { const it = x.itemId ? TRN.data.item(x.itemId) : null; return `<div class="inv-row ${x.unavailable ? 'is-out' : ''}">
        <img src="${artFor(x.itemId, x.label)}" alt="">
        <span><strong>${it ? TRN.data.itemLink(it.id, x.label) : esc(x.label)}</strong><small>${x.unavailable ? 'UNAVAILABLE — all traded' : `${x.owned}/${x.quantityTotal} owned · ${x.reserved} reserved · ${x.available} free`}${x.itemId ? '' : ' · unlisted'}</small></span>
        <i class="inv-bar"><b style="width:${100 * x.reserved / x.quantityTotal}%"></b><u style="width:${100 * x.available / x.quantityTotal}%"></u></i></div>`; }).join('')}</div>
      <p class="small-note">Reserved = allocated to a specific open listing. Pool listings draw only from free units. Quantities never go below zero.</p>`;
  }

  async function goMessage(b, intent) {
    const u = await TRN.auth.currentUser();
    const qs = `to=${encodeURIComponent(b.dataset.user)}&name=${encodeURIComponent(b.dataset.name)}&tradeId=${encodeURIComponent(b.dataset.trade)}${b.dataset.item ? '&itemId=' + encodeURIComponent(b.dataset.item) : ''}${intent ? '&intent=' + intent : ''}`;
    if (!u) { location.href = 'auth.html?next=' + encodeURIComponent('messages.html?' + qs) + '#login'; return; }
    if ((u.user_id || u.id) === b.dataset.user) { TRN.toast('This is your own listing — manage it here or from My Profile.'); return; }
    location.href = 'messages.html?' + qs;
  }
  /* Server mode "Respond / Make Offer": log in first if needed, then open the offer form on the Trade Board. */
  async function respond(b) {
    if (!srv()) return goMessage(b, 'trade');
    const u = await TRN.auth.currentUser(), target = 'trade.html?offer=' + encodeURIComponent(b.dataset.trade);
    if (!u) { location.href = 'auth.html?next=' + encodeURIComponent(target) + '#login'; return; }
    if ((u.user_id || u.id) === b.dataset.user) { TRN.toast('This is your own listing.'); return; }
    if (TRN.trades.openOffer && $('#offerModal')) TRN.trades.openOffer(b.dataset.trade); else location.href = target;
  }
  const act = async (b, fn, ok) => { b.disabled = true; try { await fn(); if (ok) TRN.toast(ok); await renderTrades(); } catch (err) { TRN.toast(err.message); b.disabled = false; } };
  async function toggleOffers(b, root) {
    const id = b.dataset.offers, panel = $(`[data-offers-for="${CSS.escape(id)}"]`, root); if (!panel) return;
    const open = panel.classList.toggle('hidden') === false; b.setAttribute('aria-expanded', String(open)); if (!open) return;
    panel.innerHTML = '<p class="muted">Loading offers…</p>';
    try {
      const d = await TRN.store.offers.forTrade(id);
      panel.innerHTML = d.offers.length ? d.offers.map(o => `<div class="offer-row"><div><span><b>${esc(o.from.display_name)}</b> <small>@${esc(o.from.username)} · ${TRN.ageFromIso(o.created_at)}</small></span>${o.offered ? `<span class="offer-item">Offers: ${TRN.data.itemLink(o.offered.item_id, o.offered.name)}</span>` : ''}<p>${esc(o.message)}</p></div>${TRN.statusChip(o.status)}${o.status === 'ACCEPTED' ? `<span class="offer-actions"><a class="btn btn-primary btn-xs" href="handoff.html?offer=${encodeURIComponent(o.id)}">View Trade Details</a></span>` : ''}${o.status === 'PENDING' ? `<span class="offer-actions"><button class="btn btn-primary btn-xs" data-offer-act="accept" data-offer="${esc(o.id)}">Accept</button><button class="btn btn-ghost btn-xs" data-offer-act="decline" data-offer="${esc(o.id)}">Decline</button></span>` : ''}</div>`).join('') : '<p class="muted">No offers yet.</p>';
      $$('[data-offer-act]', panel).forEach(x => (x.onclick = async () => {
        if (x.dataset.offerAct !== 'accept') return act(x, () => TRN.store.offers.act(x.dataset.offer, 'decline'), 'Offer declined');
        x.disabled = true;   // v6.2: accepting opens the private trade handoff straight away
        try { const d = await TRN.store.offers.act(x.dataset.offer, 'accept'); TRN.toast('Offer accepted — opening trade details'); location.href = d.handoff?.id ? 'handoff.html?id=' + encodeURIComponent(d.handoff.id) : 'messages.html'; }
        catch (err) { TRN.toast(err.message); x.disabled = false; }
      }));
    } catch (err) { panel.innerHTML = `<p class="muted">${esc(err.message)}</p>`; }
  }
  function wireTradeButtons(root = document) {
    $$('.trade-respond', root).forEach(b => (b.onclick = () => respond(b)));
    $$('.trade-message', root).forEach(b => (b.onclick = () => goMessage(b)));
    /* server-mode owner controls */
    $$('[data-edit]', root).forEach(b => (b.onclick = () => TRN.trades.openEditor?.(ALL.find(t => t.id === b.dataset.edit))));
    $$('[data-set-status]', root).forEach(b => (b.onclick = () => act(b, () => TRN.store.updateTrade(b.dataset.setStatus, { status: b.dataset.to }), { closed: 'Trade closed', completed: 'Trade marked completed', open: 'Trade reopened' }[b.dataset.to])));
    $$('[data-delete]', root).forEach(b => (b.onclick = () => {
      if (!b.classList.contains('confirming')) { b.classList.add('confirming'); b.textContent = 'Confirm delete'; setTimeout(() => { b.classList.remove('confirming'); b.textContent = 'Delete'; }, 4000); return; }
      act(b, () => TRN.store.deleteTrade(b.dataset.delete), 'Trade deleted');
    }));
    $$('[data-offers]', root).forEach(b => (b.onclick = () => toggleOffers(b, root)));
    $$('[data-withdraw]', root).forEach(b => (b.onclick = () => act(b, () => TRN.store.offers.act(b.dataset.withdraw, 'withdraw'), 'Offer withdrawn')));
    /* demo-mode owner controls */
    $$('[data-close]', root).forEach(b => (b.onclick = async () => { await TRN.store.updateTrade(b.dataset.close, { status: 'closed' }); TRN.toast('Listing closed — reserved units returned to your pool'); renderTrades(); }));
    $$('[data-traded]', root).forEach(b => (b.onclick = () => $(`[data-form="${b.dataset.traded}"]`, root)?.classList.toggle('hidden')));
    $$('.traded-form', root).forEach(f => (f.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(f), key = fd.get('key');
      try { await TRN.store.completeTrade(f.dataset.form, key ? [{ key, quantity: Number(fd.get('qty') || 1) }] : []); TRN.toast('Trade recorded — inventory updated'); renderTrades(); }
      catch (err) { f.querySelector('.form-note').textContent = err.message; }
    }));
  }

  function filterTrades() {
    const q = ($('#tradeSearch')?.value || '').toLowerCase(), r = $('#tradeRegion')?.value || '', p = $('#tradePlatform')?.value || '', s = $('#tradeStatus')?.value ?? 'open', item = TRN.param('item') || '';
    let n = 0;
    $$('#tradeRequestGrid .trade-card').forEach(c => { const ok = (!q || c.dataset.search.includes(q)) && (!r || c.dataset.region === r) && (!p || c.dataset.platform === p) && (!s || c.dataset.status === s) && (!item || c.dataset.items.split(' ').includes(item)); c.style.display = ok ? '' : 'none'; n += ok; });
    $('#tradeCount') && ($('#tradeCount').textContent = n); $('#tradeEmpty')?.classList.toggle('hidden', n > 0);
  }
  async function renderTrades() {
    const grid = $('#tradeRequestGrid'); if (!grid) return;
    const [rows0, me] = await Promise.all([TRN.store.listTrades({ fresh: true }), TRN.auth.currentUser()]);
    const rows = prep(rows0);
    MY_OFFERS = new Map();
    if (srv() && me) { try { (await TRN.store.offers.mine()).sent.filter(o => o.status === 'PENDING').forEach(o => MY_OFFERS.set(o.trade_id, o)); } catch (e) { console.error(e); } }
    if (srv()) await TRN.store.loadServerStats();
    grid.innerHTML = rows.map(t => tradeCard(t, me)).join(''); wireTradeButtons(grid); filterTrades();
    const open = rows.filter(t => t.status === 'open');
    $('#statOpenTrades').textContent = open.length; $('#statOpenOffers').textContent = open.filter(t => t.openToOffers).length;
    $('#statCompleted') && ($('#statCompleted').textContent = TRN.store.stats().tradesCompleted || 0);
    const owners = [...new Set(open.map(t => t.userId))].filter(id => inv(id));
    $('#inventoryPanels').innerHTML = owners.map(id => `<section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('inventory')} ${esc(TRN.store.publicUser(id)?.displayName || 'Raider').toUpperCase()}'S TRADE INVENTORY</span></header>${inventoryPanel(id)}</section>`).join('');
    const counts = {}; open.forEach(t => t.lookingFor.forEach(l => l.itemId && (counts[l.itemId] = (counts[l.itemId] || 0) + 1)));
    $('#mostWanted').innerHTML = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([id]) => TRN.data.item(id)).filter(Boolean).map(i => TRN.loot.miniItem(i, `${TRN.demandLabel(i.demand)} demand`)).join('') || '<p class="muted">No open requests.</p>';
    if (location.hash) { let id = location.hash.slice(1); try { id = decodeURIComponent(id); } catch { /* malformed link */ } document.getElementById(id)?.classList.add('flash'); }
  }

  function setupTradeBoard() {
    const modal = $('#tradeModal'); if (!modal) return;
    const D = TRN.db, opts = TRN.auth.options, f = $('#tradeForm');
    let editing = null;
    const notice = $('#tradeNotice');
    if (TRN.mode === 'offline') { notice.innerHTML = `${TRN.icon('warning')}<div><strong>Trade Board unavailable.</strong> ${esc(TRN.backendProblem || '')}</div>`; notice.classList.remove('hidden'); $('#openTradeModal').disabled = true; }
    if (TRN.mode === 'demo') { notice.innerHTML = `${TRN.icon('warning')}<div><strong>Local demo mode.</strong> No server is running, so listings are stored only in this browser. Run <code>npx wrangler pages dev</code> for the real backend.</div>`; notice.classList.remove('hidden'); }
    $('#tradeRegion').innerHTML = '<option value="">All regions</option>' + opts(D.regions);
    $('#tradePlatform').innerHTML = '<option value="">All platforms</option>' + opts(D.platforms);
    f.elements.region.innerHTML = opts(D.regions, 'NA East'); f.elements.platform.innerHTML = opts(D.platforms, 'Cross-platform');
    $('#tradeItemNames').innerHTML = D.items.map(i => `<option value="${esc(i.name)}">`).join('');
    if (TRN.param('item')) { const it = TRN.data.item(TRN.param('item')); if (it) $('#tradeFilterNote').innerHTML = `Showing requests that mention ${TRN.data.itemLink(it.id)} · <a href="trade.html">Show all</a>`; }
    ['tradeSearch', 'tradeRegion', 'tradePlatform', 'tradeStatus'].forEach(id => $('#' + id)?.addEventListener('input', filterTrades));
    const preview = () => { const it = TRN.data.findItemByName(f.elements.want.value); $('#tradeItemPreview').innerHTML = it ? `<img src="${TRN.img(it.image)}" alt="">${TRN.rarityBadge(it.rarity, 'sm')}<span>Linked to <a href="item.html?id=${it.id}" target="_blank">${esc(it.name)}</a> · Intel ${it.intelScore} · ${TRN.demandLabel(it.demand)} demand</span>` : f.elements.want.value ? '<span class="muted">Not in the database — will be posted as free text.</span>' : ''; };
    f.elements.want.addEventListener('input', preview);
    const syncOffer = () => { const open = f.elements.openToOffers.checked; f.elements.have.placeholder = open ? 'Optional — you are open to offers' : 'What you can offer'; };
    f.elements.openToOffers.addEventListener('change', syncOffer);
    const setEditing = t => {
      editing = t || null;
      $('#tradeModalEyebrow').textContent = editing ? 'EDIT REQUEST' : 'NEW REQUEST';
      $('#tradeModalTitle').textContent = editing ? 'Edit your trade request' : 'Post a trade request';
      $('#tradeSubmit').textContent = editing ? 'Save Changes' : 'Publish Request';
    };
    const open = async (pre, edit) => {
      const u = await TRN.auth.currentUser(); if (!u) { location.href = 'auth.html?next=' + encodeURIComponent('trade.html?new=' + (pre || '')) + '#login'; return; }
      setEditing(edit); f.reset();
      if (pre) f.elements.want.value = TRN.data.itemName(pre);
      f.elements.region.value = u.region || 'NA East'; f.elements.platform.value = u.platform || 'Cross-platform';
      prep(await TRN.store.listTrades());
      const st = inv(u.user_id || u.id);
      $('#invOfferWrap').classList.toggle('hidden', !st);
      if (st) f.elements.invKey.innerHTML = '<option value="">— Don\'t reserve (offer from pool) —</option>' + st.items.map(x => `<option value="${esc(x.key)}" ${x.available ? '' : 'disabled'}>${esc(x.label)} (${x.available} free)</option>`).join('');
      if (srv()) $('#invOfferWrap').classList.add('hidden');
      if (edit) {
        const w = edit.lookingFor[0] || {}, o = edit.offering.find(x => !x.fromInventory);
        f.elements.want.value = w.name || TRN.data.itemName(w.itemId); f.elements.wantQty.value = w.quantity || 1;
        f.elements.have.value = o ? (o.name || TRN.data.itemName(o.itemId)) : ''; f.elements.haveQty.value = o?.quantity || 1;
        f.elements.openToOffers.checked = !!edit.openToOffers; f.elements.region.value = edit.region; f.elements.platform.value = edit.platform;
        f.elements.desiredTime.value = edit.desiredTime === 'Flexible' ? '' : (edit.desiredTime || ''); f.elements.notes.value = edit.notes || '';
      }
      preview(); syncOffer(); modal.classList.remove('hidden'); f.elements.want.focus();
    };
    TRN.trades.openEditor = t => t && open(undefined, t);
    $('#openTradeModal').onclick = () => open();
    setupOfferModal();
    $('#closeTradeModal').onclick = () => modal.classList.add('hidden');
    modal.onclick = e => { if (e.target === modal) modal.classList.add('hidden'); };
    document.addEventListener('keydown', e => { if (e.key === 'Escape') modal.classList.add('hidden'); });
    f.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(f), msg = $('#tradeFormMsg');
      try {
        const u = await TRN.auth.currentUser(); if (!u) { location.href = 'auth.html#register'; return; }
        const w = TRN.data.findItemByName(fd.get('want')), hv = String(fd.get('have') || '').trim(), h = TRN.data.findItemByName(hv);
        const st = inv(u.user_id || u.id), key = fd.get('invKey');
        const offering = [];
        if (st && key) { const x = st.items.find(i => i.key === key); offering.push({ inventoryKey: key, itemId: x.itemId, name: x.label, quantity: Number(fd.get('invQty') || 1), fromInventory: true }); }
        if (hv) offering.push({ itemId: h?.id || null, name: h ? h.name : hv, quantity: Number(fd.get('haveQty') || 1) });
        const row = { lookingFor: [{ itemId: w?.id || null, name: w ? w.name : String(fd.get('want')).trim(), quantity: Number(fd.get('wantQty') || 1) }],
          offering, offerFromPool: !!st, openToOffers: !!fd.get('openToOffers') || !offering.length,
          region: fd.get('region'), platform: fd.get('platform'), desiredTime: fd.get('desiredTime') || (srv() ? '' : 'Flexible'), notes: fd.get('notes') };
        if (String(row.lookingFor[0].name || '').length < 2) throw new Error('Tell Raiders what you are looking for.');
        const btn = $('#tradeSubmit'); btn.disabled = true;
        try { if (editing) await TRN.store.updateTrade(editing.id, row); else await TRN.store.createTrade(row, u); } finally { btn.disabled = false; }
        const wasEdit = !!editing;
        msg.textContent = wasEdit ? 'Changes saved.' : 'Trade request posted.'; f.reset(); $('#tradeItemPreview').innerHTML = ''; setEditing(null);
        setTimeout(() => { modal.classList.add('hidden'); msg.textContent = ''; renderTrades(); TRN.toast(wasEdit ? 'Trade request updated' : 'Trade request posted'); }, 300);
      } catch (err) { msg.textContent = err.message; }
    };
    renderTrades().then(() => { if (TRN.param('offer')) TRN.trades.openOffer?.(TRN.param('offer')); });
    if (TRN.param('new') !== null) open(TRN.param('new') || undefined);
  }

  /* Offer form (server mode). */
  function setupOfferModal() {
    const m = $('#offerModal'), f = $('#offerForm'); if (!m || !f) return;
    let tradeId = null;
    const close = () => m.classList.add('hidden');
    $('#closeOfferModal').onclick = close; m.onclick = e => { if (e.target === m) close(); };
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
    TRN.trades.openOffer = async id => {
      const u = await TRN.auth.currentUser();
      if (!u) { location.href = 'auth.html?next=' + encodeURIComponent('trade.html?offer=' + id) + '#login'; return; }
      const t = ALL.find(x => x.id === id);
      if (!t) { TRN.toast('That trade post no longer exists.'); return; }
      if (t.userId === (u.user_id || u.id)) { TRN.toast('This is your own listing.'); return; }
      if (t.status !== 'open') { TRN.toast('This trade is no longer open.'); return; }
      tradeId = id; f.reset(); $('#offerFormMsg').textContent = '';
      $('#offerContext').innerHTML = `To <b>${esc(t.displayName)}</b> — looking for ${itemsTxt(t.lookingFor, '—')}${t.offering.length ? `, offering ${itemsTxt(t.offering, '')}` : ''}.`;
      m.classList.remove('hidden'); f.elements.offer.focus();
    };
    f.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(f), msg = $('#offerFormMsg'), btn = f.querySelector('button[type=submit]');
      const offer = String(fd.get('offer') || '').trim(), it = TRN.data.findItemByName(offer), message = String(fd.get('message') || '').trim();
      if (message.length < 2) { msg.textContent = 'Write a short message to the Raider.'; return; }
      btn.disabled = true; msg.textContent = 'Sending…';
      try {
        await TRN.store.offers.create(tradeId, { message, offered_item_id: it?.id || null, offered_item_name: it ? undefined : (offer || null) });
        msg.textContent = 'Offer sent.'; setTimeout(() => { close(); renderTrades(); TRN.toast('Offer sent — the Raider will see it on their trade'); }, 300);
        if (TRN.param('offer')) history.replaceState(null, '', 'trade.html#' + encodeURIComponent(tradeId));
      } catch (err) { msg.textContent = err.message; }
      finally { btn.disabled = false; }
    };
  }

  TRN.trades = { tradeCard, tradeRow, inventoryPanel, prep, wireTradeButtons, setupTradeBoard, renderTrades };
})();
