# The Raider Network — v5.3

**FIND IT. HUNT IT. TRADE IT. EXTRACT.**

An independent ARC Raiders community and intelligence hub covering Loot Intel, Maps, Loot Hunts, the Trade Board, Raider Profiles, Private Messages, Projects, and Routes. The site is built with plain HTML, CSS and vanilla JavaScript. There is no build step and no framework.

> Unofficial fan site. Not affiliated with Embark Studios. Core item data: [RaidTheory/arcraiders-data](https://github.com/RaidTheory/arcraiders-data) (MIT). All artwork is AI-generated concept art and does not show in-game appearance.

## What's new in v5.3 (mobile repair, desktop unchanged)

- **No horizontal page scroll at 390 / 393 / 430 / 768.** `body{overflow-x:hidden}` was removed because it hid overflow instead of fixing it, and the causes were fixed:
  - Loot Intel's dashboard was a sideways carousel on phones; it's now a single stack.
  - Auto-fill grids now use `minmax(min(Npx,100%),1fr)`, so a column can never be wider than its screen.
  - Form fields are 16px on phones. iOS zooms in on smaller fields, which left the page panned sideways.
- **New ≤768px layer:**
  - Maps, hunts, trades, routes and POIs show one card per row. Loot results are 2 per row at tablet width and 1 on phones.
  - Toolbars stack. "Looking For ↔ Available to Offer" stacks with the arrow turned. Perisher's Trade Inventory sits below the listings.
  - Layout children can shrink (`min-width:0`), and there are 44px touch targets.
- **Map touch:** at fit zoom, one-finger swipes scroll the page. Pinch or + zooms, and once zoomed a drag pans the map.
- **`tools/mobile_test.py`:** fails if `scrollWidth > clientWidth`, if anything is clipped past the right edge, if html/body hide overflow, or if the map touch behaviour regresses.

## What's new in v5.2

- **Map-first pages:** the real level map is now the first thing below the hero, with zoom, pan, full screen, a level switcher (Stella Montis has two levels) and the MetaForge overlay drawn on the calibrated map. Each map has its own calibration (see `docs/MAPS.md`). Riven Tides shows its map but keeps the overlay off until it's calibrated.
- **Map ↔ loot:** *View All Loot on This Map* and *Top loot on this map* sections were added. Loot Intel reads `?map=` and shows a clearable map banner. Map cards now have both *Explore Map* and *View Loot*.
- **Database art v2:** a new HUD blueprint card system, higher-fidelity renders for Kinetic Converter, ARC cells and drivers, Sentinel Firing Core, the rectangular Leaper Pulse Unit and others, refreshed key and keycard art, and consistent category fallbacks instead of random images. 18 polished renders were kept. See `ASSET-MANIFEST.md`.
- **Data versioning:** `TRN_DATA_VERSION = "5.2"`. Stored records whose owner isn't Perisher or a locally registered account are discarded (this removes RaiderOne, NightWolf, NomadSix, EchoTrader and similar). Real local data is kept.
- **Stats:** the first stat is now **Founding Raiders: 10**, the pre-launch roster rather than people currently online.

## What's new in v5.1

- **MetaForge map data:** 35,969 community map markers are cached in `data/maps/` (see `docs/METAFORGE-SYNC.md`). Each map page has a **Map Intelligence** panel with a marker plot, filters, search and a linked marker list. The base-map image slot is ready for real image files.
- **Real community data only:** every Trade Board listing and Loot Hunt belongs to **Perisher** (10 of each). All fictional Raiders are gone.
- **Shared trade inventory:** `data/trade-inventory.json` holds 8 real units. Listings can reserve units, but reservations plus completed trades can never exceed what's owned.
- **Launch stats:** Active Raiders 10, Trades Completed 0. Open hunts, open trades, Loot Intel records (581) and maps (6) are counted from the data.
- **Two image modes:** *feature art* (the cinematic renders) is used on the homepage, and *database art* (clean silhouette images in `assets/images/items/db/`) is used for keys, keycards, blueprints and ARC parts in Loot Intel and on item pages.
- **Pendola Pass** is modelled as an incoming map with no data until it ships.

## Deployment notes

- **MetaForge attribution is required** for public projects. It appears on map pages, the Maps page and in the footer.
- **Before enabling monetization, confirm commercial API permission with MetaForge per their API terms.** MetaForge asks paid or monetised projects to contact them first. The current build is the free version with no ads or payments.
- **Demo-mode account claim:** the first local account registered with the Raider name **Perisher** owns the seeded Perisher hunts, listings and inventory. In production, link these records to the real account in Supabase.

## Run locally

```bash
cd the-raider-network-v5
python3 -m http.server 8080
# open http://localhost:8080
```

The pages load JSON from `/data`, so they must be served over HTTP. Opening `index.html` directly from disk shows a "Data could not load" banner.

## Pages

| Page | What it does |
|---|---|
| `index.html` | Dashboard with the hero, global search, Popular Loot Hunts, Featured Route, Trade Board preview, Maps & Quick Access, Map Conditions (demo), Current Projects, Community Stats, and Raider roles |
| `loot.html` | Searchable database of 581 items. Has autocomplete, 7 filters plus 5 toggles, 5 sort orders, five dashboard panels, and deep links (`?q= ?map= ?quest= ?project= ?flag=`) |
| `item.html?id=rotary-encoder` | Item detail rendered from the data, with sections for Where to Find, Recycling/Salvage, Quests and Projects, Crafting, Hunts and Trade interest, Value breakdown, and Sources/confidence |
| `maps.html` | Map browser and the Routes list |
| `map.html?id=stella-montis` | Map detail rendered from the data: hero, gallery, overview, ARC presence, quests, POIs with linked items, most valuable / frequent / project-relevant loot, hunts, trade interest, and routes |
| `projects.html` | Active, Ending Soon and Historical projects with stage requirements linked to Loot Intel. Status is calculated from the project dates |
| `hunts.html` | Loot Hunts using `itemId`/`mapId`/`userId`, with Join, Message Raider and View Item Intel buttons |
| `trade.html` | Trade Board with Looking For, Offering, Open to Offers, Respond, Message and Intel buttons. No payments |
| `messages.html` | Private messages that carry their context (`tradeId`/`huntId`/`itemId`, e.g. "Regarding: Rotary Encoder Trade") |
| `profile.html` | Raider identity, portrait, active, completed and trade lists, and placeholders for reputation and badges |
| `auth.html` | Demo register and login |

## Structure

```
assets/
  site.css            v4 base styles (kept)
  v5.css              v5 component layer and responsive rules
  config.js           DEMO_MODE switch (unchanged)
  js/
    utils.js          helpers, icons, chips, Intel Score bands
    data.js           reference-data loader + TRN.store (localStorage <-> Supabase seam)
    auth.js           session, register/login, profile page
    loot.js           Loot Intel + item detail
    maps.js           map browser, map detail, route cards
    projects.js       projects page + homepage cards
    hunts.js          Loot Hunts
    trades.js         Trade Board
    messages.js       messages with context
    app.js            header/footer, global search, homepage, page router
  images/{branding,heroes,maps,items,raiders,ui}/   156 crops + 3 v4 banners
data/
  items.json projects.json quests.json maps.json routes.json arcs.json workshop.json map-conditions.json
  users.json hunts.json trades.json trade-inventory.json      real community seed data (Perisher)
  maps/*.json                                                MetaForge marker cache + index.json
source-boards/        the 10 original concept boards, unmodified
tools/
  crop_assets.py      boards -> web assets (+ assets/images/manifest.json)
  make_item_art.py    database art (keys, keycards, blueprints, ARC parts) -> assets/images/items/db/*.svg
  sync_metaforge.py   MetaForge API/export -> data/maps/*.json (cached, normalised)
  calibrate_maps.py   per-map MetaForge -> base-map image transforms (control points + least squares)
  build_data.py       snapshot + research.json -> /data
  build_pages.py      shared head/footer -> *.html
  make_manifest.py    -> ASSET-MANIFEST.md
  make_data_status.py -> DATA-STATUS.md
  smoke_test.py       every page, desktop + mobile, errors + overflow (Playwright)
  mobile_test.py      phone/tablet horizontal-overflow regression test (Playwright)
  flow_test.py        54 end-to-end demo-flow checks (Playwright)
  source-data/        raidtheory-snapshot.json (English-only), research.json
```

## Data rules

- Every cross-reference uses shared IDs (`rotary-encoder`, `stella-montis`, `ascending-the-mountain`). Requirement quantities live only in `projects.json` and `quests.json`; items keep ID references only.
- Confidence labels:
  - `OFFICIAL` comes from Embark directly. No record uses it yet.
  - `VERIFIED COMMUNITY` comes from compiled community game data or ARC drop tables.
  - `COMMUNITY REPORT` comes from location guides; their URLs are stored with the record.
  - `UNVERIFIED` means no claim is made.
  - Scores are labelled `NETWORK ESTIMATE`.
- Intel Score weights: 20% rarity, 20% demand, 15% quest, 15% project, 15% recycling or crafting, 10% difficulty, 5% value. Bands: 0–39 Low value, 40–59 Useful, 60–74 Valuable, 75–89 High priority, 90–100 Critical. Scores are calculated ahead of time by `tools/build_data.py`.
- To refresh the data:
  1. `git clone https://github.com/RaidTheory/arcraiders-data /tmp/ard`
  2. `python3 tools/build_data.py --snapshot /tmp/ard`
  3. `python3 tools/build_data.py`
  4. `python3 tools/make_data_status.py`
- See `DATA-STATUS.md` for counts, confidence tiers and the research backlog, and `ASSET-MANIFEST.md` for every image.

## Demo Mode

`assets/config.js` keeps `DEMO_MODE: true`. Accounts, hunts, trades and messages live only in the browser (`trn_users`, `trn_session`, `trn_hunts`, `trn_trades`, `trn_messages`, the same keys as v4). v4 hunts and trades that used free-text item and map names are migrated to IDs automatically on first load. Names that can't be matched are kept as text. There are no fictional Raiders and no auto-replies. When you have no conversations, Messages shows one static example, clearly labelled "EXAMPLE · DEMO CONTENT".

## Testing

```bash
python3 -m http.server 8080 &
pip install playwright        # Chromium required
python3 tools/smoke_test.py   # 20 pages × 2 widths: JS errors, failed requests, horizontal overflow
python3 tools/mobile_test.py  # 18 pages × 390/393/430/768: scrollWidth must equal clientWidth, no clipped content, map touch
python3 tools/flow_test.py    # 54 checks: real-data seed, stats, inventory safeguards, map intelligence, register → hunt → trade → messages with context → profile → login → search/filters
```

## Fair play

The Trade Board coordinates requests only. It has no payments, no real-money trades, and no item escrow. Embark's enforcement policy says trading in-game items for anything of value can lead to enforcement. Review the current rules before launch.
