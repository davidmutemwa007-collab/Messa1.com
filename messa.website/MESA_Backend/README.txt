MESA BACKEND 2.0 — STANDALONE PYTHON + SQLITE
================================================

WHAT THIS PACKAGE DOES
- Keeps the original standard-library Python HTTP server and SQLite database.
- Automatically adds role and account-active columns to an existing users table.
- Preserves existing customer accounts, password hashes, bookings and orders.
- Adds server-enforced administrator authorization and management APIs.
- Adds administrator audit logging.
- Keeps the original public customer API routes compatible.
- Stores revocable server-side sessions alongside signed HttpOnly cookies.

FOLDER PLACEMENT
Place this folder beside MESA_Frontend:

MESA_PROJECT/
  MESA_Backend/       <-- this package
    app.py
    setup_admin.py
    start.bat
    start.ps1
    requirements.txt
    data/              <-- copy your OLD data folder here
  MESA_Frontend/
    index.html
    static/
      css/
      js/
      media/

IMPORTANT: Copy the existing MESA_Backend/data folder (especially mesa.sqlite3
and secret.key) into this new MESA_Backend folder BEFORE first launch. Do not
replace your old database with a blank one. Keep an untouched backup elsewhere.
The app performs additive schema migration on startup.

FIRST RUN
1. Install Python 3.10 or newer.
2. Copy the old data folder into this package's MESA_Backend folder.
3. Run setup_admin.bat (or: python setup_admin.py) to create the first admin.
   The password is entered interactively and is never stored in this package.
4. Run start.bat.
5. Open http://127.0.0.1:5000 on the PC. A same-Wi-Fi phone URL is printed.

ADMIN SECURITY
- Customers cannot choose or self-assign the admin role during registration.
- Admin APIs check the signed-in account's role and endpoint permission on every request.
- Staff accounts use one of the explicit restaurant, manager, cashier, kitchen,
  delivery, or super-administrator roles.
- Local administrator bootstrap marks the password temporary and requires a
  password change before protected dashboard access.
- Admin setup is a local operator action, not a public registration route.
- Customer accounts can be disabled by an administrator.
- Role, account access, order/booking status, menu, payment review, delivery,
  content, and image operations are audit logged.
- Passwords use PBKDF2-HMAC-SHA256 with per-password random salts.
- Session cookies are HttpOnly and SameSite=Lax; do not expose this local HTTP
  server directly to the public internet. Use HTTPS/reverse proxy for production.

ADMIN API
GET  /api/admin/summary
GET  /api/admin/orders
GET  /api/admin/bookings
GET  /api/admin/users
GET  /api/admin/menu
GET  /api/admin/audit
POST /api/admin/orders/status       {"id": 1, "status": "Preparing"}
POST /api/admin/bookings/status     {"id": 1, "status": "Confirmed"}
POST /api/admin/users/access        {"user_id": 1, "active": false}
POST /api/admin/menu/save           {"id":"new-item","name":"...","description":"...","price":99,"category":"Mains","tag":"New"}
POST /api/admin/menu/delete         {"id":"new-item"}
POST /api/admin/menu/restore       {"id":"archived-item"}

The admin API is independent of frontend visibility. Hiding an admin link is not
security; the backend authorization check is the actual protection.

PAYMENTS AND DELIVERY
- Mobile-money providers start disabled. An operator must enter the real
  merchant account details before enabling a method.
- The app does not connect to MTN, Airtel, Zamtel or a payment gateway.
  Customers can submit a transaction reference; a staff member must review it.
  A submitted reference is not proof of payment, and no transaction is verified
  automatically.
- Delivery areas start inactive and have no assumed fee. Configure real zone
  fees, order minimums and free-delivery thresholds before enabling them.

The application rejects cross-origin POST requests, uses SameSite cookies, and
revokes sessions at logout; still add HTTPS, edge rate limiting, monitoring and
automated backups for public production.

DEPLOYMENT
See DEPLOYMENT.md. Run one Python instance with SQLite on durable local storage
behind an HTTPS reverse proxy. Vercel's ephemeral filesystem is not suitable
for this SQLite-backed application.

WHERE DOES api-client.js GO?
The standalone API connector is NOT a backend ZIP. It is a frontend JavaScript
file and belongs at:
  MESA_Frontend/static/js/api-client.js
The Professional Refresh frontend ZIP already contains this exact file. If you
already extracted that frontend ZIP, do not download/copy another connector.
Keep app.py in MESA_Backend; do not place api-client.js beside app.py.
