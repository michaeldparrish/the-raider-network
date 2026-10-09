/* Server-side input validation. The browser validates too, but these rules are the ones that count.
 * Text is normalised (NFC), stripped of control characters and length-limited before it reaches SQL.
 * Output escaping happens in the browser (TRN.esc) because the API only ever returns JSON. */
import { bad } from './http.js';

const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F​-‏‪-‮⁦-⁩]/g;

export function text(value, { field, label = field, max, min = 0, required = false, multiline = false }) {
  if (value === undefined || value === null) value = '';
  if (typeof value !== 'string' && typeof value !== 'number') throw bad(`${label} must be text.`, field);
  let s = String(value).normalize('NFC').replace(CONTROL, '');
  s = multiline ? s.replace(/\r\n?/g, '\n').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim() : s.replace(/\s+/g, ' ').trim();
  if (!s && required) throw bad(`${label} is required.`, field);
  if (s && s.length < min) throw bad(`${label} must be at least ${min} characters.`, field);
  if (s.length > max) throw bad(`${label} must be ${max} characters or fewer.`, field);
  return s || null;
}

export function int(value, { field, label = field, min, max, fallback }) {
  if (value === undefined || value === null || value === '') return fallback;
  const n = Number(value);
  if (!Number.isInteger(n) || n < min || n > max) throw bad(`${label} must be a whole number from ${min} to ${max}.`, field);
  return n;
}

const RESERVED = new Set(['admin', 'administrator', 'root', 'system', 'support', 'moderator', 'mod', 'staff', 'official', 'embark',
  'raidernetwork', 'the_raider_network', 'raider_network', 'api', 'null', 'undefined', 'me', 'help', 'security', 'everyone']);

export function username(v) {
  const s = String(v ?? '').trim().toLowerCase();
  if (!/^[a-z0-9_]{3,20}$/.test(s)) throw bad('Username must be 3–20 characters: letters, numbers and underscores only.', 'username');
  if (!/[a-z]/.test(s)) throw bad('Username must contain at least one letter.', 'username');
  if (RESERVED.has(s)) throw bad('That username is reserved. Please choose another.', 'username');
  return s;
}
export function displayName(v) {
  const s = text(v, { field: 'display_name', label: 'Display name', max: 30, min: 2, required: true });
  if (!/^[\p{L}\p{N}][\p{L}\p{N} ._'-]*$/u.test(s)) throw bad('Display name can use letters, numbers, spaces and . _ \' - only.', 'display_name');
  return s;
}
export function email(v) {
  const s = String(v ?? '').trim().toLowerCase();
  if (s.length > 254 || !/^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[a-z]{2,}$/i.test(s)) throw bad('Please enter a valid email address.', 'email');
  return s;
}
const COMMON = new Set(['password', 'password1', 'password12', 'password123', 'password1234', '1234567890', '12345678910', 'qwertyuiop',
  'iloveyou12', 'letmein123', 'arcraiders', 'arcraiders1', 'raidernetwork', 'speranza123', 'abcdefghij', 'qwerty1234', '1q2w3e4r5t']);
export function password(v, { username: u, email: e } = {}) {
  if (typeof v !== 'string') throw bad('Password is required.', 'password');
  if (v.length < 10) throw bad('Password must be at least 10 characters.', 'password');
  if (v.length > 128) throw bad('Password must be 128 characters or fewer.', 'password');
  const lower = v.toLowerCase();
  if (COMMON.has(lower) || /^(.)\1+$/.test(v)) throw bad('That password is too common. Please choose another.', 'password');
  if ((u && lower.includes(u.toLowerCase())) || (e && lower === e.toLowerCase())) throw bad('Password must not contain your username or email.', 'password');
  return v;
}
export function avatar(v) {
  if (v === undefined || v === null || v === '') return null;
  const s = String(v);
  if (!/^raiders\/raider-[a-z-]{3,40}\.webp$/.test(s)) throw bad('Please choose one of the provided portraits.', 'avatar_url');
  return s;
}
export function oneOf(v, list, { field, label = field, required = true }) {
  if ((v === undefined || v === null || v === '') && !required) return null;
  if (!list.includes(v)) throw bad(`Please choose a valid ${label.toLowerCase()}.`, field);
  return v;
}

/* Embark ID (stored in users.raider_tag). Format per Embark support (id.embark.games FAQ 241): DisplayName#1234.
 * Display name: 2–16 characters, starts with a letter or number; letters, numbers and - _ . (never two symbols in a row).
 * Discriminator: Embark's example shows 4 digits but does not state the length, so 3–6 digits are accepted.
 * Spaces around '#' are removed. Empty = not set. */
const EMBARK_RE = /^[\p{L}\p{N}](?:[\p{L}\p{N}]|[-_.](?=[\p{L}\p{N}])){1,15}#\d{3,6}$/u;
export function embarkId(value) {
  const s = text(value, { field: 'raider_tag', label: 'Embark ID', max: 30 });
  if (!s) return null;
  const n = s.replace(/\s*#\s*/, '#');
  if (!EMBARK_RE.test(n)) throw bad('Enter your Embark ID as it appears in ARC Raiders, for example RaiderName#1234 (Social menu → your profile → Show Discriminator).', 'raider_tag');
  return n;
}
