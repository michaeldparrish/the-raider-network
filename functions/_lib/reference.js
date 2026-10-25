/* Read-only game reference data, loaded from the site's own static JSON through the Pages ASSETS binding.
 * The Loot Intel database stays static (it is NOT copied into D1); the API only uses it to validate item IDs
 * and to take canonical item names from the database instead of trusting names sent by the browser. */
let cache = null;

export async function reference(env, request) {
  if (cache) return cache;
  const get = async path => {
    const r = await env.ASSETS.fetch(new Request(new URL(path, request.url)));
    if (!r.ok) throw new Error('reference data unavailable: ' + path);
    return r.json();
  };
  const [items, users] = await Promise.all([get('/data/items.json'), get('/data/users.json')]);
  cache = {
    items: new Map(items.items.map(i => [i.id, i.name])),
    regions: users.regions,
    platforms: users.platforms,
  };
  return cache;
}

/* v6.4: amplification data (tiers, weapons, upgrade trees and costs), used to calculate plan requirements
   server-side so the browser can never submit its own quantities. */
let ampCache = null;
export async function ampReference(env, request) {
  if (ampCache) return ampCache;
  const r = await env.ASSETS.fetch(new Request(new URL('/data/amplification.json', request.url)));
  if (!r.ok) throw new Error('amplification data unavailable');
  const d = await r.json();
  ampCache = {
    asOf: d.meta?.asOf || '',
    tiers: new Map(d.tiers.map(t => [t.id, t])),
    weapons: new Map(d.weapons.map(w => [w.id, w])),
  };
  return ampCache;
}
