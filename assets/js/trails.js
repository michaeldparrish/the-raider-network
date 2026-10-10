/* The Raider Network v6.3 — Loot Trails (persistent, collaborative, private by default).
 * All data lives on the server (D1 + private R2 screenshots). Nothing here uses browser storage for trail data.
 * Every permission is enforced by the API; the UI only hides controls a Raider cannot use. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  const MiB = 1024 * 1024, MAX_IMAGE = 20 * MiB, MAX_PAIR = 40 * MiB;
  const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
  const SHOT = { MAP_POSITION: 'Map position', LOOT: 'Loot' };
  const SHOT_HELP = { MAP_POSITION: 'Your in-game map showing your position arrow', LOOT: 'The item or loot you found' };
  const enc = encodeURIComponent;

  /* ---------------------------------------------------------------- API (server routes in functions/_lib/trails) */
  const A = {
    list: () => TRN.api.get('/trails'),
    invites: () => TRN.api.get('/me/trail-invitations'),
    get: id => TRN.api.get('/trails/' + enc(id)),
    create: b => TRN.api.post('/trails', b),
    invite: (id, username) => TRN.api.post(`/trails/${enc(id)}/invitations`, { username }),
    respond: (id, decision) => TRN.api.post(`/trails/${enc(id)}/invitations/respond`, { decision }),
    removeMember: (id, username) => TRN.api.post(`/trails/${enc(id)}/members/remove`, { username }),
    session: (id, b) => TRN.api.post(`/trails/${enc(id)}/sessions`, b),
    endSession: (id, sid) => TRN.api.post(`/trails/${enc(id)}/sessions/${enc(sid)}/end`),
    discovery: (id, b) => TRN.api.post(`/trails/${enc(id)}/discoveries`, b),
    review: (id, did, status) => TRN.api.post(`/trails/${enc(id)}/discoveries/${enc(did)}/review`, { status }),
    publish: (id, did, publish) => TRN.api.post(`/trails/${enc(id)}/discoveries/${enc(did)}/publish`, { publish }),
    visibility: (id, visibility) => TRN.api.post(`/trails/${enc(id)}/visibility`, { visibility }),
    progress: (id, did, completed) => TRN.api.post(`/trails/${enc(id)}/discoveries/${enc(did)}/progress`, { completed }),
    removeImage: (id, did, type) => TRN.api.del(`/trails/${enc(id)}/discoveries/${enc(did)}/images/${type}`),
    imageUrl: (id, did, type, v) => `/api/trails/${enc(id)}/discoveries/${enc(did)}/images/${type}${v ? '?v=' + enc(v) : ''}`,
    /* Raw upload with progress (XHR). Same CSRF header as every other change. */
    upload(id, did, type, file, onProgress) {
      return new Promise((resolve, reject) => {
        const x = new XMLHttpRequest();
        x.open('POST', `/api/trails/${enc(id)}/discoveries/${enc(did)}/images/${type}`);
        x.withCredentials = true;
        x.setRequestHeader('X-TRN-CSRF', '1'); x.setRequestHeader('Content-Type', file.type); x.setRequestHeader('Accept', 'application/json');
        x.upload.onprogress = e => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total); };
        x.onload = () => {
          let d = null; try { d = JSON.parse(x.responseText); } catch { /* not JSON */ }
          if (x.status >= 200 && x.status < 300) return resolve(d);
          const msg = x.status === 409 ? 'A screenshot of this type is already saved. Remove it first if you want to replace it.'
            : x.status === 413 ? 'That screenshot is larger than 20 MB.' : d?.error?.message || `Upload failed (${x.status}).`;
          reject(Object.assign(new Error(msg), { status: x.status }));
        };
        x.onerror = () => reject(new Error('Upload failed: the connection dropped. Try again.'));
        x.send(file);
      });
    },
  };

  /* ---------------------------------------------------------------- helpers */
  const STATUS_CHIP = { PENDING: ['Pending review', 'status-awaiting'], APPROVED: ['Approved', 'status-open'], REJECTED: ['Rejected', 'status-full'] };
  const chip = (s, label) => { const [t, c] = STATUS_CHIP[s] || [label || s, 'status-closed']; return `<span class="status-chip ${c}">${esc(String(label || t).toUpperCase())}</span>`; };
  const visChip = v => v === 'PUBLIC' ? '<span class="status-chip status-completed">PUBLIC</span>' : '<span class="status-chip status-closed">PRIVATE</span>';
  const fmtSize = n => n >= MiB ? (n / MiB).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
  const when = iso => { try { return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }); } catch { return ''; } };
  const liveMaps = () => TRN.db.maps.filter(m => m.status === 'live' && (m.mapImage?.levels || []).length);
  /* Pin levels for a map: unique level ids (Pendola Pass lists two images under level "all"; pins use the first,
     the detailed map, because the terrain overview is a different projection). */
  function levelsFor(mapId) {
    const seen = new Set(), out = [];
    for (const l of TRN.data.map(mapId)?.mapImage?.levels || []) if (!seen.has(l.id)) { seen.add(l.id); out.push(l); }
    return out;
  }
  const mapImg = l => (innerWidth < 900 && l.srcSmall ? l.srcSmall : l.src);
  const mapThumb = id => TRN.img(TRN.data.map(id)?.image || '');
  function needServer(root) {
    if (TRN.mode === 'server') return false;
    root.innerHTML = `<div class="notice-bar">${TRN.icon('warning')}<div><strong>Loot Trails need the live server.</strong> They're stored in the Raider Network database so your squad can return to them on any device, so they aren't available in local demo mode. Run <code>npx wrangler pages dev .</code> to test them locally.</div></div>`;
    return true;
  }
  const errBox = (msg) => `<div class="notice-bar">${TRN.icon('warning')}<div><strong>${esc(msg)}</strong> <a href="trails.html">Back to Loot Trails</a></div></div>`;

  /* ---------------------------------------------------------------- create form (dashboard + Loot Hunt popup) */
  function createFormHtml(id = 'trailCreateForm') {
    return `<form id="${id}" class="form-grid trail-create">
      <label class="full">Trail name<input class="input" name="title" required maxlength="100" placeholder="e.g. Stella Montis blueprint sweep"></label>
      <label class="full">Map<select class="input" name="mapId" required>${liveMaps().map(m => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('')}</select></label>
      <label class="full">Description <span class="muted-label">(optional, private to your squad)</span><textarea class="input" name="description" rows="3" maxlength="2000" placeholder="What is the squad collecting? Routes, rules, meeting times…"></textarea></label>
      <p class="small-note full">${TRN.svg('info')} Private by default: only you and Raiders you invite (and who accept) can see it. You decide later whether anything is ever published.</p>
      <button class="btn btn-primary full" type="submit">Create Loot Trail</button><p class="form-note full" role="status"></p></form>`;
  }
  function wireCreateForm(form) {
    if (TRN.param('map') && form.elements.mapId.querySelector(`option[value="${CSS.escape(TRN.param('map'))}"]`)) form.elements.mapId.value = TRN.param('map');
    form.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(form), note = $('.form-note', form), btn = $('button[type=submit]', form);
      if (TRN.mode !== 'server') { note.textContent = 'Loot Trails need the live server (not available in local demo mode).'; return; }
      btn.disabled = true; note.textContent = 'Creating…';
      try {
        const d = await A.create({ title: String(fd.get('title') || '').trim(), description: String(fd.get('description') || '').trim(), mapId: fd.get('mapId') });
        location.href = 'trails.html?id=' + enc(d.trail.id) + '&created=1';
      } catch (err) { note.textContent = err.message; btn.disabled = false; }
    };
  }

  /* Loot Hunt popup chooser: Quick Hunt keeps the v6.2 form exactly as it was; Loot Trail swaps in the trail form. */
  function wireHuntChooser(modal) {
    const quick = $('#huntForm', modal), pane = $('#huntTrailPane', modal), opts = $$('[data-hunt-mode]', modal);
    if (!quick || !pane || !opts.length) return;
    const set = mode => {
      opts.forEach(o => { const on = o.dataset.huntMode === mode; o.classList.toggle('on', on); o.setAttribute('aria-checked', String(on)); });
      quick.classList.toggle('hidden', mode !== 'quick'); pane.classList.toggle('hidden', mode !== 'trail');
      if (mode === 'trail' && !pane.dataset.ready) {
        pane.dataset.ready = '1';
        pane.innerHTML = TRN.mode === 'server' ? createFormHtml('huntTrailForm')
          : `<div class="notice-bar">${TRN.icon('warning')}<div><strong>Loot Trails need the live server.</strong> They are saved in the Raider Network database, so they aren't available in local demo mode. Quick Hunts still work here.</div></div>`;
        const tf = $('#huntTrailForm', pane); if (tf) wireCreateForm(tf);
      }
      if (mode === 'trail') $('#huntTrailForm [name=title]', pane)?.focus();
    };
    opts.forEach(o => (o.onclick = () => set(o.dataset.huntMode)));
    set(TRN.param('mode') === 'trail' ? 'trail' : 'quick');
  }

  /* ---------------------------------------------------------------- dashboard */
  async function renderDashboard(root) {
    root.innerHTML = `<section class="page-banner page-banner--slim trails-banner"><img src="assets/images/heroes/loot-hunt-squad.webp" alt=""><div class="page-banner__shade"></div>
      <div class="page-banner__copy"><span class="eyebrow">${TRN.icon('route')} LONG-TERM SQUAD PROJECTS</span><h1>Loot Trails</h1>
        <p>Record loot discoveries on the map with your squad, over as many sessions as it takes. Private until you decide otherwise.</p>
        <div class="btn-row"><button class="btn btn-primary btn-lg" id="newTrailBtn">+ Start a Loot Trail</button><a class="btn btn-ghost btn-lg" href="hunts.html">Quick Hunts</a></div></div></section>
      <div class="page-shell trails-dash">
        <div id="trailInvites"></div>
        <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('route')} MY LOOT TRAILS</span><span class="muted" id="ownedCount"></span></header><div id="ownedTrails" class="trail-grid"><p class="muted">Loading your trails…</p></div></section>
        <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('squad')} JOINED TRAILS</span><span class="muted" id="joinedCount"></span></header><div id="joinedTrails" class="trail-grid"><p class="muted">Loading…</p></div></section>
      </div>
      <div class="modal hidden" id="trailModal" role="dialog" aria-modal="true" aria-labelledby="trailModalTitle"><div class="modal-card">
        <button class="modal-close" id="closeTrailModal" aria-label="Close">×</button><span class="eyebrow">NEW LOOT TRAIL</span><h2 id="trailModalTitle">Start a Loot Trail</h2>${createFormHtml()}</div></div>`;
    const modal = $('#trailModal');
    $('#newTrailBtn').onclick = () => { modal.classList.remove('hidden'); $('#trailCreateForm').elements.title.focus(); };
    $('#closeTrailModal').onclick = () => modal.classList.add('hidden');
    modal.onclick = e => { if (e.target === modal) modal.classList.add('hidden'); };
    wireCreateForm($('#trailCreateForm'));
    if (TRN.param('new') !== null) $('#newTrailBtn').click();

    const [list, inv] = await Promise.allSettled([A.list(), A.invites()]);
    if (inv.status === 'fulfilled' && inv.value.invitations.length) {
      $('#trailInvites').innerHTML = `<section class="panel trail-invites"><header class="panel-head"><span class="eyebrow">${TRN.icon('message')} SQUAD INVITATIONS</span></header>
        ${inv.value.invitations.map(i => `<div class="invite-row"><img src="${mapThumb(i.mapId)}" alt=""><div><strong>${esc(i.title)}</strong><span>${esc(i.owner.displayName)} <small>@${esc(i.owner.username)}</small> invited you · ${esc(TRN.data.mapName(i.mapId))} · ${TRN.ageFromIso(i.invitedAt)}</span></div>
          <span class="offer-actions"><button class="btn btn-primary btn-xs" data-inv="${esc(i.trailId)}" data-d="ACCEPT">Accept</button><button class="btn btn-ghost btn-xs" data-inv="${esc(i.trailId)}" data-d="DECLINE">Decline</button></span></div>`).join('')}</section>`;
      $$('[data-inv]').forEach(b => (b.onclick = async () => {
        b.disabled = true;
        try { await A.respond(b.dataset.inv, b.dataset.d); if (b.dataset.d === 'ACCEPT') { location.href = 'trails.html?id=' + enc(b.dataset.inv); return; } TRN.toast('Invitation declined'); b.closest('.invite-row').remove(); }
        catch (err) { TRN.toast(err.message); b.disabled = false; }
      }));
    }
    if (list.status === 'rejected') { $('#ownedTrails').innerHTML = `<p class="empty-note">${esc(list.reason.message)}</p>`; $('#joinedTrails').innerHTML = ''; return; }
    const trails = list.value.trails, owned = trails.filter(t => t.myRole === 'OWNER'), joined = trails.filter(t => t.myRole !== 'OWNER');
    const card = t => {
      const s = t.stats, total = Math.max(0, s.active ?? s.discoveries), pct = total ? Math.round((s.myCompleted / total) * 100) : 0;
      return `<a class="trail-card" href="trails.html?id=${enc(t.id)}"><div class="trail-card__media"><img src="${mapThumb(t.mapId)}" alt="" loading="lazy">${visChip(t.visibility)}</div>
        <div class="trail-card__body"><strong>${esc(t.title)}</strong><span class="muted">${esc(TRN.data.mapName(t.mapId))}${t.myRole === 'OWNER' ? '' : ` · by ${esc(t.owner.displayName)}`}</span>
          <div class="trail-stats"><span><b>${s.discoveries}</b> discoveries</span><span><b>${s.approved}</b> approved</span><span><b>${s.sessions}</b> sessions</span><span><b>${s.squadSize}</b> in squad</span></div>
          <div class="trail-progress" title="Your progress"><i style="width:${pct}%"></i></div><small class="muted">You: ${s.myCompleted} of ${total} completed · updated ${TRN.ageFromIso(t.updatedAt)}</small></div></a>`;
    };
    $('#ownedCount').textContent = owned.length ? `${owned.length} trail${owned.length > 1 ? 's' : ''}` : '';
    $('#joinedCount').textContent = joined.length ? `${joined.length} trail${joined.length > 1 ? 's' : ''}` : '';
    $('#ownedTrails').innerHTML = owned.map(card).join('') || `<div class="empty-state"><strong>No Loot Trails yet.</strong><span>Start one for a long-term goal (a blueprint sweep, a project's parts) and invite your squad.</span></div>`;
    $('#joinedTrails').innerHTML = joined.map(card).join('') || `<p class="empty-note">Trails you join through an invitation appear here.</p>`;
  }

  /* ---------------------------------------------------------------- map with pins */
  function MapPins(host, mapId, { onPick, onPinClick } = {}) {
    const levels = levelsFor(mapId);
    let level = levels[0]?.id, zoom = 1, pins = [], draft = null, picking = false, pickCb = onPick, levelCb = null;
    host.innerHTML = `<div class="tm-bar">${levels.length > 1 ? `<div class="mv-levels" role="tablist">${levels.map((l, i) => `<button type="button" class="mv-level ${i ? '' : 'on'}" data-level="${esc(l.id)}">${esc(l.label)}</button>`).join('')}</div>` : `<span class="muted">${esc(levels[0]?.label || 'Map')}</span>`}
        <div class="tm-zoom"><button type="button" class="icon-btn" data-z="-1" aria-label="Zoom out">−</button><span class="tm-zoomv">100%</span><button type="button" class="icon-btn" data-z="1" aria-label="Zoom in">+</button></div></div>
      <div class="tm-stage" tabindex="0" aria-label="${esc(TRN.data.mapName(mapId))} map"><div class="tm-world"><img class="tm-img" alt="${esc(TRN.data.mapName(mapId))} map"><div class="tm-pins"></div></div></div>
      <p class="small-note tm-note"></p>`;
    const world = $('.tm-world', host), img = $('.tm-img', host), stage = $('.tm-stage', host);
    const calibrated = l => !!l?.calibrated;
    function paint() {
      const l = levels.find(x => x.id === level); if (!l) return;
      if (img.dataset.src !== mapImg(l)) { img.src = mapImg(l); img.dataset.src = mapImg(l); img.width = l.width; img.height = l.height; }
      world.style.width = (zoom * 100) + '%'; $('.tm-zoomv', host).textContent = Math.round(zoom * 100) + '%';
      const shown = pins.filter(p => p.mapLevel === level);
      $('.tm-pins', host).innerHTML = shown.map(p => `<button type="button" class="tm-pin tm-pin--${esc(p.state)} ${p.active ? 'is-active' : ''}" style="left:${(p.x * 100).toFixed(3)}%;top:${(p.y * 100).toFixed(3)}%" data-pin="${esc(p.id)}" title="${esc(p.title)}"><span>${esc(String(p.n))}</span></button>`).join('')
        + (draft && draft.level === level ? `<span class="tm-pin tm-pin--draft" style="left:${(draft.x * 100).toFixed(3)}%;top:${(draft.y * 100).toFixed(3)}%"><span>+</span></span>` : '');
      $$('[data-pin]', host).forEach(b => (b.onclick = e => { e.stopPropagation(); if (!picking) onPinClick?.(b.dataset.pin); }));
      $('.tm-note', host).innerHTML = picking ? `<b>Click or tap the map where you found it.</b> The pin is a position on this map image${calibrated(l) ? '' : ' (this map is not calibrated to game coordinates)'}; your map screenshot is the supporting evidence.`
        : calibrated(l) ? 'Pins are positions on this map image chosen by Raiders.' : 'Pins are positions on this map image chosen by Raiders. This map is not calibrated to game coordinates.';
      stage.classList.toggle('is-picking', picking);
    }
    const setLevel = id => { level = id; $$('[data-level]', host).forEach(x => x.classList.toggle('on', x.dataset.level === id)); paint(); levelCb?.(id); };
    $$('[data-level]', host).forEach(b => (b.onclick = () => setLevel(b.dataset.level)));
    $$('[data-z]', host).forEach(b => (b.onclick = () => { zoom = Math.min(4, Math.max(1, zoom + Number(b.dataset.z) * 0.5)); paint(); }));
    world.addEventListener('click', e => {
      if (!picking) return;
      const r = world.getBoundingClientRect();
      const x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
      draft = { level, x: Math.round(x * 1e5) / 1e5, y: Math.round(y * 1e5) / 1e5 }; paint(); pickCb?.(draft);
    });
    paint();
    return {
      setPins(p) { pins = p; paint(); },
      setPicking(on, cb, onLevel) { picking = on; pickCb = on ? cb : onPick; levelCb = on ? onLevel : null; if (!on) draft = null; paint(); if (on) stage.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); },
      setLevel, level: () => level, levels, draft: () => draft,
      focus(pin) { if (pin && pin.mapLevel !== level) { level = pin.mapLevel; $$('[data-level]', host).forEach(x => x.classList.toggle('on', x.dataset.level === level)); levelCb?.(level); } pins = pins.map(p => ({ ...p, active: p.id === pin?.id })); paint();
        const el = pin && $(`[data-pin="${CSS.escape(pin.id)}"]`, host); if (el) el.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' }); },
    };
  }

  /* ---------------------------------------------------------------- screenshot picker (two separate controls) */
  function shotPickerHtml() {
    return `<div class="shot-pickers">${['MAP_POSITION', 'LOOT'].map(t => `<label class="shot-pick" data-shot="${t}">
      <span class="shot-pick__label"><b>${SHOT[t]} screenshot</b><small>${SHOT_HELP[t]} · PNG, JPEG or WebP, up to 20 MB</small></span>
      <input type="file" accept="image/png,image/jpeg,image/webp" data-file="${t}">
      <span class="shot-pick__preview"></span><span class="shot-pick__status" role="status"></span></label>`).join('')}</div>`;
  }
  function validateFiles(files) {
    let total = 0;
    for (const [t, f] of Object.entries(files)) {
      if (!f) continue;
      if (!IMAGE_TYPES.includes(f.type)) return `${SHOT[t]} screenshot must be a PNG, JPEG or WebP image.`;
      if (f.size > MAX_IMAGE) return `${SHOT[t]} screenshot is ${fmtSize(f.size)}; the limit is 20 MB per screenshot.`;
      if (f.size < 1) return `${SHOT[t]} screenshot is empty.`;
      total += f.size;
    }
    if (total > MAX_PAIR) return `The two screenshots add up to ${fmtSize(total)}; the combined limit is 40 MB.`;
    return '';
  }
  function wireShotPickers(root) {
    const files = { MAP_POSITION: null, LOOT: null };
    $$('[data-file]', root).forEach(inp => (inp.onchange = () => {
      const t = inp.dataset.file, f = inp.files[0] || null, box = inp.closest('.shot-pick');
      const prev = $('.shot-pick__preview', box), st = $('.shot-pick__status', box);
      files[t] = f; prev.innerHTML = ''; st.textContent = ''; box.classList.remove('is-error');
      if (!f) return;
      const err = validateFiles({ [t]: f });
      if (err) { st.textContent = err; box.classList.add('is-error'); files[t] = null; inp.value = ''; return; }
      const url = URL.createObjectURL(f);
      prev.innerHTML = `<img src="${url}" alt=""><span>${esc(f.name)} · ${fmtSize(f.size)}</span>`;
      $('img', prev).onload = () => URL.revokeObjectURL(url);
    }));
    return files;
  }

  /* ---------------------------------------------------------------- trail detail */
  async function renderTrail(root, id) {
    root.innerHTML = '<div class="page-shell"><p class="muted">Loading Loot Trail…</p></div>';
    let D;
    try { D = await A.get(id); } catch (e) { root.innerHTML = `<div class="page-shell">${errBox(e.status === 404 ? 'This Loot Trail was not found, or you are not in its squad.' : e.message)}</div>`; return; }
    if (D.view === 'PUBLIC') return renderPublic(root, D);
    const T = D.trail, P = D.permissions;
    const sessions = D.sessions, openSessions = sessions.filter(s => !s.endedAt);
    const done = new Set(D.myCompletedDiscoveryIds);
    const counted = D.discoveries.filter(d => d.reviewStatus !== 'REJECTED');
    const myDone = counted.filter(d => done.has(d.id)).length;
    const nOf = new Map(D.discoveries.map((d, i) => [d.id, i + 1]));
    const sessionName = sid => sessions.find(s => s.id === sid)?.title || 'Session';
    const filter = { status: '', session: '', mine: false };

    root.innerHTML = `<div class="page-shell trail-shell">
      <div class="trail-head"><div><span class="eyebrow">${TRN.icon('route')} LOOT TRAIL · ${esc(TRN.data.mapName(T.mapId).toUpperCase())}</span><h1>${esc(T.title)}</h1>
        <div class="chip-row">${visChip(T.visibility)}<span class="status-chip ${P.isOwner ? 'status-awaiting' : 'status-new'}">${P.isOwner ? 'YOU OWN THIS TRAIL' : 'CONTRIBUTOR'}</span>${T.status !== 'ACTIVE' ? '<span class="status-chip status-closed">ARCHIVED</span>' : ''}</div>
        ${T.description ? `<p class="trail-desc">${esc(T.description)}</p>` : ''}</div>
        <div class="trail-progress-box"><small>YOUR PROGRESS</small><strong>${myDone} <span>of ${counted.length}</span></strong><div class="trail-progress"><i style="width:${counted.length ? Math.round(myDone / counted.length * 100) : 0}%"></i></div><small class="muted">Only you can see your own ticks.</small></div></div>
      ${TRN.param('created') ? `<div class="notice-bar notice-bar--ok">${TRN.svg('check')}<div><strong>Loot Trail created — it's private.</strong> Next: invite your squad, start a session, then record discoveries on the map.</div></div>` : ''}
      <div class="trail-steps">${['Invite squad', 'Start a session', 'Record discoveries', 'Owner reviews', 'Publish (optional)'].map((s, i) => `<span><b>${i + 1}</b>${s}</span>`).join('')}</div>
      <div class="trail-grid-main">
        <section class="panel trail-map"><header class="panel-head"><span class="eyebrow">${TRN.icon('map')} MAP</span><button class="btn btn-primary btn-xs" id="addDiscoveryBtn" ${P.canContribute ? '' : 'disabled'}>+ Record a discovery</button></header>
          <div id="trailMap"></div><div id="discoveryFormHost"></div></section>
        <aside class="trail-side">
          <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('time')} SESSIONS</span><span class="muted">${sessions.length}</span></header>
            <div id="sessionList" class="stack-sm"></div>
            ${P.canContribute ? `<details class="trail-more" ${sessions.length ? '' : 'open'}><summary>Start a new session</summary><form id="sessionForm" class="stack-sm"><label>Session title<input class="input" name="title" required maxlength="100" placeholder="e.g. Friday night run"></label><label>Notes <span class="muted-label">(optional)</span><textarea class="input" name="notes" rows="2" maxlength="2000"></textarea></label><button class="btn btn-primary btn-xs">Start session</button><span class="form-note" role="status"></span></form></details>` : ''}</section>
          <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('squad')} SQUAD</span><span class="muted">${D.squad.filter(m => m.status === 'ACCEPTED').length} active</span></header>
            <div id="squadList" class="stack-sm"></div>
            ${P.canInvite ? `<form id="inviteForm" class="invite-form"><label>Invite a Raider by username<input class="input" name="username" required maxlength="40" placeholder="username" autocomplete="off" autocapitalize="none"></label><button class="btn btn-primary btn-xs">Invite</button><span class="form-note" role="status"></span></form>` : ''}</section>
          ${P.isOwner ? `<section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('settings')} VISIBILITY</span></header>
            <p class="small-note">${T.visibility === 'PUBLIC' ? 'Public: anyone with the link sees the trail title and map, plus the title, item, notes and pin of each discovery you approved <b>and</b> published. The description, squad, sessions, unpublished discoveries and all screenshots stay private.' : 'Private: only your accepted squad can open this trail.'}</p>
            <button class="btn btn-ghost btn-xs" id="visBtn">${T.visibility === 'PUBLIC' ? 'Make private' : 'Make public…'}</button><span class="form-note" id="visNote" role="status"></span></section>` : ''}
        </aside>
      </div>
      <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('loot-intel')} DISCOVERIES</span><span class="muted">${D.discoveries.length}</span></header>
        <div class="disc-filters"><select class="input" id="fStatus" aria-label="Review status"><option value="">All statuses</option><option value="PENDING">Pending review</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option></select>
          <select class="input" id="fSession" aria-label="Session"><option value="">All sessions</option>${sessions.map(s => `<option value="${esc(s.id)}">${esc(s.title)}</option>`).join('')}</select>
          <label class="flag-toggle"><input type="checkbox" id="fMine"><span>Recorded by me</span></label>
          <label class="flag-toggle"><input type="checkbox" id="fTodo"><span>Not completed by me</span></label></div>
        <div id="discList" class="disc-list"></div></section>
      <p class="small-note"><a href="trails.html">← All Loot Trails</a></p></div>`;

    /* map */
    const map = MapPins($('#trailMap'), T.mapId, { onPinClick: did => { const c = $(`[data-disc="${CSS.escape(did)}"]`); if (c) { c.scrollIntoView({ block: 'center', behavior: 'smooth' }); c.classList.add('flash'); setTimeout(() => c.classList.remove('flash'), 1600); } } });
    const pinState = d => d.reviewStatus === 'REJECTED' ? 'rejected' : done.has(d.id) ? 'done' : d.reviewStatus === 'APPROVED' ? 'approved' : 'pending';
    map.setPins(D.discoveries.map(d => ({ id: d.id, n: nOf.get(d.id), x: d.x, y: d.y, mapLevel: d.mapLevel, title: d.title, state: pinState(d) })));

    /* sessions */
    $('#sessionList').innerHTML = sessions.length ? sessions.map(s => `<div class="session-row ${s.endedAt ? 'is-ended' : ''}"><div><strong>${esc(s.title)}</strong>
        <small>${esc(s.startedBy)} · started ${when(s.startedAt)}${s.endedAt ? ` · ended ${when(s.endedAt)}` : ''} · ${s.discoveryCount} discover${s.discoveryCount === 1 ? 'y' : 'ies'}</small>${s.notes ? `<p>${esc(s.notes)}</p>` : ''}</div>
        ${s.endedAt ? '<span class="status-chip status-closed">ENDED</span>' : `<span class="status-chip status-open">ACTIVE</span>${s.canEnd ? `<button class="text-btn" data-end="${esc(s.id)}">End</button>` : ''}`}</div>`).join('')
      : '<p class="empty-note">No sessions yet. Start one each time your squad plays; discoveries are filed under the session they were found in.</p>';
    $$('[data-end]').forEach(b => (b.onclick = async () => {
      if (!b.classList.contains('confirming')) { b.classList.add('confirming'); b.textContent = 'Confirm end'; setTimeout(() => { if (b.isConnected) { b.classList.remove('confirming'); b.textContent = 'End'; } }, 4000); return; }
      try { await A.endSession(T.id, b.dataset.end); TRN.toast('Session ended'); renderTrail(root, id); } catch (err) { TRN.toast(err.message); }
    }));
    const sf = $('#sessionForm');
    if (sf) sf.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(sf), note = $('.form-note', sf);
      try { await A.session(T.id, { title: String(fd.get('title')).trim(), notes: String(fd.get('notes') || '').trim() }); TRN.toast('Session started'); renderTrail(root, id); }
      catch (err) { note.textContent = err.message; }
    };

    /* squad */
    const statusLabel = { ACCEPTED: '', INVITED: 'Invited · waiting', DECLINED: 'Declined', REMOVED: 'Removed' };
    $('#squadList').innerHTML = D.squad.map(m => `<div class="squad-row ${m.status !== 'ACCEPTED' ? 'is-muted' : ''}"><img class="avatar-img" src="${TRN.IMG + esc(m.avatarUrl || 'raiders/raider-solo-scout.webp')}" alt="">
      <div><strong>${esc(m.displayName)}</strong><small>@${esc(m.username)}${m.platform ? ' · ' + esc(m.platform) : ''}${statusLabel[m.status] ? ' · ' + statusLabel[m.status] : ''}</small>
      ${m.completedCount !== undefined ? `<small class="muted">${m.completedCount} of ${counted.length} completed</small>` : ''}</div>
      <span class="role-tag role-${m.role.toLowerCase()}">${m.role === 'OWNER' ? 'Owner' : 'Contributor'}</span>
      ${P.isOwner && m.role !== 'OWNER' && ['INVITED', 'ACCEPTED'].includes(m.status) ? `<button class="text-btn" data-remove="${esc(m.username)}" title="${m.status === 'INVITED' ? 'Withdraw invitation' : 'Remove from squad'}">${m.status === 'INVITED' ? 'Withdraw' : 'Remove'}</button>` : ''}</div>`).join('');
    $$('[data-remove]').forEach(b => (b.onclick = async () => {
      if (!b.classList.contains('confirming')) { b.classList.add('confirming'); b.textContent = 'Confirm'; setTimeout(() => { if (b.isConnected) { b.classList.remove('confirming'); b.textContent = 'Remove'; } }, 4000); return; }
      try { await A.removeMember(T.id, b.dataset.remove); TRN.toast('Removed from squad'); renderTrail(root, id); } catch (err) { TRN.toast(err.message); }
    }));
    const inf = $('#inviteForm');
    if (inf) inf.onsubmit = async e => {
      e.preventDefault(); const note = $('.form-note', inf), u = String(new FormData(inf).get('username') || '').trim().replace(/^@/, '');
      try { const d = await A.invite(T.id, u); TRN.toast(`Invitation sent to ${d.invitation.displayName}`); renderTrail(root, id); }
      catch (err) { note.textContent = err.status === 404 ? 'No Raider with that username.' : err.message; }
    };

    /* visibility */
    const vb = $('#visBtn');
    if (vb) vb.onclick = async () => {
      const to = T.visibility === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC';
      if (to === 'PUBLIC' && !vb.classList.contains('confirming')) {
        vb.classList.add('confirming'); vb.textContent = 'Confirm: make public';
        $('#visNote').textContent = 'Making the trail public does not publish discoveries. Only discoveries you approve and then publish one by one become visible (title, item, notes and pin). Screenshots always stay private.';
        return;
      }
      try { await A.visibility(T.id, to); TRN.toast(to === 'PUBLIC' ? 'Trail is now public' : 'Trail is now private'); renderTrail(root, id); } catch (err) { $('#visNote').textContent = err.message; }
    };

    /* discoveries list */
    function shotSlot(d, t) {
      const has = d.images[t];
      const body = has ? `<a class="shot-thumb" href="${A.imageUrl(T.id, d.id, t, d.updatedAt)}" target="_blank" rel="noopener"><img src="${A.imageUrl(T.id, d.id, t, d.updatedAt)}" alt="${SHOT[t]} screenshot for ${esc(d.title)}" loading="lazy"></a>`
        : `<span class="shot-empty">No ${SHOT[t].toLowerCase()} screenshot</span>`;
      const actions = !P.canContribute ? '' : has
        ? (d.canReplaceImages ? `<button class="text-btn" data-rm="${esc(d.id)}" data-t="${t}">Remove to replace</button>` : (d.canUpload && d.reviewStatus === 'APPROVED' ? '<small class="muted">Locked (approved)</small>' : ''))
        : (d.canUpload && d.reviewStatus !== 'APPROVED' ? `<label class="text-btn shot-add">Add<input type="file" accept="image/png,image/jpeg,image/webp" data-add="${esc(d.id)}" data-t="${t}" hidden></label>` : '');
      return `<div class="shot-slot"><small>${SHOT[t].toUpperCase()}</small>${body}<div class="shot-actions">${actions}<span class="shot-msg" role="status"></span></div></div>`;
    }
    function discCard(d) {
      const it = d.itemId ? TRN.data.item(d.itemId) : null, mineDone = done.has(d.id);
      return `<article class="disc-card ${mineDone ? 'is-done' : ''}" data-disc="${esc(d.id)}">
        <header><span class="disc-n">${nOf.get(d.id)}</span><div><h3>${esc(d.title)}</h3><small>${esc(sessionName(d.sessionId))} · ${esc(d.creator.displayName)}${d.mine ? ' (you)' : ''} · ${TRN.ageFromIso(d.createdAt)}${levelsFor(T.mapId).length > 1 ? ' · ' + esc(levelsFor(T.mapId).find(l => l.id === d.mapLevel)?.label || '') : ''}</small></div>
          <div class="chip-row">${chip(d.reviewStatus)}${d.isPublic ? '<span class="status-chip status-completed">PUBLISHED</span>' : ''}</div></header>
        ${it ? `<div class="disc-item"><img src="${TRN.img(it.image)}" alt="">${TRN.data.itemLink(it.id)}</div>` : ''}
        ${d.notes ? `<p class="disc-notes">${esc(d.notes)}</p>` : ''}
        <div class="shot-row">${shotSlot(d, 'MAP_POSITION')}${shotSlot(d, 'LOOT')}</div>
        <footer><label class="flag-toggle done-toggle"><input type="checkbox" data-done="${esc(d.id)}" ${mineDone ? 'checked' : ''} ${P.canContribute ? '' : 'disabled'}><span>${mineDone ? 'Completed by me' : 'Mark completed (just for me)'}</span></label>
          <button class="text-btn" data-show="${esc(d.id)}">Show on map</button>
          ${P.canReview ? `<span class="review-actions">${['APPROVED', 'REJECTED', 'PENDING'].filter(s => s !== d.reviewStatus).map(s => `<button class="btn ${s === 'APPROVED' ? 'btn-primary' : 'btn-ghost'} btn-xs" data-review="${esc(d.id)}" data-s="${s}">${{ APPROVED: 'Approve', REJECTED: 'Reject', PENDING: 'Back to pending' }[s]}</button>`).join('')}
            ${d.reviewStatus === 'APPROVED' ? `<button class="btn btn-ghost btn-xs" data-pub="${esc(d.id)}" data-v="${d.isPublic ? '0' : '1'}">${d.isPublic ? 'Unpublish' : 'Publish…'}</button>` : ''}</span>` : ''}</footer></article>`;
    }
    function paintList() {
      const rows = D.discoveries.filter(d => (!filter.status || d.reviewStatus === filter.status) && (!filter.session || d.sessionId === filter.session) && (!filter.mine || d.mine) && (!filter.todo || !done.has(d.id)));
      $('#discList').innerHTML = rows.map(discCard).join('') || (D.discoveries.length ? '<p class="empty-note">No discoveries match these filters.</p>'
        : `<div class="empty-state"><strong>No discoveries yet.</strong><span>${openSessions.length ? 'Press “Record a discovery”, then place the pin on the map.' : 'Start a session first, then record what you find.'}</span></div>`);
      wireList();
    }
    function wireList() {
      $$('[data-done]').forEach(c => (c.onchange = async () => {
        c.disabled = true;
        try { await A.progress(T.id, c.dataset.done, c.checked); if (c.checked) done.add(c.dataset.done); else done.delete(c.dataset.done); refreshProgress(); paintList(); }
        catch (err) { TRN.toast(err.message); c.checked = !c.checked; c.disabled = false; }
      }));
      $$('[data-show]').forEach(b => (b.onclick = () => { const d = D.discoveries.find(x => x.id === b.dataset.show); map.focus({ id: d.id, mapLevel: d.mapLevel }); $('#trailMap').scrollIntoView({ behavior: 'smooth', block: 'center' }); }));
      $$('[data-review]').forEach(b => (b.onclick = async () => {
        b.disabled = true;
        try { await A.review(T.id, b.dataset.review, b.dataset.s); TRN.toast({ APPROVED: 'Approved (not published)', REJECTED: 'Rejected', PENDING: 'Set back to pending' }[b.dataset.s]); renderTrail(root, id); }
        catch (err) { TRN.toast(err.message); b.disabled = false; }
      }));
      $$('[data-pub]').forEach(b => (b.onclick = async () => {
        const on = b.dataset.v === '1';
        if (on && !b.classList.contains('confirming')) { b.classList.add('confirming'); b.textContent = T.visibility === 'PUBLIC' ? 'Confirm publish' : 'Confirm (trail is private)'; b.title = T.visibility === 'PUBLIC' ? 'Visible on the public trail page' : 'It becomes visible only if you also make the trail public'; return; }
        b.disabled = true;
        try { await A.publish(T.id, b.dataset.pub, on); TRN.toast(on ? (T.visibility === 'PUBLIC' ? 'Published' : 'Marked for publication — visible once the trail is public') : 'Unpublished'); renderTrail(root, id); }
        catch (err) { TRN.toast(err.message); b.disabled = false; }
      }));
      $$('[data-rm]').forEach(b => (b.onclick = async () => {
        if (!b.classList.contains('confirming')) { b.classList.add('confirming'); b.textContent = 'Confirm remove'; setTimeout(() => { if (b.isConnected) { b.classList.remove('confirming'); b.textContent = 'Remove to replace'; } }, 4000); return; }
        try { await A.removeImage(T.id, b.dataset.rm, b.dataset.t); TRN.toast('Screenshot removed — you can add a new one'); renderTrail(root, id); } catch (err) { TRN.toast(err.message); }
      }));
      $$('[data-add]').forEach(inp => (inp.onchange = async () => {
        const f = inp.files[0], msg = $('.shot-msg', inp.closest('.shot-slot')); if (!f) return;
        const err = validateFiles({ [inp.dataset.t]: f }); if (err) { msg.textContent = err; inp.value = ''; return; }
        msg.textContent = 'Uploading 0%';
        try { await A.upload(T.id, inp.dataset.add, inp.dataset.t, f, p => (msg.textContent = `Uploading ${Math.round(p * 100)}%`)); TRN.toast('Screenshot saved'); renderTrail(root, id); }
        catch (e2) { msg.textContent = e2.message; inp.value = ''; }
      }));
    }
    function refreshProgress() {
      const n = counted.filter(d => done.has(d.id)).length;
      $('.trail-progress-box strong').innerHTML = `${n} <span>of ${counted.length}</span>`;
      $('.trail-progress-box .trail-progress i').style.width = (counted.length ? Math.round(n / counted.length * 100) : 0) + '%';
      map.setPins(D.discoveries.map(d => ({ id: d.id, n: nOf.get(d.id), x: d.x, y: d.y, mapLevel: d.mapLevel, title: d.title, state: pinState(d) })));
    }
    $('#fStatus').onchange = e => { filter.status = e.target.value; paintList(); };
    $('#fSession').onchange = e => { filter.session = e.target.value; paintList(); };
    $('#fMine').onchange = e => { filter.mine = e.target.checked; paintList(); };
    $('#fTodo').onchange = e => { filter.todo = e.target.checked; paintList(); };
    paintList();

    /* record a discovery */
    $('#addDiscoveryBtn').onclick = () => {
      const host = $('#discoveryFormHost');
      if (!openSessions.length) {
        host.innerHTML = `<div class="notice-bar">${TRN.icon('warning')}<div><strong>Start a session first.</strong> Discoveries are filed under the gaming session they were found in. Use “Start a new session” in the Sessions panel.</div></div>`;
        $('#sessionForm')?.closest('details')?.setAttribute('open', ''); $('#sessionForm [name=title]')?.focus(); return;
      }
      const levels = levelsFor(T.mapId);
      host.innerHTML = `<form id="discForm" class="disc-form">
        <h3>Record a discovery</h3>
        <div class="form-grid">
          <label>Session<select class="input" name="sessionId" required>${openSessions.map(s => `<option value="${esc(s.id)}">${esc(s.title)}</option>`).join('')}</select></label>
          ${levels.length > 1 ? `<label>Map level<select class="input" name="mapLevel">${levels.map(l => `<option value="${esc(l.id)}" ${l.id === map.level() ? 'selected' : ''}>${esc(l.label)}</option>`).join('')}</select></label>` : `<input type="hidden" name="mapLevel" value="${esc(levels[0]?.id || 'all')}">`}
          <label class="full">What did you find?<input class="input" name="title" required maxlength="120" list="trailItemNames" placeholder="e.g. Rotary Encoder in the server room" autocomplete="off"></label>
          <datalist id="trailItemNames">${TRN.db.items.map(i => `<option value="${esc(i.name)}">`).join('')}</datalist>
          <div class="full item-preview" id="discItemPreview"></div>
          <label class="full">Notes <span class="muted-label">(optional)</span><textarea class="input" name="notes" rows="2" maxlength="2000" placeholder="Container type, floor, timing, ARC nearby…"></textarea></label>
          <div class="full pin-status" id="pinStatus">${TRN.icon('location')} <span><b>Place the pin:</b> click or tap the map above where you found it.</span></div>
          <div class="full">${shotPickerHtml()}</div>
          <p class="small-note full">Screenshots upload only when you press Save. They are private to your squad and are never published, even if the discovery is.</p>
          <div class="full btn-row"><button class="btn btn-primary" type="submit">Save discovery</button><button class="btn btn-ghost" type="button" id="discCancel">Cancel</button></div>
          <p class="form-note full" role="status" id="discMsg"></p></div></form>`;
      const f = $('#discForm'), files = wireShotPickers(f);
      let pin = null;
      const lvlSel = f.elements.mapLevel.tagName === 'SELECT' ? f.elements.mapLevel : null;
      if (lvlSel) lvlSel.onchange = () => map.setLevel(lvlSel.value);
      map.setPicking(true, dr => {
        pin = dr;
        if (lvlSel) lvlSel.value = dr.level;
        $('#pinStatus').innerHTML = `${TRN.svg('check')} <span><b>Pin placed</b> at ${(dr.x * 100).toFixed(1)}% across, ${(dr.y * 100).toFixed(1)}% down${levels.length > 1 ? ' on ' + esc(levels.find(l => l.id === dr.level)?.label || '') : ''}. Click again to move it.</span>`;
        $('#pinStatus').classList.add('is-set');
      }, lv => { if (lvlSel) lvlSel.value = lv; });
      f.elements.title.oninput = () => { const it = TRN.data.findItemByName(f.elements.title.value); $('#discItemPreview').innerHTML = it ? `<img src="${TRN.img(it.image)}" alt="">${TRN.rarityBadge(it.rarity, 'sm')}<span>Linked to Loot Intel: ${TRN.data.itemLink(it.id)}</span>` : ''; };
      $('#discCancel').onclick = () => { map.setPicking(false); host.innerHTML = ''; };
      f.onsubmit = async e => {
        e.preventDefault(); const msg = $('#discMsg'), btn = $('button[type=submit]', f), fd = new FormData(f);
        if (!pin) { msg.textContent = 'Place the pin on the map first.'; $('#trailMap').scrollIntoView({ block: 'center', behavior: 'smooth' }); return; }
        const ferr = validateFiles(files); if (ferr) { msg.textContent = ferr; return; }
        btn.disabled = true; msg.textContent = 'Saving discovery…';
        const it = TRN.data.findItemByName(fd.get('title'));
        let disc;
        try {
          disc = (await A.discovery(T.id, { title: String(fd.get('title')).trim(), notes: String(fd.get('notes') || '').trim(), sessionId: fd.get('sessionId'), mapLevel: pin.level, x: pin.x, y: pin.y, ...(it ? { itemId: it.id } : {}) })).discovery;
        } catch (err) { msg.textContent = err.message; btn.disabled = false; return; }
        const failed = [];
        for (const t of ['MAP_POSITION', 'LOOT']) {
          const file = files[t]; if (!file) continue;
          const st = $(`[data-shot="${t}"] .shot-pick__status`, f);
          try { await A.upload(T.id, disc.id, t, file, p => (st.textContent = `Uploading ${Math.round(p * 100)}%`)); st.textContent = 'Uploaded ✓'; }
          catch (err) { st.textContent = err.message; failed.push(SHOT[t]); }
        }
        map.setPicking(false);
        if (failed.length) { msg.textContent = `Discovery saved, but the ${failed.join(' and ')} screenshot didn't upload. Add it from the discovery card below.`; TRN.toast('Discovery saved (screenshot upload failed)'); setTimeout(() => renderTrail(root, id), 2500); }
        else { TRN.toast('Discovery saved — pending owner review'); renderTrail(root, id); }
      };
    };
  }

  /* ---------------------------------------------------------------- public view (approved + published only) */
  function renderPublic(root, D) {
    const T = D.trail;
    root.innerHTML = `<div class="page-shell trail-shell">
      <div class="trail-head"><div><span class="eyebrow">${TRN.icon('route')} PUBLIC LOOT TRAIL · ${esc(TRN.data.mapName(T.mapId).toUpperCase())}</span><h1>${esc(T.title)}</h1>
        <div class="chip-row">${visChip('PUBLIC')}</div><p class="muted">Discoveries a squad recorded and its owner approved for publication. Screenshots and squad details are private.</p></div></div>
      <div class="trail-grid-main trail-grid-main--public"><section class="panel trail-map"><div id="trailMap"></div></section>
        <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('loot-intel')} PUBLISHED DISCOVERIES</span><span class="muted">${D.discoveries.length}</span></header>
          <div class="disc-list">${D.discoveries.map((d, i) => { const it = d.itemId ? TRN.data.item(d.itemId) : null; return `<article class="disc-card" data-disc="${esc(d.id)}"><header><span class="disc-n">${i + 1}</span><div><h3>${esc(d.title)}</h3></div></header>${it ? `<div class="disc-item"><img src="${TRN.img(it.image)}" alt="">${TRN.data.itemLink(it.id)}</div>` : ''}${d.notes ? `<p class="disc-notes">${esc(d.notes)}</p>` : ''}</article>`; }).join('') || '<p class="empty-note">Nothing has been published on this trail yet.</p>'}</div></section></div>
      <p class="small-note"><a href="trails.html">Loot Trails</a></p></div>`;
    const map = MapPins($('#trailMap'), T.mapId, { onPinClick: did => $(`[data-disc="${CSS.escape(did)}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' }) });
    map.setPins(D.discoveries.map((d, i) => ({ id: d.id, n: i + 1, x: d.x, y: d.y, mapLevel: d.mapLevel, title: d.title, state: 'approved' })));
  }

  /* ---------------------------------------------------------------- page entry */
  async function setupTrailsPage() {
    const root = $('#trailsRoot'); if (!root) return;
    const id = TRN.param('id');
    if (needServer(root)) return;
    if (!id) { const u = await TRN.auth.requireUser('trails.html' + location.search); if (!u) return; return renderDashboard(root); }
    return renderTrail(root, id);   // the server decides: member view, public view, or 404
  }

  TRN.trails = { setupTrailsPage, wireHuntChooser, createFormHtml, wireCreateForm, A, levelsFor, validateFiles };
})();
