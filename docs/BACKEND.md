# Backend architecture — The Raider Network v6.0

## Overview

```
assets/js/api.js  ──fetch /api/*──►  functions/api/[[path]].js  ──►  functions/_lib/router.js
(browser client,                     (Pages Function entry)            ├─ session.js     cookie → session → user
 no tokens, no SQL)                                                    ├─ handlers.js    route logic + authorization
                                                                       ├─ validate.js    server-side input rules
                                                                       ├─ security.js    PBKDF2, tokens, rate limits
                                                                       ├─ reference.js   Loot Intel ids/regions (static JSON via ASSETS)
                                                                       └─ repo.js        ALL SQL (parameterised) ──► D1 (env.DB)
```

- **Repository-only files:** `functions/_middleware.js` answers 404 for server source, migrations, tools, seeds, docs and config files that are deployed alongside the site (the build output directory is the repository root).
- **Static site:** the HTML, CSS, JS, Loot Intel JSON, maps and MetaForge cache are served by Cloudflare Pages unchanged. `_routes.json` sends **only `/api/*`** to Functions, so static files never cost a Function invocation.
- **D1** stores user-generated data only. The 581-item Loot Intel database is not copied into D1. The API reads `data/items.json` and `data/users.json` through the Pages `ASSETS` binding to validate item ids, regions and platforms, and it takes canonical item names from Loot Intel instead of trusting names sent by the browser.
- **MetaForge** stays read-only and cached in `data/maps/`. Neither browsers nor the API call it.
- **Backend modes** (`assets/js/api.js`):

| Mode | When | Behaviour |
|---|---|---|
| `server` | `/api/health` answers | Production |
| `demo` | No API, and the host is `localhost` / `127.0.0.1` | Local `python3 -m http.server` only; labelled DEMO MODE |
| `offline` | Anything else | Accounts and trading are disabled with a message. No silent fallback to browser storage |

## Database schema (`migrations/0001_initial.sql`)

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | `usr_` + 24 hex. Every future table references this |
| `username` | TEXT NOCASE, UNIQUE | Public handle, stored lower-case, 3–20 `[a-z0-9_]` |
| `display_name` | TEXT | Public Raider name |
| `email` | TEXT NOCASE, UNIQUE | Private; returned only to its owner |
| `password_hash` | TEXT | `pbkdf2_sha256$100000$<salt>$<hash>` |
| `avatar_url` | TEXT | Allow-listed site portrait path |
| `region`, `platform` | TEXT | Allow-listed values |
| `raider_tag` | TEXT | Private; returned only to its owner |
| `role` | TEXT | `member` / `admin` (reserved for moderation) |
| `status` | TEXT | `active` / `suspended` / `deleted` |
| `created_at`, `updated_at` | TEXT | ISO-8601 UTC |

### `sessions`

| Column | Notes |
|---|---|
| `id` | Primary key |
| `user_id` | → `users`, ON DELETE CASCADE |
| `token_hash` | UNIQUE; SHA-256 of the cookie token |
| `created_at`, `expires_at` | Sessions last 30 days |
| `last_used_at` | Written at most every 15 minutes |
| `user_agent` | |

### `trade_posts`

| Column | Notes |
|---|---|
| `id` | Primary key |
| `user_id` | → `users`, ON DELETE CASCADE |
| `wanted_item_id` | NULL for free text |
| `wanted_item_name` | Required |
| `wanted_quantity` | 1–99 |
| `offered_item_id`, `offered_item_name`, `offered_quantity` | Optional |
| `open_to_offers` | 0 / 1 |
| `region`, `platform` | |
| `desired_time` | ≤ 80 characters |
| `notes` | ≤ 500 characters |
| `status` | `OPEN` / `CLOSED` / `COMPLETED` |
| `created_at`, `updated_at`, `closed_at` | |

### `trade_offers`

| Column | Notes |
|---|---|
| `id` | Primary key |
| `trade_post_id` | → `trade_posts`, ON DELETE CASCADE |
| `from_user_id` | → `users` |
| `message` | |
| `offered_item_id`, `offered_item_name` | |
| `status` | `PENDING` / `ACCEPTED` / `DECLINED` / `WITHDRAWN` |
| `created_at`, `updated_at` | |

A partial unique index allows only one PENDING offer per Raider per trade.

### `rate_limits`

| Column | Notes |
|---|---|
| `bucket` | Contains a SHA-256 of the IP, never the raw IP |
| `window_start` | |
| `count` | |

### Prepared for future versions

New tables only need `user_id TEXT REFERENCES users(id)`. Identity always comes from `ctx.session.user.id`, so nothing about authentication changes. The planned tables are:

- `loot_hunts (id, user_id, item_id, map_id, …)`
- `hunt_participants (hunt_id, user_id, …)`
- `messages (id, sender_id, recipient_id, trade_post_id?, hunt_id?, body, read_at, …)`
- `notifications (id, user_id, kind, ref_id, read_at, …)`

## API endpoints

All endpoints return JSON. Errors look like `{ "error": { "code", "message", "field"? } }`.

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /api/health` | – | D1 connected and migrated? |
| `POST /api/auth/register` | – | `{username, display_name, email, password, confirm_password, raider_tag?, region?, platform?, avatar_url?}` → 201, sets the session cookie |
| `POST /api/auth/login` | – | `{login (username or email), password}` → sets the session cookie |
| `POST /api/auth/logout` | cookie | Deletes the session and clears the cookie |
| `GET /api/auth/session` | optional | `{user \| null, trades:{active,completed,closed}}`. The private fields (email, tag) are included only for yourself |
| `PATCH /api/me` | required | Update display name, portrait, region, platform, Raider tag |
| `GET /api/me/offers` | required | `{sent, received}` |
| `GET /api/users/:username` | – | Public profile: no email, no tag |
| `GET /api/trades?status=OPEN\|CLOSED\|COMPLETED\|ALL&user=&limit=` | – | Trade Board (newest first, max 500) |
| `POST /api/trades` | required | Create (owner = session user) |
| `GET /api/trades/:id` | – | One trade |
| `PATCH /api/trades/:id` | owner | Edit fields and/or `status` (OPEN↔CLOSED, →COMPLETED; completed trades are locked) |
| `DELETE /api/trades/:id` | owner | Delete (its offers cascade) |
| `GET /api/trades/:id/offers` | required | The owner sees all offers; anyone else sees only their own |
| `POST /api/trades/:id/offers` | required, not the owner | `{message, offered_item_id?, offered_item_name?}`. Only on OPEN trades |
| `PATCH /api/offers/:id` | owner / sender | `{action: accept\|decline}` (trade owner) or `withdraw` (sender); PENDING only |
| `GET /api/stats` | – | `{raiders, open_trades, completed_trades}` |

## Security controls

### Passwords

- PBKDF2-HMAC-SHA256 via the platform Web Crypto API, with a 16-byte random salt and 100,000 iterations. That is the maximum the Workers runtime permits.
- Comparison is constant-time.
- The hash string records its own parameters, so stronger settings can be rolled out later, with transparent re-hashing on the next login.
- No plaintext is ever stored or logged.
- Rules: 10–128 characters; common passwords and passwords containing the username are refused.

### Sessions

- 256-bit random tokens are kept in an `HttpOnly`, `SameSite=Lax` cookie: `__Host-trn_session` with `Secure` on HTTPS, `trn_session` on local plain HTTP.
- Only the SHA-256 of the token is stored.
- Sessions expire after 30 days. Expired and unknown tokens are rejected, and expired rows are deleted.
- Tokens never appear in URLs or in JavaScript-readable storage.

### Identity and authorization

- The acting user always comes from the session cookie. Any `user_id` in a request body is ignored.
- Owner checks run in the handler, and ownership is also part of every UPDATE and DELETE `WHERE` clause.

### CSRF

- SameSite=Lax cookies.
- A required `X-TRN-CSRF` header on every mutation; HTML forms can't send it cross-site without a CORS preflight, which is never granted.
- An `Origin` check.
- JSON-only request bodies, at most 16 KB.

### SQL injection and input handling

- **SQL injection:** every query is parameterised (`?1, ?2 …`) and lives in `repo.js`; no user input is concatenated into SQL.
- **Validation:** client-side for usability and server-side as the authority. Text is NFC-normalised, control and bidi characters are stripped, and lengths are limited. Lists (regions, platforms, portraits, Loot Intel ids) are allow-listed.
- **XSS:** the API returns JSON only, and the pages escape all user content (`TRN.esc`). A Content-Security-Policy (`_headers`) allows scripts only from this site.

### Rate limiting (D1-backed fixed windows)

- **Failed logins:** 8 per account per IP, 50 per account across all IPs, and 30 per IP, each per 15 minutes. The per-account counter is keyed on the resolved account, so username and email share one counter, and someone else guessing your password cannot lock you out from your own connection.
- **Registrations:** 60 attempts and 10 accounts per IP per hour.
- **Atomic counting:** every attempt is counted atomically *before* the work is done, so parallel requests cannot slip past a limit.
- **Posting:** 30 trade posts and 30 offers per user per hour.
- **Enumeration:** unknown accounts take the same time and give the same message as wrong passwords.
- **Edge layer:** a Cloudflare WAF rule is recommended in addition (see the setup guide).

### Privacy

- Email and Raider tag are never returned by public endpoints or shown to other Raiders.
- IPs are stored only as truncated SHA-256 hashes inside rate-limit keys.
