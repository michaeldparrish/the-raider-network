/* The Raider Network v5 — map browser (maps.html), dynamic map detail (map.html?id=) and shared map cards. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN, D = () => TRN.db;
  const itemsOn = id => D().items.filter(i => i.maps.includes(id));
  const pips = n => `<span class="pips" title="${n}/5">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= n ? 'on' : ''}"></i>`).join('')}</span>`;
  const conditionFor = id => (D().conditions?.demoSchedule || []).find(c => c.mapId === id);

  function mapCard(m, hunts = [], opts = {}) {
    const linked = itemsOn(m.id).length, active = hunts.filter(h => h.mapId === m.id && h.status === 'open').length, cond = conditionFor(m.id);
    return `<article class="map-card ${opts.compact ? 'map-card--compact' : ''}">
      <a class="map-card__media" href="map.html?id=${encodeURIComponent(m.id)}"><img src="${TRN.img(m.image)}" alt="${esc(m.name)}" loading="lazy">
        ${cond ? `<span class="cond-flag cond-${esc(cond.severity)}"><img src="${TRN.IMG}ui/condition-${esc(cond.severity)}.png" alt="">${esc(cond.condition)}</span>` : ''}</a>
      <div class="map-card__body">
        <h3><a href="map.html?id=${encodeURIComponent(m.id)}">${esc(m.name)}</a></h3>
        <p>${esc(opts.compact ? m.lootProfile : m.overview)}</p>
        <dl class="kv">
          <div><dt>${TRN.icon('danger')}Difficulty</dt><dd>${pips(m.difficulty)} ${esc(m.difficultyLabel)}</dd></div>
          ${opts.compact ? '' : `<div><dt>${TRN.icon('map')}Environment</dt><dd>${esc(m.environment)}</dd></div>`}
          <div><dt>${TRN.icon('inventory')}Loot profile</dt><dd>${esc(m.lootProfile)}</dd></div>
          ${opts.compact ? '' : `<div><dt>${TRN.icon('loot-intel')}Loot Intel</dt><dd><a href="loot.html?map=${encodeURIComponent(m.id)}">${linked} linked records</a></dd></div>
          <div><dt>${TRN.icon('squad')}Active hunts</dt><dd>${active}</dd></div>`}
        </dl>
        ${opts.compact ? `<a class="btn btn-outline btn-block" href="map.html?id=${encodeURIComponent(m.id)}">Explore Map ${TRN.svg('arrow')}</a>`
          : `<div class="btn-pair"><a class="btn btn-outline" href="map.html?id=${encodeURIComponent(m.id)}">Explore Map ${TRN.svg('arrow')}</a><a class="btn btn-ghost" href="loot.html?map=${encodeURIComponent(m.id)}">${TRN.icon('loot-intel')} View Loot</a></div>`}
      </div></article>`;
  }

  function incomingCard(m) {
    return `<article class="map-card map-card--incoming"><a class="map-card__media" href="map.html?id=${encodeURIComponent(m.id)}"><img src="${TRN.img(m.image)}" alt="" loading="lazy"><span class="cond-flag">INCOMING</span></a>
      <div class="map-card__body"><h3><a href="map.html?id=${encodeURIComponent(m.id)}">${esc(m.name)}</a></h3><p>${esc(m.overview)}</p>
      <dl class="kv"><div><dt>${TRN.icon('time')}Status</dt><dd>${esc(m.releaseNote || 'Not live yet')}</dd></div><div><dt>${TRN.icon('map')}Map data</dt><dd>None yet</dd></div></dl></div></article>`;
  }

  async function setupMapsPage() {
    const grid = $('#mapGrid'); if (!grid) return;
    const hunts = await TRN.store.listHunts();
    const live = D().maps.filter(m => m.status === 'live'), incoming = D().maps.filter(m => m.status !== 'live');
    grid.innerHTML = live.map(m => mapCard(m, hunts)).join('') + incoming.map(incomingCard).join('');
    $('#mapCount').textContent = live.length;
    $('#routeList').innerHTML = D().routes.map(r => TRN.maps.routeCard(r)).join('');
  }

  function routeCard(r, big = false) {
    const m = TRN.data.map(r.mapId);
    return `<article class="route-card ${big ? 'route-card--big' : ''}" id="${esc(r.id)}">
      <div class="route-card__media"><img src="${TRN.img(r.image)}" alt="" loading="lazy">${r.featured ? '<span class="flag-chip">FEATURED ROUTE</span>' : ''}</div>
      <div class="route-card__body">
        <small class="eyebrow">${esc((m?.name || '').toUpperCase())}</small>
        <h3>${esc((m?.name || '').toUpperCase())} — ${esc(r.name.toUpperCase())}</h3>
        <p>${esc(r.summary)}</p>
        <div class="route-stats">
          <div>${TRN.icon('inventory')}<span>Loot Rating<b>${r.lootRating}/10</b></span></div>
          <div>${TRN.icon('danger')}<span>Risk<b>${r.risk}/10</b></span></div>
          <div>${TRN.icon('squad')}<span>Solo Friendly<b>${r.soloFriendly}/10</b></span></div>
          <div>${TRN.icon('time')}<span>Est. Time<b>${esc(r.estimatedTime)}</b></span></div>
        </div>
        ${big ? `<div class="route-targets"><span>Targets</span>${r.targetItems.map(id => TRN.data.itemLink(id)).join('')}</div><ol class="route-steps">${r.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>` : `<div class="route-targets"><span>Targets</span>${r.targetItems.map(id => TRN.data.itemLink(id)).join('')}</div>`}
        <div class="btn-row"><a class="btn btn-primary" href="map.html?id=${encodeURIComponent(r.mapId)}#routes">${TRN.icon('route')} View Route</a><a class="btn btn-ghost" href="hunts.html?map=${encodeURIComponent(r.mapId)}">${TRN.icon('squad')} Find Squad</a></div>
        <small class="editorial-note">${TRN.confChip(r.confidence)} Editorial demo route — ratings are Raider Network estimates.</small>
      </div></article>`;
  }

  /* ================================================================ MAP DETAIL (v5.2: map-first)
     Order: cinematic hero → actual base map (+ MetaForge overlay & controls) → POIs → loot on this map → hunts/trades → routes.
     Base map + per-map calibration come from maps.json → mapImage.levels[] (built by tools/build_data.py).
     Markers come from the cached data/maps/<map>-markers.json. MetaForge is never called from the browser. */
  const CAT_COLOR = { containers: '#ffb020', arc: '#ff5149', quests: '#c4a0ff', locations: '#19d3c5', events: '#4aa8ff', nature: '#3fd07a' };
  const human = s => String(s || '').replace(/[-_]+/g, ' ').trim().replace(/\b\w/g, c => c.toUpperCase());

  async function setupMapPage() {
    const root = $('#mapRoot'); if (!root) return;
    const m = TRN.data.map(TRN.param('id'));
    if (!m) { root.innerHTML = `<div class="page-shell"><div class="empty-state big">${TRN.icon('warning')}<h1>Map not found</h1><a class="btn btn-primary" href="maps.html">Browse maps</a></div></div>`; return; }
    document.title = `${m.name} — Maps — The Raider Network`;
    const live = m.status === 'live';
    const [hunts, trades] = await Promise.all([TRN.store.listHunts(), TRN.store.listTrades()]);
    TRN.trades.prep(trades);
    const all = itemsOn(m.id);
    const top = [...all].filter(i => !i.locations.some(l => l.map === m.id && l.common)).sort((a, b) => b.intelScore - a.intelScore).slice(0, 8);
    const frequent = all.filter(i => i.locations.some(l => l.map === m.id && l.common)).sort((a, b) => b.intelScore - a.intelScore).slice(0, 8);
    const projRel = all.filter(i => i.projects.some(p => TRN.db.idx.project.get(p)?.status !== 'HISTORICAL')).sort((a, b) => b.intelScore - a.intelScore).slice(0, 8);
    const mapHunts = hunts.filter(h => h.mapId === m.id && h.status !== 'completed');
    const ids = new Set(all.map(i => i.id));
    const mapTrades = trades.filter(t => t.status === 'open' && t.lookingFor.some(l => ids.has(l.itemId)));
    const routes = D().routes.filter(r => r.mapId === m.id);
    const arcs = D().arcs.filter(a => a.maps.includes(m.id));
    const quests = D().quests.filter(q => q.maps.includes(m.id));
    const cond = conditionFor(m.id);
    const miniList = list => list.length ? `<div class="mini-list">${list.map(i => TRN.loot.miniItem(i)).join('')}</div>` : '<p class="muted">No linked records yet.</p>';
    const lootHref = `loot.html?map=${encodeURIComponent(m.id)}`;

    root.innerHTML = `
    <section class="map-hero map-hero--compact">
      <img class="map-hero__img" src="${TRN.img(m.image)}" alt="">
      <div class="map-hero__shade"></div>
      <div class="map-hero__copy">
        <nav class="crumbs"><a href="maps.html">Maps</a><span>/</span><b>${esc(m.name)}</b></nav>
        <span class="eyebrow">${live ? esc(m.environment.toUpperCase()) : 'INCOMING MAP'}</span>
        <h1>${esc(m.name)}</h1>
        <p class="lede">${esc(m.overview)}</p>
        <div class="chip-row">${live ? `<span class="hero-chip">${TRN.icon('danger')} ${esc(m.difficultyLabel)} ${pips(m.difficulty)}</span><span class="hero-chip">${TRN.icon('inventory')} ${esc(m.lootProfile)}</span><span class="hero-chip">${TRN.icon('loot-intel')} ${all.length} Loot Intel records</span><span class="hero-chip">${TRN.icon('squad')} ${mapHunts.length} active hunts</span>` : `<span class="hero-chip">${TRN.icon('time')} ${esc(m.releaseNote || 'Not live yet')}</span>`}</div>
        ${m.unlockNote ? `<p class="small-note">${esc(m.unlockNote)}</p>` : ''}
        ${live ? `<div class="btn-row"><a class="btn btn-primary" href="#map-view">${TRN.icon('map')} View Map</a><a class="btn btn-ghost" href="${lootHref}">${TRN.icon('loot-intel')} View All Loot on This Map</a><a class="btn btn-ghost" href="#hunts">${TRN.icon('squad')} View Active Hunts</a></div>` : ''}
      </div>
      ${cond ? `<aside class="cond-panel"><small>MAP CONDITION · DEMO</small><img src="${TRN.IMG}ui/condition-${esc(cond.severity)}.png" alt=""><strong>${esc(cond.condition)}</strong><span>${esc(cond.window)}</span></aside>` : ''}
    </section>
    <div class="page-shell">
      ${mapSection(m)}
      ${live ? `
      <section class="block" id="pois"><div class="section-title-row"><div><span class="eyebrow">KEY LOCATIONS / POIs</span><h2>Points of interest</h2></div></div>
        <div class="poi-grid">${m.pois.map(p => `<article class="poi-card"><div class="poi-card__media"><img src="${TRN.img(p.image)}" alt="" loading="lazy"><h3>${esc(p.name)}</h3></div><div class="poi-card__body">${TRN.confChip(p.confidence)}<small class="muted">${esc(p.basis)}</small><div class="poi-items">${p.items.map(id => { const it = TRN.data.item(id); return it ? `<a href="item.html?id=${encodeURIComponent(id)}" class="poi-item rarity-edge-${esc(it.rarity.toLowerCase())}"><img src="${TRN.img(it.image)}" alt="" loading="lazy">${esc(it.name)}</a>` : ''; }).join('')}</div></div></article>`).join('')}</div>
      </section>
      <section class="block" id="loot">
        <div class="section-title-row"><div><span class="eyebrow">${TRN.icon('loot-intel')} ITEMS FOUND ON THIS MAP</span><h2>Top loot on ${esc(m.shortName)}</h2><p class="muted">${all.length} Loot Intel records link to this map.</p></div>
          <a class="btn btn-primary" href="${lootHref}">${TRN.icon('search')} View All Loot on This Map</a></div>
        <div class="three-up">
          <div class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('rarity')} TOP LOOT ON THIS MAP</span></header>${miniList(top)}</div>
          <div class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('inventory')} FREQUENTLY FOUND</span></header>${miniList(frequent)}<small class="muted">Common ARC drops and mapped resources.</small></div>
          <div class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('project')} PROJECT-RELEVANT LOOT</span></header>${miniList(projRel)}</div>
        </div>
      </section>
      <section class="block two-up" id="hunts">
        <div class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('squad')} ACTIVE LOOT HUNTS</span><h3>${mapHunts.length} on ${esc(m.shortName)}</h3></header>
          ${mapHunts.length ? `<div class="hunt-grid hunt-grid--tight">${mapHunts.map(h => TRN.hunts.huntCard(h)).join('')}</div>` : '<p class="muted">No hunts posted for this map.</p>'}
          <a class="btn btn-ghost btn-sm" href="hunts.html?map=${encodeURIComponent(m.id)}&new=">+ Start a hunt here</a></div>
        <div class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('trade')} TRADE INTEREST</span><h3>Requests for loot found here</h3></header>
          ${mapTrades.length ? mapTrades.map(t => TRN.trades.tradeRow(t)).join('') : '<p class="muted">No open requests for loot from this map.</p>'}</div>
      </section>
      <section class="block" id="overview"><div class="section-title-row"><div><span class="eyebrow">FIELD BRIEF</span><h2>ARC presence &amp; quests</h2></div><span class="editorial-note">${TRN.confChip('NETWORK ESTIMATE')} Overview, difficulty and loot profile are Raider Network editorial summaries.</span></div>
        <div class="brief-grid">
          <div class="panel"><h4>${TRN.icon('danger')} ARC presence</h4>${arcs.length ? `<div class="tag-cloud">${arcs.map(a => `<span class="zone-chip" title="${esc(a.threat || '')}">${esc(a.name)}</span>`).join('')}</div>${TRN.confChip('VERIFIED COMMUNITY')}` : '<p class="muted">No ARC spawn data in the current snapshot.</p>'}</div>
          <div class="panel"><h4>${TRN.icon('route')} Quests on this map</h4>${quests.length ? `<ul class="plain-list">${quests.slice(0, 10).map(q => `<li><strong>${esc(q.name)}</strong> <span class="muted">${esc(q.trader || '')}</span>${q.requiredItems.length ? ` — needs ${q.requiredItems.map(r => TRN.data.itemLink(r.itemId)).join(', ')}` : ''}</li>`).join('')}</ul>${quests.length > 10 ? `<small class="muted">+${quests.length - 10} more</small>` : ''}` : '<p class="muted">None recorded.</p>'}</div>
        </div>
      </section>
      <section class="block" id="routes"><div class="section-title-row"><div><span class="eyebrow">ROUTES / GUIDES</span><h2>Routes on ${esc(m.name)}</h2></div></div>
        ${routes.length ? `<div class="route-list">${routes.map(r => routeCard(r, true)).join('')}</div>` : '<p class="muted panel">No routes written for this map yet. Route submissions are planned for a later version.</p>'}
      </section>
      <div class="gallery-strip gallery-strip--inline">${(m.gallery || []).map(g => `<img src="${TRN.img(g)}" alt="${esc(m.name)} scene" loading="lazy">`).join('')}</div>`
      : `<p class="small-note">${(m.sources || []).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a>`).join(' · ')}</p>`}
    </div>`;
    TRN.hunts.wireHuntButtons(root); TRN.trades.wireTradeButtons(root);
    initMapViewer(m);
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }

  /* ---------------------------------------------------------------- map section markup */
  function mapSection(m) {
    const mi = m.mapImage || { levels: [] }, md = m.markerData, hasMarkers = md && md.status === 'live';
    const lv = mi.levels || [];
    const attr = `<span class="mf-attr">${hasMarkers ? `Markers: <a href="https://metaforge.app/arc-raiders" target="_blank" rel="noopener">MetaForge</a> community data (cached ${esc((md.fetchedAt || '').slice(0, 10))}).` : ''} ${mi.source ? `Map image: <a href="${esc(mi.source.url)}" target="_blank" rel="noopener">RaidTheory / arctracker</a> · © Embark Studios.` : ''}</span>`;
    if (!lv.length) {
      return `<section class="block map-intel" id="map-view"><div class="section-title-row"><div><span class="eyebrow">${TRN.icon('map')} LEVEL MAP</span><h2>Map &amp; topography</h2></div></div>
        <div class="map-placeholder"><img src="${TRN.img(m.image)}" alt="" loading="lazy"><div><strong>${m.status === 'live' ? 'Base map image coming soon' : 'Map not released yet'}</strong>
        <p>${m.status === 'live' ? 'The level map for this location has not been added yet. Marker data is still listed below.' : 'No level map, POI or marker data exists until this map ships. The page is configured and ready — adding the image and calibration requires no layout changes.'}</p></div></div></section>`;
    }
    return `<section class="block map-intel" id="map-view">
      <div class="section-title-row"><div><span class="eyebrow">${TRN.icon('map')} LEVEL MAP</span><h2>Map &amp; topography</h2>
        <p class="muted">${hasMarkers ? `${TRN.num(md.count)} community markers available as an overlay` : 'No marker data cached for this map.'}${mi.calibrated ? '' : (hasMarkers ? ' · <b class="warn-text">overlay disabled until this map is calibrated</b>' : '')}</p></div>${attr}</div>
      <div class="mv">
        <div class="mv-bar">
          ${lv.length > 1 ? `<div class="mv-levels" role="tablist">${lv.map((l, i) => `<button class="mv-level ${i === 0 ? 'on' : ''}" data-level="${i}" role="tab">${esc(l.label)}</button>`).join('')}</div>` : ''}
          <label class="mv-switch ${mi.calibrated && hasMarkers ? '' : 'is-disabled'}"><input type="checkbox" id="mvOverlay" ${mi.calibrated && hasMarkers ? 'checked' : 'disabled'}><span></span>Marker overlay</label>
          <div class="mv-zoom"><button class="icon-btn" id="mvOut" aria-label="Zoom out">−</button><button class="icon-btn" id="mvReset" aria-label="Reset view">⤢</button><button class="icon-btn" id="mvIn" aria-label="Zoom in">+</button><button class="icon-btn" id="mvFull" aria-label="Full screen">⛶</button></div>
        </div>
        <div class="mv-stage" id="mvStage" tabindex="0" aria-label="${esc(m.name)} level map. Drag to pan, scroll or use +/− to zoom.">
          <div class="mv-world" id="mvWorld"><img id="mvImg" alt="${esc(m.name)} level map" decoding="async"></div>
          <canvas id="mvCanvas"></canvas><div class="mi-tip hidden" id="miTip"></div>
          <div class="mv-hint">Drag to pan · scroll / pinch / +− to zoom</div>
          <div class="mv-loading" id="mvLoading">Loading map…</div>
        </div>
        ${hasMarkers ? `<div class="mv-controls">
          <div class="mv-cats"><span class="mv-label">SHOW</span><div class="mi-cats" id="miCats"></div><button class="text-btn" id="miAll">Show all</button><button class="text-btn" id="miNone">Hide all</button></div>
          <div class="mv-filters">
            <div class="search-field">${TRN.svg('search')}<input id="miSearch" placeholder="Search markers (locker, hatch, with a view…)" aria-label="Search markers"></div>
            <select id="miSub" class="input" aria-label="Subcategory"><option value="">All subcategories</option></select>
            <label class="flag-toggle"><input type="checkbox" id="miLinked"><span>${TRN.icon('loot-intel')}Loot Intel linked</span></label>
            <label class="flag-toggle"><input type="checkbox" id="miLocked"><span>${TRN.icon('warning')}Locked doors</span></label>
          </div>
        </div>
        <details class="mv-listwrap" id="mvListWrap"><summary><span id="miCount"></span> — marker list</summary><div class="mi-list" id="miList" role="list"></div></details>` : ''}
        <p class="small-note mv-cal">${mi.calibrated ? `Calibration: ${lv.map(l => `${esc(l.label)} — ${l.calibration.points} control points, RMS ${l.calibration.rmsPx}px on a ${l.width}px image`).join(' · ')}.` : 'This map has not been calibrated against MetaForge coordinates yet, so markers are not drawn on the image (no guessing). Markers remain searchable in the list.'}</p>
      </div>
    </section>`;
  }

  /* ---------------------------------------------------------------- viewer */
  async function initMapViewer(m) {
    const stage = $('#mvStage'); if (!stage) return;
    const mi = m.mapImage, levels = mi.levels, md = m.markerData;
    const img = $('#mvImg'), world = $('#mvWorld'), cv = $('#mvCanvas'), ctx = cv.getContext('2d'), tip = $('#miTip');
    let L = 0, z = 1, px = 0, py = 0, base = 1;            // level, zoom, pan (screen px), fit scale (image px -> screen px)
    let markers = [], view = [], sel = null, overlay = !!$('#mvOverlay')?.checked;
    const lvl = () => levels[L];
    const sw = () => stage.clientWidth, sh = () => stage.clientHeight;

    function loadLevel(i) {
      L = i; const l = lvl(); $('#mvLoading').classList.remove('hidden');
      img.onload = () => { $('#mvLoading').classList.add('hidden'); fit(); };
      img.src = (sw() < 900 ? l.srcSmall : l.src);
      stage.style.aspectRatio = `${l.width} / ${l.height}`;
      $$('.mv-level').forEach(b => b.classList.toggle('on', +b.dataset.level === i));
      apply();
    }
    function fit() { base = sw() / lvl().width; z = 1; px = 0; py = 0; draw(); }
    function clampPan() {
      const W = lvl().width * base * z, H = lvl().height * base * z;
      px = Math.min(0, Math.max(sw() - W, px)); py = Math.min(0, Math.max(sh() - H, py));
    }
    function zoomAt(f, cx = sw() / 2, cy = sh() / 2) {
      const nz = Math.min(8, Math.max(1, z * f)); const k = nz / z;
      px = cx - (cx - px) * k; py = cy - (cy - py) * k; z = nz; clampPan(); draw();
    }
    /* MetaForge coord -> image px (per-level calibration) -> screen px */
    const toImg = mk => { const l = lvl(); return [l.scaleX * mk.x + l.offsetX, l.scaleY * mk.y + l.offsetY]; };
    const toScr = mk => { const [ix, iy] = toImg(mk); return [ix * base * z + px, iy * base * z + py]; };
    const onLevel = mk => { const l = lvl(); return l.layer == null || mk.layer === 'all' || mk.layer === l.layer; };

    function draw() {
      world.style.width = lvl().width * base + 'px';
      world.style.transform = `translate(${px}px,${py}px) scale(${z})`;
      const dpr = window.devicePixelRatio || 1;
      cv.width = Math.round(sw() * dpr); cv.height = Math.round(sh() * dpr); cv.style.width = sw() + 'px'; cv.style.height = sh() + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, sw(), sh());
      if (!overlay || !lvl().calibrated) return;
      const r = Math.max(1.5, Math.min(6, (Math.min(1, sw() / 900) * 2.4) + z * 0.7));
      for (const mk of view) {
        if (!onLevel(mk)) continue;
        const [x, y] = toScr(mk); if (x < -8 || y < -8 || x > sw() + 8 || y > sh() + 8) continue;
        const rr = mk.category === 'containers' ? r * 0.72 : r;
        ctx.beginPath(); ctx.arc(x, y, rr + 1.2, 0, 6.283); ctx.fillStyle = 'rgba(0,0,0,.65)'; ctx.fill();   // dark halo for contrast
        ctx.beginPath(); ctx.arc(x, y, rr, 0, 6.283); ctx.fillStyle = CAT_COLOR[mk.category] || '#fff'; ctx.fill();
      }
      if (sel && onLevel(sel)) { const [x, y] = toScr(sel); ctx.lineWidth = 2.5; ctx.strokeStyle = '#fff'; ctx.beginPath(); ctx.arc(x, y, 11, 0, 6.283); ctx.stroke(); ctx.strokeStyle = CAT_COLOR[sel.category]; ctx.beginPath(); ctx.arc(x, y, 15, 0, 6.283); ctx.stroke(); }
    }

    /* pan / zoom input */
    let drag = null, pinch = null;
    stage.addEventListener('pointerdown', e => { if (e.pointerType === 'touch' && e.isPrimary === false) return; drag = { x: e.clientX, y: e.clientY, px, py, moved: false }; stage.setPointerCapture(e.pointerId); });
    stage.addEventListener('pointermove', e => {
      if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true; px = drag.px + dx; py = drag.py + dy; clampPan(); draw(); tip.classList.add('hidden'); return; }
      hover(e);
    });
    stage.addEventListener('pointerup', e => { if (drag && !drag.moved) pick(e); drag = null; });
    stage.addEventListener('pointerleave', () => tip.classList.add('hidden'));
    stage.addEventListener('wheel', e => { e.preventDefault(); const r = stage.getBoundingClientRect(); zoomAt(e.deltaY < 0 ? 1.25 : 0.8, e.clientX - r.left, e.clientY - r.top); }, { passive: false });
    stage.addEventListener('touchstart', e => { if (e.touches.length === 2) { pinch = { d: Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY) }; drag = null; } }, { passive: true });
    stage.addEventListener('touchmove', e => { if (pinch && e.touches.length === 2) { const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); const r = stage.getBoundingClientRect(); zoomAt(d / pinch.d, (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left, (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top); pinch.d = d; } }, { passive: true });
    stage.addEventListener('touchend', () => (pinch = null));
    stage.addEventListener('keydown', e => { const k = { '+': () => zoomAt(1.25), '=': () => zoomAt(1.25), '-': () => zoomAt(0.8), ArrowLeft: () => { px += 60; }, ArrowRight: () => { px -= 60; }, ArrowUp: () => { py += 60; }, ArrowDown: () => { py -= 60; } }[e.key]; if (k) { e.preventDefault(); k(); clampPan(); draw(); } });
    $('#mvIn').onclick = () => zoomAt(1.4); $('#mvOut').onclick = () => zoomAt(1 / 1.4); $('#mvReset').onclick = fit;
    $('#mvFull').onclick = () => { const el = stage.closest('.mv'); document.fullscreenElement ? document.exitFullscreen() : (el.requestFullscreen ? el.requestFullscreen() : el.classList.toggle('mv--max')); };
    document.addEventListener('fullscreenchange', () => setTimeout(fit, 60));
    $$('.mv-level').forEach(b => (b.onclick = () => loadLevel(+b.dataset.level)));
    $('#mvOverlay')?.addEventListener('change', e => { overlay = e.target.checked; draw(); });
    new ResizeObserver(TRN.debounce(() => { const old = base; base = sw() / lvl().width; px *= base / old || 1; py *= base / old || 1; clampPan(); draw(); }, 60)).observe(stage);

    function nearest(e, rad) {
      if (!overlay || !lvl().calibrated) return null;
      const r = stage.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      let best = null, bd = rad * rad; for (const mk of view) { if (!onLevel(mk)) continue; const [x, y] = toScr(mk), d = (x - mx) ** 2 + (y - my) ** 2; if (d < bd) { bd = d; best = mk; } }
      return best;
    }
    function hover(e) {
      const b = nearest(e, 10); if (!b) { tip.classList.add('hidden'); return; }
      const r = stage.getBoundingClientRect(); tip.classList.remove('hidden');
      tip.style.left = Math.min(sw() - 200, e.clientX - r.left + 12) + 'px'; tip.style.top = (e.clientY - r.top + 12) + 'px';
      tip.innerHTML = `<strong>${esc(b.label || human(b.subcategory))}</strong><small>${esc(human(b.category))} · ${esc(human(b.subcategory))}${b.locked ? ' · locked' : ''}</small>`;
    }
    function pick(e) { const b = nearest(e, 14); if (!b) return; sel = b; draw(); list(true); }

    /* ---- markers, filters, list */
    if (md?.file) {
      try { markers = (await fetch(md.file).then(r => r.json())).markers; } catch (err) { markers = []; }
    }
    const cats = Object.keys(md?.categories || {});
    const on = new Set(cats.filter(c => c !== 'containers' && c !== 'nature'));      // dense categories start hidden for readability
    const paintCats = () => {
      if (!$('#miCats')) return;
      $('#miCats').innerHTML = cats.map(c => `<button class="mi-cat ${on.has(c) ? 'on' : ''}" data-cat="${c}" style="--c:${CAT_COLOR[c] || '#9aa'}"><i></i>${esc(TRN.db.mapIndex?.categoryLabels?.[c] || human(c))}<b>${TRN.num(md.categories[c])}</b></button>`).join('');
      $$('.mi-cat').forEach(btn => (btn.onclick = () => { on.has(btn.dataset.cat) ? on.delete(btn.dataset.cat) : on.add(btn.dataset.cat); paintCats(); paintSubs(); apply(); }));
    };
    const paintSubs = () => { if (!$('#miSub')) return; const subs = {}; markers.forEach(x => on.has(x.category) && (subs[x.subcategory] = (subs[x.subcategory] || 0) + 1)); const cur = $('#miSub').value; $('#miSub').innerHTML = '<option value="">All subcategories</option>' + Object.entries(subs).sort((a, c) => c[1] - a[1]).map(([k, n]) => `<option value="${esc(k)}" ${k === cur ? 'selected' : ''}>${esc(human(k))} (${n})</option>`).join(''); };
    const linkFor = x => x.links?.itemId ? `<a class="mi-link" href="item.html?id=${encodeURIComponent(x.links.itemId)}">${TRN.icon('loot-intel')}${esc(TRN.data.itemName(x.links.itemId))}</a>`
      : x.links?.questId ? `<a class="mi-link" href="loot.html?quest=${encodeURIComponent(x.links.questId)}">${TRN.icon('route')}${esc(TRN.data.questName(x.links.questId))}</a>`
      : x.links?.arcId ? `<span class="mi-link">${TRN.icon('danger')}${esc(human(x.links.arcId.replace('arc-', '')))} ARC</span>` : '';
    function list(scroll) {
      if (!$('#miList')) return;
      const rows = view.slice(0, 200); if (sel && !rows.includes(sel)) rows.unshift(sel);
      $('#miList').innerHTML = rows.map((x, i) => `<button class="mi-row ${sel === x ? 'sel' : ''}" data-i="${i}" role="listitem"><i style="background:${CAT_COLOR[x.category] || '#9aa'}"></i><span><strong>${esc(x.label || human(x.subcategory))}</strong><small>${esc(human(x.category))} · ${esc(human(x.subcategory))}${x.lootAreas?.length ? ' · ' + esc(x.lootAreas.join(', ')) : ''}${levels.length > 1 && x.layer !== 'all' ? ' · level ' + esc(x.layer) : ''}</small></span>${x.locked ? '<em class="mi-lock">LOCKED</em>' : ''}${linkFor(x)}</button>`).join('')
        + (view.length > 200 ? `<p class="small-note pad">Showing 200 of ${TRN.num(view.length)} — refine the filters to see more.</p>` : '') || '<p class="muted pad">No markers match.</p>';
      $$('.mi-row').forEach(r => (r.onclick = e => {
        if (e.target.closest('a')) return; sel = rows[+r.dataset.i];
        if (levels.length > 1 && sel.layer !== 'all') { const li = levels.findIndex(l => l.layer === sel.layer); if (li > -1 && li !== L) loadLevel(li); }
        if (overlay && lvl().calibrated) { const [ix, iy] = toImg(sel); z = Math.max(z, 3); px = sw() / 2 - ix * base * z; py = sh() / 2 - iy * base * z; clampPan(); stage.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
        draw(); list();
      }));
      $('#miCount').textContent = `${TRN.num(view.length)} of ${TRN.num(markers.length)} markers shown`;
      if (scroll) { $('#mvListWrap').open = true; $('.mi-row.sel')?.scrollIntoView({ block: 'nearest' }); }
    }
    function apply() {
      if (!$('#miSearch')) { view = []; draw(); return; }
      const q = ($('#miSearch').value || '').toLowerCase(), sub = $('#miSub').value, locked = $('#miLocked').checked, linked = $('#miLinked').checked;
      view = markers.filter(x => on.has(x.category) && (!sub || x.subcategory === sub) && (!locked || x.locked) && (!linked || x.links) &&
        (!q || (x.label + ' ' + x.subcategory + ' ' + x.category).toLowerCase().replace(/[-_]/g, ' ').includes(q)));
      view.sort((a, c) => (a.category > c.category ? 1 : a.category < c.category ? -1 : (a.label || a.subcategory).localeCompare(c.label || c.subcategory)));
      if (sel && !view.includes(sel)) sel = null;
      draw(); list();
    }
    if ($('#miAll')) {
      $('#miAll').onclick = () => { cats.forEach(c => on.add(c)); paintCats(); paintSubs(); apply(); };
      $('#miNone').onclick = () => { on.clear(); paintCats(); paintSubs(); apply(); };
      ['miSearch', 'miSub', 'miLocked', 'miLinked'].forEach(id => $('#' + id).addEventListener('input', TRN.debounce(apply, 80)));
    }
    paintCats(); paintSubs(); loadLevel(0);
  }

  TRN.maps = { mapCard, routeCard, setupMapsPage, setupMapPage, conditionFor, pips };
})();
