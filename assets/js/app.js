/* The Raider Network v5 — shell (header, nav, footer, global search), homepage dashboard and page router. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  const page = document.body.dataset.page || '';

  /* ---------------------------------------------------------------- header / footer */
  const NAV = [['home', 'index.html', 'Home'], ['loot', 'loot.html', 'Loot Intel'], ['maps', 'maps.html', 'Maps'], ['hunts', 'hunts.html', 'Loot Hunts'],
    ['trade', 'trade.html', 'Trade Board'], ['messages', 'messages.html', 'Messages'], ['profile', 'profile.html', 'My Profile']];
  const NAV2 = [['projects', 'projects.html', 'Projects'], ['routes', 'maps.html#routes', 'Routes'], ['guides', 'maps.html#routes', 'Guides']];
  const ACTIVE = { item: 'loot', map: 'maps', auth: '', trails: 'hunts' };
  function renderShell() {
    const cur = ACTIVE[page] ?? page;
    const h = $('#siteHeader');
    if (h) h.innerHTML = `
      <div class="topbar">
        <a class="brand" href="index.html" aria-label="The Raider Network home"><img class="brand-logo" src="${TRN.IMG}branding/raider-network-mark.png" alt=""><span><strong>The Raider <em>Network</em></strong><small>FIND · HUNT · TRADE · EXTRACT</small></span></a>
        <nav class="main-nav" id="mainNav" aria-label="Primary">${NAV.map(([k, href, l]) => `<a class="${k === cur ? 'active' : ''}" href="${href}" data-nav="${k}">${l}</a>`).join('')}
          <div class="nav-secondary-mobile">${NAV2.map(([k, href, l]) => `<a class="${k === cur ? 'active' : ''}" href="${href}">${l}</a>`).join('')}</div>
          <div class="nav-account-mobile" id="navAccountMobile"></div></nav>
        <div class="account-actions">
          <button class="icon-btn" id="openSearch" aria-label="Search">${TRN.icon('search')}</button>
          <a class="icon-btn hidden" id="navInbox" href="messages.html" aria-label="Messages">${TRN.icon('message')}</a>
          <a class="text-btn" id="navLogin" href="auth.html">Log in</a>
          <a class="btn btn-primary btn-sm" id="navJoin" href="auth.html#register">Join the Network</a>
          <a class="nav-user hidden" id="navUser" href="profile.html"><img id="navAvatar" src="" alt=""><span id="navUserName"></span></a>
          <button class="icon-btn menu-btn" id="menuBtn" type="button" aria-label="Open menu" aria-controls="mainNav" aria-expanded="false">${TRN.svg('menu')}</button>
        </div>
      </div>
      <div class="subbar"><span class="ticker">FIND IT. <b>HUNT IT.</b> TRADE IT. <b>EXTRACT.</b></span><nav aria-label="Secondary">${NAV2.map(([k, href, l]) => `<a class="${k === cur ? 'active' : ''}" href="${href}">${l}</a>`).join('')}<span class="demo-pill hidden" id="modePill"></span></nav></div>
      <div class="search-overlay hidden" id="searchOverlay" role="dialog" aria-label="Search the network"><div class="search-overlay__box"><div class="global-search">${TRN.icon('search')}<input id="overlaySearch" placeholder="Search items, maps, projects or quests…" autocomplete="off"></div><button class="icon-btn" id="closeSearch" aria-label="Close search">${TRN.svg('close')}</button><p class="muted">Try “rotary”, “stella”, “trophy” or “with a view”.</p></div></div>`;
    const f = $('#siteFooter');
    if (f) f.innerHTML = `<div class="footer-inner">
      <div class="brand footer-brand"><img class="brand-logo" src="${TRN.IMG}branding/raider-network-mark.png" alt=""><span><strong>The Raider Network</strong><small>INDEPENDENT ARC RAIDERS COMMUNITY & INTEL HUB</small></span></div>
      <nav>${[...NAV.slice(0, 5), ...NAV2.slice(0, 2)].map(([, href, l]) => `<a href="${href}">${l}</a>`).join('')}</nav>
      <p class="mf-attr">Map data sourced in part from <a href="https://metaforge.app/arc-raiders" target="_blank" rel="noopener">MetaForge</a> community data.</p>
      <p>Unofficial fan site. Not affiliated with Embark Studios. ARC Raiders and all game content © Embark Studios AB. Core item data: <a href="https://github.com/RaidTheory/arcraiders-data" target="_blank" rel="noopener">RaidTheory arcraiders-data</a> (MIT). Artwork on this site is concept art, not in-game imagery.</p></div>`;
    setupMenu();
    const ov = $('#searchOverlay');
    const openS = () => { ov.classList.remove('hidden'); $('#overlaySearch').focus(); };
    $('#openSearch')?.addEventListener('click', openS); $('#closeSearch')?.addEventListener('click', () => ov.classList.add('hidden'));
    ov?.addEventListener('click', e => { if (e.target === ov) ov.classList.add('hidden'); });
    document.addEventListener('keydown', e => { if (e.key === '/' && !/input|textarea|select/i.test(document.activeElement.tagName)) { e.preventDefault(); openS(); } if (e.key === 'Escape') ov?.classList.add('hidden'); });
  }
  /* Mobile drawer (≤1280px). State lives in one place (body.nav-open) and is mirrored to aria-expanded / the label. */
  function setupMenu() {
    const btn = $('#menuBtn'), nav = $('#mainNav'), header = $('#siteHeader');
    if (!btn || !nav) return;
    const isOpen = () => document.body.classList.contains('nav-open');
    const set = open => {
      if (open) document.documentElement.style.setProperty('--nav-top', Math.round(header.getBoundingClientRect().bottom) + 'px');
      document.body.classList.toggle('nav-open', open);
      btn.setAttribute('aria-expanded', String(open));
      btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      btn.innerHTML = TRN.svg(open ? 'close' : 'menu');
    };
    btn.addEventListener('click', () => { const open = !isOpen(); set(open); if (open) nav.querySelector('a')?.focus({ preventScroll: true }); });
    nav.addEventListener('click', e => { if (e.target.closest('a')) set(false); });
    document.addEventListener('pointerdown', e => { if (isOpen() && !nav.contains(e.target) && !btn.contains(e.target)) set(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen()) { set(false); btn.focus(); } });
    matchMedia('(min-width:1281px)').addEventListener?.('change', m => { if (m.matches) set(false); });
    window.addEventListener('pageshow', () => set(false));   // bfcache: never come back to an open drawer
    TRN.menu = { open: () => set(true), close: () => set(false), isOpen };
  }
  async function syncNav() {
    const u = await TRN.auth.currentUser();
    ['#navLogin', '#navJoin'].forEach(s => $(s)?.classList.toggle('hidden', !!u));
    ['#navUser', '#navInbox'].forEach(s => $(s)?.classList.toggle('hidden', !u));
    if (u) { $('#navUserName').textContent = u.display_name || 'Raider'; $('#navAvatar').src = TRN.IMG + (u.avatar || 'raiders/raider-solo-scout.webp'); }
    else $$('[data-nav=messages],[data-nav=profile]').forEach(a => (a.href = 'auth.html?next=' + a.getAttribute('href') + '#login'));
    const acct = $('#navAccountMobile');
    if (acct) {
      acct.innerHTML = u
        ? `<div class="who"><img src="${TRN.IMG + esc(u.avatar || 'raiders/raider-solo-scout.webp')}" alt=""><span>Signed in as <strong>${esc(u.display_name || 'Raider')}</strong>${u.username ? `<small>@${esc(u.username)}</small>` : ''}</span></div><button class="btn btn-ghost" type="button" id="navLogoutMobile">Log out</button>`
        : `<a class="btn btn-ghost" href="auth.html#login">Log in</a><a class="btn btn-primary" href="auth.html#register">Register</a>`;
      $('#navLogoutMobile')?.addEventListener('click', () => TRN.auth.logout());
    }
  }

  /* ---------------------------------------------------------------- global search / autocomplete */
  function searchAll(q, kinds = ['item', 'map', 'project', 'quest']) {
    q = q.trim().toLowerCase(); if (q.length < 2) return [];
    const D = TRN.db, out = [];
    const score = (name) => { const n = name.toLowerCase(); return n === q ? 0 : n.startsWith(q) ? 1 : n.split(/\W+/).some(w => w.startsWith(q)) ? 2 : n.includes(q) ? 3 : 9; };
    if (kinds.includes('map')) D.maps.forEach(m => { const s = Math.min(score(m.name), score(m.shortName)); if (s < 9) out.push({ s: s - 0.5, kind: 'Map', label: m.name, sub: m.lootProfile, img: m.image, href: 'map.html?id=' + m.id }); });
    if (kinds.includes('item')) D.items.forEach(i => { const s = score(i.name); if (s < 9) out.push({ s: s + (100 - i.intelScore) / 1000, kind: 'Item', label: i.name, sub: `${i.rarity} · ${i.category} · Intel ${i.intelScore}`, img: i.image, href: 'item.html?id=' + i.id, rarity: i.rarity }); });
    if (kinds.includes('project') && D.projects.length) D.projects.forEach(p => { const s = Math.min(score(p.name), ...(p.aliases || []).map(score)); if (s < 9) out.push({ s, kind: 'Project', label: p.name, sub: p.status, href: 'projects.html#' + p.id }); });
    if (kinds.includes('quest') && D.quests.length) D.quests.forEach(qq => { const s = score(qq.name); if (s < 9) out.push({ s: s + 0.2, kind: 'Quest', label: qq.name, sub: `${qq.trader || ''}${qq.requiredItems.length ? ' · needs ' + qq.requiredItems.map(r => TRN.data.itemName(r.itemId)).join(', ') : ''}`, href: qq.requiredItems.length ? 'loot.html?quest=' + qq.id : 'loot.html?q=' + encodeURIComponent(qq.name) }); });
    return out.sort((a, b) => a.s - b.s).slice(0, 9);
  }
  function attachAutocomplete(input, { kinds, onPick } = {}) {
    if (!input) return;
    const wrap = input.closest('.global-search, .hero-search, .search-field') || input.parentElement;
    wrap.classList.add('has-ac');
    const box = document.createElement('div'); box.className = 'ac-box hidden'; box.setAttribute('role', 'listbox'); wrap.appendChild(box);
    let rows = [], sel = -1;
    const paint = () => { box.innerHTML = rows.map((r, i) => `<a class="ac-row ${i === sel ? 'sel' : ''}" href="${r.href}" role="option">${r.img ? `<img src="${TRN.img(r.img)}" alt="">` : `<span class="ac-ico">${TRN.icon(r.kind === 'Project' ? 'project' : 'route')}</span>`}<span><strong>${esc(r.label)}</strong><small>${esc(r.sub || '')}</small></span><em class="ac-kind kind-${r.kind.toLowerCase()}">${r.kind}</em></a>`).join('') + (rows.length ? '' : ''); box.classList.toggle('hidden', !rows.length); };
    input.addEventListener('input', TRN.debounce(() => { rows = searchAll(input.value, kinds); sel = -1; paint(); }, 60));
    input.addEventListener('keydown', e => {
      if (box.classList.contains('hidden')) return;
      if (e.key === 'ArrowDown') { sel = Math.min(rows.length - 1, sel + 1); paint(); e.preventDefault(); }
      if (e.key === 'ArrowUp') { sel = Math.max(-1, sel - 1); paint(); e.preventDefault(); }
      if (e.key === 'Enter' && sel > -1) { e.preventDefault(); onPick ? onPick(rows[sel]) : (location.href = rows[sel].href); }
      if (e.key === 'Escape') box.classList.add('hidden');
    });
    input.addEventListener('blur', () => setTimeout(() => box.classList.add('hidden'), 160));
    input.addEventListener('focus', () => { if (rows.length) box.classList.remove('hidden'); });
  }
  TRN.attachAutocomplete = attachAutocomplete; TRN.searchAll = searchAll;

  /* ---------------------------------------------------------------- homepage */
  async function renderHome() {
    const D = TRN.db;
    const [hunts, trades] = await Promise.all([TRN.store.listHunts(), TRN.store.listTrades(), TRN.store.loadServerStats()]);
    attachAutocomplete($('#homeSearch'));
    $('#homeSearchForm').onsubmit = e => { e.preventDefault(); const q = $('#homeSearch').value.trim(); const top = searchAll(q)[0]; location.href = top && top.s < 1.5 ? top.href : 'loot.html?q=' + encodeURIComponent(q); };
    /* Popular Loot Hunts = items with the most open hunts (real community hunts), highest Intel first. Feature art when available. */
    const openH = hunts.filter(h => h.status === 'open' && h.itemId);
    const ranked = [...new Set(openH.map(h => h.itemId))].map(id => TRN.data.item(id)).filter(Boolean)
      .sort((a, b) => openH.filter(h => h.itemId === b.id).length - openH.filter(h => h.itemId === a.id).length || b.intelScore - a.intelScore).slice(0, 4);
    $('#popularLoot').innerHTML = ranked.map(it => {
      const n = openH.filter(h => h.itemId === it.id).length;
      return TRN.loot.itemCard(it, { compact: true, feature: true }).replace('<div class="item-card__body">', `<div class="item-card__body">${n ? `<span class="hunting-now">${TRN.svg('users')} ${n} hunting now</span>` : ''}`);
    }).join('');
    const route = D.routes.find(r => r.featured) || D.routes[0];
    $('#featuredRoute').innerHTML = TRN.maps.routeCard(route);
    TRN.trades.prep(trades);
    const open = trades.filter(t => t.status === 'open').sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)).slice(0, 4);
    $('#homeTrades').innerHTML = open.map(TRN.trades.tradeRow).join('') || '<p class="muted">No open requests.</p>';
    TRN.trades.wireTradeButtons($('#homeTrades'));
    $('#homeMaps').innerHTML = D.maps.filter(m => m.status === 'live').map(m => TRN.maps.mapCard(m, hunts, { compact: true })).join('');
    const sev = { safe: 'Low risk', risky: 'Risky', 'high-threat': 'High threat', hazard: 'Hazard', weather: 'Weather risk' };
    $('#homeConditions').innerHTML = (D.conditions?.demoSchedule || []).map(c => `<a class="cond-row" href="map.html?id=${encodeURIComponent(c.mapId)}"><img src="${TRN.IMG}ui/condition-${esc(c.severity)}.png" alt=""><span><strong>${esc(c.condition)}</strong><small>${esc(TRN.data.mapName(c.mapId))} · ${esc(sev[c.severity] || '')}</small></span><em>${esc(c.window)}</em></a>`).join('');
    const proj = TRN.projects.sorted(), cur = proj.filter(p => p.status !== 'HISTORICAL'), hist = proj.filter(p => p.status === 'HISTORICAL').slice(0, Math.max(1, 3 - cur.length));
    $('#homeProjects').innerHTML = [...cur, ...hist].slice(0, 3).map(TRN.projects.projectCompact).join('');
    renderStats(hunts, trades);
    $('#statHuntsHero').textContent = hunts.filter(h => h.status === 'open').length;
    $('#statItemsHero').textContent = D.items.length;
    $('#statTradesHero').textContent = trades.filter(t => t.status === 'open').length;
  }
  /* Community stats are isolated here so they can come from Supabase aggregate views later. */
  function renderStats(hunts, trades) {
    const s = TRN.store.stats();
    const tiles = [['squad', TRN.num(s.foundingRaiders ?? s.activeRaiders), 'Founding Raiders', 'launch'], ['route', TRN.num(hunts.filter(h => h.status === 'open').length), 'Open Loot Hunts', 'live'],
      ['trade', TRN.num(trades.filter(t => t.status === 'open').length), 'Open Trade Requests', 'live'], ['extraction', TRN.num(s.tradesCompleted || 0), 'Trades Completed', 'live'],
      ['loot-intel', TRN.num(TRN.db.items.length), 'Loot Intel Records', 'live'], ['map', TRN.num(TRN.db.maps.filter(m => m.status === 'live').length), 'Maps', 'live']];
    $('#homeStats').innerHTML = tiles.map(([ic, v, l, k]) => `<div class="stat-tile" data-stat="${TRN.slug(l)}">${TRN.icon(ic)}<span><strong>${v}</strong><small>${l}</small></span><i class="spark spark-${k === 'launch' ? 'demo' : 'live'}"></i><em>${k === 'launch' ? 'LAUNCH' : 'LIVE'}</em></div>`).join('');
  }

  /* ---------------------------------------------------------------- router */
  const NEEDS = {
    home: ['items', 'maps', 'projects', 'quests', 'routes', 'conditions', 'users', 'hunts', 'trades', 'inventory'],
    loot: ['items', 'maps', 'projects', 'quests', 'users', 'hunts', 'trades'], item: ['items', 'maps', 'projects', 'quests', 'users', 'hunts', 'trades', 'workshop'],
    maps: ['items', 'maps', 'routes', 'conditions', 'users', 'hunts', 'projects', 'quests'], map: ['items', 'maps', 'projects', 'quests', 'routes', 'arcs', 'conditions', 'users', 'hunts', 'trades', 'inventory', 'mapIndex'],
    projects: ['items', 'projects', 'quests', 'maps'], hunts: ['items', 'maps', 'users', 'hunts', 'projects', 'quests'], trade: ['items', 'maps', 'users', 'trades', 'inventory', 'projects', 'quests'],
    messages: ['items', 'maps', 'users', 'hunts', 'trades', 'projects', 'quests'], profile: ['items', 'maps', 'users', 'hunts', 'trades', 'inventory', 'projects', 'quests'], trails: ['items', 'maps'], auth: ['users', 'items', 'maps', 'projects', 'quests']
  };
  /* Show which backend is active. Production (server mode) shows nothing; local demo and outages are labelled. */
  function paintMode() {
    const pill = $('#modePill'); if (!pill) return;
    if (TRN.mode === 'demo') { pill.textContent = 'DEMO MODE'; pill.title = 'Local development demo: no server is running, so accounts, hunts, trades and messages are stored only in this browser.'; pill.classList.remove('hidden'); }
    else if (TRN.mode === 'offline') { pill.textContent = 'OFFLINE'; pill.title = TRN.backendProblem || 'Accounts and trading are temporarily unavailable.'; pill.classList.remove('hidden'); }
    const hn = $('#huntsNotice');
    if (hn && TRN.mode === 'server') { hn.innerHTML = `${TRN.icon('warning')}<div><strong>Loot Hunts are in preview.</strong> Hunts you start are saved in this browser only and other Raiders can't see them yet — they move to the server in the next update. The Trade Board is fully live.</div>`; hn.classList.remove('hidden'); }
  }
  document.addEventListener('DOMContentLoaded', async () => {
    renderShell();
    try {
      await Promise.all([TRN.api.init(), TRN.data.load(NEEDS[page] || ['items', 'maps', 'users'])]);
      paintMode();
    } catch (e) {
      console.error(e);
      document.querySelector('main')?.insertAdjacentHTML('afterbegin', `<div class="load-error">${TRN.icon('warning')}<div><strong>Data could not load.</strong> Run the site through a local server: <code>python3 -m http.server 8080</code> and open http://localhost:8080 (opening the HTML file directly blocks the JSON requests).</div></div>`);
      return;
    }
    attachAutocomplete($('#overlaySearch'));
    syncNav();
    const run = { home: renderHome, loot: TRN.loot.setupLootPage, item: TRN.loot.setupItemPage, maps: TRN.maps.setupMapsPage, map: TRN.maps.setupMapPage,
      projects: TRN.projects.setupProjectsPage, hunts: TRN.hunts.setupHuntsPage, trade: TRN.trades.setupTradeBoard, messages: TRN.messages.setupMessages,
      profile: TRN.auth.setupProfilePage, auth: TRN.auth.setupAuthPage, handoff: TRN.handoffs?.setupHandoffPage, trails: TRN.trails?.setupTrailsPage }[page];
    try { await run?.(); } catch (e) { console.error(e); TRN.toast('Something went wrong rendering this page.'); }
    document.body.classList.add('ready');
  });
})();
