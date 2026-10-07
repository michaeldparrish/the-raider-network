# The Raider Network — v6.0

**FIND IT. HUNT IT. TRADE IT. EXTRACT.**

An independent ARC Raiders community and intelligence hub covering Loot Intel, Maps, Loot Hunts, the Trade Board, Raider Profiles, Private Messages, Projects, and Routes. The site is built with plain HTML, CSS and vanilla JavaScript. There is no build step and no framework.

> Unofficial fan site. Not affiliated with Embark Studios. Core item data: [RaidTheory/arcraiders-data](https://github.com/RaidTheory/arcraiders-data) (MIT). All artwork is AI-generated concept art and does not show in-game appearance.

## What's new in v6.0: real accounts and a persistent Trade Board

- **Mobile menu fixed.** The hamburger worked, but the menu drawer had collapsed to about 12 px.
  - **Cause:** `backdrop-filter` on `.site-header` (v5) and on `.topbar` (v4). Each makes its element the containing block for `position:fixed` children, so the drawer's `top:90px; bottom:0` was measured against the 70 px header instead of the screen, and `overflow:auto` clipped every link.
  - **Fix:** the blur now sits on a `::before` layer. The menu also gained `aria-expanded`/label updates, Escape and tap-outside to close, focus handling, 48 px links, and a sign-in/sign-out row.
  - **Test:** `tools/nav_test.py` really opens and uses the menu.
- **Accounts:** register, log in and log out are backed by **Cloudflare Pages Functions + D1**. Accounts use salted PBKDF2 passwords and HttpOnly session cookies. Usernames and emails are unique, and email is never shown publicly.
- **Persistent Trade Board:**
  - Trade posts live in D1, so every visitor and device sees the same board, and posts survive refreshes, cleared browsers and new deployments.
  - Owners can **edit**, **close/reopen**, **mark completed** and **delete** their posts; the server refuses anyone else.
  - **Offers:** other Raiders send offers; owners accept or decline them, and senders can withdraw them (see My Profile → Trade Offers).
- **Environment-based modes.**
  - **Production:** server mode with no DEMO badge.
  - **`python3 -m http.server`:** the old browser-only demo, on localhost only and labelled.
  - **No API on a real domain:** a clear "OFFLINE" state, never a silent fallback.
- **Still browser-only (labelled):** Loot Hunts. Private messaging is switched off in server mode until it moves to the server; offers replace it for trades.
- **Docs:** `docs/CLOUDFLARE-BACKEND-SETUP.md` (step-by-step) and `docs/BACKEND.md` (architecture, schema, API, security).

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
# Full stack: the same as production (accounts + trades in a local D1 database)
npx wrangler d1 migrations apply raider-network-db --local
npx wrangler pages dev .            # http://127.0.0.1:8788

# Static demo only: browser storage, labelled DEMO MODE
python3 -m http.server 8080         # http://localhost:8080
```

To deploy with the database, follow **docs/CLOUDFLARE-BACKEND-SETUP.md**.

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
functions/            Cloudflare Pages Functions (server-side API, /api/*): see docs/BACKEND.md
  api/[[path]].js     entry point
  _lib/               router, session, handlers, validate, security, reference, repo (all SQL)
migrations/           D1 schema (0001_initial.sql)
wrangler.toml         D1 binding "DB" -> raider-network-db (paste your database_id)
_routes.json          only /api/* runs Functions
_headers              security headers + Content-Security-Policy for static pages
seeds/                optional, manual SQL (Perisher's listings: only for an existing account)
assets/
  site.css            v4 base styles (kept)
  v5.css              v5 component layer and responsive rules
  config.js           BACKEND mode: auto | server | demo (no secrets)
  js/
    utils.js          helpers, icons, chips, Intel Score bands
    api.js            /api client + backend-mode detection (server / demo / offline)
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
  mobile_test.py      horizontal-overflow regression test, phone → desktop (Playwright)
  nav_test.py         functional mobile-menu test
  api_test.py         API auth/authorization/offers tests (local D1)
  persistence_test.py browser persistence test across server restarts (local D1)
  devserver.py        starts an isolated wrangler pages dev + throw-away D1 for tests
  make_seed_sql.py    optional Perisher listings SQL (manual)
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

## Server mode and Demo Mode

In production the site runs in **server mode**:

- Accounts, sessions, trade posts and offers live in Cloudflare D1; nothing authoritative is kept in the browser.
- Loot Hunts are still saved in the browser and are labelled as a preview.
- Private messages are disabled until they move to the server.

The rest of this section describes the local **demo mode** (`python3 -m http.server`, localhost only). It keeps the v5 behaviour: Accounts, hunts, trades and messages live only in the browser (`trn_users`, `trn_session`, `trn_hunts`, `trn_trades`, `trn_messages`, the same keys as v4). v4 hunts and trades that used free-text item and map names are migrated to IDs automatically on first load. Names that can't be matched are kept as text. There are no fictional Raiders and no auto-replies. When you have no conversations, Messages shows one static example, clearly labelled "EXAMPLE · DEMO CONTENT".

## Testing

```bash
python3 -m http.server 8080 &
pip install playwright        # Chromium required
python3 tools/smoke_test.py   # 20 pages × 2 widths: JS errors, failed requests, horizontal overflow  (add --base URL for another server)
python3 tools/nav_test.py     # mobile menu really opens/closes/navigates at 390/393/430/768 + desktop
python3 tools/api_test.py         # 89 API checks: auth, authorization, offers, validation, CSRF, rate limits (own throw-away D1)
python3 tools/persistence_test.py # 30 browser checks: register, post, server restart, fresh browsers, multi-user (own throw-away D1)
python3 tools/mobile_test.py  # 18 pages × 390/393/430/768/1440/1920: scrollWidth must equal clientWidth, no clipped content, map touch
python3 tools/flow_test.py    # 54 checks: real-data seed, stats, inventory safeguards, map intelligence, register → hunt → trade → messages with context → profile → login → search/filters
```

## Fair play

The Trade Board coordinates requests only. It has no payments, no real-money trades, and no item escrow. Embark's enforcement policy says trading in-game items for anything of value can lead to enforcement. Review the current rules before launch.
