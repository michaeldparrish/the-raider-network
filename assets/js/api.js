/* The Raider Network v6 — browser client for the Cloudflare Pages Functions API (/api/*).
 *
 * Decides which backend the page uses (TRN.mode):
 *   'server'  – /api/health answered: accounts and trades live in Cloudflare D1. This is production.
 *   'demo'    – no API (e.g. `python3 -m http.server`) AND the page is served from a development host listed in
 *               RAIDER_CONFIG.DEMO_HOSTS. Data stays in this browser and the header shows DEMO MODE.
 *   'offline' – anywhere else without a working API. Accounts and trading are disabled with a clear message;
 *               production never silently falls back to browser storage.
 * The session cookie is HttpOnly, so this file never sees or stores the session token.
 */
(function () {
  const TRN = (window.TRN = window.TRN || {});
  const cfg = window.RAIDER_CONFIG || {};

  class ApiError extends Error {
    constructor(status, body) {
      super(body?.error?.message || `Request failed (${status})`);
      this.status = status; this.code = body?.error?.code; this.field = body?.error?.field;
    }
  }

  async function request(method, path, body) {
    const opts = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (method !== 'GET') opts.headers['X-TRN-CSRF'] = '1';
    if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    let res;
    try { res = await fetch('/api' + path, opts); }
    catch { throw new ApiError(0, { error: { message: 'Could not reach The Raider Network server. Check your connection and try again.' } }); }
    let data = null;
    try { data = await res.json(); } catch { /* non-JSON */ }
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }

  const isDevHost = () => (cfg.DEMO_HOSTS || ['localhost', '127.0.0.1', '[::1]']).includes(location.hostname);
  let modePromise = null;
  function init() {
    return (modePromise ||= (async () => {
      const forced = String(cfg.BACKEND || 'auto').toLowerCase();
      if (forced === 'demo') return set('demo');
      try {
        const res = await fetch('/api/health', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        const type = res.headers.get('Content-Type') || '';
        if (type.includes('application/json')) {
          const h = await res.json().catch(() => null);
          if (res.ok && h?.ok) return set('server');
          TRN.backendProblem = h?.error?.message || h?.hint || 'The server is not ready yet.';
          return set('offline');
        }
      } catch { /* network error: no API */ }
      if (forced !== 'server' && isDevHost()) return set('demo');
      TRN.backendProblem = 'Accounts and trading are temporarily unavailable. Please try again shortly.';
      return set('offline');
    })());
  }
  function set(mode) {
    TRN.mode = mode;
    TRN.serverMode = mode === 'server';
    TRN.demoMode = mode === 'demo';
    document.documentElement.dataset.backend = mode;
    return mode;
  }

  TRN.ApiError = ApiError;
  TRN.api = {
    init,
    get: p => request('GET', p),
    post: (p, b = {}) => request('POST', p, b),
    patch: (p, b = {}) => request('PATCH', p, b),
    del: p => request('DELETE', p),
  };
})();
