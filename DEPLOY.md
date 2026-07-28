# Deploying Tailoring App to production

## Important: SQLite file storage warning
This app uses SQLite (`database/tailoring.db`) and stores uploaded images in
`static/uploads/`. On most free hosting tiers (Render free web service,
Railway, etc.) the filesystem is EPHEMERAL — it resets on every redeploy,
meaning your orders, customers, and uploaded photos/logo could be WIPED OUT.

Recommended before going live with real customer data:
- Use a host with a persistent disk (PythonAnywhere works out of the box;
  Render/Railway need a paid "persistent disk" add-on), OR
- Migrate to a hosted Postgres database (Render/Railway both offer a free
  Postgres instance) for the data, and use a cloud storage bucket
  (Cloudinary free tier is easy) for uploaded images/logo.

For a small single-shop internal tool, PythonAnywhere is the simplest safe
option since its disk is persistent by default.

## Option A: PythonAnywhere (simplest)
1. Create a free account at pythonanywhere.com
2. Upload/clone this project via their "Files" tab or git
3. Create a new "Web app" -> Manual configuration -> Python 3.10+
4. Point the WSGI file to import `app` from `app.py`
5. Set environment variable SECRET_KEY to a long random string
6. Reload the web app — you get a live yourapp.pythonanywhere.com URL

## Option B: Render.com
1. Push this project to a GitHub repo
2. On Render: New -> Web Service -> connect the repo
3. Build command: pip install -r requirements.txt
4. Start command: gunicorn app:app
5. Add environment variable SECRET_KEY (Render can auto-generate one)
6. Add a Persistent Disk mounted at /opt/render/project/src/database
   (and one for static/uploads) so data survives redeploys
7. Deploy — Render gives you a free yourapp.onrender.com URL,
   custom domain can be attached later

## Option C: Railway.app
Similar flow to Render: connect GitHub repo, it auto-detects Flask,
add SECRET_KEY env var, attach a volume for database/ and static/uploads/
for persistence.

## Change default admin password
Default login is admin / admin123 — change this immediately from
Settings after first deploy.
