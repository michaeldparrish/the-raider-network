/* The Raider Network v5 — Loot Intel database (loot.html) and item detail (item.html). */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN, D = () => TRN.db;
  const RANK = { Common: 1, Uncommon: 2, Rare: 3, Epic: 4, Legendary: 5 };

  const bestSpot = it => {
    const locs = (it.locations || []).filter(x => x.map);
    if (!locs.length) return { map: null, mapLabel: 'Unverified', area: it.lootZones?.[0] ? `${it.lootZones[0]} loot zones` : (it.arcSources?.[0] ? `${it.arcSources[0]} drop` : 'Unknown') };
    const l = locs[0], maps = [...new Set(locs.map(x => x.map))];
    if (!l.bestArea && maps.length > 1) return { map: null, mapLabel: `${maps.length} maps`, area: l.common ? 'Common ARC drop' : (l.method || '').replace(/^Dropped by /, '') + ' drop' };
    return { map: l.map, area: l.bestArea || l.areas?.[0] || ((l.method || '').startsWith('Dropped by ') ? l.method.replace(/^Dropped by /, '') + ' drop' : 'Map-wide') };
  };

  function itemCard(it, opts = {}) {
    const s = bestSpot(it);
    return `<article class="item-card rarity-edge-${esc(it.rarity.toLowerCase())}" data-id="${esc(it.id)}">
      <a class="item-card__media ${opts.feature && it.heroImage ? 'is-feature' : 'is-db-' + esc(it.imageKind)}" href="item.html?id=${encodeURIComponent(it.id)}" tabindex="-1" aria-hidden="true"><img src="${TRN.img(opts.feature && it.heroImage ? it.heroImage : it.image)}" alt="" loading="lazy">${TRN.rarityBadge(it.rarity, 'sm')}</a>
      <div class="item-card__body">
        <div class="item-card__title"><div><h3><a href="item.html?id=${encodeURIComponent(it.id)}">${esc(it.name)}</a></h3><small>${esc(it.category)}</small></div>${TRN.intelBadge(it.intelScore)}</div>
        <dl class="kv">
          <div><dt>${TRN.icon('map')}Best map</dt><dd>${s.map ? TRN.data.mapLink(s.map) : `<span class="${s.mapLabel === 'Unverified' ? 'muted' : ''}">${esc(s.mapLabel)}</span>`}</dd></div>
          <div><dt>${TRN.icon('location')}Best area</dt><dd>${esc(s.area)}</dd></div>
          <div><dt>${TRN.icon('difficulty')}Difficulty</dt><dd>${esc(TRN.diffLabel(it.difficulty))}</dd></div>
          <div><dt>${TRN.icon('value')}Demand</dt><dd class="demand-txt-${esc(TRN.demandLabel(it.demand).toLowerCase().replace(' ', '-'))}">${esc(TRN.demandLabel(it.demand))}</dd></div>
        </dl>
        ${opts.compact ? '' : `<div class="item-card__foot">${TRN.recoBadge(it.recommendation)}<span class="value-tag">${TRN.icon('value')}${TRN.num(it.sellValue)}</span></div>`}
        <a class="btn btn-outline btn-block" href="item.html?id=${encodeURIComponent(it.id)}">View Intel ${TRN.svg('arrow')}</a>
      </div></article>`;
  }
  const miniItem = (it, extra = '') => `<a class="mini-item rarity-edge-${esc(it.rarity.toLowerCase())}" href="item.html?id=${encodeURIComponent(it.id)}"><img src="${TRN.img(it.image)}" alt="" loading="lazy"><span><strong>${esc(it.name)}</strong><small>${extra || esc(it.rarity + ' · ' + it.category)}</small></span><b class="${TRN.intelClass(it.intelScore)}">${it.intelScore}</b></a>`;

  /* ---------------------------------------------------------------- loot.html */
  const state = { q: '', rarity: '', category: '', group: '', map: '', flags: new Set(), demand: '', difficulty: '', sort: 'intel', limit: 36, quest: '', project: '' };
  function filtered() {
    const q = state.q.trim().toLowerCase();
    const questReq = state.quest ? new Set((TRN.db.idx.quest.get(state.quest)?.requiredItems || []).map(r => r.itemId)) : null;
    let rows = D().items.filter(it =>
      (!q || it.name.toLowerCase().includes(q) || it.category.toLowerCase().includes(q) || (it.lootZones || []).join(' ').toLowerCase().includes(q)) &&
      (!state.rarity || it.rarity === state.rarity) && (!state.category || it.category === state.category) && (!state.group || it.group === state.group) &&
      (!state.map || it.maps.includes(state.map)) &&
      (!state.flags.has('project') || it.projects.length) && (!state.flags.has('quest') || it.quests.length) &&
      (!state.flags.has('crafting') || it.craftingUses.length) && (!state.flags.has('recyclable') || it.recyclable) &&
      (!state.flags.has('located') || it.maps.length) &&
      (!state.demand || TRN.demandLabel(it.demand) === state.demand) && (!state.difficulty || TRN.diffLabel(it.difficulty) === state.difficulty) &&
      (!questReq || questReq.has(it.id)) && (!state.project || it.projects.includes(state.project)));
    const by = { intel: (a, b) => b.intelScore - a.intelScore, demand: (a, b) => b.demand - a.demand || b.intelScore - a.intelScore,
      rarity: (a, b) => RANK[b.rarity] - RANK[a.rarity] || b.intelScore - a.intelScore, value: (a, b) => (b.sellValue || 0) - (a.sellValue || 0),
      alpha: (a, b) => a.name.localeCompare(b.name) }[state.sort];
    return rows.sort(by);
  }
  function renderResults() {
    const rows = filtered(), grid = $('#lootResults');
    $('#resultCount').innerHTML = `<strong>${rows.length}</strong> of ${D().items.length} records`;
    grid.innerHTML = rows.slice(0, state.limit).map(it => itemCard(it)).join('') || `<div class="empty-state">${TRN.icon('search')}<strong>No items match those filters.</strong><button class="btn btn-ghost" id="resetFilters2">Reset filters</button></div>`;
    $('#loadMore').classList.toggle('hidden', rows.length <= state.limit);
    $('#loadMore').textContent = `Show more (${rows.length - state.limit} remaining)`;
    $('#resetFilters2')?.addEventListener('click', resetFilters);
    const chips = [];
    if (state.quest) chips.push(`Quest: ${esc(TRN.data.questName(state.quest))}`);
    const mp = state.map && TRN.data.map(state.map);
    $('#mapBanner').innerHTML = mp ? `<div class="loot-map-banner"><img src="${TRN.img(mp.image)}" alt=""><div><small class="eyebrow">MAP FILTER</small><strong>Loot on ${esc(mp.name)}</strong></div><a class="btn btn-ghost btn-sm" href="map.html?id=${encodeURIComponent(mp.id)}">${TRN.icon('map')} Open map</a><button class="text-btn" id="clearMap">Clear</button></div>` : '';
    $('#clearMap')?.addEventListener('click', () => { state.map = ''; $('#mapFilter').value = ''; history.replaceState(null, '', 'loot.html'); renderResults(); });
    if (state.project) chips.push(`Project: ${esc(TRN.db.idx.project.get(state.project)?.name || state.project)}`);
    $('#activeContext').innerHTML = chips.map(c => `<span class="ctx-chip">${c}</span>`).join('') + (chips.length ? '<button class="text-btn" id="clearCtx">Clear</button>' : '');
    $('#clearCtx')?.addEventListener('click', () => { state.quest = state.project = ''; history.replaceState(null, '', 'loot.html'); renderResults(); });
  }
  function resetFilters() {
    Object.assign(state, { q: '', rarity: '', category: '', group: '', map: '', demand: '', difficulty: '', sort: 'intel', limit: 36, quest: '', project: '' }); state.flags.clear();
    $('#lootSearch').value = ''; $$('.filter-bar select').forEach(s => (s.value = s.id === 'sortBy' ? 'intel' : '')); $$('.flag-toggle input').forEach(c => (c.checked = false));
    renderResults();
  }
  function dashboardPanels(hunts, trades) {
    const it = D().items, loot = it.filter(x => x.group === 'Loot & Materials');
    const hunted = new Map();
    hunts.filter(h => h.status !== 'completed').forEach(h => h.itemId && hunted.set(h.itemId, (hunted.get(h.itemId) || 0) + 2));
    trades.filter(t => t.status === 'open').forEach(t => t.lookingFor.forEach(l => l.itemId && hunted.set(l.itemId, (hunted.get(l.itemId) || 0) + 1)));
    const mostHunted = [...hunted.entries()].sort((a, b) => b[1] - a[1]).map(([id, n]) => [TRN.data.item(id), n]).filter(x => x[0]).slice(0, 5);
    const panel = (title, ico, list, sub) => `<section class="dash-panel"><header>${TRN.icon(ico)}<h3>${title}</h3></header><div class="mini-list">${list.map(x => Array.isArray(x) ? miniItem(x[0], x[1]) : miniItem(x, sub ? sub(x) : '')).join('')}</div></section>`;
    $('#lootDash').innerHTML =
      panel('Most Hunted', 'squad', mostHunted.map(([i, n]) => [i, `${n} active hunt/trade signal${n > 1 ? 's' : ''}`])) +
      panel('Hardest to Find', 'difficulty', [...loot].sort((a, b) => b.difficulty - a.difficulty || b.intelScore - a.intelScore).slice(0, 5), x => `${TRN.diffLabel(x.difficulty)} · ${x.difficulty}/10`) +
      panel('Project Critical', 'project', it.filter(x => x.recommendation === 'PROJECT CRITICAL').sort((a, b) => b.intelScore - a.intelScore).slice(0, 5), x => x.projects.map(p => TRN.db.idx.project.get(p)).filter(p => p && p.status !== 'HISTORICAL').map(p => p.name)[0] || 'Active project') +
      panel('Best Recycling Value', 'recycle', loot.filter(x => x.recyclable && x.scores[4] >= 60).sort((a, b) => (b.sellValue * b.scores[4]) - (a.sellValue * a.scores[4])).slice(0, 5), x => `Recycles to ${x.scores[4]}% of its value`) +
      panel('High Demand', 'value', [...it].sort((a, b) => b.demand - a.demand || b.intelScore - a.intelScore).slice(0, 5), x => `${TRN.demandLabel(x.demand)} · ${x.demand}/10`);
  }
  async function setupLootPage() {
    if (!$('#lootResults')) return;
    const cats = [...new Set(D().items.map(i => i.category))].sort(), groups = [...new Set(D().items.map(i => i.group))];
    $('#categoryFilter').innerHTML = '<option value="">All categories</option>' + cats.map(c => `<option>${esc(c)}</option>`).join('');
    $('#groupFilter').innerHTML = '<option value="">All item groups</option>' + groups.map(c => `<option>${esc(c)}</option>`).join('');
    $('#mapFilter').innerHTML = '<option value="">All maps</option>' + D().maps.filter(m => m.status === 'live').map(m => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
    $('#statRecords').textContent = D().items.length; $('#statLocated').textContent = D().items.filter(i => i.maps.length).length;
    $('#statProjects').textContent = D().items.filter(i => i.projects.length).length; $('#statQuests').textContent = D().items.filter(i => i.quests.length).length;
    $('#dataAsOf').textContent = `Community data snapshot ${D().meta.sourceCommit?.split(' ')[1] || ''} · Scores as of ${D().meta.intelScore?.asOf}`;
    state.q = TRN.param('q') || ''; state.map = TRN.data.map(TRN.param('map'))?.id || ''; state.quest = TRN.param('quest') || ''; state.project = TRN.param('project') || '';
    if (TRN.param('flag')) state.flags.add(TRN.param('flag'));
    $('#lootSearch').value = state.q; $('#mapFilter').value = state.map;
    $$('.flag-toggle input').forEach(c => (c.checked = state.flags.has(c.value)));
    const on = (id, key) => $(id).addEventListener('change', e => { state[key] = e.target.value; state.limit = 36; renderResults(); });
    on('#rarityFilter', 'rarity'); on('#categoryFilter', 'category'); on('#groupFilter', 'group'); on('#mapFilter', 'map'); $('#mapFilter').addEventListener('change', () => history.replaceState(null, '', state.map ? 'loot.html?map=' + state.map : 'loot.html')); on('#demandFilter', 'demand'); on('#difficultyFilter', 'difficulty'); on('#sortBy', 'sort');
    $$('.flag-toggle input').forEach(c => c.addEventListener('change', () => { c.checked ? state.flags.add(c.value) : state.flags.delete(c.value); state.limit = 36; renderResults(); }));
    $('#lootSearch').addEventListener('input', TRN.debounce(e => { state.q = e.target.value; state.limit = 36; renderResults(); }, 90));
    $('#lootSearchForm').addEventListener('submit', e => { e.preventDefault(); const exact = TRN.data.findItemByName(state.q); if (exact) location.href = 'item.html?id=' + exact.id; else renderResults(); });
    $('#loadMore').onclick = () => { state.limit += 48; renderResults(); };
    $('#resetFilters').onclick = resetFilters;
    $('#filterToggle').onclick = () => $('#filterBar').classList.toggle('open');
    TRN.attachAutocomplete?.($('#lootSearch'), { kinds: ['item'], onPick: r => (location.href = r.href) });
    renderResults();
    const [hunts, trades] = await Promise.all([TRN.store.listHunts(), TRN.store.listTrades()]);
    dashboardPanels(hunts, trades);
  }

  /* ---------------------------------------------------------------- item.html */
  const bar = (label, val, note, cls = '') => `<div class="meter ${cls}"><div class="meter__head"><span>${label}</span><strong>${note}</strong></div><div class="meter__track"><i style="width:${Math.max(2, Math.min(100, val))}%"></i></div></div>`;
  async function setupItemPage() {
    const root = $('#itemRoot'); if (!root) return;
    const it = TRN.data.item(TRN.param('id'));
    if (!it) { root.innerHTML = `<div class="page-shell"><div class="empty-state big">${TRN.icon('warning')}<h1>Item not found</h1><p>No record for “${esc(TRN.param('id') || '')}”.</p><a class="btn btn-primary" href="loot.html">Search Loot Intel</a></div></div>`; return; }
    document.title = `${it.name} — Loot Intel — The Raider Network`;
    const [hunts, trades] = await Promise.all([TRN.store.listHunts(), TRN.store.listTrades()]);
    const myHunts = hunts.filter(h => h.itemId === it.id && h.status !== 'completed');
    const myTrades = trades.filter(t => t.status === 'open' && (t.lookingFor.some(l => l.itemId === it.id) || t.offering.some(o => o.itemId === it.id)));
    const reco = myTrades.length && !it.recommendation ? 'TRADE INTEREST' : it.recommendation;
    const [sR, sD, sQ, sP, sRec, sC, sDiff, sV] = it.scores;
    const locs = (it.locations || []).filter(l => l.map), primary = locs[0];
    const primaryMap = primary ? TRN.data.map(primary.map) : null;
    const otherAreas = primary ? (primary.areas || []).filter(a => a !== primary.bestArea) : [];
    const recFrom = D().items.filter(x => x.recycleOutputs.some(r => r.itemId === it.id));
    const src = id => D().meta.sources?.[id] || { label: id };
    const projUses = D().projects.flatMap(p => p.stages.flatMap(s => s.requiredItems.filter(r => r.itemId === it.id).map(r => ({ p, s, q: r.quantity }))));
    const questUses = D().quests.flatMap(q => q.requiredItems.filter(r => r.itemId === it.id).map(r => ({ q, n: r.quantity })));

    root.innerHTML = `
    <section class="item-hero rarity-glow-${esc(it.rarity.toLowerCase())}">
      <div class="item-hero__bg" style="background-image:url('${primaryMap ? TRN.img(primaryMap.image) : TRN.IMG + 'heroes/raider-network-skyline.webp'}')"></div>
      <div class="item-hero__inner">
        <nav class="crumbs"><a href="loot.html">Loot Intel</a><span>/</span><a href="loot.html?q=${encodeURIComponent(it.category)}">${esc(it.category)}</a><span>/</span><b>${esc(it.name)}</b></nav>
        <div class="item-hero__grid">
          <figure class="item-art"><img src="${TRN.img(it.image)}" alt="Artwork for ${esc(it.name)}"><figcaption>${{ database: 'Database art · reference silhouette', dedicated: 'Concept art', category: 'Category concept art', premium: 'Raider Network render' }[it.imageKind] || 'Concept art'} · not an in-game render</figcaption>${it.heroImage && it.heroImage !== it.image ? `<img class="feature-inset" src="${TRN.img(it.heroImage)}" alt="" title="Feature art (cinematic concept render)">` : ''}</figure>
          <div class="item-hero__copy">
            <div class="chip-row">${TRN.rarityBadge(it.rarity)}<span class="cat-chip">${esc(it.category)}</span>${TRN.demandChip(it.demand)}</div>
            <h1>${esc(it.name)}</h1>
            ${it.description ? `<p class="lede">${esc(it.description)}</p>` : ''}
            ${it.notes ? `<p class="intel-note">${TRN.icon('loot-intel')}<span>${esc(it.notes)}</span></p>` : ''}
            <div class="chip-row">${TRN.recoBadge(reco)}${TRN.confChip(D().meta.defaults.coreConfidence)}<span class="conf-label">Record detail: ${esc(it.dataConfidence)}</span></div>
            <div class="hero-actions">
              <a class="btn btn-primary" href="hunts.html?new=${encodeURIComponent(it.id)}">${TRN.icon('squad')} Start a Loot Hunt</a>
              <a class="btn btn-ghost" href="trade.html?new=${encodeURIComponent(it.id)}">${TRN.icon('trade')} Post Trade Request</a>
            </div>
          </div>
          ${TRN.intelBadge(it.intelScore, true)}
        </div>
      </div>
    </section>
    <div class="page-shell item-layout">
      <div class="item-main">
        <section class="panel where-panel" id="where">
          <header class="panel-head"><span class="eyebrow">${TRN.icon('location')} WHERE TO FIND</span><h2>Where to find ${esc(it.name)}</h2>${TRN.confChip(it.locationConfidence)}</header>
          ${primary ? `
          <div class="where-grid">
            <a class="where-map" href="map.html?id=${encodeURIComponent(primary.map)}"><img src="${TRN.img(primaryMap?.image)}" alt=""><span><small>PRIMARY MAP</small><strong>${esc(TRN.data.mapName(primary.map))}</strong></span></a>
            <dl class="where-facts">
              <div><dt>Best area</dt><dd>${esc(primary.bestArea || (primary.areas || [])[0] || primary.method || 'Map-wide')}</dd></div>
              <div><dt>Secondary areas</dt><dd>${otherAreas.length ? otherAreas.map(esc).join(' · ') : '<span class="muted">None recorded</span>'}</dd></div>
              <div><dt>Known container types</dt><dd>${it.containers.length ? it.containers.map(esc).join(' · ') : '<span class="muted">Not verified</span>'}</dd></div>
              <div><dt>Source method</dt><dd>${esc(primary.method || '—')}</dd></div>
              ${it.lootZones.length ? `<div><dt>Loot zone type</dt><dd>${it.lootZones.map(z => `<span class="zone-chip">${esc(z)}</span>`).join('')} ${TRN.confChip('VERIFIED COMMUNITY')}</dd></div>` : ''}
              ${it.arcSources.length ? `<div><dt>ARC sources</dt><dd>${it.arcSources.map(esc).join(' · ')}</dd></div>` : ''}
            </dl>
          </div>
          ${locs.length > 1 ? `<div class="other-maps"><span>Also reported on</span>${[...new Set(locs.slice(1).map(l => l.map))].map(m => TRN.data.mapLink(m)).join('')}</div>` : ''}
          <a class="btn btn-primary" href="map.html?id=${encodeURIComponent(primary.map)}">${TRN.icon('map')} Explore ${esc(TRN.data.mapName(primary.map))}</a>`
          : `<div class="where-unknown">${TRN.icon('warning')}<div><strong>No verified map location yet.</strong><p>${(it.locations || [])[0]?.method ? esc(it.locations[0].method) : 'This record has core data only. Map-level spawn reports have not been verified for it.'}</p>
            ${it.lootZones.length ? `<p>Known loot zone type: ${it.lootZones.map(z => `<span class="zone-chip">${esc(z)}</span>`).join('')} ${TRN.confChip('VERIFIED COMMUNITY')}</p>` : ''}
            ${it.arcSources.length ? `<p>ARC sources: ${it.arcSources.map(esc).join(' · ')}</p>` : ''}</div></div>`}
        </section>

        <section class="panel">
          <header class="panel-head"><span class="eyebrow">${TRN.icon('recycle')} RECYCLING / SALVAGE</span><h2>${it.recyclable ? `${esc(it.name)} recycles into` : 'Recycling'}</h2></header>
          <div class="io-grid">
            <div><h4>Recycles into</h4>${it.recycleOutputs.length ? `<div class="io-list">${it.recycleOutputs.map(o => ioRow(o)).join('')}</div>` : '<p class="muted">Not recyclable / no data.</p>'}</div>
            <div><h4>Salvages in raid into</h4>${it.salvageOutputs.length ? `<div class="io-list">${it.salvageOutputs.map(o => ioRow(o)).join('')}</div>` : '<p class="muted">No salvage data.</p>'}</div>
            <div><h4>Recycled from</h4>${recFrom.length ? `<div class="io-list">${recFrom.slice(0, 6).map(x => ioRow({ itemId: x.id, quantity: x.recycleOutputs.find(r => r.itemId === it.id).quantity }, true)).join('')}</div>` : '<p class="muted">No items recycle into this.</p>'}</div>
          </div>
          ${bar('Recycling utility', sRec, `${sRec}/100`, 'teal')}
        </section>

        <section class="panel two-up">
          <div><header class="panel-head"><span class="eyebrow">${TRN.icon('route')} QUESTS</span><h3>Used in quests</h3></header>
            ${questUses.length ? questUses.map(({ q, n }) => `<div class="use-row"><strong>${esc(q.name)}</strong><span>${esc(q.trader || '')}${q.maps.length ? ' · ' + q.maps.map(m => TRN.data.mapName(m)).join(', ') : ''}</span><b>×${n}</b></div>`).join('') : '<p class="muted">Not required by any recorded quest.</p>'}</div>
          <div><header class="panel-head"><span class="eyebrow">${TRN.icon('project')} PROJECTS</span><h3>Used in projects</h3></header>
            ${projUses.length ? projUses.map(({ p, s, q }) => `<div class="use-row"><strong>${TRN.data.projectLink(p.id)}</strong><span>Stage ${s.stage}: ${esc(s.name)}</span>${TRN.statusChip(p.status)}<b>×${q}</b></div>`).join('') : '<p class="muted">Not required by any recorded project.</p>'}</div>
        </section>

        <section class="panel">
          <header class="panel-head"><span class="eyebrow">${TRN.icon('crafting')} CRAFTING</span><h3>Crafting & workshop</h3></header>
          <div class="io-grid">
            <div><h4>Used to craft (${it.craftingUses.length})</h4>${it.craftingUses.length ? `<div class="tag-cloud">${it.craftingUses.map(id => TRN.data.itemLink(id)).join('')}</div>` : '<p class="muted">No recorded recipes use this.</p>'}</div>
            <div><h4>Recipe</h4>${it.recipe.length ? `<div class="io-list">${it.recipe.map(o => ioRow(o)).join('')}</div><small class="muted">${esc([].concat(it.craftBench || []).join(" / "))}</small>` : '<p class="muted">Not craftable.</p>'}</div>
            <div><h4>Workshop upgrades</h4>${it.workshopUses.length ? it.workshopUses.map(w => { const [st, lv] = w.split(':'); return `<span class="zone-chip">${esc((D().workshop || []).find(s => s.id === st)?.name || st)} L${esc(lv)}</span>`; }).join('') : '<p class="muted">None recorded.</p>'}</div>
          </div>
        </section>

        <section class="panel two-up">
          <div><header class="panel-head"><span class="eyebrow">${TRN.icon('squad')} ACTIVE LOOT HUNTS</span><h3>${myHunts.length} hunting this now</h3></header>
            ${myHunts.length ? myHunts.map(h => `<a class="use-row link-row" href="hunts.html?item=${encodeURIComponent(it.id)}#${esc(h.id)}"><strong>${esc(h.displayName)}</strong><span>${TRN.data.mapName(h.mapId)} · ${esc(h.region)} · ${esc(h.platform)}</span>${TRN.statusChip(h.status)}</a>`).join('') : '<p class="muted">No open hunts for this item.</p>'}
            <a class="btn btn-ghost btn-sm" href="hunts.html?new=${encodeURIComponent(it.id)}">+ Start a hunt</a></div>
          <div><header class="panel-head"><span class="eyebrow">${TRN.icon('trade')} TRADE INTEREST</span><h3>${myTrades.length} open request${myTrades.length === 1 ? '' : 's'}</h3></header>
            ${myTrades.length ? myTrades.map(t => `<a class="use-row link-row" href="trade.html?item=${encodeURIComponent(it.id)}#${esc(t.id)}"><strong>${esc(t.displayName)}</strong><span>${t.lookingFor.some(l => l.itemId === it.id) ? 'Looking for' : 'Offering'} · ${esc(t.region)}</span>${t.openToOffers ? '<span class="status-chip status-open">OPEN TO OFFERS</span>' : ''}</a>`).join('') : '<p class="muted">No open trade requests mention this item.</p>'}
            <a class="btn btn-ghost btn-sm" href="trade.html?new=${encodeURIComponent(it.id)}">+ Post a request</a></div>
        </section>
      </div>

      <aside class="item-side">
        <section class="panel">
          <header class="panel-head"><span class="eyebrow">${TRN.icon('value')} VALUE BREAKDOWN</span></header>
          <div class="stat-tiles"><div><small>Merchant value</small><strong>${TRN.num(it.sellValue)}</strong><span>coins</span></div><div><small>Weight</small><strong>${it.weight ?? '—'}</strong><span>kg</span></div><div><small>Stack</small><strong>${it.stackSize ?? '—'}</strong><span>max</span></div></div>
          ${bar('Merchant value', sV, `${sV}/100`)}
          ${bar('Finding difficulty', sDiff, `${TRN.diffLabel(it.difficulty)} · ${it.difficulty}/10`)}
          ${bar('Current demand', sD, `${TRN.demandLabel(it.demand)} · ${it.demand}/10`)}
          ${bar('Recycling utility', sRec, `${sRec}/100`, 'teal')}
          ${bar('Quest utility', sQ, `${sQ}/100`, 'teal')}
          ${bar('Project utility', sP, `${sP}/100`, 'teal')}
          ${bar('Crafting utility', sC, `${sC}/100`, 'teal')}
          ${bar('Raider Network Intel Score', it.intelScore, `${it.intelScore} · ${TRN.intelBand(it.intelScore)}`, 'total ' + TRN.intelClass(it.intelScore))}
          <p class="method-note">${TRN.confChip('NETWORK ESTIMATE')} Weighted: 20% rarity · 20% demand · 15% quest · 15% project · 15% recycling/crafting · 10% difficulty · 5% value. Precomputed ${esc(D().meta.intelScore.asOf)}; becomes live later.</p>
        </section>
        <section class="panel">
          <header class="panel-head"><span class="eyebrow">${TRN.icon('loot-intel')} SOURCES & CONFIDENCE</span></header>
          <ul class="source-list">${it.sources.map(id => { const s = src(id); return `<li>${TRN.confChip(s.confidence)}<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a></li>`; }).join('')}</ul>
          <dl class="kv kv-tight"><div><dt>Core facts</dt><dd>${TRN.confChip(D().meta.defaults.coreConfidence)}</dd></div><div><dt>Locations</dt><dd>${TRN.confChip(it.locationConfidence)}</dd></div><div><dt>Scores</dt><dd>${TRN.confChip('NETWORK ESTIMATE')}</dd></div>
          <div><dt>Source updated</dt><dd>${esc(it.sourceUpdated || '—')}</dd></div><div><dt>Added in patch</dt><dd>${esc(it.addedIn || '—')}</dd></div></dl>
          <p class="method-note">${esc(D().meta.defaults.imageNote)}</p>
        </section>
      </aside>
    </div>`;
  }
  function ioRow(o, reverse) {
    const x = TRN.data.item(o.itemId);
    return `<a class="io-row" href="item.html?id=${encodeURIComponent(o.itemId)}"><img src="${TRN.img(x?.image)}" alt="" loading="lazy"><span>${esc(TRN.data.itemName(o.itemId))}</span><b>${reverse ? 'gives ' : ''}×${o.quantity}</b></a>`;
  }

  TRN.loot = { itemCard, miniItem, bestSpot, setupLootPage, setupItemPage };
})();
