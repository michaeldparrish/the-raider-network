-- The Raider Network v6.3 — Loot Trails
-- Additive schema. Does not alter existing v6.2 tables.
-- Apply locally and test before any remote migration.
-- All timestamps are ISO-8601 UTC text.
-- All private access rules MUST also be enforced by API handlers.

CREATE TABLE loot_trails (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id),
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
  description TEXT NOT NULL DEFAULT '',
  map_id TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'PRIVATE'
    CHECK(visibility IN ('PRIVATE','PUBLIC')),
  status TEXT NOT NULL DEFAULT 'ACTIVE'
    CHECK(status IN ('ACTIVE','ARCHIVED')),
  published_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX loot_trails_owner_idx
  ON loot_trails(owner_id, updated_at DESC);
CREATE INDEX loot_trails_public_idx
  ON loot_trails(visibility, status, published_at DESC);

CREATE TABLE loot_trail_members (
  trail_id TEXT NOT NULL
    REFERENCES loot_trails(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL
    REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'CONTRIBUTOR'
    CHECK(role IN ('OWNER','CONTRIBUTOR')),
  status TEXT NOT NULL DEFAULT 'INVITED'
    CHECK(status IN ('INVITED','ACCEPTED','DECLINED','REMOVED')),
  invited_by TEXT REFERENCES users(id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(trail_id, user_id)
);
CREATE INDEX loot_trail_members_user_idx
  ON loot_trail_members(user_id, status);

CREATE TABLE loot_trail_sessions (
  id TEXT PRIMARY KEY,
  trail_id TEXT NOT NULL
    REFERENCES loot_trails(id) ON DELETE CASCADE,
  created_by TEXT NOT NULL REFERENCES users(id),
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
  notes TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL,
  ended_at TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX loot_trail_sessions_trail_idx
  ON loot_trail_sessions(trail_id, started_at DESC);

CREATE TABLE loot_trail_discoveries (
  id TEXT PRIMARY KEY,
  trail_id TEXT NOT NULL
    REFERENCES loot_trails(id) ON DELETE CASCADE,
  session_id TEXT NOT NULL
    REFERENCES loot_trail_sessions(id),
  created_by TEXT NOT NULL REFERENCES users(id),
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
  item_id TEXT,
  notes TEXT NOT NULL DEFAULT '',
  map_level TEXT NOT NULL,
  x_normalized REAL NOT NULL
    CHECK(x_normalized BETWEEN 0 AND 1),
  y_normalized REAL NOT NULL
    CHECK(y_normalized BETWEEN 0 AND 1),
  review_status TEXT NOT NULL DEFAULT 'PENDING'
    CHECK(review_status IN ('PENDING','APPROVED','REJECTED')),
  is_public INTEGER NOT NULL DEFAULT 0
    CHECK(is_public IN (0,1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX loot_trail_discoveries_trail_idx
  ON loot_trail_discoveries(trail_id, sort_order, created_at);
CREATE INDEX loot_trail_discoveries_public_idx
  ON loot_trail_discoveries(trail_id, is_public, review_status);

CREATE TABLE loot_trail_images (
  id TEXT PRIMARY KEY,
  discovery_id TEXT NOT NULL
    REFERENCES loot_trail_discoveries(id) ON DELETE CASCADE,
  image_type TEXT NOT NULL
    CHECK(image_type IN ('MAP_POSITION','LOOT')),
  r2_key TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL
    CHECK(content_type IN ('image/jpeg','image/png','image/webp')),
  size_bytes INTEGER NOT NULL
    CHECK(size_bytes BETWEEN 1 AND 10485760),
  uploaded_by TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  UNIQUE(discovery_id, image_type)
);
CREATE INDEX loot_trail_images_discovery_idx
  ON loot_trail_images(discovery_id);

CREATE TABLE loot_trail_progress (
  trail_id TEXT NOT NULL
    REFERENCES loot_trails(id) ON DELETE CASCADE,
  discovery_id TEXT NOT NULL
    REFERENCES loot_trail_discoveries(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  completed_at TEXT NOT NULL,
  PRIMARY KEY(discovery_id, user_id)
);
CREATE INDEX loot_trail_progress_user_idx
  ON loot_trail_progress(user_id, trail_id);
