-- The Raider Network v6.4 — Loot Trail amplification plans (multi-material hunting).
-- Additive only: new tables, no change to any existing table or row.
-- Requirement rows are calculated by the API from the published data/amplification.json,
-- never taken from the browser. Access rules are enforced by the API handlers (trail members only).
-- Rollback: DROP the six tables below (no other table references them).

-- One weapon build inside a Loot Trail ("Burletta · Sprint Shooting + Full-Auto").
CREATE TABLE loot_trail_plans (
  id TEXT PRIMARY KEY,
  trail_id TEXT NOT NULL REFERENCES loot_trails(id) ON DELETE CASCADE,
  created_by TEXT NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL DEFAULT 'AMPLIFICATION' CHECK(kind IN ('AMPLIFICATION')),
  weapon_id TEXT NOT NULL CHECK(length(weapon_id) BETWEEN 1 AND 64),
  weapon_item_id TEXT NOT NULL CHECK(length(weapon_item_id) BETWEEN 1 AND 100),
  module_item_id TEXT NOT NULL CHECK(length(module_item_id) BETWEEN 1 AND 100),
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','COMPLETED','ARCHIVED')),
  data_as_of TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX loot_trail_plans_trail_idx ON loot_trail_plans(trail_id, status, created_at);

-- Enhancements in the build: chosen by the Raider, or added because a chosen one requires them.
CREATE TABLE loot_trail_plan_enhancements (
  plan_id TEXT NOT NULL REFERENCES loot_trail_plans(id) ON DELETE CASCADE,
  upgrade_id TEXT NOT NULL CHECK(length(upgrade_id) BETWEEN 1 AND 64),
  selection TEXT NOT NULL CHECK(selection IN ('CHOSEN','PREREQUISITE')),
  sort_order INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(plan_id, upgrade_id)
);

-- Quantity snapshot per stage, calculated server-side when the plan is created.
-- stage ACTIVATION: the module (upgrade_id is ''); ENHANCEMENT: install cost; RESEARCH: research parts.
-- item_key is a Loot Intel item id, or 'label:<name>' for a research part not yet in the catalog.
CREATE TABLE loot_trail_plan_requirements (
  plan_id TEXT NOT NULL REFERENCES loot_trail_plans(id) ON DELETE CASCADE,
  stage TEXT NOT NULL CHECK(stage IN ('ACTIVATION','ENHANCEMENT','RESEARCH')),
  upgrade_id TEXT NOT NULL DEFAULT '',
  item_key TEXT NOT NULL CHECK(length(item_key) BETWEEN 1 AND 120),
  required_qty INTEGER CHECK(required_qty IS NULL OR required_qty BETWEEN 1 AND 999),
  qty_status TEXT NOT NULL CHECK(qty_status IN ('CONFIRMED','REPORTED','CONFLICT','UNVERIFIED')),
  sort_order INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(plan_id, stage, upgrade_id, item_key)
);

-- Each Raider's own stage for the build (per-Raider progress; the trail owner can see everyone's).
CREATE TABLE loot_trail_plan_members (
  plan_id TEXT NOT NULL REFERENCES loot_trail_plans(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  activation TEXT NOT NULL CHECK(activation IN ('REQUIRED','NOT_NEEDED','COMPLETED')),
  activation_completed_at TEXT,
  joined_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(plan_id, user_id)
);

-- Enhancements a Raider has installed on their weapon (their materials stop counting as outstanding).
CREATE TABLE loot_trail_plan_installed (
  plan_id TEXT NOT NULL REFERENCES loot_trail_plans(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  upgrade_id TEXT NOT NULL CHECK(length(upgrade_id) BETWEEN 1 AND 64),
  installed_at TEXT NOT NULL,
  PRIMARY KEY(plan_id, user_id, upgrade_id)
);

-- Each Raider's materials: what they already had, what they have collected since, and whether they are hunting it.
-- Counts are never reset by stage changes, so marking a stage complete keeps the collection history.
CREATE TABLE loot_trail_plan_progress (
  plan_id TEXT NOT NULL REFERENCES loot_trail_plans(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_key TEXT NOT NULL CHECK(length(item_key) BETWEEN 1 AND 120),
  had_qty INTEGER NOT NULL DEFAULT 0 CHECK(had_qty BETWEEN 0 AND 999),
  collected_qty INTEGER NOT NULL DEFAULT 0 CHECK(collected_qty BETWEEN 0 AND 999),
  hunting INTEGER NOT NULL DEFAULT 1 CHECK(hunting IN (0,1)),
  updated_at TEXT NOT NULL,
  PRIMARY KEY(plan_id, user_id, item_key)
);
CREATE INDEX loot_trail_plan_progress_user_idx ON loot_trail_plan_progress(user_id, plan_id);
