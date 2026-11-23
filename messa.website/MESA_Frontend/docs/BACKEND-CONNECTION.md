# MESA Frontend ↔ Existing Standalone Backend

This frontend is intended to replace the existing `templates/index.html` and `static/` frontend folders in the standalone Python backend you already have. **Do not replace `app.py` or the SQLite data folder.**

## Copy into the existing backend project

1. Make a backup copy of the current project folder.
2. Extract this frontend ZIP.
3. Copy the `templates` folder and `static` folder into the existing backend project root, allowing the new files to replace the old frontend files.
4. Keep the existing `app.py`, `instance/` or `data/` folder, and your SQLite database.
5. Start the existing backend with its normal `start.bat` command.
6. Visit `http://127.0.0.1:5000`.

The Python server from the original standalone edition already serves `/` from `templates/index.html` and `/static/*` from `static/`, so this is a frontend replacement, not a backend migration.

## API endpoints used

| Purpose | Method | Endpoint | Payload |
|---|---|---|---|
| Menu | GET | `/api/menu` | none |
| Current session | GET | `/api/me` | none |
| Register | POST | `/api/register` | `{ name, email, password }` |
| Sign in | POST | `/api/login` | `{ email, password }` |
| Sign out | POST | `/api/logout` | `{}` |
| Reservation | POST | `/api/bookings` | `{ name, email, phone, date, time, guests, notes }` |
| Order | POST | `/api/orders` | `{ name, email, phone, fulfilment, address, payment, items:[{id,quantity}] }` |

`static/js/api-client.js` is the single API bridge. If the backend URL changes later, edit `API_ROOT` there. It uses same-origin requests and includes no database credentials or secret values.

## Administrator dashboard

The existing Python backend enforces administrator authorization on each
`/api/admin/*` endpoint. Create the first administrator with
`MESA_Backend/setup_admin.py`; do not set a role in frontend JavaScript.
Administrator APIs provide summary statistics, customer access management,
order and reservation statuses, menu create/edit/archive/restore, and the audit
log. The interface verifies the protected administrator endpoint and does not
rely on hiding controls as authorization.

## Media and sound behaviour

All supplied photographs, the burger kitchen video and the supplied MP3 are bundled in `static/media/`. The hero video starts automatically, muted and looping. The visitor starts the soundtrack using the visible **PLAY MUSIC** control; playback can be paused/resumed, and the volume is adjustable. Browsers generally block autoplay with sound; the page waits for a visitor interaction. The food-photo feature rotates automatically and also has previous, next and pause controls.

The MP3's licensing terms have not been independently verified. Confirm the
rights before commercial/public use.

## Deployment

Use the existing Python/SQLite backend with durable local storage and HTTPS
termination. See [`MESA_Backend/DEPLOYMENT.md`](../../MESA_Backend/DEPLOYMENT.md)
for production environment variables, startup, health checks, and backup/
recovery guidance. Do not deploy SQLite to an ephemeral filesystem.
