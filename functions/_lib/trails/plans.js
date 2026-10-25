/*
 * The Raider Network v6.4 — Loot Trail amplification plans (multi-material hunting).
 * A plan is one weapon build inside a trail. Requirements are calculated HERE from the published
 * data/amplification.json; the browser only sends the weapon, "already amplified?" and the chosen enhancements.
 * Every Raider keeps their own stage (activation, installed enhancements) and material counts.
 * Access: the trail owner and accepted members only (same rule as every private Loot Trails endpoint).
 */
import { json, readJson, bad, notFound, forbidden, conflict, tooMany } from '../http.js';
import { requireUser } from '../session.js';
import { randomId, rateLimit } from '../security.js';
import { ampReference } from '../reference.js';
import * as repo from './repo.js';

const MAX_PLANS = 10, MAX_QTY = 999;
const ACTIVATION = new Set(['REQUIRED', 'NOT_NEEDED', 'COMPLETED']);

/* ---------------------------------------------------------------- pure plan maths (mirrors assets/js/amplification.js) */
export function closure(weapon, ids) {
  const out = new Set();
  const walk = id => {
    if (out.has(id)) return;
    const u = weapon.upgrades.find(x => x.id === id);
    if (!u) return;
    out.add(id);
    (u.requires || []).forEach(walk);
  };
  ids.forEach(walk);
  return out;
}

export function conflictsIn(weapon, set) {
  const bad = [];
  for (const id of set) {
    for (const x of weapon.upgrades.find(u => u.id === id)?.excludes || []) if (set.has(x)) bad.push([id, x]);
  }
  return bad;
}

const itemKey = c => c.itemId || 'label:' + String(c.label || 'Unknown part').slice(0, 100);

/* Requirement rows for a build: the module (ACTIVATION), then per enhancement its install cost (ENHANCEMENT)
   and research parts (RESEARCH). Rows with the same key inside one stage+upgrade are merged. */
export function requirementsFor(tier, weapon, set) {
  const rows = new Map();
  let order = 0;
  const add = (stage, upgradeId, c) => {
    const key = `${stage}|${upgradeId}|${itemKey(c)}`;
    const r = rows.get(key);
    if (r) { r.requiredQty = r.requiredQty == null || c.qty == null ? null : r.requiredQty + c.qty; return; }
    rows.set(key, { stage, upgradeId, itemKey: itemKey(c), requiredQty: c.qty ?? null, qtyStatus: c.status || 'UNVERIFIED', sortOrder: order++ });
  };
  add('ACTIVATION', '', { itemId: tier.itemId, qty: 1, status: tier.status || 'UNVERIFIED' });
  for (const u of weapon.upgrades.filter(x => set.has(x.id))) {
    for (const c of u.cost) add('ENHANCEMENT', u.id, c);
    for (const c of u.research?.cost || []) add('RESEARCH', u.id, c);
  }
  return [...rows.values()];
}

/* Outstanding per item for one Raider: count each requirement row once, skip the activation stage when it is
   NOT_NEEDED or COMPLETED, skip installed enhancements, then subtract what they had and collected (never below 0). */
export function outstandingFor(requirements, member, installed, progress) {
  const inst = new Set(installed.map(i => i.upgrade_id ?? i.upgradeId));
  const prog = new Map(progress.map(p => [p.item_key ?? p.itemKey, p]));
  const out = new Map();
  for (const r of requirements) {
    const stage = r.stage, up = r.upgrade_id ?? r.upgradeId, key = r.item_key ?? r.itemKey, qty = r.required_qty ?? r.requiredQty;
    const counts = stage === 'ACTIVATION' ? (member?.activation || 'REQUIRED') === 'REQUIRED' : !inst.has(up);
    const o = out.get(key) || { itemKey: key, required: 0, unknown: false, doneRequired: 0 };
    if (counts) { if (qty == null) o.unknown = true; else o.required += qty; }
    else if (qty != null) o.doneRequired += qty;
    out.set(key, o);
  }
  return [...out.values()].map(o => {
    const p = prog.get(o.itemKey) || {};
    const had = p.had_qty ?? p.had ?? 0, collected = p.collected_qty ?? p.collected ?? 0;
    // materials already spent on completed stages are no longer available for the remaining ones
    const available = Math.max(0, had + collected - o.doneRequired);
    return { itemKey: o.itemKey, stillRequired: o.required, unknownQty: o.unknown, had, collected, spent: Math.min(had + collected, o.doneRequired),
      available, hunting: (p.hunting ?? 1) ? true : false, outstanding: Math.max(0, o.required - available) };
  });
}

/* ---------------------------------------------------------------- helpers */
async function memberTrail(ctx, me) {
  const trail = await repo.trailById(ctx.db, ctx.params.id);
  if (!trail || !(await repo.canAccessPrivateTrail(ctx.db, trail, me.id))) throw notFound('Loot Trail not found.');
  return trail;
}

const qtyInt = (v, field) => {
  if (v === undefined) return undefined;
  if (!Number.isInteger(v) || v < 0 || v > MAX_QTY) throw bad(`Quantities must be whole numbers from 0 to ${MAX_QTY}.`, field);
  return v;
};

async function planById(db, trailId, planId) {
  return db.prepare('SELECT * FROM loot_trail_plans WHERE id = ? AND trail_id = ?').bind(planId, trailId).first();
}

async function planBundle(db, plan) {
  const [enh, req, members, installed, progress] = await Promise.all([
    db.prepare('SELECT upgrade_id, selection, sort_order FROM loot_trail_plan_enhancements WHERE plan_id = ? ORDER BY sort_order').bind(plan.id).all(),
    db.prepare('SELECT stage, upgrade_id, item_key, required_qty, qty_status, sort_order FROM loot_trail_plan_requirements WHERE plan_id = ? ORDER BY sort_order').bind(plan.id).all(),
    db.prepare(`SELECT m.user_id, m.activation, m.activation_completed_at, m.joined_at, u.username, u.display_name
                  FROM loot_trail_plan_members m JOIN users u ON u.id = m.user_id WHERE m.plan_id = ? ORDER BY m.joined_at`).bind(plan.id).all(),
    db.prepare('SELECT user_id, upgrade_id, installed_at FROM loot_trail_plan_installed WHERE plan_id = ?').bind(plan.id).all(),
    db.prepare('SELECT user_id, item_key, had_qty, collected_qty, hunting, updated_at FROM loot_trail_plan_progress WHERE plan_id = ?').bind(plan.id).all(),
  ]);
  return { enh: enh.results || [], req: req.results || [], members: members.results || [], installed: installed.results || [], progress: progress.results || [] };
}

function memberState(b, userId) {
  const m = b.members.find(x => x.user_id === userId);
  if (!m) return null;
  const inst = b.installed.filter(i => i.user_id === userId), prog = b.progress.filter(p => p.user_id === userId);
  return {
    activation: m.activation, activationCompletedAt: m.activation_completed_at, joinedAt: m.joined_at,
    installed: inst.map(i => ({ upgradeId: i.upgrade_id, installedAt: i.installed_at })),
    materials: outstandingFor(b.req, m, inst, prog),
  };
}

function planOutput(plan, b, me, isOwner, creatorName, active = new Set()) {
  const mine = memberState(b, me.id);
  return {
    id: plan.id, kind: plan.kind, title: plan.title, status: plan.status, dataAsOf: plan.data_as_of,
    weaponId: plan.weapon_id, weaponItemId: plan.weapon_item_id, moduleItemId: plan.module_item_id,
    createdAt: plan.created_at, updatedAt: plan.updated_at, createdBy: creatorName, mine: plan.created_by === me.id,
    canArchive: isOwner || plan.created_by === me.id,
    enhancements: b.enh.map(e => ({ upgradeId: e.upgrade_id, selection: e.selection })),
    requirements: b.req.map(r => ({ stage: r.stage, upgradeId: r.upgrade_id, itemKey: r.item_key, requiredQty: r.required_qty, qtyStatus: r.qty_status })),
    me: mine,
    // per-Raider progress: the trail owner sees every member's state, contributors only their own
    ...(isOwner ? { squad: b.members.filter(m => m.user_id === me.id || active.has(m.user_id)).map(m => {
      const st = memberState(b, m.user_id);
      return { username: m.username, displayName: m.display_name, activation: st.activation, installedCount: st.installed.length,
        outstanding: st.materials.reduce((n, x) => n + x.outstanding, 0), unknownQty: st.materials.some(x => x.unknownQty) };
    }) } : {}),
  };
}

async function activeMembers(db, trail) {
  const r = await db.prepare(`SELECT user_id FROM loot_trail_members WHERE trail_id = ? AND status = 'ACCEPTED'`).bind(trail.id).all();
  return new Set([trail.owner_id, ...(r.results || []).map(x => x.user_id)]);
}

async function listOutput(ctx, trail, me) {
  const isOwner = trail.owner_id === me.id, active = isOwner ? await activeMembers(ctx.db, trail) : new Set();
  const plans = (await ctx.db.prepare(`SELECT p.*, u.display_name AS creator_name FROM loot_trail_plans p JOIN users u ON u.id = p.created_by
      WHERE p.trail_id = ? AND p.status <> 'ARCHIVED' ORDER BY p.created_at`).bind(trail.id).all()).results || [];
  const out = [];
  for (const p of plans) out.push(planOutput(p, await planBundle(ctx.db, p), me, isOwner, p.creator_name, active));
  return out;
}

/* ---------------------------------------------------------------- endpoints */
export async function listPlans(ctx) {
  const me = await requireUser(ctx);
  const trail = await memberTrail(ctx, me);
  return json({ plans: await listOutput(ctx, trail, me), maxPlans: MAX_PLANS });
}

/* POST /api/trails/:id/plans  {weaponId, alreadyAmplified, enhancements:[upgradeId], had?:{itemKey:qty}, hunting?:{itemKey:bool}} */
export async function createPlan(ctx) {
  const me = await requireUser(ctx);
  const trail = await memberTrail(ctx, me);
  if (trail.status !== 'ACTIVE') throw notFound('Loot Trail not found.');
  const body = await readJson(ctx.request);
  const amp = await ampReference(ctx.env, ctx.request);

  const weapon = amp.weapons.get(typeof body.weaponId === 'string' ? body.weaponId : '');
  if (!weapon) throw bad('Choose one of the 15 amplifiable weapons.', 'weaponId');
  const tier = amp.tiers.get(weapon.tier);
  if (typeof body.alreadyAmplified !== 'boolean') throw bad('Say whether the weapon is already amplified.', 'alreadyAmplified');
  const chosen = Array.isArray(body.enhancements) ? [...new Set(body.enhancements.filter(x => typeof x === 'string'))] : [];
  if (chosen.length > weapon.upgrades.length || chosen.some(id => !weapon.upgrades.some(u => u.id === id))) {
    throw bad(`Unknown enhancement for the ${weapon.name}.`, 'enhancements');
  }
  const set = closure(weapon, chosen);
  const clash = conflictsIn(weapon, set);
  if (clash.length) {
    const n = id => weapon.upgrades.find(u => u.id === id)?.name || id;
    throw bad(`${n(clash[0][0])} and ${n(clash[0][1])} cannot be active together.`, 'enhancements');
  }
  if (body.alreadyAmplified && !set.size) throw bad('Choose at least one enhancement for an amplified weapon.', 'enhancements');

  const active = await ctx.db.prepare(`SELECT COUNT(*) AS n FROM loot_trail_plans WHERE trail_id = ? AND status <> 'ARCHIVED'`).bind(trail.id).first();
  if (active.n >= MAX_PLANS) throw conflict(`A Loot Trail can hold up to ${MAX_PLANS} plans. Archive one first.`);
  await rateLimit(ctx.db, 'trail-plan:' + me.id, 20, 3600, tooMany);

  const reqs = requirementsFor(tier, weapon, set);
  const keys = new Set(reqs.map(r => r.itemKey));
  const had = body.had && typeof body.had === 'object' ? body.had : {};
  const hunting = body.hunting && typeof body.hunting === 'object' ? body.hunting : {};
  for (const k of Object.keys(had)) { if (!keys.has(k)) throw bad('That material is not part of this plan.', 'had'); qtyInt(had[k], 'had'); }
  for (const k of Object.keys(hunting)) { if (!keys.has(k) || typeof hunting[k] !== 'boolean') throw bad('Invalid material selection.', 'hunting'); }

  const id = randomId('tpl'), now = new Date().toISOString();
  const names = weapon.upgrades.filter(u => chosen.includes(u.id)).map(u => u.name);   // chosen enhancements, in tree order
  const title = (`${weapon.name}${body.alreadyAmplified ? '' : ' amplification'}${names.length ? ' · ' + names.join(' + ') : ''}`).slice(0, 120);
  const ordered = weapon.upgrades.filter(u => set.has(u.id));
  const stmts = [
    ctx.db.prepare(`INSERT INTO loot_trail_plans (id, trail_id, created_by, kind, weapon_id, weapon_item_id, module_item_id, title, status, data_as_of, created_at, updated_at)
                    SELECT ?, ?, ?, 'AMPLIFICATION', ?, ?, ?, ?, 'ACTIVE', ?, ?, ?
                    WHERE (SELECT COUNT(*) FROM loot_trail_plans WHERE trail_id = ? AND status <> 'ARCHIVED') < ?`)
      .bind(id, trail.id, me.id, weapon.id, weapon.itemId, tier.itemId, title, amp.asOf, now, now, trail.id, MAX_PLANS),
    ...ordered.map((u, i) => ctx.db.prepare('INSERT INTO loot_trail_plan_enhancements (plan_id, upgrade_id, selection, sort_order) VALUES (?, ?, ?, ?)')
      .bind(id, u.id, chosen.includes(u.id) ? 'CHOSEN' : 'PREREQUISITE', i)),
    ...reqs.map(r => ctx.db.prepare('INSERT INTO loot_trail_plan_requirements (plan_id, stage, upgrade_id, item_key, required_qty, qty_status, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)')
      .bind(id, r.stage, r.upgradeId, r.itemKey, r.requiredQty, r.qtyStatus, r.sortOrder)),
    ctx.db.prepare('INSERT INTO loot_trail_plan_members (plan_id, user_id, activation, activation_completed_at, joined_at, updated_at) VALUES (?, ?, ?, NULL, ?, ?)')
      .bind(id, me.id, body.alreadyAmplified ? 'NOT_NEEDED' : 'REQUIRED', now, now),
    ...[...keys].map(k => ctx.db.prepare('INSERT INTO loot_trail_plan_progress (plan_id, user_id, item_key, had_qty, collected_qty, hunting, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?)')
      .bind(id, me.id, k, had[k] ?? 0, hunting[k] === false ? 0 : 1, now)),
  ];
  // The first statement only inserts while the trail is under the plan limit; the child rows then fail their
  // foreign key, so the whole batch (one transaction) rolls back on a race.
  try { await ctx.db.batch(stmts); }
  catch (error) {
    if (/FOREIGN KEY/i.test(String(error?.message))) throw conflict(`A Loot Trail can hold up to ${MAX_PLANS} plans. Archive one first.`);
    throw error;
  }
  await repo.touchTrail(ctx.db, trail.id, now);
  const plan = await planById(ctx.db, trail.id, id);
  return json({ plan: planOutput(plan, await planBundle(ctx.db, plan), me, trail.owner_id === me.id, me.display_name, trail.owner_id === me.id ? await activeMembers(ctx.db, trail) : new Set()) }, 201);
}

/* POST /api/trails/:id/plans/:planId/me — my own stage and counts.
   {activation?, install?:{upgradeId, installed}, progress?:[{itemKey, had?, collected?, collectedDelta?, hunting?}]} */
export async function updateMyPlan(ctx) {
  const me = await requireUser(ctx);
  const trail = await memberTrail(ctx, me);
  if (trail.status !== 'ACTIVE') throw notFound('Loot Trail not found.');
  const plan = await planById(ctx.db, trail.id, ctx.params.planId);
  if (!plan || plan.status === 'ARCHIVED') throw notFound('Plan not found.');
  const body = await readJson(ctx.request);
  await rateLimit(ctx.db, 'trail-plan-progress:' + me.id, 600, 3600, tooMany);
  const b = await planBundle(ctx.db, plan);
  const now = new Date().toISOString();
  let mine = b.members.find(m => m.user_id === me.id);
  const stmts = [];

  if (body.activation !== undefined) {
    if (!ACTIVATION.has(body.activation)) throw bad('Activation must be REQUIRED, NOT_NEEDED or COMPLETED.', 'activation');
    if (body.activation === 'REQUIRED' && b.installed.some(i => i.user_id === me.id)) {
      throw conflict('Remove the installed enhancements first: they need an amplified weapon.');
    }
  }
  if (!mine) {   // joining this plan (another squad member's build): they must say where their own weapon stands
    if (body.activation === undefined || body.activation === 'COMPLETED') throw bad('Say whether your weapon is already amplified to join this plan.', 'activation');
    stmts.push(ctx.db.prepare('INSERT OR IGNORE INTO loot_trail_plan_members (plan_id, user_id, activation, activation_completed_at, joined_at, updated_at) VALUES (?, ?, ?, NULL, ?, ?)')
      .bind(plan.id, me.id, body.activation, now, now));
    mine = { activation: body.activation };
  } else if (body.activation !== undefined) {
    stmts.push(ctx.db.prepare('UPDATE loot_trail_plan_members SET activation = ?, activation_completed_at = ?, updated_at = ? WHERE plan_id = ? AND user_id = ?')
      .bind(body.activation, body.activation === 'COMPLETED' ? now : null, now, plan.id, me.id));
    mine = { ...mine, activation: body.activation };
  }

  if (body.install !== undefined) {
    const up = body.install?.upgradeId, on = body.install?.installed;
    if (!b.enh.some(e => e.upgrade_id === up) || typeof on !== 'boolean') throw bad('That enhancement is not part of this plan.', 'install');
    const amp = await ampReference(ctx.env, ctx.request);
    const weapon = amp.weapons.get(plan.weapon_id);
    const mineInst = new Set(b.installed.filter(i => i.user_id === me.id).map(i => i.upgrade_id));
    if (on) {
      if (mine.activation === 'REQUIRED') throw conflict('Mark the amplification activation complete before installing enhancements.');
      const missing = (weapon?.upgrades.find(u => u.id === up)?.requires || []).filter(r => !mineInst.has(r));
      if (missing.length) throw conflict('Install the required enhancement first: ' + missing.map(r => weapon.upgrades.find(u => u.id === r)?.name || r).join(', ') + '.');
      stmts.push(ctx.db.prepare('INSERT OR IGNORE INTO loot_trail_plan_installed (plan_id, user_id, upgrade_id, installed_at) VALUES (?, ?, ?, ?)').bind(plan.id, me.id, up, now));
    } else {
      const dependent = weapon?.upgrades.find(u => mineInst.has(u.id) && (u.requires || []).includes(up));
      if (dependent) throw conflict(`${dependent.name} depends on it; mark that one as not installed first.`);
      stmts.push(ctx.db.prepare('DELETE FROM loot_trail_plan_installed WHERE plan_id = ? AND user_id = ? AND upgrade_id = ?').bind(plan.id, me.id, up));
    }
  }

  if (body.progress !== undefined) {
    if (!Array.isArray(body.progress) || body.progress.length > 40) throw bad('Invalid material update.', 'progress');
    const keys = new Set(b.req.map(r => r.item_key));
    const cur = new Map(b.progress.filter(p => p.user_id === me.id).map(p => [p.item_key, p]));
    if (new Set(body.progress.map(p => p?.itemKey)).size !== body.progress.length) throw bad('Each material can appear only once per update.', 'progress');
    for (const p of body.progress) {
      if (!p || !keys.has(p.itemKey)) throw bad('That material is not part of this plan.', 'progress');
      const c = cur.get(p.itemKey) || { had_qty: 0, collected_qty: 0, hunting: 1 };
      let had = qtyInt(p.had, 'had') ?? c.had_qty, collected = qtyInt(p.collected, 'collected') ?? c.collected_qty;
      if (p.collectedDelta !== undefined) {
        if (!Number.isInteger(p.collectedDelta) || Math.abs(p.collectedDelta) > MAX_QTY) throw bad('Invalid change.', 'collectedDelta');
        collected = Math.min(MAX_QTY, Math.max(0, collected + p.collectedDelta));
      }
      if (p.hunting !== undefined && typeof p.hunting !== 'boolean') throw bad('Invalid material selection.', 'hunting');
      const hunting = p.hunting === undefined ? c.hunting : (p.hunting ? 1 : 0);
      stmts.push(ctx.db.prepare(`INSERT INTO loot_trail_plan_progress (plan_id, user_id, item_key, had_qty, collected_qty, hunting, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT(plan_id, user_id, item_key) DO UPDATE SET had_qty = excluded.had_qty, collected_qty = excluded.collected_qty, hunting = excluded.hunting, updated_at = excluded.updated_at`)
        .bind(plan.id, me.id, p.itemKey, had, collected, hunting, now));
    }
  }

  if (!stmts.length) throw bad('Nothing to update.');
  stmts.push(ctx.db.prepare('UPDATE loot_trail_plans SET updated_at = ? WHERE id = ?').bind(now, plan.id));
  await ctx.db.batch(stmts);
  const fresh = await planById(ctx.db, trail.id, plan.id);
  const creator = await ctx.db.prepare('SELECT display_name FROM users WHERE id = ?').bind(fresh.created_by).first();
  const isOwner = trail.owner_id === me.id;
  return json({ plan: planOutput(fresh, await planBundle(ctx.db, fresh), me, isOwner, creator?.display_name, isOwner ? await activeMembers(ctx.db, trail) : new Set()) });
}

/* POST /api/trails/:id/plans/:planId/status {status: ACTIVE|COMPLETED|ARCHIVED} — trail owner or plan creator. */
export async function setPlanStatus(ctx) {
  const me = await requireUser(ctx);
  const trail = await memberTrail(ctx, me);
  if (trail.status !== 'ACTIVE') throw notFound('Loot Trail not found.');
  const plan = await planById(ctx.db, trail.id, ctx.params.planId);
  if (!plan) throw notFound('Plan not found.');
  await rateLimit(ctx.db, 'trail-plan-status:' + me.id, 60, 3600, tooMany);
  if (trail.owner_id !== me.id && plan.created_by !== me.id) throw forbidden('Only the trail owner or the Raider who made the plan can change it.');
  const body = await readJson(ctx.request);
  if (!['ACTIVE', 'COMPLETED', 'ARCHIVED'].includes(body.status)) throw bad('Status must be ACTIVE, COMPLETED or ARCHIVED.', 'status');
  if (body.status !== 'ARCHIVED' && plan.status === 'ARCHIVED') {
    const active = await ctx.db.prepare(`SELECT COUNT(*) AS n FROM loot_trail_plans WHERE trail_id = ? AND status <> 'ARCHIVED'`).bind(trail.id).first();
    if (active.n >= MAX_PLANS) throw conflict(`A Loot Trail can hold up to ${MAX_PLANS} plans.`);
  }
  const res = await ctx.db.prepare(`UPDATE loot_trail_plans SET status = ?, updated_at = ? WHERE id = ?
      AND (? = 'ARCHIVED' OR status <> 'ARCHIVED' OR (SELECT COUNT(*) FROM loot_trail_plans WHERE trail_id = ? AND status <> 'ARCHIVED') < ?)`)
    .bind(body.status, new Date().toISOString(), plan.id, body.status, trail.id, MAX_PLANS).run();
  if (res.meta?.changes !== 1) throw conflict(`A Loot Trail can hold up to ${MAX_PLANS} plans.`);
  return json({ planId: plan.id, status: body.status });
}
