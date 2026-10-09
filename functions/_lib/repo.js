/* Data-access layer: every SQL statement in the application lives in this file.
 * All values are bound parameters (?1, ?2 …); no user input is ever concatenated into SQL.
 * Handlers call these functions and never touch env.DB directly. */
import { nowIso } from './http.js';

/* ---------------------------------------------------------------- shapes returned to the browser */
export const publicUser = u => u && ({
  id: u.id, username: u.username, display_name: u.display_name, avatar_url: u.avatar_url,
  region: u.region, platform: u.platform, joined_at: u.created_at,
});
/* The signed-in Raider's own record. Email and Raider tag are included ONLY here. */
export const selfUser = u => u && ({ ...publicUser(u), email: u.email, raider_tag: u.raider_tag, role: u.role });

const TRADE_SELECT = `
  SELECT t.*, u.username AS owner_username, u.display_name AS owner_display_name, u.avatar_url AS owner_avatar_url,
         (SELECT COUNT(*) FROM trade_offers o WHERE o.trade_post_id = t.id AND o.status = 'PENDING') AS pending_offers,
         EXISTS (SELECT 1 FROM trade_handoffs h WHERE h.trade_post_id = t.id AND h.status = 'AWAITING_EXCHANGE') AS awaiting_exchange
    FROM trade_posts t JOIN users u ON u.id = t.user_id`;

export const tradeOut = (t, viewerId) => t && ({
  id: t.id, status: t.status,
  wanted: { item_id: t.wanted_item_id, name: t.wanted_item_name, quantity: t.wanted_quantity },
  offered: t.offered_item_name ? { item_id: t.offered_item_id, name: t.offered_item_name, quantity: t.offered_quantity || 1 } : null,
  open_to_offers: !!t.open_to_offers, region: t.region, platform: t.platform, desired_time: t.desired_time, notes: t.notes,
  created_at: t.created_at, updated_at: t.updated_at, closed_at: t.closed_at,
  owner: { id: t.user_id, username: t.owner_username, display_name: t.owner_display_name, avatar_url: t.owner_avatar_url },
  pending_offers: t.pending_offers || 0, is_mine: !!viewerId && viewerId === t.user_id,
  /* v6.2: public "Awaiting exchange" label only. Who the other Raider is and any Embark ID are never part of a trade. */
  display_status: t.awaiting_exchange ? 'AWAITING_EXCHANGE' : t.status,
});

export const offerOut = o => o && ({
  id: o.id, trade_id: o.trade_post_id, status: o.status, message: o.message,
  offered: o.offered_item_name ? { item_id: o.offered_item_id, name: o.offered_item_name } : null,
  from: { id: o.from_user_id, username: o.from_username, display_name: o.from_display_name, avatar_url: o.from_avatar_url },
  created_at: o.created_at, updated_at: o.updated_at,
  ...(o.trade_wanted_name ? { trade: { id: o.trade_post_id, wanted_name: o.trade_wanted_name, wanted_item_id: o.trade_wanted_item_id, status: o.trade_status, owner_username: o.trade_owner_username, owner_display_name: o.trade_owner_display_name } } : {}),
});

/* ---------------------------------------------------------------- users */
export const userById = (db, id) => db.prepare("SELECT * FROM users WHERE id = ?1 AND status = 'active'").bind(id).first();
export const userByUsername = (db, username) => db.prepare("SELECT * FROM users WHERE username = ?1 AND status = 'active'").bind(username).first();
export const userByLogin = (db, login) => db.prepare('SELECT * FROM users WHERE username = ?1 OR email = ?1').bind(login).first();
export const usernameTaken = async (db, username) => !!(await db.prepare('SELECT 1 FROM users WHERE username = ?1').bind(username).first());
export const emailTaken = async (db, email) => !!(await db.prepare('SELECT 1 FROM users WHERE email = ?1').bind(email).first());

export async function createUser(db, u) {
  const now = nowIso();
  await db.prepare(`INSERT INTO users (id, username, display_name, email, password_hash, avatar_url, region, platform, raider_tag, created_at, updated_at)
                    VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?10)`)
    .bind(u.id, u.username, u.display_name, u.email, u.password_hash, u.avatar_url, u.region, u.platform, u.raider_tag, now).run();
  return userById(db, u.id);
}
export async function updateUserProfile(db, id, p) {
  await db.prepare(`UPDATE users SET display_name = ?2, avatar_url = ?3, region = ?4, platform = ?5, raider_tag = ?6, updated_at = ?7 WHERE id = ?1`)
    .bind(id, p.display_name, p.avatar_url, p.region, p.platform, p.raider_tag, nowIso()).run();
  return userById(db, id);
}
export const updatePasswordHash = (db, id, hash) => db.prepare('UPDATE users SET password_hash = ?2, updated_at = ?3 WHERE id = ?1').bind(id, hash, nowIso()).run();

export async function userTradeCounts(db, id) {
  const r = await db.prepare(`SELECT
      SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS active,
      SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
      SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) AS closed
    FROM trade_posts WHERE user_id = ?1`).bind(id).first();
  return { active: r?.active || 0, completed: r?.completed || 0, closed: r?.closed || 0 };
}

/* ---------------------------------------------------------------- sessions */
export async function createSession(db, s) {
  const now = nowIso();
  await db.prepare(`INSERT INTO sessions (id, user_id, token_hash, created_at, expires_at, last_used_at, user_agent) VALUES (?1, ?2, ?3, ?4, ?5, ?4, ?6)`)
    .bind(s.id, s.user_id, s.token_hash, now, s.expires_at, s.user_agent).run();
}
export const sessionByTokenHash = (db, hash) => db.prepare(`SELECT s.id AS session_id, s.expires_at, s.last_used_at, u.*
    FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?1`).bind(hash).first();
export const touchSession = (db, id) => db.prepare('UPDATE sessions SET last_used_at = ?2 WHERE id = ?1').bind(id, nowIso()).run();
export const deleteSession = (db, id) => db.prepare('DELETE FROM sessions WHERE id = ?1').bind(id).run();
export const deleteSessionByTokenHash = (db, hash) => db.prepare('DELETE FROM sessions WHERE token_hash = ?1').bind(hash).run();
export const purgeExpired = (db) => db.batch([
  db.prepare('DELETE FROM sessions WHERE expires_at < ?1').bind(nowIso()),
  db.prepare('DELETE FROM rate_limits WHERE window_start < ?1').bind(Math.floor(Date.now() / 1000) - 86400),
]);

/* ---------------------------------------------------------------- trades */
export async function listTrades(db, { status, userId, limit }) {
  const where = [], binds = [];
  if (status) { binds.push(status); where.push(`t.status = ?${binds.length}`); }
  if (userId) { binds.push(userId); where.push(`t.user_id = ?${binds.length}`); }
  binds.push(limit);
  const sql = `${TRADE_SELECT} ${where.length ? 'WHERE ' + where.join(' AND ') : ''} ORDER BY t.created_at DESC LIMIT ?${binds.length}`;
  return (await db.prepare(sql).bind(...binds).all()).results || [];
}
export const tradeById = (db, id) => db.prepare(`${TRADE_SELECT} WHERE t.id = ?1`).bind(id).first();
export const tradeOwner = (db, id) => db.prepare('SELECT id, user_id, status FROM trade_posts WHERE id = ?1').bind(id).first();

export async function createTrade(db, t) {
  const now = nowIso();
  await db.prepare(`INSERT INTO trade_posts (id, user_id, wanted_item_id, wanted_item_name, wanted_quantity, offered_item_id, offered_item_name, offered_quantity,
                      open_to_offers, region, platform, desired_time, notes, status, created_at, updated_at)
                    VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, 'OPEN', ?14, ?14)`)
    .bind(t.id, t.user_id, t.wanted_item_id, t.wanted_item_name, t.wanted_quantity, t.offered_item_id, t.offered_item_name, t.offered_quantity,
      t.open_to_offers ? 1 : 0, t.region, t.platform, t.desired_time, t.notes, now).run();
  return tradeById(db, t.id);
}
/* Ownership is part of the WHERE clause, so a non-owner's UPDATE/DELETE can never change a row
   even if the handler's own check were bypassed. */
export async function updateTrade(db, id, ownerId, t) {
  const r = await db.prepare(`UPDATE trade_posts SET wanted_item_id = ?3, wanted_item_name = ?4, wanted_quantity = ?5, offered_item_id = ?6,
        offered_item_name = ?7, offered_quantity = ?8, open_to_offers = ?9, region = ?10, platform = ?11, desired_time = ?12, notes = ?13,
        status = ?14, closed_at = ?15, updated_at = ?16
      WHERE id = ?1 AND user_id = ?2`)
    .bind(id, ownerId, t.wanted_item_id, t.wanted_item_name, t.wanted_quantity, t.offered_item_id, t.offered_item_name, t.offered_quantity,
      t.open_to_offers ? 1 : 0, t.region, t.platform, t.desired_time, t.notes, t.status, t.closed_at, nowIso()).run();
  return r.meta.changes;
}
export const declinePendingOffers = (db, tradeId) => db.prepare(`UPDATE trade_offers SET status = 'DECLINED', updated_at = ?2 WHERE trade_post_id = ?1 AND status = 'PENDING'`).bind(tradeId, nowIso()).run();
export async function deleteTrade(db, id, ownerId) {
  const r = await db.prepare('DELETE FROM trade_posts WHERE id = ?1 AND user_id = ?2').bind(id, ownerId).run();
  return r.meta.changes;
}

/* ---------------------------------------------------------------- offers */
const OFFER_SELECT = `
  SELECT o.*, fu.username AS from_username, fu.display_name AS from_display_name, fu.avatar_url AS from_avatar_url,
         t.wanted_item_name AS trade_wanted_name, t.wanted_item_id AS trade_wanted_item_id, t.status AS trade_status, t.user_id AS trade_owner_id,
         tu.username AS trade_owner_username, tu.display_name AS trade_owner_display_name
    FROM trade_offers o
    JOIN users fu ON fu.id = o.from_user_id
    JOIN trade_posts t ON t.id = o.trade_post_id
    JOIN users tu ON tu.id = t.user_id`;
export const offersForTrade = async (db, tradeId) => (await db.prepare(`${OFFER_SELECT} WHERE o.trade_post_id = ?1 ORDER BY o.created_at DESC`).bind(tradeId).all()).results || [];
export const offersFromUserForTrade = async (db, tradeId, userId) => (await db.prepare(`${OFFER_SELECT} WHERE o.trade_post_id = ?1 AND o.from_user_id = ?2 ORDER BY o.created_at DESC`).bind(tradeId, userId).all()).results || [];
export const offersSentBy = async (db, userId) => (await db.prepare(`${OFFER_SELECT} WHERE o.from_user_id = ?1 ORDER BY o.created_at DESC LIMIT 100`).bind(userId).all()).results || [];
export const offersReceivedBy = async (db, userId) => (await db.prepare(`${OFFER_SELECT} WHERE t.user_id = ?1 ORDER BY o.created_at DESC LIMIT 100`).bind(userId).all()).results || [];
export const offerById = (db, id) => db.prepare(`${OFFER_SELECT} WHERE o.id = ?1`).bind(id).first();
export const pendingOfferExists = async (db, tradeId, userId) => !!(await db.prepare(`SELECT 1 FROM trade_offers WHERE trade_post_id = ?1 AND from_user_id = ?2 AND status = 'PENDING'`).bind(tradeId, userId).first());

export async function createOffer(db, o) {
  const now = nowIso();
  await db.prepare(`INSERT INTO trade_offers (id, trade_post_id, from_user_id, message, offered_item_id, offered_item_name, status, created_at, updated_at)
                    VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'PENDING', ?7, ?7)`)
    .bind(o.id, o.trade_post_id, o.from_user_id, o.message, o.offered_item_id, o.offered_item_name, now).run();
  return offerById(db, o.id);
}
/* Status changes are conditional on the current status (PENDING) so two racing requests cannot both win. */
export async function setOfferStatus(db, id, status) {
  const r = await db.prepare(`UPDATE trade_offers SET status = ?2, updated_at = ?3 WHERE id = ?1 AND status = 'PENDING'`).bind(id, status, nowIso()).run();
  return r.meta.changes;
}

/* ---------------------------------------------------------------- community stats */
export async function stats(db) {
  const r = await db.prepare(`SELECT
      (SELECT COUNT(*) FROM users WHERE status = 'active') AS raiders,
      (SELECT COUNT(*) FROM trade_posts WHERE status = 'OPEN') AS open_trades,
      (SELECT COUNT(*) FROM trade_posts WHERE status = 'COMPLETED') AS completed_trades`).first();
  return { raiders: r.raiders, open_trades: r.open_trades, completed_trades: r.completed_trades };
}


/* ---------------------------------------------------------------- trade handoffs (v6.2)
 * Every query that returns a handoff includes "AND (h.owner_id = ?me OR h.counterparty_id = ?me)" in SQL, so a handoff
 * row can never be read for a non-participant even if a handler check were missing. Embark IDs (users.raider_tag) are
 * selected ONLY here and only ever leave the server through handoffOut(), for an authorised participant. */
const HANDOFF_SELECT = `
  SELECT h.*,
         t.wanted_item_id, t.wanted_item_name, t.wanted_quantity, t.offered_item_id AS trade_offered_item_id,
         t.offered_item_name AS trade_offered_item_name, t.offered_quantity AS trade_offered_quantity,
         t.status AS trade_status, t.platform AS trade_platform, t.region AS trade_region, t.created_at AS trade_created_at,
         o.offered_item_id AS offer_item_id, o.offered_item_name AS offer_item_name, o.message AS offer_message, o.status AS offer_status,
         ou.username AS owner_username, ou.display_name AS owner_display_name, ou.platform AS owner_platform, ou.region AS owner_region,
         ou.avatar_url AS owner_avatar_url, ou.raider_tag AS owner_embark_id,
         cu.username AS cp_username, cu.display_name AS cp_display_name, cu.platform AS cp_platform, cu.region AS cp_region,
         cu.avatar_url AS cp_avatar_url, cu.raider_tag AS cp_embark_id
    FROM trade_handoffs h
    JOIN trade_posts t ON t.id = h.trade_post_id
    JOIN trade_offers o ON o.id = h.offer_id
    JOIN users ou ON ou.id = h.owner_id
    JOIN users cu ON cu.id = h.counterparty_id`;
const PARTICIPANT = '(h.owner_id = ?1 OR h.counterparty_id = ?1)';

export const handoffForParticipant = (db, id, me) => db.prepare(`${HANDOFF_SELECT} WHERE h.id = ?2 AND ${PARTICIPANT}`).bind(me, id).first();
export const handoffByOfferForParticipant = (db, offerId, me) => db.prepare(`${HANDOFF_SELECT} WHERE h.offer_id = ?2 AND ${PARTICIPANT}`).bind(me, offerId).first();
export const handoffsForUser = async (db, me) => (await db.prepare(`${HANDOFF_SELECT} WHERE ${PARTICIPANT} ORDER BY h.updated_at DESC LIMIT 100`).bind(me).all()).results || [];
export const anyHandoffForTrade = (db, tradeId) => db.prepare('SELECT id FROM trade_handoffs WHERE trade_post_id = ?1 LIMIT 1').bind(tradeId).first();
export const activeHandoffForTrade = (db, tradeId) => db.prepare(`SELECT id FROM trade_handoffs WHERE trade_post_id = ?1 AND status = 'AWAITING_EXCHANGE'`).bind(tradeId).first();

/* Accepted offers I'm part of that have no handoff row yet (accepted before v6.2). Read-only; the row is created on demand. */
export const acceptedOffersWithoutHandoff = async (db, me) => (await db.prepare(`${OFFER_SELECT}
    WHERE o.status = 'ACCEPTED' AND (o.from_user_id = ?1 OR t.user_id = ?1)
      AND NOT EXISTS (SELECT 1 FROM trade_handoffs h WHERE h.offer_id = o.id)
    ORDER BY o.updated_at DESC LIMIT 100`).bind(me).all()).results || [];

/* Accept an offer and open its handoff atomically (D1 batch = one transaction). The INSERT only happens if the offer
   really is ACCEPTED now; the partial unique index makes a second concurrent acceptance on the same trade fail, which
   rolls the whole batch back (including the offer status). */
export async function acceptOfferWithHandoff(db, offerId, ownerId, handoffId) {
  const now = nowIso();
  const res = await db.batch([
    db.prepare(`UPDATE trade_offers SET status = 'ACCEPTED', updated_at = ?2 WHERE id = ?1 AND status = 'PENDING' AND from_user_id <> ?3
                  AND trade_post_id IN (SELECT id FROM trade_posts WHERE user_id = ?3 AND status = 'OPEN')`).bind(offerId, now, ownerId),
    db.prepare(`INSERT INTO trade_handoffs (id, trade_post_id, offer_id, owner_id, counterparty_id, status, owner_seen_at, created_at, updated_at)
                SELECT ?1, o.trade_post_id, o.id, t.user_id, o.from_user_id, 'AWAITING_EXCHANGE', ?3, ?3, ?3
                  FROM trade_offers o JOIN trade_posts t ON t.id = o.trade_post_id
                 WHERE o.id = ?2 AND o.status = 'ACCEPTED' AND t.user_id = ?4 AND o.from_user_id <> t.user_id`).bind(handoffId, offerId, now, ownerId),
  ]);
  return res[0].meta.changes === 1 && res[1].meta.changes === 1;
}

/* Create the handoff for an offer that was accepted before v6.2. Never changes the trade or the offer.
   status: 'AWAITING_EXCHANGE' (trade still OPEN, no other live handoff) or 'HISTORICAL' (read-only). */
/* share_ids (HISTORICAL only) is decided once, here: IDs may be shared only if the trade was ALREADY COMPLETED when the
   handoff was created and this is the trade's ONLY accepted offer (an unambiguous, reliable relationship). */
export async function createHandoffForAcceptedOffer(db, { id, offerId, status }) {
  const now = nowIso();
  const r = await db.prepare(`INSERT INTO trade_handoffs (id, trade_post_id, offer_id, owner_id, counterparty_id, status, created_at, updated_at, share_ids)
      SELECT ?1, o.trade_post_id, o.id, t.user_id, o.from_user_id, ?3, ?4, ?4,
             CASE WHEN ?3 <> 'HISTORICAL' THEN 1
                  WHEN t.status = 'COMPLETED' AND (SELECT COUNT(*) FROM trade_offers x WHERE x.trade_post_id = t.id AND x.status = 'ACCEPTED') = 1 THEN 1
                  ELSE 0 END
        FROM trade_offers o JOIN trade_posts t ON t.id = o.trade_post_id
       WHERE o.id = ?2 AND o.status = 'ACCEPTED' AND t.user_id <> o.from_user_id`).bind(id, offerId, status, now).run();
  return r.meta.changes;
}

export async function markHandoffSeen(db, id, me) {
  const now = nowIso();
  await db.batch([
    db.prepare(`UPDATE trade_handoffs SET owner_seen_at = ?3 WHERE id = ?1 AND owner_id = ?2 AND owner_seen_at IS NULL`).bind(id, me, now),
    db.prepare(`UPDATE trade_handoffs SET counterparty_seen_at = ?3 WHERE id = ?1 AND counterparty_id = ?2 AND counterparty_seen_at IS NULL`).bind(id, me, now),
  ]);
}

/* Record MY confirmation only (the column is chosen by role in SQL, never by the client). When both confirmations exist,
   the same batch completes the handoff, marks the trade COMPLETED and declines the remaining pending offers.
   All statements are conditional, so repeating the request or two racing confirmations cannot double-complete. */
export async function confirmHandoff(db, id, me) {
  const now = nowIso();
  const both = `owner_confirmed_at IS NOT NULL AND counterparty_confirmed_at IS NOT NULL`;
  const res = await db.batch([
    db.prepare(`UPDATE trade_handoffs SET owner_confirmed_at = ?3, updated_at = ?3 WHERE id = ?1 AND owner_id = ?2 AND status = 'AWAITING_EXCHANGE' AND owner_confirmed_at IS NULL`).bind(id, me, now),
    db.prepare(`UPDATE trade_handoffs SET counterparty_confirmed_at = ?3, updated_at = ?3 WHERE id = ?1 AND counterparty_id = ?2 AND status = 'AWAITING_EXCHANGE' AND counterparty_confirmed_at IS NULL`).bind(id, me, now),
    db.prepare(`UPDATE trade_posts SET status = 'COMPLETED', closed_at = ?2, updated_at = ?2
                 WHERE status = 'OPEN' AND id = (SELECT trade_post_id FROM trade_handoffs WHERE id = ?1 AND status = 'AWAITING_EXCHANGE' AND ${both})`).bind(id, now),
    db.prepare(`UPDATE trade_offers SET status = 'DECLINED', updated_at = ?2
                 WHERE status = 'PENDING' AND trade_post_id = (SELECT trade_post_id FROM trade_handoffs WHERE id = ?1 AND status = 'AWAITING_EXCHANGE' AND ${both})`).bind(id, now),
    db.prepare(`UPDATE trade_handoffs SET status = 'COMPLETED', completed_at = ?2, updated_at = ?2 WHERE id = ?1 AND status = 'AWAITING_EXCHANGE' AND ${both}`).bind(id, now),
  ]);
  return { recorded: res[0].meta.changes + res[1].meta.changes, completed: res[4].meta.changes === 1 };
}

export async function cancelHandoff(db, id, me, reason) {
  const now = nowIso();
  const r = await db.prepare(`UPDATE trade_handoffs SET status = 'CANCELLED', cancelled_by = ?2, cancel_reason = ?3, updated_at = ?4
       WHERE id = ?1 AND status = 'AWAITING_EXCHANGE' AND (owner_id = ?2 OR counterparty_id = ?2)`).bind(id, me, reason, now).run();
  return r.meta.changes;
}

export async function createReport(db, r) {
  await db.prepare(`INSERT INTO trade_reports (id, handoff_id, reporter_id, reported_id, reason, details, status, created_at)
                    VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'OPEN', ?7)`).bind(r.id, r.handoff_id, r.reporter_id, r.reported_id, r.reason, r.details, nowIso()).run();
}
export const reportExists = async (db, handoffId, me) => !!(await db.prepare('SELECT 1 FROM trade_reports WHERE handoff_id = ?1 AND reporter_id = ?2').bind(handoffId, me).first());

/* Shape for the two participants only. "you" / "other" are resolved from the session user, never from the request. */
export function handoffOut(h, me, extra = {}) {
  if (!h) return null;
  const iAmOwner = h.owner_id === me;
  const side = isOwner => {
    const k = isOwner ? 'owner' : 'cp';
    return { id: isOwner ? h.owner_id : h.counterparty_id, username: h[k + '_username'], display_name: h[k + '_display_name'],
      platform: h[k + '_platform'], region: h[k + '_region'], avatar_url: h[k + '_avatar_url'], embark_id: h[k + '_embark_id'] || null,
      role: isOwner ? 'TRADE_OWNER' : 'OFFER_SENDER', confirmed_at: (isOwner ? h.owner_confirmed_at : h.counterparty_confirmed_at) || null };
  };
  const you = side(iAmOwner), other = side(!iAmOwner);
  /* Embark ID reveal rules (v6.2 security review):
     - AWAITING_EXCHANGE / COMPLETED (accepted under v6.2, where accepting is consent): both IDs.
     - CANCELLED: the other Raider's ID is hidden.
     - HISTORICAL (accepted before v6.2, when IDs were documented as "only shown to you"): only for a trade that was
       actually COMPLETED, and each Raider's ID only after THEY have opened this handoff themselves (opt-in). */
  const otherOpened = !!(iAmOwner ? h.counterparty_seen_at : h.owner_seen_at), youShared = !!(iAmOwner ? h.owner_seen_at : h.counterparty_seen_at);
  if (h.status === 'CANCELLED') other.embark_id = null;
  if (h.status === 'HISTORICAL' && (!h.share_ids || !otherOpened)) other.embark_id = null;
  const ownerGives = h.trade_offered_item_name ? { item_id: h.trade_offered_item_id, name: h.trade_offered_item_name, quantity: h.trade_offered_quantity || 1 } : null;
  const senderGives = h.offer_item_name ? { item_id: h.offer_item_id, name: h.offer_item_name, quantity: null } : null;
  return {
    id: h.id, status: h.status, created_at: h.created_at, updated_at: h.updated_at, completed_at: h.completed_at,
    cancelled: h.status === 'CANCELLED' ? { by_you: h.cancelled_by === me, reason: h.cancel_reason } : null,
    trade: { id: h.trade_post_id, status: h.trade_status, platform: h.trade_platform, region: h.trade_region, created_at: h.trade_created_at,
             wanted: { item_id: h.wanted_item_id, name: h.wanted_item_name, quantity: h.wanted_quantity } },
    offer: { id: h.offer_id, status: h.offer_status, message: h.offer_message },
    /* What each side agreed to hand over, as recorded. null = not specified in the trade/offer (nothing is invented). */
    agreed: { owner_gives: ownerGives, sender_gives: senderGives, owner_wants: { item_id: h.wanted_item_id, name: h.wanted_item_name, quantity: h.wanted_quantity } },
    you, other, your_role: iAmOwner ? 'TRADE_OWNER' : 'OFFER_SENDER',
    historical: h.status === 'HISTORICAL' ? { trade_completed: h.trade_status === 'COMPLETED', can_share: !!h.share_ids, other_opened: otherOpened, you_shared: youShared } : null,
    unseen: !(iAmOwner ? h.owner_seen_at : h.counterparty_seen_at),
    can_confirm: h.status === 'AWAITING_EXCHANGE' && !you.confirmed_at,
    can_cancel: h.status === 'AWAITING_EXCHANGE',
    ...extra,
  };
}
