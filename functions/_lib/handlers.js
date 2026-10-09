/* Route handlers. Each receives ctx = { request, env, db, params, session, url } and returns a Response.
 * Authorization rule everywhere: the acting user comes from ctx.session (the cookie), never from the request body. */
import { json, readJson, bad, notFound, forbidden, conflict, tooMany, clientIp, nowIso, ApiError } from './http.js';
import { hashPassword, verifyPassword, needsRehash, burnPasswordCheck, randomId, ipKey, rateHit, rateReset, rateUndo, rateLimit } from './security.js';
import { startSession, endSession, requireUser } from './session.js';
import { reference } from './reference.js';
import * as v from './validate.js';
import * as repo from './repo.js';

export const API_VERSION = '6.2';

/* ---------------------------------------------------------------- health */
export async function health(ctx) {
  await ctx.db.prepare('SELECT 1 AS ok').first();
  const t = await ctx.db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('users','sessions','trade_posts','trade_offers','rate_limits','trade_handoffs','trade_reports')").all();
  const tables = (t.results || []).map(r => r.name);
  const migrated = tables.length === 7;   // v6.2 needs migration 0002 (trade_handoffs, trade_reports)
  return json({ ok: migrated, api: API_VERSION, database: 'connected', migrated, ...(migrated ? {} : { hint: 'Run the D1 migrations (see docs/CLOUDFLARE-BACKEND-SETUP.md).' }) }, migrated ? 200 : 503);
}

/* ---------------------------------------------------------------- auth */
const LIMITS = {
  registerTry: { n: 60, win: 3600 },      // registration attempts per IP per hour (caps password-hashing work)
  registerOk: { n: 10, win: 3600 },       // accounts actually created per IP per hour
  loginIp: { n: 30, win: 900 },           // failed logins per IP per 15 min (all accounts)
  loginAcctIp: { n: 8, win: 900 },        // failed logins per account from one IP per 15 min
  loginAcct: { n: 50, win: 900 },         // failed logins per account from all IPs per 15 min (distributed guessing)
};

export async function register(ctx) {
  const db = ctx.db, body = await readJson(ctx.request);
  const ip = await ipKey(clientIp(ctx.request));
  await rateLimit(db, 'reg-try:' + ip, LIMITS.registerTry.n, LIMITS.registerTry.win, tooMany);
  const ref = await reference(ctx.env, ctx.request);
  const username = v.username(body.username);
  const email = v.email(body.email);
  const display_name = v.displayName(body.display_name);
  const password = v.password(body.password, { username, email });
  if (body.confirm_password !== body.password) throw bad('Passwords do not match.', 'confirm_password');
  const avatar_url = v.avatar(body.avatar_url) || 'raiders/raider-solo-scout.webp';
  const region = v.oneOf(body.region || null, ref.regions, { field: 'region', label: 'Region', required: false });
  const platform = v.oneOf(body.platform || null, ref.platforms, { field: 'platform', label: 'Platform', required: false });
  const raider_tag = v.embarkId(body.raider_tag);

  if (await repo.usernameTaken(db, username)) throw conflict('That username is already taken.', 'username');
  if (await repo.emailTaken(db, email)) throw conflict('An account with that email already exists. Try logging in.', 'email');

  // reserve one "account created" slot atomically before creating, give it back if creation fails
  await rateLimit(db, 'reg-ok:' + ip, LIMITS.registerOk.n, LIMITS.registerOk.win, tooMany);
  const password_hash = await hashPassword(password);
  let user;
  try {
    user = await repo.createUser(db, { id: randomId('usr'), username, display_name, email, password_hash, avatar_url, region, platform, raider_tag });
  } catch (e) {   // two simultaneous registrations: the UNIQUE indexes are the final authority
    await rateUndo(db, 'reg-ok:' + ip);
    const m = String(e.message || e);
    if (/UNIQUE/i.test(m)) throw conflict(/email/i.test(m) ? 'An account with that email already exists. Try logging in.' : 'That username is already taken.', /email/i.test(m) ? 'email' : 'username');
    throw e;
  }
  const cookie = await startSession(db, ctx.request, user.id);
  return json({ user: repo.selfUser(user) }, 201, { 'Set-Cookie': cookie });
}

export async function login(ctx) {
  const db = ctx.db, body = await readJson(ctx.request);
  const loginName = String(body.login ?? body.username ?? body.email ?? '').trim().toLowerCase().slice(0, 254);
  const password = typeof body.password === 'string' ? body.password.slice(0, 128) : '';
  if (!loginName || !password) throw bad('Enter your username or email and your password.');
  const user = await repo.userByLogin(db, loginName);
  // Buckets are keyed on the resolved account (so username and email share one counter) or, for unknown names,
  // on a hash of the name. The per-account limit is per IP, so someone else guessing cannot lock you out from
  // your own connection; a higher all-IPs limit still stops distributed guessing against one account.
  const ip = await ipKey(clientIp(ctx.request));
  const acct = user ? user.id : 'name:' + (await ipKey('acct:' + loginName));
  const buckets = [['login-ip:' + ip, LIMITS.loginIp], ['login-acct-ip:' + acct + ':' + ip, LIMITS.loginAcctIp], ['login-acct:' + acct, LIMITS.loginAcct]];
  // Reserve the attempt in every bucket BEFORE checking the password, so parallel requests can't exceed the limits.
  const counts = [];
  for (const [b, l] of buckets) counts.push(await rateHit(db, b, l.win));
  const over = counts.findIndex((c, i) => c.count > buckets[i][1].n);
  if (over > -1) throw tooMany(buckets[over][1].win - (Math.floor(Date.now() / 1000) - counts[over].window_start));
  let ok = false;
  if (user) ok = await verifyPassword(password, user.password_hash); else await burnPasswordCheck(password);
  if (!ok || user.status !== 'active') throw new ApiError(401, 'invalid_credentials', 'Incorrect username/email or password.');
  // success: the attempt does not count against anyone
  await rateUndo(db, buckets[0][0]); await rateReset(db, buckets[1][0]); await rateUndo(db, buckets[2][0]);
  if (needsRehash(user.password_hash)) await repo.updatePasswordHash(db, user.id, await hashPassword(password));
  if (Math.random() < 0.05) ctx.waitUntil?.(repo.purgeExpired(db));
  const cookie = await startSession(db, ctx.request, user.id);
  return json({ user: repo.selfUser(user) }, 200, { 'Set-Cookie': cookie });
}

export async function logout(ctx) {
  const cookie = await endSession(ctx.db, ctx.request);
  return json({ ok: true }, 200, { 'Set-Cookie': cookie });
}

export async function session(ctx) {
  if (!ctx.session) return json({ user: null });
  const u = ctx.session.user;
  return json({ user: repo.selfUser(u), trades: await repo.userTradeCounts(ctx.db, u.id) });
}

export async function updateMe(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request), ref = await reference(ctx.env, ctx.request);
  const patch = {
    display_name: body.display_name !== undefined ? v.displayName(body.display_name) : me.display_name,
    avatar_url: body.avatar_url !== undefined ? (v.avatar(body.avatar_url) || me.avatar_url) : me.avatar_url,
    region: body.region !== undefined ? v.oneOf(body.region || null, ref.regions, { field: 'region', label: 'Region', required: false }) : me.region,
    platform: body.platform !== undefined ? v.oneOf(body.platform || null, ref.platforms, { field: 'platform', label: 'Platform', required: false }) : me.platform,
    raider_tag: body.raider_tag !== undefined && String(body.raider_tag ?? '').trim() !== (me.raider_tag || '') ? v.embarkId(body.raider_tag) : me.raider_tag,
  };
  const u = await repo.updateUserProfile(ctx.db, me.id, patch);
  return json({ user: repo.selfUser(u) });
}

export async function myOffers(ctx) {
  const me = await requireUser(ctx);
  const [sent, received] = await Promise.all([repo.offersSentBy(ctx.db, me.id), repo.offersReceivedBy(ctx.db, me.id)]);
  return json({ sent: sent.map(repo.offerOut), received: received.map(repo.offerOut) });
}

/* ---------------------------------------------------------------- users (public) */
export async function publicProfile(ctx) {
  const u = await repo.userByUsername(ctx.db, String(ctx.params.username || '').toLowerCase());
  if (!u) throw notFound('No Raider with that username.');
  return json({ user: repo.publicUser(u), trades: await repo.userTradeCounts(ctx.db, u.id) });
}

/* ---------------------------------------------------------------- trades */
const STATUSES = ['OPEN', 'CLOSED', 'COMPLETED'];

/* Resolve an item reference: a known Loot Intel id wins and supplies the canonical name; otherwise free text. */
function itemRef(ref, id, name, { field, label, required }) {
  if (id) {
    if (typeof id !== 'string' || !ref.items.has(id)) throw bad(`${label}: unknown Loot Intel item.`, field);
    return { item_id: id, item_name: ref.items.get(id) };
  }
  const n = v.text(name, { field, label, max: 80, min: 2, required });
  return { item_id: null, item_name: n };
}

function tradeFields(body, ref, base = {}) {
  const has = k => body[k] !== undefined;
  const want = (has('wanted_item_id') || has('wanted_item_name'))
    ? itemRef(ref, body.wanted_item_id, body.wanted_item_name, { field: 'wanted_item_name', label: 'Looking for', required: true })
    : { item_id: base.wanted_item_id, item_name: base.wanted_item_name };
  if (!want.item_name) throw bad('Tell Raiders what you are looking for.', 'wanted_item_name');
  const offer = (has('offered_item_id') || has('offered_item_name'))
    ? itemRef(ref, body.offered_item_id, body.offered_item_name, { field: 'offered_item_name', label: 'Offer', required: false })
    : { item_id: base.offered_item_id ?? null, item_name: base.offered_item_name ?? null };
  const offered_quantity = offer.item_name ? v.int(has('offered_quantity') ? body.offered_quantity : base.offered_quantity, { field: 'offered_quantity', label: 'Offer quantity', min: 1, max: 99, fallback: 1 }) : null;
  return {
    wanted_item_id: want.item_id, wanted_item_name: want.item_name,
    wanted_quantity: v.int(has('wanted_quantity') ? body.wanted_quantity : base.wanted_quantity, { field: 'wanted_quantity', label: 'Quantity', min: 1, max: 99, fallback: 1 }),
    offered_item_id: offer.item_id, offered_item_name: offer.item_name, offered_quantity,
    open_to_offers: has('open_to_offers') ? !!body.open_to_offers || !offer.item_name : (base.open_to_offers ?? true) || !offer.item_name,
    region: has('region') ? v.oneOf(body.region, ref.regions, { field: 'region', label: 'Region' }) : v.oneOf(base.region, ref.regions, { field: 'region', label: 'Region' }),
    platform: has('platform') ? v.oneOf(body.platform, ref.platforms, { field: 'platform', label: 'Platform' }) : v.oneOf(base.platform, ref.platforms, { field: 'platform', label: 'Platform' }),
    desired_time: has('desired_time') ? v.text(body.desired_time, { field: 'desired_time', label: 'Desired time', max: 80 }) : base.desired_time ?? null,
    notes: has('notes') ? v.text(body.notes, { field: 'notes', label: 'Notes', max: 500, multiline: true }) : base.notes ?? null,
  };
}

export async function listTrades(ctx) {
  const q = ctx.url.searchParams;
  const status = (q.get('status') || 'ALL').toUpperCase();
  if (status !== 'ALL' && !STATUSES.includes(status)) throw bad('Unknown status filter.', 'status');
  let userId = null;
  if (q.get('user')) { const u = await repo.userByUsername(ctx.db, q.get('user').toLowerCase()); if (!u) return json({ trades: [] }); userId = u.id; }
  const limit = Math.min(500, Math.max(1, Math.floor(Number(q.get('limit'))) || 300));
  const rows = await repo.listTrades(ctx.db, { status: status === 'ALL' ? null : status, userId, limit });
  const viewer = ctx.session?.user.id;
  return json({ trades: rows.map(t => repo.tradeOut(t, viewer)) });
}

export async function getTrade(ctx) {
  const t = await repo.tradeById(ctx.db, ctx.params.id);
  if (!t) throw notFound('That trade post no longer exists.');
  return json({ trade: repo.tradeOut(t, ctx.session?.user.id) });
}

export async function createTrade(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request), ref = await reference(ctx.env, ctx.request);
  await rateLimit(ctx.db, 'post:' + me.id, 30, 3600, tooMany);
  const f = tradeFields(body, ref, { region: me.region || ref.regions[0], platform: me.platform || ref.platforms[0] });
  const t = await repo.createTrade(ctx.db, { id: randomId('trd'), user_id: me.id, ...f });
  return json({ trade: repo.tradeOut(t, me.id) }, 201);
}

async function ownedTrade(ctx, me) {
  const t = await repo.tradeById(ctx.db, ctx.params.id);
  if (!t) throw notFound('That trade post no longer exists.');
  if (t.user_id !== me.id) throw forbidden('Only the Raider who posted this trade can change it.');
  return t;
}

export async function updateTrade(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request);
  const t = await ownedTrade(ctx, me);
  const editing = Object.keys(body).some(k => k !== 'status');
  if (t.status === 'COMPLETED') throw conflict('Completed trades can no longer be changed.');
  if (await repo.activeHandoffForTrade(ctx.db, t.id)) throw conflict('This trade has an accepted offer awaiting the in-game exchange. Both Raiders confirm it in the trade handoff, or cancel the handoff first.');
  const f = editing ? tradeFields(body, await reference(ctx.env, ctx.request), t) : {
    wanted_item_id: t.wanted_item_id, wanted_item_name: t.wanted_item_name, wanted_quantity: t.wanted_quantity, offered_item_id: t.offered_item_id,
    offered_item_name: t.offered_item_name, offered_quantity: t.offered_quantity, open_to_offers: !!t.open_to_offers, region: t.region, platform: t.platform,
    desired_time: t.desired_time, notes: t.notes };
  let status = t.status, closed_at = t.closed_at;
  if (body.status !== undefined) {
    status = String(body.status).toUpperCase();
    if (!STATUSES.includes(status)) throw bad('Status must be OPEN, CLOSED or COMPLETED.', 'status');
    if (status === 'COMPLETED' && t.status !== 'COMPLETED') throw conflict('Trades are marked completed when both Raiders confirm the exchange in the trade handoff. If the trade happened elsewhere, close the post instead.', 'status');
    if (status === 'OPEN') closed_at = null; else if (status !== t.status) closed_at = nowIso();
  }
  const changed = await repo.updateTrade(ctx.db, t.id, me.id, { ...f, status, closed_at });
  if (!changed) throw forbidden();
  if (status === 'COMPLETED') await repo.declinePendingOffers(ctx.db, t.id);
  return json({ trade: repo.tradeOut(await repo.tradeById(ctx.db, t.id), me.id) });
}

export async function deleteTrade(ctx) {
  const me = await requireUser(ctx);
  const t = await ownedTrade(ctx, me);
  if (await repo.activeHandoffForTrade(ctx.db, t.id)) throw conflict('This trade has an accepted offer awaiting the in-game exchange. Cancel the handoff before deleting the trade.');
  if (await repo.anyHandoffForTrade(ctx.db, t.id)) throw conflict('This trade has a trade handoff on record, so it can be closed but not deleted.');
  const n = await repo.deleteTrade(ctx.db, t.id, me.id);
  if (!n) throw forbidden();
  return json({ ok: true, deleted: t.id });
}

/* ---------------------------------------------------------------- offers */
export async function listOffers(ctx) {
  const me = await requireUser(ctx);
  const t = await repo.tradeOwner(ctx.db, ctx.params.id);
  if (!t) throw notFound('That trade post no longer exists.');
  const rows = t.user_id === me.id ? await repo.offersForTrade(ctx.db, t.id) : await repo.offersFromUserForTrade(ctx.db, t.id, me.id);
  return json({ offers: rows.map(repo.offerOut), is_owner: t.user_id === me.id });
}

export async function createOffer(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request), ref = await reference(ctx.env, ctx.request);
  const t = await repo.tradeOwner(ctx.db, ctx.params.id);
  if (!t) throw notFound('That trade post no longer exists.');
  if (t.user_id === me.id) throw forbidden('You cannot make an offer on your own trade.');
  if (t.status !== 'OPEN') throw conflict('This trade is no longer open.');
  await rateLimit(ctx.db, 'offer:' + me.id, 30, 3600, tooMany);
  const message = v.text(body.message, { field: 'message', label: 'Message', max: 500, min: 2, required: true, multiline: true });
  const item = (body.offered_item_id || body.offered_item_name) ? itemRef(ref, body.offered_item_id, body.offered_item_name, { field: 'offered_item_name', label: 'Offered item', required: false }) : { item_id: null, item_name: null };
  if (await repo.pendingOfferExists(ctx.db, t.id, me.id)) throw conflict('You already have a pending offer on this trade. Withdraw it first to send a new one.');
  let o;
  try { o = await repo.createOffer(ctx.db, { id: randomId('ofr'), trade_post_id: t.id, from_user_id: me.id, message, offered_item_id: item.item_id, offered_item_name: item.item_name }); }
  catch (e) { if (/UNIQUE/i.test(String(e.message))) throw conflict('You already have a pending offer on this trade.'); throw e; }
  return json({ offer: repo.offerOut(o) }, 201);
}

export async function updateOffer(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request);
  const o = await repo.offerById(ctx.db, ctx.params.id);
  if (!o) throw notFound('That offer no longer exists.');
  const action = String(body.action || '').toLowerCase();
  const isOwner = o.trade_owner_id === me.id, isSender = o.from_user_id === me.id;
  let status;
  if (action === 'accept' || action === 'decline') {
    if (!isOwner) throw forbidden('Only the trade owner can accept or decline offers.');
    if (action === 'accept' && o.trade_status !== 'OPEN') throw conflict('Reopen the trade before accepting an offer.');
    status = action === 'accept' ? 'ACCEPTED' : 'DECLINED';
  } else if (action === 'withdraw') {
    if (!isSender) throw forbidden('Only the Raider who sent this offer can withdraw it.');
    status = 'WITHDRAWN';
  } else throw bad('Action must be accept, decline or withdraw.', 'action');
  if (o.status !== 'PENDING') throw conflict(`This offer is already ${o.status.toLowerCase()}.`);
  if (status === 'ACCEPTED') {
    if (await repo.activeHandoffForTrade(ctx.db, o.trade_post_id)) throw conflict('You already accepted an offer on this trade. Finish or cancel that trade handoff before accepting another.');
    let ok = false;
    try { ok = await repo.acceptOfferWithHandoff(ctx.db, o.id, me.id, randomId('hnd')); }
    catch (e) { if (/UNIQUE/i.test(String(e.message))) throw conflict('Another offer on this trade was just accepted.'); throw e; }
    if (!ok) throw conflict('This offer was already answered.');
    const h = await repo.handoffByOfferForParticipant(ctx.db, o.id, me.id);
    return json({ offer: repo.offerOut(await repo.offerById(ctx.db, o.id)), handoff: h ? { id: h.id, status: h.status } : null });
  }
  if (!(await repo.setOfferStatus(ctx.db, o.id, status))) throw conflict('This offer was already answered.');
  return json({ offer: repo.offerOut(await repo.offerById(ctx.db, o.id)) });
}

/* ---------------------------------------------------------------- trade handoffs (v6.2)
 * Participant-only. A non-participant gets 404 (the same as "does not exist") so handoff IDs reveal nothing.
 * The acting Raider always comes from the session cookie; the role (owner / offer sender) is derived in SQL. */
const HANDOFF_404 = 'That trade handoff was not found.';
const CANCEL_REASONS = ['no_show', 'could_not_connect', 'changed_mind', 'wrong_item', 'other'];
const REPORT_REASONS = ['no_show', 'did_not_deliver', 'scam_attempt', 'abusive', 'other'];

async function participantHandoff(ctx, me) {
  const h = await repo.handoffForParticipant(ctx.db, ctx.params.id, me.id);
  if (!h) throw notFound(HANDOFF_404);
  return h;
}

export async function listHandoffs(ctx) {
  const me = await requireUser(ctx);
  const [rows, legacy] = await Promise.all([repo.handoffsForUser(ctx.db, me.id), repo.acceptedOffersWithoutHandoff(ctx.db, me.id)]);
  /* Offers accepted before v6.2 are listed so they can be opened; no Embark ID is included until the handoff is opened. */
  const pending = legacy.map(o => ({ id: null, offer_id: o.id, status: 'NOT_OPENED', trade: { id: o.trade_post_id, status: o.trade_status, wanted: { item_id: o.trade_wanted_item_id, name: o.trade_wanted_name } },
    other: o.trade_owner_id === me.id ? { username: o.from_username, display_name: o.from_display_name } : { username: o.trade_owner_username, display_name: o.trade_owner_display_name },
    your_role: o.trade_owner_id === me.id ? 'TRADE_OWNER' : 'OFFER_SENDER', updated_at: o.updated_at }));
  const list = rows.map(h => { const x = repo.handoffOut(h, me.id); delete x.you.embark_id; delete x.other.embark_id; return x; });   // IDs only on the detail view
  return json({ handoffs: list, not_opened: pending, unseen: list.filter(x => x.unseen && x.status === 'AWAITING_EXCHANGE').map(x => x.id) });
}

export async function getHandoff(ctx) {
  const me = await requireUser(ctx);
  return json({ handoff: repo.handoffOut(await participantHandoff(ctx, me), me.id) });
}

/* Open (or create, for an offer accepted before v6.2) the handoff for an accepted offer. Only the two people on the
   offer can do this. Nothing about the trade or offer is changed; COMPLETED/CLOSED trades get a read-only handoff. */
export async function openHandoffForOffer(ctx) {
  const me = await requireUser(ctx);
  const o = await repo.offerById(ctx.db, ctx.params.id);
  if (!o || (o.from_user_id !== me.id && o.trade_owner_id !== me.id)) throw notFound(HANDOFF_404);
  if (o.status !== 'ACCEPTED') throw conflict('A trade handoff opens once the offer has been accepted.');
  let h = await repo.handoffByOfferForParticipant(ctx.db, o.id, me.id);
  if (!h) {
    const isOwner = o.trade_owner_id === me.id;
    const live = o.trade_status === 'OPEN' && !(await repo.activeHandoffForTrade(ctx.db, o.trade_post_id));
    /* Only the trade owner can turn an old accepted offer on a still-open trade into a live exchange
       (otherwise the sender could lock the owner's post). */
    if (live && !isOwner) throw conflict(`${o.trade_owner_display_name} needs to open this trade's details first (My Profile → Accepted trades). It will appear here once they do.`);
    await rateLimit(ctx.db, 'handoff-open:' + me.id, 60, 3600, tooMany);
    const create = status => repo.createHandoffForAcceptedOffer(ctx.db, { id: randomId('hnd'), offerId: o.id, status });
    try { await create(live ? 'AWAITING_EXCHANGE' : 'HISTORICAL'); }
    catch (e) {
      if (!/UNIQUE/i.test(String(e.message))) throw e;
      // either the same offer was opened concurrently (row now exists) or another live handoff appeared on the trade
      if (!(await repo.handoffByOfferForParticipant(ctx.db, o.id, me.id))) {
        try { await create('HISTORICAL'); } catch (e2) { if (!/UNIQUE/i.test(String(e2.message))) throw e2; }
      }
    }
    h = await repo.handoffByOfferForParticipant(ctx.db, o.id, me.id);
    if (!h) throw notFound(HANDOFF_404);
  }
  /* Opening a live handoff counts as seeing it (clears the banner). For a HISTORICAL handoff "seen" means
     "I share my Embark ID", so it is only recorded through the explicit Share button (POST /handoffs/:id/seen). */
  if (h.status !== 'HISTORICAL') { await repo.markHandoffSeen(ctx.db, h.id, me.id); h = await repo.handoffByOfferForParticipant(ctx.db, o.id, me.id); }
  return json({ handoff: repo.handoffOut(h, me.id) });
}

export async function seenHandoff(ctx) {
  const me = await requireUser(ctx);
  const h = await participantHandoff(ctx, me);
  if (h.status === 'HISTORICAL' && !h.share_ids) throw conflict('Embark IDs are not shared for this earlier offer.');
  await repo.markHandoffSeen(ctx.db, ctx.params.id, me.id);
  return json({ ok: true });
}

export async function confirmHandoff(ctx) {
  const me = await requireUser(ctx);
  const h = await participantHandoff(ctx, me);
  if (h.status !== 'AWAITING_EXCHANGE') throw conflict(h.status === 'COMPLETED' ? 'This trade is already completed.' : 'This trade handoff can no longer be confirmed.');
  await rateLimit(ctx.db, 'handoff-act:' + me.id, 60, 3600, tooMany);
  const r = await repo.confirmHandoff(ctx.db, h.id, me.id);
  const fresh = await repo.handoffForParticipant(ctx.db, h.id, me.id);
  return json({ handoff: repo.handoffOut(fresh, me.id), completed: r.completed });
}

export async function cancelHandoff(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request);
  const h = await participantHandoff(ctx, me);
  const reason = String(body.reason || '').toLowerCase();
  if (!CANCEL_REASONS.includes(reason)) throw bad('Choose a reason for cancelling.', 'reason');
  if (h.status !== 'AWAITING_EXCHANGE') throw conflict('Only a trade that is awaiting the exchange can be cancelled.');
  await rateLimit(ctx.db, 'handoff-act:' + me.id, 60, 3600, tooMany);
  if (!(await repo.cancelHandoff(ctx.db, h.id, me.id, reason))) throw conflict('This trade handoff can no longer be cancelled.');
  return json({ handoff: repo.handoffOut(await repo.handoffForParticipant(ctx.db, h.id, me.id), me.id) });
}

export async function reportHandoff(ctx) {
  const me = await requireUser(ctx), body = await readJson(ctx.request);
  const h = await participantHandoff(ctx, me);
  const reason = String(body.reason || '').toLowerCase();
  if (!REPORT_REASONS.includes(reason)) throw bad('Choose what went wrong.', 'reason');
  const details = v.text(body.details, { field: 'details', label: 'Details', max: 500, multiline: true });
  await rateLimit(ctx.db, 'report:' + me.id, 10, 86400, tooMany);
  if (await repo.reportExists(ctx.db, h.id, me.id)) throw conflict('You have already reported this trade. Our team will review it.');
  try { await repo.createReport(ctx.db, { id: randomId('rpt'), handoff_id: h.id, reporter_id: me.id, reported_id: h.owner_id === me.id ? h.counterparty_id : h.owner_id, reason, details }); }
  catch (e) { if (/UNIQUE/i.test(String(e.message))) throw conflict('You have already reported this trade.'); throw e; }
  return json({ ok: true }, 201);
}

/* ---------------------------------------------------------------- stats */
export async function stats(ctx) {
  return json({ stats: await repo.stats(ctx.db) }, 200, { 'Cache-Control': 'public, max-age=30' });
}
