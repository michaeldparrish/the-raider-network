/*
 * The Raider Network v6.3 — Loot Trails API handlers.
 * Identity always comes from the authenticated session.
 */
import { json, readJson, bad, notFound, tooMany, conflict } from '../http.js';
import { requireUser } from '../session.js';
import { randomId, rateLimit } from '../security.js';
import * as repo from './repo.js';

const SUPPORTED_MAPS = new Set([
  'dam-battlegrounds',
  'buried-city',
  'spaceport',
  'stella-montis',
  'the-blue-gate',
  'riven-tides',
  'pendola-pass'
]);

/* Private (owner / accepted member) shape. */
function trailOutput(trail, viewerId) {
  return {
    id: trail.id,
    title: trail.title,
    description: trail.description,
    mapId: trail.map_id,
    visibility: trail.visibility,
    status: trail.status,
    publishedAt: trail.published_at || null,
    createdAt: trail.created_at,
    updatedAt: trail.updated_at,
    ...(viewerId ? { myRole: trail.owner_id === viewerId ? 'OWNER' : 'CONTRIBUTOR' } : {})
  };
}

/* v6.3 security review: what an anonymous or non-member visitor of a PUBLIC trail receives.
   No description (written for the squad), no internal status/timestamps, no owner or member identity. */
function publicTrailOutput(trail) {
  return {
    id: trail.id,
    title: trail.title,
    mapId: trail.map_id,
    visibility: 'PUBLIC',
    publishedAt: trail.published_at || null
  };
}

function discoveryOutput(d, me, isOwner) {
  return {
    id: d.id,
    sessionId: d.session_id,
    title: d.title,
    itemId: d.item_id || null,
    notes: d.notes,
    mapLevel: d.map_level,
    x: d.x_normalized,
    y: d.y_normalized,
    reviewStatus: d.review_status,
    isPublic: Boolean(d.is_public),
    createdAt: d.created_at,
    updatedAt: d.updated_at,
    creator: { username: d.creator_username, displayName: d.creator_display_name },
    mine: d.created_by === me,
    images: { MAP_POSITION: Boolean(d.has_map_image), LOOT: Boolean(d.has_loot_image) },
    canUpload: isOwner || d.created_by === me,
    canReplaceImages: (isOwner || d.created_by === me) && d.review_status !== 'APPROVED'
  };
}

function publicDiscoveryOutput(d) {
  return {
    id: d.id,
    title: d.title,
    itemId: d.item_id || null,
    notes: d.notes,
    mapLevel: d.map_level,
    x: d.x_normalized,
    y: d.y_normalized
  };
}

export async function createTrail(ctx) {
  const me = await requireUser(ctx);
  const body = await readJson(ctx.request);

  const title = typeof body.title === 'string'
    ? body.title.trim() : '';
  const description = typeof body.description === 'string'
    ? body.description.trim() : '';
  const mapId = typeof body.mapId === 'string'
    ? body.mapId.trim() : '';

  if (!title || title.length > 100) {
    throw bad('Trail title must be 1–100 characters.', 'title');
  }
  if (description.length > 2000) {
    throw bad('Description must be 2000 characters or fewer.', 'description');
  }
  if (!SUPPORTED_MAPS.has(mapId)) {
    throw bad('Please select a supported ARC Raiders map.', 'mapId');
  }

  await rateLimit(
    ctx.db,
    'trail-create:' + me.id,
    10,
    3600,
    tooMany
  );

  const now = new Date().toISOString();
  const trail = await repo.createTrail(ctx.db, {
    id: randomId('trl'),
    owner_id: me.id,
    title,
    description,
    map_id: mapId,
    created_at: now
  });

  return json({ trail: trailOutput(trail, me.id) }, 201);
}

export async function listTrails(ctx) {
  const me = await requireUser(ctx);
  const trails = await repo.trailsForUserWithStats(ctx.db, me.id);

  return json({
    trails: trails.map(t => ({
      ...trailOutput(t, me.id),
      owner: { username: t.owner_username, displayName: t.owner_display_name },
      stats: {
        discoveries: t.discovery_count,
        approved: t.approved_count,
        myCompleted: t.my_completed_count,
        active: t.active_count,
        squadSize: t.squad_size,
        sessions: t.session_count
      }
    }))
  });
}

export async function getTrail(ctx) {
  const trail = await repo.trailById(ctx.db, ctx.params.id);
  if (!trail) throw notFound('Loot Trail not found.');

  const userId = ctx.session?.user.id || null;
  const member = await repo.canAccessPrivateTrail(ctx.db, trail, userId);

  if (!member && trail.visibility !== 'PUBLIC') throw notFound('Loot Trail not found.');

  /* Public view: only owner-approved AND explicitly published discoveries, no squad data. */
  if (!member) {
    const discoveries = await repo.publicDiscoveriesForTrail(ctx.db, trail.id);
    return json({
      view: 'PUBLIC',
      trail: publicTrailOutput(trail),
      discoveries: discoveries.map(publicDiscoveryOutput),
      myCompletedDiscoveryIds: []
    });
  }

  const isOwner = trail.owner_id === userId;
  const [discoveries, sessions, members, owner, progress] = await Promise.all([
    repo.discoveriesForTrailDetailed(ctx.db, trail.id),
    repo.sessionsForTrail(ctx.db, trail.id),
    repo.membersForTrail(ctx.db, trail.id),
    repo.ownerSummary(ctx.db, trail),
    ctx.db.prepare(`
      SELECT discovery_id
      FROM loot_trail_progress
      WHERE trail_id = ? AND user_id = ?
    `).bind(trail.id, userId).all()
  ]);

  const myCompletedDiscoveryIds = (progress.results || []).map(row => row.discovery_id);
  /* Squad list: the owner sees every invitation state; contributors see the owner and accepted members.
     Completion is shown as a count per Raider to the owner only (squad activity); contributors see only their own. */
  const visibleMembers = members.filter(m => isOwner || m.status === 'ACCEPTED');
  const squad = [
    { username: owner.username, displayName: owner.display_name, avatarUrl: owner.avatar_url, platform: owner.platform,
      role: 'OWNER', status: 'ACCEPTED', ...(isOwner ? { completedCount: owner.completed_count } : {}) },
    ...visibleMembers.map(m => ({
      username: m.username, displayName: m.display_name, avatarUrl: m.avatar_url, platform: m.platform,
      role: m.role, status: m.status, invitedAt: m.created_at,
      ...(isOwner && m.status === 'ACCEPTED' ? { completedCount: m.completed_count } : {})
    }))
  ];

  return json({
    view: 'MEMBER',
    trail: trailOutput(trail, userId),
    discoveries: discoveries.map(d => discoveryOutput(d, userId, isOwner)),
    sessions: sessions.map(x => ({
      id: x.id, title: x.title, notes: x.notes, startedAt: x.started_at, endedAt: x.ended_at,
      startedBy: x.created_by_name, discoveryCount: x.discovery_count,
      canEnd: !x.ended_at && trail.status === 'ACTIVE' && (isOwner || x.created_by === userId)
    })),
    squad,
    myCompletedDiscoveryIds,
    permissions: {
      isOwner,
      canInvite: isOwner && trail.status === 'ACTIVE',
      canReview: isOwner && trail.status === 'ACTIVE',
      canPublish: isOwner && trail.status === 'ACTIVE',
      canContribute: trail.status === 'ACTIVE'
    }
  });
}

/* Pending invitations addressed to the signed-in Raider. */
export async function myTrailInvitations(ctx) {
  const me = await requireUser(ctx);
  const rows = await repo.pendingInvitationsForUser(ctx.db, me.id);
  return json({
    invitations: rows.map(r => ({
      trailId: r.trail_id, title: r.title, mapId: r.map_id, invitedAt: r.invited_at,
      owner: { username: r.owner_username, displayName: r.owner_display_name }
    }))
  });
}

export async function inviteTrailMember(ctx) {
  const me = await requireUser(ctx);

  const trail = await repo.trailById(ctx.db, ctx.params.id);
  if (!trail || trail.owner_id !== me.id || trail.status !== 'ACTIVE') {
    throw notFound('Loot Trail not found.');
  }

  const body = await readJson(ctx.request);
  const username = typeof body.username === 'string'
    ? body.username.trim() : '';

  if (!username || username.length > 40) {
    throw bad('Enter a valid Raider username.', 'username');
  }

  await rateLimit(
    ctx.db,
    'trail-invite:' + me.id,
    20,
    3600,
    tooMany
  );

  const raider = await repo.findActiveRaiderByUsername(
    ctx.db,
    username
  );

  if (!raider) {
    throw notFound('Raider not found.');
  }

  if (raider.id === me.id) {
    throw bad('You already own this Loot Trail.', 'username');
  }

  const existing = await repo.trailMembership(
    ctx.db,
    trail.id,
    raider.id
  );

  const now = new Date().toISOString();

  if (existing && ['INVITED', 'ACCEPTED'].includes(existing.status)) {
    throw conflict(existing.status === 'ACCEPTED'
      ? 'This Raider is already in your squad.'
      : 'This Raider already has a pending invitation.', 'username');
  }

  if (existing) {
    // Declined or removed earlier: the owner may invite again (the Raider still has to accept).
    await repo.reinviteTrailMember(ctx.db, { trailId: trail.id, userId: raider.id, invitedBy: me.id, now });
  } else {
    try {
      await repo.createTrailInvitation(ctx.db, {
        trailId: trail.id,
        userId: raider.id,
        invitedBy: me.id,
        createdAt: now
      });
    } catch (error) {
      // Two simultaneous invites: the primary key rejects the second one.
      if (/UNIQUE|PRIMARY KEY|constraint/i.test(String(error?.message))) {
        throw conflict('This Raider already has a pending invitation.', 'username');
      }
      throw error;
    }
  }

  return json({
    invitation: {
      trailId: trail.id,
      username: raider.username,
      displayName: raider.display_name,
      status: 'INVITED'
    }
  }, 201);
}

export async function respondToInvitation(ctx) {
  const me = await requireUser(ctx);

  const body = await readJson(ctx.request);
  const decision = typeof body.decision === 'string'
    ? body.decision.trim().toUpperCase()
    : '';

  if (!['ACCEPT', 'DECLINE'].includes(decision)) {
    throw bad('Decision must be ACCEPT or DECLINE.', 'decision');
  }

  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (!trail || trail.status !== 'ACTIVE') {
    throw notFound('Invitation not found.');
  }

  const membership = await repo.trailMembership(
    ctx.db,
    trail.id,
    me.id
  );

  if (
    !membership ||
    membership.role !== 'CONTRIBUTOR' ||
    membership.status !== 'INVITED'
  ) {
    throw notFound('Invitation not found.');
  }

  const result = await repo.respondToTrailInvitation(
    ctx.db,
    trail.id,
    me.id,
    decision
  );

  if (result.meta?.changes !== 1) {
    throw notFound('Invitation is no longer pending.');
  }

  return json({
    trailId: trail.id,
    status: decision === 'ACCEPT' ? 'ACCEPTED' : 'DECLINED'
  });
}

export async function createTrailSession(ctx) {
  const me = await requireUser(ctx);

  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (
    !trail ||
    trail.status !== 'ACTIVE' ||
    !(await repo.canAccessPrivateTrail(ctx.db, trail, me.id))
  ) {
    throw notFound('Loot Trail not found.');
  }

  const body = await readJson(ctx.request);

  const title = typeof body.title === 'string'
    ? body.title.trim()
    : '';

  const notes = typeof body.notes === 'string'
    ? body.notes.trim()
    : '';

  if (!title || title.length > 100) {
    throw bad('Session title must be 1–100 characters.', 'title');
  }

  if (notes.length > 2000) {
    throw bad('Session notes must be 2000 characters or fewer.', 'notes');
  }

  await rateLimit(
    ctx.db,
    'trail-session:' + me.id,
    20,
    3600,
    tooMany
  );

  const now = new Date().toISOString();

  const session = await repo.createTrailSession(ctx.db, {
    id: randomId('tls'),
    trailId: trail.id,
    createdBy: me.id,
    title,
    notes,
    startedAt: now,
    createdAt: now
  });

  await repo.touchTrail(ctx.db, trail.id, now);

  return json({
    session: {
      id: session.id,
      trailId: session.trail_id,
      title: session.title,
      notes: session.notes,
      startedAt: session.started_at,
      endedAt: session.ended_at
    }
  }, 201);
}

const MAP_LEVELS = {
  'dam-battlegrounds': ['all'],
  'buried-city': ['all'],
  'spaceport': ['all'],
  'stella-montis': ['2', '1'],
  'the-blue-gate': ['all'],
  'riven-tides': ['all'],
  'pendola-pass': ['all']
};

export async function createTrailDiscovery(ctx) {
  const me = await requireUser(ctx);

  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (
    !trail ||
    trail.status !== 'ACTIVE' ||
    !(await repo.canAccessPrivateTrail(ctx.db, trail, me.id))
  ) {
    throw notFound('Loot Trail not found.');
  }

  const body = await readJson(ctx.request);

  const title = typeof body.title === 'string'
    ? body.title.trim() : '';
  const notes = typeof body.notes === 'string'
    ? body.notes.trim() : '';
  const sessionId = typeof body.sessionId === 'string'
    ? body.sessionId.trim() : '';
  const mapLevel = typeof body.mapLevel === 'string'
    ? body.mapLevel.trim() : '';
  const itemId = typeof body.itemId === 'string'
    ? body.itemId.trim() : '';

  if (!title || title.length > 120) {
    throw bad('Discovery title must be 1–120 characters.', 'title');
  }

  if (notes.length > 2000) {
    throw bad('Discovery notes must be 2000 characters or fewer.', 'notes');
  }

  if (!sessionId || sessionId.length > 100) {
    throw bad('A valid gameplay session is required.', 'sessionId');
  }

  if (!MAP_LEVELS[trail.map_id]?.includes(mapLevel)) {
    throw bad('Invalid map level for this Loot Trail.', 'mapLevel');
  }

  if (
    typeof body.x !== 'number' ||
    !Number.isFinite(body.x) ||
    body.x < 0 || body.x > 1 ||
    typeof body.y !== 'number' ||
    !Number.isFinite(body.y) ||
    body.y < 0 || body.y > 1
  ) {
    throw bad('Map coordinates must be between 0 and 1.', 'coordinates');
  }

  if (itemId.length > 100) {
    throw bad('Item ID is too long.', 'itemId');
  }

  const session = await ctx.db.prepare(`
    SELECT id, ended_at FROM loot_trail_sessions
    WHERE id = ? AND trail_id = ?
  `).bind(sessionId, trail.id).first();

  if (!session) {
    throw bad('Session does not belong to this Loot Trail.', 'sessionId');
  }

  if (session.ended_at) {
    throw bad('This session has ended. Start a new session to record more discoveries.', 'sessionId');
  }

  await rateLimit(
    ctx.db,
    'trail-discovery:' + me.id,
    60,
    3600,
    tooMany
  );

  const now = new Date().toISOString();

  const discovery = await repo.createTrailDiscovery(ctx.db, {
    id: randomId('tld'),
    trailId: trail.id,
    sessionId,
    createdBy: me.id,
    title,
    itemId: itemId || null,
    notes,
    mapLevel,
    x: body.x,
    y: body.y,
    createdAt: now
  });

  await repo.touchTrail(ctx.db, trail.id, now);

  return json({
    discovery: {
      id: discovery.id,
      trailId: discovery.trail_id,
      sessionId: discovery.session_id,
      title: discovery.title,
      itemId: discovery.item_id,
      notes: discovery.notes,
      mapLevel: discovery.map_level,
      x: discovery.x_normalized,
      y: discovery.y_normalized,
      reviewStatus: discovery.review_status,
      isPublic: Boolean(discovery.is_public)
    }
  }, 201);
}


export async function publishTrailDiscovery(ctx) {
  const me = await requireUser(ctx);
  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (!trail || trail.owner_id !== me.id || trail.status !== 'ACTIVE') {
    throw notFound('Loot Trail not found.');
  }

  const body = await readJson(ctx.request);
  if (typeof body.publish !== 'boolean') {
    throw bad('publish must be true or false.', 'publish');
  }

  await rateLimit(ctx.db, 'trail-publish:' + me.id, 60, 3600, tooMany);

  const now = new Date().toISOString();

  const result = await ctx.db.prepare(`
    UPDATE loot_trail_discoveries
    SET is_public = ?, updated_at = ?
    WHERE id = ?
      AND trail_id = ?
      AND review_status = 'APPROVED'
      AND EXISTS (
        SELECT 1 FROM loot_trails
        WHERE id = ? AND owner_id = ? AND status = 'ACTIVE'
      )
  `).bind(
    body.publish ? 1 : 0, now,
    ctx.params.discoveryId, trail.id, trail.id, me.id
  ).run();

  if (result.meta?.changes !== 1) {
    throw bad('Only approved discoveries can be published.');
  }

  return json({
    discoveryId: ctx.params.discoveryId,
    isPublic: body.publish
  });
}

export async function setTrailVisibility(ctx) {
  const me = await requireUser(ctx);
  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (!trail || trail.owner_id !== me.id || trail.status !== 'ACTIVE') {
    throw notFound('Loot Trail not found.');
  }

  const body = await readJson(ctx.request);
  if (!['PRIVATE', 'PUBLIC'].includes(body.visibility)) {
    throw bad('Visibility must be PRIVATE or PUBLIC.', 'visibility');
  }

  await rateLimit(ctx.db, 'trail-visibility:' + me.id, 30, 3600, tooMany);

  const now = new Date().toISOString();
  await ctx.db.prepare(`
    UPDATE loot_trails
    SET visibility = ?,
        published_at = CASE
          WHEN ? = 'PUBLIC' THEN COALESCE(published_at, ?)
          ELSE NULL
        END,
        updated_at = ?
    WHERE id = ? AND owner_id = ? AND status = 'ACTIVE'
  `).bind(
    body.visibility, body.visibility, now, now, trail.id, me.id
  ).run();

  return json({ trailId: trail.id, visibility: body.visibility });
}

export async function setTrailProgress(ctx) {
  const me = await requireUser(ctx);
  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (!trail || !(await repo.canAccessPrivateTrail(ctx.db, trail, me.id))) {
    throw notFound('Loot Trail not found.');
  }

  if (trail.status !== 'ACTIVE') {
    throw bad('This Loot Trail is archived.');
  }

  const body = await readJson(ctx.request);
  if (typeof body.completed !== 'boolean') {
    throw bad('completed must be true or false.', 'completed');
  }

  await rateLimit(ctx.db, 'trail-progress:' + me.id, 120, 3600, tooMany);

  const discovery = await ctx.db.prepare(`
    SELECT id FROM loot_trail_discoveries
    WHERE id = ? AND trail_id = ?
  `).bind(ctx.params.discoveryId, trail.id).first();

  if (!discovery) throw notFound('Discovery not found.');

  if (body.completed) {
    await ctx.db.prepare(`
      INSERT INTO loot_trail_progress
        (trail_id, discovery_id, user_id, completed_at)
      VALUES (?, ?, ?, ?)
      ON CONFLICT(discovery_id, user_id)
      DO UPDATE SET completed_at = excluded.completed_at
    `).bind(
      trail.id, discovery.id, me.id, new Date().toISOString()
    ).run();
  } else {
    await ctx.db.prepare(`
      DELETE FROM loot_trail_progress
      WHERE trail_id = ? AND discovery_id = ? AND user_id = ?
    `).bind(trail.id, discovery.id, me.id).run();
  }

  return json({
    discoveryId: discovery.id,
    completed: body.completed
  });
}

export async function reviewTrailDiscovery(ctx) {
  const me = await requireUser(ctx);

  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (
    !trail ||
    trail.owner_id !== me.id ||
    trail.status !== 'ACTIVE'
  ) {
    throw notFound('Loot Trail not found.');
  }

  const discoveryId = ctx.params.discoveryId;

  if (!discoveryId) {
    throw bad('A discovery ID is required.', 'discoveryId');
  }

  const body = await readJson(ctx.request);
  const status = typeof body.status === 'string'
    ? body.status.trim().toUpperCase() : '';

  if (!['APPROVED', 'REJECTED', 'PENDING'].includes(status)) {
    throw bad(
      'Review status must be APPROVED, REJECTED, or PENDING.',
      'status'
    );
  }

  await rateLimit(
    ctx.db,
    'trail-review:' + me.id,
    60,
    3600,
    tooMany
  );

  const discovery = await repo.reviewTrailDiscovery(ctx.db, {
    trailId: trail.id,
    discoveryId,
    ownerId: me.id,
    status,
    updatedAt: new Date().toISOString()
  });

  if (!discovery) {
    throw notFound('Discovery not found in this Loot Trail.');
  }

  return json({
    discovery: {
      id: discovery.id,
      trailId: discovery.trail_id,
      sessionId: discovery.session_id,
      title: discovery.title,
      reviewStatus: discovery.review_status,
      isPublic: Boolean(discovery.is_public),
      updatedAt: discovery.updated_at
    }
  });
}

/* v6.3: end a gaming session (no more discoveries can be added to it; its discoveries are kept).
   Allowed for the Raider who started the session or the trail owner. */
export async function endTrailSession(ctx) {
  const me = await requireUser(ctx);
  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (!trail || trail.status !== 'ACTIVE' || !(await repo.canAccessPrivateTrail(ctx.db, trail, me.id))) {
    throw notFound('Loot Trail not found.');
  }

  const session = await repo.sessionById(ctx.db, trail.id, ctx.params.sessionId);
  if (!session) throw notFound('Session not found.');
  if (session.ended_at) throw conflict('This session has already ended.');
  if (session.created_by !== me.id && trail.owner_id !== me.id) {
    throw notFound('Session not found.');
  }

  await rateLimit(ctx.db, 'trail-session-end:' + me.id, 30, 3600, tooMany);

  const now = new Date().toISOString();
  const result = await repo.endTrailSession(ctx.db, { trailId: trail.id, sessionId: session.id, userId: me.id, endedAt: now });
  if (result.meta?.changes !== 1) throw conflict('This session has already ended.');
  await repo.touchTrail(ctx.db, trail.id, now);

  return json({ session: { id: session.id, endedAt: now } });
}

/* v6.3: the owner removes a contributor or withdraws a pending invitation. Their discoveries stay on the trail. */
export async function removeTrailMember(ctx) {
  const me = await requireUser(ctx);
  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (!trail || trail.owner_id !== me.id || trail.status !== 'ACTIVE') {
    throw notFound('Loot Trail not found.');
  }

  const body = await readJson(ctx.request);
  const username = typeof body.username === 'string' ? body.username.trim() : '';
  if (!username || username.length > 40) throw bad('Enter a valid Raider username.', 'username');

  await rateLimit(ctx.db, 'trail-member-remove:' + me.id, 30, 3600, tooMany);

  const raider = await repo.findActiveRaiderByUsername(ctx.db, username);
  if (!raider) throw notFound('Raider not found.');

  const result = await repo.removeTrailMember(ctx.db, { trailId: trail.id, userId: raider.id, ownerId: me.id, now: new Date().toISOString() });
  if (result.meta?.changes !== 1) throw notFound('This Raider is not in your squad.');

  return json({ trailId: trail.id, username: raider.username, status: 'REMOVED' });
}
