/*
 * The Raider Network v6.3 — private Loot Trails screenshot endpoints.
 */
import { notFound, bad, forbidden, conflict, ApiError, json, tooMany } from '../http.js';
import { requireUser } from '../session.js';
import { randomId, rateLimit } from '../security.js';
import * as repo from './repo.js';

const IMAGE_TYPES = new Set(['MAP_POSITION', 'LOOT']);

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;

function detectImageType(bytes) {
  if (
    bytes.length >= 8 &&
    [137, 80, 78, 71, 13, 10, 26, 10]
      .every((value, index) => bytes[index] === value)
  ) {
    return 'image/png';
  }

  if (
    bytes.length >= 4 &&
    bytes[0] === 255 &&
    bytes[1] === 216 &&
    bytes[2] === 255
  ) {
    // SOI marker only: some phones and editors append data after the EOI marker.
    return 'image/jpeg';
  }

  if (
    bytes.length >= 12 &&
    String.fromCharCode(...bytes.slice(0, 4)) === 'RIFF' &&
    String.fromCharCode(...bytes.slice(8, 12)) === 'WEBP'
  ) {
    return 'image/webp';
  }

  return null;
}


async function authorizedDiscovery(ctx) {
  const me = await requireUser(ctx);
  const trail = await repo.trailById(ctx.db, ctx.params.id);

  if (
    !trail ||
    !(await repo.canAccessPrivateTrail(ctx.db, trail, me.id))
  ) {
    throw notFound('Loot Trail not found.');
  }

  const discovery = await ctx.db.prepare(`
    SELECT id, trail_id, created_by, review_status
    FROM loot_trail_discoveries
    WHERE id = ? AND trail_id = ?
  `).bind(ctx.params.discoveryId, trail.id).first();

  if (!discovery) {
    throw notFound('Discovery not found.');
  }

  return { me, trail, discovery };
}

async function authorizedImageUpload(ctx) {
  if (!IMAGE_TYPES.has(ctx.params.imageType)) {
    throw bad('Image type must be MAP_POSITION or LOOT.', 'imageType');
  }

  const { me, trail, discovery } = await authorizedDiscovery(ctx);

  if (trail.status !== 'ACTIVE') {
    throw notFound('Loot Trail not found.');
  }

  if (trail.owner_id !== me.id && discovery.created_by !== me.id) {
    throw forbidden('Only the discovery creator or trail owner can upload screenshots.');
  }

  return { me, trail, discovery };
}

export async function uploadTrailImage(ctx) {
  const { me, trail, discovery } = await authorizedImageUpload(ctx);

  if (discovery.review_status === 'APPROVED') {
    throw conflict('This discovery is approved, so its screenshots are locked. The trail owner can set it back to pending first.');
  }

  if (!ctx.env.TRAIL_IMAGES) {
    throw new Error('Private Loot Trails storage is not configured.');
  }

  const type = ctx.request.headers.get('Content-Type')?.split(';')[0]
    .trim().toLowerCase();

  if (!['image/png', 'image/jpeg', 'image/webp'].includes(type)) {
    throw new ApiError(415, 'unsupported_media_type',
      'Upload a PNG, JPEG, or WebP screenshot.');
  }

  const lengthHeader = ctx.request.headers.get('Content-Length');
  if (lengthHeader !== null) {
    const declaredLength = Number(lengthHeader);
    if (!Number.isSafeInteger(declaredLength) ||
        declaredLength < 1 || declaredLength > MAX_IMAGE_BYTES) {
      throw new ApiError(413, 'too_large',
        'Screenshot must be 20 MB or smaller.');
    }
  }

  const existing = await ctx.db.prepare(`
    SELECT id FROM loot_trail_images
    WHERE discovery_id = ? AND image_type = ?
  `).bind(discovery.id, ctx.params.imageType).first();

  if (existing) {
    throw new ApiError(409, 'conflict',
      'A screenshot of this type already exists.');
  }

  await rateLimit(ctx.db, 'trail-image:' + me.id, 30, 3600, tooMany);

  // Read at most one byte beyond the permitted size, including when
  // the browser does not supply a Content-Length header.
  const reader = ctx.request.body?.getReader();
  if (!reader) throw bad('Screenshot file is required.');

  const chunks = [];
  let total = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_IMAGE_BYTES) {
        await reader.cancel();
        throw new ApiError(413, 'too_large',
          'Screenshot must be 20 MB or smaller.');
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  if (total === 0) throw bad('Screenshot file is empty.');

  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }

  const detectedType = detectImageType(bytes);
  if (!detectedType || detectedType !== type) {
    throw bad('Screenshot contents do not match the image format.');
  }

  // Confirm authorization (and that the owner has not approved it meanwhile) immediately before storing the image.
  const recheck = await authorizedImageUpload(ctx);
  if (recheck.discovery.review_status === 'APPROVED') {
    throw conflict('This discovery was approved while you were uploading, so its screenshots are locked.');
  }

  const imageId = randomId('tli');
  const key = 'trails/' + trail.id + '/' + discovery.id + '/' +
    ctx.params.imageType + '/' + imageId;
  const now = new Date().toISOString();

  await ctx.env.TRAIL_IMAGES.put(key, bytes, {
    httpMetadata: { contentType: detectedType }
  });

  try {
    await ctx.db.prepare(`
      INSERT INTO loot_trail_images (
        id, discovery_id, image_type, r2_key,
        content_type, size_bytes, uploaded_by, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      imageId, discovery.id, ctx.params.imageType, key,
      detectedType, total, me.id, now
    ).run();
  } catch (error) {
    await ctx.env.TRAIL_IMAGES.delete(key);
    // Two simultaneous uploads of the same type: UNIQUE(discovery_id, image_type) rejects the second.
    if (/UNIQUE|constraint/i.test(String(error?.message))) {
      throw new ApiError(409, 'conflict', 'A screenshot of this type already exists.');
    }
    throw error;
  }

  return json({
    image: {
      id: imageId,
      discoveryId: discovery.id,
      imageType: ctx.params.imageType,
      contentType: detectedType,
      sizeBytes: total
,
      uploadedAt: now
    }
  }, 201);
}

export async function getTrailImage(ctx) {
  if (!IMAGE_TYPES.has(ctx.params.imageType)) {
    throw notFound('Screenshot not found.');
  }

  const { discovery } = await authorizedDiscovery(ctx);

  const image = await ctx.db.prepare(`
    SELECT r2_key, content_type
    FROM loot_trail_images
    WHERE discovery_id = ? AND image_type = ?
  `).bind(discovery.id, ctx.params.imageType).first();

  if (!image) {
    throw notFound('Screenshot not found.');
  }

  if (!ctx.env.TRAIL_IMAGES) {
    throw new Error('Private Loot Trails storage is not configured.');
  }

  const object = await ctx.env.TRAIL_IMAGES.get(image.r2_key);

  if (!object) {
    throw notFound('Screenshot not found.');
  }

  return new Response(object.body, {
    status: 200,
    headers: {
      'Content-Type': image.content_type,
      'Cache-Control': 'private, no-store',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'same-origin',
      'Content-Security-Policy': "default-src 'none'; sandbox",
      'Content-Disposition': 'inline'
    }
  });
}

/* v6.3: explicit screenshot removal, so a wrong screenshot can be replaced (remove, then upload again).
 * The duplicate-upload protection above is unchanged: a new upload still needs no existing image of that type.
 * Allowed only for the discovery creator or the trail owner, and never while the discovery is APPROVED, so a
 * reviewed result cannot change underneath the owner (the owner sets it back to PENDING first if needed). */
export async function deleteTrailImage(ctx) {
  if (!IMAGE_TYPES.has(ctx.params.imageType)) {
    throw notFound('Screenshot not found.');
  }

  const { me, trail, discovery } = await authorizedImageUpload(ctx);

  const row = await ctx.db.prepare(`
    SELECT d.review_status, i.id AS image_id, i.r2_key
    FROM loot_trail_discoveries d
    LEFT JOIN loot_trail_images i ON i.discovery_id = d.id AND i.image_type = ?
    WHERE d.id = ? AND d.trail_id = ?
  `).bind(ctx.params.imageType, discovery.id, trail.id).first();

  if (!row || !row.image_id) throw notFound('Screenshot not found.');

  if (row.review_status === 'APPROVED') {
    throw new ApiError(409, 'conflict',
      'This discovery is approved, so its screenshots are locked. The trail owner can set it back to pending to allow changes.');
  }

  await rateLimit(ctx.db, 'trail-image:' + me.id, 30, 3600, tooMany);

  const result = await ctx.db.prepare(`
    DELETE FROM loot_trail_images
    WHERE id = ? AND discovery_id = ?
      AND EXISTS (SELECT 1 FROM loot_trail_discoveries d
                  WHERE d.id = ? AND d.trail_id = ? AND d.review_status <> 'APPROVED')
  `).bind(row.image_id, discovery.id, discovery.id, trail.id).run();

  if (result.meta?.changes !== 1) {
    throw new ApiError(409, 'conflict', 'This screenshot can no longer be removed.');
  }

  // Database row first (so the screenshot disappears from the app even if storage cleanup fails), then storage.
  if (ctx.env.TRAIL_IMAGES) {
    try { await ctx.env.TRAIL_IMAGES.delete(row.r2_key); } catch (e) { console.error('R2 delete failed', e); }
  }

  return json({ discoveryId: discovery.id, imageType: ctx.params.imageType, removed: true });
}
