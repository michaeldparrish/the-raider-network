-- The Raider Network v6.3
-- Increase private Loot Trails screenshot limit from 10 MiB to 20 MiB.
-- Preserve existing image records and database constraints.

CREATE TABLE loot_trail_images_new (
  id TEXT PRIMARY KEY,
  discovery_id TEXT NOT NULL
    REFERENCES loot_trail_discoveries(id) ON DELETE CASCADE,
  image_type TEXT NOT NULL
    CHECK(image_type IN ('MAP_POSITION','LOOT')),
  r2_key TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL
    CHECK(content_type IN ('image/jpeg','image/png','image/webp')),
  size_bytes INTEGER NOT NULL
    CHECK(size_bytes BETWEEN 1 AND 20971520),
  uploaded_by TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  UNIQUE(discovery_id, image_type)
);

INSERT INTO loot_trail_images_new
SELECT * FROM loot_trail_images;

DROP TABLE loot_trail_images;

ALTER TABLE loot_trail_images_new
RENAME TO loot_trail_images;

CREATE INDEX loot_trail_images_discovery_idx
  ON loot_trail_images(discovery_id);
