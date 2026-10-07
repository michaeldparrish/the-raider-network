/* Cryptography and abuse controls. Everything here uses the platform Web Crypto API (no hand-rolled primitives).
 *
 * Passwords: PBKDF2-HMAC-SHA256 via crypto.subtle, 16-byte random salt, 256-bit output.
 *   The Cloudflare Workers runtime caps PBKDF2 at 100,000 iterations, so that is what we use. The hash string
 *   records its own algorithm and iteration count, so stronger settings can be rolled out later and existing
 *   users are re-hashed transparently on their next successful login (see needsRehash).
 * Sessions: 256-bit random tokens from crypto.getRandomValues; only SHA-256(token) is stored.
 */

const enc = new TextEncoder();
export const PBKDF2_ITERATIONS = 100000;

const b64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf)));
const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const b64url = buf => b64(buf).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');

export const randomId = prefix => prefix + '_' + hex(crypto.getRandomValues(new Uint8Array(12)));
export const randomToken = () => b64url(crypto.getRandomValues(new Uint8Array(32)));
export const sha256Hex = async text => hex(await crypto.subtle.digest('SHA-256', enc.encode(text)));

async function pbkdf2(password, salt, iterations) {
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  return crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt, iterations }, key, 256);
}

export async function hashPassword(password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const bits = await pbkdf2(password, salt, PBKDF2_ITERATIONS);
  return `pbkdf2_sha256$${PBKDF2_ITERATIONS}$${b64(salt)}$${b64(bits)}`;
}

/* Constant-time comparison of two equal-length byte arrays. */
function equalBytes(a, b) {
  if (a.byteLength !== b.byteLength) return false;
  if (crypto.subtle.timingSafeEqual) return crypto.subtle.timingSafeEqual(a, b);
  let d = 0; for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i]; return d === 0;
}

export async function verifyPassword(password, stored) {
  const parts = String(stored || '').split('$');
  if (parts.length !== 4 || parts[0] !== 'pbkdf2_sha256') return false;
  const iterations = Number(parts[1]);
  if (!Number.isInteger(iterations) || iterations < 1 || iterations > PBKDF2_ITERATIONS) return false;
  const bits = new Uint8Array(await pbkdf2(password, unb64(parts[2]), iterations));
  return equalBytes(bits, unb64(parts[3]));
}
export const needsRehash = stored => !String(stored).startsWith(`pbkdf2_sha256$${PBKDF2_ITERATIONS}$`);

/* A real PBKDF2 hash of a random, discarded password. Verifying against it when a login names an unknown account
   makes that response take as long as a wrong password does (no timing oracle for which accounts exist).
   It is a constant so even the first request after a cold start does exactly one PBKDF2 run. */
const DUMMY_HASH = 'pbkdf2_sha256$100000$OsfyqwuVt8ShyeknZheLWA==$KeNH0pHzRdLSY3G5fESaRZQ/BZ6IoTdkbVsBG/80RXc=';
export async function burnPasswordCheck(password) { await verifyPassword(password, DUMMY_HASH); }

/* ---------------------------------------------------------------- rate limiting
   Fixed-window counters in D1. The IP part of a key is hashed, so raw IPs are never stored.
   This is an application-level backstop; docs/CLOUDFLARE-BACKEND-SETUP.md also recommends a Cloudflare
   WAF rate-limiting rule on /api/auth/* at the edge. */
export const ipKey = async ip => (await sha256Hex('trn-ip:' + ip)).slice(0, 32);

export async function rateCount(db, bucket, windowSec) {
  const now = Math.floor(Date.now() / 1000);
  const row = await db.prepare('SELECT window_start, count FROM rate_limits WHERE bucket = ?1').bind(bucket).first();
  if (!row || now - row.window_start >= windowSec) return { count: 0, retryAfter: 0 };
  return { count: row.count, retryAfter: windowSec - (now - row.window_start) };
}
export async function rateHit(db, bucket, windowSec) {
  const now = Math.floor(Date.now() / 1000);
  return db.prepare(`INSERT INTO rate_limits (bucket, window_start, count) VALUES (?1, ?2, 1)
      ON CONFLICT (bucket) DO UPDATE SET
        count        = CASE WHEN ?2 - window_start >= ?3 THEN 1  ELSE count + 1 END,
        window_start = CASE WHEN ?2 - window_start >= ?3 THEN ?2 ELSE window_start END
      RETURNING count, window_start`).bind(bucket, now, windowSec).first();
}
export const rateReset = (db, bucket) => db.prepare('DELETE FROM rate_limits WHERE bucket = ?1').bind(bucket).run();
/* Give back one reserved attempt (e.g. a successful login or a registration that failed validation late). */
export const rateUndo = (db, bucket) => db.prepare('UPDATE rate_limits SET count = MAX(count - 1, 0) WHERE bucket = ?1').bind(bucket).run();

/* Reserve-then-act limiter: the attempt is counted atomically BEFORE the work happens, so parallel requests cannot
   all slip under the limit. Throws (via the caller-supplied error factory) when the bucket is over the limit. */
export async function rateLimit(db, bucket, limit, windowSec, onLimited) {
  const r = await rateHit(db, bucket, windowSec);
  if (r.count > limit) throw onLimited(windowSec - (Math.floor(Date.now() / 1000) - r.window_start));
}
