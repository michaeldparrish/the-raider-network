/* The Raider Network v5 — shared helpers. Loaded first on every page. */
(function () {
  const TRN = (window.TRN = window.TRN || {});
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  const IMG = 'assets/images/';

  const ageFromIso = iso => {
    const m = Math.max(1, Math.floor((Date.now() - new Date(iso)) / 60000));
    return m < 60 ? `${m}m ago` : m < 1440 ? `${Math.floor(m / 60)}h ago` : `${Math.floor(m / 1440)}d ago`;
  };
  const num = n => (n == null ? '—' : Number(n).toLocaleString());
  const param = k => new URLSearchParams(location.search).get(k);
  const slug = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

  /* Icons cut from the supplied icon sheet (board 08). `icon('trade')` -> <img> */
  const ICONS = ['search', 'loot-intel', 'map', 'route', 'squad', 'message', 'trade', 'profile', 'project', 'inventory',
    'rarity', 'recycle', 'crafting', 'danger', 'difficulty', 'time', 'value', 'filter', 'sort', 'location', 'extraction',
    'warning', 'online', 'settings'];
  const icon = (name, cls = '') =>
    ICONS.includes(name)
      ? `<img class="ico ${cls}" src="${IMG}ui/icon-${name}.png" alt="" aria-hidden="true">`
      : `<span class="ico ${cls}" aria-hidden="true"></span>`;

  /* Small inline SVGs for spots where a raster icon is too heavy (buttons, chips). */
  const svg = name => {
    const p = {
      arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>', close: '<path d="M6 6l12 12M18 6 6 18"/>',
      menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', swap: '<path d="M7 7h11l-3-3M17 17H6l3 3"/>',
      check: '<path d="m5 12 4 4 10-10"/>', pin: '<path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
      users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
      radio: '<rect x="3" y="8" width="18" height="12" rx="1"/><path d="m8 8 8-5M7 14h4M15 14h2"/>',
      clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
      message: '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z"/>', info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>'
    }[name] || '';
    return `<svg class="svg-ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
  };

  /* Rarity / intel / confidence presentation */
  const RARITIES = ['Common', 'Uncommon', 'Rare', 'Epic', 'Legendary'];
  const rarityBadge = (r, size = '') =>
    `<span class="rarity-chip rarity-${esc((r || 'common').toLowerCase())} ${size}"><img src="${IMG}ui/rarity-${esc((r || 'common').toLowerCase())}.png" alt="">${esc(r || 'Unknown')}</span>`;
  const intelBand = s => (s >= 90 ? 'CRITICAL' : s >= 75 ? 'HIGH PRIORITY' : s >= 60 ? 'VALUABLE' : s >= 40 ? 'USEFUL' : 'LOW VALUE');
  const intelClass = s => (s >= 90 ? 'band-critical' : s >= 75 ? 'band-high' : s >= 60 ? 'band-valuable' : s >= 40 ? 'band-useful' : 'band-low');
  const intelBadge = (s, large = false) =>
    `<div class="intel-badge ${intelClass(s)} ${large ? 'intel-badge--lg' : ''}" title="Raider Network Intel Score — ${intelBand(s)}"><strong>${s}</strong><small>${large ? 'Raider Network<br>Intel Score' : 'Intel'}</small><em>${intelBand(s)}</em></div>`;
  const demandLabel = d => (d == null ? 'Unknown' : d >= 7.5 ? 'Very High' : d >= 5.5 ? 'High' : d >= 3 ? 'Normal' : 'Low');
  const demandKey = d => ({ 'Very High': 'very-high', High: 'high', Normal: 'normal', Low: 'low' }[demandLabel(d)] || 'normal');
  const demandChip = d => `<span class="demand-chip demand-${demandKey(d)}"><img src="${IMG}ui/demand-${demandKey(d)}.png" alt="">${demandLabel(d)} demand</span>`;
  const diffLabel = d => (d == null ? 'Unknown' : d >= 8.5 ? 'Extreme' : d >= 7 ? 'Very Hard' : d >= 5 ? 'Hard' : d >= 3 ? 'Moderate' : 'Easy');
  const CONF = { 'OFFICIAL': 'official', 'VERIFIED COMMUNITY': 'verified', 'COMMUNITY REPORT': 'report', 'UNVERIFIED': 'unverified', 'NETWORK ESTIMATE': 'estimate' };
  const confChip = c => (c ? `<span class="conf-chip conf-${CONF[c] || 'unverified'}" title="Data confidence">${esc(c)}</span>` : '');
  const RECO = { 'KEEP': 'keep', 'KEEP ONE': 'keep', 'RECYCLE': 'recycle', 'SELL': 'sell', 'TRADE INTEREST': 'trade', 'PROJECT CRITICAL': 'project' };
  const recoBadge = r =>
    r ? `<span class="reco-badge reco-${slug(r)}"><img src="${IMG}ui/action-${RECO[r] || 'keep'}.png" alt="">${esc(r)}</span>`
      : `<span class="reco-badge reco-gear">GEAR / EQUIPMENT</span>`;
  const statusChip = s => `<span class="status-chip status-${slug(s)}">${esc(String(s).toUpperCase())}</span>`;
  const img = p => (p ? (p.startsWith('assets/') ? p : IMG + p) : IMG + 'items/art-scrap-electronics.webp');

  const toast = (msg) => {
    let t = $('#toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('show'); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 2600);
  };
  const debounce = (fn, ms = 120) => { let h; return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); }; };

  Object.assign(TRN, { $, $$, esc, ageFromIso, num, param, slug, icon, svg, IMG, img, RARITIES, rarityBadge, intelBand, intelClass,
    intelBadge, demandLabel, demandChip, diffLabel, confChip, recoBadge, statusChip, toast, debounce });
})();
