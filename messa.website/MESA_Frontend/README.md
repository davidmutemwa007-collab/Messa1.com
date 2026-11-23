# MESA Kitchen & Social — Frontend

The existing MESA frontend is served by the standalone Python/SQLite backend.
It uses the supplied photography, hero video and soundtrack, with customer
accounts, menu, cart, checkout, reservations, and the protected admin workspace.

## Run the existing project

Keep `MESA_Backend/data/mesa.sqlite3` and `secret.key` with the backend. Start
from the backend with `start.bat` and visit `http://127.0.0.1:5000`. The
backend serves this folder's `templates/` and `static/` resources.

See `docs/BACKEND-CONNECTION.md` for the API contract and
[`MESA_Backend/DEPLOYMENT.md`](../MESA_Backend/DEPLOYMENT.md) for production
hosting and persistent SQLite guidance.

## What's included

- Cinematic hero with your burger-preparation video as a full-bleed background and clear headline overlay.
- Real food and restaurant photographs from both of your image uploads, bundled locally.
- Auto-rotating photo feature with manual previous/next, pause and slide selectors.
- Real-photo menu cards, server-loaded menu and category filters.
- Customer registration, login and logout forms connected to the original standalone API.
- Basket, quantity changes, checkout and reservation request forms connected to the original API.
- Role-specific administrator dashboard connected to protected Python endpoints for analytics, order/reservation status, customer/staff access, menu administration, mobile-money manual review, delivery zones/assignments, website content, image uploads and audit history. Backend permission checks authorize every operation.
- Server-priced delivery zones and enabled mobile-money payment instructions. Payment references remain pending until an administrator manually reviews them; no online payment processor or automatic payment verification is configured.
- User-supplied soundtrack with a clear on/off control.
- Responsive PC and mobile layouts, favicon, accessible labels and reduced-motion preference support.

## Browser media policy

The video begins automatically muted. The visitor can enable the supplied soundtrack using the sound control. Chrome, Edge, Safari and mobile browsers restrict autoplay with sound until the visitor interacts with the page; there is no reliable frontend workaround. The carousel images rotate automatically by default.

## No paid services

No Vercel, Supabase, Node.js, npm, paid AI image tools, Runway, or external image service is needed. Media is included in `static/media/`. Google Fonts are an optional online font source; local system fallbacks are provided.

## Publishing preparation

The repository root contains a secret/data-safe `.gitignore`, a placeholder
`.env.example`, and GitHub Actions checks. No GitHub repository has been
created or pushed. Do not deploy the Python API to Vercel's ephemeral runtime:
it uses a long-running standard-library server and SQLite/uploads that require
persistent local storage. See `MESA_Backend/DEPLOYMENT.md` for the supported
single-instance Python host setup. No domain, provider account, or live payment
integration has been configured.
