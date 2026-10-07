-- The Raider Network — D1 schema v1 (v6.0)
-- Apply with:  npx wrangler d1 migrations apply raider-network-db --local   (local dev)
--              npx wrangler d1 migrations apply raider-network-db --remote  (production)
--
-- This database holds USER-GENERATED application data only. Loot Intel, maps and MetaForge
-- caches stay as static JSON in /data. D1 enforces foreign keys by default.
-- Timestamps are ISO-8601 UTC strings (e.g. 2026-10-07T18:54:00.000Z), which sort correctly as text.

-- ---------------------------------------------------------------- users
CREATE TABLE users (
  id            TEXT PRIMARY KEY,                       -- 'usr_' + 24 random hex chars; never reused
  username      TEXT NOT NULL COLLATE NOCASE,           -- public handle, stored lower-case, 3-20 [a-z0-9_]
  display_name  TEXT NOT NULL,                          -- public Raider name
  email         TEXT NOT NULL COLLATE NOCASE,           -- private; never returned by public endpoints
  password_hash TEXT NOT NULL,                          -- 'pbkdf2_sha256$<iterations>$<salt b64>$<hash b64>'
  avatar_url    TEXT,                                   -- site-relative portrait path (validated allow-list)
  region        TEXT,
  platform      TEXT,
  raider_tag    TEXT,                                   -- private in-game tag; only returned to its owner
  role          TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'admin')),
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX users_username_uq ON users (username);
CREATE UNIQUE INDEX users_email_uq    ON users (email);

-- ---------------------------------------------------------------- sessions
-- The browser holds a random 256-bit token in an HttpOnly cookie. Only its SHA-256 hash is stored,
-- so a leaked database copy cannot be used to hijack sessions.
CREATE TABLE sessions (
  id           TEXT PRIMARY KEY,                        -- 'ses_' + random
  user_id      TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  token_hash   TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  expires_at   TEXT NOT NULL,
  last_used_at TEXT NOT NULL,
  user_agent   TEXT
);
CREATE UNIQUE INDEX sessions_token_uq ON sessions (token_hash);
CREATE INDEX sessions_user_idx        ON sessions (user_id);
CREATE INDEX sessions_expiry_idx      ON sessions (expires_at);

-- ---------------------------------------------------------------- trade posts
CREATE TABLE trade_posts (
  id                TEXT PRIMARY KEY,                   -- 'trd_' + random
  user_id           TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  wanted_item_id    TEXT,                               -- Loot Intel item id (validated) or NULL for free text
  wanted_item_name  TEXT NOT NULL,
  wanted_quantity   INTEGER NOT NULL DEFAULT 1 CHECK (wanted_quantity BETWEEN 1 AND 99),
  offered_item_id   TEXT,
  offered_item_name TEXT,
  offered_quantity  INTEGER CHECK (offered_quantity IS NULL OR offered_quantity BETWEEN 1 AND 99),
  open_to_offers    INTEGER NOT NULL DEFAULT 1 CHECK (open_to_offers IN (0, 1)),
  region            TEXT NOT NULL,
  platform          TEXT NOT NULL,
  desired_time      TEXT,
  notes             TEXT,
  status            TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'COMPLETED')),
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  closed_at         TEXT
);
CREATE INDEX trade_posts_status_idx ON trade_posts (status, created_at DESC);
CREATE INDEX trade_posts_user_idx   ON trade_posts (user_id, created_at DESC);

-- ---------------------------------------------------------------- trade offers
CREATE TABLE trade_offers (
  id                TEXT PRIMARY KEY,                   -- 'ofr_' + random
  trade_post_id     TEXT NOT NULL REFERENCES trade_posts (id) ON DELETE CASCADE,
  from_user_id      TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  message           TEXT NOT NULL,
  offered_item_id   TEXT,
  offered_item_name TEXT,
  status            TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'WITHDRAWN')),
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);
CREATE INDEX trade_offers_trade_idx ON trade_offers (trade_post_id, created_at);
CREATE INDEX trade_offers_from_idx  ON trade_offers (from_user_id, created_at);
-- one live (pending) offer per Raider per trade
CREATE UNIQUE INDEX trade_offers_one_pending_uq ON trade_offers (trade_post_id, from_user_id) WHERE status = 'PENDING';

-- ---------------------------------------------------------------- rate limits
-- Fixed-window counters for login / registration / posting. Keys contain a SHA-256 of the client IP,
-- never the raw IP address.
CREATE TABLE rate_limits (
  bucket       TEXT PRIMARY KEY,
  window_start INTEGER NOT NULL,                        -- unix seconds
  count        INTEGER NOT NULL
);
