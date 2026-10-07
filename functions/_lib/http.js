/* HTTP helpers shared by every API handler: JSON responses, typed errors, body parsing, cookies, CSRF guard. */

export class ApiError extends Error {
  constructor(status, code, message, field) { super(message); this.status = status; this.code = code; this.field = field; }
}
export const bad = (message, field) => new ApiError(400, 'validation', message, field);
export const unauthorized = (message = 'Please log in to do that.') => new ApiError(401, 'unauthorized', message);
export const forbidden = (message = 'You can only change your own content.') => new ApiError(403, 'forbidden', message);
export const notFound = (message = 'Not found.') => new ApiError(404, 'not_found', message);
export const conflict = (message, field) => new ApiError(409, 'conflict', message, field);
export const tooMany = (retryAfter) => Object.assign(new ApiError(429, 'rate_limited', `Too many attempts. Try again in ${Math.max(1, Math.ceil(retryAfter / 60))} minute(s).`), { retryAfter });

const BASE_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'same-origin',
};

export function json(data, status = 200, extra = {}) {
  const h = new Headers(BASE_HEADERS);
  for (const [k, v] of Object.entries(extra)) {
    if (Array.isArray(v)) v.forEach(x => h.append(k, x)); else h.set(k, v);
  }
  return new Response(JSON.stringify(data), { status, headers: h });
}

export function errorResponse(err) {
  if (err instanceof ApiError) {
    const extra = err.retryAfter ? { 'Retry-After': String(err.retryAfter) } : {};
    return json({ error: { code: err.code, message: err.message, ...(err.field ? { field: err.field } : {}) } }, err.status, extra);
  }
  console.error('Unhandled API error', err && (err.stack || err.message || err));
  return json({ error: { code: 'server_error', message: 'Something went wrong on our side. Please try again.' } }, 500);
}

const MAX_BODY = 16 * 1024;
export async function readJson(request) {
  const type = request.headers.get('Content-Type') || '';
  if (!type.toLowerCase().startsWith('application/json')) throw new ApiError(415, 'unsupported_media_type', 'Requests must be sent as JSON.');
  const text = await request.text();
  if (text.length > MAX_BODY) throw new ApiError(413, 'too_large', 'Request body is too large.');
  if (!text) return {};
  try { const v = JSON.parse(text); if (!v || typeof v !== 'object' || Array.isArray(v)) throw 0; return v; }
  catch { throw bad('Malformed JSON body.'); }
}

/* CSRF defence for state-changing requests (in addition to SameSite=Lax cookies):
   1. a custom header that cross-site HTML forms cannot send without a CORS preflight (which we never grant), and
   2. when the browser sends an Origin header it must be this site's origin. */
export function assertSameOrigin(request) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(request.method)) return;
  if (request.headers.get('X-TRN-CSRF') !== '1') throw new ApiError(403, 'csrf', 'Missing request header.');
  const origin = request.headers.get('Origin');
  if (origin && origin !== new URL(request.url).origin) throw new ApiError(403, 'csrf', 'Cross-site request blocked.');
}

export function parseCookies(request) {
  const out = {};
  (request.headers.get('Cookie') || '').split(';').forEach(p => {
    const i = p.indexOf('='); if (i < 0) return;
    const k = p.slice(0, i).trim(), v = p.slice(i + 1).trim();
    if (!k || k in out) return;
    try { out[k] = decodeURIComponent(v); } catch { out[k] = v; }   // a malformed third-party cookie must not break the API
  });
  return out;
}

/* Production (HTTPS) uses the __Host- prefix, which the browser only accepts with Secure, Path=/ and no Domain.
   Plain-HTTP local development (wrangler pages dev on http://localhost) cannot set Secure cookies, so it uses a
   different, unprefixed name. Both are HttpOnly and SameSite=Lax. */
export function sessionCookieName(request) {
  return new URL(request.url).protocol === 'https:' ? '__Host-trn_session' : 'trn_session';
}
export function sessionCookie(request, token, maxAgeSec) {
  const secure = new URL(request.url).protocol === 'https:';
  const parts = [`${sessionCookieName(request)}=${token}`, 'Path=/', 'HttpOnly', 'SameSite=Lax', `Max-Age=${maxAgeSec}`];
  if (secure) parts.push('Secure');
  return parts.join('; ');
}
export const clearSessionCookie = request => sessionCookie(request, '', 0);

export const clientIp = request => request.headers.get('CF-Connecting-IP') || request.headers.get('X-Forwarded-For')?.split(',')[0].trim() || 'local';
export const nowIso = () => new Date().toISOString();
