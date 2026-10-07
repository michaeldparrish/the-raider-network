/* Session lifecycle. Identity is ALWAYS derived from the HttpOnly session cookie, never from a user id sent by the browser. */
import { parseCookies, sessionCookie, clearSessionCookie, sessionCookieName, unauthorized, nowIso } from './http.js';
import { randomId, randomToken, sha256Hex } from './security.js';
import * as repo from './repo.js';

export const SESSION_DAYS = 30;
const TOUCH_EVERY_MS = 15 * 60 * 1000;   // write last_used_at at most every 15 minutes per session

export async function startSession(db, request, userId) {
  const token = randomToken();
  await repo.createSession(db, {
    id: randomId('ses'), user_id: userId, token_hash: await sha256Hex(token),
    expires_at: new Date(Date.now() + SESSION_DAYS * 864e5).toISOString(),
    user_agent: (request.headers.get('User-Agent') || '').slice(0, 200),
  });
  return sessionCookie(request, token, SESSION_DAYS * 86400);
}

/* Returns { user, sessionId } or null. Expired or unknown tokens are rejected (and expired rows removed). */
export async function currentSession(db, request) {
  const token = parseCookies(request)[sessionCookieName(request)];
  if (!token || token.length < 32 || token.length > 64) return null;
  const hash = await sha256Hex(token);
  const row = await repo.sessionByTokenHash(db, hash);
  if (!row) return null;
  if (row.expires_at <= nowIso()) { await repo.deleteSession(db, row.session_id); return null; }
  if (row.status !== 'active') return null;
  if (Date.now() - Date.parse(row.last_used_at) > TOUCH_EVERY_MS) await repo.touchSession(db, row.session_id);
  const { session_id, expires_at, last_used_at, ...user } = row;
  return { user, sessionId: session_id };
}

export async function requireUser(ctx) {
  if (!ctx.session) throw unauthorized();
  return ctx.session.user;
}

export async function endSession(db, request) {
  const token = parseCookies(request)[sessionCookieName(request)];
  if (token) await repo.deleteSessionByTokenHash(db, await sha256Hex(token));
  return clearSessionCookie(request);
}
