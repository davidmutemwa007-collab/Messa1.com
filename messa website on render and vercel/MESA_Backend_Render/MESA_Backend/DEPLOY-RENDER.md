# MESA API — Render deployment

This package runs the existing standard-library HTTP server as a persistent Render web service. It deliberately does **not** use Vercel's Python function adapter; `app.py` is a server launcher, not a WSGI/ASGI `app` export.

## Deploy
1. Create a **private** GitHub repository for this backend and upload the contents of this folder (not the parent folder). Do not commit `data/mesa.sqlite3`, `data/secret.key`, `.env`, or customer exports.
2. In Render, choose **New → Blueprint** and connect the repository. Render reads `render.yaml`.
3. The blueprint uses a Starter web service and a 1 GB persistent disk mounted at `/var/data`. A persistent disk is required because this version still uses SQLite.
4. In the Render service environment settings, set `MESA_ALLOWED_ORIGINS` to the exact deployed Vercel origin, e.g. `https://mesa-website.vercel.app` (no trailing slash). If using a custom domain, include that exact origin too; separate multiple origins with commas.
5. Wait for the health check `https://YOUR-RENDER-SERVICE.onrender.com/api/health` to return JSON with `ok: true`.

Render generates `MESA_SECRET_KEY` through the blueprint. Keep it private. Do not change it casually after customers have active sessions.

## Database note
The source SQLite database is intentionally excluded from Git. The original `data/mesa.sqlite3` remains in the owner's original backend archive. Before launch, restore/migrate that data to the mounted disk using a secure, private transfer procedure and verify row counts. Do not make a customer database publicly downloadable. This package does not silently import production data.

## Current feature scope
The inspected backend supports customer registration/login, menu retrieval, bookings, order submission and health checks. The supplied source does not currently implement admin login/dashboard APIs or payment-gateway processing. Do not advertise those as live until implemented and tested.
