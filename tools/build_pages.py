"""Generate the v6 HTML pages from one shared head/scripts template. Run: python3 tools/build_pages.py
Page bodies live in this file; header/footer markup is injected at runtime by assets/js/app.js."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#071014">
<link rel="icon" href="assets/images/branding/raider-network-mark-small.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
<link rel="stylesheet" href="assets/v5.css">
</head>
<body data-page="{page}">
<a class="skip-link" href="#main">Skip to content</a>
<header id="siteHeader" class="site-header"></header>
<main id="main">
'''
FOOT = '''
</main>
<footer id="siteFooter" class="site-footer"></footer>
<script defer src="assets/config.js"></script>
<script defer src="assets/js/utils.js"></script>
<script defer src="assets/js/api.js"></script>
<script defer src="assets/js/data.js"></script>
<script defer src="assets/js/auth.js"></script>
<script defer src="assets/js/loot.js"></script>
<script defer src="assets/js/maps.js"></script>
<script defer src="assets/js/projects.js"></script>
<script defer src="assets/js/hunts.js"></script>
<script defer src="assets/js/trades.js"></script>
<script defer src="assets/js/messages.js"></script>
<script defer src="assets/js/handoff.js"></script>
<script defer src="assets/js/app.js"></script>
</body>
</html>
'''
I = lambda n: f'<img class="ico" src="assets/images/ui/icon-{n}.png" alt="" aria-hidden="true">'
SEARCH_SVG = '<svg class="svg-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>'

PAGES = {}

PAGES['index.html'] = ('home', 'The Raider Network — ARC Raiders Loot Intel, Maps, Hunts & Trading', 'Independent ARC Raiders community and intelligence hub: loot intel, map guides, loot hunts, trade board and Raider connections.', f'''
<section class="home-hero">
  <div class="home-hero__art"><img src="assets/images/heroes/home-hero-overlook.webp" alt="A Raider overlooking a ruined city beneath a giant ring structure at sunset"></div>
  <div class="home-hero__shade"></div>
  <div class="home-hero__inner">
    <div class="home-hero__copy">
      <span class="eyebrow">THE RAIDER NETWORK</span>
      <h1>Find it. <span>Hunt it.</span><br>Trade it. <span class="teal">Extract.</span></h1>
      <p>Loot intelligence, map guides, Raider connections, community hunts, and extraction knowledge.</p>
      <form class="hero-search" id="homeSearchForm" role="search">
        {SEARCH_SVG}
        <input id="homeSearch" autocomplete="off" placeholder="What are you looking for, Raider?" aria-label="Search items, maps, projects and quests">
        <button class="btn btn-primary" type="submit">Search Loot</button>
      </form>
      <div class="hero-actions"><a class="btn btn-primary btn-lg" href="loot.html">{SEARCH_SVG} Search Loot</a><a class="btn btn-ghost btn-lg" href="hunts.html">{I('squad')} Browse Hunts</a></div>
      <div class="hero-metrics"><div><strong id="statItemsHero">—</strong><span>Item records</span></div><div><strong id="statHuntsHero">—</strong><span>Open hunts</span></div><div><strong id="statTradesHero">—</strong><span>Trade requests</span></div><div><strong>6</strong><span>Maps</span></div></div>
    </div>
    <nav class="hero-quick" aria-label="Quick access">
      <a href="loot.html">{I('loot-intel')}<span><strong>Loot Intel</strong><small>Know what to keep</small></span></a>
      <a href="maps.html#routes">{I('route')}<span><strong>Map Routes</strong><small>Plan smarter runs</small></span></a>
      <a href="trade.html">{I('trade')}<span><strong>Trade Board</strong><small>Find what you need</small></span></a>
      <a href="hunts.html">{I('squad')}<span><strong>Loot Hunts</strong><small>Squad up by objective</small></span></a>
    </nav>
  </div>
</section>

<div class="dashboard">
  <section class="dash-card dash-popular" aria-labelledby="hPopular">
    <header class="dash-head"><h2 id="hPopular"><i></i>Popular Loot Hunts</h2><a href="loot.html">View all {'<svg class="svg-ico" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'}</a></header>
    <div class="item-grid item-grid--4" id="popularLoot"></div>
  </section>
  <section class="dash-card dash-route" aria-labelledby="hRoute">
    <header class="dash-head"><h2 id="hRoute"><i></i>Featured Route</h2><a href="maps.html#routes">All routes</a></header>
    <div id="featuredRoute"></div>
  </section>
  <section class="dash-card dash-trades" aria-labelledby="hTrades">
    <header class="dash-head"><h2 id="hTrades"><i></i>Trade Board</h2><a href="trade.html">View all</a></header>
    <div id="homeTrades" class="trade-rows"></div>
    <a class="btn btn-outline btn-block" href="trade.html">{I('trade')} Browse Trades</a>
  </section>
  <section class="dash-card dash-maps" aria-labelledby="hMaps">
    <header class="dash-head"><h2 id="hMaps"><i></i>Maps &amp; Quick Access</h2><a href="maps.html">View all maps</a></header>
    <div class="map-grid map-grid--6" id="homeMaps"></div>
  </section>
  <section class="dash-card dash-conditions" id="conditions" aria-labelledby="hCond">
    <header class="dash-head"><h2 id="hCond"><i></i>Map Conditions</h2><span class="demo-pill">DEMO FEED</span></header>
    <div id="homeConditions" class="cond-list"></div>
    <div class="cond-foot"><img src="assets/images/raiders/gear-comms-dish.webp" alt=""><p class="small-note">Placeholder schedule. Condition names come from community data; a live feed is planned.</p></div>
  </section>
  <section class="dash-card dash-projects" aria-labelledby="hProj">
    <header class="dash-head"><h2 id="hProj"><i></i>Current Projects</h2><a href="projects.html">All projects</a></header>
    <div id="homeProjects" class="project-mini-grid"></div>
  </section>
  <section class="dash-card dash-stats" aria-labelledby="hStats">
    <header class="dash-head"><h2 id="hStats"><i></i>Community Stats</h2></header>
    <div id="homeStats" class="stat-grid"></div>
  </section>
  <section class="dash-card dash-roles" aria-labelledby="hRoles">
    <header class="dash-head"><h2 id="hRoles"><i></i>Different Skills. Same Extraction.</h2><a href="hunts.html">Find a squad</a></header>
    <div class="role-strip">
      <a href="hunts.html" class="role-card"><img src="assets/images/raiders/raider-solo-scout.webp" alt="" loading="lazy"><span><strong>Solo Scout</strong><small>Recon &amp; intel</small></span></a>
      <a href="hunts.html" class="role-card"><img src="assets/images/raiders/raider-heavy-looter.webp" alt="" loading="lazy"><span><strong>Heavy Looter</strong><small>Salvage &amp; supply</small></span></a>
      <a href="hunts.html" class="role-card"><img src="assets/images/raiders/raider-tech-specialist.webp" alt="" loading="lazy"><span><strong>Tech Specialist</strong><small>Tools &amp; systems</small></span></a>
      <a href="hunts.html" class="role-card"><img src="assets/images/raiders/raider-mountain-runner.webp" alt="" loading="lazy"><span><strong>Mountain Runner</strong><small>Mobility &amp; access</small></span></a>
      <a href="hunts.html" class="role-card"><img src="assets/images/raiders/raider-medic-support.webp" alt="" loading="lazy"><span><strong>Medic / Support</strong><small>Heal &amp; sustain</small></span></a>
      <a href="hunts.html" class="role-card"><img src="assets/images/raiders/raider-stealth-raider.webp" alt="" loading="lazy"><span><strong>Stealth Raider</strong><small>Infiltration</small></span></a>
    </div>
  </section>
</div>

<section class="feature-band feature-band--v5">
  <img src="assets/images/raiders/raider-squad-lineup.webp" alt="A squad of three Raiders in front of a ruined city">
  <div>
    <span class="eyebrow">A DIFFERENT KIND OF LFG</span>
    <h2>Start with the loot.</h2>
    <p>Instead of posting “LFG” into a flood of messages, tell the network what you are hunting, where you want to run, and when you are available.</p>
    <ol class="steps-inline"><li><b>01</b> Search the item</li><li><b>02</b> Join or post a hunt</li><li><b>03</b> Coordinate privately</li></ol>
    <a class="btn btn-primary" href="hunts.html?new=">Start a Loot Hunt</a>
  </div>
</section>
''')

PAGES['loot.html'] = ('loot', 'Loot Intel — The Raider Network', 'Search every ARC Raiders item: where to find it, recycle outputs, quest and project uses, and the Raider Network Intel Score.', f'''
<section class="page-banner page-banner--intel">
  <img src="assets/images/heroes/hero-overlook.webp" alt="">
  <div class="page-banner__shade"></div>
  <div class="page-banner__copy">
    <span class="eyebrow">{I('loot-intel')} RAIDER INTELLIGENCE</span>
    <h1>Loot Intel</h1>
    <p>Know what to keep. Know where to hunt. Search locations, recycle outputs, quest and project uses, and a Raider Network value score for every item.</p>
    <form class="hero-search" id="lootSearchForm" role="search">{SEARCH_SVG}<input id="lootSearch" autocomplete="off" placeholder="Search Rotary Encoder, Ion Sputter, Magnetron…" aria-label="Search items"><button class="btn btn-primary">Search Intel</button></form>
    <div class="banner-stats"><span><b id="statRecords">—</b> item records</span><span><b id="statLocated">—</b> with map data</span><span><b id="statProjects">—</b> project items</span><span><b id="statQuests">—</b> quest items</span></div>
  </div>
  <div class="banner-art-strip"><img src="assets/images/items/rotary-encoder.webp" alt=""><img src="assets/images/items/ion-sputter.webp" alt=""><img src="assets/images/items/queen-reactor.webp" alt=""><img src="assets/images/items/magnetron.webp" alt=""></div>
</section>
<div class="page-shell">
  <div class="loot-dash" id="lootDash"></div>
  <section class="db-section">
    <div class="db-toolbar">
      <div><div id="mapBanner"></div><span class="eyebrow">ITEM DATABASE</span><h2>Search results</h2><p class="muted" id="resultCount"></p><div id="activeContext" class="ctx-row"></div></div>
      <button class="btn btn-ghost filter-toggle" id="filterToggle">{I('filter')} Filters</button>
    </div>
    <div class="filter-bar" id="filterBar">
      <label>{I('rarity')}<select id="rarityFilter" aria-label="Rarity"><option value="">All rarities</option><option>Common</option><option>Uncommon</option><option>Rare</option><option>Epic</option><option>Legendary</option></select></label>
      <label>{I('inventory')}<select id="categoryFilter" aria-label="Category"></select></label>
      <label>{I('loot-intel')}<select id="groupFilter" aria-label="Item group"></select></label>
      <label>{I('map')}<select id="mapFilter" aria-label="Map"></select></label>
      <label>{I('value')}<select id="demandFilter" aria-label="Demand"><option value="">Any demand</option><option>Very High</option><option>High</option><option>Normal</option><option>Low</option></select></label>
      <label>{I('difficulty')}<select id="difficultyFilter" aria-label="Difficulty"><option value="">Any difficulty</option><option>Extreme</option><option>Very Hard</option><option>Hard</option><option>Moderate</option><option>Easy</option></select></label>
      <label>{I('sort')}<select id="sortBy" aria-label="Sort"><option value="intel">Sort: Intel Score</option><option value="demand">Sort: Demand</option><option value="rarity">Sort: Rarity</option><option value="value">Sort: Merchant value</option><option value="alpha">Sort: A–Z</option></select></label>
      <div class="flag-row">
        <label class="flag-toggle"><input type="checkbox" value="project"><span>{I('project')}Project item</span></label>
        <label class="flag-toggle"><input type="checkbox" value="quest"><span>{I('route')}Quest item</span></label>
        <label class="flag-toggle"><input type="checkbox" value="crafting"><span>{I('crafting')}Crafting item</span></label>
        <label class="flag-toggle"><input type="checkbox" value="recyclable"><span>{I('recycle')}Recyclable</span></label>
        <label class="flag-toggle"><input type="checkbox" value="located"><span>{I('location')}Has map data</span></label>
        <button class="text-btn" id="resetFilters" type="button">Reset</button>
      </div>
    </div>
    <div class="item-grid" id="lootResults"></div>
    <div class="center"><button class="btn btn-outline hidden" id="loadMore">Show more</button></div>
    <p class="data-footnote"><span id="dataAsOf"></span> · Core facts: VERIFIED COMMUNITY · Locations labelled per record · Scores: NETWORK ESTIMATE · Artwork is concept art, not game data.</p>
  </section>
</div>
''')

PAGES['item.html'] = ('item', 'Item Intel — The Raider Network', 'ARC Raiders item intel: where to find it, recycling, quests, projects and value.', '''
<div id="itemRoot"><div class="page-shell"><div class="skeleton-hero"></div></div></div>
''')

PAGES['maps.html'] = ('maps', 'Maps — The Raider Network', 'ARC Raiders map browser with points of interest, linked loot intel, active hunts and routes.', f'''
<section class="page-banner page-banner--maps">
  <img src="assets/images/heroes/raider-network-skyline.webp" alt="">
  <div class="page-banner__shade"></div>
  <div class="page-banner__copy"><span class="eyebrow">{I('map')} WORLD LOCATIONS</span><h1>Maps</h1><p>Different worlds, higher stakes. <b id="mapCount">6</b> maps with points of interest, linked Loot Intel, active hunts and routes.</p></div>
</section>
<div class="page-shell">
  <p class="mf-attr maps-attr">{I('location')} Map data sourced in part from <a href="https://metaforge.app/arc-raiders" target="_blank" rel="noopener">MetaForge</a> community data — cached locally by <code>tools/sync_metaforge.py</code>; map pages never call the API live.</p>
  <div class="map-grid map-grid--browse" id="mapGrid"></div>
  <section class="block" id="routes">
    <div class="section-title-row"><div><span class="eyebrow">{I('route')} ROUTES &amp; GUIDES</span><h2>Routes</h2><p class="muted">Editorial demo routes for v5. Ratings are Raider Network estimates; community route submissions are planned.</p></div></div>
    <div class="route-list" id="routeList"></div>
  </section>
</div>
''')

PAGES['map.html'] = ('map', 'Map — The Raider Network', 'ARC Raiders map detail: POIs, loot, hunts, trade interest and routes.', '''
<div id="mapRoot"><div class="page-shell"><div class="skeleton-hero"></div></div></div>
''')

PAGES['projects.html'] = ('projects', 'Projects — The Raider Network', 'Active, ending-soon and historical ARC Raiders projects with required items linked to Loot Intel.', f'''
<section class="page-banner page-banner--projects">
  <img src="assets/images/heroes/ring-city-strip.webp" alt="">
  <div class="page-banner__shade"></div>
  <div class="page-banner__copy"><span class="eyebrow">{I('project')} PROJECT WATCH</span><h1>Projects &amp; current item demand</h1><p>Every project stays searchable after it ends, because old requirements reveal recurring high-value loot. Status is calculated from the project dates.</p></div>
  <img class="banner-side-art" src="assets/images/raiders/raider-engineer.webp" alt="">
</section>
<div class="page-shell">
  <div class="tab-row">
    <button class="tab-btn active" data-status="">All <b>0</b></button>
    <button class="tab-btn" data-status="ACTIVE">Active <b>0</b></button>
    <button class="tab-btn" data-status="ENDING SOON">Ending Soon <b>0</b></button>
    <button class="tab-btn" data-status="HISTORICAL">Historical <b>0</b></button>
    <div class="search-field">{SEARCH_SVG}<input id="projectSearch" class="input" placeholder="Search projects or required items…" aria-label="Search projects"></div>
  </div>
  <div id="projectList" class="project-list"></div>
</div>
''')

PAGES['hunts.html'] = ('hunts', 'Loot Hunts — The Raider Network', 'Find Raiders chasing the same ARC Raiders item and coordinate the run privately.', f'''
<section class="page-banner page-banner--hunts">
  <img src="assets/images/heroes/loot-hunt-squad.webp" alt="">
  <div class="page-banner__shade"></div>
  <div class="page-banner__copy"><span class="eyebrow">{I('squad')} COMMUNITY RUN BOARD</span><h1>Loot Hunts</h1><p>Find Raiders chasing the same item or objective, then coordinate the run through private messages.</p>
    <div class="btn-row"><button class="btn btn-primary btn-lg" id="openHuntModal">+ Start a Loot Hunt</button></div>
    <div class="banner-stats"><span><b id="statOpenHunts">—</b> open hunts</span><span><b id="statSlots">—</b> open squad slots</span><span><b id="statHuntItems">—</b> items targeted</span></div></div>
  <img class="banner-side-art" src="assets/images/raiders/raider-squad-lineup.webp" alt="">
</section>
<div class="page-shell">
  <div class="notice-bar hidden" id="huntsNotice" role="note"></div>
  <section class="toolbar hunts-toolbar">
    <div class="search-wrap">{SEARCH_SVG}<input id="huntSearch" class="input" placeholder="Search items, maps, or Raider names" aria-label="Search hunts"></div>
    <select id="mapFilter" class="input" aria-label="Map"></select>
    <select id="regionFilter" class="input" aria-label="Region"></select>
    <select id="platformFilter" class="input" aria-label="Platform"></select>
    <select id="statusFilter" class="input" aria-label="Status"><option value="">Any status</option><option value="open" selected>Open</option><option value="full">Full</option><option value="completed">Completed</option></select>
  </section>
  <p class="muted" id="itemFilterNote"></p>
  <p class="result-line"><b id="huntCount">0</b> hunts shown</p>
  <section id="huntGrid" class="hunt-grid"></section>
  <div id="huntEmpty" class="empty-state hidden"><img src="assets/images/raiders/gear-rusher-helmet.webp" alt="" class="empty-art"><strong>No hunts match.</strong><span>Start the first one for this objective.</span></div>
</div>
<div class="modal hidden" id="huntModal" role="dialog" aria-modal="true" aria-labelledby="huntModalTitle"><div class="modal-card">
  <button class="modal-close" id="closeHuntModal" aria-label="Close">×</button>
  <span class="eyebrow">NEW HUNT</span><h2 id="huntModalTitle">Start a Loot Hunt</h2>
  <form id="huntForm" class="form-grid">
    <label class="full">What are you hunting?<input class="input" name="itemName" list="itemNames" required maxlength="100" placeholder="Start typing — e.g. Rotary Encoder" autocomplete="off"></label>
    <datalist id="itemNames"></datalist>
    <div class="full item-preview" id="huntItemPreview"></div>
    <label>Map<select class="input" name="mapId" required></select></label>
    <label>Desired time<input class="input" name="desiredTime" maxlength="80" placeholder="Tonight after 8 PM"></label>
    <label>Region<select class="input" name="region" required></select></label>
    <label>Platform<select class="input" name="platform" required></select></label>
    <label>Squad size<select class="input" name="squadSize"><option value="2">2 Raiders</option><option value="3" selected>3 Raiders</option></select></label>
    <label class="full">Hunt notes<textarea class="input" name="description" rows="3" maxlength="500" placeholder="Route, experience level, mic preference, timing…"></textarea></label>
    <button class="btn btn-primary full" type="submit">Publish Loot Hunt</button>
    <p class="form-note full" id="huntFormMsg" role="status"></p>
  </form>
</div></div>
''')

PAGES['trade.html'] = ('trade', 'Trade Board — The Raider Network', 'Post what you are looking for in ARC Raiders, list possible offers, and respond privately. No payments.', f'''
<section class="page-banner trade-banner">
  <img src="assets/images/heroes/community-bunker.webp" alt="">
  <div class="page-banner__shade"></div>
  <div class="page-banner__copy"><span class="eyebrow">{I('trade')} COMMUNITY BOARD</span><h1>Trade Board</h1><p>Post what you are looking for, list what you might offer, or invite Raiders to message you with an offer.</p>
    <div class="btn-row"><button class="btn btn-primary btn-lg" id="openTradeModal">+ Post a Trade Request</button></div>
    <div class="banner-stats"><span><b id="statOpenTrades">—</b> open requests</span><span><b id="statOpenOffers">—</b> open to offers</span><span><b id="statCompleted">0</b> trades completed</span></div></div>
  <img class="banner-side-art" src="assets/images/raiders/raider-veteran-trader.webp" alt="">
</section>
<div class="page-shell trade-layout">
  <div>
    <div class="notice-bar hidden" id="tradeNotice" role="note"></div>
    <div class="policy-warning">{I('warning')}<div><strong>Fair-play notice:</strong> Embark currently states that trading in-game items for anything of value, whether real money or otherwise, may result in enforcement. The Raider Network does not process payments, allows no real-money trades, and does not guarantee that any proposed item transfer is permitted.</div></div>
    <div class="toolbar hunts-toolbar trade-toolbar">
      <div class="search-wrap">{SEARCH_SVG}<input class="input" id="tradeSearch" placeholder="Search wanted items, offered items, or Raider names" aria-label="Search trades"></div>
      <select class="input" id="tradeRegion" aria-label="Region"></select>
      <select class="input" id="tradePlatform" aria-label="Platform"></select>
      <select class="input" id="tradeStatus" aria-label="Status"><option value="open" selected>Open</option><option value="closed">Closed</option><option value="completed">Completed</option><option value="">Any status</option></select>
    </div>
    <p class="muted" id="tradeFilterNote"></p>
    <p class="result-line"><b id="tradeCount">0</b> requests shown</p>
    <div class="trade-request-grid" id="tradeRequestGrid"></div>
    <div id="tradeEmpty" class="empty-state hidden"><img src="assets/images/raiders/gear-rusher-knife.webp" alt="" class="empty-art"><strong>No requests match.</strong></div>
  </div>
  <aside class="trade-side-col">
    <div id="inventoryPanels"></div>
    <section class="panel"><header class="panel-head"><span class="eyebrow">{I('value')} MOST WANTED</span></header><div class="mini-list" id="mostWanted"></div></section>
    <section class="panel side-art"><img src="assets/images/raiders/gear-trader-coins.webp" alt=""><div><strong>Deals keep us moving.</strong><p>Agree terms in private messages. Share your Raider tag only when you're ready.</p></div></section>
  </aside>
</div>
<div class="modal hidden" id="tradeModal" role="dialog" aria-modal="true" aria-labelledby="tradeModalTitle"><div class="modal-card">
  <button class="modal-close" id="closeTradeModal" aria-label="Close">×</button>
  <span class="eyebrow" id="tradeModalEyebrow">NEW REQUEST</span><h2 id="tradeModalTitle">Post a trade request</h2>
  <form id="tradeForm" class="form-grid">
    <label>Looking for<input class="input" name="want" list="tradeItemNames" required placeholder="e.g. Rotary Encoder" autocomplete="off"></label>
    <label>Qty<input class="input" name="wantQty" type="number" min="1" max="99" value="1"></label>
    <div class="full item-preview" id="tradeItemPreview"></div>
    <div class="full inv-offer hidden" id="invOfferWrap"><label>Reserve from your trade inventory<select class="input" name="invKey"></select></label><label>Qty<input class="input" name="invQty" type="number" min="1" max="2" value="1"></label></div>
    <label>Other offer (free text)<input class="input" name="have" list="tradeItemNames" placeholder="Optional — you are open to offers" autocomplete="off"></label>
    <label>Qty<input class="input" name="haveQty" type="number" min="1" max="99" value="1"></label>
    <label class="full check-line"><input type="checkbox" name="openToOffers" checked> Open to offers</label>
    <datalist id="tradeItemNames"></datalist>
    <label>Region<select class="input" name="region"></select></label>
    <label>Platform<select class="input" name="platform"></select></label>
    <label class="full">Desired time<input class="input" name="desiredTime" maxlength="80" placeholder="Evenings, weekend…"></label>
    <label class="full">Notes<textarea class="input" name="notes" rows="3" maxlength="500" placeholder="What you need it for, flexibility, etc."></textarea></label>
    <div class="full"><button class="btn btn-primary" type="submit" id="tradeSubmit">Publish Request</button> <span class="form-note" id="tradeFormMsg" role="status" aria-live="polite"></span></div>
  </form>
</div></div>
<div class="modal hidden" id="offerModal" role="dialog" aria-modal="true" aria-labelledby="offerModalTitle"><div class="modal-card">
  <button class="modal-close" id="closeOfferModal" aria-label="Close">×</button>
  <span class="eyebrow">RESPOND TO A TRADE</span><h2 id="offerModalTitle">Make an offer</h2>
  <p class="muted" id="offerContext"></p>
  <form id="offerForm" class="form-grid">
    <label class="full">What can you offer? <span class="muted-label">(optional)</span><input class="input" name="offer" list="tradeItemNames" maxlength="80" placeholder="An item from Loot Intel, or free text" autocomplete="off"></label>
    <label class="full">Message to the Raider<textarea class="input" name="message" rows="4" minlength="2" maxlength="500" required placeholder="When you can play, platform, what you'd want in return…"></textarea></label>
    <p class="full small-note">Only this trade's owner can see your offer. Don't share passwords or payment details — The Raider Network never handles payments.</p>
    <div class="full"><button class="btn btn-primary" type="submit">Send Offer</button> <span class="form-note" id="offerFormMsg" role="status" aria-live="polite"></span></div>
  </form>
</div></div>
''')

PAGES['messages.html'] = ('messages', 'Messages — The Raider Network', 'Private Raider messages.', f'''
<section class="page-banner page-banner--slim">
  <img src="assets/images/raiders/raider-comms-operator.webp" alt="">
  <div class="page-banner__shade"></div>
  <div class="page-banner__copy"><span class="eyebrow">{I('message')} PRIVATE COMMS</span><h1>Messages</h1><p>Talk privately before sharing your in-game tag. Messages keep the trade or hunt they're about.</p></div>
</section>
<div class="page-shell">
  <div class="notice-bar hidden" id="messagesNotice" role="note"></div>
  <section class="panel hidden" id="handoffInbox"><header class="panel-head"><span class="eyebrow">{I('trade')} TRADE HANDOFFS</span><a class="text-btn" href="trade.html">Trade Board</a></header>
    <p class="muted">Every trade where an offer was accepted. Open one to see the other Raider's Embark ID, the agreed items, and to confirm the exchange.</p>
    <div id="handoffList" class="stack-sm"></div></section>
  <section class="messages-shell">
    <aside class="conversation-list"><div class="conversation-title">{I('message')} Conversations <b id="unreadCount"></b></div><div id="conversationList"></div></aside>
    <section class="chat-panel">
      <div id="chatEmpty" class="chat-empty"><img src="assets/images/raiders/gear-comms-radio.webp" alt=""><strong>Select a conversation</strong><span>Or choose “Message Raider” on a Loot Hunt or Trade request.</span></div>
      <div id="chatActive" class="hidden">
        <div class="chat-head"><button class="icon-btn chat-back" id="chatBack" aria-label="Back to conversations">‹</button><span id="chatAvatar"></span><span class="chat-who"><strong id="chatName">Raider</strong><small id="chatMeta"></small></span><a href="hunts.html" class="text-btn">Hunts</a><a href="trade.html" class="text-btn">Trades</a></div>
        <div class="chat-regarding hidden" id="chatRegarding"></div>
        <div id="messageThread" class="message-thread"></div>
        <form id="messageForm" class="message-compose"><textarea class="input" name="body" rows="2" maxlength="1000" placeholder="Write a message…" required aria-label="Message"></textarea><button class="btn btn-primary" type="submit">Send</button></form>
        <p class="form-note" id="messageFormMsg" role="status"></p>
      </div>
    </section>
  </section>
</div>
''')

PAGES['handoff.html'] = ('handoff', 'Trade Handoff — The Raider Network', 'Private trade handoff between two Raiders.', f'''
<div class="page-shell handoff-shell" id="handoffRoot"><p class="muted">Loading trade…</p></div>
''')

PAGES['profile.html'] = ('profile', 'My Profile — The Raider Network', 'Your Raider profile.', f'''
<section class="profile-hero">
  <img class="profile-hero__bg" src="assets/images/heroes/raider-network-skyline.webp" alt="">
  <div class="profile-hero__inner">
    <img class="profile-avatar" id="profileAvatar" src="assets/images/raiders/raider-solo-scout.webp" alt="">
    <div><span class="eyebrow">RAIDER PROFILE</span><h1 id="profileName">My Profile</h1><div class="profile-meta" id="profileMeta"></div></div>
    <div class="profile-stats"><div><b id="statActive">0</b><span id="statActiveLabel">Active hunts</span></div><div><b id="statTrades">0</b><span id="statTradesLabel">Open trades</span></div><div><b id="statDone">0</b><span id="statDoneLabel">Completed</span></div><div><b>—</b><span>Reputation <em>soon</em></span></div></div>
    <button class="btn btn-ghost" id="logoutBtn">Log out</button>
  </div>
</section>
<div class="page-shell profile-layout">
  <section class="panel"><header class="panel-head"><span class="eyebrow">{I('profile')} RAIDER IDENTITY</span></header>
    <form id="profileForm" class="stack">
      <label>Raider Display Name<input class="input" name="display_name" required maxlength="30"></label>
      <label id="embark">Embark ID <span class="muted-label">(private · only shared inside an accepted trade)</span><input class="input" name="raider_tag" maxlength="30" placeholder="RaiderName#1234" autocomplete="off"></label>
      <p class="small-note embark-help">Find it in ARC Raiders: Main Menu → Social menu (👥) → your profile → <b>Show Discriminator</b>. It looks like <code>DisplayName#1234</code>. Raiders see it only after you accept their offer or they accept yours.</p>
      <div class="two-col"><label>Platform<select class="input" name="platform"></select></label><label>Region<select class="input" name="region"></select></label></div>
      <fieldset class="avatar-field"><legend>Raider portrait</legend><div id="profileAvatarSlot"></div></fieldset>
      <button class="btn btn-primary">Save Profile</button><p class="form-note" id="profileMsg" role="status"></p>
    </form>
  </section>
  <div class="profile-cols">
    <div id="handoffBanner"></div>
    <section class="panel hidden" id="myHandoffsPanel"><header class="panel-head"><span class="eyebrow">{I('trade')} ACCEPTED TRADES</span><a class="text-btn" href="messages.html">All handoffs</a></header><div id="myHandoffs" class="stack-sm"></div></section>
    <section class="panel"><header class="panel-head"><span class="eyebrow">{I('trade')} OPEN TRADE REQUESTS</span><a class="text-btn" href="trade.html?new=">+ New</a></header><div id="myTrades" class="stack-sm"></div></section>
    <section class="panel hidden" id="myOffersPanel"><header class="panel-head"><span class="eyebrow">{I('trade')} TRADE OFFERS</span><a class="text-btn" href="trade.html">Trade Board</a></header><div id="myOffers" class="stack-sm"></div></section>
    <section class="panel"><header class="panel-head"><span class="eyebrow">{I('squad')} ACTIVE LOOT HUNTS</span><a class="text-btn" href="hunts.html?new=">+ New</a></header><p class="small-note device-only-note hidden">Loot Hunts are still in preview: they are saved in this browser only until they move to the server.</p><div id="myHunts" class="stack-sm"></div></section>
    <section class="panel hidden" id="myInventoryPanel"><header class="panel-head"><span class="eyebrow">{I('inventory')} MY TRADE INVENTORY</span><a class="text-btn" href="trade.html">Trade Board</a></header><div id="myInventory"></div></section>
    <section class="panel"><header class="panel-head"><span class="eyebrow">{I('extraction')} COMPLETED HUNTS</span></header><div id="myCompleted" class="stack-sm"></div></section>
    <section class="panel"><header class="panel-head"><span class="eyebrow">{I('rarity')} REPUTATION &amp; BADGES</span><span class="demo-pill">COMING SOON</span></header><p class="muted">Reputation will come from completed hunts and trades confirmed by both Raiders. Badges are placeholders.</p><div class="badge-grid" id="badgeGrid"></div></section>
  </div>
</div>
''')

PAGES['auth.html'] = ('auth', 'Join — The Raider Network', 'Create a Raider profile.', f'''
<section class="auth-shell">
  <div class="auth-art">
    <img class="auth-art__bg" src="assets/images/raiders/raider-squad-lineup.webp" alt="">
    <div class="auth-art__copy"><span class="eyebrow">ENTER THE NETWORK</span><h1>Your Raider identity.<br>Your hunts.<br>Your community.</h1><p>Create a simple Raider profile so people know who they are running with. Your login email is never displayed, and your Raider tag stays private until you share it.</p>
    <div class="quote-card">“Hunting: Rotary Encoder<br>Stella Montis · Tonight<br>NA East · Cross-platform”</div></div>
  </div>
  <div class="auth-card">
    <div class="auth-tabs" role="tablist"><button id="loginTab" class="active" type="button" role="tab" aria-selected="true" aria-controls="loginForm">Log in</button><button id="registerTab" type="button" role="tab" aria-selected="false" aria-controls="registerForm">Register</button></div>
    <p class="auth-next" id="authNext"></p>
    <form id="loginForm" class="stack" novalidate><label>Username or email<input class="input" name="login" required maxlength="254" autocomplete="username" autocapitalize="none" spellcheck="false"></label><label>Password<input class="input" type="password" name="password" required maxlength="128" autocomplete="current-password"></label><button class="btn btn-primary" type="submit">Log in</button><p class="form-note" id="loginMsg" role="status" aria-live="polite"></p></form>
    <form id="registerForm" class="stack hidden" novalidate>
      <div class="two-col"><label>Username <span class="muted-label">(public handle)</span><input class="input" name="username" required minlength="3" maxlength="20" pattern="[A-Za-z0-9_]{{3,20}}" autocomplete="username" autocapitalize="none" spellcheck="false" placeholder="e.g. night_runner"></label><label>Display name<input class="input" name="display_name" required minlength="2" maxlength="30" placeholder="Your in-game Raider name"></label></div>
      <label>Email <span class="muted-label">(private — never shown)</span><input class="input" type="email" name="email" required maxlength="254" autocomplete="email"></label>
      <div class="two-col"><label>Password <span class="muted-label">(10+ characters)</span><input class="input" type="password" name="password" required minlength="10" maxlength="128" autocomplete="new-password"></label><label>Confirm password<input class="input" type="password" name="confirm_password" required minlength="10" maxlength="128" autocomplete="new-password"></label></div>
      <label>Embark ID <span class="muted-label">(optional, kept private)</span><input class="input" name="raider_tag" maxlength="30" placeholder="RaiderName#1234 · add it later if you like" autocomplete="off"></label>
      <div class="two-col"><label>Platform<select class="input" name="platform"></select></label><label>Region<select class="input" name="region"></select></label></div>
      <fieldset class="avatar-field"><legend>Pick a Raider portrait</legend><div id="avatarSlot"></div></fieldset>
      <button class="btn btn-primary" type="submit">Create Raider Account</button><p class="form-note" id="registerMsg" role="status" aria-live="polite"></p></form>
    <p class="small-note" id="authModeNote"></p>
  </div>
</section>
''')

for fn, (page, title, desc, body) in PAGES.items():
    with open(os.path.join(ROOT, fn), 'w') as f:
        f.write(HEAD.format(title=title, desc=desc, page=page) + body.strip('\n') + FOOT)
print('wrote', len(PAGES), 'pages')
