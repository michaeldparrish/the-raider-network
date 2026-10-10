/* The Raider Network v5 — Loot Hunts. Hunts reference shared IDs: itemId, mapId, userId. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;

  function huntCard(h) {
    const it = TRN.data.item(h.itemId), slots = Math.max(0, (Number(h.squadSize) || 3) - (Number(h.currentMembers) || 1));
    const u = TRN.store.publicUser(h.userId);
    const search = [it?.name || h.itemName, TRN.data.mapName(h.mapId), h.displayName, h.region, h.platform, h.description].join(' ').toLowerCase();
    return `<article class="hunt-card hunt-${esc(h.status)}" id="${esc(h.id)}" data-search="${esc(search)}" data-region="${esc(h.region)}" data-platform="${esc(h.platform)}" data-map="${esc(h.mapId || '')}" data-item="${esc(h.itemId || '')}" data-status="${esc(h.status)}">
      <div class="hunt-card__media"><img src="${TRN.img(it?.image)}" alt="" loading="lazy">${it ? TRN.rarityBadge(it.rarity, 'sm') : ''}${TRN.statusChip(h.status === 'open' ? 'Open' : h.status)}</div>
      <div class="hunt-card__body">
        <span class="eyebrow compact">HUNTING</span>
        <h3>${TRN.data.itemLink(h.itemId, h.itemName)}</h3>
        <div class="raider-id">${u?.avatar ? `<img class="avatar-img" src="${TRN.IMG + u.avatar}" alt="">` : `<span class="avatar">${esc((h.displayName || 'R')[0].toUpperCase())}</span>`}<div><strong>${esc(h.displayName || 'Raider')}</strong><small>${TRN.ageFromIso(h.createdAt)}</small></div></div>
        <dl class="kv kv-2">
          <div><dt>${TRN.icon('map')}Map</dt><dd>${TRN.data.mapLink(h.mapId)}</dd></div>
          <div><dt>${TRN.icon('location')}Region</dt><dd>${esc(h.region)}</dd></div>
          <div><dt>${TRN.icon('settings')}Platform</dt><dd>${esc(h.platform)}</dd></div>
          <div><dt>${TRN.icon('time')}Desired time</dt><dd>${esc(h.desiredTime || 'Flexible')}</dd></div>
          <div><dt>${TRN.icon('squad')}Squad</dt><dd>${Number(h.currentMembers) || 1}/${Number(h.squadSize) || 3} · ${slots} slot${slots === 1 ? '' : 's'} open</dd></div>
        </dl>
        <p>${esc(h.description || 'Looking for Raiders to run this objective.')}</p>
        <div class="hunt-actions">
          <button class="btn btn-primary join-hunt" ${h.status !== 'open' ? 'disabled' : ''} data-hunt="${esc(h.id)}" data-user="${esc(h.userId)}" data-name="${esc(h.displayName)}" data-item="${esc(h.itemId || '')}">${h.status === 'open' ? 'Join Hunt' : h.status === 'full' ? 'Squad Full' : 'Completed'}</button>
          <button class="btn btn-ghost message-raider" data-hunt="${esc(h.id)}" data-user="${esc(h.userId)}" data-name="${esc(h.displayName)}" data-item="${esc(h.itemId || '')}">${TRN.svg('message')} Message Raider</button>
          ${it ? `<a class="btn btn-ghost" href="item.html?id=${encodeURIComponent(it.id)}">${TRN.icon('loot-intel')} View Item Intel</a>` : ''}
        </div>
      </div></article>`;
  }

  async function goMessage(b, intent) {
    const u = await TRN.auth.currentUser();
    const qs = `to=${encodeURIComponent(b.dataset.user)}&name=${encodeURIComponent(b.dataset.name)}&huntId=${encodeURIComponent(b.dataset.hunt)}${b.dataset.item ? '&itemId=' + encodeURIComponent(b.dataset.item) : ''}${intent ? '&intent=' + intent : ''}`;
    if (!u) { location.href = 'auth.html?next=' + encodeURIComponent('messages.html?' + qs) + '#register'; return; }
    if ((u.user_id || u.id) === b.dataset.user) { TRN.toast('This is your own hunt — manage it from My Profile.'); return; }
    location.href = 'messages.html?' + qs;
  }
  function wireHuntButtons(root = document) {
    $$('.message-raider', root).forEach(b => (b.onclick = () => goMessage(b)));
    $$('.join-hunt', root).forEach(b => (b.onclick = () => goMessage(b, 'join')));
  }

  function applyFilters() {
    const q = ($('#huntSearch')?.value || '').toLowerCase(), r = $('#regionFilter')?.value || '', p = $('#platformFilter')?.value || '', m = $('#mapFilter')?.value || '', s = $('#statusFilter')?.value || '', item = TRN.param('item') || '';
    let n = 0;
    $$('#huntGrid .hunt-card').forEach(c => { const ok = (!q || c.dataset.search.includes(q)) && (!r || c.dataset.region === r) && (!p || c.dataset.platform === p) && (!m || c.dataset.map === m) && (!s || c.dataset.status === s) && (!item || c.dataset.item === item); c.style.display = ok ? '' : 'none'; n += ok; });
    $('#huntCount') && ($('#huntCount').textContent = n);
    $('#huntEmpty')?.classList.toggle('hidden', n > 0);
  }

  async function renderHunts() {
    const grid = $('#huntGrid'); if (!grid) return;
    const hunts = await TRN.store.listHunts();
    const order = { open: 0, full: 1, completed: 2 };
    grid.innerHTML = [...hunts].sort((a, b) => order[a.status] - order[b.status] || new Date(b.createdAt) - new Date(a.createdAt)).map(huntCard).join('');
    wireHuntButtons(grid); applyFilters();
    const open = hunts.filter(h => h.status === 'open');
    $('#statOpenHunts').textContent = open.length; $('#statSlots').textContent = open.reduce((a, h) => a + Math.max(0, h.squadSize - h.currentMembers), 0);
    $('#statHuntItems').textContent = new Set(open.map(h => h.itemId)).size;
    if (location.hash) document.getElementById(location.hash.slice(1))?.classList.add('flash');
  }

  function setupHuntsPage() {
    if (!$('#huntGrid')) return;
    const D = TRN.db, opts = TRN.auth.options;
    $('#mapFilter').innerHTML = '<option value="">All maps</option>' + D.maps.filter(m => m.status === 'live').map(m => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
    $('#regionFilter').innerHTML = '<option value="">All regions</option>' + opts(D.regions);
    $('#platformFilter').innerHTML = '<option value="">All platforms</option>' + opts(D.platforms);
    const f = $('#huntForm');
    f.elements.mapId.innerHTML = D.maps.filter(m => m.status === 'live').map(m => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
    f.elements.region.innerHTML = opts(D.regions, 'NA East'); f.elements.platform.innerHTML = opts(D.platforms, 'Cross-platform');
    $('#itemNames').innerHTML = D.items.filter(i => i.group !== 'Gear' || i.category === 'Special').map(i => `<option value="${esc(i.name)}">`).join('') + D.items.filter(i => i.group === 'Gear').map(i => `<option value="${esc(i.name)}">`).join('');
    if (TRN.param('map')) $('#mapFilter').value = TRN.param('map');
    if (TRN.param('item')) { const it = TRN.data.item(TRN.param('item')); if (it) $('#itemFilterNote').innerHTML = `Showing hunts for ${TRN.data.itemLink(it.id)} · <a href="hunts.html">Show all</a>`; }
    ['huntSearch', 'regionFilter', 'platformFilter', 'mapFilter', 'statusFilter'].forEach(id => $('#' + id)?.addEventListener('input', applyFilters));
    const modal = $('#huntModal');
    const itemPreview = () => { const it = TRN.data.findItemByName(f.elements.itemName.value); $('#huntItemPreview').innerHTML = it ? `<img src="${TRN.img(it.image)}" alt="">${TRN.rarityBadge(it.rarity, 'sm')}<span>Linked to Loot Intel: <a href="item.html?id=${it.id}" target="_blank">${esc(it.name)}</a>${it.maps.length ? ' · reported on ' + it.maps.map(TRN.data.mapName).join(', ') : ''}</span>` : f.elements.itemName.value ? '<span class="muted">Not in the database yet — will be posted as free text.</span>' : ''; if (it && it.maps[0] && !f.dataset.mapTouched) f.elements.mapId.value = it.maps[0]; };
    f.elements.itemName.addEventListener('input', itemPreview);
    f.elements.mapId.addEventListener('change', () => (f.dataset.mapTouched = 1));
    const open = async (preItem) => { const u = await TRN.auth.currentUser(); if (!u) { location.href = 'auth.html?next=' + encodeURIComponent('hunts.html' + (preItem ? '?new=' + preItem : '')) + '#register'; return; } if (preItem) { f.elements.itemName.value = TRN.data.itemName(preItem); } if (TRN.param('map')) { f.elements.mapId.value = TRN.param('map'); f.dataset.mapTouched = 1; } f.elements.region.value = u.region || 'NA East'; f.elements.platform.value = u.platform || 'Cross-platform'; itemPreview(); modal.classList.remove('hidden'); f.elements.itemName.focus(); };
    $('#openHuntModal').onclick = () => open();
    $('#closeHuntModal').onclick = () => modal.classList.add('hidden');
    modal.onclick = e => { if (e.target === modal) modal.classList.add('hidden'); };
    document.addEventListener('keydown', e => { if (e.key === 'Escape') modal.classList.add('hidden'); });
    TRN.trails?.wireHuntChooser?.(modal);   // v6.3: Quick Hunt (unchanged) or Loot Trail
    f.onsubmit = async e => {
      e.preventDefault(); const msg = $('#huntFormMsg'), fd = new FormData(f); msg.textContent = 'Publishing…';
      try {
        const u = await TRN.auth.currentUser(); if (!u) throw new Error('Please log in before starting a loot hunt.');
        const it = TRN.data.findItemByName(fd.get('itemName'));
        await TRN.store.createHunt({ itemId: it?.id || null, itemName: it ? it.name : String(fd.get('itemName')).trim(), mapId: fd.get('mapId'), region: fd.get('region'), platform: fd.get('platform'), squadSize: Number(fd.get('squadSize') || 3), desiredTime: fd.get('desiredTime'), description: fd.get('description') }, u);
        msg.textContent = 'Loot hunt posted.'; f.reset(); delete f.dataset.mapTouched; $('#huntItemPreview').innerHTML = '';
        setTimeout(() => { modal.classList.add('hidden'); msg.textContent = ''; renderHunts(); TRN.toast('Loot hunt posted'); }, 300);
      } catch (err) { msg.textContent = err.message; }
    };
    renderHunts();
    if (TRN.param('new') !== null) open(TRN.param('new') || undefined);
  }

  TRN.hunts = { huntCard, wireHuntButtons, setupHuntsPage, renderHunts };
})();
