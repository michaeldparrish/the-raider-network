/*
 * The Raider Network v6.3 — Loot Trails repository.
 * Database operations only. API authorization belongs in handlers.
 * Never expose private trail records through unrestricted queries.
 */
import { conflict } from '../http.js';

export async function trailById(db, trailId) {
  return db.prepare(
    'SELECT * FROM loot_trails WHERE id = ?'
  ).bind(trailId).first();
}

export async function trailMembership(db, trailId, userId) {
  return db.prepare(`
    SELECT role, status
    FROM loot_trail_members
    WHERE trail_id = ? AND user_id = ?
  `).bind(trailId, userId).first();
}

export async function canAccessPrivateTrail(db, trail, userId) {
  if (!trail || !userId) return false;
  if (trail.owner_id === userId) return true;

  const membership = await trailMembership(db, trail.id, userId);
  return membership?.status === 'ACCEPTED';
}

export async function trailsForUser(db, userId) {
  const result = await db.prepare(`
    SELECT DISTINCT t.*
    FROM loot_trails t
    LEFT JOIN loot_trail_members m
      ON m.trail_id = t.id AND m.user_id = ?
    WHERE t.owner_id = ?
       OR m.status = 'ACCEPTED'
    ORDER BY t.updated_at DESC
    LIMIT 100
  `).bind(userId, userId).all();

  return result.results || [];
}

export async function createTrail(db, trail) {
  await db.prepare(`
    INSERT INTO loot_trails (
      id, owner_id, title, description, map_id,
      visibility, status, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, 'PRIVATE', 'ACTIVE', ?, ?)
  `).bind(
    trail.id,
    trail.owner_id,
    trail.title,
    trail.description,
    trail.map_id,
    trail.created_at,
    trail.created_at
  ).run();

  return trailById(db, trail.id);
}

export async function discoveriesForTrail(db, trailId) {
  const result = await db.prepare(`
    SELECT *
    FROM loot_trail_discoveries
    WHERE trail_id = ?
    ORDER BY sort_order, created_at
  `).bind(trailId).all();

  return result.results || [];
}

export async function publicDiscoveriesForTrail(db, trailId) {
  const result = await db.prepare(`
    SELECT d.id, d.title, d.item_id, d.notes,
           d.map_level, d.x_normalized, d.y_normalized,
           d.sort_order, d.created_at
    FROM loot_trail_discoveries d
    JOIN loot_trails t ON t.id = d.trail_id
    WHERE d.trail_id = ?
      AND t.visibility = 'PUBLIC'
      AND d.is_public = 1
      AND d.review_status = 'APPROVED'
    ORDER BY d.sort_order, d.created_at
  `).bind(trailId).all();

  return result.results || [];
}

export async function findActiveRaiderByUsername(db, username) {
  return db.prepare(`
    SELECT id, username, display_name
    FROM users
    WHERE username = ? COLLATE NOCASE
      AND status = 'active'
    LIMIT 1
  `).bind(username).first();
}

export async function createTrailInvitation(db, invitation) {
  return db.prepare(`
    INSERT INTO loot_trail_members (
      trail_id, user_id, role, status,
      invited_by, created_at, updated_at
    )
    VALUES (?, ?, 'CONTRIBUTOR', 'INVITED', ?, ?, ?)
  `).bind(
    invitation.trailId,
    invitation.userId,
    invitation.invitedBy,
    invitation.createdAt,
    invitation.createdAt
  ).run();
}

export async function respondToTrailInvitation(
  db, trailId, userId, decision
) {
  const status = decision === 'ACCEPT'
    ? 'ACCEPTED'
    : decision === 'DECLINE'
      ? 'DECLINED'
      : null;

  if (!status) {
    throw new Error('Invalid invitation decision.');
  }

  const now = new Date().toISOString();

  return db.prepare(`
    UPDATE loot_trail_members
    SET status = ?, updated_at = ?
    WHERE trail_id = ?
      AND user_id = ?
      AND status = 'INVITED'
      AND role = 'CONTRIBUTOR'
      AND EXISTS (
        SELECT 1 FROM loot_trails
        WHERE id = ?
          AND status = 'ACTIVE'
      )
  `).bind(
    status, now, trailId, userId, trailId
  ).run();
}

export async function createTrailSession(db, session) {
  await db.prepare(`
    INSERT INTO loot_trail_sessions (
      id, trail_id, created_by, title, notes,
      started_at, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).bind(
    session.id,
    session.trailId,
    session.createdBy,
    session.title,
    session.notes,
    session.startedAt,
    session.createdAt
  ).run();

  return db.prepare(`
    SELECT id, trail_id, created_by, title, notes,
           started_at, ended_at, created_at
    FROM loot_trail_sessions
    WHERE id = ? AND trail_id = ?
  `).bind(session.id, session.trailId).first();
}

export async function createTrailDiscovery(db, discovery) {
  const result = await db.prepare(`
    INSERT INTO loot_trail_discoveries (
      id, trail_id, session_id, created_by,
      title, item_id, notes, map_level,
      x_normalized, y_normalized,
      review_status, is_public,
      created_at, updated_at
    )
    SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
           'PENDING', 0, ?, ?
    WHERE EXISTS (
      SELECT 1 FROM loot_trail_sessions
      WHERE id = ? AND trail_id = ? AND ended_at IS NULL
    )
    AND EXISTS (
      SELECT 1 FROM loot_trails t
      WHERE t.id = ?2 AND t.status = 'ACTIVE'
        AND (t.owner_id = ?4 OR EXISTS (
          SELECT 1 FROM loot_trail_members m
          WHERE m.trail_id = t.id AND m.user_id = ?4 AND m.status = 'ACCEPTED'))
    )
  `).bind(
    discovery.id,
    discovery.trailId,
    discovery.sessionId,
    discovery.createdBy,
    discovery.title,
    discovery.itemId,
    discovery.notes,
    discovery.mapLevel,
    discovery.x,
    discovery.y,
    discovery.createdAt,
    discovery.createdAt,
    discovery.sessionId,
    discovery.trailId
  ).run();

  if (result.meta?.changes !== 1) {
    // Session ended, or the Raider lost access, between the handler's checks and this insert.
    throw conflict('That session has ended or you are no longer in this squad. Reload the trail.', 'sessionId');
  }

  return db.prepare(`
    SELECT id, trail_id, session_id, created_by,
           title, item_id, notes, map_level,
           x_normalized, y_normalized,
           review_status, is_public, created_at
    FROM loot_trail_discoveries
    WHERE id = ? AND trail_id = ?
  `).bind(discovery.id, discovery.trailId).first();
}

export async function reviewTrailDiscovery(db, review) {
  if (!['PENDING', 'APPROVED', 'REJECTED'].includes(review.status)) {
    throw new Error('Invalid discovery review status.');
  }

  const result = await db.prepare(`
    UPDATE loot_trail_discoveries
    SET review_status = ?,
        is_public = 0,
        updated_at = ?
    WHERE id = ?
      AND trail_id = ?
      AND EXISTS (
        SELECT 1
        FROM loot_trails
        WHERE id = ?
          AND owner_id = ?
          AND status = 'ACTIVE'
      )
  `).bind(
    review.status,
    review.updatedAt,
    review.discoveryId,
    review.trailId,
    review.trailId,
    review.ownerId
  ).run();

  if (result.meta?.changes !== 1) {
    return null;
  }

  return db.prepare(`
    SELECT id, trail_id, session_id, created_by,
           title, item_id, notes, map_level,
           x_normalized, y_normalized,
           review_status, is_public, created_at, updated_at
    FROM loot_trail_discoveries
    WHERE id = ? AND trail_id = ?
  `).bind(review.discoveryId, review.trailId).first();
}

/* ---------------------------------------------------------------- v6.3 frontend support
 * Read models for the Loot Trails UI. Every function here is called only after the handler has checked access
 * (owner or ACCEPTED member) except publicDiscoveriesForTrail above. None of them returns r2_key, emails,
 * Embark IDs, password hashes or internal user IDs to the browser (shaping happens in the handlers). */

/* Trails I own or have joined, with counts for the dashboard. */
export async function trailsForUserWithStats(db, userId) {
  const result = await db.prepare(`
    SELECT t.*,
           CASE WHEN t.owner_id = ?1 THEN 'OWNER' ELSE 'CONTRIBUTOR' END AS my_role,
           (SELECT COUNT(*) FROM loot_trail_discoveries d WHERE d.trail_id = t.id) AS discovery_count,
           (SELECT COUNT(*) FROM loot_trail_discoveries d WHERE d.trail_id = t.id AND d.review_status = 'APPROVED') AS approved_count,
           (SELECT COUNT(*) FROM loot_trail_progress p JOIN loot_trail_discoveries dd ON dd.id = p.discovery_id AND dd.review_status <> 'REJECTED' WHERE p.trail_id = t.id AND p.user_id = ?1) AS my_completed_count,
           (SELECT COUNT(*) FROM loot_trail_discoveries d WHERE d.trail_id = t.id AND d.review_status <> 'REJECTED') AS active_count,
           (SELECT COUNT(*) FROM loot_trail_members m WHERE m.trail_id = t.id AND m.status = 'ACCEPTED') + 1 AS squad_size,
           (SELECT COUNT(*) FROM loot_trail_sessions s WHERE s.trail_id = t.id) AS session_count,
           ou.display_name AS owner_display_name, ou.username AS owner_username
      FROM loot_trails t
      JOIN users ou ON ou.id = t.owner_id
     WHERE t.owner_id = ?1
        OR EXISTS (SELECT 1 FROM loot_trail_members m WHERE m.trail_id = t.id AND m.user_id = ?1 AND m.status = 'ACCEPTED')
     ORDER BY t.updated_at DESC
     LIMIT 100`).bind(userId).all();
  return result.results || [];
}

/* Pending invitations addressed to me (trail title and owner name only). */
export async function pendingInvitationsForUser(db, userId) {
  const result = await db.prepare(`
    SELECT m.trail_id, m.created_at AS invited_at, t.title, t.map_id,
           ou.display_name AS owner_display_name, ou.username AS owner_username
      FROM loot_trail_members m
      JOIN loot_trails t ON t.id = m.trail_id
      JOIN users ou ON ou.id = t.owner_id
     WHERE m.user_id = ? AND m.status = 'INVITED' AND m.role = 'CONTRIBUTOR' AND t.status = 'ACTIVE'
     ORDER BY m.created_at DESC
     LIMIT 50`).bind(userId).all();
  return result.results || [];
}

export async function membersForTrail(db, trailId) {
  const result = await db.prepare(`
    SELECT m.role, m.status, m.created_at, m.updated_at, u.username, u.display_name, u.avatar_url, u.platform,
           (SELECT COUNT(*) FROM loot_trail_progress p JOIN loot_trail_discoveries dd ON dd.id = p.discovery_id AND dd.review_status <> 'REJECTED' WHERE p.trail_id = m.trail_id AND p.user_id = m.user_id) AS completed_count
      FROM loot_trail_members m JOIN users u ON u.id = m.user_id
     WHERE m.trail_id = ?
     ORDER BY CASE m.status WHEN 'ACCEPTED' THEN 0 WHEN 'INVITED' THEN 1 ELSE 2 END, m.created_at`).bind(trailId).all();
  return result.results || [];
}

export async function ownerSummary(db, trail) {
  return db.prepare(`
    SELECT u.username, u.display_name, u.avatar_url, u.platform,
           (SELECT COUNT(*) FROM loot_trail_progress p JOIN loot_trail_discoveries dd ON dd.id = p.discovery_id AND dd.review_status <> 'REJECTED' WHERE p.trail_id = ?2 AND p.user_id = u.id) AS completed_count
      FROM users u WHERE u.id = ?1`).bind(trail.owner_id, trail.id).first();
}

export async function sessionsForTrail(db, trailId) {
  const result = await db.prepare(`
    SELECT s.id, s.title, s.notes, s.started_at, s.ended_at, s.created_at, s.created_by, u.display_name AS created_by_name,
           (SELECT COUNT(*) FROM loot_trail_discoveries d WHERE d.session_id = s.id) AS discovery_count
      FROM loot_trail_sessions s JOIN users u ON u.id = s.created_by
     WHERE s.trail_id = ?
     ORDER BY s.started_at DESC`).bind(trailId).all();
  return result.results || [];
}

/* Private (member) discovery rows with creator name and which screenshots exist — never the R2 key. */
export async function discoveriesForTrailDetailed(db, trailId) {
  const result = await db.prepare(`
    SELECT d.id, d.session_id, d.created_by, d.title, d.item_id, d.notes, d.map_level, d.x_normalized, d.y_normalized,
           d.review_status, d.is_public, d.sort_order, d.created_at, d.updated_at,
           u.display_name AS creator_display_name, u.username AS creator_username,
           EXISTS (SELECT 1 FROM loot_trail_images i WHERE i.discovery_id = d.id AND i.image_type = 'MAP_POSITION') AS has_map_image,
           EXISTS (SELECT 1 FROM loot_trail_images i WHERE i.discovery_id = d.id AND i.image_type = 'LOOT') AS has_loot_image
      FROM loot_trail_discoveries d JOIN users u ON u.id = d.created_by
     WHERE d.trail_id = ?
     ORDER BY d.sort_order, d.created_at`).bind(trailId).all();
  return result.results || [];
}

export async function sessionById(db, trailId, sessionId) {
  return db.prepare('SELECT id, trail_id, created_by, ended_at FROM loot_trail_sessions WHERE id = ? AND trail_id = ?').bind(sessionId, trailId).first();
}

/* Ends a session once. Only the session creator or the trail owner may end it (checked again in SQL). */
export async function endTrailSession(db, { trailId, sessionId, userId, endedAt }) {
  return db.prepare(`
    UPDATE loot_trail_sessions SET ended_at = ?
     WHERE id = ? AND trail_id = ? AND ended_at IS NULL
       AND (created_by = ? OR EXISTS (SELECT 1 FROM loot_trails t WHERE t.id = ? AND t.owner_id = ? AND t.status = 'ACTIVE'))`)
    .bind(endedAt, sessionId, trailId, userId, trailId, userId).run();
}

/* Re-invite a Raider who previously declined or was removed (the row already exists). */
export async function reinviteTrailMember(db, { trailId, userId, invitedBy, now }) {
  return db.prepare(`
    UPDATE loot_trail_members SET status = 'INVITED', invited_by = ?, updated_at = ?
     WHERE trail_id = ? AND user_id = ? AND role = 'CONTRIBUTOR' AND status IN ('DECLINED', 'REMOVED')`)
    .bind(invitedBy, now, trailId, userId).run();
}

export async function removeTrailMember(db, { trailId, userId, ownerId, now }) {
  return db.prepare(`
    UPDATE loot_trail_members SET status = 'REMOVED', updated_at = ?
     WHERE trail_id = ? AND user_id = ? AND role = 'CONTRIBUTOR' AND status IN ('INVITED', 'ACCEPTED')
       AND EXISTS (SELECT 1 FROM loot_trails t WHERE t.id = ? AND t.owner_id = ? AND t.status = 'ACTIVE')`)
    .bind(now, trailId, userId, trailId, ownerId).run();
}

export async function touchTrail(db, trailId, now) {
  return db.prepare('UPDATE loot_trails SET updated_at = ? WHERE id = ?').bind(now, trailId).run();
}
