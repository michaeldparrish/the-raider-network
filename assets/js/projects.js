/* The Raider Network v5 — Projects (projects.html) + compact project cards for the homepage. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN, D = () => TRN.db;
  const fmtDate = d => (d ? new Date(d + 'T12:00:00Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : null);
  const dates = p => p.type === 'Permanent' ? 'Permanent project' : (p.startDate || p.endDate) ? `${fmtDate(p.startDate) || 'Unknown start'} – ${fmtDate(p.endDate) || 'Unknown end'}` : 'Dates not verified';
  const ORDER = { 'ENDING SOON': 0, ACTIVE: 1, UPCOMING: 2, HISTORICAL: 3 };
  const sorted = () => [...D().projects].sort((a, b) => ORDER[a.status] - ORDER[b.status] || (b.endDate || '').localeCompare(a.endDate || ''));
  const reqChip = r => { const it = TRN.data.item(r.itemId); return `<a class="req-chip ${it ? 'rarity-edge-' + it.rarity.toLowerCase() : ''}" href="${it ? 'item.html?id=' + encodeURIComponent(r.itemId) : '#'}"><img src="${TRN.img(it?.image)}" alt="" loading="lazy"><span>${esc(r.name || TRN.data.itemName(r.itemId))}</span><b>×${r.quantity}</b></a>`; };

  function projectCompact(p) {
    const keyItems = p.stages.flatMap(s => s.requiredItems).map(r => ({ r, it: TRN.data.item(r.itemId) })).filter(x => x.it).sort((a, b) => b.it.intelScore - a.it.intelScore).slice(0, 4);
    return `<article class="project-mini status-${TRN.slug(p.status)}"><header>${TRN.statusChip(p.status)}<small>${esc(dates(p))}</small></header>
      <h3><a href="projects.html#${esc(p.id)}">${esc(p.name)}</a></h3>
      <div class="req-row">${keyItems.map(x => reqChip(x.r)).join('')}</div></article>`;
  }

  function projectCard(p) {
    return `<article class="project-full status-${TRN.slug(p.status)}" id="${esc(p.id)}" data-status="${esc(p.status)}" data-search="${esc((p.name + ' ' + (p.aliases || []).join(' ') + ' ' + p.stages.flatMap(s => s.requiredItems.map(r => TRN.data.itemName(r.itemId))).join(' ')).toLowerCase())}">
      <header class="project-full__head">
        <div><div class="chip-row">${TRN.statusChip(p.status)}<span class="cat-chip">${esc(p.type)}</span>${TRN.confChip(p.dataConfidence)}</div>
          <h2>${esc(p.name)}${p.aliases?.length ? ` <small>also called ${esc(p.aliases.join(', '))}</small>` : ''}</h2>
          <p>${esc(p.description || '')}</p></div>
        <div class="project-dates">${TRN.icon('time')}<span>${esc(dates(p))}</span>${p.datesNote ? `<small>${esc(p.datesNote)}</small>` : ''}</div>
      </header>
      <div class="stage-list">${p.stages.map(s => `<section class="stage"><div class="stage__num">${s.stage}</div><div class="stage__body"><h4>${esc(s.name || 'Stage ' + s.stage)}</h4>
          ${s.requiredItems.length ? `<div class="req-row">${s.requiredItems.map(reqChip).join('')}</div>` : `<p class="muted">${s.nonItemRequirement ? 'Non-item objective (category contributions, tasks or ARC damage).' : 'No item requirements recorded.'}</p>`}
          ${s.rewards?.length ? `<div class="reward-row"><span>Rewards</span>${s.rewards.map(r => r.itemId && TRN.data.item(r.itemId) ? `${TRN.data.itemLink(r.itemId)} ×${r.quantity}` : esc(r.name || TRN.data.itemName(r.itemId)) + (r.quantity > 1 ? ' ×' + r.quantity : '')).join(' · ')}</div>` : ''}
        </div></section>`).join('')}</div>
      <footer class="project-full__foot"><a class="btn btn-ghost btn-sm" href="loot.html?project=${encodeURIComponent(p.id)}">${TRN.icon('loot-intel')} All required items in Loot Intel</a>
        <span class="source-inline">Sources: ${(p.sources || []).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a>`).join(' · ')}</span>${p.rewardsNote ? `<small class="muted">${esc(p.rewardsNote)}</small>` : ''}</footer>
    </article>`;
  }

  function setupProjectsPage() {
    const list = $('#projectList'); if (!list) return;
    list.innerHTML = sorted().map(projectCard).join('');
    const counts = D().projects.reduce((a, p) => ((a[p.status] = (a[p.status] || 0) + 1), a), {});
    $$('.tab-btn[data-status]').forEach(b => { const n = b.dataset.status ? counts[b.dataset.status] || 0 : D().projects.length; b.querySelector('b').textContent = n; });
    let status = '';
    const apply = () => { const q = ($('#projectSearch').value || '').toLowerCase(); $$('.project-full').forEach(c => { c.style.display = (!status || c.dataset.status === status) && (!q || c.dataset.search.includes(q)) ? '' : 'none'; }); };
    $$('.tab-btn[data-status]').forEach(b => (b.onclick = () => { status = b.dataset.status; $$('.tab-btn').forEach(x => x.classList.toggle('active', x === b)); apply(); }));
    $('#projectSearch').addEventListener('input', apply);
    if (location.hash) { const el = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (el) { el.classList.add('flash'); setTimeout(() => el.scrollIntoView({ block: 'start' }), 60); } }
  }

  TRN.projects = { projectCompact, projectCard, setupProjectsPage, sorted, dates };
})();
