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
