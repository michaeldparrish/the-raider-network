/* The Raider Network v6 — data access layer.
 *
 * Two kinds of data:
 *  1. Reference data (items, maps, projects, quests, routes...) — static JSON in /data. Unchanged in v6.
 *  2. Community data. In SERVER mode (production) accounts, sessions, trade posts and offers live in Cloudflare D1
 *     behind /api (see assets/js/api.js and functions/). In DEMO mode (local development without the API)
 *     the v5 browser-only demo storage is used. Loot Hunts and Messages are still browser-only in v6.0.
 *  UI code only calls TRN.store.*, so page code does not care which backend is active.
 */
(function () {
  const TRN = window.TRN;
  const server = () => TRN.mode === 'server';
  const offline = () => TRN.mode === 'offline';

  /* ---------------- reference data ---------------- */
  const FILES = { items: 'items.json', maps: 'maps.json', projects: 'projects.json', quests: 'quests.json', routes: 'routes.json',
    arcs: 'arcs.json', conditions: 'map-conditions.json', users: 'users.json', hunts: 'hunts.json', trades: 'trades.json',
    inventory: 'trade-inventory.json', workshop: 'workshop.json', mapIndex: 'maps/index.json' };
  const cache = {};
  const fetchJson = name => (cache[name] ||= fetch('data/' + FILES[name]).then(r => { if (!r.ok) throw new Error('Could not load ' + FILES[name]); return r.json(); }));

  const DB = (TRN.db = { items: [], maps: [], projects: [], quests: [], routes: [], arcs: [], meta: {}, idx: {} });
  async function load(names) {
    const res = await Promise.all(names.map(fetchJson));
    names.forEach((n, i) => {
      const d = res[i];
      if (n === 'items') { DB.items = d.items; DB.meta = d.meta; DB.idx.item = new Map(d.items.map(x => [x.id, x])); DB.idx.itemName = new Map(d.items.map(x => [x.name.toLowerCase(), x])); }
      if (n === 'maps') { DB.maps = d.maps; DB.idx.map = new Map(d.maps.map(x => [x.id, x])); }
      if (n === 'projects') { DB.projects = d.projects.map(p => ({ ...p, status: projectStatus(p) })); DB.idx.project = new Map(DB.projects.map(x => [x.id, x])); }
      if (n === 'quests') { DB.quests = d.quests; DB.idx.quest = new Map(d.quests.map(x => [x.id, x])); }
      if (n === 'routes') { DB.routes = d.routes; DB.idx.route = new Map(d.routes.map(x => [x.id, x])); }
      if (n === 'arcs') { DB.arcs = d.arcs; }
      if (n === 'conditions') { DB.conditions = d; }
      if (n === 'users') { DB.publicUsers = d.users; DB.stats = d.communityStats; DB.regions = d.regions; DB.platforms = d.platforms; DB.badges = d.badges; }
      if (n === 'hunts') { DB.seedHunts = d.hunts; }
      if (n === 'trades') { DB.seedTrades = d.trades; DB.fairPlay = d.fairPlay; }
      if (n === 'workshop') { DB.workshop = d.stations; }
      if (n === 'inventory') { DB.inventory = d; }
      if (n === 'mapIndex') { DB.mapIndex = d; }
    });
    return DB;
  }

  /* Project status is computed from dates so "Ending Soon" -> "Historical" happens automatically. */
  function projectStatus(p, now = new Date()) {
    if (p.type === 'Permanent') return 'ACTIVE';
    if (!p.endDate) return 'HISTORICAL';
    const end = new Date(p.endDate + 'T23:59:59Z');
    const start = p.startDate ? new Date(p.startDate + 'T00:00:00Z') : null;
    if (now > end) return 'HISTORICAL';
    if (start && now < start) return 'UPCOMING';
    return (end - now) / 864e5 <= 3 ? 'ENDING SOON' : 'ACTIVE';
  }

  const item = id => DB.idx.item?.get(id);
  const map = id => DB.idx.map?.get(id);
  const itemName = id => item(id)?.name || (id ? id.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Unknown item');
  const mapName = id => map(id)?.name || (id ? id.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Any map');
  const findItemByName = n => DB.idx.itemName?.get(String(n || '').trim().toLowerCase()) || null;
  const findMapByName = n => DB.maps.find(m => [m.name, m.shortName, m.id].some(x => String(x).toLowerCase() === String(n || '').trim().toLowerCase())) || null;
  const itemLink = (id, label) => id && item(id) ? `<a class="item-link" href="item.html?id=${encodeURIComponent(id)}">${TRN.esc(label || itemName(id))}</a>` : `<span>${TRN.esc(label || itemName(id))}</span>`;
  const mapLink = (id, label) => id && map(id) ? `<a class="map-link" href="map.html?id=${encodeURIComponent(id)}">${TRN.esc(label || mapName(id))}</a>` : `<span>${TRN.esc(label || mapName(id))}</span>`;
  const projectLink = id => DB.idx.project?.get(id) ? `<a class="project-link" href="projects.html#${encodeURIComponent(id)}">${TRN.esc(DB.idx.project.get(id).name)}</a>` : TRN.esc(id);
  const questName = id => DB.idx.quest?.get(id)?.name || id;

  /* ---------------- community data (demo storage) ---------------- */
  const LS = {
    get(k, f) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : f; } catch { return f; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { console.warn('localStorage unavailable', e); } }
  };
  const minutesAgoIso = m => new Date(Date.now() - (m || 0) * 60000).toISOString();

  /* v4 -> v5 migration: free-text item/map names become shared IDs (unresolved text is kept as itemName). */
  function migrateHunt(h) {
    if (h.itemId !== undefined) return h;
    const it = findItemByName(h.item) || findItemByName((h.item || '').replace(/^ARC /i, 'ARC '));
    const mp = findMapByName(h.map);
    return { id: h.id, userId: h.user_id, displayName: h.display_name, itemId: it?.id || null, itemName: it ? it.name : h.item,
      mapId: mp?.id || null, region: h.region, platform: h.platform, squadSize: Number(h.squad_size) || 3,
      currentMembers: Number(h.current_members) || 1, desiredTime: h.desired_time || '', description: h.details || '',
      status: h.status || 'open', createdAt: h.created_at || new Date().toISOString() };
  }
  function migrateTrade(t) {
    if (t.lookingFor) return t;
    const w = findItemByName(t.want), have = (t.have || '').trim(), hv = findItemByName(have);
    const open = !have || /open to offers|make an offer|offers?/i.test(have);
    return { id: t.id, userId: t.user_id, displayName: t.display_name,
      lookingFor: [{ itemId: w?.id || null, name: w ? w.name : t.want, quantity: 1 }],
      offering: hv ? [{ itemId: hv.id, name: hv.name, quantity: 1 }] : (open ? [] : [{ itemId: null, name: have, quantity: 1 }]),
      openToOffers: open, region: t.region, platform: t.platform, desiredTime: t.desired_time || '', notes: t.details || '',
      status: t.status || 'open', createdAt: t.created_at || new Date().toISOString() };
  }
  const userName = id => (DB.publicUsers || []).find(u => u.id === id)?.displayName || LS.get('trn_users', []).find(u => u.id === id)?.display_name || 'Raider';

  /* v5.1 seed: real Perisher hunts/trades only. Records from the old fictional demo Raiders are removed once;
     anything a local account created is kept. */
  /* ---------------- data versioning / migration (v5.2) ----------------
     TRN_DATA_VERSION is stored in localStorage. When it is older than the current version:
       • keep a record only if its owner is a real account: the public Perisher profile (data/users.json)
         or an account actually registered in THIS browser (trn_users). Fictional seeds from any earlier
         build (NightWolf, RaiderOne, NomadSix, EchoTrader, ...) have no such owner and are discarded.
       • Perisher's seeded records are refreshed from data/*.json; local status changes (closed/completed) are kept.
       • messages are kept only when both participants are real accounts.
     A browser with no stored data simply gets the clean v5.2 seed. */
  const TRN_DATA_VERSION = '5.2';
  TRN.DATA_VERSION = TRN_DATA_VERSION;
  const realOwners = () => new Set([...(DB.publicUsers || []).map(u => u.id), ...LS.get('trn_users', []).map(u => u.id)]);
  /* Each dataset carries its own version marker (trn_data_version:<key>) so a page that loads only some
     datasets (e.g. Loot Hunts doesn't load trades) can never mark the others as migrated without their seed. */
  function migrateKey(key, seedRows, migrate) {
    const vKey = 'trn_data_version:' + key;
    if (LS.get(vKey, null) === TRN_DATA_VERSION || !seedRows) return;
    const owners = realOwners(), rows = LS.get(key, null);
    if (rows) {
      const seedIds = new Set(seedRows.map(r => r.id));
      const migrated = rows.map(migrate), kept = migrated.filter(r => owners.has(r.userId));
      const removed = migrated.filter(r => !owners.has(r.userId)).map(r => r.displayName || r.userId);
      const byId = new Map(kept.map(r => [r.id, r]));
      const fresh = seedRows.map(r => ({ ...r, displayName: userName(r.userId), createdAt: minutesAgoIso(r.minutesAgo), ...(byId.get(r.id) ? { status: byId.get(r.id).status, createdAt: byId.get(r.id).createdAt } : {}) }));
      LS.set(key, [...kept.filter(r => !seedIds.has(r.id)), ...fresh]);
      if (removed.length) console.info('[TRN] removed records from non-existent Raiders:', key, removed);
    }
    try { localStorage.removeItem('trn_seed_' + key); } catch (e) {}
    LS.set(vKey, TRN_DATA_VERSION);
  }
  function migrateAll() {
    migrateKey('trn_hunts', DB.seedHunts, migrateHunt);
    migrateKey('trn_trades', DB.seedTrades, migrateTrade);
    if (LS.get('trn_data_version:trn_messages', null) !== TRN_DATA_VERSION && DB.publicUsers) {
      const owners = realOwners(), msgs = LS.get('trn_messages', null);
      if (msgs) LS.set('trn_messages', msgs.filter(m => owners.has(m.sender_id) && owners.has(m.recipient_id) && !m.demo_reply));
      LS.set('trn_data_version:trn_messages', TRN_DATA_VERSION);
    }
    LS.set('trn_data_version', TRN_DATA_VERSION);
  }
  function seed(key, seedRows, migrate) {
    migrateAll();
    let rows = LS.get(key, null);
    if (!rows) rows = (seedRows || []).map(r => ({ ...r, displayName: userName(r.userId), createdAt: minutesAgoIso(r.minutesAgo) }));
    else rows = rows.map(migrate);
    LS.set(key, rows); return rows;
  }
  const demoHunts = () => seed('trn_hunts', DB.seedHunts, migrateHunt);
  const demoTrades = () => seed('trn_trades', DB.seedTrades, migrateTrade);

  /* ---------------- shared trade inventory (demo safeguards) ----------------
     total      = real quantity owned (data/trade-inventory.json)
     traded     = units already given in completed trades (local, never below zero)
     reserved   = units allocated as specific offers on OPEN listings
     available  = total - traded - reserved   (what new listings / pool offers can still use) */
  function inventoryState(userId, trades) {
    const inv = DB.inventory && DB.inventory.userId === userId ? DB.inventory : null;
    if (!inv) return null;
    const used = LS.get('trn_inventory_used', {})[userId] || {};
    const reserved = {};
    (trades || []).filter(t => t.userId === userId && t.status === 'open').forEach(t => (t.offering || []).forEach(o => { if (o.fromInventory && o.inventoryKey) reserved[o.inventoryKey] = (reserved[o.inventoryKey] || 0) + (Number(o.quantity) || 1); }));
    const items = inv.items.map(x => {
      const traded = Math.min(x.quantityTotal, used[x.key] || 0), owned = x.quantityTotal - traded, res = Math.min(owned, reserved[x.key] || 0);
      return { ...x, traded, owned, reserved: res, overReserved: (reserved[x.key] || 0) > owned, available: Math.max(0, owned - res), unavailable: owned <= 0 };
    });
    return { userId, items, totalUnits: items.reduce((a, x) => a + x.quantityTotal, 0), ownedUnits: items.reduce((a, x) => a + x.owned, 0),
      availableUnits: items.reduce((a, x) => a + x.available, 0), ok: items.every(x => !x.overReserved) };
  }
  function checkAllocation(userId, offering, trades, ignoreTradeId) {
    const st = inventoryState(userId, (trades || []).filter(t => t.id !== ignoreTradeId)); if (!st) return;
    const want = {}; (offering || []).filter(o => o.fromInventory).forEach(o => (want[o.inventoryKey] = (want[o.inventoryKey] || 0) + (Number(o.quantity) || 1)));
    for (const [k, q] of Object.entries(want)) {
      const it = st.items.find(x => x.key === k);
      if (!it) throw new Error('That item is not in your trade inventory.');
      if (q > it.available) throw new Error(`Only ${it.available} ${it.label} available (${it.reserved} reserved on other listings, ${it.traded} already traded).`);
    }
  }

  /* Server trade post -> the client shape the Trade Board renders (same shape as demo rows). */
  const fromServer = t => ({
    id: t.id, server: true, userId: t.owner.id, username: t.owner.username, displayName: t.owner.display_name, avatar: t.owner.avatar_url,
    lookingFor: [{ itemId: t.wanted.item_id, name: t.wanted.name, quantity: t.wanted.quantity }],
    offering: t.offered ? [{ itemId: t.offered.item_id, name: t.offered.name, quantity: t.offered.quantity }] : [],
    openToOffers: t.open_to_offers, region: t.region, platform: t.platform, desiredTime: t.desired_time || '', notes: t.notes || '',
    status: String(t.status).toLowerCase(), createdAt: t.created_at, updatedAt: t.updated_at, closedAt: t.closed_at,
    pendingOffers: t.pending_offers, isMine: t.is_mine, awaiting: t.display_status === 'AWAITING_EXCHANGE',
  });
  /* Client form row -> API body. Item ids are only sent when they exist in Loot Intel; the server re-validates. */
  const toServer = row => {
    const w = row.lookingFor?.[0] || {}, o = (row.offering || []).find(x => !x.fromInventory) || null;
    return {
      wanted_item_id: w.itemId || null, wanted_item_name: w.itemId ? undefined : w.name, wanted_quantity: w.quantity || 1,
      offered_item_id: o?.itemId || null, offered_item_name: o ? (o.itemId ? undefined : o.name) : null, offered_quantity: o ? (o.quantity || 1) : null,
      open_to_offers: !!row.openToOffers, region: row.region, platform: row.platform, desired_time: row.desiredTime || '', notes: row.notes || '',
    };
  };
  let tradeCache = null;

  TRN.store = {
    LS,
    /* Loot Hunts: browser-only in v6.0 (server storage is planned for v6.1). */
    async listHunts() { return demoHunts(); },
    async createHunt(row, user) {
      const rows = demoHunts(); rows.unshift({ ...row, id: 'h' + Date.now(), userId: user.user_id || user.id, displayName: user.display_name, currentMembers: 1, status: 'open', createdAt: new Date().toISOString(), deviceOnly: server() });
      LS.set('trn_hunts', rows);
    },
    async updateHunt(id, patch) { const rows = demoHunts(); const i = rows.findIndex(r => r.id === id); if (i > -1) { rows[i] = { ...rows[i], ...patch }; LS.set('trn_hunts', rows); } },

    async listTrades({ fresh } = {}) {
      if (server()) {
        if (!tradeCache || fresh) tradeCache = TRN.api.get('/trades?status=ALL').then(d => d.trades.map(fromServer)).catch(e => { tradeCache = null; console.error(e); TRN.backendProblem = e.message; return []; });
        return tradeCache;
      }
      if (offline()) return [];
      return demoTrades();
    },
    async createTrade(row, user) {
      if (server()) { const d = await TRN.api.post('/trades', toServer(row)); tradeCache = null; return fromServer(d.trade); }
      if (offline()) throw new Error(TRN.backendProblem || 'Trading is unavailable right now.');
      checkAllocation(user.user_id || user.id, row.offering, await TRN.store.listTrades());
      const rows = demoTrades(); rows.unshift({ ...row, id: 't' + Date.now(), userId: user.user_id || user.id, displayName: user.display_name || 'Raider', status: 'open', createdAt: new Date().toISOString() }); LS.set('trn_trades', rows);
    },
    /* patch: { status } and/or full edit fields in client shape (lookingFor, offering, ...). */
    async updateTrade(id, patch) {
      if (server()) {
        const body = patch.lookingFor ? toServer(patch) : {};
        if (patch.status) body.status = String(patch.status).toUpperCase();
        const d = await TRN.api.patch('/trades/' + encodeURIComponent(id), body); tradeCache = null; return fromServer(d.trade);
      }
      if (offline()) throw new Error(TRN.backendProblem || 'Trading is unavailable right now.');
      const rows = demoTrades(); const i = rows.findIndex(r => r.id === id); if (i > -1) { rows[i] = { ...rows[i], ...patch }; LS.set('trn_trades', rows); }
    },
    async deleteTrade(id) {
      if (server()) { await TRN.api.del('/trades/' + encodeURIComponent(id)); tradeCache = null; return; }
      if (offline()) throw new Error(TRN.backendProblem || 'Trading is unavailable right now.');
      LS.set('trn_trades', demoTrades().filter(r => r.id !== id));
    },
    /* Offers (server mode only). */
    offers: {
      forTrade: id => TRN.api.get('/trades/' + encodeURIComponent(id) + '/offers'),
      create: (id, body) => TRN.api.post('/trades/' + encodeURIComponent(id) + '/offers', body),
      act: (offerId, action) => TRN.api.patch('/offers/' + encodeURIComponent(offerId), { action }),
      mine: () => TRN.api.get('/me/offers'),
    },
    /* The Perisher trade inventory is a demo-mode feature (data/trade-inventory.json). Server inventories are planned. */
    inventory(userId, trades) { return server() || offline() ? null : inventoryState(userId, trades); },
    /* Owner marks a listing as traded: decrement the given inventory units (never below zero) and close the listing. */
    async completeTrade(tradeId, given) {
      const trades = await TRN.store.listTrades(); const t = trades.find(x => x.id === tradeId); if (!t) throw new Error('Listing not found.');
      if (t.status !== 'open') throw new Error('This listing is already closed.');
      const st = inventoryState(t.userId, trades.filter(x => x.id !== tradeId));
      const usedAll = LS.get('trn_inventory_used', {}); const used = usedAll[t.userId] || {};
      for (const g of given || []) {
        const it = st?.items.find(x => x.key === g.key); const q = Number(g.quantity) || 0;
        if (!it || q <= 0) continue;
        if (q > it.available) throw new Error(`Cannot give ${q} ${it.label}: only ${it.available} unreserved.`);
        used[g.key] = Math.min(it.quantityTotal, (used[g.key] || 0) + q);
      }
      usedAll[t.userId] = used; LS.set('trn_inventory_used', usedAll);
      await TRN.store.updateTrade(tradeId, { status: 'closed', completedAt: new Date().toISOString(), given });
      LS.set('trn_trades_completed', (LS.get('trn_trades_completed', 0) || 0) + 1);
    },
    /* Messages: browser-only in v6.0 (server messaging is planned for v6.1). */
    async listMessages(user) {
      const uid = user.user_id || user.id;
      return LS.get('trn_messages', []).filter(m => m.sender_id === uid || m.recipient_id === uid);
    },
    async sendMessage(msg) {
      if (server()) throw new Error('Private messages are not live yet. Use Make Offer on the Trade Board to contact a Raider.');
      const all = LS.get('trn_messages', []); all.push({ id: 'm' + Date.now(), created_at: new Date().toISOString(), ...msg }); LS.set('trn_messages', all);
    },
    /* Public profile lookup (never returns email or private Raider tag for other users). */
    publicUser(id) {
      const st = tradeCacheSync.find(t => t.userId === id);
      if (st) return { id, displayName: st.displayName, avatar: st.avatar, username: st.username };
      const d = (DB.publicUsers || []).find(u => u.id === id);
      if (d) return d;
      const u = LS.get('trn_users', []).find(x => x.id === id);
      return u ? { id: u.id, displayName: u.display_name, platform: u.platform, region: u.region, avatar: u.avatar || null, archetype: null, badges: [] } : null;
    },
    async loadServerStats() {
      if (!server()) return null;
      try { TRN.serverStats = (await TRN.api.get('/stats')).stats; } catch (e) { console.error(e); }
      return TRN.serverStats;
    },
    stats() {
      if (server()) return { ...(DB.stats || {}), tradesCompleted: TRN.serverStats?.completed_trades ?? 0 };
      return { ...(DB.stats || {}), tradesCompleted: (DB.stats?.tradesCompleted || 0) + (LS.get('trn_trades_completed', 0) || 0) };
    }
  };
  let tradeCacheSync = [];
  const _list = TRN.store.listTrades;
  TRN.store.listTrades = async (o) => { const r = await _list(o); if (server()) tradeCacheSync = r; return r; };

  TRN.data = { load, item, map, itemName, mapName, itemLink, mapLink, projectLink, questName, findItemByName, findMapByName, projectStatus };
})();
