/* Tiny method + path router for /api/*. Adds the session to ctx and turns thrown ApiErrors into JSON responses. */
import { json, errorResponse, assertSameOrigin, ApiError } from './http.js';
import { currentSession } from './session.js';
import * as h from './handlers.js';

const ROUTES = [
  ['GET', '/api/health', h.health],
  ['POST', '/api/auth/register', h.register],
  ['POST', '/api/auth/login', h.login],
  ['POST', '/api/auth/logout', h.logout],
  ['GET', '/api/auth/session', h.session],
  ['PATCH', '/api/me', h.updateMe],
  ['GET', '/api/me/offers', h.myOffers],
  ['GET', '/api/users/:username', h.publicProfile],
  ['GET', '/api/trades', h.listTrades],
  ['POST', '/api/trades', h.createTrade],
  ['GET', '/api/trades/:id', h.getTrade],
  ['PATCH', '/api/trades/:id', h.updateTrade],
  ['DELETE', '/api/trades/:id', h.deleteTrade],
  ['GET', '/api/trades/:id/offers', h.listOffers],
  ['POST', '/api/trades/:id/offers', h.createOffer],
  ['PATCH', '/api/offers/:id', h.updateOffer],
  ['POST', '/api/offers/:id/handoff', h.openHandoffForOffer],
  ['GET', '/api/handoffs', h.listHandoffs],
  ['GET', '/api/handoffs/:id', h.getHandoff],
  ['POST', '/api/handoffs/:id/seen', h.seenHandoff],
  ['POST', '/api/handoffs/:id/confirm', h.confirmHandoff],
  ['POST', '/api/handoffs/:id/cancel', h.cancelHandoff],
  ['POST', '/api/handoffs/:id/report', h.reportHandoff],
  ['GET', '/api/stats', h.stats],
].map(([method, path, fn]) => {
  const keys = [];
  const re = new RegExp('^' + path.replace(/:(\w+)/g, (_, k) => { keys.push(k); return '([A-Za-z0-9_-]{1,64})'; }) + '/?$');
  return { method, re, keys, fn };
});

export async function handle(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  try {
    const matches = ROUTES.filter(r => r.re.test(url.pathname));
    if (!matches.length) throw new ApiError(404, 'not_found', 'Unknown API endpoint.');
    const route = matches.find(r => r.method === request.method || (request.method === 'HEAD' && r.method === 'GET'));
    if (!route) return json({ error: { code: 'method_not_allowed', message: 'Method not allowed.' } }, 405, { Allow: [...new Set(matches.map(r => r.method))].join(', ') });
    if (!env.DB) throw new ApiError(503, 'no_database', 'The D1 database is not bound to this deployment (binding name: DB). See docs/CLOUDFLARE-BACKEND-SETUP.md.');
    assertSameOrigin(request);
    const params = {}; const m = url.pathname.match(route.re); route.keys.forEach((k, i) => (params[k] = m[i + 1]));
    const ctx = { request, env, db: env.DB, url, params, waitUntil: context.waitUntil?.bind(context) };
    ctx.session = await currentSession(env.DB, request);
    return await route.fn(ctx);
  } catch (err) {
    if (err && /no such table/i.test(String(err.message))) return json({ error: { code: 'not_migrated', message: 'The database has not been migrated yet. Run the D1 migrations (docs/CLOUDFLARE-BACKEND-SETUP.md).' } }, 503);
    return errorResponse(err);
  }
}
