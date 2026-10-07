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
         (SELECT COUNT(*) FROM trade_offers o WHERE o.trade_post_id = t.id AND o.status = 'PENDING') AS pending_offers
    FROM trade_posts t JOIN users u ON u.id = t.user_id`;

export const tradeOut = (t, viewerId) => t && ({
  id: t.id, status: t.status,
  wanted: { item_id: t.wanted_item_id, name: t.wanted_item_name, quantity: t.wanted_quantity },
  offered: t.offered_item_name ? { item_id: t.offered_item_id, name: t.offered_item_name, quantity: t.offered_quantity || 1 } : null,
  open_to_offers: !!t.open_to_offers, region: t.region, platform: t.platform, desired_time: t.desired_time, notes: t.notes,
  created_at: t.created_at, updated_at: t.updated_at, closed_at: t.closed_at,
  owner: { id: t.user_id, username: t.owner_username, display_name: t.owner_display_name, avatar_url: t.owner_avatar_url },
  pending_offers: t.pending_offers || 0, is_mine: !!viewerId && viewerId === t.user_id,
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
