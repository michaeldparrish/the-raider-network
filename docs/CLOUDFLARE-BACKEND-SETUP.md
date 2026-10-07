# Cloudflare backend setup — The Raider Network v6.0

This guide takes you from the v6.0 ZIP to a live site where accounts and Trade Board posts are stored in **Cloudflare D1** and survive refreshes, new devices and new deployments. You don't need to know Cloudflare already. Follow the steps in order and don't skip ahead to pushing to GitHub.

```
Browser ──► Cloudflare Pages (static site: HTML, CSS, JS, Loot Intel JSON, maps)
        └─► /api/*  ──► Pages Functions (functions/, server-side code) ──► D1 database "raider-network-db"
```

- **GitHub** holds the **code**: everything in this folder.
- **D1** holds the **user data**: accounts, sessions, trade posts and offers. It is never in GitHub and never in the browser.
- The Loot Intel database, maps and MetaForge cache stay as static files, exactly as before.

---

## 0. Before you start

**What you need**

- **Node.js 18 or newer.** Install the "LTS" version from <https://nodejs.org>. Check it with `node --version`.
- A terminal (on Mac: the **Terminal** app), opened in the project folder.
- The Cloudflare account that already hosts `the-raider-network.pages.dev`.

**Cost.** D1 and Pages Functions have free tiers that comfortably cover a launch. There is one thing to know:

> **CPU time and passwords.** Each login or registration runs a deliberately slow password hash (PBKDF2, 100,000 rounds; that is the strongest setting Cloudflare's runtime allows). It takes about 13 ms of CPU. The **Workers Free** plan allows **10 ms** of CPU per request, with some tolerance for occasional overruns.
>
> - If registering or logging in ever shows **"Error 1102: Worker exceeded resource limits"**, switch the account to **Workers Paid** (US $5/month, 30 seconds of CPU per request). No code change is needed.
> - In the dashboard: **Workers & Pages → Plans** (or **Manage account → Billing**).
> - Every other page and API call uses far less CPU.

All commands below use `npx wrangler …`. `npx` downloads Cloudflare's command-line tool, **wrangler**, the first time; you don't need to install anything else.

---

## 1. Test everything locally first (no Cloudflare account needed)

Unzip `the-raider-network-v6.0.zip` and open a terminal in the `the-raider-network-v6.0` folder.

```bash
# 1. create the local test database (stored in .wrangler/ in this folder)
npx wrangler d1 migrations apply raider-network-db --local

# 2. run the full site + API in Cloudflare's own runtime
npx wrangler pages dev .
```

Open <http://127.0.0.1:8788>.

- **Register** an account, then **Post a Trade Request**.
- Open a **private/incognito window**. You'll see the trade while logged out, and you can log in there with the same account.
- Stop the server with **Ctrl + C**, start it again with `npx wrangler pages dev .`, and refresh. The account and trade are still there.
- The local database lives in `.wrangler/state/`. Delete that folder (then re-run step 1) to start over. It is **never** uploaded: `.gitignore` excludes it.

**Two local modes**

| You run | Mode | What you get |
|---|---|---|
| `npx wrangler pages dev .` | **Server mode**, same as production | Real accounts and trades in a local D1 |
| `python3 -m http.server 8080` | **Local demo mode** | The old browser-only demo, labelled **DEMO MODE**. Only works on `localhost`; a real domain never falls back to it |

**Optional: run the automated tests.** You need Python 3 with `pip install playwright requests`, then `python3 -m playwright install chromium`.

```bash
python3 tools/api_test.py           # 89 auth / authorization / offers / rate-limit checks (own throw-away DB)
python3 tools/persistence_test.py   # 30 browser checks incl. server restart + fresh browsers (own throw-away DB)
python3 -m http.server 8080 &       # then, for the static/demo suites:
python3 tools/nav_test.py           # mobile hamburger menu at 390/393/430/768 + desktop
python3 tools/mobile_test.py        # no horizontal scrolling at 390/393/430/768/1440/1920
python3 tools/smoke_test.py && python3 tools/flow_test.py
```

---

## 2. Connect wrangler to your Cloudflare account

```bash
npx wrangler login      # a browser tab opens: log in to Cloudflare and click "Allow"
npx wrangler whoami     # should print your account name and Account ID
```

If you have more than one Cloudflare account, `whoami` lists them. Use the account that owns the Pages project.

---

## 3. Create the D1 database `raider-network-db`

Pick **one** of the two ways.

**A. Command line (easiest)**

```bash
npx wrangler d1 create raider-network-db
```

It prints a block that contains `database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`. **Copy that ID.** If wrangler offers to add the database to your config file automatically, you can answer **No**; you'll paste the ID yourself in step 4.

**B. Cloudflare Dashboard**

1. Go to <https://dash.cloudflare.com> and select your account.
2. In the left sidebar, open **Storage & databases → D1 SQL database**. If you can't find it, type "D1" in the dashboard search bar.
3. Click **Create Database**, name it exactly **`raider-network-db`**, and choose a location hint near your players (e.g. *Eastern North America*). Click **Create**.
4. The database page shows the **Database ID**. Copy it.

---

## 4. Bind D1 to the site (`wrangler.toml`)

Open `wrangler.toml` in the project folder and replace the placeholder with your ID:

```toml
database_id = "REPLACE_WITH_YOUR_D1_DATABASE_ID"   # ← paste the ID from step 3 here
```

Leave `binding = "DB"` and `database_name = "raider-network-db"` exactly as they are.

**How this file works, and two things to check in the dashboard first**

Because the file contains `pages_build_output_dir`, Cloudflare Pages treats `wrangler.toml` as the **source of truth** for the project's configuration once you deploy it. From then on, the matching settings in the dashboard become read-only and show what's in the file.

Before you deploy, open **Workers & Pages → the-raider-network → Settings**:

1. **Project name.** The project must be called **`the-raider-network`** (it matches `name = "the-raider-network"` in the file). If yours has a different name, change the `name` line to match.
2. **Build configuration.** The **Build output directory** should be the repository root (shown as `/` or empty), and there should be **no build command**. This matches `pages_build_output_dir = "."`.
3. **Environment variables / bindings.** v6.0 needs none besides `DB`. If you previously added variables in the dashboard, note them down: when the file becomes the source of truth they must also be in the file.

**Preview deployments (other branches).** Preview deployments use the same database unless you give them their own. That is safest once real users exist. To do that:

1. Run `npx wrangler d1 create raider-network-db-preview`.
2. Add this to the bottom of `wrangler.toml`:

```toml
[env.preview]
[[env.preview.d1_databases]]
binding = "DB"
database_name = "raider-network-db-preview"
database_id = "PASTE_PREVIEW_DATABASE_ID"
migrations_dir = "migrations"
```

3. Migrate it with `npx wrangler d1 migrations apply raider-network-db-preview --remote`.

---

## 5. Create the tables in the production database (migrations)

```bash
npx wrangler d1 migrations apply raider-network-db --remote
```

Answer **yes** when asked. You should see `0001_initial.sql │ ✅`. To check:

```bash
npx wrangler d1 execute raider-network-db --remote --command "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
```

You should see `d1_migrations`, `rate_limits`, `sessions`, `trade_offers`, `trade_posts` and `users`.

Future versions add files such as `migrations/0002_….sql`. You run the **same command** again, and only new files are applied.

---

## 6. Secrets and environment variables

**None are required for v6.0.**

- Session tokens are random values generated per login, so there is no signing key to protect.
- The database is reached through the `DB` binding, not a password, and there are no database credentials anywhere in the code or in the browser.
- Never put secrets in `assets/config.js`, because every visitor downloads it.

If a future version needs a secret (for example a Cloudflare Turnstile key), you'll add it with `npx wrangler pages secret put NAME`. For local development it goes in a file called `.dev.vars`, which `.gitignore` already excludes.

---

## 7. Deploy (your usual GitHub → Cloudflare workflow)

Only after steps 3–5 are done:

```bash
cd the-raider-network            # your local clone of michaeldparrish/the-raider-network
git checkout -b v6.0             # optional: a branch first gives you a preview deployment to test
# copy the contents of the-raider-network-v6.0/ over the repository files
git add -A
git status                       # check: no .wrangler/, node_modules/, backups/ or .dev.vars listed
git commit -m "v6.0: mobile navigation fix, D1 accounts and persistent Trade Board"
git push -u origin v6.0          # preview deployment (uses the preview DB if you set one up)
# when the preview works: merge into main (GitHub pull request, or locally:)
git checkout main && git merge v6.0 && git push
```

Watch the build under **Workers & Pages → the-raider-network → Deployments**. When it succeeds, the deployment details show a **Functions** section listing the `/api/*` route.

---

## 8. Confirm D1 is connected

Open **<https://the-raider-network.pages.dev/api/health>**.

| You see | Meaning | Fix |
|---|---|---|
| `{"ok":true,"api":"6.0","database":"connected","migrated":true}` | ✅ Everything is connected | — |
| `"code":"no_database"` | The `DB` binding is missing | Check `database_id` in `wrangler.toml` and redeploy |
| `"code":"not_migrated"` or `"migrated":false` | Tables don't exist yet | Run step 5 |
| An HTML page or a 404 | Functions weren't deployed | Make sure `functions/` and `_routes.json` are committed, then check the build log |

On the site itself: in production there is **no DEMO MODE** badge in the header. If you see an **OFFLINE** badge, `/api/health` isn't answering. Use the table above.

---

## 9. Confirm registration works

1. On the live site click **Join the Network** (or **Register** in the phone menu) and create your account. **Register `perisher` first**, before anyone else can take that username.
2. The header now shows your Raider. **My Profile** shows your display name, @username and join date.
3. Log out, then log in again from your **phone** or a **private window** with the same username and password.
4. Check the database. Run this read-only query; it never shows password hashes:

```bash
npx wrangler d1 execute raider-network-db --remote --command "SELECT username, display_name, created_at FROM users ORDER BY created_at DESC LIMIT 10"
```

You can also use the Dashboard: **Storage & databases → D1 SQL database → raider-network-db → Console**.

---

## 10. Confirm a trade persists

1. Logged in, click **+ Post a Trade Request** and publish one.
2. On another device, for example your phone on mobile data, open the Trade Board **without logging in**. The trade is there.
3. Push any small change to GitHub to trigger a new deployment. The trade is still there afterwards.
4. Query the database:

```bash
npx wrangler d1 execute raider-network-db --remote --command "SELECT t.id, u.username, t.wanted_item_name, t.status, t.created_at FROM trade_posts t JOIN users u ON u.id = t.user_id ORDER BY t.created_at DESC LIMIT 10"
```

**Optional: Perisher's 10 real listings.** Once the `perisher` account exists on the live site:

```bash
python3 tools/make_seed_sql.py                    # writes seeds/perisher-trades.sql
npx wrangler d1 execute raider-network-db --remote --file seeds/perisher-trades.sql
```

The SQL only inserts rows **for an existing `perisher` account** and is safe to run twice. Nothing like this happens automatically, and no fake Raiders are ever created.

---

## 11. Inspect production data safely

- **Use read-only `SELECT` queries.** Never run `UPDATE` or `DELETE` on production without first taking a backup (step 12).
- **Never select `password_hash` or `email`** in anything you share or screenshot. List exactly the columns you need instead of `SELECT *`.
- The `sessions` table holds only **hashes** of session tokens, so nothing in it can be used to log in.
- Useful read-only queries:

```bash
# community numbers
npx wrangler d1 execute raider-network-db --remote --command "SELECT (SELECT COUNT(*) FROM users) AS raiders, (SELECT COUNT(*) FROM trade_posts WHERE status='OPEN') AS open_trades, (SELECT COUNT(*) FROM trade_posts WHERE status='COMPLETED') AS completed"
# offers waiting for an answer
npx wrangler d1 execute raider-network-db --remote --command "SELECT o.id, fu.username AS from_user, t.wanted_item_name, o.status FROM trade_offers o JOIN users fu ON fu.id=o.from_user_id JOIN trade_posts t ON t.id=o.trade_post_id WHERE o.status='PENDING'"
```

**Suspending an account** (moderation) hides it and blocks its sessions and logins. Take a backup first:

```bash
npx wrangler d1 execute raider-network-db --remote --command "UPDATE users SET status='suspended' WHERE username='SOME_USERNAME'"
```

---

## 12. Back up / export D1

```bash
mkdir -p backups
npx wrangler d1 export raider-network-db --remote --output backups/raider-network-db-$(date +%Y-%m-%d).sql
```

- **The export contains emails and password hashes.** Keep it private: never commit it to GitHub (`backups/` is in `.gitignore`), and store it somewhere encrypted.
- **Time Travel** is D1's built-in point-in-time recovery. It is always on, with **7 days** of history on Workers Free and **30 days** on Workers Paid. To see the current restore point:

```bash
npx wrangler d1 time-travel info raider-network-db
```

A good habit: take an export **before every migration** and before any manual `UPDATE` or `DELETE`.

---

## 13. Recovery: if a deployment or migration goes wrong

**A new deployment broke the site.** Your data is not affected, because D1 is separate from deployments.

1. Open **Workers & Pages → the-raider-network → Deployments**.
2. Find the last good deployment, open its **⋯** menu and choose **Rollback to this deployment**.
3. Then fix the code and push again.

**The build failed.** For example, you pushed while `database_id` was still the placeholder. The previous deployment simply stays live. Fix `wrangler.toml` and push again.

**A migration failed part-way.**

1. Run `npx wrangler d1 migrations list raider-network-db --remote` to see what was applied. A migration that failed is not marked as applied.
2. Fix the SQL file and run `npx wrangler d1 migrations apply raider-network-db --remote` again.
3. Never edit a migration file that has already been applied; add a new numbered file instead.

**Bad data change: restore the database to an earlier time.**

```bash
# 1. note the current bookmark so you can undo the restore
npx wrangler d1 time-travel info raider-network-db
# 2. restore to a moment before the problem (Unix timestamp; https://www.epochconverter.com helps)
npx wrangler d1 time-travel restore raider-network-db --timestamp=UNIX_TIMESTAMP
```

**Restore from an export file into a fresh database** (worst case):

1. `npx wrangler d1 create raider-network-db-restored`
2. `npx wrangler d1 execute raider-network-db-restored --remote --file backups/FILE.sql`
3. Point `database_id` in `wrangler.toml` at the new database and push.

**Accounts and trading show OFFLINE or "temporarily unavailable".** Open `/api/health` and use the table in step 8.

---

## 14. Recommended protections before a wider launch

1. **Workers Paid plan.** This avoids the CPU limit on password hashing (see step 0).
2. **Edge rate limiting.** The app already limits logins, registrations, posts and offers in D1. Cloudflare **WAF rate-limiting rules** add a second layer at the edge, but they only work on a **custom domain** you've added to Cloudflare, not on `*.pages.dev`.
   - **Where:** your domain → **Security → WAF → Rate limiting rules**.
   - **Suggested rule:** path starts with `/api/auth/`, 20 requests per minute per IP → Block for 10 minutes.
3. **Cloudflare Turnstile** on the Register form. This is planned for v6.1 and needs a site key and a secret.
4. **Monetization:** before enabling monetization, confirm commercial API permission with MetaForge per their API terms.
