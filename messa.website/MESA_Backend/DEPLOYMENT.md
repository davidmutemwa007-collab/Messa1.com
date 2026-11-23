# MESA deployment guide

## Recommended architecture

Keep the Python standard-library HTTP application and SQLite database. Vercel's
ephemeral function filesystem is not a suitable home for this database or the
long-running `ThreadingHTTPServer`. Use a **single-instance Linux VM or a
single-instance container host with a persistent local disk**, terminate HTTPS
at a reverse proxy such as Caddy, and run the Python process as a supervised
service. This keeps the current backend intact and gives SQLite a durable,
local filesystem. Do not scale this SQLite deployment to multiple app
instances or network filesystems.

The supplied photographs, video and soundtrack remain under
`MESA_Frontend/static/media/` and are served by the Python application. Python
3.10+ is required; no third-party Python packages are needed.

## Production environment

Create a private environment file readable only by the service account. Set:

```text
MESA_ENV=production
MESA_HOST=127.0.0.1
PORT=5000
MESA_DATABASE=/var/lib/mesa/mesa.sqlite3
MESA_UPLOAD_DIR=/var/lib/mesa/uploads
MESA_SECRET_KEY=<at least 32 cryptographically random bytes>
MESA_COOKIE_SECURE=1
MESA_PUBLIC_URL=https://www.example.com
```

Generate a key outside the source tree, for example:

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never put the real value in source control, frontend JavaScript, or a public
deployment setting. Persist the database, uploaded media, and environment/secret storage
outside the application release directory. Restrict the database, secret, and
backup permissions to the service operator. `MESA_ENV=production` also marks
the session cookie `Secure`; keep HTTPS enabled at the proxy.

## Start and proxy

From `MESA_Backend`, the production start command is:

```sh
python3 app.py
```

Run it under systemd or the hosting platform's process supervisor, with the
environment above and the application files deployed read-only. Configure
Caddy (or an equivalent HTTPS reverse proxy) to forward the public hostname to
`127.0.0.1:5000`. Do not expose port 5000 publicly. Use one application process
and one instance for this SQLite architecture. The built-in server writes
request logs to standard output; the supervisor should retain and rotate them.

Create the first administrator locally, using the same production environment
and database path:

```sh
python3 setup_admin.py
```

The utility prompts for a temporary password and does not print or store it
in source. The administrator must change it at first sign-in before accessing
protected dashboard APIs. Do not configure an administrator password in a
deployment manifest or add an administrator registration endpoint.

## Health, SEO, and backups

- Health check: `GET /api/health` (returns `503` if SQLite cannot be queried).
- Before an older database is migrated, the application creates a timestamped
  SQLite online-backup copy beside it. Confirm the backup destination has
  adequate protected disk space. Still take a separate off-host backup before
  upgrade or restore work; never publish the database or backups.
- Set `MESA_PUBLIC_URL` to the final HTTPS origin. It enables the canonical
  link, Open Graph URL/image, and `/sitemap.xml`. `/robots.txt` excludes API
  endpoints from crawlers.
- Before applying schema changes or replacing the database, stop the service
  and take an independent backup. SQLite's online backup API can create one
  while the app is running:

```sh
python3 -c "import sqlite3; src=sqlite3.connect('/var/lib/mesa/mesa.sqlite3'); dst=sqlite3.connect('/secure-backups/mesa-$(date +%F).sqlite3'); src.backup(dst); dst.close(); src.close()"
```

Automate and monitor encrypted off-host copies, retain multiple generations,
and periodically test restoring a copy to a separate database path. To recover,
stop the service, preserve the failed database for diagnosis, restore a verified
backup to the configured path, check ownership/permissions, then restart and
call `/api/health`. Do not put database backups inside `MESA_Frontend/static/`.
Uploaded images also contain site/customer operational data; include the
configured upload directory in persistent-volume and backup plans.

The project data directory may retain local safety snapshots
`mesa.sqlite3.backup-before-session-migration-20261123` and the newer
`mesa.sqlite3.backup-current-20261123`; keep these private and out of source
control. Local copies are safety snapshots, not a substitute for scheduled
off-host production backups.

## GitHub and Vercel

The project is prepared for a private GitHub push with a root `.gitignore`,
placeholder `.env.example`, and `.github/workflows/test.yml`. Review the staged
file list before any push and ensure no `.sqlite3`, database backup, upload,
secret key, or private environment file is included. This workspace has not
been connected to GitHub and no repository has been created or published.

Vercel is not a suitable host for this Python server, SQLite database, or
uploaded-media persistence. A separate static frontend deployment would also
require an explicitly designed API origin, credentialed CORS, and compatible
cookie-domain/HTTPS settings; none are selected or configured. Keep the
frontend and API on the same Python host unless that cross-origin architecture
is deliberately designed and secured. No Vercel project, domain, or deployment
has been created.

## Operational limits

The application records orders and payment preferences; it does not process
payments. A real payment provider must be integrated and tested before online
payment is offered. Add edge or proxy rate limiting, monitoring/alerting,
automated backup verification, and an incident/recovery procedure before
public launch. Do not claim a deployment is live until the host, TLS, domain,
health check, and real persistent storage have all been verified.
