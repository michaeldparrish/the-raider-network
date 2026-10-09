-- The Raider Network — D1 schema v2 (v6.2): private trade handoffs.
-- ADDITIVE ONLY. Creates two new tables and their indexes. No existing table, column, constraint or row is changed,
-- so v6.1 code keeps working against a migrated database (it simply never reads these tables).
--
-- Apply AFTER a backup and BEFORE deploying v6.2 code:
--   npx wrangler d1 export raider-network-db --remote --output backups/pre-v6.2.sql
--   npx wrangler d1 migrations apply raider-network-db --remote
--
-- "Awaiting Exchange" lives here (trade_handoffs.status) instead of in trade_posts.status, because the CHECK constraint
-- on trade_posts.status (OPEN/CLOSED/COMPLETED) cannot be altered without rebuilding a live table. While a handoff is
-- AWAITING_EXCHANGE the trade row stays OPEN; it becomes COMPLETED only when both participants confirm.

CREATE TABLE trade_handoffs (
  id                         TEXT PRIMARY KEY,                                    -- 'hnd_' + random
  trade_post_id              TEXT NOT NULL REFERENCES trade_posts (id) ON DELETE CASCADE,
  offer_id                   TEXT NOT NULL REFERENCES trade_offers (id) ON DELETE CASCADE,
  owner_id                   TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,  -- trade owner (accepted the offer)
  counterparty_id            TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,  -- Raider whose offer was accepted
  status                     TEXT NOT NULL DEFAULT 'AWAITING_EXCHANGE'
                             CHECK (status IN ('AWAITING_EXCHANGE', 'COMPLETED', 'CANCELLED', 'HISTORICAL')),
  owner_confirmed_at         TEXT,
  counterparty_confirmed_at  TEXT,
  owner_seen_at              TEXT,                                                -- drives the one-time "Trade accepted" banner
  counterparty_seen_at       TEXT,
  cancelled_by               TEXT REFERENCES users (id) ON DELETE SET NULL,
  cancel_reason              TEXT,
  completed_at               TEXT,
  share_ids                  INTEGER NOT NULL DEFAULT 1 CHECK (share_ids IN (0, 1)),  -- HISTORICAL only: may IDs ever be shared? fixed at creation
  created_at                 TEXT NOT NULL,
  updated_at                 TEXT NOT NULL,
  CHECK (owner_id <> counterparty_id)
);
CREATE UNIQUE INDEX trade_handoffs_offer_uq  ON trade_handoffs (offer_id);
-- at most one live handoff per trade (also the final authority if two accepts race)
CREATE UNIQUE INDEX trade_handoffs_active_uq ON trade_handoffs (trade_post_id) WHERE status = 'AWAITING_EXCHANGE';
CREATE INDEX trade_handoffs_owner_idx        ON trade_handoffs (owner_id, updated_at DESC);
CREATE INDEX trade_handoffs_cp_idx           ON trade_handoffs (counterparty_id, updated_at DESC);

-- Reports about an unsuccessful or abusive exchange. Never returned by any public endpoint.
CREATE TABLE trade_reports (
  id           TEXT PRIMARY KEY,                                                  -- 'rpt_' + random
  handoff_id   TEXT NOT NULL REFERENCES trade_handoffs (id),                         -- no cascade: a report can't be erased by deleting
  reporter_id  TEXT NOT NULL REFERENCES users (id),                                  -- the trade or handoff it is about (the API also
  reported_id  TEXT NOT NULL REFERENCES users (id),                                  -- refuses to delete trades that have a handoff)
  reason       TEXT NOT NULL CHECK (reason IN ('no_show', 'did_not_deliver', 'scam_attempt', 'abusive', 'other')),
  details      TEXT,
  status       TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'REVIEWED')),
  created_at   TEXT NOT NULL
);
CREATE UNIQUE INDEX trade_reports_one_per_reporter_uq ON trade_reports (handoff_id, reporter_id);
CREATE INDEX trade_reports_status_idx ON trade_reports (status, created_at DESC);
