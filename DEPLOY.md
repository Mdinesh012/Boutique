# Deploying Tailoring App to production

## Why orders were disappearing on Render
Render's **free web service disk is ephemeral** — every restart/redeploy
wipes local files. The app was using a local SQLite file
(`database/tailoring.db`), so orders/customers saved fine but vanished
after the next restart or the next day. Uploaded images (logo, design
photos, fabric photos) in `static/uploads/` have the same problem.

**This has now been fixed in the code**: the app reads a `DATABASE_URL`
environment variable if present and uses that Postgres database instead
of local SQLite. Postgres data is NOT affected by web-service restarts.

## Render setup (recommended — free Postgres)
1. On Render dashboard: **New → PostgreSQL** → create a free instance,
   give it any name.
2. Once created, copy its **"Internal Database URL"** (starts with
   `postgres://...`).
3. Go to your Web Service → **Environment** tab → add a variable:
   - Key: `DATABASE_URL`
   - Value: (paste the Internal Database URL from step 2)
4. Also make sure `SECRET_KEY` env var is set (any random long string).
5. Redeploy (Manual Deploy → Deploy latest commit). On first boot the
   app automatically creates all tables in Postgres via `db.create_all()`.
6. From now on, orders/customers persist permanently — restarts and
   redeploys will NOT wipe your data anymore.

Note: your OLD data that was in the ephemeral SQLite file is not
automatically copied over (that file was already being reset). You'll
be starting fresh in Postgres, so re-enter the admin login and any
critical settings after first deploy.

## Uploaded images (logo, design/fabric photos)
These are still stored on Render's local disk, which is also ephemeral.
For a small-shop tool this is a lower-priority issue than losing order
data, but if uploaded photos keep disappearing too, the fix is to move
uploads to a free image host like Cloudinary — ask me if you want this
wired in.

## Change default admin password
Default login is admin / admin123 — change this immediately from
Settings after first deploy.

## Other hosting options (if not using Render)
- **PythonAnywhere**: simplest, disk is persistent by default, SQLite is
  fine there — no Postgres needed. Good if you want to avoid the
  Postgres setup above entirely.
- **Railway.app**: similar flow to Render — attach its free Postgres
  add-on and set `DATABASE_URL` the same way.

